from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PASS_THROUGH = "pass_through"
PROMISING_EXACT_DELTA = 0.02
PROMISING_EVENT_ROLE_FLOOR = -0.01
REGRESSION_EXACT_DELTA = -0.005
REGRESSION_EVENT_ROLE_DELTA = -0.02


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        summary = aggregate_r4b(args.run_root)
    except (OSError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_md.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    args.out_md.write_text(render_markdown(summary), encoding="utf-8")
    print(f"summary_json={args.out_json}")
    print(f"summary_md={args.out_md}")
    return 0


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Aggregate SAGE v2.1 R4b event planner probe outputs.")
    parser.add_argument("--run-root", type=Path, required=True)
    parser.add_argument("--out-json", type=Path, required=True)
    parser.add_argument("--out-md", type=Path, required=True)
    return parser.parse_args(argv)


def aggregate_r4b(run_root: Path) -> dict[str, Any]:
    manifest_path = run_root / "run_manifest.json"
    if not manifest_path.is_file():
        raise ValueError(f"missing R4b run manifest: {manifest_path}")
    manifest = _read_json(manifest_path)
    variants = _load_variants(run_root, manifest)
    if PASS_THROUGH not in variants:
        raise ValueError("R4b aggregate requires pass_through reference")
    variant_table = [
        _variant_row(variant, payload, baseline=variants[PASS_THROUGH])
        for variant, payload in variants.items()
    ]
    verdict = _machine_verdict(variant_table)
    return {
        "phase": "R4b event planner / record assembler dev probe",
        "created_at": _created_at(),
        "run_root": str(run_root),
        "dataset": manifest.get("dataset"),
        "split": manifest.get("split"),
        "source_prediction_path": manifest.get("source_prediction_path"),
        "source_prediction_unchanged": manifest.get("source_prediction_unchanged") is True,
        "scope": manifest.get("scope"),
        "oracle_diagnostics": manifest.get("oracle_diagnostics"),
        "variant_comparison": variant_table,
        "machine_readable_verdict": verdict,
        "dev_only_non_performance": True,
    }


def render_markdown(summary: dict[str, Any]) -> str:
    verdict = summary["machine_readable_verdict"]
    lines = [
        "# R4b Event Planner Probe Summary",
        "",
        "## Scope",
        "",
        "- dev-only non-oracle method probe plus separated oracle diagnostics.",
        "- No Qwen, no training, no test split, no gold in non-oracle planner.",
        "- Source R3 prediction is read only.",
        "",
        "## Variant Comparison",
        "",
        (
            "| Variant | Event/role F1 | Exact-record F1 | Exact delta | Event-count acc | "
            "Events | Changed docs | Decisions | Merge | Split | Dedup | Drop |"
        ),
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in summary.get("variant_comparison") or []:
        lines.append(
            "| {variant} | {role} | {exact} | {delta} | {event_count} | {events} | {changed} | "
            "{decisions} | {merge} | {split} | {dedup} | {drop} |".format(
                variant=row.get("variant"),
                role=_fmt(row.get("event_role_f1")),
                exact=_fmt(row.get("exact_record_f1")),
                delta=_fmt(row.get("exact_record_delta")),
                event_count=_fmt(row.get("event_count_acc")),
                events=row.get("canonical_event_count"),
                changed=row.get("changed_doc_count"),
                decisions=row.get("applied_decisions_count"),
                merge=row.get("planner_merge_count"),
                split=row.get("planner_split_count"),
                dedup=row.get("planner_dedup_count"),
                drop=row.get("planner_dropped_count"),
            )
        )
    lines.extend(
        [
            "",
            "## Verdict",
            "",
            f"- best_non_oracle_variant: `{verdict['best_non_oracle_variant']}`",
            f"- exact_record_delta: `{_fmt(verdict['exact_record_delta'])}`",
            f"- event_role_delta: `{_fmt(verdict['event_role_delta'])}`",
            f"- event_planner_promising: `{verdict['event_planner_promising']}`",
            f"- recommended_next_phase: `{verdict['recommended_next_phase']}`",
            "",
            "## Oracle Diagnostics",
            "",
            "- Label: `dev_only_non_performance`; oracle values are diagnostics, not method scores.",
            "",
        ]
    )
    return "\n".join(lines)


def _load_variants(run_root: Path, manifest: dict[str, Any]) -> dict[str, dict[str, Any]]:
    variant_names = [str(item) for item in manifest.get("variants") or []]
    if not variant_names:
        variant_names = sorted(path.parent.name for path in run_root.glob("*/variant_summary.json"))
    variants: dict[str, dict[str, Any]] = {}
    for variant in variant_names:
        path = run_root / variant / "variant_summary.json"
        if not path.is_file():
            raise ValueError(f"missing R4b variant summary: {path}")
        variants[variant] = _read_json(path)
    return variants


def _variant_row(variant: str, payload: dict[str, Any], *, baseline: dict[str, Any]) -> dict[str, Any]:
    evaluator = payload.get("evaluator") or {}
    baseline_evaluator = baseline.get("evaluator") or {}
    diagnostics = payload.get("planner_diagnostics") or {}
    role_f1 = _number(evaluator.get("role_level_f1"), evaluator.get("event_table_micro_f1"))
    baseline_role = _number(baseline_evaluator.get("role_level_f1"), baseline_evaluator.get("event_table_micro_f1"))
    exact_f1 = _number(evaluator.get("exact_record_f1"))
    baseline_exact = _number(baseline_evaluator.get("exact_record_f1"))
    return {
        "variant": variant,
        "event_role_f1": role_f1,
        "exact_record_f1": exact_f1,
        "event_count_acc": _number(evaluator.get("event_count_acc")),
        "merge_count": evaluator.get("merge_count"),
        "split_count": evaluator.get("split_count"),
        "wrong_grouping_count": evaluator.get("wrong_grouping_count"),
        "canonical_event_count": payload.get("canonical_event_count"),
        "changed_doc_count": payload.get("changed_doc_count"),
        "applied_decisions_count": diagnostics.get("applied_count"),
        "planner_merge_count": diagnostics.get("merge_count"),
        "planner_split_count": diagnostics.get("split_count"),
        "planner_dedup_count": diagnostics.get("dedup_count"),
        "planner_dropped_count": diagnostics.get("dropped_count"),
        "per_event_type_effect": diagnostics.get("per_event_type_effect") or {},
        "exact_record_delta": _delta(exact_f1, baseline_exact),
        "event_role_delta": _delta(role_f1, baseline_role),
    }


def _machine_verdict(variant_table: list[dict[str, Any]]) -> dict[str, Any]:
    baseline = _find_variant(variant_table, PASS_THROUGH)
    best = max(
        variant_table,
        key=lambda row: (
            _number(row.get("exact_record_f1")) if _number(row.get("exact_record_f1")) is not None else -1.0,
            row.get("variant") != PASS_THROUGH,
        ),
    )
    exact_delta = _delta(_number(best.get("exact_record_f1")), _number(baseline.get("exact_record_f1"))) or 0.0
    event_role_delta = _delta(_number(best.get("event_role_f1")), _number(baseline.get("event_role_f1"))) or 0.0
    promising = exact_delta >= PROMISING_EXACT_DELTA and event_role_delta >= PROMISING_EVENT_ROLE_FLOOR
    if promising:
        next_phase = "R4c_planner_refine_dev_only"
    elif exact_delta <= REGRESSION_EXACT_DELTA or event_role_delta <= REGRESSION_EVENT_ROLE_DELTA:
        next_phase = "stop_v2_1"
    else:
        next_phase = "R5_decision_report"
    return {
        "best_non_oracle_variant": best.get("variant"),
        "exact_record_delta": exact_delta,
        "event_role_delta": event_role_delta,
        "event_planner_promising": promising,
        "recommended_next_phase": next_phase,
    }


def _find_variant(rows: list[dict[str, Any]], variant: str) -> dict[str, Any]:
    for row in rows:
        if row.get("variant") == variant:
            return row
    raise ValueError(f"missing variant: {variant}")


def _delta(value: float | None, baseline: float | None) -> float | None:
    if value is None or baseline is None:
        return None
    return round(value - baseline, 12)


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
    if number is None:
        return "NA"
    return f"{number:.6f}"


def _read_json(path: str | Path) -> dict[str, Any]:
    with Path(path).open(encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must load as a mapping")
    return payload


def _created_at() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


if __name__ == "__main__":
    raise SystemExit(main())
