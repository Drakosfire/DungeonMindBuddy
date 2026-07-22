"""Strict versioned ThreatDraft domain models."""
from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

SCHEMA = "dmb_threat_draft_v1"
SUMMARY_SCHEMA = "dmb_threat_draft_summary_v1"
_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$")
_MAX_TEXT = 20_000
_MAX_LIST = 64
_MAX_NAME = 200


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


def _require_id(value: str, *, label: str) -> str:
    cleaned = value.strip()
    if not _ID_RE.fullmatch(cleaned):
        raise ValueError(f"invalid {label}")
    return cleaned


class RulesetRefV1(StrictModel):
    system: str = Field(min_length=1, max_length=64)
    edition: str = Field(min_length=1, max_length=64)
    house_ruleset_id: str | None = None


class GenerationIntentV1(StrictModel):
    ruleset: RulesetRefV1
    target_cr: str | None = None
    complexity: str | None = None
    must_include: list[str] = Field(default_factory=list, max_length=_MAX_LIST)
    must_avoid: list[str] = Field(default_factory=list, max_length=_MAX_LIST)


class EncounterContextV1(StrictModel):
    party_level: int | None = Field(default=None, ge=1, le=30)
    party_size: int | None = Field(default=None, ge=1, le=20)
    terrain_notes: list[str] = Field(default_factory=list, max_length=_MAX_LIST)


class GraphContextSnapshotV1(StrictModel):
    graph_revision_id: str
    selected_node_ids: list[str] = Field(default_factory=list, max_length=_MAX_LIST)
    admitted_source_anchor_ids: list[str] = Field(default_factory=list, max_length=_MAX_LIST)

    @field_validator("graph_revision_id")
    @classmethod
    def _graph_revision_id(cls, value: str) -> str:
        return _require_id(value, label="graph_revision_id")

    @field_validator("selected_node_ids", "admitted_source_anchor_ids")
    @classmethod
    def _pointer_ids(cls, values: list[str]) -> list[str]:
        return [_require_id(item, label="graph pointer id") for item in values]


class FocusV1(StrictModel):
    session: int | None = Field(default=None, ge=0)
    prep_label: str | None = Field(default=None, max_length=_MAX_NAME)


class ThreatDraftCandidateRefV1(StrictModel):
    candidate_id: str
    generated_from_draft_version: int = Field(ge=1)
    request_id: str
    created_at: str
    expires_at: str | None = None
    status: Literal["active", "superseded", "rejected", "expired", "accepted_source"] = "active"

    @field_validator("candidate_id", "request_id")
    @classmethod
    def _ids(cls, value: str) -> str:
        return _require_id(value, label="candidate ref id")


class ThreatDraftV1(StrictModel):
    schema_name: Literal["dmb_threat_draft_v1"] = Field(default=SCHEMA, alias="schema")
    draft_id: str
    version: int = Field(ge=1)
    world_id: str
    campaign_id: str
    focus: FocusV1 | None = None
    name: str = Field(min_length=1, max_length=_MAX_NAME)
    slug_hint: str | None = Field(default=None, max_length=_MAX_NAME)
    description: str = Field(min_length=1, max_length=_MAX_TEXT)
    threat_kind: str = Field(min_length=1, max_length=64)
    intended_roles: list[str] = Field(default_factory=list, max_length=_MAX_LIST)
    tags: list[str] = Field(default_factory=list, max_length=_MAX_LIST)
    generation_intent: GenerationIntentV1
    encounter_context: EncounterContextV1 = Field(default_factory=EncounterContextV1)
    graph_context_snapshot: GraphContextSnapshotV1
    candidate_refs: list[ThreatDraftCandidateRefV1] = Field(default_factory=list)
    accepted_mechanics_ref: dict | None = None
    workflow_state: Literal[
        "drafting",
        "candidate_ready",
        "mechanics_saved",
        "publication_pending",
    ] = "drafting"
    created_by: str = Field(min_length=1, max_length=_MAX_NAME)
    created_at: str
    updated_at: str

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    @field_validator("draft_id", "world_id", "campaign_id")
    @classmethod
    def _identity_ids(cls, value: str) -> str:
        return _require_id(value, label="identity id")


class ThreatDraftSummaryV1(StrictModel):
    schema_name: Literal["dmb_threat_draft_summary_v1"] = Field(
        default=SUMMARY_SCHEMA, alias="schema"
    )
    draft_id: str
    version: int
    world_id: str
    campaign_id: str
    name: str
    threat_kind: str
    workflow_state: str
    updated_at: str

    model_config = ConfigDict(extra="forbid", populate_by_name=True)


class CreateThreatDraftRequest(StrictModel):
    world_id: str
    campaign_id: str
    focus: FocusV1 | None = None
    name: str = Field(min_length=1, max_length=_MAX_NAME)
    slug_hint: str | None = Field(default=None, max_length=_MAX_NAME)
    description: str = Field(min_length=1, max_length=_MAX_TEXT)
    threat_kind: str = Field(min_length=1, max_length=64)
    intended_roles: list[str] = Field(default_factory=list, max_length=_MAX_LIST)
    tags: list[str] = Field(default_factory=list, max_length=_MAX_LIST)
    generation_intent: GenerationIntentV1
    encounter_context: EncounterContextV1 = Field(default_factory=EncounterContextV1)
    graph_context_snapshot: GraphContextSnapshotV1
    created_by: str = Field(min_length=1, max_length=_MAX_NAME)

    model_config = ConfigDict(extra="forbid")

    @field_validator("world_id", "campaign_id")
    @classmethod
    def _scope_ids(cls, value: str) -> str:
        return _require_id(value, label="scope id")


class UpdateThreatDraftRequest(StrictModel):
    expected_version: int = Field(ge=1)
    focus: FocusV1 | None = None
    name: str = Field(min_length=1, max_length=_MAX_NAME)
    slug_hint: str | None = Field(default=None, max_length=_MAX_NAME)
    description: str = Field(min_length=1, max_length=_MAX_TEXT)
    threat_kind: str = Field(min_length=1, max_length=64)
    intended_roles: list[str] = Field(default_factory=list, max_length=_MAX_LIST)
    tags: list[str] = Field(default_factory=list, max_length=_MAX_LIST)
    generation_intent: GenerationIntentV1
    encounter_context: EncounterContextV1 = Field(default_factory=EncounterContextV1)
    graph_context_snapshot: GraphContextSnapshotV1

    model_config = ConfigDict(extra="forbid")


class ThreatDraftListResponse(StrictModel):
    schema_name: Literal["dmb_threat_draft_list_v1"] = Field(
        default="dmb_threat_draft_list_v1", alias="schema"
    )
    drafts: list[ThreatDraftSummaryV1] = Field(default_factory=list)

    model_config = ConfigDict(extra="forbid", populate_by_name=True)
