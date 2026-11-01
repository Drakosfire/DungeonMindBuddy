"""Service boundary for durable, immutable source Markdown."""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from uuid import UUID, uuid4

import psycopg

from application_state.cli import assert_at_head
from application_state.config import load_runtime_dsn
from application_state.errors import (
    ApplicationStateConflictError,
    ApplicationStateValidationError,
)
from application_state.source import repository
from application_state.source.types import SourceMarkdownRecord, SourceRevisionMetadata
from application_state.unit_of_work import unit_of_work


def _normalize_digest(value: str) -> str:
    return value.removeprefix("sha256:").strip().lower()


def _require_text(markdown: str) -> str:
    if not isinstance(markdown, str) or not markdown:
        raise ApplicationStateValidationError("source Markdown must be non-empty text")
    return markdown


def _scope_conflict(
    *,
    source_domain: str,
    campaign_id: str | None,
    session_id: str | None,
    world_id: str | None,
    expected_domain: str,
    expected_campaign_id: str | None,
    expected_session_id: str | None,
    expected_world_id: str | None,
) -> None:
    if (
        source_domain != expected_domain
        or campaign_id != expected_campaign_id
        or session_id != expected_session_id
    ):
        raise ApplicationStateConflictError(
            "source artifact identity does not match the persisted source"
        )
    if (
        world_id is not None
        and expected_world_id is not None
        and world_id != expected_world_id
    ):
        raise ApplicationStateConflictError(
            "source artifact is already bound to a different World"
        )


def persist_source_markdown(
    *,
    source_artifact_id: str,
    source_domain: str,
    campaign_id: str | None,
    session_id: str | None,
    world_id: str | None,
    markdown: str,
    content_sha256: str | None = None,
    media_type: str = "text/markdown",
    encoding: str = "utf-8",
    lineage: dict[str, object] | None = None,
    source_revision_id: UUID | None = None,
    dry_run: bool = False,
    input_descriptor: dict[str, object] | None = None,
) -> SourceMarkdownRecord:
    """Persist exact source bytes once and return the immutable revision.

    The digest is computed from the UTF-8 text supplied by the caller. A
    caller-provided digest is an assertion, never a replacement for hashing.
    An optional immutable producer input descriptor is committed in the same
    transaction as the body. It conveys no DungeonMind admission authority.
    Repeating the same artifact/digest is idempotent; different bytes can only
    create a different digest-keyed revision. Explicit null-to-World membership
    assignment updates the artifact and any stored descriptor together, across
    all its revisions; immutable bodies and their provenance are unchanged.

    A caller-supplied ``source_revision_id`` is an exact identity assertion,
    not an insert hint. ``dry_run=True`` evaluates the same conflicts and
    performs no INSERT/UPDATE.
    """

    artifact_id = source_artifact_id.strip()
    domain = source_domain.strip()
    if not artifact_id:
        raise ApplicationStateValidationError("source_artifact_id is required")
    if not domain:
        raise ApplicationStateValidationError("source_domain is required")
    exact_markdown = _require_text(markdown)
    actual_digest = hashlib.sha256(exact_markdown.encode("utf-8")).hexdigest()
    if content_sha256 is not None and _normalize_digest(content_sha256) != actual_digest:
        raise ApplicationStateConflictError(
            "source Markdown does not match the recorded content digest"
        )
    requested_lineage = dict(lineage or {})

    dsn = load_runtime_dsn()
    assert_at_head(dsn=dsn)
    with unit_of_work(dsn) as conn:
        record = _persist_source_markdown(
            conn, artifact_id=artifact_id, domain=domain, campaign_id=campaign_id,
            session_id=session_id, world_id=world_id, exact_markdown=exact_markdown,
            actual_digest=actual_digest, media_type=media_type, encoding=encoding,
            requested_lineage=requested_lineage, source_revision_id=source_revision_id,
            dry_run=dry_run,
        )
        _store_input_descriptor(conn, record, input_descriptor, dry_run=dry_run)
        return record


def _persist_source_markdown(
    conn: psycopg.Connection, *, artifact_id: str, domain: str,
    campaign_id: str | None, session_id: str | None, world_id: str | None,
    exact_markdown: str, actual_digest: str, media_type: str, encoding: str,
    requested_lineage: dict[str, object], source_revision_id: UUID | None,
    dry_run: bool,
) -> SourceMarkdownRecord:
    artifact = repository.get_source_artifact(conn, artifact_id, lock=None if dry_run else "update")
    if artifact is not None:
        _scope_conflict(
            source_domain=artifact["source_domain"],
            campaign_id=artifact["campaign_id"],
            session_id=artifact["session_id"],
            world_id=artifact["world_id"],
            expected_domain=domain,
            expected_campaign_id=campaign_id,
            expected_session_id=session_id,
            expected_world_id=world_id,
        )
    existing = repository.get_source_markdown(
        conn,
        source_artifact_id=artifact_id,
        content_sha256=actual_digest,
    )
    by_revision = (
        repository.get_source_markdown_by_revision_id(conn, source_revision_id)
        if source_revision_id is not None
        else None
    )
    if source_revision_id is not None and by_revision is not None:
        if (
            by_revision.source_artifact_id != artifact_id
            or by_revision.content_sha256 != actual_digest
            or by_revision.markdown != exact_markdown
        ):
            raise ApplicationStateConflictError(
                "requested source revision already belongs to different source state"
            )
        _scope_conflict(
            source_domain=by_revision.source_domain,
            campaign_id=by_revision.campaign_id,
            session_id=by_revision.session_id,
            world_id=by_revision.world_id,
            expected_domain=domain,
            expected_campaign_id=campaign_id,
            expected_session_id=session_id,
            expected_world_id=world_id,
        )
    if existing is not None:
        if existing.markdown != exact_markdown:
            raise ApplicationStateConflictError(
                "source artifact digest is already bound to different Markdown"
            )
        _scope_conflict(
            source_domain=existing.source_domain,
            campaign_id=existing.campaign_id,
            session_id=existing.session_id,
            world_id=existing.world_id,
            expected_domain=domain,
            expected_campaign_id=campaign_id,
            expected_session_id=session_id,
            expected_world_id=world_id,
        )
        if (
            source_revision_id is not None
            and existing.source_revision_id != source_revision_id
        ):
            raise ApplicationStateConflictError(
                "source artifact/digest already exists under a different source revision"
            )
        if dry_run:
            return existing.model_copy(update={"world_id": world_id}) if existing.world_id is None and world_id is not None else existing
        if existing.world_id is not None or world_id is None:
            return existing
        source_revision_id = existing.source_revision_id

    if dry_run:
        return SourceMarkdownRecord(
            source_revision_id=source_revision_id or uuid4(),
            source_artifact_id=artifact_id,
            source_domain=domain,
            campaign_id=campaign_id,
            session_id=session_id,
            world_id=world_id,
            content_sha256=actual_digest,
            media_type=media_type,
            encoding=encoding,
            markdown=exact_markdown,
            lineage=requested_lineage,
            created_at=datetime.now(UTC),
        )

    try:
        loaded = repository.insert_source_markdown(
            conn,
            source_artifact_id=artifact_id,
            source_domain=domain,
            campaign_id=campaign_id,
            session_id=session_id,
            world_id=world_id,
            content_sha256=actual_digest,
            media_type=media_type,
            encoding=encoding,
            markdown=exact_markdown,
            lineage=requested_lineage,
            source_revision_id=source_revision_id,
        )
    except psycopg.errors.UniqueViolation as exc:
        raise ApplicationStateConflictError(
            "requested source revision already belongs to different source state"
        ) from exc
    if (
        source_revision_id is not None
        and loaded.source_revision_id != source_revision_id
    ):
        raise ApplicationStateConflictError(
            "source artifact/digest already exists under a different source revision"
        )
    # A concurrent first registration can win the insert. Its scope must still
    # agree with this caller; an existing artifact was already locked above.
    _scope_conflict(
        source_domain=loaded.source_domain, campaign_id=loaded.campaign_id,
        session_id=loaded.session_id, world_id=loaded.world_id,
        expected_domain=domain, expected_campaign_id=campaign_id,
        expected_session_id=session_id, expected_world_id=world_id,
    )
    return loaded


def get_source_markdown(
    *,
    source_artifact_id: str,
    content_sha256: str,
    source_revision_id: UUID | None = None,
    world_id: str | None = None,
) -> SourceMarkdownRecord | None:
    """Load one exact artifact/digest binding from APP-STATE."""

    artifact_id = source_artifact_id.strip()
    digest = _normalize_digest(content_sha256)
    if not artifact_id or not digest:
        raise ApplicationStateValidationError(
            "source_artifact_id and content_sha256 are required"
        )
    dsn = load_runtime_dsn()
    assert_at_head(dsn=dsn)
    with unit_of_work(dsn) as conn:
        return repository.get_source_markdown(
            conn,
            source_artifact_id=artifact_id,
            content_sha256=digest,
            source_revision_id=source_revision_id,
            world_id=world_id,
        )


def get_source_markdown_batch(
    *,
    bindings: list[tuple[str, str]],
) -> dict[tuple[str, str], SourceMarkdownRecord]:
    """Load many exact artifact/digest bindings in one APP-STATE transaction.

    Duplicate bindings are collapsed. Missing rows are omitted from the
    result map so callers can report ``source_not_durable`` without a second
    round trip.
    """
    unique: list[tuple[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for artifact_id, content_sha256 in bindings:
        key = (artifact_id.strip(), _normalize_digest(content_sha256))
        if not key[0] or not key[1] or key in seen:
            continue
        seen.add(key)
        unique.append(key)
    if not unique:
        return {}
    dsn = load_runtime_dsn()
    assert_at_head(dsn=dsn)
    with unit_of_work(dsn) as conn:
        rows = repository.get_source_markdown_batch(conn, bindings=unique)
    return {(row.source_artifact_id, row.content_sha256): row for row in rows}


def get_source_revision_metadata(
    *,
    bindings: list[tuple[str, str]],
    world_id: str,
) -> list[SourceRevisionMetadata]:
    """Batch metadata from the immutable source owner; conveys no admission."""
    if not world_id or world_id != world_id.strip():
        raise ApplicationStateValidationError("source metadata requires an exact World")
    normalized = list(
        dict.fromkeys(
            (artifact, _normalize_digest(digest)) for artifact, digest in bindings
        )
    )
    if any(
        not artifact
        or artifact != artifact.strip()
        or len(digest) != 64
        or any(c not in "0123456789abcdef" for c in digest)
        for artifact, digest in normalized
    ):
        raise ApplicationStateValidationError(
            "source metadata requires exact artifact/digest bindings"
        )
    dsn = load_runtime_dsn()
    assert_at_head(dsn=dsn)
    with unit_of_work(dsn) as conn:
        conn.execute("SET TRANSACTION READ ONLY")
        return repository.get_source_revision_metadata(
            conn, bindings=normalized, world_id=world_id
        )


def owned_source_artifacts(*, source_artifact_ids: list[str], world_id: str) -> frozenset[str]:
    """Batch exact artifact ownership metadata without opening any source bodies.

    Missing and foreign ownership cannot qualify a native catalog offer. A match
    is only a precondition: the actual read still owns full provenance/body checks.
    """
    if not isinstance(world_id, str) or not world_id.strip():
        raise ApplicationStateValidationError("source ownership requires an exact World")
    if any(not isinstance(value, str) or not value.strip() for value in source_artifact_ids):
        raise ApplicationStateValidationError("source ownership requires exact artifact IDs")
    unique = list(dict.fromkeys(source_artifact_ids))
    if not unique:
        return frozenset()
    dsn = load_runtime_dsn()
    assert_at_head(dsn=dsn)
    with unit_of_work(dsn) as conn:
        conn.execute("SET TRANSACTION READ ONLY")
        return repository.owned_source_artifacts(conn, source_artifact_ids=unique, world_id=world_id)


def get_source_artifact_scope(*, source_artifact_id: str) -> dict | None:
    """Exact metadata-only ownership check before a citation opens source bytes."""
    if not isinstance(source_artifact_id, str) or not source_artifact_id.strip():
        raise ApplicationStateValidationError("source scope requires an exact artifact ID")
    dsn = load_runtime_dsn()
    assert_at_head(dsn=dsn)
    with unit_of_work(dsn) as conn:
        conn.execute("SET TRANSACTION READ ONLY")
        row = repository.get_source_artifact(conn, source_artifact_id)
    if row is None:
        return None
    return {key: row[key] for key in ("world_id", "source_domain", "campaign_id", "session_id")}


def _input_signature(descriptor: dict) -> dict:
    # Registration timestamps and historical presentation locator do not change
    # immutable input identity. The original values remain stored on exact replay.
    return {key: value for key, value in descriptor.items() if key not in {"created_at", "updated_at", "uri"}}


def _store_input_descriptor(
    conn: psycopg.Connection, record: SourceMarkdownRecord,
    raw_descriptor: dict[str, object] | None, *, dry_run: bool,
) -> None:
    from graph_memory.evidence.source_artifact import GraphMemorySourceArtifact
    existing = repository.get_input_descriptor(conn, record.source_artifact_id, for_update=not dry_run)
    if existing is None and raw_descriptor is None:
        return
    # World membership belongs to the artifact, across all its immutable bodies.
    # Preserve the original descriptor's registration/history fields on replay.
    projected = None if existing is None else dict(existing)
    if projected is not None and projected.get("world_id") is None:
        projected["world_id"] = record.world_id
    try:
        descriptor = GraphMemorySourceArtifact.model_validate(
            raw_descriptor if raw_descriptor is not None else projected
        ).model_dump(mode="json")
    except ValueError as exc:
        raise ApplicationStateValidationError(f"invalid source input descriptor: {exc}") from exc
    fields = ("source_artifact_id", "source_domain", "world_id", "campaign_id", "session_id")
    descriptor_digest = _normalize_digest(descriptor.get("content_sha256") or "")
    # An omitted descriptor keeps its original input revision, which need not be
    # the body revision being saved. Membership still changes for the artifact.
    digest_matches = descriptor_digest == record.content_sha256
    if raw_descriptor is None and not digest_matches:
        digest_matches = repository.get_source_markdown(
            conn, source_artifact_id=record.source_artifact_id,
            content_sha256=descriptor_digest,
        ) is not None
    if any(descriptor[field] != getattr(record, field) for field in fields) or not digest_matches:
        raise ApplicationStateConflictError("source input descriptor does not match its exact stored body binding")
    if projected is not None:
        if _input_signature(projected) != _input_signature(descriptor):
            raise ApplicationStateConflictError("source input descriptor is already registered with different immutable metadata")
        descriptor = projected
    if not dry_run and descriptor != existing:
        repository.set_input_descriptor(conn, record.source_artifact_id, descriptor)


def get_source_input_descriptors(*, source_artifact_ids: list[str]) -> dict[str, dict]:
    """Read exact registered producer metadata, never latest bodies or provenance authority."""
    from graph_memory.evidence.source_artifact import GraphMemorySourceArtifact
    from application_state.errors import ApplicationStateIntegrityError
    if any(not isinstance(value, str) or not value.strip() for value in source_artifact_ids):
        raise ApplicationStateValidationError("source input lookup requires exact artifact IDs")
    ids = list(dict.fromkeys(source_artifact_ids))
    if not ids:
        return {}
    dsn = load_runtime_dsn()
    assert_at_head(dsn=dsn)
    with unit_of_work(dsn) as conn:
        conn.execute("SET TRANSACTION READ ONLY")
        rows = repository.get_input_descriptors(conn, ids)
    result = {}
    for row in rows:
        try:
            descriptor = GraphMemorySourceArtifact.model_validate(row["input_descriptor"])
            fields = ("source_artifact_id", "source_domain", "world_id", "campaign_id", "session_id")
            if any(getattr(descriptor, field) != row[field] for field in fields):
                raise ValueError("descriptor scope differs from its source input row")
            digest = _normalize_digest(descriptor.content_sha256 or "")
            if len(digest) != 64 or any(char not in "0123456789abcdef" for char in digest):
                raise ValueError("descriptor lacks exact SHA-256 content digest")
        except ValueError as exc:
            raise ApplicationStateIntegrityError(f"invalid registered source input metadata: {exc}") from exc
        result[descriptor.source_artifact_id] = descriptor.model_dump(mode="json")
    return result
