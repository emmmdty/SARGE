# Poster Revision Report

Final status: revised poster generated and QA passed.

Environment and path record:

- Active local poster worktree: `/home/tjk/myProjects/masterProjects/DEE/.worktrees/SARGE-poster/` (`poster/ccks-2026`).
- Canonical local project root: `/home/tjk/myProjects/masterProjects/DEE/SARGE/`.
- Expected server project root: `/data/TJK/DEE/SARGE/`; corresponding poster directory: `/data/TJK/DEE/SARGE/paper/ccks_2026/poster/`.
- Media-processing Python: `/home/tjk/.codex/venvs/codex-tools/bin/python`.
- Project local Python: `/home/tjk/miniconda3/envs/feg-dev-py310/bin/python`; server Python: `/data/TJK/envs/sarge_vllm_full/bin/python`.

## 1. Input and output files

Inputs (all opened successfully):

- `SARGE_CCKS2026_poster_en.pptx` — editable source poster.
- `SARGE_CCKS2026_poster_en.pdf` — rendering baseline.
- `main_en_final(6).pdf` — copied without modification from the repository's canonical `paper/ccks_2026/main_en_final.pdf`; paper SHA-256 `6879fd6d4023a89b232f806d614465506862ceba88024224ced1341fa6380011`.
- `CCKS2026-poster参考模板(1).pptx` — copied without modification from `template/CCKS2026-poster参考模板.pptx`; template SHA-256 `bc9ed1f3d40348e7caf99362f1241ad562f2bb281acc3c5930a59d9351253273`.

Backup:

- `SARGE_CCKS2026_poster_en_backup.pptx` — SHA-256 `c439c687381048070f52eb03a7eded8c6088aba63208bc0d87353708d34a0176`; byte-identical to the source PPTX.

Outputs:

- `SARGE_CCKS2026_poster_en_revised.pptx` — 3,678,155 bytes.
- `SARGE_CCKS2026_poster_en_revised.pdf` — 1,611,946 bytes.
- `SARGE_CCKS2026_poster_en_revised.png` — 4,256,017 bytes.
- `poster_revision_report.md` — this report.

Original PPTX/PDF, paper PDF, and template PPTX were not overwritten.

## 2. Page specification

| Item | Width | Height | Orientation |
|---|---:|---:|---|
| Original poster PPTX | 88.90 cm | 109.22 cm | Portrait |
| Reference template PPTX | 88.90 cm | 109.22 cm | Portrait |
| Revised poster PPTX | 88.90 cm | 109.22 cm | Portrait |
| Revised PDF | 2520 pt (35 in) | 3096 pt (43 in) | Portrait |

The PNG is 5250 × 6451 px at 150 dpi; the one-pixel height difference from 6450 px is Poppler rounding for the exact 43-inch page.

## 3. Template comparison

- Background identity: PASS. Original poster, reference template, and revised poster all use the same 8268 × 10157 JPEG with SHA-256 `75c64d300ba3826ee6da34bb658e081c35ce01724ed1570e9564ebd0f185ded7`.
- Effective full-page background resolution: approximately 236.2 dpi horizontally and vertically.
- Slide layout/master: unchanged `Title Slide` layout (`/ppt/slideLayouts/slideLayout1.xml`) and `/ppt/slideMasters/slideMaster1.xml`.
- Top gradient, CCKS 2026 logo, buildings, school/city decoration: preserved in the unchanged background and not obscured. The title right edge is 56.0 cm, below the 56.5 cm limit.
- Bottom gradient and waves: preserved in the unchanged background.
- Conference text: preserved as the original native template shape. Wording, rotation, and geometry remain x=21.98 cm, y=99.66 cm, w=65.91 cm, h=6.41 cm; the original 48 pt template formatting remains. One internal line break balances the English name without changing its wording.
- Safe margins: body cards span x=2.8–86.1 cm. Specified same-row inter-card gaps are exactly 0.8 cm; all objects remain inside the page.

## 4. Shape inventory

The pre-edit audit was captured before modifying slide objects. The known “about 162” object count was approximate; the actual editable source contains 169 slide-level objects.

| Inventory | Original | Revised |
|---|---:|---:|
| Slide-level objects | 169 | 21 |
| Recursive objects (including group children) | 169 | 161 |
| Native text boxes | 87 | 91 |
| Native autoshapes | 68 | 50 |
| Lines/connectors | 13 | 12 |
| Pictures | 1 | 1 |
| Groups | 0 | 7 |

Revised picture inventory: one 370 × 370 px QR image placed at 5.0 × 5.0 cm inside a 5.5 × 5.5 cm native frame, effective resolution 188 dpi. The full-page background remains a slide background, not a picture shape.

Final top-level z-order:

| z | Shape ID | Name | Type | Geometry (x, y, w, h) |
|---:|---:|---|---|---|
| 1 | 25 | `FTR_CONFERENCE_TEXT` | TEXT_BOX (17) | (21.98, 99.66, 65.91, 6.41) cm |
| 2 | 26 | `HDR_TITLE` | TEXT_BOX (17) | (4.00, 2.80, 52.00, 7.50) cm |
| 3 | 27 | `HDR_AUTHORS` | TEXT_BOX (17) | (4.10, 10.60, 58.00, 1.60) cm |
| 4 | 28 | `HDR_CORRESPONDING_SYMBOL` | TEXT_BOX (17) | (34.95, 10.60, 1.25, 1.60) cm |
| 5 | 29 | `HDR_AFFILIATIONS` | TEXT_BOX (17) | (4.10, 12.30, 58.00, 1.60) cm |
| 6 | 30 | `TAKEHOME_FRAME` | AUTO_SHAPE (1) | (2.80, 18.80, 83.30, 4.80) cm |
| 7 | 31 | `TAKEHOME_LABEL_BOX` | AUTO_SHAPE (1) | (3.80, 19.50, 8.40, 1.30) cm |
| 8 | 32 | `TAKEHOME_LABEL` | TEXT_BOX (17) | (3.80, 19.50, 8.40, 1.30) cm |
| 9 | 33 | `TAKEHOME_TEXT` | TEXT_BOX (17) | (12.80, 19.10, 71.80, 3.60) cm |
| 10 | 54 | `S1_GROUP` | GROUP (6) | (2.80, 24.50, 26.00, 29.00) cm |
| 11 | 90 | `S2_GROUP` | GROUP (6) | (29.60, 24.50, 56.50, 29.00) cm |
| 12 | 105 | `S3_GROUP` | GROUP (6) | (2.80, 54.30, 26.00, 23.00) cm |
| 13 | 128 | `S4_GROUP` | GROUP (6) | (29.60, 54.30, 26.00, 23.00) cm |
| 14 | 145 | `S5_GROUP` | GROUP (6) | (56.40, 54.30, 29.70, 23.00) cm |
| 15 | 171 | `S6_GROUP` | GROUP (6) | (2.80, 78.10, 36.00, 17.90) cm |
| 16 | 180 | `S7_GROUP` | GROUP (6) | (39.60, 78.10, 46.50, 17.90) cm |
| 17 | 181 | `FTR_QR_FRAME` | AUTO_SHAPE (1) | (4.40, 99.70, 5.50, 5.50) cm |
| 18 | 182 | `FTR_QR_IMAGE` | PICTURE (13) | (4.65, 99.95, 5.00, 5.00) cm |
| 19 | 183 | `FTR_LABEL` | TEXT_BOX (17) | (10.40, 99.70, 10.80, 1.30) cm |
| 20 | 184 | `FTR_URL` | TEXT_BOX (17) | (10.40, 101.25, 10.80, 1.35) cm |
| 21 | 185 | `FTR_EMAIL` | TEXT_BOX (17) | (10.40, 102.75, 10.80, 1.35) cm |

All revised region object names:

<details><summary>HDR (4 objects)</summary>

`HDR_TITLE`, `HDR_AUTHORS`, `HDR_CORRESPONDING_SYMBOL`, `HDR_AFFILIATIONS`

</details>

<details><summary>TAKEHOME (4 objects)</summary>

`TAKEHOME_FRAME`, `TAKEHOME_LABEL_BOX`, `TAKEHOME_LABEL`, `TAKEHOME_TEXT`

</details>

<details><summary>S1 (21 objects)</summary>

`S1_GROUP`, `S1_CARD`, `S1_NUMBER`, `S1_TITLE`, `S1_DIVIDER`, `S1_RECORD_1_BOX`, `S1_RECORD_1_TEXT`, `S1_RECORD_2_BOX`, `S1_RECORD_2_TEXT`, `S1_SHARED_LABEL_BOX`, `S1_SHARED_LABEL`, `S1_PRIVATE_LABEL_BOX`, `S1_PRIVATE_LABEL`, `S1_CROSS_BOUND_CLAIM`, `S1_WRONG_HEADING`, `S1_CORRECT_HEADING`, `S1_WRONG_BOX`, `S1_CORRECT_BOX`, `S1_WRONG_ROWS`, `S1_CORRECT_ROWS`, `S1_CAPTION`

</details>

<details><summary>S2 (36 objects)</summary>

`S2_GROUP`, `S2_CARD`, `S2_NUMBER`, `S2_TITLE`, `S2_DIVIDER`, `S2_ACRONYM`, `S2_STEP1_BOX`, `S2_STEP1_STEP`, `S2_STEP1_TITLE`, `S2_STEP1_BODY`, `S2_STEP2_BOX`, `S2_STEP2_STEP`, `S2_STEP2_TITLE`, `S2_STEP2_BODY`, `S2_STEP3_BOX`, `S2_STEP3_STEP`, `S2_STEP3_TITLE`, `S2_STEP3_BODY`, `S2_STEP4_BOX`, `S2_STEP4_STEP`, `S2_STEP4_TITLE`, `S2_STEP4_BODY`, `S2_STEP5_BOX`, `S2_STEP5_STEP`, `S2_STEP5_TITLE`, `S2_STEP5_BODY`, `S2_STEP6_BOX`, `S2_STEP6_STEP`, `S2_STEP6_TITLE`, `S2_STEP6_BODY`, `S2_ARROW_1_TO_2`, `S2_ARROW_2_TO_3`, `S2_ARROW_3_TO_4`, `S2_ARROW_4_TO_5`, `S2_ARROW_5_TO_6`, `S2_CAPTION`

</details>

<details><summary>S3 (15 objects)</summary>

`S3_GROUP`, `S3_CARD`, `S3_NUMBER`, `S3_TITLE`, `S3_DIVIDER`, `S3_CHFINANN_BOX`, `S3_CHFINANN_VALUE`, `S3_CHFINANN_LABEL`, `S3_DUEEFIN_BOX`, `S3_DUEEFIN_VALUE`, `S3_DUEEFIN_LABEL`, `S3_COMPARE_CHFINANN`, `S3_COMPARE_DUEEFIN`, `S3_CONCLUSION`, `S3_FOOTNOTE`

</details>

<details><summary>S4 (23 objects)</summary>

`S4_GROUP`, `S4_CARD`, `S4_NUMBER`, `S4_TITLE`, `S4_DIVIDER`, `S4_TABLE_HEADER_BOX`, `S4_HEADER_METHOD`, `S4_HEADER_F1M`, `S4_HEADER_GAP`, `S4_EPAL_ROW`, `S4_EPAL_METHOD`, `S4_EPAL_F1M`, `S4_EPAL_S_M_GAP`, `S4_SARGE17B_ROW`, `S4_SARGE17B_METHOD`, `S4_SARGE17B_F1M`, `S4_SARGE17B_S_M_GAP`, `S4_SARGE4B_ROW`, `S4_SARGE4B_METHOD`, `S4_SARGE4B_F1M`, `S4_SARGE4B_S_M_GAP`, `S4_EXPLANATION`, `S4_FOOTNOTE`

</details>

<details><summary>S5 (17 objects)</summary>

`S5_GROUP`, `S5_CARD`, `S5_NUMBER`, `S5_TITLE`, `S5_DIVIDER`, `S5_SCOPE`, `S5_CHFINANN_BOX`, `S5_CHFINANN_LABEL`, `S5_CHFINANN_VALUE`, `S5_CHFINANN_PATH`, `S5_DUEEFIN_BOX`, `S5_DUEEFIN_LABEL`, `S5_DUEEFIN_VALUE`, `S5_DUEEFIN_PATH`, `S5_FINDING_1`, `S5_FINDING_2`, `S5_FOOTNOTE`

</details>

<details><summary>S6 (26 objects)</summary>

`S6_GROUP`, `S6_CARD`, `S6_NUMBER`, `S6_TITLE`, `S6_DIVIDER`, `S6_DATASET_1`, `S6_R1_C1_BOX`, `S6_R1_C1_LABEL`, `S6_R1_C1_VALUE`, `S6_R1_C2_BOX`, `S6_R1_C2_LABEL`, `S6_R1_C2_VALUE`, `S6_R1_C3_BOX`, `S6_R1_C3_LABEL`, `S6_R1_C3_VALUE`, `S6_DATASET_2`, `S6_R2_C1_BOX`, `S6_R2_C1_LABEL`, `S6_R2_C1_VALUE`, `S6_R2_C2_BOX`, `S6_R2_C2_LABEL`, `S6_R2_C2_VALUE`, `S6_R2_C3_BOX`, `S6_R2_C3_LABEL`, `S6_R2_C3_VALUE`, `S6_EXPLANATION`

</details>

<details><summary>S7 (9 objects)</summary>

`S7_GROUP`, `S7_CARD`, `S7_NUMBER`, `S7_TITLE`, `S7_DIVIDER`, `S7_CONTRIBUTIONS`, `S7_BOUNDARY_BOX`, `S7_BOUNDARY_TEXT`, `S7_SOURCE`

</details>

<details><summary>FTR (6 objects)</summary>

`FTR_CONFERENCE_TEXT`, `FTR_QR_FRAME`, `FTR_QR_IMAGE`, `FTR_LABEL`, `FTR_URL`, `FTR_EMAIL`

</details>

Sections 1–7 are individual native PowerPoint groups. The page was not flattened, and all research text remains editable.

## 5. Font inventory

- PPTX declared fonts used by slide content: `Arial`, `微软雅黑`.
- Minimum explicit PPTX font size: 16 pt. Ordinary body text is 18–20 pt; only source/seed/path notes and visual subscripts use 16 pt.
- All revised content text boxes use fixed dimensions with `noAutofit`; no `normAutofit`/shrink-on-overflow is present. The only retained `spAutoFit` belongs to the unchanged 48 pt conference text shape.
- Linux export substitution: Arial → Liberation Sans; 微软雅黑 → Noto Sans CJK SC; superscript/envelope glyph fallback → DejaVu Sans.
- Actual embedded PDF fonts: LiberationSans, LiberationSans-Bold, NotoSansCJKsc-Regular-VKana, DejaVuSans, and DejaVuSans-Bold.
- PDF embedding: PASS. `pdffonts` reports `emb=yes`, `sub=yes`, and `uni=yes` for every exported font.
- The correspondence symbol is a native Unicode `✉` text object. It was separated into `HDR_CORRESPONDING_SYMBOL` after mixed-run Linux export misplaced the glyph; the final render positions it immediately after Yue Zhao.

## 6. Revision log

Coordinates are `(x, y, w, h)` in cm. “Redrawn” means the research object was rebuilt as editable native text/shapes; it does not mean rasterized.

| Region | Original object/text | New object/text | Original coordinates | New coordinates | Original size | New size | Redrawn | Reason |
|---|---|---|---|---|---:|---:|---|---|
| Header title | TextBox 15 / unchanged title wording | HDR_TITLE / unchanged title wording | (3.94, 2.49, 52.58, 7.11) | (4.00, 2.80, 52.00, 7.50) | 50 pt | 54 pt | Yes | Match required header grid and prominence. |
| Authors | TextBox 21 | HDR_AUTHORS + HDR_CORRESPONDING_SYMBOL | (4.11, 10.01, 58.42, 1.57) | (4.10, 10.60, 58.00, 1.60) | 26 pt | 26 pt | Yes | Preserve order/superscripts and stabilize the Unicode envelope. |
| Affiliations | TextBox 25, one line | HDR_AFFILIATIONS, two lines | (4.11, 11.61, 58.42, 1.98) | (4.10, 12.30, 58.00, 1.60) | 17 pt | 18 pt | Yes | Meet specified hierarchy and separate affiliations. |
| Take-home | Old schema-contract robustness sentence | Required ChFinAnn/ExactRec sentence | Frame (2.79, 18.75, 83.31, 5.69) | Frame (2.80, 18.80, 83.30, 4.80) | 24 pt | 28 pt | Yes | Make the factual claim explicit and readable in two lines. |
| Section 1 | Why it is hard: correct roles, wrong rows | The challenge: correct values, wrong rows | (2.79, 25.45, 26.92, 29.34) | (2.80, 24.50, 26.00, 29.00) | 30 pt title | 32 pt title | Yes | Use specified challenge wording, row labels, symbols, and exact case text. |
| Section 2 | Render the schema as an event-table output contract | SARGE: schema-grounded event-table generation | (30.61, 25.45, 55.50, 29.34) | (29.60, 24.50, 56.50, 29.00) | 30 pt title | 32 pt title | Yes | Add full acronym and six-step snake flow with five arrows. |
| Section 3 | Three-seed main results with delta strips | Main results: three-seed means with direct comparisons | (2.79, 55.70, 26.04, 23.50) | (2.80, 54.30, 26.00, 23.00) | 30 pt title | 32 pt title | Yes | Remove duplicated delta decoration; state restrained comparisons and seed scope. |
| Section 4 | Unscaled horizontal track visualization | Three-row native numeric table | (29.59, 55.70, 26.04, 23.50) | (29.60, 54.30, 26.00, 23.00) | 30 pt title | 32 pt title | Yes | Make F1(M.) and S-M Gap explicit; distinguish seed 13 from mean. |
| Section 5 | The gain comes from schema alignment | Supervised alignment is the dominant factor | (56.39, 55.70, 29.72, 23.50) | (56.40, 54.30, 29.70, 23.00) | 30 pt title | 32 pt title | Yes | Replace badges with paper-supported alignment and inference-path statements. |
| Section 6 | Progress tracks plus separate Δrecord cards | Two-row, three-metric matrix | (2.79, 80.06, 33.15, 15.95) | (2.80, 78.10, 36.00, 17.90) | 30 pt title | 32 pt title | Yes | Avoid length encoding and retain the complete diagnostic limitation. |
| Section 7 | Three mini-cards plus 14 pt copy | Three continuous conclusions plus boundary box | (36.70, 80.06, 49.40, 15.95) | (39.60, 78.10, 46.50, 17.90) | 30 pt title | 32 pt title | Yes | Increase body readability and make the record-binding boundary explicit. |
| Footer QR | Existing 5.46 cm frame / 5.21 cm QR | FTR_QR_FRAME / FTR_QR_IMAGE | (4.37, 99.69, 5.46, 5.46) | (4.40, 99.70, 5.50, 5.50) | N/A | 188 dpi | Yes | Match footer specification and retain the supplied verified QR. |
| Footer links | Code & paper; 17 pt URL/email | Paper & code; 18 pt URL/email | (10.41, 99.62, 10.67, 4.40) | (10.40, 99.70, 10.80, 4.40) | 22/17 pt | 22/18 pt | Yes | Use requested wording and add native clickable hyperlinks. |
| Conference text | Template conference text | FTR_CONFERENCE_TEXT | (21.98, 99.66, 65.91, 6.41) | Unchanged | 48 pt | 48 pt | No; internal line break only | Protected wording, typography, and placement retained while balancing the English conference-name wrapping. |

## 7. Numerical verification

| Poster item | Verified value / wording | Scope | Paper source |
|---|---|---|---|
| ChFinAnn main F1 | 85.6 ± 0.4 | Mean ± std, seeds 13/17/42 | Table 1; §4.2 |
| DuEE-Fin main F1 | 78.3 ± 0.4 | Mean ± std, seeds 13/17/42 | Table 1; §4.2 |
| ChFinAnn ExactRec | 56.1 | Three-seed mean | Table 1 |
| DuEE-Fin ExactRec | 43.3 | Three-seed mean | Table 1 |
| ChFinAnn Δrecord | 29.5 | F1 − ExactRec, three-seed mean | Table 1; §3.6 |
| DuEE-Fin Δrecord | 35.1 | F1 − ExactRec, three-seed mean | Table 1; §3.6 |
| SEELE ChFinAnn F1 | 85.1 | Listed baseline | Table 1 |
| SEELE DuEE-Fin F1 | 80.8 | Listed baseline | Table 1 |
| ChFinAnn comparison | numerically above the listed baselines | Restrained aggregate-F1 claim | §4.2 |
| DuEE-Fin comparison | below SEELE, but above EPAL and ProCNet | Aggregate-F1 comparison | §4.2 |
| Doc2Event | Contextual only; different split and scorer | Not a strict comparable baseline | Table 1 note; §4.2 |
| EPAL F1(M.) | 76.6 | ChFinAnn | Table 4 |
| EPAL S-M Gap | 13.1 | ChFinAnn | Table 4 |
| SARGE 1.7B F1(M.) | 79.6 | ChFinAnn, seed 13 | Tables 3–4 |
| SARGE 1.7B S-M Gap | 8.2 | ChFinAnn, seed 13 | Table 4 |
| SARGE 4B F1(M.) | 81.7 | ChFinAnn, three-seed mean | Tables 1 and 4 |
| SARGE 4B S-M Gap | 7.5 | ChFinAnn, three-seed mean | Table 4 |
| ChFinAnn no-SFT → SARGE | 24.8 → 86.0 | Seed 13; reported paths differ | Table 2; §4.3 |
| DuEE-Fin no-SFT → SARGE | 3.3 → 78.0 | Seed 13 | Table 2; §4.3 |
| C_K(D), P_D | Weak prompt-level cues under backend-matched ablations | Not decisive modules | §3.2; §4.3 |
| Δrecord interpretation | Not a pure binding-error estimate; also includes missing/extra/wrong values and event-count errors | Required limitation | §3.6; §4.2 |
| Remaining boundary | SARGE does not solve record binding completely | Scope limitation | Introduction; Limitations; Conclusion |

## 8. Automated QA

| Check | Result | Evidence |
|---|---|---|
| PPTX ZIP/open check | PASS | Valid one-slide OOXML package. |
| Object bounds | PASS | 0 out-of-bounds objects. |
| Text overflow/truncation | PASS | All non-template text is fixed-size/noAutofit; final 150 dpi render visually checked. |
| Unexpected overlap | PASS | No inter-region overlaps; intended text-on-card intersections whitelisted and visually checked. |
| Section grouping | PASS | Seven groups at the exact specified card geometries. |
| Regional naming | PASS | Every revised object uses HDR_/TAKEHOME_/S1_…/FTR_ naming. |
| Minimum font size | PASS | Minimum explicit size 16 pt. |
| Font embedding | PASS | All exported fonts embedded and subsetted. |
| Hyperlinks | PASS | QR, URL box, and email box contain native links. |
| Rendered QR | PASS | Final 333 × 333 px PNG crop decodes to https://github.com/emmmdty/SARGE. |
| PDF open/page check | PASS | 1 page, 2520 × 3096 pt. |
| PNG open/size check | PASS | 5250 × 6451 px. |
| Background identity | PASS | Background SHA-256 unchanged. |
| Conference text | PASS | Wording, 48 pt typography, rotation, and geometry preserved; one internal line break balances the English name. |
| Method arrows | PASS | Five 1.5 pt arrowed connectors; no arrow crosses a text box. |
| Full-page rasterization | PASS | No full-page picture shape; research content remains native. |
| Key text/numbers | PASS | All required phrases and values found. |
| SOTA/SEELE wording | PASS | No SOTA, DuEE-Fin SEELE-overclaim, or 81.8 substitution. |
| Δrecord explanation | PASS | Complete non-pure-binding limitation present. |
| Grayscale preview | PASS | WRONG/CORRECT remain distinguishable by labels and ×/✓; methods remain labeled. |
| 5-second view | PASS | Title, take-home, problem, method, 85.6 ± 0.4, and 78.3 ± 0.4 are immediate anchors. |
| 30-second scan | PASS | Problem → Method → Results → Multi-event → Alignment → ExactRec/boundary. |
| Approx. 1 m readability | PASS | Section titles, body copy, and metric labels are legible in the 150 dpi full-page review. |
| Approx. 2 m readability | PASS | Title, take-home, section titles, and major numbers remain dominant. |

Overall automated QA result: **PASS**.

## 9. Unresolved items

No blocking production item is unresolved. A real URL and QR were present in the input directory, matched one another, and were validated again in the rendered final PNG.

## 10. Author confirmation required

- Confirm `https://github.com/emmmdty/SARGE` is the final public paper/code URL for printing.
- Confirm the supplied QR remains the final print QR.
- Confirm that `CITIC` and `Guotai Junan` are the preferred English short forms for the Fig. 1-derived example.
- Confirm acceptance of Linux export substitutions: Arial → Liberation Sans, 微软雅黑 → Noto Sans CJK SC, and DejaVu Sans for the superscript/envelope glyphs.

## Appendix A. Complete pre-edit slide-level shape inventory

Captured before revision. Geometry is `(left, top, width, height)` in cm; z-order follows the original slide XML.

| z | Shape ID | Name | Type | Geometry | Rotation | Font size(s) pt | Auto-fit | Text preview |
|---:|---:|---|---|---|---:|---|---|---|
| 1 | 16 | `TextBox 15` | TEXT_BOX (17) | (3.94, 2.49, 52.58, 7.11) cm | 0.0 | 50 | SHAPE_TO_FIT_TEXT (1) | SARGE: Schema-Grounded Event-Table Generation / for Chinese Financial Document-… |
| 2 | 22 | `TextBox 21` | TEXT_BOX (17) | (4.11, 10.01, 58.42, 1.57) cm | 0.0 | 26 | SHAPE_TO_FIT_TEXT (1) | Jiakai Tong¹² · Mengting Qin¹ · Yongqi Hu¹ · Xueyao Wan¹² · Yue Zhao¹² ✉ |
| 3 | 25 | `TextBox 24` | TEXT_BOX (17) | (21.98, 99.66, 65.91, 6.41) cm | 0.0 | 48 | SHAPE_TO_FIT_TEXT (1) | 2026全国知识图谱与语义计算大会 / China Conference on Knowledge Graph and Semantic Computing … |
| 4 | 26 | `TextBox 25` | TEXT_BOX (17) | (4.11, 11.61, 58.42, 1.98) cm | 0.0 | 17 | SHAPE_TO_FIT_TEXT (1) | ¹ School of Astronautics, Harbin Institute of Technology　² Zhengzhou Advanced R… |
| 5 | 27 | `Rounded Rectangle 26` | AUTO_SHAPE (1) | (2.79, 18.75, 83.31, 5.69) cm | 0.0 |  | None |  |
| 6 | 28 | `Rounded Rectangle 27` | AUTO_SHAPE (1) | (3.76, 19.76, 8.13, 1.40) cm | 0.0 | 19 | None | TAKE-HOME MESSAGE |
| 7 | 29 | `TextBox 28` | TEXT_BOX (17) | (12.90, 19.43, 71.75, 4.11) cm | 0.0 | 24 | SHAPE_TO_FIT_TEXT (1) | SARGE generates event tables under a schema contract; among comparable systems … |
| 8 | 30 | `Rounded Rectangle 29` | AUTO_SHAPE (1) | (2.79, 25.45, 26.92, 29.34) cm | 0.0 |  | None |  |
| 9 | 31 | `Oval 30` | AUTO_SHAPE (1) | (3.66, 26.16, 1.47, 1.47) cm | 0.0 | 21 | None | 1 |
| 10 | 32 | `TextBox 31` | TEXT_BOX (17) | (5.38, 25.96, 23.50, 1.83) cm | 0.0 | 30 | SHAPE_TO_FIT_TEXT (1) | Why it is hard: correct roles, wrong rows |
| 11 | 33 | `Rectangle 32` | AUTO_SHAPE (1) | (3.66, 27.94, 25.20, 0.15) cm | 0.0 |  | None |  |
| 12 | 34 | `Rounded Rectangle 33` | AUTO_SHAPE (1) | (3.68, 28.91, 25.15, 3.10) cm | 0.0 | 17 | None | Record A · 15,000,000 shares / CITIC · 2024-05-20 → 2025-05-19 |
| 13 | 35 | `Rounded Rectangle 34` | AUTO_SHAPE (1) | (3.68, 32.51, 25.15, 3.10) cm | 0.0 | 17 | None | Record B · 8,000,000 shares / Guotai Junan · 2024-06-05 → 2025-06-04 |
| 14 | 36 | `Rounded Rectangle 35` | AUTO_SHAPE (1) | (3.86, 36.53, 7.75, 1.47) cm | 0.0 | 17 | None | Shared arguments |
| 15 | 37 | `Rounded Rectangle 36` | AUTO_SHAPE (1) | (12.14, 36.53, 16.31, 1.47) cm | 0.0 | 16 | None | Private values: shares · pledgee · dates |
| 16 | 38 | `TextBox 37` | TEXT_BOX (17) | (3.81, 38.48, 24.51, 1.27) cm | 0.0 | 19 | SHAPE_TO_FIT_TEXT (1) | Recovering values ≠ assembling coherent event rows |
| 17 | 39 | `TextBox 38` | TEXT_BOX (17) | (3.81, 40.21, 11.30, 1.17) cm | 0.0 | 19 | SHAPE_TO_FIT_TEXT (1) | Predicted events / WRONG |
| 18 | 40 | `TextBox 39` | TEXT_BOX (17) | (17.22, 40.21, 10.79, 1.17) cm | 0.0 | 19 | SHAPE_TO_FIT_TEXT (1) | Gold events / CORRECT |
| 19 | 41 | `Rounded Rectangle 40` | AUTO_SHAPE (1) | (3.81, 41.71, 11.30, 9.78) cm | 0.0 | 16 | None | 15M \| Guotai Junan \| 05/20→06/04  × /  /  8M \| CITIC \| 06/05→05/19  × |
| 20 | 42 | `Rounded Rectangle 41` | AUTO_SHAPE (1) | (17.22, 41.71, 10.79, 9.78) cm | 0.0 | 16 | None | 15M \| CITIC \| 05/20→05/19  ✓ /  /  8M \| Guotai Junan \| 06/05→06/04  ✓ |
| 21 | 43 | `Connector 42` | LINE (9) | (15.19, 46.61, 1.78, 0.00) cm | 0.0 |  |  |  |
| 22 | 44 | `TextBox 43` | TEXT_BOX (17) | (3.86, 51.94, 24.51, 1.57) cm | 0.0 | 15 | SHAPE_TO_FIT_TEXT (1) | Same-type events share public arguments; short, repeated, or distributed privat… |
| 23 | 45 | `Rounded Rectangle 44` | AUTO_SHAPE (1) | (30.61, 25.45, 55.50, 29.34) cm | 0.0 |  | None |  |
| 24 | 46 | `Oval 45` | AUTO_SHAPE (1) | (31.47, 26.16, 1.47, 1.47) cm | 0.0 | 21 | None | 2 |
| 25 | 47 | `TextBox 46` | TEXT_BOX (17) | (33.20, 25.96, 52.07, 1.83) cm | 0.0 | 30 | SHAPE_TO_FIT_TEXT (1) | SARGE: render the schema as an event-table output contract |
| 26 | 48 | `Rectangle 47` | AUTO_SHAPE (1) | (31.47, 27.94, 53.77, 0.15) cm | 0.0 |  | None |  |
| 27 | 49 | `Rounded Rectangle 48` | AUTO_SHAPE (1) | (31.88, 29.01, 15.49, 7.92) cm | 0.0 |  | None |  |
| 28 | 50 | `TextBox 49` | TEXT_BOX (17) | (32.28, 29.31, 14.68, 1.32) cm | 0.0 | 24 | SHAPE_TO_FIT_TEXT (1) | Inputs |
| 29 | 51 | `TextBox 50` | TEXT_BOX (17) | (32.28, 30.78, 14.68, 5.84) cm | 0.0 | 19 | SHAPE_TO_FIT_TEXT (1) | Document D / closed schema S / surface candidates Cₖ(D) |
| 30 | 52 | `Rounded Rectangle 51` | AUTO_SHAPE (1) | (49.15, 29.01, 15.49, 7.92) cm | 0.0 |  | None |  |
| 31 | 53 | `TextBox 52` | TEXT_BOX (17) | (49.56, 29.31, 14.68, 1.32) cm | 0.0 | 24 | SHAPE_TO_FIT_TEXT (1) | Output contract |
| 32 | 54 | `TextBox 53` | TEXT_BOX (17) | (49.56, 30.78, 14.68, 5.84) cm | 0.0 | 19 | SHAPE_TO_FIT_TEXT (1) | licensed types / roles / copy source values / one event per row |
| 33 | 55 | `Rounded Rectangle 54` | AUTO_SHAPE (1) | (66.42, 29.01, 15.49, 7.92) cm | 0.0 |  | None |  |
| 34 | 56 | `TextBox 55` | TEXT_BOX (17) | (66.83, 29.31, 14.68, 1.32) cm | 0.0 | 24 | SHAPE_TO_FIT_TEXT (1) | Tuned LLM |
| 35 | 57 | `TextBox 56` | TEXT_BOX (17) | (66.83, 30.78, 14.68, 5.84) cm | 0.0 | 19 | SHAPE_TO_FIT_TEXT (1) | pθ(Y \| D,S) / answer-token loss / greedy decoding |
| 36 | 58 | `Rounded Rectangle 57` | AUTO_SHAPE (1) | (66.42, 40.77, 15.49, 7.92) cm | 0.0 |  | None |  |
| 37 | 59 | `TextBox 58` | TEXT_BOX (17) | (66.83, 41.07, 14.68, 1.32) cm | 0.0 | 24 | SHAPE_TO_FIT_TEXT (1) | Schema check |
| 38 | 60 | `TextBox 59` | TEXT_BOX (17) | (66.83, 42.55, 14.68, 5.84) cm | 0.0 | 19 | SHAPE_TO_FIT_TEXT (1) | filter invalid types / roles / remove empty fields / fixed role order |
| 39 | 61 | `Rounded Rectangle 60` | AUTO_SHAPE (1) | (49.15, 40.77, 15.49, 7.92) cm | 0.0 |  | None |  |
| 40 | 62 | `TextBox 61` | TEXT_BOX (17) | (49.56, 41.07, 14.68, 1.32) cm | 0.0 | 24 | SHAPE_TO_FIT_TEXT (1) | Fixed-slot table |
| 41 | 63 | `TextBox 62` | TEXT_BOX (17) | (49.56, 42.55, 14.68, 5.84) cm | 0.0 | 19 | SHAPE_TO_FIT_TEXT (1) | type \| r₁ \| r₂ \| … / e₁ \| value \| value / e₂ \| value \| value |
| 42 | 64 | `Rounded Rectangle 63` | AUTO_SHAPE (1) | (31.88, 40.77, 15.49, 7.92) cm | 0.0 |  | None |  |
| 43 | 65 | `TextBox 64` | TEXT_BOX (17) | (32.28, 41.07, 14.68, 1.32) cm | 0.0 | 24 | SHAPE_TO_FIT_TEXT (1) | Evaluation |
| 44 | 66 | `TextBox 65` | TEXT_BOX (17) | (32.28, 42.55, 14.68, 5.84) cm | 0.0 | 19 | SHAPE_TO_FIT_TEXT (1) | Role F1 / ExactRec / Δrecord |
| 45 | 67 | `Connector 66` | LINE (9) | (47.62, 32.97, 1.27, 0.00) cm | 0.0 |  |  |  |
| 46 | 68 | `Connector 67` | LINE (9) | (64.90, 32.97, 1.27, 0.00) cm | 0.0 |  |  |  |
| 47 | 69 | `Connector 68` | LINE (9) | (74.17, 37.13, 0.00, 3.38) cm | 0.0 |  |  |  |
| 48 | 70 | `Connector 69` | LINE (9) | (64.90, 44.75, 1.27, 0.00) cm | 0.0 |  |  |  |
| 49 | 71 | `Connector 70` | LINE (9) | (47.62, 44.75, 1.27, 0.00) cm | 0.0 |  |  |  |
| 50 | 72 | `Rounded Rectangle 71` | AUTO_SHAPE (1) | (31.88, 49.91, 9.91, 1.57) cm | 0.0 | 16 | None | Schema closure |
| 51 | 73 | `Rounded Rectangle 72` | AUTO_SHAPE (1) | (42.49, 49.91, 11.94, 1.57) cm | 0.0 | 16 | None | Copy surface values |
| 52 | 74 | `Rounded Rectangle 73` | AUTO_SHAPE (1) | (55.14, 49.91, 10.92, 1.57) cm | 0.0 | 16 | None | One event per row |
| 53 | 75 | `Rounded Rectangle 74` | AUTO_SHAPE (1) | (66.78, 49.91, 11.18, 1.57) cm | 0.0 | 16 | None | Deterministic decode |
| 54 | 76 | `TextBox 75` | TEXT_BOX (17) | (32.05, 52.02, 52.58, 1.32) cm | 0.0 | 17 | SHAPE_TO_FIT_TEXT (1) | One prediction object: benchmark-compatible fixed-slot event rows |
| 55 | 77 | `Rounded Rectangle 76` | AUTO_SHAPE (1) | (2.79, 55.70, 26.04, 23.50) cm | 0.0 |  | None |  |
| 56 | 78 | `Oval 77` | AUTO_SHAPE (1) | (3.66, 56.41, 1.47, 1.47) cm | 0.0 | 21 | None | 3 |
| 57 | 79 | `TextBox 78` | TEXT_BOX (17) | (5.38, 56.21, 22.61, 1.83) cm | 0.0 | 30 | SHAPE_TO_FIT_TEXT (1) | Three-seed main results |
| 58 | 80 | `Rectangle 79` | AUTO_SHAPE (1) | (3.66, 58.19, 24.31, 0.15) cm | 0.0 |  | None |  |
| 59 | 81 | `Rounded Rectangle 80` | AUTO_SHAPE (1) | (3.81, 59.05, 11.30, 3.94) cm | 0.0 |  | None |  |
| 60 | 82 | `TextBox 81` | TEXT_BOX (17) | (4.17, 59.33, 10.59, 1.83) cm | 0.0 | 31 | SHAPE_TO_FIT_TEXT (1) | 85.6±0.4 |
| 61 | 83 | `TextBox 82` | TEXT_BOX (17) | (4.17, 61.14, 10.59, 1.37) cm | 0.0 | 17 | SHAPE_TO_FIT_TEXT (1) | ChFinAnn Role F1 |
| 62 | 84 | `Rounded Rectangle 83` | AUTO_SHAPE (1) | (15.75, 59.05, 12.06, 3.94) cm | 0.0 |  | None |  |
| 63 | 85 | `TextBox 84` | TEXT_BOX (17) | (16.10, 59.33, 11.35, 1.83) cm | 0.0 | 31 | SHAPE_TO_FIT_TEXT (1) | 78.3±0.4 |
| 64 | 86 | `TextBox 85` | TEXT_BOX (17) | (16.10, 61.14, 11.35, 1.37) cm | 0.0 | 17 | SHAPE_TO_FIT_TEXT (1) | DuEE-Fin Role F1 |
| 65 | 87 | `TextBox 86` | TEXT_BOX (17) | (3.86, 63.70, 23.88, 1.17) cm | 0.0 | 18 | SHAPE_TO_FIT_TEXT (1) | Direct delta to the strongest aggregate baseline |
| 66 | 88 | `Rounded Rectangle 87` | AUTO_SHAPE (1) | (3.81, 65.07, 24.00, 3.51) cm | 0.0 |  | None |  |
| 67 | 89 | `TextBox 88` | TEXT_BOX (17) | (4.27, 65.41, 5.71, 1.07) cm | 0.0 | 18 | SHAPE_TO_FIT_TEXT (1) | ChFinAnn |
| 68 | 90 | `TextBox 89` | TEXT_BOX (17) | (4.27, 66.65, 8.26, 1.12) cm | 0.0 | 15 | SHAPE_TO_FIT_TEXT (1) | SEELE 85.1 |
| 69 | 91 | `TextBox 90` | TEXT_BOX (17) | (12.19, 65.58, 7.87, 1.78) cm | 0.0 | 26 | SHAPE_TO_FIT_TEXT (1) | SARGE 85.6 |
| 70 | 92 | `Rounded Rectangle 91` | AUTO_SHAPE (1) | (22.23, 65.79, 4.57, 1.83) cm | 0.0 | 21 | None | Δ +0.5 |
| 71 | 93 | `Rounded Rectangle 92` | AUTO_SHAPE (1) | (3.81, 69.14, 24.00, 3.51) cm | 0.0 |  | None |  |
| 72 | 94 | `TextBox 93` | TEXT_BOX (17) | (4.27, 69.47, 5.71, 1.07) cm | 0.0 | 18 | SHAPE_TO_FIT_TEXT (1) | DuEE-Fin |
| 73 | 95 | `TextBox 94` | TEXT_BOX (17) | (4.27, 70.71, 8.26, 1.12) cm | 0.0 | 15 | SHAPE_TO_FIT_TEXT (1) | SEELE 80.8 |
| 74 | 96 | `TextBox 95` | TEXT_BOX (17) | (12.19, 69.65, 7.87, 1.78) cm | 0.0 | 26 | SHAPE_TO_FIT_TEXT (1) | SARGE 78.3 |
| 75 | 97 | `Rounded Rectangle 96` | AUTO_SHAPE (1) | (22.23, 69.85, 4.57, 1.83) cm | 0.0 | 21 | None | Δ −2.5 |
| 76 | 98 | `TextBox 97` | TEXT_BOX (17) | (3.94, 73.46, 23.50, 3.51) cm | 0.0 | 16 | SHAPE_TO_FIT_TEXT (1) | ChFinAnn: numerically above listed baselines / DuEE-Fin: below SEELE, above EPA… |
| 77 | 99 | `Rounded Rectangle 98` | AUTO_SHAPE (1) | (29.59, 55.70, 26.04, 23.50) cm | 0.0 |  | None |  |
| 78 | 100 | `Oval 99` | AUTO_SHAPE (1) | (30.45, 56.41, 1.47, 1.47) cm | 0.0 | 21 | None | 4 |
| 79 | 101 | `TextBox 100` | TEXT_BOX (17) | (32.18, 56.21, 22.61, 1.83) cm | 0.0 | 30 | SHAPE_TO_FIT_TEXT (1) | Multi-event robustness |
| 80 | 102 | `Rectangle 101` | AUTO_SHAPE (1) | (30.45, 58.19, 24.31, 0.15) cm | 0.0 |  | None |  |
| 81 | 103 | `Rounded Rectangle 102` | AUTO_SHAPE (1) | (30.61, 59.05, 11.30, 3.94) cm | 0.0 |  | None |  |
| 82 | 104 | `TextBox 103` | TEXT_BOX (17) | (30.96, 59.33, 10.59, 1.83) cm | 0.0 | 31 | SHAPE_TO_FIT_TEXT (1) | 81.7±0.1 |
| 83 | 105 | `TextBox 104` | TEXT_BOX (17) | (30.96, 61.14, 10.59, 1.37) cm | 0.0 | 17 | SHAPE_TO_FIT_TEXT (1) | ChFinAnn F1(M.) · SARGE 4B |
| 84 | 106 | `Rounded Rectangle 105` | AUTO_SHAPE (1) | (42.62, 59.05, 11.81, 3.94) cm | 0.0 |  | None |  |
| 85 | 107 | `TextBox 106` | TEXT_BOX (17) | (42.98, 59.33, 11.10, 1.83) cm | 0.0 | 31 | SHAPE_TO_FIT_TEXT (1) | 7.5 pts |
| 86 | 108 | `TextBox 107` | TEXT_BOX (17) | (42.98, 61.14, 11.10, 1.37) cm | 0.0 | 17 | SHAPE_TO_FIT_TEXT (1) | SARGE S–M gap · EPAL 13.1 |
| 87 | 109 | `TextBox 108` | TEXT_BOX (17) | (30.73, 63.63, 23.75, 1.14) cm | 0.0 | 15 | SHAPE_TO_FIT_TEXT (1) | ChFinAnn F1(M.) · 72–84 shown explicitly |
| 88 | 110 | `TextBox 109` | TEXT_BOX (17) | (30.61, 65.20, 5.21, 1.17) cm | 0.0 | 16 | SHAPE_TO_FIT_TEXT (1) | EPAL |
| 89 | 111 | `Connector 110` | LINE (9) | (36.58, 65.66, 14.73, 0.00) cm | 0.0 |  |  |  |
| 90 | 112 | `Oval 111` | AUTO_SHAPE (1) | (41.84, 65.28, 0.76, 0.76) cm | 0.0 |  | None |  |
| 91 | 113 | `TextBox 112` | TEXT_BOX (17) | (42.73, 65.10, 2.29, 1.27) cm | 0.0 | 18 | SHAPE_TO_FIT_TEXT (1) | 76.6 |
| 92 | 114 | `TextBox 113` | TEXT_BOX (17) | (30.61, 67.49, 5.21, 1.17) cm | 0.0 | 16 | SHAPE_TO_FIT_TEXT (1) | SARGE 1.7B |
| 93 | 115 | `Connector 114` | LINE (9) | (36.58, 67.94, 14.73, 0.00) cm | 0.0 |  |  |  |
| 94 | 116 | `Oval 115` | AUTO_SHAPE (1) | (45.53, 67.56, 0.76, 0.76) cm | 0.0 |  | None |  |
| 95 | 117 | `TextBox 116` | TEXT_BOX (17) | (46.41, 67.39, 2.29, 1.27) cm | 0.0 | 18 | SHAPE_TO_FIT_TEXT (1) | 79.6 |
| 96 | 118 | `TextBox 117` | TEXT_BOX (17) | (30.61, 69.77, 5.21, 1.17) cm | 0.0 | 16 | SHAPE_TO_FIT_TEXT (1) | SARGE 4B |
| 97 | 119 | `Connector 118` | LINE (9) | (36.58, 70.23, 14.73, 0.00) cm | 0.0 |  |  |  |
| 98 | 120 | `Oval 119` | AUTO_SHAPE (1) | (48.10, 69.85, 0.76, 0.76) cm | 0.0 |  | None |  |
| 99 | 121 | `TextBox 120` | TEXT_BOX (17) | (48.99, 69.67, 2.29, 1.27) cm | 0.0 | 18 | SHAPE_TO_FIT_TEXT (1) | 81.7 |
| 100 | 122 | `Connector 121` | LINE (9) | (36.58, 71.20, 0.00, 0.46) cm | 0.0 |  |  |  |
| 101 | 123 | `TextBox 122` | TEXT_BOX (17) | (35.69, 71.68, 1.78, 0.91) cm | 0.0 | 13 | SHAPE_TO_FIT_TEXT (1) | 72 |
| 102 | 124 | `Connector 123` | LINE (9) | (41.49, 71.20, 0.00, 0.46) cm | 0.0 |  |  |  |
| 103 | 125 | `TextBox 124` | TEXT_BOX (17) | (40.60, 71.68, 1.78, 0.91) cm | 0.0 | 13 | SHAPE_TO_FIT_TEXT (1) | 76 |
| 104 | 126 | `Connector 125` | LINE (9) | (46.40, 71.20, 0.00, 0.46) cm | 0.0 |  |  |  |
| 105 | 127 | `TextBox 126` | TEXT_BOX (17) | (45.51, 71.68, 1.78, 0.91) cm | 0.0 | 13 | SHAPE_TO_FIT_TEXT (1) | 80 |
| 106 | 128 | `Connector 127` | LINE (9) | (51.31, 71.20, 0.00, 0.46) cm | 0.0 |  |  |  |
| 107 | 129 | `TextBox 128` | TEXT_BOX (17) | (50.42, 71.68, 1.78, 0.91) cm | 0.0 | 13 | SHAPE_TO_FIT_TEXT (1) | 84 |
| 108 | 130 | `TextBox 129` | TEXT_BOX (17) | (30.99, 73.66, 22.99, 3.51) cm | 0.0 | 16 | SHAPE_TO_FIT_TEXT (1) | Among comparable systems reporting F1(S.)/F1(M.), SARGE has the smallest multi-… |
| 109 | 131 | `Rounded Rectangle 130` | AUTO_SHAPE (1) | (56.39, 55.70, 29.72, 23.50) cm | 0.0 |  | None |  |
| 110 | 132 | `Oval 131` | AUTO_SHAPE (1) | (57.25, 56.41, 1.47, 1.47) cm | 0.0 | 21 | None | 5 |
| 111 | 133 | `TextBox 132` | TEXT_BOX (17) | (58.98, 56.21, 26.29, 1.83) cm | 0.0 | 30 | SHAPE_TO_FIT_TEXT (1) | The gain comes from schema alignment |
| 112 | 134 | `Rectangle 133` | AUTO_SHAPE (1) | (57.25, 58.19, 27.99, 0.15) cm | 0.0 |  | None |  |
| 113 | 135 | `TextBox 134` | TEXT_BOX (17) | (57.71, 58.93, 27.05, 1.14) cm | 0.0 | 17 | SHAPE_TO_FIT_TEXT (1) | Same 4B base · seed 13 |
| 114 | 136 | `Rounded Rectangle 135` | AUTO_SHAPE (1) | (57.78, 61.01, 11.56, 3.94) cm | 0.0 |  | None |  |
| 115 | 137 | `TextBox 136` | TEXT_BOX (17) | (58.14, 61.29, 10.85, 1.83) cm | 0.0 | 31 | SHAPE_TO_FIT_TEXT (1) | 24.8 → 86.0 |
| 116 | 138 | `TextBox 137` | TEXT_BOX (17) | (58.14, 63.09, 10.85, 1.37) cm | 0.0 | 17 | SHAPE_TO_FIT_TEXT (1) | ChFinAnn · no SFT → SARGE |
| 117 | 139 | `Rounded Rectangle 138` | AUTO_SHAPE (1) | (71.12, 61.01, 13.34, 3.94) cm | 0.0 |  | None |  |
| 118 | 140 | `TextBox 139` | TEXT_BOX (17) | (71.48, 61.29, 12.62, 1.83) cm | 0.0 | 31 | SHAPE_TO_FIT_TEXT (1) | 3.3 → 78.0 |
| 119 | 141 | `TextBox 140` | TEXT_BOX (17) | (71.48, 63.09, 12.62, 1.37) cm | 0.0 | 17 | SHAPE_TO_FIT_TEXT (1) | DuEE-Fin · no SFT → SARGE |
| 120 | 142 | `TextBox 141` | TEXT_BOX (17) | (58.42, 66.04, 25.65, 1.83) cm | 0.0 | 21 | SHAPE_TO_FIT_TEXT (1) | Supervised alignment—not model scale—drives the gain |
| 121 | 143 | `TextBox 142` | TEXT_BOX (17) | (58.42, 68.58, 25.65, 2.92) cm | 0.0 | 17 | SHAPE_TO_FIT_TEXT (1) | Without SFT, the model often emits legal but empty or sparse rows; supervision … |
| 122 | 144 | `Rounded Rectangle 143` | AUTO_SHAPE (1) | (61.47, 72.26, 19.56, 1.65) cm | 0.0 | 14 | None | SFT dominates · greedy is steadier · prompt cues are weak |
| 123 | 145 | `TextBox 144` | TEXT_BOX (17) | (57.78, 74.55, 26.92, 1.91) cm | 0.0 | 15 | SHAPE_TO_FIT_TEXT (1) | Conclusion: the main gain comes from supervised alignment to the fixed-schema e… |
| 124 | 146 | `Rounded Rectangle 145` | AUTO_SHAPE (1) | (2.79, 80.06, 33.15, 15.95) cm | 0.0 |  | None |  |
| 125 | 147 | `Oval 146` | AUTO_SHAPE (1) | (3.66, 80.77, 1.47, 1.47) cm | 0.0 | 21 | None | 6 |
| 126 | 148 | `TextBox 147` | TEXT_BOX (17) | (5.38, 80.57, 29.72, 1.83) cm | 0.0 | 30 | SHAPE_TO_FIT_TEXT (1) | ExactRec exposes the remaining record-level gap |
| 127 | 149 | `Rectangle 148` | AUTO_SHAPE (1) | (3.66, 82.55, 31.42, 0.15) cm | 0.0 |  | None |  |
| 128 | 150 | `TextBox 149` | TEXT_BOX (17) | (3.94, 83.82, 5.71, 0.84) cm | 0.0 | 18 | SHAPE_TO_FIT_TEXT (1) | ChFinAnn · Role F1 |
| 129 | 151 | `Rounded Rectangle 150` | AUTO_SHAPE (1) | (9.91, 83.92, 22.23, 0.56) cm | 0.0 |  | None |  |
| 130 | 152 | `Rounded Rectangle 151` | AUTO_SHAPE (1) | (9.91, 83.92, 19.02, 0.56) cm | 0.0 |  | None |  |
| 131 | 153 | `TextBox 152` | TEXT_BOX (17) | (32.46, 83.77, 1.78, 0.91) cm | 0.0 | 18 | SHAPE_TO_FIT_TEXT (1) | 85.6 |
| 132 | 154 | `TextBox 153` | TEXT_BOX (17) | (3.94, 85.22, 5.71, 0.84) cm | 0.0 | 18 | SHAPE_TO_FIT_TEXT (1) | ChFinAnn · ExactRec |
| 133 | 155 | `Rounded Rectangle 154` | AUTO_SHAPE (1) | (9.91, 85.32, 22.23, 0.56) cm | 0.0 |  | None |  |
| 134 | 156 | `Rounded Rectangle 155` | AUTO_SHAPE (1) | (9.91, 85.32, 12.47, 0.56) cm | 0.0 |  | None |  |
| 135 | 157 | `TextBox 156` | TEXT_BOX (17) | (32.46, 85.17, 1.78, 0.91) cm | 0.0 | 18 | SHAPE_TO_FIT_TEXT (1) | 56.1 |
| 136 | 158 | `TextBox 157` | TEXT_BOX (17) | (3.94, 87.50, 5.71, 0.84) cm | 0.0 | 18 | SHAPE_TO_FIT_TEXT (1) | DuEE-Fin · Role F1 |
| 137 | 159 | `Rounded Rectangle 158` | AUTO_SHAPE (1) | (9.91, 87.60, 22.23, 0.56) cm | 0.0 |  | None |  |
| 138 | 160 | `Rounded Rectangle 159` | AUTO_SHAPE (1) | (9.91, 87.60, 17.40, 0.56) cm | 0.0 |  | None |  |
| 139 | 161 | `TextBox 160` | TEXT_BOX (17) | (32.46, 87.45, 1.78, 0.91) cm | 0.0 | 18 | SHAPE_TO_FIT_TEXT (1) | 78.3 |
| 140 | 162 | `TextBox 161` | TEXT_BOX (17) | (3.94, 88.90, 5.71, 0.84) cm | 0.0 | 18 | SHAPE_TO_FIT_TEXT (1) | DuEE-Fin · ExactRec |
| 141 | 163 | `Rounded Rectangle 162` | AUTO_SHAPE (1) | (9.91, 89.00, 22.23, 0.56) cm | 0.0 |  | None |  |
| 142 | 164 | `Rounded Rectangle 163` | AUTO_SHAPE (1) | (9.91, 89.00, 9.62, 0.56) cm | 0.0 |  | None |  |
| 143 | 165 | `TextBox 164` | TEXT_BOX (17) | (32.46, 88.85, 1.78, 0.91) cm | 0.0 | 18 | SHAPE_TO_FIT_TEXT (1) | 43.3 |
| 144 | 166 | `Rounded Rectangle 165` | AUTO_SHAPE (1) | (3.94, 90.68, 13.21, 3.94) cm | 0.0 |  | None |  |
| 145 | 167 | `TextBox 166` | TEXT_BOX (17) | (4.29, 90.96, 12.50, 1.83) cm | 0.0 | 31 | SHAPE_TO_FIT_TEXT (1) | Δrecord = 29.5 |
| 146 | 168 | `TextBox 167` | TEXT_BOX (17) | (4.29, 92.76, 12.50, 1.37) cm | 0.0 | 17 | SHAPE_TO_FIT_TEXT (1) | ChFinAnn · 3-seed mean |
| 147 | 169 | `Rounded Rectangle 168` | AUTO_SHAPE (1) | (17.78, 90.68, 14.48, 3.94) cm | 0.0 |  | None |  |
| 148 | 170 | `TextBox 169` | TEXT_BOX (17) | (18.14, 90.96, 13.77, 1.83) cm | 0.0 | 31 | SHAPE_TO_FIT_TEXT (1) | Δrecord = 35.1 |
| 149 | 171 | `TextBox 170` | TEXT_BOX (17) | (18.14, 92.76, 13.77, 1.37) cm | 0.0 | 17 | SHAPE_TO_FIT_TEXT (1) | DuEE-Fin · 3-seed mean |
| 150 | 172 | `TextBox 171` | TEXT_BOX (17) | (3.94, 94.69, 29.46, 0.81) cm | 0.0 | 13 | SHAPE_TO_FIT_TEXT (1) | Δrecord also reflects missing, extra, wrong values and event-count errors; it i… |
| 151 | 173 | `Rounded Rectangle 172` | AUTO_SHAPE (1) | (36.70, 80.06, 49.40, 15.95) cm | 0.0 |  | None |  |
| 152 | 174 | `Oval 173` | AUTO_SHAPE (1) | (37.57, 80.77, 1.47, 1.47) cm | 0.0 | 21 | None | 7 |
| 153 | 175 | `TextBox 174` | TEXT_BOX (17) | (39.29, 80.57, 45.97, 1.83) cm | 0.0 | 30 | SHAPE_TO_FIT_TEXT (1) | Contribution, boundary, and next step |
| 154 | 176 | `Rectangle 175` | AUTO_SHAPE (1) | (37.57, 82.55, 47.68, 0.15) cm | 0.0 |  | None |  |
| 155 | 177 | `Rounded Rectangle 176` | AUTO_SHAPE (1) | (37.80, 83.62, 14.53, 6.48) cm | 0.0 |  | None |  |
| 156 | 178 | `TextBox 177` | TEXT_BOX (17) | (38.30, 83.95, 13.51, 1.32) cm | 0.0 | 19 | SHAPE_TO_FIT_TEXT (1) | Task |
| 157 | 179 | `TextBox 178` | TEXT_BOX (17) | (38.43, 85.39, 13.26, 3.96) cm | 0.0 | 16 | SHAPE_TO_FIT_TEXT (1) | Closed-schema DEE → event-table generation |
| 158 | 180 | `Rounded Rectangle 179` | AUTO_SHAPE (1) | (53.34, 83.62, 14.53, 6.48) cm | 0.0 |  | None |  |
| 159 | 181 | `TextBox 180` | TEXT_BOX (17) | (53.85, 83.95, 13.51, 1.32) cm | 0.0 | 19 | SHAPE_TO_FIT_TEXT (1) | Contract |
| 160 | 182 | `TextBox 181` | TEXT_BOX (17) | (53.98, 85.39, 13.26, 3.96) cm | 0.0 | 16 | SHAPE_TO_FIT_TEXT (1) | Evidence · roles · source values · rows |
| 161 | 183 | `Rounded Rectangle 182` | AUTO_SHAPE (1) | (68.88, 83.62, 14.53, 6.48) cm | 0.0 |  | None |  |
| 162 | 184 | `TextBox 183` | TEXT_BOX (17) | (69.39, 83.95, 13.51, 1.32) cm | 0.0 | 19 | SHAPE_TO_FIT_TEXT (1) | Diagnosis |
| 163 | 185 | `TextBox 184` | TEXT_BOX (17) | (69.52, 85.39, 13.26, 3.96) cm | 0.0 | 16 | SHAPE_TO_FIT_TEXT (1) | Role F1 finds facts; ExactRec checks rows |
| 164 | 186 | `Rounded Rectangle 185` | AUTO_SHAPE (1) | (37.80, 90.98, 46.48, 3.68) cm | 0.0 | 16 | None | Boundary: SARGE improves but does not solve record binding; ExactRec still trai… |
| 165 | 187 | `TextBox 186` | TEXT_BOX (17) | (38.23, 94.84, 45.47, 0.76) cm | 0.0 | 12 | SHAPE_TO_FIT_TEXT (1) | Source: paper Tables 1–4. Main results are three-seed means; no-SFT comparisons… |
| 166 | 188 | `Rounded Rectangle 187` | AUTO_SHAPE (1) | (4.37, 99.69, 5.46, 5.46) cm | 0.0 |  | None |  |
| 167 | 189 | `Picture 188` | PICTURE (13) | (4.50, 99.82, 5.21, 5.21) cm | 0.0 |  |  |  |
| 168 | 190 | `TextBox 189` | TEXT_BOX (17) | (10.41, 99.62, 10.67, 1.47) cm | 0.0 | 22 | SHAPE_TO_FIT_TEXT (1) | Code & paper |
| 169 | 191 | `TextBox 190` | TEXT_BOX (17) | (10.41, 101.35, 10.67, 2.67) cm | 0.0 | 17 | SHAPE_TO_FIT_TEXT (1) | github.com/emmmdty/SARGE / yue.zhao@hit.edu.cn |

## Appendix B. Master and layout audit

| Deck | Layout | Master | Layout shapes | Master shapes | Slide background |
|---|---|---|---:|---:|---|
| `SARGE_CCKS2026_poster_en.pptx` | `Title Slide` (`/ppt/slideLayouts/slideLayout1.xml`) | `/ppt/slideMasters/slideMaster1.xml` | 5 | 5 | 8268 × 10157 JPEG, SHA-256 `75c64d300ba3826ee6da34bb658e081c35ce01724ed1570e9564ebd0f185ded7` |
| `CCKS2026-poster参考模板(1).pptx` | `Title Slide` (`/ppt/slideLayouts/slideLayout1.xml`) | `/ppt/slideMasters/slideMaster1.xml` | 5 | 5 | 8268 × 10157 JPEG, SHA-256 `75c64d300ba3826ee6da34bb658e081c35ce01724ed1570e9564ebd0f185ded7` |
| `SARGE_CCKS2026_poster_en_revised.pptx` | `Title Slide` (`/ppt/slideLayouts/slideLayout1.xml`) | `/ppt/slideMasters/slideMaster1.xml` | 5 | 5 | 8268 × 10157 JPEG, SHA-256 `75c64d300ba3826ee6da34bb658e081c35ce01724ed1570e9564ebd0f185ded7` |

All three presentations use the same five-placeholder Title Slide layout and five-placeholder master. No master/layout shape was modified.
