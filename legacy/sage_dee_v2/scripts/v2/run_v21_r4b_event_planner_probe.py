from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from collections.abc import Sequence
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "src"))

from sage_dee.io_utils import read_yaml  # noqa: E402
from sage_dee.v2.data_interface.dataset_loader import load_documents  # noqa: E402
from sage_dee.v2.data_interface.jsonl import read_jsonl  # noqa: E402
from sage_dee.v2.data_interface.schema_registry import DatasetSchema, load_schema  # noqa: E402
from sage_dee.v2.pipeline.evaluator_handoff import build_evaluator_handoff, run_evaluator_handoff  # noqa: E402
from sage_dee.v2.pipeline.export_canonical import (  # noqa: E402
    export_predictions,
    validate_minimal_canonical_prediction,
)
from sage_dee.v2.postprocess.event_planner_v21 import (  # noqa: E402
    SUPPORTED_MODES,
    TARGET_EVENT_TYPES,
    EventRecord,
    PlannerDiagnostics,
    apply_planner,
)

EXPECTED_DATASET = "DuEE-Fin-dev500"
EXPECTED_SPLIT = "dev"
EXPECTED_SOURCE_ROW = "s4_full_or_max_frozen_surface"
R0_REPORT = REPO_ROOT / "docs/refactor/SAGE_V2_1_R0_BRANCH_SETUP.md"
R1_REPORT = REPO_ROOT / "docs/refactor/SAGE_V2_1_R1_PARSER_REPARSE_ABLATION.md"
R2_REPORT = REPO_ROOT / "docs/refactor/SAGE_V2_1_R2_SURFACE_COVERAGE_FIRST.md"
R3_REPORT = REPO_ROOT / "docs/refactor/SAGE_V2_1_R3_S4_TRAIN_SIZE_SCALING.md"
R4_REPORT = REPO_ROOT / "docs/refactor/SAGE_V2_1_R4_EVENT_GROUPING_PROBE.md"
CHANGELOG = REPO_ROOT / "docs/refactor/SAGE_V2_1_DEV_RESCUE_CHANGELOG.md"
FINAL_RESULT = REPO_ROOT / "docs/refactor/SAGE_V2_FINAL_TEST_RESULT.json"
GOLD_CONFIG_KEYS = frozenset(
    {
        "gold_path",
        "dev_gold_path",
        "planner_gold_path",
        "non_oracle_gold_path",
        "gold_event_count_path",
        "gold_argument_path",
    }
)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        config = read_yaml(args.config)
        _validate_args(args, config)
        args.out_root.mkdir(parents=True, exist_ok=True)
        summary = run_probe(args=args, config=config)
    except (OSError, RuntimeError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2

    print(f"run_root={args.out_root}")
    print(f"variant_count={len(summary['variants'])}")
    print(f"run_manifest={args.out_root / 'run_manifest.json'}")
    return 0


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run SAGE v2.1 R4b event planner dev-only probe.")
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--dataset", required=True)
    parser.add_argument("--split", required=True)
    parser.add_argument("--source-prediction", type=Path, required=True)
    parser.add_argument("--out-root", type=Path, required=True)
    return parser.parse_args(argv)


def run_probe(*, args: argparse.Namespace, config: dict[str, Any]) -> dict[str, Any]:
    schema = load_schema(args.dataset, data_root=_data_root(config))
    documents = load_documents(args.dataset, args.split, data_root=_data_root(config), mode="predict")
    source_hash_before = _sha256(args.source_prediction)
    source_rows = read_jsonl(args.source_prediction)
    _validate_source_rows(source_rows, schema=schema)

    variants = [str(item) for item in config.get("variants") or []]
    variant_summaries = []
    for variant in variants:
        variant_summaries.append(
            _run_variant(
                variant,
                source_rows=source_rows,
                schema=schema,
                args=args,
                config=config,
            )
        )

    source_hash_after = _sha256(args.source_prediction)
    if source_hash_after != source_hash_before:
        raise RuntimeError("R4b refuses to continue: source prediction was modified")

    manifest = {
        "phase": "R4b event planner / record assembler dev probe",
        "created_at": _created_at(),
        "dataset": args.dataset,
        "split": args.split,
        "source_row": EXPECTED_SOURCE_ROW,
        "source_prediction_path": str(args.source_prediction),
        "source_prediction_sha256": source_hash_before,
        "source_prediction_unchanged": True,
        "document_count": len(documents),
        "variants": variants,
        "variant_summaries": [summary["summary_path"] for summary in variant_summaries],
        "scope": {
            "dev_only": True,
            "seed42_only": True,
            "s4_only": True,
            "test_run": False,
            "test_gold_read": False,
            "qwen_run": False,
            "train_run": False,
            "evaluator_modified": False,
            "source_prediction_overwritten": False,
            "gold_in_non_oracle_planner": False,
            "frozen_final_modified": False,
        },
        "oracle_diagnostics": _oracle_diagnostics(config),
    }
    _write_json(args.out_root / "run_manifest.json", manifest)
    return {"variants": variant_summaries, "manifest": manifest}


def _run_variant(
    variant: str,
    *,
    source_rows: list[dict[str, Any]],
    schema: DatasetSchema,
    args: argparse.Namespace,
    config: dict[str, Any],
) -> dict[str, Any]:
    variant_dir = args.out_root / variant
    source_manifest = _source_run_manifest(args.source_prediction)
    planned_rows = []
    aggregate = PlannerDiagnostics(mode=variant)
    changed_docs = []
    for row in source_rows:
        doc_id = str(row.get("doc_id") or "")
        source_events = [EventRecord.from_canonical(event) for event in row.get("events") or []]
        planned_events, diagnostics = apply_planner(source_events, mode=variant, schema=schema)
        aggregate.merge_child(diagnostics, doc_id=doc_id)
        planned_row = {"doc_id": doc_id, "events": [event.to_canonical() for event in planned_events]}
        validate_minimal_canonical_prediction(planned_row, schema=schema)
        planned_rows.append(planned_row)
        if planned_row != {"doc_id": doc_id, "events": deepcopy(row.get("events") or [])}:
            changed_docs.append(doc_id)

    prediction_path = variant_dir / "predictions" / args.dataset / f"{args.split}.canonical.pred.jsonl"
    export_predictions(planned_rows, prediction_path, schema=schema)
    planner_diagnostics = aggregate.to_dict()
    planner_diagnostics["changed_doc_count"] = len(changed_docs)
    planner_diagnostics["changed_docs"] = sorted(changed_docs)
    _write_json(variant_dir / "planner_diagnostics.json", planner_diagnostics)
    _write_json(
        variant_dir / "run_manifest.json",
        _variant_run_manifest(
            variant=variant,
            prediction_path=prediction_path,
            source_manifest=source_manifest,
            args=args,
        ),
    )
    evaluator = _run_evaluator(variant_dir, args=args, config=config, variant=variant)
    summary = {
        "phase": "R4b event planner / record assembler dev probe",
        "variant": variant,
        "dataset": args.dataset,
        "split": args.split,
        "canonical_prediction_path": str(prediction_path),
        "canonical_rows": len(planned_rows),
        "canonical_event_count": sum(len(row.get("events") or []) for row in planned_rows),
        "changed_doc_count": len(changed_docs),
        "changed_docs": sorted(changed_docs),
        "planner_diagnostics": planner_diagnostics,
        "evaluator": evaluator,
        "scope": {
            "dev_only": True,
            "test_run": False,
            "qwen_run": False,
            "train_run": False,
            "gold_in_non_oracle_planner": False,
        },
        "created_at": _created_at(),
    }
    summary_path = variant_dir / "variant_summary.json"
    _write_json(summary_path, summary)
    summary["summary_path"] = str(summary_path)
    return summary


def _validate_args(args: argparse.Namespace, config: dict[str, Any]) -> None:
    if args.split == "test":
        raise ValueError("R4b rejects test split")
    if args.split != EXPECTED_SPLIT:
        raise ValueError(f"R4b only permits dev split, got {args.split!r}")
    if args.dataset != EXPECTED_DATASET:
        raise ValueError(f"R4b is restricted to {EXPECTED_DATASET}, got {args.dataset!r}")
    if _path_mentions_test(args.source_prediction) or _path_mentions_test(args.out_root):
        raise ValueError("R4b rejects paths that mention test")
    if config.get("allow_test") is not False:
        raise ValueError("R4b config must set allow_test: false")
    if config.get("allow_gold_in_non_oracle_planner") is not False:
        raise ValueError("R4b config must set allow_gold_in_non_oracle_planner: false")
    forbidden = sorted(key for key in GOLD_CONFIG_KEYS if config.get(key))
    if forbidden:
        raise ValueError(f"R4b non-oracle planner rejects gold config keys: {forbidden}")
    if str(config.get("dataset")) != args.dataset or str(config.get("split")) != args.split:
        raise ValueError("R4b config dataset/split must match CLI")
    if str(config.get("source_row")) != EXPECTED_SOURCE_ROW:
        raise ValueError("R4b requires R3 Row D s4_full_or_max_frozen_surface")
    variants = [str(item) for item in config.get("variants") or []]
    required = {"pass_through", "dedup_only", "conservative_assembler_v1"}
    if not required <= set(variants):
        raise ValueError(f"R4b variants must include {sorted(required)}")
    unsupported = sorted(set(variants) - SUPPORTED_MODES)
    if unsupported:
        raise ValueError(f"R4b unsupported variants: {unsupported}")
    target_event_types = set(str(item) for item in config.get("target_event_types") or [])
    if target_event_types != set(TARGET_EVENT_TYPES):
        raise ValueError("R4b target event types must match the R4 high-risk set")
    _require_gate_documents()
    if not args.source_prediction.is_file():
        raise ValueError(f"missing source prediction: {args.source_prediction}")


def _variant_run_manifest(
    *,
    variant: str,
    prediction_path: Path,
    source_manifest: dict[str, Any],
    args: argparse.Namespace,
) -> dict[str, Any]:
    created_at = _created_at()
    return {
        "run_id": f"v21_r4b_{variant}_{created_at.replace('-', '').replace(':', '').replace('Z', 'Z')}",
        "method_name": f"SAGE-DEE-v2.1-R4b-{variant}",
        "method_family": "SAGE-DEE-v2",
        "dataset_version": args.dataset,
        "split_version": args.split,
        "evaluator_version": source_manifest.get("evaluator_version") or "eval-artifacts-v1.1",
        "prediction_format": source_manifest.get("prediction_format") or "canonical-jsonl",
        "training_view": "post_generation_existing_R3_Row_D",
        "gold_view": source_manifest.get("gold_view") or f"processed/views/evaluator_gold/{args.dataset}",
        "seed": 42,
        "git_commit": source_manifest.get("git_commit") or _git_commit(),
        "command_train": None,
        "command_infer": (
            "/home/TJK/.conda/envs/tjk-feg/bin/python "
            "scripts/v2/run_v21_r4b_event_planner_probe.py"
        ),
        "notes": (
            "R4b dev-only post-generation event planner probe; no Qwen, no training, "
            "no test split, no gold in non-oracle planner."
        ),
        "phase": "R4b event planner / record assembler dev probe",
        "variant": variant,
        "dataset": args.dataset,
        "split": args.split,
        "canonical_predictions_path": str(prediction_path),
        "source_prediction_path": str(args.source_prediction),
        "gold_visible": False,
        "test_run": False,
        "qwen_run": False,
        "train_run": False,
        "created_at": created_at,
    }


def _require_gate_documents() -> None:
    for path in (R0_REPORT, R1_REPORT, R2_REPORT, R3_REPORT, R4_REPORT, CHANGELOG, FINAL_RESULT):
        if not path.is_file():
            raise ValueError(f"missing R4b gate document: {path}")
    r4 = R4_REPORT.read_text(encoding="utf-8")
    if '"recommended_next_phase": "R4b_event_planner_dev_probe"' not in r4:
        raise ValueError("R4b gate missing R4 recommended_next_phase")
    if '"grouping_bottleneck": "high"' not in r4:
        raise ValueError("R4b gate missing grouping_bottleneck=high")
    normalized_r4 = " ".join(r4.split())
    for required in ("did not run Qwen", "did not train", "did not run the `test` split", "did not read test gold"):
        if required not in normalized_r4:
            raise ValueError(f"R4b gate missing R4 no-run statement: {required}")


def _validate_source_rows(rows: list[dict[str, Any]], *, schema: DatasetSchema) -> None:
    for row in rows:
        validate_minimal_canonical_prediction(row, schema=schema)


def _run_evaluator(
    variant_dir: Path,
    *,
    args: argparse.Namespace,
    config: dict[str, Any],
    variant: str,
) -> dict[str, Any]:
    out_dir = args.out_root / "evaluator_artifacts" / variant
    handoff = build_evaluator_handoff(
        run_root=variant_dir,
        dataset=args.dataset,
        split=args.split,
        data_repo_root=Path(str(config.get("evaluator_root") or "/home/TJK/DEE/dee-eval")),
        out_dir=out_dir,
        benchmark_root=Path(str(config.get("benchmark_root") or "/data/TJK/DEE/data/processed")),
        strict=True,
    )
    result = run_evaluator_handoff(handoff)
    _write_json(variant_dir / "v21_r4b_evaluator_handoff.json", {"handoff": handoff.to_dict(), "result": result})
    if result.get("attempted") and result.get("returncode") != 0:
        raise RuntimeError(f"R4b evaluator failed for {variant}: {result.get('stderr')}")
    artifact_root = _extract_artifact_root(result.get("stdout"))
    metrics = _read_evaluator_metrics(artifact_root, dataset=args.dataset, split=args.split)
    return {
        "attempted": result.get("attempted"),
        "returncode": result.get("returncode"),
        "evaluator_artifact_out_dir": str(out_dir),
        "evaluator_artifact_root": artifact_root,
        "evaluator_validation_ok": metrics.get("validation_ok"),
        "event_table_micro_f1": metrics.get("event_table_micro_f1"),
        "role_level_f1": metrics.get("role_level_f1"),
        "exact_record_f1": metrics.get("exact_record_f1"),
        "event_count_acc": metrics.get("event_count_acc"),
        "merge_count": metrics.get("merge_count"),
        "split_count": metrics.get("split_count"),
        "wrong_grouping_count": metrics.get("wrong_grouping_count"),
        "stdout": result.get("stdout"),
        "stderr": result.get("stderr"),
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
        metrics["event_count_acc"] = record.get("event_count_acc")
        metrics["merge_count"] = record.get("merge_case_count")
        metrics["split_count"] = record.get("split_case_count")
        metrics["wrong_grouping_count"] = record.get("wrong_grouping_case_count")
    if validation_path.is_file():
        validation = _read_json(validation_path)
        metrics["validation_ok"] = validation.get("ok")
    return metrics


def _oracle_diagnostics(config: dict[str, Any]) -> dict[str, Any]:
    analysis_path = Path(str(config.get("r4_analysis_path") or ""))
    if not analysis_path.is_file():
        return {
            "label": "dev_only_non_performance",
            "available": False,
            "performance_claim_allowed": False,
        }
    analysis = _read_json(analysis_path)
    event_count = analysis.get("event_count_diagnostics") or {}
    record = analysis.get("record_level_decomposition") or {}
    oracle = analysis.get("oracle_diagnostics") or {}
    event_type = analysis.get("event_type_residual_errors") or {}
    exact_f1 = _number(oracle.get("exact_record_f1"))
    soft_f1 = _number((oracle.get("oracle_grouping_upper_bound") or {}).get("record_f1_soft_0_8"))
    return {
        "label": "dev_only_non_performance",
        "available": True,
        "source_analysis_path": str(analysis_path),
        "gold_event_count": sum(
            int(count) * int(event_count_value)
            for event_count_value, count in (event_count.get("gold_event_count_distribution") or {}).items()
        ),
        "predicted_event_count": sum(
            int(count) * int(event_count_value)
            for event_count_value, count in (event_count.get("predicted_event_count_distribution") or {}).items()
        ),
        "event_count_oracle_possible_affected_doc_count": int(event_count.get("under_predicted_doc_count") or 0)
        + int(event_count.get("over_predicted_doc_count") or 0),
        "value_correct_wrong_record_proxy": record.get("value_correct_but_wrong_record_count"),
        "soft_record_to_exact_gap": None if exact_f1 is None or soft_f1 is None else soft_f1 - exact_f1,
        "event_types_where_oracle_grouping_likely_helps_most": (
            event_type.get("event_types_likely_requiring_event_planner") or []
        )[:10],
        "performance_claim_allowed": False,
    }


def _data_root(config: dict[str, Any]) -> Path:
    return Path(str(config.get("data_root") or config.get("benchmark_root") or "data"))


def _path_mentions_test(path: Path) -> bool:
    return any(part.lower() == "test" for part in path.parts)


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


def _read_json(path: str | Path) -> dict[str, Any]:
    with Path(path).open(encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must load as a mapping")
    return payload


def _source_run_manifest(source_prediction: Path) -> dict[str, Any]:
    candidate = source_prediction.parents[2] / "run_manifest.json" if len(source_prediction.parents) >= 3 else None
    if candidate and candidate.is_file():
        return _read_json(candidate)
    return {}


def _git_commit() -> str:
    completed = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode == 0:
        return completed.stdout.strip()
    return "unknown"


def _write_json(path: str | Path, payload: dict[str, Any]) -> None:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _created_at() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _number(value: Any) -> float | None:
    if isinstance(value, bool) or value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


if __name__ == "__main__":
    raise SystemExit(main())
