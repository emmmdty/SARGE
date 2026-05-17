from __future__ import annotations

import argparse
import json
import statistics
from collections.abc import Iterable, Sequence
from pathlib import Path
from typing import Any

VARIANT_ORDER = (
    "no_surface",
    "raw_surface",
    "compressed_surface",
    "low_k",
    "high_k",
    "no_compression",
)
METRIC_KEYS = ("event_table_micro_f1", "role_level_f1", "exact_record_f1")
GROUNDING_KEYS = (
    "candidate_precision",
    "gold_argument_unlocated_rate",
    "ambiguous_match_rate",
    "hallucinated_argument_rate",
    "non_surface_argument_rate",
)
RECALL_KS = ("1", "5", "10", "20")


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    stage_key = _stage_key(args.stage)
    summaries = _load_run_summaries(args.runs_root)
    aggregate = aggregate_phase7_runs(summaries, stage_key=stage_key)
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(
        json.dumps(aggregate, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"aggregate_json={args.out_json}")
    print(f"claim_status={aggregate['gate']['claim_status']}")
    return 0


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Aggregate SAGE v2 Phase 7 surface-memory ablation metrics.")
    parser.add_argument("--runs-root", type=Path, required=True)
    parser.add_argument("--stage", choices=("limit50", "full-dev", "full_dev"), default="full-dev")
    parser.add_argument("--out-json", type=Path, required=True)
    return parser.parse_args(argv)


def aggregate_phase7_runs(summaries: list[dict[str, Any]], *, stage_key: str) -> dict[str, Any]:
    summaries = _latest_summary_by_seed(summaries)
    rows = [_metric_row(summary, stage_key=stage_key) for summary in summaries]
    by_variant: dict[str, Any] = {}
    for variant_id in VARIANT_ORDER:
        variant_rows = [row for row in rows if row["variant_id"] == variant_id]
        by_variant[variant_id] = _variant_stats(variant_rows)
    gate = _gate(by_variant)
    return {
        "stage": stage_key,
        "run_count": len(rows),
        "by_variant": by_variant,
        "runs": rows,
        "gate": gate,
    }


def _load_run_summaries(runs_root: Path) -> list[dict[str, Any]]:
    paths = sorted(runs_root.glob("phase7_*_seed*/phase7_run_summary.json"))
    if not paths:
        raise SystemExit(f"no phase7_run_summary.json files found under {runs_root}")
    summaries = []
    for path in paths:
        with path.open(encoding="utf-8") as handle:
            payload = json.load(handle)
        if isinstance(payload, dict):
            summaries.append(payload)
    return summaries


def _latest_summary_by_seed(summaries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    latest: dict[tuple[str, int], dict[str, Any]] = {}
    for summary in summaries:
        variant_id = str(summary.get("variant_id") or "")
        seed = summary.get("seed")
        if not isinstance(seed, int):
            continue
        key = (variant_id, seed)
        if key not in latest or _summary_sort_key(summary) > _summary_sort_key(latest[key]):
            latest[key] = summary
    return sorted(latest.values(), key=lambda summary: (str(summary.get("variant_id") or ""), int(summary["seed"])))


def _summary_sort_key(summary: dict[str, Any]) -> str:
    return Path(str(summary.get("run_dir") or "")).name


def _metric_row(summary: dict[str, Any], *, stage_key: str) -> dict[str, Any]:
    stage = summary.get(stage_key) or {}
    grounding = stage.get("grounding_diagnostics") or {}
    parse_valid = stage.get("parse_valid_subset") or {}
    row = {
        "variant_id": str(summary.get("variant_id") or ""),
        "seed": summary.get("seed"),
        "run_dir": summary.get("run_dir"),
        "event_table_micro_f1": _number(stage.get("event_table_micro_f1")),
        "role_level_f1": _number(stage.get("role_level_f1")),
        "exact_record_f1": _number(stage.get("exact_record_f1")),
        "parse_valid_subset_event_table_micro_f1": _number(parse_valid.get("event_table_micro_f1")),
        "parse_valid_subset_role_level_f1": _number(parse_valid.get("role_level_f1")),
        "parse_valid_subset_exact_record_f1": _number(parse_valid.get("exact_record_f1")),
        "parse_valid_subset_doc_count": parse_valid.get("doc_count"),
        "candidate_precision": _number(grounding.get("candidate_precision")),
        "gold_argument_unlocated_rate": _number(grounding.get("gold_argument_unlocated_rate")),
        "ambiguous_match_rate": _number(grounding.get("ambiguous_match_rate")),
        "hallucinated_argument_rate": _number(grounding.get("hallucinated_argument_rate")),
        "non_surface_argument_rate": _number(grounding.get("non_surface_argument_rate")),
        "gold_argument_count": grounding.get("gold_argument_count"),
        "selected_candidate_count": grounding.get("selected_candidate_count"),
        "predicted_argument_count": grounding.get("predicted_argument_count"),
        "test_used": bool((summary.get("scope") or {}).get("test_used")),
        "full_train_used": bool((summary.get("scope") or {}).get("full_train_used")),
    }
    recall_at_k = grounding.get("candidate_recall_at_k") or {}
    for k in RECALL_KS:
        row[f"candidate_recall_at_{k}"] = _number(recall_at_k.get(k))
    return row


def _variant_stats(rows: list[dict[str, Any]]) -> dict[str, Any]:
    payload: dict[str, Any] = {"seed_count": len(rows), "seeds": [row.get("seed") for row in rows]}
    for key in (
        *METRIC_KEYS,
        "parse_valid_subset_event_table_micro_f1",
        "parse_valid_subset_role_level_f1",
        "parse_valid_subset_exact_record_f1",
        *GROUNDING_KEYS,
        *(f"candidate_recall_at_{k}" for k in RECALL_KS),
        "gold_argument_count",
        "selected_candidate_count",
        "predicted_argument_count",
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
    payload["test_used"] = any(row.get("test_used") for row in rows)
    payload["full_train_used"] = any(row.get("full_train_used") for row in rows)
    return payload


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


def _gate(by_variant: dict[str, Any]) -> dict[str, Any]:
    compressed_event = _mean(by_variant, "compressed_surface", "event_table_micro_f1")
    compressed_role = _mean(by_variant, "compressed_surface", "role_level_f1")
    no_surface_event = _mean(by_variant, "no_surface", "event_table_micro_f1")
    no_surface_role = _mean(by_variant, "no_surface", "role_level_f1")
    compressed_hallucination = _mean(by_variant, "compressed_surface", "hallucinated_argument_rate")
    no_surface_hallucination = _mean(by_variant, "no_surface", "hallucinated_argument_rate")
    compressed_non_surface = _mean(by_variant, "compressed_surface", "non_surface_argument_rate")
    no_surface_non_surface = _mean(by_variant, "no_surface", "non_surface_argument_rate")

    event_improved = _greater(compressed_event, no_surface_event)
    role_improved = _greater(compressed_role, no_surface_role)
    strict_f1_improved = event_improved or role_improved
    strict_f1_worse = _less(compressed_event, no_surface_event) and _less(compressed_role, no_surface_role)
    hallucination_not_worse = not _greater(compressed_hallucination, no_surface_hallucination)
    non_surface_not_worse = not _greater(compressed_non_surface, no_surface_non_surface)

    if strict_f1_worse:
        claim_status = "delete"
    elif strict_f1_improved and hallucination_not_worse and non_surface_not_worse:
        claim_status = "retain"
    else:
        claim_status = "downgrade"

    return {
        "claim_status": claim_status,
        "surface_memory_main_contribution": claim_status == "retain",
        "diagnostic_only": claim_status == "downgrade",
        "delete_surface_memory_claim": claim_status == "delete",
        "compressed_event_table_micro_f1_improved_vs_no_surface": bool(event_improved),
        "compressed_role_level_f1_improved_vs_no_surface": bool(role_improved),
        "hallucination_only_gain_is_main_claim": False,
        "hallucination_not_worse": bool(hallucination_not_worse),
        "non_surface_not_worse": bool(non_surface_not_worse),
        "test_blocked": not any(by_variant[variant].get("test_used") for variant in by_variant),
        "full_train_blocked": not any(by_variant[variant].get("full_train_used") for variant in by_variant),
    }


def _mean(by_variant: dict[str, Any], variant_id: str, metric_key: str) -> float | None:
    return _number(((by_variant.get(variant_id) or {}).get(metric_key) or {}).get("mean"))


def _greater(left: float | None, right: float | None) -> bool:
    return left is not None and right is not None and left > right


def _less(left: float | None, right: float | None) -> bool:
    return left is not None and right is not None and left < right


def _number(value: Any) -> float | None:
    if isinstance(value, bool) or value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _stage_key(stage: str) -> str:
    return "full_dev" if stage in {"full-dev", "full_dev"} else "limit50"


if __name__ == "__main__":
    raise SystemExit(main())
