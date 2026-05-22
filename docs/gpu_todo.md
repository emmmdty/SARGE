# GPU 待办任务清单

> 最后更新：2026-05-22 09:45 UTC+8
> 目的：记录当前服务器 GPU 任务、已完成实验资产和下一步可执行队列。本文只描述状态和命令入口，不把 running 任务写入主结果表。
> 服务器快照来源：`gpu-4090:/data/TJK/DEE/SARGE/` 只读查询。未启动、停止或 kill 任何任务。

---

## 当前服务器状态

| 项 | 值 |
|---|---|
| 本地项目根 | `/home/tjk/myProjects/masterProjects/DEE/SARGE/` |
| 服务器项目根 | `/data/TJK/DEE/SARGE/` |
| 本地 Python | `/home/tjk/miniconda3/envs/feg-dev-py310/bin/python` |
| 服务器 Python | `/data/TJK/envs/sarge_vllm_full/bin/python` |
| 服务器分支 / HEAD | `main` / `ff0761e88e456ea001429be86d892375bec36349` |
| 同步原则 | additive sync only；不用 `rsync --delete` |
| GPU 规则 | 优先空闲 GPU；kill 前必须确认 owner 是 `TJK`；禁止 kill 其他用户任务 |

只读刷新命令：

```bash
ssh gpu-4090 'cd /data/TJK/DEE/SARGE && git rev-parse HEAD && git status --short'
ssh gpu-4090 'ps -eo user,pid,etime,cmd | grep -E "SARGE|sarge_|infer_checkpoint|train_sft|postprocess_lrd_eval" | grep -v grep || true'
ssh gpu-4090 'nvidia-smi --query-gpu=index,memory.used,memory.total,utilization.gpu --format=csv,noheader,nounits'
```

GPU 快照：

| GPU | 当前占用 | 状态判断 | 调度含义 |
|---:|---|---|---|
| 0 | `~20.2GB`, util `44%`, non-TJK `Zhyw` vLLM worker | 他人任务占用 | 不 kill；不默认安排 SARGE |
| 1 | `~21.7GB`, util `84%`, TJK ChFinAnn seed42 训练 | 忙 | 不再叠加任务 |
| 2 | `~4.6GB`, util `14%`, TJK ChFinAnn seed17 HF 推理 | 低显存长任务 | 可共享显存但会拖慢吞吐；优先让现任务跑完 |
| 3 | `~20.2GB`, util `46%`, non-TJK `Zhyw` vLLM worker | 他人任务占用 | 不 kill；当前不能作为空闲消融 GPU |

注意：服务器当前 HEAD 还没有包含本地新增的 `SARGE_ABLATION_PROFILE` / `getm.prompt.ablation_profile` 消融控制代码。后续 profile 化消融必须先完成代码验收、commit 与 additive sync，再启动远程任务。

---

## 活动任务

| 任务 | GPU | 状态 | Log | 备注 |
|---|---:|---|---|---|
| ChFinAnn train seed42 HF-4bin LoRA ep2 | 1 | running | `logs/sarge_sft_ChFinAnn-Doc2EDAG_s42_ep2_gpu1_20260521T143813Z.log` | 最新日志约 `1032/3204`，约 `32%`，ETA 约 `5h32m`；adapter 尚未落盘 |
| ChFinAnn test seed17 HF-4bin + LoRA k=1 | 2 | running | `logs/sarge_infer_ChFinAnn-Doc2EDAG_test_seed17_4bitNF4_k1_20260521T231147Z.log` | 最新里程碑 `480/3204`，ETA 约 `12.6h`；完成后自动接三轨评测 |
| ChFinAnn seed42 train-to-test watcher | 1 | waiting | `logs/sarge_watch_ChFinAnn_seed42_train_to_test_gpu1_20260522T010434Z.log` | PID `3298922`；等待 seed42 adapter + summary 落盘后自动启动 HF-4bin k=1 test 和三轨评测 |
| non-TJK vLLM job | 0, 3 | running | n/a | owner `Zhyw`，双卡约 `19.9GB/GPU`；共享服务器任务，禁止 kill |

活动任务只进入状态表。只有存在完整 `eval/eval_{legacy_doc2edag,unified_strict,docfee_official}.json` 后，才允许进入结果表或 `paper/exp/data/asset_registry.json` 的 completed/main 条目。

---

## 已完成主资产

| 数据集 | Split | Seed | 资产 | Legacy-FS F1 | 处理 |
|---|---|---:|---|---:|---|
| ChFinAnn-Doc2EDAG | test | 13 | HF-4bin + LoRA, k=1 greedy | 0.8603 | 当前主结果 |
| DuEE-Fin-dev500 | test | 13 | HF-4bin + LoRA, k=1 greedy, no-LRD | 0.7796 | 当前主结果 |
| DuEE-Fin-dev500 | test | 17 | HF-4bin + LoRA, k=1 greedy, no-LRD | 0.7872 | 小型 JSON 快照已拉取；registry/表已更新 |
| DuEE-Fin-dev500 | test | 42 | HF-4bin + LoRA, k=1 greedy, no-LRD | 0.7828 | 小型 JSON 快照已拉取；registry/表已更新 |
| ChFinAnn-Doc2EDAG | train | 17 | HF-4bin LoRA ep2 adapter | n/a | 训练 JSON 快照已拉取；registry/表已更新；HF test 推理正在 GPU2 |

权威索引：`paper/exp/data/asset_registry.json`。小型证据快照：`paper/exp/data/run_snapshots/`。主表汇总：`paper/exp/seed13_summary.md` 和 `docs/exp_result.md`。

非 GPU P0 完成项：

| 完成时间 | 任务 | 本地产物 |
|---|---|---|
| 2026-05-22 09:30 UTC+8 | 拉取 DuEE-Fin seed17/42 HF test 小型 JSON 快照，并将 running 资产替换为 completed diagnostic seed-extension 资产 | `paper/exp/data/run_snapshots/dueefin_test_seed17_hf4bin_k1_no_lrd/`, `paper/exp/data/run_snapshots/dueefin_test_seed42_hf4bin_k1_no_lrd/`, `paper/exp/data/asset_registry.json` |
| 2026-05-22 09:30 UTC+8 | 生成 DuEE-Fin seed13/17/42 mean±std 草稿表 | `paper/exp/tables/12_dueefin_seed_stability.md` |
| 2026-05-22 09:30 UTC+8 | 拉取 ChFinAnn seed17 training 小型 JSON 快照，并将 seed17 train 标为 completed、seed42 train 标为 running | `paper/exp/data/run_snapshots/chfinann_train_seed17/`, `paper/exp/data/asset_registry.json`, `paper/exp/seed13_summary.md` |
| 2026-05-22 09:40 UTC+8 | 拉取 DuEE-Fin seed13/17/42 vLLM backend 小型 JSON 快照，补 registry、自动表和 backend seed-stability 表 | `paper/exp/data/run_snapshots/dueefin_test_seed13_vllm_bf16_k1/`, `paper/exp/data/run_snapshots/dueefin_test_seed17_vllm_bf16_k1/`, `paper/exp/data/run_snapshots/dueefin_test_seed42_vllm_bf16_k1/`, `paper/exp/tables/13_dueefin_backend_seed_stability.md` |

---

## 已完成消融和诊断资产

| 数据集 | Split | Seed | 类型 | 资产 | Legacy-FS F1 | 结论 |
|---|---|---:|---|---|---:|---|
| ChFinAnn-Doc2EDAG | test | 13 | backend | vLLM BF16 + LoRA, k=1 | 0.8547 | 低于 HF-4bin 主结果 |
| ChFinAnn-Doc2EDAG | test | 13 | decoding | vLLM BF16 + LoRA, k=4 T=0.7 | 0.8421 | sampling 未优于 greedy |
| ChFinAnn-Doc2EDAG | test | 13 | SFT | vLLM BF16 no-SFT | 0.2482 | SFT 是必要增益源 |
| ChFinAnn-Doc2EDAG | test | 17 | backend | vLLM BF16 + LoRA, k=1 | 0.8473 | seed17 backend 诊断已完成；低于 seed13 HF 主路径 |
| DuEE-Fin-dev500 | test | 13 | backend | vLLM BF16 + LoRA, k=1 | 0.7502 | fresh rerun；比 HF seed13 低 2.94pp |
| DuEE-Fin-dev500 | test | 17 | backend | vLLM BF16 + LoRA, k=1 | 0.7470 | backend 诊断 |
| DuEE-Fin-dev500 | test | 42 | backend | vLLM BF16 + LoRA, k=1 | 0.7583 | backend 诊断 |
| DuEE-Fin-dev500 | test | 13 | decoding | vLLM BF16 + LoRA, k=4 T=0.7 | 0.7313 | sampling 未优于 k=1 |
| DuEE-Fin-dev500 | test | 13 | SFT | HF-4bin no-SFT | 0.0330 | 无 SFT 基线极低 |
| DuEE-Fin-dev500 | test | 13 | SFT | vLLM BF16 no-SFT | 0.1129 | 无 SFT 基线极低 |
| DuEE-Fin-dev500 | test | 13 | LRD | safe-anchor tau=0.90 | 0.7800 | 增益很小；诊断/附录，不进主方法 |
| DuEE-Fin-dev500 | dev | 17 | invalid LRD | all k=4 parsed candidates | 0.3354 | 输入契约误用，禁止作为模型/LRD 性能 |

LRD 重要边界：主评测只能使用与 no-LRD/MRS 可比的 selected candidates。不要把 `parsed_candidates.*.jsonl` 里的全部 k=4 候选直接喂给 LRD 主评测；这样会造成 FP 爆炸，seed17 dev 的 `0.3354` 就是该误用的反例。

---

## 后续队列：按综合优先级排序

排序依据：先保证主结果和多种子稳定性，再补高论文价值、低 GPU 成本的模块消融；同一优先级内优先使用空闲 GPU3，避免干扰 GPU1/2 的长任务。估计时间来自当前服务器日志：DuEE-Fin HF test 约 `2.8h/run`，ChFinAnn HF test 约 `16h/run`，vLLM DuEE-Fin full test 约 `4-5min/run`，vLLM ChFinAnn full test 约 `15-20min/run`。

| 优先级 | 触发条件 | 任务 | 估计 GPU 时间 / 显存 | 论文价值 | GPU 调度 |
|---|---|---|---|---|---|
| P0 | ChFinAnn seed17 HF eval 落盘后 | 拉取 ChFinAnn seed17 HF test 快照，补 registry 和 ChFinAnn seed13/17 对照 | 0 GPU | 高：主结果稳定性 | CPU/rsync，本地完成 |
| P0 | ChFinAnn seed42 训练完成 | 启动 ChFinAnn seed42 HF-4bin k=1 test + 三轨评测 | 约 `16h`, 约 `4.6GB` | 很高：补齐 ChFinAnn mean±std | 优先 GPU3 或刚释放的 GPU1；可低显存共享，但不要压住训练 |
| P1 | ablation profile 代码 commit+sync 后，且 GPU3 空闲 | vLLM prompt-module 快速筛选：`no_surface_memory`, `no_slot_plan`, `no_surface_or_slot`, `schema_only`, `direct_json`；先 DuEE-Fin seed13，再 ChFinAnn seed13/17 | 总计约 `1.5-2.5h`，中等显存 | 高：快速确定哪些模块值得 HF 主后端确认 | 用 GPU3 独占更稳；不要和其他 vLLM/训练叠加 |
| P1 | vLLM 筛选完成，GPU3 仍空闲 | HF 主后端 DuEE-Fin seed13 核心消融：先 `no_surface_memory`、`no_slot_plan`，再 `no_surface_or_slot` | 每行约 `2.8h`, 约 `4.6GB` | 很高：主后端、主数据集、单变量证据 | GPU3 顺序跑；可在 GPU2 低负载时共享，但会拖慢 ChFinAnn seed17 |
| P2 | P1 DuEE-Fin 发现明确效应，且 ChFinAnn seed17/42 主推理完成 | HF 主后端 ChFinAnn 核心确认：只跑 P1 中影响最大的 1-2 个 profile | 每行约 `16h`, 约 `4.6GB` | 高：跨数据集确认，但成本大 | 只在空闲 GPU 上跑；不要与训练抢 GPU1 |
| P3 | P1/P2 结果需要论文 lower bound | HF 或 vLLM `schema_only` / `direct_json` 粗粒度下界 | HF 昂贵，vLLM 低成本 | 中：不是严格单变量，适合作附录/诊断 | 优先 vLLM；HF 仅在论文需要时跑 |
| P4 | 论文主消融需要稳定性区间 | 对最关键 1-2 个 component ablation 补 seed17/42 | DuEE-Fin 每行每种子约 `2.8h`；ChFinAnn 每行每种子约 `16h` | 高但很贵：mean±std 消融 | 只补最终要写进正文的行 |
| P5 | 用户单独授权 | 仅做 LRD 可比候选诊断 | 低到中 | 低到中：目前增益极小 | 只用 selected/fair candidate contract |
| P6 | 用户单独授权 | 继续扩展 backend/decoding ablation | vLLM 低，HF 中 | 低：已有足够 backend/sampling 证据 | 非当前优先事项 |

---

## 消融设计边界

核心消融要满足单变量原则：

| Profile | 模块变化 | 是否严格单变量 | 用途 |
|---|---|---|---|
| `full` | schema + role-safe instruction + surface candidates + slot plan | baseline | 现有主结果可作为 full control；若需要同代码版本 manifest，再补跑 |
| `no_surface_memory` | 只去掉 `[Surface Candidates]`，保留 slot plan | 是 | 评估 Surface Memory 贡献 |
| `no_slot_plan` | 只去掉 `[Event Slot Plan]`，保留 surface candidates | 是 | 评估 Slot Plan 贡献 |
| `no_surface_or_slot` | 同时去掉 surface candidates 和 slot plan | 否，组合去除 | 评估两个辅助模块的联合下界和交互 |
| `schema_only` | 去掉 role-safe 闭包、surface candidates、slot plan | 否，粗粒度 | 附录/诊断下界，不作为单变量主消融 |
| `direct_json` | 去掉 schema 和所有辅助 grounding | 否，粗粒度 | 最弱 direct extraction 下界 |

固定项：同一 checkpoint、同一 split、同一 `k=1` greedy、同一 seed、同一 evaluator 三轨、同一 no-LRD 主路径、同一 `slot_train_limit=50`。不要用 test 结果调参；如果要选择 profile 子集，优先在 dev/vLLM 筛选后冻结，再上 test。

---

## 消融命令模板

远程启动前仍需按项目规则再次给出 exact command + cwd + expected outputs。以下仅是 todo 模板。

HF-4bit + LoRA profile 模板：

```bash
cd /data/TJK/DEE/SARGE
export CUDA_VISIBLE_DEVICES=<gpu>
export PYTHONPATH=src
export HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 HF_DATASETS_OFFLINE=1
export TORCHDYNAMO_DISABLE=1 TORCH_COMPILE_DISABLE=1
export SARGE_ABLATION_PROFILE=<profile>
/data/TJK/envs/sarge_vllm_full/bin/python -u scripts/infer_checkpoint.py \
  --ckpt runs/sarge_sft_DuEE_Fin_dev500_s13_ep2_gpu0/artifacts/model/adapter \
  --model models/Qwen/Qwen3-4B-Instruct-2507 \
  --dataset DuEE-Fin-dev500 \
  --split test \
  --seed 13 \
  --k 1 \
  --slot-train-limit 50 \
  --source-commit <commit_with_ablation_profile_support> \
  --out runs/sarge_ablation_DuEE-Fin-dev500_test_seed13_<profile>_hf4bit_k1_<timestamp>
```

vLLM merged BF16 profile 筛选模板：

```bash
cd /data/TJK/DEE/SARGE
export CUDA_VISIBLE_DEVICES=3
export PYTHONPATH=src
export HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 HF_DATASETS_OFFLINE=1
export TORCHDYNAMO_DISABLE=1 TORCH_COMPILE_DISABLE=1
export SARGE_ABLATION_PROFILE=<profile>
/data/TJK/envs/sarge_vllm_full/bin/python -u scripts/infer_checkpoint_vllm.py \
  --merged runs/merged_models/qwen3_4b_dueefin_ep2_s13 \
  --dataset DuEE-Fin-dev500 \
  --split test \
  --seed 13 \
  --k 1 \
  --slot-train-limit 50 \
  --source-commit <commit_with_ablation_profile_support> \
  --out runs/sarge_ablation_DuEE-Fin-dev500_test_seed13_<profile>_vllm_bf16_k1_<timestamp>
```

ChFinAnn 对应替换：

```bash
# HF seed17 adapter
--ckpt runs/sarge_sft_ChFinAnn_Doc2EDAG_s17_ep2_gpu1/artifacts/model/adapter
--dataset ChFinAnn-Doc2EDAG

# vLLM seed13 / seed17 merged model
--merged runs/merged_models/qwen3_4b_chfinann_ep2_s13
--merged runs/merged_models/qwen3_4b_chfinann_ep2_s17
```

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
