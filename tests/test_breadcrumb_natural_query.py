from __future__ import annotations

from pathlib import Path

from evals.sentence_routing_retrieval_falsification.breadcrumb_query_grader import (
    grade_natural_scenario,
    load_gold,
    natural_retrieval_bundle,
)
from evals.sentence_routing_retrieval_falsification.breadcrumb_semantic_similarity import (
    cosine_similarity,
    embedding_cost_usd,
)


def test_grade_natural_scenario_passes_on_synthetic_hit_context() -> None:
    records = [
        {
            "schema": "dmb_session_memory_record_v1",
            "campaign_id": "longmont-c2",
            "session_number": 20,
            "unit_id": "U-test-lysandra-001",
            "lexical_plain": "Captain Lysandra ties the voices tower clue to her sheet after the migrating forest.",
            "routes": [
                {
                    "normalized_route": "Longmont Campaign/Campaign 2/NPCs/captain_lysandra_ironveil/",
                    "subject_class": "npc",
                    "proposed": False,
                }
            ],
            "source_recap_path": "Longmont Campaign/Campaign 2/Session Recaps/Session 20 - Recap.md",
            "line_start": 1,
            "line_end": 1,
        }
    ]
    scenario = {
        "id": "synthetic_natural",
        "campaign_id": "longmont-c2",
        "query_spec": {
            "query": "What happened to the captain after the migrating forest pulled back?",
            "session_min": 20,
            "session_max": 20,
            "max_hits": 12,
        },
        "must_hit_tokens": ["captain", "forest"],
        "stale_tokens": [],
        "expect_route_substrings": ["captain_lysandra_ironveil"],
        "min_context_support_ratio": 0.67,
        "update_signal_tokens": [],
    }
    out = grade_natural_scenario(records=records, scenario=scenario)
    assert out["ok"] is True
    assert out["violations"] == []
    assert out["semantic_verdict"] == "pass_updated"


def test_grade_natural_llm_answer_bypasses_hit_context_semantic() -> None:
    """LLM path must not fail retrieval-context semantic when the answer satisfies rubric."""
    records = [
        {
            "schema": "dmb_session_memory_record_v1",
            "campaign_id": "longmont-c2",
            "session_number": 20,
            "unit_id": "U-test-lysandra-001",
            "lexical_plain": "Captain Lysandra ties the voices tower clue to her sheet after the migrating forest.",
            "routes": [
                {
                    "normalized_route": "Longmont Campaign/Campaign 2/NPCs/captain_lysandra_ironveil/",
                    "subject_class": "npc",
                    "proposed": False,
                }
            ],
            "source_recap_path": "Longmont Campaign/Campaign 2/Session Recaps/Session 20 - Recap.md",
            "line_start": 1,
            "line_end": 1,
        }
    ]
    scenario = {
        "id": "synthetic_natural_llm",
        "campaign_id": "longmont-c2",
        "query_spec": {
            "query": "What happened to the captain after the migrating forest pulled back?",
            "session_min": 20,
            "session_max": 20,
            "max_hits": 12,
        },
        "must_hit_tokens": ["captain", "forest"],
        "stale_tokens": [],
        "expect_route_substrings": ["captain_lysandra_ironveil"],
        "min_context_support_ratio": 0.67,
        "update_signal_tokens": [],
    }
    bundle = natural_retrieval_bundle(records=records, scenario=scenario)
    out = grade_natural_scenario(
        records=records,
        scenario=scenario,
        llm_answer=(
            "After the migrating forest episode, Captain Lysandra is still in play and the recap ties "
            "her to forest-adjacent beats and tower-related clues."
        ),
        cached_retrieval=bundle,
    )
    assert out["grading_mode"] == "natural_retrieval_context+llm"
    assert out["ok"] is True
    assert out["llm_semantic_verdict"] == "pass_updated"


def test_grade_natural_llm_answer_fails_negated_required_token() -> None:
    records = [
        {
            "schema": "dmb_session_memory_record_v1",
            "campaign_id": "longmont-c2",
            "session_number": 20,
            "unit_id": "U-test-lysandra-002",
            "lexical_plain": "Captain Lysandra is tied to a tower drawing and a blueprint.",
            "routes": [
                {
                    "normalized_route": "Longmont Campaign/Campaign 2/NPCs/captain_lysandra_ironveil/",
                    "subject_class": "npc",
                    "proposed": False,
                }
            ],
            "source_recap_path": "Longmont Campaign/Campaign 2/Session Recaps/Session 20 - Recap.md",
            "line_start": 1,
            "line_end": 1,
        }
    ]
    scenario = {
        "id": "synthetic_negated_required_token",
        "campaign_id": "longmont-c2",
        "query_spec": {
            "query": "Does the recap tie a tower drawing to the captain?",
            "session_min": 20,
            "session_max": 20,
            "max_hits": 12,
        },
        "must_hit_tokens": ["captain", "tower", "blueprint"],
        "semantic_equivalences": {"blueprint": ["drawing"]},
        "must_not_cooccur": {
            "blueprint": ["no drawing", "no blueprint", "no mention of a drawing"]
        },
        "stale_tokens": [],
        "expect_route_substrings": ["captain_lysandra_ironveil"],
        "min_context_support_ratio": 1.0,
        "update_signal_tokens": [],
    }
    bundle = natural_retrieval_bundle(records=records, scenario=scenario)
    out = grade_natural_scenario(
        records=records,
        scenario=scenario,
        llm_answer="The captain is tied to the tower, but there is no mention of a drawing.",
        cached_retrieval=bundle,
    )
    assert out["ok"] is False
    assert "llm_context_support_below_threshold" in out["violations"]


def test_load_gold_accepts_natural_schema(tmp_path: Path) -> None:
    p = tmp_path / "g.json"
    p.write_text(
        '{"schema": "dmb_breadcrumb_query_natural_gold_v1", "campaign_id": "x", "scenarios": []}',
        encoding="utf-8",
    )
    data = load_gold(p)
    assert data["schema"] == "dmb_breadcrumb_query_natural_gold_v1"


def test_embedding_similarity_helpers_are_deterministic() -> None:
    assert cosine_similarity([1.0, 0.0], [1.0, 0.0]) == 1.0
    assert cosine_similarity([1.0, 0.0], [0.0, 1.0]) == 0.0
    assert cosine_similarity([], [1.0]) == 0.0
    assert embedding_cost_usd(model="text-embedding-3-large", total_tokens=1_000_000) == 0.13
