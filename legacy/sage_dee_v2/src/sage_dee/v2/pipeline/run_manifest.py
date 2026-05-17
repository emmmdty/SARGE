from __future__ import annotations

import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

EVALUATOR_VERSION = "eval-artifacts-v1.1"
PREDICTION_FORMAT = "canonical-jsonl"
METHOD_NAME = "SAGE-DEE-v2-smoke"
METHOD_FAMILY = "SAGE-DEE-v2"


def write_run_manifest(
    run_root: str | Path,
    *,
    run_id: str,
    dataset: str,
    split: str,
    seed: int,
    command_infer: str | None = None,
    notes: str | None = None,
    repo_root: str | Path | None = None,
    backend: str = "mock",
    use_csg: bool = True,
    use_lesp: bool = True,
    use_getm: bool = True,
    use_mrs: bool = True,
) -> Path:
    output_path = Path(run_root) / "run_manifest.json"
    payload = build_run_manifest(
        run_id=run_id,
        dataset=dataset,
        split=split,
        seed=seed,
        command_infer=command_infer,
        notes=notes,
        repo_root=repo_root,
        backend=backend,
        use_csg=use_csg,
        use_lesp=use_lesp,
        use_getm=use_getm,
        use_mrs=use_mrs,
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return output_path


def build_run_manifest(
    *,
    run_id: str,
    dataset: str,
    split: str,
    seed: int,
    command_infer: str | None = None,
    notes: str | None = None,
    repo_root: str | Path | None = None,
    backend: str = "mock",
    use_csg: bool = True,
    use_lesp: bool = True,
    use_getm: bool = True,
    use_mrs: bool = True,
) -> dict[str, Any]:
    module_toggles = {
        "use_csg": use_csg,
        "use_lesp": use_lesp,
        "use_getm": use_getm,
        "use_mrs": use_mrs,
    }
    return {
        "run_id": run_id,
        "method_name": METHOD_NAME,
        "method_family": METHOD_FAMILY,
        "dataset_version": dataset,
        "split_version": split,
        "evaluator_version": EVALUATOR_VERSION,
        "prediction_format": PREDICTION_FORMAT,
        "training_view": "evaluator_gold/train",
        "gold_view": f"processed/views/evaluator_gold/{dataset}",
        "seed": int(seed),
        "git_commit": _git_commit(repo_root),
        "command_train": None,
        "command_infer": command_infer,
        "created_at": _created_at(),
        "use_csg": use_csg,
        "use_lesp": use_lesp,
        "use_getm": use_getm,
        "use_mrs": use_mrs,
        "module_toggles": module_toggles,
        "backend": backend,
        "notes": notes
        or "SAGE-DEE v2 end-to-end smoke run with mock GETM backend; not model performance evidence.",
    }


def _created_at() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _git_commit(repo_root: str | Path | None) -> str | None:
    if repo_root is None:
        return None
    try:
        completed = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=Path(repo_root),
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError:
        return None
    commit = completed.stdout.strip()
    return commit if completed.returncode == 0 and commit else None
