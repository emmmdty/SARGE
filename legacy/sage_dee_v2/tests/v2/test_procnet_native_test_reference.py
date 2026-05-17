from __future__ import annotations

import json
import subprocess
from pathlib import Path

from tests.v2.subprocess_utils import PYTHON, python_env

REPO_ROOT = Path(__file__).resolve().parents[2]
RUNNER = REPO_ROOT / "scripts/v2/run_procnet_native_test_reference.py"
FINAL_RESULT = REPO_ROOT / "docs/refactor/SAGE_V2_FINAL_TEST_RESULT.json"


def test_runner_requires_explicit_branch_reference_flag_for_test(tmp_path: Path) -> None:
    schema, gold, pred = _write_inputs(tmp_path)
    completed = _run_runner(
        tmp_path,
        "--schema",
        str(schema),
        "--gold",
        str(gold),
        "--pred",
        str(pred),
        "--procnet-root",
        str(tmp_path / "procnet"),
        "--out-dir",
        str(tmp_path / "out"),
    )

    assert completed.returncode == 2
    assert "requires --branch-methodology-reference" in completed.stderr


def test_runner_rejects_phase13_run_root_output(tmp_path: Path) -> None:
    schema, gold, pred = _write_inputs(tmp_path)
    phase13_root = tmp_path / "phase13_final_test_seed42_recovery_20260506T113047Z"

    completed = _run_runner(
        tmp_path,
        "--schema",
        str(schema),
        "--gold",
        str(gold),
        "--pred",
        str(pred),
        "--procnet-root",
        str(tmp_path / "procnet"),
        "--out-dir",
        str(phase13_root / "native_reference"),
        "--branch-methodology-reference",
    )

    assert completed.returncode == 2
    assert "refuses to write under a Phase 13 run root" in completed.stderr


def test_runner_writes_reference_only_metrics_without_mutating_final_result(tmp_path: Path) -> None:
    schema, gold, pred = _write_inputs(tmp_path)
    procnet_root = _write_procnet_metric(tmp_path)
    out_dir = tmp_path / "methodology_checks" / "procnet_native_test_reference_s4_seed42_unit"
    before = FINAL_RESULT.read_text(encoding="utf-8")

    completed = _run_runner(
        tmp_path,
        "--schema",
        str(schema),
        "--gold",
        str(gold),
        "--pred",
        str(pred),
        "--procnet-root",
        str(procnet_root),
        "--out-dir",
        str(out_dir),
        "--branch-methodology-reference",
    )

    assert completed.returncode == 0, completed.stderr
    assert FINAL_RESULT.read_text(encoding="utf-8") == before

    metrics = json.loads((out_dir / "procnet_native_reference_metrics.json").read_text(encoding="utf-8"))
    diagnostics = json.loads((out_dir / "conversion_diagnostics.json").read_text(encoding="utf-8"))
    note = (out_dir / "methodology_note.md").read_text(encoding="utf-8")

    assert metrics["native_reference_only"] is True
    assert metrics["formal_metric"] is False
    assert metrics["frozen_final_result"] is False
    assert metrics["phase13_reinterpretation"] is False
    assert metrics["micro_f1"] == 1.0
    assert metrics["source_system"] == "Phase13 S4 seed42 frozen final-test prediction"
    assert diagnostics["split"] == "test"
    assert diagnostics["doc_id_alignment_ok"] is True
    assert diagnostics["unknown_gold_event_types"] == {}
    assert diagnostics["unknown_pred_event_types"] == {}
    assert "独立方法论参考分支" in note
    assert "非 frozen final result" in note
    assert "SAGE S4/full seed42" not in note
    assert "Phase13 S4 seed42 frozen final-test prediction" in note


def _run_runner(tmp_path: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [PYTHON, str(RUNNER), *args],
        cwd=REPO_ROOT,
        env=python_env({"PYTHONPATH": str(REPO_ROOT)}),
        check=False,
        capture_output=True,
        text=True,
    )


def _write_inputs(tmp_path: Path) -> tuple[Path, Path, Path]:
    schema = tmp_path / "schema.json"
    gold = tmp_path / "test.jsonl"
    pred = tmp_path / "test.canonical.pred.jsonl"
    schema.write_text(
        json.dumps(
            {
                "event_types": [
                    {
                        "event_type": "股份回购",
                        "roles": ["回购方", "交易金额"],
                    }
                ]
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    row = {
        "doc_id": "doc-1",
        "events": [
            {
                "event_type": "股份回购",
                "arguments": {
                    "回购方": [{"text": "甲公司"}],
                    "交易金额": [{"text": "100万元"}],
                },
            }
        ],
    }
    gold.write_text(json.dumps(row, ensure_ascii=False) + "\n", encoding="utf-8")
    pred.write_text(json.dumps(row, ensure_ascii=False) + "\n", encoding="utf-8")
    return schema, gold, pred


def _write_procnet_metric(tmp_path: Path) -> Path:
    root = tmp_path / "procnet"
    metric = root / "procnet" / "dee" / "dee_metric.py"
    metric.parent.mkdir(parents=True)
    (root / "procnet" / "__init__.py").write_text("", encoding="utf-8")
    (root / "procnet" / "dee" / "__init__.py").write_text("", encoding="utf-8")
    metric.write_text(
        """
def measure_event_table_filling(pred_record_mat_list, gold_record_mat_list, event_type_roles_list, event_type_list):
    return {
        "micro_precision": 1.0,
        "micro_recall": 1.0,
        "micro_f1": 1.0,
        "each_event": {},
    }
""".lstrip(),
        encoding="utf-8",
    )
    return root
