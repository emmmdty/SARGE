from __future__ import annotations

import argparse
import csv
import json
import shutil
import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))

from sage_dee.io_utils import read_yaml  # noqa: E402
from sage_dee.v2.data_interface.jsonl import read_jsonl, write_jsonl  # noqa: E402
from sage_dee.v2.getm.scope_guard import validate_getm_prediction_scope  # noqa: E402
from sage_dee.v2.pipeline.evaluator_handoff import build_evaluator_handoff, run_evaluator_handoff  # noqa: E402
from sage_dee.v2.pipeline.export_canonical import validate_minimal_canonical_prediction  # noqa: E402

FROZEN_GENERATE_CONFIG = Path("configs/v2/sage_v2_getm_format_stable.yaml")
FROZEN_GENERATE_PROFILE = "getm_format_stable_dev20_f1"
SUMMARY_FIELDS = (
    "run_id",
    "run_dir",
    "canonical_rows",
    "parse_error",
    "schema_violation_rows",
    "schema_violation",
    "unknown_role",
    "unknown_event_type",
    "forbidden_key_violations",
    "evaluator_attempted",
    "evaluator_returncode",
    "evaluator_validation_ok",
)
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
    dataset = args.dataset or str((config.get("data") or {}).get("dataset") or "DuEE-Fin-dev500")
    data_root = args.data_root or str((config.get("data") or {}).get("data_root") or "data")
    if args.split == "test":
        print("Phase 5 SFT smoke rejects test split", file=sys.stderr)
        return 2
    if args.split != "dev":
        print(f"Phase 5 SFT smoke only permits dev split, got {args.split!r}", file=sys.stderr)
        return 2
    if args.train_limit > 20:
        print("Phase 5 SFT smoke train_limit must stay <= 20", file=sys.stderr)
        return 2
    if args.dev20_limit != 20:
        print("Phase 5 SFT smoke dev20_limit must be exactly 20", file=sys.stderr)
        return 2
    if args.limit50 != 50:
        print("Phase 5 SFT smoke limit50 must be exactly 50", file=sys.stderr)
        return 2
    if args.limit50 == 50 and not args.allow_limit50 and not args.dry_run:
        print("Phase 5 limit=50 requires --allow-limit50", file=sys.stderr)
        return 2

    args.out_root.mkdir(parents=True, exist_ok=True)
    train_dir = args.out_root / "train"
    dev20_dir = args.out_root / "dev20"
    limit50_dir = args.out_root / "limit50"

    train_result = _run_train(args, dataset=dataset, data_root=data_root, out_dir=train_dir)
    adapter_dir = str(train_dir / "artifacts" / "model" / "adapter")
    if args.dry_run:
        adapter_dir = "dry-run-no-adapter"

    dev20_result = _run_generate(
        args,
        dataset=dataset,
        data_root=data_root,
        limit=args.dev20_limit,
        adapter_dir=adapter_dir,
        out_dir=dev20_dir,
        allow_limit50=False,
    )
    limit50_result = _run_generate(
        args,
        dataset=dataset,
        data_root=data_root,
        limit=args.limit50,
        adapter_dir=adapter_dir,
        out_dir=limit50_dir,
        allow_limit50=True,
    )

    subset_root = _write_subset_benchmark(
        out_root=args.out_root,
        source_data_root=Path(data_root),
        dataset=dataset,
        split=args.split,
        doc_ids=_prompt_doc_ids(limit50_dir / f"prompts.{args.split}.jsonl"),
    )
    evaluator = _run_evaluator(args, run_dir=limit50_dir, dataset=dataset, split=args.split, subset_root=subset_root)
    limit50_result.update(_summarize_evaluator(evaluator, dataset=dataset, split=args.split))

    summary = {
        "scope": {
            "dataset": dataset,
            "split": args.split,
            "train_limit": args.train_limit,
            "dev20_limit": args.dev20_limit,
            "limit50": args.limit50,
            "test_used": False,
            "full_dev_used": False,
            "full_train_used": False,
        },
        "gate": {
            "sft_smoke_not_performance": True,
            "adapter_trainable": train_result["returncode"] == 0,
            "no_oom": not _has_oom(train_dir) and not _has_oom(dev20_dir) and not _has_oom(limit50_dir),
            "label_mask_correct": bool(train_result["sft_label_mask"].get("all_prompt_labels_masked"))
            and bool(train_result["sft_label_mask"].get("all_examples_have_answer_labels")),
            "target_schema_valid": bool(train_result["sft_target_audit"].get("target_schema_valid")),
            "limit50_evaluator_readable": limit50_result.get("evaluator_validation_ok") is True
            or not bool(limit50_result.get("evaluator_attempted")),
            "test_still_blocked": True,
        },
        "train": train_result,
        "dev20": dev20_result,
        "limit50": limit50_result,
        "subset_benchmark_root": str(subset_root),
    }
    _write_json(args.out_root / "phase5_summary.json", summary)
    _write_summary_csv(args.out_root / "phase5_summary.csv", [dev20_result, limit50_result])
    print(f"out_root={args.out_root}")
    print(f"summary_json={args.out_root / 'phase5_summary.json'}")
    return 0


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run guarded SAGE v2 Phase 5 small SFT smoke.")
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--dataset")
    parser.add_argument("--data-root")
    parser.add_argument("--split", default="dev")
    parser.add_argument("--train-limit", type=int, default=8)
    parser.add_argument("--dev20-limit", type=int, default=20)
    parser.add_argument("--limit50", type=int, default=50)
    parser.add_argument("--allow-limit50", action="store_true")
    parser.add_argument("--dry-run", dest="dry_run", action="store_true", default=None)
    parser.add_argument("--real-run", action="store_true")
    parser.add_argument("--enable-telemetry", action="store_true")
    parser.add_argument("--telemetry-interval-sec", type=float)
    parser.add_argument("--skip-evaluator", action="store_true")
    parser.add_argument("--evaluator-root", type=Path, default=Path("/home/TJK/DEE/dee-eval"))
    parser.add_argument("--evaluator-out-root", type=Path)
    parser.add_argument("--out-root", type=Path, required=True)
    return parser.parse_args(argv)


def _run_train(args: argparse.Namespace, *, dataset: str, data_root: str, out_dir: Path) -> dict[str, Any]:
    cmd = [
        sys.executable,
        str(REPO_ROOT / "scripts/v2/train_getm_qwen.py"),
        "--config",
        str(args.config),
        "--profile",
        "phase5_sft_smoke_4090",
        "--dataset",
        dataset,
        "--split",
        "train",
        "--data-root",
        data_root,
        "--limit",
        str(args.train_limit),
        "--max-train-steps",
        "2",
        "--output-format",
        "minimal_text",
        "--out-dir",
        str(out_dir),
    ]
    cmd.append("--real-run" if args.real_run else "--dry-run")
    if args.enable_telemetry:
        cmd.append("--enable-telemetry")
    if args.telemetry_interval_sec is not None:
        cmd.extend(["--telemetry-interval-sec", str(args.telemetry_interval_sec)])
    completed = _run_command(
        cmd,
        out_dir / "phase5_train_command.json",
        out_dir / "phase5_train.stdout.log",
        out_dir / "phase5_train.stderr.log",
    )
    if completed.returncode != 0:
        raise RuntimeError(f"Phase 5 train failed with exit code {completed.returncode}: {completed.stderr}")
    manifest = _read_json(out_dir / "training_manifest.json")
    return {
        "returncode": completed.returncode,
        "run_dir": str(out_dir),
        "adapter_dir": manifest.get("adapter_dir"),
        "train_rows": manifest.get("train_rows"),
        "train_examples": manifest.get("train_examples"),
        "train_runtime": manifest.get("train_runtime"),
        "train_loss": manifest.get("train_loss"),
        "sft_label_mask": manifest.get("sft_label_mask") or {},
        "sft_target_audit": manifest.get("sft_target_audit") or {},
        "telemetry": _telemetry_summary(out_dir),
        "oom": _has_oom(out_dir),
    }


def _run_generate(
    args: argparse.Namespace,
    *,
    dataset: str,
    data_root: str,
    limit: int,
    adapter_dir: str,
    out_dir: Path,
    allow_limit50: bool,
) -> dict[str, Any]:
    frozen_config = REPO_ROOT / FROZEN_GENERATE_CONFIG
    frozen = read_yaml(frozen_config)
    validate_getm_prediction_scope(
        config_path=frozen_config,
        config=frozen,
        profile=FROZEN_GENERATE_PROFILE,
        split=args.split,
        limit=limit,
        allow_limit50=allow_limit50,
    )
    cmd = [
        sys.executable,
        str(REPO_ROOT / "scripts/v2/generate_getm_qwen.py"),
        "--config",
        str(frozen_config),
        "--profile",
        FROZEN_GENERATE_PROFILE,
        "--dataset",
        dataset,
        "--split",
        args.split,
        "--data-root",
        data_root,
        "--limit",
        str(limit),
        "--k",
        "1",
        "--adapter-path",
        adapter_dir,
        "--seed",
        "42",
        "--deterministic",
        "--deterministic-warn-only",
        "--record-resolved-generation-config",
        "--out-dir",
        str(out_dir),
    ]
    if allow_limit50:
        cmd.append("--allow-limit50")
    cmd.append("--real-run" if args.real_run else "--dry-run")
    if args.enable_telemetry:
        cmd.append("--enable-telemetry")
    if args.telemetry_interval_sec is not None:
        cmd.extend(["--telemetry-interval-sec", str(args.telemetry_interval_sec)])
    completed = _run_command(
        cmd,
        out_dir / "phase5_generate_command.json",
        out_dir / "phase5_generate.stdout.log",
        out_dir / "phase5_generate.stderr.log",
    )
    if completed.returncode != 0:
        raise RuntimeError(
            f"Phase 5 generate limit={limit} failed with exit code {completed.returncode}: {completed.stderr}"
        )
    return _summarize_generation(run_dir=out_dir, dataset=dataset, split=args.split, run_id=f"limit{limit}")


def _run_command(
    cmd: list[str],
    command_path: Path,
    stdout_path: Path,
    stderr_path: Path,
) -> subprocess.CompletedProcess[str]:
    command_path.parent.mkdir(parents=True, exist_ok=True)
    completed = subprocess.run(cmd, cwd=REPO_ROOT, check=False, capture_output=True, text=True)
    _write_json(command_path, {"cmd": cmd, "returncode": completed.returncode})
    stdout_path.write_text(completed.stdout, encoding="utf-8")
    stderr_path.write_text(completed.stderr, encoding="utf-8")
    return completed


def _summarize_generation(*, run_dir: Path, dataset: str, split: str, run_id: str) -> dict[str, Any]:
    diagnostics = _read_json(run_dir / f"parse_diagnostics.{split}.json")
    parsed_rows = read_jsonl(run_dir / f"parsed_candidates.{split}.jsonl")
    canonical_path = run_dir / "predictions" / dataset / f"{split}.canonical.pred.jsonl"
    canonical_rows = read_jsonl(canonical_path)
    diagnostic_counts = diagnostics.get("diagnostic_counts") or {}
    parse_status_counts = diagnostics.get("parse_status_counts") or {}
    validation = _canonical_validation(canonical_rows)
    return {
        "run_id": run_id,
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


def _run_evaluator(
    args: argparse.Namespace,
    *,
    run_dir: Path,
    dataset: str,
    split: str,
    subset_root: Path,
) -> dict[str, Any]:
    if args.skip_evaluator:
        return {"attempted": False, "returncode": None, "artifact_root": None}
    evaluator_out_root = args.evaluator_out_root or args.out_root / "evaluator_artifacts" / "limit50"
    handoff = build_evaluator_handoff(
        run_root=run_dir,
        dataset=dataset,
        split=split,
        data_repo_root=args.evaluator_root,
        out_dir=evaluator_out_root,
        benchmark_root=subset_root,
        strict=True,
    )
    result = run_evaluator_handoff(handoff)
    _write_json(run_dir / "phase5_evaluator_handoff.json", {"handoff": handoff.to_dict(), "result": result})
    return {
        "attempted": result["attempted"],
        "returncode": result["returncode"],
        "artifact_out_dir": str(evaluator_out_root),
        "artifact_root": _extract_artifact_root(result.get("stdout")),
        "stdout": result.get("stdout"),
        "stderr": result.get("stderr"),
    }


def _summarize_evaluator(evaluator: dict[str, Any], *, dataset: str, split: str) -> dict[str, Any]:
    validation_ok = None
    artifact_root = evaluator.get("artifact_root")
    if artifact_root:
        validation_path = Path(artifact_root) / "analysis" / dataset / split / "validation_report.json"
        if validation_path.is_file():
            validation_ok = _read_json(validation_path).get("ok")
    return {
        "evaluator_attempted": bool(evaluator.get("attempted")),
        "evaluator_returncode": evaluator.get("returncode"),
        "evaluator_artifact_root": artifact_root,
        "evaluator_validation_ok": validation_ok,
    }


def _write_subset_benchmark(
    *,
    out_root: Path,
    source_data_root: Path,
    dataset: str,
    split: str,
    doc_ids: list[str],
) -> Path:
    target_root = out_root / "subset_benchmark"
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
    _write_json(target_root / "doc_subset.json", {"dataset": dataset, "split": split, "doc_ids": doc_ids})
    return target_root


def _prompt_doc_ids(path: Path) -> list[str]:
    return [str(row.get("doc_id") or "") for row in read_jsonl(path)]


def _canonical_validation(canonical_rows: list[dict[str, Any]]) -> dict[str, Any]:
    schema_errors = 0
    forbidden_violations = 0
    for row in canonical_rows:
        try:
            validate_minimal_canonical_prediction(row)
        except ValueError:
            schema_errors += 1
        forbidden_violations += len(_forbidden_key_paths(row))
    return {
        "canonical_schema_errors": schema_errors,
        "forbidden_key_violations": forbidden_violations,
    }


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


def _telemetry_summary(run_dir: Path) -> dict[str, Any]:
    manifest_path = run_dir / "telemetry" / "telemetry_manifest.json"
    timing_path = run_dir / "telemetry" / "timing_summary.json"
    gpu_path = run_dir / "telemetry" / "gpu_memory_summary.json"
    return {
        "telemetry_manifest": _read_json_if_exists(manifest_path),
        "timing_summary": _read_json_if_exists(timing_path),
        "gpu_memory_summary": _read_json_if_exists(gpu_path),
    }


def _has_oom(run_dir: Path) -> bool:
    texts = []
    for path in run_dir.glob("*.stderr.log"):
        texts.append(path.read_text(encoding="utf-8", errors="ignore"))
    serialized = "\n".join(texts).lower()
    return "outofmemory" in serialized or "out of memory" in serialized or "cuda oom" in serialized


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


def _read_json_if_exists(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    return _read_json(path)


def _read_json(path: str | Path) -> dict[str, Any]:
    with Path(path).open(encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object: {path}")
    return payload


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_summary_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=SUMMARY_FIELDS, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({key: _csv_value(row.get(key)) for key in SUMMARY_FIELDS})


def _csv_value(value: Any) -> Any:
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    return value


if __name__ == "__main__":
    raise SystemExit(main())
