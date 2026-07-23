import type {
  AbilityScores,
  GeneratedStatblockCandidateV1,
  HitPointProfile,
  RuleElement_Output,
  StatblockDefinitionV1_Output,
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
};

export type StatblockViewModel = {
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

function formatRuleElement(element: RuleElement_Output): FormattedRuleElement {
  const kind = mechanicKind(element.mechanic);
  const humanAdjudicated = kind === "human_adjudicated";
  const knownKinds = new Set([
    "attack",
    "save_effect",
    "multiattack",
    "spellcasting",
    "passive",
    "composite",
    "phase_transition",
    "human_adjudicated",
  ]);
  return {
    key: element.key,
    name: element.name,
    section: element.section,
    rulesText: element.rules_text,
    summary: element.summary ?? null,
    automationSupport: element.automation_support,
    mechanicKind: kind,
    humanAdjudicated,
    unsupportedMechanic: !knownKinds.has(kind),
  };
}

export function buildStatblockViewModel(
  candidate: GeneratedStatblockCandidateV1,
  _mode: StatblockRenderMode = "review",
): StatblockViewModel {
  const definition: StatblockDefinitionV1_Output = candidate.definition;
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

  const { errors, warnings } = partitionIssues(candidate.validation_receipt);

  return {
    candidateId: candidate.candidate_id,
    contract: candidate.contract,
    contractVersion: candidate.contract_version,
    createdAt: candidate.created_at,
    expiresAt: candidate.expires_at,
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
    flavorSummary: definition.flavor_text?.summary ?? definition.flavor_text?.description ?? null,
    ruleElements: definition.rule_elements.map(formatRuleElement),
    validation: candidate.validation_receipt
      ? {
          status: candidate.validation_receipt.status,
          digest: candidate.validation_receipt.definition_digest,
          errors,
          warnings,
        }
      : null,
    generation: candidate.generation_receipt
      ? {
          requestId: candidate.generation_receipt.request_id,
          provider: candidate.generation_receipt.provider,
          model: candidate.generation_receipt.model,
          generatedAt: candidate.generation_receipt.generated_at,
        }
      : null,
  };
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
