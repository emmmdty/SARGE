from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path
from shlex import join
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "src"))

from sage_dee.io_utils import read_yaml, write_yaml  # noqa: E402
from sage_dee.v2.data_interface.dataset_loader import load_documents  # noqa: E402
from sage_dee.v2.data_interface.jsonl import read_jsonl, write_jsonl  # noqa: E402
from sage_dee.v2.getm.generation_diagnostics import (  # noqa: E402
    DIAGNOSTIC_VERSION,
    aggregate_parse_diagnostics,
)
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
    _sha256,
    _write_json,
)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    config = read_yaml(args.config)
    try:
        _validate_args(args, config)
        merge = _merge_shards(args, config)
    except (RuntimeError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    evaluator = _run_evaluator(
        args,
        run_dir=args.out_dir,
        dataset=_dataset(args, config),
        split=args.split,
        benchmark_root=_benchmark_root(args, config),
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
    _write_json(
        args.out_dir / "phase11_run_summary.json",
        _run_summary(
            args,
            config=config,
            merge=merge,
            evaluator=evaluator_summary,
            diagnostics=diagnostics,
        ),
    )
    print(f"run_root={args.out_dir}")
    print(f"canonical_path={merge['canonical_path']}")
    print(f"analysis_json={diagnostics['analysis']}")
    if evaluator_summary.get("evaluator_artifact_root"):
        print(f"evaluator_artifact_root={evaluator_summary['evaluator_artifact_root']}")
    return 0


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Merge Phase 11 DocFEE stress shards and run external evaluator.")
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--shard-roots", type=Path, nargs="+", required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--dataset")
    parser.add_argument("--split", default="dev")
    parser.add_argument("--data-root")
    parser.add_argument("--evaluator-root", type=Path)
    parser.add_argument("--benchmark-root", type=Path)
    parser.add_argument("--skip-evaluator", action="store_true")
    return parser.parse_args(argv)


def _validate_args(args: argparse.Namespace, config: dict[str, Any]) -> None:
    if args.split == "test":
        raise ValueError("Phase 11 merge rejects test split; test split remains blocked")
    if args.split != "dev":
        raise ValueError(f"Phase 11 merge only permits dev split, got {args.split!r}")
    if _dataset(args, config) != "DocFEE-dev1000":
        raise ValueError("Phase 11 merge only permits dataset DocFEE-dev1000")
    phase11 = config.get("phase11") or {}
    for key in ("train_used", "full_train_used", "docfee_train_used"):
        if phase11.get(key) is not False:
            raise ValueError(f"Phase 11 merge requires {key}=false; training remains blocked")
    if phase11.get("test_blocked") is not True:
        raise ValueError("Phase 11 merge requires test_blocked=true")
    if phase11.get("no_profile_tuning") is not True:
        raise ValueError("Phase 11 merge rejects profile tuning")


def _merge_shards(args: argparse.Namespace, config: dict[str, Any]) -> dict[str, Any]:
    args.out_dir.mkdir(parents=True, exist_ok=True)
    dataset = _dataset(args, config)
    split = args.split
    expected_doc_ids = _expected_doc_ids(args, config)
    order = {doc_id: index for index, doc_id in enumerate(expected_doc_ids)}
    shard_summaries = [_read_json(root / "phase11_run_summary.json") for root in args.shard_roots]
    _validate_shards(args.shard_roots, shard_summaries, dataset=dataset, split=split)
    prompts = _sorted_rows(_collect_jsonl(args.shard_roots, f"prompts.{split}.jsonl"), order=order, key="doc_id")
    raw_rows = _sorted_rows(_collect_jsonl(args.shard_roots, f"raw_outputs.{split}.jsonl"), order=order, key="doc_id")
    parsed_rows = _sorted_rows(
        _collect_jsonl(args.shard_roots, f"parsed_candidates.{split}.jsonl"),
        order=order,
        key="doc_id",
    )
    canonical_rel = Path("predictions") / dataset / f"{split}.canonical.pred.jsonl"
    canonical_rows = _sorted_rows(_collect_jsonl(args.shard_roots, str(canonical_rel)), order=order, key="doc_id")
    _require_exact_coverage(canonical_rows, expected_doc_ids=expected_doc_ids)
    _require_exact_coverage(prompts, expected_doc_ids=expected_doc_ids)
    write_jsonl(args.out_dir / f"prompts.{split}.jsonl", prompts)
    write_jsonl(args.out_dir / f"raw_outputs.{split}.jsonl", raw_rows)
    write_jsonl(args.out_dir / f"parsed_candidates.{split}.jsonl", parsed_rows)
    canonical_path = write_jsonl(args.out_dir / canonical_rel, canonical_rows)
    first_generation = _read_json(args.shard_roots[0] / "generation_manifest.json")
    parse_diagnostics = aggregate_parse_diagnostics(
        parsed_rows,
        dataset=dataset,
        split=split,
        k=1,
        generation_metadata=first_generation.get("generation") or {},
    )
    _write_json(args.out_dir / f"parse_diagnostics.{split}.json", parse_diagnostics)
    _write_json(args.out_dir / "run_manifest.json", _run_manifest(config=config, dataset=dataset, split=split))
    _write_json(
        args.out_dir / "generation_manifest.json",
        {
            "diagnostic_version": DIAGNOSTIC_VERSION,
            "backend": first_generation.get("backend"),
            "dry_run": False,
            "real_run": True,
            "profile": (config.get("run") or {}).get("profile"),
            "baseline_id": "S4",
            "dataset": dataset,
            "split": split,
            "document_count": len(canonical_rows),
            "k": 1,
            "merged_from_shards": [str(root) for root in args.shard_roots],
            "prompts_path": str(args.out_dir / f"prompts.{split}.jsonl"),
            "raw_outputs_path": str(args.out_dir / f"raw_outputs.{split}.jsonl"),
            "parsed_candidates_path": str(args.out_dir / f"parsed_candidates.{split}.jsonl"),
            "parse_diagnostics_path": str(args.out_dir / f"parse_diagnostics.{split}.json"),
            "canonical_predictions_path": str(canonical_path),
            "gold_visible": False,
            "phase11_stage": "merged_sharded_full_dev",
            "generation": first_generation.get("generation") or {},
        },
    )
    write_yaml(args.out_dir / "phase11_config.resolved.yaml", config)
    return {
        "canonical_path": str(canonical_path),
        "canonical_rows": len(canonical_rows),
        "parse_diagnostics_path": str(args.out_dir / f"parse_diagnostics.{split}.json"),
        "generation_manifest_path": str(args.out_dir / "generation_manifest.json"),
        "run_manifest_path": str(args.out_dir / "run_manifest.json"),
        "shards": shard_summaries,
    }


def _validate_shards(
    shard_roots: list[Path],
    summaries: list[dict[str, Any]],
    *,
    dataset: str,
    split: str,
) -> None:
    if len(shard_roots) < 2:
        raise RuntimeError("Phase 11 shard merge requires at least two shard roots")
    seen_indices: set[int] = set()
    expected_count: int | None = None
    for root, summary in zip(shard_roots, summaries, strict=True):
        scope = summary.get("scope") or {}
        if scope.get("dataset") != dataset or scope.get("split") != split:
            raise RuntimeError(f"shard scope mismatch: {root}")
        if scope.get("test_used") or scope.get("train_used") or scope.get("full_train_used"):
            raise RuntimeError(f"shard used blocked split/train path: {root}")
        shard = scope.get("shard") or {}
        if not isinstance(shard, dict):
            raise RuntimeError(f"missing shard metadata: {root}")
        index = shard.get("index")
        count = shard.get("count")
        if not isinstance(index, int) or not isinstance(count, int):
            raise RuntimeError(f"invalid shard metadata: {root}")
        if expected_count is None:
            expected_count = count
        if count != expected_count:
            raise RuntimeError("all shards must use the same shard_count")
        seen_indices.add(index)
    if expected_count is None or seen_indices != set(range(expected_count)):
        raise RuntimeError(f"missing shard indices: expected {expected_count}, got {sorted(seen_indices)}")


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
    merge: dict[str, Any],
    evaluator: dict[str, Any],
    diagnostics: dict[str, Path],
) -> dict[str, Any]:
    scope = {
        "dataset": _dataset(args, config),
        "split": args.split,
        "document_count": merge.get("canonical_rows"),
        "stage": "merged_sharded_full_dev",
        "phase6_adapter_reused": True,
        "train_used": False,
        "full_train_used": False,
        "docfee_train_used": False,
        "test_used": False,
        "dry_run": False,
        "real_run": True,
        "no_profile_tuning": True,
        "no_post_full_dev_tuning": True,
        "no_prompt_parser_surface_tuning": True,
        "merged_shards": [str(root) for root in args.shard_roots],
    }
    return {
        "phase": "Phase 11 DocFEE stress analysis",
        "dataset": _dataset(args, config),
        "split": args.split,
        "baseline_id": "S4",
        "profile": (config.get("phase11") or {}).get("profile_source"),
        "phase6_source_profile": "phase6_s4_role_safe_surface_memory",
        "seed": 42,
        "run_dir": str(args.out_dir),
        "config_path": str(args.config),
        "config_sha256": _sha256(args.config),
        "scope": scope,
        "merge": merge,
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


def _run_manifest(*, config: dict[str, Any], dataset: str, split: str) -> dict[str, Any]:
    return {
        "run_id": f"phase11_docfee_stress_merged_{_created_slug()}",
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
        "backend": "qwen",
        "dry_run": False,
        "real_run": True,
        "profile": (config.get("run") or {}).get("profile"),
        "command_train": None,
        "command_infer": join([sys.executable, "scripts/v2/merge_phase11_docfee_stress_shards.py"]),
        "git_commit": _git_commit(),
        "created_at": _created_at(),
        "notes": (
            "Phase 11 merged sharded DocFEE dev stress analysis; no train, no test, "
            "no prompt/parser/surface-memory/profile/evaluator tuning."
        ),
    }


def _expected_doc_ids(args: argparse.Namespace, config: dict[str, Any]) -> list[str]:
    limit = int((config.get("phase11") or {}).get("max_predict_docs") or 1000)
    docs = load_documents(
        _dataset(args, config),
        args.split,
        data_root=_data_root(args, config),
        mode="predict",
        limit=limit,
    )
    return [doc.doc_id for doc in docs]


def _collect_jsonl(shard_roots: list[Path], relative_path: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for root in shard_roots:
        path = root / relative_path
        if not path.is_file():
            raise RuntimeError(f"missing shard artifact: {path}")
        rows.extend(read_jsonl(path))
    return rows


def _sorted_rows(rows: list[dict[str, Any]], *, order: dict[str, int], key: str) -> list[dict[str, Any]]:
    return sorted(rows, key=lambda row: order.get(str(row.get(key) or ""), len(order)))


def _require_exact_coverage(rows: list[dict[str, Any]], *, expected_doc_ids: list[str]) -> None:
    actual = [str(row.get("doc_id") or "") for row in rows]
    expected = set(expected_doc_ids)
    actual_set = set(actual)
    if len(actual) != len(actual_set):
        raise RuntimeError("merged shard rows contain duplicate doc_id values")
    if actual_set != expected:
        missing = sorted(expected - actual_set)[:10]
        extra = sorted(actual_set - expected)[:10]
        raise RuntimeError(f"merged shard coverage mismatch; missing={missing}, extra={extra}")


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


def _read_json(path: str | Path) -> dict[str, Any]:
    with Path(path).open(encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object: {path}")
    return payload


if __name__ == "__main__":
    raise SystemExit(main())
