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


def validate_prepared_authorization(context, execution, authorization, raw):
    """Prove a pending Graph decision's exact SDK wire before any dispatch."""
    from . import types as t
    from .native_execution import validate_context_binding
    from .native_plan_graph_need import validate_wire
    from .native_writer import json_container_count
    from .plan_authoring import strict_json

    if type(authorization) is not NativePlanGraphNeedAuthorizedV1 or type(raw) is not bytes:
        raise ValueError('Graph-need authorization requires its exact typed authorization and prepared bytes')
    validate_context_binding(context, execution)
    if any(isinstance(event, t.ProviderAttemptAuthorizedEventV1) for event in execution.events):
        raise ValueError('Graph-need dispatch must be the first provider attempt')
    if authorization.sequence != len(execution.events):
        raise ValueError('Graph-need authorization sequence is stale')
    parent = NativePlanGraphNeedInputV1.model_validate_json(authorization.parent_json)
    validate_wire(parent, raw, expected_model=authorization.model)
    expected_tokens = len(raw) + 64 * (1 + json_container_count(strict_json(raw.decode('utf-8'))))
    if (authorization.envelope_sha256 != sha256(raw).hexdigest()
            or authorization.input_accounting_kind != 'conservative_upper_bound'
            or authorization.input_estimator != context.assembled_input.tokenizer_name
            or authorization.input_tokens != expected_tokens):
        raise ValueError('Graph-need authorization differs from its exact prepared wire accounting')
    t.validate_provider_envelope_accounting(context.assembled_input, execution, authorization)
    prospective = execution.model_copy(update={'events': [*execution.events, authorization]})
    validate_context_binding(context, prospective)
    return prospective


def query_transition(context, execution, *, action, event_id, query=None, reason=None):
    """Derive a single query transition from its already retained predecessor."""
    from . import types as t
    from .native_context import NativePlanGraphQueryPendingV1
    from .native_execution import validate_context_binding
    from .native_plan_graph_need import (
        NativePlanGraphQueryAuthorizedV1, NativePlanGraphQueryStartedV1,
        NativePlanGraphQueryClosedV1, NativePlanGraphQuerySettledV1, NativePlanGraphQueryFailedV1,
    )
    validate_context_binding(context, execution)
    if type(context.native_query) is not NativePlanGraphQueryPendingV1:
        raise ValueError('Graph transition requires a pending Plan query')
    events = execution.events
    needs = [e for e in events if type(e) is NativePlanGraphNeedObservedV1]
    grants = [e for e in events if type(e) is NativePlanGraphQueryAuthorizedV1]
    starts = [e for e in events if type(e) is NativePlanGraphQueryStartedV1]
    sequence = len(events)
    pending_sha = t.canonical_sha256(context.native_query)
    common = dict(event_id=event_id, sequence=sequence)
    if action == 'authorize' and len(needs) == 1 and query is None and reason is None:
        event = NativePlanGraphQueryAuthorizedV1(**common, need_event_id=needs[0].event_id,
            pending_query_sha256=pending_sha)
    elif action == 'close' and len(needs) == 1 and query is None and reason is None:
        event = NativePlanGraphQueryClosedV1(**common, need_event_id=needs[0].event_id,
            pending_query_sha256=pending_sha)
    elif action == 'start' and len(grants) == 1 and query is None and reason is None:
        event = NativePlanGraphQueryStartedV1(**common, authorization_event_id=grants[0].event_id)
    elif action == 'settle' and len(starts) == 1 and query is not None and reason is None:
        event = NativePlanGraphQuerySettledV1(**common, started_event_id=starts[0].event_id, query=query)
    elif action == 'fail' and len(starts) == 1 and query is None and reason is not None:
        event = NativePlanGraphQueryFailedV1(**common, started_event_id=starts[0].event_id, reason=reason)
    else:
        raise ValueError('Graph transition requires its exact retained predecessor and typed result')
    prospective = execution.model_copy(update={'events': [*events, event]})
    return event, validate_context_binding(context, prospective)
