# GPU 待办任务清单

> 最后更新：2026-05-20 11:38 UTC+8
> 目标：GPU 一旦空闲，可以直接按本文件启动后续任务；不把后续工作限定在 vLLM。

---

## 当前活动任务

| 字段 | 值 |
|---|---|
| 服务器项目根 | `/data/TJK/DEE/SARGE/` |
| 服务器 Python | `/data/TJK/envs/sarge_vllm_full/bin/python` |
| 当前正式任务 | W9 no-LRD HF test inference + 三轨评测已完成；safe-anchor LRD postprocess 待启动 |
| 进程 | 原 `PID 2080437` 已结束 |
| Run root | `runs/sarge_infer_DuEE-Fin-dev500_test_seed13_safe_anchor_source_f56a0d3_20260520T003122Z/sarge_infer_DuEE-Fin-dev500_test_20260520T003122Z/` |
| Log | `logs/sarge_infer_DuEE-Fin-dev500_test_seed13_safe_anchor_source_f56a0d3_20260520T003122Z.log` |
| Source commit | server `f56a0d3`, local equivalent change `8bdb6a9` |
| 当前原则 | 不在非空闲 GPU 上启动新任务；下一步优先接 W9 safe-anchor LRD postprocess |

只读状态检查：

```bash
ssh gpu-4090 'ps -eo user,pid,etime,cmd | grep -E "2080437|infer_checkpoint.py|infer_checkpoint_vllm.py|postprocess_lrd_eval.py" | grep -v grep || true'
ssh gpu-4090 'nvidia-smi --query-gpu=index,memory.used,memory.total,utilization.gpu --format=csv,noheader,nounits'
ssh gpu-4090 'cd /data/TJK/DEE/SARGE && tail -30 logs/sarge_infer_DuEE-Fin-dev500_test_seed13_safe_anchor_source_f56a0d3_20260520T003122Z.log'
```

---

## 已完成的非 GPU 准备

以下路径已在服务器确认存在：

| 用途 | 路径 |
|---|---|
| DuEE-Fin test data | `data/DuEE-Fin-dev500/test.jsonl` |
| DuEE-Fin seed13 LoRA adapter | `runs/sarge_sft_DuEE_Fin_dev500_s13_ep2_gpu0/artifacts/model/adapter/adapter_config.json` |
| LRD seed13 checkpoint | `runs/lrd/dueefin_train_seed13/checkpoints/lrd_planner.pt` |
| LRD RoBERTa encoder | `models/chinese-roberta-wwm-ext_safetensors/config.json` |
| DuEE-Fin merged BF16 for vLLM diagnostics | `runs/merged_models/qwen3_4b_dueefin_ep2_s13/config.json` |
| ChFinAnn merged BF16 for vLLM diagnostics | `runs/merged_models/qwen3_4b_chfinann_ep2_s13/config.json` |

已确认可用脚本：

| 用途 | 脚本 |
|---|---|
| HF 4-bit NF4 + LoRA inference | `scripts/infer_checkpoint.py` |
| vLLM BF16 merged inference / SACD diagnostics | `scripts/infer_checkpoint_vllm.py` |
| safe-anchor LRD postprocess | `scripts/postprocess_lrd_eval.py` |
| 三轨评测 | `scripts/eval_three_tracks.py` |
| SFT 训练 | `scripts/train_sft.py` |
| LRD 训练 | `scripts/train_lrd.py` |

通用启动前检查：

```bash
ssh gpu-4090 'cd /data/TJK/DEE/SARGE && git branch --show-current && git status --short'
ssh gpu-4090 'cd /data/TJK/DEE/SARGE && for p in data/DuEE-Fin-dev500/test.jsonl runs/sarge_sft_DuEE_Fin_dev500_s13_ep2_gpu0/artifacts/model/adapter/adapter_config.json runs/lrd/dueefin_train_seed13/checkpoints/lrd_planner.pt models/chinese-roberta-wwm-ext_safetensors/config.json; do test -e "$p" && echo OK "$p" || echo MISSING "$p"; done'
ssh gpu-4090 'nvidia-smi'
```

共享服务器约束：只使用空闲 GPU；kill 前必须确认进程 owner 是 `TJK`，禁止 kill 其他用户进程。

---

## P0 - W9 Test Set 正式链路

### 1. HF test inference + no-LRD 三轨评测

已完成。产物：

- `runs/sarge_infer_DuEE-Fin-dev500_test_seed13_safe_anchor_source_f56a0d3_20260520T003122Z/sarge_infer_DuEE-Fin-dev500_test_20260520T003122Z/intermediate/getm/parsed_candidates.test.jsonl`
- `runs/sarge_infer_DuEE-Fin-dev500_test_seed13_safe_anchor_source_f56a0d3_20260520T003122Z/sarge_infer_DuEE-Fin-dev500_test_20260520T003122Z/predictions/DuEE-Fin-dev500/test.canonical.pred.jsonl`
- `runs/sarge_infer_DuEE-Fin-dev500_test_seed13_safe_anchor_source_f56a0d3_20260520T003122Z/sarge_infer_DuEE-Fin-dev500_test_20260520T003122Z/eval/eval_{legacy_doc2edag,unified_strict,docfee_official}.json`

No-LRD test summary:

| Track | F1 | P | R | multi_F1 | single_F1 |
|---|---:|---:|---:|---:|---:|
| legacy_doc2edag | 0.7796 | 0.7664 | 0.7933 | 0.7751 | 0.7927 |
| unified_strict | 0.7888 | 0.7766 | 0.8014 | 0.7836 | 0.8026 |
| docfee_official | 0.7771 | 0.7651 | 0.7896 | 0.7622 | 0.8026 |

No-LRD test exact-record F1 is `0.4285` (`record_exact_match_count=662`, `validated_record_count=3090`).

Do not rerun unless the artifact is found corrupt. If rerun is necessary, use a new run name:

如果当前进程失败或消失，先读 log 和 output tree；不要覆盖原 run。重启命令另起新 run name：

```bash
cd /data/TJK/DEE/SARGE
RUN=sarge_infer_DuEE-Fin-dev500_test_seed13_safe_anchor_source_f56a0d3_$(date -u +%Y%m%dT%H%M%SZ)
LOG=logs/${RUN}.log
GPU=REPLACE_WITH_IDLE_GPU_ID
CUDA_VISIBLE_DEVICES=${GPU} \
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 HF_DATASETS_OFFLINE=1 \
PYTHONPATH=src \
/data/TJK/envs/sarge_vllm_full/bin/python -B scripts/infer_checkpoint.py \
  --ckpt runs/sarge_sft_DuEE_Fin_dev500_s13_ep2_gpu0/artifacts/model/adapter \
  --dataset DuEE-Fin-dev500 \
  --split test \
  --k 1 \
  --seed 13 \
  --slot-train-limit 50 \
  --source-commit f56a0d3 \
  --out runs/${RUN} > ${LOG} 2>&1
```

### 2. W9 safe-anchor LRD postprocess

等上一步生成 `parsed_candidates.test.jsonl` 后启动。该任务加载 RoBERTa/LRD，需一个空闲 GPU，但显存压力远低于 Qwen 推理。

```bash
cd /data/TJK/DEE/SARGE
CAND=$(find runs/sarge_infer_DuEE-Fin-dev500_test_seed13_safe_anchor_source_f56a0d3_20260520T003122Z -path "*intermediate/getm/parsed_candidates.test.jsonl" | sort | tail -1)
test -n "$CAND" || { echo "missing parsed_candidates.test.jsonl"; exit 2; }
POST=sarge_postlrd_DuEE-Fin-dev500_test_seed13_safe_anchor_tau0.90_$(date -u +%Y%m%dT%H%M%SZ)
LOG=logs/${POST}.log
GPU=REPLACE_WITH_IDLE_GPU_ID
CUDA_VISIBLE_DEVICES=${GPU} \
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 HF_DATASETS_OFFLINE=1 \
PYTHONPATH=src \
/data/TJK/envs/sarge_vllm_full/bin/python -B scripts/postprocess_lrd_eval.py \
  --candidates "${CAND}" \
  --dataset DuEE-Fin-dev500 \
  --split test \
  --planner lrd \
  --lrd-ckpt runs/lrd/dueefin_train_seed13/checkpoints/lrd_planner.pt \
  --roberta models/chinese-roberta-wwm-ext_safetensors \
  --tau-override 0.90 \
  --device cuda \
  --out runs/${POST} > ${LOG} 2>&1
```

预期输出：

- `runs/${POST}/predictions/DuEE-Fin-dev500/test.canonical.pred.jsonl`
- log 中 `planner=lrd docs=... events_in=... events_out=...`

### 3. W9 三轨评测与 exact-record gate

三轨评测不需要 GPU。LRD postprocess 完成后立即执行：

```bash
cd /data/TJK/DEE/SARGE
/data/TJK/envs/sarge_vllm_full/bin/python -B scripts/eval_three_tracks.py \
  --run-root runs/${POST} \
  --dataset DuEE-Fin-dev500 \
  --split test
```

从 `eval/eval_unified_strict.json` 读 exact-record F1：

```bash
cd /data/TJK/DEE/SARGE
/data/TJK/envs/sarge_vllm_full/bin/python - runs/${POST} <<'PY'
import json, sys
run = sys.argv[1]
d = json.load(open(f"{run}/eval/eval_unified_strict.json", encoding="utf-8"))
diag = d.get("diagnostics", {})
exact = diag.get("record_exact_match_count", 0)
denom = diag.get("validated_record_count", 0)
print(json.dumps({
    "unified_f1": d.get("overall", {}).get("f1"),
    "unified_multi_f1": (d.get("subset_metrics") or {}).get("multi_event", {}).get("f1"),
    "record_exact_match_count": exact,
    "validated_record_count": denom,
    "exact_record_f1": (2 * exact / denom) if denom else 0.0,
}, ensure_ascii=False, indent=2))
PY
```

W9 通过后再更新 `docs/exp_result.md`、`docs/handoff.md` 和本文件；未通过则记录失败形态，不直接进入 W11。

---

## P1 - GPU 空闲后的诊断队列

这些不是 W9 正式替代品，默认作为解释性诊断或加速可行性验证。

### 4. DuEE-Fin test vLLM BF16 k=1 诊断

目的：和 HF W9 形成 test-path backend 对照。注意：dev 上 vLLM BF16 比 HF 4-bit NF4 低约 3.9pp，因此该项不能替代 W9 HF 正式结果。

```bash
cd /data/TJK/DEE/SARGE
RUN=sarge_vllm_DuEE-Fin-dev500_test_seed13_bf16_k1_diag_$(date -u +%Y%m%dT%H%M%SZ)
LOG=logs/${RUN}.log
GPU=REPLACE_WITH_IDLE_GPU_ID
CUDA_VISIBLE_DEVICES=${GPU} \
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 HF_DATASETS_OFFLINE=1 \
PYTHONPATH=src \
/data/TJK/envs/sarge_vllm_full/bin/python -B scripts/infer_checkpoint_vllm.py \
  --merged runs/merged_models/qwen3_4b_dueefin_ep2_s13 \
  --dataset DuEE-Fin-dev500 \
  --split test \
  --k 1 \
  --seed 13 \
  --slot-train-limit 50 \
  --source-commit f56a0d3 \
  --gpu-memory-utilization 0.55 \
  --max-model-len 8192 \
  --out runs/${RUN} > ${LOG} 2>&1
```

完成后可对该 run 执行 `scripts/eval_three_tracks.py`，必要时再跑 LRD postprocess。

### 5. SACD 诊断

目的：验证 schema-aware constrained decoding 是否改善格式/角色合法性。先跑 dev 或小范围诊断，只有明显收益时才考虑 full/test。

```bash
cd /data/TJK/DEE/SARGE
RUN=sarge_vllm_DuEE-Fin-dev500_dev_seed13_sacd_lax_diag_$(date -u +%Y%m%dT%H%M%SZ)
LOG=logs/${RUN}.log
GPU=REPLACE_WITH_IDLE_GPU_ID
CUDA_VISIBLE_DEVICES=${GPU} \
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 HF_DATASETS_OFFLINE=1 \
PYTHONPATH=src \
/data/TJK/envs/sarge_vllm_full/bin/python -B scripts/infer_checkpoint_vllm.py \
  --merged runs/merged_models/qwen3_4b_dueefin_ep2_s13 \
  --dataset DuEE-Fin-dev500 \
  --split dev \
  --limit 500 \
  --k 1 \
  --seed 13 \
  --source-commit f56a0d3 \
  --gpu-memory-utilization 0.55 \
  --max-model-len 8192 \
  --sacd \
  --sacd-backend xgrammar \
  --out runs/${RUN} > ${LOG} 2>&1
```

### 6. ChFinAnn full-dev HF 4-bit NF4 cross-check

目的：复核 ChFinAnn 上 HF 4-bit NF4 与 vLLM BF16 的 full-dev 路径差异。该项是诊断，不阻塞 W9。

```bash
cd /data/TJK/DEE/SARGE
RUN=sarge_hf_ChFinAnn-Doc2EDAG_dev_seed13_4bitNF4_k1_fulldev_diag_$(date -u +%Y%m%dT%H%M%SZ)
LOG=logs/${RUN}.log
GPU=REPLACE_WITH_IDLE_GPU_ID
CUDA_VISIBLE_DEVICES=${GPU} \
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 HF_DATASETS_OFFLINE=1 \
PYTHONPATH=src \
/data/TJK/envs/sarge_vllm_full/bin/python -B scripts/infer_checkpoint.py \
  --ckpt runs/sarge_sft_ChFinAnn_Doc2EDAG_s13_ep2_gpu1/artifacts/model/adapter \
  --dataset ChFinAnn-Doc2EDAG \
  --split dev \
  --k 1 \
  --seed 13 \
  --slot-train-limit 50 \
  --source-commit f56a0d3 \
  --out runs/${RUN} > ${LOG} 2>&1
```

---

## P2 - W11 多种子补齐

仅在 W9 通过后、且用户单独授权时启动。当前未发现 seed 17 / 19 的 SFT run 目录，意味着 W11 不是“只跑评测”，而是需要训练 + 推理 + LRD/eval 全链路。

建议顺序：

1. DuEE-Fin seed 17 SFT train + dev/test inference + safe-anchor LRD/eval
2. DuEE-Fin seed 19 SFT train + dev/test inference + safe-anchor LRD/eval
3. ChFinAnn seed 17 / 19 只在主表需要 mean±std 时再补

SFT 训练模板：

```bash
cd /data/TJK/DEE/SARGE
SEED=17
GPU=REPLACE_WITH_IDLE_GPU_ID
RUNLOG=logs/sarge_sft_DuEE-Fin-dev500_s${SEED}_ep2_gpu${GPU}_$(date -u +%Y%m%dT%H%M%SZ).log
CUDA_VISIBLE_DEVICES=${GPU} \
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 HF_DATASETS_OFFLINE=1 \
PYTHONPATH=src \
/data/TJK/envs/sarge_vllm_full/bin/python -B scripts/train_sft.py \
  --dataset DuEE-Fin-dev500 \
  --epochs 2 \
  --seed ${SEED} \
  --gpu ${GPU} > ${RUNLOG} 2>&1
```

启动前必须确认：

- `SEED` 只取 `17` 或 `19`
- GPU 空闲且不会干扰 W9/W10
- 新 run name 不覆盖 seed13 证据
- 训练结束后再决定是否 merge BF16 供 vLLM 诊断；正式 DuEE-Fin 仍优先 HF 4-bit NF4 + LoRA

---

## 历史完成项

| 任务 | 结果 | 证据 |
|---|---|---|
| DuEE-Fin no-SFT baseline | 低基线成立 | `docs/exp_result.md` §2.1 / §2.7 |
| DuEE-Fin k=1 greedy 复现 | 已完成 | `docs/exp_result.md` §2.9 |
| DuEE-Fin k=4 sampling 对比 | 已完成 | `docs/exp_result.md` §2.4 / §6 |
| DuEE-Fin T=0.3 / T=0.5 ablation | 已完成 | `docs/exp_result.md` §2.5 / §2.6 |
| ChFinAnn 500-doc no-SFT baseline | 已完成 | `docs/exp_result.md` §3.6 |
| ChFinAnn full dev vLLM BF16 | 已完成 | `docs/exp_result.md` §3.3 |
| LRD safe-anchor seed13 W8 | 通过候选 gate | `docs/exp_result.md` §7 |

---

## 优先级汇总

| 优先级 | 任务 | GPU 需求 | 状态 |
|---|---|---:|---|
| P0 | 当前 W9 HF test inference + no-LRD eval | ~3h | 已完成 |
| P0 | W9 safe-anchor LRD postprocess | 低到中 | test candidates 已就绪，等空闲 GPU |
| P0 | W9 LRD 三轨评测 + exact-record gate | 0 | 等 LRD postprocess |
| P1 | DuEE-Fin test vLLM BF16 诊断 | 中 | 等空闲 GPU |
| P1 | SACD dev 诊断 | 中 | 等空闲 GPU |
| P1 | ChFinAnn full-dev HF cross-check | 中到高 | 等空闲 GPU |
| P2 | W11 seed 17 / 19 多种子 | 高 | 需 W9 通过 + 单独授权 |
