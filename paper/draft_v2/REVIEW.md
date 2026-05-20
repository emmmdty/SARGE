# SARGE draft_v1 审稿意见（NLP / EMNLP / CCKS 视角）

> 审稿对象：`paper/draft_v1/`（draft.tex + tables + figures + FACTS.md + build_assets.py）
> 审稿日期：2026-05-20
> 审稿方向：方法论 / 创新点 / 实验 / 配图
> 数据核验方式：所有数字均与服务器真实 eval JSON（`runs/.../eval/*.json`）逐条比对；EPAL/SEELE 与其论文源文档逐值比对。

---

## 0. 总体评价（Meta-review）

**一句话**：数据诚信优秀、但作为一篇会议论文，方法论深度、相关工作、创新点定位与配图都不达投稿线；结果可比性口径需要显著加固。

**核验结论（重要、正面）**：
- ✅ 主表与逐事件 SARGE 数字**全部与服务器 eval JSON 完全一致**：ChFinAnn full-dev legacy F1 `0.8549316227`、DuEE-Fin labeled test legacy F1 `0.7795968952`，逐事件 `per_event` 全部对上（含 `0.8725333…`、`0.9030289…` 等长浮点）。
- ✅ EPAL/SEELE 总体与逐事件基线**转写全部正确**（含 EPAL 自有事件代码 WB/FL/BA/BB/CF/CL/SD/SI/SR/RT/PR/PL/EC → 标准代码的映射均正确）。
- ✅ eval 文件 sha256 与 FACTS.md 记录一致（`b8e69d…`、`76b83c…`）。
- **结论：无数据造假、无幻觉数字。** 这是本草稿最强的部分，应保留并强化（可追溯 manifest + 快照）。

**核心问题**：① 方法只有名词、没有机制；② 完全没有相关工作；③ 创新点偏宣传化；④ 跨 split 对比未充分声明；⑤ 大量已有真实消融未写入；⑥ 架构图有渲染 bug 且信息量低。

**建议**：Major Revision。本轮 `draft_v2` 已按下列意见逐条修订。

---

## 1. 方法论 (Methodology)

| 编号 | 严重度 | 问题 | 在 draft_v2 的处理 |
|---|---|---|---|
| **M1** | 严重 | 方法章节只堆名词（surface memory / schema-slot contract / record disambiguation），从不定义。读者无法知道 surface memory 是什么、JSON 合约长什么样、消歧如何进行，无法复现。 | §4 用**真实代码**重写：4.2 Surface Memory（10 条正则规则、≤40 候选，`surface_memory/builder.py`）；4.3 Prompt 与 role-safe JSON 合约（六段式 prompt、`{role:[{text}]}` 合约，`generation/prompt.py`、`data/canonical.py`）；4.4 受控生成（response\_prefix、greedy、可选 SACD，`scripts/infer_checkpoint*.py`）；4.5 解析与诊断（`generation/parser.py`）；4.6 anchor 记录消歧（`postprocess/rule_planner.py`）。 |
| **M2** | 严重 | **完全没有相关工作章节**。任何 NLP 会场都会因此直接降档。 | 新增 §3 相关工作：文档级 EE 谱系 + LLM-for-IE/受限解码 + 中文金融 EE，并定位 SARGE。 |
| **M3** | 中 | 主结果实际用的是 **rule planner（no-LRD）**，但 draft 笼统说 "record disambiguation"，易被误读为用了 learned LRD。 | §4.6 明确：**主表=规则 anchor 消歧（no-LRD）**；learned LRD（safe-anchor 修复）仅作诊断/future，并在限制中重申不报告 LRD test 结论。 |
| **M4** | 中 | 任务定义缺输出空间、anchor 角色、固定槽位匹配的精确表述。 | §4.1 给出形式化定义；§4.6/§4.7 定义 anchor 角色与固定槽位 TP/FP/FN 匹配口径。 |

---

## 2. 创新点 (Novelty / Contributions)

| 编号 | 严重度 | 问题 | 在 draft_v2 的处理 |
|---|---|---|---|
| **N1** | 中 | 5 个"创新点"多为方法复述 + 宣传化措辞。schema 约束 / 受限 JSON 生成本身**不新**（function calling、grammar-constrained decoding 已普遍），未对照文献定位。 | 重写为一段贡献列表，并在 §3 相关工作中明确"与已有结构化生成的区别在于：面向中文金融**文档级、多记录**场景的端到端管线 + anchor 记录消歧 + 严格指标族分离"。 |
| **N2** | 中 | 把"可追溯实验证据"列为**创新点**不妥——那是研究严谨性，不是研究贡献。 | 降级：作为方法/实验的 rigor 声明（manifest + 快照 + 完整性断言），不再列为 contribution。 |
| **N3** | 提示 | 真正可主张且**有真实证据支撑**的卖点没讲：100% schema-valid 输出、0 解析失败、exact-record 显著高于 ProcNet 同口径参考。 | 写入 §5.4 鲁棒性分析与贡献列表。 |

---

## 3. 实验 (Experiments)

| 编号 | 严重度 | 问题 | 在 draft_v2 的处理 |
|---|---|---|---|
| **E1** | 严重（可比性） | ChFinAnn SARGE 在 **dev split(3204)**，而 EPAL/SEELE 公开数字在 **test split**；DuEE-Fin 用的是内部 labeled test(1171)。同表对比但 split 口径不一致，"高于/低于"措辞暗示了 head-to-head。 | 主表 caption + 每行 split 标注；正文软化为"公开表格参考点，非同测试集 head-to-head"；§5.5 限制置顶；图标题/坐标轴注明 split。 |
| **E2** | 中 | 两数据集主结果用了**不同推理后端**（ChFinAnn=vLLM BF16；DuEE=HF 4-bit NF4），dev 上后端差约 3.9pp，draft 仅在 run\_config 表暗示、未解释。 | §5.4 增加**后端对比表/图**（真实），坦白：full-dev 上只有 vLLM 整集 run、DuEE labeled test 上只有 HF 整集 run，并说明 dev 上 HF 略优于 vLLM。 |
| **E3** | 机会 | 大量**已有真实消融未用**，白白浪费证据。 | §5.4 补四类（均真实、零新 GPU）：No-SFT 增益、后端对比、解码策略、输出鲁棒性 + exact-record vs ProcNet。 |
| **E4** | 小 | 正文原 §122 "EquityRepurchase 低于 SEELE"**不准确**——SARGE 90.3 既低于 SEELE 92.0、**也低于 EPAL 93.4**，原文漏掉了后者。 | §5.3 改为"低于 EPAL 与 SEELE 但仍达 90.3"。 |
| **E5** | 小 | 数据集名 "DuEE-Fin-dev500" 配 1171 篇 test split 极易误解。 | §5.1 脚注澄清命名来源（内部数据集构造标签，非文档数）。 |
| **E6** | 小 | 单种子（seed 13）、无 mean±std——draft 已声明。 | 保留并在 §5.5 限制置顶；不补造多种子结论（守 FACTS 红线）。 |

---

## 4. 配图 (Figures)

| 编号 | 严重度 | 问题 | 在 draft_v2 的处理 |
|---|---|---|---|
| **F1** | 严重 | `method_pipeline.pdf` 有**文字溢出 bug**："三轨评测边界"框左侧 "三轨" 被框边裁切（`build_assets.py:362-364` 框宽/居中不匹配）；且过于扁平、把"评测口径"当作架构步骤、未体现真实机制与数据流。 | ① 用 Python 出一张**修好溢出**的占位图（框宽自适应）；② 提供 `figures/ARCH_PROMPT.md` GPT 提示词，含 role-grounding 迷你示例 + 准确机制，供网页版生成精修图替换。 |
| **F2** | 中 | `main_results.pdf` 与主表完全冗余，且 x 轴截断（起点 76/45）放大差异。 | 重绘：x 轴从 0 起（不再截断夸大），标题/caption 注明 split + "对比仅作参考"。 |
| **F3** | 小 | `event_type_results.pdf` 基本可用。 | 重绘保留，标题加 split 标注。 |
| **F4** | 机会 | 缺消融可视化。 | 新增 `ablation_sft_gain.pdf`（SFT 增益）与 `ablation_backend_decoding.pdf`（后端×解码），均来自真实数据。 |

---

## 5. 守住的红线（与 FACTS.md「Not Allowed Claims」一致）

draft_v2 全程**不**声称：统计显著性、多种子 mean±std、隐藏测试集/线上 leaderboard 结果、LRD test 结论、不混算三指标族、不写绝对 SOTA。所有新增数字均来自 `data_snapshot/` 或 `ablation_evidence.json`，并由 `build_assets.py` 的 `assert_integrity()` 锁定，防止编辑漂移。

---

## 6. 给作者的优先级行动清单

1. （已做）补相关工作 + 代码级方法重写。
2. （已做）主表/图加 split caveat，软化对比措辞。
3. （已做）补四类真实消融，把"白有的证据"用起来。
4. （需 GPU，后续）若要支撑更强主张：ChFinAnn full-dev 的 HF 4-bit 同后端 cross-check、DuEE test 的 vLLM 对照、seed 17/19 多种子——均为 gpu_todo.md 中的 P1/P2，未完成前不写入主张。
5. （需作者）用 `figures/ARCH_PROMPT.md` 在 GPT 网页版生成正式架构图替换占位图。
