# 系统架构图 GPT 提示词（用于 GPT 网页版生成 method_pipeline.pdf 替换图）

> 用法：把下面「提示词正文」整段粘进 GPT（或任意能生成矢量/高清示意图的工具）。生成后导出为 PDF，
> 命名为 `method_pipeline.pdf` 覆盖本目录同名占位图，再 `latexmk -xelatex draft.tex` 重新编译即可。
> 提示词已按真实代码实现编写（surface_memory/builder.py、generation/prompt.py、generation/parser.py、
> postprocess/rule_planner.py、evaluation/*），请勿改动事实性内容。

---

## 提示词正文（中英双语标注、学术风格、横向布局）

请生成一张**学术论文用的系统架构示意图**（横向、A4 双栏宽度、矢量风格、配色淡雅、线条清晰、留白充足、**所有文字必须完整不溢出方框**）。主题是中文金融文档级事件抽取系统 **SARGE: Schema-Aware Role-Grounded Extractor**。整体是一条从左到右的数据流管线，再向下汇入评测层。请用「圆角方框 + 箭头」表达，框内中文为主、英文术语保留原文。

### 标题
顶部居中标题：**SARGE: Schema-Aware Role-Grounded Generation Pipeline**

### 主管线（从左到右 5 个阶段，等高圆角框 + 实线箭头连接）

1. **输入 (Input)**
   - 中文：文档 $x$ + 数据集 Schema
   - 注脚小字：事件类型集合 + 每类型角色列表（event\_type → roles）

2. **Surface Memory（候选表面片段）**
   - 中文：规则抽取候选 span
   - 注脚小字：10 条正则规则（公司名 / 金额 / 比例 / 中阿日期 / 股数 / 人名 / 引用实体 / 股票代码），按优先级选 ≤ 40 个候选

3. **Prompt + Role-safe JSON 合约**
   - 中文：Schema-slot 受控提示
   - 注脚小字：拼装 [Dataset][Schema][Document][Surface Candidates][Slot Plan][Instruction]；角色名从 schema 复制，不翻译/不别名

4. **受控生成 (Controlled Generation)**
   - 中文：Qwen3-4B + LoRA
   - 注脚小字：response\_prefix `{"events":`；k=1 greedy 确定性解码；可选 schema-aware constrained decoding (xgrammar)

5. **解析 + 规则记录消歧 (Parse + Rule-based Disambiguation)**
   - 中文：JSON 解析 → anchor 兼容消歧
   - 注脚小字：校验 event\_type/role 合法性（记 parse\_failure / invalid\_*）；按事件类型 anchor 角色做 conservative merge / split / dedup（主结果为 no-LRD 规则路径）

主管线 5 个框之间用从左到右的实线箭头连接。

### 评测层（主管线末端向下用一条箭头汇入一个更宽的底部长框）

底部长框（**务必足够宽以容纳整行文字，不要让任何字被框边裁切**）：
- 第一行（稍大）：**Canonical JSONL → 三轨评测 (Three-track Evaluation)**
- 第二行（小字）：legacy fixed-slot（主表，与 EPAL/SEELE 公开表格对齐） · unified_strict（诊断 + exact-record） · official-style（专用轨道，本文不用）

### 右侧可选：一个浅色「具体示例」气泡（突出 role-grounding，使图更直观）

在主管线第 3~5 阶段上方放一个浅色虚线小气泡，展示一个迷你示例（字体小、等宽字体）：
- 文档片段："……公司A 于 2023-06-01 质押股份 1000 万股……"
- 候选片段（Surface Memory）：`公司A` / `2023-06-01` / `1000万股`
- 生成的 JSON 记录：
  ```
  {"event_type": "质押",
   "arguments": {"质押方": [{"text": "公司A"}],
                 "事件时间": [{"text": "2023-06-01"}],
                 "质押股票/股份数量": [{"text": "1000万股"}]}}
  ```
用一条细虚线把"候选片段"指向 JSON 里对应的 text 值，体现"角色取值绑定到文档可追溯证据 (role grounding)"。

### 风格要求
- 配色：低饱和度（浅灰 / 浅蓝灰 / 一个暗红强调色用于"受控生成"框），白底，专业、克制，类似 ACL/EMNLP 论文 figure。
- 不要 3D、不要阴影夸张、不要卡通图标；线条简洁。
- 中文用思源黑体/Noto Sans CJK 风格；英文用无衬线。
- **再次强调：所有方框内文字必须完整显示，框宽随文字自适应，禁止任何文字被边框裁切或溢出。**
- 输出为高分辨率、可直接放入 LaTeX 的图（PDF 或 ≥300dpi PNG）。

---

## 备注
- 本目录已提供一张 Python 生成的**修好溢出问题的占位图** `method_pipeline.pdf`，在你用 GPT 产出更精美版本之前可保证论文正常编译。
- 若 GPT 版本与占位图布局接近即可；关键是 role-grounding 示例 + 三轨评测边界要表达准确。
