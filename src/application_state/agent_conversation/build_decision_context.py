"""Request-bound Build decision capability; never source or claim authority."""
from __future__ import annotations
import hashlib
import json

HISTORICAL_POLICY = "o200k_double_plus_4096_adaptive_context_v2"
HISTORICAL_SELECTION = "build_navigate_assess_if_default_exceeded_v1"
HISTORICAL_SELECTION_POLICY = "o200k_double_plus_4096_adaptive_context_v3"
POLICY = "o200k_double_plus_4096_adaptive_context_v4"
SELECTION = "build_acquisition_selection_if_default_exceeded_v2"
DEFAULT_QUESTION = 32_000
DEFAULT_REQUEST = 64_000
LONG_LIMIT = 262_000


def phase(body, *, host_phase=None):
    state = body["state"]
    if host_phase is not None:
        # Only versioned native input owners use the clean wire contract.
        if (host_phase not in {"navigate", "select", "writer_selection"} or not isinstance(state, dict)
                or any(key in state for key in ("phase", "decision", "context_accounting"))):
            raise ValueError("Native decision contains host control metadata")
        return host_phase
    value = state.get("decision", {}).get("phase", state.get("phase"))
    if value not in {"select", "navigate", "assess", "coverage", "retention", "writer_selection"}:
        raise ValueError("Prepared Build decision phase is unavailable")
    if state.get("phase", value) != value:
        raise ValueError("Prepared Build decision phase differs")
    return value


def selected_mode(phase_name, request_estimate, question_estimate, *, policy):
    eligible = {"navigate", "assess"}
    if policy in {POLICY, HISTORICAL_SELECTION_POLICY}:
        eligible.add("writer_selection")
    elif policy != HISTORICAL_POLICY:
        raise ValueError("Unknown frozen decision context policy")
    if (phase_name in eligible
            and (request_estimate > DEFAULT_REQUEST or question_estimate > DEFAULT_QUESTION)):
        return "long_context"
    return "default"


def identity(*, envelope_sha256, provider, model, api_mode, context_mode):
    value = dict(envelope_sha256=envelope_sha256, provider=provider, model=model,
                 api_mode=api_mode, context_mode=context_mode,
                 method="POST", url="https://ai-gateway.vercel.sh/typesafe/v1/systemone")
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def mode_context(event):
    """Read actual dispatch metadata; never construct a V5 authorization."""
    from . import types as t
    if type(event) is t.ProviderAttemptAuthorizedEventV5:
        return event
    from .native_retrieval import NativeRetrievalAuthorizedV1
    if type(event) is NativeRetrievalAuthorizedV1 and event.build_context is not None:
        return event.build_context
    raise ValueError("Build decision requires its actual mode-bound dispatch context")


def validate_event(event, execution):
    context = mode_context(event)
    descriptor = getattr(execution.policy, "controller_continuation_accounting", None)
    if descriptor is None or descriptor.policy not in {POLICY, HISTORICAL_SELECTION_POLICY, HISTORICAL_POLICY}:
        raise ValueError("Decision context requires its frozen adaptive accounting")
    if (event.provider, event.model, event.api_mode) != execution.policy.provider_roles.controller.identity():
        raise ValueError("Decision context role belongs only to the Build controller")
    if (event.provider, event.model, event.api_mode) != ("typesafe", "jev-1.14.0", "typesafe_decision"):
        raise ValueError("Decision context provider identity differs")
    if context.context_mode != selected_mode(context.context_phase, event.input_tokens, context.max_question_input_tokens, policy=descriptor.policy):
        raise ValueError("Decision context mode differs from frozen selection policy")
    question_limit, request_limit = ((LONG_LIMIT, LONG_LIMIT) if context.context_mode == "long_context"
                                      else (DEFAULT_QUESTION, DEFAULT_REQUEST))
    if (context.max_question_input_tokens > question_limit or event.input_tokens > request_limit
            or context.dispatch_identity_sha256 != identity(envelope_sha256=event.envelope_sha256,
                provider=event.provider, model=event.model, api_mode=event.api_mode, context_mode=context.context_mode)):
        raise ValueError("Decision context estimate or dispatch identity differs")


def uses_role_accounting(policy):
    """Dispatch only concrete policies owned by this accounting contract."""
    from . import types as t
    if isinstance(policy, t.BuildEstimatedActionControllerWriterPolicyV1):
        return True
    if getattr(policy, "policy_version", None) != "surface_native_execution_v1":
        return False
    from .native_execution import SurfaceNativeExecutionPolicyV1, NativeBuildActionV1
    return type(policy) is SurfaceNativeExecutionPolicyV1 and isinstance(policy.action, NativeBuildActionV1)


def validate_accounting(event, execution, *, provider_index):
    """Verify the original Build role estimate; never rewrite its accounting."""
    from . import types as t
    policy = execution.policy
    if not uses_role_accounting(policy):
        raise ValueError("Build role accounting requires its frozen concrete policy")
    native = not isinstance(policy, t.BuildEstimatedActionControllerWriterPolicyV1)
    role = (event.provider, event.model, event.api_mode)
    controller = policy.provider_roles.controller.identity()
    writer = policy.provider_roles.writer.identity()
    reviewed_writer = any(isinstance(e, t.BuildReviewedActionSelectionV1)
        and e.operation == "propose_build_insertion" and e.sequence < event.sequence
        for e in execution.events)
    if role not in {controller, writer} or (provider_index == 0 and role != controller and not reviewed_writer):
        raise ValueError("provider accounting role differs from frozen policy")
    if (native or isinstance(policy, t.BuildWriterBudgetActionControllerWriterPolicyV1)) and role == writer:
        budget = policy.writer_context_budget
        if (event.output_token_reserve != budget.output_reserve_tokens
                or budget.context_limit_tokens is not None
                and event.input_tokens + event.output_token_reserve > budget.context_limit_tokens):
            raise ValueError("writer envelope exceeds its frozen role budget")
    estimated = role == controller and (native or provider_index > 0
        or isinstance(policy, t.BuildInitialEstimatedSelectedSourcePolicyV1))
    descriptor = policy.controller_continuation_accounting
    from .native_execution import NativeWriterEstimatedBudgetV1
    counted_writer = native and role == writer and isinstance(policy.writer_context_budget, NativeWriterEstimatedBudgetV1)
    kind = "estimated_token_count" if estimated or counted_writer else policy.provider_input_accounting.kind
    estimator = (descriptor.policy if estimated else policy.writer_context_budget.estimator
        if counted_writer else policy.provider_input_accounting.estimator)
    if counted_writer and event.input_tokens < descriptor.reserve:
        raise ValueError('Native writer estimate omitted its frozen accounting margin')
    if event.input_accounting_kind != kind or event.input_estimator != estimator:
        raise ValueError("provider attempt accounting differs from accepted role policy")
    if descriptor.policy in {HISTORICAL_POLICY, HISTORICAL_SELECTION_POLICY, POLICY} and role == controller:
        mode_context(event)
        validate_event(event, execution)
    elif isinstance(event, t.ProviderAttemptAuthorizedEventV5):
        raise ValueError("Mode-bound authorization requires current Build accounting")
    if estimated and descriptor.policy not in {HISTORICAL_POLICY,HISTORICAL_SELECTION_POLICY,POLICY} and event.input_tokens > descriptor.request_limit_tokens:
        raise ValueError("controller request estimate exceeds frozen policy")


def validate_prepared(event, execution, raw, *, host_phase=None):
    validate_event(event, execution)
    context = mode_context(event)
    if not isinstance(raw, str):
        raise ValueError("Decision context requires exact prepared bytes")
    # Historical records keep the admission contract that was accepted then.
    byte_limit = execution.policy.controller_continuation_accounting.raw_wire_limit_bytes
    if byte_limit is not None and len(raw.encode()) > byte_limit:
        raise ValueError("Decision context exceeds its frozen historical byte bound")
    if hashlib.sha256(raw.encode()).hexdigest() != event.envelope_sha256:
        raise ValueError("Decision context body hash differs")
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("Duplicate decision context key")
            result[key] = value
        return result
    body = json.loads(raw, object_pairs_hook=unique)
    if (set(body) != {"model", "state", "questions"} or body["model"] != event.model
            or not isinstance(body["questions"], dict) or not body["questions"]
            or phase(body, host_phase=host_phase) != context.context_phase
            or host_phase is None and body["state"].get("context_accounting") != execution.policy.controller_continuation_accounting.model_dump(mode="json")):
        raise ValueError("Prepared context phase or accounting differs from frozen execution")
