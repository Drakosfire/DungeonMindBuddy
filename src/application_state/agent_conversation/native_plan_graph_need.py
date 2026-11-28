"""Plan Graph-need decision codec. This reader does not dispatch a provider."""
from __future__ import annotations

import json
import math
from hashlib import sha256
from typing import Annotated, Literal
from uuid import UUID

from pydantic import Field
from generationengine.types import ChoiceDecisionQuestion, DecisionRequest

from .jev_retrieval_contract import MODEL, PROVIDER, RetrievalDialogue, validated_choice_answers
from .native_statement_input import Strict
from .rules_authority_types import canonical_sha256
from .plan_authoring import strict_json

Digest = Annotated[str, Field(pattern=r'^[a-f0-9]{64}$', strict=True)]
OPTIONS = ('require_graph', 'no_graph', 'uncertain')
QUESTION = 'Does the current request require World Graph facts beyond the supplied conversation and current work?'
DESCRIPTIONS = {
    'require_graph': 'Graph facts are needed to satisfy the request',
    'no_graph': 'The supplied conversation and current work are sufficient without World Graph facts',
    'uncertain': 'It is unclear whether World Graph facts are needed',
}
EXCLUSION_DESCRIPTIONS_V1 = {
    'require_graph': 'World Graph facts are needed to satisfy the request and the author permits consulting them.',
    'no_graph': 'The request can be answered from supplied context, or the author explicitly excludes searching or consulting World sources; respect that exclusion even when information is missing.',
    'uncertain': 'The intended context or permission to use World Graph facts is genuinely unclear.',
}


class NativePlanGraphNeedInputV1(Strict):
    """Retained semantic inputs plus host-only pins for one exact Plan opening."""
    schema_: Literal['dmb_plan_graph_need_input_v1'] = Field(default='dmb_plan_graph_need_input_v1', alias='schema')
    pending_query_sha256: Digest
    admission_sha256: Digest
    question: str = Field(min_length=1, strict=True)
    dialogue: tuple[RetrievalDialogue, ...]
    current_work: str = Field(strict=True)
    exclusion_guidance_version: Literal['v1'] | None = Field(
        default=None, exclude_if=lambda value: value is None)

    @property
    def digest(self):
        return canonical_sha256(self.model_dump(mode='json', by_alias=True))


def validate_input_binding(parent, *, pending_sha256, admission_sha256, question, dialogue_sha256, work_sha256):
    """Join the frozen model inputs to their already-admitted host commitments."""
    from .native_plan_opening import opening_dialogue_sha256
    if (type(parent) is not NativePlanGraphNeedInputV1
            or parent.pending_query_sha256 != pending_sha256
            or parent.admission_sha256 != admission_sha256
            or parent.question != question
            or opening_dialogue_sha256(parent.dialogue) != dialogue_sha256
            or sha256(parent.current_work.encode('utf-8')).hexdigest() != work_sha256):
        raise ValueError('Plan Graph-need input differs from its committed request, dialogue or work')


def prepare_decision(parent):
    if type(parent) is not NativePlanGraphNeedInputV1:
        raise ValueError('Plan Graph-need decision requires its exact versioned input')
    if parent.exclusion_guidance_version not in (None, 'v1'):
        raise ValueError('Unsupported Plan Graph-need guidance version')
    return DecisionRequest(provider=PROVIDER, model=MODEL, state={
        'user_request': parent.question,
        'dialogue_reference': [row.model_dump() for row in parent.dialogue],
        'current_work': parent.current_work,
    }, questions=(ChoiceDecisionQuestion(name='graph_need', question=QUESTION,
        options=OPTIONS, option_descriptions=(EXCLUSION_DESCRIPTIONS_V1
            if parent.exclusion_guidance_version == 'v1' else DESCRIPTIONS)),), max_transport_retries=0)


def canonical_wire(parent, *, expected_model=MODEL):
    decision = prepare_decision(parent)
    body = {'state': decision.state, 'model': expected_model, 'questions': {
        q.name: {'type': 'choice', 'instructions': q.question,
                 'criteria': {option: (q.option_descriptions or {}).get(option) for option in q.options}}
        for q in decision.questions}}
    return json.dumps(body, ensure_ascii=False, separators=(',', ':'), allow_nan=False).encode('utf-8')


def validate_wire(parent, raw, *, expected_model=MODEL):
    """Validate exact Jev bytes; APP separately validates dispatch identity."""
    if type(raw) is not bytes or raw != canonical_wire(parent, expected_model=expected_model):
        raise ValueError('Plan Graph-need wire differs from its admitted semantic input')
    strict_json(raw.decode('utf-8'))


def decode_decision(parent, result, *, expected_model=MODEL):
    prepare_decision(parent)
    choice = validated_choice_answers(result, {'graph_need'}, expected_model=expected_model)['graph_need']
    if choice not in OPTIONS:
        raise ValueError('Plan Graph-need decision selected an unknown option')
    distribution = result.answers['graph_need'].probabilities
    if distribution is not None:
        if (choice not in distribution or not set(distribution) <= set(OPTIONS)
                or any(not math.isfinite(value) or not 0 <= value <= 1 for value in distribution.values())):
            raise ValueError('Plan Graph-need probabilities are invalid')
        maximum = max(distribution.values())
        if distribution[choice] != maximum or sum(value == maximum for value in distribution.values()) != 1:
            raise ValueError('Plan Graph-need probability selection is tied or inconsistent')
    return choice


def decode_retained_result(parent, result_json, result_sha256, *, expected_model=MODEL):
    """Recheck a retained SDK result; its original authenticity needs the append owner."""
    from generationengine.types import DecisionResult
    if type(result_json) is not str or sha256(result_json.encode('utf-8')).hexdigest() != result_sha256:
        raise ValueError('Plan Graph-need result differs from its retained digest')
    strict_json(result_json)  # Refuse duplicate keys before Pydantic reconstruction.
    result = DecisionResult.model_validate_json(result_json)
    if result.model_dump_json() != result_json:
        raise ValueError('Plan Graph-need result differs from the exact SDK serialization')
    return decode_decision(parent, result, expected_model=expected_model)


class NativePlanGraphNeedObservedV1(Strict):
    kind: Literal['native_plan_graph_need_observed_v1'] = 'native_plan_graph_need_observed_v1'
    event_id: UUID
    sequence: int = Field(ge=0, strict=True)
    controller_attempt_id: UUID
    decision_request_id: UUID
    context_receipt_sha256: Digest
    execution_policy_sha256: Digest
    parent: NativePlanGraphNeedInputV1
    envelope_sha256: Digest
    result_json: str = Field(min_length=1)
    result_sha256: Digest
    choice: Literal['require_graph', 'no_graph', 'uncertain']


GRAPH_NEED_CLARIFICATION_QUESTION = 'What context would you like me to use for this request?'


class NativePlanGraphClarificationSegmentV1(Strict):
    kind: Literal['clarification'] = 'clarification'
    text: Literal['What context would you like me to use for this request?'] = GRAPH_NEED_CLARIFICATION_QUESTION


class NativePlanGraphClarificationCompletionV1(Strict):
    """Host-authored scope question; it is not a writer or factual answer."""
    schema_: Literal['dmb_plan_graph_need_clarification_v1'] = Field(default='dmb_plan_graph_need_clarification_v1', alias='schema')
    surface_id: Literal['plan'] = 'plan'
    context_receipt_sha256: Digest
    observation_event_id: UUID
    answer_context_status: Literal['discussion'] = 'discussion'
    answer_segments: tuple[NativePlanGraphClarificationSegmentV1] = (NativePlanGraphClarificationSegmentV1(),)


class NativePlanGraphClarificationEventV1(Strict):
    kind: Literal['native_plan_graph_clarification_v1'] = 'native_plan_graph_clarification_v1'
    event_id: UUID
    sequence: int = Field(ge=0, strict=True)
    observation_event_id: UUID
    completion_sha256: Digest


class NativePlanGraphQueryAuthorizedV1(Strict):
    kind: Literal['native_plan_graph_query_authorized_v1'] = 'native_plan_graph_query_authorized_v1'
    event_id: UUID
    sequence: int = Field(ge=0, strict=True)
    need_event_id: UUID
    pending_query_sha256: Digest


class NativePlanGraphQueryStartedV1(Strict):
    kind: Literal['native_plan_graph_query_started_v1'] = 'native_plan_graph_query_started_v1'
    event_id: UUID
    sequence: int = Field(ge=0, strict=True)
    authorization_event_id: UUID


from .native_corpus import NativeCorpusAuthorityV1
from .types import NativeCorpusUnavailableV1


class NativePlanGraphQueryClosedV1(Strict):
    kind: Literal['native_plan_graph_query_closed_without_graph_v1'] = 'native_plan_graph_query_closed_without_graph_v1'
    event_id: UUID
    sequence: int = Field(ge=0, strict=True)
    need_event_id: UUID
    pending_query_sha256: Digest
    source_authority: NativeCorpusAuthorityV1 | NativeCorpusUnavailableV1 | None = Field(
        default=None, exclude_if=lambda value: value is None)


class NativePlanGraphQueryFailedV1(Strict):
    kind: Literal['native_plan_graph_query_failed_v1'] = 'native_plan_graph_query_failed_v1'
    event_id: UUID
    sequence: int = Field(ge=0, strict=True)
    started_event_id: UUID
    reason: Literal['uncertain_owner_result', 'authority_unavailable']


from .native_plan_assertions import NativePlanQueryV2, NativeGraphQueryV3, NativeGraphQueryV4
from .native_plan_statements import NativePlanQueryUnavailableV1


class NativePlanGraphQuerySettledV1(Strict):
    kind: Literal['native_plan_graph_query_settled_v1'] = 'native_plan_graph_query_settled_v1'
    event_id: UUID
    sequence: int = Field(ge=0, strict=True)
    started_event_id: UUID
    query: NativeGraphQueryV4 | NativeGraphQueryV3 | NativePlanQueryV2 | NativePlanQueryUnavailableV1
    source_authority: NativeCorpusAuthorityV1 | NativeCorpusUnavailableV1 | None = Field(
        default=None, exclude_if=lambda value: value is None)


_GRAPH_EVENTS = (NativePlanGraphNeedObservedV1, NativePlanGraphClarificationEventV1, NativePlanGraphQueryAuthorizedV1,
    NativePlanGraphQueryStartedV1, NativePlanGraphQueryClosedV1,
    NativePlanGraphQueryFailedV1, NativePlanGraphQuerySettledV1)


def validate_graph_need_intent_prefix(execution, events, *, require_source_use=True, allow_clarify=False):
    """Validate the optional acknowledged intent preceding Graph need."""
    from . import types as t
    from .native_retrieval import NativePlanAuthorScopeAuthorizedV1

    attempts = [event for event in events if isinstance(event, t.ProviderAttemptAuthorizedEventV1)]
    if attempts:
        from .native_plan_opening import NativePlanAuthorScopeObservedV1

        intent = attempts[0]
        if len(attempts) != 1 or type(intent) is not NativePlanAuthorScopeAuthorizedV1 or not intent.intent_opening:
            raise ValueError('Graph-need dispatch must be the first provider attempt or follow one settled Plan intent')
        observations = [event for event in events if type(event) is NativePlanAuthorScopeObservedV1]
        outcomes = [event for event in events if type(event) is t.ProviderOutcomeEventV1
                    and event.provider_attempt_id == intent.provider_attempt_id]
        if (len(observations) != 1 or len(outcomes) != 2
                or [event.outcome for event in outcomes] != ['sdk_entered', 'response_received']):
            raise ValueError('Graph-need dispatch requires a settled Plan intent')
        observed = observations[0]
        if (not intent.sequence < outcomes[0].sequence < outcomes[1].sequence < observed.sequence
                or observed.controller_attempt_id != intent.provider_attempt_id
                or observed.decision_request_id != intent.decision_request_id
                or observed.controller_envelope_sha256 != intent.envelope_sha256
                or observed.parent_request_sha256 != intent.parent_request_sha256
                or observed.context_receipt_sha256 != execution.context_receipt_sha256
                or observed.execution_policy_sha256 != execution.execution_policy_sha256
                or observed.scope_observation.requested_work in (None, 'different_destination')
                or (not allow_clarify and observed.scope_observation.requested_work == 'clarify')):
            raise ValueError('Graph-need dispatch requires the exact eligible Plan intent')
        if require_source_use and observed.scope_observation.source_use in ("conversation_only", "uncertain"):
            raise ValueError("Plan intent did not authorize Graph-need dispatch")
        return observed



def validate_pending_graph(context, execution):
    """Validate the complete retained Plan query prefix and return its effective query.

    Authenticity of the decoded SDK result is supplied by its trusted APP append
    owner; this reader validates the retained proof and never dispatches work.
    """
    from . import types as t
    from .native_context import NativePlanGraphQueryPendingV1, NativePlanRequestAdmissionV1
    from .native_execution import NativePlanActionV2, NativePlanActionV3, NATIVE_WRITER_TYPES
    from .native_retrieval import NativePlanGraphNeedAuthorizedV1
    from .authored_graph_references import (native_references, object_selections,
        BuildAuthoredReferenceAuthorizedV2, BuildAuthoredReferenceReadV2, BuildAuthoredReferenceReadV3)

    query = context.native_query
    events = execution.events
    graph_events = [e for e in events if isinstance(e, _GRAPH_EVENTS)]
    need_auths = [e for e in events if type(e) is NativePlanGraphNeedAuthorizedV1]
    if type(query) is not NativePlanGraphQueryPendingV1:
        if graph_events or need_auths:
            raise ValueError('Plan Graph-need events require a pending Plan query')
        return query
    action, admission = execution.policy.action, context.assembled_input
    if (type(action) not in (NativePlanActionV2, NativePlanActionV3)
            or type(admission) is not NativePlanRequestAdmissionV1
            or query.question != action.intent.message
            or (query.authority is not None
                and action.intent.graph_request.revision_pin not in (None, query.authority.revision_id))):
        raise ValueError('Pending Plan Graph query differs from its admitted request')
    pending_sha = canonical_sha256(query)
    observations = [e for e in graph_events if type(e) is NativePlanGraphNeedObservedV1]
    clarifications = [e for e in graph_events if type(e) is NativePlanGraphClarificationEventV1]
    authorizations = [e for e in graph_events if type(e) is NativePlanGraphQueryAuthorizedV1]
    starts = [e for e in graph_events if type(e) is NativePlanGraphQueryStartedV1]
    closures = [e for e in graph_events if type(e) is NativePlanGraphQueryClosedV1]
    failures = [e for e in graph_events if type(e) is NativePlanGraphQueryFailedV1]
    settlements = [e for e in graph_events if type(e) is NativePlanGraphQuerySettledV1]
    if any(len(items) > 1 for items in (need_auths, observations, clarifications, authorizations, starts, closures, failures, settlements)):
        raise ValueError('Plan Graph-need and query transitions must be unique')
    need_auth = need_auths[0] if need_auths else None
    observed = observations[0] if observations else None
    clarification = clarifications[0] if clarifications else None
    grant = authorizations[0] if authorizations else None
    started = starts[0] if starts else None
    closed = closures[0] if closures else None
    failed = failures[0] if failures else None
    settled = settlements[0] if settlements else None
    authorized_parent = None
    if need_auth:
        validate_graph_need_intent_prefix(execution, events[:need_auth.sequence])
        strict_json(need_auth.parent_json)
        authorized_parent = NativePlanGraphNeedInputV1.model_validate_json(need_auth.parent_json)
        if authorized_parent.model_dump_json(by_alias=True) != need_auth.parent_json:
            raise ValueError('Graph-need authorization requires its exact retained parent')
        validate_input_binding(authorized_parent, pending_sha256=pending_sha,
            admission_sha256=canonical_sha256(admission), question=action.intent.message,
            dialogue_sha256=admission.dialogue_sha256, work_sha256=context.work_context.plan_basis.content_sha256)
        if ((need_auth.provider, need_auth.model, need_auth.api_mode) != execution.policy.provider_roles.controller.identity()
                or need_auth.parent_request_sha256 != authorized_parent.digest
                or need_auth.envelope_sha256 != sha256(canonical_wire(authorized_parent, expected_model=need_auth.model)).hexdigest()):
            raise ValueError('Graph-need authorization differs from its exact prepared parent')
    if observed:
        lifecycle = [e for e in events if isinstance(e, t.ProviderOutcomeEventV1)
                     and need_auth is not None and e.provider_attempt_id == need_auth.provider_attempt_id
                     and need_auth.sequence < e.sequence < observed.sequence]
        if (need_auth is None or observed.sequence <= need_auth.sequence
                or (need_auth.provider, need_auth.model, need_auth.api_mode) != execution.policy.provider_roles.controller.identity()
                or observed.controller_attempt_id != need_auth.provider_attempt_id
                or observed.decision_request_id != need_auth.decision_request_id
                or observed.context_receipt_sha256 != execution.context_receipt_sha256
                or observed.execution_policy_sha256 != execution.execution_policy_sha256
                or [e.outcome for e in lifecycle] != ['sdk_entered', 'response_received']
                or lifecycle[-1].response_sha256 not in (None, observed.result_sha256)):
            raise ValueError('Graph-need observation requires its exact acknowledged SDK lifecycle')
        validate_input_binding(observed.parent, pending_sha256=pending_sha,
            admission_sha256=canonical_sha256(admission), question=action.intent.message,
            dialogue_sha256=admission.dialogue_sha256, work_sha256=context.work_context.plan_basis.content_sha256)
        if (observed.parent != authorized_parent
                or observed.parent.digest != need_auth.parent_request_sha256
                or sha256(canonical_wire(observed.parent, expected_model=need_auth.model)).hexdigest() != need_auth.envelope_sha256
                or observed.envelope_sha256 != need_auth.envelope_sha256
                or decode_retained_result(observed.parent, observed.result_json, observed.result_sha256,
                    expected_model=need_auth.model) != observed.choice):
            raise ValueError('Graph-need observation differs from its authorized SDK result')
    if clarification:
        terminal_events = events
        from .native_retrieval import NativePlanAuthorScopeAuthorizedV1
        if need_auth is not None and events and type(events[0]) is NativePlanAuthorScopeAuthorizedV1:
            prefix = events[:need_auth.sequence]
            if len(prefix) != 4:
                raise ValueError('Plan Graph clarification requires one settled intent before Graph need')
            validate_graph_need_intent_prefix(execution, prefix)
            terminal_events = events[need_auth.sequence:]
        if (observed is None or observed.choice != 'uncertain'
                or clarification.observation_event_id != observed.event_id
                or clarification.sequence != observed.sequence + 1
                or len(events) != clarification.sequence + 1
                or any(type(event) not in (NativePlanGraphNeedAuthorizedV1, t.ProviderOutcomeEventV1,
                    NativePlanGraphNeedObservedV1, NativePlanGraphClarificationEventV1) for event in terminal_events)
                or grant is not None or started is not None or closed is not None or failed is not None or settled is not None):
            raise ValueError('Plan Graph clarification requires its unique uncertain decision without acquisitions')
    if grant and (observed is None or observed.choice != 'require_graph'
            or grant.need_event_id != observed.event_id or grant.pending_query_sha256 != pending_sha
            or grant.sequence <= observed.sequence):
        raise ValueError('Plan Graph query requires its acknowledged Graph-need decision')
    if started and (grant is None or started.authorization_event_id != grant.event_id
            or started.sequence <= grant.sequence):
        raise ValueError('Plan Graph query start requires its exact authorization')
    if settled:
        if (started is None or settled.started_event_id != started.event_id
                or settled.sequence <= started.sequence or failed is not None or closed is not None):
            raise ValueError('Plan Graph query settlement requires one open started query')
        resolved = settled.query
        if query.authority is None:
            source = settled.source_authority
            if (source is None or source.managed_world_id != context.source_authority.managed_world_id
                    or (isinstance(source, NativeCorpusAuthorityV1)
                        and action.intent.graph_request.revision_pin not in (None, source.revision_id))):
                raise ValueError("Plan settlement requires matching acquired source authority")
            if type(resolved) is NativePlanQueryUnavailableV1:
                if resolved.managed_world_id != source.managed_world_id:
                    raise ValueError("Unavailable Plan Graph query belongs to another World")
            elif (not isinstance(source, NativeCorpusAuthorityV1)
                    or resolved.question != query.question
                    or resolved.authority.scope_mode != "world"
                    or resolved.authority.campaign_id is not None
                    or resolved.authority.session_id is not None
                    or any(getattr(resolved.authority, key) != getattr(source, key) for key in (
                        "managed_world_id", "native_world_id", "binding_version", "revision_id",
                        "domain_ref", "profile_ref", "acquisition_epoch"))):
                raise ValueError("Plan Graph settlement differs from the acquired source or request")
        elif settled.source_authority is not None:
            raise ValueError("Pinned Plan Graph query cannot replace its source authority")
        elif type(resolved) is NativePlanQueryUnavailableV1:
            if resolved.managed_world_id != query.authority.managed_world_id:
                raise ValueError('Unavailable Plan Graph query belongs to another World')
        elif resolved.authority != query.authority or resolved.question != query.question:
            raise ValueError('Settled Plan Graph query differs from its pinned authority or question')
    if failed and (started is None or failed.started_event_id != started.event_id
            or failed.sequence <= started.sequence or settled is not None or closed is not None):
        raise ValueError('Plan Graph failure requires one open started query')
    if failed and any(event.sequence > failed.sequence for event in events):
        raise ValueError('Plan Graph terminal failure cannot accept late events')
    if closed and (observed is None or observed.choice != 'no_graph'
            or closed.need_event_id != observed.event_id or closed.pending_query_sha256 != pending_sha
            or closed.sequence <= observed.sequence or grant is not None or started is not None
            or settled is not None or failed is not None or object_selections(native_references(execution))):
        raise ValueError('No-Graph closure requires its exact decision and no authored Graph references')
    if closed is not None and closed.source_authority is not None:
        source = closed.source_authority
        from .native_plan_opening import NativePlanAuthorScopeObservedV1

        if (query.authority is not None
                or source.managed_world_id != context.source_authority.managed_world_id
                or (isinstance(source, NativeCorpusAuthorityV1)
                    and action.intent.graph_request.revision_pin not in (None, source.revision_id))
                or not any(type(event) is NativePlanAuthorScopeObservedV1
                           and event.scope_observation.source_use == 'source_needed'
                           for event in events[:need_auth.sequence])):
            raise ValueError("No-Graph source acquisition requires exact source-seeking Plan intent")
    source_free_intent = None
    if query.authority is None and not need_auths and not graph_events and len(events) >= 4:
        from .native_plan_opening import NativePlanAuthorScopeObservedV1

        candidate = events[3]
        if (type(candidate) is NativePlanAuthorScopeObservedV1
                and (candidate.scope_observation.requested_work == 'clarify'
                     or candidate.scope_observation.source_use in {'conversation_only', 'uncertain'})
                and not object_selections(native_references(execution))):
            source_free_intent = validate_graph_need_intent_prefix(
                execution, events[:4], require_source_use=False, allow_clarify=True)

    graph_reads = (t.NativePlanStatementReadAuthorizedV1, t.NativePlanStatementReadObservedV1,
                   t.NativePlanAssertionReadAuthorizedV1, t.NativePlanAssertionReadObservedV1,
                   BuildAuthoredReferenceAuthorizedV2, BuildAuthoredReferenceReadV2, BuildAuthoredReferenceReadV3)
    for event in events:
        if isinstance(event, graph_reads) and (settled is None or event.sequence <= settled.sequence):
            raise ValueError('Plan Graph reads require prior exact query settlement')
        if isinstance(event, NATIVE_WRITER_TYPES) and not (
                settled is not None and event.sequence > settled.sequence
                or closed is not None and event.sequence > closed.sequence
                or source_free_intent is not None and event.sequence > source_free_intent.sequence):
            raise ValueError('Plan writer requires a settled query or explicit no-Graph closure')
    if settled is not None:
        return settled.query
    return None if closed is not None or clarification is not None or source_free_intent is not None else query


def effective_plan_source_authority(receipt, events):
    """Project source authority from an already validated execution prefix."""
    from .native_context import NativePlanSourcePendingV1

    authority = receipt.source_authority
    if type(authority) is not NativePlanSourcePendingV1:
        return authority
    settled = next((event for event in events
                    if type(event) in (NativePlanGraphQueryClosedV1, NativePlanGraphQuerySettledV1)), None)
    return settled.source_authority if settled is not None else None
