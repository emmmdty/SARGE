from __future__ import annotations

from pathlib import Path

import pytest

from sage_dee.v2.contracts.surface import SurfaceCandidate
from sage_dee.v2.data_interface.dataset_loader import V2DocumentInput
from sage_dee.v2.data_interface.schema_registry import DatasetSchema
from sage_dee.v2.getm.prompt_builder import build_getm_prompt
from sage_dee.v2.lesp.slot_plan import EventSlot, SlotPlanDocument


def _schema() -> DatasetSchema:
    return DatasetSchema(
        dataset_id="unit",
        schema_dataset="unit-source",
        schema_path=Path("schema.json"),
        canonical_version=None,
        event_roles={"EventA": ("Role1", "Role2"), "EventB": ("RoleX",)},
        role_to_event_types={"Role1": ("EventA",), "Role2": ("EventA",), "RoleX": ("EventB",)},
    )


def _document() -> V2DocumentInput:
    return V2DocumentInput(
        doc_id="doc-getm-1",
        dataset_id="unit",
        dataset="unit-source",
        split="dev",
        content="Alpha company announced one EventA record with value-one.",
    )


def test_prompt_contains_required_sections_and_original_schema_labels() -> None:
    prompt = build_getm_prompt(
        dataset="unit",
        schema=_schema(),
        document=_document(),
        surface_candidates=[
            SurfaceCandidate(
                candidate_id="cand-1",
                doc_id="doc-getm-1",
                surface="value-one",
                context="record with value-one",
                chunk_id="chunk-0001",
            )
        ],
        slot_plan=SlotPlanDocument(
            doc_id="doc-getm-1",
            dataset="unit",
            slots=[
                EventSlot(
                    event_type="EventA",
                    slot_id=0,
                    count_confidence=0.8,
                    role_prior={"Role1": 0.9, "Role2": 0.1},
                    supporting_candidates=["cand-1"],
                )
            ],
        ),
    )

    for section in (
        "[Dataset]",
        "[Schema]",
        "[Document]",
        "[Surface Candidates]",
        "[Event Slot Plan]",
        "[Instruction]",
    ):
        assert section in prompt
    assert "- EventA: Role1, Role2" in prompt
    assert "Use the original dataset schema labels exactly" in prompt
    assert "Prefer copying text from Surface Candidates" in prompt
    assert "Do not invent event types or roles" in prompt
    assert "cand-1" in prompt
    assert "slot_id=0" in prompt


def test_compact_candidate_render_omits_ids_chunks_and_context_by_default() -> None:
    prompt = build_getm_prompt(
        dataset="unit",
        schema=_schema(),
        document=_document(),
        surface_candidates=[
            _candidate(
                "doc-getm-1:csg:aaaaaaaaaaaa",
                "云南锡业股份有限公司",
                rule_name="company_fragment",
                context="长上下文" * 20,
            ),
            _candidate(
                "doc-getm-1:csg:bbbbbbbbbbbb",
                "18,394,427股",
                rule_name="share_quantity",
            ),
            _candidate("doc-getm-1:csg:cccccccccccc", "1.102%", rule_name="percentage"),
        ],
        slot_plan=None,
        candidate_render_mode="compact",
        candidate_context_chars=0,
        enable_candidate_filtering=True,
        max_surface_candidates=20,
    )

    assert "[c0] 18,394,427股" in prompt
    assert "[c1] 1.102%" in prompt
    assert "[c2] 云南锡业股份有限公司" in prompt
    assert "doc-getm-1:csg:" not in prompt
    assert "chunk_" not in prompt
    assert "context=" not in prompt
    assert "source_candidate_id" not in prompt


def test_compact_candidate_render_honors_max_items_context_and_dedupe() -> None:
    prompt = build_getm_prompt(
        dataset="unit",
        schema=_schema(),
        document=_document(),
        surface_candidates=[
            _candidate("doc-getm-1:csg:000000000001", "18,394,427股", rule_name="share_quantity"),
            _candidate(
                "doc-getm-1:csg:000000000002",
                "18,394,427股",
                rule_name="share_quantity",
                context="duplicate should be removed",
            ),
            _candidate(
                "doc-getm-1:csg:000000000003",
                "云南锡业股份有限公司",
                rule_name="company_fragment",
                context="上下文保留最多六个字",
            ),
        ],
        slot_plan=None,
        max_surface_candidates=2,
        candidate_render_mode="compact",
        candidate_context_chars=6,
        enable_candidate_filtering=True,
        dedupe_surface_candidates=True,
    )

    assert prompt.count("[c") == 2
    assert prompt.count("18,394,427股") == 1
    assert "[c1] 云南锡业股份有限公司 | ctx=上下文保留最" in prompt
    assert "duplicate should be removed" not in prompt


def test_candidate_filtering_drops_low_value_company_fragments_and_caps_types() -> None:
    prompt = build_getm_prompt(
        dataset="unit",
        schema=_schema(),
        document=_document(),
        surface_candidates=[
            _candidate("doc-getm-1:csg:000000000001", "本公司", rule_name="company_fragment"),
            _candidate("doc-getm-1:csg:000000000002", "公司", rule_name="company_fragment"),
            _candidate("doc-getm-1:csg:000000000003", "1.102%", rule_name="percentage"),
            _candidate("doc-getm-1:csg:000000000004", "2.204%", rule_name="percentage"),
            _candidate("doc-getm-1:csg:000000000005", "3.306%", rule_name="percentage"),
            _candidate("doc-getm-1:csg:000000000006", "191,821,211.70元", rule_name="money"),
        ],
        slot_plan=None,
        max_surface_candidates=20,
        candidate_render_mode="compact",
        enable_candidate_filtering=True,
        max_candidates_per_type=2,
        drop_low_value_company_fragments=True,
    )

    assert "本公司" not in prompt
    assert "公司" not in prompt
    assert "191,821,211.70元" in prompt
    assert "1.102%" in prompt
    assert "2.204%" in prompt
    assert "3.306%" not in prompt


def test_compact_candidate_filtering_demotes_generic_institutions() -> None:
    prompt = build_getm_prompt(
        dataset="unit",
        schema=_schema(),
        document=_document(),
        surface_candidates=[
            _candidate(
                "doc-getm-1:csg:000000000001",
                "深圳证券交易所上市公司回购股份实施细则",
                rule_name="quoted_entity",
            ),
            _candidate("doc-getm-1:csg:000000000002", "1.102%", rule_name="percentage"),
            _candidate("doc-getm-1:csg:000000000003", "云南锡业股份有限公司", rule_name="company_fragment"),
        ],
        slot_plan=None,
        max_surface_candidates=2,
        candidate_render_mode="compact",
        enable_candidate_filtering=True,
    )

    assert "1.102%" in prompt
    assert "云南锡业股份有限公司" in prompt
    assert "深圳证券交易所上市公司回购股份实施细则" not in prompt


def test_zero_max_surface_candidates_renders_none() -> None:
    prompt = build_getm_prompt(
        dataset="unit",
        schema=_schema(),
        document=_document(),
        surface_candidates=[_candidate("doc-getm-1:csg:000000000001", "1.102%", rule_name="percentage")],
        slot_plan=None,
        max_surface_candidates=0,
        candidate_render_mode="compact",
    )

    surface_section = prompt.split("[Surface Candidates]", maxsplit=1)[1].split("[Event Slot Plan]", maxsplit=1)[0]
    assert "(none)" in surface_section
    assert "1.102%" not in surface_section


def test_prompt_rejects_gold_visible_document_payloads() -> None:
    with pytest.raises(ValueError, match="forbidden prompt key"):
        build_getm_prompt(
            dataset="unit",
            schema=_schema(),
            document={
                "doc_id": "doc-getm-2",
                "content": "safe visible text",
                "events": [{"event_type": "EventA", "arguments": {"Role1": [{"text": "gold-only"}]}}],
            },
            surface_candidates=[],
            slot_plan=None,
        )


def _candidate(
    candidate_id: str,
    surface: str,
    *,
    rule_name: str,
    context: str = "context around candidate",
) -> SurfaceCandidate:
    return SurfaceCandidate(
        candidate_id=candidate_id,
        doc_id="doc-getm-1",
        surface=surface,
        context=context,
        chunk_id="chunk_0001",
        metadata={"rule_names": [rule_name]},
    )
