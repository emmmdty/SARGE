from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "src"))

from scripts.v2.analyze_phase11_docfee_stress import (  # noqa: E402
    load_phase11_docfee_stress_analysis,
    render_phase11_docfee_stress_markdown,
)

REQUIRED_OVERALL_KEYS = (
    "event_table_micro_f1",
    "role_level_f1",
    "exact_record_f1",
    "parse_error_count",
    "parse_error_rate",
    "schema_violation_rows",
    "schema_violation_count",
)
REQUIRED_BUCKET_KEYS = (
    "bucket",
    "doc_count",
    "event_table_micro_f1",
    "parse_error_count",
    "parse_error_rate",
    "truncation_count",
    "truncation_rate",
    "missing_event_count",
    "missing_event_rate",
    "candidate_overflow_count",
    "candidate_overflow_rate",
    "surface_recall",
    "hallucinated_argument_rate",
    "non_surface_argument_rate",
)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    aggregate = aggregate_phase11(args)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(aggregate, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    out_md = args.out_md or args.out.with_suffix(".md")
    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_md.write_text(render_phase11_docfee_stress_markdown(aggregate["analysis"]), encoding="utf-8")
    print(f"aggregate_json={args.out}")
    print(f"aggregate_markdown={out_md}")
    return 0


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Aggregate Phase 11 DocFEE stress diagnostics.")
    parser.add_argument("--run-root", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--out-md", type=Path)
    return parser.parse_args(argv)


def aggregate_phase11(args: argparse.Namespace) -> dict[str, Any]:
    run_summary_path = args.run_root / "phase11_run_summary.json"
    run_summary = _read_json(run_summary_path)
    analysis = load_phase11_docfee_stress_analysis(args.run_root)
    overall = analysis.get("overall") or {}
    bucket_rows = ((analysis.get("length_bucket_diagnostics") or {}).get("length_buckets")) or []
    _require_keys(overall, REQUIRED_OVERALL_KEYS, "overall metrics")
    _require_length_buckets(bucket_rows)
    _validate_scope(run_summary=run_summary, analysis=analysis)
    aggregate = {
        "phase": "Phase 11 DocFEE stress analysis",
        "dataset": analysis.get("dataset"),
        "split": analysis.get("split"),
        "run_root": str(args.run_root),
        "run_summary_path": str(run_summary_path),
        "analysis_path": str(args.run_root / "phase11_docfee_stress_analysis.json"),
        "overall": overall,
        "length_bucket_table": bucket_rows,
        "parse_error_by_length": _bucket_metric(bucket_rows, "parse_error_count", "parse_error_rate"),
        "truncation_by_length": _bucket_metric(bucket_rows, "truncation_count", "truncation_rate"),
        "missing_event_by_length": _bucket_metric(bucket_rows, "missing_event_count", "missing_event_rate"),
        "candidate_overflow_by_length": _bucket_metric(
            bucket_rows,
            "candidate_overflow_count",
            "candidate_overflow_rate",
        ),
        "surface_recall_by_length": _bucket_value(bucket_rows, "surface_recall"),
        "hallucinated_argument_by_length": _bucket_value(bucket_rows, "hallucinated_argument_rate"),
        "non_surface_argument_by_length": _bucket_value(bucket_rows, "non_surface_argument_rate"),
        "failure_samples": analysis.get("failure_samples") or [],
        "parse_diagnostics": analysis.get("parse_diagnostics") or {},
        "truncation_diagnostics": analysis.get("truncation_diagnostics") or {},
        "surface_diagnostics": analysis.get("surface_diagnostics") or {},
        "gate": _gate(run_summary=run_summary, aggregate_overall=overall, bucket_rows=bucket_rows, analysis=analysis),
        "analysis": analysis,
    }
    if _overall_only(aggregate):
        raise SystemExit("Phase 11 aggregate rejects overall-only report; length bucket diagnostics are required")
    return aggregate


def _validate_scope(*, run_summary: dict[str, Any], analysis: dict[str, Any]) -> None:
    if analysis.get("dataset") != "DocFEE-dev1000":
        raise SystemExit("Phase 11 aggregation only permits DocFEE-dev1000")
    if analysis.get("split") == "test":
        raise SystemExit("Phase 11 aggregation rejects test split")
    if analysis.get("split") != "dev":
        raise SystemExit(f"Phase 11 aggregation only permits dev split, got {analysis.get('split')!r}")
    scope = run_summary.get("scope") or {}
    if scope.get("test_used") or scope.get("train_used") or scope.get("full_train_used"):
        raise SystemExit("Phase 11 aggregation rejects runs that used test/train/full train")
    if scope.get("no_profile_tuning") is not True:
        raise SystemExit("Phase 11 aggregation requires no profile tuning")
    if scope.get("no_prompt_parser_surface_tuning") is not True:
        raise SystemExit("Phase 11 aggregation requires no prompt/parser/surface tuning")


def _require_length_buckets(bucket_rows: Any) -> None:
    if not isinstance(bucket_rows, list) or not bucket_rows:
        raise SystemExit("Phase 11 aggregation requires length bucket diagnostics")
    for index, row in enumerate(bucket_rows):
        if not isinstance(row, dict):
            raise SystemExit(f"Phase 11 length bucket row {index} is not an object")
        _require_keys(row, REQUIRED_BUCKET_KEYS, f"length bucket row {index}")


def _require_keys(payload: dict[str, Any], keys: Sequence[str], label: str) -> None:
    missing = [key for key in keys if key not in payload]
    if missing:
        raise SystemExit(f"Phase 11 aggregation requires {label}: missing {missing}")


def _bucket_metric(bucket_rows: list[dict[str, Any]], count_key: str, rate_key: str) -> dict[str, dict[str, Any]]:
    return {
        str(row["bucket"]): {
            "doc_count": row.get("doc_count"),
            "count": row.get(count_key),
            "rate": row.get(rate_key),
        }
        for row in bucket_rows
    }


def _bucket_value(bucket_rows: list[dict[str, Any]], key: str) -> dict[str, dict[str, Any]]:
    return {
        str(row["bucket"]): {
            "doc_count": row.get("doc_count"),
            "value": row.get(key),
        }
        for row in bucket_rows
    }


def _gate(
    *,
    run_summary: dict[str, Any],
    aggregate_overall: dict[str, Any],
    bucket_rows: list[dict[str, Any]],
    analysis: dict[str, Any],
) -> dict[str, Any]:
    scope = run_summary.get("scope") or {}
    return {
        "prediction_only_completed": run_summary.get("gate", {}).get("prediction_only_completed") is True,
        "aggregate_json_completed": True,
        "length_bucket_f1_exists": all("event_table_micro_f1" in row for row in bucket_rows),
        "truncation_diagnostics_exists": bool(analysis.get("truncation_diagnostics")),
        "parse_error_by_length_exists": all("parse_error_rate" in row for row in bucket_rows),
        "missing_event_by_length_exists": all("missing_event_rate" in row for row in bucket_rows),
        "surface_recall_by_length_exists": all("surface_recall" in row for row in bucket_rows),
        "overall_event_table_micro_f1_exists": "event_table_micro_f1" in aggregate_overall,
        "test_used": bool(scope.get("test_used")),
        "train_used": bool(scope.get("train_used")),
        "full_train_used": bool(scope.get("full_train_used")),
        "no_profile_tuning": scope.get("no_profile_tuning") is True,
        "no_prompt_parser_surface_tuning": scope.get("no_prompt_parser_surface_tuning") is True,
        "no_long_document_sota_claim": True,
    }


def _overall_only(aggregate: dict[str, Any]) -> bool:
    return not aggregate.get("length_bucket_table")


def _read_json(path: str | Path) -> dict[str, Any]:
    with Path(path).open(encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object: {path}")
    return payload


if __name__ == "__main__":
    raise SystemExit(main())
