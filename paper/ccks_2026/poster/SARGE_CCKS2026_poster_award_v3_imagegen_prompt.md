# SARGE CCKS 2026 Award Poster — ImageGen Record

## Use case and execution mode

- **Use case:** `infographic-diagram`
- **Intent:** generate a new image using local images only as references; no image is an edit target in the adopted generation.
- **Asset type:** English academic conference poster composition reference for a large-format physical CCKS 2026 poster.
- **Execution mode:** default built-in ImageGen tool, default model, one project-bound asset. No CLI, API, explicit model selection, or remote GPU was used.
- **Target geometry:** 35:43 portrait. The selected built-in output was deterministically resampled to `1400 × 1720` pixels (exactly 35:43) with Pillow/LANCZOS because the built-in tool returned a narrower portrait canvas.

## Reference inputs and roles

1. `paper/ccks_2026/poster/template/CCKS2026-poster参考模板.pptx`, rendered read-only to `/tmp/sarge-template-render.M2oFfZ/template.png`: **conference-template reference** for the protected blue-purple header/footer, CCKS 2026 logo zone, campus illustration, bottom wave, and conference-information/QR concept.
2. `paper/ccks_2026/poster/SARGE_CCKS2026_poster_en_revised_v2.png`: **factual-content, typography, palette, and page-proportion reference**; explicitly not a layout template because its seven-card body grid was to be replaced.
3. `paper/ccks_2026/poster/assets/SARGE_CCKS2026_poster_reference.png`: **abstract visual-language reference** for clean vector-like diagrams, restrained icons, thin connectors, and compact spacing; its generic placeholder content was not used as scientific evidence.

The authoritative scientific sources were `paper/SARGE_CCKS2026.pdf` and `docs/superpowers/specs/2026-08-02-sarge-ccks-award-poster-design.md`. The method was constrained to contract-centered event-table generation, answer-token SFT, greedy decoding, schema checking/normalization, and fixed-slot tables. No reinforcement-learning or curriculum mechanism was introduced.

## Final adopted prompt (verbatim)

```text
Use case: infographic-diagram
Asset type: English academic conference poster composition reference for a large-format physical CCKS 2026 poster
Primary request: Generate a single polished, text-bearing, 35:43 portrait academic research poster for the paper “SARGE: Schema-Grounded Event-Table Generation for Chinese Financial Document-Level Event Extraction.” This is a visual composition reference, not a finished editable poster. It must feel award-oriented, modern, restrained, and scientifically trustworthy. Preserve the conference template’s branded top region and bottom conference-information/QR concept, but redesign the research body into a dense asymmetric progressive-disclosure composition instead of seven equal dashboard cards.

Input images:
- Image 1: conference-template reference. Preserve its blue-to-purple top and bottom branded bands, CCKS 2026 logo zone, campus illustration concept, bottom wave artwork, and overall portrait proportions. Do not copy the Chinese placeholder title or author text.
- Image 2: factual/content and palette reference. Preserve the real SARGE title, author identity, navy/teal/amber/violet/coral color logic, and verified research anchors, but do not preserve its seven-card body grid.
- Image 3: abstract composition/style reference. Use only its clean vector-like scientific diagram language, restrained icons, thin connectors, and compact spacing; do not copy placeholder bars or generic card arrangement.

Canvas and density:
- Exact visual intention: 35:43 portrait ratio, approximately 0.814 width-to-height.
- Use the full portrait canvas; show the entire poster, straight-on, with no perspective mockup, no room scene, no easel, no hands, no crop, and no outer frame.
- Keep the conference header about 18–20% of total height and the conference footer about 10–12%.
- Fill approximately 82–88% of the usable white research-body grid with meaningful content. Use small controlled outer margins, narrow gutters, and compact module padding. No large vacant panels or decorative empty space, but do not make the text chaotic.
- The body architecture must be unmistakably asymmetric and award-first: top take-home band; 40/60 problem-and-method hero; one full-width continuous evidence band; then a 58/42 diagnostic-and-boundary band.

Header and top branding:
- Use a deep blue-to-purple conference header with the CCKS 2026 logo large at upper right and the campus/architecture line-art at the lower right edge, following Image 1’s protected brand geometry.
- At upper left, render the following title prominently, verbatim, in bold white modern sans-serif, preferably no more than three lines:
“SARGE: Schema-Grounded Event-Table Generation for Chinese Financial Document-Level Event Extraction”
- Under the title, render this author line once, clearly:
“Jiakai Tong · Mengting Qin · Yongqi Hu · Xueyao Wan · Yue Zhao”
- Then two compact affiliation lines:
“School of Astronautics, Harbin Institute of Technology”
“Zhengzhou Advanced Research Institute, Harbin Institute of Technology”
- Do not let the title or authors intrude into the CCKS logo/campus zone.

Take-home band:
- Immediately below the header, place one strong full-width navy band with a compact teal label “TAKE-HOME MESSAGE”.
- Render this exact sentence in large, high-contrast white text:
“SARGE turns a closed schema into an event-table contract, reaching 85.6 F1 on ChFinAnn with strong multi-event robustness; ExactRec reveals the remaining row-assembly gap.”
- Make this sentence readable at a five-second glance.

Hero row, full research width:
LEFT 40% — problem / motivation:
- Claim heading, large and verbatim: “Correct values can still form the wrong rows”
- Use a concrete two-record equity-pledge visual, not generic clip art.
- Show two compact source-record strips:
“15M | CITIC | 05-20 → 05-19”
“8M | Guotai Junan | 06-05 → 06-04”
- Below, compare two small row groups with labels and explicit symbols:
“WRONG ×”
“15M | Guotai Junan | 05-20 → 06-04”
“8M | CITIC | 06-05 → 05-19”
and
“CORRECT ✓”
“15M | CITIC | 05-20 → 05-19”
“8M | Guotai Junan | 06-05 → 06-04”
- Use coral/red for WRONG and teal/green for CORRECT, plus words and symbols so meaning never depends on color alone.
- Add one concise caption:
“Shared arguments hide row identity; private values must stay bound together.”
- Make the wrong-versus-correct row assembly the dominant visual in this left block.

RIGHT 60% — dominant method diagram:
- Claim heading, large and verbatim: “SARGE generates one schema-valid event table”
- Build one continuous, strongly connected, left-to-right five-stage process visual. It may gently step or zigzag to stay legible, but it must read as one route, not five equal disconnected cards:
1. “INPUTS”
   “Document D”
   “Closed schema S”
   “Optional cues C_K(D), P_D”
2. “OUTPUT CONTRACT”
   “Licensed types + roles”
   “Copy source values”
   “One event per row”
3. “TUNED 4B LLM”
   “Answer-token SFT”
   “Greedy decoding”
4. “SCHEMA CHECK”
   “Filter invalid labels”
   “Drop empty fields”
   “Normalize role order”
5. “FIXED-SLOT TABLE”
   Show a clearly visible two-row endpoint table with header:
   “type | role 1 | role 2 | …”
   and two concise event rows beneath.
- Give OUTPUT CONTRACT and FIXED-SLOT TABLE the strongest visual emphasis using saturated blue/teal shapes and larger footprint. Connect all stages with clean arrows and one continuous path.
- Add a small endpoint annotation, not a sixth card:
“Evaluate: F1 · ExactRec · Δrecord”
- Important scientific constraint: do not show or mention reinforcement learning, hierarchical reinforcement, curriculum learning, CPF, RLD, RLR, RLM, chain-of-thought, or any staged training curriculum. SARGE here is contract-centered event-table generation with supervised answer-token fine-tuning, greedy decoding, schema checking/normalization, and fixed-slot tables.

Full-width evidence band:
- Below the hero, create one continuous horizontal evidence band divided into three aligned modules by subtle vertical separators and shared baselines. Do not draw three isolated rounded dashboard cards.
- Band heading: “THREE PROOFS, ONE HONEST STORY”
- Module 1 heading: “Competitive overall”
  Large numbers:
  “85.6 ± 0.4” with label “ChFinAnn F1”
  “78.3 ± 0.4” with label “DuEE-Fin F1”
  Compact qualification:
  “ChFinAnn is numerically above listed baselines.”
  “DuEE-Fin remains below SEELE (80.8).”
- Module 2 heading: “Stronger multi-event robustness”
  Use a direct paired-bar or paired-dot comparison, not a bordered table:
  “SARGE 4B: 81.7 F1(M.) · 7.5 S–M Gap”
  “EPAL: 76.6 F1(M.) · 13.1 S–M Gap”
  Visually emphasize higher F1(M.) and lower gap.
- Module 3 heading: “Alignment drives the gain”
  Use two bold before→after comparisons:
  “ChFinAnn 24.8 → 86.0”
  “DuEE-Fin 3.3 → 78.0”
  Compact qualification:
  “Same Qwen3-4B backbone, seed 13; reported inference paths differ.”
- Use blue/teal for SARGE outcomes and amber for references/no-SFT starts. Never claim that SARGE is best on DuEE-Fin overall F1. Never use “SOTA” or “state of the art.”

Bottom body band:
LEFT 58% — exact-record diagnostic:
- Heading, large and verbatim: “Role recovery is not exact row assembly”
- Show two clean horizontal paired-point/dumbbell comparisons:
  “ChFinAnn: F1 85.6 → ExactRec 56.1” and a prominent violet “Δrecord 29.5”
  “DuEE-Fin: F1 78.3 → ExactRec 43.3” and a prominent violet “Δrecord 35.1”
- Use visible endpoint labels and a violet connector/gap annotation.
- Render this exact explanation:
“Δrecord = F1 − ExactRec; it also includes missing, extra, or wrong values and event-count errors.”
- Do not describe Δrecord as a pure binding-error measure.

RIGHT 42% — contributions and limitation:
- Heading: “Contribution and remaining boundary”
- Use three terse stacked statements with small simple line icons or bold lead words:
“Reformulation — closed-schema DEE as event-table generation”
“Unified interface — generate, check, normalize, and evaluate fixed-slot rows”
“Diagnostic — ExactRec exposes row-level errors hidden by role F1”
- Finish with a high-contrast restrained coral outline box containing this exact sentence:
“Remaining boundary: SARGE does not solve record binding completely.”
- This limitation must be immediately visible, not hidden in tiny text.

Footer:
- Preserve Image 1’s deep blue-to-purple footer and flowing cyan wave motif.
- At lower left, place a crisp square QR-code concept/placeholder with label “Paper & code”, plus:
“github.com/emmmdty/SARGE”
“yue.zhao@hit.edu.cn”
- At lower center/right, render the conference identity as clearly as possible:
“China Conference on Knowledge Graph and Semantic Computing (CCKS 2026)”
“Xi’an · Aug 21–23, 2026”
- The QR is a visual placeholder concept only; do not invent a scannable destination other than the printed repository URL.

Style and typography:
- Modern flat vector-like academic infographic, restrained and credible, white research-body background, crisp sans-serif typography similar to Arial/Helvetica.
- Strong hierarchy suitable for a large physical poster: title largest; take-home sentence and method heading next; section headings clearly larger than body labels; primary numbers very large; ordinary body copy large enough to remain readable when the poster is viewed as a whole.
- Color roles: deep navy/blue for structure and primary results; teal for SARGE and positive outcomes; amber for baselines/no-SFT starts; violet for ExactRec and Δrecord; coral/red only for wrong assembly and the remaining boundary; pale tints for grouping.
- Prefer flat bands, open modules, thin separators, tables, arrows, and restrained rounded corners. Avoid repeated heavy card chrome.
- Preserve reading order from top to bottom and left to right. Align modules to a visible grid. Use small margins and tight, consistent gutters.
- Core text that must be especially clear: the full paper title; “TAKE-HOME MESSAGE”; “Correct values can still form the wrong rows”; “SARGE generates one schema-valid event table”; the five method-stage names; “85.6 ± 0.4”; “78.3 ± 0.4”; “81.7”; “7.5”; “24.8 → 86.0”; “3.3 → 78.0”; “ExactRec 56.1”; “ExactRec 43.3”; “Δrecord 29.5”; “Δrecord 35.1”; and the remaining-boundary sentence.

Constraints:
- English poster body only, except any unavoidable non-body branding detail inherited from the conference reference.
- Render all quoted strings verbatim, once, with no extra characters where possible.
- Scientific accuracy over decorative flourish.
- No invented metrics, rankings, datasets, mechanisms, architecture components, superiority claims, author names, institutions, conference claims, logos, or citations.
- No reinforcement learning, no hierarchical reinforcement, no curriculum chain, no CPF/RLD/RLR/RLM, no “record binding solved,” no “best DuEE-Fin,” no “SOTA.”
- No seven equally weighted cards, no symmetric dashboard, no dense paper-page imitation, no stock photos, no people, no 3D, no shadows, no glassmorphism, no decorative gradients inside the white body, no tiny unreadable paragraphs, no excessive whitespace, no giant empty regions, no cropped edges, no perspective, and no watermark.
- Output one single clean poster image only.
```

## Generation, revision, and selection notes

- **Initial generation:** the built-in tool returned `/home/tjk/.codex/generated_images/019fc21e-2afe-70d1-bdcb-f7c912d8c3e8/exec-2adb9c2f-1177-4394-969b-7d6720bcf640.png` at `1008 × 1560`. Its award-first hierarchy, body density, method dominance, continuous evidence band, diagnostic/boundary split, and visible scientific qualifications were accepted.
- **One targeted ImageGen revision:** attempted once because the first output was narrower than 35:43. The revision was instructed to change only the canvas proportion and spacing while preserving content. It returned `/home/tjk/.codex/generated_images/019fc21e-2afe-70d1-bdcb-f7c912d8c3e8/exec-9b3347aa-ee5e-4464-bcae-c0394d85f0a3.png` at `1484 × 1060`, incorrectly switching to landscape. It was rejected; no second ImageGen revision was made.
- **Final selection:** the initial portrait generation was selected and deterministically resampled with Pillow/LANCZOS to `1400 × 1720`, an exact 35:43 ratio. No text, color, layout element, scientific claim, or QR content was added or removed during this normalization.
- **Final workspace asset:** `paper/ccks_2026/poster/SARGE_CCKS2026_poster_award_v3_visual_reference.png`.

## Visual QA observations

Strengths:

- The title, take-home message, dominant five-stage method, three evidence modules, ExactRec diagnostic, and coral boundary box are visible in one scan.
- The problem/method hero is clearly asymmetric, the evidence reads as one band, and the body has controlled narrow gutters with no large vacant region.
- The visible claims preserve the DuEE-Fin qualification, the seed/path qualification, the non-pure interpretation of `Δrecord`, and the incomplete record-binding boundary.

Risks:

- Image-generated fine print and the QR pattern are composition placeholders and must not be treated as authoritative or machine-decodable.
- The exact 35:43 delivery required non-uniform deterministic resampling of the selected portrait output, so typography is slightly wider than the raw generation.
- The generated `C_K(D), P_D` typography is approximate at small size; any final editable poster must typeset it natively from the paper/spec.
