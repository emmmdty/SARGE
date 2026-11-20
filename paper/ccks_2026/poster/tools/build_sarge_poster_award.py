from __future__ import annotations

import argparse
from pathlib import Path

import award_poster_contract as contract
from PIL import Image
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_CONNECTOR, MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, MSO_AUTO_SIZE, PP_ALIGN
from pptx.util import Inches, Pt

FONT = contract.POSTER_FONT

NAVY = "102A56"
BLUE = "145FC2"
CYAN = "00AFC8"
TEAL = "098F88"
VIOLET = "6652C8"
AMBER = "E69A18"
AMBER_DARK = "A86100"
CORAL = "D95849"
GREEN = "27865B"
INK = "17243A"
MUTED = "53647C"
WHITE = "FFFFFF"
PALE_BLUE = "EEF4FC"
PALE_TEAL = "EAF7F4"
PALE_AMBER = "FFF4DE"
PALE_CORAL = "FCEDEA"
PALE_VIOLET = "F1EEFC"
GRID = "CBD7E8"


def rgb(value: str) -> RGBColor:
    return RGBColor.from_string(value)


def set_name(shape, name: str):
    shape.name = name
    return shape


def find_shape(slide, name: str):
    for shape in slide.shapes:
        if shape.name == name:
            return shape
    raise ValueError(f"required source shape not found: {name}")


def delete_named_shapes(slide, names: set[str]) -> None:
    found: set[str] = set()
    for shape in list(slide.shapes):
        if shape.name in names:
            found.add(shape.name)
            shape._element.getparent().remove(shape._element)
    missing = names - found
    if missing:
        raise ValueError(f"removable source shapes not found: {sorted(missing)}")


def set_fill(shape, color: str, transparency: int = 0) -> None:
    shape.fill.solid()
    shape.fill.fore_color.rgb = rgb(color)
    shape.fill.transparency = transparency


def set_line(shape, color: str, width: float = 1.0) -> None:
    shape.line.color.rgb = rgb(color)
    shape.line.width = Pt(width)


def style_run(
    run,
    *,
    size: float,
    color: str = INK,
    bold: bool = False,
    font: str = FONT,
) -> None:
    run.font.name = font
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.color.rgb = rgb(color)


def set_fixed_text(
    shape,
    text: str,
    *,
    size: float,
    color: str = INK,
    bold: bool = False,
    align: PP_ALIGN = PP_ALIGN.LEFT,
    valign: MSO_ANCHOR = MSO_ANCHOR.MIDDLE,
    margin: float = 0.04,
    line_spacing: float = 0.94,
) -> None:
    tf = shape.text_frame
    tf.clear()
    tf.auto_size = MSO_AUTO_SIZE.NONE
    tf.word_wrap = True
    tf.vertical_anchor = valign
    tf.margin_left = Inches(margin)
    tf.margin_right = Inches(margin)
    tf.margin_top = Inches(margin)
    tf.margin_bottom = Inches(margin)
    for index, line in enumerate(text.split("\n")):
        paragraph = tf.paragraphs[0] if index == 0 else tf.add_paragraph()
        paragraph.alignment = align
        paragraph.line_spacing = line_spacing
        paragraph.space_before = Pt(0)
        paragraph.space_after = Pt(0)
        run = paragraph.add_run()
        run.text = line
        style_run(run, size=size, color=color, bold=bold)


def add_text(
    slide,
    name: str,
    x: float,
    y: float,
    w: float,
    h: float,
    text: str,
    *,
    size: float,
    color: str = INK,
    bold: bool = False,
    align: PP_ALIGN = PP_ALIGN.LEFT,
    valign: MSO_ANCHOR = MSO_ANCHOR.MIDDLE,
    margin: float = 0.04,
    line_spacing: float = 0.94,
):
    shape = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    set_name(shape, name)
    set_fixed_text(
        shape,
        text,
        size=size,
        color=color,
        bold=bold,
        align=align,
        valign=valign,
        margin=margin,
        line_spacing=line_spacing,
    )
    return shape


def add_box(
    slide,
    name: str,
    x: float,
    y: float,
    w: float,
    h: float,
    *,
    fill: str,
    line: str | None = None,
    radius: bool = False,
    line_width: float = 1.0,
):
    kind = MSO_SHAPE.ROUNDED_RECTANGLE if radius else MSO_SHAPE.RECTANGLE
    shape = slide.shapes.add_shape(kind, Inches(x), Inches(y), Inches(w), Inches(h))
    set_name(shape, name)
    set_fill(shape, fill)
    if line is None:
        shape.line.fill.background()
    else:
        set_line(shape, line, line_width)
    return shape


def add_picture_contain(
    slide,
    name: str,
    path: Path,
    x: float,
    y: float,
    w: float,
    h: float,
    *,
    alt_text: str,
):
    with Image.open(path) as image:
        image_ratio = image.width / image.height
    box_ratio = w / h
    if image_ratio >= box_ratio:
        picture_w = w
        picture_h = w / image_ratio
    else:
        picture_h = h
        picture_w = h * image_ratio
    picture = slide.shapes.add_picture(
        str(path),
        Inches(x + (w - picture_w) / 2),
        Inches(y + (h - picture_h) / 2),
        Inches(picture_w),
        Inches(picture_h),
    )
    set_name(picture, name)
    properties = picture._element.nvPicPr.cNvPr
    properties.set("descr", alt_text)
    properties.set("title", "LaTeX-rendered formula")
    return picture


def add_rule(slide, name: str, x: float, y: float, w: float, color: str) -> None:
    add_box(slide, name, x, y, w, 0.08, fill=color)


def add_claim_heading(
    slide,
    name: str,
    x: float,
    y: float,
    w: float,
    text: str,
    *,
    size: float = 36,
    color: str = NAVY,
) -> None:
    add_text(
        slide,
        name,
        x,
        y,
        w,
        1.05,
        text,
        size=size,
        color=color,
        bold=True,
        margin=0,
        line_spacing=0.88,
    )


def add_pill(
    slide,
    name: str,
    x: float,
    y: float,
    w: float,
    h: float,
    text: str,
    *,
    fill: str,
    color: str,
    size: float = 24,
) -> None:
    shape = add_box(
        slide,
        f"{name}_BG",
        x,
        y,
        w,
        h,
        fill=fill,
        line=color,
        radius=True,
        line_width=1.2,
    )
    shape.adjustments[0] = 0.18
    add_text(
        slide,
        name,
        x + 0.08,
        y + 0.02,
        w - 0.16,
        h - 0.04,
        text,
        size=size,
        color=color,
        bold=True,
        align=PP_ALIGN.CENTER,
        margin=0.02,
    )


def add_stage(
    slide,
    prefix: str,
    x: float,
    y: float,
    w: float,
    h: float,
    number: str,
    title: str,
    body: str,
    *,
    accent: str,
    fill: str,
    emphasis: bool = False,
    show_body: bool = True,
) -> None:
    add_box(
        slide,
        f"{prefix}_STAGE",
        x,
        y,
        w,
        h,
        fill=fill,
        line=accent,
        radius=False,
        line_width=2.2 if emphasis else 1.2,
    )
    badge = slide.shapes.add_shape(
        MSO_SHAPE.OVAL,
        Inches(x + 0.18),
        Inches(y + 0.18),
        Inches(0.52),
        Inches(0.52),
    )
    set_name(badge, f"{prefix}_NUMBER")
    set_fill(badge, accent)
    set_line(badge, accent, 0.5)
    set_fixed_text(
        badge,
        number,
        size=24,
        color=WHITE,
        bold=True,
        align=PP_ALIGN.CENTER,
        margin=0,
    )
    add_text(
        slide,
        f"{prefix}_TITLE",
        x + 0.80,
        y + 0.14,
        w - 0.98,
        0.72,
        title,
        size=26,
        color=accent,
        bold=True,
        margin=0,
        line_spacing=0.86,
    )
    if show_body:
        add_text(
            slide,
            f"{prefix}_BODY",
            x + 0.22,
            y + 2.50,
            w - 0.44,
            h - 2.72,
            body,
            size=24,
            color=INK,
            align=PP_ALIGN.CENTER,
            valign=MSO_ANCHOR.MIDDLE,
            margin=0,
            line_spacing=0.90,
        )


def add_input_stage_content(slide, prefix: str, x: float, y: float, w: float) -> None:
    icon_w, icon_h = min(1.55, w - 0.70), 1.20
    icon_x = x + (w - icon_w) / 2
    icon = slide.shapes.add_shape(
        MSO_SHAPE.FOLDED_CORNER,
        Inches(icon_x),
        Inches(y + 1.02),
        Inches(icon_w),
        Inches(icon_h),
    )
    set_name(icon, f"{prefix}_ICON")
    set_fill(icon, WHITE)
    set_line(icon, BLUE, 1.8)
    add_picture_contain(
        slide,
        f"{prefix}_INPUT_FORMULA",
        contract.METHOD_INPUT_FORMULA,
        icon_x + 0.16,
        y + 1.30,
        icon_w - 0.32,
        0.48,
        alt_text=r"LaTeX formula: D + \mathcal{S}",
    )
    add_text(
        slide,
        f"{prefix}_BODY",
        x + 0.18,
        y + 2.50,
        w - 0.36,
        1.42,
        "Document\nClosed schema\nOptional cues",
        size=24,
        color=INK,
        align=PP_ALIGN.CENTER,
        margin=0,
        line_spacing=0.88,
    )
    add_picture_contain(
        slide,
        f"{prefix}_OPTIONAL_CUES_FORMULA",
        contract.OPTIONAL_CUES_FORMULA,
        x + 0.38,
        y + 4.12,
        w - 0.76,
        0.62,
        alt_text=r"LaTeX formula: C_{K}(D), P_D",
    )


def add_contract_stage_content(slide, prefix: str, x: float, y: float, w: float) -> None:
    inner_x, inner_y = x + 0.38, y + 1.05
    inner_w, row_h = w - 0.76, 1.25
    add_box(
        slide,
        f"{prefix}_ICON",
        inner_x,
        inner_y,
        inner_w,
        row_h * 3,
        fill=WHITE,
        line=TEAL,
        radius=False,
        line_width=1.8,
    )
    rows = (
        ("✓  type + roles", "Licensed event labels"),
        ("✓  source values", "Copy document strings"),
        ("✓  one row / event", "Preserve row identity"),
    )
    for index, (label, note) in enumerate(rows, 1):
        row_y = inner_y + (index - 1) * row_h
        if index > 1:
            add_box(
                slide,
                f"{prefix}_ROW_{index}_LINE",
                inner_x,
                row_y,
                inner_w,
                0.025,
                fill="A9DDD7",
            )
        add_text(
            slide,
            f"{prefix}_ROW_{index}",
            inner_x + 0.32,
            row_y + 0.13,
            inner_w - 0.64,
            0.44,
            label,
            size=24,
            color=TEAL,
            bold=True,
            margin=0,
        )
        add_text(
            slide,
            f"{prefix}_ROW_{index}_NOTE",
            inner_x + 0.32,
            row_y + 0.66,
            inner_w - 0.64,
            0.36,
            note,
            size=20,
            color=MUTED,
            margin=0,
        )


def add_table_stage_content(slide, prefix: str, x: float, y: float, w: float) -> None:
    table_x, table_y = x + 0.36, y + 1.18
    table_w = w - 0.72
    col_widths = (table_w * 0.34, table_w * 0.33, table_w * 0.33)
    row_heights = (0.72, 1.00, 1.00)
    values = (
        ("type", "r1", "r2"),
        ("e1", "value", "value"),
        ("e2", "value", "value"),
    )
    current_y = table_y
    for row, row_h in enumerate(row_heights):
        current_x = table_x
        for col, col_w in enumerate(col_widths):
            fill = TEAL if row == 0 else WHITE
            color = WHITE if row == 0 else INK
            add_box(
                slide,
                f"{prefix}_TABLE_{row}_{col}_CELL",
                current_x,
                current_y,
                col_w,
                row_h,
                fill=fill,
                line="91D2CB",
                radius=False,
                line_width=1.0,
            )
            add_text(
                slide,
                f"{prefix}_TABLE_{row}_{col}_TEXT",
                current_x + 0.04,
                current_y + 0.02,
                col_w - 0.08,
                row_h - 0.04,
                values[row][col],
                size=24,
                color=color,
                bold=row == 0,
                align=PP_ALIGN.CENTER,
                margin=0,
            )
            current_x += col_w
        current_y += row_h
    add_text(
        slide,
        f"{prefix}_ENDPOINT_NOTE",
        x + 0.30,
        y + 4.02,
        w - 0.60,
        0.82,
        "Preserve dataset labels\nFixed role order · scorer-ready",
        size=20,
        color=MUTED,
        align=PP_ALIGN.CENTER,
        margin=0,
        line_spacing=0.88,
    )


def add_chevron(slide, name: str, x: float, y: float, w: float, h: float) -> None:
    shape = slide.shapes.add_shape(
        MSO_SHAPE.CHEVRON, Inches(x), Inches(y), Inches(w), Inches(h)
    )
    set_name(shape, name)
    set_fill(shape, BLUE)
    shape.line.fill.background()


def add_stage_icon(
    slide,
    prefix: str,
    index: int,
    x: float,
    y: float,
    w: float,
    *,
    accent: str,
) -> None:
    icon_w = min(1.24, w - 0.60)
    icon_x = x + (w - icon_w) / 2
    icon_y = y + 1.05
    if index == 3:
        icon = slide.shapes.add_shape(
            MSO_SHAPE.HEXAGON,
            Inches(icon_x),
            Inches(icon_y),
            Inches(icon_w),
            Inches(1.16),
        )
        set_name(icon, f"{prefix}_ICON")
        set_fill(icon, PALE_BLUE)
        set_line(icon, accent, 1.8)
        set_fixed_text(
            icon,
            "4B",
            size=34,
            color=accent,
            bold=True,
            align=PP_ALIGN.CENTER,
            margin=0,
        )
    elif index == 4:
        icon = slide.shapes.add_shape(
            MSO_SHAPE.FUNNEL,
            Inches(icon_x + 0.10),
            Inches(icon_y),
            Inches(icon_w - 0.20),
            Inches(1.16),
        )
        set_name(icon, f"{prefix}_ICON")
        set_fill(icon, WHITE)
        set_line(icon, accent, 1.8)
    else:
        raise ValueError(f"stage {index} does not use a generic icon")


def add_metric_pair(
    slide,
    prefix: str,
    x: float,
    y: float,
    w: float,
    value: str,
    label: str,
    *,
    color: str,
) -> None:
    add_text(
        slide,
        f"{prefix}_VALUE",
        x,
        y,
        w,
        0.95,
        value,
        size=44,
        color=color,
        bold=True,
        align=PP_ALIGN.CENTER,
        margin=0,
    )
    add_text(
        slide,
        f"{prefix}_LABEL",
        x,
        y + 0.92,
        w,
        0.48,
        label,
        size=24,
        color=MUTED,
        bold=True,
        align=PP_ALIGN.CENTER,
        margin=0,
    )


def add_dumbbell_row(
    slide,
    prefix: str,
    x: float,
    y: float,
    w: float,
    dataset: str,
    f1_value: float,
    exact_value: float,
    delta_value: float,
) -> None:
    add_text(
        slide,
        f"{prefix}_DATASET",
        x,
        y,
        2.55,
        0.72,
        dataset,
        size=26,
        color=NAVY,
        bold=True,
        align=PP_ALIGN.RIGHT,
        margin=0,
    )
    axis_x = x + 3.05
    axis_w = w - 7.25
    axis_y = y + 0.36
    line = slide.shapes.add_connector(
        MSO_CONNECTOR.STRAIGHT,
        Inches(axis_x),
        Inches(axis_y),
        Inches(axis_x + axis_w),
        Inches(axis_y),
    )
    set_name(line, f"{prefix}_CONNECTOR")
    line.line.color.rgb = rgb(GRID)
    line.line.width = Pt(6)
    f1_x = axis_x + axis_w * f1_value / 100
    exact_x = axis_x + axis_w * exact_value / 100
    span = slide.shapes.add_connector(
        MSO_CONNECTOR.STRAIGHT,
        Inches(exact_x),
        Inches(axis_y),
        Inches(f1_x),
        Inches(axis_y),
    )
    set_name(span, f"{prefix}_GAP_CONNECTOR")
    span.line.color.rgb = rgb(VIOLET)
    span.line.width = Pt(8)
    for label, value_x, value, color in (
        ("ExactRec", exact_x, exact_value, VIOLET),
        ("F1", f1_x, f1_value, TEAL),
    ):
        dot = slide.shapes.add_shape(
            MSO_SHAPE.OVAL,
            Inches(value_x - 0.16),
            Inches(axis_y - 0.16),
            Inches(0.32),
            Inches(0.32),
        )
        set_name(dot, f"{prefix}_{label.upper()}_DOT")
        set_fill(dot, color)
        set_line(dot, WHITE, 1.0)
        add_text(
            slide,
            f"{prefix}_{label.upper()}_LABEL",
            value_x - 1.18,
            y + 0.64,
            2.36,
            0.62,
            f"{label} {value:.1f}",
            size=24,
            color=color,
            bold=True,
            align=PP_ALIGN.CENTER,
            margin=0,
        )
    add_pill(
        slide,
        f"{prefix}_DELTA",
        x + w - 3.95,
        y - 0.10,
        3.75,
        0.96,
        f"Δrecord {delta_value:.1f}",
        fill=PALE_VIOLET,
        color=VIOLET,
        size=28,
    )


def preflight_source(prs: Presentation) -> None:
    missing_formula_images = [path for path in contract.FORMULA_IMAGES if not path.is_file()]
    if missing_formula_images:
        raise ValueError(
            "render the LaTeX formula assets first: "
            f"{[str(path) for path in missing_formula_images]}"
        )
    if len(prs.slides) != 1:
        raise ValueError("award source must contain exactly one slide")
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
        raise ValueError(f"source does not satisfy the v2 shape contract: {sorted(missing)}")


def update_header(slide) -> None:
    title = find_shape(slide, "HDR_TITLE")
    title.left = Inches(1.57)
    title.top = Inches(0.96)
    title.width = Inches(20.47)
    title.height = Inches(3.14)
    set_fixed_text(
        title,
        contract.TITLE,
        size=60,
        color=WHITE,
        bold=True,
        valign=MSO_ANCHOR.MIDDLE,
        margin=0,
        line_spacing=0.86,
    )
    takehome = find_shape(slide, "TAKEHOME_TEXT")
    takehome.top = Inches(7.47)
    takehome.height = Inches(1.50)
    set_fixed_text(
        takehome,
        contract.TAKEHOME,
        size=31,
        color=WHITE,
        bold=True,
        margin=0,
        line_spacing=0.88,
    )


def add_problem_region(slide) -> None:
    x, y, w, h = 1.10, 9.65, 10.80, 11.55
    add_box(slide, "AW_PROBLEM_BG", x, y, w, h, fill=PALE_CORAL)
    add_rule(slide, "AW_PROBLEM_DIVIDER", x, y, w, CORAL)
    add_claim_heading(
        slide,
        "AW_PROBLEM_HEADING",
        x + 0.34,
        y + 0.28,
        w - 0.68,
        contract.PROBLEM_HEADING,
        size=35,
        color=NAVY,
    )
    add_text(
        slide,
        "AW_PROBLEM_NOTE",
        x + 0.34,
        y + 1.34,
        w - 0.68,
        0.46,
        "TWO SAME-TYPE EQUITY-PLEDGE EVENTS",
        size=19,
        color=CORAL,
        bold=True,
        margin=0,
    )
    for index, record in enumerate(contract.PROBLEM_RECORDS, 1):
        strip_y = y + 2.00 + (index - 1) * 1.08
        add_box(
            slide,
            f"AW_PROBLEM_RECORD_{index}_STRIP",
            x + 0.34,
            strip_y,
            w - 0.68,
            0.88,
            fill=WHITE,
            line=GRID,
            radius=False,
        )
        add_text(
            slide,
            f"AW_PROBLEM_RECORD_{index}",
            x + 0.54,
            strip_y + 0.04,
            w - 1.08,
            0.80,
            record,
            size=24,
            color=INK,
            bold=True,
            align=PP_ALIGN.CENTER,
            margin=0,
        )
    add_text(
        slide,
        "AW_PROBLEM_PROMPT",
        x + 0.34,
        y + 4.28,
        w - 0.68,
        0.54,
        "Same values. Which row assembly is valid?",
        size=24,
        color=MUTED,
        bold=True,
        align=PP_ALIGN.CENTER,
        margin=0,
    )
    panel_y = y + 5.06
    panel_w = 4.84
    for prefix, panel_x, fill, line, heading, body, status in (
        (
            "AW_PROBLEM_WRONG",
            x + 0.34,
            PALE_CORAL,
            CORAL,
            "×  WRONG",
            "15M | Guotai Junan\n05-20 → 06-04\n\n8M | CITIC\n06-05 → 05-19",
            "Private values cross rows",
        ),
        (
            "AW_PROBLEM_CORRECT",
            x + 5.62,
            PALE_TEAL,
            TEAL,
            "✓  CORRECT",
            "15M | CITIC\n05-20 → 05-19\n\n8M | Guotai Junan\n06-05 → 06-04",
            "Private values stay bound",
        ),
    ):
        add_box(
            slide,
            f"{prefix}_PANEL",
            panel_x,
            panel_y,
            panel_w,
            4.16,
            fill=fill,
            line=line,
            radius=False,
            line_width=1.5,
        )
        add_text(
            slide,
            f"{prefix}_LABEL",
            panel_x + 0.18,
            panel_y + 0.16,
            panel_w - 0.36,
            0.62,
            heading,
            size=26,
            color=line,
            bold=True,
            align=PP_ALIGN.CENTER,
            margin=0,
        )
        add_text(
            slide,
            f"{prefix}_ROWS",
            panel_x + 0.20,
            panel_y + 0.92,
            panel_w - 0.40,
            2.05,
            body,
            size=24,
            color=INK,
            bold=True,
            align=PP_ALIGN.CENTER,
            valign=MSO_ANCHOR.TOP,
            margin=0,
            line_spacing=0.88,
        )
        add_pill(
            slide,
            f"{prefix}_STATUS_CAPTION",
            panel_x + 0.38,
            panel_y + 3.25,
            panel_w - 0.76,
            0.60,
            status,
            fill=WHITE,
            color=line,
            size=22,
        )
    add_text(
        slide,
        "AW_PROBLEM_CAPTION_LABEL",
        x + 0.34,
        y + 9.42,
        w - 0.68,
        0.42,
        "WHY THIS FAILS",
        size=22,
        color=CORAL,
        bold=True,
        align=PP_ALIGN.CENTER,
        margin=0,
    )
    add_text(
        slide,
        "AW_PROBLEM_CAPTION",
        x + 0.54,
        y + 9.90,
        w - 1.08,
        1.02,
        contract.PROBLEM_CAPTION,
        size=22,
        color=NAVY,
        bold=True,
        align=PP_ALIGN.CENTER,
        margin=0,
        line_spacing=0.90,
    )


def add_method_region(slide) -> None:
    x, y, w, h = 12.20, 9.65, 21.70, 11.55
    add_box(slide, "AW_METHOD_BG", x, y, w, h, fill=PALE_BLUE)
    add_rule(slide, "AW_METHOD_DIVIDER", x, y, w, BLUE)
    add_claim_heading(
        slide,
        "AW_METHOD_HEADING",
        x + 0.35,
        y + 0.28,
        w - 0.70,
        contract.METHOD_HEADING,
        size=39,
        color=NAVY,
    )
    add_text(
        slide,
        "AW_METHOD_NOTE",
        x + 0.35,
        y + 1.34,
        w - 0.70,
        0.48,
        "ONE CONTRACT · ONE GENERATION OBJECT · ONE BENCHMARK-COMPATIBLE TABLE",
        size=19,
        color=BLUE,
        bold=True,
        margin=0,
    )
    stage_y = y + 2.03
    stage_h = 5.25
    widths = (2.90, 4.78, 3.46, 3.62, 4.70)
    gap = 0.385
    stage_x = x + 0.35
    accents = (BLUE, TEAL, NAVY, VIOLET, TEAL)
    fills = (WHITE, PALE_TEAL, WHITE, PALE_VIOLET, PALE_TEAL)
    for index, ((title, body), width, accent, fill) in enumerate(
        zip(contract.METHOD_STAGES, widths, accents, fills, strict=True),
        1,
    ):
        prefix = f"AW_METHOD_{index}"
        add_stage(
            slide,
            prefix,
            stage_x,
            stage_y,
            width,
            stage_h,
            str(index),
            title,
            body,
            accent=accent,
            fill=fill,
            emphasis=index in (2, 5),
            show_body=index in (3, 4),
        )
        if index == 1:
            add_input_stage_content(slide, prefix, stage_x, stage_y, width)
        elif index == 2:
            add_contract_stage_content(slide, prefix, stage_x, stage_y, width)
        elif index in (3, 4):
            add_stage_icon(
                slide,
                prefix,
                index,
                stage_x,
                stage_y,
                width,
                accent=accent,
            )
        else:
            add_table_stage_content(slide, prefix, stage_x, stage_y, width)
        if index < 5:
            add_chevron(
                slide,
                f"AW_METHOD_{index}_CONNECTOR",
                stage_x + width + 0.04,
                stage_y + 2.20,
                0.26,
                0.76,
            )
        stage_x += width + gap
    add_text(
        slide,
        "AW_METHOD_ALIGNMENT_CAPTION",
        x + 0.35,
        y + 7.60,
        6.10,
        0.62,
        "Schema-grounded alignment",
        size=22,
        color=NAVY,
        bold=True,
        margin=0,
    )
    add_pill(
        slide,
        "AW_METHOD_ALIGNMENT_1",
        x + 0.35,
        y + 8.35,
        6.55,
        1.17,
        "Licensed labels + row identity",
        fill=PALE_TEAL,
        color=TEAL,
        size=24,
    )
    add_pill(
        slide,
        "AW_METHOD_ALIGNMENT_2",
        x + 7.15,
        y + 8.35,
        6.55,
        1.17,
        "Answer-token SFT + greedy decode",
        fill=WHITE,
        color=BLUE,
        size=24,
    )
    add_pill(
        slide,
        "AW_METHOD_ALIGNMENT_3",
        x + 13.95,
        y + 8.35,
        7.40,
        1.17,
        "Check + normalize fixed slots",
        fill=PALE_VIOLET,
        color=VIOLET,
        size=24,
    )
    add_box(
        slide,
        "AW_METHOD_EVAL_BAR_BG",
        x + 0.35,
        y + 9.76,
        w - 0.70,
        0.82,
        fill=WHITE,
        line=BLUE,
        radius=True,
        line_width=1.2,
    )
    add_text(
        slide,
        "AW_METHOD_EVAL_CAPTION",
        x + 0.55,
        y + 9.80,
        w - 1.10,
        0.72,
        "Normalized fixed-slot table  →  F1 / F1(S.) / F1(M.)  ·  ExactRec  ·  Δrecord",
        size=22,
        color=NAVY,
        bold=True,
        align=PP_ALIGN.CENTER,
        margin=0,
    )


def add_evidence_region(slide) -> None:
    x, y, w, h = 1.10, 21.55, 32.80, 5.55
    add_box(slide, "AW_EVIDENCE_BG", x, y, w, h, fill=WHITE, line=GRID)
    add_rule(slide, "AW_EVIDENCE_TOP_DIVIDER", x, y, w, CYAN)
    add_box(
        slide,
        "AW_EVIDENCE_STORY_BG",
        x,
        y + 0.08,
        w,
        0.50,
        fill=NAVY,
    )
    add_text(
        slide,
        "AW_EVIDENCE_STORY",
        x + 0.20,
        y + 0.08,
        w - 0.40,
        0.50,
        "TWO DATASETS · 43,940 DOCUMENTS · THREE COMPLEMENTARY PROOFS",
        size=24,
        color=WHITE,
        bold=True,
        align=PP_ALIGN.CENTER,
        margin=0,
    )
    module_w = 10.65
    starts = (x + 0.25, x + 11.08, x + 21.91)
    for divider_x in (x + 10.91, x + 21.74):
        line = slide.shapes.add_connector(
            MSO_CONNECTOR.STRAIGHT,
            Inches(divider_x),
            Inches(y + 0.74),
            Inches(divider_x),
            Inches(y + h - 0.34),
        )
        set_name(line, f"AW_EVIDENCE_DIVIDER_{divider_x:.2f}")
        line.line.color.rgb = rgb(GRID)
        line.line.width = Pt(1.4)

    x1 = starts[0]
    add_text(
        slide,
        "AW_EVIDENCE_1_HEADING",
        x1,
        y + 0.70,
        module_w,
        0.72,
        contract.EVIDENCE_MODULES[0]["heading"],
        size=34,
        color=NAVY,
        bold=True,
        align=PP_ALIGN.CENTER,
        margin=0,
    )
    add_metric_pair(
        slide,
        "AW_EVIDENCE_1_CHFINANN",
        x1,
        y + 1.48,
        5.15,
        "85.6 ± 0.4",
        contract.EVIDENCE_MODULES[0]["labels"][0],
        color=TEAL,
    )
    add_metric_pair(
        slide,
        "AW_EVIDENCE_1_DUEEFIN",
        x1 + 5.40,
        y + 1.48,
        5.15,
        "78.3 ± 0.4",
        contract.EVIDENCE_MODULES[0]["labels"][1],
        color=BLUE,
    )
    add_text(
        slide,
        "AW_EVIDENCE_1_INTERPRETATION_CAPTION",
        x1 + 0.15,
        y + 3.02,
        module_w - 0.30,
        2.22,
        contract.EVIDENCE_MODULES[0]["note"],
        size=22,
        color=INK,
        align=PP_ALIGN.CENTER,
        valign=MSO_ANCHOR.MIDDLE,
        margin=0,
        line_spacing=0.92,
    )

    x2 = starts[1]
    add_text(
        slide,
        "AW_EVIDENCE_2_HEADING",
        x2,
        y + 0.70,
        module_w,
        0.72,
        contract.EVIDENCE_MODULES[1]["heading"],
        size=34,
        color=NAVY,
        bold=True,
        align=PP_ALIGN.CENTER,
        margin=0,
    )
    add_metric_pair(
        slide,
        "AW_EVIDENCE_2_F1M",
        x2,
        y + 1.48,
        5.15,
        "81.7 F1(M.)",
        "SARGE 4B · 3-seed mean",
        color=TEAL,
    )
    add_metric_pair(
        slide,
        "AW_EVIDENCE_2_GAP",
        x2 + 5.40,
        y + 1.48,
        5.15,
        "7.5 S–M Gap",
        "smaller degradation",
        color=VIOLET,
    )
    add_pill(
        slide,
        "AW_EVIDENCE_2_EPAL",
        x2 + 1.10,
        y + 3.05,
        module_w - 2.20,
        0.90,
        "EPAL: 76.6 F1(M.) · 13.1 gap",
        fill=PALE_AMBER,
        color=AMBER_DARK,
        size=24,
    )
    add_text(
        slide,
        "AW_EVIDENCE_2_INTERPRETATION_CAPTION",
        x2 + 0.20,
        y + 4.02,
        module_w - 0.40,
        1.26,
        contract.EVIDENCE_MODULES[1]["note"],
        size=22,
        color=INK,
        align=PP_ALIGN.CENTER,
        margin=0,
    )

    x3 = starts[2]
    add_text(
        slide,
        "AW_EVIDENCE_3_HEADING",
        x3,
        y + 0.70,
        module_w,
        0.72,
        contract.EVIDENCE_MODULES[2]["heading"],
        size=34,
        color=NAVY,
        bold=True,
        align=PP_ALIGN.CENTER,
        margin=0,
    )
    add_metric_pair(
        slide,
        "AW_EVIDENCE_3_CHFINANN",
        x3,
        y + 1.48,
        5.15,
        "24.8 → 86.0",
        contract.EVIDENCE_MODULES[2]["labels"][0],
        color=TEAL,
    )
    add_metric_pair(
        slide,
        "AW_EVIDENCE_3_DUEEFIN",
        x3 + 5.40,
        y + 1.48,
        5.15,
        "3.3 → 78.0",
        contract.EVIDENCE_MODULES[2]["labels"][1],
        color=BLUE,
    )
    add_text(
        slide,
        "AW_EVIDENCE_3_INTERPRETATION_CAPTION",
        x3 + 0.15,
        y + 3.02,
        module_w - 0.30,
        2.22,
        contract.EVIDENCE_MODULES[2]["note"],
        size=22,
        color=INK,
        align=PP_ALIGN.CENTER,
        valign=MSO_ANCHOR.MIDDLE,
        margin=0,
        line_spacing=0.92,
    )


def add_bottom_region(slide) -> None:
    x, y, w, h = 1.10, 27.40, 18.70, 10.40
    add_box(slide, "AW_DIAGNOSTIC_BG", x, y, w, h, fill=PALE_VIOLET)
    add_rule(slide, "AW_DIAGNOSTIC_DIVIDER", x, y, w, VIOLET)
    add_claim_heading(
        slide,
        "AW_DIAGNOSTIC_HEADING",
        x + 0.35,
        y + 0.28,
        w - 0.70,
        contract.DIAGNOSTIC_HEADING,
        size=36,
        color=NAVY,
    )
    add_text(
        slide,
        "AW_DIAGNOSTIC_CAPTION",
        x + 0.35,
        y + 1.34,
        w - 0.70,
        0.50,
        "Matched-role F1 can look strong while entire event rows remain inexact.",
        size=22,
        color=INK,
        align=PP_ALIGN.CENTER,
        margin=0,
    )
    add_dumbbell_row(
        slide,
        "AW_DIAGNOSTIC_CHFINANN",
        x + 0.35,
        y + 2.38,
        w - 0.70,
        "ChFinAnn",
        85.6,
        56.1,
        29.5,
    )
    add_dumbbell_row(
        slide,
        "AW_DIAGNOSTIC_DUEEFIN",
        x + 0.35,
        y + 4.68,
        w - 0.70,
        "DuEE-Fin",
        78.3,
        43.3,
        35.1,
    )
    add_box(
        slide,
        "AW_DIAGNOSTIC_INTERPRETATION_BG",
        x + 0.35,
        y + 6.78,
        w - 0.70,
        3.42,
        fill=WHITE,
        line=VIOLET,
        radius=False,
        line_width=1.2,
    )
    add_text(
        slide,
        "AW_DIAGNOSTIC_INTERPRETATION_LABEL",
        x + 0.72,
        y + 7.02,
        6.20,
        0.46,
        "HOW TO READ THE GAP",
        size=24,
        color=VIOLET,
        bold=True,
        align=PP_ALIGN.CENTER,
        margin=0,
    )
    add_picture_contain(
        slide,
        "AW_DIAGNOSTIC_FORMULA_IMAGE",
        contract.DELTA_RECORD_FORMULA,
        x + 0.82,
        y + 7.58,
        6.00,
        0.68,
        alt_text=(
            r"LaTeX formula: \Delta_{\mathrm{record}} = "
            r"F_1 - \mathrm{ExactRec}"
        ),
    )
    add_text(
        slide,
        "AW_DIAGNOSTIC_GAP_GUIDE",
        x + 0.72,
        y + 8.48,
        6.20,
        0.86,
        "Larger gap → more row-level inexactness",
        size=24,
        color=MUTED,
        bold=True,
        align=PP_ALIGN.CENTER,
        margin=0,
        line_spacing=0.92,
    )
    add_box(
        slide,
        "AW_DIAGNOSTIC_INTERPRETATION_LINE",
        x + 7.22,
        y + 7.03,
        0.025,
        2.80,
        fill="C9BFF3",
    )
    add_text(
        slide,
        "AW_DIAGNOSTIC_F1_READING",
        x + 7.58,
        y + 7.02,
        10.30,
        0.60,
        "F1 rewards matched role–value pairs.",
        size=24,
        color=TEAL,
        bold=True,
        margin=0,
    )
    add_text(
        slide,
        "AW_DIAGNOSTIC_EXACT_READING",
        x + 7.58,
        y + 7.72,
        10.30,
        0.60,
        "ExactRec requires every event row to match exactly.",
        size=24,
        color=VIOLET,
        bold=True,
        margin=0,
    )
    add_text(
        slide,
        "AW_DIAGNOSTIC_CAVEAT",
        x + 7.58,
        y + 8.42,
        10.30,
        1.30,
        (
            "The gap is diagnostic—not a pure binding estimate: it also counts "
            "missing, extra, or wrong values and event-count errors."
        ),
        size=24,
        color=INK,
        margin=0,
        line_spacing=0.90,
    )

    x2, w2 = 20.10, 13.80
    add_box(slide, "AW_CONTRIBUTION_BG", x2, y, w2, h, fill=PALE_TEAL)
    add_rule(slide, "AW_CONTRIBUTION_DIVIDER", x2, y, w2, TEAL)
    add_claim_heading(
        slide,
        "AW_CONTRIBUTION_HEADING",
        x2 + 0.35,
        y + 0.28,
        w2 - 0.70,
        "Why the formulation matters",
        size=36,
        color=NAVY,
    )
    contribution_y = y + 1.48
    for index, (label, body) in enumerate(contract.CONTRIBUTIONS, 1):
        row_y = contribution_y + (index - 1) * 1.72
        card = add_box(
            slide,
            f"AW_CONTRIBUTION_{index}_CARD_BG",
            x2 + 0.30,
            row_y,
            w2 - 0.60,
            1.50,
            fill=WHITE,
            line="B8E5DF",
            radius=True,
            line_width=1.0,
        )
        card.adjustments[0] = 0.12
        badge = slide.shapes.add_shape(
            MSO_SHAPE.OVAL,
            Inches(x2 + 0.38),
            Inches(row_y + 0.18),
            Inches(0.58),
            Inches(0.58),
        )
        set_name(badge, f"AW_CONTRIBUTION_{index}_NUMBER")
        set_fill(badge, TEAL)
        set_line(badge, TEAL, 0.5)
        set_fixed_text(
            badge,
            str(index),
            size=24,
            color=WHITE,
            bold=True,
            align=PP_ALIGN.CENTER,
            margin=0,
        )
        add_text(
            slide,
            f"AW_CONTRIBUTION_{index}_LABEL",
            x2 + 1.15,
            row_y + 0.12,
            w2 - 1.55,
            0.44,
            label,
            size=24,
            color=TEAL,
            bold=True,
            margin=0,
        )
        add_text(
            slide,
            f"AW_CONTRIBUTION_{index}_CAPTION",
            x2 + 1.15,
            row_y + 0.56,
            w2 - 1.58,
            0.80,
            body,
            size=22,
            color=INK,
            margin=0,
            line_spacing=0.86,
        )
    add_box(
        slide,
        "AW_BOUNDARY_BG",
        x2 + 0.35,
        y + 6.78,
        w2 - 0.70,
        3.42,
        fill=PALE_CORAL,
        line=CORAL,
        radius=False,
        line_width=2.0,
    )
    add_text(
        slide,
        "AW_BOUNDARY_LABEL",
        x2 + 0.70,
        y + 7.00,
        w2 - 1.40,
        0.44,
        "REMAINING BOUNDARY",
        size=24,
        color=CORAL,
        bold=True,
        align=PP_ALIGN.CENTER,
        margin=0,
    )
    add_text(
        slide,
        "AW_BOUNDARY_TEXT",
        x2 + 0.70,
        y + 7.42,
        w2 - 1.40,
        0.72,
        contract.BOUNDARY,
        size=27,
        color=CORAL,
        bold=True,
        align=PP_ALIGN.CENTER,
        margin=0,
        line_spacing=0.90,
    )
    add_text(
        slide,
        "AW_BOUNDARY_CAPTION",
        x2 + 0.75,
        y + 8.23,
        w2 - 1.50,
        0.88,
        contract.BOUNDARY_DETAIL,
        size=22,
        color=INK,
        align=PP_ALIGN.CENTER,
        margin=0,
        line_spacing=0.88,
    )
    add_text(
        slide,
        "AW_BOUNDARY_NEXT_CAPTION",
        x2 + 0.85,
        y + 9.20,
        w2 - 1.70,
        0.62,
        contract.BOUNDARY_NEXT,
        size=22,
        color=CORAL,
        bold=True,
        align=PP_ALIGN.CENTER,
        margin=0,
        line_spacing=0.88,
    )


def build(output: Path) -> None:
    prs = Presentation(contract.V2_PPTX)
    preflight_source(prs)
    prs.core_properties.title = " ".join(contract.TITLE.split())
    prs.core_properties.author = (
        "Jiakai Tong; Mengting Qin; Yongqi Hu; Xueyao Wan; Yue Zhao"
    )
    prs.core_properties.subject = "CCKS 2026 conference poster"
    slide = prs.slides[0]
    delete_named_shapes(slide, contract.REMOVE_BODY_SHAPES)
    update_header(slide)
    add_problem_region(slide)
    add_method_region(slide)
    add_evidence_region(slide)
    add_bottom_region(slide)
    output.parent.mkdir(parents=True, exist_ok=True)
    prs.save(output)
    print(f"saved: {output}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, default=contract.V3_PPTX)
    args = parser.parse_args()
    build(args.out)


if __name__ == "__main__":
    main()
