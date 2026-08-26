"""Preserve-only same-artifact Play Run rebase."""

from __future__ import annotations

import re
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from apps.live_control_server.services.play_run_registry import PlayRunRecord

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


class PlayRunRebaseError(ValueError):
    """Fail-closed error for preserve-only Play Run rebase."""

    status_code: int = 500

    def __init__(self, message: str, *, status_code: int = 500) -> None:
        super().__init__(message)
        self.status_code = status_code


class RebasePlayRunRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    expected_run_revision: int = Field(gt=0)
    target_playable_revision: int = Field(gt=0)
    target_playable_content_sha256: str

    @field_validator("target_playable_content_sha256")
    @classmethod
    def _validate_target_sha(cls, value: str) -> str:
        cleaned = value.strip()
        if not _SHA256_RE.fullmatch(cleaned):
            raise ValueError(
                "target_playable_content_sha256 must be 64 lowercase hex characters"
            )
        return cleaned


def rebase_or_replay_play_run(
    root: Path,
    *,
    run_id: str,
    expected_run_revision: int,
    target_playable_revision: int,
    target_playable_content_sha256: str,
) -> PlayRunRecord:
    del root
    from application_state.errors import ApplicationStateError
    from application_state.play.service import rebase_play_run
    from apps.live_control_server.services.play_run_registry import (
        _record_from_play_run,
        _validate_run_id,
    )

    try:
        request = RebasePlayRunRequest(
            expected_run_revision=expected_run_revision,
            target_playable_revision=target_playable_revision,
            target_playable_content_sha256=target_playable_content_sha256,
        )
    except ValidationError as exc:
        raise PlayRunRebaseError(str(exc), status_code=422) from exc

    canonical_run_id = _validate_run_id(run_id)
    try:
        aggregate = rebase_play_run(
            run_id=canonical_run_id,
            expected_run_revision=request.expected_run_revision,
            target_playable_revision=request.target_playable_revision,
            target_playable_content_sha256=request.target_playable_content_sha256,
        )
    except ApplicationStateError as exc:
        raise PlayRunRebaseError(str(exc), status_code=exc.status_code) from exc
    return _record_from_play_run(aggregate.run)
