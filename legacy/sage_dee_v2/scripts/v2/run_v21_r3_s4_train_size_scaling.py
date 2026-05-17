from __future__ import annotations

import argparse
import gc
import hashlib
import json
import subprocess
import sys
from collections.abc import Sequence
from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from shlex import join
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "src"))

from sage_dee.io_utils import read_yaml, write_yaml  # noqa: E402
from sage_dee.v2.csg.surface_memory import build_surface_memory  # noqa: E402
from sage_dee.v2.data_interface.dataset_loader import V2DatasetDocument, load_documents  # noqa: E402
from sage_dee.v2.data_interface.jsonl import read_jsonl, write_jsonl  # noqa: E402
from sage_dee.v2.data_interface.schema_registry import load_schema  # noqa: E402
from sage_dee.v2.getm.candidate_generator import generate_getm_candidate_files  # noqa: E402
from sage_dee.v2.getm.candidate_generator_v21 import build_v21_surface_memory  # noqa: E402
from sage_dee.v2.getm.generation_diagnostics import DIAGNOSTIC_VERSION  # noqa: E402
from sage_dee.v2.getm.qwen_backend import (  # noqa: E402
    QwenGetmBackend,
    _generation_metadata,
    start_qwen_telemetry,
    train_sft,
)
from sage_dee.v2.getm.sft_dataset import audit_sft_targets, build_getm_sft_sample  # noqa: E402
from sage_dee.v2.pipeline.evaluator_handoff import build_evaluator_handoff, run_evaluator_handoff  # noqa: E402
from sage_dee.v2.pipeline.run_manifest import EVALUATOR_VERSION, PREDICTION_FORMAT  # noqa: E402
from scripts.v2.aggregate_v21_r3_s4_train_size_scaling import aggregate_r3  # noqa: E402
from scripts.v2.run_phase6_sft_baseline_matrix import (  # noqa: E402
    _canonical_validation,
    _extract_artifact_root,
    _release_qwen_backend,
    _telemetry_summary,
)

R1_REPORT = REPO_ROOT / "docs/refactor/SAGE_V2_1_R1_PARSER_REPARSE_ABLATION.md"
R2_REPORT = REPO_ROOT / "docs/refactor/SAGE_V2_1_R2_SURFACE_COVERAGE_FIRST.md"
R0_REPORT = REPO_ROOT / "docs/refactor/SAGE_V2_1_R0_BRANCH_SETUP.md"
DEV_RESCUE_PLAN = REPO_ROOT / "docs/refactor/SAGE_V2_1_DEV_RESCUE_PLAN.md"
CHANGELOG = REPO_ROOT / "docs/refactor/SAGE_V2_1_DEV_RESCUE_CHANGELOG.md"
FINAL_RESULT = REPO_ROOT / "docs/refactor/SAGE_V2_FINAL_TEST_RESULT.json"
PRIMARY_ROW_ID = "s4_2k_frozen_surface"


@dataclass(frozen=True)
class RowSpec:
    row_id: str
    train_limit: int | str
    surface: str
    action: str
    secondary: bool = False
    conditional: bool = False


ROW_SPECS = {
    "baseline_512_existing": RowSpec(
        row_id="baseline_512_existing",
        train_limit=512,
        surface="frozen_compressed_phase6_final_profile",
        action="read_existing",
    ),
    "s4_2k_frozen_surface": RowSpec(
        row_id="s4_2k_frozen_surface",
        train_limit=2000,
        surface="frozen_compressed_phase6_final_profile",
        action="train_generate_eval",
    ),
    "s4_2k_v21_surface_secondary": RowSpec(
        row_id="s4_2k_v21_surface_secondary",
        train_limit=2000,
        surface="v21_surface_opt_in_r2",
        action="train_generate_eval",
        secondary=True,
    ),
    "s4_full_or_max_frozen_surface": RowSpec(
        row_id="s4_full_or_max_frozen_surface",
        train_limit="full_or_max",
        surface="frozen_compressed_phase6_final_profile",
        action="train_generate_eval",
        conditional=True,
    ),
}


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    config = read_yaml(args.config)
    try:
        _validate_args(args, config)
        if args.evaluator_root is None:
            args.evaluator_root = Path(str(config.get("evaluator_root") or "/home/TJK/DEE/dee-eval"))
        args.out_root.mkdir(parents=True, exist_ok=True)
        rows = _selected_rows(args.rows)
        summaries = []
        for row in rows:
            _validate_row_preconditions(row, args=args, config=config)
            if row.action == "read_existing":
                summaries.append(_run_baseline_existing(row, args=args, config=config))
            else:
                summaries.append(_run_train_generate_eval(row, args=args, config=config))
        aggregate = aggregate_r3(args.out_root)
        aggregate_path = args.out_root / "v21_r3_s4_train_size_scaling_summary.json"
        _write_json(aggregate_path, aggregate)
        _write_json(
            args.out_root / "aggregate_pointer.json",
            {
                "phase": "R3 S4 train-size scaling",
                "aggregate_json": str(aggregate_path),
                "rows": [summary["row_id"] for summary in summaries],
                "created_at": _created_at(),
            },
        )
    except (RuntimeError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2

    print(f"run_root={args.out_root}")
    print(f"aggregate_json={aggregate_path}")
    print(f"row_count={len(summaries)}")
    return 0


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run SAGE v2.1 R3 S4 train-size scaling diagnostics.")
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--dataset", required=True)
    parser.add_argument("--eval-split", default="dev")
    parser.add_argument("--train-split", default="train")
    parser.add_argument("--data-root")
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--systems", default="S4")
    parser.add_argument("--rows", required=True)
    parser.add_argument("--baseline-summary", type=Path)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--real-run", action="store_true")
    parser.add_argument("--allow-missing-gate-for-local-test", action="store_true")
    parser.add_argument("--skip-evaluator", action="store_true")
    parser.add_argument("--evaluator-root", type=Path)
    parser.add_argument("--benchmark-root", type=Path, default=Path("/data/TJK/DEE/data/processed"))
    parser.add_argument("--out-root", type=Path, required=True)
    return parser.parse_args(argv)


def row_d_triggered(baseline: dict[str, Any], primary: dict[str, Any]) -> bool:
    event_delta = _number(primary.get("event_table_micro_f1")) - _number(baseline.get("event_table_micro_f1"))
    exact_delta = _number(primary.get("exact_record_f1")) - _number(baseline.get("exact_record_f1"))
    return event_delta >= 0.05 or exact_delta >= 0.01


def _validate_args(args: argparse.Namespace, config: dict[str, Any]) -> None:
    if args.eval_split == "test":
        raise ValueError("R3 rejects test split")
    if args.eval_split != "dev":
        raise ValueError(f"R3 only permits dev eval split, got {args.eval_split!r}")
    if args.seed != 42:
        raise ValueError("R3 is seed42 only")
    if any(system != "S4" for system in _split_csv(args.systems)):
        raise ValueError("R3 is S4 only")
    if args.dataset != "DuEE-Fin-dev500":
        raise ValueError("R3 is restricted to DuEE-Fin-dev500")
    if args.train_split != "train":
        raise ValueError("R3 training split must be train")
    if config.get("allow_test") is not False or config.get("test_enabled") is not False:
        raise ValueError("R3 config must keep test disabled")
    if config.get("allow_seed43_44") is not False:
        raise ValueError("R3 config must reject seed43/44")
    if not args.allow_missing_gate_for_local_test:
        _require_gate_documents()
    _require_final_result_clean()
    _selected_rows(args.rows)


def _selected_rows(raw_rows: str) -> list[RowSpec]:
    rows = []
    for row_id in _split_csv(raw_rows):
        if row_id not in ROW_SPECS:
            raise ValueError(f"unsupported R3 row: {row_id}")
        rows.append(ROW_SPECS[row_id])
    return rows


def _validate_row_preconditions(row: RowSpec, *, args: argparse.Namespace, config: dict[str, Any]) -> None:
    if row.row_id.startswith(("S1", "S2", "S3")):
        raise ValueError("R3 rejects S1/S2/S3 rows")
    if row.secondary:
        row_b = args.out_root / PRIMARY_ROW_ID / "row_summary.json"
        if not row_b.is_file():
            raise RuntimeError("Row C requires successful Row B summary before secondary v21 run")
        row_b_summary = _read_json(row_b)
        if row_b_summary.get("oom"):
            raise RuntimeError("Row C blocked: Row B recorded OOM")
        if not args.dry_run and row_b_summary.get("evaluator_validation_ok") is not True:
            raise RuntimeError("Row C blocked: Row B evaluator validation did not pass")
    if row.conditional:
        aggregate = aggregate_r3(args.out_root)
        if not aggregate.get("row_d_triggered"):
            raise RuntimeError("Row D blocked: Row B did not meet the predeclared trigger")
        if row.surface != "frozen_compressed_phase6_final_profile":
            raise RuntimeError("Row D only permits frozen surface")
    if row.surface == "v21_surface_opt_in_r2":
        _require_r2_budget(config)


def _run_baseline_existing(row: RowSpec, *, args: argparse.Namespace, config: dict[str, Any]) -> dict[str, Any]:
    row_dir = args.out_root / row.row_id
    row_dir.mkdir(parents=True, exist_ok=True)
    summary_path = args.baseline_summary or Path(str((config.get("r3") or {}).get("baseline_summary_path") or ""))
    if not summary_path.is_file():
        raise RuntimeError(f"missing existing 512 baseline summary: {summary_path}")
    source = _read_json(summary_path)
    full_dev = source.get("full_dev") or {}
    train = source.get("train") or {}
    scope = source.get("scope") or {}
    if source.get("baseline_id") != "S4" or source.get("seed") != 42:
        raise RuntimeError("baseline_512_existing must point to Phase 6 S4 seed42")
    if int(scope.get("train_limit") or 0) != 512:
        raise RuntimeError("baseline_512_existing must have train_limit 512")
    if scope.get("test_used") or scope.get("full_train_used"):
        raise RuntimeError("baseline_512_existing must not use test or full train")

    training_manifest = {
        "row_id": row.row_id,
        "train_run": False,
        "baseline_retrained": False,
        "source_training_manifest": str(Path(str(source.get("run_dir") or "")) / "train" / "training_manifest.json"),
        "adapter_path": train.get("adapter_dir"),
    }
    generation_manifest = {
        "row_id": row.row_id,
        "generation_run": False,
        "source_generation_manifest": full_dev.get("generation_manifest_path"),
        "canonical_predictions_path": full_dev.get("canonical_path"),
    }
    _write_json(row_dir / "training_manifest.json", training_manifest)
    _write_json(row_dir / "generation_manifest.json", generation_manifest)
    row_summary = _base_row_summary(row, args=args, train_limit=512)
    row_summary.update(
        {
            "action": "read_existing",
            "train_run": False,
            "generation_run": False,
            "baseline_retrained": False,
            "adapter_path": train.get("adapter_dir"),
            "prediction_path": full_dev.get("canonical_path"),
            "evaluator_artifact_path": full_dev.get("evaluator_artifact_root"),
            "event_table_micro_f1": full_dev.get("event_table_micro_f1"),
            "role_level_f1": full_dev.get("role_level_f1"),
            "exact_record_f1": full_dev.get("exact_record_f1"),
            "parse_error": full_dev.get("parse_error"),
            "schema_violation_rows": full_dev.get("schema_violation_rows"),
            "unknown_role": full_dev.get("unknown_role"),
            "unknown_event_type": full_dev.get("unknown_event_type"),
            "canonical_rows": full_dev.get("canonical_rows"),
            "canonical_event_count": full_dev.get("canonical_event_count"),
            "accepted_event_count": full_dev.get("accepted_event_count", full_dev.get("canonical_event_count")),
            "train_examples_seen": train.get("train_examples", train.get("train_rows", 512)),
            "training_manifest_path": str(row_dir / "training_manifest.json"),
            "generation_manifest_path": str(row_dir / "generation_manifest.json"),
        }
    )
    return _write_row_outputs(row_dir, row_summary, args=args)


def _run_train_generate_eval(row: RowSpec, *, args: argparse.Namespace, config: dict[str, Any]) -> dict[str, Any]:
    row_dir = args.out_root / row.row_id
    row_dir.mkdir(parents=True, exist_ok=True)
    train_limit = _resolved_train_limit(row, args=args, config=config)
    resolved = _resolved_config(config, args=args, row=row, train_limit=train_limit, adapter_path=None)
    write_yaml(row_dir / "config.resolved.train.yaml", resolved)
    train_summary = _run_train(row_dir / "train", config=resolved, args=args, train_limit=train_limit, row=row)
    adapter_path = str(train_summary.get("adapter_path") or "dry-run-no-adapter")
    generation_config = _resolved_config(config, args=args, row=row, train_limit=train_limit, adapter_path=adapter_path)
    write_yaml(row_dir / "config.resolved.generate.yaml", generation_config)
    generation = _run_generate(
        row_dir / "full_dev",
        config=generation_config,
        args=args,
        row=row,
        adapter_path=adapter_path,
    )
    evaluator = _run_evaluator(row_dir / "full_dev", args=args)
    row_summary = _base_row_summary(row, args=args, train_limit=train_limit)
    row_summary.update(
        {
            "action": "train_generate_eval",
            "train_run": not args.dry_run,
            "generation_run": True,
            "baseline_retrained": False,
            "adapter_path": adapter_path,
            "prediction_path": generation.get("canonical_path"),
            "evaluator_artifact_path": evaluator.get("evaluator_artifact_root"),
            "evaluator_validation_ok": evaluator.get("evaluator_validation_ok"),
            "event_table_micro_f1": evaluator.get("event_table_micro_f1"),
            "role_level_f1": evaluator.get("role_level_f1"),
            "exact_record_f1": evaluator.get("exact_record_f1"),
            "parse_error": generation.get("parse_error"),
            "schema_violation_rows": generation.get("schema_violation_rows"),
            "unknown_role": generation.get("unknown_role"),
            "unknown_event_type": generation.get("unknown_event_type"),
            "canonical_rows": generation.get("canonical_rows"),
            "canonical_event_count": generation.get("canonical_event_count"),
            "accepted_event_count": generation.get("accepted_event_count"),
            "train_examples_seen": train_summary.get("train_examples_seen"),
            "num_train_epochs": train_summary.get("num_train_epochs"),
            "train_loss_final": train_summary.get("train_loss_final"),
            "train_loss_mean": train_summary.get("train_loss_mean"),
            "peak_vram": _peak_vram(train_summary.get("telemetry"), generation.get("telemetry")),
            "wallclock": {
                "train_runtime": train_summary.get("train_runtime"),
                "train_elapsed_sec": _elapsed_sec(train_summary.get("telemetry")),
                "generation_elapsed_sec": _elapsed_sec(generation.get("telemetry")),
            },
            "training_manifest_path": str(row_dir / "training_manifest.json"),
            "generation_manifest_path": str(row_dir / "generation_manifest.json"),
            "oom": bool(train_summary.get("oom") or generation.get("oom")),
        }
    )
    _write_json(row_dir / "training_manifest.json", train_summary)
    _write_json(row_dir / "generation_manifest.json", generation)
    return _write_row_outputs(row_dir, row_summary, args=args)


def _run_train(
    train_dir: Path,
    *,
    config: dict[str, Any],
    args: argparse.Namespace,
    train_limit: int,
    row: RowSpec,
) -> dict[str, Any]:
    schema = load_schema(args.dataset, data_root=_data_root(args, config))
    documents = load_documents(
        args.dataset,
        args.train_split,
        data_root=_data_root(args, config),
        mode="train",
        limit=train_limit,
    )
    rows = _build_sft_rows(documents, schema=schema, config=config, row=row)
    sft_path = write_jsonl(train_dir / "intermediate" / f"getm_sft.{args.train_split}.jsonl", rows)
    target_audit = audit_sft_targets(rows, schema)
    manifest = train_sft(config, rows, train_dir)
    manifest = {**manifest, "sft_data": str(sft_path), "sft_target_audit": target_audit}
    _write_json(train_dir / "training_manifest.json", manifest)
    return {
        "row_id": row.row_id,
        "train_manifest_path": str(train_dir / "training_manifest.json"),
        "adapter_path": manifest.get("adapter_dir"),
        "train_rows": manifest.get("train_rows", len(rows)),
        "train_examples_seen": manifest.get("train_examples", manifest.get("train_rows", len(rows))),
        "num_train_epochs": (((config.get("getm") or {}).get("qwen") or {}).get("training") or {}).get(
            "num_train_epochs"
        ),
        "train_runtime": manifest.get("train_runtime"),
        "train_loss_final": manifest.get("train_loss"),
        "train_loss_mean": manifest.get("train_loss"),
        "telemetry": _telemetry_summary(train_dir),
        "oom": _has_oom(train_dir),
    }


def _run_generate(
    run_dir: Path,
    *,
    config: dict[str, Any],
    args: argparse.Namespace,
    row: RowSpec,
    adapter_path: str,
) -> dict[str, Any]:
    run_dir.mkdir(parents=True, exist_ok=True)
    schema = load_schema(args.dataset, data_root=_data_root(args, config))
    documents = load_documents(args.dataset, args.eval_split, data_root=_data_root(args, config), mode="predict")
    surface_memories = None
    if row.surface == "v21_surface_opt_in_r2":
        surface_memories = {
            document.doc_id: build_v21_surface_memory(document.input, enable_v21_rules=True)
            for document in documents
        }
    telemetry = start_qwen_telemetry(
        config,
        run_dir,
        operation=f"v21_r3_{row.row_id}_generate",
        total_items=len(documents),
    )
    backend: QwenGetmBackend | None = None
    try:
        backend = QwenGetmBackend(config=config, telemetry=telemetry)
        output = generate_getm_candidate_files(
            documents=documents,
            dataset=args.dataset,
            split=args.eval_split,
            schema=schema,
            backend=backend,
            k=1,
            out_dir=run_dir,
            surface_memories=surface_memories,
        )
    finally:
        _release_qwen_backend(backend)
        gc.collect()
        telemetry.finish()
    write_yaml(run_dir / "config.resolved.yaml", config)
    _write_json(
        run_dir / "run_manifest.json",
        _prediction_manifest(config, args=args, row=row, adapter_path=adapter_path),
    )
    _write_json(
        run_dir / "generation_manifest.json",
        {
            "diagnostic_version": DIAGNOSTIC_VERSION,
            "backend": "qwen",
            "dry_run": bool(args.dry_run),
            "real_run": not bool(args.dry_run),
            "row_id": row.row_id,
            "surface": row.surface,
            "dataset": args.dataset,
            "split": args.eval_split,
            "document_count": len(documents),
            "k": 1,
            "prompts_path": str(output.prompts_path),
            "raw_outputs_path": str(output.raw_outputs_path),
            "parsed_candidates_path": str(output.parsed_candidates_path),
            "parse_diagnostics_path": str(output.parse_diagnostics_path),
            "canonical_predictions_path": str(output.canonical_predictions_path),
            "gold_visible": False,
            "test_run": False,
            "generation": _generation_metadata(config),
        },
    )
    summary = _summarize_generation(run_dir, dataset=args.dataset, split=args.eval_split)
    summary["generation_manifest_path"] = str(run_dir / "generation_manifest.json")
    return summary


def _run_evaluator(run_dir: Path, *, args: argparse.Namespace) -> dict[str, Any]:
    out_dir = args.out_root / "evaluator_artifacts" / run_dir.parent.name
    if args.dry_run or args.skip_evaluator:
        return {
            "attempted": False,
            "returncode": None,
            "evaluator_artifact_root": None,
            "evaluator_artifact_out_dir": str(out_dir),
            "evaluator_validation_ok": None,
            "event_table_micro_f1": None,
            "role_level_f1": None,
            "exact_record_f1": None,
        }
    handoff = build_evaluator_handoff(
        run_root=run_dir,
        dataset=args.dataset,
        split=args.eval_split,
        data_repo_root=args.evaluator_root,
        out_dir=out_dir,
        benchmark_root=args.benchmark_root,
        strict=True,
    )
    result = run_evaluator_handoff(handoff)
    _write_json(run_dir / "v21_r3_evaluator_handoff.json", {"handoff": handoff.to_dict(), "result": result})
    artifact_root = _extract_artifact_root(result.get("stdout"))
    metrics = _read_evaluator_metrics(artifact_root, dataset=args.dataset, split=args.eval_split)
    return {
        "attempted": result.get("attempted"),
        "returncode": result.get("returncode"),
        "evaluator_artifact_out_dir": str(out_dir),
        "evaluator_artifact_root": artifact_root,
        "evaluator_validation_ok": metrics.get("validation_ok"),
        "event_table_micro_f1": metrics.get("event_table_micro_f1"),
        "role_level_f1": metrics.get("role_level_f1"),
        "exact_record_f1": metrics.get("exact_record_f1"),
        "stdout": result.get("stdout"),
        "stderr": result.get("stderr"),
    }


def _build_sft_rows(
    documents: list[V2DatasetDocument],
    *,
    schema: Any,
    config: dict[str, Any],
    row: RowSpec,
) -> list[dict[str, Any]]:
    rows = []
    prompt_options = dict((config.get("getm") or {}).get("prompt") or {})
    for document in documents:
        if row.surface == "v21_surface_opt_in_r2":
            memory = build_v21_surface_memory(document.input, enable_v21_rules=True)
        else:
            memory = build_surface_memory(document.input)
        rows.append(
            build_getm_sft_sample(
                document,
                schema,
                surface_candidates=memory.candidates,
                slot_plan=None,
                output_format=str((config.get("getm") or {}).get("output_format") or "minimal_text"),
                prompt_options=prompt_options,
            )
        )
    return rows


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
        "accepted_event_count": int(diagnostic_counts.get("accepted_event_count", 0) or 0),
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


def _base_row_summary(row: RowSpec, *, args: argparse.Namespace, train_limit: int) -> dict[str, Any]:
    return {
        "phase": "R3 S4 train-size scaling",
        "row_id": row.row_id,
        "system": "S4",
        "seed": 42,
        "dataset": args.dataset,
        "split": args.eval_split,
        "surface": row.surface,
        "secondary": row.secondary,
        "conditional": row.conditional,
        "train_limit": train_limit,
        "dev_only": True,
        "seed42_only": True,
        "s4_only": True,
        "test_run": False,
        "test_gold_read": False,
        "seed43_44_run": False,
        "frozen_final_modified": False,
    }


def _write_row_outputs(row_dir: Path, row_summary: dict[str, Any], *, args: argparse.Namespace) -> dict[str, Any]:
    row_summary["row_manifest_path"] = str(row_dir / "row_manifest.json")
    _write_json(row_dir / "row_summary.json", row_summary)
    _write_json(
        row_dir / "row_manifest.json",
        {
            "phase": "R3 S4 train-size scaling",
            "row_id": row_summary["row_id"],
            "dataset": args.dataset,
            "split": args.eval_split,
            "seed": 42,
            "system": "S4",
            "surface": row_summary.get("surface"),
            "train_limit": row_summary.get("train_limit"),
            "train_run": bool(row_summary.get("train_run")),
            "generation_run": bool(row_summary.get("generation_run")),
            "evaluator_run": bool(row_summary.get("evaluator_artifact_path")),
            "test_run": False,
            "test_gold_read": False,
            "seed43_44_run": False,
            "frozen_final_modified": False,
            "created_at": _created_at(),
        },
    )
    return row_summary


def _resolved_config(
    config: dict[str, Any],
    *,
    args: argparse.Namespace,
    row: RowSpec,
    train_limit: int,
    adapter_path: str | None,
) -> dict[str, Any]:
    resolved = deepcopy(config)
    run_cfg = dict(resolved.get("run") or {})
    run_cfg.update(
        {
            "profile": f"v21_r3_{row.row_id}",
            "row_id": row.row_id,
            "dry_run": bool(args.dry_run),
            "real_run": not bool(args.dry_run),
        }
    )
    resolved["run"] = run_cfg
    data_cfg = dict(resolved.get("data") or {})
    data_cfg.update(
        {
            "dataset": args.dataset,
            "data_root": _data_root(args, resolved),
            "train_split": args.train_split,
            "eval_split": args.eval_split,
            "max_train_docs": train_limit,
            "max_predict_docs": None,
        }
    )
    resolved["data"] = data_cfg
    predict_cfg = dict(resolved.get("predict") or {})
    predict_cfg.update(
        {
            "dataset": args.dataset,
            "split": args.eval_split,
            "data_root": _data_root(args, resolved),
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
    if adapter_path:
        resolved.setdefault("getm", {}).setdefault("qwen", {})["adapter_path"] = adapter_path
    if row.surface == "v21_surface_opt_in_r2":
        resolved["surface_memory"] = {"v21_opt_in": True, "source": "R2 explicit opt-in"}
    return resolved


def _resolved_train_limit(row: RowSpec, *, args: argparse.Namespace, config: dict[str, Any]) -> int:
    if isinstance(row.train_limit, int):
        return row.train_limit
    r3 = config.get("r3") or {}
    configured = r3.get("max_affordable_train_limit") or r3.get("full_train_limit")
    if configured is not None:
        return int(configured)
    return len(load_documents(args.dataset, args.train_split, data_root=_data_root(args, config), mode="train"))


def _prediction_manifest(
    config: dict[str, Any],
    *,
    args: argparse.Namespace,
    row: RowSpec,
    adapter_path: str,
) -> dict[str, Any]:
    return {
        "run_id": f"v21_r3_{row.row_id}_{_created_slug()}",
        "method_name": "SAGE-DEE-v2.1-R3-S4",
        "method_family": "SAGE-DEE-v2",
        "stage": "predict",
        "dataset_version": args.dataset,
        "split_version": args.eval_split,
        "evaluator_version": EVALUATOR_VERSION,
        "prediction_format": PREDICTION_FORMAT,
        "training_view": "evaluator_gold/train",
        "gold_view": f"processed/views/evaluator_gold/{args.dataset}",
        "seed": 42,
        "backend": "qwen",
        "dry_run": bool(args.dry_run),
        "real_run": not bool(args.dry_run),
        "profile": (config.get("run") or {}).get("profile"),
        "row_id": row.row_id,
        "adapter_path": adapter_path,
        "command_train": None,
        "command_infer": join([sys.executable, "scripts/v2/run_v21_r3_s4_train_size_scaling.py"]),
        "git_commit": _git_commit(),
        "created_at": _created_at(),
        "notes": "R3 dev-only seed42 S4 train-size diagnostic; test split remains blocked.",
    }


def _read_evaluator_metrics(artifact_root: str | None, *, dataset: str, split: str) -> dict[str, Any]:
    if not artifact_root:
        return {}
    root = Path(artifact_root)
    overall_path = root / "metrics" / "unified_main" / dataset / split / "overall_metrics.json"
    record_path = root / "analysis" / dataset / split / "record_level_metrics.json"
    validation_path = root / "analysis" / dataset / split / "validation_report.json"
    metrics: dict[str, Any] = {}
    if overall_path.is_file():
        overall = _read_json(overall_path)
        metrics["event_table_micro_f1"] = overall.get("f1")
        metrics["role_level_f1"] = overall.get("f1")
    if record_path.is_file():
        record = _read_json(record_path)
        metrics["exact_record_f1"] = record.get("record_f1_exact")
    if validation_path.is_file():
        validation = _read_json(validation_path)
        metrics["validation_ok"] = validation.get("ok")
    return metrics


def _require_gate_documents() -> None:
    for path in (R0_REPORT, R1_REPORT, R2_REPORT, DEV_RESCUE_PLAN, CHANGELOG):
        if not path.is_file():
            raise ValueError(f"missing R3 gate document: {path}")
    r1 = R1_REPORT.read_text(encoding="utf-8")
    r2 = R2_REPORT.read_text(encoding="utf-8")
    if "not_main_cause" not in r1:
        raise ValueError("R1 gate missing parser strictness not_main_cause decision")
    if "0.362816" not in r2 and not ("0.35" in r2 and "0.45" in r2):
        raise ValueError("R2 gate missing candidate coverage in 0.35-0.45 range")
    if "0.098267" not in r2 and "p90 budget ratio" not in r2:
        raise ValueError("R2 gate missing prompt-budget proxy")
    if "did not read test gold" not in r2:
        raise ValueError("R2 gate missing no test-gold-leakage statement")


def _require_r2_budget(config: dict[str, Any]) -> None:
    del config
    r2 = R2_REPORT.read_text(encoding="utf-8")
    if "0.098267" not in r2:
        raise RuntimeError("v21 Row C blocked: R2 budget evidence missing")


def _require_final_result_clean() -> None:
    completed = subprocess.run(
        ["git", "diff", "--quiet", "--", str(FINAL_RESULT.relative_to(REPO_ROOT))],
        cwd=REPO_ROOT,
        check=False,
    )
    if completed.returncode != 0:
        raise ValueError("R3 refuses to run while frozen final result has local modifications")


def _split_csv(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def _data_root(args: argparse.Namespace, config: dict[str, Any]) -> str:
    return str(args.data_root or ((config.get("data") or {}).get("data_root")) or "data")


def _peak_vram(*telemetries: Any) -> dict[str, Any]:
    peaks = []
    for telemetry in telemetries:
        gpu = ((telemetry or {}).get("gpu_memory_summary") or {})
        value = gpu.get("max_peak_memory_used_gb")
        if isinstance(value, (int, float)):
            peaks.append(float(value))
    return {"max_peak_memory_used_gb": max(peaks) if peaks else None}


def _elapsed_sec(telemetry: Any) -> float | None:
    timing = ((telemetry or {}).get("timing_summary") or {})
    value = timing.get("elapsed_sec")
    return float(value) if isinstance(value, (int, float)) else None


def _has_oom(run_dir: Path) -> bool:
    text = "\n".join(path.read_text(encoding="utf-8", errors="ignore") for path in run_dir.glob("*.stderr.log"))
    lowered = text.lower()
    return "outofmemory" in lowered or "out of memory" in lowered or "cuda oom" in lowered


def _number(value: Any) -> float:
    if isinstance(value, bool) or value is None:
        return 0.0
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _read_json(path: str | Path) -> dict[str, Any]:
    with Path(path).open(encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object: {path}")
    return payload


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _created_at() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _created_slug() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _git_commit() -> str | None:
    completed = subprocess.run(["git", "rev-parse", "HEAD"], cwd=REPO_ROOT, check=False, capture_output=True, text=True)
    commit = completed.stdout.strip()
    return commit if completed.returncode == 0 and commit else None


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


if __name__ == "__main__":
    raise SystemExit(main())
