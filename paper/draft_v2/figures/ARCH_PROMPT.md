# 图 1 设计说明：method_pipeline.pdf

`method_pipeline.pdf` 由 `paper/draft_v2/scripts/build_assets.py` 的
`plot_method_pipeline()` 生成；不要手工覆盖该 PDF。需要调整图 1 时，先改
脚本，再运行：

```bash
/home/tjk/.codex/venvs/codex-tools/bin/python paper/draft_v2/scripts/build_assets.py
```

## 当前版式

图 1 采用学术论文用的矢量风格，白底、低饱和配色、无夸张阴影。版式由三
个主模块和一个下方评测层组成：

1. **Evidence grounding**
   - `Document x + event schema S`
   - `Surface memory: <=40 spans`
   - `Entities, amounts, dates, shares`

2. **Role-safe generation**
   - `Prompt copies event and role names`
   - `Qwen3-4B + LoRA, k=1 greedy`
   - `SACD / xgrammar remains optional`

3. **Parse and canonicalize**
   - `Schema-valid JSON parser`
   - `Rule planner: split / merge / dedup`
   - `Export canonical JSONL`

下方评测层从 canonical JSONL 引出，分为三个独立指标族：

- `Legacy-FS`: main fixed-slot table
- `Unified-Strict`: canonical diagnostics
- `DocFEE-Official`: separate official-style track

## 设计约束

- 图内标题使用统一全称：`SARGE: Schema-Aware Role-Grounded Extractor`。
- 所有箭头只横向或垂直走线，不穿过文字、不跨框斜连。
- 不再使用旧版“五阶段长横排 + 底部长框”的版式。
- 评测轨道必须明确分开，避免暗示三类指标可以混算。
