from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

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


def validate_source_artifact_scope(artifact: GraphMemorySourceArtifact) -> None:
    """Fail closed on invalid domain/scope combinations."""
    domain = str(artifact.source_domain)
    if domain == "recap":
        if not artifact.campaign_id or not artifact.session_id:
            raise ValueError("recap SourceArtifact requires campaign_id and session_id")
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
