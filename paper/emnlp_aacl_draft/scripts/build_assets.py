"""Build SARGE ACL-family paper tables and vector figures.

All quantitative values are read from the auditable paper/exp snapshots. The
script writes English LaTeX tables, SVG/PDF diagrams, and a compact source
manifest for the EMNLP/AACL draft.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path
from xml.sax.saxutils import escape

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT.parents[1]
EXP_DATA = PROJECT / "paper" / "exp" / "data"
SNAP = EXP_DATA / "data_snapshot"
REGISTRY_PATH = EXP_DATA / "asset_registry.json"
BASELINE_CONSTANTS_PATH = EXP_DATA / "baseline_constants.json"
OUT_FIG = ROOT / "figures"
OUT_TAB = ROOT / "tables"
OUT_PROMPTS = ROOT / "prompts"


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def pct(value: float) -> float:
    return value * 100.0


def fmt(value: float | None) -> str:
    return "--" if value is None else f"{value:.1f}"


def tex_escape(text: str) -> str:
    repl = {
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
    for old, new in repl.items():
        text = text.replace(old, new)
    return text


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def strip_trailing_whitespace(path: Path) -> None:
    lines = path.read_text(encoding="utf-8").splitlines()
    path.write_text("\n".join(line.rstrip() for line in lines) + "\n", encoding="utf-8")


def svg_text(x: int, y: int, text: str, size: int = 14, weight: str = "400", anchor: str = "middle") -> str:
    return (
        f'<text x="{x}" y="{y}" text-anchor="{anchor}" '
        f'font-size="{size}" font-weight="{weight}" '
        f'font-family="Arial, Helvetica, sans-serif" fill="#1f2937">{escape(text)}</text>'
    )


def svg_box(x: int, y: int, w: int, h: int, title: str, lines: list[str], fill: str, stroke: str) -> str:
    parts = [
        f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="7" fill="{fill}" stroke="{stroke}" stroke-width="1.6"/>',
        svg_text(x + w // 2, y + 25, title, 16, "700"),
    ]
    for idx, line in enumerate(lines):
        parts.append(svg_text(x + 18, y + 55 + idx * 22, line, 13, "400", "start"))
    return "\n".join(parts)


def arrow(x1: int, y1: int, x2: int, y2: int) -> str:
    return (
        f'<path d="M{x1},{y1} L{x2},{y2}" fill="none" stroke="#374151" '
        'stroke-width="1.8" marker-end="url(#arrow)"/>'
    )


def convert_svg(svg: Path) -> None:
    pdf = svg.with_suffix(".pdf")
    subprocess.run(["rsvg-convert", "-f", "pdf", "-o", str(pdf), str(svg)], check=True)


def build_architecture() -> None:
    width, height = 980, 430
    boxes = [
        (30, 100, 205, 160, "Evidence grounding", ["Document + schema", "Surface memory", "entities / dates / amounts", "schema candidate spans"], "#edf7f5", "#3b8c84"),
        (270, 100, 205, 160, "Role-grounded prompt", ["event-role schema", "candidate span table", "role-safe JSON contract", "copy role names exactly"], "#eef2ff", "#6478d3"),
        (510, 100, 205, 160, "LLM generation", ["Qwen3-4B + LoRA", "k=1 greedy decoding", "optional SACD guard", "no free-form prose"], "#fff7ed", "#d97706"),
        (750, 100, 205, 160, "Canonicalization", ["schema-valid parser", "anchor-compatible records", "deduplicate / split / merge", "canonical JSONL export"], "#f8fafc", "#64748b"),
    ]
    eval_boxes = [
        (125, 320, 205, 60, "Legacy-FS", "main fixed-slot table", "#fef2f2", "#dc2626"),
        (390, 320, 205, 60, "Unified-Strict", "canonical diagnostics", "#f0fdf4", "#16a34a"),
        (655, 320, 205, 60, "DocFEE-Official", "separate official-style track", "#f5f3ff", "#7c3aed"),
    ]
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        "<defs>",
        '<marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">',
        '<path d="M 0 0 L 10 5 L 0 10 z" fill="#374151"/>',
        "</marker>",
        "</defs>",
        '<rect width="980" height="430" fill="white"/>',
        svg_text(490, 40, "SARGE: Schema-Aware Role-Grounded Extractor", 22, "700"),
        svg_text(490, 68, "A controlled generation pipeline for Chinese financial document-level event extraction", 13),
    ]
    for x, y, w, h, title, lines, fill, stroke in boxes:
        parts.append(svg_box(x, y, w, h, title, lines, fill, stroke))
    for x1 in [235, 475, 715]:
        parts.append(arrow(x1, 180, x1 + 35, 180))
    parts.append(arrow(852, 260, 852, 305))
    parts.append(arrow(852, 305, 755, 320))
    parts.append(arrow(852, 305, 493, 320))
    parts.append(arrow(852, 305, 227, 320))
    for x, y, w, h, title, subtitle, fill, stroke in eval_boxes:
        parts.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="7" fill="{fill}" stroke="{stroke}" stroke-width="1.4"/>')
        parts.append(svg_text(x + w // 2, y + 24, title, 14, "700"))
        parts.append(svg_text(x + w // 2, y + 45, subtitle, 12))
    parts.append("</svg>")
    svg = OUT_FIG / "sarge_architecture.svg"
    write(svg, "\n".join(parts))
    convert_svg(svg)


def build_pipeline_example() -> None:
    width, height = 980, 420
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        "<defs>",
        '<marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">',
        '<path d="M 0 0 L 10 5 L 0 10 z" fill="#374151"/>',
        "</marker>",
        "</defs>",
        '<rect width="980" height="420" fill="white"/>',
        svg_text(490, 38, "From long announcement to role-safe event records", 21, "700"),
        svg_box(35, 90, 250, 210, "Input document", [
            "sentence 1: pledge notice",
            "sentence 4: 11.97M shares",
            "sentence 7: holding ratio",
            "sentence 10: release date",
            "multiple homogeneous records",
        ], "#f8fafc", "#64748b"),
        svg_box(365, 90, 250, 210, "Grounded prompt", [
            "Event type: EquityPledge",
            "Roles: pledger, shares, date...",
            "Surface candidates <= 40",
            "Amounts and dates kept verbatim",
            "Instruction: output JSON only",
        ], "#eef2ff", "#6478d3"),
        svg_box(695, 90, 250, 210, "Validated output", [
            "{\"events\": [ ... ]}",
            "schema-valid rate = 1.0",
            "parse failures = 0",
            "invalid roles = 0",
            "anchor-safe records",
        ], "#edf7f5", "#3b8c84"),
        arrow(285, 195, 365, 195),
        arrow(615, 195, 695, 195),
        svg_text(490, 345, "The model selects and organizes document-visible spans instead of freely inventing role values.", 14, "600"),
        svg_text(490, 372, "Pending multi-seed and backend-cross-check results are intentionally left as placeholders in the manuscript.", 12),
        "</svg>",
    ]
    svg = OUT_FIG / "sarge_pipeline_example.svg"
    write(svg, "\n".join(parts))
    convert_svg(svg)


def load_values() -> dict:
    registry = read_json(REGISTRY_PATH)
    entries = {entry["id"]: entry for entry in registry["entries"]}
    constants = read_json(BASELINE_CONSTANTS_PATH)
    return {"registry": registry, "entries": entries, "constants": constants}


def short_dataset(name: str) -> str:
    return name.replace("-Doc2EDAG", "").replace("-dev500", "")


def family(entry: dict, name: str = "legacy") -> dict:
    return entry.get(name) or {}


def exact_record_f1(entry: dict) -> float | None:
    return entry.get("exact_record_f1")


def legacy_cells(entry: dict) -> list[float | None]:
    values = family(entry, "legacy")
    return [
        values.get("precision"),
        values.get("recall"),
        values.get("f1"),
        values.get("single_f1"),
        values.get("multi_f1"),
    ]


def build_tables(values: dict) -> None:
    by = values["entries"]
    chf = by["chfinann_test_seed13_hf4bin_k1"]
    due = by["dueefin_test_seed13_hf4bin_k1_no_lrd"]

    main_rows = [
        ["ChFinAnn", "SARGE", "test", "HF-4bin + LoRA, k=1", *legacy_cells(chf)],
        ["DuEE-Fin", "SARGE", "test", "HF-4bin + LoRA, k=1, no-LRD", *legacy_cells(due)],
    ]
    lines = [
        r"\begin{table*}[t]",
        r"\centering",
        r"\small",
        r"\begin{tabular}{llllrrrrr}",
        r"\toprule",
        r"Dataset & Method & Split & Configuration & P & R & F1 & Single & Multi \\",
        r"\midrule",
    ]
    for row in main_rows:
        cells = row[:4] + [fmt(pct(x)) for x in row[4:]]
        lines.append(" & ".join(tex_escape(str(x)) for x in cells) + r" \\")
    lines.extend([
        r"\bottomrule",
        r"\end{tabular}",
        r"\caption{Current completed seed-13 test-set main results under the Legacy-FS metric family. HF-4bin denotes HF Transformers with 4-bit NF4 quantization and a LoRA adapter.}",
        r"\label{tab:main-results}",
        r"\end{table*}",
    ])
    write(OUT_TAB / "main_results.tex", "\n".join(lines) + "\n")

    lines = [
        r"\begin{table}[t]",
        r"\centering",
        r"\small",
        r"\resizebox{\columnwidth}{!}{%",
        r"\begin{tabular}{llrrr}",
        r"\toprule",
        r"Dataset & Track & F1 & Schema-valid & Exact-record \\",
        r"\midrule",
        f"ChFinAnn & Legacy-FS & {fmt(pct(family(chf)['f1']))} & {fmt(pct(family(chf)['schema_valid_rate']))} & {fmt(pct(exact_record_f1(chf)))} \\\\",
        f"DuEE-Fin & Legacy-FS & {fmt(pct(family(due)['f1']))} & {fmt(pct(family(due)['schema_valid_rate']))} & {fmt(pct(exact_record_f1(due)))} \\\\",
        r"\bottomrule",
        r"\end{tabular}",
        r"}",
        r"\caption{Output validity and record-level diagnostics. Exact-record is computed under Unified-Strict diagnostics and is not mixed into Legacy-FS.}",
        r"\label{tab:robustness}",
        r"\end{table}",
    ]
    write(OUT_TAB / "robustness.tex", "\n".join(lines) + "\n")

    lines = [
        r"\begin{table*}[t]",
        r"\centering",
        r"\small",
        r"\resizebox{\textwidth}{!}{%",
        r"\begin{tabular}{llllrrr}",
        r"\toprule",
        r"Dataset & Split & Backend & Ablation & Without & With & Gain \\",
        r"\midrule",
    ]
    sft_rows = [
        (
            by["chfinann_test_seed13_vllm_bf16_no_sft"],
            by["chfinann_test_seed13_vllm_bf16_k1"],
            "vLLM-bf16",
        ),
        (
            by["dueefin_test_seed13_hf4bin_no_sft"],
            by["dueefin_test_seed13_hf4bin_k1_no_lrd"],
            "HF-4bin",
        ),
        (
            by["dueefin_test_seed13_vllm_bf16_no_sft"],
            by["dueefin_test_seed13_vllm_bf16_k1"],
            "vLLM-bf16",
        ),
    ]
    for no_sft, sft, backend in sft_rows:
        without = pct(family(no_sft)["f1"])
        with_ = pct(family(sft)["f1"])
        lines.append(
            " & ".join(
                tex_escape(x)
                for x in [
                    short_dataset(sft["dataset"]),
                    sft["split"],
                    backend,
                    "LoRA SFT",
                    fmt(without),
                    fmt(with_),
                    f"+{with_ - without:.1f}",
                ]
            )
            + r" \\"
        )
    lines.extend([
        r"\bottomrule",
        r"\end{tabular}",
        r"}",
        r"\caption{Supervised fine-tuning ablations from completed seed-13 runs.}",
        r"\label{tab:sft-ablation}",
        r"\end{table*}",
    ])
    write(OUT_TAB / "sft_ablation.tex", "\n".join(lines) + "\n")

    lines = [
        r"\begin{table}[t]",
        r"\centering",
        r"\small",
        r"\resizebox{\columnwidth}{!}{%",
        r"\begin{tabular}{llrrr}",
        r"\toprule",
        r"Dataset & Split & HF & vLLM & $\Delta$ \\",
        r"\midrule",
    ]
    backend_rows = [
        (
            by["chfinann_test_seed13_hf4bin_k1"],
            by["chfinann_test_seed13_vllm_bf16_k1"],
        ),
        (
            by["dueefin_test_seed13_hf4bin_k1_no_lrd"],
            by["dueefin_test_seed13_vllm_bf16_k1"],
        ),
    ]
    for hf, vllm in backend_rows:
        hf_f1 = pct(family(hf)["f1"])
        vllm_f1 = pct(family(vllm)["f1"])
        lines.append(
            f"{tex_escape(short_dataset(hf['dataset']))} & {tex_escape(hf['split'])} & "
            f"{fmt(hf_f1)} & {fmt(vllm_f1)} & {hf_f1 - vllm_f1:+.1f} \\\\"
        )
    lines.extend([
        r"\bottomrule",
        r"\end{tabular}",
        r"}",
        r"\caption{Backend sensitivity under matched seed, split, and greedy decoding. $\Delta$ is HF-4bin minus vLLM-bf16 F1.}",
        r"\label{tab:backend-ablation}",
        r"\end{table}",
    ])
    write(OUT_TAB / "backend_ablation.tex", "\n".join(lines) + "\n")


def build_result_plot(values: dict) -> None:
    by = values["entries"]
    labels = ["ChFinAnn", "DuEE-Fin"]
    sarge = [
        pct(family(by["chfinann_test_seed13_hf4bin_k1"])["f1"]),
        pct(family(by["dueefin_test_seed13_hf4bin_k1_no_lrd"])["f1"]),
    ]
    epal = [83.4, 76.4]
    seele = [85.1, 80.8]
    x = range(len(labels))
    width = 0.24
    fig, ax = plt.subplots(figsize=(6.8, 3.2))
    ax.bar([i - width for i in x], epal, width, label="EPAL paper", color="#9ca3af")
    ax.bar(list(x), seele, width, label="SEELE paper", color="#60a5fa")
    ax.bar([i + width for i in x], sarge, width, label="SARGE completed", color="#34a853")
    ax.set_ylabel("Legacy-FS F1")
    ax.set_ylim(0, 100)
    ax.set_xticks(list(x), labels)
    ax.legend(frameon=False, ncol=3, loc="upper center", bbox_to_anchor=(0.5, 1.16))
    ax.grid(axis="y", alpha=0.2)
    for spine in ["top", "right"]:
        ax.spines[spine].set_visible(False)
    fig.tight_layout()
    OUT_FIG.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT_FIG / "main_results.pdf")
    svg = OUT_FIG / "main_results.svg"
    fig.savefig(svg)
    plt.close(fig)
    strip_trailing_whitespace(svg)


def build_manifest() -> None:
    sources = [
        REGISTRY_PATH,
        BASELINE_CONSTANTS_PATH,
        PROJECT / "paper" / "exp" / "seed13_summary.md",
        PROJECT / "docs" / "exp_result.md",
    ]
    sources.extend(sorted(SNAP.glob("*.json")))
    manifest = {
        "generated_for": "paper/emnlp_aacl_draft",
        "submission_note": "Local build metadata only; do not include this manifest in an anonymous review source bundle.",
        "local_project_root": str(PROJECT),
        "server_project_root": "/data/TJK/DEE/SARGE",
        "local_python": "/home/tjk/miniconda3/envs/feg-dev-py310/bin/python",
        "server_python": "/data/TJK/envs/sarge_vllm_full/bin/python",
        "source_files": {str(path.relative_to(PROJECT)): sha256(path) for path in sources if path.exists()},
        "generated_figures": sorted(p.name for p in OUT_FIG.glob("*") if p.is_file()),
        "generated_tables": sorted(p.name for p in OUT_TAB.glob("*.tex")),
        "note": "Quantitative values are read from asset_registry.json and completed run snapshots only; running jobs remain status-only until eval JSON exists.",
    }
    write(ROOT / "source_manifest.json", json.dumps(manifest, indent=2, ensure_ascii=False) + "\n")


def main() -> None:
    OUT_FIG.mkdir(parents=True, exist_ok=True)
    OUT_TAB.mkdir(parents=True, exist_ok=True)
    OUT_PROMPTS.mkdir(parents=True, exist_ok=True)
    values = load_values()
    build_architecture()
    build_pipeline_example()
    build_tables(values)
    build_result_plot(values)
    build_manifest()


if __name__ == "__main__":
    main()
