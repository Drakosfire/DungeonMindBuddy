"""Step 2 — canonical statblock + intent classification (Lysandra vertical slice)."""

from __future__ import annotations

import asyncio
import inspect
from typing import Any

import pytest

from evals.lysandra_vertical_slice.step0_corpus_environment import resolve_corpus_dir
from evals.lysandra_vertical_slice.step1_planner_trace import load_planner_step1_scenario
from evals.lysandra_vertical_slice.step1_retrieval import load_corpus_policy
from evals.lysandra_vertical_slice.step2_canonical_intent import (
    build_step2_intent_fixture_sequence_client,
    classify_intent,
    intent_client_for_gold_expect,
    load_step2_gold,
    parse_challenge_rating_from_statblock,
    run_step2_all,
    run_step2_canonical_gates,
    run_step2_intent_fixture_gates,
    evaluate_step2_post_planner_benchmark,
    statblock_trace_reads_matching_policy,
)
from src.npc_statblock_pipeline.canonical_intent import (
    SequenceIntentClassifierClient,
    _INTENT_CLASSIFIER_INSTRUCTIONS,
    _intent_classification_from_payload,
    _resolve_intent_classifier_model,
    classify_intent as classify_intent_src,
    intent_classification_json_schema,
)


def test_step2_gold_parse() -> None:
    g = load_step2_gold()
    assert g.get("required_statblock_markers")
    assert g.get("fixtures")


def test_parse_challenge_rating() -> None:
    text = "Challenge Rating : 4 (1100)\n"
    assert parse_challenge_rating_from_statblock(text) == 4


def test_upgrade_prose_voice_fixture_has_no_benchmark_intent_assertions() -> None:
    """``upgrade_prose`` is a natural-language scenario; Step 2 benchmark must not assert intent."""
    g2 = load_step2_gold()
    keys = (g2.get("planner_bridge") or {}).get("intent_expectations_by_planner_scenario_key") or {}
    assert "upgrade_prose" not in keys


def test_classify_explicit_cr_upgrade() -> None:
    got = classify_intent(
        "Bump Lysandra to CR 5 for the boss fight.",
        client=intent_client_for_gold_expect(
            {
                "intent_mode": "upgrade_request",
                "power_axis": "challenge_rating",
                "clarifier_required": False,
            }
        ),
    )
    assert got.intent_mode == "upgrade_request"
    assert got.power_axis == "challenge_rating"
    assert not got.clarifier_required


def test_classify_ambiguous_upgrade_requires_clarifier() -> None:
    got = classify_intent(
        "I want to level her up before next session.",
        client=intent_client_for_gold_expect(
            {
                "intent_mode": "upgrade_request",
                "power_axis": "unknown",
                "clarifier_required": True,
            }
        ),
    )
    assert got.intent_mode == "upgrade_request"
    assert got.power_axis == "unknown"
    assert got.clarifier_required
    assert got.clarifier_question


def test_step2_intent_fixtures_pass() -> None:
    g2 = load_step2_gold()
    ok, viol = run_step2_intent_fixture_gates(
        step2_gold=g2,
        client=build_step2_intent_fixture_sequence_client(g2),
    )
    assert ok, viol


def test_step2_canonical_gates_on_real_corpus() -> None:
    if not resolve_corpus_dir().is_dir():
        pytest.skip("corpus/eldyrwild-markdown not present")
    detail, ok, viol = run_step2_canonical_gates(resolve_corpus_dir())
    assert detail.get("canonical_path")
    assert detail.get("parsed_challenge_rating") == 4
    assert ok, viol
    sr = detail.get("selection_reason") or {}
    assert sr.get("outcome") == "selected"
    assert sr.get("rule_id") == "corpus_policy.canonical_statblock_relpath"
    em = detail.get("extracted_markdown") or ""
    assert "Challenge Rating" in em
    span = detail.get("extracted_section_span") or {}
    assert span.get("corpus_relative_path") == detail.get("canonical_path")
    assert span.get("end_char") == len(em)
    assert not detail.get("extracted_markdown_truncated")


def test_step2_extract_respects_detail_max_chars() -> None:
    if not resolve_corpus_dir().is_dir():
        pytest.skip("corpus/eldyrwild-markdown not present")
    gold = {**load_step2_gold(), "detail_max_extracted_markdown_chars": 120}
    detail, ok, viol = run_step2_canonical_gates(resolve_corpus_dir(), step2_gold=gold)
    assert ok, viol
    assert detail.get("extracted_markdown_truncated") is True
    assert len(detail.get("extracted_markdown") or "") <= 120
    span = detail.get("extracted_section_span") or {}
    assert span.get("end_char") == len(detail.get("extracted_markdown") or "")


def test_step2_full_on_real_corpus() -> None:
    if not resolve_corpus_dir().is_dir():
        pytest.skip("corpus/eldyrwild-markdown not present")
    g2 = load_step2_gold()
    _, ok, viol = run_step2_all(
        resolve_corpus_dir(),
        step2_gold=g2,
        intent_client=build_step2_intent_fixture_sequence_client(g2),
    )
    assert ok, viol


def test_classify_factual_ac_on_statblock() -> None:
    got = classify_intent(
        "What is Captain Lysandra's Armor Class on her current Mirathorn statblock?",
        client=intent_client_for_gold_expect(
            {
                "intent_mode": "factual_lookup",
                "power_axis": "challenge_rating",
                "clarifier_required": False,
            }
        ),
    )
    assert got.intent_mode == "factual_lookup"
    assert got.power_axis == "challenge_rating"
    assert not got.clarifier_required


def test_classify_increase_challenge_rating_is_upgrade_not_lookup() -> None:
    got = classify_intent(
        "Pull up the context on Lysandra and her latest statblock and timeline, "
        "then increase her challenge rating.",
        client=intent_client_for_gold_expect(
            {
                "intent_mode": "upgrade_request",
                "power_axis": "challenge_rating",
                "clarifier_required": False,
            }
        ),
    )
    assert got.intent_mode == "upgrade_request"
    assert got.power_axis == "challenge_rating"
    assert not got.clarifier_required


def test_classify_regenerate_from_dossier_only() -> None:
    got = classify_intent(
        "Regenerate Lysandra's creature sheet using only the character dossier as input; "
        "do not copy numbers from the old mechanical markdown.",
        client=intent_client_for_gold_expect(
            {
                "intent_mode": "upgrade_request",
                "power_axis": "unknown",
                "clarifier_required": True,
            }
        ),
    )
    assert got.intent_mode == "upgrade_request"
    assert got.power_axis == "unknown"
    assert got.clarifier_required
    assert got.clarifier_question


def test_evaluate_step2_post_planner_benchmark_accepts_canonical_statblock_read() -> None:
    g2 = load_step2_gold()
    bridge = (g2.get("planner_bridge") or {}).get("intent_expectations_by_planner_scenario_key") or {}
    expect = bridge.get("stat_check") or {}
    sc = load_planner_step1_scenario("stat_check")
    ul = str(sc["input"]["user_message"])
    trace = [
        {
            "tool": "read_corpus_file",
            "arguments": {
                "path": "Elderwyld/Cities and Towns/Mirathorn/NPCs/captain_lysandra_ironveil/captain_lysandra_ironveil_statblock_cr4.md",
            },
        }
    ]
    detail, ok, viol = evaluate_step2_post_planner_benchmark(
        user_message=ul,
        tool_trace=trace,
        planner_scenario_key="stat_check",
        intent_client=intent_client_for_gold_expect(expect),
    )
    assert ok, viol
    assert detail.get("intent_from_planner_user_message", {}).get("intent_mode") == "factual_lookup"
    assert detail.get("mechanical_statblock_reads_in_trace")


def test_evaluate_step2_post_planner_benchmark_rejects_non_canonical_statblock_read() -> None:
    g2 = load_step2_gold()
    bridge = (g2.get("planner_bridge") or {}).get("intent_expectations_by_planner_scenario_key") or {}
    expect = bridge.get("stat_check") or {}
    sc = load_planner_step1_scenario("stat_check")
    ul = str(sc["input"]["user_message"])
    trace = [
        {
            "tool": "read_corpus_file",
            "arguments": {
                "path": "Elderwyld/Cities and Towns/Mirathorn/NPCs/captain_lysandra_ironveil/captain_lysandra_ironveil_statblock_cr2.md",
            },
        }
    ]
    _detail, ok, viol = evaluate_step2_post_planner_benchmark(
        user_message=ul,
        tool_trace=trace,
        planner_scenario_key="stat_check",
        intent_client=intent_client_for_gold_expect(expect),
    )
    assert not ok
    assert any("was never opened" in v for v in viol)


def test_evaluate_step2_post_planner_benchmark_allows_archive_statblock_if_canonical_also_read() -> None:
    g2 = load_step2_gold()
    bridge = (g2.get("planner_bridge") or {}).get("intent_expectations_by_planner_scenario_key") or {}
    expect = bridge.get("autonomous") or {}
    sc = load_planner_step1_scenario("autonomous")
    ul = str(sc["input"]["user_message"])
    trace = [
        {
            "tool": "read_corpus_file",
            "arguments": {
                "path": "Elderwyld/Cities and Towns/Mirathorn/NPCs/captain_lysandra_ironveil/captain_lysandra_ironveil_statblock_cr4.md",
            },
        },
        {
            "tool": "read_corpus_file",
            "arguments": {
                "path": "Elderwyld/Cities and Towns/Mirathorn/NPCs/captain_lysandra_ironveil/captain_lysandra_ironveil_statblock_cr2.md",
            },
        },
    ]
    _detail, ok, viol = evaluate_step2_post_planner_benchmark(
        user_message=ul,
        tool_trace=trace,
        planner_scenario_key="autonomous",
        intent_client=intent_client_for_gold_expect(expect),
    )
    assert ok, viol


def test_evaluate_step2_post_planner_benchmark_no_statblock_read_still_ok() -> None:
    g2 = load_step2_gold()
    bridge = (g2.get("planner_bridge") or {}).get("intent_expectations_by_planner_scenario_key") or {}
    expect = bridge.get("autonomous") or {}
    sc = load_planner_step1_scenario("autonomous")
    ul = str(sc["input"]["user_message"])
    trace = [
        {
            "tool": "read_corpus_file",
            "arguments": {
                "path": "Longmont Campaign/Campaign 2/NPCs/captain_lysandra_ironveil/README.md",
            },
        }
    ]
    detail, ok, viol = evaluate_step2_post_planner_benchmark(
        user_message=ul,
        tool_trace=trace,
        planner_scenario_key="autonomous",
        intent_client=intent_client_for_gold_expect(expect),
    )
    assert ok, viol
    assert detail.get("mechanical_statblock_reads_in_trace") == []


def test_statblock_trace_reads_matching_policy_configurable() -> None:
    """Bridge statblock trace matching is driven by corpus_policy, not a hardcoded NPC slug."""
    policy = {
        **load_corpus_policy(),
        "mechanical_statblock_trace_path_filters": {
            "all_substrings_ignore_case": ["torbin_jove/", "torbin_jove_statblock"],
            "path_suffix_ignore_case": ".md",
        },
    }
    paths = [
        "Elderwyld/Cities and Towns/Mirathorn/NPCs/torbin_jove/torbin_jove_statblock.md",
        "Longmont Campaign/Campaign 2/Session Recaps/Session 3 - Recap.md",
    ]
    matched = statblock_trace_reads_matching_policy(paths, policy)
    assert matched == [
        "Elderwyld/Cities and Towns/Mirathorn/NPCs/torbin_jove/torbin_jove_statblock.md"
    ]


def test_generationengine_request_uses_explicit_openai_target(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("NPC_INTENT_CLASSIFIER_MODEL", raising=False)
    user_text = "Bump Lysandra to CR 5 for the boss fight."
    client = intent_client_for_gold_expect(
        {
            "intent_mode": "upgrade_request",
            "power_axis": "challenge_rating",
            "clarifier_required": False,
        }
    )
    classify_intent(user_text, client=client)
    assert len(client.requests) == 1
    request = client.requests[0]
    assert request.provider == "openai"
    assert request.model == "gpt-5.3-codex"
    assert request.profile is None
    assert request.temperature is None
    assert request.system_prompt == _INTENT_CLASSIFIER_INSTRUCTIONS
    assert request.user_prompt == user_text
    assert request.json_schema == intent_classification_json_schema()
    assert request.schema_name == "npc_intent_classification"


def test_explicit_model_override_reaches_generationengine_request() -> None:
    client = intent_client_for_gold_expect(
        {
            "intent_mode": "factual_lookup",
            "power_axis": "unknown",
            "clarifier_required": False,
        }
    )
    classify_intent("What is her AC?", client=client, model="gpt-4o-mini")
    assert client.requests[0].model == "gpt-4o-mini"


def test_env_model_override_reaches_generationengine_request(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("NPC_INTENT_CLASSIFIER_MODEL", "gpt-4o-mini")
    client = intent_client_for_gold_expect(
        {
            "intent_mode": "factual_lookup",
            "power_axis": "unknown",
            "clarifier_required": False,
        }
    )
    classify_intent("What is her AC?", client=client)
    assert client.requests[0].model == "gpt-4o-mini"


def test_policy_model_resolution_still_returns_gpt_53_codex(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("NPC_INTENT_CLASSIFIER_MODEL", raising=False)
    assert _resolve_intent_classifier_model(None) == "gpt-5.3-codex"


def test_wire_schema_validates_types_not_domain_enums() -> None:
    schema = intent_classification_json_schema()
    mode = schema["properties"]["intent_mode"]
    axis = schema["properties"]["power_axis"]
    assert "enum" not in mode
    assert "enum" not in axis
    assert set(mode["type"]) == {"string", "null"}
    assert set(axis["type"]) == {"string", "null"}
    schema["properties"]["intent_mode"]["type"] = ["number"]
    assert intent_classification_json_schema()["properties"]["intent_mode"]["type"] == [
        "string",
        "null",
    ]


def test_missing_and_null_fields_use_buddy_defaults() -> None:
    missing = classify_intent("What is her AC?", client=SequenceIntentClassifierClient([{}]))
    assert missing.intent_mode == "factual_lookup"
    assert missing.power_axis == "unknown"
    assert missing.clarifier_required is False
    assert missing.clarifier_question == ""

    nulls = classify_intent(
        "What is her AC?",
        client=SequenceIntentClassifierClient(
            [
                {
                    "intent_mode": None,
                    "power_axis": None,
                    "clarifier_required": None,
                    "clarifier_question": None,
                }
            ]
        ),
    )
    assert nulls.intent_mode == "factual_lookup"
    assert nulls.power_axis == "unknown"
    assert nulls.clarifier_required is False
    assert nulls.clarifier_question == ""


def test_unknown_domain_values_normalize_in_buddy() -> None:
    got = classify_intent(
        "What is her AC?",
        client=SequenceIntentClassifierClient(
            [
                {
                    "intent_mode": "not_a_known_mode",
                    "power_axis": "something_new",
                    "clarifier_required": False,
                    "clarifier_question": "",
                }
            ]
        ),
    )
    assert got.intent_mode == "factual_lookup"
    assert got.power_axis == "unknown"
    payload = _intent_classification_from_payload(
        {"intent_mode": "not_a_known_mode", "power_axis": "something_new"}
    )
    assert payload.intent_mode == "factual_lookup"
    assert payload.power_axis == "unknown"


def test_clarifier_required_without_question_uses_default() -> None:
    got = classify_intent(
        "I want to level her up before next session.",
        client=SequenceIntentClassifierClient(
            [
                {
                    "intent_mode": "upgrade_request",
                    "power_axis": "unknown",
                    "clarifier_required": True,
                    "clarifier_question": None,
                }
            ]
        ),
    )
    assert got.clarifier_required is True
    assert got.clarifier_question == (
        "Should this use CR-based NPC math, class-style levels, or both?"
    )


def test_non_required_clarifier_clears_question() -> None:
    got = classify_intent(
        "What is her AC?",
        client=SequenceIntentClassifierClient(
            [
                {
                    "intent_mode": "factual_lookup",
                    "power_axis": "challenge_rating",
                    "clarifier_required": False,
                    "clarifier_question": "leftover question",
                }
            ]
        ),
    )
    assert got.clarifier_required is False
    assert got.clarifier_question == ""


def test_blank_input_does_not_call_generationengine() -> None:
    class _Boom:
        async def generate_structured(self, request: Any) -> Any:
            raise AssertionError("blank input must not call GenerationEngine")

    got = classify_intent("   ", client=_Boom())
    assert got.intent_mode == "factual_lookup"
    assert got.power_axis == "unknown"
    assert got.clarifier_required is False
    assert got.clarifier_question == ""


def test_ordinary_synchronous_call_succeeds_without_running_loop() -> None:
    client = intent_client_for_gold_expect(
        {
            "intent_mode": "upgrade_request",
            "power_axis": "challenge_rating",
            "clarifier_required": False,
        }
    )
    got = classify_intent("Bump Lysandra to CR 5 for the boss fight.", client=client)
    assert got.intent_mode == "upgrade_request"
    assert len(client.requests) == 1


def test_synchronous_classifier_succeeds_from_running_event_loop() -> None:
    client = intent_client_for_gold_expect(
        {
            "intent_mode": "upgrade_request",
            "power_axis": "challenge_rating",
            "clarifier_required": False,
        }
    )

    async def _inside_running_loop() -> Any:
        return classify_intent("Bump Lysandra to CR 5 for the boss fight.", client=client)

    got = asyncio.run(_inside_running_loop())
    assert got.intent_mode == "upgrade_request"
    assert len(client.requests) == 1


def test_classifier_does_not_retry_generationengine_failures() -> None:
    class _CountingFailClient:
        def __init__(self) -> None:
            self.calls = 0

        async def generate_structured(self, request: Any) -> Any:
            self.calls += 1
            raise RuntimeError("structured generation failed")

    client = _CountingFailClient()
    with pytest.raises(RuntimeError, match="structured generation failed"):
        classify_intent("What is her AC?", client=client)
    assert client.calls == 1


def test_running_event_loop_raises_original_generationengine_failure() -> None:
    class _FailClient:
        async def generate_structured(self, request: Any) -> Any:
            raise RuntimeError("structured generation failed")

    async def _inside_running_loop() -> Any:
        return classify_intent("What is her AC?", client=_FailClient())

    with pytest.raises(RuntimeError, match="structured generation failed"):
        asyncio.run(_inside_running_loop())


def test_production_path_no_longer_owns_openai_json_parsing() -> None:
    source = inspect.getsource(classify_intent_src)
    assert "json.loads" not in source
    assert "responses.create" not in source
    assert "_strip_json_fence" not in source
    assert "generate_structured" in source
