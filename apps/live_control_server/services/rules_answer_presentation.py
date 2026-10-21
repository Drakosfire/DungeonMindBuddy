"""Project accepted Rules attribution, without opening source bytes or minting authority."""
from application_state.agent_conversation.rules_authority_reads import MixedCompletedTurnV1
from apps.live_control_server.models.agent_turn import AgentRulesAnswerContextV1, AgentRulesUnclaimedContextV1


def project_rules_answer_context(turn: MixedCompletedTurnV1, *, delivery_replay: bool) -> AgentRulesAnswerContextV1:
    from application_state.agent_conversation.types import PlayWorldGraphContextReceiptV1
    from .agent_turn_service import project_plan_turn_context, project_play_turn_context

    # Recheck the actual owner/provenance/producer joins before exposing execution metadata.
    turn = MixedCompletedTurnV1.model_validate_json(turn.model_dump_json(by_alias=True))
    base = turn.base_projection
    if base.kind == "approved" and isinstance(
        base.turn.graph_context_receipt, PlayWorldGraphContextReceiptV1
    ):
        base_context = project_play_turn_context(base.turn, delivery_replay=delivery_replay)
    elif base.kind == "approved":
        base_context = project_plan_turn_context(base.turn, delivery_replay=delivery_replay)
    else:
        base_context = None
    unclaimed_context = None
    if base.kind == "unclaimed":
        from .agent_turn_service import project_plan_graph_execution_state
        unclaimed_context = AgentRulesUnclaimedContextV1(
            receipt=base.graph_context_receipt,
            execution=project_plan_graph_execution_state("response_received", completed=True),
            delivery_replay=delivery_replay,
        )
    context = AgentRulesAnswerContextV1(
        accepted_binding=turn.accepted_binding,
        accepted_binding_sha256=turn.accepted_binding_sha256,
        base_context=base_context,
        unclaimed_context=unclaimed_context,
    )
    context.validate_answer(turn.assistant_text)
    return context
