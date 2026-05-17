from __future__ import annotations

from sage_dee.v2.mrs.pairwise_data import build_pairwise_rows


def test_pairwise_rows_prefer_higher_reward_candidates() -> None:
    reward_rows = [
        {"doc_id": "doc-1", "candidate_id": "a", "reward": 0.9, "metric_source": "local"},
        {"doc_id": "doc-1", "candidate_id": "b", "reward": 0.2, "metric_source": "local"},
    ]
    feature_rows = [
        {"doc_id": "doc-1", "candidate_id": "a", "features": {"role_coverage": 1.0}},
        {"doc_id": "doc-1", "candidate_id": "b", "features": {"role_coverage": 0.0}},
    ]

    pairs = build_pairwise_rows(reward_rows, feature_rows, min_delta=0.01)

    assert pairs == [
        {
            "doc_id": "doc-1",
            "preferred_candidate_id": "a",
            "rejected_candidate_id": "b",
            "preferred_reward": 0.9,
            "rejected_reward": 0.2,
            "reward_delta": 0.7,
            "preferred_features": {"role_coverage": 1.0},
            "rejected_features": {"role_coverage": 0.0},
            "metric_source": "local",
        }
    ]


def test_pairwise_rows_skip_ties_within_min_delta() -> None:
    reward_rows = [
        {"doc_id": "doc-1", "candidate_id": "a", "reward": 0.9, "metric_source": "local"},
        {"doc_id": "doc-1", "candidate_id": "b", "reward": 0.895, "metric_source": "local"},
    ]
    feature_rows = [
        {"doc_id": "doc-1", "candidate_id": "a", "features": {}},
        {"doc_id": "doc-1", "candidate_id": "b", "features": {}},
    ]

    assert build_pairwise_rows(reward_rows, feature_rows, min_delta=0.01) == []
