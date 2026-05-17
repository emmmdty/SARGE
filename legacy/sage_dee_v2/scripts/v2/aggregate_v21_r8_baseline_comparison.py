from __future__ import annotations

import argparse
import json
import statistics
import sys
from collections.abc import Sequence
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SAGE_SYSTEMS = ("S2", "S3", "S4")
DIRECT_STATUSES = {"direct_comparable_reused", "direct_comparable_evaluated"}
REFERENCE_STATUSES = {"native_reference_only", "reference_only"}


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        aggregate = aggregate_r8(
            run_root=args.run_root,
            r7_summary_path=args.r7_summary,
            phase8_procnet_root=args.phase8_procnet_root,
        )
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(
        json.dumps(aggregate, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    args.out_md.parent.mkdir(parents=True, exist_ok=True)
    args.out_md.write_text(render_markdown(aggregate), encoding="utf-8")
    print(f"aggregate_json={args.out_json}")
    print(f"aggregate_md={args.out_md}")
    print(f"thesis_table_ready={aggregate['verdict']['thesis_table_ready']}")
    print(f"recommended_next_phase={aggregate['verdict']['recommended_next_phase']}")
    return 0


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Aggregate SAGE v2.1 R8 ProcNet baseline comparison.")
    parser.add_argument("--run-root", type=Path, required=True)
    parser.add_argument("--r7-summary", type=Path, required=True)
    parser.add_argument("--phase8-procnet-root", type=Path, required=True)
    parser.add_argument("--out-json", type=Path, required=True)
    parser.add_argument("--out-md", type=Path, required=True)
    return parser.parse_args(argv)


def aggregate_r8(*, run_root: Path, r7_summary_path: Path, phase8_procnet_root: Path) -> dict[str, Any]:
    r7 = _load_r7(r7_summary_path)
    procnet_rows = _load_procnet_rows(run_root, phase8_procnet_root=phase8_procnet_root)
    direct = [row for row in procnet_rows if row["status"] in DIRECT_STATUSES and row.get("direct_comparable")]
    reference_only = [row for row in procnet_rows if row["status"] in REFERENCE_STATUSES or row.get("reference_only")]
    missing = [row for row in procnet_rows if row["status"] == "missing_not_rerun"]
    ambiguous = [row for row in procnet_rows if row["status"] == "ambiguous_checkpoint_skipped"]
    _validate_main_rows(r7, direct)

    procnet_seed44 = _seed_row(direct, 44)
    sage_s4 = r7["system_stats"]["S4"]
    deltas = dict(r7.get("deltas") or {})
    if procnet_seed44 is not None:
        deltas["S4_mean_minus_ProcNet_seed44_strict_f1"] = (
            float(sage_s4["event_table_micro_f1"]["mean"]) - float(procnet_seed44["strict_f1"])
        )
        deltas["S4_exact_mean_minus_ProcNet_seed44_exact_record_f1"] = (
            float(sage_s4["exact_record_f1"]["mean"]) - float(procnet_seed44["exact_record_f1"])
        )
    else:
        deltas["S4_mean_minus_ProcNet_seed44_strict_f1"] = None
        deltas["S4_exact_mean_minus_ProcNet_seed44_exact_record_f1"] = None

    procnet_stats = _procnet_stats(direct)
    verdict = _verdict(procnet_seed44=procnet_seed44, direct_count=len(direct), deltas=deltas)
    return {
        "phase": "R8 ProcNet baseline comparison",
        "run_root": str(run_root),
        "r7_summary": str(r7_summary_path),
        "phase8_procnet_root": str(phase8_procnet_root),
        "scope": {
            "dev_only": True,
            "test_run": False,
            "test_gold_read": False,
            "procnet_training_run": False,
            "sage_training_run": False,
            "s4_retrained": False,
            "evaluator_modified": False,
            "procnet_original_modified": False,
            "frozen_final_modified": False,
            "sota_claim": False,
        },
        "sage": {
            "source": str(r7_summary_path),
            "system_stats": {system: r7["system_stats"][system] for system in SAGE_SYSTEMS},
            "deltas": r7.get("deltas") or {},
            "verdict": r7.get("verdict") or {},
        },
        "procnet": {
            "source": str(phase8_procnet_root),
            "direct_comparable": direct,
            "reference_only": reference_only,
            "missing": missing,
            "ambiguous": ambiguous,
            "direct_comparable_seed_count": len(direct),
            "reference_only_seed_count": len(reference_only),
            "missing_seed_count": len(missing),
            "ambiguous_seed_count": len(ambiguous),
            "stats": procnet_stats,
            "single_seed_direct_comparable": len(direct) == 1,
            "seed44_direct_comparable": procnet_seed44 is not None,
        },
        "deltas": deltas,
        "validation": {
            "same_dataset": all(row.get("dataset") == "DuEE-Fin-dev500" for row in direct),
            "same_split": all(row.get("split") == "dev" for row in direct),
            "same_evaluator": all(row.get("validation_ok") is True for row in direct),
            "all_procnet_direct_rows_validation_ok": all(row.get("validation_ok") is True for row in direct),
            "native_procnet_score_main_metric": False,
            "missing_seeds_marked": all(row.get("status") == "missing_not_rerun" for row in missing),
        },
        "verdict": verdict,
        "created_at": _created_at(),
    }


def render_markdown(aggregate: dict[str, Any]) -> str:
    sage_stats = aggregate["sage"]["system_stats"]
    lines = [
        "# SAGE v2.1 R8 ProcNet Baseline Comparison Summary",
        "",
        "R8 is dev-only. All main rows use DuEE-Fin-dev500/dev, canonical predictions, and sibling dee-eval.",
        "Native ProcNet scores are reference-only and are not used as direct-comparable main metrics.",
        "",
        "## SAGE Rows",
        "",
        "| System | Event/role F1 mean | Event/role F1 std | Exact-record F1 mean | Exact-record F1 std | Seeds |",
        "| --- | ---: | ---: | ---: | ---: | --- |",
    ]
    for system in SAGE_SYSTEMS:
        stats = sage_stats[system]
        lines.append(
            "| {system} | {event_mean:.6f} | {event_std:.6f} | {exact_mean:.6f} | {exact_std:.6f} | {seeds} |".format(
                system=system,
                event_mean=float(stats["event_table_micro_f1"]["mean"]),
                event_std=float(stats["event_table_micro_f1"]["std"]),
                exact_mean=float(stats["exact_record_f1"]["mean"]),
                exact_std=float(stats["exact_record_f1"]["std"]),
                seeds="/".join(str(seed) for seed in stats.get("seeds", [])),
            )
        )
    lines.extend(
        [
            "",
            "## ProcNet Rows",
            "",
            "| Seed | Status | Strict F1 | Exact-record F1 | Validation | Placement |",
            "| ---: | --- | ---: | ---: | --- | --- |",
        ]
    )
    for row in aggregate["procnet"]["direct_comparable"]:
        lines.append(
            "| {seed} | {status} | {strict:.6f} | {exact:.6f} | {validation} | main direct-comparable |".format(
                seed=row["seed"],
                status=row["status"],
                strict=float(row["strict_f1"]),
                exact=float(row["exact_record_f1"]),
                validation=row.get("validation_ok"),
            )
        )
    for row in aggregate["procnet"]["reference_only"]:
        lines.append(
            f"| {row['seed']} | {row['status']} | n/a | n/a | {row.get('validation_ok')} | reference-only |"
        )
    for row in aggregate["procnet"]["missing"]:
        lines.append(f"| {row['seed']} | missing_not_rerun | n/a | n/a | false | missing |")
    for row in aggregate["procnet"]["ambiguous"]:
        lines.append(f"| {row['seed']} | ambiguous_checkpoint_skipped | n/a | n/a | false | skipped |")
    lines.extend(["", "## Deltas", "", "| Delta | Value |", "| --- | ---: |"])
    for name, value in aggregate["deltas"].items():
        if isinstance(value, dict):
            for metric, metric_value in value.items():
                if metric in {"event_table_micro_f1", "exact_record_f1"}:
                    lines.append(f"| {name}.{metric} | {float(metric_value):.6f} |")
        elif value is None:
            lines.append(f"| {name} | n/a |")
        else:
            lines.append(f"| {name} | {float(value):.6f} |")
    verdict = aggregate["verdict"]
    lines.extend(
        [
            "",
            "## Verdict",
            "",
            f"procnet_direct_comparable_available: `{verdict['procnet_direct_comparable_available']}`",
            f"procnet_seed_count: `{verdict['procnet_seed_count']}`",
            f"sage_v21_beats_procnet_seed44_strict: `{verdict['sage_v21_beats_procnet_seed44_strict']}`",
            f"sage_v21_beats_procnet_seed44_exact: `{verdict['sage_v21_beats_procnet_seed44_exact']}`",
            f"thesis_table_ready: `{verdict['thesis_table_ready']}`",
            f"ccfa_claim_ready: `{verdict['ccfa_claim_ready']}`",
            f"recommended_next_phase: `{verdict['recommended_next_phase']}`",
            "",
        ]
    )
    return "\n".join(lines)


def _load_r7(path: Path) -> dict[str, Any]:
    payload = _read_json(path)
    if (payload.get("verdict") or {}).get("recommended_next_phase") != "R8_procnet_and_thesis_tables":
        raise ValueError("R7 summary does not recommend R8_procnet_and_thesis_tables")
    for system in SAGE_SYSTEMS:
        if system not in payload.get("system_stats", {}):
            raise ValueError(f"R7 summary missing {system} stats")
        stats = payload["system_stats"][system]
        for metric in ("event_table_micro_f1", "exact_record_f1"):
            if metric not in stats or "mean" not in stats[metric] or "std" not in stats[metric]:
                raise ValueError(f"R7 {system} missing {metric} mean/std")
    return payload


def _load_procnet_rows(run_root: Path, *, phase8_procnet_root: Path) -> list[dict[str, Any]]:
    rows = []
    for path in sorted(run_root.glob("procnet_seed*/seed_summary.json")):
        payload = _read_json(path)
        if payload.get("status") in DIRECT_STATUSES and payload.get("direct_comparable"):
            _require_direct_procnet_row(payload, path)
        rows.append(payload)
    if not any(row.get("seed") == 44 and row.get("status") in DIRECT_STATUSES for row in rows):
        rows.append(_load_phase8_seed44_as_row(phase8_procnet_root))
    return sorted(rows, key=lambda row: (int(row.get("seed") or 0), str(row.get("status") or "")))


def _load_phase8_seed44_as_row(root: Path) -> dict[str, Any]:
    export = _read_json(root / "phase8_procnet_export_summary.json")
    if export.get("seed") != 44 or export.get("split") != "dev" or export.get("test_used"):
        raise ValueError("Phase 8 ProcNet seed44 cannot be used as direct-comparable R8 row")
    analysis = _default_phase8_analysis_root(root)
    overall = _read_json(analysis / "overall_metrics.json")
    record = _read_json(analysis / "record_level_metrics.json")
    validation = _read_json(analysis / "validation_report.json")
    payload = {
        "phase": "R8 ProcNet baseline comparison",
        "baseline": "ProcNet",
        "seed": 44,
        "dataset": "DuEE-Fin-dev500",
        "split": "dev",
        "status": "direct_comparable_reused",
        "direct_comparable": True,
        "reference_only": False,
        "validation_ok": validation.get("ok") is True,
        "strict_f1": overall.get("f1"),
        "strict_precision": overall.get("precision"),
        "strict_recall": overall.get("recall"),
        "exact_record_f1": record.get("record_f1_exact"),
        "soft_record_f1_0_8": record.get("record_f1_soft_0_8"),
        "canonical_rows": export.get("canonical_rows"),
        "canonical_event_count": export.get("canonical_event_count"),
        "phase8_root": str(root),
        "procnet_training_run": False,
        "test_run": False,
        "evaluator_modified": False,
    }
    _require_direct_procnet_row(payload, root / "phase8_procnet_export_summary.json")
    return payload


def _default_phase8_analysis_root(root: Path) -> Path:
    candidates = [
        root / "evaluator/procnet_dueefin_unified_s44_dev/analysis/DuEE-Fin-dev500/dev",
        Path(
            "/data/TJK/DEE/sage-dee/evaluator_artifacts/phase8_traditional_baseline_alignment/"
            "procnet_dueefin_unified_s44_dev/procnet_dueefin_unified_s44_dev/analysis/DuEE-Fin-dev500/dev"
        ),
    ]
    for candidate in candidates:
        if (candidate / "overall_metrics.json").is_file():
            return candidate
    raise ValueError(f"missing Phase 8 seed44 evaluator metrics for {root}")


def _require_direct_procnet_row(row: dict[str, Any], path: Path) -> None:
    if row.get("dataset") != "DuEE-Fin-dev500" or row.get("split") != "dev":
        raise ValueError(f"{path}: ProcNet row is not DuEE-Fin-dev500/dev")
    if row.get("validation_ok") is not True:
        raise ValueError(f"{path}: direct-comparable ProcNet row validation is not ok")
    if row.get("test_run") or row.get("procnet_training_run") or row.get("evaluator_modified"):
        raise ValueError(f"{path}: forbidden ProcNet scope flag is true")
    _required_float(row, "strict_f1", path)
    _required_float(row, "exact_record_f1", path)


def _validate_main_rows(r7: dict[str, Any], direct: list[dict[str, Any]]) -> None:
    scope = r7.get("scope") or {}
    if scope.get("test_run") or scope.get("test_gold_read"):
        raise ValueError("R7 summary violates dev-only scope")
    for row in direct:
        if row.get("dataset") != "DuEE-Fin-dev500" or row.get("split") != "dev":
            raise ValueError("all ProcNet main rows must share dataset/split")
        if row.get("validation_ok") is not True:
            raise ValueError("all ProcNet main rows must have validation ok")


def _procnet_stats(rows: list[dict[str, Any]]) -> dict[str, Any]:
    if not rows:
        return {
            "strict_f1": {"mean": None, "std": None, "n": 0},
            "exact_record_f1": {"mean": None, "std": None, "n": 0},
        }
    return {
        "strict_f1": _metric_stats([_required_float(row, "strict_f1", Path("procnet_row")) for row in rows]),
        "exact_record_f1": _metric_stats(
            [_required_float(row, "exact_record_f1", Path("procnet_row")) for row in rows]
        ),
    }


def _metric_stats(values: list[float]) -> dict[str, Any]:
    return {
        "mean": statistics.fmean(values),
        "std": statistics.pstdev(values) if len(values) > 1 else 0.0,
        "n": len(values),
    }


def _verdict(
    *,
    procnet_seed44: dict[str, Any] | None,
    direct_count: int,
    deltas: dict[str, Any],
) -> dict[str, Any]:
    strict_delta = deltas.get("S4_mean_minus_ProcNet_seed44_strict_f1")
    exact_delta = deltas.get("S4_exact_mean_minus_ProcNet_seed44_exact_record_f1")
    thesis_ready = procnet_seed44 is not None
    if not thesis_ready:
        recommended_next_phase = "R8b_more_baselines"
    elif direct_count < 3:
        recommended_next_phase = "R8c_optional_procnet_seed_training_if_authorized"
    else:
        recommended_next_phase = "R9_external_literature_and_method_upgrade"
    return {
        "procnet_direct_comparable_available": direct_count > 0,
        "procnet_seed_count": direct_count,
        "sage_v21_beats_procnet_seed44_strict": bool(strict_delta is not None and strict_delta > 0),
        "sage_v21_beats_procnet_seed44_exact": bool(exact_delta is not None and exact_delta > 0),
        "thesis_table_ready": thesis_ready,
        "ccfa_claim_ready": False,
        "recommended_next_phase": recommended_next_phase,
    }


def _seed_row(rows: list[dict[str, Any]], seed: int) -> dict[str, Any] | None:
    for row in rows:
        if int(row.get("seed") or -1) == seed:
            return row
    return None


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise ValueError(f"missing JSON file: {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return payload


def _required_float(payload: dict[str, Any], key: str, path: Path) -> float:
    value = payload.get(key)
    if not isinstance(value, (int, float)):
        raise ValueError(f"{path}: missing numeric {key}")
    return float(value)


def _created_at() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


if __name__ == "__main__":
    raise SystemExit(main())
