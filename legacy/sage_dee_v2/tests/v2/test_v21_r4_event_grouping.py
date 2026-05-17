from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from tests.v2.subprocess_utils import PYTHON, python_env

REPO_ROOT = Path(__file__).resolve().parents[2]
ANALYZER = REPO_ROOT / "scripts/v2/analyze_v21_r4_event_grouping.py"
AGGREGATOR = REPO_ROOT / "scripts/v2/aggregate_v21_r4_event_grouping_probe.py"
CHANGELOG_PATH = REPO_ROOT / "docs/refactor/SAGE_V2_1_DEV_RESCUE_CHANGELOG.md"
FINAL_RESULT_PATH = REPO_ROOT / "docs/refactor/SAGE_V2_FINAL_TEST_RESULT.json"


def test_analyzer_rejects_test_split(tmp_path: Path) -> None:
    from scripts.v2.analyze_v21_r4_event_grouping import main

    assert (
        main(
            [
                "--run-root",
                str(tmp_path / "r3"),
                "--row-id",
                "s4_full_or_max_frozen_surface",
                "--dataset",
                "DuEE-Fin-dev500",
                "--split",
                "test",
                "--out-dir",
                str(tmp_path / "r4"),
            ]
        )
        == 2
    )


def test_analyzer_does_not_expose_qwen_train_or_evaluator_args(tmp_path: Path) -> None:
    from scripts.v2.analyze_v21_r4_event_grouping import parse_args

    required = [
        "--run-root",
        str(tmp_path / "r3"),
        "--row-id",
        "s4_full_or_max_frozen_surface",
        "--dataset",
        "DuEE-Fin-dev500",
        "--split",
        "dev",
        "--out-dir",
        str(tmp_path / "r4"),
    ]

    for forbidden in ("--qwen-model", "--train", "--evaluator-root", "--run-evaluator"):
        with pytest.raises(SystemExit):
            parse_args([*required, forbidden, "x"])


def test_analyzer_requires_r3_row_d_artifact(tmp_path: Path) -> None:
    completed = subprocess.run(
        [
            PYTHON,
            str(ANALYZER),
            "--run-root",
            str(tmp_path / "missing-r3"),
            "--row-id",
            "s4_full_or_max_frozen_surface",
            "--dataset",
            "DuEE-Fin-dev500",
            "--split",
            "dev",
            "--out-dir",
            str(tmp_path / "r4"),
        ],
        cwd=REPO_ROOT,
        env=python_env(),
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 2
    assert "missing R3 aggregate" in completed.stderr or "missing Row D" in completed.stderr


def test_analyzer_writes_dev_only_grouping_diagnostics(tmp_path: Path) -> None:
    run_root = _write_r3_fixture(tmp_path / "r3")
    out_dir = tmp_path / "r4"

    completed = subprocess.run(
        [
            PYTHON,
            str(ANALYZER),
            "--run-root",
            str(run_root),
            "--row-id",
            "s4_full_or_max_frozen_surface",
            "--dataset",
            "DuEE-Fin-dev500",
            "--split",
            "dev",
            "--out-dir",
            str(out_dir),
        ],
        cwd=REPO_ROOT,
        env=python_env(),
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
    analysis = json.loads((out_dir / "r4_event_grouping_analysis.json").read_text(encoding="utf-8"))
    manifest = json.loads((out_dir / "run_manifest.json").read_text(encoding="utf-8"))

    assert analysis["scope"]["dev_only"] is True
    assert analysis["scope"]["test_run"] is False
    assert analysis["scope"]["qwen_run"] is False
    assert analysis["scope"]["train_run"] is False
    assert analysis["scope"]["evaluator_run"] is False
    assert analysis["primary_row"]["row_id"] == "s4_full_or_max_frozen_surface"
    assert analysis["oracle_diagnostics"]["label"] == "dev_only_non_performance"
    assert analysis["oracle_diagnostics"]["role_level_minus_exact_record"] == pytest.approx(0.3850795839290384)
    assert analysis["oracle_diagnostics"]["grouping_bottleneck_flag"] == "high"
    assert analysis["record_level_decomposition"]["record_exact_tp"] == 2
    assert analysis["record_level_decomposition"]["partially_correct_record_count"] == 3
    assert analysis["event_count_diagnostics"]["event_count_acc"] == pytest.approx(0.5)
    assert analysis["event_count_diagnostics"]["under_predicted_doc_count"] == 1
    assert analysis["event_count_diagnostics"]["over_predicted_doc_count"] == 1
    assert manifest["oracle_diagnostics"] == "dev_only_non_performance"


def test_aggregator_writes_summary_json_and_md(tmp_path: Path) -> None:
    run_root = _write_r3_fixture(tmp_path / "r3")
    out_dir = tmp_path / "r4"
    summary_json = out_dir / "v21_r4_event_grouping_summary.json"
    summary_md = out_dir / "v21_r4_event_grouping_summary.md"

    assert (
        subprocess.run(
            [
                PYTHON,
                str(ANALYZER),
                "--run-root",
                str(run_root),
                "--row-id",
                "s4_full_or_max_frozen_surface",
                "--dataset",
                "DuEE-Fin-dev500",
                "--split",
                "dev",
                "--out-dir",
                str(out_dir),
            ],
            cwd=REPO_ROOT,
            env=python_env(),
            check=False,
            capture_output=True,
            text=True,
        ).returncode
        == 0
    )

    completed = subprocess.run(
        [
            PYTHON,
            str(AGGREGATOR),
            "--run-root",
            str(out_dir),
            "--out-json",
            str(summary_json),
            "--out-md",
            str(summary_md),
        ],
        cwd=REPO_ROOT,
        env=python_env(),
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
    summary = json.loads(summary_json.read_text(encoding="utf-8"))
    markdown = summary_md.read_text(encoding="utf-8")

    assert summary["machine_readable_verdict"]["grouping_bottleneck"] == "high"
    assert summary["machine_readable_verdict"]["event_count_bottleneck"] == "high"
    assert summary["machine_readable_verdict"]["role_value_bottleneck"] == "medium"
    assert summary["machine_readable_verdict"]["need_event_planner"] is True
    assert summary["machine_readable_verdict"]["full_train_enough_for_thesis"] is False
    assert summary["machine_readable_verdict"]["recommended_next_phase"] == "R4b_event_planner_dev_probe"
    assert "dev-only non-performance" in markdown
    assert "Grouping bottleneck" in markdown


def test_changelog_contains_r4_change_ids() -> None:
    text = CHANGELOG_PATH.read_text(encoding="utf-8")

    for change_id in ("R4-001", "R4-002", "R4-003", "R4-004"):
        assert change_id in text


def test_frozen_final_result_file_is_not_modified() -> None:
    assert FINAL_RESULT_PATH.is_file()
    result = subprocess.run(
        ["git", "diff", "--quiet", "--", str(FINAL_RESULT_PATH.relative_to(REPO_ROOT))],
        cwd=REPO_ROOT,
        check=False,
    )

    assert result.returncode == 0


def _write_r3_fixture(run_root: Path) -> Path:
    artifact_root = run_root / "evaluator_artifacts" / "s4_full_or_max_frozen_surface" / "artifact"
    analysis_dir = artifact_root / "analysis" / "DuEE-Fin-dev500" / "dev"
    pred_path = run_root / "s4_full_or_max_frozen_surface/full_dev/predictions/DuEE-Fin-dev500/dev.canonical.pred.jsonl"
    gold_path = run_root / "gold/dev.jsonl"
    parse_path = run_root / "s4_full_or_max_frozen_surface/full_dev/parse_diagnostics.dev.json"

    analysis_dir.mkdir(parents=True)
    pred_path.parent.mkdir(parents=True)
    gold_path.parent.mkdir(parents=True)
    parse_path.parent.mkdir(parents=True, exist_ok=True)

    _write_jsonl(
        gold_path,
        [
            {"doc_id": "doc-1", "events": [{"event_type": "中标", "arguments": {"中标公司": [{"text": "甲公司"}]}}]},
            {
                "doc_id": "doc-2",
                "events": [
                    {
                        "event_type": "亏损",
                        "arguments": {"公司名称": [{"text": "乙公司"}], "净亏损": [{"text": "1亿元"}]},
                    },
                    {
                        "event_type": "亏损",
                        "arguments": {"公司名称": [{"text": "丙公司"}], "净亏损": [{"text": "2亿元"}]},
                    },
                ],
            },
            {"doc_id": "doc-3", "events": []},
        ],
    )
    _write_jsonl(
        pred_path,
        [
            {"doc_id": "doc-1", "events": [{"event_type": "中标", "arguments": {"中标公司": [{"text": "甲公司"}]}}]},
            {"doc_id": "doc-2", "events": [{"event_type": "亏损", "arguments": {"公司名称": [{"text": "乙公司"}]}}]},
            {"doc_id": "doc-3", "events": [{"event_type": "企业收购", "arguments": {}}]},
        ],
    )

    _write_json(
        run_root / "v21_r3_s4_train_size_scaling_summary.json",
        {
            "phase": "R3 S4 train-size scaling",
            "row_d_triggered": True,
            "scope": {
                "dev_only": True,
                "seed42_only": True,
                "s4_only": True,
                "test_run": False,
                "seed43_44_run": False,
            },
            "rows": {
                "baseline_512_existing": _row_summary(run_root, "baseline_512_existing", 512, 0.46, 0.05, 543),
                "s4_2k_frozen_surface": _row_summary(run_root, "s4_2k_frozen_surface", 2000, 0.64, 0.19, 674),
                "s4_full_or_max_frozen_surface": _row_summary(
                    run_root,
                    "s4_full_or_max_frozen_surface",
                    6474,
                    0.7373271889400921,
                    0.35224760501105373,
                    676,
                    evaluator_artifact_path=str(artifact_root),
                    prediction_path=str(pred_path),
                ),
            },
        },
    )
    for row_id, train_limit, event_f1, exact_f1, event_count in (
        ("baseline_512_existing", 512, 0.46, 0.05, 543),
        ("s4_2k_frozen_surface", 2000, 0.64, 0.19, 674),
        ("s4_full_or_max_frozen_surface", 6474, 0.7373271889400921, 0.35224760501105373, 676),
    ):
        row_dir = run_root / row_id
        row_dir.mkdir(parents=True, exist_ok=True)
        summary = _row_summary(
            run_root,
            row_id,
            train_limit,
            event_f1,
            exact_f1,
            event_count,
            evaluator_artifact_path=str(artifact_root) if row_id == "s4_full_or_max_frozen_surface" else None,
            prediction_path=str(pred_path) if row_id == "s4_full_or_max_frozen_surface" else None,
        )
        _write_json(row_dir / "row_summary.json", summary)
        _write_json(row_dir / "row_manifest.json", {"row_id": row_id, "split": "dev", "seed": 42, "test_run": False})
        _write_json(row_dir / "training_manifest.json", {"row_id": row_id, "train_limit": train_limit})
        _write_json(
            row_dir / "generation_manifest.json",
            {"row_id": row_id, "canonical_predictions_path": str(pred_path)},
        )

    _write_json(parse_path, {"parse_status_counts": {"ok": 3}, "diagnostic_counts": {"accepted_event_count": 3}})
    _write_json(
        artifact_root / "manifest.json",
        {
            "artifact_root": str(artifact_root),
            "inputs": [
                {
                    "dataset": "DuEE-Fin-dev500",
                    "split": "dev",
                    "gold_path": str(gold_path),
                    "prediction_path": str(pred_path),
                }
            ],
        },
    )
    _write_json(analysis_dir / "input_paths.json", {"gold_path": str(gold_path), "prediction_path": str(pred_path)})
    _write_json(
        analysis_dir / "overall_metrics.json",
        {
            "f1": 0.7373271889400921,
            "precision": 0.72,
            "recall": 0.75,
            "tp": 10,
            "fp": 4,
            "fn": 3,
            "num_gold_events": 681,
            "num_pred_events": 676,
        },
    )
    _write_json(
        analysis_dir / "record_level_metrics.json",
        {
            "event_count_acc": 0.5,
            "event_count_correct": 1,
            "event_count_total": 2,
            "record_exact_tp": 2,
            "record_exact_fp": 4,
            "record_exact_fn": 5,
            "record_f1_exact": 0.35224760501105373,
            "record_soft_0_8_tp": 5,
            "record_f1_soft_0_8": 0.6,
            "merge_case_count": 3,
            "split_case_count": 4,
            "wrong_grouping_case_count": 2,
        },
    )
    _write_json(
        analysis_dir / "validation_report.json",
        {"ok": True, "counts": {"duplicate_record_count": 1, "num_events": 676}},
    )
    (analysis_dir / "per_document_metrics.csv").write_text(
        "doc_id,tp,fp,fn,precision,recall,f1,num_gold_events,num_pred_events\n"
        "doc-1,1,0,0,1,1,1,1,1\n"
        "doc-2,1,1,1,0.5,0.5,0.5,2,1\n"
        "doc-3,0,1,0,0,0,0,0,1\n",
        encoding="utf-8",
    )
    (analysis_dir / "per_role_metrics.csv").write_text(
        "role,tp,fp,fn,precision,recall,f1\n"
        "中标公司,1,0,0,1,1,1\n"
        "净亏损,1,2,4,0.3333333333,0.2,0.25\n",
        encoding="utf-8",
    )
    (analysis_dir / "per_event_type_metrics.csv").write_text(
        "event_type,tp,fp,fn,precision,recall,f1\n"
        "中标,1,0,0,1,1,1\n"
        "亏损,2,3,4,0.4,0.3333333333,0.3636363636\n",
        encoding="utf-8",
    )
    (analysis_dir / "record_level_per_event_type.csv").write_text(
        "event_type,record_f1_exact,event_count_acc,merge_case_count,split_case_count,wrong_grouping_case_count\n"
        "中标,1,1,0,0,0\n"
        "亏损,0.2,0.5,3,4,2\n",
        encoding="utf-8",
    )
    (analysis_dir / "bucket_event_count.csv").write_text(
        "bucket,doc_count,f1\nsingle,1,0.7\nmulti,1,0.5\n",
        encoding="utf-8",
    )
    _write_jsonl(
        analysis_dir / "matched_event_pairs.jsonl",
        [
            {
                "doc_id": "doc-2",
                "event_type": "亏损",
                "match_status": "matched",
                "tp_args": [{"role": "公司名称", "norm_text": "乙公司"}],
                "fp_args": [{"role": "净亏损", "norm_text": "3亿元"}],
                "fn_args": [{"role": "净亏损", "norm_text": "1亿元"}],
            }
        ],
    )
    _write_jsonl(
        analysis_dir / "record_grouping_errors.jsonl",
        [
            {
                "doc_id": "doc-2",
                "event_type": "亏损",
                "error_type": "wrong_grouping_possible",
                "gold_records": [{"arguments": [{"role": "公司名称", "norm_text": "乙公司"}]}],
                "pred_records": [{"arguments": [{"role": "公司名称", "norm_text": "乙公司"}]}],
            }
        ],
    )
    return run_root


def _row_summary(
    run_root: Path,
    row_id: str,
    train_limit: int,
    event_f1: float,
    exact_f1: float,
    event_count: int,
    *,
    evaluator_artifact_path: str | None = None,
    prediction_path: str | None = None,
) -> dict[str, object]:
    return {
        "row_id": row_id,
        "system": "S4",
        "seed": 42,
        "split": "dev",
        "dataset": "DuEE-Fin-dev500",
        "surface": "frozen_compressed_phase6_final_profile",
        "train_limit": train_limit,
        "train_examples_seen": train_limit,
        "event_table_micro_f1": event_f1,
        "role_level_f1": event_f1,
        "exact_record_f1": exact_f1,
        "canonical_event_count": event_count,
        "accepted_event_count": event_count,
        "parse_error": 0,
        "evaluator_artifact_path": evaluator_artifact_path
        or str(run_root / "evaluator_artifacts" / row_id / "artifact"),
        "prediction_path": prediction_path or str(run_root / row_id / "predictions.jsonl"),
        "row_manifest_path": str(run_root / row_id / "row_manifest.json"),
        "training_manifest_path": str(run_root / row_id / "training_manifest.json"),
        "generation_manifest_path": str(run_root / row_id / "generation_manifest.json"),
        "dev_only": True,
        "seed42_only": True,
        "s4_only": True,
        "test_run": False,
        "test_gold_read": False,
        "seed43_44_run": False,
        "frozen_final_modified": False,
    }


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_jsonl(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )
