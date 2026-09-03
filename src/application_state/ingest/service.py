"""Ingest lifecycle over APP-STATE PostgreSQL. One mutation = one unit of work."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, NoReturn

import psycopg
from psycopg.errors import ForeignKeyViolation, UniqueViolation

from application_state.cli import assert_at_head
from application_state.config import load_runtime_dsn
from application_state.errors import (
    ApplicationStateConflictError,
    ApplicationStateIntegrityError,
    ApplicationStateNotFoundError,
    ApplicationStateUnavailableError,
    ApplicationStateValidationError,
)
from application_state.ingest import repository as repo
from application_state.unit_of_work import unit_of_work
from graph_memory.ingestion.extraction_run import (
    FROZEN_COMPONENT_STATUSES,
    TERMINAL_EXTRACTION_RUN_STATUSES,
    ExtractionRun,
    ExtractionRunDiagnostics,
    ExtractionRunStatus,
    assert_allowed_extraction_run_transition,
    validate_extraction_run_lineage,
)


@dataclass(frozen=True)
class IngestAuthoritySnapshot:
    run_count: int


def _require_run_id(run_id: str) -> str:
    cleaned = run_id.strip()
    if not cleaned:
        raise ApplicationStateValidationError("run_id is required")
    return cleaned


def _iso_now() -> str:
    return repo.iso_z(repo.now_utc()) or ""


def _connected_lineage(conn: psycopg.Connection, run: ExtractionRun) -> list[ExtractionRun]:
    connected_ids: set[str] = {run.run_id}
    changed = True
    records: dict[str, ExtractionRun] = {run.run_id: run}
    while changed:
        changed = False
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT run_id FROM ingest.run
                WHERE run_id = ANY(%s)
                   OR supersedes_run_id = ANY(%s)
                   OR superseded_by_run_id = ANY(%s)
                """,
                (list(connected_ids), list(connected_ids), list(connected_ids)),
            )
            found = {str(row[0]) for row in cur.fetchall()}
        missing = found - connected_ids
        if missing:
            for loaded in repo.get_runs_by_ids(conn, missing):
                records[loaded.run_id] = loaded
            connected_ids |= found
            changed = True
        for current in list(records.values()):
            for linked_id in (current.supersedes_run_id, current.superseded_by_run_id):
                if linked_id and linked_id not in connected_ids:
                    loaded = repo.get_run(conn, linked_id)
                    if loaded is None:
                        raise ApplicationStateIntegrityError(
                            f"ingest.run lineage pointer missing: {linked_id}"
                        )
                    records[loaded.run_id] = loaded
                    connected_ids.add(loaded.run_id)
                    changed = True
    return list(records.values())


def _validate_connected_lineage(conn: psycopg.Connection, run: ExtractionRun) -> None:
    try:
        validate_extraction_run_lineage(_connected_lineage(conn, run))
    except ValueError as exc:
        raise ApplicationStateIntegrityError(
            f"malformed extraction run lineage: {exc}"
        ) from exc


def _validate_catalog_lineage(conn: psycopg.Connection, records: list[ExtractionRun]) -> None:
    try:
        validate_extraction_run_lineage(records)
    except ValueError as exc:
        raise ApplicationStateIntegrityError(
            f"malformed extraction run lineage: {exc}"
        ) from exc


def _map_write_error(exc: BaseException, *, run_id: str) -> NoReturn:
    if isinstance(exc, UniqueViolation):
        raise ApplicationStateConflictError(
            f"extraction run already exists: {run_id}"
        ) from exc
    if isinstance(exc, ForeignKeyViolation):
        raise ApplicationStateIntegrityError(
            f"ingest.run lineage foreign key failed: {run_id}: {exc}"
        ) from exc
    raise exc


def inspect_ingest_authority() -> IngestAuthoritySnapshot:
    """Read-only catalog inspection for runtime preflight. No component-byte checks."""
    try:
        dsn = load_runtime_dsn()
    except ApplicationStateUnavailableError:
        raise
    assert_at_head(dsn=dsn)
    with unit_of_work(dsn) as conn:
        records = repo.list_runs(conn)
        _validate_catalog_lineage(conn, records)
        return IngestAuthoritySnapshot(run_count=len(records))


def get_extraction_run(run_id: str) -> ExtractionRun:
    canonical = _require_run_id(run_id)
    dsn = load_runtime_dsn()
    assert_at_head(dsn=dsn)
    with unit_of_work(dsn) as conn:
        run = repo.get_run(conn, canonical)
        if run is None:
            raise ApplicationStateNotFoundError(f"extraction run not found: {canonical}")
        _validate_connected_lineage(conn, run)
        return run


def get_extraction_run_optional(run_id: str) -> ExtractionRun | None:
    canonical = _require_run_id(run_id)
    dsn = load_runtime_dsn()
    assert_at_head(dsn=dsn)
    with unit_of_work(dsn) as conn:
        run = repo.get_run(conn, canonical)
        if run is None:
            return None
        _validate_connected_lineage(conn, run)
        return run


def list_extraction_runs(
    *,
    campaign_id: str | None = None,
    session_id: str | None = None,
    source_artifact_id: str | None = None,
) -> list[ExtractionRun]:
    dsn = load_runtime_dsn()
    assert_at_head(dsn=dsn)
    with unit_of_work(dsn) as conn:
        records = repo.list_runs(
            conn,
            campaign_id=campaign_id,
            session_id=session_id,
            source_artifact_id=source_artifact_id,
        )
        _validate_catalog_lineage(conn, records)
        return records


def create_extraction_run(run: ExtractionRun) -> ExtractionRun:
    dsn = load_runtime_dsn()
    assert_at_head(dsn=dsn)
    with unit_of_work(dsn) as conn:
        existing = repo.get_run(conn, run.run_id)
        if existing is not None:
            raise ApplicationStateConflictError(
                f"extraction run already exists: {run.run_id}"
            )
        try:
            inserted = repo.insert_run(conn, run)
        except (UniqueViolation, ForeignKeyViolation) as exc:
            _map_write_error(exc, run_id=run.run_id)
        _validate_connected_lineage(conn, inserted)
        return inserted


def update_extraction_run(
    run_id: str,
    *,
    status: ExtractionRunStatus,
    expected_revision: int,
    components: dict[str, Any] | None = None,
    diagnostics: ExtractionRunDiagnostics | None = None,
    lineage: dict[str, Any] | None = None,
) -> ExtractionRun:
    canonical = _require_run_id(run_id)
    if expected_revision < 1:
        raise ApplicationStateValidationError("expected_revision must be >= 1")
    dsn = load_runtime_dsn()
    assert_at_head(dsn=dsn)
    with unit_of_work(dsn) as conn:
        existing = repo.lock_run(conn, canonical)
        if existing is None:
            raise ApplicationStateNotFoundError(f"extraction run not found: {canonical}")
        if existing.revision != expected_revision:
            raise ApplicationStateConflictError(
                f"revision mismatch: expected {expected_revision}, current {existing.revision}"
            )
        if existing.status in TERMINAL_EXTRACTION_RUN_STATUSES:
            raise ApplicationStateConflictError(
                f"extraction run status {existing.status.value} is terminal"
            )
        try:
            assert_allowed_extraction_run_transition(existing.status, status)
        except ValueError as exc:
            raise ApplicationStateValidationError(str(exc)) from exc
        if components is not None and existing.status in FROZEN_COMPONENT_STATUSES:
            raise ApplicationStateConflictError(
                "cannot replace components for a frozen extraction run"
            )
        next_components = existing.components if components is None else components
        next_diagnostics = existing.diagnostics if diagnostics is None else diagnostics
        next_lineage = existing.lineage if lineage is None else dict(lineage)
        updated = existing.model_copy(
            update={
                "status": status,
                "revision": existing.revision + 1,
                "updated_at": _iso_now(),
                "components": next_components,
                "diagnostics": next_diagnostics,
                "lineage": next_lineage,
            }
        )
        persisted = repo.cas_update_run(
            conn, updated, expected_revision=expected_revision
        )
        if persisted is None:
            raise ApplicationStateConflictError(
                f"revision mismatch: expected {expected_revision}, current {existing.revision}"
            )
        _validate_connected_lineage(conn, persisted)
        return persisted


def supersede_extraction_run(
    run_id: str,
    *,
    expected_revision: int,
    successor: ExtractionRun,
) -> ExtractionRun:
    canonical = _require_run_id(run_id)
    if expected_revision < 1:
        raise ApplicationStateValidationError("expected_revision must be >= 1")
    if successor.supersedes_run_id != canonical:
        raise ApplicationStateValidationError(
            "successor.supersedes_run_id must equal the predecessor run_id"
        )
    dsn = load_runtime_dsn()
    assert_at_head(dsn=dsn)
    with unit_of_work(dsn) as conn:
        existing = repo.lock_run(conn, canonical)
        if existing is None:
            raise ApplicationStateNotFoundError(f"extraction run not found: {canonical}")
        if existing.revision != expected_revision:
            raise ApplicationStateConflictError(
                f"revision mismatch: expected {expected_revision}, current {existing.revision}"
            )
        if existing.status == ExtractionRunStatus.SUPERSEDED:
            raise ApplicationStateConflictError("extraction run is already superseded")
        now = successor.updated_at or _iso_now()
        predecessor = existing.model_copy(
            update={
                "status": ExtractionRunStatus.SUPERSEDED,
                "revision": existing.revision + 1,
                "updated_at": now,
                "superseded_by_run_id": successor.run_id,
            }
        )
        if predecessor.superseded_by_run_id != successor.run_id:
            raise ApplicationStateIntegrityError("supersession lineage is not reciprocal")
        if successor.supersedes_run_id != predecessor.run_id:
            raise ApplicationStateIntegrityError("supersession lineage is not reciprocal")
        try:
            inserted = repo.insert_run(conn, successor)
            persisted = repo.cas_update_run(
                conn, predecessor, expected_revision=expected_revision
            )
        except (UniqueViolation, ForeignKeyViolation) as exc:
            _map_write_error(exc, run_id=successor.run_id)
        if persisted is None:
            raise ApplicationStateConflictError(
                f"revision mismatch: expected {expected_revision}, current {existing.revision}"
            )
        _validate_connected_lineage(conn, inserted)
        return inserted
