from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))

from sage_dee.v2.csg.audit import write_audit_outputs  # noqa: E402
from sage_dee.v2.csg.candidate_builder import build_surface_memories  # noqa: E402
from sage_dee.v2.csg.surface_memory import surface_memory_to_dict  # noqa: E402
from sage_dee.v2.csg.weak_alignment import align_gold_arguments  # noqa: E402
from sage_dee.v2.data_interface.dataset_loader import load_documents  # noqa: E402
from sage_dee.v2.data_interface.jsonl import write_jsonl  # noqa: E402

RED = "\033[31m"
RESET = "\033[0m"
TEST_GOLD_WARNING = (
    "WARNING: test split gold audit is explicitly enabled. This output is diagnostic only and must not be used "
    "as a training or predict artifact."
)


def main(argv: Sequence[str] | None = None) -> None:
    args = parse_args(argv)
    out_dir = args.out_dir or Path("artifacts") / "v2" / "surface_memory" / args.dataset / args.split
    loader_mode = resolve_document_mode(args.split, args.mode, allow_gold_audit=args.allow_gold_audit)
    warning = TEST_GOLD_WARNING if args.split == "test" and loader_mode == "train" else None
    if warning:
        print(f"{RED}{warning}{RESET}", file=sys.stderr)

    documents = load_documents(args.dataset, args.split, data_root=args.data_root, mode=loader_mode)
    memories = build_surface_memories(documents)
    out_dir.mkdir(parents=True, exist_ok=True)
    memory_path = write_jsonl(out_dir / "surface_memory.jsonl", [surface_memory_to_dict(memory) for memory in memories])

    gold_visible = any(document.gold is not None for document in documents)
    alignments = []
    if gold_visible:
        memory_by_doc = {memory.doc_id: memory for memory in memories}
        for document in documents:
            alignments.extend(align_gold_arguments(document, memory_by_doc[document.doc_id]))

    summary = write_audit_outputs(
        out_dir,
        memories,
        alignments,
        dataset=args.dataset,
        split=args.split,
        mode=args.mode,
        gold_visible=gold_visible,
        allow_gold_audit=args.allow_gold_audit,
        warning=warning,
    )

    print(f"surface_memory={memory_path}")
    print(f"audit_summary={out_dir / 'audit_summary.json'}")
    print(
        "summary="
        + json.dumps(
            {
                "documents": summary["document_count"],
                "candidates": summary["candidate_count_total"],
                "gold_visible": summary["gold_visible"],
                "gold_argument_located_rate": summary["gold_argument_located_rate"],
                "unlocated_argument_rate": summary["unlocated_argument_rate"],
                "ambiguous_match_rate": summary["ambiguous_match_rate"],
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build SAGE-DEE v2 CSG surface memory and weak-alignment audit.")
    parser.add_argument("--dataset", required=True)
    parser.add_argument("--split", required=True)
    parser.add_argument("--data-root", default="data")
    parser.add_argument("--out-dir", type=Path)
    parser.add_argument("--mode", choices=("train", "predict"), default="predict")
    parser.add_argument("--allow-gold-audit", action="store_true")
    return parser.parse_args(argv)


def resolve_document_mode(split: str, mode: str, *, allow_gold_audit: bool) -> str:
    split_name = str(split).strip()
    mode_name = str(mode).strip()
    if mode_name == "predict":
        return "predict"
    if mode_name != "train":
        raise ValueError(f"mode must be train or predict; got {mode!r}")
    if split_name == "test" and not allow_gold_audit:
        raise ValueError("test split gold audit requires --allow-gold-audit")
    return "train"


if __name__ == "__main__":
    main()
