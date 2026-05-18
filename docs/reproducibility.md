# Reproducibility

## 环境

| 项 | 本地 | 服务器 |
|---|---|---|
| 项目根 | `/home/tjk/myProjects/masterProjects/DEE/SARGE/` | `/data/TJK/DEE/SARGE/` |
| Python | `/home/tjk/miniconda3/envs/feg-dev-py310/bin/python` (3.10) | `/home/TJK/.conda/envs/tjk-feg/bin/python` (3.10.20) |
| GPU | 不使用 | gpu-4090，4 × 24 GB GPU |
| 数据 | `../dee-fin/data/processed/` | `resources_data/` → `dee-fin/data/processed/` |
| 模型 | n/a | `resources_models/` → `dee-fin/models/` |
| 评测器 | `../dee-fin/evaluator/` | 同左 |

## 数据集

| 数据集 | 路径 | 文档数 |
|---|---|---|
| ChFinAnn (Doc2EDAG 拆分) | `resources_data/ChFinAnn-Doc2EDAG/` | train 25,632 / dev 3,204 / test 3,204 |
| DuEE-Fin (dev500 拆分) | `resources_data/DuEE-Fin-dev500/` | train ~7k / dev 500 / test n/a |
| DocFEE (dev1000 拆分) | `resources_data/DocFEE-dev1000/` | test 1000 |

## 模型

| 模型 | 路径 | 用途 |
|---|---|---|
| Qwen3-4B-Instruct-2507 | `resources_models/Qwen/Qwen3-4B-Instruct-2507` | 候选生成 LLM backbone |
| Chinese-RoBERTa-wwm-ext (safetensors) | `resources_models/chinese-roberta-wwm-ext_safetensors` | LRD encoder |
| Lawformer (safetensors) | `resources_models/thunlp_Lawformer_safetensors` | 长文档 fallback |

加载时设置：
```bash
export HF_HUB_OFFLINE=1
export TRANSFORMERS_OFFLINE=1
export HF_DATASETS_OFFLINE=1
```
以及 `local_files_only=True`、`use_safetensors=True`。

## Random Seeds

- 主 seed：13（W3-W10 单种子主路径）
- 补 seeds：17, 19（W11 多种子补齐，仅在 W8 hard gate 达标后启动）

## 评测命令

```bash
# 本地 invariant 测试
PYTHONDONTWRITEBYTECODE=1 /home/tjk/miniconda3/envs/feg-dev-py310/bin/python -B -m pytest tests/ -v

# 服务器评测（三 track，CPU only）
ssh TJK@gpu-4090 "cd /data/TJK/DEE/SARGE && /home/TJK/.conda/envs/tjk-feg/bin/python -B scripts/eval_three_tracks.py \
  --run-root runs/<run_name> \
  --dataset <DuEE-Fin-dev500|ChFinAnn-Doc2EDAG>"
```

## 产物拉回

```bash
# 仅拉小文件（summary.json / metrics.json），不拉 checkpoint
rsync -av --include='*/' --include='summary.json' --include='*.json' --exclude='*' \
  gpu-4090:/data/TJK/DEE/SARGE/runs/ \
  /home/tjk/myProjects/masterProjects/DEE/SARGE/runs/
```

## 历史产物（只读查阅）

| 路径 | 内容 |
|---|---|
| `legacy/sage_dee_v2/` | Sage-DEE v2 原始代码（2.2 MB 本地 / 5.9 MB 服务器） |
| `legacy/sage_dee_v2/docs/fulltrain_freeze/METRICS_SUMMARY.md` | Sage-DEE R6 S4 基线 (event/role F1 0.7339, exact-record F1 0.3609) |
| 服务器 `legacy/scripts_sage_dee/` | Sage-DEE 14 个生产脚本（仅服务器有） |
| 服务器 `legacy/runs_smoke/` | Sage-DEE 1 次 dev500 smoke 历史产物 |
