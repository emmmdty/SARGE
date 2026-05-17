from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from tests.v2.subprocess_utils import PYTHON, python_env

REPO_ROOT = Path(__file__).resolve().parents[2]
CONFIG = REPO_ROOT / "configs/v2/sage_v2_phase4_prompt_baselines.yaml"
RUNNER = REPO_ROOT / "scripts/v2/run_phase9_prompt_full_dev.py"
AGGREGATOR = REPO_ROOT / "scripts/v2/aggregate_phase9_duee_fin_main_table.py"
REPORT = REPO_ROOT / "docs/refactor/SAGE_V2_PHASE9_DUEE_FIN_FULL_DEV_MAIN_TABLE.md"
STATE = REPO_ROOT / "docs/refactor/SAGE_V2_EXECUTION_STATE.md"


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _phase4_limit50_root(tmp_path: Path) -> Path:
    root = tmp_path / "phase4_limit50"
    rows = []
    for baseline_id, profile, mode in (
        ("P1", "phase4_p1_direct_json", "direct_json"),
        ("P2", "phase4_p2_schema_only", "schema_only"),
        ("P3", "phase4_p3_role_safe", "role_safe"),
        ("P4", "phase4_p4_role_safe_surface_memory", "role_safe_surface_memory"),
    ):
        run_dir = root / baseline_id
        _write_json(
            run_dir / "generation_manifest.json",
            {
                "document_count": 50,
                "profile": profile,
                "baseline_mode": mode,
                "dataset": "DuEE-Fin-dev500",
                "split": "dev",
                "gold_visible": False,
            },
        )
        rows.append(
            {
                "baseline_id": baseline_id,
                "profile": profile,
                "baseline_mode": mode,
                "canonical_rows": 50,
                "evaluator_attempted": True,
                "evaluator_validation_ok": True,
                "parse_error": 0,
                "run_dir": str(run_dir),
            }
        )
    _write_json(root / "summary.json", {"baselines": rows})
    return root


def _prompt_summary(root: Path, baseline_id: str, seed: int, f1: float, *, dry_run: bool = False) -> None:
    run_dir = root / f"phase9_{baseline_id}_seed{seed}_20260505T000000Z"
    payload = {
        "phase": "Phase 9 prompt full-dev",
        "baseline_id": baseline_id,
        "profile": f"phase4_{baseline_id.lower()}",
        "label": baseline_id,
        "baseline_mode": "role_safe" if baseline_id == "P3" else "role_safe_surface_memory",
        "seed": seed,
        "run_dir": str(run_dir),
        "scope": {
            "dataset": "DuEE-Fin-dev500",
            "split": "dev",
            "document_count": 500,
            "full_dev_used": True,
            "test_used": False,
            "train_used": False,
            "full_train_used": False,
            "dry_run": dry_run,
            "real_run": not dry_run,
        },
        "full_dev": {
            "canonical_rows": 500,
            "parse_error": 1,
            "schema_violation_rows": 2,
            "schema_violation": 3,
            "unknown_role": 4 if baseline_id == "P2" else 0,
            "unknown_event_type": 0,
            "evaluator_attempted": True,
            "evaluator_validation_ok": True,
            "event_table_micro_f1": f1,
            "role_level_f1": f1,
            "exact_record_f1": f1 / 10,
            "parse_valid_subset": {
                "doc_count": 499,
                "source_doc_count": 500,
                "event_table_micro_f1": f1 + 0.01,
                "role_level_f1": f1 + 0.01,
                "exact_record_f1": f1 / 10,
            },
        },
    }
    _write_json(run_dir / "phase9_prompt_run_summary.json", payload)


def _phase6_aggregate(path: Path) -> None:
    by_baseline = {}
    for baseline_id, mean in (("S1", 0.1), ("S2", 0.2), ("S3", 0.3), ("S4", 0.4)):
        by_baseline[baseline_id] = {
            "seed_count": 2,
            "seeds": [42, 43],
            "event_table_micro_f1": {"mean": mean, "std": 0.01, "n": 2},
            "role_level_f1": {"mean": mean, "std": 0.01, "n": 2},
            "exact_record_f1": {"mean": mean / 10, "std": 0.001, "n": 2},
            "parse_valid_subset_event_table_micro_f1": {"mean": mean + 0.01, "std": 0.01, "n": 2},
            "parse_valid_subset_role_level_f1": {"mean": mean + 0.01, "std": 0.01, "n": 2},
            "parse_valid_subset_exact_record_f1": {"mean": mean / 10, "std": 0.001, "n": 2},
            "parse_valid_subset_doc_count": {"min": 490, "max": 491},
            "test_used": False,
            "full_train_used": False,
        }
    _write_json(
        path,
        {
            "stage": "full_dev",
            "run_count": 8,
            "by_baseline": by_baseline,
            "gate": {
                "s4_not_below_s1_s2": True,
                "parse_valid_subset_improved": True,
                "parse_only_improvement": False,
                "test_blocked": True,
                "full_train_blocked": True,
            },
        },
    )


def _phase7_aggregate(path: Path) -> None:
    _write_json(
        path,
        {
            "stage": "full_dev",
            "run_count": 6,
            "by_variant": {
                "no_surface": {
                    "seed_count": 3,
                    "seeds": [42, 43, 44],
                    "event_table_micro_f1": {"mean": 0.35, "std": 0.01, "n": 3},
                    "role_level_f1": {"mean": 0.35, "std": 0.01, "n": 3},
                    "exact_record_f1": {"mean": 0.03, "std": 0.001, "n": 3},
                    "hallucinated_argument_rate": {"mean": 0.07, "std": 0.001, "n": 3},
                    "non_surface_argument_rate": {"mean": 1.0, "std": 0.0, "n": 3},
                },
                "compressed_surface": {
                    "seed_count": 3,
                    "seeds": [42, 43, 44],
                    "event_table_micro_f1": {"mean": 0.4, "std": 0.01, "n": 3},
                    "role_level_f1": {"mean": 0.4, "std": 0.01, "n": 3},
                    "exact_record_f1": {"mean": 0.04, "std": 0.001, "n": 3},
                    "parse_valid_subset_event_table_micro_f1": {"mean": 0.41, "std": 0.01, "n": 3},
                    "parse_valid_subset_role_level_f1": {"mean": 0.41, "std": 0.01, "n": 3},
                    "parse_valid_subset_exact_record_f1": {"mean": 0.04, "std": 0.001, "n": 3},
                    "hallucinated_argument_rate": {"mean": 0.03, "std": 0.001, "n": 3},
                    "non_surface_argument_rate": {"mean": 0.8, "std": 0.01, "n": 3},
                    "candidate_recall_at_10": {"mean": 0.15, "std": 0.01, "n": 3},
                    "candidate_precision": {"mean": 0.12, "std": 0.01, "n": 3},
                },
            },
            "gate": {
                "claim_status": "retain",
                "surface_memory_main_contribution": True,
                "test_blocked": True,
                "full_train_blocked": True,
            },
        },
    )


def _phase8_artifacts(run_root: Path, evaluator_root: Path) -> None:
    _write_json(run_root / "phase8_procnet_export_summary.json", {"canonical_rows": 500, "canonical_events": 703})
    _write_json(
        evaluator_root / "metrics/unified_main/DuEE-Fin-dev500/dev/overall_metrics.json",
        {"precision": 0.7, "recall": 0.6, "f1": 0.65, "tp": 10, "fp": 2, "fn": 3},
    )
    _write_json(
        evaluator_root / "analysis/DuEE-Fin-dev500/dev/record_level_metrics.json",
        {"record_f1_exact": 0.2},
    )
    _write_json(
        evaluator_root / "analysis/DuEE-Fin-dev500/dev/validation_report.json",
        {"ok": True, "missing_doc_id_in_prediction_count": 0},
    )


def test_phase9_prompt_runner_rejects_test_and_requires_phase4_limit50_gate(tmp_path: Path) -> None:
    no_gate = subprocess.run(
        [
            PYTHON,
            str(RUNNER),
            "--config",
            str(CONFIG),
            "--phase4-limit50-root",
            str(tmp_path / "missing"),
            "--dry-run",
            "--allow-full-dev",
            "--split",
            "test",
            "--out-root",
            str(tmp_path / "out"),
        ],
        cwd=REPO_ROOT,
        env=python_env(),
        check=False,
        capture_output=True,
        text=True,
    )

    assert no_gate.returncode != 0
    assert "test split" in no_gate.stderr

    missing_gate = subprocess.run(
        [
            PYTHON,
            str(RUNNER),
            "--config",
            str(CONFIG),
            "--phase4-limit50-root",
            str(tmp_path / "missing"),
            "--dry-run",
            "--allow-full-dev",
            "--out-root",
            str(tmp_path / "out"),
        ],
        cwd=REPO_ROOT,
        env=python_env(),
        check=False,
        capture_output=True,
        text=True,
    )

    assert missing_gate.returncode != 0
    assert "Phase 4 limit50 summary" in missing_gate.stderr


def test_phase9_aggregator_builds_main_table_and_rejects_dry_run_prompt_rows(tmp_path: Path) -> None:
    prompt_root = tmp_path / "prompt"
    for baseline_id, base in (("P1", 0.05), ("P2", 0.10), ("P3", 0.15), ("P4", 0.20)):
        _prompt_summary(prompt_root, baseline_id, 42, base)
        _prompt_summary(prompt_root, baseline_id, 43, base + 0.02)
        _prompt_summary(prompt_root, baseline_id, 44, base + 0.04)
    _prompt_summary(prompt_root, "P4", 41, 0.99, dry_run=True)
    phase4 = _phase4_limit50_root(tmp_path)
    phase6 = tmp_path / "phase6.json"
    phase7 = tmp_path / "phase7.json"
    phase8_run = tmp_path / "phase8_run"
    phase8_eval = tmp_path / "phase8_eval"
    _phase6_aggregate(phase6)
    _phase7_aggregate(phase7)
    _phase8_artifacts(phase8_run, phase8_eval)
    out_json = tmp_path / "phase9.json"
    out_md = tmp_path / "phase9.md"

    completed = subprocess.run(
        [
            PYTHON,
            str(AGGREGATOR),
            "--prompt-full-dev-root",
            str(prompt_root),
            "--phase4-limit50-summary",
            str(phase4 / "summary.json"),
            "--phase6-full-dev",
            str(phase6),
            "--phase7-full-dev",
            str(phase7),
            "--phase8-run-root",
            str(phase8_run),
            "--phase8-evaluator-root",
            str(phase8_eval),
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
    rows = {row["system_id"]: row for row in aggregate["main_table"]}

    assert rows["P4"]["n"] == 3
    assert rows["P4"]["event_table_micro_f1"]["mean"] == pytest.approx(0.22)
    assert rows["ProcNet"]["n"] == 1
    assert rows["ProcNet"]["event_table_micro_f1"]["std"] is None
    assert aggregate["gate"]["no_test_used"] is True
    assert aggregate["gate"]["no_post_full_dev_tuning_declared"] is True
    assert aggregate["claim_status"]["sota"]["status"] == "delete"
    assert "P4" in out_md.read_text(encoding="utf-8")


def test_phase9_report_and_execution_state_record_required_gate_text() -> None:
    report = REPORT.read_text(encoding="utf-8")
    state = STATE.read_text(encoding="utf-8")

    for required in (
        "DuEE-Fin full dev main table",
        "error taxonomy",
        "no post-full-dev tuning",
        "P1-P4",
        "S1-S4",
        "ProcNet",
        "test split: not run",
        "SOTA: not claimed",
    ):
        assert required in report

    assert "phase9_duee_fin_full_dev_main_table" in state
    assert "chfinann_frozen_profile: allowed" in state
    assert "test remains blocked: YES" in state
