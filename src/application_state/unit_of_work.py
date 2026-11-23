"""One user-visible commit = one PostgreSQL transaction."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from os import getpid
from threading import Lock

import psycopg
from psycopg.rows import tuple_row
from sqlalchemy import event
from sqlalchemy.pool import QueuePool

from application_state.config import load_runtime_dsn
from application_state.engine import connect

_pool_lock = Lock()
_pool_owner: tuple[int, str, QueuePool] | None = None


def _new_pool(target: str) -> QueuePool:
    def open_connection() -> psycopg.Connection:
        conn = connect(target)
        # DISCARD ALL invalidates prepared statements on the server.
        conn.prepare_threshold = None
        return conn

    pool = QueuePool(open_connection, pool_size=4, max_overflow=-1, reset_on_return=None)

    @event.listens_for(pool, "reset")
    def reset(conn, _record, state):
        if state.terminate_only:
            return
        conn.rollback()
        conn.autocommit = True
        conn.execute("DISCARD ALL")
        conn.autocommit = False
        conn.row_factory = tuple_row
        conn.isolation_level = None
        conn.read_only = None
        conn.deferrable = None
        conn.prepare_threshold = None

    return pool


def _pool_for(target: str) -> QueuePool:
    global _pool_owner
    pid = getpid()
    with _pool_lock:
        previous = _pool_owner
        if previous is not None and previous[:2] == (pid, target):
            return previous[2]
        pool = _new_pool(target)
        _pool_owner = (pid, target, pool)
        if previous is not None and previous[0] == pid:
            previous[2].dispose()
        return pool


@contextmanager
def unit_of_work(dsn: str | None = None) -> Iterator[psycopg.Connection]:
    target = dsn if dsn is not None else load_runtime_dsn()
    lease = _pool_for(target).connect()
    try:
        conn = lease.driver_connection
        with conn.transaction():
            yield conn
    finally:
        lease.close()
