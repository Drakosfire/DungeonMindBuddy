"""One user-visible commit = one PostgreSQL transaction."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

import psycopg

from application_state.engine import connect


@contextmanager
def unit_of_work(dsn: str | None = None) -> Iterator[psycopg.Connection]:
    conn = connect(dsn)
    try:
        with conn.transaction():
            yield conn
    finally:
        conn.close()
