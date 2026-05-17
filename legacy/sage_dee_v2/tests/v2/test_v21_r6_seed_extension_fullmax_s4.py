from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from sage_dee.io_utils import read_yaml
from tests.v2.subprocess_utils import PYTHON, python_env

REPO_ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = REPO_ROOT / "configs/v2/sage_v2_v21_r6_seed_extension_fullmax_s4.yaml"
RUNNER = REPO_ROOT / "scripts/v2/run_v21_r6_seed_extension_fullmax_s4.py"
AGGREGATOR = REPO_ROOT / "scripts/v2/aggregate_v21_r6_seed_extension_fullmax_s4.py"
CHANGELOG_PATH = REPO_ROOT / "docs/refactor/SAGE_V2_1_DEV_RESCUE_CHANGELOG.md"
FINAL_RESULT_PATH = REPO_ROOT / "docs/refactor/SAGE_V2_FINAL_TEST_RESULT.json"


def test_config_declares_r6_dev_seed43_44_s4_only() -> None:
    config = read_yaml(CONFIG_PATH)

    assert config["phase"] == "R6"
    assert config["data"]["dataset"] == "DuEE-Fin-dev500"
    assert config["data"]["eval_split"] == "dev"
    assert config["data"]["train_split"] == "train"
    assert config["systems"] == ["S4"]
    assert config["seeds_to_run"] == [43, 44]
    assert config["allow_test"] is False
    assert config["allow_seed42_retrain"] is False
    assert config["no_v21_surface"] is True
    assert config["no_r4b_planner"] is True
    assert config["surface"] == "frozen_compressed_phase6_final_profile"
    assert "S1" not in config["systems"]
    assert "S2" not in config["systems"]
    assert "S3" not in config["systems"]


def test_runner_rejects_forbidden_scope(tmp_path: Path) -> None:
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
                "43",
                "--systems",
                "S4",
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

    seed42 = run("--seed", "42")
    assert seed42.returncode == 2
    assert "rejects seed42 retrain" in seed42.stderr

    seed45 = run("--seed", "45")
    assert seed45.returncode == 2
    assert "only permits seeds 43/44" in seed45.stderr

    s3 = run("--systems", "S3")
    assert s3.returncode == 2
    assert "S4 only" in s3.stderr

    v21 = run("--surface", "v21_surface_opt_in_r2")
    assert v21.returncode == 2
    assert "rejects v21 surface" in v21.stderr

    planner = run("--planner", "r4b")
    assert planner.returncode == 2
    assert "rejects R4b planner" in planner.stderr


def test_runner_dry_run_writes_seed_summary_and_manifests(tmp_path: Path) -> None:
    out_root = tmp_path / "seed43"

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
            "43",
            "--systems",
            "S4",
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
    summary = json.loads((out_root / "seed_summary.json").read_text(encoding="utf-8"))
    train_manifest = json.loads((out_root / "training_manifest.json").read_text(encoding="utf-8"))
    generation_manifest = json.loads((out_root / "generation_manifest.json").read_text(encoding="utf-8"))

    assert summary["phase"] == "R6 seed extension full/max S4"
    assert summary["seed"] == 43
    assert summary["split"] == "dev"
    assert summary["surface"] == "frozen_compressed_phase6_final_profile"
    assert summary["train_run"] is False
    assert summary["generation_run"] is False
    assert summary["evaluator_run"] is False
    assert summary["test_run"] is False
    assert summary["seed42_retrained"] is False
    assert train_manifest["seed"] == 43
    assert train_manifest["train_run"] is False
    assert generation_manifest["seed"] == 43
    assert generation_manifest["generation_run"] is False


def test_aggregator_requires_seed42_43_44_evidence(tmp_path: Path) -> None:
    run_root = tmp_path / "r6"
    seed42_root = _write_seed42_r3_root(tmp_path / "r3_seed42")
    _write_seed_summary(run_root / "seed43", seed=43, event_f1=0.72, exact_f1=0.31)
    out_json = tmp_path / "summary.json"
    out_md = tmp_path / "summary.md"

    completed = subprocess.run(
        [
            PYTHON,
            str(AGGREGATOR),
            "--run-root",
            str(run_root),
            "--seed42-root",
            str(seed42_root),
            "--out-json",
            str(out_json),
            "--out-md",
            str(out_md),
        ],
        cwd=REPO_ROOT,
        env=python_env(),
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 2
    assert "missing R6 seed44 summary" in completed.stderr


def test_aggregator_computes_mean_std_and_recommendation(tmp_path: Path) -> None:
    run_root = tmp_path / "r6"
    seed42_root = _write_seed42_r3_root(tmp_path / "r3_seed42", event_f1=0.737327, exact_f1=0.352248)
    _write_seed_summary(run_root / "seed43", seed=43, event_f1=0.72, exact_f1=0.31)
    _write_seed_summary(run_root / "seed44", seed=44, event_f1=0.71, exact_f1=0.32)
    out_json = tmp_path / "summary.json"
    out_md = tmp_path / "summary.md"

    completed = subprocess.run(
        [
            PYTHON,
            str(AGGREGATOR),
            "--run-root",
            str(run_root),
            "--seed42-root",
            str(seed42_root),
            "--out-json",
            str(out_json),
            "--out-md",
            str(out_md),
        ],
        cwd=REPO_ROOT,
        env=python_env(),
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
    summary = json.loads(out_json.read_text(encoding="utf-8"))
    report = out_md.read_text(encoding="utf-8")

    assert summary["phase"] == "R6 seed extension full/max S4"
    assert summary["seed_count"] == 3
    assert summary["metrics"]["mean_event_role_f1"] == pytest.approx((0.737327 + 0.72 + 0.71) / 3)
    assert summary["metrics"]["std_exact_record_f1"] > 0
    assert summary["recommended_next_phase"] == "R7_thesis_package_minimal_matrix"
    assert summary["v2_1_thesis_potential"] is True
    assert "recommended_next_phase" in report


def test_changelog_contains_r6_change_ids() -> None:
    text = CHANGELOG_PATH.read_text(encoding="utf-8")

    for change_id in ("R6-001", "R6-002", "R6-003", "R6-004", "R6-005"):
        assert change_id in text


def test_frozen_final_result_file_is_not_modified() -> None:
    assert FINAL_RESULT_PATH.is_file()
    result = subprocess.run(
        ["git", "diff", "--quiet", "--", str(FINAL_RESULT_PATH.relative_to(REPO_ROOT))],
        cwd=REPO_ROOT,
        check=False,
    )

    assert result.returncode == 0


def _write_seed42_r3_root(root: Path, *, event_f1: float = 0.737327, exact_f1: float = 0.352248) -> Path:
    row_dir = root / "s4_full_or_max_frozen_surface"
    row_dir.mkdir(parents=True)
    payload = _seed_payload(seed=42, event_f1=event_f1, exact_f1=exact_f1)
    payload.update(
        {
            "phase": "R3 S4 train-size scaling",
            "row_id": "s4_full_or_max_frozen_surface",
            "train_run": True,
            "generation_run": True,
            "evaluator_validation_ok": True,
        }
    )
    (row_dir / "row_summary.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return root


def _write_seed_summary(seed_dir: Path, *, seed: int, event_f1: float, exact_f1: float) -> None:
    seed_dir.mkdir(parents=True)
    payload = _seed_payload(seed=seed, event_f1=event_f1, exact_f1=exact_f1)
    payload.update({"phase": "R6 seed extension full/max S4"})
    (seed_dir / "seed_summary.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _seed_payload(*, seed: int, event_f1: float, exact_f1: float) -> dict[str, object]:
    seed_dir = Path(f"/tmp/r6/seed{seed}")
    return {
        "seed": seed,
        "system": "S4",
        "dataset": "DuEE-Fin-dev500",
        "split": "dev",
        "surface": "frozen_compressed_phase6_final_profile",
        "train_limit": 6474,
        "train_examples_seen": 6474,
        "event_table_micro_f1": event_f1,
        "role_level_f1": event_f1,
        "exact_record_f1": exact_f1,
        "parse_error": 0,
        "schema_violation_rows": 1,
        "unknown_role": 0,
        "unknown_event_type": 0,
        "canonical_rows": 500,
        "canonical_event_count": 550,
        "accepted_event_count": 550,
        "adapter_path": str(seed_dir / "train" / "artifacts" / "model" / "adapter"),
        "evaluator_artifact_path": str(seed_dir / "evaluator_artifacts"),
        "training_manifest_path": str(seed_dir / "training_manifest.json"),
        "generation_manifest_path": str(seed_dir / "generation_manifest.json"),
        "wallclock": {"train_elapsed_sec": 4900.0, "generation_elapsed_sec": 4300.0},
        "peak_vram": {"max_peak_memory_used_gb": 23.0},
        "test_run": False,
        "test_gold_read": False,
        "v21_surface_run": False,
        "r4b_planner_run": False,
        "frozen_final_modified": False,
    }
