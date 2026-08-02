# SARGE CCKS 2026 Award Poster Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Produce a reproducible, editable, award-oriented English CCKS 2026 poster with an independently generated text-bearing imagegen reference, a denser four-zone layout, and verified PPTX/PDF/PNG deliverables.

**Architecture:** Preserve the verified v2 PPTX as the immutable source for the conference background, header/footer, QR, and hyperlinks. Add a small contract module, a dedicated award-poster builder, and a dedicated validator; the builder removes only the seven v2 research-body groups and replaces them with native `AW_*` PowerPoint objects. A no-history imagegen subagent independently creates the composition prompt and reference image before the editable poster is authored.

**Tech Stack:** Python 3.10+, `python-pptx`, Pillow, pypdf, zxing-cpp, LibreOffice, Poppler, built-in imagegen, shared media Python `/home/tjk/.codex/venvs/codex-tools/bin/python`.

---

## File Responsibilities

- `paper/ccks_2026/poster/tools/award_poster_contract.py` — immutable input/output paths, exact text/value requirements, protected shape names, body bounds, and density rules shared by the builder and validator.
- `paper/ccks_2026/poster/tools/build_sarge_poster_award.py` — reproducibly transforms the verified v2 PPTX into the editable award-oriented v3 PPTX.
- `paper/ccks_2026/poster/tools/validate_sarge_poster_award.py` — validates source facts, PPTX structure/content/fonts/density/links, PDF geometry/font embedding, PNG size, and rendered QR.
- `paper/ccks_2026/poster/SARGE_CCKS2026_poster_award_v3_imagegen_prompt.md` — the isolated imagegen subagent's complete production prompt and generation record.
- `paper/ccks_2026/poster/SARGE_CCKS2026_poster_award_v3_visual_reference.png` — text-bearing composition reference; never embedded as the poster body.
- `paper/ccks_2026/poster/SARGE_CCKS2026_poster_en_award_v3.pptx` — final editable poster.
- `paper/ccks_2026/poster/SARGE_CCKS2026_poster_en_award_v3.pdf` — final one-page print/export proof.
- `paper/ccks_2026/poster/SARGE_CCKS2026_poster_en_award_v3.png` — final 150 dpi review render.
- `paper/ccks_2026/poster/poster_award_v3_analysis.md` — research references, imagegen prompt/output record, before/after diagnosis, exact changes, automated evidence, fresh-eyes QA, and unresolved print confirmations.

Existing v2 files, the canonical poster builder/validator, and the two untracked user files are read-only inputs and must not be overwritten or committed.

### Task 1: Add the Award-Poster Contract and Failing Validator

**Files:**
- Create: `paper/ccks_2026/poster/tools/award_poster_contract.py`
- Create: `paper/ccks_2026/poster/tools/validate_sarge_poster_award.py`
- Read: `paper/ccks_2026/poster/tools/validate_poster.py`
- Read: `paper/ccks_2026/poster/poster_revision_report.md`
- Test: `paper/ccks_2026/poster/tools/validate_sarge_poster_award.py`

- [ ] **Step 1: Define one shared contract**

Create constants for:

```python
PAGE_CM = (88.90, 109.22)
BODY_BOUNDS_IN = (1.10, 9.65, 32.80, 28.15)  # x, y, w, h; ends at y=37.80
BODY_GRID = (12, 10)
DENSITY_CELL_RANGE = (0.82, 0.88)
MAX_UNEXPLAINED_GAP_IN = 0.48  # about 1.2 cm

PROTECTED_SHAPES = {
    "FTR_CONFERENCE_TEXT",
    "FTR_QR_FRAME",
    "FTR_QR_IMAGE",
    "FTR_LABEL",
    "FTR_URL",
    "FTR_EMAIL",
}
EDITABLE_HEADER_SHAPES = {
    "HDR_TITLE",
    "HDR_AUTHORS",
    "HDR_CORRESPONDING_SYMBOL",
    "HDR_AFFILIATIONS",
    "TAKEHOME_FRAME",
    "TAKEHOME_LABEL_BOX",
    "TAKEHOME_LABEL",
    "TAKEHOME_TEXT",
}
REMOVE_BODY_SHAPES = {f"S{i}_GROUP" for i in range(1, 8)}
```

Also define the exact v2/v3 paths, paper/QR paths, required research tokens,
forbidden claims, output filenames, and the approved take-home/problem/method/
evidence/diagnostic/boundary copy from the design spec.

- [ ] **Step 2: Record protected source signatures**

Implement helpers that read the v2 source and return stable signatures for the
slide background media plus each protected shape's text, geometry, rotation,
shape type, fill/line, hyperlink relationships, and picture media hash where
applicable. Header/title/author objects are checked for exact text but may change
geometry and font sizes within the protected logo-clearance area.

- [ ] **Step 3: Write the validator before the output exists**

Implement a CLI with `--pptx-only` and `--all` modes. At minimum it must check:

```python
def validate_source() -> None: ...
def validate_pptx() -> None: ...
def validate_pdf() -> None: ...
def validate_png_and_qr() -> None: ...
def validate_density(slide) -> None: ...
```

For density, divide `BODY_BOUNDS_IN` into a 12 x 10 grid. Count cells intersected
by meaningful `AW_*` text, diagram, metric, or chart objects while excluding
full-region backgrounds, divider-only shapes, and connector-only shapes. Require
82–88% occupied cells and separately reject an unexplained horizontal or vertical
content gap deeper than 0.48 inches. Report the occupied-cell count so the result
is auditable rather than subjective.

Font validation must recurse through groups, reject `normAutofit`, require
ordinary body/figure labels to be at least 24 pt, captions at least 22 pt, and
allow 18–20 pt only for an explicit qualifier/source/footer whitelist.

- [ ] **Step 4: Run the validator and verify the expected failure**

Run:

```bash
/home/tjk/.codex/venvs/codex-tools/bin/python \
  paper/ccks_2026/poster/tools/validate_sarge_poster_award.py --pptx-only
```

Expected: non-zero exit because
`SARGE_CCKS2026_poster_en_award_v3.pptx` does not exist; source-paper,
v2-signature, and QR-asset preflight checks should pass before that failure.

- [ ] **Step 5: Commit the contract and failing validator**

```bash
git add paper/ccks_2026/poster/tools/award_poster_contract.py \
  paper/ccks_2026/poster/tools/validate_sarge_poster_award.py
git commit -m "test(poster): define award poster contract"
```

### Task 2: Generate the Independent Imagegen Prompt and Text-Bearing Reference

**Files:**
- Read: `docs/superpowers/specs/2026-08-02-sarge-ccks-award-poster-design.md`
- Read: `paper/SARGE_CCKS2026.pdf`
- Read: `paper/ccks_2026/poster/SARGE_CCKS2026_poster_en_revised_v2.png`
- Read/render: `paper/ccks_2026/poster/template/CCKS2026-poster参考模板.pptx`
- Read: `paper/ccks_2026/poster/assets/SARGE_CCKS2026_poster_reference.png`
- Create: `paper/ccks_2026/poster/SARGE_CCKS2026_poster_award_v3_imagegen_prompt.md`
- Create: `paper/ccks_2026/poster/SARGE_CCKS2026_poster_award_v3_visual_reference.png`

- [ ] **Step 1: Dispatch the dedicated no-history imagegen subagent**

Spawn with `fork_turns="none"`. In its task, require it to:

- read `/home/tjk/.codex/skills/.system/imagegen/SKILL.md` completely;
- inspect the paper, approved design spec, official template PPTX (rendering it
  if needed), template reference PNG, and v2 render;
- use `view_image` before treating the v2 PNG as an edit/reference input;
- independently author a detailed `productivity-visual` prompt rather than
  receiving the main agent's prompt wording;
- include exact major English text and numbers from the approved spec;
- preserve the CCKS header/footer concept and 35:43 portrait ratio;
- fill the research body densely without recreating the seven-card dashboard;
- use the built-in image generation tool, not the CLI fallback;
- save the complete prompt and generation notes to the required Markdown path;
- move/copy the selected generated image into the required workspace path;
- not edit any PPTX, builder, validator, paper, or existing asset.

- [ ] **Step 2: Inspect the prompt and reference independently**

The main agent must read the prompt file and inspect the generated PNG with
`view_image`. Verify the four-zone architecture, dense body usage, dominant
method visual, continuous evidence band, CCKS template respect, and absence of
new research claims. Record all generated text errors; the bitmap is a layout
reference, so small text errors do not become poster content.

- [ ] **Step 3: Allow one targeted imagegen revision only if materially needed**

If the first image has a major architecture or density failure, send one
single-change follow-up to the same imagegen subagent. Preserve the first prompt
and record the targeted revision in the Markdown file. Do not iterate merely to
perfect small generated lettering.

- [ ] **Step 4: Validate files and commit**

Run:

```bash
file paper/ccks_2026/poster/SARGE_CCKS2026_poster_award_v3_visual_reference.png
test -s paper/ccks_2026/poster/SARGE_CCKS2026_poster_award_v3_imagegen_prompt.md
```

Expected: a valid portrait PNG and a non-empty prompt record.

```bash
git add paper/ccks_2026/poster/SARGE_CCKS2026_poster_award_v3_imagegen_prompt.md \
  paper/ccks_2026/poster/SARGE_CCKS2026_poster_award_v3_visual_reference.png
git commit -m "feat(poster): add award layout imagegen reference"
```

### Task 3: Build the Editable Award-Oriented PPTX

**Files:**
- Create: `paper/ccks_2026/poster/tools/build_sarge_poster_award.py`
- Read: `paper/ccks_2026/poster/tools/build_sarge_poster.py`
- Read: `paper/ccks_2026/poster/SARGE_CCKS2026_poster_en_revised_v2.pptx`
- Create: `paper/ccks_2026/poster/SARGE_CCKS2026_poster_en_award_v3.pptx`
- Test: `paper/ccks_2026/poster/tools/validate_sarge_poster_award.py --pptx-only`

- [ ] **Step 1: Add safe source preflight and shape helpers**

The builder must refuse to run unless the v2 source is one portrait slide, all
protected and removable source shape names exist, and the background/protected
shape signatures match the contract. Reuse the existing project's color/text
helpers where safe; keep this new builder focused and do not refactor the
canonical bilingual builder.

The builder CLI must accept `--out PATH`; when omitted, it writes the canonical
award-v3 PPTX path. This enables a clean rebuild without touching the delivered
file.

Add helpers for:

```python
def find_shape(slide, name: str): ...
def delete_named_shapes(slide, names: set[str]) -> None: ...
def set_name(shape, name: str): ...
def set_fixed_text(...): ...
def add_region(...): ...
def add_claim_heading(...): ...
def add_metric(...): ...
def add_connector(...): ...
```

Every new research object must use an `AW_` prefix and fixed-size text boxes.

- [ ] **Step 2: Preserve the template and update the header/take-home**

Open the v2 PPTX, remove only `S1_GROUP` through `S7_GROUP`, and leave protected
footer objects untouched. Preserve author/title/affiliation wording and enlarge
the title only if the final right edge remains clear of the conference logo.
Replace only `TAKEHOME_TEXT` copy with the approved sentence and use 30–34 pt.

- [ ] **Step 3: Build the hero row**

Use these starting geometries in inches and adjust only within the approved
body bounds:

```python
PROBLEM = (1.10, 9.75, 10.80, 11.50)
METHOD = (12.20, 9.75, 21.70, 11.50)
```

Build the red/green wrong-versus-correct row graphic on the left. Build the
five-stage method flow on the right with a visibly dominant output contract and
fixed-slot table. Use direct labels and connectors; no arrow may cross text.

- [ ] **Step 4: Build the continuous evidence band**

Use `EVIDENCE = (1.10, 21.55, 32.80, 7.10)`. Divide it into three aligned
modules with two 0.30-inch gutters. Align claim-heading baselines, major-number
baselines, and qualifier baselines. Use a native direct comparison graphic for
the multi-event values instead of a bordered table.

- [ ] **Step 5: Build the diagnostic and boundary band**

Use:

```python
DIAGNOSTIC = (1.10, 28.95, 18.70, 8.70)
CONTRIBUTION = (20.10, 28.95, 13.80, 8.70)
```

Create two editable dumbbell comparisons from F1 to ExactRec, followed by the
full `Δrecord` limitation. Put the three compact contributions and the boundary
box in the right region. Use the full region height so the bottom row does not
contain a vacant lower half.

- [ ] **Step 6: Generate the PPTX**

Run:

```bash
/home/tjk/.codex/venvs/codex-tools/bin/python \
  paper/ccks_2026/poster/tools/build_sarge_poster_award.py
```

Expected: the new v3 PPTX is created without modifying v2.

- [ ] **Step 7: Run the PPTX validator and fix all failures**

Run:

```bash
/home/tjk/.codex/venvs/codex-tools/bin/python \
  paper/ccks_2026/poster/tools/validate_sarge_poster_award.py --pptx-only
```

Expected: page, protected signatures, required/forbidden copy, shape bounds,
hyperlinks, font thresholds, autofit, density grid, and no-full-page-raster
checks pass.

- [ ] **Step 8: Commit builder and PPTX**

```bash
git add paper/ccks_2026/poster/tools/build_sarge_poster_award.py \
  paper/ccks_2026/poster/SARGE_CCKS2026_poster_en_award_v3.pptx
git commit -m "feat(poster): build award-oriented English poster"
```

### Task 4: Export PDF/PNG and Complete Automated QA

**Files:**
- Create: `paper/ccks_2026/poster/SARGE_CCKS2026_poster_en_award_v3.pdf`
- Create: `paper/ccks_2026/poster/SARGE_CCKS2026_poster_en_award_v3.png`
- Modify: `paper/ccks_2026/poster/tools/validate_sarge_poster_award.py`

- [ ] **Step 1: Export in an isolated LibreOffice profile**

Run:

```bash
/home/tjk/.codex/venvs/codex-tools/bin/python \
  /home/tjk/.claude/skills/pptx/scripts/office/soffice.py \
  --headless --convert-to pdf --outdir paper/ccks_2026/poster \
  paper/ccks_2026/poster/SARGE_CCKS2026_poster_en_award_v3.pptx
```

Expected: one-page `SARGE_CCKS2026_poster_en_award_v3.pdf`.

- [ ] **Step 2: Render the 150 dpi review PNG**

Run:

```bash
pdftoppm -png -r 150 -singlefile \
  paper/ccks_2026/poster/SARGE_CCKS2026_poster_en_award_v3.pdf \
  paper/ccks_2026/poster/SARGE_CCKS2026_poster_en_award_v3
```

Expected: approximately 5250 x 6450 px.

- [ ] **Step 3: Finish PDF, font, PNG, and QR validation**

Complete `--all` checks for:

- one PDF page at 2520 x 3096 pt;
- all fonts reported by `pdffonts` as embedded, subsetted, and Unicode-capable;
- extractable `SARGE`, `85.6`, `78.3`, `ExactRec`, and boundary text;
- 150 dpi PNG dimensions;
- rendered QR crop decoded by `zxingcpp` to
  `https://github.com/emmmdty/SARGE`;
- unchanged v2 hashes and absence of the imagegen-reference hash from PPTX
  media parts.

- [ ] **Step 4: Run full validation**

Run:

```bash
/home/tjk/.codex/venvs/codex-tools/bin/python \
  paper/ccks_2026/poster/tools/validate_sarge_poster_award.py --all
```

Expected: `overall_pass: true` with explicit density, font, hyperlink, page,
and QR evidence.

- [ ] **Step 5: Commit export and QA changes**

```bash
git add paper/ccks_2026/poster/tools/validate_sarge_poster_award.py \
  paper/ccks_2026/poster/SARGE_CCKS2026_poster_en_award_v3.pdf \
  paper/ccks_2026/poster/SARGE_CCKS2026_poster_en_award_v3.png
git commit -m "test(poster): validate award poster exports"
```

### Task 5: Perform Visual QA and One Fix-and-Reverify Cycle

**Files:**
- Read: `paper/ccks_2026/poster/SARGE_CCKS2026_poster_en_award_v3.png`
- Modify if needed: `paper/ccks_2026/poster/tools/build_sarge_poster_award.py`
- Regenerate if needed: award v3 PPTX/PDF/PNG

- [ ] **Step 1: Create visual QA derivatives outside the repository**

Using Pillow in the shared media Python, create a temporary full-page copy,
header/hero/evidence/bottom crops, grayscale render, 25% proxy, and 12.5% proxy.
Do not commit these derivatives.

- [ ] **Step 2: Main-agent bug-hunt pass**

Inspect the full image and every crop with `view_image`. Explicitly list at
least one issue or risk from the first pass, checking:

- excessive or uneven whitespace;
- unreadable labels at reduced scale;
- awkward wrapping or clipping;
- insufficient method dominance;
- disconnected evidence modules;
- overlap, arrow crossings, low contrast, or template obstruction;
- wrong/correct and F1/ExactRec discrimination in grayscale.

- [ ] **Step 3: Dispatch a fresh no-history visual reviewer**

The reviewer must not edit files and must inspect the full poster plus hero,
evidence, diagnostic/footer, grayscale, and reduced-scale images. Require a
five-second scan, 30-second narrative, one-/two-meter proxy readability,
density/whitespace, color balance, and clipping/overlap report.

- [ ] **Step 4: Apply one targeted, evidence-backed fix**

Make the smallest builder change that resolves the most material issue from
the two reviews. Regenerate PPTX/PDF/PNG and rerun `--all`. If the first render
has several material issues, fix them as a cohesive geometry/typography pass;
do not perform unrelated restyling.

- [ ] **Step 5: Reinspect the affected regions and complete the required cycle**

Re-render and re-view the affected crops. Expected: the original issue is gone
and no new clipping, collision, or empty region has appeared.

- [ ] **Step 6: Commit the verified refinement**

```bash
git add paper/ccks_2026/poster/tools/build_sarge_poster_award.py \
  paper/ccks_2026/poster/SARGE_CCKS2026_poster_en_award_v3.pptx \
  paper/ccks_2026/poster/SARGE_CCKS2026_poster_en_award_v3.pdf \
  paper/ccks_2026/poster/SARGE_CCKS2026_poster_en_award_v3.png
git commit -m "fix(poster): refine award poster readability"
```

### Task 6: Write the Analysis Report and Run Final Rebuild Verification

**Files:**
- Create: `paper/ccks_2026/poster/poster_award_v3_analysis.md`
- Verify: all award v3 files and tools

- [ ] **Step 1: Write the analysis report**

Include:

- project/paper/template/v2 diagnosis;
- official CCKS award mechanism and verified poster-design references;
- approved dense four-zone direction;
- final imagegen prompt, built-in tool mode, saved path, and generated-text
  limitations;
- exact content reductions and layout/font changes;
- before/after density and hierarchy comparison;
- protected-object, font, link, PDF, PNG, QR, and hash evidence;
- main-agent and independent visual-QA findings plus applied fix;
- unresolved print confirmations: public URL/QR, CITIC and Guotai Junan short
  forms, and Linux/LibreOffice font substitutions.

- [ ] **Step 2: Rebuild in a clean temporary directory**

Run:

```bash
rebuild_dir=$(mktemp -d /tmp/sarge-award-clean.XXXXXX)
/home/tjk/.codex/venvs/codex-tools/bin/python \
  paper/ccks_2026/poster/tools/build_sarge_poster_award.py \
  --out "$rebuild_dir/SARGE_CCKS2026_poster_en_award_v3.pptx"
/home/tjk/.codex/venvs/codex-tools/bin/python \
  /home/tjk/.claude/skills/pptx/scripts/office/soffice.py \
  --headless --convert-to pdf --outdir "$rebuild_dir" \
  "$rebuild_dir/SARGE_CCKS2026_poster_en_award_v3.pptx"
pdftoppm -png -r 150 -singlefile \
  "$rebuild_dir/SARGE_CCKS2026_poster_en_award_v3.pdf" \
  "$rebuild_dir/SARGE_CCKS2026_poster_en_award_v3"
```

Compare normalized PPTX content, page geometry, rendered PNG dimensions, and
key hashes that should be deterministic. Byte identity is not required for
ZIP/PDF metadata, but protected media and normalized research content must
match.

- [ ] **Step 3: Run final verification commands**

```bash
/home/tjk/.codex/venvs/codex-tools/bin/python \
  paper/ccks_2026/poster/tools/build_sarge_poster_award.py
/home/tjk/.codex/venvs/codex-tools/bin/python \
  paper/ccks_2026/poster/tools/validate_sarge_poster_award.py --all
/home/tjk/.codex/venvs/codex-tools/bin/python -m markitdown \
  paper/ccks_2026/poster/SARGE_CCKS2026_poster_en_award_v3.pptx
git diff --check
git status --short
```

Expected: build succeeds, `overall_pass: true`, extracted text contains no
placeholder, diff check is clean, and only the two pre-existing untracked user
files remain outside committed deliverables.

- [ ] **Step 4: Commit report and any final reproducibility adjustment**

```bash
git add paper/ccks_2026/poster/poster_award_v3_analysis.md \
  paper/ccks_2026/poster/tools/award_poster_contract.py \
  paper/ccks_2026/poster/tools/build_sarge_poster_award.py \
  paper/ccks_2026/poster/tools/validate_sarge_poster_award.py
git commit -m "docs(poster): record award poster design and QA"
```

### Task 7: Independent Code/Artifact Review and Handoff

**Files:**
- Review: all files introduced by this plan

- [ ] **Step 1: Run a fresh implementation review**

Dispatch a no-history reviewer with the approved spec, this plan, the final
git diff, validation output, and final PNG. Ask it to check spec alignment,
scientific accuracy, non-destructive behavior, rebuildability, and material
visual defects. It must not edit files.

- [ ] **Step 2: Resolve blocking review findings only**

Apply targeted fixes for any issue that could mislead a viewer, break the
deliverables, overwrite existing work, or prevent rebuilding. Rerun the full
validator and affected visual checks.

- [ ] **Step 3: Final handoff**

Report clickable paths to the PPTX, PDF, PNG, imagegen prompt, imagegen visual
reference, build script, validator, and analysis report. State that v2 and the
two pre-existing untracked user files were preserved. Summarize validation and
identify the three author confirmations still required before physical print.
