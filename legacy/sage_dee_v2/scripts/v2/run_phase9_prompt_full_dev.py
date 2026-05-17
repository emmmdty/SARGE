from __future__ import annotations

import argparse
import gc
import hashlib
import json
import os
import shutil
import sys
from collections.abc import Sequence
from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from shlex import join
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))

from sage_dee.io_utils import read_yaml, write_yaml  # noqa: E402
from sage_dee.v2.data_interface.dataset_loader import load_documents  # noqa: E402
from sage_dee.v2.data_interface.jsonl import read_jsonl, write_jsonl  # noqa: E402
from sage_dee.v2.data_interface.schema_registry import load_schema  # noqa: E402
from sage_dee.v2.getm.candidate_generator import generate_getm_candidate_files  # noqa: E402
from sage_dee.v2.getm.generation_diagnostics import DIAGNOSTIC_VERSION  # noqa: E402
from sage_dee.v2.getm.mock_backend import MockGetmBackend  # noqa: E402
from sage_dee.v2.getm.qwen_backend import QwenGetmBackend, _generation_metadata, start_qwen_telemetry  # noqa: E402
from sage_dee.v2.pipeline.evaluator_handoff import build_evaluator_handoff, run_evaluator_handoff  # noqa: E402
from sage_dee.v2.pipeline.export_canonical import validate_minimal_canonical_prediction  # noqa: E402
from sage_dee.v2.pipeline.run_manifest import EVALUATOR_VERSION, PREDICTION_FORMAT  # noqa: E402


@dataclass(frozen=True)
class BaselineSpec:
    baseline_id: str
    profile: str
    label: str
    baseline_mode: str


@dataclass(frozen=True)
class RunSpec:
    baseline: BaselineSpec
    seed: int


BASELINES = (
    BaselineSpec("P1", "phase4_p1_direct_json", "direct prompt-to-JSON", "direct_json"),
    BaselineSpec("P2", "phase4_p2_schema_only", "schema-only prompt", "schema_only"),
    BaselineSpec("P3", "phase4_p3_role_safe", "role-safe prompt", "role_safe"),
    BaselineSpec(
        "P4",
        "phase4_p4_role_safe_surface_memory",
        "role-safe + surface memory prompt",
        "role_safe_surface_memory",
    ),
)
BASELINE_BY_ID = {baseline.baseline_id: baseline for baseline in BASELINES}
DEFAULT_SEEDS = (42, 43, 44)
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
    config = read_yaml(args.config)
    try:
        _validate_args(args)
        phase4_gate = _require_phase4_limit50_gate(args.phase4_limit50_root)
    except (ValueError, RuntimeError) as exc:
        print(str(exc), file=sys.stderr)
        return 2

    if args.force_gpu is not None:
        os.environ["CUDA_VISIBLE_DEVICES"] = str(args.force_gpu)
    args.out_root.mkdir(parents=True, exist_ok=True)
    run_specs = _run_specs(args)
    freeze_manifest = _freeze_manifest(args, config=config, run_specs=run_specs, phase4_gate=phase4_gate)
    _write_json(args.out_root / "phase9_prompt_profile_freeze_manifest.json", freeze_manifest)

    summaries = []
    for spec in run_specs:
        timestamp = _created_slug()
        run_dir = args.out_root / f"phase9_{spec.baseline.baseline_id}_seed{spec.seed}_{timestamp}"
        run_dir.mkdir(parents=True, exist_ok=False)
        run_config = _resolved_config(config, args=args, baseline=spec.baseline, seed=spec.seed)
        write_yaml(run_dir / "phase9_config.resolved.yaml", run_config)
        _write_json(run_dir / "phase9_prompt_profile_freeze_manifest.json", freeze_manifest)
        full_dev = _run_generate(
            args,
            config=run_config,
            run_dir=run_dir / "full_dev",
            dataset=_dataset(args, config),
            data_root=_data_root(args, config),
            split=args.split,
            limit=_dry_run_limit(args),
        )
        evaluator = _run_evaluator(
            args,
            run_dir=Path(full_dev["run_dir"]),
            dataset=_dataset(args, config),
            split=args.split,
            benchmark_root=args.benchmark_root,
            out_dir=(args.evaluator_out_root or run_dir / "evaluator_artifacts" / "full_dev"),
        )
        full_dev.update(_summarize_evaluator(evaluator, dataset=_dataset(args, config), split=args.split))
        full_dev["parse_valid_subset"] = _parse_valid_subset(
            args,
            stage_dir=Path(full_dev["run_dir"]),
            dataset=_dataset(args, config),
            split=args.split,
            source_data_root=Path(_data_root(args, config)),
        )
        summary = _run_summary(args, config=config, spec=spec, run_dir=run_dir, full_dev=full_dev)
        _write_json(run_dir / "phase9_prompt_run_summary.json", summary)
        summaries.append(summary)

    matrix_summary = _matrix_summary(args, config=config, summaries=summaries)
    summary_path = args.out_root / args.matrix_summary_name
    _write_json(summary_path, matrix_summary)
    print(f"summary_json={summary_path}")
    print(f"run_count={len(summaries)}")
    return 0


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run SAGE v2 Phase 9 P1-P4 frozen prompt full-dev generation.")
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--phase4-limit50-root", type=Path, required=True)
    parser.add_argument("--dataset")
    parser.add_argument("--data-root")
    parser.add_argument("--split", default="dev")
    parser.add_argument("--dry-run", dest="dry_run", action="store_true", default=None)
    parser.add_argument("--real-run", action="store_true")
    parser.add_argument("--allow-full-dev", action="store_true")
    parser.add_argument("--allow-real-partial-shard", action="store_true")
    parser.add_argument("--only-baseline", choices=tuple(BASELINE_BY_ID))
    parser.add_argument("--only-seed", type=int)
    parser.add_argument("--seed", dest="seeds", action="append", type=int)
    parser.add_argument("--dry-run-doc-limit", type=int)
    parser.add_argument("--force-gpu")
    parser.add_argument("--matrix-summary-name", default="phase9_prompt_full_dev_matrix_summary.json")
    parser.add_argument("--enable-telemetry", action="store_true")
    parser.add_argument("--telemetry-interval-sec", type=float)
    parser.add_argument("--skip-evaluator", action="store_true")
    parser.add_argument("--evaluator-root", type=Path, default=Path("/home/TJK/DEE/dee-eval"))
    parser.add_argument("--benchmark-root", type=Path, default=Path("/data/TJK/DEE/data/processed"))
    parser.add_argument("--evaluator-out-root", type=Path)
    parser.add_argument("--out-root", type=Path, required=True)
    return parser.parse_args(argv)


def _validate_args(args: argparse.Namespace) -> None:
    if args.split == "test":
        raise ValueError("Phase 9 rejects test split; test remains blocked")
    if args.split != "dev":
        raise ValueError(f"Phase 9 only permits dev split, got {args.split!r}")
    if not args.allow_full_dev:
        raise ValueError("Phase 9 full-dev prompt run requires --allow-full-dev")
    if args.real_run and args.dry_run_doc_limit is not None:
        raise ValueError("--dry-run-doc-limit is only valid for dry-run checks")
    if args.real_run and not args.allow_real_partial_shard and (args.only_baseline or args.only_seed is not None):
        raise ValueError("real partial shard requires --allow-real-partial-shard")
    if "/" in args.matrix_summary_name or args.matrix_summary_name in {"", ".", ".."}:
        raise ValueError("matrix summary name must be a file name")


def _require_phase4_limit50_gate(root: Path) -> dict[str, Any]:
    summary_path = root / "summary.json"
    if not summary_path.is_file():
        raise RuntimeError(f"Phase 4 limit50 summary is missing: {summary_path}")
    summary = _read_json(summary_path)
    rows = {str(row.get("baseline_id") or ""): row for row in summary.get("baselines") or []}
    missing = [baseline.baseline_id for baseline in BASELINES if baseline.baseline_id not in rows]
    if missing:
        raise RuntimeError(f"Phase 4 limit50 summary missing baselines: {missing}")
    for baseline in BASELINES:
        row = rows[baseline.baseline_id]
        if row.get("canonical_rows") != 50:
            raise RuntimeError(f"Phase 4 limit50 gate failed for {baseline.baseline_id}: canonical_rows != 50")
        if row.get("evaluator_attempted") is not True or row.get("evaluator_validation_ok") is not True:
            raise RuntimeError(f"Phase 4 limit50 evaluator gate failed for {baseline.baseline_id}")
        manifest_path = Path(str(row.get("run_dir") or root / baseline.baseline_id)) / "generation_manifest.json"
        if manifest_path.is_file():
            manifest = _read_json(manifest_path)
            if manifest.get("document_count") != 50:
                raise RuntimeError(f"Phase 4 manifest gate failed for {baseline.baseline_id}: document_count != 50")
            if manifest.get("gold_visible") is not False:
                raise RuntimeError(
                    f"Phase 4 manifest gate failed for {baseline.baseline_id}: gold_visible is not false"
                )
    return {"summary_path": str(summary_path), "baselines": rows}


def _run_specs(args: argparse.Namespace) -> list[RunSpec]:
    seeds = tuple(args.seeds or DEFAULT_SEEDS)
    specs = []
    for baseline in BASELINES:
        if args.only_baseline and baseline.baseline_id != args.only_baseline:
            continue
        for seed in seeds:
            if args.only_seed is not None and seed != args.only_seed:
                continue
            specs.append(RunSpec(baseline=baseline, seed=int(seed)))
    if not specs:
        raise ValueError("Phase 9 run matrix is empty")
    return specs


def _resolved_config(
    config: dict[str, Any],
    *,
    args: argparse.Namespace,
    baseline: BaselineSpec,
    seed: int,
) -> dict[str, Any]:
    profile_overrides = ((config.get("profiles") or {}).get(baseline.profile) or {})
    resolved = _deep_merge(config, profile_overrides)
    resolved.pop("profiles", None)
    run_cfg = dict(resolved.get("run") or {})
    run_cfg["profile"] = baseline.profile
    run_cfg["baseline_id"] = baseline.baseline_id
    run_cfg["dry_run"] = not bool(args.real_run)
    run_cfg["real_run"] = bool(args.real_run)
    resolved["run"] = run_cfg
    data_cfg = dict(resolved.get("data") or {})
    data_cfg["max_train_docs"] = 0
    data_cfg["max_predict_docs"] = _dry_run_limit(args)
    resolved["data"] = data_cfg
    predict_cfg = dict(resolved.get("predict") or {})
    predict_cfg["dataset"] = _dataset(args, config)
    predict_cfg["split"] = args.split
    predict_cfg["data_root"] = _data_root(args, config)
    predict_cfg["max_predict_docs"] = _dry_run_limit(args)
    resolved["predict"] = predict_cfg
    prompt = dict((resolved.get("getm") or {}).get("prompt") or {})
    prompt["baseline_mode"] = baseline.baseline_mode
    if baseline.baseline_mode == "role_safe_surface_memory":
        prompt.setdefault("max_surface_candidates", 10)
        prompt.setdefault("candidate_render_mode", "compact")
        prompt.setdefault("candidate_context_chars", 0)
        prompt.setdefault("enable_candidate_filtering", True)
        prompt.setdefault("max_candidates_per_type", 6)
        prompt.setdefault("dedupe_surface_candidates", True)
        prompt.setdefault("drop_low_value_company_fragments", True)
    else:
        prompt["max_surface_candidates"] = 0
        prompt["enable_candidate_filtering"] = False
        prompt["max_candidates_per_type"] = None
        prompt["dedupe_surface_candidates"] = False
        prompt["drop_low_value_company_fragments"] = False
    generation = dict((resolved.get("getm") or {}).get("generation") or {})
    generation["seed"] = int(seed)
    generation["k_candidates"] = 1
    generation["do_sample"] = False
    generation["temperature"] = None
    generation["top_p"] = 1.0
    generation["deterministic"] = True
    generation["deterministic_warn_only"] = True
    generation["record_resolved_generation_config"] = True
    resolved.setdefault("getm", {})["prompt"] = prompt
    resolved.setdefault("getm", {})["generation"] = generation
    resource = dict(resolved.get("resource_monitor") or {})
    if args.enable_telemetry:
        resource["enabled"] = True
    if args.telemetry_interval_sec is not None:
        resource["sample_interval_sec"] = args.telemetry_interval_sec
    if resource:
        resolved["resource_monitor"] = resource
    return resolved


def _dry_run_limit(args: argparse.Namespace) -> int | None:
    if args.real_run:
        return None
    return args.dry_run_doc_limit


def _run_generate(
    args: argparse.Namespace,
    *,
    config: dict[str, Any],
    run_dir: Path,
    dataset: str,
    data_root: str,
    split: str,
    limit: int | None,
) -> dict[str, Any]:
    run_dir.mkdir(parents=True, exist_ok=True)
    schema = load_schema(dataset, data_root=data_root)
    documents = load_documents(dataset, split, data_root=data_root, mode="predict", limit=limit)
    telemetry = None
    backend: QwenGetmBackend | MockGetmBackend | None = None
    try:
        if args.real_run:
            telemetry = start_qwen_telemetry(
                config,
                run_dir,
                operation="phase9_prompt_full_dev",
                total_items=len(documents),
            )
            backend = QwenGetmBackend(config=config, telemetry=telemetry)
        else:
            backend = MockGetmBackend(mode="empty")
        output = generate_getm_candidate_files(
            documents=documents,
            dataset=dataset,
            split=split,
            schema=schema,
            backend=backend,
            k=1,
            out_dir=run_dir,
        )
    finally:
        if isinstance(backend, QwenGetmBackend):
            _release_qwen_backend(backend)
        if telemetry is not None:
            telemetry.finish()
    write_yaml(run_dir / "config.resolved.yaml", config)
    _write_json(run_dir / "run_manifest.json", _run_manifest(config=config, dataset=dataset, split=split))
    _write_json(
        run_dir / "generation_manifest.json",
        {
            "diagnostic_version": DIAGNOSTIC_VERSION,
            "backend": "qwen" if args.real_run else "mock",
            "dry_run": bool((config.get("run") or {}).get("dry_run", True)),
            "real_run": bool((config.get("run") or {}).get("real_run", False)),
            "profile": (config.get("run") or {}).get("profile"),
            "baseline_id": (config.get("run") or {}).get("baseline_id"),
            "dataset": dataset,
            "split": split,
            "document_count": len(documents),
            "k": 1,
            "prompts_path": str(output.prompts_path),
            "raw_outputs_path": str(output.raw_outputs_path),
            "parsed_candidates_path": str(output.parsed_candidates_path),
            "parse_diagnostics_path": str(output.parse_diagnostics_path),
            "canonical_predictions_path": str(output.canonical_predictions_path),
            "gold_visible": False,
            "phase9_stage": "full_dev",
            "generation": _generation_metadata(config) if args.real_run else {},
        },
    )
    _write_json(
        run_dir / "phase9_generate_command.json",
        {
            "internal_runner": True,
            "stage": "full_dev",
            "limit": limit,
            "returncode": 0,
            "env": {"CUDA_VISIBLE_DEVICES": os.environ.get("CUDA_VISIBLE_DEVICES")},
        },
    )
    return _summarize_generation(run_dir=run_dir, dataset=dataset, split=split)


def _release_qwen_backend(backend: QwenGetmBackend | None) -> None:
    if backend is None:
        return
    runtime = getattr(backend, "_runtime", None)
    torch = getattr(runtime, "torch", None)
    model = getattr(runtime, "model", None)
    if model is not None and hasattr(model, "to"):
        try:
            model.to("cpu")
        except Exception:
            pass
    backend._runtime = None
    del runtime
    gc.collect()
    cuda = getattr(torch, "cuda", None)
    if cuda is None or not hasattr(cuda, "is_available") or not cuda.is_available():
        return
    if hasattr(cuda, "empty_cache"):
        cuda.empty_cache()
    if hasattr(cuda, "ipc_collect"):
        cuda.ipc_collect()


def _run_evaluator(
    args: argparse.Namespace,
    *,
    run_dir: Path,
    dataset: str,
    split: str,
    benchmark_root: Path,
    out_dir: Path,
) -> dict[str, Any]:
    if args.skip_evaluator:
        return {"attempted": False, "returncode": None, "artifact_out_dir": str(out_dir), "artifact_root": None}
    handoff = build_evaluator_handoff(
        run_root=run_dir,
        dataset=dataset,
        split=split,
        data_repo_root=args.evaluator_root,
        out_dir=out_dir,
        benchmark_root=benchmark_root,
        strict=True,
    )
    result = run_evaluator_handoff(handoff)
    _write_json(run_dir / "phase9_evaluator_handoff.json", {"handoff": handoff.to_dict(), "result": result})
    return {
        "attempted": result["attempted"],
        "returncode": result["returncode"],
        "artifact_out_dir": str(out_dir),
        "artifact_root": _extract_artifact_root(result.get("stdout")),
        "stdout": result.get("stdout"),
        "stderr": result.get("stderr"),
    }


def _parse_valid_subset(
    args: argparse.Namespace,
    *,
    stage_dir: Path,
    dataset: str,
    split: str,
    source_data_root: Path,
) -> dict[str, Any]:
    parsed_rows = read_jsonl(stage_dir / f"parsed_candidates.{split}.jsonl")
    ok_doc_ids = [str(row.get("doc_id") or "") for row in parsed_rows if row.get("parse_status") == "ok"]
    canonical_rows = read_jsonl(stage_dir / "predictions" / dataset / f"{split}.canonical.pred.jsonl")
    ok_set = set(ok_doc_ids)
    filtered_rows = [row for row in canonical_rows if str(row.get("doc_id") or "") in ok_set]
    result: dict[str, Any] = {
        "doc_count": len(filtered_rows),
        "source_doc_count": len(canonical_rows),
        "evaluator_attempted": False,
        "evaluator_returncode": None,
        "evaluator_validation_ok": None,
        "event_table_micro_f1": None,
        "role_level_f1": None,
        "exact_record_f1": None,
    }
    if not filtered_rows or args.skip_evaluator:
        return result
    parse_valid_run = stage_dir / "parse_valid_subset" / "run"
    prediction_path = parse_valid_run / "predictions" / dataset / f"{split}.canonical.pred.jsonl"
    write_jsonl(prediction_path, filtered_rows)
    _copy_run_manifest(stage_dir / "run_manifest.json", parse_valid_run / "run_manifest.json")
    subset_root = _write_subset_benchmark(
        out_root=stage_dir / "parse_valid_subset" / "benchmark",
        source_data_root=source_data_root,
        dataset=dataset,
        split=split,
        doc_ids=[str(row.get("doc_id") or "") for row in filtered_rows],
    )
    evaluator = _run_evaluator(
        args,
        run_dir=parse_valid_run,
        dataset=dataset,
        split=split,
        benchmark_root=subset_root,
        out_dir=stage_dir / "parse_valid_subset" / "evaluator_artifacts",
    )
    result.update(_summarize_evaluator(evaluator, dataset=dataset, split=split))
    return result


def _summarize_generation(*, run_dir: Path, dataset: str, split: str) -> dict[str, Any]:
    diagnostics = _read_json(run_dir / f"parse_diagnostics.{split}.json")
    parsed_rows = read_jsonl(run_dir / f"parsed_candidates.{split}.jsonl")
    canonical_path = run_dir / "predictions" / dataset / f"{split}.canonical.pred.jsonl"
    canonical_rows = read_jsonl(canonical_path)
    diagnostic_counts = diagnostics.get("diagnostic_counts") or {}
    parse_status_counts = diagnostics.get("parse_status_counts") or {}
    validation = _canonical_validation(canonical_rows)
    return {
        "run_dir": str(run_dir),
        "generation_manifest_path": str(run_dir / "generation_manifest.json"),
        "parse_diagnostics_path": str(run_dir / f"parse_diagnostics.{split}.json"),
        "canonical_path": str(canonical_path),
        "canonical_rows": len(canonical_rows),
        "canonical_event_count": sum(len(row.get("events") or []) for row in canonical_rows),
        "parse_status_counts": dict(sorted(parse_status_counts.items())),
        "parse_error": int(parse_status_counts.get("parse_error", 0) or 0),
        "schema_violation_rows": sum(1 for row in parsed_rows if row.get("parse_status") == "schema_violation"),
        "schema_violation": int(diagnostic_counts.get("schema_violation", 0) or 0),
        "unknown_role": int(diagnostic_counts.get("unknown_role", 0) or 0),
        "unknown_event_type": int(diagnostic_counts.get("unknown_event_type", 0) or 0),
        "forbidden_key_violations": validation["forbidden_key_violations"],
        "canonical_schema_errors": validation["canonical_schema_errors"],
        "telemetry": _telemetry_summary(run_dir),
        "oom": _has_oom(run_dir),
    }


def _summarize_evaluator(evaluator: dict[str, Any], *, dataset: str, split: str) -> dict[str, Any]:
    metrics = _read_evaluator_metrics(evaluator.get("artifact_root"), dataset=dataset, split=split)
    return {
        "evaluator_attempted": bool(evaluator.get("attempted")),
        "evaluator_returncode": evaluator.get("returncode"),
        "evaluator_artifact_out_dir": evaluator.get("artifact_out_dir"),
        "evaluator_artifact_root": evaluator.get("artifact_root"),
        "evaluator_validation_ok": metrics.get("validation_ok"),
        "event_table_micro_f1": metrics.get("event_table_micro_f1"),
        "role_level_f1": metrics.get("role_level_f1"),
        "exact_record_f1": metrics.get("exact_record_f1"),
        "tp": metrics.get("tp"),
        "fp": metrics.get("fp"),
        "fn": metrics.get("fn"),
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
        metrics["tp"] = overall.get("tp")
        metrics["fp"] = overall.get("fp")
        metrics["fn"] = overall.get("fn")
    if record_path.is_file():
        record = _read_json(record_path)
        metrics["exact_record_f1"] = record.get("record_f1_exact")
    if validation_path.is_file():
        validation = _read_json(validation_path)
        metrics["validation_ok"] = validation.get("ok")
    return metrics


def _run_summary(
    args: argparse.Namespace,
    *,
    config: dict[str, Any],
    spec: RunSpec,
    run_dir: Path,
    full_dev: dict[str, Any],
) -> dict[str, Any]:
    document_count = int(full_dev.get("canonical_rows") or 0)
    scope = {
        "dataset": _dataset(args, config),
        "split": args.split,
        "document_count": document_count,
        "train_used": False,
        "full_train_used": False,
        "full_dev_used": args.real_run and document_count == 500,
        "test_used": False,
        "dry_run": not bool(args.real_run),
        "real_run": bool(args.real_run),
        "phase4_limit50_gate_used": True,
        "no_post_full_dev_tuning": True,
    }
    return {
        "phase": "Phase 9 prompt full-dev",
        "baseline_id": spec.baseline.baseline_id,
        "profile": spec.baseline.profile,
        "label": spec.baseline.label,
        "baseline_mode": spec.baseline.baseline_mode,
        "seed": spec.seed,
        "run_dir": str(run_dir),
        "scope": scope,
        "full_dev": full_dev,
    }


def _matrix_summary(
    args: argparse.Namespace,
    *,
    config: dict[str, Any],
    summaries: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "phase": "Phase 9 prompt full-dev",
        "scope": {
            "stage": "full_dev",
            "dataset": _dataset(args, config),
            "split": args.split,
            "train_used": False,
            "full_train_used": False,
            "test_used": False,
            "dry_run": not bool(args.real_run),
            "real_run": bool(args.real_run),
        },
        "config_path": str(args.config),
        "config_sha256": _sha256(args.config),
        "phase4_limit50_root": str(args.phase4_limit50_root),
        "runs": summaries,
        "gate": {
            "all_runs_completed": len(summaries) == len(_run_specs(args)),
            "no_test_used": True,
            "no_full_train_used": True,
            "no_post_full_dev_tuning_declared": True,
        },
    }


def _run_manifest(*, config: dict[str, Any], dataset: str, split: str) -> dict[str, Any]:
    return {
        "run_id": f"phase9_prompt_full_dev_{_created_slug()}",
        "method_name": "SAGE-DEE-v2-Phase9-Prompt-FullDev",
        "method_family": "SAGE-DEE-v2",
        "stage": "predict",
        "dataset_version": dataset,
        "split_version": split,
        "evaluator_version": EVALUATOR_VERSION,
        "prediction_format": PREDICTION_FORMAT,
        "training_view": "none_prompt_only",
        "gold_view": f"processed/views/evaluator_gold/{dataset}",
        "seed": ((config.get("getm") or {}).get("generation") or {}).get("seed"),
        "backend": "qwen" if bool((config.get("run") or {}).get("real_run")) else "mock",
        "dry_run": bool((config.get("run") or {}).get("dry_run", True)),
        "real_run": bool((config.get("run") or {}).get("real_run", False)),
        "profile": (config.get("run") or {}).get("profile"),
        "baseline_id": (config.get("run") or {}).get("baseline_id"),
        "command_train": None,
        "command_infer": join([sys.executable, "scripts/v2/run_phase9_prompt_full_dev.py", "--allow-full-dev"]),
        "git_commit": _git_commit(),
        "created_at": _created_at(),
        "notes": "Phase 9 frozen P1-P4 prompt full-dev run; test split remains blocked.",
    }


def _freeze_manifest(
    args: argparse.Namespace,
    *,
    config: dict[str, Any],
    run_specs: list[RunSpec],
    phase4_gate: dict[str, Any],
) -> dict[str, Any]:
    return {
        "phase": "Phase 9 prompt full-dev",
        "created_at": _created_at(),
        "config_path": str(args.config),
        "config_sha256": _sha256(args.config),
        "dataset": _dataset(args, config),
        "split": args.split,
        "train_used": False,
        "full_train_used": False,
        "test_blocked": True,
        "phase4_limit50_summary": phase4_gate["summary_path"],
        "run_matrix": [
            {"baseline_id": spec.baseline.baseline_id, "profile": spec.baseline.profile, "seed": spec.seed}
            for spec in run_specs
        ],
        "no_prompt_parser_surface_memory_tuning_after_freeze": True,
        "no_post_full_dev_tuning": True,
    }


def _write_subset_benchmark(
    *,
    out_root: Path,
    source_data_root: Path,
    dataset: str,
    split: str,
    doc_ids: list[str],
) -> Path:
    target_root = out_root
    gold_source = source_data_root / dataset / f"{split}.jsonl"
    schema_source = source_data_root / dataset / "schema.json"
    gold_rows = read_jsonl(gold_source)
    doc_id_set = set(doc_ids)
    filtered = [row for row in gold_rows if str(row.get("doc_id") or "") in doc_id_set]
    if len(filtered) != len(doc_ids):
        found = {str(row.get("doc_id") or "") for row in filtered}
        missing = [doc_id for doc_id in doc_ids if doc_id not in found]
        raise RuntimeError(f"subset gold is missing generated doc ids: {missing[:10]}")
    view_dir = target_root / "views" / "evaluator_gold" / dataset
    dataset_dir = target_root / dataset
    write_jsonl(view_dir / f"{split}.jsonl", filtered)
    dataset_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(schema_source, dataset_dir / "schema.json")
    shutil.copy2(schema_source, view_dir / "schema.json")
    return target_root


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


def _copy_run_manifest(source: Path, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")


def _telemetry_summary(run_dir: Path) -> dict[str, Any]:
    return {
        "telemetry_manifest": _read_json_if_exists(run_dir / "telemetry" / "telemetry_manifest.json"),
        "timing_summary": _read_json_if_exists(run_dir / "telemetry" / "timing_summary.json"),
        "gpu_memory_summary": _read_json_if_exists(run_dir / "telemetry" / "gpu_memory_summary.json"),
    }


def _has_oom(run_dir: Path) -> bool:
    texts = []
    for path in run_dir.glob("*.stderr.log"):
        texts.append(path.read_text(encoding="utf-8", errors="ignore"))
    serialized = "\n".join(texts).lower()
    return "outofmemory" in serialized or "out of memory" in serialized or "cuda oom" in serialized


def _dataset(args: argparse.Namespace, config: dict[str, Any]) -> str:
    return str(args.dataset or ((config.get("data") or {}).get("dataset")) or "DuEE-Fin-dev500")


def _data_root(args: argparse.Namespace, config: dict[str, Any]) -> str:
    return str(args.data_root or ((config.get("data") or {}).get("data_root")) or "data")


def _extract_artifact_root(stdout: Any) -> str | None:
    text = str(stdout or "").strip()
    if not text:
        return None
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return None
    if isinstance(payload, dict) and payload.get("artifact_root"):
        return str(payload["artifact_root"])
    return None


def _read_json(path: str | Path) -> dict[str, Any]:
    with Path(path).open(encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object: {path}")
    return payload


def _read_json_if_exists(path: Path) -> dict[str, Any] | None:
    return _read_json(path) if path.is_file() else None


def _write_json(path: Path, payload: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    merged = deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = deepcopy(value)
    return merged


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _created_slug() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _created_at() -> str:
    return datetime.now(timezone.utc).isoformat()


def _git_commit() -> str:
    head = REPO_ROOT / ".git" / "HEAD"
    if not head.exists():
        return "unknown"
    return os.popen(f"git -C {REPO_ROOT} rev-parse --short HEAD 2>/dev/null").read().strip() or "unknown"


if __name__ == "__main__":
    raise SystemExit(main())
