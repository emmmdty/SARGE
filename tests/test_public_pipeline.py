from __future__ import annotations

import json
from pathlib import Path

from sarge.pipeline.infer import run_inference


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False) + "\n", encoding="utf-8")


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows),
        encoding="utf-8",
    )


def test_mock_pipeline_runs_without_gpu_or_model_weights(tmp_path: Path) -> None:
    dataset_root = tmp_path / "data" / "Toy"
    _write_json(
        dataset_root / "schema.json",
        {
            "dataset": "Toy",
            "event_types": [{"event_type": "Event", "roles": ["company"]}],
        },
    )
    _write_jsonl(
        dataset_root / "train.jsonl",
        [
            {
                "doc_id": "train-1",
                "content": "Alpha disclosed an event.",
                "events": [
                    {
                        "event_type": "Event",
                        "arguments": {"company": [{"text": "Alpha"}]},
                    }
                ],
            }
        ],
    )
    _write_jsonl(
        dataset_root / "test.jsonl",
        [{"doc_id": "test-1", "content": "Beta disclosed another event."}],
    )

    result = run_inference(
        dataset="Toy",
        split="test",
        data_root=tmp_path / "data",
        out_root=tmp_path / "runs",
        run_id="cpu-smoke",
        k=1,
    )

    assert result.prediction_path.is_file()
    rows = [
        json.loads(line)
        for line in result.prediction_path.read_text(encoding="utf-8").splitlines()
    ]
    assert rows == [
        {
            "doc_id": "test-1",
            "events": [{"event_type": "Event", "arguments": {}}],
        }
    ]
    summary = json.loads(
        (result.run_root / "diagnostics" / "pipeline_summary.json").read_text(
            encoding="utf-8"
        )
    )
    assert summary["backend"] == "MockGetmBackend"
    assert summary["model_performance_evidence"] is False
