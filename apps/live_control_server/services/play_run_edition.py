"""HTTP adapter for the Play-owned content edition capability.

A 404 command read is absence at that instant, not proof an in-flight command
cannot commit. Recover a lost response by replaying identical command bytes or
reading that command, never by inventing a new command identity.
"""

from fastapi import HTTPException
from pydantic import ValidationError

from application_state.errors import ApplicationStateError
from application_state.play.edition_types import ContentCommit
from application_state.play.edition_service import (
    commit_content,
    read_command,
    read_content,
)

__all__ = [
    "commit_content",
    "read_command",
    "read_content",
    "edition_response",
    "parse_commit",
]


def edition_response(operation, **kwargs):
    try:
        return operation(**kwargs).model_dump(mode="json")
    except ApplicationStateError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc


def parse_commit(raw: bytes) -> ContentCommit:
    if len(raw) > 1048576:
        raise HTTPException(
            status_code=413, detail="Run content command exceeds 1 MiB UTF8"
        )
    try:
        return ContentCommit.model_validate_json(raw)
    except ValidationError as exc:
        raise HTTPException(
            status_code=422, detail=exc.errors(include_context=False)
        ) from exc
