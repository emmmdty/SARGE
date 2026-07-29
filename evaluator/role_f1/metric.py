from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import Any

from evaluator.canonical.grouping import (
    all_document_ids,
    empty_subset_counts,
    gold_subset_for_document,
    group_by_event_type,
    merge_documents,
)
from evaluator.canonical.normalize import normalize_optional_text
from evaluator.canonical.report import add_diagnostics, build_report
from evaluator.canonical.schema import EventSchema
from evaluator.canonical.stats import Counts
from evaluator.canonical.types import CanonicalDocument, CanonicalEventRecord
from evaluator.canonical.validate import validate_documents


@dataclass(frozen=True)
class FixedSlotRecord:
    slots: tuple[str | None, ...]
    collapsed_multi_value_role_count: int


@dataclass(frozen=True)
class FixedSlotDocument:
    document_id: str
    gold_by_event: dict[str, tuple[FixedSlotRecord, ...]]
    pred_by_event: dict[str, tuple[FixedSlotRecord, ...]]


@dataclass
class ExactRecordCounts:
    matched: int = 0
    gold: int = 0
    pred: int = 0

    def add_group(
        self,
        fixed_pred: list[FixedSlotRecord],
        fixed_gold: list[FixedSlotRecord],
    ) -> None:
        pred_records = Counter(record.slots for record in fixed_pred)
        gold_records = Counter(record.slots for record in fixed_gold)
        self.matched += sum((pred_records & gold_records).values())
        self.pred += len(fixed_pred)
        self.gold += len(fixed_gold)

    def to_metrics(self) -> dict[str, float]:
        precision = self.matched / self.pred if self.pred else 0.0
        recall = self.matched / self.gold if self.gold else 0.0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        return {"precision": precision, "recall": recall, "f1": f1}


def evaluate_role_f1(
    gold_documents: list[CanonicalDocument],
    pred_documents: list[CanonicalDocument],
    *,
    dataset: str,
    schema: EventSchema | None = None,
    input_paths: dict[str, str | None] | None = None,
    schema_path: str | None = None,
    loader_diagnostics: dict[str, Any] | None = None,
) -> dict[str, Any]:
    diagnostics = add_diagnostics(
        loader_diagnostics,
        validate_documents(gold_documents, schema).to_report(),
        validate_documents(pred_documents, schema).to_report(),
    )
    native_diagnostics: dict[str, int] = {
        "fixed_slot_gold_unit_count": 0,
        "fixed_slot_pred_unit_count": 0,
        "collapsed_multi_value_role_count": 0,
        "schema_role_fallback_event_group_count": 0,
    }
    overall = Counts()
    exact_records = ExactRecordCounts()
    per_event: dict[str, Counts] = defaultdict(Counts)
    subset_counts = empty_subset_counts()

    gold_by_id = merge_documents(gold_documents)
    pred_by_id = merge_documents(pred_documents)
    for document_id in all_document_ids(gold_documents, pred_documents):
        gold_records = gold_by_id.get(document_id, [])
        pred_records = pred_by_id.get(document_id, [])
        document_counts = _score_document(
            gold_records,
            pred_records,
            per_event,
            schema,
            native_diagnostics,
            exact_records,
        )
        overall.add(document_counts)
        if gold_records:
            subset_counts[gold_subset_for_document(gold_records)].add(document_counts)

    diagnostics = add_diagnostics(
        diagnostics,
        native_diagnostics,
        {
            "exact_record_match_count": exact_records.matched,
            "gold_record_count": exact_records.gold,
            "pred_record_count": exact_records.pred,
        },
    )
    report = build_report(
        dataset=dataset,
        metric_family="role_f1_fixed_slot",
        overall=overall,
        per_event=per_event,
        subset_metrics=subset_counts,
        diagnostics=diagnostics,
        input_paths=input_paths,
        schema_path=schema_path,
        matching_policy={
            "name": "schema_ordered_fixed_slot_greedy",
            "unit": "fixed_schema_role_slot",
            "event_type_constrained": True,
            "prediction_order": "descending_non_empty_fixed_slot_count_stable",
            "objective": "per_prediction_max_role_slot_equality_including_none",
        },
        extra={
            "slot_policy": {
                "role_order": "schema_order_when_available_else_sorted_observed_roles",
                "missing_or_empty_value": "None",
                "multi_value_collapse": "last_normalized_non_empty_value_wins",
                "event_id_scored": False,
                "record_id_scored": False,
            },
        },
    )
    exact_record_metrics = exact_records.to_metrics()
    report["record_metrics"] = {
        "exact_record": exact_record_metrics,
        "delta_record": report["overall"]["f1"] - exact_record_metrics["f1"],
    }
    return report


def _score_document(
    gold_records: list[CanonicalEventRecord],
    pred_records: list[CanonicalEventRecord],
    per_event: dict[str, Counts],
    schema: EventSchema | None,
    diagnostics: dict[str, int],
    exact_records: ExactRecordCounts,
) -> Counts:
    document_counts = Counts()
    gold_by_event = group_by_event_type(gold_records)
    pred_by_event = group_by_event_type(pred_records)
    for event_name in sorted(set(gold_by_event) | set(pred_by_event)):
        pred_group = pred_by_event.get(event_name, [])
        gold_group = gold_by_event.get(event_name, [])
        role_order = _role_order_for_event(event_name, pred_group, gold_group, schema, diagnostics)
        exact_records.add_group(
            [_to_fixed_slot_record(record, role_order) for record in pred_group],
            [_to_fixed_slot_record(record, role_order) for record in gold_group],
        )
        event_counts = _score_event_group(
            pred_group,
            gold_group,
            role_order,
            diagnostics,
        )
        per_event[event_name].add(event_counts)
        document_counts.add(event_counts)
    return document_counts


def _score_event_group(
    pred_group: list[CanonicalEventRecord],
    gold_group: list[CanonicalEventRecord],
    role_order: tuple[str, ...],
    diagnostics: dict[str, int],
) -> Counts:
    fixed_pred = [_to_fixed_slot_record(record, role_order) for record in pred_group]
    fixed_gold = [_to_fixed_slot_record(record, role_order) for record in gold_group]
    diagnostics["fixed_slot_pred_unit_count"] += sum(_non_empty_slot_count(record.slots) for record in fixed_pred)
    diagnostics["fixed_slot_gold_unit_count"] += sum(_non_empty_slot_count(record.slots) for record in fixed_gold)
    diagnostics["collapsed_multi_value_role_count"] += sum(
        record.collapsed_multi_value_role_count for record in fixed_pred + fixed_gold
    )
    return _score_fixed_slot_event_group(fixed_pred, fixed_gold)


def _score_fixed_slot_event_group(
    fixed_pred: list[FixedSlotRecord],
    fixed_gold: list[FixedSlotRecord],
) -> Counts:
    counts = Counts()
    remaining_gold = list(enumerate(fixed_gold))
    sorted_pred = sorted(enumerate(fixed_pred), key=lambda item: _non_empty_slot_count(item[1].slots), reverse=True)
    used_pred = set()

    for pred_index, pred_record in sorted_pred:
        if not remaining_gold:
            break
        best_position = 0
        best_overlap = -1
        for position, (_, gold_record) in enumerate(remaining_gold):
            overlap = _slot_equality_count(pred_record.slots, gold_record.slots)
            if overlap > best_overlap:
                best_overlap = overlap
                best_position = position
        _, gold_record = remaining_gold.pop(best_position)
        counts.add(_count_fixed_slot_pair(pred_record.slots, gold_record.slots))
        used_pred.add(pred_index)

    for pred_index, pred_record in enumerate(fixed_pred):
        if pred_index not in used_pred:
            counts.fp += _non_empty_slot_count(pred_record.slots)
    for _, gold_record in remaining_gold:
        counts.fn += _non_empty_slot_count(gold_record.slots)
    return counts


def _role_order_for_event(
    event_name: str,
    pred_group: list[CanonicalEventRecord],
    gold_group: list[CanonicalEventRecord],
    schema: EventSchema | None,
    diagnostics: dict[str, int],
) -> tuple[str, ...]:
    if schema is not None:
        roles = schema.roles_for(event_name)
        if roles:
            return roles

    diagnostics["schema_role_fallback_event_group_count"] += 1
    role_names = set()
    for record in pred_group + gold_group:
        role_names.update(_record_role_names(record))
    return tuple(sorted(role_names))


def _slot_equality_count(pred_slots: tuple[str | None, ...], gold_slots: tuple[str | None, ...]) -> int:
    return sum(1 for pred_slot, gold_slot in zip(pred_slots, gold_slots) if pred_slot == gold_slot)


def _count_fixed_slot_pair(pred_slots: tuple[str | None, ...], gold_slots: tuple[str | None, ...]) -> Counts:
    counts = Counts()
    for pred_arg, gold_arg in zip(pred_slots, gold_slots):
        if pred_arg is not None and gold_arg is not None and pred_arg == gold_arg:
            counts.tp += 1
        elif pred_arg is not None and gold_arg is None:
            counts.fp += 1
        elif pred_arg is None and gold_arg is not None:
            counts.fn += 1
        elif pred_arg is not None and gold_arg is not None:
            counts.fp += 1
            counts.fn += 1
    return counts


def _to_fixed_slot_record(record: CanonicalEventRecord, role_order: tuple[str, ...]) -> FixedSlotRecord:
    values_by_role = _normalized_values_by_role(record)
    slots = []
    collapsed_multi_value_role_count = 0
    for role in role_order:
        values = values_by_role.get(role, [])
        if not values:
            slots.append(None)
        else:
            if len(values) > 1:
                collapsed_multi_value_role_count += 1
            slots.append(values[-1])
    return FixedSlotRecord(tuple(slots), collapsed_multi_value_role_count)


def _normalized_values_by_role(record: CanonicalEventRecord) -> dict[str, list[str]]:
    values_by_role: dict[str, list[str]] = {}
    for raw_role, raw_values in record.arguments.items():
        role = normalize_optional_text(raw_role)
        if role is None:
            continue
        if isinstance(raw_values, (str, bytes)):
            values = [raw_values]
        else:
            try:
                values = list(raw_values)
            except TypeError:
                values = [raw_values]
        for value in values:
            normalized = normalize_optional_text(value)
            if normalized is not None:
                values_by_role.setdefault(role, []).append(normalized)
    return values_by_role


def _record_role_names(record: CanonicalEventRecord) -> set[str]:
    role_names = set()
    for raw_role in record.arguments:
        role = normalize_optional_text(raw_role)
        if role is not None:
            role_names.add(role)
    return role_names


def _non_empty_slot_count(slots: tuple[str | None, ...]) -> int:
    return sum(1 for slot in slots if slot is not None)
