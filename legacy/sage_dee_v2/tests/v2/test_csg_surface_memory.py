from __future__ import annotations

import json

from sage_dee.v2.csg.candidate_builder import build_surface_memory_records
from sage_dee.v2.csg.surface_memory import build_surface_memory, surface_memory_to_dict
from sage_dee.v2.data_interface.dataset_loader import V2DocumentInput, load_documents


def _input_doc(content: str) -> V2DocumentInput:
    return V2DocumentInput(
        doc_id="doc-csg-1",
        dataset_id="unit",
        dataset="unit",
        split="dev",
        content=content,
    )


def test_surface_candidate_ids_are_stable() -> None:
    document = _input_doc(
        "上海万业企业股份有限公司公告。公司监事长张峻购入本公司股票50000股，"
        "披露日期为2008年12月31日，占总股本1.25%。"
    )

    first = build_surface_memory(document)
    second = build_surface_memory(document)

    assert [candidate.candidate_id for candidate in first.candidates] == [
        candidate.candidate_id for candidate in second.candidates
    ]
    assert {"上海万业企业股份有限公司", "50000股", "2008年12月31日", "1.25%"} <= {
        candidate.surface for candidate in first.candidates
    }
    assert all(candidate.source == "rule" for candidate in first.candidates)


def test_surface_memory_serialization_contains_no_gold_labels() -> None:
    memory = build_surface_memory(
        _input_doc("上海万业企业股份有限公司董事会公告，张峻持有50000股。")
    )

    payload = surface_memory_to_dict(memory)
    serialized = json.dumps(payload, ensure_ascii=False)

    assert payload["doc_id"] == "doc-csg-1"
    assert payload["source"] == "document_surface"
    assert payload["candidates"]
    assert "gold" not in serialized
    assert "norm_text" not in serialized
    assert "event_type" not in serialized
    assert "role" not in serialized
    assert "label" not in serialized


def test_predict_mode_surface_memory_records_do_not_expose_gold_events() -> None:
    documents = load_documents("DuEE-Fin-dev500", "test", mode="predict", limit=1)

    rows = list(build_surface_memory_records(documents))
    serialized = json.dumps(rows, ensure_ascii=False)

    assert len(rows) == 1
    assert documents[0].gold is None
    assert rows[0]["doc_id"] == documents[0].doc_id
    assert rows[0]["candidates"]
    assert "gold" not in serialized
    assert "events" not in serialized
