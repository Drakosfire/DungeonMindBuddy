"""In-memory turn-scoped GraphRetrievalSession store."""

from __future__ import annotations

from threading import RLock

from graph_memory.interaction.session import GraphRetrievalSession

_LOCK = RLock()
_SESSIONS: dict[str, GraphRetrievalSession] = {}


def create_session(session: GraphRetrievalSession) -> GraphRetrievalSession:
    with _LOCK:
        _SESSIONS[session.id] = session
        return session


def get_session(session_id: str) -> GraphRetrievalSession | None:
    with _LOCK:
        return _SESSIONS.get(session_id)


def replace_session(session: GraphRetrievalSession) -> GraphRetrievalSession:
    with _LOCK:
        _SESSIONS[session.id] = session
        return session


def clear_sessions() -> None:
    """Test helper — wipe all turn sessions."""
    with _LOCK:
        _SESSIONS.clear()


__all__ = [
    "clear_sessions",
    "create_session",
    "get_session",
    "replace_session",
]
