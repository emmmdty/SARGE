from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from collections import Counter
from collections.abc import Sequence
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))

from sage_dee.v2.data_interface.jsonl import read_jsonl  # noqa: E402

SCHEMA_SUBTYPE_KEYS = (
    "unknown_event_type",
    "unknown_role",
    "invalid_event_object_count",
    "invalid_arguments_shape_count",
    "empty_arguments_count",
    "duplicate_argument",
    "event_type_not_string_count",
    "role_value_not_list_count",
    "unexpected_source_candidate_id_count",
)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    run_a = _load_run(args.run_a)
    run_b = _load_run(args.run_b)

    manifest_diff = {
        "generation_manifest": _diff_mapping(run_a.generation_manifest, run_b.generation_manifest),
        "backend_manifest": _diff_mapping(run_a.backend_manifest, run_b.backend_manifest),
    }
    per_doc_rows = _per_doc_diff_rows(run_a, run_b)
    invalid_role_rows = [*_invalid_role_rows("A", run_a), *_invalid_role_rows("B", run_b)]
    summary = _summary(run_a, run_b, per_doc_rows=per_doc_rows, invalid_role_rows=invalid_role_rows)

    _write_json(args.out_dir / "reproducibility_summary.json", summary)
    _write_json(args.out_dir / "manifest_diff.json", manifest_diff)
    _write_csv(args.out_dir / "per_doc_diff.csv", per_doc_rows, fieldnames=PER_DOC_FIELDS)
    _write_csv(args.out_dir / "invalid_roles.csv", invalid_role_rows, fieldnames=INVALID_ROLE_FIELDS)

    print(f"summary={args.out_dir / 'reproducibility_summary.json'}")
    print(f"per_doc_diff={args.out_dir / 'per_doc_diff.csv'}")
    print(f"invalid_roles={args.out_dir / 'invalid_roles.csv'}")
    print(f"manifest_diff={args.out_dir / 'manifest_diff.json'}")
    return 0


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Compare two GETM dev20 generation runs without repairing artifacts.")
    parser.add_argument("--run-a", type=Path, required=True)
    parser.add_argument("--run-b", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    return parser.parse_args(argv)


class _RunArtifacts:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.prompts_path = root / "prompts.dev.jsonl"
        self.raw_outputs_path = root / "raw_outputs.dev.jsonl"
        self.parsed_candidates_path = root / "parsed_candidates.dev.jsonl"
        self.parse_diagnostics_path = root / "parse_diagnostics.dev.json"
        self.generation_manifest_path = root / "generation_manifest.json"
        self.backend_manifest_path = root / "artifacts" / "backend_manifest.json"
        self.prompts = read_jsonl(self.prompts_path)
        self.raw_outputs = read_jsonl(self.raw_outputs_path)
        self.parsed_candidates = read_jsonl(self.parsed_candidates_path)
        self.parse_diagnostics = _read_json(self.parse_diagnostics_path)
        self.generation_manifest = _read_json(self.generation_manifest_path)
        self.backend_manifest = _read_json(self.backend_manifest_path) if self.backend_manifest_path.exists() else {}
        self.doc_ids = [str(row.get("doc_id") or "") for row in self.prompts]
        self.prompt_sha256 = _file_sha256(self.prompts_path)
        self.raw_by_doc = _group_by_doc_id(self.raw_outputs)
        self.parsed_by_doc = _group_by_doc_id(self.parsed_candidates)
        self.raw_events_by_doc = _raw_events_by_doc(self)
        self.role_counts = _role_counts(self.raw_events_by_doc)
        self.schema_subtypes = _schema_subtype_counts(self)
        self.accepted_event_count = _diagnostic_count(self, "accepted_event_count")
        self.raw_event_count = _diagnostic_count(self, "raw_event_count")


def _load_run(root: Path) -> _RunArtifacts:
    return _RunArtifacts(root)


PER_DOC_FIELDS = (
    "doc_id",
    "in_a",
    "in_b",
    "raw_output_sha_a",
    "raw_output_sha_b",
    "raw_output_sha_equal",
    "stopped_output_sha_a",
    "stopped_output_sha_b",
    "stopped_output_sha_equal",
    "parse_status_a",
    "parse_status_b",
    "event_roles_a",
    "event_roles_b",
    "raw_roles_a",
    "raw_roles_b",
    "unknown_role_a",
    "unknown_role_b",
    "empty_arguments_a",
    "empty_arguments_b",
    "accepted_event_count_a",
    "accepted_event_count_b",
    "raw_event_count_a",
    "raw_event_count_b",
)

INVALID_ROLE_FIELDS = (
    "run",
    "doc_id",
    "candidate_id",
    "event_type",
    "role",
    "raw_event",
)


def _per_doc_diff_rows(run_a: _RunArtifacts, run_b: _RunArtifacts) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    doc_ids = sorted(set(run_a.doc_ids) | set(run_b.doc_ids))
    for doc_id in doc_ids:
        raw_a = run_a.raw_by_doc.get(doc_id, [])
        raw_b = run_b.raw_by_doc.get(doc_id, [])
        parsed_a = run_a.parsed_by_doc.get(doc_id, [])
        parsed_b = run_b.parsed_by_doc.get(doc_id, [])
        raw_sha_a = _rows_field_sha(raw_a, "raw_output")
        raw_sha_b = _rows_field_sha(raw_b, "raw_output")
        stopped_sha_a = _rows_field_sha(raw_a, "stopped_output")
        stopped_sha_b = _rows_field_sha(raw_b, "stopped_output")
        rows.append(
            {
                "doc_id": doc_id,
                "in_a": doc_id in run_a.doc_ids,
                "in_b": doc_id in run_b.doc_ids,
                "raw_output_sha_a": raw_sha_a,
                "raw_output_sha_b": raw_sha_b,
                "raw_output_sha_equal": raw_sha_a == raw_sha_b,
                "stopped_output_sha_a": stopped_sha_a,
                "stopped_output_sha_b": stopped_sha_b,
                "stopped_output_sha_equal": stopped_sha_a == stopped_sha_b,
                "parse_status_a": _parse_statuses(parsed_a),
                "parse_status_b": _parse_statuses(parsed_b),
                "event_roles_a": _event_roles(parsed_a),
                "event_roles_b": _event_roles(parsed_b),
                "raw_roles_a": _raw_roles(run_a.raw_events_by_doc.get(doc_id, [])),
                "raw_roles_b": _raw_roles(run_b.raw_events_by_doc.get(doc_id, [])),
                "unknown_role_a": _parsed_diagnostic_sum(parsed_a, "unknown_role"),
                "unknown_role_b": _parsed_diagnostic_sum(parsed_b, "unknown_role"),
                "empty_arguments_a": _parsed_diagnostic_sum(parsed_a, "empty_arguments_count"),
                "empty_arguments_b": _parsed_diagnostic_sum(parsed_b, "empty_arguments_count"),
                "accepted_event_count_a": _parsed_diagnostic_sum(parsed_a, "accepted_event_count"),
                "accepted_event_count_b": _parsed_diagnostic_sum(parsed_b, "accepted_event_count"),
                "raw_event_count_a": _parsed_diagnostic_sum(parsed_a, "raw_event_count"),
                "raw_event_count_b": _parsed_diagnostic_sum(parsed_b, "raw_event_count"),
            }
        )
    return rows


def _summary(
    run_a: _RunArtifacts,
    run_b: _RunArtifacts,
    *,
    per_doc_rows: list[dict[str, Any]],
    invalid_role_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    raw_same = sum(1 for row in per_doc_rows if row["raw_output_sha_equal"])
    stopped_same = sum(1 for row in per_doc_rows if row["stopped_output_sha_equal"])
    return {
        "run_a": str(run_a.root),
        "run_b": str(run_b.root),
        "doc_ids_identical": run_a.doc_ids == run_b.doc_ids,
        "doc_count_a": len(run_a.doc_ids),
        "doc_count_b": len(run_b.doc_ids),
        "doc_ids_a": run_a.doc_ids,
        "doc_ids_b": run_b.doc_ids,
        "prompts_sha256_a": run_a.prompt_sha256,
        "prompts_sha256_b": run_b.prompt_sha256,
        "prompts_sha256_identical": run_a.prompt_sha256 == run_b.prompt_sha256,
        "raw_output_sha_identical_count": raw_same,
        "raw_output_sha_different_count": len(per_doc_rows) - raw_same,
        "stopped_output_sha_identical_count": stopped_same,
        "stopped_output_sha_different_count": len(per_doc_rows) - stopped_same,
        "accepted_event_count_a": run_a.accepted_event_count,
        "accepted_event_count_b": run_b.accepted_event_count,
        "accepted_event_count_delta": run_b.accepted_event_count - run_a.accepted_event_count,
        "raw_event_count_a": run_a.raw_event_count,
        "raw_event_count_b": run_b.raw_event_count,
        "schema_subtype_counts_a": run_a.schema_subtypes,
        "schema_subtype_counts_b": run_b.schema_subtypes,
        "role_label_counts_a": dict(sorted(run_a.role_counts.items())),
        "role_label_counts_b": dict(sorted(run_b.role_counts.items())),
        "invalid_role_row_count": len(invalid_role_rows),
    }


def _invalid_role_rows(run_label: str, run: _RunArtifacts) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for parsed_row in run.parsed_candidates:
        diagnostics = parsed_row.get("diagnostics") or {}
        if not isinstance(diagnostics, dict) or int(diagnostics.get("unknown_role", 0) or 0) <= 0:
            continue
        doc_id = str(parsed_row.get("doc_id") or "")
        candidate_id = str(parsed_row.get("candidate_id") or "")
        accepted_roles = _accepted_roles_by_event(parsed_row)
        for raw_event in _raw_events_for_candidate(run, candidate_id):
            if not isinstance(raw_event, dict):
                continue
            event_type = str(raw_event.get("event_type") or "")
            arguments = raw_event.get("arguments", raw_event.get("arguments_by_role"))
            if not isinstance(arguments, dict):
                continue
            accepted = accepted_roles.get(event_type, set())
            for role in arguments:
                role_name = str(role).strip()
                if role_name and role_name not in accepted:
                    rows.append(
                        {
                            "run": run_label,
                            "doc_id": doc_id,
                            "candidate_id": candidate_id,
                            "event_type": event_type,
                            "role": role_name,
                            "raw_event": json.dumps(raw_event, ensure_ascii=False, sort_keys=True),
                        }
                    )
    return rows


def _raw_events_for_candidate(run: _RunArtifacts, candidate_id: str) -> list[Any]:
    events: list[Any] = []
    generation = run.generation_manifest.get("generation") or {}
    response_prefix = generation.get("response_prefix")
    for row in run.raw_outputs:
        if str(row.get("candidate_id") or "") != candidate_id:
            continue
        text = str(row.get("stopped_output") or row.get("raw_output") or "")
        events.extend(_raw_events_from_text(text, response_prefix=response_prefix))
    return events


def _raw_events_by_doc(run: _RunArtifacts) -> dict[str, list[Any]]:
    generation = run.generation_manifest.get("generation") or {}
    response_prefix = generation.get("response_prefix")
    events_by_doc: dict[str, list[Any]] = {}
    for row in run.raw_outputs:
        doc_id = str(row.get("doc_id") or "")
        text = str(row.get("stopped_output") or row.get("raw_output") or "")
        events_by_doc.setdefault(doc_id, []).extend(_raw_events_from_text(text, response_prefix=response_prefix))
    return events_by_doc


def _raw_events_from_text(text: str, *, response_prefix: Any) -> list[Any]:
    payload = _json_payload(text)
    if payload is None and response_prefix:
        payload = _json_payload(f"{response_prefix}{text}")
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        if "event_type" in payload:
            return [payload]
        events = payload.get("events") or []
        return events if isinstance(events, list) else []
    return []


def _json_payload(text: str) -> Any | None:
    stripped = str(text).strip()
    if not stripped:
        return None
    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        pass
    try:
        payload, end_index = json.JSONDecoder().raw_decode(stripped)
    except json.JSONDecodeError:
        payload = None
    else:
        if not stripped[end_index:].strip():
            return payload
    start = stripped.find("{")
    if start >= 0:
        end = _balanced_json_object_end(stripped, start)
        if end is not None:
            try:
                return json.loads(stripped[start:end])
            except json.JSONDecodeError:
                return None
    if stripped.startswith("["):
        try:
            return json.loads(stripped)
        except json.JSONDecodeError:
            return None
    return None


def _balanced_json_object_end(text: str, start: int) -> int | None:
    depth = 0
    in_string = False
    escaped = False
    for index, char in enumerate(text[start:], start):
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            continue
        if char == '"':
            in_string = True
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return index + 1
    return None


def _accepted_roles_by_event(parsed_row: dict[str, Any]) -> dict[str, set[str]]:
    accepted: dict[str, set[str]] = {}
    for event in parsed_row.get("events") or []:
        if not isinstance(event, dict):
            continue
        event_type = str(event.get("event_type") or "")
        arguments = event.get("arguments") or {}
        if isinstance(arguments, dict):
            accepted.setdefault(event_type, set()).update(str(role).strip() for role in arguments)
    return accepted


def _schema_subtype_counts(run: _RunArtifacts) -> dict[str, int]:
    diagnostic_counts = run.parse_diagnostics.get("diagnostic_counts") or {}
    if isinstance(diagnostic_counts, dict):
        return {key: int(diagnostic_counts.get(key, 0) or 0) for key in SCHEMA_SUBTYPE_KEYS}
    counts = Counter()
    for row in run.parsed_candidates:
        diagnostics = row.get("diagnostics") or {}
        if isinstance(diagnostics, dict):
            for key in SCHEMA_SUBTYPE_KEYS:
                counts[key] += int(diagnostics.get(key, 0) or 0)
    return {key: int(counts.get(key, 0)) for key in SCHEMA_SUBTYPE_KEYS}


def _diagnostic_count(run: _RunArtifacts, key: str) -> int:
    diagnostic_counts = run.parse_diagnostics.get("diagnostic_counts") or {}
    if isinstance(diagnostic_counts, dict) and key in diagnostic_counts:
        return int(diagnostic_counts.get(key, 0) or 0)
    return sum(_parsed_diagnostic_sum(rows, key) for rows in run.parsed_by_doc.values())


def _role_counts(raw_events_by_doc: dict[str, list[Any]]) -> Counter[str]:
    counts: Counter[str] = Counter()
    for events in raw_events_by_doc.values():
        for event in events:
            if not isinstance(event, dict):
                continue
            arguments = event.get("arguments", event.get("arguments_by_role"))
            if not isinstance(arguments, dict):
                continue
            for role in arguments:
                role_name = str(role).strip()
                if role_name:
                    counts[role_name] += 1
    return counts


def _raw_roles(events: list[Any]) -> str:
    roles: list[str] = []
    for event in events:
        if not isinstance(event, dict):
            continue
        event_type = str(event.get("event_type") or "")
        arguments = event.get("arguments", event.get("arguments_by_role"))
        if isinstance(arguments, dict):
            roles.extend(f"{event_type}/{role}" for role in sorted(str(role) for role in arguments))
    return ";".join(sorted(roles))


def _event_roles(parsed_rows: list[dict[str, Any]]) -> str:
    roles: list[str] = []
    for row in parsed_rows:
        for event in row.get("events") or []:
            if not isinstance(event, dict):
                continue
            event_type = str(event.get("event_type") or "")
            arguments = event.get("arguments") or {}
            if isinstance(arguments, dict):
                roles.extend(f"{event_type}/{role}" for role in sorted(str(role) for role in arguments))
    return ";".join(sorted(roles))


def _parse_statuses(parsed_rows: list[dict[str, Any]]) -> str:
    return ";".join(str(row.get("parse_status") or "") for row in parsed_rows)


def _parsed_diagnostic_sum(parsed_rows: list[dict[str, Any]], key: str) -> int:
    total = 0
    for row in parsed_rows:
        diagnostics = row.get("diagnostics") or {}
        if isinstance(diagnostics, dict):
            total += int(diagnostics.get(key, 0) or 0)
    return total


def _rows_field_sha(rows: list[dict[str, Any]], field: str) -> str:
    hasher = hashlib.sha256()
    for row in rows:
        value = row.get(field)
        if value is None and field == "stopped_output":
            value = row.get("raw_output")
        hasher.update(str(value or "").encode("utf-8"))
        hasher.update(b"\n")
    return hasher.hexdigest()


def _diff_mapping(a: dict[str, Any], b: dict[str, Any]) -> dict[str, dict[str, Any]]:
    flat_a = _flatten(a)
    flat_b = _flatten(b)
    diff: dict[str, dict[str, Any]] = {}
    for key in sorted(set(flat_a) | set(flat_b)):
        value_a = flat_a.get(key)
        value_b = flat_b.get(key)
        diff[key] = {"a": value_a, "b": value_b, "same": value_a == value_b}
    return diff


def _flatten(value: Any, *, prefix: str = "") -> dict[str, Any]:
    if isinstance(value, dict):
        flattened: dict[str, Any] = {}
        for key, child in value.items():
            child_prefix = f"{prefix}.{key}" if prefix else str(key)
            flattened.update(_flatten(child, prefix=child_prefix))
        return flattened
    return {prefix: value}


def _group_by_doc_id(rows: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        grouped.setdefault(str(row.get("doc_id") or ""), []).append(row)
    return grouped


def _file_sha256(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def _read_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object: {path}")
    return payload


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_csv(path: Path, rows: list[dict[str, Any]], *, fieldnames: Sequence[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({key: _csv_value(row.get(key)) for key in fieldnames})


def _csv_value(value: Any) -> Any:
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    return value


if __name__ == "__main__":
    raise SystemExit(main())
