from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))

from sage_dee.v2.data_interface.jsonl import read_jsonl  # noqa: E402
from sage_dee.v2.getm.parser_ablation import PARSER_ABLATION_MODES  # noqa: E402


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    _enforce_dev_only(args)
    summary = aggregate(args.run_root, dataset=args.dataset, split=args.split)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"summary={args.out}")
    return 0


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Aggregate SAGE v2.1 R1 parser reparse ablation.")
    parser.add_argument("--run-root", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--dataset", default="DuEE-Fin-dev500")
    parser.add_argument("--split", default="dev")
    return parser.parse_args(argv)


def aggregate(run_root: Path, *, dataset: str, split: str) -> dict[str, Any]:
    rows = [_mode_row(run_root / mode, mode=mode, dataset=dataset, split=split) for mode in PARSER_ABLATION_MODES]
    return {
        "phase": "R1 parser/canonical dev reparse ablation",
        "dataset": dataset,
        "split": split,
        "run_root": str(run_root),
        "modes": rows,
        "decision": _decision(rows),
        "scope": {
            "dev_only": True,
            "qwen_run": False,
            "train_run": False,
            "test_run": False,
            "test_gold_read": False,
        },
    }


def _mode_row(run_dir: Path, *, mode: str, dataset: str, split: str) -> dict[str, Any]:
    diagnostics_path = run_dir / f"parse_diagnostics.{split}.json"
    prediction_path = run_dir / "predictions" / dataset / f"{split}.canonical.pred.jsonl"
    manifest_path = run_dir / "run_manifest.json"
    diagnostics = _read_json(diagnostics_path)
    diagnostic_counts = diagnostics.get("diagnostic_counts") if isinstance(diagnostics, dict) else {}
    if not isinstance(diagnostic_counts, dict):
        diagnostic_counts = {}
    row = {
        "mode": mode,
        "run_dir": str(run_dir),
        "manifest_path": str(manifest_path) if manifest_path.is_file() else None,
        "canonical_prediction_path": str(prediction_path) if prediction_path.is_file() else None,
        "parse_diagnostics_path": str(diagnostics_path) if diagnostics_path.is_file() else None,
        "canonical_rows": _canonical_rows(prediction_path),
        "raw_event_count": _int_count(diagnostic_counts, "raw_event_count"),
        "accepted_event_count": _int_count(diagnostic_counts, "accepted_event_count"),
        "unknown_role_count": _int_count(diagnostic_counts, "unknown_role_count"),
        "unknown_event_type_count": _int_count(diagnostic_counts, "unknown_event_type_count"),
        "dropped_event_count": _int_count(diagnostic_counts, "dropped_event_count"),
        "dropped_role_count": _int_count(diagnostic_counts, "dropped_role_count"),
        "schema_violation_rows": _parse_status_rows(diagnostics, "schema_violation"),
        "parse_error": _parse_status_rows(diagnostics, "parse_error"),
    }
    row.update(_evaluator_metrics(run_dir, dataset=dataset, split=split))
    return row


def _canonical_rows(path: Path) -> int | None:
    if not path.is_file():
        return None
    return len(read_jsonl(path))


def _parse_status_rows(diagnostics: dict[str, Any], status: str) -> int | None:
    counts = diagnostics.get("parse_status_counts") if isinstance(diagnostics, dict) else {}
    if not isinstance(counts, dict):
        return None
    value = counts.get(status)
    return int(value) if isinstance(value, int) else 0


def _int_count(counts: dict[str, Any], key: str) -> int | None:
    value = counts.get(key)
    if value is None:
        return None
    return int(value)


def _evaluator_metrics(run_dir: Path, *, dataset: str, split: str) -> dict[str, Any]:
    candidates = _evaluator_root_candidates(run_dir, dataset=dataset, split=split)
    for root in candidates:
        overall = root / "metrics" / "unified_main" / dataset / split / "overall_metrics.json"
        record = root / "analysis" / dataset / split / "record_level_metrics.json"
        validation = root / "analysis" / dataset / split / "validation_report.json"
        if overall.is_file() or record.is_file() or validation.is_file():
            overall_payload = _read_json(overall)
            record_payload = _read_json(record)
            validation_payload = _read_json(validation)
            return {
                "evaluator_status": "present",
                "evaluator_artifact_root": str(root),
                "evaluator_validation_ok": validation_payload.get("ok"),
                "event_table_micro_f1": _optional_float(overall_payload.get("f1")),
                "role_level_f1": _optional_float(overall_payload.get("f1")),
                "exact_record_f1": _optional_float(record_payload.get("record_f1_exact")),
            }
    return {
        "evaluator_status": "missing",
        "evaluator_artifact_root": None,
        "evaluator_validation_ok": None,
        "event_table_micro_f1": None,
        "role_level_f1": None,
        "exact_record_f1": None,
    }


def _evaluator_root_candidates(run_dir: Path, *, dataset: str, split: str) -> list[Path]:
    bases = [
        run_dir / "evaluator_artifacts",
        run_dir / "eval",
        run_dir / "evaluator",
        Path("/data/TJK/DEE/sage-dee/evaluator_artifacts")
        / run_dir.name
        / dataset
        / split,
        Path("/data/TJK/DEE/sage-dee/evaluator_artifacts")
        / run_dir.parent.name
        / run_dir.name
        / dataset
        / split,
    ]
    candidates: list[Path] = []
    for base in bases:
        candidates.append(base)
        if base.is_dir():
            candidates.extend(path for path in sorted(base.iterdir(), reverse=True) if path.is_dir())
    return candidates


def _decision(rows: list[dict[str, Any]]) -> dict[str, Any]:
    strict = next((row for row in rows if row["mode"] == "frozen_strict"), None)
    if strict is None:
        return {"status": "missing_frozen_strict", "parser_strictness": "unknown"}
    if strict.get("event_table_micro_f1") is None or strict.get("exact_record_f1") is None:
        return {
            "parser_strictness": "evaluator_metrics_missing",
            "comparisons": [],
            "reason": "frozen_strict evaluator metrics are unavailable",
        }
    comparisons: list[dict[str, Any]] = []
    meaningful = False
    all_small = True
    for row in rows:
        if row["mode"] == "frozen_strict":
            continue
        event_delta = _delta(row.get("event_table_micro_f1"), strict.get("event_table_micro_f1"))
        exact_delta = _delta(row.get("exact_record_f1"), strict.get("exact_record_f1"))
        comparisons.append(
            {
                "mode": row["mode"],
                "event_table_micro_f1_delta": event_delta,
                "exact_record_f1_delta": exact_delta,
            }
        )
        if (event_delta is not None and event_delta >= 0.02) or (exact_delta is not None and exact_delta >= 0.01):
            meaningful = True
        if event_delta is None and exact_delta is None:
            return {
                "parser_strictness": "evaluator_metrics_missing",
                "comparisons": comparisons,
                "reason": f"{row['mode']} evaluator metrics are unavailable",
            }
        if (event_delta is not None and event_delta >= 0.01) or (exact_delta is not None and exact_delta >= 0.01):
            all_small = False
    if meaningful:
        parser_strictness = "engineering_bug_likely"
    elif all_small:
        parser_strictness = "not_main_cause"
    else:
        parser_strictness = "minor_contributor"
    return {
        "parser_strictness": parser_strictness,
        "comparisons": comparisons,
        "thresholds": {
            "meaningful_event_or_role_f1_delta": 0.02,
            "meaningful_exact_record_f1_delta": 0.01,
            "not_main_cause_delta_lt": 0.01,
        },
    }


def _delta(value: Any, baseline: Any) -> float | None:
    left = _optional_float(value)
    right = _optional_float(baseline)
    if left is None or right is None:
        return None
    return left - right


def _optional_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    with path.open(encoding="utf-8") as handle:
        payload = json.load(handle)
    return payload if isinstance(payload, dict) else {}


def _enforce_dev_only(args: argparse.Namespace) -> None:
    if args.split != "dev":
        raise SystemExit("R1 parser reparse aggregation is dev split only")
    if args.dataset != "DuEE-Fin-dev500":
        raise SystemExit("R1 parser reparse aggregation is restricted to DuEE-Fin-dev500/dev")
    for label, path in (("run-root", args.run_root), ("out", args.out)):
        if _path_mentions_test_split(path):
            raise SystemExit(f"R1 rejects {label} path containing test: {path}")


def _path_mentions_test_split(path: Path) -> bool:
    for part in path.parts:
        lowered = part.lower()
        if lowered == "test" or "-test" in lowered or ".test" in lowered or "test." in lowered:
            return True
    return False


if __name__ == "__main__":
    raise SystemExit(main())
