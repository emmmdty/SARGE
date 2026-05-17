from __future__ import annotations

from pathlib import Path

import pytest

from sage_dee.v2.data_interface.dataset_loader import V2DatasetDocument, V2DocumentInput, V2GoldDocument
from sage_dee.v2.data_interface.schema_registry import DatasetSchema
from sage_dee.v2.mrs.oracle_gap import compute_oracle_gap_rows
from sage_dee.v2.mrs.selector import select_candidate_rows
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


def _predict_document() -> V2DatasetDocument:
    return V2DatasetDocument(
        input=V2DocumentInput(doc_id="doc-1", dataset_id="unit", dataset="unit", split="dev", content="alpha beta"),
        gold=None,
    )


def test_selector_rejects_gold_visible_documents() -> None:
    document = _predict_document()
    gold_document = V2DatasetDocument(
        input=document.input,
        gold=V2GoldDocument(
            doc_id="doc-1",
            dataset_id="unit",
            dataset="unit",
            split="dev",
            events=[{"event_type": "EventA", "arguments": {"Role1": [{"text": "alpha"}]}}],
        ),
    )

    with pytest.raises(ValueError, match="must not expose gold"):
        select_candidate_rows(
            candidates=[{"candidate_id": "doc-1:getm:0", "doc_id": "doc-1", "events": []}],
            documents=[gold_document],
            schema=_schema(),
            model={"version": "mrs_simple_ranker_v0", "weights": {}},
        )


def test_selector_chooses_best_candidate_and_returns_canonical_prediction() -> None:
    candidates = [
        {
            "candidate_id": "doc-1:getm:0",
            "doc_id": "doc-1",
            "candidate_index": 0,
            "events": [],
            "diagnostics": {},
        },
        {
            "candidate_id": "doc-1:getm:1",
            "doc_id": "doc-1",
            "candidate_index": 1,
            "events": [
                {
                    "event_type": "EventA",
                    "slot_id": 0,
                    "arguments": {"Role1": [{"text": "alpha", "source_candidate_id": "csg-1"}]},
                }
            ],
            "diagnostics": {},
        },
    ]
    result = select_candidate_rows(
        candidates=candidates,
        documents=[_predict_document()],
        schema=_schema(),
        model={"version": "mrs_simple_ranker_v0", "weights": {"role_coverage": 2.0, "empty_prediction": -1.0}},
    )

    assert result.selected_rows[0]["candidate_id"] == "doc-1:getm:1"
    assert result.canonical_predictions == [
        {"doc_id": "doc-1", "events": [{"event_type": "EventA", "arguments": {"Role1": [{"text": "alpha"}]}}]}
    ]
    validate_minimal_canonical_prediction(result.canonical_predictions[0])
    assert "slot_id" not in str(result.canonical_predictions)
    assert "source_candidate_id" not in str(result.canonical_predictions)


def test_oracle_gap_rows_compute_scores_without_order_assumption() -> None:
    rows = compute_oracle_gap_rows(
        selected_rows=[{"doc_id": "doc-1", "candidate_id": "b"}],
        reward_rows=[
            {"doc_id": "doc-1", "candidate_id": "a", "candidate_index": 0, "reward": 0.4},
            {"doc_id": "doc-1", "candidate_id": "b", "candidate_index": 1, "reward": 0.6},
            {"doc_id": "doc-1", "candidate_id": "c", "candidate_index": 2, "reward": 0.8},
        ],
    )

    assert rows == [
        {
            "doc_id": "doc-1",
            "greedy_candidate_id": "a",
            "selected_candidate_id": "b",
            "oracle_candidate_id": "c",
            "greedy_score": 0.4,
            "selected_score": 0.6,
            "oracle_best_score": 0.8,
            "oracle_gap": 0.2,
            "mrs_gain": 0.2,
        }
    ]
