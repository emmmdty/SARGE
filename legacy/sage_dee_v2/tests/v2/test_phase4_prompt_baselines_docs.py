from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
REPORT = REPO_ROOT / "docs" / "refactor" / "SAGE_V2_PHASE4_PROMPT_BASELINES_P1_P4.md"
STATE = REPO_ROOT / "docs" / "refactor" / "SAGE_V2_EXECUTION_STATE.md"


def test_phase4_report_records_prompt_baseline_gate_evidence() -> None:
    text = REPORT.read_text(encoding="utf-8")

    assert "Phase 4 passed" in text
    assert "prompt baseline pilot only, not main-table performance" in text
    assert "phase4_prompt_baselines_20260503T160836Z" in text
    for required in (
        "P1",
        "P2",
        "P3",
        "P4",
        "summary.json",
        "summary.csv",
        "doc_subset.json",
        "subset_benchmark",
        "generation_manifest.json",
        "parse_diagnostics.dev.json",
        "raw_outputs.dev.jsonl",
        "parsed_candidates.dev.jsonl",
        "dev.canonical.pred.jsonl",
        "telemetry/timing_summary.json",
        "telemetry/gpu_memory_summary.json",
        "validation_ok=true",
        "unknown_role",
        "event-table / role micro-F1",
        "exact-record F1",
    ):
        assert required in text
    for restricted in (
        "SFT: NO",
        "full dev: NO",
        "test: NO",
        "full train: NO",
    ):
        assert restricted in text


def test_execution_state_records_phase5_2_gate_and_keeps_test_blocked() -> None:
    text = STATE.read_text(encoding="utf-8")

    assert "current_phase: Phase 4 completed" in text
    assert "last_passed_phase: Phase 5.2 small SFT smoke" in text
    assert "small_sft_smoke: allowed" in text
    assert "phase4_prompt_baselines: completed" in text
    assert "phase5_2_long_prompt_packing_retry: completed" in text
    assert "next_phase: Phase 6 SFT baseline matrix" in text
    assert "full dev/test/full train remain forbidden: YES" in text
    assert "P1-P4 canonical rows = 50: YES" in text
    assert "role-safe reduced unknown-role count vs schema-only: YES" in text
    assert "limit=50 zero parse-error stability: YES" in text
    assert "execution state allows Phase 6 SFT baseline matrix: YES" in text
    assert "test remains blocked: YES" in text
