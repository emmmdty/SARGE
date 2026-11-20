# CCKS 2026 poster

Final poster deliverables derived from the accepted CCKS 2026 paper.

## Deliverables

- `SARGE_CCKS2026_poster_en.pptx` and `.pdf`
- `SARGE_CCKS2026_poster_zh.pptx` and `.pdf`
- `final_v6/SARGE_CCKS2026_poster_en_award_v6.pptx`, `.pdf`, and `.png`
- `assets/` and `template/`: retained build inputs, including
  `assets/build_inputs/` source decks and figure PPTX files
- `tools/`: QR generation, PPTX build, and structural validation

Only these canonical files are final. Intermediate versions and analysis
drafts are intentionally not kept here.

## Requirements

Python 3.10+, `python-pptx`, `Pillow`, `pypdf`, `qrcode[pil]`,
`zxing-cpp`, LibreOffice, and Poppler. The poster build is local and CPU-only.

## Rebuild

From the repository root, regenerate the QR asset when its target changes:

```bash
python paper/ccks_2026/poster/tools/generate_qr.py
```

Build the standard English and Chinese posters:

```bash
python paper/ccks_2026/poster/tools/build_sarge_poster.py
```

Export both PPTX files to PDF with headless LibreOffice. The posters use an
88.90 x 109.22 cm portrait canvas.

Validate the source metrics, QR asset, PPTX canvas and bounds, required text,
and PDF page size:

```bash
python paper/ccks_2026/poster/tools/validate_poster.py
```

## Publication poster v6

V6 is rebuilt from the accepted paper, the official CCKS template, and editable
poster metadata. Its final directory contains only the matching editable PPTX,
PDF, and 150 dpi PNG:

`final_v6/SARGE_CCKS2026_poster_en_award_v6.pptx`

Build the PowerPoint from the repository root:

```bash
python paper/ccks_2026/poster/tools/build_sarge_poster_v6.py
```

Export with LibreOffice and Poppler:

```bash
soffice --headless --convert-to pdf \
  --outdir paper/ccks_2026/poster/final_v6 \
  paper/ccks_2026/poster/final_v6/SARGE_CCKS2026_poster_en_award_v6.pptx

pdftoppm -png -r 150 -singlefile \
  paper/ccks_2026/poster/final_v6/SARGE_CCKS2026_poster_en_award_v6.pdf \
  paper/ccks_2026/poster/final_v6/SARGE_CCKS2026_poster_en_award_v6
```

Validate the editable structure, scientific copy, charts, page size, embedded
fonts, output directory, and rendered QR code:

```bash
python paper/ccks_2026/poster/tools/validate_sarge_poster_v6.py --all
```
