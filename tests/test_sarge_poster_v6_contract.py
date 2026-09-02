from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
POSTER_DIR = ROOT / "paper/ccks_2026/poster"
CONTRACT_PATH = POSTER_DIR / "tools/award_poster_contract.py"
README_PATH = POSTER_DIR / "README.md"


def _load_contract():
    spec = importlib.util.spec_from_file_location("award_poster_contract_v6", CONTRACT_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def contract():
    return _load_contract()


def test_v6_output_paths_are_isolated_from_sources(contract) -> None:
    assert contract.V6_OUTPUT_DIR == POSTER_DIR / "final_v6"
    assert contract.V6_PPTX == contract.V6_OUTPUT_DIR / "SARGE_CCKS2026_poster_en_award_v6.pptx"
    assert contract.V6_PDF == contract.V6_OUTPUT_DIR / "SARGE_CCKS2026_poster_en_award_v6.pdf"
    assert contract.V6_PNG == contract.V6_OUTPUT_DIR / "SARGE_CCKS2026_poster_en_award_v6.png"
    assert contract.V6_PPTX not in {
        contract.V2_PPTX,
        contract.V3_PPTX,
        contract.V4_PPTX,
        contract.V5_PPTX,
    }


def test_v6_takehome_is_exact_and_has_emphasis_targets(contract) -> None:
    assert contract.V6_TAKEHOME == (
        "Correct argument values can still form the wrong event rows. "
        "On ChFinAnn, SARGE gains 5.1 Multi-Event F1 points over EPAL; "
        "ExactRec reveals complete-row failures beyond role F1."
    )
    assert contract.V6_TAKEHOME_EMPHASIS == (
        "wrong event rows",
        "5.1 Multi-Event F1 points",
        "ExactRec",
    )


def test_v6_motivation_is_concise_and_paper_backed(contract) -> None:
    assert contract.V6_MOTIVATION_STAGES == (
        "Source evidence",
        "Recovered role values (unordered)",
        "Event-row assembly",
    )
    assert contract.V6_MOTIVATION_CONSEQUENCE == (
        "Every displayed value is correct, yet the wrong assembly describes two "
        "pledge records absent from the source evidence."
    )
    assert contract.V6_MOTIVATION_ANCHORS == (
        (
            "Assembly risk",
            "Post-hoc assignment can cross-bind correct values across same-type records.",
        ),
        (
            "Evaluation blind spot",
            "Role F1 rewards role–value recovery without requiring an exact event row.",
        ),
        (
            "Financial consequence",
            "A counterparty or end date can be attributed to the wrong pledge record.",
        ),
    )
    assert contract.V6_MECHANISMS == (
        (
            "Cross-row recombination",
            "Complete-row generation makes one event row the prediction unit.",
        ),
        (
            "Schema-invalid output",
            "Schema-defined types, roles, and slots define valid structure.",
        ),
        (
            "Source-unanchored values",
            "Bounded candidates and copy instructions encourage source-faithful values.",
        ),
    )


def test_v6_equity_pledge_example_matches_the_paper(contract) -> None:
    assert contract.V6_EQUITY_PLEDGE_ROWS == (
        ("15M", "CITIC", "2024-05-20", "2025-05-19"),
        ("8M", "Guotai Junan", "2024-06-05", "2025-06-04"),
    )
    assert contract.V6_EQUITY_PLEDGE_WRONG_ROWS == (
        ("15M", "Guotai Junan", "2024-05-20", "2025-06-04"),
        ("8M", "CITIC", "2024-06-05", "2025-05-19"),
    )


def test_v6_method_copy_distinguishes_prompt_target_decode_and_validation(contract) -> None:
    assert contract.V6_METHOD_FLOW == (
        "Prompt contract",
        "Answer-only SFT target",
        "Standard greedy decoding",
        "Post-validation + fixed-slot table",
    )
    assert contract.V6_METHOD_CORE_CHANGE == (
        "Core change: supervise the serialized gold event table so each output row "
        "represents one event record."
    )
    assert contract.V6_GROUNDING_NOTE == (
        "Schema and source cues enter the prompt contract; row structure is learned "
        "from answer-only table targets; schema checking occurs after standard decoding."
    )
    assert contract.V6_VALIDATION_NOTE == (
        "Checks schema-defined types/roles, removes empty fields, and normalizes slot order."
    )
    assert contract.V6_IMPLEMENTATION == (
        "Qwen3-4B · LoRA SFT · 3 seeds"
    )
    assert contract.V6_METHOD_INPUT_FORMULA.name == "v6_method_input.png"
    assert contract.V6_SFT_LOSS_FORMULA.name == "v6_sft_loss.png"
    assert contract.V6_DELTA_FORMULA.name == "v6_delta_record.png"


def test_v6_results_match_accepted_paper(contract) -> None:
    assert contract.V6_OVERALL_F1 == (
        {"model": "Doc2EDAG", "citation": "[18]", "chfinann": 78.8, "duee_fin": 63.4},
        {"model": "GIT", "citation": "[14]", "chfinann": 80.3, "duee_fin": 67.8},
        {"model": "ProCNet", "citation": "[13]", "chfinann": 80.8, "duee_fin": 75.1},
        {"model": "EPAL", "citation": "[7]", "chfinann": 83.4, "duee_fin": 76.4},
        {"model": "SEELE", "citation": "[15]", "chfinann": 85.1, "duee_fin": 80.8},
        {
            "model": "SARGE",
            "citation": "",
            "chfinann": 85.6,
            "duee_fin": 78.3,
            "std": {"chfinann": 0.4, "duee_fin": 0.4},
        },
    )
    rows = {row["model"]: row for row in contract.V6_MULTI_EVENT}
    assert rows["EPAL"] == {"model": "EPAL", "single": 89.7, "multi": 76.6, "gap": 13.1}
    assert rows["SARGE"] == {
        "model": "SARGE",
        "single": 89.2,
        "multi": 81.7,
        "gap": 7.5,
        "std": {"single": 0.7, "multi": 0.1},
    }
    assert rows["SARGE"]["multi"] - rows["EPAL"]["multi"] == pytest.approx(5.1)
    assert rows["EPAL"]["gap"] - rows["SARGE"]["gap"] == pytest.approx(5.6)
    assert contract.V6_MULTI_EVENT_DEFINITION == (
        "Multi-event documents contain more than one non-empty gold event record."
    )
    assert contract.V6_EVIDENCE_SCOPE == (
        "+5.1 establishes general multi-event robustness; EPAL ExactRec is unavailable, "
        "so it does not isolate binding-error reduction."
    )


def test_v6_exactrec_copy_is_precise_and_honest(contract) -> None:
    assert contract.V6_RECORD_DIAGNOSTICS == (
        {"dataset": "ChFinAnn", "role_f1": 85.6, "exact_rec": 56.1, "gap": 29.5},
        {"dataset": "DuEE-Fin", "role_f1": 78.3, "exact_rec": 43.3, "gap": 35.1},
    )
    assert contract.V6_EXACTREC_DEFINITION == (
        "ExactRec tests whether each complete event row matches exactly."
    )
    assert contract.V6_ROLE_F1_QUESTION == "Are the role–value pairs recovered?"
    assert contract.V6_EXACTREC_QUESTION == "Is the complete event row exact?"
    assert contract.V6_EXACTREC_CAVEAT == (
        "The F1–ExactRec gap includes missing, extra, incorrect, and misbound "
        "arguments; it is not a pure binding-error estimate."
    )
    assert contract.V6_DIAGNOSTIC_COLUMN == "F1 − ExactRec"
    assert contract.V6_DUEE_GAP_NOTE == (
        "† Mean of per-seed gaps; displayed component means are rounded."
    )


def test_v6_conclusion_uses_gain_diagnostic_and_remaining_limitation(contract) -> None:
    assert tuple(label for label, _ in contract.V6_CONCLUSION) == (
        "Gain",
        "Diagnostic",
        "Remaining limitation",
    )
    all_text = " ".join(text for _, text in contract.V6_CONCLUSION)
    assert "ExactRec reaches 56.1 on ChFinAnn and 43.3 on DuEE-Fin" in all_text
    assert "Prediction-unit insight" in all_text
    assert "closed-schema Chinese financial DEE" in all_text
    assert "open-schema behavior is not evaluated" in all_text
    assert "does not solve exact record binding" not in all_text.casefold()


def test_v6_layout_and_typography_lock_the_poster_scale(contract) -> None:
    assert contract.V6_BODY_X == pytest.approx(1.10)
    assert contract.V6_BODY_W == pytest.approx(32.80)
    assert contract.V6_BANDS == {
        "takehome": (8.92, 1.25),
        "motivation": (10.42, 7.60),
        "method": (18.22, 9.30),
        "results": (27.72, 7.50),
        "conclusion": (35.42, 2.93),
    }
    assert contract.V6_FONT == "Noto Sans"
    assert contract.V6_WHITE_BODY_TOP == pytest.approx(8.80)
    assert contract.V6_WHITE_BODY_BOTTOM == pytest.approx(38.35)
    assert contract.V6_PLOT_RANGE == (70, 95)
    assert contract.V6_TITLE_PT == 74
    assert contract.V6_BODY_PT >= 24
    assert contract.V6_FIGURE_PT >= 22
    assert contract.V6_QUALIFIER_PT >= 18
    assert contract.V6_MAX_ROUNDED_BODY_SHAPES <= 10
    assert contract.V6_WORD_COUNT_RANGE == (450, 620)


def test_v6_readme_documents_build_export_and_validation() -> None:
    text = README_PATH.read_text()
    assert "build_sarge_poster_v6.py" in text
    assert "validate_sarge_poster_v6.py --all" in text
    assert "final_v6/SARGE_CCKS2026_poster_en_award_v6.pptx" in text
