from __future__ import annotations

from pathlib import Path

import pytest

from sage_dee.v2.contracts.surface import SurfaceCandidate, SurfaceMemory
from sage_dee.v2.data_interface.dataset_loader import V2DatasetDocument, V2DocumentInput, V2GoldDocument
from sage_dee.v2.data_interface.jsonl import read_jsonl
from sage_dee.v2.data_interface.schema_registry import DatasetSchema
from sage_dee.v2.getm.candidate_generator import generate_getm_candidate_files
from sage_dee.v2.getm.mock_backend import MockGetmBackend
from sage_dee.v2.lesp.slot_plan import EventSlot, SlotPlanDocument
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
        input=V2DocumentInput(
            doc_id="doc-gen-1",
            dataset_id="unit",
            dataset="unit-source",
            split="dev",
            content="The document contains value-one.",
        ),
        gold=None,
    )


def test_mock_k4_generation_writes_candidate_and_canonical_files(tmp_path: Path) -> None:
    output = generate_getm_candidate_files(
        documents=[_predict_document()],
        dataset="unit",
        split="dev",
        schema=_schema(),
        backend=MockGetmBackend(mode="echo_candidates"),
        k=4,
        out_dir=tmp_path,
        surface_memories={
            "doc-gen-1": SurfaceMemory(
                doc_id="doc-gen-1",
                candidates=[
                    SurfaceCandidate(
                        candidate_id="cand-1",
                        doc_id="doc-gen-1",
                        surface="value-one",
                        context="contains value-one",
                        chunk_id="chunk-0000",
                    )
                ],
            )
        },
        slot_plans={
            "doc-gen-1": SlotPlanDocument(
                doc_id="doc-gen-1",
                dataset="unit",
                slots=[
                    EventSlot(
                        event_type="EventA",
                        slot_id=0,
                        count_confidence=0.9,
                        role_prior={"Role1": 1.0},
                        supporting_candidates=["cand-1"],
                    )
                ],
            )
        },
    )

    assert output.raw_outputs_path.is_file()
    assert output.parsed_candidates_path.is_file()
    assert output.parse_diagnostics_path.is_file()
    assert output.canonical_predictions_path.is_file()
    assert len(read_jsonl(output.raw_outputs_path)) == 4
    assert len(read_jsonl(output.parsed_candidates_path)) == 4
    canonical_rows = read_jsonl(output.canonical_predictions_path)
    assert canonical_rows == [
        {
            "doc_id": "doc-gen-1",
            "events": [{"event_type": "EventA", "arguments": {"Role1": [{"text": "value-one"}]}}],
        }
    ]
    validate_minimal_canonical_prediction(canonical_rows[0])


def test_candidate_generator_rejects_gold_visible_documents(tmp_path: Path) -> None:
    document = _predict_document()
    gold_document = V2DatasetDocument(
        input=document.input,
        gold=V2GoldDocument(
            doc_id=document.doc_id,
            dataset_id="unit",
            dataset="unit-source",
            split="dev",
            events=[{"event_type": "EventA", "arguments": {"Role1": [{"text": "gold"}]}}],
        ),
    )

    with pytest.raises(ValueError, match="must not expose gold"):
        generate_getm_candidate_files(
            documents=[gold_document],
            dataset="unit",
            split="dev",
            schema=_schema(),
            backend=MockGetmBackend(mode="empty"),
            k=1,
            out_dir=tmp_path,
        )


def test_candidate_generator_persists_compact_prompt_candidate_metadata(tmp_path: Path) -> None:
    output = generate_getm_candidate_files(
        documents=[_predict_document()],
        dataset="unit",
        split="dev",
        schema=_schema(),
        backend=_CompactPromptBackend(),
        k=1,
        out_dir=tmp_path,
        surface_memories={
            "doc-gen-1": SurfaceMemory(
                doc_id="doc-gen-1",
                candidates=[
                    SurfaceCandidate(
                        candidate_id="doc-gen-1:csg:000000000001",
                        doc_id="doc-gen-1",
                        surface="1.102%",
                        context="context should not render",
                        chunk_id="chunk_0000",
                        metadata={"rule_names": ["percentage"]},
                    ),
                    SurfaceCandidate(
                        candidate_id="doc-gen-1:csg:000000000002",
                        doc_id="doc-gen-1",
                        surface="2.204%",
                        context="context should not render",
                        chunk_id="chunk_0000",
                        metadata={"rule_names": ["percentage"]},
                    ),
                ],
            )
        },
    )

    prompt_row = read_jsonl(output.prompts_path)[0]
    assert "[c0] 1.102%" in prompt_row["prompt"]
    assert "doc-gen-1:csg:" not in prompt_row["prompt"]
    assert "chunk_0000" not in prompt_row["prompt"]
    assert "context should not render" not in prompt_row["prompt"]
    assert len(prompt_row["prompt_surface_candidates"]) == 1
    assert prompt_row["prompt_metadata"]["selected_surface_candidate_count"] == 1
    parsed_row = read_jsonl(output.parsed_candidates_path)[0]
    assert parsed_row["diagnostics"]["surface_candidate_count"] == 1


class _CompactPromptBackend:
    @property
    def generation_metadata(self) -> dict[str, object]:
        return {
            "output_format": "minimal_text",
            "candidate_render_mode": "compact",
            "candidate_context_chars": 0,
            "max_surface_candidates": 1,
            "enable_candidate_filtering": True,
            "dedupe_surface_candidates": True,
            "drop_low_value_company_fragments": True,
            "prompt_token_budget": 4096,
        }

    @property
    def parse_options(self) -> dict[str, object]:
        return {"output_format": "minimal_text"}

    def generate_one(
        self,
        *,
        prompt: str,
        document: object,
        schema: object,
        surface_candidates: list[SurfaceCandidate],
        slot_plan: object,
        candidate_index: int,
    ) -> str:
        del prompt, document, schema, surface_candidates, slot_plan, candidate_index
        return '{"events":[]}'
