from __future__ import annotations

import importlib.util
import sys
from hashlib import sha256
from itertools import pairwise
from pathlib import Path

import pytest
from pptx import Presentation
from pptx.enum.shapes import MSO_AUTO_SHAPE_TYPE, MSO_SHAPE_TYPE
from pptx.enum.text import MSO_AUTO_SIZE

ROOT = Path(__file__).resolve().parents[1]
TOOLS_DIR = ROOT / "paper/ccks_2026/poster/tools"
BUILDER_PATH = TOOLS_DIR / "build_sarge_poster_v5.py"
sys.path.insert(0, str(TOOLS_DIR))


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


contract = _load_module("award_poster_contract_v5_builder_test", TOOLS_DIR / "award_poster_contract.py")
validator = _load_module(
    "validate_sarge_poster_award_v5_builder_test",
    TOOLS_DIR / "validate_sarge_poster_award.py",
)


def _find(slide, name: str):
    for shape in validator.recursive_shapes(slide.shapes):
        if shape.name == name:
            return shape
    raise AssertionError(f"missing shape: {name}")


def _all_text(slide) -> str:
    return validator.slide_text(slide)


def _font_sizes(shape) -> list[float]:
    return [
        run.font.size.pt
        for paragraph in shape.text_frame.paragraphs
        for run in paragraph.runs
        if run.text and run.font.size is not None
    ]


def _font_names(shape) -> list[str | None]:
    return [
        run.font.name
        for paragraph in shape.text_frame.paragraphs
        for run in paragraph.runs
        if run.text
    ]


def _fill_rgb(shape) -> str | None:
    try:
        return str(shape.fill.fore_color.rgb)
    except (AttributeError, TypeError, ValueError):
        return None


def _sha256(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


@pytest.fixture(scope="module")
def built_deck(tmp_path_factory):
    assert BUILDER_PATH.is_file(), "v5 builder module has not been implemented"
    builder = _load_module("build_sarge_poster_v5_test", BUILDER_PATH)

    source_digest = _sha256(contract.V2_PPTX)
    default_digest = _sha256(builder.DEFAULT_OUTPUT) if builder.DEFAULT_OUTPUT.is_file() else None
    output = tmp_path_factory.mktemp("sarge_poster_v5") / contract.V5_PPTX.name
    assert output != builder.DEFAULT_OUTPUT
    assert builder.build(output) == output
    assert output.is_file()
    assert _sha256(contract.V2_PPTX) == source_digest
    if default_digest is not None:
        assert _sha256(builder.DEFAULT_OUTPUT) == default_digest
    else:
        assert not builder.DEFAULT_OUTPUT.exists()
    return builder, Presentation(output), output


def test_v5_builder_module_exists() -> None:
    assert BUILDER_PATH.is_file(), "v5 builder module has not been implemented"


def test_v5_default_output_path_is_new_and_versioned() -> None:
    builder = _load_module("build_sarge_poster_v5_default_path_test", BUILDER_PATH)

    assert builder.DEFAULT_OUTPUT == contract.V5_PPTX
    assert builder.DEFAULT_OUTPUT not in {
        contract.V2_PPTX,
        contract.V3_PPTX,
        contract.V4_PPTX,
    }


def test_v5_keeps_official_canvas_and_protected_source_shapes(built_deck) -> None:
    _, prs, output = built_deck

    assert len(prs.slides) == 1
    assert prs.slide_width / 360000 == pytest.approx(contract.PAGE_CM[0], abs=0.01)
    assert prs.slide_height / 360000 == pytest.approx(contract.PAGE_CM[1], abs=0.01)
    assert validator.protected_signatures(output) == validator.protected_signatures(
        contract.V2_PPTX
    )


def test_v5_replaces_only_legacy_body_takehome_and_envelope_shapes(built_deck) -> None:
    _, prs, _ = built_deck
    slide = prs.slides[0]
    output_names = {shape.name for shape in validator.recursive_shapes(slide.shapes)}
    source_names = {
        shape.name
        for shape in validator.recursive_shapes(Presentation(contract.V2_PPTX).slides[0].shapes)
    }

    assert not (contract.REMOVE_BODY_SHAPES & output_names)
    assert not ({name for name in contract.EDITABLE_HEADER_SHAPES if name.startswith("TAKEHOME_")} & output_names)
    assert "HDR_CORRESPONDING_SYMBOL" not in output_names
    assert {"HDR_TITLE", "HDR_AUTHORS", "HDR_AFFILIATIONS"} <= output_names
    assert all(name.startswith("V5_") for name in output_names - source_names)


def test_v5_header_and_takehome_are_readable_and_complete(built_deck) -> None:
    _, prs, _ = built_deck
    slide = prs.slides[0]
    title = _find(slide, "HDR_TITLE")
    authors = _find(slide, "HDR_AUTHORS")
    affiliations = _find(slide, "HDR_AFFILIATIONS")
    takehome = _find(slide, "V5_TAKEHOME_TEXT")

    assert title.text == contract.TITLE
    assert "Yue Zhao¹²*" in authors.text
    assert "* Corresponding author:" in affiliations.text
    assert contract.CONTACT_EMAIL in affiliations.text
    assert takehome.text == contract.V5_TAKEHOME
    assert min(_font_sizes(title)) >= contract.V5_TITLE_PT
    assert min(_font_sizes(authors)) >= contract.V5_AUTHORS_PT
    assert min(_font_sizes(affiliations)) >= contract.V5_AFFILIATIONS_PT
    assert _find(slide, "V5_TAKEHOME_BG").auto_shape_type == MSO_AUTO_SHAPE_TYPE.ROUNDED_RECTANGLE
    assert _find(slide, "V5_TAKEHOME_LABEL_BG").auto_shape_type == MSO_AUTO_SHAPE_TYPE.ROUNDED_RECTANGLE


def test_v5_authors_use_one_unified_arial_run_and_standard_marker(built_deck) -> None:
    _, prs, _ = built_deck
    authors = _find(prs.slides[0], "HDR_AUTHORS")
    runs = [
        run
        for paragraph in authors.text_frame.paragraphs
        for run in paragraph.runs
        if run.text
    ]
    assert len(runs) == 1
    assert runs[0].text.endswith("Yue Zhao¹²*")
    assert runs[0].font.name == "Arial"
    assert runs[0].font.size is not None
    assert runs[0].font.size.pt >= contract.V5_AUTHORS_PT


def test_v5_contains_the_complete_evidence_contract_without_overclaims(built_deck) -> None:
    _, prs, _ = built_deck
    text = _all_text(prs.slides[0])
    folded = text.casefold()

    for token in contract.V5_REQUIRED_TOKENS:
        assert token in text, f"required v5 token missing: {token}"
    for phrase in contract.V5_FORBIDDEN_CLAIMS:
        assert phrase.casefold() not in folded, f"forbidden claim present: {phrase}"
    for reason in contract.V5_MOTIVATION["reasons"]:
        assert reason in text
    assert contract.V5_MOTIVATION["research_gap"] in text
    assert contract.V5_MOTIVATION["contribution"] in text
    for heading, contribution in contract.V5_CONTRIBUTIONS:
        assert heading in text
        assert contribution in text
    for message in contract.V5_CONCLUSION_MESSAGES:
        assert message in text


def test_v5_equity_pledge_example_names_roles_and_distinguishes_end_dates(
    built_deck,
) -> None:
    _, prs, _ = built_deck
    slide = prs.slides[0]
    wrong = _find(slide, "V5_MOTIVATION_WRONG_ROW").text
    correct = _find(slide, "V5_MOTIVATION_CORRECT_ROW").text

    assert "15M | Guotai Junan" in wrong
    assert "8M | CITIC" in wrong
    assert "15M | CITIC" in correct
    assert "8M | Guotai Junan" in correct
    assert "06-04" in wrong and "05-19" in correct


def test_v5_bands_follow_the_vertical_narrative_and_method_dominates(built_deck) -> None:
    _, prs, _ = built_deck
    slide = prs.slides[0]
    bands = [
        _find(slide, "V5_MOTIVATION_BAND"),
        _find(slide, "V5_METHOD_BAND"),
        _find(slide, "V5_RESULTS_BAND"),
        _find(slide, "V5_CONCLUSION_BAND"),
    ]

    assert [band.name for band in bands] == [
        "V5_MOTIVATION_BAND",
        "V5_METHOD_BAND",
        "V5_RESULTS_BAND",
        "V5_CONCLUSION_BAND",
    ]
    assert all(first.top + first.height < second.top for first, second in pairwise(bands))
    assert bands[1].height == max(band.height for band in bands)
    scientific_body_height = bands[-1].top + bands[-1].height - bands[0].top
    assert 0.34 <= bands[1].height / scientific_body_height <= 0.40

    headings = [
        "1 Motivation — Correct values can still form wrong rows",
        "2 Method — Schema grounding governs the event-table pipeline",
        "3 Results — Competitive overall; +5.1 multi-event F1 over EPAL on ChFinAnn",
        "4 Conclusion — One table contract clarifies both gains and limits",
    ]
    text = _all_text(slide)
    assert all(heading in text for heading in headings)


def test_v5_text_uses_explicit_arial_sizes_without_shrink_to_fit(built_deck) -> None:
    _, prs, _ = built_deck
    slide = prs.slides[0]

    for shape in validator.recursive_shapes(slide.shapes):
        if not shape.name.startswith("V5_") or not getattr(shape, "has_text_frame", False):
            continue
        if not shape.text.strip():
            continue
        assert shape.text_frame.auto_size != MSO_AUTO_SIZE.TEXT_TO_FIT_SHAPE, shape.name
        sizes = _font_sizes(shape)
        fonts = _font_names(shape)
        assert sizes, f"explicit font size missing: {shape.name}"
        assert fonts and all(font == "Arial" for font in fonts), (shape.name, fonts)
        if "_QUALIFIER" in shape.name:
            minimum = contract.V5_QUALIFIER_MIN_PT
        elif "_CHART_" in shape.name or "_CAPTION" in shape.name:
            minimum = contract.V5_CHART_CAPTION_MIN_PT
        else:
            minimum = contract.V5_BODY_MIN_PT
        assert min(sizes) >= minimum, (shape.name, min(sizes), minimum)


def test_v5_uses_deliberate_editable_shapes_and_only_formula_media(built_deck) -> None:
    _, prs, output = built_deck
    slide = prs.slides[0]
    page_area = prs.slide_width * prs.slide_height

    output_hashes = set(validator.media_hashes(output).values())
    expected_hashes = set(validator.media_hashes(contract.V2_PPTX).values()) | {
        _sha256(path) for path in contract.FORMULA_IMAGES
    }
    assert output_hashes == expected_hashes
    formula_names = {
        "V5_METHOD_STAGE_1_INPUT_FORMULA",
        "V5_METHOD_STAGE_1_CUES_FORMULA",
        "V5_RESULTS_C_DELTA_FORMULA",
    }
    for shape in validator.recursive_shapes(slide.shapes):
        if shape.shape_type == MSO_SHAPE_TYPE.PICTURE:
            assert shape.width * shape.height < page_area * 0.50, shape.name
        if shape.name in formula_names:
            assert "LaTeX formula" in shape._element.nvPicPr.cNvPr.get("descr", "")
            continue
        if not shape.name.startswith("V5_"):
            continue
        assert shape.shape_type != MSO_SHAPE_TYPE.PICTURE, shape.name
        assert "ICON" not in shape.name.upper()
        assert "<a:outerShdw" not in shape._element.xml
        assert "<a:gradFill" not in shape._element.xml


def test_v5_native_charts_have_axes_labels_data_encoding_and_error_bars(built_deck) -> None:
    builder, prs, _ = built_deck
    slide = prs.slides[0]
    text = _all_text(slide)
    method_key = lambda value: value.upper().replace("-", "_")

    for dataset, value_key in (("CHFINANN", "chfinann"), ("DUEE_FIN", "duee_fin")):
        tick_lines = {
            tick: _find(slide, f"V5_RESULTS_A_{dataset}_CHART_TICK_LINE_{tick}")
            for tick in (60, 70, 80, 90)
        }
        for tick in (60, 70, 80, 90):
            assert _find(slide, f"V5_RESULTS_A_{dataset}_CHART_TICK_{tick}").text == str(tick)
        x_min = tick_lines[60].left
        x_max = tick_lines[90].left
        for row in contract.V5_OVERALL_F1_DATA:
            key = method_key(row["method"])
            bar = _find(slide, f"V5_RESULTS_A_{dataset}_CHART_BAR_{key}")
            expected_right = x_min + (row[value_key] - 60) / 30 * (x_max - x_min)
            assert bar.left == pytest.approx(x_min, abs=1500)
            assert bar.left + bar.width == pytest.approx(expected_right, abs=18000)
            expected_color = (
                builder.TEAL
                if row["method"] == "SARGE"
                else builder.NAVY
                if row["method"] == "SEELE"
                else builder.BASELINE_GRAY
            )
            assert _fill_rgb(bar) == expected_color
        assert _find(slide, f"V5_RESULTS_A_{dataset}_CHART_ERROR_BAR").shape_type == MSO_SHAPE_TYPE.LINE
        assert _find(slide, f"V5_RESULTS_A_{dataset}_CHART_ERROR_CAP_LEFT").shape_type == MSO_SHAPE_TYPE.LINE
        assert _find(slide, f"V5_RESULTS_A_{dataset}_CHART_ERROR_CAP_RIGHT").shape_type == MSO_SHAPE_TYPE.LINE

    for tick in (70, 80, 90):
        assert _find(slide, f"V5_RESULTS_B_CHART_Y_TICK_{tick}").text == str(tick)
        assert _find(slide, f"V5_RESULTS_B_CHART_Y_TICK_LINE_{tick}").shape_type == MSO_SHAPE_TYPE.LINE
    multi_event_rows = {
        row["method"]: row for row in contract.V5_MULTI_EVENT_DATA["rows"]
    }
    for row in multi_event_rows.values():
        for metric in ("F1_S", "F1_M"):
            _find(slide, f"V5_RESULTS_B_CHART_BAR_{row['method'].upper()}_{metric}")
    f1_m_gain = multi_event_rows["SARGE"]["f1_m"] - multi_event_rows["EPAL"]["f1_m"]
    gap_reduction = multi_event_rows["EPAL"]["gap"] - multi_event_rows["SARGE"]["gap"]
    assert f"+{f1_m_gain:.1f} F1(M.)" in text
    assert f"{gap_reduction:.1f}-point smaller S–M gap" in text
    assert "Diagnostic gap, not a pure binding-error estimate" in text
    assert _find(slide, "V5_RESULTS_A_CHFINANN_CHART_TITLE").text == (
        "ChFinAnn F1 (SARGE: mean ± std, 3 seeds)"
    )
    assert _find(slide, "V5_RESULTS_A_DUEE_FIN_CHART_TITLE").text == (
        "DuEE-Fin F1 (SARGE: mean ± std, 3 seeds)"
    )
    assert _find(slide, "V5_RESULTS_A_PROVENANCE_QUALIFIER").text == (
        "Baselines: reported values [7,10,13,15,18]; SARGE seeds 13/17/42."
    )
    assert _find(slide, "V5_RESULTS_C_ALIGNMENT_LABEL").text == (
        "Same backend · No SFT → answer-token SFT"
    )


def test_v5_defines_custom_method_and_record_terms_at_first_use(built_deck) -> None:
    _, prs, _ = built_deck
    slide = prs.slides[0]
    inputs = _find(slide, "V5_METHOD_STAGE_1_TEXT")
    output_heading = _find(slide, "V5_METHOD_STAGE_5_TITLE")
    input_formula = _find(slide, "V5_METHOD_STAGE_1_INPUT_FORMULA")
    cues_formula = _find(slide, "V5_METHOD_STAGE_1_CUES_FORMULA")
    cues_qualifier = _find(slide, "V5_METHOD_STAGE_1_QUALIFIER")
    delta_formula = _find(slide, "V5_RESULTS_C_DELTA_FORMULA")
    takehome = _find(slide, "V5_TAKEHOME_TEXT")
    contribution = _find(slide, "V5_MOTIVATION_CONTRIBUTION_3")

    assert "document" in inputs.text and "closed schema" in inputs.text
    assert "document D plus closed schema S" in input_formula._element.nvPicPr.cNvPr.get(
        "descr", ""
    )
    assert "surface candidates C_K(D) and slot prior P_D" in (
        cues_formula._element.nvPicPr.cNvPr.get("descr", "")
    )
    assert cues_qualifier.text == "C_K(D): candidates  ·  P_D: role-slot prior"
    assert output_heading.text == "Fixed-slot table"
    assert "ExactRec (strict event-row match)" in takehome.text
    assert "Δrecord (= F1 − ExactRec)" in contribution.text
    assert "Delta_record equals F1 minus ExactRec" in (
        delta_formula._element.nvPicPr.cNvPr.get("descr", "")
    )

    for shape in (inputs, output_heading, takehome, contribution):
        assert shape.text_frame.auto_size != MSO_AUTO_SIZE.TEXT_TO_FIT_SHAPE
        sizes = _font_sizes(shape)
        assert sizes
        minimum = (
            contract.V5_QUALIFIER_MIN_PT
            if "_QUALIFIER" in shape.name
            else contract.V5_BODY_MIN_PT
        )
        assert min(sizes) >= minimum


def test_v5_multi_event_chart_serializes_solid_colors_and_data_heights(built_deck) -> None:
    _, prs, _ = built_deck
    slide = prs.slides[0]
    expected_fills = {
        ("EPAL", "F1_S"): "D8DEE8",
        ("EPAL", "F1_M"): "8D99AB",
        ("SARGE", "F1_S"): "A9DDD7",
        ("SARGE", "F1_M"): "098F88",
    }
    rows = {row["method"]: row for row in contract.V5_MULTI_EVENT_DATA["rows"]}
    y70 = _find(slide, "V5_RESULTS_B_CHART_Y_TICK_LINE_70").top
    y90 = _find(slide, "V5_RESULTS_B_CHART_Y_TICK_LINE_90").top
    emu_per_point = (y70 - y90) / 20

    legend = _find(slide, "V5_RESULTS_B_CHART_LEGEND")
    assert legend.text == "F1(S.): single/light · F1(M.): multi/dark"
    for method, row in rows.items():
        for metric, data_key in (("F1_S", "f1_s"), ("F1_M", "f1_m")):
            bar = _find(slide, f"V5_RESULTS_B_CHART_BAR_{method}_{metric}")
            expected_height = (row[data_key] - 70) * emu_per_point
            expected_fill = expected_fills[(method, metric)]
            assert bar.top + bar.height == pytest.approx(y70, abs=18000)
            assert bar.height == pytest.approx(expected_height, abs=18000)
            assert _fill_rgb(bar) == expected_fill
            assert f'val="{expected_fill}"' in bar._element.xml
            assert "<a:alpha" not in bar._element.xml


def test_v5_preflight_requires_formula_assets_used_by_the_design(
    built_deck, tmp_path, monkeypatch
) -> None:
    builder, _, _ = built_deck
    missing_formula = tmp_path / "unused-formula.png"
    monkeypatch.setattr(builder.contract, "FORMULA_IMAGES", (missing_formula,))
    output = tmp_path / "v5-without-formulas.pptx"

    with pytest.raises(ValueError, match="missing v5 formula assets"):
        builder.build(output)


def test_v5_multi_event_annotations_follow_contract_relationships(
    built_deck, tmp_path, monkeypatch
) -> None:
    builder, _, _ = built_deck
    revised_rows = (
        {"method": "EPAL", "f1_s": 88.0, "f1_m": 75.0, "gap": 13.0},
        {"method": "SARGE", "f1_s": 90.0, "f1_m": 82.0, "gap": 8.0},
    )
    revised_data = {**builder.contract.V5_MULTI_EVENT_DATA, "rows": revised_rows}
    monkeypatch.setattr(builder.contract, "V5_MULTI_EVENT_DATA", revised_data)
    output = tmp_path / "v5-revised-multi-event.pptx"

    builder.build(output)
    text = _all_text(Presentation(output).slides[0])
    rows = {row["method"]: row for row in revised_rows}
    f1_m_gain = rows["SARGE"]["f1_m"] - rows["EPAL"]["f1_m"]
    gap_reduction = rows["EPAL"]["gap"] - rows["SARGE"]["gap"]
    assert f"+{f1_m_gain:.1f} F1(M.)" in text
    assert f"{gap_reduction:.1f}-point smaller S–M gap" in text
    assert (
        f"EPAL gap {rows['EPAL']['gap']:.1f} · SARGE gap {rows['SARGE']['gap']:.1f}"
        in text
    )


def test_v5_qr_picture_has_semantic_alt_description(built_deck) -> None:
    _, prs, _ = built_deck
    qr = _find(prs.slides[0], "FTR_QR_IMAGE")
    description = qr._element.nvPicPr.cNvPr.get("descr", "")

    assert "QR code" in description
    assert contract.DISPLAY_URL in description


def test_all_new_v5_shapes_are_inside_the_official_canvas(built_deck) -> None:
    _, prs, _ = built_deck

    for shape in validator.recursive_shapes(prs.slides[0].shapes):
        if not shape.name.startswith("V5_"):
            continue
        assert shape.left >= 0 and shape.top >= 0, shape.name
        assert shape.left + shape.width <= prs.slide_width + 1000, shape.name
        assert shape.top + shape.height <= prs.slide_height + 1000, shape.name
