"""Plan-owned decision dispatch and result joins. A selection is never evidence.

The host-only parent digest stays in the ledger. Only question, labels/kinds and
closed choice instructions are transmitted. Actual Graph provider lifecycle owns
SDK entry and exact typed-response digest; no Build events are relabelled here.
"""
from __future__ import annotations

from hashlib import sha256
from .rules_authority_packet import _unique_object
import json


def strict_json(raw):
    return json.loads(raw, object_pairs_hook=_unique_object,
        parse_constant=lambda _value: (_ for _ in ()).throw(ValueError("Nonfinite Plan decision JSON")))


def _owner(turn):
    from . import types as t
    if (not isinstance(turn, t.Turn) or turn.status != "running"
            or turn.provenance.surface_id != "plan" or turn.provenance.surface_resolution != "resolved"
            or not isinstance(turn.graph_context_receipt, t.PlanWorldGraphContextReceiptV1)
            or not isinstance(turn.graph_context_execution, t.PlanWorldGraphExecutionV3)
            or not isinstance(turn.graph_context_execution.policy, t.PlanJevRetrievalPolicyV1)):
        raise ValueError("Jev decision requires the current resolved Plan owner and frozen policy")
    return turn.graph_context_receipt, turn.graph_context_execution


def scope_digest(turn):
    """Host-only binding; identical Plan content cannot transfer between turns."""
    receipt, execution = _owner(turn)
    value = {"world_id": turn.world_id, "conversation_id": str(turn.conversation_id),
        "turn_id": str(turn.turn_id), "product_attempt": turn.attempt,
        "context_receipt_sha256": receipt.context_receipt_sha256,
        "execution_policy_sha256": execution.execution_policy_sha256,
        "graph_revision": receipt.graph_authority.graph_revision}
    return sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def verify_input(turn, auth, proof):
    from . import types as t
    from .jev_retrieval_contract import RetrievalDecisionInput, validate_wire_body, MODEL, PROVIDER
    receipt, execution = _owner(turn)
    if (not isinstance(auth, t.PlanJevProviderAuthorizedV1) or not isinstance(proof, dict)
            or set(proof) != {"parent_request_json", "request_json"}):
        raise ValueError("Plan Jev authorization requires its exact prepared request proof")
    parent, raw = proof["parent_request_json"], proof["request_json"]
    if not isinstance(parent, str) or not isinstance(raw, str):
        raise ValueError("Plan decision request proof must carry exact serialized bytes")
    request = RetrievalDecisionInput.model_validate(strict_json(parent))
    if (request.digest != auth.parent_request_sha256 or request.request_id != auth.decision_request_id
            or request.question != turn.user_text or request.parent_attempt_id != auth.provider_attempt_id
            or request.scope_sha256 != scope_digest(turn)
            or request.revision != receipt.graph_authority.graph_revision
            or sha256(raw.encode()).hexdigest() != auth.envelope_sha256
            or (auth.provider, auth.model, auth.api_mode) != (PROVIDER, MODEL, "decision")
            or auth.serializer_version != "typesafe-sdk-json-v1"
            or auth.included_assertion_ids or auth.included_relationship_ids
            or auth.included_evidence_ref_ids or auth.included_graph_event_ids
            or auth.included_source_read_event_ids):
        raise ValueError("Plan Jev prepared request differs from its actual owner/authorization")
    validate_wire_body(request, raw.encode())
    return request


def verify_selection(turn, event, proof, trace):
    from . import types as t
    from .jev_retrieval_contract import decode_selection, validate_selection
    from generationengine.types import DecisionResult
    receipt, execution = _owner(turn)
    if not isinstance(proof, dict) or set(proof) != {"parent_request_json", "request_json", "response_json"}:
        raise ValueError("Plan selection requires exact producing request and typed response")
    auths = [item for item in execution.events if isinstance(item, t.ProviderAttemptAuthorizedEventV1)]
    if not auths or auths[-1].provider_attempt_id != event.controller_attempt_id:
        raise ValueError("Plan selection lacks its current controller")
    auth = auths[-1]
    request = verify_input(turn, auth, {key: proof[key] for key in ("parent_request_json", "request_json")})
    raw = proof["response_json"]
    if not isinstance(raw, str):
        raise ValueError("Plan selection requires exact serialized response bytes")
    response_digest = sha256(raw.encode()).hexdigest()
    outcomes = [item for item in execution.events if isinstance(item, t.ProviderOutcomeEventV1)
                and item.provider_attempt_id == auth.provider_attempt_id]
    if (not outcomes or outcomes[-1].outcome != "response_received"
            or outcomes[-1].response_sha256 not in (None, response_digest)
            or event.controller_response_sha256 != response_digest):
        raise ValueError("Plan decision response differs from its acknowledged actual provider outcome")
    if (not isinstance(trace, dict) or trace.get("world_id") != turn.world_id
            or trace.get("turn_id") != str(turn.turn_id)
            or trace.get("conversation_id") != str(turn.conversation_id)
            or type(trace.get("attempt")) is not int or trace["attempt"] != turn.attempt
            or trace.get("capture_status") != "recording"):
        raise ValueError("Plan decision capture differs from its current owner")
    item_id = f"unvalidated-plan-jev-result:{auth.provider_attempt_id}"
    captures = [material for observation in trace.get("observations", [])
        if observation.get("kind") == "context_snapshot" and observation.get("stage") == "after"
        for material in observation.get("materials", []) if material.get("item_id") == item_id]
    if len(captures) != 1 or captures[0].get("text") != raw:
        raise ValueError("Plan decision result differs from exact protected SDK capture")
    result = DecisionResult.model_validate(strict_json(raw))
    selected = decode_selection(request, result)
    validate_selection(request, selected, expected_request_sha256=auth.parent_request_sha256,
        current_scope_sha256=scope_digest(turn), current_revision=receipt.graph_authority.graph_revision,
        current_parent_attempt_id=auth.provider_attempt_id)
    observation = result.observation
    if (event.context_receipt_sha256 != receipt.context_receipt_sha256
            or event.execution_policy_sha256 != execution.execution_policy_sha256
            or event.decision_request_id != request.request_id
            or event.controller_envelope_sha256 != auth.envelope_sha256
            or event.parent_request_sha256 != request.digest
            or event.operation != selected.operation or tuple(event.selected_handles) != selected.selected_handles
            or event.actual_input_tokens != observation.input_tokens
            or event.actual_output_tokens != observation.output_tokens):
        raise ValueError("Plan selection/usage differs from its exact typed producer result")


def validate_decision_phases(execution):
    from . import types as t
    active = isinstance(execution.policy, t.PlanJevRetrievalPolicyV1)
    if not active:
        if any(isinstance(e, (t.PlanJevRetrievalSelectionV1, t.PlanJevProviderAuthorizedV1, t.PlanJevWriterAuthorizedV1)) for e in execution.events):
            raise ValueError("Plan Jev events require their frozen Plan policy")
        return
    auth = None
    outcome = None
    selected = None
    writer = None
    request_ids = set()
    pending_sources = set()
    for event in execution.events:
        if isinstance(event, t.ProviderAttemptAuthorizedEventV1):
            identity = (event.provider, event.model, event.api_mode)
            if auth is not None and selected is None:
                raise ValueError("Plan controller must settle its decision before another provider")
            if identity == execution.policy.provider_roles.controller.identity():
                if (writer is not None or selected is not None and selected.operation == "finish_retrieval"
                        or not isinstance(event, t.PlanJevProviderAuthorizedV1)
                        or event.decision_request_id in request_ids):
                    raise ValueError("Plan controller cannot resume or reuse an admitted decision")
                request_ids.add(event.decision_request_id)
                auth, outcome, selected = event, None, None
            else:
                if selected is None or selected.operation != "finish_retrieval" or not isinstance(event, t.PlanJevWriterAuthorizedV1):
                    raise ValueError("Plan writer requires an explicit completed retrieval finish")
                writer = event.provider_attempt_id
        elif isinstance(event, t.ProviderOutcomeEventV1) and auth is not None and event.provider_attempt_id == auth.provider_attempt_id:
            outcome = event
        elif isinstance(event, t.PlanJevRetrievalSelectionV1):
            if (auth is None or selected is not None or writer is not None
                    or outcome is None or outcome.outcome != "response_received"
                    or outcome.response_sha256 not in (None, event.controller_response_sha256)
                    or event.controller_attempt_id != auth.provider_attempt_id
                    or event.decision_request_id != auth.decision_request_id
                    or event.parent_request_sha256 != auth.parent_request_sha256
                    or event.controller_envelope_sha256 != auth.envelope_sha256
                    or event.context_receipt_sha256 != execution.context_receipt_sha256
                    or event.execution_policy_sha256 != execution.execution_policy_sha256):
                raise ValueError("Plan decision lacks its unique acknowledged controller and frozen scope")
            if event.operation == "finish_retrieval" and pending_sources:
                raise ValueError("Plan retrieval cannot finish with an unresolved source read")
            selected = event
        elif isinstance(event, (t.ValidatedGraphOperationEventV1, t.SourceScopeExtensionEventV3,
                t.SourceReadAuthorizationEventV2, t.ValidatedSourceReadEventV2, t.SourcePassageReuseEventV1,
                t.RelatedRecapContextAuthorizationEventV2, t.ValidatedRelatedRecapContextEventV2,
                t.NativeSourceNavigationAuthorizedV1, t.NativeSourceCatalogObservedV1,
                t.NativeSourceSectionAuthorizedV1, t.NativeSourceSectionObservedV1)):
            if writer is not None or selected is None or selected.operation == "finish_retrieval":
                raise ValueError("Plan acquisition requires an active completed retrieval decision")
            if isinstance(event, t.NativeSourceSectionAuthorizedV1):
                pending_sources.add(("native_section", event.read_id))
            elif isinstance(event, t.NativeSourceSectionObservedV1):
                pending_sources.discard(("native_section", event.read_id))
            elif isinstance(event, t.SourceReadAuthorizationEventV2):
                pending_sources.add(("source", event.read_call_id))
            elif isinstance(event, t.ValidatedSourceReadEventV2):
                pending_sources.discard(("source", event.read_call_id))
            elif isinstance(event, t.RelatedRecapContextAuthorizationEventV2):
                pending_sources.add(("related_recap", event.read_call_id))
            elif isinstance(event, t.ValidatedRelatedRecapContextEventV2):
                pending_sources.discard(("related_recap", event.read_call_id))


def current_selection(turn):
    """Resolve the current acknowledged controller before any parent acquisition."""
    from . import types as t
    _, execution = _owner(turn)
    providers = [event for event in execution.events if isinstance(event, t.ProviderAttemptAuthorizedEventV1)]
    selections = [event for event in execution.events if isinstance(event, t.PlanJevRetrievalSelectionV1)]
    if (not providers or not selections or not isinstance(providers[-1], t.PlanJevProviderAuthorizedV1)
            or selections[-1].controller_attempt_id != providers[-1].provider_attempt_id
            or selections[-1].decision_request_id != providers[-1].decision_request_id):
        raise ValueError("Plan acquisition decision is no longer current")
    outcomes = [event for event in execution.events if isinstance(event, t.ProviderOutcomeEventV1)
                and event.provider_attempt_id == providers[-1].provider_attempt_id]
    if not outcomes or outcomes[-1].outcome != "response_received":
        raise ValueError("Plan acquisition controller has no settled response")
    return selections[-1]
