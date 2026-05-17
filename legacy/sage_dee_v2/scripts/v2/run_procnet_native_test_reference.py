from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from collections.abc import Sequence
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def main(argv: Sequence[str] | None = None) -> int:
    try:
        args = parse_args(argv)
        _validate_args(args)
        metrics, diagnostics = run_reference(args)
        args.out_dir.mkdir(parents=True, exist_ok=True)
        _write_json(args.out_dir / "procnet_native_reference_metrics.json", metrics)
        _write_json(args.out_dir / "conversion_diagnostics.json", diagnostics)
        _write_note(args.out_dir / "methodology_note.md", metrics=metrics, diagnostics=diagnostics)
        print(f"procnet_native_reference_out={args.out_dir}")
        print(
            "metrics="
            + json.dumps(
                {
                    "micro_precision": metrics["micro_precision"],
                    "micro_recall": metrics["micro_recall"],
                    "micro_f1": metrics["micro_f1"],
                },
                ensure_ascii=False,
                sort_keys=True,
            )
        )
        return 0
    except (FileNotFoundError, ImportError, RuntimeError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run ProcNet-native table-filling reference scoring for an existing SAGE test prediction."
    )
    parser.add_argument("--procnet-root", required=True, type=Path)
    parser.add_argument("--schema", required=True, type=Path)
    parser.add_argument("--gold", required=True, type=Path)
    parser.add_argument("--pred", required=True, type=Path)
    parser.add_argument("--out-dir", required=True, type=Path)
    parser.add_argument("--dataset", default="DuEE-Fin-dev500")
    parser.add_argument("--split", default="test")
    parser.add_argument("--seed", default=42, type=int)
    parser.add_argument("--source-system", default="Phase13 S4 seed42 frozen final-test prediction")
    parser.add_argument("--branch-methodology-reference", action="store_true")
    return parser.parse_args(argv)


def run_reference(args: argparse.Namespace) -> tuple[dict[str, Any], dict[str, Any]]:
    sys.path.insert(0, str(args.procnet_root))
    from procnet.dee.dee_metric import measure_event_table_filling

    schema = json.loads(args.schema.read_text(encoding="utf-8"))
    event_type_roles_list = _event_type_roles_list(schema)
    event_type_list = [event_type for event_type, _roles in event_type_roles_list]
    event_to_index = {event_type: index for index, event_type in enumerate(event_type_list)}
    role_sets = {event_type: set(roles) for event_type, roles in event_type_roles_list}

    gold_rows = _read_jsonl(args.gold)
    pred_rows = _read_jsonl(args.pred)
    gold_by_doc = _index_by_doc_id(gold_rows, label="gold")
    pred_by_doc = _index_by_doc_id(pred_rows, label="pred")
    _assert_same_docs(gold_by_doc, pred_by_doc)

    created_at = _created_at()
    diagnostics: dict[str, Any] = {
        "created_at": created_at,
        "source_system": args.source_system,
        "seed": args.seed,
        "dataset": args.dataset,
        "split": args.split,
        "gold_path": str(args.gold),
        "prediction_path": str(args.pred),
        "schema_path": str(args.schema),
        "procnet_root": str(args.procnet_root),
        "doc_id_alignment_ok": True,
        "gold_rows": len(gold_rows),
        "prediction_rows": len(pred_rows),
        "doc_count": len(gold_by_doc),
        "gold_event_count": sum(len(row.get("events") or []) for row in gold_rows),
        "prediction_event_count": sum(len(row.get("events") or []) for row in pred_rows),
        "event_type_count": len(event_type_list),
        "unknown_gold_event_types": Counter(),
        "unknown_pred_event_types": Counter(),
        "unknown_gold_roles": Counter(),
        "unknown_pred_roles": Counter(),
        "multi_value_role_slots": Counter(),
        "empty_text_values": Counter(),
        "record_count_by_source": Counter(),
        "conversion_policy": _conversion_policy(),
    }

    gold_record_mat_list = []
    pred_record_mat_list = []
    for doc_id in gold_by_doc:
        gold_record_mat_list.append(
            _canonical_doc_to_record_mat(
                gold_by_doc[doc_id],
                event_to_index=event_to_index,
                role_sets=role_sets,
                event_type_roles_list=event_type_roles_list,
                diagnostics=diagnostics,
                source="gold",
            )
        )
        pred_record_mat_list.append(
            _canonical_doc_to_record_mat(
                pred_by_doc[doc_id],
                event_to_index=event_to_index,
                role_sets=role_sets,
                event_type_roles_list=event_type_roles_list,
                diagnostics=diagnostics,
                source="pred",
            )
        )

    _fail_on_unknowns(diagnostics)
    score = measure_event_table_filling(
        pred_record_mat_list,
        gold_record_mat_list,
        event_type_roles_list,
        event_type_list,
    )
    metrics = {
        "created_at": created_at,
        "source_system": args.source_system,
        "seed": args.seed,
        "dataset": args.dataset,
        "split": args.split,
        "native_reference_only": True,
        "formal_metric": False,
        "frozen_final_result": False,
        "phase13_reinterpretation": False,
        "metric_family": "ProcNet native table-filling reference",
        "procnet_metric_module": str(args.procnet_root / "procnet/dee/dee_metric.py"),
        "score": score,
        "micro_precision": score.get("micro_precision"),
        "micro_recall": score.get("micro_recall"),
        "micro_f1": score.get("micro_f1"),
        "source_prediction_path": str(args.pred),
        "source_gold_path": str(args.gold),
        "conversion_policy": diagnostics["conversion_policy"],
    }
    return metrics, diagnostics


def _validate_args(args: argparse.Namespace) -> None:
    if args.split != "test":
        raise ValueError("ProcNet-native test reference requires split=test")
    if not args.branch_methodology_reference:
        raise ValueError("test reference scoring requires --branch-methodology-reference")
    if _under_phase13_run_root(args.out_dir):
        raise ValueError("ProcNet-native test reference refuses to write under a Phase 13 run root")
    for path in (args.procnet_root, args.schema, args.gold, args.pred):
        if not path.exists():
            raise FileNotFoundError(path)


def _under_phase13_run_root(path: Path) -> bool:
    return any("phase13_final_test" in part for part in path.resolve().parts)


def _event_type_roles_list(schema: dict[str, Any]) -> list[tuple[str, list[str]]]:
    event_types = schema.get("event_types")
    if not isinstance(event_types, list) or not event_types:
        raise ValueError("schema.event_types must be a non-empty list")
    result: list[tuple[str, list[str]]] = []
    for event in event_types:
        event_type = str(event.get("event_type") or "").strip()
        roles = [str(role).strip() for role in (event.get("roles") or []) if str(role).strip()]
        if not event_type or not roles:
            raise ValueError(f"invalid schema event entry: {event!r}")
        result.append((event_type, roles))
    return result


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = []
    with path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            if not isinstance(row, dict):
                raise ValueError(f"{path}:{line_number}: row must be an object")
            rows.append(row)
    return rows


def _index_by_doc_id(rows: list[dict[str, Any]], *, label: str) -> dict[str, dict[str, Any]]:
    by_doc: dict[str, dict[str, Any]] = {}
    for index, row in enumerate(rows, 1):
        doc_id = str(row.get("doc_id") or "").strip()
        if not doc_id:
            raise ValueError(f"{label} row {index} missing doc_id")
        if doc_id in by_doc:
            raise ValueError(f"{label} duplicate doc_id: {doc_id}")
        by_doc[doc_id] = row
    return by_doc


def _assert_same_docs(gold_by_doc: dict[str, Any], pred_by_doc: dict[str, Any]) -> None:
    gold_docs = set(gold_by_doc)
    pred_docs = set(pred_by_doc)
    if gold_docs != pred_docs:
        missing_pred = sorted(gold_docs - pred_docs)[:10]
        extra_pred = sorted(pred_docs - gold_docs)[:10]
        raise ValueError(f"doc_id mismatch: missing_pred={missing_pred}, extra_pred={extra_pred}")


def _canonical_doc_to_record_mat(
    row: dict[str, Any],
    *,
    event_to_index: dict[str, int],
    role_sets: dict[str, set[str]],
    event_type_roles_list: list[tuple[str, list[str]]],
    diagnostics: dict[str, Any],
    source: str,
) -> list[list[tuple[Any, ...]]]:
    record_mat: list[list[tuple[Any, ...]]] = [[] for _ in event_type_roles_list]
    events = row.get("events") or []
    if not isinstance(events, list):
        raise ValueError(f"{source} doc {row.get('doc_id')}: events must be a list")
    for event in events:
        if not isinstance(event, dict):
            raise ValueError(f"{source} doc {row.get('doc_id')}: event must be an object")
        event_type = str(event.get("event_type") or "").strip()
        if event_type not in event_to_index:
            diagnostics[f"unknown_{source}_event_types"][event_type] += 1
            continue
        arguments = event.get("arguments") or {}
        if not isinstance(arguments, dict):
            raise ValueError(f"{source} doc {row.get('doc_id')} event {event_type}: arguments must be an object")
        role_values: dict[str, Any] = {}
        for role, values in arguments.items():
            role_name = str(role).strip()
            if role_name not in role_sets[event_type]:
                diagnostics[f"unknown_{source}_roles"][(event_type, role_name)] += 1
                continue
            texts = _extract_texts(values, diagnostics=diagnostics, source=source)
            if not texts:
                continue
            if len(texts) > 1:
                diagnostics["multi_value_role_slots"][(source, event_type, role_name)] += 1
            role_values[role_name] = texts[0] if len(texts) == 1 else tuple(texts)
        roles = event_type_roles_list[event_to_index[event_type]][1]
        record = tuple(role_values.get(role) for role in roles)
        record_mat[event_to_index[event_type]].append(record)
        diagnostics["record_count_by_source"][(source, event_type)] += 1
    return record_mat


def _extract_texts(values: Any, *, diagnostics: dict[str, Any], source: str) -> list[str]:
    if not isinstance(values, list):
        raise ValueError(f"{source} argument values must be lists")
    texts: list[str] = []
    for value in values:
        if isinstance(value, dict):
            text = str(value.get("text") or "").strip()
        else:
            text = str(value or "").strip()
        if text:
            texts.append(text)
        else:
            diagnostics["empty_text_values"][source] += 1
    return sorted(set(texts))


def _fail_on_unknowns(diagnostics: dict[str, Any]) -> None:
    unknowns = {
        key: dict(value)
        for key, value in diagnostics.items()
        if key.startswith("unknown_") and isinstance(value, Counter) and value
    }
    if unknowns:
        raise ValueError(f"unknown schema items encountered without repair: {unknowns}")


def _conversion_policy() -> dict[str, Any]:
    return {
        "role_value_matching": "exact_text",
        "multi_value_role_slot": "tuple_of_sorted_unique_exact_texts",
        "empty_text": "ignored",
        "alias_mapping": False,
        "role_guessing": False,
        "event_type_guessing": False,
        "semantic_repair": False,
        "llm_judge": False,
        "formal_metric": False,
        "native_reference_only": True,
    }


def _jsonable(value: Any) -> Any:
    if isinstance(value, Counter):
        return {
            " | ".join(map(str, key)) if isinstance(key, tuple) else str(key): _jsonable(count)
            for key, count in value.items()
        }
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    return value


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(_jsonable(payload), ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _write_note(path: Path, *, metrics: dict[str, Any], diagnostics: dict[str, Any]) -> None:
    text = f"""# ProcNet-Native Test Reference: {metrics['source_system']}

This artifact is an 独立方法论参考分支 result. It is a 非正式指标 and a 非 frozen final result.

- source system: `{metrics['source_system']}`
- source prediction: `{metrics['source_prediction_path']}`
- gold: `{metrics['source_gold_path']}`
- ProcNet metric module: `{metrics['procnet_metric_module']}`
- micro precision: `{metrics['micro_precision']}`
- micro recall: `{metrics['micro_recall']}`
- micro F1: `{metrics['micro_f1']}`
- gold rows: `{diagnostics['gold_rows']}`
- prediction rows: `{diagnostics['prediction_rows']}`
- gold events: `{diagnostics['gold_event_count']}`
- prediction events: `{diagnostics['prediction_event_count']}`

Scope declarations:

- native_reference_only: `true`
- formal_metric: `false`
- frozen_final_result: `false`
- phase13_reinterpretation: `false`
- SAGE training run: `NO`
- ProcNet training run: `NO`
- Qwen inference run: `NO`
- dee-eval run: `NO`
- evaluator modification: `NO`
- alias mapping / role guessing / event type guessing / semantic repair / LLM judge: `NO`

Conversion policy: canonical event records are mapped into ProcNet event-table matrices using the evaluator-gold schema
order. Role values are exact text; multi-value role slots are represented as sorted unique exact-text tuples.
"""
    path.write_text(text, encoding="utf-8")


def _created_at() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


if __name__ == "__main__":
    raise SystemExit(main())
