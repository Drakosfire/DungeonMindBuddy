"""Plan Graph-need producer helpers; no operation here grants append authority."""
from hashlib import sha256

from generationengine.types import DecisionResult

from .native_plan_graph_need import NativePlanGraphNeedInputV1, NativePlanGraphNeedObservedV1, decode_decision
from .native_retrieval import NativePlanGraphNeedAuthorizedV1


def observed_from_sdk_result(context, execution, *, event_id, result):
    """Construct an observation only from a typed SDK result and admitted prefix.

    The transaction owner must call this from its trusted SDK callback; this
    function cannot establish that an arbitrary caller supplied the SDK result.
    """
    from .native_execution import validate_context_binding

    if type(result) is not DecisionResult:
        raise ValueError('Plan Graph-need observation requires its typed SDK result')
    validate_context_binding(context, execution)
    auths = [event for event in execution.events if type(event) is NativePlanGraphNeedAuthorizedV1]
    if len(auths) != 1 or any(type(event) is NativePlanGraphNeedObservedV1 for event in execution.events):
        raise ValueError('Plan Graph-need observation requires one unresolved authorization')
    auth = auths[0]
    parent = NativePlanGraphNeedInputV1.model_validate_json(auth.parent_json)
    choice = decode_decision(parent, result, expected_model=auth.model)
    raw = result.model_dump_json()
    observed = NativePlanGraphNeedObservedV1(event_id=event_id, sequence=len(execution.events),
        controller_attempt_id=auth.provider_attempt_id, decision_request_id=auth.decision_request_id,
        context_receipt_sha256=execution.context_receipt_sha256,
        execution_policy_sha256=execution.execution_policy_sha256, parent=parent,
        envelope_sha256=auth.envelope_sha256, result_json=raw,
        result_sha256=sha256(raw.encode('utf-8')).hexdigest(), choice=choice)
    prospective = execution.model_copy(update={'events': [*execution.events, observed]})
    validate_context_binding(context, prospective)
    return observed
