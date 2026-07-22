from __future__ import annotations

from pathlib import Path

import pytest

from apps.live_control_server.services.tiptap_markdown_write import (
    TiptapMarkdownWriteCommitRequest,
    TiptapMarkdownWriteError,
    TiptapMarkdownWritePrepareRequest,
    commit_tiptap_markdown_write,
    markdown_lossy_diagnostics,
    normalize_tiptap_target_relpath,
    prepare_tiptap_markdown_write,
)
from apps.live_control_server.services.workspace_document_registry import (
    create_workspace_document,
    discard_workspace_document,
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


def test_lossy_markdown_blocks_prepare_and_commit(tmp_path: Path) -> None:
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
