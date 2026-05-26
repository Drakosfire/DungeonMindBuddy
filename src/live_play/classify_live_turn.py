from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from src.agent.synthesis import _load_api_key
from src.live_play.live_turn_classification_schema import LiveTurnClassificationModel
from src.live_play.live_turn_classifier_client import (
    OpenAILiveTurnClassifierClient,
    SequenceLiveTurnClassifierClient,
)

WEATHER_ROLL_RE = re.compile(r"Weather\s+(\d+)\.?", re.IGNORECASE)
R5_ROLL_RE = re.compile(r"R5\s+(\d+)\.?", re.IGNORECASE)
TABLE_ROLL_RE = re.compile(r"(T-[A-Z0-9-]+|R\d+)\s+(\d+)\.?", re.IGNORECASE)
NATURE_SKILL_RE = re.compile(r"([A-Za-z]+)\s+Nature\s+(\d+)", re.IGNORECASE)
CONTEXT_QUESTION_RE = re.compile(
    r"^\s*what\s+is\b.+\?\s*$|^\s*how\s+.+\?\s*$",
    re.IGNORECASE,
)

_CLASSIFIER_MODEL_ENV = "LIVE_TURN_CLASSIFIER_MODEL"
_CLASSIFIER_MODE_ENV = "LIVE_TURN_CLASSIFIER_MODE"
_FALLBACK_ENV = "LIVE_TURN_CLASSIFIER_ALLOW_HEURISTIC_FALLBACK"
_POLICY_ACTION = "live_turn_classifier"
_DEFAULT_CLASSIFIER_MODEL = "gpt-4o-mini"
ClassifierMode = Literal["heuristic", "llm", "llm_with_heuristic_fallback"]


@dataclass(frozen=True)
class TurnClassification:
    latency_mode: str
    event_type: str
    intent: str
    table_id: str | None = None
    roll: int | None = None
    skill_check: dict[str, object] | None = None
    confidence: str = "high"


def _model_policy_paths() -> list[Path]:
    here = Path(__file__).resolve()
    return [here.parents[2] / "MODEL_POLICY.json", here.parents[3] / "MODEL_POLICY.json"]


def _resolve_classifier_model(model: str | None) -> str:
    if model and str(model).strip():
        return str(model).strip()
    env_model = os.environ.get(_CLASSIFIER_MODEL_ENV, "").strip()
    if env_model:
        return env_model
    for policy_path in _model_policy_paths():
        if not policy_path.is_file():
            continue
        try:
            policy = json.loads(policy_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        models = policy.get("models") or {}
        actions = policy.get("actions") or {}
        role = actions.get(_POLICY_ACTION) or actions.get("structured_generation")
        if isinstance(role, str) and role.strip():
            mid = models.get(role.strip())
            if isinstance(mid, str) and mid.strip():
                return mid.strip()
        cheapest = models.get("cheapest")
        if isinstance(cheapest, str) and cheapest.strip():
            return cheapest.strip()
    return _DEFAULT_CLASSIFIER_MODEL


def _truthy_env(name: str) -> bool | None:
    raw = os.environ.get(name)
    if raw is None:
        return None
    normalized = raw.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    return None


def _classifier_mode(allow_heuristic_fallback: bool | None) -> ClassifierMode:
    """Resolve runtime classifier mode.

    Default runtime behavior is LLM-first with deterministic fallback. This keeps the
    live app usable when the OpenAI key/network is unavailable while preserving LLM
    routing as the normal configured path.
    """
    if allow_heuristic_fallback is False:
        return "llm"

    explicit_mode = os.environ.get(_CLASSIFIER_MODE_ENV, "").strip().lower()
    if explicit_mode in {"heuristic", "llm", "llm_with_heuristic_fallback"}:
        return explicit_mode  # type: ignore[return-value]

    if allow_heuristic_fallback is True:
        return "llm_with_heuristic_fallback"

    fallback_env = _truthy_env(_FALLBACK_ENV)
    if fallback_env is False:
        return "llm"
    return "llm_with_heuristic_fallback"


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


def _skill_check_from_match(text: str) -> dict[str, object] | None:
    skill_match = NATURE_SKILL_RE.search(text)
    if not skill_match:
        return None
    return {
        "actor": skill_match.group(1),
        "skill": "Nature",
        "total": int(skill_match.group(2)),
    }


def _turn_classification_from_model(parsed: LiveTurnClassificationModel) -> TurnClassification:
    skill_check = None
    if parsed.skill_check is not None:
        skill_check = {
            "actor": parsed.skill_check.actor,
            "skill": parsed.skill_check.skill,
            "total": parsed.skill_check.total,
        }
    return TurnClassification(
        latency_mode=parsed.latency_mode,
        event_type=parsed.event_type,
        intent=parsed.intent.strip() or "unclassified_note",
        table_id=parsed.table_id,
        roll=parsed.roll,
        skill_check=skill_check,
        confidence=parsed.confidence,
    )


def _repair_roll_fields(text: str, classification: TurnClassification) -> TurnClassification:
    """Backfill table_id/roll from the GM line when the model chose roll_result but omitted numbers."""
    if classification.event_type != "roll_result":
        return classification
    table_id, roll = classification.table_id, classification.roll
    if table_id is not None and roll is not None:
        return classification
    extracted_id, extracted_roll = _extract_roll(text)
    if extracted_id is None or extracted_roll is None:
        return classification
    skill_check = classification.skill_check or _skill_check_from_match(text)
    return TurnClassification(
        latency_mode=classification.latency_mode,
        event_type=classification.event_type,
        intent=classification.intent,
        table_id=extracted_id,
        roll=extracted_roll,
        skill_check=skill_check,
        confidence=classification.confidence,
    )


def classify_live_turn_heuristic(text: str) -> TurnClassification:
    """Deterministic regex classifier (tests and explicit fallback only)."""
    stripped = text.strip()
    lowered = stripped.lower()

    if CONTEXT_QUESTION_RE.match(stripped) or (
        "?" in stripped and ("what is" in lowered or "feeling" in lowered)
    ):
        return TurnClassification(
            latency_mode="context_lookup",
            event_type="context_question",
            intent="npc_or_scene_context",
            confidence="deterministic",
        )

    if "bottles the" in lowered or "bottles " in lowered:
        return TurnClassification(
            latency_mode="fast_live",
            event_type="canon_commit",
            intent="session_canon_commit",
            confidence="deterministic",
        )

    if "is her father" in lowered or "is his father" in lowered or "canon correction" in lowered:
        return TurnClassification(
            latency_mode="fast_live",
            event_type="canon_correction",
            intent="relationship_correction",
            confidence="deterministic",
        )

    if "does not call" in lowered or ("grobnok" in lowered and "morning" in lowered):
        return TurnClassification(
            latency_mode="fast_live",
            event_type="open_loop_update",
            intent="open_loop_status",
            confidence="deterministic",
        )

    table_id, roll = _extract_roll(stripped)
    skill_check = _skill_check_from_match(stripped)

    if table_id is not None and roll is not None:
        return TurnClassification(
            latency_mode="fast_live",
            event_type="roll_result",
            intent="resolve_roll_table",
            table_id=table_id,
            roll=roll,
            skill_check=skill_check,
            confidence="deterministic",
        )

    return TurnClassification(
        latency_mode="fast_live",
        event_type="state_note",
        intent="unclassified_note",
        confidence="deterministic",
    )


def _classification_model_from_turn(c: TurnClassification) -> LiveTurnClassificationModel:
    from src.live_play.live_turn_classification_schema import LiveTurnSkillCheck

    skill = None
    if c.skill_check:
        skill = LiveTurnSkillCheck(
            actor=str(c.skill_check["actor"]),
            skill=str(c.skill_check["skill"]),
            total=int(c.skill_check["total"]),
        )
    confidence = c.confidence if c.confidence in {"high", "medium", "low"} else "high"
    return LiveTurnClassificationModel(
        latency_mode=c.latency_mode,  # type: ignore[arg-type]
        event_type=c.event_type,  # type: ignore[arg-type]
        intent=c.intent,
        table_id=c.table_id,
        roll=c.roll,
        skill_check=skill,
        confidence=confidence,  # type: ignore[arg-type]
    )


def build_live_turn_classifier_sequence_client(
    classifications: list[TurnClassification],
) -> SequenceLiveTurnClassifierClient:
    return SequenceLiveTurnClassifierClient(
        [_classification_model_from_turn(c) for c in classifications]
    )


def classify_live_turn(
    text: str,
    *,
    client: Any | None = None,
    model: str | None = None,
    allow_heuristic_fallback: bool | None = None,
) -> TurnClassification:
    """
    Classify GM live-play input via LLM-first routing.

    Defaults to LLM routing with deterministic heuristic fallback so the local live
    control surface remains usable without an API key or network. Pass
    ``allow_heuristic_fallback=False`` or set ``LIVE_TURN_CLASSIFIER_MODE=llm``
    when a caller wants hard failure instead of fallback. Tests may pass a
    ``client=`` such as ``SequenceLiveTurnClassifierClient``.
    """
    stripped = text.strip()
    if not stripped:
        return TurnClassification(
            latency_mode="fast_live",
            event_type="state_note",
            intent="empty_input",
            confidence="high",
        )

    mode = _classifier_mode(allow_heuristic_fallback)
    if mode == "heuristic":
        return classify_live_turn_heuristic(stripped)

    if client is None:
        api_key = _load_api_key()
        if not api_key:
            if mode == "llm_with_heuristic_fallback":
                return classify_live_turn_heuristic(stripped)
            raise RuntimeError(
                "OPENAI_API_KEY is required for classify_live_turn when "
                f"{_CLASSIFIER_MODE_ENV}=llm or allow_heuristic_fallback=False"
            )

    mid = _resolve_classifier_model(model)
    try:
        adapter = OpenAILiveTurnClassifierClient(sdk_client=client)
        parsed = adapter.classify_turn(model=mid, text=stripped)
    except Exception as exc:
        if mode == "llm_with_heuristic_fallback":
            return classify_live_turn_heuristic(stripped)
        raise RuntimeError(f"Live turn classifier failed: {exc}") from exc
    classification = _turn_classification_from_model(parsed)
    return _repair_roll_fields(stripped, classification)
