from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from sage_dee.io_utils import read_yaml
from tests.v2.subprocess_utils import PYTHON, python_env

REPO_ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = REPO_ROOT / "configs/v2/sage_v2_v21_r7_thesis_minimal_matrix.yaml"
RUNNER = REPO_ROOT / "scripts/v2/run_v21_r7_thesis_minimal_matrix.py"
AGGREGATOR = REPO_ROOT / "scripts/v2/aggregate_v21_r7_thesis_minimal_matrix.py"
FINAL_RESULT_PATH = REPO_ROOT / "docs/refactor/SAGE_V2_FINAL_TEST_RESULT.json"


def test_config_declares_r7_dev_s2_s3_only_and_reuses_s4() -> None:
    config = read_yaml(CONFIG_PATH)

    assert config["phase"] == "R7"
    assert config["dataset"] == "DuEE-Fin-dev500"
    assert config["train_split"] == "train"
    assert config["eval_split"] == "dev"
    assert config["expected_train_limit"] == 6474
    assert config["systems_to_run"] == ["S2", "S3"]
    assert config["systems_to_reuse"] == ["S4"]
    assert config["seeds"] == [42, 43, 44]
    assert config["no_test"] is True
    assert config["allow_test"] is False
    assert config["no_s1"] is True
    assert config["no_v21_surface"] is True
    assert config["no_r4b_planner"] is True
    assert config["no_s4_retrain"] is True
    assert "S1" not in config["systems_to_run"]
    assert config["systems"]["S2"]["baseline_mode"] == "schema_only"
    assert config["systems"]["S2"]["surface"] == "none"
    assert config["systems"]["S3"]["baseline_mode"] == "role_safe"
    assert config["systems"]["S3"]["surface"] == "none"


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
                "--system",
                "S2",
                "--seed",
                "42",
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

    s1 = run("--system", "S1")
    assert s1.returncode == 2
    assert "rejects S1" in s1.stderr

    s4 = run("--system", "S4")
    assert s4.returncode == 2
    assert "rejects S4 retrain" in s4.stderr

    s5 = run("--system", "S5")
    assert s5.returncode == 2
    assert "only accepts S2/S3" in s5.stderr

    v21 = run("--surface", "v21_surface_opt_in_r2")
    assert v21.returncode == 2
    assert "rejects v21 surface" in v21.stderr

    planner = run("--planner", "r4b")
    assert planner.returncode == 2
    assert "rejects R4b planner" in planner.stderr


def test_runner_dry_run_writes_row_summary_and_manifests(tmp_path: Path) -> None:
    out_root = tmp_path / "S3_seed44"

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
            "--system",
            "S3",
            "--seed",
            "44",
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
    summary = json.loads((out_root / "row_summary.json").read_text(encoding="utf-8"))
    train_manifest = json.loads((out_root / "training_manifest.json").read_text(encoding="utf-8"))
    generation_manifest = json.loads((out_root / "generation_manifest.json").read_text(encoding="utf-8"))
    row_manifest = json.loads((out_root / "row_manifest.json").read_text(encoding="utf-8"))

    assert summary["phase"] == "R7 thesis minimal matrix"
    assert summary["system"] == "S3"
    assert summary["seed"] == 44
    assert summary["split"] == "dev"
    assert summary["surface"] == "none"
    assert summary["baseline_mode"] == "role_safe"
    assert summary["train_run"] is False
    assert summary["generation_run"] is False
    assert summary["evaluator_run"] is False
    assert summary["test_run"] is False
    assert summary["s1_run"] is False
    assert summary["s4_retrained"] is False
    assert summary["v21_surface_run"] is False
    assert summary["r4b_planner_run"] is False
    assert train_manifest["train_run"] is False
    assert generation_manifest["generation_run"] is False
    assert row_manifest["s4_retrained"] is False


def test_aggregator_requires_s2_s3_s4_seed_evidence(tmp_path: Path) -> None:
    run_root = tmp_path / "r7"
    r3_root = _write_r3_s4_seed42(tmp_path / "r3")
    r6_root = _write_r6_s4(tmp_path / "r6")
    _write_r7_row(run_root / "S2_seed42", "S2", 42, 0.50, 0.10)
    _write_r7_row(run_root / "S2_seed43", "S2", 43, 0.51, 0.11)
    _write_r7_row(run_root / "S2_seed44", "S2", 44, 0.52, 0.12)
    _write_r7_row(run_root / "S3_seed42", "S3", 42, 0.56, 0.16)
    _write_r7_row(run_root / "S3_seed43", "S3", 43, 0.57, 0.17)
    out_json = tmp_path / "summary.json"
    out_md = tmp_path / "summary.md"

    completed = subprocess.run(
        [
            PYTHON,
            str(AGGREGATOR),
            "--run-root",
            str(run_root),
            "--r6-s4-root",
            str(r6_root),
            "--r3-s4-seed42-root",
            str(r3_root),
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
    assert "missing R7 S3 seed44 summary" in completed.stderr


def test_aggregator_computes_deltas_and_verdict(tmp_path: Path) -> None:
    run_root = tmp_path / "r7"
    r3_root = _write_r3_s4_seed42(tmp_path / "r3", event_f1=0.737327, exact_f1=0.352248)
    r6_root = _write_r6_s4(tmp_path / "r6", seed43=(0.734293, 0.367965), seed44=(0.730063, 0.362573))
    for seed, event, exact in ((42, 0.50, 0.10), (43, 0.51, 0.11), (44, 0.52, 0.12)):
        _write_r7_row(run_root / f"S2_seed{seed}", "S2", seed, event, exact)
    for seed, event, exact in ((42, 0.56, 0.16), (43, 0.57, 0.17), (44, 0.58, 0.18)):
        _write_r7_row(run_root / f"S3_seed{seed}", "S3", seed, event, exact)
    out_json = tmp_path / "summary.json"
    out_md = tmp_path / "summary.md"

    completed = subprocess.run(
        [
            PYTHON,
            str(AGGREGATOR),
            "--run-root",
            str(run_root),
            "--r6-s4-root",
            str(r6_root),
            "--r3-s4-seed42-root",
            str(r3_root),
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

    assert summary["phase"] == "R7 thesis minimal matrix"
    assert summary["system_stats"]["S2"]["seed_count"] == 3
    assert summary["system_stats"]["S4"]["event_table_micro_f1"]["mean"] == pytest.approx(
        (0.737327 + 0.734293 + 0.730063) / 3
    )
    assert summary["deltas"]["S3_minus_S2"]["event_table_micro_f1"] == pytest.approx(0.06)
    assert summary["deltas"]["S4_minus_S3"]["exact_record_f1"] > 0.01
    assert summary["verdict"]["role_safe_effective"] is True
    assert summary["verdict"]["surface_memory_effective"] is True
    assert summary["verdict"]["thesis_experiment_viable"] is True
    assert summary["verdict"]["recommended_next_phase"] == "R8_procnet_and_thesis_tables"
    assert "thesis_experiment_viable" in report


def test_frozen_final_result_file_is_not_modified() -> None:
    assert FINAL_RESULT_PATH.is_file()
    result = subprocess.run(
        ["git", "diff", "--quiet", "--", str(FINAL_RESULT_PATH.relative_to(REPO_ROOT))],
        cwd=REPO_ROOT,
        check=False,
    )

    assert result.returncode == 0


def _write_r7_row(seed_dir: Path, system: str, seed: int, event_f1: float, exact_f1: float) -> None:
    seed_dir.mkdir(parents=True)
    payload = _row_payload(system=system, seed=seed, event_f1=event_f1, exact_f1=exact_f1)
    (seed_dir / "row_summary.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _write_r3_s4_seed42(root: Path, *, event_f1: float = 0.737327, exact_f1: float = 0.352248) -> Path:
    row_dir = root / "s4_full_or_max_frozen_surface"
    row_dir.mkdir(parents=True)
    payload = _row_payload(system="S4", seed=42, event_f1=event_f1, exact_f1=exact_f1)
    payload.update({"surface": "frozen_compressed_phase6_final_profile", "s4_retrained": False})
    (row_dir / "row_summary.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return root


def _write_r6_s4(
    root: Path,
    *,
    seed43: tuple[float, float] = (0.734293, 0.367965),
    seed44: tuple[float, float] = (0.730063, 0.362573),
) -> Path:
    for seed, (event_f1, exact_f1) in ((43, seed43), (44, seed44)):
        seed_dir = root / f"seed{seed}"
        seed_dir.mkdir(parents=True)
        payload = _row_payload(system="S4", seed=seed, event_f1=event_f1, exact_f1=exact_f1)
        payload.update({"surface": "frozen_compressed_phase6_final_profile", "s4_retrained": False})
        (seed_dir / "seed_summary.json").write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    return root


def _row_payload(system: str, seed: int, event_f1: float, exact_f1: float) -> dict[str, object]:
    return {
        "phase": "R7 thesis minimal matrix" if system in {"S2", "S3"} else "R6 reused S4",
        "system": system,
        "seed": seed,
        "dataset": "DuEE-Fin-dev500",
        "split": "dev",
        "surface": "none" if system in {"S2", "S3"} else "frozen_compressed_phase6_final_profile",
        "baseline_mode": {"S2": "schema_only", "S3": "role_safe"}.get(system, "role_safe_surface_memory"),
        "train_limit": 6474,
        "train_examples_seen": 6474,
        "train_run": system in {"S2", "S3"},
        "generation_run": True,
        "evaluator_run": True,
        "evaluator_validation_ok": True,
        "event_table_micro_f1": event_f1,
        "role_level_f1": event_f1,
        "exact_record_f1": exact_f1,
        "parse_error": 0,
        "schema_violation_rows": 1,
        "unknown_role": 0,
        "unknown_event_type": 0,
        "canonical_rows": 500,
        "canonical_event_count": 650 + seed,
        "accepted_event_count": 650 + seed,
        "dev_only": True,
        "test_run": False,
        "test_gold_read": False,
        "s1_run": False,
        "s4_retrained": False,
        "v21_surface_run": False,
        "r4b_planner_run": False,
        "chfinann_run": False,
        "docfee_run": False,
        "frozen_final_modified": False,
    }
