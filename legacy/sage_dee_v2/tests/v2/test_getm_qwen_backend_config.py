from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from sage_dee.io_utils import read_yaml
from sage_dee.v2.getm.qwen_backend import (
    _pack_generation_token_ids,
    _tokenize_generation_prompt_with_metadata,
    build_model,
    generate_candidates,
    train_sft,
)
from tests.v2.subprocess_utils import PYTHON, python_env

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_v2_qwen_configs_load_with_4090_qlora_defaults() -> None:
    config = read_yaml(REPO_ROOT / "configs/v2/getm_qwen3_4b_qlora.yaml")

    qwen = config["getm"]["qwen"]
    assert qwen["base_model"] == "Qwen/Qwen3-4B-Instruct-2507"
    assert qwen["quantization"] == "4-bit NF4"
    assert qwen["double_quantization"] is True
    assert qwen["compute_dtype"] == "bf16"
    assert qwen["lora"]["rank"] == 16
    assert qwen["lora"]["alpha"] == 32
    assert qwen["lora"]["dropout"] == 0.05
    assert qwen["training"]["micro_batch_size"] == 1
    assert qwen["training"]["gradient_accumulation"] in {8, 16}
    assert qwen["training"]["max_seq_len"] == 4096
    assert qwen["training"]["gradient_checkpointing"] is True
    assert config["getm"]["generation"]["k_candidates"] == 4


@pytest.mark.parametrize(
    "config_path",
    [
        "configs/v2/getm_qwen3_4b_qlora.yaml",
        "configs/v2/sage_v2_smoke.yaml",
        "configs/v2/sage_v2_duee_fin.yaml",
    ],
)
def test_predict_config_does_not_contain_gold_path(config_path: str) -> None:
    config = read_yaml(REPO_ROOT / config_path)
    serialized = json.dumps(config.get("predict", config), ensure_ascii=False).lower()

    for forbidden in ("gold_path", "gold_template", "events_path"):
        assert forbidden not in serialized


def test_qwen_backend_dry_run_does_not_require_gpu(tmp_path: Path) -> None:
    config = {
        "run": {"dry_run": True, "real_run": False, "profile": "local_dry_run"},
        "getm": {
            "backend": "qwen",
            "qwen": {"base_model": "Qwen/Qwen3-4B-Instruct-2507"},
            "generation": {"k_candidates": 4},
        },
    }
    model_manifest = build_model(config)
    train_manifest = train_sft(config, [{"doc_id": "doc-1", "prompt": "P", "output": {"events": []}}], tmp_path)

    assert model_manifest["dry_run"] is True
    assert train_manifest["dry_run"] is True
    assert train_manifest["training_manifest_path"].endswith("training_manifest.json")
    assert (tmp_path / "training_manifest.json").is_file()


def test_generate_candidates_dry_run_rejects_gold_visible_input(tmp_path: Path) -> None:
    input_path = tmp_path / "prompts.jsonl"
    input_path.write_text(
        json.dumps(
            {
                "doc_id": "doc-1",
                "prompt": "P",
                "events": [{"event_type": "GoldLeak", "arguments": {}}],
            }
        )
        + "\n",
        encoding="utf-8",
    )
    config = {
        "run": {"dry_run": True, "real_run": False, "profile": "local_dry_run"},
        "getm": {"backend": "qwen", "generation": {"k_candidates": 4}},
    }

    with pytest.raises(ValueError, match="gold-visible"):
        generate_candidates(config, input_path, tmp_path / "out", k=4)


def test_qwen_backend_real_run_requires_explicit_flag(tmp_path: Path) -> None:
    config = {
        "run": {"dry_run": False, "real_run": False, "profile": "server_smoke_4090"},
        "getm": {
            "backend": "qwen",
            "qwen": {"base_model": "Qwen/Qwen3-4B-Instruct-2507"},
            "generation": {"k_candidates": 4},
        },
    }

    with pytest.raises(RuntimeError, match="--real-run"):
        build_model(config)


def test_generate_script_defaults_to_dry_run(tmp_path: Path) -> None:
    out_dir = tmp_path / "generate"
    completed = subprocess.run(
        [
            PYTHON,
            str(REPO_ROOT / "scripts/v2/generate_getm_qwen.py"),
            "--config",
            str(REPO_ROOT / "configs/v2/sage_v2_smoke.yaml"),
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
    assert manifest["dry_run"] is True
    assert manifest["real_run"] is False


def test_train_script_real_run_requires_explicit_flag(tmp_path: Path) -> None:
    completed = subprocess.run(
        [
            PYTHON,
            str(REPO_ROOT / "scripts/v2/train_getm_qwen.py"),
            "--config",
            str(REPO_ROOT / "configs/v2/sage_v2_smoke.yaml"),
            "--no-dry-run",
            "--out-dir",
            str(tmp_path / "train"),
        ],
        cwd=REPO_ROOT,
        env=python_env(),
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode != 0
    assert "--real-run" in completed.stderr


def test_generation_prompt_packing_keeps_prefix_and_protocol_suffix() -> None:
    packed, metadata = _pack_generation_token_ids(list(range(120)), max_length=100, prefix_keep_tokens=10)

    assert packed == list(range(10)) + list(range(30, 120))
    assert metadata["prompt_packing_strategy"] == "middle_truncate_keep_prefix_suffix"
    assert metadata["full_prompt_token_count"] == 120
    assert metadata["prompt_token_count"] == 100
    assert metadata["prompt_middle_token_drop_count"] == 20


class _CharTokenizer:
    eos_token = "<eos>"
    eos_token_id = 0
    pad_token_id = 0

    def apply_chat_template(
        self,
        messages: list[dict[str, str]],
        *,
        tokenize: bool,
        continue_final_message: bool = False,
        add_generation_prompt: bool = False,
        **_: object,
    ):
        rendered = ""
        for message in messages:
            rendered += f"<|{message['role']}|>{message['content']}<|end|>"
        if add_generation_prompt:
            rendered += "<|assistant|>"
        if continue_final_message:
            rendered += "<|assistant_continue|>"
        if not tokenize:
            return rendered
        return {"input_ids": [ord(char) for char in rendered]}

    def __call__(self, text: str, **_: object) -> dict[str, list[int]]:
        return {"input_ids": [ord(char) for char in text]}

    def decode(self, ids: list[int], **_: object) -> str:
        return "".join(chr(token_id) for token_id in ids)


def test_generation_prompt_tokenization_preserves_delimiter_and_response_prefix_when_over_budget() -> None:
    prompt = "x" * 160 + "\n### RESPONSE_JSON"
    config = {
        "getm": {
            "generation": {
                "use_chat_template": True,
                "use_response_prefix": True,
                "response_prefix": '{"events":',
            },
            "qwen": {"training": {"max_seq_len": 80}},
            "prompt": {"prompt_token_budget": 80},
        }
    }

    model_inputs, metadata = _tokenize_generation_prompt_with_metadata(_CharTokenizer(), prompt, config)
    decoded = _CharTokenizer().decode(model_inputs["input_ids"])

    assert len(model_inputs["input_ids"]) == 80
    assert "### RESPONSE_JSON" in decoded
    assert '{"events":' in decoded
    assert metadata["prompt_packing_strategy"] == "middle_truncate_keep_prefix_suffix"
    assert metadata["prompt_delimiter_present_after_packing"] is True
    assert metadata["response_prefix_present_after_packing"] is True
