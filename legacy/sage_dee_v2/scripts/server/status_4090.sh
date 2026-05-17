#!/usr/bin/env bash
set -euo pipefail

RUN_ROOT="${1:-}"
if [[ -z "${RUN_ROOT}" ]]; then
  echo "Usage: bash scripts/server/status_4090.sh <run_root>" >&2
  exit 1
fi

echo "run_root=${RUN_ROOT}"

for rel_path in \
  "run_manifest.json" \
  "generation_manifest.json" \
  "config.resolved.yaml" \
  "diagnostics/evaluator_handoff_result.json" \
  "diagnostics/parse_diagnostics.dev.jsonl" \
  "predictions/DuEE-Fin-dev500/dev.canonical.pred.jsonl" \
  "canonical_predictions.dev.jsonl" \
  "parsed_candidates.dev.jsonl" \
  "raw_outputs.dev.jsonl"
do
  path="${RUN_ROOT}/${rel_path}"
  if [[ -e "${path}" ]]; then
    echo "artifact ${rel_path}=present"
  else
    echo "artifact ${rel_path}=missing"
  fi
done

echo "processes:"
pgrep -af "${RUN_ROOT}" | grep -v "status_4090.sh" || true

if command -v nvidia-smi >/dev/null 2>&1; then
  echo "gpu:"
  nvidia-smi --query-gpu=index,name,memory.used,memory.total,utilization.gpu --format=csv,noheader || true
else
  echo "gpu=nvidia-smi_missing"
fi
