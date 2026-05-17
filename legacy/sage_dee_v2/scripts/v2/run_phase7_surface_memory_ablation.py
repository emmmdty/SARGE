from __future__ import annotations

import argparse
import gc
import os
import re
import subprocess
import sys
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass
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
from sage_dee.v2.getm.qwen_backend import QwenGetmBackend, _generation_metadata, start_qwen_telemetry  # noqa: E402
from sage_dee.v2.pipeline.evaluator_handoff import build_evaluator_handoff, run_evaluator_handoff  # noqa: E402
from sage_dee.v2.pipeline.run_manifest import EVALUATOR_VERSION, PREDICTION_FORMAT  # noqa: E402
from scripts.v2.run_phase6_sft_baseline_matrix import (  # noqa: E402
    _canonical_validation,
    _created_at,
    _created_slug,
    _deep_merge,
    _extract_artifact_root,
    _git_commit,
    _has_oom,
    _prompt_doc_ids,
    _read_json,
    _release_qwen_backend,
    _sha256,
    _telemetry_summary,
    _write_json,
    _write_subset_benchmark,
)

VARIANT_ORDER = (
    "no_surface",
    "raw_surface",
    "compressed_surface",
    "low_k",
    "high_k",
    "no_compression",
)
RECALL_KS = (1, 5, 10, 20)


@dataclass(frozen=True)
class VariantSpec:
    variant_id: str
    profile: str
    label: str


@dataclass(frozen=True)
class RunSpec:
    variant: VariantSpec
    seed: int


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    if args.dry_run is None:
        args.dry_run = not args.real_run
    config = read_yaml(args.config)
    try:
        _validate_args(args, config)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    args.out_root.mkdir(parents=True, exist_ok=True)
    gpu_selection = _select_gpu(config, force_gpu=args.force_gpu)
    if gpu_selection.get("selected_gpu"):
        os.environ["CUDA_VISIBLE_DEVICES"] = str(gpu_selection["selected_gpu"])

    if args.stage == "limit50":
        summaries = _run_limit50_matrix(args, config=config, gpu_selection=gpu_selection)
    else:
        summaries = _run_full_dev_matrix(args, config=config, gpu_selection=gpu_selection)

    matrix_summary = _matrix_summary(args, config=config, gpu_selection=gpu_selection, summaries=summaries)
    summary_path = args.out_root / args.matrix_summary_name
    _write_json(summary_path, matrix_summary)
    print(f"summary_json={summary_path}")
    print(f"run_count={len(summaries)}")
    return 0


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run SAGE v2 Phase 7 surface-memory ablation.")
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
    parser.add_argument("--only-variant", choices=VARIANT_ORDER)
    parser.add_argument("--only-seed", type=int)
    parser.add_argument("--force-gpu")
    parser.add_argument("--phase6-runs-root", type=Path, default=Path("/data/TJK/DEE/sage-dee/runs"))
    parser.add_argument("--matrix-summary-name", default="phase7_surface_memory_ablation_matrix_summary.json")
    parser.add_argument("--enable-telemetry", action="store_true")
    parser.add_argument("--telemetry-interval-sec", type=float)
    parser.add_argument("--skip-evaluator", action="store_true")
    parser.add_argument("--evaluator-root", type=Path, default=Path("/home/TJK/DEE/dee-eval"))
    parser.add_argument("--benchmark-root", type=Path, default=Path("/data/TJK/DEE/data/processed"))
    parser.add_argument("--evaluator-out-root", type=Path)
    parser.add_argument("--out-root", type=Path, required=True)
    return parser.parse_args(argv)


def _validate_args(args: argparse.Namespace, config: dict[str, Any]) -> None:
    if args.split == "test":
        raise ValueError("Phase 7 rejects test split; test remains blocked")
    if args.split != "dev":
        raise ValueError(f"Phase 7 only permits dev split, got {args.split!r}")
    partial = bool(args.only_variant or args.only_seed is not None)
    if partial and not (
        (args.dry_run and args.allow_partial_dry_run)
        or (args.real_run and args.allow_real_partial_shard)
    ):
        raise ValueError("partial matrix selection requires --allow-partial-dry-run or --allow-real-partial-shard")
    if "/" in args.matrix_summary_name or args.matrix_summary_name in {"", ".", ".."}:
        raise ValueError("matrix summary name must be a file name")
    if args.stage == "limit50" and not args.allow_limit50 and not args.dry_run:
        raise ValueError("Phase 7 limit50 stage requires --allow-limit50")
    if args.stage == "full-dev" and not args.allow_full_dev:
        raise ValueError("Phase 7 full-dev stage requires --allow-full-dev")
    phase7 = config.get("phase7") or {}
    if phase7.get("train_used") is not False:
        raise ValueError("Phase 7 must not train; train_used must be false")
    if phase7.get("full_train_used") is not False:
        raise ValueError("Phase 7 full train must remain blocked")
    if phase7.get("test_blocked") is not True:
        raise ValueError("Phase 7 config must keep test blocked")
    missing = [variant_id for variant_id in VARIANT_ORDER if variant_id not in (config.get("variants") or {})]
    if missing:
        raise ValueError(f"Phase 7 config is missing variants: {missing}")


def _run_limit50_matrix(
    args: argparse.Namespace,
    *,
    config: dict[str, Any],
    gpu_selection: dict[str, Any],
) -> list[dict[str, Any]]:
    run_specs = _run_specs(config, args=args)
    freeze_manifest = _freeze_manifest(args, config=config, run_specs=run_specs, gpu_selection=gpu_selection)
    _write_json(args.out_root / "phase7_profile_freeze_manifest.json", freeze_manifest)
    summaries = []
    for spec in run_specs:
        timestamp = _created_slug()
        run_dir = args.out_root / f"phase7_{spec.variant.variant_id}_seed{spec.seed}_{timestamp}"
        run_dir.mkdir(parents=True, exist_ok=False)
        adapter_path = _phase6_adapter_path(
            args.phase6_runs_root,
            seed=spec.seed,
            real_run=bool(args.real_run),
        )
        run_config = _resolved_config(
            config,
            variant=spec.variant,
            seed=spec.seed,
            stage="limit50",
            args=args,
            adapter_path=adapter_path,
        )
        write_yaml(run_dir / "phase7_config.resolved.yaml", run_config)
        _write_json(run_dir / "phase7_profile_freeze_manifest.json", freeze_manifest)
        limit50 = _run_generate(
            args,
            config=run_config,
            run_dir=run_dir / "limit50",
            dataset=_dataset(args, config),
            data_root=_data_root(args, config),
            split=args.split,
            limit=int((config.get("phase7") or {}).get("limit50_predict_docs") or 50),
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
        limit50["grounding_diagnostics"] = _grounding_diagnostics(
            stage_dir=Path(limit50["run_dir"]),
            dataset=_dataset(args, config),
            split=args.split,
            data_root=Path(_data_root(args, config)),
            limit=int((config.get("phase7") or {}).get("limit50_predict_docs") or 50),
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
        _write_json(run_dir / "phase7_run_summary.json", summary)
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
            raise RuntimeError(f"missing completed Phase 7 limit50 run for {spec.variant.variant_id} seed {spec.seed}")
        previous = _read_json(existing / "phase7_run_summary.json")
        _require_profile_hash(args, existing)
        _require_limit50_gate(previous)
        adapter_path = str(previous.get("adapter_path") or "")
        full_dev_config = _resolved_config(
            config,
            variant=spec.variant,
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
        full_dev["grounding_diagnostics"] = _grounding_diagnostics(
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
        _write_json(existing / "phase7_run_summary.json", updated)
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
    telemetry = start_qwen_telemetry(
        config,
        run_dir,
        operation=f"phase7_{stage_name}_generate",
        total_items=len(documents),
    )
    backend: QwenGetmBackend | None = None
    try:
        backend = QwenGetmBackend(config=config, telemetry=telemetry)
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
        _release_qwen_backend(backend)
        gc.collect()
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
            "backend": "qwen",
            "dry_run": bool((config.get("run") or {}).get("dry_run", True)),
            "real_run": bool((config.get("run") or {}).get("real_run", False)),
            "profile": (config.get("run") or {}).get("profile"),
            "variant_id": (config.get("run") or {}).get("variant_id"),
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
            "phase7_stage": stage_name,
            "generation": _generation_metadata(config),
        },
    )
    _write_json(
        run_dir / "phase7_generate_command.json",
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
    _write_json(run_dir / "phase7_evaluator_handoff.json", {"handoff": handoff.to_dict(), "result": result})
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


def _grounding_diagnostics(
    *,
    stage_dir: Path,
    dataset: str,
    split: str,
    data_root: Path,
    limit: int | None,
) -> dict[str, Any]:
    prompt_rows = read_jsonl(stage_dir / f"prompts.{split}.jsonl")
    pred_rows = read_jsonl(stage_dir / "predictions" / dataset / f"{split}.canonical.pred.jsonl")
    doc_ids = [str(row.get("doc_id") or "") for row in prompt_rows]
    gold_docs = {
        document.doc_id: document
        for document in load_documents(dataset, split, data_root=data_root, mode="train", limit=limit)
        if document.doc_id in set(doc_ids)
    }
    selected_by_doc = {
        str(row.get("doc_id") or ""): [
            _surface_text(candidate) for candidate in (row.get("prompt_surface_candidates") or [])
        ]
        for row in prompt_rows
    }
    gold_args_by_doc = {doc_id: _gold_argument_texts(document) for doc_id, document in gold_docs.items()}
    content_by_doc = {doc_id: _document_content(document) for doc_id, document in gold_docs.items()}

    gold_total = sum(len(args) for args in gold_args_by_doc.values())
    recall_hits = {k: 0 for k in RECALL_KS}
    unlocated = 0
    ambiguous = 0
    for doc_id, gold_args in gold_args_by_doc.items():
        selected = selected_by_doc.get(doc_id, [])
        selected_counter = Counter(selected)
        for gold_text in gold_args:
            if selected_counter.get(gold_text, 0) == 0:
                unlocated += 1
            if selected_counter.get(gold_text, 0) > 1:
                ambiguous += 1
            for k in RECALL_KS:
                if gold_text in set(selected[:k]):
                    recall_hits[k] += 1

    selected_total = sum(len(values) for values in selected_by_doc.values())
    candidate_hits = 0
    for doc_id, selected in selected_by_doc.items():
        gold_set = set(gold_args_by_doc.get(doc_id, []))
        candidate_hits += sum(1 for surface in selected if surface in gold_set)

    pred_args = list(_prediction_arguments(pred_rows))
    hallucinated = 0
    non_surface = 0
    for doc_id, text in pred_args:
        content = content_by_doc.get(doc_id, "")
        selected_set = set(selected_by_doc.get(doc_id, []))
        if text and text not in content:
            hallucinated += 1
        if text and text not in selected_set:
            non_surface += 1

    diagnostics = {
        "diagnostic_scope": "post_hoc_dev_gold_audit_only",
        "gold_visible_to_prediction": False,
        "document_count": len(prompt_rows),
        "gold_argument_count": gold_total,
        "selected_candidate_count": selected_total,
        "candidate_recall_at_k": {
            str(k): _rate(recall_hits[k], gold_total) for k in RECALL_KS
        },
        "candidate_precision": _rate(candidate_hits, selected_total),
        "gold_argument_unlocated_rate": _rate(unlocated, gold_total),
        "ambiguous_match_rate": _rate(ambiguous, gold_total),
        "predicted_argument_count": len(pred_args),
        "hallucinated_argument_rate": _rate(hallucinated, len(pred_args)),
        "non_surface_argument_rate": _rate(non_surface, len(pred_args)),
        "counts": {
            "candidate_recall_hits": {str(k): recall_hits[k] for k in RECALL_KS},
            "candidate_precision_hits": candidate_hits,
            "gold_argument_unlocated_count": unlocated,
            "ambiguous_match_count": ambiguous,
            "hallucinated_argument_count": hallucinated,
            "non_surface_argument_count": non_surface,
        },
    }
    _write_json(stage_dir / "phase7_grounding_diagnostics.json", diagnostics)
    return diagnostics


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
        "phase6_adapter_reused": True,
        "train_used": False,
        "full_train_used": False,
        "limit50": int((config.get("phase7") or {}).get("limit50_predict_docs") or 50),
        "full_dev_used": full_dev is not None,
        "test_used": False,
        "hallucination_only_claim_blocked": True,
    }
    return {
        "phase": "Phase 7 surface memory ablation",
        "variant_id": spec.variant.variant_id,
        "profile": spec.variant.profile,
        "label": spec.variant.label,
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
    }
    if stage == "limit50":
        gate["full_dev_allowed"] = (
            not args.dry_run
            and not args.skip_evaluator
            and not bool(args.only_variant or args.only_seed is not None)
            and _limit50_matrix_gate(summaries)
        )
    return {
        "phase": "Phase 7 surface memory ablation",
        "scope": {
            "stage": stage,
            "dataset": _dataset(args, config),
            "split": args.split,
            "train_used": False,
            "full_train_used": False,
            "full_dev_used": stage == "full_dev",
            "test_used": False,
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
    manifest = _read_json(run_dir / "phase7_profile_freeze_manifest.json")
    expected = manifest.get("config_sha256")
    actual = _sha256(args.config)
    if expected != actual:
        raise RuntimeError("full dev blocked: Phase 7 config hash differs from frozen limit50 profile")


def _run_specs(config: dict[str, Any], *, args: argparse.Namespace) -> list[RunSpec]:
    seed_matrix = (config.get("phase7") or {}).get("seed_matrix") or {}
    specs = []
    for variant in _variant_specs(config):
        if args.only_variant and variant.variant_id != args.only_variant:
            continue
        seeds = [int(seed) for seed in seed_matrix.get(variant.variant_id, [])]
        for seed in seeds:
            if args.only_seed is not None and seed != args.only_seed:
                continue
            specs.append(RunSpec(variant=variant, seed=seed))
    if not specs:
        raise ValueError("Phase 7 run matrix is empty")
    return specs


def _variant_specs(config: dict[str, Any]) -> list[VariantSpec]:
    variants = config.get("variants") or {}
    specs = []
    for variant_id in VARIANT_ORDER:
        payload = variants.get(variant_id) or {}
        specs.append(
            VariantSpec(
                variant_id=variant_id,
                profile=f"phase7_{variant_id}",
                label=str(payload.get("label") or variant_id.replace("_", " ")),
            )
        )
    return specs


def _resolved_config(
    config: dict[str, Any],
    *,
    variant: VariantSpec,
    seed: int,
    stage: str,
    args: argparse.Namespace,
    adapter_path: str,
) -> dict[str, Any]:
    variant_overrides = ((config.get("variants") or {}).get(variant.variant_id) or {})
    resolved = _deep_merge(config, variant_overrides)
    resolved.pop("variants", None)
    run_cfg = dict(resolved.get("run") or {})
    run_cfg["profile"] = variant.profile
    run_cfg["variant_id"] = variant.variant_id
    run_cfg["dry_run"] = not bool(args.real_run)
    run_cfg["real_run"] = bool(args.real_run)
    resolved["run"] = run_cfg
    data_cfg = dict(resolved.get("data") or {})
    data_cfg["max_predict_docs"] = 50 if stage == "limit50" else None
    resolved["data"] = data_cfg
    predict_cfg = dict(resolved.get("predict") or {})
    predict_cfg["max_predict_docs"] = 50 if stage == "limit50" else None
    predict_cfg["split"] = args.split
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


def _phase6_adapter_path(phase6_runs_root: Path, *, seed: int, real_run: bool) -> str:
    pattern = f"phase6_S4_seed{seed}_*"
    candidates = [
        path for path in phase6_runs_root.glob(pattern) if (path / "phase6_run_summary.json").is_file()
    ]
    if not candidates:
        if real_run:
            raise RuntimeError(f"missing Phase 6 S4 seed {seed} run under {phase6_runs_root}")
        return "dry-run-no-adapter"
    latest = sorted(candidates)[-1]
    summary = _read_json(latest / "phase6_run_summary.json")
    adapter_path = str(((summary.get("train") or {}).get("adapter_dir")) or "")
    if not adapter_path and real_run:
        raise RuntimeError(f"missing adapter_dir in {latest / 'phase6_run_summary.json'}")
    return adapter_path or "dry-run-no-adapter"


def _latest_limit50_run(out_root: Path, spec: RunSpec) -> Path | None:
    pattern = f"phase7_{spec.variant.variant_id}_seed{spec.seed}_*"
    candidates = [path for path in out_root.glob(pattern) if (path / "phase7_run_summary.json").is_file()]
    if not candidates:
        return None
    return sorted(candidates)[-1]


def _select_gpu(config: dict[str, Any], *, force_gpu: str | None = None) -> dict[str, Any]:
    phase7 = config.get("phase7") or {}
    preferred = str(phase7.get("preferred_gpu") or "3")
    auto = bool(phase7.get("auto_select_idle_gpu", True))
    idle_memory_mb = int(phase7.get("idle_memory_mb") or 1024)
    idle_util_pct = int(phase7.get("idle_utilization_pct") or 15)
    fake = os.environ.get("SAGE_DEE_PHASE7_FAKE_NVIDIA_SMI")
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


def _parse_gpu_rows(text: str | None) -> list[dict[str, Any]]:
    rows = []
    for line in str(text or "").splitlines():
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
        "run_id": f"phase7_{stage_name}_{_created_slug()}",
        "method_name": "SAGE-DEE-v2-Phase7-Surface-Ablation",
        "method_family": "SAGE-DEE-v2",
        "stage": "predict",
        "dataset_version": dataset,
        "split_version": split,
        "evaluator_version": EVALUATOR_VERSION,
        "prediction_format": PREDICTION_FORMAT,
        "training_view": "phase6_s4_adapter_reused",
        "gold_view": f"processed/views/evaluator_gold/{dataset}",
        "seed": ((config.get("getm") or {}).get("generation") or {}).get("seed"),
        "backend": "qwen",
        "dry_run": bool((config.get("run") or {}).get("dry_run", True)),
        "real_run": bool((config.get("run") or {}).get("real_run", False)),
        "profile": (config.get("run") or {}).get("profile"),
        "variant_id": (config.get("run") or {}).get("variant_id"),
        "command_train": None,
        "command_infer": join(
            [sys.executable, "scripts/v2/run_phase7_surface_memory_ablation.py", "--stage", stage_name]
        ),
        "git_commit": _git_commit(),
        "created_at": _created_at(),
        "notes": "Phase 7 surface-memory ablation generation; test split remains blocked.",
    }


def _freeze_manifest(
    args: argparse.Namespace,
    *,
    config: dict[str, Any],
    run_specs: list[RunSpec],
    gpu_selection: dict[str, Any],
) -> dict[str, Any]:
    return {
        "phase": "Phase 7 surface memory ablation",
        "created_at": _created_at(),
        "config_path": str(args.config),
        "config_sha256": _sha256(args.config),
        "dataset": _dataset(args, config),
        "split": args.split,
        "train_used": False,
        "full_train_used": False,
        "test_blocked": True,
        "phase6_source_profile": (config.get("phase7") or {}).get("phase6_source_profile"),
        "run_matrix": [
            {"variant_id": spec.variant.variant_id, "profile": spec.variant.profile, "seed": spec.seed}
            for spec in run_specs
        ],
        "gpu_selection": gpu_selection,
        "no_prompt_parser_surface_memory_tuning_after_freeze": True,
    }


def _dataset(args: argparse.Namespace, config: dict[str, Any]) -> str:
    return str(args.dataset or ((config.get("data") or {}).get("dataset")) or "DuEE-Fin-dev500")


def _data_root(args: argparse.Namespace, config: dict[str, Any]) -> str:
    return str(args.data_root or ((config.get("data") or {}).get("data_root")) or "data")


def _gold_argument_texts(document: V2DatasetDocument) -> list[str]:
    if document.gold is None:
        return []
    texts = []
    for event in document.gold.events:
        if not isinstance(event, dict):
            continue
        arguments = event.get("arguments") or {}
        if not isinstance(arguments, dict):
            continue
        for values in arguments.values():
            if not isinstance(values, list):
                continue
            for value in values:
                if isinstance(value, dict):
                    text = _normalize_surface(str(value.get("text") or ""))
                    if text:
                        texts.append(text)
    return texts


def _prediction_arguments(rows: list[dict[str, Any]]) -> list[tuple[str, str]]:
    arguments = []
    for row in rows:
        doc_id = str(row.get("doc_id") or "")
        for event in row.get("events") or []:
            if not isinstance(event, dict):
                continue
            raw_arguments = event.get("arguments") or {}
            if not isinstance(raw_arguments, dict):
                continue
            for values in raw_arguments.values():
                if not isinstance(values, list):
                    continue
                for value in values:
                    if isinstance(value, dict):
                        text = _normalize_surface(str(value.get("text") or ""))
                        if text:
                            arguments.append((doc_id, text))
    return arguments


def _document_content(document: V2DatasetDocument) -> str:
    parts = [document.input.content]
    if document.input.content_raw and document.input.content_raw != document.input.content:
        parts.append(document.input.content_raw)
    return _normalize_surface("\n".join(parts))


def _surface_text(candidate: Any) -> str:
    if not isinstance(candidate, dict):
        return ""
    return _normalize_surface(str(candidate.get("surface") or ""))


def _normalize_surface(text: str) -> str:
    return re.sub(r"\s+", "", text).strip()


def _rate(numerator: int, denominator: int) -> float | None:
    if denominator == 0:
        return None
    return numerator / denominator


if __name__ == "__main__":
    raise SystemExit(main())
