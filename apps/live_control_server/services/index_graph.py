"""Compose one Buddy index guest session with its native graph authority."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
import os

from application_state.index_graph.sessions import (
    SESSION_TTL, IndexGraphSession, hosted_guest_graph_enabled,
)
from application_state.index_graph.store import IndexGraphStore
from apps.live_control_server.integrations.dungeonmind.native_registry_source import (
    repository,
)
from apps.live_control_server.native_graph_demo import NativeGraphDemoService
from dungeonmind.domain.errors import PersistenceUnavailableError


@contextmanager
def open_index_graph_service(
    session: IndexGraphSession,
) -> Iterator[NativeGraphDemoService]:
    """Open a service bound only to this server-owned session and allocation."""
    store = IndexGraphStore(session.session_id, session.allocation_id)
    service: NativeGraphDemoService | None = None
    try:
        snapshot = None
        if hosted_guest_graph_enabled():
            source_space = os.environ.get("DMB_GUEST_GRAPH_SOURCE_SPACE", "").strip()
            source_revision = os.environ.get("DMB_GUEST_GRAPH_SOURCE_REVISION", "").strip()
            if not source_space or not source_revision:
                raise PersistenceUnavailableError("Guest World snapshot is not configured")
            snapshot = (source_space, source_revision, session.expires_at - SESSION_TTL)
        service = NativeGraphDemoService(
            repository(),
            storage_label="postgres",
            store=store,
            allocation_id=session.allocation_id,
            source_snapshot=snapshot,
        )
        yield service
    finally:
        if service is not None:
            service.close()
        else:
            store.close()


def ensure_guest_managed_world(session: IndexGraphSession):
    """Initialize this session's Graph and bind that same copy for Buddy surfaces.

    Authentication, origin checks and session credential resolution are the
    caller's responsibility; this function grants no request access.
    """
    from application_state.index_graph.managed_world import bind_initialized_guest_world

    with open_index_graph_service(session) as service:
        service.graph()
    return bind_initialized_guest_world(session)
