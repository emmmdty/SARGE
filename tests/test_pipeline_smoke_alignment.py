"""End-to-end pipeline alignment between SARGE and legacy Sage-DEE.

Stages 3 DuEE-Fin documents into SARGE canonical layout, then runs the
full inference pipeline twice — once via ``sarge.pipeline.infer.run_inference``
and once via the legacy ``sage_dee.v2.pipeline.run_v2_smoke.run_v2_smoke``
shipped in ``legacy/sage_dee_v2/src/`` — and asserts the canonical
prediction file is byte-identical between the two implementations.

This is the structural W2 acceptance gate that the refactor preserves
end-to-end inference behaviour. Mode/seed/k/limit are pinned. Both runs
share the same staging dir so the only variable is the pipeline code path.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

from sarge.data.staging import stage_dataset
from sarge.pipeline.infer import run_inference

REPO_ROOT = Path(__file__).resolve().parent.parent
LEGACY_SRC = REPO_ROOT / "legacy" / "sage_dee_v2" / "src"
DEE_FIN_PROCESSED_ROOT = REPO_ROOT.parent / "dee-fin" / "data" / "processed"

if str(LEGACY_SRC) not in sys.path:
    sys.path.insert(0, str(LEGACY_SRC))


@pytest.fixture
def staging_dir(tmp_path: Path) -> Path:
    return tmp_path / "staging"


def _stage(staging: Path, *, train_limit: int = 30, dev_limit: int = 3) -> None:
    stage_dataset(
        dataset="DuEE-Fin-dev500",
        processed_root=DEE_FIN_PROCESSED_ROOT,
        output_root=staging,
        splits=("train",),
        limit=train_limit,
    )
    stage_dataset(
        dataset="DuEE-Fin-dev500",
        processed_root=DEE_FIN_PROCESSED_ROOT,
        output_root=staging,
        splits=("dev",),
        limit=dev_limit,
    )


def _read_predictions(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


@pytest.mark.skipif(
    not (DEE_FIN_PROCESSED_ROOT / "DuEE-Fin-dev500" / "dev.jsonl").is_file(),
    reason="dee-fin DuEE-Fin-dev500 not present",
)
@pytest.mark.skipif(
    not LEGACY_SRC.is_dir(),
    reason="legacy/sage_dee_v2/src not present",
)
def test_sarge_pipeline_matches_legacy_byte_for_byte(staging_dir: Path, tmp_path: Path) -> None:
    """SARGE inference output equals legacy Sage-DEE inference output."""
    _stage(staging_dir, train_limit=30, dev_limit=3)

    sarge_out = tmp_path / "sarge_runs"
    sarge_result = run_inference(
        dataset="DuEE-Fin-dev500",
        split="dev",
        data_root=staging_dir,
        out_root=sarge_out,
        limit=3,
        seed=13,
        k=4,
    )

    from sage_dee.v2.pipeline.run_v2_smoke import run_v2_smoke as legacy_run

    legacy_out = tmp_path / "legacy_runs"
    legacy_result = legacy_run(
        dataset="DuEE-Fin-dev500",
        split="dev",
        data_root=staging_dir,
        out_root=legacy_out,
        limit=3,
        seed=13,
        k=4,
    )

    sarge_rows = _read_predictions(sarge_result.prediction_path)
    legacy_rows = _read_predictions(legacy_result.prediction_path)

    assert len(sarge_rows) == len(legacy_rows) == 3
    for s_row, l_row in zip(sarge_rows, legacy_rows):
        assert s_row == l_row, f"prediction mismatch for doc {s_row.get('doc_id')!r}"
