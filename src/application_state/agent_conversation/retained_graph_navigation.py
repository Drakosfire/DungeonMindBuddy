"""Historical Graph labels are navigation hints, never evidence or source scope."""
from dataclasses import dataclass
from . import types as t
from .context_trace import TraceGraphTool
from .rules_authority_reads import MixedCompletedTurnV1


@dataclass(frozen=True)
class RetainedGraphSubject:
    node_id: str
    label: str
    kind: str


def from_history(conn, *, world_id, conversation_id, authority, previous_turns):
    from . import repository as repo
    eligible = {}
    for previous in previous_turns:
        if isinstance(previous, MixedCompletedTurnV1):
            if previous.base_projection.kind != 'approved':
                continue
            previous = previous.base_projection.turn
        if (previous.status == 'completed' and previous.completed_at is not None
                and previous.world_id == world_id and previous.conversation_id == conversation_id
                and previous.graph_context_receipt is not None
                and previous.graph_context_receipt.graph_authority == authority
                and previous.graph_context_execution is not None):
            eligible[previous.turn_id] = previous
    selected = {}
    for turn_id, attempt, raw in repo.list_retained_graph_tools(conn, world_id, conversation_id, eligible, authority):
        previous = eligible.get(turn_id)
        if previous is None or previous.attempt != attempt:
            continue
        try:
            observation = TraceGraphTool.model_validate(raw)
        except (ValueError, TypeError):
            continue
        event = next((event for event in previous.graph_context_execution.events
            if isinstance(event, t.ValidatedGraphOperationEventV3)
            and event.event_id == observation.execution_event_id), None)
        if (event is None or observation.scope_mode != 'world'
                or observation.revision_pin != authority.graph_revision
                or event.graph_revision != authority.graph_revision
                or event.request_arguments_sha256 != observation.request_arguments_sha256
                or event.result_packet_sha256 != observation.result_packet_sha256):
            continue
        for node in observation.result.nodes:
            selected.setdefault(node.node_id, RetainedGraphSubject(node.node_id, node.label, node.kind))
    return tuple(selected[key] for key in sorted(selected))
