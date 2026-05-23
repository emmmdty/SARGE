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
| test | backend | vLLM-bf16 + LoRA k1 | 75.0 | 74.8 | 75.2 | 78.6 | 73.2 | backend cross-check |
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
| ChFinAnn | 17 | 2 | 25632 | - | 502.5 min | runs/sarge_sft_ChFinAnn_Doc2EDAG_s17_ep2_gpu1 | completed |
| ChFinAnn | 42 | 2 | 25632 | - | 507.2 min | runs/sarge_sft_ChFinAnn_Doc2EDAG_s42_ep2_gpu1 | completed |

### Table 9. Artifact Index

| Dataset | Split | Asset | Status | Role | Snapshot | Main |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| ChFinAnn | test | chfinann_test_seed13_hf4bin_k1 | main | main_result | paper/exp/data/run_snapshots/chfinann_test_seed13_hf4bin_k1 | yes |
| DuEE-Fin | test | dueefin_test_seed13_hf4bin_k1_no_lrd | main | main_result | paper/exp/data/run_snapshots/dueefin_test_seed13_hf4bin_k1_no_lrd | yes |
| DuEE-Fin | test | dueefin_test_seed17_hf4bin_k1_no_lrd | diagnostic | seed_extension_test | paper/exp/data/run_snapshots/dueefin_test_seed17_hf4bin_k1_no_lrd | no |
| DuEE-Fin | test | dueefin_test_seed42_hf4bin_k1_no_lrd | diagnostic | seed_extension_test | paper/exp/data/run_snapshots/dueefin_test_seed42_hf4bin_k1_no_lrd | no |
| DuEE-Fin | test | dueefin_test_seed13_hf4bin_k1_lrd | diagnostic | lrd_test_diagnostic | paper/exp/data/run_snapshots/dueefin_test_seed13_hf4bin_k1_lrd | no |
| ChFinAnn | test | chfinann_test_seed13_vllm_bf16_k1 | ablation | backend_crosscheck | paper/exp/data/run_snapshots/chfinann_test_seed13_vllm_bf16_k1 | no |
| ChFinAnn | test | chfinann_test_seed13_vllm_bf16_k4_t07 | ablation | decoding_ablation | paper/exp/data/run_snapshots/chfinann_test_seed13_vllm_bf16_k4_t07 | no |
| ChFinAnn | test | chfinann_test_seed13_vllm_bf16_no_sft | ablation | sft_ablation | paper/exp/data/run_snapshots/chfinann_test_seed13_vllm_bf16_no_sft | no |
| DuEE-Fin | test | dueefin_test_seed13_hf4bin_no_sft | ablation | sft_ablation | paper/exp/data/run_snapshots/dueefin_test_seed13_hf4bin_no_sft | no |
| DuEE-Fin | test | dueefin_test_seed13_vllm_bf16_k1 | ablation | backend_crosscheck | paper/exp/data/run_snapshots/dueefin_test_seed13_vllm_bf16_k1 | no |
| DuEE-Fin | test | dueefin_test_seed17_vllm_bf16_k1 | ablation | backend_crosscheck | paper/exp/data/run_snapshots/dueefin_test_seed17_vllm_bf16_k1 | no |
| DuEE-Fin | test | dueefin_test_seed42_vllm_bf16_k1 | ablation | backend_crosscheck | paper/exp/data/run_snapshots/dueefin_test_seed42_vllm_bf16_k1 | no |
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
| ChFinAnn | train | chfinann_train_seed17 | training | training_asset_completed | paper/exp/data/run_snapshots/chfinann_train_seed17 | no |
| ChFinAnn | train | chfinann_train_seed42 | training | training_asset_completed | paper/exp/data/run_snapshots/chfinann_train_seed42 | no |
| ChFinAnn | test | chfinann_test_seed17_hf4bin_k1 | diagnostic | seed_extension_test | paper/exp/data/run_snapshots/chfinann_test_seed17_hf4bin_k1 | no |
| DuEE-Fin | test | dueefin_test_seed13_hf4bin_ablation_no_surface_memory | ablation | prompt_module_ablation_hf | paper/exp/data/run_snapshots/dueefin_test_seed13_hf4bin_ablation_no_surface_memory | no |
| DuEE-Fin | test | dueefin_test_seed13_vllm_ablation_no_surface_memory | ablation | prompt_module_fast_screen_vllm | paper/exp/data/run_snapshots/dueefin_test_seed13_vllm_ablation_no_surface_memory | no |
| DuEE-Fin | test | dueefin_test_seed13_vllm_ablation_no_slot_plan | ablation | prompt_module_fast_screen_vllm | paper/exp/data/run_snapshots/dueefin_test_seed13_vllm_ablation_no_slot_plan | no |
| DuEE-Fin | test | dueefin_test_seed13_vllm_ablation_no_surface_or_slot | ablation | prompt_module_fast_screen_vllm | paper/exp/data/run_snapshots/dueefin_test_seed13_vllm_ablation_no_surface_or_slot | no |
| DuEE-Fin | test | dueefin_test_seed13_vllm_ablation_schema_only | ablation | prompt_module_fast_screen_vllm | paper/exp/data/run_snapshots/dueefin_test_seed13_vllm_ablation_schema_only | no |
| DuEE-Fin | test | dueefin_test_seed13_vllm_ablation_direct_json | ablation | prompt_module_fast_screen_vllm | paper/exp/data/run_snapshots/dueefin_test_seed13_vllm_ablation_direct_json | no |
| DuEE-Fin | test | dueefin_test_seed13_vllm_mechanism_full_limit128_default | diagnostic | backend_mechanism_probe | paper/exp/data/run_snapshots/dueefin_test_seed13_vllm_mechanism_full_limit128_default | no |
| DuEE-Fin | test | dueefin_test_seed13_vllm_mechanism_no_surface_memory_limit128_default | diagnostic | backend_mechanism_probe | paper/exp/data/run_snapshots/dueefin_test_seed13_vllm_mechanism_no_surface_memory_limit128_default | no |
| DuEE-Fin | test | dueefin_test_seed13_vllm_mechanism_no_surface_or_slot_limit128_default | diagnostic | backend_mechanism_probe | paper/exp/data/run_snapshots/dueefin_test_seed13_vllm_mechanism_no_surface_or_slot_limit128_default | no |
| DuEE-Fin | test | dueefin_test_seed13_vllm_mechanism_full_limit128_mem080 | diagnostic | backend_mechanism_probe | paper/exp/data/run_snapshots/dueefin_test_seed13_vllm_mechanism_full_limit128_mem080 | no |
| DuEE-Fin | test | dueefin_test_seed13_vllm_mechanism_no_surface_memory_limit128_mem080 | diagnostic | backend_mechanism_probe | paper/exp/data/run_snapshots/dueefin_test_seed13_vllm_mechanism_no_surface_memory_limit128_mem080 | no |
| DuEE-Fin | test | dueefin_test_seed13_vllm_mechanism_no_slot_plan_limit128_mem080 | diagnostic | backend_mechanism_probe | paper/exp/data/run_snapshots/dueefin_test_seed13_vllm_mechanism_no_slot_plan_limit128_mem080 | no |
| DuEE-Fin | test | dueefin_test_seed13_vllm_mechanism_no_surface_or_slot_limit128_mem080 | diagnostic | backend_mechanism_probe | paper/exp/data/run_snapshots/dueefin_test_seed13_vllm_mechanism_no_surface_or_slot_limit128_mem080 | no |
| DuEE-Fin | test | dueefin_test_seed13_vllm_mechanism_no_surface_memory_sacd_strict_limit128_mem080 | diagnostic | backend_mechanism_probe | paper/exp/data/run_snapshots/dueefin_test_seed13_vllm_mechanism_no_surface_memory_sacd_strict_limit128_mem080 | no |
| DuEE-Fin | test | dueefin_test_seed13_vllm_mechanism_no_slot_plan_sacd_strict_limit128_mem080 | diagnostic | backend_mechanism_probe | paper/exp/data/run_snapshots/dueefin_test_seed13_vllm_mechanism_no_slot_plan_sacd_strict_limit128_mem080 | no |
| ChFinAnn | test | chfinann_test_seed42_hf4bin_k1 | diagnostic | seed_extension_test | paper/exp/data/run_snapshots/chfinann_test_seed42_hf4bin_k1 | no |
| DuEE-Fin | test | dueefin_test_seed13_hf4bin_ablation_no_slot_plan | ablation | prompt_module_ablation_hf | paper/exp/data/run_snapshots/dueefin_test_seed13_hf4bin_ablation_no_slot_plan | no |
| ChFinAnn | test | chfinann_test_seed13_vllm_ablation_full_mem080 | diagnostic | prompt_module_fast_screen_vllm | paper/exp/data/run_snapshots/chfinann_test_seed13_vllm_ablation_full_mem080 | no |
| ChFinAnn | test | chfinann_test_seed13_vllm_ablation_no_surface_memory_mem080 | diagnostic | prompt_module_fast_screen_vllm | paper/exp/data/run_snapshots/chfinann_test_seed13_vllm_ablation_no_surface_memory_mem080 | no |
| ChFinAnn | test | chfinann_test_seed13_vllm_ablation_no_slot_plan_mem080 | diagnostic | prompt_module_fast_screen_vllm | paper/exp/data/run_snapshots/chfinann_test_seed13_vllm_ablation_no_slot_plan_mem080 | no |

## Output Diagnostics

### Table 10. Robustness Diagnostics

| Dataset | Split | Run | SchemaOK | ParseFail | InvType | InvRole | ValidRec | Exact | ExactRec | Status |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| ChFinAnn | test | chfinann_test_seed13_hf4bin_k1 | 100.0 | 0 | 0 | 0 | 9640 | 2816 | 58.4 | main |
| DuEE-Fin | test | dueefin_test_seed13_hf4bin_k1_no_lrd | 100.0 | 0 | 0 | 0 | 3090 | 662 | 42.8 | main |
| DuEE-Fin | test | dueefin_test_seed17_hf4bin_k1_no_lrd | 100.0 | 0 | 0 | 0 | 3041 | 656 | 43.1 | diagnostic |
| DuEE-Fin | test | dueefin_test_seed42_hf4bin_k1_no_lrd | 100.0 | 0 | 0 | 0 | 3067 | 672 | 43.8 | diagnostic |
| DuEE-Fin | test | dueefin_test_seed13_hf4bin_k1_lrd | 100.0 | 0 | 0 | 0 | 3088 | 662 | 42.9 | diagnostic |
| ChFinAnn | test | chfinann_test_seed13_vllm_bf16_k1 | 100.0 | 0 | 0 | 0 | 9637 | 2689 | 55.8 | ablation |
| ChFinAnn | test | chfinann_test_seed13_vllm_bf16_k4_t07 | 100.0 | 0 | 0 | 0 | 9933 | 2729 | 54.9 | ablation |
| ChFinAnn | test | chfinann_test_seed13_vllm_bf16_no_sft | 100.0 | 0 | 0 | 0 | 6330 | 323 | 10.2 | ablation |
| DuEE-Fin | test | dueefin_test_seed13_hf4bin_no_sft | 100.0 | 0 | 0 | 0 | 2443 | 0 | 0.0 | ablation |
| DuEE-Fin | test | dueefin_test_seed13_vllm_bf16_k1 | 100.0 | 0 | 0 | 0 | 3014 | 576 | 38.2 | ablation |
| DuEE-Fin | test | dueefin_test_seed17_vllm_bf16_k1 | 100.0 | 0 | 0 | 0 | 2999 | 549 | 36.6 | ablation |
| DuEE-Fin | test | dueefin_test_seed42_vllm_bf16_k1 | 100.0 | 0 | 0 | 0 | 3018 | 597 | 39.6 | ablation |
| DuEE-Fin | test | dueefin_test_seed13_vllm_bf16_k4_t07 | 100.0 | 0 | 0 | 0 | 3170 | 550 | 34.7 | ablation |
| DuEE-Fin | test | dueefin_test_seed13_vllm_bf16_no_sft | 100.0 | 0 | 0 | 0 | 2333 | 3 | 0.3 | ablation |
| DuEE-Fin | dev | dueefin_dev_seed13_hf4bin_k1 | 100.0 | 0 | 0 | 0 | 1351 | 282 | 41.7 | diagnostic |
| DuEE-Fin | dev | dueefin_dev_seed13_hf4bin_k1_lrd | 100.0 | 0 | 0 | 0 | 1349 | 282 | 41.8 | diagnostic |
| DuEE-Fin | dev | dueefin_dev_seed17_train_sft_mrs_no_lrd | 100.0 | 0 | 0 | 0 | 1347 | 282 | 41.9 | diagnostic |
| DuEE-Fin | dev | dueefin_dev_seed42_train_sft_mrs_no_lrd | 100.0 | 0 | 0 | 0 | 1352 | 283 | 41.9 | diagnostic |
| DuEE-Fin | dev | dueefin_dev_seed17_lrd_invalid_k4_pool | 100.0 | 0 | 0 | 0 | 3118 | 282 | 18.1 | invalid |
| ChFinAnn | test | chfinann_test_seed17_hf4bin_k1 | 100.0 | 0 | 0 | 0 | 9714 | 2687 | 55.3 | diagnostic |
| DuEE-Fin | test | dueefin_test_seed13_hf4bin_ablation_no_surface_memory | 100.0 | 0 | 0 | 0 | 3101 | 665 | 42.9 | ablation |
| DuEE-Fin | test | dueefin_test_seed13_vllm_ablation_no_surface_memory | 100.0 | 0 | 0 | 0 | 1604 | 7 | 0.9 | ablation |
| DuEE-Fin | test | dueefin_test_seed13_vllm_ablation_no_slot_plan | 100.0 | 0 | 0 | 0 | 1588 | 6 | 0.8 | ablation |
| DuEE-Fin | test | dueefin_test_seed13_vllm_ablation_no_surface_or_slot | 100.0 | 0 | 0 | 0 | 3028 | 570 | 37.6 | ablation |
| DuEE-Fin | test | dueefin_test_seed13_vllm_ablation_schema_only | 100.0 | 0 | 0 | 0 | 2804 | 264 | 18.8 | ablation |
| DuEE-Fin | test | dueefin_test_seed13_vllm_ablation_direct_json | 100.0 | 0 | 0 | 0 | 1533 | 0 | 0.0 | ablation |
| DuEE-Fin | test | dueefin_test_seed13_vllm_mechanism_full_limit128_default | 100.0 | 0 | 0 | 0 | 180 | 0 | 0.0 | diagnostic |
| DuEE-Fin | test | dueefin_test_seed13_vllm_mechanism_no_surface_memory_limit128_default | 100.0 | 0 | 0 | 0 | 180 | 0 | 0.0 | diagnostic |
| DuEE-Fin | test | dueefin_test_seed13_vllm_mechanism_no_surface_or_slot_limit128_default | 100.0 | 0 | 0 | 0 | 195 | 3 | 3.1 | diagnostic |
| DuEE-Fin | test | dueefin_test_seed13_vllm_mechanism_full_limit128_mem080 | 100.0 | 0 | 0 | 0 | 307 | 44 | 28.7 | diagnostic |
| DuEE-Fin | test | dueefin_test_seed13_vllm_mechanism_no_surface_memory_limit128_mem080 | 100.0 | 0 | 0 | 0 | 313 | 42 | 26.8 | diagnostic |
| DuEE-Fin | test | dueefin_test_seed13_vllm_mechanism_no_slot_plan_limit128_mem080 | 100.0 | 0 | 0 | 0 | 309 | 36 | 23.3 | diagnostic |
| DuEE-Fin | test | dueefin_test_seed13_vllm_mechanism_no_surface_or_slot_limit128_mem080 | 100.0 | 0 | 0 | 0 | 311 | 40 | 25.7 | diagnostic |
| DuEE-Fin | test | dueefin_test_seed13_vllm_mechanism_no_surface_memory_sacd_strict_limit128_mem080 | 100.0 | 0 | 0 | 0 | 344 | 36 | 20.9 | diagnostic |
| DuEE-Fin | test | dueefin_test_seed13_vllm_mechanism_no_slot_plan_sacd_strict_limit128_mem080 | 100.0 | 0 | 0 | 0 | 369 | 44 | 23.8 | diagnostic |
| ChFinAnn | test | chfinann_test_seed42_hf4bin_k1 | 100.0 | 0 | 0 | 0 | 9716 | 2653 | 54.6 | diagnostic |
| DuEE-Fin | test | dueefin_test_seed13_hf4bin_ablation_no_slot_plan | 100.0 | 0 | 0 | 0 | 3083 | 662 | 42.9 | ablation |
| ChFinAnn | test | chfinann_test_seed13_vllm_ablation_full_mem080 | 100.0 | 0 | 0 | 0 | 9615 | 2689 | - | diagnostic |
| ChFinAnn | test | chfinann_test_seed13_vllm_ablation_no_surface_memory_mem080 | 100.0 | 0 | 0 | 0 | 9534 | 2675 | - | diagnostic |
| ChFinAnn | test | chfinann_test_seed13_vllm_ablation_no_slot_plan_mem080 | 100.0 | 0 | 0 | 0 | 9668 | 2725 | - | diagnostic |

### Table 11. Active And Invalid Assets

| Asset | Dataset | Split | Seed | Status | Log | Note |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| dueefin_dev_seed17_lrd_invalid_k4_pool | DuEE-Fin | dev | 17 | invalid | - | Invalid for model comparison: postprocess flattened all k=4 candidates (2692 events in, 2444 out), causing FP explosion. |

### Table 12. DuEE-Fin HF Seed Stability

| Dataset | Split | Backend | Seeds | Legacy-FS F1 | Unified F1 | DocFEE F1 | ExactRec |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| DuEE-Fin-dev500 | test | HF-4bin + LoRA, k=1 greedy, no-LRD | 13 | 77.96 | 78.88 | 77.71 | 42.85 |
| DuEE-Fin-dev500 | test | HF-4bin + LoRA, k=1 greedy, no-LRD | 17 | 78.72 | 79.37 | 78.22 | 43.14 |
| DuEE-Fin-dev500 | test | HF-4bin + LoRA, k=1 greedy, no-LRD | 42 | 78.28 | 79.21 | 78.09 | 43.82 |
| DuEE-Fin-dev500 | test | HF-4bin + LoRA, k=1 greedy, no-LRD | mean±std | 78.32±0.38 | 79.15±0.25 | 78.01±0.26 | 43.27±0.50 |

### Table 13. DuEE-Fin Backend Seed Stability

| Dataset | Split | Backend | Seeds | Legacy-FS F1 | Unified F1 | DocFEE F1 | ExactRec |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| DuEE-Fin-dev500 | test | HF-4bin + LoRA, k=1 greedy, no-LRD | 13 | 77.96 | 78.88 | 77.71 | 42.85 |
| DuEE-Fin-dev500 | test | HF-4bin + LoRA, k=1 greedy, no-LRD | 17 | 78.72 | 79.37 | 78.22 | 43.14 |
| DuEE-Fin-dev500 | test | HF-4bin + LoRA, k=1 greedy, no-LRD | 42 | 78.28 | 79.21 | 78.09 | 43.82 |
| DuEE-Fin-dev500 | test | HF-4bin + LoRA, k=1 greedy, no-LRD | mean±std | 78.32±0.38 | 79.15±0.25 | 78.01±0.26 | 43.27±0.50 |
| DuEE-Fin-dev500 | test | vLLM BF16 merged, k=1 greedy | 13 | 75.02 | 75.96 | 74.96 | 38.22 |
| DuEE-Fin-dev500 | test | vLLM BF16 merged, k=1 greedy | 17 | 74.70 | 75.44 | 74.49 | 36.61 |
| DuEE-Fin-dev500 | test | vLLM BF16 merged, k=1 greedy | 42 | 75.83 | 76.75 | 75.94 | 39.56 |
| DuEE-Fin-dev500 | test | vLLM BF16 merged, k=1 greedy | mean±std | 75.18±0.58 | 76.05±0.66 | 75.13±0.74 | 38.13±1.48 |

### Table 14. DuEE-Fin Prompt Module Ablation

| Backend | Profile | Docs | gmem | Legacy-FS | Unified | DocFEE | ExactRec | Note |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| HF-4bin + LoRA | full | 1171 | - | 78.0 | 78.9 | 77.7 | 42.8 | Primary DuEE-Fin test result; no-LRD remains the main path. |
| HF-4bin + LoRA | no_surface_memory | 1171 | - | 78.1 | 79.0 | 77.8 | 42.9 | HF-4bit confirmation for Surface Memory removal; removal did not cause a visible drop relative to the HF full row. |
| HF-4bin + LoRA | no_slot_plan | 1171 | - | 77.6 | 78.6 | 77.3 | 42.9 | HF-4bit no_slot_plan module ablation; compared with full and no_surface_memory, slot plan shows weak positive contribution without vLLM collapse. |
| vLLM-bf16 merged | full | 1171 | - | 75.0 | 76.0 | 75.0 | 38.2 | Fresh vLLM BF16 merged backend rerun; kept as diagnostic backend cross-check, not main result. |
| vLLM-bf16 merged | no_surface_memory | 1171 | 0.7 | 2.1 | 2.1 | 2.1 | 0.9 | vLLM full-test fast screen; removal of surface candidates collapsed recall under gpu_memory_utilization=0.70. |
| vLLM-bf16 merged | no_slot_plan | 1171 | 0.7 | 1.6 | 1.7 | 1.6 | 0.8 | vLLM full-test fast screen; removal of slot plan collapsed recall under gpu_memory_utilization=0.70. |
| vLLM-bf16 merged | no_surface_or_slot | 1171 | 0.7 | 75.5 | 76.4 | 75.2 | 37.6 | vLLM full-test fast screen; combined removal stayed near full-vLLM level, indicating backend/prompt interaction rather than simple additive module effect. |
| vLLM-bf16 merged | schema_only | 1171 | 0.7 | 65.5 | 66.2 | 65.0 | 18.8 | vLLM full-test coarse lower-bound diagnostic; not a single-variable module ablation. |
| vLLM-bf16 merged | direct_json | 1171 | 0.7 | 0.0 | 0.0 | 0.0 | 0.0 | vLLM full-test direct JSON lower bound; extraction failed completely. |

### Table 15. DuEE-Fin vLLM Mechanism Probes

| Profile | Variant | gmem | Docs | Legacy-FS | Unified | DocFEE | ExactRec | ValidRec | Note |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| full | base | 0.7 | 128 | 0.2 | 0.2 | 0.2 | 0.0 | 180 | Limit-128 vLLM mechanism probe for backend/prompt sensitivity; gpu_memory_utilization=0.7. |
| no_surface_memory | base | 0.7 | 128 | 0.2 | 0.5 | 0.5 | 0.0 | 180 | Limit-128 vLLM mechanism probe for backend/prompt sensitivity; gpu_memory_utilization=0.7. |
| no_surface_or_slot | base | 0.7 | 128 | 7.9 | 7.8 | 7.6 | 3.1 | 195 | Limit-128 vLLM mechanism probe for backend/prompt sensitivity; gpu_memory_utilization=0.7. |
| full | base | 0.8 | 128 | 65.6 | 65.1 | 64.3 | 28.7 | 307 | Limit-128 vLLM mechanism probe for backend/prompt sensitivity; gpu_memory_utilization=0.8. |
| no_surface_memory | base | 0.8 | 128 | 67.5 | 66.8 | 65.8 | 26.8 | 313 | Limit-128 vLLM mechanism probe for backend/prompt sensitivity; gpu_memory_utilization=0.8. |
| no_slot_plan | base | 0.8 | 128 | 63.1 | 62.5 | 61.5 | 23.3 | 309 | Limit-128 vLLM mechanism probe for backend/prompt sensitivity; gpu_memory_utilization=0.8. |
| no_surface_or_slot | base | 0.8 | 128 | 65.8 | 65.3 | 64.5 | 25.7 | 311 | Limit-128 vLLM mechanism probe for backend/prompt sensitivity; gpu_memory_utilization=0.8. |
| no_surface_memory | sacd_strict | 0.8 | 128 | 57.9 | 58.1 | 57.3 | 20.9 | 344 | Limit-128 vLLM mechanism probe for backend/prompt sensitivity; gpu_memory_utilization=0.8; SACD strict enabled. |
| no_slot_plan | sacd_strict | 0.8 | 128 | 57.8 | 57.8 | 57.0 | 23.8 | 369 | Limit-128 vLLM mechanism probe for backend/prompt sensitivity; gpu_memory_utilization=0.8; SACD strict enabled. |

### Table 16. ChFinAnn HF Seed Stability

| Dataset | Split | Backend | Seeds | Legacy-FS F1 | Unified F1 | DocFEE F1 | ExactRec |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| ChFinAnn-Doc2EDAG | test | HF-4bin + LoRA, k=1 greedy | 13 | 86.03 | 87.42 | 86.53 | 58.42 |
| ChFinAnn-Doc2EDAG | test | HF-4bin + LoRA, k=1 greedy | 17 | 85.36 | 87.05 | 86.27 | 55.32 |
| ChFinAnn-Doc2EDAG | test | HF-4bin + LoRA, k=1 greedy | 42 | 85.33 | 87.01 | 86.13 | 54.61 |
| ChFinAnn-Doc2EDAG | test | HF-4bin + LoRA, k=1 greedy | mean±std | 85.57±0.39 | 87.16±0.23 | 86.31±0.20 | 56.12±2.03 |

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
