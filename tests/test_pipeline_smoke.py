"""End-to-end pipeline smoke test.

Stages 3 DuEE-Fin-dev500 documents from the copied data snapshot into
SARGE canonical layout,
runs the full inference pipeline with the mock GETM backend, and asserts
that the canonical prediction file is well-formed (doc_id, events,
event_type, arguments, role, text). No GPU / no Qwen weights / no network.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from sarge.data.canonical import (
    CANONICAL_ARGUMENT_KEYS,
    CANONICAL_DOCUMENT_KEYS,
    CANONICAL_EVENT_RECORD_KEYS,
)
from sarge.data.staging import stage_dataset
from sarge.pipeline.infer import InferenceResult, run_inference

PROCESSED_ROOT = Path(__file__).resolve().parent.parent / "data"


@pytest.fixture
def staging_dir(tmp_path: Path) -> Path:
    return tmp_path / "staging"


@pytest.fixture
def out_root(tmp_path: Path) -> Path:
    return tmp_path / "runs"


def _stage_duee_fin(staging: Path, *, train_limit: int = 30, dev_limit: int = 3) -> None:
    stage_dataset(
        dataset="DuEE-Fin-dev500",
        processed_root=PROCESSED_ROOT,
        output_root=staging,
        splits=("train",),
        limit=train_limit,
    )
    stage_dataset(
        dataset="DuEE-Fin-dev500",
        processed_root=PROCESSED_ROOT,
        output_root=staging,
        splits=("dev",),
        limit=dev_limit,
    )


@pytest.mark.skipif(
    not (PROCESSED_ROOT / "DuEE-Fin-dev500" / "dev.jsonl").is_file(),
    reason="data/DuEE-Fin-dev500/dev.jsonl not present",
)
def test_pipeline_runs_end_to_end_with_mock_backend(staging_dir: Path, out_root: Path) -> None:
    _stage_duee_fin(staging_dir, train_limit=30, dev_limit=3)
    result: InferenceResult = run_inference(
        dataset="DuEE-Fin-dev500",
        split="dev",
        data_root=staging_dir,
        out_root=out_root,
        limit=3,
        seed=13,
        k=4,
    )

    assert result.prediction_path.is_file(), "canonical prediction file missing"
    rows = [json.loads(line) for line in result.prediction_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert len(rows) == 3, f"expected 3 prediction rows, got {len(rows)}"

    # Every prediction conforms to the frozen canonical schema.
    for row in rows:
        assert set(row.keys()) <= CANONICAL_DOCUMENT_KEYS | {"doc_id", "events"}
        assert "doc_id" in row and isinstance(row["doc_id"], str)
        assert "events" in row and isinstance(row["events"], list)
        for event in row["events"]:
            assert set(event.keys()) <= CANONICAL_EVENT_RECORD_KEYS
            assert isinstance(event["event_type"], str)
            assert isinstance(event["arguments"], dict)
            for role, values in event["arguments"].items():
                assert isinstance(role, str)
                assert isinstance(values, list)
                for value in values:
                    assert set(value.keys()) <= CANONICAL_ARGUMENT_KEYS
                    assert isinstance(value["text"], str)


@pytest.mark.skipif(
    not (PROCESSED_ROOT / "DuEE-Fin-dev500" / "dev.jsonl").is_file(),
    reason="data/DuEE-Fin-dev500/dev.jsonl not present",
)
def test_staging_writes_expected_schema_shape(staging_dir: Path) -> None:
    _stage_duee_fin(staging_dir, train_limit=10, dev_limit=3)
    schema_path = staging_dir / "DuEE-Fin-dev500" / "schema.json"
    assert schema_path.is_file()
    payload = json.loads(schema_path.read_text(encoding="utf-8"))
    assert payload["dataset"] == "DuEE-Fin-dev500"
    assert isinstance(payload["event_types"], list)
    assert all("event_type" in entry and "roles" in entry for entry in payload["event_types"])
