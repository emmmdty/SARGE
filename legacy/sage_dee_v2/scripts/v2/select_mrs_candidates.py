from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))

from sage_dee.v2.csg.surface_memory import build_surface_memory, surface_memory_to_dict  # noqa: E402
from sage_dee.v2.data_interface.dataset_loader import load_documents  # noqa: E402
from sage_dee.v2.data_interface.jsonl import read_jsonl, write_jsonl  # noqa: E402
from sage_dee.v2.data_interface.schema_registry import load_schema  # noqa: E402
from sage_dee.v2.mrs.selector import select_candidate_rows  # noqa: E402
from sage_dee.v2.mrs.simple_ranker import load_model  # noqa: E402
from sage_dee.v2.pipeline.export_canonical import export_predictions  # noqa: E402


def main(argv: Sequence[str] | None = None) -> None:
    args = parse_args(argv)
    out_dir = args.out_dir or Path("artifacts") / "v2" / "mrs_selected" / args.dataset / args.split
    out_dir.mkdir(parents=True, exist_ok=True)
    schema = load_schema(args.dataset, data_root=args.data_root)
    documents = load_documents(args.dataset, args.split, data_root=args.data_root, mode="predict", limit=args.limit)
    candidate_rows = read_jsonl(_candidate_file(args.candidates, args.split))
    surface_memories = _load_surface_memories(args, documents)
    slot_plans = _load_slot_plans(args.slot_plan)
    model = load_model(args.model)

    result = select_candidate_rows(
        candidates=candidate_rows,
        documents=documents,
        schema=schema,
        model=model,
        surface_memories=surface_memories,
        slot_plans=slot_plans,
    )
    scores_path = write_jsonl(out_dir / f"selector_scores.{args.split}.jsonl", result.score_rows)
    selected_path = write_jsonl(out_dir / f"selected_candidates.{args.split}.jsonl", result.selected_rows)
    canonical_path = out_dir / "predictions" / args.dataset / f"{args.split}.canonical.pred.jsonl"
    export_predictions(result.canonical_predictions, canonical_path)
    summary = {
        "dataset": args.dataset,
        "split": args.split,
        "document_count": len(documents),
        "candidate_count": len(candidate_rows),
        "selected_count": len(result.selected_rows),
        "selector_gold_visible": False,
        "model": str(args.model),
        "canonical_predictions": str(canonical_path),
    }
    summary_path = out_dir / "selection_summary.json"
    _write_json(summary_path, summary)

    print(f"selector_scores={scores_path}")
    print(f"selected_candidates={selected_path}")
    print(f"canonical_predictions={canonical_path}")
    print("selector_gold_visible=false")
    print("selected_example=" + _json_or_null(result.selected_rows[0] if result.selected_rows else None))
    print("summary=" + json.dumps(summary, ensure_ascii=False, sort_keys=True))


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Select final SAGE-DEE v2 candidates with MRS.")
    parser.add_argument("--dataset", required=True)
    parser.add_argument("--split", required=True)
    parser.add_argument("--candidates", required=True, type=Path)
    parser.add_argument("--model", required=True, type=Path)
    parser.add_argument("--out-dir", type=Path)
    parser.add_argument("--data-root", default="data")
    parser.add_argument("--surface-memory", type=Path)
    parser.add_argument("--slot-plan", type=Path)
    parser.add_argument("--limit", type=int)
    return parser.parse_args(argv)


def _candidate_file(candidates: Path, split: str) -> Path:
    if candidates.is_dir():
        return candidates / f"parsed_candidates.{split}.jsonl"
    return candidates


def _load_surface_memories(
    args: argparse.Namespace,
    documents,
) -> dict[str, dict[str, Any]]:
    if args.surface_memory:
        return {str(row.get("doc_id", "")): row for row in read_jsonl(args.surface_memory)}
    prompts_path = args.candidates / f"prompts.{args.split}.jsonl" if args.candidates.is_dir() else None
    if prompts_path and prompts_path.exists():
        memories = {}
        for row in read_jsonl(prompts_path):
            doc_id = str(row.get("doc_id", ""))
            memories[doc_id] = {
                "doc_id": doc_id,
                "source": "getm_prompts",
                "candidates": row.get("surface_candidates") or [],
            }
        return memories
    return {document.doc_id: surface_memory_to_dict(build_surface_memory(document.input)) for document in documents}


def _load_slot_plans(path: Path | None) -> dict[str, dict[str, Any]] | None:
    if path is None:
        return None
    return {str(row.get("doc_id", "")): row for row in read_jsonl(path)}


def _write_json(path: Path, payload: dict[str, Any]) -> Path:
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
    return path


def _json_or_null(payload: dict[str, Any] | None) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True) if payload is not None else "null"


if __name__ == "__main__":
    main()
