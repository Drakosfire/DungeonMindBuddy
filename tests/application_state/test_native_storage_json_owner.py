"""Real PostgreSQL parity, refusal and transactional migration owner checks."""
from copy import deepcopy
from datetime import datetime, timezone
from importlib import import_module
from uuid import uuid4
import json

from alembic import command
import psycopg
from psycopg import sql
from psycopg.types.json import Jsonb
from pydantic_core import to_json
import pytest

from application_state import cli
from application_state.config import APPLICATION_STATE_DSN_ENV
from application_state.errors import ApplicationStateMigrationError
from tests.test_surface_native_turn_records import retained, submission, stored_row

MIGRATION = 'application_state.migrations.versions.20261109_0142_native_storage_json_owner'
JSON_NULL = object()


def _definition(conn):
    return conn.execute("SELECT pg_get_expr(conbin,conrelid) FROM pg_constraint "
        "WHERE conrelid='agent.turn'::regclass AND conname='agent_turn_lifecycle_check'").fetchone()[0]


@pytest.fixture
def storage_predecessor(monkeypatch):
    from tests.application_state.conftest import _admin_dsn, _create_database, _drop_database, _replace_database
    admin = _admin_dsn()
    name = 'dungeonbuddy_app_state_test_' + uuid4().hex[:12]
    _create_database(admin, name)
    try:
        dsn = _replace_database(admin, name)
        monkeypatch.setenv(APPLICATION_STATE_DSN_ENV, dsn)
        command.upgrade(cli.alembic_config(), '20261108_0141')
        yield dsn
    finally:
        _drop_database(admin, name)


def _bind(value, kind):
    if value is JSON_NULL:
        return Jsonb(None)
    return Jsonb(json.loads(to_json(value))) if kind == 'jsonb' and value is not None else value


def _variants(surface):
    owner = import_module(MIGRATION)
    base, _ = stored_row(retained(submission(surface)))
    yield 'valid', base
    for name, _ in owner._ARGS:
        row = deepcopy(base)
        row[name] = None
        yield 'sql_null/' + name, row
    for name in ('graph_context_receipt', 'graph_context_execution', 'completion', 'play_context_receipt'):
        for index, value in enumerate((JSON_NULL, {}, [], 42, True, 'text')):
            row = deepcopy(base)
            row[name] = value
            yield f'json_type/{name}/{index}', row
    for name in ('graph_context_receipt', 'graph_context_execution'):
        for key in base[name]:
            row = deepcopy(base)
            del row[name][key]
            yield f'missing/{name}/{key}', row
        row = deepcopy(base)
        row[name]['extra'] = 'invalid'
        yield 'extra/' + name, row
    for state in ('accepted', 'running', 'interrupted', 'completed'):
        row = deepcopy(base)
        row.update(status=state, completed_at=datetime.now(timezone.utc)
            if state in ('interrupted', 'completed') else None)
        yield 'state/' + state, row
    completed = deepcopy(base)
    completed.update(status='completed', completed_at=datetime.now(timezone.utc),
        claim_expires_at=None, assistant_text='Storage shape only, not grounded admission')
    completed['graph_context_execution']['events'].append({'kind': 'completion_binding'})
    completed['completion'] = dict(schema='dmb_surface_native_completion_v1', surface_id=surface,
        context_receipt_sha256=base['graph_context_receipt']['context_receipt_sha256'],
        producing_provider_attempt_id='11111111-1111-1111-1111-111111111111',
        answer_basis='mixed_evidence', answer_context_status='graph_grounded',
        answer_segments=[{'text': 'shape only'}], collaboration=None, saved_source_citations=[],
        native_body_citations=[], native_clause_citations=[], native_assertion_citations=[])
    yield 'completed_shape', completed
    for key in completed['completion']:
        row = deepcopy(completed)
        del row['completion'][key]
        yield 'completion_missing/' + key, row
    for index, value in enumerate((None, {}, [], 42, True, 'text')):
        row = deepcopy(completed)
        row['completion']['answer_segments'] = value
        yield 'completion_segments/' + str(index), row


    # Distinct native completion families have their own exact key sets.
    if surface == 'build':
        for schema, basis, state, result_key in (
            ('dmb_build_authoring_completion_v1', 'prepared_page_proposal', 'proposal_ready', 'proposal_result_sha256'),
            ('dmb_build_image_preparation_completion_v1', 'prepared_image_direction', 'image_preparation_ready', 'preparation_result_sha256'),
        ):
            row = deepcopy(completed)
            row['completion'] = dict(schema=schema,
                context_receipt_sha256=base['graph_context_receipt']['context_receipt_sha256'],
                answer_basis=basis, answer_context_status=state, answer_segments=[{'text': 'shape only'}],
                citation_map=None, action_id='11111111-1111-1111-1111-111111111111',
                reservation_sha256='a' * 64, provider_attempt_id='11111111-1111-1111-1111-111111111111',
                envelope_sha256='b' * 64, **{result_key: 'c' * 64})
            yield schema + '/valid_shape', row
            for key in row['completion']:
                broken = deepcopy(row)
                del broken['completion'][key]
                yield schema + '/missing/' + key, broken
            broken = deepcopy(row)
            broken['completion']['extra'] = True
            yield schema + '/extra', broken
    mixed = deepcopy(completed)
    mixed.update(answer_composition_kind='rules_mixed_v1', completion=None)
    mixed['graph_context_execution']['events'] = []
    yield 'mixed_valid_shape', mixed
    for text in (None, '', '   '):
        row = deepcopy(mixed)
        row['assistant_text'] = text
        yield 'mixed_text/' + repr(text), row
    row = deepcopy(mixed)
    row['graph_context_execution']['events'] = [{'kind': 'completion_binding'}]
    yield 'mixed_unbound_completion', row


def test_current_native_storage_function_is_one_non_strict_invoker_owner(application_state_dsn):
    owner = import_module(MIGRATION)
    old = import_module('application_state.migrations.versions.20261101_0103_shared_native_turns')
    with psycopg.connect(application_state_dsn) as conn:
        props = conn.execute('SELECT proisstrict,provolatile,proparallel,prosecdef,proconfig,'
            'pg_get_functiondef(oid) FROM pg_proc WHERE oid=to_regprocedure(%s)', (owner._SIGNATURE,)).fetchone()
        assert props[:5] == (False, 'i', 's', False, ['search_path=pg_catalog'])
        assert props[5].count(old._NATIVE) == 1
        assert props[5].count("|| '{}'::jsonb") == 2
        assert _definition(conn).count(owner._FUNCTION + '(') == 1
        assert conn.execute("SELECT to_regclass('pg_temp.dmb_native_json_owner_shape')").fetchone() == (None,)


@pytest.mark.parametrize('surface', ['build', 'plan', 'play'])
def test_original_and_current_whole_lifecycle_have_identical_values_and_errors(
    application_state_dsn, storage_predecessor, surface,
):
    with psycopg.connect(storage_predecessor) as conn:
        before = _definition(conn)
    with psycopg.connect(application_state_dsn) as conn:
        after = _definition(conn)
        columns = conn.execute("SELECT attname,format_type(atttypid,atttypmod) FROM pg_attribute "
            "WHERE attrelid='agent.turn'::regclass AND attnum>0 AND NOT attisdropped ORDER BY attnum").fetchall()
        source = 'SELECT ' + ','.join('%s::' + kind + ' AS ' + name for name, kind in columns)
        for label, row in _variants(surface):
            values = [_bind(row.get(name), kind) for name, kind in columns]
            outcomes = []
            for expression in (before, after):
                try:
                    with conn.transaction(force_rollback=True):
                        result = conn.execute('SELECT (' + expression + ') FROM (' + source + ') AS input', values).fetchone()[0]
                        outcomes.append(('value', result))
                except psycopg.Error as exc:
                    outcomes.append(('sqlstate', exc.sqlstate))
            # Do not use bool(): SQL NULL passes a CHECK, unlike FALSE.
            assert outcomes[0] == outcomes[1], (surface, label, outcomes)
            if label in {'valid', 'completed_shape', 'mixed_valid_shape'} or label.endswith('/valid_shape'):
                assert outcomes[0] == ('value', True), (surface, label, outcomes)


@pytest.mark.parametrize('surface', ['build', 'plan', 'play'])
def test_actual_current_checks_reject_corruption_even_with_null_arguments(application_state_dsn, surface):
    base, _ = stored_row(retained(submission(surface)))
    # Opaque DB-only bindings are outside the native storage-shape predicate.
    base['request_fingerprint'] = base['idempotency_fingerprint'] = 'f' * 64
    mutations = [None, ('graph_context_receipt', None), ('graph_context_execution', None),
        ('submitted_intent_fingerprint_v2', None), ('graph_context_execution', 42)]
    with psycopg.connect(application_state_dsn) as conn:
        conn.execute('CREATE TEMP TABLE native_json_check_probe (LIKE agent.turn INCLUDING CONSTRAINTS) ON COMMIT DROP')
        columns = conn.execute("SELECT attname,format_type(atttypid,atttypmod) FROM pg_attribute "
            "WHERE attrelid='agent.turn'::regclass AND attnum>0 AND NOT attisdropped ORDER BY attnum").fetchall()
        query = sql.SQL('INSERT INTO native_json_check_probe ({}) VALUES ({})').format(
            sql.SQL(',').join(sql.Identifier(name) for name, _ in columns),
            sql.SQL(',').join(sql.Placeholder() for _ in columns))
        for mutation in mutations:
            row = deepcopy(base)
            if mutation:
                row[mutation[0]] = mutation[1]
                with pytest.raises(psycopg.errors.CheckViolation):
                    with conn.transaction(force_rollback=True):
                        conn.execute(query, [_bind(row.get(name), kind) for name, kind in columns])
            else:
                with conn.transaction(force_rollback=True):
                    conn.execute(query, [_bind(row.get(name), kind) for name, kind in columns])
                    assert conn.execute('SELECT count(*) FROM native_json_check_probe').fetchone() == (1,)


def test_upgrade_conserves_populated_rows_and_old_reader_fails(storage_predecessor, monkeypatch):
    from tests.application_state.test_rules_authority_migration import turn_fixture
    from tests.application_state.test_surface_native_turns import accept
    with monkeypatch.context() as patch:
        patch.setattr(cli, '_alembic_head', lambda: '20261108_0141')
        turn_fixture()
        accept('plan')
    def snapshot():
        with psycopg.connect(storage_predecessor) as conn:
            return (conn.execute('SELECT turn_id,to_jsonb(t) FROM agent.turn t ORDER BY turn_id').fetchall(),
                conn.execute('SELECT to_jsonb(r) FROM agent.turn_reference r ORDER BY turn_id,reference_role,ordinal').fetchall(),
                dict(conn.execute("SELECT conname,pg_get_expr(conbin,conrelid) FROM pg_constraint "
                    "WHERE conrelid='agent.turn'::regclass AND conname<>'agent_turn_lifecycle_check'").fetchall()))
    before = snapshot()
    command.upgrade(cli.alembic_config(), 'head')
    assert snapshot() == before
    with monkeypatch.context() as patch:
        patch.setattr(cli, '_alembic_head', lambda: '20261108_0141')
        with pytest.raises(ApplicationStateMigrationError):
            cli.assert_at_head(dsn=storage_predecessor)
    with pytest.raises(RuntimeError, match='forward migration'):
        command.downgrade(cli.alembic_config(), '20261108_0141')
    assert snapshot() == before


@pytest.mark.parametrize('failure', ['changed_predicate', 'after_function'])
def test_failed_upgrade_rolls_back_function_constraint_and_revision(storage_predecessor, failure):
    from sqlalchemy import event
    from sqlalchemy.engine import Engine
    owner = import_module(MIGRATION)
    if failure == 'changed_predicate':
        with psycopg.connect(storage_predecessor) as conn:
            conn.execute('ALTER TABLE agent.turn DROP CONSTRAINT agent_turn_lifecycle_check')
            conn.execute('ALTER TABLE agent.turn ADD CONSTRAINT agent_turn_lifecycle_check CHECK(TRUE)')
    with psycopg.connect(storage_predecessor) as conn:
        before = _definition(conn)
    def interrupt(conn, cursor, statement, parameters, context, executemany):
        if statement == 'ALTER TABLE agent.turn DROP CONSTRAINT agent_turn_lifecycle_check':
            raise RuntimeError('injected failure after function creation')
    if failure == 'after_function':
        event.listen(Engine, 'after_cursor_execute', interrupt)
    try:
        with pytest.raises(RuntimeError, match='predicate changed|injected failure'):
            command.upgrade(cli.alembic_config(), 'head')
    finally:
        if failure == 'after_function':
            event.remove(Engine, 'after_cursor_execute', interrupt)
    with psycopg.connect(storage_predecessor) as conn:
        assert _definition(conn) == before
        assert conn.execute('SELECT version_num FROM application_state.schema_migrations').fetchone() == ('20261108_0141',)
        assert conn.execute('SELECT to_regprocedure(%s)', (owner._SIGNATURE,)).fetchone() == (None,)
        assert conn.execute("SELECT to_regclass('pg_temp.dmb_native_json_owner_shape')").fetchone() == (None,)


def test_unexpected_function_identity_refuses_without_replacing_it(storage_predecessor):
    from sqlalchemy.exc import DBAPIError
    owner = import_module(MIGRATION)
    parameters = ','.join(name + ' ' + kind for name, kind in owner._ARGS)
    with psycopg.connect(storage_predecessor) as conn:
        conn.execute('CREATE FUNCTION ' + owner._FUNCTION + '(' + parameters +
            ') RETURNS boolean LANGUAGE sql AS $$ SELECT TRUE $$')
        before = _definition(conn)
        original = conn.execute('SELECT pg_get_functiondef(to_regprocedure(%s))', (owner._SIGNATURE,)).fetchone()[0]
    with pytest.raises(DBAPIError) as caught:
        command.upgrade(cli.alembic_config(), 'head')
    assert caught.value.orig.sqlstate == '42723'
    with psycopg.connect(storage_predecessor) as conn:
        assert _definition(conn) == before
        assert conn.execute('SELECT version_num FROM application_state.schema_migrations').fetchone() == ('20261108_0141',)
        assert conn.execute('SELECT pg_get_functiondef(to_regprocedure(%s))', (owner._SIGNATURE,)).fetchone() == (original,)
