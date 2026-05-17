#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
CONDA_ENV="${CONDA_ENV:-tjk-feg}"
SERVER_PYTHON="${SERVER_PYTHON:-/home/TJK/.conda/envs/${CONDA_ENV}/bin/python}"

source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/_init_conda.sh"
init_conda_env "${CONDA_ENV}"

if [[ ! -x "${SERVER_PYTHON}" ]]; then
  echo "missing server python: ${SERVER_PYTHON}" >&2
  exit 1
fi

cd "${REPO_ROOT}"
export PATH="$(dirname "${SERVER_PYTHON}"):${PATH}"
export PYTHONPATH="${REPO_ROOT}/src${PYTHONPATH:+:${PYTHONPATH}}"

"${SERVER_PYTHON}" - <<'PY'
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

repo_root = Path.cwd()
checks = {
    "repo_root": str(repo_root),
    "python": sys.executable,
    "path_head": os.environ.get("PATH", "").split(":")[:3],
    "data_link": str((repo_root / "data").resolve()),
    "data_exists": (repo_root / "data").exists(),
    "duee_fin_exists": (repo_root / "data" / "DuEE-Fin-dev500").exists(),
    "chfinann_exists": (repo_root / "data" / "ChFinAnn").exists(),
    "docfee_exists": (repo_root / "data" / "DocFEE-dev1000").exists(),
    "server_data_exists": Path("/data/TJK/DEE/data").exists(),
    "server_artifacts_exists": Path("/data/TJK/DEE/sage-dee").exists(),
    "qwen_models_exists": Path("/data/TJK/DEE/models/Qwen").exists(),
    "external_evaluator_exists": Path("/home/TJK/DEE/dee-eval/scripts/build_eval_artifacts.py").is_file(),
}

try:
    import sage_dee.v2  # noqa: F401

    checks["sage_dee_v2_importable"] = True
except Exception as exc:  # pragma: no cover - server environment dependent
    checks["sage_dee_v2_importable"] = False
    checks["sage_dee_v2_error"] = f"{type(exc).__name__}: {exc}"

print(json.dumps(checks, ensure_ascii=False, indent=2, sort_keys=True))

required = [
    checks["data_exists"],
    checks["duee_fin_exists"],
    checks["server_data_exists"],
    checks["server_artifacts_exists"],
    checks["qwen_models_exists"],
    checks["external_evaluator_exists"],
    checks["sage_dee_v2_importable"],
]
if not all(required):
    raise SystemExit(1)
PY
