from __future__ import annotations

import json
from pathlib import Path

from evaluator.cli import main


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False) + "\n", encoding="utf-8")


def test_role_f1_cli_writes_role_and_record_metrics(tmp_path: Path) -> None:
    schema = tmp_path / "schema.json"
    gold = tmp_path / "gold.jsonl"
    pred = tmp_path / "pred.jsonl"
    output = tmp_path / "nested" / "role_f1.json"
    _write_json(schema, {"Event": ["role_a", "role_b"]})
    document = {
        "doc_id": "doc-1",
        "events": [
            {
                "event_type": "Event",
                "arguments": {"role_a": ["a1"], "role_b": ["b1"]},
            }
        ],
    }
    _write_json(gold, document)
    _write_json(pred, document)

    main(
        [
            "role-f1",
            "--dataset",
            "Toy",
            "--gold",
            str(gold),
            "--pred",
            str(pred),
            "--schema",
            str(schema),
            "--out",
            str(output),
        ]
    )

    report = json.loads(output.read_text(encoding="utf-8"))
    assert report["overall"]["f1"] == 1.0
    assert report["record_metrics"]["exact_record"]["f1"] == 1.0
