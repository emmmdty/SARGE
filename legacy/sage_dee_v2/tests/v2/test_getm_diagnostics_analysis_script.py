from __future__ import annotations

import json
import subprocess
from pathlib import Path

from sage_dee.v2.data_interface.jsonl import read_jsonl
from tests.v2.subprocess_utils import PYTHON, python_env

REPO_ROOT = Path(__file__).resolve().parents[2]


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows),
        encoding="utf-8",
    )


def test_analyze_getm_generation_diagnostics_enriches_existing_artifacts(tmp_path: Path) -> None:
    raw_outputs = tmp_path / "raw_outputs.dev.jsonl"
    prompts = tmp_path / "prompts.dev.jsonl"
    parsed_candidates = tmp_path / "parsed_candidates.dev.jsonl"
    generation_manifest = tmp_path / "generation_manifest.json"
    config_resolved = tmp_path / "config.resolved.yaml"
    canonical_predictions = tmp_path / "dev.canonical.pred.jsonl"
    out_dir = tmp_path / "diagnostics"

    _write_jsonl(
        raw_outputs,
        [
            {
                "candidate_id": "doc-1:getm:0",
                "doc_id": "doc-1",
                "candidate_index": 0,
                "raw_output": "- id=doc-1:csg:abc | text=value | chunk=chunk_0000 | context=value",
                "generated_token_count": 3,
                "generated_token_count_source": "retokenized_raw_output_approx",
            }
        ],
    )
    _write_jsonl(
        prompts,
        [
            {
                "doc_id": "doc-1",
                "prompt": "prompt text",
                "surface_candidates": [{"candidate_id": "doc-1:csg:abc"}],
            }
        ],
    )
    _write_jsonl(
        parsed_candidates,
        [
            {
                "candidate_id": "doc-1:getm:0",
                "doc_id": "doc-1",
                "parse_status": "parse_error",
                "generation_score": None,
                "slot_plan_ids": [],
                "diagnostics": {"parse_error": 1},
                "events": [],
            }
        ],
    )
    generation_manifest.write_text(
        json.dumps({"generation": {"max_new_tokens": 3}, "k": 1}, ensure_ascii=False),
        encoding="utf-8",
    )
    config_resolved.write_text("getm:\n  generation:\n    max_new_tokens: 3\n", encoding="utf-8")
    _write_jsonl(canonical_predictions, [{"doc_id": "doc-1", "events": []}])

    completed = subprocess.run(
        [
            PYTHON,
            str(REPO_ROOT / "scripts/v2/analyze_getm_generation_diagnostics.py"),
            "--raw-outputs",
            str(raw_outputs),
            "--prompts",
            str(prompts),
            "--parsed-candidates",
            str(parsed_candidates),
            "--generation-manifest",
            str(generation_manifest),
            "--config-resolved",
            str(config_resolved),
            "--canonical-predictions",
            str(canonical_predictions),
            "--dataset",
            "unit",
            "--split",
            "dev",
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
    enhanced_raw = read_jsonl(out_dir / "raw_outputs.dev.enhanced.jsonl")
    enhanced_parsed = read_jsonl(out_dir / "parsed_candidates.dev.enhanced.jsonl")
    diagnostics = json.loads((out_dir / "parse_diagnostics.dev.json").read_text(encoding="utf-8"))
    validation = json.loads((out_dir / "validation_summary.json").read_text(encoding="utf-8"))

    assert enhanced_raw[0]["candidate_line_copy_count"] == 1
    assert enhanced_raw[0]["hit_max_new_tokens"] is True
    assert enhanced_parsed[0]["diagnostics"]["parse_error_primary_subtype"] == "candidate_list_continuation"
    assert diagnostics["parse_error_subtype_counts"] == {
        "candidate_list_continuation": 1,
        "no_json_started": 1,
        "truncated_or_hit_max_new_tokens": 1,
    }
    assert validation["forbidden_key_violation_count"] == 0
    assert validation["project_canonical_schema_error_count"] == 0
