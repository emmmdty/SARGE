from __future__ import annotations

import json
from pathlib import Path

import pytest

from sage_dee.v2.diagnostics.time_eta import TimingTracker


def test_timing_tracker_writes_events_summary_and_eta(tmp_path: Path) -> None:
    ticks = iter([100.0, 102.0, 106.0, 109.0])
    tracker = TimingTracker(total_items=3, moving_window_size=2, clock=lambda: next(ticks))

    tracker.record_item(item_id="doc-1", item_type="doc")
    tracker.record_item(item_id="doc-2", item_type="doc")
    summary = tracker.finish(tmp_path)

    assert (tmp_path / "timing_events.jsonl").is_file()
    assert (tmp_path / "timing_summary.json").is_file()
    assert summary["total_items"] == 3
    assert summary["completed_items"] == 2
    assert summary["avg_sec_per_item"] == pytest.approx(3.0)
    assert summary["moving_avg_sec_per_item"] == pytest.approx(3.0)
    assert summary["estimated_total_sec"] == pytest.approx(9.0)
    assert summary["eta_sec"] == pytest.approx(3.0)

    events = [json.loads(line) for line in (tmp_path / "timing_events.jsonl").read_text(encoding="utf-8").splitlines()]
    assert [event["item_id"] for event in events] == ["doc-1", "doc-2"]
    assert events[0]["duration_sec"] == pytest.approx(2.0)


def test_timing_tracker_handles_no_items_without_crashing(tmp_path: Path) -> None:
    ticks = iter([10.0, 11.0])
    tracker = TimingTracker(total_items=0, clock=lambda: next(ticks))

    summary = tracker.finish(tmp_path)

    assert summary["total_items"] == 0
    assert summary["completed_items"] == 0
    assert summary["avg_sec_per_item"] is None
    assert summary["moving_avg_sec_per_item"] is None
    assert summary["eta_sec"] is None
