from __future__ import annotations

import ast
import os
import re
import sys
from pathlib import Path

from tests.v2.subprocess_utils import PYTHON, python_env

REPO_ROOT = Path(__file__).resolve().parents[2]
CODE_ROOTS = (REPO_ROOT / "tests", REPO_ROOT / "scripts", REPO_ROOT / "src")
SHELL_LIKE_PYTHON = re.compile(r"(^|\$\()python(?=\s)")


def test_python_env_prefers_current_interpreter() -> None:
    env = python_env({"PATH": os.defpath})

    assert PYTHON == sys.executable
    assert env["PYTHON"] == sys.executable
    assert env["PATH"].split(os.pathsep)[0] == str(Path(sys.executable).parent)


def test_no_subprocess_call_starts_bare_python() -> None:
    offenders: list[str] = []
    for path in _python_files():
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call) or not _is_subprocess_call(node):
                continue
            if node.args and _starts_bare_python(node.args[0]):
                offenders.append(f"{path.relative_to(REPO_ROOT)}:{node.lineno}")
            if any(keyword.arg == "shell" and _literal_true(keyword.value) for keyword in node.keywords):
                offenders.append(f"{path.relative_to(REPO_ROOT)}:{node.lineno}: shell=True")

    assert offenders == []


def test_no_shell_like_bare_python_commands_remain() -> None:
    offenders: list[str] = []
    for path in _python_files() + _shell_files():
        for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            if SHELL_LIKE_PYTHON.search(line.strip()):
                offenders.append(f"{path.relative_to(REPO_ROOT)}:{lineno}:{line.strip()}")

    assert offenders == []


def _python_files() -> list[Path]:
    return sorted(path for root in CODE_ROOTS for path in root.rglob("*.py"))


def _shell_files() -> list[Path]:
    return sorted((REPO_ROOT / "scripts").rglob("*.sh"))


def _is_subprocess_call(node: ast.Call) -> bool:
    func = node.func
    return (
        isinstance(func, ast.Attribute)
        and func.attr in {"run", "check_call", "check_output", "Popen"}
        and isinstance(func.value, ast.Name)
        and func.value.id == "subprocess"
    )


def _starts_bare_python(node: ast.AST) -> bool:
    return (
        isinstance(node, ast.List)
        and bool(node.elts)
        and isinstance(node.elts[0], ast.Constant)
        and node.elts[0].value == "python"
    )


def _literal_true(node: ast.AST) -> bool:
    return isinstance(node, ast.Constant) and node.value is True
