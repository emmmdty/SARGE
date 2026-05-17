from __future__ import annotations

from pathlib import Path

import pytest

from sage_dee.v2.data_interface.schema_registry import DatasetSchema
from sage_dee.v2.mrs.features import compute_candidate_features, compute_feature_rows


def _schema() -> DatasetSchema:
    return DatasetSchema(
        dataset_id="unit",
        schema_dataset="unit-source",
        schema_path=Path("schema.json"),
        canonical_version=None,
        event_roles={"EventA": ("Role1", "Role2"), "EventB": ("RoleX",)},
        role_to_event_types={"Role1": ("EventA",), "Role2": ("EventA",), "RoleX": ("EventB",)},
    )


def test_feature_vector_records_schema_duplicate_empty_and_grounding_features() -> None:
    candidate = {
        "candidate_id": "doc-1:getm:0",
        "doc_id": "doc-1",
        "parse_status": "schema_violation",
        "generation_score": -0.5,
        "diagnostics": {
            "schema_violation": 1,
            "unknown_event_type": 1,
            "unknown_role": 2,
            "duplicate_argument": 1,
            "raw_event_count": 2,
            "accepted_event_count": 1,
        },
        "events": [{"event_type": "EventA", "arguments": {"Role1": [{"text": "alpha"}]}}],
    }
    surface_memory = {
        "doc_id": "doc-1",
        "source": "document_surface",
        "candidates": [{"candidate_id": "c1", "doc_id": "doc-1", "surface": "alpha", "role_score": 0.8}],
    }
    slot_plan = {
        "doc_id": "doc-1",
        "dataset": "unit",
        "slots": [{"event_type": "EventA", "slot_id": 0, "count_confidence": 0.9, "role_prior": {"Role1": 1.0}}],
    }

    row = compute_candidate_features(
        candidate,
        schema=_schema(),
        surface_memory=surface_memory,
        slot_plan=slot_plan,
        peer_candidates=[candidate],
    )
    features = row["features"]

    assert features["schema_valid_rate"] < 1.0
    assert features["role_coverage"] == pytest.approx(0.5)
    assert features["duplicate_argument_rate"] > 0.0
    assert features["unknown_event_type_count"] == 1.0
    assert features["unknown_role_count"] == 2.0
    assert features["empty_prediction"] == 0.0
    assert features["candidate_length"] == 1.0
    assert features["avg_logprob"] == -0.5
    assert features["grounding_confidence"] == pytest.approx(0.8)
    assert features["lesp_event_count_agreement"] == pytest.approx(1.0)
    assert features["self_consistency_argument_jaccard"] == pytest.approx(1.0)


def test_self_consistency_features_compare_candidates_for_same_doc() -> None:
    candidates = [
        {
            "candidate_id": "doc-1:getm:0",
            "doc_id": "doc-1",
            "events": [{"event_type": "EventA", "arguments": {"Role1": [{"text": "alpha"}]}}],
            "diagnostics": {},
        },
        {
            "candidate_id": "doc-1:getm:1",
            "doc_id": "doc-1",
            "events": [
                {
                    "event_type": "EventA",
                    "arguments": {"Role1": [{"text": "alpha"}], "Role2": [{"text": "beta"}]},
                }
            ],
            "diagnostics": {},
        },
    ]

    rows = compute_feature_rows(candidates, schema=_schema())

    assert rows[0]["features"]["self_consistency_argument_jaccard"] == pytest.approx(0.5)
    assert rows[1]["features"]["self_consistency_argument_jaccard"] == pytest.approx(0.5)
    assert rows[0]["features"]["self_consistency_event_type_jaccard"] == pytest.approx(1.0)
