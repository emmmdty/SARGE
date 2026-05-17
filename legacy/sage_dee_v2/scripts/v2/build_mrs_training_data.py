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
from sage_dee.v2.mrs.features import compute_feature_rows  # noqa: E402
from sage_dee.v2.mrs.pairwise_data import build_pairwise_rows  # noqa: E402
from sage_dee.v2.mrs.reward import METRIC_SOURCE, compute_reward_rows  # noqa: E402


def main(argv: Sequence[str] | None = None) -> None:
    args = parse_args(argv)
    if args.split == "test":
        raise SystemExit("MRS reward construction is restricted to train/dev gold-visible splits")

    out_dir = args.out_dir or Path("artifacts") / "v2" / "mrs_training_data" / args.dataset / args.split
    out_dir.mkdir(parents=True, exist_ok=True)
    schema = load_schema(args.dataset, data_root=args.data_root)
    documents = load_documents(args.dataset, args.split, data_root=args.data_root, mode="train", limit=args.limit)
    candidate_rows = read_jsonl(_candidate_file(args.candidates, args.split))
    surface_memories = _load_surface_memories(args, documents)
    slot_plans = _load_slot_plans(args.slot_plan)

    feature_rows = compute_feature_rows(
        candidate_rows,
        schema=schema,
        surface_memories=surface_memories,
        slot_plans=slot_plans,
    )
    reward_rows = compute_reward_rows(
        candidate_rows,
        documents=documents,
        schema=schema,
        lambda_record=args.lambda_record,
    )
    pair_rows = build_pairwise_rows(reward_rows, feature_rows, min_delta=args.min_delta)

    features_path = write_jsonl(out_dir / "features.jsonl", feature_rows)
    rewards_path = write_jsonl(out_dir / "rewards.jsonl", reward_rows)
    pairs_path = write_jsonl(out_dir / "pairs.jsonl", pair_rows)
    summary = {
        "dataset": args.dataset,
        "split": args.split,
        "document_count": len(documents),
        "candidate_count": len(candidate_rows),
        "feature_count": len(feature_rows),
        "reward_count": len(reward_rows),
        "pair_count": len(pair_rows),
        "metric_source": METRIC_SOURCE,
        "reward_uses_gold": True,
        "candidate_source": str(_candidate_file(args.candidates, args.split)),
    }
    summary_path = out_dir / "summary.json"
    _write_json(summary_path, summary)

    print(f"features={features_path}")
    print(f"rewards={rewards_path}")
    print(f"pairs={pairs_path}")
    print(f"summary={summary_path}")
    print("feature_example=" + _json_or_null(feature_rows[0] if feature_rows else None))
    print("reward_example=" + _json_or_null(reward_rows[0] if reward_rows else None))
    print("pair_example=" + _json_or_null(pair_rows[0] if pair_rows else None))
    print("summary_json=" + json.dumps(summary, ensure_ascii=False, sort_keys=True))


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build SAGE-DEE v2 MRS feature, reward, and pairwise data.")
    parser.add_argument("--dataset", required=True)
    parser.add_argument("--split", required=True)
    parser.add_argument("--candidates", required=True, type=Path)
    parser.add_argument("--out-dir", type=Path)
    parser.add_argument("--data-root", default="data")
    parser.add_argument("--surface-memory", type=Path)
    parser.add_argument("--slot-plan", type=Path)
    parser.add_argument("--lambda-record", type=float, default=0.5)
    parser.add_argument("--min-delta", type=float, default=1e-9)
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
