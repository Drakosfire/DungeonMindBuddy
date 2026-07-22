"""Transport-envelope models for DungeonMind statblock v1 responses."""
from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field

# Published v1 identity (DungeonMindServer statblocks_v1).
ContractNameV1 = Literal["dungeonmind.dungeonbuddy-statblocks"]
ContractVersionV1 = Literal["1.0.0"]

_STATBLOCK_ID_PATTERN = r"^sb_[a-z0-9]+$"
_REVISION_ID_PATTERN = r"^rev_[a-z0-9]+$"
_DEFINITION_DIGEST_PATTERN = r"^sha256:[0-9a-f]{64}$"


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ErrorDetailV1(StrictModel):
    code: str
    message: str
    details: dict[str, Any] | None = None


class ErrorEnvelopeV1(StrictModel):
    error: ErrorDetailV1


class HealthResponseV1(StrictModel):
    status: str
    contract: ContractNameV1
    contract_version: ContractVersionV1
    capabilities: list[str] = Field(default_factory=list)


class ReadinessResponseV1(StrictModel):
    status: str
    contract: ContractNameV1
    generation_enabled: bool = False
    read_routes_enabled: bool = False
    errors: list[str] = Field(default_factory=list)
    detail: str | None = None


class ExactRevisionResourceV1(StrictModel):
    """Minimal exact-revision identity fields required by SBW01 proofs."""

    model_config = ConfigDict(extra="allow")

    statblock_id: str = Field(pattern=_STATBLOCK_ID_PATTERN)
    revision_id: str = Field(pattern=_REVISION_ID_PATTERN)
    definition_digest: str = Field(pattern=_DEFINITION_DIGEST_PATTERN)
    contract: ContractNameV1
    contract_version: ContractVersionV1
    definition: dict[str, Any] | None = None


_CANDIDATE_ID_PATTERN = r"^cand_[a-z0-9]+$"


class ExactRevisionLocatorV1(StrictModel):
    statblock_id: str = Field(pattern=_STATBLOCK_ID_PATTERN)
    revision_id: str = Field(pattern=_REVISION_ID_PATTERN)


class AssetVariantV1(StrictModel):
    name: str = Field(min_length=1, max_length=128)
    url: str = Field(min_length=1, max_length=2048)


class AssetRefV1(StrictModel):
    asset_id: str = Field(min_length=1, max_length=128)
    provider_kind: Literal["cloudflare_images", "cloudflare_r2", "image_pipeline"]
    url: str = Field(min_length=1, max_length=2048)
    mime_type: str = Field(min_length=1, max_length=128)
    alt_text: str | None = Field(default=None, max_length=512)
    width: int | None = Field(default=None, ge=1)
    height: int | None = Field(default=None, ge=1)
    prompt: str | None = Field(default=None, max_length=4096)
    generation_provenance: str | None = Field(default=None, max_length=512)
    variants: list[AssetVariantV1] = Field(default_factory=list)
    created_at: datetime


class AssetBriefV1(StrictModel):
    prompt: str = Field(min_length=1, max_length=4096)
    recommended_roles: list[
        Literal["portrait", "token", "full_body", "encounter_art", "alternate"]
    ] = Field(default_factory=list)


class AssetWarningV1(StrictModel):
    code: Literal["asset_generator_unconfigured", "asset_generation_failed"]
    message: str = Field(min_length=1, max_length=1024)


class CandidateGenerationReceiptV1(StrictModel):
    request_id: str = Field(min_length=1, max_length=128)
    provider: str = Field(min_length=1, max_length=128)
    model: str = Field(min_length=1, max_length=128)
    prompt_version: str = Field(min_length=1, max_length=128)
    schema_version: str = Field(min_length=1, max_length=128)
    schema_fingerprint: str = Field(min_length=1, max_length=128)
    generated_at: datetime
    caller_scope: str = Field(min_length=1, max_length=128)
    actor: str | None = Field(default=None, max_length=128)
    source_description_digest: str | None = None
    source_definition_digest: str | None = None
    source_locator: ExactRevisionLocatorV1 | None = None
    provider_request_id: str | None = Field(default=None, max_length=256)
    provider_response_id: str | None = Field(default=None, max_length=256)
    latency_ms: int | None = Field(default=None, ge=0)
    input_tokens: int | None = Field(default=None, ge=0)
    output_tokens: int | None = Field(default=None, ge=0)


class ValidationIssueV1(StrictModel):
    code: str = Field(min_length=1, max_length=128)
    severity: Literal["info", "warning", "error"]
    field_path: str = Field(min_length=1, max_length=512)
    message: str = Field(min_length=1, max_length=1024)
    suggested_resolution: str | None = Field(default=None, max_length=1024)


class CandidateValidationReceiptV1(StrictModel):
    status: Literal["valid", "warnings", "invalid"]
    mode: Literal["generation_candidate", "editor_preview", "persistence"]
    validator_version: str = Field(min_length=1, max_length=128)
    canonicalizer_version: str = Field(min_length=1, max_length=128)
    definition_digest: str = Field(pattern=_DEFINITION_DIGEST_PATTERN)
    validated_at: datetime
    issues: list[ValidationIssueV1] = Field(default_factory=list)


class DistanceV1(StrictModel):
    value: int = Field(ge=0)
    unit: Literal["feet"] = "feet"


class DiceExpressionV1(StrictModel):
    count: int = Field(ge=0)
    die: int = Field(ge=1)
    modifier: int = 0


class RulesetRefContractV1(StrictModel):
    system: Literal["dnd5e"]
    edition: Literal["2014", "2024"]
    house_ruleset_id: str | None = Field(default=None, max_length=128)


class CreatureIdentityV1(StrictModel):
    name: str = Field(min_length=1, max_length=256)
    size: str = Field(min_length=1, max_length=64)
    creature_type: str = Field(min_length=1, max_length=64)
    subtypes: list[str] = Field(default_factory=list)
    alignment: str | None = Field(default=None, max_length=64)


class ArmorClassProfileV1(StrictModel):
    key: str = Field(min_length=1, max_length=64)
    value: int
    label: str | None = Field(default=None, max_length=128)
    condition: str | None = Field(default=None, max_length=256)
    default: bool = False


class DamageInteractionV1(StrictModel):
    key: str = Field(min_length=1, max_length=64)
    kind: Literal["vulnerability", "resistance", "immunity"]
    damage_types: list[str]
    qualifiers: list[str] = Field(default_factory=list)
    bypasses: list[str] = Field(default_factory=list)


class DefenseProfileV1(StrictModel):
    armor_classes: list[ArmorClassProfileV1]
    damage_interactions: list[DamageInteractionV1] = Field(default_factory=list)
    condition_immunities: list[str] = Field(default_factory=list)


class HitPointProfileV1(StrictModel):
    method: Literal["formula", "fixed"]
    formula: DiceExpressionV1 | None = None
    fixed_value: int | None = None
    displayed_average: int | None = None


class VitalityProfileV1(StrictModel):
    hit_points: HitPointProfileV1


class MovementModeV1(StrictModel):
    key: str = Field(min_length=1, max_length=64)
    mode: Literal["walk", "fly", "swim", "climb", "burrow", "hover", "special"]
    distance: DistanceV1
    qualifiers: list[str] = Field(default_factory=list)


class MovementProfileV1(StrictModel):
    modes: list[MovementModeV1]


class AbilityScoresV1(StrictModel):
    strength: int
    dexterity: int
    constitution: int
    intelligence: int
    wisdom: int
    charisma: int


class SavingThrowBonusV1(StrictModel):
    ability: Literal[
        "strength", "dexterity", "constitution", "intelligence", "wisdom", "charisma"
    ]
    value: int
    derivation: Literal["standard", "expertise", "explicit_override"]
    note: str | None = Field(default=None, max_length=256)


class SkillBonusV1(StrictModel):
    skill: str = Field(min_length=1, max_length=64)
    ability: Literal[
        "strength", "dexterity", "constitution", "intelligence", "wisdom", "charisma"
    ]
    value: int
    derivation: Literal["standard", "expertise", "explicit_override"]
    note: str | None = Field(default=None, max_length=256)


class ProficiencyProfileV1(StrictModel):
    saving_throws: list[SavingThrowBonusV1] = Field(default_factory=list)
    skills: list[SkillBonusV1] = Field(default_factory=list)


class SenseV1(StrictModel):
    kind: Literal["darkvision", "blindsight", "tremorsense", "truesight", "special"]
    range: DistanceV1
    qualifiers: list[str] = Field(default_factory=list)


class SenseProfileV1(StrictModel):
    senses: list[SenseV1] = Field(default_factory=list)
    passive_perception: int


class CommunicationProfileV1(StrictModel):
    languages: list[str] = Field(default_factory=list)
    telepathy_range: DistanceV1 | None = None
    special_modes: list[str] = Field(default_factory=list)


class ChallengeProfileV1(StrictModel):
    rating: str = Field(min_length=1, max_length=32)
    proficiency_bonus: int
    xp_override: int | None = None


class ResourcePoolV1(StrictModel):
    key: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=128)
    maximum: int = Field(ge=0)
    refresh: str = Field(min_length=1, max_length=128)
    rules_text: str | None = Field(default=None, max_length=2048)


class TriggerV1(StrictModel):
    kind: str = Field(min_length=1, max_length=64)
    source_element_key: str | None = Field(default=None, max_length=64)
    condition_text: str | None = Field(default=None, max_length=512)


class ActivationV1(StrictModel):
    kind: Literal[
        "passive",
        "action",
        "bonus_action",
        "reaction",
        "triggered",
        "legendary",
        "lair_initiative",
        "special",
    ]
    trigger: TriggerV1 | None = None
    timing_text: str | None = Field(default=None, max_length=256)


class RechargeRangeV1(StrictModel):
    minimum: int
    maximum: int


class UsageV1(StrictModel):
    kind: Literal[
        "at_will",
        "recharge",
        "per_turn",
        "per_round",
        "per_day",
        "once",
        "resource",
        "spell_slots",
        "manual",
    ]
    recharge_range: RechargeRangeV1 | None = None
    uses: int | None = None
    resource_key: str | None = Field(default=None, max_length=64)
    refresh_text: str | None = Field(default=None, max_length=256)


class ResourceCostV1(StrictModel):
    resource_key: str = Field(min_length=1, max_length=64)
    amount: int


class DurationV1(StrictModel):
    kind: Literal[
        "instantaneous",
        "until_start_turn",
        "until_end_turn",
        "rounds",
        "minutes",
        "hours",
        "until_save",
        "permanent",
        "special",
    ]
    value: int | None = None


class RangeProfileV1(StrictModel):
    normal: DistanceV1
    long: DistanceV1 | None = None


class TargetProfileV1(StrictModel):
    kind: Literal[
        "creature",
        "creatures",
        "self",
        "point",
        "area",
        "object",
        "structure",
        "special",
    ]
    count: int | None = None
    range: RangeProfileV1 | None = None
    area: str | None = Field(default=None, max_length=128)
    qualifiers: list[str] = Field(default_factory=list)


class DamageEffectV1(StrictModel):
    kind: Literal["damage"] = "damage"
    damage: DiceExpressionV1
    damage_type: str = Field(min_length=1, max_length=64)
    duration: DurationV1 | None = None


class HealingEffectV1(StrictModel):
    kind: Literal["healing"] = "healing"
    healing: DiceExpressionV1


class ConditionEffectV1(StrictModel):
    kind: Literal["condition"] = "condition"
    condition: str = Field(min_length=1, max_length=64)
    duration: DurationV1 | None = None


class MovementEffectV1(StrictModel):
    kind: Literal["movement"] = "movement"
    movement_mode_key: str | None = Field(default=None, max_length=64)
    distance: DistanceV1 | None = None


class ForcedMovementEffectV1(StrictModel):
    kind: Literal["forced_movement"] = "forced_movement"
    distance: DistanceV1
    direction: str = Field(min_length=1, max_length=128)


class ResourceChangeEffectV1(StrictModel):
    kind: Literal["resource_change"] = "resource_change"
    resource_key: str = Field(min_length=1, max_length=64)
    amount: int


class SummonEffectV1(StrictModel):
    kind: Literal["summon"] = "summon"
    creature_description: str = Field(min_length=1, max_length=1024)
    duration: DurationV1 | None = None


class StatModifierEffectV1(StrictModel):
    kind: Literal["stat_modifier"] = "stat_modifier"
    stat: str = Field(min_length=1, max_length=64)
    modifier: int
    duration: DurationV1 | None = None


class EnableElementsEffectV1(StrictModel):
    kind: Literal["enable_elements"] = "enable_elements"
    element_keys: list[str]


class DisableElementsEffectV1(StrictModel):
    kind: Literal["disable_elements"] = "disable_elements"
    element_keys: list[str]


class EnterPhaseEffectV1(StrictModel):
    kind: Literal["enter_phase"] = "enter_phase"
    phase_key: str = Field(min_length=1, max_length=64)


class HumanAdjudicatedEffectV1(StrictModel):
    kind: Literal["human_adjudicated"] = "human_adjudicated"
    adjudication_text: str = Field(min_length=1, max_length=2048)


EffectV1 = Annotated[
    DamageEffectV1
    | HealingEffectV1
    | ConditionEffectV1
    | MovementEffectV1
    | ForcedMovementEffectV1
    | ResourceChangeEffectV1
    | SummonEffectV1
    | StatModifierEffectV1
    | EnableElementsEffectV1
    | DisableElementsEffectV1
    | EnterPhaseEffectV1
    | HumanAdjudicatedEffectV1,
    Field(discriminator="kind"),
]


class AttackMechanicV1(StrictModel):
    kind: Literal["attack"] = "attack"
    attack_type: Literal[
        "melee_weapon", "ranged_weapon", "melee_spell", "ranged_spell", "special"
    ]
    attack_bonus: int
    reach: DistanceV1 | None = None
    range: RangeProfileV1 | None = None
    target: TargetProfileV1
    hit_effects: list[EffectV1] = Field(default_factory=list)
    miss_effects: list[EffectV1] = Field(default_factory=list)


class SavingThrowV1(StrictModel):
    ability: Literal[
        "strength", "dexterity", "constitution", "intelligence", "wisdom", "charisma"
    ]
    dc: int


class SaveEffectMechanicV1(StrictModel):
    kind: Literal["save_effect"] = "save_effect"
    save: SavingThrowV1
    target: TargetProfileV1
    failure_effects: list[EffectV1] = Field(default_factory=list)
    success_effects: list[EffectV1] = Field(default_factory=list)


class ElementUseV1(StrictModel):
    element_key: str = Field(min_length=1, max_length=64)
    count: int = Field(ge=1)
    choice_group: str | None = Field(default=None, max_length=64)


class MultiattackMechanicV1(StrictModel):
    kind: Literal["multiattack"] = "multiattack"
    sequences: list[ElementUseV1]


class SpellRefV1(StrictModel):
    name: str = Field(min_length=1, max_length=128)
    school: str | None = Field(default=None, max_length=64)
    source_id: str | None = Field(default=None, max_length=128)
    rules_text: str | None = Field(default=None, max_length=4096)


class SpellGroupV1(StrictModel):
    usage: UsageV1
    level: int | None = None
    slots: int | None = None
    spells: list[SpellRefV1]


class SpellcastingMechanicV1(StrictModel):
    kind: Literal["spellcasting"] = "spellcasting"
    casting_mode: Literal["prepared", "known", "innate", "charges", "special"]
    ability: Literal[
        "strength", "dexterity", "constitution", "intelligence", "wisdom", "charisma"
    ] | None = None
    save_dc: int | None = None
    attack_bonus: int | None = None
    caster_level: int | None = None
    groups: list[SpellGroupV1]


class PassiveMechanicV1(StrictModel):
    kind: Literal["passive"] = "passive"
    effects: list[EffectV1] = Field(default_factory=list)


class CompositeMechanicV1(StrictModel):
    kind: Literal["composite"] = "composite"
    target: TargetProfileV1 | None = None
    effects: list[EffectV1] = Field(default_factory=list)


class PhaseTransitionMechanicV1(StrictModel):
    kind: Literal["phase_transition"] = "phase_transition"
    destination_phase_key: str = Field(min_length=1, max_length=64)
    effects: list[EffectV1] = Field(default_factory=list)


class HumanAdjudicatedMechanicV1(StrictModel):
    kind: Literal["human_adjudicated"] = "human_adjudicated"
    adjudication_tags: list[str] = Field(default_factory=list)


MechanicV1 = Annotated[
    AttackMechanicV1
    | SaveEffectMechanicV1
    | MultiattackMechanicV1
    | SpellcastingMechanicV1
    | PassiveMechanicV1
    | CompositeMechanicV1
    | PhaseTransitionMechanicV1
    | HumanAdjudicatedMechanicV1,
    Field(discriminator="kind"),
]


class RuleElementV1(StrictModel):
    key: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=128)
    section: Literal[
        "trait",
        "action",
        "bonus_action",
        "reaction",
        "legendary_action",
        "lair_action",
        "regional_effect",
    ]
    summary: str | None = Field(default=None, max_length=512)
    rules_text: str = Field(min_length=1, max_length=8192)
    activation: ActivationV1
    usage: UsageV1
    costs: list[ResourceCostV1] = Field(default_factory=list)
    mechanic: MechanicV1
    tags: list[str] = Field(default_factory=list)
    automation_support: Literal["full", "partial", "manual"]


class CreaturePhaseV1(StrictModel):
    key: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=128)
    default: bool = False
    enabled_element_keys: list[str] = Field(default_factory=list)
    disabled_element_keys: list[str] = Field(default_factory=list)
    entry_rules_text: str | None = Field(default=None, max_length=2048)


class LairProfileV1(StrictModel):
    name: str | None = Field(default=None, max_length=128)
    description: str | None = Field(default=None, max_length=4096)
    initiative_count: int | None = None
    initiative_tiebreak: int | None = None
    regional_rules_text: str | None = Field(default=None, max_length=4096)


class StatblockFlavorTextV1(StrictModel):
    summary: str | None = Field(default=None, max_length=1024)
    description: str | None = Field(default=None, max_length=8192)


class StatblockDefinitionV1(StrictModel):
    """Published definition envelope; mechanics are typed, not free-form dicts."""

    ruleset: RulesetRefContractV1
    identity: CreatureIdentityV1
    defenses: DefenseProfileV1
    vitality: VitalityProfileV1
    movement: MovementProfileV1
    abilities: AbilityScoresV1
    proficiencies: ProficiencyProfileV1
    senses: SenseProfileV1
    communication: CommunicationProfileV1
    challenge: ChallengeProfileV1
    resources: list[ResourcePoolV1] = Field(default_factory=list)
    rule_elements: list[RuleElementV1]
    phases: list[CreaturePhaseV1] = Field(default_factory=list)
    lair: LairProfileV1 | None = None
    flavor_text: StatblockFlavorTextV1 | None = None


class GeneratedStatblockCandidateV1(StrictModel):
    """Published DungeonMind candidate envelope enforced at Buddy's trust boundary."""

    candidate_id: str = Field(pattern=_CANDIDATE_ID_PATTERN)
    contract: ContractNameV1
    contract_version: ContractVersionV1
    created_at: datetime
    expires_at: datetime
    definition: StatblockDefinitionV1
    generation_receipt: CandidateGenerationReceiptV1
    validation_receipt: CandidateValidationReceiptV1
    assets: list[AssetRefV1] = Field(default_factory=list)
    asset_warnings: list[AssetWarningV1] = Field(default_factory=list)
    asset_brief: AssetBriefV1 | None = None
    source_locator: ExactRevisionLocatorV1 | None = None


class StatblockIntegrationReadinessV1(StrictModel):
    schema_name: Literal["dmb_statblock_integration_readiness_v1"] = Field(
        default="dmb_statblock_integration_readiness_v1",
        alias="schema",
    )
    configured: bool
    available: bool
    downstream_status: str
    contract: ContractNameV1 | None = None
    contract_version: ContractVersionV1 | None = None
    capabilities: list[str] = Field(default_factory=list)
    diagnostics: list[str] = Field(default_factory=list)

    model_config = ConfigDict(extra="forbid", populate_by_name=True)
