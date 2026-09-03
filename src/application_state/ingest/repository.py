"""Ingest SQL for canonical ExtractionRun rows. Repositories do not commit."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import psycopg
from pydantic import ValidationError
from psycopg import sql as psql
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from application_state.errors import ApplicationStateIntegrityError
from graph_memory.ingestion.extraction_run import ExtractionRun

_RUN_COLUMNS = """
    run_id, schema_version, record_version, source_artifact_id, source_domain,
    status, revision, campaign_id, session_id, profile_id, components, diagnostics,
    lineage, superseded_by_run_id, supersedes_run_id, created_at, updated_at
"""


def now_utc() -> datetime:
    return datetime.now(UTC)


def iso_z(value: datetime | None) -> str | None:
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def dt_from_iso(value: str | None) -> datetime | None:
    if value is None or value == "":
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _run_from_row(row: dict[str, Any]) -> ExtractionRun:
    payload = {
        "schema_version": row["schema_version"],
        "version": row["record_version"],
        "run_id": row["run_id"],
        "source_artifact_id": row["source_artifact_id"],
        "source_domain": row["source_domain"],
        "status": row["status"],
        "revision": row["revision"],
        "campaign_id": row["campaign_id"],
        "session_id": row["session_id"],
        "profile_id": row["profile_id"],
        "created_at": iso_z(row["created_at"]),
        "updated_at": iso_z(row["updated_at"]),
        "components": row["components"] or {},
        "diagnostics": row["diagnostics"] or {},
        "lineage": row["lineage"] or {},
        "superseded_by_run_id": row["superseded_by_run_id"],
        "supersedes_run_id": row["supersedes_run_id"],
    }
    try:
        return ExtractionRun.model_validate(payload)
    except (ValidationError, ValueError, TypeError) as exc:
        run_id = row.get("run_id", "<unknown>")
        raise ApplicationStateIntegrityError(
            f"ingest.run row cannot be interpreted as ExtractionRun: {run_id}: {exc}"
        ) from exc


def _params(run: ExtractionRun) -> dict[str, Any]:
    return {
        "run_id": run.run_id,
        "schema_version": run.schema_version,
        "record_version": run.version,
        "source_artifact_id": run.source_artifact_id,
        "source_domain": run.source_domain,
        "status": run.status.value,
        "revision": run.revision,
        "campaign_id": run.campaign_id,
        "session_id": run.session_id,
        "profile_id": run.profile_id,
        "components": Jsonb(
            {key: value.model_dump(mode="json") for key, value in run.components.items()}
        ),
        "diagnostics": Jsonb(run.diagnostics.model_dump(mode="json")),
        "lineage": Jsonb(dict(run.lineage)),
        "superseded_by_run_id": run.superseded_by_run_id,
        "supersedes_run_id": run.supersedes_run_id,
        "created_at": dt_from_iso(run.created_at),
        "updated_at": dt_from_iso(run.updated_at),
    }


def insert_run(conn: psycopg.Connection, run: ExtractionRun) -> ExtractionRun:
    conn.execute(
        f"""
        INSERT INTO ingest.run ({_RUN_COLUMNS})
        VALUES (
            %(run_id)s, %(schema_version)s, %(record_version)s, %(source_artifact_id)s,
            %(source_domain)s, %(status)s, %(revision)s, %(campaign_id)s, %(session_id)s,
            %(profile_id)s, %(components)s, %(diagnostics)s, %(lineage)s,
            %(superseded_by_run_id)s, %(supersedes_run_id)s, %(created_at)s, %(updated_at)s
        )
        """,
        _params(run),
    )
    loaded = get_run(conn, run.run_id)
    if loaded is None:
        raise ApplicationStateIntegrityError("ingest.run insert did not persist")
    return loaded


def get_run(conn: psycopg.Connection, run_id: str) -> ExtractionRun | None:
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            f"SELECT {_RUN_COLUMNS} FROM ingest.run WHERE run_id = %s",
            (run_id,),
        )
        row = cur.fetchone()
    return None if row is None else _run_from_row(row)


def lock_run(conn: psycopg.Connection, run_id: str) -> ExtractionRun | None:
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            f"""
            SELECT {_RUN_COLUMNS}
            FROM ingest.run
            WHERE run_id = %s
            FOR UPDATE
            """,
            (run_id,),
        )
        row = cur.fetchone()
    return None if row is None else _run_from_row(row)


def list_runs(
    conn: psycopg.Connection,
    *,
    campaign_id: str | None = None,
    session_id: str | None = None,
    source_artifact_id: str | None = None,
    status: str | None = None,
) -> list[ExtractionRun]:
    filters: list[psql.SQL] = []
    params: list[object] = []
    if campaign_id is not None:
        filters.append(psql.SQL("campaign_id = %s"))
        params.append(campaign_id)
    if session_id is not None:
        filters.append(psql.SQL("session_id = %s"))
        params.append(session_id)
    if source_artifact_id is not None:
        filters.append(psql.SQL("source_artifact_id = %s"))
        params.append(source_artifact_id)
    if status is not None:
        filters.append(psql.SQL("status = %s"))
        params.append(status)
    where = (
        psql.SQL(" WHERE ") + psql.SQL(" AND ").join(filters) if filters else psql.SQL("")
    )
    query = (
        psql.SQL("SELECT ")
        + psql.SQL(
            """
            run_id, schema_version, record_version, source_artifact_id, source_domain,
            status, revision, campaign_id, session_id, profile_id, components, diagnostics,
            lineage, superseded_by_run_id, supersedes_run_id, created_at, updated_at
            """
        )
        + psql.SQL(" FROM ingest.run")
        + where
        + psql.SQL(" ORDER BY updated_at DESC NULLS LAST, run_id ASC")
    )
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(query, params)
        rows = cur.fetchall()
    return [_run_from_row(row) for row in rows]


def count_runs(conn: psycopg.Connection) -> int:
    row = conn.execute("SELECT count(*) FROM ingest.run").fetchone()
    if row is None:
        return 0
    return int(row[0])


def cas_update_run(
    conn: psycopg.Connection,
    run: ExtractionRun,
    *,
    expected_revision: int,
) -> ExtractionRun | None:
    params = _params(run)
    params["expected_revision"] = expected_revision
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            f"""
            UPDATE ingest.run
            SET schema_version = %(schema_version)s,
                record_version = %(record_version)s,
                source_artifact_id = %(source_artifact_id)s,
                source_domain = %(source_domain)s,
                status = %(status)s,
                revision = %(revision)s,
                campaign_id = %(campaign_id)s,
                session_id = %(session_id)s,
                profile_id = %(profile_id)s,
                components = %(components)s,
                diagnostics = %(diagnostics)s,
                lineage = %(lineage)s,
                superseded_by_run_id = %(superseded_by_run_id)s,
                supersedes_run_id = %(supersedes_run_id)s,
                created_at = %(created_at)s,
                updated_at = %(updated_at)s
            WHERE run_id = %(run_id)s
              AND revision = %(expected_revision)s
            RETURNING {_RUN_COLUMNS}
            """,
            params,
        )
        row = cur.fetchone()
    return None if row is None else _run_from_row(row)


def get_runs_by_ids(conn: psycopg.Connection, run_ids: set[str]) -> list[ExtractionRun]:
    if not run_ids:
        return []
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            f"""
            SELECT {_RUN_COLUMNS}
            FROM ingest.run
            WHERE run_id = ANY(%s)
            """,
            (list(run_ids),),
        )
        rows = cur.fetchall()
    return [_run_from_row(row) for row in rows]
