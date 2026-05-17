from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter
from collections.abc import Iterable, Sequence
from pathlib import Path
from typing import Any


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    if args.split == "test":
        raise SystemExit("Phase 8 split audit rejects test split; test remains blocked")

    procnet_docs = _load_procnet_doc2edag(args.procnet_view)
    evaluator_docs = _load_evaluator_gold_jsonl(args.evaluator_view)
    report = audit_split_alignment(
        procnet_docs=procnet_docs,
        evaluator_docs=evaluator_docs,
        dataset=args.dataset,
        split=args.split,
        procnet_view=args.procnet_view,
        evaluator_view=args.evaluator_view,
    )

    payload = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.out_json is not None:
        args.out_json.parent.mkdir(parents=True, exist_ok=True)
        args.out_json.write_text(payload, encoding="utf-8")
        print(f"split_audit_json={args.out_json}")
    else:
        print(payload, end="")
    return 0 if report["direct_comparable_split"] else 1


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Audit ProcNet split alignment against evaluator_gold views.")
    parser.add_argument("--dataset", required=True)
    parser.add_argument("--split", default="dev", choices=("train", "dev", "test"))
    parser.add_argument("--procnet-view", required=True, type=Path)
    parser.add_argument("--evaluator-view", required=True, type=Path)
    parser.add_argument("--out-json", type=Path)
    return parser.parse_args(argv)


def audit_split_alignment(
    *,
    procnet_docs: list[dict[str, str]],
    evaluator_docs: list[dict[str, str]],
    dataset: str,
    split: str,
    procnet_view: Path,
    evaluator_view: Path,
) -> dict[str, Any]:
    procnet_ids = [doc["doc_id"] for doc in procnet_docs]
    evaluator_ids = [doc["doc_id"] for doc in evaluator_docs]
    procnet_texts = [doc["content"] for doc in procnet_docs]
    evaluator_texts = [doc["content"] for doc in evaluator_docs]

    ids_same_order = procnet_ids == evaluator_ids
    ids_same_set = set(procnet_ids) == set(evaluator_ids)
    content_exact_same_order = procnet_texts == evaluator_texts
    content_normalized_same_order = [_normalize_content(text) for text in procnet_texts] == [
        _normalize_content(text) for text in evaluator_texts
    ]
    direct_comparable_split = (
        len(procnet_docs) == len(evaluator_docs)
        and ids_same_order
        and ids_same_set
        and content_normalized_same_order
        and not _duplicates(procnet_ids)
        and not _duplicates(evaluator_ids)
    )

    missing_in_evaluator = sorted(set(procnet_ids) - set(evaluator_ids))
    missing_in_procnet = sorted(set(evaluator_ids) - set(procnet_ids))
    return {
        "dataset": dataset,
        "split": split,
        "procnet_view": str(procnet_view),
        "evaluator_view": str(evaluator_view),
        "procnet_doc_count": len(procnet_docs),
        "evaluator_doc_count": len(evaluator_docs),
        "ids_same_order": ids_same_order,
        "ids_same_set": ids_same_set,
        "content_exact_same_order": content_exact_same_order,
        "content_normalized_same_order": content_normalized_same_order,
        "procnet_doc_id_hash": _stable_hash(procnet_ids),
        "evaluator_doc_id_hash": _stable_hash(evaluator_ids),
        "procnet_normalized_content_hash": _stable_hash(_hash_text(_normalize_content(text)) for text in procnet_texts),
        "evaluator_normalized_content_hash": _stable_hash(
            _hash_text(_normalize_content(text)) for text in evaluator_texts
        ),
        "procnet_duplicate_doc_ids": _duplicates(procnet_ids),
        "evaluator_duplicate_doc_ids": _duplicates(evaluator_ids),
        "missing_in_evaluator_sample": missing_in_evaluator[:10],
        "missing_in_procnet_sample": missing_in_procnet[:10],
        "direct_comparable_split": direct_comparable_split,
        "placement_if_export_and_evaluator_pass": "main-table traditional baseline",
        "placement_if_export_or_evaluator_fails": "appendix/reference-only",
    }


def _load_procnet_doc2edag(path: Path) -> list[dict[str, str]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError(f"{path}: ProcNet view must be a JSON list")
    docs = []
    for index, row in enumerate(payload, 1):
        if isinstance(row, (list, tuple)) and len(row) >= 2:
            doc_id = row[0]
            body = row[1]
        elif isinstance(row, dict):
            doc_id = row.get("doc_id")
            body = row
        else:
            raise ValueError(f"{path}: unsupported ProcNet row at index {index}")
        if not isinstance(body, dict):
            raise ValueError(f"{path}: ProcNet row body must be a mapping at index {index}")
        docs.append({"doc_id": _required_text(doc_id, path=path, index=index), "content": _procnet_content(body)})
    return docs


def _load_evaluator_gold_jsonl(path: Path) -> list[dict[str, str]]:
    docs = []
    with path.open(encoding="utf-8") as handle:
        for index, line in enumerate(handle, 1):
            if not line.strip():
                continue
            row = json.loads(line)
            if not isinstance(row, dict):
                raise ValueError(f"{path}: evaluator row must be a mapping at line {index}")
            docs.append(
                {
                    "doc_id": _required_text(row.get("doc_id"), path=path, index=index),
                    "content": str(row.get("content") or row.get("content_raw") or ""),
                }
            )
    return docs


def _procnet_content(body: dict[str, Any]) -> str:
    sentences = body.get("sentences")
    if isinstance(sentences, list):
        return "\n".join(str(sentence) for sentence in sentences)
    return str(body.get("content") or body.get("content_raw") or "")


def _required_text(value: object, *, path: Path, index: int) -> str:
    text = str(value or "").strip()
    if not text:
        raise ValueError(f"{path}: missing doc_id at row {index}")
    return text


def _normalize_content(text: str) -> str:
    return re.sub(r"\s+", "", text)


def _hash_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _stable_hash(values: Iterable[str]) -> str:
    return _hash_text("\n".join(values))


def _duplicates(values: Sequence[str]) -> list[str]:
    counts = Counter(values)
    return sorted(value for value, count in counts.items() if count > 1)


if __name__ == "__main__":
    raise SystemExit(main())
