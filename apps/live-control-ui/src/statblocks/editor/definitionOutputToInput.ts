import type {
  AbilityScores,
  Activation,
  AttackMechanic_Input,
  AttackMechanic_Output,
  CommunicationProfile_Input,
  CommunicationProfile_Output,
  CompositeMechanic_Input,
  CompositeMechanic_Output,
  ConditionEffect_Input,
  ConditionEffect_Output,
  CreatureIdentity,
  CreaturePhase,
  DamageEffect_Input,
  DamageEffect_Output,
  DefenseProfile_Input,
  DefenseProfile_Output,
  DiceExpression,
  Distance,
  Duration,
  ForcedMovementEffect_Input,
  ForcedMovementEffect_Output,
  HitPointProfile,
  HumanAdjudicatedEffect,
  HumanAdjudicatedMechanic,
  LairProfile,
  MovementEffect_Input,
  MovementEffect_Output,
  MovementMode_Input,
  MovementMode_Output,
  MovementProfile_Input,
  MovementProfile_Output,
  MultiattackMechanic,
  PassiveMechanic_Input,
  PassiveMechanic_Output,
  PhaseTransitionMechanic_Input,
  PhaseTransitionMechanic_Output,
  ProficiencyProfile_Input,
  ProficiencyProfile_Output,
  RangeProfile_Input,
  RangeProfile_Output,
  ResourceChangeEffect,
  ResourceCost,
  ResourcePool,
  RuleElement_Input,
  RuleElement_Output,
  SaveEffectMechanic_Input,
  SaveEffectMechanic_Output,
  SavingThrow,
  SavingThrowBonus,
  Sense_Input,
  Sense_Output,
  SenseProfile_Input,
  SenseProfile_Output,
  SkillBonus,
  SpellcastingMechanic_Input,
  SpellcastingMechanic_Output,
  SpellGroup_Input,
  SpellGroup_Output,
  SpellRef,
  StatModifierEffect_Input,
  StatModifierEffect_Output,
  StatblockDefinitionV1_Input,
  StatblockDefinitionV1_Output,
  StatblockFlavorText,
  SummonEffect_Input,
  SummonEffect_Output,
  TargetProfile_Input,
  TargetProfile_Output,
  Usage,
  VitalityProfile_Input,
  VitalityProfile_Output,
  ChallengeProfile,
  RulesetRef,
  EnableElementsEffect,
  DisableElementsEffect,
  EnterPhaseEffect,
  HealingEffect,
  DamageInteraction,
  ArmorClassProfile,
} from "../../contracts/dungeonbuddy-statblocks-v1/client";

type MechanicEffectOutput =
  | DamageEffect_Output
  | HealingEffect
  | ConditionEffect_Output
  | MovementEffect_Output
  | ForcedMovementEffect_Output
  | ResourceChangeEffect
  | SummonEffect_Output
  | StatModifierEffect_Output
  | EnableElementsEffect
  | DisableElementsEffect
  | EnterPhaseEffect
  | HumanAdjudicatedEffect;

type MechanicEffectInput =
  | DamageEffect_Input
  | HealingEffect
  | ConditionEffect_Input
  | MovementEffect_Input
  | ForcedMovementEffect_Input
  | ResourceChangeEffect
  | SummonEffect_Input
  | StatModifierEffect_Input
  | EnableElementsEffect
  | DisableElementsEffect
  | EnterPhaseEffect
  | HumanAdjudicatedEffect;

function cloneDiceExpression(dice: DiceExpression): DiceExpression {
  return structuredClone(dice);
}

function cloneDistance(distance: Distance): Distance {
  return structuredClone(distance);
}

function cloneDuration(duration: Duration): Duration {
  return structuredClone(duration);
}

function cloneActivation(activation: Activation): Activation {
  return structuredClone(activation);
}

function cloneUsage(usage: Usage): Usage {
  return structuredClone(usage);
}

function cloneSavingThrow(save: SavingThrow): SavingThrow {
  return structuredClone(save);
}

function cloneCreatureIdentity(identity: CreatureIdentity): CreatureIdentity {
  return structuredClone(identity);
}

function cloneRuleset(ruleset: RulesetRef): RulesetRef {
  return structuredClone(ruleset);
}

function cloneChallenge(challenge: ChallengeProfile): ChallengeProfile {
  return structuredClone(challenge);
}

function cloneHitPointProfile(hitPoints: HitPointProfile): HitPointProfile {
  return structuredClone(hitPoints);
}

function cloneArmorClassProfile(profile: ArmorClassProfile): ArmorClassProfile {
  return structuredClone(profile);
}

function cloneDamageInteraction(interaction: DamageInteraction): DamageInteraction {
  return structuredClone(interaction);
}

function cloneSavingThrowBonus(bonus: SavingThrowBonus): SavingThrowBonus {
  return structuredClone(bonus);
}

function cloneSkillBonus(bonus: SkillBonus): SkillBonus {
  return structuredClone(bonus);
}

function cloneSpellRef(spell: SpellRef): SpellRef {
  return structuredClone(spell);
}

function cloneResourceCost(cost: ResourceCost): ResourceCost {
  return structuredClone(cost);
}

function cloneResourcePool(pool: ResourcePool): ResourcePool {
  return structuredClone(pool);
}

function cloneCreaturePhase(phase: CreaturePhase): CreaturePhase {
  return structuredClone(phase);
}

function cloneLairProfile(lair: LairProfile): LairProfile {
  return structuredClone(lair);
}

function cloneFlavorText(flavor: StatblockFlavorText): StatblockFlavorText {
  return structuredClone(flavor);
}

function mapRangeProfile(range: RangeProfile_Output): RangeProfile_Input {
  const input: RangeProfile_Input = {
    normal: cloneDistance(range.normal),
  };
  if (range.long !== undefined) {
    input.long = range.long === null ? null : cloneDistance(range.long);
  }
  return input;
}

function mapTargetProfile(target: TargetProfile_Output): TargetProfile_Input {
  const input: TargetProfile_Input = {
    kind: target.kind,
    count: target.count ?? null,
    area: target.area ?? null,
    qualifiers: target.qualifiers ? [...target.qualifiers] : [],
  };
  if (target.range !== undefined) {
    input.range = target.range === null ? null : mapRangeProfile(target.range);
  }
  return input;
}

function mapDamageEffect(effect: DamageEffect_Output): DamageEffect_Input {
  return {
    kind: effect.kind ?? "damage",
    damage: cloneDiceExpression(effect.damage),
    damage_type: effect.damage_type,
    duration: effect.duration === undefined ? undefined : effect.duration === null ? null : cloneDuration(effect.duration),
  };
}

function mapConditionEffect(effect: ConditionEffect_Output): ConditionEffect_Input {
  return {
    kind: effect.kind ?? "condition",
    condition: effect.condition,
    duration: effect.duration === undefined ? undefined : effect.duration === null ? null : cloneDuration(effect.duration),
  };
}

function mapMovementEffect(effect: MovementEffect_Output): MovementEffect_Input {
  const input: MovementEffect_Input = {
    kind: effect.kind ?? "movement",
  };
  if (effect.movement_mode_key !== undefined) {
    input.movement_mode_key = effect.movement_mode_key;
  }
  if (effect.distance !== undefined) {
    input.distance = effect.distance === null ? null : cloneDistance(effect.distance);
  }
  return input;
}

function mapForcedMovementEffect(effect: ForcedMovementEffect_Output): ForcedMovementEffect_Input {
  return {
    kind: effect.kind ?? "forced_movement",
    distance: cloneDistance(effect.distance),
    direction: effect.direction,
  };
}

function mapSummonEffect(effect: SummonEffect_Output): SummonEffect_Input {
  return {
    kind: effect.kind ?? "summon",
    creature_description: effect.creature_description,
    duration: effect.duration === undefined ? undefined : effect.duration === null ? null : cloneDuration(effect.duration),
  };
}

function mapStatModifierEffect(effect: StatModifierEffect_Output): StatModifierEffect_Input {
  return {
    kind: effect.kind ?? "stat_modifier",
    stat: effect.stat,
    modifier: effect.modifier,
    duration: effect.duration === undefined ? undefined : effect.duration === null ? null : cloneDuration(effect.duration),
  };
}

function mapHealingEffect(effect: HealingEffect): HealingEffect {
  return {
    kind: effect.kind ?? "healing",
    healing: cloneDiceExpression(effect.healing),
  };
}

function mapResourceChangeEffect(effect: ResourceChangeEffect): ResourceChangeEffect {
  return structuredClone(effect);
}

function mapEnableElementsEffect(effect: EnableElementsEffect): EnableElementsEffect {
  return {
    kind: effect.kind ?? "enable_elements",
    element_keys: [...effect.element_keys],
  };
}

function mapDisableElementsEffect(effect: DisableElementsEffect): DisableElementsEffect {
  return {
    kind: effect.kind ?? "disable_elements",
    element_keys: [...effect.element_keys],
  };
}

function mapEnterPhaseEffect(effect: EnterPhaseEffect): EnterPhaseEffect {
  return {
    kind: effect.kind ?? "enter_phase",
    phase_key: effect.phase_key,
  };
}

function mapHumanAdjudicatedEffect(effect: HumanAdjudicatedEffect): HumanAdjudicatedEffect {
  return {
    kind: effect.kind ?? "human_adjudicated",
    adjudication_text: effect.adjudication_text,
  };
}

function mapMechanicEffect(effect: MechanicEffectOutput): MechanicEffectInput {
  const kind = effect.kind ?? inferEffectKind(effect);
  switch (kind) {
    case "damage":
      return mapDamageEffect(effect as DamageEffect_Output);
    case "healing":
      return mapHealingEffect(effect as HealingEffect);
    case "condition":
      return mapConditionEffect(effect as ConditionEffect_Output);
    case "movement":
      return mapMovementEffect(effect as MovementEffect_Output);
    case "forced_movement":
      return mapForcedMovementEffect(effect as ForcedMovementEffect_Output);
    case "resource_change":
      return mapResourceChangeEffect(effect as ResourceChangeEffect);
    case "summon":
      return mapSummonEffect(effect as SummonEffect_Output);
    case "stat_modifier":
      return mapStatModifierEffect(effect as StatModifierEffect_Output);
    case "enable_elements":
      return mapEnableElementsEffect(effect as EnableElementsEffect);
    case "disable_elements":
      return mapDisableElementsEffect(effect as DisableElementsEffect);
    case "enter_phase":
      return mapEnterPhaseEffect(effect as EnterPhaseEffect);
    case "human_adjudicated":
      return mapHumanAdjudicatedEffect(effect as HumanAdjudicatedEffect);
    default:
      throw new Error(`Unsupported effect kind: ${String(kind)}`);
  }
}

function inferEffectKind(effect: MechanicEffectOutput): string {
  if ("damage" in effect && "damage_type" in effect) return "damage";
  if ("healing" in effect) return "healing";
  if ("condition" in effect) return "condition";
  if ("movement_mode_key" in effect || ("distance" in effect && !("direction" in effect))) return "movement";
  if ("direction" in effect && "distance" in effect) return "forced_movement";
  if ("resource_key" in effect && "amount" in effect) return "resource_change";
  if ("creature_description" in effect) return "summon";
  if ("stat" in effect && "modifier" in effect) return "stat_modifier";
  if ("element_keys" in effect) {
    if (effect.kind === "disable_elements") return "disable_elements";
    return "enable_elements";
  }
  if ("phase_key" in effect && !("destination_phase_key" in effect)) return "enter_phase";
  if ("adjudication_text" in effect) return "human_adjudicated";
  return "damage";
}

function mapEffects(effects: MechanicEffectOutput[] | undefined): MechanicEffectInput[] | undefined {
  if (effects === undefined) return undefined;
  return effects.map(mapMechanicEffect);
}

function mapAttackMechanic(mechanic: AttackMechanic_Output): AttackMechanic_Input {
  const input: AttackMechanic_Input = {
    kind: mechanic.kind ?? "attack",
    attack_type: mechanic.attack_type,
    attack_bonus: mechanic.attack_bonus,
    target: mapTargetProfile(mechanic.target),
  };
  if (mechanic.reach !== undefined) {
    input.reach = mechanic.reach === null ? null : cloneDistance(mechanic.reach);
  }
  if (mechanic.range !== undefined) {
    input.range = mechanic.range === null ? null : mapRangeProfile(mechanic.range);
  }
  if (mechanic.hit_effects !== undefined) {
    input.hit_effects = mapEffects(mechanic.hit_effects);
  }
  if (mechanic.miss_effects !== undefined) {
    input.miss_effects = mapEffects(mechanic.miss_effects);
  }
  return input;
}

function mapSaveEffectMechanic(mechanic: SaveEffectMechanic_Output): SaveEffectMechanic_Input {
  const input: SaveEffectMechanic_Input = {
    kind: mechanic.kind ?? "save_effect",
    save: cloneSavingThrow(mechanic.save),
    target: mapTargetProfile(mechanic.target),
  };
  if (mechanic.failure_effects !== undefined) {
    input.failure_effects = mapEffects(mechanic.failure_effects);
  }
  if (mechanic.success_effects !== undefined) {
    input.success_effects = mapEffects(mechanic.success_effects);
  }
  return input;
}

function mapMultiattackMechanic(mechanic: MultiattackMechanic): MultiattackMechanic {
  return {
    kind: mechanic.kind ?? "multiattack",
    sequences: mechanic.sequences.map((sequence) => ({
      element_key: sequence.element_key,
      count: sequence.count,
      choice_group: sequence.choice_group ?? null,
    })),
  };
}

function mapSpellGroup(group: SpellGroup_Output): SpellGroup_Input {
  return {
    usage: cloneUsage(group.usage),
    level: group.level ?? null,
    slots: group.slots ?? null,
    spells: group.spells.map(cloneSpellRef),
  };
}

function mapSpellcastingMechanic(mechanic: SpellcastingMechanic_Output): SpellcastingMechanic_Input {
  return {
    kind: mechanic.kind ?? "spellcasting",
    casting_mode: mechanic.casting_mode,
    ability: mechanic.ability ?? null,
    save_dc: mechanic.save_dc ?? null,
    attack_bonus: mechanic.attack_bonus ?? null,
    caster_level: mechanic.caster_level ?? null,
    groups: mechanic.groups.map(mapSpellGroup),
  };
}

function mapPassiveMechanic(mechanic: PassiveMechanic_Output): PassiveMechanic_Input {
  const input: PassiveMechanic_Input = {
    kind: mechanic.kind ?? "passive",
  };
  if (mechanic.effects !== undefined) {
    input.effects = mapEffects(mechanic.effects);
  }
  return input;
}

function mapCompositeMechanic(mechanic: CompositeMechanic_Output): CompositeMechanic_Input {
  const input: CompositeMechanic_Input = {
    kind: mechanic.kind ?? "composite",
  };
  if (mechanic.target !== undefined) {
    input.target = mechanic.target === null ? null : mapTargetProfile(mechanic.target);
  }
  if (mechanic.effects !== undefined) {
    input.effects = mapEffects(mechanic.effects);
  }
  return input;
}

function mapPhaseTransitionMechanic(mechanic: PhaseTransitionMechanic_Output): PhaseTransitionMechanic_Input {
  const input: PhaseTransitionMechanic_Input = {
    kind: mechanic.kind ?? "phase_transition",
    destination_phase_key: mechanic.destination_phase_key,
  };
  if (mechanic.effects !== undefined) {
    input.effects = mapEffects(mechanic.effects);
  }
  return input;
}

function mapHumanAdjudicatedMechanic(mechanic: HumanAdjudicatedMechanic): HumanAdjudicatedMechanic {
  return {
    kind: mechanic.kind ?? "human_adjudicated",
    adjudication_tags: mechanic.adjudication_tags ? [...mechanic.adjudication_tags] : undefined,
  };
}

function resolveMechanicKind(mechanic: RuleElement_Output["mechanic"]): string {
  if (mechanic.kind) return mechanic.kind;
  if ("groups" in mechanic) return "spellcasting";
  if ("sequences" in mechanic) return "multiattack";
  if ("destination_phase_key" in mechanic) return "phase_transition";
  if ("adjudication_tags" in mechanic && !("attack_bonus" in mechanic)) return "human_adjudicated";
  if ("save" in mechanic) return "save_effect";
  if ("attack_bonus" in mechanic) return "attack";
  if ("effects" in mechanic && "target" in mechanic) return "composite";
  if ("effects" in mechanic) return "passive";
  return "passive";
}

function mapRuleElementMechanic(mechanic: RuleElement_Output["mechanic"]): RuleElement_Input["mechanic"] {
  const kind = resolveMechanicKind(mechanic);
  switch (kind) {
    case "attack":
      return mapAttackMechanic(mechanic as AttackMechanic_Output);
    case "save_effect":
      return mapSaveEffectMechanic(mechanic as SaveEffectMechanic_Output);
    case "multiattack":
      return mapMultiattackMechanic(mechanic as MultiattackMechanic);
    case "spellcasting":
      return mapSpellcastingMechanic(mechanic as SpellcastingMechanic_Output);
    case "passive":
      return mapPassiveMechanic(mechanic as PassiveMechanic_Output);
    case "composite":
      return mapCompositeMechanic(mechanic as CompositeMechanic_Output);
    case "phase_transition":
      return mapPhaseTransitionMechanic(mechanic as PhaseTransitionMechanic_Output);
    case "human_adjudicated":
      return mapHumanAdjudicatedMechanic(mechanic as HumanAdjudicatedMechanic);
    default:
      throw new Error(`Unsupported mechanic kind: ${String(kind)}`);
  }
}

function mapRuleElement(element: RuleElement_Output): RuleElement_Input {
  const input: RuleElement_Input = {
    key: element.key,
    name: element.name,
    section: element.section,
    rules_text: element.rules_text,
    activation: cloneActivation(element.activation),
    usage: cloneUsage(element.usage),
    mechanic: mapRuleElementMechanic(element.mechanic),
    automation_support: element.automation_support,
  };
  if (element.summary !== undefined) {
    input.summary = element.summary;
  }
  if (element.tags !== undefined) {
    input.tags = [...element.tags];
  }
  if (element.costs !== undefined) {
    input.costs = element.costs.map(cloneResourceCost);
  }
  return input;
}

function mapDefenseProfile(defenses: DefenseProfile_Output): DefenseProfile_Input {
  const input: DefenseProfile_Input = {
    armor_classes: defenses.armor_classes.map(cloneArmorClassProfile),
  };
  if (defenses.damage_interactions !== undefined) {
    input.damage_interactions = defenses.damage_interactions.map(cloneDamageInteraction);
  }
  if (defenses.condition_immunities !== undefined) {
    input.condition_immunities = [...defenses.condition_immunities];
  }
  return input;
}

function mapVitalityProfile(vitality: VitalityProfile_Output): VitalityProfile_Input {
  return {
    hit_points: cloneHitPointProfile(vitality.hit_points),
  };
}

function mapMovementMode(mode: MovementMode_Output): MovementMode_Input {
  return {
    key: mode.key,
    mode: mode.mode,
    distance: cloneDistance(mode.distance),
    qualifiers: mode.qualifiers ? [...mode.qualifiers] : [],
  };
}

function mapMovementProfile(movement: MovementProfile_Output): MovementProfile_Input {
  return {
    modes: movement.modes.map(mapMovementMode),
  };
}

function mapAbilityScores(abilities: AbilityScores): AbilityScores {
  return structuredClone(abilities);
}

function mapProficiencyProfile(proficiencies: ProficiencyProfile_Output): ProficiencyProfile_Input {
  const input: ProficiencyProfile_Input = {};
  if (proficiencies.saving_throws !== undefined) {
    input.saving_throws = proficiencies.saving_throws.map(cloneSavingThrowBonus);
  }
  if (proficiencies.skills !== undefined) {
    input.skills = proficiencies.skills.map(cloneSkillBonus);
  }
  return input;
}

function mapSense(sense: Sense_Output): Sense_Input {
  return {
    kind: sense.kind,
    range: cloneDistance(sense.range),
    qualifiers: sense.qualifiers ? [...sense.qualifiers] : [],
  };
}

function mapSenseProfile(senses: SenseProfile_Output): SenseProfile_Input {
  const input: SenseProfile_Input = {
    passive_perception: senses.passive_perception,
  };
  if (senses.senses !== undefined) {
    input.senses = senses.senses.map(mapSense);
  }
  return input;
}

function mapCommunicationProfile(communication: CommunicationProfile_Output): CommunicationProfile_Input {
  const input: CommunicationProfile_Input = {};
  if (communication.languages !== undefined) {
    input.languages = [...communication.languages];
  }
  if (communication.special_modes !== undefined) {
    input.special_modes = [...communication.special_modes];
  }
  if (communication.telepathy_range !== undefined) {
    input.telepathy_range =
      communication.telepathy_range === null ? null : cloneDistance(communication.telepathy_range);
  }
  return input;
}

export function definitionOutputToInput(output: StatblockDefinitionV1_Output): StatblockDefinitionV1_Input {
  const input: StatblockDefinitionV1_Input = {
    ruleset: cloneRuleset(output.ruleset),
    identity: cloneCreatureIdentity(output.identity),
    defenses: mapDefenseProfile(output.defenses),
    vitality: mapVitalityProfile(output.vitality),
    movement: mapMovementProfile(output.movement),
    abilities: mapAbilityScores(output.abilities),
    proficiencies: mapProficiencyProfile(output.proficiencies),
    senses: mapSenseProfile(output.senses),
    communication: mapCommunicationProfile(output.communication),
    challenge: cloneChallenge(output.challenge),
    rule_elements: output.rule_elements.map(mapRuleElement),
  };

  if (output.resources !== undefined) {
    input.resources = output.resources.map(cloneResourcePool);
  }
  if (output.phases !== undefined) {
    input.phases = output.phases.map(cloneCreaturePhase);
  }
  if (output.lair !== undefined) {
    input.lair = output.lair === null ? null : cloneLairProfile(output.lair);
  }
  if (output.flavor_text !== undefined) {
    input.flavor_text = output.flavor_text === null ? null : cloneFlavorText(output.flavor_text);
  }

  return input;
}
