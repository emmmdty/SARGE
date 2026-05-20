# SARGE draft_v1 fact sheet

## Scope

- 本目录只生成中文论文草稿与可编译资产：`paper/draft_v1/draft.tex`、`tables/*.tex`、`figures/*.pdf`、`source_manifest.json`、`build.log`。
- 本地项目根：`/home/tjk/myProjects/masterProjects/DEE/SARGE/`
- 服务器项目根：`/data/TJK/DEE/SARGE/`
- 本地 Python：`/home/tjk/miniconda3/envs/feg-dev-py310/bin/python`
- 服务器 Python：`/data/TJK/envs/sarge_vllm_full/bin/python`
- 本目录的资产生成使用：`/home/tjk/.codex/venvs/codex-tools/bin/python`

## Method Name And Task

- 方法名：SARGE, Schema-Aware Role-Grounded Extractor。
- 任务：中文金融文档级事件抽取，输入文档与事件 schema，输出结构化事件记录。
- 方法抽象：schema-slot contract 约束输出结构，surface memory 约束候选表面片段，Qwen3-4B + LoRA 执行受控 JSON 生成，record disambiguation 处理同文同类多记录。

## Main Result Policy

- 主表只使用 `legacy_doc2edag_native_fixed_slot`。
- `unified_strict` 仅可作为 canonical JSONL 严格诊断；不与 fixed-slot 主表混算。
- `docfee_official` 不用于本文两个主数据集的主表。
- EPAL 与 SEELE 使用公开论文表格值；不补造原文未报告的 P/R 或单事件/多事件列。
- DuEE-Fin 主结果采用已完成 W9 no-LRD labeled test 1171 文档结果。DuEE-Fin-dev500 500 文档结果只作为开发/诊断补充，不写入主表。

## SARGE Main Evidence

| 数据集 | split | docs | metric_family | P | R | F1 | 来源 |
| --- | --- | ---: | --- | ---: | ---: | ---: | --- |
| ChFinAnn-Doc2EDAG | dev/full-dev | 3204 | legacy_doc2edag_native_fixed_slot | 0.8350634371 | 0.8757682751 | 0.8549316227 | `/data/TJK/DEE/SARGE/runs/sarge_infer_ChFinAnn-Doc2EDAG_dev_20260519T040525Z/eval/eval_legacy_doc2edag.json` |
| DuEE-Fin-dev500 | test/labeled test | 1171 | legacy_doc2edag_native_fixed_slot | 0.7663503462 | 0.7933094385 | 0.7795968952 | `/data/TJK/DEE/SARGE/runs/sarge_infer_DuEE-Fin-dev500_test_seed13_safe_anchor_source_f56a0d3_20260520T003122Z/sarge_infer_DuEE-Fin-dev500_test_20260520T003122Z/eval/eval_legacy_doc2edag.json` |

### SARGE Source Hashes

- ChFinAnn eval hash: `b8e69d9f79647887a20cb53ef0b7dfa63e154fb4a8861ce67af41d27a9b8d3e6`
- ChFinAnn manifest hash: `2d11517e9511021e85543ca4a8dd43f96f851ab9622048ef74b118c2e28786f4`
- DuEE-Fin test eval hash: `76b83c471fb168954f9e08bed7ccdcf15262eb5964985557fb7f34d172ef2f91`
- DuEE-Fin test manifest hash: `c16c11614971db5561a25b05f30a1d9082d21e538a5a7fd4bab55b2980782642`

## Baseline Evidence

| 方法 | 文件 | sha256 | 使用表格 |
| --- | --- | --- | --- |
| EPAL | `/home/tjk/myProjects/masterProjects/DEE/dee-fin/baseline/EPAL/docs/paper/EPAL.md` | `bc36dcb99c3001c77d14281f3f5ff9409b22384230d869e41b5ce0df24886da6` | Table 1, Appendix Table 4, Appendix Table 5 |
| SEELE | `/home/tjk/myProjects/masterProjects/DEE/dee-fin/baseline/SEELE/docs/full.md` | `e4a397916502d62d126f5dfbb6ec22a7890587f2c074acb156c5dafa4d8e5199` | Table 2, Table 3 |

## Reportable Conclusions

- SARGE 在 ChFinAnn full-dev 上 fixed-slot F1 = 85.49，可写作约 85.5。
- SARGE 在 DuEE-Fin labeled test 上 fixed-slot F1 = 77.96，可写作约 78.0。
- 在公开 fixed-slot 表格口径下，SARGE 的 DuEE-Fin F1 高于 EPAL Table 1 的 76.4，低于 SEELE Table 3 的 80.8。
- 在公开 fixed-slot 表格口径下，SARGE 的 ChFinAnn F1 高于 EPAL Table 1 的 83.4，与 SEELE Table 2 的 85.1 处于同一量级并略高。

## Not Allowed Claims

- 不声称统计显著性。
- 不声称多种子 mean±std。
- 不声称隐藏测试集或线上 leaderboard 结果。
- 不声称 LRD test 结论。
- 不把 DuEE-Fin 500 文档开发诊断写作主表性能。
- 不把 `legacy_doc2edag_native_fixed_slot`、`unified_strict`、`docfee_official` 混成同一个指标。
- 不写 SOTA 绝对结论；只能写在上述公开表格口径下的有限比较。
