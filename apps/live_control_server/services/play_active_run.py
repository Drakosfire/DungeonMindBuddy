"""Play-owned durable selection for ordinary Play re-entry."""

from __future__ import annotations

import re
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, field_validator, model_validator

from application_state.errors import ApplicationStateError
from application_state.play import service as play_service

PLAY_ACTIVE_RUN_SCHEMA = "dmb_play_active_run_v1"
_UTC_TIMESTAMP_RE = re.compile(r".*Z$")


class PlayActiveRunError(ValueError):
    """Fail-closed error for the Play active-Run selection record."""

    status_code: int = 500

    def __init__(self, message: str, *, status_code: int = 500) -> None:
        super().__init__(message)
        self.status_code = status_code


def _canonical_uuid(value: str, *, field_name: str) -> str:
    cleaned = value.strip()
    try:
        parsed = uuid.UUID(cleaned)
    except (AttributeError, ValueError) as exc:
        raise ValueError(f"{field_name} must be a canonical UUID") from exc
    canonical = str(parsed)
    if cleaned != canonical:
        raise ValueError(f"{field_name} must be a canonical UUID")
    return canonical


def _utc_iso(value: str) -> str:
    cleaned = value.strip()
    if not _UTC_TIMESTAMP_RE.fullmatch(cleaned):
        raise ValueError("selected_at must be an ISO-8601 UTC value ending in Z")
    try:
        parsed = datetime.fromisoformat(cleaned[:-1] + "+00:00")
    except ValueError as exc:
        raise ValueError("selected_at must be an ISO-8601 UTC value") from exc
    if parsed.utcoffset() != UTC.utcoffset(parsed):
        raise ValueError("selected_at must be UTC")
    return cleaned


def _iso_z(value: datetime) -> str:
    stamp = value if value.tzinfo is not None else value.replace(tzinfo=UTC)
    return stamp.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _map_application_state(exc: Exception) -> PlayActiveRunError:
    return PlayActiveRunError(str(exc), status_code=int(getattr(exc, "status_code", 500)))


class SetPlayActiveRunRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    run_id: str

    @field_validator("run_id")
    @classmethod
    def _validate_run_id(cls, value: str) -> str:
        return _canonical_uuid(value, field_name="run_id")


class PlayActiveRunState(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    schema_version: Literal["dmb_play_active_run_v1"] = PLAY_ACTIVE_RUN_SCHEMA
    run_id: str | None
    selected_at: str | None

    @field_validator("run_id")
    @classmethod
    def _validate_run_id(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return _canonical_uuid(value, field_name="run_id")

    @field_validator("selected_at")
    @classmethod
    def _validate_selected_at(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return _utc_iso(value)

    @model_validator(mode="after")
    def _validate_selection_pair(self) -> "PlayActiveRunState":
        if (self.run_id is None) != (self.selected_at is None):
            raise ValueError("run_id and selected_at must both be present or both be null")
        return self


def _empty_state() -> PlayActiveRunState:
    return PlayActiveRunState(run_id=None, selected_at=None)


def _state_from_row(row: object) -> PlayActiveRunState:
    return PlayActiveRunState(run_id=str(row.run_id), selected_at=_iso_z(row.selected_at))


def get_play_active_run(root: Path) -> PlayActiveRunState:
    """Read the PostgreSQL pointer without inferring or selecting any Run."""

    del root
    try:
        row = play_service.get_play_active_run()
    except ApplicationStateError as exc:
        raise _map_application_state(exc) from exc
    if row is None:
        return _empty_state()
    return _state_from_row(row)


def set_play_active_run(root: Path, *, run_id: str) -> PlayActiveRunState:
    """Persist focus on an existing PostgreSQL Run after proving its sealed identity."""

    del root
    try:
        canonical_run_id = _canonical_uuid(run_id, field_name="run_id")
    except ValueError as exc:
        raise PlayActiveRunError(str(exc), status_code=422) from exc
    try:
        row = play_service.set_play_active_run(canonical_run_id)
    except ApplicationStateError as exc:
        raise _map_application_state(exc) from exc
    return _state_from_row(row)


def clear_play_active_run(root: Path) -> PlayActiveRunState:
    """Delete the singleton row. Missing row is the durable null state."""

    del root
    try:
        play_service.clear_play_active_run()
    except ApplicationStateError as exc:
        raise _map_application_state(exc) from exc
    return _empty_state()
