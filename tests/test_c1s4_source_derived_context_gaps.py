from __future__ import annotations

from evals.c1s4_preplanning_vertical_slice.source_derived_context_gaps import (
    SOURCE_DERIVED_GAP_SCHEMA,
    build_source_derived_context_gaps,
    gap_text_contains_forbidden_gold_phrase,
    is_source_derived_route_gap_hit,
)


def test_q3_route_question_emits_source_derived_gap_when_route_details_absent() -> None:
    gaps = build_source_derived_context_gaps(
        question_id="q03_how_far_away_is_mirathorn_at_this_point",
        question_text="How far away is Mirathorn at this point? Is anyone traveling that direction?",
        retrieval_mode="prior_only",
        candidate_context=[
            {
                "unit_id": "corpus:session_recap:session-3:observed-play-prose",
                "snippet": "The party is pointed toward Mirathorn after Stone Bridge.",
                "source_path": "corpus/eldyrwild-markdown/Longmont Campaign/Campaign 1/Session Recaps/Session 3 - The Stone Bridge Flood.md",
            },
            {
                "unit_id": "corpus:location:stone_bridge:canon-summary",
                "snippet": "Stone Bridge is the current location after the flood.",
                "source_path": "corpus/eldyrwild-markdown/Longmont Campaign/Campaign 1/Locations/stone_bridge/README.md",
            },
        ],
        admitted_context=[],
        query_features={},
    )

    assert gaps
    gap_text = gaps[0]["gap"]
    assert gaps[0]["schema"] == SOURCE_DERIVED_GAP_SCHEMA
    assert gaps[0]["source"] == "deterministic_absence_analysis"
    assert gaps[0]["evidence_scope"] == "allowed_prior_context"
    assert gaps[0]["gap_id"] == "source_gap:mirathorn_exact_route_gap"
    assert "route gazetteer" not in gap_text.lower()
    assert is_source_derived_route_gap_hit(gaps[0])


def test_non_route_question_emits_no_source_derived_gap() -> None:
    gaps = build_source_derived_context_gaps(
        question_id="q01_who_are_the_npcs",
        question_text="Who are the NPCs the players encountered?",
        retrieval_mode="prior_only",
        candidate_context=[{"unit_id": "u1", "snippet": "Pippa at Stone Bridge"}],
        admitted_context=[],
        query_features={},
    )
    assert gaps == []


def test_source_derived_gap_does_not_copy_gold_gap_phrases() -> None:
    gaps = build_source_derived_context_gaps(
        question_id="q03_how_far_away_is_mirathorn_at_this_point",
        question_text="How far away is Mirathorn? What is on the road?",
        retrieval_mode="prior_only",
        candidate_context=[
            {"unit_id": "corpus:location:stone_bridge:canon-summary", "snippet": "Stone Bridge toward Mirathorn"},
        ],
        admitted_context=[],
        query_features={},
    )
    assert gaps
    assert not gap_text_contains_forbidden_gold_phrase(gaps[0]["gap"])


def test_source_derived_gap_requires_positive_allowed_context() -> None:
    gaps = build_source_derived_context_gaps(
        question_id="q03_how_far_away_is_mirathorn_at_this_point",
        question_text="How far away is Mirathorn at this point?",
        retrieval_mode="prior_only",
        candidate_context=[{"unit_id": "u1", "snippet": "Mirathorn is far away"}],
        admitted_context=[],
        query_features={},
    )
    assert gaps == []


def test_open_canon_absence_text_does_not_suppress_route_gap() -> None:
    gaps = build_source_derived_context_gaps(
        question_id="q03_how_far_away_is_mirathorn_at_this_point",
        question_text="How far away is Mirathorn? Traveling on the road?",
        retrieval_mode="prior_only",
        candidate_context=[
            {
                "unit_id": "corpus:location:stone_bridge:open-canon-questions",
                "snippet": "Exact Stone Bridge-to-Mirathorn route details are not yet established in campaign-canon location hubs.",
            },
            {
                "unit_id": "corpus:location:stone_bridge:canon-summary",
                "snippet": "Stone Bridge is the current anchor; Mirathorn lies ahead.",
            },
        ],
        admitted_context=[],
        query_features={},
    )
    assert gaps


def test_source_derived_gap_has_allowed_prior_context_scope() -> None:
    gaps = build_source_derived_context_gaps(
        question_id="q03_how_far_away_is_mirathorn_at_this_point",
        question_text="How far away is Mirathorn? Traveling on the road?",
        retrieval_mode="prior_only",
        candidate_context=[
            {"unit_id": "corpus:session_recap:session-3", "snippet": "Stone Bridge flood; Mirathorn next"},
        ],
        admitted_context=[],
        query_features={},
    )
    assert gaps
    assert gaps[0]["evidence_scope"] == "allowed_prior_context"
    basis = gaps[0].get("basis") or {}
    assert basis.get("positive_context_refs")
    assert basis.get("missing_context_type") == "route_gazetteer"
