import type {
  AbilityScores,
  Activation,
  CreaturePhase,
  DamageInteraction,
  GeneratedStatblockCandidateV1,
  HitPointProfile,
  LairProfile,
  ResourcePool,
  RuleElement_Output,
  StatblockDefinitionV1_Output,
  StatblockRevisionResourceV1,
  Usage,
  ValidationIssueV1,
  ValidationReceiptV1,
} from "../../contracts/dungeonbuddy-statblocks-v1/client";

export type StatblockRenderMode = "review" | "summary" | "full" | "embed" | "combat-drilldown";

export type AbilityRow = {
  ability: keyof AbilityScores;
  score: number;
  modifier: number;
  label: string;
};

export type FormattedDamageInteraction = {
  key: string;
  kind: string;
  damageTypes: string;
  qualifiers: string | null;
  bypasses: string | null;
};

export type FormattedResource = {
  key: string;
  name: string;
  maximum: number;
  refresh: string;
  rulesText: string | null;
};

export type FormattedPhase = {
  key: string;
  name: string;
  isDefault: boolean;
  enabledElementKeys: string[];
  disabledElementKeys: string[];
  entryRulesText: string | null;
};

export type FormattedLair = {
  name: string | null;
  description: string | null;
  initiativeCount: number | null;
  initiativeTiebreak: number | null;
  regionalRulesText: string | null;
};

export type FormattedActivation = {
  kind: string;
  trigger: string | null;
  timingText: string | null;
};

export type FormattedUsage = {
  kind: string;
  summary: string;
};

export type FormattedCost = {
  resourceKey: string;
  amount: number;
};

export type FormattedMechanicDetail = {
  kind: string;
  lines: string[];
};

export type FormattedRuleElement = {
  key: string;
  name: string;
  section: string;
  rulesText: string;
  summary: string | null;
  automationSupport: string;
  mechanicKind: string;
  humanAdjudicated: boolean;
  unsupportedMechanic: boolean;
  activation: FormattedActivation;
  usage: FormattedUsage;
  costs: FormattedCost[];
  mechanicDetails: FormattedMechanicDetail;
};

export type StatblockViewModel = {
  recordKind: "candidate" | "revision";
  candidateId: string;
  contract: string;
  contractVersion: string;
  createdAt: string;
  expiresAt: string;
  identityLine: string;
  name: string;
  armorClassSummary: string;
  hitPointsSummary: string;
  speedSummary: string;
  challengeSummary: string;
  abilities: AbilityRow[];
  savingThrows: string;
  skills: string;
  sensesSummary: string;
  languagesSummary: string;
  damageInteractions: FormattedDamageInteraction[];
  conditionImmunities: string[];
  resources: FormattedResource[];
  phases: FormattedPhase[];
  lair: FormattedLair | null;
  flavorSummary: string | null;
  ruleElements: FormattedRuleElement[];
  validation: {
    status: string;
    digest: string;
    errors: ValidationIssueV1[];
    warnings: ValidationIssueV1[];
  } | null;
  generation: {
    requestId: string;
    provider: string;
    model: string;
    generatedAt: string;
  } | null;
};

const ABILITY_ORDER: Array<keyof AbilityScores> = [
  "strength",
  "dexterity",
  "constitution",
  "intelligence",
  "wisdom",
  "charisma",
];

const ABILITY_LABEL: Record<keyof AbilityScores, string> = {
  strength: "STR",
  dexterity: "DEX",
  constitution: "CON",
  intelligence: "INT",
  wisdom: "WIS",
  charisma: "CHA",
};

const KNOWN_MECHANIC_KINDS = new Set([
  "attack",
  "save_effect",
  "multiattack",
  "spellcasting",
  "passive",
  "composite",
  "phase_transition",
  "human_adjudicated",
]);

export function abilityModifier(score: number): number {
  return Math.floor((score - 10) / 2);
}

export function formatModifier(modifier: number): string {
  return modifier >= 0 ? `+${modifier}` : String(modifier);
}

function formatHitPoints(hp: HitPointProfile): string {
  const average = hp.displayed_average;
  if (hp.method === "fixed" && hp.fixed_value != null) {
    return String(hp.fixed_value);
  }
  if (hp.formula) {
    const { count, die, modifier = 0 } = hp.formula;
    const formula = `${count}d${die}${modifier >= 0 ? `+${modifier}` : modifier}`;
    return average != null ? `${average} (${formula})` : formula;
  }
  return average != null ? String(average) : "—";
}

function formatDistance(value: { value: number; unit?: string } | null | undefined): string {
  if (!value) return "";
  return `${value.value} ${value.unit ?? "feet"}`;
}

function partitionIssues(receipt: ValidationReceiptV1 | null | undefined): {
  errors: ValidationIssueV1[];
  warnings: ValidationIssueV1[];
} {
  const issues = receipt?.issues ?? [];
  return {
    errors: issues.filter((issue) => issue.severity === "error"),
    warnings: issues.filter((issue) => issue.severity !== "error"),
  };
}

function mechanicKind(mechanic: RuleElement_Output["mechanic"]): string {
  if (mechanic && typeof mechanic === "object" && "kind" in mechanic && typeof mechanic.kind === "string") {
    return mechanic.kind;
  }
  return "unknown";
}

function formatActivation(activation: Activation): FormattedActivation {
  const triggerParts = [
    activation.trigger?.kind ? `kind ${activation.trigger.kind}` : null,
    activation.trigger?.source_element_key ? `source ${activation.trigger.source_element_key}` : null,
    activation.trigger?.condition_text ?? null,
  ].filter(Boolean);
  return {
    kind: activation.kind,
    trigger: triggerParts.length ? triggerParts.join("; ") : null,
    timingText: activation.timing_text ?? null,
  };
}

function formatUsage(usage: Usage): FormattedUsage {
  const parts = [usage.kind.replace(/_/g, " ")];
  if (usage.uses != null) parts.push(`${usage.uses} uses`);
  if (usage.recharge_range) {
    parts.push(`recharge ${usage.recharge_range.minimum}–${usage.recharge_range.maximum}`);
  }
  if (usage.resource_key) parts.push(`resource ${usage.resource_key}`);
  if (usage.refresh_text) parts.push(usage.refresh_text);
  return { kind: usage.kind, summary: parts.join(" · ") };
}

function formatTarget(
  target:
    | { kind?: string; count?: number | null; area?: string | null; qualifiers?: string[] | null; notes?: string | null }
    | null
    | undefined,
): string | null {
  if (!target) return null;
  const parts = [
    target.kind ? String(target.kind).replace(/_/g, " ") : null,
    target.count != null ? `count ${target.count}` : null,
    target.area ?? null,
    target.qualifiers?.length ? target.qualifiers.join(", ") : null,
    target.notes ?? null,
  ].filter(Boolean);
  return parts.length ? parts.join(", ") : null;
}

function formatMechanicDetails(mechanic: RuleElement_Output["mechanic"]): FormattedMechanicDetail {
  const kind = mechanicKind(mechanic);
  const lines: string[] = [];

  if (!mechanic || typeof mechanic !== "object") {
    return { kind, lines: ["No typed mechanic payload"] };
  }

  switch (kind) {
    case "attack": {
      const attack = mechanic as Extract<RuleElement_Output["mechanic"], { attack_type: string }>;
      lines.push(`Attack type: ${attack.attack_type.replace(/_/g, " ")}`);
      lines.push(`Attack bonus: ${formatModifier(attack.attack_bonus)}`);
      if (attack.reach) lines.push(`Reach: ${formatDistance(attack.reach)}`);
      if (attack.range?.normal) {
        const long = attack.range.long ? ` / ${formatDistance(attack.range.long)}` : "";
        lines.push(`Range: ${formatDistance(attack.range.normal)}${long}`);
      }
      const target = formatTarget(attack.target);
      if (target) lines.push(`Target: ${target}`);
      if (attack.hit_effects?.length) lines.push(`Hit effects: ${attack.hit_effects.length}`);
      if (attack.miss_effects?.length) lines.push(`Miss effects: ${attack.miss_effects.length}`);
      break;
    }
    case "save_effect": {
      const save = mechanic as Extract<RuleElement_Output["mechanic"], { save: { ability: string; dc: number } }>;
      lines.push(`Save: ${save.save.ability} DC ${save.save.dc}`);
      const target = formatTarget(save.target);
      if (target) lines.push(`Target: ${target}`);
      if (save.failure_effects?.length) lines.push(`On failure: ${save.failure_effects.length} effect(s)`);
      if (save.success_effects?.length) lines.push(`On success: ${save.success_effects.length} effect(s)`);
      break;
    }
    case "multiattack": {
      const multi = mechanic as Extract<RuleElement_Output["mechanic"], { sequences: Array<{ element_key: string; count: number }> }>;
      for (const sequence of multi.sequences ?? []) {
        const choice = "choice_group" in sequence && sequence.choice_group ? ` [${sequence.choice_group}]` : "";
        lines.push(`${sequence.count}× ${sequence.element_key}${choice}`);
      }
      if (!lines.length) lines.push("No sequences declared");
      break;
    }
    case "spellcasting": {
      const casting = mechanic as Extract<
        RuleElement_Output["mechanic"],
        { casting_mode: string; groups: Array<{ spells: Array<{ name: string }>; usage: Usage; level?: number | null; slots?: number | null }> }
      >;
      lines.push(`Casting mode: ${casting.casting_mode}`);
      if (casting.ability) lines.push(`Ability: ${casting.ability}`);
      if (casting.save_dc != null) lines.push(`Save DC: ${casting.save_dc}`);
      if (casting.attack_bonus != null) lines.push(`Spell attack: ${formatModifier(casting.attack_bonus)}`);
      if (casting.caster_level != null) lines.push(`Caster level: ${casting.caster_level}`);
      for (const group of casting.groups ?? []) {
        const usage = formatUsage(group.usage).summary;
        const level = group.level != null ? `L${group.level}` : "cantrip/special";
        const slots = group.slots != null ? `${group.slots} slots` : "no slot count";
        const spells = group.spells.map((spell) => spell.name).join(", ") || "(no spells)";
        lines.push(`Group ${level} · ${slots} · ${usage}: ${spells}`);
      }
      break;
    }
    case "passive":
    case "composite": {
      const effects = "effects" in mechanic ? mechanic.effects : undefined;
      lines.push(`Effects: ${effects?.length ?? 0}`);
      if ("target" in mechanic && mechanic.target) {
        const target = formatTarget(mechanic.target);
        if (target) lines.push(`Target: ${target}`);
      }
      break;
    }
    case "phase_transition": {
      const phase = mechanic as Extract<RuleElement_Output["mechanic"], { destination_phase_key: string }>;
      lines.push(`Destination phase: ${phase.destination_phase_key}`);
      if (phase.effects?.length) lines.push(`Transition effects: ${phase.effects.length}`);
      break;
    }
    case "human_adjudicated": {
      const human = mechanic as Extract<RuleElement_Output["mechanic"], { adjudication_tags?: string[] }>;
      const tags = human.adjudication_tags?.length ? human.adjudication_tags.join(", ") : "no tags";
      lines.push(`Adjudication tags: ${tags}`);
      break;
    }
    default:
      lines.push("Typed mechanic details unavailable for this kind");
      break;
  }

  return { kind, lines };
}

function formatRuleElement(element: RuleElement_Output): FormattedRuleElement {
  const kind = mechanicKind(element.mechanic);
  const humanAdjudicated = kind === "human_adjudicated";
  return {
    key: element.key,
    name: element.name,
    section: element.section,
    rulesText: element.rules_text,
    summary: element.summary ?? null,
    automationSupport: element.automation_support,
    mechanicKind: kind,
    humanAdjudicated,
    unsupportedMechanic: !KNOWN_MECHANIC_KINDS.has(kind),
    activation: formatActivation(element.activation),
    usage: formatUsage(element.usage),
    costs: (element.costs ?? []).map((cost) => ({
      resourceKey: cost.resource_key,
      amount: cost.amount,
    })),
    mechanicDetails: formatMechanicDetails(element.mechanic),
  };
}

function formatDamageInteraction(entry: DamageInteraction): FormattedDamageInteraction {
  return {
    key: entry.key,
    kind: entry.kind,
    damageTypes: entry.damage_types.join(", "),
    qualifiers: entry.qualifiers?.length ? entry.qualifiers.join(", ") : null,
    bypasses: entry.bypasses?.length ? entry.bypasses.join(", ") : null,
  };
}

function formatResource(pool: ResourcePool): FormattedResource {
  return {
    key: pool.key,
    name: pool.name,
    maximum: pool.maximum,
    refresh: pool.refresh,
    rulesText: pool.rules_text ?? null,
  };
}

function formatPhase(phase: CreaturePhase): FormattedPhase {
  return {
    key: phase.key,
    name: phase.name,
    isDefault: phase.default,
    enabledElementKeys: phase.enabled_element_keys ?? [],
    disabledElementKeys: phase.disabled_element_keys ?? [],
    entryRulesText: phase.entry_rules_text ?? null,
  };
}

function formatLair(lair: LairProfile | null | undefined): FormattedLair | null {
  if (!lair) return null;
  return {
    name: lair.name ?? null,
    description: lair.description ?? null,
    initiativeCount: lair.initiative_count ?? null,
    initiativeTiebreak: lair.initiative_tiebreak ?? null,
    regionalRulesText: lair.regional_rules_text ?? null,
  };
}

function buildViewModelFromDefinition(
  definition: StatblockDefinitionV1_Output,
  metadata: {
    recordId: string;
    recordKind: "candidate" | "revision";
    contract: string;
    contractVersion: string;
    createdAt: string;
    expiresAt: string;
    validationReceipt: ValidationReceiptV1 | null | undefined;
    generation: StatblockViewModel["generation"];
  },
): StatblockViewModel {
  const identity = definition.identity;
  const subtypes = identity.subtypes?.length ? ` (${identity.subtypes.join(", ")})` : "";
  const identityLine = [
    identity.size,
    `${identity.creature_type}${subtypes}`,
    identity.alignment ?? null,
  ]
    .filter(Boolean)
    .join(", ");

  const acParts = definition.defenses.armor_classes.map((ac) => {
    const label = ac.label ? ` (${ac.label})` : "";
    const condition = ac.condition ? `; ${ac.condition}` : "";
    return `${ac.value}${label}${condition}`;
  });

  const speedParts = definition.movement.modes.map((mode) => {
    const distance = formatDistance(mode.distance);
    const qualifiers = mode.qualifiers?.length ? ` (${mode.qualifiers.join(", ")})` : "";
    return `${mode.mode} ${distance}${qualifiers}`.trim();
  });

  const senseParts = [
    ...(definition.senses.senses ?? []).map((sense) => {
      const range = "range" in sense && sense.range ? ` ${formatDistance(sense.range)}` : "";
      return `${sense.kind}${range}`;
    }),
    `passive Perception ${definition.senses.passive_perception}`,
  ];

  const languages = definition.communication.languages ?? [];
  const specialModes = definition.communication.special_modes ?? [];
  const languageParts = [
    ...languages,
    ...specialModes,
    definition.communication.telepathy_range
      ? `telepathy ${formatDistance(definition.communication.telepathy_range)}`
      : null,
  ].filter(Boolean) as string[];

  const { errors, warnings } = partitionIssues(metadata.validationReceipt);

  return {
    recordKind: metadata.recordKind,
    candidateId: metadata.recordId,
    contract: metadata.contract,
    contractVersion: metadata.contractVersion,
    createdAt: metadata.createdAt,
    expiresAt: metadata.expiresAt,
    identityLine,
    name: identity.name,
    armorClassSummary: acParts.length ? acParts.join("; ") : "—",
    hitPointsSummary: formatHitPoints(definition.vitality.hit_points),
    speedSummary: speedParts.length ? speedParts.join(", ") : "—",
    challengeSummary: `CR ${definition.challenge.rating} (PB ${formatModifier(definition.challenge.proficiency_bonus)})`,
    abilities: ABILITY_ORDER.map((ability) => ({
      ability,
      score: definition.abilities[ability],
      modifier: abilityModifier(definition.abilities[ability]),
      label: ABILITY_LABEL[ability],
    })),
    savingThrows:
      definition.proficiencies.saving_throws
        ?.map((entry) => `${entry.ability} ${formatModifier(entry.value)}`)
        .join(", ") || "—",
    skills:
      definition.proficiencies.skills
        ?.map((entry) => `${entry.skill} ${formatModifier(entry.value)}`)
        .join(", ") || "—",
    sensesSummary: senseParts.join(", "),
    languagesSummary: languageParts.length ? languageParts.join(", ") : "—",
    damageInteractions: (definition.defenses.damage_interactions ?? []).map(formatDamageInteraction),
    conditionImmunities: definition.defenses.condition_immunities ?? [],
    resources: (definition.resources ?? []).map(formatResource),
    phases: (definition.phases ?? []).map(formatPhase),
    lair: formatLair(definition.lair),
    flavorSummary: definition.flavor_text?.summary ?? definition.flavor_text?.description ?? null,
    ruleElements: definition.rule_elements.map(formatRuleElement),
    validation: metadata.validationReceipt
      ? {
          status: metadata.validationReceipt.status,
          digest: metadata.validationReceipt.definition_digest,
          errors,
          warnings,
        }
      : null,
    generation: metadata.generation,
  };
}

export function buildStatblockViewModel(
  source: GeneratedStatblockCandidateV1 | StatblockRevisionResourceV1,
  _mode: StatblockRenderMode = "review",
): StatblockViewModel {
  if ("candidate_id" in source) {
    return buildViewModelFromDefinition(source.definition, {
      recordId: source.candidate_id,
      recordKind: "candidate",
      contract: source.contract,
      contractVersion: source.contract_version,
      createdAt: source.created_at,
      expiresAt: source.expires_at,
      validationReceipt: source.validation_receipt,
      generation: source.generation_receipt
        ? {
            requestId: source.generation_receipt.request_id,
            provider: source.generation_receipt.provider,
            model: source.generation_receipt.model,
            generatedAt: source.generation_receipt.generated_at,
          }
        : null,
    });
  }

  return buildViewModelFromDefinition(source.definition, {
    recordId: source.revision_id,
    recordKind: "revision",
    contract: source.contract,
    contractVersion: source.contract_version,
    createdAt: source.created_at,
    expiresAt: "—",
    validationReceipt: source.validation_receipt,
    generation: null,
  });
}

export function groupRuleElementsBySection(
  elements: FormattedRuleElement[],
): Array<{ section: string; elements: FormattedRuleElement[] }> {
  const order: string[] = [];
  const map = new Map<string, FormattedRuleElement[]>();
  for (const element of elements) {
    if (!map.has(element.section)) {
      order.push(element.section);
      map.set(element.section, []);
    }
    map.get(element.section)!.push(element);
  }
  return order.map((section) => ({ section, elements: map.get(section)! }));
}
