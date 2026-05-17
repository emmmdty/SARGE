from __future__ import annotations

import argparse
import json
from collections.abc import Sequence
from pathlib import Path
from typing import Any

BASELINE_ROW_ID = "baseline_512_existing"
PRIMARY_ROW_ID = "s4_2k_frozen_surface"
ROW_C_ID = "s4_2k_v21_surface_secondary"
EVENT_ROLE_TRIGGER_DELTA = 0.05
EXACT_TRIGGER_DELTA = 0.01


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        aggregate = aggregate_r3(args.run_root)
    except ValueError as exc:
        print(str(exc), file=__import__("sys").stderr)
        return 2
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(
        json.dumps(aggregate, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"aggregate_json={args.out_json}")
    print(f"row_d_triggered={aggregate['row_d_triggered']}")
    return 0


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Aggregate SAGE v2.1 R3 S4 train-size scaling rows.")
    parser.add_argument("--run-root", type=Path, required=True)
    parser.add_argument("--out-json", type=Path, required=True)
    return parser.parse_args(argv)


def aggregate_r3(run_root: Path) -> dict[str, Any]:
    rows = _load_rows(run_root)
    if BASELINE_ROW_ID not in rows:
        raise ValueError("R3 aggregate requires baseline_512_existing row")
    baseline = rows[BASELINE_ROW_ID]
    enriched = {
        row_id: _enriched_row(row, baseline=baseline)
        for row_id, row in rows.items()
    }
    primary = enriched.get(PRIMARY_ROW_ID)
    row_d_trigger = bool(primary and _row_d_triggered(enriched[BASELINE_ROW_ID], primary))
    return {
        "phase": "R3 S4 train-size scaling",
        "run_root": str(run_root),
        "baseline_row_id": BASELINE_ROW_ID,
        "primary_row_id": PRIMARY_ROW_ID,
        "row_count": len(enriched),
        "rows": enriched,
        "row_d_triggered": row_d_trigger,
        "undertraining_verdict": _undertraining_verdict(enriched[BASELINE_ROW_ID], primary),
        "surface_v21_verdict": _surface_v21_verdict(primary, enriched.get(ROW_C_ID)),
        "next_phase_decision": "R3b full train only if triggered" if row_d_trigger else "R4 event grouping probe",
        "scope": {
            "dev_only": True,
            "seed42_only": True,
            "s4_only": True,
            "test_run": False,
            "seed43_44_run": False,
            "frozen_final_modified": False,
        },
    }


def _load_rows(run_root: Path) -> dict[str, dict[str, Any]]:
    rows: dict[str, dict[str, Any]] = {}
    for path in sorted(run_root.glob("*/row_summary.json")):
        with path.open(encoding="utf-8") as handle:
            payload = json.load(handle)
        if isinstance(payload, dict):
            row_id = str(payload.get("row_id") or path.parent.name)
            rows[row_id] = payload
    if not rows:
        raise ValueError(f"no R3 row_summary.json files found under {run_root}")
    return rows


def _enriched_row(row: dict[str, Any], *, baseline: dict[str, Any]) -> dict[str, Any]:
    event = _number(row.get("event_table_micro_f1"))
    exact = _number(row.get("exact_record_f1"))
    baseline_event = _number(baseline.get("event_table_micro_f1"))
    baseline_exact = _number(baseline.get("exact_record_f1"))
    payload = {
        key: row.get(key)
        for key in (
            "row_id",
            "system",
            "seed",
            "split",
            "surface",
            "action",
            "secondary",
            "conditional",
            "train_limit",
            "train_examples_seen",
            "num_train_epochs",
            "train_loss_final",
            "train_loss_mean",
            "peak_vram",
            "wallclock",
            "adapter_path",
            "evaluator_artifact_path",
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
            "row_manifest_path",
            "training_manifest_path",
            "generation_manifest_path",
        )
    }
    payload["event_table_micro_f1_delta_vs_baseline"] = _delta(event, baseline_event)
    payload["role_level_f1_delta_vs_baseline"] = _delta(
        _number(row.get("role_level_f1")),
        _number(baseline.get("role_level_f1")),
    )
    payload["exact_record_f1_delta_vs_baseline"] = _delta(exact, baseline_exact)
    return payload


def _row_d_triggered(baseline: dict[str, Any], primary: dict[str, Any]) -> bool:
    event_delta = _number(primary.get("event_table_micro_f1_delta_vs_baseline"))
    exact_delta = _number(primary.get("exact_record_f1_delta_vs_baseline"))
    return bool(
        (event_delta is not None and event_delta >= EVENT_ROLE_TRIGGER_DELTA)
        or (exact_delta is not None and exact_delta >= EXACT_TRIGGER_DELTA)
    )


def _undertraining_verdict(baseline: dict[str, Any], primary: dict[str, Any] | None) -> str:
    if primary is None:
        return "low"
    event_delta = _delta(_number(primary.get("event_table_micro_f1")), _number(baseline.get("event_table_micro_f1")))
    exact_delta = _delta(_number(primary.get("exact_record_f1")), _number(baseline.get("exact_record_f1")))
    if (event_delta is not None and event_delta >= EVENT_ROLE_TRIGGER_DELTA) or (
        exact_delta is not None and exact_delta >= EXACT_TRIGGER_DELTA
    ):
        return "high"
    if (event_delta is not None and event_delta >= 0.02) or (exact_delta is not None and exact_delta >= 0.005):
        return "medium"
    return "low"


def _surface_v21_verdict(primary: dict[str, Any] | None, row_c: dict[str, Any] | None) -> str:
    if row_c is None:
        return "not_run"
    if primary is None:
        return "secondary_not_promising"
    event_delta = _delta(_number(row_c.get("event_table_micro_f1")), _number(primary.get("event_table_micro_f1")))
    exact_delta = _delta(_number(row_c.get("exact_record_f1")), _number(primary.get("exact_record_f1")))
    if event_delta is not None and event_delta >= 0.02:
        return "needs_R2b_compression"
    if exact_delta is not None and exact_delta >= 0.005:
        return "secondary_promising"
    return "secondary_not_promising"


def _delta(value: float | None, baseline: float | None) -> float | None:
    if value is None or baseline is None:
        return None
    return value - baseline


def _number(value: Any) -> float | None:
    if isinstance(value, bool) or value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


if __name__ == "__main__":
    raise SystemExit(main())
