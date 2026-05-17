from __future__ import annotations

import argparse
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
sys.path.insert(0, str(REPO_ROOT / "src"))

from sage_dee.io_utils import read_yaml, write_yaml  # noqa: E402
from sage_dee.v2.data_interface.dataset_loader import load_documents  # noqa: E402
from sage_dee.v2.data_interface.schema_registry import load_schema  # noqa: E402
from sage_dee.v2.getm.candidate_generator import generate_getm_candidate_files  # noqa: E402
from sage_dee.v2.getm.generation_diagnostics import DIAGNOSTIC_VERSION  # noqa: E402
from sage_dee.v2.getm.mock_backend import MockGetmBackend  # noqa: E402
from sage_dee.v2.getm.qwen_backend import QwenGetmBackend, _generation_metadata, start_qwen_telemetry  # noqa: E402
from sage_dee.v2.getm.scope_guard import validate_getm_prediction_scope  # noqa: E402
from sage_dee.v2.pipeline.run_manifest import EVALUATOR_VERSION, PREDICTION_FORMAT  # noqa: E402


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    config = _resolve_config(args)
    backend_name = args.backend or str((config.get("getm") or {}).get("backend") or "qwen")
    if backend_name == "qwen" and not _run_flag_allowed(config):
        print("real Qwen GETM inference requires explicit --real-run", file=sys.stderr)
        return 2

    out_dir = args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    data_cfg = config.get("data") or {}
    predict_cfg = config.get("predict") or {}
    dataset = str(args.dataset or predict_cfg.get("dataset") or data_cfg.get("dataset") or "DuEE-Fin-dev500")
    split = str(args.split or predict_cfg.get("split") or data_cfg.get("predict_split") or "dev")
    data_root = str(args.data_root or predict_cfg.get("data_root") or data_cfg.get("data_root") or "data")
    limit = args.limit
    if limit is None:
        limit = predict_cfg.get("max_predict_docs", data_cfg.get("max_predict_docs"))
    k = args.k or int(((config.get("getm") or {}).get("generation") or {}).get("k_candidates", 4))
    try:
        validate_getm_prediction_scope(
            config_path=args.config,
            config=config,
            profile=str((config.get("run") or {}).get("profile") or ""),
            split=split,
            limit=limit,
            allow_limit50=bool(args.allow_limit50),
        )
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    schema = load_schema(dataset, data_root=data_root)
    documents = load_documents(dataset, split, data_root=data_root, mode="predict", limit=limit)
    telemetry = None
    if backend_name == "qwen":
        telemetry = start_qwen_telemetry(
            config,
            out_dir,
            operation="generate_candidates",
            total_items=len(documents) * k,
        )
    try:
        backend = _backend(backend_name, config=config, mock_mode=args.mock_mode, telemetry=telemetry)
        output = generate_getm_candidate_files(
            documents=documents,
            dataset=dataset,
            split=split,
            schema=schema,
            backend=backend,
            k=k,
            out_dir=out_dir,
        )
    finally:
        if telemetry is not None:
            telemetry.finish()

    config_path = out_dir / "config.resolved.yaml"
    write_yaml(config_path, config)
    run_manifest_path = _write_json(
        out_dir / "run_manifest.json",
        _run_manifest(
            config=config,
            dataset=dataset,
            split=split,
            command_infer=_command(argv),
            backend=backend_name,
        ),
    )
    generation_manifest_path = _write_json(
        out_dir / "generation_manifest.json",
        {
            "diagnostic_version": DIAGNOSTIC_VERSION,
            "backend": backend_name,
            "dry_run": bool((config.get("run") or {}).get("dry_run", True)),
            "real_run": bool((config.get("run") or {}).get("real_run", False)),
            "profile": (config.get("run") or {}).get("profile"),
            "dataset": dataset,
            "split": split,
            "document_count": len(documents),
            "k": k,
            "prompts_path": str(output.prompts_path),
            "raw_outputs_path": str(output.raw_outputs_path),
            "parsed_candidates_path": str(output.parsed_candidates_path),
            "parse_diagnostics_path": str(output.parse_diagnostics_path),
            "canonical_predictions_path": str(output.canonical_predictions_path),
            "gold_visible": False,
            "generation": _backend_generation_metadata(backend, config),
        },
    )

    print(f"out_dir={out_dir}")
    print(f"config_resolved={config_path}")
    print(f"run_manifest={run_manifest_path}")
    print(f"generation_manifest={generation_manifest_path}")
    print(f"prompts={output.prompts_path}")
    print(f"raw_outputs={output.raw_outputs_path}")
    print(f"parsed_candidates={output.parsed_candidates_path}")
    print(f"parse_diagnostics={output.parse_diagnostics_path}")
    print(f"canonical_predictions={output.canonical_predictions_path}")
    return 0


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate SAGE-DEE v2 GETM Qwen candidate files.")
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--profile")
    parser.add_argument("--dry-run", dest="dry_run", action="store_true", default=None)
    parser.add_argument("--no-dry-run", dest="dry_run", action="store_false")
    parser.add_argument("--real-run", action="store_true")
    parser.add_argument("--backend", choices=("qwen", "mock"))
    parser.add_argument("--mock-mode", choices=("empty", "schema_only", "echo_candidates"), default="empty")
    parser.add_argument("--adapter-path")
    parser.add_argument("--dataset")
    parser.add_argument("--split")
    parser.add_argument("--data-root")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--k", type=int)
    parser.add_argument("--allow-limit50", action="store_true")
    parser.add_argument("--enable-telemetry", action="store_true")
    parser.add_argument("--telemetry-interval-sec", type=float)
    parser.add_argument("--vram-soft-limit-gb", type=float)
    parser.add_argument("--vram-target-min-gb", type=float)
    parser.add_argument("--vram-target-max-gb", type=float)
    parser.add_argument("--fail-on-vram-limit", action="store_true")
    parser.add_argument("--max-new-tokens", type=int)
    parser.add_argument("--do-sample", dest="do_sample", action="store_true", default=None)
    parser.add_argument("--no-do-sample", dest="do_sample", action="store_false")
    parser.add_argument("--temperature", type=_parse_optional_float, default=argparse.SUPPRESS)
    parser.add_argument("--top-p", type=float)
    parser.add_argument("--top-k", type=_parse_optional_int, default=argparse.SUPPRESS)
    parser.add_argument("--num-beams", type=int)
    parser.add_argument("--num-return-sequences", type=int)
    parser.add_argument("--repetition-penalty", type=float)
    parser.add_argument("--seed", type=_parse_optional_int, default=argparse.SUPPRESS)
    parser.add_argument("--deterministic", dest="deterministic", action="store_true", default=None)
    parser.add_argument("--no-deterministic", dest="deterministic", action="store_false")
    parser.add_argument("--deterministic-warn-only", dest="deterministic_warn_only", action="store_true", default=None)
    parser.add_argument("--no-deterministic-warn-only", dest="deterministic_warn_only", action="store_false")
    parser.add_argument(
        "--record-resolved-generation-config",
        dest="record_resolved_generation_config",
        action="store_true",
        default=None,
    )
    parser.add_argument(
        "--no-record-resolved-generation-config",
        dest="record_resolved_generation_config",
        action="store_false",
    )
    parser.add_argument("--use-response-prefix", dest="use_response_prefix", action="store_true", default=None)
    parser.add_argument("--no-use-response-prefix", dest="use_response_prefix", action="store_false")
    parser.add_argument("--response-prefix")
    parser.add_argument(
        "--enable-balanced-json-stopping",
        dest="enable_balanced_json_stopping",
        action="store_true",
        default=None,
    )
    parser.add_argument(
        "--no-enable-balanced-json-stopping",
        dest="enable_balanced_json_stopping",
        action="store_false",
    )
    parser.add_argument(
        "--stop-after-balanced-events-json",
        dest="stop_after_balanced_events_json",
        action="store_true",
        default=None,
    )
    parser.add_argument(
        "--no-stop-after-balanced-events-json",
        dest="stop_after_balanced_events_json",
        action="store_false",
    )
    parser.add_argument("--output-format", choices=("minimal_text", "argument_object"))
    parser.add_argument("--max-surface-candidates", type=int)
    parser.add_argument("--candidate-context-chars", type=_parse_optional_int, default=argparse.SUPPRESS)
    parser.add_argument("--candidate-render-mode", choices=("full", "compact"))
    parser.add_argument(
        "--enable-candidate-filtering",
        dest="enable_candidate_filtering",
        action="store_true",
        default=None,
    )
    parser.add_argument("--no-enable-candidate-filtering", dest="enable_candidate_filtering", action="store_false")
    parser.add_argument("--max-candidates-per-type", type=int)
    parser.add_argument(
        "--dedupe-surface-candidates",
        dest="dedupe_surface_candidates",
        action="store_true",
        default=None,
    )
    parser.add_argument("--no-dedupe-surface-candidates", dest="dedupe_surface_candidates", action="store_false")
    parser.add_argument(
        "--drop-low-value-company-fragments",
        dest="drop_low_value_company_fragments",
        action="store_true",
        default=None,
    )
    parser.add_argument(
        "--no-drop-low-value-company-fragments",
        dest="drop_low_value_company_fragments",
        action="store_false",
    )
    parser.add_argument("--prompt-token-budget", type=int)
    parser.add_argument(
        "--baseline-mode",
        choices=("direct_json", "schema_only", "role_safe", "role_safe_surface_memory"),
    )
    parser.add_argument(
        "--fail-on-prompt-token-limit",
        dest="fail_on_prompt_token_limit",
        action="store_true",
        default=None,
    )
    parser.add_argument("--no-fail-on-prompt-token-limit", dest="fail_on_prompt_token_limit", action="store_false")
    parser.add_argument("--out-dir", type=Path, default=Path("runs/v2_getm_qwen_generate"))
    return parser.parse_args(argv)



def _backend_generation_metadata(backend: Any, config: dict[str, Any]) -> dict[str, Any]:
    metadata = getattr(backend, "generation_metadata", None)
    if callable(metadata):
        metadata = metadata()
    if isinstance(metadata, dict):
        return dict(metadata)
    return _generation_metadata(config)

def _backend(name: str, *, config: dict[str, Any], mock_mode: str, telemetry: Any | None = None):
    if name == "mock":
        return MockGetmBackend(mode=mock_mode)
    if name == "qwen":
        return QwenGetmBackend(config=config, telemetry=telemetry)
    raise ValueError(f"unsupported GETM backend: {name}")


def _resolve_config(args: argparse.Namespace) -> dict[str, Any]:
    config = read_yaml(args.config)
    profile = args.profile or str((config.get("run") or {}).get("profile") or "local_dry_run")
    profile_overrides = ((config.get("profiles") or {}).get(profile) or {})
    config = _deep_merge(config, profile_overrides)
    run_cfg = dict(config.get("run") or {})
    run_cfg["profile"] = profile
    if args.real_run:
        run_cfg["real_run"] = True
        run_cfg["dry_run"] = False
    elif args.dry_run is not None:
        run_cfg["dry_run"] = bool(args.dry_run)
        run_cfg["real_run"] = False
    else:
        run_cfg.setdefault("dry_run", True)
        run_cfg.setdefault("real_run", False)
    config["run"] = run_cfg
    _apply_telemetry_args(config, args)
    _apply_generation_args(config, args)
    _apply_prompt_args(config, args)
    if args.adapter_path:
        config.setdefault("getm", {}).setdefault("qwen", {})["adapter_path"] = args.adapter_path
    return config



def _apply_generation_args(config: dict[str, Any], args: argparse.Namespace) -> None:
    generation = dict((config.get("getm") or {}).get("generation") or {})
    if args.max_new_tokens is not None:
        generation["max_new_tokens"] = args.max_new_tokens
    if args.do_sample is not None:
        generation["do_sample"] = bool(args.do_sample)
    if hasattr(args, "temperature"):
        generation["temperature"] = args.temperature
    if args.top_p is not None:
        generation["top_p"] = args.top_p
    if hasattr(args, "top_k"):
        generation["top_k"] = args.top_k
    if args.num_beams is not None:
        generation["num_beams"] = args.num_beams
    if args.num_return_sequences is not None:
        generation["num_return_sequences"] = args.num_return_sequences
    if args.repetition_penalty is not None:
        generation["repetition_penalty"] = args.repetition_penalty
    if hasattr(args, "seed"):
        generation["seed"] = args.seed
    if args.deterministic is not None:
        generation["deterministic"] = bool(args.deterministic)
    if args.deterministic_warn_only is not None:
        generation["deterministic_warn_only"] = bool(args.deterministic_warn_only)
    if args.record_resolved_generation_config is not None:
        generation["record_resolved_generation_config"] = bool(args.record_resolved_generation_config)
    if args.use_response_prefix is not None:
        generation["use_response_prefix"] = bool(args.use_response_prefix)
    if args.response_prefix is not None:
        generation["response_prefix"] = args.response_prefix
    if args.enable_balanced_json_stopping is not None:
        generation["enable_balanced_json_stopping"] = bool(args.enable_balanced_json_stopping)
    if args.stop_after_balanced_events_json is not None:
        generation["stop_after_balanced_events_json"] = bool(args.stop_after_balanced_events_json)
    if args.output_format is not None:
        config.setdefault("getm", {})["output_format"] = args.output_format
    if generation:
        config.setdefault("getm", {})["generation"] = generation


def _apply_prompt_args(config: dict[str, Any], args: argparse.Namespace) -> None:
    prompt = dict((config.get("getm") or {}).get("prompt") or {})
    if args.max_surface_candidates is not None:
        prompt["max_surface_candidates"] = args.max_surface_candidates
    if hasattr(args, "candidate_context_chars"):
        prompt["candidate_context_chars"] = args.candidate_context_chars
    if args.candidate_render_mode is not None:
        prompt["candidate_render_mode"] = args.candidate_render_mode
    if args.enable_candidate_filtering is not None:
        prompt["enable_candidate_filtering"] = bool(args.enable_candidate_filtering)
    if args.max_candidates_per_type is not None:
        prompt["max_candidates_per_type"] = args.max_candidates_per_type
    if args.dedupe_surface_candidates is not None:
        prompt["dedupe_surface_candidates"] = bool(args.dedupe_surface_candidates)
    if args.drop_low_value_company_fragments is not None:
        prompt["drop_low_value_company_fragments"] = bool(args.drop_low_value_company_fragments)
    if args.prompt_token_budget is not None:
        prompt["prompt_token_budget"] = args.prompt_token_budget
    if args.baseline_mode is not None:
        prompt["baseline_mode"] = args.baseline_mode
    if args.fail_on_prompt_token_limit is not None:
        prompt["fail_on_prompt_token_limit"] = bool(args.fail_on_prompt_token_limit)
    if prompt:
        config.setdefault("getm", {})["prompt"] = prompt


def _parse_optional_float(value: str) -> float | None:
    lowered = value.strip().lower()
    if lowered in {"none", "null", ""}:
        return None
    try:
        return float(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"expected float or none, got {value!r}") from exc


def _parse_optional_int(value: str) -> int | None:
    lowered = value.strip().lower()
    if lowered in {"none", "null", ""}:
        return None
    try:
        return int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"expected int or none, got {value!r}") from exc


def _apply_telemetry_args(config: dict[str, Any], args: argparse.Namespace) -> None:
    resource = dict(config.get("resource_monitor") or {})
    if args.enable_telemetry:
        resource["enabled"] = True
    if args.telemetry_interval_sec is not None:
        resource["sample_interval_sec"] = args.telemetry_interval_sec
    if args.vram_soft_limit_gb is not None:
        resource["vram_soft_limit_gb"] = args.vram_soft_limit_gb
    if args.vram_target_min_gb is not None:
        resource["vram_target_min_gb"] = args.vram_target_min_gb
    if args.vram_target_max_gb is not None:
        resource["vram_target_max_gb"] = args.vram_target_max_gb
    if args.fail_on_vram_limit:
        resource["fail_on_vram_limit"] = True
    if resource:
        config["resource_monitor"] = resource


def _run_flag_allowed(config: dict[str, Any]) -> bool:
    run_cfg = config.get("run") or {}
    return bool(run_cfg.get("dry_run", True)) or bool(run_cfg.get("real_run", False))


def _run_manifest(
    *,
    config: dict[str, Any],
    dataset: str,
    split: str,
    command_infer: str,
    backend: str,
) -> dict[str, Any]:
    return {
        "run_id": f"getm_qwen_generate_{_created_slug()}",
        "method_name": "SAGE-DEE-v2-GETM-Qwen",
        "method_family": "SAGE-DEE-v2",
        "stage": "predict",
        "dataset_version": dataset,
        "split_version": split,
        "evaluator_version": EVALUATOR_VERSION,
        "prediction_format": PREDICTION_FORMAT,
        "training_view": "evaluator_gold/train",
        "gold_view": f"processed/views/evaluator_gold/{dataset}",
        "seed": _manifest_seed(config),
        "backend": backend,
        "dry_run": bool((config.get("run") or {}).get("dry_run", True)),
        "real_run": bool((config.get("run") or {}).get("real_run", False)),
        "profile": (config.get("run") or {}).get("profile"),
        "command_train": None,
        "command_infer": command_infer,
        "git_commit": _git_commit(),
        "created_at": _created_at(),
        "notes": "GETM Qwen generation wrapper run; dry-run/mock artifacts are not model performance evidence.",
    }


def _manifest_seed(config: dict[str, Any]) -> int | str:
    seed = ((config.get("getm") or {}).get("generation") or {}).get("seed")
    return int(seed) if seed is not None else "none"


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    merged = deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = deepcopy(value)
    return merged


def _write_json(path: Path, payload: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def _command(argv: Sequence[str] | None) -> str:
    if argv is None:
        return join([sys.executable, *sys.argv])
    return join([sys.executable, "scripts/v2/generate_getm_qwen.py", *argv])


def _created_at() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _created_slug() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _git_commit() -> str | None:
    completed = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    commit = completed.stdout.strip()
    return commit if completed.returncode == 0 and commit else None


if __name__ == "__main__":
    raise SystemExit(main())
