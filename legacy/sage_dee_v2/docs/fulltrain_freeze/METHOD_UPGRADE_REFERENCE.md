# Method Upgrade Reference

This document records method-upgrade implications from the full-train and
test-reference evidence.

## Established Components

- The role-safe contract is effective and should remain a core component.
- Full training makes role-level extraction substantially stronger.
- Surface memory provides a small auxiliary gain, especially for exact-record
  behavior, but it is not a main contribution by itself.

## Bottlenecks

- Record exact matching remains much weaker than role-level extraction.
- Event grouping and record binding remain the major bottlenecks.
- Multi-event assembly remains unresolved.
- A simple rule planner has already been tested as not promising enough for the
  main line.

## Upgrade Direction

Future method work should focus on:

- evidence-state modeling;
- event-level planning;
- record binding;
- multi-event assembly;
- stronger handling of cross-sentence and multi-record evidence.

## Do Not Do

- Do not continue piling regex surface memory as the main method.
- Do not treat evaluator behavior as algorithmic innovation.
- Do not treat canonical export as algorithmic innovation.
- Do not treat GETM as a new backbone or core algorithmic contribution.
- Do not revive CSG/LESP/GETM/MRS four-stage legacy narration as the main
  method story.
- Do not use schema alias mapping, role guessing, event type guessing,
  gold-based repair, semantic-equivalence scoring, or LLM-judge scoring as the
  main evaluation path.

## Paper-Safe Method Framing

The safe current framing is a controlled generation framework with a role-safe
schema contract, auxiliary document-local surface memory, strict canonical
export, and external evaluator handoff. The method-upgrade gap is event-level
state and record assembly, not more surface regex rules.
