@AGENTS.md

# 本地路径速查

- 项目根：`/home/tjk/myProjects/masterProjects/DEE/SARGE/`
- 数据（共享，不修改）：`/home/tjk/myProjects/masterProjects/DEE/dee-fin/data/processed/`
- 评测器（共享，不修改）：`/home/tjk/myProjects/masterProjects/DEE/dee-fin/evaluator/`
- 本地 Python：`/home/tjk/miniconda3/envs/feg-dev-py310/bin/python`
- 历史产物（只读）：`/home/tjk/myProjects/masterProjects/DEE/SARGE/legacy/sage_dee_v2/`

# 服务器路径速查

- 项目根：`/data/TJK/DEE/SARGE/`
- 数据 symlink：`/data/TJK/DEE/SARGE/resources_data/` → `/data/TJK/DEE/dee-fin/data/processed/`
- 模型 symlink：`/data/TJK/DEE/SARGE/resources_models/` → `/data/TJK/DEE/dee-fin/models/`
- Qwen 模型：`/data/TJK/DEE/SARGE/resources_models/Qwen/Qwen3-4B-Instruct-2507`
- 服务器 Python：`/home/TJK/.conda/envs/tjk-feg/bin/python`
- 历史产物（只读）：`/data/TJK/DEE/SARGE/legacy/{sage_dee_v2,scripts_sage_dee,runs_smoke}/`

# Plan 与进度

- Plan 文件：`/home/tjk/.claude/plans/sage-dee-baseline-sage-dee-data-tjk-dee-parallel-dewdrop.md`
- 阶段：W1-W12（CCKS 2026 主投，2026-08 截稿前）
- 论文标题（主）："**SARGE: An End-to-End Schema-Aware LLM Pipeline for Chinese Financial Document-Level Event Extraction**"

# 多人共享与 GPU 规则

- **Kill 进程**：服务器多人共享，kill 进程前必须检查进程属主；仅允许 kill `TJK` 用户的进程，其他用户进程禁止 kill
- **GPU 资源**：gpu-4090 共 4 块 GPU（均为 4090），小显存可在单块 GPU 上加载；**优先选择空闲 GPU**，兼顾时间效益与资源公平
