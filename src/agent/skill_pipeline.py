"""Intent → Cursor skill routing (target orchestration; planner integration TBD).

The **product** flow we want:

1. User text in  
2. Agent checks intent  
3. Agent selects the skill  
4. Research (corpus tools)  
5. Attach baseline (``load_context_markdown`` on canonical statblock)  
6. Write prose (power-rise description only)  
7. Combine (bundle for downstream generator / store — future)

Benchmark evals exercise (4)–(6) inside a single planner turn (tools + gold gates); scenario-specific
instruction appendices are intentionally not injected—workflow lives in Cursor skills.
This module formalizes (2)–(3) for callers that run **before** the planner.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from src.npc_statblock_pipeline.canonical_intent import IntentClassification, classify_intent

# Cursor skill folder under ``.cursor/skills/<id>/SKILL.md`` in this repo.
NPC_POWER_INCREASE_SKILL_ID = "npc-power-increase"


@dataclass(frozen=True)
class RoutedTurn:
    """Intent classification plus optional Cursor skill id for preprompting."""

    intent: IntentClassification
    skill_cursor_id: str | None


def scenario_key_for_user_line(
    user_line: str,
    *,
    client: Any | None = None,
    model: str | None = None,
) -> str:
    """
    Map a ``user_line`` to a **benchmark** gold key (``planner_step1_<key>.json``).

    Used when the harness must pick which **eval** fixture file to load (e.g. env
    ``LYSANDRA_PLANNER_USER_MESSAGE`` without ``LYSANDRA_PLANNER_STEP1_SCENARIO``). This is not
    the corpus planner’s internal routing.

    Today: ``upgrade_request`` intent → ``upgrade_prose``; everything else → ``autonomous``.
    (``directed`` / ``stat_check`` remain opt-in via ``LYSANDRA_PLANNER_STEP1_SCENARIO``.)
    """
    r = route_user_line_to_skill(user_line, client=client, model=model)
    if r.skill_cursor_id == NPC_POWER_INCREASE_SKILL_ID:
        return "upgrade_prose"
    return "autonomous"


def route_user_line_to_skill(
    user_line: str,
    *,
    client: Any | None = None,
    model: str | None = None,
) -> RoutedTurn:
    """
    **Runtime / product path:** ``classify_intent`` (Responses API; model from ``MODEL_POLICY`` by default)
    then Cursor skill selection.

    Today only **upgrade_request** maps to ``npc-power-increase``; other modes
    return ``skill_cursor_id=None`` until additional skills exist.

    (Contrast: ``evaluate_step2_post_planner_benchmark`` only **scores** a planner turn; it does not select skills.)
    """
    intent = classify_intent(user_line, client=client, model=model)
    skill: str | None = None
    if intent.intent_mode == "upgrade_request":
        skill = NPC_POWER_INCREASE_SKILL_ID
    return RoutedTurn(intent=intent, skill_cursor_id=skill)
