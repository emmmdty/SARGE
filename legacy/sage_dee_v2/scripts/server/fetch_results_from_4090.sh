#!/usr/bin/env bash
set -euo pipefail

REMOTE="${REMOTE:-gpu-4090}"
SERVER_ARTIFACT_ROOT="${SERVER_ARTIFACT_ROOT:-/data/TJK/DEE/sage-dee}"
MODE="apply"

usage() {
  cat <<'USAGE'
Usage: bash scripts/server/fetch_results_from_4090.sh [--dry-run] <remote_path> [local_dir]

Fetches a specific server result path into a local ignored directory.
Relative remote paths are resolved under /data/TJK/DEE/sage-dee.

Defaults:
  local_dir = server_results/
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --dry-run)
      MODE="dry-run"
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    --*)
      echo "unknown argument: $1" >&2
      usage >&2
      exit 2
      ;;
    *)
      break
      ;;
  esac
done

if [[ $# -lt 1 || $# -gt 2 ]]; then
  usage >&2
  exit 2
fi

REMOTE_PATH="$1"
LOCAL_DIR="${2:-server_results}"

case "${REMOTE_PATH}" in
  /*) ;;
  *) REMOTE_PATH="${SERVER_ARTIFACT_ROOT}/${REMOTE_PATH}" ;;
esac

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "${REPO_ROOT}"
mkdir -p "${LOCAL_DIR}"

RSYNC_ARGS=(-az --itemize-changes)
if [[ "${MODE}" == "dry-run" ]]; then
  RSYNC_ARGS+=(--dry-run)
fi

echo "mode=${MODE}"
echo "source=${REMOTE}:${REMOTE_PATH}"
echo "dest=${LOCAL_DIR}/"

rsync "${RSYNC_ARGS[@]}" "${REMOTE}:${REMOTE_PATH}" "${LOCAL_DIR}/"

if [[ "${MODE}" == "dry-run" ]]; then
  echo "dry_run_complete=true"
else
  echo "fetch_complete=true"
fi
