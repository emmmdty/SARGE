from __future__ import annotations

import json
from pathlib import Path

from sage_dee.v2.data_interface.schema_registry import DatasetSchema
from sage_dee.v2.getm.parser import parse_getm_output


def _schema() -> DatasetSchema:
    return DatasetSchema(
        dataset_id="unit",
        schema_dataset="unit-source",
        schema_path=Path("schema.json"),
        canonical_version=None,
        event_roles={"EventA": ("Role1", "Role2")},
        role_to_event_types={"Role1": ("EventA",), "Role2": ("EventA",)},
    )


def _parse(raw_output: str, *, response_prefix: str = '{"events":'):
    return parse_getm_output(
        raw_output,
        doc_id="doc-prefix-1",
        candidate_id="doc-prefix-1:getm:0",
        schema=_schema(),
        response_prefix=response_prefix,
        response_prefix_used=True,
    )


def test_response_prefix_reconstructs_continuation_json() -> None:
    candidate = _parse('[{"event_type":"EventA","arguments":{"Role1":[{"text":"value-one"}]}}]}')

    assert candidate.parse_status == "ok"
    assert candidate.events[0].event_type == "EventA"
    assert candidate.events[0].arguments["Role1"][0].text == "value-one"
    assert candidate.diagnostics["response_prefix_used"] == 1
    assert candidate.diagnostics["response_prefix_reconstructed_count"] == 1
    assert candidate.diagnostics["response_prefix_array_reconstructed_count"] == 1
    assert candidate.diagnostics["repair_type_counts"] == {"response_prefix_array_reconstructed": 1}


def test_response_prefix_array_reconstructs_empty_array_continuation() -> None:
    candidate = _parse("]}", response_prefix='{"events":[')

    assert candidate.parse_status == "ok"
    assert candidate.events == []
    assert candidate.diagnostics["response_prefix_reconstructed_count"] == 1
    assert candidate.diagnostics["response_prefix_array_reconstructed_count"] == 1
    assert candidate.diagnostics["repair_type_counts"] == {"response_prefix_array_reconstructed": 1}


def test_response_prefix_array_reconstructs_event_object_continuation() -> None:
    candidate = _parse(
        '{"event_type":"EventA","arguments":{"Role2":[{"text":"value-two"}]}}]}',
        response_prefix='{"events":[',
    )

    assert candidate.parse_status == "ok"
    assert candidate.events[0].event_type == "EventA"
    assert candidate.events[0].arguments["Role2"][0].text == "value-two"
    assert candidate.diagnostics["response_prefix_reconstructed_count"] == 1
    assert candidate.diagnostics["response_prefix_array_reconstructed_count"] == 1
    assert candidate.diagnostics["repair_type_counts"] == {"response_prefix_array_reconstructed": 1}


def test_response_prefix_array_line4_like_output_is_safely_repaired() -> None:
    candidate = _parse(
        '[{"event_type":"EventA","arguments":{"Role1":[{"text":"value-one"}],"Role2":[{"text":"value-two"}]}}]}',
        response_prefix='{"events":',
    )

    assert candidate.parse_status == "ok"
    assert [event.event_type for event in candidate.events] == ["EventA"]
    assert candidate.diagnostics["response_prefix_array_reconstructed_count"] == 1


def test_complete_json_is_not_prefixed_twice() -> None:
    raw_output = json.dumps(
        {"events": [{"event_type": "EventA", "arguments": {"Role2": [{"text": "value-two"}]}}]},
        ensure_ascii=False,
    )

    candidate = _parse(raw_output)

    assert candidate.parse_status == "ok"
    assert candidate.events[0].arguments["Role2"][0].text == "value-two"
    assert candidate.diagnostics["response_prefix_used"] == 1
    assert candidate.diagnostics["response_prefix_reconstructed_count"] == 0
    assert "response_prefix_reconstructed" not in candidate.diagnostics["repair_type_counts"]


def test_response_prefix_reconstruction_does_not_map_schema_aliases() -> None:
    candidate = _parse('[{"event_type":"EventA_alias","arguments":{"RoleOne":[{"text":"x"}]}}]}')

    assert candidate.parse_status == "schema_violation"
    assert candidate.events == []
    assert candidate.diagnostics["unknown_event_type"] == 1
    assert candidate.diagnostics["unknown_role"] == 0
    assert candidate.diagnostics["schema_violation"] == 1


def test_candidate_list_continuation_is_not_repaired_into_json() -> None:
    candidate = _parse(
        '- id=doc-prefix-1:csg:abc | text={"event_type":"EventA","arguments":{"Role1":[{"text":"x"}]}} '
        "| chunk=chunk_0000 | context=body",
        response_prefix='{"events":[',
    )

    assert candidate.parse_status == "parse_error"
    assert candidate.events == []
    assert candidate.diagnostics["parse_error_primary_subtype"] == "candidate_list_continuation"
    assert candidate.diagnostics["response_prefix_reconstructed_count"] == 0
    assert candidate.diagnostics["repair_type_counts"] == {}


def test_copied_prompt_markers_and_missing_json_are_counted() -> None:
    candidate = _parse("[Schema]\n- EventA: Role1\n[Document]\ncontent only")

    assert candidate.parse_status == "parse_error"
    assert candidate.diagnostics["copied_prompt_marker_count"] == 2
    assert candidate.diagnostics["no_complete_json_object_count"] == 1
    assert candidate.diagnostics["response_prefix_reconstructed_count"] == 0
