from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from datetime import datetime, timezone
from pathlib import Path
from shlex import join
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))

from sage_dee.v2.contracts.surface import SurfaceCandidate, SurfaceMemory  # noqa: E402
from sage_dee.v2.csg.audit import write_audit_outputs  # noqa: E402
from sage_dee.v2.csg.candidate_builder import build_surface_memories  # noqa: E402
from sage_dee.v2.csg.surface_memory import surface_memory_to_dict  # noqa: E402
from sage_dee.v2.csg.weak_alignment import align_gold_arguments  # noqa: E402
from sage_dee.v2.data_interface.dataset_loader import load_documents  # noqa: E402
from sage_dee.v2.data_interface.jsonl import read_jsonl, write_jsonl  # noqa: E402
from sage_dee.v2.data_interface.schema_registry import load_schema  # noqa: E402
from sage_dee.v2.getm.candidate_generator import generate_getm_candidate_files  # noqa: E402
from sage_dee.v2.getm.mock_backend import MockGetmBackend  # noqa: E402
from sage_dee.v2.lesp.audit import audit_slot_plans  # noqa: E402
from sage_dee.v2.lesp.baseline_planner import TrainPriorPlanner  # noqa: E402
from sage_dee.v2.lesp.slot_plan import slot_plan_from_dict, slot_plan_to_dict  # noqa: E402
from sage_dee.v2.mrs.selector import select_candidate_rows  # noqa: E402
from sage_dee.v2.mrs.simple_ranker import default_rule_based_model  # noqa: E402
from sage_dee.v2.pipeline.evaluator_handoff import DEFAULT_DATA_REPO_ROOT  # noqa: E402
from sage_dee.v2.pipeline.export_canonical import (  # noqa: E402
    export_predictions,
    validate_minimal_canonical_prediction,
)
from sage_dee.v2.pipeline.run_v2_smoke import run_v2_smoke  # noqa: E402

DEFAULT_DATASETS = ("DuEE-Fin-dev500", "ChFinAnn", "DocFEE-dev1000")
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
    summary = run_final_smoke(
        out_root=args.out_root,
        dataset=args.dataset,
        split=args.split,
        data_root=args.data_root,
        limit=args.limit,
        train_limit=args.train_limit,
        k=args.k,
        data_interface_datasets=tuple(args.data_interface_dataset),
        data_repo_root=args.data_repo_root,
    )
    print(f"summary={args.out_root / 'summary.json'}")
    print(f"status={summary['status']}")
    print(f"evaluator_handoff_command={summary['steps']['evaluator_handoff']['command']}")
    return 0


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run final SAGE-DEE v2 local acceptance smoke.")
    parser.add_argument("--out-root", type=Path, required=True)
    parser.add_argument("--dataset", default="DuEE-Fin-dev500")
    parser.add_argument("--split", default="dev")
    parser.add_argument("--data-root", type=Path, default=Path("data"))
    parser.add_argument("--limit", type=int, default=5)
    parser.add_argument("--train-limit", type=int, default=32)
    parser.add_argument("--k", type=int, default=4)
    parser.add_argument(
        "--data-interface-dataset",
        action="append",
        default=list(DEFAULT_DATASETS),
        help="Dataset to include in data-interface smoke. Repeat to override/extend defaults.",
    )
    parser.add_argument("--data-repo-root", type=Path, default=DEFAULT_DATA_REPO_ROOT)
    return parser.parse_args(argv)


def run_final_smoke(
    *,
    out_root: str | Path,
    dataset: str = "DuEE-Fin-dev500",
    split: str = "dev",
    data_root: str | Path = "data",
    limit: int = 5,
    train_limit: int = 32,
    k: int = 4,
    data_interface_datasets: Sequence[str] = DEFAULT_DATASETS,
    data_repo_root: str | Path = DEFAULT_DATA_REPO_ROOT,
) -> dict[str, Any]:
    output_root = Path(out_root)
    output_root.mkdir(parents=True, exist_ok=True)
    data_root_path = Path(data_root)
    dataset_list = tuple(dict.fromkeys(data_interface_datasets))

    summary: dict[str, Any] = {
        "status": "running",
        "created_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "out_root": str(output_root),
        "dataset": dataset,
        "split": split,
        "limit": limit,
        "train_limit": train_limit,
        "k": k,
        "qwen_real_run_started": False,
        "evaluator_handoff_ran": False,
        "steps": {},
    }

    summary["steps"]["data_interface"] = run_data_interface_smoke(
        out_dir=output_root / "data_interface",
        datasets=dataset_list,
        data_root=data_root_path,
        limit=min(limit, 2),
    )
    csg_train = run_csg_smoke(
        out_dir=output_root / "csg_train_mode",
        dataset=dataset,
        split=split,
        data_root=data_root_path,
        mode="train",
        limit=limit,
    )
    summary["steps"]["csg_train_mode"] = csg_train
    summary["steps"]["csg_test_predict_mode"] = run_csg_smoke(
        out_dir=output_root / "csg_test_predict_mode",
        dataset=dataset,
        split="test",
        data_root=data_root_path,
        mode="predict",
        limit=limit,
    )
    lesp = run_lesp_train_prior_smoke(
        out_dir=output_root / "lesp_train_prior",
        dataset=dataset,
        split=split,
        data_root=data_root_path,
        limit=limit,
        train_limit=train_limit,
    )
    summary["steps"]["lesp_train_prior"] = lesp
    getm = run_getm_mock_smoke(
        out_dir=output_root / "getm_mock_candidates",
        dataset=dataset,
        split=split,
        data_root=data_root_path,
        limit=limit,
        k=k,
        surface_memory_path=Path(csg_train["surface_memory"]),
        slot_plan_path=Path(lesp["slot_plan"]),
    )
    summary["steps"]["getm_mock_candidates"] = getm
    mrs = run_mrs_selector_smoke(
        out_dir=output_root / "mrs_selector",
        dataset=dataset,
        split=split,
        data_root=data_root_path,
        limit=limit,
        candidates_dir=Path(getm["out_dir"]),
        surface_memory_path=Path(csg_train["surface_memory"]),
        slot_plan_path=Path(lesp["slot_plan"]),
    )
    summary["steps"]["mrs_selector"] = mrs
    pipeline = run_v2_pipeline_smoke(
        out_dir=output_root / "pipeline_smoke",
        dataset=dataset,
        split=split,
        data_root=data_root_path,
        limit=limit,
        k=k,
        slot_plan_path=Path(lesp["slot_plan"]),
        data_repo_root=Path(data_repo_root),
    )
    summary["steps"]["v2_pipeline_smoke"] = pipeline
    summary["steps"]["canonical_validation"] = validate_canonical_outputs(output_root)
    summary["steps"]["evaluator_handoff"] = {
        "command": pipeline["handoff_command"],
        "script_exists": pipeline["handoff_script_exists"],
        "ran": False,
    }
    summary["status"] = "ok"
    write_json(output_root / "summary.json", summary)
    return summary


def run_data_interface_smoke(
    *,
    out_dir: Path,
    datasets: Sequence[str],
    data_root: Path,
    limit: int,
) -> dict[str, Any]:
    result: dict[str, Any] = {"out_dir": str(out_dir), "datasets": {}}
    for dataset in datasets:
        schema = load_schema(dataset, data_root=data_root)
        dataset_summary: dict[str, Any] = {
            "schema_dataset": schema.schema_dataset,
            "event_type_count": len(schema.event_types),
            "unique_role_count": len(schema.unique_roles),
            "splits": {},
        }
        for split_name, mode in (("train", "train"), ("dev", "eval_internal"), ("test", "predict")):
            documents = load_documents(dataset, split_name, data_root=data_root, mode=mode, limit=limit)
            prediction_rows = [{"doc_id": document.doc_id, "events": []} for document in documents]
            canonical_path = out_dir / dataset / f"{split_name}.canonical.pred.jsonl"
            export_predictions(prediction_rows, canonical_path)
            dataset_summary["splits"][split_name] = {
                "mode": mode,
                "documents_read": len(documents),
                "gold_visible": any(document.gold is not None for document in documents),
                "canonical_prediction_path": str(canonical_path),
            }
        result["datasets"][dataset] = dataset_summary
    return result


def run_csg_smoke(
    *,
    out_dir: Path,
    dataset: str,
    split: str,
    data_root: Path,
    mode: str,
    limit: int,
) -> dict[str, Any]:
    documents = load_documents(dataset, split, data_root=data_root, mode=mode, limit=limit)
    memories = build_surface_memories(documents)
    memory_path = write_jsonl(out_dir / "surface_memory.jsonl", [surface_memory_to_dict(memory) for memory in memories])
    gold_visible = any(document.gold is not None for document in documents)
    alignments = []
    if gold_visible:
        memory_by_doc = {memory.doc_id: memory for memory in memories}
        for document in documents:
            alignments.extend(align_gold_arguments(document, memory_by_doc[document.doc_id]))
    audit = write_audit_outputs(
        out_dir,
        memories,
        alignments,
        dataset=dataset,
        split=split,
        mode=mode,
        gold_visible=gold_visible,
        allow_gold_audit=False,
    )
    return {
        "out_dir": str(out_dir),
        "surface_memory": str(memory_path),
        "audit_summary": str(out_dir / "audit_summary.json"),
        "document_count": len(documents),
        "candidate_count_total": audit["candidate_count_total"],
        "gold_visible": gold_visible,
    }


def run_lesp_train_prior_smoke(
    *,
    out_dir: Path,
    dataset: str,
    split: str,
    data_root: Path,
    limit: int,
    train_limit: int,
) -> dict[str, Any]:
    schema = load_schema(dataset, data_root=data_root)
    train_documents = load_documents(dataset, "train", data_root=data_root, mode="train", limit=train_limit)
    predict_documents = load_documents(dataset, split, data_root=data_root, mode="predict", limit=limit)
    planner = TrainPriorPlanner.fit(schema, train_documents)
    plans = planner.predict(predict_documents)
    slot_plan_path = write_jsonl(out_dir / "slot_plan.jsonl", [slot_plan_to_dict(plan) for plan in plans])
    audit = audit_slot_plans(plans, schema)
    audit_path = write_json(out_dir / "slot_plan_audit.json", audit)
    planner_summary = {
        "planner": "train_prior",
        "train_document_count": len(train_documents),
        "predict_document_count": len(predict_documents),
        "train_gold_visible": any(document.gold is not None for document in train_documents),
        "predict_gold_visible": any(document.gold is not None for document in predict_documents),
        "selected_event_type": planner.selected_event_type,
        "slot_count_total": audit["slot_count_total"],
        "invalid_plan_count": audit["invalid_plan_count"],
        "forbidden_key_violation_count": audit["forbidden_key_violation_count"],
    }
    summary_path = write_json(out_dir / "planner_summary.json", planner_summary)
    return {
        "out_dir": str(out_dir),
        "slot_plan": str(slot_plan_path),
        "slot_plan_audit": str(audit_path),
        "planner_summary": str(summary_path),
        **planner_summary,
    }


def run_getm_mock_smoke(
    *,
    out_dir: Path,
    dataset: str,
    split: str,
    data_root: Path,
    limit: int,
    k: int,
    surface_memory_path: Path,
    slot_plan_path: Path,
) -> dict[str, Any]:
    schema = load_schema(dataset, data_root=data_root)
    documents = load_documents(dataset, split, data_root=data_root, mode="predict", limit=limit)
    surface_memories = _load_surface_memory_objects(surface_memory_path)
    slot_plan_rows = {
        str(row.get("doc_id", "")): slot_plan_from_dict(row)
        for row in read_jsonl(slot_plan_path)
    }
    output = generate_getm_candidate_files(
        documents=documents,
        dataset=dataset,
        split=split,
        schema=schema,
        backend=MockGetmBackend(mode="echo_candidates"),
        k=k,
        out_dir=out_dir,
        surface_memories=surface_memories,
        slot_plans=slot_plan_rows,
    )
    diagnostics = json.loads(output.parse_diagnostics_path.read_text(encoding="utf-8"))
    return {
        "out_dir": str(out_dir),
        "backend": "mock",
        "mock_mode": "echo_candidates",
        "k": k,
        "document_count": len(documents),
        "prompts": str(output.prompts_path),
        "raw_outputs": str(output.raw_outputs_path),
        "parsed_candidates": str(output.parsed_candidates_path),
        "parse_diagnostics": str(output.parse_diagnostics_path),
        "canonical_predictions": str(output.canonical_predictions_path),
        "diagnostics": diagnostics,
        "performance_evidence": False,
    }


def run_mrs_selector_smoke(
    *,
    out_dir: Path,
    dataset: str,
    split: str,
    data_root: Path,
    limit: int,
    candidates_dir: Path,
    surface_memory_path: Path,
    slot_plan_path: Path,
) -> dict[str, Any]:
    schema = load_schema(dataset, data_root=data_root)
    documents = load_documents(dataset, split, data_root=data_root, mode="predict", limit=limit)
    candidate_rows = read_jsonl(candidates_dir / f"parsed_candidates.{split}.jsonl")
    surface_memories = {str(row.get("doc_id", "")): row for row in read_jsonl(surface_memory_path)}
    slot_plan_rows = {str(row.get("doc_id", "")): row for row in read_jsonl(slot_plan_path)}
    result = select_candidate_rows(
        candidates=candidate_rows,
        documents=documents,
        schema=schema,
        model=default_rule_based_model(),
        surface_memories=surface_memories,
        slot_plans=slot_plan_rows,
    )
    selector_scores_path = write_jsonl(out_dir / f"selector_scores.{split}.jsonl", result.score_rows)
    selected_candidates_path = write_jsonl(out_dir / f"selected_candidates.{split}.jsonl", result.selected_rows)
    canonical_path = out_dir / "predictions" / dataset / f"{split}.canonical.pred.jsonl"
    export_predictions(result.canonical_predictions, canonical_path)
    selection_summary = {
        "dataset": dataset,
        "split": split,
        "document_count": len(documents),
        "candidate_count": len(candidate_rows),
        "selected_count": len(result.selected_rows),
        "selector_gold_visible": False,
        "model_mode": "rule_based",
        "canonical_predictions": str(canonical_path),
    }
    summary_path = write_json(out_dir / "selection_summary.json", selection_summary)
    return {
        "out_dir": str(out_dir),
        "selector_scores": str(selector_scores_path),
        "selected_candidates": str(selected_candidates_path),
        "selection_summary": str(summary_path),
        **selection_summary,
    }


def run_v2_pipeline_smoke(
    *,
    out_dir: Path,
    dataset: str,
    split: str,
    data_root: Path,
    limit: int,
    k: int,
    slot_plan_path: Path,
    data_repo_root: Path,
) -> dict[str, Any]:
    result = run_v2_smoke(
        dataset=dataset,
        split=split,
        data_root=data_root,
        out_root=out_dir,
        run_id="sage_v2_final_pipeline_smoke",
        seed=13,
        k=k,
        slot_plan_path=slot_plan_path,
        data_repo_root=data_repo_root,
        limit=limit,
        command_infer=join([sys.executable, "scripts/v2/smoke_all_v2.py"]),
    )
    return {
        "out_dir": str(out_dir),
        "run_root": str(result.run_root),
        "prediction_path": str(result.prediction_path),
        "run_manifest": str(result.run_manifest_path),
        "handoff_command": result.handoff_command,
        "handoff_script_exists": result.handoff_script_exists,
    }


def validate_canonical_outputs(root: str | Path) -> dict[str, Any]:
    root_path = Path(root)
    validated_files: list[str] = []
    row_count = 0
    for path in sorted(root_path.rglob("*.canonical.pred.jsonl")):
        rows = read_jsonl(path)
        for row in rows:
            _reject_forbidden_keys(row, path)
            validate_minimal_canonical_prediction(row)
            row_count += 1
        validated_files.append(str(path))
    if not validated_files:
        raise ValueError(f"no canonical prediction files found under {root_path}")
    return {
        "validated_file_count": len(validated_files),
        "validated_row_count": row_count,
        "validated_files": validated_files,
        "forbidden_keys": sorted(FORBIDDEN_CANONICAL_KEYS),
    }


def _reject_forbidden_keys(value: Any, path: Path) -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            if key in FORBIDDEN_CANONICAL_KEYS:
                raise ValueError(f"forbidden canonical field in {path}: {key}")
            _reject_forbidden_keys(child, path)
    elif isinstance(value, list):
        for child in value:
            _reject_forbidden_keys(child, path)


def write_json(path: str | Path, payload: dict[str, Any]) -> Path:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return output_path


def _load_surface_memory_objects(path: Path) -> dict[str, SurfaceMemory]:
    memories: dict[str, SurfaceMemory] = {}
    for row in read_jsonl(path):
        candidates = []
        for candidate in row.get("candidates") or []:
            if not isinstance(candidate, dict):
                continue
            candidates.append(
                SurfaceCandidate(
                    candidate_id=str(candidate.get("candidate_id", "")),
                    doc_id=str(candidate.get("doc_id", "")),
                    surface=str(candidate.get("surface", "")),
                    context=str(candidate.get("context", "")),
                    chunk_id=str(candidate.get("chunk_id", "")),
                    source=str(candidate.get("source", "rule")),
                    char_start=_optional_int(candidate.get("char_start")),
                    char_end=_optional_int(candidate.get("char_end")),
                    event_type=_optional_str(candidate.get("event_type")),
                    role=_optional_str(candidate.get("role")),
                    role_score=_optional_float(candidate.get("role_score")),
                    metadata=dict(candidate.get("metadata") or {}),
                )
            )
        doc_id = str(row.get("doc_id", ""))
        memories[doc_id] = SurfaceMemory(
            doc_id=doc_id,
            candidates=candidates,
            source=str(row.get("source", "document_surface")),
        )
    return memories


def _optional_int(value: Any) -> int | None:
    if value is None:
        return None
    return int(value)


def _optional_float(value: Any) -> float | None:
    if value is None:
        return None
    return float(value)


def _optional_str(value: Any) -> str | None:
    if value is None:
        return None
    return str(value)


if __name__ == "__main__":
    raise SystemExit(main())
