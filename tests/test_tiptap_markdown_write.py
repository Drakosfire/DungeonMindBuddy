from __future__ import annotations

from pathlib import Path

import pytest

from apps.live_control_server.services.tiptap_markdown_write import (
    TiptapMarkdownWriteCommitRequest,
    TiptapMarkdownWriteError,
    TiptapMarkdownWritePrepareRequest,
    authorize_target_for_record,
    commit_tiptap_markdown_write,
    markdown_lossy_diagnostics,
    normalize_tiptap_target_relpath,
    prepare_tiptap_markdown_write,
)
from apps.live_control_server.services.workspace_document_registry import (
    WorkspaceDocumentRecord,
    WorkspaceDocumentRegistryError,
    create_workspace_document,
    discard_workspace_document,
    get_workspace_document,
)


def test_normalize_allows_worldbuilding_workspace_target() -> None:
    document_id = "11111111-1111-4111-8111-111111111111"
    relpath = f"out/workspace/worldbuilding/{document_id}.md"
    assert normalize_tiptap_target_relpath(relpath) == relpath


def test_normalize_rejects_traversal_and_escape() -> None:
    with pytest.raises(TiptapMarkdownWriteError):
        normalize_tiptap_target_relpath("../secrets.md")
    with pytest.raises(TiptapMarkdownWriteError):
        normalize_tiptap_target_relpath("/tmp/escape.md")
    with pytest.raises(TiptapMarkdownWriteError):
        normalize_tiptap_target_relpath("out/workspace/worldbuilding/not-a-uuid.md")


def test_lossy_markdown_diagnostics_block_tables_and_html() -> None:
    diagnostics = markdown_lossy_diagnostics("| a | b |\n| --- | --- |\n<div>x</div>\n")
    assert diagnostics
    assert any("line 1" in item for item in diagnostics)


def test_worldbuilding_prepare_commit_round_trip(tmp_path: Path) -> None:
    record = create_workspace_document(
        tmp_path,
        title="World Lore",
        campaign_id="eldyrwild",
        kind="worldbuilding_source",
        source_domain="worldbuilding",
        document_class="lore",
        authority_state="draft",
        visibility_state="internal",
    )
    markdown = "# Title\n\nA supported paragraph.\n"
    prepared = prepare_tiptap_markdown_write(
        root=tmp_path,
        request=TiptapMarkdownWritePrepareRequest(
            document_id=record.document_id,
            markdown=markdown,
            expected_revision=1,
        ),
    )
    assert prepared.writer_ok is True
    assert prepared.writer_confirm_token
    assert prepared.target_relpath == record.target_relpath

    committed = commit_tiptap_markdown_write(
        root=tmp_path,
        request=TiptapMarkdownWriteCommitRequest(
            document_id=record.document_id,
            markdown=markdown,
            writer_confirm_token=prepared.writer_confirm_token,
            expected_revision=1,
        ),
    )
    assert committed.writer_ok is True
    assert committed.bytes_written
    target = tmp_path / record.target_relpath
    assert target.is_file()
    assert target.read_text(encoding="utf-8") == "# Title\n\nA supported paragraph.\n"


def test_lossy_markdown_blocks_prepare_and_commit_for_worldbuilding(tmp_path: Path) -> None:
    record = create_workspace_document(
        tmp_path,
        title="World Lore",
        campaign_id="eldyrwild",
        kind="worldbuilding_source",
        source_domain="worldbuilding",
        document_class="lore",
        authority_state="draft",
        visibility_state="internal",
    )
    markdown = "# Title\n\n| a | b |\n| --- | --- |\n| 1 | 2 |\n"
    prepared = prepare_tiptap_markdown_write(
        root=tmp_path,
        request=TiptapMarkdownWritePrepareRequest(
            document_id=record.document_id,
            markdown=markdown,
            expected_revision=1,
        ),
    )
    assert prepared.writer_ok is False
    assert prepared.writer_confirm_token is None
    assert any("lossy" in item for item in prepared.diagnostics)

    with pytest.raises(TiptapMarkdownWriteError) as exc_info:
        commit_tiptap_markdown_write(
            root=tmp_path,
            request=TiptapMarkdownWriteCommitRequest(
                document_id=record.document_id,
                markdown=markdown,
                writer_confirm_token="deadbeef",
                expected_revision=1,
            ),
        )
    assert "lossy" in str(exc_info.value)
    assert not (tmp_path / record.target_relpath).exists()


@pytest.mark.parametrize("kind", ["plan", "runbook"])
def test_lossy_markdown_is_advisory_for_plan_and_runbook(tmp_path: Path, kind: str) -> None:
    if kind == "plan":
        target = (
            "corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/"
            "Session Prep/Session 23 Prep.md"
        )
    else:
        target = "evals/c2_live_prep/mireward-prep/content/tiptap/advisory-lossy.md"
    record = create_workspace_document(
        tmp_path,
        title="Advisory Doc",
        campaign_id="eldyrwild",
        kind=kind,  # type: ignore[arg-type]
        target_relpath=target,
    )
    markdown = "# Title\n\n| a | b |\n| --- | --- |\n| 1 | 2 |\n"
    prepared = prepare_tiptap_markdown_write(
        root=tmp_path,
        request=TiptapMarkdownWritePrepareRequest(
            document_id=record.document_id,
            markdown=markdown,
            expected_revision=1,
        ),
    )
    assert prepared.writer_ok is True
    assert prepared.writer_confirm_token
    assert any("lossy" in item for item in prepared.diagnostics)
    assert any("advisory" in item.lower() for item in prepared.warnings)

    committed = commit_tiptap_markdown_write(
        root=tmp_path,
        request=TiptapMarkdownWriteCommitRequest(
            document_id=record.document_id,
            markdown=markdown,
            writer_confirm_token=prepared.writer_confirm_token,
            expected_revision=1,
        ),
    )
    assert committed.writer_ok is True
    assert (tmp_path / target).read_text(encoding="utf-8") == markdown


def test_plan_and_runbook_cannot_target_foreign_worldbuilding_path(tmp_path: Path) -> None:
    worldbuilding = create_workspace_document(
        tmp_path,
        title="World Lore",
        campaign_id="eldyrwild",
        kind="worldbuilding_source",
        source_domain="worldbuilding",
        document_class="lore",
        authority_state="draft",
        visibility_state="internal",
    )
    foreign_target = worldbuilding.target_relpath
    assert foreign_target
    original = tmp_path / foreign_target
    original.parent.mkdir(parents=True, exist_ok=True)
    original.write_text("# owned by worldbuilding\n", encoding="utf-8")

    for kind in ("plan", "runbook"):
        record = create_workspace_document(
            tmp_path,
            title=f"Cross-kind {kind}",
            campaign_id="eldyrwild",
            kind=kind,  # type: ignore[arg-type]
            target_relpath=foreign_target,
        )
        with pytest.raises(TiptapMarkdownWriteError):
            prepare_tiptap_markdown_write(
                root=tmp_path,
                request=TiptapMarkdownWritePrepareRequest(
                    document_id=record.document_id,
                    markdown="# hijack\n",
                    expected_revision=1,
                ),
            )
        with pytest.raises(TiptapMarkdownWriteError):
            commit_tiptap_markdown_write(
                root=tmp_path,
                request=TiptapMarkdownWriteCommitRequest(
                    document_id=record.document_id,
                    markdown="# hijack\n",
                    writer_confirm_token="deadbeef",
                    expected_revision=1,
                ),
            )
        assert original.read_text(encoding="utf-8") == "# owned by worldbuilding\n"


def test_authorize_target_binds_worldbuilding_to_own_document_id() -> None:
    own_id = "11111111-1111-4111-8111-111111111111"
    other_id = "22222222-2222-4222-8222-222222222222"
    record = WorkspaceDocumentRecord(
        document_id=own_id,
        title="WB",
        campaign_id="eldyrwild",
        kind="worldbuilding_source",
        target_relpath=f"out/workspace/worldbuilding/{other_id}.md",
        created_at="2026-01-01T00:00:00Z",
        updated_at="2026-01-01T00:00:00Z",
        source_domain="worldbuilding",
        document_class="lore",
        authority_state="draft",
        visibility_state="internal",
    )
    with pytest.raises(TiptapMarkdownWriteError):
        authorize_target_for_record(record)


def test_registry_failure_rolls_back_new_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    record = create_workspace_document(
        tmp_path,
        title="World Lore",
        campaign_id="eldyrwild",
        kind="worldbuilding_source",
        source_domain="worldbuilding",
        document_class="lore",
        authority_state="draft",
        visibility_state="internal",
    )
    markdown = "# Title\n\nBody.\n"
    prepared = prepare_tiptap_markdown_write(
        root=tmp_path,
        request=TiptapMarkdownWritePrepareRequest(
            document_id=record.document_id,
            markdown=markdown,
            expected_revision=1,
        ),
    )
    target = tmp_path / (record.target_relpath or "")
    assert not target.exists()

    def boom(*_args: object, **_kwargs: object) -> None:
        raise WorkspaceDocumentRegistryError("injected registry failure", status_code=500)

    monkeypatch.setattr(
        "apps.live_control_server.services.tiptap_markdown_write.mark_workspace_document_committed",
        boom,
    )
    with pytest.raises(TiptapMarkdownWriteError) as exc_info:
        commit_tiptap_markdown_write(
            root=tmp_path,
            request=TiptapMarkdownWriteCommitRequest(
                document_id=record.document_id,
                markdown=markdown,
                writer_confirm_token=prepared.writer_confirm_token or "",
                expected_revision=1,
            ),
        )
    assert exc_info.value.status_code == 500
    assert not target.exists()
    fresh = get_workspace_document(tmp_path, record.document_id)
    assert fresh.content_status == "draft"
    assert fresh.revision == record.revision


def test_registry_failure_restores_prior_file_bytes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    record = create_workspace_document(
        tmp_path,
        title="World Lore",
        campaign_id="eldyrwild",
        kind="worldbuilding_source",
        source_domain="worldbuilding",
        document_class="lore",
        authority_state="draft",
        visibility_state="internal",
    )
    target = tmp_path / (record.target_relpath or "")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("# prior\n", encoding="utf-8")
    markdown = "# Title\n\nReplacement.\n"
    prepared = prepare_tiptap_markdown_write(
        root=tmp_path,
        request=TiptapMarkdownWritePrepareRequest(
            document_id=record.document_id,
            markdown=markdown,
            expected_revision=1,
        ),
    )

    def boom(*_args: object, **_kwargs: object) -> None:
        raise WorkspaceDocumentRegistryError("injected registry failure", status_code=500)

    monkeypatch.setattr(
        "apps.live_control_server.services.tiptap_markdown_write.mark_workspace_document_committed",
        boom,
    )
    with pytest.raises(TiptapMarkdownWriteError):
        commit_tiptap_markdown_write(
            root=tmp_path,
            request=TiptapMarkdownWriteCommitRequest(
                document_id=record.document_id,
                markdown=markdown,
                writer_confirm_token=prepared.writer_confirm_token or "",
                expected_revision=1,
            ),
        )
    assert target.read_text(encoding="utf-8") == "# prior\n"


def test_discarded_document_cannot_write(tmp_path: Path) -> None:
    record = create_workspace_document(
        tmp_path,
        title="World Lore",
        campaign_id="eldyrwild",
        kind="worldbuilding_source",
        source_domain="worldbuilding",
        document_class="lore",
        authority_state="draft",
        visibility_state="internal",
    )
    discard_workspace_document(tmp_path, record.document_id)
    with pytest.raises(TiptapMarkdownWriteError):
        prepare_tiptap_markdown_write(
            root=tmp_path,
            request=TiptapMarkdownWritePrepareRequest(
                document_id=record.document_id,
                markdown="# Title\n\nBody.\n",
                expected_revision=2,
            ),
        )


def test_stale_revision_prepare_conflicts(tmp_path: Path) -> None:
    record = create_workspace_document(
        tmp_path,
        title="World Lore",
        campaign_id="eldyrwild",
        kind="worldbuilding_source",
        source_domain="worldbuilding",
        document_class="lore",
        authority_state="draft",
        visibility_state="internal",
    )
    with pytest.raises(TiptapMarkdownWriteError) as exc_info:
        prepare_tiptap_markdown_write(
            root=tmp_path,
            request=TiptapMarkdownWritePrepareRequest(
                document_id=record.document_id,
                markdown="# Title\n\nBody.\n",
                expected_revision=99,
            ),
        )
    assert exc_info.value.status_code == 409
