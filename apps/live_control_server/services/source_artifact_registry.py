"""Server-owned SourceArtifact registry for committed workspace revisions."""

from __future__ import annotations

import hashlib
import re
from datetime import UTC, datetime
from pathlib import Path

from pydantic import BaseModel, Field, ValidationError

from apps.live_control_server.services.tiptap_markdown_write import (
    TiptapMarkdownWriteError,
    authorize_target_for_record,
    resolve_tiptap_markdown_target,
)
from apps.live_control_server.services.workspace_document_registry import (
    WorkspaceDocumentRegistryError,
    get_workspace_document,
)
from graph_memory.evidence.source_artifact import (
    GraphMemorySourceArtifact,
    build_worldbuilding_source_artifact_id,
    validate_source_artifact_scope,
)
from graph_memory.source_span import (
    SourceSpanIndex,
    build_source_span_index_for_text,
    source_artifact_text_from_markdown,
    source_span_index_from_dict,
    source_span_index_to_dict,
    source_span_refs_from_index,
    validate_source_span_index,
    resolve_source_span_ref,
)
from apps.live_control_server.services.registry_file_lock import (
    registry_mutation_lock,
    registry_token,
)
from src.live_play.live_store import load_json, write_json

DEFAULT_SOURCE_ARTIFACT_REGISTRY_REL = "out/registries/source_artifacts.json"
DEFAULT_SOURCE_SPAN_INDEX_DIR_REL = "out/registries/source_span_indexes"
SOURCE_ARTIFACT_REGISTRY_SCHEMA = "dmb_source_artifact_registry_v1"

_SAFE_ARTIFACT_DIR_RE = re.compile(r"[^A-Za-z0-9._-]+")


class SourceArtifactRegistryError(ValueError):
    status_code: int = 404

    def __init__(self, message: str, *, status_code: int = 404) -> None:
        super().__init__(message)
        self.status_code = status_code


class SourceArtifactRegistryDocument(BaseModel):
    schema_version: str = SOURCE_ARTIFACT_REGISTRY_SCHEMA
    records: list[GraphMemorySourceArtifact] = Field(default_factory=list)


def _utc_now_iso() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def source_artifacts_path(root: Path) -> Path:
    return root / DEFAULT_SOURCE_ARTIFACT_REGISTRY_REL


def _normalize_committed_markdown(markdown: str) -> str:
    """Match the Tiptap writer contract: trailing newline, non-empty body."""
    if not markdown.strip():
        raise SourceArtifactRegistryError(
            "committed source file is empty",
            status_code=422,
        )
    return markdown.rstrip("\n") + "\n"


def _artifact_dir_name(source_artifact_id: str) -> str:
    return _SAFE_ARTIFACT_DIR_RE.sub("_", source_artifact_id)


def source_span_index_relpath(source_artifact_id: str) -> str:
    return (
        f"{DEFAULT_SOURCE_SPAN_INDEX_DIR_REL}/"
        f"{_artifact_dir_name(source_artifact_id)}/source_span_index.json"
    )


def source_span_index_path(root: Path, source_artifact_id: str) -> Path:
    return root / source_span_index_relpath(source_artifact_id)


def _validate_registry_records(records: list[GraphMemorySourceArtifact]) -> None:
    seen: set[str] = set()
    for record in records:
        try:
            validate_source_artifact_scope(record)
        except ValueError as exc:
            raise SourceArtifactRegistryError(
                f"malformed source artifact registry record: {exc}",
                status_code=500,
            ) from exc
        if record.source_artifact_id in seen:
            raise SourceArtifactRegistryError(
                f"duplicate source artifact id: {record.source_artifact_id}",
                status_code=500,
            )
        seen.add(record.source_artifact_id)


def _load_unlocked(root: Path) -> tuple[SourceArtifactRegistryDocument, str]:
    path = source_artifacts_path(root)
    token = registry_token(path)
    if not path.is_file():
        return SourceArtifactRegistryDocument(), token
    try:
        document = SourceArtifactRegistryDocument.model_validate(load_json(path))
    except (ValidationError, TypeError, ValueError) as exc:
        raise SourceArtifactRegistryError(
            f"malformed source artifact registry: {exc}",
            status_code=500,
        ) from exc
    _validate_registry_records(document.records)
    return document, token


def _load(root: Path) -> SourceArtifactRegistryDocument:
    document, _token = _load_unlocked(root)
    return document


def _save_cas(
    root: Path,
    document: SourceArtifactRegistryDocument,
    *,
    expected_token: str,
) -> None:
    _validate_registry_records(document.records)
    path = source_artifacts_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    current = registry_token(path)
    if current != expected_token:
        raise SourceArtifactRegistryError(
            "source artifact registry changed concurrently",
            status_code=409,
        )
    write_json(path, document.model_dump(mode="json"))


def _read_committed_target_markdown(root: Path, record) -> tuple[str, str, str]:
    """Resolve BLD-02 target, read committed bytes, return (relpath, markdown, digest)."""
    try:
        relpath = authorize_target_for_record(record)
        target = resolve_tiptap_markdown_target(root, relpath)
    except TiptapMarkdownWriteError as exc:
        raise SourceArtifactRegistryError(str(exc), status_code=422) from exc
    if not target.is_file():
        raise SourceArtifactRegistryError(
            "committed workspace target file is missing",
            status_code=409,
        )
    try:
        raw = target.read_text(encoding="utf-8")
    except OSError as exc:
        raise SourceArtifactRegistryError(
            f"failed to read committed workspace target: {exc}",
            status_code=500,
        ) from exc
    content = _normalize_committed_markdown(raw)
    digest = hashlib.sha256(content.encode("utf-8")).hexdigest()
    return relpath, content, digest


def _records_match(existing: GraphMemorySourceArtifact, candidate: GraphMemorySourceArtifact) -> bool:
    fields = (
        "source_artifact_id",
        "source_domain",
        "campaign_id",
        "session_id",
        "uri",
        "content_sha256",
        "artifact_kind",
        "document_class",
        "workspace_document_id",
        "workspace_document_revision",
    )
    return all(getattr(existing, field) == getattr(candidate, field) for field in fields)


def _persist_span_index(root: Path, index: SourceSpanIndex) -> str:
    validate_source_span_index(
        index,
        source_artifact_id=index.source_artifact_id,
        content_sha256=index.content_sha256,
    )
    relpath = source_span_index_relpath(index.source_artifact_id)
    path = root / relpath
    path.parent.mkdir(parents=True, exist_ok=True)
    write_json(path, source_span_index_to_dict(index))
    return relpath


def load_source_span_index(root: Path, source_artifact_id: str) -> SourceSpanIndex:
    path = source_span_index_path(root, source_artifact_id)
    if not path.is_file():
        raise SourceArtifactRegistryError(
            f"source span index not found for artifact: {source_artifact_id}",
            status_code=404,
        )
    try:
        payload = load_json(path)
        index = source_span_index_from_dict(payload)
    except (TypeError, ValueError, KeyError, ValidationError) as exc:
        raise SourceArtifactRegistryError(
            f"malformed source span index: {exc}",
            status_code=500,
        ) from exc
    artifact = get_source_artifact(root, source_artifact_id)
    try:
        validate_source_span_index(
            index,
            source_artifact_id=artifact.source_artifact_id,
            content_sha256=artifact.content_sha256 or "",
        )
    except ValueError as exc:
        raise SourceArtifactRegistryError(str(exc), status_code=500) from exc
    return index


def resolve_worldbuilding_source_span(
    root: Path,
    source_artifact_id: str,
    *,
    span_index: int = 0,
):
    """Load one persisted worldbuilding span and resolve it through the evidence resolver."""
    artifact = get_source_artifact(root, source_artifact_id)
    if str(artifact.source_domain) != "worldbuilding":
        raise SourceArtifactRegistryError(
            "resolve_worldbuilding_source_span requires a worldbuilding artifact",
            status_code=422,
        )
    if not artifact.uri.startswith("repo://"):
        raise SourceArtifactRegistryError("artifact uri must be repo-relative", status_code=500)
    relpath = artifact.uri.removeprefix("repo://")
    try:
        target = resolve_tiptap_markdown_target(root, relpath)
        text = _normalize_committed_markdown(target.read_text(encoding="utf-8"))
    except (TiptapMarkdownWriteError, OSError) as exc:
        raise SourceArtifactRegistryError(
            f"failed to load artifact text for span resolution: {exc}",
            status_code=500,
        ) from exc
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    if digest != (artifact.content_sha256 or ""):
        raise SourceArtifactRegistryError(
            "artifact content digest mismatch during span resolution",
            status_code=409,
        )
    index = load_source_span_index(root, source_artifact_id)
    refs = source_span_refs_from_index(index)
    if not refs:
        raise SourceArtifactRegistryError("source span index has no spans", status_code=500)
    if span_index < 0 or span_index >= len(refs):
        raise SourceArtifactRegistryError("span_index out of range", status_code=404)
    text_artifact = source_artifact_text_from_markdown(
        source_artifact_id=artifact.source_artifact_id,
        text=text,
        label=artifact.document_class or artifact.source_artifact_id,
        visibility_state=artifact.visibility_state or "internal",
    )
    return resolve_source_span_ref(
        refs[span_index],
        text_artifacts={artifact.source_artifact_id: text_artifact},
    )


def get_source_artifact(root: Path, source_artifact_id: str) -> GraphMemorySourceArtifact:
    document = _load(root)
    for record in document.records:
        if record.source_artifact_id == source_artifact_id:
            return record
    raise SourceArtifactRegistryError(
        f"source artifact not found: {source_artifact_id}",
        status_code=404,
    )


def create_source_artifact_from_workspace_document(
    root: Path,
    *,
    document_id: str,
    expected_revision: int | None = None,
    expected_content_sha256: str | None = None,
) -> GraphMemorySourceArtifact:
    """Create an immutable SourceArtifact from a committed worldbuilding workspace revision.

    Markdown bytes are server-resolved from the BLD-02 target. A client-supplied digest is
    accepted only as an assertion that must match the committed file.
    """
    try:
        record = get_workspace_document(root, document_id)
    except WorkspaceDocumentRegistryError as exc:
        err = SourceArtifactRegistryError(str(exc), status_code=exc.status_code)
        raise err from exc

    if record.kind != "worldbuilding_source":
        raise SourceArtifactRegistryError(
            "only worldbuilding_source documents can create worldbuilding SourceArtifacts",
            status_code=422,
        )
    if record.status != "active":
        raise SourceArtifactRegistryError(
            "discarded workspace documents cannot create SourceArtifacts",
            status_code=409,
        )
    if record.content_status != "committed":
        raise SourceArtifactRegistryError(
            "workspace document must be committed before SourceArtifact creation",
            status_code=422,
        )
    if expected_revision is not None and record.revision != expected_revision:
        raise SourceArtifactRegistryError(
            f"revision mismatch: expected {expected_revision}, current {record.revision}",
            status_code=409,
        )
    if not record.target_relpath:
        raise SourceArtifactRegistryError(
            "workspace document has no target_relpath",
            status_code=422,
        )

    relpath, content, content_sha256 = _read_committed_target_markdown(root, record)
    if expected_content_sha256 is not None:
        expected = expected_content_sha256.removeprefix("sha256:").strip().lower()
        if expected != content_sha256:
            raise SourceArtifactRegistryError(
                "expected_content_sha256 does not match committed source bytes",
                status_code=409,
            )

    source_artifact_id = build_worldbuilding_source_artifact_id(
        workspace_document_id=record.document_id,
        workspace_document_revision=record.revision,
        content_sha256=content_sha256,
    )

    now = _utc_now_iso()
    candidate = GraphMemorySourceArtifact(
        source_artifact_id=source_artifact_id,
        source_domain="worldbuilding",
        campaign_id=record.campaign_id,
        session_id=None,
        uri=f"repo://{relpath}",
        content_sha256=content_sha256,
        artifact_kind="worldbuilding_markdown",
        document_class=record.document_class,
        authority_state=record.authority_state,
        visibility_state=record.visibility_state,
        world_id=record.campaign_id,
        workspace_document_id=record.document_id,
        workspace_document_revision=record.revision,
        lineage={
            "workspace_document_id": record.document_id,
            "workspace_document_revision": record.revision,
            "source_span_index_uri": f"repo://{source_span_index_relpath(source_artifact_id)}",
        },
        created_at=now,
        updated_at=now,
    )

    path = source_artifacts_path(root)
    with registry_mutation_lock(path):
        document, token = _load_unlocked(root)
        existing = next(
            (row for row in document.records if row.source_artifact_id == source_artifact_id),
            None,
        )
        if existing is not None:
            if not _records_match(existing, candidate):
                raise SourceArtifactRegistryError(
                    "source artifact id collision with mismatched digest or foreign keys",
                    status_code=409,
                )
            try:
                load_source_span_index(root, existing.source_artifact_id)
            except SourceArtifactRegistryError:
                index = build_source_span_index_for_text(
                    source_artifact_id=existing.source_artifact_id,
                    content_sha256=existing.content_sha256 or content_sha256,
                    text=content,
                )
                _persist_span_index(root, index)
            return existing

        index = build_source_span_index_for_text(
            source_artifact_id=source_artifact_id,
            content_sha256=content_sha256,
            text=content,
        )
        _persist_span_index(root, index)

        document.records.append(candidate)
        _save_cas(root, document, expected_token=token)
        return candidate
