from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from collections.abc import Sequence
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))

from sage_dee.v2.data_interface.jsonl import read_jsonl, write_jsonl  # noqa: E402
from sage_dee.v2.data_interface.schema_registry import DatasetSchema, load_schema  # noqa: E402
from sage_dee.v2.getm.generation_diagnostics import aggregate_parse_diagnostics  # noqa: E402
from sage_dee.v2.getm.parser_ablation import (  # noqa: E402
    PARSER_ABLATION_MODES,
    candidate_set_to_canonical_prediction,
    candidate_set_to_dict,
    parse_getm_output_ablation,
)
from sage_dee.v2.pipeline.export_canonical import (  # noqa: E402
    export_predictions,
    validate_minimal_canonical_prediction,
)
from sage_dee.v2.pipeline.run_manifest import EVALUATOR_VERSION, PREDICTION_FORMAT  # noqa: E402

DEFAULT_SERVER_RUNS_ROOT = Path("/data/TJK/DEE/sage-dee/runs")
DEFAULT_SERVER_SCHEMA_ROOT = Path("/data/TJK/DEE/data/processed")
DEFAULT_LOCAL_SCHEMA_ROOT = REPO_ROOT / "data"
DISCOVERY_REPORTS = (
    REPO_ROOT / "docs/refactor/SAGE_V2_PHASE7_SURFACE_MEMORY_ABLATION.md",
    REPO_ROOT / "docs/refactor/SAGE_V2_PHASE6_SFT_BASELINE_MATRIX_S1_S4.md",
    REPO_ROOT / "docs/refactor/SAGE_V2_PHASE9_DUEE_FIN_FULL_DEV_MAIN_TABLE.md",
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
    _enforce_dev_only(args)

    raw_output = args.raw_output or discover_dev_raw_output(args.dataset)
    _reject_test_path(raw_output, label="raw-output")
    if not raw_output.is_file():
        raise SystemExit(f"dev raw-output path does not exist: {raw_output}")

    schema = resolve_schema(args.dataset, args.schema)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    raw_rows = read_jsonl(raw_output)
    source_generation = _source_generation_metadata(raw_output)
    output_format = str(source_generation.get("output_format") or args.output_format)
    response_prefix_used = bool(source_generation.get("response_prefix_used"))
    response_prefix = str(source_generation.get("response_prefix") or "") if response_prefix_used else None

    parsed_rows: list[dict[str, Any]] = []
    first_candidates: dict[str, Any] = {}
    for row_number, row in enumerate(raw_rows, 1):
        doc_id = str(row.get("doc_id") or "").strip()
        if not doc_id:
            raise ValueError(f"raw output row {row_number} missing doc_id")
        candidate_id = str(row.get("candidate_id") or f"{doc_id}:getm:{row_number - 1}").strip()
        raw_text = str(row.get("raw_output") or row.get("stopped_output") or "")
        candidate = parse_getm_output_ablation(
            raw_text,
            doc_id=doc_id,
            candidate_id=candidate_id,
            schema=schema,
            mode=args.mode,
            response_prefix=response_prefix,
            response_prefix_used=response_prefix_used,
            generation_metadata=source_generation,
            token_metadata=row,
            output_format=output_format,
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
    manifest_path = args.out_dir / "run_manifest.json"
    _write_json(
        manifest_path,
        _run_manifest(
            args=args,
            raw_output=raw_output,
            schema_path=schema.schema_path,
            parsed_path=parsed_path,
            diagnostics_path=diagnostics_path,
            prediction_path=prediction_path,
            validation_path=validation_path,
            raw_row_count=len(raw_rows),
            canonical_row_count=len(first_candidates),
            source_generation=source_generation,
        ),
    )

    print(f"raw_output={raw_output}")
    print(f"parsed_candidates={parsed_path}")
    print(f"parse_diagnostics={diagnostics_path}")
    print(f"canonical_predictions={prediction_path}")
    print(f"validation_summary={validation_path}")
    print(f"run_manifest={manifest_path}")
    return 0


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="SAGE v2.1 R1 dev-only parser reparse ablation.")
    parser.add_argument("--dataset", default="DuEE-Fin-dev500")
    parser.add_argument("--split", default="dev")
    parser.add_argument("--raw-output", type=Path)
    parser.add_argument("--schema", type=Path)
    parser.add_argument("--mode", choices=PARSER_ABLATION_MODES, required=True)
    parser.add_argument("--output-format", choices=("minimal_text", "argument_object"), default="minimal_text")
    parser.add_argument("--out-dir", type=Path, required=True)
    return parser.parse_args(argv)


def discover_dev_raw_output(dataset: str) -> Path:
    candidates: list[Path] = []
    candidates.extend(_phase7_seed42_compressed_candidates(dataset))
    candidates.extend(_phase6_seed42_s4_candidates(dataset))
    for path in candidates:
        if _is_allowed_dev_raw_output(path) and path.is_file():
            return path
    tried = "\n".join(str(path) for path in candidates) or "(none)"
    raise SystemExit(
        "could not auto-discover DuEE-Fin-dev500/dev raw outputs for R1; "
        "provide --raw-output explicitly. Tried:\n"
        f"{tried}"
    )


def resolve_schema(dataset: str, schema_path: Path | None) -> DatasetSchema:
    if schema_path is not None:
        _reject_test_path(schema_path, label="schema")
        return _load_schema_file(dataset, schema_path)
    for root in (DEFAULT_SERVER_SCHEMA_ROOT, DEFAULT_LOCAL_SCHEMA_ROOT):
        candidate = root / dataset / "schema.json"
        if candidate.is_file():
            if root == DEFAULT_LOCAL_SCHEMA_ROOT:
                return load_schema(dataset, data_root=root)
            return _load_schema_file(dataset, candidate)
    raise SystemExit(
        f"could not resolve schema for {dataset}; tried "
        f"{DEFAULT_SERVER_SCHEMA_ROOT / dataset / 'schema.json'} and "
        f"{DEFAULT_LOCAL_SCHEMA_ROOT / dataset / 'schema.json'}"
    )


def _phase7_seed42_compressed_candidates(dataset: str) -> list[Path]:
    paths: list[Path] = []
    aggregate_paths = _paths_from_reports(r"phase7_surface_memory_ablation_aggregate\.full_dev\.json")
    aggregate_paths.append(DEFAULT_SERVER_RUNS_ROOT / "phase7_surface_memory_ablation_aggregate.full_dev.json")
    for aggregate_path in aggregate_paths:
        payload = _read_json_if_exists(aggregate_path)
        for row in payload.get("runs") or []:
            if (
                row.get("variant_id") == "compressed_surface"
                and row.get("seed") == 42
                and row.get("test_used") is False
            ):
                run_dir = Path(str(row.get("run_dir") or ""))
                paths.append(run_dir / "full_dev" / "raw_outputs.dev.jsonl")
    paths.append(
        DEFAULT_SERVER_RUNS_ROOT
        / "phase7_compressed_surface_seed42_20260504T122801Z/full_dev/raw_outputs.dev.jsonl"
    )
    return _dedupe_paths(paths)


def _phase6_seed42_s4_candidates(dataset: str) -> list[Path]:
    paths: list[Path] = []
    aggregate_paths = _paths_from_reports(r"phase6_sft_baseline_matrix_aggregate\.full_dev\.json")
    aggregate_paths.append(DEFAULT_SERVER_RUNS_ROOT / "phase6_sft_baseline_matrix_aggregate.full_dev.json")
    for aggregate_path in aggregate_paths:
        payload = _read_json_if_exists(aggregate_path)
        for row in payload.get("runs") or []:
            if (
                row.get("baseline_id") == "S4"
                and row.get("seed") == 42
                and row.get("test_used") is False
            ):
                run_dir = Path(str(row.get("run_dir") or ""))
                paths.append(run_dir / "full_dev" / "raw_outputs.dev.jsonl")
    paths.append(DEFAULT_SERVER_RUNS_ROOT / "phase6_S4_seed42_20260504T052553Z/full_dev/raw_outputs.dev.jsonl")
    return _dedupe_paths(paths)


def _paths_from_reports(filename_pattern: str) -> list[Path]:
    paths: list[Path] = []
    path_re = re.compile(r"/data/TJK/DEE/sage-dee/runs/[^\s`)]+")
    filename_re = re.compile(filename_pattern)
    for report in DISCOVERY_REPORTS:
        if not report.is_file():
            continue
        text = report.read_text(encoding="utf-8")
        for match in path_re.finditer(text):
            value = match.group(0)
            if filename_re.search(value):
                paths.append(Path(value))
    return _dedupe_paths(paths)


def _read_json_if_exists(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    with path.open(encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        return {}
    return payload


def _source_generation_metadata(raw_output: Path) -> dict[str, Any]:
    manifest = _read_json_if_exists(raw_output.parent / "generation_manifest.json")
    generation = manifest.get("generation")
    return dict(generation) if isinstance(generation, dict) else {}


def _dedupe_paths(paths: list[Path]) -> list[Path]:
    seen: set[str] = set()
    deduped: list[Path] = []
    for path in paths:
        key = str(path)
        if not key or key in seen:
            continue
        seen.add(key)
        deduped.append(path)
    return deduped


def _is_allowed_dev_raw_output(path: Path) -> bool:
    text = str(path)
    return "raw_outputs.dev.jsonl" in text and "test" not in text.lower()


def _enforce_dev_only(args: argparse.Namespace) -> None:
    if args.split != "dev":
        raise SystemExit("R1 parser reparse ablation is dev split only")
    if args.dataset != "DuEE-Fin-dev500":
        raise SystemExit("R1 parser reparse ablation is restricted to DuEE-Fin-dev500/dev")
    if args.raw_output is not None:
        _reject_test_path(args.raw_output, label="raw-output")
    _reject_test_path(args.out_dir, label="out-dir")


def _reject_test_path(path: Path, *, label: str) -> None:
    if _path_mentions_test_split(path):
        raise SystemExit(f"R1 rejects {label} path containing test: {path}")


def _path_mentions_test_split(path: Path) -> bool:
    for part in path.parts:
        lowered = part.lower()
        if lowered == "test" or "-test" in lowered or ".test" in lowered or "test." in lowered:
            return True
    return False


def _load_schema_file(dataset: str, schema_path: Path) -> DatasetSchema:
    with schema_path.open(encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError(f"schema must be a mapping: {schema_path}")
    raw_event_types = payload.get("event_types")
    if not isinstance(raw_event_types, list):
        raise ValueError(f"schema event_types must be a list: {schema_path}")
    event_roles: dict[str, tuple[str, ...]] = {}
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
    schema: DatasetSchema,
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
        "created_at": _created_at(),
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


def _run_manifest(
    *,
    args: argparse.Namespace,
    raw_output: Path,
    schema_path: Path,
    parsed_path: Path,
    diagnostics_path: Path,
    prediction_path: Path,
    validation_path: Path,
    raw_row_count: int,
    canonical_row_count: int,
    source_generation: dict[str, Any],
) -> dict[str, Any]:
    return {
        "run_id": f"v21_r1_parser_ablation_{args.mode}_{_created_slug()}",
        "phase": "R1 parser/canonical dev reparse ablation",
        "method_name": "SAGE-DEE-v2.1-R1-Parser-Reparse-Ablation",
        "method_family": "SAGE-DEE-v2.1-dev-rescue",
        "stage": "offline_reparse",
        "dataset": args.dataset,
        "split": args.split,
        "dataset_version": args.dataset,
        "split_version": args.split,
        "evaluator_version": EVALUATOR_VERSION,
        "prediction_format": PREDICTION_FORMAT,
        "training_view": "existing_seed42_dev_raw_outputs",
        "gold_view": f"processed/views/evaluator_gold/{args.dataset}",
        "mode": args.mode,
        "raw_output_path": str(raw_output),
        "schema_path": str(schema_path),
        "parsed_candidates_path": str(parsed_path),
        "parse_diagnostics_path": str(diagnostics_path),
        "canonical_predictions_path": str(prediction_path),
        "validation_summary_path": str(validation_path),
        "source_generation_manifest_path": str(raw_output.parent / "generation_manifest.json"),
        "source_generation_response_prefix_used": bool(source_generation.get("response_prefix_used")),
        "source_generation_output_format": source_generation.get("output_format"),
        "raw_row_count": raw_row_count,
        "canonical_row_count": canonical_row_count,
        "qwen_run": False,
        "train_run": False,
        "test_run": False,
        "test_gold_read": False,
        "gold_visible": False,
        "seed": 42,
        "backend": "offline_reparse",
        "dry_run": False,
        "real_run": True,
        "command_train": None,
        "command_infer": " ".join(
            [
                sys.executable,
                "scripts/v2/run_v21_r1_parser_reparse_ablation.py",
                "--dataset",
                args.dataset,
                "--split",
                args.split,
                "--mode",
                args.mode,
                "--out-dir",
                str(args.out_dir),
            ]
        ),
        "created_at": _created_at(),
        "command": " ".join([sys.executable, *sys.argv]),
        "git_commit": _git_commit(),
        "notes": "Dev-only offline reparse of existing raw outputs; no Qwen, no training, no test.",
    }


def _created_at() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _created_slug() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _git_commit() -> str | None:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=REPO_ROOT,
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except Exception:
        return None


def _write_json(path: Path, payload: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
    return path


if __name__ == "__main__":
    raise SystemExit(main())
