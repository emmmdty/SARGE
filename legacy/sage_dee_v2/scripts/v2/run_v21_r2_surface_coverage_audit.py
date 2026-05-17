from __future__ import annotations

import argparse
import json
import math
import statistics
import sys
from collections.abc import Sequence
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "src"))

from sage_dee.io_utils import read_yaml  # noqa: E402
from sage_dee.v2.csg.surface_memory import build_surface_memory  # noqa: E402
from sage_dee.v2.csg.weak_alignment import align_gold_arguments  # noqa: E402
from sage_dee.v2.data_interface.dataset_loader import V2DatasetDocument, load_documents  # noqa: E402
from sage_dee.v2.getm.candidate_generator_v21 import build_v21_surface_memory, rule_inventory  # noqa: E402


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        config = read_yaml(args.config)
        summary = run_coverage_audit(args=args, config=config)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    args.out_dir.mkdir(parents=True, exist_ok=True)
    summary_path = args.out_dir / "coverage_summary.json"
    markdown_path = args.out_dir / "coverage_summary.md"
    inventory_path = args.out_dir / "rule_inventory.json"
    manifest_path = args.out_dir / "run_manifest.json"

    _write_json(summary_path, summary)
    markdown_path.write_text(render_markdown(summary), encoding="utf-8")
    _write_json(inventory_path, {"rules": rule_inventory()})
    _write_json(manifest_path, _run_manifest(args=args, config=config, summary=summary))

    print(f"coverage_summary={summary_path}")
    print(f"coverage_markdown={markdown_path}")
    print(f"rule_inventory={inventory_path}")
    print(f"run_manifest={manifest_path}")
    return 0


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="SAGE v2.1 R2 surface coverage-only audit.")
    parser.add_argument("--dataset", required=True)
    parser.add_argument("--split", required=True)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    return parser.parse_args(argv)


def run_coverage_audit(*, args: argparse.Namespace, config: dict[str, Any]) -> dict[str, Any]:
    _validate_args(args, config)
    data_root = Path((config.get("data") or {}).get("data_root") or "data")
    predict_docs = {
        document.doc_id: document
        for document in load_documents(
            args.dataset,
            args.split,
            data_root=data_root,
            mode="predict",
        )
    }
    gold_docs = {
        document.doc_id: document
        for document in load_documents(
            args.dataset,
            args.split,
            data_root=data_root,
            mode="train",
        )
    }

    ordered_doc_ids = [doc_id for doc_id in predict_docs if doc_id in gold_docs]
    baseline_memories = {doc_id: build_surface_memory(predict_docs[doc_id].input) for doc_id in ordered_doc_ids}
    v21_memories = {
        doc_id: build_v21_surface_memory(predict_docs[doc_id].input, enable_v21_rules=True)
        for doc_id in ordered_doc_ids
    }

    baseline_alignments = {
        doc_id: align_gold_arguments(gold_docs[doc_id], memory)
        for doc_id, memory in baseline_memories.items()
    }
    v21_alignments = {
        doc_id: align_gold_arguments(gold_docs[doc_id], memory)
        for doc_id, memory in v21_memories.items()
    }

    role_rows, event_rows = _coverage_tables(baseline_alignments, v21_alignments)
    baseline_metrics = _aggregate_metrics(
        documents=[predict_docs[doc_id] for doc_id in ordered_doc_ids],
        memories=baseline_memories,
        alignments=baseline_alignments,
        prompt_budget_chars_per_token=_prompt_chars_per_token(config),
        prompt_budget_tokens=_prompt_budget_tokens(config),
    )
    v21_metrics = _aggregate_metrics(
        documents=[predict_docs[doc_id] for doc_id in ordered_doc_ids],
        memories=v21_memories,
        alignments=v21_alignments,
        prompt_budget_chars_per_token=_prompt_chars_per_token(config),
        prompt_budget_tokens=_prompt_budget_tokens(config),
    )

    role_improvements = sorted(
        (
            {
                "role": row["role"],
                "delta": row["v21_candidate_coverage"] - row["baseline_candidate_coverage"],
                "baseline_candidate_coverage": row["baseline_candidate_coverage"],
                "v21_candidate_coverage": row["v21_candidate_coverage"],
                "gold_argument_count": row["gold_argument_count"],
            }
            for row in role_rows
        ),
        key=lambda item: (-item["delta"], -item["gold_argument_count"], item["role"]),
    )
    still_zero_roles = [row for row in role_rows if row["v21_candidate_coverage"] == 0.0]

    prompt_budget_p90_tokens = v21_metrics["prompt_budget_estimate"]["estimated_tokens_p90"]
    prompt_budget_tokens = _prompt_budget_tokens(config)
    prompt_budget_ratio = prompt_budget_p90_tokens / max(prompt_budget_tokens, 1)
    decision = _decision(v21_metrics["candidate_coverage_overall"], prompt_budget_ratio, config)

    rc0_baseline = float((config.get("coverage") or {}).get("rc0_baseline_candidate_coverage", 0.227233))
    summary = {
        "phase": "R2 surface coverage first",
        "dataset": args.dataset,
        "split": args.split,
        "data_root": str(data_root),
        "document_count": len(ordered_doc_ids),
        "gold_argument_count": baseline_metrics["gold_argument_count"],
        "candidate_count": v21_metrics["candidate_count"],
        "baseline": baseline_metrics,
        "v21": v21_metrics,
        "comparison_against_rc0_baseline": {
            "rc0_candidate_coverage": rc0_baseline,
            "v21_candidate_coverage_delta": v21_metrics["candidate_coverage_overall"] - rc0_baseline,
        },
        "role_level_coverage": role_rows,
        "event_type_level_coverage": event_rows,
        "top_improved_roles": role_improvements[:10],
        "still_zero_roles": still_zero_roles,
        "false_positive_proxy": {
            "candidates_per_doc_mean": v21_metrics["candidates_per_doc"]["mean"],
            "candidates_per_doc_p50": v21_metrics["candidates_per_doc"]["p50"],
            "candidates_per_doc_p90": v21_metrics["candidates_per_doc"]["p90"],
            "candidates_per_doc_max": v21_metrics["candidates_per_doc"]["max"],
            "duplicate_candidate_rate": v21_metrics["duplicate_candidate_rate"],
        },
        "prompt_budget_estimate": {
            "chars_per_token": _prompt_chars_per_token(config),
            "budget_tokens": prompt_budget_tokens,
            "estimated_tokens_mean": v21_metrics["prompt_budget_estimate"]["estimated_tokens_mean"],
            "estimated_tokens_p50": v21_metrics["prompt_budget_estimate"]["estimated_tokens_p50"],
            "estimated_tokens_p90": v21_metrics["prompt_budget_estimate"]["estimated_tokens_p90"],
            "estimated_tokens_max": v21_metrics["prompt_budget_estimate"]["estimated_tokens_max"],
            "p90_budget_ratio": prompt_budget_ratio,
        },
        "decision": decision,
        "rule_inventory": rule_inventory(),
    }
    return summary


def render_markdown(summary: dict[str, Any]) -> str:
    baseline = summary["baseline"]
    v21 = summary["v21"]
    lines = [
        "# R2 Surface Coverage-First Rescue",
        "",
        "## Scope",
        "",
        "- Dev-only DuEE-Fin-dev500/dev coverage audit.",
        "- No Qwen, no training, no evaluator, no test split.",
        "",
        "## Overall",
        "",
        "| Metric | Baseline | V21 |",
        "| --- | ---: | ---: |",
        f"| Documents | {baseline['document_count']} | {v21['document_count']} |",
        f"| Gold arguments | {baseline['gold_argument_count']} | {v21['gold_argument_count']} |",
        f"| Candidate count | {baseline['candidate_count']} | {v21['candidate_count']} |",
        (
            f"| Candidate coverage | {baseline['candidate_coverage_overall']:.6f} | "
            f"{v21['candidate_coverage_overall']:.6f} |"
        ),
        f"| Content coverage | {baseline['content_coverage_overall']:.6f} | {v21['content_coverage_overall']:.6f} |",
        f"| Duplicate rate | {baseline['duplicate_candidate_rate']:.6f} | {v21['duplicate_candidate_rate']:.6f} |",
        "",
        "## Role-Level Coverage",
        "",
        "| Role | Gold | Baseline cov | V21 cov | Delta |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    for row in summary["role_level_coverage"]:
        lines.append(
            f"| {row['role']} | {row['gold_argument_count']} | {row['baseline_candidate_coverage']:.6f} | "
            f"{row['v21_candidate_coverage']:.6f} | {row['delta']:.6f} |"
        )
    lines.extend(
        [
            "",
            "## Event-Type Coverage",
            "",
            "| Event type | Gold | Baseline cov | V21 cov | Delta |",
            "| --- | ---: | ---: | ---: | ---: |",
        ]
    )
    for row in summary["event_type_level_coverage"]:
        lines.append(
            f"| {row['event_type']} | {row['gold_argument_count']} | {row['baseline_candidate_coverage']:.6f} | "
            f"{row['v21_candidate_coverage']:.6f} | {row['delta']:.6f} |"
        )
    lines.extend(
        [
            "",
            "## Decision",
            "",
            f"- {summary['decision']['label']}",
            "",
            "## Prompt Budget",
            "",
            f"- p90 estimated tokens: {summary['prompt_budget_estimate']['estimated_tokens_p90']:.2f}",
            f"- p90 budget ratio: {summary['prompt_budget_estimate']['p90_budget_ratio']:.6f}",
            "",
            "## Still-Zero Roles",
            "",
            "| Role | Gold | V21 cov |",
            "| --- | ---: | ---: |",
        ]
    )
    for row in summary["still_zero_roles"]:
        lines.append(f"| {row['role']} | {row['gold_argument_count']} | {row['v21_candidate_coverage']:.6f} |")
    lines.append("")
    return "\n".join(lines)


def _validate_args(args: argparse.Namespace, config: dict[str, Any]) -> None:
    if args.dataset != "DuEE-Fin-dev500":
        raise ValueError("R2 coverage audit is restricted to DuEE-Fin-dev500")
    if args.split != "dev":
        raise ValueError("R2 coverage audit is dev split only")
    if _path_mentions_test(args.out_dir) or _path_mentions_test(args.config):
        raise ValueError("R2 coverage audit rejects test paths")
    if not (config.get("surface_memory") or {}).get("v21_opt_in", False):
        raise ValueError("R2 coverage audit requires explicit v21_opt_in: true")
    _reject_forbidden_config_sections(config)


def _reject_forbidden_config_sections(config: dict[str, Any]) -> None:
    forbidden = ("qwen", "generation", "evaluator", "train", "training")
    found: list[str] = []

    def visit(value: Any, path: str = "") -> None:
        if isinstance(value, dict):
            for key, child in value.items():
                key_name = str(key).lower()
                if key_name in forbidden:
                    found.append(f"{path}.{key}" if path else str(key))
                visit(child, f"{path}.{key}" if path else str(key))
        elif isinstance(value, list):
            for index, child in enumerate(value):
                visit(child, f"{path}[{index}]")

    visit(config)
    if found:
        raise ValueError(f"R2 coverage audit rejects forbidden config sections: {sorted(found)}")


def _coverage_tables(
    baseline_alignments: dict[str, list[Any]],
    v21_alignments: dict[str, list[Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    role_records: dict[str, dict[str, Any]] = {}
    event_records: dict[str, dict[str, Any]] = {}

    for _doc_id, alignments in baseline_alignments.items():
        for record in alignments:
            role_bucket = role_records.setdefault(
                record.role,
                {
                    "role": record.role,
                    "gold_argument_count": 0,
                    "baseline_candidate_located": 0,
                    "v21_candidate_located": 0,
                    "content_located": 0,
                },
            )
            event_bucket = event_records.setdefault(
                record.event_type,
                {
                    "event_type": record.event_type,
                    "gold_argument_count": 0,
                    "baseline_candidate_located": 0,
                    "v21_candidate_located": 0,
                    "content_located": 0,
                },
            )
            role_bucket["gold_argument_count"] += 1
            event_bucket["gold_argument_count"] += 1
            if record.candidate_match_count > 0:
                role_bucket["baseline_candidate_located"] += 1
                event_bucket["baseline_candidate_located"] += 1
            if record.content_match_count > 0:
                role_bucket["content_located"] += 1
                event_bucket["content_located"] += 1

    for _doc_id, alignments in v21_alignments.items():
        for record in alignments:
            role_bucket = role_records.setdefault(
                record.role,
                {
                    "role": record.role,
                    "gold_argument_count": 0,
                    "baseline_candidate_located": 0,
                    "v21_candidate_located": 0,
                    "content_located": 0,
                },
            )
            event_bucket = event_records.setdefault(
                record.event_type,
                {
                    "event_type": record.event_type,
                    "gold_argument_count": 0,
                    "baseline_candidate_located": 0,
                    "v21_candidate_located": 0,
                    "content_located": 0,
                },
            )
            if record.candidate_match_count > 0:
                role_bucket["v21_candidate_located"] += 1
                event_bucket["v21_candidate_located"] += 1

    role_rows = [
        {
            "role": role,
            "gold_argument_count": row["gold_argument_count"],
            "baseline_candidate_located": row["baseline_candidate_located"],
            "baseline_candidate_coverage": _rate(row["baseline_candidate_located"], row["gold_argument_count"]),
            "v21_candidate_located": row["v21_candidate_located"],
            "v21_candidate_coverage": _rate(row["v21_candidate_located"], row["gold_argument_count"]),
            "content_located": row["content_located"],
            "content_candidate_coverage": _rate(row["content_located"], row["gold_argument_count"]),
            "delta": _rate(row["v21_candidate_located"], row["gold_argument_count"])
            - _rate(row["baseline_candidate_located"], row["gold_argument_count"]),
        }
        for role, row in sorted(role_records.items())
    ]
    event_rows = [
        {
            "event_type": event_type,
            "gold_argument_count": row["gold_argument_count"],
            "baseline_candidate_located": row["baseline_candidate_located"],
            "baseline_candidate_coverage": _rate(row["baseline_candidate_located"], row["gold_argument_count"]),
            "v21_candidate_located": row["v21_candidate_located"],
            "v21_candidate_coverage": _rate(row["v21_candidate_located"], row["gold_argument_count"]),
            "content_located": row["content_located"],
            "content_candidate_coverage": _rate(row["content_located"], row["gold_argument_count"]),
            "delta": _rate(row["v21_candidate_located"], row["gold_argument_count"])
            - _rate(row["baseline_candidate_located"], row["gold_argument_count"]),
        }
        for event_type, row in sorted(event_records.items())
    ]
    return role_rows, event_rows


def _aggregate_metrics(
    *,
    documents: list[V2DatasetDocument],
    memories: dict[str, Any],
    alignments: dict[str, list[Any]],
    prompt_budget_chars_per_token: float,
    prompt_budget_tokens: int,
) -> dict[str, Any]:
    candidate_counts = [len(memory.candidates) for memory in memories.values()]
    duplicate_counts = [
        len(memory.candidates)
        - len(
            {
                (candidate.char_start, candidate.char_end, candidate.surface)
                for candidate in memory.candidates
            }
        )
        for memory in memories.values()
    ]
    selected_candidates = [candidate.surface for memory in memories.values() for candidate in memory.candidates]
    gold_arguments = [record for records in alignments.values() for record in records]
    candidate_located = [record for record in gold_arguments if record.candidate_match_count > 0]
    content_located = [record for record in gold_arguments if record.content_match_count > 0]
    prompt_estimates = [
        _estimate_prompt_tokens(memory.candidates, prompt_budget_chars_per_token) for memory in memories.values()
    ]
    candidate_count_total = sum(candidate_counts)
    duplicate_candidate_total = sum(duplicate_counts)
    return {
        "document_count": len(documents),
        "gold_argument_count": len(gold_arguments),
        "candidate_count": candidate_count_total,
        "candidate_count_per_doc": candidate_counts,
        "candidate_count_stats": _stats(candidate_counts),
        "duplicate_candidate_count": duplicate_candidate_total,
        "duplicate_candidate_rate": _rate(duplicate_candidate_total, candidate_count_total),
        "candidate_located_gold_arguments": len(candidate_located),
        "candidate_coverage_overall": _rate(len(candidate_located), len(gold_arguments)),
        "content_located_gold_arguments": len(content_located),
        "content_coverage_overall": _rate(len(content_located), len(gold_arguments)),
        "prompt_budget_estimate": {
            "estimated_tokens_mean": statistics.fmean(prompt_estimates) if prompt_estimates else 0.0,
            "estimated_tokens_p50": _percentile(prompt_estimates, 50),
            "estimated_tokens_p90": _percentile(prompt_estimates, 90),
            "estimated_tokens_max": max(prompt_estimates) if prompt_estimates else 0.0,
            "prompt_budget_tokens": prompt_budget_tokens,
        },
        "candidates_per_doc": {
            "mean": statistics.fmean(candidate_counts) if candidate_counts else 0.0,
            "p50": _percentile(candidate_counts, 50),
            "p90": _percentile(candidate_counts, 90),
            "max": max(candidate_counts) if candidate_counts else 0,
        },
        "content_match_count_total": len(content_located),
        "candidate_match_count_total": len(candidate_located),
        "prompt_candidate_surfaces": selected_candidates,
    }


def _estimate_prompt_tokens(candidates: list[Any], chars_per_token: float) -> float:
    chars = sum(len(f"[c{i}] {candidate.surface}") for i, candidate in enumerate(candidates))
    return chars / max(chars_per_token, 1.0)


def _stats(values: list[int]) -> dict[str, float]:
    return {
        "mean": statistics.fmean(values) if values else 0.0,
        "p50": _percentile(values, 50),
        "p90": _percentile(values, 90),
        "max": max(values) if values else 0,
    }


def _percentile(values: list[int | float], percentile: int) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = max(0, min(len(ordered) - 1, math.ceil(percentile / 100 * len(ordered)) - 1))
    return float(ordered[index])


def _rate(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        return 0.0
    return numerator / denominator


def _decision(candidate_coverage: float, prompt_budget_ratio: float, config: dict[str, Any]) -> dict[str, Any]:
    coverage_cfg = config.get("coverage") or {}
    promising_threshold = float(coverage_cfg.get("promising_min_candidate_coverage", 0.45))
    insufficient_threshold = float(coverage_cfg.get("insufficient_max_candidate_coverage", 0.35))
    budget_threshold = float(coverage_cfg.get("prompt_budget_p90_token_ratio_threshold", 0.5))
    if candidate_coverage >= promising_threshold:
        if prompt_budget_ratio > budget_threshold:
            label = "coverage_explodes_prompt_budget"
        else:
            label = "engineering_coverage_rescue_promising"
    elif candidate_coverage < insufficient_threshold:
        label = "coverage_not_enough"
    else:
        label = "coverage_not_enough"
    return {
        "label": label,
        "candidate_coverage": candidate_coverage,
        "prompt_budget_ratio": prompt_budget_ratio,
        "promising_threshold": promising_threshold,
        "insufficient_threshold": insufficient_threshold,
        "budget_threshold": budget_threshold,
    }


def _prompt_chars_per_token(config: dict[str, Any]) -> float:
    coverage = config.get("coverage") or {}
    return float(coverage.get("prompt_budget_chars_per_token", 2.0))


def _prompt_budget_tokens(config: dict[str, Any]) -> int:
    coverage = config.get("coverage") or {}
    return int(coverage.get("prompt_budget_tokens", 4096))


def _path_mentions_test(path: Path) -> bool:
    for part in path.parts:
        lowered = part.lower()
        if lowered == "test" or "-test" in lowered or ".test" in lowered or "test." in lowered:
            return True
    return False


def _run_manifest(*, args: argparse.Namespace, config: dict[str, Any], summary: dict[str, Any]) -> dict[str, Any]:
    return {
        "run_id": f"v21_r2_surface_coverage_{_created_slug()}",
        "phase": "R2 surface coverage first",
        "dataset": args.dataset,
        "split": args.split,
        "config_path": str(args.config),
        "out_dir": str(args.out_dir),
        "data_root": str((config.get("data") or {}).get("data_root") or "data"),
        "dev_only": True,
        "qwen_run": False,
        "train_run": False,
        "evaluator_run": False,
        "test_run": False,
        "test_gold_read": False,
        "candidate_coverage_overall": summary["v21"]["candidate_coverage_overall"],
        "decision": summary["decision"]["label"],
        "created_at": _created_at(),
        "command": " ".join([sys.executable, *sys.argv]),
    }


def _created_at() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _created_slug() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
