from __future__ import annotations

import argparse
import re
import subprocess
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from zipfile import ZipFile

import award_poster_contract as contract
from PIL import Image
from pptx import Presentation
from pptx.enum.shapes import MSO_SHAPE_TYPE
from pptx.enum.text import MSO_AUTO_SIZE
from pypdf import PdfReader

EMU_PER_INCH = 914400


@dataclass(frozen=True)
class ValidationResult:
    name: str
    detail: str


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


def shape_signature(shape) -> tuple:
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


def media_hashes(path: Path) -> dict[str, str]:
    with ZipFile(path) as archive:
        return {
            name: sha256(archive.read(name)).hexdigest()
            for name in archive.namelist()
            if name.startswith("ppt/media/")
        }


def protected_signatures(path: Path) -> dict[str, tuple]:
    slide = Presentation(path).slides[0]
    return {
        name: shape_signature(find_shape(slide, name))
        for name in sorted(contract.PROTECTED_SHAPES)
    }


def validate_source() -> list[ValidationResult]:
    required_files = (
        contract.PAPER_PDF,
        contract.V2_PPTX,
        contract.V2_PNG,
        contract.TEMPLATE_PPTX,
        contract.QR_IMAGE,
    )
    for path in required_files:
        assert path.is_file(), f"missing source file: {path}"

    paper_text = "\n".join(
        page.extract_text() or "" for page in PdfReader(contract.PAPER_PDF).pages
    )
    for token in contract.SOURCE_REQUIRED_TOKENS:
        assert token in paper_text, f"paper token missing: {token}"

    with Image.open(contract.QR_IMAGE) as image:
        assert image.width == image.height and image.width >= 256
        qr_detail = f"{image.width}x{image.height}"

    prs = Presentation(contract.V2_PPTX)
    assert len(prs.slides) == 1
    assert abs(prs.slide_width / 360000 - contract.PAGE_CM[0]) < 0.01
    assert abs(prs.slide_height / 360000 - contract.PAGE_CM[1]) < 0.01
    slide = prs.slides[0]
    names = {shape.name for shape in recursive_shapes(slide.shapes)}
    expected_names = (
        contract.PROTECTED_SHAPES
        | contract.EDITABLE_HEADER_SHAPES
        | contract.REMOVE_BODY_SHAPES
    )
    assert expected_names <= names, f"v2 shapes missing: {sorted(expected_names - names)}"

    text = slide_text(slide)
    for token in contract.V2_REQUIRED_TOKENS:
        assert token in text, f"v2 token missing: {token}"

    signatures = protected_signatures(contract.V2_PPTX)
    assert all(signatures.values())
    hashes = media_hashes(contract.V2_PPTX)
    assert "ppt/media/image1.jpeg" in hashes
    assert len(hashes) == 2, f"unexpected v2 media inventory: {sorted(hashes)}"

    return [
        ValidationResult("paper", f"{len(contract.SOURCE_REQUIRED_TOKENS)} metrics"),
        ValidationResult("qr_asset", qr_detail),
        ValidationResult("v2", f"{len(names)} recursive shapes"),
        ValidationResult("protected", f"{len(signatures)} shape signatures"),
    ]


def _is_qualifier(name: str) -> bool:
    return any(marker in name for marker in contract.QUALIFIER_NAME_MARKERS)


def _is_caption(name: str) -> bool:
    return any(marker in name for marker in contract.CAPTION_NAME_MARKERS)


def _validate_fonts(slide) -> None:
    for shape in recursive_shapes(slide.shapes):
        if not shape.name.startswith("AW_") or not getattr(shape, "has_text_frame", False):
            continue
        if not shape.text.strip():
            continue
        assert shape.text_frame.auto_size != MSO_AUTO_SIZE.TEXT_TO_FIT_SHAPE, (
            shape.name,
            "shrink-to-fit is forbidden",
        )
        sizes = [
            run.font.size.pt
            for paragraph in shape.text_frame.paragraphs
            for run in paragraph.runs
            if run.text and run.font.size is not None
        ]
        assert sizes, f"explicit font size missing: {shape.name}"
        minimum = 18 if _is_qualifier(shape.name) else 22 if _is_caption(shape.name) else 24
        assert min(sizes) >= minimum, (shape.name, min(sizes), minimum)
        if _is_qualifier(shape.name):
            assert min(sizes) <= 20, (shape.name, "qualifier should remain 18-20 pt")


def _validate_no_full_page_raster(prs) -> None:
    page_area = prs.slide_width * prs.slide_height
    for shape in recursive_shapes(prs.slides[0].shapes):
        if shape.shape_type != MSO_SHAPE_TYPE.PICTURE:
            continue
        assert shape.width * shape.height < page_area * 0.50, (
            shape.name,
            "unexpected large raster picture",
        )


def validate_density(slide) -> ValidationResult:
    x, y, width, height = contract.BODY_BOUNDS_IN
    cols, rows = contract.BODY_GRID
    cell_w = width / cols
    cell_h = height / rows
    occupied: set[tuple[int, int]] = set()

    for shape in recursive_shapes(slide.shapes):
        if not shape.name.startswith("AW_"):
            continue
        if any(marker in shape.name for marker in contract.DENSITY_EXCLUDED_NAME_MARKERS):
            continue
        if shape.shape_type == MSO_SHAPE_TYPE.LINE:
            continue
        left = shape.left / EMU_PER_INCH
        top = shape.top / EMU_PER_INCH
        right = (shape.left + shape.width) / EMU_PER_INCH
        bottom = (shape.top + shape.height) / EMU_PER_INCH
        for col in range(cols):
            cell_left = x + col * cell_w
            cell_right = cell_left + cell_w
            for row in range(rows):
                cell_top = y + row * cell_h
                cell_bottom = cell_top + cell_h
                if right > cell_left and left < cell_right and bottom > cell_top and top < cell_bottom:
                    occupied.add((col, row))

    ratio = len(occupied) / (cols * rows)
    low, high = contract.DENSITY_CELL_RANGE
    assert low <= ratio <= high, f"density {ratio:.3f} outside {low:.2f}-{high:.2f}"

    max_empty_cols = max(
        (sum((col, row) not in occupied for col in range(cols)) for row in range(rows)),
        default=0,
    )
    assert max_empty_cols * cell_w <= width + contract.MAX_UNEXPLAINED_GAP_IN
    return ValidationResult("density", f"{len(occupied)}/{cols * rows}={ratio:.3f}")


def validate_pptx() -> list[ValidationResult]:
    assert contract.V3_PPTX.is_file(), f"missing output: {contract.V3_PPTX}"
    prs = Presentation(contract.V3_PPTX)
    assert len(prs.slides) == 1
    assert abs(prs.slide_width / 360000 - contract.PAGE_CM[0]) < 0.01
    assert abs(prs.slide_height / 360000 - contract.PAGE_CM[1]) < 0.01
    slide = prs.slides[0]
    text = slide_text(slide)
    folded = text.casefold()
    for token in contract.V3_REQUIRED_TOKENS:
        assert token in text, f"v3 token missing: {token}"
    for phrase in contract.FORBIDDEN_CLAIMS:
        assert phrase.casefold() not in folded, f"forbidden claim: {phrase}"

    for shape in recursive_shapes(slide.shapes):
        assert shape.left >= 0 and shape.top >= 0, (shape.name, "negative position")
        assert shape.left + shape.width <= prs.slide_width + 1000, (shape.name, "right bound")
        assert shape.top + shape.height <= prs.slide_height + 1000, (shape.name, "bottom bound")

    assert protected_signatures(contract.V3_PPTX) == protected_signatures(contract.V2_PPTX)
    v2_media = media_hashes(contract.V2_PPTX)
    v3_media = media_hashes(contract.V3_PPTX)
    assert v3_media == v2_media, "v3 must retain only unchanged background and QR media"
    _validate_no_full_page_raster(prs)
    _validate_fonts(slide)
    density = validate_density(slide)
    return [ValidationResult("pptx", f"{len(list(recursive_shapes(slide.shapes)))} shapes"), density]


def validate_pdf() -> list[ValidationResult]:
    assert contract.V3_PDF.is_file(), f"missing output: {contract.V3_PDF}"
    reader = PdfReader(contract.V3_PDF)
    assert len(reader.pages) == 1
    page = reader.pages[0]
    width = float(page.mediabox.width)
    height = float(page.mediabox.height)
    assert abs(width - contract.PAGE_PT[0]) < 1
    assert abs(height - contract.PAGE_PT[1]) < 1
    text = page.extract_text() or ""
    for token in ("SARGE", "85.6", "78.3", "ExactRec", "record binding"):
        assert token in text, f"PDF token missing: {token}"

    fonts = subprocess.run(
        ["pdffonts", str(contract.V3_PDF)],
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    font_rows = [line for line in fonts.splitlines()[2:] if line.strip()]
    assert font_rows and all(re.search(r"\byes\s+yes\s+yes\b", row) for row in font_rows), fonts
    return [ValidationResult("pdf", f"{width:.0f}x{height:.0f} pt, {len(font_rows)} fonts")]


def validate_png_and_qr() -> list[ValidationResult]:
    assert contract.V3_PNG.is_file(), f"missing output: {contract.V3_PNG}"
    with Image.open(contract.V3_PNG) as image:
        assert abs(image.width - 5250) <= 2
        assert abs(image.height - 6450) <= 2
        prs = Presentation(contract.V3_PPTX)
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

        result = zxingcpp.read_barcode(crop)
        assert result is not None, "rendered QR did not decode"
        assert result.text == contract.REPOSITORY_URL, result.text
        detail = f"{image.width}x{image.height}, QR={result.text}"
    return [ValidationResult("png", detail)]


def print_results(results: list[ValidationResult]) -> None:
    for result in results:
        print(f"PASS {result.name}: {result.detail}")


def main() -> None:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--pptx-only", action="store_true")
    mode.add_argument("--all", action="store_true")
    args = parser.parse_args()

    results = validate_source()
    print_results(results)
    results = validate_pptx()
    print_results(results)
    if args.all:
        results = validate_pdf()
        print_results(results)
        results = validate_png_and_qr()
        print_results(results)
    print("overall_pass: true")


if __name__ == "__main__":
    main()
