# Poster Visual Analysis and Refinement

## 1. Scope and source constraints

This refinement is a visual-only second pass over
`SARGE_CCKS2026_poster_en_revised.pptx`. The paper, the verified first revision,
the conference template, and the original poster remain the factual and visual
sources of truth. No web source or generated image was used as a research
source.

The approved direction was **hero method diagram + evidence band**. The
research wording, numerical values, qualifications, author block, conference
template, URL, QR code, email, and hyperlinks were preserved. The new version
is delivered separately and does not overwrite the original or first revised
files.

## 2. Visual diagnosis of the first revision

The first revision already provided a strong paper title, a concise take-home
band, accurate numerical evidence, numbered sections, and a correct
problem-to-boundary reading order. Its remaining visual limitations were:

- repeated rounded borders made the research body read like a dashboard;
- seven sections had nearly equal visual weight, so the method did not act as
  the main research visual;
- Sections 3–5 appeared as three separate result cards rather than one evidence
  sequence;
- the six-node method diagram was correct but visually resembled a form;
- qualifications were distributed across unrelated card bottoms;
- blue, teal, orange, purple, and red occupied similar visual area, weakening
  the primary blue/teal story.

The redesign therefore did not add content. It changed visual hierarchy,
spacing, border weight, and emphasis so that the intended scan becomes:

`Problem → Method → Main results → Multi-event robustness → Alignment → ExactRec / boundary`

## 3. External design references

Only layout principles were borrowed; no third-party artwork, wording, data, or
branding was copied.

- [IEEE VIS award history](https://www.ieeevis.org/year/2026/info/history/best-paper-awards/)
  identifies the official Best Poster selections used to choose examples.
- [IEEE VIS 2024 Best Poster — Transformer Explainer](https://ieeevis.b-cdn.net/vis_2024/posters/v-vis-posters-1068.pdf)
  demonstrates a single obvious visual anchor, direct annotation, and
  restrained supporting text.
- [IEEE VIS 2023 Best Poster — ManimML](https://ieeevis.b-cdn.net/vis_2023/posters/v-vis-posters-1028.pdf)
  demonstrates strong narrative flow and visual grouping without giving every
  element equal weight.
- [Georgia Tech report on the ManimML poster award](https://www.cc.gatech.edu/news/machine-learning-animation-tool-takes-best-poster-prize-visualization-conference)
  confirms that it was selected best among 49 posters.
- [MIT — Making a Great Poster](https://biology.mit.edu/wp-content/uploads/2017/12/Outreach_Effective_Posters.pdf)
  emphasizes a clear message, readable hierarchy, and removing nonessential
  detail.
- [ACM CHI 2026 poster guidance](https://chi2026.acm.org/authors/posters/)
  emphasizes communicating the contribution clearly in a short poster
  interaction.

The common design principles applied here were:

1. one obvious message and one dominant research visual;
2. large, self-explanatory graphics with concise supporting prose;
3. a visible left-to-right, top-to-bottom narrative;
4. strong contrast between primary evidence and qualifications;
5. fewer decorative containers and more conceptual whitespace;
6. direct labels instead of legends or repeated numeric decoration.

## 4. Imagegen reference

The generated reference is:

`/home/tjk/myProjects/masterProjects/DEE/.worktrees/SARGE-poster/paper/ccks_2026/poster/SARGE_CCKS2026_poster_en_visual_reference.png`

It was produced in the built-in image-edit mode using the first revised poster
PNG as the only reference image. The prompt requested a portrait academic
poster composition that preserved the CCKS header/footer and page proportions,
made the six-step SARGE method the dominant visual, aligned Sections 3–5 as a
continuous evidence band, reduced nested card chrome, and used abstract
placeholder copy. It allowed only the exact major anchors `SARGE`, `85.6`,
`78.3`, `81.7`, and `ExactRec`, and explicitly prohibited new claims, data,
logos, illustrations, or photography.

The generated PNG is a composition reference only. It is not embedded in the
PowerPoint, and generated text was not used in the final poster.

Prompt specification used for the edit:

> Refine the supplied portrait academic poster as a high-end visual-composition
> reference. Preserve the CCKS conference header, footer, logo clearance, page
> proportions, and the problem → method → evidence → boundary story. Make the
> six-step SARGE method the dominant research visual and align the three middle
> result sections as one continuous evidence band. Reduce nested rounded cards,
> use more whitespace and direct labels, and keep blue/teal dominant with
> orange, purple, and red used sparingly. Use abstract placeholder text for
> small copy. Keep only the exact readable anchors SARGE, 85.6, 78.3, 81.7, and
> ExactRec. Do not introduce new claims, data, logos, illustrations, or
> photographic imagery.

## 5. Implemented visual changes

### Header and take-home

- Preserved byte-for-byte/object-for-object from the verified first revision.
- Preserved title, authors, affiliations, logo clearance, take-home wording,
  conference footer, public URL, QR code, email, and hyperlink targets.

### Section 1 — problem

- Kept the two-record wrong-row/correct-row example and all wording.
- Removed the nonessential outlines around the shared/record-specific labels.
- Retained stronger red `WRONG / ×` and green `CORRECT / ✓` containers so the
  distinction remains legible in grayscale by words and symbols.

### Section 2 — method hero

- Retained all six verified steps and the snake-flow connectors.
- Promoted `Output contract` and `Fixed-slot table` as the central pair with
  stronger blue/teal treatment.
- Reduced the fill and border prominence of Inputs, LLM, normalization, and
  evaluation.
- Enlarged the step badges and strengthened the blue arrow route.
- Preserved `Optional slot prior P_D`, `Surface candidates C_K(D)`, and their
  non-decisive status.

### Sections 3–5 — continuous evidence band

- Aligned all major numeric anchors to `y = 58.40 cm`.
- Standardized internal side padding to `0.80 cm`.
- Used matching pale anchor zones so the three sections read as a sequence.
- Kept `85.6 ± 0.4`, `78.3 ± 0.4`, `81.7`, and `7.5` as the first visual
  evidence.
- Promoted the three-seed SARGE 4B row in Section 4 while keeping EPAL and
  SARGE 1.7B as compact, explicitly qualified comparisons.
- Aligned the two no-SFT transitions in Section 5 and kept the seed-13 and
  inference-path qualifications verbatim.

### Sections 6–7 — diagnosis and boundary

- Reduced table chrome in the ExactRec matrix while retaining direct labels.
- Kept F1 blue/teal and ExactRec/Δrecord purple.
- Lowered the visual weight of the three contribution statements.
- Increased the prominence of the pale-red boundary box without using a large
  saturated red area.
- Preserved the full statement that Δrecord is not a pure binding-error
  estimate.

### Card chrome and color

- Softened all seven outer section borders to `#E8EDF5`, 0.85 pt.
- Reduced visible internal strokes from 27 to 16, a 40.7% reduction.
- Reserved saturated blue/teal for the method route and primary numerical
  evidence; orange, purple, and red remain semantically targeted.
- Added no shadows, gradients, third-party images, or rasterized research
  regions.

## 6. Before/after hierarchy

| Viewing task | First revision | Visual refinement v2 |
|---|---|---|
| Five-second read | Title and take-home were clear; body sections competed | Title → take-home → method → 85.6 / 78.3 / 81.7 / 7.5 |
| Thirty-second scan | Correct order, but visually segmented | Continuous problem → method → evidence → diagnosis/boundary path |
| Method prominence | Six equal form-like nodes | Central Output contract / Fixed-slot table pair with one strong route |
| Results comparison | Three independent cards | One aligned evidence band across Sections 3–5 |
| Qualification layer | Distributed among card bottoms | Deliberately secondary to metric anchors |
| Container density | 27 visible internal strokes | 16 visible internal strokes |

## 7. Structural and factual QA

| Check | Result |
|---|---|
| Normalized v1/v2 research text | PASS — no text or shape-name differences |
| Required SEELE, Doc2Event, seed, inference-path, and Δrecord qualifications | PASS |
| Forbidden SOTA / both-datasets / binding-rate wording | PASS — no hits |
| Page | PASS — one portrait slide, 88.90 × 109.22 cm |
| Conference footer text and geometry | PASS — preserved at 48 pt |
| Background | PASS — identical JPEG SHA-256 `75c64d300ba3826ee6da34bb658e081c35ce01724ed1570e9564ebd0f185ded7` |
| Template/header/take-home/footer object XML | PASS — signatures identical to v1 |
| Object inventory | PASS — 21 slide-level / 161 recursive objects |
| Object types | 50 auto shapes, 91 text boxes, 12 connectors, 1 picture, 7 groups |
| Section geometry and regional naming | PASS |
| Object bounds | PASS — no recursive object out of slide bounds |
| Text autofit | PASS — all non-template text uses fixed size/no autofit |
| Minimum font size | PASS — 18 pt body; 16 pt permitted notes and visual subscripts only |
| Rasterization | PASS — only the existing editable QR picture shape is present |
| Background/image media parts | PASS — byte-identical to v1; reference mockup absent |
| Hyperlinks | PASS — URL/QR and `mailto:` targets preserved |
| PDF | PASS — one page, 2520 × 3096 pt |
| PDF font embedding | PASS — all exported fonts embedded |
| PNG | PASS — 5250 × 6451 px at the requested 150 dpi conversion |
| Isolated fresh render | PASS — freshly exported 150 dpi PNG is byte-identical to the delivered PNG |
| Rendered QR | PASS — decodes to `https://github.com/emmmdty/SARGE` |
| Original/v1 file integrity | PASS — all frozen SHA-256 values unchanged |

Linux/LibreOffice exported the PPTX fonts as embedded DejaVu Sans,
DejaVu Sans Bold, Liberation Sans, Liberation Sans Bold, and
Noto Sans CJK SC Regular-VKana. This is the same export-environment limitation
already documented for the first revision; author acceptance is still required
before print.

## 8. Independent visual QA

An independent fresh-eyes reviewer who did not implement v2 inspected the
full-page render, hero row, evidence band, diagnostic/footer row, grayscale
render, and approximate one-/two-meter proxy renders.

| Review item | Result |
|---|---|
| Five-second hierarchy | PASS — title → take-home → method → headline metrics is immediate |
| Thirty-second narrative | PASS — numbered sections preserve the intended problem-to-boundary flow |
| Approximate one-meter readability | PASS — body copy and diagrams remain usable |
| Approximate two-meter readability | PASS — title, headings, take-home, method structure, and key metrics remain legible; footnotes appropriately recede |
| Grayscale discrimination | WARN — orange/teal differences weaken, but labels, arrows, ×/✓ marks, and numbers preserve meaning |
| Text clipping and wrapping | PASS — no clipped body text or problematic wrapping |
| Overlap and arrow crossings | PASS — no overlap or arrow crossing text |
| Color balance | PASS — cohesive and restrained, with warm accents limited to contrast and boundary statements |
| CCKS template obstruction | PASS — header and footer remain unobstructed |
| Method dominance | PASS — established by area, placement, and the six-step route |
| Sections 3–5 evidence sequence | PASS — aggregate results → multi-event robustness → alignment evidence |

Blocking issues: **none**. Independent result: **APPROVED**.

## 9. Deliverables and hashes

| File | SHA-256 |
|---|---|
| `SARGE_CCKS2026_poster_en_visual_reference.png` | `02404e0fd2ab151ba4f8eec96ccab902d4e158ee233fdf78edb0235fdd0190fa` |
| `SARGE_CCKS2026_poster_en_revised_v2.pptx` | `fd5f35ac04884c6407106773cd64e17550f4aa6cc163fc475665de49b72350f8` |
| `SARGE_CCKS2026_poster_en_revised_v2.pdf` | `7ec3cc950a1ae41601d6f00f0469d8970979d1f53a23cb855c56a6b8c4ce0725` |
| `SARGE_CCKS2026_poster_en_revised_v2.png` | `381e236fb8f1a9de0cb79305b450aa081ab9cbebf1e9ed7d4e06a06111e9eb70` |

## 10. Environment and reproducibility

- Worktree: `/home/tjk/myProjects/masterProjects/DEE/.worktrees/SARGE-poster`
- Canonical local repository: `/home/tjk/myProjects/masterProjects/DEE/SARGE`
- Canonical server repository: `/data/TJK/DEE/SARGE`
- Shared document/media Python:
  `/home/tjk/.codex/venvs/codex-tools/bin/python`
- Project local Python:
  `/home/tjk/miniconda3/envs/feg-dev-py310/bin/python`
- Server Python: `/data/TJK/envs/sarge_vllm_full/bin/python`
- PPTX/PDF export: LibreOffice in an isolated Linux user profile
- PNG rendering and PDF inspection: Poppler

## 11. Author confirmation still required

1. Confirm that `https://github.com/emmmdty/SARGE` is the final public
   paper/code URL and that the current QR is approved for printing.
2. Confirm that `CITIC` and `Guotai Junan` should remain the displayed English
   short forms.
3. Confirm acceptance of the documented Linux/LibreOffice font substitutions,
   or perform the final print export in Microsoft PowerPoint with Arial and
   Microsoft YaHei available.
