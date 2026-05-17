from __future__ import annotations

import argparse
import gc
import json
import subprocess
import sys
from collections.abc import Sequence
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from shlex import join
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "src"))

from sage_dee.io_utils import read_yaml, write_yaml  # noqa: E402
from sage_dee.v2.data_interface.dataset_loader import V2DatasetDocument, load_documents  # noqa: E402
from sage_dee.v2.data_interface.jsonl import read_jsonl, write_jsonl  # noqa: E402
from sage_dee.v2.data_interface.schema_registry import load_schema  # noqa: E402
from sage_dee.v2.getm.candidate_generator import generate_getm_candidate_files  # noqa: E402
from sage_dee.v2.getm.generation_diagnostics import DIAGNOSTIC_VERSION  # noqa: E402
from sage_dee.v2.getm.mock_backend import MockGetmBackend  # noqa: E402
from sage_dee.v2.getm.qwen_backend import QwenGetmBackend, _generation_metadata, start_qwen_telemetry  # noqa: E402
from sage_dee.v2.pipeline.export_canonical import validate_minimal_canonical_prediction  # noqa: E402
from sage_dee.v2.pipeline.run_manifest import EVALUATOR_VERSION, PREDICTION_FORMAT  # noqa: E402
from scripts.v2.run_phase6_sft_baseline_matrix import (  # noqa: E402
    FORBIDDEN_CANONICAL_KEYS,
    _release_qwen_backend,
    _telemetry_summary,
)

SOURCE_ROW_ID = "s4_full_or_max_frozen_surface"
SOURCE_METHOD_NAME = "SAGE-DEE-v2.1-R3-S4-full-or-max"
DEFAULT_SOURCE_ROW_ROOT = Path(
    "/data/TJK/DEE/sage-dee/runs/v21_r3_s4_train_size_scaling_seed42/s4_full_or_max_frozen_surface"
)
DEFAULT_SOURCE_ADAPTER = DEFAULT_SOURCE_ROW_ROOT / "train/artifacts/model/adapter"
FINAL_RESULT = REPO_ROOT / "docs/refactor/SAGE_V2_FINAL_TEST_RESULT.json"


def main(argv: Sequence[str] | None = None) -> int:
    try:
        args = parse_args(argv)
        config = read_yaml(args.config)
        _validate_args(args, config)
        if args.merge_shards:
            result = merge_shards(args, config)
        else:
            result = generate_shard(args, config)
    except (FileNotFoundError, RuntimeError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2

    print(f"out_dir={args.out_dir}")
    for key in ("canonical_path", "generation_manifest_path", "run_manifest_path"):
        if result.get(key):
            print(f"{key}={result[key]}")
    return 0


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate or merge S4 full-or-max Row D test predictions for methodology-reference evaluation."
    )
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--dataset", default="DuEE-Fin-dev500")
    parser.add_argument("--split", default="test")
    parser.add_argument("--data-root", default="data")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--source-row-root", type=Path, default=DEFAULT_SOURCE_ROW_ROOT)
    parser.add_argument("--adapter-path", type=Path)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--backend", choices=("qwen", "mock"), default="qwen")
    parser.add_argument("--mock-mode", choices=("empty", "schema_only", "echo_candidates"), default="empty")
    parser.add_argument("--real-run", action="store_true")
    parser.add_argument("--num-shards", type=int, default=1)
    parser.add_argument("--shard-index", type=int, default=0)
    parser.add_argument("--merge-shards", action="store_true")
    parser.add_argument("--shard-dirs", type=Path, nargs="*")
    parser.add_argument("--branch-methodology-reference", action="store_true")
    return parser.parse_args(argv)


def generate_shard(args: argparse.Namespace, config: dict[str, Any]) -> dict[str, Any]:
    args.out_dir.mkdir(parents=True, exist_ok=True)
    adapter_path = _adapter_path(args)
    resolved = _resolved_config(config, args=args, adapter_path=adapter_path)
    schema = load_schema(args.dataset, data_root=args.data_root)
    all_documents = load_documents(args.dataset, args.split, data_root=args.data_root, mode="predict")
    documents = _shard_documents(all_documents, num_shards=args.num_shards, shard_index=args.shard_index)
    write_yaml(args.out_dir / "config.resolved.yaml", resolved)

    telemetry = None
    backend: QwenGetmBackend | MockGetmBackend | None = None
    if args.backend == "qwen":
        telemetry = start_qwen_telemetry(
            resolved,
            args.out_dir,
            operation=f"{SOURCE_ROW_ID}_test_reference_shard_{args.shard_index:02d}_of_{args.num_shards:02d}",
            total_items=len(documents),
        )
        backend = QwenGetmBackend(config=resolved, telemetry=telemetry)
    else:
        backend = MockGetmBackend(mode=args.mock_mode)

    try:
        output = generate_getm_candidate_files(
            documents=documents,
            dataset=args.dataset,
            split=args.split,
            schema=schema,
            backend=backend,
            k=1,
            out_dir=args.out_dir,
        )
    finally:
        if isinstance(backend, QwenGetmBackend):
            _release_qwen_backend(backend)
            gc.collect()
        if telemetry is not None:
            telemetry.finish()

    run_manifest_path = _write_json(
        args.out_dir / "run_manifest.json",
        _run_manifest(args=args, config=resolved, adapter_path=adapter_path),
    )
    generation_manifest_path = _write_json(
        args.out_dir / "generation_manifest.json",
        {
            **_reference_scope(args=args, adapter_path=adapter_path),
            "diagnostic_version": DIAGNOSTIC_VERSION,
            "backend": args.backend,
            "mock_mode": args.mock_mode if args.backend == "mock" else None,
            "dry_run": args.backend != "qwen",
            "real_run": args.backend == "qwen",
            "dataset": args.dataset,
            "split": args.split,
            "document_count": len(documents),
            "source_document_count": len(all_documents),
            "k": 1,
            "shard": {
                "num_shards": args.num_shards,
                "shard_index": args.shard_index,
                "doc_ids": [document.doc_id for document in documents],
            },
            "prompts_path": str(output.prompts_path),
            "raw_outputs_path": str(output.raw_outputs_path),
            "parsed_candidates_path": str(output.parsed_candidates_path),
            "parse_diagnostics_path": str(output.parse_diagnostics_path),
            "canonical_predictions_path": str(output.canonical_predictions_path),
            "gold_visible": False,
            "test_gold_read_by_generation": False,
            "generation": _backend_generation_metadata(backend, resolved),
        },
    )
    summary = _summarize_generation(args.out_dir, dataset=args.dataset, split=args.split)
    _write_json(
        args.out_dir / "reference_summary.json",
        {
            **_reference_scope(args=args, adapter_path=adapter_path),
            **summary,
            "run_manifest_path": str(run_manifest_path),
            "generation_manifest_path": str(generation_manifest_path),
        },
    )
    return {
        "canonical_path": summary["canonical_path"],
        "run_manifest_path": str(run_manifest_path),
        "generation_manifest_path": str(generation_manifest_path),
    }


def merge_shards(args: argparse.Namespace, config: dict[str, Any]) -> dict[str, Any]:
    args.out_dir.mkdir(parents=True, exist_ok=True)
    adapter_path = _adapter_path(args)
    source_rows = load_documents(args.dataset, args.split, data_root=args.data_root, mode="predict")
    source_doc_ids = [document.doc_id for document in source_rows]
    merged_by_doc: dict[str, dict[str, Any]] = {}
    shard_dirs = args.shard_dirs or []
    if not shard_dirs:
        raise ValueError("--merge-shards requires --shard-dirs")

    for shard_dir in shard_dirs:
        manifest_path = shard_dir / "generation_manifest.json"
        if not manifest_path.is_file():
            raise FileNotFoundError(manifest_path)
        manifest = _read_json(manifest_path)
        if manifest.get("source_row") != SOURCE_ROW_ID:
            raise ValueError(f"{manifest_path} is not an {SOURCE_ROW_ID} shard")
        pred_path = shard_dir / "predictions" / args.dataset / f"{args.split}.canonical.pred.jsonl"
        for row in read_jsonl(pred_path):
            doc_id = str(row.get("doc_id") or "")
            if doc_id in merged_by_doc:
                raise ValueError(f"duplicate shard prediction doc_id: {doc_id}")
            merged_by_doc[doc_id] = row

    missing = [doc_id for doc_id in source_doc_ids if doc_id not in merged_by_doc]
    extra = sorted(set(merged_by_doc) - set(source_doc_ids))
    if missing or extra:
        raise ValueError(f"merged shard doc mismatch: missing={missing[:10]}, extra={extra[:10]}")

    merged_rows = [merged_by_doc[doc_id] for doc_id in source_doc_ids]
    prediction_path = args.out_dir / "predictions" / args.dataset / f"{args.split}.canonical.pred.jsonl"
    write_jsonl(prediction_path, merged_rows)
    resolved = _resolved_config(config, args=args, adapter_path=adapter_path)
    write_yaml(args.out_dir / "config.resolved.yaml", resolved)
    run_manifest_path = _write_json(
        args.out_dir / "run_manifest.json",
        _run_manifest(args=args, config=resolved, adapter_path=adapter_path),
    )
    validation = _canonical_validation(merged_rows)
    generation_manifest_path = _write_json(
        args.out_dir / "generation_manifest.json",
        {
            **_reference_scope(args=args, adapter_path=adapter_path),
            "diagnostic_version": DIAGNOSTIC_VERSION,
            "backend": "merged_shards",
            "merged_shards": True,
            "shard_dirs": [str(path) for path in shard_dirs],
            "dataset": args.dataset,
            "split": args.split,
            "document_count": len(merged_rows),
            "canonical_predictions_path": str(prediction_path),
            "canonical_event_count": sum(len(row.get("events") or []) for row in merged_rows),
            "canonical_schema_errors": validation["canonical_schema_errors"],
            "forbidden_key_violations": validation["forbidden_key_violations"],
            "gold_visible": False,
            "test_gold_read_by_generation": False,
        },
    )
    _write_json(
        args.out_dir / "reference_summary.json",
        {
            **_reference_scope(args=args, adapter_path=adapter_path),
            "merged_shards": True,
            "canonical_path": str(prediction_path),
            "canonical_rows": len(merged_rows),
            "canonical_event_count": sum(len(row.get("events") or []) for row in merged_rows),
            "canonical_schema_errors": validation["canonical_schema_errors"],
            "forbidden_key_violations": validation["forbidden_key_violations"],
            "run_manifest_path": str(run_manifest_path),
            "generation_manifest_path": str(generation_manifest_path),
        },
    )
    return {
        "canonical_path": str(prediction_path),
        "run_manifest_path": str(run_manifest_path),
        "generation_manifest_path": str(generation_manifest_path),
    }


def _validate_args(args: argparse.Namespace, config: dict[str, Any]) -> None:
    if not args.branch_methodology_reference:
        raise ValueError("S4 full-or-max test reference requires --branch-methodology-reference")
    if args.dataset != "DuEE-Fin-dev500":
        raise ValueError("S4 full-or-max test reference is restricted to DuEE-Fin-dev500")
    if args.split != "test":
        raise ValueError("S4 full-or-max test reference requires split=test")
    if args.seed != 42:
        raise ValueError("S4 full-or-max test reference is seed42 only")
    if args.backend == "qwen" and not args.real_run and not args.merge_shards:
        raise ValueError("Qwen test generation requires explicit --real-run")
    if args.num_shards < 1:
        raise ValueError("--num-shards must be >= 1")
    if args.shard_index < 0 or args.shard_index >= args.num_shards:
        raise ValueError("--shard-index must satisfy 0 <= index < num_shards")
    if _under_phase13_run_root(args.out_dir):
        raise ValueError("S4 full-or-max test reference refuses to write under a Phase 13 run root")
    if config.get("allow_test") is not False or config.get("test_enabled") is not False:
        raise ValueError(
            "source R3 config must keep test disabled; this runner is the explicit branch-only test reference"
        )
    _validate_source_row(args)
    _require_final_result_clean()


def _validate_source_row(args: argparse.Namespace) -> None:
    summary_path = args.source_row_root / "row_summary.json"
    if not summary_path.is_file():
        raise FileNotFoundError(summary_path)
    summary = _read_json(summary_path)
    if summary.get("row_id") != SOURCE_ROW_ID:
        raise ValueError(f"source row must be {SOURCE_ROW_ID}")
    if summary.get("seed") != 42:
        raise ValueError("source row must be seed42")
    if summary.get("dataset") != "DuEE-Fin-dev500":
        raise ValueError("source row dataset must be DuEE-Fin-dev500")
    if int(summary.get("train_limit") or 0) != 6474:
        raise ValueError("source row train_limit must be 6474")
    expected_adapter = args.source_row_root / "train" / "artifacts" / "model" / "adapter"
    adapter_path = _adapter_path(args)
    if adapter_path.resolve() != expected_adapter.resolve():
        raise ValueError(f"adapter path must match R3 Row D adapter: {expected_adapter}")
    if not (adapter_path / "adapter_config.json").is_file():
        raise FileNotFoundError(adapter_path / "adapter_config.json")


def _adapter_path(args: argparse.Namespace) -> Path:
    return args.adapter_path or (args.source_row_root / "train" / "artifacts" / "model" / "adapter")


def _under_phase13_run_root(path: Path) -> bool:
    return any("phase13_final_test" in part for part in path.resolve().parts)


def _require_final_result_clean() -> None:
    completed = subprocess.run(
        ["git", "diff", "--quiet", "--", str(FINAL_RESULT.relative_to(REPO_ROOT))],
        cwd=REPO_ROOT,
        check=False,
    )
    if completed.returncode != 0:
        raise ValueError(
            "S4 full-or-max test reference refuses to run while frozen final result has local modifications"
        )


def _shard_documents(
    documents: list[V2DatasetDocument],
    *,
    num_shards: int,
    shard_index: int,
) -> list[V2DatasetDocument]:
    return [document for index, document in enumerate(documents) if index % num_shards == shard_index]


def _resolved_config(config: dict[str, Any], *, args: argparse.Namespace, adapter_path: Path) -> dict[str, Any]:
    resolved = deepcopy(config)
    resolved["allow_test"] = False
    resolved["test_enabled"] = False
    run_cfg = dict(resolved.get("run") or {})
    run_cfg.update(
        {
            "profile": "s4_full_method_test_reference",
            "row_id": SOURCE_ROW_ID,
            "dry_run": args.backend != "qwen",
            "real_run": args.backend == "qwen",
        }
    )
    resolved["run"] = run_cfg
    data_cfg = dict(resolved.get("data") or {})
    data_cfg.update(
        {
            "dataset": args.dataset,
            "data_root": str(args.data_root),
            "eval_split": args.split,
            "max_predict_docs": None,
        }
    )
    resolved["data"] = data_cfg
    predict_cfg = dict(resolved.get("predict") or {})
    predict_cfg.update(
        {
            "dataset": args.dataset,
            "split": args.split,
            "data_root": str(args.data_root),
            "max_predict_docs": None,
        }
    )
    resolved["predict"] = predict_cfg
    generation = dict((resolved.get("getm") or {}).get("generation") or {})
    generation.update(
        {
            "seed": 42,
            "k_candidates": 1,
            "do_sample": False,
            "temperature": None,
            "top_p": 1.0,
            "deterministic": True,
            "deterministic_warn_only": True,
            "record_resolved_generation_config": True,
        }
    )
    resolved.setdefault("getm", {})["generation"] = generation
    resolved.setdefault("getm", {}).setdefault("qwen", {})["adapter_path"] = str(adapter_path)
    return resolved


def _reference_scope(args: argparse.Namespace, *, adapter_path: Path) -> dict[str, Any]:
    return {
        "method_name": SOURCE_METHOD_NAME,
        "source_row": SOURCE_ROW_ID,
        "source_row_root": str(args.source_row_root),
        "source_train_limit": 6474,
        "adapter_path": str(adapter_path),
        "seed": 42,
        "methodology_reference": True,
        "native_reference_only": False,
        "formal_metric": False,
        "frozen_final_result": False,
        "phase13_reinterpretation": False,
        "phase13_result_modified": False,
        "training_run": False,
    }


def _run_manifest(*, args: argparse.Namespace, config: dict[str, Any], adapter_path: Path) -> dict[str, Any]:
    return {
        "run_id": f"s4_full_method_test_reference_seed42_{_created_slug()}",
        "method_name": SOURCE_METHOD_NAME,
        "method_family": "SAGE-DEE-v2",
        "stage": "predict",
        "dataset_version": args.dataset,
        "split_version": args.split,
        "evaluator_version": EVALUATOR_VERSION,
        "prediction_format": PREDICTION_FORMAT,
        "training_view": "evaluator_gold/train",
        "gold_view": f"processed/views/evaluator_gold/{args.dataset}",
        "seed": 42,
        "backend": args.backend,
        "dry_run": bool((config.get("run") or {}).get("dry_run", True)),
        "real_run": bool((config.get("run") or {}).get("real_run", False)),
        "profile": (config.get("run") or {}).get("profile"),
        "source_row": SOURCE_ROW_ID,
        "source_train_limit": 6474,
        "adapter_path": str(adapter_path),
        "command_train": None,
        "command_infer": join([sys.executable, "scripts/v2/run_s4_full_method_test_reference.py"]),
        "git_commit": _git_commit(),
        "created_at": _created_at(),
        "notes": (
            "Branch-only S4 full-or-max Row D test methodology reference; "
            "not Phase 13 frozen final result and not a reinterpretation of Phase 13."
        ),
    }


def _backend_generation_metadata(backend: Any, config: dict[str, Any]) -> dict[str, Any]:
    metadata = getattr(backend, "generation_metadata", None)
    if callable(metadata):
        metadata = metadata()
    if isinstance(metadata, dict):
        return dict(metadata)
    return _generation_metadata(config)


def _summarize_generation(run_dir: Path, *, dataset: str, split: str) -> dict[str, Any]:
    diagnostics = _read_json(run_dir / f"parse_diagnostics.{split}.json")
    parsed_rows = read_jsonl(run_dir / f"parsed_candidates.{split}.jsonl")
    canonical_path = run_dir / "predictions" / dataset / f"{split}.canonical.pred.jsonl"
    canonical_rows = read_jsonl(canonical_path)
    diagnostic_counts = diagnostics.get("diagnostic_counts") or {}
    parse_status_counts = diagnostics.get("parse_status_counts") or {}
    validation = _canonical_validation(canonical_rows)
    return {
        "run_dir": str(run_dir),
        "parse_diagnostics_path": str(run_dir / f"parse_diagnostics.{split}.json"),
        "canonical_path": str(canonical_path),
        "canonical_rows": len(canonical_rows),
        "canonical_event_count": sum(len(row.get("events") or []) for row in canonical_rows),
        "parse_status_counts": dict(sorted(parse_status_counts.items())),
        "parse_error": int(parse_status_counts.get("parse_error", 0) or 0),
        "schema_violation_rows": sum(1 for row in parsed_rows if row.get("parse_status") == "schema_violation"),
        "unknown_role": int(diagnostic_counts.get("unknown_role", 0) or 0),
        "unknown_event_type": int(diagnostic_counts.get("unknown_event_type", 0) or 0),
        "forbidden_key_violations": validation["forbidden_key_violations"],
        "canonical_schema_errors": validation["canonical_schema_errors"],
        "telemetry": _telemetry_summary(run_dir),
        "oom": _has_oom(run_dir),
    }


def _canonical_validation(canonical_rows: list[dict[str, Any]]) -> dict[str, Any]:
    schema_errors = 0
    forbidden_violations = 0
    for row in canonical_rows:
        try:
            validate_minimal_canonical_prediction(row)
        except ValueError:
            schema_errors += 1
        forbidden_violations += len(_forbidden_key_paths(row))
    return {"canonical_schema_errors": schema_errors, "forbidden_key_violations": forbidden_violations}


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


def _has_oom(run_dir: Path) -> bool:
    for path in run_dir.rglob("*.log"):
        try:
            if "out of memory" in path.read_text(encoding="utf-8", errors="ignore").lower():
                return True
        except OSError:
            continue
    return False


def _read_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return payload


def _write_json(path: Path, payload: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(_jsonable(payload), ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return path


def _jsonable(value: Any) -> Any:
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    return value


def _git_commit() -> str:
    completed = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip() if completed.returncode == 0 else "unknown"


def _created_at() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _created_slug() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


if __name__ == "__main__":
    raise SystemExit(main())
