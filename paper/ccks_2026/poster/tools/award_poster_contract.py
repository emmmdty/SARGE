from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
POSTER_DIR = ROOT / "paper/ccks_2026/poster"
POSTER_FONT = "Arial"

PAPER_PDF = ROOT / "paper/SARGE_CCKS2026.pdf"
V2_PPTX = POSTER_DIR / "SARGE_CCKS2026_poster_en_revised_v2.pptx"
V2_PNG = POSTER_DIR / "SARGE_CCKS2026_poster_en_revised_v2.png"
TEMPLATE_PPTX = POSTER_DIR / "template/CCKS2026-poster参考模板.pptx"
TEMPLATE_REFERENCE_PNG = POSTER_DIR / "assets/SARGE_CCKS2026_poster_reference.png"
QR_IMAGE = POSTER_DIR / "assets/github_repository_qr.png"
FORMULA_DIR = POSTER_DIR / "assets/formulas"
METHOD_INPUT_FORMULA = FORMULA_DIR / "method_input.png"
OPTIONAL_CUES_FORMULA = FORMULA_DIR / "optional_cues.png"
DELTA_RECORD_FORMULA = FORMULA_DIR / "delta_record.png"
FORMULA_IMAGES = (
    METHOD_INPUT_FORMULA,
    OPTIONAL_CUES_FORMULA,
    DELTA_RECORD_FORMULA,
)

V3_PPTX = POSTER_DIR / "SARGE_CCKS2026_poster_en_award_v3.pptx"
V3_PDF = POSTER_DIR / "SARGE_CCKS2026_poster_en_award_v3.pdf"
V3_PNG = POSTER_DIR / "SARGE_CCKS2026_poster_en_award_v3.png"
IMAGEGEN_PROMPT = POSTER_DIR / "SARGE_CCKS2026_poster_award_v3_imagegen_prompt.md"
IMAGEGEN_REFERENCE = POSTER_DIR / "SARGE_CCKS2026_poster_award_v3_visual_reference.png"
ANALYSIS_REPORT = POSTER_DIR / "poster_award_v3_analysis.md"

V4_PPTX = POSTER_DIR / "SARGE_CCKS2026_poster_en_award_v4.pptx"
V4_PDF = POSTER_DIR / "SARGE_CCKS2026_poster_en_award_v4.pdf"
V4_PNG = POSTER_DIR / "SARGE_CCKS2026_poster_en_award_v4.png"
V4_REPORT = POSTER_DIR / "poster_revision_report.md"

V5_PPTX = POSTER_DIR / "SARGE_CCKS2026_poster_en_award_v5.pptx"
V5_PDF = POSTER_DIR / "SARGE_CCKS2026_poster_en_award_v5.pdf"
V5_PNG = POSTER_DIR / "SARGE_CCKS2026_poster_en_award_v5.png"
V5_REPORT = POSTER_DIR / "poster_award_v5_analysis.md"

PAGE_CM = (88.90, 109.22)
PAGE_PT = (2520, 3096)
V5_TITLE_PT = 74
V5_AUTHORS_PT = 32
V5_AFFILIATIONS_PT = 22
V5_BODY_MIN_PT = 22
V5_CHART_CAPTION_MIN_PT = 20
V5_QUALIFIER_MIN_PT = 18
V5_VERTICAL_NARRATIVE_RATIOS = {
    "takehome": 0.05,
    "motivation": 0.20,
    "method": 0.36,
    "results": 0.28,
    "conclusion": 0.08,
}
BODY_BOUNDS_IN = (1.10, 9.65, 32.80, 28.15)
BODY_GRID = (12, 10)
DENSITY_CELL_RANGE = (0.82, 0.89)
DENSITY_CELL_COVERAGE_MIN = 0.41
MAX_UNEXPLAINED_GAP_IN = 0.48

PROTECTED_SHAPES = {
    "FTR_CONFERENCE_TEXT",
    "FTR_QR_FRAME",
    "FTR_QR_IMAGE",
    "FTR_LABEL",
    "FTR_URL",
    "FTR_EMAIL",
}
EDITABLE_HEADER_SHAPES = {
    "HDR_TITLE",
    "HDR_AUTHORS",
    "HDR_CORRESPONDING_SYMBOL",
    "HDR_AFFILIATIONS",
    "TAKEHOME_FRAME",
    "TAKEHOME_LABEL_BOX",
    "TAKEHOME_LABEL",
    "TAKEHOME_TEXT",
}
REMOVE_BODY_SHAPES = {f"S{index}_GROUP" for index in range(1, 8)}

REPOSITORY_URL = "https://github.com/emmmdty/SARGE"
DISPLAY_URL = "github.com/emmmdty/SARGE"
CONTACT_EMAIL = "yue.zhao@hit.edu.cn"

TITLE = (
    "SARGE: Schema-Grounded Event-Table Generation\n"
    "for Chinese Financial Document-Level\n"
    "Event Extraction"
)
AUTHORS = (
    "Jiakai Tong¹² · Mengting Qin¹ · Yongqi Hu¹ · "
    "Xueyao Wan¹² · Yue Zhao¹²*"
)
AFFILIATIONS = (
    "¹ School of Astronautics, Harbin Institute of Technology\n"
    "² Zhengzhou Advanced Research Institute, Harbin Institute of Technology"
)
TAKEHOME = (
    "SARGE turns a closed schema into an event-table contract, reaching 85.6 F1 "
    "on ChFinAnn with strong multi-event robustness; ExactRec reveals the "
    "remaining row-assembly gap."
)

V5_TAKEHOME = (
    "Correct values can still form wrong rows. SARGE's schema-grounded contract "
    "improves ChFinAnn multi-event F1 by 5.1 over EPAL; ExactRec (strict event-row "
    "match) reveals what role F1 misses."
)
V5_MOTIVATION = {
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
V5_CONTRIBUTIONS = (
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
V5_OVERALL_F1_DATA = (
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
V5_MULTI_EVENT_DATA = {
    "dataset": "ChFinAnn",
    "aggregation": "mean",
    "seeds": (13, 17, 42),
    "scope_method": "SARGE",
    "rows": (
        {"method": "EPAL", "f1_s": 89.7, "f1_m": 76.6, "gap": 13.1},
        {"method": "SARGE", "f1_s": 89.2, "f1_m": 81.7, "gap": 7.5},
    ),
}
V5_ALIGNMENT_DIAGNOSTICS = (
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
V5_RECORD_DIAGNOSTICS = (
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
V5_CONCLUSION_MESSAGES = (
    (
        "Schema-grounded event-table generation improves multi-event robustness by "
        "predicting complete event rows."
    ),
    "ExactRec exposes row-assembly failures that role F1 can hide.",
    "Schema validity is necessary, but SARGE does not solve exact record binding.",
)

PROBLEM_HEADING = "Correct values can still form the wrong rows"
PROBLEM_RECORDS = (
    "15M | CITIC | 05-20 → 05-19",
    "8M | Guotai Junan | 06-05 → 06-04",
)
PROBLEM_CAPTION = (
    "Shared arguments make candidate rows look alike. The extractor succeeds only "
    "when each pledgee, share amount, and date span stays jointly bound."
)

METHOD_HEADING = "SARGE generates one schema-valid event table"
METHOD_STAGES = (
    ("Inputs", "Document D\nClosed schema S\nOptional cues C_K(D), P_D"),
    (
        "Output contract",
        "Licensed event types and roles\nCopy source values\nOne event per row",
    ),
    (
        "4B LLM",
        "Answer-token SFT\nOutput-only loss\nGreedy decoding\nOne table per doc",
    ),
    (
        "Schema check",
        (
            "Reject illegal labels\nDrop empty fields\nNormalize role order\n"
            "Post-check schema conformance is 100%"
        ),
    ),
    ("Fixed-slot table", "type | r1 | r2 | …\ne1 | value | value\ne2 | value | value"),
)

EVIDENCE_MODULES = (
    {
        "heading": "Competitive overall",
        "anchors": ("85.6 ± 0.4", "78.3 ± 0.4"),
        "labels": ("ChFinAnn F1", "DuEE-Fin F1"),
        "note": (
            "Competitive, with a dataset-specific caveat: ChFinAnn is numerically above the "
            "listed baselines; on DuEE-Fin, SARGE trails SEELE (80.8) but exceeds "
            "EPAL and ProCNet."
        ),
    },
    {
        "heading": "Stronger multi-event robustness",
        "anchors": ("81.7 F1(M.)", "7.5 S–M Gap"),
        "labels": ("SARGE 4B · 3-seed mean", "smaller degradation"),
        "note": (
            "vs EPAL: +5.1 F1(M.) and a 5.6-point smaller S–M gap. "
            "Performance stays stronger as same-type row ambiguity grows."
        ),
    },
    {
        "heading": "Alignment drives the gain",
        "anchors": ("24.8 → 86.0", "3.3 → 78.0"),
        "labels": (
            "ChFinAnn · No SFT → +SFT",
            "DuEE-Fin · No SFT → +SFT",
        ),
        "note": (
            "Removing SFT collapses F1. The dominant gain comes from learning the "
            "event-table interface, not from raw 4B capacity alone. Same backbone, "
            "seed 13; reported inference paths differ."
        ),
    },
)

DIAGNOSTIC_HEADING = "Role recovery is not exact row assembly"
DIAGNOSTIC_ROWS = (
    ("ChFinAnn", "F1 85.6", "ExactRec 56.1", "Δrecord 29.5"),
    ("DuEE-Fin", "F1 78.3", "ExactRec 43.3", "Δrecord 35.1"),
)
DELTA_NOTE = (
    "Δrecord = F1 − ExactRec; it also includes missing, extra, or wrong values "
    "and event-count errors."
)
CONTRIBUTIONS = (
    (
        "Prediction object",
        (
            "Predict complete event rows so row identity is learned rather than "
            "reconstructed after independent role decisions."
        ),
    ),
    (
        "Schema contract",
        (
            "Licensed types and roles define the output space; document-visible strings "
            "guide faithful copying."
        ),
    ),
    (
        "Honest evaluation",
        (
            "F1 measures recovered role–value pairs; ExactRec asks whether each entire "
            "event row is jointly correct."
        ),
    ),
)
BOUNDARY = "SARGE does not solve record binding completely."
BOUNDARY_DETAIL = (
    "Schema checking guarantees legal labels, not correct private-value binding; "
    "ExactRec still trails F1 by 29.5 / 35.1 points."
)
BOUNDARY_NEXT = "Next: explicit same-type row assembly under shared evidence."

SOURCE_REQUIRED_TOKENS = (
    "85.6",
    "78.3",
    "81.7",
    "24.8",
    "3.3",
    "56.1",
    "43.3",
    "29.5",
    "35.1",
)
V2_REQUIRED_TOKENS = (
    "Jiakai Tong",
    "Mengting Qin",
    "Yongqi Hu",
    "Xueyao Wan",
    "Yue Zhao",
    "Means over seeds 13/17/42",
    "below SEELE",
    "not a pure binding-error estimate",
    DISPLAY_URL,
    CONTACT_EMAIL,
)
V3_REQUIRED_TOKENS = (
    "Jiakai Tong",
    "Mengting Qin",
    "Yongqi Hu",
    "Xueyao Wan",
    "Yue Zhao",
    "85.6 ± 0.4",
    "78.3 ± 0.4",
    "81.7",
    "7.5",
    "76.6",
    "13.1",
    "24.8 → 86.0",
    "3.3 → 78.0",
    "ExactRec 56.1",
    "ExactRec 43.3",
    "Δrecord 29.5",
    "Δrecord 35.1",
    "trails SEELE (80.8)",
    "reported inference paths differ",
    "No SFT → +SFT",
    "+5.1 F1(M.)",
    "Post-check schema conformance is 100%",
    "Predict complete event rows",
    "Schema checking guarantees legal labels",
    "event-count errors",
    "does not solve record binding completely",
    DISPLAY_URL,
    CONTACT_EMAIL,
)
FORBIDDEN_CLAIMS = (
    "state-of-the-art",
    "sota",
    "outperforms seele on duee-fin",
    "outperforms all baselines on both datasets",
    "solves record binding",
)

V5_REQUIRED_TOKENS = (
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
    DISPLAY_URL,
    CONTACT_EMAIL,
)
V5_FORBIDDEN_CLAIMS = FORBIDDEN_CLAIMS + (
    "eliminates record-binding errors",
    "exactrec isolates binding errors",
)

QUALIFIER_NAME_MARKERS = ("_NOTE", "_SOURCE", "_QUALIFIER", "_FOOTNOTE")
CAPTION_NAME_MARKERS = ("_CAPTION",)
DENSITY_EXCLUDED_NAME_MARKERS = ("_BG", "_DIVIDER", "_CONNECTOR", "_LINE")

# V6 publication-poster contract. V5 remains immutable source material; v6
# writes only to the dedicated final_v6 directory.
V6_OUTPUT_DIR = POSTER_DIR / "final_v6"
V6_PPTX = V6_OUTPUT_DIR / "SARGE_CCKS2026_poster_en_award_v6.pptx"
V6_PDF = V6_OUTPUT_DIR / "SARGE_CCKS2026_poster_en_award_v6.pdf"
V6_PNG = V6_OUTPUT_DIR / "SARGE_CCKS2026_poster_en_award_v6.png"
V6_FONT = "Noto Sans"
V6_FIGURE_SOURCE_DIR = ROOT.parents[1] / "SARGE/paper/ccks_2026/figures"
V6_FIG1_PPTX = V6_FIGURE_SOURCE_DIR / "fig1_binding_gap_vector.pptx"
V6_FIG2_PPTX = V6_FIGURE_SOURCE_DIR / "fig2_sarge_pipeline_vector.pptx"
V6_METHOD_INPUT_FORMULA = FORMULA_DIR / "v6_method_input.png"
V6_SFT_LOSS_FORMULA = FORMULA_DIR / "v6_sft_loss.png"
V6_DELTA_FORMULA = FORMULA_DIR / "v6_delta_record.png"

V6_TAKEHOME = (
    "Correct argument values can still form the wrong event rows. "
    "On ChFinAnn, SARGE gains 5.1 Multi-Event F1 points over EPAL; "
    "ExactRec reveals complete-row failures beyond role F1."
)
V6_TAKEHOME_EMPHASIS = (
    "wrong event rows",
    "5.1 Multi-Event F1 points",
    "ExactRec",
)

V6_MOTIVATION_STAGES = (
    "Source evidence",
    "Recovered role values (unordered)",
    "Event-row assembly",
)
V6_EQUITY_PLEDGE_HEADERS = ("Shares", "Pledgee", "Start", "End")
V6_EQUITY_PLEDGE_ROWS = (
    ("15M", "CITIC", "2024-05-20", "2025-05-19"),
    ("8M", "Guotai Junan", "2024-06-05", "2025-06-04"),
)
V6_EQUITY_PLEDGE_WRONG_ROWS = (
    ("15M", "Guotai Junan", "2024-05-20", "2025-06-04"),
    ("8M", "CITIC", "2024-06-05", "2025-05-19"),
)
V6_MOTIVATION_CONSEQUENCE = (
    "Every displayed value is correct, yet the wrong assembly describes two "
    "pledge records absent from the source evidence."
)
V6_MOTIVATION_ANCHORS = (
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
V6_MECHANISMS = (
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
V6_MECHANISM_SHORT = (
    ("Post-hoc row assembly", "Complete-table supervision"),
    ("Schema-invalid output", "Closed schema contract"),
    ("Source-unanchored values", "Bounded source cues"),
)

V6_CONVENTIONAL_FLOW = (
    "Role-wise argument values",
    "Post-hoc record assembly",
    "Cross-row binding risk",
)
V6_METHOD_FLOW = (
    "Prompt contract",
    "Answer-only SFT target",
    "Standard greedy decoding",
    "Post-validation + fixed-slot table",
)
V6_METHOD_DETAILS = (
    "Document D, closed schema S, bounded candidates C_K(D), optional prior P_D, and instruction I_S",
    "Gold serialized event table; the loss is computed only on answer tokens",
    "Full tokenizer vocabulary; one candidate per document; no constrained decoding",
    "Filter malformed or schema-invalid rows and roles, remove empty fields, and normalize role order",
)
V6_METHOD_CORE_CHANGE = (
    "Core change: supervise the serialized gold event table so each output row "
    "represents one event record."
)
V6_GROUNDING_NOTE = (
    "Schema and source cues enter the prompt contract; row structure is learned "
    "from answer-only table targets; schema checking occurs after standard decoding."
)
V6_METHOD_MECHANISM = (
    "Not prompt-only: one contract structures SFT inputs and table targets; validation maps decoded rows to fixed slots."
)
V6_VALIDATION_NOTE = (
    "Checks schema-defined types/roles, removes empty fields, and normalizes slot order."
)
V6_IMPLEMENTATION = "Qwen3-4B · LoRA SFT · 3 seeds"

V6_OVERALL_F1 = (
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
V6_MULTI_EVENT = (
    {"model": "EPAL", "single": 89.7, "multi": 76.6, "gap": 13.1},
    {
        "model": "SARGE",
        "single": 89.2,
        "multi": 81.7,
        "gap": 7.5,
        "std": {"single": 0.7, "multi": 0.1},
    },
)
V6_MULTI_EVENT_DEFINITION = (
    "Multi-event documents contain more than one non-empty gold event record."
)
V6_EVIDENCE_SCOPE = (
    "+5.1 establishes general multi-event robustness; EPAL ExactRec is unavailable, "
    "so it does not isolate binding-error reduction."
)
V6_RECORD_DIAGNOSTICS = (
    {"dataset": "ChFinAnn", "role_f1": 85.6, "exact_rec": 56.1, "gap": 29.5},
    {"dataset": "DuEE-Fin", "role_f1": 78.3, "exact_rec": 43.3, "gap": 35.1},
)
V6_EXACTREC_DEFINITION = "ExactRec tests whether each complete event row matches exactly."
V6_ROLE_F1_QUESTION = "Are the role–value pairs recovered?"
V6_EXACTREC_QUESTION = "Is the complete event row exact?"
V6_EXACTREC_CAVEAT = (
    "The F1–ExactRec gap includes missing, extra, incorrect, and misbound "
    "arguments; it is not a pure binding-error estimate."
)
V6_DIAGNOSTIC_COLUMN = "F1 − ExactRec"
V6_DUEE_GAP_NOTE = "† Mean of per-seed gaps; displayed component means are rounded."
V6_CONCLUSION = (
    (
        "Gain",
        "Prediction-unit insight: supervising the serialized event table shifts learning from isolated values toward coherent event rows.",
    ),
    (
        "Diagnostic",
        "Role F1 and ExactRec provide complementary views of role–value recovery and exact row correctness.",
    ),
    (
        "Remaining limitation",
        "The reported study covers closed-schema Chinese financial DEE; open-schema behavior is not evaluated. ExactRec reaches 56.1 on ChFinAnn and 43.3 on DuEE-Fin.",
    ),
)

V6_BODY_X = 1.10
V6_BODY_W = 32.80
V6_WHITE_BODY_TOP = 8.80
V6_WHITE_BODY_BOTTOM = 38.35
V6_BANDS = {
    "takehome": (8.92, 1.25),
    "motivation": (10.42, 7.60),
    "method": (18.22, 9.30),
    "results": (27.72, 7.50),
    "conclusion": (35.42, 2.93),
}
V6_TITLE_PT = 74
V6_AUTHORS_PT = 32
V6_AFFILIATIONS_PT = 22
V6_SECTION_PT = 32
V6_BODY_PT = 24
V6_FIGURE_PT = 22
V6_QUALIFIER_PT = 18
V6_MAX_ROUNDED_BODY_SHAPES = 10
V6_WORD_COUNT_RANGE = (450, 620)
V6_PLOT_RANGE = (70, 95)
V6_PALETTE = {
    "navy": "102A56",
    "teal": "098F88",
    "red": "D95849",
    "ink": "17243A",
    "muted": "53647C",
    "grid": "CBD7E8",
    "gray": "A8B2C2",
    "light_gray": "F3F6F9",
    "light_teal": "EAF7F4",
    "light_red": "FCEDEA",
    "white": "FFFFFF",
}

V6_REQUIRED_TOKENS = (
    V6_TAKEHOME,
    "Schema-grounded event-table contract",
    V6_METHOD_CORE_CHANGE,
    V6_VALIDATION_NOTE,
    "5.1 points over EPAL on ChFinAnn",
    "Single-to-Multi gap: 13.1 → 7.5, reduced by 5.6",
    "Doc2EDAG [18]",
    "GIT [14]",
    "ProCNet [13]",
    "EPAL [7]",
    "SEELE [15]",
    "85.6 ± 0.4",
    "78.3 ± 0.4",
    "56.1",
    "43.3",
    "29.5",
    "35.1",
    V6_DIAGNOSTIC_COLUMN,
    V6_EXACTREC_CAVEAT,
    V6_EVIDENCE_SCOPE,
    DISPLAY_URL,
    CONTACT_EMAIL,
)
V6_FORBIDDEN_CLAIMS = FORBIDDEN_CLAIMS + (
    "role-grounded contract",
    "100% schema-valid",
    "pure binding error",
    "does not solve exact record binding",
    "no sft",
    "by +5.1",
    "preserves event identity",
    "100% post-validation schema conformance",
    "unlicensed structure",
    "uncontrolled values",
)
