from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
MANIFEST = REPO_ROOT / "docs/refactor/SAGE_V2_FINAL_FREEZE_MANIFEST.json"
REPORT = REPO_ROOT / "docs/refactor/SAGE_V2_PHASE12_FINAL_FREEZE_PACKAGE.md"
STATE = REPO_ROOT / "docs/refactor/SAGE_V2_EXECUTION_STATE.md"
AGENTS = REPO_ROOT / "AGENTS.md"
README = REPO_ROOT / "README.md"
BUILDER = REPO_ROOT / "scripts/v2/build_phase12_final_freeze_manifest.py"


def _manifest() -> dict:
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def test_phase12_manifest_exists_and_freezes_primary_seed42() -> None:
    assert BUILDER.is_file()
    assert MANIFEST.is_file()
    assert REPORT.is_file()

    manifest = _manifest()
    strategy = manifest["final_seed_strategy"]
    policy = manifest["final_test_policy"]

    assert strategy["selected_strategy"] == "primary_seed_42_single_final_test"
    assert strategy["forbidden_alternative_after_freeze"]
    assert manifest["final_test_command"]["command"]
    assert manifest["final_test_command"]["executed"] is False
    assert manifest["final_test_executed"] is False
    assert policy["phase"] == "Phase 13 only"
    assert policy["no_post_test_modification"] is True
    assert policy["no_post_test_seed_picking"] is True
    assert policy["no_post_test_parser_repair"] is True
    assert policy["no_post_test_prompt_tuning"] is True
    assert policy["no_post_test_checkpoint_change"] is True


def test_phase12_manifest_records_evaluator_and_phase_artifacts() -> None:
    manifest = _manifest()

    assert manifest["evaluator"]["root"] == "/home/TJK/DEE/dee-eval"
    phase_artifacts = manifest["phase_artifacts"]
    for phase_key in ("phase9", "phase10", "phase11"):
        assert phase_key in phase_artifacts
        assert phase_artifacts[phase_key]["report"].startswith("docs/refactor/SAGE_V2_PHASE")
        assert phase_artifacts[phase_key]["aggregate_json"]

    audit = manifest["audit_evidence"]
    assert audit["no_test_run"] is True
    assert audit["no_full_train"] is True
    assert audit["no_post_full_dev_prompt_tuning"] is True
    assert audit["no_post_full_dev_parser_tuning"] is True
    assert audit["no_post_full_dev_surface_tuning"] is True
    assert audit["no_evaluator_modification"] is True
    assert audit["canonical_forbidden_key_check"]["path_or_command"]
    assert audit["parser_no_semantic_repair_evidence"]["path_or_test"]
    assert audit["dev_test_gold_visibility_audit"]["path_or_test"]


def test_phase12_manifest_contains_no_sota_claims() -> None:
    manifest = _manifest()
    text = REPORT.read_text(encoding="utf-8")

    assert manifest["final_claim_status"]["sota"] == "not_claimed"
    assert manifest["final_claim_status"]["long_document_sota"] == "not_claimed"
    assert "claimed SOTA" not in text
    assert "claimed long-document SOTA" not in text
    assert "not a SOTA claim" in text
    assert "not a long-document SOTA claim" in text


def test_phase12_execution_state_advances_only_to_final_test_once() -> None:
    text = STATE.read_text(encoding="utf-8")

    assert "current_phase: Phase 12 final freeze package completed" in text
    assert "last_passed_phase: Phase 12 final freeze package" in text
    assert "next_phase: Phase 13 final test once" in text
    assert "final_freeze_manifest: docs/refactor/SAGE_V2_FINAL_FREEZE_MANIFEST.json" in text
    assert "final_test_seed_strategy: primary_seed_42_single_final_test" in text
    assert "test_allowed_only_by_manifest: true" in text
    assert "dataset test split remains blocked except via final freeze manifest: YES" in text
    assert "full train remains blocked: YES" in text
    assert "post_test_modification: forbidden" in text
    assert "post_test_seed_switching: forbidden" in text


def test_phase12_docs_keep_governance_examples_clean() -> None:
    agents = AGENTS.read_text(encoding="utf-8")
    readme = README.read_text(encoding="utf-8")

    assert "当前 Phase 0" not in agents
    assert "Phase 1 前 blocked operations" not in agents
    assert "P0 未修复并通过 Phase 1 gate 前" not in agents
    assert '"RoleName": [{"text": "..."}]' in readme
    assert '"arguments": {"role":' not in readme
    assert '"role": [{"text": "..."}]' not in readme
