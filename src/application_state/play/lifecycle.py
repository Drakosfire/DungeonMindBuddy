"""Recoverable World Play session lifecycle, serialized with existing Run writes."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from application_state.cli import assert_at_head
from application_state.config import load_runtime_dsn
from application_state.errors import (
    ApplicationStateConflictError,
    ApplicationStateNotFoundError,
    ApplicationStateValidationError,
)
from application_state.unit_of_work import unit_of_work


def _world_id(value: str) -> str:
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        raise ApplicationStateValidationError(
            "world_id must be non-empty and canonical"
        )
    return value


def _positive(value: int, name: str, *, zero: bool = False) -> int:
    if (
        not isinstance(value, int)
        or isinstance(value, bool)
        or value < (0 if zero else 1)
    ):
        raise ApplicationStateValidationError(f"{name} is invalid")
    return value


def current_world_play_revision(conn, run_id: UUID) -> int:
    row = conn.execute(
        "SELECT head_revision FROM play.run_edition WHERE run_id=%s", (run_id,)
    ).fetchone()
    return 0 if row is None else row[0]


def list_trashed_world_play_sessions(*, world_id: str) -> list[dict]:
    world = _world_id(world_id)
    dsn = load_runtime_dsn()
    assert_at_head(dsn=dsn)
    with unit_of_work(dsn) as conn:
        rows = conn.execute(
            """
            SELECT r.run_id, COALESCE(w.title, 'Play session'), r.run_revision,
                   r.updated_at, COALESCE(e.head_revision, 0), r.created_at
            FROM play.run r
            LEFT JOIN content.work_object w ON w.work_object_id=r.playable_work_object_id
            LEFT JOIN play.run_edition e ON e.run_id=r.run_id
            WHERE r.world_id=%s AND r.lifecycle_status='trashed'
            ORDER BY r.updated_at DESC,r.run_id
        """,
            (world,),
        ).fetchall()
    return [
        {
            "kind": "session",
            "id": str(row[0]),
            "title": f"{row[1]} — {row[5].date().isoformat()}",
            "status": "trashed",
            "revision": row[2],
            "surface": "play",
            "updated_at": row[3].astimezone(UTC).isoformat().replace("+00:00", "Z"),
            "content_revision": row[4],
        }
        for row in rows
    ]


def set_world_play_session_trash(
    *,
    world_id: str,
    run_id: UUID,
    expected_revision: int,
    expected_content_revision: int,
    restore: bool,
) -> dict:
    world = _world_id(world_id)
    expected_run = _positive(expected_revision, "expected_revision")
    expected_content = _positive(
        expected_content_revision, "expected_content_revision", zero=True
    )
    dsn = load_runtime_dsn()
    assert_at_head(dsn=dsn)
    with unit_of_work(dsn) as conn:
        run = conn.execute(
            "SELECT r.world_id,r.run_revision,r.lifecycle_status,r.updated_at,COALESCE(w.title,'Play session'),r.created_at "
            "FROM play.run r LEFT JOIN content.work_object w ON w.work_object_id=r.playable_work_object_id "
            "WHERE r.run_id=%s FOR UPDATE OF r",
            (run_id,),
        ).fetchone()
        if run is None or run[0] != world:
            raise ApplicationStateNotFoundError("Play session not found in this World")
        if run[1] != expected_run:
            raise ApplicationStateConflictError("Play session revision changed")
        current_content_revision = current_world_play_revision(conn, run_id)
        if current_content_revision != expected_content:
            raise ApplicationStateConflictError("Play session content revision changed")
        wanted = "active" if restore else "trashed"
        if run[2] == wanted:
            raise ApplicationStateConflictError(
                "Play session is already restored"
                if restore
                else "Play session is already in Trash"
            )
        if run[2] != ("trashed" if restore else "active"):
            raise ApplicationStateConflictError("Play session lifecycle changed")
        updated_at = datetime.now(UTC)
        updated = conn.execute(
            """
            UPDATE play.run
            SET lifecycle_status=%s,run_revision=run_revision+1,updated_at=%s
            WHERE run_id=%s AND world_id=%s AND run_revision=%s AND lifecycle_status=%s
            RETURNING run_revision,updated_at
        """,
            (wanted, updated_at, run_id, world, expected_run, run[2]),
        ).fetchone()
        if updated is None:
            raise ApplicationStateConflictError("Play session lifecycle changed")
        if not restore:
            conn.execute(
                "DELETE FROM play.active_run WHERE scope_key='local' AND run_id=%s",
                (run_id,),
            )
        return {
            "kind": "session",
            "id": str(run_id),
            "title": f"{run[4]} — {run[5].date().isoformat()}",
            "status": wanted,
            "revision": updated[0],
            "surface": "play",
            "updated_at": updated[1].astimezone(UTC).isoformat().replace("+00:00", "Z"),
            "content_revision": current_content_revision,
        }
