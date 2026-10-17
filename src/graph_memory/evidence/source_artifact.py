from __future__ import annotations

import hashlib
import json
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from graph_memory.evidence.source_domain import SourceDomain

SOURCE_ARTIFACT_SCHEMA = "dmb_source_artifact_v1"


class GraphMemorySourceArtifact(BaseModel):
    """Canonical source artifact that can provide evidence for graph memory.

    Workspace document IDs and SourceArtifact IDs are separate namespaces.
    Worldbuilding sources may omit campaign/session scope.
    """

    model_config = ConfigDict(extra="allow", strict=True)

    schema_version: Literal["dmb_source_artifact_v1"] = SOURCE_ARTIFACT_SCHEMA
    source_artifact_id: str
    source_domain: SourceDomain | str
    # Legacy recap artifacts require campaign_id; worldbuilding may omit it.
    campaign_id: str | None = None
    session_id: str | None = None
    uri: str
    content_sha256: str | None = None
    artifact_kind: str | None = None
    document_class: str | None = None
    authority_state: Literal["draft", "reviewed", "canonical"] | None = None
    visibility_state: Literal["internal", "player_safe"] | None = None
    world_id: str | None = None
    workspace_document_id: str | None = None
    workspace_document_revision: int | None = None
    lineage: dict[str, Any] = Field(default_factory=dict)
    status: Literal["active", "superseded"] = "active"
    created_at: str | None = None
    updated_at: str | None = None

    @model_validator(mode="after")
    def _validate_persisted_invariants(self) -> GraphMemorySourceArtifact:
        validate_source_artifact_scope(self)
        return self


def build_worldbuilding_source_artifact_id(
    *,
    workspace_document_id: str,
    workspace_document_revision: int,
    content_sha256: str,
) -> str:
    """Stable, non-UUID artifact ID. Never equals the workspace document UUID."""
    digest_prefix = content_sha256[:12]
    return (
        f"artifact:worldbuilding:{workspace_document_id}:"
        f"r{workspace_document_revision}:{digest_prefix}"
    )


def build_recap_source_artifact_id(
    *,
    campaign_id: str,
    session_id: str,
    content_sha256: str,
) -> str:
    """Stable recap artifact ID bound to campaign, session, and content digest."""
    digest_prefix = content_sha256.removeprefix("sha256:")[:12]
    return f"artifact:recap:{campaign_id}:{session_id}:{digest_prefix}"


def build_world_scoped_recap_source_artifact_id(
    *,
    world_id: str,
    campaign_id: str,
    session_id: str,
    content_sha256: str,
) -> str:
    """Build a fresh recap identity scoped by World and the complete content digest.

    Legacy ``artifact:recap:<campaign>:<session>:<digest-prefix>`` IDs remain
    readable, but new sources use this namespace so identical recaps in
    separate Worlds cannot alias.
    """
    values = (world_id, campaign_id, session_id)
    if any(not value or value != value.strip() for value in values):
        raise ValueError("world-scoped recap identity requires normalized World/campaign/session IDs")
    digest = content_sha256.removeprefix("sha256:").strip().lower()
    if len(digest) != 64 or any(char not in "0123456789abcdef" for char in digest):
        raise ValueError("world-scoped recap identity requires a full SHA-256 content digest")
    canonical_tuple = json.dumps(
        [world_id, campaign_id, session_id, digest],
        ensure_ascii=False,
        separators=(",", ":"),
    )
    identity_digest = hashlib.sha256(canonical_tuple.encode("utf-8")).hexdigest()
    return f"artifact:recap:v2:{identity_digest}"


def validate_source_artifact_scope(artifact: GraphMemorySourceArtifact) -> None:
    """Fail closed on invalid domain/scope combinations."""
    domain = str(artifact.source_domain)
    if domain == "recap":
        if not artifact.campaign_id or not artifact.session_id:
            raise ValueError("recap SourceArtifact requires campaign_id and session_id")
        if artifact.source_artifact_id.startswith("artifact:recap:v2:"):
            if not artifact.world_id:
                raise ValueError("World-scoped recap SourceArtifact requires world_id")
            if not artifact.content_sha256:
                raise ValueError("World-scoped recap SourceArtifact requires content_sha256")
            expected_id = build_world_scoped_recap_source_artifact_id(
                world_id=artifact.world_id,
                campaign_id=artifact.campaign_id,
                session_id=artifact.session_id,
                content_sha256=artifact.content_sha256,
            )
            if artifact.source_artifact_id != expected_id:
                raise ValueError("World-scoped recap SourceArtifact ID does not match its identity")
    if domain == "worldbuilding":
        if artifact.session_id is not None:
            raise ValueError("worldbuilding SourceArtifact must not fabricate a session_id")
    if artifact.workspace_document_id is not None:
        if artifact.source_artifact_id == artifact.workspace_document_id:
            raise ValueError(
                "SourceArtifact ID must not equal workspace_document_id"
            )
        if artifact.workspace_document_revision is None or artifact.workspace_document_revision < 1:
            raise ValueError("workspace_document_revision is required with workspace_document_id")
        if not artifact.content_sha256:
            raise ValueError("content_sha256 is required with workspace_document_id")
