"""Database-owner qualification for shared native predicate factoring."""
from importlib import import_module

import psycopg
import pytest

from tests.test_native_plan_assertions import lane as lane
from tests.test_surface_native_build_ordinary import _fresh_case


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
