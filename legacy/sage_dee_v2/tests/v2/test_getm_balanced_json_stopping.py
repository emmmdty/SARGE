from __future__ import annotations

from sage_dee.v2.getm.json_stopping import apply_balanced_json_stopping


def test_balanced_json_stop_truncates_after_complete_object() -> None:
    result = apply_balanced_json_stopping(
        '{"events": []} trailing text',
        enabled=True,
        stop_after_balanced_events_json=True,
    )

    assert result.stopped_output == '{"events": []}'
    assert result.stop_reason == "balanced_json_closed"
    assert result.balanced_stop_applied is True


def test_balanced_json_stop_reconstructs_events_prefix_array_value() -> None:
    result = apply_balanced_json_stopping(
        '[{"event_type":"EventA","arguments":{"Role1":["value"]}}]} trailing',
        enabled=True,
        stop_after_balanced_events_json=True,
        response_prefix='{"events":',
        response_prefix_used=True,
    )

    assert result.stopped_output == '[{"event_type":"EventA","arguments":{"Role1":["value"]}}]}'
    assert result.stop_reason == "balanced_json_closed"


def test_balanced_json_stop_reconstructs_events_array_prefix_continuation() -> None:
    result = apply_balanced_json_stopping(
        '{"event_type":"EventA","arguments":{"Role1":["value"]}}]} trailing',
        enabled=True,
        stop_after_balanced_events_json=True,
        response_prefix='{"events":[',
        response_prefix_used=True,
    )

    assert result.stopped_output == '{"event_type":"EventA","arguments":{"Role1":["value"]}}]}'
    assert result.stop_reason == "balanced_json_closed"


def test_balanced_json_stop_handles_empty_events_with_array_prefix() -> None:
    result = apply_balanced_json_stopping(
        "]} trailing",
        enabled=True,
        stop_after_balanced_events_json=True,
        response_prefix='{"events":[',
        response_prefix_used=True,
    )

    assert result.stopped_output == "]}"
    assert result.stop_reason == "balanced_json_closed"


def test_balanced_json_stop_ignores_braces_inside_quoted_strings() -> None:
    result = apply_balanced_json_stopping(
        '{"events":[{"event_type":"EventA","arguments":{"Role1":["value } ] {"]}}]} tail',
        enabled=True,
        stop_after_balanced_events_json=True,
    )

    assert result.stopped_output == '{"events":[{"event_type":"EventA","arguments":{"Role1":["value } ] {"]}}]}'
    assert result.stop_reason == "balanced_json_closed"


def test_balanced_json_stop_does_not_sanitize_candidate_line_continuation() -> None:
    raw_output = (
        '- id=doc-1:csg:abc | text={"event_type":"EventA","arguments":{"Role1":["x"]}} '
        "| chunk=chunk_0000 | context=body"
    )

    result = apply_balanced_json_stopping(
        raw_output,
        enabled=True,
        stop_after_balanced_events_json=True,
        response_prefix='{"events":[',
        response_prefix_used=True,
    )

    assert result.stopped_output == raw_output
    assert result.stop_reason == "no_stop"
    assert result.balanced_stop_applied is False


def test_balanced_json_stop_records_disabled_reason() -> None:
    result = apply_balanced_json_stopping(
        '{"events": []}',
        enabled=False,
        stop_after_balanced_events_json=True,
    )

    assert result.stop_reason == "disabled"
    assert result.stopped_output == '{"events": []}'
