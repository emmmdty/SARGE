from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.v2.smoke_all_v2 import run_final_smoke


def test_run_final_smoke_writes_summary_and_canonical_outputs(tmp_path: Path) -> None:
    data_root = _write_tiny_dataset(tmp_path)
    out_root = tmp_path / "final-smoke"

    summary = run_final_smoke(
        out_root=out_root,
        dataset="TinySmoke",
        split="dev",
        data_root=data_root,
        limit=1,
        train_limit=1,
        k=2,
        data_interface_datasets=("TinySmoke",),
        data_repo_root=tmp_path / "data_repo",
    )

    assert summary["status"] == "ok"
    assert summary["qwen_real_run_started"] is False
    assert summary["evaluator_handoff_ran"] is False
    assert summary["steps"]["data_interface"]["datasets"]["TinySmoke"]["splits"]["test"]["gold_visible"] is False
    assert summary["steps"]["csg_train_mode"]["gold_visible"] is True
    assert summary["steps"]["csg_test_predict_mode"]["gold_visible"] is False
    assert summary["steps"]["canonical_validation"]["validated_file_count"] >= 3
    assert "build_eval_artifacts.py" in summary["steps"]["evaluator_handoff"]["command"]

    summary_path = out_root / "summary.json"
    assert summary_path.is_file()
    persisted = json.loads(summary_path.read_text(encoding="utf-8"))
    assert persisted["status"] == "ok"

    canonical_paths = [
        Path(path)
        for path in summary["steps"]["canonical_validation"]["validated_files"]
        if path.endswith(".canonical.pred.jsonl")
    ]
    assert canonical_paths
    serialized = "\n".join(path.read_text(encoding="utf-8") for path in canonical_paths)
    for forbidden in ("gold", "norm_text", "slot_id", "source_candidate_id", "reward", "mrs_score"):
        assert forbidden not in serialized


def test_validate_canonical_outputs_rejects_auxiliary_fields(tmp_path: Path) -> None:
    from scripts.v2.smoke_all_v2 import validate_canonical_outputs

    bad_path = tmp_path / "bad.canonical.pred.jsonl"
    bad_path.write_text(
        json.dumps(
            {
                "doc_id": "doc-1",
                "events": [
                    {
                        "event_type": "EventA",
                        "arguments": {"Role1": [{"text": "Acme", "source_candidate_id": "c1"}]},
                    }
                ],
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="forbidden canonical field"):
        validate_canonical_outputs(tmp_path)


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
    for split, doc_id in (("train", "train-1"), ("dev", "dev-1"), ("test", "test-1")):
        _write_jsonl(
            dataset_root / f"{split}.jsonl",
            [
                {
                    "doc_id": doc_id,
                    "dataset": "TinySmoke",
                    "split": split,
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
