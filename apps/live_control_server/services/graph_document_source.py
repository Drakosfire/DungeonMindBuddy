"""Exact registered Build revisions as governed authoring sources, without extraction."""
from __future__ import annotations

import hashlib
import json
import os
import uuid
from pathlib import Path
from types import SimpleNamespace

from pydantic import BaseModel, ConfigDict, Field

from apps.live_control_server.config import artifact_data_root
from apps.live_control_server.services.registry_file_lock import workspace_document_mutation_lock
from apps.live_control_server.services.source_artifact_registry import (
    SourceArtifactRegistryError,
    _create_source_artifact_from_workspace_document_unlocked,
    _read_committed_target_markdown,
    get_source_artifact,
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


def _paths(root: Path, artifact_id: str) -> tuple[Path, Path]:
    base = root / "out/registries/source_content/graph_documents" / hashlib.sha256(artifact_id.encode()).hexdigest()
    if not base.resolve().is_relative_to(root.resolve()):
        raise SourceArtifactRegistryError("Frozen document source escapes its repository", status_code=409)
    return base / "source.md", base / "source_span_index.json"


def _write_once(path: Path, raw: bytes) -> None:
    """Never replace a historical component; interrupted writes are errors, not new authority."""
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    temporary = path.with_name("." + path.name + "." + uuid.uuid4().hex + ".tmp")
    try:
        with temporary.open("xb") as handle:
            os.chmod(temporary, 0o600)
            handle.write(raw)
            handle.flush()
            os.fsync(handle.fileno())
        try:
            os.link(temporary, path)
        except FileExistsError:
            if path.is_symlink() or path.read_bytes() != raw:
                raise SourceArtifactRegistryError("Frozen document source component changed", status_code=409)
        fd = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)
    finally:
        temporary.unlink(missing_ok=True)


def frozen_document_source(root: Path, artifact) -> tuple[Path, Path] | None:
    """Resolve only an exact artifact-derived snapshot; no caller path or latest lookup."""
    root = artifact_data_root(root)
    body, index = _paths(root, artifact.source_artifact_id)
    if not body.exists() and not index.exists():
        return None
    try:
        if body.is_symlink() or index.is_symlink():
            raise ValueError("symlink component")
        raw = body.read_bytes()
        text = raw.decode("utf-8")
        if hashlib.sha256(raw).hexdigest() != artifact.content_sha256:
            raise ValueError("body digest changed")
        expected = source_span_index_to_dict(build_source_span_index_for_text(
            source_artifact_id=artifact.source_artifact_id,
            content_sha256=artifact.content_sha256, text=text))
        if json.loads(index.read_bytes()) != expected:
            raise ValueError("span index changed")
    except (OSError, ValueError, TypeError, KeyError, UnicodeDecodeError) as exc:
        raise SourceArtifactRegistryError("Frozen document source is unavailable or changed", status_code=409) from exc
    return body, index


def resolve_graph_document_source(root: Path, selector: GraphDocumentSource, *, world_id: str, campaign_id: str):
    """Freeze current saved bytes once; subsequent exact retries use that immutable revision."""
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
        body, index = _paths(root, artifact_id)
        # Only a complete retained source permits historical recovery. A partial
        # first freeze can retry against the still-current saved revision.
        if body.exists() and index.exists():
            artifact = get_source_artifact(root, artifact_id)
        else:
            artifact = _create_source_artifact_from_workspace_document_unlocked(root,
                document_id=selector.document_id, expected_revision=selector.revision,
                expected_content_sha256=selector.content_sha256)
            _, text, digest = _read_committed_target_markdown(root, record)
            if digest != selector.content_sha256:
                raise SourceArtifactRegistryError("Document source changed before freezing", status_code=409)
            _write_once(body, text.encode("utf-8"))
            payload = source_span_index_to_dict(build_source_span_index_for_text(
                source_artifact_id=artifact_id, content_sha256=digest, text=text))
            _write_once(index, (json.dumps(payload, sort_keys=True, ensure_ascii=False) + "\n").encode())
        if (artifact.source_domain != "worldbuilding" or artifact.world_id != world_id
                or artifact.campaign_id != campaign_id or artifact.status != "active"
                or artifact.workspace_document_id != selector.document_id
                or artifact.workspace_document_revision != selector.revision
                or artifact.content_sha256 != selector.content_sha256):
            raise SourceArtifactRegistryError("Retained document source identity changed", status_code=409)
        frozen_document_source(root, artifact)
        return SimpleNamespace(source_artifact=artifact, source_artifact_id=artifact_id,
            source_revision_id="sha256:" + selector.content_sha256,
            source_domain="worldbuilding", campaign_id=campaign_id, world_id=world_id, session_id=None,
            document_source_selector=selector.model_dump(mode="json", by_alias=True),
            sealed_source_uri="repo://" + body.relative_to(root).as_posix(),
            source_span_index_path=index, source_span_index_sha256=hashlib.sha256(index.read_bytes()).hexdigest())
