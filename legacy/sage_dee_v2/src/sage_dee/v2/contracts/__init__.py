"""Typed SAGE-DEE v2 boundary contracts."""

from sage_dee.v2.contracts.candidate import GeneratedCandidateSet, GeneratedCandidateSetDict, MRSFeatureVector
from sage_dee.v2.contracts.canonical import (
    CANONICAL_ARGUMENT_KEYS,
    CANONICAL_DOCUMENT_KEYS,
    CANONICAL_EVENT_RECORD_KEYS,
    CanonicalArgument,
    CanonicalArgumentDict,
    CanonicalEventRecord,
    CanonicalEventRecordDict,
    CanonicalPredictionDocument,
    CanonicalPredictionDocumentDict,
)
from sage_dee.v2.contracts.run import SageV2RunManifest, SageV2RunManifestDict
from sage_dee.v2.contracts.slot import EventSlotPlan, EventSlotPlanDict
from sage_dee.v2.contracts.surface import SurfaceCandidate, SurfaceCandidateDict, SurfaceMemory, SurfaceMemoryDict

__all__ = [
    "CANONICAL_ARGUMENT_KEYS",
    "CANONICAL_DOCUMENT_KEYS",
    "CANONICAL_EVENT_RECORD_KEYS",
    "CanonicalArgument",
    "CanonicalArgumentDict",
    "CanonicalEventRecord",
    "CanonicalEventRecordDict",
    "CanonicalPredictionDocument",
    "CanonicalPredictionDocumentDict",
    "EventSlotPlan",
    "EventSlotPlanDict",
    "GeneratedCandidateSet",
    "GeneratedCandidateSetDict",
    "MRSFeatureVector",
    "SageV2RunManifest",
    "SageV2RunManifestDict",
    "SurfaceCandidate",
    "SurfaceCandidateDict",
    "SurfaceMemory",
    "SurfaceMemoryDict",
]

