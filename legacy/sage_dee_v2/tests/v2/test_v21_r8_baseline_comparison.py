from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from sage_dee.io_utils import read_yaml, write_yaml
from tests.v2.subprocess_utils import PYTHON, python_env

REPO_ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = REPO_ROOT / "configs/v2/sage_v2_v21_r8_baseline_comparison.yaml"
RUNNER = REPO_ROOT / "scripts/v2/run_v21_r8_procnet_baseline_comparison.py"
AGGREGATOR = REPO_ROOT / "scripts/v2/aggregate_v21_r8_baseline_comparison.py"
FINAL_RESULT_PATH = REPO_ROOT / "docs/refactor/SAGE_V2_FINAL_TEST_RESULT.json"


def test_config_declares_no_test_no_procnet_training_and_no_sota() -> None:
    config = read_yaml(CONFIG_PATH)

    assert config["phase"] == "R8"
    assert config["dataset"] == "DuEE-Fin-dev500"
    assert config["split"] == "dev"
    assert config["test_enabled"] is False
    assert config["no_test"] is True
    assert config["no_procnet_training"] is True
    assert config["no_sota_claim"] is True
    assert config["procnet_seeds_to_check"] == [42, 43, 44]
    assert config["sage_r7_aggregate_json"].endswith("v21_r7_thesis_minimal_matrix_summary.json")
    assert "procnet_dueefin_unified_s44_dev" in config["procnet_existing_seed44_root"]


def test_runner_rejects_test_split(tmp_path: Path) -> None:
    config = _write_config(tmp_path)
    completed = _run_runner(
        tmp_path,
        "--config",
        str(config),
        "--dataset",
        "DuEE-Fin-dev500",
        "--split",
        "test",
        "--out-root",
        str(tmp_path / "out"),
        "--mode",
        "discover_and_reuse",
    )

    assert completed.returncode == 2
    assert "rejects test split" in completed.stderr


def test_runner_marks_missing_procnet_checkpoint_as_missing_not_rerun(tmp_path: Path) -> None:
    config = _write_config(tmp_path, checkpoint_seeds={44})
    out_root = tmp_path / "out"

    completed = _run_runner(
        tmp_path,
        "--config",
        str(config),
        "--dataset",
        "DuEE-Fin-dev500",
        "--split",
        "dev",
        "--out-root",
        str(out_root),
        "--mode",
        "discover_and_reuse",
    )

    assert completed.returncode == 0, completed.stderr
    seed42 = json.loads((out_root / "procnet_seed42" / "seed_summary.json").read_text(encoding="utf-8"))
    discovery = json.loads((out_root / "checkpoint_discovery.json").read_text(encoding="utf-8"))

    assert seed42["status"] == "missing_not_rerun"
    assert seed42["procnet_training_run"] is False
    assert discovery["seeds"]["42"]["status"] == "missing"


def test_runner_refuses_ambiguous_checkpoint(tmp_path: Path) -> None:
    config = _write_config(tmp_path, checkpoint_seeds={44}, ambiguous_seed=42)
    out_root = tmp_path / "out"

    completed = _run_runner(
        tmp_path,
        "--config",
        str(config),
        "--dataset",
        "DuEE-Fin-dev500",
        "--split",
        "dev",
        "--out-root",
        str(out_root),
        "--mode",
        "discover_and_reuse",
    )

    assert completed.returncode == 0, completed.stderr
    seed42 = json.loads((out_root / "procnet_seed42" / "seed_summary.json").read_text(encoding="utf-8"))

    assert seed42["status"] == "ambiguous_checkpoint_skipped"
    assert seed42["direct_comparable"] is False
    assert len(seed42["checkpoint_candidates"]) == 2


def test_runner_marks_available_checkpoint_as_pending_export(tmp_path: Path) -> None:
    config = _write_config(tmp_path, checkpoint_seeds={42, 44})
    out_root = tmp_path / "out"

    completed = _run_runner(
        tmp_path,
        "--config",
        str(config),
        "--dataset",
        "DuEE-Fin-dev500",
        "--split",
        "dev",
        "--out-root",
        str(out_root),
        "--mode",
        "discover_and_reuse",
    )

    assert completed.returncode == 0, completed.stderr
    seed42 = json.loads((out_root / "procnet_seed42" / "seed_summary.json").read_text(encoding="utf-8"))

    assert seed42["status"] == "available_pending_export"
    assert seed42["direct_comparable"] is False
    assert seed42["checkpoint_discovery_status"] == "available"


def test_runner_requires_split_audit_before_canonical_export(tmp_path: Path) -> None:
    config = _write_config(tmp_path, checkpoint_seeds={42, 44}, create_procnet_view=False)
    out_root = tmp_path / "out"

    completed = _run_runner(
        tmp_path,
        "--config",
        str(config),
        "--dataset",
        "DuEE-Fin-dev500",
        "--split",
        "dev",
        "--out-root",
        str(out_root),
        "--mode",
        "export_eval_existing_checkpoint",
        "--seed",
        "42",
    )

    assert completed.returncode == 2
    assert "split audit failed before canonical export" in completed.stderr
    assert not (out_root / "procnet_seed42" / "predictions").exists()


def test_runner_does_not_train_procnet(tmp_path: Path) -> None:
    config = _write_config(tmp_path, checkpoint_seeds={44})
    out_root = tmp_path / "out"

    completed = _run_runner(
        tmp_path,
        "--config",
        str(config),
        "--dataset",
        "DuEE-Fin-dev500",
        "--split",
        "dev",
        "--out-root",
        str(out_root),
        "--mode",
        "discover_and_reuse",
    )

    assert completed.returncode == 0, completed.stderr
    summary = json.loads((out_root / "discover_and_reuse_summary.json").read_text(encoding="utf-8"))

    assert summary["scope"]["no_procnet_training"] is True
    assert summary["scope"]["procnet_training_run"] is False
    assert "train_procnet" not in RUNNER.read_text(encoding="utf-8")


def test_aggregator_distinguishes_direct_comparable_from_reference_only(tmp_path: Path) -> None:
    r7_summary = _write_r7_summary(tmp_path / "r7_summary.json")
    phase8_root = _write_phase8_seed44(tmp_path / "phase8")
    run_root = tmp_path / "run"
    _write_procnet_seed(
        run_root,
        44,
        strict_f1=0.69,
        exact_f1=0.20,
        status="direct_comparable_reused",
    )
    _write_procnet_seed(
        run_root,
        42,
        strict_f1=0.99,
        exact_f1=0.99,
        status="native_reference_only",
        native_micro_f1=0.99,
    )
    out_json = tmp_path / "summary.json"
    out_md = tmp_path / "summary.md"

    completed = _run_aggregator(run_root, r7_summary, phase8_root, out_json, out_md)

    assert completed.returncode == 0, completed.stderr
    summary = json.loads(out_json.read_text(encoding="utf-8"))

    assert summary["procnet"]["direct_comparable_seed_count"] == 1
    assert summary["procnet"]["reference_only_seed_count"] == 1
    assert summary["procnet"]["stats"]["strict_f1"]["mean"] == pytest.approx(0.69)
    assert summary["procnet"]["reference_only"][0]["native_micro_f1"] == pytest.approx(0.99)


def test_aggregator_computes_sage_vs_procnet_deltas_and_verdict(tmp_path: Path) -> None:
    r7_summary = _write_r7_summary(tmp_path / "r7_summary.json")
    phase8_root = _write_phase8_seed44(tmp_path / "phase8")
    run_root = tmp_path / "run"
    _write_procnet_seed(
        run_root,
        44,
        strict_f1=0.6925015752993069,
        exact_f1=0.20809248554913296,
        status="direct_comparable_reused",
    )
    out_json = tmp_path / "summary.json"
    out_md = tmp_path / "summary.md"

    completed = _run_aggregator(run_root, r7_summary, phase8_root, out_json, out_md)

    assert completed.returncode == 0, completed.stderr
    summary = json.loads(out_json.read_text(encoding="utf-8"))
    report = out_md.read_text(encoding="utf-8")

    assert summary["deltas"]["S4_mean_minus_ProcNet_seed44_strict_f1"] == pytest.approx(
        0.7338943109332204 - 0.6925015752993069
    )
    assert summary["deltas"]["S4_exact_mean_minus_ProcNet_seed44_exact_record_f1"] == pytest.approx(
        0.36092869079720885 - 0.20809248554913296
    )
    assert summary["verdict"]["procnet_direct_comparable_available"] is True
    assert summary["verdict"]["sage_v21_beats_procnet_seed44_strict"] is True
    assert summary["verdict"]["sage_v21_beats_procnet_seed44_exact"] is True
    assert summary["verdict"]["thesis_table_ready"] is True
    assert summary["verdict"]["ccfa_claim_ready"] is False
    assert "Native ProcNet scores are reference-only" in report


def test_frozen_final_result_file_is_not_modified() -> None:
    assert FINAL_RESULT_PATH.is_file()
    result = subprocess.run(
        ["git", "diff", "--quiet", "--", str(FINAL_RESULT_PATH.relative_to(REPO_ROOT))],
        cwd=REPO_ROOT,
        check=False,
    )

    assert result.returncode == 0


def _run_runner(tmp_path: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [PYTHON, str(RUNNER), *args],
        cwd=REPO_ROOT,
        env=python_env({"R8_LOCAL_TEST_ROOT": tmp_path}),
        check=False,
        capture_output=True,
        text=True,
    )


def _run_aggregator(
    run_root: Path,
    r7_summary: Path,
    phase8_root: Path,
    out_json: Path,
    out_md: Path,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            PYTHON,
            str(AGGREGATOR),
            "--run-root",
            str(run_root),
            "--r7-summary",
            str(r7_summary),
            "--phase8-procnet-root",
            str(phase8_root),
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


def _write_config(
    tmp_path: Path,
    *,
    checkpoint_seeds: set[int] | None = None,
    ambiguous_seed: int | None = None,
    create_procnet_view: bool = True,
) -> Path:
    checkpoint_root = tmp_path / "procnet" / "Checkpoint"
    workspace_root = tmp_path / "procnet" / "workspaces"
    for seed in checkpoint_seeds or set():
        checkpoint = checkpoint_root / f"procnet_dueefin_unified_s{seed}" / "best.pt"
        checkpoint.parent.mkdir(parents=True)
        checkpoint.write_text(f"seed {seed}\n", encoding="utf-8")
    if ambiguous_seed is not None:
        for index in (1, 2):
            candidate = workspace_root / f"unified_dueefin_s{ambiguous_seed}_{index}" / "best.pt"
            candidate.parent.mkdir(parents=True)
            candidate.write_text(f"ambiguous {index}\n", encoding="utf-8")

    data_root = tmp_path / "data"
    if create_procnet_view:
        procnet_view = data_root / "processed/procnet/DuEE-Fin-dev500_ProcNet_Doc2EDAG/dev.json"
        procnet_view.parent.mkdir(parents=True)
        procnet_view.write_text(json.dumps([["doc-1", {"sentences": ["甲公司公告。"]}]]), encoding="utf-8")
    evaluator_view = data_root / "processed/views/evaluator_gold/DuEE-Fin-dev500/dev.jsonl"
    evaluator_view.parent.mkdir(parents=True)
    evaluator_view.write_text(json.dumps({"doc_id": "doc-1", "content": "甲公司公告。"}) + "\n", encoding="utf-8")

    r7_summary = _write_r7_summary(tmp_path / "r7_summary.json")
    phase8_root = _write_phase8_seed44(tmp_path / "phase8")
    config = {
        "phase": "R8",
        "dataset": "DuEE-Fin-dev500",
        "split": "dev",
        "test_enabled": False,
        "sage_r7_aggregate_json": str(r7_summary),
        "procnet_existing_seed44_root": str(phase8_root),
        "procnet_existing_seed44_evaluator_artifact_root": str(
            phase8_root / "evaluator/procnet_dueefin_unified_s44_dev/analysis/DuEE-Fin-dev500/dev"
        ),
        "procnet_checkpoint_search_roots": [str(checkpoint_root), str(workspace_root)],
        "procnet_seeds_to_check": [42, 43, 44],
        "procnet_python": PYTHON,
        "sage_python": PYTHON,
        "evaluator_root": str(tmp_path / "dee-eval"),
        "data_root": str(data_root),
        "procnet_workdir": str(tmp_path / "procnet_workdir"),
        "procnet_export_script": str(tmp_path / "procnet_export.py"),
        "no_procnet_training": True,
        "no_test": True,
        "no_sota_claim": True,
    }
    config_path = tmp_path / "r8.yaml"
    write_yaml(config_path, config)
    return config_path


def _write_r7_summary(path: Path) -> Path:
    payload = {
        "phase": "R7 thesis minimal matrix",
        "scope": {"test_run": False, "test_gold_read": False},
        "system_stats": {
            "S2": _stats(0.6220266086681092, 0.005207960170969922, 0.12848650277289606, 0.010964277533173309),
            "S3": _stats(0.7302975998988174, 0.003279797305633346, 0.3441823285284442, 0.0030423781370824197),
            "S4": _stats(0.7338943109332204, 0.0029788933458154416, 0.36092869079720885, 0.006521251303709938),
        },
        "deltas": {
            "S3_minus_S2": {
                "event_table_micro_f1": 0.10827099123070816,
                "exact_record_f1": 0.21569582575554816,
            },
            "S4_minus_S3": {
                "event_table_micro_f1": 0.003596711034403066,
                "exact_record_f1": 0.016746362268764636,
            },
            "S4_minus_S2": {
                "event_table_micro_f1": 0.11186770226511122,
                "exact_record_f1": 0.2324421880243128,
            },
        },
        "verdict": {
            "recommended_next_phase": "R8_procnet_and_thesis_tables",
            "role_safe_effective": True,
            "surface_memory_effective": True,
            "thesis_experiment_viable": True,
        },
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def _stats(event_mean: float, event_std: float, exact_mean: float, exact_std: float) -> dict[str, object]:
    return {
        "seed_count": 3,
        "seeds": [42, 43, 44],
        "event_table_micro_f1": {"mean": event_mean, "std": event_std, "n": 3},
        "role_level_f1": {"mean": event_mean, "std": event_std, "n": 3},
        "exact_record_f1": {"mean": exact_mean, "std": exact_std, "n": 3},
    }


def _write_phase8_seed44(root: Path) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    (root / "split_audit.json").write_text(
        json.dumps(
            {
                "dataset": "DuEE-Fin-dev500",
                "split": "dev",
                "direct_comparable_split": True,
                "ids_same_order": True,
                "content_normalized_same_order": True,
            }
        )
        + "\n",
        encoding="utf-8",
    )
    (root / "phase8_procnet_export_summary.json").write_text(
        json.dumps(
            {
                "baseline": "ProcNet",
                "dataset": "DuEE-Fin-dev500",
                "split": "dev",
                "seed": 44,
                "canonical_rows": 500,
                "canonical_event_count": 703,
                "checkpoint": "/tmp/procnet_dueefin_unified_s44/best.pt",
                "test_used": False,
            }
        )
        + "\n",
        encoding="utf-8",
    )
    (root / "run_manifest.json").write_text(
        json.dumps(
            {
                "method_name": "ProcNet",
                "seed": 44,
                "split_version": "dev",
                "test_used": False,
                "procnet_workdir": "/tmp/procnet_workdir",
                "procnet_export_script": "/tmp/procnet_export.py",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    analysis = root / "evaluator/procnet_dueefin_unified_s44_dev/analysis/DuEE-Fin-dev500/dev"
    analysis.mkdir(parents=True)
    (analysis / "validation_report.json").write_text(
        json.dumps({"ok": True, "counts": {"num_docs": 500, "possible_gold_leakage_field_count": 0}}) + "\n",
        encoding="utf-8",
    )
    (analysis / "overall_metrics.json").write_text(
        json.dumps(
            {
                "metric": "U-Text-F1-Strict",
                "f1": 0.6925015752993069,
                "precision": 0.7545485753518709,
                "recall": 0.6398835516739447,
                "uses_naen": False,
                "uses_offset": False,
            }
        )
        + "\n",
        encoding="utf-8",
    )
    (analysis / "record_level_metrics.json").write_text(
        json.dumps({"record_f1_exact": 0.20809248554913296, "record_f1_soft_0_8": 0.4364161849710983})
        + "\n",
        encoding="utf-8",
    )
    return root


def _write_procnet_seed(
    run_root: Path,
    seed: int,
    *,
    strict_f1: float,
    exact_f1: float,
    status: str,
    native_micro_f1: float | None = None,
) -> None:
    seed_dir = run_root / f"procnet_seed{seed}"
    seed_dir.mkdir(parents=True)
    payload = {
        "phase": "R8 ProcNet baseline comparison",
        "baseline": "ProcNet",
        "seed": seed,
        "dataset": "DuEE-Fin-dev500",
        "split": "dev",
        "status": status,
        "direct_comparable": status.startswith("direct_comparable"),
        "reference_only": status == "native_reference_only",
        "validation_ok": status.startswith("direct_comparable"),
        "strict_f1": strict_f1,
        "exact_record_f1": exact_f1,
        "native_micro_f1": native_micro_f1,
        "test_run": False,
        "procnet_training_run": False,
        "evaluator_modified": False,
    }
    (seed_dir / "seed_summary.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
