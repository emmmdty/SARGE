# SAGE-DEE v2 Full-Train / Test-Reference Freeze

This workspace is the clean paper-experiment freeze for SAGE-DEE v2 full-train
and test-reference evidence.

Start here:

- `docs/fulltrain_freeze/README.md`
- `docs/fulltrain_freeze/SAGE_DEE_V2_FULLTRAIN_PROCESS_RECORD.md`
- `docs/fulltrain_freeze/METRICS_SUMMARY.md`
- `docs/fulltrain_freeze/PAPER_EXPERIMENT_BOUNDARIES.md`
- `docs/fulltrain_freeze/METHOD_UPGRADE_REFERENCE.md`

The phase0-phase13 reports and v1 archive are no longer default working
context. Phase 13 is preserved only as a historical frozen boundary through
`docs/refactor/SAGE_V2_FINAL_TEST_RESULT.json`.

## Current Evidence

The compact freeze evidence separates:

- historical Phase 13 frozen final-test boundary;
- R3/R6/R7 full-train dev evidence;
- R8 ProcNet direct-comparable dev baseline;
- ProcNet-native test reference;
- S4 full-method test reference;
- CUBLAS determinism caveat.

The S4 full-method test-reference result has
`U-Text-F1-Strict F1 = 0.7502346830214657`, but it is a methodology reference,
not a formal frozen final result and not a reinterpretation of Phase 13.

Historical Phase 13 remains:

- `event_table_micro_f1 = 0.47374134889401553`
- `role_level_f1 = 0.47374134889401553`
- `exact_record_f1 = 0.05601436265709156`

## Boundaries

This repository must not claim SOTA, long-document SOTA, CCF-A readiness, or
SCI 1/2 readiness. ProcNet-native metrics are reference-only and are not the
formal main metric.

Do not run new training, Qwen inference, additional test, evaluator jobs, or
test-gold reads unless a later prompt explicitly authorizes that work. Do not
modify sibling `dee-eval`, ProcNet, existing canonical predictions, or existing
metrics.

Do not write evaluator handoff, canonical export, or GETM as algorithmic
contributions. Do not revive CSG/LESP/GETM/MRS as the current method story.

## Repository Shape

- `docs/fulltrain_freeze/`: active freeze entrypoint and paper-boundary docs.
- `docs/refactor/SAGE_V2_FINAL_TEST_RESULT.json`: immutable historical Phase 13
  boundary artifact kept for compatibility with guards/tests.
- `src/sage_dee/v2/`: v2 implementation retained for reproducibility.
- `scripts/v2/`: reproducibility and reference helpers retained.
- `configs/v2/`: retained configs used by reference helpers and tests.
- `tests/v2/`: retained unit/contract tests.

Large data, models, checkpoints, runs, outputs, caches, evaluator artifacts, and
server artifacts stay out of Git.

## Python

Never use bare `python`.

Local validation uses:

```bash
PATH=/home/tjk/miniconda3/envs/feg-dev-py310/bin:$PATH \
/home/tjk/miniconda3/envs/feg-dev-py310/bin/python -m pytest -q \
tests/v2/test_procnet_native_test_reference.py \
tests/v2/test_s4_full_method_test_reference.py
```

Server paths, artifact roots, and the CUBLAS determinism wrapper requirements
are recorded in `docs/fulltrain_freeze/ARTIFACT_INDEX.md` and
`docs/fulltrain_freeze/REPRODUCIBILITY_AND_DETERMINISM.md`.
