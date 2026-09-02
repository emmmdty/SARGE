# SARGE CCKS 2026 poster v5: redesign and validation record

This report records why v5 was rebuilt, what evidence the poster now presents, and
which checks still require a human before printing. The poster remains an English,
single-page, editable PowerPoint on the official CCKS 2026 portrait canvas.

## Reviewer diagnosis

The v4 poster did not let a passing reader recover the problem–method–result–limit
story in roughly 30 seconds. Its motivation was effectively one point, the core
schema-grounding mechanism occupied less space than the result blocks, and the
sections did not form a stable top-to-bottom reading order. Custom metrics appeared
before they were explained, while comparisons and ablations did not make their
experimental scope sufficiently visible. The many framed modules, mixed accent
colors, small qualifiers, and decorative styling weakened both hierarchy and
credibility. However, v4 did have useful strengths that the first v5 draft had
over-corrected away: proper mathematical typesetting, compact method stages,
large result callouts, and selective color emphasis. The final redesign retains
those strengths inside the clearer v5 narrative.

## V5 narrative and visual response

V5 uses one explicit sequence: take-home message → motivation → method → results →
conclusion. Motivation now gives three independent reasons for the work, an equity-
pledge row-binding counterexample, the research gap, and three concrete
contributions. The method is the largest scientific band and explains how the
closed schema governs licensed types, roles, source values, row identity, and the
post-generation schema check. The results then distinguish overall comparison,
multi-event robustness, same-backend SFT alignment, and separate record-level
diagnostics. Custom terms are defined where they first appear: the take-home
defines ExactRec, the motivation contribution defines Δrecord, and the method
input uses LaTeX-rendered D, S, C_K(D), and P_D beside plain-language labels. The
conclusion states the gain, what ExactRec diagnoses, and the remaining boundary.

The visual system now uses controlled contrast rather than flat white space: navy
section headings, teal/blue/violet mechanism highlights, coral only for the wrong
row and remaining limitation, and gray for baselines. Rounded shapes are limited
to small badges, highlight ribbons, and the three conclusion panels; there are no
shadows, gradients, or generic icons. Charts and table cells remain editable
PowerPoint shapes. Three high-resolution transparent formula images restore v4's
mathematical typography without rasterizing any scientific panel. The title is at
least 74 pt, authors 32 pt, affiliations 22 pt, main body text at least 22 pt,
chart/caption text 20 pt, and qualifiers 18 pt. All editable PowerPoint text uses
Arial, including the standard asterisk corresponding-author marker. The protected
Chinese conference footer retains the official template font.

## Metric provenance

- Overall F1 uses the listed papers' reported values: Doc2EDAG [18], ReDEE-RAAT [10], ProCNet
  [13], EPAL [7], SEELE [15], and SARGE. SARGE is 85.6 ± 0.4 on ChFinAnn and
  78.3 ± 0.4 on DuEE-Fin. The poster states the dataset-specific caveat plainly:
  SARGE is numerically above the listed ChFinAnn baselines but below SEELE on
  DuEE-Fin. Only SARGE is summarized as mean ± standard deviation over seeds
  13/17/42; the baseline bars are the papers' reported values.
- The ChFinAnn multi-event comparison shows EPAL at F1(S.) 89.7, F1(M.) 76.6,
  gap 13.1, versus SARGE at 89.2, 81.7, and 7.5. SARGE values are the mean over
  seeds 13/17/42; the comparison supports +5.1 F1(M.) and a 5.6-point smaller
  single-to-multiple gap.
- The alignment diagnostic is a same-backend, seed 13 comparison: ChFinAnn
  24.8 → 85.5 with vLLM-BF16 and DuEE-Fin 3.3 → 78.0 with HF-4bit. It is kept
  separate from the three-seed headline results.
- The record diagnostic is the mean over seeds 13/17/42: ChFinAnn F1 85.6,
  ExactRec 56.1, Δrecord 29.5; DuEE-Fin F1 78.3, ExactRec 43.3, reported
  Δrecord 35.1. The DuEE-Fin displayed means differ by 35.0 after rounding; 35.1
  is the paper's seed-level aggregate. Δrecord is not presented as a pure estimate
  of binding error because missing, extra, or wrong values and event-count errors
  also contribute.

## Quality assurance

The v5 validator checks the one-slide 88.90 × 109.22 cm canvas; official protected
footer signatures and media; type minima and the absence of shrink-to-fit; object
bounds; narrative order and method-band dominance; required and forbidden claims;
chart geometry, labels, values, error bars, seed/backend provenance; editable
native shapes; the three expected formula-image hashes and alt descriptions; QR
alt text and hyperlink; and the absence of body rasterization, shadows, generic
icons, and gradients across every non-template body shape. Full validation
additionally checks the one-page 2520 × 3096 pt PDF, embedded fonts and the
Yue Zhao¹²* header,
the 150 dpi PNG dimensions, and a decoded QR target of
`https://github.com/emmmdty/SARGE`.

The validator is v5-specific and verifies the three formula assets that the final
design intentionally reuses from v4. A `--pptx-only` mode supports fast source
checks, while `--all` covers PPTX, PDF, PNG, and QR. Both human-readable and JSON
output return a nonzero status on failure.

## Remaining print and manual checks

LibreOffice substitutes Arial with Liberation Sans in its PDF export on this WSL
environment; the editable PPTX still specifies Arial. Before final print, open the
PPTX on the presentation/print machine, confirm the intended Arial metrics or an
approved substitute, and recheck the three-line title, asterisk marker, formula
sharpness, mathematical symbols, and footer alignment at 100% zoom. Print one
reduced proof to verify that 18–20 pt qualifiers remain readable at viewing distance.
Scan the QR from both the
proof and the final 150 dpi image. Finally, confirm conference-specific author-symbol
and affiliation conventions with the organizer; these policy details cannot be
established by automated layout tests.
