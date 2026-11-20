from __future__ import annotations

from pathlib import Path

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.dml import MSO_LINE_DASH_STYLE
from pptx.enum.shapes import MSO_CONNECTOR, MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Inches, Pt


ROOT = Path(__file__).resolve().parents[4]
OUT_DIR = ROOT / "paper/ccks_2026/poster"
TEMPLATE = OUT_DIR / "template/CCKS2026-poster参考模板.pptx"
QR_IMAGE = OUT_DIR / "assets/github_repository_qr.png"
REPOSITORY_URL = "github.com/emmmdty/SARGE"

NAVY = "102A56"
BLUE = "125FD1"
CYAN = "00AFC8"
TEAL = "0BA7A1"
TEAL_DARK = "087E7A"
VIOLET = "6048C8"
AMBER = "F2A11F"
CORAL = "E85C4A"
GREEN = "2C9B63"
INK = "162238"
MUTED = "5D6B82"
LIGHT_TEXT = "DDE7F8"
PANEL = "F7F9FD"
BLUE_TINT = "EEF4FF"
TEAL_TINT = "EAF8F6"
AMBER_TINT = "FFF5DF"
CORAL_TINT = "FDEDEA"
GRID = "D9E2F1"
WHITE = "FFFFFF"
GRAY = "9AA8BC"
LIGHT_GRAY = "EDF1F7"


def rgb(value: str) -> RGBColor:
    return RGBColor.from_string(value)


def delete_shape(shape) -> None:
    shape._element.getparent().remove(shape._element)


def set_shape_fill(shape, color: str, transparency: int = 0) -> None:
    shape.fill.solid()
    shape.fill.fore_color.rgb = rgb(color)
    shape.fill.transparency = transparency


def set_shape_line(
    shape,
    color: str,
    width: float = 1.2,
    dash: MSO_LINE_DASH_STYLE | None = None,
) -> None:
    shape.line.color.rgb = rgb(color)
    shape.line.width = Pt(width)
    if dash is not None:
        shape.line.dash_style = dash


def style_run(
    run,
    *,
    size: float,
    color: str = INK,
    bold: bool = False,
    font: str,
) -> None:
    run.font.name = font
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.color.rgb = rgb(color)


def write_text(
    shape,
    text: str,
    *,
    size: float,
    color: str = INK,
    bold: bool = False,
    font: str,
    align: PP_ALIGN = PP_ALIGN.LEFT,
    valign: MSO_ANCHOR = MSO_ANCHOR.MIDDLE,
    margin: float = 0.08,
    line_spacing: float = 1.0,
) -> None:
    tf = shape.text_frame
    tf.clear()
    tf.word_wrap = True
    tf.vertical_anchor = valign
    tf.margin_left = Inches(margin)
    tf.margin_right = Inches(margin)
    tf.margin_top = Inches(margin)
    tf.margin_bottom = Inches(margin)
    lines = text.split("\n")
    for index, line in enumerate(lines):
        p = tf.paragraphs[0] if index == 0 else tf.add_paragraph()
        p.alignment = align
        p.line_spacing = line_spacing
        p.space_after = Pt(0)
        run = p.add_run()
        run.text = line
        style_run(run, size=size, color=color, bold=bold, font=font)


def add_text(
    slide,
    x: float,
    y: float,
    w: float,
    h: float,
    text: str,
    *,
    size: float,
    font: str,
    color: str = INK,
    bold: bool = False,
    align: PP_ALIGN = PP_ALIGN.LEFT,
    valign: MSO_ANCHOR = MSO_ANCHOR.MIDDLE,
    margin: float = 0.05,
    line_spacing: float = 1.0,
):
    shape = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    write_text(
        shape,
        text,
        size=size,
        font=font,
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
    x: float,
    y: float,
    w: float,
    h: float,
    *,
    fill: str = WHITE,
    line: str = GRID,
    radius: bool = True,
    line_width: float = 1.2,
):
    kind = MSO_SHAPE.ROUNDED_RECTANGLE if radius else MSO_SHAPE.RECTANGLE
    shape = slide.shapes.add_shape(kind, Inches(x), Inches(y), Inches(w), Inches(h))
    set_shape_fill(shape, fill)
    set_shape_line(shape, line, line_width)
    return shape


def add_badge(
    slide,
    x: float,
    y: float,
    w: float,
    h: float,
    text: str,
    *,
    fill: str,
    color: str,
    font: str,
    size: float = 20,
):
    shape = add_box(slide, x, y, w, h, fill=fill, line=fill)
    write_text(
        shape,
        text,
        size=size,
        font=font,
        color=color,
        bold=True,
        align=PP_ALIGN.CENTER,
        margin=0.03,
    )
    return shape


def add_panel(
    slide,
    x: float,
    y: float,
    w: float,
    h: float,
    number: str,
    title: str,
    *,
    font: str,
    accent: str = BLUE,
):
    panel = add_box(slide, x, y, w, h, fill=WHITE, line=GRID, line_width=1.4)
    circle = slide.shapes.add_shape(
        MSO_SHAPE.OVAL, Inches(x + 0.34), Inches(y + 0.28), Inches(0.58), Inches(0.58)
    )
    set_shape_fill(circle, accent)
    set_shape_line(circle, accent, 0.8)
    write_text(
        circle,
        number,
        size=21,
        font=font,
        color=WHITE,
        bold=True,
        align=PP_ALIGN.CENTER,
        margin=0,
    )
    add_text(
        slide,
        x + 1.02,
        y + 0.2,
        w - 1.35,
        0.72,
        title,
        size=30,
        font=font,
        color=NAVY,
        bold=True,
        margin=0,
    )
    line_shape = slide.shapes.add_shape(
        MSO_SHAPE.RECTANGLE,
        Inches(x + 0.34),
        Inches(y + 0.98),
        Inches(w - 0.68),
        Inches(0.06),
    )
    set_shape_fill(line_shape, accent)
    set_shape_line(line_shape, accent, 0)
    return panel


def add_arrow(slide, x1: float, y1: float, x2: float, y2: float, color: str = BLUE):
    connector = slide.shapes.add_connector(
        MSO_CONNECTOR.STRAIGHT,
        Inches(x1),
        Inches(y1),
        Inches(x2),
        Inches(y2),
    )
    connector.line.color.rgb = rgb(color)
    connector.line.width = Pt(2.2)
    connector.line.end_arrowhead = True
    return connector


def add_node(
    slide,
    x: float,
    y: float,
    w: float,
    h: float,
    title: str,
    subtitle: str,
    *,
    font: str,
    accent: str,
    fill: str,
):
    node = add_box(slide, x, y, w, h, fill=fill, line=accent, line_width=1.4)
    add_text(
        slide,
        x + 0.16,
        y + 0.12,
        w - 0.32,
        0.52,
        title,
        size=24,
        font=font,
        color=accent,
        bold=True,
        align=PP_ALIGN.CENTER,
        margin=0,
    )
    add_text(
        slide,
        x + 0.16,
        y + 0.7,
        w - 0.32,
        h - 0.82,
        subtitle,
        size=19,
        font=font,
        color=INK,
        align=PP_ALIGN.CENTER,
        margin=0.02,
        line_spacing=0.9,
    )
    return node


def add_horizontal_bar(
    slide,
    x: float,
    y: float,
    w: float,
    label: str,
    value: float,
    *,
    max_value: float,
    color: str,
    font: str,
    label_size: float = 18,
):
    add_text(
        slide,
        x,
        y,
        2.25,
        0.33,
        label,
        size=label_size,
        font=font,
        color=MUTED,
        bold=False,
        margin=0,
    )
    bg = slide.shapes.add_shape(
        MSO_SHAPE.ROUNDED_RECTANGLE,
        Inches(x + 2.35),
        Inches(y + 0.04),
        Inches(w - 3.2),
        Inches(0.22),
    )
    set_shape_fill(bg, LIGHT_GRAY)
    set_shape_line(bg, LIGHT_GRAY, 0)
    bar_width = max(0.25, (w - 3.2) * value / max_value)
    bar = slide.shapes.add_shape(
        MSO_SHAPE.ROUNDED_RECTANGLE,
        Inches(x + 2.35),
        Inches(y + 0.04),
        Inches(bar_width),
        Inches(0.22),
    )
    set_shape_fill(bar, color)
    set_shape_line(bar, color, 0)
    add_text(
        slide,
        x + w - 0.72,
        y - 0.02,
        0.7,
        0.36,
        f"{value:.1f}",
        size=18,
        font=font,
        color=color,
        bold=True,
        align=PP_ALIGN.RIGHT,
        margin=0,
    )


def add_vertical_bar(
    slide,
    x: float,
    base_y: float,
    w: float,
    max_h: float,
    value: float,
    *,
    min_value: float,
    max_value: float,
    color: str,
    label: str,
    font: str,
):
    height = max_h * (value - min_value) / (max_value - min_value)
    height = max(0.12, height)
    bar = slide.shapes.add_shape(
        MSO_SHAPE.ROUNDED_RECTANGLE,
        Inches(x),
        Inches(base_y - height),
        Inches(w),
        Inches(height),
    )
    set_shape_fill(bar, color)
    set_shape_line(bar, color, 0)
    add_text(
        slide,
        x - 0.1,
        base_y - height - 0.42,
        w + 0.2,
        0.36,
        f"{value:.1f}",
        size=18,
        font=font,
        color=color,
        bold=True,
        align=PP_ALIGN.CENTER,
        margin=0,
    )
    add_text(
        slide,
        x - 0.5,
        base_y + 0.04,
        w + 1.0,
        0.72,
        label,
        size=15,
        font=font,
        color=MUTED,
        align=PP_ALIGN.CENTER,
        valign=MSO_ANCHOR.TOP,
        margin=0,
        line_spacing=0.86,
    )


def add_metric(
    slide,
    x: float,
    y: float,
    w: float,
    value: str,
    label: str,
    *,
    font: str,
    color: str,
    fill: str,
):
    card = add_box(slide, x, y, w, 1.55, fill=fill, line=color, line_width=1.3)
    add_text(
        slide,
        x + 0.14,
        y + 0.11,
        w - 0.28,
        0.72,
        value,
        size=31,
        font=font,
        color=color,
        bold=True,
        align=PP_ALIGN.CENTER,
        margin=0,
    )
    add_text(
        slide,
        x + 0.14,
        y + 0.82,
        w - 0.28,
        0.54,
        label,
        size=17,
        font=font,
        color=MUTED,
        align=PP_ALIGN.CENTER,
        margin=0,
        line_spacing=0.9,
    )
    return card


def add_comparison_card(
    slide,
    x: float,
    y: float,
    w: float,
    dataset: str,
    sarge_value: str,
    baseline_value: str,
    delta: str,
    *,
    font: str,
    accent: str,
    fill: str,
    delta_fill: str,
):
    card = add_box(slide, x, y, w, 1.38, fill=fill, line=accent, line_width=1.25)
    add_text(
        slide,
        x + 0.18,
        y + 0.13,
        2.25,
        0.42,
        dataset,
        size=18,
        font=font,
        color=NAVY,
        bold=True,
        margin=0,
    )
    add_text(
        slide,
        x + 0.18,
        y + 0.62,
        3.25,
        0.44,
        baseline_value,
        size=15,
        font=font,
        color=MUTED,
        margin=0,
    )
    add_text(
        slide,
        x + 3.3,
        y + 0.2,
        3.1,
        0.7,
        sarge_value,
        size=26,
        font=font,
        color=accent,
        bold=True,
        align=PP_ALIGN.CENTER,
        margin=0,
    )
    badge = add_box(
        slide,
        x + w - 2.2,
        y + 0.28,
        1.8,
        0.72,
        fill=delta_fill,
        line=delta_fill,
    )
    write_text(
        badge,
        delta,
        size=21,
        font=font,
        color=accent,
        bold=True,
        align=PP_ALIGN.CENTER,
        margin=0,
    )
    return card


def add_lollipop_row(
    slide,
    x: float,
    y: float,
    w: float,
    label: str,
    value: float,
    *,
    min_value: float,
    max_value: float,
    color: str,
    font: str,
):
    add_text(
        slide,
        x,
        y - 0.18,
        2.05,
        0.46,
        label,
        size=16,
        font=font,
        color=NAVY,
        bold=True,
        align=PP_ALIGN.RIGHT,
        margin=0,
    )
    axis_x = x + 2.35
    axis_w = w - 3.45
    line = slide.shapes.add_connector(
        MSO_CONNECTOR.STRAIGHT,
        Inches(axis_x),
        Inches(y),
        Inches(axis_x + axis_w),
        Inches(y),
    )
    line.line.color.rgb = rgb(GRID)
    line.line.width = Pt(2)
    point_x = axis_x + axis_w * (value - min_value) / (max_value - min_value)
    dot = slide.shapes.add_shape(
        MSO_SHAPE.OVAL,
        Inches(point_x - 0.15),
        Inches(y - 0.15),
        Inches(0.3),
        Inches(0.3),
    )
    set_shape_fill(dot, color)
    set_shape_line(dot, WHITE, 1.2)
    add_text(
        slide,
        point_x + 0.2,
        y - 0.22,
        0.9,
        0.5,
        f"{value:.1f}",
        size=18,
        font=font,
        color=color,
        bold=True,
        margin=0,
    )


def add_lollipop_axis(
    slide,
    x: float,
    y: float,
    w: float,
    *,
    min_value: float,
    max_value: float,
    ticks: list[float],
    font: str,
):
    axis_x = x + 2.35
    axis_w = w - 3.45
    for tick in ticks:
        tick_x = axis_x + axis_w * (tick - min_value) / (max_value - min_value)
        mark = slide.shapes.add_connector(
            MSO_CONNECTOR.STRAIGHT,
            Inches(tick_x),
            Inches(y - 0.09),
            Inches(tick_x),
            Inches(y + 0.09),
        )
        mark.line.color.rgb = rgb(MUTED)
        mark.line.width = Pt(1)
        add_text(
            slide,
            tick_x - 0.35,
            y + 0.1,
            0.7,
            0.36,
            f"{tick:g}",
            size=13,
            font=font,
            color=MUTED,
            align=PP_ALIGN.CENTER,
            margin=0,
        )


def add_dot_row(
    slide,
    x: float,
    y: float,
    w: float,
    text: str,
    *,
    font: str,
    color: str = INK,
    size: float = 20,
):
    dot = slide.shapes.add_shape(
        MSO_SHAPE.OVAL, Inches(x), Inches(y + 0.11), Inches(0.17), Inches(0.17)
    )
    set_shape_fill(dot, CYAN)
    set_shape_line(dot, CYAN, 0)
    add_text(
        slide,
        x + 0.3,
        y,
        w - 0.3,
        0.48,
        text,
        size=size,
        font=font,
        color=color,
        margin=0,
    )


def replace_template_header(prs: Presentation, lang: str, font: str) -> None:
    slide = prs.slides[0]
    for shape in list(slide.shapes):
        if getattr(shape, "has_text_frame", False):
            text = shape.text.strip()
            if "文章标题放在这里" in text:
                shape.left = Inches(1.55)
                shape.top = Inches(1.18)
                shape.width = Inches(22.7)
                shape.height = Inches(2.45)
                title = (
                    "SARGE：面向中文金融文档级事件抽取的\nSchema 引导式事件表生成"
                    if lang == "zh"
                    else "SARGE: Schema-Grounded Event-Table Generation\n"
                    "for Chinese Financial Document-Level\nEvent Extraction"
                )
                if lang == "en":
                    shape.width = Inches(20.7)
                    shape.top = Inches(0.98)
                    shape.height = Inches(2.8)
                write_text(
                    shape,
                    title,
                    size=68 if lang == "zh" else 50,
                    font=font,
                    color=WHITE,
                    bold=True,
                    valign=MSO_ANCHOR.MIDDLE,
                    margin=0,
                    line_spacing=0.9,
                )
            elif "张三" in text:
                shape.left = Inches(1.62)
                shape.top = Inches(3.94)
                shape.width = Inches(23.0)
                shape.height = Inches(0.62)
                authors = (
                    "童佳锴¹² · 覃梦婷¹ · 扈永琪¹ · 万雪瑶¹² · 赵悦¹² ✉"
                    if lang == "zh"
                    else "Jiakai Tong¹² · Mengting Qin¹ · Yongqi Hu¹ · Xueyao Wan¹² · Yue Zhao¹² ✉"
                )
                write_text(
                    shape,
                    authors,
                    size=29 if lang == "zh" else 26,
                    font=font,
                    color="FFF1A8",
                    bold=True,
                    margin=0,
                )
            elif "作者联系" in text:
                delete_shape(shape)
        if shape.name == "Graphic 18":
            delete_shape(shape)

    affiliation = (
        "¹ 哈尔滨工业大学航天学院　² 哈尔滨工业大学郑州研究院　"
        if lang == "zh"
        else "¹ School of Astronautics, Harbin Institute of Technology　"
        "² Zhengzhou Advanced Research Institute, Harbin Institute of Technology"
    )
    add_text(
        slide,
        1.62,
        4.57,
        23.0,
        0.78,
        affiliation,
        size=20 if lang == "zh" else 17,
        font=font,
        color=LIGHT_TEXT,
        margin=0,
    )


def add_footer(slide, lang: str, font: str) -> None:
    add_box(
        slide,
        1.72,
        39.25,
        2.15,
        2.15,
        fill=WHITE,
        line=WHITE,
        line_width=1.8,
    )
    slide.shapes.add_picture(
        str(QR_IMAGE),
        Inches(1.77),
        Inches(39.30),
        width=Inches(2.05),
        height=Inches(2.05),
    )
    add_text(
        slide,
        4.1,
        39.22,
        4.2,
        0.58,
        "代码与论文" if lang == "zh" else "Code & paper",
        size=22,
        font=font,
        color="8EF4EA",
        bold=True,
        margin=0,
    )
    add_text(
        slide,
        4.1,
        39.9,
        4.2,
        1.05,
        f"{REPOSITORY_URL}\n"
        "yue.zhao@hit.edu.cn"
        if lang == "zh"
        else f"{REPOSITORY_URL}\n"
        "yue.zhao@hit.edu.cn",
        size=17,
        font=font,
        color=WHITE,
        margin=0,
        line_spacing=0.9,
    )


def add_takeaway(slide, lang: str, font: str) -> None:
    add_box(slide, 1.1, 7.38, 32.8, 2.24, fill=NAVY, line=NAVY)
    label = "核心结论" if lang == "zh" else "TAKE-HOME MESSAGE"
    add_badge(
        slide,
        1.48,
        7.78,
        3.2,
        0.55,
        label,
        fill=CYAN,
        color=NAVY,
        font=font,
        size=19,
    )
    text = (
        "SARGE 以 Schema 契约直接生成事件表；在报告 F1(S.)/F1(M.) 的可比系统中，"
        "多事件退化最小，并用 ExactRec 显式暴露剩余行组装差距。"
        if lang == "zh"
        else "SARGE generates event tables under a schema contract; among comparable systems "
        "reporting F1(S.)/F1(M.), it degrades least on multi-event documents, while ExactRec "
        "exposes remaining row-assembly errors."
    )
    add_text(
        slide,
        5.08,
        7.65,
        28.25,
        1.62,
        text,
        size=28 if lang == "zh" else 24,
        font=font,
        color=WHITE,
        bold=True,
        margin=0,
        line_spacing=0.93,
    )


def add_problem_panel(slide, lang: str, font: str) -> None:
    title = (
        "为什么难：角色值正确，事件行仍可错绑"
        if lang == "zh"
        else "Why it is hard: correct roles, wrong rows"
    )
    add_panel(slide, 1.1, 10.02, 10.6, 11.55, "1", title, font=font, accent=CORAL)

    row_a = add_box(slide, 1.45, 11.38, 9.9, 1.22, fill=BLUE_TINT, line=BLUE)
    row_b = add_box(slide, 1.45, 12.8, 9.9, 1.22, fill=TEAL_TINT, line=TEAL)
    text_a = (
        "记录 A　15,000,000 股｜中信证券｜2024-05-20 → 2025-05-19"
        if lang == "zh"
        else "Record A · 15,000,000 shares\nCITIC · 2024-05-20 → 2025-05-19"
    )
    text_b = (
        "记录 B　 8,000,000 股｜国泰君安｜2024-06-05 → 2025-06-04"
        if lang == "zh"
        else "Record B · 8,000,000 shares\nGuotai Junan · 2024-06-05 → 2025-06-04"
    )
    write_text(row_a, text_a, size=19 if lang == "zh" else 17, font=font, color=INK, bold=True)
    write_text(row_b, text_b, size=19 if lang == "zh" else 17, font=font, color=INK, bold=True)

    add_badge(
        slide,
        1.52,
        14.38,
        3.05,
        0.58,
        "共享论元" if lang == "zh" else "Shared arguments",
        fill=LIGHT_GRAY,
        color=NAVY,
        font=font,
        size=17,
    )
    add_badge(
        slide,
        4.78,
        14.38,
        6.42,
        0.58,
        "私有值：股数 · 质权人 · 日期"
        if lang == "zh"
        else "Private values: shares · pledgee · dates",
        fill=AMBER_TINT,
        color="9A6400",
        font=font,
        size=16,
    )

    add_text(
        slide,
        1.5,
        15.15,
        9.65,
        0.5,
        "角色值抽对 ≠ 事件行组装正确"
        if lang == "zh"
        else "Recovering values ≠ assembling coherent event rows",
        size=23 if lang == "zh" else 19,
        font=font,
        color=CORAL,
        bold=True,
        align=PP_ALIGN.CENTER,
        margin=0,
    )

    add_text(
        slide,
        1.5,
        15.83,
        4.45,
        0.46,
        "错误预测 / WRONG" if lang == "zh" else "Predicted events / WRONG",
        size=19,
        font=font,
        color=CORAL,
        bold=True,
        align=PP_ALIGN.CENTER,
        margin=0,
    )
    add_text(
        slide,
        6.78,
        15.83,
        4.25,
        0.46,
        "正确记录 / CORRECT" if lang == "zh" else "Gold events / CORRECT",
        size=19,
        font=font,
        color=GREEN,
        bold=True,
        align=PP_ALIGN.CENTER,
        margin=0,
    )
    wrong = add_box(slide, 1.5, 16.42, 4.45, 3.85, fill=CORAL_TINT, line=CORAL)
    correct = add_box(slide, 6.78, 16.42, 4.25, 3.85, fill=TEAL_TINT, line=GREEN)
    wrong_text = (
        "15M｜国泰君安｜05-20 → 06-04　×\n\n"
        " 8M｜中信证券｜06-05 → 05-19　×"
        if lang == "zh"
        else "15M | Guotai Junan | 05/20→06/04  ×\n\n"
        " 8M | CITIC | 06/05→05/19  ×"
    )
    correct_text = (
        "15M｜中信证券｜05-20 → 05-19　✓\n\n"
        " 8M｜国泰君安｜06-05 → 06-04　✓"
        if lang == "zh"
        else "15M | CITIC | 05/20→05/19  ✓\n\n"
        " 8M | Guotai Junan | 06/05→06/04  ✓"
    )
    write_text(
        wrong,
        wrong_text,
        size=18 if lang == "zh" else 16,
        font=font,
        color=CORAL,
        bold=True,
        align=PP_ALIGN.CENTER,
        margin=0.18,
        line_spacing=0.9,
    )
    write_text(
        correct,
        correct_text,
        size=18 if lang == "zh" else 16,
        font=font,
        color=GREEN,
        bold=True,
        align=PP_ALIGN.CENTER,
        margin=0.18,
        line_spacing=0.9,
    )
    add_arrow(slide, 5.98, 18.35, 6.68, 18.35, color=AMBER)
    add_text(
        slide,
        1.52,
        20.45,
        9.65,
        0.62,
        "同类型事件共享公有论元；短小、重复或分散的私有值决定记录边界。"
        if lang == "zh"
        else "Same-type events share public arguments; short, repeated, or distributed private values define row identity.",
        size=16 if lang == "zh" else 15,
        font=font,
        color=MUTED,
        align=PP_ALIGN.CENTER,
        margin=0,
    )


def add_method_panel(slide, lang: str, font: str) -> None:
    title = (
        "SARGE：把 Schema 变成事件表输出契约"
        if lang == "zh"
        else "SARGE: render the schema as an event-table output contract"
    )
    add_panel(slide, 12.05, 10.02, 21.85, 11.55, "2", title, font=font, accent=CYAN)

    nodes = [
        (
            "输入" if lang == "zh" else "Inputs",
            "文档 D\n封闭 Schema S\n源值候选 Cₖ(D)"
            if lang == "zh"
            else "Document D\nclosed schema S\nsurface candidates Cₖ(D)",
            BLUE,
            BLUE_TINT,
        ),
        (
            "输出契约" if lang == "zh" else "Output contract",
            "合法类型 / 角色\n复制原文值\n一条事件一行"
            if lang == "zh"
            else "licensed types / roles\ncopy source values\none event per row",
            NAVY,
            BLUE_TINT,
        ),
        (
            "微调 LLM" if lang == "zh" else "Tuned LLM",
            "pθ(Y｜D,S)\n答案 token 监督\n贪心解码"
            if lang == "zh"
            else "pθ(Y | D,S)\nanswer-token loss\ngreedy decoding",
            CYAN,
            TEAL_TINT,
        ),
        (
            "Schema 校验" if lang == "zh" else "Schema check",
            "过滤非法类型 / 角色\n移除空字段\n固定角色顺序"
            if lang == "zh"
            else "filter invalid types / roles\nremove empty fields\nfixed role order",
            TEAL_DARK,
            TEAL_TINT,
        ),
        (
            "固定槽位事件表" if lang == "zh" else "Fixed-slot table",
            "type｜r₁｜r₂｜…\ne₁｜value｜value\ne₂｜value｜value"
            if lang == "zh"
            else "type | r₁ | r₂ | …\ne₁ | value | value\ne₂ | value | value",
            BLUE,
            BLUE_TINT,
        ),
        (
            "评测与诊断" if lang == "zh" else "Evaluation",
            "Role F1\nExactRec\nΔrecord"
            if lang == "zh"
            else "Role F1\nExactRec\nΔrecord",
            AMBER,
            AMBER_TINT,
        ),
    ]
    xs = [12.55, 19.35, 26.15]
    for index, node in enumerate(nodes[:3]):
        add_node(
            slide,
            xs[index],
            11.42,
            6.1,
            3.12,
            node[0],
            node[1],
            font=font,
            accent=node[2],
            fill=node[3],
        )
    for index, node in enumerate(nodes[3:]):
        x = xs[2 - index]
        add_node(
            slide,
            x,
            16.05,
            6.1,
            3.12,
            node[0],
            node[1],
            font=font,
            accent=node[2],
            fill=node[3],
        )
    add_arrow(slide, 18.75, 12.98, 19.25, 12.98, color=BLUE)
    add_arrow(slide, 25.55, 12.98, 26.05, 12.98, color=BLUE)
    add_arrow(slide, 29.2, 14.62, 29.2, 15.95, color=TEAL)
    add_arrow(slide, 26.05, 17.62, 25.55, 17.62, color=TEAL)
    add_arrow(slide, 19.25, 17.62, 18.75, 17.62, color=TEAL)

    badge_labels = (
        ["Schema closure", "Copy surface values", "One event per row", "Deterministic decode"]
        if lang == "en"
        else ["封闭 Schema", "复制原文表面值", "一条事件一行", "确定性解码"]
    )
    badge_widths = [3.9, 4.7, 4.3, 4.4]
    cursor = 12.55
    fills = [BLUE_TINT, TEAL_TINT, AMBER_TINT, BLUE_TINT]
    colors = [BLUE, TEAL_DARK, "9A6400", NAVY]
    for label, width, fill, color in zip(badge_labels, badge_widths, fills, colors):
        add_badge(
            slide,
            cursor,
            19.65,
            width,
            0.62,
            label,
            fill=fill,
            color=color,
            font=font,
            size=16,
        )
        cursor += width + 0.28

    add_text(
        slide,
        12.62,
        20.48,
        20.7,
        0.52,
        "统一预测对象：可直接进入基准评测器的固定槽位事件行"
        if lang == "zh"
        else "One prediction object: benchmark-compatible fixed-slot event rows",
        size=19 if lang == "zh" else 17,
        font=font,
        color=NAVY,
        bold=True,
        align=PP_ALIGN.CENTER,
        margin=0,
    )


def add_results_panels(slide, lang: str, font: str) -> None:
    add_panel(
        slide,
        1.1,
        21.93,
        10.25,
        9.25,
        "3",
        "三种子主要结果" if lang == "zh" else "Three-seed main results",
        font=font,
        accent=BLUE,
    )
    add_metric(
        slide,
        1.5,
        23.25,
        4.45,
        "85.6±0.4",
        "ChFinAnn Role F1",
        font=font,
        color=BLUE,
        fill=BLUE_TINT,
    )
    add_metric(
        slide,
        6.2,
        23.25,
        4.75,
        "78.3±0.4",
        "DuEE-Fin Role F1",
        font=font,
        color=TEAL_DARK,
        fill=TEAL_TINT,
    )
    add_text(
        slide,
        1.52,
        25.08,
        9.4,
        0.46,
        "与最强总体基线的直接差值" if lang == "zh" else "Direct delta to the strongest aggregate baseline",
        size=18,
        font=font,
        color=MUTED,
        bold=True,
        margin=0,
    )
    add_comparison_card(
        slide,
        1.5,
        25.62,
        9.45,
        "ChFinAnn",
        "SARGE 85.6",
        "SEELE 85.1",
        "Δ +0.5",
        font=font,
        accent=BLUE,
        fill=BLUE_TINT,
        delta_fill="DCEAFF",
    )
    add_comparison_card(
        slide,
        1.5,
        27.22,
        9.45,
        "DuEE-Fin",
        "SARGE 78.3",
        "SEELE 80.8",
        "Δ −2.5",
        font=font,
        accent=CORAL,
        fill=CORAL_TINT,
        delta_fill="FAD9D4",
    )
    add_text(
        slide,
        1.55,
        28.92,
        9.25,
        1.38,
        "ChFinAnn：数值上高于已列基线\n"
        "DuEE-Fin：低于 SEELE，高于 EPAL / ProCNet"
        if lang == "zh"
        else "ChFinAnn: numerically above listed baselines\n"
        "DuEE-Fin: below SEELE, above EPAL / ProCNet",
        size=18 if lang == "zh" else 16,
        font=font,
        color=INK,
        bold=True,
        align=PP_ALIGN.CENTER,
        margin=0.05,
        line_spacing=0.95,
    )

    add_panel(
        slide,
        11.65,
        21.93,
        10.25,
        9.25,
        "4",
        "多事件鲁棒性" if lang == "zh" else "Multi-event robustness",
        font=font,
        accent=TEAL,
    )
    add_metric(
        slide,
        12.05,
        23.25,
        4.45,
        "81.7±0.1",
        "ChFinAnn F1(M.) · SARGE 4B",
        font=font,
        color=TEAL_DARK,
        fill=TEAL_TINT,
    )
    add_metric(
        slide,
        16.78,
        23.25,
        4.65,
        "7.5 pts",
        "SARGE S–M gap · EPAL 13.1",
        font=font,
        color=AMBER,
        fill=AMBER_TINT,
    )
    add_text(
        slide,
        12.1,
        25.05,
        9.35,
        0.45,
        "ChFinAnn F1(M.) · 72–84 shown explicitly"
        if lang == "en"
        else "ChFinAnn F1(M.) · 显式显示 72–84 刻度",
        size=15,
        font=font,
        color=MUTED,
        align=PP_ALIGN.CENTER,
        margin=0,
    )
    add_lollipop_row(
        slide,
        12.05,
        25.85,
        9.25,
        "EPAL",
        76.6,
        min_value=72,
        max_value=84,
        font=font,
        color=GRAY,
    )
    add_lollipop_row(
        slide,
        12.05,
        26.75,
        9.25,
        "SARGE 1.7B",
        79.6,
        min_value=72,
        max_value=84,
        font=font,
        color=CYAN,
    )
    add_lollipop_row(
        slide,
        12.05,
        27.65,
        9.25,
        "SARGE 4B",
        81.7,
        min_value=72,
        max_value=84,
        font=font,
        color=TEAL_DARK,
    )
    add_lollipop_axis(
        slide,
        12.05,
        28.12,
        9.25,
        min_value=72,
        max_value=84,
        ticks=[72, 76, 80, 84],
        font=font,
    )
    add_text(
        slide,
        12.2,
        29.0,
        9.05,
        1.38,
        "在报告 F1(S.)/F1(M.) 的可比系统中，SARGE 的多事件退化最小。"
        if lang == "zh"
        else "Among comparable systems reporting F1(S.)/F1(M.), SARGE has the smallest multi-event degradation.",
        size=18 if lang == "zh" else 16,
        font=font,
        color=NAVY,
        bold=True,
        align=PP_ALIGN.CENTER,
        margin=0.06,
        line_spacing=0.92,
    )

    add_panel(
        slide,
        22.2,
        21.93,
        11.7,
        9.25,
        "5",
        "增益来自 Schema 对齐" if lang == "zh" else "The gain comes from schema alignment",
        font=font,
        accent=AMBER,
    )
    add_text(
        slide,
        22.72,
        23.2,
        10.65,
        0.45,
        "同一 4B 基座 · seed 13" if lang == "zh" else "Same 4B base · seed 13",
        size=17,
        font=font,
        color=MUTED,
        bold=True,
        align=PP_ALIGN.CENTER,
        margin=0,
    )
    add_metric(
        slide,
        22.75,
        24.02,
        4.55,
        "24.8 → 86.0",
        "ChFinAnn · no SFT → SARGE",
        font=font,
        color=BLUE,
        fill=BLUE_TINT,
    )
    add_metric(
        slide,
        28.0,
        24.02,
        5.25,
        "3.3 → 78.0",
        "DuEE-Fin · no SFT → SARGE",
        font=font,
        color=TEAL_DARK,
        fill=TEAL_TINT,
    )
    add_text(
        slide,
        23.0,
        26.0,
        10.1,
        0.72,
        "监督对齐，而非模型规模，是主要增益来源"
        if lang == "zh"
        else "Supervised alignment—not model scale—drives the gain",
        size=25 if lang == "zh" else 21,
        font=font,
        color=NAVY,
        bold=True,
        align=PP_ALIGN.CENTER,
        margin=0,
        line_spacing=0.93,
    )
    add_text(
        slide,
        23.0,
        27.0,
        10.1,
        1.15,
        "未微调模型常输出合法但空或稀疏的事件行；监督微调教会模型实现事件表契约。"
        if lang == "zh"
        else "Without SFT, the model often emits legal but empty or sparse rows; supervision teaches it to realize the event-table contract.",
        size=19 if lang == "zh" else 17,
        font=font,
        color=INK,
        align=PP_ALIGN.CENTER,
        margin=0,
        line_spacing=0.93,
    )
    add_badge(
        slide,
        24.2,
        28.45,
        7.7,
        0.65,
        "SFT 主导 · 贪心更稳 · 提示先验弱"
        if lang == "zh"
        else "SFT dominates · greedy is steadier · prompt cues are weak",
        fill=AMBER_TINT,
        color="9A6400",
        font=font,
        size=16 if lang == "zh" else 14,
    )
    add_text(
        slide,
        22.75,
        29.35,
        10.6,
        0.75,
        "结论：性能提升主要来自固定 Schema 事件表接口的监督对齐。"
        if lang == "zh"
        else "Conclusion: the main gain comes from supervised alignment to the fixed-schema event-table interface.",
        size=18 if lang == "zh" else 15,
        font=font,
        color=NAVY,
        bold=True,
        align=PP_ALIGN.CENTER,
        margin=0.05,
        line_spacing=0.92,
    )


def add_bottom_panels(slide, lang: str, font: str) -> None:
    add_panel(
        slide,
        1.1,
        31.52,
        13.05,
        6.28,
        "6",
        "ExactRec 暴露剩余记录级差距"
        if lang == "zh"
        else "ExactRec exposes the remaining record-level gap",
        font=font,
        accent=NAVY,
    )
    add_horizontal_bar(
        slide, 1.55, 33.0, 11.95, "ChFinAnn · Role F1", 85.6, max_value=100, color=BLUE, font=font
    )
    add_horizontal_bar(
        slide, 1.55, 33.55, 11.95, "ChFinAnn · ExactRec", 56.1, max_value=100, color=NAVY, font=font
    )
    add_horizontal_bar(
        slide, 1.55, 34.45, 11.95, "DuEE-Fin · Role F1", 78.3, max_value=100, color=TEAL, font=font
    )
    add_horizontal_bar(
        slide, 1.55, 35.0, 11.95, "DuEE-Fin · ExactRec", 43.3, max_value=100, color=NAVY, font=font
    )
    add_metric(
        slide,
        1.55,
        35.7,
        5.2,
        "Δrecord = 29.5",
        "ChFinAnn · 3-seed mean",
        font=font,
        color=NAVY,
        fill=BLUE_TINT,
    )
    add_metric(
        slide,
        7.0,
        35.7,
        5.7,
        "Δrecord = 35.1",
        "DuEE-Fin · 3-seed mean",
        font=font,
        color=NAVY,
        fill=BLUE_TINT,
    )
    add_text(
        slide,
        1.55,
        37.28,
        11.6,
        0.32,
        "Δrecord 还包含缺失、多余、错值和事件数错误，并非纯绑定误差。"
        if lang == "zh"
        else "Δrecord also reflects missing, extra, wrong values and event-count errors; it is not a pure binding-error estimate.",
        size=15 if lang == "zh" else 13,
        font=font,
        color=MUTED,
        align=PP_ALIGN.CENTER,
        margin=0,
    )

    add_panel(
        slide,
        14.45,
        31.52,
        19.45,
        6.28,
        "7",
        "贡献、边界与下一步" if lang == "zh" else "Contribution, boundary, and next step",
        font=font,
        accent=CYAN,
    )
    labels = (
        [
            ("任务重述", "闭集 DEE → Schema 事件表生成"),
            ("输出契约", "证据 · 角色 · 原文值 · 事件行"),
            ("评测诊断", "Role F1 发现事实；ExactRec 检查整行"),
        ]
        if lang == "zh"
        else [
            ("Task", "Closed-schema DEE → event-table generation"),
            ("Contract", "Evidence · roles · source values · rows"),
            ("Diagnosis", "Role F1 finds facts; ExactRec checks rows"),
        ]
    )
    fills = [BLUE_TINT, TEAL_TINT, AMBER_TINT]
    colors = [BLUE, TEAL_DARK, "9A6400"]
    for index, (label, body) in enumerate(labels):
        x = 14.88 + index * 6.12
        add_box(slide, x, 32.92, 5.72, 2.55, fill=fills[index], line=colors[index])
        add_text(
            slide,
            x + 0.2,
            33.05,
            5.32,
            0.52,
            label,
            size=21 if lang == "zh" else 19,
            font=font,
            color=colors[index],
            bold=True,
            align=PP_ALIGN.CENTER,
            margin=0,
        )
        add_text(
            slide,
            x + 0.25,
            33.62,
            5.22,
            1.56,
            body,
            size=18 if lang == "zh" else 16,
            font=font,
            color=INK,
            align=PP_ALIGN.CENTER,
            margin=0.02,
            line_spacing=0.9,
        )
    boundary = add_box(slide, 14.88, 35.82, 18.3, 1.45, fill=CORAL_TINT, line=CORAL)
    boundary_text = (
        "边界：SARGE 改善但未解决 record binding；ExactRec 仍低于 Role F1，精确行组装是下一步。"
        if lang == "zh"
        else "Boundary: SARGE improves but does not solve record binding; ExactRec still trails Role F1, so exact row assembly remains the next step."
    )
    write_text(
        boundary,
        boundary_text,
        size=18 if lang == "zh" else 16,
        font=font,
        color=CORAL,
        bold=True,
        align=PP_ALIGN.CENTER,
        margin=0.12,
        line_spacing=0.92,
    )
    add_text(
        slide,
        15.05,
        37.34,
        17.9,
        0.3,
        "数据来源：论文 Table 1–4；主要结果为三种子均值，no-SFT 对照为 seed 13。"
        if lang == "zh"
        else "Source: paper Tables 1–4. Main results are three-seed means; no-SFT comparisons use seed 13.",
        size=13 if lang == "zh" else 12,
        font=font,
        color=MUTED,
        align=PP_ALIGN.CENTER,
        margin=0,
    )


def build(lang: str) -> Path:
    prs = Presentation(TEMPLATE)
    font = "微软雅黑" if lang == "zh" else "Arial"
    replace_template_header(prs, lang, font)
    slide = prs.slides[0]
    add_takeaway(slide, lang, font)
    add_problem_panel(slide, lang, font)
    add_method_panel(slide, lang, font)
    add_results_panels(slide, lang, font)
    add_bottom_panels(slide, lang, font)
    add_footer(slide, lang, font)

    filename = f"SARGE_CCKS2026_poster_{lang}.pptx"
    out = OUT_DIR / filename
    prs.save(out)
    return out


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for language in ("zh", "en"):
        path = build(language)
        print(path)


if __name__ == "__main__":
    main()
