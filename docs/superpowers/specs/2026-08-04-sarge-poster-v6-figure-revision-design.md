# SARGE CCKS 2026 Poster v6 Figure Revision Design

## Objective

Revise the existing v6 poster so a conference viewer can understand, in order:

1. why correct role values can still yield wrong event records;
2. what SARGE changes in the prediction unit and schema contract;
3. where the reported improvement appears and what ExactRec adds;
4. which record-assembly limitation remains.

The accepted paper remains the only authority for claims and numbers.

## Template and typography

- Preserve the official 88.90 × 109.22 cm slide size and official background.
- Reserve the upper blue region for title, authors, affiliations, corresponding-author contact, and CCKS identity only.
- Reserve the lower blue region for QR/paper-code contact and mandatory conference metadata only.
- Place the Take-home statement inside the white content area.
- Use Noto Sans for English scientific content and Noto Sans CJK SC for retained Chinese conference text.
- Use integer point sizes only. No auto-fit shrinking.
- Use dark navy for structure, teal for SARGE/correct outcomes, restrained red for wrong assembly/limitations, and gray for secondary material.

## Body layout

The white body follows five bands:

1. Take-home: one compact, non-rounded headline with emphasized “wrong event rows,” “5.1 points,” and “ExactRec”.
2. Motivation: native PowerPoint adaptation of paper Fig. 1.
3. Method: native PowerPoint adaptation of paper Fig. 2 plus one explicit prediction-unit annotation.
4. Results: overall table, 0–100 Single/Multi-Event connected-dot plot, and ExactRec diagnostic.
5. Conclusion: Gain, Diagnostic, Remaining limitation.

## Motivation figure

Reuse the scientific progression of `fig1_binding_gap_vector.pptx`:

- A: source evidence with highlighted shares, pledgees, and dates;
- B: recovered role values as an unordered pool;
- C: the same correct values assembled into WRONG versus CORRECT event rows.

Rebuild/restyle as native shapes rather than inserting a screenshot. The operational consequence is stated conservatively: cross-binding creates an internally incorrect counterparty–amount–date record. The figure remains an illustrative same-type case, not a claim that the reported Multi-Event subset contains only same-type events.

## Method figure

Reuse the icon-based structure of `fig2_sarge_pipeline_vector.pptx`:

`Document + closed schema + prompt-level cues → schema-grounded event-table contract → answer-token SFT / complete-row generation → post-generation schema check → fixed-slot event table`.

The figure must make four distinctions explicit:

- schema closure defines permitted event types, roles, and slot structure;
- surface candidates and copy-oriented instructions encourage source grounding but do not hard-constrain decoding;
- the supervised target and prediction unit are complete event rows;
- post-generation validation filters malformed/unlicensed structure and normalizes the fixed-slot table.

Use “helps preserve event identity,” not an absolute preservation claim. Remove the isolated seed-13 100% conformance slogan. Retain only a short subordinate implementation line.

Render the model-input equation with LaTeX as an image:

`x_D = [D; S; C_K(D); P_D; I_S]`.

## Results

- Expand Panel A to include representative Doc2EDAG, GIT, ProCNet, EPAL, SEELE, and SARGE rows with accepted-paper citations.
- Use the paper-supported wording “Numerically above listed baselines on ChFinAnn; below SEELE on DuEE-Fin.”
- Panel B uses a full 0–100 scale and labels “5.1 points over EPAL on ChFinAnn.”
- Define Multi-Event exactly as documents with more than one non-empty gold event record.
- Do not treat the general Multi-Event result as a direct same-type binding-error estimate.
- Rename Panel C’s derived column to `F1 − ExactRec`.
- Keep the paper’s 35.1 value as `35.1†`; explain briefly that it is the mean of per-seed gaps and displayed component means are rounded.
- Render `Δ_record = F_1 − ExactRec` with LaTeX as an image and state that it is a descriptive diagnostic, not a pure binding-error estimate.

## Conclusion

- Gain: supervising and generating complete records under a closed schema improves Multi-Event robustness.
- Diagnostic: ExactRec evaluates strict complete-row correctness beyond role-value F1.
- Remaining limitation: exact row assembly remains incomplete; do not add unsupported open-domain, cross-domain, or event-count degradation claims.

## Validation

- Build PPTX, PDF, and PNG from one revision.
- Verify exact output filenames and exactly three files in `final_v6`.
- Verify all font sizes are integer pt, all body content lies in the white template area, and all objects remain inside the slide.
- Verify native editability of the two scientific figures and result tables.
- Validate paper-backed values, citations, terminology, QR target, one-page PDF, embedded fonts, and PNG QR decoding.
- Inspect full resolution, 50%, 25%, and an A4-scaled rendering.

No commit, push, publication, or source-file overwrite is permitted.
