from __future__ import annotations

from pathlib import Path
import sys

from PIL import Image
from pypdf import PdfReader
from pptx import Presentation


ROOT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parents[4]
POSTER_DIR = ROOT / "paper/ccks_2026/poster"
SOURCE_PDF = ROOT / "paper/SARGE_CCKS2026.pdf"
QR_IMAGE = POSTER_DIR / "assets/github_repository_qr.png"

PLACEHOLDERS = (
    "文章标题放在这里",
    "张三",
    "第二作者",
    "作者联系",
    "lorem",
    "ipsum",
    "QR pending",
    "QR 待补充",
    "Public link pending",
    "公开链接待补充",
)

COMMON_REQUIRED = (
    "85.6±0.4",
    "78.3±0.4",
    "81.7",
    "24.8 → 86.0",
    "3.3 → 78.0",
    "Δrecord = 29.5",
    "Δrecord = 35.1",
    "ExactRec",
    "github.com/emmmdty/SARGE",
    "yue.zhao@hit.edu.cn",
)

LANG_REQUIRED = {
    "zh": (
        "童佳锴",
        "覃梦婷",
        "扈永琪",
        "万雪瑶",
        "赵悦",
        "改善但未解决 record binding",
    ),
    "en": (
        "Jiakai Tong",
        "Mengting Qin",
        "Yongqi Hu",
        "Xueyao Wan",
        "Yue Zhao",
        "improves but does not solve record binding",
        "Predicted events / WRONG",
        "Gold events / CORRECT",
    ),
}


def slide_text(prs: Presentation) -> str:
    parts = []
    for slide in prs.slides:
        for shape in slide.shapes:
            if getattr(shape, "has_text_frame", False):
                parts.append(shape.text)
    return "\n".join(parts)


def validate_pptx(lang: str) -> None:
    path = POSTER_DIR / f"SARGE_CCKS2026_poster_{lang}.pptx"
    prs = Presentation(path)
    assert len(prs.slides) == 1
    assert abs(prs.slide_width / 360000 - 88.9) < 0.01
    assert abs(prs.slide_height / 360000 - 109.22) < 0.01

    text = slide_text(prs)
    for placeholder in PLACEHOLDERS:
        assert placeholder.lower() not in text.lower(), (path.name, placeholder)
    for required in COMMON_REQUIRED + LANG_REQUIRED[lang]:
        assert required in text, (path.name, required)

    for shape in prs.slides[0].shapes:
        assert shape.left >= 0 and shape.top >= 0, (path.name, shape.name)
        assert shape.left + shape.width <= prs.slide_width + 1000, (path.name, shape.name)
        assert shape.top + shape.height <= prs.slide_height + 1000, (path.name, shape.name)

    print(
        f"PPTX OK {path.name}: 1 slide, "
        f"{prs.slide_width / 360000:.2f}×{prs.slide_height / 360000:.2f} cm, "
        f"{len(prs.slides[0].shapes)} shapes"
    )


def validate_pdf(lang: str) -> None:
    path = POSTER_DIR / f"SARGE_CCKS2026_poster_{lang}.pdf"
    reader = PdfReader(path)
    assert len(reader.pages) == 1
    page = reader.pages[0]
    width = float(page.mediabox.width)
    height = float(page.mediabox.height)
    assert abs(width - 2520) < 1
    assert abs(height - 3096) < 1
    text = page.extract_text() or ""
    for token in ("85.6", "78.3", "ExactRec", "SARGE"):
        assert token in text, (path.name, token)
    print(f"PDF OK  {path.name}: 1 page, {width:.1f}×{height:.1f} pt")


def validate_source_metrics() -> None:
    source_text = "\n".join(page.extract_text() or "" for page in PdfReader(SOURCE_PDF).pages)
    for token in ("85.6", "78.3", "81.7", "24.8", "3.3", "29.5", "35.1"):
        assert token in source_text, token
    print("Source metric cross-check OK")


def validate_qr_asset() -> None:
    with Image.open(QR_IMAGE) as image:
        assert image.width == image.height
        assert image.width >= 256
    print(f"QR asset OK {QR_IMAGE.name}: {image.width}×{image.height}")


def main() -> None:
    validate_source_metrics()
    validate_qr_asset()
    for language in ("zh", "en"):
        validate_pptx(language)
        validate_pdf(language)


if __name__ == "__main__":
    main()
