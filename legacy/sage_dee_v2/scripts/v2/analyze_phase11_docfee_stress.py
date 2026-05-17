from __future__ import annotations

import csv
import json
import sys
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "src"))

from sage_dee.v2.data_interface.dataset_loader import V2DatasetDocument, load_documents  # noqa: E402
from sage_dee.v2.data_interface.jsonl import read_jsonl  # noqa: E402
from scripts.v2.run_phase7_surface_memory_ablation import (  # noqa: E402
    _document_content,
    _gold_argument_texts,
    _prediction_arguments,
    _rate,
    _surface_text,
)


@dataclass(frozen=True)
class LengthBucketSpec:
    name: str
    min_exclusive: int | None
    max_inclusive: int | None

    def matches(self, value: int) -> bool:
        if self.min_exclusive is not None and value <= self.min_exclusive:
            return False
        if self.max_inclusive is not None and value > self.max_inclusive:
            return False
        return True


DEFAULT_LENGTH_BUCKETS = (
    LengthBucketSpec("<= 1024", None, 1024),
    LengthBucketSpec("1024 < x <= 2048", 1024, 2048),
    LengthBucketSpec("2048 < x <= 4096", 2048, 4096),
    LengthBucketSpec("> 4096", 4096, None),
)

FAILURE_CLASS_ORDER = (
    "parse_error",
    "schema_violation",
    "truncation",
    "missing_event",
    "candidate_overflow",
    "low_surface_recall",
    "hallucinated_argument",
    "non_surface_argument",
)


def build_phase11_docfee_stress_analysis(
    *,
    run_root: str | Path,
    dataset: str,
    split: str,
    data_root: str | Path,
    evaluator_artifact_root: str | Path | None,
    length_buckets: Sequence[LengthBucketSpec] = DEFAULT_LENGTH_BUCKETS,
    length_measure_name: str = "char_count",
    length_measure_source: str = "content_raw",
) -> dict[str, Any]:
    run_root_path = Path(run_root)
    prompt_rows = read_jsonl(run_root_path / f"prompts.{split}.jsonl")
    raw_rows = _index_rows(read_jsonl(run_root_path / f"raw_outputs.{split}.jsonl"), "candidate_id")
    parsed_rows = _index_rows(read_jsonl(run_root_path / f"parsed_candidates.{split}.jsonl"), "candidate_id")
    canonical_rows = _index_rows(
        read_jsonl(run_root_path / "predictions" / dataset / f"{split}.canonical.pred.jsonl"),
        "doc_id",
    )
    parse_diagnostics = _read_json(run_root_path / f"parse_diagnostics.{split}.json")
    gold_docs = {
        doc.doc_id: doc
        for doc in load_documents(dataset, split, data_root=data_root, mode="train")
    }
    evaluator = _read_evaluator_artifacts(evaluator_artifact_root, dataset=dataset, split=split)
    per_document_metrics = _index_rows(evaluator.get("per_document_metrics") or [], "doc_id")

    doc_records = [
        _build_doc_record(
            prompt_row=prompt_row,
            raw_row=raw_rows.get(f"{prompt_row.get('doc_id')}:getm:0", {}),
            parsed_row=parsed_rows.get(f"{prompt_row.get('doc_id')}:getm:0", {}),
            canonical_row=canonical_rows.get(str(prompt_row.get("doc_id") or ""), {}),
            gold_doc=gold_docs.get(str(prompt_row.get("doc_id") or "")),
            metrics_row=per_document_metrics.get(str(prompt_row.get("doc_id") or ""), {}),
            length_buckets=length_buckets,
        )
        for prompt_row in prompt_rows
    ]
    doc_records = [record for record in doc_records if record is not None]

    overall = _overall_summary(
        doc_records=doc_records,
        parse_diagnostics=parse_diagnostics,
        evaluator=evaluator,
        dataset=dataset,
        split=split,
        length_measure_name=length_measure_name,
        length_measure_source=length_measure_source,
    )
    bucket_rows = _bucket_rows(doc_records, length_buckets=length_buckets)
    parse_summary = _parse_diagnostics_summary(parse_diagnostics, doc_count=len(doc_records), bucket_rows=bucket_rows)
    truncation_summary = _truncation_summary(doc_records, bucket_rows=bucket_rows, doc_count=len(doc_records))
    surface_summary = _surface_summary(doc_records, bucket_rows=bucket_rows, doc_count=len(doc_records))
    failure_samples = _failure_samples(doc_records)

    return {
        "phase": "Phase 11 DocFEE stress analysis",
        "dataset": dataset,
        "split": split,
        "run_root": str(run_root_path),
        "evaluator_artifact_root": str(evaluator_artifact_root) if evaluator_artifact_root else None,
        "length_measure": {
            "name": length_measure_name,
            "source": length_measure_source,
        },
        "overall": overall,
        "parse_diagnostics": parse_summary,
        "truncation_diagnostics": truncation_summary,
        "surface_diagnostics": surface_summary,
        "length_bucket_diagnostics": {
            "bucket_spec": [bucket.__dict__ for bucket in length_buckets],
            "length_buckets": bucket_rows,
        },
        "failure_samples": failure_samples,
        "limitation": {
            "status": "diagnostic-only",
            "evidence": "DocFEE stress is a boundary analysis, not a long-document SOTA claim",
        },
    }


def write_phase11_docfee_stress_outputs(run_root: str | Path, analysis: dict[str, Any]) -> dict[str, Path]:
    run_root_path = Path(run_root)
    outputs = {
        "analysis": run_root_path / "phase11_docfee_stress_analysis.json",
        "parse": run_root_path / "phase11_parse_diagnostics.json",
        "truncation": run_root_path / "phase11_truncation_diagnostics.json",
        "surface": run_root_path / "phase11_surface_diagnostics.json",
        "length": run_root_path / "phase11_length_bucket_diagnostics.json",
        "failure_samples": run_root_path / "phase11_failure_samples.json",
    }
    _write_json(outputs["analysis"], analysis)
    _write_json(outputs["parse"], analysis["parse_diagnostics"])
    _write_json(outputs["truncation"], analysis["truncation_diagnostics"])
    _write_json(outputs["surface"], analysis["surface_diagnostics"])
    _write_json(outputs["length"], analysis["length_bucket_diagnostics"])
    _write_json(outputs["failure_samples"], {"failure_samples": analysis["failure_samples"]})
    return outputs


def load_phase11_docfee_stress_analysis(run_root: str | Path) -> dict[str, Any]:
    path = Path(run_root) / "phase11_docfee_stress_analysis.json"
    payload = _read_json(path)
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object: {path}")
    return payload


def render_phase11_docfee_stress_markdown(analysis: dict[str, Any]) -> str:
    overall = analysis.get("overall") or {}
    bucket_rows = (analysis.get("length_bucket_diagnostics") or {}).get("length_buckets") or []
    failure_samples = analysis.get("failure_samples") or []
    prompt_token_hits = _format_number(_truncation_value(analysis, "prompt_token_limit_hit_count"))
    prompt_middle_drops = _format_number(_truncation_value(analysis, "prompt_middle_token_drop_count"))
    max_new_token_hits = _format_number(_truncation_value(analysis, "hit_max_new_tokens_count"))
    lines = [
        "# Phase 11 DocFEE Stress Analysis",
        "",
        "## Overall",
        "",
        "| Metric | Value |",
        "| --- | ---: |",
        f"| Event-table micro-F1 | {_format_number(overall.get('event_table_micro_f1'))} |",
        f"| Role-level F1 | {_format_number(overall.get('role_level_f1'))} |",
        f"| Exact-record F1 | {_format_number(overall.get('exact_record_f1'))} |",
        f"| Parse error count | {_format_number(overall.get('parse_error_count'))} |",
        f"| Parse error rate | {_format_number(overall.get('parse_error_rate'))} |",
        f"| Schema violation rows | {_format_number(overall.get('schema_violation_rows'))} |",
        f"| Schema violation count | {_format_number(overall.get('schema_violation_count'))} |",
        "",
        "## Length Buckets",
        "",
        "| Bucket | Docs | F1 | Parse error | Truncation | Missing event | "
        "Candidate overflow | Surface recall | Hallucinated arg | Non-surface arg |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in bucket_rows:
        lines.append(
            (
                "| {bucket} | {doc_count} | {f1} | {parse_error_rate} | {truncation_rate} | "
                "{missing_event_rate} | {candidate_overflow_rate} | {surface_recall} | "
                "{hallucinated_argument_rate} | {non_surface_argument_rate} |"
            ).format(
                bucket=row.get("bucket"),
                doc_count=row.get("doc_count"),
                f1=_format_number(row.get("event_table_micro_f1")),
                parse_error_rate=_format_number(row.get("parse_error_rate")),
                truncation_rate=_format_number(row.get("truncation_rate")),
                missing_event_rate=_format_number(row.get("missing_event_rate")),
                candidate_overflow_rate=_format_number(row.get("candidate_overflow_rate")),
                surface_recall=_format_number(row.get("surface_recall")),
                hallucinated_argument_rate=_format_number(row.get("hallucinated_argument_rate")),
                non_surface_argument_rate=_format_number(row.get("non_surface_argument_rate")),
            )
        )
    lines.extend(
        [
            "",
            "## Truncation Diagnostics",
            "",
            f"- prompt token limit hit: {prompt_token_hits}",
            f"- prompt middle-token drop: {prompt_middle_drops}",
            f"- hit max new tokens: {max_new_token_hits}",
            "",
            "## Failure Samples",
            "",
            "| doc_id | error_class |",
            "| --- | --- |",
        ]
    )
    for sample in failure_samples:
        lines.append(f"| {sample.get('doc_id')} | {sample.get('error_class')} |")
    lines.append("")
    return "\n".join(lines)


def _build_doc_record(
    *,
    prompt_row: dict[str, Any],
    raw_row: dict[str, Any],
    parsed_row: dict[str, Any],
    canonical_row: dict[str, Any],
    gold_doc: V2DatasetDocument | None,
    metrics_row: dict[str, Any],
    length_buckets: Sequence[LengthBucketSpec],
) -> dict[str, Any] | None:
    doc_id = str(prompt_row.get("doc_id") or "").strip()
    if not doc_id or gold_doc is None:
        return None
    content = _document_content(gold_doc)
    length_value = len(gold_doc.input.content_raw or gold_doc.input.content or "")
    bucket = _bucket_for_length(length_value, length_buckets=length_buckets).name
    selected_surface_candidates = [
        _surface_text(candidate)
        for candidate in (prompt_row.get("prompt_surface_candidates") or [])
        if _surface_text(candidate)
    ]
    raw_surface_candidates = [
        _surface_text(candidate)
        for candidate in (prompt_row.get("surface_candidates") or [])
        if _surface_text(candidate)
    ]
    prompt_metadata = prompt_row.get("prompt_metadata") or {}
    if not isinstance(prompt_metadata, dict):
        prompt_metadata = {}
    max_surface_candidates = _as_int(prompt_metadata.get("max_surface_candidates")) or len(selected_surface_candidates)
    gold_argument_texts = _gold_argument_texts(gold_doc)
    predicted_arguments = _prediction_arguments([canonical_row])
    selected_counter = Counter(selected_surface_candidates)
    gold_counter = Counter(gold_argument_texts)
    gold_hits = 0
    gold_unlocated = 0
    ambiguous = 0
    for text in gold_argument_texts:
        if selected_counter.get(text, 0) > 0:
            gold_hits += 1
        else:
            gold_unlocated += 1
        if selected_counter.get(text, 0) > 1:
            ambiguous += 1
    candidate_precision_hits = sum(1 for text in selected_surface_candidates if text in gold_counter)
    hallucinated = sum(1 for _, text in predicted_arguments if text not in content)
    non_surface = sum(1 for _, text in predicted_arguments if text not in selected_counter)
    parse_status = str(parsed_row.get("parse_status") or "").strip()
    truncation = bool(
        _as_int(raw_row.get("prompt_middle_token_drop_count"))
        or raw_row.get("prompt_token_limit_hit") is True
        or raw_row.get("hit_max_new_tokens") is True
    )
    gold_events = (gold_doc.gold.events if gold_doc.gold else []) or []
    gold_event_count = _as_int(metrics_row.get("num_gold_events")) or len(gold_events)
    pred_event_count = _as_int(metrics_row.get("num_pred_events")) or len(canonical_row.get("events") or [])
    missing_event_count = max(0, gold_event_count - pred_event_count)
    per_doc = {
        "doc_id": doc_id,
        "bucket": bucket,
        "length_value": length_value,
        "parse_status": parse_status,
        "parse_error": parse_status == "parse_error",
        "schema_violation": parse_status == "schema_violation",
        "truncation": truncation,
        "candidate_overflow": len(raw_surface_candidates) > int(max_surface_candidates),
        "candidate_overflow_limit": int(max_surface_candidates),
        "surface_recall": _rate(gold_hits, len(gold_argument_texts)),
        "candidate_precision": _rate(candidate_precision_hits, len(selected_surface_candidates)),
        "gold_argument_unlocated_rate": _rate(gold_unlocated, len(gold_argument_texts)),
        "ambiguous_match_rate": _rate(ambiguous, len(gold_argument_texts)),
        "hallucinated_argument_rate": _rate(hallucinated, len(predicted_arguments)),
        "non_surface_argument_rate": _rate(non_surface, len(predicted_arguments)),
        "candidate_hits": gold_hits,
        "candidate_precision_hits": candidate_precision_hits,
        "gold_argument_unlocated_count": gold_unlocated,
        "ambiguous_match_count": ambiguous,
        "selected_surface_count": len(selected_surface_candidates),
        "raw_surface_count": len(raw_surface_candidates),
        "gold_argument_count": len(gold_argument_texts),
        "predicted_argument_count": len(predicted_arguments),
        "hallucinated_argument_count": hallucinated,
        "non_surface_argument_count": non_surface,
        "gold_event_count": gold_event_count,
        "pred_event_count": pred_event_count,
        "missing_event_count": missing_event_count,
        "missing_event_rate": _rate(missing_event_count, gold_event_count),
        "prompt_token_limit_hit": bool(raw_row.get("prompt_token_limit_hit")),
        "hit_max_new_tokens": bool(raw_row.get("hit_max_new_tokens")),
        "prompt_middle_token_drop_count": _as_int(raw_row.get("prompt_middle_token_drop_count")) or 0,
        "tp": _as_int(metrics_row.get("tp")) or 0,
        "fp": _as_int(metrics_row.get("fp")) or 0,
        "fn": _as_int(metrics_row.get("fn")) or 0,
    }
    per_doc["failure_class"] = _failure_class(per_doc)
    return per_doc


def _overall_summary(
    *,
    doc_records: list[dict[str, Any]],
    parse_diagnostics: dict[str, Any],
    evaluator: dict[str, Any],
    dataset: str,
    split: str,
    length_measure_name: str,
    length_measure_source: str,
) -> dict[str, Any]:
    doc_count = len(doc_records)
    tp = sum(int(row.get("tp") or 0) for row in doc_records)
    fp = sum(int(row.get("fp") or 0) for row in doc_records)
    fn = sum(int(row.get("fn") or 0) for row in doc_records)
    parse_error_count = sum(1 for row in doc_records if row.get("parse_error"))
    schema_violation_rows = sum(1 for row in doc_records if row.get("schema_violation"))
    truncation_count = sum(1 for row in doc_records if row.get("truncation"))
    candidate_overflow_count = sum(1 for row in doc_records if row.get("candidate_overflow"))
    missing_event_count = sum(int(row.get("missing_event_count") or 0) for row in doc_records)
    gold_event_count = sum(int(row.get("gold_event_count") or 0) for row in doc_records)
    pred_event_count = sum(int(row.get("pred_event_count") or 0) for row in doc_records)
    gold_argument_count = sum(int(row.get("gold_argument_count") or 0) for row in doc_records)
    selected_surface_count = sum(int(row.get("selected_surface_count") or 0) for row in doc_records)
    candidate_hits = sum(int(row.get("candidate_hits") or 0) for row in doc_records)
    candidate_precision_hits = sum(int(row.get("candidate_precision_hits") or 0) for row in doc_records)
    gold_unlocated_count = sum(int(row.get("gold_argument_unlocated_count") or 0) for row in doc_records)
    ambiguous_count = sum(int(row.get("ambiguous_match_count") or 0) for row in doc_records)
    hallucinated_count = sum(int(row.get("hallucinated_argument_count") or 0) for row in doc_records)
    non_surface_count = sum(int(row.get("non_surface_argument_count") or 0) for row in doc_records)
    predicted_argument_count = sum(int(row.get("predicted_argument_count") or 0) for row in doc_records)
    event_table_micro_f1 = evaluator.get("event_table_micro_f1")
    if event_table_micro_f1 is None:
        event_table_micro_f1 = _f1(tp, fp, fn)
    role_level_f1 = evaluator.get("role_level_f1")
    if role_level_f1 is None:
        role_level_f1 = event_table_micro_f1
    overall = {
        "dataset": dataset,
        "split": split,
        "length_measure_name": length_measure_name,
        "length_measure_source": length_measure_source,
        "doc_count": doc_count,
        "event_table_micro_f1": event_table_micro_f1,
        "role_level_f1": role_level_f1,
        "exact_record_f1": evaluator.get("exact_record_f1"),
        "parse_error_count": parse_error_count,
        "parse_error_rate": _rate(parse_error_count, doc_count),
        "schema_violation_rows": schema_violation_rows,
        "schema_violation_count": _schema_violation_count(parse_diagnostics),
        "truncation_count": truncation_count,
        "truncation_rate": _rate(truncation_count, doc_count),
        "candidate_overflow_count": candidate_overflow_count,
        "candidate_overflow_rate": _rate(candidate_overflow_count, doc_count),
        "missing_event_count": missing_event_count,
        "missing_event_rate": _rate(missing_event_count, gold_event_count),
        "surface_recall": _rate(candidate_hits, gold_argument_count),
        "candidate_precision": _rate(candidate_precision_hits, selected_surface_count),
        "gold_argument_unlocated_rate": _rate(gold_unlocated_count, gold_argument_count),
        "ambiguous_match_rate": _rate(ambiguous_count, gold_argument_count),
        "hallucinated_argument_rate": _rate(hallucinated_count, predicted_argument_count),
        "non_surface_argument_rate": _rate(non_surface_count, predicted_argument_count),
        "gold_event_count": gold_event_count,
        "pred_event_count": pred_event_count,
        "gold_argument_count": gold_argument_count,
        "selected_surface_count": selected_surface_count,
        "candidate_hits": candidate_hits,
        "candidate_precision_hits": candidate_precision_hits,
        "gold_argument_unlocated_count": gold_unlocated_count,
        "ambiguous_match_count": ambiguous_count,
        "hallucinated_argument_count": hallucinated_count,
        "non_surface_argument_count": non_surface_count,
        "evaluator_validation_ok": evaluator.get("validation_ok"),
        "evaluator_artifact_root": evaluator.get("artifact_root"),
    }
    return overall


def _parse_diagnostics_summary(
    parse_diagnostics: dict[str, Any],
    *,
    doc_count: int,
    bucket_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    parse_status_counts = dict(parse_diagnostics.get("parse_status_counts") or {})
    return {
        "diagnostic_version": parse_diagnostics.get("diagnostic_version"),
        "parse_status_counts": parse_status_counts,
        "diagnostic_counts": dict(parse_diagnostics.get("diagnostic_counts") or {}),
        "parse_error_subtype_counts": dict(parse_diagnostics.get("parse_error_subtype_counts") or {}),
        "parse_error_primary_subtype_counts": dict(parse_diagnostics.get("parse_error_primary_subtype_counts") or {}),
        "prompt_token_summary": dict(parse_diagnostics.get("prompt_token_summary") or {}),
        "doc_count": doc_count,
        "parse_error_count": int(parse_status_counts.get("parse_error") or 0),
        "parse_error_rate": _rate(int(parse_status_counts.get("parse_error") or 0), doc_count),
        "schema_violation_rows": int(parse_status_counts.get("schema_violation") or 0),
        "schema_violation_count": _schema_violation_count(parse_diagnostics),
        "by_length_bucket": {
            row["bucket"]: {
                "doc_count": row["doc_count"],
                "parse_error_count": row["parse_error_count"],
                "parse_error_rate": row["parse_error_rate"],
                "schema_violation_rows": row["schema_violation_rows"],
            }
            for row in bucket_rows
        },
    }


def _truncation_summary(
    doc_records: list[dict[str, Any]],
    *,
    bucket_rows: list[dict[str, Any]],
    doc_count: int,
) -> dict[str, Any]:
    prompt_token_limit_hit_count = sum(1 for row in doc_records if row.get("prompt_token_limit_hit"))
    prompt_middle_token_drop_count = sum(
        1 for row in doc_records if int(row.get("prompt_middle_token_drop_count") or 0) > 0
    )
    hit_max_new_tokens_count = sum(1 for row in doc_records if row.get("hit_max_new_tokens"))
    truncation_count = sum(1 for row in doc_records if row.get("truncation"))
    by_bucket = {
        row["bucket"]: {
            "doc_count": row["doc_count"],
            "truncation_count": row["truncation_count"],
            "truncation_rate": row["truncation_rate"],
        }
        for row in bucket_rows
    }
    return {
        "doc_count": doc_count,
        "prompt_token_limit_hit_count": prompt_token_limit_hit_count,
        "prompt_middle_token_drop_count": prompt_middle_token_drop_count,
        "hit_max_new_tokens_count": hit_max_new_tokens_count,
        "truncation_count": truncation_count,
        "truncation_rate": _rate(truncation_count, doc_count),
        "by_length_bucket": by_bucket,
    }


def _surface_summary(
    doc_records: list[dict[str, Any]],
    *,
    bucket_rows: list[dict[str, Any]],
    doc_count: int,
) -> dict[str, Any]:
    gold_argument_count = sum(int(row.get("gold_argument_count") or 0) for row in doc_records)
    selected_surface_count = sum(int(row.get("selected_surface_count") or 0) for row in doc_records)
    candidate_hits = sum(int(row.get("candidate_hits") or 0) for row in doc_records)
    candidate_precision_hits = sum(int(row.get("candidate_precision_hits") or 0) for row in doc_records)
    gold_argument_unlocated_count = sum(int(row.get("gold_argument_unlocated_count") or 0) for row in doc_records)
    ambiguous_match_count = sum(int(row.get("ambiguous_match_count") or 0) for row in doc_records)
    hallucinated_count = sum(int(row.get("hallucinated_argument_count") or 0) for row in doc_records)
    non_surface_count = sum(int(row.get("non_surface_argument_count") or 0) for row in doc_records)
    predicted_argument_count = sum(int(row.get("predicted_argument_count") or 0) for row in doc_records)
    by_bucket = {
        row["bucket"]: {
            "surface_recall": row["surface_recall"],
            "candidate_precision": row["candidate_precision"],
            "gold_argument_unlocated_rate": row["gold_argument_unlocated_rate"],
            "ambiguous_match_rate": row["ambiguous_match_rate"],
            "hallucinated_argument_rate": row["hallucinated_argument_rate"],
            "non_surface_argument_rate": row["non_surface_argument_rate"],
        }
        for row in bucket_rows
    }
    return {
        "doc_count": doc_count,
        "gold_argument_count": gold_argument_count,
        "selected_surface_count": selected_surface_count,
        "candidate_hits": candidate_hits,
        "candidate_precision_hits": candidate_precision_hits,
        "candidate_precision": _rate(candidate_precision_hits, selected_surface_count),
        "gold_argument_unlocated_count": gold_argument_unlocated_count,
        "gold_argument_unlocated_rate": _rate(gold_argument_unlocated_count, gold_argument_count),
        "ambiguous_match_count": ambiguous_match_count,
        "ambiguous_match_rate": _rate(ambiguous_match_count, gold_argument_count),
        "predicted_argument_count": predicted_argument_count,
        "hallucinated_argument_count": hallucinated_count,
        "hallucinated_argument_rate": _rate(hallucinated_count, predicted_argument_count),
        "non_surface_argument_count": non_surface_count,
        "non_surface_argument_rate": _rate(non_surface_count, predicted_argument_count),
        "surface_recall": _rate(candidate_hits, gold_argument_count),
        "by_length_bucket": by_bucket,
    }


def _bucket_rows(
    doc_records: list[dict[str, Any]],
    *,
    length_buckets: Sequence[LengthBucketSpec],
) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = {bucket.name: [] for bucket in length_buckets}
    for record in doc_records:
        grouped.setdefault(record["bucket"], []).append(record)
    rows: list[dict[str, Any]] = []
    for bucket in length_buckets:
        records = grouped.get(bucket.name, [])
        rows.append(_bucket_row(bucket=bucket, records=records))
    return rows


def _bucket_row(*, bucket: LengthBucketSpec, records: list[dict[str, Any]]) -> dict[str, Any]:
    doc_count = len(records)
    if not records:
        return {
            "bucket": bucket.name,
            "min_exclusive": bucket.min_exclusive,
            "max_inclusive": bucket.max_inclusive,
            "doc_count": 0,
            "length_min": None,
            "length_max": None,
            "length_mean": None,
            "tp": 0,
            "fp": 0,
            "fn": 0,
            "event_table_micro_f1": None,
            "parse_error_count": 0,
            "parse_error_rate": None,
            "schema_violation_rows": 0,
            "schema_violation_rate": None,
            "truncation_count": 0,
            "truncation_rate": None,
            "missing_event_count": 0,
            "missing_event_rate": None,
            "candidate_overflow_count": 0,
            "candidate_overflow_rate": None,
            "surface_recall": None,
            "candidate_precision": None,
            "gold_argument_unlocated_rate": None,
            "ambiguous_match_rate": None,
            "hallucinated_argument_rate": None,
            "non_surface_argument_rate": None,
            "gold_event_count": 0,
            "pred_event_count": 0,
            "gold_argument_count": 0,
            "selected_surface_count": 0,
            "candidate_hits": 0,
            "candidate_precision_hits": 0,
            "gold_argument_unlocated_count": 0,
            "ambiguous_match_count": 0,
            "hallucinated_argument_count": 0,
            "non_surface_argument_count": 0,
        }
    tp = sum(int(row.get("tp") or 0) for row in records)
    fp = sum(int(row.get("fp") or 0) for row in records)
    fn = sum(int(row.get("fn") or 0) for row in records)
    gold_event_count = sum(int(row.get("gold_event_count") or 0) for row in records)
    pred_event_count = sum(int(row.get("pred_event_count") or 0) for row in records)
    gold_argument_count = sum(int(row.get("gold_argument_count") or 0) for row in records)
    selected_surface_count = sum(int(row.get("selected_surface_count") or 0) for row in records)
    candidate_hits = sum(int(row.get("candidate_hits") or 0) for row in records)
    candidate_precision_hits = sum(int(row.get("candidate_precision_hits") or 0) for row in records)
    gold_unlocated_count = sum(int(row.get("gold_argument_unlocated_count") or 0) for row in records)
    ambiguous_count = sum(int(row.get("ambiguous_match_count") or 0) for row in records)
    hallucinated_count = sum(int(row.get("hallucinated_argument_count") or 0) for row in records)
    non_surface_count = sum(int(row.get("non_surface_argument_count") or 0) for row in records)
    predicted_argument_count = sum(int(row.get("predicted_argument_count") or 0) for row in records)
    return {
        "bucket": bucket.name,
        "min_exclusive": bucket.min_exclusive,
        "max_inclusive": bucket.max_inclusive,
        "doc_count": doc_count,
        "length_min": min(int(row.get("length_value") or 0) for row in records),
        "length_max": max(int(row.get("length_value") or 0) for row in records),
        "length_mean": sum(int(row.get("length_value") or 0) for row in records) / doc_count,
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "event_table_micro_f1": _f1(tp, fp, fn),
        "parse_error_count": sum(1 for row in records if row.get("parse_error")),
        "parse_error_rate": _rate(sum(1 for row in records if row.get("parse_error")), doc_count),
        "schema_violation_rows": sum(1 for row in records if row.get("schema_violation")),
        "schema_violation_rate": _rate(sum(1 for row in records if row.get("schema_violation")), doc_count),
        "truncation_count": sum(1 for row in records if row.get("truncation")),
        "truncation_rate": _rate(sum(1 for row in records if row.get("truncation")), doc_count),
        "missing_event_count": sum(int(row.get("missing_event_count") or 0) for row in records),
        "missing_event_rate": _rate(sum(int(row.get("missing_event_count") or 0) for row in records), gold_event_count),
        "candidate_overflow_count": sum(1 for row in records if row.get("candidate_overflow")),
        "candidate_overflow_rate": _rate(sum(1 for row in records if row.get("candidate_overflow")), doc_count),
        "surface_recall": _rate(candidate_hits, gold_argument_count),
        "candidate_precision": _rate(candidate_precision_hits, selected_surface_count),
        "gold_argument_unlocated_rate": _rate(gold_unlocated_count, gold_argument_count),
        "ambiguous_match_rate": _rate(ambiguous_count, gold_argument_count),
        "hallucinated_argument_rate": _rate(hallucinated_count, predicted_argument_count),
        "non_surface_argument_rate": _rate(non_surface_count, predicted_argument_count),
        "gold_event_count": gold_event_count,
        "pred_event_count": pred_event_count,
        "gold_argument_count": gold_argument_count,
        "selected_surface_count": selected_surface_count,
        "candidate_hits": candidate_hits,
        "candidate_precision_hits": candidate_precision_hits,
        "gold_argument_unlocated_count": gold_unlocated_count,
        "ambiguous_match_count": ambiguous_count,
        "hallucinated_argument_count": hallucinated_count,
        "non_surface_argument_count": non_surface_count,
    }


def _failure_samples(doc_records: list[dict[str, Any]], limit: int = 12) -> list[dict[str, Any]]:
    ranked = []
    for row in doc_records:
        error_class = row.get("failure_class")
        if not error_class:
            continue
        severity = (
            FAILURE_CLASS_ORDER.index(error_class)
            if error_class in FAILURE_CLASS_ORDER
            else len(FAILURE_CLASS_ORDER)
        )
        ranked.append((severity, -int(row.get("length_value") or 0), str(row.get("doc_id") or ""), error_class))
    ranked.sort()
    samples = []
    seen: set[str] = set()
    for _, _, doc_id, error_class in ranked:
        if doc_id in seen:
            continue
        samples.append({"doc_id": doc_id, "error_class": error_class})
        seen.add(doc_id)
        if len(samples) >= limit:
            break
    return samples


def _failure_class(row: dict[str, Any]) -> str | None:
    if row.get("parse_error"):
        return "parse_error"
    if row.get("schema_violation"):
        return "schema_violation"
    if row.get("truncation"):
        return "truncation"
    if int(row.get("missing_event_count") or 0) > 0:
        return "missing_event"
    if row.get("candidate_overflow"):
        return "candidate_overflow"
    if row.get("surface_recall") is not None and float(row["surface_recall"]) < 0.25:
        return "low_surface_recall"
    if row.get("hallucinated_argument_rate") is not None and float(row["hallucinated_argument_rate"]) > 0:
        return "hallucinated_argument"
    if row.get("non_surface_argument_rate") is not None and float(row["non_surface_argument_rate"]) > 0:
        return "non_surface_argument"
    return None


def _read_evaluator_artifacts(artifact_root: str | Path | None, *, dataset: str, split: str) -> dict[str, Any]:
    if artifact_root is None:
        return {
            "event_table_micro_f1": None,
            "role_level_f1": None,
            "exact_record_f1": None,
            "validation_ok": None,
            "artifact_root": None,
            "per_document_metrics": [],
        }
    root = Path(artifact_root)
    overall_path = root / "metrics" / "unified_main" / dataset / split / "overall_metrics.json"
    record_path = root / "analysis" / dataset / split / "record_level_metrics.json"
    validation_path = root / "analysis" / dataset / split / "validation_report.json"
    per_document_path = root / "analysis" / dataset / split / "per_document_metrics.csv"
    overall = _read_json(overall_path) if overall_path.is_file() else {}
    record = _read_json(record_path) if record_path.is_file() else {}
    validation = _read_json(validation_path) if validation_path.is_file() else {}
    per_document = _read_csv(per_document_path) if per_document_path.is_file() else []
    return {
        "event_table_micro_f1": overall.get("f1"),
        "role_level_f1": overall.get("f1"),
        "exact_record_f1": record.get("record_f1_exact"),
        "validation_ok": validation.get("ok"),
        "artifact_root": str(root),
        "per_document_metrics": per_document,
    }


def _read_json(path: str | Path) -> dict[str, Any]:
    with Path(path).open(encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object: {path}")
    return payload


def _read_csv(path: str | Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with Path(path).open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            rows.append(dict(row))
    return rows


def _index_rows(rows: list[dict[str, Any]], key: str) -> dict[str, dict[str, Any]]:
    indexed: dict[str, dict[str, Any]] = {}
    for row in rows:
        value = str(row.get(key) or "").strip()
        if value:
            indexed[value] = row
    return indexed


def _bucket_for_length(value: int, *, length_buckets: Sequence[LengthBucketSpec]) -> LengthBucketSpec:
    for bucket in length_buckets:
        if bucket.matches(value):
            return bucket
    return length_buckets[-1]


def _f1(tp: int, fp: int, fn: int) -> float | None:
    if tp + fp == 0 or tp + fn == 0:
        return None
    precision = tp / (tp + fp)
    recall = tp / (tp + fn)
    return 2 * precision * recall / (precision + recall) if precision + recall else None


def _as_int(value: Any) -> int | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _schema_violation_count(parse_diagnostics: dict[str, Any]) -> int:
    return _as_int((parse_diagnostics.get("diagnostic_counts") or {}).get("schema_violation")) or 0


def _truncation_value(analysis: dict[str, Any], key: str) -> Any:
    return (analysis.get("truncation_diagnostics") or {}).get(key)


def _format_number(value: Any) -> str:
    if value is None:
        return "pending"
    if isinstance(value, (int, float)):
        return f"{value:.6f}" if isinstance(value, float) else str(value)
    return str(value)


def _write_json(path: str | Path, payload: dict[str, Any]) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return target
