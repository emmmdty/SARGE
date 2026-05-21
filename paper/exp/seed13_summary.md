# Seed13 Experiment Summary

This document contains test-only main comparison tables plus supporting ablation and diagnostic tables for seed13.

## Main Test Results

The following are test-only main comparison tables.

### Table 1. ChFinAnn

| ChFinAnn | P | R | F1 | F1(S) | F1(M) |
| --- | ---: | ---: | ---: | ---: | ---: |
| Doc2EDAG | 82.7 | 75.2 | 78.8 | 83.9 | 67.3 |
| DE-PPN | 83.7 | 76.4 | 79.9 | 85.9 | 68.4 |
| PTPCG | 83.7 | 75.4 | 79.4 | 88.2 | - |
| GIT | 82.3 | 78.4 | 80.3 | 87.6 | 72.3 |
| ReDEE | 83.9 | 79.9 | 81.9 | 88.7 | 74.1 |
| ProCNet | 83.6 | 78.1 | 80.8 | 87.5 | 73.5 |
| EPAL | 83.1 | 83.5 | 83.4 | 89.7 | 76.6 |
| SEELE | - | - | 85.1 | - | - |
| SARGE | 84.1 | 86.9 | 85.5 | 89.8 | 80.8 |

### Table 2. DuEE-Fin

| DuEE-Fin | P | R | F1 | F1(S) | F1(M) |
| --- | ---: | ---: | ---: | ---: | ---: |
| Doc2EDAG | 67.1 | 60.1 | 63.4 | 69.1 | 58.7 |
| DE-PPN | 69.0 | 33.5 | 45.1 | 54.2 | 21.8 |
| PTPCG | 71.0 | 61.7 | 66.0 | - | - |
| GIT | 69.8 | 65.9 | 67.8 | 73.7 | 63.8 |
| ReDEE | 77.0 | 72.0 | 74.4 | 78.9 | 70.6 |
| ProCNet | 79.3 | 71.4 | 75.1 | 80.1 | 71.0 |
| EPAL | 77.3 | 75.5 | 76.4 | 81.2 | 72.7 |
| SEELE | - | - | 80.8 | - | - |
| SARGE | 76.6 | 79.3 | 78.0 | 79.3 | 77.5 |

## Ablation Results

### Table 3. ChFinAnn Ablation

| Split | Factor | Setting | F1 | P | R | F1(S) | F1(M) | Note |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| dev (full-dev, 3204) | SFT | vLLM 0.8.5 BF16 no-SFT | 18.6 | - | - | - | - | 3.4 / 3.3 |
| dev (full-dev, 3204) | SFT | vLLM 0.8.5 BF16 SFT | 85.5 | - | - | - | - | delta=66.9 |
| dev (500) | backend | HF-4bin, k=1 greedy | 84.4 | - | - | - | - | 3.1 / 3.2 / 5 |
| dev (500) | backend | vLLM-bf16, k=1 greedy | 84.2 | - | - | - | - | delta=-0.3 |
| dev (full-dev, 3204) | decoding | vLLM 0.8.5 BF16 merged k1 | 85.5 | - | - | - | - | 3.3 / 3.5 / 6 |
| dev (full-dev, 3204) | decoding | vLLM 0.8.5 BF16 merged k4 T0.7 | 84.3 | - | - | - | - | 3.3 / 3.5 / 6 |
| test | no-SFT | vLLM BF16, k=1 greedy | 24.8 | 61.2 | 15.6 | 38.9 | 6.8 | SFT 是主要增益来源 |
| test | decoding | vLLM BF16, SFT | 84.2 | 79.5 | 89.5 | 87.5 | 80.7 | k=4 T=0.7 低于 k=1 主路径 1.26pp |

### Table 4. DuEE-Fin Ablation

| Split | Factor | Setting | F1 | P | R | F1(S) | F1(M) | Note |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| dev (500) | SFT | HF Transformers 4-bit NF4 + LoRA no-SFT | 3.8 | - | - | - | - | 2.1 / 2.9 |
| dev (500) | SFT | HF Transformers 4-bit NF4 + LoRA SFT | 76.7 | - | - | - | - | delta=72.8 |
| dev (500) | SFT | vLLM 0.8.5 BF16 merged no-SFT | 11.2 | - | - | - | - | 2.7 / 2.3 |
| dev (500) | SFT | vLLM 0.8.5 BF16 merged SFT | 72.8 | - | - | - | - | delta=61.5 |
| dev (500) | backend | HF-4bin, k=1 greedy | 76.7 | - | - | - | - | 2.9 / 2.3 / 5 |
| dev (500) | backend | vLLM-bf16, k=1 greedy | 72.8 | - | - | - | - | delta=-3.9 |
| dev (500) | decoding | vLLM 0.8.5 BF16 merged k1 | 72.8 | - | - | - | - | 2.3 / 2.5 / 2.6 / 2.4 / 6 |
| dev (500) | decoding | vLLM 0.8.5 BF16 merged k4 T0.3 | 73.9 | - | - | - | - | 2.3 / 2.5 / 2.6 / 2.4 / 6 |
| dev (500) | decoding | vLLM 0.8.5 BF16 merged k4 T0.5 | 72.7 | - | - | - | - | 2.3 / 2.5 / 2.6 / 2.4 / 6 |
| dev (500) | decoding | vLLM 0.8.5 BF16 merged k4 T0.7 | 72.3 | - | - | - | - | 2.3 / 2.5 / 2.6 / 2.4 / 6 |
| test | backend | SFT, k=1 greedy | 73.5 | 74.0 | 73.0 | 77.2 | 72.0 | vLLM BF16 比 HF 4-bit 主路径低 4.42pp |
| test | no-SFT | vLLM BF16, k=1 greedy | 11.3 | 37.2 | 6.7 | 13.8 | 9.4 | SFT 是主要增益来源 |
| test | decoding | vLLM BF16, SFT | 73.1 | 69.2 | 77.5 | 75.8 | 72.5 | k=4 T=0.7 未优于 vLLM k=1 |
| test | LRD | no-LRD | 78.0 | 76.6 | 79.3 | 79.3 | 77.5 | docs/exp_result.md 7.2 |
| test | LRD | safe-anchor | 78.0 | 76.7 | 79.3 | 79.4 | 77.5 | delta=0.0 |
| dev | LRD | safe-anchor tau=0.90 | 76.8 | - | - | - | 75.5 | docs/exp_result.md 7 |

## Unified Diagnostic Results

### Table 5. Legacy-FS vs Unified

| Dataset | Split | Run | Legacy-FS | Unified | DocFEE | ExactRec |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| ChFinAnn | dev | SARGE | 85.5 | 87.0 | 86.4 | 56.0 |
| ChFinAnn | test | SARGE | 85.5 | 86.9 | 86.0 | 55.8 |
| DuEE-Fin | test | SARGE no-LRD | 78.0 | 78.9 | 77.7 | 42.8 |
| DuEE-Fin | test | SARGE LRD | 78.0 | 78.9 | 77.8 | 42.9 |
| DuEE-Fin | dev | SARGE | 76.7 | 77.2 | 76.8 | 41.8 |

## Event-Level Results

### Table 6. ChFinAnn Event F1

| ChFinAnn Event | EPAL | SEELE | SARGE | Delta EPAL | Delta SEELE |
| --- | ---: | ---: | ---: | ---: | ---: |
| EquityFreeze | 74.8 | 78.8 | 76.5 | 1.7 | -2.3 |
| EquityRepurchase | 93.4 | 92.0 | 94.6 | 1.2 | 2.6 |
| EquityUnderweight | 76.3 | 77.7 | 84.9 | 8.6 | 7.2 |
| EquityOverweight | 77.3 | 82.4 | 80.4 | 3.1 | -2.0 |
| EquityPledge | 81.5 | 83.1 | 83.5 | 2.0 | 0.4 |

### Table 7. DuEE-Fin Event F1

| DuEE-Fin Event | EPAL | SEELE | SARGE | Delta EPAL | Delta SEELE |
| --- | ---: | ---: | ---: | ---: | ---: |
| 公司上市 | 59.1 | 66.5 | 64.1 | 5.0 | -2.4 |
| 股东减持 | 74.5 | 76.7 | 76.7 | 2.2 | 0.0 |
| 股东增持 | 57.5 | 75.5 | 71.5 | 14.0 | -4.0 |
| 企业收购 | 68.3 | 72.1 | 72.2 | 3.9 | 0.1 |
| 企业融资 | 76.1 | 79.1 | 77.6 | 1.5 | -1.5 |
| 股份回购 | 91.3 | 94.8 | 91.0 | -0.3 | -3.8 |
| 质押 | 78.2 | 85.3 | 79.5 | 1.3 | -5.8 |
| 解除质押 | 76.8 | 84.8 | 79.2 | 2.4 | -5.6 |
| 企业破产 | 69.3 | 62.0 | 67.4 | -1.9 | 5.4 |
| 亏损 | 86.1 | 86.2 | 83.9 | -2.2 | -2.3 |
| 被约谈 | 71.1 | 58.0 | 70.3 | -0.8 | 12.3 |
| 中标 | 76.3 | 76.6 | 76.9 | 0.6 | 0.3 |
| 高管变动 | 61.2 | 64.8 | 63.4 | 2.2 | -1.4 |

## Training And Artifacts

### Table 8. Training Summary

| Dataset | Seed | Epochs | Train docs | Train events | Loss | Time | GPU | Run |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| DuEE-Fin | 13 | 2 | 6515 | 8824 | 0.0791 | 166 min | 0 | runs/sarge_sft_DuEE_Fin_dev500_s13_ep2_gpu0/ |
| ChFinAnn | 13 | 2 | 25632 | 38088 | 0.0202 | 505 min | 1 | runs/sarge_sft_ChFinAnn_Doc2EDAG_s13_ep2_gpu1/ |

### Table 9. Artifact Index

| Dataset | Split | Type | Docs | Events | Path | Status |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| ChFinAnn | test | legacy snapshot | - | - | paper/exp/data/data_snapshot/chfinann_test_legacy.json | present |
| ChFinAnn | test | unified snapshot | - | - | paper/exp/data/data_snapshot/chfinann_test_unified.json | present |
| DuEE-Fin | test | legacy snapshot | - | - | paper/exp/data/data_snapshot/dueefin_test_legacy.json | present |
| DuEE-Fin | test | unified snapshot | - | - | paper/exp/data/data_snapshot/dueefin_test_unified.json | present |
| DuEE-Fin | test | LRD legacy snapshot | - | - | paper/exp/data/data_snapshot/dueefin_test_lrd_legacy.json | present |
| DuEE-Fin | test | LRD unified snapshot | - | - | paper/exp/data/data_snapshot/dueefin_test_lrd_unified.json | present |
| All | all | ablation evidence | - | - | paper/exp/data/ablation_evidence.json | present |

## Output Diagnostics

### Table 10. Robustness Diagnostics

| Dataset | Split | Run | SchemaOK | ParseFail | InvType | InvRole | ValidRec | Exact | ExactRec |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| ChFinAnn | dev | SARGE | 100.0 | 0 | 0 | 0 | 10207 | 2856 | 56.0 |
| ChFinAnn | test | SARGE | 100.0 | 0 | 0 | 0 | 9637 | 2689 | 55.8 |
| DuEE-Fin | test | SARGE no-LRD | 100.0 | 0 | 0 | 0 | 3090 | 662 | 42.8 |
| DuEE-Fin | test | SARGE LRD | 100.0 | 0 | 0 | 0 | 3088 | 662 | 42.9 |
| DuEE-Fin | dev | SARGE | 100.0 | 0 | 0 | 0 | - | - | 41.8 |

## F1 Definitions

Legacy-FS F1 is the fixed-schema role-slot micro-F1 used for the main EPAL/SEELE comparison. After event-type constrained record matching, role slots are counted as TP, FP, or FN, then F1 is computed from precision and recall.

Unified F1 is a strict canonical JSONL role-value metric with event-type constrained global bipartite matching. It is useful for same-format diagnostics and ExactRec analysis, but it is not used in the public baseline comparison tables.

## Notes

- All values are percentages.
- Published baseline rows are from EPAL and SEELE reported test-set tables.
- `F1(S)` means single-event F1; `F1(M)` means multi-event F1.
- `-` means not reported or unavailable.
- `HF-4bin` means HF Transformers with 4-bit NF4 quantization and LoRA adapter.
- `vLLM-bf16` means vLLM with BF16 merged weights.
- Main tables use fixed-slot / Legacy-FS only.
- Unified F1 uses strict canonical JSONL matching and is reported only in the diagnostic table.
- ExactRec is recomputed as `2 * exact_matches / validated_records`.
