from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))

from sage_dee.v2.data_interface.dataset_loader import load_documents  # noqa: E402
from sage_dee.v2.data_interface.schema_registry import load_schema  # noqa: E402
from sage_dee.v2.getm.candidate_generator import generate_getm_candidate_files  # noqa: E402
from sage_dee.v2.getm.mock_backend import MockGetmBackend  # noqa: E402


def main(argv: Sequence[str] | None = None) -> None:
    args = parse_args(argv)
    out_dir = args.out_dir or Path("artifacts") / "v2" / "getm_candidates" / args.dataset / args.split
    schema = load_schema(args.dataset, data_root=args.data_root)
    documents = load_documents(args.dataset, args.split, data_root=args.data_root, mode="predict", limit=args.limit)
    backend = _backend(args.backend, args.mock_mode)

    output = generate_getm_candidate_files(
        documents=documents,
        dataset=args.dataset,
        split=args.split,
        schema=schema,
        backend=backend,
        k=args.k,
        out_dir=out_dir,
    )
    diagnostics = json.loads(output.parse_diagnostics_path.read_text(encoding="utf-8"))
    print(f"prompts={output.prompts_path}")
    print(f"raw_outputs={output.raw_outputs_path}")
    print(f"parsed_candidates={output.parsed_candidates_path}")
    print(f"parse_diagnostics={output.parse_diagnostics_path}")
    print(f"canonical_predictions={output.canonical_predictions_path}")
    print("diagnostics=" + json.dumps(diagnostics, ensure_ascii=False, sort_keys=True))


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate SAGE-DEE v2 GETM candidate files.")
    parser.add_argument("--dataset", required=True)
    parser.add_argument("--split", required=True)
    parser.add_argument("--backend", choices=("mock",), required=True)
    parser.add_argument("--mock-mode", choices=("empty", "schema_only", "echo_candidates"), default="echo_candidates")
    parser.add_argument("--k", type=int, default=1)
    parser.add_argument("--data-root", default="data")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--out-dir", type=Path)
    return parser.parse_args(argv)


def _backend(name: str, mock_mode: str):
    if name == "mock":
        return MockGetmBackend(mode=mock_mode)
    raise ValueError(f"unsupported GETM backend: {name}")


if __name__ == "__main__":
    main()

