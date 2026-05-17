from __future__ import annotations

import argparse
import json
import statistics
import sys
from collections.abc import Sequence
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SEEDS = (42, 43, 44)
R3_ROW_D = "s4_full_or_max_frozen_surface"


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        aggregate = aggregate_r6(args.run_root, seed42_root=args.seed42_root)
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
    print(f"recommended_next_phase={aggregate['recommended_next_phase']}")
    return 0


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Aggregate SAGE v2.1 R6 seed extension full/max S4 results.")
    parser.add_argument("--run-root", type=Path, required=True)
    parser.add_argument("--seed42-root", type=Path, required=True)
    parser.add_argument("--out-json", type=Path, required=True)
    parser.add_argument("--out-md", type=Path, required=True)
    return parser.parse_args(argv)


def aggregate_r6(run_root: Path, *, seed42_root: Path) -> dict[str, Any]:
    seed_summaries = {
        42: _load_seed42(seed42_root),
        43: _load_r6_seed(run_root, 43),
        44: _load_r6_seed(run_root, 44),
    }
    _validate_scope(seed_summaries)

    per_seed = {str(seed): _public_seed_summary(summary) for seed, summary in seed_summaries.items()}
    event_values = [_required_number(seed_summaries[seed], "event_table_micro_f1") for seed in SEEDS]
    exact_values = [_required_number(seed_summaries[seed], "exact_record_f1") for seed in SEEDS]
    metrics = {
        "mean_event_role_f1": statistics.fmean(event_values),
        "std_event_role_f1": _pstdev(event_values),
        "mean_exact_record_f1": statistics.fmean(exact_values),
        "std_exact_record_f1": _pstdev(exact_values),
    }
    decision = _decision(metrics)
    return {
        "phase": "R6 seed extension full/max S4",
        "run_root": str(run_root),
        "seed42_root": str(seed42_root),
        "seed_count": len(SEEDS),
        "seeds": per_seed,
        "metrics": metrics,
        "stability_verdict": decision["stability_verdict"],
        "recommended_next_phase": decision["recommended_next_phase"],
        "v2_1_thesis_potential": decision["v2_1_thesis_potential"],
        "high_variance": decision["high_variance"],
        "scope": {
            "dev_only": True,
            "s4_only": True,
            "test_run": False,
            "test_gold_read": False,
            "seed42_retrained": False,
            "v21_surface_run": False,
            "r4b_planner_run": False,
            "chfinann_run": False,
            "docfee_run": False,
            "frozen_final_modified": False,
        },
        "created_at": _created_at(),
    }


def render_markdown(aggregate: dict[str, Any]) -> str:
    seeds = aggregate["seeds"]
    metrics = aggregate["metrics"]
    lines = [
        "# SAGE v2.1 R6 Seed Extension Full/Max S4 Summary",
        "",
        "R6 is dev-only and reuses seed42 from R3 Row D. It adds only seed43 and seed44.",
        "",
        "| Seed | Source | Event/role F1 | Exact-record F1 | Parse error | Unknown role | "
        "Unknown event type | Canonical rows | Canonical events |",
        "| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for seed in ("42", "43", "44"):
        row = seeds[seed]
        lines.append(
            "| {seed} | {source} | {event:.6f} | {exact:.6f} | {parse_error} | {unknown_role} | "
            "{unknown_event_type} | {canonical_rows} | {canonical_event_count} |".format(
                seed=seed,
                source=row["source"],
                event=float(row["event_table_micro_f1"]),
                exact=float(row["exact_record_f1"]),
                parse_error=row.get("parse_error"),
                unknown_role=row.get("unknown_role"),
                unknown_event_type=row.get("unknown_event_type"),
                canonical_rows=row.get("canonical_rows"),
                canonical_event_count=row.get("canonical_event_count"),
            )
        )
    lines.extend(
        [
            "",
            "| Metric | Value |",
            "| --- | ---: |",
            f"| mean_event_role_f1 | {metrics['mean_event_role_f1']:.6f} |",
            f"| std_event_role_f1 | {metrics['std_event_role_f1']:.6f} |",
            f"| mean_exact_record_f1 | {metrics['mean_exact_record_f1']:.6f} |",
            f"| std_exact_record_f1 | {metrics['std_exact_record_f1']:.6f} |",
            "",
            f"stability_verdict: `{aggregate['stability_verdict']}`",
            f"recommended_next_phase: `{aggregate['recommended_next_phase']}`",
            "",
        ]
    )
    return "\n".join(lines)


def _load_seed42(seed42_root: Path) -> dict[str, Any]:
    path = seed42_root / R3_ROW_D / "row_summary.json"
    if not path.is_file():
        raise ValueError(f"missing R3 seed42 Row D summary: {path}")
    payload = _read_json(path)
    payload["source"] = "R3 Row D reused evidence"
    return payload


def _load_r6_seed(run_root: Path, seed: int) -> dict[str, Any]:
    path = run_root / f"seed{seed}" / "seed_summary.json"
    if not path.is_file():
        raise ValueError(f"missing R6 seed{seed} summary: {path}")
    payload = _read_json(path)
    payload["source"] = f"R6 seed{seed}"
    return payload


def _validate_scope(seed_summaries: dict[int, dict[str, Any]]) -> None:
    for seed, summary in seed_summaries.items():
        if int(summary.get("seed") or -1) != seed:
            raise ValueError(f"seed summary mismatch for seed{seed}")
        if summary.get("dataset") != "DuEE-Fin-dev500":
            raise ValueError(f"R6 only permits DuEE-Fin-dev500, got seed{seed}")
        if summary.get("split") != "dev":
            raise ValueError(f"R6 only permits dev split, got seed{seed}")
        if summary.get("system") != "S4":
            raise ValueError(f"R6 only permits S4, got seed{seed}")
        if summary.get("surface") != "frozen_compressed_phase6_final_profile":
            raise ValueError(f"R6 only permits frozen compressed surface, got seed{seed}")
        for key in ("test_run", "test_gold_read", "v21_surface_run", "r4b_planner_run", "frozen_final_modified"):
            if summary.get(key):
                raise ValueError(f"forbidden R6 scope flag {key}=true for seed{seed}")
    if seed_summaries[42].get("train_run") is not True:
        raise ValueError("R3 seed42 Row D evidence must be a completed training row")
    if seed_summaries[42].get("evaluator_validation_ok") is not True:
        raise ValueError("R3 seed42 Row D evaluator validation must be ok")
    for seed in (43, 44):
        if seed_summaries[seed].get("seed42_retrained"):
            raise ValueError(f"R6 seed{seed} summary indicates seed42 retrain")


def _public_seed_summary(summary: dict[str, Any]) -> dict[str, Any]:
    keys = (
        "source",
        "seed",
        "dataset",
        "split",
        "system",
        "surface",
        "train_limit",
        "train_examples_seen",
        "event_table_micro_f1",
        "role_level_f1",
        "exact_record_f1",
        "parse_error",
        "schema_violation_rows",
        "unknown_role",
        "unknown_event_type",
        "canonical_rows",
        "canonical_event_count",
        "accepted_event_count",
        "wallclock",
        "peak_vram",
        "adapter_path",
        "evaluator_artifact_path",
        "training_manifest_path",
        "generation_manifest_path",
    )
    return {key: summary.get(key) for key in keys}


def _decision(metrics: dict[str, float]) -> dict[str, Any]:
    mean_event = metrics["mean_event_role_f1"]
    mean_exact = metrics["mean_exact_record_f1"]
    std_event = metrics["std_event_role_f1"]
    std_exact = metrics["std_exact_record_f1"]
    high_variance = std_event > 0.05 or std_exact > 0.05
    if mean_event >= 0.70 and mean_exact >= 0.30:
        recommended = "R7_thesis_package_minimal_matrix"
        potential = True
        verdict = "stable_promising"
    elif mean_event < 0.65 or mean_exact < 0.25:
        recommended = "stop_v2_1_move_v3"
        potential = False
        verdict = "unstable_or_weak"
    elif high_variance:
        recommended = "R6b_train_stability_audit"
        potential = False
        verdict = "high_variance"
    else:
        recommended = "R7_thesis_package_with_limitations"
        potential = True
        verdict = "stable_with_limitations"
    return {
        "recommended_next_phase": recommended,
        "v2_1_thesis_potential": potential,
        "high_variance": high_variance,
        "stability_verdict": verdict,
    }


def _pstdev(values: list[float]) -> float:
    return statistics.pstdev(values) if len(values) > 1 else 0.0


def _required_number(summary: dict[str, Any], key: str) -> float:
    value = summary.get(key)
    if isinstance(value, bool) or value is None:
        raise ValueError(f"missing numeric metric {key} for seed{summary.get('seed')}")
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"invalid numeric metric {key} for seed{summary.get('seed')}: {value!r}") from exc


def _read_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object: {path}")
    return payload


def _created_at() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


if __name__ == "__main__":
    raise SystemExit(main())
