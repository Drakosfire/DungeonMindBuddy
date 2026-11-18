"""Recorded native Build acquisition of exact saved mechanics."""
from typing import Literal
from uuid import UUID

from pydantic import Field, JsonValue

from application_state.world_mechanics.types import MechanicsLocator
from .native_statement_input import Strict


class SavedStatblockPdfCrop(Strict):
    assertion_id: str = Field(min_length=1)
    evidence_ref_id: str = Field(pattern=r"^pdf-region:.+$")
    text: str


class SavedStatblockPdfPin(Strict):
    managed_world_id: str
    native_world_id: str
    binding_version: int = Field(gt=0)
    revision_id: str
    scope_mode: Literal["world"]
    campaign_id: None


class SavedStatblockPdfSupport(Strict):
    scope: SavedStatblockPdfPin
    support: list[SavedStatblockPdfCrop]


class SavedStatblockAssociationAnchor(Strict):
    association_id: UUID
    node_id: str = Field(min_length=1)


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
    pdf_support: SavedStatblockPdfSupport | None = None
    continuity_verified: bool = Field(default=False, exclude_if=lambda value: not value)
    association_anchor: SavedStatblockAssociationAnchor | None = Field(
        default=None, exclude_if=lambda value: value is None,
    )
    reused_from_turn_id: UUID | None = Field(default=None, exclude_if=lambda value: value is None)


def validate_prior_read(event, current, previous):
    """Bind reuse to one authenticated earlier read in this conversation."""
    from .native_corpus import NativeCorpusAuthorityV1

    if (previous is None or previous.turn_id != event.reused_from_turn_id
            or previous.world_id != current.world_id
            or previous.conversation_id != current.conversation_id
            or previous.sequence >= current.sequence or previous.status != "completed"
            or previous.graph_context_execution is None):
        raise ValueError("Saved statblock reuse requires an earlier completed turn in this conversation")
    current_receipt = current.graph_context_receipt
    prior_receipt = previous.graph_context_receipt
    authority = getattr(current_receipt, "source_authority", None)
    if (not event.continuity_verified or not isinstance(authority, NativeCorpusAuthorityV1)
            or authority != getattr(prior_receipt, "source_authority", None)
            or current_receipt.work_context.source_basis != prior_receipt.work_context.source_basis):
        raise ValueError("Saved statblock reuse authority differs from its producing turn")
    matching = [
        read for read in previous.graph_context_execution.events
        if isinstance(read, BuildSavedStatblockReadV1) and read.world_id == current.world_id
        and read.draft_id == event.draft_id and read.locator == event.locator
    ]
    if len(matching) != 1 or not matching[0].continuity_verified:
        raise ValueError("Saved statblock reuse requires one verified source read")
    old = matching[0]
    if event.association_anchor is None or event.association_anchor != old.association_anchor:
        raise ValueError("Saved statblock reuse differs from its producing World association")
    if old.definition != event.definition or old.pdf_support != event.pdf_support:
        raise ValueError("Saved statblock reuse differs from its verified source evidence")


def validate_read(event, execution):
    from .native_execution import NativeBuildActionV1
    from .native_retrieval import native_selection_types

    if not isinstance(execution.policy.action, NativeBuildActionV1):
        raise ValueError("Saved statblock reads require native Build")
    if event.pdf_support is not None and event.pdf_support.scope.managed_world_id != event.world_id:
        raise ValueError("Saved statblock PDF support belongs to another World")
    prior_events = execution.events[:event.sequence]
    selections = [entry for entry in prior_events if isinstance(entry, native_selection_types())]
    if (not selections or selections[-1].event_id != event.selection_event_id
            or event.handle not in selections[-1].selected_handles
            or event.world_id != execution.policy.action.intent.world_id):
        raise ValueError("Saved statblock read differs from its current Build selection")
    if any(isinstance(entry, BuildSavedStatblockReadV1) and entry.handle == event.handle
           for entry in prior_events):
        raise ValueError("Saved statblock selection was already read")
