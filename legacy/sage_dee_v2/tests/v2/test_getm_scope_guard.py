from __future__ import annotations

from pathlib import Path

import pytest

from sage_dee.io_utils import read_yaml
from sage_dee.v2.getm.scope_guard import validate_getm_prediction_scope

REPO_ROOT = Path(__file__).resolve().parents[2]
FROZEN_CONFIG = REPO_ROOT / "configs/v2/sage_v2_getm_format_stable.yaml"


def test_format_stable_config_freezes_f1_profile() -> None:
    config = read_yaml(FROZEN_CONFIG)

    assert config["run"]["profile"] == "getm_format_stable_dev20_f1"
    assert config["run"]["dry_run"] is False
    assert config["run"]["real_run"] is False
    assert config["predict"]["split"] == "dev"
    assert config["predict"]["max_predict_docs"] == 20
    assert config["getm"]["output_format"] == "minimal_text"
    assert config["getm"]["prompt"] == {
        "max_surface_candidates": 10,
        "candidate_context_chars": 0,
        "candidate_render_mode": "compact",
        "enable_candidate_filtering": True,
        "max_candidates_per_type": 6,
        "dedupe_surface_candidates": True,
        "drop_low_value_company_fragments": True,
        "prompt_token_budget": 4096,
        "fail_on_prompt_token_limit": False,
    }
    assert config["getm"]["generation"]["k_candidates"] == 1
    assert config["getm"]["generation"]["use_response_prefix"] is True
    assert config["getm"]["generation"]["response_prefix"] == '{"events":'
    assert config["getm"]["generation"]["enable_balanced_json_stopping"] is True
    assert config["getm"]["generation"]["stop_after_balanced_events_json"] is True
    assert config["getm"]["generation"]["max_new_tokens"] == 1024
    assert config["getm"]["generation"]["do_sample"] is False
    assert config["getm"]["generation"]["temperature"] is None
    assert config["getm"]["generation"]["top_p"] == 1.0


def test_prediction_scope_guard_rejects_test_full_dev_and_large_limit_by_default() -> None:
    config = read_yaml(FROZEN_CONFIG)

    with pytest.raises(ValueError, match="test split"):
        validate_getm_prediction_scope(
            config_path=FROZEN_CONFIG,
            config=config,
            profile="getm_format_stable_dev20_f1",
            split="test",
            limit=20,
        )
    with pytest.raises(ValueError, match="full dev"):
        validate_getm_prediction_scope(
            config_path=FROZEN_CONFIG,
            config=config,
            profile="getm_format_stable_dev20_f1",
            split="dev",
            limit=None,
        )
    with pytest.raises(ValueError, match="limit > 20"):
        validate_getm_prediction_scope(
            config_path=FROZEN_CONFIG,
            config=config,
            profile="getm_format_stable_dev20_f1",
            split="dev",
            limit=50,
        )


def test_prediction_scope_guard_only_allows_limit50_for_frozen_profile_with_flag() -> None:
    frozen = read_yaml(FROZEN_CONFIG)
    smoke_config = read_yaml(REPO_ROOT / "configs/v2/sage_v2_smoke.yaml")

    validate_getm_prediction_scope(
        config_path=FROZEN_CONFIG,
        config=frozen,
        profile="getm_format_stable_dev20_f1",
        split="dev",
        limit=50,
        allow_limit50=True,
    )

    with pytest.raises(ValueError, match="frozen format-stable"):
        validate_getm_prediction_scope(
            config_path=REPO_ROOT / "configs/v2/sage_v2_smoke.yaml",
            config=smoke_config,
            profile="local_dry_run",
            split="dev",
            limit=50,
            allow_limit50=True,
        )
    with pytest.raises(ValueError, match="exactly 50"):
        validate_getm_prediction_scope(
            config_path=FROZEN_CONFIG,
            config=frozen,
            profile="getm_format_stable_dev20_f1",
            split="dev",
            limit=21,
            allow_limit50=True,
        )
