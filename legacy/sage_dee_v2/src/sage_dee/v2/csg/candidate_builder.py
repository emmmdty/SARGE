from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path
from typing import Any

from sage_dee.v2.contracts.surface import SurfaceMemory
from sage_dee.v2.csg.surface_memory import build_surface_memory, surface_memory_to_dict
from sage_dee.v2.data_interface.dataset_loader import V2DatasetDocument
from sage_dee.v2.data_interface.jsonl import write_jsonl


def build_surface_memories(documents: Iterable[V2DatasetDocument]) -> list[SurfaceMemory]:
    return [build_surface_memory(document.input) for document in documents]


def build_surface_memory_records(documents: Iterable[V2DatasetDocument]) -> Iterable[dict[str, Any]]:
    for document in documents:
        yield surface_memory_to_dict(build_surface_memory(document.input))


def write_surface_memory_records(documents: Iterable[V2DatasetDocument], output_path: str | Path) -> Path:
    return write_jsonl(output_path, build_surface_memory_records(documents))
