"""Closed intent and metadata receipts for explicit encounter overrides."""
from datetime import datetime
from typing import Literal
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, model_validator
from .types import CombatEncounterRecord, SavedCombatMechanicsSnapshot
from application_state.world_mechanics.types import MechanicsLocator


class Closed(BaseModel):
    model_config = ConfigDict(extra='forbid', frozen=True)


class ActorAdoption(Closed):
    actor_id: str = Field(min_length=1)
    expected_snapshot_digest: str = Field(pattern=r'^sha256:[0-9a-f]{64}$')
    ac_policy: Literal['keep','use_saved'] = 'keep'
    hp_policy: Literal['keep','preserve_current','clamp_current','reset_full'] = 'keep'


class AdoptMechanicsRequest(Closed):
    schema_name: Literal['dmb_combat_mechanics_adoption_request_v1'] = Field(default='dmb_combat_mechanics_adoption_request_v1',alias='schema')
    operation_id: UUID
    expected_revision: int = Field(gt=0)
    draft_id: UUID
    locator: MechanicsLocator
    actors: list[ActorAdoption] = Field(min_length=1)

    @model_validator(mode='after')
    def unique_actors(self):
        if len({actor.actor_id for actor in self.actors})!=len(self.actors):
            raise ValueError('Choose each actor once')
        return self


class AdoptionTransition(Closed):
    actor_id: str
    before_snapshot_digest: str = Field(pattern=r'^sha256:[0-9a-f]{64}$')
    after_snapshot_digest: str = Field(pattern=r'^sha256:[0-9a-f]{64}$')
    ac_policy: Literal['keep','use_saved']
    hp_policy: Literal['keep','preserve_current','clamp_current','reset_full']
    before_ac: int | str | None
    after_ac: int | str | None
    before_hp: int | str | None
    after_hp: int | str | None
    before_max_hp: int | str | None
    after_max_hp: int | str | None


class AdoptionReceipt(Closed):
    schema_name: Literal['dmb_combat_mechanics_adoption_receipt_v1'] = Field(default='dmb_combat_mechanics_adoption_receipt_v1',alias='schema')
    operation_id: UUID
    world_id: str
    encounter_id: UUID
    request_digest: str = Field(pattern=r'^sha256:[0-9a-f]{64}$')
    state: Literal['applied','canceled']
    source: MechanicsLocator
    expected_revision: int
    committed_revision: int | None
    transitions: list[AdoptionTransition]
    created_at: datetime

    @model_validator(mode='after')
    def terminal(self):
        if len({t.actor_id for t in self.transitions})!=len(self.transitions):raise ValueError('Receipt repeats an actor')
        if self.state=='applied':
            if self.committed_revision!=self.expected_revision+1 or not self.transitions:
                raise ValueError('Applied receipt requires exact committed revision and transitions')
        elif self.committed_revision is not None or self.transitions:
            raise ValueError('Canceled receipt cannot claim actor changes')
        return self


class AdoptionOutcome(Closed):
    receipt: AdoptionReceipt
    encounter: CombatEncounterRecord
    advanced_since_apply: bool


class AdoptionPreview(Closed):
    snapshot: SavedCombatMechanicsSnapshot
    armor_class: int | None
    hit_points: int | None


class SavedMechanicsPreviewRequest(Closed):
    draft_id: UUID
    locator: MechanicsLocator
