from __future__ import annotations

import argparse
import csv
import json
import subprocess
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))

from sage_dee.io_utils import read_yaml  # noqa: E402
from sage_dee.v2.data_interface.jsonl import read_jsonl  # noqa: E402
from sage_dee.v2.getm.scope_guard import validate_getm_prediction_scope  # noqa: E402
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
class AblationGroup:
    name: str
    max_new_tokens: int
    use_response_prefix: bool
    response_prefix: str | None
    enable_balanced_json_stopping: bool
    stop_after_balanced_events_json: bool


GROUPS = (
    AblationGroup("F0", 1024, True, '{"events":', False, False),
    AblationGroup("F1", 1024, True, '{"events":', True, True),
    AblationGroup("F2", 768, True, '{"events":', True, True),
    AblationGroup("F3", 1536, True, '{"events":', True, True),
    AblationGroup("F4", 1024, False, None, False, False),
    AblationGroup("F5", 1024, True, '{"events":[', True, True),
)

SUMMARY_FIELDS = (
    "group",
    "run_dir",
    "parse_status_counts",
    "parse_error",
    "parse_error_subtypes",
    "schema_violation_rows",
    "schema_subtypes",
    "candidate_list_continuation",
    "candidate_line_copy_count",
    "instruction_loop_count",
    "no_complete_json_object_count",
    "copied_prompt_marker_count",
    "schema_violation",
    "unknown_role",
    "unknown_event_type",
    "prompt_token_count_max",
    "prompt_token_count_mean",
    "prompt_token_count_4096_rows",
    "hit_max_new_tokens",
    "stop_reason_counts",
    "accepted_event_count",
    "raw_event_count",
    "canonical_rows",
    "canonical_schema_errors",
    "forbidden_key_violations",
    "source_candidate_id_in_canonical",
)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    args.out_root.mkdir(parents=True, exist_ok=True)
    summaries: list[dict[str, Any]] = []
    doc_subset: list[str] | None = None
    for group in GROUPS:
        run_dir = args.out_root / group.name
        run_dir.mkdir(parents=True, exist_ok=True)
        _run_group(args, group=group, run_dir=run_dir)
        summary = _summarize_group(group=group, run_dir=run_dir, dataset=args.dataset, split=args.split)
        summaries.append(summary)
        group_doc_subset = _prompt_doc_ids(run_dir / f"prompts.{args.split}.jsonl")
        if doc_subset is None:
            doc_subset = group_doc_subset
            _write_json(args.out_root / "doc_subset.dev20.json", {"split": args.split, "doc_ids": doc_subset})
        elif group_doc_subset != doc_subset:
            raise RuntimeError(f"{group.name} used a different doc subset")

    _write_json(args.out_root / "summary.json", {"groups": summaries})
    _write_summary_csv(args.out_root / "summary.csv", summaries)
    print(f"out_root={args.out_root}")
    print(f"summary_json={args.out_root / 'summary.json'}")
    print(f"summary_csv={args.out_root / 'summary.csv'}")
    return 0


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run guarded SAGE v2 GETM dev20 generation-setting ablations.")
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--dataset", default="DuEE-Fin-dev500")
    parser.add_argument("--data-root")
    parser.add_argument("--split", default="dev")
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--k", type=int, default=1)
    parser.add_argument("--dry-run", dest="dry_run", action="store_true", default=None)
    parser.add_argument("--real-run", action="store_true")
    parser.add_argument("--adapter-path")
    parser.add_argument("--enable-telemetry", action="store_true")
    parser.add_argument("--telemetry-interval-sec", type=float)
    parser.add_argument("--vram-soft-limit-gb", type=float)
    parser.add_argument("--vram-target-min-gb", type=float)
    parser.add_argument("--vram-target-max-gb", type=float)
    parser.add_argument("--fail-on-vram-limit", action="store_true")
    parser.add_argument("--out-root", type=Path, required=True)
    args = parser.parse_args(argv)
    if args.split != "dev":
        parser.error("phase 2 ablation only permits --split dev; test is forbidden")
    if args.limit != 20:
        parser.error("phase 2 ablation only permits --limit 20; full dev and limit=50 are forbidden")
    if args.k != 1:
        parser.error("phase 2 ablation only permits --k 1")
    try:
        validate_getm_prediction_scope(
            config_path=args.config,
            config=read_yaml(args.config),
            profile="",
            split=args.split,
            limit=args.limit,
        )
    except ValueError as exc:
        parser.error(str(exc))
    return args


def _run_group(args: argparse.Namespace, *, group: AblationGroup, run_dir: Path) -> None:
    cmd = [
        sys.executable,
        str(REPO_ROOT / "scripts/v2/generate_getm_qwen.py"),
        "--config",
        str(args.config),
        "--dataset",
        args.dataset,
        "--split",
        args.split,
        "--limit",
        str(args.limit),
        "--k",
        str(args.k),
        "--max-new-tokens",
        str(group.max_new_tokens),
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
        "--output-format",
        "minimal_text",
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
        "--prompt-token-budget",
        "4096",
        "--no-fail-on-prompt-token-limit",
        "--out-dir",
        str(run_dir),
    ]
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
    cmd.append("--use-response-prefix" if group.use_response_prefix else "--no-use-response-prefix")
    if group.response_prefix is not None:
        cmd.extend(["--response-prefix", group.response_prefix])
    cmd.append(
        "--enable-balanced-json-stopping"
        if group.enable_balanced_json_stopping
        else "--no-enable-balanced-json-stopping"
    )
    cmd.append(
        "--stop-after-balanced-events-json"
        if group.stop_after_balanced_events_json
        else "--no-stop-after-balanced-events-json"
    )

    completed = subprocess.run(cmd, cwd=REPO_ROOT, check=False, capture_output=True, text=True)
    (run_dir / "ablation_command.json").write_text(
        json.dumps({"cmd": cmd, "returncode": completed.returncode}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (run_dir / "ablation.stdout.log").write_text(completed.stdout, encoding="utf-8")
    (run_dir / "ablation.stderr.log").write_text(completed.stderr, encoding="utf-8")
    if completed.returncode != 0:
        raise RuntimeError(f"{group.name} failed with exit code {completed.returncode}: {completed.stderr}")


def _summarize_group(*, group: AblationGroup, run_dir: Path, dataset: str, split: str) -> dict[str, Any]:
    diagnostics = _read_json(run_dir / f"parse_diagnostics.{split}.json")
    parsed_rows = read_jsonl(run_dir / f"parsed_candidates.{split}.jsonl")
    canonical_path = run_dir / "predictions" / dataset / f"{split}.canonical.pred.jsonl"
    canonical_rows = read_jsonl(canonical_path)
    validation = _canonical_validation(canonical_rows)
    diagnostic_counts = diagnostics.get("diagnostic_counts") or {}
    prompt_summary = diagnostics.get("prompt_token_summary") or {}
    parse_status_counts = diagnostics.get("parse_status_counts") or {}
    parse_error_subtypes = diagnostics.get("parse_error_subtype_counts") or {}
    schema_subtypes = _schema_subtypes(diagnostic_counts)
    stop_reason_counts = diagnostics.get("stop_reason_counts") or _stop_reason_counts(parsed_rows)
    summary = {
        "group": group.name,
        "run_dir": str(run_dir),
        "parse_status_counts": dict(sorted(parse_status_counts.items())),
        "parse_error": int(parse_status_counts.get("parse_error", 0) or 0),
        "parse_error_subtypes": dict(sorted(parse_error_subtypes.items())),
        "schema_violation_rows": sum(1 for row in parsed_rows if row.get("parse_status") == "schema_violation"),
        "schema_subtypes": schema_subtypes,
        "candidate_list_continuation": int(parse_error_subtypes.get("candidate_list_continuation", 0) or 0),
        "candidate_line_copy_count": int(diagnostic_counts.get("candidate_line_copy_count", 0) or 0),
        "instruction_loop_count": int(diagnostic_counts.get("instruction_loop_count", 0) or 0),
        "no_complete_json_object_count": int(diagnostic_counts.get("no_complete_json_object_count", 0) or 0),
        "copied_prompt_marker_count": int(diagnostic_counts.get("copied_prompt_marker_count", 0) or 0),
        "schema_violation": int(diagnostic_counts.get("schema_violation", 0) or 0),
        "unknown_role": int(diagnostic_counts.get("unknown_role", 0) or 0),
        "unknown_event_type": int(diagnostic_counts.get("unknown_event_type", 0) or 0),
        "prompt_token_count_max": prompt_summary.get("max"),
        "prompt_token_count_mean": prompt_summary.get("mean"),
        "prompt_token_count_4096_rows": int(prompt_summary.get("rows_at_budget", 0) or 0),
        "hit_max_new_tokens": int(diagnostic_counts.get("hit_max_new_tokens", 0) or 0),
        "stop_reason_counts": dict(sorted(stop_reason_counts.items())),
        "accepted_event_count": int(diagnostic_counts.get("accepted_event_count", 0) or 0),
        "raw_event_count": int(diagnostic_counts.get("raw_event_count", 0) or 0),
        "canonical_rows": len(canonical_rows),
        "canonical_schema_errors": validation["canonical_schema_errors"],
        "forbidden_key_violations": validation["forbidden_key_violations"],
        "source_candidate_id_in_canonical": validation["source_candidate_id_in_canonical"],
        "canonical_path": str(canonical_path),
        "enable_balanced_json_stopping": group.enable_balanced_json_stopping,
        "max_new_tokens": group.max_new_tokens,
        "use_response_prefix": group.use_response_prefix,
        "response_prefix": group.response_prefix,
    }
    _write_json(run_dir / "ablation_summary.json", summary)
    return summary


def _schema_subtypes(diagnostic_counts: dict[str, Any]) -> dict[str, int]:
    keys = (
        "unknown_event_type",
        "unknown_role",
        "invalid_event_object_count",
        "invalid_arguments_shape_count",
        "empty_arguments_count",
        "duplicate_argument",
        "event_type_not_string_count",
        "role_value_not_list_count",
        "unexpected_source_candidate_id_count",
    )
    return {key: int(diagnostic_counts.get(key, 0) or 0) for key in keys}


def _stop_reason_counts(parsed_rows: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in parsed_rows:
        diagnostics = row.get("diagnostics") or {}
        if not isinstance(diagnostics, dict):
            continue
        reason = diagnostics.get("stop_reason")
        if isinstance(reason, str) and reason:
            counts[reason] = counts.get(reason, 0) + 1
    return counts


def _canonical_validation(canonical_rows: list[dict[str, Any]]) -> dict[str, Any]:
    schema_errors = 0
    forbidden_violations = 0
    source_candidate_id_in_canonical = False
    for row in canonical_rows:
        try:
            validate_minimal_canonical_prediction(row)
        except ValueError:
            schema_errors += 1
        forbidden_paths = _forbidden_key_paths(row)
        forbidden_violations += len(forbidden_paths)
        source_candidate_id_in_canonical = source_candidate_id_in_canonical or any(
            path.endswith("source_candidate_id") for path in forbidden_paths
        )
    return {
        "canonical_schema_errors": schema_errors,
        "forbidden_key_violations": forbidden_violations,
        "source_candidate_id_in_canonical": source_candidate_id_in_canonical,
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


def _prompt_doc_ids(path: Path) -> list[str]:
    return [str(row.get("doc_id") or "") for row in read_jsonl(path)]


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


def _read_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object: {path}")
    return payload


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
