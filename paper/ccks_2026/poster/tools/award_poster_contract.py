from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
POSTER_DIR = ROOT / "paper/ccks_2026/poster"

PAPER_PDF = ROOT / "paper/SARGE_CCKS2026.pdf"
V2_PPTX = POSTER_DIR / "SARGE_CCKS2026_poster_en_revised_v2.pptx"
V2_PNG = POSTER_DIR / "SARGE_CCKS2026_poster_en_revised_v2.png"
TEMPLATE_PPTX = POSTER_DIR / "template/CCKS2026-poster参考模板.pptx"
TEMPLATE_REFERENCE_PNG = POSTER_DIR / "assets/SARGE_CCKS2026_poster_reference.png"
QR_IMAGE = POSTER_DIR / "assets/github_repository_qr.png"

V3_PPTX = POSTER_DIR / "SARGE_CCKS2026_poster_en_award_v3.pptx"
V3_PDF = POSTER_DIR / "SARGE_CCKS2026_poster_en_award_v3.pdf"
V3_PNG = POSTER_DIR / "SARGE_CCKS2026_poster_en_award_v3.png"
IMAGEGEN_PROMPT = POSTER_DIR / "SARGE_CCKS2026_poster_award_v3_imagegen_prompt.md"
IMAGEGEN_REFERENCE = POSTER_DIR / "SARGE_CCKS2026_poster_award_v3_visual_reference.png"
ANALYSIS_REPORT = POSTER_DIR / "poster_award_v3_analysis.md"

PAGE_CM = (88.90, 109.22)
PAGE_PT = (2520, 3096)
BODY_BOUNDS_IN = (1.10, 9.65, 32.80, 28.15)
BODY_GRID = (12, 10)
DENSITY_CELL_RANGE = (0.82, 0.88)
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
    "Xueyao Wan¹² · Yue Zhao¹²"
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

PROBLEM_HEADING = "Correct values can still form the wrong rows"
PROBLEM_RECORDS = (
    "15M | CITIC | 05-20 → 05-19",
    "8M | Guotai Junan | 06-05 → 06-04",
)
PROBLEM_CAPTION = (
    "Shared arguments hide row identity; private values must stay bound together."
)

METHOD_HEADING = "SARGE generates one schema-valid event table"
METHOD_STAGES = (
    ("Inputs", "Document D\nClosed schema S\nOptional cues C_K(D), P_D"),
    (
        "Output contract",
        "Licensed event types and roles\nCopy source values\nOne event per row",
    ),
    ("Tuned 4B LLM", "Answer-token SFT\nGreedy decoding"),
    (
        "Schema check",
        "Filter invalid labels\nDrop empty fields\nNormalize role order",
    ),
    ("Fixed-slot table", "type | r1 | r2 | …\ne1 | value | value\ne2 | value | value"),
)

EVIDENCE_MODULES = (
    {
        "heading": "Competitive overall",
        "anchors": ("85.6 ± 0.4", "78.3 ± 0.4"),
        "labels": ("ChFinAnn F1", "DuEE-Fin F1"),
        "note": (
            "ChFinAnn is numerically above the listed baselines; "
            "DuEE-Fin remains below SEELE (80.8)."
        ),
    },
    {
        "heading": "Stronger multi-event robustness",
        "anchors": ("81.7 F1(M.)", "7.5 S–M Gap"),
        "labels": ("SARGE 4B · 3-seed mean", "EPAL: 76.6 · 13.1"),
        "note": "Higher F1(M.) and a smaller S–M Gap are better.",
    },
    {
        "heading": "Alignment drives the gain",
        "anchors": ("24.8 → 86.0", "3.3 → 78.0"),
        "labels": ("ChFinAnn F1", "DuEE-Fin F1"),
        "note": (
            "Same Qwen3-4B backbone, seed 13; reported inference paths differ."
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
    ("Reformulation", "closed-schema DEE as event-table generation"),
    ("Unified interface", "generate, check, normalize, and evaluate fixed-slot rows"),
    ("Diagnostic", "ExactRec exposes row-level errors hidden by role F1"),
)
BOUNDARY = "Remaining boundary: SARGE does not solve record binding completely."

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
    "below SEELE (80.8)",
    "reported inference paths differ",
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

QUALIFIER_NAME_MARKERS = ("_NOTE", "_SOURCE", "_QUALIFIER", "_FOOTNOTE")
CAPTION_NAME_MARKERS = ("_CAPTION",)
DENSITY_EXCLUDED_NAME_MARKERS = ("_BG", "_DIVIDER", "_CONNECTOR", "_LINE")
