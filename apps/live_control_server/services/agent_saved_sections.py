"""Read exact authored sections captured in a completed writer's durable input."""

from __future__ import annotations

from uuid import UUID

from application_state.agent_conversation import AgentConversationService
from application_state.agent_conversation.types import (
    SavedSourceClaimV1,
    BuildGraphContextReceiptV1,
    BuildSectionAnswerBindingV1,
    BuildSectionProviderInclusionV1,
    Turn,
    ValidatedBuildSectionReadV1,
)
from apps.live_control_server.models.agent_turn import (
    AgentSavedBuildSectionReadV1,
    AgentSavedBuildSectionTargetV1,
)
from .agent_source_passages import SourcePassageOpenError


def saved_section_targets(turn: Turn) -> list[AgentSavedBuildSectionTargetV1]:
    # Reconstruct, rather than trusting model_copy or a mutable in-memory object.
    turn = Turn.model_validate(turn.model_dump(mode="python", by_alias=True))
    if (
        turn.status != "completed"
        or not any(
            isinstance(segment, SavedSourceClaimV1)
            for segment in getattr(turn.completion, "answer_segments", ())
        )
        or not isinstance(turn.graph_context_receipt, BuildGraphContextReceiptV1)
        or turn.graph_context_execution is None
    ):
        return []
    receipt, execution = turn.graph_context_receipt, turn.graph_context_execution
    if receipt.source_basis.world_id != turn.world_id:
        raise ValueError("Saved source World differs")
    bindings = [
        e for e in execution.events if isinstance(e, BuildSectionAnswerBindingV1)
    ]
    if not bindings:
        return []  # Historical turns without bindings have no invented targets.
    if len(bindings) != 1:
        raise ValueError("Saved answer binding is ambiguous")
    binding = bindings[0]
    included = [
        e
        for e in execution.events
        if isinstance(e, BuildSectionProviderInclusionV1)
        and e.provider_attempt_id == binding.provider_attempt_id
        and e.envelope_sha256 == binding.envelope_sha256
    ]
    if len(included) != 1:
        raise ValueError("Saved answer lacks producing inclusion")
    reads = {
        e.event_id: e
        for e in execution.events
        if isinstance(e, ValidatedBuildSectionReadV1)
    }
    targets = []
    for item in binding.bindings:
        for event_id in item.section_event_ids:
            read = reads[event_id]
            if (
                event_id not in included[0].section_event_ids
                or read.source_basis != receipt.source_basis
            ):
                raise ValueError("Saved source differs from producing receipt")
            targets.append(
                AgentSavedBuildSectionTargetV1(
                    world_id=turn.world_id,
                    turn_id=turn.turn_id,
                    segment_index=item.segment_index,
                    section_event_id=read.event_id,
                    section_read_id=read.read_id,
                    source_basis=read.source_basis,
                    source_class=read.source_class,
                    line_start=read.line_start,
                    line_end=read.line_end,
                    excerpt_sha256=read.excerpt_sha256,
                    text_sha256=item.text_sha256,
                )
            )
    return targets


def open_saved_section(
    *,
    world_id: str,
    turn_id: UUID,
    segment_index: int,
    section_event_id: UUID,
    service: AgentConversationService | None = None,
) -> AgentSavedBuildSectionReadV1:
    if (
        isinstance(segment_index, bool)
        or not isinstance(segment_index, int)
        or not 0 <= segment_index <= 127
    ):
        raise SourcePassageOpenError("saved_section_selector_invalid", 422)
    turn = (service or AgentConversationService()).inspect_turn(
        world_id=world_id, turn_id=turn_id
    )
    if turn.world_id != world_id or turn.turn_id != turn_id:
        raise SourcePassageOpenError("saved_section_turn_unavailable", 404)
    matches = [
        t
        for t in saved_section_targets(turn)
        if t.segment_index == segment_index and t.section_event_id == section_event_id
    ]
    if len(matches) != 1:
        raise SourcePassageOpenError("saved_section_not_found", 404)
    target = matches[0]
    read = next(
        e
        for e in turn.graph_context_execution.events
        if isinstance(e, ValidatedBuildSectionReadV1)
        and e.event_id == target.section_event_id
    )
    # Full typed reconstruction above checks excerpt hash/range, completion and
    # producing inclusion. No filesystem, current document or native Graph read.
    return AgentSavedBuildSectionReadV1(target=target, content=read.text)
