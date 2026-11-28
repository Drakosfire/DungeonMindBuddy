"""The intent-only request and result codec for the first Play decision."""
from __future__ import annotations

from typing import Literal

from generationengine.types import DecisionRequest, DecisionResult
from pydantic import BaseModel, ConfigDict, Field, StrictStr

from .jev_retrieval_contract import RetrievalDialogue, validated_choice_answers
from .play_graph_context import validate_work_intent
from .surface_action_catalog import opening_action_menu, prepare_opening_intent, validate_opening_action_wire
from .types import PlayGraphIntentV1, PlayRunTurnContextReceiptV2


class NativePlayOpeningInputV1(BaseModel):
    """Only user-visible intent context enters this provider request."""

    model_config = ConfigDict(extra="forbid", frozen=True)
    schema_: Literal["dmb_native_play_opening_input_v1"] = Field(
        default="dmb_native_play_opening_input_v1", alias="schema")
    question: StrictStr = Field(min_length=1)
    dialogue: tuple[RetrievalDialogue, ...] = ()
    current_scene_title: StrictStr | None = None


def prepare_play_opening(request: NativePlayOpeningInputV1) -> DecisionRequest:
    state = {"surface": "play", "user_utterance": request.question}
    if request.dialogue:
        state["prior_dialogue"] = [row.model_dump() for row in request.dialogue]
    if request.current_scene_title is not None:
        state["current_scene_title"] = request.current_scene_title
    return prepare_opening_intent("play", state)


def decode_play_opening(result: DecisionResult) -> str:
    """Return an offered intent without granting any Run operation."""
    choice = validated_choice_answers(result, {"requested_work"})["requested_work"]
    if choice not in opening_action_menu("play"):
        raise ValueError("Play decision is outside its opening action menu")
    return choice


def validate_play_opening(
    request: NativePlayOpeningInputV1,
    raw: bytes,
    result: DecisionResult,
    *,
    intent: PlayGraphIntentV1,
    basis: PlayRunTurnContextReceiptV2,
) -> str:
    """Join the choice to the independently resolved Run basis and its wire."""
    validate_work_intent(basis, intent)
    if request.question != intent.message:
        raise ValueError("Play opening differs from its submitted utterance")
    validate_opening_action_wire(prepare_play_opening(request), raw)
    return decode_play_opening(result)
