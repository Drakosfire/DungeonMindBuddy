"""Database-owner qualification for shared native predicate factoring."""
from copy import deepcopy
from datetime import datetime, timezone
from importlib import import_module
import json
from uuid import uuid4

from alembic import command
import psycopg
from psycopg import sql
from psycopg.types.json import Jsonb
from pydantic_core import to_json
import pytest

from application_state import cli
from application_state.config import APPLICATION_STATE_DSN_ENV
from application_state.errors import ApplicationStateMigrationError
from tests.test_native_plan_assertions import lane as lane
from tests.test_surface_native_build_ordinary import _fresh_case
from tests.test_surface_native_turn_records import retained, submission, stored_row


def test_native_predicate_has_one_storage_owner(application_state_dsn):
    with psycopg.connect(application_state_dsn) as conn:
        assert conn.execute("SELECT to_regclass('pg_temp.dmb_native_storage_shape')").fetchone() == (None,)
        rows = dict(conn.execute("SELECT conname,pg_get_expr(conbin,conrelid) FROM pg_constraint "
            "WHERE conrelid='agent.turn'::regclass AND conname IN "
            "('agent_turn_lifecycle_check','agent_turn_graph_context_receipt_check',"
            "'agent_turn_graph_context_execution_check','agent_turn_graph_completion_check')").fetchall())
        owner = import_module('application_state.migrations.versions.20261101_0103_shared_native_turns')
        conn.execute('CREATE TEMP TABLE native_expected_shape (LIKE agent.turn) ON COMMIT DROP')
        conn.execute('ALTER TABLE native_expected_shape ADD CONSTRAINT expected_native CHECK (COALESCE(('
            + owner._NATIVE + '),FALSE))')
        native = conn.execute("SELECT pg_get_expr(conbin,conrelid) FROM pg_constraint "
            "WHERE conrelid='pg_temp.native_expected_shape'::regclass AND conname='expected_native'").fetchone()[0]
        anchor = native.split('\n', 1)[0]
        materialized = import_module('application_state.migrations.versions.20261109_0142_native_storage_json_owner')
        expression = rows['agent_turn_lifecycle_check']
        assert expression.count(materialized._FUNCTION + '(') == 1
        assert anchor not in expression
        for name, expression in rows.items():
            if name != 'agent_turn_lifecycle_check':
                assert anchor not in expression
                assert materialized._FUNCTION not in expression
                # Both halves must still dispatch malformed mixed-generation rows.
                assert 'dmb_surface_native_context_receipt_v1' in expression
                assert 'dmb_surface_native_execution_v1' in expression


def test_native_direct_sql_still_rejects_invalid_rows(lane, tmp_path, monkeypatch, application_state_dsn):
    _fresh_case(lane, tmp_path, monkeypatch, None, True, False, False)
    mutations = [
        "graph_context_receipt=NULL",
        "graph_context_execution=NULL",
        "graph_context_execution='42'::jsonb",
        "graph_context_receipt=jsonb_set(graph_context_receipt,'{schema}','\"foreign\"'::jsonb)",
        "graph_context_execution=jsonb_set(graph_context_execution,'{schema}','\"foreign\"'::jsonb)",
        "graph_context_receipt=graph_context_receipt-'provenance_sha256'",
        "submitted_intent_fingerprint_v2=NULL",
        "surface_id=NULL",
        "graph_context_execution=jsonb_set(graph_context_execution,'{events}','{}'::jsonb)",
    ]
    with psycopg.connect(application_state_dsn) as conn:
        turn_id = conn.execute("SELECT turn_id FROM agent.turn WHERE world_id=%s ORDER BY accepted_at DESC LIMIT 1",
            (lane.world.world_id,)).fetchone()[0]
        before = conn.execute('SELECT to_jsonb(t) FROM agent.turn t WHERE turn_id=%s', (turn_id,)).fetchone()[0]
        for change in mutations:
            with pytest.raises(psycopg.errors.CheckViolation):
                with conn.transaction():
                    conn.execute('UPDATE agent.turn SET ' + change + ' WHERE turn_id=%s', (turn_id,))
            assert conn.execute('SELECT to_jsonb(t) FROM agent.turn t WHERE turn_id=%s', (turn_id,)).fetchone()[0] == before


@pytest.fixture
def predecessor_database(monkeypatch):
    from uuid import uuid4
    from alembic import command
    from application_state.cli import alembic_config
    from application_state.config import APPLICATION_STATE_DSN_ENV
    from tests.application_state.conftest import (
        _admin_dsn, _create_database, _drop_database, _replace_database,
    )
    name = 'dungeonbuddy_app_state_test_' + uuid4().hex[:12]
    admin = _admin_dsn()
    _create_database(admin, name)
    try:
        dsn = _replace_database(admin, name)
        monkeypatch.setenv(APPLICATION_STATE_DSN_ENV, dsn)
        command.upgrade(alembic_config(), '20261108_0138')
        yield dsn
    finally:
        _drop_database(admin, name)


def _definitions(conn):
    owner = import_module('application_state.migrations.versions.20261108_0139_native_storage_owner')
    names = [owner._LIFECYCLE, *owner._DUPLICATES]
    return dict(conn.execute('SELECT conname,pg_get_expr(conbin,conrelid) FROM pg_constraint '
        "WHERE conrelid='agent.turn'::regclass AND conname=ANY(%s)", (names,)).fetchall())


def test_upgrade_keeps_lifecycle_and_legacy_row_exact(predecessor_database, monkeypatch):
    from alembic import command
    from application_state import cli
    from tests.application_state.test_rules_authority_migration import turn_fixture
    # The predecessor fixture owns its exact schema; no serving process is used.
    with monkeypatch.context() as patch:
        patch.setattr(cli, '_alembic_head', lambda: '20261108_0138')
        turn = turn_fixture()
    with psycopg.connect(predecessor_database) as conn:
        before = _definitions(conn)
        row_before = conn.execute('SELECT to_jsonb(t) FROM agent.turn t WHERE turn_id=%s', (turn.turn_id,)).fetchone()[0]
    command.upgrade(cli.alembic_config(), '20261108_0139')
    with psycopg.connect(predecessor_database) as conn:
        after = _definitions(conn)
        row_after = conn.execute('SELECT to_jsonb(t) FROM agent.turn t WHERE turn_id=%s', (turn.turn_id,)).fetchone()[0]
    assert before['agent_turn_lifecycle_check'] == after['agent_turn_lifecycle_check']
    assert row_before == row_after
    for name in before:
        if name != 'agent_turn_lifecycle_check':
            assert len(after[name]) < len(before[name])


def test_unmatched_predicate_refuses_upgrade_without_partial_changes(predecessor_database):
    from alembic import command
    from application_state import cli
    with psycopg.connect(predecessor_database) as conn:
        conn.execute('ALTER TABLE agent.turn DROP CONSTRAINT agent_turn_graph_completion_check')
        conn.execute('ALTER TABLE agent.turn ADD CONSTRAINT agent_turn_graph_completion_check CHECK (TRUE)')
    with psycopg.connect(predecessor_database) as conn:
        before = _definitions(conn)
    with pytest.raises(RuntimeError, match='Native storage predicate changed'):
        command.upgrade(cli.alembic_config(), '20261108_0139')
    with psycopg.connect(predecessor_database) as conn:
        assert _definitions(conn) == before
        assert conn.execute('SELECT version_num FROM application_state.schema_migrations').fetchone() == ('20261108_0138',)
        assert conn.execute("SELECT to_regclass('pg_temp.dmb_native_storage_shape')").fetchone() == (None,)


def test_mid_ddl_failure_rolls_back_all_constraints(predecessor_database):
    from alembic import command
    from application_state import cli
    from sqlalchemy import event
    from sqlalchemy.engine import Engine
    with psycopg.connect(predecessor_database) as conn:
        before = _definitions(conn)
    seen = []
    def interrupt(conn, cursor, statement, parameters, context, executemany):
        if statement.startswith('ALTER TABLE agent.turn ADD CONSTRAINT "agent_turn_graph_context_receipt_check"'):
            seen.append(statement)
            raise RuntimeError('injected after first constraint replacement')
    event.listen(Engine, 'after_cursor_execute', interrupt)
    try:
        with pytest.raises(RuntimeError, match='injected after first'):
            command.upgrade(cli.alembic_config(), '20261108_0139')
    finally:
        event.remove(Engine, 'after_cursor_execute', interrupt)
    assert len(seen) == 1
    with psycopg.connect(predecessor_database) as conn:
        assert _definitions(conn) == before
        assert conn.execute('SELECT version_num FROM application_state.schema_migrations').fetchone() == ('20261108_0138',)


def test_update_comparison_preserves_row_and_reports_cost(
    lane, tmp_path, monkeypatch, application_state_dsn, predecessor_database, record_property,
):
    import json
    from alembic import command
    from application_state import cli
    from application_state.config import APPLICATION_STATE_DSN_ENV
    with psycopg.connect(predecessor_database) as conn:
        old = _definitions(conn)
    # This historical experiment qualifies migration139, not later owners.
    command.upgrade(cli.alembic_config(), '20261108_0139')
    with monkeypatch.context() as patch:
        patch.setenv(APPLICATION_STATE_DSN_ENV, predecessor_database)
        patch.setattr(cli, '_alembic_head', lambda: '20261108_0139')
        _fresh_case(lane, tmp_path, patch, None, True, False, False)
    measurements = []
    with psycopg.connect(predecessor_database) as conn:
        current = _definitions(conn)
        assert current['agent_turn_lifecycle_check'] == old['agent_turn_lifecycle_check']
        turn_id = conn.execute('SELECT turn_id FROM agent.turn WHERE world_id=%s ORDER BY accepted_at DESC LIMIT 1',
            (lane.world.world_id,)).fetchone()[0]
        row = conn.execute('SELECT to_jsonb(t) FROM agent.turn t WHERE turn_id=%s', (turn_id,)).fetchone()[0]
        owner = import_module('application_state.migrations.versions.20261108_0139_native_storage_owner')
        # Fixed alternating order; DDL/validation is outside UPDATE measurements.
        for arm, definitions in [('old', old), ('single_owner', current), ('single_owner', current), ('old', old)]:
            for name in owner._DUPLICATES:
                conn.execute(f'ALTER TABLE agent.turn DROP CONSTRAINT "{name}"')
                conn.execute(f'ALTER TABLE agent.turn ADD CONSTRAINT "{name}" CHECK ({definitions[name]})')
            with conn.transaction(force_rollback=True):
                plan = conn.execute('EXPLAIN (ANALYZE,FORMAT JSON,BUFFERS) UPDATE agent.turn '
                    'SET graph_context_execution=graph_context_execution WHERE turn_id=%s', (turn_id,)).fetchone()[0][0]
                measurements.append({'arm': arm, 'planning_ms': plan['Planning Time'], 'execution_ms': plan['Execution Time']})
            assert conn.execute('SELECT to_jsonb(t) FROM agent.turn t WHERE turn_id=%s', (turn_id,)).fetchone()[0] == row
        for name in owner._DUPLICATES:
            conn.execute(f'ALTER TABLE agent.turn DROP CONSTRAINT "{name}"')
            conn.execute(f'ALTER TABLE agent.turn ADD CONSTRAINT "{name}" CHECK ({current[name]})')
        assert _definitions(conn) == current
    record_property('native_storage_update_timing', json.dumps(measurements))


# Materialized JSON owner: current migration qualification.
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
    command.upgrade(cli.alembic_config(), '20261109_0142')
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
