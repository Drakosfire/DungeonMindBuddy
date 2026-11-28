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
    AuthorLocationQuote, LiteralScopeName, NamedScopePath, ScopeExpression, ScopeWithExclusion,
    UnresolvedLocation, UnscopedLocation, author_scope_hypotheses,
    author_scope_offer_view, matches_literal_scope_path, name_key,
)
from .plan_placement import PlanRequestedWorkInputV8, PlanRequestedWorkInputV9
from .plan_authoring import (
    PlanAuthoringCaptureV1, PlanAuthoringComposedSnapshotV1, PlanRequestedWorkInputV1,
)
from .plan_composed_targeting import (
    ComposedColumn, ComposedPlanPlacementCatalogV1,
    composed_nomination_from_answers,
    prepare_composed_plan_nomination,
    resolve_composed_plan_nomination,
)
from .jev_retrieval_contract import Digest, NativePlanBatchDecisionInputV3, RetrievalDialogue


class NativePlanOpeningInputV1(PlanRequestedWorkInputV8, NativePlanBatchDecisionInputV3):
    schema_: Literal['dmb_native_plan_opening_input_v1'] = Field(
        default='dmb_native_plan_opening_input_v1', alias='schema')


PageEditIntent = Literal['page_edit', 'discussion', 'unresolved']
AuthorEditorFocus = Literal['text_selection', 'caret']
_EDITOR_FOCUS_GUIDANCE = {
    'text_selection': (
        'The author has selected existing text in the open Plan. For a direct request to '
        'rewrite or revise this with no other referent, choose the selected-text rewrite '
        'and no section constraint. Details requested for the new wording do not locate '
        'another passage. Respect requests for a different target or for a draft in chat.'
    ),
    'caret': (
        'The open Plan has a text caret. When the author asks to add writing and gives '
        'no existing page location, choose the unstated insertion location and no section '
        'constraint. Keep every explicit location, including a section qualifying an '
        'existing paragraph. A name used only as the subject of the new writing does '
        'not locate the edit. A stated but unclear page location remains unresolved. '
        'A request to discuss or draft in chat does not grant an edit.'
    ),
}
_CARET_INTENT_GUIDANCE = (
    "The open Plan has a text caret. First determine the requested work from the "
    "user's words. A request to explain, recount, trace or discuss existing "
    "events or evidence is discussion. A caret supplies a location only after "
    "the user asks to add writing to the open Plan. For that edit, when no "
    "existing page location is stated, choose the unstated insertion location "
    "and no section constraint. Keep every explicit location, including a section "
    "qualifying an existing paragraph. A name used only as the subject of new "
    "writing does not locate the edit. A stated but unclear page location "
    "remains unresolved. A request to draft in chat does not grant an edit."
)
_SELECTION_REFERENCE_GUIDANCE = (
    ' A direct request to rewrite or revise this can refer to the current selection '
    'without saying “selected text.” Choose the selection rewrite when “this” '
    'is the text to change and the author gives no different target. If “this” names '
    'an idea from the conversation or the request points to another location, '
    'use that meaning. A sample rewrite requested in chat is not a selection edit.'
)


class NativePlanIntentInputV1(Strict):
    """Visible context for the intent question before placement or source work."""

    question: str = Field(min_length=1)
    page_title: str | None = None
    selected_text: str | None = None
    dialogue: tuple[RetrievalDialogue, ...] = ()
    requested_operation: Literal["discuss", "write_current_page"] | None = None

    def prepare(self):
        from .surface_action_catalog import prepare_opening_intent

        state = {"surface": "plan", "user_utterance": self.question}
        if self.page_title is not None:
            state["page_title"] = self.page_title
        if self.selected_text is not None:
            state["selected_text"] = self.selected_text
        if self.dialogue:
            state["prior_dialogue"] = [row.model_dump() for row in self.dialogue]
        if self.requested_operation is not None:
            state["explicit_editor_operation"] = self.requested_operation
        return prepare_opening_intent("plan", state, plan_operation=self.requested_operation)


class NativePlanAuthorScopeInputV1(Strict):
    """Source-blind parent for one proposed interpretation of author text."""

    schema_: Literal['dmb_native_plan_author_scope_input_v1'] = Field(
        default='dmb_native_plan_author_scope_input_v1', alias='schema')
    question: str = Field(min_length=1)
    dialogue: tuple[RetrievalDialogue, ...]
    max_span_attempts: int = Field(strict=True, gt=0)
    quote_context: bool = Field(strict=True)
    assess_page_edit: bool = Field(default=False, strict=True, exclude_if=lambda value: not value)
    implicit_caret_version: Literal['v1'] | None = Field(default=None, exclude_if=lambda value: value is None)
    selection_reference_version: Literal['v1'] | None = Field(
        default=None, exclude_if=lambda value: value is None)
    editor_focus: AuthorEditorFocus | None = Field(default=None, exclude_if=lambda value: value is None)
    caret_guidance_version: Literal['v2'] | None = Field(default=None, exclude_if=lambda value: value is None)
    requested_operation: Literal['discuss', 'write_current_page'] | None = Field(
        default=None, exclude_if=lambda value: value is None)


class NativePlanAuthorScopeObservationV1(Strict):
    """Interpretation evidence alone, with no source or placement authority."""

    requested_work: str | None = Field(default=None, exclude_if=lambda value: value is None)
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
    implicit_caret_version: Literal['v1'] | None = Field(default=None, exclude_if=lambda value: value is None)
    evidence_relevance_version: Literal['v1'] | None = Field(
        default=None, exclude_if=lambda value: value is None)
    opening_graph_relevance_version: Literal['v1'] | None = Field(
        default=None, exclude_if=lambda value: value is None)


class NativePlanOpeningInputV3(NativePlanOpeningInputV1):
    schema_: Literal['dmb_native_plan_opening_input_v3'] = Field(
        default='dmb_native_plan_opening_input_v3', alias='schema')
    placement_catalog: ComposedPlanPlacementCatalogV1
    original_capture: PlanAuthoringComposedSnapshotV1
    author_scope_binding: NativePlanOpeningScopeBindingV1
    column_scope_version: Literal['v1'] | None = Field(default=None, exclude_if=lambda value: value is None)
    implicit_caret_version: Literal['v1'] | None = Field(default=None, exclude_if=lambda value: value is None)


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
    return prepare_composed_plan_nomination(author, request.original_capture, request.placement_catalog,
        offer_caret=request.implicit_caret_version == 'v1')


def _observed_column(scope) -> str | None:
    if (isinstance(scope, NamedScopePath) and not scope.rooted and scope.occurrence is None
            and len(scope.names) == 1 and isinstance(scope.names[0], LiteralScopeName)):
        return name_key(scope.names[0].text).removeprefix("the ")
    return None


_COLUMN_MENTION = re.compile(r'\b(?:only|left|middle|right)\s+column\b', re.IGNORECASE)
_COLUMN_PREFIX = re.compile(r'\b(?:in|within|inside|from|of)\s+(?:the\s+)?$', re.IGNORECASE)
_COLUMN_CLAUSE_END = re.compile(r'^\s*(?:[.!?,;:]|$)')


def composed_author_column(request) -> ComposedColumn | None:
    """Type a source-blind literal only when the author actually uses column syntax."""
    if request.column_scope_version != 'v1':
        return None
    observed = _observed_column(request.author_scope_binding.observation.scope)
    mentions = [row for row in _COLUMN_MENTION.finditer(request.question)
                if name_key(row.group()) == observed]
    if len(mentions) != 1:
        return None
    mention = mentions[0]
    prefix = _COLUMN_PREFIX.search(request.question[:mention.start()])
    if prefix is None or not _COLUMN_CLAUSE_END.match(request.question[mention.end():]):
        return None
    try:
        AuthorLocationQuote(utterance_index=len(request.dialogue), start=prefix.start(),
            end=mention.end(), text=request.question[prefix.start():mention.end()]).verify(
                request.question, request.dialogue,
            )
    except ValueError:
        return None
    return observed


def resolve_composed_opening(snapshot, catalog, binding, nomination, operation, *, author_column=None,
        implicit_caret_version=None):
    from .plan_contextual_targets import UNSTATED_INSERTION_LOCATION
    if author_column is not None and _observed_column(binding.observation.scope) != author_column:
        raise ValueError('Composed column differs from the retained author scope')
    if operation == 'discuss' or binding.page_edit_intent == 'discussion':
        intent = 'discuss'
    elif nomination.confirmed_work == 'different_destination':
        intent = 'different_destination'
    elif binding.page_edit_intent != 'page_edit':
        intent = 'clarify'
    else:
        intent = 'write_current_page'
    unstated_location = binding.observation.relation == UNSTATED_INSERTION_LOCATION
    resolved = resolve_composed_plan_nomination(snapshot, catalog, intent, nomination,
        allow_caret=(implicit_caret_version == 'v1' and unstated_location
            and isinstance(binding.observation.scope, UnscopedLocation) and author_column is None))
    capture = resolved.capture
    if capture is not None:
        observed_relation = binding.observation.relation
        if nomination.scope != 'caret_boundary' and observed_relation not in (
                'unresolved', f'{capture.slot_address.relation}_paragraph'):
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
            paragraph = catalog.paragraph_for(capture.slot_address)
            positive_matches = supports_literal_scope and (
                paragraph.column == author_column if author_column is not None
                else matches_literal_scope_path(paragraph.heading_path, positive)
            )
            if (not positive_matches or excluded is not None
                    and matches_literal_scope_path(paragraph.heading_path, excluded)):
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
    intent_opening: NativePlanIntentInputV1 | None = Field(default=None, exclude_if=lambda value: value is None)
    prior_scope_event_id: UUID | None = Field(default=None, exclude_if=lambda value: value is None)
    scope_review: tuple[NativePlanOpeningScopeBindingV1, NativePlanOpeningScopeBindingV1] | None = Field(
        default=None, exclude_if=lambda value: value is None)
    max_span_attempts: int = Field(strict=True, gt=0, le=2048)

    @property
    def digest(self) -> str:
        return t.canonical_sha256(self.model_dump(mode='json', by_alias=True))


def plan_intent_input(action, dialogue):
    capture = action.authoring_capture
    selected = (getattr(capture, "selection_witness_text", None)
                or (getattr(capture, "selected_text", None) if author_editor_focus(action) == "text_selection" else None))
    return NativePlanIntentInputV1(
        question=action.intent.message, page_title=getattr(action, "document_title", None),
        selected_text=selected or None, dialogue=tuple(dialogue),
        requested_operation=getattr(action.intent, "plan_requested_operation", None),
    )


def author_editor_focus(action) -> AuthorEditorFocus | None:
    """Project editor intent without sending selected bytes or editor geometry."""
    capture = action.authoring_capture
    if type(capture) is PlanAuthoringCaptureV1:
        if capture.target_kind == 'replace_selection':
            return 'text_selection'
        if capture.target_kind == 'insert_at_caret' and any(
                entry.kind == 'captured_target' for entry in action.placement_catalog.entries):
            return 'caret'
    if (type(capture) is PlanAuthoringComposedSnapshotV1
            and capture.from_ == capture.to):
        # The opening catalog still has to prove an exact available slot boundary.
        return 'caret'
    return None


def _include_editor_focus(state, request):
    from .plan_author_location import explicit_direction_options, explicit_scope_conflict

    if (request.editor_focus is None
            or explicit_direction_options(request.question, allow_plain_prose=True)
            or explicit_scope_conflict(request.question, UnscopedLocation())):
        return
    state['current_editor_focus'] = (_CARET_INTENT_GUIDANCE
        if request.editor_focus == 'caret' and request.caret_guidance_version == 'v2'
        else _EDITOR_FOCUS_GUIDANCE[request.editor_focus])


def _author_scope_offers(request):
    return author_scope_hypotheses(request.question, request.dialogue,
        max_span_attempts=request.max_span_attempts)


def _author_relation_options(request):
    from .plan_contextual_targets import AUTHOR_RELATIONS, UNSTATED_INSERTION_LOCATION

    if request.implicit_caret_version == 'v1':
        return AUTHOR_RELATIONS | {UNSTATED_INSERTION_LOCATION: (
            'The author asks to insert new writing into this Plan and leaves the page location open. '
            'Names that describe only the new writing do not name an existing page location. '
            'Use unresolved if the author states a location that is unclear, asks for incompatible '
            'locations, or leaves the kind of edit unclear.'
        )}
    return AUTHOR_RELATIONS


def prepare_author_scope_decision(request: NativePlanAuthorScopeInputV1):
    from generationengine.types import ChoiceDecisionQuestion, DecisionRequest
    from .jev_retrieval_contract import MODEL, PROVIDER
    if getattr(request, 'scope_review', None) is not None:
        return _prepare_author_scope_review(request)[0]
    intent_input = getattr(request, "intent_opening", None)
    if intent_input is not None:
        return intent_input.prepare()
    relation_options = _author_relation_options(request)
    hypotheses = _author_scope_offers(request)
    state = author_scope_offer_view(request.question, request.dialogue, hypotheses,
        include_quote_context=request.quote_context)
    _include_editor_focus(state, request)
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
        ChoiceDecisionQuestion(name='location_relation', options=tuple(relation_options),
            option_descriptions=relation_options,
            question='What relation to an existing location does the current author request? '
                'Use prior dialogue only to resolve a reference omitted from the current request. '
                'Rewriting the explicitly selected paragraph or text uses the whole capture, even when '
                'the replacement preserves its existing wording and adds a warning. Ignore ordering in '
                'proposed new content. If distinct relations cannot be reconciled, choose unresolved.'
                + (' Selected sentences, lines and excerpts are selected text.' if request.assess_page_edit else '')
                + (_SELECTION_REFERENCE_GUIDANCE if request.selection_reference_version == 'v1' else '')),
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
    from .plan_author_location import (
        LiteralScopeName, NamedScopePath, explicit_direction_options, explicit_scope_conflict, is_complete_scope_recovery,
        nominal_scope_needs_review, nominal_scope_subject,
    )

    relation_options = _author_relation_options(request)
    first, second = (row.observation for row in request.scope_review)
    hypotheses = _author_scope_offers(request)
    view = author_scope_offer_view(request.question, request.dialogue, hypotheses,
        include_quote_context=True)
    _include_editor_focus(view, request)
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
            interpretation = {'relation': relation_options[relation],
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
                interpretation = {'relation': relation_options[relation], 'scope': options[alias]}
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
        key = json.dumps({'relation': relation_options[relation], 'scope': {'kind': scope.kind}},
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
                criteria[alias] = (f'{relation_options[relation]} The author names “{scope.names[0].text}” as the '
                    f'section and describes the existing paragraph in that section by its subject “{subject}”.')
            elif nominal_scope_needs_review(request.question, scope):
                criteria[alias] = (f'{relation_options[relation]} The author uses the entire phrase '
                    f'“{scope.names[0].text}” as the exact section title, with no separate paragraph description.')
    criteria['unresolved'] = 'None of the complete offered interpretations matches the author location.'
    question = ChoiceDecisionQuestion(name='adjudicated_scope', options=tuple(criteria), option_descriptions=criteria,
        question='Choose the complete interpretation of the author’s existing location. '
            'The author can identify an existing prose block by what it says without using the word paragraph. '
            'An explicit selected-text rewrite uses its capture by itself. Do not treat its words as a heading. '
            'Preserve every author-established name, path and exclusion. Ignore new-fragment content as location evidence.'
            + (_SELECTION_REFERENCE_GUIDANCE if request.selection_reference_version == 'v1' else '')
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
    from .native_execution import NativePlanActionV2, NativePlanActionV3
    from .native_retrieval import NativePlanAuthorScopeAuthorizedV1

    if (type(authorization) is not NativePlanAuthorScopeAuthorizedV1
            or type(parent) is not NativePlanAuthorScopeParentV1
            or (type(execution.policy.action) is not NativePlanActionV3
                and not (type(execution.policy.action) is NativePlanActionV2 and parent.intent_opening is not None))
            or (parent.implicit_caret_version is not None
                and opening_input_type(execution.policy.action) not in (NativePlanOpeningInputV2, NativePlanOpeningInputV3))
            or type(context.assembled_input) is not NativePlanRequestAdmissionV1
            or (parent.editor_focus is not None
                and parent.editor_focus != author_editor_focus(execution.policy.action))
            or parent.request_manifest_sha256 != context.assembled_input.manifest_sha256
            or parent.prior_scope_event_id != authorization.prior_scope_event_id
            or parent.quote_context != (parent.prior_scope_event_id is not None)
            or parent.requested_operation != (getattr(execution.policy.action.intent, 'plan_requested_operation', None)
                if parent.assess_page_edit else None)
            or opening_dialogue_sha256(parent.dialogue) != context.assembled_input.dialogue_sha256):
        raise ValueError('Author scope parent differs from its admitted Plan request or dialogue')
    prefix = execution.events[:authorization.sequence]
    is_intent_opening = parent.intent_opening is not None
    if bool(authorization.intent_opening) != is_intent_opening:
        raise ValueError("Plan intent authorization differs from its exact producer")
    if is_intent_opening and (
        parent.intent_opening != plan_intent_input(execution.policy.action, parent.dialogue)
        or parent.prior_scope_event_id is not None or parent.scope_review is not None
    ):
        raise ValueError("Plan intent must be bound to the exact editor state")
    review_ids = tuple(row.observation_event_id for row in parent.scope_review) if parent.scope_review else None
    if authorization.scope_review_event_ids != review_ids or (review_ids is not None and parent.prior_scope_event_id):
        raise ValueError('Author scope review differs from its authorized prior observations')
    for row in parent.scope_review or ():
        require_retained_author_scope(execution.model_copy(update={'events': prefix}),
            row.observation_event_id, row.observation)
    validate_opening_prefix(context, prefix,
        author_scope_event_id=review_ids[-1] if review_ids else authorization.prior_scope_event_id,
        author_scope_recheck=True, review_event_ids=review_ids, author_question=parent.question,
        intent_opening=is_intent_opening)


def decode_author_scope_decision(request: NativePlanAuthorScopeInputV1, result):
    from .jev_retrieval_contract import validated_choice_answers
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
    intent_input = getattr(request, "intent_opening", None)
    if intent_input is not None:
        from .surface_action_catalog import opening_action_menu

        choice = validated_choice_answers(result, {"requested_work"})["requested_work"]
        if choice not in opening_action_menu("plan", plan_operation=intent_input.requested_operation):
            raise ValueError("Plan did not offer this requested work")
        return NativePlanAuthorScopeObservationV1(
            requested_work=choice, relation="unresolved", selected_alias="none",
            scope=UnscopedLocation(),
        )
    expected = {'location_relation', 'existing_scope'}
    if request.assess_page_edit:
        expected.add('page_edit_intent')
    answers = validated_choice_answers(result, expected)
    relation = answers['location_relation']
    if relation not in _author_relation_options(request):
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
    observations = [event.scope_observation for event in execution.events[:selected.sequence + 1]
                    if type(event) is NativePlanAuthorScopeObservedV1]
    opening_work = next((item.requested_work for item in observations if item.requested_work is not None), None)
    prior = [item.page_edit_intent for item in observations if item.requested_work is None][:2]
    if not any(prior):
        intent = None  # Historical openings have no retained edit-intent observations.
    elif prior == ['page_edit', 'page_edit']:
        intent = 'page_edit'
    elif 'discussion' in prior and 'page_edit' not in prior:
        intent = 'discussion'
    else:
        intent = 'unresolved'
    if opening_work == "discuss":
        intent = "discussion"
    elif opening_work == "clarify" or (opening_work is not None and opening_work != "write_current_page" and intent == "page_edit"):
        intent = "unresolved"
    return NativePlanOpeningScopeBindingV1(observation_event_id=observation_event_id,
        observation=observation, page_edit_intent=intent)


def can_skip_author_scope_recheck(request, observation, capture):
    from .plan_author_location import UnscopedLocation, explicit_direction_options
    from .plan_contextual_targets import UNSTATED_INSERTION_LOCATION

    # A bare caret supplies no location for an explicit discussion decision.
    # Keep the provider observation intact and preserve the direction veto.
    unscoped_relation = observation.relation == 'unresolved' or (
        observation.relation == UNSTATED_INSERTION_LOCATION
        and observation.page_edit_intent == 'discussion'
        and not explicit_direction_options(request.question, allow_plain_prose=True)
    )
    return (
        not request.dialogue
        and request.requested_operation is None
        and (capture is None or not capture.selected_text)
        and observation.page_edit_intent in ('discussion', 'unresolved')
        and unscoped_relation
        and observation.selected_alias == 'none'
        and isinstance(observation.scope, UnscopedLocation)
        and not _author_scope_offers(request)
        and not author_scope_review_required(request.question, observation, observation)
    )


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
    work_questions = work.questions
    if type(request) is NativePlanOpeningInputV2 and request.evidence_relevance_version == 'v1':
        guidance = (
            " A factual question about a place, person, event, object, or source belongs in discussion, "
            "even when its answer is a location or requires reading evidence. "
            "Choose clarification only if the requested action or an intended editing destination is ambiguous."
        )
        work_questions = tuple(q.model_copy(update={'question': q.question + guidance})
            if q.name == 'requested_work' else q for q in work_questions)
        saved_page_guidance = (
            " Include this page only if it provides evidence needed for the current request, "
            "such as an explicitly named or referenced page or an authored fact. "
            "A topic match alone does not warrant reading it."
        )
        state['candidates'] = [
            candidate | {'kind': candidate['kind'] + saved_page_guidance}
            if candidate['kind'].startswith('Saved authored Worldbuilding page;') else candidate
            for candidate in state['candidates']
        ]
    if type(request) is NativePlanOpeningInputV2 and request.opening_graph_relevance_version == 'v1':
        graph_votes = {f"candidate_{index}" for index, candidate in enumerate(request.candidates)
                       if candidate.kind.startswith("Native Graph object")}
        guidance = (
            " Read this Graph object when its own relationship, identity, event, or qualification could "
            "directly support the specific question. When an offered event targets the requested episode, "
            "do not also open a participant merely because they might be connected to it. "
            "Read both only when a distinct requested detail needs both objects."
        )
        questions = tuple(q.model_copy(update={'question': q.question + guidance})
            if q.name in graph_votes else q for q in questions)
    return DecisionRequest(provider=work.provider, model=work.model,
        state=state, questions=(*work_questions, *questions), max_transport_retries=0)


def _composed_opening_fields(request, answers):
    work = _composed_work_request(request)
    nomination = composed_nomination_from_answers(work, {q.name: answers[q.name] for q in work.questions})
    author_column = composed_author_column(request)
    return resolve_composed_opening(
        request.original_capture, request.placement_catalog,
        request.author_scope_binding, nomination, request.plan_requested_operation,
        author_column=author_column, implicit_caret_version=request.implicit_caret_version,
    ) | {"composed_nomination": nomination, "column_scope_version": request.column_scope_version,
           "implicit_caret_version": request.implicit_caret_version, "author_column": author_column}


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
                            review_event_ids=None, author_question='', intent_opening=False):
    if intent_opening:
        if any(type(event) is not t.BuildAuthoredReferencesCapturedV1 for event in prefix):
            raise ValueError("Plan intent must precede source reads and all provider calls")
        return
    from .native_corpus import NativeCorpusAuthorityV1, NativePlanRequestSearchAuthorizedV1, NativeBodySearchObservedV1
    from .native_retrieval import NativePlanAuthorScopeAuthorizedV1
    attempts = [e for e in prefix if isinstance(e, t.ProviderAttemptAuthorizedEventV1)]
    first_intent = attempts[0] if attempts and type(attempts[0]) is NativePlanAuthorScopeAuthorizedV1 and attempts[0].intent_opening else None
    if first_intent is not None:
        observations = [e for e in prefix if type(e) is NativePlanAuthorScopeObservedV1
                        and e.controller_attempt_id == first_intent.provider_attempt_id]
        if len(observations) != 1 or observations[0].scope_observation.requested_work is None:
            raise ValueError("Plan intent requires its settled first response")
        intent = observations[0]
        if author_scope_event_id == intent.event_id:
            if (author_scope_recheck or review_event_ids is not None or len(attempts) != 1
                    or intent.scope_observation.requested_work not in {"discuss", "clarify"}):
                raise ValueError("Only discussion or clarification can use the intent receipt without placement interpretation")
        else:
            attempts = attempts[1:]
            prefix = tuple(e for e in prefix if e is not intent)
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
        # Source-blind interpretation can precede discovery. Historical turns
        # with discovery already in the prefix still require exact settlement.
        if author_scope_recheck and not grants:
            return
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
        if (type(event) is NativePlanAuthorScopeAuthorizedV1 and type(action) is not NativePlanActionV3
                and not event.intent_opening):
            raise ValueError('Author scope decisions require their actual contextual Plan action')
        if type(event) is NativePlanAuthorScopeAuthorizedV1:
            review_ids = event.scope_review_event_ids
            if review_ids is not None and event.prior_scope_event_id is not None:
                raise ValueError('Author scope recheck and review require different authorizations')
            validate_opening_prefix(context, execution.events[:event.sequence],
                author_scope_event_id=review_ids[-1] if review_ids else event.prior_scope_event_id,
                author_scope_recheck=True, review_event_ids=review_ids, author_question=action.intent.message,
                intent_opening=event.intent_opening is True)
        elif type(event) is NativePlanOpeningAuthorizedV1:
            validate_opening_prefix(context, execution.events[:event.sequence],
                author_scope_event_id=event.author_scope_event_id, author_question=action.intent.message)
    return admission
