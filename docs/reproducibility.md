# Reproducibility

## 环境

| 项 | 本地 | 服务器 |
|---|---|---|
| 项目根 | `/home/tjk/myProjects/masterProjects/DEE/SARGE/` | `/data/TJK/DEE/SARGE/` |
| Python | `/home/tjk/miniconda3/envs/feg-dev-py310/bin/python` (3.10) | `/home/TJK/.conda/envs/tjk-feg/bin/python` (3.10.20); vLLM: `/data/TJK/envs/sarge_vllm/bin/python` |
| GPU | 不使用 | gpu-4090，4 × 24 GB GPU |
| 数据 | `data/` | `data/` |
| 模型 | `models/` | `models/` |
| 评测器 | `evaluator/` | `evaluator/` |

## 数据集

| 数据集 | 路径 | 文档数 |
|---|---|---|
| ChFinAnn (Doc2EDAG 拆分) | `data/ChFinAnn-Doc2EDAG/` | train 25,632 / dev 3,204 / test 3,204 |
| DuEE-Fin (dev500 拆分) | `data/DuEE-Fin-dev500/` | train ~7k / dev 500 / test n/a |
| DocFEE (dev1000 拆分) | `data/DocFEE-dev1000/` | test 1000 |

## 模型

| 模型 | 路径 | 用途 |
|---|---|---|
| Qwen3-4B-Instruct-2507 | `models/Qwen/Qwen3-4B-Instruct-2507` | 候选生成 LLM backbone |
| Chinese-RoBERTa-wwm-ext (safetensors) | `models/chinese-roberta-wwm-ext_safetensors` | LRD encoder |
| Lawformer (safetensors) | `models/thunlp_Lawformer_safetensors` | 长文档 fallback |

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

## 论文证据要求

主表或正文性能数字必须来自可追溯 run。`run_manifest.json` 需记录
`git_commit`、`command_infer`、真实 `backend`、模型/adapter 或 merged
model 路径、解码配置、`limit`、`document_count`，且
`model_performance_evidence` 必须为 `true`。服务器目录不是 Git checkout
时，推理命令必须显式传入 `--source-commit <committed_local_git_hash>`。

详见 `docs/w3_5_evidence_hardening.md`。`MockGetmBackend` 产物仅用于
pipeline smoke，不得进入论文主表。

## 产物拉回

```bash
# 仅拉小文件（summary.json / metrics.json），不拉 checkpoint
rsync -av --include='*/' --include='summary.json' --include='*.json' --exclude='*' \
  gpu-4090:/data/TJK/DEE/SARGE/runs/ \
  /home/tjk/myProjects/masterProjects/DEE/SARGE/runs/
```

## 历史产物（只读查阅）

`legacy/` 仅用于追溯历史代码与产物，不作为当前 SARGE 运行依赖。
