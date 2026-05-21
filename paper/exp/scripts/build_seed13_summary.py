"""Build seed13 experiment summary tables under paper/exp.

The generator is intentionally standard-library only. It reads the audited
draft_v2 snapshots plus the already verified EPAL/SEELE constants from
draft_v2's asset builder, then writes Markdown tables for paper analysis.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[3]
EXP_DIR = PROJECT_ROOT / "paper" / "exp"
DATA_DIR = EXP_DIR / "data"
TABLE_DIR = EXP_DIR / "tables"
SUMMARY_PATH = EXP_DIR / "seed13_summary.md"
SNAPSHOT_DIR = DATA_DIR / "data_snapshot"
ABLATION_PATH = DATA_DIR / "ablation_evidence.json"
BASELINE_CONSTANTS_PATH = DATA_DIR / "baseline_constants.json"


EXPECTED_INPUTS = [
    SNAPSHOT_DIR / "chfinann_dev_legacy.json",
    SNAPSHOT_DIR / "chfinann_dev_unified.json",
    SNAPSHOT_DIR / "chfinann_test_legacy.json",
    SNAPSHOT_DIR / "chfinann_test_unified.json",
    SNAPSHOT_DIR / "dueefin_test_legacy.json",
    SNAPSHOT_DIR / "dueefin_test_unified.json",
    SNAPSHOT_DIR / "dueefin_test_lrd_legacy.json",
    SNAPSHOT_DIR / "dueefin_test_lrd_unified.json",
    ABLATION_PATH,
    BASELINE_CONSTANTS_PATH,
    PROJECT_ROOT / "docs" / "exp_result.md",
]


DOCFEE_F1 = {
    ("ChFinAnn", "dev", "SARGE"): 86.4,
    ("ChFinAnn", "test", "SARGE"): 86.0,
    ("DuEE-Fin", "dev", "SARGE"): 76.8,
    ("DuEE-Fin", "test", "SARGE no-LRD"): 77.7,
    ("DuEE-Fin", "test", "SARGE LRD"): 77.8,
}

TRAINING_ROWS = [
    ["DuEE-Fin", "13", "2", "6515", "8824", "0.0791", "166 min", "0", "runs/sarge_sft_DuEE_Fin_dev500_s13_ep2_gpu0/"],
    ["ChFinAnn", "13", "2", "25632", "38088", "0.0202", "505 min", "1", "runs/sarge_sft_ChFinAnn_Doc2EDAG_s13_ep2_gpu1/"],
]


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def require_inputs(project_root: Path) -> None:
    missing = [str(path.relative_to(project_root)) for path in EXPECTED_INPUTS if not path.exists()]
    if missing:
        raise FileNotFoundError("Missing required seed13 inputs: " + ", ".join(missing))


def pct(value: float | int | None) -> float | None:
    if value is None:
        return None
    return float(value) * 100.0


def fmt(value: float | int | None) -> str:
    if value is None:
        return "-"
    if isinstance(value, int):
        return str(value)
    return f"{float(value):.1f}"


def markdown_table(headers: list[str], rows: list[list[Any]]) -> str:
    align = ["---"] + ["---:" for _ in headers[1:]]
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join(align) + " |",
    ]
    for row in rows:
        lines.append("| " + " | ".join(fmt(cell) if isinstance(cell, (int, float)) or cell is None else str(cell) for cell in row) + " |")
    return "\n".join(lines)


def legacy_metrics(snapshot: dict[str, Any]) -> dict[str, float]:
    overall = snapshot["overall"]
    subsets = snapshot["subset_metrics"]
    return {
        "p": pct(overall["precision"]),
        "r": pct(overall["recall"]),
        "f1": pct(overall["f1"]),
        "single": pct(subsets["single_event"]["f1"]),
        "multi": pct(subsets["multi_event"]["f1"]),
    }


def unified_f1(snapshot: dict[str, Any]) -> float:
    return pct(snapshot["overall"]["f1"])


def exact_record_f1(diagnostics: dict[str, Any]) -> float | None:
    denom = diagnostics.get("validated_record_count", 0)
    if not denom:
        return None
    return round(2 * diagnostics["record_exact_match_count"] / denom * 100.0, 1)


def load_sources(project_root: Path) -> dict[str, Any]:
    constants = load_json(BASELINE_CONSTANTS_PATH)
    return {
        "epal_rows": constants["epal_rows"],
        "seele_rows": constants["seele_rows"],
        "chfinann_baseline": constants["chfinann_event_baseline"],
        "dueefin_baseline": constants["dueefin_event_baseline"],
        "chfinann_dev_legacy": load_json(SNAPSHOT_DIR / "chfinann_dev_legacy.json"),
        "chfinann_dev_unified": load_json(SNAPSHOT_DIR / "chfinann_dev_unified.json"),
        "chfinann_test_legacy": load_json(SNAPSHOT_DIR / "chfinann_test_legacy.json"),
        "chfinann_test_unified": load_json(SNAPSHOT_DIR / "chfinann_test_unified.json"),
        "dueefin_test_legacy": load_json(SNAPSHOT_DIR / "dueefin_test_legacy.json"),
        "dueefin_test_unified": load_json(SNAPSHOT_DIR / "dueefin_test_unified.json"),
        "dueefin_test_lrd_legacy": load_json(SNAPSHOT_DIR / "dueefin_test_lrd_legacy.json"),
        "dueefin_test_lrd_unified": load_json(SNAPSHOT_DIR / "dueefin_test_lrd_unified.json"),
        "ablation": load_json(ABLATION_PATH),
        "exp_result": (project_root / "docs" / "exp_result.md").read_text(encoding="utf-8"),
    }


def baseline_rows(sources: dict[str, Any], dataset: str) -> list[list[Any]]:
    rows = []
    for row in sources["epal_rows"]:
        if row["dataset"] != dataset:
            continue
        rows.append([row["method"], row["p"], row["r"], row["f1"], row["single"], row["multi"]])
    for row in sources["seele_rows"]:
        if row["dataset"] == dataset:
            rows.append([row["method"], row["p"], row["r"], row["f1"], row["single"], row["multi"]])
    return rows


def main_tables(sources: dict[str, Any]) -> dict[str, str]:
    chfinann = baseline_rows(sources, "ChFinAnn")
    chfinann_metrics = legacy_metrics(sources["chfinann_test_legacy"])
    chfinann.append(["SARGE", chfinann_metrics["p"], chfinann_metrics["r"], chfinann_metrics["f1"], chfinann_metrics["single"], chfinann_metrics["multi"]])

    dueefin = baseline_rows(sources, "DuEE-Fin")
    dueefin_metrics = legacy_metrics(sources["dueefin_test_legacy"])
    dueefin.append(["SARGE", dueefin_metrics["p"], dueefin_metrics["r"], dueefin_metrics["f1"], dueefin_metrics["single"], dueefin_metrics["multi"]])

    return {
        "01_chfinann_main.md": markdown_table(["ChFinAnn", "P", "R", "F1", "F1(S)", "F1(M)"], chfinann),
        "02_dueefin_main.md": markdown_table(["DuEE-Fin", "P", "R", "F1", "F1(S)", "F1(M)"], dueefin),
    }


def metric_cell(value: str) -> float | str:
    if value == "-":
        return "-"
    try:
        number = float(value)
    except ValueError:
        return value
    if abs(number) <= 1.0:
        return pct(number)
    return number


def test_ablation_rows(exp_result: str, dataset_raw: str) -> list[list[Any]]:
    rows = []
    for line in exp_result.splitlines():
        if not line.startswith(f"| {dataset_raw} | test | 13 |"):
            continue
        cells = [cell.strip().strip("`") for cell in line.strip().strip("|").split("|")]
        if len(cells) < 11:
            continue
        factor = cells[3]
        if factor not in {"backend", "no-SFT", "decoding"}:
            continue
        setting = cells[4]
        rows.append([
            "test",
            factor,
            setting,
            metric_cell(cells[6]),
            metric_cell(cells[7]),
            metric_cell(cells[8]),
            metric_cell(cells[10]),
            metric_cell(cells[9]),
            cells[11] if len(cells) > 11 else "-",
        ])
    return rows


def sft_ablation_rows(sources: dict[str, Any], dataset_raw: str) -> list[list[Any]]:
    rows = []
    for row in sources["ablation"]["sft_gain"]:
        if row["dataset"] != dataset_raw:
            continue
        rows.append([row["split"], "SFT", f"{row['backend']} no-SFT", pct(row["no_sft_f1"]), "-", "-", "-", "-", row["exp_result_ref"]])
        rows.append([row["split"], "SFT", f"{row['backend']} SFT", pct(row["sft_f1"]), "-", "-", "-", "-", f"delta={fmt(pct(row['sft_f1'] - row['no_sft_f1']))}"])
    return rows


def backend_ablation_rows(sources: dict[str, Any], dataset_raw: str) -> list[list[Any]]:
    rows = []
    for row in sources["ablation"]["backend"]:
        if row["dataset"] != dataset_raw:
            continue
        rows.append([row["split"], "backend", f"HF-4bin, {row['decoding']}", pct(row["hf_4bit_nf4_f1"]), "-", "-", "-", "-", row["exp_result_ref"]])
        rows.append([row["split"], "backend", f"vLLM-bf16, {row['decoding']}", pct(row["vllm_bf16_f1"]), "-", "-", "-", "-", f"delta={row['delta_pp']:.1f}"])
    return rows


def decoding_ablation_rows(sources: dict[str, Any], dataset_raw: str) -> list[list[Any]]:
    rows = []
    for row in sources["ablation"]["decoding"]:
        if row["dataset"] != dataset_raw:
            continue
        rows.append([row["split"], "decoding", f"{row['backend']} k1", pct(row["k1_greedy_f1"]), "-", "-", "-", "-", row["exp_result_ref"]])
        for key, label in (("k4_t03_f1", "k4 T0.3"), ("k4_t05_f1", "k4 T0.5"), ("k4_t07_f1", "k4 T0.7")):
            if key in row:
                rows.append([row["split"], "decoding", f"{row['backend']} {label}", pct(row[key]), "-", "-", "-", "-", row["exp_result_ref"]])
    return rows


def lrd_ablation_rows(sources: dict[str, Any]) -> list[list[Any]]:
    no_lrd = legacy_metrics(sources["dueefin_test_legacy"])
    lrd = legacy_metrics(sources["dueefin_test_lrd_legacy"])
    return [
        ["test", "LRD", "no-LRD", no_lrd["f1"], no_lrd["p"], no_lrd["r"], no_lrd["single"], no_lrd["multi"], "docs/exp_result.md 7.2"],
        ["test", "LRD", "safe-anchor", lrd["f1"], lrd["p"], lrd["r"], lrd["single"], lrd["multi"], f"delta={fmt(lrd['f1'] - no_lrd['f1'])}"],
        ["dev", "LRD", "safe-anchor tau=0.90", 76.8, "-", "-", "-", 75.5, "docs/exp_result.md 7"],
    ]


def ablation_tables(sources: dict[str, Any]) -> dict[str, str]:
    headers = ["Split", "Factor", "Setting", "F1", "P", "R", "F1(S)", "F1(M)", "Note"]
    chfinann_rows = (
        sft_ablation_rows(sources, "ChFinAnn-Doc2EDAG")
        + backend_ablation_rows(sources, "ChFinAnn-Doc2EDAG")
        + decoding_ablation_rows(sources, "ChFinAnn-Doc2EDAG")
        + test_ablation_rows(sources["exp_result"], "ChFinAnn-Doc2EDAG")
    )
    dueefin_rows = (
        sft_ablation_rows(sources, "DuEE-Fin-dev500")
        + backend_ablation_rows(sources, "DuEE-Fin-dev500")
        + decoding_ablation_rows(sources, "DuEE-Fin-dev500")
        + test_ablation_rows(sources["exp_result"], "DuEE-Fin-dev500")
        + lrd_ablation_rows(sources)
    )
    return {
        "03_chfinann_ablation.md": markdown_table(headers, chfinann_rows),
        "04_dueefin_ablation.md": markdown_table(headers, dueefin_rows),
    }


def unified_rows(sources: dict[str, Any]) -> list[list[Any]]:
    rows = []
    specs = [
        ("ChFinAnn", "dev", "SARGE", sources["chfinann_dev_legacy"], sources["chfinann_dev_unified"]),
        ("ChFinAnn", "test", "SARGE", sources["chfinann_test_legacy"], sources["chfinann_test_unified"]),
        ("DuEE-Fin", "test", "SARGE no-LRD", sources["dueefin_test_legacy"], sources["dueefin_test_unified"]),
        ("DuEE-Fin", "test", "SARGE LRD", sources["dueefin_test_lrd_legacy"], sources["dueefin_test_lrd_unified"]),
    ]
    for dataset, split, run, legacy, unified in specs:
        rows.append([
            dataset,
            split,
            run,
            legacy_metrics(legacy)["f1"],
            unified_f1(unified),
            DOCFEE_F1.get((dataset, split, run)),
            exact_record_f1(unified["diagnostics"]),
        ])
    rows.append(["DuEE-Fin", "dev", "SARGE", 76.7, 77.2, DOCFEE_F1[("DuEE-Fin", "dev", "SARGE")], 41.8])
    return rows


def unified_table(sources: dict[str, Any]) -> dict[str, str]:
    return {
        "05_unified_diagnostics.md": markdown_table(
            ["Dataset", "Split", "Run", "Legacy-FS", "Unified", "DocFEE", "ExactRec"],
            unified_rows(sources),
        )
    }


def event_rows(snapshot: dict[str, Any], baseline: dict[str, Any]) -> list[list[Any]]:
    rows = []
    for key, (code, event_name, epal, seele) in baseline.items():
        sarge = pct(snapshot["per_event"][key]["f1"])
        rows.append([event_name, epal, seele, sarge, sarge - epal, sarge - seele])
    return rows


def event_tables(sources: dict[str, Any]) -> dict[str, str]:
    return {
        "06_chfinann_event_f1.md": markdown_table(
            ["ChFinAnn Event", "EPAL", "SEELE", "SARGE", "Delta EPAL", "Delta SEELE"],
            event_rows(sources["chfinann_test_legacy"], sources["chfinann_baseline"]),
        ),
        "07_dueefin_event_f1.md": markdown_table(
            ["DuEE-Fin Event", "EPAL", "SEELE", "SARGE", "Delta EPAL", "Delta SEELE"],
            event_rows(sources["dueefin_test_legacy"], sources["dueefin_baseline"]),
        ),
    }


def training_table() -> dict[str, str]:
    return {
        "08_training_summary.md": markdown_table(
            ["Dataset", "Seed", "Epochs", "Train docs", "Train events", "Loss", "Time", "GPU", "Run"],
            TRAINING_ROWS,
        )
    }


def artifact_table() -> dict[str, str]:
    rows = [
        ["ChFinAnn", "test", "legacy snapshot", "-", "-", "paper/exp/data/data_snapshot/chfinann_test_legacy.json", "present"],
        ["ChFinAnn", "test", "unified snapshot", "-", "-", "paper/exp/data/data_snapshot/chfinann_test_unified.json", "present"],
        ["DuEE-Fin", "test", "legacy snapshot", "-", "-", "paper/exp/data/data_snapshot/dueefin_test_legacy.json", "present"],
        ["DuEE-Fin", "test", "unified snapshot", "-", "-", "paper/exp/data/data_snapshot/dueefin_test_unified.json", "present"],
        ["DuEE-Fin", "test", "LRD legacy snapshot", "-", "-", "paper/exp/data/data_snapshot/dueefin_test_lrd_legacy.json", "present"],
        ["DuEE-Fin", "test", "LRD unified snapshot", "-", "-", "paper/exp/data/data_snapshot/dueefin_test_lrd_unified.json", "present"],
        ["All", "all", "ablation evidence", "-", "-", "paper/exp/data/ablation_evidence.json", "present"],
    ]
    return {
        "09_artifact_index.md": markdown_table(
            ["Dataset", "Split", "Type", "Docs", "Events", "Path", "Status"],
            rows,
        )
    }


def diagnostics_rows(sources: dict[str, Any]) -> list[list[Any]]:
    rows = []
    specs = [
        ("ChFinAnn", "dev", "SARGE", sources["chfinann_dev_legacy"], sources["chfinann_dev_unified"]),
        ("ChFinAnn", "test", "SARGE", sources["chfinann_test_legacy"], sources["chfinann_test_unified"]),
        ("DuEE-Fin", "test", "SARGE no-LRD", sources["dueefin_test_legacy"], sources["dueefin_test_unified"]),
        ("DuEE-Fin", "test", "SARGE LRD", sources["dueefin_test_lrd_legacy"], sources["dueefin_test_lrd_unified"]),
    ]
    for dataset, split, run, legacy, unified in specs:
        diag = legacy["diagnostics"]
        udiag = unified["diagnostics"]
        rows.append([
            dataset,
            split,
            run,
            pct(diag["schema_valid_rate"]),
            diag["parse_failure_count"],
            diag["invalid_event_type_count"],
            diag["invalid_role_count"],
            udiag["validated_record_count"],
            udiag["record_exact_match_count"],
            exact_record_f1(udiag),
        ])
    rows.append(["DuEE-Fin", "dev", "SARGE", 100.0, 0, 0, 0, "-", "-", 41.8])
    return rows


def diagnostics_table(sources: dict[str, Any]) -> dict[str, str]:
    return {
        "10_robustness_diagnostics.md": markdown_table(
            ["Dataset", "Split", "Run", "SchemaOK", "ParseFail", "InvType", "InvRole", "ValidRec", "Exact", "ExactRec"],
            diagnostics_rows(sources),
        )
    }


def notes() -> str:
    return "\n".join(
        [
            "- All values are percentages.",
            "- Published baseline rows are from EPAL and SEELE reported test-set tables.",
            "- `F1(S)` means single-event F1; `F1(M)` means multi-event F1.",
            "- `-` means not reported or unavailable.",
            "- `HF-4bin` means HF Transformers with 4-bit NF4 quantization and LoRA adapter.",
            "- `vLLM-bf16` means vLLM with BF16 merged weights.",
            "- Main tables use fixed-slot / Legacy-FS only.",
            "- Unified F1 uses strict canonical JSONL matching and is reported only in the diagnostic table.",
            "- ExactRec is recomputed as `2 * exact_matches / validated_records`.",
        ]
    )


def f1_explanation() -> str:
    return "\n".join(
        [
            "Legacy-FS F1 is the fixed-schema role-slot micro-F1 used for the main EPAL/SEELE comparison. After event-type constrained record matching, role slots are counted as TP, FP, or FN, then F1 is computed from precision and recall.",
            "",
            "Unified F1 is a strict canonical JSONL role-value metric with event-type constrained global bipartite matching. It is useful for same-format diagnostics and ExactRec analysis, but it is not used in the public baseline comparison tables.",
        ]
    )


def all_tables(sources: dict[str, Any]) -> dict[str, str]:
    tables: dict[str, str] = {}
    for group in (
        main_tables,
        ablation_tables,
        unified_table,
        event_tables,
        lambda _: training_table(),
        lambda _: artifact_table(),
        diagnostics_table,
    ):
        tables.update(group(sources))
    return tables


def render_summary(project_root: Path = PROJECT_ROOT) -> str:
    require_inputs(project_root)
    sources = load_sources(project_root)
    tables = all_tables(sources)
    sections = [
        "# Seed13 Experiment Summary",
        "",
        "This document contains test-only main comparison tables plus supporting ablation and diagnostic tables for seed13.",
        "",
        "## Main Test Results",
        "",
        "The following are test-only main comparison tables.",
        "",
        "### Table 1. ChFinAnn",
        "",
        tables["01_chfinann_main.md"],
        "",
        "### Table 2. DuEE-Fin",
        "",
        tables["02_dueefin_main.md"],
        "",
        "## Ablation Results",
        "",
        "### Table 3. ChFinAnn Ablation",
        "",
        tables["03_chfinann_ablation.md"],
        "",
        "### Table 4. DuEE-Fin Ablation",
        "",
        tables["04_dueefin_ablation.md"],
        "",
        "## Unified Diagnostic Results",
        "",
        "### Table 5. Legacy-FS vs Unified",
        "",
        tables["05_unified_diagnostics.md"],
        "",
        "## Event-Level Results",
        "",
        "### Table 6. ChFinAnn Event F1",
        "",
        tables["06_chfinann_event_f1.md"],
        "",
        "### Table 7. DuEE-Fin Event F1",
        "",
        tables["07_dueefin_event_f1.md"],
        "",
        "## Training And Artifacts",
        "",
        "### Table 8. Training Summary",
        "",
        tables["08_training_summary.md"],
        "",
        "### Table 9. Artifact Index",
        "",
        tables["09_artifact_index.md"],
        "",
        "## Output Diagnostics",
        "",
        "### Table 10. Robustness Diagnostics",
        "",
        tables["10_robustness_diagnostics.md"],
        "",
        "## F1 Definitions",
        "",
        f1_explanation(),
        "",
        "## Notes",
        "",
        notes(),
        "",
    ]
    return "\n".join(sections)


def write_outputs(project_root: Path = PROJECT_ROOT) -> None:
    require_inputs(project_root)
    sources = load_sources(project_root)
    tables = all_tables(sources)
    TABLE_DIR.mkdir(parents=True, exist_ok=True)
    for filename, content in tables.items():
        (TABLE_DIR / filename).write_text(content + "\n", encoding="utf-8")
    SUMMARY_PATH.write_text(render_summary(project_root), encoding="utf-8")


def main() -> None:
    write_outputs(PROJECT_ROOT)
    print(f"wrote {SUMMARY_PATH.relative_to(PROJECT_ROOT)}")
    print(f"wrote {len(all_tables(load_sources(PROJECT_ROOT)))} table files under {TABLE_DIR.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
