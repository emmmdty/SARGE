# GPU 待办任务清单

> 最后更新：2026-05-21 23:15 UTC+8
> 目的：记录当前服务器 GPU 任务、已完成实验资产和下一步可执行队列。本文只描述状态和命令入口，不把 running 任务写入主结果表。

---

## 当前服务器状态

| 项 | 值 |
|---|---|
| 本地项目根 | `/home/tjk/myProjects/masterProjects/DEE/SARGE/` |
| 服务器项目根 | `/data/TJK/DEE/SARGE/` |
| 本地 Python | `/home/tjk/miniconda3/envs/feg-dev-py310/bin/python` |
| 服务器 Python | `/data/TJK/envs/sarge_vllm_full/bin/python` |
| 服务器分支 / HEAD | `main` / `7ddc3da97044050512f43d4fac94fea60957d94c` |
| 同步原则 | additive sync only；不用 `rsync --delete` |
| GPU 规则 | 优先空闲 GPU；kill 前必须确认 owner 是 `TJK`；禁止 kill 其他用户任务 |

只读刷新命令：

```bash
ssh gpu-4090 'cd /data/TJK/DEE/SARGE && git rev-parse HEAD && git status --short'
ssh gpu-4090 'ps -eo user,pid,etime,cmd | grep -E "SARGE|sarge_|infer_checkpoint|train_sft|postprocess_lrd_eval" | grep -v grep || true'
ssh gpu-4090 'nvidia-smi --query-gpu=index,memory.used,memory.total,utilization.gpu --format=csv,noheader,nounits'
```

---

## 活动任务

| 任务 | GPU | 状态 | Log | 备注 |
|---|---:|---|---|---|
| DuEE-Fin test seed17 HF-4bin + LoRA k=1 | 0 | running | `logs/sarge_infer_DuEE-Fin-dev500_test_seed17_4bitNF4_k1_20260521T2141Z.log` | 23:15 刷新时约 `638/1171` docs；完成后自动接三轨评测 |
| DuEE-Fin test seed42 HF-4bin + LoRA k=1 | 0 | running | `logs/sarge_infer_DuEE-Fin-dev500_test_seed42_4bitNF4_k1_20260521T2221Z.log` | 23:15 刷新时约 `348/1171` docs；完成后需确认 eval 是否落盘 |
| ChFinAnn train seed17 HF-4bin LoRA ep2 | 1 | running | `logs/sarge_sft_ChFinAnn-Doc2EDAG_s17_ep2_gpu1_20260521T143813Z.log` | `--skip-eval`；训练完成后才可安排 test 推理 |
| ChFinAnn train seed42 HF-4bin LoRA ep2 | 1 | queued | `logs/sarge_sft_ChFinAnn-Doc2EDAG_s42_ep2_gpu1_20260521T143813Z.log` | seed17 结束后由队列启动；当前日志可能尚不存在 |

活动任务只进入状态表。只有存在完整 `eval/eval_{legacy_doc2edag,unified_strict,docfee_official}.json` 后，才允许进入结果表或 `paper/exp/data/asset_registry.json` 的 completed/main 条目。

---

## 已完成主资产

| 数据集 | Split | Seed | 资产 | Legacy-FS F1 | 处理 |
|---|---|---:|---|---:|---|
| ChFinAnn-Doc2EDAG | test | 13 | HF-4bin + LoRA, k=1 greedy | 0.8603 | 当前主结果 |
| DuEE-Fin-dev500 | test | 13 | HF-4bin + LoRA, k=1 greedy, no-LRD | 0.7796 | 当前主结果 |

权威索引：`paper/exp/data/asset_registry.json`。小型证据快照：`paper/exp/data/run_snapshots/`。主表汇总：`paper/exp/seed13_summary.md` 和 `docs/exp_result.md`。

---

## 已完成消融和诊断资产

| 数据集 | Split | Seed | 类型 | 资产 | Legacy-FS F1 | 结论 |
|---|---|---:|---|---|---:|---|
| ChFinAnn-Doc2EDAG | test | 13 | backend | vLLM BF16 + LoRA, k=1 | 0.8547 | 低于 HF-4bin 主结果 |
| ChFinAnn-Doc2EDAG | test | 13 | decoding | vLLM BF16 + LoRA, k=4 T=0.7 | 0.8421 | sampling 未优于 greedy |
| ChFinAnn-Doc2EDAG | test | 13 | SFT | vLLM BF16 no-SFT | 0.2482 | SFT 是必要增益源 |
| DuEE-Fin-dev500 | test | 13 | backend | vLLM BF16 + LoRA, k=1 | 0.7354 | 比 HF-4bin 主结果低 4.42pp |
| DuEE-Fin-dev500 | test | 13 | decoding | vLLM BF16 + LoRA, k=4 T=0.7 | 0.7313 | sampling 未优于 greedy |
| DuEE-Fin-dev500 | test | 13 | SFT | HF-4bin no-SFT | 0.0330 | 无 SFT 基线极低 |
| DuEE-Fin-dev500 | test | 13 | SFT | vLLM BF16 no-SFT | 0.1129 | 无 SFT 基线极低 |
| DuEE-Fin-dev500 | test | 13 | LRD | safe-anchor tau=0.90 | 0.7800 | 增益很小；诊断/附录，不进主方法 |
| DuEE-Fin-dev500 | dev | 17 | invalid LRD | all k=4 parsed candidates | 0.3354 | 输入契约误用，禁止作为模型/LRD 性能 |

LRD 重要边界：主评测只能使用与 no-LRD/MRS 可比的 selected candidates。不要把 `parsed_candidates.*.jsonl` 里的全部 k=4 候选直接喂给 LRD 主评测；这样会造成 FP 爆炸，seed17 dev 的 `0.3354` 就是该误用的反例。

---

## 下一步队列

| 优先级 | 触发条件 | 任务 | GPU | 输出要求 |
|---|---|---|---:|---|
| P0 | DuEE-Fin seed17/42 test inference 结束 | 拉取小型 JSON 快照并更新 `asset_registry.json` | 0 | `summary/run_manifest/eval/diagnostics`，不拉 predictions/checkpoints |
| P0 | DuEE-Fin seed17/42 eval 落盘 | 计算 seed13/17/42 mean±std 草稿表 | 0 | 只更新状态/诊断表，是否进正文等用户确认 |
| P1 | ChFinAnn seed17 训练完成 | 启动 ChFinAnn seed17 test HF-4bin k=1 推理 + 三轨评测 | 1 块空闲 GPU | 新 run name；不覆盖 seed13 |
| P1 | ChFinAnn seed42 训练完成 | 启动 ChFinAnn seed42 test HF-4bin k=1 推理 + 三轨评测 | 1 块空闲 GPU | 新 run name；不覆盖 seed13 |
| P2 | 用户单独授权 | 仅做 LRD 可比候选诊断 | 低到中 | 只用 selected/fair candidate contract |

---

## 常用后处理命令

三轨评测不需要 GPU：

```bash
cd /data/TJK/DEE/SARGE
/data/TJK/envs/sarge_vllm_full/bin/python -B scripts/eval_three_tracks.py \
  --run-root runs/<run_name>/<inner_run_name> \
  --dataset <DuEE-Fin-dev500|ChFinAnn-Doc2EDAG> \
  --split test
```

拉取小型证据快照时只同步 JSON，不拉 checkpoint、prediction JSONL、raw output 或 parsed candidates：

```bash
rsync -av \
  --include='*/' \
  --include='*.json' \
  --exclude='*' \
  gpu-4090:/data/TJK/DEE/SARGE/runs/<run_name>/ \
  paper/exp/data/run_snapshots/<asset_id>/
```

本地重建实验汇总：

```bash
PYTHONDONTWRITEBYTECODE=1 /home/tjk/miniconda3/envs/feg-dev-py310/bin/python -B paper/exp/scripts/build_seed13_summary.py
```
