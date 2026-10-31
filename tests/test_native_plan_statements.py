"""Core-backed query/support characterization; ordinary HTTP integration remains an acceptance gate."""
from dataclasses import replace
from types import SimpleNamespace
from uuid import uuid4
import pytest
from tests.test_source_statements import lane, commit, advance, GM, BODY
from apps.live_control_server.services.native_plan_statements import prepare_query, read_selected
from application_state.agent_conversation.native_plan_statements import NativePlanStatementReadAuthorizedV1


def bound(lane):
    return SimpleNamespace(managed_world_id=lane.world.world_id, native_world_id=lane.world.world_id,
        binding_version=1)


def query(lane, text='What did B do?', **kwargs):
    return prepare_query(lane.world.world_id, text, GM, repository=lane.repo,
        resolve_binding=lambda _: bound(lane), **kwargs)


def selected(lane, ctx, statement_ids=None):
    grant = NativePlanStatementReadAuthorizedV1(event_id=uuid4(), sequence=0,
        provider_attempt_id=uuid4(), query_sha256=ctx.query.sha256,
        statement_ids=statement_ids or tuple(m.statement_id for m in ctx.query.matches))
    return read_selected(ctx, grant, GM, resolve_binding=lambda _: bound(lane))


def test_natural_query_discovers_qualified_statement_without_subject_id(lane):
    prepared, _ = commit(lane)
    ctx, result = query(lane)
    assert result.status == 'complete' and len(result.matches) == 1
    assert result.question == 'What did B do?'
    assert result.matches[0].statement_id != lane.ids['B']
    assert 'quote' not in result.model_dump_json() and 'B fled' not in result.model_dump_json()
    (read,), unavailable = selected(lane, ctx)
    assert not unavailable
    assert read.support.payload == prepared.envelope['payload']
    assert read.support.clause_text == BODY.splitlines(keepends=True)[0]
    assert read.source_body_bytes == len(BODY.encode())
    assert read.support.payload['embedded_content_factive'] is False
    assert read.support.payload['episode'] == 'episode-1'
    assert read.support.payload['reporter'] == lane.ids['A']


def test_identity_only_is_not_qualified_support_and_campaign_scope_is_preserved(lane):
    _, empty = query(lane, 'B')
    assert empty.discovered_entity_ids and not empty.matches
    commit(lane)
    _, hidden = query(lane, scope_mode='campaign', campaign_id='c2')
    assert not hidden.matches and hidden.universal_absence_claimed is False
    ctx, visible = query(lane, scope_mode='campaign', campaign_id='c1')
    assert visible.matches
    assert selected(lane, ctx)[0]


def test_selected_read_rejects_injected_ids_and_authority_changes(lane):
    commit(lane)
    ctx, _ = query(lane)
    with pytest.raises(ValueError, match='not discovered'):
        selected(lane, ctx, ('ent:not-discovered',))
    grant = NativePlanStatementReadAuthorizedV1(event_id=uuid4(), sequence=0,
        provider_attempt_id=uuid4(), query_sha256=ctx.query.sha256,
        statement_ids=(ctx.query.matches[0].statement_id,))
    with pytest.raises(ValueError, match='binding changed'):
        read_selected(ctx, grant, GM, resolve_binding=lambda _: SimpleNamespace(binding_version=99))
    with pytest.raises(ValueError, match='GM authority'):
        prepare_query(lane.world.world_id, 'B', replace(GM, role='player'), repository=lane.repo,
            resolve_binding=lambda _: bound(lane))


def test_historical_query_support_survives_unrelated_head_advance(lane):
    commit(lane)
    ctx, original = query(lane)
    before, _ = selected(lane, ctx)
    advance(lane)
    after, _ = selected(lane, ctx)
    assert before == after
    assert before[0].support.ancestry[0]['revision_id'] == original.authority.revision_id


def test_missing_active_binding_is_typed_not_a_source_or_graph_fallback(lane):
    from apps.live_control_server.services.world_graph_projection import WorldGraphProjectionServiceError
    def no_graph(_):
        raise WorldGraphProjectionServiceError('Pending', code='native_graph_provisioning_pending', status_code=409)
    ctx, result = prepare_query(lane.world.world_id, 'B', GM, repository=lane.repo, resolve_binding=no_graph)
    assert ctx is None and result.reason == 'native_graph_binding_unavailable'
    assert result.managed_world_id == lane.world.world_id


def test_world_query_retains_two_campaigns_without_fabricating_common_frame(lane):
    commit(lane)
    # Publish visible identities in the second campaign through the real WK/Core
    # fixture, rather than bypassing the endpoint authority gate.
    from tests.test_source_statements import service, transport, wk, NOW, CAMPAIGN_SCOPE_AXIS
    from graph_memory.vnext.domain_runtime import dungeonbuddy_world_domain_contract, dungeonbuddy_dnd5e_custom_predicate_profile
    runtime = transport.runtime(lane.repo, dungeonbuddy_world_domain_contract(),
        dungeonbuddy_dnd5e_custom_predicate_profile(), now=NOW, operation_id='second-campaign-identities')
    meta = replace(lane.meta, scope=(wk.ScopeBinding(CAMPAIGN_SCOPE_AXIS, 'c2'),))
    change = wk.WorldChangeIntent(lane.world.world_id, 'query-test', tuple(
        wk.UseExisting(identity, (wk.CreateFact('c2-name-' + name, 'dnd5e:name', wk.LiteralFactValue(name), meta),))
        for name, identity in lane.ids.items()))
    runtime.commit_prepared_change(runtime.prepare_change(change), confirmed_by=GM.subject)
    lane.selection = lane.selection.model_copy(update={
        'campaign_id': 'c2', 'episode': 'episode-c2',
        'expected_parent_revision_id': lane.repo.get_head(lane.world.world_id).head_revision_id})
    commit(lane)
    ctx, result = query(lane)
    assert {m.campaign_id for m in result.matches} == {'c1', 'c2'}
    reads, unavailable = selected(lane, ctx)
    assert not unavailable
    assert {r.support.payload['clause']['campaign'] for r in reads} == {'c1', 'c2'}
    _, scoped = query(lane, scope_mode='campaign', campaign_id='c1')
    assert {m.campaign_id for m in scoped.matches} == {'c1'}


def test_query_does_not_open_clauses_before_selected_read(lane, monkeypatch):
    commit(lane)
    import apps.live_control_server.services.source_statements as statements
    import apps.live_control_server.services.native_statement_answer_context as support
    def forbidden(*_args, **_kwargs):
        pytest.fail('Source body opened during metadata-only native discovery')
    monkeypatch.setattr(statements, 'open_admitted_native_text', forbidden)
    monkeypatch.setattr(support, 'open_admitted_native_text', forbidden)
    ctx, result = query(lane)
    assert ctx is not None and result.matches


@pytest.mark.parametrize('whole_clause,unavailable_read', [(False, False), (True, False), (False, True)])
def test_historical_native_http_retry_preserves_reader_support_and_citations(lane, application_state_dsn, monkeypatch, tmp_path, whole_clause, unavailable_read):
    import json
    import httpx2
    from hashlib import sha256
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from apps.live_control_server.routes import agent
    from apps.live_control_server.services import plan_jev_harness, managed_world_graph_projection as managed
    from apps.live_control_server.services import native_plan_statements as native_query
    from apps.live_control_server.services.plan_jev_harness import PlanJevHarness
    from tests.test_agent_turn_service import _pinned_plan_request, _pinned_plan_work
    from tests.test_plan_jev_writer import WriterWire
    if whole_clause:
        lane.selection = lane.selection.model_copy(update={'end_byte': len(BODY.encode()),
            'clause_sha256': sha256(BODY.encode()).hexdigest()})
    commit(lane)
    world = lane.world.world_id
    binding = SimpleNamespace(managed_world_id=world, native_world_id=world, binding_version=1,
        provisioning_id=None)
    monkeypatch.setattr(managed, 'resolve_managed_source_identity', lambda _: binding)
    monkeypatch.setattr(native_query, 'resolve_managed_world_binding', lambda _: binding)
    monkeypatch.setattr('apps.live_control_server.services.agent_graph_policy.resolve_agent_graph_openai_inference',
        lambda **_: ('openai-api', 'gpt-6-luna', 'https://api.openai.com/v1'))
    markdown = '# Query Plan\n\nA proposed visit.\n'
    work = _pinned_plan_work(markdown)
    work = replace(work, world_id=world, owner_id=world, content_basis=work.content_basis.model_copy(update={
        'world_id': world, 'content_sha256': sha256(markdown.encode()).hexdigest(), 'work_revision_id': str(uuid4())}))
    request = _pinned_plan_request()
    request = type(request).model_validate(request.model_dump(mode='json', by_alias=True) | {
        'turn_id': str(uuid4()), 'message': 'What did B do?',
        'owner_scope': {'kind': 'world', 'world_id': world},
        'primary_work': request.primary_work.model_dump(mode='json', by_alias=True) | {
            'expected_content_sha256': work.content_basis.content_sha256},
        'plan_context_policy': {'policy': 'auto_plan_world'}, 'graph_request': {'mode': 'none'}})
    monkeypatch.setenv('DMB_AGENT_GRAPH_AUTH_MODE', 'local_operator')
    monkeypatch.setenv('DMB_AGENT_GRAPH_AUTH_ENVIRONMENT', 'local')
    token = 'synthetic-native-plan-test-token-1234567890'
    monkeypatch.setenv('DMB_AGENT_GRAPH_LOCAL_OPERATOR_TOKEN', token)
    monkeypatch.setattr(agent, 'repo_root', lambda: tmp_path)
    monkeypatch.setattr(agent, 'session_dir', lambda: tmp_path / 'sessions')
    monkeypatch.setattr(agent, '_owner_resolver', lambda _: {'kind': 'world', 'id': world, 'name': 'Synthetic World'})
    monkeypatch.setattr(agent, '_verified_world_id', lambda value: value)
    monkeypatch.setattr(agent, '_work_resolver', lambda *_: work)
    monkeypatch.setattr(agent, '_historical_work_resolver', lambda *_args, **_kwargs: work)
    monkeypatch.setattr(agent, '_graph_resolver', lambda *_: pytest.fail('Generic Graph fallback'))
    monkeypatch.setattr('apps.live_control_server.integrations.dungeonmind.world_graph_reads.direct_services_from_config',
        lambda *_: pytest.fail('Historical native retry changed its reader'))
    examined_inputs = []
    if unavailable_read:
        monkeypatch.setattr(native_query, 'read_selected', lambda context, authorization, principal:
            ((), authorization.statement_ids))
    class Decisions(httpx2.AsyncBaseTransport):
        async def handle_async_request(self, req):
            body = json.loads(req.content)
            candidates = body.get('state', {}).get('candidates', [])
            native = {i for i, c in enumerate(candidates) if str(c.get('kind', '')).startswith('Qualified native')}
            examined_inputs.extend(row for row in body.get('state', {}).get('examined_subjects', [])
                if row['kind'].startswith('Previously selected native statement:'))
            assert BODY not in req.content.decode()
            assert all(candidates[i]['label'].startswith('About B [') for i in native)
            answers = {}
            for name, entry in body['questions'].items():
                choice = ('discuss' if name == 'requested_work' else
                    'finish_retrieval' if name == 'operation' else
                    'include' if name.startswith('candidate_') and int(name.split('_')[-1]) in native else 'exclude')
                answers[name] = {'type': 'choice', 'choice': choice, 'confidence': 1,
                    'probabilities': {key: float(key == choice) for key in entry['criteria']}}
            return httpx2.Response(200, request=req, json={'model': 'jev-1.14.0', 'answers': answers,
                'usage': {'input_tokens': 37, 'output_tokens': 9}})
    class Writer(WriterWire):
        async def handle_async_request(self, req):
            frame = json.loads(json.loads(req.content)['input'][0]['content'])
            if unavailable_read:
                assert not frame['native_statements']['statements']
                self.text = json.dumps({'schema': frame['answer_policy'], 'answer_segments': [],
                    'limitations': ['missing_requested_details', 'partial_retrieval'],
                    'requested_detail_gaps': [{'question_phrase': 'What did B do?'}]})
                return await super().handle_async_request(req)
            row = frame['native_statements']['statements'][0]
            assert row['payload']['quote'] == BODY.splitlines(keepends=True)[0]
            assert row['payload']['embedded_content_factive'] is False
            assert len(frame['native_statements']['statements']) == 1
            assert 'clause_text' not in row
            assert json.dumps(frame).count(row['payload']['quote'].strip()) == 1
            self.text = json.dumps({'schema': frame['answer_policy'], 'limitations': [], 'requested_detail_gaps': [],
                'answer_segments': [{'kind': 'native_statement_report', 'text': 'A reports that B fled, with uncertainty.',
                    'statement_handles': [row['statement_handle']]}]})
            return await super().handle_async_request(req)
    wire = Writer(None, '')
    class Harness(PlanJevHarness):
        def execute(self, adapter, **kwargs):
            wire.adapter = adapter
            try:
                return super().execute(adapter, **kwargs)
            except BaseException:
                import traceback
                wire.failure = traceback.format_exc()
                raise
    monkeypatch.setattr(plan_jev_harness, 'default_plan_jev_runtime', lambda: Harness(
        decision_transport=Decisions(), writer_transport=wire,
        decision_api_key='synthetic-not-secret', writer_api_key='synthetic-not-secret'))
    # Retain a genuine interrupted native turn from the prior reader contract.
    # Fresh questions use the managed publication Graph; this retry stays pinned.
    import asyncio
    from application_state.agent_conversation import AgentConversationService, types as t
    from apps.live_control_server.services import agent_turn_service as owner
    from apps.live_control_server.services.plan_source_turn import prepare
    from apps.live_control_server.services.plan_jev_dispatch import PlanJevDispatch, request_budget
    corpus, authority = prepare(world, GM)
    context, query_record = native_query.prepare_query(world, request.message, GM,
        source_context=corpus)
    from application_state.agent_conversation.native_plan_statements import NativePlanQueryV1
    query_record = NativePlanQueryV1.model_validate(query_record.model_dump(mode='json', by_alias=True, exclude={'assertion_matches'}) | {'schema':'dmb_native_plan_query_v1'})
    context = replace(context, query=query_record)
    service = AgentConversationService()
    prior = owner._PolicyExecutionAdapter(service=service, request=request,
        world_id=world, work=work, bootstrap=None, playable_target=None,
        submitted_intent=owner._submitted_turn_intent(request, world_id=world), existing_turn=None,
        budget=request_budget(), context_read_enabled=True, native_corpus_context=corpus,
        native_source_authority=authority, native_query_context=context, native_query=query_record)
    initial = PlanJevDispatch.requested_work(prior, page_title='Query Plan')
    def interrupt_after_claim(view):
        owner._PolicyExecutionAdapter._ensure_claimed(prior, view)
        raise RuntimeError('synthetic interruption before provider authorization')
    prior._ensure_claimed = interrupt_after_claim
    try:
        with pytest.raises(Exception):
            asyncio.run(initial.run(transport=Decisions(), api_key='synthetic-not-secret'))
        retained = prior.fence.turn
        assert isinstance(retained.graph_context_receipt, t.PlanNativeContextReceiptV1)
        assert retained.graph_context_execution.events == []
        service.fail_turn(t.TurnFailure(world_id=world, conversation_id=retained.conversation_id,
            turn_id=retained.turn_id, expected_revision=retained.revision,
            failure_code='synthetic_interruption'), interrupted=True)
    finally:
        if prior.fence is not None:
            prior.fence.renewer.stop_and_join()
    app = FastAPI(); app.include_router(agent.router, prefix='/api/live')
    client = TestClient(app, client=('127.0.0.1', 42000), headers={'Authorization': 'Bearer ' + token})
    response = client.post('/api/live/agent/turn', json=request.model_dump(mode='json', by_alias=True))
    assert response.status_code == (503 if whole_clause else 200), response.text + getattr(wire, 'failure', '')
    assert len(examined_inputs) == 1
    assert examined_inputs[0]['label'].startswith('About B [')
    assert (': unavailable;' if unavailable_read else ': opened;') in examined_inputs[0]['kind']
    if unavailable_read:
        assert response.status_code == 200, response.text + getattr(wire, 'failure', '')
        assert not response.json()['plan_context']['completion']['native_clause_citations']
        replay = client.post('/api/live/agent/turn', json=request.model_dump(mode='json', by_alias=True))
        assert replay.json()['plan_context']['completion'] == response.json()['plan_context']['completion']
        assert len(wire.calls) == 1
        return
    if whole_clause:
        assert response.status_code == 503 and not wire.calls
        assert 'explicit full-document decision' in wire.failure
        return
    assert response.status_code == 200, response.text + getattr(wire, "failure", "")
    data = response.json()
    assert data['answer']['status'] == 'ok', data
    assert data['plan_context']['schema'] == 'dmb_agent_plan_native_context_response_v1'
    assert data['plan_context']['receipt']['graph_capability'] is None
    completion = data['plan_context']['completion']
    assert completion['schema'] == 'dmb_surface_evidence_completion_v6' and completion['native_clause_citations']
    turn = wire.adapter.turn
    from application_state.agent_conversation.native_plan_statements import (
        validate_execution, NativePlanStatementReadObservedV1)
    events = turn.graph_context_execution.events
    observation = next(e for e in events if isinstance(e, NativePlanStatementReadObservedV1))
    pending = turn.graph_context_execution.model_copy(update={'events': [
        e for e in events if not isinstance(e, NativePlanStatementReadObservedV1)]})
    with pytest.raises(ValueError, match='every selected read grant'):
        validate_execution(turn.graph_context_receipt, pending)
    unavailable = observation.model_copy(update={'reads': (), 'status': 'partial',
        'unavailable_statement_ids': tuple(r.support.statement_id for r in observation.reads)})
    settled = turn.graph_context_execution.model_copy(update={'events': [
        unavailable if e is observation else e for e in events]})
    validate_execution(turn.graph_context_receipt, settled)
    # New controller calls cannot outrun a read or substitute another frozen query.
    import asyncio
    from apps.live_control_server.services.plan_jev_driver import PlanJevDriver
    driver = PlanJevDriver(wire.adapter)
    assert len(driver._native_statement_examined()) == 1
    assert ': opened;' in driver._native_statement_examined()[0].kind
    class NoProvider(httpx2.AsyncBaseTransport):
        async def handle_async_request(self, req):
            pytest.fail('Controller provider reached before acquisition validation')
    original_execution = wire.adapter._broker_execution
    grant_index = next(i for i, e in enumerate(events) if e.kind == 'native_plan_statement_read_authorized_v1')
    unfinished = turn.graph_context_execution.model_copy(update={'events': events[:grant_index + 1]})
    monkeypatch.setattr(wire.adapter, '_broker_execution', lambda: unfinished)
    with pytest.raises(ValueError, match='must settle before another controller'):
        asyncio.run(driver.run(transport=NoProvider(), api_key='synthetic-not-secret'))
    monkeypatch.setattr(wire.adapter, '_broker_execution', lambda: settled)
    assert ': unavailable;' in driver._native_statement_examined()[0].kind
    monkeypatch.setattr(wire.adapter, '_broker_execution', original_execution)
    original_query = wire.adapter.native_query
    monkeypatch.setattr(wire.adapter, 'native_query', original_query.model_copy(update={'question': 'Foreign question'}))
    with pytest.raises(ValueError, match='differs from its frozen receipt'):
        asyncio.run(driver.run(transport=NoProvider(), api_key='synthetic-not-secret'))
    monkeypatch.setattr(wire.adapter, 'native_query', original_query)
    duplicated = turn.graph_context_execution.model_copy(update={'events': [*events, observation]})
    monkeypatch.setattr(wire.adapter, '_broker_execution', lambda: duplicated)
    with pytest.raises(ValueError, match='observation differs'):
        asyncio.run(driver.run(transport=NoProvider(), api_key='synthetic-not-secret'))
    monkeypatch.setattr(wire.adapter, '_broker_execution', original_execution)
    advance(lane)
    opened = client.get(f'/api/live/agent/worlds/{world}/conversation/turns/{turn.turn_id}/native-source-clauses/0')
    assert opened.status_code == 200, opened.text
    assert opened.json()['content'] == BODY.splitlines(keepends=True)[0]
    replay = client.post('/api/live/agent/turn', json=request.model_dump(mode='json', by_alias=True))
    assert replay.status_code == 200, replay.text
    assert replay.json()['plan_context']['completion'] == completion and len(wire.calls) == 1
    history = client.get(f'/api/live/agent/worlds/{world}/conversation?include_turn_correlation=true')
    assert history.status_code == 200, history.text
    assert history.json()['turns'][0]['plan_context']['completion'] == completion


@pytest.mark.parametrize('failure', ['statement_payload_invalid', 'statement_receipt_invalid',
    'statement_semantic_conflict', 'statement_bundle_unavailable', 'witness', 'type'])
def test_selected_integrity_errors_are_not_partial_retrieval(lane, monkeypatch, failure):
    from apps.live_control_server.services import native_plan_statements as native
    commit(lane)
    ctx, _ = query(lane)
    if failure == 'witness':
        original = native.statements._bundle
        def changed(*args, **kwargs):
            return original(*args, **kwargs) | {'assertion_ids': []}
        monkeypatch.setattr(native.statements, '_bundle', changed)
        error = ValueError
    else:
        error = TypeError if failure == 'type' else native.statements.StatementError
        def broken(*args, **kwargs):
            if failure == 'type':
                raise TypeError('Malformed support')
            raise native.statements.StatementError(failure, 'Invalid selected support')
        monkeypatch.setattr(native.statements, '_bundle', broken)
    with pytest.raises(error):
        selected(lane, ctx)


def test_core_not_found_is_typed_unavailable_but_incomplete_is_fatal(lane, monkeypatch):
    from apps.live_control_server.services import native_plan_statements as native
    commit(lane)
    ctx, _ = query(lane)
    monkeypatch.setattr(native.statements, 'EntityReadService', lambda: SimpleNamespace(
        get_complete_entity=lambda *_: SimpleNamespace(found=False)))
    reads, unavailable = selected(lane, ctx)
    assert not reads and unavailable == tuple(m.statement_id for m in ctx.query.matches)
    monkeypatch.setattr(native.statements, 'EntityReadService', lambda: SimpleNamespace(
        get_complete_entity=lambda *_: SimpleNamespace(found=True,
            completeness=SimpleNamespace(status='partial'))))
    with pytest.raises(native.statements.StatementError):
        selected(lane, ctx)


@pytest.mark.parametrize('case', ['missing', 'conflicting', 'wrong_campaign', 'partial', 'other_predicate'])
def test_navigation_names_require_unambiguous_admitted_scoped_identity(lane, monkeypatch, case):
    from apps.live_control_server.services import native_plan_statements as native
    commit(lane)
    original = native.EntityReadService()
    calls = []
    def read(context, identity):
        calls.append(identity)
        entity = original.get_complete_entity(context, identity)
        if identity != lane.ids['B']:
            return entity
        name = next(a for a in entity.assertions if a.subject_entity_id == identity and a.predicate == 'dnd5e:name')
        assertions = [a for a in entity.assertions if a is not name]
        if case == 'conflicting':
            assertions += [name, replace(name, assertion_id='asrt:conflicting',
                value=replace(name.value, value='Other', canonical_json_text='"Other"'))]
        elif case == 'wrong_campaign':
            assertions += [replace(name, metadata=replace(name.metadata,
                scope=(replace(name.metadata.scope[0], value='c2'),)))]
        elif case == 'other_predicate':
            assertions += [replace(name, predicate='dnd5e:summary')]
        elif case == 'partial':
            return replace(entity, completeness=replace(entity.completeness, status='partial', reason='support_unavailable'))
        return replace(entity, assertions=tuple(assertions))
    monkeypatch.setattr(native, 'EntityReadService', lambda: SimpleNamespace(get_complete_entity=read))
    _, result = query(lane)
    assert len(result.matches) == 1
    assert result.matches[0].label.startswith('About ' + lane.ids['B'] + ' · ')
    assert 'About B [' not in result.matches[0].label and 'Other' not in result.matches[0].label
    assert len(calls) == len(set(calls))
    assert set(calls) <= set(result.discovered_entity_ids) | {m.statement_id for m in result.matches}


def test_shared_source_and_episode_labels_distinguish_about_subjects(lane, monkeypatch):
    commit(lane)
    lane.selection = lane.selection.model_copy(update={
        'referents': [lane.ids['A']], 'meaning': 'A reports another source-local episode',
        'start_byte': len(BODY.splitlines(keepends=True)[0].encode()), 'end_byte': len(BODY.encode()),
        'clause_sha256': __import__('hashlib').sha256(BODY.splitlines(keepends=True)[1].encode()).hexdigest(),
        'expected_parent_revision_id': lane.repo.get_head(lane.world.world_id).head_revision_id})
    commit(lane)
    _, result = query(lane, 'A B')
    labels = [m.label for m in result.matches]
    assert len(labels) == 2
    assert any(label.startswith('About A [') for label in labels)
    assert any(label.startswith('About B [') for label in labels)
    assert all('episode-1 (c1)' in label for label in labels)
    assert all('flight' not in label and 'fled' not in label and 'uncertain' not in label for label in labels)


def test_direct_statement_hit_never_expands_referent_names(lane, monkeypatch):
    from apps.live_control_server.services import native_plan_statements as native
    commit(lane)
    original = native.EntityReadService()
    calls = []
    def read(context, identity):
        calls.append(identity)
        assert identity not in lane.ids.values()
        return original.get_complete_entity(context, identity)
    monkeypatch.setattr(native, 'EntityReadService', lambda: SimpleNamespace(get_complete_entity=read))
    _, result = query(lane, 'episode-1')
    assert len(result.matches) == 1 and calls == list(result.discovered_entity_ids)
    assert not result.matches[0].label.startswith('About ')
