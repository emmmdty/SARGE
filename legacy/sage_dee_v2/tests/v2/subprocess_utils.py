from __future__ import annotations

import os
import sys
from collections.abc import Mapping
from pathlib import Path

PYTHON = sys.executable


def python_env(overrides: Mapping[str, object] | None = None) -> dict[str, str]:
    env = dict(os.environ)
    if overrides:
        env.update({key: str(value) for key, value in overrides.items()})

    python_dir = str(Path(PYTHON).parent)
    path = env.get("PATH", "")
    env["PYTHON"] = PYTHON
    env["PATH"] = python_dir if not path else f"{python_dir}{os.pathsep}{path}"
    return env

