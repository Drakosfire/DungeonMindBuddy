"""Small immutable ruleset catalog used to pin encounter semantics."""

from __future__ import annotations

import hashlib
import json
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class CombatRulesetField(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    key: Literal["initiative", "armor_class", "hit_points", "temp_hit_points", "conditions", "notes"]
    label: str = Field(min_length=1, max_length=80)
    enabled: bool = True


class CombatRulesetConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, populate_by_name=True)

    schema_: Literal["dmb_combat_ruleset_v1"] = Field(
        default="dmb_combat_ruleset_v1", alias="schema"
    )
    config_id: str = Field(min_length=1, max_length=96)
    system_id: str = Field(min_length=1, max_length=64)
    edition_id: str = Field(min_length=1, max_length=64)
    revision: str = Field(min_length=1, max_length=64)
    mode: Literal["manual_tracking"]
    fields: tuple[CombatRulesetField, ...]
    manual_defaults: dict[str, str | int | bool | None]


GENERIC_MANUAL_V1 = CombatRulesetConfig(
    config_id="generic.manual-tracking",
    system_id="generic",
    edition_id="manual",
    revision="1",
    mode="manual_tracking",
    fields=(
        CombatRulesetField(key="initiative", label="Initiative"),
        CombatRulesetField(key="armor_class", label="AC"),
        CombatRulesetField(key="hit_points", label="HP"),
        CombatRulesetField(key="temp_hit_points", label="Temp HP"),
        CombatRulesetField(key="conditions", label="Conditions"),
        CombatRulesetField(key="notes", label="Notes"),
    ),
    manual_defaults={"round": 1, "team": "enemy", "queue_model": "circular_barrel_v1"},
)

_CATALOG = {GENERIC_MANUAL_V1.config_id: GENERIC_MANUAL_V1}


def canonical_ruleset_payload(config: CombatRulesetConfig) -> dict:
    return config.model_dump(mode="json", by_alias=True)


def ruleset_digest(config: CombatRulesetConfig) -> str:
    canonical = json.dumps(
        canonical_ruleset_payload(config), sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def load_ruleset(config_id: str) -> CombatRulesetConfig:
    try:
        return _CATALOG[config_id]
    except KeyError as exc:
        raise ValueError(f"combat ruleset is not available: {config_id}") from exc
