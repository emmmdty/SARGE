from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from collections.abc import Sequence
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]

FROZEN_BLUEPRINT = "docs/SAGE_V2_RESEARCH_BLUEPRINT_VFINAL_FROZEN.md"
PHASE6_REPORT = "docs/refactor/SAGE_V2_PHASE6_SFT_BASELINE_MATRIX_S1_S4.md"
PHASE7_REPORT = "docs/refactor/SAGE_V2_PHASE7_SURFACE_MEMORY_ABLATION.md"
PHASE8_REPORT = "docs/refactor/SAGE_V2_PHASE8_TRADITIONAL_BASELINE_ALIGNMENT.md"
PHASE9_REPORT = "docs/refactor/SAGE_V2_PHASE9_DUEE_FIN_FULL_DEV_MAIN_TABLE.md"
PHASE10_REPORT = "docs/refactor/SAGE_V2_PHASE10_CHFINANN_FROZEN_PROFILE.md"
PHASE11_REPORT = "docs/refactor/SAGE_V2_PHASE11_DOCFEE_STRESS_ANALYSIS.md"

PHASE6_CONFIG = "configs/v2/S1-S4/sage_v2_phase6_sft_baselines.yaml"
PHASE7_CONFIG = "configs/v2/sage_v2_phase7_surface_memory_ablation.yaml"
PHASE10_CONFIG = "configs/v2/sage_v2_phase10_chfinann_frozen_profile.yaml"
PHASE11_CONFIG = "configs/v2/sage_v2_phase11_docfee_stress.yaml"

SERVER_REPO = "/home/TJK/DEE/sage-dee"
SERVER_PYTHON = "/home/TJK/.conda/envs/tjk-feg/bin/python"
SERVER_DATA_ROOT = "/data/TJK/DEE/data"
SERVER_PROCESSED_VIEW = "/data/TJK/DEE/data/processed/views/evaluator_gold"
SERVER_EVALUATOR_ROOT = "/home/TJK/DEE/dee-eval"
SERVER_RUN_ROOT = "/data/TJK/DEE/sage-dee/runs"
SERVER_PHASE6_S4_SEED42_RUN = f"{SERVER_RUN_ROOT}/phase6_S4_seed42_20260504T052553Z"
SERVER_PHASE6_S4_SEED42_ADAPTER = f"{SERVER_PHASE6_S4_SEED42_RUN}/adapter"
FINAL_TEST_OUTPUT_ROOT = "/data/TJK/DEE/sage-dee/runs/phase13_final_test_seed42_<timestamp>"

DEV_VIEWS = (
    ("DuEE-Fin-dev500", "dev"),
    ("ChFinAnn", "dev"),
    ("DocFEE-dev1000", "dev"),
)
FINAL_TEST_DATASET = "DuEE-Fin-dev500"
FINAL_TEST_SPLIT = "test"


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    execution_state_text = _read_text(args.execution_state)
    _validate_entry_state(execution_state_text)

    manifest = build_manifest(args)
    _write_json(args.out_manifest, manifest)
    args.out_report.parent.mkdir(parents=True, exist_ok=True)
    args.out_report.write_text(render_report(manifest), encoding="utf-8")
    print(f"manifest={args.out_manifest}")
    print(f"report={args.out_report}")
    print("final_test_executed=false")
    return 0


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build SAGE v2 Phase 12 final freeze manifest.")
    parser.add_argument("--execution-state", type=Path, required=True)
    parser.add_argument("--out-manifest", type=Path, required=True)
    parser.add_argument("--out-report", type=Path, required=True)
    return parser.parse_args(argv)


def build_manifest(args: argparse.Namespace) -> dict[str, Any]:
    phase6_config = _read_yaml(REPO_ROOT / PHASE6_CONFIG)
    phase7_config = _read_yaml(REPO_ROOT / PHASE7_CONFIG)
    phase11_config = _read_yaml(REPO_ROOT / PHASE11_CONFIG)
    final_command = _final_test_command()
    return {
        "manifest_version": "sage-dee-v2-final-freeze.v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "git_commit": _git(["rev-parse", "HEAD"]),
        "git_branch": _git(["branch", "--show-current"]),
        "repository": str(REPO_ROOT),
        "frozen_blueprint_path": FROZEN_BLUEPRINT,
        "execution_state_path": str(args.execution_state),
        "final_system_id": "S4",
        "final_system_description": "S4 role-safe + compressed surface memory SFT, primary seed42 checkpoint.",
        "final_system_scope": {
            "primary_dataset": FINAL_TEST_DATASET,
            "primary_split": FINAL_TEST_SPLIT,
            "phase12_scope": "freeze manifest and audit only",
            "phase12_test_split_used": False,
            "phase12_training_used": False,
            "phase12_qwen_called": False,
        },
        "final_claim_status": {
            "role_safe_schema_contract": "retain",
            "surface_memory": "retain_with_limitations",
            "same_backbone_sft": "retain",
            "traditional_baseline": "ProcNet direct-comparable, stronger than SAGE-DEE v2 on DuEE-Fin dev",
            "sota": "not_claimed",
            "long_document_sota": "not_claimed",
            "final_test_once_is_not_overfitting_proof": True,
        },
        "data_roots": {
            "server_data_root": SERVER_DATA_ROOT,
            "server_processed_view": SERVER_PROCESSED_VIEW,
            "local_data_link": "data/",
        },
        "dataset_views": _dataset_views(),
        "data_split_hashes": _data_split_hashes(),
        "schema_hashes": _schema_hashes(),
        "evaluator": _evaluator_info(),
        "prompt_template_hash": _path_hash_record(
            "src/sage_dee/v2/getm/prompt_builder.py",
            label="prompt builder source",
        ),
        "parser_config_hash": _path_hash_record(
            "src/sage_dee/v2/getm/parser.py",
            label="parser source",
        ),
        "decoding_config_hash": _inline_hash_record(
            _final_decoding_config(phase11_config),
            label="Phase 11/S4 deterministic generation config",
        ),
        "surface_memory_config_hash": _inline_hash_record(
            _final_surface_memory_config(phase7_config, phase11_config),
            label="compressed surface memory config",
        ),
        "SFT_checkpoint": _sft_checkpoint_info(phase6_config),
        "final_seed_strategy": {
            "selected_strategy": "primary_seed_42_single_final_test",
            "rationale": (
                "dev table reports seeds 42/43/44; final test uses one pre-registered primary seed "
                "to avoid seed selection"
            ),
            "forbidden_alternative_after_freeze": (
                "cannot switch to seed 42/43/44 alternatives after seeing the seed42 test result"
            ),
            "dev_reported_seed_set": [42, 43, 44],
            "primary_seed": 42,
        },
        "final_test_command": {
            "command": final_command,
            "executed": False,
            "status": (
                "TODO-safe skeleton; Phase 13 must implement minimal runner wrapper if no final-test "
                "entrypoint exists"
            ),
        },
        "final_test_executed": False,
        "audit_evidence": _audit_evidence(),
        "phase_artifacts": _phase_artifacts(),
        "final_test_policy": {
            "phase": "Phase 13 only",
            "no_post_test_modification": True,
            "no_post_test_seed_picking": True,
            "no_post_test_parser_repair": True,
            "no_post_test_prompt_tuning": True,
            "no_post_test_checkpoint_change": True,
            "no_post_test_evaluator_change": True,
            "test_allowed_only_by_manifest": True,
        },
        "phase12_scope_statement": (
            "Phase 12 generated only the final freeze manifest and audit report; no test, train, "
            "full train, Qwen inference, prompt/parser/surface/checkpoint/evaluator change, or "
            "evaluator-on-test was run."
        ),
    }


def _validate_entry_state(text: str) -> None:
    phase12_entry = (
        "last_passed_phase: Phase 11 DocFEE stress analysis" in text
        and "next_phase: Phase 12 final freeze package" in text
    )
    phase12_completed = (
        "last_passed_phase: Phase 12 final freeze package" in text
        and "next_phase: Phase 13 final test once" in text
    )
    if not (phase12_entry or phase12_completed):
        raise SystemExit(
            "Phase 12 entry state is not satisfied; expected Phase 11->12 entry "
            "or idempotent Phase 12->13 completed state"
        )
    required = (
        "no_post_full_dev_tuning: true",
        "full train remains blocked: YES",
    )
    missing = [item for item in required if item not in text]
    if missing:
        raise SystemExit(f"Phase 12 entry state is not satisfied; missing {missing}")
    if "dataset test split remains blocked: YES" not in text and (
        "dataset test split remains blocked except via final freeze manifest: YES" not in text
    ):
        raise SystemExit("Phase 12 entry state is not satisfied; test split is not blocked")


def _dataset_views() -> list[dict[str, Any]]:
    rows = [
        {
            "dataset": dataset,
            "split": split,
            "view": f"{dataset} {split}",
            "status": (
                "available locally"
                if (REPO_ROOT / "data" / dataset / f"{split}.jsonl").is_file()
                else "unavailable locally"
            ),
        }
        for dataset, split in DEV_VIEWS
    ]
    rows.append(
        {
            "dataset": FINAL_TEST_DATASET,
            "split": FINAL_TEST_SPLIT,
            "view": f"{FINAL_TEST_DATASET} {FINAL_TEST_SPLIT}",
            "status": "known final test target; not inspected in Phase 12",
        }
    )
    return rows


def _data_split_hashes() -> dict[str, Any]:
    hashes: dict[str, Any] = {}
    for dataset, split in DEV_VIEWS:
        rel = Path("data") / dataset / f"{split}.jsonl"
        hashes[f"{dataset}/{split}"] = _path_hash_record(str(rel), label=f"{dataset} {split} data")
    test_rel = Path("data") / FINAL_TEST_DATASET / f"{FINAL_TEST_SPLIT}.jsonl"
    server_test = f"{SERVER_PROCESSED_VIEW}/{FINAL_TEST_DATASET}/{FINAL_TEST_SPLIT}.jsonl"
    hashes[f"{FINAL_TEST_DATASET}/{FINAL_TEST_SPLIT}"] = {
        "status": "not_computed_phase12_test_blocked",
        "path": str(test_rel),
        "server_path": server_test,
        "command_to_compute": f"sha256sum {server_test}",
        "reason": "Phase 12 must not inspect the test split.",
    }
    return hashes


def _schema_hashes() -> dict[str, Any]:
    return {
        dataset: _path_hash_record(f"data/{dataset}/schema.json", label=f"{dataset} schema")
        for dataset, _split in DEV_VIEWS
    }


def _evaluator_info() -> dict[str, Any]:
    return {
        "root": SERVER_EVALUATOR_ROOT,
        "status": "version/hash not queried locally in Phase 12",
        "command_used_to_query_version_hash": (
            f"cd {SERVER_EVALUATOR_ROOT} && "
            "git rev-parse HEAD 2>/dev/null || "
            "find . -path ./.git -prune -o -type f -print0 | sort -z | xargs -0 sha256sum | sha256sum"
        ),
    }


def _sft_checkpoint_info(phase6_config: dict[str, Any]) -> dict[str, Any]:
    lora_config = (((phase6_config.get("getm") or {}).get("qwen") or {}).get("lora")) or {}
    return {
        "baseline_id": "S4",
        "seed": 42,
        "phase6_profile": "phase6_s4_role_safe_surface_memory",
        "phase6_seed42_run_path": SERVER_PHASE6_S4_SEED42_RUN,
        "adapter_path": SERVER_PHASE6_S4_SEED42_ADAPTER,
        "checkpoint_hash": {
            "status": "unavailable_locally",
            "command_to_compute": (
                f"find {SERVER_PHASE6_S4_SEED42_ADAPTER} -type f -print0 | "
                "sort -z | xargs -0 sha256sum | sha256sum"
            ),
        },
        "LoRA_config_hash": _inline_hash_record(lora_config, label="Phase 6 S4 LoRA config"),
        "LoRA_config": lora_config,
    }


def _audit_evidence() -> dict[str, Any]:
    return {
        "no_test_run": True,
        "no_full_train": True,
        "no_train": True,
        "no_post_full_dev_prompt_tuning": True,
        "no_post_full_dev_parser_tuning": True,
        "no_post_full_dev_surface_tuning": True,
        "no_checkpoint_modification": True,
        "no_evaluator_modification": True,
        "canonical_forbidden_key_check": {
            "path_or_command": "tests/v2/test_canonical_export.py and tests/test_sage_v2_boundaries.py",
            "status": "covered by local tests; Phase 12 did not modify canonical export",
        },
        "parser_no_semantic_repair_evidence": {
            "path_or_test": "tests/v2/test_getm_parser.py and tests/v2/test_getm_parser_format_repair.py",
            "status": "parser repair remains JSON-format only; no alias/role/event semantic repair added",
        },
        "dev_test_gold_visibility_audit": {
            "path_or_test": "tests/v2/test_getm_qwen_backend_config.py and tests/v2/test_smoke_all_v2.py",
            "status": "prediction-time gold visibility remains blocked; Phase 12 did not inspect test split",
        },
    }


def _phase_artifacts() -> dict[str, Any]:
    return {
        "phase6": {
            "report": PHASE6_REPORT,
            "aggregate_json": f"{SERVER_RUN_ROOT}/phase6_sft_baseline_matrix_aggregate.full_dev.json",
            "S4_seed42_run": SERVER_PHASE6_S4_SEED42_RUN,
        },
        "phase7": {
            "report": PHASE7_REPORT,
            "aggregate_json": f"{SERVER_RUN_ROOT}/phase7_surface_memory_ablation_aggregate.full_dev.json",
        },
        "phase8": {
            "report": PHASE8_REPORT,
            "baseline_path": (
                f"{SERVER_RUN_ROOT}/phase8_traditional_baseline_alignment/procnet_dueefin_unified_s44_dev"
            ),
        },
        "phase9": {
            "report": PHASE9_REPORT,
            "aggregate_json": f"{SERVER_RUN_ROOT}/phase9_duee_fin_main_table.json",
        },
        "phase10": {
            "report": PHASE10_REPORT,
            "aggregate_json": (
                f"{SERVER_RUN_ROOT}/phase10_chfinann_frozen_profile_20260505T044703Z/"
                "phase10_chfinann_frozen_profile_aggregate.full_dev.json"
            ),
        },
        "phase11": {
            "report": PHASE11_REPORT,
            "aggregate_json": (
                f"{SERVER_RUN_ROOT}/phase11_docfee_stress_sharded_20260506T032912Z/"
                "merged_full_dev/phase11_docfee_stress_aggregate.full_dev.json"
            ),
        },
    }


def _final_test_command() -> str:
    return (
        f"cd {SERVER_REPO} && "
        f"RUN_ROOT={FINAL_TEST_OUTPUT_ROOT} && "
        f"PATH=/home/TJK/.conda/envs/tjk-feg/bin:$PATH {SERVER_PYTHON} "
        "scripts/v2/run_phase13_final_test_once.py "
        "--config configs/v2/sage_v2_phase11_docfee_stress.yaml "
        f"--manifest docs/refactor/SAGE_V2_FINAL_FREEZE_MANIFEST.json "
        f"--dataset {FINAL_TEST_DATASET} "
        f"--split {FINAL_TEST_SPLIT} "
        "--seed 42 "
        "--profile phase11_s4_role_safe_surface_memory "
        f"--phase6-runs-root {SERVER_RUN_ROOT} "
        f"--adapter-path {SERVER_PHASE6_S4_SEED42_ADAPTER} "
        f"--evaluator-root {SERVER_EVALUATOR_ROOT} "
        "--benchmark-root /data/TJK/DEE/data/processed "
        '--out-dir "${RUN_ROOT}"'
    )


def _final_decoding_config(config: dict[str, Any]) -> dict[str, Any]:
    return (((config.get("getm") or {}).get("generation")) or {}).copy()


def _final_surface_memory_config(phase7: dict[str, Any], phase11: dict[str, Any]) -> dict[str, Any]:
    compressed = (((phase7.get("variants") or {}).get("compressed_surface") or {}).get("getm") or {}).get("prompt")
    return {
        "phase7_compressed_surface": compressed or {},
        "phase11_prompt": (((phase11.get("getm") or {}).get("prompt")) or {}),
    }


def render_report(manifest: dict[str, Any]) -> str:
    unavailable = _unavailable_hash_lines(manifest)
    phase_artifacts = "\n".join(
        (
            f"- {key}: report `{value.get('report')}`, "
            f"aggregate/baseline `{value.get('aggregate_json') or value.get('baseline_path')}`"
        )
        for key, value in manifest["phase_artifacts"].items()
    )
    hashes = _hash_summary_lines(manifest)
    command = manifest["final_test_command"]["command"]
    return f"""# SAGE v2 Phase 12 Final Freeze Package

## Scope

Phase 12 generated the final freeze manifest and audit report only. It did not
run test, train, full train, Qwen inference, or evaluator-on-test. It did not
change prompt templates, parser behavior, surface memory construction,
checkpoints, evaluator code, or seed strategy.

## Freeze Decision

- Manifest path: `docs/refactor/SAGE_V2_FINAL_FREEZE_MANIFEST.json`
- Final system: `{manifest['final_system_id']}` S4 role-safe + compressed surface memory SFT
- Primary checkpoint: Phase 6 S4 seed42 adapter `{manifest['SFT_checkpoint']['adapter_path']}`
- Frozen profile source: Phase 9/10/11 frozen profile
- This is not a SOTA claim.
- This is not a long-document SOTA claim.
- The final-test-once protocol is not an overfitting proof.

## Final Seed Strategy

The registered strategy is `primary_seed_42_single_final_test`. Dev tables
report seeds 42/43/44, but Phase 13 must use the pre-registered seed42 result
and cannot switch seeds after seeing test output.

## Final Test Command

Generated but not executed in Phase 12:

```bash
{command}
```

No dedicated final-test entrypoint exists in the current runner set. Phase 13
may implement only a minimal `run_phase13_final_test_once.py` wrapper that loads
this manifest and preserves model behavior, prompt, parser, surface memory,
checkpoint, evaluator, and seed strategy.

## Hashes Collected

{hashes}

## Unavailable Hashes

{unavailable}

## Audit Checklist

- Phase 6 SFT baseline matrix completed: YES
- Phase 7 surface memory ablation completed: YES
- Phase 8 ProcNet alignment completed: YES
- Phase 9 DuEE-Fin full dev main table completed: YES
- Phase 10 ChFinAnn frozen-profile completed: YES
- Phase 11 DocFEE stress analysis completed: YES
- no_post_full_dev_tuning: true
- test run in Phase 12: NO
- train run in Phase 12: NO
- full train run in Phase 12: NO
- prompt/parser/surface/checkpoint/evaluator tuning in Phase 12: NO
- evaluator modification in Phase 12: NO

## Phase Artifact Summary

{phase_artifacts}

## Phase 13 Gate

Phase 13 is allowed only as final test once by this manifest. After test output
exists, prompt tuning, parser repair, surface-memory tuning, checkpoint changes,
evaluator changes, and seed switching are forbidden.
"""


def _hash_summary_lines(manifest: dict[str, Any]) -> str:
    lines = []
    for key in (
        "prompt_template_hash",
        "parser_config_hash",
        "decoding_config_hash",
        "surface_memory_config_hash",
    ):
        value = manifest[key]
        lines.append(f"- {key}: {_format_hash(value)} ({value.get('label')})")
    lines.append(f"- SFT LoRA config hash: `{manifest['SFT_checkpoint']['LoRA_config_hash']['sha256']}`")
    for dataset, value in manifest["schema_hashes"].items():
        lines.append(f"- schema {dataset}: {_format_hash(value)}")
    return "\n".join(lines)


def _unavailable_hash_lines(manifest: dict[str, Any]) -> str:
    rows = [
        (
            "final test split hash",
            manifest["data_split_hashes"][f"{FINAL_TEST_DATASET}/{FINAL_TEST_SPLIT}"]["command_to_compute"],
        ),
        ("evaluator version/hash", manifest["evaluator"]["command_used_to_query_version_hash"]),
        ("checkpoint hash", manifest["SFT_checkpoint"]["checkpoint_hash"]["command_to_compute"]),
    ]
    for key, value in manifest["data_split_hashes"].items():
        if value.get("status") != "computed" and key != f"{FINAL_TEST_DATASET}/{FINAL_TEST_SPLIT}":
            rows.append((f"data split hash {key}", value["command_to_compute"]))
    for key, value in manifest["schema_hashes"].items():
        if value.get("status") != "computed":
            rows.append((f"schema hash {key}", value["command_to_compute"]))
    return "\n".join(f"- {label}: `{command}`" for label, command in rows)


def _format_hash(value: dict[str, Any]) -> str:
    if value.get("status") == "computed":
        return f"`{value.get('sha256')}`"
    return f"`{value.get('status')}`; command `{value.get('command_to_compute')}`"


def _path_hash_record(path: str, *, label: str) -> dict[str, Any]:
    rel = Path(path)
    full = REPO_ROOT / rel
    if not full.is_file():
        return {
            "label": label,
            "path": path,
            "status": "unavailable_locally",
            "command_to_compute": f"sha256sum {path}",
        }
    return {
        "label": label,
        "path": path,
        "status": "computed",
        "sha256": _sha256_file(full),
    }


def _inline_hash_record(payload: Any, *, label: str) -> dict[str, Any]:
    text = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return {
        "label": label,
        "status": "computed",
        "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
        "canonical_json": json.loads(text),
    }


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_yaml(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        payload = yaml.safe_load(handle)
    if not isinstance(payload, dict):
        raise ValueError(f"expected YAML object: {path}")
    return payload


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _git(args: list[str]) -> str:
    completed = subprocess.run(
        ["/usr/bin/git", *args],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        return f"unavailable: {completed.stderr.strip()}"
    return completed.stdout.strip()


if __name__ == "__main__":
    raise SystemExit(main())
