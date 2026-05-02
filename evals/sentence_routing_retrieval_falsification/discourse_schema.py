"""``sentence_discourse_state_v1`` — Stage B1 discourse/local-state classification (per sentence unit).

Stage B1 does **not** emit assigned hubs; see :mod:`discourse_reducer` for deterministic hub routing.
"""

from __future__ import annotations

import re
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from evals.sentence_routing_retrieval_falsification.route_schema import THE_PARTY_ROUTE_SENTINEL

SCHEMA_SENTENCE_DISCOURSE_STATE_V1 = "sentence_discourse_state_v1"

_SLUG_RE = re.compile(r"^[a-z0-9_]+$")

DISCOURSE_MODE_VALUES = (
    "true_empty",
    "explicit_pc",
    "explicit_party",
    "implicit_party",
    "previous_unit_pc_continuation",
    "scene_owner_pc",
    "topic_pc",
    "perceiver_pc",
    "placeholder_only",
)
DISCOURSE_MODE_ENUM: tuple[str, ...] = tuple(sorted(DISCOURSE_MODE_VALUES))

COLLECTIVE_ACTOR_VALUES = frozenset({THE_PARTY_ROUTE_SENTINEL})

# Placeholder / bookkeeping buckets that may appear when no hub assignment fits.
_MISSING_ENTITY_VALUES = frozenset(
    {
        "npc_placeholder",
        "location_placeholder",
        "event_or_object_placeholder",
        "new_hub_candidate",
        "true_empty",
    }
)


def _unique_slug_list(values: Any, *, label: str) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    if not isinstance(values, list):
        return out
    for x in values:
        s = str(x).strip()
        if not s:
            continue
        if not _SLUG_RE.match(s):
            raise ValueError(f"{label}: invalid slug shape {s!r}")
        if s not in seen:
            seen.add(s)
            out.append(s)
    return out


class DiscourseRow(BaseModel):
    """Structured discourse classification for one sentence unit (no hub assignments)."""

    unit_id: str
    discourse_mode: str
    direct_pc_slugs: list[str] = Field(default_factory=list)
    topic_pc_slugs: list[str] = Field(default_factory=list)
    scene_owner_pc_slugs: list[str] = Field(default_factory=list)
    perceiver_pc_slugs: list[str] = Field(default_factory=list)
    collective_actor: str | None = None
    party_expansion_allowed: bool = False
    narrow_pc_only: bool = False
    continuation_from_unit_id: str | None = None
    missing_entity_bucket: str | None = None
    rationale: str = ""

    @field_validator("unit_id")
    @classmethod
    def unit_id_nonempty(cls, v: str) -> str:
        s = str(v).strip()
        if not s:
            raise ValueError("unit_id must be non-empty")
        return s

    @field_validator("discourse_mode")
    @classmethod
    def discourse_mode_ok(cls, v: str) -> str:
        s = str(v).strip()
        if s not in DISCOURSE_MODE_VALUES:
            raise ValueError(
                f"discourse_mode must be one of {sorted(DISCOURSE_MODE_VALUES)}; got {v!r}"
            )
        return s

    @field_validator(
        "direct_pc_slugs",
        "topic_pc_slugs",
        "scene_owner_pc_slugs",
        "perceiver_pc_slugs",
        mode="before",
    )
    @classmethod
    def slug_lists(cls, v: Any) -> list[str]:
        return _unique_slug_list(v, label="slug_list")

    @field_validator("collective_actor")
    @classmethod
    def collective_ok(cls, v: str | None) -> str | None:
        if v is None:
            return None
        s = str(v).strip()
        if not s:
            return None
        if s not in COLLECTIVE_ACTOR_VALUES:
            raise ValueError(
                f"collective_actor must be null or one of {sorted(COLLECTIVE_ACTOR_VALUES)}; got {v!r}"
            )
        return s

    @field_validator("continuation_from_unit_id")
    @classmethod
    def continuation_ok(cls, v: str | None) -> str | None:
        if v is None:
            return None
        s = str(v).strip()
        return s or None

    @field_validator("missing_entity_bucket")
    @classmethod
    def missing_bucket_ok(cls, v: str | None) -> str | None:
        if v is None:
            return None
        s = str(v).strip()
        if not s:
            return None
        if s not in _MISSING_ENTITY_VALUES:
            raise ValueError(
                f"missing_entity_bucket must be one of {sorted(_MISSING_ENTITY_VALUES)} or null; got {v!r}"
            )
        return s

    @model_validator(mode="after")
    def rationale_when_non_true_empty(self) -> DiscourseRow:
        if self.discourse_mode == "true_empty":
            return self
        if not str(self.rationale or "").strip():
            raise ValueError("rationale must be non-empty unless discourse_mode is true_empty")
        return self


class DiscourseEnvelope(BaseModel):
    """Wire JSON uses key ``schema`` (alias)."""

    model_config = ConfigDict(populate_by_name=True)

    envelope_schema: str = Field(alias="schema")
    discourse: list[DiscourseRow]

    @field_validator("envelope_schema")
    @classmethod
    def schema_ok(cls, v: str) -> str:
        if str(v) != SCHEMA_SENTENCE_DISCOURSE_STATE_V1:
            raise ValueError(f"schema must be {SCHEMA_SENTENCE_DISCOURSE_STATE_V1!r}")
        return str(v)


def parse_discourse_envelope(payload: dict[str, Any]) -> DiscourseEnvelope:
    """Validate Stage B1 payload; raises ``pydantic.ValidationError`` on failure."""
    return DiscourseEnvelope.model_validate(payload)


def discourse_openai_json_schema(*, allowed_pc_slugs: list[str]) -> dict[str, Any]:
    """Strict Chat Completions JSON schema for ``sentence_discourse_state_v1``."""
    mode_enum = sorted(DISCOURSE_MODE_VALUES)
    missing_enum = sorted(_MISSING_ENTITY_VALUES)
    slug_items: dict[str, Any]
    if allowed_pc_slugs:
        slug_items = {"type": "string", "enum": sorted(set(allowed_pc_slugs))}
    else:
        slug_items = {"type": "string", "pattern": "^[a-z0-9_]+$"}

    row_properties: dict[str, Any] = {
        "unit_id": {"type": "string"},
        "discourse_mode": {"type": "string", "enum": mode_enum},
        "direct_pc_slugs": {"type": "array", "items": slug_items},
        "topic_pc_slugs": {"type": "array", "items": slug_items},
        "scene_owner_pc_slugs": {"type": "array", "items": slug_items},
        "perceiver_pc_slugs": {"type": "array", "items": slug_items},
        "collective_actor": {
            "anyOf": [{"type": "null"}, {"type": "string", "enum": [THE_PARTY_ROUTE_SENTINEL]}],
        },
        "party_expansion_allowed": {"type": "boolean"},
        "narrow_pc_only": {"type": "boolean"},
        "continuation_from_unit_id": {"anyOf": [{"type": "null"}, {"type": "string"}]},
        "missing_entity_bucket": {
            "anyOf": [{"type": "null"}, {"type": "string", "enum": missing_enum}],
        },
        "rationale": {"type": "string"},
    }
    required_row = list(row_properties.keys())

    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["schema", "discourse"],
        "properties": {
            "schema": {"type": "string", "enum": [SCHEMA_SENTENCE_DISCOURSE_STATE_V1]},
            "discourse": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": required_row,
                    "properties": row_properties,
                },
            },
        },
    }
