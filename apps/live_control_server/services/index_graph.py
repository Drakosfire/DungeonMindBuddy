"""Compose one Buddy index guest session with its native graph authority."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from application_state.index_graph.sessions import IndexGraphSession
from application_state.index_graph.store import IndexGraphStore
from apps.live_control_server.integrations.dungeonmind.native_registry_source import (
    repository,
)
from apps.live_control_server.native_graph_demo import NativeGraphDemoService


@contextmanager
def open_index_graph_service(
    session: IndexGraphSession,
) -> Iterator[NativeGraphDemoService]:
    """Open a service bound only to this server-owned session and allocation."""
    store = IndexGraphStore(session.session_id, session.allocation_id)
    service: NativeGraphDemoService | None = None
    try:
        service = NativeGraphDemoService(
            repository(),
            storage_label="postgres",
            store=store,
            allocation_id=session.allocation_id,
        )
        yield service
    finally:
        if service is not None:
            service.close()
        else:
            store.close()
