from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import asdict, dataclass
from hashlib import sha256
from itertools import pairwise
from pathlib import Path
from zipfile import ZipFile

import award_poster_contract as contract
from PIL import Image
from pptx import Presentation
from pptx.enum.shapes import MSO_AUTO_SHAPE_TYPE, MSO_SHAPE_TYPE
from pptx.enum.text import MSO_AUTO_SIZE
from pypdf import PdfReader

FORMULA_PICTURE_PATHS = {
    "V5_METHOD_STAGE_1_INPUT_FORMULA": contract.METHOD_INPUT_FORMULA,
    "V5_METHOD_STAGE_1_CUES_FORMULA": contract.OPTIONAL_CUES_FORMULA,
    "V5_RESULTS_C_DELTA_FORMULA": contract.DELTA_RECORD_FORMULA,
}
FORMULA_PICTURE_NAMES = set(FORMULA_PICTURE_PATHS)

ROUNDED_BODY_SHAPE_NAMES = {
    "V5_TAKEHOME_BG",
    "V5_TAKEHOME_LABEL_BG",
    "V5_MOTIVATION_REASON_BADGE_1",
    "V5_MOTIVATION_REASON_BADGE_2",
    "V5_MOTIVATION_REASON_BADGE_3",
    "V5_MOTIVATION_CONTRIBUTION_BADGE_1",
    "V5_MOTIVATION_CONTRIBUTION_BADGE_2",
    "V5_MOTIVATION_CONTRIBUTION_BADGE_3",
    "V5_METHOD_STAGE_1_BADGE",
    "V5_METHOD_STAGE_2_BADGE",
    "V5_METHOD_STAGE_3_BADGE",
    "V5_METHOD_STAGE_4_BADGE",
    "V5_METHOD_STAGE_5_BADGE",
    "V5_METHOD_STAGE_4_VALIDITY_BG",
    "V5_METHOD_RIBBON_1_BG",
    "V5_METHOD_RIBBON_2_BG",
    "V5_METHOD_RIBBON_3_BG",
    "V5_METHOD_OBJECTIVE_BG",
    "V5_METHOD_HIGHLIGHT_BG",
    "V5_RESULTS_B_HIGHLIGHT_BG",
    "V5_RESULTS_C_ALIGNMENT_HIGHLIGHT_1",
    "V5_RESULTS_C_ALIGNMENT_HIGHLIGHT_2",
    "V5_CONCLUSION_1_BG",
    "V5_CONCLUSION_2_BG",
    "V5_CONCLUSION_3_BG",
}


@dataclass(frozen=True)
class ValidationResult:
    name: str
    detail: str
    passed: bool = True


def normalized_text(value: str) -> str:
    return " ".join(value.replace("\x0b", "\n").split())


def recursive_shapes(shapes):
    for shape in shapes:
        yield shape
        if shape.shape_type == MSO_SHAPE_TYPE.GROUP:
            yield from recursive_shapes(shape.shapes)


def slide_text(slide) -> str:
    return "\n".join(
        shape.text
        for shape in recursive_shapes(slide.shapes)
        if getattr(shape, "has_text_frame", False) and shape.text
    )


def find_shape(slide, name: str):
    for shape in recursive_shapes(slide.shapes):
        if shape.name == name:
            return shape
    raise AssertionError(f"missing shape: {name}")


def _color_signature(color_format) -> str | None:
    try:
        if color_format.type is None:
            return None
        if color_format.rgb is not None:
            return str(color_format.rgb)
        if color_format.theme_color is not None:
            return f"theme:{int(color_format.theme_color)}"
    except (AttributeError, TypeError, ValueError):
        return None
    return None


def _hyperlink(shape) -> str | None:
    try:
        return shape.click_action.hyperlink.address
    except (AttributeError, KeyError, ValueError):
        return None


def _shape_signature(shape) -> tuple:
    fill_color = None
    line_color = None
    line_width = None
    try:
        fill_color = _color_signature(shape.fill.fore_color)
    except (AttributeError, TypeError):
        pass
    try:
        line_color = _color_signature(shape.line.color)
        line_width = int(shape.line.width) if shape.line.width is not None else None
    except (AttributeError, TypeError):
        pass
    image_hash = None
    if shape.shape_type == MSO_SHAPE_TYPE.PICTURE:
        image_hash = sha256(shape.image.blob).hexdigest()
    return (
        shape.name,
        normalized_text(shape.text) if getattr(shape, "has_text_frame", False) else "",
        int(shape.left),
        int(shape.top),
        int(shape.width),
        int(shape.height),
        float(shape.rotation or 0),
        int(shape.shape_type),
        fill_color,
        line_color,
        line_width,
        _hyperlink(shape),
        image_hash,
    )


def _protected_signatures(path: Path) -> dict[str, tuple]:
    slide = Presentation(path).slides[0]
    return {
        name: _shape_signature(find_shape(slide, name))
        for name in sorted(contract.PROTECTED_SHAPES)
    }


def _media_hashes(path: Path) -> dict[str, str]:
    with ZipFile(path) as archive:
        return {
            name: sha256(archive.read(name)).hexdigest()
            for name in archive.namelist()
            if name.startswith("ppt/media/")
        }


def _text_runs(shape):
    return [
        run
        for paragraph in shape.text_frame.paragraphs
        for run in paragraph.runs
        if run.text
    ]


def _font_sizes(shape) -> list[float]:
    runs = _text_runs(shape)
    assert runs, f"text runs missing: {shape.name}"
    assert all(run.font.size is not None for run in runs), (
        f"explicit font size missing: {shape.name}"
    )
    return [run.font.size.pt for run in runs]


def _font_names(shape) -> list[str | None]:
    return [run.font.name for run in _text_runs(shape)]


def _validate_header_typography(slide) -> None:
    title = find_shape(slide, "HDR_TITLE")
    authors = find_shape(slide, "HDR_AUTHORS")
    affiliations = find_shape(slide, "HDR_AFFILIATIONS")

    for shape in (title, authors, affiliations):
        assert shape.text_frame.auto_size != MSO_AUTO_SIZE.TEXT_TO_FIT_SHAPE, (
            shape.name,
            "shrink-fit is forbidden",
        )
    assert min(_font_sizes(title)) >= contract.V5_TITLE_PT, "title below 74 pt"
    assert min(_font_sizes(authors)) >= contract.V5_AUTHORS_PT, "authors below 32 pt"
    assert min(_font_sizes(affiliations)) >= contract.V5_AFFILIATIONS_PT, (
        "affiliations below 22 pt"
    )
    assert "Yue Zhao¹²*" in authors.text, "corresponding-author marker/name missing"
    assert "* Corresponding author:" in affiliations.text
    for shape in (title, authors, affiliations):
        assert all(
            run.font.name == contract.POSTER_FONT for run in _text_runs(shape)
        ), f"header font must be {contract.POSTER_FONT}: {shape.name}"


def _validate_body_typography(slide) -> int:
    count = 0
    template_names = contract.PROTECTED_SHAPES | contract.EDITABLE_HEADER_SHAPES
    for shape in recursive_shapes(slide.shapes):
        if shape.name in template_names or not getattr(shape, "has_text_frame", False):
            continue
        if not shape.text.strip():
            continue
        assert shape.name.startswith("V5_"), f"unapproved body text shape: {shape.name}"
        count += 1
        assert shape.text_frame.auto_size != MSO_AUTO_SIZE.TEXT_TO_FIT_SHAPE, (
            shape.name,
            "shrink-fit is forbidden",
        )
        sizes = _font_sizes(shape)
        fonts = _font_names(shape)
        assert sizes, f"explicit font size missing: {shape.name}"
        assert fonts and all(font == contract.POSTER_FONT for font in fonts), (
            shape.name,
            fonts,
        )
        if "_QUALIFIER" in shape.name:
            minimum = contract.V5_QUALIFIER_MIN_PT
        elif "_CHART_" in shape.name or "_CAPTION" in shape.name:
            minimum = contract.V5_CHART_CAPTION_MIN_PT
        else:
            minimum = contract.V5_BODY_MIN_PT
        assert min(sizes) >= minimum, (shape.name, min(sizes), minimum)
    return count


def _validate_bounds(prs) -> int:
    shapes = list(recursive_shapes(prs.slides[0].shapes))
    for shape in shapes:
        assert shape.left >= 0 and shape.top >= 0, (shape.name, "negative position")
        assert shape.left + shape.width <= prs.slide_width + 1000, (
            shape.name,
            "right bound",
        )
        assert shape.top + shape.height <= prs.slide_height + 1000, (
            shape.name,
            "bottom bound",
        )
    return len(shapes)


def _validate_narrative(slide) -> float:
    takehome = find_shape(slide, "V5_TAKEHOME_BG")
    bands = [
        find_shape(slide, "V5_MOTIVATION_BAND"),
        find_shape(slide, "V5_METHOD_BAND"),
        find_shape(slide, "V5_RESULTS_BAND"),
        find_shape(slide, "V5_CONCLUSION_BAND"),
    ]
    assert takehome.top + takehome.height < bands[0].top, (
        "take-home must precede motivation"
    )
    assert all(
        first.top + first.height < second.top for first, second in pairwise(bands)
    ), "scientific bands must read top-to-bottom"
    assert bands[1].height == max(band.height for band in bands), (
        "method band must be the largest scientific band"
    )
    scientific_height = bands[-1].top + bands[-1].height - bands[0].top
    method_ratio = bands[1].height / scientific_height
    assert 0.34 <= method_ratio <= 0.40, (
        f"method ratio outside plan: {method_ratio:.3f}"
    )

    expected_headings = (
        "1 Motivation — Correct values can still form wrong rows",
        "2 Method — Schema grounding governs the event-table pipeline",
        "3 Results — Competitive overall; +5.1 multi-event F1 over EPAL on ChFinAnn",
        "4 Conclusion — One table contract clarifies both gains and limits",
    )
    text = slide_text(slide)
    assert all(heading in text for heading in expected_headings), (
        "section heading missing"
    )
    return method_ratio


def _validate_claims(slide) -> None:
    text = slide_text(slide)
    folded = text.casefold()
    for token in contract.V5_REQUIRED_TOKENS:
        assert token in text, f"required v5 token missing: {token}"
    for phrase in contract.V5_FORBIDDEN_CLAIMS:
        assert phrase.casefold() not in folded, f"forbidden claim present: {phrase}"
    for reason in contract.V5_MOTIVATION["reasons"]:
        assert reason in text, f"motivation reason missing: {reason}"
    assert contract.V5_MOTIVATION["research_gap"] in text
    assert contract.V5_MOTIVATION["contribution"] in text
    for heading, contribution in contract.V5_CONTRIBUTIONS:
        assert heading in text and contribution in text
    for message in contract.V5_CONCLUSION_MESSAGES:
        assert message in text
    takehome = find_shape(slide, "V5_TAKEHOME_TEXT")
    contribution = find_shape(slide, "V5_MOTIVATION_CONTRIBUTION_3")
    assert "ExactRec (strict event-row match)" in takehome.text
    assert "Δrecord (= F1 − ExactRec)" in contribution.text
    assert find_shape(slide, "V5_METHOD_STAGE_5_TITLE").text == "Fixed-slot table"
    assert find_shape(slide, "V5_RESULTS_B_CHART_LEGEND").text == (
        "F1(S.): single/light · F1(M.): multi/dark"
    )
    formula_descriptions = {
        name: find_shape(slide, name)._element.nvPicPr.cNvPr.get("descr", "")
        for name in FORMULA_PICTURE_NAMES
    }
    assert "document D plus closed schema S" in formula_descriptions[
        "V5_METHOD_STAGE_1_INPUT_FORMULA"
    ]
    assert "surface candidates C_K(D) and slot prior P_D" in formula_descriptions[
        "V5_METHOD_STAGE_1_CUES_FORMULA"
    ]
    assert find_shape(slide, "V5_METHOD_STAGE_1_QUALIFIER").text == (
        "C_K(D): candidates  ·  P_D: role-slot prior"
    )
    assert "Delta_record equals F1 minus ExactRec" in formula_descriptions[
        "V5_RESULTS_C_DELTA_FORMULA"
    ]


def _method_key(value: str) -> str:
    return value.upper().replace("-", "_")


def _validate_charts(slide) -> int:
    checked = 0
    expected_titles = {
        "CHFINANN": "ChFinAnn F1 (SARGE: mean ± std, 3 seeds)",
        "DUEE_FIN": "DuEE-Fin F1 (SARGE: mean ± std, 3 seeds)",
    }
    for dataset, value_key in (("CHFINANN", "chfinann"), ("DUEE_FIN", "duee_fin")):
        prefix = f"V5_RESULTS_A_{dataset}_CHART"
        assert find_shape(slide, f"{prefix}_TITLE").text == expected_titles[dataset]
        tick_lines = {
            tick: find_shape(slide, f"{prefix}_TICK_LINE_{tick}")
            for tick in (60, 70, 80, 90)
        }
        x_min = tick_lines[60].left
        x_max = tick_lines[90].left
        for tick in (60, 70, 80, 90):
            assert find_shape(slide, f"{prefix}_TICK_{tick}").text == str(tick)
        for row in contract.V5_OVERALL_F1_DATA:
            key = _method_key(row["method"])
            bar = find_shape(slide, f"{prefix}_BAR_{key}")
            assert bar.shape_type == MSO_SHAPE_TYPE.AUTO_SHAPE
            assert bar.auto_shape_type == MSO_AUTO_SHAPE_TYPE.RECTANGLE
            expected_right = x_min + (row[value_key] - 60) / 30 * (x_max - x_min)
            assert abs(bar.left - x_min) <= 1500, (bar.name, "unexpected origin")
            assert abs(bar.left + bar.width - expected_right) <= 18000, (
                bar.name,
                "bar does not encode contract value",
            )
            label = find_shape(slide, f"{prefix}_LABEL_{key}").text
            expected_label = (
                f"{row['method']} {row['reference']}"
                if row["reference"]
                else row["method"]
            )
            assert label == expected_label
            expected_value = (
                f"{row[value_key]:.1f} ± {row['std'][value_key]:.1f}"
                if row["method"] == "SARGE"
                else f"{row[value_key]:.1f}"
            )
            assert find_shape(slide, f"{prefix}_VALUE_{key}").text == expected_value
            checked += 1
        for suffix in ("ERROR_BAR", "ERROR_CAP_LEFT", "ERROR_CAP_RIGHT"):
            assert (
                find_shape(slide, f"{prefix}_{suffix}").shape_type
                == MSO_SHAPE_TYPE.LINE
            )
        sarge = next(
            row for row in contract.V5_OVERALL_F1_DATA if row["method"] == "SARGE"
        )
        sarge_bar = find_shape(slide, f"{prefix}_BAR_SARGE")
        center_x = sarge_bar.left + sarge_bar.width
        center_y = sarge_bar.top + sarge_bar.height / 2
        half_error = sarge["std"][value_key] / 30 * (x_max - x_min)
        error_bar = find_shape(slide, f"{prefix}_ERROR_BAR")
        assert abs(error_bar.left - (center_x - half_error)) <= 18000, (
            prefix,
            "error bar left endpoint",
        )
        assert abs(error_bar.left + error_bar.width - (center_x + half_error)) <= 18000, (
            prefix,
            "error bar right endpoint",
        )
        assert abs(error_bar.top - center_y) <= 18000, (
            prefix,
            "error bar vertical anchor",
        )
        assert abs(error_bar.height) <= 1500, (prefix, "error bar must be horizontal")
        for side, expected_x in (
            ("LEFT", center_x - half_error),
            ("RIGHT", center_x + half_error),
        ):
            cap = find_shape(slide, f"{prefix}_ERROR_CAP_{side}")
            assert abs(cap.left - expected_x) <= 18000, (
                prefix,
                f"error bar {side.lower()} cap",
            )
            assert cap.top < center_y < cap.top + cap.height, (
                prefix,
                f"error bar {side.lower()} cap anchor",
            )
            assert abs(cap.width) <= 1500, (
                prefix,
                f"error bar {side.lower()} cap must be vertical",
            )

    multi_prefix = "V5_RESULTS_B_CHART"
    y70 = find_shape(slide, f"{multi_prefix}_Y_TICK_LINE_70").top
    y90 = find_shape(slide, f"{multi_prefix}_Y_TICK_LINE_90").top
    emu_per_point = (y70 - y90) / 20
    for row in contract.V5_MULTI_EVENT_DATA["rows"]:
        for metric in ("f1_s", "f1_m"):
            suffix = metric.upper()
            bar = find_shape(slide, f"{multi_prefix}_BAR_{row['method']}_{suffix}")
            assert bar.shape_type == MSO_SHAPE_TYPE.AUTO_SHAPE
            assert bar.auto_shape_type == MSO_AUTO_SHAPE_TYPE.RECTANGLE
            expected_height = (row[metric] - 70) * emu_per_point
            assert abs(bar.top + bar.height - y70) <= 18000, (
                bar.name,
                "multi-event bar baseline",
            )
            assert abs(bar.height - expected_height) <= 18000, (
                bar.name,
                "multi-event bar height",
            )
            assert find_shape(
                slide, f"{multi_prefix}_VALUE_{row['method']}_{suffix}"
            ).text == (f"{row[metric]:.1f}")
            checked += 1
    multi_rows = {
        row["method"]: row for row in contract.V5_MULTI_EVENT_DATA["rows"]
    }
    epal = multi_rows["EPAL"]
    sarge = multi_rows["SARGE"]
    expected_gap_label = (
        f"EPAL gap {epal['gap']:.1f} · SARGE gap {sarge['gap']:.1f}"
    )
    assert find_shape(slide, "V5_RESULTS_B_CHART_GAPS").text == expected_gap_label, (
        "multi-event gap label does not match its method"
    )
    assert find_shape(slide, "V5_RESULTS_B_CALLOUT_MULTI").text == (
        f"+{sarge['f1_m'] - epal['f1_m']:.1f} F1(M.)"
    )
    assert find_shape(slide, "V5_RESULTS_B_CALLOUT_GAP").text == (
        f"{epal['gap'] - sarge['gap']:.1f}-point smaller S–M gap"
    )
    assert (
        "Mean over seeds 13/17/42" in find_shape(slide, "V5_RESULTS_B_QUALIFIER").text
    )
    assert find_shape(slide, "V5_RESULTS_A_PROVENANCE_QUALIFIER").text == (
        "Baselines: reported values [7,10,13,15,18]; SARGE seeds 13/17/42."
    )
    assert find_shape(slide, "V5_RESULTS_C_ALIGNMENT_LABEL").text == (
        "Same backend · No SFT → answer-token SFT"
    )

    for index, row in enumerate(contract.V5_ALIGNMENT_DIAGNOSTICS, start=1):
        assert find_shape(slide, f"V5_RESULTS_C_ALIGNMENT_{index}").text == (
            f"{row['dataset']}  {row['no_sft']:.1f} → {row['sft']:.1f}"
        )
        qualifier = find_shape(slide, f"V5_RESULTS_C_ALIGNMENT_{index}_QUALIFIER").text
        assert qualifier == f"{row['backend']} · seed {row['seed']}"
    for index, row in enumerate(contract.V5_RECORD_DIAGNOSTICS, start=1):
        assert find_shape(slide, f"V5_RESULTS_C_RECORD_CHART_ROW_{index}").text == (
            f"{row['dataset']}  F1 {row['f1']:.1f}  |  ExactRec {row['exact_rec']:.1f}  |  "
            f"Δrecord {row['delta']:.1f}"
        )
    record_note = find_shape(slide, "V5_RESULTS_C_RECORD_QUALIFIER").text
    assert "3-seed mean" in record_note
    assert "not a pure binding-error estimate" in record_note
    return checked


def _validate_visual_style(prs, slide) -> None:
    page_area = prs.slide_width * prs.slide_height
    template_names = contract.PROTECTED_SHAPES | contract.EDITABLE_HEADER_SHAPES
    for shape in recursive_shapes(slide.shapes):
        if shape.shape_type == MSO_SHAPE_TYPE.PICTURE:
            assert shape.width * shape.height < page_area * 0.50, (
                shape.name,
                "unexpected full-slide raster",
            )
        if shape.name in template_names:
            continue
        assert shape.name.startswith("V5_"), f"unapproved body shape: {shape.name}"
        if shape.shape_type == MSO_SHAPE_TYPE.PICTURE:
            assert shape.name in FORMULA_PICTURE_NAMES, (
                shape.name,
                "only formula pictures are allowed in the body",
            )
            description = shape._element.nvPicPr.cNvPr.get("descr", "")
            assert "LaTeX formula" in description
            continue
        assert "ICON" not in shape.name.upper(), (
            f"decorative icon forbidden: {shape.name}"
        )
        xml = shape._element.xml
        assert "<a:outerShdw" not in xml and "<a:innerShdw" not in xml, (
            shape.name,
            "shadow forbidden",
        )
        assert "<a:gradFill" not in xml, (shape.name, "body gradient forbidden")
        if shape.shape_type == MSO_SHAPE_TYPE.AUTO_SHAPE:
            allowed_types = {
                MSO_AUTO_SHAPE_TYPE.RECTANGLE,
                MSO_AUTO_SHAPE_TYPE.ROUNDED_RECTANGLE,
                MSO_AUTO_SHAPE_TYPE.HEXAGON,
            }
            assert shape.auto_shape_type in allowed_types, (
                shape.name,
                "unsupported decorative auto-shape",
            )
            if shape.auto_shape_type == MSO_AUTO_SHAPE_TYPE.HEXAGON:
                assert shape.name == "V5_METHOD_STAGE_3_MODEL_BADGE"
            if shape.auto_shape_type == MSO_AUTO_SHAPE_TYPE.ROUNDED_RECTANGLE:
                assert shape.name in ROUNDED_BODY_SHAPE_NAMES, (
                    shape.name,
                    "unapproved rounded body shape",
                )


def _validate_qr(slide) -> None:
    qr = find_shape(slide, "FTR_QR_IMAGE")
    assert qr.shape_type == MSO_SHAPE_TYPE.PICTURE
    description = qr._element.nvPicPr.cNvPr.get("descr", "")
    assert "QR code" in description and contract.DISPLAY_URL in description
    assert _hyperlink(qr) == contract.REPOSITORY_URL
    url = find_shape(slide, "FTR_URL")
    assert contract.DISPLAY_URL in url.text
    assert _hyperlink(url) == contract.REPOSITORY_URL


def validate_pptx(path: Path = contract.V5_PPTX) -> list[ValidationResult]:
    path = Path(path)
    assert path.is_file(), f"missing PPTX: {path}"
    assert contract.V2_PPTX.is_file(), (
        f"missing protected template source: {contract.V2_PPTX}"
    )
    prs = Presentation(path)
    assert len(prs.slides) == 1, "poster must contain exactly one slide"
    assert abs(prs.slide_width / 360000 - contract.PAGE_CM[0]) < 0.01
    assert abs(prs.slide_height / 360000 - contract.PAGE_CM[1]) < 0.01
    slide = prs.slides[0]
    shape_count = _validate_bounds(prs)

    assert _protected_signatures(path) == _protected_signatures(contract.V2_PPTX), (
        "official protected footer changed"
    )
    output_media = set(_media_hashes(path).values())
    expected_media = set(_media_hashes(contract.V2_PPTX).values()) | {
        sha256(formula.read_bytes()).hexdigest() for formula in contract.FORMULA_IMAGES
    }
    assert output_media == expected_media, "unexpected media beyond official + formulas"
    for shape_name, formula_path in FORMULA_PICTURE_PATHS.items():
        formula_picture = find_shape(slide, shape_name)
        assert formula_picture.shape_type == MSO_SHAPE_TYPE.PICTURE
        assert sha256(formula_picture.image.blob).hexdigest() == sha256(
            formula_path.read_bytes()
        ).hexdigest(), f"formula asset mismatch at {shape_name}"
    _validate_header_typography(slide)
    body_text_count = _validate_body_typography(slide)
    method_ratio = _validate_narrative(slide)
    _validate_claims(slide)
    chart_count = _validate_charts(slide)
    _validate_visual_style(prs, slide)
    _validate_qr(slide)

    return [
        ValidationResult(
            "pptx_canvas",
            f"1 slide, {prs.slide_width / 360000:.2f}x{prs.slide_height / 360000:.2f} cm, "
            f"{shape_count} shapes in bounds",
        ),
        ValidationResult(
            "pptx_template", "protected signatures preserved; formula media verified"
        ),
        ValidationResult(
            "pptx_typography", f"{body_text_count} v5 text shapes checked"
        ),
        ValidationResult(
            "pptx_narrative", f"method/scientific-body ratio={method_ratio:.3f}"
        ),
        ValidationResult(
            "pptx_claims", f"{len(contract.V5_REQUIRED_TOKENS)} required claims"
        ),
        ValidationResult("pptx_charts", f"{chart_count} native editable bars checked"),
        ValidationResult(
            "pptx_visual_style",
            "native highlights + three LaTeX formulas; no body rasterization",
        ),
        ValidationResult(
            "pptx_qr", f"alt text and hyperlink={contract.REPOSITORY_URL}"
        ),
    ]


def _pdf_font_rows(path: Path) -> tuple[str, list[str]]:
    completed = subprocess.run(
        ["pdffonts", str(path)],
        check=True,
        capture_output=True,
        text=True,
    )
    rows = [line for line in completed.stdout.splitlines()[2:] if line.strip()]
    return completed.stdout, rows


def validate_pdf(path: Path = contract.V5_PDF) -> list[ValidationResult]:
    path = Path(path)
    assert path.is_file(), f"missing PDF: {path}"
    reader = PdfReader(path)
    assert len(reader.pages) == 1, "PDF must contain exactly one page"
    page = reader.pages[0]
    width = float(page.mediabox.width)
    height = float(page.mediabox.height)
    assert abs(width - contract.PAGE_PT[0]) < 1, (width, contract.PAGE_PT[0])
    assert abs(height - contract.PAGE_PT[1]) < 1, (height, contract.PAGE_PT[1])
    text = normalized_text(page.extract_text() or "")
    for token in contract.V5_REQUIRED_TOKENS:
        assert normalized_text(token) in text, f"PDF token missing: {token}"
    assert "Yue Zhao¹²*" in text, "PDF author marker/name missing"

    fonts, rows = _pdf_font_rows(path)
    assert rows, "PDF contains no font records"
    assert all(re.search(r"\byes\s+yes\s+yes\b", row) for row in rows), (
        "PDF fonts must be embedded, subset, and Unicode-mapped",
        fonts,
    )
    folded_fonts = fonts.casefold()
    assert any(
        name in folded_fonts for name in ("arial", "liberationsans", "carlito")
    ), (
        "Arial or its LibreOffice-compatible substitute is missing",
        fonts,
    )
    return [
        ValidationResult(
            "pdf",
            f"{width:.0f}x{height:.0f} pt, 1 page, {len(rows)} fonts embedded",
        )
    ]


def validate_png_and_qr(
    png_path: Path = contract.V5_PNG,
    pptx_path: Path = contract.V5_PPTX,
) -> list[ValidationResult]:
    png_path = Path(png_path)
    pptx_path = Path(pptx_path)
    assert png_path.is_file(), f"missing PNG: {png_path}"
    assert pptx_path.is_file(), f"missing PPTX for QR geometry: {pptx_path}"
    with Image.open(png_path) as image:
        assert abs(image.width - 5250) <= 2 and abs(image.height - 6450) <= 2, (
            f"expected 150 dpi poster near 5250x6450, got {image.width}x{image.height}"
        )
        prs = Presentation(pptx_path)
        qr = find_shape(prs.slides[0], "FTR_QR_IMAGE")
        sx = image.width / prs.slide_width
        sy = image.height / prs.slide_height
        pad = 12
        box = (
            max(0, int(qr.left * sx) - pad),
            max(0, int(qr.top * sy) - pad),
            min(image.width, int((qr.left + qr.width) * sx) + pad),
            min(image.height, int((qr.top + qr.height) * sy) + pad),
        )
        crop = image.crop(box).convert("RGB")
        import zxingcpp

        decoded = zxingcpp.read_barcode(crop)
        assert decoded is not None, "rendered QR did not decode"
        assert decoded.text == contract.REPOSITORY_URL, decoded.text
        detail = f"{image.width}x{image.height}, QR={decoded.text}"
    return [ValidationResult("png", detail)]


def _json_payload(
    *,
    mode: str,
    results: list[ValidationResult] | None = None,
    error: str | None = None,
) -> dict:
    return {
        "overall_pass": error is None,
        "mode": mode,
        "results": [asdict(result) for result in results or []],
        **({"error": error} if error is not None else {}),
    }


def _print_text(payload: dict) -> None:
    for result in payload["results"]:
        print(f"PASS {result['name']}: {result['detail']}")
    if payload["overall_pass"]:
        print("overall_pass: true")
    else:
        print(f"FAIL: {payload['error']}")
        print("overall_pass: false")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Validate the SARGE CCKS 2026 v5 poster"
    )
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--pptx-only", action="store_true")
    mode.add_argument("--all", action="store_true")
    parser.add_argument("--pptx", type=Path, default=contract.V5_PPTX)
    parser.add_argument("--pdf", type=Path, default=contract.V5_PDF)
    parser.add_argument("--png", type=Path, default=contract.V5_PNG)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    mode_name = "all" if args.all else "pptx-only"

    try:
        results = validate_pptx(args.pptx)
        if args.all:
            results.extend(validate_pdf(args.pdf))
            results.extend(validate_png_and_qr(args.png, args.pptx))
        payload = _json_payload(mode=mode_name, results=results)
        status = 0
    except (AssertionError, OSError, subprocess.SubprocessError, ValueError) as exc:
        detail = str(exc) or exc.__class__.__name__
        payload = _json_payload(mode=mode_name, error=detail)
        status = 1

    if args.json:
        print(json.dumps(payload, indent=2, ensure_ascii=False))
    else:
        _print_text(payload)
    return status


if __name__ == "__main__":
    sys.exit(main())
