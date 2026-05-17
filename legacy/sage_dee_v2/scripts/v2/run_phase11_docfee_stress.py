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
from sage_dee.v2.data_interface.jsonl import read_jsonl  # noqa: E402
from sage_dee.v2.data_interface.schema_registry import load_schema  # noqa: E402
from sage_dee.v2.getm.candidate_generator import generate_getm_candidate_files  # noqa: E402
from sage_dee.v2.getm.generation_diagnostics import DIAGNOSTIC_VERSION  # noqa: E402
from sage_dee.v2.getm.mock_backend import MockGetmBackend  # noqa: E402
from sage_dee.v2.getm.qwen_backend import QwenGetmBackend, _generation_metadata, start_qwen_telemetry  # noqa: E402
from sage_dee.v2.pipeline.evaluator_handoff import build_evaluator_handoff, run_evaluator_handoff  # noqa: E402
from sage_dee.v2.pipeline.run_manifest import EVALUATOR_VERSION, PREDICTION_FORMAT  # noqa: E402
from scripts.v2.analyze_phase11_docfee_stress import (  # noqa: E402
    DEFAULT_LENGTH_BUCKETS,
    LengthBucketSpec,
    build_phase11_docfee_stress_analysis,
    write_phase11_docfee_stress_outputs,
)
from scripts.v2.run_phase6_sft_baseline_matrix import (  # noqa: E402
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
from scripts.v2.run_phase10_chfinann_frozen_profile import (  # noqa: E402
    _canonical_validation,
    _phase6_adapter_path,
)


@dataclass(frozen=True)
class BaselineSpec:
    baseline_id: str
    profile: str
    phase6_profile: str
    label: str
    baseline_mode: str


S4_BASELINE = BaselineSpec(
    baseline_id="S4",
    profile="phase11_s4_role_safe_surface_memory",
    phase6_profile="phase6_s4_role_safe_surface_memory",
    label="role-safe + surface memory SFT",
    baseline_mode="role_safe_surface_memory",
)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    if args.dry_run and args.real_run:
        print("Phase 11 runner cannot use both --dry-run and --real-run", file=sys.stderr)
        return 2
    if not args.dry_run and not args.real_run:
        args.real_run = True
    config = read_yaml(args.config)
    try:
        _validate_args(args, config)
        phase9_gate, phase10_gate = _require_phase_gates(args, config)
        adapter_path = _resolve_adapter_path(args, config)
    except (RuntimeError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2

    args.out_dir.mkdir(parents=True, exist_ok=True)
    gpu_selection = _select_gpu(config, force_gpu=args.force_gpu)
    if gpu_selection.get("selected_gpu"):
        os.environ["CUDA_VISIBLE_DEVICES"] = str(gpu_selection["selected_gpu"])

    limit = _predict_limit(args, config)
    stage_name = "limit50" if args.limit is not None else "full_dev"
    run_config = _resolved_config(
        config,
        args=args,
        adapter_path=adapter_path,
        limit=limit,
    )
    write_yaml(args.out_dir / "phase11_config.resolved.yaml", run_config)
    generation = _run_generate(
        args,
        config=run_config,
        dataset=_dataset(args, config),
        split=args.split,
        data_root=_data_root(args, config),
        limit=limit,
        stage_name=stage_name,
    )
    benchmark_root = _benchmark_root(args, config)
    if args.limit is not None and not args.skip_evaluator:
        benchmark_root = _write_subset_benchmark(
            out_root=args.out_dir / "limit_subset_benchmark",
            source_data_root=Path(_data_root(args, config)),
            dataset=_dataset(args, config),
            split=args.split,
            doc_ids=_prompt_doc_ids(args.out_dir / f"prompts.{args.split}.jsonl"),
        )
    evaluator = _run_evaluator(
        args,
        run_dir=args.out_dir,
        dataset=_dataset(args, config),
        split=args.split,
        benchmark_root=benchmark_root,
        out_dir=args.out_dir / "evaluator_artifacts",
    )
    evaluator_summary = _summarize_evaluator(evaluator, dataset=_dataset(args, config), split=args.split)
    analysis = build_phase11_docfee_stress_analysis(
        run_root=args.out_dir,
        dataset=_dataset(args, config),
        split=args.split,
        data_root=_data_root(args, config),
        evaluator_artifact_root=evaluator_summary.get("evaluator_artifact_root"),
        length_buckets=_length_buckets(config),
        length_measure_name=str(((config.get("data") or {}).get("length_measure")) or "char_count"),
        length_measure_source=str(((config.get("data") or {}).get("length_measure_source")) or "content_raw"),
    )
    diagnostics = write_phase11_docfee_stress_outputs(args.out_dir, analysis)
    summary = _run_summary(
        args,
        config=config,
        adapter_path=adapter_path,
        gpu_selection=gpu_selection,
        phase9_gate=phase9_gate,
        phase10_gate=phase10_gate,
        generation=generation,
        evaluator=evaluator_summary,
        diagnostics=diagnostics,
        stage_name=stage_name,
        limit=limit,
    )
    _write_json(args.out_dir / "phase11_run_summary.json", summary)
    print(f"run_root={args.out_dir}")
    print(f"canonical_path={generation['canonical_path']}")
    print(f"analysis_json={diagnostics['analysis']}")
    if evaluator_summary.get("evaluator_artifact_root"):
        print(f"evaluator_artifact_root={evaluator_summary['evaluator_artifact_root']}")
    return 0


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run SAGE v2 Phase 11 DocFEE prediction-only stress analysis.")
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--dataset")
    parser.add_argument("--split", default="dev")
    parser.add_argument("--data-root")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--real-run", action="store_true")
    parser.add_argument("--skip-evaluator", action="store_true")
    parser.add_argument("--allow-missing-gate-for-local-test", action="store_true")
    parser.add_argument("--shard-index", type=int)
    parser.add_argument("--shard-count", type=int)
    parser.add_argument("--force-gpu")
    parser.add_argument("--phase6-runs-root", type=Path)
    parser.add_argument("--phase9-aggregate", type=Path)
    parser.add_argument("--phase10-aggregate", type=Path)
    parser.add_argument("--evaluator-root", type=Path)
    parser.add_argument("--benchmark-root", type=Path)
    parser.add_argument("--out-dir", type=Path, required=True)
    return parser.parse_args(argv)


def _validate_args(args: argparse.Namespace, config: dict[str, Any]) -> None:
    if args.split == "test":
        raise ValueError("Phase 11 rejects test split; test split remains blocked")
    if args.split != "dev":
        raise ValueError(f"Phase 11 only permits dev split, got {args.split!r}")
    if _dataset(args, config) == "test" or _dataset(args, config) != "DocFEE-dev1000":
        raise ValueError("Phase 11 only permits dataset DocFEE-dev1000")
    if args.limit is not None and args.limit <= 0:
        raise ValueError("Phase 11 --limit must be positive")
    if (args.shard_index is None) != (args.shard_count is None):
        raise ValueError("Phase 11 sharding requires both --shard-index and --shard-count")
    if args.shard_count is not None:
        if args.shard_count <= 1:
            raise ValueError("Phase 11 --shard-count must be greater than 1")
        if args.shard_index is None or args.shard_index < 0 or args.shard_index >= args.shard_count:
            raise ValueError("Phase 11 --shard-index must satisfy 0 <= index < shard_count")
        if not args.skip_evaluator:
            raise ValueError("Phase 11 shard runs require --skip-evaluator; merge handles external evaluator handoff")
    phase11 = config.get("phase11") or {}
    for key in ("train_used", "full_train_used", "docfee_train_used"):
        if phase11.get(key) is not False:
            raise ValueError(f"Phase 11 requires {key}=false; training remains blocked")
    if phase11.get("test_blocked") is not True:
        raise ValueError("Phase 11 config must keep test blocked")
    if phase11.get("no_profile_tuning") is not True:
        raise ValueError("Phase 11 rejects profile tuning; no_profile_tuning must be true")
    if phase11.get("no_post_full_dev_tuning") is not True:
        raise ValueError("Phase 11 requires no_post_full_dev_tuning=true")
    if phase11.get("systems") != ["S4"]:
        raise ValueError("Phase 11 only permits S4 system by default")
    if int(phase11.get("seed") or -1) != 42:
        raise ValueError("Phase 11 only permits seed 42")
    adapter_source = phase11.get("adapter_source") or {}
    expected_adapter = {
        "baseline_id": "S4",
        "seed": 42,
        "phase6_profile": "phase6_s4_role_safe_surface_memory",
    }
    if adapter_source != expected_adapter:
        raise ValueError("Phase 11 requires the Phase 6 S4 seed42 frozen adapter source")
    if ((config.get("data") or {}).get("dataset")) != "DocFEE-dev1000":
        raise ValueError("Phase 11 data.dataset must be DocFEE-dev1000")
    if ((config.get("predict") or {}).get("dataset")) != "DocFEE-dev1000":
        raise ValueError("Phase 11 predict.dataset must be DocFEE-dev1000")
    if ((config.get("predict") or {}).get("split")) != "dev":
        raise ValueError("Phase 11 predict.split must be dev")


def _require_phase_gates(
    args: argparse.Namespace,
    config: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    if args.allow_missing_gate_for_local_test:
        return {"skipped_for_local_test": True}, {"skipped_for_local_test": True}
    return (
        _require_phase9_gate(_phase9_aggregate(args, config)),
        _require_phase10_gate(_phase10_aggregate(args, config)),
    )


def _require_phase9_gate(path: Path | None) -> dict[str, Any]:
    if path is None:
        raise RuntimeError("Phase 9 aggregate is required before Phase 11")
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
        raise RuntimeError(f"Phase 9 aggregate does not allow Phase 11; failed gate keys: {failed}")
    return {key: gate.get(key) for key in required}


def _require_phase10_gate(path: Path | None) -> dict[str, Any]:
    if path is None:
        raise RuntimeError("Phase 10 aggregate is required before Phase 11")
    if not path.is_file():
        raise RuntimeError(f"Phase 10 aggregate is missing: {path}")
    payload = _read_json(path)
    gate = payload.get("gate") or {}
    required = {
        "required_seed_coverage": True,
        "test_blocked": True,
        "train_blocked": True,
        "full_train_blocked": True,
        "no_chfinann_tuning": True,
        "robustness_evidence_complete": True,
    }
    failed = [key for key, expected in required.items() if gate.get(key) is not expected]
    if failed:
        raise RuntimeError(f"Phase 10 aggregate does not allow Phase 11; failed gate keys: {failed}")
    return {key: gate.get(key) for key in required}


def _resolve_adapter_path(args: argparse.Namespace, config: dict[str, Any]) -> str:
    if args.dry_run and args.allow_missing_gate_for_local_test:
        return str(((config.get("getm") or {}).get("qwen") or {}).get("adapter_path") or "LOCAL_TEST_PHASE6_S4_SEED42")
    return _phase6_adapter_path(_phase6_runs_root(args, config), baseline=S4_BASELINE, seed=42)


def _run_generate(
    args: argparse.Namespace,
    *,
    config: dict[str, Any],
    dataset: str,
    split: str,
    data_root: str,
    limit: int | None,
    stage_name: str,
) -> dict[str, Any]:
    schema = load_schema(dataset, data_root=data_root)
    documents = _load_predict_documents(
        dataset=dataset,
        split=split,
        data_root=data_root,
        limit=limit,
        shard_index=args.shard_index,
        shard_count=args.shard_count,
    )
    telemetry = None
    backend: QwenGetmBackend | MockGetmBackend | None = None
    try:
        if args.real_run:
            telemetry = start_qwen_telemetry(
                config,
                args.out_dir,
                operation=f"phase11_{stage_name}_generate",
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
            out_dir=args.out_dir,
        )
    finally:
        if isinstance(backend, QwenGetmBackend):
            _release_qwen_backend(backend)
            gc.collect()
        if telemetry is not None:
            telemetry.finish()
    _write_json(args.out_dir / "run_manifest.json", _run_manifest(config=config, dataset=dataset, split=split))
    _write_json(
        args.out_dir / "generation_manifest.json",
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
            "shard": _shard_payload(args),
            "k": 1,
            "prompts_path": str(output.prompts_path),
            "raw_outputs_path": str(output.raw_outputs_path),
            "parsed_candidates_path": str(output.parsed_candidates_path),
            "parse_diagnostics_path": str(output.parse_diagnostics_path),
            "canonical_predictions_path": str(output.canonical_predictions_path),
            "gold_visible": False,
            "phase11_stage": stage_name,
            "generation": _generation_metadata(config) if args.real_run else {},
        },
    )
    _write_json(
        args.out_dir / "phase11_generate_command.json",
        {
            "internal_runner": True,
            "stage": stage_name,
            "limit": limit,
            "returncode": 0,
            "env": {"CUDA_VISIBLE_DEVICES": os.environ.get("CUDA_VISIBLE_DEVICES")},
        },
    )
    return _summarize_generation(run_dir=args.out_dir, dataset=dataset, split=split)


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
        data_repo_root=_evaluator_root(args),
        out_dir=out_dir,
        benchmark_root=benchmark_root,
        strict=True,
    )
    result = run_evaluator_handoff(handoff)
    _write_json(run_dir / "phase11_evaluator_handoff.json", {"handoff": handoff.to_dict(), "result": result})
    return {
        "attempted": result["attempted"],
        "returncode": result["returncode"],
        "artifact_out_dir": str(out_dir),
        "artifact_root": _extract_artifact_root(result.get("stdout")),
        "stdout": result.get("stdout"),
        "stderr": result.get("stderr"),
    }


def _summarize_generation(*, run_dir: Path, dataset: str, split: str) -> dict[str, Any]:
    diagnostics = _read_json(run_dir / f"parse_diagnostics.{split}.json")
    parsed_rows = read_jsonl(run_dir / f"parsed_candidates.{split}.jsonl")
    canonical_path = run_dir / "predictions" / dataset / f"{split}.canonical.pred.jsonl"
    canonical_rows = read_jsonl(canonical_path)
    diagnostic_counts = diagnostics.get("diagnostic_counts") or {}
    parse_status_counts = diagnostics.get("parse_status_counts") or {}
    validation = _canonical_validation(canonical_rows)
    return {
        "generation_manifest_path": str(run_dir / "generation_manifest.json"),
        "run_manifest_path": str(run_dir / "run_manifest.json"),
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
    adapter_path: str,
    gpu_selection: dict[str, Any],
    phase9_gate: dict[str, Any],
    phase10_gate: dict[str, Any],
    generation: dict[str, Any],
    evaluator: dict[str, Any],
    diagnostics: dict[str, Path],
    stage_name: str,
    limit: int | None,
) -> dict[str, Any]:
    scope = {
        "dataset": _dataset(args, config),
        "split": args.split,
        "document_count": generation.get("canonical_rows"),
        "stage": stage_name,
        "limit": limit,
        "shard": _shard_payload(args),
        "phase6_adapter_reused": True,
        "train_used": False,
        "full_train_used": False,
        "docfee_train_used": False,
        "test_used": False,
        "dry_run": bool(args.dry_run),
        "real_run": bool(args.real_run),
        "no_profile_tuning": True,
        "no_post_full_dev_tuning": True,
        "no_prompt_parser_surface_tuning": True,
    }
    return {
        "phase": "Phase 11 DocFEE stress analysis",
        "dataset": _dataset(args, config),
        "split": args.split,
        "baseline_id": "S4",
        "profile": S4_BASELINE.profile,
        "phase6_source_profile": S4_BASELINE.phase6_profile,
        "seed": 42,
        "run_dir": str(args.out_dir),
        "config_path": str(args.config),
        "config_sha256": _sha256(args.config),
        "adapter_path": adapter_path,
        "phase9_gate": phase9_gate,
        "phase10_gate": phase10_gate,
        "gpu_selection": gpu_selection,
        "scope": scope,
        "generation": generation,
        "evaluator": evaluator,
        "diagnostics": {key: str(path) for key, path in diagnostics.items()},
        "gate": {
            "prediction_only_completed": True,
            "aggregate_required": True,
            "test_blocked": True,
            "train_blocked": True,
            "full_train_blocked": True,
            "no_profile_tuning": True,
            "no_long_document_sota_claim": True,
        },
    }


def _resolved_config(
    config: dict[str, Any],
    *,
    args: argparse.Namespace,
    adapter_path: str,
    limit: int | None,
) -> dict[str, Any]:
    profile_overrides = ((config.get("profiles") or {}).get(S4_BASELINE.profile) or {})
    resolved = _deep_merge(config, profile_overrides)
    resolved.pop("profiles", None)
    run_cfg = dict(resolved.get("run") or {})
    run_cfg["profile"] = S4_BASELINE.profile
    run_cfg["baseline_id"] = S4_BASELINE.baseline_id
    run_cfg["dry_run"] = bool(args.dry_run)
    run_cfg["real_run"] = bool(args.real_run)
    resolved["run"] = run_cfg
    data_cfg = dict(resolved.get("data") or {})
    data_cfg["dataset"] = _dataset(args, config)
    data_cfg["data_root"] = _data_root(args, config)
    data_cfg["max_train_docs"] = 0
    data_cfg["max_predict_docs"] = limit
    resolved["data"] = data_cfg
    predict_cfg = dict(resolved.get("predict") or {})
    predict_cfg["dataset"] = _dataset(args, config)
    predict_cfg["split"] = args.split
    predict_cfg["data_root"] = _data_root(args, config)
    predict_cfg["max_predict_docs"] = limit
    resolved["predict"] = predict_cfg
    generation = dict((resolved.get("getm") or {}).get("generation") or {})
    generation["seed"] = 42
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


def _load_predict_documents(
    *,
    dataset: str,
    split: str,
    data_root: str,
    limit: int | None,
    shard_index: int | None,
    shard_count: int | None,
) -> list[Any]:
    documents = load_documents(dataset, split, data_root=data_root, mode="predict", limit=limit)
    if shard_index is None or shard_count is None:
        return documents
    return [document for index, document in enumerate(documents) if index % shard_count == shard_index]


def _shard_payload(args: argparse.Namespace) -> dict[str, int] | None:
    if args.shard_index is None or args.shard_count is None:
        return None
    return {"index": int(args.shard_index), "count": int(args.shard_count)}


def _run_manifest(*, config: dict[str, Any], dataset: str, split: str) -> dict[str, Any]:
    return {
        "run_id": f"phase11_docfee_stress_{_created_slug()}",
        "method_name": "SAGE-DEE-v2-Phase11-DocFEE-Stress",
        "method_family": "SAGE-DEE-v2",
        "stage": "predict",
        "dataset_version": dataset,
        "split_version": split,
        "evaluator_version": EVALUATOR_VERSION,
        "prediction_format": PREDICTION_FORMAT,
        "training_view": "DuEE-Fin Phase 6 S4 seed42 frozen adapter",
        "gold_view": f"processed/views/evaluator_gold/{dataset}",
        "seed": 42,
        "backend": "qwen" if (config.get("run") or {}).get("real_run") else "mock",
        "dry_run": bool((config.get("run") or {}).get("dry_run", True)),
        "real_run": bool((config.get("run") or {}).get("real_run", False)),
        "profile": (config.get("run") or {}).get("profile"),
        "command_train": None,
        "command_infer": join([sys.executable, "scripts/v2/run_phase11_docfee_stress.py"]),
        "git_commit": _git_commit(),
        "created_at": _created_at(),
        "notes": (
            "Phase 11 prediction-only DocFEE dev stress analysis; no train, no test, "
            "no prompt/parser/surface-memory/profile/evaluator tuning."
        ),
    }


def _select_gpu(config: dict[str, Any], *, force_gpu: str | None = None) -> dict[str, Any]:
    phase11 = config.get("phase11") or {}
    preferred = str(phase11.get("preferred_gpu") or "3")
    auto = bool(phase11.get("auto_select_idle_gpu", True))
    idle_memory_mb = int(phase11.get("idle_memory_mb") or 1024)
    idle_util_pct = int(phase11.get("idle_utilization_pct") or 15)
    fake = os.environ.get("SAGE_DEE_PHASE11_FAKE_NVIDIA_SMI")
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


def _phase6_runs_root(args: argparse.Namespace, config: dict[str, Any]) -> Path:
    configured = args.phase6_runs_root or (config.get("phase11") or {}).get("phase6_runs_root")
    if configured is None:
        raise RuntimeError("Phase 6 runs root is required")
    return Path(configured)


def _phase9_aggregate(args: argparse.Namespace, config: dict[str, Any]) -> Path | None:
    configured = args.phase9_aggregate or (config.get("phase11") or {}).get("phase9_source_aggregate")
    return Path(configured) if configured else None


def _phase10_aggregate(args: argparse.Namespace, config: dict[str, Any]) -> Path | None:
    configured = args.phase10_aggregate or (config.get("phase11") or {}).get("phase10_source_aggregate")
    return Path(configured) if configured else None


def _evaluator_root(args: argparse.Namespace) -> Path:
    return args.evaluator_root or Path("/home/TJK/DEE/dee-eval")


def _benchmark_root(args: argparse.Namespace, config: dict[str, Any]) -> Path:
    configured = args.benchmark_root or (config.get("evaluation") or {}).get("benchmark_root")
    return Path(configured or "/data/TJK/DEE/data/processed")


def _dataset(args: argparse.Namespace, config: dict[str, Any]) -> str:
    return str(
        args.dataset
        or ((config.get("phase11") or {}).get("dataset"))
        or ((config.get("data") or {}).get("dataset"))
    )


def _data_root(args: argparse.Namespace, config: dict[str, Any]) -> str:
    return str(args.data_root or ((config.get("data") or {}).get("data_root")) or "data")


def _predict_limit(args: argparse.Namespace, config: dict[str, Any]) -> int | None:
    if args.limit is not None:
        return args.limit
    value = (config.get("phase11") or {}).get("max_predict_docs")
    return int(value) if value is not None else None


def _length_buckets(config: dict[str, Any]) -> tuple[LengthBucketSpec, ...]:
    rows = (config.get("phase11") or {}).get("length_buckets")
    if not rows:
        return DEFAULT_LENGTH_BUCKETS
    return tuple(
        LengthBucketSpec(
            name=str(row["name"]),
            min_exclusive=row.get("min_exclusive"),
            max_inclusive=row.get("max_inclusive"),
        )
        for row in rows
    )


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    merged = deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = deepcopy(value)
    return merged


def _read_json(path: str | Path) -> dict[str, Any]:
    with Path(path).open(encoding="utf-8") as handle:
        payload = __import__("json").load(handle)
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object: {path}")
    return payload


if __name__ == "__main__":
    raise SystemExit(main())
