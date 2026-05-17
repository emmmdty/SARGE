from __future__ import annotations

import json
import subprocess
import types
from pathlib import Path

import pytest

from sage_dee.io_utils import read_yaml
from scripts.v2.run_phase6_sft_baseline_matrix import _release_qwen_backend, _select_gpu, _validate_args, parse_args
from tests.v2.subprocess_utils import PYTHON, python_env

REPO_ROOT = Path(__file__).resolve().parents[2]
CONFIG = REPO_ROOT / "configs/v2/S1-S4/sage_v2_phase6_sft_baselines.yaml"
RUNNER = REPO_ROOT / "scripts/v2/run_phase6_sft_baseline_matrix.py"
AGGREGATOR = REPO_ROOT / "scripts/v2/aggregate_phase6_sft_baseline_matrix.py"
REPORT = REPO_ROOT / "docs/refactor/SAGE_V2_PHASE6_SFT_BASELINE_MATRIX_S1_S4.md"
STATE = REPO_ROOT / "docs/refactor/SAGE_V2_EXECUTION_STATE.md"


def test_phase6_config_freezes_sft_matrix_and_high_throughput_batch() -> None:
    config = read_yaml(CONFIG)

    assert config["phase6"]["train_limit"] == 512
    assert config["phase6"]["full_train_used"] is False
    assert config["phase6"]["test_blocked"] is True
    assert config["phase6"]["preferred_gpu"] == "3"
    assert config["phase6"]["auto_select_idle_gpu"] is True
    assert config["phase6"]["seed_matrix"] == {
        "S1": [42, 43],
        "S2": [42, 43],
        "S3": [42, 43],
        "S4": [42, 43, 44],
    }

    training = config["getm"]["qwen"]["training"]
    assert training["micro_batch_size"] == 1
    assert training["gradient_accumulation"] == 16
    assert config["training_budget"]["micro_batch_size"] == 1
    assert config["training_budget"]["gradient_accumulation_steps"] == 16
    assert config["training_budget"]["max_train_steps"] is None

    expected_profiles = {
        "phase6_s1_direct_json": "direct_json",
        "phase6_s2_schema_only": "schema_only",
        "phase6_s3_role_safe": "role_safe",
        "phase6_s4_role_safe_surface_memory": "role_safe_surface_memory",
    }
    assert set(config["profiles"]) == set(expected_profiles)
    for profile_name, baseline_mode in expected_profiles.items():
        profile = config["profiles"][profile_name]
        assert profile["getm"]["prompt"]["baseline_mode"] == baseline_mode
        generation = profile["getm"]["generation"]
        assert generation["do_sample"] is False
        assert generation["temperature"] is None
        assert generation["top_p"] == 1.0
        assert generation["deterministic"] is True
        assert generation["deterministic_warn_only"] is True
        assert generation["record_resolved_generation_config"] is True


def test_phase6_runner_dry_run_writes_guarded_limit50_summary(tmp_path: Path) -> None:
    out_root = tmp_path / "phase6"
    completed = subprocess.run(
        [
            PYTHON,
            str(RUNNER),
            "--config",
            str(CONFIG),
            "--stage",
            "limit50",
            "--dry-run",
            "--allow-limit50",
            "--skip-evaluator",
            "--allow-partial-dry-run",
            "--only-baseline",
            "S1",
            "--only-seed",
            "42",
            "--out-root",
            str(out_root),
        ],
        cwd=REPO_ROOT,
        env=python_env({"SAGE_DEE_PHASE6_FAKE_NVIDIA_SMI": "3,0,0\n0,7000,90\n"}),
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
    matrix = json.loads((out_root / "phase6_matrix_summary.json").read_text(encoding="utf-8"))

    assert matrix["scope"]["stage"] == "limit50"
    assert matrix["scope"]["train_limit"] == 512
    assert matrix["scope"]["full_train_used"] is False
    assert matrix["scope"]["full_dev_used"] is False
    assert matrix["scope"]["test_used"] is False
    assert matrix["gpu_selection"]["selected_gpu"] == "3"
    assert matrix["gate"]["all_runs_completed"] is True
    assert matrix["gate"]["full_dev_allowed"] is False

    assert len(matrix["runs"]) == 1
    run = matrix["runs"][0]
    assert run["baseline_id"] == "S1"
    assert run["seed"] == 42
    assert run["train"]["train_rows"] == 512
    assert run["limit50"]["canonical_rows"] == 50
    assert run["limit50"]["evaluator_attempted"] is False
    assert Path(run["run_dir"]).name.startswith("phase6_S1_seed42_")
    command = json.loads((Path(run["run_dir"]) / "train" / "phase6_train_command.json").read_text(encoding="utf-8"))
    assert command["env"]["CUDA_VISIBLE_DEVICES"] == "3"
    assert command["env"]["PYTORCH_CUDA_ALLOC_CONF"] == "expandable_segments:True"


def test_phase6_runner_rejects_forbidden_scopes(tmp_path: Path) -> None:
    test_split = subprocess.run(
        [
            PYTHON,
            str(RUNNER),
            "--config",
            str(CONFIG),
            "--stage",
            "limit50",
            "--dry-run",
            "--allow-limit50",
            "--split",
            "test",
            "--out-root",
            str(tmp_path / "test-split"),
        ],
        cwd=REPO_ROOT,
        env=python_env(),
        check=False,
        capture_output=True,
        text=True,
    )
    assert test_split.returncode != 0
    assert "test split" in test_split.stderr

    full_dev_without_gate = subprocess.run(
        [
            PYTHON,
            str(RUNNER),
            "--config",
            str(CONFIG),
            "--stage",
            "full-dev",
            "--dry-run",
            "--out-root",
            str(tmp_path / "full-dev"),
        ],
        cwd=REPO_ROOT,
        env=python_env(),
        check=False,
        capture_output=True,
        text=True,
    )
    assert full_dev_without_gate.returncode != 0
    assert "--allow-full-dev" in full_dev_without_gate.stderr

    partial_real = subprocess.run(
        [
            PYTHON,
            str(RUNNER),
            "--config",
            str(CONFIG),
            "--stage",
            "limit50",
            "--real-run",
            "--allow-limit50",
            "--allow-partial-dry-run",
            "--only-baseline",
            "S1",
            "--out-root",
            str(tmp_path / "partial-real"),
        ],
        cwd=REPO_ROOT,
        env=python_env(),
        check=False,
        capture_output=True,
        text=True,
    )
    assert partial_real.returncode != 0
    assert "partial matrix selection requires" in partial_real.stderr

    shard_args = parse_args(
        [
            "--config",
            str(CONFIG),
            "--stage",
            "limit50",
            "--real-run",
            "--allow-limit50",
            "--allow-real-partial-shard",
            "--only-baseline",
            "S4",
            "--only-seed",
            "44",
            "--force-gpu",
            "2",
            "--matrix-summary-name",
            "phase6_matrix_summary.gpu2.json",
            "--out-root",
            str(tmp_path / "real-shard"),
        ]
    )
    config = read_yaml(CONFIG)
    _validate_args(shard_args, config)
    assert _select_gpu(config, force_gpu=shard_args.force_gpu)["selected_gpu"] == "2"


def test_phase6_runner_releases_generation_backend_cuda_cache() -> None:
    class FakeCuda:
        empty_called = False
        ipc_called = False

        @staticmethod
        def is_available() -> bool:
            return True

        @classmethod
        def empty_cache(cls) -> None:
            cls.empty_called = True

        @classmethod
        def ipc_collect(cls) -> None:
            cls.ipc_called = True

    class FakeModel:
        moved_to: str | None = None

        def to(self, device: str) -> None:
            self.moved_to = device

    model = FakeModel()
    backend = types.SimpleNamespace(
        _runtime=types.SimpleNamespace(torch=types.SimpleNamespace(cuda=FakeCuda), model=model)
    )

    _release_qwen_backend(backend)  # type: ignore[arg-type]

    assert backend._runtime is None
    assert model.moved_to == "cpu"
    assert FakeCuda.empty_called is True
    assert FakeCuda.ipc_called is True


def test_phase6_aggregator_computes_mean_std_and_parse_valid_gate(tmp_path: Path) -> None:
    root = tmp_path / "runs"
    root.mkdir()
    rows = [
        ("S1", 42, 0.10, 0.11, 0.0, 0.10, 0.11),
        ("S1", 43, 0.20, 0.21, 0.0, 0.20, 0.21),
        ("S2", 42, 0.12, 0.13, 0.0, 0.12, 0.13),
        ("S2", 43, 0.13, 0.14, 0.0, 0.13, 0.14),
        ("S3", 42, 0.14, 0.15, 0.0, 0.14, 0.15),
        ("S3", 43, 0.15, 0.16, 0.0, 0.15, 0.16),
        ("S4", 42, 0.25, 0.30, 0.1, 0.28, 0.31),
        ("S4", 43, 0.27, 0.32, 0.1, 0.29, 0.33),
        ("S4", 44, 0.29, 0.34, 0.1, 0.30, 0.35),
    ]
    for baseline_id, seed, full_f1, role_f1, exact_f1, pv_f1, pv_role_f1 in rows:
        run_dir = root / f"phase6_{baseline_id}_seed{seed}_20260504T000000Z"
        run_dir.mkdir()
        payload = {
            "baseline_id": baseline_id,
            "seed": seed,
            "run_dir": str(run_dir),
            "full_dev": {
                "event_table_micro_f1": full_f1,
                "role_level_f1": role_f1,
                "exact_record_f1": exact_f1,
                "parse_valid_subset": {
                    "event_table_micro_f1": pv_f1,
                    "role_level_f1": pv_role_f1,
                    "exact_record_f1": exact_f1,
                    "doc_count": 400,
                },
            },
            "scope": {"test_used": False, "full_train_used": False},
        }
        (run_dir / "phase6_run_summary.json").write_text(
            json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    stale_dir = root / "phase6_S1_seed42_20260503T000000Z"
    stale_dir.mkdir()
    stale_payload = {
        "baseline_id": "S1",
        "seed": 42,
        "run_dir": str(stale_dir),
        "full_dev": {
            "event_table_micro_f1": 0.90,
            "role_level_f1": 0.90,
            "exact_record_f1": 0.90,
            "parse_valid_subset": {
                "event_table_micro_f1": 0.90,
                "role_level_f1": 0.90,
                "exact_record_f1": 0.90,
                "doc_count": 400,
            },
        },
        "scope": {"test_used": False, "full_train_used": False},
    }
    (stale_dir / "phase6_run_summary.json").write_text(
        json.dumps(stale_payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    out_path = tmp_path / "aggregate.json"
    completed = subprocess.run(
        [
            PYTHON,
            str(AGGREGATOR),
            "--runs-root",
            str(root),
            "--stage",
            "full_dev",
            "--out-json",
            str(out_path),
        ],
        cwd=REPO_ROOT,
        env=python_env(),
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
    aggregate = json.loads(out_path.read_text(encoding="utf-8"))
    assert aggregate["gate"]["s4_not_below_s1_s2"] is True
    assert aggregate["gate"]["parse_valid_subset_improved"] is True
    assert aggregate["gate"]["parse_only_improvement"] is False
    assert aggregate["by_baseline"]["S4"]["seed_count"] == 3
    assert aggregate["by_baseline"]["S4"]["event_table_micro_f1"]["mean"] == pytest.approx(0.27)
    assert aggregate["by_baseline"]["S1"]["seed_count"] == 2
    assert aggregate["by_baseline"]["S1"]["event_table_micro_f1"]["mean"] == pytest.approx(0.15)


def test_phase6_report_and_execution_state_record_runtime_scope() -> None:
    report = REPORT.read_text(encoding="utf-8")
    state = STATE.read_text(encoding="utf-8")

    for required in (
        "Phase 6 completed on server",
        "S1 direct JSON SFT",
        "S2 schema-only SFT",
        "S3 role-safe SFT",
        "S4 role-safe + surface memory SFT",
        "train_limit=512",
        "micro_batch_size=1",
        "gradient_accumulation=16",
        "resource-only failure before evaluation",
        "GPU3 or least-busy idle GPU",
        "full dev: completed only after limit50 gate passed",
        "test: blocked",
        "parse-only improvement is not extraction improvement",
    ):
        assert required in report

    assert "phase6_sft_baseline_matrix_local_engineering: implemented" in state
    server_runtime = "phase6_sft_baseline_matrix_server_runtime"
    assert f"{server_runtime}: completed" in state
    assert "phase6_sft_baseline_matrix_gate: passed" in state
    assert "phase7_surface_memory_ablation: allowed" in state
    assert "test remains blocked: YES" in state
