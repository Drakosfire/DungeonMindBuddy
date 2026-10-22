"""Direct Plan Rules lookup authority from an acknowledged actual Jev choice.

The model selects a semantic public-rules offer. Current question, corpus,
operation identity and all database authority remain host-owned.
"""
from uuid import uuid4

from .jev_retrieval_contract import RetrievalCandidate, RetrievalDecisionInput
from .plan_jev_decision import _owner, scope_digest, strict_json
from .rules_authority_events import (
    RulesPlanJevToolAuthorizedV1, normalized_question, query_identity, plan_jev_rules_operation_id,
)

RULES_HANDLE = "rules:current-question"


def rules_candidate():
    return RetrievalCandidate(handle=RULES_HANDLE, label="Public game rules: D&D 2024 SRD occupancy section (not campaign lore)",
        kind="public_rules_lookup")


def _selected_offer(turn, parent_request_json):
    from .types import PlanJevRetrievalSelectionV1, PlanJevProviderAuthorizedV1, ProviderAttemptAuthorizedEventV1
    receipt, graph = _owner(turn)
    if not isinstance(parent_request_json, str):
        raise ValueError("Plan Rules read requires its exact serialized parent request")
    parent = RetrievalDecisionInput.model_validate(strict_json(parent_request_json))
    choices = [e for e in graph.events if isinstance(e, PlanJevRetrievalSelectionV1)]
    providers = [e for e in graph.events if isinstance(e, ProviderAttemptAuthorizedEventV1)]
    if not choices or not providers:
        raise ValueError("Plan Rules read requires an acknowledged selected offer")
    choice, provider = choices[-1], providers[-1]
    if (not isinstance(provider, PlanJevProviderAuthorizedV1)
            or choice.operation != "select_candidates" or RULES_HANDLE not in choice.selected_handles
            or choice.controller_attempt_id != provider.provider_attempt_id
            or choice.parent_request_sha256 != parent.digest or provider.parent_request_sha256 != parent.digest
            or choice.decision_request_id != parent.request_id or provider.decision_request_id != parent.request_id
            or parent.parent_attempt_id != provider.provider_attempt_id
            or parent.scope_sha256 != scope_digest(turn) or parent.revision != receipt.graph_authority.graph_revision
            or parent.question != turn.user_text or rules_candidate() not in parent.candidates):
        raise ValueError("Plan Rules read differs from its actual selected Jev offer")
    return choice


def prepare_authorization(execution, turn, parent_request_json):
    """Pure operation preparation; the locked APP append independently rechecks."""
    choice = _selected_offer(turn, parent_request_json)
    query = query_identity(execution.scope, turn.user_text)
    prior = [e for e in execution.events if isinstance(e, RulesPlanJevToolAuthorizedV1)
             and e.query_id == query]
    if prior:
        if len(prior) != 1:
            raise ValueError("Plan Rules decision operation is ambiguous")
        return prior[0]
    return RulesPlanJevToolAuthorizedV1(kind="plan_jev_tool_authorized", event_id=uuid4(),
        sequence=len(execution.events), execution_id=execution.scope.execution_id,
        call_id=plan_jev_rules_operation_id(choice.event_id, query), query_id=query,
        normalized_question=normalized_question(turn.user_text), packet_limit=4,
        decision_event_id=choice.event_id, origin_provider_attempt_id=choice.controller_attempt_id,
        decision_request_id=choice.decision_request_id, parent_request_sha256=choice.parent_request_sha256)


def verify_authorization(execution, turn, event, parent_request_json):
    choice = _selected_offer(turn, parent_request_json)
    scope = execution.scope
    if ((scope.world_id, scope.conversation_id, scope.turn_id, scope.product_attempt)
            != (turn.world_id, turn.conversation_id, turn.turn_id, turn.attempt)
            or event.execution_id != scope.execution_id or event.decision_event_id != choice.event_id
            or event.origin_provider_attempt_id != choice.controller_attempt_id
            or event.decision_request_id != choice.decision_request_id
            or event.parent_request_sha256 != choice.parent_request_sha256
            or event.query_id != query_identity(scope, turn.user_text)
            or event.normalized_question != normalized_question(turn.user_text)):
        raise ValueError("Plan Rules lookup differs from its current owner/decision/question")
