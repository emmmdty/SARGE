from __future__ import annotations

import json
from pathlib import Path

import pytest

from sage_dee.v2.contracts.surface import SurfaceCandidate
from sage_dee.v2.data_interface.dataset_loader import V2DatasetDocument, V2DocumentInput, V2GoldDocument
from sage_dee.v2.data_interface.schema_registry import DatasetSchema
from sage_dee.v2.getm.sft_dataset import (
    audit_sft_targets,
    build_getm_sft_sample,
    build_sft_training_examples,
    render_sft_answer_suffix,
    render_sft_training_text,
    render_sft_user_assistant_prefix,
)


def _schema() -> DatasetSchema:
    return DatasetSchema(
        dataset_id="unit",
        schema_dataset="unit-source",
        schema_path=Path("schema.json"),
        canonical_version=None,
        event_roles={"EventA": ("Role1", "Role2")},
        role_to_event_types={"Role1": ("EventA",), "Role2": ("EventA",)},
    )


def _document(split: str, events: list[dict] | None) -> V2DatasetDocument:
    input_doc = V2DocumentInput(
        doc_id=f"doc-{split}",
        dataset_id="unit",
        dataset="unit-source",
        split=split,
        content="The document contains value-one and value-two.",
    )
    if events is None:
        return V2DatasetDocument(input=input_doc, gold=None)
    return V2DatasetDocument(
        input=input_doc,
        gold=V2GoldDocument(
            doc_id=input_doc.doc_id,
            dataset_id="unit",
            dataset="unit-source",
            split=split,
            events=events,
        ),
    )


def test_train_sft_output_uses_text_and_candidate_id_without_norm_text() -> None:
    sample = build_getm_sft_sample(
        _document(
            "train",
            [
                {
                    "event_type": "EventA",
                    "arguments": {
                        "Role1": [{"text": "value-one", "norm_text": "normalized-one"}],
                        "Role2": [{"text": "not-in-candidates", "norm_text": "normalized-two"}],
                    },
                }
            ],
        ),
        _schema(),
        surface_candidates=[
            SurfaceCandidate(
                candidate_id="cand-1",
                doc_id="doc-train",
                surface="value-one",
                context="contains value-one",
                chunk_id="chunk-0000",
            )
        ],
        slot_plan=None,
        output_format="argument_object",
    )

    assert "output" in sample
    assert sample["output"] == {
        "events": [
            {
                "event_type": "EventA",
                "arguments": {
                    "Role1": [{"text": "value-one", "source_candidate_id": "cand-1"}],
                    "Role2": [{"text": "not-in-candidates", "source_candidate_id": None}],
                },
            }
        ]
    }
    serialized = json.dumps(sample, ensure_ascii=False)
    assert "norm_text" not in serialized
    assert "normalized-one" not in serialized


def test_train_sft_output_defaults_to_minimal_text_values() -> None:
    sample = build_getm_sft_sample(
        _document(
            "train",
            [
                {
                    "event_type": "EventA",
                    "arguments": {
                        "Role1": [{"text": "value-one", "norm_text": "normalized-one"}],
                    },
                }
            ],
        ),
        _schema(),
        surface_candidates=[
            SurfaceCandidate(
                candidate_id="cand-1",
                doc_id="doc-train",
                surface="value-one",
                context="contains value-one",
                chunk_id="chunk-0000",
            )
        ],
        slot_plan=None,
    )

    assert sample["output"] == {
        "events": [{"event_type": "EventA", "arguments": {"Role1": ["value-one"]}}]
    }
    assert "source_candidate_id" not in json.dumps(sample, ensure_ascii=False)


def test_sft_target_roles_are_schema_valid() -> None:
    with pytest.raises(ValueError, match="Unknown role"):
        build_getm_sft_sample(
            _document(
                "train",
                [
                    {
                        "event_type": "EventA",
                        "arguments": {
                            "role": [{"text": "must-not-map"}],
                            "Role1": [{"text": "value-one"}],
                        },
                    }
                ],
            ),
            _schema(),
            surface_candidates=[],
            slot_plan=None,
        )


@pytest.mark.parametrize("split", ("dev", "test"))
def test_dev_test_sft_rows_are_prompt_only(split: str) -> None:
    sample = build_getm_sft_sample(
        _document(
            split,
            [
                {
                    "event_type": "EventA",
                    "arguments": {"Role1": [{"text": "must-not-output", "norm_text": "must-not-output"}]},
                }
            ],
        ),
        _schema(),
        surface_candidates=[],
        slot_plan=None,
    )

    assert sample["split"] == split
    assert "prompt" in sample
    assert "output" not in sample
    assert "must-not-output" not in json.dumps(sample, ensure_ascii=False)


class _FakeTokenizer:
    eos_token = "<eos>"
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
            rendered += f"<|{message['role']}|>{message['content']}"
        if add_generation_prompt:
            rendered += "<|assistant|>"
        if continue_final_message:
            rendered += "<|continue|>"
        if not tokenize:
            return rendered
        return {"input_ids": [ord(char) for char in rendered]}

    def __call__(self, text: str, *, add_special_tokens: bool = False, **_: object) -> dict[str, list[int]]:
        del add_special_tokens
        return {"input_ids": [ord(char) for char in text]}


def test_sft_training_examples_mask_prompt_prefix_and_label_answer_tokens() -> None:
    tokenizer = _FakeTokenizer()
    rows = [{"doc_id": "doc-1", "prompt": "PROMPT", "output": {"events": []}}]
    config = {
        "getm": {
            "generation": {
                "use_chat_template": True,
                "use_response_prefix": True,
                "response_prefix": '{"events":',
            }
        }
    }

    examples, audit = build_sft_training_examples(rows=rows, tokenizer=tokenizer, max_seq_len=256, config=config)
    prefix_ids = tokenizer(render_sft_user_assistant_prefix(tokenizer, "PROMPT", config), add_special_tokens=False)[
        "input_ids"
    ]

    assert len(examples) == 1
    assert examples[0]["labels"][: len(prefix_ids)] == [-100] * len(prefix_ids)
    assert any(label != -100 for label in examples[0]["labels"][len(prefix_ids) :])
    assert examples[0]["input_ids"][len(prefix_ids) :] == examples[0]["labels"][len(prefix_ids) :]
    assert audit["all_prompt_labels_masked"] is True
    assert audit["all_examples_have_answer_labels"] is True


def test_sft_training_template_prefix_matches_inference_prefix_shape() -> None:
    tokenizer = _FakeTokenizer()
    config = {
        "getm": {
            "generation": {
                "use_chat_template": True,
                "use_response_prefix": True,
                "response_prefix": '{"events":',
            }
        }
    }

    train_text = render_sft_training_text(tokenizer, "PROMPT", {"events": []}, config)
    prefix = render_sft_user_assistant_prefix(tokenizer, "PROMPT", config)

    assert train_text.startswith(prefix)
    assert "<|assistant|>{\"events\":" in prefix


def test_sft_response_prefix_target_labels_only_json_continuation() -> None:
    tokenizer = _FakeTokenizer()
    config = {
        "getm": {
            "generation": {
                "use_chat_template": True,
                "use_response_prefix": True,
                "response_prefix": '{"events":',
            }
        }
    }

    target = render_sft_answer_suffix(tokenizer, {"events": []}, config)

    assert target == "[]}<eos>"
    assert not target.startswith('{"events":')


def test_sft_target_audit_reports_schema_valid_role_keys() -> None:
    sample = build_getm_sft_sample(
        _document(
            "train",
            [
                {
                    "event_type": "EventA",
                    "arguments": {"Role1": [{"text": "value-one"}]},
                }
            ],
        ),
        _schema(),
        surface_candidates=[],
        slot_plan=None,
    )

    audit = audit_sft_targets([sample], _schema())

    assert audit["target_schema_valid"] is True
    assert audit["invalid_target_role_count"] == 0
    assert audit["literal_role_key_count"] == 0
