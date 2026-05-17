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

from sage_dee.v2.data_interface.jsonl import read_jsonl, write_jsonl  # noqa: E402
from sage_dee.v2.data_interface.schema_registry import DatasetSchema  # noqa: E402
from sage_dee.v2.getm.generation_diagnostics import aggregate_parse_diagnostics  # noqa: E402
from sage_dee.v2.getm.parser import (  # noqa: E402
    candidate_set_to_canonical_prediction,
    candidate_set_to_dict,
    parse_getm_output,
)
from sage_dee.v2.pipeline.export_canonical import (  # noqa: E402
    export_predictions,
    validate_minimal_canonical_prediction,
)

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
    schema = load_schema_file(args.dataset, args.schema)
    raw_rows = read_jsonl(args.raw_outputs)
    args.out_dir.mkdir(parents=True, exist_ok=True)

    parsed_rows: list[dict[str, Any]] = []
    first_candidates: dict[str, Any] = {}
    for row_number, row in enumerate(raw_rows):
        doc_id = str(row.get("doc_id") or "").strip()
        if not doc_id:
            raise ValueError(f"raw output row {row_number + 1} missing doc_id")
        candidate_id = str(row.get("candidate_id") or f"{doc_id}:getm:{row_number}").strip()
        raw_output = str(row.get("raw_output") or "")
        candidate = parse_getm_output(
            raw_output,
            doc_id=doc_id,
            candidate_id=candidate_id,
            schema=schema,
            token_metadata=row,
            output_format=args.output_format,
        )
        parsed_rows.append(candidate_set_to_dict(candidate))
        if _is_first_candidate(row) and doc_id not in first_candidates:
            first_candidates[doc_id] = candidate
        elif doc_id not in first_candidates:
            first_candidates[doc_id] = candidate

    parsed_path = write_jsonl(args.out_dir / f"parsed_candidates.{args.split}.jsonl", parsed_rows)
    diagnostics_path = args.out_dir / f"parse_diagnostics.{args.split}.json"
    _write_json(
        diagnostics_path,
        aggregate_parse_diagnostics(parsed_rows, dataset=args.dataset, split=args.split, k=None),
    )
    prediction_path = args.out_dir / "predictions" / args.dataset / f"{args.split}.canonical.pred.jsonl"
    export_predictions(
        [
            candidate_set_to_canonical_prediction(candidate, schema=schema)
            for candidate in first_candidates.values()
        ],
        prediction_path,
        schema=schema,
    )
    validation_path = args.out_dir / "validation_summary.json"
    _write_json(
        validation_path,
        _validation_summary(
            prediction_path=prediction_path,
            dataset=args.dataset,
            split=args.split,
            schema=schema,
        ),
    )

    print(f"parsed_candidates={parsed_path}")
    print(f"parse_diagnostics={diagnostics_path}")
    print(f"canonical_predictions={prediction_path}")
    print(f"validation_summary={validation_path}")
    return 0


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Offline reparse existing GETM raw outputs without model generation.")
    parser.add_argument("--raw-outputs", type=Path, required=True)
    parser.add_argument("--dataset", required=True)
    parser.add_argument("--split", required=True)
    parser.add_argument("--schema", type=Path, required=True)
    parser.add_argument("--output-format", choices=("minimal_text", "argument_object"), default="minimal_text")
    parser.add_argument("--out-dir", type=Path, required=True)
    return parser.parse_args(argv)


def load_schema_file(dataset: str, schema_path: Path) -> DatasetSchema:
    with schema_path.open(encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError(f"schema must be a mapping: {schema_path}")
    event_roles: dict[str, tuple[str, ...]] = {}
    raw_event_types = payload.get("event_types")
    if not isinstance(raw_event_types, list):
        raise ValueError(f"schema event_types must be a list: {schema_path}")
    for index, raw_event in enumerate(raw_event_types, 1):
        if not isinstance(raw_event, dict):
            raise ValueError(f"schema event_types[{index}] must be a mapping: {schema_path}")
        event_type = str(raw_event.get("event_type") or "").strip()
        if not event_type:
            raise ValueError(f"schema event_types[{index}] missing event_type: {schema_path}")
        roles = tuple(str(role).strip() for role in raw_event.get("roles") or [] if str(role).strip())
        event_roles[event_type] = roles
    return DatasetSchema(
        dataset_id=dataset,
        schema_dataset=str(payload.get("dataset") or dataset),
        schema_path=schema_path,
        canonical_version=_optional_str(payload.get("canonical_version")),
        event_roles=event_roles,
        role_to_event_types=_role_to_event_types(event_roles),
    )


def _optional_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _role_to_event_types(event_roles: dict[str, tuple[str, ...]]) -> dict[str, tuple[str, ...]]:
    role_map: dict[str, list[str]] = {}
    for event_type, roles in event_roles.items():
        for role in roles:
            role_map.setdefault(role, []).append(event_type)
    return {role: tuple(event_types) for role, event_types in sorted(role_map.items())}


def _is_first_candidate(row: dict[str, Any]) -> bool:
    candidate_index = row.get("candidate_index")
    if candidate_index is None:
        return True
    try:
        return int(candidate_index) == 0
    except (TypeError, ValueError):
        return False


def _validation_summary(
    *,
    prediction_path: Path,
    dataset: str,
    split: str,
    schema: DatasetSchema | None = None,
) -> dict[str, Any]:
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
            validate_minimal_canonical_prediction(row, schema=schema)
        except ValueError as exc:
            schema_errors.append({"row": row_index, "error": str(exc)})
    return {
        "created_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
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
        "offline_reparse": True,
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


def _write_json(path: Path, payload: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
    return path


if __name__ == "__main__":
    raise SystemExit(main())
