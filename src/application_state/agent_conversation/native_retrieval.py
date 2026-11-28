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
from uuid import UUID

from pydantic import ConfigDict, Field
from . import types as t
from .jev_retrieval_contract import parse_native_retrieval_input


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
    play_intent_opening: Literal[True] | None = Field(default=None, exclude_if=lambda value: value is None)


class NativePlanOpeningAuthorizedV1(t.PlanRequestedWorkAuthorizedV2):
    """One actual SDK envelope explicitly produces work and its first batch."""
    kind: Literal['native_plan_opening_authorized_v1'] = 'native_plan_opening_authorized_v1'
    author_scope_event_id: UUID | None = Field(default=None, exclude_if=lambda value: value is None)


class NativePlanAuthorScopeAuthorizedV1(t.PlanRequestedWorkAuthorizedV2):
    """Source-blind interpretation input. It cannot settle opening work."""

    kind: Literal['native_plan_author_scope_authorized_v1'] = 'native_plan_author_scope_authorized_v1'
    intent_opening: Literal[True] | None = Field(default=None, exclude_if=lambda value: value is None)
    prior_scope_event_id: UUID | None = Field(default=None, exclude_if=lambda value: value is None)
    scope_review_event_ids: tuple[UUID, UUID] | None = Field(
        default=None, exclude_if=lambda value: value is None)


class NativeRetrievalSelectedV1(t.PlanJevRetrievalSelectionV1):
    kind: Literal["native_retrieval_selected_v1"] = "native_retrieval_selected_v1"


class NativeRetrievalSelectedV2(NativeRetrievalSelectedV1):
    kind: Literal['native_retrieval_selected_v2'] = 'native_retrieval_selected_v2'
    post_read_plan: Literal['review_after_reads', 'finish_if_selected_reads_succeed']
    exhausted_continuation_offer: Literal[True] | None = Field(
        default=None, exclude_if=lambda value: value is None)


class NativePlayIntentSelectedV1(NativeRetrievalSelectedV1):
    kind: Literal["native_play_intent_selected_v1"] = "native_play_intent_selected_v1"
    requested_work: str

    @property
    def defers_source_reads(self) -> bool:
        return self.requested_work in {"clarify_request", "different_destination", "play_edit"}


NATIVE_RETRIEVAL_SELECTION_TYPES = (
    NativeRetrievalSelectedV1, NativeRetrievalSelectedV2, NativePlayIntentSelectedV1,
)


def native_selection_types():
    """Closed native acquisition selections, including the real opening batch."""
    from .native_execution import NATIVE_PLAN_OPENING_SELECTION_TYPES
    return (*NATIVE_RETRIEVAL_SELECTION_TYPES, *NATIVE_PLAN_OPENING_SELECTION_TYPES)


def prospective_selection_types():
    from .native_execution import NATIVE_PLAN_OPENING_SELECTION_TYPES
    return (NativeRetrievalSelectedV2, *NATIVE_PLAN_OPENING_SELECTION_TYPES)


class NativeReadBatchConcludedV1(t.StrictModel):
    """APP fulfillment of a real prospective plan, not a provider response."""
    kind: Literal['native_read_batch_concluded_v1'] = 'native_read_batch_concluded_v1'
    event_id: UUID
    sequence: int = Field(ge=0, strict=True)
    selection_event_id: UUID
    read_event_ids: tuple[UUID, ...]
    exhausted_continuation: Literal[True] | None = Field(
        default=None, exclude_if=lambda value: value is None)


def _action(execution):
    from .native_execution import BuildPendingExecutionV1, BuildPendingExecutionPolicyV1, NativeBuildSourceSettledV1
    if type(execution.policy) is BuildPendingExecutionPolicyV1:
        if type(execution) is not BuildPendingExecutionV1:
            raise ValueError('Pending retrieval requires its concrete Build execution')
        return execution.policy.action if any(type(row) is NativeBuildSourceSettledV1 for row in execution.events) else None
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
    from .native_context import BuildPendingContextReceiptV1
    if type(getattr(turn, 'graph_context_receipt', None)) is BuildPendingContextReceiptV1:
        from .build_pending_native import pending_native_owner
        return pending_native_owner(turn)
    from .native_context import SurfaceNativeContextReceiptV1
    from .native_execution import (
        SurfaceNativeExecutionV1,
        NativeBuildActionV1,
        NativePlanActionV1, NativePlayActionV1, NATIVE_PLAN_ACTION_TYPES,
        validate_request_identity,
    )

    if (
        not isinstance(turn, t.Turn)
        or turn.status != "running"
        or type(turn.graph_context_receipt) is not SurfaceNativeContextReceiptV1
        or type(turn.graph_context_execution) is not SurfaceNativeExecutionV1
        or type(turn.graph_context_execution.policy.action)
        not in (NativeBuildActionV1, NativePlayActionV1, *NATIVE_PLAN_ACTION_TYPES)
        or turn.provenance.surface_resolution != "resolved"
        or turn.provenance.surface_id
        != turn.graph_context_execution.policy.action.surface_id
    ):
        raise ValueError("Native retrieval requires its actual running surface owner")
    validate_request_identity(
        turn.graph_context_receipt, turn.graph_context_execution, turn
    )
    return turn.graph_context_receipt, turn.graph_context_execution


def source_pins(receipt, execution=None):
    from .native_corpus import NativeCorpusAuthorityV1
    from .native_plan_statements import NativePlanQueryV1

    from .native_context import BuildPendingContextReceiptV1
    if type(receipt) is BuildPendingContextReceiptV1:
        from .build_pending_native import prepared_pending_source
        authority, query = prepared_pending_source(receipt, execution)
    else:
        authority, query = receipt.source_authority, receipt.native_query
    available = isinstance(authority, NativeCorpusAuthorityV1)
    return dict(
        source_authority_status="available" if available else "unavailable",
        source_revision=authority.revision_id if available else None,
        graph_revision=query.authority.revision_id if isinstance(query, NativePlanQueryV1) else None,
    )


def source_expansion_handle(turn):
    return 'native-corpus-expand:' + t.canonical_sha256({
        'scope': scope_digest(turn), 'query': sha256(turn.user_text.encode()).hexdigest()})


def source_expansion_selected(turn):
    handle = source_expansion_handle(turn)
    return any(type(event) in native_selection_types() and
        event.operation == 'select_candidates' and handle in event.selected_handles
        for event in turn.graph_context_execution.events)


def scope_digest(turn):
    receipt, execution = owner(turn)
    value = dict(
        world_id=turn.world_id,
        conversation_id=str(turn.conversation_id),
        turn_id=str(turn.turn_id),
        product_attempt=turn.attempt,
        context_receipt_sha256=receipt.context_receipt_sha256,
        execution_policy_sha256=execution.execution_policy_sha256,
        **source_pins(receipt, execution),
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
    parent = parse_native_retrieval_input(strict_json(proof["parent_request_json"]),
        surface_id=execution.policy.action.surface_id)
    from .jev_retrieval_contract import NativePlanBatchDecisionInputV3, NativePlayIntentDecisionInputV1
    play_opening = type(parent) is NativePlayIntentDecisionInputV1
    if bool(auth.play_intent_opening) != play_opening:
        raise ValueError("Play intent authorization differs from its exact producer")
    if play_opening and any(isinstance(event, t.ProviderAttemptAuthorizedEventV1)
                            for event in execution.events[:auth.sequence]):
        raise ValueError("Play intent ballot requires the first conversational request")
    if type(parent) is NativePlanBatchDecisionInputV3:
        from .native_corpus import initial_source_discovery_enabled
        if not initial_source_discovery_enabled(execution):
            raise ValueError("Prospective read plans require current readonly Plan work")
    if type(parent) is NativePlanBatchDecisionInputV3 and parent.bounded_continuation:
        from .native_batch_completion import selected_read_closure

        # At outcome acknowledgement the current authorization and outcome are
        # already stored. Recheck the same preceding prefix used at admission.
        before = execution.events[:auth.sequence]
        if (parent.allowed_operations != ("select_candidates", "finish_retrieval")
                or not parent.candidates
                or any(not row.handle.startswith("native-body:") for row in parent.candidates)
                or not selected_read_closure(receipt, execution, parent.bounded_continuation,
                    before_sequence=len(before))):
            raise ValueError("Bounded continuation has no directly preceding settled Plan batch")
    if type(parent) is NativePlanBatchDecisionInputV3 and parent.expanded_relevance_version:
        if not source_expansion_selected(turn):
            raise ValueError("Expanded relevance requires a recorded source expansion")
    from .jev_retrieval_contract import NativePlayRetrievalDecisionInputV1
    if isinstance(parent,NativePlayRetrievalDecisionInputV1):
        from .native_play_work import producing_authored_records
        producing_authored_records(receipt.work_context,turn.provenance,parent.play_work,turn.idempotency_key)
    role = execution.policy.provider_roles.controller
    if (
        parent.digest != auth.parent_request_sha256
        or parent.request_id != auth.decision_request_id
        or parent.question != turn.user_text
        or parent.question != execution.policy.action.intent.message
        or parent.scope_sha256 != scope_digest(turn)
        or parent.parent_attempt_id != auth.provider_attempt_id
        or any(
            getattr(parent, key) != value for key, value in source_pins(receipt, execution).items()
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
    from .native_source_keywords import RETAINED_KEYWORD_KIND, retained_keyword_candidates
    focus = tuple(c for c in parent.examined_candidates if c.kind == RETAINED_KEYWORD_KIND)
    if focus and focus != retained_keyword_candidates(turn):
        raise ValueError("Native keyword focus differs from its actual acknowledged scope")
    accounting = controller_accounting(execution)
    if accounting is None:
        if auth.build_context is not None:
            raise ValueError("Plan retrieval cannot borrow Build dispatch context")
    else:
        from .build_decision_context import validate_prepared

        from .jev_retrieval_contract import NativeBuildRetrievalDecisionInputV3
        validate_prepared(auth, execution, proof["request_json"],
            host_phase="navigate" if isinstance(parent, NativeBuildRetrievalDecisionInputV3) else None)
    validate_wire_body(
        parent, proof["request_json"].encode(), controller_accounting=accounting
    )
    return parent


def exhausts_continuation_offer(parent, selected):
    from .jev_retrieval_contract import NativePlanBatchDecisionInputV3

    if (type(parent) is not NativePlanBatchDecisionInputV3
            or parent.bounded_continuation is None
            or parent.allowed_operations != ("select_candidates", "finish_retrieval")
            or selected.operation != "select_candidates"
            or selected.post_read_plan != "review_after_reads"
            or not parent.candidates):
        return None
    handles = {candidate.handle for candidate in parent.candidates}
    if (handles == set(selected.selected_handles)
            and all(handle.startswith("native-body:") for handle in handles)):
        return True
    return None


def verify_selection(turn, event, proof, trace):
    from .source_writer_output import strict_json
    from .jev_retrieval_contract import decode_selection, validate_source_selection
    from generationengine.types import DecisionResult

    receipt, execution = owner(turn)
    if (
        type(event) not in NATIVE_RETRIEVAL_SELECTION_TYPES
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
    from .jev_retrieval_contract import NativePlanBatchDecisionInputV3
    if (type(event) is NativeRetrievalSelectedV2) != (type(parent) is NativePlanBatchDecisionInputV3):
        raise ValueError('Prospective selection requires its exact versioned producer')
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
    from .jev_retrieval_contract import NativePlayIntentDecisionInputV1
    from .native_play_opening import decode_play_opening

    if (type(event) is NativePlayIntentSelectedV1) != (type(parent) is NativePlayIntentDecisionInputV1):
        raise ValueError("Play intent requires its exact versioned producer")
    if type(event) is NativePlayIntentSelectedV1 and event.requested_work != decode_play_opening(result):
        raise ValueError("Recorded Play intent differs from the actual controller choice")
    selected = decode_selection(parent, result)
    if (type(event) is NativeRetrievalSelectedV2
            and event.exhausted_continuation_offer != exhausts_continuation_offer(parent, selected)):
        raise ValueError("Native selection differs from the accepted bounded continuation offer")
    if event.exclusion_replay is not None:
        from .jev_retrieval_contract import retrieval_exclusions_for_replay
        if event.exclusion_replay != retrieval_exclusions_for_replay(parent, result):
            raise ValueError("Replay exclusions differ from the exact native controller votes")
    pins = source_pins(receipt, execution)
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
        or type(event) is NativeRetrievalSelectedV2 and event.post_read_plan != selected.post_read_plan
    ):
        raise ValueError(
            "Native selection differs from its typed result, usage or committed scope"
        )


def current_selection(turn):
    _, execution = owner(turn)
    return _current_selection_from_execution(execution)


def _current_selection_from_execution(execution):
    """Resolve the settled selection from an already validated native execution."""
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
    from .authored_graph_references import (
        native_references, object_selections, AuthoredSourceReferenceV1, BuildAuthoredReferenceAuthorizedV2, BuildAuthoredReferenceReadV2)
    references = native_references(execution) if native_action is not None else None
    pending_author_nodes = {ref.node_id for ref in object_selections(references)}
    pending_author_sources = {index for index, ref in enumerate(() if references is None else references.references)
                              if isinstance(ref, AuthoredSourceReferenceV1)}
    retrieval_started = False
    retrieval_finished = False
    initial_search = None
    events = execution.events
    from .native_execution import BuildPendingExecutionV1, NativeBuildSourceSettledV1
    if type(execution) is BuildPendingExecutionV1:
        settlements = [e for e in events if type(e) is NativeBuildSourceSettledV1]
        if len(settlements) != 1:
            raise ValueError('Pending retrieval requires one admitted source settlement')
        events = events[settlements[0].sequence + 1:]
    for event in events:
        if isinstance(event, NativeReadBatchConcludedV1):
            # Exact read closure joins the real query at context binding;
            # this phase owner checks the actual controller intent and order.
            if (retrieval_finished or writer is not None or pending_sources
                    or pending_author_nodes or pending_author_sources
                    or type(selected) not in prospective_selection_types()
                    or selected.operation != 'select_candidates'
                    or selected.event_id != event.selection_event_id
                    or (event.exhausted_continuation is True and (
                        type(selected) is not NativeRetrievalSelectedV2
                        or selected.exhausted_continuation_offer is not True))
                    or selected.post_read_plan != (
                        'review_after_reads' if event.exhausted_continuation
                        else 'finish_if_selected_reads_succeed')):
                raise ValueError('Read batch conclusion lacks its active prospective plan')
            retrieval_finished = True
            continue
        if isinstance(event, t.NativePlanRequestSearchAuthorizedV1):
            from .native_corpus import validate_request_source_search
            validate_request_source_search(execution, event)
            if (initial_search is not None or retrieval_started or writer is not None
                    or pending_author_nodes or pending_author_sources or intent is not None):
                raise ValueError('Request discovery requires settled human references before work/provider selection')
            initial_search = event
            pending_sources.add((type(event), event.event_id))
            continue
        if isinstance(event, t.NativeInitialSourceSearchAuthorizedV1):
            from .native_corpus import validate_initial_source_search
            validate_initial_source_search(execution, event)
            if (initial_search is not None or retrieval_started or writer is not None
                    or pending_author_nodes or pending_author_sources
                    or intent is None or event.work_selection_event_id != intent.event_id):
                raise ValueError("Initial source discovery requires settled readonly work before retrieval")
            initial_search = event
            pending_sources.add((t.NativeInitialSourceSearchAuthorizedV1, event.event_id))
            continue
        if (isinstance(event, t.NativeBodySearchObservedV1) and initial_search is not None
                and event.authorization_event_id == initial_search.event_id):
            pending = (type(initial_search), initial_search.event_id)
            if pending not in pending_sources or retrieval_started or writer is not None:
                raise ValueError("Initial source discovery observation cannot repeat or follow retrieval")
            pending_sources.remove(pending)
            continue
        if isinstance(event, t.ProviderAttemptAuthorizedEventV1):
            if type(event) is NativePlanOpeningAuthorizedV1 and (pending_author_nodes or pending_author_sources):
                raise ValueError('Opening provider requires settled actual human-selected references')
            identity = (event.provider, event.model, event.api_mode)
            if auth is not None and selected is None:
                raise ValueError(
                    "Plan controller must settle its decision before another provider"
                )
            if identity == execution.policy.provider_roles.controller.identity():
                from .native_execution import NativePlanActionV3, NativePlanOpeningSelectedV2, NativePlanOpeningSelectedV3
                if (type(native_action) is NativePlanActionV3 and type(intent) in (NativePlanOpeningSelectedV2, NativePlanOpeningSelectedV3)
                        and intent.requested_work == 'clarify'):
                    raise ValueError('Question-only Plan work cannot open factual retrieval')
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
                play_opening = (type(event) is NativeRetrievalAuthorizedV1
                                and event.play_intent_opening is True)
                if play_opening and (native_action is None or native_action.surface_id != "play" or auth is not None):
                    raise ValueError("Play intent authorization requires the first Play decision")
                if ((pending_author_nodes or pending_author_sources) and not play_opening
                        and not isinstance(event, t.PlanRequestedWorkAuthorizedV1)):
                    raise ValueError('Native retrieval requires settled author-requested reads')
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
                from .native_execution import NativePlanActionV3, NativePlanOpeningSelectedV2, NativePlanOpeningSelectedV3
                question_only = (type(native_action) is NativePlanActionV3
                    and type(intent) in (NativePlanOpeningSelectedV2, NativePlanOpeningSelectedV3) and intent.requested_work == 'clarify')
                if (
                    not isinstance(event, writer_type)
                    or (pending_author_nodes or pending_author_sources) and not (
                        type(selected) is NativePlayIntentSelectedV1 and selected.defers_source_reads
                    )
                    or pending_sources
                    or retrieval_started
                    and not retrieval_finished
                    or not native_build and not retrieval_finished and not question_only
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
        elif event.kind == 'native_plan_author_scope_observed_v1':
            from .native_plan_opening import NativePlanAuthorScopeObservedV1

            if (type(event) is not NativePlanAuthorScopeObservedV1
                    or type(auth) is not NativePlanAuthorScopeAuthorizedV1
                    or intent is not None or writer is not None
                    or outcome is None or outcome.outcome != 'response_received'
                    or outcome.response_sha256 not in (None, event.controller_response_sha256)
                    or event.controller_attempt_id != auth.provider_attempt_id
                    or event.decision_request_id != auth.decision_request_id
                    or event.parent_request_sha256 != auth.parent_request_sha256
                    or event.controller_envelope_sha256 != auth.envelope_sha256
                    or event.context_receipt_sha256 != execution.context_receipt_sha256
                    or event.execution_policy_sha256 != execution.execution_policy_sha256):
                raise ValueError('Author scope observation requires its unique settled SDK response')
            auth, outcome = None, None
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
            from .native_execution import NATIVE_PLAN_OPENING_SELECTION_TYPES
            if type(event) in NATIVE_PLAN_OPENING_SELECTION_TYPES:
                if type(auth) is not NativePlanOpeningAuthorizedV1:
                    raise ValueError('Opening selection requires its actual dual-purpose provider')
                binding = getattr(event, 'author_scope_binding', None)
                if auth.author_scope_event_id != (binding.observation_event_id if binding is not None else None):
                    raise ValueError('Opening result differs from its authorized author scope')
                if event.operation is not None:
                    selected = event
                    retrieval_started = True
                    retrieval_finished = event.operation == 'finish_retrieval'
                else:
                    auth, outcome = None, None
            else:
                if type(auth) in (NativePlanOpeningAuthorizedV1, NativePlanAuthorScopeAuthorizedV1):
                    raise ValueError('Current Plan SDK cannot settle as historical work-only selection')
                auth, outcome = None, None
        elif isinstance(event, t.PlanJevRetrievalSelectionV1):
            if type(event) is NativeRetrievalSelectedV2:
                from .native_corpus import initial_source_discovery_enabled
                if not initial_source_discovery_enabled(execution):
                    raise ValueError("Prospective read plans require current readonly Plan work")
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
        elif isinstance(event, t.NativeAuthoredSourceReadV1):
            if references is None or writer is not None or (
                retrieval_finished and not (type(selected) is NativePlayIntentSelectedV1
                    and not selected.defers_source_reads)
            ):
                raise ValueError('Human source acquisition cannot resume after retrieval or writing')
            pending_author_sources.discard(event.reference_index)
        elif isinstance(event, (BuildAuthoredReferenceAuthorizedV2, BuildAuthoredReferenceReadV2)):
            if references is None or writer is not None or (
                retrieval_finished and not (type(selected) is NativePlayIntentSelectedV1
                    and not selected.defers_source_reads)
            ):
                raise ValueError('Human acquisition cannot resume after native retrieval or writing')
            if isinstance(event, BuildAuthoredReferenceAuthorizedV2):
                pending_sources.add((BuildAuthoredReferenceAuthorizedV2, event.event_id))
            else:
                pending_sources.discard((BuildAuthoredReferenceAuthorizedV2, event.authorization_event_id))
                pending_author_nodes.discard(event.node_id)
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
                    t.NativeDirectSourceAuthorizedV1,
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
                writer is not None or retrieval_finished
                or selected is None
                or selected.operation == "finish_retrieval"
            ):
                raise ValueError(
                    "Plan acquisition requires an active completed retrieval decision"
                )
            if native_action is not None:
                native_pairs = (
                    (t.NativeDirectSourceAuthorizedV1, t.NativeDirectSourceObservedV1),
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
