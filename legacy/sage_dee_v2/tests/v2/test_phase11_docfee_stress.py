from __future__ import annotations

import json
import subprocess
from pathlib import Path

import yaml

from sage_dee.io_utils import read_yaml
from tests.v2.subprocess_utils import PYTHON, python_env

REPO_ROOT = Path(__file__).resolve().parents[2]
CONFIG = REPO_ROOT / "configs/v2/sage_v2_phase11_docfee_stress.yaml"
RUNNER = REPO_ROOT / "scripts/v2/run_phase11_docfee_stress.py"
AGGREGATOR = REPO_ROOT / "scripts/v2/aggregate_phase11_docfee_stress.py"
MERGE_HELPER = REPO_ROOT / "scripts/v2/merge_phase11_docfee_stress_shards.py"
REPORT = REPO_ROOT / "docs/refactor/SAGE_V2_PHASE11_DOCFEE_STRESS_ANALYSIS.md"


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_yaml(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(payload, allow_unicode=True, sort_keys=False), encoding="utf-8")


def _run_runner(args: list[str], *, env_overrides: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [PYTHON, str(RUNNER), *args],
        cwd=REPO_ROOT,
        env=python_env(env_overrides or {}),
        check=False,
        capture_output=True,
        text=True,
    )


def test_phase11_config_freezes_docfee_profile_without_training() -> None:
    assert CONFIG.exists()
    config = read_yaml(CONFIG)

    phase11 = config["phase11"]
    assert phase11["dataset"] == "DocFEE-dev1000"
    assert phase11["split"] == "dev"
    assert phase11["systems"] == ["S4"]
    assert phase11["seed"] == 42
    assert phase11["train_used"] is False
    assert phase11["full_train_used"] is False
    assert phase11["test_blocked"] is True
    assert phase11["no_profile_tuning"] is True
    assert phase11["no_post_full_dev_tuning"] is True
    assert phase11["adapter_source"] == {
        "baseline_id": "S4",
        "seed": 42,
        "phase6_profile": "phase6_s4_role_safe_surface_memory",
    }
    assert phase11["phase9_source_aggregate"].endswith("phase9_duee_fin_main_table.json")
    assert phase11["phase10_source_aggregate"].endswith("phase10_chfinann_frozen_profile_aggregate.full_dev.json")
    assert config["evaluation"]["evaluator_root"] == "/home/TJK/DEE/dee-eval"
    assert config["evaluation"]["benchmark_root"] == "/data/TJK/DEE/data/processed"
    assert config["data"]["dataset"] == "DocFEE-dev1000"
    assert config["predict"]["dataset"] == "DocFEE-dev1000"
    assert config["predict"]["split"] == "dev"
    assert config["getm"]["prompt"]["baseline_mode"] == "role_safe_surface_memory"
    assert config["getm"]["generation"]["seed"] == 42
    assert [bucket["name"] for bucket in phase11["length_buckets"]] == [
        "<= 1024",
        "1024 < x <= 2048",
        "2048 < x <= 4096",
        "> 4096",
    ]


def test_phase11_runner_rejects_test_split_training_and_tuning(tmp_path: Path) -> None:
    test_split = _run_runner(
        [
            "--config",
            str(CONFIG),
            "--split",
            "test",
            "--dry-run",
            "--skip-evaluator",
            "--allow-missing-gate-for-local-test",
            "--out-dir",
            str(tmp_path / "test-split"),
        ]
    )
    assert test_split.returncode != 0
    assert "test split" in test_split.stderr

    tuned_config_path = tmp_path / "tuned.yaml"
    tuned_config = read_yaml(CONFIG)
    tuned_config["phase11"]["train_used"] = True
    _write_yaml(tuned_config_path, tuned_config)
    training_rejected = _run_runner(
        [
            "--config",
            str(tuned_config_path),
            "--dry-run",
            "--skip-evaluator",
            "--allow-missing-gate-for-local-test",
            "--out-dir",
            str(tmp_path / "training-rejected"),
        ]
    )
    assert training_rejected.returncode != 0
    assert "train_used" in training_rejected.stderr

    tuning_config_path = tmp_path / "tuning.yaml"
    tuning_config = read_yaml(CONFIG)
    tuning_config["phase11"]["no_profile_tuning"] = False
    _write_yaml(tuning_config_path, tuning_config)
    tuning_rejected = _run_runner(
        [
            "--config",
            str(tuning_config_path),
            "--dry-run",
            "--skip-evaluator",
            "--allow-missing-gate-for-local-test",
            "--out-dir",
            str(tmp_path / "tuning-rejected"),
        ]
    )
    assert tuning_rejected.returncode != 0
    assert "profile tuning" in tuning_rejected.stderr


def test_phase11_runner_rejects_missing_phase9_or_phase10_gate(tmp_path: Path) -> None:
    missing_phase9_config_path = tmp_path / "phase9-missing.yaml"
    config = read_yaml(CONFIG)
    config["phase11"]["phase9_source_aggregate"] = str(tmp_path / "missing-phase9.json")
    _write_yaml(missing_phase9_config_path, config)
    missing_phase9 = _run_runner(
        [
            "--config",
            str(missing_phase9_config_path),
            "--dry-run",
            "--skip-evaluator",
            "--out-dir",
            str(tmp_path / "missing-phase9"),
        ]
    )
    assert missing_phase9.returncode != 0
    assert "Phase 9 aggregate" in missing_phase9.stderr

    phase9_path = tmp_path / "phase9.json"
    _write_json(
        phase9_path,
        {
            "phase": "Phase 9 DuEE-Fin full dev main table",
            "gate": {
                "dev_main_table_complete": True,
                "no_post_full_dev_tuning_declared": True,
                "chfinann_frozen_profile_allowed": True,
                "test_blocked": True,
                "no_test_used": True,
                "no_full_train_used": True,
            },
        },
    )
    phase10_missing_config_path = tmp_path / "phase10-missing.yaml"
    config = read_yaml(CONFIG)
    config["phase11"]["phase9_source_aggregate"] = str(phase9_path)
    config["phase11"]["phase10_source_aggregate"] = str(tmp_path / "missing-phase10.json")
    _write_yaml(phase10_missing_config_path, config)
    missing_phase10 = _run_runner(
        [
            "--config",
            str(phase10_missing_config_path),
            "--dry-run",
            "--skip-evaluator",
            "--out-dir",
            str(tmp_path / "missing-phase10"),
        ]
    )
    assert missing_phase10.returncode != 0
    assert "Phase 10 aggregate" in missing_phase10.stderr


def test_phase11_shard_runner_requires_merge_evaluator_boundary(tmp_path: Path) -> None:
    assert MERGE_HELPER.exists()
    completed = _run_runner(
        [
            "--config",
            str(CONFIG),
            "--dry-run",
            "--allow-missing-gate-for-local-test",
            "--shard-index",
            "0",
            "--shard-count",
            "4",
            "--out-dir",
            str(tmp_path / "bad-shard"),
        ]
    )
    assert completed.returncode != 0
    assert "shard runs require --skip-evaluator" in completed.stderr


def test_phase11_aggregator_requires_length_bucket_fields_and_rejects_overall_only(tmp_path: Path) -> None:
    run_root = tmp_path / "run"
    _write_json(
        run_root / "phase11_run_summary.json",
        {
            "phase": "Phase 11 DocFEE stress analysis",
            "dataset": "DocFEE-dev1000",
            "split": "dev",
            "run_dir": str(run_root),
        },
    )
    _write_json(
        run_root / "phase11_docfee_stress_analysis.json",
        {
            "overall": {
                "event_table_micro_f1": 0.1,
                "role_level_f1": 0.1,
                "exact_record_f1": 0.01,
                "parse_error_count": 1,
                "parse_error_rate": 0.1,
                "schema_violation_rows": 2,
                "schema_violation_count": 2,
            }
        },
    )
    completed = subprocess.run(
        [
            PYTHON,
            str(AGGREGATOR),
            "--run-root",
            str(run_root),
            "--out",
            str(tmp_path / "aggregate.json"),
        ],
        cwd=REPO_ROOT,
        env=python_env(),
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode != 0
    assert "length bucket" in completed.stderr


def test_phase11_report_contains_limitation_section() -> None:
    report = REPORT.read_text(encoding="utf-8")

    for required in (
        "DocFEE Stress Analysis",
        "diagnostic-only long-document stress analysis",
        "char-count fallback",
        "no test",
        "no train",
        "no full train",
        "no profile tuning",
        "no prompt tuning",
        "no parser tuning",
        "no surface-memory tuning",
        "Limitation",
    ):
        assert required in report
