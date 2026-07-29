"""Per-document inference latency summaries.

Computes p50/p95 latency, tokens/second, and length-bucketed statistics
from per-request timing records collected during inference.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Sequence


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------

@dataclass
class LatencyRecord:
    """Per-document timing record collected during inference."""
    doc_id: str
    dataset: str
    split: str
    prompt_chars: int
    generated_tokens: int
    latency_seconds: float

    def tokens_per_second(self) -> float:
        if self.latency_seconds <= 0 or self.generated_tokens <= 0:
            return 0.0
        return self.generated_tokens / self.latency_seconds


@dataclass
class LatencyBucket:
    """One length bucket of latency statistics."""
    label: str
    count: int
    records: list[LatencyRecord] = field(default_factory=list, repr=False, compare=False)

    @staticmethod
    def from_range_name(name: str) -> LatencyBucket:
        return LatencyBucket(label=name, count=0)

    @staticmethod
    def from_records(
        records: list[LatencyRecord],
        boundaries: Callable[[list[LatencyRecord]], tuple[float, float, float]],
    ) -> list[LatencyBucket]:
        if not records:
            return []
        lo, hi, _ = boundaries(records)
        short: list[LatencyRecord] = []
        medium: list[LatencyRecord] = []
        long: list[LatencyRecord] = []
        for rec in records:
            if rec.prompt_chars <= lo:
                short.append(rec)
            elif rec.prompt_chars <= hi:
                medium.append(rec)
            else:
                long.append(rec)
        return [
            LatencyBucket(label="short_P0_P33", count=len(short), records=short),
            LatencyBucket(label="medium_P33_P66", count=len(medium), records=medium),
            LatencyBucket(label="long_P66_P100", count=len(long), records=long),
        ]


@dataclass
class LatencySummary:
    dataset: str
    split: str
    document_count: int
    p50_latency_s: float | None = None
    p95_latency_s: float | None = None
    mean_latency_s: float | None = None
    tokens_per_second: float | None = None
    total_tokens: int = 0
    total_latency_s: float = 0.0
    length_buckets: list[LatencyBucket] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Percentile helpers
# ---------------------------------------------------------------------------

def _percentile(sorted_values: Sequence[float], pct: float) -> float:
    """Nearest-rank percentile (rounds down)."""
    if not sorted_values:
        return 0.0
    idx = int(pct * len(sorted_values) / 100.0)
    idx = max(0, min(idx, len(sorted_values) - 1))
    return sorted_values[idx]


# ---------------------------------------------------------------------------
# Default length-bucket boundaries
# ---------------------------------------------------------------------------

def BUCKET_BOUNDARIES_P33_P66(
    records: list[LatencyRecord],
) -> tuple[float, float, float]:
    """Return (P33, P66, inf) prompt-character boundaries from the data."""
    if not records:
        return (0.0, 0.0, float("inf"))
    chars = sorted(r.prompt_chars for r in records)
    lo = _percentile(chars, 100.0 / 3)   # P33
    hi = _percentile(chars, 200.0 / 3)   # P66
    return (float(lo), float(hi), float("inf"))


# ---------------------------------------------------------------------------
# Summary computation
# ---------------------------------------------------------------------------

def compute_latency_summary(
    records: list[LatencyRecord],
    *,
    dataset: str,
    split: str,
    boundaries: Callable[
        [list[LatencyRecord]], tuple[float, float, float]
    ] = BUCKET_BOUNDARIES_P33_P66,
) -> LatencySummary:
    # Clamp negative latencies
    sanitized = [
        rec if rec.latency_seconds >= 0 else LatencyRecord(
            doc_id=rec.doc_id,
            dataset=rec.dataset,
            split=rec.split,
            prompt_chars=rec.prompt_chars,
            generated_tokens=rec.generated_tokens,
            latency_seconds=0.0,
        )
        for rec in records
    ]
    lats = sorted(rec.latency_seconds for rec in sanitized)
    count = len(sanitized)
    total_tokens = sum(rec.generated_tokens for rec in sanitized)
    total_latency = sum(rec.latency_seconds for rec in sanitized)
    tps = total_tokens / total_latency if total_latency > 0 else 0.0

    return LatencySummary(
        dataset=dataset,
        split=split,
        document_count=count,
        p50_latency_s=_percentile(lats, 50) if lats else None,
        p95_latency_s=_percentile(lats, 95) if lats else None,
        mean_latency_s=total_latency / count if count else None,
        tokens_per_second=tps,
        total_tokens=total_tokens,
        total_latency_s=total_latency,
        length_buckets=LatencyBucket.from_records(sanitized, boundaries=boundaries),
    )


# ---------------------------------------------------------------------------
# JSON serialization
# ---------------------------------------------------------------------------

def _bucket_to_dict(bucket: LatencyBucket) -> dict:
    lats = sorted(r.latency_seconds for r in bucket.records)
    tokens = sum(r.generated_tokens for r in bucket.records)
    total_time = sum(r.latency_seconds for r in bucket.records)
    return {
        "label": bucket.label,
        "count": bucket.count,
        "p50_latency_s": _percentile(lats, 50) if lats else None,
        "p95_latency_s": _percentile(lats, 95) if lats else None,
        "mean_latency_s": sum(lats) / len(lats) if lats else None,
        "tokens_per_second": tokens / total_time if total_time > 0 else None,
    }


def write_latency_summary(summary: LatencySummary, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload: dict = {
        "dataset": summary.dataset,
        "split": summary.split,
        "document_count": summary.document_count,
        "p50_latency_s": summary.p50_latency_s,
        "p95_latency_s": summary.p95_latency_s,
        "mean_latency_s": summary.mean_latency_s,
        "tokens_per_second": summary.tokens_per_second,
        "total_tokens": summary.total_tokens,
        "total_latency_s": summary.total_latency_s,
        "length_buckets": [_bucket_to_dict(b) for b in summary.length_buckets],
    }
    with path.open("w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2, ensure_ascii=False)
        fh.write("\n")


def read_latency_summary(path: Path) -> LatencySummary:
    with path.open("r", encoding="utf-8") as fh:
        d = json.load(fh)
    buckets = []
    for bd in d.get("length_buckets", []):
        buckets.append(LatencyBucket(
            label=bd["label"],
            count=bd["count"],
            records=[],
        ))
    return LatencySummary(
        dataset=d["dataset"],
        split=d["split"],
        document_count=d["document_count"],
        p50_latency_s=d["p50_latency_s"],
        p95_latency_s=d["p95_latency_s"],
        mean_latency_s=d["mean_latency_s"],
        tokens_per_second=d["tokens_per_second"],
        total_tokens=d["total_tokens"],
        total_latency_s=d["total_latency_s"],
        length_buckets=buckets,
    )
