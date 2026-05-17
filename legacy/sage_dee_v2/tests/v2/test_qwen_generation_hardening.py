from __future__ import annotations

import argparse
import json
import os
import subprocess
from pathlib import Path

from sage_dee.io_utils import read_yaml
from sage_dee.v2.data_interface.jsonl import read_jsonl
from sage_dee.v2.getm.qwen_backend import (
    QwenGetmBackend,
    _apply_reproducibility_settings,
    _generation_config,
    _generation_metadata,
    _prompt_config,
)
from tests.v2.subprocess_utils import PYTHON, python_env

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_hardened_generation_defaults_load_from_yaml() -> None:
    config = read_yaml(REPO_ROOT / "configs/v2/sage_v2_smoke.yaml")
    generation = _generation_config(config)
    prompt = _prompt_config(config)

    assert generation["use_chat_template"] is True
    assert generation["add_generation_prompt"] is False
    assert generation["continue_final_message"] is True
    assert generation["use_response_prefix"] is True
    assert generation["response_prefix"] == '{"events":'
    assert generation["output_format"] == "minimal_text"
    assert generation["max_new_tokens"] >= 768
    assert generation["do_sample"] is False
    assert generation["temperature"] is None
    assert generation["top_p"] == 1.0
    assert generation["repetition_penalty"] == 1.05
    assert prompt["max_surface_candidates"] == 20
    assert prompt["candidate_render_mode"] == "compact"
    assert prompt["candidate_context_chars"] == 0
    assert prompt["enable_candidate_filtering"] is True
    assert prompt["dedupe_surface_candidates"] is True
    assert prompt["drop_low_value_company_fragments"] is True
    assert prompt["prompt_token_budget"] == 4096
    assert prompt["fail_on_prompt_token_limit"] is False


def test_frozen_format_stable_generation_profile_loads_from_yaml() -> None:
    config = read_yaml(REPO_ROOT / "configs/v2/sage_v2_getm_format_stable.yaml")
    generation = _generation_config(config)
    prompt = _prompt_config(config)

    assert (config["run"]["profile"], config["run"]["real_run"]) == ("getm_format_stable_dev20_f1", False)
    assert generation["k_candidates"] == 1
    assert generation["output_format"] == "minimal_text"
    assert generation["use_response_prefix"] is True
    assert generation["response_prefix"] == '{"events":'
    assert generation["enable_balanced_json_stopping"] is True
    assert generation["stop_after_balanced_events_json"] is True
    assert generation["max_new_tokens"] == 1024
    assert generation["do_sample"] is False
    assert generation["temperature"] is None
    assert generation["top_p"] == 1.0
    assert generation["seed"] == 42
    assert generation["deterministic"] is True
    assert generation["deterministic_warn_only"] is True
    assert generation["record_resolved_generation_config"] is True
    assert generation["num_beams"] == 1
    assert generation["num_return_sequences"] == 1
    assert prompt["max_surface_candidates"] == 10
    assert prompt["candidate_render_mode"] == "compact"
    assert prompt["candidate_context_chars"] == 0
    assert prompt["enable_candidate_filtering"] is True
    assert prompt["max_candidates_per_type"] == 6
    assert prompt["dedupe_surface_candidates"] is True
    assert prompt["drop_low_value_company_fragments"] is True
    assert prompt["prompt_token_budget"] == 4096
    assert prompt["fail_on_prompt_token_limit"] is False


def test_generation_metadata_records_chat_template_and_prefix() -> None:
    metadata = _generation_metadata(
        {
            "getm": {
                "generation": {
                    "use_chat_template": True,
                    "use_response_prefix": True,
                    "response_prefix": '{"events":',
                    "max_new_tokens": 1024,
                    "do_sample": False,
                    "temperature": None,
                    "top_p": 1.0,
                    "repetition_penalty": 1.05,
                    "prompt_delimiter": "### RESPONSE_JSON",
                    "seed": 42,
                    "deterministic": True,
                    "deterministic_warn_only": True,
                    "record_resolved_generation_config": True,
                }
            }
        }
    )

    assert metadata["chat_template_used"] is True
    assert metadata["add_generation_prompt"] is False
    assert metadata["continue_final_message"] is True
    assert metadata["response_prefix_used"] is True
    assert metadata["response_prefix"] == '{"events":'
    assert metadata["output_format"] == "minimal_text"
    assert metadata["prompt_delimiter"] == "### RESPONSE_JSON"
    assert metadata["prompt_delimiter_used"] is True
    assert metadata["seed"] == 42
    assert metadata["deterministic"] is True
    assert metadata["deterministic_warn_only"] is True
    assert metadata["resolved_generation_config"]["do_sample"] is False
    assert metadata["resolved_generation_config"]["num_beams"] == 1
    assert metadata["resolved_generation_config"]["num_return_sequences"] == 1


def test_apply_reproducibility_settings_sets_seed_and_torch_determinism() -> None:
    calls: list[tuple[str, object]] = []
    old_cublas_config = os.environ.pop("CUBLAS_WORKSPACE_CONFIG", None)

    class _FakeCudaBackend:
        matmul = type("_Matmul", (), {"allow_tf32": True})()

    class _FakeCudnn:
        allow_tf32 = True
        benchmark = True
        deterministic = False

    class _FakeCuda:
        @staticmethod
        def manual_seed_all(seed: int) -> None:
            calls.append(("cuda.manual_seed_all", seed))

        @staticmethod
        def is_available() -> bool:
            return True

        @staticmethod
        def get_device_name(index: int = 0) -> str:
            return f"fake-cuda-{index}"

    class _FakeTorch:
        __version__ = "2.fake"
        version = type("_Version", (), {"cuda": "12.fake"})()
        backends = type("_Backends", (), {"cuda": _FakeCudaBackend, "cudnn": _FakeCudnn})()
        cuda = _FakeCuda()

        @staticmethod
        def manual_seed(seed: int) -> None:
            calls.append(("torch.manual_seed", seed))

        @staticmethod
        def use_deterministic_algorithms(enabled: bool, *, warn_only: bool = False) -> None:
            calls.append(("torch.use_deterministic_algorithms", (enabled, warn_only)))

    try:
        manifest = _apply_reproducibility_settings(
            torch=_FakeTorch,
            seed=42,
            deterministic=True,
            warn_only=True,
        )
    finally:
        if old_cublas_config is not None:
            os.environ["CUBLAS_WORKSPACE_CONFIG"] = old_cublas_config
        else:
            os.environ.pop("CUBLAS_WORKSPACE_CONFIG", None)

    assert ("torch.manual_seed", 42) in calls
    assert ("cuda.manual_seed_all", 42) in calls
    assert ("torch.use_deterministic_algorithms", (True, True)) in calls
    assert _FakeTorch.backends.cuda.matmul.allow_tf32 is False
    assert _FakeTorch.backends.cudnn.allow_tf32 is False
    assert _FakeTorch.backends.cudnn.benchmark is False
    assert _FakeTorch.backends.cudnn.deterministic is True
    assert manifest["seed"] == 42
    assert manifest["deterministic"] is True
    assert manifest["cublas_workspace_config"] == ":4096:8"
    assert manifest["torch_version"] == "2.fake"


def test_qwen_dry_run_uses_matching_array_prefix_continuation() -> None:
    backend = QwenGetmBackend(
        config={
            "run": {"dry_run": True, "real_run": False},
            "getm": {"generation": {"use_response_prefix": True, "response_prefix": '{"events":['}},
        }
    )

    raw_output = backend.generate_one(
        prompt="P",
        document={"doc_id": "doc-1", "content": "safe"},
        schema=None,
        surface_candidates=[],
        slot_plan=None,
        candidate_index=0,
    )

    assert raw_output == "]}"


def test_generate_script_cli_overrides_generation_config(tmp_path: Path) -> None:
    out_dir = tmp_path / "generate"
    completed = subprocess.run(
        [
            PYTHON,
            str(REPO_ROOT / "scripts/v2/generate_getm_qwen.py"),
            "--config",
            str(REPO_ROOT / "configs/v2/sage_v2_smoke.yaml"),
            "--dry-run",
            "--limit",
            "1",
            "--k",
            "1",
            "--max-new-tokens",
            "768",
            "--no-do-sample",
            "--temperature",
            "none",
            "--top-p",
            "1.0",
            "--repetition-penalty",
            "1.05",
            "--response-prefix",
            '{"events":',
            "--output-format",
            "argument_object",
            "--max-surface-candidates",
            "10",
            "--candidate-render-mode",
            "full",
            "--candidate-context-chars",
            "40",
            "--no-enable-candidate-filtering",
            "--max-candidates-per-type",
            "2",
            "--no-dedupe-surface-candidates",
            "--no-drop-low-value-company-fragments",
            "--prompt-token-budget",
            "2048",
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
    manifest = json.loads((out_dir / "generation_manifest.json").read_text(encoding="utf-8"))
    run_manifest = json.loads((out_dir / "run_manifest.json").read_text(encoding="utf-8"))
    diagnostics = json.loads((out_dir / "parse_diagnostics.dev.json").read_text(encoding="utf-8"))
    raw_rows = read_jsonl(out_dir / "raw_outputs.dev.jsonl")
    parsed_rows = read_jsonl(out_dir / "parsed_candidates.dev.jsonl")
    required_run_manifest_fields = {
        "run_id",
        "method_name",
        "method_family",
        "dataset_version",
        "split_version",
        "evaluator_version",
        "prediction_format",
        "training_view",
        "gold_view",
        "seed",
        "git_commit",
        "command_train",
        "command_infer",
        "created_at",
        "notes",
    }
    assert required_run_manifest_fields <= set(run_manifest)
    assert run_manifest["evaluator_version"] == "eval-artifacts-v1.1"
    assert run_manifest["training_view"] == "evaluator_gold/train"
    assert run_manifest["gold_view"] == "processed/views/evaluator_gold/DuEE-Fin-dev500"
    assert run_manifest["seed"] == "none"
    assert manifest["diagnostic_version"] == "getm_generation_diagnostics_p0_v1"
    assert diagnostics["diagnostic_version"] == "getm_generation_diagnostics_p0_v1"
    assert manifest["generation"]["max_new_tokens"] == 768
    assert manifest["generation"]["do_sample"] is False
    assert manifest["generation"]["temperature"] is None
    assert "seed" in manifest["generation"]
    assert "deterministic" in manifest["generation"]
    assert "record_resolved_generation_config" in manifest["generation"]
    assert manifest["generation"]["resolved_generation_config"]["do_sample"] is False
    assert manifest["generation"]["resolved_generation_config"]["num_beams"] == 1
    assert manifest["generation"]["resolved_generation_config"]["num_return_sequences"] == 1
    assert manifest["generation"]["response_prefix_used"] is True
    assert manifest["generation"]["output_format"] == "argument_object"
    assert manifest["generation"]["max_surface_candidates"] == 10
    assert manifest["generation"]["candidate_render_mode"] == "full"
    assert manifest["generation"]["candidate_context_chars"] == 40
    assert manifest["generation"]["enable_candidate_filtering"] is False
    assert manifest["generation"]["max_candidates_per_type"] == 2
    assert manifest["generation"]["dedupe_surface_candidates"] is False
    assert manifest["generation"]["drop_low_value_company_fragments"] is False
    assert manifest["generation"]["prompt_token_budget"] == 2048
    assert raw_rows[0]["diagnostic_version"] == "getm_generation_diagnostics_p0_v1"
    assert raw_rows[0]["raw_output_char_count"] == 3
    assert raw_rows[0]["prompt_token_budget"] == 2048
    assert raw_rows[0]["prompt_token_limit_hit"] is False
    assert parsed_rows[0]["diagnostics"]["surface_candidate_count"] >= 0
    assert parsed_rows[0]["diagnostics"]["prompt_token_budget"] == 2048
    assert diagnostics["max_new_tokens"] == 768
    assert diagnostics["do_sample"] is False
    assert diagnostics["temperature"] is None
    assert diagnostics["prompt_token_summary"]["prompt_token_budget"] == 2048


def test_generate_script_rejects_forbidden_prediction_scope_before_loading_data(tmp_path: Path) -> None:
    completed = subprocess.run(
        [
            PYTHON,
            str(REPO_ROOT / "scripts/v2/generate_getm_qwen.py"),
            "--config",
            str(REPO_ROOT / "configs/v2/sage_v2_smoke.yaml"),
            "--dry-run",
            "--split",
            "test",
            "--limit",
            "1",
            "--out-dir",
            str(tmp_path / "generate"),
        ],
        cwd=REPO_ROOT,
        env=python_env(),
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 2
    assert "test split" in completed.stderr


def test_generate_run_manifest_records_frozen_profile_seed() -> None:
    from scripts.v2.generate_getm_qwen import _run_manifest

    run_manifest = _run_manifest(
        config=read_yaml(REPO_ROOT / "configs/v2/sage_v2_getm_format_stable.yaml"),
        dataset="DuEE-Fin-dev500",
        split="dev",
        command_infer="generate",
        backend="qwen",
    )

    assert run_manifest["evaluator_version"] == "eval-artifacts-v1.1"
    assert run_manifest["prediction_format"] == "canonical-jsonl"
    assert run_manifest["training_view"] == "evaluator_gold/train"
    assert run_manifest["gold_view"] == "processed/views/evaluator_gold/DuEE-Fin-dev500"
    assert run_manifest["seed"] == 42


def test_temperature_cli_parser_accepts_none() -> None:
    from scripts.v2.generate_getm_qwen import _parse_optional_float, _parse_optional_int

    assert _parse_optional_float("none") is None
    assert _parse_optional_float("null") is None
    assert _parse_optional_float("0.7") == 0.7
    assert _parse_optional_int("none") is None
    assert _parse_optional_int("40") == 40

    try:
        _parse_optional_float("bad")
    except argparse.ArgumentTypeError:
        pass
    else:  # pragma: no cover - defensive test failure path
        raise AssertionError("bad optional float was accepted")
