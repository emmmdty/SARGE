from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))

from sage_dee.v2.data_interface.dataset_loader import load_documents  # noqa: E402
from sage_dee.v2.data_interface.jsonl import write_jsonl  # noqa: E402
from sage_dee.v2.data_interface.schema_registry import load_schema  # noqa: E402
from sage_dee.v2.lesp.audit import audit_slot_plans  # noqa: E402
from sage_dee.v2.lesp.baseline_planner import SchemaEmptyPlanner, TrainPriorPlanner  # noqa: E402
from sage_dee.v2.lesp.slot_plan import slot_plan_to_dict  # noqa: E402


def main(argv: Sequence[str] | None = None) -> None:
    args = parse_args(argv)
    out_dir = args.out_dir or Path("artifacts") / "v2" / "slot_plan" / args.dataset / args.split / args.planner
    schema = load_schema(args.dataset, data_root=args.data_root)
    predict_documents = load_documents(args.dataset, args.split, data_root=args.data_root, mode="predict")
    planner = _build_planner(args.planner, schema, args.dataset, args.data_root)
    plans = planner.predict(predict_documents)

    out_dir.mkdir(parents=True, exist_ok=True)
    slot_plan_path = write_jsonl(out_dir / "slot_plan.jsonl", [slot_plan_to_dict(plan) for plan in plans])
    audit = audit_slot_plans(plans, schema)
    audit_path = out_dir / "slot_plan_audit.json"
    with audit_path.open("w", encoding="utf-8") as handle:
        json.dump(audit, handle, ensure_ascii=False, indent=2)
        handle.write("\n")

    summary = _planner_summary(args.planner, planner, len(predict_documents), audit)
    summary_path = out_dir / "planner_summary.json"
    with summary_path.open("w", encoding="utf-8") as handle:
        json.dump(summary, handle, ensure_ascii=False, indent=2)
        handle.write("\n")

    print(f"slot_plan={slot_plan_path}")
    print(f"slot_plan_audit={audit_path}")
    print(f"planner_summary={summary_path}")
    print("summary=" + json.dumps(summary, ensure_ascii=False, sort_keys=True))


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Predict SAGE-DEE v2 LESP slot plans.")
    parser.add_argument("--dataset", required=True)
    parser.add_argument("--split", required=True)
    parser.add_argument("--planner", choices=("schema_empty", "train_prior"), required=True)
    parser.add_argument("--data-root", default="data")
    parser.add_argument("--out-dir", type=Path)
    return parser.parse_args(argv)


def _build_planner(planner_name: str, schema, dataset: str, data_root: str):
    if planner_name == "schema_empty":
        return SchemaEmptyPlanner(schema)
    if planner_name == "train_prior":
        train_documents = load_documents(dataset, "train", data_root=data_root, mode="train")
        return TrainPriorPlanner.fit(schema, train_documents)
    raise ValueError(f"unknown planner: {planner_name}")


def _planner_summary(planner_name: str, planner, document_count: int, audit: dict[str, object]) -> dict[str, object]:
    summary: dict[str, object] = {
        "planner": planner_name,
        "predict_document_count": document_count,
        "slot_count_total": audit["slot_count_total"],
        "invalid_plan_count": audit["invalid_plan_count"],
        "forbidden_key_violation_count": audit["forbidden_key_violation_count"],
    }
    if isinstance(planner, TrainPriorPlanner):
        summary["selected_event_type"] = planner.selected_event_type
        if planner.selected_event_type is not None:
            prior = planner.event_type_priors[planner.selected_event_type]
            summary["selected_event_type_presence_rate"] = prior.presence_rate
            summary["selected_event_type_positive_count_mode"] = prior.positive_count_mode
            summary["selected_event_type_positive_count_confidence"] = prior.positive_count_confidence
    return summary


if __name__ == "__main__":
    main()
