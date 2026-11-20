from __future__ import annotations

from pathlib import Path

from pptx import Presentation
from pptx.enum.shapes import MSO_SHAPE_TYPE
from pptx.util import Cm, Pt


POSTER_DIR = Path(__file__).resolve().parents[1]
SOURCE = POSTER_DIR / "SARGE_CCKS2026_poster_en_award_v3.pptx"
OUTPUT = POSTER_DIR / "SARGE_CCKS2026_poster_en_award_v4.pptx"


def recursive_shapes(shapes):
    for shape in shapes:
        yield shape
        if shape.shape_type == MSO_SHAPE_TYPE.GROUP:
            yield from recursive_shapes(shape.shapes)


def shape_map(slide):
    return {shape.name: shape for shape in recursive_shapes(slide.shapes)}


def replace_text(shape, text: str, *, size: float | None = None) -> None:
    """Replace uniform text while preserving the shape's established styling."""
    text_frame = shape.text_frame
    prototype_paragraph = text_frame.paragraphs[0]
    prototype_run = prototype_paragraph.runs[0]
    font = prototype_run.font

    style = {
        "name": font.name,
        "size": Pt(size) if size is not None else font.size,
        "bold": font.bold,
        "italic": font.italic,
        "alignment": prototype_paragraph.alignment,
        "line_spacing": prototype_paragraph.line_spacing,
        "space_before": prototype_paragraph.space_before,
        "space_after": prototype_paragraph.space_after,
        "level": prototype_paragraph.level,
    }
    rgb = None
    try:
        rgb = font.color.rgb
    except (AttributeError, TypeError, ValueError):
        pass

    text_frame.clear()
    for index, line in enumerate(text.split("\n")):
        paragraph = text_frame.paragraphs[0] if index == 0 else text_frame.add_paragraph()
        paragraph.alignment = style["alignment"]
        paragraph.line_spacing = style["line_spacing"]
        paragraph.space_before = style["space_before"]
        paragraph.space_after = style["space_after"]
        paragraph.level = style["level"]
        run = paragraph.add_run()
        run.text = line
        run.font.name = style["name"]
        run.font.size = style["size"]
        run.font.bold = style["bold"]
        run.font.italic = style["italic"]
        if rgb is not None:
            run.font.color.rgb = rgb


def main() -> None:
    presentation = Presentation(SOURCE)
    assert len(presentation.slides) == 1
    slide = presentation.slides[0]
    shapes = shape_map(slide)

    shapes["HDR_AUTHORS"].width = Cm(31.20)
    shapes["HDR_CORRESPONDING_SYMBOL"].left = Cm(35.55)

    replacements: dict[str, tuple[str, float | None]] = {
        "TAKEHOME_TEXT": (
            "SARGE turns a closed schema into an event-table contract: "
            "85.6 ± 0.4 F1 on ChFinAnn (3-seed mean), strong multi-event "
            "robustness, and an explicit ExactRec row-assembly diagnostic.",
            30,
        ),
        "AW_PROBLEM_NOTE": ("TWO SAME-TYPE EQUITY-PLEDGE RECORDS", 20),
        "AW_METHOD_HEADING": (
            "SARGE generates and validates one fixed-slot event table",
            None,
        ),
        "AW_METHOD_NOTE": (
            "ONE CONTRACT · ONE PREDICTION OBJECT · ONE BENCHMARK-COMPATIBLE TABLE",
            20,
        ),
        "AW_METHOD_3_TITLE": ("Qwen3-4B\n+ LoRA SFT", 22),
        "AW_METHOD_3_BODY": (
            "4-bit NF4\nAnswer-only loss\n2 epochs\nGreedy decoding\nOne table / doc",
            None,
        ),
        "AW_METHOD_4_BODY": (
            "Licensed labels only\nDrop empty fields\nNormalize role order\n"
            "100% post-validation\nschema conformance\n(seed 13)",
            23,
        ),
        "AW_METHOD_ALIGNMENT_CAPTION": (
            "Implementation · single RTX 4090",
            None,
        ),
        "AW_EVIDENCE_STORY": (
            "TWO DATASETS · 43,940 TOTAL DOCUMENTS · "
            "ChFinAnn 32,040 · DuEE-Fin 11,900",
            22,
        ),
        "AW_EVIDENCE_1_CHFINANN_LABEL": (
            "ChFinAnn F1 · 3-seed mean",
            23,
        ),
        "AW_EVIDENCE_1_DUEEFIN_LABEL": (
            "DuEE-Fin F1 · 3-seed mean",
            23,
        ),
        "AW_EVIDENCE_2_F1M_VALUE": ("81.7 ± 0.1", 44),
        "AW_EVIDENCE_2_F1M_LABEL": (
            "ChFinAnn F1(M.) · 3-seed mean",
            22,
        ),
        "AW_EVIDENCE_2_GAP_VALUE": ("77.6 ± 0.2", 44),
        "AW_EVIDENCE_2_GAP_LABEL": (
            "DuEE-Fin F1(M.) · 3-seed mean",
            22,
        ),
        "AW_EVIDENCE_2_EPAL": (
            "ChFinAnn S–M gap: 7.5 vs EPAL 13.1",
            23,
        ),
        "AW_EVIDENCE_2_INTERPRETATION_CAPTION": (
            "Multi-event F1 remains close to overall F1 on both datasets. "
            "On ChFinAnn, SARGE is +5.1 F1(M.) above EPAL with a 5.6-point "
            "smaller S–M gap.",
            None,
        ),
        "AW_EVIDENCE_3_CHFINANN_VALUE": ("24.8 → 85.5", None),
        "AW_EVIDENCE_3_CHFINANN_LABEL": (
            "ChFinAnn · No SFT → SFT",
            23,
        ),
        "AW_EVIDENCE_3_DUEEFIN_LABEL": (
            "DuEE-Fin · No SFT → SFT",
            23,
        ),
        "AW_EVIDENCE_3_INTERPRETATION_CAPTION": (
            "Same-backend diagnostic (seed 13): ChFinAnn uses vLLM-BF16 for "
            "both endpoints; DuEE-Fin uses HF-4bit. No-SFT generators emit "
            "empty or sparse rows; SFT aligns generation with the event-table contract.",
            None,
        ),
        "AW_DIAGNOSTIC_CAPTION": (
            "3-seed mean: matched role–value F1 can look strong while complete "
            "event rows remain inexact.",
            None,
        ),
        "AW_DIAGNOSTIC_CAVEAT": (
            "Δrecord is a diagnostic gap, not a pure binding-error estimate. "
            "It also counts missing, extra, or wrong values and event-count errors.",
            None,
        ),
        "AW_BOUNDARY_LABEL": (
            "REMAINING CHALLENGE — EXACT SAME-TYPE ROW BINDING",
            23,
        ),
        "AW_BOUNDARY_TEXT": (
            "Schema validity ≠ exact record assembly.",
            None,
        ),
        "AW_BOUNDARY_CAPTION": (
            "Shared evidence can still cause private values to be assigned to "
            "imperfect rows—even after 100% post-validation schema conformance.",
            None,
        ),
        "AW_BOUNDARY_NEXT_CAPTION": (
            "Next: model explicit row identity under shared evidence.",
            None,
        ),
    }

    missing = sorted(set(replacements) - set(shapes))
    assert not missing, f"missing source shapes: {missing}"
    for name, (text, size) in replacements.items():
        replace_text(shapes[name], text, size=size)

    # Separate adjacent text-frame bounds that relied on internal whitespace in v3.
    # This keeps the rendered baselines while removing even sub-millimetre box overlap.
    for name in (
        "AW_EVIDENCE_1_CHFINANN_LABEL",
        "AW_EVIDENCE_1_DUEEFIN_LABEL",
        "AW_EVIDENCE_2_F1M_LABEL",
        "AW_EVIDENCE_2_GAP_LABEL",
        "AW_EVIDENCE_3_CHFINANN_LABEL",
        "AW_EVIDENCE_3_DUEEFIN_LABEL",
    ):
        shapes[name].top = Cm(60.98)

    for name in (
        "AW_CONTRIBUTION_1_CAPTION",
        "AW_CONTRIBUTION_2_CAPTION",
        "AW_CONTRIBUTION_3_CAPTION",
    ):
        shapes[name].top += Cm(0.08)
        shapes[name].height -= Cm(0.08)

    shapes["AW_BOUNDARY_TEXT"].top = Cm(88.60)
    shapes["AW_BOUNDARY_TEXT"].height = Cm(1.67)

    for name in ("AW_DIAGNOSTIC_CHFINANN_DELTA", "AW_DIAGNOSTIC_DUEEFIN_DELTA"):
        for paragraph in shapes[name].text_frame.paragraphs:
            for run in paragraph.runs:
                run.font.size = Pt(30)

    presentation.core_properties.subject = (
        "CCKS 2026 English academic poster, v4; revised from editable v3"
    )
    presentation.save(OUTPUT)
    print(OUTPUT)


if __name__ == "__main__":
    main()
