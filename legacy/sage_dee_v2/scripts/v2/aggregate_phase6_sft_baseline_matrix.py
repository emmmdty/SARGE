from __future__ import annotations

import argparse
import json
import statistics
import sys
from collections.abc import Iterable, Sequence
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))


BASELINE_IDS = ("S1", "S2", "S3", "S4")
METRIC_KEYS = ("event_table_micro_f1", "role_level_f1", "exact_record_f1")


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    stage_key = _stage_key(args.stage)
    summaries = _load_run_summaries(args.runs_root)
    aggregate = aggregate_phase6_runs(summaries, stage_key=stage_key)
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(
        json.dumps(aggregate, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"aggregate_json={args.out_json}")
    return 0


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Aggregate SAGE v2 Phase 6 SFT baseline matrix metrics.")
    parser.add_argument("--runs-root", type=Path, required=True)
    parser.add_argument("--stage", choices=("limit50", "full-dev", "full_dev"), default="full-dev")
    parser.add_argument("--out-json", type=Path, required=True)
    return parser.parse_args(argv)


def aggregate_phase6_runs(summaries: list[dict[str, Any]], *, stage_key: str) -> dict[str, Any]:
    summaries = _latest_summary_by_seed(summaries)
    rows = [_metric_row(summary, stage_key=stage_key) for summary in summaries]
    by_baseline: dict[str, Any] = {}
    for baseline_id in BASELINE_IDS:
        baseline_rows = [row for row in rows if row["baseline_id"] == baseline_id]
        by_baseline[baseline_id] = _baseline_stats(baseline_rows)
    gate = _gate(by_baseline)
    return {
        "stage": stage_key,
        "run_count": len(rows),
        "by_baseline": by_baseline,
        "runs": rows,
        "gate": gate,
    }


def _load_run_summaries(runs_root: Path) -> list[dict[str, Any]]:
    paths = sorted(runs_root.glob("phase6_*_seed*/phase6_run_summary.json"))
    if not paths:
        raise SystemExit(f"no phase6_run_summary.json files found under {runs_root}")
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
        baseline_id = str(summary.get("baseline_id") or "")
        seed = summary.get("seed")
        if not isinstance(seed, int):
            continue
        key = (baseline_id, seed)
        if key not in latest or _summary_sort_key(summary) > _summary_sort_key(latest[key]):
            latest[key] = summary
    return sorted(latest.values(), key=lambda summary: (str(summary.get("baseline_id") or ""), int(summary["seed"])))


def _summary_sort_key(summary: dict[str, Any]) -> str:
    return Path(str(summary.get("run_dir") or "")).name


def _metric_row(summary: dict[str, Any], *, stage_key: str) -> dict[str, Any]:
    stage = summary.get(stage_key) or {}
    parse_valid = stage.get("parse_valid_subset") or {}
    return {
        "baseline_id": str(summary.get("baseline_id") or ""),
        "seed": summary.get("seed"),
        "run_dir": summary.get("run_dir"),
        "event_table_micro_f1": _number(stage.get("event_table_micro_f1")),
        "role_level_f1": _number(stage.get("role_level_f1")),
        "exact_record_f1": _number(stage.get("exact_record_f1")),
        "parse_valid_subset_event_table_micro_f1": _number(parse_valid.get("event_table_micro_f1")),
        "parse_valid_subset_role_level_f1": _number(parse_valid.get("role_level_f1")),
        "parse_valid_subset_exact_record_f1": _number(parse_valid.get("exact_record_f1")),
        "parse_valid_subset_doc_count": parse_valid.get("doc_count"),
        "test_used": bool((summary.get("scope") or {}).get("test_used")),
        "full_train_used": bool((summary.get("scope") or {}).get("full_train_used")),
    }


def _baseline_stats(rows: list[dict[str, Any]]) -> dict[str, Any]:
    payload: dict[str, Any] = {"seed_count": len(rows), "seeds": [row.get("seed") for row in rows]}
    for key in (
        *METRIC_KEYS,
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


def _gate(by_baseline: dict[str, Any]) -> dict[str, Any]:
    s4 = _mean(by_baseline, "S4", "event_table_micro_f1")
    s1 = _mean(by_baseline, "S1", "event_table_micro_f1")
    s2 = _mean(by_baseline, "S2", "event_table_micro_f1")
    s4_not_below_s1_s2 = (
        s4 is not None
        and s1 is not None
        and s2 is not None
        and s4 >= s1
        and s4 >= s2
    )
    full_metric_improved = _improved_against_s1_s2(
        by_baseline,
        "event_table_micro_f1",
    ) or _improved_against_s1_s2(by_baseline, "role_level_f1")
    parse_valid_subset_improved = _improved_against_s1_s2(
        by_baseline,
        "parse_valid_subset_event_table_micro_f1",
    ) or _improved_against_s1_s2(by_baseline, "parse_valid_subset_role_level_f1")
    return {
        "s4_not_below_s1_s2": bool(s4_not_below_s1_s2),
        "parse_valid_subset_improved": bool(parse_valid_subset_improved),
        "parse_only_improvement": bool(full_metric_improved and not parse_valid_subset_improved),
        "test_blocked": not any(by_baseline[baseline].get("test_used") for baseline in by_baseline),
        "full_train_blocked": not any(
            by_baseline[baseline].get("full_train_used") for baseline in by_baseline
        ),
    }


def _improved_against_s1_s2(by_baseline: dict[str, Any], metric_key: str) -> bool:
    s4 = _mean(by_baseline, "S4", metric_key)
    s1 = _mean(by_baseline, "S1", metric_key)
    s2 = _mean(by_baseline, "S2", metric_key)
    if s4 is None or s1 is None or s2 is None:
        return False
    return s4 > max(s1, s2)


def _mean(by_baseline: dict[str, Any], baseline_id: str, metric_key: str) -> float | None:
    return _number(((by_baseline.get(baseline_id) or {}).get(metric_key) or {}).get("mean"))


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
