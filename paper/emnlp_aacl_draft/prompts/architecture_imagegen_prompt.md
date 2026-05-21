# Codex Image-Gen Prompt: SARGE Architecture Figure

Create a publication-quality vector-style architecture figure for an ACL/EMNLP paper.

Title: "SARGE: Schema-Aware Role-Grounded Extractor".

Canvas and style:
- Landscape aspect ratio suitable for a two-column NLP paper figure.
- White background, thin dark-gray outlines, restrained color palette.
- Use clean geometric boxes, arrows, and small schematic icons only.
- Do not use 3D effects, decorative gradients, shadows, clipart, or stock-photo elements.
- Text must be crisp and legible at paper scale.
- Use a style similar to top-tier NLP method figures: precise, sparse, and technical.

Content layout:
1. Left block: "Evidence grounding".
   Include document and event schema entering a surface memory builder.
   Show candidate spans such as entities, amounts, dates, and shares.
2. Middle-left block: "Role-grounded prompt".
   Show schema roles copied into a role-safe JSON contract and a candidate span table.
3. Middle-right block: "LLM generation".
   Show Qwen3-4B + LoRA, k=1 greedy decoding, optional SACD guard.
4. Right block: "Canonicalization".
   Show schema-valid parser, anchor-compatible split/merge/dedup, and canonical JSONL export.
5. Bottom layer: three separated evaluation tracks.
   Boxes must read "Legacy-FS: main fixed-slot table", "Unified-Strict: canonical diagnostics", and "DocFEE-Official: separate official-style track".

Critical constraints:
- Keep the three evaluation tracks visually separate. Do not imply that their metrics are averaged or mixed.
- Do not mention CACD.
- Do not include author names, institution names, or GitHub URLs.
- Avoid any claim like SOTA or leaderboard.
- Prefer simple arrow routing that does not cross text.

Output target:
- A clean SVG-like or PDF-like vector composition that can be redrawn deterministically for LaTeX.
