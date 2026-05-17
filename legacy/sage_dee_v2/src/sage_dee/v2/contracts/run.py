from __future__ import annotations

from dataclasses import dataclass, field
from typing import TypedDict

from sage_dee.v2.contracts.canonical import CANONICAL_PREDICTION_FORMAT_VERSION

SAGE_V2_RUN_MANIFEST_VERSION = "sage_dee_v2.run_manifest.v1"


class SageV2RunManifestDict(TypedDict, total=False):
    run_id: str
    dataset_id: str
    split: str
    method_name: str
    manifest_version: str
    prediction_format: str
    canonical_prediction_path: str
    evaluator_run_manifest_path: str
    artifacts: dict[str, str]
    diagnostics: dict[str, str]


@dataclass(frozen=True)
class SageV2RunManifest:
    run_id: str
    dataset_id: str
    split: str
    method_name: str = "sage-dee-v2"
    manifest_version: str = SAGE_V2_RUN_MANIFEST_VERSION
    prediction_format: str = CANONICAL_PREDICTION_FORMAT_VERSION
    canonical_prediction_path: str | None = None
    evaluator_run_manifest_path: str | None = None
    artifacts: dict[str, str] = field(default_factory=dict)
    diagnostics: dict[str, str] = field(default_factory=dict)

