from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from hashlib import sha256
from itertools import pairwise
from pathlib import Path
from typing import NamedTuple
from zipfile import ZipFile

import award_poster_contract as contract
import build_sarge_poster_v6 as builder
from PIL import Image
from pptx import Presentation
from pptx.enum.shapes import MSO_AUTO_SHAPE_TYPE, MSO_SHAPE_TYPE
from pptx.enum.text import MSO_AUTO_SIZE
from pypdf import PdfReader


class ValidationResult(NamedTuple):
    name: str
    detail: str


def normalized_text(value: str) -> str:
    return " ".join(value.replace("\x0b", "\n").split())


def slide_text(slide) -> str:
    chunks: list[str] = []
    for shape in slide.shapes:
        if getattr(shape, "has_text_frame", False) and shape.text:
            chunks.append(shape.text)
        if getattr(shape, "has_table", False):
            chunks.extend(cell.text for row in shape.table.rows for cell in row.cells)
    return normalized_text("\n".join(chunks))


def find_shape(slide, name: str):
    for shape in slide.shapes:
        if shape.name == name:
            return shape
    raise AssertionError(f"missing shape: {name}")


def _text_runs(shape):
    return [
        run
        for paragraph in shape.text_frame.paragraphs
        for run in paragraph.runs
        if run.text
    ]


def _table_runs(shape):
    return [
        run
        for row in shape.table.rows
        for cell in row.cells
        for paragraph in cell.text_frame.paragraphs
        for run in paragraph.runs
        if run.text
    ]


def _media_hashes(path: Path) -> dict[str, str]:
    with ZipFile(path) as archive:
        return {
            name: sha256(archive.read(name)).hexdigest()
            for name in archive.namelist()
            if name.startswith("ppt/media/")
        }


def _hyperlink(shape) -> str | None:
    try:
        address = shape.click_action.hyperlink.address
        if address:
            return address
    except (AttributeError, KeyError, ValueError):
        pass
    if getattr(shape, "has_text_frame", False):
        for run in _text_runs(shape):
            try:
                if address := run.hyperlink.address:
                    return address
            except (AttributeError, KeyError, ValueError):
                pass
    return None


def _table_rows(shape) -> tuple[tuple[str, ...], ...]:
    assert getattr(shape, "has_table", False), f"not a table: {shape.name}"
    return tuple(tuple(cell.text for cell in row.cells) for row in shape.table.rows)


def _validate_canvas_and_bounds(prs) -> int:
    assert len(prs.slides) == 1, "poster must contain exactly one slide"
    assert abs(prs.slide_width / 360000 - contract.PAGE_CM[0]) < 0.01
    assert abs(prs.slide_height / 360000 - contract.PAGE_CM[1]) < 0.01
    count = 0
    for shape in prs.slides[0].shapes:
        count += 1
        assert shape.left >= 0 and shape.top >= 0, f"outside slide: {shape.name}"
        assert shape.left + shape.width <= prs.slide_width + 1000, (
            f"outside slide: {shape.name}"
        )
        assert shape.top + shape.height <= prs.slide_height + 1000, (
            f"outside slide: {shape.name}"
        )
    return count


def _validate_template(path: Path, slide) -> None:
    media = _media_hashes(path)
    assert media["ppt/media/image1.jpeg"] == (
        "75c64d300ba3826ee6da34bb658e081c35ce01724ed1570e9564ebd0f185ded7"
    )
    assert len(media) == 5, "v6 media must be background, QR, and three LaTeX formulas"
    assert normalized_text(find_shape(slide, "FTR_CONFERENCE_TEXT").text) == normalized_text(
        find_shape(Presentation(contract.TEMPLATE_PPTX).slides[0], "TextBox 24").text
    )


def _validate_typography(slide) -> int:
    header_minima = {
        "HDR_TITLE": contract.V6_TITLE_PT,
        "HDR_AUTHORS": contract.V6_AUTHORS_PT,
        "HDR_AFFILIATIONS": contract.V6_AFFILIATIONS_PT,
    }
    for name, minimum in header_minima.items():
        shape = find_shape(slide, name)
        runs = _text_runs(shape)
        assert runs and all(run.font.size is not None for run in runs)
        assert min(run.font.size.pt for run in runs) >= minimum
        assert all(run.font.name == contract.V6_FONT for run in runs)
        assert all(run.font.size.pt.is_integer() for run in runs), (
            f"integer point size required: {name}"
        )
        assert shape.text_frame.auto_size != MSO_AUTO_SIZE.TEXT_TO_FIT_SHAPE

    checked = 0
    for shape in slide.shapes:
        if not shape.name.startswith("V6_"):
            continue
        runs = []
        if getattr(shape, "has_text_frame", False) and shape.text.strip():
            assert shape.text_frame.auto_size in {None, MSO_AUTO_SIZE.NONE}
            runs.extend(_text_runs(shape))
        if getattr(shape, "has_table", False):
            for row in shape.table.rows:
                for cell in row.cells:
                    assert cell.text_frame.auto_size in {None, MSO_AUTO_SIZE.NONE}
            runs.extend(_table_runs(shape))
        if not runs:
            continue
        checked += 1
        assert all(run.font.name == contract.V6_FONT for run in runs), shape.name
        assert all(run.font.size is not None for run in runs), shape.name
        assert min(run.font.size.pt for run in runs) >= contract.V6_QUALIFIER_PT, shape.name
        assert all(run.font.size.pt.is_integer() for run in runs), (
            f"integer point size required: {shape.name}"
        )
    return checked


def _validate_content(slide) -> None:
    text = slide_text(slide)
    for token in contract.V6_REQUIRED_TOKENS:
        assert normalized_text(token) in text, f"required v6 token missing: {token}"
    folded = text.casefold()
    for phrase in contract.V6_FORBIDDEN_CLAIMS:
        assert phrase.casefold() not in folded, f"forbidden claim present: {phrase}"
    assert re.search(r"(?<!\d)24\.8(?!\d)", text) is None
    assert re.search(r"(?<!\d)3\.3(?!\d)", text) is None
    assert contract.TITLE.replace("\n", " ") in text
    assert normalized_text(contract.AUTHORS) in text
    assert contract.V6_GROUNDING_NOTE in text
    assert contract.V6_MULTI_EVENT_DEFINITION in text
    assert contract.V6_EXACTREC_CAVEAT in text
    for stage in contract.V6_MOTIVATION_STAGES:
        assert stage in text
    assert contract.V6_METHOD_CORE_CHANGE in text
    assert contract.V6_VALIDATION_NOTE in text


def _validate_layout(slide) -> tuple[int, int]:
    heading_names = (
        "V6_MOTIVATION_HEADING",
        "V6_METHOD_HEADING",
        "V6_RESULTS_HEADING",
        "V6_CONCLUSION_HEADING",
    )
    headings = [find_shape(slide, name) for name in heading_names]
    assert all(a.top < b.top for a, b in pairwise(headings)), (
        "section order is not top-to-bottom"
    )
    rounded = 0
    words: list[str] = []
    for shape in slide.shapes:
        if shape.name.startswith("V5_"):
            raise AssertionError(f"legacy v5 shape remains: {shape.name}")
        if not shape.name.startswith("V6_"):
            continue
        top = shape.top / 914400
        bottom = (shape.top + shape.height) / 914400
        assert top >= contract.V6_WHITE_BODY_TOP - 0.01, (
            f"shape outside white body region: {shape.name}"
        )
        assert bottom <= contract.V6_WHITE_BODY_BOTTOM + 0.01, (
            f"shape outside white body region: {shape.name}"
        )
        if shape.shape_type == MSO_SHAPE_TYPE.AUTO_SHAPE:
            rounded += shape.auto_shape_type == MSO_AUTO_SHAPE_TYPE.ROUNDED_RECTANGLE
        if getattr(shape, "has_text_frame", False) and shape.text.strip():
            words.extend(re.findall(r"[A-Za-z0-9]+(?:[-'][A-Za-z0-9]+)*", shape.text))
    assert rounded <= contract.V6_MAX_ROUNDED_BODY_SHAPES
    low, high = contract.V6_WORD_COUNT_RANGE
    assert low <= len(words) <= high, f"v6 prose word count outside target: {len(words)}"
    return len(words), rounded


def _validate_results(slide) -> int:
    overall = find_shape(slide, "V6_RESULTS_A_TABLE")
    expected_overall = (
        ("Model", "ChFinAnn F1", "DuEE-Fin F1"),
        ("Doc2EDAG [18]", "78.8", "63.4"),
        ("GIT [14]", "80.3", "67.8"),
        ("ProCNet [13]", "80.8", "75.1"),
        ("EPAL [7]", "83.4", "76.4"),
        ("SEELE [15]", "85.1", "80.8"),
        ("SARGE", "85.6 ± 0.4", "78.3 ± 0.4"),
    )
    assert _table_rows(overall) == expected_overall
    records = find_shape(slide, "V6_RESULTS_C_TABLE")
    assert _table_rows(records) == (
        ("Dataset", "Role F1", "ExactRec", "F1 − ExactRec"),
        ("ChFinAnn", "85.6", "56.1", "29.5"),
        ("DuEE-Fin", "78.3", "43.3", "35.1†"),
    )
    names = {shape.name for shape in slide.shapes}
    assert not any("_BAR_" in name for name in names), "truncated-axis bars are forbidden"
    checked = 0
    for row in contract.V6_MULTI_EVENT:
        model = row["model"].upper()
        for metric in ("single", "multi"):
            marker = find_shape(slide, f"V6_RESULTS_B_{model}_{metric.upper()}_MARKER")
            center_x = (marker.left + marker.width / 2) / 914400
            expected = builder.multi_event_x(row[metric])
            assert abs(center_x - expected) <= 0.01, (
                f"dumbbell marker misplaced: {marker.name}"
            )
            checked += 1
    for tick in (70, 75, 80, 85, 90, 95):
        assert find_shape(slide, f"V6_RESULTS_B_TICK_{tick}").text == str(tick), (
            "Multi-Event plot must show the explicit 70–95 zoomed axis"
        )
    assert find_shape(slide, "V6_RESULTS_B_AXIS_NOTE").text == "ZOOMED AXIS 70–95", (
        "Multi-Event plot must label the 70–95 zoomed axis"
    )
    return checked


def _validate_editability(path: Path, slide) -> tuple[int, int]:
    table_names = {
        "V6_MOTIVATION_WRONG_TABLE",
        "V6_MOTIVATION_CORRECT_TABLE",
        "V6_MOTIVATION_SOURCE_TABLE",
        "V6_METHOD_SFT_TARGET_TABLE",
        "V6_METHOD_OUTPUT_TABLE",
        "V6_RESULTS_A_TABLE",
        "V6_RESULTS_C_TABLE",
    }
    for name in table_names:
        assert find_shape(slide, name).shape_type == MSO_SHAPE_TYPE.TABLE
    body_pictures = [
        shape
        for shape in slide.shapes
        if shape.name.startswith("V6_") and shape.shape_type == MSO_SHAPE_TYPE.PICTURE
    ]
    assert {shape.name for shape in body_pictures} == {
        "V6_METHOD_INPUT_FORMULA",
        "V6_METHOD_SFT_FORMULA",
        "V6_RESULTS_C_FORMULA",
    }, "only LaTeX formulas may be raster images in the scientific body"
    pictures = [shape for shape in slide.shapes if shape.shape_type == MSO_SHAPE_TYPE.PICTURE]
    assert {shape.name for shape in pictures} == {
        "FTR_QR_IMAGE",
        "V6_METHOD_INPUT_FORMULA",
        "V6_METHOD_SFT_FORMULA",
        "V6_RESULTS_C_FORMULA",
    }
    assert find_shape(slide, "V6_METHOD_INPUT_FORMULA").image.blob == (
        contract.V6_METHOD_INPUT_FORMULA.read_bytes()
    )
    assert find_shape(slide, "V6_RESULTS_C_FORMULA").image.blob == (
        contract.V6_DELTA_FORMULA.read_bytes()
    )
    assert find_shape(slide, "V6_METHOD_SFT_FORMULA").image.blob == (
        contract.V6_SFT_LOSS_FORMULA.read_bytes()
    )
    assert find_shape(slide, "V6_METHOD_CONTRACT_ICON").shape_type == MSO_SHAPE_TYPE.AUTO_SHAPE
    assert find_shape(slide, "V6_METHOD_ROW_UNIT_HIGHLIGHT").shape_type == MSO_SHAPE_TYPE.AUTO_SHAPE
    assert len(_media_hashes(path)) == 5
    return len(table_names), len(pictures)


def _validate_qr(slide) -> None:
    qr = find_shape(slide, "FTR_QR_IMAGE")
    assert qr.width == qr.height
    assert abs(qr.width / 360000 - 4.32) <= 0.04
    assert sha256(qr.image.blob).hexdigest() == (
        "4bd02bddc64bd1d4b9f23fd29a46709a52d4b702b362519f5beed85e04b538a8"
    )
    assert _hyperlink(qr) == contract.REPOSITORY_URL
    assert _hyperlink(find_shape(slide, "FTR_URL")) == contract.REPOSITORY_URL


def validate_pptx(path: Path = contract.V6_PPTX) -> list[ValidationResult]:
    path = Path(path)
    assert path.is_file(), f"missing PPTX: {path}"
    prs = Presentation(path)
    shape_count = _validate_canvas_and_bounds(prs)
    slide = prs.slides[0]
    _validate_template(path, slide)
    text_count = _validate_typography(slide)
    _validate_content(slide)
    word_count, rounded = _validate_layout(slide)
    marker_count = _validate_results(slide)
    table_count, picture_count = _validate_editability(path, slide)
    _validate_qr(slide)
    return [
        ValidationResult(
            "pptx_canvas",
            f"1 slide, {prs.slide_width / 360000:.2f}x{prs.slide_height / 360000:.2f} cm, {shape_count} objects in bounds",
        ),
        ValidationResult("pptx_template", "official background and conference identity preserved"),
        ValidationResult("pptx_typography", f"{text_count} editable text/table objects checked"),
        ValidationResult("pptx_content", "paper-backed claims and forbidden wording checked"),
        ValidationResult("pptx_layout", f"{word_count} prose tokens, {rounded} rounded body shapes"),
        ValidationResult("pptx_results", f"2 native tables and {marker_count} dumbbell markers checked"),
        ValidationResult(
            "pptx_editability",
            f"{table_count} native tables, {picture_count} retained/LaTeX pictures, no large body raster",
        ),
        ValidationResult("pptx_qr", f"editable QR target={contract.REPOSITORY_URL}"),
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


def validate_pdf(path: Path = contract.V6_PDF) -> list[ValidationResult]:
    path = Path(path)
    assert path.is_file(), f"missing PDF: {path}"
    reader = PdfReader(path)
    assert len(reader.pages) == 1, "PDF must contain exactly one page"
    page = reader.pages[0]
    width = float(page.mediabox.width)
    height = float(page.mediabox.height)
    assert abs(width - contract.PAGE_PT[0]) < 1
    assert abs(height - contract.PAGE_PT[1]) < 1
    text = normalized_text(page.extract_text() or "")
    for token in contract.V6_REQUIRED_TOKENS:
        if token in {
            contract.V6_VALIDATION_NOTE,
            "Single-to-Multi gap: 13.1 → 7.5, reduced by 5.6",
            contract.V6_DIAGNOSTIC_COLUMN,
        }:
            continue
        assert normalized_text(token) in text, f"PDF token missing: {token}"
    for fragment in ("Checks schema-defined types/roles", "removes empty fields", "normalizes slot"):
        assert fragment in text, f"PDF validation fragment missing: {fragment}"
    for fragment in ("Single-to-Multi gap: 13.1", "7.5, reduced by 5.6"):
        assert fragment in text, f"PDF gap fragment missing: {fragment}"
    assert normalized_text(contract.AUTHORS) in text
    fonts, rows = _pdf_font_rows(path)
    assert rows, "PDF contains no font records"
    assert all(re.search(r"\byes\s+yes\s+yes\b", row) for row in rows), (
        "PDF fonts must be embedded, subset, and Unicode-mapped",
        fonts,
    )
    assert any(
        name in fonts.casefold() for name in ("notosans", "noto sans", "liberationsans")
    ), "Noto Sans-compatible font missing from PDF"
    return [
        ValidationResult(
            "pdf",
            f"{width:.0f}x{height:.0f} pt, 1 page, {len(rows)} fonts embedded",
        )
    ]


def validate_png_and_qr(
    png_path: Path = contract.V6_PNG,
    pptx_path: Path = contract.V6_PPTX,
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
        pad = 16
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


def validate_output_directory(path: Path = contract.V6_OUTPUT_DIR) -> ValidationResult:
    path = Path(path)
    assert path.is_dir(), f"missing output directory: {path}"
    expected = {contract.V6_PPTX.name, contract.V6_PDF.name, contract.V6_PNG.name}
    actual = {item.name for item in path.iterdir()}
    assert actual == expected, "final_v6 must contain exactly the three required deliverables"
    return ValidationResult("output_directory", "exactly three final v6 deliverables")


def _json_payload(mode: str, results=None, error: str | None = None) -> dict:
    return {
        "overall_pass": error is None,
        "mode": mode,
        "results": [result._asdict() for result in results or []],
        **({"error": error} if error else {}),
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
    parser = argparse.ArgumentParser(description="Validate the SARGE CCKS 2026 v6 poster")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--pptx-only", action="store_true")
    mode.add_argument("--all", action="store_true")
    parser.add_argument("--pptx", type=Path, default=contract.V6_PPTX)
    parser.add_argument("--pdf", type=Path, default=contract.V6_PDF)
    parser.add_argument("--png", type=Path, default=contract.V6_PNG)
    parser.add_argument("--output-dir", type=Path, default=contract.V6_OUTPUT_DIR)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    mode_name = "all" if args.all else "pptx-only"
    try:
        results = validate_pptx(args.pptx)
        if args.all:
            results.extend(validate_pdf(args.pdf))
            results.extend(validate_png_and_qr(args.png, args.pptx))
            results.append(validate_output_directory(args.output_dir))
        payload = _json_payload(mode_name, results=results)
        status = 0
    except (AssertionError, OSError, subprocess.SubprocessError, ValueError) as exc:
        payload = _json_payload(mode_name, error=str(exc) or exc.__class__.__name__)
        status = 1
    if args.json:
        print(json.dumps(payload, indent=2, ensure_ascii=False))
    else:
        _print_text(payload)
    return status


if __name__ == "__main__":
    sys.exit(main())
