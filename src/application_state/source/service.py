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
from application_state.source.types import SourceMarkdownRecord
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
) -> SourceMarkdownRecord:
    """Persist exact source bytes once and return the immutable revision.

    The digest is computed from the UTF-8 text supplied by the caller. A
    caller-provided digest is an assertion, never a replacement for hashing.
    Repeating the same artifact/digest is idempotent; different bytes can only
    create a different digest-keyed revision.

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
        artifact = repository.get_source_artifact(conn, artifact_id)
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
                return existing
            if existing.world_id is None and world_id is not None:
                return repository.insert_source_markdown(
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
                    source_revision_id=existing.source_revision_id,
                )
            return existing

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
        return loaded


def get_source_markdown(
    *,
    source_artifact_id: str,
    content_sha256: str,
    source_revision_id: UUID | None = None,
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
        )
