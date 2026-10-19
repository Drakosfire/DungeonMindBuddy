"""World-scoped recoverable trash inventory and lifecycle operations."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from application_state.errors import ApplicationStateError
from apps.live_control_server.services.world_container_registry import (
    get_world_container,
)
from apps.live_control_server.services.workspace_document_registry import (
    WorldOwnedPlanRecordV2,
    WorkspaceDocumentRegistryError,
    discard_workspace_document,
    get_workspace_document,
    list_workspace_documents,
    list_world_owned_plans_v2,
    restore_workspace_document,
)


def _verify_world(root: Path, world_id: str) -> str:
    try:
        world = get_world_container(root, world_id)
    except Exception as exc:
        if isinstance(exc, WorkspaceDocumentRegistryError):
            raise
        if isinstance(exc, ApplicationStateError):
            raise WorkspaceDocumentRegistryError(
                str(exc), status_code=exc.status_code
            ) from exc
        if isinstance(exc, ValueError):
            raise WorkspaceDocumentRegistryError(
                str(exc), status_code=int(getattr(exc, "status_code", 404))
            ) from exc
        raise WorkspaceDocumentRegistryError(
            "Managed World storage is unavailable", status_code=503
        ) from exc
    if world.world_id != world_id:
        raise WorkspaceDocumentRegistryError("World identity mismatch", status_code=404)
    return world_id


def _document_item(record: Any, status: str | None = None) -> dict[str, Any]:
    surface = "build" if record.kind == "worldbuilding_source" else "plan"
    item_status = status or (
        "trashed" if record.status == "discarded" else record.status
    )
    return {
        "kind": "document",
        "id": record.document_id,
        "title": record.title,
        "status": item_status,
        "revision": record.revision,
        "surface": surface,
        "updated_at": record.updated_at,
    }


def list_world_workspace_trash(root: Path, *, world_id: str) -> dict[str, Any]:
    world = _verify_world(root, world_id)
    documents = [
        _document_item(record)
        for record in list_workspace_documents(
            root, kind="worldbuilding_source", status="discarded"
        )
        if record.world_id == world
    ]
    plans = [
        _document_item(record)
        for record in list_world_owned_plans_v2(
            root, world_id=world, status="discarded"
        ).records
    ]
    from application_state.play.lifecycle import list_trashed_world_play_sessions

    sessions = list_trashed_world_play_sessions(world_id=world)
    items = [*documents, *plans, *sessions]
    items.sort(
        key=lambda item: (item["updated_at"], item["kind"], item["id"]), reverse=True
    )
    return {"world_id": world, "items": items}


def set_world_document_trash(
    root: Path,
    *,
    world_id: str,
    document_id: str,
    expected_revision: int,
    restore: bool,
) -> dict[str, Any]:
    world = _verify_world(root, world_id)
    record = get_workspace_document(root, document_id)
    if record.kind == "worldbuilding_source":
        if record.world_id != world:
            raise WorkspaceDocumentRegistryError(
                "Document not found in this World", status_code=404
            )
    elif isinstance(record, WorldOwnedPlanRecordV2):
        if record.world_id != world:
            raise WorkspaceDocumentRegistryError(
                "Plan not found in this World", status_code=404
            )
    else:
        raise WorkspaceDocumentRegistryError(
            "Document is not a trashable World workspace item", status_code=404
        )
    if record.revision != expected_revision:
        raise WorkspaceDocumentRegistryError(
            "Document revision changed", status_code=409
        )
    wanted = "active" if restore else "discarded"
    if record.status != wanted:
        mutate = restore_workspace_document if restore else discard_workspace_document
        record = mutate(root, document_id, expected_revision=expected_revision)
    return _document_item(record, status="active" if restore else "trashed")


def set_world_session_trash(
    *,
    world_id: str,
    run_id: str,
    expected_revision: int,
    expected_content_revision: int,
    restore: bool,
) -> dict[str, Any]:
    from uuid import UUID
    from application_state.play.lifecycle import set_world_play_session_trash

    try:
        return set_world_play_session_trash(
            world_id=world_id,
            run_id=UUID(run_id),
            expected_revision=expected_revision,
            expected_content_revision=expected_content_revision,
            restore=restore,
        )
    except Exception as exc:
        if isinstance(exc, WorkspaceDocumentRegistryError):
            raise
        if isinstance(exc, ApplicationStateError):
            raise WorkspaceDocumentRegistryError(
                str(exc), status_code=exc.status_code
            ) from exc
        if isinstance(exc, ValueError):
            raise WorkspaceDocumentRegistryError(
                str(exc), status_code=int(getattr(exc, "status_code", 422))
            ) from exc
        raise WorkspaceDocumentRegistryError(
            "Play session lifecycle is unavailable", status_code=503
        ) from exc
