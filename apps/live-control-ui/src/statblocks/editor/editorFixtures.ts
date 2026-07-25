import type {
  AttackMechanic_Output,
  GeneratedStatblockCandidateV1,
  RuleElement_Output,
  StatblockDefinitionV1_Output,
} from "../../contracts/dungeonbuddy-statblocks-v1/client";
import fixture from "../../../../../tests/fixtures/statblocks/v1/candidate-response.json";

const candidate = fixture as GeneratedStatblockCandidateV1;

export function baseCandidateDefinition(): StatblockDefinitionV1_Output {
  return structuredClone(candidate.definition);
}

/** Base definition with explicit `lair: null` for clone parity tests. */
export function baseCandidateDefinitionWithNullLair(): StatblockDefinitionV1_Output {
  const base = baseCandidateDefinition();
  return { ...base, lair: null };
}

export function complexCandidateDefinition(): StatblockDefinitionV1_Output {
  const base = baseCandidateDefinition();
  const baseElement = base.rule_elements[0] as RuleElement_Output;

  const spellcasting: RuleElement_Output = {
    ...baseElement,
    key: "innate_spellcasting",
    name: "Innate Spellcasting",
    summary: "Innate casting",
    section: "trait",
    rules_text: "The brute's innate spellcasting ability is Charisma.",
    activation: { kind: "special", timing_text: null, trigger: null },
    usage: { kind: "at_will", recharge_range: null, refresh_text: null, resource_key: null, uses: null },
    costs: [{ resource_key: "spell_charge", amount: 1 }],
    mechanic: {
      kind: "spellcasting",
      casting_mode: "innate",
      ability: "charisma",
      save_dc: 13,
      attack_bonus: 5,
      caster_level: 5,
      groups: [
        {
          usage: {
            kind: "per_day",
            uses: 1,
            recharge_range: null,
            refresh_text: null,
            resource_key: null,
          },
          level: 3,
          slots: 1,
          spells: [
            { name: "Fear", school: "illusion", source_id: null, rules_text: null },
            { name: "Fireball", school: "evocation", source_id: null, rules_text: null },
          ],
        },
      ],
    },
  };

  const lairAction: RuleElement_Output = {
    ...baseElement,
    key: "collapse_ceiling",
    name: "Collapse Ceiling",
    section: "lair_action",
    rules_text: "Debris falls in a 10-foot radius.",
    activation: { kind: "lair_initiative", timing_text: "initiative 20", trigger: null },
    usage: { kind: "per_round", uses: 1, recharge_range: null, refresh_text: null, resource_key: null },
    costs: [],
    mechanic: {
      kind: "save_effect",
      save: { ability: "dexterity", dc: 14 },
      target: { kind: "area", count: null, area: "10-foot radius", qualifiers: [], range: null },
      failure_effects: [],
      success_effects: [],
    },
  };

  const transition: RuleElement_Output = {
    ...baseElement,
    key: "enter_enraged",
    name: "Enter Enraged",
    section: "trait",
    rules_text: "The brute enters its enraged phase.",
    activation: {
      kind: "triggered",
      timing_text: null,
      trigger: { kind: "hp_threshold", source_element_key: null, condition_text: "below half HP" },
    },
    usage: { kind: "once", uses: 1, recharge_range: null, refresh_text: null, resource_key: null },
    costs: [],
    mechanic: {
      kind: "phase_transition",
      destination_phase_key: "enraged",
      effects: [
        { kind: "enable_elements", element_keys: ["frenzy"] },
        { kind: "disable_elements", element_keys: ["greatclub"] },
      ],
    },
  };

  const humanAdjudicated: RuleElement_Output = {
    ...baseElement,
    key: "lair_pressure",
    name: "Lair Pressure",
    section: "trait",
    rules_text: "The GM decides when the pressure escalates.",
    automation_support: "manual",
    tags: ["lair", "pressure"],
    mechanic: {
      kind: "human_adjudicated",
      adjudication_tags: ["table_judgment"],
    },
  };

  const attackMechanic = baseElement.mechanic as AttackMechanic_Output;
  const nestedAttack: RuleElement_Output = {
    ...baseElement,
    mechanic: {
      ...attackMechanic,
      kind: "attack",
      hit_effects: [
        ...(attackMechanic.hit_effects ?? []),
        {
          kind: "human_adjudicated",
          adjudication_text: "GM may rule extra knockback on a crit.",
        },
      ],
      miss_effects: [
        {
          kind: "enable_elements",
          element_keys: ["opening"],
        },
      ],
    },
  };

  const omittedKindEffectElement: RuleElement_Output = {
    ...baseElement,
    key: "wild_surge",
    name: "Wild Surge",
    section: "trait",
    rules_text: "Surges of wild magic.",
    mechanic: {
      kind: "composite",
      target: null,
      effects: [
        {
          condition: "frightened",
          duration: null,
        },
      ],
    },
  };

  return {
    ...base,
    lair: {
      name: "Ironhold",
      description: "A slag-choked cavern.",
      initiative_count: 20,
      initiative_tiebreak: 0,
      regional_rules_text: "Ash clouds impose disadvantage on Perception.",
    },
    phases: [
      {
        key: "enraged",
        name: "Enraged",
        default: false,
        enabled_element_keys: ["frenzy"],
        disabled_element_keys: ["greatclub"],
        entry_rules_text: "Enter when reduced below half HP.",
      },
    ],
    resources: [
      {
        key: "legendary",
        name: "Legendary Resistance",
        maximum: 3,
        refresh: "long_rest",
        rules_text: "Expend to succeed a failed save.",
      },
    ],
    rule_elements: [
      nestedAttack,
      spellcasting,
      lairAction,
      transition,
      humanAdjudicated,
      omittedKindEffectElement,
    ],
  };
}
