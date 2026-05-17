from __future__ import annotations

import json
from pathlib import Path

from sage_dee.v2.data_interface.dataset_loader import V2DatasetDocument, V2DocumentInput, V2GoldDocument
from sage_dee.v2.data_interface.schema_registry import DatasetSchema
from sage_dee.v2.getm.prompt_builder import build_getm_prompt
from sage_dee.v2.getm.sft_dataset import build_getm_sft_sample


def _schema() -> DatasetSchema:
    return DatasetSchema(
        dataset_id="unit",
        schema_dataset="unit-source",
        schema_path=Path("schema.json"),
        canonical_version=None,
        event_roles={"EventA": ("Role1", "Role2")},
        role_to_event_types={"Role1": ("EventA",), "Role2": ("EventA",)},
    )


def _input_doc(split: str = "dev") -> V2DocumentInput:
    return V2DocumentInput(
        doc_id=f"doc-{split}",
        dataset_id="unit",
        dataset="unit-source",
        split=split,
        content="The document contains value-one.",
    )


def test_prompt_contains_strict_format_adherence_instructions() -> None:
    prompt = build_getm_prompt(
        dataset="unit",
        schema=_schema(),
        document=_input_doc(),
        surface_candidates=[],
        slot_plan=None,
    )

    required_fragments = (
        "Return ONLY one valid JSON object",
        "Do not wrap it in markdown fences",
        "Do not explain",
        "Do not repeat the document, schema, candidates, or instruction",
        "Do not output YAML",
        "The top-level JSON object must contain only the `events` key",
        "If no valid event is present, return exactly {\"events\": []}",
        "Do not output fields outside the event type and role schema",
        "event_type and role names must be copied exactly from the schema",
    )
    for fragment in required_fragments:
        assert fragment in prompt
    assert "The first character of your answer must be" not in prompt


def test_prompt_shape_does_not_use_literal_role() -> None:
    prompt = build_getm_prompt(
        dataset="unit",
        schema=_schema(),
        document=_input_doc(),
        surface_candidates=[],
        slot_plan=None,
        output_format="minimal_text",
    )

    assert '"arguments":{"role":' not in prompt
    assert '{"events":[{"event_type":"EventA","arguments":{"Role1":["..."]}}]}' in prompt
    assert "source_candidate_id" not in prompt
    assert '{"text":"..."}' not in prompt
    assert "Each argument must have a \"text\" field" not in prompt


def test_prompt_schema_lists_valid_roles() -> None:
    prompt = build_getm_prompt(
        dataset="unit",
        schema=_schema(),
        document=_input_doc(),
        surface_candidates=[],
        slot_plan=None,
    )

    assert "- EventA: Role1, Role2" in prompt
    assert "arguments keys must be valid roles for the generated event_type" in prompt
    assert "For EventA, valid argument keys are: Role1, Role2." in prompt


def test_argument_object_prompt_keeps_legacy_argument_shape() -> None:
    prompt = build_getm_prompt(
        dataset="unit",
        schema=_schema(),
        document=_input_doc(),
        surface_candidates=[],
        slot_plan=None,
        output_format="argument_object",
    )

    assert '{"text":"..."}' in prompt
    assert '"arguments":{"role":' not in prompt
    assert '{"events":[{"event_type":"EventA","arguments":{"Role1":[{"text":"..."}' in prompt
    assert '"source_candidate_id":"candidate-id-or-null"' in prompt
    assert "source_candidate_id is an internal candidate-stage field" in prompt


def test_prompt_uses_prefix_array_continuation_instruction() -> None:
    prompt = build_getm_prompt(
        dataset="unit",
        schema=_schema(),
        document=_input_doc(),
        surface_candidates=[],
        slot_plan=None,
        use_response_prefix=True,
        response_prefix='{"events":[',
        prompt_delimiter="### RESPONSE_JSON",
        output_format="minimal_text",
    )

    required_fragments = (
        "The assistant response has already started with the configured response prefix.",
        "Continue only the JSON continuation.",
        "If there are no valid events, output exactly ]}.",
        "Do not repeat schema, document, candidates, or instructions.",
        "Do not output fields outside the event type and role schema.",
        "### RESPONSE_JSON",
    )
    for fragment in required_fragments:
        assert fragment in prompt
    assert "The top-level JSON object must contain only the `events` key" not in prompt
    assert "The first character of your answer must be" not in prompt


def test_prompt_allows_only_internal_source_candidate_id_for_arguments() -> None:
    prompt = build_getm_prompt(
        dataset="unit",
        schema=_schema(),
        document=_input_doc(),
        surface_candidates=[],
        slot_plan=None,
        output_format="argument_object",
    )

    assert '{"text":"..."}' in prompt
    assert '"source_candidate_id":"candidate-id-or-null"' in prompt
    assert "source_candidate_id is an internal candidate-stage field" in prompt


def test_test_split_sft_output_remains_prompt_only() -> None:
    document = V2DatasetDocument(
        input=_input_doc(split="test"),
        gold=V2GoldDocument(
            doc_id="doc-test",
            dataset_id="unit",
            dataset="unit-source",
            split="test",
            events=[
                {
                    "event_type": "EventA",
                    "arguments": {"Role1": [{"text": "must-not-output", "norm_text": "must-not-output"}]},
                }
            ],
        ),
    )

    sample = build_getm_sft_sample(document, _schema(), surface_candidates=[], slot_plan=None)

    assert sample["split"] == "test"
    assert "prompt" in sample
    assert "output" not in sample
    assert "must-not-output" not in json.dumps(sample, ensure_ascii=False)
