from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))

from sage_dee.v2.data_interface.jsonl import read_jsonl  # noqa: E402
from sage_dee.v2.mrs.simple_ranker import save_model, train_ranker  # noqa: E402


def main(argv: Sequence[str] | None = None) -> None:
    args = parse_args(argv)
    pair_rows = read_jsonl(args.train_data) if args.train_data.exists() else []
    model = train_ranker(pair_rows, mode=args.mode, epochs=args.epochs, learning_rate=args.learning_rate)

    args.out_dir.mkdir(parents=True, exist_ok=True)
    model_path = save_model(model, args.out_dir / "model.json")
    summary = {
        "train_data": str(args.train_data),
        "mode": args.mode,
        "pair_count": len(pair_rows),
        "model_path": str(model_path),
        "fallback_rule_based": bool(model.get("fallback_rule_based", False)),
    }
    summary_path = args.out_dir / "training_summary.json"
    with summary_path.open("w", encoding="utf-8") as handle:
        json.dump(summary, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")

    print(f"model={model_path}")
    print(f"training_summary={summary_path}")
    print("summary=" + json.dumps(summary, ensure_ascii=False, sort_keys=True))


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train a lightweight SAGE-DEE v2 MRS ranker.")
    parser.add_argument("--train-data", required=True, type=Path)
    parser.add_argument("--out-dir", required=True, type=Path)
    parser.add_argument(
        "--mode",
        choices=("weighted_linear", "sklearn_logistic", "rule_based"),
        default="weighted_linear",
    )
    parser.add_argument("--epochs", type=int, default=5)
    parser.add_argument("--learning-rate", type=float, default=0.1)
    return parser.parse_args(argv)


if __name__ == "__main__":
    main()
