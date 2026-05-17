"""Metric-trained Reward Selector package boundary."""

from sage_dee.v2.mrs.features import FEATURE_NAMES, compute_candidate_features, compute_feature_rows
from sage_dee.v2.mrs.oracle_gap import compute_oracle_gap_rows, summarize_oracle_gap
from sage_dee.v2.mrs.pairwise_data import build_pairwise_rows
from sage_dee.v2.mrs.reward import METRIC_SOURCE, compute_candidate_reward, compute_reward_rows
from sage_dee.v2.mrs.selector import MRSSelectionResult, select_candidate_rows
from sage_dee.v2.mrs.simple_ranker import load_model, save_model, score_with_model, train_ranker

__all__ = [
    "FEATURE_NAMES",
    "METRIC_SOURCE",
    "MRSSelectionResult",
    "build_pairwise_rows",
    "compute_candidate_features",
    "compute_candidate_reward",
    "compute_feature_rows",
    "compute_oracle_gap_rows",
    "compute_reward_rows",
    "load_model",
    "save_model",
    "score_with_model",
    "select_candidate_rows",
    "summarize_oracle_gap",
    "train_ranker",
]
