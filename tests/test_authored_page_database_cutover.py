"""Ordinary workspace Page controls have one database owner, never a file mirror."""

import pytest
from application_state.content import pages
from application_state.errors import ApplicationStateValidationError
from application_state.world_catalog.service import create_world
from apps.live_control_server.services import workspace_document_registry as workspace
from apps.live_control_server.services import source_artifact_registry as sources
from apps.live_control_server.services.tiptap_markdown_write import (
    TiptapMarkdownWritePrepareRequest,
    TiptapMarkdownWriteCommitRequest,
    TiptapMarkdownWriteConflictError,
    prepare_tiptap_markdown_write,
    commit_tiptap_markdown_write,
)

pytestmark = pytest.mark.usefixtures("application_state_dsn")


@pytest.fixture
def page(tmp_path, monkeypatch):
    monkeypatch.setenv("DMB_ARTIFACT_DATA_ROOT", str(tmp_path))
    world = create_world(name="Page cutover").record.world_id
    return workspace.create_workspace_document(
        tmp_path,
        title="A place",
        world_id=world,
        campaign_id=None,
        kind="worldbuilding_source",
        source_domain="worldbuilding",
        document_class="lore",
        authority_state="draft",
        visibility_state="internal",
    )


def prepare(root, record, text, mode="authoring"):
    return prepare_tiptap_markdown_write(
        root=root,
        request=TiptapMarkdownWritePrepareRequest(
            document_id=record.document_id,
            markdown=text,
            expected_revision=record.revision,
            write_mode=mode,
        ),
    )


def save(root, record, text, mode="authoring"):
    prepared = prepare(root, record, text, mode)
    assert prepared.writer_ok, prepared.diagnostics
    request = TiptapMarkdownWriteCommitRequest(
        document_id=record.document_id,
        markdown=text,
        expected_revision=record.revision,
        write_mode=mode,
        writer_confirm_token=prepared.writer_confirm_token,
    )
    return commit_tiptap_markdown_write(root=root, request=request), request


def test_workspace_page_create_save_read_trash_restore_has_no_file_authority(
    tmp_path, page
):
    assert page.campaign_id is None and page.target_relpath is None
    before = pages.committed_page(page.document_id, world_id=page.world_id)
    prepared = prepare(tmp_path, page, "Saved\n")
    assert pages.committed_page(page.document_id, world_id=page.world_id) == before
    assert not prepared.file_exists
    receipt, request = save(tmp_path, page, "Saved\n")
    assert commit_tiptap_markdown_write(root=tmp_path, request=request) == receipt
    assert not workspace.get_workspace_document_snapshot(
        tmp_path, page.document_id
    ).file_exists
    assert workspace.list_workspace_documents(
        tmp_path, kind="worldbuilding_source"
    ) == [receipt.committed_record]
    discarded = workspace.discard_workspace_document(
        tmp_path, page.document_id, expected_revision=receipt.committed_revision
    )
    assert (
        workspace.list_workspace_documents(tmp_path, kind="worldbuilding_source") == []
    )
    workspace.restore_workspace_document(
        tmp_path, page.document_id, expected_revision=discarded.revision
    )
    assert (
        workspace.get_committed_page_snapshot(tmp_path, page.document_id).markdown
        == "Saved\n"
    )
    assert not list(tmp_path.rglob("*.md")) and not list(
        tmp_path.rglob("workspace_documents.json")
    )


def test_working_copy_never_becomes_saved_source(tmp_path, page):
    receipt, _ = save(tmp_path, page, "Last saved\n")
    basis = pages.snapshot_page(page.document_id, world_id=page.world_id)
    pages.save_draft(
        page.document_id,
        "New draft\n",
        world_id=page.world_id,
        expected_revision=basis.page.object_revision,
        expected_working_copy_revision=basis.working_copy_revision,
    )
    editor = workspace.get_workspace_document_snapshot(tmp_path, page.document_id)
    saved = workspace.get_committed_page_snapshot(tmp_path, page.document_id)
    assert editor.markdown == "New draft\n" and editor.record.content_status == "draft"
    assert editor.committed_markdown == "Last saved\n"
    assert editor.committed_content_sha256 == saved.content_sha256
    assert (
        saved.markdown == "Last saved\n" and saved.record.content_status == "committed"
    )
    artifact = sources.create_source_artifact_from_workspace_document(
        tmp_path,
        document_id=page.document_id,
        expected_revision=saved.loaded_revision,
        expected_content_sha256=saved.content_sha256,
    )
    assert (
        sources.load_registered_source_artifact_text(
            tmp_path, artifact.source_artifact_id
        )[1]
        == "Last saved\n"
    )
    assert (
        pages.snapshot_page(page.document_id, world_id=page.world_id).markdown
        == "New draft\n"
    )


def test_prepared_save_refuses_intervening_working_copy(tmp_path, page):
    prepared = prepare(tmp_path, page, "Proposed\n")
    pages.save_draft(
        page.document_id,
        "Newer\n",
        world_id=page.world_id,
        expected_revision=1,
        expected_working_copy_revision=None,
    )
    with pytest.raises(TiptapMarkdownWriteConflictError):
        commit_tiptap_markdown_write(
            root=tmp_path,
            request=TiptapMarkdownWriteCommitRequest(
                document_id=page.document_id,
                markdown="Proposed\n",
                expected_revision=1,
                writer_confirm_token=prepared.writer_confirm_token,
            ),
        )
    assert (
        workspace.get_workspace_document_snapshot(tmp_path, page.document_id).markdown
        == "Newer\n"
    )
    assert (
        workspace.get_committed_page_snapshot(
            tmp_path, page.document_id
        ).record.content_status
        == "draft"
    )


def test_source_import_is_exact_initial_save_and_retry(tmp_path, page):
    text = "---\nowner: someone\n---\n\n<table>raw</table>\n\n\n"
    receipt, request = save(tmp_path, page, text, "source_import")
    assert (
        workspace.get_committed_page_snapshot(tmp_path, page.document_id).markdown
        == text
    )
    assert commit_tiptap_markdown_write(root=tmp_path, request=request) == receipt
    with pytest.raises(TiptapMarkdownWriteConflictError):
        prepare(tmp_path, receipt.committed_record, text, "source_import")


def test_frontmatter_check_uses_saved_bytes_not_divergent_draft(tmp_path, page):
    original = "---\nowner: original\n---\n\nBody\n"
    receipt, _ = save(tmp_path, page, original, "source_import")
    basis = pages.snapshot_page(page.document_id, world_id=page.world_id)
    pages.save_draft(
        page.document_id,
        original.replace("original", "draft"),
        world_id=page.world_id,
        expected_revision=basis.page.object_revision,
        expected_working_copy_revision=basis.working_copy_revision,
    )
    record = workspace.get_workspace_document(tmp_path, page.document_id)
    assert prepare(tmp_path, record, original.replace("Body", "New body")).writer_ok
    assert not prepare(
        tmp_path, record, original.replace("original", "draft")
    ).writer_ok


def test_source_descriptor_and_old_body_survive_new_save(tmp_path, page):
    receipt, _ = save(tmp_path, page, "Before\n")
    artifact = sources.create_source_artifact_from_workspace_document(
        tmp_path, document_id=page.document_id
    )
    assert (
        sources.create_source_artifact_from_workspace_document(
            tmp_path, document_id=page.document_id
        )
        == artifact
    )
    save(tmp_path, receipt.committed_record, "After\n")
    assert sources.load_registered_source_artifact_text(
        tmp_path, artifact.source_artifact_id
    ) == (artifact, "Before\n")
    assert (
        sources.create_source_artifact_from_workspace_document(
            tmp_path, document_id=page.document_id
        ).source_artifact_id
        != artifact.source_artifact_id
    )


def test_page_uuid_remains_inadmissible_as_playable(tmp_path, page):
    from application_state.content import service

    with pytest.raises(
        ApplicationStateValidationError, match="page-specific Content owner"
    ):
        service.current_committed_revision(page.document_id)


def test_source_capture_is_coherent_across_concurrent_page_save(
    tmp_path, page, monkeypatch
):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Event, current_thread
    from application_state.content import repository

    receipt, _ = save(tmp_path, page, "Before\n")
    initial = pages.committed_page(page.document_id, world_id=page.world_id)
    entered, release = Event(), Event()
    read = repository.get_work_revision

    def pause_read(conn, revision_id):
        if (
            current_thread().name.startswith("source-capture")
            and revision_id == initial.revision.work_revision_id
        ):
            entered.set()
            assert release.wait(10), "test did not release the captured read"
        return read(conn, revision_id)

    monkeypatch.setattr(repository, "get_work_revision", pause_read)
    with ThreadPoolExecutor(thread_name_prefix="source-capture") as pool:
        future = pool.submit(
            sources.create_source_artifact_from_workspace_document,
            tmp_path,
            document_id=page.document_id,
            expected_revision=receipt.committed_revision,
        )
        assert entered.wait(10), (
            "capture did not reach its transaction-bound revision read"
        )
        try:
            renamed = workspace.update_workspace_document_metadata(
                tmp_path,
                page.document_id,
                title="Newer title",
                expected_revision=receipt.committed_revision,
            )
            save(tmp_path, renamed, "After\n")
        finally:
            release.set()
        artifact = future.result()
    assert artifact.workspace_document_revision == receipt.committed_revision
    assert artifact.lineage["source_name"] == initial.page.title
    assert artifact.content_sha256 == initial.revision.content_sha256
    assert (
        sources.load_registered_source_artifact_text(
            tmp_path, artifact.source_artifact_id
        )[1]
        == "Before\n"
    )
    assert (
        workspace.get_committed_page_snapshot(tmp_path, page.document_id).markdown
        == "After\n"
    )


def test_legacy_source_descriptor_survives_explicit_page_adoption_and_file_loss(
    tmp_path, monkeypatch
):
    from datetime import UTC, datetime
    from uuid import uuid4
    from application_state.content.import_pages import FrozenPage, adopt_pages
    from application_state.content.types import AuthoredPageObject, sha256_utf8
    from graph_memory.evidence.source_artifact import (
        GraphMemorySourceArtifact,
        build_worldbuilding_source_artifact_id,
    )
    from apps.live_control_server.services.graph_document_source import (
        GraphDocumentSource,
        resolve_graph_document_source,
    )

    monkeypatch.setenv("DMB_ARTIFACT_DATA_ROOT", str(tmp_path))
    world = create_world(name="Adopted World").record.world_id
    document_id = str(uuid4())
    body, revision = "Retained source.\n", 17
    digest = sha256_utf8(body)
    source_id = build_worldbuilding_source_artifact_id(
        workspace_document_id=document_id,
        workspace_document_revision=revision,
        content_sha256=digest,
    )
    metadata = pages.PageMetadata(document_class="lore")
    legacy_file = tmp_path / "old-operational-page.md"
    legacy_file.write_text(body)
    stamp = datetime(2026, 10, 25, tzinfo=UTC)
    artifact = GraphMemorySourceArtifact(
        source_artifact_id=source_id,
        source_domain="worldbuilding",
        campaign_id=world,
        world_id=world,
        uri="repo://old-operational-page.md",
        content_sha256=digest,
        artifact_kind="worldbuilding_markdown",
        document_class="lore",
        authority_state="draft",
        visibility_state="internal",
        workspace_document_id=document_id,
        workspace_document_revision=revision,
        lineage={
            "source_name": "Retained page",
            "workspace_document_id": document_id,
            "workspace_document_revision": revision,
            "source_span_index_uri": f"repo://{sources.source_span_index_relpath(source_id)}",
        },
        created_at=stamp.isoformat(),
        updated_at=stamp.isoformat(),
    )
    original = sources._register_source_input(artifact, body)
    frozen = FrozenPage(
        page=AuthoredPageObject(
            work_object_id=document_id,
            world_id=world,
            campaign_id=world,
            title="Retained page",
            object_revision=revision,
            created_at=stamp,
            updated_at=stamp,
        ),
        metadata=metadata,
        content_status="committed",
        markdown=legacy_file.read_text(),
        content_sha256=digest,
    )
    assert adopt_pages([frozen], dry_run=False).status == "adopted"
    legacy_file.unlink()
    assert (
        sources.create_source_artifact_from_workspace_document(
            tmp_path,
            document_id=document_id,
            expected_revision=revision,
            expected_content_sha256=digest,
        )
        == original
    )
    selector = GraphDocumentSource(
        documentId=document_id, revision=revision, contentSha256=digest
    )
    captured = resolve_graph_document_source(
        tmp_path, selector, world_id=world, campaign_id=world
    )
    assert captured.source_artifact == original
    current = workspace.get_workspace_document(tmp_path, document_id)
    save(tmp_path, current, "Newer writing\n")
    assert (
        resolve_graph_document_source(
            tmp_path, selector, world_id=world, campaign_id=world
        ).source_artifact
        == original
    )
    assert sources.load_registered_source_artifact_text(tmp_path, source_id) == (
        original,
        body,
    )


@pytest.mark.parametrize("campaign_id", [None, "longmont-c2"])
def test_world_inventory_does_not_treat_campaign_tag_as_page_owner(tmp_path, page, campaign_id):
    tagged = workspace.create_workspace_document(
        tmp_path, title="Tagged page", world_id=page.world_id, campaign_id=campaign_id,
        kind="worldbuilding_source", source_domain="worldbuilding", document_class="lore",
        authority_state="draft", visibility_state="internal",
    )
    other_world = create_world(name="Other owner").record.world_id
    foreign = workspace.create_workspace_document(
        tmp_path, title="Foreign", world_id=other_world, campaign_id=page.world_id,
        kind="worldbuilding_source", source_domain="worldbuilding", document_class="lore",
        authority_state="draft", visibility_state="internal",
    )
    from apps.live_control_server.routes.workspace_documents import get_workspace_documents
    response = get_workspace_documents(world_id=page.world_id, campaign_id=None, kind="worldbuilding_source", status="active")
    assert {row["document_id"] for row in response["records"]} == {page.document_id, tagged.document_id}
    assert workspace.get_workspace_document(tmp_path, tagged.document_id).campaign_id == campaign_id
    assert [record.document_id for record in workspace.list_workspace_documents(
        tmp_path, kind="worldbuilding_source", campaign_id=page.world_id
    )] == [foreign.document_id]
    with pytest.raises(workspace.WorkspaceDocumentRegistryError, match="requires kind"):
        workspace.list_workspace_documents(tmp_path, world_id=page.world_id, kind="plan")
