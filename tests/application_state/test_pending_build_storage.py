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
