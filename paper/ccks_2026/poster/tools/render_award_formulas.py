from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path


FORMULA_DIR = Path(__file__).resolve().parents[1] / "assets/formulas"


def run(command: list[str], *, cwd: Path) -> None:
    subprocess.run(command, cwd=cwd, check=True, capture_output=True, text=True)


def render(source: Path) -> Path:
    output = source.with_suffix(".png")
    with tempfile.TemporaryDirectory(prefix="sarge-formula-") as temp_dir:
        temp = Path(temp_dir)
        run(
            [
                "latex",
                "-interaction=nonstopmode",
                "-halt-on-error",
                f"-output-directory={temp}",
                str(source),
            ],
            cwd=FORMULA_DIR,
        )
        dvi = temp / f"{source.stem}.dvi"
        svg = temp / f"{source.stem}.svg"
        run(
            ["dvisvgm", "--no-fonts", "--exact", f"--output={svg}", str(dvi)],
            cwd=temp,
        )
        run(
            [
                "rsvg-convert",
                "--dpi-x",
                "600",
                "--dpi-y",
                "600",
                "--keep-aspect-ratio",
                "--output",
                str(output),
                str(svg),
            ],
            cwd=temp,
        )
    return output


def main() -> None:
    sources = sorted(FORMULA_DIR.glob("*.tex"))
    if not sources:
        raise SystemExit(f"no formula sources found in {FORMULA_DIR}")
    for source in sources:
        print(f"rendered: {render(source)}")


if __name__ == "__main__":
    main()
