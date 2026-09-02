from __future__ import annotations

import argparse
from pathlib import Path

import award_poster_contract as contract
from build_sarge_poster_award import (
    add_box,
    add_picture_contain,
    add_text,
    delete_named_shapes,
    find_shape,
    rgb,
    set_fixed_text,
    set_name,
)
from pptx import Presentation
from pptx.enum.shapes import MSO_CONNECTOR, MSO_SHAPE, MSO_SHAPE_TYPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Inches, Pt
from validate_sarge_poster_award import shape_signature

DEFAULT_OUTPUT = contract.V5_PPTX

FONT = "Arial"
NAVY = "102A56"
TEAL = "098F88"
CORAL = "D95849"
BLUE = "1767D2"
VIOLET = "6B55D9"
GOLD = "D9902F"
INK = "17243A"
MUTED = "53647C"
WHITE = "FFFFFF"
LIGHT_TEAL = "EAF7F4"
LIGHT_CORAL = "FCEDEA"
LIGHT_BLUE = "EEF4FC"
LIGHT_GRAY = "F3F6F9"
LIGHT_VIOLET = "F2EEFD"
LIGHT_GOLD = "FFF4DD"
GRID = "CBD7E8"
BASELINE_GRAY = "A8B2C2"
EPAL_LIGHT = "D8DEE8"
EPAL_DARK = "8D99AB"
SARGE_LIGHT = "A9DDD7"
SARGE_DARK = TEAL


def _add_line(
    slide,
    name: str,
    x1: float,
    y1: float,
    x2: float,
    y2: float,
    *,
    color: str = GRID,
    width: float = 1.0,
):
    line = slide.shapes.add_connector(
        MSO_CONNECTOR.STRAIGHT,
        Inches(x1),
        Inches(y1),
        Inches(x2),
        Inches(y2),
    )
    set_name(line, name)
    line.line.color.rgb = rgb(color)
    line.line.width = Pt(width)
    return line


def _protected_shape_signatures(slide) -> dict[str, tuple]:
    return {
        name: shape_signature(find_shape(slide, name))
        for name in sorted(contract.PROTECTED_SHAPES)
    }


def _preflight_source(prs: Presentation) -> None:
    if len(prs.slides) != 1:
        raise ValueError("v5 source must contain exactly one slide")
    if abs(prs.slide_width / 360000 - contract.PAGE_CM[0]) >= 0.01:
        raise ValueError("source width does not match the CCKS template")
    if abs(prs.slide_height / 360000 - contract.PAGE_CM[1]) >= 0.01:
        raise ValueError("source height does not match the CCKS template")

    slide = prs.slides[0]
    names = {shape.name for shape in slide.shapes}
    required = (
        contract.PROTECTED_SHAPES
        | contract.EDITABLE_HEADER_SHAPES
        | contract.REMOVE_BODY_SHAPES
    )
    missing = required - names
    if missing:
        raise ValueError(f"source does not satisfy the v5 shape contract: {sorted(missing)}")
    qr = find_shape(slide, "FTR_QR_IMAGE")
    if qr.shape_type != MSO_SHAPE_TYPE.PICTURE or not qr.image.blob:
        raise ValueError("v5 source QR picture is missing or invalid")
    missing_formulas = [path for path in contract.FORMULA_IMAGES if not path.is_file()]
    if missing_formulas:
        raise ValueError(f"missing v5 formula assets: {missing_formulas}")


def _update_header(slide) -> None:
    title = find_shape(slide, "HDR_TITLE")
    title.left = Inches(1.57)
    title.top = Inches(0.78)
    # The 74 pt first line needs the otherwise-unused upper-right header space to
    # retain the contract's deliberate three-line break without shrink-to-fit.
    title.width = Inches(26.40)
    title.height = Inches(3.25)
    set_fixed_text(
        title,
        contract.TITLE,
        size=contract.V5_TITLE_PT,
        color=WHITE,
        bold=True,
        valign=MSO_ANCHOR.MIDDLE,
        margin=0,
        line_spacing=0.82,
    )

    authors = find_shape(slide, "HDR_AUTHORS")
    authors.left = Inches(1.61)
    authors.top = Inches(4.12)
    authors.width = Inches(23.40)
    authors.height = Inches(0.66)
    set_fixed_text(
        authors,
        contract.AUTHORS,
        size=contract.V5_AUTHORS_PT,
        color=WHITE,
        bold=True,
        margin=0,
        line_spacing=0.88,
    )

    affiliations = find_shape(slide, "HDR_AFFILIATIONS")
    affiliations.left = Inches(1.61)
    affiliations.top = Inches(4.83)
    affiliations.width = Inches(23.40)
    affiliations.height = Inches(1.06)
    affiliation_text = (
        f"{contract.AFFILIATIONS}\n"
        f"* Corresponding author: {contract.CONTACT_EMAIL}"
    )
    set_fixed_text(
        affiliations,
        affiliation_text,
        size=contract.V5_AFFILIATIONS_PT,
        color=WHITE,
        margin=0,
        line_spacing=0.86,
    )


def _add_takehome(slide) -> None:
    add_box(
        slide,
        "V5_TAKEHOME_BG",
        1.10,
        7.40,
        32.80,
        1.70,
        fill=NAVY,
        radius=True,
    )
    add_box(
        slide,
        "V5_TAKEHOME_LABEL_BG",
        1.48,
        7.69,
        3.34,
        0.66,
        fill=TEAL,
        radius=True,
    )
    add_text(
        slide,
        "V5_TAKEHOME_LABEL",
        1.64,
        7.82,
        3.02,
        0.36,
        "TAKE-HOME MESSAGE",
        size=22,
        color=WHITE,
        bold=True,
        align=PP_ALIGN.CENTER,
        margin=0,
    )
    add_text(
        slide,
        "V5_TAKEHOME_TEXT",
        5.08,
        7.60,
        28.18,
        1.25,
        contract.V5_TAKEHOME,
        size=28,
        color=WHITE,
        bold=True,
        margin=0,
        line_spacing=0.86,
    )


def _add_section_heading(slide, name: str, y: float, text: str) -> None:
    add_text(
        slide,
        name,
        1.24,
        y + 0.10,
        32.50,
        0.66,
        text,
        size=32,
        color=NAVY,
        bold=True,
        margin=0,
        line_spacing=0.88,
    )


def _add_motivation(slide) -> None:
    x, y, w, h = 1.10, 9.55, 32.80, 5.55
    add_box(slide, "V5_MOTIVATION_BAND", x, y, w, h, fill=LIGHT_GRAY)
    add_box(slide, "V5_MOTIVATION_TOP_RULE", x, y, w, 0.08, fill=CORAL)
    _add_section_heading(
        slide,
        "V5_MOTIVATION_HEADING",
        y,
        "1 Motivation — Correct values can still form wrong rows",
    )
    add_box(
        slide,
        "V5_MOTIVATION_WHY_BG",
        1.28,
        10.35,
        8.30,
        4.48,
        fill=LIGHT_BLUE,
        line=GRID,
    )
    add_text(
        slide,
        "V5_MOTIVATION_WHY_LABEL",
        1.60,
        10.56,
        7.70,
        0.38,
        "WHY THIS PROBLEM MATTERS",
        size=22,
        color=BLUE,
        bold=True,
        margin=0,
    )
    reasons = "\n".join(contract.V5_MOTIVATION["reasons"])
    add_text(
        slide,
        "V5_MOTIVATION_REASONS",
        2.42,
        11.13,
        6.76,
        3.42,
        reasons,
        size=24,
        color=INK,
        margin=0,
        line_spacing=0.79,
        valign=MSO_ANCHOR.TOP,
    )
    for index, reason_y in enumerate((11.14, 12.29, 13.44), start=1):
        add_box(
            slide,
            f"V5_MOTIVATION_REASON_BADGE_{index}",
            1.62,
            reason_y,
            0.56,
            0.56,
            fill=BLUE if index < 3 else CORAL,
            radius=True,
        )
        add_text(
            slide,
            f"V5_MOTIVATION_REASON_BADGE_TEXT_{index}",
            1.62,
            reason_y + 0.08,
            0.56,
            0.30,
            str(index),
            size=22,
            color=WHITE,
            bold=True,
            align=PP_ALIGN.CENTER,
            margin=0,
        )

    add_box(
        slide,
        "V5_MOTIVATION_EXAMPLE_BG",
        9.82,
        10.35,
        12.20,
        4.48,
        fill=LIGHT_CORAL,
        line="F1B8B0",
    )
    add_text(
        slide,
        "V5_MOTIVATION_EXAMPLE_LABEL",
        10.10,
        10.55,
        11.64,
        0.38,
        "EQUITY-PLEDGE EXAMPLE · TWO SAME-TYPE EVENTS",
        size=22,
        color=NAVY,
        bold=True,
        align=PP_ALIGN.CENTER,
        margin=0,
    )
    source_rows = (
        ("Shares 15M | Pledgee CITIC | 05-20 → 05-19", 10.98),
        ("Shares 8M | Pledgee Guotai Junan | 06-05 → 06-04", 11.48),
    )
    for index, (row_text, row_y) in enumerate(source_rows, start=1):
        add_box(
            slide,
            f"V5_MOTIVATION_SOURCE_ROW_{index}_BG",
            10.18,
            row_y,
            11.48,
            0.40,
            fill=WHITE,
            line=GRID,
        )
        add_text(
            slide,
            f"V5_MOTIVATION_SOURCE_ROW_{index}",
            10.38,
            row_y + 0.06,
            11.08,
            0.26,
            row_text,
            size=22,
            color=NAVY,
            bold=True,
            align=PP_ALIGN.CENTER,
            margin=0,
        )
    add_box(
        slide,
        "V5_MOTIVATION_WRONG_ROW_BG",
        10.18,
        12.06,
        5.52,
        2.50,
        fill=WHITE,
        line=CORAL,
        line_width=1.2,
    )
    add_text(
        slide,
        "V5_MOTIVATION_WRONG_ROW",
        10.38,
        12.20,
        5.12,
        1.78,
        (
            "WRONG — CROSS-BOUND\n"
            "15M | Guotai Junan\n05-20 → 06-04\n"
            "8M | CITIC\n06-05 → 05-19"
        ),
        size=22,
        color=CORAL,
        bold=True,
        align=PP_ALIGN.CENTER,
        margin=0,
        line_spacing=0.78,
    )
    add_text(
        slide,
        "V5_MOTIVATION_WRONG_QUALIFIER",
        10.38,
        14.08,
        5.12,
        0.30,
        "Private values cross rows",
        size=18,
        color=CORAL,
        bold=True,
        align=PP_ALIGN.CENTER,
        margin=0,
    )
    add_box(
        slide,
        "V5_MOTIVATION_CORRECT_ROW_BG",
        15.92,
        12.06,
        5.74,
        2.50,
        fill=WHITE,
        line=TEAL,
        line_width=1.2,
    )
    add_text(
        slide,
        "V5_MOTIVATION_CORRECT_ROW",
        16.12,
        12.20,
        5.34,
        1.78,
        (
            "CORRECT — JOINTLY BOUND\n"
            "15M | CITIC\n05-20 → 05-19\n"
            "8M | Guotai Junan\n06-05 → 06-04"
        ),
        size=22,
        color=TEAL,
        bold=True,
        align=PP_ALIGN.CENTER,
        margin=0,
        line_spacing=0.78,
    )
    add_text(
        slide,
        "V5_MOTIVATION_CORRECT_QUALIFIER",
        16.12,
        14.08,
        5.34,
        0.30,
        "Private values stay bound",
        size=18,
        color=TEAL,
        bold=True,
        align=PP_ALIGN.CENTER,
        margin=0,
    )

    add_box(
        slide,
        "V5_MOTIVATION_RESPONSE_BG",
        22.28,
        10.35,
        11.42,
        4.48,
        fill=LIGHT_TEAL,
        line="ABDCD7",
    )
    add_text(
        slide,
        "V5_MOTIVATION_RESPONSE_LABEL",
        22.60,
        10.55,
        10.78,
        0.38,
        "WHAT SARGE CHANGES",
        size=22,
        color=TEAL,
        bold=True,
        margin=0,
    )
    add_text(
        slide,
        "V5_MOTIVATION_GAP",
        22.60,
        11.02,
        10.78,
        0.78,
        f"Research gap — {contract.V5_MOTIVATION['research_gap']}",
        size=22,
        color=INK,
        margin=0,
        line_spacing=0.80,
        valign=MSO_ANCHOR.TOP,
    )
    add_text(
        slide,
        "V5_MOTIVATION_CONTRIBUTION",
        22.60,
        11.86,
        10.78,
        0.76,
        f"Response — {contract.V5_MOTIVATION['contribution']}",
        size=22,
        color=TEAL,
        bold=True,
        margin=0,
        line_spacing=0.79,
        valign=MSO_ANCHOR.TOP,
    )
    for index, (heading, text) in enumerate(contract.V5_CONTRIBUTIONS, start=1):
        row_y = 12.72 + (index - 1) * 0.66
        add_box(
            slide,
            f"V5_MOTIVATION_CONTRIBUTION_BADGE_{index}",
            22.60,
            row_y,
            0.48,
            0.48,
            fill=TEAL if index < 3 else VIOLET,
            radius=True,
        )
        add_text(
            slide,
            f"V5_MOTIVATION_CONTRIBUTION_BADGE_TEXT_{index}",
            22.60,
            row_y + 0.07,
            0.48,
            0.28,
            str(index),
            size=22,
            color=WHITE,
            bold=True,
            align=PP_ALIGN.CENTER,
            margin=0,
        )
        add_text(
            slide,
            f"V5_MOTIVATION_CONTRIBUTION_{index}",
            23.28,
            row_y - 0.01,
            10.06,
            0.58,
            f"{heading} — {text}",
            size=22,
            color=NAVY if index != 3 else VIOLET,
            bold=True,
            margin=0,
            line_spacing=0.76,
            valign=MSO_ANCHOR.TOP,
        )


def _add_stage(
    slide,
    index: int,
    x: float,
    y: float,
    w: float,
    title: str,
    *,
    fill: str,
    accent: str,
) -> None:
    add_box(
        slide,
        f"V5_METHOD_STAGE_{index}_BG",
        x,
        y,
        w,
        4.64,
        fill=fill,
        line=accent,
        line_width=1.35,
    )
    add_box(
        slide,
        f"V5_METHOD_STAGE_{index}_BADGE",
        x + 0.18,
        y + 0.16,
        0.56,
        0.56,
        fill=accent,
        radius=True,
    )
    add_text(
        slide,
        f"V5_METHOD_STAGE_{index}_BADGE_TEXT",
        x + 0.18,
        y + 0.24,
        0.56,
        0.30,
        str(index),
        size=22,
        color=WHITE,
        bold=True,
        align=PP_ALIGN.CENTER,
        margin=0,
    )
    add_text(
        slide,
        f"V5_METHOD_STAGE_{index}_TITLE",
        x + 0.86,
        y + 0.18,
        w - 1.04,
        0.52,
        title,
        size=24,
        color=accent,
        bold=True,
        margin=0,
    )


def _add_method(slide) -> None:
    x, y, w, h = 1.10, 15.40, 32.80, 10.35
    add_box(slide, "V5_METHOD_BAND", x, y, w, h, fill=LIGHT_BLUE)
    add_box(slide, "V5_METHOD_TOP_RULE", x, y, w, 0.08, fill=BLUE)
    _add_section_heading(
        slide,
        "V5_METHOD_HEADING",
        y,
        "2 Method — Schema grounding governs the event-table pipeline",
    )
    add_text(
        slide,
        "V5_METHOD_SUBHEADING",
        20.10,
        15.58,
        13.38,
        0.38,
        "ONE CONTRACT  ·  ONE PREDICTION OBJECT  ·  ONE TABLE",
        size=22,
        color=BLUE,
        bold=True,
        align=PP_ALIGN.RIGHT,
        margin=0,
    )

    stage_y = 16.34
    stage_w = 5.93
    gap = 0.48
    stage_x = [1.28 + index * (stage_w + gap) for index in range(5)]
    stages = (
        ("Inputs", WHITE, BLUE),
        ("Role-grounded contract", LIGHT_TEAL, TEAL),
        ("Qwen3-4B + LoRA", WHITE, NAVY),
        ("Schema check", LIGHT_VIOLET, VIOLET),
        ("Fixed-slot table", LIGHT_TEAL, TEAL),
    )
    for index, (title, fill, accent) in enumerate(stages, start=1):
        _add_stage(
            slide,
            index,
            stage_x[index - 1],
            stage_y,
            stage_w,
            title,
            fill=fill,
            accent=accent,
        )
        if index < len(stages):
            add_text(
                slide,
                f"V5_METHOD_FLOW_ARROW_{index}",
                stage_x[index - 1] + stage_w,
                stage_y + 1.90,
                gap,
                0.70,
                "→",
                size=34,
                color=BLUE,
                bold=True,
                align=PP_ALIGN.CENTER,
                margin=0,
            )

    # Stage 1: proper math typography from the v4 formula assets.
    add_picture_contain(
        slide,
        "V5_METHOD_STAGE_1_INPUT_FORMULA",
        contract.METHOD_INPUT_FORMULA,
        stage_x[0] + 1.58,
        17.18,
        2.80,
        0.76,
        alt_text=r"LaTeX formula: document D plus closed schema S",
    )
    add_text(
        slide,
        "V5_METHOD_STAGE_1_TEXT",
        stage_x[0] + 0.34,
        18.02,
        stage_w - 0.68,
        0.76,
        "document  +  closed schema",
        size=22,
        color=INK,
        bold=True,
        align=PP_ALIGN.CENTER,
        margin=0,
    )
    add_picture_contain(
        slide,
        "V5_METHOD_STAGE_1_CUES_FORMULA",
        contract.OPTIONAL_CUES_FORMULA,
        stage_x[0] + 0.92,
        18.96,
        4.10,
        0.76,
        alt_text=r"LaTeX formula: surface candidates C_K(D) and slot prior P_D",
    )
    add_text(
        slide,
        "V5_METHOD_STAGE_1_QUALIFIER",
        stage_x[0] + 0.28,
        19.83,
        stage_w - 0.56,
        0.56,
        "C_K(D): candidates  ·  P_D: role-slot prior",
        size=20,
        color=MUTED,
        align=PP_ALIGN.CENTER,
        margin=0,
    )

    # Stage 2: the closed schema becomes an explicit row-generation contract.
    contract_rows = (
        ("•  licensed type + roles", "schema closure"),
        ("•  document-visible values", "source grounding"),
        ("•  one complete row / event", "row identity"),
    )
    for index, (label, qualifier) in enumerate(contract_rows, start=1):
        row_y = 17.26 + (index - 1) * 1.02
        add_box(
            slide,
            f"V5_METHOD_STAGE_2_ROW_{index}_BG",
            stage_x[1] + 0.34,
            row_y,
            stage_w - 0.68,
            0.88,
            fill=WHITE,
            line="A7D9D5",
        )
        add_text(
            slide,
            f"V5_METHOD_STAGE_2_ROW_{index}",
            stage_x[1] + 0.56,
            row_y + 0.10,
            stage_w - 1.12,
            0.34,
            label,
            size=22,
            color=TEAL,
            bold=True,
            margin=0,
        )
        add_text(
            slide,
            f"V5_METHOD_STAGE_2_ROW_{index}_QUALIFIER",
            stage_x[1] + 0.56,
            row_y + 0.48,
            stage_w - 1.12,
            0.26,
            qualifier,
            size=18,
            color=MUTED,
            margin=0,
        )

    # Stage 3: highlight the trained generator without letting hardware dominate.
    model_badge = slide.shapes.add_shape(
        MSO_SHAPE.HEXAGON,
        Inches(stage_x[2] + 1.95),
        Inches(17.28),
        Inches(2.05),
        Inches(1.45),
    )
    set_name(model_badge, "V5_METHOD_STAGE_3_MODEL_BADGE")
    model_badge.fill.solid()
    model_badge.fill.fore_color.rgb = rgb(LIGHT_BLUE)
    model_badge.line.color.rgb = rgb(NAVY)
    model_badge.line.width = Pt(1.4)
    add_text(
        slide,
        "V5_METHOD_STAGE_3_MODEL_TEXT",
        stage_x[2] + 2.20,
        17.68,
        1.55,
        0.52,
        "4B",
        size=34,
        color=NAVY,
        bold=True,
        align=PP_ALIGN.CENTER,
        margin=0,
    )
    add_text(
        slide,
        "V5_METHOD_STAGE_3_TEXT",
        stage_x[2] + 0.34,
        18.94,
        stage_w - 0.68,
        1.50,
        "4-bit NF4\nAnswer-token SFT · 2 epochs\nGreedy, non-thinking decode\nOne table / document",
        size=22,
        color=INK,
        align=PP_ALIGN.CENTER,
        margin=0,
        line_spacing=0.80,
    )

    # Stage 4: schema validity is visible, but explicitly not conflated with binding.
    add_box(
        slide,
        "V5_METHOD_STAGE_4_VALIDITY_BG",
        stage_x[3] + 1.10,
        17.26,
        3.72,
        0.92,
        fill=WHITE,
        line=VIOLET,
        radius=True,
    )
    add_text(
        slide,
        "V5_METHOD_STAGE_4_VALIDITY",
        stage_x[3] + 1.10,
        17.45,
        3.72,
        0.42,
        "100% schema-valid",
        size=24,
        color=VIOLET,
        bold=True,
        align=PP_ALIGN.CENTER,
        margin=0,
    )
    add_text(
        slide,
        "V5_METHOD_STAGE_4_TEXT",
        stage_x[3] + 0.36,
        18.48,
        stage_w - 0.72,
        1.80,
        "Licensed labels + roles\nDrop empty fields\nNormalize role order\nSchema-valid ≠ exact binding",
        size=22,
        color=INK,
        align=PP_ALIGN.CENTER,
        margin=0,
        line_spacing=0.81,
    )

    # Stage 5: native editable fixed-slot table.
    table_x = stage_x[4] + 0.36
    table_y = 17.34
    col_w = (2.08, 1.52, 1.52)
    row_h = 0.72
    table_rows = (("type", "r₁", "r₂"), ("e₁", "value", "value"), ("e₂", "value", "value"))
    for row_index, row in enumerate(table_rows):
        cell_x = table_x
        for col_index, (cell, width) in enumerate(zip(row, col_w)):
            header = row_index == 0
            add_box(
                slide,
                f"V5_METHOD_STAGE_5_CELL_{row_index}_{col_index}",
                cell_x,
                table_y + row_index * row_h,
                width,
                row_h,
                fill=TEAL if header else WHITE,
                line="A7D9D5",
            )
            add_text(
                slide,
                f"V5_METHOD_STAGE_5_CELL_TEXT_{row_index}_{col_index}",
                cell_x,
                table_y + row_index * row_h + 0.17,
                width,
                0.34,
                cell,
                size=22,
                color=WHITE if header else INK,
                bold=header,
                align=PP_ALIGN.CENTER,
                margin=0,
            )
            cell_x += width
    add_text(
        slide,
        "V5_METHOD_STAGE_5_TEXT",
        stage_x[4] + 0.34,
        19.78,
        stage_w - 0.68,
        0.58,
        "Preserve dataset labels\nFixed role order · scorer-ready",
        size=22,
        color=MUTED,
        align=PP_ALIGN.CENTER,
        margin=0,
        line_spacing=0.78,
    )

    ribbons = (
        ("SCHEMA CLOSURE", "licensed labels + fixed role slots", LIGHT_TEAL, TEAL),
        ("SOURCE GROUNDING", "copy document-visible values", LIGHT_BLUE, BLUE),
        ("ROW IDENTITY", "generate one complete row at a time", LIGHT_VIOLET, VIOLET),
    )
    for index, (label, detail, fill, accent) in enumerate(ribbons, start=1):
        ribbon_x = 1.28 + (index - 1) * 10.78
        add_box(
            slide,
            f"V5_METHOD_RIBBON_{index}_BG",
            ribbon_x,
            21.25,
            10.34,
            1.08,
            fill=fill,
            line=accent,
            radius=True,
        )
        add_text(
            slide,
            f"V5_METHOD_RIBBON_{index}",
            ribbon_x + 0.24,
            21.48,
            9.86,
            0.56,
            f"{label}  ·  {detail}",
            size=22,
            color=accent,
            bold=True,
            align=PP_ALIGN.CENTER,
            margin=0,
        )

    add_box(
        slide,
        "V5_METHOD_OBJECTIVE_BG",
        1.28,
        22.58,
        32.18,
        0.82,
        fill=WHITE,
        line=BLUE,
        radius=True,
    )
    add_text(
        slide,
        "V5_METHOD_OBJECTIVE",
        1.58,
        22.80,
        31.58,
        0.38,
        "Document + schema  →  answer-token SFT  →  greedy decode  →  schema check  →  fixed-slot table",
        size=22,
        color=NAVY,
        bold=True,
        align=PP_ALIGN.CENTER,
        margin=0,
    )
    add_box(
        slide,
        "V5_METHOD_HIGHLIGHT_BG",
        1.28,
        23.64,
        32.18,
        0.82,
        fill=LIGHT_GOLD,
        line=GOLD,
        radius=True,
    )
    add_text(
        slide,
        "V5_METHOD_HIGHLIGHT",
        1.58,
        23.84,
        31.58,
        0.40,
        "Why it helps: the schema licenses the output space; row-wise generation keeps private values bound.",
        size=22,
        color=NAVY,
        bold=True,
        align=PP_ALIGN.CENTER,
        margin=0,
    )

    add_text(
        slide,
        "V5_METHOD_QUALIFIER",
        1.30,
        24.66,
        32.20,
        0.48,
        (
            "Implementation: Qwen3-4B · 4-bit NF4 · LoRA · 2 epochs · single RTX 4090 · "
            "seed-13 post-validation schema conformance: 100%."
        ),
        size=20,
        color=MUTED,
        align=PP_ALIGN.CENTER,
        margin=0,
    )


def _method_key(value: str) -> str:
    return value.upper().replace("-", "_")


def _add_overall_chart(
    slide,
    dataset: str,
    value_key: str,
    title: str,
    x: float,
    y: float,
    w: float,
    h: float,
) -> None:
    prefix = f"V5_RESULTS_A_{dataset}_CHART"
    add_text(
        slide,
        f"{prefix}_TITLE",
        x,
        y,
        w,
        0.34,
        title,
        size=20,
        color=NAVY,
        bold=True,
        margin=0,
    )
    plot_x = x + 3.10
    plot_w = w - 4.14
    row_top = y + 0.38
    row_step = 0.265
    bar_h = 0.16
    axis_y = y + h - 0.31

    for tick in (60, 70, 80, 90):
        tick_x = plot_x + (tick - 60) / 30 * plot_w
        _add_line(
            slide,
            f"{prefix}_TICK_LINE_{tick}",
            tick_x,
            row_top - 0.02,
            tick_x,
            axis_y,
            color=GRID,
            width=0.75 if tick != 60 else 1.25,
        )
        add_text(
            slide,
            f"{prefix}_TICK_{tick}",
            tick_x - 0.32,
            axis_y,
            0.64,
            0.29,
            str(tick),
            size=20,
            color=MUTED,
            align=PP_ALIGN.CENTER,
            margin=0,
        )

    for index, row in enumerate(contract.V5_OVERALL_F1_DATA):
        row_y = row_top + index * row_step
        key = _method_key(row["method"])
        label = f"{row['method']} {row['reference']}" if row["reference"] else row["method"]
        add_text(
            slide,
            f"{prefix}_LABEL_{key}",
            x,
            row_y - 0.055,
            2.90,
            0.27,
            label,
            size=20,
            color=TEAL if row["method"] == "SARGE" else NAVY,
            bold=row["method"] in {"SEELE", "SARGE"},
            margin=0,
        )
        value = row[value_key]
        bar_w = (value - 60) / 30 * plot_w
        color = (
            TEAL
            if row["method"] == "SARGE"
            else NAVY
            if row["method"] == "SEELE"
            else BASELINE_GRAY
        )
        add_box(
            slide,
            f"{prefix}_BAR_{key}",
            plot_x,
            row_y,
            bar_w,
            bar_h,
            fill=color,
        )
        value_text = (
            f"{value:.1f} ± {row['std'][value_key]:.1f}"
            if row["method"] == "SARGE"
            else f"{value:.1f}"
        )
        add_text(
            slide,
            f"{prefix}_VALUE_{key}",
            plot_x + bar_w + 0.10,
            row_y - 0.07,
            1.42,
            0.30,
            value_text,
            size=20,
            color=color,
            bold=row["method"] == "SARGE",
            margin=0,
        )

        if row["method"] == "SARGE":
            error = row["std"][value_key] / 30 * plot_w
            center_x = plot_x + bar_w
            center_y = row_y + bar_h / 2
            _add_line(
                slide,
                f"{prefix}_ERROR_BAR",
                center_x - error,
                center_y,
                center_x + error,
                center_y,
                color=TEAL,
                width=2.0,
            )
            _add_line(
                slide,
                f"{prefix}_ERROR_CAP_LEFT",
                center_x - error,
                center_y - 0.10,
                center_x - error,
                center_y + 0.10,
                color=TEAL,
                width=2.0,
            )
            _add_line(
                slide,
                f"{prefix}_ERROR_CAP_RIGHT",
                center_x + error,
                center_y - 0.10,
                center_x + error,
                center_y + 0.10,
                color=TEAL,
                width=2.0,
            )


def _add_multi_event_chart(slide) -> None:
    x, y, w, h = 15.62, 27.48, 8.52, 3.18
    prefix = "V5_RESULTS_B_CHART"
    plot_left = x + 0.82
    plot_right = x + w - 0.18
    plot_top = y + 0.38
    plot_bottom = y + h - 0.48
    min_value, max_value = 70.0, 92.0

    add_text(
        slide,
        f"{prefix}_LEGEND",
        x + 0.82,
        y,
        7.46,
        0.32,
        "F1(S.): single/light · F1(M.): multi/dark",
        size=20,
        color=MUTED,
        align=PP_ALIGN.RIGHT,
        margin=0,
    )
    for tick in (70, 80, 90):
        tick_y = plot_bottom - (tick - min_value) / (max_value - min_value) * (
            plot_bottom - plot_top
        )
        _add_line(
            slide,
            f"{prefix}_Y_TICK_LINE_{tick}",
            plot_left,
            tick_y,
            plot_right,
            tick_y,
            color=GRID,
            width=0.8 if tick != 70 else 1.25,
        )
        add_text(
            slide,
            f"{prefix}_Y_TICK_{tick}",
            x,
            tick_y - 0.15,
            0.65,
            0.30,
            str(tick),
            size=20,
            color=MUTED,
            align=PP_ALIGN.RIGHT,
            margin=0,
        )

    centers = {"EPAL": x + 2.72, "SARGE": x + 6.10}
    bar_colors = {
        ("EPAL", "f1_s"): EPAL_LIGHT,
        ("EPAL", "f1_m"): EPAL_DARK,
        ("SARGE", "f1_s"): SARGE_LIGHT,
        ("SARGE", "f1_m"): SARGE_DARK,
    }
    for row in contract.V5_MULTI_EVENT_DATA["rows"]:
        label_color = EPAL_DARK if row["method"] == "EPAL" else SARGE_DARK
        for metric, dx in (("f1_s", -0.48), ("f1_m", 0.48)):
            value = row[metric]
            color = bar_colors[(row["method"], metric)]
            bar_top = plot_bottom - (value - min_value) / (max_value - min_value) * (
                plot_bottom - plot_top
            )
            add_box(
                slide,
                f"{prefix}_BAR_{row['method']}_{metric.upper()}",
                centers[row["method"]] + dx - 0.33,
                bar_top,
                0.66,
                plot_bottom - bar_top,
                fill=color,
            )
            add_text(
                slide,
                f"{prefix}_VALUE_{row['method']}_{metric.upper()}",
                centers[row["method"]] + dx - 0.55,
                bar_top - 0.34,
                1.10,
                0.30,
                f"{value:.1f}",
                size=20,
                color=label_color,
                bold=True,
                align=PP_ALIGN.CENTER,
                margin=0,
            )
        add_text(
            slide,
            f"{prefix}_METHOD_{row['method']}",
            centers[row["method"]] - 1.05,
            plot_bottom + 0.05,
            2.10,
            0.34,
            row["method"],
            size=20,
            color=NAVY,
            bold=row["method"] == "SARGE",
            align=PP_ALIGN.CENTER,
            margin=0,
        )


def _add_results(slide) -> None:
    x, y, w, h = 1.10, 26.00, 32.80, 7.70
    multi_event_rows = {
        row["method"]: row for row in contract.V5_MULTI_EVENT_DATA["rows"]
    }
    epal = multi_event_rows["EPAL"]
    sarge = multi_event_rows["SARGE"]
    f1_m_gain = sarge["f1_m"] - epal["f1_m"]
    gap_reduction = epal["gap"] - sarge["gap"]
    add_box(slide, "V5_RESULTS_BAND", x, y, w, h, fill=LIGHT_GRAY)
    add_box(slide, "V5_RESULTS_TOP_RULE", x, y, w, 0.08, fill=TEAL)
    panels = (
        ("A", 1.22, 26.68, 13.98, 6.82, WHITE, NAVY),
        ("B", 15.48, 26.68, 8.78, 6.82, LIGHT_GOLD, GOLD),
        ("C", 24.54, 26.68, 9.18, 6.82, LIGHT_TEAL, TEAL),
    )
    for label, panel_x, panel_y, panel_w, panel_h, fill, accent in panels:
        add_box(
            slide,
            f"V5_RESULTS_PANEL_{label}_BG",
            panel_x,
            panel_y,
            panel_w,
            panel_h,
            fill=fill,
            line=GRID,
        )
        add_box(
            slide,
            f"V5_RESULTS_PANEL_{label}_RULE",
            panel_x,
            panel_y,
            panel_w,
            0.08,
            fill=accent,
        )
    _add_section_heading(
        slide,
        "V5_RESULTS_HEADING",
        y,
        "3 Results — Competitive overall; +5.1 multi-event F1 over EPAL on ChFinAnn",
    )
    _add_line(slide, "V5_RESULTS_SEPARATOR_A_B", 15.37, 26.78, 15.37, 33.48)
    _add_line(slide, "V5_RESULTS_SEPARATOR_B_C", 24.42, 26.78, 24.42, 33.48)

    add_text(
        slide,
        "V5_RESULTS_A_TITLE",
        1.30,
        26.75,
        13.78,
        0.42,
        "A  Overall F1 · listed baselines",
        size=25,
        color=NAVY,
        bold=True,
        margin=0,
    )
    _add_overall_chart(
        slide,
        "CHFINANN",
        "chfinann",
        "ChFinAnn F1 (SARGE: mean ± std, 3 seeds)",
        1.30,
        27.23,
        13.78,
        2.25,
    )
    _add_overall_chart(
        slide,
        "DUEE_FIN",
        "duee_fin",
        "DuEE-Fin F1 (SARGE: mean ± std, 3 seeds)",
        1.30,
        29.62,
        13.78,
        2.25,
    )
    add_text(
        slide,
        "V5_RESULTS_A_PROVENANCE_QUALIFIER",
        1.30,
        32.03,
        13.78,
        0.34,
        "Baselines: reported values [7,10,13,15,18]; SARGE seeds 13/17/42.",
        size=18,
        color=MUTED,
        margin=0,
    )
    add_text(
        slide,
        "V5_RESULTS_A_CAPTION",
        1.30,
        32.42,
        13.78,
        0.84,
        (
            "ChFinAnn: SARGE is numerically above the listed baselines. "
            "DuEE-Fin: SARGE trails SEELE (80.8), while exceeding EPAL and ProCNet."
        ),
        size=20,
        color=MUTED,
        margin=0,
        line_spacing=0.86,
        valign=MSO_ANCHOR.TOP,
    )

    add_text(
        slide,
        "V5_RESULTS_B_TITLE",
        15.62,
        26.75,
        8.52,
        0.46,
        "B  ChFinAnn F1(S.) vs F1(M.)",
        size=25,
        color=NAVY,
        bold=True,
        margin=0,
    )
    _add_multi_event_chart(slide)
    add_box(
        slide,
        "V5_RESULTS_B_HIGHLIGHT_BG",
        16.10,
        30.72,
        7.42,
        1.16,
        fill=WHITE,
        line=GOLD,
        radius=True,
    )
    add_text(
        slide,
        "V5_RESULTS_B_CALLOUT_MULTI",
        15.74,
        30.78,
        8.20,
        0.45,
        f"+{f1_m_gain:.1f} F1(M.)",
        size=26,
        color=TEAL,
        bold=True,
        align=PP_ALIGN.CENTER,
        margin=0,
    )
    add_text(
        slide,
        "V5_RESULTS_B_CALLOUT_GAP",
        15.74,
        31.28,
        8.20,
        0.56,
        f"{gap_reduction:.1f}-point smaller S–M gap",
        size=24,
        color=NAVY,
        bold=True,
        align=PP_ALIGN.CENTER,
        margin=0,
    )
    add_text(
        slide,
        "V5_RESULTS_B_CHART_GAPS",
        15.74,
        31.89,
        8.20,
        0.43,
        f"EPAL gap {epal['gap']:.1f} · SARGE gap {sarge['gap']:.1f}",
        size=20,
        color=MUTED,
        align=PP_ALIGN.CENTER,
        margin=0,
    )
    add_text(
        slide,
        "V5_RESULTS_B_QUALIFIER",
        15.74,
        32.39,
        8.20,
        0.56,
        "Mean over seeds 13/17/42; higher F1(M.) and a smaller S–M gap are better.",
        size=18,
        color=MUTED,
        align=PP_ALIGN.CENTER,
        margin=0,
        line_spacing=0.84,
    )

    add_text(
        slide,
        "V5_RESULTS_C_TITLE",
        24.70,
        26.75,
        8.90,
        0.46,
        "C  Alignment ≠ exact rows",
        size=25,
        color=NAVY,
        bold=True,
        margin=0,
    )
    add_text(
        slide,
        "V5_RESULTS_C_ALIGNMENT_LABEL",
        24.70,
        27.30,
        8.90,
        0.38,
        "Same backend · No SFT → answer-token SFT",
        size=22,
        color=TEAL,
        bold=True,
        margin=0,
    )
    for index, highlight_y in enumerate((27.69, 28.27), start=1):
        add_box(
            slide,
            f"V5_RESULTS_C_ALIGNMENT_HIGHLIGHT_{index}",
            24.82,
            highlight_y,
            8.66,
            0.50,
            fill=WHITE,
            line="B8DDD9" if index == 1 else GRID,
            radius=True,
        )
    for index, row in enumerate(contract.V5_ALIGNMENT_DIAGNOSTICS):
        row_y = 27.75 + index * 0.58
        add_text(
            slide,
            f"V5_RESULTS_C_ALIGNMENT_{index + 1}",
            24.70,
            row_y,
            5.20,
            0.45,
            f"{row['dataset']}  {row['no_sft']:.1f} → {row['sft']:.1f}",
            size=24,
            color=NAVY,
            bold=True,
            margin=0,
        )
        add_text(
            slide,
            f"V5_RESULTS_C_ALIGNMENT_{index + 1}_QUALIFIER",
            29.98,
            row_y,
            3.62,
            0.45,
            f"{row['backend']} · seed {row['seed']}",
            size=18,
            color=MUTED,
            align=PP_ALIGN.RIGHT,
            margin=0,
        )

    add_text(
        slide,
        "V5_RESULTS_C_RECORD_LABEL",
        24.70,
        29.04,
        8.90,
        0.38,
        "Separate 3-seed record diagnostics",
        size=24,
        color=TEAL,
        bold=True,
        margin=0,
    )
    for index, row in enumerate(contract.V5_RECORD_DIAGNOSTICS):
        add_text(
            slide,
            f"V5_RESULTS_C_RECORD_CHART_ROW_{index + 1}",
            24.70,
            29.53 + index * 0.65,
            8.90,
            0.52,
            (
                f"{row['dataset']}  F1 {row['f1']:.1f}  |  "
                f"ExactRec {row['exact_rec']:.1f}  |  Δrecord {row['delta']:.1f}"
            ),
            size=20,
            color=NAVY if index == 0 else TEAL,
            bold=True,
            margin=0,
        )
    add_picture_contain(
        slide,
        "V5_RESULTS_C_DELTA_FORMULA",
        contract.DELTA_RECORD_FORMULA,
        26.24,
        30.89,
        5.82,
        0.48,
        alt_text=r"LaTeX formula: Delta_record equals F1 minus ExactRec",
    )
    add_text(
        slide,
        "V5_RESULTS_C_RECORD_QUALIFIER",
        24.82,
        31.46,
        8.66,
        0.64,
        (
            "3-seed mean. Diagnostic gap, not a pure binding-error estimate; it also "
            "includes missing, extra, wrong values and event-count errors."
        ),
        size=18,
        color=MUTED,
        margin=0,
        line_spacing=0.80,
        valign=MSO_ANCHOR.TOP,
    )
    add_text(
        slide,
        "V5_RESULTS_C_CAPTION",
        24.70,
        32.25,
        8.90,
        0.70,
        "Alignment gains and record-level gaps answer different questions and are reported separately.",
        size=20,
        color=INK,
        margin=0,
        line_spacing=0.84,
        valign=MSO_ANCHOR.TOP,
    )


def _add_conclusion(slide) -> None:
    x, y, w, h = 1.10, 34.10, 32.80, 3.00
    add_box(slide, "V5_CONCLUSION_BAND", x, y, w, h, fill=LIGHT_GRAY)
    add_box(slide, "V5_CONCLUSION_TOP_RULE", x, y, w, 0.08, fill=VIOLET)
    _add_section_heading(
        slide,
        "V5_CONCLUSION_HEADING",
        y,
        "4 Conclusion — One table contract clarifies both gains and limits",
    )
    labels = ("Gain", "Diagnostic", "Boundary")
    column_x = (1.28, 12.18, 23.08)
    fills = (LIGHT_TEAL, LIGHT_VIOLET, LIGHT_CORAL)
    accents = (TEAL, VIOLET, CORAL)
    for index, (label, message, item_x) in enumerate(
        zip(labels, contract.V5_CONCLUSION_MESSAGES, column_x), start=1
    ):
        add_box(
            slide,
            f"V5_CONCLUSION_{index}_BG",
            item_x,
            34.86,
            10.36,
            2.02,
            fill=fills[index - 1],
            line=accents[index - 1],
            radius=True,
        )
        add_text(
            slide,
            f"V5_CONCLUSION_{index}_LABEL",
            item_x + 0.30,
            35.06,
            9.76,
            0.38,
            label,
            size=25,
            color=accents[index - 1],
            bold=True,
            margin=0,
        )
        add_text(
            slide,
            f"V5_CONCLUSION_{index}_TEXT",
            item_x + 0.30,
            35.50,
            9.76,
            1.12,
            message,
            size=22,
            color=INK,
            margin=0,
            line_spacing=0.80,
            valign=MSO_ANCHOR.TOP,
        )


def _set_picture_alt_descriptions(slide) -> None:
    qr = find_shape(slide, "FTR_QR_IMAGE")
    properties = qr._element.nvPicPr.cNvPr
    properties.set(
        "descr",
        f"QR code linking to the SARGE paper and code at {contract.DISPLAY_URL}",
    )
    properties.set("title", "SARGE paper and code QR code")


def build(output: Path = DEFAULT_OUTPUT) -> Path:
    output = Path(output)
    forbidden_outputs = {contract.V2_PPTX.resolve(), contract.V3_PPTX.resolve(), contract.V4_PPTX.resolve()}
    if output.resolve() in forbidden_outputs:
        raise ValueError("v5 output must not overwrite a source or earlier award poster")

    if not contract.V2_PPTX.is_file():
        raise ValueError(f"missing v5 source deck: {contract.V2_PPTX}")
    prs = Presentation(contract.V2_PPTX)
    _preflight_source(prs)
    slide = prs.slides[0]
    protected_before = _protected_shape_signatures(slide)

    delete_named_shapes(slide, set(contract.REMOVE_BODY_SHAPES))
    takehome_shapes = {
        name for name in contract.EDITABLE_HEADER_SHAPES if name.startswith("TAKEHOME_")
    }
    delete_named_shapes(slide, takehome_shapes | {"HDR_CORRESPONDING_SYMBOL"})
    _update_header(slide)
    _add_takehome(slide)
    _add_motivation(slide)
    _add_method(slide)
    _add_results(slide)
    _add_conclusion(slide)
    _set_picture_alt_descriptions(slide)

    if _protected_shape_signatures(slide) != protected_before:
        raise AssertionError("protected conference/footer shape signature changed")

    prs.core_properties.title = " ".join(contract.TITLE.split())
    prs.core_properties.author = "Jiakai Tong; Mengting Qin; Yongqi Hu; Xueyao Wan; Yue Zhao"
    prs.core_properties.subject = "CCKS 2026 award poster, v5 horizontal-band narrative"
    output.parent.mkdir(parents=True, exist_ok=True)
    prs.save(output)
    return output


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    output = build(args.out)
    print(f"saved: {output}")


if __name__ == "__main__":
    main()
