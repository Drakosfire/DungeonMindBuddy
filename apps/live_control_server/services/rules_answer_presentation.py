"""Project accepted Rules attribution, without opening source bytes or minting authority."""
from application_state.agent_conversation.rules_authority_reads import MixedCompletedTurnV1
from apps.live_control_server.models.agent_turn import AgentRulesAnswerContextV1


def project_rules_answer_context(turn: MixedCompletedTurnV1, *, delivery_replay: bool) -> AgentRulesAnswerContextV1:
    from .agent_turn_service import project_plan_turn_context

    base = turn.base_projection
    context = AgentRulesAnswerContextV1(
        accepted_binding=turn.accepted_binding,
        accepted_binding_sha256=turn.accepted_binding_sha256,
        base_context=project_plan_turn_context(base.turn, delivery_replay=delivery_replay)
            if base.kind == "approved" else None,
    )
    context.validate_answer(turn.assistant_text)
    return context
