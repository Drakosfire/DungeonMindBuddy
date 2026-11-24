"""Provision one frozen synthetic case in the verified disposable App clone."""
from hashlib import sha256
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

from .fixture_sources import inspect_related_pages
from .owned_db_fixture import checked_owned_dsn


def provision_fixture(fixture, *, root):
    """Create and verify synthetic pages; never reset an existing World.

    The caller owns the isolated root and must retain partial failures. This
    does not seed conversation history or dispatch a model request.
    """
    from application_state.content import pages
    from application_state.world_catalog import service as worlds
    from application_state.world_catalog.types import WorldContainerRecord
    from apps.live_control_server.services.workspace_document_registry import (
        create_workspace_document, get_workspace_document_snapshot,
    )

    root = Path(root).resolve(strict=True)
    if not root.is_dir():
        raise ValueError("An existing isolated fixture root is required")
    page = fixture.get("page")
    related = fixture.get("related_pages")
    if (not isinstance(page, str) or not page.strip() or not isinstance(related, list)
            or any(not isinstance(row, dict) or set(row) != {"label", "title", "body"}
                   or any(not isinstance(row[key], str) or not row[key].strip()
                          for key in ("label", "title", "body")) for row in related)
            or len({row["label"] for row in related}) != len(related)
            or len({row["title"] for row in related}) != len(related)):
        raise ValueError("Synthetic pages require unique nonblank labels, titles and content")
    checked_owned_dsn()
    world = "negative-seed-" + uuid4().hex
    if worlds.get_world(world) is not None:
        raise ValueError("Synthetic World already exists")
    worlds.save_world(WorldContainerRecord(
        world_id=world, name="Synthetic retrieval fixture",
        source_root_relpath=worlds.world_source_root_relpath(world),
        created_at="2026-01-01T00:00:00Z"), expected_revision=0)

    def save(title, body):
        record = create_workspace_document(root, world_id=world, campaign_id=world, title=title,
            kind="worldbuilding_source", source_domain="worldbuilding", document_class="lore",
            authority_state="draft", visibility_state="internal")
        basis = pages.snapshot_page(record.document_id, world_id=world)
        pages.commit_page(record.document_id, body, world_id=world,
            expected_revision=basis.page.object_revision,
            expected_working_copy_revision=basis.working_copy_revision)
        saved = get_workspace_document_snapshot(root, record.document_id)
        digest = sha256(body.encode("utf-8")).hexdigest()
        if (saved.record.world_id != world or saved.markdown != body or saved.committed_markdown != body
                or saved.content_sha256 != digest or saved.committed_content_sha256 != digest
                or saved.loaded_revision != saved.record.revision):
            raise ValueError("Persisted synthetic page differs from the fixture")
        return saved

    primary = save("Synthetic benchmark page", page)
    for source in related:
        save(source["title"], source["body"])
    work = {"object_id": primary.record.document_id, "expected_revision": primary.record.revision,
            "expected_content_sha256": primary.content_sha256}
    request = SimpleNamespace(owner_scope=SimpleNamespace(world_id=world), primary_work=SimpleNamespace(**work))
    inventory = inspect_related_pages(request, fixture)
    return {"world": world, "primary_work": work, "related_inventory": inventory}
