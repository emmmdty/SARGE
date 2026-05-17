from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))

from sage_dee.v2.data_interface.dataset_loader import load_documents  # noqa: E402
from sage_dee.v2.data_interface.jsonl import read_jsonl  # noqa: E402
from sage_dee.v2.data_interface.schema_registry import load_schema  # noqa: E402
from sage_dee.v2.lesp.metrics import compute_slot_plan_metrics  # noqa: E402
from sage_dee.v2.lesp.slot_plan import slot_plan_from_dict, validate_slot_plan  # noqa: E402


def main(argv: Sequence[str] | None = None) -> None:
    args = parse_args(argv)
    if args.split == "test" and not args.allow_test_gold_eval:
        raise ValueError("test split slot-plan eval requires --allow-test-gold-eval")

    schema = load_schema(args.dataset, data_root=args.data_root)
    plans = [slot_plan_from_dict(row) for row in read_jsonl(args.pred)]
    for plan in plans:
        validate_slot_plan(plan, schema)
    documents = load_documents(args.dataset, args.split, data_root=args.data_root, mode="eval_internal")
    metrics = compute_slot_plan_metrics(plans, documents, schema)
    metrics.update({"dataset": args.dataset, "split": args.split, "pred": str(args.pred)})

    output_path = args.out or Path(args.pred).parent / f"slot_plan.metrics.{args.split}.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as handle:
        json.dump(metrics, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")

    print(f"slot_plan_metrics={output_path}")
    print("metrics=" + json.dumps(metrics, ensure_ascii=False, sort_keys=True))


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate SAGE-DEE v2 LESP slot plans against gold-visible split.")
    parser.add_argument("--dataset", required=True)
    parser.add_argument("--split", required=True)
    parser.add_argument("--pred", type=Path, required=True)
    parser.add_argument("--data-root", default="data")
    parser.add_argument("--out", type=Path)
    parser.add_argument("--allow-test-gold-eval", action="store_true")
    return parser.parse_args(argv)


if __name__ == "__main__":
    main()
