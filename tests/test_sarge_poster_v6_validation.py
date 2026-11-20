from __future__ import annotations

import importlib.util
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
from PIL import Image
from pptx import Presentation
from pptx.util import Inches, Pt

ROOT = Path(__file__).resolve().parents[1]
POSTER_DIR = ROOT / "paper/ccks_2026/poster"
TOOLS_DIR = POSTER_DIR / "tools"
CONTRACT_PATH = TOOLS_DIR / "award_poster_contract.py"
BUILDER_PATH = TOOLS_DIR / "build_sarge_poster_v6.py"
VALIDATOR_PATH = TOOLS_DIR / "validate_sarge_poster_v6.py"
SOFFICE = shutil.which("soffice") or shutil.which("libreoffice")
PDFTOPPM = shutil.which("pdftoppm")


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
    return _load_module("award_poster_contract_v6_validation", CONTRACT_PATH)


@pytest.fixture(scope="module")
def builder():
    return _load_module("build_sarge_poster_v6_validation", BUILDER_PATH)


@pytest.fixture(scope="module")
def validator():
    return _load_module("validate_sarge_poster_v6_test", VALIDATOR_PATH)


@pytest.fixture(scope="module")
def built_pptx(tmp_path_factory, builder, contract):
    output = tmp_path_factory.mktemp("poster-v6-validation") / contract.V6_PPTX.name
    builder.build(output)
    return output


@pytest.fixture(scope="module")
def rendered_artifacts(tmp_path_factory, built_pptx, contract):
    if SOFFICE is None or PDFTOPPM is None:
        pytest.skip("LibreOffice and pdftoppm are required for render validation")
    output_dir = tmp_path_factory.mktemp("poster-v6-render")
    pptx_path = output_dir / contract.V6_PPTX.name
    pptx_path.write_bytes(built_pptx.read_bytes())
    subprocess.run(
        [
            SOFFICE,
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
    pdf_path = output_dir / contract.V6_PDF.name
    png_path = output_dir / contract.V6_PNG.name
    subprocess.run(
        [
            PDFTOPPM,
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
    return pptx_path, pdf_path, png_path


def test_v6_validator_module_exists() -> None:
    assert VALIDATOR_PATH.is_file()


def test_v6_pptx_validation_covers_required_contract(validator, built_pptx) -> None:
    results = validator.validate_pptx(built_pptx)
    assert {result.name for result in results} == {
        "pptx_canvas",
        "pptx_template",
        "pptx_typography",
        "pptx_content",
        "pptx_layout",
        "pptx_results",
        "pptx_editability",
        "pptx_qr",
    }


def test_v6_validator_rejects_forbidden_claim(tmp_path, validator, built_pptx) -> None:
    broken = tmp_path / "forbidden.pptx"
    prs = Presentation(built_pptx)
    prs.slides[0].shapes.add_textbox(0, 0, 1000000, 1000000).text = "100% schema-valid"
    prs.save(broken)
    with pytest.raises(AssertionError, match="forbidden claim"):
        validator.validate_pptx(broken)


def test_v6_validator_rejects_out_of_bounds_object(tmp_path, validator, built_pptx) -> None:
    broken = tmp_path / "out-of-bounds.pptx"
    prs = Presentation(built_pptx)
    shape = prs.slides[0].shapes.add_textbox(prs.slide_width, 0, 1000000, 1000000)
    shape.name = "V6_BROKEN_OUT_OF_BOUNDS"
    shape.text = "broken"
    prs.save(broken)
    with pytest.raises(AssertionError, match="outside slide"):
        validator.validate_pptx(broken)


def test_v6_validator_rejects_body_content_in_template_header(
    tmp_path, validator, built_pptx
) -> None:
    broken = tmp_path / "body-in-header.pptx"
    prs = Presentation(built_pptx)
    shape = next(
        shape for shape in prs.slides[0].shapes if shape.name == "V6_TAKEHOME_TEXT"
    )
    shape.top = Inches(7.40)
    prs.save(broken)
    with pytest.raises(AssertionError, match="white body region"):
        validator.validate_pptx(broken)


def test_v6_validator_rejects_fractional_point_size(
    tmp_path, validator, built_pptx
) -> None:
    broken = tmp_path / "fractional-font.pptx"
    prs = Presentation(built_pptx)
    shape = next(
        shape for shape in prs.slides[0].shapes if shape.name == "V6_RESULTS_B_GAIN"
    )
    shape.text_frame.paragraphs[0].runs[0].font.size = Pt(41.5)
    prs.save(broken)
    with pytest.raises(AssertionError, match="integer point size"):
        validator.validate_pptx(broken)


def test_v6_validator_rejects_corrupted_dumbbell_geometry(
    tmp_path, validator, built_pptx
) -> None:
    broken = tmp_path / "bad-dumbbell.pptx"
    prs = Presentation(built_pptx)
    marker = next(
        shape
        for shape in prs.slides[0].shapes
        if shape.name == "V6_RESULTS_B_SARGE_MULTI_MARKER"
    )
    marker.left += 300000
    prs.save(broken)
    with pytest.raises(AssertionError, match="dumbbell marker"):
        validator.validate_pptx(broken)


def test_v6_validator_requires_explicit_seventy_to_ninety_five_zoomed_axis(
    tmp_path, validator, built_pptx
) -> None:
    broken = tmp_path / "truncated-axis.pptx"
    prs = Presentation(built_pptx)
    tick = next(
        shape for shape in prs.slides[0].shapes if shape.name == "V6_RESULTS_B_TICK_70"
    )
    tick.text_frame.paragraphs[0].runs[0].text = "75"
    prs.save(broken)
    with pytest.raises(AssertionError, match="70–95 zoomed axis"):
        validator.validate_pptx(broken)


def test_v6_pdf_validation_checks_page_text_and_fonts(
    validator, rendered_artifacts
) -> None:
    _, pdf_path, _ = rendered_artifacts
    results = validator.validate_pdf(pdf_path)
    assert [result.name for result in results] == ["pdf"]
    assert "fonts embedded" in results[0].detail


def test_v6_png_validation_checks_resolution_and_rendered_qr(
    validator, rendered_artifacts
) -> None:
    pytest.importorskip("zxingcpp")
    pptx_path, _, png_path = rendered_artifacts
    results = validator.validate_png_and_qr(png_path, pptx_path)
    assert [result.name for result in results] == ["png"]
    assert "github.com/emmmdty/SARGE" in results[0].detail
    with Image.open(png_path) as image:
        assert image.width == pytest.approx(5250, abs=2)
        assert image.height == pytest.approx(6450, abs=2)


def test_v6_output_directory_must_contain_exactly_three_deliverables(
    tmp_path, validator, rendered_artifacts, contract
) -> None:
    output_dir = tmp_path / "final_v6"
    output_dir.mkdir()
    for source in rendered_artifacts:
        (output_dir / source.name).write_bytes(source.read_bytes())
    result = validator.validate_output_directory(output_dir)
    assert result.name == "output_directory"
    (output_dir / "debug.txt").write_text("unexpected")
    with pytest.raises(AssertionError, match="exactly the three"):
        validator.validate_output_directory(output_dir)


def test_v6_cli_emits_machine_readable_json(validator, built_pptx, capsys) -> None:
    status = validator.main(["--pptx-only", "--pptx", str(built_pptx), "--json"])
    payload = json.loads(capsys.readouterr().out)
    assert status == 0
    assert payload["overall_pass"] is True
    assert payload["mode"] == "pptx-only"
