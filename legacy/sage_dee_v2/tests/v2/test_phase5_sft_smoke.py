from __future__ import annotations

import json
import subprocess
from pathlib import Path

from sage_dee.io_utils import read_yaml
from tests.v2.subprocess_utils import PYTHON, python_env

REPO_ROOT = Path(__file__).resolve().parents[2]
CONFIG = REPO_ROOT / "configs/v2/sage_v2_sft_smoke.yaml"


def test_phase5_sft_smoke_config_is_small_seeded_and_train_only() -> None:
    config = read_yaml(CONFIG)

    assert config["run"]["profile"] == "phase5_sft_smoke_4090"
    assert config["data"]["train_split"] == "train"
    assert config["data"]["max_train_docs"] == 8
    assert config["getm"]["generation"]["seed"] == 42
    assert config["getm"]["generation"]["use_chat_template"] is True
    assert config["getm"]["generation"]["use_response_prefix"] is True
    assert config["getm"]["qwen"]["training"]["max_train_steps"] == 2
    assert config["getm"]["qwen"]["training"]["micro_batch_size"] == 1
    assert config["getm"]["qwen"]["training"]["gradient_accumulation"] == 4


def test_phase5_runner_dry_run_writes_guarded_summary(tmp_path: Path) -> None:
    out_root = tmp_path / "phase5"
    completed = subprocess.run(
        [
            PYTHON,
            str(REPO_ROOT / "scripts/v2/train_phase5_sft_smoke.py"),
            "--config",
            str(CONFIG),
            "--dry-run",
            "--allow-limit50",
            "--skip-evaluator",
            "--out-root",
            str(out_root),
        ],
        cwd=REPO_ROOT,
        env=python_env(),
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
    summary = json.loads((out_root / "phase5_summary.json").read_text(encoding="utf-8"))

    assert summary["scope"]["train_limit"] == 8
    assert summary["scope"]["dev20_limit"] == 20
    assert summary["scope"]["limit50"] == 50
    assert summary["scope"]["test_used"] is False
    assert summary["gate"]["sft_smoke_not_performance"] is True
    assert summary["train"]["sft_label_mask"]["all_prompt_labels_masked"] is True
    assert summary["train"]["sft_target_audit"]["target_schema_valid"] is True
    assert summary["limit50"]["canonical_rows"] == 50
    assert summary["limit50"]["evaluator_attempted"] is False


def test_phase5_runner_rejects_forbidden_test_scope(tmp_path: Path) -> None:
    completed = subprocess.run(
        [
            PYTHON,
            str(REPO_ROOT / "scripts/v2/train_phase5_sft_smoke.py"),
            "--config",
            str(CONFIG),
            "--dry-run",
            "--split",
            "test",
            "--out-root",
            str(tmp_path / "phase5"),
        ],
        cwd=REPO_ROOT,
        env=python_env(),
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode != 0
    assert "test split" in completed.stderr
