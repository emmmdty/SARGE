from __future__ import annotations

import ast
from pathlib import Path

V2_ROOT = Path("src/sage_dee/v2")
CONTRACTS_ROOT = V2_ROOT / "contracts"

EXPECTED_PACKAGE_FILES = {
    V2_ROOT / "__init__.py",
    CONTRACTS_ROOT / "__init__.py",
    CONTRACTS_ROOT / "canonical.py",
    CONTRACTS_ROOT / "surface.py",
    CONTRACTS_ROOT / "slot.py",
    CONTRACTS_ROOT / "candidate.py",
    CONTRACTS_ROOT / "run.py",
    V2_ROOT / "data_interface" / "__init__.py",
    V2_ROOT / "csg" / "__init__.py",
    V2_ROOT / "lesp" / "__init__.py",
    V2_ROOT / "getm" / "__init__.py",
    V2_ROOT / "mrs" / "__init__.py",
    V2_ROOT / "pipeline" / "__init__.py",
    V2_ROOT / "diagnostics" / "__init__.py",
}


def _python_files(root: Path) -> list[Path]:
    assert root.exists(), f"missing v2 root: {root}"
    return sorted(root.rglob("*.py"))


def _imported_roots(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    roots: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            roots.update(alias.name.split(".", 1)[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            roots.add(node.module.split(".", 1)[0])
    return roots


def test_sage_v2_package_skeleton_exists() -> None:
    missing = sorted(str(path) for path in EXPECTED_PACKAGE_FILES if not path.exists())
    assert missing == []


def test_sage_v2_does_not_import_sibling_dee_data_or_evaluator() -> None:
    forbidden = {"dee_eval", "dee_data"}
    offenders = {
        str(path): sorted(_imported_roots(path) & forbidden)
        for path in _python_files(V2_ROOT)
        if _imported_roots(path) & forbidden
    }

    assert offenders == {}


def test_sage_v2_contracts_do_not_import_training_stacks() -> None:
    forbidden = {"torch", "transformers", "peft"}
    offenders = {
        str(path): sorted(_imported_roots(path) & forbidden)
        for path in _python_files(CONTRACTS_ROOT)
        if _imported_roots(path) & forbidden
    }

    assert offenders == {}


def test_sage_v2_contracts_do_not_embed_evaluator_or_gold_matching_logic() -> None:
    forbidden_markers = {
        "score_event_records",
        "DocEEArgTableMicroF1",
        "EventRecordExactF1",
        "gold_matching",
        "match_gold",
        "offset_as_gold",
        "gold_offset",
        "span_label",
    }
    offenders: dict[str, list[str]] = {}
    for path in _python_files(CONTRACTS_ROOT):
        source = path.read_text(encoding="utf-8")
        hits = sorted(marker for marker in forbidden_markers if marker in source)
        if hits:
            offenders[str(path)] = hits

    assert offenders == {}


def test_sage_v2_final_canonical_schema_contains_only_surface_prediction_keys() -> None:
    from sage_dee.v2.contracts.canonical import (
        CANONICAL_ARGUMENT_KEYS,
        CANONICAL_DOCUMENT_KEYS,
        CANONICAL_EVENT_RECORD_KEYS,
    )

    assert CANONICAL_DOCUMENT_KEYS == frozenset({"doc_id", "events"})
    assert CANONICAL_EVENT_RECORD_KEYS == frozenset({"event_type", "arguments"})
    assert CANONICAL_ARGUMENT_KEYS == frozenset({"text"})


def test_v2_1_dev_rescue_docs_preserve_frozen_final_boundaries() -> None:
    text = "\n".join(
        (
            Path("AGENTS.md").read_text(encoding="utf-8"),
            Path("docs/refactor/SAGE_V2_1_DEV_RESCUE_PLAN.md").read_text(encoding="utf-8"),
            Path("docs/refactor/SAGE_V2_1_R0_BRANCH_SETUP.md").read_text(encoding="utf-8"),
            Path("docs/refactor/SAGE_V2_1_R5_SINGLE_SEED_RESCUE_DECISION.md").read_text(
                encoding="utf-8"
            ),
            Path("docs/refactor/SAGE_V2_1_NEXT_EXPERIMENT_MATRIX.md").read_text(
                encoding="utf-8"
            ),
        )
    )

    for required in (
        "dev-only",
        "seed42",
        "no test",
        "frozen final test",
        "additional final test",
        "test gold",
        "seed switching",
        "evaluator modification",
        "schema alias mapping",
        "role guessing",
        "event type guessing",
    ):
        assert required in text
