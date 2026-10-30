from __future__ import annotations

import hashlib
import os
from pathlib import Path

import pytest
from pydantic import ValidationError

from graph_memory.evidence.source_artifact import (
    GraphMemorySourceArtifact,
    build_worldbuilding_source_artifact_id,
    build_world_scoped_recap_source_artifact_id,
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


def test_world_scoped_recap_id_uses_full_digest_and_unambiguous_world_scope() -> None:
    digest = hashlib.sha256(b"same recap").hexdigest()
    same_world = build_world_scoped_recap_source_artifact_id(
        world_id="world:elderwyld",
        campaign_id="longmont-c2",
        session_id="session-29",
        content_sha256=digest,
    )
    assert same_world == build_world_scoped_recap_source_artifact_id(
        world_id="world:elderwyld",
        campaign_id="longmont-c2",
        session_id="session-29",
        content_sha256=f"sha256:{digest}",
    )
    assert same_world != build_world_scoped_recap_source_artifact_id(
        world_id="world:conks-and-cons",
        campaign_id="longmont-c2",
        session_id="session-29",
        content_sha256=digest,
    )
    assert same_world != build_world_scoped_recap_source_artifact_id(
        world_id="world:elderwyld",
        campaign_id="longmont-c2",
        session_id="session-29",
        content_sha256=hashlib.sha256(b"different recap").hexdigest(),
    )
    assert same_world.startswith("artifact:recap:v2:")


def test_world_scoped_recap_artifact_rejects_missing_or_forged_world_identity() -> None:
    digest = hashlib.sha256(b"recap").hexdigest()
    artifact_id = build_world_scoped_recap_source_artifact_id(
        world_id="world:elderwyld",
        campaign_id="longmont-c2",
        session_id="session-29",
        content_sha256=digest,
    )
    with pytest.raises(ValidationError, match="requires world_id"):
        GraphMemorySourceArtifact(
            source_artifact_id=artifact_id,
            source_domain="recap",
            campaign_id="longmont-c2",
            session_id="session-29",
            uri="repo://recaps/session-29.md",
            content_sha256=digest,
        )
    with pytest.raises(ValidationError, match="ID does not match its identity"):
        GraphMemorySourceArtifact(
            source_artifact_id=artifact_id,
            source_domain="recap",
            campaign_id="longmont-c2",
            session_id="session-29",
            world_id="world:conks-and-cons",
            uri="repo://recaps/session-29.md",
            content_sha256=digest,
        )


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


def test_registered_source_byte_loader_preserves_exact_database_bytes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, application_state_dsn: str,
) -> None:
    import json

    from apps.live_control_server.services.source_artifact_registry import (
        SourceArtifactRegistryError,
        load_registered_source_artifact_bytes,
        source_artifacts_path,
    )

    content = b"First line\r\nSecond line\r\n"
    digest = hashlib.sha256(content).hexdigest()
    artifact = GraphMemorySourceArtifact(
        source_artifact_id="artifact:recap:campaign:session:exact-bytes",
        source_domain="recap", campaign_id="campaign", session_id="session",
        uri="repo://source.md", content_sha256=digest,
    )
    (tmp_path / "source.md").write_bytes(content)
    registry = source_artifacts_path(tmp_path)
    registry.parent.mkdir(parents=True, exist_ok=True)
    registry.write_text(json.dumps({
        "schema_version": "dmb_source_artifact_registry_v1",
        "records": [artifact.model_dump(mode="json")],
    }))

    from application_state.source.service import persist_source_markdown
    monkeypatch.setenv("DMB_ARTIFACT_DATA_ROOT", str(tmp_path))
    saved = persist_source_markdown(
        source_artifact_id=artifact.source_artifact_id, source_domain="recap",
        campaign_id=artifact.campaign_id, session_id=artifact.session_id,
        world_id=artifact.world_id, markdown=content.decode("utf-8"), content_sha256=digest,
    )

    loaded, exact = load_registered_source_artifact_bytes(
        tmp_path, artifact.source_artifact_id,
    )
    assert loaded == artifact
    assert exact == content

    (tmp_path / "source.md").write_bytes(b"First line\nSecond line\n")
    assert load_registered_source_artifact_bytes(tmp_path, artifact.source_artifact_id)[1] == content
    import psycopg
    with psycopg.connect(application_state_dsn) as conn:
        conn.execute("UPDATE source.revision SET markdown=%s WHERE source_revision_id=%s",
                     ("First line\nSecond line\n", saved.source_revision_id))
    with pytest.raises(SourceArtifactRegistryError, match="digest mismatch"):
        load_registered_source_artifact_bytes(tmp_path, artifact.source_artifact_id)


def test_registered_source_byte_loader_does_not_follow_symlink_locator(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, application_state_dsn: str,
) -> None:
    import json

    from apps.live_control_server.services.source_artifact_registry import (
        SourceArtifactRegistryError,
        load_registered_source_artifact_bytes,
        source_artifacts_path,
    )

    content = b"Immutable source\n"
    digest = hashlib.sha256(content).hexdigest()
    artifact = GraphMemorySourceArtifact(
        source_artifact_id="artifact:recap:campaign:session:symlink",
        source_domain="recap", campaign_id="campaign", session_id="session",
        uri="repo://alias/source.md", content_sha256=digest,
    )
    target = tmp_path / "actual"
    target.mkdir()
    (target / "source.md").write_bytes(content)
    (tmp_path / "alias").symlink_to(target, target_is_directory=True)
    registry = source_artifacts_path(tmp_path)
    registry.parent.mkdir(parents=True, exist_ok=True)
    registry.write_text(json.dumps({
        "schema_version": "dmb_source_artifact_registry_v1",
        "records": [artifact.model_dump(mode="json")],
    }))

    from application_state.source.service import persist_source_markdown
    from apps.live_control_server.services import source_artifact_registry
    monkeypatch.setenv("DMB_ARTIFACT_DATA_ROOT", str(tmp_path))
    persist_source_markdown(
        source_artifact_id=artifact.source_artifact_id, source_domain="recap",
        campaign_id=artifact.campaign_id, session_id=artifact.session_id,
        world_id=artifact.world_id, markdown=content.decode("utf-8"), content_sha256=digest,
    )
    (target / "source.md").write_bytes(b"Unrelated file bytes")
    monkeypatch.setattr(source_artifact_registry, "_read_exact_repo_uri_bytes",
                        lambda *args: pytest.fail("Database body read followed a file locator"))
    assert load_registered_source_artifact_bytes(tmp_path, artifact.source_artifact_id)[1] == content


@pytest.mark.skipif(not hasattr(os, "mkfifo"), reason="FIFO paths require POSIX")
def test_exact_source_reader_rejects_fifo_without_blocking(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    from apps.live_control_server.services import source_artifact_registry
    from apps.live_control_server.services.source_artifact_registry import (
        SourceArtifactRegistryError,
    )

    fifo = tmp_path / "component.fifo"
    os.mkfifo(fifo)
    original_open = os.open

    def require_nonblocking(path, flags, *args, **kwargs):
        if path == fifo.name:
            assert flags & os.O_NONBLOCK
        return original_open(path, flags, *args, **kwargs)

    monkeypatch.setattr(source_artifact_registry.os, "open", require_nonblocking)
    with pytest.raises(SourceArtifactRegistryError, match="not a regular file"):
        source_artifact_registry._read_exact_repo_uri_bytes(tmp_path, "repo://component.fifo")
