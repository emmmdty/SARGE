from __future__ import annotations

from evaluator.canonical.schema import EventSchema
from evaluator.canonical.types import CanonicalDocument, CanonicalEventRecord
from evaluator.role_f1.metric import evaluate_role_f1


SCHEMA = EventSchema.from_mapping({"Event": ["role_a", "role_b"]})


def _record(*, a: str | None = None, b: str | None = None) -> CanonicalEventRecord:
    arguments: dict[str, list[str]] = {}
    if a is not None:
        arguments["role_a"] = [a]
    if b is not None:
        arguments["role_b"] = [b]
    return CanonicalEventRecord(document_id="doc-1", event_type="Event", arguments=arguments)


def _score(
    gold_records: list[CanonicalEventRecord],
    pred_records: list[CanonicalEventRecord],
) -> dict:
    return evaluate_role_f1(
        [CanonicalDocument("doc-1", gold_records)],
        [CanonicalDocument("doc-1", pred_records)],
        dataset="Toy",
        schema=SCHEMA,
    )


def test_exact_record_is_order_insensitive() -> None:
    gold = [_record(a="a1", b="b1"), _record(a="a2", b="b2")]
    pred = [_record(a="a2", b="b2"), _record(a="a1", b="b1")]

    report = _score(gold, pred)

    assert report["overall"]["f1"] == 1.0
    assert report["record_metrics"]["exact_record"] == {
        "precision": 1.0,
        "recall": 1.0,
        "f1": 1.0,
    }
    assert report["record_metrics"]["delta_record"] == 0.0


def test_exact_record_exposes_cross_record_binding_error() -> None:
    gold = [_record(a="a1", b="b1"), _record(a="a2", b="b2")]
    pred = [_record(a="a1", b="b2"), _record(a="a2", b="b1")]

    report = _score(gold, pred)

    assert report["overall"]["f1"] == 0.5
    assert report["record_metrics"]["exact_record"]["f1"] == 0.0
    assert report["record_metrics"]["delta_record"] == 0.5
    assert report["diagnostics"]["exact_record_match_count"] == 0
    assert report["diagnostics"]["gold_record_count"] == 2
    assert report["diagnostics"]["pred_record_count"] == 2


def test_exact_record_counts_missing_and_extra_records() -> None:
    gold = [_record(a="a1", b="b1"), _record(a="a2", b="b2")]
    pred = [_record(a="a1", b="b1"), _record(a="extra", b="extra")]

    report = _score(gold, pred)

    assert report["record_metrics"]["exact_record"] == {
        "precision": 0.5,
        "recall": 0.5,
        "f1": 0.5,
    }
    assert report["diagnostics"]["exact_record_match_count"] == 1


def test_partial_record_is_not_an_exact_match() -> None:
    report = _score([_record(a="a1", b="b1")], [_record(a="a1")])

    assert report["overall"]["precision"] == 1.0
    assert report["overall"]["recall"] == 0.5
    assert report["record_metrics"]["exact_record"]["f1"] == 0.0
    assert report["record_metrics"]["delta_record"] == report["overall"]["f1"]
