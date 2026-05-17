from __future__ import annotations

from pathlib import Path


def _read(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


def _readme_and_agents() -> str:
    return "\n".join((_read("README.md"), _read("AGENTS.md")))


def test_readme_is_chinese_v2_paper_contract() -> None:
    text = _read("README.md")

    assert "SAGE-DEE v2" in text
    assert "role-safe and surface-memory controlled generation framework" in text
    assert "strict Chinese financial DEE" in text
    assert "docs/SAGE_V2_RESEARCH_BLUEPRINT_VFINAL_FROZEN.md" in text
    assert "`docs/SAGE_V2_RESEARCH_BLUEPRINT_VFINAL_FROZEN.md` 是唯一研究蓝图" in text
    assert "DuEE-Fin evaluator_gold dev500 view" in text
    assert "## 数据集" in text
    assert "## 方法论" in text
    assert "## 评价器与指标" in text
    assert "## 当前阶段摘要" in text
    assert "DocEEArgTableMicroF1_dev" in text
    assert "EventRecordExactF1_dev" in text
    assert "外部评价器" in text
    assert "/home/TJK/DEE/dee-eval" in text
    assert "/home/tjk/myProjects/masterProjects/DEE/data" in text
    assert "$$" in text
    assert '"RoleName": [{"text": "..."}]' in text
    assert '"arguments": {"role":' not in text
    assert '"role": [{"text": "..."}]' not in text
    assert "Phase 9 DuEE-Fin full dev main table completed" in text
    assert "Phase 10 ChFinAnn frozen-profile robustness completed" in text
    assert "Phase 11 DocFEE stress analysis completed" in text
    assert "Next phase: Phase 12 final freeze package" in text
    assert (
        "ProcNet is the direct-comparable traditional baseline and is stronger than SAGE-DEE v2 on DuEE-Fin dev"
        in text
    )
    assert "ChFinAnn absolute F1 is low" in text
    assert "official online evaluation" not in text
    assert "docs/server_runbook_4090.md" not in text


def test_agents_doc_is_project_control_contract() -> None:
    text = _read("AGENTS.md")

    assert "当前冻结主线是 SAGE-DEE v2 vFinal-frozen" in text
    assert "Execution Authority" in text
    assert "docs/SAGE_V2_RESEARCH_BLUEPRINT_VFINAL_FROZEN.md" in text
    assert "docs/refactor/SAGE_V2_EXECUTION_STATE.md" in text
    assert "可以修改的目录" in text
    assert "src/sage_dee/v2/" in text
    assert "archive/v1/" in text
    assert "/home/tjk/myProjects/masterProjects/DEE/data" in text
    assert "/home/TJK/DEE/sage-dee" in text
    assert "/data/TJK/DEE/data" in text
    assert "/home/TJK/DEE/dee-eval" in text
    assert "本地 Git 工作区是唯一代码版本源" in text
    assert "scripts/server/sync_to_4090.sh --dry-run" in text
    assert "scripts/server/fetch_results_from_4090.sh" in text
    assert "Prediction-time code must not read gold labels." in text
    assert "Current allowed operations are determined by `docs/refactor/SAGE_V2_EXECUTION_STATE.md`" in text
    assert "Phase 11 DocFEE stress analysis has completed" in text
    assert "The next allowed phase is Phase 12 final freeze package" in text
    assert "Dataset `test` split and full train remain blocked until Phase 12 final freeze manifest" in text
    assert "当前 Phase 0" not in text
    assert "Phase 1 前 blocked operations" not in text
    assert "P0 未修复并通过 Phase 1 gate 前" not in text
    assert "alias mapping、role guessing、event type guessing、gold repair、semantic repair" in text
    assert "docs/server_runbook_4090.md" not in text


def test_vfinal_frozen_docs_reject_deprecated_four_module_claims() -> None:
    text = _readme_and_agents()

    forbidden_claims = {
        "v2 主线由四个模块组成",
        "| CSG |",
        "| LESP |",
        "| MRS |",
        "CSG 是 Contextual Surface Grounder",
        "CSG is Contextual Surface Grounder",
        "LESP 是 Latent Event Slot Planner",
        "LESP is Latent Event Slot Planner",
        "MRS 是 Metric-trained Reward Selector",
        "MRS is Metric-trained Reward Selector",
        "GETM 是新 backbone",
        "GETM is a new backbone",
    }

    hits = sorted(claim for claim in forbidden_claims if claim in text)
    assert hits == []

    assert "surface memory" in text
    assert "Qwen-based event-table generator" in text
    assert "docs/SAGE_V2_RESEARCH_BLUEPRINT_VFINAL_FROZEN.md" in text


def test_execution_state_records_phase11_5_final_freeze_readiness_gate() -> None:
    text = _read("docs/refactor/SAGE_V2_EXECUTION_STATE.md")

    assert "current_phase: Phase 11 completed" in text
    assert "last_passed_phase: Phase 11 DocFEE stress analysis" in text
    assert "next_phase: Phase 12 final freeze package" in text
    assert "phase11_gate: passed" in text
    assert "allowed_next_operations:" in text
    assert "- Phase 12 final freeze package" in text
    assert "blocked_operations:" in text
    for blocked in (
        "- dataset test split",
        "- full train",
        "- post-full-dev prompt tuning",
        "- post-full-dev parser tuning",
        "- post-full-dev surface-memory tuning",
        "- evaluator modification",
    ):
        assert blocked in text
    assert "phase9_artifacts:" in text
    assert "phase10_artifacts:" in text
    assert "role_safe_schema_contract: retain" in text
    assert "surface_memory: retain_with_limitations" in text
    assert "same_backbone_sft: retain" in text
    assert "traditional_baseline: ProcNet direct-comparable, stronger than SAGE-DEE v2 on DuEE-Fin dev" in text
    assert "sota: delete" in text
    assert "long_document_sota: delete" in text
    assert "no_post_full_dev_tuning: true" in text
    assert "final_test_policy: final test once only after Phase 12 frozen manifest" in text
    assert "dataset test split remains blocked: YES" in text
    assert "full train remains blocked: YES" in text


def test_phase11_5_final_freeze_readiness_report_records_scope() -> None:
    text = _read("docs/refactor/SAGE_V2_PHASE11_5_FINAL_FREEZE_READINESS_REPAIR.md")

    assert "## Drift Found" in text
    assert "## Modified Files" in text
    assert "## Tests Run" in text
    assert "## Result" in text
    assert "## Scope Not Run" in text
    assert "## Phase 12 Gate" in text
    assert "AGENTS.md" in text
    assert "docs/refactor/SAGE_V2_EXECUTION_STATE.md" in text
    assert "tests/test_documentation_consistency.py" in text
    assert "dataset `test` split: NO" in text
    assert "train: NO" in text
    assert "full train: NO" in text
    assert "GPU/Qwen inference: NO" in text
    assert "evaluator modification: NO" in text


def test_v2_1_dev_rescue_r0_docs_exist_and_record_scope() -> None:
    plan_path = Path("docs/refactor/SAGE_V2_1_DEV_RESCUE_PLAN.md")
    changelog_path = Path("docs/refactor/SAGE_V2_1_DEV_RESCUE_CHANGELOG.md")
    report_path = Path("docs/refactor/SAGE_V2_1_R0_BRANCH_SETUP.md")

    assert plan_path.exists()
    assert changelog_path.exists()
    assert report_path.exists()

    plan = plan_path.read_text(encoding="utf-8")
    changelog = changelog_path.read_text(encoding="utf-8")
    report = report_path.read_text(encoding="utf-8")
    combined = "\n".join((plan, changelog, report))

    for required in ("dev-only", "seed42", "no test"):
        assert required in combined

    assert "R1 parser/canonical dev reparse ablation" in plan
    assert "R2 surface coverage diagnostics" in plan
    assert "R3 training-budget dev-only probe plan" in plan
    assert "R4 surface-memory candidate ablation" in plan
    assert "R5 event planning/grouping synthesis" in plan
    assert (
        "| Change ID | Phase | File | Function/Class | Purpose | Expected Effect | Risk | Test | Rollback |"
        in changelog
    )
    assert "branch: `sage-v2.1-dev-rescue-seed42`" in report
    assert "base commit: `410cb1826ca3754df74971c512b4deb346c81503`" in report
    assert "frozen final test locked: YES" in report
    assert "next phase: R1 parser/canonical dev reparse ablation" in report
    for not_run in (
        "Qwen run: NO",
        "evaluator run: NO",
        "training run: NO",
        "dev generation run: NO",
        "full dev run: NO",
        "test run: NO",
    ):
        assert not_run in report


def test_v2_1_r5_decision_docs_exist_and_record_boundaries() -> None:
    decision_path = Path("docs/refactor/SAGE_V2_1_R5_SINGLE_SEED_RESCUE_DECISION.md")
    matrix_path = Path("docs/refactor/SAGE_V2_1_NEXT_EXPERIMENT_MATRIX.md")
    execution_state_path = Path("docs/refactor/SAGE_V2_EXECUTION_STATE.md")

    assert decision_path.exists()
    assert matrix_path.exists()

    decision = decision_path.read_text(encoding="utf-8")
    matrix = matrix_path.read_text(encoding="utf-8")
    execution_state = execution_state_path.read_text(encoding="utf-8")

    for required in (
        "no test",
        "no Qwen",
        "no training",
        "no evaluator",
        "R6_seed_extension_fullmax_S4",
        "no claim SOTA",
        "no claim long-document SOTA",
    ):
        assert required in decision

    for forbidden_positive_claim in (
        "claim SOTA: YES",
        "long-document SOTA: YES",
        "achieve SOTA",
        "achieves SOTA",
    ):
        assert forbidden_positive_claim not in decision
        assert forbidden_positive_claim not in matrix

    for required in (
        "dev only",
        "seed43 and seed44",
        "no v21 surface",
        "no R4b planner",
        "no test",
        "event/role F1 `>= 0.70`",
        "exact-record mean `>= 0.30`",
        "event/role mean `< 0.65`",
        "exact-record mean `< 0.25`",
    ):
        assert required in matrix

    for required in (
        "v2_1_current_phase: R5 single-seed rescue decision completed",
        "v2_1_last_passed_phase: R5",
        "v2_1_recommended_next_phase: R6_seed_extension_fullmax_S4",
        "frozen_final_test_status: unchanged",
        "additional_test_runs: blocked",
        "dev_only_rescue: true",
    ):
        assert required in execution_state


def test_phase3_limit50_format_stability_report_records_diagnostic_only_scope() -> None:
    text = _read("docs/refactor/SAGE_V2_PHASE3_LIMIT50_FORMAT_STABILITY.md")

    assert "Phase 3 passed" in text
    assert "format-stability diagnostic only, not performance result" in text
    assert "canonical rows: `50`" in text
    assert "parse_status_counts: `{\"ok\": 16, \"parse_error\": 1, \"schema_violation\": 33}`" in text
    assert (
        "strict evaluator handoff: readable but strict coverage failed because limit=50 covers 50/500 dev docs"
        in text
    )
    assert "non-strict evaluator artifact build: PASS" in text
    for required in (
        "generation_manifest.json",
        "parse_diagnostics.dev.json",
        "raw_outputs.dev.jsonl",
        "parsed_candidates.dev.jsonl",
        "dev.canonical.pred.jsonl",
        "telemetry/timing_summary.json",
        "telemetry/gpu_memory_summary.json",
        "validation_report.json",
        "evaluator_artifacts",
    ):
        assert required in text
    for restricted in (
        "SFT: NO",
        "full dev: NO",
        "test: NO",
    ):
        assert restricted in text


def test_rules_doc_records_recurring_issues_not_stage_reports() -> None:
    text = _read("RULES.md")

    assert "recurring project pitfalls" in text
    assert "Symptom" in text
    assert "Root cause" in text
    assert "Fix" in text
    assert "Guardrail" in text
    assert "Stage reports belong in `docs/refactor/`" in text
    assert "Server Is A Run Mirror, Not A Git Remote" in text


def test_baseline_doc_is_kept_as_metric_reference() -> None:
    text = _read("docs/baseline.md")

    assert "DocEEArgTableMicroF1_dev" in text
    assert "Baseline" in text


def test_legacy_macro_docs_are_archived() -> None:
    assert not Path("docs/master_plan.md").exists()
    assert not Path("docs/server_runbook_4090.md").exists()
    assert not Path("docs/sage_v2_mainline.md").exists()
    assert not Path("docs/sage_v2_experiment_matrix.md").exists()

    assert Path("archive/v1/docs/master_plan.md").exists()
    assert Path("archive/v1/docs/server_runbook_4090.md").exists()
    assert Path("archive/v1/docs/sage_v2_mainline.md").exists()
    assert Path("archive/v1/docs/sage_v2_experiment_matrix.md").exists()


def test_legacy_configs_are_archived() -> None:
    assert Path("configs/v2").is_dir()
    assert not Path("configs/experiments").exists()
    assert not Path("configs/ladders").exists()
    assert not Path("configs/runtime").exists()
    assert not Path("configs/experiment_registry.yaml").exists()

    assert Path("archive/v1/src/configs/experiments").is_dir()
    assert Path("archive/v1/src/configs/ladders").is_dir()
    assert Path("archive/v1/src/configs/runtime").is_dir()
    assert Path("archive/v1/src/configs/experiment_registry.yaml").exists()
