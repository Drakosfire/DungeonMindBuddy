"""Verify lease isolation and transaction boundaries against PostgreSQL."""

import subprocess
import sys

import psycopg
import pytest
from psycopg.rows import dict_row

from application_state.engine import connect
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



def test_idle_backend_is_replaced_before_transaction(application_state_dsn):
    with unit_of_work(application_state_dsn) as conn:
        old_pid = conn.execute("SELECT pg_backend_pid()").fetchone()[0]

    with connect(application_state_dsn) as admin:
        assert admin.execute("SELECT pg_terminate_backend(%s, 1000)", (old_pid,)).fetchone() == (True,)

    with unit_of_work(application_state_dsn) as conn:
        assert conn.execute("SELECT pg_backend_pid()").fetchone()[0] != old_pid

def test_child_can_create_pool_with_parent_guard_held():
    subprocess.run(
        [sys.executable, "-B", "-c", """
import os
from importlib import import_module

owner = import_module("application_state.unit_of_work")
original = owner._pool_for("unused-parent-target")
with owner._pool_lock:
    pid = os.fork()
    if pid == 0:
        assert owner._pool_for("unused-parent-target") is not original
        os._exit(0)
    assert os.waitpid(pid, 0)[1] == 0
assert owner._pool_for("unused-parent-target") is original
"""],
        check=True,
        timeout=10,
    )
