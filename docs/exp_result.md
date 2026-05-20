# SARGE 实验结果记录

> 最后更新：2026-05-20 11:38 UTC+8
> 所有数据从服务器实际文件读取，非记忆推断。

---

## 1. 训练产物

### 1.1 DuEE-Fin-dev500 — 4-bit NF4, epoch 2, seed 13

| 字段 | 值 | 来源 |
|---|---|---|
| Run dir | `runs/sarge_sft_DuEE_Fin_dev500_s13_ep2_gpu0/` | `summary_train.json` |
| Base model | Qwen3-4B-Instruct-2507 | `training_manifest.json` |
| 量化 | 4-bit NF4, double_quant=True | `training_manifest.json` |
| compute_dtype | bf16 | `training_manifest.json` |
| LoRA | r=16, alpha=32, dropout=0.05, target=[q/k/v/o]_proj | `training_manifest.json` |
| train docs | 6515 (8824 events) | `summary_train.json` |
| epochs | 2 | `summary_train.json` |
| train loss | 0.0791 | `training_manifest.json` |
| train time | 9971s (166 min) | `summary_train.json` |
| GPU | 0 | `summary_train.json` |
| Adapter | `artifacts/model/adapter/` | `summary_train.json` |
| Checkpoints | checkpoint-408 (ep1), checkpoint-816 (ep2) | `summary_train.json` |

**训练内置评测（4-bit NF4 + LoRA, k=4 sampling）：**

| Track | F1 | P | R | multi_F1 | single_F1 | 来源 |
|---|---|---|---|---|---|---|
| legacy_doc2edag | 0.7704 | 0.7547 | 0.7867 | 0.7636 | 0.7903 | `eval_legacy_ep2.json` |
| unified_strict | 0.7759 | 0.7608 | 0.7917 | 0.7724 | 0.7911 | `eval_unified_v3.json` |
| docfee_official | 0.7711 | 0.7560 | 0.7868 | 0.7639 | 0.7911 | `eval_docfee_ep2.json` |

### 1.2 ChFinAnn-Doc2EDAG — 4-bit NF4, epoch 2, seed 13

| 字段 | 值 | 来源 |
|---|---|---|
| Run dir | `runs/sarge_sft_ChFinAnn_Doc2EDAG_s13_ep2_gpu1/` | `summary_train.json` |
| Base model | Qwen3-4B-Instruct-2507 | `training_manifest.json` |
| 量化 | 4-bit NF4, double_quant=True | `training_manifest.json` |
| compute_dtype | bf16 | `training_manifest.json` |
| LoRA | r=16, alpha=32, dropout=0.05, target=[q/k/v/o]_proj | `training_manifest.json` |
| train docs | 25632 (38088 events) | `summary_train.json` |
| epochs | 2 | `summary_train.json` |
| train loss | 0.0202 | `training_manifest.json` |
| train time | 30310s (505 min = 8.4h) | `summary_train.json` |
| GPU | 1 | `summary_train.json` |
| Adapter | `artifacts/model/adapter/` | `summary_train.json` |
| Checkpoints | checkpoint-3204 (ep1), checkpoint-6408 (ep2) | `summary_train.json` |

### 1.3 vLLM 合并权重 (merged models)

| 目录 | 用途 | 来源 Adapter |
|---|---|---|
| `runs/merged_models/qwen3_4b_dueefin_ep2_s13/` | DuEE-Fin vLLM 推理 | §1.1 LoRA merged → BF16 full weights |
| `runs/merged_models/qwen3_4b_chfinann_ep2_s13/` | ChFinAnn vLLM 推理 | §1.2 LoRA merged → BF16 full weights |

---

## 2. 推理与评测 — DuEE-Fin-dev500

> 以下所有实验均为 500 dev docs，seed 13。

### 2.1 no-SFT baseline — HF 4-bit NF4 (k 未知)

| 字段 | 值 |
|---|---|
| Run dir | `runs/sarge_infer_DuEE-Fin-dev500_dev_20260518T033841Z/` |
| Backend | HF transformers, 4-bit NF4, 无 adapter |
| 文档数 | 500 |

| Track | F1 | P | R | multi_F1 | single_F1 |
|---|---|---|---|---|---|
| legacy_doc2edag | 0.0382 | 0.5909 | 0.0197 | 0.0455 | 0.0274 |
| unified_strict | 0.0467 | 0.6269 | 0.0243 | 0.0529 | 0.0378 |
| docfee_official | 0.0456 | 0.6119 | 0.0237 | 0.0510 | 0.0378 |

### 2.2 BF16-trained ep1 LoRA — HF 4-bit NF4 (k 未知)

| 字段 | 值 |
|---|---|
| Run dir | `runs/sarge_infer_DuEE-Fin-dev500_dev_20260518T055217Z/` |
| Backend | HF transformers, 4-bit NF4 base + BF16-trained LoRA ep1 |

| Track | F1 | P | R | multi_F1 | single_F1 |
|---|---|---|---|---|---|
| legacy_doc2edag | 0.6959 | 0.6870 | 0.7051 | 0.6697 | 0.7470 |
| unified_strict | 0.7092 | 0.7008 | 0.7178 | 0.6911 | 0.7490 |
| docfee_official | 0.7015 | 0.6932 | 0.7100 | 0.6771 | 0.7490 |

### 2.3 vLLM BF16 merged ep2 — k=1 greedy

| 字段 | 值 |
|---|---|
| Run dir | `runs/sarge_infer_DuEE-Fin-dev500_dev_20260519T035806Z/` |
| Backend | vLLM 0.8.5, BF16 merged weights (§1.3) |
| 解码 | k=1, do_sample=False, greedy |
| Log | `logs/sarge_vllm_dueefin_500_s13_k1_greedy_ep2_gpu0_20260519T115527Z.log` |

| Track | F1 | P | R | multi_F1 | single_F1 |
|---|---|---|---|---|---|
| legacy_doc2edag | 0.7275 | 0.7442 | 0.7115 | 0.6995 | 0.7818 |
| unified_strict | 0.7354 | 0.7545 | 0.7172 | 0.7060 | 0.7906 |
| docfee_official | 0.7312 | 0.7502 | 0.7132 | 0.6986 | 0.7906 |

### 2.4 vLLM BF16 merged ep2 — k=4 sampling T=0.7

| 字段 | 值 |
|---|---|
| Run dir | `runs/sarge_infer_DuEE-Fin-dev500_dev_20260519T040454Z/` |
| Backend | vLLM 0.8.5, BF16 merged weights (§1.3) |
| 解码 | k=4, do_sample=True, T=0.7, top_p=0.95 |
| Log | `logs/sarge_vllm_dueefin_500_s13_k4_sample_T0.7_ep2_gpu0_20260519T120122Z.log` |

| Track | F1 | P | R | multi_F1 | single_F1 |
|---|---|---|---|---|---|
| legacy_doc2edag | 0.7228 | 0.6685 | 0.7867 | 0.7210 | 0.7488 |
| unified_strict | 0.7332 | 0.6789 | 0.7969 | 0.7322 | 0.7574 |
| docfee_official | 0.7303 | 0.6762 | 0.7938 | 0.7270 | 0.7574 |

### 2.5 vLLM BF16 merged ep2 — k=4 sampling T=0.3

| 字段 | 值 |
|---|---|
| Run dir | `runs/sarge_infer_DuEE-Fin-dev500_dev_20260519T054526Z/` |
| Backend | vLLM 0.8.5, BF16 merged weights (§1.3) |
| 解码 | k=4, do_sample=True, T=0.3, top_p=0.95 |
| Log | `logs/sarge_vllm_dueefin_500_s13_k4_sample_T0.3_ep2_gpu2_20260519T134206Z.log` |

| Track | F1 | P | R | multi_F1 | single_F1 |
|---|---|---|---|---|---|
| legacy_doc2edag | 0.7386 | 0.7094 | 0.7703 | 0.7221 | 0.7794 |
| unified_strict | 0.7525 | 0.7240 | 0.7834 | 0.7380 | 0.7899 |
| docfee_official | 0.7500 | 0.7216 | 0.7808 | 0.7335 | 0.7899 |

### 2.6 vLLM BF16 merged ep2 — k=4 sampling T=0.5

| 字段 | 值 |
|---|---|
| Run dir | `runs/sarge_infer_DuEE-Fin-dev500_dev_20260519T054536Z/` |
| Backend | vLLM 0.8.5, BF16 merged weights (§1.3) |
| 解码 | k=4, do_sample=True, T=0.5, top_p=0.95 |
| Log | `logs/sarge_vllm_dueefin_500_s13_k4_sample_T0.5_ep2_gpu3_20260519T134221Z.log` |

| Track | F1 | P | R | multi_F1 | single_F1 |
|---|---|---|---|---|---|
| legacy_doc2edag | 0.7265 | 0.6893 | 0.7679 | 0.7166 | 0.7638 |
| unified_strict | 0.7381 | 0.7022 | 0.7779 | 0.7279 | 0.7750 |
| docfee_official | 0.7332 | 0.6975 | 0.7727 | 0.7191 | 0.7750 |

### 2.7 vLLM BF16 no-SFT baseline — k=1 greedy

| 字段 | 值 |
|---|---|
| Run dir | `runs/sarge_infer_DuEE-Fin-dev500_dev_20260519T044910Z/` |
| Backend | vLLM 0.8.5, BF16 base model, 无 adapter |
| 解码 | k=1, do_sample=False, greedy |
| Log | `logs/sarge_vllm_dueefin_500_noSFT_baseline_k1_gpu3_20260519T124655Z.log` |

| Track | F1 | P | R | multi_F1 | single_F1 |
|---|---|---|---|---|---|
| legacy_doc2edag | 0.1125 | 0.4329 | 0.0646 | 0.0848 | 0.1506 |
| unified_strict | 0.1180 | 0.4519 | 0.0679 | 0.0840 | 0.1640 |
| docfee_official | 0.1170 | 0.4481 | 0.0673 | 0.0822 | 0.1640 |

### 2.8 vLLM BF16 merged ep2 — k=1 greedy（首次 vLLM 验证）

| 字段 | 值 |
|---|---|
| Run dir | `runs/sarge_infer_DuEE-Fin-dev500_dev_20260518T233710Z/` |
| Backend | vLLM 0.8.5, BF16 merged weights（merge+infer 流水线） |
| 备注 | 首次 vLLM 推理验证，manifest 为 pre-hardening 版本 |

| Track | F1 | P | R | multi_F1 | single_F1 |
|---|---|---|---|---|---|
| legacy_doc2edag | 0.7281 | 0.7506 | 0.7069 | 0.6968 | 0.7864 |
| unified_strict | 0.7371 | 0.7627 | 0.7132 | 0.7073 | 0.7925 |
| docfee_official | 0.7335 | 0.7590 | 0.7097 | 0.7008 | 0.7925 |

> 与 §2.3 互为验证：两次独立 vLLM k=1 推理，legacy F1 仅差 0.0006。

### 2.9 HF 4-bit NF4 + LoRA ep2 — k=1 greedy

| 字段 | 值 |
|---|---|
| Run dir | `runs/sarge_infer_DuEE-Fin-dev500_dev_20260519T043458Z/` |
| Backend | HF transformers, 4-bit NF4 base + 4-bit NF4 LoRA ep2 (§1.1) |
| 解码 | k=1, greedy |
| 目的 | 验证 4-bit NF4 推理路径 vs vLLM BF16 差距 |
| Log | `logs/sarge_hf_dueefin_500_s13_k1_4bitNF4_LoRA_ep2_gpu0_20260519T123458Z.log` |

| Track | F1 | P | R | multi_F1 | single_F1 |
|---|---|---|---|---|---|
| legacy_doc2edag | 0.7666 | 0.7548 | 0.7788 | 0.7536 | 0.7943 |
| unified_strict | 0.7723 | 0.7607 | 0.7842 | 0.7616 | 0.7964 |
| docfee_official | 0.7675 | 0.7560 | 0.7793 | 0.7531 | 0.7964 |

---

## 3. 推理与评测 — ChFinAnn-Doc2EDAG

> 以下实验均为 full dev (3204 docs)，seed 13。标注 limit=500 的为 500-doc 子集。

### 3.1 HF 4-bit NF4 + LoRA ep2 — k=1 greedy (limit=500)

| 字段 | 值 |
|---|---|
| Run dir | `runs/sarge_infer_ChFinAnn-Doc2EDAG_dev_20260518T113445Z/` |
| Backend | HF transformers, 4-bit NF4 + LoRA ep2 (§1.2) |
| 文档数 | 500 |

| Track | F1 | P | R | multi_F1 | single_F1 |
|---|---|---|---|---|---|
| legacy_doc2edag | 0.8444 | 0.8245 | 0.8653 | 0.8164 | 0.8807 |
| unified_strict | 0.8604 | 0.8401 | 0.8816 | 0.8398 | 0.8870 |
| docfee_official | 0.8505 | 0.8304 | 0.8715 | 0.8223 | 0.8870 |

### 3.2 vLLM BF16 merged ep2 — k=1 greedy (limit=500)

| 字段 | 值 |
|---|---|
| Run dir | `runs/sarge_infer_ChFinAnn-Doc2EDAG_dev_20260518T232750Z/` |
| Backend | vLLM 0.8.5, BF16 merged weights |
| 文档数 | 500 |

| Track | F1 | P | R | multi_F1 | single_F1 |
|---|---|---|---|---|---|
| legacy_doc2edag | 0.8419 | 0.8219 | 0.8629 | 0.8102 | 0.8836 |
| unified_strict | 0.8600 | 0.8396 | 0.8814 | 0.8355 | 0.8922 |
| docfee_official | 0.8535 | 0.8332 | 0.8748 | 0.8241 | 0.8922 |

### 3.3 vLLM BF16 merged ep2 — k=1 greedy (full dev, 3204 docs) ⭐

| 字段 | 值 |
|---|---|
| Run dir | `runs/sarge_infer_ChFinAnn-Doc2EDAG_dev_20260519T040525Z/` |
| Backend | vLLM 0.8.5, BF16 merged weights (§1.3) |
| 文档数 | **3204 (full dev)** |
| 解码 | k=1, do_sample=False, greedy |
| Log | `logs/sarge_vllm_chfinann_fulldev_s13_k1_ep2_gpu3_20260519T115223Z.log` |

| Track | F1 | P | R | multi_F1 | single_F1 |
|---|---|---|---|---|---|
| legacy_doc2edag | **0.8549** | 0.8351 | 0.8758 | 0.8307 | 0.8834 |
| unified_strict | **0.8705** | 0.8502 | 0.8917 | 0.8507 | 0.8937 |
| docfee_official | **0.8643** | 0.8442 | 0.8854 | 0.8393 | 0.8937 |

> **超过 SEELE (85.1) 的 ChFinAnn SOTA。**

### 3.4 vLLM BF16 no-SFT baseline — k=1 greedy (full dev, 3204 docs)

| 字段 | 值 |
|---|---|
| Run dir | `runs/sarge_infer_ChFinAnn-Doc2EDAG_dev_20260519T042901Z/` |
| Backend | vLLM 0.8.5, BF16 base model, 无 adapter |
| 文档数 | 3204 |
| Log | `logs/sarge_vllm_chfinann_noSFT_baseline_k1_gpu0_20260519T122009Z.log` |

| Track | F1 | P | R | multi_F1 | single_F1 |
|---|---|---|---|---|---|
| legacy_doc2edag | 0.1861 | 0.4900 | 0.1149 | 0.0804 | 0.2946 |
| unified_strict | 0.1860 | 0.4830 | 0.1151 | 0.0806 | 0.2942 |
| docfee_official | 0.1815 | 0.4713 | 0.1124 | 0.0718 | 0.2942 |

> SFT 增益：**+66.9pp** (legacy F1: 0.1861 → 0.8549)

### 3.5 vLLM BF16 merged ep2 — k=4 sampling T=0.7 (full dev, 3204 docs)

| 字段 | 值 |
|---|---|
| Run dir | `runs/sarge_infer_ChFinAnn-Doc2EDAG_dev_20260519T044351Z/` |
| Backend | vLLM 0.8.5, BF16 merged weights (§1.3) |
| 文档数 | 3204 |
| 解码 | k=4, do_sample=True, T=0.7, top_p=0.95 |
| Log | `logs/sarge_vllm_chfinann_fulldev_s13_k4_sample_T0.7_ep2_gpu3_20260519T122209Z.log` |

| Track | F1 | P | R | multi_F1 | single_F1 |
|---|---|---|---|---|---|
| legacy_doc2edag | 0.8432 | 0.7913 | 0.9023 | 0.8296 | 0.8594 |
| unified_strict | 0.8631 | 0.8100 | 0.9236 | 0.8569 | 0.8705 |
| docfee_official | 0.8583 | 0.8056 | 0.9185 | 0.8481 | 0.8705 |

> Sampling 损害 ChFinAnn：-1.2pp vs k=1 greedy。

### 3.6 HF 4-bit NF4 no-SFT baseline — k=1 greedy (limit=500)

| 字段 | 值 |
|---|---|
| Run dir | `runs/sarge_infer_ChFinAnn-Doc2EDAG_dev_20260519T045252Z/` |
| Backend | HF transformers, 4-bit NF4, 无 adapter |
| 文档数 | 500 |
| Log | `logs/sarge_hf_chfinann_500_noSFT_baseline_k1_4bitNF4_gpu3_20260519T125250Z.log` |

| Track | F1 | P | R | multi_F1 | single_F1 |
|---|---|---|---|---|---|
| legacy_doc2edag | 0.0273 | 0.2243 | 0.0145 | 0.0269 | 0.0279 |
| unified_strict | 0.0277 | 0.2226 | 0.0147 | 0.0275 | 0.0279 |
| docfee_official | 0.0261 | 0.2104 | 0.0139 | 0.0248 | 0.0279 |

---

## 4. 汇总对照

### 4.1 DuEE-Fin-dev500 (500 docs, seed 13)

| # | 实验 | 推理后端 | 量化 | Adapter | k | 解码 | legacy F1 | unified F1 | docfee F1 | multi_F1 | single_F1 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 2.1 | no-SFT baseline | HF transf. | 4-bit NF4 | 无 | ? | ? | 0.0382 | 0.0467 | 0.0456 | 0.0455 | 0.0274 |
| 2.7 | no-SFT baseline | vLLM | BF16 | 无 | 1 | greedy | 0.1125 | 0.1180 | 0.1170 | 0.0848 | 0.1506 |
| 2.2 | BF16 ep1 LoRA | HF transf. | 4-bit NF4 | BF16 ep1 | ? | ? | 0.6959 | 0.7092 | 0.7015 | 0.6697 | 0.7470 |
| 2.3 | vLLM merged ep2 | vLLM | BF16 | merged | 1 | greedy | 0.7275 | 0.7354 | 0.7312 | 0.6995 | 0.7818 |
| 2.4 | vLLM merged ep2 | vLLM | BF16 | merged | 4 | T=0.7 | 0.7228 | 0.7332 | 0.7303 | 0.7210 | 0.7488 |
| 2.5 | vLLM merged ep2 | vLLM | BF16 | merged | 4 | T=0.3 | 0.7386 | 0.7525 | 0.7500 | 0.7221 | 0.7794 |
| 2.6 | vLLM merged ep2 | vLLM | BF16 | merged | 4 | T=0.5 | 0.7265 | 0.7381 | 0.7332 | 0.7166 | 0.7638 |
| §1.1 | **HF 4-bit NF4 ep2** | HF transf. | 4-bit NF4 | 4-bit NF4 ep2 | 4* | sample* | **0.7704** | **0.7759** | **0.7711** | 0.7636 | 0.7903 |
| 2.9 | HF 4-bit NF4 ep2 | HF transf. | 4-bit NF4 | 4-bit NF4 ep2 | 1 | greedy | 0.7666 | 0.7723 | 0.7675 | 0.7536 | 0.7943 |

> *§1.1 的训练内置推理使用 k=4 sampling（历史参数），与 §2.3 的 k=1 greedy 不同。
> **关键发现**：同为 k=1 greedy 时，DuEE-Fin 上 vLLM BF16 比 HF 4-bit NF4 低约 3.9pp（0.7275 vs 0.7666）。差距来自推理路径数值差异（BF16 merged vs 4-bit NF4 + LoRA），非 `balanced_json_stopping` 截断（已验证 `balanced_stop_applied=False` 对所有 500 docs）。

### 4.2 ChFinAnn-Doc2EDAG

| # | 实验 | 推理后端 | 量化 | docs | k | 解码 | legacy F1 | unified F1 | docfee F1 | multi_F1 | single_F1 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 3.4 | no-SFT baseline | vLLM | BF16 | 3204 | 1 | greedy | 0.1861 | 0.1860 | 0.1815 | 0.0804 | 0.2946 |
| 3.1 | HF 4-bit NF4 ep2 | HF transf. | 4-bit NF4 | 500 | 1 | greedy | 0.8444 | 0.8604 | 0.8505 | 0.8164 | 0.8807 |
| 3.2 | vLLM merged ep2 | vLLM | BF16 | 500 | 1 | greedy | 0.8419 | 0.8600 | 0.8535 | 0.8102 | 0.8836 |
| 3.5 | vLLM merged ep2 | vLLM | BF16 | 3204 | 4 | T=0.7 | 0.8432 | 0.8631 | 0.8583 | 0.8296 | 0.8594 |
| **3.3** | **vLLM merged ep2** | vLLM | BF16 | **3204** | 1 | greedy | **0.8549** | **0.8705** | **0.8643** | 0.8307 | 0.8834 |
| 3.6 | HF no-SFT baseline | HF transf. | 4-bit NF4 | 500 | 1 | greedy | 0.0273 | 0.0277 | 0.0261 | 0.0269 | 0.0279 |

### 4.3 vs 已发表 SOTA (legacy_doc2edag track)

| Method | ChFinAnn F1 | DuEE-Fin F1 |
|---|---|---|
| Doc2EDAG | 78.8 | 63.4 |
| GIT | 80.3 | 67.8 |
| ProCNet | 80.8 | 75.1 |
| EPAL | 83.4 | 76.4 |
| SEELE | **85.1** | **80.8** |
| **SARGE (ours, vLLM BF16)** | **85.5** | **72.8** |
| **SARGE (ours, HF 4-bit NF4)** | **84.4** | **76.7** |

> **ChFinAnn**: vLLM BF16 超越 SEELE 0.4pp (85.5 vs 85.1)；HF 4-bit NF4 略低于 SEELE (84.4 vs 85.1)。
> **DuEE-Fin**: HF 4-bit NF4 k=1 greedy 路径 (76.7) 距 SEELE (80.8) 差 4.1pp；训练内置 k=4 sampling 历史结果为 77.0。vLLM BF16 路径 (72.8) 进一步落后。

---

## 5. 推理路径差异分析

vLLM BF16 merged 与 HF 4-bit NF4 + LoRA 之间存在系统性性能差距：

| 数据集 | HF 4-bit NF4 F1 | vLLM BF16 F1 | Δ |
|---|---|---|---|
| DuEE-Fin (k=1 greedy) | 0.7666 | 0.7275 | -3.9pp |
| DuEE-Fin (k=4 sample) | 0.7704 | 0.7228 | -4.8pp |
| ChFinAnn (k=1 greedy, 500 docs) | 0.8444 | 0.8419 | -0.3pp |

**已验证不是 `balanced_json_stopping` 截断问题**：全部 500 DuEE-Fin docs `balanced_stop_applied=False`，模型主动提前输出 EOS。

**结论**：§2.9 已完成，同解码策略下 HF 4-bit NF4 + LoRA 明显优于 vLLM BF16 merged。

---

## 6. 解码策略影响

| 数据集 | k=1 greedy | k=4 T=0.7 | Δ |
|---|---|---|---|
| DuEE-Fin (vLLM BF16) | 0.7275 | 0.7228 | -0.5pp |
| ChFinAnn (vLLM BF16, full dev) | 0.8549 | 0.8432 | -1.2pp |

> k=4 sampling 在两个数据集上均不利于 overall F1，但 DuEE-Fin 上 multi_F1 提升 +2.2pp (0.6995→0.7210)，single_F1 下降 -3.3pp (0.7818→0.7488)。T=0.3 和 T=0.5 均未优于 k=1 greedy。

---

## 7. LRD 原型诊断与 safe-anchor 复验

LRD 数据生成、预编码、pairwise BCE 训练和 dev postprocess 已在服务器执行。初始 LRD 合并边界过宽，低于 rule-planner 基线；2026-05-20 safe-anchor 修复后完成一次 seed 13 W8 复验。

| Run | checkpoint | tau | legacy F1 | legacy F1(M.) | unified F1 | exact-record F1 | 结论 |
|---|---|---:|---:|---:|---:|---:|---|
| `runs/sarge_postlrd_DuEE-Fin-dev500_dev_seed13_tau0.90/` | `runs/lrd/dueefin_train_seed13/checkpoints/lrd_planner.pt` | 0.90 | 0.6911 | 0.6157 | 0.6921 | 0.3471 | diagnostic only |
| `runs/sarge_postlrd_DuEE-Fin-dev500_dev_seed13_ep15_tau0.95/` | `runs/lrd/dueefin_train_seed13_ep15_lr5e5/checkpoints/lrd_planner.pt` | 0.95 | 0.6746 | 0.5776 | 0.6707 | 0.3159 | diagnostic only |
| `runs/sarge_postlrd_DuEE-Fin-dev500_dev_seed13_safe_anchor_tau0.90_20260520T001837Z/` | `runs/lrd/dueefin_train_seed13/checkpoints/lrd_planner.pt` | 0.90 | 0.7679 | 0.7550 | 0.7735 | 0.4181 | W8 seed13 pass candidate |

训练摘要：

| Run | train docs | epochs | objective | reward |
|---|---:|---:|---|---|
| `runs/lrd/dueefin_train_seed13/` | 1855 | 5 | pairwise_bce | disabled |
| `runs/lrd/dueefin_train_seed13_ep15_lr5e5/` | 1855 | 15 | pairwise_bce | disabled |

失败形态诊断（2026-05-20）：

| 对比 | rule planner | LRD tau=0.90 | 变化 |
|---|---:|---:|---:|
| legacy F1 | 0.7277 | 0.6911 | -0.0366 |
| TP / FP / FN | 2344 / 802 / 952 | 2080 / 643 / 1216 | TP -264, FP -159, FN +264 |
| validated records | 1292 | 1210 | -82 |
| fixed-slot pred units | 3146 | 2723 | -423 |
| collapsed multi-value roles | 209 | 347 | +138 |

最大降分来自 `被约谈`：rule F1 `0.7376`，LRD tau=0.90 F1 `0.1942`。典型错误是多条共享 `约谈机构` / `被约谈时间`、但 `公司名称` 不同的真实记录被 LRD 合成一条多值记录。

**根因**：LRD learned cluster 在合并阶段只约束同一 `event_type`，没有继承 rule planner 的 anchor/role 兼容边界；因此高相似但互斥的真实记录会被 union 成单条记录，固定槽位评测下表现为 recall 大幅下降。

**本地修复与复验**：`src/sarge/postprocess/lrd_planner.py` 已改为只合并通过 anchor/role 兼容检查的 cluster members，并新增单测锁定 `被约谈` anchor 冲突场景。服务器复验使用 GPU 0，命令输入为 `runs/sarge_infer_DuEE-Fin-dev500_dev_20260519T043458Z/intermediate/getm/parsed_candidates.dev.jsonl`，日志为 `logs/sarge_postlrd_DuEE-Fin-dev500_dev_seed13_safe_anchor_tau0.90_20260520T001837Z.log`。postprocess 输出 `docs=500 events_in=677 events_out=675`，评测三轨均已生成。

**W8 判定**：safe-anchor LRD seed13 复验通过候选 gate：legacy F1(M.) `0.7550` ≥ rule planner `0.6992` + 3pp，exact-record F1 `0.4181` ≥ `0.40`。这只证明 DuEE-Fin seed13 dev W8 复验通过；W9 test set 和 W11 seed 17/19 仍未执行，需作为后续单独阶段启动。

### 7.1 ProcNet comparable exact-record reference

服务器 `dee-fin` 中存在 ProcNet seed42 的 canonical prediction 与 `unified_strict` 评测结果，可作为 exact-record 的同口径参考。该结果来自 `/data/TJK/DEE/dee-fin/runs/baseline/procnet/procnet_duee_fin_dev500_seed42_es100/`；只使用 `eval/unified_strict.{dev,test}.json` 与 `canonical/*.canonical.{pred,gold}.jsonl`，不混用 `legacy_native_event_table` native 指标。

exact-record F1 口径：`2 * record_exact_match_count / validated_record_count`，其中 `validated_record_count = pred_record_count + gold_record_count`。

| System | Dataset | split | seed | pred records | gold records | exact matches | exact-record F1 | unified F1 | unified F1(M.) | unified F1(S.) | 证据 |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| ProcNet | DuEE-Fin-dev500 | dev | 42 | 659 | 674 | 158 | 0.2371 | 0.7042 | 0.6790 | 0.7364 | `runs/baseline/procnet/procnet_duee_fin_dev500_seed42_es100/eval/unified_strict.dev.json` |
| ProcNet | DuEE-Fin-dev500 | test | 42 | 1504 | 1533 | 344 | 0.2265 | 0.7066 | 0.6709 | 0.7506 | `runs/baseline/procnet/procnet_duee_fin_dev500_seed42_es100/eval/unified_strict.test.json` |

对比当前 SARGE dev seed13：no-LRD exact-record F1 `0.4175`，safe-anchor LRD exact-record F1 `0.4181`。因此，已有 dev 证据中 SARGE 的 exact-record 明显高于 ProcNet seed42 dev reference；test 仍需等待 W9 产物完成后再做同表比较。

### 7.2 W9 no-LRD test result

W9 no-LRD test set 使用 HF 4-bit NF4 + LoRA seed13、k=1 greedy 路径。推理已完成，run root 为 `runs/sarge_infer_DuEE-Fin-dev500_test_seed13_safe_anchor_source_f56a0d3_20260520T003122Z/sarge_infer_DuEE-Fin-dev500_test_20260520T003122Z/`，输出 `1171` docs、`1557` events，三轨评测已写入 `eval/`。

| Track | F1 | P | R | TP | FP | FN | multi_F1 | single_F1 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| legacy_doc2edag | 0.7796 | 0.7664 | 0.7933 | 5976 | 1822 | 1557 | 0.7751 | 0.7927 |
| unified_strict | 0.7888 | 0.7766 | 0.8014 | 6337 | 1823 | 1570 | 0.7836 | 0.8026 |
| docfee_official | 0.7771 | 0.7651 | 0.7896 | 6243 | 1917 | 1664 | 0.7622 | 0.8026 |

`unified_strict` diagnostics: `record_exact_match_count=662`, `validated_record_count=3090`，no-LRD test exact-record F1 `0.4285`。Schema-valid rate is `1.0`; parse failures, invalid event types, and invalid roles are all `0`.

---

## 8. 待执行

| # | 任务 | 预估 | 状态 |
|---|---|---|---|
| T=0.3 | DuEE-Fin 温度 ablation T=0.3 | ~2h | 已完成 |
| T=0.5 | DuEE-Fin 温度 ablation T=0.5 | ~2h | 已完成 |
| LRD W4-W7 | LRD 原型训练 + pipeline 集成 | ~9-12 GPU-h | 已完成；初始诊断失败，safe-anchor 修复已复验 |
| W8 | LRD hard gate 评测 | — | seed13 safe-anchor 复验通过候选 gate |
| W9 | Test set no-LRD 评测 | ~2-4 GPU-h | 已完成；safe-anchor LRD postprocess 待 GPU |
| W10 | Ablation 表 | — | gated on W9 LRD |
| W11 | 多种子 seed 17/19 | ~30 GPU-h | 未执行；需后续单独授权 |
| W12 | 预审 + 提交 | — | 2026-08 截稿 |

---

## 9. 环境与路径

| 资源 | 路径 |
|---|---|
| 服务器项目根 | `/data/TJK/DEE/SARGE/` |
| 服务器 Python (default) | `/data/TJK/envs/sarge_vllm_full/bin/python` |
| 服务器 runs | `/data/TJK/DEE/SARGE/runs/` |
| 服务器数据 | `/data/TJK/DEE/SARGE/data/` |
| Qwen 模型 | `/data/TJK/DEE/SARGE/models/Qwen/Qwen3-4B-Instruct-2507` |
| 评测器 | `/data/TJK/DEE/SARGE/evaluator/` |
| 评测脚本 | `scripts/eval_three_tracks.py` |
| 推理脚本 (HF) | `scripts/infer_checkpoint.py` |
| 推理脚本 (vLLM) | `scripts/infer_checkpoint_vllm.py` |
| 本地项目根 | `/home/tjk/myProjects/masterProjects/DEE/SARGE/` |
| 本地 Python | `/home/tjk/miniconda3/envs/feg-dev-py310/bin/python` |
