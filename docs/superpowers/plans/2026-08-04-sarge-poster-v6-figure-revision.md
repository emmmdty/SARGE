# SARGE Poster v6 Figure Revision Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Revise the v6 CCKS poster with paper-derived editable scientific figures, template-compliant blue regions, integer typography, accurate metrics, and stronger visual hierarchy.

**Architecture:** Extend the existing v6 contract, builder, and independent validator. Adapt the source-figure PPT structures as native PowerPoint shapes rather than raster screenshots, render only mathematical notation through LaTeX, and regenerate all three synchronized deliverables.

**Tech Stack:** Python, python-pptx, LaTeX/dvisvgm/rsvg-convert, LibreOffice, Poppler, OpenCV/QR decoder, pytest, Ruff.

---

### Task 1: Lock the revised scientific and layout contract

**Files:**
- Modify: `paper/ccks_2026/poster/tools/award_poster_contract.py`
- Modify: `tests/test_sarge_poster_v6_contract.py`
- Modify: `tests/test_sarge_poster_v6_builder.py`

- [ ] Add failing tests for the white-body Take-home position, integer font sizes, Noto Sans, source-figure progression, 0–100 Multi-Event scale, revised metric labels, and forbidden overclaims.
- [ ] Run the focused tests and confirm the new assertions fail against the current builder.
- [ ] Add exact revised copy, representative baseline rows, source-figure paths, formula paths, and body-band coordinates to the v6 contract.
- [ ] Run the contract tests and confirm they pass.

### Task 2: Render the required LaTeX formulas

**Files:**
- Create: `paper/ccks_2026/poster/assets/formulas/v6_method_input.tex`
- Create: `paper/ccks_2026/poster/assets/formulas/v6_delta_record.tex`
- Create through the existing renderer: matching `.png` files

- [ ] Add LaTeX sources for `x_D=[D;\mathcal{S};C_K(D);P_D;I_S]` and `\Delta_{\mathrm{record}}=F_1-\mathrm{ExactRec}` with visually smaller subscripts.
- [ ] Render both formulas with `tools/render_award_formulas.py`.
- [ ] Verify transparent backgrounds, nonzero dimensions, and adequate resolution.

### Task 3: Rebuild Motivation and Method as scientific figures

**Files:**
- Modify: `paper/ccks_2026/poster/tools/build_sarge_poster_v6.py`

- [ ] Move the Take-home message fully into the white template region and restyle it without a rounded dark banner.
- [ ] Rebuild Motivation from `fig1_binding_gap_vector.pptx`: source evidence, unordered value pool, and WRONG/CORRECT event-row assembly.
- [ ] Use restrained navy/teal/red/gray rather than the source figure’s neon palette.
- [ ] Rebuild Method from `fig2_sarge_pipeline_vector.pptx`: inputs, schema-grounded contract, answer-token SFT/complete-row generation, post-generation check, fixed-slot table.
- [ ] Insert the LaTeX method-input image and highlight the complete event row as the prediction unit.
- [ ] Remove the isolated seed-13 100% conformance claim and reduce implementation details to one subordinate line.
- [ ] Normalize every generated font size to an integer point value.

### Task 4: Strengthen Results and Conclusion without overclaiming

**Files:**
- Modify: `paper/ccks_2026/poster/tools/build_sarge_poster_v6.py`

- [ ] Expand the main table with Doc2EDAG, GIT, ProCNet, EPAL, SEELE, and SARGE.
- [ ] Change the Multi-Event plot to a visible 0–100 axis and label the 5.1-point result as ChFinAnn-specific.
- [ ] Change `Record-level gap` to `F1 − ExactRec`; retain `35.1†` with the short per-seed footnote.
- [ ] Insert the LaTeX diagnostic formula image and explain its descriptive scope.
- [ ] Update Take-home and conclusion language to distinguish illustrative same-type binding from the general Multi-Event evaluation subset.
- [ ] Use only accepted-paper-supported limitations.

### Task 5: Extend independent validation

**Files:**
- Modify: `paper/ccks_2026/poster/tools/validate_sarge_poster_v6.py`
- Modify: `tests/test_sarge_poster_v6_validation.py`

- [ ] Add failing validator tests for integer point sizes, body/header/footer region separation, required source-figure stages, formula images, 0–100 plot endpoints, revised wording, and exact output contents.
- [ ] Implement the checks independently of builder constants where practical.
- [ ] Run all v6 tests and fix failures.
- [ ] Run the v5 regression suite to confirm v5 remains unchanged.

### Task 6: Export and visual QA

**Files:**
- Regenerate only:
  - `paper/ccks_2026/poster/final_v6/SARGE_CCKS2026_poster_en_award_v6.pptx`
  - `paper/ccks_2026/poster/final_v6/SARGE_CCKS2026_poster_en_award_v6.pdf`
  - `paper/ccks_2026/poster/final_v6/SARGE_CCKS2026_poster_en_award_v6.png`

- [ ] Build the PPTX with the shared media Python environment.
- [ ] Export PDF with LibreOffice and PNG with Poppler.
- [ ] Run the full v6 validator, Ruff, PPTX ZIP integrity, PDF font/page checks, and QR decoding.
- [ ] Inspect the final render at full size, 50%, 25%, and A4-scaled size.
- [ ] Complete at least one visual fix-and-reverify cycle.
- [ ] Confirm `final_v6` contains exactly the three requested deliverables and source v5 hashes remain unchanged.

The user explicitly prohibited commits, pushes, publication, destructive cleanup, and source-file overwrites, so no commit steps are included.
