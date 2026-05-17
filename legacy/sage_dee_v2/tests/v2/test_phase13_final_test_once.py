from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from sage_dee.io_utils import read_yaml
from scripts.v2.run_phase13_final_test_once import (
    build_final_resolved_config,
    build_final_test_result_payload,
    build_phase13_recovery_log_wrapper_command,
    build_phase13_run_manifest,
    resolve_manifest_command,
    validate_final_args,
    validate_manifest_adapter_path,
    validate_phase13_recovery_authorization,
    validate_recovery_roots,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
MANIFEST_PATH = REPO_ROOT / "docs/refactor/SAGE_V2_FINAL_FREEZE_MANIFEST.json"
CONFIG_PATH = REPO_ROOT / "configs/v2/sage_v2_phase11_docfee_stress.yaml"
PHASE13_REPORT_PATH = REPO_ROOT / "docs/refactor/SAGE_V2_PHASE13_FINAL_TEST_ONCE.md"
PHASE13_1_REPORT_PATH = REPO_ROOT / "docs/refactor/SAGE_V2_PHASE13_1_FAILURE_FORENSIC_AUDIT.md"
RESULT_PATH = REPO_ROOT / "docs/refactor/SAGE_V2_FINAL_TEST_RESULT.json"
STATE_PATH = REPO_ROOT / "docs/refactor/SAGE_V2_EXECUTION_STATE.md"
OLD_ADAPTER_PATH = "/data/TJK/DEE/sage-dee/runs/phase6_S4_seed42_20260504T052553Z/adapter"
REPAIRED_ADAPTER_PATH = (
    "/data/TJK/DEE/sage-dee/runs/phase6_S4_seed42_20260504T052553Z/train/artifacts/model/adapter"
)
PHASE6_SEED42_RUN_PATH = "/data/TJK/DEE/sage-dee/runs/phase6_S4_seed42_20260504T052553Z"
PHASE13_2A_ADAPTER_HASH = "e3da2ec526dcc7dd46c2412841e71943cf602087575f3882ade10d70343bcab0"


def _manifest() -> dict:
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def _result() -> dict:
    return json.loads(RESULT_PATH.read_text(encoding="utf-8"))


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _args(tmp_path: Path) -> SimpleNamespace:
    return SimpleNamespace(
        config=CONFIG_PATH,
        manifest=MANIFEST_PATH,
        dataset="DuEE-Fin-dev500",
        split="test",
        seed=42,
        profile="phase11_s4_role_safe_surface_memory",
        data_root=None,
        phase6_runs_root=Path("/data/TJK/DEE/sage-dee/runs"),
        adapter_path=Path(REPAIRED_ADAPTER_PATH),
        evaluator_root=Path("/home/TJK/DEE/dee-eval"),
        benchmark_root=Path("/data/TJK/DEE/data/processed"),
        out_dir=tmp_path / "phase13_final_test_seed42_20260506T120000Z",
        allow_human_authorized_operational_recovery=False,
    )


def _adapter_manifest(path: Path, *, phase6_run_path: Path | None = None) -> dict:
    manifest = _manifest()
    manifest["SFT_checkpoint"]["adapter_path"] = str(path)
    manifest["SFT_checkpoint"]["phase6_seed42_run_path"] = str(phase6_run_path or path.parents[3])
    manifest["final_test_command"]["command"] = manifest["final_test_command"]["command"].replace(
        OLD_ADAPTER_PATH,
        str(path),
    )
    return manifest


def _write_minimal_adapter(path: Path) -> None:
    path.mkdir(parents=True)
    (path / "adapter_config.json").write_text("{}", encoding="utf-8")
    (path / "adapter_model.safetensors").write_bytes(b"phase13.2a adapter preflight")


def test_phase13_command_resolution_only_replaces_run_root_timestamp() -> None:
    command = _manifest()["final_test_command"]["command"]

    resolved = resolve_manifest_command(command, "20260506T120000Z")

    assert "<timestamp>" not in resolved
    assert "RUN_ROOT=/data/TJK/DEE/sage-dee/runs/phase13_final_test_seed42_20260506T120000Z" in resolved
    assert "--seed 42" in resolved
    assert "--dataset DuEE-Fin-dev500" in resolved
    assert "--split test" in resolved
    assert '--out-dir "${RUN_ROOT}"' in resolved


def test_phase13_command_resolution_rejects_timestamp_outside_run_root() -> None:
    command = _manifest()["final_test_command"]["command"] + " --adapter-path /tmp/<timestamp>"

    with pytest.raises(ValueError, match="only appear in RUN_ROOT"):
        resolve_manifest_command(command, "20260506T120000Z")


def test_phase13_resolved_config_preserves_frozen_final_test_settings(tmp_path: Path) -> None:
    manifest = _manifest()
    config = read_yaml(CONFIG_PATH)
    args = _args(tmp_path)

    validate_final_args(args, config, manifest, require_adapter_exists=False)
    resolved = build_final_resolved_config(config, args=args)

    assert resolved["run"]["profile"] == "phase11_s4_role_safe_surface_memory"
    assert resolved["run"]["baseline_id"] == "S4"
    assert resolved["run"]["dry_run"] is False
    assert resolved["run"]["real_run"] is True
    assert resolved["data"]["dataset"] == "DuEE-Fin-dev500"
    assert resolved["data"]["max_train_docs"] == 0
    assert resolved["data"]["max_predict_docs"] is None
    assert resolved["predict"]["dataset"] == "DuEE-Fin-dev500"
    assert resolved["predict"]["split"] == "test"
    assert resolved["predict"]["max_predict_docs"] is None
    assert resolved["getm"]["qwen"]["adapter_path"] == manifest["SFT_checkpoint"]["adapter_path"]
    assert resolved["getm"]["generation"]["seed"] == 42
    assert resolved["getm"]["generation"]["do_sample"] is False
    assert resolved["getm"]["generation"]["temperature"] is None
    assert resolved["getm"]["generation"]["top_p"] == 1.0


def test_manifest_adapter_path_exists_or_preflight_required(tmp_path: Path) -> None:
    adapter_path = tmp_path / "phase6_S4_seed42_20260504T052553Z" / "train/artifacts/model/adapter"
    _write_minimal_adapter(adapter_path)
    manifest = _adapter_manifest(adapter_path)

    validate_manifest_adapter_path(Path(manifest["SFT_checkpoint"]["adapter_path"]), manifest)

    repaired = _manifest()["SFT_checkpoint"]
    assert repaired["adapter_path"] == REPAIRED_ADAPTER_PATH
    assert repaired["checkpoint_hash"]["status"] == "computed_server_preflight_phase13_2a"
    assert repaired["checkpoint_hash"]["sha256"] == PHASE13_2A_ADAPTER_HASH


def test_cli_adapter_path_must_match_manifest(tmp_path: Path) -> None:
    manifest = _manifest()
    config = read_yaml(CONFIG_PATH)
    args = _args(tmp_path)
    args.adapter_path = Path(REPAIRED_ADAPTER_PATH).parent / "wrong_adapter"

    with pytest.raises(ValueError, match="adapter path must match the freeze manifest"):
        validate_final_args(args, config, manifest)


def test_adapter_path_must_be_under_phase6_seed42_run(tmp_path: Path) -> None:
    adapter_path = tmp_path / "other_run" / "train/artifacts/model/adapter"
    phase6_run_path = tmp_path / "phase6_S4_seed42_20260504T052553Z"
    _write_minimal_adapter(adapter_path)
    manifest = _adapter_manifest(adapter_path, phase6_run_path=phase6_run_path)

    with pytest.raises(ValueError, match="under manifest phase6_seed42_run_path"):
        validate_manifest_adapter_path(adapter_path, manifest)


def test_manifest_pointer_repair_does_not_change_seed_dataset_split_final_system() -> None:
    manifest = _manifest()

    assert manifest["final_system_id"] == "S4"
    assert manifest["final_seed_strategy"]["selected_strategy"] == "primary_seed_42_single_final_test"
    assert manifest["final_seed_strategy"]["primary_seed"] == 42
    assert manifest["final_system_scope"]["primary_dataset"] == "DuEE-Fin-dev500"
    assert manifest["final_system_scope"]["primary_split"] == "test"
    assert manifest["SFT_checkpoint"]["baseline_id"] == "S4"
    assert manifest["SFT_checkpoint"]["seed"] == 42
    assert manifest["SFT_checkpoint"]["LoRA_config"] == {
        "alpha": 32,
        "dropout": 0.05,
        "rank": 16,
        "target_modules": ["q_proj", "k_proj", "v_proj", "o_proj"],
    }


def test_final_test_command_uses_manifest_adapter_path() -> None:
    manifest = _manifest()
    adapter_path = manifest["SFT_checkpoint"]["adapter_path"]
    command = manifest["final_test_command"]["command"]

    assert adapter_path == REPAIRED_ADAPTER_PATH
    assert f"--adapter-path {adapter_path}" in command
    assert OLD_ADAPTER_PATH not in command


def test_checkpoint_hash_command_uses_manifest_adapter_path() -> None:
    manifest = _manifest()
    adapter_path = manifest["SFT_checkpoint"]["adapter_path"]
    command = manifest["SFT_checkpoint"]["checkpoint_hash"]["command_to_compute"]

    assert adapter_path == REPAIRED_ADAPTER_PATH
    assert command == f"find {adapter_path} -type f -print0 | sort -z | xargs -0 sha256sum | sha256sum"
    assert OLD_ADAPTER_PATH not in command


def test_phase13_run_manifest_declares_final_test_scope() -> None:
    manifest = build_phase13_run_manifest(
        dataset="DuEE-Fin-dev500",
        split="test",
        profile="phase11_s4_role_safe_surface_memory",
        seed=42,
        command_argv=["scripts/v2/run_phase13_final_test_once.py", "--split", "test"],
    )

    assert manifest["method_name"] == "SAGE-DEE-v2-Phase13-Final-Test-Once"
    assert manifest["split_version"] == "test"
    assert manifest["seed"] == 42
    assert manifest["phase13_final_test_once"] is True
    assert manifest["test_used"] is True
    assert manifest["command_train"] is None
    assert "no test" not in manifest["notes"]


def test_log_wrapper_must_not_precreate_final_run_root() -> None:
    manifest_command = _manifest()["final_test_command"]["command"]
    result = _result()
    original = result["original_failed_attempt_result"]
    phase13_report = _read(PHASE13_REPORT_PATH)
    forensic_report = _read(PHASE13_1_REPORT_PATH)

    assert 'mkdir -p "${RUN_ROOT}"' not in manifest_command
    assert 'mkdir -p "${RUN_ROOT}"' in original["command_attempted_with_log_capture"]
    assert 'mkdir -p "${RUN_ROOT}"' not in result["command_executed"]
    assert 'mkdir -p "${RUN_ROOT}"' in phase13_report
    assert "Phase 13 refuses to reuse existing final-test run directory" in original["server_stderr"]
    assert "failure_category: harness_precreated_run_dir_collision" in forensic_report
    assert "wrapper-induced run-directory collision" in forensic_report


def test_phase13_recovery_records_original_pre_generation_failure_and_completed_recovery() -> None:
    result = _result()
    original = result["original_failed_attempt_result"]
    forensic_report = _read(PHASE13_1_REPORT_PATH)
    state = _read(STATE_PATH)

    assert result["status"] == "phase13_2_operational_recovery_completed"
    assert result["original_failed_attempt_status"] == "failed_before_generation"
    assert original["qwen_generation_started"] is False
    assert original["evaluator_started"] is False
    assert original["canonical_prediction_exists"] is False
    assert original["evaluator_artifact_exists"] is False
    assert result["qwen_generation_started"] is True
    assert result["evaluator_started"] is True
    assert result["canonical_prediction_exists"] is True
    assert result["evaluator_artifact_exists"] is True
    assert result["returncode"] == 0
    assert result["ssh_transport_returncode"] == 255
    assert result["wrapper_returncode_file_status"] == "present_but_empty_after_ssh_transport_closed"
    assert "Qwen generation started: NO" in forensic_report
    assert "evaluator started: NO" in forensic_report
    assert "canonical predictions created: NO" in forensic_report
    assert "test jsonl content read: NO evidence" in forensic_report
    assert "current_phase: Phase 13.2b operational recovery completed" in state
    assert "qwen_generation_started: true" in state
    assert "evaluator_started: true" in state
    assert "canonical_predictions_created: true" in state
    assert "operational_recovery_status: completed" in state
    assert "no further test run allowed: YES" in state


def test_phase13_recovery_does_not_change_seed_dataset_split() -> None:
    manifest = _manifest()
    result = _result()
    forensic_report = _read(PHASE13_1_REPORT_PATH)
    state = _read(STATE_PATH)

    assert manifest["final_seed_strategy"]["selected_strategy"] == "primary_seed_42_single_final_test"
    assert manifest["final_seed_strategy"]["primary_seed"] == 42
    assert "--dataset DuEE-Fin-dev500" in result["command_executed"]
    assert "--split test" in result["command_executed"]
    assert "--seed 42" in result["command_executed"]
    assert result["dataset"] == "DuEE-Fin-dev500"
    assert result["split"] == "test"
    assert result["seed"] == 42
    assert "no seed/dataset/split change: YES" in forensic_report
    assert "phase13_attempt_status: recovered_completed" in state
    assert "additional_test_runs: blocked" in state


def test_phase13_recovery_keeps_manifest_final_system() -> None:
    manifest = _manifest()
    result = _result()
    forensic_report = _read(PHASE13_1_REPORT_PATH)
    state = _read(STATE_PATH)

    assert manifest["final_system_id"] == "S4"
    assert manifest["SFT_checkpoint"]["adapter_path"] == REPAIRED_ADAPTER_PATH
    assert manifest["final_system_scope"]["primary_dataset"] == "DuEE-Fin-dev500"
    assert manifest["final_system_scope"]["primary_split"] == "test"
    assert result["final_system_id"] == "S4"
    assert result["adapter_path"] == REPAIRED_ADAPTER_PATH
    assert "manifest final system changed: NO" in forensic_report
    assert "no prompt/parser/surface/checkpoint/evaluator modification: YES" in forensic_report
    assert "phase13_failure_category: original_harness_precreated_run_dir_collision_recovered" in state


def test_phase13_2b_final_result_locks_metrics_and_artifacts() -> None:
    result = _result()
    state = _read(STATE_PATH)

    assert result["recovery_authorized"] is True
    assert result["recovery_run_root"].endswith("phase13_final_test_seed42_recovery_20260506T113047Z")
    assert result["recovery_log_root"].endswith("phase13_recovery_logs/phase13_final_test_seed42_20260506T113047Z")
    assert result["canonical_prediction_path"].endswith("predictions/DuEE-Fin-dev500/test.canonical.pred.jsonl")
    assert result["evaluator_artifact_root"].endswith("evaluator_artifacts/phase13_final_test_once_20260506T140545Z")
    assert result["final_metrics"] == {
        "event_table_micro_f1": 0.47374134889401553,
        "role_level_f1": 0.47374134889401553,
        "exact_record_f1": 0.05601436265709156,
        "evaluator_validation_ok": True,
    }
    assert result["post_test_modification_locked"] is True
    assert result["additional_test_runs_blocked"] is True
    assert result["no_additional_test_run"] is True
    assert result["old_failed_run_root_preserved"] is True
    assert "final_test_metrics_available: true" in state
    assert "next_phase: paper cut only" in state


def test_phase13_recovery_requires_explicit_human_authorization(tmp_path: Path) -> None:
    args = _args(tmp_path)
    args.out_dir = tmp_path / "phase13_final_test_seed42_recovery_20260506T120000Z"

    with pytest.raises(ValueError, match="requires --allow-human-authorized-operational-recovery"):
        validate_phase13_recovery_authorization(args, forensic_report_path=PHASE13_1_REPORT_PATH)


def test_phase13_recovery_requires_phase13_1_forensic_audit(tmp_path: Path) -> None:
    args = _args(tmp_path)
    args.out_dir = tmp_path / "phase13_final_test_seed42_recovery_20260506T120000Z"
    args.allow_human_authorized_operational_recovery = True
    incomplete_report = tmp_path / "SAGE_V2_PHASE13_1_FAILURE_FORENSIC_AUDIT.md"
    incomplete_report.write_text("failure_category: harness_precreated_run_dir_collision\n", encoding="utf-8")

    with pytest.raises(RuntimeError, match="Phase 13.1 forensic audit"):
        validate_phase13_recovery_authorization(args, forensic_report_path=incomplete_report)


def test_phase13_recovery_authorization_keeps_frozen_manifest_settings(tmp_path: Path) -> None:
    manifest = _manifest()
    config = read_yaml(CONFIG_PATH)
    args = _args(tmp_path)
    args.out_dir = tmp_path / "phase13_final_test_seed42_recovery_20260506T120000Z"
    args.allow_human_authorized_operational_recovery = True

    validate_final_args(args, config, manifest, require_adapter_exists=False)

    assert args.seed == 42
    assert args.dataset == "DuEE-Fin-dev500"
    assert args.split == "test"
    assert manifest["final_system_id"] == "S4"
    assert str(args.adapter_path) == manifest["SFT_checkpoint"]["adapter_path"]
    assert str(args.evaluator_root) == manifest["evaluator"]["root"]


def test_phase13_recovery_rejects_existing_run_root_but_allows_existing_log_root(tmp_path: Path) -> None:
    run_root = tmp_path / "phase13_final_test_seed42_recovery_20260506T120000Z"
    log_root = tmp_path / "phase13_recovery_logs" / "phase13_final_test_seed42_20260506T120000Z"
    log_root.mkdir(parents=True)

    validate_recovery_roots(run_root=run_root, log_root=log_root)

    run_root.mkdir()
    with pytest.raises(ValueError, match="RUN_ROOT already exists"):
        validate_recovery_roots(run_root=run_root, log_root=log_root)


def test_phase13_recovery_log_wrapper_separates_log_root_from_run_root() -> None:
    command = build_phase13_recovery_log_wrapper_command("20260506T120000Z")

    assert "RUN_ROOT=/data/TJK/DEE/sage-dee/runs/phase13_final_test_seed42_recovery_20260506T120000Z" in command
    assert (
        "LOG_ROOT=/data/TJK/DEE/sage-dee/runs/phase13_recovery_logs/"
        "phase13_final_test_seed42_20260506T120000Z"
    ) in command
    assert 'test ! -e "${RUN_ROOT}" && mkdir -p "${LOG_ROOT}"' in command
    assert 'mkdir -p "${RUN_ROOT}"' not in command
    assert '--allow-human-authorized-operational-recovery' in command
    assert 'tee "${LOG_ROOT}/phase13_recovery.stdout.log"' in command
    assert '--seed 42' in command
    assert '--dataset DuEE-Fin-dev500' in command
    assert '--split test' in command


def test_phase13_final_result_payload_records_original_and_recovery_attempts(tmp_path: Path) -> None:
    original = _result()
    recovery_run_root = "/data/TJK/DEE/sage-dee/runs/phase13_final_test_seed42_recovery_20260506T120000Z"
    payload = build_final_test_result_payload(
        original_failed_result=original,
        recovery_command="ssh gpu-4090 'phase13 recovery'",
        recovery_run_root=recovery_run_root,
        recovery_log_root="/data/TJK/DEE/sage-dee/runs/phase13_recovery_logs/phase13_final_test_seed42_20260506T120000Z",
        returncode=0,
        summary={
            "generation": {
                "canonical_path": (
                    f"{recovery_run_root}/predictions/DuEE-Fin-dev500/test.canonical.pred.jsonl"
                )
            },
            "evaluator": {
                "evaluator_artifact_root": f"{recovery_run_root}/evaluator_artifacts/run"
            },
            "final_metrics": {
                "event_table_micro_f1": 0.1,
                "role_level_f1": 0.1,
                "exact_record_f1": 0.0,
                "evaluator_validation_ok": True,
            },
        },
    )

    assert payload["original_failed_attempt_run_root"] == (
        "/data/TJK/DEE/sage-dee/runs/phase13_final_test_seed42_20260506T065342Z"
    )
    assert payload["original_failed_attempt_status"] == "failed_before_generation"
    assert payload["recovery_authorized"] is True
    assert payload["recovery_reason"] == "harness/logging run-dir collision before generation"
    assert payload["recovery_run_root"].endswith("phase13_final_test_seed42_recovery_20260506T120000Z")
    assert payload["recovery_log_root"].endswith("phase13_recovery_logs/phase13_final_test_seed42_20260506T120000Z")
    assert payload["seed"] == 42
    assert payload["dataset"] == "DuEE-Fin-dev500"
    assert payload["split"] == "test"
    assert payload["profile"] == "phase11_s4_role_safe_surface_memory"
    assert payload["checkpoint"]["adapter_path"] == REPAIRED_ADAPTER_PATH
    assert payload["evaluator_root"] == "/home/TJK/DEE/dee-eval"
    assert payload["canonical_prediction_path"].endswith("test.canonical.pred.jsonl")
    assert payload["final_metrics"]["evaluator_validation_ok"] is True
    assert payload["post_test_modification_locked"] is True
    assert payload["additional_test_runs_blocked"] is True
