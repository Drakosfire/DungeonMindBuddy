"""Intent → skill routing (``src.agent.skill_pipeline``)."""

from __future__ import annotations

from evals.lysandra_vertical_slice.step2_canonical_intent import intent_client_for_gold_expect
from src.agent.skill_pipeline import (
    NPC_POWER_INCREASE_SKILL_ID,
    scenario_key_for_user_line,
    route_user_line_to_skill,
)


def test_route_upgrade_request_to_npc_power_skill() -> None:
    r = route_user_line_to_skill(
        "Bump Lysandra to CR 6 for the finale.",
        client=intent_client_for_gold_expect(
            {
                "intent_mode": "upgrade_request",
                "power_axis": "challenge_rating",
                "clarifier_required": False,
            }
        ),
    )
    assert r.intent.intent_mode == "upgrade_request"
    assert r.skill_cursor_id == NPC_POWER_INCREASE_SKILL_ID


def test_route_factual_lookup_has_no_skill_yet() -> None:
    r = route_user_line_to_skill(
        "What is Lysandra's AC from the sheet?",
        client=intent_client_for_gold_expect(
            {
                "intent_mode": "factual_lookup",
                "power_axis": "challenge_rating",
                "clarifier_required": False,
            }
        ),
    )
    assert r.intent.intent_mode == "factual_lookup"
    assert r.skill_cursor_id is None


def test_scenario_upgrade_prose_for_cr_bump() -> None:
    assert (
        scenario_key_for_user_line(
            "Bump Lysandra to CR 6 for the finale.",
            client=intent_client_for_gold_expect(
                {
                    "intent_mode": "upgrade_request",
                    "power_axis": "challenge_rating",
                    "clarifier_required": False,
                }
            ),
        )
        == "upgrade_prose"
    )


def test_scenario_autonomous_for_prep_tone() -> None:
    assert (
        scenario_key_for_user_line(
            "Grab the latest on Lysandra for tonight's prep.",
            client=intent_client_for_gold_expect(
                {
                    "intent_mode": "factual_lookup",
                    "power_axis": "unknown",
                    "clarifier_required": False,
                }
            ),
        )
        == "autonomous"
    )
