from __future__ import annotations

import hashlib
import importlib.util
import re
import sys
from pathlib import Path
from zipfile import ZipFile

import pytest
from pptx import Presentation
from pptx.enum.shapes import MSO_AUTO_SHAPE_TYPE, MSO_SHAPE_TYPE
from pptx.enum.text import MSO_AUTO_SIZE

ROOT = Path(__file__).resolve().parents[1]
POSTER_DIR = ROOT / "paper/ccks_2026/poster"
TOOLS_DIR = POSTER_DIR / "tools"
CONTRACT_PATH = TOOLS_DIR / "award_poster_contract.py"
BUILDER_PATH = TOOLS_DIR / "build_sarge_poster_v6.py"


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(TOOLS_DIR))
    try:
        spec.loader.exec_module(module)
    finally:
        sys.path.pop(0)
    return module


@pytest.fixture(scope="module")
def contract():
    return _load_module("award_poster_contract_v6_builder", CONTRACT_PATH)


@pytest.fixture(scope="module")
def built_deck(tmp_path_factory, contract):
    builder = _load_module("build_sarge_poster_v6_test", BUILDER_PATH)
    output = tmp_path_factory.mktemp("poster-v6") / contract.V6_PPTX.name
    source_hash = hashlib.sha256(contract.V5_PPTX.read_bytes()).hexdigest()
    builder.build(output)
    assert hashlib.sha256(contract.V5_PPTX.read_bytes()).hexdigest() == source_hash
    return builder, Presentation(output), output


def _find(slide, name: str):
    for shape in slide.shapes:
        if shape.name == name:
            return shape
    raise AssertionError(f"shape not found: {name}")


def _all_text(slide) -> str:
    chunks: list[str] = []
    for shape in slide.shapes:
        if getattr(shape, "has_text_frame", False):
            chunks.append(shape.text)
        if getattr(shape, "has_table", False):
            chunks.extend(cell.text for row in shape.table.rows for cell in row.cells)
    return re.sub(r"\s+", " ", "\n".join(chunks)).strip()


def _runs(shape):
    return [
        run
        for paragraph in shape.text_frame.paragraphs
        for run in paragraph.runs
        if run.text
    ]


def test_v6_builder_module_exists() -> None:
    assert BUILDER_PATH.is_file()


def test_v6_builder_defaults_to_the_final_v6_pptx(contract) -> None:
    builder = _load_module("build_sarge_poster_v6_default", BUILDER_PATH)
    assert builder.DEFAULT_OUTPUT == contract.V6_PPTX


def test_v6_preserves_official_canvas_background_and_conference_identity(
    built_deck, contract
) -> None:
    _, prs, output = built_deck
    assert len(prs.slides) == 1
    assert prs.slide_width / 360000 == pytest.approx(contract.PAGE_CM[0], abs=0.01)
    assert prs.slide_height / 360000 == pytest.approx(contract.PAGE_CM[1], abs=0.01)
    with ZipFile(output) as zf:
        background = zf.read("ppt/media/image1.jpeg")
    assert hashlib.sha256(background).hexdigest() == (
        "75c64d300ba3826ee6da34bb658e081c35ce01724ed1570e9564ebd0f185ded7"
    )
    text = _all_text(prs.slides[0])
    assert "2026全国知识图谱与语义计算大会" in text
    assert "China Conference on Knowledge Graph and Semantic Computing" in text
    assert "西安 8.21-8.23" in text


def test_v6_header_is_exact_and_large(built_deck, contract) -> None:
    _, prs, _ = built_deck
    slide = prs.slides[0]
    title = _find(slide, "HDR_TITLE")
    authors = _find(slide, "HDR_AUTHORS")
    affiliations = _find(slide, "HDR_AFFILIATIONS")
    assert title.text == contract.TITLE
    assert authors.text == contract.AUTHORS
    assert contract.AFFILIATIONS in affiliations.text
    assert f"* Corresponding author: {contract.CONTACT_EMAIL}" in affiliations.text
    assert min(run.font.size.pt for run in _runs(title)) >= contract.V6_TITLE_PT
    assert min(run.font.size.pt for run in _runs(authors)) >= contract.V6_AUTHORS_PT
    assert min(run.font.size.pt for run in _runs(affiliations)) >= contract.V6_AFFILIATIONS_PT


def test_v6_body_is_native_editable_with_only_latex_formula_images(
    built_deck, contract
) -> None:
    _, prs, output = built_deck
    slide = prs.slides[0]
    names = {shape.name for shape in slide.shapes}
    assert not any(name.startswith("V5_") for name in names)
    assert any(name.startswith("V6_") for name in names)
    body_pictures = [
        shape
        for shape in slide.shapes
        if shape.shape_type == MSO_SHAPE_TYPE.PICTURE and shape.name.startswith("V6_")
    ]
    assert {shape.name for shape in body_pictures} == {
        "V6_METHOD_INPUT_FORMULA",
        "V6_METHOD_SFT_FORMULA",
        "V6_RESULTS_C_FORMULA",
    }
    slide_pictures = [
        shape for shape in slide.shapes if shape.shape_type == MSO_SHAPE_TYPE.PICTURE
    ]
    assert {shape.name for shape in slide_pictures} == {
        "FTR_QR_IMAGE",
        "V6_METHOD_INPUT_FORMULA",
        "V6_METHOD_SFT_FORMULA",
        "V6_RESULTS_C_FORMULA",
    }
    assert all(
        _find(slide, name).shape_type == MSO_SHAPE_TYPE.TABLE
        for name in (
            "V6_MOTIVATION_WRONG_TABLE",
            "V6_MOTIVATION_CORRECT_TABLE",
            "V6_MOTIVATION_SOURCE_TABLE",
            "V6_METHOD_OUTPUT_TABLE",
            "V6_RESULTS_A_TABLE",
            "V6_RESULTS_C_TABLE",
        )
    )
    with ZipFile(output) as zf:
        media = sorted(name for name in zf.namelist() if name.startswith("ppt/media/"))
    assert len(media) == 5
    assert contract.V6_METHOD_INPUT_FORMULA.read_bytes() in {
        _find(slide, "V6_METHOD_INPUT_FORMULA").image.blob
    }


def test_v6_takehome_emphasis_uses_semantic_colors(built_deck, contract) -> None:
    _, prs, _ = built_deck
    shape = _find(prs.slides[0], "V6_TAKEHOME_TEXT")
    assert shape.text == contract.V6_TAKEHOME
    run_map = {run.text: str(run.font.color.rgb) for run in _runs(shape)}
    for token in contract.V6_TAKEHOME_EMPHASIS:
        assert token in run_map
    assert run_map["wrong event rows"] == contract.V6_PALETTE["red"]
    assert run_map["5.1 Multi-Event F1 points"] == contract.V6_PALETTE["teal"]
    assert run_map["ExactRec"] == contract.V6_PALETTE["teal"]
    assert shape.top / 914400 >= contract.V6_WHITE_BODY_TOP
    assert (shape.top + shape.height) / 914400 <= contract.V6_WHITE_BODY_BOTTOM


def test_v6_scientific_copy_is_complete_and_forbidden_copy_is_absent(
    built_deck, contract
) -> None:
    _, prs, _ = built_deck
    text = _all_text(prs.slides[0])
    for token in contract.V6_REQUIRED_TOKENS:
        assert token in text, token
    folded = text.casefold()
    for phrase in contract.V6_FORBIDDEN_CLAIMS:
        assert phrase.casefold() not in folded, phrase
    assert "Same base" not in text
    assert "24.8" not in text
    assert re.search(r"(?<!\d)3\.3(?!\d)", text) is None


def test_v6_body_typography_word_count_and_card_reduction(built_deck, contract) -> None:
    _, prs, _ = built_deck
    slide = prs.slides[0]
    rounded = 0
    words: list[str] = []
    for shape in slide.shapes:
        if shape.name.startswith("V6_") and shape.shape_type == MSO_SHAPE_TYPE.AUTO_SHAPE:
            rounded += shape.auto_shape_type == MSO_AUTO_SHAPE_TYPE.ROUNDED_RECTANGLE
        if not shape.name.startswith("V6_") or not getattr(shape, "has_text_frame", False):
            continue
        if shape.text.strip():
            words.extend(re.findall(r"[A-Za-z0-9]+(?:[-'][A-Za-z0-9]+)*", shape.text))
            assert shape.text_frame.auto_size in {None, MSO_AUTO_SIZE.NONE}
            for run in _runs(shape):
                assert run.font.name == contract.V6_FONT
                assert run.font.size is not None
                assert run.font.size.pt >= contract.V6_QUALIFIER_PT
                assert run.font.size.pt.is_integer()
        if not shape.name.startswith("V6_") or not getattr(shape, "has_table", False):
            continue
        for row in shape.table.rows:
            for cell in row.cells:
                for paragraph in cell.text_frame.paragraphs:
                    for run in paragraph.runs:
                        if not run.text:
                            continue
                        assert run.font.name == contract.V6_FONT
                        assert run.font.size is not None
                        assert run.font.size.pt.is_integer()
    assert rounded <= contract.V6_MAX_ROUNDED_BODY_SHAPES
    low, high = contract.V6_WORD_COUNT_RANGE
    assert low <= len(words) <= high, len(words)


def test_v6_method_is_one_comparison_flow_not_repeated_cards(built_deck, contract) -> None:
    _, prs, _ = built_deck
    slide = prs.slides[0]
    text = _all_text(slide)
    assert "A common role-wise pipeline" in text
    assert "SARGE: schema-grounded event-table generation" in text
    assert contract.V6_METHOD_CORE_CHANGE in text
    assert contract.V6_VALIDATION_NOTE in text
    for label in contract.V6_CONVENTIONAL_FLOW + contract.V6_METHOD_FLOW:
        assert label in text
    assert text.count(contract.V6_GROUNDING_NOTE) == 1
    assert "ONE CONTRACT" not in text
    assert not any("HEXAGON" in shape.name for shape in slide.shapes)
    assert "No constrained decoding" in text
    assert "Loss on answer tokens only" in text
    assert _find(slide, "V6_METHOD_SFT_FORMULA").shape_type == MSO_SHAPE_TYPE.PICTURE
    prompt = _find(slide, "V6_METHOD_PROMPT_BG")
    sft = _find(slide, "V6_METHOD_SFT_BG")
    assert prompt.width > _find(slide, "V6_METHOD_DECODE_BG").width
    assert sft.width > _find(slide, "V6_METHOD_DECODE_BG").width


def test_v6_reuses_the_paper_figures_as_native_scientific_stages(
    built_deck, contract
) -> None:
    _, prs, _ = built_deck
    slide = prs.slides[0]
    text = _all_text(slide)
    for stage in contract.V6_MOTIVATION_STAGES:
        assert stage in text
    assert contract.V6_MOTIVATION_CONSEQUENCE in text
    assert _find(slide, "V6_MOTIVATION_SOURCE_TABLE").shape_type == MSO_SHAPE_TYPE.TABLE
    for index, (title, body) in enumerate(contract.V6_MOTIVATION_ANCHORS, start=1):
        assert title in text
        assert body in text
        assert _find(slide, f"V6_MOTIVATION_ANCHOR_{index}_MARKER")
    assert _find(slide, "V6_METHOD_CONTRACT_ICON").shape_type == MSO_SHAPE_TYPE.AUTO_SHAPE
    assert _find(slide, "V6_METHOD_ROW_UNIT_HIGHLIGHT").shape_type == MSO_SHAPE_TYPE.AUTO_SHAPE


def test_v6_results_use_table_and_dumbbell_without_bars(built_deck, contract) -> None:
    builder, prs, _ = built_deck
    slide = prs.slides[0]
    names = {shape.name for shape in slide.shapes}
    assert not any("_BAR_" in name for name in names)
    for tick in (70, 75, 80, 85, 90, 95):
        assert _find(slide, f"V6_RESULTS_B_TICK_{tick}").text == str(tick)
    assert _find(slide, "V6_RESULTS_B_AXIS_NOTE").text == "ZOOMED AXIS 70–95"
    for row in contract.V6_MULTI_EVENT:
        for metric in ("single", "multi"):
            marker = _find(slide, f"V6_RESULTS_B_{row['model'].upper()}_{metric.upper()}_MARKER")
            expected_x = builder.multi_event_x(row[metric])
            assert marker.left / 914400 == pytest.approx(expected_x - 0.14, abs=0.01)
    text = _all_text(slide)
    assert "5.1 points over EPAL on ChFinAnn" in text
    assert "Single-to-Multi gap: 13.1 → 7.5, reduced by 5.6" in text
    assert "ChFinAnn · 85.6 ± 0.4 · highest listed" in text
    assert "DuEE-Fin · 78.3 ± 0.4 · below SEELE 80.8" in text
    assert "Mean ± std over seeds 13/17/42" in text
    assert contract.V6_DIAGNOSTIC_COLUMN in text
    assert contract.V6_ROLE_F1_QUESTION in text
    assert contract.V6_EXACTREC_QUESTION in text
    assert contract.V6_EVIDENCE_SCOPE in text
    assert "35.1†" in text
    assert len(_find(slide, "V6_RESULTS_A_TABLE").table.rows) == 7


def test_v6_white_body_has_no_underfilled_primary_scientific_regions(
    built_deck, contract
) -> None:
    _, prs, _ = built_deck
    slide = prs.slides[0]
    source = _find(slide, "V6_MOTIVATION_SOURCE_TABLE")
    assert source.height / 914400 >= 2.20
    prompt = _find(slide, "V6_METHOD_PROMPT_BG")
    output = _find(slide, "V6_METHOD_OUTPUT_BG")
    assert prompt.left / 914400 <= 1.30
    assert (output.left + output.width) / 914400 >= 33.65
    method_height = contract.V6_BANDS["method"][1]
    results_height = contract.V6_BANDS["results"][1]
    assert method_height > results_height


def test_v6_all_scientific_body_objects_stay_in_the_white_template_region(
    built_deck, contract
) -> None:
    _, prs, _ = built_deck
    for shape in prs.slides[0].shapes:
        if not shape.name.startswith("V6_"):
            continue
        top = shape.top / 914400
        bottom = (shape.top + shape.height) / 914400
        assert top >= contract.V6_WHITE_BODY_TOP - 0.01, shape.name
        assert bottom <= contract.V6_WHITE_BODY_BOTTOM + 0.01, shape.name


def test_v6_qr_target_is_preserved_and_print_sized(built_deck, contract) -> None:
    _, prs, _ = built_deck
    slide = prs.slides[0]
    qr = _find(slide, "FTR_QR_IMAGE")
    assert qr.width == qr.height
    assert qr.width / 360000 == pytest.approx(4.32, abs=0.04)
    assert hashlib.sha256(qr.image.blob).hexdigest() == (
        "4bd02bddc64bd1d4b9f23fd29a46709a52d4b702b362519f5beed85e04b538a8"
    )
    rel_id = qr._element.nvPicPr.cNvPr.hlinkClick.get(
        "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"
    )
    assert rel_id and slide.part.rels[rel_id].target_ref == contract.REPOSITORY_URL


def test_v6_all_top_level_objects_are_inside_the_canvas(built_deck) -> None:
    _, prs, _ = built_deck
    for shape in prs.slides[0].shapes:
        assert shape.left >= 0, shape.name
        assert shape.top >= 0, shape.name
        assert shape.left + shape.width <= prs.slide_width + 1000, shape.name
        assert shape.top + shape.height <= prs.slide_height + 1000, shape.name
