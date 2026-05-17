from __future__ import annotations

import json
from pathlib import Path

from sage_dee.v2.data_interface.jsonl import read_jsonl
from sage_dee.v2.pipeline.run_v2_smoke import run_v2_smoke


def test_v2_smoke_pipeline_writes_manifest_and_canonical_prediction(tmp_path: Path) -> None:
    data_root = _write_tiny_dataset(tmp_path)

    result = run_v2_smoke(
        dataset="TinySmoke",
        split="dev",
        data_root=data_root,
        out_root=tmp_path / "runs",
        run_id="tiny-smoke-run",
        data_repo_root=tmp_path / "data_repo",
        seed=7,
    )

    assert result.run_root == tmp_path / "runs" / "tiny-smoke-run"
    assert result.prediction_path.is_file()
    assert result.run_manifest_path.is_file()
    assert result.prediction_path == result.run_root / "predictions" / "TinySmoke" / "dev.canonical.pred.jsonl"

    rows = read_jsonl(result.prediction_path)
    assert rows == [
        {
            "doc_id": "dev-1",
            "events": [
                {
                    "event_type": "EventA",
                    "arguments": {"Role1": [{"text": "测试股份有限公司"}]},
                }
            ],
        }
    ]
    serialized = json.dumps(rows, ensure_ascii=False)
    for forbidden in ("gold", "norm_text", "slot_id", "source_candidate_id", "reward", "mrs_score"):
        assert forbidden not in serialized

    manifest = json.loads(result.run_manifest_path.read_text(encoding="utf-8"))
    required_fields = {
        "run_id",
        "method_name",
        "method_family",
        "dataset_version",
        "split_version",
        "evaluator_version",
        "prediction_format",
        "training_view",
        "gold_view",
        "seed",
        "git_commit",
        "command_train",
        "command_infer",
        "created_at",
        "use_csg",
        "use_lesp",
        "use_getm",
        "use_mrs",
        "backend",
        "notes",
    }
    assert required_fields <= set(manifest)
    assert manifest["run_id"] == "tiny-smoke-run"
    assert manifest["method_name"] == "SAGE-DEE-v2-smoke"
    assert manifest["method_family"] == "SAGE-DEE-v2"
    assert manifest["dataset_version"] == "TinySmoke"
    assert manifest["split_version"] == "dev"
    assert manifest["evaluator_version"] == "eval-artifacts-v1.1"
    assert manifest["prediction_format"] == "canonical-jsonl"
    assert manifest["training_view"] == "evaluator_gold/train"
    assert manifest["gold_view"] == "processed/views/evaluator_gold/TinySmoke"
    assert manifest["seed"] == 7
    assert manifest["use_csg"] is True
    assert manifest["use_lesp"] is True
    assert manifest["use_getm"] is True
    assert manifest["use_mrs"] is True
    assert manifest["backend"] == "mock"

    assert (result.run_root / "intermediate" / "surface_memory.jsonl").is_file()
    assert (result.run_root / "intermediate" / "slot_plan.jsonl").is_file()
    assert (result.run_root / "diagnostics" / "pipeline_summary.json").is_file()
    assert result.handoff_command


def _write_tiny_dataset(tmp_path: Path) -> Path:
    data_root = tmp_path / "data"
    dataset_root = data_root / "TinySmoke"
    dataset_root.mkdir(parents=True)
    _write_json(
        dataset_root / "schema.json",
        {
            "dataset": "TinySmoke",
            "canonical_version": "tiny-v1",
            "event_types": [{"event_type": "EventA", "roles": ["Role1", "Role2"]}],
        },
    )
    _write_jsonl(
        dataset_root / "train.jsonl",
        [
            {
                "doc_id": "train-1",
                "dataset": "TinySmoke",
                "split": "train",
                "content": "测试股份有限公司发布公告。",
                "events": [
                    {
                        "event_type": "EventA",
                        "arguments": {"Role1": [{"text": "测试股份有限公司"}]},
                    }
                ],
            }
        ],
    )
    _write_jsonl(
        dataset_root / "dev.jsonl",
        [
            {
                "doc_id": "dev-1",
                "dataset": "TinySmoke",
                "split": "dev",
                "content": "测试股份有限公司发布公告。",
                "events": [
                    {
                        "event_type": "EventA",
                        "arguments": {"Role1": [{"text": "测试股份有限公司"}]},
                    }
                ],
            }
        ],
    )
    return data_root


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows),
        encoding="utf-8",
    )
