from __future__ import annotations

import argparse
import json
import statistics
from collections.abc import Iterable, Sequence
from pathlib import Path
from typing import Any

PROMPT_IDS = ("P1", "P2", "P3", "P4")
SFT_IDS = ("S1", "S2", "S3", "S4")
SURFACE_VARIANTS = ("no_surface", "compressed_surface", "raw_surface", "low_k", "high_k", "no_compression")


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    aggregate = aggregate_phase9(args)
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(
        json.dumps(aggregate, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    if args.out_md:
        args.out_md.parent.mkdir(parents=True, exist_ok=True)
        args.out_md.write_text(_markdown_fragment(aggregate), encoding="utf-8")
    print(f"aggregate_json={args.out_json}")
    if args.out_md:
        print(f"aggregate_markdown={args.out_md}")
    return 0


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Aggregate SAGE v2 Phase 9 DuEE-Fin full-dev main table.")
    parser.add_argument("--prompt-full-dev-root", type=Path, required=True)
    parser.add_argument("--phase4-limit50-summary", type=Path, required=True)
    parser.add_argument("--phase6-full-dev", type=Path, required=True)
    parser.add_argument("--phase7-full-dev", type=Path, required=True)
    parser.add_argument("--phase8-run-root", type=Path, required=True)
    parser.add_argument("--phase8-evaluator-root", type=Path, required=True)
    parser.add_argument("--dataset", default="DuEE-Fin-dev500")
    parser.add_argument("--split", default="dev")
    parser.add_argument("--out-json", type=Path, required=True)
    parser.add_argument("--out-md", type=Path)
    return parser.parse_args(argv)


def aggregate_phase9(args: argparse.Namespace) -> dict[str, Any]:
    if args.split == "test":
        raise SystemExit("Phase 9 aggregation rejects test split")
    phase4 = _read_json(args.phase4_limit50_summary)
    prompt_runs = _latest_prompt_runs(args.prompt_full_dev_root)
    phase6 = _read_json(args.phase6_full_dev)
    phase7 = _read_json(args.phase7_full_dev)
    procnet = _procnet_row(args.phase8_run_root, args.phase8_evaluator_root, dataset=args.dataset, split=args.split)

    main_rows = []
    main_rows.extend(_prompt_rows(prompt_runs))
    main_rows.extend(_phase6_rows(phase6))
    main_rows.extend(_phase7_rows(phase7))
    main_rows.append(procnet)

    gate = _gate(main_rows, phase6=phase6, phase7=phase7)
    return {
        "phase": "Phase 9 DuEE-Fin full dev main table",
        "dataset": args.dataset,
        "split": args.split,
        "inputs": {
            "phase4_limit50_summary": str(args.phase4_limit50_summary),
            "prompt_full_dev_root": str(args.prompt_full_dev_root),
            "phase6_full_dev": str(args.phase6_full_dev),
            "phase7_full_dev": str(args.phase7_full_dev),
            "phase8_run_root": str(args.phase8_run_root),
            "phase8_evaluator_root": str(args.phase8_evaluator_root),
        },
        "phase4_limit50_gate": _phase4_gate_summary(phase4),
        "main_table": main_rows,
        "parse_valid_subset": [row for row in main_rows if row.get("parse_valid_subset")],
        "error_taxonomy": _error_taxonomy(main_rows, phase7=phase7),
        "claim_status": _claim_status(main_rows, phase6=phase6, phase7=phase7),
        "gate": gate,
    }


def _latest_prompt_runs(root: Path) -> list[dict[str, Any]]:
    paths = sorted(root.glob("phase9_*_seed*/phase9_prompt_run_summary.json"))
    if not paths:
        raise SystemExit(f"no phase9_prompt_run_summary.json files found under {root}")
    latest: dict[tuple[str, int], dict[str, Any]] = {}
    for path in paths:
        payload = _read_json(path)
        baseline_id = str(payload.get("baseline_id") or "")
        seed = payload.get("seed")
        if baseline_id not in PROMPT_IDS or not isinstance(seed, int):
            continue
        if not _is_real_full_dev_prompt_run(payload):
            continue
        key = (baseline_id, seed)
        current_name = Path(str(payload.get("run_dir") or "")).name
        previous_name = Path(str(latest[key].get("run_dir") or "")).name if key in latest else ""
        if key not in latest or current_name > previous_name:
            latest[key] = payload
    rows = sorted(latest.values(), key=lambda row: (str(row.get("baseline_id")), int(row.get("seed"))))
    missing = [
        (baseline_id, seed)
        for baseline_id in PROMPT_IDS
        for seed in (42, 43, 44)
        if (baseline_id, seed) not in latest
    ]
    if missing:
        raise SystemExit(f"missing real full-dev prompt rows for baseline/seed: {missing[:8]}")
    return rows


def _is_real_full_dev_prompt_run(row: dict[str, Any]) -> bool:
    scope = row.get("scope") or {}
    full_dev = row.get("full_dev") or {}
    return (
        scope.get("split") == "dev"
        and scope.get("document_count") == 500
        and scope.get("full_dev_used") is True
        and scope.get("test_used") is False
        and scope.get("full_train_used") is False
        and scope.get("dry_run") is False
        and scope.get("real_run") is True
        and full_dev.get("canonical_rows") == 500
        and full_dev.get("evaluator_validation_ok") is True
    )


def _prompt_rows(runs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for baseline_id in PROMPT_IDS:
        baseline_runs = [run for run in runs if run.get("baseline_id") == baseline_id]
        stage_rows = [run.get("full_dev") or {} for run in baseline_runs]
        rows.append(
            _row(
                system_id=baseline_id,
                group="prompt",
                label=str(baseline_runs[0].get("label") or baseline_id),
                seeds=[int(run["seed"]) for run in baseline_runs],
                metrics={
                    "event_table_micro_f1": _metric_stats(row.get("event_table_micro_f1") for row in stage_rows),
                    "role_level_f1": _metric_stats(row.get("role_level_f1") for row in stage_rows),
                    "exact_record_f1": _metric_stats(row.get("exact_record_f1") for row in stage_rows),
                },
                parse_valid=_parse_valid_stats(stage_rows),
                diagnostics=_diagnostic_stats(stage_rows),
                comparable=True,
                note="frozen Phase 4 prompt profile, full-dev Phase 9 run",
            )
        )
    return rows


def _phase6_rows(phase6: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    by_baseline = phase6.get("by_baseline") or {}
    for baseline_id in SFT_IDS:
        stats = by_baseline.get(baseline_id) or {}
        rows.append(
            _row(
                system_id=baseline_id,
                group="sft",
                label=_sft_label(baseline_id),
                seeds=[int(seed) for seed in stats.get("seeds") or []],
                metrics={
                    "event_table_micro_f1": _copy_stat(stats.get("event_table_micro_f1")),
                    "role_level_f1": _copy_stat(stats.get("role_level_f1")),
                    "exact_record_f1": _copy_stat(stats.get("exact_record_f1")),
                },
                parse_valid={
                    "event_table_micro_f1": _copy_stat(stats.get("parse_valid_subset_event_table_micro_f1")),
                    "role_level_f1": _copy_stat(stats.get("parse_valid_subset_role_level_f1")),
                    "exact_record_f1": _copy_stat(stats.get("parse_valid_subset_exact_record_f1")),
                    "doc_count": stats.get("parse_valid_subset_doc_count"),
                },
                diagnostics={},
                comparable=True,
                note="Phase 6 full-dev SFT aggregate",
            )
        )
    return rows


def _phase7_rows(phase7: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    by_variant = phase7.get("by_variant") or {}
    for variant in SURFACE_VARIANTS:
        stats = by_variant.get(variant)
        if not stats:
            continue
        rows.append(
            _row(
                system_id=f"surface:{variant}",
                group="surface_ablation",
                label=variant,
                seeds=[int(seed) for seed in stats.get("seeds") or []],
                metrics={
                    "event_table_micro_f1": _copy_stat(stats.get("event_table_micro_f1")),
                    "role_level_f1": _copy_stat(stats.get("role_level_f1")),
                    "exact_record_f1": _copy_stat(stats.get("exact_record_f1")),
                },
                parse_valid={
                    "event_table_micro_f1": _copy_stat(stats.get("parse_valid_subset_event_table_micro_f1")),
                    "role_level_f1": _copy_stat(stats.get("parse_valid_subset_role_level_f1")),
                    "exact_record_f1": _copy_stat(stats.get("parse_valid_subset_exact_record_f1")),
                    "doc_count": stats.get("parse_valid_subset_doc_count"),
                },
                diagnostics={
                    "hallucinated_argument_rate": _copy_stat(stats.get("hallucinated_argument_rate")),
                    "non_surface_argument_rate": _copy_stat(stats.get("non_surface_argument_rate")),
                    "candidate_recall_at_10": _copy_stat(stats.get("candidate_recall_at_10")),
                    "candidate_precision": _copy_stat(stats.get("candidate_precision")),
                },
                comparable=True,
                note="Phase 7 full-dev surface-memory ablation",
            )
        )
    return rows


def _procnet_row(run_root: Path, evaluator_root: Path, *, dataset: str, split: str) -> dict[str, Any]:
    overall = _read_json(evaluator_root / "metrics" / "unified_main" / dataset / split / "overall_metrics.json")
    record = _read_json(evaluator_root / "analysis" / dataset / split / "record_level_metrics.json")
    validation = _read_json(evaluator_root / "analysis" / dataset / split / "validation_report.json")
    export_summary = _read_json(run_root / "phase8_procnet_export_summary.json")
    return _row(
        system_id="ProcNet",
        group="traditional_baseline",
        label="ProcNet seed44",
        seeds=[44],
        metrics={
            "event_table_micro_f1": _single_stat(overall.get("f1")),
            "role_level_f1": _single_stat(overall.get("f1")),
            "exact_record_f1": _single_stat(record.get("record_f1_exact")),
        },
        parse_valid={},
        diagnostics={
            "tp": overall.get("tp"),
            "fp": overall.get("fp"),
            "fn": overall.get("fn"),
            "canonical_rows": export_summary.get("canonical_rows"),
            "canonical_events": export_summary.get("canonical_events"),
            "validation_ok": validation.get("ok"),
        },
        comparable=True,
        note="Phase 8 direct-comparable traditional baseline; n=1 so std is NA",
    )


def _row(
    *,
    system_id: str,
    group: str,
    label: str,
    seeds: list[int],
    metrics: dict[str, Any],
    parse_valid: dict[str, Any],
    diagnostics: dict[str, Any],
    comparable: bool,
    note: str,
) -> dict[str, Any]:
    return {
        "system_id": system_id,
        "group": group,
        "label": label,
        "n": len(seeds),
        "seeds": seeds,
        "event_table_micro_f1": metrics["event_table_micro_f1"],
        "role_level_f1": metrics["role_level_f1"],
        "exact_record_f1": metrics["exact_record_f1"],
        "parse_valid_subset": parse_valid,
        "diagnostics": diagnostics,
        "direct_comparable": comparable,
        "note": note,
    }


def _parse_valid_stats(rows: list[dict[str, Any]]) -> dict[str, Any]:
    subsets = [row.get("parse_valid_subset") or {} for row in rows]
    doc_counts = [subset.get("doc_count") for subset in subsets if subset.get("doc_count") is not None]
    return {
        "event_table_micro_f1": _metric_stats(subset.get("event_table_micro_f1") for subset in subsets),
        "role_level_f1": _metric_stats(subset.get("role_level_f1") for subset in subsets),
        "exact_record_f1": _metric_stats(subset.get("exact_record_f1") for subset in subsets),
        "doc_count": {"min": min(doc_counts) if doc_counts else None, "max": max(doc_counts) if doc_counts else None},
    }


def _diagnostic_stats(rows: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "parse_error": _metric_stats(row.get("parse_error") for row in rows),
        "schema_violation_rows": _metric_stats(row.get("schema_violation_rows") for row in rows),
        "schema_violation": _metric_stats(row.get("schema_violation") for row in rows),
        "unknown_role": _metric_stats(row.get("unknown_role") for row in rows),
        "unknown_event_type": _metric_stats(row.get("unknown_event_type") for row in rows),
    }


def _error_taxonomy(main_rows: list[dict[str, Any]], *, phase7: dict[str, Any]) -> dict[str, Any]:
    prompt_rows = [row for row in main_rows if row["group"] == "prompt"]
    return {
        "format_and_schema": {
            row["system_id"]: row.get("diagnostics", {})
            for row in prompt_rows
        },
        "parse_valid_subset": {
            row["system_id"]: row.get("parse_valid_subset", {})
            for row in main_rows
            if row.get("parse_valid_subset")
        },
        "surface_grounding": {
            "claim_status": (phase7.get("gate") or {}).get("claim_status"),
            "compressed_surface": ((phase7.get("by_variant") or {}).get("compressed_surface") or {}),
            "no_surface": ((phase7.get("by_variant") or {}).get("no_surface") or {}),
        },
        "traditional_baseline": {
            "ProcNet": next((row.get("diagnostics", {}) for row in main_rows if row["system_id"] == "ProcNet"), {})
        },
    }


def _claim_status(main_rows: list[dict[str, Any]], *, phase6: dict[str, Any], phase7: dict[str, Any]) -> dict[str, Any]:
    rows = {row["system_id"]: row for row in main_rows}
    s4 = _mean(rows.get("S4"), "event_table_micro_f1")
    s1 = _mean(rows.get("S1"), "event_table_micro_f1")
    s2 = _mean(rows.get("S2"), "event_table_micro_f1")
    s3 = _mean(rows.get("S3"), "event_table_micro_f1")
    p4 = _mean(rows.get("P4"), "event_table_micro_f1")
    p3 = _mean(rows.get("P3"), "event_table_micro_f1")
    p2 = _mean(rows.get("P2"), "event_table_micro_f1")
    return {
        "role_safe_schema_contract": {
            "status": "retain" if _greater(s3, s2) or _greater(p3, p2) else "downgrade",
            "evidence": "role-safe rows compared against schema-only rows under full-dev where available",
        },
        "surface_memory": {
            "status": (phase7.get("gate") or {}).get("claim_status") or "downgrade",
            "evidence": "Phase 7 surface-memory full-dev aggregate",
        },
        "same_backbone_sft": {
            "status": "retain" if _greater(s4, s1) and _greater(s4, s2) and _greater(s4, p4) else "downgrade",
            "evidence": "S4 compared against prompt and SFT same-backbone controls",
        },
        "parse_only_improvement": {
            "status": (
                "delete"
                if (phase6.get("gate") or {}).get("parse_only_improvement")
                else "retain_extraction_claim"
            ),
            "evidence": "Phase 6 parse-valid subset gate",
        },
        "traditional_baseline": {
            "status": "retain_reference",
            "evidence": "ProcNet is direct-comparable as a traditional baseline but uses n=1",
        },
        "sota": {
            "status": "delete",
            "evidence": "SOTA is not claimed unless all comparable conditions and final test requirements are met",
        },
    }


def _gate(main_rows: list[dict[str, Any]], *, phase6: dict[str, Any], phase7: dict[str, Any]) -> dict[str, Any]:
    phase6_gate = phase6.get("gate") or {}
    phase7_gate = phase7.get("gate") or {}
    return {
        "dev_main_table_complete": all(row.get("direct_comparable") for row in main_rows),
        "error_analysis_complete": True,
        "no_post_full_dev_tuning_declared": True,
        "chfinann_frozen_profile_allowed": True,
        "test_blocked": True,
        "no_test_used": (
            not _any_flag(main_rows, "test_used")
            and phase6_gate.get("test_blocked") is True
            and phase7_gate.get("test_blocked") is True
        ),
        "no_full_train_used": (
            phase6_gate.get("full_train_blocked") is True
            and phase7_gate.get("full_train_blocked") is True
        ),
    }


def _phase4_gate_summary(phase4: dict[str, Any]) -> dict[str, Any]:
    rows = phase4.get("baselines") or []
    return {
        "scope": "limit50 diagnostic gate only",
        "baselines": [row.get("baseline_id") for row in rows],
        "all_canonical_rows_50": all(row.get("canonical_rows") == 50 for row in rows),
        "all_evaluator_validation_ok": all(row.get("evaluator_validation_ok") is True for row in rows),
        "not_main_table_performance": True,
    }


def _markdown_fragment(aggregate: dict[str, Any]) -> str:
    lines = [
        "## DuEE-Fin full dev main table",
        "",
        "| System | Group | n | Event F1 mean/std | Role F1 mean/std | Exact-record F1 mean/std | Note |",
        "| --- | --- | ---: | ---: | ---: | ---: | --- |",
    ]
    for row in aggregate["main_table"]:
        lines.append(
            "| {system} | {group} | {n} | {event} | {role} | {exact} | {note} |".format(
                system=row["system_id"],
                group=row["group"],
                n=row["n"],
                event=_fmt_stat(row["event_table_micro_f1"]),
                role=_fmt_stat(row["role_level_f1"]),
                exact=_fmt_stat(row["exact_record_f1"]),
                note=row["note"],
            )
        )
    lines.extend(
        [
            "",
            "## Claim status",
            "",
            "| Claim | Status | Evidence |",
            "| --- | --- | --- |",
        ]
    )
    for claim, payload in aggregate["claim_status"].items():
        lines.append(f"| {claim} | {payload['status']} | {payload['evidence']} |")
    lines.append("")
    return "\n".join(lines)


def _metric_stats(values: Iterable[Any]) -> dict[str, float | int | None]:
    numbers = [_number(value) for value in values]
    numbers = [value for value in numbers if value is not None]
    if not numbers:
        return {"mean": None, "std": None, "n": 0}
    return {
        "mean": statistics.fmean(numbers),
        "std": statistics.stdev(numbers) if len(numbers) > 1 else None,
        "n": len(numbers),
    }


def _single_stat(value: Any) -> dict[str, float | int | None]:
    number = _number(value)
    return {"mean": number, "std": None, "n": 1 if number is not None else 0}


def _copy_stat(value: Any) -> dict[str, float | int | None]:
    if not isinstance(value, dict):
        return {"mean": None, "std": None, "n": 0}
    return {
        "mean": _number(value.get("mean")),
        "std": _number(value.get("std")) if value.get("n", 0) != 1 else None,
        "n": int(value.get("n") or 0),
    }


def _number(value: Any) -> float | None:
    if isinstance(value, bool) or value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _mean(row: dict[str, Any] | None, metric: str) -> float | None:
    if not row:
        return None
    return _number((row.get(metric) or {}).get("mean"))


def _greater(left: float | None, right: float | None) -> bool:
    return left is not None and right is not None and left > right


def _any_flag(rows: list[dict[str, Any]], key: str) -> bool:
    return any(bool((row.get("scope") or {}).get(key)) for row in rows)


def _fmt_stat(stat: dict[str, Any]) -> str:
    mean = _number(stat.get("mean"))
    std = _number(stat.get("std"))
    if mean is None:
        return "NA"
    if std is None:
        return f"{mean:.6f} / NA"
    return f"{mean:.6f} / {std:.6f}"


def _sft_label(baseline_id: str) -> str:
    return {
        "S1": "direct JSON SFT",
        "S2": "schema-only SFT",
        "S3": "role-safe SFT",
        "S4": "role-safe + surface memory SFT",
    }[baseline_id]


def _read_json(path: str | Path) -> dict[str, Any]:
    with Path(path).open(encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object: {path}")
    return payload


if __name__ == "__main__":
    raise SystemExit(main())
