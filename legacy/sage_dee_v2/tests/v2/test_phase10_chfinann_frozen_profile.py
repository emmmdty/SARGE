from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from sage_dee.io_utils import read_yaml
from tests.v2.subprocess_utils import PYTHON, python_env

REPO_ROOT = Path(__file__).resolve().parents[2]
CONFIG = REPO_ROOT / "configs/v2/sage_v2_phase10_chfinann_frozen_profile.yaml"
RUNNER = REPO_ROOT / "scripts/v2/run_phase10_chfinann_frozen_profile.py"
AGGREGATOR = REPO_ROOT / "scripts/v2/aggregate_phase10_chfinann_frozen_profile.py"
REPORT = REPO_ROOT / "docs/refactor/SAGE_V2_PHASE10_CHFINANN_FROZEN_PROFILE.md"
STATE = REPO_ROOT / "docs/refactor/SAGE_V2_EXECUTION_STATE.md"


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _phase9_aggregate(path: Path) -> None:
    _write_json(
        path,
        {
            "phase": "Phase 9 DuEE-Fin full dev main table",
            "dataset": "DuEE-Fin-dev500",
            "split": "dev",
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


def _phase6_run(root: Path, baseline_id: str, seed: int, *, timestamp: str = "20260504T000000Z") -> Path:
    profile = {
        "S1": "phase6_s1_direct_json",
        "S2": "phase6_s2_schema_only",
        "S4": "phase6_s4_role_safe_surface_memory",
    }[baseline_id]
    mode = {
        "S1": "direct_json",
        "S2": "schema_only",
        "S4": "role_safe_surface_memory",
    }[baseline_id]
    run_dir = root / f"phase6_{baseline_id}_seed{seed}_{timestamp}"
    adapter = run_dir / "train/artifacts/model/adapter"
    adapter.mkdir(parents=True)
    _write_json(
        run_dir / "phase6_run_summary.json",
        {
            "phase": "Phase 6 SFT baseline matrix S1-S4",
            "baseline_id": baseline_id,
            "profile": profile,
            "baseline_mode": mode,
            "seed": seed,
            "run_dir": str(run_dir),
            "scope": {
                "dataset": "DuEE-Fin-dev500",
                "split": "dev",
                "full_dev_used": True,
                "full_train_used": False,
                "test_used": False,
            },
            "train": {"adapter_dir": str(adapter)},
            "full_dev": {
                "canonical_rows": 500,
                "evaluator_attempted": True,
                "evaluator_validation_ok": True,
            },
        },
    )
    return run_dir


def _phase10_summary(
    root: Path,
    baseline_id: str,
    seed: int,
    f1: float,
    *,
    dry_run: bool = False,
    timestamp: str = "20260505T000000Z",
) -> None:
    run_dir = root / f"phase10_{baseline_id}_seed{seed}_{timestamp}"
    payload = {
        "phase": "Phase 10 ChFinAnn frozen-profile robustness",
        "baseline_id": baseline_id,
        "profile": f"phase6_{baseline_id.lower()}",
        "label": baseline_id,
        "seed": seed,
        "run_dir": str(run_dir),
        "adapter_path": str(run_dir / "adapter"),
        "scope": {
            "dataset": "ChFinAnn",
            "split": "dev",
            "document_count": 3204,
            "full_dev_used": True,
            "limit50_used": True,
            "test_used": False,
            "train_used": False,
            "full_train_used": False,
            "dry_run": dry_run,
            "real_run": not dry_run,
            "no_chfinann_tuning": True,
        },
        "full_dev": {
            "canonical_rows": 3204,
            "canonical_event_count": 20,
            "parse_error": 2,
            "schema_violation_rows": 3,
            "schema_violation": 4,
            "unknown_role": 5,
            "unknown_event_type": 0,
            "evaluator_attempted": True,
            "evaluator_validation_ok": True,
            "event_table_micro_f1": f1,
            "role_level_f1": f1,
            "exact_record_f1": f1 / 10,
            "parse_valid_subset": {
                "doc_count": 3202,
                "source_doc_count": 3204,
                "event_table_micro_f1": f1 + 0.01,
                "role_level_f1": f1 + 0.01,
                "exact_record_f1": f1 / 10,
            },
            "surface_diagnostics": {
                "diagnostic_scope": "post_hoc_dev_gold_audit_only",
                "gold_visible_to_prediction": False,
                "candidate_recall_at_k": {"10": f1 / 2},
                "hallucinated_argument_rate": 0.2 - f1 / 10,
                "non_surface_argument_rate": 0.8,
            },
        },
    }
    _write_json(run_dir / "phase10_run_summary.json", payload)


def test_phase10_config_freezes_chfinann_profile_without_training() -> None:
    assert CONFIG.exists()
    config = read_yaml(CONFIG)

    assert config["phase10"]["phase9_source_profile"] == "DuEE-Fin frozen profile"
    assert config["phase10"]["train_used"] is False
    assert config["phase10"]["full_train_used"] is False
    assert config["phase10"]["test_blocked"] is True
    assert config["phase10"]["no_chfinann_tuning"] is True
    assert config["phase10"]["seed_matrix"] == {
        "S1": [42, 43],
        "S2": [42, 43],
        "S4": [42, 43, 44],
    }
    assert config["data"]["dataset"] == "ChFinAnn"
    assert config["predict"]["dataset"] == "ChFinAnn"
    assert config["predict"]["split"] == "dev"

    expected_profiles = {
        "phase10_s1_direct_json": "direct_json",
        "phase10_s2_schema_only": "schema_only",
        "phase10_s4_role_safe_surface_memory": "role_safe_surface_memory",
    }
    assert set(config["profiles"]) == set(expected_profiles)
    for profile_name, baseline_mode in expected_profiles.items():
        profile = config["profiles"][profile_name]
        assert profile["getm"]["prompt"]["baseline_mode"] == baseline_mode
        generation = profile["getm"]["generation"]
        assert generation["do_sample"] is False
        assert generation["temperature"] is None
        assert generation["top_p"] == 1.0
        assert generation["deterministic"] is True


def test_phase10_runner_rejects_test_split_and_missing_phase9_gate(tmp_path: Path) -> None:
    test_split = subprocess.run(
        [
            PYTHON,
            str(RUNNER),
            "--config",
            str(CONFIG),
            "--stage",
            "limit50",
            "--dry-run",
            "--allow-limit50",
            "--split",
            "test",
            "--phase9-aggregate",
            str(tmp_path / "missing_phase9.json"),
            "--phase6-runs-root",
            str(tmp_path / "phase6"),
            "--out-root",
            str(tmp_path / "test-split"),
        ],
        cwd=REPO_ROOT,
        env=python_env(),
        check=False,
        capture_output=True,
        text=True,
    )
    assert test_split.returncode != 0
    assert "test split" in test_split.stderr

    missing_phase9 = subprocess.run(
        [
            PYTHON,
            str(RUNNER),
            "--config",
            str(CONFIG),
            "--stage",
            "limit50",
            "--dry-run",
            "--allow-limit50",
            "--phase9-aggregate",
            str(tmp_path / "missing_phase9.json"),
            "--phase6-runs-root",
            str(tmp_path / "phase6"),
            "--out-root",
            str(tmp_path / "missing-phase9"),
        ],
        cwd=REPO_ROOT,
        env=python_env(),
        check=False,
        capture_output=True,
        text=True,
    )
    assert missing_phase9.returncode != 0
    assert "Phase 9 aggregate" in missing_phase9.stderr


def test_phase10_runner_dry_run_writes_prediction_only_summary(tmp_path: Path) -> None:
    phase9 = tmp_path / "phase9.json"
    phase6_root = tmp_path / "phase6"
    _phase9_aggregate(phase9)
    _phase6_run(phase6_root, "S1", 42)
    out_root = tmp_path / "phase10"

    completed = subprocess.run(
        [
            PYTHON,
            str(RUNNER),
            "--config",
            str(CONFIG),
            "--stage",
            "limit50",
            "--dry-run",
            "--allow-limit50",
            "--skip-evaluator",
            "--allow-partial-dry-run",
            "--only-baseline",
            "S1",
            "--only-seed",
            "42",
            "--phase9-aggregate",
            str(phase9),
            "--phase6-runs-root",
            str(phase6_root),
            "--out-root",
            str(out_root),
        ],
        cwd=REPO_ROOT,
        env=python_env({"SAGE_DEE_PHASE10_FAKE_NVIDIA_SMI": "3,0,0\n0,7000,90\n"}),
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
    matrix = json.loads((out_root / "phase10_matrix_summary.json").read_text(encoding="utf-8"))
    assert matrix["scope"]["dataset"] == "ChFinAnn"
    assert matrix["scope"]["split"] == "dev"
    assert matrix["scope"]["train_used"] is False
    assert matrix["scope"]["test_used"] is False
    assert matrix["gate"]["full_dev_allowed"] is False
    assert len(matrix["runs"]) == 1

    run = matrix["runs"][0]
    assert run["baseline_id"] == "S1"
    assert run["seed"] == 42
    assert run["scope"]["no_chfinann_tuning"] is True
    assert run["limit50"]["canonical_rows"] == 50
    assert "train" not in run
    assert Path(run["run_dir"]).name.startswith("phase10_S1_seed42_")


def test_phase10_aggregator_dedupes_and_reports_required_metrics(tmp_path: Path) -> None:
    root = tmp_path / "runs"
    for baseline_id, seeds, base in (
        ("S1", [42, 43], 0.10),
        ("S2", [42, 43], 0.15),
        ("S4", [42, 43, 44], 0.16),
    ):
        for offset, seed in enumerate(seeds):
            _phase10_summary(root, baseline_id, seed, base + offset / 100)
    _phase10_summary(root, "S1", 42, 0.99, timestamp="20260504T000000Z")
    _phase10_summary(root, "S4", 44, 0.01, dry_run=True, timestamp="20260506T000000Z")
    out_json = tmp_path / "aggregate.json"
    out_md = tmp_path / "aggregate.md"

    completed = subprocess.run(
        [
            PYTHON,
            str(AGGREGATOR),
            "--runs-root",
            str(root),
            "--stage",
            "full-dev",
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
    aggregate = json.loads(out_json.read_text(encoding="utf-8"))
    rows = aggregate["by_baseline"]

    assert aggregate["dataset"] == "ChFinAnn"
    assert aggregate["split"] == "dev"
    assert rows["S1"]["seed_count"] == 2
    assert rows["S1"]["event_table_micro_f1"]["mean"] == pytest.approx(0.105)
    assert rows["S4"]["seed_count"] == 3
    assert rows["S4"]["seeds"] == [42, 43, 44]
    assert rows["S4"]["event_table_micro_f1"]["mean"] == pytest.approx(0.17)
    assert rows["S4"]["parse_error"]["mean"] == pytest.approx(2.0)
    assert rows["S4"]["schema_violation"]["mean"] == pytest.approx(4.0)
    assert rows["S4"]["surface_diagnostics"]["candidate_recall_at_10"]["n"] == 3
    assert aggregate["gate"]["required_seed_coverage"] is True
    assert aggregate["gate"]["test_blocked"] is True
    assert aggregate["claim_status"]["sota"]["status"] == "not_claimed"
    assert "robustness limitation" in aggregate["claim_status"]["limitation"]["status"]
    assert "S4" in out_md.read_text(encoding="utf-8")


def test_phase10_report_and_execution_state_record_required_scope_text() -> None:
    assert REPORT.exists()
    report = REPORT.read_text(encoding="utf-8")
    state = STATE.read_text(encoding="utf-8")

    for required in (
        "ChFinAnn frozen-profile robustness",
        "prediction-only",
        "S1/S2/S4",
        "seeds 42/43",
        "S4 seed 44",
        "schema invalid",
        "parse error",
        "role-level F1",
        "event-table micro-F1",
        "surface diagnostics",
        "evaluator benchmark root `/data/TJK/DEE/data/processed`",
        "test split: not run",
        "generalization/SOTA: not claimed",
        "limitation",
    ):
        assert required in report

    assert "phase10_chfinann_frozen_profile" in state
    assert "Phase 10 ChFinAnn frozen-profile robustness" in state
    assert "test remains blocked: YES" in state
    assert "no ChFinAnn prompt/parser/profile tuning: YES" in state
