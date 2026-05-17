from __future__ import annotations

import json
from pathlib import Path

import pytest

from sage_dee.v2.data_interface.jsonl import read_jsonl, write_jsonl
from sage_dee.v2.data_interface.schema_registry import DatasetSchema
from sage_dee.v2.getm.parser_ablation import parse_getm_output_ablation


def _schema() -> DatasetSchema:
    return DatasetSchema(
        dataset_id="DuEE-Fin-dev500",
        schema_dataset="unit",
        schema_path=Path("schema.json"),
        canonical_version=None,
        event_roles={"EventA": ("Role1", "Role2")},
        role_to_event_types={"Role1": ("EventA",), "Role2": ("EventA",)},
    )


def _schema_file(tmp_path: Path) -> Path:
    path = tmp_path / "schema.json"
    path.write_text(
        json.dumps(
            {
                "dataset": "DuEE-Fin-dev500",
                "event_types": [{"event_type": "EventA", "roles": ["Role1", "Role2"]}],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    return path


def test_unknown_event_type_is_dropped_without_guessing() -> None:
    candidate = parse_getm_output_ablation(
        '{"events":[{"event_type":"EventA_alias","arguments":{"Role1":["bad"]}}]}',
        doc_id="doc-1",
        candidate_id="doc-1:getm:0",
        schema=_schema(),
        mode="drop_invalid_role_only",
    )

    assert candidate.events == []
    assert candidate.diagnostics["unknown_event_type"] == 1
    assert candidate.diagnostics["dropped_event_count"] == 1
    assert "EventA_alias" not in json.dumps(candidate.events, ensure_ascii=False)


def test_unknown_role_is_not_mapped_in_lenient_modes() -> None:
    candidate = parse_getm_output_ablation(
        '{"events":[{"event_type":"EventA","arguments":{"RoleOne":["bad"],"Role1":["valid"]}}]}',
        doc_id="doc-1",
        candidate_id="doc-1:getm:0",
        schema=_schema(),
        mode="drop_invalid_role_only",
    )

    assert len(candidate.events) == 1
    assert candidate.events[0].arguments.keys() == {"Role1"}
    assert candidate.events[0].arguments["Role1"][0].text == "valid"
    assert candidate.diagnostics["unknown_role"] == 1
    assert candidate.diagnostics["dropped_role_count"] == 1


def test_frozen_strict_drops_whole_event_on_unknown_role() -> None:
    candidate = parse_getm_output_ablation(
        '{"events":[{"event_type":"EventA","arguments":{"UnknownRole":["bad"],"Role1":["valid"]}}]}',
        doc_id="doc-1",
        candidate_id="doc-1:getm:0",
        schema=_schema(),
        mode="frozen_strict",
    )

    assert candidate.events == []
    assert candidate.diagnostics["unknown_role"] == 1
    assert candidate.diagnostics["dropped_role_count"] == 1
    assert candidate.diagnostics["dropped_event_count"] == 1
    assert candidate.diagnostics["accepted_event_count"] == 0


def test_drop_invalid_role_only_keeps_valid_roles() -> None:
    candidate = parse_getm_output_ablation(
        '{"events":[{"event_type":"EventA","arguments":{"UnknownRole":["bad"],"Role1":["valid"]}}]}',
        doc_id="doc-1",
        candidate_id="doc-1:getm:0",
        schema=_schema(),
        mode="drop_invalid_role_only",
    )

    assert len(candidate.events) == 1
    assert candidate.events[0].arguments["Role1"][0].text == "valid"
    assert candidate.diagnostics["dropped_role_count"] == 1
    assert candidate.diagnostics["dropped_event_count"] == 0
    assert candidate.diagnostics["accepted_event_count"] == 1


def test_keep_event_schema_valid_args_keeps_only_schema_valid_args() -> None:
    candidate = parse_getm_output_ablation(
        json.dumps(
            {
                "events": [
                    {
                        "event_type": "EventA",
                        "arguments": {
                            "UnknownRole": ["bad"],
                            "Role1": ["valid"],
                            "Role2": "not-a-list",
                        },
                    }
                ]
            },
            ensure_ascii=False,
        ),
        doc_id="doc-1",
        candidate_id="doc-1:getm:0",
        schema=_schema(),
        mode="keep_event_schema_valid_args",
    )

    assert len(candidate.events) == 1
    assert candidate.events[0].arguments.keys() == {"Role1"}
    assert candidate.diagnostics["dropped_role_count"] == 2
    assert candidate.diagnostics["role_value_not_list_count"] == 1
    assert candidate.diagnostics["dropped_event_count"] == 0


def test_runner_rejects_test_split_and_test_paths(tmp_path: Path) -> None:
    from scripts.v2.run_v21_r1_parser_reparse_ablation import main

    schema = _schema_file(tmp_path)
    raw = tmp_path / "raw_outputs.dev.jsonl"
    write_jsonl(raw, [{"doc_id": "doc-1", "raw_output": '{"events":[]}'}])

    with pytest.raises(SystemExit, match="dev split only"):
        main(
            [
                "--dataset",
                "DuEE-Fin-dev500",
                "--split",
                "test",
                "--raw-output",
                str(raw),
                "--schema",
                str(schema),
                "--mode",
                "frozen_strict",
                "--out-dir",
                str(tmp_path / "out"),
            ]
        )

    with pytest.raises(SystemExit, match="test"):
        main(
            [
                "--dataset",
                "DuEE-Fin-dev500",
                "--split",
                "dev",
                "--raw-output",
                str(tmp_path / "contains-test" / "raw_outputs.dev.jsonl"),
                "--schema",
                str(schema),
                "--mode",
                "frozen_strict",
                "--out-dir",
                str(tmp_path / "out"),
            ]
        )


def test_runner_writes_manifest_flags_and_dev_canonical_outputs(tmp_path: Path) -> None:
    from scripts.v2.run_v21_r1_parser_reparse_ablation import main

    schema = _schema_file(tmp_path)
    raw = tmp_path / "raw_outputs.dev.jsonl"
    write_jsonl(
        raw,
        [
            {
                "doc_id": "doc-1",
                "candidate_id": "doc-1:getm:0",
                "candidate_index": 0,
                "raw_output": (
                    '{"events":[{"event_type":"EventA",'
                    '"arguments":{"UnknownRole":["bad"],"Role1":["valid"]}}]}'
                ),
            }
        ],
    )
    out_dir = tmp_path / "out"

    assert (
        main(
            [
                "--dataset",
                "DuEE-Fin-dev500",
                "--split",
                "dev",
                "--raw-output",
                str(raw),
                "--schema",
                str(schema),
                "--mode",
                "drop_invalid_role_only",
                "--out-dir",
                str(out_dir),
            ]
        )
        == 0
    )

    manifest = json.loads((out_dir / "run_manifest.json").read_text(encoding="utf-8"))
    assert manifest["qwen_run"] is False
    assert manifest["train_run"] is False
    assert manifest["test_run"] is False
    assert manifest["test_gold_read"] is False
    assert manifest["split"] == "dev"
    assert manifest["mode"] == "drop_invalid_role_only"

    rows = read_jsonl(out_dir / "predictions" / "DuEE-Fin-dev500" / "dev.canonical.pred.jsonl")
    assert rows == [
        {
            "doc_id": "doc-1",
            "events": [{"event_type": "EventA", "arguments": {"Role1": [{"text": "valid"}]}}],
        }
    ]
    diagnostics = json.loads((out_dir / "parse_diagnostics.dev.json").read_text(encoding="utf-8"))
    assert diagnostics["diagnostic_counts"]["dropped_role_count"] == 1
    assert diagnostics["diagnostic_counts"]["dropped_event_count"] == 0


def test_aggregator_does_not_classify_without_evaluator_metrics(tmp_path: Path) -> None:
    from scripts.v2.aggregate_v21_r1_parser_reparse_ablation import aggregate

    summary = aggregate(tmp_path / "run-root", dataset="DuEE-Fin-dev500", split="dev")

    assert summary["decision"]["parser_strictness"] == "evaluator_metrics_missing"


def test_aggregator_prefers_latest_nested_evaluator_artifact(tmp_path: Path) -> None:
    from scripts.v2.aggregate_v21_r1_parser_reparse_ablation import aggregate

    mode_root = tmp_path / "run-root" / "frozen_strict"
    _write_evaluator_artifact(mode_root / "evaluator_artifacts" / "r1_20260507T040000Z", f1=0.0)
    _write_evaluator_artifact(mode_root / "evaluator_artifacts" / "r1_20260507T050000Z", f1=0.5)

    summary = aggregate(tmp_path / "run-root", dataset="DuEE-Fin-dev500", split="dev")
    frozen = next(row for row in summary["modes"] if row["mode"] == "frozen_strict")

    assert frozen["event_table_micro_f1"] == 0.5
    assert frozen["evaluator_artifact_root"].endswith("r1_20260507T050000Z")


def _write_evaluator_artifact(root: Path, *, f1: float) -> None:
    overall = root / "metrics" / "unified_main" / "DuEE-Fin-dev500" / "dev" / "overall_metrics.json"
    record = root / "analysis" / "DuEE-Fin-dev500" / "dev" / "record_level_metrics.json"
    validation = root / "analysis" / "DuEE-Fin-dev500" / "dev" / "validation_report.json"
    overall.parent.mkdir(parents=True, exist_ok=True)
    record.parent.mkdir(parents=True, exist_ok=True)
    validation.parent.mkdir(parents=True, exist_ok=True)
    overall.write_text(json.dumps({"f1": f1}, ensure_ascii=False), encoding="utf-8")
    record.write_text(json.dumps({"record_f1_exact": f1 / 10}, ensure_ascii=False), encoding="utf-8")
    validation.write_text(json.dumps({"ok": True}, ensure_ascii=False), encoding="utf-8")
