from __future__ import annotations

import json
import subprocess
from pathlib import Path

from tests.v2.subprocess_utils import PYTHON, python_env

REPO_ROOT = Path(__file__).resolve().parents[2]
RUNNER = REPO_ROOT / "scripts/v2/run_s4_full_method_test_reference.py"
FINAL_RESULT = REPO_ROOT / "docs/refactor/SAGE_V2_FINAL_TEST_RESULT.json"


def test_runner_requires_explicit_methodology_reference_flag(tmp_path: Path) -> None:
    config, data_root, source_row_root = _write_reference_inputs(tmp_path)

    completed = _run_runner(
        "--config",
        str(config),
        "--dataset",
        "DuEE-Fin-dev500",
        "--split",
        "test",
        "--data-root",
        str(data_root),
        "--source-row-root",
        str(source_row_root),
        "--out-dir",
        str(tmp_path / "out"),
        "--backend",
        "mock",
    )

    assert completed.returncode == 2
    assert "requires --branch-methodology-reference" in completed.stderr


def test_runner_rejects_non_r3_row_d_adapter(tmp_path: Path) -> None:
    config, data_root, source_row_root = _write_reference_inputs(tmp_path)
    wrong_adapter = (
        tmp_path
        / "runs"
        / "phase6_S4_seed42_20260504T052553Z"
        / "train"
        / "artifacts"
        / "model"
        / "adapter"
    )
    wrong_adapter.mkdir(parents=True)

    completed = _run_runner(
        "--config",
        str(config),
        "--dataset",
        "DuEE-Fin-dev500",
        "--split",
        "test",
        "--data-root",
        str(data_root),
        "--source-row-root",
        str(source_row_root),
        "--adapter-path",
        str(wrong_adapter),
        "--out-dir",
        str(tmp_path / "out"),
        "--backend",
        "mock",
        "--branch-methodology-reference",
    )

    assert completed.returncode == 2
    assert "must match R3 Row D adapter" in completed.stderr


def test_runner_generates_mock_shard_manifest_without_mutating_final_result(tmp_path: Path) -> None:
    config, data_root, source_row_root = _write_reference_inputs(tmp_path)
    out_dir = (
        tmp_path
        / "methodology_checks"
        / "s4_full_method_test_reference_seed42_unit"
        / "shards"
        / "shard_00_of_02"
    )
    before = FINAL_RESULT.read_text(encoding="utf-8")

    completed = _run_runner(
        "--config",
        str(config),
        "--dataset",
        "DuEE-Fin-dev500",
        "--split",
        "test",
        "--data-root",
        str(data_root),
        "--source-row-root",
        str(source_row_root),
        "--out-dir",
        str(out_dir),
        "--backend",
        "mock",
        "--mock-mode",
        "empty",
        "--num-shards",
        "2",
        "--shard-index",
        "0",
        "--branch-methodology-reference",
    )

    assert completed.returncode == 0, completed.stderr
    assert FINAL_RESULT.read_text(encoding="utf-8") == before

    manifest = json.loads((out_dir / "generation_manifest.json").read_text(encoding="utf-8"))
    run_manifest = json.loads((out_dir / "run_manifest.json").read_text(encoding="utf-8"))
    canonical_rows = _read_jsonl(out_dir / "predictions" / "DuEE-Fin-dev500" / "test.canonical.pred.jsonl")

    assert manifest["source_row"] == "s4_full_or_max_frozen_surface"
    assert manifest["methodology_reference"] is True
    assert manifest["formal_metric"] is False
    assert manifest["frozen_final_result"] is False
    assert manifest["phase13_reinterpretation"] is False
    assert manifest["gold_visible"] is False
    assert manifest["test_gold_read_by_generation"] is False
    assert manifest["shard"]["num_shards"] == 2
    assert manifest["shard"]["shard_index"] == 0
    assert manifest["source_train_limit"] == 6474
    assert run_manifest["adapter_path"] == str(source_row_root / "train" / "artifacts" / "model" / "adapter")
    assert len(canonical_rows) == 2


def test_merge_shards_writes_merged_run_root_and_rejects_missing_docs(tmp_path: Path) -> None:
    config, data_root, source_row_root = _write_reference_inputs(tmp_path)
    out_root = tmp_path / "methodology_checks" / "s4_full_method_test_reference_seed42_unit"
    shard0 = out_root / "shards" / "shard_00_of_02"
    shard1 = out_root / "shards" / "shard_01_of_02"
    _write_shard_prediction(shard0, ["doc-0", "doc-2"])
    _write_shard_prediction(shard1, ["doc-1", "doc-3"])

    completed = _run_runner(
        "--config",
        str(config),
        "--dataset",
        "DuEE-Fin-dev500",
        "--split",
        "test",
        "--data-root",
        str(data_root),
        "--source-row-root",
        str(source_row_root),
        "--out-dir",
        str(out_root / "merged"),
        "--merge-shards",
        "--shard-dirs",
        str(shard0),
        str(shard1),
        "--branch-methodology-reference",
    )

    assert completed.returncode == 0, completed.stderr
    merged_rows = _read_jsonl(out_root / "merged" / "predictions" / "DuEE-Fin-dev500" / "test.canonical.pred.jsonl")
    manifest = json.loads((out_root / "merged" / "generation_manifest.json").read_text(encoding="utf-8"))

    assert [row["doc_id"] for row in merged_rows] == ["doc-0", "doc-1", "doc-2", "doc-3"]
    assert manifest["merged_shards"] is True
    assert manifest["document_count"] == 4
    assert manifest["gold_visible"] is False
    assert manifest["test_gold_read_by_generation"] is False


def _run_runner(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [PYTHON, str(RUNNER), *args],
        cwd=REPO_ROOT,
        env=python_env({"PYTHONPATH": str(REPO_ROOT)}),
        check=False,
        capture_output=True,
        text=True,
    )


def _write_reference_inputs(tmp_path: Path) -> tuple[Path, Path, Path]:
    data_root = tmp_path / "data"
    dataset_dir = data_root / "DuEE-Fin-dev500"
    dataset_dir.mkdir(parents=True)
    schema = {
        "dataset": "DuEE-Fin-dev500",
        "event_types": [
            {
                "event_type": "股份回购",
                "roles": ["回购方", "交易金额"],
            }
        ],
    }
    (dataset_dir / "schema.json").write_text(json.dumps(schema, ensure_ascii=False) + "\n", encoding="utf-8")
    rows = [
        {
            "doc_id": f"doc-{index}",
            "dataset": "DuEE-Fin-dev500",
            "split": "test",
            "content": f"甲公司拟回购 {index}",
            "events": [],
        }
        for index in range(4)
    ]
    (dataset_dir / "test.jsonl").write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows),
        encoding="utf-8",
    )

    config = tmp_path / "config.yaml"
    config.write_text(
        """
version: unit-test
test_enabled: false
allow_test: false
data:
  dataset: DuEE-Fin-dev500
  data_root: data
getm:
  backend: qwen
  output_format: minimal_text
  prompt:
    baseline_mode: role_safe_surface_memory
    max_surface_candidates: 2
  qwen:
    adapter_path: null
  generation:
    k_candidates: 1
    seed: 42
    do_sample: false
    top_p: 1.0
    use_response_prefix: true
    response_prefix: '{"events":'
    prompt_delimiter: "### RESPONSE_JSON"
resource_monitor:
  enabled: false
""".lstrip(),
        encoding="utf-8",
    )

    source_row_root = tmp_path / "runs" / "v21_r3_s4_train_size_scaling_seed42" / "s4_full_or_max_frozen_surface"
    adapter = source_row_root / "train" / "artifacts" / "model" / "adapter"
    adapter.mkdir(parents=True)
    (adapter / "adapter_config.json").write_text("{}\n", encoding="utf-8")
    (source_row_root / "row_summary.json").write_text(
        json.dumps(
            {
                "row_id": "s4_full_or_max_frozen_surface",
                "seed": 42,
                "dataset": "DuEE-Fin-dev500",
                "split": "dev",
                "train_limit": 6474,
                "adapter_path": str(adapter),
                "test_run": False,
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    return config, data_root, source_row_root


def _write_shard_prediction(shard_dir: Path, doc_ids: list[str]) -> None:
    prediction = shard_dir / "predictions" / "DuEE-Fin-dev500" / "test.canonical.pred.jsonl"
    prediction.parent.mkdir(parents=True)
    rows = [{"doc_id": doc_id, "events": []} for doc_id in doc_ids]
    prediction.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8")
    (shard_dir / "generation_manifest.json").write_text(
        json.dumps(
            {
                "source_row": "s4_full_or_max_frozen_surface",
                "dataset": "DuEE-Fin-dev500",
                "split": "test",
                "canonical_predictions_path": str(prediction),
                "gold_visible": False,
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )


def _read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
