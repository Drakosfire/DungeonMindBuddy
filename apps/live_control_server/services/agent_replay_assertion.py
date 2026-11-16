"""Read one admitted assertion from a saved Graph lookup."""

from application_state.agent_conversation.context_trace import TraceGraphTool
from apps.live_control_server.models.native_graph_inspection import InspectionPin
from apps.live_control_server.services.native_graph_inspection import InspectionUnavailable, read_assertion


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
