# SARGE

**S**chema-**A**ware **R**ole-**G**rounded **E**xtractor — 面向中文金融文档级事件抽取（Document-Level Event Extraction, DEE）的端到端 schema-aware LLM 系统。

## 概述

SARGE 把 Qwen3-4B + LoRA SFT 候选生成、schema-aware 约束、候选选择、与学习型记录消歧（LRD）整合为单一 pipeline，目标是在 DuEE-Fin 与 ChFinAnn 上达到或超过已发表 SOTA 的 role-level micro-F1。

## Pipeline

```
Document
   → Surface Memory Builder
   → Slot Planner (schema-aware)
   → Candidate Generator (Qwen3-4B + LoRA SFT + role-safe contract)
   → Candidate Selector
   → Record Postprocessor (rule planner | LRD)
   → Canonical Export → Evaluator
```

## 项目结构

```
SARGE/
├── src/sarge/         # Python package
├── configs/           # YAML 配置
├── scripts/           # CLI 入口
├── tests/             # pytest
├── docs/              # 文档（含 reproducibility.md）
├── resources/         # symlinks 到数据 + 模型
└── legacy/            # Sage-DEE 历史代码（只读查阅）
```

## 快速开始

详见 [`docs/reproducibility.md`](docs/reproducibility.md)。

## 评测器

3 个 track，来自 `dee-fin/evaluator/`：

- `legacy_doc2edag` — Doc2EDAG/ProcNet-style micro-F1，与所有已发表论文横比
- `unified_strict` — 全局二分图严格匹配，内部诊断
- `docfee_official` — DocFEE 官方评测器，DocFEE 基线对比

## 许可

MIT
