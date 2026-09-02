# SARGE Poster v6 Density and Mechanism Revision Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rebalance the final v6 poster around a fuller motivation and a technically explicit, dominant method figure while eliminating large blank regions and preserving paper accuracy.

**Architecture:** Extend the existing contract-driven Python poster builder. Tests specify scientific wording, band geometry, native-object editability, zoomed-axis integrity, and white-space occupancy; the builder then redraws the affected sections and the validator checks the exported PPTX/PDF/PNG.

**Tech Stack:** Python, python-pptx, LaTeX/dvisvgm/rsvg-convert, LibreOffice, Poppler, pytest, Ruff, zxing-cpp.

---

### Task 1: Encode the revised scientific and layout contract

**Files:**
- Modify: `paper/ccks_2026/poster/tools/award_poster_contract.py`
- Modify: `tests/test_sarge_poster_v6_contract.py`

- [ ] Add tests for revised take-home wording, three motivation anchors, four method layers, evidence scope, conclusion scope, 70–95 plot range, and method/results band proportions.
- [ ] Run contract tests and confirm the new assertions fail for the current poster contract.
- [ ] Implement the revised constants and geometry without adding unsupported claims.
- [ ] Re-run contract tests and confirm they pass.

### Task 2: Add the answer-token SFT equation

**Files:**
- Create: `paper/ccks_2026/poster/assets/formulas/v6_sft_loss.tex`
- Create: `paper/ccks_2026/poster/assets/formulas/v6_sft_loss.png`
- Modify: `tests/test_sarge_poster_v6_builder.py`

- [ ] Add a builder test requiring a named SFT-loss formula picture with descriptive alt text.
- [ ] Run the targeted test and confirm it fails because the formula is absent.
- [ ] Add the LaTeX source and render it with the existing formula renderer.
- [ ] Inspect the rendering and confirm true subscripts and transparency.

### Task 3: Rebuild Motivation without empty source regions

**Files:**
- Modify: `paper/ccks_2026/poster/tools/build_sarge_poster_v6.py`
- Modify: `tests/test_sarge_poster_v6_builder.py`

- [ ] Add tests for a native source-evidence table, consistent chevrons, three motivation anchors, and stronger wrong/correct markers.
- [ ] Run the targeted tests and confirm failure.
- [ ] Replace the under-filled source box and rebuild the lower motivation argument.
- [ ] Render a temporary poster and inspect the Motivation crop.

### Task 4: Expand the method into four explicit layers

**Files:**
- Modify: `paper/ccks_2026/poster/tools/build_sarge_poster_v6.py`
- Modify: `tests/test_sarge_poster_v6_builder.py`

- [ ] Add tests for the compact comparison strip, prompt/SFT/decoding/post-validation layer labels, standard-decoding disclaimer, SFT formula, and highlighted row identity.
- [ ] Run the targeted tests and confirm failure.
- [ ] Replace the vertical conventional lane and enlarge the contract/SFT modules.
- [ ] Move the shortened engineering note to the bottom-right and render a method crop.

### Task 5: Densify Results and clarify evidence

**Files:**
- Modify: `paper/ccks_2026/poster/tools/build_sarge_poster_v6.py`
- Modify: `tests/test_sarge_poster_v6_builder.py`

- [ ] Add tests for the 70–95 zoomed dot plot, explicit axis label, navy evidence scope, paired Role F1/ExactRec questions, and retained Delta_record definition.
- [ ] Run targeted tests and confirm failure.
- [ ] Implement the revised Panel B and Panel C layouts without bar marks.
- [ ] Render and inspect Results at full and 50% scale.

### Task 6: Update conclusion and validation rules

**Files:**
- Modify: `paper/ccks_2026/poster/tools/validate_sarge_poster_v6.py`
- Modify: `tests/test_sarge_poster_v6_validation.py`

- [ ] Add validation tests for integer-point Noto Sans text, revised terminology, allowed formula media, band geometry, object bounds, and forbidden causal/constraint claims.
- [ ] Run the validation tests and confirm failure.
- [ ] Implement the validator updates and revised conclusion layout.
- [ ] Run all v6 tests, all v5 regression tests, Ruff, and `git diff --check`.

### Task 7: Export and inspect final deliverables

**Files:**
- Overwrite only: `paper/ccks_2026/poster/final_v6/SARGE_CCKS2026_poster_en_award_v6.{pptx,pdf,png}`

- [ ] Build the PPTX with the shared media Python.
- [ ] Export PDF with the repository LibreOffice wrapper.
- [ ] Render the 150 dpi PNG with Poppler.
- [ ] Run `validate_sarge_poster_v6.py --all` and verify QR decoding.
- [ ] Inspect final full-size, 50%, 25%, and A4-scaled renders; perform at least one fix-and-reverify cycle.
- [ ] Confirm `final_v6` contains exactly three files and the v5 PPTX hash is unchanged.
