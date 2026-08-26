"""Explicit one-time adoption of active-run.json. Not ordinary selection authority."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

from application_state.cli import assert_at_head
from application_state.config import load_runtime_dsn
from application_state.errors import ApplicationStateConflictError, ApplicationStateIntegrityError
from application_state.play import repository as repo
from application_state.play.service import _iso_z, require_persisted_aggregate_integrity
from application_state.play.types import PlayActiveRunImportReport
from application_state.unit_of_work import unit_of_work

_NULL_POINTER = (None, None)


def _parse_selected_at(value: str) -> datetime:
    cleaned = value.strip()
    if cleaned.endswith("Z"):
        cleaned = cleaned[:-1] + "+00:00"
    parsed = datetime.fromisoformat(cleaned)
    return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=UTC)


def capture_legacy_active_run_pointer(root: Path) -> tuple[UUID, datetime] | tuple[None, None]:
    """Read the predecessor file under lock. Ordinary GET/PUT must not call this."""
    from apps.live_control_server.services.play_active_run import (
        PlayActiveRunError,
        load_legacy_play_active_run_file,
    )

    try:
        state = load_legacy_play_active_run_file(root)
    except PlayActiveRunError as exc:
        raise ApplicationStateIntegrityError(str(exc), status_code=exc.status_code) from exc
    if state.run_id is None or state.selected_at is None:
        return _NULL_POINTER
    return UUID(state.run_id), _parse_selected_at(state.selected_at)


def import_play_active_run_from_legacy_file(root: Path) -> PlayActiveRunImportReport:
    dsn = load_runtime_dsn()
    assert_at_head(dsn=dsn)
    captured = capture_legacy_active_run_pointer(root)
    report = PlayActiveRunImportReport()
    with unit_of_work(dsn) as conn:
        if captured == _NULL_POINTER:
            existing = repo.lock_active_run(conn)
            if existing is None:
                report.noop = 1
                return report
            raise ApplicationStateConflictError(
                "legacy active-run pointer is absent/null but play.active_run already has a selection"
            )
        run_id, selected_at = captured
        run = repo.lock_run(conn, run_id)
        if run is None:
            raise ApplicationStateIntegrityError(
                f"legacy active-run pointer references a missing Play Run: {run_id}"
            )
        require_persisted_aggregate_integrity(run, repo.get_manifest(conn, run_id))
        existing = repo.lock_active_run(conn)
        if existing is not None:
            if (
                existing.run_id == run_id
                and _iso_z(existing.selected_at) == _iso_z(selected_at)
            ):
                report.noop = 1
                return report
            raise ApplicationStateConflictError(
                "legacy active-run pointer conflicts with the stored play.active_run selection"
            )
        stored = repo.upsert_active_run(conn, run_id=run_id, selected_at=selected_at)
        if stored.run_id != run_id or _iso_z(stored.selected_at) != _iso_z(selected_at):
            raise ApplicationStateIntegrityError(
                "imported play.active_run does not match the captured legacy pointer"
            )
        report.imported = 1
        return report
