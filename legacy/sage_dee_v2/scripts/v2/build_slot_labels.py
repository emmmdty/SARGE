from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from collections.abc import Sequence
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))

from sage_dee.v2.data_interface.dataset_loader import load_documents  # noqa: E402
from sage_dee.v2.data_interface.jsonl import write_jsonl  # noqa: E402
from sage_dee.v2.data_interface.schema_registry import load_schema  # noqa: E402
from sage_dee.v2.lesp.slot_labels import derive_slot_labels  # noqa: E402


def main(argv: Sequence[str] | None = None) -> None:
    args = parse_args(argv)
    if args.split == "test":
        raise ValueError("LESP slot label derivation is only allowed for train/dev splits")

    out_dir = args.out_dir or Path("artifacts") / "v2" / "lesp_labels" / args.dataset / args.split
    schema = load_schema(args.dataset, data_root=args.data_root)
    documents = load_documents(args.dataset, args.split, data_root=args.data_root, mode="train")
    labels = [derive_slot_labels(document, schema) for document in documents]
    rows = [label.to_dict() for label in labels]

    out_dir.mkdir(parents=True, exist_ok=True)
    labels_path = write_jsonl(out_dir / f"slot_labels.{args.split}.jsonl", rows)
    summary = _summary(args.dataset, args.split, rows)
    summary_path = out_dir / f"slot_label_summary.{args.split}.json"
    with summary_path.open("w", encoding="utf-8") as handle:
        json.dump(summary, handle, ensure_ascii=False, indent=2)
        handle.write("\n")

    print(f"slot_labels={labels_path}")
    print(f"slot_label_summary={summary_path}")
    print("summary=" + json.dumps(summary, ensure_ascii=False, sort_keys=True))


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build SAGE-DEE v2 LESP supervised slot labels.")
    parser.add_argument("--dataset", required=True)
    parser.add_argument("--split", choices=("train", "dev", "test"), required=True)
    parser.add_argument("--data-root", default="data")
    parser.add_argument("--out-dir", type=Path)
    return parser.parse_args(argv)


def _summary(dataset: str, split: str, rows: list[dict[str, object]]) -> dict[str, object]:
    count_buckets: Counter[str] = Counter()
    same_type_multi = 0
    event_type_label_count = 0
    record_slot_label_count = 0
    for row in rows:
        event_type_labels = row.get("event_type_labels") or []
        record_slot_labels = row.get("record_slot_labels") or []
        if isinstance(record_slot_labels, list):
            record_slot_label_count += len(record_slot_labels)
        if not isinstance(event_type_labels, list):
            continue
        event_type_label_count += len(event_type_labels)
        for label in event_type_labels:
            if not isinstance(label, dict):
                continue
            count_buckets[str(label.get("count_bucket"))] += 1
            if label.get("same_type_multi_event") is True:
                same_type_multi += 1
    return {
        "dataset": dataset,
        "split": split,
        "document_count": len(rows),
        "event_type_label_count": event_type_label_count,
        "record_slot_label_count": record_slot_label_count,
        "count_bucket_distribution": dict(sorted(count_buckets.items())),
        "same_type_multi_event_label_count": same_type_multi,
    }


if __name__ == "__main__":
    main()
