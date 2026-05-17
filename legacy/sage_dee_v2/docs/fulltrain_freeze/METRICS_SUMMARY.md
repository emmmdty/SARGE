# Metrics Summary

All rows below preserve their original scope. Do not compare rows across metric
families unless the paper text explicitly explains the protocol difference.

## A. Historical Boundary Only: Phase 13 Frozen Final Test

| Scope | Metric | Value | Status | Paper-use note |
| --- | --- | ---: | --- | --- |
| Phase 13 frozen final test | event_table_micro_f1 | 0.47374134889401553 | locked | historical boundary only |
| Phase 13 frozen final test | role_level_f1 | 0.47374134889401553 | locked | historical boundary only |
| Phase 13 frozen final test | exact_record_f1 | 0.05601436265709156 | locked | historical boundary only |
| Phase 13 frozen final test | canonical_rows | 1171 | locked | diagnostic count |
| Phase 13 frozen final test | canonical_event_count | 1252 | locked | diagnostic count |
| Phase 13 frozen final test | evaluator_validation_ok | true | locked | validation evidence |

## B. Full-Train Dev Evidence

| Scope | Metric | Value | Status | Paper-use note |
| --- | --- | ---: | --- | --- |
| R3 S4 full/max dev | train_limit | 6474 | completed | full available train count |
| R3 S4 full/max dev | event/role F1 | 0.7373271889400921 | dev-only | undertraining evidence |
| R3 S4 full/max dev | exact-record F1 | 0.35224760501105373 | dev-only | record-level evidence |
| R6 S4 full/max dev | event/role F1 mean | 0.733894 | dev-only | seed stability evidence |
| R6 S4 full/max dev | event/role F1 std | 0.002979 | dev-only | seed stability evidence |
| R6 S4 full/max dev | exact-record F1 mean | 0.360929 | dev-only | seed stability evidence |
| R6 S4 full/max dev | exact-record F1 std | 0.006521 | dev-only | seed stability evidence |

## C. R7 S2/S3/S4 Matrix

| Scope | Metric | Value | Status | Paper-use note |
| --- | --- | ---: | --- | --- |
| R7 S2 dev matrix | event/role mean | 0.622027 | dev-only | schema-only baseline |
| R7 S2 dev matrix | exact mean | 0.128487 | dev-only | schema-only baseline |
| R7 S3 dev matrix | event/role mean | 0.730298 | dev-only | role-safe contract gain |
| R7 S3 dev matrix | exact mean | 0.344182 | dev-only | role-safe contract gain |
| R7 S4 dev matrix | event/role mean | 0.733894 | dev-only | full method dev row |
| R7 S4 dev matrix | exact mean | 0.360929 | dev-only | full method dev row |
| R7 S3 - S2 | event/role delta | 0.108271 | dev-only | role-safe effect |
| R7 S3 - S2 | exact delta | 0.215696 | dev-only | role-safe effect |
| R7 S4 - S3 | event/role delta | 0.003597 | dev-only | surface memory auxiliary gain |
| R7 S4 - S3 | exact delta | 0.016746 | dev-only | surface memory auxiliary gain |

## D. R8 ProcNet Comparable Dev Baseline

| Scope | Metric | Value | Status | Paper-use note |
| --- | --- | ---: | --- | --- |
| R8 ProcNet dev comparison | ProcNet mean strict F1 | 0.693720 | direct-comparable dev | baseline row |
| R8 ProcNet dev comparison | ProcNet mean exact-record F1 | 0.212657 | direct-comparable dev | baseline row |
| R8 ProcNet dev comparison | SAGE S4 mean event/role F1 | 0.733894 | dev-only | SAGE comparison row |
| R8 ProcNet dev comparison | SAGE S4 mean exact-record F1 | 0.360929 | dev-only | SAGE comparison row |
| R8 ProcNet dev comparison | thesis_table_ready | true | completed | conservative table ready |
| R8 ProcNet dev comparison | ccfa_claim_ready | false | boundary | not CCF-A / SCI 1/2 ready |

## E. S4 Full-Method Test Reference

| Scope | Metric | Value | Status | Paper-use note |
| --- | --- | ---: | --- | --- |
| S4 full-method test reference | U-Text-F1-Strict precision | 0.7425668979187314 | methodology reference | non-formal metric |
| S4 full-method test reference | U-Text-F1-Strict recall | 0.7580624762868344 | methodology reference | non-formal metric |
| S4 full-method test reference | U-Text-F1-Strict F1 | 0.7502346830214657 | methodology reference | non-formal metric |
| S4 full-method test reference | TP / FP / FN | 5994 / 2078 / 1913 | methodology reference | count evidence |
| S4 full-method test reference | record exact F1 | 0.37894736842105264 | auxiliary | record-level bottleneck |
| S4 full-method test reference | record soft 0.8 F1 | 0.5993421052631579 | auxiliary | record-level auxiliary |
| S4 full-method test reference | event count accuracy | 0.7022653721682848 | auxiliary | event-count diagnostic |
| S4 full-method test reference | ProcNet-native micro F1 | 0.7340111511971138 | reference-only | not main formal metric |
| S4 full-method test reference | canonical rows | 1171 | validation | generation count |
| S4 full-method test reference | canonical_event_count | 1507 | validation | generation count |
| S4 full-method test reference | canonical_schema_errors | 0 | validation | schema gate |
| S4 full-method test reference | forbidden_key_violations | 0 | validation | canonical gate |
| S4 full-method test reference | unified_validation_ok | true | validation | evaluator validation |
| S4 full-method test reference | methodology_reference | true | boundary | independent reference |
| S4 full-method test reference | formal_metric | false | boundary | not official final |
| S4 full-method test reference | frozen_final_result | false | boundary | not Phase 13 |
| S4 full-method test reference | phase13_reinterpretation | false | boundary | no reinterpretation |

## F. ProcNet-Native Reference Metrics

| Scope | Metric | Value | Status | Paper-use note |
| --- | --- | ---: | --- | --- |
| ProcNet-native Phase13 test reference | micro precision | 0.49322815895222505 | reference-only | native scorer on Phase 13 prediction |
| ProcNet-native Phase13 test reference | micro recall | 0.4399309703969202 | reference-only | native scorer on Phase 13 prediction |
| ProcNet-native Phase13 test reference | micro F1 | 0.46505753578445125 | reference-only | not formal metric |
| ProcNet-native Phase13 test reference | native_reference_only | true | boundary | not main metric |
| ProcNet-native Phase13 test reference | formal_metric | false | boundary | not official final |
