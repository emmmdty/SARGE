from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path
from shlex import join

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))

from sage_dee.v2.pipeline.evaluator_handoff import DEFAULT_DATA_REPO_ROOT, run_evaluator_handoff  # noqa: E402
from sage_dee.v2.pipeline.run_v2_smoke import run_v2_smoke  # noqa: E402


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    command_infer = _command_infer(argv)
    result = run_v2_smoke(
        dataset=args.dataset,
        split=args.split,
        data_root=args.data_root,
        out_root=args.out_root,
        run_id=args.run_id,
        seed=args.seed,
        k=args.k,
        slot_plan_path=args.slot_plan,
        data_repo_root=args.data_repo_root,
        evaluator_out_dir=args.evaluator_out_dir,
        limit=args.limit,
        command_infer=command_infer,
    )

    print(f"run_root={result.run_root}")
    print(f"prediction_path={result.prediction_path}")
    print(f"run_manifest={result.run_manifest_path}")
    print(f"handoff_command={result.handoff_command}")
    print(f"artifact_layer_available={str(result.handoff_script_exists).lower()}")

    if args.run_evaluator:
        handoff_result = run_evaluator_handoff(result.handoff)
        handoff_result_path = result.run_root / "diagnostics" / "evaluator_handoff_result.json"
        handoff_result_path.write_text(
            json.dumps(handoff_result, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        print(f"artifact_layer_result={handoff_result_path}")
        print(f"artifact_layer_returncode={handoff_result.get('returncode')}")
        if handoff_result.get("stdout"):
            print("artifact_layer_stdout=" + str(handoff_result["stdout"]).strip())
        if handoff_result.get("stderr"):
            print("artifact_layer_stderr=" + str(handoff_result["stderr"]).strip())
        returncode = handoff_result.get("returncode")
        return int(returncode) if returncode is not None else 2

    print("artifact_layer_result=not_run")
    return 0


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run SAGE-DEE v2 end-to-end smoke pipeline.")
    parser.add_argument("--dataset", default="DuEE-Fin-dev500")
    parser.add_argument("--split", default="dev")
    parser.add_argument("--data-root", default="data")
    parser.add_argument("--out-root", type=Path, default=Path("runs"))
    parser.add_argument("--run-id")
    parser.add_argument("--seed", type=int, default=13)
    parser.add_argument("--k", type=int, default=4)
    parser.add_argument("--slot-plan", type=Path)
    parser.add_argument("--data-repo-root", type=Path, default=DEFAULT_DATA_REPO_ROOT)
    parser.add_argument("--evaluator-out-dir", type=Path)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--run-evaluator", action="store_true")
    return parser.parse_args(argv)


def _command_infer(argv: Sequence[str] | None) -> str:
    if argv is None:
        return join([sys.executable, *sys.argv])
    return join([sys.executable, "scripts/v2/run_sage_v2_smoke.py", *argv])


if __name__ == "__main__":
    raise SystemExit(main())
