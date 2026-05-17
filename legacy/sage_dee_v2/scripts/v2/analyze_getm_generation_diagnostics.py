from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))

from sage_dee.io_utils import read_yaml  # noqa: E402
from sage_dee.v2.data_interface.jsonl import read_jsonl, write_jsonl  # noqa: E402
from sage_dee.v2.getm.generation_diagnostics import (  # noqa: E402
    DIAGNOSTIC_VERSION,
    aggregate_parse_diagnostics,
    build_generation_diagnostics,
    generation_diagnostic_fields,
)
from sage_dee.v2.pipeline.export_canonical import validate_minimal_canonical_prediction  # noqa: E402

FORBIDDEN_CANONICAL_KEYS = frozenset(
    {
        "gold",
        "events_gold",
        "norm_text",
        "slot_id",
        "source_candidate_id",
        "evidence_chunk_id",
        "alignment_score",
        "logprob",
        "reward",
        "mrs_score",
        "content",
        "content_raw",
        "dataset",
        "split",
    }
)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    raw_rows = read_jsonl(args.raw_outputs)
    prompt_rows = read_jsonl(args.prompts)
    parsed_rows = read_jsonl(args.parsed_candidates)
    generation_manifest = _read_json(args.generation_manifest)
    config = read_yaml(args.config_resolved) if args.config_resolved else {}
    generation_metadata = _generation_metadata(generation_manifest=generation_manifest, config=config)
    tokenizer = _load_tokenizer(args.tokenizer_path)

    prompts_by_doc_id = _index_by_key(prompt_rows, "doc_id")
    parsed_by_candidate_id = _index_by_key(parsed_rows, "candidate_id")
    enhanced_raw_rows: list[dict[str, Any]] = []
    enhanced_parsed_rows: list[dict[str, Any]] = []
    generation_diagnostic_rows: list[dict[str, Any]] = []

    for raw_row in raw_rows:
        candidate_id = str(raw_row.get("candidate_id") or "").strip()
        if not candidate_id:
            raise ValueError("raw output row missing candidate_id")
        doc_id = str(raw_row.get("doc_id") or "").strip()
        parsed_row = dict(parsed_by_candidate_id.get(candidate_id) or {})
        if not parsed_row:
            raise ValueError(f"parsed candidate row missing for {candidate_id}")
        prompt_row = prompts_by_doc_id.get(doc_id) or {}
        raw_output = str(raw_row.get("raw_output") or "")
        diagnostic_output = str(raw_row.get("stopped_output") or raw_output)
        prompt = str(prompt_row.get("prompt") or "")
        surface_candidate_count = _surface_candidate_count(prompt_row)
        token_metadata = _token_metadata(
            raw_row=raw_row,
            prompt_row=prompt_row,
            prompt=prompt,
            raw_output=diagnostic_output,
            tokenizer=tokenizer,
            generation_metadata=generation_metadata,
            config=config,
        )
        diagnostics = build_generation_diagnostics(
            raw_output=raw_output,
            prompt=prompt,
            surface_candidate_count=surface_candidate_count,
            max_new_tokens=_optional_int(generation_metadata.get("max_new_tokens")),
            prompt_token_count=_optional_int(token_metadata.get("prompt_token_count")),
            prompt_token_count_source=_optional_str(token_metadata.get("prompt_token_count_source")),
            prompt_token_budget=_optional_int(token_metadata.get("prompt_token_budget")),
            prompt_section_char_counts=_optional_int_mapping(token_metadata.get("prompt_section_char_counts")),
            prompt_section_token_counts=_optional_int_mapping(token_metadata.get("prompt_section_token_counts")),
            generated_token_count=_optional_int(token_metadata.get("generated_token_count")),
            generated_token_count_source=_optional_str(token_metadata.get("generated_token_count_source")),
            hit_max_new_tokens=_optional_bool(token_metadata.get("hit_max_new_tokens")),
            hit_max_new_tokens_source=_optional_str(token_metadata.get("hit_max_new_tokens_source")),
            ended_with_eos=_optional_bool(token_metadata.get("ended_with_eos")),
            ended_with_eos_source=_optional_str(token_metadata.get("ended_with_eos_source")),
            ended_with_eos_reason=_optional_str(token_metadata.get("ended_with_eos_reason")),
            include_parse_error_subtypes=str(parsed_row.get("parse_status") or "") == "parse_error",
        )
        diagnostic_fields = generation_diagnostic_fields(diagnostics)
        enhanced_raw_rows.append({**raw_row, **diagnostic_fields})
        existing_diagnostics = parsed_row.get("diagnostics") or {}
        if not isinstance(existing_diagnostics, dict):
            existing_diagnostics = {}
        parsed_row["diagnostics"] = {**existing_diagnostics, **diagnostics}
        enhanced_parsed_rows.append(parsed_row)
        generation_diagnostic_rows.append(
            {
                "candidate_id": candidate_id,
                "doc_id": doc_id,
                "parse_status": parsed_row.get("parse_status"),
                **diagnostic_fields,
            }
        )

    args.out_dir.mkdir(parents=True, exist_ok=True)
    raw_path = write_jsonl(args.out_dir / f"raw_outputs.{args.split}.enhanced.jsonl", enhanced_raw_rows)
    parsed_path = write_jsonl(args.out_dir / f"parsed_candidates.{args.split}.enhanced.jsonl", enhanced_parsed_rows)
    generation_diagnostics_path = write_jsonl(
        args.out_dir / f"generation_diagnostics.{args.split}.jsonl",
        generation_diagnostic_rows,
    )
    diagnostics_path = _write_json(
        args.out_dir / f"parse_diagnostics.{args.split}.json",
        aggregate_parse_diagnostics(
            enhanced_parsed_rows,
            dataset=args.dataset,
            split=args.split,
            k=_optional_int(generation_manifest.get("k")),
            generation_metadata=generation_metadata,
        ),
    )
    validation_path = _write_json(
        args.out_dir / "validation_summary.json",
        _validation_summary(prediction_path=args.canonical_predictions, dataset=args.dataset, split=args.split),
    )

    print(f"enhanced_raw_outputs={raw_path}")
    print(f"enhanced_parsed_candidates={parsed_path}")
    print(f"generation_diagnostics={generation_diagnostics_path}")
    print(f"parse_diagnostics={diagnostics_path}")
    print(f"validation_summary={validation_path}")
    return 0


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Enhance existing GETM generation artifacts with P0 diagnostics.")
    parser.add_argument("--raw-outputs", type=Path, required=True)
    parser.add_argument("--prompts", type=Path, required=True)
    parser.add_argument("--parsed-candidates", type=Path, required=True)
    parser.add_argument("--generation-manifest", type=Path, required=True)
    parser.add_argument("--config-resolved", type=Path)
    parser.add_argument("--tokenizer-path", type=Path)
    parser.add_argument("--canonical-predictions", type=Path, required=True)
    parser.add_argument("--dataset", required=True)
    parser.add_argument("--split", required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    return parser.parse_args(argv)


def _read_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError(f"JSON file must contain a mapping: {path}")
    return payload


def _write_json(path: Path, payload: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
    return path


def _index_by_key(rows: list[dict[str, Any]], key: str) -> dict[str, dict[str, Any]]:
    indexed: dict[str, dict[str, Any]] = {}
    for row in rows:
        value = str(row.get(key) or "").strip()
        if value:
            indexed[value] = row
    return indexed


def _generation_metadata(*, generation_manifest: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
    generation = dict(generation_manifest.get("generation") or {})
    getm = config.get("getm") or {}
    if "output_format" in getm:
        generation["output_format"] = getm["output_format"]
    generation.update({key: value for key, value in (getm.get("prompt") or {}).items()})
    generation.update({key: value for key, value in ((config.get("getm") or {}).get("generation") or {}).items()})
    generation.update({key: value for key, value in (generation_manifest.get("generation") or {}).items()})
    generation["diagnostic_version"] = DIAGNOSTIC_VERSION
    return generation


def _load_tokenizer(tokenizer_path: Path | None) -> Any | None:
    if tokenizer_path is None:
        return None
    transformers = __import__("transformers")
    return transformers.AutoTokenizer.from_pretrained(str(tokenizer_path), trust_remote_code=True)


def _surface_candidate_count(prompt_row: dict[str, Any]) -> int | None:
    prompt_candidates = prompt_row.get("prompt_surface_candidates")
    if isinstance(prompt_candidates, list):
        return len(prompt_candidates)
    candidates = prompt_row.get("surface_candidates")
    return len(candidates) if isinstance(candidates, list) else None


def _prompt_metadata(*, prompt_row: dict[str, Any], prompt: str) -> dict[str, Any]:
    prompt_sections = _prompt_sections(prompt)
    raw_metadata = prompt_row.get("prompt_metadata") or {}
    if not isinstance(raw_metadata, dict):
        raw_metadata = {}
    char_counts = raw_metadata.get("prompt_section_char_counts")
    if not isinstance(char_counts, dict):
        char_counts = {section: len(text) for section, text in prompt_sections.items()}
    parsed_char_counts: dict[str, int] = {}
    for section, count in char_counts.items():
        parsed = _optional_int(count)
        if parsed is not None:
            parsed_char_counts[str(section)] = parsed
    return {
        "prompt_sections": prompt_sections,
        "prompt_section_char_counts": parsed_char_counts,
    }


def _prompt_sections(prompt: str) -> dict[str, str]:
    markers = (
        ("schema", "[Schema]"),
        ("document", "[Document]"),
        ("candidates", "[Surface Candidates]"),
        ("slot_plan", "[Event Slot Plan]"),
        ("instruction", "[Instruction]"),
    )
    positions = [(name, marker, prompt.find(marker)) for name, marker in markers]
    found = [(name, marker, position) for name, marker, position in positions if position >= 0]
    sections: dict[str, str] = {}
    for index, (name, marker, position) in enumerate(found):
        start = position + len(marker)
        end = found[index + 1][2] if index + 1 < len(found) else len(prompt)
        sections[name] = prompt[start:end].strip()
    return sections


def _prompt_section_token_counts(*, tokenizer: Any, sections: dict[str, str]) -> dict[str, int]:
    return {
        section: _input_id_count(tokenizer(text, add_special_tokens=False)["input_ids"])
        for section, text in sections.items()
    }


def _token_metadata(
    *,
    raw_row: dict[str, Any],
    prompt_row: dict[str, Any],
    prompt: str,
    raw_output: str,
    tokenizer: Any | None,
    generation_metadata: dict[str, Any],
    config: dict[str, Any],
) -> dict[str, Any]:
    metadata = {
        "prompt_token_count": raw_row.get("prompt_token_count"),
        "prompt_token_count_source": raw_row.get("prompt_token_count_source"),
        "prompt_token_budget": raw_row.get("prompt_token_budget"),
        "prompt_section_char_counts": raw_row.get("prompt_section_char_counts"),
        "prompt_section_token_counts": raw_row.get("prompt_section_token_counts"),
        "generated_token_count": raw_row.get("generated_token_count"),
        "generated_token_count_source": raw_row.get("generated_token_count_source"),
        "hit_max_new_tokens": raw_row.get("hit_max_new_tokens"),
        "hit_max_new_tokens_source": raw_row.get("hit_max_new_tokens_source"),
        "ended_with_eos": raw_row.get("ended_with_eos"),
        "ended_with_eos_source": raw_row.get("ended_with_eos_source"),
        "ended_with_eos_reason": raw_row.get("ended_with_eos_reason"),
    }
    prompt_metadata = _prompt_metadata(prompt_row=prompt_row, prompt=prompt)
    if metadata["prompt_token_budget"] is None:
        metadata["prompt_token_budget"] = generation_metadata.get("prompt_token_budget") or _max_seq_len(config)
    if not isinstance(metadata["prompt_section_char_counts"], dict):
        metadata["prompt_section_char_counts"] = prompt_metadata["prompt_section_char_counts"]
    if tokenizer is not None:
        if metadata["prompt_token_count"] is None:
            metadata["prompt_token_count"] = _input_id_count(
                _tokenize_prompt_for_diagnostics(
                    tokenizer=tokenizer,
                    prompt=prompt,
                    generation_metadata=generation_metadata,
                    max_seq_len=_max_seq_len(config),
                )
            )
            metadata["prompt_token_count_source"] = "generation_prompt_retokenized_approx"
        if metadata["generated_token_count"] is None:
            metadata["generated_token_count"] = _input_id_count(
                tokenizer(raw_output, add_special_tokens=False)["input_ids"]
            )
            metadata["generated_token_count_source"] = "retokenized_raw_output_approx"
        if not isinstance(metadata["prompt_section_token_counts"], dict) or not metadata["prompt_section_token_counts"]:
            metadata["prompt_section_token_counts"] = _prompt_section_token_counts(
                tokenizer=tokenizer,
                sections=prompt_metadata["prompt_sections"],
            )
    if metadata["ended_with_eos"] is None:
        metadata["ended_with_eos_reason"] = (
            "decoded raw_output was persisted with skip_special_tokens=True; EOS/finish_reason cannot be reconstructed"
        )
    return metadata


def _tokenize_prompt_for_diagnostics(
    *,
    tokenizer: Any,
    prompt: str,
    generation_metadata: dict[str, Any],
    max_seq_len: int,
) -> Any:
    use_chat_template = bool(generation_metadata.get("use_chat_template", True))
    use_response_prefix = bool(generation_metadata.get("use_response_prefix", True))
    response_prefix = str(generation_metadata.get("response_prefix") or '{"events":')
    if use_chat_template and hasattr(tokenizer, "apply_chat_template"):
        if use_response_prefix:
            messages = [
                {"role": "user", "content": prompt},
                {"role": "assistant", "content": response_prefix},
            ]
            return tokenizer.apply_chat_template(
                messages,
                tokenize=True,
                continue_final_message=True,
                truncation=True,
                max_length=max_seq_len,
            )
        return tokenizer.apply_chat_template(
            [{"role": "user", "content": prompt}],
            tokenize=True,
            add_generation_prompt=True,
            truncation=True,
            max_length=max_seq_len,
        )
    fallback_prompt = f"{prompt}\n{response_prefix}" if use_response_prefix else prompt
    return tokenizer(
        fallback_prompt,
        add_special_tokens=True,
        truncation=True,
        max_length=max_seq_len,
    )["input_ids"]


def _max_seq_len(config: dict[str, Any]) -> int:
    qwen = (config.get("getm") or {}).get("qwen") or {}
    training = qwen.get("training") or {}
    budget = config.get("training_budget") or {}
    return int(training.get("max_seq_len", budget.get("max_seq_len", 4096)))


def _input_id_count(input_ids: Any) -> int:
    if hasattr(input_ids, "get"):
        nested_input_ids = input_ids.get("input_ids")
        if nested_input_ids is not None and nested_input_ids is not input_ids:
            return _input_id_count(nested_input_ids)
    if hasattr(input_ids, "shape"):
        shape = tuple(input_ids.shape)
        return int(shape[-1]) if shape else 0
    if isinstance(input_ids, list) and input_ids and isinstance(input_ids[0], list):
        return len(input_ids[0])
    return len(input_ids or [])


def _validation_summary(*, prediction_path: Path, dataset: str, split: str) -> dict[str, Any]:
    rows = read_jsonl(prediction_path)
    forbidden_violations: list[dict[str, Any]] = []
    schema_errors: list[dict[str, Any]] = []
    missing_doc_id_or_events: list[int] = []
    for row_index, row in enumerate(rows, 1):
        if not row.get("doc_id") or "events" not in row:
            missing_doc_id_or_events.append(row_index)
        for key_path in _forbidden_key_paths(row):
            forbidden_violations.append({"row": row_index, "key_path": key_path})
        try:
            validate_minimal_canonical_prediction(row)
        except ValueError as exc:
            schema_errors.append({"row": row_index, "error": str(exc)})
    return {
        "created_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "diagnostic_version": DIAGNOSTIC_VERSION,
        "dataset": dataset,
        "split": split,
        "prediction_path": str(prediction_path),
        "row_count": len(rows),
        "rows_with_doc_id_and_events": len(rows) - len(missing_doc_id_or_events),
        "missing_doc_id_or_events": missing_doc_id_or_events,
        "forbidden_keys": sorted(FORBIDDEN_CANONICAL_KEYS),
        "forbidden_key_violation_count": len(forbidden_violations),
        "forbidden_key_violations": forbidden_violations,
        "project_canonical_schema_error_count": len(schema_errors),
        "project_canonical_schema_errors": schema_errors,
        "offline_diagnostics_only": True,
        "gold_visible": False,
    }


def _forbidden_key_paths(value: Any, *, prefix: str = "") -> list[str]:
    paths: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            key_path = f"{prefix}.{key}" if prefix else str(key)
            if key in FORBIDDEN_CANONICAL_KEYS:
                paths.append(key_path)
            paths.extend(_forbidden_key_paths(child, prefix=key_path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            key_path = f"{prefix}[{index}]" if prefix else f"[{index}]"
            paths.extend(_forbidden_key_paths(child, prefix=key_path))
    return paths


def _optional_int(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _optional_bool(value: Any) -> bool | None:
    return value if isinstance(value, bool) else None


def _optional_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _optional_int_mapping(value: Any) -> dict[str, int] | None:
    if not isinstance(value, dict):
        return None
    mapping: dict[str, int] = {}
    for key, raw_value in value.items():
        parsed = _optional_int(raw_value)
        if parsed is not None:
            mapping[str(key)] = parsed
    return mapping or None


if __name__ == "__main__":
    raise SystemExit(main())
