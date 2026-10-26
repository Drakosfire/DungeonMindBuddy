"""Read the saved origin selected by one admitted completed page review."""
from application_state.agent_conversation import types as t
from application_state.agent_conversation.collaboration import ProposedConnectedPage, saved_excerpt
from application_state.agent_conversation.connected_page_origins import execution_rows


def open_origin(service, world_id, turn_id):
    turn = service.inspect_turn(world_id=world_id,turn_id=turn_id)
    from application_state.agent_conversation.rules_authority_reads import MixedCompletedTurnV1
    if isinstance(turn,MixedCompletedTurnV1):
        if turn.base_projection.kind != 'approved':
            raise ValueError('Connected origin lacks its approved base completion')
        turn=turn.base_projection.turn
    turn=t.Turn.model_validate(turn.model_dump(mode='python',by_alias=True))
    review=getattr(turn.completion,'collaboration',None)
    if (turn.world_id != world_id or turn.turn_id != turn_id or turn.status != 'completed'
        or not isinstance(review,ProposedConnectedPage) or not isinstance(turn.graph_context_receipt,t.BuildGraphContextReceiptV1)):
        raise ValueError('Connected origin requires its exact completed page review')
    bindings=[e for e in turn.graph_context_execution.events if isinstance(e,t.CompletionBindingEventV1)]
    if len(bindings)!=1:
        raise ValueError('Connected origin producing completion is ambiguous')
    rows=execution_rows(turn.graph_context_execution,turn.graph_context_receipt.source_basis,bindings[0].provider_attempt_id)
    origin=saved_excerpt(review,rows)
    return {'schema':'dmb_agent_connected_page_origin_v1','world_id':world_id,
        'turn_id':str(turn_id),'read_id':review.read_id,'origin':origin}
