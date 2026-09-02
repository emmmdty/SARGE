# CCKS 2026 poster

This local branch contains the final poster deliverables derived from the
public `main` branch. Both language variants point to:

`https://github.com/emmmdty/SARGE`

## Deliverables

- `SARGE_CCKS2026_poster_en.pptx` and `.pdf`
- `SARGE_CCKS2026_poster_zh.pptx` and `.pdf`
- `previews/`: rendered PNGs for visual inspection
- `tools/`: QR generation, PPTX build, and structural validation
- `template/` and `assets/`: source template and retained visual assets

Only the canonical filenames above are final. No `_revised`, draft, cache, or
LibreOffice profile files belong on this branch.

## Environments and paths

- Local project root: `/home/tjk/myProjects/masterProjects/DEE/SARGE/`
- Shared media Python: `/home/tjk/.codex/venvs/codex-tools/bin/python`
- Local project Python: `/home/tjk/miniconda3/envs/feg-dev-py310/bin/python`
- Server project root: `/data/TJK/DEE/SARGE/`
- Server Python: `/data/TJK/envs/sarge_vllm_full/bin/python`

The poster build is local and CPU-only.

## Rebuild

From the repository root, regenerate the QR asset when its target changes:

```bash
UV_CACHE_DIR=/tmp/sarge-poster-uv-cache \
uv run --no-project \
  --python /home/tjk/.codex/venvs/codex-tools/bin/python \
  --with 'qrcode[pil]' \
  python paper/ccks_2026/poster/tools/generate_qr.py
```

Build both PPTX files:

```bash
/home/tjk/.codex/venvs/codex-tools/bin/python \
  paper/ccks_2026/poster/tools/build_sarge_poster.py
```

Export both PPTX files to PDF with headless LibreOffice, then render the first
PDF page to the corresponding file under `previews/`. The current PDFs use an
88.90 × 109.22 cm portrait canvas.

Validate the source metrics, QR asset, PPTX canvas and bounds, required text,
and PDF page size:

```bash
/home/tjk/.codex/venvs/codex-tools/bin/python \
  paper/ccks_2026/poster/tools/validate_poster.py
```

## Publication poster v6

V6 is rebuilt from the accepted paper, official CCKS template, and editable v5
metadata. Its final directory contains only the matching editable PPTX, PDF,
and 150 dpi PNG:

`final_v6/SARGE_CCKS2026_poster_en_award_v6.pptx`

Build the PowerPoint from the repository root:

```bash
/home/tjk/.codex/venvs/codex-tools/bin/python \
  paper/ccks_2026/poster/tools/build_sarge_poster_v6.py
```

Export with LibreOffice and Poppler:

```bash
/home/tjk/.codex/venvs/codex-tools/bin/python \
  /home/tjk/.claude/skills/pptx/scripts/office/soffice.py \
  --headless --convert-to pdf \
  --outdir paper/ccks_2026/poster/final_v6 \
  paper/ccks_2026/poster/final_v6/SARGE_CCKS2026_poster_en_award_v6.pptx

pdftoppm -png -r 150 -singlefile \
  paper/ccks_2026/poster/final_v6/SARGE_CCKS2026_poster_en_award_v6.pdf \
  paper/ccks_2026/poster/final_v6/SARGE_CCKS2026_poster_en_award_v6
```

Validate the editable structure, scientific copy, charts, page size, embedded
fonts, output directory, and rendered QR code:

```bash
/home/tjk/.codex/venvs/codex-tools/bin/python \
  paper/ccks_2026/poster/tools/validate_sarge_poster_v6.py --all
```
