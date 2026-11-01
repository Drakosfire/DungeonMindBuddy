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
            or not (
                (isinstance(turn.graph_context_receipt, t.PlanSourceContextReceiptV1)
                 and isinstance(turn.graph_context_execution, t.PlanSourceExecutionV1))
                or (isinstance(turn.graph_context_receipt, t.PlanWorldGraphContextReceiptV1)
                    and isinstance(turn.graph_context_execution, t.PlanWorldGraphExecutionV3)
                    and not isinstance(turn.graph_context_execution, t.PlanSourceExecutionV1)))
            or not isinstance(turn.graph_context_execution.policy, t.PlanJevRetrievalPolicyV1)):
        raise ValueError("Jev decision requires the current resolved Plan owner and frozen policy")
    return turn.graph_context_receipt, turn.graph_context_execution


def _native_plan_action(execution):
    if getattr(execution.policy, "policy_version", None) != "surface_native_execution_v1":
        return None
    from .native_execution import SurfaceNativeExecutionV1, NativePlanActionV1
    if type(execution) is SurfaceNativeExecutionV1:
        if not isinstance(execution.policy.action, NativePlanActionV1):
            raise ValueError("Plan decision proof requires its actual Plan action")
        return execution.policy.action
    return None


def scope_digest(turn):
    """Host-only binding; identical Plan content cannot transfer between turns."""
    receipt, execution = _owner(turn)
    return _scope_digest(receipt, execution, world_id=turn.world_id,
        conversation_id=turn.conversation_id, turn_id=turn.turn_id, attempt=turn.attempt)


def _scope_digest(receipt, execution, *, world_id, conversation_id, turn_id, attempt):
    from . import types as t
    native_action = _native_plan_action(execution)
    if native_action is not None and world_id != native_action.intent.world_id:
        raise ValueError("Plan decision scope differs from its actual work World")
    value = {"world_id": world_id, "conversation_id": str(conversation_id),
        "turn_id": str(turn_id), "product_attempt": attempt,
        "context_receipt_sha256": receipt.context_receipt_sha256,
        "execution_policy_sha256": execution.execution_policy_sha256}
    if native_action is not None or isinstance(receipt, t.PlanSourceContextReceiptV1):
        value.update(_source_pins(receipt))
    else:
        value["graph_revision"] = receipt.graph_authority.graph_revision
    return sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def _source_pins(receipt):
    from .native_corpus import NativeCorpusAuthorityV1
    from .native_context import SurfaceNativeContextReceiptV1
    from .native_plan_statements import NativePlanQueryV1
    available = isinstance(receipt.source_authority, NativeCorpusAuthorityV1)
    if type(receipt) is SurfaceNativeContextReceiptV1:
        graph_revision = receipt.native_query.authority.revision_id if isinstance(receipt.native_query, NativePlanQueryV1) else None
    else:
        graph_revision = receipt.graph_capability.graph_authority.graph_revision if receipt.graph_capability is not None else None
    return {"source_authority_status": "available" if available else "unavailable",
        "source_revision": receipt.source_authority.revision_id if available else None,
        "graph_revision": graph_revision}


def verify_input(turn, auth, proof):
    receipt, execution = _owner(turn)
    return verify_input_records(receipt, execution, auth, proof, question=turn.user_text,
        scope_sha256=_scope_digest(receipt, execution, world_id=turn.world_id,
            conversation_id=turn.conversation_id, turn_id=turn.turn_id, attempt=turn.attempt))


def verify_input_records(receipt, execution, auth, proof, *, question, scope_sha256):
    """Exact SDK input proof only; the locked Turn owner grants dispatch."""
    from . import types as t
    from .jev_retrieval_contract import RetrievalDecisionInput, PlanSourceRetrievalDecisionInputV1, validate_wire_body, MODEL, PROVIDER
    native_action = _native_plan_action(execution)
    if native_action is not None:
        from .native_reads import validate_execution_binding
        validate_execution_binding(receipt, execution)
        if question != native_action.intent.message:
            raise ValueError("Plan decision changed its actual submitted question")
    if (not isinstance(auth, t.PlanJevProviderAuthorizedV1) or not isinstance(proof, dict)
            or set(proof) != {"parent_request_json", "request_json"}):
        raise ValueError("Plan Jev authorization requires its exact prepared request proof")
    parent, raw = proof["parent_request_json"], proof["request_json"]
    if not isinstance(parent, str) or not isinstance(raw, str):
        raise ValueError("Plan decision request proof must carry exact serialized bytes")
    semantic = isinstance(auth, t.PlanRequestedWorkAuthorizedV1)
    if semantic:
        from .plan_authoring import PlanRequestedWorkInputV1, validate_requested_work_wire
        if native_action is None and not isinstance(execution.policy, t.PlanAuthoringPolicyV1):
            raise ValueError('Plan destination decision requires its frozen authoring policy')
        from .plan_placement import PlanRequestedWorkInputV2, PlanRequestedWorkInputV3
        placement = isinstance(auth, t.PlanRequestedWorkAuthorizedV2)
        if placement != (native_action is not None or isinstance(execution.policy, t.PlanPlacementAuthoringPolicyV1)):
            raise ValueError('Plan placement authorization differs from its current policy')
        parent_value = strict_json(parent)
        schema = parent_value.get("schema") if isinstance(parent_value, dict) else None
        if placement:
            parent_type = {
                "dmb_plan_requested_work_input_v2": PlanRequestedWorkInputV2,
                "dmb_plan_requested_work_input_v3": PlanRequestedWorkInputV3,
            }.get(schema)
        else:
            parent_type = PlanRequestedWorkInputV1 if schema == "dmb_plan_requested_work_input_v1" else None
        if parent_type is None:
            raise ValueError("Unknown Plan requested-work parent contract")
        request = parent_type.model_validate(parent_value)
        capture_sha = native_action.intent.plan_authoring_capture_sha256 if native_action is not None else execution.policy.plan_authoring_capture_sha256
        catalog_sha = native_action.intent.plan_placement_catalog_sha256 if native_action is not None else getattr(execution.policy, "placement_catalog_sha256", None)
        if placement and (request.placement_catalog.sha256 if request.placement_catalog is not None else None) != catalog_sha:
            raise ValueError('Plan placement catalog differs from its frozen current intent')
        if request.target_capture_sha256 != capture_sha:
            raise ValueError('Plan semantic target differs from its frozen capture')
    else:
        parent_type = PlanSourceRetrievalDecisionInputV1 if native_action is not None or isinstance(receipt, t.PlanSourceContextReceiptV1) else RetrievalDecisionInput
        request = parent_type.model_validate(strict_json(parent))
    pins_match = True
    if not semantic:
        pins_match = (all(getattr(request, key) == value for key, value in _source_pins(receipt).items())
            if native_action is not None or isinstance(receipt, t.PlanSourceContextReceiptV1)
            else request.revision == receipt.graph_authority.graph_revision)
    if (request.digest != auth.parent_request_sha256 or request.request_id != auth.decision_request_id
            or request.question != question or request.parent_attempt_id != auth.provider_attempt_id
            or request.scope_sha256 != scope_sha256
            or not pins_match
            or sha256(raw.encode()).hexdigest() != auth.envelope_sha256
            or (auth.provider, auth.model, auth.api_mode) != (PROVIDER, MODEL, "decision")
            or auth.serializer_version != "typesafe-sdk-json-v1"
            or auth.included_assertion_ids or auth.included_relationship_ids
            or auth.included_evidence_ref_ids or auth.included_graph_event_ids
            or auth.included_source_read_event_ids):
        raise ValueError("Plan Jev prepared request differs from its actual owner/authorization")
    if semantic:
        validate_requested_work_wire(request, raw.encode())
    else:
        validate_wire_body(request, raw.encode())
    return request


def verify_selection(turn, event, proof, trace):
    receipt, execution = _owner(turn)
    return verify_selection_records(receipt, execution, event, proof, trace, question=turn.user_text,
        world_id=turn.world_id, conversation_id=turn.conversation_id, turn_id=turn.turn_id, attempt=turn.attempt)


def verify_selection_records(receipt, execution, event, proof, trace, *, question,
                             world_id, conversation_id, turn_id, attempt):
    """Exact producing result proof; this neither appends nor authorizes reads."""
    from . import types as t
    from .jev_retrieval_contract import decode_selection, validate_selection, validate_source_selection
    from generationengine.types import DecisionResult
    native_action = _native_plan_action(execution)
    scope_sha256 = _scope_digest(receipt, execution, world_id=world_id,
        conversation_id=conversation_id, turn_id=turn_id, attempt=attempt)
    if not isinstance(proof, dict) or set(proof) != {"parent_request_json", "request_json", "response_json"}:
        raise ValueError("Plan selection requires exact producing request and typed response")
    auths = [item for item in execution.events if isinstance(item, t.ProviderAttemptAuthorizedEventV1)]
    if not auths or auths[-1].provider_attempt_id != event.controller_attempt_id:
        raise ValueError("Plan selection lacks its current controller")
    auth = auths[-1]
    request = verify_input_records(receipt, execution, auth, {key: proof[key] for key in ("parent_request_json", "request_json")}, question=question, scope_sha256=scope_sha256)
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
    if (not isinstance(trace, dict) or trace.get("world_id") != world_id
            or trace.get("turn_id") != str(turn_id)
            or trace.get("conversation_id") != str(conversation_id)
            or type(trace.get("attempt")) is not int or trace["attempt"] != attempt
            or trace.get("capture_status") != "recording"):
        raise ValueError("Plan decision capture differs from its current owner")
    item_id = f"unvalidated-plan-jev-result:{auth.provider_attempt_id}"
    captures = [material for observation in trace.get("observations", [])
        if observation.get("kind") == "context_snapshot" and observation.get("stage") == "after"
        for material in observation.get("materials", []) if material.get("item_id") == item_id]
    if len(captures) != 1 or captures[0].get("text") != raw:
        raise ValueError("Plan decision result differs from exact protected SDK capture")
    result = DecisionResult.model_validate(strict_json(raw))
    semantic = isinstance(event, t.PlanRequestedWorkSelectedV1)
    if semantic != isinstance(auth, t.PlanRequestedWorkAuthorizedV1):
        raise ValueError('Plan decision kind differs from its actual producer')
    if semantic:
        from .plan_authoring import decode_requested_work_decision
        from .plan_placement import PlanRequestedWorkInputV2
        selected = decode_requested_work_decision(request, result)
        if isinstance(event, t.PlanRequestedWorkSelectedV2):
            from .plan_placement import PlanRequestedWorkInputV2, work_choice
            if not isinstance(request, PlanRequestedWorkInputV2):
                raise ValueError('Plan placement selection lacks its exact V2 producer')
            fields = work_choice(request, selected)
            if (any(getattr(event, key) != value for key, value in fields.items())
                    or event.original_capture != (request.original_capture.model_dump(mode='json',by_alias=True) if request.original_capture is not None else None)
                    or event.placement_catalog != (request.placement_catalog.model_dump(mode='json',by_alias=True) if request.placement_catalog is not None else None)
                    or event.original_capture_sha256 != request.target_capture_sha256
                    or event.placement_catalog_sha256 != (request.placement_catalog.sha256 if request.placement_catalog is not None else None)):
                raise ValueError('Plan placement differs from its exact offered typed result')
        elif (isinstance(request, PlanRequestedWorkInputV2)
                or event.requested_work != selected or event.target_capture_sha256 != request.target_capture_sha256):
            raise ValueError('Plan destination differs from its exact typed result or capture')
    else:
        selected = decode_selection(request, result)
        if native_action is not None or isinstance(receipt, t.PlanSourceContextReceiptV1):
            pins = _source_pins(receipt)
            validate_source_selection(request, selected, expected_request_sha256=auth.parent_request_sha256,
                current_scope_sha256=scope_sha256, current_source_revision=pins["source_revision"],
                current_graph_revision=pins["graph_revision"], current_parent_attempt_id=auth.provider_attempt_id)
        else:
            validate_selection(request, selected, expected_request_sha256=auth.parent_request_sha256,
                current_scope_sha256=scope_sha256, current_revision=receipt.graph_authority.graph_revision,
                current_parent_attempt_id=auth.provider_attempt_id)
    observation = result.observation
    if (event.context_receipt_sha256 != receipt.context_receipt_sha256
            or event.execution_policy_sha256 != execution.execution_policy_sha256
            or event.decision_request_id != request.request_id
            or event.controller_envelope_sha256 != auth.envelope_sha256
            or event.parent_request_sha256 != request.digest
            or (not semantic and (event.operation != selected.operation or tuple(event.selected_handles) != selected.selected_handles))
            or event.actual_input_tokens != observation.input_tokens
            or event.actual_output_tokens != observation.output_tokens):
        raise ValueError("Plan selection/usage differs from its exact typed producer result")


def validate_decision_phases(execution):
    from . import types as t
    policy = execution.policy
    native_action = _native_plan_action(execution)
    if native_action is not None:
        from .native_execution import NativeWriterAuthorizedV1
    active = native_action is not None or isinstance(policy, t.PlanJevRetrievalPolicyV1)
    if not active:
        if any(isinstance(e, (t.PlanRequestedWorkSelectedV1, t.PlanJevRetrievalSelectionV1, t.PlanJevProviderAuthorizedV1, t.PlanJevWriterAuthorizedV1)) for e in execution.events):
            raise ValueError("Plan Jev events require their frozen Plan policy")
        return
    intent = None
    semantic_policy = native_action is not None or isinstance(policy, t.PlanAuthoringPolicyV1)
    placement_policy = native_action is not None or isinstance(policy, t.PlanPlacementAuthoringPolicyV1)
    if native_action is not None:
        capture_sha = native_action.intent.plan_authoring_capture_sha256
        catalog_sha = native_action.intent.plan_placement_catalog_sha256
    else:
        capture_sha = getattr(policy, "plan_authoring_capture_sha256", None)
        catalog_sha = getattr(policy, "placement_catalog_sha256", None)
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
                semantic_auth = isinstance(event, t.PlanRequestedWorkAuthorizedV1)
                if semantic_auth != (semantic_policy and intent is None):
                    raise ValueError('Plan destination must be decided exactly once before retrieval')
                if (writer is not None or selected is not None and selected.operation == "finish_retrieval"
                        or not isinstance(event, t.PlanJevProviderAuthorizedV1)
                        or event.decision_request_id in request_ids):
                    raise ValueError("Plan controller cannot resume or reuse an admitted decision")
                request_ids.add(event.decision_request_id)
                auth, outcome, selected = event, None, None
            else:
                if (semantic_policy and (intent is None or intent.requested_work == 'write_current_page'
                        and intent.target_capture_sha256 is None)):
                    raise ValueError('Plan writer lacks a resolved destination and captured edit target')
                writer_type = NativeWriterAuthorizedV1 if native_action is not None else t.PlanJevWriterAuthorizedV1
                if selected is None or selected.operation != "finish_retrieval" or not isinstance(event, writer_type):
                    raise ValueError("Plan writer requires an explicit completed retrieval finish")
                writer = event.provider_attempt_id
        elif isinstance(event, t.ProviderOutcomeEventV1) and auth is not None and event.provider_attempt_id == auth.provider_attempt_id:
            outcome = event
        elif isinstance(event, t.PlanRequestedWorkSelectedV1):
            if (not semantic_policy or intent is not None or not isinstance(auth, t.PlanRequestedWorkAuthorizedV1)
                    or outcome is None or outcome.outcome != 'response_received'
                    or outcome.response_sha256 not in (None, event.controller_response_sha256)
                    or event.controller_attempt_id != auth.provider_attempt_id
                    or event.decision_request_id != auth.decision_request_id
                    or event.parent_request_sha256 != auth.parent_request_sha256
                    or event.controller_envelope_sha256 != auth.envelope_sha256
                    or event.context_receipt_sha256 != execution.context_receipt_sha256
                    or event.execution_policy_sha256 != execution.execution_policy_sha256
                    or (isinstance(event, t.PlanRequestedWorkSelectedV2)
                        and (not placement_policy
                            or event.original_capture_sha256 != capture_sha
                            or event.placement_catalog_sha256 != catalog_sha))
                    or (not isinstance(event, t.PlanRequestedWorkSelectedV2)
                        and (placement_policy
                            or event.target_capture_sha256 != capture_sha))):
                raise ValueError('Plan destination lacks its unique acknowledged controller and frozen target')
            intent = event
            auth, outcome = None, None
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
                t.CorpusSourceSearchAuthorizedV1, t.CorpusSourceSearchObservedV1,
                t.NativeSourceNavigationAuthorizedV1, t.NativeSourceCatalogObservedV1,
                t.NativeSourceSectionAuthorizedV1, t.NativeSourceSectionObservedV1)) or (native_action is not None
                and isinstance(event, (t.NativeBodySearchAuthorizedV1, t.NativeBodySearchObservedV1,
                    t.NativeBodyReadAuthorizedV1, t.NativeBodyReadObservedV1,
                    t.NativePlanStatementReadAuthorizedV1, t.NativePlanStatementReadObservedV1,
                    t.NativePlanAssertionReadAuthorizedV1, t.NativePlanAssertionReadObservedV1))):
            if writer is not None or selected is None or selected.operation == "finish_retrieval":
                raise ValueError("Plan acquisition requires an active completed retrieval decision")
            if native_action is not None:
                native_pairs = (
                    (t.NativeBodySearchAuthorizedV1, t.NativeBodySearchObservedV1),
                    (t.NativeBodyReadAuthorizedV1, t.NativeBodyReadObservedV1),
                    (t.NativePlanStatementReadAuthorizedV1, t.NativePlanStatementReadObservedV1),
                    (t.NativePlanAssertionReadAuthorizedV1, t.NativePlanAssertionReadObservedV1),
                )
                for grant_type, observed_type in native_pairs:
                    if isinstance(event, grant_type):
                        pending_sources.add((grant_type, event.event_id))
                    elif isinstance(event, observed_type):
                        pending_sources.discard((grant_type, event.authorization_event_id))
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
