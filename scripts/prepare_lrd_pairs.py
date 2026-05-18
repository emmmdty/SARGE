"""Generate pairwise training labels for LRD from SARGE candidate output.

Reads the intermediate parsed-candidates jsonl produced by the GETM stage
and the evaluator-gold (or staged-gold) jsonl, then runs Hungarian alignment
to assign each predicted record to the best-matching gold record.  Pairs
assigned to the same gold record become positive samples; all others are
negative.

Output: a jsonl file where each row is a single document with fields
``doc_id``, ``records`` (list of event dicts), ``pairs`` (list of
``[i, j, label, event_type]`` entries), and ``pair_mask`` for training.

Example:
    python scripts/prepare_lrd_pairs.py \\
        --candidates runs/.../parsed_candidates.dev.jsonl \\
        --gold data/processed/DuEE-Fin-dev500/dev.jsonl \\
        --schema data/processed/DuEE-Fin-dev500/schema.json \\
        --out runs/lrd/train_pairs.jsonl
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Iterable
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
SRC = REPO_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from sarge.data.schema import load_schema  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidates", required=True, help="parsed GETM candidates jsonl")
    parser.add_argument("--gold", required=True, help="gold jsonl (dee-fin processed format)")
    parser.add_argument("--schema", required=True, help="schema.json path")
    parser.add_argument("--out", required=True, help="output jsonl for LRD training pairs")
    parser.add_argument("--max-docs", type=int, default=None, help="cap on documents")
    args = parser.parse_args()

    schema = load_schema("lrd", data_root=Path(args.schema).parent)
    candidates_by_doc = _load_candidates(args.candidates, args.max_docs)
    gold_by_doc = _load_gold(args.gold, args.max_docs)

    total_pairs = 0
    total_pos = 0
    written = 0
    with Path(args.out).open("w", encoding="utf-8") as handle:
        for doc_id, gold_records in gold_by_doc.items():
            candidate_rows = candidates_by_doc.get(doc_id)
            if not candidate_rows:
                continue
            # Flatten multi-k candidate entries into a single record list.
            pred_records = _flatten_candidates(candidate_rows)
            if len(pred_records) < 2:
                continue

            # Build pairwise labels via Hungarian matching to gold.
            pairs, pos_count = _build_pairs(pred_records, gold_records, schema)
            if len(pairs) < 1:
                continue

            row = {
                "doc_id": doc_id,
                "records": pred_records,
                "pairs": pairs,
            }
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
            written += 1
            total_pairs += len(pairs)
            total_pos += pos_count

    print(f"wrote {written} docs, {total_pairs} pairs (pos={total_pos}, neg={total_pairs - total_pos})")
    return 0


def _flatten_candidates(rows: list[dict]) -> list[dict]:
    """Each row may contain multiple candidate events (k variants)."""
    records: list[dict] = []
    for row in rows:
        events = row.get("events") or row.get("predictions") or []
        if isinstance(events, list):
            for event in events:
                if isinstance(event, dict):
                    records.append(event)
    return records


def _build_pairs(
    pred_records: list[dict],
    gold_records: list[dict],
    schema: Any,
) -> tuple[list[dict], int]:
    """Hungarian-align predictions to gold, then label pairwise matches."""
    n = len(pred_records)
    # Simple greedy matching (unified_strict style: event_type match,
    # role-value overlap score).
    assignments = _match_predictions(pred_records, gold_records)

    pairs: list[dict] = []
    pos_count = 0
    for i in range(n):
        for j in range(i + 1, n):
            same = assignments.get(i) is not None and assignments.get(j) is not None and assignments[i] == assignments[j]
            label = 1 if same else 0
            pairs.append({
                "i": i, "j": j,
                "label": label,
                "event_type_i": pred_records[i].get("event_type", ""),
                "event_type_j": pred_records[j].get("event_type", ""),
            })
            if label == 1:
                pos_count += 1
    return pairs, pos_count


def _match_predictions(pred_records: list[dict], gold_records: list[dict]) -> dict[int, int]:
    """Greedy record-to-record matching (event_type constrained)."""
    assignments: dict[int, int] = {}

    def _score(pred: dict, gold: dict) -> int:
        if pred.get("event_type") != gold.get("event_type"):
            return 0
        pred_args = _flat_args(pred)
        gold_args = _flat_args(gold)
        return len(pred_args & gold_args)

    available_gold = list(enumerate(gold_records))
    for pi, pred in enumerate(pred_records):
        best_g = -1
        best_s = 0
        for g_idx, (gi, gold) in enumerate(available_gold):
            s = _score(pred, gold)
            if s > best_s:
                best_s = s
                best_g = g_idx
        if best_g >= 0 and best_s > 0:
            _, gi = available_gold.pop(best_g)
            assignments[pi] = gi
    return assignments


def _flat_args(record: dict) -> set[tuple[str, str]]:
    result: set[tuple[str, str]] = set()
    args = record.get("arguments") or {}
    for role, values in (args.items() if isinstance(args, dict) else []):
        for value in (values or []):
            text = str(value if isinstance(value, str) else value.get("text", "")).strip()
            if text:
                result.add((role, text))
    return result


def _load_candidates(path: str, limit: int | None) -> dict[str, list[dict]]:
    result: dict[str, list[dict]] = {}
    with Path(path).open(encoding="utf-8") as f:
        for idx, line in enumerate(f):
            if limit is not None and idx >= limit:
                break
            if not line.strip():
                continue
            row = json.loads(line)
            doc_id = row.get("doc_id") or row.get("document_id") or ""
            if not doc_id:
                continue
            result.setdefault(doc_id, []).append(row)
    return result


def _load_gold(path: str, limit: int | None) -> dict[str, list[dict]]:
    """Load gold jsonl in dee-fin processed format."""
    result: dict[str, list[dict]] = {}
    with Path(path).open(encoding="utf-8") as f:
        for idx, line in enumerate(f):
            if limit is not None and idx >= limit:
                break
            if not line.strip():
                continue
            row = json.loads(line)
            doc_id = row.get("doc_id") or row.get("id") or ""
            if not doc_id:
                continue
            # Convert event_list → canonical events.
            events = row.get("event_list") or row.get("events") or []
            gold_records: list[dict] = []
            for event in (events if isinstance(events, list) else []):
                if not isinstance(event, dict):
                    continue
                et = event.get("event_type", "")
                args: dict[str, list[str]] = {}
                for arg in (event.get("arguments") or []):
                    if not isinstance(arg, dict):
                        continue
                    role = arg.get("role", "")
                    val = arg.get("argument") or arg.get("text") or ""
                    if role and val:
                        args.setdefault(str(role), []).append(str(val))
                if et:
                    gold_records.append({
                        "event_type": str(et),
                        "arguments": args,
                    })
            if gold_records:
                result[doc_id] = gold_records
    return result


if __name__ == "__main__":
    raise SystemExit(main())
