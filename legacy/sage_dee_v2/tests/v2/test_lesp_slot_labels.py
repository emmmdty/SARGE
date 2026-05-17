from __future__ import annotations

import json
from pathlib import Path

import pytest

from sage_dee.v2.data_interface.dataset_loader import V2DatasetDocument, V2DocumentInput, V2GoldDocument
from sage_dee.v2.data_interface.schema_registry import DatasetSchema
from sage_dee.v2.lesp.slot_labels import count_bucket, derive_slot_labels


def _schema() -> DatasetSchema:
    return DatasetSchema(
        dataset_id="unit",
        schema_dataset="unit",
        schema_path=Path("schema.json"),
        canonical_version=None,
        event_roles={"EventA": ("Role1", "Role2"), "EventB": ("RoleX",)},
        role_to_event_types={"Role1": ("EventA",), "Role2": ("EventA",), "RoleX": ("EventB",)},
    )


def _document(events: list[dict]) -> V2DatasetDocument:
    input_doc = V2DocumentInput(
        doc_id="doc-lesp-labels-1",
        dataset_id="unit",
        dataset="unit",
        split="train",
        content="content must not be serialized into labels",
    )
    return V2DatasetDocument(
        input=input_doc,
        gold=V2GoldDocument(
            doc_id=input_doc.doc_id,
            dataset_id=input_doc.dataset_id,
            dataset=input_doc.dataset,
            split=input_doc.split,
            events=events,
        ),
    )


def test_count_bucket_maps_zero_one_two_and_three_plus() -> None:
    assert count_bucket(0) == "0"
    assert count_bucket(1) == "1"
    assert count_bucket(2) == "2"
    assert count_bucket(3) == "3+"
    assert count_bucket(9) == "3+"


def test_slot_labels_derive_counts_role_occupancy_and_same_type_multi_event() -> None:
    labels = derive_slot_labels(
        _document(
            [
                {
                    "event_type": "EventA",
                    "arguments": {
                        "Role1": [{"text": "alpha", "norm_text": "ALPHA"}],
                        "Role2": [],
                    },
                },
                {
                    "event_type": "EventA",
                    "arguments": {
                        "Role1": [],
                        "Role2": [{"text": "beta", "norm_text": "BETA"}],
                    },
                },
            ]
        ),
        _schema(),
    )

    by_event_type = {row.event_type: row for row in labels.event_type_labels}

    assert by_event_type["EventA"].presence is True
    assert by_event_type["EventA"].event_count == 2
    assert by_event_type["EventA"].count_bucket == "2"
    assert by_event_type["EventA"].same_type_multi_event is True
    assert by_event_type["EventA"].role_occupancy == {"Role1": True, "Role2": True}
    assert by_event_type["EventB"].presence is False
    assert by_event_type["EventB"].event_count == 0
    assert by_event_type["EventB"].count_bucket == "0"
    assert by_event_type["EventB"].role_occupancy == {"RoleX": False}

    assert [slot.slot_id for slot in labels.record_slot_labels] == [0, 1]
    assert labels.record_slot_labels[0].role_occupancy == {"Role1": True, "Role2": False}
    assert labels.record_slot_labels[1].role_occupancy == {"Role1": False, "Role2": True}


def test_slot_label_serialization_excludes_argument_text_and_norm_text() -> None:
    labels = derive_slot_labels(
        _document(
            [
                {
                    "event_type": "EventB",
                    "arguments": {"RoleX": [{"text": "secret-text", "norm_text": "secret-norm"}]},
                }
            ]
        ),
        _schema(),
    )

    payload = labels.to_dict()
    serialized = json.dumps(payload, ensure_ascii=False)

    assert payload["doc_id"] == "doc-lesp-labels-1"
    assert payload["dataset"] == "unit"
    assert "secret-text" not in serialized
    assert "secret-norm" not in serialized
    assert "norm_text" not in serialized
    assert "arguments" not in serialized
    assert "content" not in serialized


def test_slot_labels_require_gold_visible_document() -> None:
    document = _document([])
    predict_document = V2DatasetDocument(input=document.input, gold=None)

    with pytest.raises(ValueError, match="gold-visible"):
        derive_slot_labels(predict_document, _schema())
