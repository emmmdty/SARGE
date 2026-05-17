from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from sage_dee.v2.diagnostics.gpu_monitor import (
    GpuMemoryMonitor,
    ResourceMonitorConfig,
    VramLimitExceeded,
    parse_nvidia_smi_csv,
)


def test_parse_nvidia_smi_csv_handles_utilization_na() -> None:
    samples = parse_nvidia_smi_csv(
        "0, 20480, 24564, 76\n1, 1024, 24564, [N/A]\n",
        timestamp="2026-05-02T00:00:00Z",
    )

    assert samples[0].gpu_index == 0
    assert samples[0].memory_used_mb == 20480
    assert samples[0].memory_total_mb == 24564
    assert samples[0].utilization_gpu_percent == 76
    assert samples[1].utilization_gpu_percent is None


def test_gpu_monitor_writes_samples_and_summary_with_target_band(tmp_path: Path) -> None:
    def fake_run(cmd: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(cmd, 0, stdout="0, 21504, 24564, 88\n", stderr="")

    monitor = GpuMemoryMonitor(
        out_dir=tmp_path,
        config=ResourceMonitorConfig(vram_soft_limit_gb=23.0, vram_target_min_gb=20.0, vram_target_max_gb=23.0),
        run_command=fake_run,
    )

    monitor.sample_once()
    summary = monitor.finish()

    assert (tmp_path / "gpu_memory_samples.csv").is_file()
    assert (tmp_path / "gpu_memory_summary.json").is_file()
    assert summary["peak_memory_used_mb_by_gpu"] == {"0": 21504}
    assert summary["max_peak_memory_used_gb"] == pytest.approx(21.0)
    assert summary["exceeded_soft_limit"] is False
    assert summary["within_target_band"] is True
    assert summary["sample_count"] == 1


def test_gpu_monitor_records_warning_when_nvidia_smi_missing(tmp_path: Path) -> None:
    def missing_run(cmd: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        raise FileNotFoundError("nvidia-smi")

    monitor = GpuMemoryMonitor(out_dir=tmp_path, config=ResourceMonitorConfig(), run_command=missing_run)

    monitor.sample_once()
    summary = monitor.finish()

    assert summary["sample_count"] == 0
    assert summary["within_target_band"] is None
    assert summary["warnings"]
    assert "nvidia-smi" in summary["warnings"][0]


def test_gpu_monitor_uses_numeric_cuda_visible_devices(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    seen_commands: list[list[str]] = []

    def fake_run(cmd: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        seen_commands.append(cmd)
        return subprocess.CompletedProcess(cmd, 0, stdout="2, 1024, 24564, 10\n3, 2048, 24564, 20\n", stderr="")

    monkeypatch.setenv("CUDA_VISIBLE_DEVICES", "2,3")
    monitor = GpuMemoryMonitor(out_dir=tmp_path, config=ResourceMonitorConfig(), run_command=fake_run)

    monitor.sample_once()

    assert "--id=2,3" in seen_commands[0]


def test_fail_on_vram_limit_raises_only_for_real_run(tmp_path: Path) -> None:
    def over_limit_run(cmd: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(cmd, 0, stdout="0, 24064, 24564, 98\n", stderr="")

    config = ResourceMonitorConfig(vram_soft_limit_gb=23.0, fail_on_vram_limit=True)
    monitor = GpuMemoryMonitor(out_dir=tmp_path, config=config, run_command=over_limit_run)
    monitor.sample_once()
    summary = monitor.finish()

    assert summary["exceeded_soft_limit"] is True
    monitor.enforce_vram_limit(real_run=False)
    with pytest.raises(VramLimitExceeded):
        monitor.enforce_vram_limit(real_run=True)

    persisted = json.loads((tmp_path / "gpu_memory_summary.json").read_text(encoding="utf-8"))
    assert persisted["exceeded_soft_limit"] is True
