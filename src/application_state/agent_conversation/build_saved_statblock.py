"""Recorded native Build acquisition of exact saved mechanics."""
from typing import Literal
from uuid import UUID

from pydantic import Field, JsonValue

from application_state.world_mechanics.types import MechanicsLocator
from .native_statement_input import Strict


class BuildSavedStatblockReadV1(Strict):
    kind: Literal["build_saved_statblock_read_v1"] = "build_saved_statblock_read_v1"
    event_id: UUID
    sequence: int = Field(ge=0)
    selection_event_id: UUID
    handle: str = Field(pattern=r"^saved-statblock:[0-9]+$")
    world_id: str
    draft_id: UUID
    locator: MechanicsLocator
    definition: dict[str, JsonValue]
    pdf_support: dict[str, JsonValue] | None = None


def validate_read(event, execution):
    from .native_execution import NativeBuildActionV1
    from .native_retrieval import native_selection_types

    if not isinstance(execution.policy.action, NativeBuildActionV1):
        raise ValueError("Saved statblock reads require native Build")
    prior_events = execution.events[:event.sequence]
    selections = [entry for entry in prior_events if isinstance(entry, native_selection_types())]
    if (not selections or selections[-1].event_id != event.selection_event_id
            or event.handle not in selections[-1].selected_handles
            or event.world_id != execution.policy.action.intent.world_id):
        raise ValueError("Saved statblock read differs from its current Build selection")
    if any(isinstance(entry, BuildSavedStatblockReadV1) and entry.handle == event.handle
           for entry in prior_events):
        raise ValueError("Saved statblock selection was already read")
