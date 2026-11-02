"""One current native retrieval commitment and selected-result owner.

The existing APP Turn/claim/capture ledger owns dispatch and selection. Core owns
native source identity and support. Surface work selection remains surface-owned.
Historical Plan codecs retain their exact readers; new native retrieval records
name neither a borrowed Plan surface nor an alternate provenance authority.
"""

from __future__ import annotations

from hashlib import sha256
import json
from typing import Literal

from pydantic import ConfigDict, Field
from . import types as t
from .jev_retrieval_contract import NativeRetrievalDecisionInputV1


class NativeBuildDecisionContextV1(t.StrictModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    context_mode: Literal["default", "long_context"]
    context_phase: Literal["navigate"]
    max_question_input_tokens: int = Field(strict=True, ge=0)
    dispatch_identity_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")


class NativeRetrievalAuthorizedV1(t.PlanJevProviderAuthorizedV1):
    """Reuses host commitment fields; actual kind/work/role are native."""

    kind: Literal["native_retrieval_authorized_v1"] = "native_retrieval_authorized_v1"
    build_context: NativeBuildDecisionContextV1 | None = None


class NativeRetrievalSelectedV1(t.PlanJevRetrievalSelectionV1):
    kind: Literal["native_retrieval_selected_v1"] = "native_retrieval_selected_v1"


def _action(execution):
    if (
        getattr(execution.policy, "policy_version", None)
        != "surface_native_execution_v1"
    ):
        return None
    from .native_execution import SurfaceNativeExecutionV1

    if type(execution) is not SurfaceNativeExecutionV1:
        raise ValueError("Native retrieval requires its concrete shared execution")
    return execution.policy.action


def owner(turn):
    from .native_context import SurfaceNativeContextReceiptV1
    from .native_execution import (
        SurfaceNativeExecutionV1,
        NativeBuildActionV1,
        NativePlanActionV1,
        validate_request_identity,
    )

    if (
        not isinstance(turn, t.Turn)
        or turn.status != "running"
        or type(turn.graph_context_receipt) is not SurfaceNativeContextReceiptV1
        or type(turn.graph_context_execution) is not SurfaceNativeExecutionV1
        or type(turn.graph_context_execution.policy.action)
        not in {NativeBuildActionV1, NativePlanActionV1}
        or turn.provenance.surface_resolution != "resolved"
        or turn.provenance.surface_id
        != turn.graph_context_execution.policy.action.surface_id
    ):
        raise ValueError("Native retrieval requires its actual running surface owner")
    validate_request_identity(
        turn.graph_context_receipt, turn.graph_context_execution, turn
    )
    return turn.graph_context_receipt, turn.graph_context_execution


def source_pins(receipt):
    from .native_corpus import NativeCorpusAuthorityV1
    from .native_plan_statements import NativePlanQueryV1

    available = isinstance(receipt.source_authority, NativeCorpusAuthorityV1)
    return dict(
        source_authority_status="available" if available else "unavailable",
        source_revision=receipt.source_authority.revision_id if available else None,
        graph_revision=receipt.native_query.authority.revision_id
        if isinstance(receipt.native_query, NativePlanQueryV1)
        else None,
    )


def scope_digest(turn):
    receipt, execution = owner(turn)
    value = dict(
        world_id=turn.world_id,
        conversation_id=str(turn.conversation_id),
        turn_id=str(turn.turn_id),
        product_attempt=turn.attempt,
        context_receipt_sha256=receipt.context_receipt_sha256,
        execution_policy_sha256=execution.execution_policy_sha256,
        **source_pins(receipt),
    )
    return sha256(
        json.dumps(
            value, sort_keys=True, separators=(",", ":"), allow_nan=False
        ).encode()
    ).hexdigest()


def controller_accounting(execution):
    action = _action(execution)
    if action is not None and action.surface_id == "build":
        return execution.policy.controller_continuation_accounting.model_dump(
            mode="json"
        )
    return None


def verify_input(turn, auth, proof):
    from .source_writer_output import strict_json
    from .jev_retrieval_contract import validate_wire_body

    receipt, execution = owner(turn)
    if (
        type(auth) is not NativeRetrievalAuthorizedV1
        or not isinstance(proof, dict)
        or set(proof) != {"parent_request_json", "request_json"}
        or not all(isinstance(value, str) for value in proof.values())
    ):
        raise ValueError(
            "Native retrieval requires exact pre-dispatch parent and SDK bytes"
        )
    parent = NativeRetrievalDecisionInputV1.model_validate(
        strict_json(proof["parent_request_json"])
    )
    role = execution.policy.provider_roles.controller
    if (
        parent.digest != auth.parent_request_sha256
        or parent.request_id != auth.decision_request_id
        or parent.question != turn.user_text
        or parent.question != execution.policy.action.intent.message
        or parent.scope_sha256 != scope_digest(turn)
        or parent.parent_attempt_id != auth.provider_attempt_id
        or any(
            getattr(parent, key) != value for key, value in source_pins(receipt).items()
        )
        or sha256(proof["request_json"].encode()).hexdigest() != auth.envelope_sha256
        or (auth.provider, auth.model, auth.api_mode) != role.identity()
        or auth.serializer_version != "typesafe-sdk-json-v1"
        or auth.tool_schema_sha256 != sha256(b"[]").hexdigest()
        or auth.included_assertion_ids
        or auth.included_relationship_ids
        or auth.included_evidence_ref_ids
        or auth.included_graph_event_ids
        or auth.included_source_read_event_ids
    ):
        raise ValueError(
            "Native retrieval input differs from its actual scope and dispatch commitment"
        )
    accounting = controller_accounting(execution)
    if accounting is None:
        if auth.build_context is not None:
            raise ValueError("Plan retrieval cannot borrow Build dispatch context")
    else:
        from .build_decision_context import validate_prepared

        validate_prepared(auth, execution, proof["request_json"])
    validate_wire_body(
        parent, proof["request_json"].encode(), controller_accounting=accounting
    )
    return parent


def verify_selection(turn, event, proof, trace):
    from .source_writer_output import strict_json
    from .jev_retrieval_contract import decode_selection, validate_source_selection
    from generationengine.types import DecisionResult

    receipt, execution = owner(turn)
    if (
        type(event) is not NativeRetrievalSelectedV1
        or not isinstance(proof, dict)
        or set(proof) != {"parent_request_json", "request_json", "response_json"}
        or not all(isinstance(value, str) for value in proof.values())
    ):
        raise ValueError(
            "Native selection requires its exact precommitted SDK producer"
        )
    providers = [
        e for e in execution.events if isinstance(e, t.ProviderAttemptAuthorizedEventV1)
    ]
    auth = providers[-1] if providers else None
    if (
        type(auth) is not NativeRetrievalAuthorizedV1
        or auth.provider_attempt_id != event.controller_attempt_id
    ):
        raise ValueError("Native selection lacks its current native controller")
    parent = verify_input(
        turn, auth, {key: proof[key] for key in ("parent_request_json", "request_json")}
    )
    raw = proof["response_json"]
    digest = sha256(raw.encode()).hexdigest()
    outcomes = [
        e
        for e in execution.events
        if isinstance(e, t.ProviderOutcomeEventV1)
        and e.provider_attempt_id == auth.provider_attempt_id
    ]
    if (
        not outcomes
        or outcomes[-1].outcome != "response_received"
        or outcomes[-1].response_sha256 not in (None, digest)
        or event.controller_response_sha256 != digest
    ):
        raise ValueError("Native selection lacks its acknowledged actual result")
    if (
        not isinstance(trace, dict)
        or trace.get("world_id") != turn.world_id
        or trace.get("conversation_id") != str(turn.conversation_id)
        or trace.get("turn_id") != str(turn.turn_id)
        or type(trace.get("attempt")) is not int
        or trace["attempt"] != turn.attempt
        or trace.get("capture_status") != "recording"
    ):
        raise ValueError("Native selection capture belongs to another request")
    captures = [
        m
        for o in trace.get("observations", [])
        if o.get("kind") == "context_snapshot" and o.get("stage") == "after"
        for m in o.get("materials", [])
        if m.get("item_id")
        == f"unvalidated-native-retrieval-result:{auth.provider_attempt_id}"
    ]
    if len(captures) != 1 or captures[0].get("text") != raw:
        raise ValueError(
            "Native selection differs from its exact protected SDK response"
        )
    result = DecisionResult.model_validate(strict_json(raw))
    selected = decode_selection(parent, result)
    pins = source_pins(receipt)
    validate_source_selection(
        parent,
        selected,
        expected_request_sha256=auth.parent_request_sha256,
        current_scope_sha256=scope_digest(turn),
        current_source_revision=pins["source_revision"],
        current_graph_revision=pins["graph_revision"],
        current_parent_attempt_id=auth.provider_attempt_id,
    )
    if (
        event.context_receipt_sha256 != execution.context_receipt_sha256
        or event.execution_policy_sha256 != execution.execution_policy_sha256
        or event.decision_request_id != parent.request_id
        or event.parent_request_sha256 != parent.digest
        or event.controller_envelope_sha256 != auth.envelope_sha256
        or event.operation != selected.operation
        or tuple(event.selected_handles) != selected.selected_handles
        or event.actual_input_tokens != result.observation.input_tokens
        or event.actual_output_tokens != result.observation.output_tokens
    ):
        raise ValueError(
            "Native selection differs from its typed result, usage or committed scope"
        )


def current_selection(turn):
    _, execution = owner(turn)
    providers = [
        e for e in execution.events if isinstance(e, t.ProviderAttemptAuthorizedEventV1)
    ]
    choices = [
        e for e in execution.events if isinstance(e, t.PlanJevRetrievalSelectionV1)
    ]
    if (
        not providers
        or not choices
        or not isinstance(providers[-1], t.PlanJevProviderAuthorizedV1)
        or choices[-1].controller_attempt_id != providers[-1].provider_attempt_id
        or choices[-1].decision_request_id != providers[-1].decision_request_id
    ):
        raise ValueError("Native acquisition decision is no longer current")
    if execution.policy.action.surface_id == "build" and (
        type(providers[-1]) is not NativeRetrievalAuthorizedV1
        or type(choices[-1]) is not NativeRetrievalSelectedV1
    ):
        raise ValueError(
            "Build acquisition cannot borrow a Plan controller or selection"
        )
    outcomes = [
        e
        for e in execution.events
        if isinstance(e, t.ProviderOutcomeEventV1)
        and e.provider_attempt_id == providers[-1].provider_attempt_id
    ]
    if not outcomes or outcomes[-1].outcome != "response_received":
        raise ValueError("Native acquisition controller has no settled result")
    return choices[-1]


def validate_decision_phases(execution):
    from . import types as t

    policy = execution.policy
    native_action = _action(execution)
    if native_action is not None:
        from .native_execution import NativeWriterAuthorizedV1
    active = native_action is not None or isinstance(policy, t.PlanJevRetrievalPolicyV1)
    if not active:
        if any(
            isinstance(
                e,
                (
                    t.PlanRequestedWorkSelectedV1,
                    t.PlanJevRetrievalSelectionV1,
                    t.PlanJevProviderAuthorizedV1,
                    t.PlanJevWriterAuthorizedV1,
                ),
            )
            for e in execution.events
        ):
            raise ValueError("Plan Jev events require their frozen Plan policy")
        return
    intent = None
    native_plan = native_action is not None and native_action.surface_id == "plan"
    native_build = native_action is not None and native_action.surface_id == "build"
    semantic_policy = native_plan or isinstance(policy, t.PlanAuthoringPolicyV1)
    placement_policy = native_plan or isinstance(
        policy, t.PlanPlacementAuthoringPolicyV1
    )
    if native_plan:
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
    retrieval_started = False
    retrieval_finished = False
    for event in execution.events:
        if isinstance(event, t.ProviderAttemptAuthorizedEventV1):
            identity = (event.provider, event.model, event.api_mode)
            if auth is not None and selected is None:
                raise ValueError(
                    "Plan controller must settle its decision before another provider"
                )
            if identity == execution.policy.provider_roles.controller.identity():
                if native_build and type(event) is t.ProviderAttemptAuthorizedEventV5:
                    if (
                        writer is not None
                        or retrieval_started
                        and not retrieval_finished
                        or pending_sources
                    ):
                        raise ValueError(
                            "Build controller cannot bypass unfinished native retrieval"
                        )
                    auth, outcome, selected = None, None, None
                    continue
                if native_build and type(event) is not NativeRetrievalAuthorizedV1:
                    raise ValueError(
                        "Build retrieval requires its neutral pre-dispatch commitment"
                    )
                if native_build and not any(
                    isinstance(
                        prior,
                        (
                            t.BuildRequestedWorkResolutionV1,
                            t.BuildReviewedActionSelectionV1,
                        ),
                    )
                    for prior in execution.events[: event.sequence]
                ):
                    raise ValueError(
                        "Build retrieval requires its actual semantic or reviewed work selection"
                    )
                semantic_auth = isinstance(event, t.PlanRequestedWorkAuthorizedV1)
                if semantic_auth != (semantic_policy and intent is None):
                    raise ValueError(
                        "Plan destination must be decided exactly once before retrieval"
                    )
                if (
                    writer is not None
                    or retrieval_finished
                    or not isinstance(event, t.PlanJevProviderAuthorizedV1)
                    or event.decision_request_id in request_ids
                ):
                    raise ValueError(
                        "Plan controller cannot resume or reuse an admitted decision"
                    )
                request_ids.add(event.decision_request_id)
                if not semantic_auth:
                    retrieval_started = True
                auth, outcome, selected = event, None, None
            else:
                if semantic_policy and (
                    intent is None
                    or intent.requested_work == "write_current_page"
                    and intent.target_capture_sha256 is None
                ):
                    raise ValueError(
                        "Plan writer lacks a resolved destination and captured edit target"
                    )
                writer_type = (
                    NativeWriterAuthorizedV1
                    if native_action is not None
                    else t.PlanJevWriterAuthorizedV1
                )
                if (
                    not isinstance(event, writer_type)
                    or pending_sources
                    or retrieval_started
                    and not retrieval_finished
                    or selected is None
                    and not native_build
                    or selected is not None
                    and selected.operation != "finish_retrieval"
                ):
                    raise ValueError(
                        "Native writer requires an explicit completed retrieval finish and settled reads"
                    )
                writer = event.provider_attempt_id
        elif (
            isinstance(event, t.ProviderOutcomeEventV1)
            and auth is not None
            and event.provider_attempt_id == auth.provider_attempt_id
        ):
            outcome = event
        elif isinstance(event, t.PlanRequestedWorkSelectedV1):
            if (
                not semantic_policy
                or intent is not None
                or not isinstance(auth, t.PlanRequestedWorkAuthorizedV1)
                or outcome is None
                or outcome.outcome != "response_received"
                or outcome.response_sha256
                not in (None, event.controller_response_sha256)
                or event.controller_attempt_id != auth.provider_attempt_id
                or event.decision_request_id != auth.decision_request_id
                or event.parent_request_sha256 != auth.parent_request_sha256
                or event.controller_envelope_sha256 != auth.envelope_sha256
                or event.context_receipt_sha256 != execution.context_receipt_sha256
                or event.execution_policy_sha256 != execution.execution_policy_sha256
                or (
                    isinstance(event, t.PlanRequestedWorkSelectedV2)
                    and (
                        not placement_policy
                        or event.original_capture_sha256 != capture_sha
                        or event.placement_catalog_sha256 != catalog_sha
                    )
                )
                or (
                    not isinstance(event, t.PlanRequestedWorkSelectedV2)
                    and (placement_policy or event.target_capture_sha256 != capture_sha)
                )
            ):
                raise ValueError(
                    "Plan destination lacks its unique acknowledged controller and frozen target"
                )
            intent = event
            auth, outcome = None, None
        elif isinstance(event, t.PlanJevRetrievalSelectionV1):
            if native_build and type(event) is not NativeRetrievalSelectedV1:
                raise ValueError("Build cannot borrow a Plan retrieval selection")
            if (
                auth is None
                or selected is not None
                or writer is not None
                or outcome is None
                or outcome.outcome != "response_received"
                or outcome.response_sha256
                not in (None, event.controller_response_sha256)
                or event.controller_attempt_id != auth.provider_attempt_id
                or event.decision_request_id != auth.decision_request_id
                or event.parent_request_sha256 != auth.parent_request_sha256
                or event.controller_envelope_sha256 != auth.envelope_sha256
                or event.context_receipt_sha256 != execution.context_receipt_sha256
                or event.execution_policy_sha256 != execution.execution_policy_sha256
            ):
                raise ValueError(
                    "Plan decision lacks its unique acknowledged controller and frozen scope"
                )
            if event.operation == "finish_retrieval" and pending_sources:
                raise ValueError(
                    "Plan retrieval cannot finish with an unresolved source read"
                )
            selected = event
            if event.operation == "finish_retrieval":
                retrieval_finished = True
        elif isinstance(
            event,
            (
                t.ValidatedGraphOperationEventV1,
                t.SourceScopeExtensionEventV3,
                t.SourceReadAuthorizationEventV2,
                t.ValidatedSourceReadEventV2,
                t.SourcePassageReuseEventV1,
                t.RelatedRecapContextAuthorizationEventV2,
                t.ValidatedRelatedRecapContextEventV2,
                t.CorpusSourceSearchAuthorizedV1,
                t.CorpusSourceSearchObservedV1,
                t.NativeSourceNavigationAuthorizedV1,
                t.NativeSourceCatalogObservedV1,
                t.NativeSourceSectionAuthorizedV1,
                t.NativeSourceSectionObservedV1,
            ),
        ) or (
            native_action is not None
            and isinstance(
                event,
                (
                    t.NativeBodySearchAuthorizedV1,
                    t.NativeBodySearchObservedV1,
                    t.NativeBodyReadAuthorizedV1,
                    t.NativeBodyReadObservedV1,
                    t.NativePlanStatementReadAuthorizedV1,
                    t.NativePlanStatementReadObservedV1,
                    t.NativePlanAssertionReadAuthorizedV1,
                    t.NativePlanAssertionReadObservedV1,
                ),
            )
        ):
            if (
                writer is not None
                or selected is None
                or selected.operation == "finish_retrieval"
            ):
                raise ValueError(
                    "Plan acquisition requires an active completed retrieval decision"
                )
            if native_action is not None:
                native_pairs = (
                    (t.NativeBodySearchAuthorizedV1, t.NativeBodySearchObservedV1),
                    (t.NativeBodyReadAuthorizedV1, t.NativeBodyReadObservedV1),
                    (
                        t.NativePlanStatementReadAuthorizedV1,
                        t.NativePlanStatementReadObservedV1,
                    ),
                    (
                        t.NativePlanAssertionReadAuthorizedV1,
                        t.NativePlanAssertionReadObservedV1,
                    ),
                )
                for grant_type, observed_type in native_pairs:
                    if isinstance(event, grant_type):
                        pending_sources.add((grant_type, event.event_id))
                    elif isinstance(event, observed_type):
                        pending_sources.discard(
                            (grant_type, event.authorization_event_id)
                        )
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
