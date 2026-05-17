from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from collections.abc import Sequence
from datetime import datetime, timezone
from pathlib import Path
from shlex import join
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "src"))

from sage_dee.io_utils import read_yaml  # noqa: E402

FINAL_RESULT = REPO_ROOT / "docs/refactor/SAGE_V2_FINAL_TEST_RESULT.json"
R7_REPORT = REPO_ROOT / "docs/refactor/SAGE_V2_1_R7_THESIS_MINIMAL_MATRIX.md"
R7_PACKAGE = REPO_ROOT / "docs/refactor/SAGE_V2_1_THESIS_EXPERIMENT_PACKAGE.md"
PHASE8_REPORT = REPO_ROOT / "docs/refactor/SAGE_V2_PHASE8_TRADITIONAL_BASELINE_ALIGNMENT.md"
SPLIT_AUDIT = REPO_ROOT / "scripts/v2/baselines/procnet_split_audit.py"
PROCNET_EXPORT = REPO_ROOT / "scripts/v2/baselines/export_procnet_canonical.py"
SERVER_EVAL = REPO_ROOT / "scripts/server/eval_4090.sh"
ALLOWED_SEEDS = (42, 43, 44)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        config = read_yaml(args.config)
        _validate_args(args, config)
        args.out_root.mkdir(parents=True, exist_ok=True)
        discovery = discover_checkpoints(config)
        _write_json(args.out_root / "checkpoint_discovery.json", discovery)

        if args.mode == "discover_and_reuse":
            summary = run_discover_and_reuse(args=args, config=config, discovery=discovery)
            _write_json(args.out_root / "discover_and_reuse_summary.json", summary)
            print(f"discover_and_reuse_summary={args.out_root / 'discover_and_reuse_summary.json'}")
            return 0

        if args.seed is None:
            raise ValueError("export_eval_existing_checkpoint requires --seed")
        seed_summary = run_export_eval_existing_checkpoint(args=args, config=config, discovery=discovery)
        print(f"seed_summary={args.out_root / f'procnet_seed{args.seed}' / 'seed_summary.json'}")
        print(f"status={seed_summary['status']}")
        return 0
    except (RuntimeError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run SAGE v2.1 R8 ProcNet baseline comparison on dev.")
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--dataset", required=True)
    parser.add_argument("--split", default="dev")
    parser.add_argument("--out-root", type=Path, required=True)
    parser.add_argument(
        "--mode",
        choices=("discover_and_reuse", "export_eval_existing_checkpoint"),
        required=True,
    )
    parser.add_argument("--seed", type=int)
    return parser.parse_args(argv)


def run_discover_and_reuse(
    *,
    args: argparse.Namespace,
    config: dict[str, Any],
    discovery: dict[str, Any],
) -> dict[str, Any]:
    r7 = _load_r7_summary(Path(str(config["sage_r7_aggregate_json"])))
    phase8 = _load_phase8_seed44(config, dataset=args.dataset, split=args.split)
    procnet_seeds: dict[str, Any] = {}
    for seed in _configured_seeds(config):
        seed_dir = args.out_root / f"procnet_seed{seed}"
        seed_dir.mkdir(parents=True, exist_ok=True)
        if seed == 44 and phase8["validation_ok"]:
            payload = dict(phase8)
            payload.update(
                {
                    "phase": "R8 ProcNet baseline comparison",
                    "status": "direct_comparable_reused",
                    "direct_comparable": True,
                    "reference_only": False,
                    "checkpoint_discovery_status": discovery["seeds"][str(seed)]["status"],
                    "procnet_training_run": False,
                    "test_run": False,
                    "test_gold_read": False,
                    "evaluator_modified": False,
                }
            )
            _write_json(seed_dir / "seed_summary.json", payload)
            _write_json(seed_dir / "r8_run_manifest.json", _seed_manifest(payload, config=config, mode=args.mode))
        else:
            payload = _status_payload_for_discovery(seed, args=args, config=config, discovery=discovery)
            _write_json(seed_dir / "seed_summary.json", payload)
        procnet_seeds[str(seed)] = payload

    return {
        "phase": "R8 ProcNet baseline comparison",
        "mode": "discover_and_reuse",
        "dataset": args.dataset,
        "split": args.split,
        "sage_r7": {
            "source": str(config["sage_r7_aggregate_json"]),
            "recommended_next_phase": r7["verdict"]["recommended_next_phase"],
        },
        "checkpoint_discovery": discovery,
        "procnet_seeds": procnet_seeds,
        "scope": _scope(),
        "created_at": _created_at(),
    }


def run_export_eval_existing_checkpoint(
    *,
    args: argparse.Namespace,
    config: dict[str, Any],
    discovery: dict[str, Any],
) -> dict[str, Any]:
    seed = int(args.seed)
    seed_dir = args.out_root / f"procnet_seed{seed}"
    seed_dir.mkdir(parents=True, exist_ok=True)
    state = discovery["seeds"].get(str(seed))
    if state is None:
        raise ValueError(f"seed {seed} is not configured")
    if state["status"] == "missing":
        payload = _status_payload_for_discovery(seed, args=args, config=config, discovery=discovery)
        _write_json(seed_dir / "seed_summary.json", payload)
        return payload
    if state["status"] == "ambiguous":
        payload = _status_payload_for_discovery(seed, args=args, config=config, discovery=discovery)
        _write_json(seed_dir / "seed_summary.json", payload)
        raise ValueError(f"ambiguous ProcNet checkpoint for seed{seed}; export skipped")
    checkpoint = Path(state["checkpoint"])

    split_audit = _run_split_audit(args=args, config=config, seed_dir=seed_dir)
    if not split_audit.get("direct_comparable_split"):
        raise ValueError(f"split audit failed before canonical export for seed{seed}")

    export_summary = _run_procnet_export(args=args, config=config, seed_dir=seed_dir, checkpoint=checkpoint)
    evaluator_artifacts = _run_sibling_evaluator(args=args, config=config, seed_dir=seed_dir)
    metrics = _load_evaluator_metrics(evaluator_artifacts, dataset=args.dataset, split=args.split)
    payload = {
        "phase": "R8 ProcNet baseline comparison",
        "baseline": "ProcNet",
        "seed": seed,
        "dataset": args.dataset,
        "split": args.split,
        "status": "direct_comparable_evaluated",
        "direct_comparable": True,
        "reference_only": False,
        "checkpoint": str(checkpoint),
        "checkpoint_discovery_status": state["status"],
        "checkpoint_candidates": state["candidates"],
        "strict_f1": metrics["strict_f1"],
        "strict_precision": metrics["strict_precision"],
        "strict_recall": metrics["strict_recall"],
        "exact_record_f1": metrics["exact_record_f1"],
        "soft_record_f1_0_8": metrics.get("soft_record_f1_0_8"),
        "validation_ok": metrics["validation_ok"],
        "canonical_rows": export_summary.get("canonical_rows"),
        "canonical_event_count": export_summary.get("canonical_event_count"),
        "split_audit_path": str(seed_dir / "split_audit.json"),
        "export_summary_path": str(seed_dir / "phase8_procnet_export_summary.json"),
        "evaluator_artifact_root": str(evaluator_artifacts),
        "procnet_training_run": False,
        "test_run": False,
        "test_gold_read": False,
        "evaluator_modified": False,
        "procnet_original_modified": False,
    }
    _write_json(seed_dir / "seed_summary.json", payload)
    _write_json(seed_dir / "r8_run_manifest.json", _seed_manifest(payload, config=config, mode=args.mode))
    return payload


def discover_checkpoints(config: dict[str, Any]) -> dict[str, Any]:
    seeds = _configured_seeds(config)
    roots = [Path(str(path)) for path in config.get("procnet_checkpoint_search_roots") or []]
    result: dict[str, Any] = {"roots": [str(root) for root in roots], "seeds": {}}
    for seed in seeds:
        candidates = _checkpoint_candidates(seed, roots)
        if not candidates:
            status = "missing"
            checkpoint = None
        elif len(candidates) == 1:
            status = "available"
            checkpoint = candidates[0]
        else:
            status = "ambiguous"
            checkpoint = None
        result["seeds"][str(seed)] = {
            "seed": seed,
            "status": status,
            "checkpoint": checkpoint,
            "candidates": candidates,
        }
    return result


def _checkpoint_candidates(seed: int, roots: list[Path]) -> list[str]:
    candidates: set[str] = set()
    for root in roots:
        exact = root / f"procnet_dueefin_unified_s{seed}" / "best.pt"
        if exact.is_file():
            candidates.add(str(exact))
        if not root.exists():
            continue
        for path in root.rglob("best.pt"):
            text = str(path).lower()
            if "dueefin" not in text or "unified" not in text:
                continue
            if any(marker in text for marker in (f"seed{seed}", f"s{seed}", f"_{seed}", f"-{seed}")):
                candidates.add(str(path))
    return sorted(candidates)


def _validate_args(args: argparse.Namespace, config: dict[str, Any]) -> None:
    if args.split == "test":
        raise ValueError("R8 rejects test split")
    if args.split != "dev":
        raise ValueError(f"R8 only permits dev split, got {args.split!r}")
    if args.dataset != "DuEE-Fin-dev500":
        raise ValueError("R8 is restricted to DuEE-Fin-dev500")
    if args.seed is not None and args.seed not in ALLOWED_SEEDS:
        raise ValueError("R8 only permits ProcNet seeds 42/43/44")
    _validate_config(config)
    _require_entry_documents()
    _load_r7_summary(Path(str(config["sage_r7_aggregate_json"])))
    _load_phase8_seed44(config, dataset=args.dataset, split=args.split)
    _require_final_result_clean()


def _validate_config(config: dict[str, Any]) -> None:
    required = {
        "phase": "R8",
        "dataset": "DuEE-Fin-dev500",
        "split": "dev",
        "test_enabled": False,
        "no_procnet_training": True,
        "no_test": True,
        "no_sota_claim": True,
    }
    for key, expected in required.items():
        if config.get(key) != expected:
            raise ValueError(f"R8 config must set {key}={expected!r}")
    if _configured_seeds(config) != list(ALLOWED_SEEDS):
        raise ValueError("R8 config must check ProcNet seeds 42/43/44")
    for key in (
        "sage_r7_aggregate_json",
        "procnet_existing_seed44_root",
        "procnet_checkpoint_search_roots",
        "procnet_python",
        "sage_python",
        "evaluator_root",
        "data_root",
    ):
        if key not in config:
            raise ValueError(f"R8 config missing {key}")


def _require_entry_documents() -> None:
    for path in (R7_REPORT, R7_PACKAGE, PHASE8_REPORT, SPLIT_AUDIT, PROCNET_EXPORT, SERVER_EVAL):
        if not path.exists():
            raise ValueError(f"missing R8 entry file: {path}")
    r7_text = R7_REPORT.read_text(encoding="utf-8")
    if "recommended_next_phase: `R8_procnet_and_thesis_tables`" not in r7_text:
        raise ValueError("R7 report does not recommend R8_procnet_and_thesis_tables")
    phase8_text = PHASE8_REPORT.read_text(encoding="utf-8")
    if "ProcNet" not in phase8_text or "direct-comparable" not in phase8_text:
        raise ValueError("Phase 8 ProcNet baseline alignment report is not direct-comparable")


def _load_r7_summary(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise ValueError(f"missing R7 aggregate JSON: {path}")
    payload = _read_json(path)
    verdict = payload.get("verdict") or {}
    if verdict.get("recommended_next_phase") != "R8_procnet_and_thesis_tables":
        raise ValueError("R7 aggregate does not recommend R8_procnet_and_thesis_tables")
    if (payload.get("scope") or {}).get("test_run") or (payload.get("scope") or {}).get("test_gold_read"):
        raise ValueError("R7 aggregate violates dev-only scope")
    for system in ("S2", "S3", "S4"):
        stats = (payload.get("system_stats") or {}).get(system)
        if not stats:
            raise ValueError(f"R7 aggregate missing {system} stats")
    return payload


def _load_phase8_seed44(config: dict[str, Any], *, dataset: str, split: str) -> dict[str, Any]:
    root = Path(str(config["procnet_existing_seed44_root"]))
    if not root.is_dir():
        raise ValueError(f"missing Phase 8 ProcNet seed44 root: {root}")
    export_summary = _read_json(root / "phase8_procnet_export_summary.json")
    run_manifest = _read_json(root / "run_manifest.json")
    split_audit = _read_json(root / "split_audit.json")
    if export_summary.get("dataset") != dataset or export_summary.get("split") != split:
        raise ValueError("Phase 8 ProcNet seed44 is not on the requested dataset/split")
    if export_summary.get("seed") != 44 or export_summary.get("test_used"):
        raise ValueError("Phase 8 ProcNet seed44 violates R8 scope")
    if split_audit.get("direct_comparable_split") is not True:
        raise ValueError("Phase 8 ProcNet seed44 split is not direct-comparable")
    metrics = _load_evaluator_metrics(
        _phase8_evaluator_root(config, dataset=dataset, split=split),
        dataset=dataset,
        split=split,
    )
    if not metrics["validation_ok"]:
        raise ValueError("Phase 8 ProcNet seed44 evaluator validation is not ok")
    return {
        "baseline": "ProcNet",
        "seed": 44,
        "dataset": dataset,
        "split": split,
        "phase8_root": str(root),
        "checkpoint": export_summary.get("checkpoint") or run_manifest.get("procnet_checkpoint"),
        "canonical_rows": export_summary.get("canonical_rows"),
        "canonical_event_count": export_summary.get("canonical_event_count"),
        "strict_f1": metrics["strict_f1"],
        "strict_precision": metrics["strict_precision"],
        "strict_recall": metrics["strict_recall"],
        "exact_record_f1": metrics["exact_record_f1"],
        "soft_record_f1_0_8": metrics.get("soft_record_f1_0_8"),
        "validation_ok": metrics["validation_ok"],
        "evaluator_artifact_root": str(_phase8_evaluator_root(config, dataset=dataset, split=split)),
    }


def _phase8_evaluator_root(config: dict[str, Any], *, dataset: str, split: str) -> Path:
    configured = config.get("procnet_existing_seed44_evaluator_artifact_root")
    if configured:
        return Path(str(configured))
    return (
        Path("/data/TJK/DEE/sage-dee/evaluator_artifacts/phase8_traditional_baseline_alignment")
        / "procnet_dueefin_unified_s44_dev/procnet_dueefin_unified_s44_dev/analysis"
        / dataset
        / split
    )


def _run_split_audit(*, args: argparse.Namespace, config: dict[str, Any], seed_dir: Path) -> dict[str, Any]:
    out_json = seed_dir / "split_audit.json"
    data_root = Path(str(config["data_root"]))
    command = [
        sys.executable,
        str(SPLIT_AUDIT),
        "--dataset",
        args.dataset,
        "--split",
        args.split,
        "--procnet-view",
        str(data_root / "processed" / "procnet" / f"{args.dataset}_ProcNet_Doc2EDAG" / f"{args.split}.json"),
        "--evaluator-view",
        str(data_root / "processed" / "views" / "evaluator_gold" / args.dataset / f"{args.split}.jsonl"),
        "--out-json",
        str(out_json),
    ]
    completed = subprocess.run(command, cwd=REPO_ROOT, capture_output=True, text=True, check=False)
    if completed.returncode != 0:
        _write_json(
            seed_dir / "split_audit_failure.json",
            {
                "command": join(command),
                "returncode": completed.returncode,
                "stdout": completed.stdout,
                "stderr": completed.stderr,
            },
        )
        raise ValueError(f"split audit failed before canonical export for seed{args.seed}")
    return _read_json(out_json)


def _run_procnet_export(
    *,
    args: argparse.Namespace,
    config: dict[str, Any],
    seed_dir: Path,
    checkpoint: Path,
) -> dict[str, Any]:
    phase8_manifest = _read_json(Path(str(config["procnet_existing_seed44_root"])) / "run_manifest.json")
    procnet_workdir = _existing_path(config.get("procnet_workdir"), phase8_manifest.get("procnet_workdir"))
    procnet_export_script = _existing_path(
        config.get("procnet_export_script"),
        phase8_manifest.get("procnet_export_script"),
    )
    if procnet_workdir is None:
        raise ValueError("missing ProcNet workdir; original implementation will not be modified")
    if procnet_export_script is None:
        raise ValueError("missing ProcNet export script; original implementation will not be modified")
    run_id = f"v21_r8_procnet_seed{args.seed}_dev"
    command = [
        sys.executable,
        str(PROCNET_EXPORT),
        "--dataset",
        args.dataset,
        "--split",
        args.split,
        "--seed",
        str(args.seed),
        "--run-id",
        run_id,
        "--run-dir",
        str(seed_dir),
        "--procnet-workdir",
        str(procnet_workdir),
        "--procnet-export-script",
        str(procnet_export_script),
        "--checkpoint",
        str(checkpoint),
        "--data-root",
        str(Path(str(config["data_root"])) / "processed" / "views" / "evaluator_gold"),
        "--python",
        str(config["procnet_python"]),
        "--device",
        "cuda",
        "--notes",
        "R8 existing ProcNet checkpoint dev export; no ProcNet training; test blocked.",
    ]
    completed = subprocess.run(command, cwd=REPO_ROOT, capture_output=True, text=True, check=False)
    _write_json(
        seed_dir / "procnet_export_command.json",
        {
            "command": join(command),
            "returncode": completed.returncode,
            "stdout": completed.stdout,
            "stderr": completed.stderr,
        },
    )
    if completed.returncode != 0:
        raise ValueError(f"ProcNet canonical export failed for seed{args.seed}")
    return _read_json(seed_dir / "phase8_procnet_export_summary.json")


def _run_sibling_evaluator(*, args: argparse.Namespace, config: dict[str, Any], seed_dir: Path) -> Path:
    out_dir = seed_dir / "evaluator_artifacts"
    env = dict(os.environ)
    env["EVALUATOR_ROOT"] = str(config["evaluator_root"])
    env["BENCHMARK_ROOT"] = str(Path(str(config["data_root"])) / "processed")
    command = ["bash", str(SERVER_EVAL), str(seed_dir), args.dataset, args.split, str(out_dir)]
    completed = subprocess.run(command, cwd=REPO_ROOT, env=env, capture_output=True, text=True, check=False)
    _write_json(
        seed_dir / "evaluator_command.json",
        {
            "command": join(command),
            "returncode": completed.returncode,
            "stdout": completed.stdout,
            "stderr": completed.stderr,
        },
    )
    if completed.returncode != 0:
        raise ValueError(f"sibling dee-eval failed for seed{args.seed}")
    return out_dir


def _load_evaluator_metrics(root: Path, *, dataset: str, split: str) -> dict[str, Any]:
    analysis_root = _analysis_root(root, dataset=dataset, split=split)
    overall = _read_json(analysis_root / "overall_metrics.json")
    record = _read_json(analysis_root / "record_level_metrics.json")
    validation = _read_json(analysis_root / "validation_report.json")
    return {
        "strict_f1": _required_float(overall, "f1", analysis_root / "overall_metrics.json"),
        "strict_precision": _required_float(overall, "precision", analysis_root / "overall_metrics.json"),
        "strict_recall": _required_float(overall, "recall", analysis_root / "overall_metrics.json"),
        "exact_record_f1": _required_float(record, "record_f1_exact", analysis_root / "record_level_metrics.json"),
        "soft_record_f1_0_8": record.get("record_f1_soft_0_8"),
        "validation_ok": validation.get("ok") is True,
        "validation_counts": validation.get("counts") or {},
        "analysis_root": str(analysis_root),
        "uses_naen": overall.get("uses_naen"),
        "uses_offset": overall.get("uses_offset"),
    }


def _analysis_root(root: Path, *, dataset: str, split: str) -> Path:
    candidates = [
        root,
        root / "analysis" / dataset / split,
        root / root.name / "analysis" / dataset / split,
    ]
    candidates.extend(root.glob(f"*/analysis/{dataset}/{split}"))
    for candidate in candidates:
        if (candidate / "overall_metrics.json").is_file():
            return candidate
    raise ValueError(f"missing evaluator metrics under {root}")


def _status_payload_for_discovery(
    seed: int,
    *,
    args: argparse.Namespace,
    config: dict[str, Any],
    discovery: dict[str, Any],
) -> dict[str, Any]:
    state = discovery["seeds"][str(seed)]
    if state["status"] == "missing":
        status = "missing_not_rerun"
    elif state["status"] == "ambiguous":
        status = "ambiguous_checkpoint_skipped"
    else:
        status = "available_pending_export"
    return {
        "phase": "R8 ProcNet baseline comparison",
        "baseline": "ProcNet",
        "seed": seed,
        "dataset": args.dataset,
        "split": args.split,
        "status": status,
        "direct_comparable": False,
        "reference_only": False,
        "checkpoint": state.get("checkpoint"),
        "checkpoint_candidates": state.get("candidates") or [],
        "checkpoint_discovery_status": state["status"],
        "strict_f1": None,
        "exact_record_f1": None,
        "validation_ok": False,
        "procnet_training_run": False,
        "test_run": False,
        "test_gold_read": False,
        "evaluator_modified": False,
        "procnet_original_modified": False,
        "no_procnet_training": bool(config.get("no_procnet_training")),
    }


def _seed_manifest(payload: dict[str, Any], *, config: dict[str, Any], mode: str) -> dict[str, Any]:
    return {
        "phase": "R8 ProcNet baseline comparison",
        "mode": mode,
        "baseline": "ProcNet",
        "seed": payload["seed"],
        "dataset": payload["dataset"],
        "split": payload["split"],
        "status": payload["status"],
        "checkpoint": payload.get("checkpoint"),
        "evaluator_root": config["evaluator_root"],
        "data_root": config["data_root"],
        "procnet_training_run": False,
        "test_run": False,
        "test_gold_read": False,
        "evaluator_modified": False,
        "procnet_original_modified": False,
        "created_at": _created_at(),
    }


def _scope() -> dict[str, bool]:
    return {
        "dev_only": True,
        "no_test": True,
        "test_run": False,
        "test_gold_read": False,
        "no_procnet_training": True,
        "procnet_training_run": False,
        "sage_training_run": False,
        "s4_retrained": False,
        "evaluator_modified": False,
        "procnet_original_modified": False,
        "frozen_final_modified": False,
        "sota_claim": False,
    }


def _configured_seeds(config: dict[str, Any]) -> list[int]:
    return [int(seed) for seed in config.get("procnet_seeds_to_check") or []]


def _existing_path(primary: object, fallback: object) -> Path | None:
    for value in (primary, fallback):
        if not value:
            continue
        path = Path(str(value))
        if path.exists():
            return path
    return None


def _require_final_result_clean() -> None:
    if not FINAL_RESULT.exists():
        raise ValueError(f"missing frozen final result file: {FINAL_RESULT}")
    completed = subprocess.run(
        ["git", "diff", "--quiet", "--", str(FINAL_RESULT.relative_to(REPO_ROOT))],
        cwd=REPO_ROOT,
        check=False,
    )
    if completed.returncode != 0:
        raise ValueError("frozen final result JSON has local modifications")


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise ValueError(f"missing JSON file: {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return payload


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _required_float(payload: dict[str, Any], key: str, path: Path) -> float:
    value = payload.get(key)
    if not isinstance(value, (int, float)):
        raise ValueError(f"{path} missing numeric {key}")
    return float(value)


def _created_at() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


if __name__ == "__main__":
    raise SystemExit(main())
