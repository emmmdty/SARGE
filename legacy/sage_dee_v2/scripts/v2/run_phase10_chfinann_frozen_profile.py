from __future__ import annotations

import argparse
import gc
import os
import subprocess
import sys
from collections.abc import Sequence
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from shlex import join
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))
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
from scripts.v2.run_phase6_sft_baseline_matrix import (  # noqa: E402
    FORBIDDEN_CANONICAL_KEYS,
    _created_at,
    _created_slug,
    _extract_artifact_root,
    _git_commit,
    _has_oom,
    _prompt_doc_ids,
    _release_qwen_backend,
    _sha256,
    _telemetry_summary,
    _write_json,
    _write_subset_benchmark,
)
from scripts.v2.run_phase7_surface_memory_ablation import _grounding_diagnostics  # noqa: E402


@dataclass(frozen=True)
class BaselineSpec:
    baseline_id: str
    profile: str
    phase6_profile: str
    label: str
    baseline_mode: str


@dataclass(frozen=True)
class RunSpec:
    baseline: BaselineSpec
    seed: int


BASELINES = (
    BaselineSpec("S1", "phase10_s1_direct_json", "phase6_s1_direct_json", "direct JSON SFT", "direct_json"),
    BaselineSpec("S2", "phase10_s2_schema_only", "phase6_s2_schema_only", "schema-only SFT", "schema_only"),
    BaselineSpec(
        "S4",
        "phase10_s4_role_safe_surface_memory",
        "phase6_s4_role_safe_surface_memory",
        "role-safe + surface memory SFT",
        "role_safe_surface_memory",
    ),
)
BASELINE_BY_ID = {baseline.baseline_id: baseline for baseline in BASELINES}


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    if args.dry_run is None:
        args.dry_run = not args.real_run
    config = read_yaml(args.config)
    try:
        _validate_args(args, config)
        phase9_gate = _require_phase9_gate(args.phase9_aggregate)
    except (ValueError, RuntimeError) as exc:
        print(str(exc), file=sys.stderr)
        return 2

    args.out_root.mkdir(parents=True, exist_ok=True)
    gpu_selection = _select_gpu(config, force_gpu=args.force_gpu)
    if gpu_selection.get("selected_gpu"):
        os.environ["CUDA_VISIBLE_DEVICES"] = str(gpu_selection["selected_gpu"])

    if args.stage == "limit50":
        summaries = _run_limit50_matrix(args, config=config, gpu_selection=gpu_selection, phase9_gate=phase9_gate)
    else:
        summaries = _run_full_dev_matrix(args, config=config, gpu_selection=gpu_selection)

    matrix_summary = _matrix_summary(args, config=config, gpu_selection=gpu_selection, summaries=summaries)
    summary_path = args.out_root / args.matrix_summary_name
    _write_json(summary_path, matrix_summary)
    print(f"summary_json={summary_path}")
    print(f"run_count={len(summaries)}")
    return 0


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run SAGE v2 Phase 10 ChFinAnn frozen-profile robustness.")
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--stage", choices=("limit50", "full-dev"), required=True)
    parser.add_argument("--dataset")
    parser.add_argument("--data-root")
    parser.add_argument("--split", default="dev")
    parser.add_argument("--dry-run", dest="dry_run", action="store_true", default=None)
    parser.add_argument("--real-run", action="store_true")
    parser.add_argument("--allow-limit50", action="store_true")
    parser.add_argument("--allow-full-dev", action="store_true")
    parser.add_argument("--allow-partial-dry-run", action="store_true")
    parser.add_argument("--allow-real-partial-shard", action="store_true")
    parser.add_argument("--only-baseline", choices=tuple(BASELINE_BY_ID))
    parser.add_argument("--only-seed", type=int)
    parser.add_argument("--force-gpu")
    parser.add_argument("--phase6-runs-root", type=Path)
    parser.add_argument("--phase9-aggregate", type=Path)
    parser.add_argument("--matrix-summary-name", default="phase10_matrix_summary.json")
    parser.add_argument("--enable-telemetry", action="store_true")
    parser.add_argument("--telemetry-interval-sec", type=float)
    parser.add_argument("--skip-evaluator", action="store_true")
    parser.add_argument("--evaluator-root", type=Path, default=Path("/home/TJK/DEE/dee-eval"))
    parser.add_argument(
        "--benchmark-root",
        type=Path,
        default=Path("/data/TJK/DEE/data/processed"),
    )
    parser.add_argument("--evaluator-out-root", type=Path)
    parser.add_argument("--out-root", type=Path, required=True)
    return parser.parse_args(argv)


def _validate_args(args: argparse.Namespace, config: dict[str, Any]) -> None:
    if args.split == "test":
        raise ValueError("Phase 10 rejects test split; test remains blocked")
    if args.split != "dev":
        raise ValueError(f"Phase 10 only permits dev split, got {args.split!r}")
    if _dataset(args, config) != "ChFinAnn":
        raise ValueError("Phase 10 only permits dataset ChFinAnn")
    partial = bool(args.only_baseline or args.only_seed is not None)
    if partial and not (
        (args.dry_run and args.allow_partial_dry_run)
        or (args.real_run and args.allow_real_partial_shard)
    ):
        raise ValueError("partial matrix selection requires --allow-partial-dry-run or --allow-real-partial-shard")
    if "/" in args.matrix_summary_name or args.matrix_summary_name in {"", ".", ".."}:
        raise ValueError("matrix summary name must be a file name")
    if args.stage == "limit50" and not args.allow_limit50 and not args.dry_run:
        raise ValueError("Phase 10 limit50 stage requires --allow-limit50")
    if args.stage == "full-dev" and not args.allow_full_dev:
        raise ValueError("Phase 10 full-dev stage requires --allow-full-dev")
    phase10 = config.get("phase10") or {}
    if phase10.get("train_used") is not False:
        raise ValueError("Phase 10 must not train; train_used must be false")
    if phase10.get("full_train_used") is not False:
        raise ValueError("Phase 10 full train must remain blocked")
    if phase10.get("test_blocked") is not True:
        raise ValueError("Phase 10 config must keep test blocked")
    if phase10.get("no_chfinann_tuning") is not True:
        raise ValueError("Phase 10 config must declare no ChFinAnn tuning")


def _run_limit50_matrix(
    args: argparse.Namespace,
    *,
    config: dict[str, Any],
    gpu_selection: dict[str, Any],
    phase9_gate: dict[str, Any],
) -> list[dict[str, Any]]:
    run_specs = _run_specs(config, args=args)
    freeze_manifest = _freeze_manifest(
        args,
        config=config,
        run_specs=run_specs,
        gpu_selection=gpu_selection,
        phase9_gate=phase9_gate,
    )
    _write_json(args.out_root / "phase10_profile_freeze_manifest.json", freeze_manifest)
    summaries = []
    for spec in run_specs:
        timestamp = _created_slug()
        run_dir = args.out_root / f"phase10_{spec.baseline.baseline_id}_seed{spec.seed}_{timestamp}"
        run_dir.mkdir(parents=True, exist_ok=False)
        adapter_path = _phase6_adapter_path(
            _phase6_runs_root(args, config),
            baseline=spec.baseline,
            seed=spec.seed,
        )
        run_config = _resolved_config(
            config,
            baseline=spec.baseline,
            seed=spec.seed,
            stage="limit50",
            args=args,
            adapter_path=adapter_path,
        )
        write_yaml(run_dir / "phase10_config.resolved.yaml", run_config)
        _write_json(run_dir / "phase10_profile_freeze_manifest.json", freeze_manifest)
        limit50 = _run_generate(
            args,
            config=run_config,
            run_dir=run_dir / "limit50",
            dataset=_dataset(args, config),
            data_root=_data_root(args, config),
            split=args.split,
            limit=int((config.get("phase10") or {}).get("limit50_predict_docs") or 50),
            stage_name="limit50",
        )
        subset_root = _write_subset_benchmark(
            out_root=run_dir / "limit50_subset_benchmark",
            source_data_root=Path(_data_root(args, config)),
            dataset=_dataset(args, config),
            split=args.split,
            doc_ids=_prompt_doc_ids(Path(limit50["run_dir"]) / f"prompts.{args.split}.jsonl"),
        )
        evaluator = _run_evaluator(
            args,
            run_dir=Path(limit50["run_dir"]),
            dataset=_dataset(args, config),
            split=args.split,
            benchmark_root=subset_root,
            out_dir=(args.evaluator_out_root or run_dir / "evaluator_artifacts" / "limit50"),
        )
        limit50.update(_summarize_evaluator(evaluator, dataset=_dataset(args, config), split=args.split))
        limit50["parse_valid_subset"] = _parse_valid_subset(
            args,
            stage_dir=Path(limit50["run_dir"]),
            dataset=_dataset(args, config),
            split=args.split,
            source_data_root=Path(_data_root(args, config)),
        )
        limit50["surface_diagnostics"] = _surface_diagnostics(
            stage_dir=Path(limit50["run_dir"]),
            dataset=_dataset(args, config),
            split=args.split,
            data_root=Path(_data_root(args, config)),
            limit=int((config.get("phase10") or {}).get("limit50_predict_docs") or 50),
        )
        summary = _run_summary(
            args,
            config=config,
            spec=spec,
            run_dir=run_dir,
            gpu_selection=gpu_selection,
            adapter_path=adapter_path,
            limit50=limit50,
            full_dev=None,
        )
        _write_json(run_dir / "phase10_run_summary.json", summary)
        summaries.append(summary)
    return summaries


def _run_full_dev_matrix(
    args: argparse.Namespace,
    *,
    config: dict[str, Any],
    gpu_selection: dict[str, Any],
) -> list[dict[str, Any]]:
    summaries = []
    for spec in _run_specs(config, args=args):
        existing = _latest_limit50_run(args.out_root, spec)
        if existing is None:
            raise RuntimeError(
                f"missing completed Phase 10 limit50 run for {spec.baseline.baseline_id} seed {spec.seed}"
            )
        previous = _read_json(existing / "phase10_run_summary.json")
        _require_profile_hash(args, existing)
        _require_limit50_gate(previous)
        adapter_path = str(previous.get("adapter_path") or "")
        full_dev_config = _resolved_config(
            config,
            baseline=spec.baseline,
            seed=spec.seed,
            stage="full_dev",
            args=args,
            adapter_path=adapter_path,
        )
        full_dev = _run_generate(
            args,
            config=full_dev_config,
            run_dir=existing / "full_dev",
            dataset=_dataset(args, config),
            data_root=_data_root(args, config),
            split=args.split,
            limit=None,
            stage_name="full_dev",
        )
        evaluator = _run_evaluator(
            args,
            run_dir=Path(full_dev["run_dir"]),
            dataset=_dataset(args, config),
            split=args.split,
            benchmark_root=args.benchmark_root,
            out_dir=(args.evaluator_out_root or existing / "evaluator_artifacts" / "full_dev"),
        )
        full_dev.update(_summarize_evaluator(evaluator, dataset=_dataset(args, config), split=args.split))
        full_dev["parse_valid_subset"] = _parse_valid_subset(
            args,
            stage_dir=Path(full_dev["run_dir"]),
            dataset=_dataset(args, config),
            split=args.split,
            source_data_root=Path(_data_root(args, config)),
        )
        full_dev["surface_diagnostics"] = _surface_diagnostics(
            stage_dir=Path(full_dev["run_dir"]),
            dataset=_dataset(args, config),
            split=args.split,
            data_root=Path(_data_root(args, config)),
            limit=None,
        )
        updated = dict(previous)
        updated["full_dev"] = full_dev
        updated["scope"]["full_dev_used"] = True
        updated["gpu_selection"] = gpu_selection
        _write_json(existing / "phase10_run_summary.json", updated)
        summaries.append(updated)
    return summaries


def _run_generate(
    args: argparse.Namespace,
    *,
    config: dict[str, Any],
    run_dir: Path,
    dataset: str,
    data_root: str,
    split: str,
    limit: int | None,
    stage_name: str,
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
                operation=f"phase10_{stage_name}_generate",
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
            gc.collect()
        if telemetry is not None:
            telemetry.finish()
    write_yaml(run_dir / "config.resolved.yaml", config)
    _write_json(
        run_dir / "run_manifest.json",
        _run_manifest(config=config, dataset=dataset, split=split, stage_name=stage_name),
    )
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
            "phase10_stage": stage_name,
            "generation": _generation_metadata(config) if args.real_run else {},
        },
    )
    _write_json(
        run_dir / "phase10_generate_command.json",
        {
            "internal_runner": True,
            "stage": stage_name,
            "limit": limit,
            "returncode": 0,
            "env": {"CUDA_VISIBLE_DEVICES": os.environ.get("CUDA_VISIBLE_DEVICES")},
        },
    )
    return _summarize_generation(run_dir=run_dir, dataset=dataset, split=split)


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
    _write_json(run_dir / "phase10_evaluator_handoff.json", {"handoff": handoff.to_dict(), "result": result})
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


def _copy_run_manifest(source: Path, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")


def _surface_diagnostics(
    *,
    stage_dir: Path,
    dataset: str,
    split: str,
    data_root: Path,
    limit: int | None,
) -> dict[str, Any]:
    diagnostics = _grounding_diagnostics(
        stage_dir=stage_dir,
        dataset=dataset,
        split=split,
        data_root=data_root,
        limit=limit,
    )
    _write_json(stage_dir / "phase10_surface_diagnostics.json", diagnostics)
    return diagnostics


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


def _run_summary(
    args: argparse.Namespace,
    *,
    config: dict[str, Any],
    spec: RunSpec,
    run_dir: Path,
    gpu_selection: dict[str, Any],
    adapter_path: str,
    limit50: dict[str, Any],
    full_dev: dict[str, Any] | None,
) -> dict[str, Any]:
    scope = {
        "dataset": _dataset(args, config),
        "split": args.split,
        "document_count": limit50.get("canonical_rows") if full_dev is None else full_dev.get("canonical_rows"),
        "phase6_adapter_reused": True,
        "train_used": False,
        "full_train_used": False,
        "limit50_used": True,
        "full_dev_used": full_dev is not None,
        "test_used": False,
        "dry_run": not bool(args.real_run),
        "real_run": bool(args.real_run),
        "no_chfinann_tuning": True,
    }
    return {
        "phase": "Phase 10 ChFinAnn frozen-profile robustness",
        "baseline_id": spec.baseline.baseline_id,
        "profile": spec.baseline.profile,
        "phase6_source_profile": spec.baseline.phase6_profile,
        "baseline_mode": spec.baseline.baseline_mode,
        "label": spec.baseline.label,
        "seed": spec.seed,
        "run_dir": str(run_dir),
        "adapter_path": adapter_path,
        "scope": scope,
        "gpu_selection": gpu_selection,
        "limit50": limit50,
        "full_dev": full_dev,
    }


def _matrix_summary(
    args: argparse.Namespace,
    *,
    config: dict[str, Any],
    gpu_selection: dict[str, Any],
    summaries: list[dict[str, Any]],
) -> dict[str, Any]:
    stage = "full_dev" if args.stage == "full-dev" else "limit50"
    gate = {
        "all_runs_completed": len(summaries) == len(_run_specs(config, args=args)),
        "full_dev_allowed": False,
        "test_blocked": True,
        "full_train_blocked": True,
        "no_chfinann_tuning": True,
    }
    if stage == "limit50":
        gate["full_dev_allowed"] = (
            not args.dry_run
            and not args.skip_evaluator
            and not bool(args.only_baseline or args.only_seed is not None)
            and _limit50_matrix_gate(summaries)
        )
    return {
        "phase": "Phase 10 ChFinAnn frozen-profile robustness",
        "scope": {
            "stage": stage,
            "dataset": _dataset(args, config),
            "split": args.split,
            "train_used": False,
            "full_train_used": False,
            "full_dev_used": stage == "full_dev",
            "test_used": False,
            "no_chfinann_tuning": True,
        },
        "gpu_selection": gpu_selection,
        "config_path": str(args.config),
        "config_sha256": _sha256(args.config),
        "runs": summaries,
        "gate": gate,
    }


def _limit50_matrix_gate(summaries: list[dict[str, Any]]) -> bool:
    if not summaries:
        return False
    for summary in summaries:
        limit50 = summary.get("limit50") or {}
        if limit50.get("canonical_rows") != 50:
            return False
        if limit50.get("oom"):
            return False
        if limit50.get("evaluator_attempted") and limit50.get("evaluator_validation_ok") is not True:
            return False
    return True


def _require_limit50_gate(summary: dict[str, Any]) -> None:
    limit50 = summary.get("limit50") or {}
    if limit50.get("canonical_rows") != 50:
        raise RuntimeError("full dev blocked: limit50 canonical rows are not 50")
    if limit50.get("oom"):
        raise RuntimeError("full dev blocked: limit50 run recorded OOM")
    if limit50.get("evaluator_attempted") is not True:
        raise RuntimeError("full dev blocked: limit50 evaluator was not attempted")
    if limit50.get("evaluator_validation_ok") is not True:
        raise RuntimeError("full dev blocked: limit50 evaluator validation did not pass")


def _require_profile_hash(args: argparse.Namespace, run_dir: Path) -> None:
    manifest = _read_json(run_dir / "phase10_profile_freeze_manifest.json")
    expected = manifest.get("config_sha256")
    actual = _sha256(args.config)
    if expected != actual:
        raise RuntimeError("full dev blocked: Phase 10 config hash differs from frozen limit50 profile")


def _run_specs(config: dict[str, Any], *, args: argparse.Namespace) -> list[RunSpec]:
    seed_matrix = (config.get("phase10") or {}).get("seed_matrix") or {}
    specs = []
    for baseline in BASELINES:
        if args.only_baseline and baseline.baseline_id != args.only_baseline:
            continue
        seeds = [int(seed) for seed in seed_matrix.get(baseline.baseline_id, [])]
        for seed in seeds:
            if args.only_seed is not None and seed != args.only_seed:
                continue
            specs.append(RunSpec(baseline=baseline, seed=seed))
    if not specs:
        raise ValueError("Phase 10 run matrix is empty")
    return specs


def _resolved_config(
    config: dict[str, Any],
    *,
    baseline: BaselineSpec,
    seed: int,
    stage: str,
    args: argparse.Namespace,
    adapter_path: str,
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
    data_cfg["dataset"] = _dataset(args, config)
    data_cfg["data_root"] = _data_root(args, config)
    data_cfg["max_train_docs"] = 0
    data_cfg["max_predict_docs"] = 50 if stage == "limit50" else None
    resolved["data"] = data_cfg
    predict_cfg = dict(resolved.get("predict") or {})
    predict_cfg["dataset"] = _dataset(args, config)
    predict_cfg["split"] = args.split
    predict_cfg["data_root"] = _data_root(args, config)
    predict_cfg["max_predict_docs"] = 50 if stage == "limit50" else None
    resolved["predict"] = predict_cfg
    generation = dict((resolved.get("getm") or {}).get("generation") or {})
    generation["seed"] = int(seed)
    generation["k_candidates"] = 1
    generation["do_sample"] = False
    generation["temperature"] = None
    generation["top_p"] = 1.0
    generation["deterministic"] = True
    generation["deterministic_warn_only"] = True
    generation["record_resolved_generation_config"] = True
    resolved.setdefault("getm", {})["generation"] = generation
    resolved.setdefault("getm", {}).setdefault("qwen", {})["adapter_path"] = adapter_path
    return resolved


def _phase6_adapter_path(phase6_runs_root: Path, *, baseline: BaselineSpec, seed: int) -> str:
    pattern = f"phase6_{baseline.baseline_id}_seed{seed}_*"
    candidates = [
        path for path in phase6_runs_root.glob(pattern) if (path / "phase6_run_summary.json").is_file()
    ]
    if not candidates:
        raise RuntimeError(f"missing Phase 6 {baseline.baseline_id} seed {seed} run under {phase6_runs_root}")
    for candidate in sorted(candidates, reverse=True):
        summary = _read_json(candidate / "phase6_run_summary.json")
        if summary.get("baseline_id") != baseline.baseline_id or summary.get("seed") != seed:
            continue
        if summary.get("profile") not in {baseline.phase6_profile, baseline.profile}:
            continue
        scope = summary.get("scope") or {}
        full_dev = summary.get("full_dev") or {}
        if scope.get("dataset") != "DuEE-Fin-dev500":
            continue
        if scope.get("test_used") or scope.get("full_train_used"):
            continue
        if full_dev.get("canonical_rows") != 500 or full_dev.get("evaluator_validation_ok") is not True:
            continue
        adapter_path = str(((summary.get("train") or {}).get("adapter_dir")) or "")
        if adapter_path:
            return adapter_path
    raise RuntimeError(f"missing valid Phase 6 adapter for {baseline.baseline_id} seed {seed}")


def _latest_limit50_run(out_root: Path, spec: RunSpec) -> Path | None:
    pattern = f"phase10_{spec.baseline.baseline_id}_seed{spec.seed}_*"
    candidates = [path for path in out_root.glob(pattern) if (path / "phase10_run_summary.json").is_file()]
    if not candidates:
        return None
    return sorted(candidates)[-1]


def _select_gpu(config: dict[str, Any], *, force_gpu: str | None = None) -> dict[str, Any]:
    phase10 = config.get("phase10") or {}
    preferred = str(phase10.get("preferred_gpu") or "3")
    auto = bool(phase10.get("auto_select_idle_gpu", True))
    idle_memory_mb = int(phase10.get("idle_memory_mb") or 1024)
    idle_util_pct = int(phase10.get("idle_utilization_pct") or 15)
    fake = os.environ.get("SAGE_DEE_PHASE10_FAKE_NVIDIA_SMI")
    if force_gpu is not None:
        rows = _parse_gpu_rows(fake) if fake is not None else []
        return {
            "preferred_gpu": preferred,
            "selected_gpu": str(force_gpu),
            "source": "forced",
            "idle_memory_mb": idle_memory_mb,
            "idle_utilization_pct": idle_util_pct,
            "available_gpus": rows,
        }
    rows = _parse_gpu_rows(fake) if fake is not None else _query_gpu_rows()
    if not auto or not rows:
        return {
            "preferred_gpu": preferred,
            "selected_gpu": preferred,
            "source": "preferred_without_query",
            "available_gpus": rows,
        }
    preferred_row = next((row for row in rows if row["index"] == preferred), None)
    if (
        preferred_row
        and preferred_row["memory_used_mb"] <= idle_memory_mb
        and preferred_row["utilization_pct"] <= idle_util_pct
    ):
        selected = preferred
        source = "preferred_idle"
    else:
        selected_row = min(rows, key=lambda row: (row["memory_used_mb"], row["utilization_pct"], int(row["index"])))
        selected = selected_row["index"]
        source = "least_busy_idle_gpu"
    return {
        "preferred_gpu": preferred,
        "selected_gpu": selected,
        "source": source,
        "idle_memory_mb": idle_memory_mb,
        "idle_utilization_pct": idle_util_pct,
        "available_gpus": rows,
    }


def _query_gpu_rows() -> list[dict[str, Any]]:
    completed = subprocess.run(
        [
            "nvidia-smi",
            "--query-gpu=index,memory.used,utilization.gpu",
            "--format=csv,noheader,nounits",
        ],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        return []
    return _parse_gpu_rows(completed.stdout)


def _parse_gpu_rows(text: str) -> list[dict[str, Any]]:
    rows = []
    for line in text.splitlines():
        parts = [part.strip() for part in line.split(",")]
        if len(parts) < 3:
            continue
        try:
            rows.append(
                {
                    "index": parts[0],
                    "memory_used_mb": int(float(parts[1])),
                    "utilization_pct": int(float(parts[2])),
                }
            )
        except ValueError:
            continue
    return rows


def _run_manifest(*, config: dict[str, Any], dataset: str, split: str, stage_name: str) -> dict[str, Any]:
    return {
        "run_id": f"phase10_{stage_name}_{_created_slug()}",
        "method_name": "SAGE-DEE-v2-Phase10-ChFinAnn-Frozen-Profile",
        "method_family": "SAGE-DEE-v2",
        "stage": "predict",
        "dataset_version": dataset,
        "split_version": split,
        "evaluator_version": EVALUATOR_VERSION,
        "prediction_format": PREDICTION_FORMAT,
        "training_view": "DuEE-Fin Phase 6 frozen adapters",
        "gold_view": f"processed/views/evaluator_gold/{dataset}",
        "seed": ((config.get("getm") or {}).get("generation") or {}).get("seed"),
        "backend": "qwen" if (config.get("run") or {}).get("real_run") else "mock",
        "dry_run": bool((config.get("run") or {}).get("dry_run", True)),
        "real_run": bool((config.get("run") or {}).get("real_run", False)),
        "profile": (config.get("run") or {}).get("profile"),
        "command_train": None,
        "command_infer": join(
            [sys.executable, "scripts/v2/run_phase10_chfinann_frozen_profile.py", "--stage", stage_name]
        ),
        "git_commit": _git_commit(),
        "created_at": _created_at(),
        "notes": (
            "Phase 10 prediction-only ChFinAnn frozen-profile robustness; "
            "no ChFinAnn prompt/parser/profile tuning; test split remains blocked."
        ),
    }


def _freeze_manifest(
    args: argparse.Namespace,
    *,
    config: dict[str, Any],
    run_specs: list[RunSpec],
    gpu_selection: dict[str, Any],
    phase9_gate: dict[str, Any],
) -> dict[str, Any]:
    return {
        "phase": "Phase 10 ChFinAnn frozen-profile robustness",
        "created_at": _created_at(),
        "config_path": str(args.config),
        "config_sha256": _sha256(args.config),
        "dataset": _dataset(args, config),
        "split": args.split,
        "phase9_aggregate": str(args.phase9_aggregate),
        "phase9_gate": phase9_gate,
        "phase6_runs_root": str(_phase6_runs_root(args, config)),
        "train_used": False,
        "full_train_used": False,
        "test_blocked": True,
        "no_chfinann_tuning": True,
        "run_matrix": [
            {"baseline_id": spec.baseline.baseline_id, "profile": spec.baseline.profile, "seed": spec.seed}
            for spec in run_specs
        ],
        "gpu_selection": gpu_selection,
    }


def _require_phase9_gate(path: Path | None) -> dict[str, Any]:
    if path is None:
        raise RuntimeError("Phase 9 aggregate is required before Phase 10")
    if not path.is_file():
        raise RuntimeError(f"Phase 9 aggregate is missing: {path}")
    payload = _read_json(path)
    gate = payload.get("gate") or {}
    required = {
        "dev_main_table_complete": True,
        "no_post_full_dev_tuning_declared": True,
        "chfinann_frozen_profile_allowed": True,
        "test_blocked": True,
        "no_test_used": True,
        "no_full_train_used": True,
    }
    failed = [key for key, expected in required.items() if gate.get(key) is not expected]
    if failed:
        raise RuntimeError(f"Phase 9 aggregate does not allow Phase 10; failed gate keys: {failed}")
    return {key: gate.get(key) for key in required}


def _phase6_runs_root(args: argparse.Namespace, config: dict[str, Any]) -> Path:
    configured = args.phase6_runs_root or (config.get("phase10") or {}).get("phase6_runs_root")
    if configured is None:
        raise RuntimeError("Phase 6 runs root is required")
    return Path(configured)


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


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    merged = deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = deepcopy(value)
    return merged


def _dataset(args: argparse.Namespace, config: dict[str, Any]) -> str:
    return str(args.dataset or ((config.get("data") or {}).get("dataset")) or "ChFinAnn")


def _data_root(args: argparse.Namespace, config: dict[str, Any]) -> str:
    return str(args.data_root or ((config.get("data") or {}).get("data_root")) or "data")


def _read_json(path: str | Path) -> dict[str, Any]:
    with Path(path).open(encoding="utf-8") as handle:
        payload = __import__("json").load(handle)
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object: {path}")
    return payload


if __name__ == "__main__":
    raise SystemExit(main())
