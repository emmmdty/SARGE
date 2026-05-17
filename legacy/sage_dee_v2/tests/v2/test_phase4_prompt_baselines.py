from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from sage_dee.io_utils import read_yaml
from sage_dee.v2.contracts.surface import SurfaceCandidate
from sage_dee.v2.data_interface.dataset_loader import V2DocumentInput
from sage_dee.v2.data_interface.schema_registry import DatasetSchema
from sage_dee.v2.getm.prompt_builder import build_getm_prompt
from sage_dee.v2.getm.scope_guard import validate_getm_prediction_scope
from tests.v2.subprocess_utils import PYTHON, python_env

REPO_ROOT = Path(__file__).resolve().parents[2]
PHASE4_CONFIG = REPO_ROOT / "configs/v2/sage_v2_phase4_prompt_baselines.yaml"


def _schema() -> DatasetSchema:
    return DatasetSchema(
        dataset_id="unit",
        schema_dataset="unit-source",
        schema_path=Path("schema.json"),
        canonical_version=None,
        event_roles={"EventA": ("Role1", "Role2")},
        role_to_event_types={"Role1": ("EventA",), "Role2": ("EventA",)},
    )


def _document() -> V2DocumentInput:
    return V2DocumentInput(
        doc_id="doc-phase4-1",
        dataset_id="unit",
        dataset="unit-source",
        split="dev",
        content="Alpha announced value-one for EventA.",
    )


def _candidate() -> SurfaceCandidate:
    return SurfaceCandidate(
        candidate_id="doc-phase4-1:csg:000000000001",
        doc_id="doc-phase4-1",
        surface="value-one",
        context="Alpha announced value-one for EventA.",
        chunk_id="chunk_0001",
    )


@pytest.mark.parametrize(
    ("baseline_mode", "expect_schema", "expect_role_safe", "expect_surface"),
    [
        ("direct_json", False, False, False),
        ("schema_only", True, False, False),
        ("role_safe", True, True, False),
        ("role_safe_surface_memory", True, True, True),
    ],
)
def test_phase4_prompt_baseline_modes_render_expected_prompt_sections(
    baseline_mode: str,
    expect_schema: bool,
    expect_role_safe: bool,
    expect_surface: bool,
) -> None:
    prompt = build_getm_prompt(
        dataset="unit",
        schema=_schema(),
        document=_document(),
        surface_candidates=[_candidate()],
        slot_plan=None,
        candidate_render_mode="compact",
        candidate_context_chars=0,
        baseline_mode=baseline_mode,
    )

    assert ("- EventA: Role1, Role2" in prompt) is expect_schema
    assert ("For EventA, valid argument keys are: Role1, Role2." in prompt) is expect_role_safe
    assert ("arguments keys must be valid roles for the generated event_type" in prompt) is expect_role_safe
    assert ("[c0] value-one" in prompt) is expect_surface
    assert "gold-only" not in prompt


def test_phase4_config_defines_all_prompt_baselines_and_deterministic_generation() -> None:
    config = read_yaml(PHASE4_CONFIG)

    assert set(config["profiles"]) == {
        "phase4_p1_direct_json",
        "phase4_p2_schema_only",
        "phase4_p3_role_safe",
        "phase4_p4_role_safe_surface_memory",
    }
    for profile_name, baseline_mode in (
        ("phase4_p1_direct_json", "direct_json"),
        ("phase4_p2_schema_only", "schema_only"),
        ("phase4_p3_role_safe", "role_safe"),
        ("phase4_p4_role_safe_surface_memory", "role_safe_surface_memory"),
    ):
        profile = config["profiles"][profile_name]
        assert profile["getm"]["prompt"]["baseline_mode"] == baseline_mode
        generation = profile["getm"]["generation"]
        assert generation["do_sample"] is False
        assert generation["temperature"] is None
        assert generation["top_p"] == 1.0
        assert generation["seed"] == 42
        assert generation["deterministic"] is True
        assert generation["record_resolved_generation_config"] is True


def test_phase4_scope_guard_allows_limit50_only_for_phase4_baseline_profiles() -> None:
    config = read_yaml(PHASE4_CONFIG)

    validate_getm_prediction_scope(
        config_path=PHASE4_CONFIG,
        config={**config, "run": {"profile": "phase4_p1_direct_json"}},
        profile="phase4_p1_direct_json",
        split="dev",
        limit=50,
        allow_limit50=True,
    )

    with pytest.raises(ValueError, match="full dev"):
        validate_getm_prediction_scope(
            config_path=PHASE4_CONFIG,
            config={**config, "run": {"profile": "phase4_p1_direct_json"}},
            profile="phase4_p1_direct_json",
            split="dev",
            limit=None,
            allow_limit50=True,
        )
    with pytest.raises(ValueError, match="test split"):
        validate_getm_prediction_scope(
            config_path=PHASE4_CONFIG,
            config={**config, "run": {"profile": "phase4_p1_direct_json"}},
            profile="phase4_p1_direct_json",
            split="test",
            limit=50,
            allow_limit50=True,
        )


def test_phase4_runner_dry_run_writes_summary_and_subset_inputs(tmp_path: Path) -> None:
    out_root = tmp_path / "phase4"
    completed = subprocess.run(
        [
            PYTHON,
            str(REPO_ROOT / "scripts/v2/run_phase4_prompt_baselines.py"),
            "--config",
            str(PHASE4_CONFIG),
            "--dry-run",
            "--limit",
            "20",
            "--k",
            "1",
            "--out-root",
            str(out_root),
            "--skip-evaluator",
        ],
        cwd=REPO_ROOT,
        env=python_env(),
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
    summary = json.loads((out_root / "summary.json").read_text(encoding="utf-8"))
    assert [row["baseline_id"] for row in summary["baselines"]] == ["P1", "P2", "P3", "P4"]
    assert (out_root / "summary.csv").is_file()
    assert (out_root / "doc_subset.json").is_file()
    assert (out_root / "subset_benchmark" / "views" / "evaluator_gold" / "DuEE-Fin-dev500" / "dev.jsonl").is_file()
    assert (out_root / "subset_benchmark" / "DuEE-Fin-dev500" / "schema.json").is_file()

    for row in summary["baselines"]:
        assert row["canonical_rows"] == 20
        assert row["evaluator_attempted"] is False
        command = json.loads((Path(row["run_dir"]) / "phase4_command.json").read_text(encoding="utf-8"))["cmd"]
        assert "--seed" in command
        assert "42" in command
        assert "--deterministic" in command
        assert "--record-resolved-generation-config" in command
