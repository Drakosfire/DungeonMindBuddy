from __future__ import annotations

from evals.c1s4_preplanning_vertical_slice.planner_affordances import (
    derive_planner_affordances_for_support_card,
    derive_query_planner_affordances,
)
from evals.c1s4_preplanning_vertical_slice.support_knowledge_loader import (
    load_support_retrieval_field_policy,
    normalize_support_card,
)


def test_support_affordances_are_source_derived_from_visible_fields() -> None:
    card = {
        "support_card_id": "fixture_visible_tree",
        "title": "Grotesque tree as visible threat",
        "summary": "An obvious village-scale problem seen from the road, with thorned branches and metallic leaves.",
        "retrieval_terms": ["towering tree"],
        "usable_for_questions": ["q10_should_not_matter"],
        "question_id": "forbidden",
        "gold_group_id": "forbidden",
    }

    affordances = derive_planner_affordances_for_support_card(card, include_retrieval_terms=False)
    names = {a["affordance"] for a in affordances}

    assert "visible_landmark" in names
    assert "approach_description" in names
    assert all(a["source_visible"] is True for a in affordances)
    assert {a["basis_field"] for a in affordances} <= {"title", "summary"}


def test_query_affordances_are_question_text_derived() -> None:
    assert set(
        derive_query_planner_affordances(
            "As the party approaches Hempholm, what should they see first from a distance? Give boxed text."
        )
    ) >= {"approach_description", "visible_landmark", "boxed_text"}
    assert set(
        derive_query_planner_affordances(
            "What are the first three NPCs the players should meet, and what immediate tension does each represent?"
        )
    ) >= {"npc_intro", "social_tension"}
    assert set(
        derive_query_planner_affordances(
            "Design the encounter as a battlefield with terrain, civilians, hazards, and objectives."
        )
    ) >= {"encounter_design", "battlefield_terrain", "civilian_pressure", "environmental_hazard", "objective_design"}


def test_forbidden_eval_fields_do_not_affect_support_index_text() -> None:
    policy = load_support_retrieval_field_policy()
    base = {
        "support_card_id": "same",
        "campaign_id": "longmont-c1",
        "source_layer": "support",
        "authority_role": "adaptation",
        "canon_status": "support",
        "title": "Grotesque tree as visible threat",
        "summary": "An obvious village-scale problem seen from the road.",
        "retrieval_terms": ["visible threat"],
    }
    with_eval = {
        **base,
        "usable_for_questions": ["q10_demo_specific"],
        "expected_retrieval_context": ["forbidden"],
        "oracle_risk": "forbidden",
    }

    normalized_base = normalize_support_card(
        base,
        retrieval_mode="content_plus_lexical_hints",
        field_policy=policy,
    )
    normalized_eval = normalize_support_card(
        with_eval,
        retrieval_mode="content_plus_lexical_hints",
        field_policy=policy,
    )

    assert normalized_base["lexical_plain"] == normalized_eval["lexical_plain"]
    assert normalized_base["planner_affordances"] == normalized_eval["planner_affordances"]
