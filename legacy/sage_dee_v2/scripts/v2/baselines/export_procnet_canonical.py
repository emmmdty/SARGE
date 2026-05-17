from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from collections.abc import Sequence
from datetime import datetime, timezone
from pathlib import Path
from shlex import join
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "src"))

from sage_dee.v2.data_interface.jsonl import read_jsonl  # noqa: E402
from sage_dee.v2.data_interface.schema_registry import load_schema  # noqa: E402
from sage_dee.v2.pipeline.export_canonical import export_predictions  # noqa: E402
from sage_dee.v2.pipeline.run_manifest import EVALUATOR_VERSION, PREDICTION_FORMAT  # noqa: E402


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    if args.split == "test":
        raise SystemExit("Phase 8 ProcNet export rejects test split; test remains blocked")

    raw_path = args.run_dir / "procnet_raw" / args.dataset / f"{args.split}.canonical.raw.jsonl"
    canonical_path = args.run_dir / "predictions" / args.dataset / f"{args.split}.canonical.pred.jsonl"

    command = _procnet_command(args=args, raw_path=raw_path)
    if args.raw_input is None:
        _run_procnet_export(command, cwd=REPO_ROOT)
    else:
        raw_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(args.raw_input, raw_path)

    schema = load_schema(args.dataset, data_root=args.data_root)
    raw_rows = read_jsonl(raw_path)
    export_predictions(raw_rows, canonical_path, schema=schema)
    canonical_rows = read_jsonl(canonical_path)
    summary = _summary(args=args, raw_path=raw_path, canonical_path=canonical_path, canonical_rows=canonical_rows)
    manifest = _run_manifest(args=args, command=command, canonical_path=canonical_path, raw_path=raw_path, summary=summary)

    args.run_dir.mkdir(parents=True, exist_ok=True)
    (args.run_dir / "run_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (args.run_dir / "phase8_procnet_export_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export ProcNet predictions through the SAGE canonical contract.")
    parser.add_argument("--dataset", required=True)
    parser.add_argument("--split", default="dev", choices=("dev", "test"))
    parser.add_argument("--seed", required=True, type=int)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--run-dir", required=True, type=Path)
    parser.add_argument("--procnet-workdir", required=True, type=Path)
    parser.add_argument("--procnet-export-script", required=True, type=Path)
    parser.add_argument("--checkpoint", required=True, type=Path)
    parser.add_argument("--data-root", default=Path("data"), type=Path)
    parser.add_argument("--python", default=sys.executable)
    parser.add_argument("--device", default="cuda")
    parser.add_argument("--model-name", default="hfl/chinese-roberta-wwm-ext")
    parser.add_argument("--node-size", default=512, type=int)
    parser.add_argument("--proxy-slot-num", default=16, type=int)
    parser.add_argument("--max-len", default=510, type=int)
    parser.add_argument("--read-pseudo", default="false", choices=("true", "false"))
    parser.add_argument("--raw-input", type=Path, help="Existing ProcNet raw JSONL for local conversion checks.")
    parser.add_argument("--command-train")
    parser.add_argument("--notes")
    return parser.parse_args(argv)


def _procnet_command(*, args: argparse.Namespace, raw_path: Path) -> list[str]:
    return [
        args.python,
        str(args.procnet_export_script),
        "--workdir",
        str(args.procnet_workdir),
        "--checkpoint",
        str(args.checkpoint),
        "--output",
        str(raw_path),
        "--dataset",
        args.dataset,
        "--split",
        args.split,
        "--read-pseudo",
        args.read_pseudo,
        "--seed",
        str(args.seed),
        "--device",
        args.device,
        "--model-name",
        args.model_name,
        "--node-size",
        str(args.node_size),
        "--proxy-slot-num",
        str(args.proxy_slot_num),
        "--max-len",
        str(args.max_len),
    ]


def _run_procnet_export(command: list[str], *, cwd: Path) -> None:
    completed = subprocess.run(command, cwd=cwd, check=False, text=True)
    if completed.returncode != 0:
        raise SystemExit(completed.returncode)


def _summary(
    *,
    args: argparse.Namespace,
    raw_path: Path,
    canonical_path: Path,
    canonical_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "baseline": "ProcNet",
        "dataset": args.dataset,
        "split": args.split,
        "seed": args.seed,
        "run_id": args.run_id,
        "checkpoint": str(args.checkpoint),
        "run_dir": str(args.run_dir),
        "raw_predictions_path": str(raw_path),
        "canonical_predictions_path": str(canonical_path),
        "canonical_rows": len(canonical_rows),
        "canonical_event_count": sum(len(row.get("events") or []) for row in canonical_rows),
        "prediction_format": PREDICTION_FORMAT,
        "evaluator_version": EVALUATOR_VERSION,
        "test_used": False,
        "status_before_evaluator": "canonical-export-complete",
    }


def _run_manifest(
    *,
    args: argparse.Namespace,
    command: list[str],
    canonical_path: Path,
    raw_path: Path,
    summary: dict[str, Any],
) -> dict[str, Any]:
    return {
        "run_id": args.run_id,
        "method_name": "ProcNet",
        "method_family": "traditional_dee",
        "stage": "phase8_traditional_baseline_alignment",
        "dataset_version": args.dataset,
        "split_version": args.split,
        "evaluator_version": EVALUATOR_VERSION,
        "prediction_format": PREDICTION_FORMAT,
        "training_view": "procnet_clean_train",
        "gold_view": f"processed/views/evaluator_gold/{args.dataset}",
        "seed": args.seed,
        "backend": "procnet",
        "command_train": args.command_train,
        "command_infer": join(command),
        "git_commit": _git_commit(),
        "created_at": _created_at(),
        "notes": args.notes or "Phase 8 traditional baseline alignment; dev split only; test remains blocked.",
        "native_method_name": "ProcNet",
        "native_evaluator_name": "ProcNet native DocEE_metric",
        "native_metric_names": ["micro_precision", "micro_recall", "micro_f1", "single_event_f1", "multi_event_f1"],
        "native_output_format": "ProcNet event slot predictions exported from checkpoint",
        "procnet_checkpoint": str(args.checkpoint),
        "procnet_workdir": str(args.procnet_workdir),
        "procnet_export_script": str(args.procnet_export_script),
        "raw_predictions_path": str(raw_path),
        "canonical_predictions_path": str(canonical_path),
        "canonical_rows": summary["canonical_rows"],
        "test_used": False,
    }


def _created_at() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


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
