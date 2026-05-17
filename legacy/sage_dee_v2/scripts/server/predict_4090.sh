#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
CONFIG_PATH="${1:-configs/v2/getm_qwen3_4b_qlora.yaml}"
PROFILE="${PROFILE:-server_smoke_4090}"
CONDA_ENV="${CONDA_ENV:-tjk-feg}"
SERVER_PYTHON="${SERVER_PYTHON:-/home/TJK/.conda/envs/${CONDA_ENV}/bin/python}"
if [[ $# -gt 0 ]]; then
  shift
fi

source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/_init_conda.sh"
init_conda_env "${CONDA_ENV}"

cd "${REPO_ROOT}"
export PATH="$(dirname "${SERVER_PYTHON}"):${PATH}"
export PYTHONPATH="${REPO_ROOT}/src${PYTHONPATH:+:${PYTHONPATH}}"

"${SERVER_PYTHON}" scripts/v2/generate_getm_qwen.py \
  --config "${CONFIG_PATH}" \
  --profile "${PROFILE}" \
  "$@"
