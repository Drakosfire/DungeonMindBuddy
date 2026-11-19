"""Immutable, non-executable accounting for reviewed first-World effects."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Literal

BlockerCode = Literal[
    "prospective_alias_target_unsupported",
    "native_evidence_binding_required",
    "metadata_translation_required",
    "summary_disposition_required",
    "predicate_mapping_required",
    "unsupported_effect_field",
    "unsupported_graph_effect",
    "existing_identity_unsupported",
    "identity_effect_unsupported",
]


@dataclass(frozen=True, slots=True)
class EffectBlocker:
    code: BlockerCode
    field_path: str
    assertion_id: str | None = None
    candidate_ids: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class EffectFieldAccounting:
    field_path: str
    reviewed_json: str
    native_role: str
    assertion_id: str | None = None
    candidate_ids: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class AliasEffectAccounting:
    assertion_id: str
    candidate_ids: tuple[str, ...]
    owner_correlation_id: str
    reviewed_json: str
    classic_published_aliases: tuple[str, ...]
    evidence_ref_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class SummaryEffectAccounting:
    assertion_id: str
    reviewed_json: str
    classic_published_json: str = "null"
    native_disposition: Literal["unresolved"] = "unresolved"


@dataclass(frozen=True, slots=True)
class FirstWorldEffectInventory:
    reviewed_effect_json: str
    effect_sha256: str
    fields: tuple[EffectFieldAccounting, ...]
    aliases: tuple[AliasEffectAccounting, ...]
    summaries: tuple[SummaryEffectAccounting, ...]
    accepted_graph_effect_count: int

    @property
    def reviewed_effect(self) -> dict:
        """Fresh audit copy; mutation cannot change the sealed commitments."""
        return json.loads(self.reviewed_effect_json)


@dataclass(frozen=True, slots=True)
class UnsupportedFirstWorldEffects:
    inventory: FirstWorldEffectInventory
    blockers: tuple[EffectBlocker, ...]
    status: Literal["unsupported"] = "unsupported"


@dataclass(frozen=True, slots=True)
class NonPublishingDecisionPacket:
    inventory: FirstWorldEffectInventory
    status: Literal["non_publishing"] = "non_publishing"


FirstWorldEffectResult = UnsupportedFirstWorldEffects | NonPublishingDecisionPacket
