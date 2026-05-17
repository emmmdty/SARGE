"""Behavior-alignment test between SARGE rule_planner and legacy event_planner_v21.

Loads both implementations and runs them on the same fixtures, asserting that
every diagnostic field and every output record matches byte-for-byte. This
is the structural W2 acceptance gate: SARGE post-processing must replicate
Sage-DEE v2 outputs exactly until LRD replaces it in W4+.

Imports legacy directly from ``legacy/sage_dee_v2/src/``; that subtree is a
read-only snapshot kept for reference and regression testing.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

import pytest

_LEGACY_SRC = Path(__file__).resolve().parent.parent / "legacy" / "sage_dee_v2" / "src"
if str(_LEGACY_SRC) not in sys.path:
    sys.path.insert(0, str(_LEGACY_SRC))

from sage_dee.v2.postprocess import event_planner_v21 as legacy  # noqa: E402

from sarge.postprocess import rule_planner as sarge_rule  # noqa: E402


@dataclass(frozen=True)
class _FakeSchema:
    """Schema stub that satisfies both legacy and SARGE validate_* calls."""

    dataset_id: str = "alignment_fixture"
    event_roles: dict[str, tuple[str, ...]] = None  # type: ignore[assignment]

    def __post_init__(self):
        if self.event_roles is None:
            object.__setattr__(
                self,
                "event_roles",
                {
                    "质押": ("质押方", "质押物", "质押股票/股份数量", "事件时间"),
                    "解除质押": ("质押方", "质押物", "质押股票/股份数量", "事件时间"),
                    "股东减持": ("减持方", "交易股票/股份数量", "交易金额", "每股交易价格"),
                    "中标": ("中标公司", "招标方", "中标标的", "中标金额"),
                    "亏损": ("公司名称", "财报周期", "净亏损"),
                    "其他事件": ("其他角色",),
                },
            )

    def validate_event_type(self, event_type: str) -> str:
        normalized = str(event_type).strip()
        if normalized not in self.event_roles:
            raise ValueError(f"unknown event_type: {normalized!r}")
        return normalized

    def validate_role(self, event_type: str, role: str) -> str:
        if role not in self.event_roles[event_type]:
            raise ValueError(f"unknown role {event_type}/{role!r}")
        return role


def _to_legacy(records, ctor):
    return [ctor(event_type=r.event_type, arguments=r.arguments) for r in records]


def _build(event_type, **roles_to_texts):
    return {
        "event_type": event_type,
        "arguments": {role: [{"text": v} for v in values] for role, values in roles_to_texts.items()},
    }


FIXTURE_CASES: list[tuple[str, list[dict]]] = [
    (
        "empty",
        [],
    ),
    (
        "pass_through_single_record",
        [_build("质押", 质押方=["甲公司"], 质押物=["A 股票"])],
    ),
    (
        "exact_duplicates_collapse",
        [
            _build("质押", 质押方=["甲"], 事件时间=["2024-01-01"]),
            _build("质押", 质押方=["甲"], 事件时间=["2024-01-01"]),
            _build("中标", 中标公司=["乙"]),
        ],
    ),
    (
        "empty_target_dropped",
        [
            _build("质押"),
            _build("中标", 中标公司=["丙"]),
        ],
    ),
    (
        "anchor_aligned_split",
        [
            {
                "event_type": "股东减持",
                "arguments": {
                    "减持方": [{"text": "甲"}, {"text": "乙"}],
                    "交易股票/股份数量": [{"text": "100"}, {"text": "200"}],
                    "每股交易价格": [{"text": "1.0"}],
                },
            },
        ],
    ),
    (
        "anchor_compatible_merge",
        [
            _build("质押", 质押方=["甲"], 质押物=["A 股票"]),
            _build("质押", 质押方=["甲"], 质押物=["A 股票"], 事件时间=["2024-01-01"]),
        ],
    ),
    (
        "near_dedup_superset_wins",
        [
            _build("中标", 中标公司=["甲"], 招标方=["乙"]),
            _build("中标", 中标公司=["甲"], 招标方=["乙"], 中标金额=["100"]),
        ],
    ),
    (
        "non_target_event_kept_untouched",
        [
            _build("其他事件", 其他角色=["x"]),
            _build("其他事件", 其他角色=["x"]),
        ],
    ),
    (
        "mixed_target_and_non_target",
        [
            _build("质押", 质押方=["甲"]),
            _build("其他事件", 其他角色=["y"]),
            _build("质押", 质押方=["甲"]),
        ],
    ),
]


def _canonicalize(record_dataclass) -> dict:
    """Convert either legacy or sarge EventRecord into a canonical dict for comparison."""
    return {"event_type": record_dataclass.event_type, "arguments": record_dataclass.arguments}


@pytest.fixture
def schema() -> _FakeSchema:
    return _FakeSchema()


@pytest.mark.parametrize("case_id,raw_records", FIXTURE_CASES)
@pytest.mark.parametrize("mode", ["pass_through", "dedup_only", "conservative_assembler_v1"])
def test_sarge_matches_legacy(case_id: str, raw_records: list[dict], mode: str, schema) -> None:
    """SARGE rule_planner output equals legacy event_planner_v21 output."""
    sarge_records = [sarge_rule.EventRecord.from_canonical(payload) for payload in raw_records]
    legacy_records = [legacy.EventRecord.from_canonical(payload) for payload in raw_records]

    sarge_planned, sarge_diag = sarge_rule.apply_planner(sarge_records, mode=mode, schema=schema)
    legacy_planned, legacy_diag = legacy.apply_planner(legacy_records, mode=mode, schema=schema)

    # Record equivalence
    assert len(sarge_planned) == len(legacy_planned), f"{case_id}/{mode}: record count differs"
    for s, l in zip(sarge_planned, legacy_planned):
        assert _canonicalize(s) == _canonicalize(l), f"{case_id}/{mode}: record content differs"

    # Diagnostic counters must agree on the observable fields
    assert sarge_diag.events_before == legacy_diag.events_before
    assert sarge_diag.events_after == legacy_diag.events_after
    assert sarge_diag.applied_count == legacy_diag.applied_count
    assert sarge_diag.merge_count == legacy_diag.merge_count
    assert sarge_diag.split_count == legacy_diag.split_count
    assert sarge_diag.dedup_count == legacy_diag.dedup_count
    assert sarge_diag.dropped_count == legacy_diag.dropped_count


def test_sarge_supported_modes_match_legacy() -> None:
    assert sarge_rule.SUPPORTED_MODES == legacy.SUPPORTED_MODES


def test_sarge_target_event_types_match_legacy() -> None:
    assert sarge_rule.TARGET_EVENT_TYPES == legacy.TARGET_EVENT_TYPES


def test_sarge_anchor_roles_match_legacy() -> None:
    assert sarge_rule.ANCHOR_ROLES_BY_EVENT_TYPE == legacy.ANCHOR_ROLES_BY_EVENT_TYPE
