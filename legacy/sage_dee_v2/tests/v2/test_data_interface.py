from __future__ import annotations

from pathlib import Path

import pytest

from sage_dee.v2.data_interface.dataset_loader import iter_documents, load_documents
from sage_dee.v2.data_interface.schema_registry import load_schema

DATASETS = ("DuEE-Fin-dev500", "ChFinAnn", "DocFEE-dev1000")
SPLITS = ("train", "dev", "test")


def test_expected_evaluator_gold_paths_exist() -> None:
    for dataset in DATASETS:
        dataset_root = Path("data") / dataset
        assert dataset_root.exists(), dataset
        assert (dataset_root / "schema.json").is_file(), dataset
        for split in SPLITS:
            assert (dataset_root / f"{split}.jsonl").is_file(), f"{dataset}/{split}"


def test_schema_registry_enforces_closed_event_types_and_roles() -> None:
    schema = load_schema("ChFinAnn")

    schema.validate_event_type("EquityPledge")
    schema.validate_role("EquityPledge", "Pledger")

    with pytest.raises(ValueError, match="Unknown event_type"):
        schema.validate_event_type("质押")
    with pytest.raises(ValueError, match="Unknown role"):
        schema.validate_role("EquityPledge", "质押方")


def test_predict_mode_does_not_expose_gold_events() -> None:
    documents = load_documents("DuEE-Fin-dev500", "test", mode="predict", limit=1)

    assert len(documents) == 1
    document = documents[0]
    assert document.gold is None
    assert document.input.doc_id
    assert document.input.content
    input_payload = document.input.to_dict()
    assert "events" not in input_payload
    assert "events_gold" not in input_payload
    assert "gold" not in input_payload
    assert "raw_annotations" not in input_payload


def test_train_mode_exposes_gold_only_on_gold_field() -> None:
    documents = load_documents("DocFEE-dev1000", "train", mode="train", limit=1)

    assert len(documents) == 1
    document = documents[0]
    assert document.gold is not None
    assert document.gold.events
    assert "events" not in document.input.to_dict()


def test_iter_documents_respects_limit() -> None:
    documents = list(iter_documents("ChFinAnn", "dev", mode="predict", limit=2))

    assert len(documents) == 2
    assert all(document.gold is None for document in documents)


def test_dataset_schemas_are_not_merged() -> None:
    chfinann = load_schema("ChFinAnn")
    duee_fin = load_schema("DuEE-Fin-dev500")
    docfee = load_schema("DocFEE-dev1000")

    chfinann.validate_event_type("EquityPledge")
    duee_fin.validate_event_type("质押")
    docfee.validate_event_type("股权质押")

    with pytest.raises(ValueError, match="Unknown event_type"):
        duee_fin.validate_event_type("EquityPledge")
    with pytest.raises(ValueError, match="Unknown event_type"):
        chfinann.validate_event_type("质押")
    with pytest.raises(ValueError, match="Unknown event_type"):
        duee_fin.validate_event_type("股权质押")
