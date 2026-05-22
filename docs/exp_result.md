# SARGE 实验结果记录

> 最后更新：2026-05-23 00:45 UTC+8
> 证据来源：服务器 `/data/TJK/DEE/SARGE/runs/` 的已完成 run；小型 JSON 快照已收拢到 `paper/exp/data/run_snapshots/`，索引见 `paper/exp/data/asset_registry.json`。

---

## 1. 当前主结果

主表口径为 `legacy_doc2edag` / Legacy-FS。`unified_strict`、`docfee_official` 和 ExactRec 只作为诊断指标，不与主表基线混算。

| Dataset | Split | Seed | 主设置 | Asset | Legacy-FS F1 | P | R | F1(S) | F1(M) | Unified F1 | DocFEE F1 | ExactRec |
|---|---|---:|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| ChFinAnn-Doc2EDAG | test | 13 | HF-4bin + LoRA, k=1 greedy | `chfinann_test_seed13_hf4bin_k1` | 0.8603 | 0.8437 | 0.8775 | 0.8995 | 0.8182 | 0.8742 | 0.8653 | 0.5842 |
| DuEE-Fin-dev500 | test | 13 | HF-4bin + LoRA, k=1 greedy, no-LRD | `dueefin_test_seed13_hf4bin_k1_no_lrd` | 0.7796 | 0.7664 | 0.7933 | 0.7927 | 0.7751 | 0.7888 | 0.7771 | 0.4285 |

ChFinAnn 主结果已从原 vLLM BF16 行切换到 HF-4bin cross-check 行，因为 full-test HF-4bin Legacy-FS F1 为 `0.8603`，高于 vLLM BF16 的 `0.8547`，且与 DuEE-Fin 主路径保持一致。

---

## 2. Test 消融与诊断

| Dataset | Split | Seed | Factor | Setting | Legacy-FS F1 | P | R | F1(S) | F1(M) | 结论 |
|---|---|---:|---|---|---:|---:|---:|---:|---:|---|
| ChFinAnn-Doc2EDAG | test | 13 | backend | HF-4bin + LoRA, k=1 | 0.8603 | 0.8437 | 0.8775 | 0.8995 | 0.8182 | 当前 ChFinAnn 主路径 |
| ChFinAnn-Doc2EDAG | test | 13 | backend | vLLM BF16 + LoRA, k=1 | 0.8547 | 0.8407 | 0.8691 | 0.8978 | 0.8082 | 后端交叉验证，略低于 HF |
| ChFinAnn-Doc2EDAG | test | 13 | no-SFT | vLLM BF16 base, k=1 | 0.2482 | 0.6119 | 0.1556 | 0.3893 | 0.0675 | SFT 是主要增益来源 |
| ChFinAnn-Doc2EDAG | test | 13 | decoding | vLLM BF16 + LoRA, k=4 T=0.7 | 0.8421 | 0.7954 | 0.8945 | 0.8752 | 0.8071 | sampling 未优于 k=1 |
| DuEE-Fin-dev500 | test | 13 | backend | HF-4bin + LoRA, k=1 | 0.7796 | 0.7664 | 0.7933 | 0.7927 | 0.7751 | 当前 DuEE-Fin 主路径 |
| DuEE-Fin-dev500 | test | 13 | module | HF-4bit no surface memory | 0.7812 | 0.7653 | 0.7978 | 0.7975 | 0.7767 | HF 单变量确认：去掉 Surface Memory 未造成可见下降；no_slot_plan 仍在跑 |
| DuEE-Fin-dev500 | test | 13 | backend | vLLM BF16 + LoRA, k=1 | 0.7502 | 0.7480 | 0.7524 | 0.7857 | 0.7323 | fresh rerun；比 HF 主路径低 2.94pp |
| DuEE-Fin-dev500 | test | 17 | backend | vLLM BF16 + LoRA, k=1 | 0.7470 | 0.7515 | 0.7426 | 0.7875 | 0.7225 | backend seed-extension 诊断 |
| DuEE-Fin-dev500 | test | 42 | backend | vLLM BF16 + LoRA, k=1 | 0.7583 | 0.7579 | 0.7588 | 0.7941 | 0.7378 | backend seed-extension 诊断 |
| DuEE-Fin-dev500 | test | 13 | module-fast-screen | vLLM no surface memory | 0.0208 | 0.4520 | 0.0106 | 0.0358 | 0.0092 | vLLM 0.70 显存配置下召回坍塌；只作快筛/故障形态证据 |
| DuEE-Fin-dev500 | test | 13 | module-fast-screen | vLLM no slot plan | 0.0164 | 0.4565 | 0.0084 | 0.0289 | 0.0069 | vLLM 0.70 显存配置下召回坍塌；只作快筛/故障形态证据 |
| DuEE-Fin-dev500 | test | 13 | module-fast-screen | vLLM no surface or slot | 0.7549 | 0.7509 | 0.7589 | 0.7831 | 0.7419 | 与 full vLLM 接近，提示 profile 与 vLLM 输出控制存在交互 |
| DuEE-Fin-dev500 | test | 13 | coarse-lower-bound | vLLM schema only | 0.6555 | 0.7527 | 0.5805 | 0.7091 | 0.6122 | 非单变量；附录/诊断下界 |
| DuEE-Fin-dev500 | test | 13 | coarse-lower-bound | vLLM direct json | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 最弱直接抽取失败 |
| DuEE-Fin-dev500 | test | 13 | no-SFT | HF-4bin base, k=1 | 0.0330 | 0.4479 | 0.0171 | 0.0368 | 0.0304 | HF no-SFT 极低，确认 SFT 必要 |
| DuEE-Fin-dev500 | test | 13 | no-SFT | vLLM BF16 base, k=1 | 0.1129 | 0.3722 | 0.0665 | 0.1378 | 0.0936 | SFT 是主要增益来源 |
| DuEE-Fin-dev500 | test | 13 | decoding | vLLM BF16 + LoRA, k=4 T=0.7 | 0.7313 | 0.6922 | 0.7751 | 0.7583 | 0.7249 | sampling 未优于 k=1 |
| DuEE-Fin-dev500 | test | 13 | LRD | safe-anchor tau=0.90 | 0.7800 | 0.7671 | 0.7933 | 0.7937 | 0.7751 | 增益很小；LRD 保持诊断/附录 |

---

## 3. Dev 与多种子诊断

这些结果用于种子稳定性和错误形态分析，不进入 test 主表。

| Dataset | Split | Seed | Setting | Legacy-FS F1 | Unified F1 | DocFEE F1 | ExactRec | Status |
|---|---|---:|---|---:|---:|---:|---:|---|
| ChFinAnn-Doc2EDAG | test | 17 | HF-4bin + LoRA, k=1 | 0.8536 | 0.8705 | 0.8627 | 0.5532 | seed-extension diagnostic |
| DuEE-Fin-dev500 | test | 17 | HF-4bin + LoRA, k=1, no-LRD | 0.7872 | 0.7937 | 0.7822 | 0.4314 | seed-extension diagnostic |
| DuEE-Fin-dev500 | test | 42 | HF-4bin + LoRA, k=1, no-LRD | 0.7828 | 0.7921 | 0.7809 | 0.4382 | seed-extension diagnostic |
| DuEE-Fin-dev500 | test | mean±std | HF seeds 13/17/42, no-LRD | 0.7832±0.0038 | 0.7915±0.0025 | 0.7801±0.0026 | 0.4327±0.0050 | stability diagnostic |
| DuEE-Fin-dev500 | dev | 13 | HF-4bin + LoRA, k=1 | 0.7666 | 0.7723 | 0.7675 | 0.4175 | valid diagnostic |
| DuEE-Fin-dev500 | dev | 17 | train_sft k=4 + MRS selected, no-LRD | 0.7794 | 0.7849 | 0.7812 | 0.4187 | valid diagnostic |
| DuEE-Fin-dev500 | dev | 42 | train_sft k=4 + MRS selected, no-LRD | 0.7669 | 0.7736 | 0.7688 | 0.4186 | valid diagnostic |
| DuEE-Fin-dev500 | dev | 17 | LRD over all k=4 parsed candidates | 0.3354 | 0.3458 | 0.3458 | 0.1809 | invalid |

Seed17 dev LRD `0.3354` 是输入契约误用诊断：`postprocess_lrd_eval.py` 吃入 `parsed_candidates.dev.jsonl` 的全部 k=4 候选，`events_in=2692`、`events_out=2444`，而 fair no-LRD/MRS 预测只有 `673` 个事件。该结果不得作为 seed17 模型或 LRD 性能报告。

---

## 4. 训练资产

| Dataset | Seed | Epochs | Train docs | Train events | Train time | Run root | Status |
|---|---:|---:|---:|---:|---:|---|---|
| DuEE-Fin-dev500 | 13 | 2 | 6515 | 8824 | 9970.7s | `runs/sarge_sft_DuEE_Fin_dev500_s13_ep2_gpu0/` | completed |
| DuEE-Fin-dev500 | 17 | 2 | 6515 | 8824 | 9840.3s | `runs/sarge_sft_DuEE_Fin_dev500_s17_ep2_gpu0/` | completed |
| DuEE-Fin-dev500 | 42 | 2 | 6515 | 8824 | 10025.2s | `runs/sarge_sft_DuEE_Fin_dev500_s42_ep2_gpu1/` | completed |
| ChFinAnn-Doc2EDAG | 13 | 2 | 25632 | 38088 | 30310.2s | `runs/sarge_sft_ChFinAnn_Doc2EDAG_s13_ep2_gpu1/` | completed |
| ChFinAnn-Doc2EDAG | 17 | 2 | 25632 | 38088 | 30152.7s | `runs/sarge_sft_ChFinAnn_Doc2EDAG_s17_ep2_gpu1/` | completed; test eval synced |
| ChFinAnn-Doc2EDAG | 42 | 2 | 25632 | 38088 | - | `runs/sarge_sft_ChFinAnn_Doc2EDAG_s42_ep2_gpu1/` | test inference running on GPU1 |

---

## 5. 运行中任务

| Task | GPU | Log | Status |
|---|---:|---|---|
| ChFinAnn test seed42 HF-4bin + LoRA k=1 | 1 | `logs/sarge_watch_ChFinAnn_seed42_train_to_test_gpu1_20260522T010434Z.log` / `runs/sarge_infer_ChFinAnn-Doc2EDAG_test_seed42_4bitNF4_k1_20260522T080426Z/` | running; only partial diagnostics exist, no eval JSON yet |
| DuEE-Fin test seed13 HF-4bit no_slot_plan | 1 | parent `runs/sarge_ablation_DuEE-Fin-dev500_test_seed13_no_slot_plan_hf4bit_k1_20260522T152510Z/` | running; no eval JSON yet |

运行中任务完成后再拉快照、补 registry 和表格；完成前不进入主表。

---

## 6. API 诊断

DeepSeek API 诊断是 CPU/API-only，不使用 GPU，不进入论文主表。汇总文件为 `paper/exp/data/api_diagnostics/deepseek_api_diagnostics_20260522.json`，报告为 `docs/deepseek_api_diagnostics_20260522.md`。

关键结果：修复响应预算后，DuEE-Fin dev500 full prompt 达到 flash Legacy-FS F1 `0.4529`、pro `0.4348`；`schema_only` 和 `surface_only` 没有追上本地 SARGE checkpoint。临时 value normalization probe 将 flash/pro full prompt 提升到 `0.5046` / `0.4849`，说明主要问题是输出值表面形式与评测规范不匹配，而不是 DeepSeek API 连接失败。
