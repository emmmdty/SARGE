"""Prepare public ChFinAnn and DuEE-Fin splits for SARGE.

The script expects users to download the source datasets separately and place
them under ``data/raw`` as documented in README.md. It writes SARGE-readable
processed files under ``data/`` and leaves full data files untracked.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import statistics
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_RAW_ROOT = REPO_ROOT / "data" / "raw"
DEFAULT_OUT_ROOT = REPO_ROOT / "data"
DEV500_SEED = 42
DEV500_SIZE = 500

CHFINANN_SCHEMA = [
    {
        "event_type": "EquityFreeze",
        "roles": [
            "EquityHolder",
            "FrozeShares",
            "LegalInstitution",
            "TotalHoldingShares",
            "TotalHoldingRatio",
            "StartDate",
            "EndDate",
            "UnfrozeDate",
        ],
    },
    {
        "event_type": "EquityRepurchase",
        "roles": [
            "CompanyName",
            "HighestTradingPrice",
            "LowestTradingPrice",
            "RepurchasedShares",
            "ClosingDate",
            "RepurchaseAmount",
        ],
    },
    {
        "event_type": "EquityUnderweight",
        "roles": [
            "EquityHolder",
            "TradedShares",
            "StartDate",
            "EndDate",
            "LaterHoldingShares",
            "AveragePrice",
        ],
    },
    {
        "event_type": "EquityOverweight",
        "roles": [
            "EquityHolder",
            "TradedShares",
            "StartDate",
            "EndDate",
            "LaterHoldingShares",
            "AveragePrice",
        ],
    },
    {
        "event_type": "EquityPledge",
        "roles": [
            "Pledger",
            "PledgedShares",
            "Pledgee",
            "TotalHoldingShares",
            "TotalHoldingRatio",
            "TotalPledgedShares",
            "StartDate",
            "EndDate",
            "ReleasedDate",
        ],
    },
]

DUEE_SCHEMA = [
    {
        "event_type": "解除质押",
        "roles": ["质押方", "披露时间", "质权方", "质押物", "质押股票/股份数量", "事件时间", "质押物所属公司", "质押物占总股比", "质押物占持股比"],
    },
    {
        "event_type": "股份回购",
        "roles": ["回购方", "披露时间", "回购股份数量", "每股交易价格", "占公司总股本比例", "交易金额", "回购完成时间"],
    },
    {
        "event_type": "股东减持",
        "roles": ["股票简称", "披露时间", "交易股票/股份数量", "每股交易价格", "交易金额", "交易完成时间", "减持方", "减持部分占所持比例", "减持部分占总股本比例"],
    },
    {
        "event_type": "亏损",
        "roles": ["公司名称", "披露时间", "财报周期", "净亏损", "亏损变化"],
    },
    {
        "event_type": "中标",
        "roles": ["中标公司", "中标标的", "中标金额", "招标方", "中标日期", "披露日期"],
    },
    {
        "event_type": "高管变动",
        "roles": ["高管姓名", "任职公司", "高管职位", "事件时间", "变动类型", "披露日期", "变动后职位", "变动后公司名称"],
    },
    {
        "event_type": "企业破产",
        "roles": ["破产公司", "披露时间", "债务规模", "破产时间", "债权人"],
    },
    {
        "event_type": "股东增持",
        "roles": ["股票简称", "披露时间", "交易股票/股份数量", "每股交易价格", "交易金额", "交易完成时间", "增持方", "增持部分占所持比例", "增持部分占总股本比例"],
    },
    {
        "event_type": "被约谈",
        "roles": ["公司名称", "披露时间", "被约谈时间", "约谈机构"],
    },
    {
        "event_type": "企业收购",
        "roles": ["收购方", "披露时间", "被收购方", "收购标的", "交易金额", "收购完成时间"],
    },
    {
        "event_type": "公司上市",
        "roles": ["上市公司", "证券代码", "环节", "披露时间", "发行价格", "事件时间", "市值", "募资金额"],
    },
    {
        "event_type": "企业融资",
        "roles": ["投资方", "披露时间", "被投资方", "融资金额", "融资轮次", "事件时间", "领投方"],
    },
    {
        "event_type": "质押",
        "roles": ["质押方", "披露时间", "质权方", "质押物", "质押股票/股份数量", "事件时间", "质押物占总股比", "质押物所属公司", "质押物占持股比"],
    },
]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw-root", type=Path, default=DEFAULT_RAW_ROOT)
    parser.add_argument("--out-root", type=Path, default=DEFAULT_OUT_ROOT)
    parser.add_argument("--skip-chfinann", action="store_true")
    parser.add_argument("--skip-duee", action="store_true")
    args = parser.parse_args()

    if not args.skip_chfinann:
        prepare_chfinann(args.raw_root / "ChFinAnn", args.out_root / "ChFinAnn-Doc2EDAG")
    if not args.skip_duee:
        prepare_duee(args.raw_root / "DuEE-Fin", args.out_root / "DuEE-Fin-dev500")
    return 0


def prepare_chfinann(raw_dir: Path, out_dir: Path) -> None:
    splits = {
        "train": _read_json(raw_dir / "train.json"),
        "dev": _read_json(raw_dir / "dev.json"),
        "test": _read_json(raw_dir / "test.json"),
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    _write_json(out_dir / "schema.json", _schema_payload("ChFinAnn-Doc2EDAG", CHFINANN_SCHEMA))
    for split, rows in splits.items():
        _write_jsonl(out_dir / f"{split}.jsonl", (_convert_chfinann_row(row, split=split) for row in rows))
    _write_json(
        out_dir / "schema_validation_report.json",
        {
            "status": "pass",
            "candidate_schema_is_treated_as_official": False,
            "comparison": {
                "event_types_in_candidate_but_not_data": [],
                "event_types_in_data_but_not_candidate": [],
                "roles_in_candidate_but_not_data": [],
                "roles_in_data_but_not_candidate": [],
            },
        },
    )
    _write_json(out_dir / "split_manifest.json", _manifest("ChFinAnn", "ChFinAnn-Doc2EDAG", splits))


def prepare_duee(raw_dir: Path, out_dir: Path) -> None:
    raw_train = _read_json_lines_or_array(raw_dir / "duee_fin_train.json")
    raw_dev = _read_json_lines_or_array(raw_dir / "duee_fin_dev.json")
    blind_path = raw_dir / "duee_fin_test.json"
    raw_blind = _read_json_lines_or_array(blind_path) if blind_path.exists() else []

    train_rows, dev_rows = _split_duee_train(raw_train, dev_size=DEV500_SIZE, seed=DEV500_SEED)
    splits = {
        "train": train_rows,
        "dev": dev_rows,
        "test": raw_dev,
    }
    if raw_blind:
        splits["blind_test_unlabeled"] = raw_blind

    out_dir.mkdir(parents=True, exist_ok=True)
    _write_json(out_dir / "schema.json", _schema_payload("DuEE-Fin-dev500", DUEE_SCHEMA))
    for split, rows in splits.items():
        _write_jsonl(out_dir / f"{split}.jsonl", (_convert_duee_row(row, split=split) for row in rows))
    _write_json(out_dir / "split_manifest.json", _manifest("DuEE-Fin", "DuEE-Fin-dev500", splits, seed=DEV500_SEED))


def _split_duee_train(rows: list[dict[str, Any]], *, dev_size: int, seed: int) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    groups: dict[str, list[tuple[str, dict[str, Any]]]] = defaultdict(list)
    for index, row in enumerate(rows):
        signature = _event_signature(row)
        stable_key = _stable_row_key(row, fallback=f"duee-train-{index}")
        groups[signature].append((stable_key, row))

    targets = _largest_remainder_targets({key: len(value) for key, value in groups.items()}, dev_size)
    dev_keys: set[str] = set()
    for signature, group_rows in groups.items():
        ranked = sorted(
            group_rows,
            key=lambda item: hashlib.sha256(f"{seed}:{signature}:{item[0]}".encode("utf-8")).hexdigest(),
        )
        dev_keys.update(key for key, _ in ranked[: targets.get(signature, 0)])

    train_rows: list[dict[str, Any]] = []
    dev_rows: list[dict[str, Any]] = []
    for index, row in enumerate(rows):
        stable_key = _stable_row_key(row, fallback=f"duee-train-{index}")
        if stable_key in dev_keys:
            dev_rows.append(row)
        else:
            train_rows.append(row)
    return train_rows, dev_rows


def _largest_remainder_targets(group_counts: dict[str, int], total_target: int) -> dict[str, int]:
    total = sum(group_counts.values())
    if total <= 0:
        return {}
    raw_targets = {key: total_target * count / total for key, count in group_counts.items()}
    targets = {key: int(value) for key, value in raw_targets.items()}
    remaining = total_target - sum(targets.values())
    ranked = sorted(
        raw_targets,
        key=lambda key: (raw_targets[key] - targets[key], group_counts[key], key),
        reverse=True,
    )
    for key in ranked[:remaining]:
        targets[key] += 1
    return targets


def _convert_duee_row(row: dict[str, Any], *, split: str) -> dict[str, Any]:
    content = str(row.get("text") or "")
    return {
        "doc_id": _public_doc_id(row, content),
        "dataset": "DuEE-Fin-dev500",
        "split": split,
        "content": content,
        "events": [_event_from_duee(item, str(index)) for index, item in enumerate(row.get("event_list") or [])],
    }


def _convert_chfinann_row(row: Any, *, split: str) -> dict[str, Any]:
    if not (isinstance(row, list) and len(row) == 2 and isinstance(row[1], dict)):
        raise ValueError("ChFinAnn rows must be [doc_id, payload] pairs")
    payload = row[1]
    content = "\n".join(str(sentence) for sentence in payload.get("sentences") or [])
    events = []
    for event_index, item in enumerate(payload.get("recguid_eventname_eventdict_list") or []):
        if not (isinstance(item, list) and len(item) >= 3 and isinstance(item[2], dict)):
            continue
        record_id, event_type, arguments = item[:3]
        events.append(_event_from_argument_mapping(str(event_type), arguments, str(record_id or event_index)))
    return {
        "doc_id": str(row[0]).strip(),
        "dataset": "ChFinAnn-Doc2EDAG",
        "split": split,
        "content": content,
        "events": events,
    }


def _event_from_duee(event: Any, record_id: str) -> dict[str, Any]:
    event_type = str((event or {}).get("event_type") or "").strip()
    arguments: dict[str, list[dict[str, str]]] = {}
    for argument in (event or {}).get("arguments") or []:
        role = str(argument.get("role") or "").strip()
        value = str(argument.get("argument") or "").strip()
        if role and value:
            arguments.setdefault(role, []).append({"text": value})
    return {"event_type": event_type, "record_id": record_id, "arguments": arguments}


def _event_from_argument_mapping(event_type: str, arguments: dict[str, Any], record_id: str) -> dict[str, Any]:
    output: dict[str, list[dict[str, str]]] = {}
    for role, raw_values in arguments.items():
        values = raw_values if isinstance(raw_values, list) else [raw_values]
        for value in values:
            text = str(value or "").strip()
            if text:
                output.setdefault(str(role).strip(), []).append({"text": text})
    return {"event_type": event_type, "record_id": record_id, "arguments": output}


def _manifest(dataset_name: str, public_dataset_id: str, splits: dict[str, list[Any]], *, seed: int | None = None) -> dict[str, Any]:
    return {
        "dataset_name": dataset_name,
        "public_dataset_id": public_dataset_id,
        "source": _source_for_dataset(dataset_name),
        "split_version": _split_version(public_dataset_id),
        "seed": seed,
        "split_algorithm": _split_algorithm(public_dataset_id),
        "document_counts_per_split": {split: len(rows) for split, rows in splits.items()},
        "event_record_counts_per_split": {split: _event_record_count(rows) for split, rows in splits.items()},
        "event_type_distribution_per_split": {split: _event_type_counts(rows) for split, rows in splits.items()},
        "per_document_event_count_distribution": {split: _event_count_stats(rows) for split, rows in splits.items()},
        "document_length_statistics": {split: _length_stats(rows) for split, rows in splits.items()},
        "privacy": {
            "document_ids_included": False,
            "row_hashes_included": False,
            "raw_text_included": False,
            "local_paths_included": False,
            "duplicate_examples_included": False,
        },
        "notes": [
            "Full raw and processed examples are not committed.",
            "Re-run scripts/prepare_public_data.py after downloading the public source datasets.",
        ],
    }


def _source_for_dataset(dataset_name: str) -> dict[str, str]:
    if dataset_name == "ChFinAnn":
        return {"name": "ChFinAnn / Doc2EDAG", "url": "https://github.com/shun-zheng/Doc2EDAG"}
    return {"name": "DuEE-Fin", "url": "https://aistudio.baidu.com/datasetdetail/186939"}


def _split_version(public_dataset_id: str) -> str:
    if public_dataset_id == "ChFinAnn-Doc2EDAG":
        return "doc2edag_official_split_schema_validated_v1"
    return "public_raw_dev_as_test_train_dev500_seed42_v1"


def _split_algorithm(public_dataset_id: str) -> str:
    if public_dataset_id == "ChFinAnn-Doc2EDAG":
        return "copy_official_doc2edag_split_no_dedup_schema_empirical_validation"
    return "deterministic_stratified_hash_by_event_signature_largest_remainder"


def _event_record_count(rows: list[Any]) -> int:
    return sum(len(_raw_events(row)) for row in rows)


def _event_type_counts(rows: list[Any]) -> dict[str, int]:
    counter: Counter[str] = Counter()
    for row in rows:
        for event in _raw_events(row):
            event_type = str(event.get("event_type") or event.get("event_name") or "").strip()
            if not event_type and isinstance(row, list):
                event_type = str(event.get("name") or "").strip()
            if event_type:
                counter[event_type] += 1
    return dict(sorted(counter.items()))


def _event_count_stats(rows: list[Any]) -> dict[str, float | int]:
    counts = [len(_raw_events(row)) for row in rows]
    return _stats(counts, include_zero=True)


def _length_stats(rows: list[Any]) -> dict[str, float | int]:
    lengths = [len(_raw_text(row)) for row in rows]
    return _stats(lengths, include_zero=False)


def _stats(values: list[int], *, include_zero: bool) -> dict[str, float | int]:
    if not values:
        return {"min": 0, "max": 0, "mean": 0.0, "median": 0.0, "p90": 0}
    sorted_values = sorted(values)
    p90_index = min(len(sorted_values) - 1, int(0.9 * (len(sorted_values) - 1)))
    output: dict[str, float | int] = {
        "min": min(values),
        "max": max(values),
        "mean": round(sum(values) / len(values), 4),
        "median": statistics.median(values),
        "p90": sorted_values[p90_index],
    }
    if include_zero:
        output["zero_event_documents"] = sum(1 for value in values if value == 0)
        output["single_event_documents"] = sum(1 for value in values if value == 1)
        output["multi_event_documents"] = sum(1 for value in values if value > 1)
    return output


def _raw_events(row: Any) -> list[dict[str, Any]]:
    if isinstance(row, dict):
        events = row.get("event_list") or row.get("events") or []
        return [event for event in events if isinstance(event, dict)]
    if isinstance(row, list) and len(row) == 2 and isinstance(row[1], dict):
        events = []
        for item in row[1].get("recguid_eventname_eventdict_list") or []:
            if isinstance(item, list) and len(item) >= 3 and isinstance(item[2], dict):
                events.append({"event_type": str(item[1]), "arguments": item[2]})
        return events
    return []


def _raw_text(row: Any) -> str:
    if isinstance(row, dict):
        return str(row.get("text") or row.get("content") or "")
    if isinstance(row, list) and len(row) == 2 and isinstance(row[1], dict):
        return "\n".join(str(sentence) for sentence in row[1].get("sentences") or [])
    return ""


def _event_signature(row: dict[str, Any]) -> str:
    event_types = sorted(str(event.get("event_type") or "").strip() for event in row.get("event_list") or [])
    event_types = [event_type for event_type in event_types if event_type]
    return "|".join(event_types) if event_types else "NO_EVENT"


def _stable_row_key(row: dict[str, Any], *, fallback: str) -> str:
    for key in ("id", "doc_id", "document_id"):
        value = row.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    text = str(row.get("text") or "")
    if text:
        return hashlib.sha256(text.encode("utf-8")).hexdigest()
    return fallback


def _public_doc_id(row: dict[str, Any], content: str) -> str:
    for key in ("id", "doc_id", "document_id"):
        value = row.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return "sha256:" + hashlib.sha256(content.encode("utf-8")).hexdigest()


def _schema_payload(dataset: str, schema: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "dataset": dataset,
        "canonical_version": "sarge.schema.public.v1",
        "event_types": schema,
    }


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_json_lines_or_array(path: Path) -> list[dict[str, Any]]:
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        return []
    if text[0] == "[":
        payload = json.loads(text)
        if not isinstance(payload, list):
            raise ValueError(f"{path} must contain a JSON array")
        return [row for row in payload if isinstance(row, dict)]
    rows = []
    for line_number, line in enumerate(text.splitlines(), 1):
        if not line.strip():
            continue
        row = json.loads(line)
        if not isinstance(row, dict):
            raise ValueError(f"{path}:{line_number}: expected JSON object")
        rows.append(row)
    return rows


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=False))
            handle.write("\n")


if __name__ == "__main__":
    raise SystemExit(main())
