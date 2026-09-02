# SARGE CCKS 2026 English Poster v4 Revision Report

## Outcome

The English CCKS 2026 poster was revised from the editable v3 source and
delivered as a new v4 PPTX, PDF, and high-resolution PNG. The v3 PPTX was not
overwritten; its SHA-256 remains
`80b3641ddcff8e98c85c005a299e931868be62ab5b8ce0df7b52bd45bd4a1646`.
No online material or result outside `SARGE_CCKS2026.pdf` was introduced.

Outputs:

- `SARGE_CCKS2026_poster_en_award_v4.pptx`
- `SARGE_CCKS2026_poster_en_award_v4.pdf`
- `SARGE_CCKS2026_poster_en_award_v4.png`
- `poster_revision_report.md`

## Page size and template compliance

| File | Pages/slides | Width | Height |
|---|---:|---:|---:|
| CCKS reference template | 1 | 88.90 cm | 109.22 cm |
| v3 source PPTX | 1 | 88.90 cm | 109.22 cm |
| v4 PPTX | 1 | 88.90 cm | 109.22 cm |
| v4 PDF | 1 | 2520 pt | 3096 pt |
| v4 PNG | 1 | 5250 px | 6451 px |

The canvas therefore matches the conference template. The original conference
background, CCKS mark, header/footer artwork, conference name, Xi'an location,
and 8.21--8.23 date are preserved. The unchanged background SHA-256 is
`75c64d300ba3826ee6da34bb658e081c35ce01724ed1570e9564ebd0f185ded7`.
Body content remains inside the established approximately 2.8 cm side margins.

## Scientific-body word count

Counting English words in `TAKEHOME_TEXT` and all `AW_*` scientific objects,
while excluding the paper title, authors, affiliations, conference name, URL,
email, fixed footer text, and decorative labels:

| Version | Words | Change from v3 |
|---|---:|---:|
| v3 | 462 | -- |
| v4 | 488 | +26 / **+5.6%** |

The increase comes from paper-backed dataset, model, inference-path, and
diagnostic qualifications rather than repeated conclusions.

## Main content corrections

- Replaced `ONE GENERATION OBJECT` with `ONE PREDICTION OBJECT`.
- Changed the problem label to `TWO SAME-TYPE EQUITY-PLEDGE RECORDS` and kept
  the red wrong-row versus teal correct-row example.
- Identified the tuned model as `Qwen3-4B + LoRA SFT`, with 4-bit NF4,
  answer-only loss, two epochs, greedy decoding, and a single RTX 4090 noted in
  the method area.
- Corrected the dataset summary to `43,940 TOTAL DOCUMENTS` and added
  `ChFinAnn 32,040` and `DuEE-Fin 11,900`.
- Labeled the headline results as three-seed means and displayed all four
  paper-reported values: ChFinAnn F1 `85.6 +/- 0.4`, DuEE-Fin F1
  `78.3 +/- 0.4`, ChFinAnn F1(M.) `81.7 +/- 0.1`, and DuEE-Fin F1(M.)
  `77.6 +/- 0.2` (the poster uses the proper `+/-` symbol).
- Kept the baseline conclusion restrained: ChFinAnn is numerically above the
  listed baselines; DuEE-Fin trails SEELE (80.8) but exceeds EPAL and ProCNet.
- Replaced the mixed-path ChFinAnn no-SFT comparison with the same-backend
  diagnostic `24.8 -> 85.5` (vLLM-BF16, seed 13). DuEE-Fin remains
  `3.3 -> 78.0` under HF-4bit, with `No SFT -> SFT` and seed scope explicit.
- Changed schema wording to `100% post-validation schema conformance` and added
  the paper's seed-13 scope.
- Kept `Delta_record = F1 - ExactRec` prominent and stated that F1 rewards
  matched role--value pairs whereas ExactRec requires an entire event row to
  match exactly.
- Added the exact qualification: `Delta_record is a diagnostic gap, not a pure
  binding-error estimate`, followed by the missing/extra/wrong-value and
  event-count explanation.
- Reframed the boundary as `REMAINING CHALLENGE -- EXACT SAME-TYPE ROW BINDING`:
  schema validity does not imply exact record assembly, and shared evidence can
  still assign private values to imperfect rows.

## Main layout adjustments

- Preserved the Header -> Take-home -> Problem -> Five-step Method -> Three
  evidence cards -> ExactRec/Significance -> Footer reading path.
- Kept the three evidence columns equal in width and height, aligned all six
  principal metric baselines, and standardized the principal numbers at 44 pt.
- Used the middle evidence card for both datasets' F1(M.) values, while keeping
  the ChFinAnn S--M gap comparison in a compact strip.
- Increased effective density through the dataset ribbon and implementation
  line rather than smaller prose; no new abstract, references, or conclusion
  block was added.
- Preserved the continuous five-step method route and arrows. Model and schema
  checking qualifications now sit inside their respective stages.
- Preserved and emphasized the purple ExactRec dumbbells and Delta_record
  badges. The left diagnostic and right significance/challenge areas retain
  matched height and visual weight, with no empty lower-right hole.
- Removed sub-millimetre text-frame boundary intersections around evidence
  labels, contribution captions, the challenge heading, and the corresponding
  author marker without changing the visible hierarchy.

## Editability, typography, and object QA

- v4 remains one editable PowerPoint slide with **179 named objects**.
- It contains four small pictures: the QR code and three formula images. There
  is no full-page raster, PDF-page background, or flattened poster screenshot.
- Minimum scientific explanatory text: **20 pt** for compact method notes.
  Ordinary body/captions are at least 22 pt; diagram/body text is commonly
  23--24 pt; main metrics are 44 pt; the paper title is 60 pt.
- Minimum text anywhere on the poster: **18 pt**, limited to affiliations,
  fixed footer details, and the compact take-home label.
- No research text uses shrink-to-fit. Structural checks found zero
  out-of-bounds objects and zero text-box intersections; full-poster and local
  crop review found no visible overflow, clipping, or unintended overlap.
- MarkItDown extraction found all required content and no leftover template
  placeholders.

## Export and review loop

Actual tools used:

- editing: `python-pptx` under
  `/home/tjk/.codex/venvs/codex-tools/bin/python`;
- PDF export: LibreOffice 7.3 headless through the PPTX skill's `soffice.py`
  wrapper;
- PNG export: Poppler `pdftoppm` at 150 dpi;
- visual crops: Pillow;
- PDF/PPTX checks: `pypdf`, `python-pptx`, MarkItDown, and `pdffonts`;
- rendered QR decoding: `zxing-cpp`.

The required loop was completed multiple times: edit -> export -> full/crop
inspection -> fix -> re-export -> re-inspect. The final PDF contains five
embedded, subsetted fonts. The PPTX and PDF page sizes match exactly.

## QR and final validation

- The QR bitmap is byte-identical to v3.
- The picture hyperlink remains `https://github.com/emmmdty/SARGE`.
- A crop taken from the final rendered PNG decoded successfully to
  `https://github.com/emmmdty/SARGE`.
- Final checks: one slide/page, valid OOXML ZIP, 179 objects, no full-page
  raster, no out-of-bounds objects, no text-frame overlap, no shrink-to-fit,
  required claims present, forbidden overclaims absent, PDF 2520 x 3096 pt,
  PNG 5250 x 6451 px.

## Remaining manual-check risk

No blocking digital issue remains. Before physical printing, check the v4 PPTX
once in the exact Microsoft PowerPoint version used by the print workflow,
because PowerPoint and LibreOffice can differ slightly in font metrics. Also
confirm the print vendor's bleed/PDF standard and scan the QR from a paper proof
at the intended viewing distance.
