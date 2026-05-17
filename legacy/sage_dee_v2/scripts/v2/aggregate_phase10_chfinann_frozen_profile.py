from __future__ import annotations

import argparse
import json
import statistics
from collections.abc import Iterable, Sequence
from pathlib import Path
from typing import Any

BASELINE_IDS = ("S1", "S2", "S4")
REQUIRED_SEEDS = {"S1": (42, 43), "S2": (42, 43), "S4": (42, 43, 44)}
METRIC_KEYS = ("event_table_micro_f1", "role_level_f1", "exact_record_f1")
DIAGNOSTIC_KEYS = (
    "parse_error",
    "schema_violation_rows",
    "schema_violation",
    "unknown_role",
    "unknown_event_type",
    "canonical_rows",
    "canonical_event_count",
)
SURFACE_KEYS = (
    "candidate_recall_at_10",
    "candidate_precision",
    "hallucinated_argument_rate",
    "non_surface_argument_rate",
)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    aggregate = aggregate_phase10(args)
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
    parser = argparse.ArgumentParser(description="Aggregate SAGE v2 Phase 10 ChFinAnn frozen-profile robustness.")
    parser.add_argument("--runs-root", type=Path, required=True)
    parser.add_argument("--stage", choices=("limit50", "full-dev", "full_dev"), default="full-dev")
    parser.add_argument("--dataset", default="ChFinAnn")
    parser.add_argument("--split", default="dev")
    parser.add_argument("--out-json", type=Path, required=True)
    parser.add_argument("--out-md", type=Path)
    return parser.parse_args(argv)


def aggregate_phase10(args: argparse.Namespace) -> dict[str, Any]:
    if args.dataset != "ChFinAnn":
        raise SystemExit("Phase 10 aggregation only permits ChFinAnn")
    if args.split == "test":
        raise SystemExit("Phase 10 aggregation rejects test split")
    if args.split != "dev":
        raise SystemExit(f"Phase 10 aggregation only permits dev split, got {args.split!r}")
    stage_key = _stage_key(args.stage)
    summaries = _latest_summary_by_seed(_load_run_summaries(args.runs_root), stage_key=stage_key)
    rows = [_metric_row(summary, stage_key=stage_key) for summary in summaries]
    _require_seed_coverage(rows)

    by_baseline = {}
    for baseline_id in BASELINE_IDS:
        baseline_rows = [row for row in rows if row["baseline_id"] == baseline_id]
        by_baseline[baseline_id] = _baseline_stats(baseline_rows)
    gate = _gate(by_baseline)
    return {
        "phase": "Phase 10 ChFinAnn frozen-profile robustness",
        "dataset": args.dataset,
        "split": args.split,
        "stage": stage_key,
        "run_count": len(rows),
        "by_baseline": by_baseline,
        "runs": rows,
        "gate": gate,
        "claim_status": _claim_status(by_baseline),
        "error_taxonomy": _error_taxonomy(by_baseline),
    }


def _load_run_summaries(runs_root: Path) -> list[dict[str, Any]]:
    paths = sorted(runs_root.glob("phase10_*_seed*/phase10_run_summary.json"))
    if not paths:
        raise SystemExit(f"no phase10_run_summary.json files found under {runs_root}")
    summaries = []
    for path in paths:
        payload = _read_json(path)
        if isinstance(payload, dict):
            summaries.append(payload)
    return summaries


def _latest_summary_by_seed(summaries: list[dict[str, Any]], *, stage_key: str) -> list[dict[str, Any]]:
    latest: dict[tuple[str, int], dict[str, Any]] = {}
    for summary in summaries:
        baseline_id = str(summary.get("baseline_id") or "")
        seed = summary.get("seed")
        stage = summary.get(stage_key) or {}
        scope = summary.get("scope") or {}
        if baseline_id not in BASELINE_IDS or not isinstance(seed, int):
            continue
        if scope.get("dataset") != "ChFinAnn" or scope.get("split") != "dev":
            continue
        if scope.get("dry_run") or not scope.get("real_run"):
            continue
        if scope.get("test_used") or scope.get("train_used") or scope.get("full_train_used"):
            continue
        if scope.get("no_chfinann_tuning") is not True:
            continue
        if not _stage_valid(stage, stage_key=stage_key):
            continue
        key = (baseline_id, seed)
        if key not in latest or _summary_sort_key(summary) > _summary_sort_key(latest[key]):
            latest[key] = summary
    return sorted(latest.values(), key=lambda summary: (str(summary.get("baseline_id")), int(summary["seed"])))


def _stage_valid(stage: dict[str, Any], *, stage_key: str) -> bool:
    expected_rows = 50 if stage_key == "limit50" else 3204
    if stage.get("canonical_rows") != expected_rows:
        return False
    if stage.get("evaluator_attempted") is not True:
        return False
    if stage.get("evaluator_validation_ok") is not True:
        return False
    return True


def _metric_row(summary: dict[str, Any], *, stage_key: str) -> dict[str, Any]:
    stage = summary.get(stage_key) or {}
    parse_valid = stage.get("parse_valid_subset") or {}
    surface = stage.get("surface_diagnostics") or {}
    recall_at_k = surface.get("candidate_recall_at_k") or {}
    return {
        "baseline_id": str(summary.get("baseline_id") or ""),
        "seed": int(summary.get("seed")),
        "run_dir": summary.get("run_dir"),
        "adapter_path": summary.get("adapter_path"),
        "event_table_micro_f1": _number(stage.get("event_table_micro_f1")),
        "role_level_f1": _number(stage.get("role_level_f1")),
        "exact_record_f1": _number(stage.get("exact_record_f1")),
        "parse_error": _number(stage.get("parse_error")),
        "schema_violation_rows": _number(stage.get("schema_violation_rows")),
        "schema_violation": _number(stage.get("schema_violation")),
        "unknown_role": _number(stage.get("unknown_role")),
        "unknown_event_type": _number(stage.get("unknown_event_type")),
        "canonical_rows": _number(stage.get("canonical_rows")),
        "canonical_event_count": _number(stage.get("canonical_event_count")),
        "parse_valid_subset_event_table_micro_f1": _number(parse_valid.get("event_table_micro_f1")),
        "parse_valid_subset_role_level_f1": _number(parse_valid.get("role_level_f1")),
        "parse_valid_subset_exact_record_f1": _number(parse_valid.get("exact_record_f1")),
        "parse_valid_subset_doc_count": parse_valid.get("doc_count"),
        "candidate_recall_at_10": _number(recall_at_k.get("10")),
        "candidate_precision": _number(surface.get("candidate_precision")),
        "hallucinated_argument_rate": _number(surface.get("hallucinated_argument_rate")),
        "non_surface_argument_rate": _number(surface.get("non_surface_argument_rate")),
        "test_used": bool((summary.get("scope") or {}).get("test_used")),
        "train_used": bool((summary.get("scope") or {}).get("train_used")),
        "full_train_used": bool((summary.get("scope") or {}).get("full_train_used")),
    }


def _baseline_stats(rows: list[dict[str, Any]]) -> dict[str, Any]:
    payload: dict[str, Any] = {"seed_count": len(rows), "seeds": [row.get("seed") for row in rows]}
    for key in (*METRIC_KEYS, *DIAGNOSTIC_KEYS):
        payload[key] = _metric_stats(row.get(key) for row in rows)
    for key in (
        "parse_valid_subset_event_table_micro_f1",
        "parse_valid_subset_role_level_f1",
        "parse_valid_subset_exact_record_f1",
    ):
        payload[key] = _metric_stats(row.get(key) for row in rows)
    doc_counts = [
        row.get("parse_valid_subset_doc_count")
        for row in rows
        if row.get("parse_valid_subset_doc_count") is not None
    ]
    payload["parse_valid_subset_doc_count"] = {
        "min": min(doc_counts) if doc_counts else None,
        "max": max(doc_counts) if doc_counts else None,
    }
    payload["surface_diagnostics"] = {
        key: _metric_stats(row.get(key) for row in rows)
        for key in SURFACE_KEYS
    }
    payload["test_used"] = any(row.get("test_used") for row in rows)
    payload["train_used"] = any(row.get("train_used") for row in rows)
    payload["full_train_used"] = any(row.get("full_train_used") for row in rows)
    return payload


def _gate(by_baseline: dict[str, Any]) -> dict[str, Any]:
    return {
        "required_seed_coverage": _seed_coverage(by_baseline),
        "test_blocked": not any(by_baseline[baseline].get("test_used") for baseline in by_baseline),
        "train_blocked": not any(by_baseline[baseline].get("train_used") for baseline in by_baseline),
        "full_train_blocked": not any(by_baseline[baseline].get("full_train_used") for baseline in by_baseline),
        "no_chfinann_tuning": True,
        "robustness_evidence_complete": all(
            ((by_baseline[baseline].get("event_table_micro_f1") or {}).get("n") or 0) > 0
            for baseline in BASELINE_IDS
        ),
    }


def _claim_status(by_baseline: dict[str, Any]) -> dict[str, Any]:
    s4 = _mean(by_baseline, "S4", "event_table_micro_f1")
    s2 = _mean(by_baseline, "S2", "event_table_micro_f1")
    s1 = _mean(by_baseline, "S1", "event_table_micro_f1")
    delta = None if s4 is None or s2 is None else s4 - s2
    limitation_required = delta is None or delta < 0.02
    return {
        "frozen_profile_robustness": {
            "status": "diagnostic_only",
            "evidence": "ChFinAnn dev frozen-profile run; not a generalization or SOTA claim",
        },
        "role_safe_schema_contract": {
            "status": "diagnostic_only",
            "evidence": "Compare S2/S4 schema invalid and unknown-role diagnostics under frozen profile",
        },
        "surface_memory": {
            "status": "no_obvious_harm" if s4 is not None and s1 is not None and s4 >= s1 else "limitation",
            "evidence": "S4 compared against S1/S2 with surface diagnostics",
        },
        "limitation": {
            "status": "robustness limitation required" if limitation_required else "limitation optional",
            "evidence": "Write limitation when ChFinAnn transfer gain is small",
        },
        "sota": {
            "status": "not_claimed",
            "evidence": "Phase 10 is dev-only robustness validation; test split is blocked",
        },
    }


def _error_taxonomy(by_baseline: dict[str, Any]) -> dict[str, Any]:
    return {
        baseline_id: {
            "parse_error": stats.get("parse_error"),
            "schema_invalid": stats.get("schema_violation"),
            "schema_invalid_rows": stats.get("schema_violation_rows"),
            "unknown_role": stats.get("unknown_role"),
            "unknown_event_type": stats.get("unknown_event_type"),
            "surface_diagnostics": stats.get("surface_diagnostics"),
        }
        for baseline_id, stats in by_baseline.items()
    }


def _require_seed_coverage(rows: list[dict[str, Any]]) -> None:
    actual: dict[str, set[int]] = {baseline_id: set() for baseline_id in BASELINE_IDS}
    for row in rows:
        actual.setdefault(str(row.get("baseline_id")), set()).add(int(row.get("seed")))
    missing = {
        baseline_id: sorted(set(seeds) - actual.get(baseline_id, set()))
        for baseline_id, seeds in REQUIRED_SEEDS.items()
        if set(seeds) - actual.get(baseline_id, set())
    }
    if missing:
        raise SystemExit(f"missing required Phase 10 baseline/seed rows: {missing}")


def _seed_coverage(by_baseline: dict[str, Any]) -> bool:
    for baseline_id, seeds in REQUIRED_SEEDS.items():
        if tuple(by_baseline.get(baseline_id, {}).get("seeds") or ()) != seeds:
            return False
    return True


def _markdown_fragment(aggregate: dict[str, Any]) -> str:
    lines = [
        "## ChFinAnn frozen-profile robustness",
        "",
        "| System | n | Seeds | Event-table micro-F1 mean/std | Role-level F1 mean/std | "
        "Parse error mean/std | Schema invalid mean/std | Note |",
        "| --- | ---: | --- | ---: | ---: | ---: | ---: | --- |",
    ]
    for baseline_id in BASELINE_IDS:
        row = aggregate["by_baseline"][baseline_id]
        lines.append(
            (
                "| {system} | {n} | {seeds} | {event} | {role} | {parse_error} | "
                "{schema_invalid} | frozen DuEE-Fin profile |"
            ).format(
                system=baseline_id,
                n=row["seed_count"],
                seeds=",".join(str(seed) for seed in row["seeds"]),
                event=_fmt_stat(row["event_table_micro_f1"]),
                role=_fmt_stat(row["role_level_f1"]),
                parse_error=_fmt_stat(row["parse_error"]),
                schema_invalid=_fmt_stat(row["schema_violation"]),
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
        "std": statistics.stdev(numbers) if len(numbers) > 1 else 0.0,
        "n": len(numbers),
    }


def _mean(by_baseline: dict[str, Any], baseline_id: str, metric_key: str) -> float | None:
    return _number(((by_baseline.get(baseline_id) or {}).get(metric_key) or {}).get("mean"))


def _number(value: Any) -> float | None:
    if isinstance(value, bool) or value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _summary_sort_key(summary: dict[str, Any]) -> str:
    return Path(str(summary.get("run_dir") or "")).name


def _stage_key(stage: str) -> str:
    return "full_dev" if stage in {"full-dev", "full_dev"} else "limit50"


def _fmt_stat(stat: dict[str, Any]) -> str:
    mean = _number(stat.get("mean"))
    std = _number(stat.get("std"))
    if mean is None:
        return "NA"
    if std is None:
        return f"{mean:.6f} / NA"
    return f"{mean:.6f} / {std:.6f}"


def _read_json(path: str | Path) -> dict[str, Any]:
    with Path(path).open(encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object: {path}")
    return payload


if __name__ == "__main__":
    raise SystemExit(main())
