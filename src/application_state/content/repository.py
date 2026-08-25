"""Content SQL for admitted kinds. Repositories do not commit."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

import psycopg
from psycopg.rows import dict_row

from application_state.content.types import WorkObject, WorkRevision, WorkingCopy
from application_state.errors import ApplicationStateIntegrityError

_WORK_OBJECT_COLUMNS = """
    work_object_id, kind, campaign_id, world_id, title, target_session,
    target_relpath, status, current_revision_id, object_revision, created_at, updated_at
"""


def _now() -> datetime:
    return datetime.now(UTC)


def _work_object_from_row(row: dict) -> WorkObject:
    return WorkObject.model_validate(row)


def insert_work_object(conn: psycopg.Connection, obj: WorkObject) -> WorkObject:
    conn.execute(
        f"""
        INSERT INTO content.work_object ({_WORK_OBJECT_COLUMNS})
        VALUES (
            %(work_object_id)s, %(kind)s, %(campaign_id)s, %(world_id)s, %(title)s,
            %(target_session)s, %(target_relpath)s, %(status)s, %(current_revision_id)s,
            %(object_revision)s, %(created_at)s, %(updated_at)s
        )
        """,
        obj.model_dump(),
    )
    loaded = get_work_object(conn, obj.work_object_id)
    if loaded is None:
        raise ApplicationStateIntegrityError("work_object insert did not persist")
    return loaded


def get_work_object(conn: psycopg.Connection, work_object_id: UUID) -> WorkObject | None:
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            f"SELECT {_WORK_OBJECT_COLUMNS} FROM content.work_object WHERE work_object_id = %s",
            (work_object_id,),
        )
        row = cur.fetchone()
    return None if row is None else _work_object_from_row(row)


def lock_work_object(conn: psycopg.Connection, work_object_id: UUID) -> WorkObject | None:
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            f"""
            SELECT {_WORK_OBJECT_COLUMNS}
            FROM content.work_object
            WHERE work_object_id = %s
            FOR UPDATE
            """,
            (work_object_id,),
        )
        row = cur.fetchone()
    return None if row is None else _work_object_from_row(row)


def list_work_objects(
    conn: psycopg.Connection,
    *,
    campaign_id: str | None = None,
    status: str | None = "active",
) -> list[WorkObject]:
    clauses = ["kind = 'plan'"]
    params: list[object] = []
    if status is not None:
        clauses.append("status = %s")
        params.append(status)
    if campaign_id is not None:
        clauses.append("campaign_id = %s")
        params.append(campaign_id)
    sql = f"""
        SELECT {_WORK_OBJECT_COLUMNS}
        FROM content.work_object
        WHERE {' AND '.join(clauses)}
        ORDER BY updated_at DESC
    """
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(sql, params)
        rows = cur.fetchall()
    return [_work_object_from_row(row) for row in rows]


def update_work_object(
    conn: psycopg.Connection,
    obj: WorkObject,
    *,
    expected_object_revision: int,
) -> WorkObject | None:
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            f"""
            UPDATE content.work_object
            SET
                title = %(title)s,
                target_session = %(target_session)s,
                target_relpath = %(target_relpath)s,
                status = %(status)s,
                current_revision_id = %(current_revision_id)s,
                object_revision = %(object_revision)s,
                updated_at = %(updated_at)s
            WHERE work_object_id = %(work_object_id)s
              AND object_revision = %(expected_object_revision)s
            RETURNING {_WORK_OBJECT_COLUMNS}
            """,
            {
                **obj.model_dump(),
                "expected_object_revision": expected_object_revision,
            },
        )
        row = cur.fetchone()
    return None if row is None else _work_object_from_row(row)


def insert_work_revision(conn: psycopg.Connection, revision: WorkRevision) -> WorkRevision:
    conn.execute(
        """
        INSERT INTO content.work_revision (
            work_revision_id, work_object_id, revision_n, markdown, content_sha256, created_at
        )
        VALUES (
            %(work_revision_id)s, %(work_object_id)s, %(revision_n)s,
            %(markdown)s, %(content_sha256)s, %(created_at)s
        )
        """,
        revision.model_dump(),
    )
    loaded = get_work_revision(conn, revision.work_revision_id)
    if loaded is None:
        raise ApplicationStateIntegrityError("work_revision insert did not persist")
    return loaded


def get_work_revision(conn: psycopg.Connection, work_revision_id: UUID) -> WorkRevision | None:
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            """
            SELECT work_revision_id, work_object_id, revision_n, markdown, content_sha256, created_at
            FROM content.work_revision
            WHERE work_revision_id = %s
            """,
            (work_revision_id,),
        )
        row = cur.fetchone()
    return None if row is None else WorkRevision.model_validate(row)


def get_work_revision_by_n(
    conn: psycopg.Connection, work_object_id: UUID, revision_n: int
) -> WorkRevision | None:
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            """
            SELECT work_revision_id, work_object_id, revision_n, markdown, content_sha256, created_at
            FROM content.work_revision
            WHERE work_object_id = %s AND revision_n = %s
            """,
            (work_object_id, revision_n),
        )
        row = cur.fetchone()
    return None if row is None else WorkRevision.model_validate(row)


def next_revision_n(conn: psycopg.Connection, work_object_id: UUID) -> int:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT COALESCE(MAX(revision_n), 0) + 1
            FROM content.work_revision
            WHERE work_object_id = %s
            """,
            (work_object_id,),
        )
        row = cur.fetchone()
    return int(row[0]) if row is not None else 1


def upsert_working_copy(conn: psycopg.Connection, copy: WorkingCopy) -> WorkingCopy:
    conn.execute(
        """
        INSERT INTO content.working_copy (
            work_object_id, markdown, content_sha256, base_revision_id,
            working_copy_revision, updated_at
        )
        VALUES (
            %(work_object_id)s, %(markdown)s, %(content_sha256)s, %(base_revision_id)s,
            %(working_copy_revision)s, %(updated_at)s
        )
        ON CONFLICT (work_object_id) DO UPDATE SET
            markdown = EXCLUDED.markdown,
            content_sha256 = EXCLUDED.content_sha256,
            base_revision_id = EXCLUDED.base_revision_id,
            working_copy_revision = EXCLUDED.working_copy_revision,
            updated_at = EXCLUDED.updated_at
        """,
        copy.model_dump(),
    )
    loaded = get_working_copy(conn, copy.work_object_id)
    if loaded is None:
        raise ApplicationStateIntegrityError("working_copy upsert did not persist")
    return loaded


def get_working_copy(conn: psycopg.Connection, work_object_id: UUID) -> WorkingCopy | None:
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            """
            SELECT work_object_id, markdown, content_sha256, base_revision_id,
                   working_copy_revision, updated_at
            FROM content.working_copy
            WHERE work_object_id = %s
            """,
            (work_object_id,),
        )
        row = cur.fetchone()
    return None if row is None else WorkingCopy.model_validate(row)


def now_utc() -> datetime:
    return _now()
