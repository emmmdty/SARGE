from __future__ import annotations

import argparse
import gc
import json
import os
import random
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
from sage_dee.v2.contracts.surface import SurfaceMemory  # noqa: E402
from sage_dee.v2.data_interface.dataset_loader import V2DatasetDocument, load_documents  # noqa: E402
from sage_dee.v2.data_interface.jsonl import read_jsonl, write_jsonl  # noqa: E402
from sage_dee.v2.data_interface.schema_registry import load_schema  # noqa: E402
from sage_dee.v2.getm.candidate_generator import generate_getm_candidate_files  # noqa: E402
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
from scripts.v2.run_phase6_sft_baseline_matrix import (  # noqa: E402
    _canonical_validation,
    _extract_artifact_root,
    _release_qwen_backend,
    _telemetry_summary,
)

ALLOWED_SYSTEMS = {"S2", "S3"}
ALLOWED_SEEDS = {42, 43, 44}
SYSTEM_BASELINE_MODES = {"S2": "schema_only", "S3": "role_safe"}
FINAL_RESULT = REPO_ROOT / "docs/refactor/SAGE_V2_FINAL_TEST_RESULT.json"
R6_REPORT = REPO_ROOT / "docs/refactor/SAGE_V2_1_R6_SEED_EXTENSION_FULLMAX_S4.md"
R5_REPORT = REPO_ROOT / "docs/refactor/SAGE_V2_1_R5_SINGLE_SEED_RESCUE_DECISION.md"
R3_REPORT = REPO_ROOT / "docs/refactor/SAGE_V2_1_R3_S4_TRAIN_SIZE_SCALING.md"
CHANGELOG = REPO_ROOT / "docs/refactor/SAGE_V2_1_DEV_RESCUE_CHANGELOG.md"


@dataclass(frozen=True)
class RowSpec:
    system: str
    seed: int
    train_limit: int | str = "full_or_max"
    surface: str = "none"


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    config = read_yaml(args.config)
    try:
        _validate_args(args, config)
        if args.evaluator_root is None:
            args.evaluator_root = Path(str(config.get("evaluator_root") or "/home/TJK/DEE/dee-eval"))
        args.out_root.mkdir(parents=True, exist_ok=True)
        spec = RowSpec(system=args.system, seed=args.seed, surface=args.surface)
        summary = _run_row(spec, args=args, config=config)
    except (RuntimeError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2

    print(f"system={args.system}")
    print(f"seed={args.seed}")
    print(f"run_root={args.out_root}")
    print(f"row_summary={args.out_root / 'row_summary.json'}")
    print(f"event_table_micro_f1={summary.get('event_table_micro_f1')}")
    print(f"exact_record_f1={summary.get('exact_record_f1')}")
    return 0


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run SAGE v2.1 R7 S2/S3 full/max thesis matrix rows on dev.")
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--dataset", required=True)
    parser.add_argument("--eval-split", default="dev")
    parser.add_argument("--train-split", default="train")
    parser.add_argument("--data-root")
    parser.add_argument("--system", required=True)
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--surface", default="none")
    parser.add_argument("--planner", default="none")
    parser.add_argument("--gpu-id")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--allow-missing-gate-for-local-test", action="store_true")
    parser.add_argument("--skip-evaluator", action="store_true")
    parser.add_argument("--evaluator-root", type=Path)
    parser.add_argument("--benchmark-root", type=Path, default=Path("/data/TJK/DEE/data/processed"))
    parser.add_argument("--out-root", type=Path, required=True)
    return parser.parse_args(argv)


def _validate_args(args: argparse.Namespace, config: dict[str, Any]) -> None:
    system = str(args.system).upper()
    args.system = system
    if args.eval_split == "test":
        raise ValueError("R7 rejects test split")
    if args.eval_split != "dev":
        raise ValueError(f"R7 only permits dev eval split, got {args.eval_split!r}")
    if args.train_split != "train":
        raise ValueError("R7 training split must be train")
    if args.dataset != "DuEE-Fin-dev500":
        raise ValueError("R7 is restricted to DuEE-Fin-dev500")
    if system == "S1":
        raise ValueError("R7 rejects S1")
    if system == "S4":
        raise ValueError("R7 rejects S4 retrain; reuse R6/R3 S4 artifacts")
    if system not in ALLOWED_SYSTEMS:
        raise ValueError("R7 only accepts S2/S3 systems")
    if args.seed not in ALLOWED_SEEDS:
        raise ValueError("R7 only permits seeds 42/43/44")
    if str(args.surface).lower() not in {"", "none", "no_surface", "schema_only"}:
        raise ValueError("R7 rejects v21 surface and only permits no surface for S2/S3")
    if str(args.planner).lower() not in {"", "none"}:
        raise ValueError("R7 rejects R4b planner")
    _validate_config(config)
    if not args.allow_missing_gate_for_local_test:
        _require_gate_documents(config)
    _require_final_result_clean()


def _validate_config(config: dict[str, Any]) -> None:
    if config.get("phase") != "R7":
        raise ValueError("R7 config must declare phase R7")
    if config.get("dataset") != "DuEE-Fin-dev500":
        raise ValueError("R7 config must use DuEE-Fin-dev500")
    if config.get("eval_split") != "dev" or config.get("train_split") != "train":
        raise ValueError("R7 config must use train/dev")
    if config.get("allow_test") is not False or config.get("no_test") is not True:
        raise ValueError("R7 config must keep test disabled")
    for key in ("no_s1", "no_v21_surface", "no_r4b_planner", "no_s4_retrain"):
        if config.get(key) is not True:
            raise ValueError(f"R7 config must set {key}=true")
    if config.get("systems_to_run") != ["S2", "S3"]:
        raise ValueError("R7 config must run only S2/S3")
    if config.get("systems_to_reuse") != ["S4"]:
        raise ValueError("R7 config must reuse S4 only")
    if config.get("seeds") != [42, 43, 44]:
        raise ValueError("R7 config must list seeds 42/43/44")
    if int(config.get("expected_train_limit") or 0) != 6474:
        raise ValueError("R7 expected train limit must be 6474")
    systems = config.get("systems") or {}
    for system, mode in SYSTEM_BASELINE_MODES.items():
        system_cfg = systems.get(system) or {}
        prompt_cfg = system_cfg.get("prompt") or {}
        if system_cfg.get("baseline_mode") != mode or prompt_cfg.get("baseline_mode") != mode:
            raise ValueError(f"R7 {system} must use baseline_mode={mode}")
        if system_cfg.get("surface") != "none":
            raise ValueError(f"R7 {system} must declare surface none")


def _run_row(spec: RowSpec, *, args: argparse.Namespace, config: dict[str, Any]) -> dict[str, Any]:
    train_limit = _resolved_train_limit(spec, args=args, config=config)
    if args.dry_run:
        return _run_row_dry(spec, args=args, train_limit=train_limit)

    train_config = _resolved_config(config, args=args, spec=spec, train_limit=train_limit, adapter_path=None)
    write_yaml(args.out_root / "config.resolved.train.yaml", train_config)
    train_summary = _run_train(
        args.out_root / "train",
        config=train_config,
        args=args,
        spec=spec,
        train_limit=train_limit,
    )
    adapter_path = str(train_summary.get("adapter_path") or "")
    if not adapter_path:
        raise RuntimeError(f"R7 {spec.system} seed{spec.seed} training did not produce an adapter path")

    generation_config = _resolved_config(
        config,
        args=args,
        spec=spec,
        train_limit=train_limit,
        adapter_path=adapter_path,
    )
    write_yaml(args.out_root / "config.resolved.generate.yaml", generation_config)
    generation = _run_generate(
        args.out_root / "full_dev",
        config=generation_config,
        args=args,
        spec=spec,
        adapter_path=adapter_path,
    )
    evaluator = _run_evaluator(args.out_root / "full_dev", args=args, spec=spec)
    summary = _base_row_summary(spec, args=args, train_limit=train_limit)
    summary.update(
        {
            "train_run": True,
            "generation_run": True,
            "evaluator_run": bool(evaluator.get("attempted")),
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
            "training_manifest_path": str(args.out_root / "training_manifest.json"),
            "generation_manifest_path": str(args.out_root / "generation_manifest.json"),
            "oom": bool(train_summary.get("oom") or generation.get("oom")),
        }
    )
    _write_json(args.out_root / "training_manifest.json", train_summary)
    _write_json(args.out_root / "generation_manifest.json", generation)
    return _write_row_outputs(args.out_root, summary, args=args)


def _run_row_dry(spec: RowSpec, *, args: argparse.Namespace, train_limit: int) -> dict[str, Any]:
    train_manifest = {
        "phase": "R7 thesis minimal matrix",
        "system": spec.system,
        "seed": spec.seed,
        "train_run": False,
        "dry_run": True,
        "train_limit": train_limit,
        "adapter_path": "dry-run-no-adapter",
        "test_run": False,
    }
    generation_manifest = {
        "phase": "R7 thesis minimal matrix",
        "system": spec.system,
        "seed": spec.seed,
        "generation_run": False,
        "dry_run": True,
        "split": args.eval_split,
        "surface": spec.surface,
        "test_run": False,
        "gold_visible": False,
    }
    summary = _base_row_summary(spec, args=args, train_limit=train_limit)
    summary.update(
        {
            "train_run": False,
            "generation_run": False,
            "evaluator_run": False,
            "adapter_path": "dry-run-no-adapter",
            "prediction_path": None,
            "evaluator_artifact_path": None,
            "training_manifest_path": str(args.out_root / "training_manifest.json"),
            "generation_manifest_path": str(args.out_root / "generation_manifest.json"),
        }
    )
    _write_json(args.out_root / "training_manifest.json", train_manifest)
    _write_json(args.out_root / "generation_manifest.json", generation_manifest)
    return _write_row_outputs(args.out_root, summary, args=args)


def _run_train(
    train_dir: Path,
    *,
    config: dict[str, Any],
    args: argparse.Namespace,
    train_limit: int,
    spec: RowSpec,
) -> dict[str, Any]:
    _apply_seed(spec.seed)
    schema = load_schema(args.dataset, data_root=_data_root(args, config))
    documents = load_documents(
        args.dataset,
        args.train_split,
        data_root=_data_root(args, config),
        mode="train",
        limit=train_limit,
    )
    rows = _build_sft_rows(documents, schema=schema, config=config)
    sft_path = write_jsonl(train_dir / "intermediate" / f"getm_sft.{args.train_split}.jsonl", rows)
    target_audit = audit_sft_targets(rows, schema)
    manifest = train_sft(config, rows, train_dir)
    manifest = {
        **manifest,
        "phase": "R7 thesis minimal matrix",
        "system": spec.system,
        "seed": spec.seed,
        "sft_data": str(sft_path),
        "sft_target_audit": target_audit,
        "surface": spec.surface,
        "baseline_mode": SYSTEM_BASELINE_MODES[spec.system],
        "test_run": False,
    }
    _write_json(train_dir / "training_manifest.json", manifest)
    return {
        "system": spec.system,
        "seed": spec.seed,
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
    spec: RowSpec,
    adapter_path: str,
) -> dict[str, Any]:
    _apply_seed(spec.seed)
    run_dir.mkdir(parents=True, exist_ok=True)
    schema = load_schema(args.dataset, data_root=_data_root(args, config))
    documents = load_documents(args.dataset, args.eval_split, data_root=_data_root(args, config), mode="predict")
    telemetry = start_qwen_telemetry(
        config,
        run_dir,
        operation=f"v21_r7_{spec.system}_seed{spec.seed}_generate",
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
            surface_memories=_empty_surface_memories(documents),
        )
    finally:
        _release_qwen_backend(backend)
        gc.collect()
        telemetry.finish()
    write_yaml(run_dir / "config.resolved.yaml", config)
    _write_json(
        run_dir / "run_manifest.json",
        _prediction_manifest(config, args=args, spec=spec, adapter_path=adapter_path),
    )
    _write_json(
        run_dir / "generation_manifest.json",
        {
            "diagnostic_version": DIAGNOSTIC_VERSION,
            "backend": "qwen",
            "dry_run": bool(args.dry_run),
            "real_run": not bool(args.dry_run),
            "phase": "R7 thesis minimal matrix",
            "system": spec.system,
            "seed": spec.seed,
            "surface": spec.surface,
            "baseline_mode": SYSTEM_BASELINE_MODES[spec.system],
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
            "v21_surface_run": False,
            "r4b_planner_run": False,
            "s1_run": False,
            "s4_retrained": False,
            "generation": _generation_metadata(config),
        },
    )
    summary = _summarize_generation(run_dir, dataset=args.dataset, split=args.eval_split)
    summary["generation_manifest_path"] = str(run_dir / "generation_manifest.json")
    return summary


def _run_evaluator(run_dir: Path, *, args: argparse.Namespace, spec: RowSpec) -> dict[str, Any]:
    out_dir = args.out_root / "evaluator_artifacts" / f"{spec.system}_seed{spec.seed}"
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
    _write_json(run_dir / "v21_r7_evaluator_handoff.json", {"handoff": handoff.to_dict(), "result": result})
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
) -> list[dict[str, Any]]:
    rows = []
    prompt_options = dict((config.get("getm") or {}).get("prompt") or {})
    for document in documents:
        rows.append(
            build_getm_sft_sample(
                document,
                schema,
                surface_candidates=[],
                slot_plan=None,
                output_format=str((config.get("getm") or {}).get("output_format") or "minimal_text"),
                prompt_options=prompt_options,
            )
        )
    return rows


def _empty_surface_memories(documents: list[V2DatasetDocument]) -> dict[str, SurfaceMemory]:
    return {
        document.doc_id: SurfaceMemory(doc_id=document.doc_id, candidates=[], source="r7_no_surface")
        for document in documents
    }


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


def _base_row_summary(spec: RowSpec, *, args: argparse.Namespace, train_limit: int) -> dict[str, Any]:
    return {
        "phase": "R7 thesis minimal matrix",
        "system": spec.system,
        "seed": spec.seed,
        "dataset": args.dataset,
        "split": args.eval_split,
        "surface": spec.surface,
        "baseline_mode": SYSTEM_BASELINE_MODES[spec.system],
        "train_limit": train_limit,
        "dev_only": True,
        "test_run": False,
        "test_gold_read": False,
        "s1_run": False,
        "s4_retrained": False,
        "v21_surface_run": False,
        "r4b_planner_run": False,
        "chfinann_run": False,
        "docfee_run": False,
        "frozen_final_modified": False,
        "gpu_id_metadata": args.gpu_id,
    }


def _write_row_outputs(row_dir: Path, summary: dict[str, Any], *, args: argparse.Namespace) -> dict[str, Any]:
    summary["row_summary_path"] = str(row_dir / "row_summary.json")
    _write_json(row_dir / "row_summary.json", summary)
    _write_json(
        row_dir / "row_manifest.json",
        {
            "phase": "R7 thesis minimal matrix",
            "system": summary["system"],
            "seed": summary["seed"],
            "dataset": args.dataset,
            "split": args.eval_split,
            "surface": summary.get("surface"),
            "baseline_mode": summary.get("baseline_mode"),
            "train_limit": summary.get("train_limit"),
            "train_run": bool(summary.get("train_run")),
            "generation_run": bool(summary.get("generation_run")),
            "evaluator_run": bool(summary.get("evaluator_run")),
            "test_run": False,
            "test_gold_read": False,
            "s1_run": False,
            "s4_retrained": False,
            "v21_surface_run": False,
            "r4b_planner_run": False,
            "frozen_final_modified": False,
            "created_at": _created_at(),
        },
    )
    return summary


def _resolved_config(
    config: dict[str, Any],
    *,
    args: argparse.Namespace,
    spec: RowSpec,
    train_limit: int,
    adapter_path: str | None,
) -> dict[str, Any]:
    resolved = deepcopy(config)
    system_cfg = ((resolved.get("systems") or {}).get(spec.system) or {})
    prompt_override = dict(system_cfg.get("prompt") or {})
    resolved.pop("systems", None)
    resolved["seed"] = spec.seed
    run_cfg = dict(resolved.get("run") or {})
    run_cfg.update(
        {
            "profile": str(system_cfg.get("profile") or f"v21_r7_{spec.system.lower()}_fullmax"),
            "phase": "R7",
            "system": spec.system,
            "seed": spec.seed,
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
    prompt = dict((resolved.get("getm") or {}).get("prompt") or {})
    prompt.update(prompt_override)
    prompt["baseline_mode"] = SYSTEM_BASELINE_MODES[spec.system]
    prompt["max_surface_candidates"] = 0
    prompt["enable_candidate_filtering"] = False
    prompt["max_candidates_per_type"] = None
    prompt["dedupe_surface_candidates"] = False
    prompt["drop_low_value_company_fragments"] = False
    resolved.setdefault("getm", {})["prompt"] = prompt
    generation = dict((resolved.get("getm") or {}).get("generation") or {})
    generation.update(
        {
            "seed": spec.seed,
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
    training = dict(((resolved.get("getm") or {}).get("qwen") or {}).get("training") or {})
    training["seed"] = spec.seed
    resolved.setdefault("getm", {}).setdefault("qwen", {})["training"] = training
    if adapter_path:
        resolved.setdefault("getm", {}).setdefault("qwen", {})["adapter_path"] = adapter_path
    return resolved


def _resolved_train_limit(spec: RowSpec, *, args: argparse.Namespace, config: dict[str, Any]) -> int:
    del spec
    if args.dry_run:
        return int(config.get("expected_train_limit") or 6474)
    configured = (config.get("r7") or {}).get("train_limit", config.get("train_limit"))
    if isinstance(configured, int):
        return configured
    return len(load_documents(args.dataset, args.train_split, data_root=_data_root(args, config), mode="train"))


def _prediction_manifest(
    config: dict[str, Any],
    *,
    args: argparse.Namespace,
    spec: RowSpec,
    adapter_path: str,
) -> dict[str, Any]:
    return {
        "run_id": f"v21_r7_{spec.system}_seed{spec.seed}_{_created_slug()}",
        "method_name": f"SAGE-DEE-v2.1-R7-{spec.system}",
        "method_family": "SAGE-DEE-v2",
        "stage": "predict",
        "dataset_version": args.dataset,
        "split_version": args.eval_split,
        "evaluator_version": EVALUATOR_VERSION,
        "prediction_format": PREDICTION_FORMAT,
        "training_view": "evaluator_gold/train",
        "gold_view": f"processed/views/evaluator_gold/{args.dataset}",
        "seed": spec.seed,
        "backend": "qwen",
        "dry_run": bool(args.dry_run),
        "real_run": not bool(args.dry_run),
        "profile": (config.get("run") or {}).get("profile"),
        "system": spec.system,
        "surface": spec.surface,
        "baseline_mode": SYSTEM_BASELINE_MODES[spec.system],
        "adapter_path": adapter_path,
        "command_train": None,
        "command_infer": join([sys.executable, "scripts/v2/run_v21_r7_thesis_minimal_matrix.py"]),
        "git_commit": _git_commit(),
        "created_at": _created_at(),
        "notes": (
            "R7 dev-only S2/S3 thesis minimal matrix row; test, S1, S4 retrain, "
            "v21 surface, and R4b planner remain blocked."
        ),
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


def _require_gate_documents(config: dict[str, Any]) -> None:
    for path in (R6_REPORT, R5_REPORT, R3_REPORT, CHANGELOG):
        if not path.is_file():
            raise ValueError(f"missing R7 gate document: {path}")
    r6_text = R6_REPORT.read_text(encoding="utf-8")
    if "recommended_next_phase: `R7_thesis_package_minimal_matrix`" not in r6_text:
        raise ValueError("R6 report does not recommend R7_thesis_package_minimal_matrix")
    r6_root = Path(str(config.get("r6_s4_artifact_root") or ""))
    r3_root = Path(str(config.get("r3_s4_seed42_artifact_root") or ""))
    _validate_r6_evidence(r6_root, r3_root)


def _validate_r6_evidence(r6_root: Path, r3_root: Path) -> None:
    summary_path = r6_root / "v21_r6_seed_extension_summary.json"
    if not summary_path.is_file():
        raise ValueError(f"missing R6 summary: {summary_path}")
    summary = _read_json(summary_path)
    metrics = summary.get("metrics") or {}
    if summary.get("recommended_next_phase") != "R7_thesis_package_minimal_matrix":
        raise ValueError("R6 summary does not recommend R7")
    if float(metrics.get("mean_event_role_f1") or 0.0) < 0.70:
        raise ValueError("R6 mean_event_role_f1 is below R7 gate")
    if float(metrics.get("mean_exact_record_f1") or 0.0) < 0.30:
        raise ValueError("R6 mean_exact_record_f1 is below R7 gate")
    for seed in (43, 44):
        if not (r6_root / f"seed{seed}" / "seed_summary.json").is_file():
            raise ValueError(f"missing R6 S4 seed{seed} evidence")
    if not (r3_root / "s4_full_or_max_frozen_surface" / "row_summary.json").is_file():
        raise ValueError("missing R3 S4 seed42 Row D evidence")


def _require_final_result_clean() -> None:
    completed = subprocess.run(
        ["git", "diff", "--quiet", "--", str(FINAL_RESULT.relative_to(REPO_ROOT))],
        cwd=REPO_ROOT,
        check=False,
    )
    if completed.returncode != 0:
        raise ValueError("R7 refuses to run while frozen final result has local modifications")


def _apply_seed(seed: int) -> None:
    random.seed(seed)
    os.environ.setdefault("PYTHONHASHSEED", str(seed))
    try:
        import numpy

        numpy.random.seed(seed)
    except Exception:
        pass
    try:
        import torch

        torch.manual_seed(seed)
        if torch.cuda.is_available():
            torch.cuda.manual_seed_all(seed)
    except Exception:
        pass
    try:
        import transformers

        transformers.set_seed(seed)
    except Exception:
        pass


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


if __name__ == "__main__":
    raise SystemExit(main())
