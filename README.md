# SARGE

**S**chema-**A**ware **R**ole-**G**rounded **E**xtractor — 面向中文金融文档级事件抽取（Document-Level Event Extraction, DEE）的端到端 schema-aware LLM 系统。

## 概述

SARGE 把 Qwen3-4B + LoRA SFT 生成、schema-aware 约束、与记录消歧整合为单一 pipeline，目标是在 DuEE-Fin 与 ChFinAnn 上达到或超过已发表 SOTA 的 role-level micro-F1。计划引入学习型记录消歧（LRD）作为可选组件进一步提升 multi-event 子集性能。

## Pipeline

```
Document
   → Surface Memory Builder (CSG)
   → Slot Planner (LEEP, schema-aware)
   → GETM Generator (Qwen3-4B + LoRA SFT, greedy, role-safe contract)
   → Record Disambiguation (rule planner)
   → Canonical Export → Evaluator (3 tracks)
```

## 项目结构

```
SARGE/
├── src/sarge/         # Python package
├── configs/           # YAML 配置
├── scripts/           # CLI 入口
├── tests/             # pytest
├── docs/              # 文档（含 reproducibility.md）
├── data/              # 复制到本项目的数据快照（git 忽略）
├── models/            # 复制到本项目的模型快照（git 忽略）
├── evaluator/         # 复制到本项目的评测器快照
└── legacy/            # 历史代码（只读查阅）
```

## 快速开始

详见 [`docs/reproducibility.md`](docs/reproducibility.md)。

## 评测器

3 个 track，来自本项目内的 `evaluator/`：

- `legacy_doc2edag` — Doc2EDAG/ProcNet-style micro-F1，与所有已发表论文横比
- `unified_strict` — 全局二分图严格匹配，内部诊断
- `docfee_official` — DocFEE 官方评测器，DocFEE 基线对比

## 许可

MIT
