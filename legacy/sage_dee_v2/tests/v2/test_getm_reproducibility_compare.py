from __future__ import annotations

import csv
import json
import subprocess
from pathlib import Path

from tests.v2.subprocess_utils import PYTHON, python_env

REPO_ROOT = Path(__file__).resolve().parents[2]


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )


def _run_fixture(root: Path, *, role: str, accepted_event_count: int) -> None:
    _write_jsonl(root / "prompts.dev.jsonl", [{"doc_id": "doc-1", "prompt": "same prompt"}])
    _write_json(
        root / "generation_manifest.json",
        {
            "generation": {"do_sample": False, "max_new_tokens": 1024},
            "k": 1,
            "backend": "qwen",
        },
    )
    (root / "artifacts").mkdir(parents=True)
    _write_json(
        root / "artifacts" / "backend_manifest.json",
        {"model_path": "/models/qwen", "adapter_path": None, "compute_dtype": "bf16"},
    )
    raw_output = json.dumps(
        {"events": [{"event_type": "EventA", "arguments": {role: ["value"]}}]},
        ensure_ascii=False,
    )
    _write_jsonl(
        root / "raw_outputs.dev.jsonl",
        [
            {
                "candidate_id": "doc-1:getm:0",
                "doc_id": "doc-1",
                "raw_output": raw_output,
                "stopped_output": raw_output,
            }
        ],
    )
    _write_jsonl(
        root / "parsed_candidates.dev.jsonl",
        [
            {
                "candidate_id": "doc-1:getm:0",
                "doc_id": "doc-1",
                "parse_status": "schema_violation" if role == "BadRole" else "ok",
                "diagnostics": {
                    "accepted_event_count": accepted_event_count,
                    "raw_event_count": 1,
                    "schema_violation": 1 if role == "BadRole" else 0,
                    "unknown_role": 1 if role == "BadRole" else 0,
                    "empty_arguments_count": 1 if role == "BadRole" else 0,
                },
                "events": [
                    {
                        "event_type": "EventA",
                        "arguments": {} if role == "BadRole" else {"Role1": [{"text": "value"}]},
                    }
                ],
            }
        ],
    )
    _write_json(
        root / "parse_diagnostics.dev.json",
        {
            "diagnostic_counts": {
                "accepted_event_count": accepted_event_count,
                "raw_event_count": 1,
                "schema_violation": 1 if role == "BadRole" else 0,
                "unknown_role": 1 if role == "BadRole" else 0,
                "empty_arguments_count": 1 if role == "BadRole" else 0,
            },
            "parse_status_counts": {"schema_violation" if role == "BadRole" else "ok": 1},
        },
    )


def test_compare_getm_dev20_reproducibility_reports_invalid_roles_and_sha_diffs(tmp_path: Path) -> None:
    run_a = tmp_path / "run_a"
    run_b = tmp_path / "run_b"
    out_dir = tmp_path / "compare"
    run_a.mkdir()
    run_b.mkdir()
    _run_fixture(run_a, role="Role1", accepted_event_count=1)
    _run_fixture(run_b, role="BadRole", accepted_event_count=0)

    completed = subprocess.run(
        [
            PYTHON,
            str(REPO_ROOT / "scripts/v2/compare_getm_dev20_reproducibility.py"),
            "--run-a",
            str(run_a),
            "--run-b",
            str(run_b),
            "--out-dir",
            str(out_dir),
        ],
        cwd=REPO_ROOT,
        env=python_env(),
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
    summary = json.loads((out_dir / "reproducibility_summary.json").read_text(encoding="utf-8"))
    manifest_diff = json.loads((out_dir / "manifest_diff.json").read_text(encoding="utf-8"))
    per_doc_rows = list(csv.DictReader((out_dir / "per_doc_diff.csv").open(encoding="utf-8")))
    invalid_role_rows = list(csv.DictReader((out_dir / "invalid_roles.csv").open(encoding="utf-8")))

    assert summary["doc_ids_identical"] is True
    assert summary["prompts_sha256_identical"] is True
    assert summary["raw_output_sha_identical_count"] == 0
    assert summary["accepted_event_count_delta"] == -1
    assert summary["schema_subtype_counts_b"]["unknown_role"] == 1
    assert manifest_diff["backend_manifest"]["model_path"]["same"] is True
    assert per_doc_rows[0]["raw_output_sha_equal"] == "False"
    assert per_doc_rows[0]["empty_arguments_b"] == "1"
    assert invalid_role_rows[0]["run"] == "B"
    assert invalid_role_rows[0]["role"] == "BadRole"
    assert invalid_role_rows[0]["event_type"] == "EventA"
