"""Pure validation and adjustments for immutable manual Combat profiles.

Legacy v1 DTOs and serializers deliberately do not import this module. The
versioned record owner composes these values with identity, source and turn
state rather than inferring mechanics from human field labels.
"""

from __future__ import annotations

import hashlib
import json
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

_LIMIT = 999999
_CANONICAL_PROFILE_BYTES = 32 * 1024
Identifier = Annotated[str, Field(strict=True, min_length=1, max_length=64, pattern=r"^[A-Za-z0-9][A-Za-z0-9_-]*$")]
Label = Annotated[str, Field(strict=True, min_length=1, max_length=80, pattern=r"\S")]
IntegerValue = Annotated[int, Field(strict=True, ge=-_LIMIT, le=_LIMIT)]
TextValue = Annotated[str, Field(strict=True, max_length=256)]
StatValue = IntegerValue | TextValue | None


class _Immutable(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, revalidate_instances="always")


class ResourceValue(_Immutable):
    current: IntegerValue | None = None
    minimum: IntegerValue | None = None
    maximum: IntegerValue | None = None

    @model_validator(mode="after")
    def coherent_bounds(self):
        if self.minimum is not None and self.maximum is not None and self.minimum > self.maximum:
            raise ValueError("resource minimum must not exceed maximum")
        # Current may remain outside newly edited bounds; validation never heals.
        return self


class StatDefinition(_Immutable):
    field_id: Identifier
    label: Label
    value_type: Literal["integer", "text"]
    initial: StatValue = None

    @model_validator(mode="after")
    def matching_default(self):
        _require_stat_type(self.value_type, self.initial)
        return self


class ResourceDefinition(_Immutable):
    field_id: Identifier
    label: Label
    initial: ResourceValue = Field(default_factory=ResourceValue)


class OrderedPacing(_Immutable):
    mode: Literal["ordered"] = "ordered"
    rounds: Annotated[bool, Field(strict=True)] = False


class SidePacing(_Immutable):
    mode: Literal["side"] = "side"
    rounds: Literal[False] = False

    @field_validator("rounds", mode="before")
    @classmethod
    def strict_rounds(cls, value):
        if type(value) is not bool:
            raise ValueError("side pacing requires a boolean round capability")
        return value


class ManualCombatProfile(_Immutable):
    model_config = ConfigDict(extra="forbid", frozen=True, populate_by_name=True, revalidate_instances="always")

    schema_: Literal["dmb_combat_profile_v2"] = Field(default="dmb_combat_profile_v2", alias="schema")
    profile_id: Identifier
    name: Annotated[str, Field(strict=True, min_length=1, max_length=160, pattern=r"\S")]
    system_id: Identifier
    revision: Annotated[int, Field(strict=True, ge=1, le=9999)] = 1
    stats: tuple[StatDefinition, ...] = Field(default=(), max_length=32)
    resources: tuple[ResourceDefinition, ...] = Field(default=(), max_length=16)
    pacing: Annotated[OrderedPacing | SidePacing, Field(discriminator="mode")] = Field(default_factory=OrderedPacing)

    @field_validator("pacing", mode="before")
    @classmethod
    def retain_ordered_input_default(cls, value):
        # Previously OrderedPacing accepted an omitted mode. Retained snapshots
        # are explicit, but existing creation callers must keep that default.
        if isinstance(value, dict) and "mode" not in value:
            return {"mode": "ordered", **value}
        return value

    @model_validator(mode="after")
    def bounded_unique_descriptors(self):
        ids = [field.field_id for field in (*self.stats, *self.resources)]
        if len(ids) != len(set(ids)):
            raise ValueError("profile descriptor IDs must be unique")
        if len(_canonical_bytes(self.model_dump(mode="json", by_alias=True))) > _CANONICAL_PROFILE_BYTES:
            raise ValueError("manual profile exceeds the 32 KiB canonical limit")
        return self


class ManualActorValues(BaseModel):
    model_config = ConfigDict(extra="forbid", revalidate_instances="always")

    stats: dict[Identifier, StatValue] = Field(default_factory=dict, max_length=32)
    resources: dict[Identifier, ResourceValue] = Field(default_factory=dict, max_length=16)


def _require_stat_type(value_type: Literal["integer", "text"], value: StatValue) -> None:
    if value is None:
        return
    expected = int if value_type == "integer" else str
    if type(value) is not expected:
        raise ValueError(f"manual stat requires {value_type} or explicit null")


def _canonical_bytes(payload: dict) -> bytes:
    return json.dumps(payload, sort_keys=True, ensure_ascii=False, allow_nan=False, separators=(",", ":")).encode("utf-8")


def canonical_manual_profile(profile: ManualCombatProfile) -> dict:
    validated = ManualCombatProfile.model_validate(profile)
    return validated.model_dump(mode="json", by_alias=True)


def manual_profile_digest(profile: ManualCombatProfile) -> str:
    """Unprefixed SHA-256, matching the existing ruleset digest storage format."""
    return hashlib.sha256(_canonical_bytes(canonical_manual_profile(profile))).hexdigest()


def validate_actor_values(profile: ManualCombatProfile, values: ManualActorValues | dict) -> ManualActorValues:
    profile = ManualCombatProfile.model_validate(profile)
    validated = ManualActorValues.model_validate(values)
    if set(validated.stats) != {field.field_id for field in profile.stats}:
        raise ValueError("actor stat IDs must exactly match its pinned profile")
    if set(validated.resources) != {field.field_id for field in profile.resources}:
        raise ValueError("actor resource IDs must exactly match its pinned profile")
    for field in profile.stats:
        _require_stat_type(field.value_type, validated.stats[field.field_id])
    return validated


def initial_actor_values(profile: ManualCombatProfile) -> ManualActorValues:
    profile = ManualCombatProfile.model_validate(profile)
    return validate_actor_values(profile, {
        "stats": {field.field_id: field.initial for field in profile.stats},
        "resources": {field.field_id: field.initial.model_dump(mode="python") for field in profile.resources},
    })


def adjust_resource(value: ResourceValue, direction: Literal["increase", "decrease"], amount: int) -> ResourceValue:
    """Adjust one resource without implicit participation or source side effects."""
    value = ResourceValue.model_validate(value)
    if direction not in ("increase", "decrease"):
        raise ValueError("unknown resource adjustment direction")
    if type(amount) is not int or not 1 <= amount <= _LIMIT:
        raise ValueError("adjustment amount must be a positive supported integer")
    if value.current is None:
        raise ValueError("set a current value before adjusting this resource")
    if direction == "increase":
        if value.maximum is not None and value.current >= value.maximum:
            return value
        result = value.current + amount
        if value.maximum is not None:
            result = min(result, value.maximum)
    else:
        if value.minimum is not None and value.current <= value.minimum:
            return value
        result = value.current - amount
        if value.minimum is not None:
            result = max(result, value.minimum)
    if not -_LIMIT <= result <= _LIMIT:
        raise ValueError("resource adjustment exceeds the supported numeric range")
    return ResourceValue(current=result, minimum=value.minimum, maximum=value.maximum)
