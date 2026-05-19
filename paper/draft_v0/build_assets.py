from __future__ import annotations

import csv
import hashlib
import json
import math
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch


BASE_DIR = Path(__file__).resolve().parent
TABLE_DIR = BASE_DIR / "tables"
ASSET_DIR = BASE_DIR / "assets"

LOCAL_PROJECT_ROOT = "/home/tjk/myProjects/masterProjects/DEE/SARGE"
SERVER_PROJECT_ROOT = "/data/TJK/DEE/SARGE"
EPAL_DOC = Path(
    "/home/tjk/myProjects/masterProjects/DEE/dee-fin/baseline/EPAL/docs/paper/EPAL.md"
)
SEELE_DOC = Path(
    "/home/tjk/myProjects/masterProjects/DEE/dee-fin/baseline/SEELE/docs/full.md"
)
FONT_PATH = Path("/home/tjk/.local/share/fonts/codex-decks/NotoSansCJKsc-Regular.otf")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def fmt(value: Any, digits: int = 1) -> str:
    if value is None:
        return "-"
    if isinstance(value, float):
        if math.isnan(value):
            return "-"
        return f"{value:.{digits}f}"
    return str(value)


def write_table(
    stem: str,
    rows: list[dict[str, Any]],
    columns: list[tuple[str, str]],
    digits: int = 1,
) -> None:
    TABLE_DIR.mkdir(parents=True, exist_ok=True)

    csv_path = TABLE_DIR / f"{stem}.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh, lineterminator="\n")
        writer.writerow([key for key, _ in columns])
        for row in rows:
            writer.writerow([fmt(row.get(key), digits) for key, _ in columns])

    md_path = TABLE_DIR / f"{stem}.md"
    headers = [label for _, label in columns]
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join(["---"] * len(headers)) + " |",
    ]
    for row in rows:
        lines.append("| " + " | ".join(fmt(row.get(key), digits) for key, _ in columns) + " |")
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


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
            "axes.labelsize": 10,
            "axes.titlesize": 11,
            "xtick.labelsize": 8.5,
            "ytick.labelsize": 8.5,
            "legend.fontsize": 8.5,
            "savefig.dpi": 300,
        }
    )


def save_figure(fig: plt.Figure, stems: list[str]) -> None:
    ASSET_DIR.mkdir(parents=True, exist_ok=True)
    for stem in stems:
        fig.savefig(ASSET_DIR / f"{stem}.png", bbox_inches="tight", dpi=300)
        fig.savefig(ASSET_DIR / f"{stem}.pdf", bbox_inches="tight")
    plt.close(fig)


EPAL_TABLE1_ROWS: list[dict[str, Any]] = [
    {
        "dataset": "ChFinAnn-Doc2EDAG",
        "method": "Doc2EDAG",
        "source": "EPAL Table 1",
        "p": 82.7,
        "r": 75.2,
        "f1": 78.8,
        "single_f1": 83.9,
        "multi_f1": 67.3,
    },
    {
        "dataset": "ChFinAnn-Doc2EDAG",
        "method": "DE-PPN",
        "source": "EPAL Table 1",
        "p": 83.7,
        "r": 76.4,
        "f1": 79.9,
        "single_f1": 85.9,
        "multi_f1": 68.4,
    },
    {
        "dataset": "ChFinAnn-Doc2EDAG",
        "method": "PTPCG",
        "source": "EPAL Table 1",
        "p": 83.7,
        "r": 75.4,
        "f1": 79.4,
        "single_f1": 88.2,
        "multi_f1": None,
    },
    {
        "dataset": "ChFinAnn-Doc2EDAG",
        "method": "GIT",
        "source": "EPAL Table 1",
        "p": 82.3,
        "r": 78.4,
        "f1": 80.3,
        "single_f1": 87.6,
        "multi_f1": 72.3,
    },
    {
        "dataset": "ChFinAnn-Doc2EDAG",
        "method": "ReDEE",
        "source": "EPAL Table 1",
        "p": 83.9,
        "r": 79.9,
        "f1": 81.9,
        "single_f1": 88.7,
        "multi_f1": 74.1,
    },
    {
        "dataset": "ChFinAnn-Doc2EDAG",
        "method": "ProCNet",
        "source": "EPAL Table 1",
        "p": 83.6,
        "r": 78.1,
        "f1": 80.8,
        "single_f1": 87.5,
        "multi_f1": 73.5,
    },
    {
        "dataset": "ChFinAnn-Doc2EDAG",
        "method": "EPAL",
        "source": "EPAL Table 1",
        "p": 83.1,
        "r": 83.5,
        "f1": 83.4,
        "single_f1": 89.7,
        "multi_f1": 76.6,
    },
    {
        "dataset": "DuEE-Fin-dev500",
        "method": "Doc2EDAG",
        "source": "EPAL Table 1",
        "p": 67.1,
        "r": 60.1,
        "f1": 63.4,
        "single_f1": 69.1,
        "multi_f1": 58.7,
    },
    {
        "dataset": "DuEE-Fin-dev500",
        "method": "DE-PPN",
        "source": "EPAL Table 1",
        "p": 69.0,
        "r": 33.5,
        "f1": 45.1,
        "single_f1": 54.2,
        "multi_f1": 21.8,
    },
    {
        "dataset": "DuEE-Fin-dev500",
        "method": "PTPCG",
        "source": "EPAL Table 1",
        "p": 71.0,
        "r": 61.7,
        "f1": 66.0,
        "single_f1": None,
        "multi_f1": None,
    },
    {
        "dataset": "DuEE-Fin-dev500",
        "method": "GIT",
        "source": "EPAL Table 1",
        "p": 69.8,
        "r": 65.9,
        "f1": 67.8,
        "single_f1": 73.7,
        "multi_f1": 63.8,
    },
    {
        "dataset": "DuEE-Fin-dev500",
        "method": "ReDEE",
        "source": "EPAL Table 1",
        "p": 77.0,
        "r": 72.0,
        "f1": 74.4,
        "single_f1": 78.9,
        "multi_f1": 70.6,
    },
    {
        "dataset": "DuEE-Fin-dev500",
        "method": "ProCNet",
        "source": "EPAL Table 1",
        "p": 79.3,
        "r": 71.4,
        "f1": 75.1,
        "single_f1": 80.1,
        "multi_f1": 71.0,
    },
    {
        "dataset": "DuEE-Fin-dev500",
        "method": "EPAL",
        "source": "EPAL Table 1",
        "p": 77.3,
        "r": 75.5,
        "f1": 76.4,
        "single_f1": 81.2,
        "multi_f1": 72.7,
    },
]

SEELE_ROWS = [
    {
        "dataset": "ChFinAnn-Doc2EDAG",
        "method": "SEELE",
        "source": "SEELE Table 2",
        "p": None,
        "r": None,
        "f1": 85.1,
        "single_f1": None,
        "multi_f1": None,
    },
    {
        "dataset": "DuEE-Fin-dev500",
        "method": "SEELE",
        "source": "SEELE Table 3",
        "p": None,
        "r": None,
        "f1": 80.8,
        "single_f1": None,
        "multi_f1": None,
    },
]

SARGE_RUN_ROWS = [
    {
        "dataset": "ChFinAnn-Doc2EDAG",
        "run_id": "sarge_infer_ChFinAnn-Doc2EDAG_dev_20260519T040525Z",
        "docs": 3204,
        "backend": "vLLM 0.8.5",
        "model_path": "runs/merged_models/qwen3_4b_chfinann_ep2_s13",
        "quantization": "BF16 merged weights",
        "adapter": "merged LoRA ep2",
        "decoding": "k=1 greedy, temperature=None, top_p=1.0",
        "seed": 13,
        "p": 83.50634371395617,
        "r": 87.5768275140578,
        "f1": 85.49316227041346,
        "single_f1": 88.34381405690859,
        "multi_f1": 83.07165623893283,
        "source": "SARGE eval_legacy_doc2edag.json",
    },
    {
        "dataset": "DuEE-Fin-dev500",
        "run_id": "sarge_infer_DuEE-Fin-dev500_dev_20260519T043458Z",
        "docs": 500,
        "backend": "HF Transformers 5.4.0",
        "model_path": "/data/TJK/DEE/SARGE/models/Qwen/Qwen3-4B-Instruct-2507",
        "quantization": "4-bit NF4, double_quant=True, compute_dtype=bf16",
        "adapter": "runs/sarge_sft_DuEE_Fin_dev500_s13_ep2_gpu0/artifacts/model/adapter",
        "decoding": "k=1 greedy, temperature=None, top_p=1.0",
        "seed": 13,
        "p": 75.47780064686856,
        "r": 77.88228155339806,
        "f1": 76.66119157831864,
        "single_f1": 79.43362831858407,
        "multi_f1": 75.35853976531942,
        "source": "SARGE eval_legacy_doc2edag.json",
    },
]


def main_rows() -> list[dict[str, Any]]:
    rows = [dict(row) for row in EPAL_TABLE1_ROWS]
    rows.extend(dict(row) for row in SEELE_ROWS)
    for row in SARGE_RUN_ROWS:
        rows.append(
            {
                "dataset": row["dataset"],
                "method": "SARGE",
                "source": row["source"],
                "p": row["p"],
                "r": row["r"],
                "f1": row["f1"],
                "single_f1": row["single_f1"],
                "multi_f1": row["multi_f1"],
            }
        )
    order = {
        "Doc2EDAG": 0,
        "DE-PPN": 1,
        "PTPCG": 2,
        "GIT": 3,
        "ReDEE": 4,
        "ProCNet": 5,
        "EPAL": 6,
        "SEELE": 7,
        "SARGE": 8,
    }
    return sorted(rows, key=lambda item: (item["dataset"], order[item["method"]]))


CHFINANN_EVENTS = [
    {"code": "EF", "event_type": "EquityFreeze", "epal_f1": 74.8, "seele_f1": 78.8, "sarge_f1": 87.25333333333334},
    {"code": "ER", "event_type": "EquityRepurchase", "epal_f1": 93.4, "seele_f1": 92.0, "sarge_f1": 90.30289823490957},
    {"code": "EU", "event_type": "EquityUnderweight", "epal_f1": 76.3, "seele_f1": 77.7, "sarge_f1": 82.48155233670401},
    {"code": "EO", "event_type": "EquityOverweight", "epal_f1": 77.3, "seele_f1": 82.4, "sarge_f1": 84.60268804527235},
    {"code": "EP", "event_type": "EquityPledge", "epal_f1": 81.5, "seele_f1": 83.1, "sarge_f1": 84.63748071705942},
]

DUEEFIN_EVENTS = [
    {"code": "CL", "event_type": "公司上市", "epal_f1": 59.1, "seele_f1": 66.5, "sarge_f1": 59.23344947735191},
    {"code": "SR", "event_type": "股东减持", "epal_f1": 74.5, "seele_f1": 76.7, "sarge_f1": 73.76146788990826},
    {"code": "EO", "event_type": "股东增持", "epal_f1": 57.5, "seele_f1": 75.5, "sarge_f1": 62.12765957446809},
    {"code": "EA", "event_type": "企业收购", "epal_f1": 68.3, "seele_f1": 72.1, "sarge_f1": 64.35845213849286},
    {"code": "FI", "event_type": "企业融资", "epal_f1": 76.1, "seele_f1": 79.1, "sarge_f1": 80.88235294117646},
    {"code": "ER", "event_type": "股份回购", "epal_f1": 91.3, "seele_f1": 94.8, "sarge_f1": 90.34825870646767},
    {"code": "EP", "event_type": "质押", "epal_f1": 78.2, "seele_f1": 85.3, "sarge_f1": 78.76520112254444},
    {"code": "CP", "event_type": "解除质押", "epal_f1": 76.8, "seele_f1": 84.8, "sarge_f1": 82.99319727891158},
    {"code": "GB", "event_type": "企业破产", "epal_f1": 69.3, "seele_f1": 62.0, "sarge_f1": 57.53424657534247},
    {"code": "EL", "event_type": "亏损", "epal_f1": 86.1, "seele_f1": 86.2, "sarge_f1": 83.53140916808149},
    {"code": "BG", "event_type": "被约谈", "epal_f1": 71.1, "seele_f1": 58.0, "sarge_f1": 72.1518987341772},
    {"code": "BI", "event_type": "中标", "epal_f1": 76.3, "seele_f1": 76.6, "sarge_f1": 73.53407290015848},
    {"code": "SC", "event_type": "高管变动", "epal_f1": 61.2, "seele_f1": 64.8, "sarge_f1": 67.21581548599671},
]


def add_event_deltas(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out = []
    for row in rows:
        item = dict(row)
        item["sarge_minus_epal"] = item["sarge_f1"] - item["epal_f1"]
        item["sarge_minus_seele"] = item["sarge_f1"] - item["seele_f1"]
        out.append(item)
    return out


def write_all_tables() -> None:
    main = main_rows()
    main_columns = [
        ("dataset", "数据集"),
        ("method", "方法"),
        ("source", "来源"),
        ("p", "P"),
        ("r", "R"),
        ("f1", "F1"),
        ("single_f1", "F1(S.)"),
        ("multi_f1", "F1(M.)"),
    ]
    write_table("main_epal_baselines", main, main_columns)
    write_table("main_results_long", main, main_columns)

    methods = ["Doc2EDAG", "DE-PPN", "PTPCG", "GIT", "ReDEE", "ProCNet", "EPAL", "SEELE", "SARGE"]
    wide_rows = []
    for method in methods:
        wide_rows.append(
            {
                "method": method,
                "chfinann_f1": next(
                    row["f1"]
                    for row in main
                    if row["dataset"] == "ChFinAnn-Doc2EDAG" and row["method"] == method
                ),
                "dueefin_f1": next(
                    row["f1"]
                    for row in main
                    if row["dataset"] == "DuEE-Fin-dev500" and row["method"] == method
                ),
            }
        )
    write_table(
        "main_results_wide",
        wide_rows,
        [("method", "方法"), ("chfinann_f1", "ChFinAnn F1"), ("dueefin_f1", "DuEE-Fin F1")],
    )

    run_columns = [
        ("dataset", "数据集"),
        ("run_id", "run_id"),
        ("docs", "文档数"),
        ("backend", "推理后端"),
        ("quantization", "量化/权重形态"),
        ("adapter", "Adapter/merged"),
        ("decoding", "解码"),
        ("seed", "seed"),
        ("p", "P"),
        ("r", "R"),
        ("f1", "F1"),
        ("single_f1", "F1(S.)"),
        ("multi_f1", "F1(M.)"),
    ]
    write_table("sarge_run_config", SARGE_RUN_ROWS, run_columns)
    write_table("sarge_completed_runs", SARGE_RUN_ROWS, run_columns)

    event_columns = [
        ("code", "事件代码"),
        ("event_type", "事件类型"),
        ("epal_f1", "EPAL"),
        ("seele_f1", "SEELE"),
        ("sarge_f1", "SARGE"),
        ("sarge_minus_epal", "SARGE-EPAL"),
        ("sarge_minus_seele", "SARGE-SEELE"),
    ]
    write_table("chfinann_event_results", add_event_deltas(CHFINANN_EVENTS), event_columns)
    write_table("dueefin_event_results", add_event_deltas(DUEEFIN_EVENTS), event_columns)


METHOD_COLORS = {
    "SARGE": "#9d3a35",
    "SEELE": "#397367",
    "EPAL": "#4f5d75",
    "Doc2EDAG": "#9a9a9a",
    "DE-PPN": "#9a9a9a",
    "PTPCG": "#9a9a9a",
    "GIT": "#9a9a9a",
    "ReDEE": "#9a9a9a",
    "ProCNet": "#9a9a9a",
}


def plot_method_overview() -> None:
    fig, ax = plt.subplots(figsize=(11.2, 4.2))
    ax.set_axis_off()

    boxes = [
        (0.04, 0.58, "输入\n文档 + 事件 schema"),
        (0.25, 0.58, "候选片段组织\nsurface memory"),
        (0.46, 0.58, "角色安全提示\nschema-slot contract"),
        (0.67, 0.58, "Qwen3-4B + LoRA\n结构化生成"),
        (0.84, 0.58, "fixed-slot\n论文可比评测"),
    ]
    for x, y, text in boxes:
        box = FancyBboxPatch(
            (x, y),
            0.14,
            0.18,
            boxstyle="round,pad=0.015,rounding_size=0.008",
            linewidth=1.0,
            edgecolor="#333333",
            facecolor="#f6f6f6",
        )
        ax.add_patch(box)
        ax.text(x + 0.07, y + 0.09, text, ha="center", va="center", fontsize=10)
    for start, end in zip(boxes[:-1], boxes[1:]):
        sx, sy, _ = start
        ex, ey, _ = end
        arrow = FancyArrowPatch(
            (sx + 0.145, sy + 0.09),
            (ex - 0.005, ey + 0.09),
            arrowstyle="-|>",
            mutation_scale=10,
            linewidth=0.9,
            color="#555555",
        )
        ax.add_patch(arrow)

    ax.plot([0.10, 0.90], [0.43, 0.43], color="#333333", linewidth=0.8)
    ax.text(0.50, 0.47, "已完成推理路径", ha="center", va="center", fontsize=10.5, color="#333333")

    runtime_boxes = [
        (
            0.10,
            0.18,
            "ChFinAnn-Doc2EDAG\nvLLM 0.8.5, BF16 merged\nk=1 greedy, 3204 docs",
            "#eef2f5",
        ),
        (
            0.56,
            0.18,
            "DuEE-Fin-dev500\nHF Transformers 5.4.0\n4-bit NF4 + LoRA ep2, 500 docs",
            "#f5efee",
        ),
    ]
    for x, y, text, color in runtime_boxes:
        box = FancyBboxPatch(
            (x, y),
            0.34,
            0.17,
            boxstyle="round,pad=0.018,rounding_size=0.008",
            linewidth=1.0,
            edgecolor="#333333",
            facecolor=color,
        )
        ax.add_patch(box)
        ax.text(x + 0.17, y + 0.085, text, ha="center", va="center", fontsize=9.6)

    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    save_figure(fig, ["method_overview", "graphical_abstract"])


def plot_main_comparison() -> None:
    data = main_rows()
    datasets = ["ChFinAnn-Doc2EDAG", "DuEE-Fin-dev500"]
    fig, axes = plt.subplots(1, 2, figsize=(10.5, 5.8), sharey=False)
    for ax, dataset in zip(axes, datasets):
        rows = sorted([row for row in data if row["dataset"] == dataset], key=lambda row: row["f1"], reverse=True)
        y = list(range(len(rows)))
        for idx, row in enumerate(rows):
            method = row["method"]
            size = 58 if method == "SARGE" else 46
            marker = "s" if method == "SARGE" else "D" if method == "SEELE" else "o"
            ax.scatter(row["f1"], idx, s=size, marker=marker, color=METHOD_COLORS[method], zorder=3)
            ax.text(row["f1"] + 0.25, idx, fmt(row["f1"]), va="center", ha="left", fontsize=8.2)
        ax.set_yticks(y, [row["method"] for row in rows])
        ax.invert_yaxis()
        values = [row["f1"] for row in rows]
        ax.set_xlim(max(0, min(values) - 4), min(100, max(values) + 3.5))
        ax.grid(axis="x", color="#e0e0e0", linewidth=0.7)
        ax.set_xlabel("F1 (%)")
        ax.set_title(dataset)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
    fig.suptitle("公开基线与 SARGE 论文可比 F1 对比", y=0.99, fontsize=12)
    fig.text(0.50, 0.01, "灰色为 EPAL 表1收录基线；SEELE 与 SARGE 分别来自对应论文表格和本项目完成运行。", ha="center", fontsize=8.6)
    fig.tight_layout(rect=(0, 0.035, 1, 0.96))
    save_figure(fig, ["main_f1_comparison", "main_results_overall"])


def plot_event_comparison(rows: list[dict[str, Any]], title: str, stems: list[str], figsize: tuple[float, float]) -> None:
    fig, ax = plt.subplots(figsize=figsize)
    labels = [f"{row['code']}  {row['event_type']}" for row in rows]
    y = list(range(len(rows)))
    offsets = {"EPAL": -0.18, "SEELE": 0.0, "SARGE": 0.18}
    values_by_method = {
        "EPAL": [row["epal_f1"] for row in rows],
        "SEELE": [row["seele_f1"] for row in rows],
        "SARGE": [row["sarge_f1"] for row in rows],
    }
    colors = {"EPAL": "#6f6f6f", "SEELE": "#397367", "SARGE": "#9d3a35"}
    markers = {"EPAL": "o", "SEELE": "D", "SARGE": "s"}
    for idx, row in enumerate(rows):
        xmin = min(row["epal_f1"], row["seele_f1"], row["sarge_f1"])
        xmax = max(row["epal_f1"], row["seele_f1"], row["sarge_f1"])
        ax.plot([xmin, xmax], [idx, idx], color="#d2d2d2", linewidth=0.9, zorder=1)
    for method in ["EPAL", "SEELE", "SARGE"]:
        ax.scatter(
            values_by_method[method],
            [pos + offsets[method] for pos in y],
            label=method,
            color=colors[method],
            marker=markers[method],
            s=35,
            zorder=3,
        )
    ax.set_yticks(y, labels)
    ax.invert_yaxis()
    flat_values = [value for values in values_by_method.values() for value in values]
    ax.set_xlim(max(0, min(flat_values) - 4), min(100, max(flat_values) + 4))
    ax.set_xlabel("F1 (%)")
    ax.set_title(title)
    ax.grid(axis="x", color="#e5e5e5", linewidth=0.7)
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.18), frameon=False, ncol=3)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.tight_layout(rect=(0, 0.08, 1, 1))
    save_figure(fig, stems)


def write_source_manifest() -> None:
    generated_tables = sorted(path.name for path in TABLE_DIR.glob("*") if path.is_file())
    generated_assets = sorted(path.name for path in ASSET_DIR.glob("*") if path.is_file())
    manifest = {
        "generated_for": "paper/draft_v0",
        "generated_at": "2026-05-20 Asia/Shanghai",
        "project": "SARGE",
        "local_project_root": LOCAL_PROJECT_ROOT,
        "server_project_root": SERVER_PROJECT_ROOT,
        "asset_base_commit": "6281ae9",
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
                "run_root": "/data/TJK/DEE/SARGE/runs/sarge_infer_ChFinAnn-Doc2EDAG_dev_20260519T040525Z",
                "run_manifest_sha256": "2d11517e9511021e85543ca4a8dd43f96f851ab9622048ef74b118c2e28786f4",
                "paper_eval_sha256": "b8e69d9f79647887a20cb53ef0b7dfa63e154fb4a8861ce67af41d27a9b8d3e6",
                "paper_metric_family": "legacy_doc2edag_native_fixed_slot",
                "backend": "vLLM 0.8.5",
                "quantization": "BF16 merged weights",
                "document_count": 3204,
                "decoding": "k=1 greedy",
            },
            {
                "dataset": "DuEE-Fin-dev500",
                "run_root": "/data/TJK/DEE/SARGE/runs/sarge_infer_DuEE-Fin-dev500_dev_20260519T043458Z",
                "run_manifest_sha256": "c19c2b3d17d152babf5fd7118db3e12d047d9aa86b6c33fbbed81102ac7d5d25",
                "paper_eval_sha256": "fbaa02691265d7beef83ad33725a2cd7a30a0b38d8c983d1c7f31ee4c6634a60",
                "paper_metric_family": "legacy_doc2edag_native_fixed_slot",
                "backend": "HF Transformers 5.4.0",
                "quantization": "4-bit NF4 + LoRA ep2",
                "document_count": 500,
                "decoding": "k=1 greedy",
            },
        ],
        "reporting_policy": {
            "comparison_metric": "legacy_doc2edag_native_fixed_slot",
            "baseline_rule": "Use EPAL and SEELE published tables directly; do not fabricate missing P/R or single/multi columns.",
            "sarge_rule": "Use only completed SARGE runs with model_performance_evidence=true in run_manifest.json.",
        },
        "generated_tables": generated_tables,
        "generated_assets": generated_assets,
    }
    (BASE_DIR / "source_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    TABLE_DIR.mkdir(parents=True, exist_ok=True)
    ASSET_DIR.mkdir(parents=True, exist_ok=True)
    configure_matplotlib()
    write_all_tables()
    plot_method_overview()
    plot_main_comparison()
    plot_event_comparison(
        CHFINANN_EVENTS,
        "ChFinAnn 分事件类型 F1",
        ["chfinann_event_comparison", "chfinann_per_event_f1"],
        (7.2, 3.7),
    )
    plot_event_comparison(
        DUEEFIN_EVENTS,
        "DuEE-Fin 分事件类型 F1",
        ["dueefin_event_comparison", "dueefin_per_event_f1"],
        (7.5, 6.4),
    )
    write_source_manifest()


if __name__ == "__main__":
    main()
