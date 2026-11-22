"""Literal reference binding exercises names and occurrences, not editor offsets."""
import asyncio
import json

import httpx2
import pytest
from apps.live_control_server.services.plan_jev_dispatch import decision_client

from application_state.agent_conversation.plan_author_location import (
    AuthorLocationQuote, AuthorScopeHypothesis, DescribedScopeName, DocumentTitleScopeName,
    LiteralScopeName, NamedScopePath, ScopeWithExclusion,
    UnresolvedLocation, UnscopedLocation, author_scope_hypotheses, author_scope_offer_view,
    bind_scope, literal_reference,
    source_heading_inventory,
)
from application_state.agent_conversation.jev_retrieval_contract import RetrievalDialogue
from application_state.agent_conversation.native_plan_opening import (
    NativePlanAuthorScopeInputV1, author_editor_focus, decode_author_scope_decision, prepare_author_scope_decision,
    validate_author_scope_wire,
)
from tests.application_state.test_plan_contextual_targets import captured_catalog, family_catalog, heading, prose


def author_quote(text, quote, utterance_index=0):
    start = text.index(quote)
    return AuthorLocationQuote(utterance_index=utterance_index, start=start,
        end=start + len(quote), text=quote)


def test_location_quote_uses_exact_admitted_author_turn_and_offsets():
    earlier = 'Use “North. Gate” in the plan.'
    current = "Keep the keeper's warning. Use Café North instead."
    dialogue = (RetrievalDialogue(role='user', content=earlier),
        RetrievalDialogue(role='assistant', content='Use South.'))
    assert author_quote(earlier, '“North. Gate”').verify(current, dialogue) == '“North. Gate”'
    assert author_quote(current, 'Café North', 2).verify(current, dialogue) == 'Café North'
    with pytest.raises(ValueError, match='admitted author utterance'):
        author_quote('Use South.', 'South', 1).verify(current, dialogue)
    with pytest.raises(ValueError, match='admitted author utterance'):
        author_quote(current, 'Café North', 3).verify(current, dialogue)
    with pytest.raises(ValueError, match='exact author quote'):
        author_quote(current, 'Café North', 2).model_copy(update={'text': 'Cafe North'}).verify(current, dialogue)


def test_location_quote_does_not_treat_plural_possessive_as_quote_opener():
    request = "After the players' notes, use 'North Gate'."
    assert author_quote(request, "'North Gate'").verify(request, ()) == "'North Gate'"
    with pytest.raises(ValueError, match='within a quoted name'):
        author_quote(request, 'North').verify(request, ())


@pytest.mark.parametrize('text,quote,error', [
    ('Use Preparation. Leave it intact.', 'Preparation. Leave', 'sentence boundary'),
    ('Use “North. Gate”.', 'North.', 'within a quoted name'),
    ('Use “North. Gate”.', '“North.', 'within a quoted name'),
    ('Use Workshop.', 'shop', 'cut a word'),
    ('Use Workshop.', 'Work', 'cut a word'),
    ('Use Workshop.', ' Workshop', 'exact author quote'),
])
def test_location_quote_rejects_partial_or_cross_sentence_evidence(text, quote, error):
    with pytest.raises(ValueError, match=error):
        author_quote(text, quote).verify(text, ())


@pytest.mark.parametrize('phrase,grammar,names,edges', [
    ('Mill / Equipment', 'literal_path', (LiteralScopeName(text='Mill'),
        LiteralScopeName(text='Equipment')), ('direct_parent',)),
    ('“North / South”', 'literal_name', (LiteralScopeName(text='North / South'),), ()),
    ('“Tea and Cakes”', 'literal_name', (LiteralScopeName(text='Tea and Cakes'),), ()),
    ('“A paragraph in winter”', 'literal_name', (LiteralScopeName(text='A paragraph in winter'),), ()),
    ('Equipment inside Atrium / East passage', 'natural_path', (LiteralScopeName(text='Atrium'),
        LiteralScopeName(text='East passage'), LiteralScopeName(text='Equipment')),
        ('direct_parent', 'any_ancestor')),
    ('“Equipment inside” directly under “Mill / Atrium”', 'natural_path',
        (LiteralScopeName(text='Mill / Atrium'), LiteralScopeName(text='Equipment inside')),
        ('direct_parent',)),
    ('Equipment whose parent is the section with the same name as this page', 'natural_path',
        (DocumentTitleScopeName(), LiteralScopeName(text='Equipment')), ('direct_parent',)),
    ('the section with the same title as this page', 'document_title', (DocumentTitleScopeName(),), ()),
    ('the section about fired ceramics', 'description', (DescribedScopeName(text='fired ceramics'),), ()),
])
def test_author_scope_hypothesis_rebuilds_complete_typed_path(phrase, grammar, names, edges):
    request = f'Use {phrase}.'
    candidate = AuthorScopeHypothesis(evidence=author_quote(request, phrase), grammar=grammar)
    assert candidate.compile(request, ()) == NamedScopePath(names=names, edges=edges)


@pytest.mark.parametrize('phrase,grammar,error', [
    ('the section with the same title as this page', 'literal_name', 'Typed reference'),
    ('the section about fired ceramics', 'literal_name', 'Typed reference'),
    ('Equipment', 'description', 'describe an existing section'),
    ('Equipment', 'document_title', 'current page title'),
    ('Mill / Equipment', 'literal_name', 'path structure'),
    ('Mill', 'literal_path', 'path separator'),
    ('Equipment directly under Mill', 'literal_name', 'path structure'),
    ('Equipment and Depot', 'literal_path', 'compound or excluded'),
    ('second Equipment', 'literal_name', 'ordinal scope'),
    ('Mill / second Equipment', 'literal_path', 'ordinal scope'),
    ('ceramic-weights paragraph in Atrium / East passage / Depot',
        'literal_path', 'separate location clause'),
])
def test_author_scope_hypothesis_refuses_incomplete_or_substituted_grammar(phrase, grammar, error):
    request = f'Use {phrase}.'
    candidate = AuthorScopeHypothesis(evidence=author_quote(request, phrase), grammar=grammar)
    with pytest.raises(ValueError, match=error):
        candidate.compile(request, ())


@pytest.mark.parametrize('utterance, fragment, grammar, error', [
    ('Use Mill / Equipment.', 'Equipment', 'literal_name', 'slash-connected'),
    ('Use Mill / Equipment.', 'Mill', 'literal_name', 'slash-connected'),
    ('Use “Mill”/ “Equipment”.', '“Equipment”', 'literal_name', 'slash-connected'),
    ('Use Mill / Equipment / Depot.', 'Equipment / Depot', 'literal_path', 'slash-connected'),
    ('Use Equipment section directly under Mill.', 'Equipment', 'literal_name', 'natural path operand'),
    ('Use Equipment whose parent is Mill.', 'Mill', 'literal_name', 'natural path operand'),
    ('Use Equipment, rather than Depot.', 'Equipment', 'literal_name', 'exclusion operand'),
    ('Use Equipment except Depot.', 'Depot', 'literal_name', 'exclusion operand'),
    ('Use Equipment except Depot.', 'Equipment except Depot.', 'exclusion', 'closing punctuation'),
])
def test_author_scope_hypothesis_cannot_start_or_end_inside_a_path(utterance, fragment, grammar, error):
    candidate = AuthorScopeHypothesis(evidence=author_quote(utterance, fragment), grammar=grammar)
    with pytest.raises(ValueError, match=error):
        candidate.compile(utterance, ())


def test_scope_hypotheses_offer_exact_names_from_author_turns_without_section_source():
    request = 'Add a warning after the paragraph in Mill / Equipment.'
    dialogue = (RetrievalDialogue(role='assistant', content='Use paragraph in Greenhouse / Equipment.'),)
    offers = author_scope_hypotheses(request, dialogue, max_span_attempts=100)
    assert offers == author_scope_hypotheses(request, dialogue, max_span_attempts=100)
    assert 'Mill / Equipment' in {v.evidence.text for v in offers.values()}
    assert not any(v.evidence.text in {'Mill', 'Equipment'} or 'Greenhouse' in v.evidence.text
        for v in offers.values())
    assert all(v.evidence.utterance_index == len(dialogue) for v in offers.values())


def test_named_paragraph_locator_keeps_the_complete_label_and_quoted_article():
    request = 'After the North Arrival paragraph about the latch, add a warning.'
    offers = author_scope_hypotheses(request, (), max_span_attempts=100)
    ending_at_label = {v.evidence.text for v in offers.values()
        if v.evidence.end == request.index(' paragraph')}
    assert ending_at_label == {'North Arrival'}

    request = 'After the “The Arrival” paragraph about the latch, add a warning.'
    offers = author_scope_hypotheses(request, (), max_span_attempts=100)
    assert any(v.evidence.text == '“The Arrival”'
        and v.compile(request, ()) == literal_reference('The Arrival', path=False) for v in offers.values())


def test_describing_is_an_explicit_paragraph_locator():
    from application_state.agent_conversation.plan_author_location import explicit_paragraph_locator

    request = 'Put a caution before the Courtyard paragraph describing the bell.'
    offers = author_scope_hypotheses(request, (), max_span_attempts=100)
    assert explicit_paragraph_locator(request, 'before_paragraph') == 'the bell'
    assert {row.evidence.text for row in offers.values() if row.evidence.end == request.index(' paragraph')} == {
        'Courtyard'}


def test_quoted_paragraph_locator_preserves_exact_case_punctuation_and_line_breaks():
    from application_state.agent_conversation.plan_author_location import (
        contains_exact_paragraph_excerpt, quoted_paragraph_locator,
    )

    quote = 'Open the vent.\nWait for the green signal.'
    request = f'After the paragraph containing “{quote}”, add a note saying “Check the gate”.'
    assert quoted_paragraph_locator(request, 'after_paragraph') == (quote, True)
    assert quoted_paragraph_locator(request, 'before_paragraph') is None
    assert quoted_paragraph_locator('Add the phrase “before the paragraph that says Open the vent”.',
        'before_paragraph') is None
    assert quoted_paragraph_locator('Add a note after the paragraph containing “rope” and ending with “frayed”.',
        'after_paragraph') == ('rope', False)
    assert quoted_paragraph_locator('Add a note after the paragraph containing “rope” but not “hook”.',
        'after_paragraph') == ('rope', False)
    assert contains_exact_paragraph_excerpt(f'Instructions: {quote} Then record the time.', quote)
    assert not contains_exact_paragraph_excerpt(quote.replace('\n', ' '), quote)
    assert not contains_exact_paragraph_excerpt('The Dial is ready.', 'dial')
    assert not contains_exact_paragraph_excerpt('catalogue cards', 'cat')
    assert not contains_exact_paragraph_excerpt('Open the vent?', 'Open the vent.')


def test_nominal_label_prefix_is_only_an_alternative_when_both_titles_exist():
    from application_state.agent_conversation.plan_author_location import (
        nominal_scope_needs_review, nominal_scope_subject, paragraph_label_conflict,
    )

    request = 'After the Approach rope paragraph, add a caution about the hook.'
    offers = author_scope_hypotheses(request, (), max_span_attempts=100)
    assert {'Approach', 'Approach rope'} <= {row.evidence.text for row in offers.values()}
    prefix = next(row for row in offers.values() if row.evidence.text == 'Approach')
    assert nominal_scope_subject(prefix, request, ()) == 'rope'
    scope = literal_reference('Approach', path=False)
    assert nominal_scope_needs_review(request, literal_reference('Approach rope', path=False))
    assert not nominal_scope_needs_review(request, scope)
    one, one_catalog = family_catalog([heading('Approach'), prose('Check the rope.')])
    assert not paragraph_label_conflict(request, scope, one, one_catalog)
    both, both_catalog = family_catalog([heading('Approach'), prose('Check the rope.'),
        heading('Approach Rope'), prose('Check the rope.')])
    assert paragraph_label_conflict(request, scope, both, both_catalog)
    assert paragraph_label_conflict(request, literal_reference('Approach Rope', path=False), both, both_catalog)


def test_explicit_current_scope_and_durable_antecedent_have_distinct_authority():
    from application_state.agent_conversation.plan_author_location import explicit_scope_conflict

    current = 'Use Approach for this edit: add a note after the ferry rope paragraph.'
    dialogue = (RetrievalDialogue(role='user', content='For the next edit, Equipment is the section I mean.'),
        RetrievalDialogue(role='assistant', content='We are in Stores.'))
    candidates = author_scope_hypotheses(current, dialogue, max_span_attempts=300)
    assert any(item.evidence.text == 'Approach' and item.evidence.utterance_index == 2 for item in candidates.values())
    assert explicit_scope_conflict(current, literal_reference('Equipment', path=False))
    assert not explicit_scope_conflict(current, literal_reference('Approach', path=False))
    reference = 'In that section, add a caution after the paragraph about securing the wheels.'
    candidates = author_scope_hypotheses(reference, dialogue, max_span_attempts=300)
    assert any(item.evidence.text == 'Equipment' and item.evidence.utterance_index == 0 for item in candidates.values())
    assert not any(item.evidence.text in {'that', 'that section', 'Stores'} for item in candidates.values())
    for mention in ('Do not use Stores for this edit: add a note after the first paragraph.',
                    'The earlier note says to use Stores for this edit, not Approach.'):
        assert not explicit_scope_conflict(mention, UnscopedLocation())


def test_unquoted_locator_label_cannot_be_dropped_or_pick_between_article_titles():
    from application_state.agent_conversation.plan_author_location import paragraph_label_conflict

    request = 'Add a warning before the Arrival paragraph about the latch.'
    scope = literal_reference('Arrival', path=False)
    capture, catalog = family_catalog([heading('Arrival'), prose('Check the latch.')])
    assert not paragraph_label_conflict(request, scope, capture, catalog)
    assert paragraph_label_conflict(request, UnscopedLocation(), capture, catalog)
    capture, catalog = family_catalog([heading('Arrival'), prose('Check the latch.'),
        heading('The Arrival'), prose('Check the latch.')])
    assert paragraph_label_conflict(request, scope, capture, catalog)
    assert not paragraph_label_conflict(
        'Add a warning before the “The Arrival” paragraph about the latch.',
        literal_reference('The Arrival', path=False), capture, catalog)


def test_scope_hypotheses_preserve_typed_references_and_refuse_budget_truncation():
    request = 'Use the paragraph in the section with the same title as this page.'
    offers = author_scope_hypotheses(request, (), max_span_attempts=100)
    assert any(v.compile(request, ()).names == (DocumentTitleScopeName(),) for v in offers.values())
    with pytest.raises(ValueError, match='configured span budget'):
        author_scope_hypotheses(request, (), max_span_attempts=1)


def test_scope_hypotheses_offer_complete_natural_path_after_an_article():
    request = 'Add a note after the paragraph in the Equipment section directly under Mill.'
    offers = author_scope_hypotheses(request, (), max_span_attempts=100)
    assert any(h.compile(request, ()) == literal_reference('Mill / Equipment', path=True)
        for h in offers.values())


def test_descendant_qualifier_is_not_in_the_offered_literal_heading():
    request = 'Add a reminder before the loose-papers paragraph within Public Wing, including its subsections.'
    offers = author_scope_hypotheses(request, (), max_span_attempts=200)
    assert any(h.evidence.text == 'Public Wing' for h in offers.values())
    assert not any('including its subsections' in h.evidence.text for h in offers.values())
    quoted = 'Add a reminder within “Public Wing, including its subsections”.'
    offers = author_scope_hypotheses(quoted, (), max_span_attempts=100)
    assert any(h.compile(quoted, ()) == literal_reference('Public Wing, including its subsections', path=False)
        for h in offers.values())


@pytest.mark.parametrize('positive,excluded', [
    ('Lower Trail', 'Upper Trail'),
    ('“Lower Trail”', '“Upper Trail, ridge”'),
])
@pytest.mark.parametrize('qualifier', ['', ' for this change'])
def test_explicit_scope_contrast_retains_both_durable_names(positive, excluded, qualifier):
    from application_state.agent_conversation.plan_author_location import explicit_contrast_conflict

    directive = f'Use {positive}{qualifier}, not {excluded}'
    request = f'{directive}: immediately after the loose-ledge paragraph, insert a warning.'
    offers = author_scope_hypotheses(request, (), max_span_attempts=200)
    preserved = next(h for h in offers.values() if h.evidence.text == directive)
    scope = ScopeWithExclusion(
        positive=literal_reference(positive, path=False), excluded=literal_reference(excluded, path=False))
    assert preserved.compile(request, ()) == scope
    assert not explicit_contrast_conflict(request, scope)
    assert explicit_contrast_conflict(request, UnscopedLocation())
    with pytest.raises(ValueError, match='both parts'):
        AuthorScopeHypothesis(evidence=author_quote(request, positive), grammar='literal_name').compile(request, ())


def test_direction_adjudication_preserves_unresolved_alternatives():
    from application_state.agent_conversation.native_plan_opening import (
        NativePlanAuthorScopeObservationV1, author_scope_review_required,
    )
    from application_state.agent_conversation.plan_author_location import explicit_direction_options

    first = NativePlanAuthorScopeObservationV1(
        relation='unresolved', selected_alias='scope0', scope=literal_reference('Evening', path=False))
    request = 'In Evening, add a checklist just before the porter seals the blue crate.'
    assert explicit_direction_options(request) == ('before_paragraph', 'before_heading')
    assert author_scope_review_required(request, first, first)
    assert not author_scope_review_required('Put it both immediately before and after the crate paragraph.', first, first)
    assert not explicit_direction_options('Do the porters arrive right after sunset?')
    assert not explicit_direction_options('Add the words “right after sunset” to the warning.')
    assert not explicit_direction_options('Add the words “after the paragraph” to the warning.',
        allow_plain_prose=True)
    assert not explicit_direction_options('Add the warning before the note or after the passage.',
        allow_plain_prose=True)
    request = 'After the existing instruction about latching the upper hatch, add a reminder.'
    assert not explicit_direction_options(request)
    assert explicit_direction_options(request, allow_plain_prose=True) == ('after_paragraph',)
    edit = first.model_copy(update={'page_edit_intent': 'page_edit'})
    discussion = first.model_copy(update={'page_edit_intent': 'discussion'})
    assert author_scope_review_required(request, edit, edit)
    assert not author_scope_review_required(request, edit, discussion)
    assert explicit_direction_options('Put a note right after the Arrival heading.') == (
        'after_paragraph', 'after_heading', 'after_section')


def test_unresolved_scope_adjudication_offers_whole_author_clauses_without_unscoped_fallback():
    import json
    from uuid import uuid4
    from application_state.agent_conversation.native_plan_opening import (
        NativePlanAuthorScopeObservationV1, NativePlanAuthorScopeParentV1, NativePlanOpeningScopeBindingV1,
        author_scope_review_required, prepare_author_scope_decision,
    )

    unresolved = NativePlanAuthorScopeObservationV1(relation='after_paragraph', selected_alias='unresolved',
        scope=UnresolvedLocation(reason='No complete scope was initially selected'))
    scope_review = tuple(NativePlanOpeningScopeBindingV1(observation_event_id=uuid4(), observation=unresolved)
        for _ in range(2))

    def scopes(question):
        parent = NativePlanAuthorScopeParentV1(question=question, dialogue=(), max_span_attempts=100,
            quote_context=True, request_id=uuid4(), parent_attempt_id=uuid4(),
            scope_sha256='0' * 64, request_manifest_sha256='0' * 64, scope_review=scope_review)
        assert author_scope_review_required(question, unresolved, unresolved)
        criteria = prepare_author_scope_decision(parent).questions[0].option_descriptions
        return [json.loads(value)['scope'] for name, value in criteria.items() if name != 'unresolved']

    supported = scopes('Put a warning after the token paragraph in West / Equipment.')
    assert any(scope.get('components') == [{'kind': 'literal_name', 'text': 'West'},
        {'kind': 'literal_name', 'text': 'Equipment'}] for scope in supported)
    assert all(scope.get('kind') != 'unscoped' for scope in supported)
    compound = scopes('Put a warning after the token paragraph in West or in East.')
    assert all('components' not in scope for scope in compound)
    unmarked_contrast = scopes('Put a warning after the token paragraph in Records, not Dispatch.')
    assert all('components' not in scope for scope in unmarked_contrast)
    continuation = scopes('Put a warning after the token paragraph in North, inside Equipment.')
    assert all(len(scope.get('components', ())) != 1 for scope in continuation)


def test_scope_offer_view_has_local_aliases_and_author_text_without_host_offsets():
    request = 'Use the paragraph in Mill / Equipment.'
    options = author_scope_hypotheses(request, (), max_span_attempts=100)
    view = author_scope_offer_view(request, (), options, include_quote_context=True)
    assert set(view['scope_hypotheses']) == set(options)
    offer = next(row for row in view['scope_hypotheses'].values()
        if row['author_quote']['text'] == 'Mill / Equipment')
    assert offer['author_quote'] == {'utterance': 'utterance0', 'text': 'Mill / Equipment',
        'text_before': 'Use the paragraph in ', 'text_after': '.'}
    assert json.loads(json.dumps(view)) == view


def test_scope_hypothesis_retains_both_operands_of_a_restated_exclusion():
    phrase = 'Conservatory / Supplies, the Supplies section directly under Conservatory rather than the one inside Loft'
    request = f'Add a warning after the paragraph in {phrase}.'
    offers = author_scope_hypotheses(request, (), max_span_attempts=300)
    chosen = next(h for h in offers.values() if h.evidence.text == phrase)
    compiled = chosen.compile(request, ())
    assert compiled == ScopeWithExclusion(
        positive=literal_reference('Conservatory / Supplies', path=True),
        excluded=NamedScopePath(names=(LiteralScopeName(text='Loft'), LiteralScopeName(text='Supplies')),
            edges=('any_ancestor',)),
    )
    assert not any(h.evidence.text == 'Conservatory / Supplies' for h in offers.values())
    view = author_scope_offer_view(request, (), offers)
    visible = next(v for v in view['scope_hypotheses'].values() if v['author_quote']['text'] == phrase)
    assert visible['excluded_path'] == {'components': [
        {'kind': 'literal_name', 'text': 'Loft'}, {'kind': 'literal_name', 'text': 'Supplies'}],
        'edges': ['any_ancestor']}


def test_compiled_scope_exclusion_removes_only_the_exact_matching_occurrence():
    nodes = [heading('Conservatory', 1), heading('Supplies'), prose('Shared.'),
        heading('Loft', 1), heading('Supplies'), prose('Shared.')]
    request = 'Use Supplies rather than the one inside Loft.'
    phrase = 'Supplies rather than the one inside Loft'
    hypothesis = AuthorScopeHypothesis(evidence=author_quote(request, phrase), grammar='exclusion')
    result = bind(nodes, hypothesis.compile(request, ()))
    assert result.heading_indices == (1,)
    assert len(result.paragraph_anchors) == 1


def test_scope_exclusion_requires_frozen_title_for_symbolic_excluded_operand():
    nodes = [heading('Supplies'), prose('Shared.')]
    scope = ScopeWithExclusion(positive=literal_reference('Supplies', path=False),
        excluded=NamedScopePath(names=(DocumentTitleScopeName(),)))
    assert bind(nodes, scope).status == 'unsupported'
    assert bind(nodes, scope, document_title='Supplies').status == 'missing'
    assert bind(nodes, scope, document_title='Notes').status == 'matched'


def test_scope_exclusion_removes_descendant_heading_and_paragraph_addresses_together():
    nodes = [heading('North', 1), heading('Equipment'), prose('First.'),
        heading('South', 1), heading('Equipment'), prose('Second.')]
    positive = literal_reference('Equipment', path=False)
    scope = ScopeWithExclusion(positive=positive, excluded=literal_reference('North', path=False))
    result = bind(nodes, scope)
    assert result.heading_indices == (4,)
    assert len(result.paragraph_anchors) == 1
    assert bind(nodes[:3], scope).status == 'missing'


def test_scope_exclusion_rejects_restatement_that_changes_the_path():
    phrase = 'Atrium / Supplies, the Supplies section directly under Loft rather than Depot'
    hypothesis = AuthorScopeHypothesis(evidence=author_quote(phrase, phrase), grammar='exclusion')
    with pytest.raises(ValueError, match='restated path'):
        hypothesis.compile(phrase, ())


def test_source_blind_author_scope_round_trips_through_sdk_and_reconstructs_offered_quote():
    parent = NativePlanAuthorScopeInputV1(question='Add a note after the heading in Mill / Equipment.',
        dialogue=(), max_span_attempts=100, quote_context=True)
    decision = prepare_author_scope_decision(parent)
    alias = next(key for key, offer in decision.state['scope_hypotheses'].items()
        if offer['author_quote']['text'] == 'Mill / Equipment')
    prepared_payloads = []

    async def authorize(prepared):
        validate_author_scope_wire(parent, prepared.body)
        prepared_payloads.append(prepared.body)
        return True

    async def record(_):
        return True

    async def respond(request):
        assert request.content == prepared_payloads[0]
        body = json.loads(request.content)
        assert set(body['state']) == {'current_request', 'dialogue', 'scope_hypotheses'}
        selections = {'location_relation': 'after_heading', 'existing_scope': alias}
        answers = {name: {'type': 'choice', 'choice': selection, 'confidence': 1.0,
            'probabilities': {key: float(key == selection) for key in body['questions'][name]['criteria']}}
            for name, selection in selections.items()}
        return httpx2.Response(200, request=request,
            json={'model': decision.model, 'answers': answers, 'usage': {'input_tokens': 40, 'output_tokens': 8}})

    async def run():
        client = decision_client(authorize=authorize, record=record,
            transport=httpx2.MockTransport(respond), api_key='synthetic-not-secret')
        try:
            return await client.decide(decision)
        finally:
            await client.aclose()

    result = asyncio.run(run())
    observation = decode_author_scope_decision(parent, result)
    assert observation.relation == 'after_heading'
    assert observation.scope == literal_reference('Mill / Equipment', path=True)
    modified = json.loads(prepared_payloads[0])
    modified['state']['scope_hypotheses'][alias]['components'].pop(0)
    with pytest.raises(ValueError, match='reconstructed local choices'):
        validate_author_scope_wire(parent, json.dumps(modified).encode())
    foreign = result.answers['existing_scope'].model_copy(update={'selected': 'scope999'})
    with pytest.raises(ValueError, match='unoffered hypothesis'):
        decode_author_scope_decision(parent,
            result.model_copy(update={'answers': {**result.answers, 'existing_scope': foreign}}))


def test_selection_reference_guidance_keeps_historical_source_blind_wire():
    historical = NativePlanAuthorScopeInputV1(
        question='Rewrite this to emphasize the three lanterns.',
        dialogue=(), max_span_attempts=100, quote_context=False, assess_page_edit=True,
    )
    current = historical.model_copy(update={'selection_reference_version': 'v1'})

    def wire(parent):
        decision = prepare_author_scope_decision(parent)
        questions = {question.name: {
            'type': 'choice',
            'instructions': question.question,
            'criteria': question.option_descriptions,
        } for question in decision.questions}
        return json.dumps({
            'model': decision.model, 'state': decision.state, 'questions': questions,
        }).encode()

    old_wire, new_wire = wire(historical), wire(current)
    validate_author_scope_wire(historical, old_wire)
    validate_author_scope_wire(current, new_wire)
    with pytest.raises(ValueError, match='reconstructed local choices'):
        validate_author_scope_wire(historical, new_wire)

    old_body, new_body = json.loads(old_wire), json.loads(new_wire)
    assert old_body['state'] == new_body['state']
    assert 'selection_reference_version' not in historical.model_dump()
    assert new_body['questions']['location_relation']['criteria'] == old_body['questions']['location_relation']['criteria']
    guidance = new_body['questions']['location_relation']['instructions']
    assert 'without saying “selected text.”' in guidance
    assert 'the request points to another location' in guidance


@pytest.mark.parametrize("selected,expected,phrase", [
    (True, "text_selection", "selected existing text"),
    (False, "caret", "unstated insertion location"),
])
def test_author_editor_focus_projects_only_a_semantic_fact(selected, expected, phrase):
    from types import SimpleNamespace

    capture, catalog = captured_catalog(selected=selected)
    action = SimpleNamespace(authoring_capture=capture, placement_catalog=catalog)
    assert author_editor_focus(action) == expected
    parent = NativePlanAuthorScopeInputV1(
        question="Make a change to this.", dialogue=(), max_span_attempts=100,
        quote_context=False, assess_page_edit=True, implicit_caret_version="v1",
    )
    legacy = prepare_author_scope_decision(parent)
    current = prepare_author_scope_decision(parent.model_copy(update={"editor_focus": expected}))
    assert set(current.state) == set(legacy.state) | {"current_editor_focus"}
    assert phrase in current.state["current_editor_focus"]
    state = json.dumps(current.state)
    assert capture.document_id not in state
    if selected:
        assert capture.selected_text not in state
    assert author_editor_focus(SimpleNamespace(authoring_capture=None, placement_catalog=None)) is None


@pytest.mark.parametrize("quoted", [False, True])
def test_explicit_plan_location_keeps_its_existing_provider_wire(quoted):
    parent = NativePlanAuthorScopeInputV1(
        question="Add a Read Aloud immediately after the first paragraph in Arrival.",
        dialogue=(), max_span_attempts=100, quote_context=quoted, assess_page_edit=True,
        implicit_caret_version="v1", selection_reference_version="v1",
    )
    named = prepare_author_scope_decision(parent)
    with_caret = prepare_author_scope_decision(parent.model_copy(update={"editor_focus": "caret"}))
    assert named == with_caret


def bind(nodes, scope, **kwargs):
    capture, catalog = family_catalog(nodes)
    original = capture.editor_json
    result = bind_scope(capture, catalog, scope, document_title=kwargs.pop('document_title', None), **kwargs)
    assert capture.editor_json == original
    return result


def test_missing_literal_parent_cannot_be_replaced_by_document_title_or_existing_parent():
    nodes = [heading('Greenhouse', 1), heading('Equipment'), prose('Return the misting wand.')]
    result = bind(nodes, literal_reference('Mill / Equipment', path=True), document_title='Greenhouse')
    assert result.status == 'missing' and result.heading_indices == result.paragraph_anchors == ()
    # This remains a refusal with only ONE viable paragraph. Ambiguity cannot
    # accidentally mask erasure of the missing parent.
    partial = bind(nodes, literal_reference('Mill / Greenhouse / Equipment', path=True),
        document_title='Greenhouse')
    assert partial.status == 'missing' and partial.paragraph_anchors == ()


def test_primary_title_expands_every_parent_and_repeated_complete_path():
    nodes = [heading('North', 1), heading('Supplies'), prose('Shared.'),
        heading('South', 1), heading('Supplies'), prose('Shared.'), heading('Supplies'), prose('Shared.')]
    all_matches = bind(nodes, literal_reference('Supplies', path=False))
    assert all_matches.heading_indices == (1, 4, 6)
    assert len(all_matches.paragraph_anchors) == 3
    north = bind(nodes, literal_reference('North / Supplies', path=True))
    assert north.heading_indices == (1,) and len(north.paragraph_anchors) == 1
    south = bind(nodes, literal_reference('South / Supplies', path=True))
    assert south.heading_indices == (4, 6) and len(south.paragraph_anchors) == 2


def test_join_uses_primary_heading_occurrence_before_expanding_ranges():
    trap = [heading('Archive', 1), heading('Other'), prose('Shared.')]
    assert bind(trap, literal_reference('Archive / Archive', path=True)).status == 'missing'
    repeated = [heading('Archive', 1), heading('Archive'), prose('Shared.')]
    actual = bind(repeated, literal_reference('Archive / Archive', path=True))
    assert actual.heading_indices == (1,) and len(actual.paragraph_anchors) == 1


def test_ancestor_scope_includes_descendants_but_named_child_cannot_fall_back():
    nodes = [heading('Workshop', 1), heading('North'), prose('Shared.'), heading('South'), prose('Shared.')]
    parent = bind(nodes, literal_reference('Workshop', path=False))
    assert parent.heading_indices == (0,) and len(parent.paragraph_anchors) == 2
    missing_child = bind(nodes, literal_reference('Workshop / Missing', path=True))
    assert missing_child.status == 'missing' and missing_child.paragraph_anchors == ()


def test_direct_parent_and_ordered_ancestor_are_distinct_source_constraints():
    nodes = [heading('Conservatory', 1), heading('Supplies'), prose('Shared.'),
        heading('Loft'), heading('Supplies', 3), prose('Shared.')]
    direct = bind(nodes, literal_reference('Conservatory / Supplies', path=True))
    assert direct.heading_indices == (1,)
    ancestor = bind(nodes, NamedScopePath(names=(LiteralScopeName(text='Conservatory'),
        LiteralScopeName(text='Supplies')), edges=('any_ancestor',)))
    assert ancestor.heading_indices == (1, 4)
    # Root binding is explicit, not inferred by dropping a source prefix.
    nested = [heading('Outer', 1), heading('Conservatory', 2), heading('Supplies', 3), prose('Shared.')]
    assert bind(nested, literal_reference('Conservatory / Supplies', path=True)).status == 'matched'
    assert bind(nested, literal_reference('Conservatory / Supplies', path=True, rooted=True)).status == 'missing'


def test_symbolic_document_title_is_typed_and_has_no_h1_fallback():
    nodes = [heading('Harbor watch', 1), prose('Shared.'),
        heading('document_title', 1), prose('Shared.')]
    symbolic = NamedScopePath(names=(DocumentTitleScopeName(),))
    assert bind(nodes, symbolic, document_title='Harbor watch').heading_indices == (0,)
    assert bind(nodes, symbolic).status == 'missing'
    literal = literal_reference('document_title', path=False)
    assert bind(nodes, literal, document_title='Harbor watch').heading_indices == (2,)
    # A changed binding would select another occurrence, so native admission
    # must retain and compare the original frozen Content title, not reread it.
    assert bind(nodes, symbolic, document_title='document_title').heading_indices == (2,)


def test_symbolic_parent_and_literal_child_bind_to_the_same_source_occurrence():
    nodes = [heading('Harbor watch', 1), heading('Records'), prose('Shared.'),
        heading('Night patrol', 1), heading('Records'), prose('Shared.')]
    scope = NamedScopePath(names=(DocumentTitleScopeName(), LiteralScopeName(text='Records')),
        edges=('direct_parent',))
    assert bind(nodes, scope, document_title='Harbor watch').heading_indices == (1,)
    assert bind(nodes, scope, document_title='Absent').status == 'missing'


def test_normalized_name_collisions_expand_all_exact_source_occurrences():
    nodes = [heading('CAFÉ  NORD', 1), prose('Shared.'),
        heading('cafe\u0301 nord', 1), prose('Shared.'), heading('Café Nord', 1), prose('Shared.')]
    result = bind(nodes, literal_reference('café nord', path=False))
    assert result.heading_indices == (0, 2, 4) and len(result.paragraph_anchors) == 3
    capture, catalog = family_catalog(nodes)
    inventory = source_heading_inventory(capture, catalog)
    assert len(inventory['titles']) == 3  # No normalization of source families/bytes.


def test_literal_slash_title_and_structured_path_are_distinct():
    nodes = [heading('North / South', 1), prose('Shared.'),
        heading('North', 1), heading('South'), prose('Shared.')]
    label = literal_reference('“North / South”', path=False)
    path = literal_reference('North / South', path=True)
    assert bind(nodes, label).heading_indices == (0,)
    assert bind(nodes, path).heading_indices == (3,)
    with pytest.raises(ValueError, match='unquoted slash'):
        literal_reference('North / South', path=False)
    assert literal_reference('North / South', path=False, quoted=True) == label


def test_quotes_in_source_titles_are_data_not_author_quote_syntax():
    nodes = [heading('North', 1), prose('Shared.'), heading('"North"', 1), prose('Shared.')]
    assert bind(nodes, literal_reference('"North"', path=False)).heading_indices == (0,)
    assert bind(nodes, literal_reference('`"North"`', path=False)).heading_indices == (2,)
    quoted_parts = literal_reference('"North" / "South"', path=True)
    assert [component.text for component in quoted_parts.names] == ['North', 'South']
    escaped = literal_reference('"North\\" gate" / South', path=True)
    assert escaped.names[0].text == 'North" gate'


@pytest.mark.parametrize('text', ['North /', '/ South', 'North // South', 'North / "South',
    'A / B / C / D / E / F / G', '"North"extra / South', 'North / "South"extra',
    '"North / South"'])
def test_malformed_or_overflow_paths_cannot_truncate_to_available_names(text):
    with pytest.raises(ValueError):
        literal_reference(text, path=True)


def test_description_matches_cannot_override_a_literal_name_or_missing_component():
    nodes = [heading('Greenhouse', 1), heading('Equipment'), prose('Shared.')]
    capture, catalog = family_catalog(nodes)
    scope = literal_reference('Mill / Equipment', path=True)
    with pytest.raises(ValueError, match='declared description'):
        bind_scope(capture, catalog, scope, document_title='Greenhouse', description_matches={0: ('heading0',)})
    described = NamedScopePath(names=(DescribedScopeName(text='the equipment area'),))
    with pytest.raises(ValueError, match='declared description'):
        bind_scope(capture, catalog, described, document_title=None)
    assert bind_scope(capture, catalog, described, document_title=None,
        description_matches={0: ('heading1',)}).heading_indices == (1,)
    assert bind_scope(capture, catalog, described, document_title=None,
        description_matches={0: ()}).status == 'missing'
    for matches in [('foreign',), ('title1',), ('heading1', 'heading1')]:
        with pytest.raises(ValueError, match='Foreign or duplicate'):
            bind_scope(capture, catalog, described, document_title=None, description_matches={0: matches})


def test_description_binds_the_nominated_ancestor_occurrence_and_exclusion():
    nodes = [heading('West', 1), heading('Workshop', 2), prose('Clay is fired.'),
        heading('Notes', 3), prose('Shared.'),
        heading('East', 1), heading('Workshop', 2), prose('Wood is sawn.'),
        heading('Notes', 3), prose('Shared.')]
    capture, catalog = family_catalog(nodes)
    ceramics = DescribedScopeName(text='the workshop for fired ceramics')
    notes = LiteralScopeName(text='Notes')
    scope = NamedScopePath(names=(ceramics, notes), edges=('direct_parent',))
    assert bind_scope(capture, catalog, scope, document_title=None,
        description_matches={0: ('heading1',)}).heading_indices == (3,)
    assert bind_scope(capture, catalog, scope, document_title=None,
        description_matches={0: ('heading1', 'heading4')}).heading_indices == (3, 8)

    east = NamedScopePath(names=(LiteralScopeName(text='East'), ceramics, notes),
        edges=('direct_parent', 'direct_parent'))
    assert bind_scope(capture, catalog, east, document_title=None,
        description_matches={1: ('heading1',)}).status == 'missing'

    excluded = ScopeWithExclusion(positive=NamedScopePath(names=(notes,)),
        excluded=NamedScopePath(names=(ceramics,)))
    assert bind_scope(capture, catalog, excluded, document_title=None,
        excluded_description_matches={0: ('heading1',)}).heading_indices == (8,)
    assert bind_scope(capture, catalog, excluded, document_title=None,
        excluded_description_matches={0: ()}).status == 'unsupported'


def test_ordinal_never_enables_paragraph_scope_and_only_explicitly_selects_heading():
    nodes = [heading('Preparation'), prose('First.'), heading('Preparation'), prose('Second.')]
    scope = NamedScopePath(names=(LiteralScopeName(text='Preparation'),), occurrence=2)
    assert bind(nodes, scope).status == 'unsupported'
    assert bind(nodes, scope, allow_ordinal=True).heading_indices == (2,)
    absent = scope.model_copy(update={'occurrence': 3})
    assert bind(nodes, absent, allow_ordinal=True).status == 'missing'


def test_unscoped_and_unresolved_have_different_authority_and_no_named_root_fallback():
    nodes = [prose('Root.'), heading('Later'), prose('Body.')]
    assert len(bind(nodes, UnscopedLocation()).paragraph_anchors) == 2
    rejected = bind(nodes, UnresolvedLocation(reason='independent section constraints'))
    assert rejected.status == 'unsupported' and rejected.paragraph_anchors == ()
    missing = bind(nodes, literal_reference('Absent', path=False))
    assert missing.status == 'missing' and missing.paragraph_anchors == ()


def test_name_binding_never_invents_a_table_caption_section():
    table = dict(type='table', content=[dict(type='tableRow', content=[dict(type='tableCell',
        attrs=dict(colspan=1, rowspan=1), content=[prose('Loot.')])])])
    nodes = [heading('Treasure'), table, prose('Shared.')]
    assert bind(nodes, literal_reference('Treasure', path=False)).status == 'missing'


def test_typed_paths_require_every_relationship_and_roundtrip_without_source_changes():
    path = literal_reference('North / Supplies', path=True)
    assert NamedScopePath.model_validate(json.loads(path.model_dump_json())) == path
    with pytest.raises(ValueError, match='Every adjacent'):
        NamedScopePath(names=(LiteralScopeName(text='North'), LiteralScopeName(text='Supplies')))
    with pytest.raises(ValueError):
        LiteralScopeName(text=' ')


@pytest.mark.parametrize('changed', ['work_object_id', 'world_id', 'status',
    'object_revision', 'current_revision_id'])
def test_title_metadata_rejects_a_different_or_changed_content_basis(monkeypatch, changed):
    from types import SimpleNamespace
    from application_state.errors import ApplicationStateConflictError
    from apps.live_control_server.services.plan_source_turn import _contextual_document_title
    basis = SimpleNamespace(document_id='doc', world_id='world', object_revision=3,
        work_revision_id='revision')
    values = dict(work_object_id='doc', world_id='world', status='active',
        object_revision=3, current_revision_id='revision', title='Actual Content title')
    monkeypatch.setattr('application_state.content.service.get_plan', lambda _: SimpleNamespace(**values))
    assert _contextual_document_title(basis) == 'Actual Content title'
    values[changed] = 4 if changed == 'object_revision' else 'different'
    with pytest.raises(ApplicationStateConflictError, match='metadata changed'):
        _contextual_document_title(basis)


def test_actual_content_metadata_title_rename_invalidates_old_basis(application_state_dsn):
    from types import SimpleNamespace
    from application_state.content.service import create_world_plan, commit_plan, update_plan_metadata
    from application_state.errors import ApplicationStateConflictError
    from apps.live_control_server.services.plan_source_turn import _contextual_document_title
    obj = create_world_plan(title='Harbor watch', world_id='world:title-binding')
    obj, revision = commit_plan(str(obj.work_object_id), '# Different editor H1\n\nA note.\n',
        expected_world_id=obj.world_id, expected_revision=obj.object_revision)
    basis = SimpleNamespace(document_id=str(obj.work_object_id), world_id=obj.world_id,
        object_revision=obj.object_revision, work_revision_id=str(revision.work_revision_id))
    frozen = _contextual_document_title(basis)
    assert frozen == 'Harbor watch'
    renamed = update_plan_metadata(str(obj.work_object_id), title='Night patrol',
        expected_revision=obj.object_revision)
    assert renamed.current_revision_id == obj.current_revision_id
    with pytest.raises(ApplicationStateConflictError, match='metadata changed'):
        _contextual_document_title(basis)
    basis.object_revision = renamed.object_revision
    assert _contextual_document_title(basis) == 'Night patrol'
    assert frozen == 'Harbor watch'
