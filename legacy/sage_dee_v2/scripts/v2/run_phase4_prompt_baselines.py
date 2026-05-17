from __future__ import annotations

import argparse
import csv
import json
import shutil
import subprocess
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))

from sage_dee.io_utils import read_yaml  # noqa: E402
from sage_dee.v2.data_interface.jsonl import read_jsonl, write_jsonl  # noqa: E402
from sage_dee.v2.getm.scope_guard import validate_getm_prediction_scope  # noqa: E402
from sage_dee.v2.pipeline.evaluator_handoff import build_evaluator_handoff, run_evaluator_handoff  # noqa: E402
from sage_dee.v2.pipeline.export_canonical import validate_minimal_canonical_prediction  # noqa: E402

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


@dataclass(frozen=True)
class BaselineSpec:
    baseline_id: str
    profile: str
    label: str
    baseline_mode: str


BASELINES = (
    BaselineSpec("P1", "phase4_p1_direct_json", "direct prompt-to-JSON", "direct_json"),
    BaselineSpec("P2", "phase4_p2_schema_only", "schema-only prompt", "schema_only"),
    BaselineSpec("P3", "phase4_p3_role_safe", "role-safe prompt", "role_safe"),
    BaselineSpec("P4", "phase4_p4_role_safe_surface_memory", "role-safe + surface memory prompt", "role_safe_surface_memory"),
)

SUMMARY_FIELDS = (
    "baseline_id",
    "profile",
    "baseline_mode",
    "run_dir",
    "parse_status_counts",
    "parse_error",
    "schema_violation_rows",
    "schema_violation",
    "unknown_role",
    "unknown_event_type",
    "canonical_rows",
    "canonical_event_count",
    "canonical_schema_errors",
    "forbidden_key_violations",
    "evaluator_attempted",
    "evaluator_returncode",
    "evaluator_artifact_root",
    "evaluator_validation_ok",
    "event_table_micro_f1",
    "role_level_f1",
    "exact_record_f1",
)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    config = read_yaml(args.config)
    try:
        validate_getm_prediction_scope(
            config_path=args.config,
            config={**config, "run": {"profile": BASELINES[0].profile}},
            profile=BASELINES[0].profile,
            split=args.split,
            limit=args.limit,
            allow_limit50=bool(args.allow_limit50),
        )
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    args.out_root.mkdir(parents=True, exist_ok=True)
    summaries: list[dict[str, Any]] = []
    doc_subset: list[str] | None = None
    subset_benchmark_root: Path | None = None

    for baseline in BASELINES:
        run_dir = args.out_root / baseline.baseline_id
        run_dir.mkdir(parents=True, exist_ok=True)
        _run_baseline(args, baseline=baseline, run_dir=run_dir)
        group_doc_subset = _prompt_doc_ids(run_dir / f"prompts.{args.split}.jsonl")
        if doc_subset is None:
            doc_subset = group_doc_subset
            subset_benchmark_root = _write_subset_benchmark(
                out_root=args.out_root,
                source_data_root=Path(args.data_root or _config_data_root(config)),
                dataset=args.dataset,
                split=args.split,
                doc_ids=doc_subset,
            )
            _write_json(args.out_root / "doc_subset.json", {"dataset": args.dataset, "split": args.split, "doc_ids": doc_subset})
        elif group_doc_subset != doc_subset:
            raise RuntimeError(f"{baseline.baseline_id} used a different doc subset")

        evaluator = _run_evaluator(args, run_dir=run_dir, baseline=baseline, subset_benchmark_root=subset_benchmark_root)
        summary = _summarize_baseline(
            baseline=baseline,
            run_dir=run_dir,
            dataset=args.dataset,
            split=args.split,
            evaluator=evaluator,
        )
        summaries.append(summary)
        _write_json(run_dir / "phase4_summary.json", summary)

    _write_json(args.out_root / "summary.json", {"baselines": summaries})
    _write_summary_csv(args.out_root / "summary.csv", summaries)
    print(f"out_root={args.out_root}")
    print(f"summary_json={args.out_root / 'summary.json'}")
    print(f"summary_csv={args.out_root / 'summary.csv'}")
    return 0


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run guarded SAGE v2 Phase 4 P1-P4 prompt baselines.")
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--dataset", default="DuEE-Fin-dev500")
    parser.add_argument("--data-root")
    parser.add_argument("--split", default="dev")
    parser.add_argument("--limit", type=int, default=50)
    parser.add_argument("--k", type=int, default=1)
    parser.add_argument("--allow-limit50", action="store_true")
    parser.add_argument("--dry-run", dest="dry_run", action="store_true", default=None)
    parser.add_argument("--real-run", action="store_true")
    parser.add_argument("--adapter-path")
    parser.add_argument("--enable-telemetry", action="store_true")
    parser.add_argument("--telemetry-interval-sec", type=float)
    parser.add_argument("--vram-soft-limit-gb", type=float)
    parser.add_argument("--vram-target-min-gb", type=float)
    parser.add_argument("--vram-target-max-gb", type=float)
    parser.add_argument("--fail-on-vram-limit", action="store_true")
    parser.add_argument("--skip-evaluator", action="store_true")
    parser.add_argument("--evaluator-root", type=Path, default=Path("/home/TJK/DEE/dee-eval"))
    parser.add_argument("--evaluator-out-root", type=Path)
    parser.add_argument("--out-root", type=Path, required=True)
    args = parser.parse_args(argv)
    if args.split != "dev":
        parser.error("Phase 4 prompt baselines only permit --split dev; test is forbidden")
    if args.limit is None:
        parser.error("Phase 4 prompt baselines require an explicit --limit")
    if args.limit > 20 and args.limit != 50:
        parser.error("Phase 4 prompt baselines permit limit <= 20 or exactly limit=50")
    if args.limit == 50 and not args.allow_limit50 and not args.dry_run:
        parser.error("Phase 4 limit=50 requires --allow-limit50")
    if args.k != 1:
        parser.error("Phase 4 prompt baselines only permit --k 1")
    return args


def _run_baseline(args: argparse.Namespace, *, baseline: BaselineSpec, run_dir: Path) -> None:
    cmd = [
        sys.executable,
        str(REPO_ROOT / "scripts/v2/generate_getm_qwen.py"),
        "--config",
        str(args.config),
        "--profile",
        baseline.profile,
        "--dataset",
        args.dataset,
        "--split",
        args.split,
        "--limit",
        str(args.limit),
        "--k",
        str(args.k),
        "--max-new-tokens",
        "1024",
        "--no-do-sample",
        "--temperature",
        "none",
        "--top-p",
        "1.0",
        "--seed",
        "42",
        "--deterministic",
        "--deterministic-warn-only",
        "--record-resolved-generation-config",
        "--baseline-mode",
        baseline.baseline_mode,
        "--output-format",
        "minimal_text",
        "--prompt-token-budget",
        "4096",
        "--no-fail-on-prompt-token-limit",
        "--use-response-prefix",
        "--response-prefix",
        '{"events":',
        "--enable-balanced-json-stopping",
        "--stop-after-balanced-events-json",
        "--out-dir",
        str(run_dir),
    ]
    if args.limit == 50:
        cmd.append("--allow-limit50")
    if baseline.baseline_mode == "role_safe_surface_memory":
        cmd.extend(
            [
                "--max-surface-candidates",
                "10",
                "--candidate-render-mode",
                "compact",
                "--candidate-context-chars",
                "0",
                "--enable-candidate-filtering",
                "--max-candidates-per-type",
                "6",
                "--dedupe-surface-candidates",
                "--drop-low-value-company-fragments",
            ]
        )
    else:
        cmd.extend(
            [
                "--max-surface-candidates",
                "0",
                "--candidate-render-mode",
                "compact",
                "--candidate-context-chars",
                "0",
                "--no-enable-candidate-filtering",
                "--no-dedupe-surface-candidates",
                "--no-drop-low-value-company-fragments",
            ]
        )
    cmd.append("--real-run" if args.real_run else "--dry-run")
    if args.data_root:
        cmd.extend(["--data-root", args.data_root])
    if args.adapter_path:
        cmd.extend(["--adapter-path", args.adapter_path])
    if args.enable_telemetry:
        cmd.append("--enable-telemetry")
    if args.telemetry_interval_sec is not None:
        cmd.extend(["--telemetry-interval-sec", str(args.telemetry_interval_sec)])
    if args.vram_soft_limit_gb is not None:
        cmd.extend(["--vram-soft-limit-gb", str(args.vram_soft_limit_gb)])
    if args.vram_target_min_gb is not None:
        cmd.extend(["--vram-target-min-gb", str(args.vram_target_min_gb)])
    if args.vram_target_max_gb is not None:
        cmd.extend(["--vram-target-max-gb", str(args.vram_target_max_gb)])
    if args.fail_on_vram_limit:
        cmd.append("--fail-on-vram-limit")

    completed = subprocess.run(cmd, cwd=REPO_ROOT, check=False, capture_output=True, text=True)
    _write_json(run_dir / "phase4_command.json", {"cmd": cmd, "returncode": completed.returncode})
    (run_dir / "phase4.stdout.log").write_text(completed.stdout, encoding="utf-8")
    (run_dir / "phase4.stderr.log").write_text(completed.stderr, encoding="utf-8")
    if completed.returncode != 0:
        raise RuntimeError(f"{baseline.baseline_id} failed with exit code {completed.returncode}: {completed.stderr}")


def _run_evaluator(
    args: argparse.Namespace,
    *,
    run_dir: Path,
    baseline: BaselineSpec,
    subset_benchmark_root: Path | None,
) -> dict[str, Any]:
    if args.skip_evaluator:
        return {"attempted": False, "returncode": None, "artifact_out_dir": None, "artifact_root": None}
    if subset_benchmark_root is None:
        raise RuntimeError("subset benchmark root was not built before evaluator handoff")
    evaluator_out_root = args.evaluator_out_root or args.out_root / "evaluator_artifacts" / baseline.baseline_id
    handoff = build_evaluator_handoff(
        run_root=run_dir,
        dataset=args.dataset,
        split=args.split,
        data_repo_root=args.evaluator_root,
        out_dir=evaluator_out_root,
        benchmark_root=subset_benchmark_root,
        strict=True,
    )
    result = run_evaluator_handoff(handoff)
    _write_json(run_dir / "phase4_evaluator_handoff.json", {"handoff": handoff.to_dict(), "result": result})
    return {
        "attempted": result["attempted"],
        "returncode": result["returncode"],
        "artifact_out_dir": str(evaluator_out_root),
        "artifact_root": _extract_artifact_root(result.get("stdout")),
        "stdout": result.get("stdout"),
        "stderr": result.get("stderr"),
    }


def _summarize_baseline(
    *,
    baseline: BaselineSpec,
    run_dir: Path,
    dataset: str,
    split: str,
    evaluator: dict[str, Any],
) -> dict[str, Any]:
    diagnostics = _read_json(run_dir / f"parse_diagnostics.{split}.json")
    parsed_rows = read_jsonl(run_dir / f"parsed_candidates.{split}.jsonl")
    canonical_path = run_dir / "predictions" / dataset / f"{split}.canonical.pred.jsonl"
    canonical_rows = read_jsonl(canonical_path)
    validation = _canonical_validation(canonical_rows)
    diagnostic_counts = diagnostics.get("diagnostic_counts") or {}
    parse_status_counts = diagnostics.get("parse_status_counts") or {}
    evaluator_metrics = _read_evaluator_metrics(evaluator.get("artifact_root"), dataset=dataset, split=split)
    summary = {
        "baseline_id": baseline.baseline_id,
        "profile": baseline.profile,
        "label": baseline.label,
        "baseline_mode": baseline.baseline_mode,
        "run_dir": str(run_dir),
        "generation_manifest_path": str(run_dir / "generation_manifest.json"),
        "parse_diagnostics_path": str(run_dir / f"parse_diagnostics.{split}.json"),
        "canonical_path": str(canonical_path),
        "parse_status_counts": dict(sorted(parse_status_counts.items())),
        "parse_error": int(parse_status_counts.get("parse_error", 0) or 0),
        "schema_violation_rows": sum(1 for row in parsed_rows if row.get("parse_status") == "schema_violation"),
        "schema_violation": int(diagnostic_counts.get("schema_violation", 0) or 0),
        "unknown_role": int(diagnostic_counts.get("unknown_role", 0) or 0),
        "unknown_event_type": int(diagnostic_counts.get("unknown_event_type", 0) or 0),
        "canonical_rows": len(canonical_rows),
        "canonical_event_count": sum(len(row.get("events") or []) for row in canonical_rows),
        "canonical_schema_errors": validation["canonical_schema_errors"],
        "forbidden_key_violations": validation["forbidden_key_violations"],
        "evaluator_attempted": bool(evaluator.get("attempted")),
        "evaluator_returncode": evaluator.get("returncode"),
        "evaluator_artifact_out_dir": evaluator.get("artifact_out_dir"),
        "evaluator_artifact_root": evaluator.get("artifact_root"),
        "evaluator_validation_ok": evaluator_metrics.get("validation_ok"),
        "event_table_micro_f1": evaluator_metrics.get("event_table_micro_f1"),
        "role_level_f1": evaluator_metrics.get("role_level_f1"),
        "exact_record_f1": evaluator_metrics.get("exact_record_f1"),
    }
    return summary


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


def _config_data_root(config: dict[str, Any]) -> str:
    return str(((config.get("predict") or {}).get("data_root")) or ((config.get("data") or {}).get("data_root")) or "data")


def _prompt_doc_ids(path: Path) -> list[str]:
    return [str(row.get("doc_id") or "") for row in read_jsonl(path)]


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
