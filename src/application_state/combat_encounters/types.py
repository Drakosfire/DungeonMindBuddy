"""Validated immutable-record and mutable-draft types for Combat encounters."""

from __future__ import annotations

import json
import re
from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from application_state.combat_encounters.rulesets import CombatRulesetConfig

_WORLD_ID = re.compile(r"^[a-z][a-z0-9_-]{0,62}$")
_MAX_DRAFT_BYTES = 700 * 1024


def _campaign_id_not_blank(value: str | None) -> str | None:
    if value is not None and not value.strip():
        raise ValueError("campaign_id must not be blank")
    return value


class CombatEntityProvenance(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    source: Literal["generated_statblock_view"]
    artifact_id: str = Field(min_length=1, max_length=256)
    draft_id: str | None = Field(default=None, max_length=256)
    corpus_display_path: str | None = Field(default=None, max_length=1024)
    corpus_file_fingerprint: str | None = Field(default=None, max_length=128)
    retrieval_status: str | None = Field(default=None, max_length=96)
    retrieval_verified_at: str | None = Field(default=None, max_length=96)
    added_at: str = Field(min_length=1, max_length=96)
    hydration_contract: Literal["combat_defaults"] = "combat_defaults"


class CombatEncounterProvenance(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    source: Literal["statblock_combat_add"]
    artifact_id: str = Field(min_length=1, max_length=256)
    added_entity_ids: list[str] = Field(min_length=1, max_length=20)
    added_at: str = Field(min_length=1, max_length=96)


class CombatEntity(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1, max_length=128)
    name: str = Field(min_length=1, max_length=160)
    team: Literal["pc", "ally", "enemy", "neutral"] = "enemy"
    order: int = Field(ge=1, le=1000)
    init: int | None = Field(default=None, ge=-999, le=999)
    ac: int | str | None = None
    hp: int | str | None = None
    max_hp: int | str | None = None
    temp_hp: int = Field(default=0, ge=0, le=999999)
    defeated: bool = False
    notes: str = Field(default="", max_length=4096)
    conditions: list[str] = Field(default_factory=list, max_length=32)
    tags: list[str] = Field(default_factory=list, max_length=32)
    statblock_path: str | None = Field(default=None, max_length=1024)
    statblock_artifact_id: str | None = Field(default=None, max_length=256)
    statblock_title: str | None = Field(default=None, max_length=256)
    corpus_fingerprint: str | None = Field(default=None, max_length=128)
    source: Literal["corpus", "generated_pending", "manual", "imported"] = "manual"
    provenance: list[CombatEntityProvenance] = Field(default_factory=list, max_length=16)

    @field_validator("id", "name", mode="before")
    @classmethod
    def _trim_identity(cls, value: object) -> object:
        if isinstance(value, str) and value != value.strip():
            raise ValueError("combatant identity fields must not have surrounding whitespace")
        return value

    @field_validator("conditions", "tags")
    @classmethod
    def _validate_labels(cls, values: list[str]) -> list[str]:
        if any(not item.strip() or len(item) > 80 for item in values):
            raise ValueError("combatant labels must be non-empty and at most 80 characters")
        if len(values) != len(set(values)):
            raise ValueError("combatant labels must be unique")
        return values

    @field_validator("ac", "hp", "max_hp", mode="before")
    @classmethod
    def _bound_manual_stat(cls, value: object) -> int | str | None:
        if isinstance(value, bool):
            raise ValueError("combat stats cannot be booleans")  # noqa: TRY004 - Pydantic field validation expects ValueError.
        if isinstance(value, str) and len(value) > 64:
            raise ValueError("manual combat stats must be at most 64 characters")
        if isinstance(value, int) and (value < -999999 or value > 999999):
            raise ValueError("combat stats must be within supported bounds")
        return value


class CombatGroup(BaseModel):
    model_config = ConfigDict(extra="forbid")

    group_key: str = Field(min_length=1, max_length=128)
    label: str = Field(min_length=1, max_length=160)
    statblock_path: str | None = Field(default=None, max_length=1024)
    member_ids: list[str] = Field(min_length=1, max_length=100)
    collapsed: bool = False


class CombatEncounterDraft(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    schema_: Literal["dmb_combat_encounter_draft_v1"] = Field(
        default="dmb_combat_encounter_draft_v1", alias="schema"
    )
    title: str = Field(min_length=1, max_length=160)
    round: int = Field(default=1, ge=1, le=9999)
    active_turn_entity_id: str | None = Field(default=None, max_length=128)
    round_start_entity_id: str | None = Field(default=None, max_length=128)
    queue_model: Literal["circular_barrel_v1"] = "circular_barrel_v1"
    entities: list[CombatEntity] = Field(default_factory=list, max_length=100)
    groups: list[CombatGroup] = Field(default_factory=list, max_length=100)
    provenance: list[CombatEncounterProvenance] = Field(default_factory=list, max_length=100)

    @field_validator("title")
    @classmethod
    def _trim_title(cls, value: str) -> str:
        if value != value.strip():
            raise ValueError("encounter title must not have surrounding whitespace")
        return value

    @model_validator(mode="after")
    def _references_resolve(self) -> CombatEncounterDraft:
        ids = [entity.id for entity in self.entities]
        if len(ids) != len(set(ids)):
            raise ValueError("combatant IDs must be unique")
        orders = [entity.order for entity in self.entities]
        if len(orders) != len(set(orders)):
            raise ValueError("combatant order values must be unique")
        id_set = set(ids)
        if self.active_turn_entity_id is not None and self.active_turn_entity_id not in id_set:
            raise ValueError("active turn must reference a combatant in this encounter")
        if self.round_start_entity_id is not None and self.round_start_entity_id not in id_set:
            raise ValueError("round start must reference a combatant in this encounter")
        seen_group_members: set[str] = set()
        group_keys = [group.group_key for group in self.groups]
        if len(group_keys) != len(set(group_keys)):
            raise ValueError("group keys must be unique")
        for group in self.groups:
            if len(group.member_ids) != len(set(group.member_ids)):
                raise ValueError("group members must be unique")
            if not set(group.member_ids).issubset(id_set):
                raise ValueError("group members must reference combatants in this encounter")
            if seen_group_members.intersection(group.member_ids):
                raise ValueError("a combatant cannot belong to more than one group")
            seen_group_members.update(group.member_ids)
        serialized = json.dumps(
            self.model_dump(mode="json", by_alias=True),
            ensure_ascii=False,
            separators=(",", ":"),
        ).encode("utf-8")
        if len(serialized) > _MAX_DRAFT_BYTES:
            raise ValueError("combat encounter draft exceeds the 700 KiB storage limit")
        return self


class CombatEncounterRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    encounter_id: UUID
    world_id: str = Field(min_length=1, max_length=63)
    campaign_id: str | None = Field(default=None, max_length=128)
    session: int | None = Field(default=None, ge=1, le=9999)
    revision: int = Field(ge=1)
    ruleset: CombatRulesetConfig
    ruleset_digest: str = Field(pattern=r"^[a-f0-9]{64}$")
    draft: CombatEncounterDraft
    created_at: datetime
    updated_at: datetime

    @field_validator("world_id")
    @classmethod
    def _canonical_world_id(cls, value: str) -> str:
        if not _WORLD_ID.fullmatch(value):
            raise ValueError("world_id must be a canonical managed World id")
        return value

    @field_validator("campaign_id")
    @classmethod
    def _nonblank_campaign_id(cls, value: str | None) -> str | None:
        return _campaign_id_not_blank(value)

    @model_validator(mode="after")
    def _scope_is_coherent(self) -> CombatEncounterRecord:
        if self.session is not None and self.campaign_id is None:
            raise ValueError("session metadata requires a campaign")
        return self


class CreateCombatEncounterRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(default="New encounter", min_length=1, max_length=160)
    campaign_id: str | None = Field(default=None, max_length=128)
    session: int | None = Field(default=None, ge=1, le=9999)
    ruleset_id: str = Field(default="generic.manual-tracking", min_length=1, max_length=96)

    @field_validator("campaign_id")
    @classmethod
    def _nonblank_campaign_id(cls, value: str | None) -> str | None:
        return _campaign_id_not_blank(value)

    @model_validator(mode="after")
    def _scope_is_coherent(self) -> CreateCombatEncounterRequest:
        if self.session is not None and self.campaign_id is None:
            raise ValueError("session metadata requires a campaign")
        return self


class SaveCombatEncounterRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    expected_revision: int = Field(ge=1)
    draft: CombatEncounterDraft


class AddGeneratedStatblockRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    expected_revision: int = Field(ge=1)
    team: Literal["pc", "ally", "enemy", "neutral"] = "enemy"
    count: int = Field(default=1, ge=1, le=20)
    name_override: str | None = Field(default=None, max_length=160)
    initiative: int | None = Field(default=None, ge=-999, le=999)
    insert_after_entity_id: str | None = Field(default=None, max_length=128)
    group_key: str | None = Field(default=None, max_length=128)
    notes: str | None = Field(default=None, max_length=4096)
    hp_override: int | None = Field(default=None, ge=0, le=999999)
    max_hp_override: int | None = Field(default=None, ge=0, le=999999)


class AddGeneratedStatblockResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    added_entities: list[CombatEntity]
    encounter: CombatEncounterRecord
