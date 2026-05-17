from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from sage_dee.v2.contracts.surface import SurfaceMemory
from sage_dee.v2.csg.surface_memory import build_surface_memory, surface_candidate_to_dict
from sage_dee.v2.data_interface.dataset_loader import V2DatasetDocument
from sage_dee.v2.data_interface.jsonl import write_jsonl
from sage_dee.v2.data_interface.schema_registry import DatasetSchema
from sage_dee.v2.getm.generation_diagnostics import (
    aggregate_parse_diagnostics,
    generation_diagnostic_fields,
)
from sage_dee.v2.getm.parser import (
    candidate_set_to_canonical_prediction,
    candidate_set_to_dict,
    parse_getm_output,
)
from sage_dee.v2.getm.prompt_builder import build_getm_prompt_result
from sage_dee.v2.lesp.slot_plan import SlotPlanDocument
from sage_dee.v2.pipeline.export_canonical import export_predictions


@dataclass(frozen=True)
class GetmCandidateGenerationOutput:
    prompts_path: Path
    raw_outputs_path: Path
    parsed_candidates_path: Path
    parse_diagnostics_path: Path
    canonical_predictions_path: Path


def generate_getm_candidate_files(
    *,
    documents: list[V2DatasetDocument],
    dataset: str,
    split: str,
    schema: DatasetSchema,
    backend: Any,
    k: int,
    out_dir: str | Path,
    surface_memories: dict[str, SurfaceMemory] | None = None,
    slot_plans: dict[str, SlotPlanDocument] | None = None,
) -> GetmCandidateGenerationOutput:
    if k < 1:
        raise ValueError("k must be >= 1")
    output_dir = Path(out_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    prompts: list[dict[str, Any]] = []
    raw_rows: list[dict[str, Any]] = []
    parsed_rows: list[dict[str, Any]] = []
    first_candidates = []
    parse_options = _backend_parse_options(backend)
    backend_generation_metadata = _backend_generation_metadata(backend)
    prompt_options = _backend_prompt_options(backend_generation_metadata)

    for document in documents:
        if document.gold is not None:
            raise ValueError("GETM candidate generation documents must not expose gold")
        memory = _surface_memory_for_doc(document, surface_memories)
        slot_plan = _slot_plan_for_doc(document, schema, slot_plans)
        surface_candidates = list(memory.candidates)
        prompt_result = build_getm_prompt_result(
            dataset=dataset,
            schema=schema,
            document=document.input,
            surface_candidates=surface_candidates,
            slot_plan=slot_plan,
            **prompt_options,
        )
        prompt = prompt_result.prompt
        prompts.append(
            {
                "doc_id": document.doc_id,
                "dataset": dataset,
                "split": split,
                "prompt": prompt,
                "surface_candidates": [surface_candidate_to_dict(candidate) for candidate in surface_candidates],
                "prompt_surface_candidates": list(prompt_result.selected_surface_candidates),
                "prompt_metadata": dict(prompt_result.prompt_metadata),
            }
        )

        for candidate_index in range(k):
            candidate_id = f"{document.doc_id}:getm:{candidate_index}"
            generated_output = backend.generate_one(
                prompt=prompt,
                document=document.input,
                schema=schema,
                surface_candidates=surface_candidates,
                slot_plan=slot_plan,
                candidate_index=candidate_index,
            )
            token_metadata = _backend_last_generation_metadata(backend)
            raw_output = str(token_metadata.get("raw_output", generated_output))
            stopped_output = str(token_metadata.get("stopped_output", generated_output))
            backend_generation_metadata = _backend_generation_metadata(backend)
            generation_metadata = {**backend_generation_metadata, **prompt_result.prompt_metadata}
            parsed = parse_getm_output(
                stopped_output,
                doc_id=document.doc_id,
                candidate_id=candidate_id,
                schema=schema,
                prompt=prompt,
                surface_candidate_count=len(prompt_result.selected_surface_candidates),
                generation_metadata=generation_metadata,
                token_metadata=token_metadata,
                **parse_options,
            )
            parsed_row = candidate_set_to_dict(parsed)
            raw_rows.append(
                {
                    "candidate_id": candidate_id,
                    "doc_id": document.doc_id,
                    "candidate_index": candidate_index,
                    "backend": type(backend).__name__,
                    "raw_output": raw_output,
                    "stopped_output": stopped_output,
                    "stop_reason": token_metadata.get("stop_reason"),
                    "balanced_stop_applied": token_metadata.get("balanced_stop_applied"),
                    **generation_diagnostic_fields(parsed_row["diagnostics"]),
                }
            )
            parsed_rows.append(parsed_row)
            if candidate_index == 0:
                first_candidates.append(parsed)

    prompts_path = write_jsonl(output_dir / f"prompts.{split}.jsonl", prompts)
    raw_outputs_path = write_jsonl(output_dir / f"raw_outputs.{split}.jsonl", raw_rows)
    parsed_candidates_path = write_jsonl(output_dir / f"parsed_candidates.{split}.jsonl", parsed_rows)
    generation_metadata = _backend_generation_metadata(backend)
    diagnostics = aggregate_parse_diagnostics(
        parsed_rows,
        dataset=dataset,
        split=split,
        k=k,
        generation_metadata=generation_metadata,
    )
    parse_diagnostics_path = output_dir / f"parse_diagnostics.{split}.json"
    with parse_diagnostics_path.open("w", encoding="utf-8") as handle:
        json.dump(diagnostics, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")

    canonical_predictions_path = output_dir / "predictions" / dataset / f"{split}.canonical.pred.jsonl"
    export_predictions(
        [candidate_set_to_canonical_prediction(candidate, schema=schema) for candidate in first_candidates],
        canonical_predictions_path,
        schema=schema,
    )
    return GetmCandidateGenerationOutput(
        prompts_path=prompts_path,
        raw_outputs_path=raw_outputs_path,
        parsed_candidates_path=parsed_candidates_path,
        parse_diagnostics_path=parse_diagnostics_path,
        canonical_predictions_path=canonical_predictions_path,
    )



def _backend_parse_options(backend: Any) -> dict[str, Any]:
    options = getattr(backend, "parse_options", None)
    if callable(options):
        options = options()
    if isinstance(options, dict):
        return dict(options)
    return {}


def _backend_generation_metadata(backend: Any) -> dict[str, Any]:
    metadata = getattr(backend, "generation_metadata", None)
    if callable(metadata):
        metadata = metadata()
    if isinstance(metadata, dict):
        return dict(metadata)
    return {}


def _backend_prompt_options(generation_metadata: dict[str, Any]) -> dict[str, Any]:
    use_response_prefix = bool(
        generation_metadata.get("use_response_prefix", generation_metadata.get("response_prefix_used", False))
    )
    options: dict[str, Any] = {
        "use_response_prefix": use_response_prefix,
        "response_prefix": str(generation_metadata.get("response_prefix") or ""),
        "prompt_delimiter": str(generation_metadata.get("prompt_delimiter") or "### RESPONSE_JSON"),
        "output_format": str(generation_metadata.get("output_format") or "minimal_text"),
    }
    for key in (
        "max_surface_candidates",
        "candidate_context_chars",
        "candidate_render_mode",
        "enable_candidate_filtering",
        "max_candidates_per_type",
        "dedupe_surface_candidates",
        "drop_low_value_company_fragments",
        "baseline_mode",
    ):
        if key in generation_metadata:
            options[key] = generation_metadata[key]
    return options


def _backend_last_generation_metadata(backend: Any) -> dict[str, Any]:
    metadata = getattr(backend, "last_generation_metadata", None)
    if callable(metadata):
        metadata = metadata()
    if isinstance(metadata, dict):
        return dict(metadata)
    return {}


def _surface_memory_for_doc(
    document: V2DatasetDocument,
    surface_memories: dict[str, SurfaceMemory] | None,
) -> SurfaceMemory:
    if surface_memories and document.doc_id in surface_memories:
        return surface_memories[document.doc_id]
    return build_surface_memory(document.input)


def _slot_plan_for_doc(
    document: V2DatasetDocument,
    schema: DatasetSchema,
    slot_plans: dict[str, SlotPlanDocument] | None,
) -> SlotPlanDocument:
    if slot_plans and document.doc_id in slot_plans:
        return slot_plans[document.doc_id]
    return SlotPlanDocument(doc_id=document.doc_id, dataset=schema.dataset_id, slots=[])
