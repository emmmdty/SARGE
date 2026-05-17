from __future__ import annotations

from pathlib import Path

import pytest

from sage_dee.v2.data_interface.dataset_loader import V2DatasetDocument, V2DocumentInput
from sage_dee.v2.data_interface.schema_registry import DatasetSchema
from sage_dee.v2.mrs.reward import compute_candidate_reward


def _schema() -> DatasetSchema:
    return DatasetSchema(
        dataset_id="unit",
        schema_dataset="unit-source",
        schema_path=Path("schema.json"),
        canonical_version=None,
        event_roles={"EventA": ("Role1", "Role2")},
        role_to_event_types={"Role1": ("EventA",), "Role2": ("EventA",)},
    )


def _gold_events() -> list[dict]:
    return [{"event_type": "EventA", "arguments": {"Role1": [{"text": "alpha"}], "Role2": [{"text": "beta"}]}}]


def test_reward_requires_gold_visible_document() -> None:
    document = V2DatasetDocument(
        input=V2DocumentInput(doc_id="doc-1", dataset_id="unit", dataset="unit", split="dev", content="alpha beta"),
        gold=None,
    )

    with pytest.raises(ValueError, match="requires gold"):
        compute_candidate_reward(
            {"candidate_id": "c1", "doc_id": "doc-1", "events": []},
            document=document,
            schema=_schema(),
        )


def test_reward_rewards_surface_and_record_match() -> None:
    row = compute_candidate_reward(
        {
            "candidate_id": "doc-1:getm:0",
            "doc_id": "doc-1",
            "events": _gold_events(),
            "diagnostics": {},
        },
        gold_events=_gold_events(),
        schema=_schema(),
    )

    assert row["candidate_id"] == "doc-1:getm:0"
    assert row["metric_source"] == "sage_dee_v2.lightweight_surface_record_reward.v0"
    assert row["uses_gold"] is True
    assert row["components"]["surface_f1"] == pytest.approx(1.0)
    assert row["components"]["record_f1"] == pytest.approx(1.0)
    assert row["reward"] > 1.0


def test_reward_penalizes_schema_violation_duplicate_and_empty_prediction() -> None:
    schema = _schema()
    good = compute_candidate_reward(
        {"candidate_id": "good", "doc_id": "doc-1", "events": _gold_events(), "diagnostics": {}},
        gold_events=_gold_events(),
        schema=schema,
    )
    duplicate = compute_candidate_reward(
        {
            "candidate_id": "dup",
            "doc_id": "doc-1",
            "events": [{"event_type": "EventA", "arguments": {"Role1": [{"text": "alpha"}]}}],
            "diagnostics": {"duplicate_argument": 2},
        },
        gold_events=_gold_events(),
        schema=schema,
    )
    violation = compute_candidate_reward(
        {
            "candidate_id": "bad-schema",
            "doc_id": "doc-1",
            "events": [{"event_type": "EventA", "arguments": {"Role1": [{"text": "alpha"}]}}],
            "diagnostics": {"schema_violation": 1, "unknown_role": 1},
        },
        gold_events=_gold_events(),
        schema=schema,
    )
    empty = compute_candidate_reward(
        {"candidate_id": "empty", "doc_id": "doc-1", "events": [], "diagnostics": {}},
        gold_events=_gold_events(),
        schema=schema,
    )

    assert duplicate["components"]["penalty_duplicate"] > 0.0
    assert violation["components"]["penalty_schema"] > 0.0
    assert empty["components"]["penalty_empty"] > 0.0
    assert good["reward"] > duplicate["reward"] > empty["reward"]
    assert good["reward"] > violation["reward"] > empty["reward"]
