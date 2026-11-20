# SARGE CCKS 2026 English Poster Visual Refinement Design

## Objective

Refine the existing English SARGE poster so that a conference attendee can
understand the problem, method, primary results, and remaining boundary within
approximately 30 seconds. The revision should borrow the hierarchy, whitespace,
and visual storytelling qualities seen in strong conference and award-winning
posters without copying their branding, artwork, or research content.

The approved direction is **hero method diagram + evidence band**.

## Source of Truth and Invariants

The refinement must preserve:

- `SARGE_CCKS2026_poster_en_revised.pptx` as the sole editable v2 base;
- every research fact, value, qualification, author, affiliation, and claim
  boundary already verified against `main_en_final(6).pdf`;
- the 88.90 cm × 109.22 cm portrait page;
- the complete CCKS background, logo, top decoration, bottom decoration, and
  conference text;
- the current verified public URL, QR code, email, and hyperlinks;
- editable native PowerPoint text, shapes, groups, and connectors;
- the established semantic colors:
  - blue for primary results;
  - teal for SARGE and positive outcomes;
  - orange for baselines and ablations;
  - red for wrong examples and boundaries;
  - purple for ExactRec and Δrecord;
- minimum 16 pt source/seed notes and minimum 18 pt ordinary body text;
- the SEELE, Doc2Event, Δrecord, and record-binding qualifications verbatim;
- the prohibition on introducing any SOTA, leaderboard, or “outperforms SEELE
  on DuEE-Fin” claim.

The current revised files remain unchanged. The visual refinement is saved as a
separate `v2` deliverable set.

“Preserve the conference template” means preserve the v1 background JPEG with
SHA-256
`75c64d300ba3826ee6da34bb658e081c35ce01724ed1570e9564ebd0f185ded7`
and preserve the v1 conference text shape's wording, internal line break,
rotation, 48 pt formatting, and geometry:
`x=21.9798 cm`, `y=99.6597 cm`, `w=65.9077 cm`, `h=6.4082 cm`.

The URL/QR pair is mechanically verified but remains pending final author
confirmation for print. The CITIC/Guotai Junan short forms and Linux export font
substitutions also remain pending author confirmation; v2 must not report these
items as newly resolved.

## Reference Principles

The design uses the following principles observed in official conference and
award-poster material:

1. One obvious message and one obvious visual anchor.
2. Large, self-explanatory graphics with minimal supporting prose.
3. A left-to-right, top-to-bottom narrative that remains visible at a distance.
4. Strong contrast between primary evidence and contextual qualifications.
5. Fewer decorative containers and more whitespace between conceptual groups.
6. Direct labels instead of legends or duplicated numeric decoration.

References:

- IEEE VIS 2024 Best Poster, *Transformer Explainer*.
- IEEE VIS 2023 Best Poster, *ManimML*.
- MIT, *Making a Great Poster*.
- ACM CHI 2026 poster presentation guidance.

## Visual Diagnosis of the Current Poster

The current poster already has a strong title, take-home band, clear section
numbering, accurate data, and a correct reading order. Its main limitations are:

- repeated rounded card borders make the page feel like a dashboard;
- all seven sections have nearly equal visual weight;
- Sections 3–6 distribute the evidence across several independent containers;
- the six-node method diagram is correct but visually resembles a form;
- Section 2 is dense while Section 5 has comparatively large unused space;
- five accent colors occupy similar visual area, weakening the blue/teal story;
- several qualifiers sit at unrelated card bottoms rather than forming a clear
  secondary annotation layer.

## Approved Layout Strategy

### 1. Header and Take-home

Keep the existing header, title, authors, affiliations, logo clearance, and
take-home wording. Preserve the conference template exactly.

The take-home remains the bridge between the conference header and research
body. Its visual treatment stays dark blue with a teal label.

### 2. Hero Row: Problem and Method

Retain the current Section 1 / Section 2 widths and overall body row position.

Section 1 remains a concrete wrong-row versus correct-row example. Reduce
nonessential outlines and make the existing central contrast visually read as:

`same values → wrong row assembly` versus `coherent gold rows`.

Section 2 becomes the page's dominant research visual:

- keep the six verified steps and snake flow;
- emphasize `Output contract` and `Fixed-slot table` as the central pair;
- reduce the fill strength of Inputs, LLM, normalization, and evaluation;
- use larger step numbers, shorter arrows, and a clearer continuous route;
- reduce card-within-card decoration;
- preserve the optional status of `P_D` and the non-decisive role of `C_K(D)`.

### 3. Evidence Band: Main Results, Multi-event Robustness, Alignment

Retain Sections 3–5 as separate editable groups, but align them visually as one
continuous evidence band:

- retain three distinct white outer cards, but give their numeric-anchor zones
  the same pale-blue/white treatment;
- align all three title dividers, major-number top edges, and metric-label
  typographic baselines;
- keep the existing 0.8 cm gutters, while using matching internal left/right
  padding so the eye perceives one horizontal sequence;
- make `85.6 ± 0.4`, `78.3 ± 0.4`, `81.7`, and `7.5` the dominant anchors;
- keep SEELE, EPAL, seed, and inference-path qualifications visually secondary;
- reduce internal rounded rectangles and decorative borders;
- retain Section 5's two existing evidence sentences verbatim, but place them as
  compact aligned text blocks so its whitespace matches Sections 3 and 4;
- keep no-SFT values explicitly scoped to seed 13.

### 4. Diagnostic and Boundary Row

Keep Sections 6 and 7 as the final row.

- simplify the ExactRec matrix to two dataset rows with direct labels;
- keep F1 in blue/teal and ExactRec/Δrecord in purple;
- visually connect the Δrecord explanation to the red boundary box;
- maintain the full “not a pure binding-error estimate” qualification;
- keep the three contributions but lower their visual weight relative to the
  boundary statement.

### 5. Card Chrome and Color Use

- Keep outer section cards to satisfy the established poster system, but reduce
  border contrast and corner prominence.
- Remove or soften approximately 35–45% of internal container strokes.
- Reserve saturated blue/teal for the method route and main numeric anchors.
- Use orange, purple, and red in smaller, semantically targeted areas.
- Do not add shadows, gradients, photographs, or third-party imagery.

## Imagegen Reference Mockup

Generate one portrait reference mockup using the current poster PNG as the edit
target. It is a visual composition reference only and is not inserted into the
PowerPoint.

The prompt must:

- preserve the CCKS header/footer and page proportions;
- preserve the overall problem → method → evidence → boundary story;
- show a dominant method hero and continuous evidence band;
- reduce nested rounded cards and increase whitespace;
- use abstract placeholder text for small copy so generated text cannot become a
  research source;
- include only the exact major anchors `SARGE`, `85.6`, `78.3`, `81.7`, and
  `ExactRec`;
- forbid new claims, logos, data, illustrations, and photographic imagery.

Save the selected mockup as:

`paper/ccks_2026/poster/SARGE_CCKS2026_poster_en_visual_reference.png`

## Deliverables

- `SARGE_CCKS2026_poster_en_visual_reference.png`
- `SARGE_CCKS2026_poster_en_revised_v2.pptx`
- `SARGE_CCKS2026_poster_en_revised_v2.pdf`
- `SARGE_CCKS2026_poster_en_revised_v2.png`
- `poster_visual_analysis.md`

The existing source, backup, baseline, and first revised deliverables must not be
overwritten.

## Implementation Constraints

- Reuse the current verified v1 research wording and numerical values.
- Rebuild only visual styling and geometry needed for the approved direction.
- Do not paraphrase, condense, or add research wording. Line-break-only edits are
  allowed. Any other wording change requires a fresh comparison to the paper and
  explicit documentation before implementation.
- Keep all research text editable.
- Keep each section grouped and regionally named.
- Use fixed-size text boxes with no shrink-on-overflow.
- Preserve hyperlink behavior and the background JPEG byte-for-byte.
- Use LibreOffice for deterministic Linux export and Poppler for the 150 dpi
  full-page PNG.

## Acceptance Criteria

The v2 revision is accepted when:

- the method is the dominant research visual after the title and take-home;
- Sections 3–5 read as one evidence sequence rather than three disconnected
  dashboards;
- `85.6 ± 0.4`, `78.3 ± 0.4`, `81.7`, and `7.5` are visible within five seconds;
- the 30-second scan remains Problem → Method → Results → Multi-event evidence
  → Alignment → ExactRec/boundary;
- no verified fact, qualifier, or template element changes;
- all text remains editable and at or above the established size thresholds;
- no shape is out of bounds and no text, arrow, or object is visibly clipped or
  obstructed;
- the PDF uses the required 2520 × 3096 pt page and embeds every exported font;
- the 150 dpi PNG is approximately 5250 × 6450 px;
- the final rendered QR still decodes to the supplied public URL;
- independent visual QA finds no major issue.

## V2 Verification Evidence

The v2 validator must target the v2 filenames and record the following evidence
in `poster_visual_analysis.md`:

- exact normalized text and qualifier comparison against the v1 PPTX;
- unchanged background SHA-256;
- recursive object bounds and visible clipping/overlap review;
- fixed-size/no-autofit status for all non-template text;
- minimum font sizes;
- section grouping and regional naming;
- native URL, QR, and email hyperlink targets;
- absence of a full-page picture shape or rasterized research region;
- PDF page size and font embedding;
- 150 dpi PNG dimensions;
- successful rendered-QR decoding;
- unchanged SHA-256 hashes for the source, backup, baseline, v1 PPTX, v1 PDF,
  v1 PNG, and v1 report.

“Independent visual QA” means a fresh-eyes subagent that did not implement the
v2 revision. It must review the full-page PNG for five-second hierarchy,
30-second narrative flow, approximate one- and two-meter readability, grayscale
discrimination, text clipping, awkward wrapping, accidental overlap, arrow
crossings, color balance, and template obstruction. Its checklist and result
must be reproduced in `poster_visual_analysis.md`.
