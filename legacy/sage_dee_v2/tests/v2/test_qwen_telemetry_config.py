from __future__ import annotations

import json
import subprocess
from pathlib import Path

from sage_dee.io_utils import read_yaml
from sage_dee.v2.getm.qwen_backend import train_sft
from tests.v2.subprocess_utils import PYTHON, python_env

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_v2_configs_define_resource_monitor_defaults() -> None:
    for config_path in (
        "configs/v2/sage_v2_smoke.yaml",
        "configs/v2/getm_qwen3_4b_qlora.yaml",
        "configs/v2/sage_v2_duee_fin.yaml",
    ):
        config = read_yaml(REPO_ROOT / config_path)
        resource = config["resource_monitor"]
        budget = config["training_budget"]

        assert resource["enabled"] is True
        assert resource["sample_interval_sec"] == 1.0
        assert resource["vram_soft_limit_gb"] == 23.0
        assert resource["vram_target_min_gb"] == 20.0
        assert resource["vram_target_max_gb"] == 23.0
        assert resource["fail_on_vram_limit"] is False
        assert budget["max_seq_len"] == 4096
        assert budget["micro_batch_size"] == 1
        assert budget["gradient_accumulation_steps"] in {8, 16}
        assert "max_train_steps" in budget


def test_train_sft_dry_run_writes_telemetry_manifest_without_monitor(tmp_path: Path) -> None:
    config = {
        "run": {"dry_run": True, "real_run": False, "profile": "local_dry_run"},
        "resource_monitor": {"enabled": True, "sample_interval_sec": 1.0},
        "getm": {
            "backend": "qwen",
            "qwen": {"base_model": "Qwen/Qwen3-4B-Instruct-2507"},
            "generation": {"k_candidates": 4},
        },
    }

    manifest = train_sft(config, [{"doc_id": "doc-1", "prompt": "P", "output": {"events": []}}], tmp_path)

    telemetry_manifest = json.loads((tmp_path / "telemetry" / "telemetry_manifest.json").read_text(encoding="utf-8"))
    timing_summary = json.loads((tmp_path / "telemetry" / "timing_summary.json").read_text(encoding="utf-8"))

    assert manifest["dry_run"] is True
    assert telemetry_manifest["telemetry_enabled"] is True
    assert telemetry_manifest["real_run"] is False
    assert telemetry_manifest["dry_run"] is True
    assert telemetry_manifest["monitor_started"] is False
    assert timing_summary["total_items"] == 1
    assert timing_summary["completed_items"] == 1


def test_train_script_accepts_telemetry_args_in_dry_run(tmp_path: Path) -> None:
    out_dir = tmp_path / "train"
    completed = subprocess.run(
        [
            PYTHON,
            str(REPO_ROOT / "scripts/v2/train_getm_qwen.py"),
            "--config",
            str(REPO_ROOT / "configs/v2/sage_v2_smoke.yaml"),
            "--dry-run",
            "--enable-telemetry",
            "--telemetry-interval-sec",
            "1.0",
            "--vram-soft-limit-gb",
            "23.0",
            "--vram-target-min-gb",
            "20.0",
            "--vram-target-max-gb",
            "23.0",
            "--max-train-steps",
            "2",
            "--limit",
            "1",
            "--out-dir",
            str(out_dir),
        ],
        cwd=REPO_ROOT,
        env=python_env(),
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
    telemetry_manifest = json.loads((out_dir / "telemetry" / "telemetry_manifest.json").read_text(encoding="utf-8"))
    assert telemetry_manifest["real_run"] is False
    assert telemetry_manifest["monitor_started"] is False
    assert (out_dir / "telemetry" / "timing_summary.json").is_file()


def test_generate_script_accepts_telemetry_args_in_dry_run(tmp_path: Path) -> None:
    out_dir = tmp_path / "generate"
    completed = subprocess.run(
        [
            PYTHON,
            str(REPO_ROOT / "scripts/v2/generate_getm_qwen.py"),
            "--config",
            str(REPO_ROOT / "configs/v2/sage_v2_smoke.yaml"),
            "--dry-run",
            "--enable-telemetry",
            "--telemetry-interval-sec",
            "1.0",
            "--vram-soft-limit-gb",
            "23.0",
            "--vram-target-min-gb",
            "20.0",
            "--vram-target-max-gb",
            "23.0",
            "--limit",
            "1",
            "--k",
            "1",
            "--out-dir",
            str(out_dir),
        ],
        cwd=REPO_ROOT,
        env=python_env(),
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
    telemetry_manifest = json.loads((out_dir / "telemetry" / "telemetry_manifest.json").read_text(encoding="utf-8"))
    assert telemetry_manifest["real_run"] is False
    assert telemetry_manifest["monitor_started"] is False
    assert (out_dir / "telemetry" / "timing_summary.json").is_file()
