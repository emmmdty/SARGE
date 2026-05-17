#!/usr/bin/env bash
set -euo pipefail

REMOTE="${REMOTE:-gpu-4090}"
REMOTE_DIR="${REMOTE_DIR:-/home/TJK/DEE/sage-dee}"
MODE="dry-run"
RUN_PREFLIGHT="false"

usage() {
  cat <<'USAGE'
Usage: bash scripts/server/sync_to_4090.sh [--dry-run|--apply] [--preflight]

Uploads the local source tree to gpu-4090 as a run mirror. Dry-run is the default.

Environment overrides:
  REMOTE       SSH target, default gpu-4090
  REMOTE_DIR   Server repo mirror, default /home/TJK/DEE/sage-dee
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --dry-run)
      MODE="dry-run"
      shift
      ;;
    --apply)
      MODE="apply"
      shift
      ;;
    --preflight)
      RUN_PREFLIGHT="true"
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "unknown argument: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "${REPO_ROOT}"

RSYNC_ARGS=(-az --delete --itemize-changes)
if [[ "${MODE}" == "dry-run" ]]; then
  RSYNC_ARGS+=(--dry-run)
fi

FILTERS=(
  "--filter=- /.git/"
  "--filter=- /.pytest_cache/"
  "--filter=- /.ruff_cache/"
  "--filter=- /.venv/"
  "--filter=- /.worktrees/"
  "--filter=- /.mypy_cache/"
  "--filter=- /.hypothesis/"
  "--filter=- /data/"
  "--filter=- /data_full/"
  "--filter=- /models/"
  "--filter=- /artifacts/"
  "--filter=- /runs/"
  "--filter=- /outputs/"
  "--filter=- /checkpoints/"
  "--filter=- /wandb/"
  "--filter=- /cache/"
  "--filter=- /.cache/"
  "--filter=- /evaluator_artifacts/"
  "--filter=- /server_results/"
  "--filter=- /archive/v1/server_active_snapshot_*/"
  "--filter=- /htmlcov/"
  "--filter=- /build/"
  "--filter=- /dist/"
  "--filter=- /.coverage"
  "--filter=- /coverage.xml"
  "--filter=- /**/__pycache__/"
  "--filter=- *.pyc"
  "--filter=- *.egg-info/"
  "--filter=- *.log"
  "--filter=- *:Zone.Identifier"
  "--filter=+ /AGENTS.md"
  "--filter=+ /README.md"
  "--filter=+ /RULES.md"
  "--filter=+ /.gitignore"
  "--filter=+ /pyproject.toml"
  "--filter=+ /archive/***"
  "--filter=+ /configs/***"
  "--filter=+ /docs/***"
  "--filter=+ /scripts/***"
  "--filter=+ /src/***"
  "--filter=+ /tests/***"
  "--filter=- *"
)

echo "mode=${MODE}"
echo "remote=${REMOTE}:${REMOTE_DIR}"

rsync "${RSYNC_ARGS[@]}" "${FILTERS[@]}" ./ "${REMOTE}:${REMOTE_DIR}/"

if [[ "${MODE}" == "dry-run" ]]; then
  echo "dry_run_complete=true"
  exit 0
fi

echo "sync_applied=true"

if [[ "${RUN_PREFLIGHT}" == "true" ]]; then
  ssh "${REMOTE}" "cd '${REMOTE_DIR}' && bash scripts/server/preflight_4090.sh"
fi
