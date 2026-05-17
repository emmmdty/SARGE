from __future__ import annotations

import argparse
import json
import statistics
import sys
from collections.abc import Sequence
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SYSTEMS = ("S2", "S3", "S4")
SEEDS = (42, 43, 44)
METRIC_KEYS = (
    "event_table_micro_f1",
    "role_level_f1",
    "exact_record_f1",
    "parse_error",
    "schema_violation_rows",
    "unknown_role",
    "unknown_event_type",
    "canonical_event_count",
)
R3_ROW_D = "s4_full_or_max_frozen_surface"


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        aggregate = aggregate_r7(
            args.run_root,
            r6_s4_root=args.r6_s4_root,
            r3_s4_seed42_root=args.r3_s4_seed42_root,
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
    print(f"recommended_next_phase={aggregate['verdict']['recommended_next_phase']}")
    return 0


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Aggregate SAGE v2.1 R7 thesis minimal matrix results.")
    parser.add_argument("--run-root", type=Path, required=True)
    parser.add_argument("--r6-s4-root", type=Path, required=True)
    parser.add_argument("--r3-s4-seed42-root", type=Path, required=True)
    parser.add_argument("--out-json", type=Path, required=True)
    parser.add_argument("--out-md", type=Path, required=True)
    return parser.parse_args(argv)


def aggregate_r7(run_root: Path, *, r6_s4_root: Path, r3_s4_seed42_root: Path) -> dict[str, Any]:
    rows = _load_all_rows(run_root, r6_s4_root=r6_s4_root, r3_s4_seed42_root=r3_s4_seed42_root)
    _validate_scope(rows)
    system_stats = {system: _system_stats(rows[system]) for system in SYSTEMS}
    deltas = {
        "S3_minus_S2": _delta(system_stats["S3"], system_stats["S2"]),
        "S4_minus_S3": _delta(system_stats["S4"], system_stats["S3"]),
        "S4_minus_S2": _delta(system_stats["S4"], system_stats["S2"]),
    }
    verdict = _verdict(system_stats, deltas)
    return {
        "phase": "R7 thesis minimal matrix",
        "run_root": str(run_root),
        "r6_s4_root": str(r6_s4_root),
        "r3_s4_seed42_root": str(r3_s4_seed42_root),
        "systems": {system: [_public_row(row) for row in rows[system]] for system in SYSTEMS},
        "system_stats": system_stats,
        "deltas": deltas,
        "verdict": verdict,
        "scope": {
            "dev_only": True,
            "systems_compared": list(SYSTEMS),
            "seeds": list(SEEDS),
            "test_run": False,
            "test_gold_read": False,
            "s1_run": False,
            "s4_retrained": False,
            "v21_surface_run": False,
            "r4b_planner_run": False,
            "chfinann_run": False,
            "docfee_run": False,
            "frozen_final_modified": False,
        },
        "created_at": _created_at(),
    }


def render_markdown(aggregate: dict[str, Any]) -> str:
    lines = [
        "# SAGE v2.1 R7 Thesis Minimal Matrix Summary",
        "",
        "R7 is dev-only. S2/S3 are full/max R7 rows; S4 is reused read-only from R6/R3.",
        "",
        "| System | Seed | Source | Event/role F1 | Role F1 | Exact-record F1 | Parse error | "
        "Schema violation rows | Unknown role | Unknown event type | Canonical events |",
        "| --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for system in SYSTEMS:
        for row in aggregate["systems"][system]:
            lines.append(
                "| {system} | {seed} | {source} | {event:.6f} | {role:.6f} | {exact:.6f} | "
                "{parse_error} | {schema_violation_rows} | {unknown_role} | {unknown_event_type} | "
                "{canonical_event_count} |".format(
                    system=system,
                    seed=row["seed"],
                    source=row["source"],
                    event=float(row["event_table_micro_f1"]),
                    role=float(row["role_level_f1"]),
                    exact=float(row["exact_record_f1"]),
                    parse_error=row.get("parse_error"),
                    schema_violation_rows=row.get("schema_violation_rows"),
                    unknown_role=row.get("unknown_role"),
                    unknown_event_type=row.get("unknown_event_type"),
                    canonical_event_count=row.get("canonical_event_count"),
                )
            )
    lines.extend(["", "| System | Metric | Mean | Std |", "| --- | --- | ---: | ---: |"])
    for system, stats in aggregate["system_stats"].items():
        for metric in ("event_table_micro_f1", "exact_record_f1", "parse_error", "canonical_event_count"):
            value = stats[metric]
            lines.append(f"| {system} | {metric} | {value['mean']:.6f} | {value['std']:.6f} |")
    lines.extend(["", "| Delta | Event/role F1 | Exact-record F1 |", "| --- | ---: | ---: |"])
    for name, delta in aggregate["deltas"].items():
        lines.append(
            f"| {name} | {delta['event_table_micro_f1']:.6f} | {delta['exact_record_f1']:.6f} |"
        )
    verdict = aggregate["verdict"]
    lines.extend(
        [
            "",
            f"role_safe_effective: `{verdict['role_safe_effective']}`",
            f"surface_memory_effective: `{verdict['surface_memory_effective']}`",
            f"thesis_experiment_viable: `{verdict['thesis_experiment_viable']}`",
            f"thesis_experiment_viability_verdict: `{verdict['thesis_experiment_viability_verdict']}`",
            f"recommended_next_phase: `{verdict['recommended_next_phase']}`",
            "",
        ]
    )
    return "\n".join(lines)


def _load_all_rows(
    run_root: Path,
    *,
    r6_s4_root: Path,
    r3_s4_seed42_root: Path,
) -> dict[str, list[dict[str, Any]]]:
    return {
        "S2": [_load_r7_row(run_root, "S2", seed) for seed in SEEDS],
        "S3": [_load_r7_row(run_root, "S3", seed) for seed in SEEDS],
        "S4": [
            _load_s4_seed42(r3_s4_seed42_root),
            _load_s4_r6_seed(r6_s4_root, 43),
            _load_s4_r6_seed(r6_s4_root, 44),
        ],
    }


def _load_r7_row(run_root: Path, system: str, seed: int) -> dict[str, Any]:
    path = run_root / f"{system}_seed{seed}" / "row_summary.json"
    if not path.is_file():
        raise ValueError(f"missing R7 {system} seed{seed} summary: {path}")
    payload = _read_json(path)
    payload["source"] = f"R7 {system} seed{seed}"
    return payload


def _load_s4_seed42(root: Path) -> dict[str, Any]:
    path = root / R3_ROW_D / "row_summary.json"
    if not path.is_file():
        raise ValueError(f"missing S4 seed42 R3 Row D summary: {path}")
    payload = _read_json(path)
    payload["source"] = "R3 Row D reused evidence"
    payload["system"] = "S4"
    payload["s4_retrained"] = False
    return payload


def _load_s4_r6_seed(root: Path, seed: int) -> dict[str, Any]:
    path = root / f"seed{seed}" / "seed_summary.json"
    if not path.is_file():
        raise ValueError(f"missing S4 seed{seed} R6 summary: {path}")
    payload = _read_json(path)
    payload["source"] = f"R6 S4 seed{seed}"
    payload["system"] = "S4"
    payload["s4_retrained"] = False
    return payload


def _validate_scope(rows: dict[str, list[dict[str, Any]]]) -> None:
    for system in SYSTEMS:
        if len(rows.get(system) or []) != len(SEEDS):
            raise ValueError(f"R7 requires {system} seeds 42/43/44")
        seen = {int(row.get("seed") or -1) for row in rows[system]}
        if seen != set(SEEDS):
            raise ValueError(f"R7 requires {system} seeds 42/43/44, got {sorted(seen)}")
    for system, system_rows in rows.items():
        for row in system_rows:
            seed = row.get("seed")
            if row.get("dataset") != "DuEE-Fin-dev500":
                raise ValueError(f"{system} seed{seed} is not DuEE-Fin-dev500")
            if row.get("split") != "dev":
                raise ValueError(f"{system} seed{seed} is not dev split")
            if row.get("system") != system:
                raise ValueError(f"{system} seed{seed} system mismatch")
            for key in (
                "test_run",
                "test_gold_read",
                "v21_surface_run",
                "r4b_planner_run",
                "frozen_final_modified",
            ):
                if row.get(key):
                    raise ValueError(f"forbidden R7 scope flag {key}=true for {system} seed{seed}")
            if system in {"S2", "S3"}:
                if row.get("surface") != "none":
                    raise ValueError(f"{system} seed{seed} must have surface none")
                if row.get("evaluator_validation_ok") is not True:
                    raise ValueError(f"{system} seed{seed} evaluator validation must be ok")
            if system == "S4" and row.get("s4_retrained"):
                raise ValueError(f"S4 seed{seed} must be reused, not retrained")


def _system_stats(rows: list[dict[str, Any]]) -> dict[str, Any]:
    stats: dict[str, Any] = {"seed_count": len(rows), "seeds": [row.get("seed") for row in rows]}
    for key in METRIC_KEYS:
        values = [_required_number(row, key) for row in rows]
        stats[key] = {
            "mean": statistics.fmean(values),
            "std": statistics.pstdev(values) if len(values) > 1 else 0.0,
            "n": len(values),
        }
    return stats


def _delta(numerator: dict[str, Any], denominator: dict[str, Any]) -> dict[str, float]:
    return {
        key: float(numerator[key]["mean"]) - float(denominator[key]["mean"])
        for key in ("event_table_micro_f1", "role_level_f1", "exact_record_f1")
    }


def _verdict(system_stats: dict[str, Any], deltas: dict[str, dict[str, float]]) -> dict[str, Any]:
    role_delta = deltas["S3_minus_S2"]
    surface_delta = deltas["S4_minus_S3"]
    role_safe_effective = role_delta["event_table_micro_f1"] >= 0.03 or role_delta["exact_record_f1"] >= 0.02
    surface_memory_effective = (
        surface_delta["event_table_micro_f1"] >= 0.02 or surface_delta["exact_record_f1"] >= 0.01
    )
    s4_event = float(system_stats["S4"]["event_table_micro_f1"]["mean"])
    s4_exact = float(system_stats["S4"]["exact_record_f1"]["mean"])
    s4_stable = s4_event >= 0.70 and s4_exact >= 0.30
    viable = bool(s4_stable and (role_safe_effective or surface_memory_effective))
    if viable:
        viability = "viable"
        recommended = "R8_procnet_and_thesis_tables"
    elif s4_stable:
        viability = "weak_empirical_study_only"
        recommended = "R8_optional_s1_appendix"
    else:
        viability = "not_viable"
        recommended = "stop_v2_1_move_v3"
    return {
        "role_safe_effective": bool(role_safe_effective),
        "surface_memory_effective": bool(surface_memory_effective),
        "thesis_experiment_viable": viable,
        "thesis_experiment_viability_verdict": viability,
        "recommended_next_phase": recommended,
    }


def _public_row(row: dict[str, Any]) -> dict[str, Any]:
    keys = (
        "source",
        "system",
        "seed",
        "dataset",
        "split",
        "surface",
        "baseline_mode",
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
    return {key: row.get(key) for key in keys}


def _required_number(row: dict[str, Any], key: str) -> float:
    value = row.get(key)
    if key == "role_level_f1" and value is None:
        value = row.get("event_table_micro_f1")
    if isinstance(value, bool) or value is None:
        raise ValueError(f"missing numeric metric {key} for {row.get('system')} seed{row.get('seed')}")
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(
            f"invalid numeric metric {key} for {row.get('system')} seed{row.get('seed')}: {value!r}"
        ) from exc


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
