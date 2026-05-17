from __future__ import annotations

import json
import subprocess
from pathlib import Path

from tests.v2.subprocess_utils import PYTHON, python_env

REPO_ROOT = Path(__file__).resolve().parents[2]


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def test_role_safe_diagnostics_counts(tmp_path: Path) -> None:
    prompts_path = tmp_path / "prompts.dev.jsonl"
    targets_path = tmp_path / "targets.dev.jsonl"
    canonical_path = tmp_path / "canonical.dev.jsonl"
    parsed_path = tmp_path / "parsed.dev.jsonl"
    out_dir = tmp_path / "audit"

    _write_jsonl(
        prompts_path,
        [{"doc_id": "doc-1", "prompt": 'shape {"events":[{"event_type":"EventA","arguments":{"role":["..."]}}]}'}],
    )
    _write_jsonl(
        targets_path,
        [{"doc_id": "doc-1", "output": {"events": [{"event_type": "EventA", "arguments": {"Role1": ["x"]}}]}}],
    )
    _write_jsonl(
        canonical_path,
        [
            {
                "doc_id": "doc-1",
                "events": [
                    {
                        "event_type": "EventA",
                        "arguments": {"Role1": [{"text": "x", "source_candidate_id": "cand-1"}]},
                    }
                ],
            }
        ],
    )
    _write_jsonl(
        parsed_path,
        [
            {
                "doc_id": "doc-1",
                "parse_status": "schema_violation",
                "diagnostics": {"unknown_role": 2, "unknown_event_type": 1, "schema_violation": 3},
            }
        ],
    )

    completed = subprocess.run(
        [
            PYTHON,
            str(REPO_ROOT / "scripts/v2/audit_role_safe_contract.py"),
            "--dataset",
            "unit",
            "--split",
            "dev",
            "--prompts",
            str(prompts_path),
            "--targets",
            str(targets_path),
            "--canonical",
            str(canonical_path),
            "--parsed-candidates",
            str(parsed_path),
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
    summary = json.loads((out_dir / "role_safe_audit.dev.json").read_text(encoding="utf-8"))
    assert summary["literal_role_argument_key_occurrences"] == 1
    assert summary["artifact_counts"]["prompts"]["literal_role_argument_key_occurrences"] == 1
    assert summary["artifact_counts"]["targets"]["literal_role_argument_key_occurrences"] == 0
    assert summary["unknown_role_count"] == 2
    assert summary["unknown_event_type_count"] == 1
    assert summary["schema_violation_count"] == 3
    assert summary["forbidden_key_violation_count"] == 1
    assert (out_dir / "prompt_sample.dev.txt").is_file()
    assert (out_dir / "target_sample.dev.json").is_file()
    assert (out_dir / "canonical_sample.dev.json").is_file()
