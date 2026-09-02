from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "paper/ccks_2026/poster/tools/award_poster_contract.py"
SPEC = importlib.util.spec_from_file_location("award_poster_contract", CONTRACT_PATH)
assert SPEC is not None and SPEC.loader is not None
contract = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(contract)


def test_v4_output_paths_match_current_artifacts() -> None:
    poster_dir = ROOT / "paper/ccks_2026/poster"

    assert contract.V4_PPTX == poster_dir / "SARGE_CCKS2026_poster_en_award_v4.pptx"
    assert contract.V4_PDF == poster_dir / "SARGE_CCKS2026_poster_en_award_v4.pdf"
    assert contract.V4_PNG == poster_dir / "SARGE_CCKS2026_poster_en_award_v4.png"
    assert contract.V4_REPORT == poster_dir / "poster_revision_report.md"


def test_v5_output_paths_are_new_and_versioned() -> None:
    poster_dir = ROOT / "paper/ccks_2026/poster"

    assert contract.V5_PPTX == poster_dir / "SARGE_CCKS2026_poster_en_award_v5.pptx"
    assert contract.V5_PDF == poster_dir / "SARGE_CCKS2026_poster_en_award_v5.pdf"
    assert contract.V5_PNG == poster_dir / "SARGE_CCKS2026_poster_en_award_v5.png"
    assert contract.V5_REPORT == poster_dir / "poster_award_v5_analysis.md"
    assert contract.V5_PPTX != contract.V3_PPTX
    assert contract.V5_PDF != contract.V3_PDF
    assert contract.V5_PNG != contract.V3_PNG
    assert contract.V5_REPORT != contract.ANALYSIS_REPORT
    assert contract.V5_PPTX != contract.V4_PPTX
    assert contract.V5_PDF != contract.V4_PDF
    assert contract.V5_PNG != contract.V4_PNG
    assert contract.V5_REPORT != contract.V4_REPORT


def test_v5_keeps_the_official_page_size() -> None:
    assert contract.PAGE_CM == (88.90, 109.22)
    assert contract.PAGE_PT == (2520, 3096)


def test_v5_type_scale_sets_readable_minimums() -> None:
    assert contract.V5_TITLE_PT == 74
    assert contract.V5_AUTHORS_PT == 32
    assert contract.V5_AFFILIATIONS_PT == 22
    assert contract.V5_BODY_MIN_PT == 22
    assert contract.V5_CHART_CAPTION_MIN_PT == 20
    assert contract.V5_QUALIFIER_MIN_PT == 18


def test_v5_vertical_narrative_reserves_space_for_gaps() -> None:
    assert contract.V5_VERTICAL_NARRATIVE_RATIOS == {
        "takehome": 0.05,
        "motivation": 0.20,
        "method": 0.36,
        "results": 0.28,
        "conclusion": 0.08,
    }
    assert sum(contract.V5_VERTICAL_NARRATIVE_RATIOS.values()) <= 0.97


def test_v5_takehome_is_exact() -> None:
    assert contract.V5_TAKEHOME == (
        "Correct values can still form wrong rows. SARGE's schema-grounded contract "
        "improves ChFinAnn multi-event F1 by 5.1 over EPAL; ExactRec (strict event-row "
        "match) reveals what role F1 misses."
    )


def test_v5_motivation_has_three_reasons_gap_and_contribution() -> None:
    assert contract.V5_MOTIVATION == {
        "reasons": (
            (
                "Financial document-level event extraction assembles fixed-schema records "
                "from long announcements."
            ),
            (
                "Multiple same-type events share public arguments while private values "
                "distinguish their rows."
            ),
            (
                "Role-value F1 can remain high when pledgee, amount, and dates are "
                "cross-bound between rows."
            ),
        ),
        "research_gap": (
            "Prior pipelines recover roles but do not directly learn a schema-valid "
            "complete-row prediction object."
        ),
        "contribution": (
            "SARGE learns a schema-grounded event-table contract and evaluates both "
            "role recovery and exact row assembly."
        ),
    }


def test_v5_contributions_cover_prediction_contract_and_diagnostic() -> None:
    assert contract.V5_CONTRIBUTIONS == (
        (
            "Prediction object",
            (
                "Predict one complete fixed-slot row instead of assembling roles after "
                "extraction."
            ),
        ),
        (
            "Output contract",
            (
                "Use licensed types, roles, and source values as one output contract."
            ),
        ),
        (
            "Row-level diagnostic",
            (
                "Report ExactRec and Δrecord (= F1 − ExactRec) to expose exact-row "
                "errors hidden by role F1."
            ),
        ),
    )


def test_v5_overall_f1_chart_data_is_exact() -> None:
    assert contract.V5_OVERALL_F1_DATA == (
        {
            "method": "Doc2EDAG",
            "reference": "[18]",
            "chfinann": 78.8,
            "duee_fin": 63.4,
        },
        {
            "method": "ReDEE-RAAT",
            "reference": "[10]",
            "chfinann": 81.9,
            "duee_fin": 74.4,
        },
        {
            "method": "ProCNet",
            "reference": "[13]",
            "chfinann": 80.8,
            "duee_fin": 75.1,
        },
        {
            "method": "EPAL",
            "reference": "[7]",
            "chfinann": 83.4,
            "duee_fin": 76.4,
        },
        {
            "method": "SEELE",
            "reference": "[15]",
            "chfinann": 85.1,
            "duee_fin": 80.8,
        },
        {
            "method": "SARGE",
            "reference": None,
            "chfinann": 85.6,
            "duee_fin": 78.3,
            "std": {"chfinann": 0.4, "duee_fin": 0.4},
        },
    )


def test_v5_overall_f1_rows_have_unique_methods_and_exact_schemas() -> None:
    rows = contract.V5_OVERALL_F1_DATA

    assert len({row["method"] for row in rows}) == len(rows)
    for row in rows:
        expected_keys = {"method", "reference", "chfinann", "duee_fin"}
        if row["method"] == "SARGE":
            expected_keys.add("std")
            assert set(row["std"]) == {"chfinann", "duee_fin"}
        assert set(row) == expected_keys


def test_v5_multi_event_chart_data_is_exact_and_scoped_to_sarge() -> None:
    assert contract.V5_MULTI_EVENT_DATA == {
        "dataset": "ChFinAnn",
        "aggregation": "mean",
        "seeds": (13, 17, 42),
        "scope_method": "SARGE",
        "rows": (
            {"method": "EPAL", "f1_s": 89.7, "f1_m": 76.6, "gap": 13.1},
            {"method": "SARGE", "f1_s": 89.2, "f1_m": 81.7, "gap": 7.5},
        ),
    }


def test_v5_multi_event_rows_have_unique_methods_schema_and_calculated_gaps() -> None:
    data = contract.V5_MULTI_EVENT_DATA

    assert data["dataset"] == "ChFinAnn"
    assert data["aggregation"] == "mean"
    assert data["seeds"] == (13, 17, 42)
    assert data["scope_method"] == "SARGE"
    assert len({row["method"] for row in data["rows"]}) == len(data["rows"])
    for row in data["rows"]:
        assert set(row) == {"method", "f1_s", "f1_m", "gap"}
        assert round(row["f1_s"] - row["f1_m"], 1) == row["gap"]


def test_v5_alignment_diagnostics_are_same_backend_seed_13_rows() -> None:
    assert contract.V5_ALIGNMENT_DIAGNOSTICS == (
        {
            "dataset": "ChFinAnn",
            "no_sft": 24.8,
            "sft": 85.5,
            "backend": "vLLM-BF16",
            "seed": 13,
        },
        {
            "dataset": "DuEE-Fin",
            "no_sft": 3.3,
            "sft": 78.0,
            "backend": "HF-4bit",
            "seed": 13,
        },
    )


def test_v5_alignment_diagnostics_have_unique_datasets_and_exact_schema() -> None:
    rows = contract.V5_ALIGNMENT_DIAGNOSTICS

    assert len({row["dataset"] for row in rows}) == len(rows)
    for row in rows:
        assert set(row) == {"dataset", "no_sft", "sft", "backend", "seed"}
        assert row["seed"] == 13


def test_v5_record_diagnostics_are_three_seed_means() -> None:
    assert contract.V5_RECORD_DIAGNOSTICS == (
        {
            "dataset": "ChFinAnn",
            "f1": 85.6,
            "exact_rec": 56.1,
            "delta": 29.5,
            "aggregation": "mean",
            "seeds": (13, 17, 42),
        },
        {
            "dataset": "DuEE-Fin",
            "f1": 78.3,
            "exact_rec": 43.3,
            "delta": 35.1,
            "aggregation": "mean",
            "seeds": (13, 17, 42),
        },
    )


def test_v5_record_diagnostics_have_unique_datasets_schema_and_calculated_gaps() -> None:
    rows = contract.V5_RECORD_DIAGNOSTICS

    assert len({row["dataset"] for row in rows}) == len(rows)
    for row in rows:
        assert set(row) == {
            "dataset",
            "f1",
            "exact_rec",
            "delta",
            "aggregation",
            "seeds",
        }
        assert row["aggregation"] == "mean"
        assert row["seeds"] == (13, 17, 42)
        # Displayed aggregate means are independently rounded, while Δrecord is
        # averaged from seed-level gaps; a 0.1 display discrepancy is expected.
        assert abs((row["f1"] - row["exact_rec"]) - row["delta"]) <= 0.11
        if row["dataset"] == "ChFinAnn":
            assert round(row["f1"] - row["exact_rec"], 1) == row["delta"]


def test_v5_ambiguous_combined_diagnostics_are_removed() -> None:
    assert not hasattr(contract, "V5_DIAGNOSTICS")


def test_v5_conclusion_has_three_explicit_messages() -> None:
    assert contract.V5_CONCLUSION_MESSAGES == (
        (
            "Schema-grounded event-table generation improves multi-event robustness by "
            "predicting complete event rows."
        ),
        "ExactRec exposes row-assembly failures that role F1 can hide.",
        "Schema validity is necessary, but SARGE does not solve exact record binding.",
    )


def test_v5_required_tokens_and_forbidden_overclaims_are_explicit() -> None:
    assert contract.V5_REQUIRED_TOKENS == (
        "Correct values can still form wrong rows.",
        "Doc2EDAG [18]",
        "ReDEE-RAAT [10]",
        "ProCNet [13]",
        "EPAL [7]",
        "SEELE [15]",
        "85.6 ± 0.4",
        "78.3 ± 0.4",
        "89.7",
        "76.6",
        "13.1",
        "89.2",
        "81.7",
        "7.5",
        "24.8 → 85.5",
        "3.3 → 78.0",
        "vLLM-BF16",
        "HF-4bit",
        "seed 13",
        "ExactRec 56.1",
        "ExactRec 43.3",
        "Δrecord 29.5",
        "Δrecord 35.1",
        "does not solve exact record binding",
        contract.DISPLAY_URL,
        contract.CONTACT_EMAIL,
    )
    assert contract.V5_FORBIDDEN_CLAIMS == (
        "state-of-the-art",
        "sota",
        "outperforms seele on duee-fin",
        "outperforms all baselines on both datasets",
        "solves record binding",
        "eliminates record-binding errors",
        "exactrec isolates binding errors",
    )
