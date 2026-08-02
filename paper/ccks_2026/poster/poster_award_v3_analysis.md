# SARGE CCKS 2026 Award Poster — Redesign and Validation Record

## Outcome

The English CCKS 2026 poster was rebuilt as a new, reproducible award-oriented
version without overwriting the prior v2 deliverables. The final poster is a
single editable PowerPoint slide at 88.90 × 109.22 cm, with matching one-page
PDF and 150 dpi PNG exports.

The redesign replaces the previous seven equal-weight cards with a four-zone
progressive-disclosure narrative:

1. a full-width take-home claim;
2. a 40/60 problem–method hero;
3. one continuous three-part evidence band;
4. a 58/42 ExactRec diagnostic and contribution/boundary band.

The research body is deliberately compact. Automated sampling reports 103 of
120 body-grid cells materially occupied (85.8%), with no full-width vertical
gap larger than 0.35 inches.

## Authoritative Inputs

- paper: `paper/SARGE_CCKS2026.pdf`;
- conference template:
  `paper/ccks_2026/poster/template/CCKS2026-poster参考模板.pptx`;
- editable baseline:
  `paper/ccks_2026/poster/SARGE_CCKS2026_poster_en_revised_v2.pptx`;
- baseline render:
  `paper/ccks_2026/poster/SARGE_CCKS2026_poster_en_revised_v2.png`;
- existing visual-language reference:
  `paper/ccks_2026/poster/assets/SARGE_CCKS2026_poster_reference.png`;
- QR asset: `paper/ccks_2026/poster/assets/github_repository_qr.png`.

The paper PDF was treated as authoritative when summaries differed. In
particular, the three-seed mean uses seeds 13, 17, and 42. No reinforcement-
learning or curriculum mechanism was added: the method shown is the paper's
contract-centered event-table generation with answer-token SFT, greedy
decoding, schema checking/normalization, and fixed-slot output.

## Poster-Award Design Research

The redesign uses patterns observed in award-winning or officially recognized
research posters:

- the CCKS 2026 Poster & Demo page states that Best Poster is selected through
  on-site attendee voting, favoring an immediately scannable public-vote
  hierarchy;
- the ESWC 2024 Best Poster uses an asymmetric portrait composition and lets a
  concrete technical example carry the explanation;
- IEEE VIS Best Posters use one dominant technical visual, strong typographic
  hierarchy, and an obvious resource path;
- the ICT.OPEN public-vote winner uses a dominant system diagram followed by
  compact evidence modules;
- the MIT poster guide recommends claim-led headings, readable graphics, and
  a short visual path rather than a paper-page layout.

Sources:

- https://sigkg.cn/ccks2026/poster-demo-%E5%BE%81%E9%9B%86/
- https://2024.eswc-conferences.org/awards/
- https://www.lassila.org/publications/2024/HartigEtAl_SPARQLCDTs_Poster2024.pdf
- https://www.ieeevis.org/year/2026/info/history/best-paper-awards/
- https://ieeevis.b-cdn.net/vis_2024/posters/v-vis-posters-1068.pdf
- https://ieeevis.b-cdn.net/vis_2023/posters/v-vis-posters-1028.pdf
- https://research.vu.nl/en/publications/knowledge-driven-data-exchange-and-validation-for-smart-buildings/
- https://biology.mit.edu/wp-content/uploads/2017/12/Outreach_Effective_Posters.pdf

## Diagnosis of v2

The v2 poster was scientifically careful and structurally complete, but its
seven equal cards distributed attention too evenly. Section headings were
mostly 32 pt, body text was commonly 18–20 pt, and several essential caveats
were 16 pt. At full-poster scale, the method, strongest result, and limitation
competed with secondary detail. The repeated rounded-card chrome also made the
page read like a dashboard rather than a single research argument.

The v3 redesign therefore removes only `S1_GROUP` through `S7_GROUP`, retains
the conference artwork/header/footer, and reconstructs the body with native
PowerPoint objects named `AW_*`.

## Independent ImageGen Exploration

A dedicated no-history subagent independently inspected the paper, approved
design specification, conference template, v2 render, and visual-language
reference. It wrote the complete production prompt to:

`paper/ccks_2026/poster/SARGE_CCKS2026_poster_award_v3_imagegen_prompt.md`

It generated a text-bearing composition reference and saved the adopted image
to:

`paper/ccks_2026/poster/SARGE_CCKS2026_poster_award_v3_visual_reference.png`

The adopted image was normalized to 1400 × 1720 pixels (35:43). One targeted
revision was attempted solely to correct canvas proportion; it incorrectly
returned a landscape image and was rejected. The generated QR and fine text
were explicitly treated as unreliable placeholders.

Two useful ImageGen ideas were translated into editable native objects:

- the evidence modules are tied together by a single
  `THREE PROOFS, ONE HONEST STORY` band;
- the method flow uses simple PowerPoint-native icons and a visibly structured
  fixed-slot table endpoint.

No generated bitmap is embedded in the final PPTX, and no generated scientific
wording was copied without checking it against the paper and contract.

## Final Information Architecture

### Header and take-home

- 60 pt three-line title, with protected CCKS logo clearance;
- 26 pt author line and 18 pt affiliations;
- 31 pt result-led take-home sentence in the existing navy band.

### Problem–method hero

- left: two same-type equity-pledge records and explicit `WRONG ×` versus
  `CORRECT ✓` row assembly;
- right: one connected five-stage method route from inputs to fixed-slot table;
- output contract and table endpoint receive teal emphasis;
- supporting alignment and evaluation labels remain inside the same method
  region rather than becoming additional cards.

### Evidence band

- overall F1: `85.6 ± 0.4` and `78.3 ± 0.4`;
- multi-event robustness: `81.7 F1(M.)`, `7.5 S–M Gap`, with EPAL
  `76.6 · 13.1`;
- supervised alignment: `24.8 → 86.0` and `3.3 → 78.0`;
- the DuEE-Fin and seed/inference-path qualifications remain directly beneath
  the associated claims.

### Diagnostic and boundary

- two native dumbbell comparisons show F1 versus ExactRec;
- `Δrecord 29.5` and `Δrecord 35.1` are explicit;
- the explanation states that the gap also includes missing, extra, or wrong
  values and event-count errors;
- the final coral box states that SARGE does not solve record binding
  completely.

## Typography, Color, and Whitespace

- title: 60 pt;
- main claim headings: 32–39 pt;
- primary metrics: 44 pt;
- ordinary body and diagram labels: at least 24 pt;
- captions: at least 22 pt;
- only named qualifiers use 18–20 pt;
- no shrink-to-fit is used.

Navy/blue establishes structure, teal marks SARGE and positive endpoints,
amber marks comparison/no-SFT starts, violet marks ExactRec gaps, and coral is
reserved for wrong row assembly and the remaining boundary. Words, symbols,
position, and line style support the color encoding in grayscale.

Whitespace was treated as controlled gutter space rather than a decorative
feature. The evidence band was shortened after the first render exposed a
vacant lower half; the released height was reassigned to the diagnostic and
boundary band. Large single-line callouts were then split into formula,
explanation, boundary label, and next-step caption to avoid fake visual fill.

## Automated Verification

The dedicated validator checks source facts before every output check, then
verifies:

- one 88.90 × 109.22 cm slide;
- unchanged protected footer shapes and unchanged background/QR media;
- all required names, values, qualifications, URL, and email;
- absence of `SOTA`, false DuEE-Fin superiority, and complete-binding claims;
- explicit font sizes and no shrink-to-fit;
- 85.8% sampled body-grid occupancy;
- no full-width unexplained gap deeper than 0.48 inches;
- no full-page raster;
- one-page 2520 × 3096 pt PDF with five embedded font subsets;
- 5250 × 6451 px review PNG;
- rendered QR decoding to `https://github.com/emmmdty/SARGE`.

Latest validator result:

```text
PASS paper: 9 metrics
PASS qr_asset: 370x370
PASS v2: 161 recursive shapes
PASS protected: 6 shape signatures
PASS pptx: 140 shapes
PASS density: 103/120=0.858; max gaps x=0.00 in, y=0.35 in
PASS pdf: 2520x3096 pt, 5 fonts
PASS png: 5250x6451, QR=https://github.com/emmmdty/SARGE
overall_pass: true
```

A separate clean rebuild to `/tmp` reproduced one slide with the same 140
recursive shapes, identical protected footer signatures, identical background
and QR media, and identical extracted slide text. Its PDF and PNG also matched
the required page count and raster geometry. MarkItDown extraction from the
delivered PPTX and PDF found every required research token; the extracted text
records contained 3,096 and 3,092 characters, respectively.

## Visual QA and Remaining Print Checks

The full render, hero crop, evidence crop, bottom crop, grayscale render, 25%
render, and 12.5% render were inspected. The title, take-home sentence, method
heading, primary metrics, and ExactRec gap remain visible in the reduced view.
The color-to-grayscale conversion preserves the reading order and the explicit
`×`, `✓`, labels, and endpoint values prevent color-only interpretation.

A fresh no-history visual reviewer returned `APPROVED` with no blocking
issues. It confirmed that the five-second and 30-second reading paths work,
that the method behaves as one connected dominant visual, and that the body has
no large vacant band. Two of its refinements were applied and revalidated:

- the EPAL comparison text was darkened for grayscale contrast;
- the `Δrecord 29.5` and `Δrecord 35.1` badges were enlarged from 24 pt to
  28 pt to move the ExactRec gap earlier in the five-second scan.

The reviewer considered the remaining lower callout padding non-blocking. It
was retained because the formula, caveat, limitation, and next-step lines need
clear separation at physical poster size, and reducing the boxes would create
an unexplained lower-body gap rather than meaningful density.

Before physical printing, confirm the print vendor's required bleed, embedded-
font policy, and preferred PDF standard, and scan the QR from a paper proof at
the intended viewing distance. These print-vendor checks cannot be completed
from the digital artifact alone.

## Rebuild and Validate

```bash
/home/tjk/.codex/venvs/codex-tools/bin/python \
  paper/ccks_2026/poster/tools/build_sarge_poster_award.py

/home/tjk/.codex/venvs/codex-tools/bin/python \
  /home/tjk/.claude/skills/pptx/scripts/office/soffice.py \
  --headless --convert-to pdf --outdir paper/ccks_2026/poster \
  paper/ccks_2026/poster/SARGE_CCKS2026_poster_en_award_v3.pptx

pdftoppm -png -r 150 -singlefile \
  paper/ccks_2026/poster/SARGE_CCKS2026_poster_en_award_v3.pdf \
  paper/ccks_2026/poster/SARGE_CCKS2026_poster_en_award_v3

/home/tjk/.codex/venvs/codex-tools/bin/python \
  paper/ccks_2026/poster/tools/validate_sarge_poster_award.py --all
```
