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
    turn=t.Turn.model_validate_json(turn.model_dump_json(by_alias=True))
    review=getattr(turn.completion,'collaboration',None)
    from application_state.agent_conversation.native_context import SurfaceNativeContextReceiptV1,BuildWorkContextV1,PlanWorkContextV1
    receipt=turn.graph_context_receipt
    basis=(receipt.work_context.source_basis if type(receipt) is SurfaceNativeContextReceiptV1
        and type(receipt.work_context) is BuildWorkContextV1 else receipt.source_basis
        if isinstance(receipt,t.BuildGraphContextReceiptV1) else None)
    from application_state.agent_conversation.plan_jev_decision import connected_page_review_enabled
    plan_origin=(type(receipt) is SurfaceNativeContextReceiptV1
        and type(receipt.work_context) is PlanWorkContextV1
        and connected_page_review_enabled(turn.graph_context_execution))
    if (turn.world_id != world_id or turn.turn_id != turn_id or turn.status != 'completed'
        or not isinstance(review,ProposedConnectedPage) or basis is None and not plan_origin):
        raise ValueError('Connected origin requires its exact completed page review')
    bindings=[e for e in turn.graph_context_execution.events if isinstance(e,t.CompletionBindingEventV1)]
    if len(bindings)!=1:
        raise ValueError('Connected origin producing completion is ambiguous')
    rows=execution_rows(turn.graph_context_execution,basis,bindings[0].provider_attempt_id)
    origin=saved_excerpt(review,rows)
    return {'schema':'dmb_agent_connected_page_origin_v1','world_id':world_id,
        'turn_id':str(turn_id),'read_id':review.read_id,'origin':origin}
