# SARGE 实验结果记录

> 最后更新：2026-05-18 22:00 UTC+8
> 所有数据从服务器实际文件读取，非记忆推断。

---

## 1. 训练产物

### 1.1 DuEE-Fin-dev500 — 4-bit NF4, epoch 2, seed 13 ✅

| 字段 | 值 | 来源 |
|---|---|---|
| Run dir | `runs/sarge_sft_DuEE_Fin_dev500_s13_ep2_gpu0/` | `summary_train.json` |
| 量化 | **4-bit NF4** | `training_manifest.json: quantization="4-bit NF4"` |
| compute_dtype | bf16 | `training_manifest.json` |
| LoRA rank | 16 | `training_manifest.json` |
| train docs | 6515 | `summary_train.json` |
| SFT rows | 6515 (8824 events) | `summary_train.json` |
| epochs | **2** | `summary_train.json` |
| train loss | 0.0791 | `training_manifest.json` |
| train time | 9944s (166 min) | `summary_train.json` |
| GPU | 0 | `summary_train.json` |
| Adapter | `artifacts/model/adapter/` | `summary_train.json` |
| Checkpoints | checkpoint-408 (ep1), checkpoint-816 (ep2) | `summary_train.json` |

### 1.2 ChFinAnn-Doc2EDAG — 4-bit NF4, epoch 2, seed 13 ✅

| 字段 | 值 | 来源 |
|---|---|---|
| Run dir | `runs/sarge_sft_ChFinAnn_Doc2EDAG_s13_ep2_gpu1/` | `summary_train.json` |
| 量化 | **4-bit NF4** | `training_manifest.json: quantization="4-bit NF4"` |
| compute_dtype | bf16 | `training_manifest.json` |
| LoRA rank | 16 | `training_manifest.json` |
| train docs | 25632 | `summary_train.json` |
| SFT rows | 25632 (38088 events) | `summary_train.json` |
| epochs | **2** | `summary_train.json` |
| train loss | 0.0202 | `training_manifest.json` |
| train time | 30229s (504 min = 8.4h) | `summary_train.json` |
| GPU | 1 | `summary_train.json` |
| Adapter | `artifacts/model/adapter/` | `summary_train.json` |
| Checkpoints | checkpoint-3204 (ep1), checkpoint-6408 (ep2) | `summary_train.json` |

### 1.3 DuEE-Fin-dev500 — BF16 (无量化), epoch 1, seed 13 ✅

| 字段 | 值 | 来源 |
|---|---|---|
| Run dir | `runs/sarge_sft_DuEE_Fin_dev500_s13_ep1_gpu3/` | `summary_train.json` |
| 量化 | **无 (BF16 full precision)** | `training_manifest.json: quantization=null` |
| compute_dtype | bf16 | `training_manifest.json` |
| LoRA rank | 16 | `training_manifest.json` |
| train docs | 6515 | `summary_train.json` |
| SFT rows | 6515 (8824 events) | `summary_train.json` |
| epochs | **1** | `summary_train.json` |
| train loss | 0.1006 | `training_manifest.json` |
| train time | 4038s (67 min) | `summary_train.json` |
| GPU | 3 | `summary_train.json` |
| Adapter | `artifacts/model/adapter/` | `summary_train.json` |
| Checkpoints | checkpoint-408 (ep1) | `summary_train.json` |

> **注意**：此 adapter 训练时 base model 为 BF16 全精度（无 4-bit 量化），与 §1.1 的 4-bit NF4 训练不同。
> 推理时 base model 仍以 4-bit NF4 加载，仅 LoRA adapter 权重来自 BF16 训练。

### 1.4 无效训练产物 ❌

| Run dir | 状态 | 证据 |
|---|---|---|
| `sarge_sft_ChFinAnn_Doc2EDAG_s13_ep1_gpu1/` | 仅 train.log，无 adapter/manifest | 目录只有 `train.log` |
| `sarge_sft_ChFinAnn_Doc2EDAG_s13_ep3_gpu1/` | 仅 train.log，无 adapter/manifest | 同上 |
| `sarge_sft_DuEE_Fin_dev500_s13_ep1_gpu0/` | 仅 train.log，无 adapter/manifest | 同上（4-bit ep1，与 §1.3 重复但未完成） |
| `sarge_sft_DuEE_Fin_dev500_s13_ep3_gpu0/` | 仅 train.log，无 adapter/manifest | 同上 |
| `sarge_sft_DuEE_Fin_dev500_s13_ep1_bf16_gpu3/` | 仅 train.log，无 adapter/manifest | 误命名目录，实际产物在 §1.3 |

---

## 2. 推理与评测

### 2.1 DuEE-Fin-dev500 — Qwen3-4B no-SFT baseline (50 docs) ✅

| 字段 | 值 | 来源 |
|---|---|---|
| Run dir | `runs/sarge_infer_DuEE-Fin-dev500_dev_20260518T031935Z/` | log `DONE pred=...` |
| 模型 | Qwen3-4B-Instruct-2507, 4-bit NF4, **无 adapter** | 启动参数 `--no-adapter` |
| docs / events | 50 / 40 | log |
| 推理耗时 | 597s (10 min) | log |
| GPU | 3 | 启动 `CUDA_VISIBLE_DEVICES=3` |

| Track | F1 | P | R | multi_F1 | single_F1 | 来源 |
|---|---|---|---|---|---|---|
| legacy_doc2edag | 0.0369 | 0.4615 | 0.0192 | 0.0426 | 0.0292 | `eval/eval_legacy_doc2edag.json` |
| unified_strict | 0.0403 | 0.3182 | 0.0215 | 0.0400 | 0.0408 | `eval/eval_unified_strict.json` |
| docfee_official | 0.0346 | 0.2727 | 0.0185 | 0.0300 | 0.0408 | `eval/eval_docfee_official.json` |

### 2.2 DuEE-Fin-dev500 — Qwen3-4B no-SFT baseline (full dev) ✅

| 字段 | 值 | 来源 |
|---|---|---|
| Run dir | `runs/sarge_infer_DuEE-Fin-dev500_dev_20260518T033841Z/` | log `DONE pred=...` |
| 模型 | Qwen3-4B-Instruct-2507, 4-bit NF4, **无 adapter** | 启动参数 `--no-adapter` |
| docs / events | 500 / 398 | log |
| 推理耗时 | 6435s (107 min) | log |
| GPU | 3 | 启动 `CUDA_VISIBLE_DEVICES=3` |

| Track | F1 | P | R | multi_F1 | single_F1 | 来源 |
|---|---|---|---|---|---|---|
| legacy_doc2edag | 0.0382 | 0.5909 | 0.0197 | 0.0455 | 0.0274 | `eval/eval_legacy_doc2edag.json` |
| unified_strict | 0.0467 | 0.6269 | 0.0243 | 0.0529 | 0.0378 | `eval/eval_unified_strict.json` |
| docfee_official | 0.0456 | 0.6119 | 0.0237 | 0.0510 | 0.0378 | `eval/eval_docfee_official.json` |

### 2.3 DuEE-Fin-dev500 — 4-bit NF4, epoch 2, seed 13 ✅

| 字段 | 值 | 来源 |
|---|---|---|
| Run dir | `runs/sarge_sft_DuEE_Fin_dev500_s13_ep2_gpu0/` | `summary.json` |
| Adapter | §1.1 (4-bit NF4 ep2) | `summary.json: adapter_dir` |
| 推理方式 | `train_sft.py` 内置（训完即推） | `summary.json: infer_secs` |
| docs / events / args | 500 / 681 / 3603 | `summary.json` |
| 推理耗时 | 12401.9s (207 min) | `summary.json` |

| Track | F1 | P | R | multi_F1 | single_F1 | 来源 |
|---|---|---|---|---|---|---|
| legacy_doc2edag | 0.7704 | 0.7547 | 0.7867 | 0.7636 | 0.7903 | `eval_legacy_ep2.json` |
| unified_strict | 0.7759 | 0.7608 | 0.7917 | 0.7724 | 0.7911 | `eval_unified_ep2.json` |
| docfee_official | 0.7711 | 0.7560 | 0.7868 | 0.7639 | 0.7911 | `eval_docfee_ep2.json` |

### 2.4 DuEE-Fin-dev500 — BF16-trained ep1 LoRA, full dev ✅

| 字段 | 值 | 来源 |
|---|---|---|
| Run dir | `runs/sarge_infer_DuEE-Fin-dev500_dev_20260518T055217Z/` | log `DONE pred=...` |
| Base model | Qwen3-4B-Instruct-2507, 4-bit NF4 | 启动参数（默认 4-bit） |
| Adapter | §1.3 (BF16 训练 ep1 LoRA) | 启动参数 `--ckpt ...ep1_gpu3/artifacts/model/adapter` |
| docs / events | 500 / 699 | log |
| 推理耗时 | 12709s (212 min) | log |
| GPU | 3（与 ChFinAnn P0 共享） | 启动 `CUDA_VISIBLE_DEVICES=3` |

| Track | F1 | P | R | multi_F1 | single_F1 | 来源 |
|---|---|---|---|---|---|---|
| legacy_doc2edag | 0.6959 | 0.6870 | 0.7051 | 0.6697 | 0.7470 | `eval/eval_legacy_doc2edag.json` |
| unified_strict | 0.7092 | 0.7008 | 0.7178 | 0.6911 | 0.7490 | `eval/eval_unified_strict.json` |
| docfee_official | 0.7015 | 0.6932 | 0.7100 | 0.6771 | 0.7490 | `eval/eval_docfee_official.json` |

### 2.5 ChFinAnn-Doc2EDAG — 4-bit NF4 ep2 LoRA, limit=500, seed 13 ✅

| 字段 | 值 | 来源 |
|---|---|---|
| Run dir | `runs/sarge_infer_ChFinAnn-Doc2EDAG_dev_20260518T113445Z/` | log `DONE pred=...` |
| Base model | Qwen3-4B-Instruct-2507, 4-bit NF4 | 启动参数 |
| Adapter | §1.2 (4-bit NF4 ep2) | 启动参数 `--ckpt ...ep2_gpu1/artifacts/model/adapter` |
| docs / events | 500 / 834 | log |
| 推理耗时 | 5464s (91 min) | log |
| GPU | 3，k=1 贪婪解码 | 启动 `CUDA_VISIBLE_DEVICES=3 --k 1` |

| Track | F1 | P | R | multi_F1 | single_F1 | 来源 |
|---|---|---|---|---|---|---|
| legacy_doc2edag | 0.8444 | 0.8245 | 0.8653 | 0.8164 | 0.8807 | `eval/eval_legacy_doc2edag.json` |
| unified_strict | 0.8604 | 0.8401 | 0.8816 | 0.8398 | 0.8870 | `eval/eval_unified_strict.json` |
| docfee_official | 0.8505 | 0.8304 | 0.8715 | 0.8223 | 0.8870 | `eval/eval_docfee_official.json` |

---

## 3. 汇总对照

### DuEE-Fin-dev500 全量 dev (500 docs, seed 13)

| 实验 | 量化 | epoch | k | F1 (legacy) | F1 (unified) | F1 (docfee) | multi_F1 | single_F1 |
|---|---|---|---|---|---|---|---|
| no-SFT baseline | 4-bit NF4 | — | 4 | 0.0382 | 0.0467 | 0.0456 | 0.0455 | 0.0274 |
| BF16-trained LoRA | BF16 (无量化) | 1 | 4 | 0.6959 | 0.7092 | 0.7015 | 0.6697 | 0.7470 |
| 4-bit NF4 LoRA | 4-bit NF4 | 2 | 4* | **0.7704** | **0.7759** | **0.7711** | 0.7636 | 0.7903 |

### ChFinAnn-Doc2EDAG 500-doc 子集 (seed 13)

| 实验 | 量化 | epoch | k | F1 (legacy) | F1 (unified) | F1 (docfee) | multi_F1 | single_F1 |
|---|---|---|---|---|---|---|---|
| 4-bit NF4 LoRA | 4-bit NF4 | 2 | 1 | **0.8444** | **0.8604** | **0.8505** | 0.8164 | 0.8807 |

### vs 已发表 SOTA (legacy_doc2edag track)

| Method | ChFinAnn F1 | DuEE-Fin F1 |
|---|---|---|
| Doc2EDAG | 78.8 | 63.4 |
| GIT | 80.3 | 67.8 |
| ProCNet | 80.8 | 75.1 |
| EPAL | 83.4 | 76.4 |
| SEELE | **85.1** | **80.8** |
| **SARGE (ours)** | **84.4** | **77.0** |

> **解码策略**：所有实验使用 greedy decoding（`do_sample=False`）。在此设置下 `k>1` 生成相同输出，多候选选择无增益。ChFinAnn 实验使用 `k=1` 贪婪直出；DuEE-Fin ep2 使用 `k=4`（训练内置推理的历史参数）。后续计划在 DuEE-Fin 上做 k=1 vs k=4 sampling 对比消融，验证解码策略影响。

---

## 4. 待执行

| # | 任务 | 预估 GPU-h | 备注 |
|---|---|---|---|
| LRD W4-W7 | LRD 原型训练 + pipeline 集成 | ~9-12 | plan W4-W7，依赖 ChFinAnn dev 数字（已达标） |
| W8 | LRD hard gate 评测 | — | F1(M.) +3pp vs rule planner |
| W9 | Test set 评测 | ~2-4 | 主表 8 列填齐 |
| W10 | Ablation 表 | — | 4 行 ablation |
| W11 | 多种子 seed 17/19 | ~30 | gated on W8 |
| W12 | 预审 + 提交 | — | 8 月截稿 |

---

## 5. 环境与路径

| 资源 | 路径 |
|---|---|
| 服务器项目根 | `/data/TJK/DEE/SARGE/` |
| 服务器 Python | `/home/TJK/.conda/envs/tjk-feg/bin/python` |
| 服务器 runs | `/data/TJK/DEE/SARGE/runs/` |
| 服务器数据 | `/data/TJK/DEE/SARGE/data/` |
| 服务器模型 | `/data/TJK/DEE/SARGE/models/Qwen/Qwen3-4B-Instruct-2507` |
| 本地项目根 | `/home/tjk/myProjects/masterProjects/DEE/SARGE/` |
| 本地 Python | `/home/tjk/miniconda3/envs/feg-dev-py310/bin/python` |
| 评测器 | `/data/TJK/DEE/SARGE/evaluator/` |
| 评测脚本 | `scripts/eval_three_tracks.py` (本地+服务器双份) |
| 推理脚本 | `scripts/infer_checkpoint.py` (本地+服务器双份) |
