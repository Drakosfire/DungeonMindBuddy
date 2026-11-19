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
def test_world_inventory_does_not_treat_campaign_tag_as_page_owner(
    tmp_path, page, campaign_id
):
    tagged = workspace.create_workspace_document(
        tmp_path,
        title="Tagged page",
        world_id=page.world_id,
        campaign_id=campaign_id,
        kind="worldbuilding_source",
        source_domain="worldbuilding",
        document_class="lore",
        authority_state="draft",
        visibility_state="internal",
    )
    other_world = create_world(name="Other owner").record.world_id
    foreign = workspace.create_workspace_document(
        tmp_path,
        title="Foreign",
        world_id=other_world,
        campaign_id=page.world_id,
        kind="worldbuilding_source",
        source_domain="worldbuilding",
        document_class="lore",
        authority_state="draft",
        visibility_state="internal",
    )
    from apps.live_control_server.routes.workspace_documents import (
        get_workspace_documents,
    )

    response = get_workspace_documents(
        world_id=page.world_id,
        campaign_id=None,
        kind="worldbuilding_source",
        status="active",
    )
    assert {row["document_id"] for row in response["records"]} == {
        page.document_id,
        tagged.document_id,
    }
    assert (
        workspace.get_workspace_document(tmp_path, tagged.document_id).campaign_id
        == campaign_id
    )
    assert [
        record.document_id
        for record in workspace.list_workspace_documents(
            tmp_path, kind="worldbuilding_source", campaign_id=page.world_id
        )
    ] == [foreign.document_id]
    with pytest.raises(workspace.WorkspaceDocumentRegistryError, match="requires kind"):
        workspace.list_workspace_documents(
            tmp_path, world_id=page.world_id, kind="plan"
        )


# Page composer prerequisite: typed presentation is revision-bound, never evidence.
def presentation_for(text, widths=(6, 6)):
    from hashlib import sha256
    from application_state.content.markdown_source_blocks import source_block_spans
    from application_state.content.page_presentation import leading_yaml

    prefix = leading_yaml(text)
    offset = len(prefix.encode())
    raw = text.encode()
    blocks = [
        dict(
            kind="block",
            id=f"block-{i}",
            byte_start=a + offset,
            byte_end=b + offset,
            sha256=sha256(raw[a + offset : b + offset]).hexdigest(),
        )
        for i, (a, b) in enumerate(source_block_spans(text[len(prefix) :]))
    ]
    return dict(
        schema_version="dmb_page_presentation_v1",
        markdown_sha256=sha256(raw).hexdigest(),
        items=[
            dict(
                kind="row",
                id="row-1",
                min_height=0,
                line_mode="guide",
                slots=[
                    dict(id="left", width=widths[0], blocks=blocks[:1]),
                    dict(id="right", width=widths[1], blocks=blocks[1:]),
                ],
            )
        ],
    )


def save_composed(root, record, text, layout):
    prepared = prepare_tiptap_markdown_write(
        root=root,
        request=TiptapMarkdownWritePrepareRequest(
            document_id=record.document_id,
            markdown=text,
            expected_revision=record.revision,
            page_presentation=layout,
        ),
    )
    assert prepared.writer_ok
    request = TiptapMarkdownWriteCommitRequest(
        document_id=record.document_id,
        markdown=text,
        expected_revision=record.revision,
        page_presentation=layout,
        writer_confirm_token=prepared.writer_confirm_token,
    )
    return commit_tiptap_markdown_write(root=root, request=request), request


def test_layout_only_revision_exact_retry_noop_and_source_continuity(tmp_path, page):
    text = "Café 🌲\n\nAnother paragraph.\n"
    first, _ = save(tmp_path, page, text)
    source = sources.create_source_artifact_from_workspace_document(
        tmp_path,
        document_id=page.document_id,
        expected_revision=first.committed_revision,
        expected_content_sha256=first.normalized_content_sha256,
    )
    second, request = save_composed(
        tmp_path, first.committed_record, text, presentation_for(text)
    )
    assert second.committed_revision == first.committed_revision + 1
    assert second.page_presentation_sha256 is not None
    assert second.normalized_content_sha256 == first.normalized_content_sha256
    assert commit_tiptap_markdown_write(root=tmp_path, request=request) == second
    same, _ = save_composed(
        tmp_path, second.committed_record, text, presentation_for(text)
    )
    assert same.committed_revision == second.committed_revision
    third, request = save_composed(
        tmp_path, same.committed_record, text, presentation_for(text, (4, 8))
    )
    assert third.committed_revision == second.committed_revision + 1
    assert commit_tiptap_markdown_write(root=tmp_path, request=request) == third
    snap = workspace.get_workspace_document_snapshot(tmp_path, page.document_id)
    assert (
        snap.markdown == text
        and snap.page_presentation
        == pages.committed_page(page.document_id, world_id=page.world_id).presentation
    )
    assert snap.page_presentation.items[0].slots[0].width == 4
    assert snap.page_presentation_sha256 == third.page_presentation_sha256
    assert third.page_presentation_sha256 != second.page_presentation_sha256
    assert (
        sources.load_registered_source_artifact_text(
            tmp_path, source.source_artifact_id
        )[1]
        == text
    )


def test_presentation_token_binds_layout_and_stale_resize_cannot_overwrite(
    tmp_path, page
):
    text = "One\n\nTwo\n"
    layout = presentation_for(text)
    prepared = prepare_tiptap_markdown_write(
        root=tmp_path,
        request=TiptapMarkdownWritePrepareRequest(
            document_id=page.document_id,
            markdown=text,
            expected_revision=page.revision,
            page_presentation=layout,
        ),
    )
    wrong = TiptapMarkdownWriteCommitRequest(
        document_id=page.document_id,
        markdown=text,
        expected_revision=page.revision,
        page_presentation=presentation_for(text, (4, 8)),
        writer_confirm_token=prepared.writer_confirm_token,
    )
    with pytest.raises(TiptapMarkdownWriteConflictError):
        commit_tiptap_markdown_write(root=tmp_path, request=wrong)
    first, request = save_composed(tmp_path, page, text, layout)
    second, _ = save_composed(
        tmp_path, first.committed_record, text, presentation_for(text, (4, 8))
    )
    with pytest.raises(TiptapMarkdownWriteConflictError):
        commit_tiptap_markdown_write(root=tmp_path, request=request)
    assert (
        workspace.get_workspace_document_snapshot(
            tmp_path, page.document_id
        ).loaded_revision
        == second.committed_revision
    )


def test_composed_page_refuses_old_writer_and_draft_but_allows_explicit_unwrap(
    tmp_path, page
):
    from apps.live_control_server.services.tiptap_markdown_write import (
        TiptapMarkdownWriteError,
    )

    text = "One\n\nTwo\n"
    first, _ = save_composed(tmp_path, page, text, presentation_for(text))
    before = pages.snapshot_page(page.document_id, world_id=page.world_id)
    with pytest.raises(TiptapMarkdownWriteError, match="explicit presentation"):
        prepare(tmp_path, first.committed_record, text)
    with pytest.raises(ApplicationStateValidationError, match="Markdown-only"):
        pages.save_draft(
            page.document_id,
            "Overwrite",
            world_id=page.world_id,
            expected_revision=before.page.object_revision,
            expected_working_copy_revision=before.working_copy_revision,
        )
    assert pages.snapshot_page(page.document_id, world_id=page.world_id) == before
    cleared, request = save_composed(tmp_path, first.committed_record, text, None)
    assert cleared.committed_revision == first.committed_revision + 1
    assert commit_tiptap_markdown_write(root=tmp_path, request=request) == cleared
    assert (
        workspace.get_workspace_document_snapshot(
            tmp_path, page.document_id
        ).page_presentation
        is None
    )


@pytest.mark.parametrize(
    "damage", ["hash", "span", "order", "duplicate", "width", "yaml"]
)
def test_invalid_presentation_refuses_before_mutation(tmp_path, page, damage):
    from apps.live_control_server.services.tiptap_markdown_write import (
        TiptapMarkdownWriteError,
    )

    text = "---\ntitle: Café\n---\n\nOne 🌲\n\nTwo\n"
    saved, _ = save(tmp_path, page, text, "source_import")
    layout = presentation_for(text)
    left, right = layout["items"][0]["slots"]
    if damage == "hash":
        layout["markdown_sha256"] = "0" * 64
    if damage == "span":
        left["blocks"][0]["byte_end"] -= 1
    if damage == "order":
        left["blocks"], right["blocks"] = right["blocks"], left["blocks"]
    if damage == "duplicate":
        right["blocks"][0]["id"] = left["blocks"][0]["id"]
    if damage == "width":
        left["width"] = 5
    if damage == "yaml":
        left["blocks"][0]["byte_start"] = 0
    before = pages.snapshot_page(page.document_id, world_id=page.world_id)
    with pytest.raises(TiptapMarkdownWriteError):
        save_composed(tmp_path, saved.committed_record, text, layout)
    assert pages.snapshot_page(page.document_id, world_id=page.world_id) == before


def test_presentation_insert_failure_rolls_back_revision_and_working_copy(
    tmp_path, page, monkeypatch
):
    from application_state.content import page_presentation

    text = "One\n\nTwo\n"
    before = pages.snapshot_page(page.document_id, world_id=page.world_id)

    def fail(*_):
        raise RuntimeError("test atomic rollback")

    monkeypatch.setattr(page_presentation, "insert", fail)
    with pytest.raises(RuntimeError, match="atomic rollback"):
        save_composed(tmp_path, page, text, presentation_for(text))
    assert pages.snapshot_page(page.document_id, world_id=page.world_id) == before


def test_presentation_mixed_body_unicode_yaml_and_foreign_world(page):
    from application_state.content.page_presentation import PagePresentation
    from application_state.errors import ApplicationStateNotFoundError

    text = (
        "---\ntitle: Café\n---\n\nCafé 🌲 prose.\n\n"
        "![Art](dmb-media:00000000-0000-0000-0000-000000000001)\n\n"
        "| Name | Value |\n| --- | --- |\n| Tree | Tall |\n\n"
        "> [!GM-NOTE] Secret\n> The tree sings.\n"
    )
    layout = PagePresentation.model_validate(presentation_for(text)).checked(text)
    basis = pages.committed_page(page.document_id, world_id=page.world_id)
    with pytest.raises(ApplicationStateNotFoundError):
        pages.commit_page(
            page.document_id,
            text,
            world_id="foreign",
            expected_revision=1,
            expected_working_copy_revision=None,
            page_presentation=layout,
        )
    committed, revision = pages.commit_page(
        page.document_id,
        text,
        world_id=page.world_id,
        expected_revision=basis.page.object_revision,
        expected_working_copy_revision=basis.working_copy_revision,
        page_presentation=layout,
    )
    snap = pages.snapshot_page(page.document_id, world_id=page.world_id)
    assert snap.presentation == layout and snap.markdown == text
    assert len(layout.items[0].slots[1].blocks) == 3
    # These are byte offsets, and never bind the preserved frontmatter.
    assert layout.items[0].slots[0].blocks[0].byte_start == len(
        "---\ntitle: Café\n---\n".encode()
    )


def test_shared_span_extraction_preserves_evidence_handles():
    from application_state.agent_conversation.authored_excerpt_blocks import (
        partition,
        block_handle,
    )
    from application_state.content.markdown_source_blocks import source_block_spans
    from hashlib import sha256

    text = "Café 🌲\r\n\r\n| A | B |\r\n| --- | --- |\r\n| 1 | 2 |\r\n\r\n> [!GM-NOTE] Hi\r\n> Bye\r\n"
    raw = text.encode()
    evidence = partition(text, "retained-source")
    assert [(b.byte_start, b.byte_end) for b in evidence] == list(
        source_block_spans(text)
    )
    assert "".join(b.text for b in evidence) == text
    for b in evidence:
        assert b.block_handle == block_handle(
            "retained-source",
            b.byte_start,
            b.byte_end,
            sha256(raw[b.byte_start : b.byte_end]).hexdigest(),
        )


@pytest.mark.parametrize(
    "change", ["schema", "nested", "float", "extra", "digest", "html", "code"]
)
def test_presentation_schema_and_block_admission_are_closed(change):
    from pydantic import ValidationError
    from application_state.content.page_presentation import PagePresentation

    text = "One\n\nTwo\n"
    if change == "html":
        text = "<div>Unowned HTML</div>\n"
    if change == "code":
        text = "```unknown\nwidget\n```\n"
    value = presentation_for(text)
    if change == "schema":
        value["schema_version"] = "future_v2"
    if change == "nested":
        value["items"][0]["slots"][0]["blocks"] = [value["items"][0].copy()]
    if change == "float":
        value["items"][0]["slots"][0]["width"] = 6.0
    if change == "extra":
        value["items"][0]["css"] = "position:absolute"
    if change == "digest":
        value["items"][0]["slots"][0]["blocks"][0]["sha256"] = "0" * 64
    with pytest.raises((ValidationError, ApplicationStateValidationError)):
        PagePresentation.model_validate(value).checked(text)


def test_presentation_rejects_reference_definition_that_parser_hides():
    from application_state.content.page_presentation import PagePresentation

    text = "![Bird][bird]\n\nOther text.\n\n[bird]: dmb-media:11111111-1111-4111-8111-111111111111\n"
    with pytest.raises(ApplicationStateValidationError, match="reference definitions"):
        PagePresentation.model_validate(presentation_for(text)).checked(text)


# Slice C: an image/text stack is only presentation over two ordinary blocks.
def staged_image_text(title="Title"):
    from io import BytesIO
    from PIL import Image
    from application_state import media

    data = BytesIO()
    Image.new("RGB", (32, 32), (150, 170, 100)).save(data, format="PNG")
    asset = media.stage_image(
        data.getvalue(), "local_operator", {"kind": "synthetic_stack_test"}
    )
    return f"![Artwork](dmb-media:{asset['asset_id']})\n\n{title}\n"


def image_text_presentation(text, *, nested=False, anchor="middle-center"):
    layout = presentation_for(text)
    row = layout["items"][0]
    blocks = [block for slot in row["slots"] for block in slot["blocks"]]
    stack = dict(
        kind="image_text",
        id="stack-1",
        image=blocks[0],
        text=blocks[1],
        anchor=anchor,
        inset="small",
        backing="contrast",
    )
    if nested:
        row["slots"] = [dict(id="only", width=12, blocks=[stack])]
    else:
        layout["items"] = [stack]
    return layout


@pytest.mark.parametrize("nested", [False, True])
def test_image_text_revision_retry_cas_and_historical_source(tmp_path, page, nested):
    from apps.live_control_server.services.tiptap_markdown_write import (
        TiptapMarkdownWriteError,
    )

    text = staged_image_text("# Café 🌲")
    plain, _ = save(tmp_path, page, text)
    source = sources.create_source_artifact_from_workspace_document(
        tmp_path,
        document_id=page.document_id,
        expected_revision=plain.committed_revision,
        expected_content_sha256=plain.normalized_content_sha256,
    )
    first, request = save_composed(
        tmp_path,
        plain.committed_record,
        text,
        image_text_presentation(text, nested=nested),
    )
    assert commit_tiptap_markdown_write(root=tmp_path, request=request) == first
    same, _ = save_composed(
        tmp_path,
        first.committed_record,
        text,
        image_text_presentation(text, nested=nested),
    )
    assert same.committed_revision == first.committed_revision
    second, _ = save_composed(
        tmp_path,
        same.committed_record,
        text,
        image_text_presentation(text, nested=nested, anchor="bottom-right"),
    )
    assert second.committed_revision == first.committed_revision + 1
    assert second.normalized_content_sha256 == plain.normalized_content_sha256
    snap = workspace.get_workspace_document_snapshot(tmp_path, page.document_id)
    assert snap.markdown == text
    assert snap.page_presentation_sha256 == second.page_presentation_sha256
    assert snap.page_presentation.model_dump() == image_text_presentation(
        text, nested=nested, anchor="bottom-right"
    )
    with pytest.raises(TiptapMarkdownWriteConflictError):
        commit_tiptap_markdown_write(root=tmp_path, request=request)
    with pytest.raises(TiptapMarkdownWriteError, match="explicit presentation"):
        prepare(tmp_path, second.committed_record, text)
    assert (
        sources.load_registered_source_artifact_text(
            tmp_path, source.source_artifact_id
        )[1]
        == text
    )
    assert workspace.get_workspace_document_snapshot(tmp_path, page.document_id) == snap


@pytest.mark.parametrize(
    "source",
    [
        "ordinary paragraph\n\nTitle\n",
        "![External](https://example.com/art.png)\n\nTitle\n",
        "before ![Art](dmb-media:11111111-1111-4111-8111-111111111111)\n\nTitle\n",
        "![Art](dmb-media:11111111-1111-4111-8111-111111111111)\n\n![Second](dmb-media:22222222-2222-4222-8222-222222222222)\n",
        "![Art](dmb-media:11111111-1111-4111-8111-111111111111)\n\n> quote\n",
        "![Art](dmb-media:not-a-uuid)\n\nTitle\n",
    ],
)
def test_image_text_requires_actual_source_types(source):
    from application_state.content.page_presentation import PagePresentation

    with pytest.raises(ApplicationStateValidationError):
        PagePresentation.model_validate(image_text_presentation(source)).checked(source)


@pytest.mark.parametrize(
    "damage", ["anchor", "inset", "backing", "nested", "duplicate", "reorder", "hash"]
)
def test_image_text_invalid_layout_preserves_revision(tmp_path, page, damage):
    from apps.live_control_server.services.tiptap_markdown_write import (
        TiptapMarkdownWriteError,
    )

    text = staged_image_text()
    layout = image_text_presentation(text)
    stack = layout["items"][0]
    if damage in {"anchor", "inset", "backing"}:
        stack[damage] = "not-allowed"
    if damage == "nested":
        stack["text"] = dict(stack)
    if damage == "duplicate":
        stack["text"]["id"] = stack["image"]["id"]
    if damage == "reorder":
        stack["image"], stack["text"] = stack["text"], stack["image"]
    if damage == "hash":
        stack["text"]["sha256"] = "0" * 64
    before = pages.snapshot_page(page.document_id, world_id=page.world_id)
    with pytest.raises((TiptapMarkdownWriteError, ValueError)):
        save_composed(tmp_path, page, text, layout)
    assert pages.snapshot_page(page.document_id, world_id=page.world_id) == before


def test_unlayered_v1_fingerprint_is_unchanged():
    import hashlib
    import json
    from application_state.content.page_presentation import PagePresentation

    text = "One\n\nTwo\n"
    payload = presentation_for(text)
    value = PagePresentation.model_validate(payload).checked(text)
    assert value.model_dump() == payload
    assert (
        value.fingerprint()
        == hashlib.sha256(
            json.dumps(
                payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False
            ).encode()
        ).hexdigest()
    )


def test_saved_variant_href_survives_ordinary_page_commit(tmp_path, page):
    from uuid import uuid4

    body = "# Edge\n\nBefore the insertion.\n\nAfter the insertion.\n"
    first, _ = save(tmp_path, page, body)
    href = (
        f"/statblock?world={page.world_id}&conversation={uuid4()}"
        f"&turn={uuid4()}&variantReview={uuid4()}"
    )
    link = f"[Open saved statblock variant]({href})"
    edited = body.replace("After the insertion.", f"{link}\n\nAfter the insertion.")
    result, _ = save(tmp_path, first.committed_record, edited)
    reopened = workspace.get_committed_page_snapshot(tmp_path, page.document_id)
    assert reopened.loaded_revision == result.committed_record.revision
    assert reopened.markdown == edited
    assert reopened.markdown.count(href) == 1
