from __future__ import annotations

import pytest

from sage_dee.v2.contracts.surface import SurfaceCandidate, SurfaceMemory
from sage_dee.v2.csg.audit import compute_audit_summary
from sage_dee.v2.csg.weak_alignment import align_gold_arguments
from sage_dee.v2.data_interface.dataset_loader import V2DatasetDocument, V2DocumentInput, V2GoldDocument
from scripts.v2.build_surface_memory import resolve_document_mode


def _document(content: str, argument_text: str, *, role: str = "Pledger") -> V2DatasetDocument:
    input_doc = V2DocumentInput(
        doc_id="doc-align-1",
        dataset_id="unit",
        dataset="unit",
        split="train",
        content=content,
    )
    gold = V2GoldDocument(
        doc_id=input_doc.doc_id,
        dataset_id=input_doc.dataset_id,
        dataset=input_doc.dataset,
        split=input_doc.split,
        events=[
            {
                "event_id": "0",
                "event_type": "EquityPledge",
                "arguments": {role: [{"text": argument_text, "norm_text": "ignored"}]},
                "empty_roles": [],
            }
        ],
    )
    return V2DatasetDocument(input=input_doc, gold=gold)


def _memory(candidates: list[SurfaceCandidate]) -> SurfaceMemory:
    return SurfaceMemory(doc_id="doc-align-1", candidates=candidates)


def test_unlocated_argument_is_not_forced_into_positive_candidate() -> None:
    document = _document("张三持有50000股。", "不存在的论元")
    memory = _memory(
        [
            SurfaceCandidate(
                candidate_id="doc-align-1:csg:1",
                doc_id="doc-align-1",
                surface="50000股",
                context="张三持有50000股。",
                chunk_id="chunk_0000",
            )
        ]
    )

    records = align_gold_arguments(document, memory)

    assert len(records) == 1
    assert records[0].status == "unlocated"
    assert records[0].candidate_ids == []
    assert records[0].ambiguous is False


def test_ambiguous_exact_surface_match_is_recorded() -> None:
    document = _document("张三增持股份。随后张三继续增持。", "张三")
    memory = _memory(
        [
            SurfaceCandidate(
                candidate_id="doc-align-1:csg:1",
                doc_id="doc-align-1",
                surface="张三",
                context="张三增持股份。",
                chunk_id="chunk_0000",
                char_start=0,
                char_end=2,
            ),
            SurfaceCandidate(
                candidate_id="doc-align-1:csg:2",
                doc_id="doc-align-1",
                surface="张三",
                context="随后张三继续增持。",
                chunk_id="chunk_0001",
                char_start=9,
                char_end=11,
            ),
        ]
    )

    records = align_gold_arguments(document, memory)

    assert records[0].status == "located"
    assert records[0].ambiguous is True
    assert records[0].match_count == 2
    assert records[0].candidate_ids == ["doc-align-1:csg:1", "doc-align-1:csg:2"]


def test_strict_match_does_not_apply_semantic_or_numeric_normalization() -> None:
    document = _document("公司支付1,000,000元。", "100万元")
    memory = _memory(
        [
            SurfaceCandidate(
                candidate_id="doc-align-1:csg:1",
                doc_id="doc-align-1",
                surface="1,000,000元",
                context="公司支付1,000,000元。",
                chunk_id="chunk_0000",
            )
        ]
    )

    records = align_gold_arguments(document, memory)

    assert records[0].status == "unlocated"
    assert records[0].candidate_ids == []


def test_audit_summary_reports_located_unlocated_and_ambiguous_rates() -> None:
    document = _document("张三增持股份。随后张三继续增持。", "张三")
    memory = _memory(
        [
            SurfaceCandidate("doc-align-1:csg:1", "doc-align-1", "张三", "张三增持股份。", "chunk_0000"),
            SurfaceCandidate("doc-align-1:csg:2", "doc-align-1", "张三", "随后张三继续增持。", "chunk_0001"),
        ]
    )
    alignments = align_gold_arguments(document, memory)

    summary = compute_audit_summary([memory], alignments, recall_ks=(1, 2))

    assert summary["candidate_count_per_doc"] == {"doc-align-1": 2}
    assert summary["gold_argument_located_rate"] == 1.0
    assert summary["unlocated_argument_rate"] == 0.0
    assert summary["ambiguous_match_rate"] == 1.0
    assert summary["candidate_recall_at_k"] == {"1": 1.0, "2": 1.0}
    assert summary["per_role_located_rate"] == {"Pledger": 1.0}
    assert summary["per_event_type_located_rate"] == {"EquityPledge": 1.0}


def test_test_split_gold_audit_requires_explicit_override() -> None:
    with pytest.raises(ValueError, match="test split gold audit"):
        resolve_document_mode("test", "train", allow_gold_audit=False)

    assert resolve_document_mode("test", "train", allow_gold_audit=True) == "train"
    assert resolve_document_mode("test", "predict", allow_gold_audit=False) == "predict"
