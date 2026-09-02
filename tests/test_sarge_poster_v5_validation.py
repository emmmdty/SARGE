from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

import pytest
from PIL import Image
from pptx import Presentation
from pptx.enum.shapes import MSO_AUTO_SHAPE_TYPE
from pptx.util import Inches, Pt

ROOT = Path(__file__).resolve().parents[1]
TOOLS_DIR = ROOT / "paper/ccks_2026/poster/tools"
VALIDATOR_PATH = TOOLS_DIR / "validate_sarge_poster_v5.py"
REPORT_PATH = ROOT / "paper/ccks_2026/poster/poster_award_v5_analysis.md"
SHARED_PYTHON = Path("/home/tjk/.codex/venvs/codex-tools/bin/python")


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


contract = _load_module(
    "award_poster_contract_v5_validation_test",
    TOOLS_DIR / "award_poster_contract.py",
)


@pytest.fixture(scope="module")
def validator():
    assert VALIDATOR_PATH.is_file(), "v5 validator module has not been implemented"
    sys.path.insert(0, str(TOOLS_DIR))
    return _load_module("validate_sarge_poster_v5_test", VALIDATOR_PATH)


@pytest.fixture(scope="module")
def rendered_artifacts(tmp_path_factory):
    output_dir = tmp_path_factory.mktemp("v5-rendered-validation")
    pptx_path = output_dir / contract.V5_PPTX.name
    pdf_path = output_dir / contract.V5_PDF.name
    png_path = output_dir / contract.V5_PNG.name
    pptx_path.write_bytes(contract.V5_PPTX.read_bytes())

    wrapper = Path("/home/tjk/.claude/skills/pptx/scripts/office/soffice.py")
    subprocess.run(
        [
            str(SHARED_PYTHON),
            str(wrapper),
            "--headless",
            "--convert-to",
            "pdf",
            "--outdir",
            str(output_dir),
            str(pptx_path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    subprocess.run(
        [
            "pdftoppm",
            "-png",
            "-r",
            "150",
            "-singlefile",
            str(pdf_path),
            str(png_path.with_suffix("")),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    assert pdf_path.is_file() and png_path.is_file()
    return pptx_path, pdf_path, png_path


def test_v5_validator_module_exists() -> None:
    assert VALIDATOR_PATH.is_file(), "v5 validator module has not been implemented"


def test_pptx_validation_covers_full_editable_visual_contract(validator) -> None:
    results = validator.validate_pptx(contract.V5_PPTX)
    names = {result.name for result in results}

    assert {
        "pptx_canvas",
        "pptx_template",
        "pptx_typography",
        "pptx_narrative",
        "pptx_claims",
        "pptx_charts",
        "pptx_visual_style",
        "pptx_qr",
    } <= names
    assert all(result.passed for result in results)


def test_validator_verifies_the_three_formula_assets(validator) -> None:
    slide = Presentation(contract.V5_PPTX).slides[0]
    for name in validator.FORMULA_PICTURE_NAMES:
        picture = validator.find_shape(slide, name)
        assert "LaTeX formula" in picture._element.nvPicPr.cNvPr.get("descr", "")
    assert all(result.passed for result in validator.validate_pptx(contract.V5_PPTX))


def test_pptx_validation_rejects_swapped_formula_assets(
    validator, tmp_path: Path
) -> None:
    broken_path = tmp_path / "swapped-formulas.pptx"
    with ZipFile(contract.V5_PPTX) as archive:
        members = {name: archive.read(name) for name in archive.namelist()}
    media_names = {
        blob: name for name, blob in members.items() if name.startswith("ppt/media/")
    }
    input_media = media_names[contract.METHOD_INPUT_FORMULA.read_bytes()]
    delta_media = media_names[contract.DELTA_RECORD_FORMULA.read_bytes()]
    members[input_media], members[delta_media] = (
        members[delta_media],
        members[input_media],
    )
    with ZipFile(broken_path, "w", compression=ZIP_DEFLATED) as archive:
        for name, blob in members.items():
            archive.writestr(name, blob)

    with pytest.raises(AssertionError, match="formula asset mismatch"):
        validator.validate_pptx(broken_path)


def test_pptx_validation_rejects_missing_required_claim(
    validator, tmp_path: Path
) -> None:
    broken_path = tmp_path / "missing-takehome.pptx"
    prs = Presentation(contract.V5_PPTX)
    shape = validator.find_shape(prs.slides[0], "V5_TAKEHOME_TEXT")
    first_run = shape.text_frame.paragraphs[0].runs[0]
    first_run.text = first_run.text.replace("Correct values", "Recovered values")
    prs.save(broken_path)

    with pytest.raises(AssertionError, match="required v5 token missing"):
        validator.validate_pptx(broken_path)


def test_pptx_validation_rejects_out_of_bounds_object(
    validator, tmp_path: Path
) -> None:
    broken_path = tmp_path / "out-of-bounds.pptx"
    prs = Presentation(contract.V5_PPTX)
    shape = validator.find_shape(prs.slides[0], "V5_CONCLUSION_BAND")
    shape.left = prs.slide_width
    prs.save(broken_path)

    with pytest.raises(AssertionError, match="right bound"):
        validator.validate_pptx(broken_path)


def test_pptx_validation_rejects_corrupted_multi_event_geometry_and_gap_labels(
    validator, tmp_path: Path
) -> None:
    broken_bar_path = tmp_path / "wrong-multi-height.pptx"
    prs = Presentation(contract.V5_PPTX)
    bar = validator.find_shape(
        prs.slides[0], "V5_RESULTS_B_CHART_BAR_SARGE_F1_M"
    )
    bar.height = bar.height // 2
    prs.save(broken_bar_path)
    with pytest.raises(AssertionError, match="multi-event bar"):
        validator.validate_pptx(broken_bar_path)

    broken_gap_path = tmp_path / "swapped-gap-labels.pptx"
    prs = Presentation(contract.V5_PPTX)
    gap_label = validator.find_shape(prs.slides[0], "V5_RESULTS_B_CHART_GAPS")
    gap_label.text_frame.paragraphs[0].runs[0].text = (
        "SARGE gap 13.1 · EPAL gap 7.5"
    )
    prs.save(broken_gap_path)
    with pytest.raises(AssertionError, match="gap label"):
        validator.validate_pptx(broken_gap_path)


def test_pptx_validation_rejects_corrupted_overall_error_bar(
    validator, tmp_path: Path
) -> None:
    broken_path = tmp_path / "wrong-error-bar.pptx"
    prs = Presentation(contract.V5_PPTX)
    error_bar = validator.find_shape(
        prs.slides[0], "V5_RESULTS_A_CHFINANN_CHART_ERROR_BAR"
    )
    error_bar.width = 1000
    prs.save(broken_path)

    with pytest.raises(AssertionError, match="error bar"):
        validator.validate_pptx(broken_path)


def test_pptx_validation_rejects_any_nonempty_run_without_explicit_size(
    validator, tmp_path: Path
) -> None:
    broken_path = tmp_path / "implicit-run-size.pptx"
    prs = Presentation(contract.V5_PPTX)
    shape = validator.find_shape(prs.slides[0], "V5_TAKEHOME_TEXT")
    run = shape.text_frame.paragraphs[0].add_run()
    run.text = " extra"
    run.font.name = contract.POSTER_FONT
    run.font.size = None
    prs.save(broken_path)

    with pytest.raises(AssertionError, match="explicit font size missing"):
        validator.validate_pptx(broken_path)


def test_pptx_validation_rejects_renamed_tiny_body_text(
    validator, tmp_path: Path
) -> None:
    broken_path = tmp_path / "renamed-tiny-body.pptx"
    prs = Presentation(contract.V5_PPTX)
    shape = validator.find_shape(prs.slides[0], "V5_MOTIVATION_REASONS")
    shape.name = "CUSTOM_BODY_TEXT"
    for paragraph in shape.text_frame.paragraphs:
        for run in paragraph.runs:
            if run.text:
                run.font.size = Pt(4)
    prs.save(broken_path)

    with pytest.raises(AssertionError, match="CUSTOM_BODY_TEXT"):
        validator.validate_pptx(broken_path)


def test_pptx_validation_rejects_non_template_decorative_shape(
    validator, tmp_path: Path
) -> None:
    broken_path = tmp_path / "decorative-rounded-card.pptx"
    prs = Presentation(contract.V5_PPTX)
    shape = prs.slides[0].shapes.add_shape(
        MSO_AUTO_SHAPE_TYPE.ROUNDED_RECTANGLE,
        100000,
        100000,
        1000000,
        500000,
    )
    shape.name = "V5_DECORATIVE_ROUNDED_CARD"
    prs.save(broken_path)

    with pytest.raises(AssertionError, match="unapproved rounded body shape"):
        validator.validate_pptx(broken_path)


@pytest.mark.parametrize("shape_name", ["HDR_TITLE", "HDR_AFFILIATIONS"])
def test_pptx_validation_rejects_non_arial_editable_header(
    validator, tmp_path: Path, shape_name: str
) -> None:
    broken_path = tmp_path / f"non-arial-{shape_name}.pptx"
    prs = Presentation(contract.V5_PPTX)
    shape = validator.find_shape(prs.slides[0], shape_name)
    for paragraph in shape.text_frame.paragraphs:
        for run in paragraph.runs:
            if run.text:
                run.font.name = "Comic Sans MS"
    prs.save(broken_path)

    with pytest.raises(AssertionError, match="header font must be Arial"):
        validator.validate_pptx(broken_path)


def test_pptx_validation_requires_definitions_at_first_use(validator) -> None:
    slide = Presentation(contract.V5_PPTX).slides[0]
    takehome = validator.find_shape(slide, "V5_TAKEHOME_TEXT")
    contribution = validator.find_shape(slide, "V5_MOTIVATION_CONTRIBUTION_3")
    inputs = validator.find_shape(slide, "V5_METHOD_STAGE_1_TEXT")
    output_title = validator.find_shape(slide, "V5_METHOD_STAGE_5_TITLE")
    legend = validator.find_shape(slide, "V5_RESULTS_B_CHART_LEGEND")
    input_formula = validator.find_shape(slide, "V5_METHOD_STAGE_1_INPUT_FORMULA")
    cues_formula = validator.find_shape(slide, "V5_METHOD_STAGE_1_CUES_FORMULA")
    cues_qualifier = validator.find_shape(slide, "V5_METHOD_STAGE_1_QUALIFIER")
    delta_formula = validator.find_shape(slide, "V5_RESULTS_C_DELTA_FORMULA")

    assert "ExactRec (strict event-row match)" in takehome.text
    assert "Δrecord (= F1 − ExactRec)" in contribution.text
    assert "document" in inputs.text and "closed schema" in inputs.text
    assert "document D plus closed schema S" in input_formula._element.nvPicPr.cNvPr.get(
        "descr", ""
    )
    assert "surface candidates C_K(D) and slot prior P_D" in (
        cues_formula._element.nvPicPr.cNvPr.get("descr", "")
    )
    assert cues_qualifier.text == "C_K(D): candidates  ·  P_D: role-slot prior"
    assert "Delta_record equals F1 minus ExactRec" in (
        delta_formula._element.nvPicPr.cNvPr.get("descr", "")
    )
    assert output_title.text == "Fixed-slot table"
    assert legend.text == "F1(S.): single/light · F1(M.): multi/dark"


def test_pptx_validation_rejects_diagonal_error_bar_or_horizontal_cap(
    validator, tmp_path: Path
) -> None:
    diagonal_path = tmp_path / "diagonal-error-bar.pptx"
    prs = Presentation(contract.V5_PPTX)
    line = validator.find_shape(
        prs.slides[0], "V5_RESULTS_A_CHFINANN_CHART_ERROR_BAR"
    )
    line.height = Inches(1)
    prs.save(diagonal_path)
    with pytest.raises(AssertionError, match="horizontal"):
        validator.validate_pptx(diagonal_path)

    horizontal_cap_path = tmp_path / "horizontal-error-cap.pptx"
    prs = Presentation(contract.V5_PPTX)
    cap = validator.find_shape(
        prs.slides[0], "V5_RESULTS_A_CHFINANN_CHART_ERROR_CAP_LEFT"
    )
    cap.width = Inches(1)
    prs.save(horizontal_cap_path)
    with pytest.raises(AssertionError, match="vertical"):
        validator.validate_pptx(horizontal_cap_path)


def test_pdf_validation_checks_page_text_header_glyph_and_embedded_fonts(
    validator, rendered_artifacts
) -> None:
    _, pdf_path, _ = rendered_artifacts
    results = validator.validate_pdf(pdf_path)

    assert {result.name for result in results} == {"pdf"}
    assert results[0].passed
    assert "2520x3096 pt" in results[0].detail
    assert "fonts embedded" in results[0].detail


def test_png_validation_checks_150dpi_size_and_decodable_qr(
    validator, rendered_artifacts
) -> None:
    pptx_path, _, png_path = rendered_artifacts
    results = validator.validate_png_and_qr(png_path, pptx_path)

    assert {result.name for result in results} == {"png"}
    assert results[0].passed
    assert "5250x6451" in results[0].detail
    assert contract.REPOSITORY_URL in results[0].detail


def test_png_validation_rejects_wrong_dimensions(
    validator, rendered_artifacts, tmp_path: Path
) -> None:
    pptx_path, _, png_path = rendered_artifacts
    broken_path = tmp_path / "wrong-size.png"
    with Image.open(png_path) as image:
        image.resize((1200, 1200)).save(broken_path)

    with pytest.raises(AssertionError, match="150 dpi"):
        validator.validate_png_and_qr(broken_path, pptx_path)


def test_cli_pptx_only_emits_machine_readable_json(validator) -> None:
    completed = subprocess.run(
        [
            str(SHARED_PYTHON),
            str(VALIDATOR_PATH),
            "--pptx-only",
            "--pptx",
            str(contract.V5_PPTX),
            "--json",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(completed.stdout)

    assert payload["overall_pass"] is True
    assert payload["mode"] == "pptx-only"
    assert {row["name"] for row in payload["results"]} >= {
        "pptx_canvas",
        "pptx_charts",
        "pptx_qr",
    }


def test_cli_returns_nonzero_and_readable_failure_json(tmp_path: Path) -> None:
    missing_path = tmp_path / "missing.pptx"
    completed = subprocess.run(
        [
            str(SHARED_PYTHON),
            str(VALIDATOR_PATH),
            "--pptx-only",
            "--pptx",
            str(missing_path),
            "--json",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode != 0
    payload = json.loads(completed.stdout)
    assert payload["overall_pass"] is False
    assert "missing PPTX" in payload["error"]


def test_v5_analysis_report_covers_decisions_provenance_qa_and_risks() -> None:
    assert REPORT_PATH.is_file(), "v5 analysis report has not been implemented"
    report = REPORT_PATH.read_text(encoding="utf-8")

    for heading in (
        "## Reviewer diagnosis",
        "## V5 narrative and visual response",
        "## Metric provenance",
        "## Quality assurance",
        "## Remaining print and manual checks",
    ):
        assert heading in report
    for token in (
        "ChFinAnn",
        "DuEE-Fin",
        "85.6 ± 0.4",
        "78.3 ± 0.4",
        "ExactRec",
        "seed 13",
        "seeds 13/17/42",
        "Arial",
        "LaTeX",
        "formula",
        "QR",
    ):
        assert token in report
