"""Bind Play/workspace tests to WorkRevision.revision_n, not object CAS."""

from __future__ import annotations

from apps.live_control_server.services.workspace_document_registry import (
    WorkspaceDocumentSnapshot,
    get_committed_playable_revision,
)

_PLAYABLE_BY_SHA: dict[tuple[str, str], int] = {}


def clear_playable_bindings() -> None:
    _PLAYABLE_BY_SHA.clear()


def remember_committed_playable(
    snapshot: WorkspaceDocumentSnapshot,
) -> WorkspaceDocumentSnapshot:
    if snapshot.record.kind != "runbook":
        return snapshot
    committed = get_committed_playable_revision(snapshot.record.document_id, kind=None)
    if committed.content_sha256 == snapshot.content_sha256:
        _PLAYABLE_BY_SHA[(snapshot.record.document_id, snapshot.content_sha256)] = (
            committed.revision_n
        )
    return snapshot


def playable_binding(snapshot: WorkspaceDocumentSnapshot) -> tuple[int, str]:
    key = (snapshot.record.document_id, snapshot.content_sha256)
    remembered = _PLAYABLE_BY_SHA.get(key)
    if remembered is not None:
        return remembered, snapshot.content_sha256
    committed = get_committed_playable_revision(snapshot.record.document_id, kind=None)
    return committed.revision_n, committed.content_sha256
