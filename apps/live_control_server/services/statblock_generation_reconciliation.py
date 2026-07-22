"""Durable generation request-to-candidate reconciliation for replay recovery."""
from __future__ import annotations

import hashlib
import json
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from apps.live_control_server.integrations.dungeonmind_statblocks.config import (
    validate_candidate_id,
)
from apps.live_control_server.models.threat_draft import require_draft_id
from src.live_play.live_store import load_json, write_json

DEFAULT_RECONCILIATION_REL = "out/statblock_generation_requests"
RECONCILIATION_SCHEMA = "dmb_statblock_generation_request_v1"
_REQUEST_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$")


class GenerationReconciliationError(ValueError):
    status_code: int = 500

    def __init__(self, message: str, *, status_code: int = 500) -> None:
        super().__init__(message)
        self.status_code = status_code


class GenerationReconciliationRecordV1(BaseModel):
    schema_name: Literal["dmb_statblock_generation_request_v1"] = Field(
        default=RECONCILIATION_SCHEMA, alias="schema"
    )
    draft_id: str
    draft_version: int = Field(ge=1)
    request_id: str
    request_digest: str
    candidate_id: str
    created_at: str

    model_config = ConfigDict(extra="forbid", populate_by_name=True)


def _utc_now_iso() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def validate_request_id(value: str) -> str:
    cleaned = value.strip()
    if not _REQUEST_ID_RE.fullmatch(cleaned):
        raise GenerationReconciliationError("invalid request_id", status_code=422)
    return cleaned


def request_digest_for_body(body: dict[str, Any]) -> str:
    canonical = json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return "sha256:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def reconciliation_root(repo_root: Path) -> Path:
    return repo_root / DEFAULT_RECONCILIATION_REL


def _record_path(root: Path, *, draft_id: str, draft_version: int, request_id: str) -> Path:
    try:
        safe_draft = require_draft_id(draft_id)
        safe_request = validate_request_id(request_id)
    except ValueError as exc:
        raise GenerationReconciliationError(str(exc), status_code=422) from None
    if draft_version < 1:
        raise GenerationReconciliationError("invalid draft_version", status_code=422)
    store_root = reconciliation_root(root).resolve()
    directory = (store_root / safe_draft).resolve()
    if directory.parent != store_root:
        raise GenerationReconciliationError(
            "reconciliation path escape",
            status_code=500,
        )
    path = (directory / f"v{draft_version}__{safe_request}.json").resolve()
    if path.parent != directory:
        raise GenerationReconciliationError(
            "reconciliation path escape",
            status_code=500,
        )
    return path


def read_reconciliation(
    root: Path,
    *,
    draft_id: str,
    draft_version: int,
    request_id: str,
) -> GenerationReconciliationRecordV1 | None:
    path = _record_path(
        root,
        draft_id=draft_id,
        draft_version=draft_version,
        request_id=request_id,
    )
    try:
        if not path.is_file():
            return None
        payload = load_json(path)
        record = GenerationReconciliationRecordV1.model_validate(payload)
    except GenerationReconciliationError:
        raise
    except Exception:
        raise GenerationReconciliationError(
            "corrupt generation reconciliation record",
            status_code=500,
        ) from None
    if (
        record.draft_id != require_draft_id(draft_id)
        or record.draft_version != draft_version
        or record.request_id != validate_request_id(request_id)
    ):
        raise GenerationReconciliationError(
            "generation reconciliation identity mismatch",
            status_code=500,
        )
    try:
        validate_candidate_id(record.candidate_id)
    except ValueError as exc:
        raise GenerationReconciliationError(str(exc), status_code=500) from None
    return record


def write_reconciliation(
    root: Path,
    *,
    draft_id: str,
    draft_version: int,
    request_id: str,
    request_digest: str,
    candidate_id: str,
) -> GenerationReconciliationRecordV1:
    try:
        record = GenerationReconciliationRecordV1(
            draft_id=require_draft_id(draft_id),
            draft_version=draft_version,
            request_id=validate_request_id(request_id),
            request_digest=request_digest,
            candidate_id=validate_candidate_id(candidate_id),
            created_at=_utc_now_iso(),
        )
    except GenerationReconciliationError:
        raise
    except ValueError as exc:
        raise GenerationReconciliationError(str(exc), status_code=422) from None
    path = _record_path(
        root,
        draft_id=record.draft_id,
        draft_version=record.draft_version,
        request_id=record.request_id,
    )
    existing = read_reconciliation(
        root,
        draft_id=record.draft_id,
        draft_version=record.draft_version,
        request_id=record.request_id,
    )
    if existing is not None:
        if (
            existing.request_digest != record.request_digest
            or existing.candidate_id != record.candidate_id
        ):
            raise GenerationReconciliationError(
                "generation reconciliation conflict",
                status_code=409,
            )
        return existing
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        write_json(path, record.model_dump(mode="json", by_alias=True))
    except OSError:
        raise GenerationReconciliationError(
            "generation reconciliation storage unavailable",
            status_code=500,
        ) from None
    return record
