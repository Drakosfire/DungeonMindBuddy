"""Pending-family storage constraints and schema-head refusal, without data resets."""
from copy import deepcopy
import json

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb
from pydantic_core import to_json
import pytest

from application_state import cli
from application_state.agent_conversation import repository
from application_state.errors import ApplicationStateMigrationError
from tests.test_build_source_free_protocol import pending_submission
from tests.test_surface_native_turn_records import retained, stored_row


def test_pending_shape_sql_admission_readback_and_crossed_family_refusal(application_state_dsn):
    turn = retained(pending_submission())
    row, references = stored_row(turn)
    row.update(request_fingerprint='a' * 64, idempotency_fingerprint='b' * 64, updated_at=turn.accepted_at)
    payload = json.loads(to_json(row))
    with psycopg.connect(application_state_dsn) as conn:
        cli.assert_connection_at_head(conn)
        # LIKE copies the actual owning CHECK predicates without needing user
        # records/FKs; all data is connection-local and discarded on commit.
        conn.execute('CREATE TEMP TABLE pending_turn_sql (LIKE agent.turn INCLUDING CONSTRAINTS) ON COMMIT DROP')
        conn.execute('INSERT INTO pending_turn_sql SELECT (jsonb_populate_record(NULL::agent.turn,%s)).*', (Jsonb(payload),))
        with conn.cursor(row_factory=dict_row) as cur:
            stored = cur.execute('SELECT ' + repository._TURN_COLS_T + ' FROM pending_turn_sql t').fetchone()
        assert repository._turn_from_row(None, stored, references=references) == turn
        cases = [
            ('graph_context_receipt', {'schema': 'dmb_surface_native_context_receipt_v1'}),
            ('graph_context_execution', {'schema': 'dmb_surface_native_execution_v1'}),
            ('graph_context_receipt', {'source_authority': {}}),
            ('graph_context_receipt', {'conversation_observation': {'conversation_id': '00000000-0000-0000-0000-000000000000', 'pointer_revision': 1}}),
            ('graph_context_execution', {'events': {}}),
            ('graph_context_execution', {'context_receipt_sha256': 'c' * 64}),
        ]
        for field, change in cases:
            altered = deepcopy(payload)
            altered[field].update(change)
            with pytest.raises(psycopg.errors.CheckViolation), conn.transaction():
                conn.execute('INSERT INTO pending_turn_sql SELECT (jsonb_populate_record(NULL::agent.turn,%s)).*', (Jsonb(altered),))
        for change in [dict(surface_id='plan'), dict(submitted_intent_fingerprint_v2=None),
                       dict(status='completed', completed_at=str(turn.accepted_at), assistant_text='Unbound reply')]:
            with pytest.raises(psycopg.errors.CheckViolation), conn.transaction():
                conn.execute('INSERT INTO pending_turn_sql SELECT (jsonb_populate_record(NULL::agent.turn,%s)).*', (Jsonb(payload | change),))
        assert conn.execute('SELECT count(*) AS n FROM pending_turn_sql').fetchone()[0] == 1


def test_pending_schema_head_refuses_previous_reader(application_state_dsn, monkeypatch):
    with psycopg.connect(application_state_dsn) as conn:
        cli.assert_connection_at_head(conn)
        monkeypatch.setattr(cli, '_alembic_head', lambda: '20261124_0210')
        with pytest.raises(ApplicationStateMigrationError):
            cli.assert_connection_at_head(conn)


def test_completed_pending_sdk_reply_survives_real_sql_checks(application_state_dsn, monkeypatch):
    import asyncio
    import httpx
    from tests.test_build_source_free_protocol import pending_writer_completion_case
    def reply(request):
        body = json.loads(request.content)
        candidate = {'answer_segments': [{'kind': 'discussion', 'text': 'What should this new page describe?'}], 'limitations': []}
        if 'collaboration' in body['text']['format']['schema']['properties']:
            candidate['collaboration'] = None
        return httpx.Response(200, request=request, json={'id': 'resp_sql_pending', 'object': 'response',
            'created_at': 1, 'model': body['model'], 'status': 'completed', 'output': [{'type': 'message',
                'id': 'msg_sql_pending', 'role': 'assistant', 'status': 'completed',
                'content': [{'type': 'output_text', 'text': json.dumps(candidate), 'annotations': []}]}]})
    with pending_writer_completion_case(monkeypatch, source_free_work='clarify_creation') as (state, adapter, rules, writer, prepared):
        turn = asyncio.run(writer.run(transport=httpx.MockTransport(reply), api_key='synthetic'))
        assert turn.status == 'completed' and state.completions == 1
    row, references = stored_row(turn)
    row.update(request_fingerprint='a' * 64, idempotency_fingerprint='b' * 64, updated_at=turn.completed_at)
    with psycopg.connect(application_state_dsn) as conn:
        conn.execute('CREATE TEMP TABLE pending_completed_sql (LIKE agent.turn INCLUDING CONSTRAINTS) ON COMMIT DROP')
        conn.execute('INSERT INTO pending_completed_sql SELECT (jsonb_populate_record(NULL::agent.turn,%s)).*',
            (Jsonb(json.loads(to_json(row))),))
        with conn.cursor(row_factory=dict_row) as cur:
            stored = cur.execute('SELECT ' + repository._TURN_COLS_T + ' FROM pending_completed_sql t').fetchone()
        assert repository._turn_from_row(None, stored, references=references) == turn


@pytest.mark.parametrize('mode', ['clarify', 'rules', 'body', 'reset'])
def test_fresh_pending_build_post_completes_captured_routes(application_state_dsn, tmp_path, monkeypatch, mode):
    import httpx
    from tests.test_source_statements import make_lane
    from tests.test_surface_native_build_ordinary import _fresh_case
    from apps.live_control_server.services import build_jev_runtime as factory, plan_source_turn
    from apps.live_control_server.integrations.dungeonmind import native_corpus_source
    calls = []
    clarify_mode = mode in {'clarify', 'reset'}
    def reply(request):
        body = json.loads(request.content)
        calls.append(body)
        candidate = {'answer_segments': [{'kind': 'discussion', 'text': 'One detail will help me draft this page.'}], 'limitations': []}
        if 'collaboration' in body['text']['format']['schema']['properties']:
            candidate['collaboration'] = {'kind': 'questions', 'questions': [{'text': 'What should the new page describe?'}]}
        if mode == 'body':
            candidate = {'answer_segments': [{'kind': 'native_body_claim',
                'text': 'The source supplies the cited passage.', 'excerpt_handles': ['body0']}], 'limitations': []}
            if 'collaboration' in body['text']['format']['schema']['properties']:
                candidate['collaboration'] = None
        if mode == 'rules':
            candidate = {'kind': 'rules_answer', 'base_output': None,
                'rules_segments': [{'kind': 'rules_claim', 'text': 'An occupied space prevents ending movement.', 'support_ids': ['rule_0']}],
                'ordered_refs': [{'domain': 'rules', 'segment_index': 0}]}
        if mode == 'reset':
            from uuid import uuid4
            from application_state.agent_conversation import AgentConversationService, types as t
            service = AgentConversationService()
            pointer = service.get_world_pointer(lane.world.world_id)
            service.new_conversation(t.ConversationCommand(world_id=lane.world.world_id, command_id=uuid4(),
                expected_pointer_revision=pointer.revision, expected_active_conversation_id=pointer.active_conversation_id))
        return httpx.Response(200, request=request, json={'id': 'resp_post_pending', 'object': 'response',
            'created_at': 1, 'model': body['model'], 'status': 'completed', 'output': [{'type': 'message',
                'id': 'msg_post_pending', 'role': 'assistant', 'status': 'completed',
                'content': [{'type': 'output_text', 'text': json.dumps(candidate), 'annotations': []}]}]})
    original = factory.BuildJevHarness
    class Harness(original):
        def __init__(self, **kwargs):
            kwargs['writer_transport'] = httpx.MockTransport(reply)
            super().__init__(**kwargs)
    monkeypatch.setattr(factory, 'BuildJevHarness', Harness)
    prepares = []
    prepare = native_corpus_source.prepare_native_source_context
    def prepare_source(**kwargs):
        prepares.append(1)
        if clarify_mode: pytest.fail('Clarification must not prepare native sources')
        return prepare(**kwargs)
    monkeypatch.setattr(native_corpus_source, 'prepare_native_source_context', prepare_source)
    monkeypatch.setattr(plan_source_turn, 'prepare_native_source_context', prepare_source)
    lane = make_lane(tmp_path, monkeypatch, narrow=True)
    monkeypatch.setattr(native_corpus_source, 'turn_source_repository', lambda **kwargs: lane.repo)
    monkeypatch.setattr(plan_source_turn, 'turn_source_repository', lambda **kwargs: lane.repo)
    def send(client, world, body):
        body['build_authored_references'] = None
        return client.post('/api/live/agent/turn', json=body)
    case = _fresh_case(lane, tmp_path, monkeypatch, 'used_rules' if mode == 'rules' else None, True, False, False, dispatch=send,
        requested_work='clarify_creation' if clarify_mode else 'discuss',
        source_need='uncertain' if clarify_mode else 'source_lookup', source_answer_output='capture_pending',
        native_body='direct_support' if mode == 'body' else None, direct_source=mode == 'body',
        message='Can I end my move in an occupied space?' if mode == 'rules' else 'What does the source say?' if mode == 'body'
            else 'Please make a new page. Ask me what it should describe.')
    if mode == 'reset':
        assert case.response.status_code in {409, 503}
        assert case.turn.status == 'interrupted' and case.turn.completion is None
        assert not prepares and len(calls) == len(case.decisions.calls) == 1
        again = case.client.post('/api/live/agent/turn', json=case.request)
        assert again.status_code in {409, 503} and len(calls) == len(case.decisions.calls) == 1
        return
    assert case.response.status_code == 200, case.response.text
    receipt = case.turn.base_projection.graph_context_receipt if mode == 'rules' else case.turn.graph_context_receipt
    envelope = case.turn.envelope if mode == 'rules' else case.turn
    assert receipt.schema_ == 'dmb_build_pending_context_receipt_v1'
    assert envelope.status == 'completed'
    if mode == 'clarify':
        assert case.turn.completion.collaboration.questions[0].text == 'What should the new page describe?'
        assert not prepares and len(case.decisions.calls) == 1
    elif mode == 'rules':
        assert 'occupied space' in case.turn.assistant_text and len(prepares) == 1
        assert len(case.decisions.calls) >= 3
        forged = case.turn.model_copy(update={'envelope': case.turn.envelope.model_copy(update={'user_text': 'Another request'})})
        with pytest.raises(ValueError):
            type(case.turn).model_validate_json(forged.model_dump_json(by_alias=True))
    else:
        assert case.turn.completion.native_body_citations and len(prepares) == 1
        assert len(case.decisions.calls) >= 4
    assert len(calls) == 1
    decision_count = len(case.decisions.calls)
    replay = case.client.post('/api/live/agent/turn', json=case.request)
    assert replay.status_code == 200, replay.text
    replay_context = replay.json()['rules_context']['unclaimed_context'] if mode == 'rules' else replay.json()['knowledge_context']
    assert replay_context['delivery_replay'] is True
    assert len(case.decisions.calls) == decision_count and len(calls) == 1
