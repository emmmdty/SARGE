"""Build experiment summary tables under paper/exp.

The generator reads checked-in run snapshots plus asset_registry.json. It keeps
main Legacy-FS tables separate from unified/docfee diagnostics and excludes
running or invalid assets from main comparisons.
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
REGISTRY_PATH = DATA_DIR / "asset_registry.json"
BASELINE_CONSTANTS_PATH = DATA_DIR / "baseline_constants.json"


EXPECTED_INPUTS = [
    REGISTRY_PATH,
    BASELINE_CONSTANTS_PATH,
    SNAPSHOT_DIR / "chfinann_test_legacy.json",
    SNAPSHOT_DIR / "chfinann_test_unified.json",
    SNAPSHOT_DIR / "dueefin_test_legacy.json",
    SNAPSHOT_DIR / "dueefin_test_unified.json",
    SNAPSHOT_DIR / "dueefin_test_lrd_legacy.json",
    SNAPSHOT_DIR / "dueefin_test_lrd_unified.json",
]


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def require_inputs(project_root: Path) -> None:
    missing = [str(path.relative_to(project_root)) for path in EXPECTED_INPUTS if not path.exists()]
    if missing:
        raise FileNotFoundError("Missing experiment inputs: " + ", ".join(missing))


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


def exact_record_f1(diagnostics: dict[str, Any]) -> float | None:
    exact = diagnostics.get("record_exact_match_count")
    denom = diagnostics.get("validated_record_count")
    if exact is None or not denom:
        return None
    return round(2.0 * float(exact) / float(denom) * 100.0, 1)


def markdown_table(headers: list[str], rows: list[list[Any]]) -> str:
    align = ["---"] + ["---:" for _ in headers[1:]]
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join(align) + " |",
    ]
    for row in rows:
        lines.append("| " + " | ".join(fmt(cell) if isinstance(cell, (int, float)) or cell is None else str(cell) for cell in row) + " |")
    return "\n".join(lines)


def load_sources(_: Path) -> dict[str, Any]:
    constants = load_json(BASELINE_CONSTANTS_PATH)
    registry = load_json(REGISTRY_PATH)
    entries = registry["entries"]
    by_id = {entry["id"]: entry for entry in entries}
    return {
        "epal_rows": constants["epal_rows"],
        "seele_rows": constants["seele_rows"],
        "chfinann_baseline": constants["chfinann_event_baseline"],
        "dueefin_baseline": constants["dueefin_event_baseline"],
        "chfinann_test_legacy": load_json(SNAPSHOT_DIR / "chfinann_test_legacy.json"),
        "dueefin_test_legacy": load_json(SNAPSHOT_DIR / "dueefin_test_legacy.json"),
        "registry": registry,
        "entries": entries,
        "by_id": by_id,
    }


def metric(entry: dict[str, Any], family: str = "legacy") -> dict[str, float | None]:
    data = entry.get(family) or {}
    return {
        "p": pct(data.get("precision")),
        "r": pct(data.get("recall")),
        "f1": pct(data.get("f1")),
        "single": pct(data.get("single_f1")),
        "multi": pct(data.get("multi_f1")),
    }


def baseline_rows(sources: dict[str, Any], dataset: str) -> list[list[Any]]:
    rows = []
    for row in sources["epal_rows"]:
        if row["dataset"] == dataset:
            rows.append([row["method"], row["p"], row["r"], row["f1"], row["single"], row["multi"]])
    for row in sources["seele_rows"]:
        if row["dataset"] == dataset:
            rows.append([row["method"], row["p"], row["r"], row["f1"], row["single"], row["multi"]])
    return rows


def main_tables(sources: dict[str, Any]) -> dict[str, str]:
    chfinann = baseline_rows(sources, "ChFinAnn")
    chf = metric(sources["by_id"]["chfinann_test_seed13_hf4bin_k1"], "legacy")
    chfinann.append(["SARGE", chf["p"], chf["r"], chf["f1"], chf["single"], chf["multi"]])

    dueefin = baseline_rows(sources, "DuEE-Fin")
    due = metric(sources["by_id"]["dueefin_test_seed13_hf4bin_k1_no_lrd"], "legacy")
    dueefin.append(["SARGE", due["p"], due["r"], due["f1"], due["single"], due["multi"]])

    return {
        "01_chfinann_main.md": markdown_table(["ChFinAnn", "P", "R", "F1", "F1(S)", "F1(M)"], chfinann),
        "02_dueefin_main.md": markdown_table(["DuEE-Fin", "P", "R", "F1", "F1(S)", "F1(M)"], dueefin),
    }


def ablation_row(entry: dict[str, Any], factor: str, setting: str, note: str | None = None) -> list[Any]:
    m = metric(entry, "legacy")
    return [
        entry["split"],
        factor,
        setting,
        m["f1"],
        m["p"],
        m["r"],
        m["single"],
        m["multi"],
        note or entry["note"],
    ]


def ablation_tables(sources: dict[str, Any]) -> dict[str, str]:
    by = sources["by_id"]
    headers = ["Split", "Factor", "Setting", "F1", "P", "R", "F1(S)", "F1(M)", "Note"]
    chfinann_rows = [
        ablation_row(by["chfinann_test_seed13_vllm_bf16_no_sft"], "SFT", "vLLM-bf16 no-SFT"),
        ablation_row(by["chfinann_test_seed13_hf4bin_k1"], "backend", "HF-4bin + LoRA k1", "main ChFinAnn backend"),
        ablation_row(by["chfinann_test_seed13_vllm_bf16_k1"], "backend", "vLLM-bf16 + LoRA k1", "backend cross-check"),
        ablation_row(by["chfinann_test_seed13_vllm_bf16_k4_t07"], "decoding", "vLLM-bf16 + LoRA k4 T0.7"),
    ]
    dueefin_rows = [
        ablation_row(by["dueefin_test_seed13_hf4bin_no_sft"], "SFT", "HF-4bin no-SFT"),
        ablation_row(by["dueefin_test_seed13_vllm_bf16_no_sft"], "SFT", "vLLM-bf16 no-SFT"),
        ablation_row(by["dueefin_test_seed13_hf4bin_k1_no_lrd"], "backend", "HF-4bin + LoRA k1", "main DuEE-Fin backend"),
        ablation_row(by["dueefin_test_seed13_vllm_bf16_k1"], "backend", "vLLM-bf16 + LoRA k1", "backend cross-check"),
        ablation_row(by["dueefin_test_seed13_vllm_bf16_k4_t07"], "decoding", "vLLM-bf16 + LoRA k4 T0.7"),
        ablation_row(by["dueefin_test_seed13_hf4bin_k1_no_lrd"], "LRD", "no-LRD"),
        ablation_row(by["dueefin_test_seed13_hf4bin_k1_lrd"], "LRD", "safe-anchor tau=0.90"),
        ablation_row(by["dueefin_dev_seed17_lrd_invalid_k4_pool"], "LRD", "invalid k4-pool diagnostic", "not comparable; FP explosion from candidate-pool misuse"),
    ]
    return {
        "03_chfinann_ablation.md": markdown_table(headers, chfinann_rows),
        "04_dueefin_ablation.md": markdown_table(headers, dueefin_rows),
    }


def unified_rows(sources: dict[str, Any]) -> list[list[Any]]:
    rows = []
    for asset_id in (
        "chfinann_test_seed13_hf4bin_k1",
        "chfinann_test_seed13_vllm_bf16_k1",
        "dueefin_test_seed13_hf4bin_k1_no_lrd",
        "dueefin_test_seed13_hf4bin_k1_lrd",
        "dueefin_dev_seed13_hf4bin_k1",
        "dueefin_dev_seed17_train_sft_mrs_no_lrd",
        "dueefin_dev_seed42_train_sft_mrs_no_lrd",
        "dueefin_dev_seed17_lrd_invalid_k4_pool",
    ):
        entry = sources["by_id"][asset_id]
        legacy = metric(entry, "legacy")
        unified = metric(entry, "unified")
        docfee = metric(entry, "docfee")
        rows.append([
            entry["dataset"].replace("-Doc2EDAG", "").replace("-dev500", ""),
            entry["split"],
            entry["id"],
            legacy["f1"],
            unified["f1"],
            docfee["f1"],
            pct(entry.get("exact_record_f1")),
            entry["status"],
        ])
    return rows


def unified_table(sources: dict[str, Any]) -> dict[str, str]:
    return {
        "05_unified_diagnostics.md": markdown_table(
            ["Dataset", "Split", "Run", "Legacy-FS", "Unified", "DocFEE", "ExactRec", "Status"],
            unified_rows(sources),
        )
    }


def event_rows(snapshot: dict[str, Any], baseline: dict[str, Any]) -> list[list[Any]]:
    rows = []
    for key, (_, event_name, epal, seele) in baseline.items():
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


def training_table(sources: dict[str, Any]) -> dict[str, str]:
    rows = []
    for entry in sources["entries"]:
        if entry["role"] != "training_asset_completed":
            continue
        rows.append([
            entry["dataset"].replace("-Doc2EDAG", "").replace("-dev500", ""),
            entry["seed"],
            2,
            entry["document_count"],
            "-",
            fmt((entry["train_secs"] or 0) / 60.0) + " min" if entry["train_secs"] else "-",
            entry["run_root"],
            "completed",
        ])
    return {
        "08_training_summary.md": markdown_table(
            ["Dataset", "Seed", "Epochs", "Train docs", "Train events", "Time", "Run", "Status"],
            rows,
        )
    }


def artifact_table(sources: dict[str, Any]) -> dict[str, str]:
    rows = []
    for entry in sources["entries"]:
        rows.append([
            entry["dataset"].replace("-Doc2EDAG", "").replace("-dev500", ""),
            entry["split"],
            entry["id"],
            entry["status"],
            entry["role"],
            entry["snapshot_dir"] or "-",
            "yes" if entry["include_in_main_table"] else "no",
        ])
    return {
        "09_artifact_index.md": markdown_table(
            ["Dataset", "Split", "Asset", "Status", "Role", "Snapshot", "Main"],
            rows,
        )
    }


def diagnostics_table(sources: dict[str, Any]) -> dict[str, str]:
    rows = []
    for entry in sources["entries"]:
        if not entry.get("legacy"):
            continue
        diag = entry["legacy"]
        unified = entry.get("unified") or {}
        rows.append([
            entry["dataset"].replace("-Doc2EDAG", "").replace("-dev500", ""),
            entry["split"],
            entry["id"],
            pct(diag.get("schema_valid_rate")),
            diag.get("parse_failure_count"),
            diag.get("invalid_event_type_count"),
            diag.get("invalid_role_count"),
            unified.get("validated_record_count"),
            unified.get("record_exact_match_count"),
            pct(entry.get("exact_record_f1")),
            entry["status"],
        ])
    return {
        "10_robustness_diagnostics.md": markdown_table(
            ["Dataset", "Split", "Run", "SchemaOK", "ParseFail", "InvType", "InvRole", "ValidRec", "Exact", "ExactRec", "Status"],
            rows,
        )
    }


def asset_status_table(sources: dict[str, Any]) -> dict[str, str]:
    rows = []
    for entry in sources["entries"]:
        if entry["status"] == "training" and entry["role"] == "training_asset_completed":
            continue
        if entry["status"] not in {"running", "training", "invalid"}:
            continue
        rows.append([
            entry["id"],
            entry["dataset"].replace("-Doc2EDAG", "").replace("-dev500", ""),
            entry["split"],
            entry["seed"],
            entry["status"],
            entry["log"] or "-",
            entry["note"],
        ])
    return {
        "11_asset_status.md": markdown_table(
            ["Asset", "Dataset", "Split", "Seed", "Status", "Log", "Note"],
            rows,
        )
    }


def notes() -> str:
    return "\n".join(
        [
            "- All metric values in tables are percentages.",
            "- Published baseline rows are from EPAL and SEELE reported test-set tables.",
            "- `F1(S)` means single-event F1; `F1(M)` means multi-event F1.",
            "- `-` means not reported or unavailable.",
            "- `HF-4bin` means HF Transformers with 4-bit NF4 quantization and LoRA adapter.",
            "- `vLLM-bf16` means vLLM with BF16 merged weights.",
            "- Main tables use fixed-slot / Legacy-FS only.",
            "- Unified F1 uses strict canonical JSONL matching and is reported only in the diagnostic table.",
            "- ExactRec is recomputed as `2 * exact_matches / validated_records`.",
            "- Running and invalid assets are excluded from main result tables.",
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
        training_table,
        artifact_table,
        diagnostics_table,
        asset_status_table,
    ):
        tables.update(group(sources))
    return tables


def render_summary(project_root: Path = PROJECT_ROOT) -> str:
    require_inputs(project_root)
    sources = load_sources(project_root)
    tables = all_tables(sources)
    sections = [
        "# Experiment Asset Summary",
        "",
        "This document contains test-only main comparison tables plus supporting ablation, diagnostic, and asset-status tables. Values come from checked-in run snapshots and `asset_registry.json`.",
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
        "### Table 11. Active And Invalid Assets",
        "",
        tables["11_asset_status.md"],
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
