"""Play SQL for run / run_manifest. Repositories do not commit."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from application_state.errors import ApplicationStateIntegrityError
from application_state.play.types import PlayActiveRun, PlayRun, PlayRunManifest

LOCAL_ACTIVE_RUN_SCOPE = "local"

_ACTIVE_RUN_COLUMNS = "run_id, selected_at"

_RUN_COLUMNS = """
    run_id, campaign_id, playable_work_object_id, playable_revision_n,
    playable_work_revision_id, playable_content_sha256, run_revision, progress,
    rebased_from_run_revision, created_at, updated_at
"""

_MANIFEST_COLUMNS = """
    run_id, playable_work_object_id, playable_revision_n, playable_work_revision_id,
    playable_content_sha256, manifest, sealed_at
"""


def now_utc() -> datetime:
    return datetime.now(UTC)


def _run_from_row(row: dict) -> PlayRun:
    return PlayRun.model_validate(row)


def _manifest_from_row(row: dict) -> PlayRunManifest:
    return PlayRunManifest.model_validate(row)


def insert_run(conn: psycopg.Connection, run: PlayRun) -> PlayRun:
    conn.execute(
        f"""
        INSERT INTO play.run ({_RUN_COLUMNS})
        VALUES (
            %(run_id)s, %(campaign_id)s, %(playable_work_object_id)s,
            %(playable_revision_n)s, %(playable_work_revision_id)s,
            %(playable_content_sha256)s, %(run_revision)s, %(progress)s,
            %(rebased_from_run_revision)s, %(created_at)s, %(updated_at)s
        )
        """,
        {**run.model_dump(), "progress": Jsonb(run.progress)},
    )
    loaded = get_run(conn, run.run_id)
    if loaded is None:
        raise ApplicationStateIntegrityError("play.run insert did not persist")
    return loaded


def get_run(conn: psycopg.Connection, run_id: UUID) -> PlayRun | None:
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            f"SELECT {_RUN_COLUMNS} FROM play.run WHERE run_id = %s",
            (run_id,),
        )
        row = cur.fetchone()
    return None if row is None else _run_from_row(row)


def lock_run(conn: psycopg.Connection, run_id: UUID) -> PlayRun | None:
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            f"""
            SELECT {_RUN_COLUMNS}
            FROM play.run
            WHERE run_id = %s
            FOR UPDATE
            """,
            (run_id,),
        )
        row = cur.fetchone()
    return None if row is None else _run_from_row(row)


def list_runs(
    conn: psycopg.Connection,
    *,
    campaign_id: str | None = None,
    playable_work_object_id: UUID | None = None,
) -> list[PlayRun]:
    clauses: list[str] = []
    params: list[object] = []
    if campaign_id is not None:
        clauses.append("campaign_id = %s")
        params.append(campaign_id)
    if playable_work_object_id is not None:
        clauses.append("playable_work_object_id = %s")
        params.append(playable_work_object_id)
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    sql = f"""
        SELECT {_RUN_COLUMNS}
        FROM play.run
        {where}
        ORDER BY created_at DESC, run_id ASC
    """
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(sql, params)
        rows = cur.fetchall()
    return [_run_from_row(row) for row in rows]


def insert_manifest(conn: psycopg.Connection, manifest: PlayRunManifest) -> PlayRunManifest:
    conn.execute(
        f"""
        INSERT INTO play.run_manifest ({_MANIFEST_COLUMNS})
        VALUES (
            %(run_id)s, %(playable_work_object_id)s, %(playable_revision_n)s,
            %(playable_work_revision_id)s, %(playable_content_sha256)s,
            %(manifest)s, %(sealed_at)s
        )
        """,
        {**manifest.model_dump(), "manifest": Jsonb(manifest.manifest)},
    )
    loaded = get_manifest(conn, manifest.run_id)
    if loaded is None:
        raise ApplicationStateIntegrityError("play.run_manifest insert did not persist")
    return loaded


def get_manifest(conn: psycopg.Connection, run_id: UUID) -> PlayRunManifest | None:
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            f"SELECT {_MANIFEST_COLUMNS} FROM play.run_manifest WHERE run_id = %s",
            (run_id,),
        )
        row = cur.fetchone()
    return None if row is None else _manifest_from_row(row)


def replace_manifest(conn: psycopg.Connection, manifest: PlayRunManifest) -> PlayRunManifest:
    conn.execute(
        f"""
        INSERT INTO play.run_manifest ({_MANIFEST_COLUMNS})
        VALUES (
            %(run_id)s, %(playable_work_object_id)s, %(playable_revision_n)s,
            %(playable_work_revision_id)s, %(playable_content_sha256)s,
            %(manifest)s, %(sealed_at)s
        )
        ON CONFLICT (run_id) DO UPDATE SET
            playable_work_object_id = EXCLUDED.playable_work_object_id,
            playable_revision_n = EXCLUDED.playable_revision_n,
            playable_work_revision_id = EXCLUDED.playable_work_revision_id,
            playable_content_sha256 = EXCLUDED.playable_content_sha256,
            manifest = EXCLUDED.manifest,
            sealed_at = EXCLUDED.sealed_at
        """,
        {**manifest.model_dump(), "manifest": Jsonb(manifest.manifest)},
    )
    loaded = get_manifest(conn, manifest.run_id)
    if loaded is None:
        raise ApplicationStateIntegrityError("play.run_manifest replace did not persist")
    return loaded


def cas_replace_progress(
    conn: psycopg.Connection,
    *,
    run_id: UUID,
    expected_run_revision: int,
    progress: dict,
    updated_at: datetime,
) -> PlayRun | None:
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            f"""
            UPDATE play.run
            SET progress = %(progress)s,
                run_revision = run_revision + 1,
                updated_at = %(updated_at)s,
                rebased_from_run_revision = NULL
            WHERE run_id = %(run_id)s
              AND run_revision = %(expected_run_revision)s
            RETURNING {_RUN_COLUMNS}
            """,
            {
                "run_id": run_id,
                "expected_run_revision": expected_run_revision,
                "progress": Jsonb(progress),
                "updated_at": updated_at,
            },
        )
        row = cur.fetchone()
    return None if row is None else _run_from_row(row)


def _active_run_from_row(row: dict) -> PlayActiveRun:
    return PlayActiveRun.model_validate(row)


def get_active_run(conn: psycopg.Connection) -> PlayActiveRun | None:
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            f"""
            SELECT {_ACTIVE_RUN_COLUMNS}
            FROM play.active_run
            WHERE scope_key = %s
            """,
            (LOCAL_ACTIVE_RUN_SCOPE,),
        )
        row = cur.fetchone()
    return None if row is None else _active_run_from_row(row)


def lock_active_run(conn: psycopg.Connection) -> PlayActiveRun | None:
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            f"""
            SELECT {_ACTIVE_RUN_COLUMNS}
            FROM play.active_run
            WHERE scope_key = %s
            FOR UPDATE
            """,
            (LOCAL_ACTIVE_RUN_SCOPE,),
        )
        row = cur.fetchone()
    return None if row is None else _active_run_from_row(row)


def upsert_active_run(
    conn: psycopg.Connection,
    *,
    run_id: UUID,
    selected_at: datetime,
) -> PlayActiveRun:
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            f"""
            INSERT INTO play.active_run (scope_key, run_id, selected_at)
            VALUES (%(scope_key)s, %(run_id)s, %(selected_at)s)
            ON CONFLICT (scope_key) DO UPDATE SET
                run_id = EXCLUDED.run_id,
                selected_at = EXCLUDED.selected_at
            RETURNING {_ACTIVE_RUN_COLUMNS}
            """,
            {
                "scope_key": LOCAL_ACTIVE_RUN_SCOPE,
                "run_id": run_id,
                "selected_at": selected_at,
            },
        )
        row = cur.fetchone()
    if row is None:
        raise ApplicationStateIntegrityError("play.active_run upsert did not persist")
    return _active_run_from_row(row)


def delete_active_run(conn: psycopg.Connection) -> None:
    conn.execute(
        "DELETE FROM play.active_run WHERE scope_key = %s",
        (LOCAL_ACTIVE_RUN_SCOPE,),
    )


def update_run_binding(
    conn: psycopg.Connection,
    *,
    run_id: UUID,
    expected_run_revision: int,
    playable_revision_n: int,
    playable_work_revision_id: UUID,
    playable_content_sha256: str,
    rebased_from_run_revision: int,
    updated_at: datetime,
) -> PlayRun | None:
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            f"""
            UPDATE play.run
            SET playable_revision_n = %(playable_revision_n)s,
                playable_work_revision_id = %(playable_work_revision_id)s,
                playable_content_sha256 = %(playable_content_sha256)s,
                run_revision = run_revision + 1,
                rebased_from_run_revision = %(rebased_from_run_revision)s,
                updated_at = %(updated_at)s
            WHERE run_id = %(run_id)s
              AND run_revision = %(expected_run_revision)s
            RETURNING {_RUN_COLUMNS}
            """,
            {
                "run_id": run_id,
                "expected_run_revision": expected_run_revision,
                "playable_revision_n": playable_revision_n,
                "playable_work_revision_id": playable_work_revision_id,
                "playable_content_sha256": playable_content_sha256,
                "rebased_from_run_revision": rebased_from_run_revision,
                "updated_at": updated_at,
            },
        )
        row = cur.fetchone()
    return None if row is None else _run_from_row(row)
