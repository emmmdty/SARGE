from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

GROUPING_HIGH_GAP = 0.25
GROUPING_MEDIUM_GAP = 0.10
EVENT_COUNT_HIGH_ACC = 0.65
EVENT_COUNT_MEDIUM_ACC = 0.80
ROLE_VALUE_HIGH_F1 = 0.60
ROLE_VALUE_MEDIUM_F1 = 0.75


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        summary = aggregate_r4(args.run_root)
    except (OSError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2

    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_md.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    args.out_md.write_text(render_markdown(summary), encoding="utf-8")
    print(f"summary_json={args.out_json}")
    print(f"summary_md={args.out_md}")
    return 0


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Aggregate SAGE v2.1 R4 event grouping probe diagnostics.")
    parser.add_argument("--run-root", type=Path, required=True)
    parser.add_argument("--out-json", type=Path, required=True)
    parser.add_argument("--out-md", type=Path, required=True)
    return parser.parse_args(argv)


def aggregate_r4(run_root: Path) -> dict[str, Any]:
    analysis_path = run_root / "r4_event_grouping_analysis.json"
    if not analysis_path.is_file():
        raise ValueError(f"missing R4 analysis JSON: {analysis_path}")
    analysis = _read_json(analysis_path)
    verdict = _machine_verdict(analysis)
    return {
        "phase": "R4 event planning/grouping probe",
        "created_at": _created_at(),
        "run_root": str(run_root),
        "analysis_path": str(analysis_path),
        "dataset": analysis.get("dataset"),
        "split": analysis.get("split"),
        "primary_row": analysis.get("primary_row"),
        "scope": analysis.get("scope"),
        "overall_metrics": analysis.get("overall_metrics"),
        "event_count_diagnostics": analysis.get("event_count_diagnostics"),
        "record_level_decomposition": analysis.get("record_level_decomposition"),
        "oracle_diagnostics": analysis.get("oracle_diagnostics"),
        "train_size_progression": analysis.get("train_size_progression"),
        "role_value_residual_summary": _role_value_summary(analysis),
        "event_type_residual_summary": _event_type_summary(analysis),
        "machine_readable_verdict": verdict,
        "dev_only_non_performance": True,
    }


def render_markdown(summary: dict[str, Any]) -> str:
    verdict = summary["machine_readable_verdict"]
    oracle = summary.get("oracle_diagnostics") or {}
    event_count = summary.get("event_count_diagnostics") or {}
    record = summary.get("record_level_decomposition") or {}
    primary = summary.get("primary_row") or {}
    progression = summary.get("train_size_progression") or []
    lines = [
        "# R4 Event Grouping Probe Summary",
        "",
        "## Scope",
        "",
        "- dev-only non-performance diagnostics.",
        "- No Qwen, no training, no evaluator rerun, no test split.",
        "- Existing R3 dev evaluator artifacts are read only.",
        "",
        "## Primary Row",
        "",
        f"- row_id: `{primary.get('row_id')}`",
        f"- train_limit: `{primary.get('train_limit')}`",
        f"- event/role F1: `{_fmt(primary.get('role_level_f1') or primary.get('event_table_micro_f1'))}`",
        f"- exact-record F1: `{_fmt(primary.get('exact_record_f1'))}`",
        "",
        "## Verdict",
        "",
        f"- Grouping bottleneck: `{verdict['grouping_bottleneck']}`",
        f"- Event-count bottleneck: `{verdict['event_count_bottleneck']}`",
        f"- Role/value bottleneck: `{verdict['role_value_bottleneck']}`",
        f"- Need event planner: `{verdict['need_event_planner']}`",
        f"- Full train enough for thesis: `{verdict['full_train_enough_for_thesis']}`",
        f"- Recommended next phase: `{verdict['recommended_next_phase']}`",
        "",
        "## Oracle-Style Dev Diagnostics",
        "",
        f"- label: `{oracle.get('label')}`",
        f"- role_level_f1 - exact_record_f1: `{_fmt(oracle.get('role_level_minus_exact_record'))}`",
        f"- grouping flag: `{oracle.get('grouping_bottleneck_flag')}`",
        (
            "- soft record F1 proxy: "
            f"`{_fmt((oracle.get('oracle_grouping_upper_bound') or {}).get('record_f1_soft_0_8'))}`"
        ),
        "",
        "## Event Count",
        "",
        f"- event_count_acc: `{_fmt(event_count.get('event_count_acc'))}`",
        f"- under-predicted docs: `{event_count.get('under_predicted_doc_count')}`",
        f"- over-predicted docs: `{event_count.get('over_predicted_doc_count')}`",
        f"- exact count match docs: `{event_count.get('exact_event_count_match_doc_count')}`",
        "",
        "## Record Decomposition",
        "",
        (
            "- exact TP/FP/FN: "
            f"`{record.get('record_exact_tp')}/{record.get('record_exact_fp')}/"
            f"{record.get('record_exact_fn')}`"
        ),
        (
            "- merge/split/wrong grouping: "
            f"`{record.get('merge_count')}/{record.get('split_count')}/"
            f"{record.get('wrong_grouping_count')}`"
        ),
        f"- partially correct records: `{record.get('partially_correct_record_count')}`",
        "",
        "## Train-Size Progression",
        "",
        (
            "| Row | Train limit | Event/role F1 | Exact-record F1 | Event-count acc | "
            "Merge | Split | Wrong grouping | Events | Parse errors |"
        ),
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in progression:
        lines.append(
            "| {row_id} | {train_limit} | {event_f1} | {exact_f1} | {event_count_acc} | "
            "{merge} | {split} | {wrong} | {events} | {parse} |".format(
                row_id=row.get("row_id"),
                train_limit=row.get("train_limit"),
                event_f1=_fmt(row.get("event_role_f1")),
                exact_f1=_fmt(row.get("exact_record_f1")),
                event_count_acc=_fmt(row.get("event_count_acc")),
                merge=row.get("merge_count"),
                split=row.get("split_count"),
                wrong=row.get("wrong_grouping_count"),
                events=row.get("canonical_event_count"),
                parse=row.get("parse_error"),
            )
        )
    lines.append("")
    return "\n".join(lines)


def _machine_verdict(analysis: dict[str, Any]) -> dict[str, Any]:
    primary = analysis.get("primary_row") or {}
    event_count = analysis.get("event_count_diagnostics") or {}
    role_value = analysis.get("role_value_diagnostics") or {}
    oracle = analysis.get("oracle_diagnostics") or {}

    gap = _number(oracle.get("role_level_minus_exact_record")) or 0.0
    event_count_acc = _number(event_count.get("event_count_acc"))
    role_f1 = _number(primary.get("role_level_f1"), primary.get("event_table_micro_f1")) or 0.0
    exact_f1 = _number(primary.get("exact_record_f1")) or 0.0
    low_role_count = len(role_value.get("roles_still_below_0_3_f1") or [])

    grouping = _grouping_bottleneck(gap)
    event_count_label = _event_count_bottleneck(event_count_acc)
    role_value_label = _role_value_bottleneck(role_f1, low_role_count)
    need_planner = grouping == "high" or event_count_label == "high" or (
        event_count_label == "medium" and grouping in {"medium", "high"}
    )
    full_train_enough = not (exact_f1 < 0.50 or grouping == "high")
    if need_planner:
        next_phase = "R4b_event_planner_dev_probe"
    elif role_value_label == "high":
        next_phase = "R3_seed_extension"
    else:
        next_phase = "R5_decision_report"
    return {
        "grouping_bottleneck": grouping,
        "event_count_bottleneck": event_count_label,
        "role_value_bottleneck": role_value_label,
        "need_event_planner": need_planner,
        "full_train_enough_for_thesis": full_train_enough,
        "recommended_next_phase": next_phase,
    }


def _role_value_summary(analysis: dict[str, Any]) -> dict[str, Any]:
    role_value = analysis.get("role_value_diagnostics") or {}
    return {
        "low_recall_roles_top20": role_value.get("top_20_low_recall_roles") or [],
        "low_precision_roles_top20": role_value.get("top_20_low_precision_roles") or [],
        "roles_still_below_0_3_f1": role_value.get("roles_still_below_0_3_f1") or [],
        "roles_improved_most_from_512_to_full": role_value.get("roles_improved_most_from_512_to_full") or [],
        "r2_coverage_joined": role_value.get("r2_coverage_joined") is True,
    }


def _event_type_summary(analysis: dict[str, Any]) -> dict[str, Any]:
    event_type = analysis.get("event_type_residual_errors") or {}
    return {
        "event_types_still_low_after_full": event_type.get("event_types_still_low_after_full") or [],
        "event_types_improved_most_from_512_to_full": (
            event_type.get("event_types_improved_most_from_512_to_full") or []
        ),
        "event_types_with_high_merge_split_wrong_grouping": event_type.get(
            "event_types_with_high_merge_split_wrong_grouping"
        )
        or [],
        "event_types_likely_requiring_event_planner": event_type.get("event_types_likely_requiring_event_planner")
        or [],
    }


def _grouping_bottleneck(gap: float) -> str:
    if gap >= GROUPING_HIGH_GAP:
        return "high"
    if gap >= GROUPING_MEDIUM_GAP:
        return "medium"
    return "low"


def _event_count_bottleneck(event_count_acc: float | None) -> str:
    if event_count_acc is None:
        return "medium"
    if event_count_acc < EVENT_COUNT_HIGH_ACC:
        return "high"
    if event_count_acc < EVENT_COUNT_MEDIUM_ACC:
        return "medium"
    return "low"


def _role_value_bottleneck(role_f1: float, low_role_count: int) -> str:
    if role_f1 < ROLE_VALUE_HIGH_F1:
        return "high"
    if role_f1 < ROLE_VALUE_MEDIUM_F1 or low_role_count > 0:
        return "medium"
    return "low"


def _number(*values: Any) -> float | None:
    for value in values:
        if isinstance(value, bool) or value is None:
            continue
        try:
            return float(value)
        except (TypeError, ValueError):
            continue
    return None


def _fmt(value: Any) -> str:
    number = _number(value)
    return "NA" if number is None else f"{number:.6f}"


def _read_json(path: str | Path) -> dict[str, Any]:
    with Path(path).open(encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object: {path}")
    return payload


def _created_at() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


if __name__ == "__main__":
    raise SystemExit(main())
