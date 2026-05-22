# SARGE 实验结果记录

> 最后更新：2026-05-22 09:40 UTC+8
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
| DuEE-Fin-dev500 | test | 13 | backend | vLLM BF16 + LoRA, k=1 | 0.7502 | 0.7480 | 0.7524 | 0.7857 | 0.7323 | fresh rerun；比 HF 主路径低 2.94pp |
| DuEE-Fin-dev500 | test | 17 | backend | vLLM BF16 + LoRA, k=1 | 0.7470 | 0.7515 | 0.7426 | 0.7875 | 0.7225 | backend seed-extension 诊断 |
| DuEE-Fin-dev500 | test | 42 | backend | vLLM BF16 + LoRA, k=1 | 0.7583 | 0.7579 | 0.7588 | 0.7941 | 0.7378 | backend seed-extension 诊断 |
| DuEE-Fin-dev500 | test | 13 | no-SFT | HF-4bin base, k=1 | 0.0330 | 0.4479 | 0.0171 | 0.0368 | 0.0304 | HF no-SFT 极低，确认 SFT 必要 |
| DuEE-Fin-dev500 | test | 13 | no-SFT | vLLM BF16 base, k=1 | 0.1129 | 0.3722 | 0.0665 | 0.1378 | 0.0936 | SFT 是主要增益来源 |
| DuEE-Fin-dev500 | test | 13 | decoding | vLLM BF16 + LoRA, k=4 T=0.7 | 0.7313 | 0.6922 | 0.7751 | 0.7583 | 0.7249 | sampling 未优于 k=1 |
| DuEE-Fin-dev500 | test | 13 | LRD | safe-anchor tau=0.90 | 0.7800 | 0.7671 | 0.7933 | 0.7937 | 0.7751 | 增益很小；LRD 保持诊断/附录 |

---

## 3. Dev 与多种子诊断

这些结果用于种子稳定性和错误形态分析，不进入 test 主表。

| Dataset | Split | Seed | Setting | Legacy-FS F1 | Unified F1 | DocFEE F1 | ExactRec | Status |
|---|---|---:|---|---:|---:|---:|---:|---|
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
| ChFinAnn-Doc2EDAG | 17 | 2 | 25632 | 38088 | 30152.7s | `runs/sarge_sft_ChFinAnn_Doc2EDAG_s17_ep2_gpu1/` | completed; test inference running on GPU2 |
| ChFinAnn-Doc2EDAG | 42 | 2 | 25632 | 38088 | - | `runs/sarge_sft_ChFinAnn_Doc2EDAG_s42_ep2_gpu1/` | running on GPU1 |

---

## 5. 运行中任务

| Task | GPU | Log | Status |
|---|---:|---|---|
| ChFinAnn test seed17 HF-4bin + LoRA k=1 | 2 | `logs/sarge_infer_ChFinAnn-Doc2EDAG_test_seed17_4bitNF4_k1_20260521T231147Z.log` | running |
| ChFinAnn train seed42 HF-4bin LoRA ep2 --skip-eval | 1 | `logs/sarge_sft_ChFinAnn-Doc2EDAG_s42_ep2_gpu1_20260521T143813Z.log` | running |
| ChFinAnn seed42 train-to-test watcher | 1 | `logs/sarge_watch_ChFinAnn_seed42_train_to_test_gpu1_20260522T010434Z.log` | waiting for adapter, then starts HF test + three-track eval |

运行中任务完成后再拉快照、补 registry 和表格；完成前不进入主表。
