from __future__ import annotations

import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from shlex import quote
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_DATA_REPO_ROOT = REPO_ROOT / "data"


@dataclass(frozen=True)
class EvaluatorHandoff:
    command: str
    argv: tuple[str, ...]
    data_repo_root: Path
    out_dir: Path
    script_exists: bool

    @property
    def script_path(self) -> Path:
        return REPO_ROOT / "evaluator"

    def to_dict(self) -> dict[str, Any]:
        return {
            "command": self.command,
            "argv": list(self.argv),
            "data_repo_root": str(self.data_repo_root),
            "script_path": str(self.script_path),
            "out_dir": str(self.out_dir),
            "script_exists": self.script_exists,
        }


def build_evaluator_handoff(
    *,
    run_root: str | Path,
    dataset: str,
    split: str,
    data_repo_root: str | Path = DEFAULT_DATA_REPO_ROOT,
    out_dir: str | Path | None = None,
    profiles: tuple[str, ...] | None = None,
    benchmark_root: str | Path | None = None,
    strict: bool = True,
) -> EvaluatorHandoff:
    del profiles, benchmark_root, strict
    data_root = Path(data_repo_root)
    artifact_out_dir = Path(out_dir) if out_dir is not None else Path(run_root) / "eval"
    prediction_path = Path(run_root) / "predictions" / dataset / f"{split}.canonical.pred.jsonl"
    gold_path = data_root / dataset / f"{split}.jsonl"
    schema_path = data_root / dataset / "schema.json"
    out_path = artifact_out_dir / "role_f1.json"
    python_bin = sys.executable
    argv = [
        python_bin,
        "-B",
        "-m",
        "evaluator",
        "role-f1",
        "--dataset",
        dataset,
        "--gold",
        str(gold_path),
        "--pred",
        str(prediction_path),
        "--schema",
        str(schema_path),
        "--out",
        str(out_path),
    ]
    command = f"cd {quote(str(REPO_ROOT))} && " + " ".join(
        ["UV_CACHE_DIR=/tmp/uv-cache", *[quote(arg) for arg in argv]]
    )
    return EvaluatorHandoff(
        command=command,
        argv=tuple(argv),
        data_repo_root=data_root,
        out_dir=artifact_out_dir,
        script_exists=(REPO_ROOT / "evaluator" / "__main__.py").is_file(),
    )


def run_evaluator_handoff(handoff: EvaluatorHandoff) -> dict[str, Any]:
    if not handoff.script_exists:
        return {
            "attempted": False,
            "returncode": None,
            "stdout": "",
            "stderr": f"missing evaluator package: {handoff.script_path}",
        }
    env = dict(os.environ)
    env["UV_CACHE_DIR"] = "/tmp/uv-cache"
    completed = subprocess.run(
        list(handoff.argv),
        cwd=REPO_ROOT,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )
    return {
        "attempted": True,
        "returncode": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
    }
