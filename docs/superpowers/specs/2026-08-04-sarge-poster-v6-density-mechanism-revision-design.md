# SARGE Poster v6 Density and Mechanism Revision Design

## Objective

Revise the existing v6 poster so it carries enough scientific information for an excellent conference poster without returning to equal-sized cards or dense paper-like prose. The four sections must remain visually distinct, the method must occupy more space than the results, and the accepted paper remains the sole authority for every mechanism, claim, limitation, and number.

## Scientific boundaries

- Do not claim that the ChFinAnn multi-event gain causally proves fewer binding errors; EPAL ExactRec predictions are unavailable.
- Treat `Delta_record = F1 - ExactRec` as the paper-defined diagnostic separation, while retaining the caveat that it is not a pure binding-error estimate.
- State that source-value grounding uses bounded document candidates and copy-oriented prompt instructions; it is not constrained decoding or a hard lexical filter.
- State that answer-token SFT computes loss only on the serialized gold event-table answer.
- State that inference uses standard greedy decoding over the tokenizer vocabulary, followed by schema checking and fixed-slot normalization.
- Do not add unsupported claims about open-domain failure, cross-domain degradation, or performance as event count grows. A scope statement may say only that the reported study is closed-schema Chinese financial DEE and that open-schema behavior is not evaluated.

## Information architecture

Keep the official blue header and footer unchanged. Use the white body as four explicit numbered bands:

1. Take-home: a short statement about wrong event rows, the 5.1-point ChFinAnn multi-event gain, and ExactRec revealing complete-row failures.
2. Motivation: approximately 7.6 inches high, with a dominant wrong/correct event example plus three explicit reasons the problem matters.
3. Method: approximately 9.3 inches high and visually larger than Results. Show the common post-hoc pipeline only as a compact comparison strip, then devote the main area to a four-layer SARGE mechanism.
4. Results: approximately 7.5 inches high with overall comparison, a zoomed 70–95 multi-event dot plot, and complementary Role F1/ExactRec diagnosis.
5. Conclusion: approximately 2.9 inches high with prediction-unit insight, evaluation insight, and a supported scope/limitation statement.

## Motivation design

- Replace the under-filled source-evidence box with a compact native table containing event ID, shares, pledgee, and period for both same-type events.
- Use consistent chevron arrows between source evidence, recovered unordered values, and row assembly.
- Strengthen the wrong/correct contrast with a visible red cross, a teal check, heavier outlines, and direct field highlighting.
- Replace the generic consequence sentence with: all displayed values are correct, yet the wrong assembly describes two pledge records that do not occur in the source evidence.
- Add three concise motivation anchors: assembly risk, evaluation blind spot, and false-record consequence.
- End with the design goal: make the event table the structured prediction object and keep one event per row.

## Method design

- Replace the tall left column with a compact horizontal comparison strip: role-wise values to post-hoc assembly to cross-row risk.
- Use four explicit mechanism layers across the full width:
  1. Prompt contract: document, closed schema, bounded candidates, optional slot prior, and one-event-per-row instruction.
  2. Answer-only SFT target: the gold serialized event table; only answer tokens contribute to the loss.
  3. Standard decoding: greedy decoding over the normal tokenizer vocabulary; no constrained vocabulary.
  4. Post-validation and fixed-slot output: remove malformed or unlicensed rows/roles, empty fields, duplicates, and normalize role order.
- Make the prompt-contract and answer-only SFT modules the two largest modules.
- Add a LaTeX-rendered answer-token SFT loss formula.
- Show row identity through a highlighted output row and explain that the serialized table is the prediction object; do not imply separate per-row model calls.
- Move the shortened engineering line to a subordinate bottom-right position.

## Results design

- Retain six representative rows in the overall table and focus its interpretation on the reported strength profile rather than claiming universal SOTA.
- Change the multi-event plot to an explicitly labelled `Zoomed axis: 70–95` dot plot with all ticks visible and no bars. This removes the unused 0–75 field without hiding the scale.
- Use lower-case `multi-event` in running prose and title-case `Multi-Event F1` only for metric/title labels.
- Change the evidence note to navy/gray and state that +5.1 demonstrates general multi-event robustness but does not isolate binding-error reduction because baseline ExactRec is unavailable.
- In the diagnostic panel, add two visually paired questions: Role F1 asks whether role–value pairs are recovered; ExactRec asks whether the complete row is exact.
- Retain the paper-defined Delta_record formula and its caveat.

## Conclusion design

- Gain: prediction-unit insight rather than a score restatement.
- Diagnostic: Role F1 and ExactRec are complementary views of value recovery and exact row correctness.
- Remaining limitation: the reported setting is closed-schema Chinese financial DEE; open-schema behavior is not evaluated, and ExactRec remains incomplete.

## Visual system

- Preserve Noto Sans and integer-point sizes.
- Use navy for structure, teal for SARGE/correct outcomes, restrained red for invalid assembly, and gray for evidence scope and secondary detail.
- Use one chevron-arrow language throughout; eliminate mixed arrow glyph styles.
- Avoid rounded cards and decorative capsules. Use native tables, aligned rules, small stage labels, and one continuous method flow.
- Fill previously empty regions with scientific content or enlarge adjacent figures; do not add decorative filler.
- Keep equations as LaTeX-rendered images with true subscripts.

## Acceptance checks

- Method band is taller and contains more editable scientific content than Results.
- No large unexplained blank region remains in the three user-identified areas or elsewhere in the white body.
- At 25% scale, problem, mechanism, 5.1, ExactRec, and conclusion remain identifiable.
- At 50% scale, the four method layers and principal numbers are readable.
- PPTX/PDF/PNG remain synchronized; QR decodes; v5 is unchanged; `final_v6` contains exactly three files.
