from __future__ import annotations

from sarge.models.qwen_backend import _generation_config
from sarge.models.vllm_backend import VllmGetmBackend, _stable_candidate_seed


def _config(*, do_sample: bool = False) -> dict:
    return {
        "run": {"dry_run": False, "real_run": True},
        "getm": {
            "backend": "vllm",
            "output_format": "minimal_text",
            "prompt": {"prompt_token_budget": 4096},
            "qwen": {"model_path": "/tmp/not-loaded"},
            "generation": {
                "k_candidates": 4,
                "max_new_tokens": 1024,
                "do_sample": do_sample,
                "temperature": 0.7 if do_sample else None,
                "top_p": 0.95 if do_sample else 1.0,
                "repetition_penalty": 1.05,
                "use_chat_template": True,
                "use_response_prefix": True,
                "response_prefix": '{"events":',
                "seed": 13,
            },
        },
    }


def test_generation_config_enables_balanced_json_stopping_by_default() -> None:
    generation = _generation_config(_config())
    assert generation["enable_balanced_json_stopping"] is True
    assert generation["stop_after_balanced_events_json"] is True


def test_stable_candidate_seed_is_deterministic_and_candidate_specific() -> None:
    seed_a0 = _stable_candidate_seed(13, "doc-a", 0)
    seed_a0_again = _stable_candidate_seed(13, "doc-a", 0)
    seed_a1 = _stable_candidate_seed(13, "doc-a", 1)
    seed_b0 = _stable_candidate_seed(13, "doc-b", 0)
    assert seed_a0 == seed_a0_again
    assert len({seed_a0, seed_a1, seed_b0}) == 3


def test_sampling_params_use_distinct_per_candidate_seed() -> None:
    class Params:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

    backend = VllmGetmBackend(config=_config(do_sample=True))
    backend._sampling_params_cls = Params
    backend._sampling_common_kwargs = {"max_tokens": 8, "repetition_penalty": 1.05}
    backend._base_seed = 13
    generation = _generation_config(backend.config)

    first = backend._sampling_params_for_prompt(doc_id="doc-a", candidate_index=0, generation_cfg=generation)
    second = backend._sampling_params_for_prompt(doc_id="doc-a", candidate_index=1, generation_cfg=generation)

    assert first.kwargs["seed"] != second.kwargs["seed"]
    assert first.kwargs["temperature"] == 0.7
    assert second.kwargs["top_p"] == 0.95


def test_prefilled_cache_preserves_token_metadata_and_balanced_stop() -> None:
    backend = VllmGetmBackend(config=_config())
    backend._prefilled_outputs[("doc-a", 2)] = {
        "text": '[{"event_type":"质押","arguments":{}}]} trailing text',
        "token_count": 7,
        "ended_with_eos": False,
    }

    output = backend.generate_one(
        prompt="prompt",
        document={"doc_id": "doc-a", "content": "公告文本"},
        schema=None,
        surface_candidates=[],
        slot_plan=None,
        candidate_index=2,
    )

    assert output == '{"events":[{"event_type":"质押","arguments":{}}]}'
    metadata = backend.last_generation_metadata
    assert metadata["generated_token_count"] == 7
    assert metadata["ended_with_eos"] is False
    assert metadata["balanced_stop_applied"] is True
