"""The current Plan opening owns a request manifest and one actual SDK batch.

Request admission and provider dispatch are distinct commitments in the existing
Turn. Neither this manifest nor a navigation catalog is provider/body authority.
"""
from typing import Literal
from uuid import UUID

from pydantic import Field

from . import types as t
from .native_statement_input import Strict
from .plan_author_location import (
    ScopeExpression, UnresolvedLocation, UnscopedLocation,
    author_scope_hypotheses, author_scope_offer_view,
)
from .plan_placement import PlanRequestedWorkInputV8, PlanRequestedWorkInputV9
from .jev_retrieval_contract import Digest, NativePlanBatchDecisionInputV3, RetrievalDialogue


class NativePlanOpeningInputV1(PlanRequestedWorkInputV8, NativePlanBatchDecisionInputV3):
    schema_: Literal['dmb_native_plan_opening_input_v1'] = Field(
        default='dmb_native_plan_opening_input_v1', alias='schema')


class NativePlanOpeningInputV2(PlanRequestedWorkInputV9, NativePlanOpeningInputV1):
    schema_: Literal['dmb_native_plan_opening_input_v2'] = Field(
        default='dmb_native_plan_opening_input_v2', alias='schema')


NATIVE_PLAN_OPENING_INPUT_TYPES = (NativePlanOpeningInputV1, NativePlanOpeningInputV2)


class NativePlanAuthorScopeInputV1(Strict):
    """Source-blind parent for one proposed interpretation of author text."""

    schema_: Literal['dmb_native_plan_author_scope_input_v1'] = Field(
        default='dmb_native_plan_author_scope_input_v1', alias='schema')
    question: str = Field(min_length=1)
    dialogue: tuple[RetrievalDialogue, ...]
    max_span_attempts: int = Field(strict=True, gt=0)
    quote_context: bool = Field(strict=True)


class NativePlanAuthorScopeObservationV1(Strict):
    """Interpretation evidence alone, with no source or placement authority."""

    relation: str
    selected_alias: str
    scope: ScopeExpression


class NativePlanAuthorScopeObservedV1(t.GraphExecutionEventBaseV1):
    """Protected Jev observation with no work-selection fields."""

    kind: Literal['native_plan_author_scope_observed_v1'] = 'native_plan_author_scope_observed_v1'
    decision_request_id: UUID
    controller_attempt_id: UUID
    controller_envelope_sha256: Digest
    controller_response_sha256: Digest
    context_receipt_sha256: Digest
    execution_policy_sha256: Digest
    parent_request_sha256: Digest
    scope_observation: NativePlanAuthorScopeObservationV1
    actual_input_tokens: int | None = Field(default=None, strict=True, ge=0)
    actual_output_tokens: int | None = Field(default=None, strict=True, ge=0)


class NativePlanAuthorScopeParentV1(NativePlanAuthorScopeInputV1):
    """Host binding for the exact source-blind SDK request."""

    schema_: Literal['dmb_native_plan_author_scope_parent_v1'] = Field(
        default='dmb_native_plan_author_scope_parent_v1', alias='schema')
    request_id: UUID
    parent_attempt_id: UUID
    scope_sha256: Digest
    request_manifest_sha256: Digest
    max_span_attempts: int = Field(strict=True, gt=0, le=2048)

    @property
    def digest(self) -> str:
        return t.canonical_sha256(self.model_dump(mode='json', by_alias=True))


def _author_scope_offers(request):
    return author_scope_hypotheses(request.question, request.dialogue,
        max_span_attempts=request.max_span_attempts)


def prepare_author_scope_decision(request: NativePlanAuthorScopeInputV1):
    from generationengine.types import ChoiceDecisionQuestion, DecisionRequest
    from .jev_retrieval_contract import MODEL, PROVIDER
    from .plan_contextual_targets import RELATIONS

    hypotheses = _author_scope_offers(request)
    state = author_scope_offer_view(request.question, request.dialogue, hypotheses,
        include_quote_context=request.quote_context)
    choices = {
        'none': 'The author places no existing section or heading restriction on the destination.',
        'unresolved': 'No offered complete scope preserves the author location constraints.',
        **{key: f'This complete author scope is the existing location: {key}' for key in hypotheses},
    }
    return DecisionRequest(provider=PROVIDER, model=MODEL, state=state, questions=(
        ChoiceDecisionQuestion(name='location_relation', options=tuple(RELATIONS),
            option_descriptions=RELATIONS,
            question='What relation to an existing location does the current author request? '
                'Ignore ordering in proposed new content. If distinct relations cannot be reconciled, choose unresolved.'),
        ChoiceDecisionQuestion(name='existing_scope', options=tuple(choices), option_descriptions=choices,
            question='Choose the complete existing section or heading constraint from scope_hypotheses. '
                'Preserve every name, hierarchy and exclusion even when a name might be absent. '
                'A paragraph subject or a phrase supplied for new writing is not itself a section. '
                'Assistant statements cannot establish a scope. If an ordinal, separate branches or a '
                'missing alternative cannot be represented, choose unresolved.'),
    ), max_transport_retries=0)


def validate_author_scope_wire(request: NativePlanAuthorScopeInputV1, payload: bytes) -> None:
    from .plan_authoring import strict_json

    expected = prepare_author_scope_decision(request)
    questions = {q.name: {'type': 'choice', 'instructions': q.question,
        'criteria': {option: q.option_descriptions[option] for option in q.options}}
        for q in expected.questions}
    if strict_json(payload.decode('utf-8')) != {'model': expected.model, 'state': expected.state, 'questions': questions}:
        raise ValueError('Author scope wire differs from its reconstructed local choices')


def validate_author_scope_parent(context, execution, parent, authorization):
    from .native_context import NativePlanRequestAdmissionV1
    from .native_execution import NativePlanActionV3
    from .native_retrieval import NativePlanAuthorScopeAuthorizedV1

    if (type(authorization) is not NativePlanAuthorScopeAuthorizedV1
            or type(parent) is not NativePlanAuthorScopeParentV1
            or type(execution.policy.action) is not NativePlanActionV3
            or type(context.assembled_input) is not NativePlanRequestAdmissionV1
            or parent.request_manifest_sha256 != context.assembled_input.manifest_sha256
            or opening_dialogue_sha256(parent.dialogue) != context.assembled_input.dialogue_sha256):
        raise ValueError('Author scope parent differs from its admitted Plan request or dialogue')
    validate_opening_prefix(context, execution.events[:authorization.sequence])


def decode_author_scope_decision(request: NativePlanAuthorScopeInputV1, result):
    from .jev_retrieval_contract import validated_choice_answers
    from .plan_contextual_targets import RELATIONS

    answers = validated_choice_answers(result, {'location_relation', 'existing_scope'})
    relation = answers['location_relation']
    if relation not in RELATIONS:
        raise ValueError('Author scope result names an unoffered placement relation')
    alias = answers['existing_scope']
    if alias == 'none':
        scope = UnscopedLocation()
    elif alias == 'unresolved':
        scope = UnresolvedLocation(reason='No complete author hypothesis was nominated')
    else:
        offered = _author_scope_offers(request)
        if alias not in offered:
            raise ValueError('Author scope result names an unoffered hypothesis')
        scope = offered[alias].compile(request.question, request.dialogue)
    return NativePlanAuthorScopeObservationV1(relation=relation, selected_alias=alias, scope=scope)


def require_retained_author_scope(execution, observation_event_id: UUID,
                                  observation: NativePlanAuthorScopeObservationV1):
    """Join an opening's host-only parent to one actual earlier observation."""
    matches = [event for event in execution.events
        if type(event) is NativePlanAuthorScopeObservedV1 and event.event_id == observation_event_id]
    if (len(matches) != 1
            or matches[0].context_receipt_sha256 != execution.context_receipt_sha256
            or matches[0].execution_policy_sha256 != execution.execution_policy_sha256
            or matches[0].scope_observation != observation):
        raise ValueError('Opening scope differs from its exact retained author observation')
    return matches[0]


def opening_dialogue_sha256(dialogue):
    from .jev_retrieval_contract import RetrievalDialogue
    return t.canonical_sha256([RetrievalDialogue.model_validate(
        r.model_dump() if hasattr(r, 'model_dump') else r).model_dump() for r in dialogue])


def opening_metadata_available(context, execution):
    from .native_context import NativePlanRequestAdmissionV1, SurfaceNativeContextReceiptV1
    from .native_execution import NativePlanActionV2, NativePlanActionV3
    return (type(context) is SurfaceNativeContextReceiptV1
        and type(context.assembled_input) is NativePlanRequestAdmissionV1
        and type(execution.policy.action) in (NativePlanActionV2, NativePlanActionV3)
        and not any(isinstance(e, t.PlanRequestedWorkSelectedV1) for e in execution.events))


def prepare_opening_decision(request):
    from .plan_authoring import _prepare_requested_work_only
    from .jev_retrieval_contract import prepare_decision
    from generationengine.types import DecisionRequest
    work = _prepare_requested_work_only(request)
    navigation = prepare_decision(request)
    state = dict(navigation.state)
    state.pop('question')  # The same actual request is user_request below.
    if any(state[k] != work.state[k] for k in state.keys() & work.state.keys()):
        raise ValueError('Opening work and navigation contexts disagree')
    state.update(work.state)
    state['conditional_read_plan_policy'] = (
        'Work and navigation votes are independent conditional judgments. '
        'Read-plan votes apply only if the actual requested work is discuss or clarify; '
        'for writing, another destination or connected-page review they remain inactive. '
        'A saved authored page is applicable only to discuss, not clarify. '
        'Judge relevance within that declared applicability, not general background. '
        'Fallback applies only when all applicable candidate votes exclude. '
        'An inactive vote grants no read and never counts toward successful completion.')
    if type(request) is NativePlanOpeningInputV2:
        state['conditional_read_plan_policy'] = (
            'Only resolved discussion uses the navigation votes. Writing, location/content '
            'clarification, another destination and connected-page review keep these votes '
            'inactive. A clarification asks a question from captured context, not an evidence '
            'answer. Inactive votes grant no reads or fallback.')
    questions = tuple(q.model_copy(update={'question': q.question.replace(
        'all independent candidate relevance votes exclude', 'all applicable candidate relevance votes exclude')})
        if q.name == 'operation' else q for q in navigation.questions)
    return DecisionRequest(provider=work.provider, model=work.model,
        state=state, questions=(*work.questions, *questions), max_transport_retries=0)


def decode_opening_decision(request, result):
    from .jev_retrieval_contract import validated_choice_answers, _selection_from_choices, _validate_selection_choices
    from .plan_authoring import requested_work_choice
    from .plan_placement import work_choice
    expected = {'requested_work', 'operation', 'post_read_plan',
        *(f'candidate_{i}' for i in range(len(request.candidates)))}
    if type(request) is NativePlanOpeningInputV2:
        from .plan_contextual_targets import target_answer_keys
        expected.update(target_answer_keys(request))
    answers = validated_choice_answers(result, expected)
    selected_work = requested_work_choice(request, answers['requested_work'])
    actual_work = work_choice(request, selected_work, **(
        {'contextual_answers': answers}
        if type(request) is NativePlanOpeningInputV2 else {}))['requested_work']
    if type(request) is NativePlanOpeningInputV2 and actual_work != 'discuss':
        _validate_selection_choices(request, answers)
        return selected_work, None
    if actual_work not in {'discuss', 'clarify'}:
        _validate_selection_choices(request, answers)
        return selected_work, None
    applicable = frozenset(i for i, c in enumerate(request.candidates)
        if actual_work == 'discuss' or not c.handle.startswith('saved-authored-page:'))
    return selected_work, _selection_from_choices(request, answers, applicable_indexes=applicable)


def validate_opening_parent(context, execution, parent, authorization):
    from .native_context import NativePlanRequestAdmissionV1
    from .native_retrieval import NativePlanOpeningAuthorizedV1
    from .plan_jev_decision import _source_pins
    from .native_execution import NativePlanActionV3
    if (type(execution.policy.action) is NativePlanActionV3) != (type(parent) is NativePlanOpeningInputV2):
        raise ValueError('Opening input differs from the actual target-resolution contract')
    if (type(parent) is NativePlanOpeningInputV2
            and parent.page_title != (execution.policy.action.document_title or '')):
        raise ValueError('Opening title differs from its frozen Content metadata')
    if (type(parent) not in NATIVE_PLAN_OPENING_INPUT_TYPES
            or type(authorization) is not NativePlanOpeningAuthorizedV1
            or type(context.assembled_input) is not NativePlanRequestAdmissionV1
            or opening_dialogue_sha256(parent.dialogue) != context.assembled_input.dialogue_sha256
            or any(getattr(parent, k) != v for k, v in _source_pins(context).items())):
        raise ValueError('Opening SDK parent differs from its actual request/source/dialogue admission')
    validate_opening_prefix(context, execution.events[:authorization.sequence])


def validate_opening_prefix(context, prefix):
    from .native_corpus import NativeCorpusAuthorityV1, NativePlanRequestSearchAuthorizedV1, NativeBodySearchObservedV1
    if any(isinstance(e, t.ProviderAttemptAuthorizedEventV1) for e in prefix):
        raise ValueError('Opening SDK must be the first actual provider attempt')
    grants = [e for e in prefix if isinstance(e, NativePlanRequestSearchAuthorizedV1)]
    if isinstance(context.source_authority, NativeCorpusAuthorityV1):
        if (len(grants) != 1 or len([e for e in prefix if isinstance(e, NativeBodySearchObservedV1)
                and e.authorization_event_id == grants[0].event_id]) != 1):
            raise ValueError('Opening SDK requires actual settled request-owned discovery')
    elif grants:
        raise ValueError('Unavailable source authority cannot acquire a discovery grant')


def validate_opening_sdk_entry(execution, outcome, expected_authorization):
    """Join the locked stored first authorization to the admitted SDK gate.

    This is the same real authorization already proven against prepared bytes,
    not a new receipt or permission to replay an interrupted provider.
    """
    from .native_retrieval import NativePlanAuthorScopeAuthorizedV1, NativePlanOpeningAuthorizedV1
    authorizations = [e for e in execution.events if isinstance(e, t.ProviderAttemptAuthorizedEventV1)]
    current = authorizations[-1] if authorizations else None
    opening_entry = (type(current) in (NativePlanOpeningAuthorizedV1, NativePlanAuthorScopeAuthorizedV1)
        and outcome.outcome == 'sdk_entered' and outcome.provider_attempt_id == current.provider_attempt_id)
    if opening_entry:
        if type(expected_authorization) is not type(current) or expected_authorization != current:
            raise ValueError('Opening SDK entry differs from its exact admitted prepared authorization')
    elif expected_authorization is not None:
        raise ValueError('Opening SDK authorization cannot be borrowed by another lifecycle transition')


def request_manifest(*, action, work_context, source_authority_sha256, native_query_sha256,
        provenance_sha256, provider_roles, provider_input_accounting, admission):
    from .native_execution import NativePlanActionV3
    return dict(schema='dmb_native_plan_request_manifest_v1',
        intent=action.intent.model_dump(mode='json', by_alias=True),
        work_capabilities=dict(authoring_capture_sha256=action.authoring_capture.sha256 if action.authoring_capture is not None else None,
            placement_catalog_sha256=action.placement_catalog.sha256 if action.placement_catalog is not None else None,
            related_page_catalog_sha256=t.canonical_sha256([p.model_dump(mode='json', by_alias=True)
                for p in action.related_page_catalog]),
            **({'document_title': action.document_title} if type(action) is NativePlanActionV3 else {})),
        work_context=work_context.model_dump(mode='json', by_alias=True),
        provenance_sha256=provenance_sha256,
        source_authority_sha256=source_authority_sha256,
        native_query_sha256=native_query_sha256,
        provider_roles=provider_roles.model_dump(mode='json', by_alias=True)
            if hasattr(provider_roles, 'model_dump') else provider_roles,
        provider_input_accounting=provider_input_accounting.model_dump(mode='json', by_alias=True)
            if hasattr(provider_input_accounting, 'model_dump') else provider_input_accounting,
        request_context={key: value for key, value in admission.model_dump(mode='json').items()
            if key not in {'manifest_sha256', 'submitted_intent_sha256'}})


def validate_request_admission(context, execution):
    from .native_context import NativePlanRequestAdmissionV1, PlanWorkContextV1
    from .native_execution import NativePlanActionV2, NativePlanActionV3
    admission = context.assembled_input
    action = execution.policy.action
    if (type(admission) is not NativePlanRequestAdmissionV1
            or type(context.work_context) is not PlanWorkContextV1
            or type(action) not in (NativePlanActionV2, NativePlanActionV3)
            or type(context.work_context.plan_context_policy) is not t.PlanContextPolicyV2
            or admission.tokenizer_name != execution.policy.provider_input_accounting.estimator
            or admission.submitted_intent_sha256 != t.canonical_sha256(action.intent)):
        raise ValueError('Plan request admission differs from its actual governed request')
    manifest = request_manifest(action=action, work_context=context.work_context,
        source_authority_sha256=execution.policy.source_authority_sha256,
        native_query_sha256=execution.policy.native_query_sha256,
        provenance_sha256=context.provenance_sha256,
        provider_roles=execution.policy.provider_roles,
        provider_input_accounting=execution.policy.provider_input_accounting, admission=admission)
    if t.canonical_sha256(manifest) != admission.manifest_sha256:
        raise ValueError('Plan request admission manifest differs from its frozen owners')
    from .native_corpus import NativePlanRequestSearchAuthorizedV1, NativeInitialSourceSearchAuthorizedV1
    for event in execution.events:
        if isinstance(event, NativePlanRequestSearchAuthorizedV1) and event.request_manifest_sha256 != admission.manifest_sha256:
            raise ValueError('Request source grant differs from its actual request manifest')
        if isinstance(event, NativeInitialSourceSearchAuthorizedV1):
            raise ValueError('Request-admitted Plan cannot borrow the historical work-owned search')
        from .native_retrieval import NativePlanOpeningAuthorizedV1
        from .native_retrieval import NativePlanAuthorScopeAuthorizedV1
        if type(event) is NativePlanAuthorScopeAuthorizedV1 and type(action) is not NativePlanActionV3:
            raise ValueError('Author scope decisions require their actual contextual Plan action')
        if type(event) in (NativePlanOpeningAuthorizedV1, NativePlanAuthorScopeAuthorizedV1):
            validate_opening_prefix(context, execution.events[:event.sequence])
    return admission
