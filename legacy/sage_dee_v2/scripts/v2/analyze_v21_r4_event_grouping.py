from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter
from collections.abc import Iterable, Sequence
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROW_D_ID = "s4_full_or_max_frozen_surface"
PROGRESSION_ROW_IDS = (
    "baseline_512_existing",
    "s4_2k_frozen_surface",
    ROW_D_ID,
)
EXPECTED_DATASET = "DuEE-Fin-dev500"
EXPECTED_SPLIT = "dev"
EXPECTED_ROW_D_EVENT_F1 = 0.737327
EXPECTED_ROW_D_EXACT_F1 = 0.352248
GROUPING_HIGH_GAP = 0.25
GROUPING_MEDIUM_GAP = 0.10


def main(argv: Sequence[str] | None = None) -> int:
    try:
        args = parse_args(argv)
        analysis = analyze_r4(args)
    except (OSError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2

    args.out_dir.mkdir(parents=True, exist_ok=True)
    analysis_path = args.out_dir / "r4_event_grouping_analysis.json"
    manifest_path = args.out_dir / "run_manifest.json"
    _write_json(analysis_path, analysis)
    _write_json(manifest_path, _run_manifest(args=args, analysis=analysis, analysis_path=analysis_path))
    print(f"analysis_json={analysis_path}")
    print(f"run_manifest={manifest_path}")
    return 0


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="SAGE v2.1 R4 event planning/grouping dev-only probe.")
    parser.add_argument("--run-root", type=Path, required=True)
    parser.add_argument("--row-id", required=True)
    parser.add_argument("--dataset", required=True)
    parser.add_argument("--split", required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--r2-coverage-json", type=Path)
    return parser.parse_args(argv)


def analyze_r4(args: argparse.Namespace) -> dict[str, Any]:
    _validate_args(args)
    aggregate = _read_r3_aggregate(args.run_root)
    rows = _load_r3_rows(args.run_root, aggregate)
    _validate_r3_gate(args, aggregate, rows)

    primary = rows[args.row_id]
    artifact_root = _discover_evaluator_artifact(args.run_root, args.row_id, primary)
    analysis_dir = artifact_root / "analysis" / args.dataset / args.split
    if not analysis_dir.is_dir():
        raise ValueError(f"missing dev evaluator artifact analysis directory: {analysis_dir}")

    input_paths = _read_json(analysis_dir / "input_paths.json")
    prediction_path = _existing_path(
        primary.get("prediction_path"),
        input_paths.get("prediction_path"),
        _canonical_path_from_generation_manifest(primary.get("generation_manifest_path")),
    )
    gold_path = _existing_path(input_paths.get("gold_path"))
    parse_path = _existing_path(primary.get("parse_diagnostics_path"), _default_parse_path(args.run_root, args.row_id))

    gold_rows = _read_jsonl(gold_path)
    pred_rows = _read_jsonl(prediction_path)
    overall = _read_json(analysis_dir / "overall_metrics.json")
    record_level = _read_json(analysis_dir / "record_level_metrics.json")
    validation = _read_json(analysis_dir / "validation_report.json")
    parse_diagnostics = _read_json(parse_path) if parse_path and parse_path.is_file() else {}
    per_document = _read_csv(analysis_dir / "per_document_metrics.csv")
    per_role = _read_csv(analysis_dir / "per_role_metrics.csv")
    per_event = _read_csv(analysis_dir / "per_event_type_metrics.csv")
    record_event = _read_csv(analysis_dir / "record_level_per_event_type.csv")
    bucket_event_count = _read_csv(analysis_dir / "bucket_event_count.csv")
    matched_pairs = _read_jsonl_if_exists(analysis_dir / "matched_event_pairs.jsonl")
    grouping_errors = _read_jsonl_if_exists(analysis_dir / "record_grouping_errors.jsonl")
    r2_coverage = _load_r2_coverage(args)

    role_level_f1 = _number(primary.get("role_level_f1"), overall.get("f1")) or 0.0
    exact_record_f1 = _number(primary.get("exact_record_f1"), record_level.get("record_f1_exact")) or 0.0

    event_count = _event_count_diagnostics(
        gold_rows=gold_rows,
        pred_rows=pred_rows,
        record_level=record_level,
        per_document=per_document,
        record_event=record_event,
        bucket_event_count=bucket_event_count,
    )
    record_decomposition = _record_level_decomposition(
        pred_rows=pred_rows,
        record_level=record_level,
        validation=validation,
        matched_pairs=matched_pairs,
        grouping_errors=grouping_errors,
    )
    role_value = _role_value_diagnostics(
        per_role=per_role,
        rows=rows,
        r2_coverage=r2_coverage,
        dataset=args.dataset,
        split=args.split,
    )
    event_type = _event_type_diagnostics(
        per_event=per_event,
        record_event=record_event,
        rows=rows,
        dataset=args.dataset,
        split=args.split,
    )
    oracle = _oracle_diagnostics(
        role_level_f1=role_level_f1,
        exact_record_f1=exact_record_f1,
        record_level=record_level,
    )

    return {
        "phase": "R4 event planning/grouping probe",
        "dataset": args.dataset,
        "split": args.split,
        "run_root": str(args.run_root),
        "row_id": args.row_id,
        "created_at": _created_at(),
        "scope": {
            "dev_only": True,
            "seed42_only": True,
            "s4_only": True,
            "test_run": False,
            "test_gold_read": False,
            "qwen_run": False,
            "train_run": False,
            "evaluator_run": False,
            "evaluator_artifact_read_only": True,
            "frozen_final_modified": False,
            "oracle_diagnostics": "dev_only_non_performance",
        },
        "primary_row": _primary_row_summary(primary, artifact_root=artifact_root, prediction_path=prediction_path),
        "artifacts": {
            "row_manifest": primary.get("row_manifest_path"),
            "training_manifest": primary.get("training_manifest_path"),
            "generation_manifest": primary.get("generation_manifest_path"),
            "canonical_prediction_jsonl": str(prediction_path),
            "dev_gold_jsonl": str(gold_path),
            "parse_diagnostics": str(parse_path) if parse_path else None,
            "evaluator_artifact_root": str(artifact_root),
            "overall_metrics": str(analysis_dir / "overall_metrics.json"),
            "record_level_metrics": str(analysis_dir / "record_level_metrics.json"),
            "validation_report": str(analysis_dir / "validation_report.json"),
        },
        "overall_metrics": _overall_metrics(overall),
        "event_count_diagnostics": event_count,
        "record_level_decomposition": record_decomposition,
        "role_value_diagnostics": role_value,
        "event_type_residual_errors": event_type,
        "oracle_diagnostics": oracle,
        "train_size_progression": _train_size_progression(rows, dataset=args.dataset, split=args.split),
        "parse_diagnostics": parse_diagnostics,
    }


def _validate_args(args: argparse.Namespace) -> None:
    if not args.row_id:
        raise ValueError("missing row-id")
    if args.split == "test":
        raise ValueError("R4 rejects test split")
    if args.split != EXPECTED_SPLIT:
        raise ValueError(f"R4 only permits dev split, got {args.split!r}")
    if args.dataset != EXPECTED_DATASET:
        raise ValueError(f"R4 is restricted to {EXPECTED_DATASET}, got {args.dataset!r}")
    if _path_mentions_test(args.run_root) or _path_mentions_test(args.out_dir):
        raise ValueError("R4 rejects paths that mention test")


def _read_r3_aggregate(run_root: Path) -> dict[str, Any]:
    aggregate_path = run_root / "v21_r3_s4_train_size_scaling_summary.json"
    if not aggregate_path.is_file():
        raise ValueError(f"missing R3 aggregate: {aggregate_path}")
    return _read_json(aggregate_path)


def _load_r3_rows(run_root: Path, aggregate: dict[str, Any]) -> dict[str, dict[str, Any]]:
    rows = {
        str(row_id): dict(row)
        for row_id, row in (aggregate.get("rows") or {}).items()
        if isinstance(row, dict)
    }
    for path in sorted(run_root.glob("*/row_summary.json")):
        row = _read_json(path)
        row_id = str(row.get("row_id") or path.parent.name)
        merged = dict(rows.get(row_id) or {})
        merged.update(row)
        rows[row_id] = merged
    return rows


def _validate_r3_gate(args: argparse.Namespace, aggregate: dict[str, Any], rows: dict[str, dict[str, Any]]) -> None:
    if args.row_id != ROW_D_ID:
        raise ValueError("R4 primary analysis requires Row D s4_full_or_max_frozen_surface")
    if ROW_D_ID not in rows:
        raise ValueError("missing Row D s4_full_or_max_frozen_surface artifact")
    for required in PROGRESSION_ROW_IDS:
        if required not in rows:
            raise ValueError(f"missing R3 comparison row: {required}")
    if aggregate.get("row_d_triggered") is not True:
        raise ValueError("R4 requires completed Row D full/max diagnostic")
    scope = aggregate.get("scope") or {}
    if scope.get("test_run") or scope.get("seed43_44_run"):
        raise ValueError("R4 rejects R3 aggregates that ran test or seed43/44")
    row = rows[ROW_D_ID]
    checks = {
        "seed": row.get("seed") == 42,
        "system": row.get("system") == "S4",
        "split": row.get("split") == EXPECTED_SPLIT,
        "surface": row.get("surface") == "frozen_compressed_phase6_final_profile",
        "train_limit": int(row.get("train_limit") or 0) == 6474,
        "test_run": row.get("test_run") is False,
        "seed43_44_run": row.get("seed43_44_run") is False,
    }
    failed = [name for name, ok in checks.items() if not ok]
    if failed:
        raise ValueError(f"R4 Row D gate failed: {failed}")
    event_f1 = _number(row.get("event_table_micro_f1"), row.get("role_level_f1"))
    exact_f1 = _number(row.get("exact_record_f1"))
    if round(event_f1 or 0.0, 6) != EXPECTED_ROW_D_EVENT_F1:
        raise ValueError(f"R4 requires Row D event/role F1 0.737327, got {event_f1}")
    if round(exact_f1 or 0.0, 6) != EXPECTED_ROW_D_EXACT_F1:
        raise ValueError(f"R4 requires Row D exact-record F1 0.352248, got {exact_f1}")


def _discover_evaluator_artifact(run_root: Path, row_id: str, row: dict[str, Any]) -> Path:
    direct = Path(str(row.get("evaluator_artifact_path") or ""))
    if direct.is_dir() and (direct / "manifest.json").is_file():
        return direct
    roots = sorted((run_root / "evaluator_artifacts" / row_id).glob("*/manifest.json"))
    if roots:
        return roots[-1].parent
    raise ValueError(f"missing Row D evaluator artifact for {row_id}")


def _event_count_diagnostics(
    *,
    gold_rows: list[dict[str, Any]],
    pred_rows: list[dict[str, Any]],
    record_level: dict[str, Any],
    per_document: list[dict[str, Any]],
    record_event: list[dict[str, Any]],
    bucket_event_count: list[dict[str, Any]],
) -> dict[str, Any]:
    gold_counts = {str(row.get("doc_id")): _event_count(row) for row in gold_rows}
    pred_counts = {str(row.get("doc_id")): _event_count(row) for row in pred_rows}
    doc_ids = sorted(set(gold_counts) | set(pred_counts))
    under = [doc_id for doc_id in doc_ids if pred_counts.get(doc_id, 0) < gold_counts.get(doc_id, 0)]
    over = [doc_id for doc_id in doc_ids if pred_counts.get(doc_id, 0) > gold_counts.get(doc_id, 0)]
    exact = [doc_id for doc_id in doc_ids if pred_counts.get(doc_id, 0) == gold_counts.get(doc_id, 0)]
    return {
        "documents_total": len(doc_ids),
        "gold_event_count_distribution": _count_distribution(gold_counts.values()),
        "predicted_event_count_distribution": _count_distribution(pred_counts.values()),
        "event_count_acc": _number(record_level.get("event_count_acc")),
        "event_count_correct": _number(record_level.get("event_count_correct")),
        "event_count_total": _number(record_level.get("event_count_total")),
        "under_predicted_doc_count": len(under),
        "under_predicted_docs": under,
        "over_predicted_doc_count": len(over),
        "over_predicted_docs": over,
        "exact_event_count_match_doc_count": len(exact),
        "exact_event_count_match_docs": exact,
        "event_count_error_by_event_type": _event_count_error_by_event_type(record_event),
        "single_event_vs_multi_event_doc_f1": _bucket_event_count_f1(bucket_event_count),
        "per_document_available": bool(per_document),
    }


def _record_level_decomposition(
    *,
    pred_rows: list[dict[str, Any]],
    record_level: dict[str, Any],
    validation: dict[str, Any],
    matched_pairs: list[dict[str, Any]],
    grouping_errors: list[dict[str, Any]],
) -> dict[str, Any]:
    exact_tp = int(_number(record_level.get("record_exact_tp")) or 0)
    soft_tp = int(_number(record_level.get("record_soft_0_8_tp")) or 0)
    validation_counts = validation.get("counts") or {}
    return {
        "record_exact_tp": exact_tp,
        "record_exact_fp": int(_number(record_level.get("record_exact_fp")) or 0),
        "record_exact_fn": int(_number(record_level.get("record_exact_fn")) or 0),
        "exact_record_f1": _number(record_level.get("record_f1_exact")),
        "record_soft_0_8_f1": _number(record_level.get("record_f1_soft_0_8")),
        "merge_count": int(_number(record_level.get("merge_case_count")) or 0),
        "split_count": int(_number(record_level.get("split_case_count")) or 0),
        "wrong_grouping_count": int(_number(record_level.get("wrong_grouping_case_count")) or 0),
        "duplicate_predicted_event_count": int(
            _number(validation_counts.get("duplicate_record_count"))
            or _duplicate_event_count(pred_rows)
        ),
        "empty_event_count": _empty_event_count(pred_rows),
        "partially_correct_record_count": max(soft_tp - exact_tp, 0),
        "role_complete_but_value_wrong_count": _role_value_wrong_proxy(matched_pairs),
        "value_correct_but_wrong_record_count": _value_correct_wrong_record_proxy(grouping_errors),
        "derivation_notes": {
            "partially_correct_record_count": "record_soft_0_8_tp - record_exact_tp",
            "role_complete_but_value_wrong_count": "matched-event proxy: same role appears in FP and FN args",
            "value_correct_but_wrong_record_count": (
                "record-grouping proxy: shared role/value appears in unmatched grouped records"
            ),
        },
    }


def _role_value_diagnostics(
    *,
    per_role: list[dict[str, Any]],
    rows: dict[str, dict[str, Any]],
    r2_coverage: dict[str, Any] | None,
    dataset: str,
    split: str,
) -> dict[str, Any]:
    role_rows = [_metrics_row(row, name_key="role") for row in per_role]
    role_rows = [row for row in role_rows if row.get("role")]
    role_by_name = {str(row["role"]): row for row in role_rows}
    coverage_by_role = _coverage_by_role(r2_coverage)
    for role, row in role_by_name.items():
        if role in coverage_by_role:
            row["r2_v21_candidate_coverage"] = coverage_by_role[role].get("v21_candidate_coverage")
            row["r2_baseline_candidate_coverage"] = coverage_by_role[role].get("baseline_candidate_coverage")
    return {
        "per_role_metrics": sorted(role_rows, key=lambda row: str(row["role"])),
        "top_20_low_recall_roles": sorted(role_rows, key=lambda row: (row.get("recall") or 0.0, str(row["role"])))[:20],
        "top_20_low_precision_roles": sorted(
            role_rows,
            key=lambda row: (row.get("precision") or 0.0, str(row["role"])),
        )[:20],
        "roles_improved_most_from_512_to_full": _metric_improvements(
            rows,
            analysis_file="per_role_metrics.csv",
            key="role",
            dataset=dataset,
            split=split,
        )[:20],
        "roles_still_below_0_3_f1": [
            row
            for row in sorted(role_rows, key=lambda row: (row.get("f1") or 0.0, str(row["role"])))
            if (row.get("f1") or 0.0) < 0.3
        ],
        "surface_high_extraction_low_roles": [
            row
            for row in role_rows
            if (row.get("r2_v21_candidate_coverage") or 0.0) >= 0.5
            and (row.get("f1") or 0.0) < 0.3
        ],
        "surface_low_extraction_low_roles": [
            row
            for row in role_rows
            if (row.get("r2_v21_candidate_coverage") or 0.0) < 0.3
            and (row.get("f1") or 0.0) < 0.3
        ],
        "r2_coverage_joined": bool(coverage_by_role),
    }


def _event_type_diagnostics(
    *,
    per_event: list[dict[str, Any]],
    record_event: list[dict[str, Any]],
    rows: dict[str, dict[str, Any]],
    dataset: str,
    split: str,
) -> dict[str, Any]:
    event_rows = [_metrics_row(row, name_key="event_type") for row in per_event]
    record_by_event = {str(row.get("event_type")): _numeric_copy(row) for row in record_event if row.get("event_type")}
    for row in event_rows:
        event_type = str(row.get("event_type"))
        if event_type in record_by_event:
            row["record_level"] = record_by_event[event_type]
    event_rows = [row for row in event_rows if row.get("event_type")]
    grouping_rows = sorted(
        (
            {
                "event_type": event_type,
                "record_f1_exact": metrics.get("record_f1_exact"),
                "event_count_acc": metrics.get("event_count_acc"),
                "merge_case_count": int(metrics.get("merge_case_count") or 0),
                "split_case_count": int(metrics.get("split_case_count") or 0),
                "wrong_grouping_case_count": int(metrics.get("wrong_grouping_case_count") or 0),
                "grouping_case_count": int(metrics.get("merge_case_count") or 0)
                + int(metrics.get("split_case_count") or 0)
                + int(metrics.get("wrong_grouping_case_count") or 0),
            }
            for event_type, metrics in record_by_event.items()
        ),
        key=lambda row: (-row["grouping_case_count"], str(row["event_type"])),
    )
    return {
        "event_type_f1_table": sorted(event_rows, key=lambda row: str(row["event_type"])),
        "event_types_improved_most_from_512_to_full": _metric_improvements(
            rows,
            analysis_file="per_event_type_metrics.csv",
            key="event_type",
            dataset=dataset,
            split=split,
        )[:20],
        "event_types_still_low_after_full": [
            row
            for row in sorted(event_rows, key=lambda row: (row.get("f1") or 0.0, str(row["event_type"])))
            if (row.get("f1") or 0.0) < 0.5
        ],
        "event_types_with_high_merge_split_wrong_grouping": grouping_rows[:20],
        "event_types_likely_requiring_event_planner": [
            row
            for row in grouping_rows
            if row["grouping_case_count"] > 0
            and ((row.get("event_count_acc") or 0.0) < 0.8 or (row.get("record_f1_exact") or 0.0) < 0.5)
        ][:20],
    }


def _oracle_diagnostics(
    *,
    role_level_f1: float,
    exact_record_f1: float,
    record_level: dict[str, Any],
) -> dict[str, Any]:
    gap = role_level_f1 - exact_record_f1
    return {
        "label": "dev_only_non_performance",
        "oracle_event_count_upper_bound": {
            "status": "not_estimable_from_static_artifacts",
            "observed_event_count_acc": _number(record_level.get("event_count_acc")),
        },
        "oracle_grouping_upper_bound": {
            "status": "proxy_from_existing_soft_record_metric",
            "record_f1_soft_0_8": _number(record_level.get("record_f1_soft_0_8")),
            "soft_threshold": _number(record_level.get("soft_threshold")),
        },
        "argument_level_f1": role_level_f1,
        "exact_record_f1": exact_record_f1,
        "argument_level_f1_vs_exact_record_gap": gap,
        "record_assembly_gap": gap,
        "role_level_minus_exact_record": gap,
        "grouping_bottleneck_flag": _grouping_flag(gap),
        "performance_claim_allowed": False,
    }


def _train_size_progression(rows: dict[str, dict[str, Any]], *, dataset: str, split: str) -> list[dict[str, Any]]:
    progression = []
    for row_id in PROGRESSION_ROW_IDS:
        row = rows.get(row_id) or {}
        record = _record_metrics_for_row(row, dataset=dataset, split=split)
        progression.append(
            {
                "row_id": row_id,
                "train_limit": row.get("train_limit"),
                "surface": row.get("surface"),
                "event_role_f1": _number(row.get("role_level_f1"), row.get("event_table_micro_f1")),
                "exact_record_f1": _number(row.get("exact_record_f1")),
                "event_count_acc": _number(record.get("event_count_acc")),
                "merge_count": int(_number(record.get("merge_case_count")) or 0) if record else None,
                "split_count": int(_number(record.get("split_case_count")) or 0) if record else None,
                "wrong_grouping_count": int(_number(record.get("wrong_grouping_case_count")) or 0) if record else None,
                "canonical_event_count": row.get("canonical_event_count"),
                "parse_error": row.get("parse_error"),
            }
        )
    return progression


def _record_metrics_for_row(row: dict[str, Any], *, dataset: str, split: str) -> dict[str, Any]:
    root = Path(str(row.get("evaluator_artifact_path") or ""))
    path = root / "analysis" / dataset / split / "record_level_metrics.json"
    if path.is_file():
        return _read_json(path)
    return {}


def _metric_improvements(
    rows: dict[str, dict[str, Any]],
    *,
    analysis_file: str,
    key: str,
    dataset: str,
    split: str,
) -> list[dict[str, Any]]:
    baseline = _analysis_csv_for_row(rows.get("baseline_512_existing") or {}, dataset, split, analysis_file)
    full = _analysis_csv_for_row(rows.get(ROW_D_ID) or {}, dataset, split, analysis_file)
    baseline_by_key = {str(row.get(key)): _metrics_row(row, name_key=key) for row in baseline if row.get(key)}
    improvements = []
    for raw in full:
        item = _metrics_row(raw, name_key=key)
        name = str(item.get(key) or "")
        if not name:
            continue
        base = baseline_by_key.get(name) or {}
        improvements.append(
            {
                key: name,
                "baseline_f1": base.get("f1"),
                "full_f1": item.get("f1"),
                "delta_f1": None if base.get("f1") is None or item.get("f1") is None else item["f1"] - base["f1"],
                "baseline_recall": base.get("recall"),
                "full_recall": item.get("recall"),
                "full_precision": item.get("precision"),
            }
        )
    return sorted(
        improvements,
        key=lambda row: (-(row.get("delta_f1") if row.get("delta_f1") is not None else -999.0), str(row.get(key))),
    )


def _analysis_csv_for_row(row: dict[str, Any], dataset: str, split: str, filename: str) -> list[dict[str, Any]]:
    root = Path(str(row.get("evaluator_artifact_path") or ""))
    path = root / "analysis" / dataset / split / filename
    return _read_csv(path)


def _overall_metrics(overall: dict[str, Any]) -> dict[str, Any]:
    return {
        "event_table_micro_f1": _number(overall.get("f1")),
        "precision": _number(overall.get("precision")),
        "recall": _number(overall.get("recall")),
        "tp": int(_number(overall.get("tp")) or 0),
        "fp": int(_number(overall.get("fp")) or 0),
        "fn": int(_number(overall.get("fn")) or 0),
        "num_gold_events": int(_number(overall.get("num_gold_events")) or 0),
        "num_pred_events": int(_number(overall.get("num_pred_events")) or 0),
        "metric": overall.get("metric"),
        "uses_offset": overall.get("uses_offset"),
        "uses_naen": overall.get("uses_naen"),
    }


def _primary_row_summary(row: dict[str, Any], *, artifact_root: Path, prediction_path: Path) -> dict[str, Any]:
    return {
        "row_id": row.get("row_id"),
        "seed": row.get("seed"),
        "system": row.get("system"),
        "dataset": row.get("dataset", EXPECTED_DATASET),
        "split": row.get("split"),
        "surface": row.get("surface"),
        "train_limit": row.get("train_limit"),
        "event_table_micro_f1": row.get("event_table_micro_f1"),
        "role_level_f1": row.get("role_level_f1"),
        "exact_record_f1": row.get("exact_record_f1"),
        "canonical_event_count": row.get("canonical_event_count"),
        "parse_error": row.get("parse_error"),
        "prediction_path": str(prediction_path),
        "evaluator_artifact_path": str(artifact_root),
    }


def _run_manifest(args: argparse.Namespace, analysis: dict[str, Any], analysis_path: Path) -> dict[str, Any]:
    return {
        "phase": "R4 event planning/grouping probe",
        "dataset": args.dataset,
        "split": args.split,
        "row_id": args.row_id,
        "analysis_json": str(analysis_path),
        "created_at": analysis["created_at"],
        "qwen_run": False,
        "train_run": False,
        "evaluator_run": False,
        "test_run": False,
        "test_gold_read": False,
        "oracle_diagnostics": "dev_only_non_performance",
        "frozen_final_modified": False,
    }


def _event_count(row: dict[str, Any]) -> int:
    events = row.get("events") or []
    return len(events) if isinstance(events, list) else 0


def _event_signature(event: dict[str, Any]) -> tuple[Any, ...]:
    args = event.get("arguments") or {}
    pairs = []
    if isinstance(args, dict):
        for role, values in args.items():
            if isinstance(values, list):
                for value in values:
                    if isinstance(value, dict):
                        pairs.append((str(role), str(value.get("text") or value.get("norm_text") or "")))
                    else:
                        pairs.append((str(role), str(value)))
    return (str(event.get("event_type") or ""), tuple(sorted(pairs)))


def _duplicate_event_count(rows: list[dict[str, Any]]) -> int:
    duplicates = 0
    for row in rows:
        seen: set[tuple[Any, ...]] = set()
        for event in row.get("events") or []:
            if not isinstance(event, dict):
                continue
            signature = _event_signature(event)
            if signature in seen:
                duplicates += 1
            seen.add(signature)
    return duplicates


def _empty_event_count(rows: list[dict[str, Any]]) -> int:
    count = 0
    for row in rows:
        for event in row.get("events") or []:
            if isinstance(event, dict) and not any((event.get("arguments") or {}).values()):
                count += 1
    return count


def _role_value_wrong_proxy(matched_pairs: list[dict[str, Any]]) -> int:
    count = 0
    for pair in matched_pairs:
        fp_roles = {str(arg.get("role")) for arg in pair.get("fp_args") or [] if isinstance(arg, dict)}
        fn_roles = {str(arg.get("role")) for arg in pair.get("fn_args") or [] if isinstance(arg, dict)}
        if fp_roles & fn_roles:
            count += 1
    return count


def _value_correct_wrong_record_proxy(grouping_errors: list[dict[str, Any]]) -> int:
    count = 0
    for row in grouping_errors:
        gold_args = _flatten_record_args(row.get("gold_records") or [])
        pred_args = _flatten_record_args(row.get("pred_records") or [])
        if gold_args & pred_args:
            count += 1
    return count


def _flatten_record_args(records: Iterable[Any]) -> set[tuple[str, str]]:
    args: set[tuple[str, str]] = set()
    for record in records:
        if not isinstance(record, dict):
            continue
        for arg in record.get("arguments") or []:
            if isinstance(arg, dict):
                args.add((str(arg.get("role") or ""), str(arg.get("norm_text") or arg.get("text") or "")))
    return args


def _event_count_error_by_event_type(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    table = []
    for row in rows:
        table.append(
            {
                "event_type": row.get("event_type"),
                "event_count_acc": _number(row.get("event_count_acc")),
                "event_count_correct": _number(row.get("event_count_correct")),
                "event_count_total": _number(row.get("event_count_total")),
                "record_f1_exact": _number(row.get("record_f1_exact")),
                "merge_case_count": int(_number(row.get("merge_case_count")) or 0),
                "split_case_count": int(_number(row.get("split_case_count")) or 0),
                "wrong_grouping_case_count": int(_number(row.get("wrong_grouping_case_count")) or 0),
            }
        )
    return table


def _bucket_event_count_f1(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "bucket": row.get("bucket"),
            "doc_count": int(_number(row.get("doc_count")) or 0),
            "f1": _number(row.get("f1")),
            "precision": _number(row.get("precision")),
            "recall": _number(row.get("recall")),
        }
        for row in rows
    ]


def _metrics_row(row: dict[str, Any], *, name_key: str) -> dict[str, Any]:
    return {
        name_key: row.get(name_key),
        "tp": int(_number(row.get("tp")) or 0),
        "fp": int(_number(row.get("fp")) or 0),
        "fn": int(_number(row.get("fn")) or 0),
        "precision": _number(row.get("precision")),
        "recall": _number(row.get("recall")),
        "f1": _number(row.get("f1")),
    }


def _numeric_copy(row: dict[str, Any]) -> dict[str, Any]:
    converted: dict[str, Any] = {}
    for key, value in row.items():
        converted[key] = _number(value) if key != "event_type" else value
    return converted


def _coverage_by_role(summary: dict[str, Any] | None) -> dict[str, dict[str, Any]]:
    if not summary:
        return {}
    output = {}
    for row in summary.get("role_level_coverage") or []:
        if isinstance(row, dict) and row.get("role"):
            output[str(row["role"])] = row
    return output


def _load_r2_coverage(args: argparse.Namespace) -> dict[str, Any] | None:
    candidates = []
    if args.r2_coverage_json is not None:
        candidates.append(args.r2_coverage_json)
    candidates.extend(
        [
            args.run_root.parent / "v21_r2_surface_coverage_seed42" / "coverage_summary.json",
            Path("server_results/v21_r2_surface_coverage_seed42/coverage_summary.json"),
        ]
    )
    for path in candidates:
        if path.is_file():
            return _read_json(path)
    return None


def _grouping_flag(gap: float) -> str:
    if gap >= GROUPING_HIGH_GAP:
        return "high"
    if gap >= GROUPING_MEDIUM_GAP:
        return "medium"
    return "low"


def _count_distribution(values: Iterable[int]) -> dict[str, int]:
    return {str(key): value for key, value in sorted(Counter(values).items())}


def _canonical_path_from_generation_manifest(path: Any) -> Path | None:
    if not path:
        return None
    manifest = Path(str(path))
    if not manifest.is_file():
        return None
    payload = _read_json(manifest)
    raw = payload.get("canonical_predictions_path") or payload.get("canonical_path")
    return Path(str(raw)) if raw else None


def _default_parse_path(run_root: Path, row_id: str) -> Path:
    return run_root / row_id / "full_dev" / "parse_diagnostics.dev.json"


def _existing_path(*candidates: Any) -> Path:
    for candidate in candidates:
        if not candidate:
            continue
        path = candidate if isinstance(candidate, Path) else Path(str(candidate))
        if path.is_file():
            return path
    raise ValueError(f"missing required artifact path from candidates: {[str(item) for item in candidates if item]}")


def _path_mentions_test(path: Path) -> bool:
    return any(part.lower() == "test" for part in path.parts)


def _read_json(path: str | Path) -> dict[str, Any]:
    with Path(path).open(encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object: {path}")
    return payload


def _read_jsonl(path: str | Path) -> list[dict[str, Any]]:
    rows = []
    with Path(path).open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            payload = json.loads(line)
            if isinstance(payload, dict):
                rows.append(payload)
    return rows


def _read_jsonl_if_exists(path: Path) -> list[dict[str, Any]]:
    return _read_jsonl(path) if path.is_file() else []


def _read_csv(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    with path.open(newline="", encoding="utf-8") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _number(*values: Any) -> float | None:
    for value in values:
        if isinstance(value, bool) or value is None:
            continue
        try:
            return float(value)
        except (TypeError, ValueError):
            continue
    return None


def _created_at() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


if __name__ == "__main__":
    raise SystemExit(main())
