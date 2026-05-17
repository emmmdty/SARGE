from __future__ import annotations

import json
import subprocess
from pathlib import Path

from sage_dee.v2.data_interface.jsonl import read_jsonl
from tests.v2.subprocess_utils import PYTHON, python_env

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_getm_dev20_ablation_harness_dry_run_writes_summaries(tmp_path: Path) -> None:
    out_root = tmp_path / "ablation"

    completed = subprocess.run(
        [
            PYTHON,
            str(REPO_ROOT / "scripts/v2/run_getm_dev20_ablation.py"),
            "--config",
            str(REPO_ROOT / "configs/v2/sage_v2_smoke.yaml"),
            "--dry-run",
            "--limit",
            "20",
            "--k",
            "1",
            "--out-root",
            str(out_root),
        ],
        cwd=REPO_ROOT,
        env=python_env(),
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
    summary = json.loads((out_root / "summary.json").read_text(encoding="utf-8"))
    assert [row["group"] for row in summary["groups"]] == ["F0", "F1", "F2", "F3", "F4", "F5"]
    assert (out_root / "summary.csv").is_file()
    assert (out_root / "doc_subset.dev20.json").is_file()
    group_cmd = json.loads((out_root / "F1" / "ablation_command.json").read_text(encoding="utf-8"))["cmd"]
    assert "--seed" in group_cmd
    assert "42" in group_cmd
    assert "--deterministic" in group_cmd
    assert "--deterministic-warn-only" in group_cmd
    assert "--record-resolved-generation-config" in group_cmd
    assert summary["groups"][0]["canonical_rows"] == 20
    assert summary["groups"][0]["source_candidate_id_in_canonical"] is False
    assert summary["groups"][0]["parse_status_counts"] == {"ok": 20}
    for required_count in (
        "no_complete_json_object_count",
        "copied_prompt_marker_count",
        "schema_violation",
        "unknown_role",
        "unknown_event_type",
    ):
        assert required_count in summary["groups"][0]

    canonical_rows = read_jsonl(
        out_root / "F1" / "predictions" / "DuEE-Fin-dev500" / "dev.canonical.pred.jsonl"
    )
    assert len(canonical_rows) == 20
    assert "source_candidate_id" not in json.dumps(canonical_rows, ensure_ascii=False)


def test_getm_dev20_ablation_harness_rejects_forbidden_scopes(tmp_path: Path) -> None:
    base_cmd = [
        PYTHON,
        str(REPO_ROOT / "scripts/v2/run_getm_dev20_ablation.py"),
        "--config",
        str(REPO_ROOT / "configs/v2/sage_v2_smoke.yaml"),
        "--dry-run",
        "--out-root",
        str(tmp_path / "ablation"),
    ]

    for forbidden_args in (
        ["--split", "test"],
        ["--limit", "50"],
        ["--k", "2"],
    ):
        completed = subprocess.run(
            [*base_cmd, *forbidden_args],
            cwd=REPO_ROOT,
            env=python_env(),
            check=False,
            capture_output=True,
            text=True,
        )

        assert completed.returncode == 2
        assert "phase 2 ablation" in completed.stderr
