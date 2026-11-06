"""Durable connected-page operation journal; Content remains the page owner."""
from contextlib import contextmanager
from uuid import UUID

from psycopg.types.json import Jsonb

from application_state.cli import assert_at_head
from application_state.config import load_runtime_dsn
from application_state.engine import connect


class OperationConflict(ValueError):
    pass


class OperationJournal:
    def __init__(self, connection, operation_id):
        self.connection = connection
        self.operation_id = str(UUID(str(operation_id)))

    def read(self):
        row = self.connection.execute(
            "SELECT payload FROM content.connected_page_operation WHERE operation_id=%s",
            (self.operation_id,),
        ).fetchone()
        return row[0] if row else None

    def save(self, state):
        if str(UUID(state["intent"]["operation_id"])) != self.operation_id:
            raise OperationConflict("Operation identity changed")
        row = self.connection.execute(
            """INSERT INTO content.connected_page_operation AS existing
               (operation_id, world_id, page_id, payload) VALUES (%s,%s,%s,%s)
               ON CONFLICT (operation_id) DO UPDATE SET payload=EXCLUDED.payload
               WHERE existing.world_id=EXCLUDED.world_id
                 AND existing.page_id=EXCLUDED.page_id
                 AND existing.payload->>'intent_sha256'=EXCLUDED.payload->>'intent_sha256'
               RETURNING operation_id""",
            (self.operation_id, state["intent"]["world_id"], state["page_id"], Jsonb(state)),
        ).fetchone()
        if row is None:
            raise OperationConflict("Operation already belongs to another page request")


@contextmanager
def locked_operation(operation_id):
    """Serialize across workers, committing each phase before downstream work.

    A dedicated autocommit connection holds the session lock, not a transaction
    spanning the separate page and Graph owners. Closing it releases the lock
    even after a lost response or process failure.
    """
    dsn = load_runtime_dsn()
    assert_at_head(dsn=dsn)
    with connect(dsn) as connection:
        connection.autocommit = True
        key = "connected-page:" + str(UUID(str(operation_id)))
        connection.execute("SELECT pg_advisory_lock(hashtextextended(%s,0))", (key,))
        try:
            yield OperationJournal(connection, operation_id)
        finally:
            connection.execute("SELECT pg_advisory_unlock(hashtextextended(%s,0))", (key,))
