from __future__ import annotations

import re
from dataclasses import dataclass

WEATHER_ROLL_RE = re.compile(r"Weather\s+(\d+)\.?", re.IGNORECASE)
R5_ROLL_RE = re.compile(r"R5\s+(\d+)\.?", re.IGNORECASE)
TABLE_ROLL_RE = re.compile(r"(T-[A-Z0-9-]+|R\d+)\s+(\d+)\.?", re.IGNORECASE)
NATURE_SKILL_RE = re.compile(r"([A-Za-z]+)\s+Nature\s+(\d+)", re.IGNORECASE)
CONTEXT_QUESTION_RE = re.compile(
    r"^\s*what\s+is\b.+\?\s*$|^\s*how\s+.+\?\s*$",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class TurnClassification:
    latency_mode: str
    event_type: str
    intent: str
    table_id: str | None = None
    roll: int | None = None
    skill_check: dict[str, object] | None = None
    confidence: str = "deterministic"


def _extract_roll(text: str) -> tuple[str | None, int | None]:
    match = WEATHER_ROLL_RE.search(text)
    if match:
        return "T-WX", int(match.group(1))
    match = R5_ROLL_RE.search(text)
    if match:
        return "R5", int(match.group(1))
    match = TABLE_ROLL_RE.search(text)
    if match:
        return match.group(1).upper(), int(match.group(2))
    return None, None


def classify_live_turn(text: str) -> TurnClassification:
    stripped = text.strip()
    lowered = stripped.lower()

    if CONTEXT_QUESTION_RE.match(stripped) or (
        "?" in stripped and ("what is" in lowered or "feeling" in lowered)
    ):
        return TurnClassification(
            latency_mode="context_lookup",
            event_type="context_question",
            intent="npc_or_scene_context",
        )

    if "bottles the" in lowered or "bottles " in lowered:
        return TurnClassification(
            latency_mode="fast_live",
            event_type="canon_commit",
            intent="session_canon_commit",
        )

    if "is her father" in lowered or "is his father" in lowered or "canon correction" in lowered:
        return TurnClassification(
            latency_mode="fast_live",
            event_type="canon_correction",
            intent="relationship_correction",
        )

    if "does not call" in lowered or ("grobnok" in lowered and "morning" in lowered):
        return TurnClassification(
            latency_mode="fast_live",
            event_type="open_loop_update",
            intent="open_loop_status",
        )

    table_id, roll = _extract_roll(stripped)
    skill_match = NATURE_SKILL_RE.search(stripped)
    skill_check = None
    if skill_match:
        skill_check = {
            "actor": skill_match.group(1),
            "skill": "Nature",
            "total": int(skill_match.group(2)),
        }

    if table_id is not None and roll is not None:
        return TurnClassification(
            latency_mode="fast_live",
            event_type="roll_result",
            intent="resolve_roll_table",
            table_id=table_id,
            roll=roll,
            skill_check=skill_check,
        )

    return TurnClassification(
        latency_mode="fast_live",
        event_type="state_note",
        intent="unclassified_note",
    )
