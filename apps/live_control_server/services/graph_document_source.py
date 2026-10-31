"""Exact registered Build revisions as governed authoring sources, without extraction."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

from pydantic import BaseModel, ConfigDict, Field

from apps.live_control_server.config import artifact_data_root
from apps.live_control_server.services.registry_file_lock import workspace_document_mutation_lock
from apps.live_control_server.services.source_artifact_registry import (
    SourceArtifactRegistryError,
    _create_source_artifact_from_workspace_document_unlocked,
    get_source_artifact,
    load_registered_source_artifact_bytes,
)
from apps.live_control_server.services.workspace_document_registry import (
    load_workspace_document_under_registry_lock,
)
from graph_memory.evidence.source_artifact import build_worldbuilding_source_artifact_id
from graph_memory.source_span import build_source_span_index_for_text, source_span_index_to_dict


class GraphDocumentSource(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True, strict=True)
    document_id: str = Field(alias="documentId", pattern=r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,199}$")
    revision: int = Field(ge=1)
    content_sha256: str = Field(alias="contentSha256", pattern=r"^[a-f0-9]{64}$")


def _document_source_uri(artifact_id: str) -> str:
    # Preserve the exact historical review locator spelling. It is an identity
    # in retained seals, never a file to create, discover or read.
    return ("repo://out/registries/source_content/graph_documents/"
            + hashlib.sha256(artifact_id.encode()).hexdigest() + "/source.md")


def resolve_graph_document_source(root: Path, selector: GraphDocumentSource, *, world_id: str, campaign_id: str):
    """Capture an exact saved revision once in APP; replay the immutable DB source."""
    root = artifact_data_root(root)
    with workspace_document_mutation_lock(root, selector.document_id):
        record = load_workspace_document_under_registry_lock(root, selector.document_id)
        if (record.kind != "worldbuilding_source" or record.status != "active"
                or record.world_id != world_id or record.campaign_id != campaign_id
                or world_id != campaign_id):
            raise SourceArtifactRegistryError("Document source does not belong to this managed World", status_code=409)
        artifact_id = build_worldbuilding_source_artifact_id(
            workspace_document_id=selector.document_id,
            workspace_document_revision=selector.revision, content_sha256=selector.content_sha256)
        try:
            artifact = get_source_artifact(root, artifact_id)
        except SourceArtifactRegistryError as exc:
            if exc.status_code != 404:
                raise
            artifact = _create_source_artifact_from_workspace_document_unlocked(root,
                document_id=selector.document_id, expected_revision=selector.revision,
                expected_content_sha256=selector.content_sha256)
        if (artifact.source_domain != "worldbuilding" or artifact.world_id != world_id
                or artifact.campaign_id != campaign_id or artifact.status != "active"
                or artifact.workspace_document_id != selector.document_id
                or artifact.workspace_document_revision != selector.revision
                or artifact.content_sha256 != selector.content_sha256):
            raise SourceArtifactRegistryError("Retained document source identity changed", status_code=409)
        stored, raw = load_registered_source_artifact_bytes(root, artifact_id)
        if stored != artifact:
            raise SourceArtifactRegistryError("Retained document source identity changed", status_code=409)
        index = source_span_index_to_dict(build_source_span_index_for_text(
            source_artifact_id=artifact_id, content_sha256=selector.content_sha256,
            text=raw.decode("utf-8")))
        index_bytes = (json.dumps(index, sort_keys=True, ensure_ascii=False) + "\n").encode()
        return SimpleNamespace(source_artifact=artifact, source_artifact_id=artifact_id,
            source_revision_id="sha256:" + selector.content_sha256,
            source_domain="worldbuilding", campaign_id=campaign_id, world_id=world_id, session_id=None,
            document_source_selector=selector.model_dump(mode="json", by_alias=True),
            sealed_source_uri=_document_source_uri(artifact_id),
            source_span_index=index, source_span_index_sha256=hashlib.sha256(index_bytes).hexdigest())
