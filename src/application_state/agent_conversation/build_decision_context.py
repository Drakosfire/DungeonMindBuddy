"""Request-bound Build decision capability; never source or claim authority."""
from __future__ import annotations
import hashlib
import json

HISTORICAL_POLICY = "o200k_double_plus_4096_adaptive_context_v2"
HISTORICAL_SELECTION = "build_navigate_assess_if_default_exceeded_v1"
POLICY = "o200k_double_plus_4096_adaptive_context_v3"
SELECTION = "build_acquisition_selection_if_default_exceeded_v2"
DEFAULT_QUESTION = 32_000
DEFAULT_REQUEST = 64_000
LONG_LIMIT = 262_000
RAW_LIMIT = 256_000


def phase(body):
    state = body["state"]
    value = state.get("decision", {}).get("phase", state.get("phase"))
    if value not in {"select", "navigate", "assess", "coverage", "retention", "writer_selection"}:
        raise ValueError("Prepared Build decision phase is unavailable")
    if state.get("phase", value) != value:
        raise ValueError("Prepared Build decision phase differs")
    return value


def selected_mode(phase_name, request_estimate, question_estimate, *, policy):
    eligible = {"navigate", "assess"}
    if policy == POLICY:
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


def validate_event(event, execution):
    descriptor = getattr(execution.policy, "controller_continuation_accounting", None)
    if descriptor is None or descriptor.policy not in {POLICY, HISTORICAL_POLICY}:
        raise ValueError("Decision context requires its frozen adaptive accounting")
    if (event.provider, event.model, event.api_mode) != execution.policy.provider_roles.controller.identity():
        raise ValueError("Decision context role belongs only to the Build controller")
    if (event.provider, event.model, event.api_mode) != ("typesafe", "jev-1.14.0", "typesafe_decision"):
        raise ValueError("Decision context provider identity differs")
    if event.context_mode != selected_mode(event.context_phase, event.input_tokens, event.max_question_input_tokens, policy=descriptor.policy):
        raise ValueError("Decision context mode differs from frozen selection policy")
    question_limit, request_limit = ((LONG_LIMIT, LONG_LIMIT) if event.context_mode == "long_context"
                                      else (DEFAULT_QUESTION, DEFAULT_REQUEST))
    if (event.max_question_input_tokens > question_limit or event.input_tokens > request_limit
            or event.dispatch_identity_sha256 != identity(envelope_sha256=event.envelope_sha256,
                provider=event.provider, model=event.model, api_mode=event.api_mode, context_mode=event.context_mode)):
        raise ValueError("Decision context estimate or dispatch identity differs")


def validate_prepared(event, execution, raw):
    validate_event(event, execution)
    if not isinstance(raw, str) or len(raw.encode()) > RAW_LIMIT:
        raise ValueError("Decision context requires exact bounded prepared bytes")
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
            or phase(body) != event.context_phase
            or body["state"].get("context_accounting") != execution.policy.controller_continuation_accounting.model_dump(mode="json")):
        raise ValueError("Prepared context phase or accounting differs from frozen execution")
