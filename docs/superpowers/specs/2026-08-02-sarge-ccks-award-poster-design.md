# SARGE CCKS 2026 Award-Oriented English Poster Design

## Objective

Redesign the latest English poster,
`paper/ccks_2026/poster/SARGE_CCKS2026_poster_en_revised_v2.pptx`, for the
CCKS 2026 on-site Best Poster vote. The poster must communicate the problem,
SARGE's event-table formulation, the strongest evidence, and the remaining
record-assembly limitation within about 30 seconds while remaining useful for
a three-minute technical discussion.

The approved direction is **award-first progressive disclosure**. It may
remove repeated explanations and secondary details from the current seven-card
layout, but it must retain every qualification needed to avoid a misleading
research claim.

## Source of Truth

The implementation must use these local sources:

- paper: `paper/SARGE_CCKS2026.pdf`;
- editable and visual baseline:
  `paper/ccks_2026/poster/SARGE_CCKS2026_poster_en_revised_v2.pptx`;
- baseline render:
  `paper/ccks_2026/poster/SARGE_CCKS2026_poster_en_revised_v2.png`;
- conference template:
  `paper/ccks_2026/poster/template/CCKS2026-poster参考模板.pptx`;
- QR asset: `paper/ccks_2026/poster/assets/github_repository_qr.png`;
- verified numerical record and caveats:
  `paper/ccks_2026/poster/poster_revision_report.md`.

The paper PDF is authoritative when any repository summary conflicts with it.
In particular, the three-seed means use seeds 13, 17, and 42.

## Conference and Reference Findings

The CCKS 2026 Poster & Demo session will select a Best Poster through on-site
attendee voting. The official poster template in the repository defines an
88.90 x 109.22 cm portrait canvas with protected conference branding at the
top and bottom.

The design adapts the following evidence-backed patterns:

- the ESWC 2024 Best Poster uses a portrait-native, asymmetric modular layout
  and lets concrete technical examples act as visuals;
- the IEEE VIS 2024 and 2023 Best Posters use one dominant visual anchor,
  extremely clear hierarchy, large typography, and a prominent resource path;
- the ICT.OPEN 2026 Public Best Poster uses one dominant system diagram and
  compact, high-contrast evidence regions for a public-vote setting;
- poster-design guidance consistently favors claim-led headings, readable
  graphics, and progressive detail over paper-section headings and prose.

References:

- https://sigkg.cn/ccks2026/poster-demo-%E5%BE%81%E9%9B%86/
- https://2024.eswc-conferences.org/awards/
- https://www.lassila.org/publications/2024/HartigEtAl_SPARQLCDTs_Poster2024.pdf
- https://www.ieeevis.org/year/2026/info/history/best-paper-awards/
- https://ieeevis.b-cdn.net/vis_2024/posters/v-vis-posters-1068.pdf
- https://ieeevis.b-cdn.net/vis_2023/posters/v-vis-posters-1028.pdf
- https://research.vu.nl/en/publications/knowledge-driven-data-exchange-and-validation-for-smart-buildings/
- https://biology.mit.edu/wp-content/uploads/2017/12/Outreach_Effective_Posters.pdf

## Non-Negotiable Invariants

The award-oriented poster must preserve:

- the 88.90 x 109.22 cm portrait page;
- the conference background, CCKS logo, top illustration, bottom wave artwork,
  and complete conference text;
- title wording, author order, affiliations, corresponding-author marker,
  email, repository URL, QR target, and hyperlinks;
- the verified values `85.6 ± 0.4`, `78.3 ± 0.4`, `81.7`, `7.5`, `76.6`,
  `13.1`, `24.8 → 86.0`, `3.3 → 78.0`, `56.1`, `43.3`, `29.5`, and `35.1`;
- the qualification that DuEE-Fin remains below SEELE at aggregate F1;
- the qualification that the no-SFT comparisons use seed 13 and the reported
  inference paths differ;
- the qualification that `Δrecord` is not a pure binding-error measure;
- the boundary that SARGE does not completely solve record binding;
- editable native PowerPoint text, shapes, connectors, and simple charts.

The generated image is a composition reference only. It must not be embedded
as a full-page raster and must not become a source of scientific wording or
data.

## Density and Whitespace Constraint

The poster must not contain large unused body regions. Approximately 82–88%
of the usable research-body area should be occupied by meaningful figures,
text, charts, or compact supporting backgrounds. Whitespace should appear as
controlled margins and breathing room, not as vacant panels.

- page-side body margin: approximately 2.8 cm;
- major inter-region gutters: 0.8–1.0 cm;
- internal padding: 0.6–0.9 cm;
- no unexplained blank body region deeper than about 1.2 cm;
- evidence and diagnostic bands use the full available width;
- content must not be enlarged merely to fill space, and repeated prose must
  not be reintroduced as filler.

This constraint deliberately rejects both the current card-grid clutter and an
extreme minimalist or billboard-only layout.

## Visual Architecture

### 1. Conference Header and Take-Home Band

Keep the existing header geometry and conference-logo clearance. Increase the
paper title to approximately 60–64 pt if it fits without crossing the protected
logo area. Authors remain approximately 26–28 pt and affiliations approximately
18–20 pt.

Retain the dark take-home band but replace its body copy with one result-led
sentence at approximately 30–34 pt:

> SARGE turns a closed schema into an event-table contract, reaching 85.6 F1
> on ChFinAnn with strong multi-event robustness; ExactRec reveals the
> remaining row-assembly gap.

The wording may receive a line-break-only adjustment during layout.

### 2. Hero Row: Problem and Method

Use an asymmetric 40/60 split spanning the full research width. The left block
explains the core problem; the right block is the dominant research visual.

#### Problem block

Claim heading:

> Correct values can still form the wrong rows

Use the existing two-record equity-pledge example, simplified to two compact
source-record strips and a direct red-versus-green comparison:

- `15M | CITIC | 05-20 → 05-19`
- `8M | Guotai Junan | 06-05 → 06-04`

The wrong side cross-binds the pledgees or end dates and uses both the word
`WRONG` and `×`. The correct side uses `CORRECT` and `✓`. Color must not be the
only carrier of meaning.

Caption:

> Shared arguments hide row identity; private values must stay bound together.

#### Method block

Claim heading:

> SARGE generates one schema-valid event table

Build one continuous left-to-right flow with five visually distinct stages:

1. **Inputs** — `Document D`, `Closed schema S`, and a compact note for optional
   cues `C_K(D), P_D`.
2. **Output contract** — licensed event types and roles, copy source values,
   one event per row.
3. **Tuned 4B LLM** — answer-token SFT and greedy decoding.
4. **Schema check** — filter invalid labels, drop empty fields, normalize role
   order.
5. **Fixed-slot table** — a clearly visible two-row event table as the endpoint.

The output contract and fixed-slot table receive the strongest visual emphasis.
Evaluation metrics appear as a compact endpoint annotation rather than a sixth
equal-size process card.

### 3. Full-Width Evidence Band

Use one continuous band divided into three aligned evidence modules with small
gaps and shared baselines. Do not use three disconnected dashboard cards.

#### Competitive overall

- `85.6 ± 0.4` — ChFinAnn F1;
- `78.3 ± 0.4` — DuEE-Fin F1;
- note: `ChFinAnn is numerically above the listed baselines; DuEE-Fin remains below SEELE (80.8).`

#### Stronger multi-event robustness

- SARGE 4B three-seed mean: `81.7 F1(M.)`, `7.5 S–M Gap`;
- EPAL reference: `76.6 F1(M.)`, `13.1 S–M Gap`;
- use a direct comparison graphic rather than a table with repeated borders.

#### Alignment drives the gain

- ChFinAnn: `24.8 → 86.0`;
- DuEE-Fin: `3.3 → 78.0`;
- note: `Same Qwen3-4B backbone, seed 13; reported inference paths differ.`

### 4. Diagnostic and Boundary Band

Use an approximately 58/42 split.

The left side uses two native dumbbell or paired-point comparisons:

- ChFinAnn: `F1 85.6 → ExactRec 56.1`, `Δrecord 29.5`;
- DuEE-Fin: `F1 78.3 → ExactRec 43.3`, `Δrecord 35.1`.

Use the heading:

> Role recovery is not exact row assembly

Required explanation:

> Δrecord = F1 − ExactRec; it also includes missing, extra, or wrong values and
> event-count errors.

The right side contains three terse contributions:

- **Reformulation** — closed-schema DEE as event-table generation;
- **Unified interface** — generate, check, normalize, and evaluate fixed-slot
  rows;
- **Diagnostic** — ExactRec exposes row-level errors hidden by role F1.

Finish with a high-contrast but restrained boundary box:

> Remaining boundary: SARGE does not solve record binding completely.

### 5. Footer

Preserve the conference text, QR code, `Paper & code`, repository URL, email,
and native hyperlinks. The QR must remain machine-decodable after rendering.

## Typography and Color

Target sizes:

- paper title: 60–64 pt;
- section claim headings: 34–40 pt;
- take-home sentence: 30–34 pt;
- primary numbers: 44–58 pt;
- ordinary body and figure labels: 24–28 pt;
- captions: 22–24 pt;
- seed, path, comparison, and source qualifiers: 18–20 pt;
- conference footer text: preserve the template's 48 pt formatting.

Use Arial for new English content to match the existing poster. Preserve the
template font for conference text. Use no text shrink-to-fit.

Color roles:

- navy/blue: structure and primary results;
- teal: SARGE, positive outcome, and method route;
- amber: baselines and no-SFT starting points;
- violet: ExactRec and `Δrecord`;
- coral/red: wrong assembly and the remaining boundary;
- pale tints: compact region grouping without heavy outlines.

Use labels, symbols, line styles, and position in addition to color. Avoid
shadows, decorative gradients, stock imagery, and repeated rounded-card chrome.

## Imagegen Isolation and Deliverables

The imagegen work must be executed by a dedicated subagent with no inherited
conversation history. That subagent must independently inspect the paper,
template reference, v2 render, and this approved spec; read the imagegen skill;
write its own detailed production prompt; and use the built-in image generation
tool.

The subagent must generate one portrait, text-bearing composition reference
that preserves the CCKS header/footer concept and uses the exact major research
anchors. It must save:

- its complete prompt to
  `paper/ccks_2026/poster/SARGE_CCKS2026_poster_award_v3_imagegen_prompt.md`;
- the selected output to
  `paper/ccks_2026/poster/SARGE_CCKS2026_poster_award_v3_visual_reference.png`.

The generated image must be inspected for hierarchy, layout density, scientific
drift, and text errors. A single targeted imagegen revision is allowed if the
first result materially violates the approved architecture. Generated text is
never copied into the final PPTX without checking it against this spec and the
paper.

## Implementation Strategy

Preserve all current deliverables. Create a new reproducible award-poster build
path using the repository's existing Python/PPTX conventions. Use the verified
v2 file as the starting point so the conference background, header, footer,
QR, and hyperlinks are preserved. Replace the seven body groups and update the
take-home copy with newly authored native PowerPoint objects.

Expected new files:

- `paper/ccks_2026/poster/tools/build_sarge_poster_award.py`;
- `paper/ccks_2026/poster/tools/validate_sarge_poster_award.py`;
- `paper/ccks_2026/poster/SARGE_CCKS2026_poster_en_award_v3.pptx`;
- `paper/ccks_2026/poster/SARGE_CCKS2026_poster_en_award_v3.pdf`;
- `paper/ccks_2026/poster/SARGE_CCKS2026_poster_en_award_v3.png`;
- the imagegen prompt and visual reference listed above;
- `paper/ccks_2026/poster/poster_award_v3_analysis.md`.

The build is local and CPU-only. No GPU work is required.

## Validation and Acceptance Criteria

The redesign is complete when all of the following pass:

- one portrait slide at exactly 88.90 x 109.22 cm;
- unchanged conference background and protected header/footer elements;
- no modification or overwrite of existing v2 or user-owned files;
- all required values, claim boundaries, author details, and links present;
- no `SOTA`, `state-of-the-art`, or false DuEE-Fin superiority claim;
- body occupancy consistent with the 82–88% density target and no unexplained
  large blank body region;
- ordinary body and figure labels at least 24 pt, with only named qualifiers at
  18–20 pt;
- all research content editable and no full-page raster artwork in the PPTX;
- no text clipping, shape overflow, accidental overlap, or connector crossing;
- method is the dominant body visual and the evidence band reads as one
  continuous sequence;
- title, take-home, method, `85.6`, `78.3`, `81.7`, and the ExactRec gap are
  visible in a five-second scan;
- the problem, method, evidence, and boundary are understandable within about
  30 seconds;
- PDF is one page at 2520 x 3096 pt with embedded fonts;
- 150 dpi PNG is approximately 5250 x 6450 px;
- rendered QR decodes to `https://github.com/emmmdty/SARGE`;
- content extraction finds no placeholder or imagegen-corrupted text;
- grayscale and reduced-scale reviews retain meaning;
- an independent fresh-eyes visual reviewer reports no unresolved major issue;
- at least one fix-and-reverify cycle is completed before delivery.

