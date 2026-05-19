# GPU 待办任务清单

> 最后更新：2026-05-18
> 按论文重要性排序。每个任务标注预估 GPU 时长 + 论文用途。

---

## P0 — 论文必需（阻塞主表/核心主张）

### 1. ChFinAnn no-SFT baseline

| 字段 | 值 |
|---|---|
| 命令 | `--no-adapter --dataset ChFinAnn-Doc2EDAG --limit 500 --k 1` |
| 预估 GPU | ~1.5h |
| 论文用途 | 证明 "prompt 不足以独立完成 DEE"（ChFinAnn 侧），补全 §1 主张 |
| 现有数据 | DuEE-Fin baseline ✅ (F1=0.04)；ChFinAnn baseline ❌ |
| 阻塞 | 论文 §1 开篇论述 |

### 2. DuEE-Fin k=1 greedy vs k=4 sampling ablation

| 字段 | 值 |
|---|---|
| 贪婪命令 | `--ckpt ...ep2_gpu0/adapter --dataset DuEE-Fin-dev500 --limit 500 --k 1` |
| 采样命令 | `--ckpt ...ep2_gpu0/adapter --dataset DuEE-Fin-dev500 --limit 500 --sample` |
| 预估 GPU | ~1.2h (k=1) + ~2.7h (k=4) = **~4h** |
| 论文用途 | §5 Analysis：验证贪婪解码足够，还是采样+MRS 有增益 |
| 现有数据 | 已完成 smoke (10 docs, sampling k=4 F1≈0.76) |
| 阻塞 | 论文 §5 ablation 行 |

### 3. ChFinAnn full dev (3204 docs)

| 字段 | 值 |
|---|---|
| 命令 | `--ckpt ...ep2_gpu1/artifacts/model/adapter --dataset ChFinAnn-Doc2EDAG --k 1 --source-commit <committed_local_git_hash>` |
| 预估 GPU | ~6-8h（按 500 docs=91min 外推） |
| 论文用途 | 论文主表正式 ChFinAnn 数字（当前 limit=500 为子集评测） |
| 现有数据 | 500-doc 子集 F1=0.8444 ✅ |
| 阻塞 | 论文主表正式数字 |

---

## P1 — 论文增强（消融/对比/诊断）

### 4. DuEE-Fin ep2 k=1 复现（验证当前 k=4 结果一致性）

| 字段 | 值 |
|---|---|
| 命令 | `--ckpt ...ep2_gpu0/adapter --dataset DuEE-Fin-dev500 --limit 500 --k 1` |
| 预估 GPU | ~1.2h（可与 P0.2 的 k=1 分支共享产物） |
| 论文用途 | 确认当前 DuEE-Fin ep2 F1=0.77（k=4 greedy）与 k=1 一致 |
| 现有数据 | DuEE-Fin ep2 built-in F1=0.7704（k=4 贪婪，训练内置推理） |

### 5. ChFinAnn no-SFT baseline full dev (3204 docs)

| 字段 | 值 |
|---|---|
| 命令 | `--no-adapter --dataset ChFinAnn-Doc2EDAG --k 1` |
| 预估 GPU | ~6-8h |
| 论文用途 | ChFinAnn 全量 baseline（若审稿人质疑 limit=500 子集不够） |
| 阻塞 | 非必需；P0.1 的 500-doc 子集大概率足够 |

---

## P2 — LRD 管线（plan W4-W8，论文 C3）

### 6. LRD 训练数据生成

| 字段 | 值 |
|---|---|
| 内容 | 本系统 inference on ChFinAnn train (25,632 docs) + DuEE-Fin train，dump pre-LRD candidates |
| 预估 GPU | ~6-12h |
| 论文用途 | C3 组件训练数据 |
| 阻塞 | plan W6 |

### 7. LRD 单种子训练 + hard gate 评测

| 字段 | 值 |
|---|---|
| 预估 GPU | ~3h 训练 + ~2h 推理 |
| 论文用途 | C3 实证：F1(M.) +3pp vs rule planner, exact-record F1 ≥0.40 |
| 阻塞 | plan W7-W8 |

---

## P3 — 多种子补齐（plan W11，gated on W8）

### 8. 多种子复现 (seed 17, 19)

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
| 1 | P0 | ChFinAnn no-SFT baseline | 1.5 | ❌ |
| 2 | P0 | k=1 vs k=4 sampling ablation | 4 | smoke ✅ |
| 3 | P0 | ChFinAnn full dev | 6-8 | ❌ |
| 4 | P1 | DuEE ep2 k=1 复现 | 1.2 | ❌ |
| 5 | P1 | ChFinAnn no-SFT full baseline | 6-8 | ❌ |
| 6 | P2 | LRD 训练数据生成 | 6-12 | ❌ |
| 7 | P2 | LRD 训练 + hard gate | 5 | ❌ |
| 8 | P3 | 多种子 seed 17/19 | 30 | ❌ |

**总计最低**: ~12h (P0 only) → 论文主表完备
**总计全部**: ~55h
