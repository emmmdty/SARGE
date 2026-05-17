from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))

from sage_dee.v2.data_interface.dataset_loader import load_documents  # noqa: E402
from sage_dee.v2.data_interface.jsonl import read_jsonl, write_jsonl  # noqa: E402
from sage_dee.v2.data_interface.schema_registry import load_schema  # noqa: E402
from sage_dee.v2.mrs.oracle_gap import compute_oracle_gap_rows, summarize_oracle_gap  # noqa: E402
from sage_dee.v2.mrs.reward import compute_reward_rows  # noqa: E402


def main(argv: Sequence[str] | None = None) -> None:
    args = parse_args(argv)
    out_dir = args.out_dir or Path("artifacts") / "v2" / "mrs_oracle_gap" / args.dataset / args.split
    out_dir.mkdir(parents=True, exist_ok=True)
    selected_rows = read_jsonl(_selected_file(args.selected, args.split))
    reward_rows = read_jsonl(args.rewards) if args.rewards else _compute_rewards(args)

    gap_rows = compute_oracle_gap_rows(selected_rows=selected_rows, reward_rows=reward_rows)
    summary = summarize_oracle_gap(gap_rows)
    gap_path = write_jsonl(out_dir / f"oracle_gap.{args.split}.jsonl", gap_rows)
    summary_path = out_dir / f"oracle_gap_summary.{args.split}.json"
    with summary_path.open("w", encoding="utf-8") as handle:
        json.dump(summary, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")

    print(f"oracle_gap={gap_path}")
    print(f"oracle_gap_summary={summary_path}")
    print("oracle_gap_example=" + _json_or_null(gap_rows[0] if gap_rows else None))
    print("summary=" + json.dumps(summary, ensure_ascii=False, sort_keys=True))


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Analyze SAGE-DEE v2 MRS selected-vs-oracle gap.")
    parser.add_argument("--dataset", required=True)
    parser.add_argument("--split", required=True)
    parser.add_argument("--selected", required=True, type=Path)
    parser.add_argument("--out-dir", type=Path)
    parser.add_argument("--data-root", default="data")
    parser.add_argument("--rewards", type=Path)
    parser.add_argument("--candidates", type=Path)
    parser.add_argument("--lambda-record", type=float, default=0.5)
    return parser.parse_args(argv)


def _compute_rewards(args: argparse.Namespace) -> list[dict]:
    if args.split == "test":
        raise SystemExit("oracle-gap reward computation is restricted to train/dev gold-visible splits")
    if args.candidates is None:
        raise SystemExit("--candidates is required when --rewards is not provided")
    schema = load_schema(args.dataset, data_root=args.data_root)
    documents = load_documents(args.dataset, args.split, data_root=args.data_root, mode="train")
    candidate_rows = read_jsonl(_candidate_file(args.candidates, args.split))
    return compute_reward_rows(candidate_rows, documents=documents, schema=schema, lambda_record=args.lambda_record)


def _candidate_file(candidates: Path, split: str) -> Path:
    if candidates.is_dir():
        return candidates / f"parsed_candidates.{split}.jsonl"
    return candidates


def _selected_file(selected: Path, split: str) -> Path:
    if selected.is_dir():
        return selected / f"selected_candidates.{split}.jsonl"
    return selected


def _json_or_null(payload: dict | None) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True) if payload is not None else "null"


if __name__ == "__main__":
    main()
