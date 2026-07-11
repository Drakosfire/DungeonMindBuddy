"""v0 identity resolution collision policy (PR004)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class IdentityResolutionPolicy(BaseModel):
    """Deterministic v0 policy — no fuzzy matching, confidence is not authority."""

    model_config = ConfigDict(extra="forbid", strict=True)

    exact_label_match_kinds: bool = True
    alias_match_kinds: bool = True
    block_cross_kind_alias_collision: bool = True
    allow_provisional_new: bool = True
    require_evidence_for_created_new: bool = True


DEFAULT_IDENTITY_RESOLUTION_POLICY = IdentityResolutionPolicy()
