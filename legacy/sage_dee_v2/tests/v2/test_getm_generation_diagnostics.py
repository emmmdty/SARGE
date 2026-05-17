from __future__ import annotations

from sage_dee.v2.getm.generation_diagnostics import build_generation_diagnostics


def test_candidate_line_continuation_raw_output_is_classified() -> None:
    raw_output = (
        "=doc-1:csg:333333333333 | text=1.102% | chunk=chunk_0001 | context=prefix\n"
        "- id=doc-1:csg:000000000000 | text=18,394,427股 | chunk=chunk_0001 | context=body\n"
        "- id=doc-1:csg:000000000001 | text=191,821,211.70元 | chunk=chunk_0001 | context=body"
    )

    diagnostics = build_generation_diagnostics(
        raw_output=raw_output,
        prompt="",
        surface_candidate_count=40,
        max_new_tokens=1024,
    )

    assert diagnostics["candidate_line_copy_count"] == 3
    assert diagnostics["candidate_id_copy_count"] == 3
    assert diagnostics["starts_with_candidate_fragment"] == 1
    assert diagnostics["parse_error_subtypes"] == ["no_json_started", "candidate_list_continuation"]
    assert diagnostics["parse_error_primary_subtype"] == "candidate_list_continuation"


def test_instruction_loop_raw_output_is_classified() -> None:
    sentence = "The text field must not contain any extra characters or whitespace."
    raw_output = "\n".join(
        [
            "The event type must match the schema.",
            sentence,
            sentence,
            sentence,
            sentence,
        ]
    )

    diagnostics = build_generation_diagnostics(
        raw_output=raw_output,
        prompt="",
        surface_candidate_count=0,
        max_new_tokens=1024,
    )

    assert diagnostics["starts_with_instruction_text"] == 1
    assert diagnostics["instruction_sentence_copy_count"] == 5
    assert diagnostics["instruction_loop_count"] == 3
    assert diagnostics["parse_error_subtypes"] == ["no_json_started", "instruction_loop"]
    assert diagnostics["parse_error_primary_subtype"] == "instruction_loop"


def test_top_level_array_sets_array_start_and_array_continuation_subtype() -> None:
    diagnostics = build_generation_diagnostics(
        raw_output='[{"event_type":"EventA","arguments":{}}]}',
        prompt="",
        surface_candidate_count=1,
        max_new_tokens=1024,
    )

    assert diagnostics["starts_with_json_object"] == 0
    assert diagnostics["starts_with_json_array"] == 1
    assert diagnostics["brace_balance_state"] == "malformed_or_extra_closer"
    assert diagnostics["parse_error_subtypes"] == ["array_continuation_not_reconstructed", "malformed_json"]


def test_hit_max_new_tokens_can_be_approximated_from_retokenized_output() -> None:
    diagnostics = build_generation_diagnostics(
        raw_output="alpha beta gamma",
        prompt="one two",
        surface_candidate_count=0,
        max_new_tokens=3,
        generated_token_count=3,
        generated_token_count_source="retokenized_raw_output_approx",
        prompt_token_count=2,
        prompt_token_count_source="retokenized_prompt_approx",
    )

    assert diagnostics["prompt_token_count"] == 2
    assert diagnostics["generated_token_count"] == 3
    assert diagnostics["hit_max_new_tokens"] is True
    assert diagnostics["hit_max_new_tokens_source"] == "retokenized_raw_output_approx"
    assert diagnostics["generated_token_count_source"] == "retokenized_raw_output_approx"
    assert diagnostics["parse_error_subtypes"] == ["no_json_started", "truncated_or_hit_max_new_tokens"]


def test_prompt_token_limit_hit_and_section_breakdown_are_recorded() -> None:
    diagnostics = build_generation_diagnostics(
        raw_output='{"events":[]}',
        prompt="prompt text",
        surface_candidate_count=2,
        max_new_tokens=1024,
        prompt_token_count=4096,
        prompt_token_count_source="generation_input_ids_exact",
        prompt_token_budget=4096,
        prompt_section_char_counts={
            "schema": 10,
            "document": 20,
            "candidates": 30,
            "instruction": 40,
        },
        prompt_section_token_counts={
            "schema": 1,
            "document": 2,
            "candidates": 3,
            "instruction": 4,
        },
    )

    assert diagnostics["prompt_token_budget"] == 4096
    assert diagnostics["prompt_token_limit_hit"] is True
    assert diagnostics["prompt_section_char_counts"] == {
        "schema": 10,
        "document": 20,
        "candidates": 30,
        "instruction": 40,
    }
    assert diagnostics["prompt_section_token_counts"] == {
        "schema": 1,
        "document": 2,
        "candidates": 3,
        "instruction": 4,
    }


def test_prompt_packing_contract_diagnostics_are_recorded() -> None:
    diagnostics = build_generation_diagnostics(
        raw_output='{"events":[]}',
        prompt="prompt text",
        surface_candidate_count=2,
        max_new_tokens=1024,
        prompt_token_count=4096,
        prompt_token_count_source="generation_input_ids_exact",
        prompt_token_budget=4096,
        full_prompt_token_count=4141,
        prompt_packing_strategy="middle_truncate_keep_prefix_suffix",
        prompt_middle_token_drop_count=45,
        prompt_delimiter_present_after_packing=True,
        response_prefix_present_after_packing=True,
    )

    assert diagnostics["full_prompt_token_count"] == 4141
    assert diagnostics["prompt_packing_strategy"] == "middle_truncate_keep_prefix_suffix"
    assert diagnostics["prompt_middle_token_drop_count"] == 45
    assert diagnostics["prompt_delimiter_present_after_packing"] is True
    assert diagnostics["response_prefix_present_after_packing"] is True
