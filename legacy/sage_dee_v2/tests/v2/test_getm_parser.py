from __future__ import annotations

import json
from pathlib import Path

from sage_dee.v2.data_interface.schema_registry import DatasetSchema
from sage_dee.v2.getm.parser import candidate_set_to_canonical_prediction, parse_getm_output
from sage_dee.v2.pipeline.export_canonical import validate_minimal_canonical_prediction


def _schema() -> DatasetSchema:
    return DatasetSchema(
        dataset_id="unit",
        schema_dataset="unit-source",
        schema_path=Path("schema.json"),
        canonical_version=None,
        event_roles={"EventA": ("Role1", "Role2")},
        role_to_event_types={"Role1": ("EventA",), "Role2": ("EventA",)},
    )


def test_parser_strips_auxiliary_fields_for_canonical_prediction() -> None:
    raw_output = json.dumps(
        {
            "events": [
                {
                    "event_type": "EventA",
                    "slot_id": 0,
                    "logprob": -0.3,
                    "arguments": {
                        "Role1": [
                            {
                                "text": "value-one",
                                "source_candidate_id": "cand-1",
                                "alignment_score": 0.7,
                            }
                        ]
                    },
                }
            ]
        },
        ensure_ascii=False,
    )

    candidate = parse_getm_output(
        raw_output,
        doc_id="doc-1",
        candidate_id="doc-1:getm:0",
        schema=_schema(),
    )
    canonical = candidate_set_to_canonical_prediction(candidate)

    assert candidate.parse_status == "ok"
    assert canonical == {
        "doc_id": "doc-1",
        "events": [{"event_type": "EventA", "arguments": {"Role1": [{"text": "value-one"}]}}],
    }
    validate_minimal_canonical_prediction(canonical)
    serialized = json.dumps(canonical, ensure_ascii=False)
    assert "source_candidate_id" not in serialized
    assert "slot_id" not in serialized
    assert "alignment_score" not in serialized
    assert "logprob" not in serialized


def test_parser_records_schema_violations_and_duplicates() -> None:
    candidate = parse_getm_output(
        """
        ```json
        {"events":[
          {"event_type":"UnknownEvent","arguments":{"Role1":[{"text":"x"}]}},
          {"event_type":"EventA","arguments":{
            "UnknownRole":[{"text":"bad"}],
            "Role1":[{"text":"value-one"},{"text":"value-one"}]
          }}
        ]}
        ```
        """,
        doc_id="doc-2",
        candidate_id="doc-2:getm:0",
        schema=_schema(),
    )

    assert candidate.parse_status == "schema_violation"
    assert candidate.diagnostics["unknown_event_type"] == 1
    assert candidate.diagnostics["unknown_role"] == 1
    assert candidate.diagnostics["duplicate_argument"] == 0
    assert candidate.diagnostics["schema_violation"] == 2
    assert candidate_set_to_canonical_prediction(candidate) == {
        "doc_id": "doc-2",
        "events": [],
    }


def test_parser_rejects_literal_role_key() -> None:
    candidate = parse_getm_output(
        '{"events":[{"event_type":"EventA","arguments":{"role":["value-one"],"Role1":["value-two"]}}]}',
        doc_id="doc-literal-role-1",
        candidate_id="doc-literal-role-1:getm:0",
        schema=_schema(),
        output_format="minimal_text",
    )

    assert candidate.parse_status == "schema_violation"
    assert candidate.events == []
    assert candidate.diagnostics["unknown_role"] == 1
    assert candidate.diagnostics["schema_violation"] == 1


def test_parser_rejects_unknown_role_without_mapping() -> None:
    candidate = parse_getm_output(
        '{"events":[{"event_type":"EventA","arguments":{"RoleOne":["bad"],"Role1":["valid"]}}]}',
        doc_id="doc-unknown-role-1",
        candidate_id="doc-unknown-role-1:getm:0",
        schema=_schema(),
        output_format="minimal_text",
    )

    assert candidate.parse_status == "schema_violation"
    assert candidate.events == []
    assert candidate.diagnostics["unknown_role"] == 1
    assert candidate.diagnostics["schema_violation"] == 1


def test_parser_rejects_unknown_event_type_without_mapping() -> None:
    candidate = parse_getm_output(
        '{"events":[{"event_type":"EventA_alias","arguments":{"Role1":["bad"]}}]}',
        doc_id="doc-unknown-event-1",
        candidate_id="doc-unknown-event-1:getm:0",
        schema=_schema(),
        output_format="minimal_text",
    )

    assert candidate.parse_status == "schema_violation"
    assert candidate.events == []
    assert candidate.diagnostics["unknown_event_type"] == 1
    assert candidate.diagnostics["schema_violation"] == 1


def test_parser_accepts_minimal_text_role_values() -> None:
    candidate = parse_getm_output(
        '{"events":[{"event_type":"EventA","arguments":{"Role1":["value-one","value-two"]}}]}',
        doc_id="doc-minimal-1",
        candidate_id="doc-minimal-1:getm:0",
        schema=_schema(),
        output_format="minimal_text",
    )

    assert candidate.parse_status == "ok"
    assert candidate_set_to_canonical_prediction(candidate) == {
        "doc_id": "doc-minimal-1",
        "events": [
            {
                "event_type": "EventA",
                "arguments": {"Role1": [{"text": "value-one"}, {"text": "value-two"}]},
            }
        ],
    }


def test_parser_keeps_argument_object_compatibility() -> None:
    candidate = parse_getm_output(
        '{"events":[{"event_type":"EventA","arguments":{"Role2":[{"text":"value-two"}]}}]}',
        doc_id="doc-object-1",
        candidate_id="doc-object-1:getm:0",
        schema=_schema(),
        output_format="argument_object",
    )

    assert candidate.parse_status == "ok"
    assert candidate_set_to_canonical_prediction(candidate) == {
        "doc_id": "doc-object-1",
        "events": [{"event_type": "EventA", "arguments": {"Role2": [{"text": "value-two"}]}}],
    }


def test_minimal_text_counts_unexpected_source_candidate_id_without_exporting_it() -> None:
    candidate = parse_getm_output(
        '{"events":[{"event_type":"EventA","arguments":{"Role1":[{"text":"value-one",'
        '"source_candidate_id":"cand-1"}]}}]}',
        doc_id="doc-minimal-source-1",
        candidate_id="doc-minimal-source-1:getm:0",
        schema=_schema(),
        output_format="minimal_text",
    )

    canonical = candidate_set_to_canonical_prediction(candidate)

    assert candidate.parse_status == "ok"
    assert candidate.diagnostics["unexpected_source_candidate_id_count"] == 1
    assert canonical == {
        "doc_id": "doc-minimal-source-1",
        "events": [{"event_type": "EventA", "arguments": {"Role1": [{"text": "value-one"}]}}],
    }
    assert "source_candidate_id" not in json.dumps(canonical, ensure_ascii=False)


def test_parser_counts_schema_violation_subtypes() -> None:
    candidate = parse_getm_output(
        json.dumps(
            {
                "events": [
                    ["not-an-event-object"],
                    {"event_type": 7, "arguments": {"Role1": ["bad-event-type"]}},
                    {"event_type": "UnknownEvent", "arguments": {"Role1": ["bad-event"]}},
                    {"event_type": "EventA", "arguments": ["not-a-mapping"]},
                    {"event_type": "EventA", "arguments": {"UnknownRole": ["bad-role"]}},
                    {"event_type": "EventA", "arguments": {"Role1": "not-a-list"}},
                    {"event_type": "EventA", "arguments": {}},
                ]
            },
            ensure_ascii=False,
        ),
        doc_id="doc-schema-subtypes-1",
        candidate_id="doc-schema-subtypes-1:getm:0",
        schema=_schema(),
        output_format="minimal_text",
    )

    assert candidate.parse_status == "schema_violation"
    assert candidate.diagnostics["invalid_event_object_count"] == 1
    assert candidate.diagnostics["event_type_not_string_count"] == 1
    assert candidate.diagnostics["unknown_event_type"] == 1
    assert candidate.diagnostics["invalid_arguments_shape_count"] == 1
    assert candidate.diagnostics["unknown_role"] == 1
    assert candidate.diagnostics["role_value_not_list_count"] == 1
    assert candidate.diagnostics["empty_arguments_count"] == 2
    assert candidate.diagnostics["raw_event_count"] == 7
    assert candidate.diagnostics["accepted_event_count"] == 2


def test_parser_does_not_complete_truncated_json() -> None:
    candidate = parse_getm_output(
        '{"events": [{"event_type": "EventA", "arguments": {"Role1": [{"text": "x"}]}}],}',
        doc_id="doc-3",
        candidate_id="doc-3:getm:0",
        schema=_schema(),
    )

    assert candidate.parse_status == "parse_error"
    assert candidate.events == []
    assert candidate.diagnostics["parse_error"] == 1
