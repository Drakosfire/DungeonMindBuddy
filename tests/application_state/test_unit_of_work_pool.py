"""Verify lease isolation and transaction boundaries against PostgreSQL."""

import psycopg
import pytest
from psycopg.rows import dict_row

from application_state.unit_of_work import unit_of_work


def test_reused_connection_resets_driver_and_server_state(application_state_dsn):
    with unit_of_work(application_state_dsn) as first:
        first.row_factory = dict_row
        pid = first.execute("SELECT pg_backend_pid() AS pid").fetchone()["pid"]
        first.execute("SELECT set_config('dmb.pool_probe', 'previous lease', false)")

    with unit_of_work(application_state_dsn) as second:
        assert second.execute("SELECT pg_backend_pid()").fetchone() == (pid,)
        assert second.execute(
            "SELECT nullif(current_setting('dmb.pool_probe', true), '')"
        ).fetchone() == (None,)


def test_failed_transaction_is_rolled_back_before_reuse(application_state_dsn):
    with unit_of_work(application_state_dsn) as conn:
        pid = conn.execute("SELECT pg_backend_pid()").fetchone()[0]

    with pytest.raises(psycopg.errors.DivisionByZero):
        with unit_of_work(application_state_dsn) as conn:
            conn.execute("CREATE TABLE pool_rollback_probe (value integer)")
            conn.execute("SELECT 1 / 0")

    with unit_of_work(application_state_dsn) as conn:
        assert conn.execute("SELECT pg_backend_pid()").fetchone() == (pid,)
        assert conn.execute("SELECT to_regclass('pool_rollback_probe')").fetchone() == (None,)
