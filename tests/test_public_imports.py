from __future__ import annotations

import importlib


PUBLIC_MODULES = [
    "sarge",
    "sarge.data.loader",
    "sarge.generation.prompt",
    "sarge.models.mock_backend",
    "sarge.models.qwen_backend",
    "sarge.models.vllm_backend",
    "sarge.pipeline.infer",
    "sarge.pipeline.latency",
    "sarge.selection.selector",
    "evaluator.cli",
    "evaluator.role_f1.metric",
]


def test_public_modules_import_without_server_dependencies() -> None:
    failures: list[str] = []
    for module_name in PUBLIC_MODULES:
        try:
            importlib.import_module(module_name)
        except Exception as exc:  # noqa: BLE001
            failures.append(f"{module_name}: {type(exc).__name__}: {exc}")
    assert failures == []
