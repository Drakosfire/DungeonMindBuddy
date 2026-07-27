"""SBW06a: revise-operation models and Buddy-local revise API contracts."""
from __future__ import annotations

import hashlib
import json
import re
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from apps.live_control_server.integrations.dungeonmind_statblocks.generated.models import (
    AssetOptionsV1,
    EncounterContextV1,
    GenerationIntentV1,
    ReviseCandidateRequestV1,
    RulesetRef,
    SourceSnapshotV1,
    StatblockDefinitionV1Input,
)
from apps.live_control_server.services.statblock_generation_reconciliation import (
    validate_request_id,
)

REVISE_OPERATION_SCHEMA = "dmb_statblock_revise_operation_v1"

MAX_REVISION_INSTRUCTIONS = 16
MAX_INSTRUCTION_CODEPOINTS = 500
MAX_INSTRUCTIONS_TOTAL_CODEPOINTS = 4000

_REQUEST_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$")


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


ReviseOperationStatus = Literal[
    "claimed",
    "dispatched_unknown",
    "candidate_received",
    "cache_stored_ref_pending",
    "reconciled",
    "terminal_failure",
]

ReviseCacheMaterialization = Literal["missing", "stored", "failed"]
ReviseDraftRefMaterialization = Literal["missing", "failed", "attached"]
ReviseSourceStatusMaterialization = Literal["none", "applied"]

ClaimReviseOutcome = Literal[
    "claimed",
    "resume",
    "revise_input_conflict",
    "revise_busy",
    "revise_history_full",
    "version_mismatch",
]

ReviseResultLabel = Literal[
    "revise_claimed",
    "dispatched_unknown",
    "candidate_received",
    "cache_stored_ref_pending",
    "reconciled",
    "revise_busy",
    "revise_history_full",
    "revise_input_conflict",
    "revise_integrity_conflict",
    "revise_blocked",
    "revise_draft_unavailable",
    "terminal_failure",
]


class ReviseMaterializationV1(StrictModel):
    cache: ReviseCacheMaterialization = "missing"
    draft_ref: ReviseDraftRefMaterialization = "missing"
    source_status: ReviseSourceStatusMaterialization = "none"


class ReviseOperationV1(StrictModel):
    schema_name: Literal["dmb_statblock_revise_operation_v1"] = Field(
        default=REVISE_OPERATION_SCHEMA, alias="schema"
    )
    request_id: str
    request_digest: str = Field(min_length=1)
    request_body: dict[str, Any]
    draft_id: str
    source_draft_version: int = Field(ge=1)
    editor_state_revision: str = Field(min_length=1, max_length=256)
    source_origin_kind: Literal["edited_working_copy"] = "edited_working_copy"
    source_definition_digest: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    instruction_options_digest: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    status: ReviseOperationStatus
    candidate_id: str | None = Field(default=None, pattern=r"^cand_[a-z0-9]+$")
    materialization: ReviseMaterializationV1 = Field(
        default_factory=ReviseMaterializationV1
    )
    terminal_code: str | None = None
    failure_category: str | None = None
    http_status: int | None = None
    terminal_details: dict[str, Any] | None = None
    # Non-terminal authority/recovery annotation (e.g. exact-body 409).
    # Allowed on dispatched_unknown only; never releases the reservation.
    recovery_classification: str | None = None
    recovery_details: dict[str, Any] | None = None
    created_at: str
    updated_at: str

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    @field_validator("request_id")
    @classmethod
    def _request_id(cls, value: str) -> str:
        return validate_request_id(value)

    @model_validator(mode="after")
    def _invariants(self) -> ReviseOperationV1:
        try:
            typed = ReviseCandidateRequestV1.model_validate(self.request_body)
        except Exception as exc:
            raise ValueError("request_body must validate as ReviseCandidateRequestV1") from exc

        if typed.request_id != self.request_id:
            raise ValueError("request_body.request_id must equal record request_id")

        recomputed = revise_request_digest_for_server_body(self.request_body)
        if recomputed != self.request_digest:
            raise ValueError("request_digest does not match request_body")

        src_digest = source_definition_digest_from_body(self.request_body["source_definition"])
        if src_digest != self.source_definition_digest:
            raise ValueError("source_definition_digest does not match request_body")

        normalized = normalize_revision_instructions(typed.revision_instructions)
        instr_digest = instruction_options_digest(
            normalized, typed.preserve_element_keys
        )
        if instr_digest != self.instruction_options_digest:
            raise ValueError("instruction_options_digest does not match request_body")

        state = self.status
        has_terminal = (
            self.terminal_code is not None
            or self.failure_category is not None
            or self.http_status is not None
            or self.terminal_details is not None
        )
        has_recovery = (
            self.recovery_classification is not None
            or self.recovery_details is not None
        )
        if state == "claimed":
            if self.candidate_id is not None:
                raise ValueError("claimed forbids candidate_id")
            if self.materialization.cache != "missing":
                raise ValueError("claimed requires cache=missing")
            if self.materialization.draft_ref != "missing":
                raise ValueError("claimed requires draft_ref=missing")
            if has_terminal:
                raise ValueError("claimed forbids terminal fields")
            if has_recovery:
                raise ValueError("claimed forbids recovery classification")
        elif state == "dispatched_unknown":
            if self.materialization.draft_ref != "missing":
                raise ValueError("dispatched_unknown requires draft_ref=missing")
            if has_terminal:
                raise ValueError("dispatched_unknown forbids terminal fields")
            # recovery_classification may annotate exact-body Server 409 without
            # terminalizing or releasing the reservation.
        elif state == "candidate_received":
            if not self.candidate_id:
                raise ValueError("candidate_received requires candidate_id")
            if self.materialization.draft_ref not in {"missing", "failed"}:
                raise ValueError(
                    "candidate_received requires draft_ref missing|failed"
                )
            if has_terminal:
                raise ValueError("candidate_received forbids terminal fields")
            if has_recovery:
                raise ValueError("candidate_received forbids recovery classification")
        elif state == "cache_stored_ref_pending":
            if not self.candidate_id:
                raise ValueError("cache_stored_ref_pending requires candidate_id")
            if self.materialization.cache != "stored":
                raise ValueError("cache_stored_ref_pending requires cache=stored")
            if self.materialization.draft_ref not in {"missing", "failed"}:
                raise ValueError(
                    "cache_stored_ref_pending requires draft_ref missing|failed"
                )
            if has_terminal:
                raise ValueError("cache_stored_ref_pending forbids terminal fields")
            if has_recovery:
                raise ValueError(
                    "cache_stored_ref_pending forbids recovery classification"
                )
        elif state == "reconciled":
            if not self.candidate_id:
                raise ValueError("reconciled requires candidate_id")
            if self.materialization.cache not in {"stored", "failed", "missing"}:
                raise ValueError("reconciled requires cache stored|failed|missing")
            if self.materialization.draft_ref != "attached":
                raise ValueError("reconciled requires draft_ref=attached")
            if self.materialization.source_status not in {"none", "applied"}:
                raise ValueError("reconciled requires source_status none|applied")
            if has_terminal:
                raise ValueError("reconciled forbids terminal fields")
            if has_recovery:
                raise ValueError("reconciled forbids recovery classification")
        elif state == "terminal_failure":
            if self.candidate_id is not None:
                raise ValueError("terminal_failure forbids candidate_id")
            if self.materialization.cache != "missing":
                raise ValueError("terminal_failure requires cache=missing")
            if self.materialization.draft_ref != "missing":
                raise ValueError("terminal_failure requires draft_ref=missing")
            if (
                not self.terminal_code
                or not self.failure_category
                or self.http_status is None
            ):
                raise ValueError("terminal_failure requires terminal fields")
            if has_recovery:
                raise ValueError("terminal_failure forbids recovery classification")
        return self


class ReviseCandidateFromEditedDefinitionRequestV1(StrictModel):
    request_id: str
    expected_draft_version: int = Field(ge=1)
    editor_state_revision: str = Field(min_length=1, max_length=256)
    source_definition: StatblockDefinitionV1Input
    revision_instructions: list[str] = Field(min_length=1)
    preserve_element_keys: bool = True
    ruleset: RulesetRef
    actor: str | None = Field(default=None, max_length=128)
    intent: GenerationIntentV1 | None = None
    context: EncounterContextV1 | None = None
    asset_options: AssetOptionsV1 | None = None
    source: SourceSnapshotV1 | None = None

    @field_validator("request_id")
    @classmethod
    def _request_id(cls, value: str) -> str:
        return validate_request_id(value)


class ReviseCandidateFromEditedDefinitionResponseV1(StrictModel):
    schema_name: Literal["dmb_revise_candidate_from_edited_definition_response_v1"] = (
        Field(default="dmb_revise_candidate_from_edited_definition_response_v1", alias="schema")
    )
    result: ReviseResultLabel
    request_id: str
    operation_status: ReviseOperationStatus | None = None
    candidate_id: str | None = None
    request_digest: str
    source_definition_digest: str
    instruction_options_digest: str

    model_config = ConfigDict(extra="forbid", populate_by_name=True)


def normalize_revision_instructions(raw: list[str]) -> list[str]:
    """Trim, drop empty, preserve order; enforce §12.4 bounds."""
    normalized: list[str] = []
    total_codepoints = 0
    for item in raw:
        trimmed = item.strip()
        if not trimmed:
            continue
        if len(trimmed) > MAX_INSTRUCTION_CODEPOINTS:
            raise ValueError("revision instruction exceeds maximum length")
        total_codepoints += len(trimmed)
        if total_codepoints > MAX_INSTRUCTIONS_TOTAL_CODEPOINTS:
            raise ValueError("revision instructions exceed total payload bound")
        normalized.append(trimmed)
    if not normalized:
        raise ValueError("revision instructions empty after normalization")
    if len(normalized) > MAX_REVISION_INSTRUCTIONS:
        raise ValueError("too many revision instructions")
    return normalized


def source_definition_digest_from_body(source_definition: dict[str, Any]) -> str:
    """Server-compatible definition digest (parse → canonicalize → sha256)."""
    from apps.live_control_server.integrations.dungeonmind_statblocks.definition_digest import (
        source_definition_digest_from_body as _server_compatible_digest,
    )

    return _server_compatible_digest(source_definition)


def instruction_options_digest(
    normalized_instructions: list[str],
    preserve_element_keys: bool,
) -> str:
    payload = {
        "revision_instructions": normalized_instructions,
        "preserve_element_keys": preserve_element_keys,
    }
    canonical = json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    )
    return "sha256:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def revise_request_digest_for_server_body(body: dict[str, Any]) -> str:
    """Buddy-owned request digest inputs (§12.4); not Server private digest.

    Includes ``actor`` (nullable) so journal integrity matches Server revise
    request identity, which always digests caller actor.
    """
    if body.get("source_locator") is not None and body.get("source_definition") is not None:
        raise ValueError("ambiguous revise source")
    if body.get("source_definition") is None:
        raise ValueError("SBW06a requires source_definition")
    normalized = normalize_revision_instructions(body["revision_instructions"])
    payload: dict[str, Any] = {
        "source_variant": "definition",
        "source_definition_digest": source_definition_digest_from_body(
            body["source_definition"]
        ),
        "revision_instructions": normalized,
        "preserve_element_keys": body.get("preserve_element_keys", True),
        "ruleset": body["ruleset"],
        "actor": body.get("actor"),
    }
    for key in ("intent", "context", "asset_options", "source"):
        value = body.get(key)
        if value is not None:
            payload[key] = value
    canonical = json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    )
    return "sha256:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def map_edited_definition_to_revise_server_body(
    request: ReviseCandidateFromEditedDefinitionRequestV1,
) -> dict[str, Any]:
    normalized = normalize_revision_instructions(request.revision_instructions)
    typed = ReviseCandidateRequestV1(
        request_id=request.request_id,
        ruleset=request.ruleset,
        revision_instructions=normalized,
        source_definition=request.source_definition,
        source_locator=None,
        preserve_element_keys=request.preserve_element_keys,
        actor=request.actor,
        intent=request.intent,
        context=request.context,
        asset_options=request.asset_options,
        source=request.source,
    )
    return json.loads(
        typed.model_dump_json(by_alias=True, exclude_none=True)
    )


__all__ = [
    "REVISE_OPERATION_SCHEMA",
    "ClaimReviseOutcome",
    "ReviseCandidateFromEditedDefinitionRequestV1",
    "ReviseCandidateFromEditedDefinitionResponseV1",
    "ReviseMaterializationV1",
    "ReviseOperationV1",
    "ReviseResultLabel",
    "instruction_options_digest",
    "map_edited_definition_to_revise_server_body",
    "normalize_revision_instructions",
    "revise_request_digest_for_server_body",
    "source_definition_digest_from_body",
]
