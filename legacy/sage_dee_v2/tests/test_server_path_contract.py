from __future__ import annotations

from pathlib import Path


def test_server_helpers_use_v2_paths_and_external_evaluator() -> None:
    preflight = Path("scripts/server/preflight_4090.sh").read_text(encoding="utf-8")
    evaluator = Path("scripts/server/eval_4090.sh").read_text(encoding="utf-8")
    train = Path("scripts/server/train_4090.sh").read_text(encoding="utf-8")
    predict = Path("scripts/server/predict_4090.sh").read_text(encoding="utf-8")

    assert "/home/TJK/DEE/dee-eval" in evaluator
    assert "EVALUATOR_PYTHON" in evaluator
    assert ".venv/bin/python" in evaluator
    assert "/data/TJK/DEE/data/processed" in evaluator
    assert "/data/TJK/DEE/sage-dee/evaluator_artifacts" in evaluator
    assert "scripts/build_eval_artifacts.py" in evaluator

    assert "sage_dee.v2" in preflight
    assert "/data/TJK/DEE/models/Qwen" in preflight
    assert "scripts/v2/train_getm_qwen.py" in train
    assert "scripts/v2/generate_getm_qwen.py" in predict


def test_server_sync_scripts_use_local_to_remote_mirror_contract() -> None:
    sync = Path("scripts/server/sync_to_4090.sh").read_text(encoding="utf-8")
    fetch = Path("scripts/server/fetch_results_from_4090.sh").read_text(encoding="utf-8")
    gitignore = Path(".gitignore").read_text(encoding="utf-8")

    assert 'MODE="dry-run"' in sync
    assert "--delete" in sync
    assert "scripts/server/preflight_4090.sh" in sync
    assert "--filter=- /.git/" in sync
    assert "--filter=- /data/" in sync
    assert "--filter=- /models/" in sync
    assert "--filter=- /runs/" in sync
    assert "--filter=- /checkpoints/" in sync
    assert "--filter=- /evaluator_artifacts/" in sync
    assert "--filter=- /.mypy_cache/" in sync
    assert "--filter=- /.hypothesis/" in sync
    assert "--filter=- /htmlcov/" in sync
    assert "--filter=- /build/" in sync
    assert "--filter=- /dist/" in sync
    assert "--filter=- /.coverage" in sync
    assert "--filter=- /coverage.xml" in sync
    assert "--filter=- *.egg-info/" in sync
    assert "--filter=- *.log" in sync
    assert "--filter=+ /src/***" in sync
    assert "--filter=+ /tests/***" in sync
    assert "--filter=+ /archive/***" in sync
    assert "git pull" not in sync
    assert "git fetch" not in sync

    assert 'LOCAL_DIR="${2:-server_results}"' in fetch
    assert "SERVER_ARTIFACT_ROOT" in fetch
    assert "git " not in fetch
    assert "server_results/" in gitignore
    assert ".mypy_cache/" in gitignore
    assert ".hypothesis/" in gitignore
    assert "htmlcov/" in gitignore
    assert "build/" in gitignore
    assert "dist/" in gitignore
    assert ".coverage" in gitignore
    assert "coverage.xml" in gitignore
    assert "*.egg-info/" in gitignore
    assert "*.log" in gitignore


def test_old_round_server_scripts_are_archived() -> None:
    for script_name in (
        "run_round4_ablation_4090.sh",
        "run_round5_metric_ladder_4090.sh",
        "run_round6_selector_ladder_4090.sh",
        "run_round7_selector_ladder_4090.sh",
    ):
        assert not Path("scripts/server", script_name).exists()
        assert Path("archive/v1/src/scripts/server", script_name).exists()
