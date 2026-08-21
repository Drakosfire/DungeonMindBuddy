"""Play-owned durable selection for ordinary Play re-entry."""

from __future__ import annotations

import re
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, field_validator, model_validator

from apps.live_control_server.services.play_run_reference_manifest import (
    PlayRunReferenceManifestError,
    load_play_run_reference_manifest_for_record,
)
from apps.live_control_server.services.play_run_registry import (
    PlayRunRegistryError,
    get_play_run,
)
from apps.live_control_server.services.registry_file_lock import registry_mutation_lock
from src.live_play.live_store import load_json, write_json

PLAY_ACTIVE_RUN_SCHEMA = "dmb_play_active_run_v1"
PLAY_ACTIVE_RUN_REL = "out/runtime/play/active-run.json"
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


def play_active_run_path(root: Path) -> Path:
    return root / PLAY_ACTIVE_RUN_REL


def _empty_state() -> PlayActiveRunState:
    return PlayActiveRunState(run_id=None, selected_at=None)


def _load_state(path: Path) -> PlayActiveRunState:
    try:
        return PlayActiveRunState.model_validate(load_json(path))
    except (OSError, TypeError, ValueError) as exc:
        raise PlayActiveRunError(
            f"malformed persisted Play active-Run selection {path.name}: {exc}",
            status_code=500,
        ) from exc


def get_play_active_run(root: Path) -> PlayActiveRunState:
    """Read the pointer without inferring or selecting any Run."""

    path = play_active_run_path(root)
    if not path.is_file():
        return _empty_state()
    with registry_mutation_lock(path):
        if not path.is_file():
            return _empty_state()
        return _load_state(path)


def set_play_active_run(root: Path, *, run_id: str) -> PlayActiveRunState:
    """Persist focus on an existing Run after proving its sealed identity."""

    try:
        canonical_run_id = _canonical_uuid(run_id, field_name="run_id")
    except ValueError as exc:
        raise PlayActiveRunError(str(exc), status_code=422) from exc

    try:
        record = get_play_run(root, canonical_run_id)
        load_play_run_reference_manifest_for_record(root, record)
    except PlayRunRegistryError as exc:
        raise PlayActiveRunError(str(exc), status_code=exc.status_code) from exc
    except PlayRunReferenceManifestError as exc:
        status_code = 409 if exc.status_code == 404 else exc.status_code
        raise PlayActiveRunError(str(exc), status_code=status_code) from exc

    path = play_active_run_path(root)
    with registry_mutation_lock(path):
        if path.is_file():
            current = _load_state(path)
            if current.run_id == canonical_run_id:
                return current

        state = PlayActiveRunState(
            run_id=canonical_run_id,
            selected_at=datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        )
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            write_json(path, state.model_dump(mode="json"))
        except (OSError, TypeError, ValueError) as exc:
            raise PlayActiveRunError(
                f"failed to persist Play active-Run selection: {exc}",
                status_code=500,
            ) from exc
        return state
