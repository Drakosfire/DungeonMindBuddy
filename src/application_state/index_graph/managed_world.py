"""Register a guest's existing native Graph as a managed Buddy World.

This internal primitive does not authenticate a request or expose a route.  Its
caller must have resolved the session credential at the HTTP boundary first.
"""
from __future__ import annotations

from uuid import UUID

import psycopg

from application_state.config import load_runtime_dsn
from application_state.errors import ApplicationStateConflictError, ApplicationStateUnavailableError
from application_state.index_graph.sessions import IndexGraphSession
from application_state.index_graph.guest_documents import seed_guest_documents
from application_state.index_graph.guest_apprentice_plan import seed_guest_apprentice_plan
from application_state.index_graph.guest_apprentice_combat import seed_guest_apprentice_combat
from application_state.unit_of_work import unit_of_work
from application_state.world_catalog import service as catalog
from application_state.world_catalog.types import NativeGraphBindingRecord, WorldContainerRecord


def bind_initialized_guest_world(session: IndexGraphSession) -> catalog.StoredWorld:
    """Recover or create the exact catalog binding for an active session.

    The native identity comes exclusively from the session's persisted copy
    receipt, never from a caller-provided World selector. The session row lock
    serializes this operation with reset, which expires the old credential.
    """
    try:
        canonical = str(UUID(session.session_id))
    except (ValueError, TypeError, AttributeError) as exc:
        raise ApplicationStateConflictError("Invalid guest session") from exc
    if canonical != session.session_id:
        raise ApplicationStateConflictError("Invalid guest session")
    world_id = f"guest-{UUID(canonical).hex}"
    subject = f"guest-session:{canonical}"
    try:
        with unit_of_work(load_runtime_dsn()) as conn:
            row = conn.execute(
                "SELECT allocation_id, created_at FROM application_state.index_graph_sessions "
                "WHERE session_id = %s::uuid AND expires_at > clock_timestamp() FOR UPDATE",
                (canonical,),
            ).fetchone()
            if row is None or row[0] != session.allocation_id:
                raise ApplicationStateConflictError("Guest session is no longer active")
            values = dict(conn.execute(
                "SELECT key, value FROM application_state.index_graph_bindings "
                "WHERE session_id = %s::uuid AND key IN ('space_id', 'genesis_revision_id')",
                (canonical,),
            ).fetchall())
            native_id, revision = values.get("space_id"), values.get("genesis_revision_id")
            if not native_id or not revision:
                raise ApplicationStateConflictError("Guest Graph copy is not initialized")
            created_at = row[1].isoformat()
            expected = catalog._validated_record(WorldContainerRecord(
                world_id=world_id,
                name="Sizzek World",
                source_root_relpath=catalog.world_source_root_relpath(world_id),
                created_at=created_at,
                owner_subject=subject,
                native_graph_binding=NativeGraphBindingRecord(
                    native_world_id=native_id, status="active", binding_version=1,
                    validated_at=created_at, validated_head_revision_id=revision,
                ),
            ))
            catalog._lock_world_revision(conn, world_id)
            records = catalog._records(conn, world_id=world_id)
            if records:
                if records[0].record != expected:
                    raise ApplicationStateConflictError("Guest World binding conflicts with saved metadata")
                seed_guest_documents(conn, session_id=canonical, world_id=world_id)
                seed_guest_apprentice_plan(conn, session_id=canonical, world_id=world_id)
                seed_guest_apprentice_combat(conn, session_id=canonical, world_id=world_id)
                return records[0]
            catalog._write(conn, expected, revision=1)
            seed_guest_documents(conn, session_id=canonical, world_id=world_id)
            seed_guest_apprentice_plan(conn, session_id=canonical, world_id=world_id)
            seed_guest_apprentice_combat(conn, session_id=canonical, world_id=world_id)
            return catalog.StoredWorld(expected, 1)
    except psycopg.IntegrityError as exc:
        raise ApplicationStateConflictError("Guest World binding conflicts with saved metadata") from exc
    except psycopg.Error as exc:
        raise ApplicationStateUnavailableError("Guest World binding is unavailable") from exc
