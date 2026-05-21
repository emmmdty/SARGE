# Codex Image-Gen Prompt: SARGE Pipeline Example Figure

Create a publication-quality vector-style pipeline example for an ACL/EMNLP paper.

Theme:
SARGE converts a long Chinese financial announcement into validated event records by grounding generation in schema roles and document-visible surface candidates.

Canvas and style:
- Landscape aspect ratio for a two-column paper.
- White background, restrained blue/green/gray palette, thin outlines.
- Precise academic schematic style inspired by SEELE and EPAL figures, but do not copy their layout.
- No decorative stock imagery, no 3D, no gradient-heavy design.
- Text must be short and readable.

Figure content:
1. Left panel: "Input document".
   Show a long announcement split into sentence snippets.
   Indicate scattered evidence: pledge notice, share amount, holding ratio, release date.
2. Middle panel: "Grounded prompt".
   Show event schema roles and a surface-candidate table with no more than four rows.
   Label: "copy event and role names exactly".
3. Right panel: "Validated output".
   Show a compact JSON-like event record with event_type and arguments.
   Add small validation badges: schema-valid, zero parse failure, zero invalid role.
4. Bottom annotation:
   "The model selects and organizes document-visible spans instead of freely inventing role values."

Critical constraints:
- Do not include fabricated real company names.
- Do not include any unverified metric number in the figure.
- Do not include pending multi-seed numbers.
- Keep all visible text in English.

Output target:
- A clean SVG-like or PDF-like vector composition that can be redrawn deterministically for LaTeX.
