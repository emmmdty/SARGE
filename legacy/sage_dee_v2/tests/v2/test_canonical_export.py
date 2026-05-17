from __future__ import annotations

import json
from pathlib import Path

import pytest

from sage_dee.v2.data_interface.jsonl import read_jsonl
from sage_dee.v2.data_interface.schema_registry import DatasetSchema
from sage_dee.v2.pipeline.export_canonical import (
    export_predictions,
    strip_auxiliary_fields,
    validate_minimal_canonical_prediction,
)


def _schema() -> DatasetSchema:
    return DatasetSchema(
        dataset_id="unit",
        schema_dataset="unit-source",
        schema_path=Path("schema.json"),
        canonical_version=None,
        event_roles={"EquityPledge": ("Pledger",)},
        role_to_event_types={"Pledger": ("EquityPledge",)},
    )


def test_strip_auxiliary_fields_keeps_only_minimal_canonical_prediction() -> None:
    candidate_doc = {
        "doc_id": "doc-1",
        "dataset": "ChFinAnn",
        "split": "dev",
        "content": "张三质押股份。",
        "source_candidate_id": "cand-1",
        "gold": {"events": []},
        "events": [
            {
                "event_type": "EquityPledge",
                "slot_id": 0,
                "evidence_chunk_id": "chunk-1",
                "alignment_score": 0.91,
                "logprob": -0.5,
                "reward": 0.8,
                "arguments": {
                    "Pledger": [
                        {
                            "text": "张三",
                            "norm_text": "张三",
                            "source_candidate_id": "surface-1",
                            "alignment_score": 0.91,
                            "gold": True,
                        }
                    ]
                },
            }
        ],
    }

    stripped = strip_auxiliary_fields(candidate_doc)

    assert stripped == {
        "doc_id": "doc-1",
        "events": [
            {
                "event_type": "EquityPledge",
                "arguments": {"Pledger": [{"text": "张三"}]},
            }
        ],
    }


def test_gold_and_auxiliary_fields_do_not_reach_exported_predictions(tmp_path: Path) -> None:
    output_path = tmp_path / "predictions.jsonl"
    pred_docs = [
        {
            "doc_id": "doc-1",
            "gold": {"events": [{"event_type": "EquityPledge"}]},
            "events": [
                {
                    "event_type": "EquityPledge",
                    "reward": 1.0,
                    "arguments": {
                        "Pledger": [{"text": "张三", "norm_text": "张三", "gold": True}],
                    },
                }
            ],
        }
    ]

    export_predictions(pred_docs, output_path)

    rows = read_jsonl(output_path)
    assert rows == [
        {
            "doc_id": "doc-1",
            "events": [
                {
                    "event_type": "EquityPledge",
                    "arguments": {"Pledger": [{"text": "张三"}]},
                }
            ],
        }
    ]
    serialized = json.dumps(rows, ensure_ascii=False)
    assert "gold" not in serialized
    assert "norm_text" not in serialized
    assert "reward" not in serialized


def test_canonical_forbidden_keys_zero(tmp_path: Path) -> None:
    output_path = tmp_path / "predictions.jsonl"
    export_predictions(
        [
            {
                "doc_id": "doc-1",
                "events": [
                    {
                        "event_type": "EquityPledge",
                        "slot_id": 0,
                        "arguments": {
                            "Pledger": [
                                {
                                    "text": "张三",
                                    "gold": True,
                                    "norm_text": "张三",
                                    "source_candidate_id": "cand-1",
                                }
                            ]
                        },
                    }
                ],
            }
        ],
        output_path,
        schema=_schema(),
    )

    rows = read_jsonl(output_path)
    serialized = json.dumps(rows, ensure_ascii=False)
    for forbidden in ("gold", "norm_text", "slot_id", "source_candidate_id"):
        assert forbidden not in serialized
    validate_minimal_canonical_prediction(rows[0], schema=_schema())


def test_canonical_rejects_unknown_schema_role() -> None:
    pred_doc = {
        "doc_id": "doc-1",
        "events": [
            {
                "event_type": "EquityPledge",
                "arguments": {"role": [{"text": "张三"}]},
            }
        ],
    }

    with pytest.raises(ValueError, match="Unknown role"):
        validate_minimal_canonical_prediction(pred_doc, schema=_schema())


@pytest.mark.parametrize(
    "pred_doc, message",
    [
        ({"events": []}, "doc_id"),
        ({"doc_id": "doc-1", "events": {}}, "events"),
        ({"doc_id": "doc-1", "events": [{"arguments": {}}]}, "event_type"),
        (
            {"doc_id": "doc-1", "events": [{"event_type": "x", "arguments": {"Role": [{"text": "a", "gold": True}]}}]},
            "Unexpected argument keys",
        ),
        (
            {"doc_id": "doc-1", "events": [{"event_type": "x", "arguments": {"Role": [{"text": ""}]}}]},
            "text",
        ),
    ],
)
def test_invalid_canonical_prediction_fails(pred_doc: dict, message: str) -> None:
    with pytest.raises(ValueError, match=message):
        validate_minimal_canonical_prediction(pred_doc)


def test_export_predictions_rejects_invalid_prediction(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="doc_id"):
        export_predictions([{"events": []}], tmp_path / "predictions.jsonl")
