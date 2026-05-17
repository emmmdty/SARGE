from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from sage_dee.io_utils import read_yaml
from sage_dee.v2.csg.surface_memory import build_surface_memory
from sage_dee.v2.data_interface.dataset_loader import V2DocumentInput

REPO_ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = REPO_ROOT / "configs/v2/sage_v2_v21_surface_coverage.yaml"
CHANGELOG_PATH = REPO_ROOT / "docs/refactor/SAGE_V2_1_DEV_RESCUE_CHANGELOG.md"
FINAL_RESULT_PATH = REPO_ROOT / "docs/refactor/SAGE_V2_FINAL_TEST_RESULT.json"


def test_runner_rejects_test_split(tmp_path: Path) -> None:
    from scripts.v2.run_v21_r2_surface_coverage_audit import main

    config_path = _coverage_config(tmp_path, data_root=tmp_path / "data")

    assert (
        main(
            [
                "--dataset",
                "DuEE-Fin-dev500",
                "--split",
                "test",
                "--config",
                str(config_path),
                "--out-dir",
                str(tmp_path / "out"),
            ]
        )
        == 2
    )


def test_runner_does_not_expose_qwen_train_or_evaluator_args() -> None:
    from scripts.v2.run_v21_r2_surface_coverage_audit import parse_args

    required = [
        "--dataset",
        "DuEE-Fin-dev500",
        "--split",
        "dev",
        "--config",
        str(CONFIG_PATH),
        "--out-dir",
        "/tmp/r2-out",
    ]
    forbidden_args = ("--qwen-model", "--train", "--evaluator-root", "--generation-k")

    for forbidden in forbidden_args:
        with pytest.raises(SystemExit):
            parse_args([*required, forbidden, "x"])


def test_config_enables_v21_rules_only_by_opt_in() -> None:
    from sage_dee.v2.getm.candidate_generator_v21 import build_v21_surface_memory

    config = read_yaml(CONFIG_PATH)
    assert config["surface_memory"]["v21_opt_in"] is True

    document = V2DocumentInput(
        doc_id="doc-r2-1",
        dataset_id="DuEE-Fin-dev500",
        dataset="DuEE-Fin-dev500",
        split="dev",
        content="公司董事长辞职，并披露半年度报告。",
    )
    frozen = {candidate.surface for candidate in build_surface_memory(document).candidates}
    disabled = {
        candidate.surface
        for candidate in build_v21_surface_memory(document, enable_v21_rules=False).candidates
    }
    enabled = {candidate.surface for candidate in build_v21_surface_memory(document, enable_v21_rules=True).candidates}

    assert disabled == frozen
    assert "董事长" not in frozen
    assert {"董事长", "辞职", "半年度"} <= enabled


def test_dev_gold_is_used_only_for_audit_scoring_not_candidate_generation() -> None:
    from sage_dee.v2.getm.candidate_generator_v21 import build_v21_surface_memory

    document = V2DocumentInput(
        doc_id="doc-r2-2",
        dataset_id="DuEE-Fin-dev500",
        dataset="DuEE-Fin-dev500",
        split="dev",
        content="公司总经理辞职。",
    )
    memory = build_v21_surface_memory(document, enable_v21_rules=True)
    serialized = json.dumps([candidate.__dict__ for candidate in memory.candidates], ensure_ascii=False)

    assert "gold" not in serialized
    assert "SECRET_GOLD_ONLY" not in serialized


def test_v21_rules_capture_short_exact_role_surfaces() -> None:
    from sage_dee.v2.getm.candidate_generator_v21 import build_v21_surface_memory

    document = V2DocumentInput(
        doc_id="doc-r2-3",
        dataset_id="DuEE-Fin-dev500",
        dataset="DuEE-Fin-dev500",
        split="dev",
        content=(
            "公司完成A轮融资，计划减持不超过3260万股，"
            "收购标的为100%股权，公司由盈转亏并正式上市。"
        ),
    )

    surfaces = {
        candidate.surface
        for candidate in build_v21_surface_memory(document, enable_v21_rules=True).candidates
    }

    assert {"A", "不超过3260万", "100%股权", "由盈转亏", "正式上市"} <= surfaces


def test_rule_inventory_contains_target_role_metadata() -> None:
    from sage_dee.v2.getm.candidate_generator_v21 import rule_inventory

    inventory = rule_inventory()

    assert inventory
    assert all(row["rule_name"] for row in inventory)
    assert all(row["target_roles"] for row in inventory)
    assert all(row["pattern"] for row in inventory)
    assert all(row["rationale"] for row in inventory)
    assert all(row["risk"] for row in inventory)
    assert any("高管职位" in row["target_roles"] for row in inventory)
    assert any("财报周期" in row["target_roles"] for row in inventory)


def test_coverage_runner_writes_role_and_event_tables(tmp_path: Path) -> None:
    from scripts.v2.run_v21_r2_surface_coverage_audit import main

    data_root = _write_tiny_duee_fin_dataset(tmp_path / "data")
    config_path = _coverage_config(tmp_path, data_root=data_root)
    out_dir = tmp_path / "out"

    assert (
        main(
            [
                "--dataset",
                "DuEE-Fin-dev500",
                "--split",
                "dev",
                "--config",
                str(config_path),
                "--out-dir",
                str(out_dir),
            ]
        )
        == 0
    )

    summary_path = out_dir / "coverage_summary.json"
    markdown_path = out_dir / "coverage_summary.md"
    inventory_path = out_dir / "rule_inventory.json"
    manifest_path = out_dir / "run_manifest.json"

    assert summary_path.is_file()
    assert markdown_path.is_file()
    assert inventory_path.is_file()
    assert manifest_path.is_file()

    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    markdown = markdown_path.read_text(encoding="utf-8")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    assert summary["dataset"] == "DuEE-Fin-dev500"
    assert summary["split"] == "dev"
    assert summary["gold_argument_count"] == 5
    assert summary["role_level_coverage"]
    assert summary["event_type_level_coverage"]
    assert summary["v21"]["candidate_coverage_overall"] > summary["baseline"]["candidate_coverage_overall"]
    assert "## Role-Level Coverage" in markdown
    assert "## Event-Type Coverage" in markdown
    assert manifest["qwen_run"] is False
    assert manifest["train_run"] is False
    assert manifest["evaluator_run"] is False
    assert manifest["test_run"] is False
    assert manifest["test_gold_read"] is False


def test_changelog_contains_r2_change_ids() -> None:
    text = CHANGELOG_PATH.read_text(encoding="utf-8")

    for change_id in ("R2-001", "R2-002", "R2-003", "R2-004", "R2-005"):
        assert change_id in text


def test_frozen_final_result_is_not_modified() -> None:
    assert FINAL_RESULT_PATH.is_file()
    result = subprocess.run(
        ["git", "diff", "--quiet", "--", str(FINAL_RESULT_PATH.relative_to(REPO_ROOT))],
        cwd=REPO_ROOT,
        check=False,
    )

    assert result.returncode == 0


def _write_tiny_duee_fin_dataset(data_root: Path) -> Path:
    dataset_root = data_root / "DuEE-Fin-dev500"
    dataset_root.mkdir(parents=True)
    (dataset_root / "schema.json").write_text(
        json.dumps(
            {
                "dataset": "DuEE-Fin-dev500",
                "event_types": [
                    {"event_type": "高管变动", "roles": ["高管职位", "变动类型"]},
                    {"event_type": "企业融资", "roles": ["融资轮次"]},
                    {"event_type": "股份质押", "roles": ["质押物", "交易股票/股份数量"]},
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (dataset_root / "dev.jsonl").write_text(
        json.dumps(
            {
                "doc_id": "doc-r2-dev-1",
                "dataset": "DuEE-Fin-dev500",
                "split": "dev",
                "content": "公司董事长辞职，完成A轮融资，并质押股份100万股。",
                "events": [
                    {
                        "event_type": "高管变动",
                        "arguments": {
                            "高管职位": [{"text": "董事长"}],
                            "变动类型": [{"text": "辞职"}],
                        },
                    },
                    {"event_type": "企业融资", "arguments": {"融资轮次": [{"text": "A轮"}]}},
                    {
                        "event_type": "股份质押",
                        "arguments": {
                            "质押物": [{"text": "股份"}],
                            "交易股票/股份数量": [{"text": "100万股"}],
                        },
                    },
                ],
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    return data_root


def _coverage_config(tmp_path: Path, *, data_root: Path) -> Path:
    path = tmp_path / "coverage.yaml"
    path.write_text(
        "\n".join(
            [
                "version: v2.1-r2-surface-coverage-test",
                "phase: R2",
                "data:",
                "  dataset: DuEE-Fin-dev500",
                "  split: dev",
                f"  data_root: {data_root}",
                "surface_memory:",
                "  v21_opt_in: true",
                "  context_window: 36",
                "  chunk_size: 512",
                "coverage:",
                "  rc0_baseline_candidate_coverage: 0.227233",
                "  prompt_budget_chars_per_token: 2.0",
                "  prompt_budget_tokens: 4096",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    return path
