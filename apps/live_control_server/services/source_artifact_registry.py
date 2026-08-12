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
    load_workspace_document_under_registry_lock,
)
from graph_memory.evidence.source_artifact import (
    GraphMemorySourceArtifact,
    build_recap_source_artifact_id,
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
    workspace_document_mutation_lock,
)
from src.live_play.live_store import load_json, write_json

DEFAULT_SOURCE_ARTIFACT_REGISTRY_REL = "out/registries/source_artifacts.json"
DEFAULT_SOURCE_SPAN_INDEX_DIR_REL = "out/registries/source_span_indexes"
SOURCE_ARTIFACT_REGISTRY_SCHEMA = "dmb_source_artifact_registry_v1"

_SAFE_ARTIFACT_DIR_RE = re.compile(r"[^A-Za-z0-9._-]+")
# Single path segment: no slashes, no ``..``, no empty / absolute segments.
_SAFE_PATH_SEGMENT_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


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


def _require_safe_path_segment(value: str, *, field_name: str) -> str:
    cleaned = (value or "").strip()
    if not cleaned or not _SAFE_PATH_SEGMENT_RE.fullmatch(cleaned):
        raise SourceArtifactRegistryError(
            f"{field_name} must be a single safe path segment",
            status_code=422,
        )
    if cleaned in {".", ".."} or "/" in cleaned or "\\" in cleaned:
        raise SourceArtifactRegistryError(
            f"{field_name} must be a single safe path segment",
            status_code=422,
        )
    return cleaned


def _resolve_registry_content_path(root: Path, relpath: str) -> Path:
    """Resolve ``root / relpath`` and reject escapes outside ``root``."""
    resolved_root = root.resolve()
    target = (resolved_root / relpath).resolve()
    if not target.is_relative_to(resolved_root):
        raise SourceArtifactRegistryError(
            "recap content path escapes repository root",
            status_code=422,
        )
    return target


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

    The per-document mutation lock is held across load/verify/read/persist so a concurrent
    Markdown commit cannot interleave target bytes with a prior workspace revision.
    """
    with workspace_document_mutation_lock(root, document_id):
        return _create_source_artifact_from_workspace_document_unlocked(
            root,
            document_id=document_id,
            expected_revision=expected_revision,
            expected_content_sha256=expected_content_sha256,
        )


def _create_source_artifact_from_workspace_document_unlocked(
    root: Path,
    *,
    document_id: str,
    expected_revision: int | None = None,
    expected_content_sha256: str | None = None,
) -> GraphMemorySourceArtifact:
    try:
        record = load_workspace_document_under_registry_lock(root, document_id)
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
    # Legacy worldbuilding records without world_id use campaign_id as world identity.
    artifact_world_id = record.world_id if record.world_id else record.campaign_id
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
        world_id=artifact_world_id,
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


def _resolve_repo_contained_path(root: Path, path: Path) -> tuple[Path, str]:
    root_resolved = root.resolve()
    resolved = path.expanduser().resolve()
    try:
        relpath = resolved.relative_to(root_resolved).as_posix()
    except ValueError as exc:
        raise SourceArtifactRegistryError(
            "source path must be contained within the repository root",
            status_code=422,
        ) from exc
    if ".." in Path(relpath).parts:
        raise SourceArtifactRegistryError(
            "source path must be contained within the repository root",
            status_code=422,
        )
    return resolved, relpath


def _normalize_source_text(text: str) -> str:
    if not text.strip():
        raise SourceArtifactRegistryError("source text is empty", status_code=422)
    return text.rstrip("\n") + "\n"


def _upsert_source_artifact(
    root: Path,
    *,
    candidate: GraphMemorySourceArtifact,
    content: str,
) -> GraphMemorySourceArtifact:
    path = source_artifacts_path(root)
    with registry_mutation_lock(path):
        document, token = _load_unlocked(root)
        existing = next(
            (
                row
                for row in document.records
                if row.source_artifact_id == candidate.source_artifact_id
            ),
            None,
        )
        if existing is not None:
            same_bytes = (existing.content_sha256 or "") == (candidate.content_sha256 or "")
            same_scope = (
                existing.source_domain == candidate.source_domain
                and existing.campaign_id == candidate.campaign_id
                and existing.session_id == candidate.session_id
                and existing.artifact_kind == candidate.artifact_kind
                and existing.document_class == candidate.document_class
                and existing.workspace_document_id == candidate.workspace_document_id
                and existing.workspace_document_revision
                == candidate.workspace_document_revision
            )
            if same_bytes and same_scope:
                # Idempotent re-admission of the same bytes. Keep the existing URI
                # so previously reviewable runs remain bound to immutable content.
                try:
                    load_source_span_index(root, existing.source_artifact_id)
                except SourceArtifactRegistryError:
                    index = build_source_span_index_for_text(
                        source_artifact_id=existing.source_artifact_id,
                        content_sha256=existing.content_sha256 or candidate.content_sha256 or "",
                        text=content,
                    )
                    _persist_span_index(root, index)
                return existing
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
                    content_sha256=existing.content_sha256 or candidate.content_sha256 or "",
                    text=content,
                )
                _persist_span_index(root, index)
            return existing

        index = build_source_span_index_for_text(
            source_artifact_id=candidate.source_artifact_id,
            content_sha256=candidate.content_sha256 or "",
            text=content,
        )
        _persist_span_index(root, index)
        document.records.append(candidate)
        _save_cas(root, document, expected_token=token)
        return candidate


def create_recap_source_artifact(
    root: Path,
    *,
    campaign_id: str,
    session_id: str,
    recap_path: Path | None = None,
    recap_text: str | None = None,
    expected_content_sha256: str | None = None,
) -> GraphMemorySourceArtifact:
    """Create an immutable recap SourceArtifact from committed recap bytes.

    Bytes are always materialized under a registry-owned, repo-contained URI
    keyed by the full content digest
    (``out/registries/source_content/recap/<campaign>/<session>/<sha256>.md``).
    The caller's original recap path is read-only input and is never rewritten.
    """
    cleaned_campaign = _require_safe_path_segment(
        campaign_id or "", field_name="campaign_id"
    )
    cleaned_session = _require_safe_path_segment(
        session_id or "", field_name="session_id"
    )
    if recap_path is None and recap_text is None:
        raise SourceArtifactRegistryError(
            "recap_path or recap_text is required",
            status_code=422,
        )

    if recap_path is not None:
        resolved = recap_path.expanduser().resolve()
        if not resolved.is_file():
            raise SourceArtifactRegistryError(
                "recap source file is missing",
                status_code=409,
            )
        try:
            raw = resolved.read_text(encoding="utf-8")
        except OSError as exc:
            raise SourceArtifactRegistryError(
                f"failed to read recap source file: {exc}",
                status_code=500,
            ) from exc
        content = _normalize_source_text(raw)
    else:
        content = _normalize_source_text(recap_text or "")

    content_sha256 = hashlib.sha256(content.encode("utf-8")).hexdigest()
    if expected_content_sha256 is not None:
        expected = expected_content_sha256.removeprefix("sha256:").strip().lower()
        if expected != content_sha256:
            raise SourceArtifactRegistryError(
                "expected_content_sha256 does not match recap source bytes",
                status_code=409,
            )

    # Always materialize into a registry-owned, digest-namespaced path. Never
    # retain or rewrite the caller's original recap path — that source must stay
    # immutable from the registry's perspective.
    relpath = (
        "out/registries/source_content/recap/"
        f"{cleaned_campaign}/{cleaned_session}/{content_sha256}.md"
    )
    target = _resolve_registry_content_path(root, relpath)
    target.parent.mkdir(parents=True, exist_ok=True)
    if not target.is_file():
        target.write_text(content, encoding="utf-8")
    else:
        existing = target.read_text(encoding="utf-8")
        if existing != content:
            raise SourceArtifactRegistryError(
                "registry-owned recap content path already exists with different bytes",
                status_code=409,
            )

    source_artifact_id = build_recap_source_artifact_id(
        campaign_id=cleaned_campaign,
        session_id=cleaned_session,
        content_sha256=content_sha256,
    )
    now = _utc_now_iso()
    candidate = GraphMemorySourceArtifact(
        source_artifact_id=source_artifact_id,
        source_domain="recap",
        campaign_id=cleaned_campaign,
        session_id=cleaned_session,
        uri=f"repo://{relpath}",
        content_sha256=content_sha256,
        artifact_kind="recap_markdown",
        document_class="recap",
        visibility_state="internal",
        lineage={
            "source_span_index_uri": f"repo://{source_span_index_relpath(source_artifact_id)}",
        },
        created_at=now,
        updated_at=now,
    )
    return _upsert_source_artifact(root, candidate=candidate, content=content)


def load_registered_source_artifact_text(
    root: Path,
    source_artifact_id: str,
) -> tuple[GraphMemorySourceArtifact, str]:
    """Load a registered SourceArtifact and its committed text bytes."""
    artifact = get_source_artifact(root, source_artifact_id)
    if not artifact.uri.startswith("repo://"):
        raise SourceArtifactRegistryError(
            "artifact uri must be repo-relative",
            status_code=500,
        )
    relpath = artifact.uri.removeprefix("repo://")
    target = root / relpath
    if not target.is_file():
        raise SourceArtifactRegistryError(
            "registered source artifact file is missing",
            status_code=409,
        )
    try:
        content = _normalize_source_text(target.read_text(encoding="utf-8"))
    except OSError as exc:
        raise SourceArtifactRegistryError(
            f"failed to read registered source artifact: {exc}",
            status_code=500,
        ) from exc
    digest = hashlib.sha256(content.encode("utf-8")).hexdigest()
    if digest != (artifact.content_sha256 or ""):
        raise SourceArtifactRegistryError(
            "registered source artifact digest mismatch",
            status_code=409,
        )
    return artifact, content
