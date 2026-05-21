# Experiment Asset Summary

This document contains test-only main comparison tables plus supporting ablation, diagnostic, and asset-status tables. Values come from checked-in run snapshots and `asset_registry.json`.

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
| SARGE | 84.4 | 87.7 | 86.0 | 89.9 | 81.8 |

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
| test | SFT | vLLM-bf16 no-SFT | 24.8 | 61.2 | 15.6 | 38.9 | 6.8 | No-SFT test baseline. |
| test | backend | HF-4bin + LoRA k1 | 86.0 | 84.4 | 87.7 | 89.9 | 81.8 | main ChFinAnn backend |
| test | backend | vLLM-bf16 + LoRA k1 | 85.5 | 84.1 | 86.9 | 89.8 | 80.8 | backend cross-check |
| test | decoding | vLLM-bf16 + LoRA k4 T0.7 | 84.2 | 79.5 | 89.5 | 87.5 | 80.7 | Sampling decoding ablation. |

### Table 4. DuEE-Fin Ablation

| Split | Factor | Setting | F1 | P | R | F1(S) | F1(M) | Note |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| test | SFT | HF-4bin no-SFT | 3.3 | 44.8 | 1.7 | 3.7 | 3.0 | HF no-SFT test baseline completed after earlier docs were written. |
| test | SFT | vLLM-bf16 no-SFT | 11.3 | 37.2 | 6.7 | 13.8 | 9.4 | vLLM no-SFT test baseline. |
| test | backend | HF-4bin + LoRA k1 | 78.0 | 76.6 | 79.3 | 79.3 | 77.5 | main DuEE-Fin backend |
| test | backend | vLLM-bf16 + LoRA k1 | 73.5 | 74.0 | 73.1 | 77.2 | 72.0 | backend cross-check |
| test | decoding | vLLM-bf16 + LoRA k4 T0.7 | 73.1 | 69.2 | 77.5 | 75.8 | 72.5 | Sampling decoding ablation. |
| test | LRD | no-LRD | 78.0 | 76.6 | 79.3 | 79.3 | 77.5 | Primary DuEE-Fin test result; no-LRD remains the main path. |
| test | LRD | safe-anchor tau=0.90 | 78.0 | 76.7 | 79.3 | 79.4 | 77.5 | LRD diagnostic; gain is negligible and it is not the main method. |
| dev | LRD | invalid k4-pool diagnostic | 33.5 | 21.3 | 78.6 | 31.7 | 35.5 | not comparable; FP explosion from candidate-pool misuse |

## Unified Diagnostic Results

### Table 5. Legacy-FS vs Unified

| Dataset | Split | Run | Legacy-FS | Unified | DocFEE | ExactRec | Status |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| ChFinAnn | test | chfinann_test_seed13_hf4bin_k1 | 86.0 | 87.4 | 86.5 | 58.4 | main |
| ChFinAnn | test | chfinann_test_seed13_vllm_bf16_k1 | 85.5 | 86.9 | 86.0 | 55.8 | ablation |
| DuEE-Fin | test | dueefin_test_seed13_hf4bin_k1_no_lrd | 78.0 | 78.9 | 77.7 | 42.8 | main |
| DuEE-Fin | test | dueefin_test_seed13_hf4bin_k1_lrd | 78.0 | 78.9 | 77.8 | 42.9 | diagnostic |
| DuEE-Fin | dev | dueefin_dev_seed13_hf4bin_k1 | 76.7 | 77.2 | 76.7 | 41.7 | diagnostic |
| DuEE-Fin | dev | dueefin_dev_seed17_train_sft_mrs_no_lrd | 77.9 | 78.5 | 78.1 | 41.9 | diagnostic |
| DuEE-Fin | dev | dueefin_dev_seed42_train_sft_mrs_no_lrd | 76.7 | 77.4 | 76.9 | 41.9 | diagnostic |
| DuEE-Fin | dev | dueefin_dev_seed17_lrd_invalid_k4_pool | 33.5 | 34.6 | 34.6 | 18.1 | invalid |

## Event-Level Results

### Table 6. ChFinAnn Event F1

| ChFinAnn Event | EPAL | SEELE | SARGE | Delta EPAL | Delta SEELE |
| --- | ---: | ---: | ---: | ---: | ---: |
| EquityFreeze | 74.8 | 78.8 | 78.6 | 3.8 | -0.2 |
| EquityRepurchase | 93.4 | 92.0 | 95.1 | 1.7 | 3.1 |
| EquityUnderweight | 76.3 | 77.7 | 85.8 | 9.5 | 8.1 |
| EquityOverweight | 77.3 | 82.4 | 81.3 | 4.0 | -1.1 |
| EquityPledge | 81.5 | 83.1 | 83.8 | 2.3 | 0.7 |

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

| Dataset | Seed | Epochs | Train docs | Train events | Time | Run | Status |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| DuEE-Fin | 13 | 2 | 6515 | - | 166.2 min | runs/sarge_sft_DuEE_Fin_dev500_s13_ep2_gpu0 | completed |
| DuEE-Fin | 17 | 2 | 6515 | - | 164.0 min | runs/sarge_sft_DuEE_Fin_dev500_s17_ep2_gpu0 | completed |
| DuEE-Fin | 42 | 2 | 6515 | - | 167.1 min | runs/sarge_sft_DuEE_Fin_dev500_s42_ep2_gpu1 | completed |
| ChFinAnn | 13 | 2 | 25632 | - | 505.2 min | runs/sarge_sft_ChFinAnn_Doc2EDAG_s13_ep2_gpu1 | completed |

### Table 9. Artifact Index

| Dataset | Split | Asset | Status | Role | Snapshot | Main |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| ChFinAnn | test | chfinann_test_seed13_hf4bin_k1 | main | main_result | paper/exp/data/run_snapshots/chfinann_test_seed13_hf4bin_k1 | yes |
| DuEE-Fin | test | dueefin_test_seed13_hf4bin_k1_no_lrd | main | main_result | paper/exp/data/run_snapshots/dueefin_test_seed13_hf4bin_k1_no_lrd | yes |
| DuEE-Fin | test | dueefin_test_seed13_hf4bin_k1_lrd | diagnostic | lrd_test_diagnostic | paper/exp/data/run_snapshots/dueefin_test_seed13_hf4bin_k1_lrd | no |
| ChFinAnn | test | chfinann_test_seed13_vllm_bf16_k1 | ablation | backend_crosscheck | paper/exp/data/run_snapshots/chfinann_test_seed13_vllm_bf16_k1 | no |
| ChFinAnn | test | chfinann_test_seed13_vllm_bf16_k4_t07 | ablation | decoding_ablation | paper/exp/data/run_snapshots/chfinann_test_seed13_vllm_bf16_k4_t07 | no |
| ChFinAnn | test | chfinann_test_seed13_vllm_bf16_no_sft | ablation | sft_ablation | paper/exp/data/run_snapshots/chfinann_test_seed13_vllm_bf16_no_sft | no |
| DuEE-Fin | test | dueefin_test_seed13_hf4bin_no_sft | ablation | sft_ablation | paper/exp/data/run_snapshots/dueefin_test_seed13_hf4bin_no_sft | no |
| DuEE-Fin | test | dueefin_test_seed13_vllm_bf16_k1 | ablation | backend_crosscheck | paper/exp/data/run_snapshots/dueefin_test_seed13_vllm_bf16_k1 | no |
| DuEE-Fin | test | dueefin_test_seed13_vllm_bf16_k4_t07 | ablation | decoding_ablation | paper/exp/data/run_snapshots/dueefin_test_seed13_vllm_bf16_k4_t07 | no |
| DuEE-Fin | test | dueefin_test_seed13_vllm_bf16_no_sft | ablation | sft_ablation | paper/exp/data/run_snapshots/dueefin_test_seed13_vllm_bf16_no_sft | no |
| DuEE-Fin | dev | dueefin_dev_seed13_hf4bin_k1 | diagnostic | dev_reference | paper/exp/data/run_snapshots/dueefin_dev_seed13_hf4bin_k1 | no |
| DuEE-Fin | dev | dueefin_dev_seed13_hf4bin_k1_lrd | diagnostic | lrd_dev_reference | paper/exp/data/run_snapshots/dueefin_dev_seed13_hf4bin_k1_lrd | no |
| DuEE-Fin | dev | dueefin_dev_seed17_train_sft_mrs_no_lrd | diagnostic | seed_extension_dev | paper/exp/data/run_snapshots/dueefin_dev_seed17_train_sft_mrs_no_lrd | no |
| DuEE-Fin | dev | dueefin_dev_seed42_train_sft_mrs_no_lrd | diagnostic | seed_extension_dev | paper/exp/data/run_snapshots/dueefin_dev_seed42_train_sft_mrs_no_lrd | no |
| DuEE-Fin | dev | dueefin_dev_seed17_lrd_invalid_k4_pool | invalid | contract_misuse_diagnostic | paper/exp/data/run_snapshots/dueefin_dev_seed17_lrd_invalid_k4_pool | no |
| DuEE-Fin | train | dueefin_train_seed13 | training | training_asset_completed | paper/exp/data/run_snapshots/dueefin_train_seed13 | no |
| DuEE-Fin | train | dueefin_train_seed17 | training | training_asset_completed | paper/exp/data/run_snapshots/dueefin_train_seed17 | no |
| DuEE-Fin | train | dueefin_train_seed42 | training | training_asset_completed | paper/exp/data/run_snapshots/dueefin_train_seed42 | no |
| ChFinAnn | train | chfinann_train_seed13 | training | training_asset_completed | paper/exp/data/run_snapshots/chfinann_train_seed13 | no |
| DuEE-Fin | test | dueefin_test_seed17_hf4bin_k1_running | running | seed_extension_test | - | no |
| DuEE-Fin | test | dueefin_test_seed42_hf4bin_k1_running | running | seed_extension_test | - | no |
| ChFinAnn | train | chfinann_train_seed17_running | training | seed_extension_train | - | no |
| ChFinAnn | train | chfinann_train_seed42_queued | training | seed_extension_train | - | no |

## Output Diagnostics

### Table 10. Robustness Diagnostics

| Dataset | Split | Run | SchemaOK | ParseFail | InvType | InvRole | ValidRec | Exact | ExactRec | Status |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| ChFinAnn | test | chfinann_test_seed13_hf4bin_k1 | 100.0 | 0 | 0 | 0 | 9640 | 2816 | 58.4 | main |
| DuEE-Fin | test | dueefin_test_seed13_hf4bin_k1_no_lrd | 100.0 | 0 | 0 | 0 | 3090 | 662 | 42.8 | main |
| DuEE-Fin | test | dueefin_test_seed13_hf4bin_k1_lrd | 100.0 | 0 | 0 | 0 | 3088 | 662 | 42.9 | diagnostic |
| ChFinAnn | test | chfinann_test_seed13_vllm_bf16_k1 | 100.0 | 0 | 0 | 0 | 9637 | 2689 | 55.8 | ablation |
| ChFinAnn | test | chfinann_test_seed13_vllm_bf16_k4_t07 | 100.0 | 0 | 0 | 0 | 9933 | 2729 | 54.9 | ablation |
| ChFinAnn | test | chfinann_test_seed13_vllm_bf16_no_sft | 100.0 | 0 | 0 | 0 | 6330 | 323 | 10.2 | ablation |
| DuEE-Fin | test | dueefin_test_seed13_hf4bin_no_sft | 100.0 | 0 | 0 | 0 | 2443 | 0 | 0.0 | ablation |
| DuEE-Fin | test | dueefin_test_seed13_vllm_bf16_k1 | 100.0 | 0 | 0 | 0 | 2986 | 561 | 37.6 | ablation |
| DuEE-Fin | test | dueefin_test_seed13_vllm_bf16_k4_t07 | 100.0 | 0 | 0 | 0 | 3170 | 550 | 34.7 | ablation |
| DuEE-Fin | test | dueefin_test_seed13_vllm_bf16_no_sft | 100.0 | 0 | 0 | 0 | 2333 | 3 | 0.3 | ablation |
| DuEE-Fin | dev | dueefin_dev_seed13_hf4bin_k1 | 100.0 | 0 | 0 | 0 | 1351 | 282 | 41.7 | diagnostic |
| DuEE-Fin | dev | dueefin_dev_seed13_hf4bin_k1_lrd | 100.0 | 0 | 0 | 0 | 1349 | 282 | 41.8 | diagnostic |
| DuEE-Fin | dev | dueefin_dev_seed17_train_sft_mrs_no_lrd | 100.0 | 0 | 0 | 0 | 1347 | 282 | 41.9 | diagnostic |
| DuEE-Fin | dev | dueefin_dev_seed42_train_sft_mrs_no_lrd | 100.0 | 0 | 0 | 0 | 1352 | 283 | 41.9 | diagnostic |
| DuEE-Fin | dev | dueefin_dev_seed17_lrd_invalid_k4_pool | 100.0 | 0 | 0 | 0 | 3118 | 282 | 18.1 | invalid |

### Table 11. Active And Invalid Assets

| Asset | Dataset | Split | Seed | Status | Log | Note |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| dueefin_dev_seed17_lrd_invalid_k4_pool | DuEE-Fin | dev | 17 | invalid | - | Invalid for model comparison: postprocess flattened all k=4 candidates (2692 events in, 2444 out), causing FP explosion. |
| dueefin_test_seed17_hf4bin_k1_running | DuEE-Fin | test | 17 | running | logs/sarge_infer_DuEE-Fin-dev500_test_seed17_4bitNF4_k1_20260521T2141Z.log | Running on GPU0 at registry creation; do not enter main table until eval exists. |
| dueefin_test_seed42_hf4bin_k1_running | DuEE-Fin | test | 42 | running | logs/sarge_infer_DuEE-Fin-dev500_test_seed42_4bitNF4_k1_20260521T2221Z.log | Running on GPU0 at registry creation; do not enter main table until eval exists. |
| chfinann_train_seed17_running | ChFinAnn | train | 17 | training | logs/sarge_sft_ChFinAnn-Doc2EDAG_s17_ep2_gpu1_20260521T143813Z.log | Running on GPU1 at registry creation; queue will start seed42 after completion. |
| chfinann_train_seed42_queued | ChFinAnn | train | 42 | training | logs/sarge_sft_ChFinAnn-Doc2EDAG_s42_ep2_gpu1_20260521T143813Z.log | Queued behind ChFinAnn seed17 on GPU1 at registry creation. |

## F1 Definitions

Legacy-FS F1 is the fixed-schema role-slot micro-F1 used for the main EPAL/SEELE comparison. After event-type constrained record matching, role slots are counted as TP, FP, or FN, then F1 is computed from precision and recall.

Unified F1 is a strict canonical JSONL role-value metric with event-type constrained global bipartite matching. It is useful for same-format diagnostics and ExactRec analysis, but it is not used in the public baseline comparison tables.

## Notes

- All metric values in tables are percentages.
- Published baseline rows are from EPAL and SEELE reported test-set tables.
- `F1(S)` means single-event F1; `F1(M)` means multi-event F1.
- `-` means not reported or unavailable.
- `HF-4bin` means HF Transformers with 4-bit NF4 quantization and LoRA adapter.
- `vLLM-bf16` means vLLM with BF16 merged weights.
- Main tables use fixed-slot / Legacy-FS only.
- Unified F1 uses strict canonical JSONL matching and is reported only in the diagnostic table.
- ExactRec is recomputed as `2 * exact_matches / validated_records`.
- Running and invalid assets are excluded from main result tables.
