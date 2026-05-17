from __future__ import annotations

import json
from pathlib import Path

from sage_dee.v2.data_interface.dataset_loader import V2DatasetDocument, V2DocumentInput, V2GoldDocument
from sage_dee.v2.data_interface.schema_registry import DatasetSchema
from sage_dee.v2.lesp.audit import audit_slot_plans
from sage_dee.v2.lesp.baseline_planner import SchemaEmptyPlanner, TrainPriorPlanner
from sage_dee.v2.lesp.slot_plan import slot_plan_to_dict, validate_slot_plan


def _schema() -> DatasetSchema:
    return DatasetSchema(
        dataset_id="unit",
        schema_dataset="unit",
        schema_path=Path("schema.json"),
        canonical_version=None,
        event_roles={"EventA": ("Role1", "Role2"), "EventB": ("RoleX",)},
        role_to_event_types={"Role1": ("EventA",), "Role2": ("EventA",), "RoleX": ("EventB",)},
    )


def _document(doc_id: str, events: list[dict] | None) -> V2DatasetDocument:
    input_doc = V2DocumentInput(
        doc_id=doc_id,
        dataset_id="unit",
        dataset="unit",
        split="dev",
        content=f"{doc_id} content must not leak",
    )
    if events is None:
        return V2DatasetDocument(input=input_doc, gold=None)
    return V2DatasetDocument(
        input=input_doc,
        gold=V2GoldDocument(
            doc_id=doc_id,
            dataset_id="unit",
            dataset="unit",
            split="train",
            events=events,
        ),
    )


def test_schema_empty_outputs_legal_empty_slot_plan() -> None:
    plan = SchemaEmptyPlanner(_schema()).predict_one(_document("doc-predict-1", None))
    payload = slot_plan_to_dict(plan)

    assert payload == {"doc_id": "doc-predict-1", "dataset": "unit", "slots": []}
    validate_slot_plan(plan, _schema())


def test_train_prior_predicts_without_target_gold_and_does_not_leak_gold_fields() -> None:
    planner = TrainPriorPlanner.fit(
        _schema(),
        [
            _document(
                "doc-train-1",
                [
                    {
                        "event_type": "EventA",
                        "arguments": {
                            "Role1": [{"text": "gold-alpha", "norm_text": "gold-alpha-norm"}],
                            "Role2": [],
                        },
                    }
                ],
            ),
            _document(
                "doc-train-2",
                [
                    {
                        "event_type": "EventA",
                        "arguments": {
                            "Role1": [{"text": "gold-beta", "norm_text": "gold-beta-norm"}],
                            "Role2": [{"text": "gold-gamma", "norm_text": "gold-gamma-norm"}],
                        },
                    }
                ],
            ),
        ],
    )

    predict_doc = _document("doc-dev-1", None)
    plan = planner.predict_one(predict_doc)
    payload = slot_plan_to_dict(plan)
    serialized = json.dumps(payload, ensure_ascii=False)

    assert predict_doc.gold is None
    assert payload["doc_id"] == "doc-dev-1"
    assert payload["dataset"] == "unit"
    assert payload["slots"] == [
        {
            "event_type": "EventA",
            "slot_id": 0,
            "count_confidence": 1.0,
            "role_prior": {"Role1": 1.0, "Role2": 0.5},
            "supporting_candidates": [],
        }
    ]
    assert "gold" not in serialized
    assert "events" not in serialized
    assert "arguments" not in serialized
    assert "text" not in serialized
    assert "norm_text" not in serialized
    assert "content" not in serialized
    assert "surface" not in serialized
    assert "context" not in serialized
    assert audit_slot_plans([plan], _schema())["forbidden_key_violation_count"] == 0


def test_train_prior_refuses_gold_visible_prediction_documents() -> None:
    planner = TrainPriorPlanner.fit(_schema(), [_document("doc-train-1", [{"event_type": "EventB", "arguments": {}}])])

    try:
        planner.predict_one(_document("doc-dev-with-gold", [{"event_type": "EventB", "arguments": {}}]))
    except ValueError as exc:
        assert "predict document must not expose gold" in str(exc)
    else:
        raise AssertionError("TrainPriorPlanner accepted a gold-visible predict document")
