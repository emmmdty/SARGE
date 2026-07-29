from __future__ import annotations

import importlib.util
import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def _load_prepare_module():
    spec = importlib.util.spec_from_file_location(
        "prepare_public_data",
        REPO_ROOT / "scripts" / "prepare_public_data.py",
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_duee_dev_split_is_deterministic() -> None:
    module = _load_prepare_module()
    rows = [
        {
            "id": f"doc-{index}",
            "text": f"Document {index}",
            "event_list": [{"event_type": "EventA" if index % 2 else "EventB"}],
        }
        for index in range(20)
    ]

    first = module._split_duee_train(rows, dev_size=5, seed=42)
    second = module._split_duee_train(list(reversed(rows)), dev_size=5, seed=42)

    assert {row["id"] for row in first[1]} == {row["id"] for row in second[1]}
    assert len(first[0]) == 15
    assert len(first[1]) == 5


def test_committed_manifests_contain_aggregate_metadata_only() -> None:
    forbidden_fragments = (
        "/home/",
        "file://",
        '"doc_id"',
        '"row_hash"',
        '"output_hash"',
        '"raw_text"',
    )
    manifests = sorted((REPO_ROOT / "data").glob("*/split_manifest.json"))
    assert manifests
    for path in manifests:
        payload = json.loads(path.read_text(encoding="utf-8"))
        text = json.dumps(payload, ensure_ascii=False)
        assert not any(fragment in text for fragment in forbidden_fragments)
