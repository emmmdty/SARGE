from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))

from sage_dee.v2.csg.surface_memory import build_surface_memory  # noqa: E402
from sage_dee.v2.data_interface.dataset_loader import load_documents  # noqa: E402
from sage_dee.v2.data_interface.jsonl import write_jsonl  # noqa: E402
from sage_dee.v2.data_interface.schema_registry import load_schema  # noqa: E402
from sage_dee.v2.getm.sft_dataset import build_getm_sft_sample  # noqa: E402


def main(argv: Sequence[str] | None = None) -> None:
    args = parse_args(argv)
    out_dir = args.out_dir or Path("artifacts") / "v2" / "getm_sft" / args.dataset / args.split
    schema = load_schema(args.dataset, data_root=args.data_root)
    mode = "train" if args.split == "train" else "predict"
    documents = load_documents(args.dataset, args.split, data_root=args.data_root, mode=mode, limit=args.limit)

    rows = []
    for document in documents:
        memory = build_surface_memory(document.input)
        rows.append(
            build_getm_sft_sample(
                document,
                schema,
                surface_candidates=memory.candidates,
                slot_plan=None,
                output_format=args.output_format,
            )
        )

    out_dir.mkdir(parents=True, exist_ok=True)
    sft_path = write_jsonl(out_dir / f"getm_sft.{args.split}.jsonl", rows)
    summary = _summary(args.dataset, args.split, rows, mode)
    summary_path = out_dir / f"getm_sft_summary.{args.split}.json"
    with summary_path.open("w", encoding="utf-8") as handle:
        json.dump(summary, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")

    prompt_example_path = out_dir / f"prompt_example.{args.split}.txt"
    prompt_example_path.write_text(rows[0]["prompt"] if rows else "", encoding="utf-8")
    sample_example_path = out_dir / f"sft_sample_example.{args.split}.json"
    with sample_example_path.open("w", encoding="utf-8") as handle:
        json.dump(rows[0] if rows else {}, handle, ensure_ascii=False, indent=2)
        handle.write("\n")

    print(f"getm_sft={sft_path}")
    print(f"getm_sft_summary={summary_path}")
    print(f"prompt_example={prompt_example_path}")
    print(f"sft_sample_example={sample_example_path}")
    print("summary=" + json.dumps(summary, ensure_ascii=False, sort_keys=True))


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build SAGE-DEE v2 GETM SFT prompt/output JSONL.")
    parser.add_argument("--dataset", required=True)
    parser.add_argument("--split", choices=("train", "dev", "test"), required=True)
    parser.add_argument("--data-root", default="data")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--output-format", choices=("minimal_text", "argument_object"), default="minimal_text")
    parser.add_argument("--out-dir", type=Path)
    return parser.parse_args(argv)


def _summary(dataset: str, split: str, rows: list[dict[str, object]], mode: str) -> dict[str, object]:
    output_count = sum(1 for row in rows if "output" in row)
    return {
        "dataset": dataset,
        "split": split,
        "loader_mode": mode,
        "document_count": len(rows),
        "output_count": output_count,
        "prompt_only_count": len(rows) - output_count,
        "gold_visible": mode == "train",
    }


if __name__ == "__main__":
    main()
