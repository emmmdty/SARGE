#!/usr/bin/env bash

init_conda_env() {
  local env_name="$1"
  local conda_bin=""

  if command -v conda >/dev/null 2>&1; then
    conda_bin="$(command -v conda)"
  else
    local candidates=(
      "$HOME/anaconda3/bin/conda"
      "$HOME/miniconda3/bin/conda"
      "$HOME/mambaforge/bin/conda"
      "/home/anaconda3/bin/conda"
      "/home/miniconda3/bin/conda"
      "/opt/conda/bin/conda"
    )
    local candidate
    for candidate in "${candidates[@]}"; do
      if [[ -x "${candidate}" ]]; then
        conda_bin="${candidate}"
        break
      fi
    done
  fi

  if [[ -z "${conda_bin}" ]]; then
    echo "Failed to locate conda executable." >&2
    return 1
  fi

  # Initialize conda in non-interactive shells without assuming a fixed install path.
  eval "$("${conda_bin}" shell.bash hook)"
  conda activate "${env_name}"
}
