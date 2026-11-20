"""Bind explicitly selected source excerpts to exact committed page revisions.

The caller must authenticate the owner and retain the returned text only inside
the staged, owner-reviewed release. The text is data: clients must render it as
plain text and must not interpret Markdown, HTML, URLs, or embedded media.
"""
from __future__ import annotations

import hashlib
import re
from uuid import uuid4

from application_state.content import pages, repository
from application_state.unit_of_work import unit_of_work

_DOMAIN = re.compile(r"(?i)(?:[a-z0-9-]+\.)+[a-z]{2,}(?:\b|$)")


class GuestReleaseSourceError(ValueError):
    """A requested source excerpt is not safe to prepare."""


def contains_unsupported_destination(text: str) -> bool:
    """Fail closed on paths and destination syntax until local rewriting exists."""
    return any(char in text for char in "[]<>/\\@:") or bool(_DOMAIN.search(text))


def selected_page_excerpt(*, world_id: str, document_id: str, revision_n: int,
                          expected_sha256: str, start: int, end: int,
                          expected_excerpt: str) -> tuple[dict, tuple]:
    """Copy an owner-selected exact span from a currently player-safe page."""
    if (type(start) is not int or type(end) is not int or start < 0 or end <= start
        or end - start > 20_000 or not isinstance(expected_excerpt, str)):
        raise GuestReleaseSourceError("Invalid source selection")
    # Snapshot eligibility and the requested immutable revision together. This
    # does not yet implement withdrawal invalidation for staged candidates.
    with unit_of_work(pages._dsn()) as conn:
        conn.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
        state = pages._state(conn, document_id, world_id)
        if state.page.status != "active" or state.metadata.visibility_state != "player_safe":
            raise GuestReleaseSourceError("Source is not player-safe")
        revision = repository.get_work_revision_by_n(conn, state.page.work_object_id, revision_n)
        if revision is None or revision.work_object_id != state.page.work_object_id or revision.world_id != world_id:
            raise GuestReleaseSourceError("Source revision unavailable")
        if state.page.current_revision_id != revision.work_revision_id:
            raise GuestReleaseSourceError("Historical page origin cannot be established")
        generation = conn.execute(
            "SELECT m.guest_visibility_generation, COALESCE(g.generation,0) "
            "FROM content.page_metadata m LEFT JOIN workspace.guest_source_status_generation g "
            "ON g.work_object_id=m.work_object_id WHERE m.work_object_id=%s",
            (state.page.work_object_id,),
        ).fetchone()
        if generation is None:
            raise GuestReleaseSourceError("Source status unavailable")
    actual_digest = hashlib.sha256(revision.markdown.encode("utf-8")).hexdigest()
    if actual_digest != expected_sha256 or revision.markdown[start:end] != expected_excerpt:
        raise GuestReleaseSourceError("Source selection changed")
    if end > len(revision.markdown) or not expected_excerpt.strip():
        raise GuestReleaseSourceError("Source selection is empty or incomplete")
    # Until a release-local link rewrite exists, reject rather than publish
    # opaque Markdown destinations, paths, addresses, HTML or bare hostnames.
    if contains_unsupported_destination(expected_excerpt):
        raise GuestReleaseSourceError("Source selection contains a link or path")
    # This is an explicitly selected excerpt, not its private document identity,
    # source locator, World, source digest, or original revision identifier.
    excerpt_id = uuid4()
    return ({"id": str(excerpt_id), "text": expected_excerpt},
            (excerpt_id, state.page.work_object_id, generation[0], generation[1],
             revision_n, expected_sha256, start, end, state.page.object_revision))
