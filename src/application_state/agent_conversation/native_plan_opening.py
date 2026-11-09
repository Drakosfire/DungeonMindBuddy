"""The current Plan opening owns a request manifest and one actual SDK batch.

Request admission and provider dispatch are distinct commitments in the existing
Turn. Neither this manifest nor a navigation catalog is provider/body authority.
"""
from typing import Literal

from pydantic import Field

from . import types as t
from .plan_placement import PlanRequestedWorkInputV8
from .jev_retrieval_contract import NativePlanBatchDecisionInputV3


class NativePlanOpeningInputV1(PlanRequestedWorkInputV8, NativePlanBatchDecisionInputV3):
    schema_: Literal['dmb_native_plan_opening_input_v1'] = Field(
        default='dmb_native_plan_opening_input_v1', alias='schema')


def opening_dialogue_sha256(dialogue):
    from .jev_retrieval_contract import RetrievalDialogue
    return t.canonical_sha256([RetrievalDialogue.model_validate(
        r.model_dump() if hasattr(r, 'model_dump') else r).model_dump() for r in dialogue])


def opening_metadata_available(context, execution):
    from .native_context import NativePlanRequestAdmissionV1, SurfaceNativeContextReceiptV1
    from .native_execution import NativePlanActionV2
    return (type(context) is SurfaceNativeContextReceiptV1
        and type(context.assembled_input) is NativePlanRequestAdmissionV1
        and type(execution.policy.action) is NativePlanActionV2
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
    answers = validated_choice_answers(result, expected)
    selected_work = requested_work_choice(request, answers['requested_work'])
    actual_work = work_choice(request, selected_work)['requested_work']
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
    if (type(parent) is not NativePlanOpeningInputV1
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
    from .native_retrieval import NativePlanOpeningAuthorizedV1
    authorizations = [e for e in execution.events if isinstance(e, t.ProviderAttemptAuthorizedEventV1)]
    current = authorizations[-1] if authorizations else None
    opening_entry = (type(current) is NativePlanOpeningAuthorizedV1
        and outcome.outcome == 'sdk_entered' and outcome.provider_attempt_id == current.provider_attempt_id)
    if opening_entry:
        if type(expected_authorization) is not NativePlanOpeningAuthorizedV1 or expected_authorization != current:
            raise ValueError('Opening SDK entry differs from its exact admitted prepared authorization')
    elif expected_authorization is not None:
        raise ValueError('Opening SDK authorization cannot be borrowed by another lifecycle transition')


def request_manifest(*, action, work_context, source_authority_sha256, native_query_sha256,
        provenance_sha256, provider_roles, provider_input_accounting, admission):
    return dict(schema='dmb_native_plan_request_manifest_v1',
        intent=action.intent.model_dump(mode='json', by_alias=True),
        work_capabilities=dict(authoring_capture_sha256=action.authoring_capture.sha256 if action.authoring_capture is not None else None,
            placement_catalog_sha256=action.placement_catalog.sha256 if action.placement_catalog is not None else None,
            related_page_catalog_sha256=t.canonical_sha256([p.model_dump(mode='json', by_alias=True)
                for p in action.related_page_catalog])),
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
    from .native_execution import NativePlanActionV2
    admission = context.assembled_input
    action = execution.policy.action
    if (type(admission) is not NativePlanRequestAdmissionV1
            or type(context.work_context) is not PlanWorkContextV1
            or type(action) is not NativePlanActionV2
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
        if type(event) is NativePlanOpeningAuthorizedV1:
            validate_opening_prefix(context, execution.events[:event.sequence])
    return admission
