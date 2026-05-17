# SAGE-DEE v2 Full-Train Process Record

## Status

This is a compact record of the full-train / test-reference freeze. It condenses
the evidence needed for paper-experiment analysis and removes phase-history bulk
from the default reading path.

No new training, Qwen inference, evaluator run, test split run, test-gold read,
canonical prediction edit, metric edit, ProcNet edit, or `dee-eval` edit is part
of this freeze.

## Historical Frozen Phase 13 Boundary

Phase 13 remains the locked historical frozen final-test result for the earlier
vFinal-frozen system. It is not the full-train main evidence and must not be
reinterpreted by later test-reference results.

Locked Phase 13 facts:

| Field | Value |
| --- | ---: |
| event_table_micro_f1 | 0.47374134889401553 |
| role_level_f1 | 0.47374134889401553 |
| exact_record_f1 | 0.05601436265709156 |
| canonical_rows | 1171 |
| canonical_event_count | 1252 |
| evaluator_validation_ok | true |

Paper-use note: cite as a historical boundary and negative motivation only. Do
not mix it into the full-train headline metric narrative.

## v2.1 Full-Train Dev Evidence

R3 established that undertraining was the dominant failure mode for the earlier
S4 result. Row D used full available train count `6474` on
`DuEE-Fin-dev500/dev` and reached:

| Metric | Value |
| --- | ---: |
| event/role F1 | 0.7373271889400921 |
| exact-record F1 | 0.35224760501105373 |

R6 extended the full/max S4 evidence to seeds 42/43/44:

| Metric | Mean | Std |
| --- | ---: | ---: |
| event/role F1 | 0.733894 | 0.002979 |
| exact-record F1 | 0.360929 | 0.006521 |

Status: dev-only evidence. It did not run test and did not modify the frozen
Phase 13 result.

## R7 Thesis Matrix

R7 compared S2/S3/S4 under full/max dev conditions and reused S4 evidence
read-only.

| System | Event/role mean | Exact mean | Paper-use note |
| --- | ---: | ---: | --- |
| S2 | 0.622027 | 0.128487 | schema-only baseline |
| S3 | 0.730298 | 0.344182 | role-safe contract effect |
| S4 | 0.733894 | 0.360929 | role-safe plus surface memory |

| Delta | Event/role delta | Exact delta |
| --- | ---: | ---: |
| S3 - S2 | 0.108271 | 0.215696 |
| S4 - S3 | 0.003597 | 0.016746 |

Interpretation: role-safe contract is a strong component; surface memory is an
auxiliary exact-record gain, not a standalone main contribution.

## R8 ProcNet Comparable Dev Baseline

R8 compared ProcNet under the same `DuEE-Fin-dev500/dev` split, sibling
`dee-eval`, and SAGE canonical contract. Native ProcNet scores were kept
reference-only.

| System | Strict/event F1 | Exact-record F1 | Status |
| --- | ---: | ---: | --- |
| ProcNet mean | 0.693720 | 0.212657 | direct-comparable dev baseline |
| SAGE S4 mean | 0.733894 | 0.360929 | SAGE full/max dev row |

Verdict fields: `thesis_table_ready=true`, `ccfa_claim_ready=false`.

Paper-use note: suitable for a conservative thesis or SCI/EI indexed opportunity
analysis table. Not enough for SOTA, CCF-A, or SCI 1/2 claims.

## ProcNet-Native Test Reference

The ProcNet-native Phase13 test reference scores the existing Phase 13 canonical
prediction with ProcNet's native table-filling scorer. It is not formal, not
frozen-final, not a Phase 13 rerun, and not a replacement for the unified
strict metric.

| Metric | Value |
| --- | ---: |
| micro precision | 0.49322815895222505 |
| micro recall | 0.4399309703969202 |
| micro F1 | 0.46505753578445125 |

Flags: `native_reference_only=true`, `formal_metric=false`.

## S4 Full-Method Test Reference

The S4 full-method test reference evaluates the R3 Row D
`s4_full_or_max_frozen_surface` method on test for methodology comparison. It is
an independent methodology-reference branch result, not a formal metric and not
a frozen final result.

| Metric | Value |
| --- | ---: |
| U-Text-F1-Strict precision | 0.7425668979187314 |
| U-Text-F1-Strict recall | 0.7580624762868344 |
| U-Text-F1-Strict F1 | 0.7502346830214657 |
| TP / FP / FN | 5994 / 2078 / 1913 |
| record exact F1 | 0.37894736842105264 |
| record soft 0.8 F1 | 0.5993421052631579 |
| event count accuracy | 0.7022653721682848 |
| ProcNet-native micro F1 | 0.7340111511971138 |
| canonical rows | 1171 |
| canonical_event_count | 1507 |
| canonical_schema_errors | 0 |
| forbidden_key_violations | 0 |
| unified_validation_ok | true |

Flags: `methodology_reference=true`, `formal_metric=false`,
`frozen_final_result=false`, `phase13_reinterpretation=false`.

## CUBLAS Determinism Warning

R6 logs reported PyTorch deterministic warn-only messages related to
`CUBLAS_WORKSPACE_CONFIG`. This is a bit-level determinism and strict
reproducibility caveat, not evidence that existing artifact-level metrics are
wrong.

Future training, inference, and evaluation shell wrappers must set before
Python starts:

```bash
export CUBLAS_WORKSPACE_CONFIG=:4096:8
export PYTHONHASHSEED=42
```

Do not rerun existing test-reference results automatically because of this
warning.
