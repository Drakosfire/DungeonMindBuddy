from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

DraftMode = Literal[
    "generate_from_prompt",
    "generate_from_source_statblock",
    "revise_existing",
    "quick_reinforcement",
    "terrain_pressure",
    "render_existing",
]

LifecycleState = Literal[
    "description_requested",
    "description_drafted",
    "description_approved",
    "generation_requested",
    "live_draft",
    "needs_review",
    "reviewed",
    "stored_artifact",
    "promotion_previewed",
    "corpus_promoted",
    "indexed",
    "combat_ready",
]

ReviewStatus = Literal["needs_dm_review", "warnings", "failed", "approved", "rejected"]


class _PermissiveModel(BaseModel):
    model_config = ConfigDict(extra="allow")


class OutputOptions(_PermissiveModel):
    include_markdown: bool = True
    include_json: bool = True
    include_combat_defaults: bool = True
    include_review_warnings: bool = True
    persist: bool = False
    style: str | None = None


class SourceRef(_PermissiveModel):
    id: str | None = None
    kind: str | None = None
    label: str | None = None
    reason: str | None = None
    source_type: str | None = None
    source_id: str | None = None
    title: str | None = None
    uri: str | None = None
    path: str | None = None
    page: str | int | None = None
    excerpt: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class DraftIntent(_PermissiveModel):
    mode: DraftMode = "generate_from_prompt"
    prompt: str | None = None
    creature_name: str | None = None
    challenge_rating: str | None = None
    role: str | None = None
    tone: str | None = None
    instructions: str | None = None


class EncounterContext(_PermissiveModel):
    party_level: int | None = None
    party_size: int | None = None
    encounter_role: str | None = None
    environment: str | None = None
    constraints: list[str] = Field(default_factory=list)


class TerrainContext(_PermissiveModel):
    terrain_type: str | None = None
    hazards: list[str] = Field(default_factory=list)
    cover: str | None = None
    mobility_notes: str | None = None


class StatBlockDraftRequest(_PermissiveModel):
    request_id: str | None = None
    mode: DraftMode = "generate_from_prompt"
    intent: DraftIntent | None = None
    prompt: str | None = None
    encounter_context: EncounterContext | None = None
    terrain_context: TerrainContext | None = None
    source_refs: list[SourceRef] = Field(default_factory=list)
    source_statblock: dict[str, Any] | None = None
    existing_draft: dict[str, Any] | None = None
    revision_instructions: list[str] = Field(default_factory=list)
    output_options: OutputOptions = Field(default_factory=OutputOptions)


class StatBlockDraftRenderRequest(_PermissiveModel):
    request_id: str | None = None
    mode: DraftMode = "render_existing"
    statblock: dict[str, Any]
    output_options: OutputOptions = Field(default_factory=OutputOptions)
    source_refs: list[SourceRef] = Field(default_factory=list)


class CombatDefaults(_PermissiveModel):
    name: str | None = None
    armor_class: int | str | None = None
    hit_points: int | str | None = None
    initiative_bonus: int | None = None
    passive_perception: int | str | None = None
    speed_summary: str | None = None
    # Compatibility field for early Buddy code and hand-authored fixtures; prefer
    # ``speed_summary`` when hydrating combat UI from production v2 responses.
    speed: str | None = None
    senses_summary: str | None = None
    primary_actions: list[str] = Field(default_factory=list)
    suggested_tactics: list[str] = Field(default_factory=list)
    legendary_actions: int | None = None

    @property
    def effective_speed_summary(self) -> str | None:
        return self.speed_summary or self.speed


class ReviewWarning(_PermissiveModel):
    code: str | None = None
    message: str
    severity: str = "warning"
    path: str | None = None


class DraftProvenance(_PermissiveModel):
    request_id: str | None = None
    mode: DraftMode | str
    generator: str | None = None
    generated_at: str | None = None
    source_refs: list[SourceRef] = Field(default_factory=list)
    generation_info: dict[str, Any] = Field(default_factory=dict)
    persistence_request: dict[str, Any] | None = None


class StatBlockDraft(_PermissiveModel):
    draft_id: str
    lifecycle_state: LifecycleState = "live_draft"
    review_status: ReviewStatus = "needs_dm_review"
    markdown: str
    statblock: dict[str, Any] = Field(default_factory=dict)
    combat_defaults: CombatDefaults = Field(default_factory=CombatDefaults)
    warnings: list[ReviewWarning] = Field(default_factory=list)
    provenance: DraftProvenance


class ContractError(_PermissiveModel):
    code: str
    message: str
    details: dict[str, Any] | None = None


class StatBlockDraftResponse(_PermissiveModel):
    success: bool
    draft: StatBlockDraft | None = None
    error: ContractError | None = None
    timestamp: str | None = None

    @model_validator(mode="after")
    def validate_envelope_invariant(self) -> "StatBlockDraftResponse":
        if self.success and self.draft is None:
            raise ValueError("successful statblock draft response must include draft")
        if not self.success and self.error is None:
            raise ValueError("failed statblock draft response must include error")
        return self


class StatBlockGeneratorHealth(_PermissiveModel):
    ok: bool | None = None
    status: str | None = None
    service: str | None = None
    contract: str | None = None
    version: str | None = None
    generator_ready: bool | None = None
    openai_configured: bool | None = None
    supports: list[str] = Field(default_factory=list)
    timestamp: str | None = None
