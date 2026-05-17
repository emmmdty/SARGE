from __future__ import annotations

import argparse
import json
import re
import sys
from collections.abc import Sequence
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))

from sage_dee.v2.data_interface.jsonl import read_jsonl  # noqa: E402

ARGUMENTS_LITERAL_ROLE_RE = re.compile(r'"arguments"\s*:\s*\{\s*"role"\s*:')

FORBIDDEN_CANONICAL_KEYS = frozenset(
    {
        "gold",
        "events_gold",
        "norm_text",
        "slot_id",
        "source_candidate_id",
        "evidence_chunk_id",
        "alignment_score",
        "logprob",
        "reward",
        "mrs_score",
        "content",
        "content_raw",
        "dataset",
        "split",
    }
)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    args.out_dir.mkdir(parents=True, exist_ok=True)

    artifact_counts = {
        "prompts": _artifact_counts(args.prompts, content_key="prompt"),
        "targets": _artifact_counts(args.targets, content_key="output"),
        "canonical": _artifact_counts(args.canonical, content_key=None),
    }
    diagnostic_counts = _diagnostic_counts(
        parsed_candidates=args.parsed_candidates,
        parse_diagnostics=args.parse_diagnostics,
    )
    forbidden_violations = _forbidden_key_violations(args.canonical)

    summary = {
        "created_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "dataset": args.dataset,
        "split": args.split,
        "artifact_counts": artifact_counts,
        "literal_role_argument_key_occurrences": sum(
            counts["literal_role_argument_key_occurrences"] for counts in artifact_counts.values()
        ),
        "unknown_role_count": diagnostic_counts["unknown_role_count"],
        "unknown_event_type_count": diagnostic_counts["unknown_event_type_count"],
        "schema_violation_count": diagnostic_counts["schema_violation_count"],
        "parse_status_counts": diagnostic_counts["parse_status_counts"],
        "forbidden_key_violation_count": len(forbidden_violations),
        "forbidden_key_violations": forbidden_violations,
        "forbidden_keys": sorted(FORBIDDEN_CANONICAL_KEYS),
        "gold_visible": False,
        "offline_audit_only": True,
    }

    _write_samples(args)
    summary_path = _write_json(args.out_dir / f"role_safe_audit.{args.split}.json", summary)
    print(f"role_safe_audit={summary_path}")
    return 0


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Audit SAGE-DEE v2 Phase 1 role-safe GETM artifacts.")
    parser.add_argument("--dataset", required=True)
    parser.add_argument("--split", required=True)
    parser.add_argument("--prompts", type=Path)
    parser.add_argument("--targets", type=Path)
    parser.add_argument("--canonical", type=Path)
    parser.add_argument("--parsed-candidates", type=Path)
    parser.add_argument("--parse-diagnostics", type=Path)
    parser.add_argument("--out-dir", type=Path, required=True)
    return parser.parse_args(argv)


def _artifact_counts(path: Path | None, *, content_key: str | None) -> dict[str, int | str | None]:
    if path is None:
        return {
            "path": None,
            "row_count": 0,
            "literal_role_argument_key_occurrences": 0,
        }
    rows = read_jsonl(path)
    count = 0
    for row in rows:
        count += _literal_role_argument_key_count(_artifact_content(row, content_key=content_key))
    return {
        "path": str(path),
        "row_count": len(rows),
        "literal_role_argument_key_occurrences": count,
    }


def _artifact_content(row: Any, *, content_key: str | None) -> str:
    if content_key is None:
        return json.dumps(row, ensure_ascii=False, sort_keys=True)
    if isinstance(row, dict) and content_key in row:
        value = row[content_key]
    else:
        value = row
    if isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def _literal_role_argument_key_count(text: str) -> int:
    return len(ARGUMENTS_LITERAL_ROLE_RE.findall(text))


def _diagnostic_counts(
    *,
    parsed_candidates: Path | None,
    parse_diagnostics: Path | None,
) -> dict[str, Any]:
    if parsed_candidates is not None:
        rows = read_jsonl(parsed_candidates)
        counts = {
            "unknown_role_count": 0,
            "unknown_event_type_count": 0,
            "schema_violation_count": 0,
        }
        parse_status_counts: dict[str, int] = {}
        for row in rows:
            status = str(row.get("parse_status") or "unknown")
            parse_status_counts[status] = parse_status_counts.get(status, 0) + 1
            diagnostics = row.get("diagnostics") or {}
            if not isinstance(diagnostics, dict):
                continue
            counts["unknown_role_count"] += _diagnostic_value(diagnostics, "unknown_role")
            counts["unknown_event_type_count"] += _diagnostic_value(diagnostics, "unknown_event_type")
            counts["schema_violation_count"] += _diagnostic_value(diagnostics, "schema_violation")
        return {**counts, "parse_status_counts": dict(sorted(parse_status_counts.items()))}

    if parse_diagnostics is not None:
        payload = _read_json(parse_diagnostics)
        counts = payload.get("diagnostic_counts") or {}
        if not isinstance(counts, dict):
            counts = {}
        return {
            "unknown_role_count": _diagnostic_value(counts, "unknown_role"),
            "unknown_event_type_count": _diagnostic_value(counts, "unknown_event_type"),
            "schema_violation_count": _diagnostic_value(counts, "schema_violation"),
            "parse_status_counts": payload.get("parse_status_counts") or {},
        }

    return {
        "unknown_role_count": 0,
        "unknown_event_type_count": 0,
        "schema_violation_count": 0,
        "parse_status_counts": {},
    }


def _diagnostic_value(diagnostics: dict[str, Any], key: str) -> int:
    direct = diagnostics.get(key)
    if isinstance(direct, int):
        return direct
    counted = diagnostics.get(f"{key}_count")
    if isinstance(counted, int):
        return counted
    return 0


def _forbidden_key_violations(path: Path | None) -> list[dict[str, Any]]:
    if path is None:
        return []
    rows = read_jsonl(path)
    violations = []
    for row_index, row in enumerate(rows, 1):
        for key_path in _forbidden_key_paths(row):
            violations.append({"row": row_index, "key_path": key_path})
    return violations


def _forbidden_key_paths(value: Any, *, prefix: str = "") -> list[str]:
    paths: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            key_path = f"{prefix}.{key}" if prefix else str(key)
            if key in FORBIDDEN_CANONICAL_KEYS:
                paths.append(key_path)
            paths.extend(_forbidden_key_paths(child, prefix=key_path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            key_path = f"{prefix}[{index}]" if prefix else f"[{index}]"
            paths.extend(_forbidden_key_paths(child, prefix=key_path))
    return paths


def _write_samples(args: argparse.Namespace) -> None:
    prompt_sample = _first_row(args.prompts)
    if isinstance(prompt_sample, dict):
        (args.out_dir / f"prompt_sample.{args.split}.txt").write_text(
            str(prompt_sample.get("prompt") or ""),
            encoding="utf-8",
        )
    target_sample = _first_row(args.targets)
    if target_sample is not None:
        _write_json(args.out_dir / f"target_sample.{args.split}.json", target_sample)
    canonical_sample = _first_row(args.canonical)
    if canonical_sample is not None:
        _write_json(args.out_dir / f"canonical_sample.{args.split}.json", canonical_sample)


def _first_row(path: Path | None) -> Any | None:
    if path is None:
        return None
    rows = read_jsonl(path)
    return rows[0] if rows else None


def _read_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object: {path}")
    return payload


def _write_json(path: Path, payload: Any) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
    return path


if __name__ == "__main__":
    raise SystemExit(main())
