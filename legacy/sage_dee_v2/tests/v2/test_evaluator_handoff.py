from __future__ import annotations

import ast
from pathlib import Path

from sage_dee.v2.pipeline.evaluator_handoff import build_evaluator_handoff


def test_evaluator_handoff_command_points_to_sibling_artifact_builder(tmp_path: Path) -> None:
    handoff = build_evaluator_handoff(
        run_root=tmp_path / "runs" / "run-1",
        dataset="DuEE-Fin-dev500",
        split="dev",
        data_repo_root=Path("/home/tjk/myProjects/masterProjects/DEE/data"),
        out_dir=tmp_path / "artifacts",
    )

    command = handoff.command
    assert "cd /home/tjk/myProjects/masterProjects/DEE/data" in command
    assert "UV_CACHE_DIR=/tmp/uv-cache uv run python scripts/build_eval_artifacts.py" in command
    assert f"--run_dir {tmp_path / 'runs' / 'run-1'}" in command
    assert "--benchmark_root processed" in command
    assert f"--out_dir {tmp_path / 'artifacts'}" in command
    assert "--profiles unified_main record_level aux_basic paper_tables leaderboard" in command
    assert "--datasets DuEE-Fin-dev500" in command
    assert "--splits dev" in command
    assert "--strict" in command
    assert handoff.argv[:4] == ("uv", "run", "python", "scripts/build_eval_artifacts.py")
    assert "--run_dir" in handoff.argv


def test_evaluator_handoff_does_not_import_sibling_evaluator() -> None:
    path = Path("src/sage_dee/v2/pipeline/evaluator_handoff.py")
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    imported_roots: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_roots.update(alias.name.split(".", 1)[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported_roots.add(node.module.split(".", 1)[0])

    assert imported_roots.isdisjoint({"dee_eval", "dee_contracts", "dee_data"})
