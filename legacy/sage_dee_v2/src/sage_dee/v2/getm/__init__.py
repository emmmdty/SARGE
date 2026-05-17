"""Generative Event Table Model package boundary."""

from sage_dee.v2.getm.candidate_generator import GetmCandidateGenerationOutput, generate_getm_candidate_files
from sage_dee.v2.getm.mock_backend import MockGetmBackend
from sage_dee.v2.getm.parser import candidate_set_to_canonical_prediction, parse_getm_output
from sage_dee.v2.getm.prompt_builder import build_getm_prompt
from sage_dee.v2.getm.sft_dataset import build_getm_sft_sample

__all__ = [
    "GetmCandidateGenerationOutput",
    "MockGetmBackend",
    "build_getm_prompt",
    "build_getm_sft_sample",
    "candidate_set_to_canonical_prediction",
    "generate_getm_candidate_files",
    "parse_getm_output",
]
