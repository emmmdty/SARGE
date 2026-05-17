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
from sage_dee.v2.csg.surface_memory import build_surface_memory  # noqa: E402
from sage_dee.v2.data_interface.dataset_loader import load_documents  # noqa: E402
from sage_dee.v2.data_interface.jsonl import write_jsonl  # noqa: E402
from sage_dee.v2.data_interface.schema_registry import load_schema  # noqa: E402
from sage_dee.v2.getm.qwen_backend import train_sft  # noqa: E402
from sage_dee.v2.getm.sft_dataset import audit_sft_targets, build_getm_sft_sample  # noqa: E402


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    config = _resolve_config(args)
    if not _run_flag_allowed(config):
        print("real Qwen GETM training requires explicit --real-run", file=sys.stderr)
        return 2

    out_dir = args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    data_cfg = config.get("data") or {}
    dataset = str(args.dataset or data_cfg.get("dataset") or "DuEE-Fin-dev500")
    split = str(args.split or data_cfg.get("train_split") or "train")
    data_root = str(args.data_root or data_cfg.get("data_root") or "data")
    limit = args.limit if args.limit is not None else data_cfg.get("max_train_docs")

    schema = load_schema(dataset, data_root=data_root)
    documents = load_documents(dataset, split, data_root=data_root, mode="train", limit=limit)
    rows = []
    for document in documents:
        memory = build_surface_memory(document.input)
        rows.append(
            build_getm_sft_sample(
                document,
                schema,
                surface_candidates=memory.candidates,
                slot_plan=None,
                output_format=_output_format(config),
                prompt_options=_prompt_options(config),
            )
        )

    sft_path = write_jsonl(out_dir / "intermediate" / f"getm_sft.{split}.jsonl", rows)
    target_audit = audit_sft_targets(rows, schema)
    backend_manifest = train_sft(config, rows, out_dir)
    _merge_training_manifest(
        out_dir / "training_manifest.json",
        {"sft_target_audit": target_audit},
    )
    config_path = out_dir / "config.resolved.yaml"
    write_yaml(config_path, config)
    run_manifest_path = _write_json(
        out_dir / "run_manifest.json",
        _run_manifest(
            config=config,
            dataset=dataset,
            split=split,
            command_train=_command(argv),
            backend="qwen_getm",
        ),
    )

    print(f"out_dir={out_dir}")
    print(f"sft_data={sft_path}")
    print(f"config_resolved={config_path}")
    print(f"run_manifest={run_manifest_path}")
    print(f"training_manifest={backend_manifest['training_manifest_path']}")
    print(f"backend_manifest={backend_manifest['backend_manifest_path']}")
    print("summary=" + json.dumps(_summary(config, rows, target_audit), ensure_ascii=False, sort_keys=True))
    return 0


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train or dry-run SAGE-DEE v2 GETM Qwen SFT.")
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--profile")
    parser.add_argument("--dry-run", dest="dry_run", action="store_true", default=None)
    parser.add_argument("--no-dry-run", dest="dry_run", action="store_false")
    parser.add_argument("--real-run", action="store_true")
    parser.add_argument("--dataset")
    parser.add_argument("--split")
    parser.add_argument("--data-root")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--enable-telemetry", action="store_true")
    parser.add_argument("--telemetry-interval-sec", type=float)
    parser.add_argument("--vram-soft-limit-gb", type=float)
    parser.add_argument("--vram-target-min-gb", type=float)
    parser.add_argument("--vram-target-max-gb", type=float)
    parser.add_argument("--fail-on-vram-limit", action="store_true")
    parser.add_argument("--max-train-steps", type=int)
    parser.add_argument("--output-format", choices=("minimal_text", "argument_object"))
    parser.add_argument("--out-dir", type=Path, default=Path("runs/v2_getm_qwen_train"))
    return parser.parse_args(argv)


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
    if args.output_format is not None:
        config.setdefault("getm", {})["output_format"] = args.output_format
    return config


def _output_format(config: dict[str, Any]) -> str:
    return str((config.get("getm") or {}).get("output_format") or "minimal_text")


def _prompt_options(config: dict[str, Any]) -> dict[str, Any]:
    return dict((config.get("getm") or {}).get("prompt") or {})


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
    budget = dict(config.get("training_budget") or {})
    if args.max_train_steps is not None:
        budget["max_train_steps"] = args.max_train_steps
    if budget:
        config["training_budget"] = budget


def _run_flag_allowed(config: dict[str, Any]) -> bool:
    run_cfg = config.get("run") or {}
    return bool(run_cfg.get("dry_run", True)) or bool(run_cfg.get("real_run", False))


def _summary(config: dict[str, Any], rows: list[dict[str, Any]], target_audit: dict[str, Any]) -> dict[str, Any]:
    run_cfg = config.get("run") or {}
    return {
        "dry_run": bool(run_cfg.get("dry_run", True)),
        "real_run": bool(run_cfg.get("real_run", False)),
        "profile": run_cfg.get("profile"),
        "train_rows": len(rows),
        "sft_target_audit": target_audit,
    }


def _run_manifest(
    *,
    config: dict[str, Any],
    dataset: str,
    split: str,
    command_train: str,
    backend: str,
) -> dict[str, Any]:
    return {
        "run_id": f"getm_qwen_train_{_created_slug()}",
        "method_name": "SAGE-DEE-v2-GETM-Qwen",
        "method_family": "SAGE-DEE-v2",
        "stage": "train",
        "dataset_version": dataset,
        "split_version": split,
        "backend": backend,
        "dry_run": bool((config.get("run") or {}).get("dry_run", True)),
        "real_run": bool((config.get("run") or {}).get("real_run", False)),
        "profile": (config.get("run") or {}).get("profile"),
        "prediction_format": "canonical-jsonl",
        "command_train": command_train,
        "command_infer": None,
        "git_commit": _git_commit(),
        "created_at": _created_at(),
        "notes": "GETM Qwen training wrapper run; dry-run artifacts are not model performance evidence.",
    }


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


def _merge_training_manifest(path: Path, extra: dict[str, Any]) -> None:
    if not path.is_file():
        return
    with path.open(encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        return
    payload.update(extra)
    _write_json(path, payload)
    backend_path = path.parent / "artifacts" / "backend_manifest.json"
    if backend_path.is_file():
        with backend_path.open(encoding="utf-8") as handle:
            backend_payload = json.load(handle)
        if isinstance(backend_payload, dict):
            backend_payload.update(extra)
            _write_json(backend_path, backend_payload)


def _command(argv: Sequence[str] | None) -> str:
    if argv is None:
        return join([sys.executable, *sys.argv])
    return join([sys.executable, "scripts/v2/train_getm_qwen.py", *argv])


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
