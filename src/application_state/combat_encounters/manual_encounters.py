"""Versioned system-neutral encounter records and creation/Save intents.

Source access is reference-only: named tracker values never hydrate from an
exact statblock. Existing v1 models remain their own serialization authority.
"""

from __future__ import annotations

import json
from copy import deepcopy
from typing import Annotated, Literal
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, field_validator, model_validator

from application_state.combat_encounters.manual_profiles import (
    ManualActorValues,
    ManualCombatProfile,
    manual_profile_digest,
    validate_actor_values,
)
from application_state.combat_encounters.types import (
    AcceptedCombatMechanicsSnapshot,
    CombatEncounterRecord,
    CombatMechanicsSnapshot,
    CombatWorldIdentity,
    ConversationVariantCombatSnapshot,
    CreateCombatEncounterRequest,
    SaveCombatEncounterRequest,
    SavedCombatMechanicsSnapshot,
)

Identity = Annotated[str, Field(strict=True, min_length=1, max_length=128, pattern=r"^\S+$")]
Name = Annotated[str, Field(strict=True, min_length=1, max_length=160, pattern=r"\S")]
Status = Annotated[str, Field(strict=True, min_length=1, max_length=80, pattern=r"\S")]
SourceSnapshot = CombatMechanicsSnapshot | AcceptedCombatMechanicsSnapshot | SavedCombatMechanicsSnapshot | ConversationVariantCombatSnapshot


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True, revalidate_instances="always")


class ManualParticipant(_Model):
    id: Identity
    name: Name
    side_id: Identity | None = None
    participation: Literal["in_action", "out_of_action"] = "in_action"
    values: ManualActorValues
    notes: Annotated[str, Field(strict=True, max_length=4096)] = ""
    statuses: tuple[Status, ...] = Field(default=(), max_length=32)
    tags: tuple[Status, ...] = Field(default=(), max_length=32)
    world_identity: CombatWorldIdentity | None = None
    mechanics_snapshot: SourceSnapshot | None = None

    @field_validator("world_identity", "mechanics_snapshot", mode="before")
    @classmethod
    def revalidate_reference_models(cls, value):
        # Imported v1 source DTOs do not revalidate instances by default. Their
        # nested resource dictionaries must still pass the exact proof on entry.
        return value.model_dump(mode="json") if isinstance(value, BaseModel) else deepcopy(value)

    @model_validator(mode="after")
    def coherent_identity(self):
        if self.name != self.name.strip():
            raise ValueError("participant name must not have surrounding whitespace")
        if len(set(self.statuses)) != len(self.statuses) or len(set(self.tags)) != len(self.tags):
            raise ValueError("participant statuses and tags must be unique")
        if isinstance(self.mechanics_snapshot, CombatMechanicsSnapshot) and self.world_identity != self.mechanics_snapshot.target:
            raise ValueError("associated source requires its exact World identity")
        if isinstance(self.mechanics_snapshot, ConversationVariantCombatSnapshot) and self.world_identity is not None:
            raise ValueError("conversation variant cannot claim a World creature identity")
        return self


class ManualGroup(_Model):
    id: Identity
    label: Name
    member_ids: tuple[Identity, ...] = Field(min_length=1, max_length=100)
    collapsed: Annotated[bool, Field(strict=True)] = False


class ManualSide(_Model):
    id: Identity
    label: Name


class OrderedTurn(_Model):
    kind: Literal["ordered"] = "ordered"
    active_actor_id: Identity | None = None


class OrderedRoundTurn(_Model):
    kind: Literal["ordered_rounds"] = "ordered_rounds"
    active_actor_id: Identity | None = None
    round: Annotated[int, Field(strict=True, ge=1, le=9999)] = 1
    round_start_actor_id: Identity | None = None


class SideTurn(_Model):
    kind: Literal["side"] = "side"
    active_side_id: Identity | None = None
    active_actor_id: Identity | None = None
    acted_actor_ids: tuple[Identity, ...] = Field(default=(), max_length=100)


class ManualEncounterDraft(_Model):
    schema_: Literal["dmb_combat_encounter_draft_v2"] = Field(default="dmb_combat_encounter_draft_v2", alias="schema")
    title: Name
    entities: list[ManualParticipant] = Field(default_factory=list, max_length=100)
    groups: list[ManualGroup] = Field(default_factory=list, max_length=100)
    sides: list[ManualSide] = Field(default_factory=list, max_length=32)
    turn: Annotated[OrderedTurn | OrderedRoundTurn | SideTurn, Field(discriminator="kind")] = Field(default_factory=OrderedTurn)

    @model_validator(mode="after")
    def coherent_references(self):
        if self.title != self.title.strip():
            raise ValueError("encounter title must not have surrounding whitespace")
        actors = {actor.id: actor for actor in self.entities}
        if len(actors) != len(self.entities):
            raise ValueError("participant IDs must be unique")
        side_ids = {side.id for side in self.sides}
        if len(side_ids) != len(self.sides):
            raise ValueError("side IDs must be unique")
        if any(actor.side_id is not None and actor.side_id not in side_ids for actor in self.entities):
            raise ValueError("participant side must reference this encounter")
        if len({group.id for group in self.groups}) != len(self.groups):
            raise ValueError("group IDs must be unique")
        grouped: set[str] = set()
        for group in self.groups:
            members = set(group.member_ids)
            if len(members) != len(group.member_ids) or not members.issubset(actors):
                raise ValueError("group members must uniquely reference this encounter")
            if grouped.intersection(members):
                raise ValueError("a participant cannot belong to more than one group")
            grouped.update(members)
        active = self.turn.active_actor_id
        if active is not None and (active not in actors or actors[active].participation != "in_action"):
            raise ValueError("active turn must reference an in-action participant")
        if isinstance(self.turn, SideTurn):
            side = self.turn.active_side_id
            acted = self.turn.acted_actor_ids
            if side is None:
                if active is not None or acted:
                    raise ValueError("unstarted side turn cannot retain actor references")
            elif side not in side_ids:
                raise ValueError("active side must reference this encounter")
            if active is not None and actors[active].side_id != side:
                raise ValueError("active actor must belong to the active side")
            if len(set(acted)) != len(acted) or any(actor not in actors or actors[actor].side_id != side for actor in acted):
                raise ValueError("acted markers must uniquely reference actors on the active side")
            if active in acted:
                raise ValueError("active actor cannot also have a finished turn marker")
        if isinstance(self.turn, OrderedRoundTurn):
            anchor = self.turn.round_start_actor_id
            if active is not None and anchor is None:
                raise ValueError("an active round requires an explicit anchor")
            if anchor is not None and anchor not in actors:
                raise ValueError("round anchor must reference this encounter")
        body = json.dumps(self.model_dump(mode="json", by_alias=True), ensure_ascii=False, allow_nan=False, separators=(",", ":")).encode("utf-8")
        if len(body) > 700 * 1024:
            raise ValueError("manual draft exceeds the 700 KiB canonical limit")
        return self


class ManualEncounterRecord(_Model):
    model_config = ConfigDict(extra="forbid", frozen=True, populate_by_name=True, revalidate_instances="always")

    encounter_id: UUID
    world_id: Annotated[str, Field(strict=True, pattern=r"^[a-z][a-z0-9_-]{0,62}$")]
    campaign_id: Annotated[str, Field(strict=True, min_length=1, max_length=128, pattern=r"\S")] | None = None
    session: Annotated[int, Field(strict=True, ge=1, le=9999)] | None = None
    revision: Annotated[int, Field(strict=True, ge=1)]
    ruleset: ManualCombatProfile
    ruleset_digest: Annotated[str, Field(strict=True, pattern=r"^[a-f0-9]{64}$")]
    draft: ManualEncounterDraft
    created_at: AwareDatetime
    updated_at: AwareDatetime

    @model_validator(mode="after")
    def coherent_profile_and_world(self):
        if self.session is not None and self.campaign_id is None:
            raise ValueError("session metadata requires a campaign")
        if self.ruleset_digest != manual_profile_digest(self.ruleset):
            raise ValueError("manual profile digest differs from its pinned snapshot")
        if (self.ruleset.pacing.mode == "side") != isinstance(self.draft.turn, SideTurn):
            raise ValueError("turn state must match the profile's pacing mode")
        if self.ruleset.pacing.rounds != isinstance(self.draft.turn, OrderedRoundTurn):
            raise ValueError("turn state must match the profile's round capability")
        for actor in self.draft.entities:
            validate_actor_values(self.ruleset, actor.values)
            identity = actor.world_identity
            if identity is not None and identity.managed_world_id != self.world_id:
                raise ValueError("participant World identity belongs to another World")
            snapshot = actor.mechanics_snapshot
            if snapshot is not None:
                source_world = snapshot.target.managed_world_id if isinstance(snapshot, CombatMechanicsSnapshot) else snapshot.managed_world_id
                if source_world != self.world_id:
                    raise ValueError("exact source snapshot belongs to another World")
        return self


def empty_manual_draft(profile: ManualCombatProfile, title: str) -> ManualEncounterDraft:
    profile = ManualCombatProfile.model_validate(profile)
    turn = SideTurn() if profile.pacing.mode == "side" else OrderedRoundTurn() if profile.pacing.rounds else OrderedTurn()
    return ManualEncounterDraft(title=title, turn=turn)


def _explicit_schema(payload: object) -> str:
    if not isinstance(payload, dict):
        raise ValueError("record version requires an object")
    keys = [key for key in ("schema", "schema_") if key in payload]
    if len(keys) != 1 or not isinstance(payload[keys[0]], str):
        raise ValueError("record version requires exactly one explicit schema identifier")
    return payload[keys[0]]


def decode_combat_record(payload: dict) -> CombatEncounterRecord | ManualEncounterRecord:
    """Validate an explicit version pair without normalizing its legacy preimage."""
    if not isinstance(payload, dict):
        raise ValueError("combat record must be an object")
    version = (_explicit_schema(payload.get("ruleset")), _explicit_schema(payload.get("draft")))
    if version == ("dmb_combat_ruleset_v1", "dmb_combat_encounter_draft_v1"):
        return CombatEncounterRecord.model_validate(payload)
    if version == ("dmb_combat_profile_v2", "dmb_combat_encounter_draft_v2"):
        return ManualEncounterRecord.model_validate(payload)
    raise ValueError("unsupported or mixed combat record versions")


class CreateManualEncounterRequest(_Model):
    schema_version: Literal["dmb_manual_combat_create_v2"] = "dmb_manual_combat_create_v2"
    title: Name = "New manual encounter"
    profile: ManualCombatProfile
    campaign_id: Annotated[str, Field(strict=True, min_length=1, max_length=128, pattern=r"\S")] | None = None
    session: Annotated[int, Field(strict=True, ge=1, le=9999)] | None = None

    @model_validator(mode="after")
    def coherent_creation(self):
        empty_manual_draft(self.profile, self.title)
        if self.session is not None and self.campaign_id is None:
            raise ValueError("session metadata requires a campaign")
        return self


class SaveManualEncounterRequest(_Model):
    expected_revision: Annotated[int, Field(strict=True, ge=1)]
    draft: ManualEncounterDraft


AnyCombatRecord = CombatEncounterRecord | ManualEncounterRecord
AnyCreateEncounterRequest = CreateCombatEncounterRequest | CreateManualEncounterRequest
AnySaveEncounterRequest = SaveCombatEncounterRequest | SaveManualEncounterRequest
