from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from sage_dee.io_utils import read_yaml
from tests.v2.subprocess_utils import PYTHON, python_env

REPO_ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = REPO_ROOT / "configs/v2/sage_v2_v21_s4_train_size_scaling.yaml"
RUNNER = REPO_ROOT / "scripts/v2/run_v21_r3_s4_train_size_scaling.py"
AGGREGATOR = REPO_ROOT / "scripts/v2/aggregate_v21_r3_s4_train_size_scaling.py"
CHANGELOG_PATH = REPO_ROOT / "docs/refactor/SAGE_V2_1_DEV_RESCUE_CHANGELOG.md"
FINAL_RESULT_PATH = REPO_ROOT / "docs/refactor/SAGE_V2_FINAL_TEST_RESULT.json"


def test_config_declares_dev_seed42_s4_only_rows() -> None:
    config = read_yaml(CONFIG_PATH)

    assert config["data"]["dataset"] == "DuEE-Fin-dev500"
    assert config["data"]["eval_split"] == "dev"
    assert config["data"]["train_split"] == "train"
    assert config["seed"] == 42
    assert config["systems"] == ["S4"]
    assert config["test_enabled"] is False
    assert config["allow_test"] is False
    assert config["allow_seed43_44"] is False
    assert [row["row_id"] for row in config["rows"]] == [
        "baseline_512_existing",
        "s4_2k_frozen_surface",
        "s4_2k_v21_surface_secondary",
        "s4_full_or_max_frozen_surface",
    ]
    assert config["rows"][0]["action"] == "read_existing"
    assert config["rows"][2]["secondary"] is True
    assert config["rows"][3]["conditional"] is True


def test_runner_rejects_test_split_seed_switching_and_non_s4(tmp_path: Path) -> None:
    def run(*extra: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                PYTHON,
                str(RUNNER),
                "--config",
                str(CONFIG_PATH),
                "--dataset",
                "DuEE-Fin-dev500",
                "--eval-split",
                "dev",
                "--seed",
                "42",
                "--rows",
                "baseline_512_existing",
                "--dry-run",
                "--allow-missing-gate-for-local-test",
                "--out-root",
                str(tmp_path / "out"),
                *extra,
            ],
            cwd=REPO_ROOT,
            env=python_env(),
            check=False,
            capture_output=True,
            text=True,
        )

    test_split = run("--eval-split", "test")
    assert test_split.returncode == 2
    assert "rejects test split" in test_split.stderr

    seed43 = run("--seed", "43")
    assert seed43.returncode == 2
    assert "seed42 only" in seed43.stderr

    s3 = run("--systems", "S3")
    assert s3.returncode == 2
    assert "S4 only" in s3.stderr


def test_baseline_existing_row_is_read_only_and_writes_manifest(tmp_path: Path) -> None:
    baseline = _write_baseline_summary(tmp_path / "phase6" / "phase6_S4_seed42_fake")
    out_root = tmp_path / "r3"

    completed = subprocess.run(
        [
            PYTHON,
            str(RUNNER),
            "--config",
            str(CONFIG_PATH),
            "--dataset",
            "DuEE-Fin-dev500",
            "--eval-split",
            "dev",
            "--seed",
            "42",
            "--rows",
            "baseline_512_existing",
            "--baseline-summary",
            str(baseline),
            "--dry-run",
            "--allow-missing-gate-for-local-test",
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
    row_dir = out_root / "baseline_512_existing"
    row_summary = json.loads((row_dir / "row_summary.json").read_text(encoding="utf-8"))
    row_manifest = json.loads((row_dir / "row_manifest.json").read_text(encoding="utf-8"))

    assert row_summary["row_id"] == "baseline_512_existing"
    assert row_summary["action"] == "read_existing"
    assert row_summary["train_run"] is False
    assert row_summary["generation_run"] is False
    assert row_summary["baseline_retrained"] is False
    assert row_summary["train_limit"] == 512
    assert row_manifest["test_run"] is False
    assert row_manifest["seed"] == 42


def test_row_c_secondary_and_row_d_trigger_logic() -> None:
    from scripts.v2.run_v21_r3_s4_train_size_scaling import (
        ROW_SPECS,
        row_d_triggered,
    )

    assert ROW_SPECS["s4_2k_v21_surface_secondary"].secondary is True
    assert row_d_triggered(
        {"event_table_micro_f1": 0.456984, "exact_record_f1": 0.054236},
        {"event_table_micro_f1": 0.507, "exact_record_f1": 0.055},
    )
    assert row_d_triggered(
        {"event_table_micro_f1": 0.456984, "exact_record_f1": 0.054236},
        {"event_table_micro_f1": 0.46, "exact_record_f1": 0.0645},
    )
    assert not row_d_triggered(
        {"event_table_micro_f1": 0.456984, "exact_record_f1": 0.054236},
        {"event_table_micro_f1": 0.49, "exact_record_f1": 0.06},
    )


def test_aggregator_computes_improvement_against_baseline(tmp_path: Path) -> None:
    run_root = tmp_path / "r3"
    _write_row_summary(
        run_root / "baseline_512_existing",
        row_id="baseline_512_existing",
        train_limit=512,
        event_f1=0.456984,
        exact_f1=0.054236,
        train_run=False,
    )
    _write_row_summary(
        run_root / "s4_2k_frozen_surface",
        row_id="s4_2k_frozen_surface",
        train_limit=2000,
        event_f1=0.516984,
        exact_f1=0.055,
        train_run=True,
    )
    out_json = tmp_path / "aggregate.json"

    completed = subprocess.run(
        [
            PYTHON,
            str(AGGREGATOR),
            "--run-root",
            str(run_root),
            "--out-json",
            str(out_json),
        ],
        cwd=REPO_ROOT,
        env=python_env(),
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
    aggregate = json.loads(out_json.read_text(encoding="utf-8"))

    assert aggregate["baseline_row_id"] == "baseline_512_existing"
    assert aggregate["primary_row_id"] == "s4_2k_frozen_surface"
    assert aggregate["row_d_triggered"] is True
    assert aggregate["undertraining_verdict"] in {"high", "medium"}
    assert aggregate["rows"]["s4_2k_frozen_surface"]["event_table_micro_f1_delta_vs_baseline"] == pytest.approx(0.06)


def test_changelog_contains_r3_change_ids() -> None:
    text = CHANGELOG_PATH.read_text(encoding="utf-8")

    for change_id in ("R3-001", "R3-002", "R3-003", "R3-004", "R3-005"):
        assert change_id in text


def test_frozen_final_result_file_is_not_modified() -> None:
    assert FINAL_RESULT_PATH.is_file()
    result = subprocess.run(
        ["git", "diff", "--quiet", "--", str(FINAL_RESULT_PATH.relative_to(REPO_ROOT))],
        cwd=REPO_ROOT,
        check=False,
    )

    assert result.returncode == 0


def _write_baseline_summary(run_dir: Path) -> Path:
    run_dir.mkdir(parents=True)
    adapter_dir = run_dir / "train" / "artifacts" / "model" / "adapter"
    adapter_dir.mkdir(parents=True)
    canonical_path = run_dir / "full_dev" / "predictions" / "DuEE-Fin-dev500" / "dev.canonical.pred.jsonl"
    canonical_path.parent.mkdir(parents=True)
    canonical_path.write_text('{"doc_id":"doc-1","events":[]}\n', encoding="utf-8")
    summary = {
        "phase": "Phase 6 SFT baseline matrix S1-S4",
        "baseline_id": "S4",
        "profile": "phase6_s4_role_safe_surface_memory",
        "seed": 42,
        "run_dir": str(run_dir),
        "scope": {"train_limit": 512, "test_used": False, "full_train_used": False},
        "train": {"adapter_dir": str(adapter_dir), "train_rows": 512, "train_examples": 512},
        "full_dev": {
            "run_dir": str(run_dir / "full_dev"),
            "canonical_path": str(canonical_path),
            "generation_manifest_path": str(run_dir / "full_dev" / "generation_manifest.json"),
            "evaluator_artifact_root": str(run_dir / "evaluator_artifacts" / "full_dev"),
            "event_table_micro_f1": 0.456984,
            "role_level_f1": 0.456984,
            "exact_record_f1": 0.054236,
            "parse_error": 7,
            "schema_violation_rows": 5,
            "unknown_role": 4,
            "unknown_event_type": 0,
            "canonical_rows": 500,
            "canonical_event_count": 551,
            "accepted_event_count": 543,
        },
    }
    summary_path = run_dir / "phase6_run_summary.json"
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return summary_path


def _write_row_summary(
    row_dir: Path,
    *,
    row_id: str,
    train_limit: int,
    event_f1: float,
    exact_f1: float,
    train_run: bool,
) -> None:
    row_dir.mkdir(parents=True)
    payload = {
        "row_id": row_id,
        "seed": 42,
        "system": "S4",
        "split": "dev",
        "train_limit": train_limit,
        "train_run": train_run,
        "generation_run": train_run,
        "event_table_micro_f1": event_f1,
        "role_level_f1": event_f1,
        "exact_record_f1": exact_f1,
        "parse_error": 1,
        "schema_violation_rows": 2,
        "unknown_role": 3,
        "unknown_event_type": 0,
        "canonical_rows": 500,
        "canonical_event_count": 550,
        "accepted_event_count": 548,
        "train_examples_seen": train_limit if train_run else 512,
        "num_train_epochs": 1.0,
        "adapter_path": str(row_dir / "adapter"),
        "evaluator_artifact_path": str(row_dir / "evaluator"),
    }
    (row_dir / "row_summary.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
