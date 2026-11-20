from __future__ import annotations

import argparse
from pathlib import Path

import award_poster_contract as contract
from build_sarge_poster_award import (
    add_box,
    add_picture_contain,
    delete_named_shapes,
    find_shape,
    rgb,
    set_name,
)
from build_sarge_poster_award import (
    style_run as _base_style_run,
)
from pptx import Presentation
from pptx.enum.shapes import MSO_CONNECTOR, MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, MSO_AUTO_SIZE, PP_ALIGN
from pptx.util import Inches, Pt

DEFAULT_OUTPUT = contract.V6_PPTX

FONT = contract.V6_FONT
NAVY = contract.V6_PALETTE["navy"]
TEAL = contract.V6_PALETTE["teal"]
RED = contract.V6_PALETTE["red"]
INK = contract.V6_PALETTE["ink"]
MUTED = contract.V6_PALETTE["muted"]
GRID = contract.V6_PALETTE["grid"]
GRAY = contract.V6_PALETTE["gray"]
LIGHT_GRAY = contract.V6_PALETTE["light_gray"]
LIGHT_TEAL = contract.V6_PALETTE["light_teal"]
LIGHT_RED = contract.V6_PALETTE["light_red"]
WHITE = contract.V6_PALETTE["white"]
PLOT_X = 13.18
PLOT_W = 9.55
PLOT_MIN = 70.0
PLOT_MAX = 95.0


def style_run(
    run,
    *,
    size: int,
    color: str = INK,
    bold: bool = False,
    font: str = FONT,
) -> None:
    _base_style_run(run, size=size, color=color, bold=bold, font=font)


def set_fixed_text(
    shape,
    text: str,
    *,
    size: int,
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
    size: int,
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


def _add_circle(
    slide,
    name: str,
    center_x: float,
    center_y: float,
    diameter: float,
    *,
    fill: str,
    line: str,
    line_width: float = 1.5,
):
    shape = slide.shapes.add_shape(
        MSO_SHAPE.OVAL,
        Inches(center_x - diameter / 2),
        Inches(center_y - diameter / 2),
        Inches(diameter),
        Inches(diameter),
    )
    set_name(shape, name)
    shape.fill.solid()
    shape.fill.fore_color.rgb = rgb(fill)
    shape.line.color.rgb = rgb(line)
    shape.line.width = Pt(line_width)
    return shape


def _add_flow_arrow(
    slide,
    name: str,
    x: float,
    y: float,
    w: float = 0.50,
    h: float = 0.42,
    *,
    color: str = TEAL,
):
    arrow = slide.shapes.add_shape(
        MSO_SHAPE.CHEVRON,
        Inches(x),
        Inches(y),
        Inches(w),
        Inches(h),
    )
    set_name(arrow, name)
    arrow.fill.solid()
    arrow.fill.fore_color.rgb = rgb(color)
    arrow.line.fill.background()
    return arrow


def _add_stage_badge(
    slide,
    name: str,
    letter: str,
    x: float,
    y: float,
    *,
    color: str,
) -> None:
    _add_circle(slide, f"{name}_BADGE", x + 0.24, y + 0.24, 0.48, fill=color, line=color)
    add_text(
        slide,
        f"{name}_LETTER",
        x,
        y + 0.01,
        0.48,
        0.46,
        letter,
        size=20,
        color=WHITE,
        bold=True,
        align=PP_ALIGN.CENTER,
        margin=0,
    )


def _add_grid_icon(
    slide,
    prefix: str,
    x: float,
    y: float,
    w: float,
    h: float,
    *,
    color: str = NAVY,
) -> None:
    border = add_box(slide, f"{prefix}_BORDER", x, y, w, h, fill=WHITE, line=color, line_width=2)
    border.fill.transparency = 100
    for index in (1, 2):
        _add_line(
            slide,
            f"{prefix}_V_{index}",
            x + w * index / 3,
            y,
            x + w * index / 3,
            y + h,
            color=color,
            width=2,
        )
        _add_line(
            slide,
            f"{prefix}_H_{index}",
            x,
            y + h * index / 3,
            x + w,
            y + h * index / 3,
            color=color,
            width=2,
        )


def _add_network_icon(slide, prefix: str, x: float, y: float, *, color: str = NAVY) -> None:
    points = ((x, y + 0.32), (x + 0.52, y), (x + 1.02, y + 0.42), (x + 0.45, y + 0.82))
    edges = ((0, 1), (1, 2), (2, 3), (3, 0), (1, 3))
    for index, (start, end) in enumerate(edges, start=1):
        _add_line(
            slide,
            f"{prefix}_EDGE_{index}",
            points[start][0],
            points[start][1],
            points[end][0],
            points[end][1],
            color=color,
            width=2,
        )
    for index, (cx, cy) in enumerate(points, start=1):
        _add_circle(
            slide,
            f"{prefix}_NODE_{index}",
            cx,
            cy,
            0.28,
            fill=WHITE,
            line=color,
            line_width=2,
        )


def _add_check_icon(slide, prefix: str, x: float, y: float, *, color: str = TEAL) -> None:
    background = add_box(
        slide,
        f"{prefix}_ICON",
        x,
        y,
        1.10,
        0.94,
        fill=WHITE,
        line=color,
        line_width=2,
    )
    background.fill.transparency = 100
    _add_line(slide, f"{prefix}_CHECK_1", x + 0.22, y + 0.52, x + 0.46, y + 0.73, color=color, width=4)
    _add_line(slide, f"{prefix}_CHECK_2", x + 0.46, y + 0.73, x + 0.88, y + 0.25, color=color, width=4)


def _set_shape_text_runs(
    shape,
    segments: tuple[tuple[str, str, bool, float], ...],
    *,
    align: PP_ALIGN = PP_ALIGN.LEFT,
    valign: MSO_ANCHOR = MSO_ANCHOR.MIDDLE,
    margin: float = 0,
    line_spacing: float = 0.88,
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
    paragraph = tf.paragraphs[0]
    paragraph.alignment = align
    paragraph.line_spacing = line_spacing
    paragraph.space_before = Pt(0)
    paragraph.space_after = Pt(0)
    for text, color, bold, size in segments:
        run = paragraph.add_run()
        run.text = text
        style_run(run, size=size, color=color, bold=bold)


def _add_rich_text(
    slide,
    name: str,
    x: float,
    y: float,
    w: float,
    h: float,
    segments: tuple[tuple[str, str, bool, float], ...],
    *,
    align: PP_ALIGN = PP_ALIGN.LEFT,
    valign: MSO_ANCHOR = MSO_ANCHOR.MIDDLE,
    margin: float = 0,
    line_spacing: float = 0.88,
):
    shape = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    set_name(shape, name)
    _set_shape_text_runs(
        shape,
        segments,
        align=align,
        valign=valign,
        margin=margin,
        line_spacing=line_spacing,
    )
    return shape


def _set_table_cell(
    cell,
    text: str,
    *,
    size: float,
    color: str = INK,
    bold: bool = False,
    fill: str = WHITE,
    align: PP_ALIGN = PP_ALIGN.CENTER,
) -> None:
    cell.fill.solid()
    cell.fill.fore_color.rgb = rgb(fill)
    cell.margin_left = Inches(0.05)
    cell.margin_right = Inches(0.05)
    cell.margin_top = Inches(0.03)
    cell.margin_bottom = Inches(0.03)
    tf = cell.text_frame
    tf.clear()
    tf.auto_size = MSO_AUTO_SIZE.NONE
    tf.word_wrap = True
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    paragraph = tf.paragraphs[0]
    paragraph.alignment = align
    paragraph.space_before = Pt(0)
    paragraph.space_after = Pt(0)
    paragraph.line_spacing = 0.88
    run = paragraph.add_run()
    run.text = text
    style_run(run, size=size, color=color, bold=bold)


def _add_table(
    slide,
    name: str,
    x: float,
    y: float,
    w: float,
    h: float,
    rows: tuple[tuple[str, ...], ...],
    *,
    col_widths: tuple[float, ...] | None = None,
    header_fill: str = NAVY,
    header_color: str = WHITE,
    body_fill: str = WHITE,
    header_size: float = 20,
    body_size: float = 20,
):
    shape = slide.shapes.add_table(
        len(rows),
        len(rows[0]),
        Inches(x),
        Inches(y),
        Inches(w),
        Inches(h),
    )
    set_name(shape, name)
    table = shape.table
    if col_widths:
        for column, width in zip(table.columns, col_widths):
            column.width = Inches(width)
    row_height = h / len(rows)
    for row in table.rows:
        row.height = Inches(row_height)
    for row_index, row in enumerate(rows):
        for col_index, text in enumerate(row):
            header = row_index == 0
            _set_table_cell(
                table.cell(row_index, col_index),
                text,
                size=header_size if header else body_size,
                color=header_color if header else INK,
                bold=header,
                fill=header_fill if header else body_fill,
            )
    return shape


def _set_cell_fill(shape, row: int, col: int, fill: str, color: str, *, bold: bool = True) -> None:
    cell = shape.table.cell(row, col)
    text = cell.text
    size = next(
        (
            run.font.size.pt
            for paragraph in cell.text_frame.paragraphs
            for run in paragraph.runs
            if run.text and run.font.size is not None
        ),
        contract.V6_FIGURE_PT,
    )
    _set_table_cell(
        cell,
        text,
        size=size,
        color=color,
        bold=bold,
        fill=fill,
    )


def _section_heading(slide, prefix: str, number: str, title: str, y: float) -> None:
    _add_line(slide, f"{prefix}_DIVIDER", 1.10, y, 33.90, y, color=GRID, width=1.25)
    add_text(
        slide,
        f"{prefix}_NUMBER",
        1.24,
        y + 0.10,
        0.60,
        0.58,
        number,
        size=contract.V6_SECTION_PT,
        color=TEAL,
        bold=True,
        align=PP_ALIGN.CENTER,
        margin=0,
    )
    add_text(
        slide,
        f"{prefix}_HEADING",
        1.98,
        y + 0.10,
        31.70,
        0.58,
        title,
        size=contract.V6_SECTION_PT,
        color=NAVY,
        bold=True,
        margin=0,
    )


def _preflight() -> None:
    for path in (
        contract.V2_PPTX,
        contract.V5_PPTX,
        contract.TEMPLATE_PPTX,
        contract.PAPER_PDF,
        contract.V6_FIG1_PPTX,
        contract.V6_FIG2_PPTX,
        contract.V6_METHOD_INPUT_FORMULA,
        contract.V6_SFT_LOSS_FORMULA,
        contract.V6_DELTA_FORMULA,
    ):
        if not path.is_file():
            raise ValueError(f"missing required poster source: {path}")
    source = Presentation(contract.V2_PPTX)
    v5 = Presentation(contract.V5_PPTX)
    if len(source.slides) != 1 or len(v5.slides) != 1:
        raise ValueError("v6 sources must each contain one slide")
    for prs in (source, v5):
        if abs(prs.slide_width / 360000 - contract.PAGE_CM[0]) >= 0.01:
            raise ValueError("source width does not match the CCKS template")
        if abs(prs.slide_height / 360000 - contract.PAGE_CM[1]) >= 0.01:
            raise ValueError("source height does not match the CCKS template")
    required_v5 = {
        "HDR_TITLE",
        "HDR_AUTHORS",
        "HDR_AFFILIATIONS",
        "FTR_CONFERENCE_TEXT",
        "FTR_QR_IMAGE",
        "FTR_URL",
    }
    names = {shape.name for shape in v5.slides[0].shapes}
    if missing := required_v5 - names:
        raise ValueError(f"v5 metadata source is incomplete: {sorted(missing)}")


def _update_header(slide) -> None:
    title = find_shape(slide, "HDR_TITLE")
    title.left = Inches(1.57)
    title.top = Inches(0.78)
    title.width = Inches(26.40)
    title.height = Inches(3.25)
    set_fixed_text(
        title,
        contract.TITLE,
        size=contract.V6_TITLE_PT,
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
        size=contract.V6_AUTHORS_PT,
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
    set_fixed_text(
        affiliations,
        f"{contract.AFFILIATIONS}\n* Corresponding author: {contract.CONTACT_EMAIL}",
        size=contract.V6_AFFILIATIONS_PT,
        color=WHITE,
        margin=0,
        line_spacing=0.86,
    )


def _update_footer(slide) -> None:
    frame = find_shape(slide, "FTR_QR_FRAME")
    frame.left = Inches(1.72)
    frame.top = Inches(39.34)
    frame.width = Inches(1.94)
    frame.height = Inches(1.94)
    frame.fill.solid()
    frame.fill.fore_color.rgb = rgb(WHITE)
    frame.line.fill.background()

    qr = find_shape(slide, "FTR_QR_IMAGE")
    qr.left = Inches(1.84)
    qr.top = Inches(39.46)
    qr.width = Inches(1.70)
    qr.height = Inches(1.70)
    properties = qr._element.nvPicPr.cNvPr
    properties.set("descr", f"QR code linking to {contract.REPOSITORY_URL}")
    properties.set("title", "SARGE paper and code QR code")

    footer_items = (
        ("FTR_LABEL", 3.96, 39.28, 22, True, "Paper & code"),
        ("FTR_URL", 3.96, 39.92, 18, False, contract.DISPLAY_URL),
        ("FTR_EMAIL", 3.96, 40.50, 18, False, contract.CONTACT_EMAIL),
    )
    for name, x, y, size, bold, text in footer_items:
        shape = find_shape(slide, name)
        shape.left = Inches(x)
        shape.top = Inches(y)
        shape.width = Inches(4.55)
        shape.height = Inches(0.46)
        shape.fill.background()
        shape.line.fill.background()
        set_fixed_text(
            shape,
            text,
            size=size,
            color=WHITE,
            bold=bold,
            margin=0,
        )
    url_shape = find_shape(slide, "FTR_URL")
    url_run = url_shape.text_frame.paragraphs[0].runs[0]
    url_run.hyperlink.address = None
    url_shape.click_action.hyperlink.address = contract.REPOSITORY_URL
    style_run(url_run, size=18, color=WHITE)
    url_run.font.underline = False


def _add_takehome(slide) -> None:
    y, h = contract.V6_BANDS["takehome"]
    add_box(slide, "V6_TAKEHOME_BG", 1.10, y, 32.80, h, fill=LIGHT_GRAY)
    add_box(slide, "V6_TAKEHOME_ACCENT", 1.10, y, 0.16, h, fill=TEAL)
    add_text(
        slide,
        "V6_TAKEHOME_LABEL",
        1.52,
        y + 0.27,
        2.15,
        0.64,
        "TAKE-HOME",
        size=22,
        color=TEAL,
        bold=True,
        margin=0,
    )
    segments = (
        ("Correct argument values can still form the ", INK, True, 27),
        ("wrong event rows", RED, True, 31),
        (". On ChFinAnn, SARGE gains ", INK, True, 27),
        ("5.1 Multi-Event F1 points", TEAL, True, 31),
        (" over EPAL; ", INK, True, 27),
        ("ExactRec", TEAL, True, 30),
        (" reveals complete-row failures beyond role F1.", INK, True, 27),
    )
    _add_rich_text(
        slide,
        "V6_TAKEHOME_TEXT",
        3.88,
        y + 0.08,
        29.55,
        h - 0.16,
        segments,
        margin=0,
        line_spacing=0.82,
    )


def _add_motivation(slide) -> None:
    y, _ = contract.V6_BANDS["motivation"]
    _section_heading(
        slide,
        "V6_MOTIVATION",
        "1",
        "Motivation — Wrong event rows from correct arguments",
        y,
    )
    content_y = y + 0.82
    a_x, a_w = 1.25, 8.35
    b_x, b_w = 10.35, 6.15
    c_x, c_w = 17.30, 16.40

    _add_stage_badge(slide, "V6_MOTIVATION_STAGE_A", "A", a_x, content_y, color=NAVY)
    add_text(slide, "V6_MOTIVATION_STAGE_A_TITLE", a_x + 0.62, content_y, a_w - 0.62, 0.48, contract.V6_MOTIVATION_STAGES[0], size=24, color=NAVY, bold=True, margin=0)
    add_text(slide, "V6_MOTIVATION_SOURCE_SUBTITLE", a_x, content_y + 0.53, a_w, 0.38, "Two same-type equity-pledge events", size=20, color=MUTED, bold=True, margin=0)
    source_table = _add_table(
        slide,
        "V6_MOTIVATION_SOURCE_TABLE",
        a_x,
        content_y + 0.98,
        a_w,
        2.65,
        (
            ("Event", "Shares", "Pledgee", "Period"),
            ("E1", "15M", "CITIC", "20 May 2024 → 19 May 2025"),
            ("E2", "8M", "Guotai Junan", "5 Jun 2024 → 4 Jun 2025"),
        ),
        col_widths=(0.82, 1.12, 2.18, 4.23),
        header_fill=NAVY,
        header_size=18,
        body_size=18,
    )
    for row in (1, 2):
        for col in range(4):
            _set_cell_fill(
                source_table,
                row,
                col,
                LIGHT_TEAL if col in {0, 2} else LIGHT_GRAY,
                TEAL if col in {0, 2} else INK,
                bold=col in {0, 1, 2},
            )

    _add_flow_arrow(slide, "V6_MOTIVATION_ARROW_A_B", 9.76, content_y + 2.02, 0.48, 0.62, color=NAVY)
    _add_stage_badge(slide, "V6_MOTIVATION_STAGE_B", "B", b_x, content_y, color=TEAL)
    add_text(slide, "V6_MOTIVATION_STAGE_B_TITLE", b_x + 0.62, content_y, b_w - 0.62, 0.58, contract.V6_MOTIVATION_STAGES[1], size=23, color=TEAL, bold=True, margin=0)
    pool_values = (
        "15M shares", "8M shares", "CITIC", "Guotai Junan",
        "20 May 2024", "19 May 2025", "5 Jun 2024", "4 Jun 2025",
    )
    for index, value in enumerate(pool_values, start=1):
        col = (index - 1) % 2
        row = (index - 1) // 2
        chip_x = b_x + col * 3.08
        chip_y = content_y + 0.98 + row * 0.66
        chip = add_box(slide, f"V6_MOTIVATION_VALUE_POOL_{index}", chip_x, chip_y, 2.86, 0.48, fill=WHITE, line=TEAL if row == 1 else GRID, line_width=1.2)
        if row == 1:
            chip.fill.fore_color.rgb = rgb(LIGHT_TEAL)
        add_text(slide, f"V6_MOTIVATION_VALUE_POOL_{index}_TEXT", chip_x + 0.06, chip_y + 0.03, 2.74, 0.40, value, size=18, color=TEAL if row == 1 else INK, bold=row < 2, align=PP_ALIGN.CENTER, margin=0)
    add_text(slide, "V6_MOTIVATION_POOL_NOTE", b_x, content_y + 3.60, b_w, 0.42, "Correct values; event membership is lost.", size=19, color=INK, bold=True, align=PP_ALIGN.CENTER, margin=0)

    _add_flow_arrow(slide, "V6_MOTIVATION_ARROW_B_C", 16.67, content_y + 2.02, 0.48, 0.62, color=NAVY)
    _add_stage_badge(slide, "V6_MOTIVATION_STAGE_C", "C", c_x, content_y, color=RED)
    add_text(slide, "V6_MOTIVATION_STAGE_C_TITLE", c_x + 0.62, content_y, c_w - 0.62, 0.48, contract.V6_MOTIVATION_STAGES[2], size=24, color=RED, bold=True, margin=0)
    left_w = 7.85
    right_x = c_x + 8.55
    add_text(slide, "V6_MOTIVATION_WRONG_LABEL", c_x + 0.55, content_y + 0.58, left_w - 0.55, 0.42, "WRONG — CROSS-BOUND", size=22, color=RED, bold=True, align=PP_ALIGN.CENTER, margin=0)
    _add_circle(slide, "V6_MOTIVATION_WRONG_MARKER", c_x + 0.30, content_y + 0.79, 0.42, fill=WHITE, line=RED, line_width=2.5)
    _add_line(slide, "V6_MOTIVATION_WRONG_X_1", c_x + 0.20, content_y + 0.69, c_x + 0.40, content_y + 0.89, color=RED, width=3)
    _add_line(slide, "V6_MOTIVATION_WRONG_X_2", c_x + 0.40, content_y + 0.69, c_x + 0.20, content_y + 0.89, color=RED, width=3)
    add_text(slide, "V6_MOTIVATION_CORRECT_LABEL", right_x + 0.55, content_y + 0.58, left_w - 0.55, 0.42, "CORRECT — ROWS STAY JOINT", size=22, color=TEAL, bold=True, align=PP_ALIGN.CENTER, margin=0)
    _add_circle(slide, "V6_MOTIVATION_CORRECT_MARKER", right_x + 0.30, content_y + 0.79, 0.42, fill=WHITE, line=TEAL, line_width=2.5)
    _add_line(slide, "V6_MOTIVATION_CORRECT_CHECK_1", right_x + 0.19, content_y + 0.79, right_x + 0.27, content_y + 0.87, color=TEAL, width=3)
    _add_line(slide, "V6_MOTIVATION_CORRECT_CHECK_2", right_x + 0.27, content_y + 0.87, right_x + 0.42, content_y + 0.68, color=TEAL, width=3)
    wrong_table = _add_table(
        slide,
        "V6_MOTIVATION_WRONG_TABLE",
        c_x,
        content_y + 1.08,
        left_w,
        2.55,
        (contract.V6_EQUITY_PLEDGE_HEADERS,) + contract.V6_EQUITY_PLEDGE_WRONG_ROWS,
        col_widths=(1.05, 2.35, 2.20, 2.25),
        header_fill=RED,
        header_size=18,
        body_size=18,
    )
    for row in (1, 2):
        _set_cell_fill(wrong_table, row, 1, LIGHT_RED, RED, bold=True)
        _set_cell_fill(wrong_table, row, 3, LIGHT_RED, RED, bold=True)
    correct_table = _add_table(
        slide,
        "V6_MOTIVATION_CORRECT_TABLE",
        right_x,
        content_y + 1.08,
        left_w,
        2.55,
        (contract.V6_EQUITY_PLEDGE_HEADERS,) + contract.V6_EQUITY_PLEDGE_ROWS,
        col_widths=(1.05, 2.35, 2.20, 2.25),
        header_fill=TEAL,
        header_size=18,
        body_size=18,
    )
    for row in (1, 2):
        for col in range(4):
            _set_cell_fill(correct_table, row, col, LIGHT_TEAL, TEAL, bold=col in {0, 1})
    consequence_y = content_y + 4.02
    add_box(slide, "V6_MOTIVATION_CONSEQUENCE_MARKER", 1.25, consequence_y, 0.12, 0.72, fill=RED)
    add_text(slide, "V6_MOTIVATION_CONSEQUENCE", 1.58, consequence_y, 32.12, 0.72, contract.V6_MOTIVATION_CONSEQUENCE, size=23, color=RED, bold=True, margin=0)

    anchor_y = consequence_y + 0.88
    anchor_x = (1.25, 12.10, 22.95)
    for index, ((title, body), item_x) in enumerate(
        zip(contract.V6_MOTIVATION_ANCHORS, anchor_x),
        start=1,
    ):
        if index > 1:
            _add_line(slide, f"V6_MOTIVATION_ANCHOR_{index}_DIVIDER", item_x - 0.36, anchor_y, item_x - 0.36, anchor_y + 1.20, color=GRID)
        _add_circle(slide, f"V6_MOTIVATION_ANCHOR_{index}_MARKER", item_x + 0.22, anchor_y + 0.23, 0.44, fill=NAVY if index == 2 else TEAL, line=NAVY if index == 2 else TEAL)
        add_text(slide, f"V6_MOTIVATION_ANCHOR_{index}_NUMBER", item_x, anchor_y, 0.44, 0.44, str(index), size=18, color=WHITE, bold=True, align=PP_ALIGN.CENTER, margin=0)
        add_text(slide, f"V6_MOTIVATION_ANCHOR_{index}_TITLE", item_x + 0.58, anchor_y, 9.65, 0.40, title, size=21, color=NAVY, bold=True, margin=0)
        add_text(slide, f"V6_MOTIVATION_ANCHOR_{index}_TEXT", item_x + 0.58, anchor_y + 0.42, 9.65, 0.70, body, size=18, color=INK, valign=MSO_ANCHOR.TOP, margin=0, line_spacing=0.82)
    add_text(slide, "V6_MOTIVATION_DESIGN_GOAL", 1.25, y + 7.04, 32.45, 0.38, "Design goal: predict one structured event table with one event per row.", size=20, color=TEAL, bold=True, align=PP_ALIGN.CENTER, margin=0)


def _add_method(slide) -> None:
    y, _ = contract.V6_BANDS["method"]
    _section_heading(
        slide,
        "V6_METHOD",
        "2",
        "Method — Where the contract acts and how rows stay organized",
        y,
    )
    title_y = y + 0.82

    add_text(slide, "V6_METHOD_CONVENTIONAL_TITLE", 1.25, title_y, 11.60, 0.42, "A common role-wise pipeline", size=22, color=NAVY, bold=True, margin=0)
    comparison_y = title_y + 0.50
    comparison_nodes = (
        (1.25, 3.35, contract.V6_CONVENTIONAL_FLOW[0], LIGHT_GRAY, GRID, INK),
        (5.05, 3.55, contract.V6_CONVENTIONAL_FLOW[1], LIGHT_GRAY, GRID, INK),
        (9.05, 3.60, contract.V6_CONVENTIONAL_FLOW[2], LIGHT_RED, RED, RED),
    )
    for index, (node_x, node_w, label, fill, line, color) in enumerate(
        comparison_nodes,
        start=1,
    ):
        add_box(slide, f"V6_METHOD_CONVENTIONAL_{index}_BG", node_x, comparison_y, node_w, 0.62, fill=fill, line=line, line_width=1.4)
        add_text(slide, f"V6_METHOD_CONVENTIONAL_{index}", node_x + 0.12, comparison_y + 0.08, node_w - 0.24, 0.46, label, size=18, color=color, bold=True, align=PP_ALIGN.CENTER, margin=0)
    _add_flow_arrow(slide, "V6_METHOD_CONVENTIONAL_ARROW_1", 4.63, comparison_y + 0.12, 0.36, 0.38, color=GRAY)
    _add_flow_arrow(slide, "V6_METHOD_CONVENTIONAL_ARROW_2", 8.63, comparison_y + 0.12, 0.36, 0.38, color=RED)

    add_text(slide, "V6_METHOD_SARGE_TITLE", 13.35, title_y, 20.35, 0.42, "SARGE: schema-grounded event-table generation", size=24, color=TEAL, bold=True, margin=0)
    add_text(slide, "V6_METHOD_CORE_CHANGE", 13.35, comparison_y, 20.35, 0.62, contract.V6_METHOD_CORE_CHANGE, size=21, color=NAVY, bold=True, margin=0, line_spacing=0.82)

    block_y, block_h = title_y + 1.42, 4.45
    prompt_x, prompt_w = 1.25, 9.10
    sft_x, sft_w = 10.85, 9.25
    decode_x, decode_w = 20.60, 5.65
    output_x, output_w = 26.75, 6.95
    for name, x, width, fill, line in (
        ("PROMPT", prompt_x, prompt_w, LIGHT_TEAL, TEAL),
        ("SFT", sft_x, sft_w, LIGHT_TEAL, TEAL),
        ("DECODE", decode_x, decode_w, LIGHT_GRAY, NAVY),
        ("OUTPUT", output_x, output_w, LIGHT_GRAY, TEAL),
    ):
        add_box(slide, f"V6_METHOD_{name}_BG", x, block_y, width, block_h, fill=fill, line=line, line_width=2)

    add_text(slide, "V6_METHOD_PROMPT_LAYER", prompt_x + 0.22, block_y + 0.10, prompt_w - 0.44, 0.34, "INPUT · PROMPT", size=18, color=TEAL, bold=True, align=PP_ALIGN.CENTER, margin=0)
    add_text(slide, "V6_METHOD_PROMPT_TITLE", prompt_x + 0.22, block_y + 0.44, prompt_w - 0.44, 0.72, "Prompt contract\nSchema-grounded event-table contract", size=22, color=NAVY, bold=True, align=PP_ALIGN.CENTER, margin=0, line_spacing=0.80)
    _add_grid_icon(slide, "V6_METHOD_INPUT_SCHEMA_ICON", prompt_x + 0.36, block_y + 1.42, 1.10, 0.94, color=NAVY)
    add_text(slide, "V6_METHOD_INPUT_DOCUMENT", prompt_x + 1.68, block_y + 1.38, 5.60, 1.02, "Document D · Closed schema S\nBounded C_K(D) · Optional P_D", size=18, color=INK, bold=True, margin=0, line_spacing=0.82)
    contract_icon = slide.shapes.add_shape(MSO_SHAPE.FOLDED_CORNER, Inches(prompt_x + 7.52), Inches(block_y + 1.38), Inches(1.12), Inches(1.02))
    set_name(contract_icon, "V6_METHOD_CONTRACT_ICON")
    contract_icon.fill.solid()
    contract_icon.fill.fore_color.rgb = rgb(WHITE)
    contract_icon.line.color.rgb = rgb(TEAL)
    contract_icon.line.width = Pt(2)
    add_picture_contain(slide, "V6_METHOD_INPUT_FORMULA", contract.V6_METHOD_INPUT_FORMULA, prompt_x + 0.46, block_y + 2.62, prompt_w - 0.92, 0.62, alt_text="LaTeX formula for document, schema, bounded candidates, optional prior, and instruction input")
    add_text(slide, "V6_METHOD_PROMPT_DETAIL", prompt_x + 0.36, block_y + 3.38, prompt_w - 0.72, 0.78, "Schema labels + role definitions · copy source values\none event per row", size=18, color=INK, bold=True, align=PP_ALIGN.CENTER, margin=0, line_spacing=0.82)

    add_text(slide, "V6_METHOD_SFT_LAYER", sft_x + 0.22, block_y + 0.10, sft_w - 0.44, 0.34, "TRAINING", size=18, color=TEAL, bold=True, align=PP_ALIGN.CENTER, margin=0)
    add_text(slide, "V6_METHOD_SFT_TITLE", sft_x + 0.22, block_y + 0.44, sft_w - 0.44, 0.52, contract.V6_METHOD_FLOW[1], size=23, color=NAVY, bold=True, align=PP_ALIGN.CENTER, margin=0)
    add_picture_contain(slide, "V6_METHOD_SFT_FORMULA", contract.V6_SFT_LOSS_FORMULA, sft_x + 0.46, block_y + 1.10, sft_w - 0.92, 0.86, alt_text="LaTeX answer-token supervised fine-tuning loss over the serialized gold event table")
    add_text(slide, "V6_METHOD_SFT_LOSS_NOTE", sft_x + 0.36, block_y + 2.05, sft_w - 0.72, 0.46, "Loss on answer tokens only", size=22, color=TEAL, bold=True, align=PP_ALIGN.CENTER, margin=0)
    add_text(slide, "V6_METHOD_SFT_DETAIL", sft_x + 0.36, block_y + 2.50, sft_w - 0.72, 0.54, "Gold serialized event table = supervised target", size=18, color=INK, bold=True, align=PP_ALIGN.CENTER, margin=0)
    target_table = _add_table(slide, "V6_METHOD_SFT_TARGET_TABLE", sft_x + 0.52, block_y + 3.10, sft_w - 1.04, 1.02, (("Target row", "Joint roles within one event"), ("e1", "type · r1 · r2 · …"), ("e2", "type · r1 · r2 · …")), col_widths=(2.08, 6.13), header_fill=TEAL, header_size=18, body_size=18)
    for row in (1, 2):
        _set_cell_fill(target_table, row, 0, LIGHT_TEAL, TEAL, bold=True)

    add_text(slide, "V6_METHOD_DECODE_LAYER", decode_x + 0.18, block_y + 0.10, decode_w - 0.36, 0.34, "INFERENCE", size=18, color=NAVY, bold=True, align=PP_ALIGN.CENTER, margin=0)
    add_text(slide, "V6_METHOD_DECODE_TITLE", decode_x + 0.18, block_y + 0.44, decode_w - 0.36, 0.70, contract.V6_METHOD_FLOW[2], size=22, color=NAVY, bold=True, align=PP_ALIGN.CENTER, margin=0, line_spacing=0.82)
    _add_network_icon(slide, "V6_METHOD_LLM_ICON", decode_x + 2.30, block_y + 1.45, color=NAVY)
    add_text(slide, "V6_METHOD_DECODE_DETAIL", decode_x + 0.28, block_y + 2.56, decode_w - 0.56, 1.28, "Full tokenizer vocabulary\nNo constrained decoding\nOne candidate / document", size=18, color=INK, bold=True, align=PP_ALIGN.CENTER, margin=0, line_spacing=0.82)

    add_text(slide, "V6_METHOD_OUTPUT_LAYER", output_x + 0.18, block_y + 0.10, output_w - 0.36, 0.34, "POST", size=18, color=TEAL, bold=True, align=PP_ALIGN.CENTER, margin=0)
    add_text(slide, "V6_METHOD_OUTPUT_TITLE", output_x + 0.18, block_y + 0.44, output_w - 0.36, 0.70, contract.V6_METHOD_FLOW[3], size=21, color=TEAL, bold=True, align=PP_ALIGN.CENTER, margin=0, line_spacing=0.82)
    _add_check_icon(slide, "V6_METHOD_SCHEMA_CHECK", output_x + 0.28, block_y + 1.40, color=TEAL)
    row_highlight = add_box(slide, "V6_METHOD_ROW_UNIT_HIGHLIGHT", output_x + 1.56, block_y + 1.66, 4.98, 0.58, fill=WHITE, line=TEAL, line_width=3)
    row_highlight.fill.transparency = 100
    output_table = _add_table(slide, "V6_METHOD_OUTPUT_TABLE", output_x + 1.62, block_y + 1.18, 4.86, 1.62, (("type", "r1", "r2"), ("e1", "value", "value"), ("e2", "value", "value")), col_widths=(1.16, 1.85, 1.85), header_fill=TEAL, header_size=18, body_size=18)
    for row in (1, 2):
        for col in range(3):
            _set_cell_fill(output_table, row, col, LIGHT_TEAL if row == 1 else WHITE, INK, bold=col == 0)
    add_text(slide, "V6_METHOD_CHECK_DETAIL", output_x + 0.28, block_y + 2.96, output_w - 0.56, 0.78, contract.V6_VALIDATION_NOTE, size=18, color=INK, align=PP_ALIGN.CENTER, margin=0, line_spacing=0.80)
    add_text(slide, "V6_METHOD_ROW_UNIT_LABEL", output_x + 0.28, block_y + 3.78, output_w - 0.56, 0.42, "Highlighted row = one event record", size=18, color=TEAL, bold=True, align=PP_ALIGN.CENTER, margin=0)

    for index, arrow_x in enumerate((10.39, 20.14, 26.29), start=1):
        _add_flow_arrow(slide, f"V6_METHOD_FLOW_ARROW_{index}", arrow_x, block_y + 1.92, 0.42, 0.56, color=TEAL)

    annotation_y = block_y + 4.68
    annotation_items = (
        ("Schema closure", "Schema-defined types, roles, and slots specify valid output structure."),
        ("Source grounding", "Bounded document candidates + copy instructions provide cues; no hard lexical filter."),
        ("Row identity", "The serialized table is the prediction object; each row groups one event's roles."),
    )
    for index, (heading, detail) in enumerate(annotation_items, start=1):
        item_x = 1.25 + (index - 1) * 10.86
        if index > 1:
            _add_line(slide, f"V6_METHOD_ANNOTATION_{index}_DIVIDER", item_x - 0.34, annotation_y, item_x - 0.34, annotation_y + 0.92, color=GRID)
        add_text(slide, f"V6_METHOD_ANNOTATION_{index}_TITLE", item_x, annotation_y, 10.20, 0.34, heading, size=20, color=TEAL, bold=True, margin=0)
        add_text(slide, f"V6_METHOD_ANNOTATION_{index}_TEXT", item_x, annotation_y + 0.36, 10.20, 0.62, detail, size=18, color=INK, valign=MSO_ANCHOR.TOP, margin=0, line_spacing=0.82)

    add_text(slide, "V6_METHOD_GROUNDING_NOTE", 1.25, y + 8.02, 26.10, 0.66, contract.V6_GROUNDING_NOTE, size=18, color=NAVY, bold=True, margin=0, line_spacing=0.82)
    add_text(slide, "V6_METHOD_IMPLEMENTATION", 27.72, y + 8.12, 5.98, 0.34, contract.V6_IMPLEMENTATION, size=18, color=MUTED, align=PP_ALIGN.RIGHT, margin=0)
    add_text(slide, "V6_METHOD_MECHANISM", 1.25, y + 8.72, 32.45, 0.34, contract.V6_METHOD_MECHANISM, size=19, color=TEAL, bold=True, align=PP_ALIGN.CENTER, margin=0)


def multi_event_x(value: float) -> float:
    return PLOT_X + (value - PLOT_MIN) / (PLOT_MAX - PLOT_MIN) * PLOT_W


def _add_results(slide) -> None:
    y, _ = contract.V6_BANDS["results"]
    _section_heading(
        slide,
        "V6_RESULTS",
        "3",
        "Results — Where SARGE improves and what ExactRec reveals",
        y,
    )
    panel_y = y + 0.82
    a_x, a_w = 1.25, 9.35
    b_x, b_w = 11.00, 12.60
    c_x, c_w = 24.05, 9.65
    _add_line(slide, "V6_RESULTS_A_B_DIVIDER", 10.78, panel_y, 10.78, y + 7.25, color=GRID)
    _add_line(slide, "V6_RESULTS_B_C_DIVIDER", 23.82, panel_y, 23.82, y + 7.25, color=GRID)

    add_text(
        slide,
        "V6_RESULTS_A_TITLE",
        a_x,
        panel_y,
        a_w,
        0.50,
        "A  Overall position among representative baselines",
        size=23,
        color=NAVY,
        bold=True,
        margin=0,
    )
    overall_rows = [("Model", "ChFinAnn F1", "DuEE-Fin F1")]
    for row in contract.V6_OVERALL_F1:
        model = f"{row['model']} {row['citation']}".strip()
        if row["model"] == "SARGE":
            ch = f"{row['chfinann']:.1f} ± {row['std']['chfinann']:.1f}"
            du = f"{row['duee_fin']:.1f} ± {row['std']['duee_fin']:.1f}"
        else:
            ch = f"{row['chfinann']:.1f}"
            du = f"{row['duee_fin']:.1f}"
        overall_rows.append((model, ch, du))
    overall_table = _add_table(
        slide,
        "V6_RESULTS_A_TABLE",
        a_x,
        panel_y + 0.62,
        a_w,
        3.76,
        tuple(overall_rows),
        col_widths=(3.45, 2.95, 2.95),
        header_fill=NAVY,
        header_size=18,
        body_size=18,
    )
    sarge_row = len(overall_rows) - 1
    seele_row = next(index for index, row in enumerate(overall_rows) if row[0].startswith("SEELE"))
    for col in range(3):
        _set_cell_fill(overall_table, sarge_row, col, LIGHT_TEAL, TEAL, bold=True)
    _set_cell_fill(overall_table, seele_row, 2, LIGHT_GRAY, NAVY, bold=True)
    add_text(
        slide,
        "V6_RESULTS_A_INTERPRETATION",
        a_x,
        panel_y + 4.52,
        a_w,
        0.46,
        "ChFinAnn · 85.6 ± 0.4 · highest listed",
        size=21,
        color=TEAL,
        bold=True,
        valign=MSO_ANCHOR.TOP,
        margin=0,
        line_spacing=0.84,
    )
    add_text(slide, "V6_RESULTS_A_DUEE_NOTE", a_x, panel_y + 5.10, a_w, 0.46, "DuEE-Fin · 78.3 ± 0.4 · below SEELE 80.8", size=20, color=NAVY, bold=True, margin=0)
    add_text(slide, "V6_RESULTS_A_SEEDS", a_x, panel_y + 5.72, a_w, 0.42, "Mean ± std over seeds 13/17/42", size=18, color=MUTED, margin=0)
    add_text(
        slide,
        "V6_RESULTS_B_TITLE",
        b_x,
        panel_y,
        b_w,
        0.52,
        "B  Single-Event vs Multi-Event F1 · ChFinAnn",
        size=25,
        color=NAVY,
        bold=True,
        margin=0,
    )
    add_text(
        slide,
        "V6_RESULTS_B_SUBTITLE",
        b_x,
        panel_y + 0.50,
        8.10,
        0.42,
        "○ Single-Event F1 · ● Multi-Event F1",
        size=18,
        color=MUTED,
        margin=0,
    )
    add_text(slide, "V6_RESULTS_B_AXIS_NOTE", b_x + 8.42, panel_y + 0.50, 4.18, 0.36, "ZOOMED AXIS 70–95", size=18, color=NAVY, bold=True, align=PP_ALIGN.RIGHT, margin=0)
    plot_top = panel_y + 1.06
    axis_y = panel_y + 3.34
    _add_line(slide, "V6_RESULTS_B_AXIS", PLOT_X, axis_y, PLOT_X + PLOT_W, axis_y, color=GRAY, width=1.3)
    for index, offset in enumerate((-0.13, -0.03), start=1):
        _add_line(
            slide,
            f"V6_RESULTS_B_AXIS_BREAK_{index}",
            PLOT_X + offset,
            axis_y + 0.09,
            PLOT_X + offset + 0.08,
            axis_y - 0.09,
            color=NAVY,
            width=1.7,
        )
    for tick in (70, 75, 80, 85, 90, 95):
        tick_x = multi_event_x(tick)
        _add_line(
            slide,
            f"V6_RESULTS_B_TICK_LINE_{tick}",
            tick_x,
            plot_top + 0.12,
            tick_x,
            axis_y,
            color=GRID,
            width=0.8,
        )
        add_text(
            slide,
            f"V6_RESULTS_B_TICK_{tick}",
            tick_x - 0.35,
            axis_y + 0.08,
            0.70,
            0.34,
            str(tick),
            size=20,
            color=MUTED,
            align=PP_ALIGN.CENTER,
            margin=0,
        )
    row_y = {"EPAL": plot_top + 0.68, "SARGE": plot_top + 1.62}
    row_color = {"EPAL": GRAY, "SARGE": TEAL}
    for row in contract.V6_MULTI_EVENT:
        model = row["model"]
        y_row = row_y[model]
        color = row_color[model]
        add_text(
            slide,
            f"V6_RESULTS_B_{model.upper()}_LABEL",
            b_x,
            y_row - 0.20,
            1.35,
            0.42,
            model,
            size=22,
            color=NAVY if model == "EPAL" else TEAL,
            bold=True,
            margin=0,
        )
        x_multi = multi_event_x(row["multi"])
        x_single = multi_event_x(row["single"])
        _add_line(
            slide,
            f"V6_RESULTS_B_{model.upper()}_CONNECTOR",
            x_multi,
            y_row,
            x_single,
            y_row,
            color=color,
            width=3.0 if model == "SARGE" else 2.0,
        )
        _add_circle(
            slide,
            f"V6_RESULTS_B_{model.upper()}_MULTI_MARKER",
            x_multi,
            y_row,
            0.28,
            fill=color,
            line=color,
            line_width=2.0,
        )
        _add_circle(
            slide,
            f"V6_RESULTS_B_{model.upper()}_SINGLE_MARKER",
            x_single,
            y_row,
            0.28,
            fill=WHITE,
            line=color,
            line_width=2.2,
        )
        add_text(
            slide,
            f"V6_RESULTS_B_{model.upper()}_MULTI_VALUE",
            x_multi - 0.62,
            y_row + 0.18,
            1.24,
            0.38,
            f"{row['multi']:.1f}",
            size=22,
            color=color,
            bold=True,
            align=PP_ALIGN.CENTER,
            margin=0,
        )
        single_value = f"{row['single']:.1f}"
        if model == "SARGE":
            single_value += " ± 0.7"
        add_text(
            slide,
            f"V6_RESULTS_B_{model.upper()}_SINGLE_VALUE",
            x_single - 0.85,
            y_row - 0.58,
            1.70,
            0.38,
            single_value,
            size=20,
            color=color,
            bold=True,
            align=PP_ALIGN.CENTER,
            margin=0,
        )
    add_text(
        slide,
        "V6_RESULTS_B_GAIN",
        b_x,
        panel_y + 3.82,
        b_w,
        0.58,
        "5.1 points over EPAL on ChFinAnn",
        size=36,
        color=TEAL,
        bold=True,
        align=PP_ALIGN.CENTER,
        margin=0,
    )
    add_text(
        slide,
        "V6_RESULTS_B_GAP",
        b_x,
        panel_y + 4.48,
        b_w,
        0.52,
        "Single-to-Multi gap: 13.1 → 7.5, reduced by 5.6",
        size=23,
        color=NAVY,
        bold=True,
        align=PP_ALIGN.CENTER,
        margin=0,
    )
    add_text(
        slide,
        "V6_RESULTS_B_DEFINITION",
        b_x + 0.25,
        panel_y + 5.06,
        b_w - 0.50,
        0.60,
        contract.V6_MULTI_EVENT_DEFINITION,
        size=21,
        color=INK,
        bold=True,
        align=PP_ALIGN.CENTER,
        margin=0,
    )
    add_text(
        slide,
        "V6_RESULTS_B_EVIDENCE_BOUNDARY",
        b_x + 0.25,
        panel_y + 5.70,
        b_w - 0.50,
        0.68,
        contract.V6_EVIDENCE_SCOPE,
        size=18,
        color=NAVY,
        bold=True,
        align=PP_ALIGN.CENTER,
        margin=0,
    )
    add_text(slide, "V6_RESULTS_B_PROVENANCE", b_x + 0.25, panel_y + 6.40, b_w - 0.50, 0.36, "Multi-Event F1 = 81.7 ± 0.1 (3-seed mean).", size=18, color=MUTED, align=PP_ALIGN.CENTER, margin=0)

    add_text(
        slide,
        "V6_RESULTS_C_TITLE",
        c_x,
        panel_y,
        c_w,
        0.52,
        "C  What does ExactRec reveal?",
        size=23,
        color=NAVY,
        bold=True,
        margin=0,
    )
    add_text(
        slide,
        "V6_RESULTS_C_DEFINITION",
        c_x,
        panel_y + 0.50,
        c_w,
        0.48,
        contract.V6_EXACTREC_DEFINITION,
        size=20,
        color=TEAL,
        bold=True,
        margin=0,
    )
    add_box(slide, "V6_RESULTS_C_ROLE_F1_BG", c_x, panel_y + 0.98, 4.58, 0.78, fill=LIGHT_GRAY, line=GRID, line_width=1.4)
    add_text(slide, "V6_RESULTS_C_ROLE_F1_QUESTION", c_x + 0.16, panel_y + 1.05, 4.26, 0.64, f"ROLE F1\n{contract.V6_ROLE_F1_QUESTION}", size=18, color=NAVY, bold=True, align=PP_ALIGN.CENTER, margin=0, line_spacing=0.80)
    add_box(slide, "V6_RESULTS_C_EXACTREC_BG", c_x + 4.82, panel_y + 0.98, 4.83, 0.78, fill=LIGHT_TEAL, line=TEAL, line_width=1.4)
    add_text(slide, "V6_RESULTS_C_EXACTREC_QUESTION", c_x + 4.98, panel_y + 1.05, 4.51, 0.64, f"EXACTREC\n{contract.V6_EXACTREC_QUESTION}", size=18, color=TEAL, bold=True, align=PP_ALIGN.CENTER, margin=0, line_spacing=0.80)
    add_picture_contain(slide, "V6_RESULTS_C_FORMULA", contract.V6_DELTA_FORMULA, c_x + 0.30, panel_y + 1.84, c_w - 0.60, 0.48, alt_text="LaTeX formula defining the F1 minus ExactRec diagnostic gap")
    record_rows = [("Dataset", "Role F1", "ExactRec", contract.V6_DIAGNOSTIC_COLUMN)]
    for row in contract.V6_RECORD_DIAGNOSTICS:
        gap = f"{row['gap']:.1f}"
        if row["dataset"] == "DuEE-Fin":
            gap += "†"
        record_rows.append(
            (
                row["dataset"],
                f"{row['role_f1']:.1f}",
                f"{row['exact_rec']:.1f}",
                gap,
            )
        )
    record_table = _add_table(
        slide,
        "V6_RESULTS_C_TABLE",
        c_x,
        panel_y + 2.42,
        c_w,
        1.65,
        tuple(record_rows),
        col_widths=(2.30, 1.70, 1.90, 3.75),
        header_fill=NAVY,
        header_size=18,
        body_size=20,
    )
    for row in (1, 2):
        _set_cell_fill(record_table, row, 2, LIGHT_TEAL, TEAL, bold=True)
        _set_cell_fill(record_table, row, 3, LIGHT_GRAY, NAVY, bold=True)
    add_box(
        slide,
        "V6_RESULTS_C_CAVEAT_BG",
        c_x,
        panel_y + 4.20,
        c_w,
        1.05,
        fill=LIGHT_GRAY,
        line=NAVY,
    )
    add_text(
        slide,
        "V6_RESULTS_C_CAVEAT",
        c_x + 0.20,
        panel_y + 4.30,
        c_w - 0.40,
        0.82,
        contract.V6_EXACTREC_CAVEAT,
        size=19,
        color=INK,
        bold=True,
        valign=MSO_ANCHOR.TOP,
        margin=0,
        line_spacing=0.82,
    )
    add_text(
        slide,
        "V6_RESULTS_C_GAP_NOTE",
        c_x,
        panel_y + 5.36,
        c_w,
        0.40,
        contract.V6_DUEE_GAP_NOTE,
        size=18,
        color=MUTED,
        valign=MSO_ANCHOR.TOP,
        margin=0,
        line_spacing=0.82,
    )
    add_text(slide, "V6_RESULTS_C_INTERPRETATION", c_x, panel_y + 5.82, c_w, 0.72, "Together, the metrics separate ‘found the right fields’ from ‘assembled the right record.’", size=19, color=NAVY, bold=True, valign=MSO_ANCHOR.TOP, margin=0, line_spacing=0.82)

def _add_conclusion(slide) -> None:
    y, _ = contract.V6_BANDS["conclusion"]
    _section_heading(
        slide,
        "V6_CONCLUSION",
        "4",
        "Conclusion — Prediction unit, diagnostic, and scope",
        y,
    )
    col_x = (1.25, 11.88, 22.50)
    col_w = (10.10, 10.10, 11.20)
    content_y = y + 0.86
    for index, ((label, message), x, width) in enumerate(
        zip(contract.V6_CONCLUSION, col_x, col_w),
        start=1,
    ):
        add_text(
            slide,
            f"V6_CONCLUSION_{index}_LABEL",
            x,
            content_y,
            width,
            0.42,
            label,
            size=24,
            color=RED if index == 3 else TEAL,
            bold=True,
            margin=0,
        )
        add_text(
            slide,
            f"V6_CONCLUSION_{index}_TEXT",
            x,
            content_y + 0.48,
            width,
            1.25,
            message,
            size=22 if index < 3 else 20,
            color=INK,
            valign=MSO_ANCHOR.TOP,
            margin=0,
            line_spacing=0.82,
        )
        if index < 3:
            _add_line(
                slide,
                f"V6_CONCLUSION_{index}_DIVIDER",
                x + width + 0.26,
                content_y,
                x + width + 0.26,
                content_y + 1.78,
                color=GRID,
            )


def build(output: Path = DEFAULT_OUTPUT) -> Path:
    output = Path(output)
    forbidden = {
        contract.V2_PPTX.resolve(),
        contract.V3_PPTX.resolve(),
        contract.V4_PPTX.resolve(),
        contract.V5_PPTX.resolve(),
        contract.TEMPLATE_PPTX.resolve(),
    }
    if output.resolve() in forbidden:
        raise ValueError("v6 output must not overwrite a source poster or template")
    _preflight()
    prs = Presentation(contract.V2_PPTX)
    slide = prs.slides[0]
    delete_named_shapes(slide, set(contract.REMOVE_BODY_SHAPES))
    delete_named_shapes(
        slide,
        {
            "TAKEHOME_FRAME",
            "TAKEHOME_LABEL_BOX",
            "TAKEHOME_LABEL",
            "TAKEHOME_TEXT",
            "HDR_CORRESPONDING_SYMBOL",
        },
    )
    _update_header(slide)
    _update_footer(slide)
    _add_takehome(slide)
    _add_motivation(slide)
    _add_method(slide)
    _add_results(slide)
    _add_conclusion(slide)
    prs.core_properties.title = " ".join(contract.TITLE.split())
    prs.core_properties.author = "Jiakai Tong; Mengting Qin; Yongqi Hu; Xueyao Wan; Yue Zhao"
    prs.core_properties.subject = "CCKS 2026 award poster, v6 publication-accurate scientific narrative"
    output.parent.mkdir(parents=True, exist_ok=True)
    prs.save(output)
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the SARGE CCKS 2026 v6 poster")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    print(f"saved: {build(args.out)}")


if __name__ == "__main__":
    main()
