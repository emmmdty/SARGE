# GPU 待办任务清单

> 最后更新：2026-05-19
> 按论文重要性排序。已完成项保留为证据，不再作为阻塞项。

---

## 已完成

| 任务 | 结果 | 证据 |
|---|---|---|
| DuEE-Fin no-SFT baseline | 低基线成立 | `docs/exp_result.md` §2.1 / §2.5 |
| DuEE-Fin k=1 greedy 复现 | 已完成 | `docs/exp_result.md` §2.7 |
| DuEE-Fin k=4 sampling 对比 | 已完成 | `docs/exp_result.md` §2.4 / §6 |
| ChFinAnn 500-doc no-SFT baseline | 已完成 | `docs/exp_result.md` §3.6 |
| ChFinAnn full dev vLLM BF16 | 已完成 | `docs/exp_result.md` §3.3 |

---

## P0 - 论文主表已覆盖，后续只保留诊断

### 1. ChFinAnn full-dev HF path cross-check

| 字段 | 值 |
|---|---|
| 命令 | `--ckpt ...ep2_gpu1/artifacts/model/adapter --dataset ChFinAnn-Doc2EDAG --k 1` |
| 目的 | 复核 HF 4-bit NF4 与 vLLM BF16 的路径差异 |
| 当前状态 | 非阻塞诊断项 |

### 2. DuEE-Fin k=1 vs k=4 解码差异整理

| 字段 | 值 |
|---|---|
| 命令 | `--ckpt ...ep2_gpu0/adapter --dataset DuEE-Fin-dev500 --limit 500 --k 1/--sample` |
| 目的 | 解释训练内置 k=4 与推理 k=1 的差异 |
| 当前状态 | 结论已写入 `docs/exp_result.md` |

---

## P1 - LRD 管线

### 3. LRD 训练数据生成

| 字段 | 值 |
|---|---|
| 内容 | 本系统 inference on ChFinAnn train (25,632 docs) + DuEE-Fin train，dump pre-LRD candidates |
| 预估 GPU | ~6-12h |
| 论文用途 | C3 组件训练数据 |
| 阻塞 | plan W6 |

### 4. LRD 单种子训练 + hard gate 评测

| 字段 | 值 |
|---|---|
| 预估 GPU | ~3h 训练 + ~2h 推理 |
| 论文用途 | C3 实证：F1(M.) +3pp vs rule planner，exact-record F1 ≥0.40 |
| 状态 | 训练 objective 已收敛为 pairwise BCE；reward 代理已禁用 |

---

## P2 - 多种子补齐

### 5. 多种子复现 (seed 17, 19)

| 字段 | 值 |
|---|---|
| 内容 | DuEE-Fin + ChFinAnn 两数据集 × 2 seeds × 全流程 |
| 预估 GPU | ~30h |
| 论文用途 | 主表 mean±std |
| 阻塞 | W8 hard gate 通过后才启动 |

---

## 汇总

| # | 优先级 | 任务 | GPU-h | 状态 |
|---|---|---|---|---|
| 1 | P1 | LRD 训练数据生成 | 6-12 | 待做 |
| 2 | P1 | LRD 训练 + hard gate | 5 | 待做 |
| 3 | P2 | 多种子 seed 17/19 | 30 | 待做 |

**总计最低**: ~11h
**总计全部**: ~41h
