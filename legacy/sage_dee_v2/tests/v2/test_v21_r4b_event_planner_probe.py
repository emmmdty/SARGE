from __future__ import annotations

import json
import subprocess
from copy import deepcopy
from pathlib import Path

from sage_dee.v2.data_interface.jsonl import read_jsonl, write_jsonl
from sage_dee.v2.data_interface.schema_registry import DatasetSchema
from sage_dee.v2.postprocess.event_planner_v21 import (
    EventRecord,
    apply_planner,
    normalize_record_signature,
)


def test_runner_rejects_test_split(tmp_path: Path) -> None:
    from scripts.v2.run_v21_r4b_event_planner_probe import main

    config = _write_config(tmp_path)

    assert (
        main(
            [
                "--config",
                str(config),
                "--dataset",
                "DuEE-Fin-dev500",
                "--split",
                "test",
                "--source-prediction",
                str(tmp_path / "source.jsonl"),
                "--out-root",
                str(tmp_path / "out"),
            ]
        )
        == 2
    )


def test_non_oracle_planner_rejects_gold_input(tmp_path: Path) -> None:
    from scripts.v2.run_v21_r4b_event_planner_probe import main

    config = _write_config(tmp_path, extra={"non_oracle_gold_path": str(tmp_path / "gold.jsonl")})

    assert (
        main(
            [
                "--config",
                str(config),
                "--dataset",
                "DuEE-Fin-dev500",
                "--split",
                "dev",
                "--source-prediction",
                str(tmp_path / "source.jsonl"),
                "--out-root",
                str(tmp_path / "out"),
            ]
        )
        == 2
    )


def test_pass_through_produces_unchanged_records() -> None:
    schema = _schema()
    records = [
        EventRecord(
            event_type="亏损",
            arguments={"公司名称": [{"text": "甲公司"}], "净亏损": [{"text": "1亿元"}]},
        ),
        EventRecord(event_type="股份回购", arguments={"回购方": [{"text": "乙公司"}]}),
    ]

    planned, diagnostics = apply_planner(records, mode="pass_through", schema=schema)

    assert [record.to_canonical() for record in planned] == [record.to_canonical() for record in records]
    assert diagnostics.events_before == 2
    assert diagnostics.events_after == 2
    assert diagnostics.applied_count == 0


def test_dedup_only_removes_exact_duplicates_only() -> None:
    schema = _schema()
    duplicated = EventRecord(
        event_type="中标",
        arguments={"中标公司": [{"text": "甲公司"}], "中标金额": [{"text": "100万元"}]},
    )
    similar = EventRecord(
        event_type="中标",
        arguments={"中标公司": [{"text": "甲公司"}], "中标金额": [{"text": "101万元"}]},
    )

    planned, diagnostics = apply_planner(
        [duplicated, deepcopy(duplicated), similar],
        mode="dedup_only",
        schema=schema,
    )

    assert len(planned) == 2
    assert normalize_record_signature(duplicated) in {normalize_record_signature(record) for record in planned}
    assert normalize_record_signature(similar) in {normalize_record_signature(record) for record in planned}
    assert diagnostics.dedup_count == 1
    assert diagnostics.merge_count == 0
    assert diagnostics.split_count == 0


def test_conservative_assembler_v1_does_not_hallucinate_roles_or_values() -> None:
    schema = _schema()
    records = [
        EventRecord(
            event_type="企业融资",
            arguments={"被投资方": [{"text": "甲公司"}], "融资金额": [{"text": "1亿元"}]},
        ),
        EventRecord(
            event_type="企业融资",
            arguments={"被投资方": [{"text": "甲公司"}], "融资轮次": [{"text": "A轮"}]},
        ),
    ]

    planned, diagnostics = apply_planner(records, mode="conservative_assembler_v1", schema=schema)

    observed_values = {
        value["text"]
        for record in planned
        for values in record.arguments.values()
        for value in values
    }
    observed_roles = {role for record in planned for role in record.arguments}

    assert observed_values <= {"甲公司", "1亿元", "A轮"}
    assert observed_roles <= set(schema.event_roles["企业融资"])
    assert diagnostics.merge_count == 1


def test_planner_never_creates_event_type_or_role_outside_schema() -> None:
    schema = _schema()
    records = [
        EventRecord(
            event_type="公司上市",
            arguments={"上市公司": [{"text": "甲公司"}], "证券代码": [{"text": "000001"}]},
        ),
        EventRecord(
            event_type="质押",
            arguments={"质押方": [{"text": "乙公司"}], "质押股票/股份数量": [{"text": "100万股"}]},
        ),
    ]

    planned, _diagnostics = apply_planner(records, mode="conservative_assembler_v1", schema=schema)

    for record in planned:
        assert record.event_type in schema.event_types
        assert set(record.arguments) <= set(schema.event_roles[record.event_type])


def test_runner_preserves_source_prediction_and_marks_oracle_non_performance(
    tmp_path: Path,
    monkeypatch,
) -> None:
    import scripts.v2.run_v21_r4b_event_planner_probe as runner

    schema = _schema()
    source = tmp_path / "source" / "dev.canonical.pred.jsonl"
    write_jsonl(
        source,
        [
            {
                "doc_id": "doc-1",
                "events": [
                    {"event_type": "中标", "arguments": {"中标公司": [{"text": "甲公司"}]}},
                    {"event_type": "中标", "arguments": {"中标公司": [{"text": "甲公司"}]}},
                ],
            }
        ],
    )
    before = source.read_text(encoding="utf-8")
    config = _write_config(tmp_path)

    monkeypatch.setattr(runner, "load_schema", lambda dataset, data_root="data": schema)
    monkeypatch.setattr(runner, "load_documents", lambda *args, **kwargs: [])
    monkeypatch.setattr(
        runner,
        "_run_evaluator",
        lambda variant_dir, *, args, config, variant: {
            "attempted": False,
            "returncode": None,
            "evaluator_artifact_root": None,
            "evaluator_validation_ok": None,
            "event_table_micro_f1": None,
            "role_level_f1": None,
            "exact_record_f1": None,
        },
    )

    assert (
        runner.main(
            [
                "--config",
                str(config),
                "--dataset",
                "DuEE-Fin-dev500",
                "--split",
                "dev",
                "--source-prediction",
                str(source),
                "--out-root",
                str(tmp_path / "out"),
            ]
        )
        == 0
    )

    assert source.read_text(encoding="utf-8") == before
    manifest = json.loads((tmp_path / "out" / "run_manifest.json").read_text(encoding="utf-8"))
    assert manifest["scope"]["test_run"] is False
    assert manifest["scope"]["qwen_run"] is False
    assert manifest["scope"]["train_run"] is False
    assert manifest["scope"]["gold_in_non_oracle_planner"] is False
    assert manifest["oracle_diagnostics"]["label"] == "dev_only_non_performance"
    dedup_rows = read_jsonl(
        tmp_path / "out" / "dedup_only" / "predictions" / "DuEE-Fin-dev500" / "dev.canonical.pred.jsonl"
    )
    assert len(dedup_rows[0]["events"]) == 1


def test_aggregator_emits_verdict(tmp_path: Path) -> None:
    from scripts.v2.aggregate_v21_r4b_event_planner_probe import aggregate_r4b

    run_root = tmp_path / "r4b"
    _write_variant_summary(
        run_root,
        "pass_through",
        exact=0.35,
        role=0.73,
        event_count_acc=0.68,
        canonical_events=3,
        changed_docs=0,
        decisions=0,
    )
    _write_variant_summary(
        run_root,
        "dedup_only",
        exact=0.37,
        role=0.729,
        event_count_acc=0.69,
        canonical_events=2,
        changed_docs=1,
        decisions=1,
    )
    _write_json(
        run_root / "run_manifest.json",
        {"variants": ["pass_through", "dedup_only"], "scope": {"dev_only": True}},
    )

    summary = aggregate_r4b(run_root)

    assert summary["machine_readable_verdict"]["best_non_oracle_variant"] == "dedup_only"
    assert summary["machine_readable_verdict"]["exact_record_delta"] == 0.02
    assert summary["machine_readable_verdict"]["event_planner_promising"] is True
    assert summary["machine_readable_verdict"]["recommended_next_phase"] == "R4c_planner_refine_dev_only"


def test_frozen_final_result_file_is_not_modified() -> None:
    final_result = Path("docs/refactor/SAGE_V2_FINAL_TEST_RESULT.json")
    assert final_result.is_file()
    completed = subprocess.run(
        ["git", "diff", "--quiet", "--", str(final_result)],
        check=False,
    )
    assert completed.returncode == 0


def _schema() -> DatasetSchema:
    event_roles = {
        "中标": ("中标公司", "中标日期", "中标标的", "中标金额", "披露日期", "招标方"),
        "亏损": ("亏损变化", "公司名称", "净亏损", "披露时间", "财报周期"),
        "企业融资": ("事件时间", "投资方", "披露时间", "融资轮次", "融资金额", "被投资方", "领投方"),
        "企业收购": ("交易金额", "披露时间", "收购完成时间", "收购方", "收购标的", "被收购方"),
        "公司上市": ("上市公司", "事件时间", "募资金额", "发行价格", "市值", "披露时间", "环节", "证券代码"),
        "股东减持": (
            "交易完成时间",
            "交易股票/股份数量",
            "交易金额",
            "减持方",
            "减持部分占总股本比例",
            "减持部分占所持比例",
            "披露时间",
            "每股交易价格",
            "股票简称",
        ),
        "被约谈": ("公司名称", "披露时间", "约谈机构", "被约谈时间"),
        "解除质押": (
            "事件时间",
            "披露时间",
            "质押方",
            "质押物",
            "质押物占总股比",
            "质押物占持股比",
            "质押物所属公司",
            "质押股票/股份数量",
            "质权方",
        ),
        "质押": (
            "事件时间",
            "披露时间",
            "质押方",
            "质押物",
            "质押物占总股比",
            "质押物占持股比",
            "质押物所属公司",
            "质押股票/股份数量",
            "质权方",
        ),
        "高管变动": (
            "事件时间",
            "任职公司",
            "变动后公司名称",
            "变动后职位",
            "变动类型",
            "披露日期",
            "高管姓名",
            "高管职位",
        ),
        "股份回购": ("交易金额", "回购方"),
    }
    role_to_event_types: dict[str, list[str]] = {}
    for event_type, roles in event_roles.items():
        for role in roles:
            role_to_event_types.setdefault(role, []).append(event_type)
    return DatasetSchema(
        dataset_id="DuEE-Fin-dev500",
        schema_dataset="DuEE-Fin-dev500",
        schema_path=Path("schema.json"),
        canonical_version=None,
        event_roles=event_roles,
        role_to_event_types={role: tuple(types) for role, types in role_to_event_types.items()},
    )


def _write_config(
    tmp_path: Path,
    *,
    variants: list[str] | None = None,
    extra: dict[str, object] | None = None,
) -> Path:
    config = {
        "dataset": "DuEE-Fin-dev500",
        "split": "dev",
        "source_row": "s4_full_or_max_frozen_surface",
        "source_prediction_path": str(tmp_path / "source.jsonl"),
        "variants": variants or ["pass_through", "dedup_only", "conservative_assembler_v1"],
        "target_event_types": [
            "亏损",
            "高管变动",
            "质押",
            "股东减持",
            "中标",
            "解除质押",
            "企业收购",
            "企业融资",
            "被约谈",
            "公司上市",
        ],
        "allow_test": False,
        "allow_gold_in_non_oracle_planner": False,
        "evaluator_root": "/home/TJK/DEE/dee-eval",
        "benchmark_root": "/data/TJK/DEE/data/processed",
        "out_root": str(tmp_path / "out"),
    }
    if extra:
        config.update(extra)
    path = tmp_path / "config.yaml"
    path.write_text("\n".join(_yaml_lines(config)) + "\n", encoding="utf-8")
    return path


def _yaml_lines(payload: dict[str, object]) -> list[str]:
    lines: list[str] = []
    for key, value in payload.items():
        if isinstance(value, list):
            lines.append(f"{key}:")
            for item in value:
                lines.append(f"  - {item}")
        elif isinstance(value, bool):
            lines.append(f"{key}: {str(value).lower()}")
        else:
            lines.append(f"{key}: {value}")
    return lines


def _write_variant_summary(
    run_root: Path,
    variant: str,
    *,
    exact: float,
    role: float,
    event_count_acc: float,
    canonical_events: int,
    changed_docs: int,
    decisions: int,
) -> None:
    _write_json(
        run_root / variant / "variant_summary.json",
        {
            "variant": variant,
            "canonical_event_count": canonical_events,
            "changed_doc_count": changed_docs,
            "planner_diagnostics": {"applied_count": decisions},
            "evaluator": {
                "event_table_micro_f1": role,
                "role_level_f1": role,
                "exact_record_f1": exact,
                "event_count_acc": event_count_acc,
                "merge_count": 1,
                "split_count": 2,
                "wrong_grouping_count": 3,
            },
        },
    )


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
