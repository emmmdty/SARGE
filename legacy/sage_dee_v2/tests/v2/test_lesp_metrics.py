from __future__ import annotations

from pathlib import Path

from sage_dee.v2.data_interface.dataset_loader import V2DatasetDocument, V2DocumentInput, V2GoldDocument
from sage_dee.v2.data_interface.schema_registry import DatasetSchema
from sage_dee.v2.lesp.metrics import compute_slot_plan_metrics
from sage_dee.v2.lesp.slot_plan import EventSlot, SlotPlanDocument


def _schema() -> DatasetSchema:
    return DatasetSchema(
        dataset_id="unit",
        schema_dataset="unit",
        schema_path=Path("schema.json"),
        canonical_version=None,
        event_roles={"EventA": ("Role1", "Role2"), "EventB": ("RoleX",)},
        role_to_event_types={"Role1": ("EventA",), "Role2": ("EventA",), "RoleX": ("EventB",)},
    )


def _document(doc_id: str, events: list[dict]) -> V2DatasetDocument:
    input_doc = V2DocumentInput(
        doc_id=doc_id,
        dataset_id="unit",
        dataset="unit",
        split="dev",
        content="content",
    )
    return V2DatasetDocument(
        input=input_doc,
        gold=V2GoldDocument(
            doc_id=doc_id,
            dataset_id="unit",
            dataset="unit",
            split="dev",
            events=events,
        ),
    )


def test_slot_plan_metrics_cover_presence_count_bucket_multi_event_and_roles() -> None:
    gold_documents = [
        _document(
            "doc-1",
            [
                {"event_type": "EventA", "arguments": {"Role1": [{"text": "a"}], "Role2": []}},
                {"event_type": "EventA", "arguments": {"Role1": [], "Role2": [{"text": "b"}]}},
            ],
        ),
        _document("doc-2", [{"event_type": "EventB", "arguments": {"RoleX": [{"text": "x"}]}}]),
    ]
    predictions = [
        SlotPlanDocument(
            doc_id="doc-1",
            dataset="unit",
            slots=[
                EventSlot("EventA", 0, 0.8, {"Role1": 0.8, "Role2": 0.2}, []),
                EventSlot("EventA", 1, 0.7, {"Role1": 0.2, "Role2": 0.8}, []),
            ],
        ),
        SlotPlanDocument(
            doc_id="doc-2",
            dataset="unit",
            slots=[EventSlot("EventA", 0, 0.6, {"Role1": 0.9, "Role2": 0.1}, [])],
        ),
    ]

    metrics = compute_slot_plan_metrics(predictions, gold_documents, _schema())

    assert metrics["event_presence_precision"] == 0.5
    assert metrics["event_presence_recall"] == 0.5
    assert metrics["event_presence_f1"] == 0.5
    assert metrics["event_count_accuracy"] == 2 / 4
    assert metrics["event_count_bucket_accuracy"] == 2 / 4
    assert metrics["same_type_multi_event_recall"] == 1.0
    assert metrics["role_occupancy_precision"] == 2 / 3
    assert metrics["role_occupancy_recall"] == 2 / 3
    assert metrics["role_occupancy_f1"] == 2 / 3
