from __future__ import annotations

import hashlib

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
