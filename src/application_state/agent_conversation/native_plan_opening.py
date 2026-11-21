"""The current Plan opening owns a request manifest and one actual SDK batch.

Request admission and provider dispatch are distinct commitments in the existing
Turn. Neither this manifest nor a navigation catalog is provider/body authority.
"""
from typing import Literal
import re
from uuid import UUID

from pydantic import Field

from . import types as t
from .native_statement_input import Strict
from .plan_author_location import (
    LiteralScopeName, NamedScopePath, ScopeExpression, ScopeWithExclusion,
    UnresolvedLocation, UnscopedLocation, author_scope_hypotheses,
    author_scope_offer_view, matches_literal_scope_path,
)
from .plan_placement import PlanRequestedWorkInputV8, PlanRequestedWorkInputV9
from .plan_authoring import PlanAuthoringComposedSnapshotV1, PlanRequestedWorkInputV1
from .plan_composed_targeting import (
    ComposedPlanPlacementCatalogV1,
    composed_nomination_from_answers,
    prepare_composed_plan_nomination,
    resolve_composed_plan_nomination,
)
from .jev_retrieval_contract import Digest, NativePlanBatchDecisionInputV3, RetrievalDialogue


class NativePlanOpeningInputV1(PlanRequestedWorkInputV8, NativePlanBatchDecisionInputV3):
    schema_: Literal['dmb_native_plan_opening_input_v1'] = Field(
        default='dmb_native_plan_opening_input_v1', alias='schema')


PageEditIntent = Literal['page_edit', 'discussion', 'unresolved']


class NativePlanAuthorScopeInputV1(Strict):
    """Source-blind parent for one proposed interpretation of author text."""

    schema_: Literal['dmb_native_plan_author_scope_input_v1'] = Field(
        default='dmb_native_plan_author_scope_input_v1', alias='schema')
    question: str = Field(min_length=1)
    dialogue: tuple[RetrievalDialogue, ...]
    max_span_attempts: int = Field(strict=True, gt=0)
    quote_context: bool = Field(strict=True)
    assess_page_edit: bool = Field(default=False, strict=True, exclude_if=lambda value: not value)
    requested_operation: Literal['discuss', 'write_current_page'] | None = Field(
        default=None, exclude_if=lambda value: value is None)


class NativePlanAuthorScopeObservationV1(Strict):
    """Interpretation evidence alone, with no source or placement authority."""

    relation: str
    selected_alias: str
    scope: ScopeExpression
    paragraph_subject: str | None = Field(default=None, min_length=1, exclude_if=lambda value: value is None)
    page_edit_intent: PageEditIntent | None = Field(default=None, exclude_if=lambda value: value is None)


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


class NativePlanOpeningScopeBindingV1(Strict):
    observation_event_id: UUID
    observation: NativePlanAuthorScopeObservationV1
    page_edit_intent: PageEditIntent | None = Field(default=None, exclude_if=lambda value: value is None)


class NativePlanOpeningInputV2(PlanRequestedWorkInputV9, NativePlanOpeningInputV1):
    schema_: Literal['dmb_native_plan_opening_input_v2'] = Field(
        default='dmb_native_plan_opening_input_v2', alias='schema')
    author_scope_binding: NativePlanOpeningScopeBindingV1 | None = Field(
        default=None, exclude_if=lambda value: value is None)


class NativePlanOpeningInputV3(NativePlanOpeningInputV1):
    schema_: Literal['dmb_native_plan_opening_input_v3'] = Field(
        default='dmb_native_plan_opening_input_v3', alias='schema')
    placement_catalog: ComposedPlanPlacementCatalogV1
    original_capture: PlanAuthoringComposedSnapshotV1
    author_scope_binding: NativePlanOpeningScopeBindingV1


NATIVE_PLAN_OPENING_INPUT_TYPES = (
    NativePlanOpeningInputV1, NativePlanOpeningInputV2, NativePlanOpeningInputV3,
)


def opening_input_type(action):
    from .native_execution import NativePlanActionV3
    if type(action) is NativePlanActionV3:
        if type(action.placement_catalog) is ComposedPlanPlacementCatalogV1:
            return NativePlanOpeningInputV3
        return NativePlanOpeningInputV2
    return NativePlanOpeningInputV1


def _composed_work_request(request):
    author = PlanRequestedWorkInputV1(
        request_id=request.request_id, parent_attempt_id=request.parent_attempt_id,
        scope_sha256=request.scope_sha256, question=request.question, page_title=request.page_title,
        dialogue=tuple({"role": row.role, "content": row.content} for row in request.dialogue),
        target_available=False,
    )
    return prepare_composed_plan_nomination(author, request.original_capture, request.placement_catalog)


def resolve_composed_opening(snapshot, catalog, binding, nomination, operation):
    if operation == 'discuss' or binding.page_edit_intent == 'discussion':
        intent = 'discuss'
    elif nomination.confirmed_work == 'different_destination':
        intent = 'different_destination'
    elif binding.page_edit_intent != 'page_edit':
        intent = 'clarify'
    else:
        intent = 'write_current_page'
    resolved = resolve_composed_plan_nomination(snapshot, catalog, intent, nomination)
    capture = resolved.capture
    if capture is not None:
        observed_relation = binding.observation.relation
        if observed_relation not in ('unresolved', f'{capture.slot_address.relation}_paragraph'):
            return {'requested_work': 'clarify', 'target_resolution': 'unresolved',
                    'placement_selector': None, 'target_capture_sha256': None}
        scope = binding.observation.scope
        if isinstance(scope, (NamedScopePath, ScopeWithExclusion)):
            positive = scope.positive if isinstance(scope, ScopeWithExclusion) else scope
            excluded = scope.excluded if isinstance(scope, ScopeWithExclusion) else None
            paths = (positive, excluded) if excluded is not None else (positive,)
            supports_literal_scope = all(
                path.occurrence is None and all(isinstance(name, LiteralScopeName) for name in path.names)
                for path in paths
            )
            headings = catalog.paragraph_for(capture.slot_address).heading_path
            if (not supports_literal_scope or not matches_literal_scope_path(headings, positive)
                    or excluded is not None and matches_literal_scope_path(headings, excluded)):
                return {'requested_work': 'clarify', 'target_resolution': 'unresolved',
                        'placement_selector': None, 'target_capture_sha256': None}
    return {
        'requested_work': resolved.work,
        'target_resolution': resolved.resolution,
        'placement_selector': catalog.selector_for(capture.slot_address) if capture is not None else None,
        'target_capture_sha256': capture.sha256 if capture is not None else None,
    }

_CAPTURE_REWRITE = re.compile(r'^\s*(?:please\s+)?(?:rewrite|replace|revise|edit|update)\s+'
    r'(?:(?:the|my)\s+)?(?:selected|highlighted)\s+(?:paragraph|text|passage)\b', re.IGNORECASE)
_CURRENT_CAPTURE_REWRITE = re.compile(r'^\s*(?:please\s+)?(?:rewrite|replace|revise|edit|update)\s+'
    r'(?:only\s+)?(?:(?:the|my)\s+)?(?:selected|highlighted)\s+'
    r'(?:paragraph|text|passage|sentence|line|excerpt|phrase)\b', re.IGNORECASE)


def explicit_capture_rewrite(question, *, assessed_edit_intent):
    pattern = _CURRENT_CAPTURE_REWRITE if assessed_edit_intent else _CAPTURE_REWRITE
    return pattern.match(question) is not None


class NativePlanAuthorScopeParentV1(NativePlanAuthorScopeInputV1):
    """Host binding for the exact source-blind SDK request."""

    schema_: Literal['dmb_native_plan_author_scope_parent_v1'] = Field(
        default='dmb_native_plan_author_scope_parent_v1', alias='schema')
    request_id: UUID
    parent_attempt_id: UUID
    scope_sha256: Digest
    request_manifest_sha256: Digest
    prior_scope_event_id: UUID | None = Field(default=None, exclude_if=lambda value: value is None)
    scope_review: tuple[NativePlanOpeningScopeBindingV1, NativePlanOpeningScopeBindingV1] | None = Field(
        default=None, exclude_if=lambda value: value is None)
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
    from .plan_contextual_targets import AUTHOR_RELATIONS

    if getattr(request, 'scope_review', None) is not None:
        return _prepare_author_scope_review(request)[0]
    hypotheses = _author_scope_offers(request)
    state = author_scope_offer_view(request.question, request.dialogue, hypotheses,
        include_quote_context=request.quote_context)
    choices = {
        'none': 'The author places no existing section or heading restriction on the destination.',
        'unresolved': 'No offered complete scope preserves the author location constraints.',
        **{key: f'This complete author scope is the existing location: {key}' for key in hypotheses},
    }
    edit_question = ()
    preservation_instruction = ''
    operation_instruction = ''
    if request.assess_page_edit:
        preservation_instruction = (' A separate instruction to leave surrounding text untouched does '
            'not add a destination constraint. “This Plan” and “the current page” refer to the document.')
        if request.requested_operation is not None:
            state['explicit_editor_operation'] = request.requested_operation
            operation_instruction = (' The explicit_editor_operation is the operation the author chose '
                'in the interface. Use it as evidence when the text leaves the mode implicit. If the text '
                'explicitly asks for conversation or defers the edit, it does not authorize a page edit.')
        edit_choices = {
            'page_edit': 'The author actually asks for an edit proposal for this Plan page now, even if the exact location needs clarification.',
            'discussion': 'The author asks for a conversational answer, advice, example or draft in chat, or discusses or defers a possible edit.',
            'unresolved': 'The current turn does not establish whether the author wants this page edited now.',
        }
        edit_question = (ChoiceDecisionQuestion(name='page_edit_intent',
            options=tuple(edit_choices), option_descriptions=edit_choices,
            question='Does the author currently ask Buddy to prepare an actual edit of this Plan page? '
                'Treat quoted/sample instructions, hypothetical edits, feedback on wording or location, '
                'and a request to discuss before acting as conversation. An earlier plan to edit does '
                'not authorize this turn. Use prior dialogue only to understand a current explicit '
                'confirmation or reference. An instruction to preserve unrelated material can still authorize '
                'a bounded edit.' + operation_instruction),)
    return DecisionRequest(provider=PROVIDER, model=MODEL, state=state, questions=(
        *edit_question,
        ChoiceDecisionQuestion(name='location_relation', options=tuple(AUTHOR_RELATIONS),
            option_descriptions=AUTHOR_RELATIONS,
            question='What relation to an existing location does the current author request? '
                'Use prior dialogue only to resolve a reference omitted from the current request. '
                'Rewriting the explicitly selected paragraph or text uses the whole capture, even when '
                'the replacement preserves its existing wording and adds a warning. Ignore ordering in '
                'proposed new content. If distinct relations cannot be reconciled, choose unresolved.'
                + (' Selected sentences, lines and excerpts are selected text.' if request.assess_page_edit else '')),
        ChoiceDecisionQuestion(name='existing_scope', options=tuple(choices), option_descriptions=choices,
            question='Choose the complete existing section or heading constraint from scope_hypotheses. '
                'Preserve every name, hierarchy and exclusion even when a name might be absent. '
                'A paragraph subject or a phrase supplied for new writing is not itself a section. '
                'Assistant statements cannot establish a scope. If an ordinal, separate branches or a '
                'missing alternative cannot be represented, choose unresolved.' + preservation_instruction),
    ), max_transport_retries=0)


def _prepare_author_scope_review(request):
    import json
    from generationengine.types import ChoiceDecisionQuestion, DecisionRequest
    from .jev_retrieval_contract import MODEL, PROVIDER
    from .plan_contextual_targets import AUTHOR_RELATIONS
    from .plan_author_location import (
        LiteralScopeName, NamedScopePath, explicit_direction_options, explicit_scope_conflict, is_complete_scope_recovery,
        nominal_scope_needs_review, nominal_scope_subject,
    )

    first, second = (row.observation for row in request.scope_review)
    hypotheses = _author_scope_offers(request)
    view = author_scope_offer_view(request.question, request.dialogue, hypotheses,
        include_quote_context=True)
    options = view.pop('scope_hypotheses')
    pairs = {}
    relations = {first.relation, second.relation}
    explicit_conflict = any(explicit_scope_conflict(request.question, prior.scope) for prior in (first, second))
    nominal_review = any(nominal_scope_needs_review(request.question, prior.scope) for prior in (first, second))
    if 'unresolved' in relations:
        relations.update(explicit_direction_options(request.question,
            allow_plain_prose=first.page_edit_intent == second.page_edit_intent == 'page_edit'))
    for relation in sorted(relations):
        for prior in (first, second):
            interpretation = {'relation': AUTHOR_RELATIONS[relation],
                'scope': options.get(prior.selected_alias, {'kind': prior.scope.kind})}
            key = json.dumps(interpretation, sort_keys=True, ensure_ascii=False)
            pairs.setdefault(key, (relation, prior.scope, prior.paragraph_subject))
    if _unresolved_author_scope(first, second) or explicit_conflict or nominal_review:
        for alias, hypothesis in hypotheses.items():
            subject = nominal_scope_subject(hypothesis, request.question, request.dialogue) if nominal_review else None
            if subject is None and not is_complete_scope_recovery(hypothesis, request.question, request.dialogue):
                continue
            scope = hypothesis.compile(request.question, request.dialogue)
            if subject is not None and (not isinstance(scope, NamedScopePath) or len(scope.names) != 1
                    or not isinstance(scope.names[0], LiteralScopeName)):
                continue
            for relation in sorted(relations - {'unresolved'}):
                if subject is not None and relation not in {'before_paragraph', 'after_paragraph'}:
                    continue
                interpretation = {'relation': AUTHOR_RELATIONS[relation], 'scope': options[alias]}
                if subject is not None:
                    interpretation['existing_paragraph_subject'] = subject
                key = json.dumps(interpretation, sort_keys=True, ensure_ascii=False)
                pairs.setdefault(key, (relation, scope, subject))
    if explicit_conflict:
        eligible = {description: pair for description, pair in pairs.items()
                    if not explicit_scope_conflict(request.question, pair[1])}
        pairs = eligible or pairs
    assessed_edit_intent = bool(first.page_edit_intent or second.page_edit_intent)
    explicit_rewrite = explicit_capture_rewrite(request.question, assessed_edit_intent=assessed_edit_intent)
    if explicit_rewrite:
        # An explicit author-requested rewrite supplies a possible analysis for
        # Jev to judge even if both initial passes carried over a prior relation.
        scope = UnscopedLocation()
        relation = 'replace_explicit_selection'
        key = json.dumps({'relation': AUTHOR_RELATIONS[relation], 'scope': {'kind': scope.kind}},
            sort_keys=True, ensure_ascii=False)
        pairs.setdefault(key, (relation, scope, None))
        if all(isinstance(prior.scope, (UnscopedLocation, UnresolvedLocation))
               for prior in (first, second)):
            # The requested destination is the selection. Neither observation
            # found a section constraint that needs dialogue to disambiguate.
            view['dialogue'] = []
    bindings = {f'option{i}': pair for i, (_, pair) in enumerate(sorted(pairs.items()))}
    criteria = {f'option{i}': key for i, key in enumerate(sorted(pairs))}
    if nominal_review:
        for alias, (relation, scope, subject) in bindings.items():
            if subject is not None:
                criteria[alias] = (f'{AUTHOR_RELATIONS[relation]} The author names “{scope.names[0].text}” as the '
                    f'section and describes the existing paragraph in that section by its subject “{subject}”.')
            elif nominal_scope_needs_review(request.question, scope):
                criteria[alias] = (f'{AUTHOR_RELATIONS[relation]} The author uses the entire phrase '
                    f'“{scope.names[0].text}” as the exact section title, with no separate paragraph description.')
    criteria['unresolved'] = 'None of the complete offered interpretations matches the author location.'
    question = ChoiceDecisionQuestion(name='adjudicated_scope', options=tuple(criteria), option_descriptions=criteria,
        question='Choose the complete interpretation of the author’s existing location. '
            'The author can identify an existing prose block by what it says without using the word paragraph. '
            'An explicit selected-text rewrite uses its capture by itself. Do not treat its words as a heading. '
            'Preserve every author-established name, path and exclusion. Ignore new-fragment content as location evidence.'
            + (' A separate instruction to leave surrounding text untouched does not add a destination constraint.'
               if assessed_edit_intent else '')
            + (' A scope stated in the current request supersedes earlier dialogue.' if explicit_conflict else '')
            + (' In an unquoted phrase that names both a section and the subject of its paragraph, preserve '
                'the section label by itself. Consider the full phrase as a title when the author names it as such.'
                if nominal_review else ''))
    return DecisionRequest(provider=PROVIDER, model=MODEL, state=view,
        questions=(question,), max_transport_retries=0), bindings


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
            or parent.prior_scope_event_id != authorization.prior_scope_event_id
            or parent.quote_context != (parent.prior_scope_event_id is not None)
            or parent.requested_operation != (getattr(execution.policy.action.intent, 'plan_requested_operation', None)
                if parent.assess_page_edit else None)
            or opening_dialogue_sha256(parent.dialogue) != context.assembled_input.dialogue_sha256):
        raise ValueError('Author scope parent differs from its admitted Plan request or dialogue')
    prefix = execution.events[:authorization.sequence]
    review_ids = tuple(row.observation_event_id for row in parent.scope_review) if parent.scope_review else None
    if authorization.scope_review_event_ids != review_ids or (review_ids is not None and parent.prior_scope_event_id):
        raise ValueError('Author scope review differs from its authorized prior observations')
    for row in parent.scope_review or ():
        require_retained_author_scope(execution.model_copy(update={'events': prefix}),
            row.observation_event_id, row.observation)
    validate_opening_prefix(context, prefix,
        author_scope_event_id=review_ids[-1] if review_ids else authorization.prior_scope_event_id,
        author_scope_recheck=True, review_event_ids=review_ids, author_question=parent.question)


def decode_author_scope_decision(request: NativePlanAuthorScopeInputV1, result):
    from .jev_retrieval_contract import validated_choice_answers
    from .plan_contextual_targets import AUTHOR_RELATIONS

    if getattr(request, 'scope_review', None) is not None:
        _, bindings = _prepare_author_scope_review(request)
        alias = validated_choice_answers(result, {'adjudicated_scope'})['adjudicated_scope']
        if alias == 'unresolved':
            return NativePlanAuthorScopeObservationV1(relation='unresolved', selected_alias=alias,
                scope=UnresolvedLocation(reason='The author scope interpretations could not be reconciled'))
        if alias not in bindings:
            raise ValueError('Author scope review names an unoffered interpretation')
        relation, scope, subject = bindings[alias]
        return NativePlanAuthorScopeObservationV1(
            relation=relation, selected_alias=alias, scope=scope, paragraph_subject=subject)
    expected = {'location_relation', 'existing_scope'}
    if request.assess_page_edit:
        expected.add('page_edit_intent')
    answers = validated_choice_answers(result, expected)
    relation = answers['location_relation']
    if relation not in AUTHOR_RELATIONS:
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
    return NativePlanAuthorScopeObservationV1(relation=relation, selected_alias=alias, scope=scope,
        page_edit_intent=answers.get('page_edit_intent'))


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


def bind_opening_author_scope(execution, observation_event_id, observation):
    selected = require_retained_author_scope(execution, observation_event_id, observation)
    prior = [event.scope_observation.page_edit_intent for event in execution.events[:selected.sequence + 1]
             if type(event) is NativePlanAuthorScopeObservedV1][:2]
    if not any(prior):
        intent = None  # Historical openings have no retained edit-intent observations.
    elif prior == ['page_edit', 'page_edit']:
        intent = 'page_edit'
    elif 'discussion' in prior and 'page_edit' not in prior:
        intent = 'discussion'
    else:
        intent = 'unresolved'
    return NativePlanOpeningScopeBindingV1(observation_event_id=observation_event_id,
        observation=observation, page_edit_intent=intent)


def author_scope_review_required(question, first, second):
    from .plan_author_location import explicit_direction_options, explicit_scope_conflict, nominal_scope_needs_review

    return (first.relation != second.relation or first.scope != second.scope
        or _unresolved_author_scope(first, second)
        or explicit_scope_conflict(question, first.scope)
        or nominal_scope_needs_review(question, first.scope)
        or (first.relation == 'unresolved' and bool(explicit_direction_options(question,
            allow_plain_prose=first.page_edit_intent == second.page_edit_intent == 'page_edit')))
        or (first.relation != 'replace_explicit_selection' and explicit_capture_rewrite(
            question, assessed_edit_intent=bool(first.page_edit_intent or second.page_edit_intent))))


def _unresolved_author_scope(first, second):
    return (first.relation != 'unresolved' and second.relation != 'unresolved'
        and isinstance(first.scope, UnresolvedLocation) and isinstance(second.scope, UnresolvedLocation))


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
    work = _composed_work_request(request) if type(request) is NativePlanOpeningInputV3 else _prepare_requested_work_only(request)
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
    if type(request) in (NativePlanOpeningInputV2, NativePlanOpeningInputV3):
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


def _composed_opening_fields(request, answers):
    work = _composed_work_request(request)
    nomination = composed_nomination_from_answers(work, {q.name: answers[q.name] for q in work.questions})
    return resolve_composed_opening(
        request.original_capture, request.placement_catalog,
        request.author_scope_binding, nomination, request.plan_requested_operation,
    ) | {"composed_nomination": nomination}


def composed_opening_fields(request, result):
    from .jev_retrieval_contract import validated_choice_answers
    answers = validated_choice_answers(result, {q.name for q in prepare_opening_decision(request).questions})
    return _composed_opening_fields(request, answers)


def decode_opening_decision(request, result):
    from .jev_retrieval_contract import validated_choice_answers, _selection_from_choices, _validate_selection_choices
    from .plan_authoring import requested_work_choice
    from .plan_placement import work_choice
    composed = type(request) is NativePlanOpeningInputV3
    expected = {'operation', 'post_read_plan',
        *(f'candidate_{i}' for i in range(len(request.candidates)))}
    if composed:
        expected.update(q.name for q in _composed_work_request(request).questions)
    else:
        expected.add('requested_work')
        if type(request) is NativePlanOpeningInputV2:
            from .plan_contextual_targets import target_answer_keys
            expected.update(target_answer_keys(request))
    answers = validated_choice_answers(result, expected)
    if composed:
        selected_work = answers["confirmed_work"]
        actual_work = _composed_opening_fields(request, answers)["requested_work"]
    else:
        selected_work = requested_work_choice(request, answers['requested_work'])
        actual_work = work_choice(request, selected_work, **(
            {'contextual_answers': answers}
            if type(request) is NativePlanOpeningInputV2 else {}))['requested_work']
    if type(request) in (NativePlanOpeningInputV2, NativePlanOpeningInputV3) and actual_work != 'discuss':
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
    if type(parent) is not opening_input_type(execution.policy.action):
        raise ValueError('Opening input differs from the actual target-resolution contract')
    if (type(parent) in (NativePlanOpeningInputV2, NativePlanOpeningInputV3)
            and parent.page_title != (execution.policy.action.document_title or '')):
        raise ValueError('Opening title differs from its frozen Content metadata')
    if (type(parent) not in NATIVE_PLAN_OPENING_INPUT_TYPES
            or type(authorization) is not NativePlanOpeningAuthorizedV1
            or type(context.assembled_input) is not NativePlanRequestAdmissionV1
            or opening_dialogue_sha256(parent.dialogue) != context.assembled_input.dialogue_sha256
            or any(getattr(parent, k) != v for k, v in _source_pins(context).items())):
        raise ValueError('Opening SDK parent differs from its actual request/source/dialogue admission')
    prefix = execution.events[:authorization.sequence]
    binding = getattr(parent, 'author_scope_binding', None)
    event_id = binding.observation_event_id if binding is not None else None
    if authorization.author_scope_event_id != event_id:
        raise ValueError('Opening authorization differs from its author scope parent')
    if binding is not None and binding != bind_opening_author_scope(
            execution.model_copy(update={'events': prefix}), binding.observation_event_id, binding.observation):
        raise ValueError('Opening page edit intent differs from its actual author observations')
    validate_opening_prefix(context, prefix, author_scope_event_id=event_id, author_question=parent.question)


def validate_opening_prefix(context, prefix, *, author_scope_event_id=None, author_scope_recheck=False,
                            review_event_ids=None, author_question=''):
    from .native_corpus import NativeCorpusAuthorityV1, NativePlanRequestSearchAuthorizedV1, NativeBodySearchObservedV1
    from .native_retrieval import NativePlanAuthorScopeAuthorizedV1
    attempts = [e for e in prefix if isinstance(e, t.ProviderAttemptAuthorizedEventV1)]
    if author_scope_event_id is not None:
        observations = [e for e in prefix if type(e) is NativePlanAuthorScopeObservedV1]
        allowed_counts = (2,) if review_event_ids is not None else (1,) if author_scope_recheck else (1, 2, 3)
        if (len(attempts) not in allowed_counts or len(observations) != len(attempts)
                or observations[-1].event_id != author_scope_event_id
                or any(type(a) is not NativePlanAuthorScopeAuthorizedV1
                    or o.controller_attempt_id != a.provider_attempt_id for a, o in zip(attempts, observations))
                or attempts[0].prior_scope_event_id is not None or attempts[0].scope_review_event_ids is not None
                or (len(attempts) >= 2 and (attempts[1].prior_scope_event_id != observations[0].event_id
                    or attempts[1].scope_review_event_ids is not None))):
            raise ValueError('Scope-bound stage requires its exact earlier observed author attempts')
        if len(observations) >= 2:
            first, second = (event.scope_observation for event in observations[:2])
            disagreement = author_scope_review_required(author_question, first, second)
            prior_ids = tuple(event.event_id for event in observations[:2])
            if review_event_ids is not None and (review_event_ids != prior_ids or not disagreement):
                raise ValueError('Author scope review requires the exact disagreeing pair')
            if len(observations) == 3 and (not disagreement or attempts[2].prior_scope_event_id is not None
                    or attempts[2].scope_review_event_ids != prior_ids):
                raise ValueError('Scope-bound opening requires an actual adjudication of the disagreeing pair')
            if len(observations) == 2 and disagreement and review_event_ids is None:
                raise ValueError('Disagreeing author scope observations require adjudication before opening')
    elif attempts:
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
        if type(event) is NativePlanAuthorScopeAuthorizedV1:
            review_ids = event.scope_review_event_ids
            if review_ids is not None and event.prior_scope_event_id is not None:
                raise ValueError('Author scope recheck and review require different authorizations')
            validate_opening_prefix(context, execution.events[:event.sequence],
                author_scope_event_id=review_ids[-1] if review_ids else event.prior_scope_event_id,
                author_scope_recheck=True, review_event_ids=review_ids, author_question=action.intent.message)
        elif type(event) is NativePlanOpeningAuthorizedV1:
            validate_opening_prefix(context, execution.events[:event.sequence],
                author_scope_event_id=event.author_scope_event_id, author_question=action.intent.message)
    return admission
