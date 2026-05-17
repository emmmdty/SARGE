#!/usr/bin/env bash
set -euo pipefail

RUN_ROOT="${1:-}"
DATASET="${2:-DuEE-Fin-dev500}"
SPLIT="${3:-dev}"
EVALUATOR_ROOT="${EVALUATOR_ROOT:-/home/TJK/DEE/dee-eval}"
EVALUATOR_PYTHON="${EVALUATOR_PYTHON:-${EVALUATOR_ROOT}/.venv/bin/python}"
BENCHMARK_ROOT="${BENCHMARK_ROOT:-/data/TJK/DEE/data/processed}"

if [[ -z "${RUN_ROOT}" ]]; then
  echo "Usage: bash scripts/server/eval_4090.sh <run_root> [dataset] [split] [out_dir]" >&2
  exit 1
fi

RUN_NAME="$(basename "${RUN_ROOT}")"
OUT_DIR="${4:-/data/TJK/DEE/sage-dee/evaluator_artifacts/${RUN_NAME}/${DATASET}/${SPLIT}}"

cd "${EVALUATOR_ROOT}"
mkdir -p "${OUT_DIR}"

if [[ -x "${EVALUATOR_PYTHON}" ]]; then
  "${EVALUATOR_PYTHON}" scripts/build_eval_artifacts.py \
    --run_dir "${RUN_ROOT}" \
    --benchmark_root "${BENCHMARK_ROOT}" \
    --out_dir "${OUT_DIR}" \
    --profiles unified_main record_level aux_basic paper_tables leaderboard \
    --datasets "${DATASET}" \
    --splits "${SPLIT}" \
    --strict
elif command -v uv >/dev/null 2>&1; then
  UV_CACHE_DIR="${UV_CACHE_DIR:-/tmp/uv-cache}" uv run python scripts/build_eval_artifacts.py \
    --run_dir "${RUN_ROOT}" \
    --benchmark_root "${BENCHMARK_ROOT}" \
    --out_dir "${OUT_DIR}" \
    --profiles unified_main record_level aux_basic paper_tables leaderboard \
    --datasets "${DATASET}" \
    --splits "${SPLIT}" \
    --strict
else
  echo "missing evaluator python: ${EVALUATOR_PYTHON}; uv is also unavailable" >&2
  exit 127
fi

echo "evaluator_artifacts=${OUT_DIR}"
