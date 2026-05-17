from __future__ import annotations

import argparse
import gc
import json
import os
import re
import shutil
import subprocess
import sys
from collections.abc import Sequence
from copy import deepcopy
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
    _release_qwen_backend,
    _sha256,
    _telemetry_summary,
    _write_json,
)

FINAL_SYSTEM_ID = "S4"
FINAL_BASELINE_LABEL = "role-safe + surface memory SFT"
FINAL_PHASE6_PROFILE = "phase6_s4_role_safe_surface_memory"
FINAL_PROFILE = "phase11_s4_role_safe_surface_memory"
FINAL_DATASET = "DuEE-Fin-dev500"
FINAL_SPLIT = "test"
FINAL_SEED = 42
FINAL_ADAPTER_PATH = (
    "/data/TJK/DEE/sage-dee/runs/phase6_S4_seed42_20260504T052553Z/train/artifacts/model/adapter"
)
FINAL_EVALUATOR_ROOT = "/home/TJK/DEE/dee-eval"
FINAL_BENCHMARK_ROOT = "/data/TJK/DEE/data/processed"
ORIGINAL_FAILED_ATTEMPT_RUN_ROOT = "/data/TJK/DEE/sage-dee/runs/phase13_final_test_seed42_20260506T065342Z"
PHASE13_1_FORENSIC_REPORT = REPO_ROOT / "docs/refactor/SAGE_V2_PHASE13_1_FAILURE_FORENSIC_AUDIT.md"
RECOVERY_REQUIRED_FORENSIC_MARKERS = (
    "failure_category: harness_precreated_run_dir_collision",
    "Qwen generation started: NO",
    "evaluator started: NO",
    "canonical predictions created: NO",
    "final metrics produced: NO",
    "test jsonl content read: NO evidence",
)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    config = read_yaml(args.config)
    manifest = _read_json(args.manifest)
    try:
        validate_final_args(args, config, manifest)
        validate_recovery_roots(run_root=args.out_dir, log_root=None)
    except (RuntimeError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2

    try:
        args.out_dir.mkdir(parents=True, exist_ok=False)
    except FileExistsError:
        print(f"Phase 13 refuses to reuse existing final-test run directory: {args.out_dir}", file=sys.stderr)
        return 2

    gpu_selection = _select_gpu(config)
    if gpu_selection.get("selected_gpu"):
        os.environ["CUDA_VISIBLE_DEVICES"] = str(gpu_selection["selected_gpu"])

    run_config = build_final_resolved_config(config, args=args)
    write_yaml(args.out_dir / "phase13_config.resolved.yaml", run_config)
    manifest_copy = args.out_dir / "SAGE_V2_FINAL_FREEZE_MANIFEST.copy.json"
    shutil.copy2(args.manifest, manifest_copy)
    _write_json(
        args.out_dir / "phase13_manifest_audit.json",
        {
            "manifest_path": str(args.manifest),
            "manifest_sha256": _sha256(args.manifest),
            "manifest_copy": str(manifest_copy),
            "selected_strategy": manifest["final_seed_strategy"]["selected_strategy"],
            "seed": int(args.seed),
            "final_test_command": manifest["final_test_command"]["command"],
            "phase13_2_operational_recovery_authorized": bool(
                args.allow_human_authorized_operational_recovery
            ),
            "git_commit": _git_commit(),
            "created_at": _created_at(),
        },
    )

    generation = _run_generation(args, config=run_config)
    evaluator = _run_evaluator(
        args,
        run_dir=args.out_dir,
        dataset=args.dataset,
        split=args.split,
        benchmark_root=args.benchmark_root,
        out_dir=args.out_dir / "evaluator_artifacts",
    )
    evaluator_summary = _summarize_evaluator(evaluator, dataset=args.dataset, split=args.split)
    summary = _run_summary(
        args,
        config=run_config,
        manifest=manifest,
        manifest_copy=manifest_copy,
        gpu_selection=gpu_selection,
        generation=generation,
        evaluator=evaluator_summary,
    )
    summary_path = args.out_dir / "phase13_final_test_summary.json"
    _write_json(summary_path, summary)

    print(f"run_root={args.out_dir}")
    print(f"canonical_path={generation['canonical_path']}")
    print(f"manifest_copy={manifest_copy}")
    print(f"final_metrics_json={summary_path}")
    if evaluator_summary.get("evaluator_artifact_root"):
        print(f"evaluator_artifact_root={evaluator_summary['evaluator_artifact_root']}")
    if evaluator_summary.get("evaluator_returncode") not in (0, None):
        return int(evaluator_summary["evaluator_returncode"]) or 1
    if evaluator_summary.get("evaluator_validation_ok") is not True:
        print("Phase 13 evaluator validation did not pass", file=sys.stderr)
        return 1
    return 0


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the SAGE v2 Phase 13 final test once.")
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--dataset", required=True)
    parser.add_argument("--split", required=True)
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--profile", required=True)
    parser.add_argument("--data-root")
    parser.add_argument("--phase6-runs-root", type=Path, required=True)
    parser.add_argument("--adapter-path", type=Path, required=True)
    parser.add_argument("--evaluator-root", type=Path, required=True)
    parser.add_argument("--benchmark-root", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument(
        "--allow-human-authorized-operational-recovery",
        action="store_true",
        help="Record explicit Phase 13.2 human authorization for the single operational recovery attempt.",
    )
    return parser.parse_args(argv)


def resolve_manifest_command(command: str, timestamp_utc: str) -> str:
    if not re.fullmatch(r"\d{8}T\d{6}Z", timestamp_utc):
        raise ValueError(f"timestamp must be a UTC slug like YYYYMMDDTHHMMSSZ, got {timestamp_utc!r}")
    marker = "<timestamp>"
    total = command.count(marker)
    if total == 0:
        return command
    run_root_match = re.search(r"(?:^|\s)RUN_ROOT=[^\s;&]*<timestamp>[^\s;&]*", command)
    if run_root_match is None:
        raise ValueError("<timestamp> may only appear in RUN_ROOT path materialization")
    if command[run_root_match.start() : run_root_match.end()].count(marker) != total:
        raise ValueError("<timestamp> may only appear in RUN_ROOT path materialization")
    return command.replace(marker, timestamp_utc)


def validate_final_args(
    args: argparse.Namespace,
    config: dict[str, Any],
    manifest: dict[str, Any],
    *,
    require_adapter_exists: bool = True,
) -> None:
    strategy = manifest.get("final_seed_strategy") or {}
    command = (manifest.get("final_test_command") or {}).get("command") or ""
    if strategy.get("selected_strategy") != "primary_seed_42_single_final_test":
        raise ValueError("Phase 13 requires selected_strategy=primary_seed_42_single_final_test")
    if int(strategy.get("primary_seed") or -1) != FINAL_SEED:
        raise ValueError("Phase 13 requires manifest primary_seed=42")
    if manifest.get("final_test_executed") is not False:
        raise ValueError("Phase 13 entry requires manifest final_test_executed=false")
    if (manifest.get("final_test_command") or {}).get("executed") is not False:
        raise ValueError("Phase 13 entry requires manifest final_test_command.executed=false")
    if manifest.get("final_system_id") != FINAL_SYSTEM_ID:
        raise ValueError("Phase 13 requires final_system_id=S4")
    if args.dataset != FINAL_DATASET:
        raise ValueError(f"Phase 13 final test must use dataset {FINAL_DATASET}")
    if args.split != FINAL_SPLIT:
        raise ValueError("Phase 13 final test must use split test")
    if int(args.seed) != FINAL_SEED:
        raise ValueError("Phase 13 final test must use seed 42")
    if args.profile != FINAL_PROFILE:
        raise ValueError(f"Phase 13 final test must use profile {FINAL_PROFILE}")
    if str(args.adapter_path) != str((manifest.get("SFT_checkpoint") or {}).get("adapter_path")):
        raise ValueError("Phase 13 adapter path must match the freeze manifest")
    if str(args.adapter_path) != FINAL_ADAPTER_PATH:
        raise ValueError("Phase 13 adapter path must remain the frozen S4 seed42 adapter")
    validate_manifest_adapter_path(args.adapter_path, manifest, require_exists=require_adapter_exists)
    if str(args.evaluator_root) != str((manifest.get("evaluator") or {}).get("root")):
        raise ValueError("Phase 13 evaluator root must match the freeze manifest")
    if str(args.evaluator_root) != FINAL_EVALUATOR_ROOT:
        raise ValueError("Phase 13 evaluator root must remain the frozen external evaluator")
    if str(args.benchmark_root) != FINAL_BENCHMARK_ROOT:
        raise ValueError("Phase 13 benchmark root must remain /data/TJK/DEE/data/processed")
    if "--dataset DuEE-Fin-dev500" not in command or "--split test" not in command or "--seed 42" not in command:
        raise ValueError("Phase 13 manifest command does not encode the frozen dataset/split/seed")
    if "--out-dir \"${RUN_ROOT}\"" not in command:
        raise ValueError("Phase 13 manifest command must write to the registered RUN_ROOT")
    if not _path_is_registered_in_command(args.config, command):
        raise ValueError("Phase 13 config path must match the freeze manifest command")
    if str(args.adapter_path) not in command:
        raise ValueError("Phase 13 adapter path must match the freeze manifest command")
    if str(args.evaluator_root) not in command:
        raise ValueError("Phase 13 evaluator root must match the freeze manifest command")
    if str(args.benchmark_root) not in command:
        raise ValueError("Phase 13 benchmark root must match the freeze manifest command")
    if args.profile not in (config.get("profiles") or {}):
        raise ValueError(f"Phase 13 profile is missing from config profiles: {args.profile}")
    phase11 = config.get("phase11") or {}
    if phase11.get("train_used") is not False or phase11.get("full_train_used") is not False:
        raise ValueError("Phase 13 requires a frozen prediction-only config with train/full_train disabled")
    if phase11.get("no_post_full_dev_tuning") is not True:
        raise ValueError("Phase 13 requires no_post_full_dev_tuning=true")
    validate_phase13_recovery_authorization(args)


def validate_manifest_adapter_path(
    adapter_path: Path,
    manifest: dict[str, Any],
    *,
    require_exists: bool = True,
) -> None:
    checkpoint = manifest.get("SFT_checkpoint") or {}
    manifest_adapter_path = Path(str(checkpoint.get("adapter_path") or ""))
    phase6_run_path = Path(str(checkpoint.get("phase6_seed42_run_path") or ""))
    if str(adapter_path) != str(manifest_adapter_path):
        raise ValueError("Phase 13 adapter path must match the freeze manifest")
    if not phase6_run_path:
        raise ValueError("Phase 13 manifest is missing phase6_seed42_run_path")
    if not _path_is_under(adapter_path, phase6_run_path):
        raise ValueError("Phase 13 adapter path must be under manifest phase6_seed42_run_path")
    if not require_exists:
        return
    if not adapter_path.is_dir():
        raise ValueError(f"Phase 13 adapter path is missing or not a directory: {adapter_path}")
    if adapter_path.is_symlink():
        raise ValueError(f"Phase 13 adapter path must not be a symlink: {adapter_path}")
    adapter_config = adapter_path / "adapter_config.json"
    model_files = [
        child
        for child in adapter_path.iterdir()
        if child.is_file() and child.name.startswith("adapter_model") and child.suffix in {".safetensors", ".bin"}
    ]
    if not adapter_config.is_file() or not model_files:
        raise ValueError("Phase 13 adapter path must contain adapter_config.json and adapter_model files")


def validate_phase13_recovery_authorization(
    args: argparse.Namespace,
    *,
    forensic_report_path: Path = PHASE13_1_FORENSIC_REPORT,
) -> None:
    is_recovery_path = "_recovery_" in str(args.out_dir)
    authorized = bool(getattr(args, "allow_human_authorized_operational_recovery", False))
    if not is_recovery_path and not authorized:
        return
    if not authorized:
        raise ValueError("Phase 13.2 recovery requires --allow-human-authorized-operational-recovery")
    if not forensic_report_path.is_file():
        raise RuntimeError(f"Phase 13.2 recovery requires Phase 13.1 forensic audit: {forensic_report_path}")
    report = forensic_report_path.read_text(encoding="utf-8")
    missing = [marker for marker in RECOVERY_REQUIRED_FORENSIC_MARKERS if marker not in report]
    if missing:
        raise RuntimeError(f"Phase 13.2 recovery requires Phase 13.1 forensic audit markers: {missing}")


def validate_recovery_roots(*, run_root: Path, log_root: Path | None) -> None:
    if run_root.exists():
        raise ValueError(f"Phase 13.2 recovery RUN_ROOT already exists and must not be reused: {run_root}")
    if log_root is None:
        return
    if run_root == log_root:
        raise ValueError("Phase 13.2 recovery LOG_ROOT must be separate from RUN_ROOT")
    if run_root in log_root.parents or log_root in run_root.parents:
        raise ValueError("Phase 13.2 recovery LOG_ROOT and RUN_ROOT must not be nested")


def build_phase13_recovery_log_wrapper_command(timestamp_utc: str) -> str:
    if not re.fullmatch(r"\d{8}T\d{6}Z", timestamp_utc):
        raise ValueError(f"timestamp must be a UTC slug like YYYYMMDDTHHMMSSZ, got {timestamp_utc!r}")
    run_root = f"/data/TJK/DEE/sage-dee/runs/phase13_final_test_seed42_recovery_{timestamp_utc}"
    log_root = f"/data/TJK/DEE/sage-dee/runs/phase13_recovery_logs/phase13_final_test_seed42_{timestamp_utc}"
    return (
        "ssh gpu-4090 'cd /home/TJK/DEE/sage-dee "
        f"&& RUN_ROOT={run_root} "
        f"&& LOG_ROOT={log_root} "
        '&& test ! -e "${RUN_ROOT}" && mkdir -p "${LOG_ROOT}" '
        "&& { PATH=/home/TJK/.conda/envs/tjk-feg/bin:$PATH "
        "/home/TJK/.conda/envs/tjk-feg/bin/python scripts/v2/run_phase13_final_test_once.py "
        "--config configs/v2/sage_v2_phase11_docfee_stress.yaml "
        "--manifest docs/refactor/SAGE_V2_FINAL_FREEZE_MANIFEST.json "
        "--dataset DuEE-Fin-dev500 --split test --seed 42 "
        "--profile phase11_s4_role_safe_surface_memory "
        "--phase6-runs-root /data/TJK/DEE/sage-dee/runs "
        f"--adapter-path {FINAL_ADAPTER_PATH} "
        f"--evaluator-root {FINAL_EVALUATOR_ROOT} "
        f"--benchmark-root {FINAL_BENCHMARK_ROOT} "
        '--out-dir "${RUN_ROOT}" '
        "--allow-human-authorized-operational-recovery "
        '> >(tee "${LOG_ROOT}/phase13_recovery.stdout.log") '
        '2> >(tee "${LOG_ROOT}/phase13_recovery.stderr.log" >&2); '
        'rc=$?; echo "phase13_recovery_returncode=${rc}" | tee "${LOG_ROOT}/phase13_recovery.returncode"; '
        'echo "RUN_ROOT=${RUN_ROOT}" | tee "${LOG_ROOT}/phase13_recovery.run_root"; '
        'echo "LOG_ROOT=${LOG_ROOT}" | tee "${LOG_ROOT}/phase13_recovery.log_root"; '
        "exit ${rc}; }'"
    )


def build_final_test_result_payload(
    *,
    original_failed_result: dict[str, Any],
    recovery_command: str,
    recovery_run_root: str,
    recovery_log_root: str,
    returncode: int,
    summary: dict[str, Any] | None = None,
    server_stdout: str = "",
    server_stderr: str = "",
) -> dict[str, Any]:
    generation = (summary or {}).get("generation") or {}
    evaluator = (summary or {}).get("evaluator") or {}
    final_metrics = (summary or {}).get("final_metrics") or {
        "event_table_micro_f1": None,
        "role_level_f1": None,
        "exact_record_f1": None,
        "evaluator_validation_ok": None,
    }
    succeeded = returncode == 0 and final_metrics.get("evaluator_validation_ok") is True
    return {
        "status": "phase13_2_operational_recovery_completed" if succeeded else "phase13_2_operational_recovery_failed",
        "original_failed_attempt_run_root": original_failed_result.get("run_root") or ORIGINAL_FAILED_ATTEMPT_RUN_ROOT,
        "original_failed_attempt_status": "failed_before_generation",
        "original_failed_attempt_result": original_failed_result,
        "recovery_authorized": True,
        "recovery_reason": "harness/logging run-dir collision before generation",
        "recovery_run_root": recovery_run_root,
        "recovery_log_root": recovery_log_root,
        "command_executed": recovery_command,
        "returncode": int(returncode),
        "server_stdout": server_stdout,
        "server_stderr": server_stderr,
        "seed": FINAL_SEED,
        "dataset": FINAL_DATASET,
        "split": FINAL_SPLIT,
        "profile": FINAL_PROFILE,
        "checkpoint": {"adapter_path": FINAL_ADAPTER_PATH},
        "evaluator_root": FINAL_EVALUATOR_ROOT,
        "benchmark_root": FINAL_BENCHMARK_ROOT,
        "generation_manifest_path": generation.get("generation_manifest_path"),
        "canonical_prediction_path": generation.get("canonical_path"),
        "canonical_prediction_exists": bool(generation.get("canonical_path")),
        "evaluator_artifact_root": evaluator.get("evaluator_artifact_root"),
        "evaluator_artifact_exists": bool(evaluator.get("evaluator_artifact_root")),
        "final_metrics_json": str(Path(recovery_run_root) / "phase13_final_test_summary.json") if summary else None,
        "final_metrics": final_metrics,
        "post_test_modification_locked": True,
        "additional_test_runs_blocked": True,
        "no_prompt_parser_surface_checkpoint_evaluator_modification": True,
        "no_seed_switching": True,
    }


def build_final_resolved_config(config: dict[str, Any], *, args: argparse.Namespace) -> dict[str, Any]:
    profile_overrides = ((config.get("profiles") or {}).get(args.profile) or {})
    resolved = _deep_merge(config, profile_overrides)
    resolved.pop("profiles", None)
    run_cfg = dict(resolved.get("run") or {})
    run_cfg["profile"] = args.profile
    run_cfg["baseline_id"] = FINAL_SYSTEM_ID
    run_cfg["dry_run"] = False
    run_cfg["real_run"] = True
    resolved["run"] = run_cfg

    data_cfg = dict(resolved.get("data") or {})
    data_cfg["dataset"] = args.dataset
    data_cfg["data_root"] = _data_root(args, config)
    data_cfg["max_train_docs"] = 0
    data_cfg["max_predict_docs"] = None
    resolved["data"] = data_cfg

    predict_cfg = dict(resolved.get("predict") or {})
    predict_cfg["dataset"] = args.dataset
    predict_cfg["split"] = args.split
    predict_cfg["data_root"] = _data_root(args, config)
    predict_cfg["max_predict_docs"] = None
    resolved["predict"] = predict_cfg

    generation = dict((resolved.get("getm") or {}).get("generation") or {})
    generation["seed"] = int(args.seed)
    generation["k_candidates"] = 1
    generation["do_sample"] = False
    generation["temperature"] = None
    generation["top_p"] = 1.0
    generation["deterministic"] = True
    generation["deterministic_warn_only"] = True
    generation["record_resolved_generation_config"] = True
    resolved.setdefault("getm", {})["generation"] = generation
    resolved.setdefault("getm", {}).setdefault("qwen", {})["adapter_path"] = str(args.adapter_path)
    return resolved


def build_phase13_run_manifest(
    *,
    dataset: str,
    split: str,
    profile: str,
    seed: int,
    command_argv: Sequence[str],
    recovery_authorized: bool = False,
) -> dict[str, Any]:
    return {
        "run_id": f"phase13_final_test_once_{_created_slug()}",
        "method_name": "SAGE-DEE-v2-Phase13-Final-Test-Once",
        "method_family": "SAGE-DEE-v2",
        "stage": "final_test_once",
        "dataset_version": dataset,
        "split_version": split,
        "evaluator_version": EVALUATOR_VERSION,
        "prediction_format": PREDICTION_FORMAT,
        "training_view": "DuEE-Fin Phase 6 S4 seed42 frozen adapter",
        "gold_view": f"processed/views/evaluator_gold/{dataset}",
        "seed": int(seed),
        "backend": "qwen",
        "dry_run": False,
        "real_run": True,
        "profile": profile,
        "command_train": None,
        "command_infer": join(command_argv),
        "git_commit": _git_commit(),
        "created_at": _created_at(),
        "phase13_final_test_once": True,
        "phase13_2_operational_recovery_authorized": bool(recovery_authorized),
        "test_used": True,
        "train_used": False,
        "full_train_used": False,
        "post_test_modification_locked": True,
        "notes": (
            "Phase 13 final test once under the frozen manifest; no seed switching, no training, "
            "and no prompt/parser/surface/checkpoint/evaluator modification."
        ),
    }


def _run_generation(args: argparse.Namespace, *, config: dict[str, Any]) -> dict[str, Any]:
    schema = load_schema(args.dataset, data_root=_data_root(args, config))
    documents = load_documents(args.dataset, args.split, data_root=_data_root(args, config), mode="predict", limit=None)
    telemetry = start_qwen_telemetry(
        config,
        args.out_dir,
        operation="phase13_final_test_once_generate",
        total_items=len(documents),
    )
    backend: QwenGetmBackend | None = None
    try:
        backend = QwenGetmBackend(config=config, telemetry=telemetry)
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
        _release_qwen_backend(backend)
        gc.collect()
        telemetry.finish()

    _write_json(
        args.out_dir / "run_manifest.json",
        build_phase13_run_manifest(
            dataset=args.dataset,
            split=args.split,
            profile=args.profile,
            seed=args.seed,
            command_argv=sys.argv,
            recovery_authorized=bool(args.allow_human_authorized_operational_recovery),
        ),
    )
    _write_json(
        args.out_dir / "generation_manifest.json",
        {
            "diagnostic_version": DIAGNOSTIC_VERSION,
            "backend": "qwen",
            "dry_run": False,
            "real_run": True,
            "profile": args.profile,
            "baseline_id": FINAL_SYSTEM_ID,
            "dataset": args.dataset,
            "split": args.split,
            "document_count": len(documents),
            "k": 1,
            "prompts_path": str(output.prompts_path),
            "raw_outputs_path": str(output.raw_outputs_path),
            "parsed_candidates_path": str(output.parsed_candidates_path),
            "parse_diagnostics_path": str(output.parse_diagnostics_path),
            "canonical_predictions_path": str(output.canonical_predictions_path),
            "gold_visible": False,
            "phase13_final_test_once": True,
            "phase13_2_operational_recovery_authorized": bool(
                args.allow_human_authorized_operational_recovery
            ),
            "test_used": True,
            "post_test_modification_locked": True,
            "generation": _generation_metadata(config),
        },
    )
    _write_json(
        args.out_dir / "phase13_generate_command.json",
        {
            "internal_runner": True,
            "returncode": 0,
            "env": {"CUDA_VISIBLE_DEVICES": os.environ.get("CUDA_VISIBLE_DEVICES")},
            "argv": sys.argv,
            "phase13_2_operational_recovery_authorized": bool(
                args.allow_human_authorized_operational_recovery
            ),
        },
    )
    return _summarize_generation(run_dir=args.out_dir, dataset=args.dataset, split=args.split)


def _run_evaluator(
    args: argparse.Namespace,
    *,
    run_dir: Path,
    dataset: str,
    split: str,
    benchmark_root: Path,
    out_dir: Path,
) -> dict[str, Any]:
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
    _write_json(run_dir / "phase13_evaluator_handoff.json", {"handoff": handoff.to_dict(), "result": result})
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
        "overall_metrics_path": metrics.get("overall_metrics_path"),
        "record_level_metrics_path": metrics.get("record_level_metrics_path"),
        "validation_report_path": metrics.get("validation_report_path"),
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
        metrics["overall_metrics_path"] = str(overall_path)
    if record_path.is_file():
        record = _read_json(record_path)
        metrics["exact_record_f1"] = record.get("record_f1_exact")
        metrics["record_level_metrics_path"] = str(record_path)
    if validation_path.is_file():
        validation = _read_json(validation_path)
        metrics["validation_ok"] = validation.get("ok")
        metrics["validation_report_path"] = str(validation_path)
    return metrics


def _run_summary(
    args: argparse.Namespace,
    *,
    config: dict[str, Any],
    manifest: dict[str, Any],
    manifest_copy: Path,
    gpu_selection: dict[str, Any],
    generation: dict[str, Any],
    evaluator: dict[str, Any],
) -> dict[str, Any]:
    final_metrics = {
        "event_table_micro_f1": evaluator.get("event_table_micro_f1"),
        "role_level_f1": evaluator.get("role_level_f1"),
        "exact_record_f1": evaluator.get("exact_record_f1"),
        "evaluator_validation_ok": evaluator.get("evaluator_validation_ok"),
    }
    return {
        "phase": "Phase 13 final test once",
        "dataset": args.dataset,
        "split": args.split,
        "baseline_id": FINAL_SYSTEM_ID,
        "profile": args.profile,
        "phase6_source_profile": FINAL_PHASE6_PROFILE,
        "seed": int(args.seed),
        "run_dir": str(args.out_dir),
        "config_path": str(args.config),
        "config_sha256": _sha256(args.config),
        "manifest_path": str(args.manifest),
        "manifest_sha256": _sha256(args.manifest),
        "manifest_copy": str(manifest_copy),
        "selected_strategy": (manifest.get("final_seed_strategy") or {}).get("selected_strategy"),
        "adapter_path": str(args.adapter_path),
        "gpu_selection": gpu_selection,
        "scope": {
            "dataset": args.dataset,
            "split": args.split,
            "document_count": generation.get("canonical_rows"),
            "phase6_adapter_reused": True,
            "test_used": True,
            "train_used": False,
            "full_train_used": False,
            "dry_run": False,
            "real_run": True,
            "no_profile_tuning": True,
            "no_post_full_dev_tuning": True,
            "no_prompt_parser_surface_tuning": True,
            "no_seed_switching": True,
            "post_test_modification_locked": True,
            "phase13_2_operational_recovery_authorized": bool(
                args.allow_human_authorized_operational_recovery
            ),
        },
        "generation": generation,
        "evaluator": evaluator,
        "final_metrics": final_metrics,
        "gate": {
            "final_test_once_completed": evaluator.get("evaluator_validation_ok") is True,
            "test_split_used_only_by_manifest": True,
            "train_blocked": True,
            "full_train_blocked": True,
            "no_seed_switching": True,
            "post_test_modification_locked": True,
            "no_sota_claim": True,
        },
        "final_claim_status": manifest.get("final_claim_status"),
    }


def _select_gpu(config: dict[str, Any]) -> dict[str, Any]:
    phase11 = config.get("phase11") or {}
    preferred = str(phase11.get("preferred_gpu") or "3")
    auto = bool(phase11.get("auto_select_idle_gpu", True))
    idle_memory_mb = int(phase11.get("idle_memory_mb") or 1024)
    idle_util_pct = int(phase11.get("idle_utilization_pct") or 15)
    rows = _query_gpu_rows()
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
            paths.extend(_forbidden_key_paths(child, prefix=f"{prefix}[{index}]"))
    return paths


def _data_root(args: argparse.Namespace, config: dict[str, Any]) -> str:
    return str(args.data_root or ((config.get("data") or {}).get("data_root")) or "data")


def _path_is_registered_in_command(path: Path, command: str) -> bool:
    path_text = str(path)
    if path_text in command:
        return True
    try:
        relative = path.resolve().relative_to(REPO_ROOT)
    except ValueError:
        return False
    return str(relative) in command


def _path_is_under(path: Path, parent: Path) -> bool:
    try:
        path.resolve(strict=False).relative_to(parent.resolve(strict=False))
    except ValueError:
        return False
    return True


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
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object: {path}")
    return payload


if __name__ == "__main__":
    raise SystemExit(main())
