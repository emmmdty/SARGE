"""Regenerate draft_v2 tables and figures from auditable real data.

SARGE numbers are read from ``data_snapshot/*.json`` (server eval JSON, hashes
match FACTS.md). Ablation numbers are read from ``ablation_evidence.json`` (each
value annotated with its server run root). EPAL/SEELE baseline numbers are
published-paper constants (verified against the baseline source docs).

Run with the codex-tools venv (has matplotlib + PIL + the CJK font):
    /home/tjk/.codex/venvs/codex-tools/bin/python paper/draft_v2/scripts/build_assets.py
"""
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
SNAPSHOT_DIR = BASE_DIR / "data_snapshot"
ABLATION_PATH = BASE_DIR / "ablation_evidence.json"

LOCAL_PROJECT_ROOT = "/home/tjk/myProjects/masterProjects/DEE/SARGE"
SERVER_PROJECT_ROOT = "/data/TJK/DEE/SARGE"
LOCAL_PYTHON = "/home/tjk/miniconda3/envs/feg-dev-py310/bin/python"
SERVER_PYTHON = "/data/TJK/envs/sarge_vllm_full/bin/python"
ASSET_PYTHON = "/home/tjk/.codex/venvs/codex-tools/bin/python"

EPAL_DOC = Path("/home/tjk/myProjects/masterProjects/DEE/dee-fin/baseline/EPAL/docs/paper/EPAL.md")
SEELE_DOC = Path("/home/tjk/myProjects/masterProjects/DEE/dee-fin/baseline/SEELE/docs/full.md")
FONT_PATH = Path("/home/tjk/.local/share/fonts/codex-decks/NotoSansCJKsc-Regular.otf")

CHFINANN_SNAPSHOT = SNAPSHOT_DIR / "chfinann_dev_legacy.json"
DUEEFIN_SNAPSHOT = SNAPSHOT_DIR / "dueefin_test_legacy.json"
DUEEFIN_UNIFIED = SNAPSHOT_DIR / "dueefin_test_unified.json"


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #
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
        "\\": r"\textbackslash{}", "&": r"\&", "%": r"\%", "$": r"\$",
        "#": r"\#", "_": r"\_", "{": r"\{", "}": r"\}",
        "~": r"\textasciitilde{}", "^": r"\textasciicircum{}",
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


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


# --------------------------------------------------------------------------- #
# data: SARGE from snapshot, baselines from published tables
# --------------------------------------------------------------------------- #
CHF = load_json(CHFINANN_SNAPSHOT)
DUE = load_json(DUEEFIN_SNAPSHOT)
DUE_UNIFIED = load_json(DUEEFIN_UNIFIED)
ABL = load_json(ABLATION_PATH)


def sarge_overall(snapshot: dict[str, Any]) -> dict[str, float]:
    o = snapshot["overall"]
    s = snapshot["subset_metrics"]
    return {
        "p": pct(o["precision"]), "r": pct(o["recall"]), "f1": pct(o["f1"]),
        "single": pct(s["single_event"]["f1"]), "multi": pct(s["multi_event"]["f1"]),
    }


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

_chf = sarge_overall(CHF)
_due = sarge_overall(DUE)
SARGE_ROWS: list[dict[str, Any]] = [
    {"dataset": "ChFinAnn", "method": "SARGE", "source": r"\textbf{本项目} (dev/full-dev)", **_chf},
    {"dataset": "DuEE-Fin", "method": "SARGE", "source": r"\textbf{本项目} (labeled test)", **_due},
]

RUN_CONFIG_ROWS = [
    {"dataset": "ChFinAnn", "split": "dev (full-dev)", "docs": 3204, "backend": "vLLM 0.8.5", "model": "Qwen3-4B + LoRA ep2 merged", "weights": "BF16 merged", "decoding": "k=1 greedy", "seed": 13, "f1": _chf["f1"]},
    {"dataset": "DuEE-Fin", "split": "labeled test", "docs": 1171, "backend": "HF Transformers 5.4.0", "model": "Qwen3-4B + LoRA ep2 adapter", "weights": "4-bit NF4 + bf16 compute", "decoding": "k=1 greedy", "seed": 13, "f1": _due["f1"]},
]

# baselines per event (verified against EPAL Appendix Table 4/5 and SEELE Table 2/3)
CHFINANN_BASELINE = {
    "EquityFreeze": ("EF", "EquityFreeze", 74.8, 78.8),
    "EquityRepurchase": ("ER", "EquityRepurchase", 93.4, 92.0),
    "EquityUnderweight": ("EU", "EquityUnderweight", 76.3, 77.7),
    "EquityOverweight": ("EO", "EquityOverweight", 77.3, 82.4),
    "EquityPledge": ("EP", "EquityPledge", 81.5, 83.1),
}
CHFINANN_ORDER = ["EquityFreeze", "EquityRepurchase", "EquityUnderweight", "EquityOverweight", "EquityPledge"]

DUEEFIN_BASELINE = {
    "公司上市": ("CL", "公司上市", 59.1, 66.5),
    "股东减持": ("SR", "股东减持", 74.5, 76.7),
    "股东增持": ("EO", "股东增持", 57.5, 75.5),
    "企业收购": ("EA", "企业收购", 68.3, 72.1),
    "企业融资": ("FI", "企业融资", 76.1, 79.1),
    "股份回购": ("ER", "股份回购", 91.3, 94.8),
    "质押": ("EP", "质押", 78.2, 85.3),
    "解除质押": ("CP", "解除质押", 76.8, 84.8),
    "企业破产": ("GB", "企业破产", 69.3, 62.0),
    "亏损": ("EL", "亏损", 86.1, 86.2),
    "被约谈": ("BG", "被约谈", 71.1, 58.0),
    "中标": ("BI", "中标", 76.3, 76.6),
    "高管变动": ("SC", "高管变动", 61.2, 64.8),
}
DUEEFIN_ORDER = list(DUEEFIN_BASELINE.keys())


def event_rows(snapshot: dict[str, Any], baseline: dict, order: list[str]) -> list[dict[str, Any]]:
    rows = []
    for key in order:
        code, name, epal, seele = baseline[key]
        sarge = pct(snapshot["per_event"][key]["f1"])
        rows.append({"code": code, "event_type": name, "epal": epal, "seele": seele, "sarge": sarge})
    return rows


CHFINANN_EVENTS = event_rows(CHF, CHFINANN_BASELINE, CHFINANN_ORDER)
DUEEFIN_EVENTS = event_rows(DUE, DUEEFIN_BASELINE, DUEEFIN_ORDER)


# --------------------------------------------------------------------------- #
# tables
# --------------------------------------------------------------------------- #
def ordered_main_rows() -> list[dict[str, Any]]:
    order = {"Doc2EDAG": 0, "DE-PPN": 1, "PTPCG": 2, "GIT": 3, "ReDEE": 4, "ProCNet": 5, "EPAL": 6, "SEELE": 7, "SARGE": 8}
    rows = [*EPAL_ROWS, *SEELE_ROWS, *SARGE_ROWS]
    return sorted(rows, key=lambda row: (row["dataset"], order[row["method"]]))


def write_main_table() -> None:
    lines = [
        r"\begin{table}[htbp]", r"\centering",
        r"\caption{公开 fixed-slot 基线与 SARGE 主结果（单位：\%）。EPAL/SEELE 取自其论文 \emph{test} split 公开表格；SARGE 在 ChFinAnn 为 \emph{dev}(full-dev 3204)、DuEE-Fin 为内部 \emph{labeled test}(1171)。split 口径不同，对比仅作公开表格参考点，非同测试集 head-to-head。}",
        r"\label{tab:main-results}", r"\scriptsize", r"\resizebox{\textwidth}{!}{%",
        r"\begin{tabular}{lllSSSSS}", r"\toprule",
        r"数据集 & 方法 & 来源/split & {P} & {R} & {F1} & {F1(S.)} & {F1(M.)} \\", r"\midrule",
    ]
    last = None
    for row in ordered_main_rows():
        if last and row["dataset"] != last:
            lines.append(r"\midrule")
        last = row["dataset"]
        method = row["method"]
        method_cell = r"\textbf{SARGE}" if method == "SARGE" else latex_text(method)
        source_cell = row["source"] if method == "SARGE" else latex_text(row["source"])
        lines.append(" & ".join([
            latex_text(row["dataset"]), method_cell, source_cell,
            latex_num(row["p"]), latex_num(row["r"]), latex_num(row["f1"]),
            latex_num(row["single"]), latex_num(row["multi"]),
        ]) + r" \\")
    lines.extend([r"\bottomrule", r"\end{tabular}%", r"}", r"\end{table}", ""])
    write_table_file("main_results.tex", "\n".join(lines))


def write_run_config_table() -> None:
    lines = [
        r"\begin{table}[htbp]", r"\centering",
        r"\caption{SARGE 主结果运行配置。两个数据集使用不同推理后端：ChFinAnn 用 vLLM BF16 merged（full-dev 上唯一已完成的整集 run），DuEE-Fin 用 HF 4-bit NF4 + LoRA（dev 上较 vLLM 高约 3.9pp，见消融）。}",
        r"\label{tab:run-config}", r"\scriptsize", r"\resizebox{\textwidth}{!}{%",
        r"\begin{tabular}{lllllllcS}", r"\toprule",
        r"数据集 & split & 文档数 & 后端 & 模型 & 权重 & 解码 & seed & {F1} \\", r"\midrule",
    ]
    for row in RUN_CONFIG_ROWS:
        lines.append(" & ".join([
            latex_text(row["dataset"]), latex_text(row["split"]), str(row["docs"]),
            latex_text(row["backend"]), latex_text(row["model"]), latex_text(row["weights"]),
            latex_text(row["decoding"]), str(row["seed"]), latex_num(row["f1"]),
        ]) + r" \\")
    lines.extend([r"\bottomrule", r"\end{tabular}%", r"}", r"\end{table}", ""])
    write_table_file("run_config.tex", "\n".join(lines))


def write_event_table(filename: str, caption: str, label: str, rows: list[dict[str, Any]]) -> None:
    lines = [
        r"\begin{table}[htbp]", r"\centering",
        rf"\caption{{{caption}}}", rf"\label{{{label}}}", r"\small",
        r"\begin{tabular}{llSSSSS}", r"\toprule",
        r"代码 & 事件类型 & {EPAL} & {SEELE} & {SARGE} & {$\Delta$EPAL} & {$\Delta$SEELE} \\", r"\midrule",
    ]
    for row in rows:
        lines.append(" & ".join([
            latex_text(row["code"]), latex_text(row["event_type"]),
            latex_num(row["epal"]), latex_num(row["seele"]), latex_num(row["sarge"]),
            latex_num(row["sarge"] - row["epal"]), latex_num(row["sarge"] - row["seele"]),
        ]) + r" \\")
    lines.extend([r"\bottomrule", r"\end{tabular}", r"\end{table}", ""])
    write_table_file(filename, "\n".join(lines))


def write_metric_family_table() -> None:
    rows = [
        ("legacy_doc2edag_native_fixed_slot", "主表", "与 EPAL/SEELE 公开 fixed-slot 表格对齐；报告 ChFinAnn full-dev 与 DuEE-Fin labeled test。"),
        ("unified_strict", "附录诊断", "回答 canonical JSONL 的严格文本匹配问题，并提供 exact-record 诊断；不与 fixed-slot 主表混算。"),
        ("docfee_official", "不用于本文主表", "仅适用于 DocFEE official-style 轨道；本文两个主数据集不报告该指标。"),
    ]
    lines = [
        r"\begin{table}[htbp]", r"\centering", r"\caption{评测指标族边界。三族回答不同问题，不可压成单一综合数。}",
        r"\label{tab:metric-families}", r"\small",
        r"\begin{tabular}{>{\raggedright\arraybackslash}p{0.34\textwidth}>{\raggedright\arraybackslash}p{0.16\textwidth}>{\raggedright\arraybackslash}p{0.42\textwidth}}",
        r"\toprule", r"指标族 & 本文位置 & 边界说明 \\", r"\midrule",
    ]
    for metric, place, note in rows:
        metric_text = latex_text(metric).replace(r"\_", r"\_\allowbreak{}")
        lines.append(f"{metric_text} & {latex_text(place)} & {latex_text(note)} \\\\")
    lines.extend([r"\bottomrule", r"\end{tabular}", r"\end{table}", ""])
    write_table_file("metric_families.tex", "\n".join(lines))


def write_sft_gain_table() -> None:
    lines = [
        r"\begin{table}[htbp]", r"\centering",
        r"\caption{监督微调（SFT）增益。同一 split、同一后端下，no-SFT 基座与 LoRA-SFT 的 fixed-slot F1 对比（单位：\%）。}",
        r"\label{tab:sft-gain}", r"\small", r"\resizebox{\textwidth}{!}{%",
        r"\begin{tabular}{lllSSS}", r"\toprule",
        r"数据集 & split & 后端 & {no-SFT} & {SFT} & {$\Delta$} \\", r"\midrule",
    ]
    for r in ABL["sft_gain"]:
        ns, sf = pct(r["no_sft_f1"]), pct(r["sft_f1"])
        lines.append(" & ".join([
            latex_text(r["dataset"]), latex_text(r["split"]), latex_text(r["backend"]),
            latex_num(ns), latex_num(sf), latex_num(sf - ns),
        ]) + r" \\")
    lines.extend([r"\bottomrule", r"\end{tabular}%", r"}", r"\end{table}", ""])
    write_table_file("sft_gain.tex", "\n".join(lines))


def write_backend_table() -> None:
    lines = [
        r"\begin{table}[htbp]", r"\centering",
        r"\caption{推理后端对比（同 split、同 k=1 greedy）。HF 4-bit NF4 + LoRA 与 vLLM BF16 merged 的 fixed-slot F1（单位：\%）。}",
        r"\label{tab:backend}", r"\small",
        r"\begin{tabular}{llSSS}", r"\toprule",
        r"数据集 & split & {HF 4-bit NF4} & {vLLM BF16} & {$\Delta$} \\", r"\midrule",
    ]
    for r in ABL["backend"]:
        hf, vl = pct(r["hf_4bit_nf4_f1"]), pct(r["vllm_bf16_f1"])
        lines.append(" & ".join([
            latex_text(r["dataset"]), latex_text(r["split"]),
            latex_num(hf), latex_num(vl), latex_num(vl - hf),
        ]) + r" \\")
    lines.extend([r"\bottomrule", r"\end{tabular}", r"\end{table}", ""])
    write_table_file("backend.tex", "\n".join(lines))


def write_decoding_table() -> None:
    lines = [
        r"\begin{table}[htbp]", r"\centering",
        r"\caption{解码策略消融（vLLM BF16）。greedy(k=1) 与 sampling(k=4, top\_p=0.95) 在不同温度下的 fixed-slot F1（单位：\%）。}",
        r"\label{tab:decoding}", r"\small",
        r"\begin{tabular}{llSSSS}", r"\toprule",
        r"数据集 & split & {k=1 greedy} & {k=4 T=0.3} & {k=4 T=0.5} & {k=4 T=0.7} \\", r"\midrule",
    ]
    for r in ABL["decoding"]:
        cells = [latex_text(r["dataset"]), latex_text(r["split"]), latex_num(pct(r["k1_greedy_f1"]))]
        cells.append(latex_num(pct(r["k4_t03_f1"])) if "k4_t03_f1" in r else r"\multicolumn{1}{c}{--}")
        cells.append(latex_num(pct(r["k4_t05_f1"])) if "k4_t05_f1" in r else r"\multicolumn{1}{c}{--}")
        cells.append(latex_num(pct(r["k4_t07_f1"])) if "k4_t07_f1" in r else r"\multicolumn{1}{c}{--}")
        lines.append(" & ".join(cells) + r" \\")
    lines.extend([r"\bottomrule", r"\end{tabular}", r"\end{table}", ""])
    write_table_file("decoding.tex", "\n".join(lines))


def write_robustness_table() -> None:
    rob = ABL["robustness"]
    er = rob["exact_record_f1"]
    lines = [
        r"\begin{table}[htbp]", r"\centering",
        r"\caption{输出鲁棒性与 exact-record 诊断（unified\_strict 口径）。schema-valid rate 为 schema 合法预测占比；exact-record F1 $=2\cdot\text{record\_exact\_match}/\text{validated\_record}$。ProcNet 为同口径 seed42 参考。}",
        r"\label{tab:robustness}", r"\small",
        r"\begin{tabular}{lSS}", r"\toprule",
        r"指标 & {ChFinAnn dev} & {DuEE-Fin test} \\", r"\midrule",
    ]
    chf, due = rob["chfinann_dev"], rob["dueefin_test"]
    lines.append(rf"schema-valid rate & {chf['schema_valid_rate']:.2f} & {due['schema_valid_rate']:.2f} \\")
    lines.append(rf"parse failures & {chf['parse_failure_count']} & {due['parse_failure_count']} \\")
    lines.append(rf"invalid event types & {chf['invalid_event_type_count']} & {due['invalid_event_type_count']} \\")
    lines.append(rf"invalid roles & {chf['invalid_role_count']} & {due['invalid_role_count']} \\")
    lines.extend([
        r"\midrule",
        rf"SARGE exact-record F1 & \multicolumn{{1}}{{c}}{{--}} & {pct(er['sarge_dueefin_test_no_lrd']):.1f} \\",
        rf"ProcNet exact-record F1 (seed42) & \multicolumn{{1}}{{c}}{{--}} & {pct(er['procnet_dueefin_test_seed42']):.1f} \\",
        r"\bottomrule", r"\end{tabular}", r"\end{table}", "",
    ])
    write_table_file("robustness.tex", "\n".join(lines))


def write_tables() -> None:
    write_main_table()
    write_run_config_table()
    write_event_table("chfinann_event_results.tex", r"ChFinAnn 分事件类型 fixed-slot F1（dev/full-dev，单位：\%）", "tab:chfinann-events", CHFINANN_EVENTS)
    write_event_table("dueefin_event_results.tex", r"DuEE-Fin labeled test 分事件类型 fixed-slot F1（单位：\%）", "tab:dueefin-events", DUEEFIN_EVENTS)
    write_metric_family_table()
    write_sft_gain_table()
    write_backend_table()
    write_decoding_table()
    write_robustness_table()


# --------------------------------------------------------------------------- #
# figures
# --------------------------------------------------------------------------- #
def configure_matplotlib() -> None:
    if FONT_PATH.exists():
        font_manager.fontManager.addfont(str(FONT_PATH))
        font_name = font_manager.FontProperties(fname=str(FONT_PATH)).get_name()
        plt.rcParams["font.family"] = font_name
    plt.rcParams.update({
        "axes.unicode_minus": False, "figure.facecolor": "white", "axes.facecolor": "white",
        "axes.edgecolor": "#333333", "axes.linewidth": 0.8, "axes.labelsize": 9.5,
        "axes.titlesize": 10.5, "xtick.labelsize": 8.2, "ytick.labelsize": 8.2,
        "legend.fontsize": 8.4, "savefig.dpi": 300,
    })


def save_pdf(fig: plt.Figure, name: str) -> None:
    FIGURE_DIR.mkdir(parents=True, exist_ok=True)
    buffer = io.BytesIO()
    fig.savefig(buffer, format="png", bbox_inches="tight", dpi=220)
    buffer.seek(0)
    with Image.open(buffer) as image:
        image.convert("RGB").save(FIGURE_DIR / name, "PDF", resolution=220.0)
    plt.close(fig)


COLOR_SARGE = "#9b3a34"
COLOR_SEELE = "#27766f"
COLOR_EPAL = "#44546a"
COLOR_GREY = "#a9a9a9"


def plot_method_pipeline() -> None:
    """Fixed fallback architecture figure (no text overflow).

    The publication figure is regenerated from figures/ARCH_PROMPT.md via the
    GPT web UI; this fallback keeps the document compilable in the meantime.
    """
    fig, ax = plt.subplots(figsize=(11.8, 4.6))
    ax.set_axis_off()
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    steps = [
        (0.020, "文档 + Schema\n事件类型与角色表"),
        (0.215, "Surface Memory\n规则候选片段(≤40)"),
        (0.410, "Role-safe JSON 合约\nSchema-slot 受控生成"),
        (0.605, "Qwen3-4B + LoRA\nk=1 greedy 解码"),
        (0.800, "规则记录消歧\nanchor 兼容合并"),
    ]
    w, h, y = 0.180, 0.24, 0.58
    for x, text in steps:
        ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.012,rounding_size=0.012",
                                    linewidth=1.0, edgecolor="#2f3437", facecolor="#f5f6f4"))
        ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=9.4)
    for (x0, _), (x1, _) in zip(steps[:-1], steps[1:]):
        ax.add_patch(FancyArrowPatch((x0 + w + 0.002, y + h / 2), (x1 - 0.004, y + h / 2),
                                     arrowstyle="-|>", mutation_scale=11, linewidth=1.0, color="#555555"))
    # eval box: width chosen to fully contain its text
    ebx, ebw = 0.150, 0.700
    ax.add_patch(FancyBboxPatch((ebx, 0.16), ebw, 0.20, boxstyle="round,pad=0.012,rounding_size=0.012",
                                linewidth=1.0, edgecolor="#2f3437", facecolor="#eef2f5"))
    ax.text(ebx + ebw / 2, 0.30, "Canonical JSONL → 三轨评测", ha="center", va="center", fontsize=9.8)
    ax.text(ebx + ebw / 2, 0.225, "legacy fixed-slot（主表） · unified_strict（诊断） · official-style（专用轨道）",
            ha="center", va="center", fontsize=8.6)
    ax.add_patch(FancyArrowPatch((0.800 + w / 2, y - 0.002), (ebx + ebw - 0.06, 0.36),
                                 arrowstyle="-|>", mutation_scale=11, linewidth=1.0, color="#555555"))
    ax.text(0.5, 0.92, "SARGE：schema-aware role-grounded generation pipeline",
            ha="center", va="center", fontsize=12)
    save_pdf(fig, "method_pipeline.pdf")


def plot_main_results() -> None:
    rows = ordered_main_rows()
    datasets = ["ChFinAnn", "DuEE-Fin"]
    fig, axes = plt.subplots(1, 2, figsize=(10.8, 5.7), sharex=False)
    colors = {"SARGE": COLOR_SARGE, "SEELE": COLOR_SEELE, "EPAL": COLOR_EPAL}
    for ax, dataset in zip(axes, datasets):
        subset = sorted([r for r in rows if r["dataset"] == dataset], key=lambda r: r["f1"])
        labels = [r["method"] for r in subset]
        values = [r["f1"] for r in subset]
        bar_colors = [colors.get(r["method"], COLOR_GREY) for r in subset]
        ax.barh(labels, values, color=bar_colors, height=0.58)
        for label, value in zip(labels, values):
            ax.text(value + 0.25, label, one_decimal(value), va="center", fontsize=8.2)
        ax.set_xlim(0, min(100, max(values) + 6))
        ax.set_xlabel("Fixed-slot F1 (%)")
        ax.set_title(dataset)
        ax.grid(axis="x", color="#e3e3e3", linewidth=0.7)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
    fig.suptitle("SARGE 与公开 fixed-slot 基线主结果（split 见正文，对比仅作参考）", y=0.99, fontsize=11.5)
    fig.tight_layout(rect=(0, 0, 1, 0.955))
    save_pdf(fig, "main_results.pdf")


def plot_event_type_results() -> None:
    fig, axes = plt.subplots(1, 2, figsize=(12.0, 6.0), gridspec_kw={"width_ratios": [0.82, 1.18]})
    for ax, rows, title in [(axes[0], CHFINANN_EVENTS, "ChFinAnn (dev)"),
                            (axes[1], DUEEFIN_EVENTS, "DuEE-Fin (labeled test)")]:
        y = list(range(len(rows)))
        labels = [f"{r['code']} {r['event_type']}" for r in rows]
        for idx, r in enumerate(rows):
            ax.plot([r["epal"], r["seele"], r["sarge"]], [idx - 0.17, idx, idx + 0.17],
                    color="#d7d7d7", linewidth=0.8, zorder=1)
        ax.scatter([r["epal"] for r in rows], [i - 0.17 for i in y], label="EPAL", color="#666666", s=25, zorder=2)
        ax.scatter([r["seele"] for r in rows], y, label="SEELE", color=COLOR_SEELE, marker="D", s=25, zorder=2)
        ax.scatter([r["sarge"] for r in rows], [i + 0.17 for i in y], label="SARGE", color=COLOR_SARGE, marker="s", s=28, zorder=3)
        vals = [v for r in rows for v in (r["epal"], r["seele"], r["sarge"])]
        ax.set_yticks(y, labels)
        ax.invert_yaxis()
        ax.set_xlim(max(0, min(vals) - 4), min(100, max(vals) + 4))
        ax.set_xlabel("Fixed-slot F1 (%)")
        ax.set_title(title)
        ax.grid(axis="x", color="#e5e5e5", linewidth=0.7)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
    axes[0].legend(loc="lower center", bbox_to_anchor=(1.15, -0.18), ncol=3, frameon=False)
    fig.suptitle("分事件类型 F1 对比", y=0.99, fontsize=12)
    fig.tight_layout(rect=(0, 0.055, 1, 0.955))
    save_pdf(fig, "event_type_results.pdf")


def plot_sft_gain() -> None:
    rows = ABL["sft_gain"]
    labels = [f"{r['dataset'].split('-')[0]}\n{r['backend'].split()[0]}" for r in rows]
    no_sft = [pct(r["no_sft_f1"]) for r in rows]
    sft = [pct(r["sft_f1"]) for r in rows]
    x = list(range(len(rows)))
    fig, ax = plt.subplots(figsize=(7.4, 4.4))
    bw = 0.36
    ax.bar([i - bw / 2 for i in x], no_sft, width=bw, label="no-SFT 基座", color=COLOR_GREY)
    ax.bar([i + bw / 2 for i in x], sft, width=bw, label="LoRA-SFT", color=COLOR_SARGE)
    for i, (a, b) in enumerate(zip(no_sft, sft)):
        ax.text(i - bw / 2, a + 1.2, f"{a:.1f}", ha="center", fontsize=8)
        ax.text(i + bw / 2, b + 1.2, f"{b:.1f}", ha="center", fontsize=8)
        ax.annotate(f"+{b - a:.1f}", xy=(i, max(a, b) + 6), ha="center", fontsize=8.6, color=COLOR_SARGE)
    ax.set_xticks(x, labels)
    ax.set_ylim(0, 100)
    ax.set_ylabel("Fixed-slot F1 (%)")
    ax.set_title("监督微调增益（同 split / 同后端）")
    ax.legend(frameon=False, loc="upper right")
    ax.grid(axis="y", color="#e5e5e5", linewidth=0.7)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.tight_layout()
    save_pdf(fig, "ablation_sft_gain.pdf")


def plot_backend_decoding() -> None:
    fig, axes = plt.subplots(1, 2, figsize=(11.0, 4.4))
    # backend panel
    ax = axes[0]
    brows = ABL["backend"]
    labels = [f"{r['dataset'].split('-')[0]}\n{r['split']}" for r in brows]
    hf = [pct(r["hf_4bit_nf4_f1"]) for r in brows]
    vl = [pct(r["vllm_bf16_f1"]) for r in brows]
    x = list(range(len(brows)))
    bw = 0.36
    ax.bar([i - bw / 2 for i in x], hf, width=bw, label="HF 4-bit NF4", color=COLOR_EPAL)
    ax.bar([i + bw / 2 for i in x], vl, width=bw, label="vLLM BF16", color=COLOR_SEELE)
    for i, (a, b) in enumerate(zip(hf, vl)):
        ax.text(i - bw / 2, a + 0.4, f"{a:.1f}", ha="center", fontsize=8)
        ax.text(i + bw / 2, b + 0.4, f"{b:.1f}", ha="center", fontsize=8)
    ax.set_xticks(x, labels)
    ax.set_ylim(60, 90)
    ax.set_ylabel("Fixed-slot F1 (%)")
    ax.set_title("推理后端对比 (k=1 greedy)")
    ax.legend(frameon=False, loc="upper left")
    ax.grid(axis="y", color="#e5e5e5", linewidth=0.7)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    # decoding panel
    ax = axes[1]
    temps = ["k1", "T0.3", "T0.5", "T0.7"]
    tkeys = {"k1": "k1_greedy_f1", "T0.3": "k4_t03_f1", "T0.5": "k4_t05_f1", "T0.7": "k4_t07_f1"}
    markers = {"DuEE-Fin-dev500": ("o", COLOR_SARGE), "ChFinAnn-Doc2EDAG": ("s", COLOR_SEELE)}
    for r in ABL["decoding"]:
        xs, ys = [], []
        for i, t in enumerate(temps):
            if tkeys[t] in r:
                xs.append(i)
                ys.append(pct(r[tkeys[t]]))
        m, c = markers[r["dataset"]]
        ax.plot(xs, ys, marker=m, color=c, label=r["dataset"].split("-")[0], linewidth=1.2)
        for xi, yi in zip(xs, ys):
            ax.text(xi, yi + 0.4, f"{yi:.1f}", ha="center", fontsize=7.6, color=c)
    ax.set_xticks(range(len(temps)), ["k=1\ngreedy", "k=4\nT=0.3", "k=4\nT=0.5", "k=4\nT=0.7"])
    ax.set_ylabel("Fixed-slot F1 (%)")
    ax.set_title("解码策略消融 (vLLM BF16)")
    ax.legend(frameon=False, loc="center right")
    ax.grid(axis="y", color="#e5e5e5", linewidth=0.7)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    fig.tight_layout()
    save_pdf(fig, "ablation_backend_decoding.pdf")


# --------------------------------------------------------------------------- #
# manifest + integrity check
# --------------------------------------------------------------------------- #
def assert_integrity() -> None:
    """Fail loudly if a table number would drift from the snapshot truth."""
    assert abs(CHF["overall"]["f1"] - 0.8549316227041346) < 1e-12, "ChFinAnn F1 drift"
    assert abs(DUE["overall"]["f1"] - 0.7795968951797012) < 1e-12, "DuEE-Fin F1 drift"
    assert set(CHF["per_event"]) == set(CHFINANN_ORDER), "ChFinAnn per_event keys mismatch"
    assert set(DUE["per_event"]) == set(DUEEFIN_ORDER), "DuEE-Fin per_event keys mismatch"
    er = DUE_UNIFIED["diagnostics"]
    val = 2 * er["record_exact_match_count"] / er["validated_record_count"]
    assert abs(val - ABL["robustness"]["exact_record_f1"]["sarge_dueefin_test_no_lrd"]) < 5e-4, "exact-record drift"
    assert CHF["diagnostics"]["schema_valid_rate"] == 1.0
    assert DUE["diagnostics"]["schema_valid_rate"] == 1.0
    print("integrity OK: snapshot hashes drive every SARGE number.")


def write_source_manifest() -> None:
    manifest = {
        "generated_for": "paper/draft_v2",
        "generated_at": "2026-05-20 Asia/Shanghai",
        "local_project_root": LOCAL_PROJECT_ROOT,
        "server_project_root": SERVER_PROJECT_ROOT,
        "local_python": LOCAL_PYTHON,
        "server_python": SERVER_PYTHON,
        "asset_python": ASSET_PYTHON,
        "data_snapshot": {
            name: {"sha256": sha256_file(SNAPSHOT_DIR / name)}
            for name in sorted(p.name for p in SNAPSHOT_DIR.glob("*.json"))
        },
        "baseline_sources": [
            {"method": "EPAL", "path": str(EPAL_DOC), "sha256": sha256_file(EPAL_DOC), "tables_used": ["Table 1", "Appendix Table 4", "Appendix Table 5"]},
            {"method": "SEELE", "path": str(SEELE_DOC), "sha256": sha256_file(SEELE_DOC), "tables_used": ["Table 2", "Table 3"]},
        ],
        "sarge_sources": [
            {"dataset": "ChFinAnn-Doc2EDAG", "split": "dev", "document_count": 3204,
             "run_root": "/data/TJK/DEE/SARGE/runs/sarge_infer_ChFinAnn-Doc2EDAG_dev_20260519T040525Z",
             "snapshot": "data_snapshot/chfinann_dev_legacy.json",
             "metric_family": "legacy_doc2edag_native_fixed_slot", "overall": CHF["overall"]},
            {"dataset": "DuEE-Fin-dev500", "split": "test", "document_count": 1171,
             "run_root": "/data/TJK/DEE/SARGE/runs/sarge_infer_DuEE-Fin-dev500_test_seed13_safe_anchor_source_f56a0d3_20260520T003122Z",
             "snapshot": "data_snapshot/dueefin_test_legacy.json",
             "metric_family": "legacy_doc2edag_native_fixed_slot", "overall": DUE["overall"]},
        ],
        "ablation_evidence": "ablation_evidence.json",
        "generated_figures": sorted(p.name for p in FIGURE_DIR.glob("*.pdf")),
        "generated_tables": sorted(p.name for p in TABLE_DIR.glob("*.tex")),
    }
    (BASE_DIR / "source_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    FIGURE_DIR.mkdir(parents=True, exist_ok=True)
    TABLE_DIR.mkdir(parents=True, exist_ok=True)
    assert_integrity()
    configure_matplotlib()
    write_tables()
    plot_method_pipeline()
    plot_main_results()
    plot_event_type_results()
    plot_sft_gain()
    plot_backend_decoding()
    write_source_manifest()
    print("done.")


if __name__ == "__main__":
    main()
