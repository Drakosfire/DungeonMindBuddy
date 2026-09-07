"""SQL repository for the immutable source-content authority.

Repositories do not open or commit transactions. The service layer owns those
boundaries and the invariant checks around idempotent adoption.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from application_state.source.types import SourceMarkdownRecord


def _now() -> datetime:
    return datetime.now(UTC)


def _record_from_row(row: dict) -> SourceMarkdownRecord:
    return SourceMarkdownRecord.model_validate(row)


def get_source_artifact(
    conn: psycopg.Connection,
    source_artifact_id: str,
) -> dict | None:
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            """
            SELECT source_artifact_id, source_domain, campaign_id, session_id, world_id
            FROM source.artifact
            WHERE source_artifact_id = %s
            """,
            (source_artifact_id,),
        )
        row = cur.fetchone()
    return None if row is None else dict(row)


def get_source_markdown(
    conn: psycopg.Connection,
    *,
    source_artifact_id: str,
    content_sha256: str,
    source_revision_id: UUID | None = None,
) -> SourceMarkdownRecord | None:
    clauses = [
        "r.source_artifact_id = %s",
        "r.content_sha256 = %s",
    ]
    params: list[object] = [source_artifact_id, content_sha256]
    if source_revision_id is not None:
        clauses.append("r.source_revision_id = %s")
        params.append(source_revision_id)
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            f"""
            SELECT
                r.source_revision_id,
                r.source_artifact_id,
                a.source_domain,
                a.campaign_id,
                a.session_id,
                a.world_id,
                r.content_sha256,
                r.media_type,
                r.encoding,
                r.markdown,
                r.lineage,
                r.created_at
            FROM source.revision AS r
            JOIN source.artifact AS a
              ON a.source_artifact_id = r.source_artifact_id
            WHERE {" AND ".join(clauses)}
            """,
            params,
        )
        row = cur.fetchone()
    return None if row is None else _record_from_row(row)


def insert_source_markdown(
    conn: psycopg.Connection,
    *,
    source_artifact_id: str,
    source_domain: str,
    campaign_id: str | None,
    session_id: str | None,
    world_id: str | None,
    content_sha256: str,
    media_type: str,
    encoding: str,
    markdown: str,
    lineage: dict[str, object],
    source_revision_id: UUID | None = None,
) -> SourceMarkdownRecord:
    revision_id = source_revision_id or uuid4()
    now = _now()
    conn.execute(
        """
        INSERT INTO source.artifact (
            source_artifact_id, source_domain, campaign_id, session_id,
            world_id, created_at, updated_at
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (source_artifact_id) DO NOTHING
        """,
        (
            source_artifact_id,
            source_domain,
            campaign_id,
            session_id,
            world_id,
            now,
            now,
        ),
    )
    conn.execute(
        """
        UPDATE source.artifact
        SET world_id = %s, updated_at = %s
        WHERE source_artifact_id = %s
          AND world_id IS NULL
        """,
        (world_id, now, source_artifact_id),
    )
    conn.execute(
        """
        INSERT INTO source.revision (
            source_revision_id, source_artifact_id, content_sha256,
            media_type, encoding, markdown, lineage, created_at
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (source_artifact_id, content_sha256) DO NOTHING
        """,
        (
            revision_id,
            source_artifact_id,
            content_sha256,
            media_type,
            encoding,
            markdown,
            Jsonb(lineage),
            now,
        ),
    )
    loaded = get_source_markdown(
        conn,
        source_artifact_id=source_artifact_id,
        content_sha256=content_sha256,
    )
    if loaded is None:
        raise RuntimeError("source revision insert did not persist")
    return loaded
