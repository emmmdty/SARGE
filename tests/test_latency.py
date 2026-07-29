from __future__ import annotations

from pathlib import Path

import pytest

from sarge.pipeline.latency import (
    LatencyRecord,
    compute_latency_summary,
    read_latency_summary,
    write_latency_summary,
)


def _record(doc_id: str, prompt_chars: int, tokens: int, seconds: float) -> LatencyRecord:
    return LatencyRecord(
        doc_id=doc_id,
        dataset="Toy",
        split="test",
        prompt_chars=prompt_chars,
        generated_tokens=tokens,
        latency_seconds=seconds,
    )


def test_latency_summary_reports_percentiles_throughput_and_buckets() -> None:
    records = [
        _record(f"doc-{index}", 1000 * index, 100, 0.1 * index)
        for index in range(1, 10)
    ]

    summary = compute_latency_summary(records, dataset="Toy", split="test")

    assert summary.document_count == 9
    assert summary.p50_latency_s == pytest.approx(0.5)
    assert summary.p95_latency_s == pytest.approx(0.9)
    assert summary.tokens_per_second == pytest.approx(200.0)
    assert sum(bucket.count for bucket in summary.length_buckets) == 9


def test_latency_summary_round_trip(tmp_path: Path) -> None:
    path = tmp_path / "diagnostics" / "latency_summary.json"
    expected = compute_latency_summary(
        [_record("doc-1", 1000, 100, 0.5)],
        dataset="Toy",
        split="test",
    )

    write_latency_summary(expected, path)
    actual = read_latency_summary(path)

    assert actual == expected
