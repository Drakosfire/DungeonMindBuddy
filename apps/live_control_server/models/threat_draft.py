"""Strict versioned ThreatDraft domain models."""
from __future__ import annotations

import re
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from apps.live_control_server.models.statblock_mechanics_acceptance import (
    AcceptedMechanicsRefV1,
)

SCHEMA = "dmb_threat_draft_v1"
SUMMARY_SCHEMA = "dmb_threat_draft_summary_v1"
INDEX_SCHEMA = "dmb_threat_draft_index_v1"
LIST_SCHEMA = "dmb_threat_draft_list_v1"

_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$")
# World Graph revision ids are typically `rev:<hex>`; ThreatDraft must accept the colon.
_GRAPH_REVISION_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$")
_MAX_TEXT = 20_000
_MAX_LIST = 64
_MAX_NAME = 200
_MAX_SHORT = 64
_MAX_CR = 32
_MAX_LIST_ELEMENT = 500

DEFAULT_LIST_LIMIT = 50
MAX_LIST_LIMIT = 100
MAX_CANDIDATE_REFS = _MAX_LIST


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


def _require_id(value: str, *, label: str) -> str:
    cleaned = value.strip()
    if not _ID_RE.fullmatch(cleaned):
        raise ValueError(f"invalid {label}")
    return cleaned


def _require_graph_revision_id(value: str | None) -> str | None:
    """Accept None for freestanding drafts; otherwise require a concrete revision id.

    ThreatDraft creation and candidate generation do not write to the World Graph.
    A graph revision is provenance for later publication / grounding, not a
    prerequisite for authoring or generation.
    """
    if value is None:
        return None
    cleaned = value.strip()
    if not cleaned:
        return None
    if not _GRAPH_REVISION_ID_RE.fullmatch(cleaned):
        raise ValueError("invalid graph_revision_id")
    return cleaned


def require_draft_id(value: str) -> str:
    """Draft identity is always a UUID; reject path/traversal forms."""
    cleaned = value.strip()
    try:
        return str(UUID(cleaned))
    except ValueError as exc:
        raise ValueError("invalid draft_id") from exc


def _bounded_string_list(values: list[str], *, label: str) -> list[str]:
    bounded: list[str] = []
    for item in values:
        if not isinstance(item, str):
            raise ValueError(f"invalid {label} element")
        cleaned = item.strip()
        if not cleaned:
            raise ValueError(f"empty {label} element")
        if len(cleaned) > _MAX_LIST_ELEMENT:
            raise ValueError(f"{label} element exceeds max length")
        bounded.append(cleaned)
    return bounded


class RulesetRefV1(StrictModel):
    system: str = Field(min_length=1, max_length=_MAX_SHORT)
    edition: str = Field(min_length=1, max_length=_MAX_SHORT)
    house_ruleset_id: str | None = Field(default=None, max_length=_MAX_SHORT)


class GenerationIntentV1(StrictModel):
    ruleset: RulesetRefV1
    target_cr: str | None = Field(default=None, max_length=_MAX_CR)
    complexity: str | None = Field(default=None, max_length=_MAX_SHORT)
    must_include: list[str] = Field(default_factory=list, max_length=_MAX_LIST)
    must_avoid: list[str] = Field(default_factory=list, max_length=_MAX_LIST)

    @field_validator("must_include", "must_avoid")
    @classmethod
    def _instruction_items(cls, values: list[str]) -> list[str]:
        return _bounded_string_list(values, label="generation instruction")


class EncounterContextV1(StrictModel):
    party_level: int | None = Field(default=None, ge=1, le=30)
    party_size: int | None = Field(default=None, ge=1, le=20)
    terrain_notes: list[str] = Field(default_factory=list, max_length=_MAX_LIST)

    @field_validator("terrain_notes")
    @classmethod
    def _terrain_items(cls, values: list[str]) -> list[str]:
        return _bounded_string_list(values, label="terrain note")


class GraphContextSnapshotV1(StrictModel):
    graph_revision_id: str | None = None
    selected_node_ids: list[str] = Field(default_factory=list, max_length=_MAX_LIST)
    admitted_source_anchor_ids: list[str] = Field(default_factory=list, max_length=_MAX_LIST)

    @field_validator("graph_revision_id")
    @classmethod
    def _graph_revision_id(cls, value: str | None) -> str | None:
        return _require_graph_revision_id(value)

    @field_validator("selected_node_ids", "admitted_source_anchor_ids")
    @classmethod
    def _pointer_ids(cls, values: list[str]) -> list[str]:
        return [_require_id(item, label="graph pointer id") for item in values]


class FocusV1(StrictModel):
    session: int | None = Field(default=None, ge=0)
    prep_label: str | None = Field(default=None, max_length=_MAX_NAME)


class EditedWorkingCopyLineageV1(StrictModel):
    draft_id: str
    source_draft_version: int = Field(ge=1)
    editor_state_revision: str = Field(min_length=1, max_length=256)
    source_definition_digest: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @field_validator("draft_id")
    @classmethod
    def _draft_id(cls, value: str) -> str:
        return require_draft_id(value)


class CandidateOriginLineageV1(StrictModel):
    source_candidate_id: str = Field(pattern=r"^cand_[a-z0-9]+$")
    source_candidate_request_id: str
    draft_id: str
    source_generated_from_draft_version: int = Field(ge=1)
    source_definition_digest: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @field_validator("draft_id")
    @classmethod
    def _draft_id(cls, value: str) -> str:
        return require_draft_id(value)

    @field_validator("source_candidate_request_id")
    @classmethod
    def _source_candidate_request_id(cls, value: str) -> str:
        return _require_id(value, label="source_candidate_request_id")


class AcceptedRevisionLineageV1(StrictModel):
    provider: Literal["dungeonmind"] = "dungeonmind"
    statblock_id: str = Field(pattern=r"^sb_[a-z0-9]+$")
    revision_id: str = Field(pattern=r"^rev_[a-z0-9]+$")
    contract: str
    contract_version: str
    definition_digest: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")


class CandidateLineageV1(StrictModel):
    schema_name: Literal["dmb_candidate_lineage_v1"] = Field(
        default="dmb_candidate_lineage_v1", alias="schema"
    )
    revise_request_id: str
    source_origin_kind: Literal[
        "edited_working_copy", "candidate", "accepted_revision"
    ]
    instruction_options_digest: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    created_at: str
    edited_working_copy: EditedWorkingCopyLineageV1 | None = None
    candidate: CandidateOriginLineageV1 | None = None
    accepted_revision: AcceptedRevisionLineageV1 | None = None

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    @field_validator("revise_request_id")
    @classmethod
    def _revise_request_id(cls, value: str) -> str:
        return _require_id(value, label="revise_request_id")

    @model_validator(mode="after")
    def _exactly_one_variant(self) -> CandidateLineageV1:
        variants: dict[str, object | None] = {
            "edited_working_copy": self.edited_working_copy,
            "candidate": self.candidate,
            "accepted_revision": self.accepted_revision,
        }
        present = [name for name, value in variants.items() if value is not None]
        if len(present) != 1 or present[0] != self.source_origin_kind:
            raise ValueError("lineage variant must match source_origin_kind")
        return self


class RequestedSourceStatusTransitionV1(StrictModel):
    """Explicit source-ref lifecycle transition for the revise CAS only.

    ``exact_expires_at`` is required for ``expired`` and must equal the source
    candidate ref's durable ``expires_at`` (exact expiry evidence, not a bool).
    """

    source_candidate_id: str = Field(pattern=r"^cand_[a-z0-9]+$")
    to_status: Literal[
        "superseded", "rejected", "expired", "accepted_source", "active"
    ]
    exact_expires_at: str | None = Field(default=None, max_length=64)


class ThreatDraftCandidateRefV1(StrictModel):
    candidate_id: str = Field(pattern=r"^cand_[a-z0-9]+$")
    generated_from_draft_version: int = Field(ge=1)
    request_id: str = Field(min_length=1, max_length=128)
    created_at: str = Field(min_length=1, max_length=64)
    expires_at: str | None = Field(default=None, max_length=64)
    status: Literal["active", "superseded", "rejected", "expired", "accepted_source"] = (
        "active"
    )
    lineage: CandidateLineageV1 | None = None

    @field_validator("request_id")
    @classmethod
    def _request_id(cls, value: str) -> str:
        return _require_id(value, label="request_id")

    @model_validator(mode="after")
    def _lineage_request_binding(self) -> ThreatDraftCandidateRefV1:
        if (
            self.lineage is not None
            and self.lineage.revise_request_id != self.request_id
        ):
            raise ValueError("lineage.revise_request_id must equal request_id")
        return self


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
    threat_kind: str = Field(min_length=1, max_length=_MAX_SHORT)
    intended_roles: list[str] = Field(default_factory=list, max_length=_MAX_LIST)
    tags: list[str] = Field(default_factory=list, max_length=_MAX_LIST)
    generation_intent: GenerationIntentV1
    encounter_context: EncounterContextV1 = Field(default_factory=EncounterContextV1)
    graph_context_snapshot: GraphContextSnapshotV1
    # Candidate refs are workflow evidence (SBW03); authored concept fields stay separate.
    candidate_refs: list[ThreatDraftCandidateRefV1] = Field(
        default_factory=list, max_length=_MAX_LIST
    )
    accepted_mechanics_ref: AcceptedMechanicsRefV1 | None = None
    workflow_state: Literal["drafting", "candidate_ready", "mechanics_saved"] = (
        "drafting"
    )
    created_by: str = Field(min_length=1, max_length=_MAX_NAME)
    created_at: str
    updated_at: str

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    @field_validator("draft_id")
    @classmethod
    def _draft_id(cls, value: str) -> str:
        return require_draft_id(value)

    @field_validator("world_id", "campaign_id")
    @classmethod
    def _identity_ids(cls, value: str) -> str:
        return _require_id(value, label="identity id")

    @field_validator("intended_roles", "tags")
    @classmethod
    def _role_tag_items(cls, values: list[str]) -> list[str]:
        return _bounded_string_list(values, label="role or tag")

    @model_validator(mode="after")
    def _accepted_mechanics_workflow_invariant(self) -> ThreatDraftV1:
        has_ref = self.accepted_mechanics_ref is not None
        if has_ref and self.workflow_state != "mechanics_saved":
            raise ValueError(
                "accepted_mechanics_ref requires workflow_state=mechanics_saved"
            )
        if self.workflow_state == "mechanics_saved" and not has_ref:
            raise ValueError(
                "workflow_state=mechanics_saved requires accepted_mechanics_ref"
            )
        return self


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


class ThreatDraftIndexV1(StrictModel):
    schema_name: Literal["dmb_threat_draft_index_v1"] = Field(
        default=INDEX_SCHEMA, alias="schema"
    )
    draft_ids: list[str] = Field(default_factory=list)

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    @field_validator("draft_ids")
    @classmethod
    def _draft_ids(cls, values: list[str]) -> list[str]:
        cleaned = [require_draft_id(item) for item in values]
        if len(cleaned) != len(set(cleaned)):
            raise ValueError("duplicate draft_id in index")
        return cleaned


class CreateThreatDraftRequest(StrictModel):
    world_id: str
    campaign_id: str
    focus: FocusV1 | None = None
    name: str = Field(min_length=1, max_length=_MAX_NAME)
    slug_hint: str | None = Field(default=None, max_length=_MAX_NAME)
    description: str = Field(min_length=1, max_length=_MAX_TEXT)
    threat_kind: str = Field(min_length=1, max_length=_MAX_SHORT)
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

    @field_validator("intended_roles", "tags")
    @classmethod
    def _role_tag_items(cls, values: list[str]) -> list[str]:
        return _bounded_string_list(values, label="role or tag")


class UpdateThreatDraftRequest(StrictModel):
    expected_version: int = Field(ge=1)
    focus: FocusV1 | None = None
    name: str = Field(min_length=1, max_length=_MAX_NAME)
    slug_hint: str | None = Field(default=None, max_length=_MAX_NAME)
    description: str = Field(min_length=1, max_length=_MAX_TEXT)
    threat_kind: str = Field(min_length=1, max_length=_MAX_SHORT)
    intended_roles: list[str] = Field(default_factory=list, max_length=_MAX_LIST)
    tags: list[str] = Field(default_factory=list, max_length=_MAX_LIST)
    generation_intent: GenerationIntentV1
    encounter_context: EncounterContextV1 = Field(default_factory=EncounterContextV1)
    graph_context_snapshot: GraphContextSnapshotV1

    model_config = ConfigDict(extra="forbid")

    @field_validator("intended_roles", "tags")
    @classmethod
    def _role_tag_items(cls, values: list[str]) -> list[str]:
        return _bounded_string_list(values, label="role or tag")


class ThreatDraftListResponse(StrictModel):
    schema_name: Literal["dmb_threat_draft_list_v1"] = Field(
        default=LIST_SCHEMA, alias="schema"
    )
    drafts: list[ThreatDraftSummaryV1] = Field(default_factory=list, max_length=MAX_LIST_LIMIT)
    limit: int = Field(ge=1, le=MAX_LIST_LIMIT)
    offset: int = Field(ge=0)
    total: int = Field(ge=0)

    model_config = ConfigDict(extra="forbid", populate_by_name=True)
