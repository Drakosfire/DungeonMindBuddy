"""Read one admitted assertion from a saved Graph lookup."""

from application_state.agent_conversation.context_trace import TraceGraphTool
from apps.live_control_server.models.native_graph_inspection import InspectionPin
from apps.live_control_server.services.native_graph_inspection import InspectionUnavailable, read_assertion


def open_native_replay_assertion(*, service, principal, world_id, turn_id, trace_id, sequence, assertion_id):
    from application_state.agent_conversation.native_plan_assertions import (
        NativePlanAssertionReadV2, compact_assertion_read,
    )
    from .native_graph_reads import reopen_context
    from .native_statement_clause_reads import _reopen_record

    from application_state.agent_conversation.native_replay import load_native_replay_read

    try:
        selected = load_native_replay_read(world_id=world_id, turn_id=turn_id, trace_id=trace_id,
                                           sequence=sequence, assertion_id=assertion_id)
        if selected is None:
            selected = _load_mixed_native_replay_read(service=service, world_id=world_id, turn_id=turn_id,
                                                       trace_id=trace_id, sequence=sequence, assertion_id=assertion_id)
        query, grant, saved = selected
        authority = query.authority
        reopened = _reopen_record(reopen_context(query, principal), grant, assertion_id, principal, assertion=True)
        retained = compact_assertion_read(reopened) if isinstance(saved, NativePlanAssertionReadV2) else reopened
        if retained != saved:
            raise ValueError("Pinned native assertion differs from its saved read")
    except (ValueError, TypeError, KeyError, AttributeError, StopIteration) as exc:
        raise InspectionUnavailable("replay_native_assertion_unavailable") from exc
    return {
        "schema": "dmb_replay_native_assertion_v1", "world_id": world_id,
        "turn_id": str(turn_id), "trace_id": str(trace_id), "sequence": sequence,
        "revision_id": authority.revision_id,
        "assertion": reopened.assertion.model_dump(mode="json"),
        "excerpts": [span.model_dump(mode="json") for span in reopened.spans],
    }


def _load_mixed_native_replay_read(*, service, world_id, turn_id, trace_id, sequence, assertion_id):
    from application_state.agent_conversation.native_plan_assertions import (
        NativePlanAssertionReadAuthorizedV1, NativePlanAssertionReadObservedV1,
    )
    from application_state.agent_conversation.rules_authority_reads import MixedCompletedTurnV1

    attempts = service.list_context_trace_attempts(world_id=world_id, turn_id=turn_id)
    trace = next((row for row in attempts if row.trace_id == trace_id
                  and row.world_id == world_id and row.turn_id == turn_id), None)
    if trace is None or not any(step.sequence == sequence and assertion_id in step.assertion_ids
                               for step in trace.native_assertion_steps or ()):
        raise InspectionUnavailable("replay_assertion_unavailable")
    turn = service.inspect_turn(world_id=world_id, turn_id=turn_id)
    if isinstance(turn, MixedCompletedTurnV1):
        if turn.base_projection.kind != "approved":
            raise InspectionUnavailable("replay_assertion_unavailable")
        turn = turn.base_projection.turn
    if (turn.world_id, turn.turn_id, turn.conversation_id) != (world_id, turn_id, trace.conversation_id):
        raise InspectionUnavailable("replay_trace_unavailable")
    query = turn.graph_context_receipt.native_query
    authority = query.authority
    if authority.managed_world_id != world_id:
        raise ValueError("Recorded query belongs to a different World")
    events = turn.graph_context_execution.events
    observed = next(event for event in events
                        if isinstance(event, NativePlanAssertionReadObservedV1) and event.sequence == sequence)
    grant = next(event for event in events
                     if isinstance(event, NativePlanAssertionReadAuthorizedV1)
                     and event.event_id == observed.authorization_event_id)
    saved = next(read for read in observed.reads if read.assertion.assertion_id == assertion_id)
    return query, grant, saved


def open_replay_assertion(*, service, principal, world_id, turn_id, trace_id, sequence, assertion_id):
    attempts = service.list_context_trace_attempts(world_id=world_id, turn_id=turn_id)
    trace = next((row for row in attempts if row.trace_id == trace_id
                  and row.world_id == world_id and row.turn_id == turn_id), None)
    if trace is None:
        raise InspectionUnavailable("replay_trace_unavailable")
    step = next((event for event in trace.observations
                 if isinstance(event, TraceGraphTool) and event.sequence == sequence), None)
    if step is None or assertion_id not in step.result.claim_ids:
        raise InspectionUnavailable("replay_assertion_unavailable")
    turn = service.inspect_turn(world_id=world_id, turn_id=turn_id)
    authority = getattr(getattr(turn, "graph_context_receipt", None), "graph_authority", None)
    if (turn.world_id != world_id or turn.turn_id != turn_id
        or getattr(turn, "conversation_id", None) != trace.conversation_id
        or authority is None or authority.managed_world_id != world_id
        or authority.graph_revision != step.revision_pin):
        raise InspectionUnavailable("replay_graph_pin_unavailable")
    pin = InspectionPin(managed_world_id=world_id, native_world_id=authority.native_world_id,
                        binding_version=authority.binding_version, revision_id=step.revision_pin,
                        scope_mode=step.scope_mode, campaign_id=step.campaign_id)
    opened = read_assertion(pin, principal, assertion_id)
    return {"schema": "dmb_replay_assertion_v1", "world_id": world_id,
            "turn_id": str(turn_id), "trace_id": str(trace_id), "sequence": sequence, **opened}
