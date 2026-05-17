from __future__ import annotations

import json
from pathlib import Path

from sage_dee.v2.data_interface.schema_registry import DatasetSchema
from sage_dee.v2.getm.parser import candidate_set_to_canonical_prediction, parse_getm_output


def _schema() -> DatasetSchema:
    return DatasetSchema(
        dataset_id="unit",
        schema_dataset="unit-source",
        schema_path=Path("schema.json"),
        canonical_version=None,
        event_roles={"EventA": ("Role1", "Role2")},
        role_to_event_types={"Role1": ("EventA",), "Role2": ("EventA",)},
    )


def _parse(raw_output: str):
    return parse_getm_output(
        raw_output,
        doc_id="doc-format-1",
        candidate_id="doc-format-1:getm:0",
        schema=_schema(),
    )


def test_parser_strips_markdown_fence_and_records_repair() -> None:
    candidate = _parse(
        """
        ```json
        {"events": []}
        ```
        """
    )

    assert candidate.parse_status == "ok"
    assert candidate.events == []
    assert candidate.diagnostics["repaired_count"] == 1
    assert candidate.diagnostics["markdown_fence_stripped_count"] == 1
    assert candidate.diagnostics["repair_type_counts"] == {"markdown_fence_stripped": 1}


def test_parser_extracts_json_from_leading_prose_and_records_repair() -> None:
    candidate = _parse(
        'The answer is below.\n{"events":[{"event_type":"EventA","arguments":{"Role1":[{"text":"value-one"}]}}]}'
    )

    assert candidate.parse_status == "ok"
    assert candidate.events[0].event_type == "EventA"
    assert candidate.diagnostics["repaired_count"] == 1
    assert candidate.diagnostics["extracted_json_object_count"] == 1
    assert candidate.diagnostics["leading_text_removed_count"] == 1
    assert candidate.diagnostics["repair_type_counts"] == {
        "extracted_json_object": 1,
        "leading_text_removed": 1,
    }


def test_parser_extracts_json_before_trailing_prose_and_records_repair() -> None:
    candidate = _parse(
        '{"events":[{"event_type":"EventA","arguments":{"Role2":[{"text":"value-two"}]}}]}\nAdditional analysis.'
    )

    assert candidate.parse_status == "ok"
    assert candidate.events[0].arguments["Role2"][0].text == "value-two"
    assert candidate.diagnostics["repaired_count"] == 1
    assert candidate.diagnostics["extracted_json_object_count"] == 1
    assert candidate.diagnostics["trailing_text_removed_count"] == 1
    assert candidate.diagnostics["repair_type_counts"] == {
        "extracted_json_object": 1,
        "trailing_text_removed": 1,
    }


def test_parser_wraps_top_level_list_and_records_repair() -> None:
    candidate = _parse('[{"event_type":"EventA","arguments":{"Role1":[{"text":"value-one"}]}}]')

    assert candidate.parse_status == "ok"
    assert candidate.events[0].event_type == "EventA"
    assert candidate.diagnostics["repaired_count"] == 1
    assert candidate.diagnostics["top_level_array_wrapped_count"] == 1
    assert candidate.diagnostics["repair_type_counts"] == {"top_level_array_wrapped": 1}


def test_parser_full_object_parses_without_repair() -> None:
    candidate = _parse('{"events":[{"event_type":"EventA","arguments":{"Role1":[{"text":"value-one"}]}}]}')

    assert candidate.parse_status == "ok"
    assert candidate.events[0].arguments["Role1"][0].text == "value-one"
    assert candidate.diagnostics["repaired_count"] == 0
    assert candidate.diagnostics["repair_type_counts"] == {}


def test_parser_reports_parse_error_for_truncated_json() -> None:
    candidate = _parse('{"events":[{"event_type":"EventA","arguments":{"Role1":[{"text":"value-one"}]}}]')

    assert candidate.parse_status == "parse_error"
    assert candidate.events == []
    assert candidate.diagnostics["parse_error"] == 1
    assert candidate.diagnostics["repaired_count"] == 0
    assert candidate.diagnostics["repair_type_counts"] == {}


def test_parser_rejects_invalid_event_type_or_role_without_mapping() -> None:
    candidate = _parse(
        json.dumps(
            {
                "events": [
                    {
                        "event_type": "EventA_alias",
                        "arguments": {"Role1": [{"text": "wrong-event"}]},
                    },
                    {
                        "event_type": "EventA",
                        "arguments": {"RoleOne": [{"text": "wrong-role"}]},
                    },
                ]
            }
        )
    )

    assert candidate.parse_status == "schema_violation"
    assert candidate.diagnostics["unknown_event_type"] == 1
    assert candidate.diagnostics["unknown_role"] == 1
    assert candidate.diagnostics["schema_violation"] == 2
    assert candidate.events == []


def test_final_canonical_export_strips_auxiliary_source_candidate_id_after_repair() -> None:
    candidate = _parse(
        '{"events":[{"event_type":"EventA","arguments":{"Role1":[{"text":"value-one",'
        '"source_candidate_id":"cand-1"}]}}]} trailing text'
    )

    canonical = candidate_set_to_canonical_prediction(candidate)

    assert candidate.parse_status == "ok"
    assert canonical == {
        "doc_id": "doc-format-1",
        "events": [{"event_type": "EventA", "arguments": {"Role1": [{"text": "value-one"}]}}],
    }
    serialized = json.dumps(canonical, ensure_ascii=False)
    assert "source_candidate_id" not in serialized
