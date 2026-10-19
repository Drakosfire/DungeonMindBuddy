"""Typed records and bounded validation for inert Play scene edit proposals."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import Field, model_validator

from application_state.agent_conversation.types import PlayRunTurnContextReceiptV2, StrictModel

MAX_JSON_BYTES = 1024 * 1024
MAX_CONTEXT_BYTES = 256 * 1024
MAX_FRAGMENT_BYTES = 256 * 1024
_SCENE_ID = re.compile(r"^scene:[a-z0-9][a-z0-9._-]{0,127}$")
_FAILURE_CODE = re.compile(r"^[a-z][a-z0-9_]{0,63}$")


def canonical_json_bytes(value: object) -> bytes:
    try:
        return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    except (TypeError, ValueError, UnicodeEncodeError) as exc:
        raise ValueError("proposal values must be canonical UTF-8 JSON") from exc


def _bounded_json(value: object, limit: int, label: str) -> bytes:
    encoded = canonical_json_bytes(value)
    if len(encoded) > limit:
        raise ValueError(f"{label} exceeds its UTF-8 JSON storage limit")
    return encoded


class SceneEditProposalRecord(StrictModel):
    world_id: str = Field(min_length=1, max_length=128)
    run_id: UUID
    proposal_id: UUID
    request_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    request: dict
    context_receipt: PlayRunTurnContextReceiptV2
    status: Literal["pending", "ready", "failed"]
    result: dict | None = None
    failure_code: str | None = Field(default=None, pattern=r"^[a-z][a-z0-9_]{0,63}$")
    created_at: datetime
    updated_at: datetime

    @model_validator(mode="after")
    def validate_record(self) -> "SceneEditProposalRecord":
        if self.world_id != self.world_id.strip():
            raise ValueError("world_id must be canonical")
        _bounded_json(self.request, MAX_CONTEXT_BYTES, "proposal request")
        _bounded_json(self.context_receipt.model_dump(mode="json", by_alias=True), MAX_CONTEXT_BYTES, "context receipt")
        _validate_request(self.request, self.context_receipt)
        expected = hashlib.sha256(canonical_json_bytes({
            "request": self.request,
            "context_receipt": self.context_receipt.model_dump(mode="json", by_alias=True),
        })).hexdigest()
        if self.request_sha256 != expected:
            raise ValueError("proposal request fingerprint does not match frozen basis")
        if self.status == "pending":
            if self.result is not None or self.failure_code is not None:
                raise ValueError("pending proposals cannot carry terminal data")
        elif self.status == "ready":
            if self.failure_code is not None or self.result is None:
                raise ValueError("ready proposals require a result and no failure code")
            validate_result(self.result)
        elif self.result is not None or self.failure_code is None:
            raise ValueError("failed proposals require a failure code and no result")
        return self


def _validate_request(request: dict, receipt: PlayRunTurnContextReceiptV2) -> None:
    if request.get("schema_version") != "dmb_play_scene_edit_request_v1":
        raise ValueError("unsupported Play scene edit request schema")
    if set(request) != {"schema_version", "run_revision", "content_basis", "scene_id", "instruction"}:
        raise ValueError("Play scene edit request has unexpected fields")
    revision = request["run_revision"]
    if not isinstance(revision, int) or isinstance(revision, bool) or revision < 1:
        raise ValueError("run_revision must be a positive integer")
    basis = request["content_basis"]
    if not isinstance(basis, dict) or set(basis) != {"edition_revision", "edition_revision_id", "content_sha256"}:
        raise ValueError("content_basis is invalid")
    if (basis["edition_revision"] != receipt.edition_revision
            or basis["edition_revision_id"] != (str(receipt.edition_revision_id) if receipt.edition_revision_id else None)
            or basis["content_sha256"] != receipt.content_sha256):
        raise ValueError("request content basis differs from its frozen context receipt")
    if revision != receipt.run_revision:
        raise ValueError("request Run revision differs from its frozen context receipt")
    scene_id = request["scene_id"]
    if scene_id != receipt.scene_id or not isinstance(scene_id, str) or not _SCENE_ID.fullmatch(scene_id):
        raise ValueError("request Scene differs from its frozen context receipt")
    instruction = request["instruction"]
    if not isinstance(instruction, str) or not instruction.strip() or len(instruction) > 8000:
        raise ValueError("instruction must be non-empty and at most 8000 characters")


def validate_result(result: dict) -> None:
    keys = {"schema_version", "before_markdown", "replacement_markdown", "candidate_markdown", "candidate_sha256", "summary", "assumptions", "model", "model_observed", "model_latency_ms", "wall_latency_ms"}
    optional_offsets = {"body_start_utf8", "body_end_utf8"}
    if (not isinstance(result, dict) or not keys.issubset(result)
            or set(result) - keys - optional_offsets
            or (set(result) & optional_offsets not in (set(), optional_offsets))
            or result.get("schema_version") != "dmb_play_scene_edit_result_v1"):
        raise ValueError("invalid Play scene edit result schema")
    for key in ("before_markdown", "replacement_markdown", "candidate_markdown"):
        value = result[key]
        limit = MAX_JSON_BYTES if key == "candidate_markdown" else MAX_FRAGMENT_BYTES
        if not isinstance(value, str) or len(value.encode("utf-8")) > limit:
            raise ValueError(f"{key} exceeds its UTF-8 size limit")
    digest = hashlib.sha256(result["candidate_markdown"].encode("utf-8")).hexdigest()
    if result["candidate_sha256"] != digest:
        raise ValueError("candidate_sha256 does not match candidate Markdown")
    if optional_offsets.issubset(result):
        start, end = result["body_start_utf8"], result["body_end_utf8"]
        candidate_bytes = len(result["candidate_markdown"].encode("utf-8"))
        before_bytes = len(result["before_markdown"].encode("utf-8"))
        replacement_bytes = len(result["replacement_markdown"].encode("utf-8"))
        original_bytes = candidate_bytes - replacement_bytes + before_bytes
        if (not isinstance(start, int) or isinstance(start, bool) or not isinstance(end, int)
                or isinstance(end, bool) or start < 0 or end < start
                or end - start != before_bytes or end > original_bytes):
            raise ValueError("scene body offsets must be a bounded UTF-8 range")
    if not isinstance(result["summary"], str) or not result["summary"].strip() or len(result["summary"]) > 2000:
        raise ValueError("summary must be non-empty and bounded")
    assumptions = result["assumptions"]
    if not isinstance(assumptions, list) or len(assumptions) > 32 or any(not isinstance(x, str) or len(x) > 1000 for x in assumptions):
        raise ValueError("assumptions must be a bounded string list")
    if not isinstance(result["model"], str) or not result["model"] or len(result["model"]) > 128:
        raise ValueError("model must be a bounded non-empty string")
    if not isinstance(result["model_observed"], bool):
        raise ValueError("model_observed must be boolean")
    for key in ("model_latency_ms", "wall_latency_ms"):
        value = result[key]
        if not isinstance(value, int) or isinstance(value, bool) or not 0 <= value <= 3_600_000:
            raise ValueError(f"{key} must be a bounded non-negative integer")
    _bounded_json(result, MAX_JSON_BYTES, "proposal result")


def validate_failure_code(value: str | None) -> str:
    if not isinstance(value, str) or not _FAILURE_CODE.fullmatch(value):
        raise ValueError("failure_code must be a canonical lowercase code")
    return value
