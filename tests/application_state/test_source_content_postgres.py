from __future__ import annotations

import hashlib
from uuid import UUID

import psycopg
import pytest

from application_state.errors import ApplicationStateConflictError
from application_state.source.service import (
    get_source_markdown,
    persist_source_markdown,
)


def test_source_markdown_is_immutable_and_idempotent(
    application_state_dsn: str,
) -> None:
    markdown = "# Session 25\n\nA durable paragraph.\n"
    digest = hashlib.sha256(markdown.encode("utf-8")).hexdigest()

    first = persist_source_markdown(
        source_artifact_id="artifact:recap:longmont-c2:session-25:abc123",
        source_domain="recap",
        campaign_id="longmont-c2",
        session_id="session-25",
        world_id="eldyrwild",
        markdown=markdown,
        content_sha256=f"sha256:{digest}",
        lineage={"adopted_from_run_id": "run-25"},
    )
    second = persist_source_markdown(
        source_artifact_id=first.source_artifact_id,
        source_domain="recap",
        campaign_id="longmont-c2",
        session_id="session-25",
        world_id="eldyrwild",
        markdown=markdown,
        content_sha256=digest,
        lineage={"adopted_from_run_id": "run-25"},
    )

    assert first.source_revision_id == second.source_revision_id
    assert second.markdown == markdown
    assert second.content_sha256 == digest
    assert get_source_markdown(
        source_artifact_id=first.source_artifact_id,
        content_sha256=digest,
    ) == second

    with psycopg.connect(application_state_dsn) as conn:
        revision_count = conn.execute("SELECT count(*) FROM source.revision").fetchone()
    assert revision_count == (1,)

    with pytest.raises(ApplicationStateConflictError, match="does not match"):
        persist_source_markdown(
            source_artifact_id=first.source_artifact_id,
            source_domain="recap",
            campaign_id="longmont-c2",
            session_id="session-25",
            world_id="eldyrwild",
            markdown="# Different\n",
            content_sha256=digest,
        )


def test_source_lookup_is_exact_artifact_and_digest(
    application_state_dsn: str,
) -> None:
    markdown = "Exact bytes.\n"
    record = persist_source_markdown(
        source_artifact_id="artifact:recap:longmont-c1:session-10:abc123",
        source_domain="recap",
        campaign_id="longmont-c1",
        session_id="session-10",
        world_id="eldyrwild",
        markdown=markdown,
    )

    assert get_source_markdown(
        source_artifact_id=record.source_artifact_id,
        content_sha256=record.content_sha256,
        source_revision_id=UUID(str(record.source_revision_id)),
    ) == record
    assert get_source_markdown(
        source_artifact_id=record.source_artifact_id,
        content_sha256="0" * 64,
    ) is None
