from __future__ import annotations

import hashlib
import io
import json
import math
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch
from PIL import Image


BASE_DIR = Path(__file__).resolve().parents[1]
FIGURE_DIR = BASE_DIR / "figures"
TABLE_DIR = BASE_DIR / "tables"

LOCAL_PROJECT_ROOT = "/home/tjk/myProjects/masterProjects/DEE/SARGE"
SERVER_PROJECT_ROOT = "/data/TJK/DEE/SARGE"
LOCAL_PYTHON = "/home/tjk/miniconda3/envs/feg-dev-py310/bin/python"
SERVER_PYTHON = "/data/TJK/envs/sarge_vllm_full/bin/python"

EPAL_DOC = Path("/home/tjk/myProjects/masterProjects/DEE/dee-fin/baseline/EPAL/docs/paper/EPAL.md")
SEELE_DOC = Path("/home/tjk/myProjects/masterProjects/DEE/dee-fin/baseline/SEELE/docs/full.md")
FONT_PATH = Path("/home/tjk/.local/share/fonts/codex-decks/NotoSansCJKsc-Regular.otf")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def pct(value: float | None) -> float | None:
    return None if value is None else value * 100.0


def one_decimal(value: float | None) -> str:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return "--"
    return f"{value:.1f}"


def latex_text(value: Any) -> str:
    text = str(value)
    replacements = {
        "\\": r"\textbackslash{}",
        "&": r"\&",
        "%": r"\%",
        "$": r"\$",
        "#": r"\#",
        "_": r"\_",
        "{": r"\{",
        "}": r"\}",
        "~": r"\textasciitilde{}",
        "^": r"\textasciicircum{}",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    return text


def latex_num(value: float | None) -> str:
    if value is None:
        return r"\multicolumn{1}{c}{--}"
    return f"{value:.1f}"


def write_table_file(name: str, content: str) -> None:
    TABLE_DIR.mkdir(parents=True, exist_ok=True)
    (TABLE_DIR / name).write_text(content, encoding="utf-8")


EPAL_ROWS: list[dict[str, Any]] = [
    {"dataset": "ChFinAnn", "method": "Doc2EDAG", "source": "EPAL Table 1", "p": 82.7, "r": 75.2, "f1": 78.8, "single": 83.9, "multi": 67.3},
    {"dataset": "ChFinAnn", "method": "DE-PPN", "source": "EPAL Table 1", "p": 83.7, "r": 76.4, "f1": 79.9, "single": 85.9, "multi": 68.4},
    {"dataset": "ChFinAnn", "method": "PTPCG", "source": "EPAL Table 1", "p": 83.7, "r": 75.4, "f1": 79.4, "single": 88.2, "multi": None},
    {"dataset": "ChFinAnn", "method": "GIT", "source": "EPAL Table 1", "p": 82.3, "r": 78.4, "f1": 80.3, "single": 87.6, "multi": 72.3},
    {"dataset": "ChFinAnn", "method": "ReDEE", "source": "EPAL Table 1", "p": 83.9, "r": 79.9, "f1": 81.9, "single": 88.7, "multi": 74.1},
    {"dataset": "ChFinAnn", "method": "ProCNet", "source": "EPAL Table 1", "p": 83.6, "r": 78.1, "f1": 80.8, "single": 87.5, "multi": 73.5},
    {"dataset": "ChFinAnn", "method": "EPAL", "source": "EPAL Table 1", "p": 83.1, "r": 83.5, "f1": 83.4, "single": 89.7, "multi": 76.6},
    {"dataset": "DuEE-Fin", "method": "Doc2EDAG", "source": "EPAL Table 1", "p": 67.1, "r": 60.1, "f1": 63.4, "single": 69.1, "multi": 58.7},
    {"dataset": "DuEE-Fin", "method": "DE-PPN", "source": "EPAL Table 1", "p": 69.0, "r": 33.5, "f1": 45.1, "single": 54.2, "multi": 21.8},
    {"dataset": "DuEE-Fin", "method": "PTPCG", "source": "EPAL Table 1", "p": 71.0, "r": 61.7, "f1": 66.0, "single": None, "multi": None},
    {"dataset": "DuEE-Fin", "method": "GIT", "source": "EPAL Table 1", "p": 69.8, "r": 65.9, "f1": 67.8, "single": 73.7, "multi": 63.8},
    {"dataset": "DuEE-Fin", "method": "ReDEE", "source": "EPAL Table 1", "p": 77.0, "r": 72.0, "f1": 74.4, "single": 78.9, "multi": 70.6},
    {"dataset": "DuEE-Fin", "method": "ProCNet", "source": "EPAL Table 1", "p": 79.3, "r": 71.4, "f1": 75.1, "single": 80.1, "multi": 71.0},
    {"dataset": "DuEE-Fin", "method": "EPAL", "source": "EPAL Table 1", "p": 77.3, "r": 75.5, "f1": 76.4, "single": 81.2, "multi": 72.7},
]

SEELE_ROWS: list[dict[str, Any]] = [
    {"dataset": "ChFinAnn", "method": "SEELE", "source": "SEELE Table 2", "p": None, "r": None, "f1": 85.1, "single": None, "multi": None},
    {"dataset": "DuEE-Fin", "method": "SEELE", "source": "SEELE Table 3", "p": None, "r": None, "f1": 80.8, "single": None, "multi": None},
]

SARGE_ROWS: list[dict[str, Any]] = [
    {
        "dataset": "ChFinAnn",
        "method": "SARGE",
        "source": "本项目 ChFinAnn full-dev",
        "p": pct(0.8350634371395617),
        "r": pct(0.875768275140578),
        "f1": pct(0.8549316227041346),
        "single": pct(0.8834381405690859),
        "multi": pct(0.8307165623893283),
    },
    {
        "dataset": "DuEE-Fin",
        "method": "SARGE",
        "source": "本项目 labeled test",
        "p": pct(0.7663503462426263),
        "r": pct(0.7933094384707288),
        "f1": pct(0.7795968951797012),
        "single": pct(0.7927453561503583),
        "multi": pct(0.7751275661564021),
    },
]

RUN_CONFIG_ROWS = [
    {
        "dataset": "ChFinAnn full-dev",
        "split": "dev",
        "docs": 3204,
        "backend": "vLLM 0.8.5",
        "model": "Qwen3-4B + LoRA ep2 merged",
        "weights": "BF16 merged weights",
        "decoding": "k=1 greedy; temperature=None; top_p=1.0",
        "seed": 13,
        "f1": pct(0.8549316227041346),
    },
    {
        "dataset": "DuEE-Fin labeled test",
        "split": "test",
        "docs": 1171,
        "backend": "HF Transformers 5.4.0",
        "model": "Qwen3-4B + LoRA ep2 adapter",
        "weights": "4-bit NF4, double quant, bf16",
        "decoding": "k=1 greedy; temperature=None; top_p=1.0",
        "seed": 13,
        "f1": pct(0.7795968951797012),
    },
]

CHFINANN_EVENTS = [
    {"code": "EF", "event_type": "EquityFreeze", "epal": 74.8, "seele": 78.8, "sarge": pct(0.8725333333333334)},
    {"code": "ER", "event_type": "EquityRepurchase", "epal": 93.4, "seele": 92.0, "sarge": pct(0.9030289823490957)},
    {"code": "EU", "event_type": "EquityUnderweight", "epal": 76.3, "seele": 77.7, "sarge": pct(0.8248155233670401)},
    {"code": "EO", "event_type": "EquityOverweight", "epal": 77.3, "seele": 82.4, "sarge": pct(0.8460268804527235)},
    {"code": "EP", "event_type": "EquityPledge", "epal": 81.5, "seele": 83.1, "sarge": pct(0.8463748071705942)},
]

DUEEFIN_EVENTS = [
    {"code": "CL", "event_type": "公司上市", "epal": 59.1, "seele": 66.5, "sarge": pct(0.640677966101695)},
    {"code": "SR", "event_type": "股东减持", "epal": 74.5, "seele": 76.7, "sarge": pct(0.7673130193905818)},
    {"code": "EO", "event_type": "股东增持", "epal": 57.5, "seele": 75.5, "sarge": pct(0.7152317880794702)},
    {"code": "EA", "event_type": "企业收购", "epal": 68.3, "seele": 72.1, "sarge": pct(0.7224199288256228)},
    {"code": "FI", "event_type": "企业融资", "epal": 76.1, "seele": 79.1, "sarge": pct(0.7755102040816325)},
    {"code": "ER", "event_type": "股份回购", "epal": 91.3, "seele": 94.8, "sarge": pct(0.909807010634108)},
    {"code": "EP", "event_type": "质押", "epal": 78.2, "seele": 85.3, "sarge": pct(0.7950089126559713)},
    {"code": "CP", "event_type": "解除质押", "epal": 76.8, "seele": 84.8, "sarge": pct(0.7924999999999999)},
    {"code": "GB", "event_type": "企业破产", "epal": 69.3, "seele": 62.0, "sarge": pct(0.6735751295336787)},
    {"code": "EL", "event_type": "亏损", "epal": 86.1, "seele": 86.2, "sarge": pct(0.8387997208653175)},
    {"code": "BG", "event_type": "被约谈", "epal": 71.1, "seele": 58.0, "sarge": pct(0.7029702970297029)},
    {"code": "BI", "event_type": "中标", "epal": 76.3, "seele": 76.6, "sarge": pct(0.7693510555121189)},
    {"code": "SC", "event_type": "高管变动", "epal": 61.2, "seele": 64.8, "sarge": pct(0.6344735077129444)},
]


def ordered_main_rows() -> list[dict[str, Any]]:
    order = {"Doc2EDAG": 0, "DE-PPN": 1, "PTPCG": 2, "GIT": 3, "ReDEE": 4, "ProCNet": 5, "EPAL": 6, "SEELE": 7, "SARGE": 8}
    rows = [*EPAL_ROWS, *SEELE_ROWS, *SARGE_ROWS]
    return sorted(rows, key=lambda row: (row["dataset"], order[row["method"]]))


def write_main_table() -> None:
    lines = [
        r"\begin{table}[htbp]",
        r"\centering",
        r"\caption{公开基线与 SARGE 主结果（单位：\%）}",
        r"\label{tab:main-results}",
        r"\scriptsize",
        r"\resizebox{\textwidth}{!}{%",
        r"\begin{tabular}{lllSSSSS}",
        r"\toprule",
        r"数据集 & 方法 & 来源 & {P} & {R} & {F1} & {F1(S.)} & {F1(M.)} \\",
        r"\midrule",
    ]
    last_dataset = None
    for row in ordered_main_rows():
        if last_dataset and row["dataset"] != last_dataset:
            lines.append(r"\midrule")
        last_dataset = row["dataset"]
        lines.append(
            " & ".join(
                [
                    latex_text(row["dataset"]),
                    latex_text(row["method"]),
                    latex_text(row["source"]),
                    latex_num(row["p"]),
                    latex_num(row["r"]),
                    latex_num(row["f1"]),
                    latex_num(row["single"]),
                    latex_num(row["multi"]),
                ]
            )
            + r" \\"
        )
    lines.extend([r"\bottomrule", r"\end{tabular}%", r"}", r"\end{table}", ""])
    write_table_file("main_results.tex", "\n".join(lines))


def write_run_config_table() -> None:
    lines = [
        r"\begin{table}[htbp]",
        r"\centering",
        r"\caption{SARGE 主结果运行配置}",
        r"\label{tab:run-config}",
        r"\scriptsize",
        r"\resizebox{\textwidth}{!}{%",
        r"\begin{tabular}{lllclllcS}",
        r"\toprule",
        r"数据集 & split & 文档数 & 后端 & 模型 & 权重形态 & 解码 & seed & {F1} \\",
        r"\midrule",
    ]
    for row in RUN_CONFIG_ROWS:
        lines.append(
            " & ".join(
                [
                    latex_text(row["dataset"]),
                    latex_text(row["split"]),
                    str(row["docs"]),
                    latex_text(row["backend"]),
                    latex_text(row["model"]),
                    latex_text(row["weights"]),
                    latex_text(row["decoding"]),
                    str(row["seed"]),
                    latex_num(row["f1"]),
                ]
            )
            + r" \\"
        )
    lines.extend([r"\bottomrule", r"\end{tabular}%", r"}", r"\end{table}", ""])
    write_table_file("run_config.tex", "\n".join(lines))


def write_event_table(filename: str, caption: str, label: str, rows: list[dict[str, Any]]) -> None:
    lines = [
        r"\begin{table}[htbp]",
        r"\centering",
        rf"\caption{{{caption}}}",
        rf"\label{{{label}}}",
        r"\small",
        r"\begin{tabular}{llSSSSS}",
        r"\toprule",
        r"代码 & 事件类型 & {EPAL} & {SEELE} & {SARGE} & {SARGE-EPAL} & {SARGE-SEELE} \\",
        r"\midrule",
    ]
    for row in rows:
        lines.append(
            " & ".join(
                [
                    latex_text(row["code"]),
                    latex_text(row["event_type"]),
                    latex_num(row["epal"]),
                    latex_num(row["seele"]),
                    latex_num(row["sarge"]),
                    latex_num(row["sarge"] - row["epal"]),
                    latex_num(row["sarge"] - row["seele"]),
                ]
            )
            + r" \\"
        )
    lines.extend([r"\bottomrule", r"\end{tabular}", r"\end{table}", ""])
    write_table_file(filename, "\n".join(lines))


def write_metric_family_table() -> None:
    rows = [
        ("legacy_doc2edag_native_fixed_slot", "主表", "与 EPAL/SEELE 公开 fixed-slot 表格对齐；报告 ChFinAnn full-dev 与 DuEE-Fin labeled test。"),
        ("unified_strict", "内部诊断/附录候选", "回答跨数据集 canonical JSONL 的严格文本匹配问题；不与论文 fixed-slot 主表混算。"),
        ("docfee_official", "不用于本文主表", "仅适用于 DocFEE official-style 轨道；本文两个主数据集不报告该指标。"),
    ]
    lines = [
        r"\begin{table}[htbp]",
        r"\centering",
        r"\caption{评测指标族边界}",
        r"\label{tab:metric-families}",
        r"\small",
        r"\begin{tabular}{>{\raggedright\arraybackslash}p{0.34\textwidth}>{\raggedright\arraybackslash}p{0.18\textwidth}>{\raggedright\arraybackslash}p{0.40\textwidth}}",
        r"\toprule",
        r"指标族 & 本文位置 & 边界说明 \\",
        r"\midrule",
    ]
    for metric, place, note in rows:
        metric_text = latex_text(metric).replace(r"\_", r"\_\allowbreak{}")
        lines.append(f"{metric_text} & {latex_text(place)} & {latex_text(note)} \\\\")
    lines.extend([r"\bottomrule", r"\end{tabular}", r"\end{table}", ""])
    write_table_file("metric_families.tex", "\n".join(lines))


def write_tables() -> None:
    write_main_table()
    write_run_config_table()
    write_event_table("chfinann_event_results.tex", r"ChFinAnn 分事件类型 fixed-slot F1（单位：\%）", "tab:chfinann-events", CHFINANN_EVENTS)
    write_event_table("dueefin_event_results.tex", r"DuEE-Fin labeled test 分事件类型 fixed-slot F1（单位：\%）", "tab:dueefin-events", DUEEFIN_EVENTS)
    write_metric_family_table()


def configure_matplotlib() -> None:
    if FONT_PATH.exists():
        font_manager.fontManager.addfont(str(FONT_PATH))
        font_name = font_manager.FontProperties(fname=str(FONT_PATH)).get_name()
        plt.rcParams["font.family"] = font_name
    plt.rcParams.update(
        {
            "axes.unicode_minus": False,
            "figure.facecolor": "white",
            "axes.facecolor": "white",
            "axes.edgecolor": "#333333",
            "axes.linewidth": 0.8,
            "axes.labelsize": 9.5,
            "axes.titlesize": 10.5,
            "xtick.labelsize": 8.2,
            "ytick.labelsize": 8.2,
            "legend.fontsize": 8.4,
            "savefig.dpi": 300,
        }
    )


def save_pdf(fig: plt.Figure, name: str) -> None:
    FIGURE_DIR.mkdir(parents=True, exist_ok=True)
    buffer = io.BytesIO()
    fig.savefig(buffer, format="png", bbox_inches="tight", dpi=220)
    buffer.seek(0)
    with Image.open(buffer) as image:
        image.convert("RGB").save(FIGURE_DIR / name, "PDF", resolution=220.0)
    plt.close(fig)


def plot_method_pipeline() -> None:
    fig, ax = plt.subplots(figsize=(11.5, 4.2))
    ax.set_axis_off()
    steps = [
        (0.035, 0.56, "文档 + schema\n事件类型与角色表"),
        (0.215, 0.56, "surface memory\n候选表面片段约束"),
        (0.405, 0.56, "schema-slot contract\n角色安全 JSON 合约"),
        (0.610, 0.56, "Qwen3-4B + LoRA\n受控结构化生成"),
        (0.805, 0.56, "record disambiguation\n同类多记录消歧"),
    ]
    for x, y, text in steps:
        box = FancyBboxPatch((x, y), 0.150, 0.22, boxstyle="round,pad=0.015,rounding_size=0.012", linewidth=1.0, edgecolor="#2f3437", facecolor="#f5f6f4")
        ax.add_patch(box)
        ax.text(x + 0.075, y + 0.11, text, ha="center", va="center", fontsize=9.6)
    for left, right in zip(steps[:-1], steps[1:]):
        ax.add_patch(FancyArrowPatch((left[0] + 0.154, left[1] + 0.11), (right[0] - 0.010, right[1] + 0.11), arrowstyle="-|>", mutation_scale=10, linewidth=1.0, color="#555555"))

    eval_box = FancyBboxPatch((0.235, 0.16), 0.530, 0.18, boxstyle="round,pad=0.018,rounding_size=0.012", linewidth=1.0, edgecolor="#2f3437", facecolor="#eef2f5")
    ax.add_patch(eval_box)
    ax.text(0.50, 0.25, "三轨评测边界：legacy fixed-slot 主表 / unified_strict 诊断 / official-style 专用轨道", ha="center", va="center", fontsize=10)
    ax.add_patch(FancyArrowPatch((0.880, 0.55), (0.755, 0.34), arrowstyle="-|>", mutation_scale=10, linewidth=1.0, color="#555555"))
    ax.text(0.50, 0.91, "SARGE：schema-aware role-grounded generation pipeline", ha="center", va="center", fontsize=12)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    save_pdf(fig, "method_pipeline.pdf")


def plot_main_results() -> None:
    rows = ordered_main_rows()
    datasets = ["ChFinAnn", "DuEE-Fin"]
    fig, axes = plt.subplots(1, 2, figsize=(10.8, 5.7), sharex=False)
    colors = {"SARGE": "#9b3a34", "SEELE": "#27766f", "EPAL": "#44546a"}
    for ax, dataset in zip(axes, datasets):
        subset = sorted([row for row in rows if row["dataset"] == dataset], key=lambda row: row["f1"])
        labels = [row["method"] for row in subset]
        values = [row["f1"] for row in subset]
        bar_colors = [colors.get(row["method"], "#a9a9a9") for row in subset]
        ax.barh(labels, values, color=bar_colors, height=0.58)
        for label, value in zip(labels, values):
            ax.text(value + 0.25, label, one_decimal(value), va="center", fontsize=8.2)
        ax.set_xlim(max(0, min(values) - 4), min(100, max(values) + 4.5))
        ax.set_xlabel("F1 (%)")
        ax.set_title(dataset)
        ax.grid(axis="x", color="#e3e3e3", linewidth=0.7)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
    fig.suptitle("SARGE 与公开 fixed-slot 基线主结果", y=0.99, fontsize=12)
    fig.tight_layout(rect=(0, 0, 1, 0.955))
    save_pdf(fig, "main_results.pdf")


def plot_event_type_results() -> None:
    fig, axes = plt.subplots(1, 2, figsize=(12.0, 6.0), gridspec_kw={"width_ratios": [0.82, 1.18]})
    for ax, rows, title in [
        (axes[0], CHFINANN_EVENTS, "ChFinAnn"),
        (axes[1], DUEEFIN_EVENTS, "DuEE-Fin labeled test"),
    ]:
        y = list(range(len(rows)))
        labels = [f"{row['code']} {row['event_type']}" for row in rows]
        for idx, row in enumerate(rows):
            ax.plot([row["epal"], row["seele"], row["sarge"]], [idx - 0.17, idx, idx + 0.17], color="#d7d7d7", linewidth=0.8, zorder=1)
        ax.scatter([row["epal"] for row in rows], [idx - 0.17 for idx in y], label="EPAL", color="#666666", s=25, zorder=2)
        ax.scatter([row["seele"] for row in rows], y, label="SEELE", color="#27766f", marker="D", s=25, zorder=2)
        ax.scatter([row["sarge"] for row in rows], [idx + 0.17 for idx in y], label="SARGE", color="#9b3a34", marker="s", s=28, zorder=3)
        values = [value for row in rows for value in (row["epal"], row["seele"], row["sarge"])]
        ax.set_yticks(y, labels)
        ax.invert_yaxis()
        ax.set_xlim(max(0, min(values) - 4), min(100, max(values) + 4))
        ax.set_xlabel("F1 (%)")
        ax.set_title(title)
        ax.grid(axis="x", color="#e5e5e5", linewidth=0.7)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
    axes[0].legend(loc="lower center", bbox_to_anchor=(1.15, -0.18), ncol=3, frameon=False)
    fig.suptitle("分事件类型 F1 对比", y=0.99, fontsize=12)
    fig.tight_layout(rect=(0, 0.055, 1, 0.955))
    save_pdf(fig, "event_type_results.pdf")


def write_source_manifest() -> None:
    manifest = {
        "generated_for": "paper/draft_v1",
        "generated_at": "2026-05-20 Asia/Shanghai",
        "local_project_root": LOCAL_PROJECT_ROOT,
        "server_project_root": SERVER_PROJECT_ROOT,
        "local_python": LOCAL_PYTHON,
        "server_python": SERVER_PYTHON,
        "baseline_sources": [
            {
                "method": "EPAL",
                "path": str(EPAL_DOC),
                "sha256": sha256_file(EPAL_DOC),
                "tables_used": ["Table 1", "Appendix Table 4", "Appendix Table 5"],
            },
            {
                "method": "SEELE",
                "path": str(SEELE_DOC),
                "sha256": sha256_file(SEELE_DOC),
                "tables_used": ["Table 2", "Table 3"],
            },
        ],
        "sarge_sources": [
            {
                "dataset": "ChFinAnn-Doc2EDAG",
                "split": "dev",
                "document_count": 3204,
                "run_root": "/data/TJK/DEE/SARGE/runs/sarge_infer_ChFinAnn-Doc2EDAG_dev_20260519T040525Z",
                "eval_path": "/data/TJK/DEE/SARGE/runs/sarge_infer_ChFinAnn-Doc2EDAG_dev_20260519T040525Z/eval/eval_legacy_doc2edag.json",
                "run_manifest_sha256": "2d11517e9511021e85543ca4a8dd43f96f851ab9622048ef74b118c2e28786f4",
                "eval_sha256": "b8e69d9f79647887a20cb53ef0b7dfa63e154fb4a8861ce67af41d27a9b8d3e6",
                "metric_family": "legacy_doc2edag_native_fixed_slot",
                "overall": {"p": 0.8350634371395617, "r": 0.875768275140578, "f1": 0.8549316227041346},
            },
            {
                "dataset": "DuEE-Fin-dev500",
                "split": "test",
                "document_count": 1171,
                "run_root": "/data/TJK/DEE/SARGE/runs/sarge_infer_DuEE-Fin-dev500_test_seed13_safe_anchor_source_f56a0d3_20260520T003122Z/sarge_infer_DuEE-Fin-dev500_test_20260520T003122Z",
                "eval_path": "/data/TJK/DEE/SARGE/runs/sarge_infer_DuEE-Fin-dev500_test_seed13_safe_anchor_source_f56a0d3_20260520T003122Z/sarge_infer_DuEE-Fin-dev500_test_20260520T003122Z/eval/eval_legacy_doc2edag.json",
                "run_manifest_sha256": "c16c11614971db5561a25b05f30a1d9082d21e538a5a7fd4bab55b2980782642",
                "eval_sha256": "76b83c471fb168954f9e08bed7ccdcf15262eb5964985557fb7f34d172ef2f91",
                "metric_family": "legacy_doc2edag_native_fixed_slot",
                "overall": {"p": 0.7663503462426263, "r": 0.7933094384707288, "f1": 0.7795968951797012},
            },
        ],
        "generated_figures": sorted(path.name for path in FIGURE_DIR.glob("*.pdf")),
        "generated_tables": sorted(path.name for path in TABLE_DIR.glob("*.tex")),
    }
    (BASE_DIR / "source_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    FIGURE_DIR.mkdir(parents=True, exist_ok=True)
    TABLE_DIR.mkdir(parents=True, exist_ok=True)
    configure_matplotlib()
    write_tables()
    plot_method_pipeline()
    plot_main_results()
    plot_event_type_results()
    write_source_manifest()


if __name__ == "__main__":
    main()
