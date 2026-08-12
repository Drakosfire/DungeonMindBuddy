from __future__ import annotations

import hashlib
from pathlib import Path

import pytest
from pydantic import ValidationError

from graph_memory.evidence.source_artifact import (
    GraphMemorySourceArtifact,
    build_worldbuilding_source_artifact_id,
    validate_source_artifact_scope,
)


def test_legacy_recap_artifact_still_validates() -> None:
    artifact = GraphMemorySourceArtifact(
        source_artifact_id="artifact:recap:longmont-c2:session-1",
        source_domain="recap",
        campaign_id="longmont-c2",
        session_id="session-1",
        uri="repo://recaps/session-1.md",
    )
    validate_source_artifact_scope(artifact)
    assert artifact.campaign_id == "longmont-c2"


def test_worldbuilding_artifact_allows_null_session() -> None:
    workspace_id = "11111111-1111-4111-8111-111111111111"
    digest = hashlib.sha256(b"# Lore\n").hexdigest()
    artifact_id = build_worldbuilding_source_artifact_id(
        workspace_document_id=workspace_id,
        workspace_document_revision=2,
        content_sha256=digest,
    )
    assert artifact_id != workspace_id
    artifact = GraphMemorySourceArtifact(
        source_artifact_id=artifact_id,
        source_domain="worldbuilding",
        campaign_id="eldyrwild",
        session_id=None,
        uri="repo://out/workspace/worldbuilding/x.md",
        content_sha256=digest,
        workspace_document_id=workspace_id,
        workspace_document_revision=2,
        document_class="lore",
        authority_state="draft",
        visibility_state="internal",
    )
    validate_source_artifact_scope(artifact)
    assert artifact.session_id is None


def test_worldbuilding_rejects_fabricated_session() -> None:
    with pytest.raises(ValidationError, match="must not fabricate a session_id"):
        GraphMemorySourceArtifact(
            source_artifact_id="artifact:worldbuilding:x",
            source_domain="worldbuilding",
            campaign_id="eldyrwild",
            session_id="session-1",
            uri="repo://x.md",
        )


def test_workspace_id_cannot_equal_source_artifact_id() -> None:
    workspace_id = "11111111-1111-4111-8111-111111111111"
    with pytest.raises(ValidationError, match="must not equal workspace_document_id"):
        GraphMemorySourceArtifact(
            source_artifact_id=workspace_id,
            source_domain="worldbuilding",
            campaign_id="eldyrwild",
            uri="repo://x.md",
            content_sha256="abc",
            workspace_document_id=workspace_id,
            workspace_document_revision=1,
        )


def test_world_scoped_source_artifact_uses_record_world_id(tmp_path: Path) -> None:
    from apps.live_control_server.services.source_artifact_registry import (
        create_source_artifact_from_workspace_document,
    )
    from apps.live_control_server.services.tiptap_markdown_write import (
        TiptapMarkdownWriteCommitRequest,
        TiptapMarkdownWritePrepareRequest,
        commit_tiptap_markdown_write,
        prepare_tiptap_markdown_write,
    )
    from apps.live_control_server.services.workspace_document_registry import (
        create_workspace_document,
    )

    (tmp_path / "corpus" / "eldyrwild-markdown").mkdir(parents=True)
    record = create_workspace_document(
        tmp_path,
        title="World Source",
        campaign_id="longmont-c2",
        kind="worldbuilding_source",
        world_id="eldyrwild",
        source_domain="worldbuilding",
        document_class="lore",
        authority_state="draft",
        visibility_state="internal",
    )
    markdown = "# Lore\n\nImported bytes.\n"
    prepared = prepare_tiptap_markdown_write(
        root=tmp_path,
        request=TiptapMarkdownWritePrepareRequest(
            document_id=record.document_id,
            markdown=markdown,
            expected_revision=1,
            write_mode="source_import",
        ),
    )
    commit_tiptap_markdown_write(
        root=tmp_path,
        request=TiptapMarkdownWriteCommitRequest(
            document_id=record.document_id,
            markdown=markdown,
            writer_confirm_token=prepared.writer_confirm_token or "",
            expected_revision=1,
            write_mode="source_import",
        ),
    )
    artifact = create_source_artifact_from_workspace_document(
        tmp_path,
        document_id=record.document_id,
        expected_revision=2,
    )
    assert artifact.world_id == "eldyrwild"
    assert artifact.campaign_id == "longmont-c2"


def test_legacy_worldbuilding_source_artifact_uses_campaign_id_compat(tmp_path: Path) -> None:
    from apps.live_control_server.services.source_artifact_registry import (
        create_source_artifact_from_workspace_document,
    )
    from apps.live_control_server.services.tiptap_markdown_write import (
        TiptapMarkdownWriteCommitRequest,
        TiptapMarkdownWritePrepareRequest,
        commit_tiptap_markdown_write,
        prepare_tiptap_markdown_write,
    )
    from apps.live_control_server.services.workspace_document_registry import (
        create_workspace_document,
    )

    record = create_workspace_document(
        tmp_path,
        title="Legacy Source",
        campaign_id="eldyrwild",
        kind="worldbuilding_source",
        source_domain="worldbuilding",
        document_class="lore",
        authority_state="draft",
        visibility_state="internal",
    )
    markdown = "# Legacy\n\nBody.\n"
    prepared = prepare_tiptap_markdown_write(
        root=tmp_path,
        request=TiptapMarkdownWritePrepareRequest(
            document_id=record.document_id,
            markdown=markdown,
            expected_revision=1,
        ),
    )
    commit_tiptap_markdown_write(
        root=tmp_path,
        request=TiptapMarkdownWriteCommitRequest(
            document_id=record.document_id,
            markdown=markdown,
            writer_confirm_token=prepared.writer_confirm_token or "",
            expected_revision=1,
        ),
    )
    artifact = create_source_artifact_from_workspace_document(
        tmp_path,
        document_id=record.document_id,
        expected_revision=2,
    )
    assert artifact.world_id == "eldyrwild"
    assert record.world_id is None
