# SARGE Poster Visual Refinement Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Produce a non-destructive v2 English SARGE poster with a dominant method hero, a continuous results evidence band, an imagegen reference mockup, and complete visual/engineering QA.

**Architecture:** Use the verified v1 PPTX as the only editable base. Generate a raster composition reference with built-in imagegen, then reproduce only its approved hierarchy and spacing ideas with native PowerPoint text, shapes, groups, and connectors. Export through LibreOffice, render through Poppler, and compare v2 structure/text/template invariants against v1.

**Tech Stack:** Built-in imagegen, python-pptx plus direct OOXML, Pillow, LibreOffice Impress, Poppler, ImageMagick, `pdffonts`, `zxing-cpp`, shared media Python `/home/tjk/.codex/venvs/codex-tools/bin/python`.

---

### Task 1: Freeze v1 Baseline and Target Paths

**Files:**
- Read: `paper/ccks_2026/poster/SARGE_CCKS2026_poster_en_revised.pptx`
- Read: `paper/ccks_2026/poster/SARGE_CCKS2026_poster_en_revised.pdf`
- Read: `paper/ccks_2026/poster/SARGE_CCKS2026_poster_en_revised.png`
- Read: `paper/ccks_2026/poster/poster_revision_report.md`
- Create: `/tmp/sarge_poster_v2_legacy_hashes.txt`

- [ ] **Step 1: Confirm branch and source files**

Run:

```bash
git branch --show-current
ls -lh paper/ccks_2026/poster/SARGE_CCKS2026_poster_en_revised.{pptx,pdf,png}
```

Expected: branch `poster/ccks-2026`; all three v1 files exist.

- [ ] **Step 2: Capture legacy hashes**

Run:

```bash
sha256sum \
  paper/ccks_2026/poster/SARGE_CCKS2026_poster_en.pptx \
  paper/ccks_2026/poster/SARGE_CCKS2026_poster_en.pdf \
  paper/ccks_2026/poster/SARGE_CCKS2026_poster_en_backup.pptx \
  paper/ccks_2026/poster/SARGE_CCKS2026_poster_en_revised.pptx \
  paper/ccks_2026/poster/SARGE_CCKS2026_poster_en_revised.pdf \
  paper/ccks_2026/poster/SARGE_CCKS2026_poster_en_revised.png \
  paper/ccks_2026/poster/poster_revision_report.md \
  > /tmp/sarge_poster_v2_legacy_hashes.txt
```

Expected: seven non-empty hash records.

### Task 2: Generate and Save the Imagegen Reference

**Files:**
- Read/reference: `paper/ccks_2026/poster/SARGE_CCKS2026_poster_en_revised.png`
- Create: `paper/ccks_2026/poster/SARGE_CCKS2026_poster_en_visual_reference.png`

- [ ] **Step 1: Inspect the v1 PNG as the image edit target**

Use `view_image` at original detail.

Expected: the complete portrait poster is legible and available as Image 1.

- [ ] **Step 2: Generate one reference mockup with built-in imagegen**

Use case: `infographic-diagram`.

Prompt requirements:

```text
Image 1 is the edit target and sole content/layout reference.
Create a polished academic-poster composition study, not a final factual poster.
Keep the CCKS blue-purple header, title zone, logo clearance, dark take-home band,
and blue-purple footer visually unchanged.
Change only the white research-body composition.
Make the six-step SARGE method the dominant hero visual.
Make the three middle result sections read as one continuous evidence band.
Reduce nested rounded cards and repeated outlines by roughly forty percent.
Increase whitespace and align the major numeric anchors.
Keep only these major readable anchors: “SARGE”, “85.6”, “78.3”, “81.7”,
and “ExactRec”. Represent all smaller copy as abstract gray line blocks.
Use blue and teal as the primary accents; orange, purple, and red only for small
semantic callouts.
Preserve portrait proportions and the Problem → Method → Evidence → Boundary flow.
No new logos, no new claims, no additional data, no illustrations, no photos,
no decorative gradients in the white body, no watermark.
```

Expected: one portrait composition reference that visibly demonstrates the
approved hierarchy without introducing research content.

Invoke the built-in tool with the absolute v1 PNG path in
`referenced_image_paths`; do not rely on conversational image numbering alone.

- [ ] **Step 3: Save the selected result in the workspace**

Copy the built-in generated image from its reported `$CODEX_HOME/generated_images`
path to:

`paper/ccks_2026/poster/SARGE_CCKS2026_poster_en_visual_reference.png`

Expected: the project-local PNG opens successfully and is not referenced by the
PowerPoint package.

- [ ] **Step 4: Record the reference image hash**

Run:

```bash
sha256sum \
  paper/ccks_2026/poster/SARGE_CCKS2026_poster_en_visual_reference.png \
  > /tmp/sarge_poster_v2_reference_hash.txt
```

Expected: one non-empty hash record used later to prove that the reference image
is absent from v2 PPTX media and relationships.

### Task 3: Build the Editable v2 PPTX

**Files:**
- Create: `/tmp/sarge_poster_v2_build.py`
- Read: `paper/ccks_2026/poster/SARGE_CCKS2026_poster_en_revised.pptx`
- Create: `paper/ccks_2026/poster/SARGE_CCKS2026_poster_en_revised_v2.pptx`

- [ ] **Step 1: Write a v2 build script**

The script must:

- open the v1 PPTX and preserve the single slide, slide master/layout,
  background image, header, take-home, footer, hyperlinks, and conference text;
- work recursively inside `S1_GROUP` through `S7_GROUP`;
- preserve normalized text content against v1;
- preserve the seven outer group geometries;
- reduce outer card border contrast from `#D9E2F1` to a lighter neutral;
- soften or remove selected internal outlines while preserving semantic fills;
- restyle Section 2 so `Output contract` and `Fixed-slot table` receive stronger
  blue/teal emphasis and the other four nodes receive lighter fills;
- enlarge and align Section 2 step-number badges and clarify the five-arrow route;
- align Section 3–5 divider positions, major-number top edges, and metric labels;
- use a shared pale-blue numeric-anchor treatment across Sections 3–5;
- use matching Section 3–5 internal left/right padding;
- count v1 and v2 internal stroked shapes and reduce that count by 35–45%;
- preserve blue/teal/orange/red/purple semantic color assignments;
- retain all Section 5 sentences verbatim while tightening vertical spacing;
- simplify Section 6 cell chrome and visually relate its explanation to the
  Section 7 boundary without adding text;
- reduce the three Section 7 contribution lines' weight through tint and type
  weight while keeping the boundary box more prominent;
- preserve font minima, fixed-size text, grouping, naming, and editability;
- save only to the v2 path.

- [ ] **Step 2: Run the build script**

Run:

```bash
/home/tjk/.codex/venvs/codex-tools/bin/python /tmp/sarge_poster_v2_build.py
```

Expected: a valid one-slide v2 PPTX.

- [ ] **Step 3: Verify package integrity**

Run:

```bash
unzip -t paper/ccks_2026/poster/SARGE_CCKS2026_poster_en_revised_v2.pptx
```

Expected: `No errors detected`.

### Task 4: Export v2 PDF and PNG

**Files:**
- Create: `paper/ccks_2026/poster/SARGE_CCKS2026_poster_en_revised_v2.pdf`
- Create: `paper/ccks_2026/poster/SARGE_CCKS2026_poster_en_revised_v2.png`

- [ ] **Step 1: Export PDF with isolated LibreOffice profile**

Run:

```bash
export_dir=$(mktemp -d /tmp/sarge-poster-v2-export.XXXXXX)
lo_profile=$(mktemp -d /tmp/sarge-poster-v2-lo-profile.XXXXXX)
soffice -env:UserInstallation=file://$lo_profile --headless \
  --convert-to pdf --outdir "$export_dir" \
  paper/ccks_2026/poster/SARGE_CCKS2026_poster_en_revised_v2.pptx
cp -a "$export_dir/SARGE_CCKS2026_poster_en_revised_v2.pdf" \
  paper/ccks_2026/poster/SARGE_CCKS2026_poster_en_revised_v2.pdf
```

Expected: one-page PDF.

- [ ] **Step 2: Render 150 dpi PNG**

Run:

```bash
pdftoppm -png -r 150 -singlefile \
  paper/ccks_2026/poster/SARGE_CCKS2026_poster_en_revised_v2.pdf \
  paper/ccks_2026/poster/SARGE_CCKS2026_poster_en_revised_v2
```

Expected: approximately `5250 × 6450 px`.

- [ ] **Step 3: Inspect the complete render and targeted crops**

Create the crops and distance/grayscale proxies first:

```bash
qa_dir=$(mktemp -d /tmp/sarge-poster-v2-visual-qa.XXXXXX)
convert paper/ccks_2026/poster/SARGE_CCKS2026_poster_en_revised_v2.png \
  -crop 5250x2140+0+870 +repage "$qa_dir/hero-row.png"
convert paper/ccks_2026/poster/SARGE_CCKS2026_poster_en_revised_v2.png \
  -crop 5250x1780+0+3000 +repage "$qa_dir/evidence-band.png"
convert paper/ccks_2026/poster/SARGE_CCKS2026_poster_en_revised_v2.png \
  -crop 5250x2151+0+4300 +repage "$qa_dir/diagnostic-footer.png"
convert paper/ccks_2026/poster/SARGE_CCKS2026_poster_en_revised_v2.png \
  -colorspace Gray "$qa_dir/grayscale.png"
convert paper/ccks_2026/poster/SARGE_CCKS2026_poster_en_revised_v2.png \
  -resize 25% "$qa_dir/one-meter-proxy.png"
convert paper/ccks_2026/poster/SARGE_CCKS2026_poster_en_revised_v2.png \
  -resize 12.5% "$qa_dir/two-meter-proxy.png"
```

Expected: six readable QA images. The reduced-scale images are screen proxies
for hierarchy at increasing viewing distance, not physical-distance calibration.

Use `view_image` on the full page and crops covering:

- header/take-home;
- problem/method hero row;
- Sections 3–5 evidence band;
- Sections 6–7 and footer.

Expected: no clipping, accidental overlap, arrow crossing, or template
obstruction.

### Task 5: Create the v2 Validator and Visual Analysis Report

**Files:**
- Create: `/tmp/sarge_poster_v2_qa.py`
- Create: `paper/ccks_2026/poster/poster_visual_analysis.md`

- [ ] **Step 1: Write the validator**

The validator must compare v1 and v2 and emit structured evidence for:

- normalized text equality while ignoring only permitted line-break differences;
- exact required qualifier presence;
- separate exact conference-text checks for wording, internal line break,
  rotation, 48 pt size, and geometry;
- required background hash equality;
- recursive bounds;
- fixed-size/no-shrink text;
- ordinary-body font minimum 18 pt and a named whitelist of source/seed/path
  notes that may use 16 pt;
- group geometry and regional names;
- hyperlink targets;
- full-page-rasterization absence;
- absence of the visual-reference hash from PPTX media and absence of any
  relationship to the reference filename;
- exact v1/v2 picture-shape, media-part, and image-relationship comparison,
  allowing only the unchanged v1 background and QR assets and rejecting any
  new or re-encoded raster research region;
- exact v1/v2 signatures for every non-body template element: `HDR_*`,
  `TAKEHOME_*`, and `FTR_*` shapes, including wording, geometry, rotation,
  typography, fills/lines, hyperlinks, and media relationships; the CCKS logo
  and top/bottom decorations are covered by the unchanged background asset;
- v1/v2 internal-stroke counts and a 35–45% reduction result;
- matching Section 3–5 internal padding and preserved semantic color checks;
- PDF page size and font embedding;
- PNG dimensions;
- rendered QR decoding;
- legacy hash preservation.

- [ ] **Step 2: Run the validator**

Run:

```bash
/home/tjk/.codex/venvs/codex-tools/bin/python \
  /tmp/sarge_poster_v2_qa.py \
  --legacy-hashes /tmp/sarge_poster_v2_legacy_hashes.txt \
  --output /tmp/sarge_poster_v2_qa.json
```

Expected: `overall_pass: true`.

- [ ] **Step 3: Write the analysis report**

`poster_visual_analysis.md` must include:

- current-v1 diagnosis;
- external design references and URLs;
- approved direction and rationale;
- imagegen prompt, tool mode, and saved path;
- exact implementation changes;
- before/after visual hierarchy comparison;
- engineering QA table;
- unresolved author confirmations;
- required local/server project paths and local/server/shared-media Python
  environments;
- placeholder for independent visual QA.

The unresolved-confirmation section must retain:

- final public URL and QR confirmation for print;
- CITIC and Guotai Junan short-form confirmation;
- acceptance of Linux font substitutions.

### Task 6: Independent Visual QA and Refinement

**Files:**
- Read: `paper/ccks_2026/poster/SARGE_CCKS2026_poster_en_revised_v2.png`
- Modify if required: `/tmp/sarge_poster_v2_build.py`
- Regenerate if required: v2 PPTX/PDF/PNG
- Modify: `paper/ccks_2026/poster/poster_visual_analysis.md`

- [ ] **Step 1: Dispatch a fresh-eyes visual reviewer**

Dispatch a different fresh-eyes subagent that did not implement v2. The reviewer
must not edit files. Require checks for:

- five-second hierarchy;
- 30-second narrative flow;
- one- and two-meter readability;
- grayscale discrimination;
- text clipping or awkward wrapping;
- overlap and arrow crossings;
- color balance;
- template obstruction;
- whether the method is visibly dominant;
- whether Sections 3–5 read as one evidence sequence.

Expected: `APPROVED` or a concise issue list.

- [ ] **Step 2: Apply only evidence-backed refinements**

For each material issue:

- make one targeted change in the build script;
- regenerate PPTX/PDF/PNG;
- rerun v2 QA;
- reinspect the changed region.

Expected: no unresolved major visual issue.

- [ ] **Step 3: Record the independent QA result**

Append the review checklist, result, and any applied fixes to
`poster_visual_analysis.md`.

### Task 7: Final Verification and Handoff

**Files:**
- Verify all five v2 deliverables plus the design and plan documents.

- [ ] **Step 1: Re-render v2 from PPTX in a fresh temporary directory**

Run:

```bash
verify_dir=$(mktemp -d /tmp/sarge-poster-v2-final-verify.XXXXXX)
lo_profile=$(mktemp -d /tmp/sarge-poster-v2-final-lo.XXXXXX)
soffice -env:UserInstallation=file://$lo_profile --headless \
  --convert-to pdf --outdir "$verify_dir" \
  paper/ccks_2026/poster/SARGE_CCKS2026_poster_en_revised_v2.pptx
pdftoppm -png -r 150 -singlefile \
  "$verify_dir/SARGE_CCKS2026_poster_en_revised_v2.pdf" \
  "$verify_dir/recheck"
cmp -s "$verify_dir/recheck.png" \
  paper/ccks_2026/poster/SARGE_CCKS2026_poster_en_revised_v2.png
```

Expected: `cmp` exits 0; the regenerated PNG is byte-identical to the delivered
PNG.

- [ ] **Step 2: Run fresh structural QA**

Expected:

- one slide;
- 88.90 × 109.22 cm portrait;
- zero out-of-bounds objects;
- no non-template auto-fit/shrink;
- ordinary body text at least 18 pt;
- only explicitly named source/seed/path notes at 16 pt;
- seven section groups;
- five method arrows;
- correct native hyperlinks;
- unchanged template/background;
- PDF 2520 × 3096 pt with embedded fonts;
- PNG approximately 5250 × 6450 px;
- QR decodes to the supplied public URL;
- no forbidden claim.

Run:

```bash
/home/tjk/.codex/venvs/codex-tools/bin/python \
  /tmp/sarge_poster_v2_qa.py \
  --legacy-hashes /tmp/sarge_poster_v2_legacy_hashes.txt \
  --output "$verify_dir/final_qa.json"
jq '{
  overall_pass,
  bounds_pass,
  body_font_min_pass,
  note_font_whitelist_pass,
  text_invariants_pass,
  conference_invariants_pass,
  background_identity_pass,
  reference_image_absent_pass,
  internal_stroke_reduction_pass,
  semantic_color_pass,
  pdf_fonts_embedded_pass,
  qr_decode_pass
}' "$verify_dir/final_qa.json"
```

Expected: every printed check is `true`.

- [ ] **Step 3: Verify deliverable hashes and git scope**

Run:

```bash
sha256sum \
  paper/ccks_2026/poster/SARGE_CCKS2026_poster_en_visual_reference.png \
  paper/ccks_2026/poster/SARGE_CCKS2026_poster_en_revised_v2.pptx \
  paper/ccks_2026/poster/SARGE_CCKS2026_poster_en_revised_v2.pdf \
  paper/ccks_2026/poster/SARGE_CCKS2026_poster_en_revised_v2.png \
  paper/ccks_2026/poster/poster_visual_analysis.md
git status --short
```

Expected: all deliverables exist; no legacy hash changed; unrelated files remain
untouched.
