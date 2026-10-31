"""Synthetic Page fixtures use real database owners, never a file emulation."""

from application_state.content import pages
from application_state.world_catalog import service as worlds
from application_state.world_catalog.types import WorldContainerRecord
from apps.live_control_server.services.workspace_document_registry import (
    create_workspace_document,
    get_workspace_document,
    get_committed_page_snapshot,
)


def create_page_fixture(root, *, world_id="eldyrwild", **values):
    if worlds.get_world(world_id) is None:
        worlds.save_world(
            WorldContainerRecord(
                world_id=world_id,
                name=world_id,
                source_root_relpath=worlds.world_source_root_relpath(world_id),
                created_at="2026-10-31T00:00:00Z",
            ),
            expected_revision=0,
        )
    return create_workspace_document(root, world_id=world_id, **values)


def save_page(root, document_id, markdown):
    state = pages.find_page(document_id)
    assert state is not None
    basis = pages.snapshot_page(document_id, world_id=state.page.world_id)
    pages.commit_page(
        document_id,
        markdown,
        world_id=state.page.world_id,
        expected_revision=basis.page.object_revision,
        expected_working_copy_revision=basis.working_copy_revision,
    )
    return get_workspace_document(root, document_id)


def page_text(root, document_id):
    return get_committed_page_snapshot(root, document_id).markdown
