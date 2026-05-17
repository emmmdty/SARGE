from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
REPORT = REPO_ROOT / "docs" / "refactor" / "SAGE_V2_PHASE2_DEV20_PROFILE_FREEZE.md"


def test_phase2_profile_freeze_report_records_required_gate_evidence() -> None:
    text = REPORT.read_text(encoding="utf-8")

    assert "Phase 2 passed" in text
    assert "dev20 debugging gate, not a performance result" in text
    for required in (
        "parse_status_counts",
        "no_complete_json_object_count",
        "copied_prompt_marker_count",
        "schema_violation",
        "unknown_role",
        "unknown_event_type",
        "generation_manifest.json",
        "parse_diagnostics.dev.json",
        "raw_outputs.dev.jsonl",
        "parsed_candidates.dev.jsonl",
        "dev.canonical.pred.jsonl",
        "telemetry/timing_summary.json",
        "telemetry/gpu_memory_summary.json",
        "ablation comparison table",
        "git diff",
    ):
        assert required in text

    for restricted in (
        "limit=50: NO",
        "SFT: NO",
        "full dev: NO",
        "test: NO",
    ):
        assert restricted in text


def test_phase2_report_allows_only_phase3_limit50_after_phase2_pass() -> None:
    text = REPORT.read_text(encoding="utf-8")

    assert "Phase 3 `limit=50` is allowed next under the frozen profile and explicit guard flag" in text
    assert "SFT, full\ndev, and test remain blocked" in text
    assert "dev20 remains a debugging gate, not a performance result" in text
