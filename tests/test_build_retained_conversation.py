"""The retained closure has no recent-turn cutoff or fresh source acquisition."""
from hashlib import sha256
import json
from types import SimpleNamespace as NS
from uuid import uuid4

import pytest

from application_state.agent_conversation import types as t
from application_state.agent_conversation import retained_conversation as retained


def fixture_closure(count=60):
    world, chat = 'retained-world', uuid4()
    basis = t.BuildSourceContextBasisV1(world_id=world, document_id=str(uuid4()),
        registry_revision=1, content_sha256='a' * 64, visibility='internal')
    text = 'Ashbell has three bridges; this is authored setting, not a played event.'
    turns = []
    for i in range(count):
        event = t.ValidatedBuildSectionReadV1(kind='validated_build_section_read_v1',
            event_id=uuid4(), sequence=0, read_id=uuid4(), source_basis=basis,
            source_class='saved_authored_source_not_played_truth', line_start=1, line_end=1,
            text=text, excerpt_sha256=sha256(text.encode()).hexdigest())
        turns.append(NS(world_id=world, conversation_id=chat, turn_id=uuid4(),
            sequence=i + 1, attempt=1, status='completed', user_text=f'Constraint {i}',
            assistant_text=f'Answer {i}', completion=None,
            graph_context_execution=NS(events=(event,) if i in (0, 12) else ())))
    turns[-1].user_text = 'Correction: the fare is a memory, not coins. Keep identity unresolved.'
    current = NS(world_id=world, conversation_id=chat, turn_id=uuid4(), sequence=count + 1,
        attempt=2, graph_context_execution=NS(events=()))
    return current, turns


def capture(current, turns, seed=None):
    return retained.capture(current, turns, event_id=uuid4(), work_event_id=uuid4(),
        pointer_revision=7, seed=seed)


def test_complete_history_and_deduplicated_occurrences_survive_more_than_fifty_turns():
    current, turns = fixture_closure()
    value = capture(current, turns)
    assert len(value.history) == 60
    assert len(value.authored_context) == 1
    assert len(value.authored_context[0].occurrences) == 2
    execution = NS(events=(value,))
    messages = retained.dialogue_messages(execution)
    assert len(messages) == 120
    assert json.loads(messages[0]['content'])['conversation'] == turns[0].user_text
    assert 'Correction:' in messages[-2]['content']
    frame = retained.authored_frame(execution)
    assert frame[0]['from_turns'] == ['turn0', 'turn12']
    assert frame[0]['role'] == 'saved_authored_historical_not_played_truth'
    wire = json.dumps([messages, frame])
    for host_identity in (str(current.conversation_id), str(turns[0].turn_id),
                          value.authored_context[0].source_basis.document_id, 'a' * 64):
        assert host_identity not in wire
    restored = t.BuildPriorBodyEvidenceAdmittedV2.model_validate_json(value.model_dump_json())
    assert restored == value


@pytest.mark.parametrize('mutation', ['omitted', 'changed', 'extra'])
def test_producing_request_rejects_missing_changed_and_unadmitted_dialogue(mutation):
    current, turns = fixture_closure()
    execution = NS(events=(capture(current, turns),))
    messages = retained.dialogue_messages(execution)
    retained.validate_dialogue_request(execution, {'input': messages})
    if mutation == 'omitted':
        messages = messages[2:]
    elif mutation == 'changed':
        messages[0] = dict(role='user', content='changed')
    else:
        messages.append(dict(role='user', content='{"conversation":"unadmitted"}'))
    with pytest.raises(ValueError):
        retained.validate_dialogue_request(execution, {'input': messages})


@pytest.mark.parametrize('status', ['failed', 'interrupted'])
def test_failed_turn_preserves_user_constraints_without_assistant_or_read_evidence(status):
    current, turns = fixture_closure(2)
    turns[0].status = status
    value = capture(current, turns)
    assert value.history[0].user_text == turns[0].user_text
    assert value.history[0].assistant_text is None
    assert not value.authored_context
    assert all(row['role'] != 'assistant' or 'Answer 0' not in row['content']
               for row in retained.dialogue_messages(NS(events=(value,))))


@pytest.mark.parametrize('field', ['world_id', 'conversation_id', 'turn_id', 'sequence'])
def test_foreign_or_current_turn_cannot_enter_frozen_closure(field):
    current, turns = fixture_closure(2)
    setattr(turns[0], field, getattr(current, field) if field in ('turn_id', 'sequence')
            else ('foreign' if field == 'world_id' else uuid4()))
    with pytest.raises(ValueError, match='scope'):
        capture(current, turns)


def test_historical_saved_material_keeps_its_exact_original_world_owner():
    current, turns = fixture_closure(2)
    read = turns[0].graph_context_execution.events[0]
    foreign = read.model_copy(update={'source_basis': read.source_basis.model_copy(update={'world_id':'foreign'})})
    turns[0].graph_context_execution.events = (foreign,)
    with pytest.raises(ValueError, match='World ownership'):
        capture(current, turns)


def test_legacy_admission_does_not_change_historical_dialogue_codec():
    legacy = t.BuildPriorBodyEvidenceAdmittedV1(event_id=uuid4(), sequence=0,
        work_event_id=uuid4(), supports=())
    assert retained.dialogue_messages(NS(events=(legacy,))) is None
    retained.validate_dialogue_request(NS(events=(legacy,)), {'input': 'historical'})


from tests.test_native_plan_assertions import lane as lane


@pytest.mark.parametrize('turn_count,discussion', [(8, False), (60, False), (8, True)])
def test_ordinary_http_retains_early_uncited_reads_after_sixty_turns_without_editor_or_new_search(
        lane, tmp_path, monkeypatch, turn_count, discussion):
    from tests.test_surface_native_build_ordinary import _fresh_case
    from application_state.agent_conversation.native_corpus import acquired_body_reads
    from application_state.agent_conversation.service import AgentConversationService
    from application_state.agent_conversation.native_execution import NativeBuildQuerySettledV1

    synthesis = ('Recap everything we discussed, including the earlier saved notes. Do not search again.' if discussion
                 else 'Create a new page titled "Glass Regent" from the context we discussed. Do not search again.')
    case = _fresh_case(lane, tmp_path, monkeypatch, None, False, True, False,
        native_body='irrelevant',
        requested_work=lambda message: ('discuss' if discussion else 'review_lore_page_from_conversation') if message == synthesis else 'discuss',
        source_need=lambda message: 'anchored' if message == synthesis else 'source_lookup')
    original = case.turn
    # The initial explicit source selection supplied the early read. Follow-ups
    # request reuse, not another author-selected source acquisition.
    case.request['build_authored_references'] = None
    from tests.page_fixtures import save_page
    from apps.live_control_server.services.workspace_document_registry import get_workspace_document_snapshot
    save_page(tmp_path, case.page.document_id, '# Changed revision\n\nA proposed conversation.\n\nAn added context note.\n')
    changed = get_workspace_document_snapshot(tmp_path, case.page.document_id)
    case.request['primary_work'].update(expected_revision=changed.loaded_revision,
        expected_content_sha256=changed.content_sha256)
    assert acquired_body_reads(original.graph_context_execution)
    assert not original.completion.native_body_citations
    assert any(isinstance(event, t.ValidatedBuildSectionReadV1)
               for event in original.graph_context_execution.events)
    # These are ordinary terminal turns, not synthetic database inserts or a
    # preconstructed writer request. They remain outside the final six-row view.
    for index in range(turn_count - 1):
        response = case.client.post('/api/live/agent/turn', json=case.request | {
            'turn_id': str(uuid4()), 'message': f'Author constraint {index}: retain the blue lantern as a proposal.'})
        assert response.status_code == 200, response.text
    from tests.page_fixtures import save_page
    from apps.live_control_server.services.workspace_document_registry import get_workspace_document_snapshot
    from tests.page_fixtures import create_page_fixture
    from application_state.content import pages
    replacement = create_page_fixture(tmp_path, world_id=case.world, campaign_id=case.world,
        title='Different current page', kind='worldbuilding_source', source_domain='worldbuilding',
        document_class='lore', authority_state='draft', visibility_state='internal')
    save_page(tmp_path, replacement.document_id, '# Different current page\n\nA proposed conversation.\n')
    current = get_workspace_document_snapshot(tmp_path, replacement.document_id)
    original_page = pages.get_page(case.page.document_id, world_id=case.world)
    pages.update_page(case.page.document_id, world_id=case.world,
        expected_revision=original_page.page.object_revision, status='discarded')
    case.request['surface']['instance_id'] = replacement.document_id
    case.request['primary_work'].update(object_id=replacement.document_id,
        expected_revision=current.loaded_revision, expected_content_sha256=current.content_sha256)
    from application_state.errors import (ApplicationStateConflictError,
        ApplicationStateNotFoundError, ApplicationStateValidationError)
    original_admit = AgentConversationService.admit_build_prior_body_evidence
    from time import perf_counter
    admission_times = []
    from application_state.agent_conversation import repository
    original_rows = repository.list_retained_build_turns
    decoded_rows = []
    def measured_rows(conn, current):
        result = original_rows(conn, current)
        decoded_rows.append({'rows': len(result[0]), 'exact_prefix_reused': result[1] is not None})
        return result
    monkeypatch.setattr(repository, 'list_retained_build_turns', measured_rows)
    fenced = []
    def checked_admit(owner, world, conversation, turn_id, **values):
        prior = owner.inspect_turn(world_id=world, turn_id=turn_id)
        for change in ({'expected_revision': values['expected_revision'] - 1},
                       {'expected_attempt': values['expected_attempt'] + 1}):
            with pytest.raises(ApplicationStateConflictError):
                original_admit(owner, world, conversation, turn_id, **(values | change))
            assert owner.inspect_turn(world_id=world, turn_id=turn_id) == prior
            fenced.append(change)
        with pytest.raises((ApplicationStateConflictError, ApplicationStateNotFoundError)):
            original_admit(owner, world, uuid4(), turn_id, **values)
        started = perf_counter()
        result = original_admit(owner, world, conversation, turn_id, **values)
        admission_times.append((perf_counter() - started) * 1000)
        return result
    monkeypatch.setattr(AgentConversationService, 'admit_build_prior_body_evidence', checked_admit)

    original_authorize = AgentConversationService.authorize_native_writer
    tampered = []
    def checked_authorize(owner, world, conversation, turn_id, **values):
        from apps.live_control_server.services.agent_turn_service import _json_node_count
        prior = owner.inspect_turn(world_id=world, turn_id=turn_id)
        if retained.admission(prior.graph_context_execution) is not None:
            for mutation in ('omit', 'change'):
                request = json.loads(values['prepared_request_json'])
                if mutation == 'omit':
                    request['input'] = request['input'][2:]
                else:
                    request['input'][0]['content'] = '{"conversation":"changed older context"}'
                raw = json.dumps(request, ensure_ascii=False)
                auth = values['authorization'].model_copy(update={
                    'envelope_sha256': sha256(raw.encode()).hexdigest(),
                    'input_tokens': len(raw.encode()) + 64 * (1 + _json_node_count(request))})
                with pytest.raises(ApplicationStateValidationError):
                    original_authorize(owner, world, conversation, turn_id,
                        **(values | {'prepared_request_json': raw, 'authorization': auth}))
                assert owner.inspect_turn(world_id=world, turn_id=turn_id) == prior
                tampered.append(mutation)
        return original_authorize(owner, world, conversation, turn_id, **values)
    monkeypatch.setattr(AgentConversationService, 'authorize_native_writer', checked_authorize)
    if discussion:
        from apps.live_control_server.services import native_graph_reads, build_related_pages
        from apps.live_control_server.integrations.dungeonmind import native_corpus_source
        def forbidden(*args, **kwargs):
            raise AssertionError('Anchored discussion attempted new source acquisition')
        monkeypatch.setattr(native_graph_reads, 'prepare_query', forbidden)
        monkeypatch.setattr(build_related_pages, 'acquire_selected_pages', forbidden)
        monkeypatch.setattr(native_corpus_source, 'open_native_corpus_member', forbidden)
        monkeypatch.setattr(native_corpus_source, 'read_native_corpus_member', forbidden)
    before = len(case.writer.calls)
    response = case.client.post('/api/live/agent/turn', json=case.request | {
        'turn_id': str(uuid4()), 'message': synthesis})
    assert response.status_code == 200, response.text
    owner = AgentConversationService()
    turn = max(owner.list_turns(case.world, original.conversation_id), key=lambda row: row.sequence)
    value = retained.admission(turn.graph_context_execution)
    assert value is not None
    assert type(value) is (t.BuildPriorBodyEvidenceAdmittedV3 if discussion else t.BuildPriorBodyEvidenceAdmittedV2)
    if discussion:
        raw = turn.graph_context_execution.model_dump(mode='python', by_alias=True)
        for event in raw['events']:
            if event['kind'] == value.kind:
                event['kind'] = 'build_prior_body_evidence_admitted_v2'
        with pytest.raises(ValueError, match='unique producing Build work decision'):
            type(turn.graph_context_execution).model_validate(raw)
    assert len(fenced) == 2 and tampered == ['omit', 'change']
    assert len(value.history) == turn_count
    assert value.history[0].turn_id == original.turn_id
    assert original.turn_id not in {pin.turn_id for pin in turn.graph_context_receipt.assembled_input.included_history}
    assert value.authored_context and value.native_context
    assert any(row.source_basis.document_id == case.page.document_id for row in value.authored_context)
    assert turn.graph_context_receipt.work_context.source_basis.document_id == replacement.document_id
    assert not acquired_body_reads(turn.graph_context_execution)
    assert not any(isinstance(event, NativeBuildQuerySettledV1) for event in turn.graph_context_execution.events)
    assert len(case.writer.calls) == before + 1
    request = json.loads(case.writer.calls[-1].content)
    assert request['input'][:turn_count * 2] == retained.dialogue_messages(turn.graph_context_execution)
    assert 'build_draft_context' not in case.request
    loaded = AgentConversationService().inspect_turn(world_id=case.world, turn_id=turn.turn_id)
    assert retained.admission(loaded.graph_context_execution) == value
    for citation in loaded.completion.native_body_citations:
        from application_state.agent_conversation.native_corpus import resolve_retained_body_citation
        _, _, text = resolve_retained_body_citation(loaded.graph_context_execution, citation)
        assert text
    for index in range(3):
        response = case.client.post('/api/live/agent/turn', json=case.request | {
            'turn_id': str(uuid4()), 'message': synthesis})
        assert response.status_code == 200, response.text
    assert decoded_rows[0] == {'rows': turn_count, 'exact_prefix_reused': False}
    assert decoded_rows[1:] == [{'rows': 1, 'exact_prefix_reused': True}] * 3
    (tmp_path / 'retained-performance.json').write_text(json.dumps({
        'prior_turns': turn_count, 'admission_ms': admission_times,
        'decoded_rows': decoded_rows}, indent=2) + '\n')


@pytest.mark.parametrize('revision,parent', [('0193', '0192'), ('0194', '0193')])
def test_old_reader_refuses_retained_context_database_before_decoding(application_state_dsn, monkeypatch, revision, parent):
    from importlib import import_module
    from application_state import cli
    from application_state.errors import ApplicationStateMigrationError
    name = 'build_retained_conversation' if revision == '0193' else 'build_discussion_context'
    fence = import_module(f'application_state.migrations.versions.20261122_{revision}_{name}_fence')
    assert fence.down_revision == '20261122_' + parent
    cli.assert_at_head(dsn=application_state_dsn)
    with monkeypatch.context() as old:
        old.setattr(cli, '_alembic_head', lambda: fence.down_revision)
        with pytest.raises(ApplicationStateMigrationError):
            cli.assert_at_head(dsn=application_state_dsn)
    with pytest.raises(RuntimeError, match='forward recovery'):
        fence.downgrade()


def test_repeated_synthesis_reuses_exact_prior_closure_without_recursive_history_decoding():
    current, turns = fixture_closure()
    first = capture(current, turns)
    completed = NS(**{key: getattr(current, key) for key in (
        'world_id', 'conversation_id', 'turn_id', 'sequence', 'attempt')},
        status='completed', user_text='Create the page from all this context.',
        assistant_text='A proposed page, not a completed save.', completion=None,
        graph_context_execution=NS(events=(first,)))
    successor = NS(world_id=current.world_id, conversation_id=current.conversation_id,
        turn_id=uuid4(), sequence=current.sequence + 1, attempt=1,
        graph_context_execution=NS(events=()))
    second = capture(successor, (completed,), seed=first)
    assert second.history[:-1] == first.history
    assert second.history[-1].turn_id == completed.turn_id
    assert second.authored_context == first.authored_context
    assert second.native_context == first.native_context
    assert len(retained.dialogue_messages(NS(events=(second,)))) == 122


def test_late_prior_completion_is_not_hidden_by_a_newer_retained_prefix(lane, tmp_path, monkeypatch):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Event
    from tests.test_surface_native_build_ordinary import _fresh_case
    from tests.page_fixtures import save_page
    from apps.live_control_server.services.workspace_document_registry import get_workspace_document_snapshot
    from application_state.agent_conversation import AgentConversationService, repository

    entered, release = Event(), Event()
    stalled = 'Retain this late-completing earlier constraint: the lantern rings only for lies.'
    synthesis = 'Create a page titled "Glass Regent" from our conversation.'
    def before_provider(adapter, provider):
        if adapter.request.message == stalled and provider == 'typesafe' and not entered.is_set():
            entered.set()
            assert release.wait(60), 'overlapping-turn fixture did not release its provider'
    case = _fresh_case(lane, tmp_path, monkeypatch, None, False, True, False,
        native_body='irrelevant', before_provider=before_provider,
        requested_work=lambda message: 'review_lore_page_from_conversation' if message == synthesis else 'discuss',
        source_need=lambda message: 'anchored' if message == synthesis else 'source_lookup')
    case.request['build_authored_references'] = None
    save_page(tmp_path, case.page.document_id, '# Retained notes\n\nA proposed conversation.\n')
    current = get_workspace_document_snapshot(tmp_path, case.page.document_id)
    case.request['primary_work'].update(expected_revision=current.loaded_revision,
        expected_content_sha256=current.content_sha256)
    selections = []
    original_rows = repository.list_retained_build_turns
    def observe_rows(conn, current):
        rows, seed = original_rows(conn, current)
        selections.append((tuple(row.sequence for row in rows), seed is not None))
        return rows, seed
    monkeypatch.setattr(repository, 'list_retained_build_turns', observe_rows)
    owner = AgentConversationService()
    def submit(message):
        return case.client.post('/api/live/agent/turn', json=case.request | {
            'turn_id': str(uuid4()), 'message': message})
    with ThreadPoolExecutor(max_workers=1) as pool:
        pending = pool.submit(submit, stalled)
        try:
            assert entered.wait(10)
            first = submit(synthesis)
            assert first.status_code == 200, first.text
            seed_owner = max(owner.list_turns(case.world, case.turn.conversation_id), key=lambda row: row.sequence)
            first_closure = retained.admission(seed_owner.graph_context_execution)
            assert first_closure is not None
            assert stalled not in [row.user_text for row in first_closure.history]
        finally:
            release.set()
        completed = pending.result(timeout=30)
        assert completed.status_code == 200, completed.text
    last = submit(synthesis)
    assert last.status_code == 200, last.text
    final = max(owner.list_turns(case.world, case.turn.conversation_id), key=lambda row: row.sequence)
    closure = retained.admission(final.graph_context_execution)
    assert closure is not None
    assert any(row.user_text == stalled and row.assistant_text is not None for row in closure.history)
    assert selections == [((1,), False), ((1, 2, 3), False)]


@pytest.mark.parametrize('boundary,discussion', [('admission', False), ('writer', False), ('admission', True), ('writer', True), ('writer_roundtrip', True)])
def test_reset_fences_retained_capture_and_physical_writer_dispatch(lane, tmp_path, monkeypatch, boundary, discussion):
    from tests.test_surface_native_build_ordinary import _fresh_case
    from application_state.agent_conversation import AgentConversationService
    synthesis = ('Recap our conversation without another search.' if discussion
                 else 'Create a page titled "Glass Regent" from our conversation.')
    case = _fresh_case(lane, tmp_path, monkeypatch, None, False, False, False,
        native_body='irrelevant',
        requested_work=lambda message: ('discuss' if discussion else 'review_lore_page_from_conversation') if message == synthesis else 'discuss',
        source_need=lambda message: 'anchored' if message == synthesis else 'source_lookup')
    case.request['build_authored_references'] = None
    method = 'admit_build_prior_body_evidence' if boundary == 'admission' else 'authorize_native_writer'
    original = getattr(AgentConversationService, method)
    resets = []
    def reset_first(owner, world, conversation, turn_id, **values):
        current = owner.inspect_turn(world_id=world, turn_id=turn_id)
        if current.user_text == synthesis:
            pointer = owner.get_world_pointer(world)
            receipt = owner.new_conversation(t.ConversationCommand(world_id=world,
                command_id=uuid4(), expected_pointer_revision=pointer.revision,
                expected_active_conversation_id=conversation))
            resets.append(receipt)
            if boundary == 'writer_roundtrip':
                moved = owner.get_world_pointer(world)
                owner.reopen_conversation(t.ReopenCommand(world_id=world, command_id=uuid4(),
                    expected_pointer_revision=moved.revision,
                    expected_active_conversation_id=moved.active_conversation_id,
                    conversation_id=conversation))
                returned = owner.get_world_pointer(world)
                assert returned.active_conversation_id == conversation
                assert returned.revision > retained.admission(current.graph_context_execution).pointer_revision
        return original(owner, world, conversation, turn_id, **values)
    monkeypatch.setattr(AgentConversationService, method, reset_first)
    before = len(case.writer.calls)
    response = case.client.post('/api/live/agent/turn', json=case.request | {
        'turn_id': str(uuid4()), 'message': synthesis})
    assert response.status_code in (409, 503), response.text
    assert len(resets) == 1
    assert len(case.writer.calls) == before
    pointer = AgentConversationService().get_world_pointer(case.world)
    assert (pointer.active_conversation_id == case.turn.conversation_id) == (boundary == 'writer_roundtrip')


def test_actual_mixed_unclaimed_completion_retains_approved_rules_dialogue_without_base_evidence(application_state_dsn):
    from tests.application_state.test_agent_conversation_postgres import _accepted_execution_turn
    from tests.application_state.test_rules_authority_completion import ready_rules, join_graph_provider
    from application_state.agent_conversation import AgentConversationService
    from application_state.agent_conversation.rules_authority_completion import MixedTurnResultV1
    owner = AgentConversationService()
    _, _, _, turn = _accepted_execution_turn(owner, 'retained-unclaimed-world')
    turn, result = ready_rules(application_state_dsn, turn)
    turn = join_graph_provider(application_state_dsn, owner, turn, result)
    fields = result.model_dump(mode='json', by_alias=True)
    fields['expected_turn_revision'] = turn.revision
    fields['composition']['base_disposition'] = 'unclaimed'
    completed = owner.complete_mixed_turn(MixedTurnResultV1.model_validate_json(json.dumps(fields)))
    assert completed.base_projection.kind == 'unclaimed'
    current = NS(world_id=turn.world_id, conversation_id=turn.conversation_id,
        turn_id=uuid4(), sequence=turn.sequence + 1, attempt=1, graph_context_execution=NS(events=()))
    value = capture(current, (completed,))
    assert value.history[0].user_text == turn.user_text
    assert value.history[0].assistant_text == completed.assistant_text
    assert not value.history[0].base_approved
    assert not value.history[0].proposal_context
    assert not value.authored_context and not value.native_context


def test_actual_approved_mixed_http_reply_retains_visible_questions(lane, tmp_path, monkeypatch):
    from tests.test_surface_native_build_ordinary import _fresh_case
    from application_state.agent_conversation import AgentConversationService
    from application_state.agent_conversation.rules_authority_reads import MixedCompletedTurnV1
    from application_state.agent_conversation import work_plan as w
    from application_state.build_proposal.types import BuildWriteCapability
    case = _fresh_case(lane, tmp_path, monkeypatch, 'mixed_questions', True, False, False)
    step = w.StepV2(step_id=uuid4(), text='Can I end my move in an occupied space?',
        selected=True, kind='discuss', references=())
    deferred = w.StepV2(step_id=uuid4(), text='Write a paragraph only after placement is chosen.',
        selected=False, kind='prepare_insertion', references=())
    plan = w.save(case.world, case.turn.conversation_id, case.turn.turn_id,
        w.ReviewV3(expected_revision=0, objective='Choose placement before writing.',
                   steps=[step, deferred], root_references=case.selected.references))
    continued = w.continue_step(case.world, case.turn.conversation_id, case.turn.turn_id,
        w.Continue(expected_revision=plan['revision'], step_id=step.step_id, command_id=uuid4()))
    dispatch = continued['dispatch']
    snapshot = case.draft.snapshot
    cap = BuildWriteCapability(idempotency_key=uuid4(), conversation_id=case.draft.conversation_id,
        expected_pointer_revision=case.draft.expected_pointer_revision,
        draft_markdown=snapshot.draft_markdown,
        basis=dict(**{key: getattr(snapshot, key) for key in ('world_id', 'document_id',
            'registry_revision', 'content_sha256', 'visibility', 'draft_sha256', 'editor_sha256',
            'draft_generation')}, caret=1, selection_generation=0))
    case.writer.review = {'kind': 'questions', 'questions': [{'text': 'Where should the lamp stand?'}]}
    response = case.client.post('/api/live/agent/turn', json=case.request | {
        'client_thread_id': dispatch['client_thread_id'], 'turn_id': dispatch['client_turn_id'],
        'message': dispatch['message'], 'reviewed_step': continued['reviewed_step'],
        'build_write_capability': cap.model_dump(mode='json'),
        'build_authored_references': dispatch['authored_references']})
    assert response.status_code == 200, response.text
    owner = AgentConversationService()
    completed = max(owner.list_turns(case.world, case.turn.conversation_id), key=lambda row: row.envelope.sequence
                    if isinstance(row, MixedCompletedTurnV1) else row.sequence)
    assert isinstance(completed, MixedCompletedTurnV1)
    assert completed.base_projection.kind == 'approved'
    envelope = completed.envelope
    current = NS(world_id=envelope.world_id, conversation_id=envelope.conversation_id,
        turn_id=uuid4(), sequence=envelope.sequence + 1, attempt=1, graph_context_execution=NS(events=()))
    value = capture(current, (completed,))
    assert value.history[0].assistant_text == completed.assistant_text
    assert value.history[0].proposal_context == ('Proposed questions', 'Where should the lamp stand?')
    wire = json.dumps(retained.dialogue_messages(NS(events=(value,))))
    assert str(envelope.turn_id) not in wire
    assert str(completed.accepted_binding_sha256) not in wire


def test_retained_source_presentation_projects_owned_navigation_and_pdf_provenance():
    from application_state.agent_conversation.model_markdown import project_retained_source_markdown
    ident = str(uuid4())
    source = (f'[From Earlier notes](/build?world=retained-world&documentId={ident}) · saved revision 7, lines 5–5\n\n'
              f'Original PDF SHA-256: `{"a" * 64}`.\n\n'
              'The lantern rings only when someone lies.\n')
    projected = project_retained_source_markdown(source)
    assert ident not in projected and 'a' * 64 not in projected
    assert 'saved revision' not in projected
    assert 'Earlier notes' in projected and 'The lantern rings only when someone lies.' in projected
    assert len(projected.splitlines()) == len(source.splitlines())
    assert source != projected  # Original caller-owned source remains unchanged.


def test_retained_projection_preserves_external_links_fenced_literals_and_ordinary_hash_prose():
    from application_state.agent_conversation.model_markdown import project_retained_source_markdown
    source = (f'[An external reference](https://example.test/build?documentId={uuid4()})\n\n'
              f'```text\nOriginal PDF SHA-256: `{"b" * 64}`.\n```\n\n'
              f'The author supplied this literal code: `{"c" * 64}`.\n')
    assert project_retained_source_markdown(source) == source


def test_historical_retained_presentation_replays_but_cannot_authorize_new_dispatch():
    current, turns = fixture_closure(2)
    value = capture(current, turns)
    assert value.presentation_policy == 'retained_conversation_semantic_v2'
    retained.require_current_presentation(NS(events=(value,)))
    historical = value.model_copy(update={'presentation_policy':'retained_conversation_full_v1'})
    wire = historical.model_dump_json()
    assert 'presentation_policy' not in wire
    restored = t.BuildPriorBodyEvidenceAdmittedV2.model_validate_json(wire)
    assert restored.presentation_policy == 'retained_conversation_full_v1'
    assert retained.dialogue_messages(NS(events=(restored,))) == retained.dialogue_messages(NS(events=(value,)))
    with pytest.raises(ValueError, match='replay-only'):
        retained.require_current_presentation(NS(events=(restored,)))


def test_owned_navigation_preserves_mixed_external_links_formatting_and_literal_counter():
    from application_state.agent_conversation.model_markdown import project_retained_source_markdown
    uri = '/build?documentId=' + str(uuid4())
    source = f'Read [the **page**]({uri}), then [the reference](https://example.test/proof "Evidence") and *retain emphasis* · saved revision 7\n'
    assert project_retained_source_markdown(source) == 'Read the **page**, then [the reference](https://example.test/proof "Evidence") and *retain emphasis* · saved revision 7\n'


@pytest.mark.parametrize('form', ['auto', 'destination_label', 'reference', 'quote'])
def test_structured_navigation_forms_do_not_reveal_destination_identity(form):
    from application_state.agent_conversation.model_markdown import project_retained_source_markdown
    ident = str(uuid4())
    uri = 'https://buddy.dungeonmind.net/build?documentId=' + ident
    sources = {
        'auto': f'Read <{uri}> beside [external](https://example.test).\n',
        'destination_label': f'[{uri}]({uri})\n',
        'reference': f'[Earlier **notes**][note] and [external][other].\n\n[note]: {uri}\n[other]: https://example.test\n',
        'quote': f'> Read [earlier\n> **notes**]({uri}) and *preserve this*.\n',
    }
    source = sources[form]
    projected = project_retained_source_markdown(source)
    assert ident not in projected
    assert len(projected.splitlines()) == len(source.splitlines())
    if form in {'auto', 'reference'}:
        assert 'https://example.test' in projected
    if form in {'reference', 'quote'}:
        assert '**notes**' in projected
    if form == 'quote':
        assert '> **notes**' in projected and '*preserve this*' in projected


def test_managed_images_preserve_external_destinations_and_nested_navigation_labels():
    from application_state.agent_conversation.model_markdown import project_retained_source_markdown
    media, document = str(uuid4()), str(uuid4())
    source = (f'Keep **bold**, ![the *map*](dmb-media:{media}), and [reference](https://example.test).\n\n'
              f'[![map](dmb-media:{media})](/build?documentId={document})\n')
    assert project_retained_source_markdown(source) == (
        'Keep **bold**, [Image: the *map*], and [reference](https://example.test).\n\n[Image: map]\n')


def test_owned_navigation_keeps_source_line_endings_and_link_title_context():
    from application_state.agent_conversation.model_markdown import project_retained_source_markdown
    uri = '/build?documentId=' + str(uuid4())
    source = f'> [a **rumor**]({uri} "Unconfirmed possibility")\r\n\r\nKeep [external](https://example.test).\r\n'
    assert project_retained_source_markdown(source) == '> a **rumor** (Unconfirmed possibility)\r\n\r\nKeep [external](https://example.test).\r\n'


def test_discussion_reuse_is_versioned_and_fresh_lookup_keeps_acquisition():
    from application_state.agent_conversation.native_corpus import is_prior_conversation_work
    assert not is_prior_conversation_work('discuss', 'anchored')
    assert is_prior_conversation_work('discuss', 'anchored', allow_discussion=True)
    for scope in ('source_lookup', 'uncertain'):
        assert not is_prior_conversation_work('discuss', scope, allow_discussion=True)
    current, turns = fixture_closure(8)
    value = retained.capture(current, turns, event_id=uuid4(), work_event_id=uuid4(),
        pointer_revision=7, discussion=True)
    assert type(value) is t.BuildPriorBodyEvidenceAdmittedV3
    assert t.BuildPriorBodyEvidenceAdmittedV3.model_validate_json(value.model_dump_json()) == value
    assert len(retained.dialogue_messages(NS(events=(value,)))) == 16
