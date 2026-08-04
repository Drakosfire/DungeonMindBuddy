import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import type {
  GeneratedStatblockCandidateV1,
  RuleElement_Output,
} from "../../contracts/dungeonbuddy-statblocks-v1/client";
import fixture from "../../../../../tests/fixtures/statblocks/v1/candidate-response.json";
import revisionFixture from "../../../../../tests/fixtures/statblocks/v1/exact-revision-response.json";
import { StatblockRenderer } from "./StatblockRenderer";
import { abilityModifier, buildStatblockViewModel, formatModifier } from "./statblockViewModel";
import type { StatblockRevisionResourceV1 } from "../../contracts/dungeonbuddy-statblocks-v1/client";

const candidate = fixture as GeneratedStatblockCandidateV1;
const revision = revisionFixture as StatblockRevisionResourceV1;
const baseElement = candidate.definition.rule_elements[0] as RuleElement_Output;

function withDefinition(
  overrides: Partial<GeneratedStatblockCandidateV1["definition"]>,
  elements?: RuleElement_Output[],
): GeneratedStatblockCandidateV1 {
  return {
    ...candidate,
    definition: {
      ...candidate.definition,
      ...overrides,
      rule_elements: elements ?? candidate.definition.rule_elements,
    },
  };
}

describe("statblockViewModel", () => {
  it("derives ability modifiers deterministically", () => {
    expect(abilityModifier(18)).toBe(4);
    expect(abilityModifier(8)).toBe(-1);
    expect(formatModifier(4)).toBe("+4");
  });

  it("maps structured definition fields without using Markdown", () => {
    const view = buildStatblockViewModel(candidate);
    expect(view.name).toBe("Ironhide Brute");
    expect(view.candidateId).toBe("cand_fixture1");
    expect(view.armorClassSummary).toContain("15");
    expect(view.hitPointsSummary).toContain("68");
    expect(view.speedSummary).toContain("walk");
    expect(view.ruleElements[0]?.key).toBe("greatclub");
    expect(view.ruleElements[0]?.rulesText).toContain("Melee Weapon Attack");
    expect(view.ruleElements[0]?.activation.kind).toBe("action");
    expect(view.ruleElements[0]?.usage.kind).toBe("at_will");
    expect(view.ruleElements[0]?.mechanicDetails.lines.some((line) => line.includes("Attack bonus"))).toBe(
      true,
    );
    expect(view.validation?.digest).toMatch(/^sha256:/);
  });

  it("projects defenses, resources, phases, and lair without dropping them", () => {
    const complex = withDefinition({
      defenses: {
        ...candidate.definition.defenses,
        damage_interactions: [
          {
            key: "fire_resist",
            kind: "resistance",
            damage_types: ["fire"],
            qualifiers: ["nonmagical"],
            bypasses: ["adamantine"],
          },
        ],
        condition_immunities: ["charmed", "frightened"],
      },
      resources: [
        {
          key: "legendary",
          name: "Legendary Resistance",
          maximum: 3,
          refresh: "long_rest",
          rules_text: "Expend to succeed a failed save.",
        },
      ],
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
      lair: {
        name: "Ironhold",
        description: "A slag-choked cavern.",
        initiative_count: 20,
        initiative_tiebreak: 0,
        regional_rules_text: "Ash clouds impose disadvantage on Perception.",
      },
    });
    const view = buildStatblockViewModel(complex);
    expect(view.damageInteractions[0]?.kind).toBe("resistance");
    expect(view.conditionImmunities).toEqual(["charmed", "frightened"]);
    expect(view.resources[0]?.name).toBe("Legendary Resistance");
    expect(view.phases[0]?.key).toBe("enraged");
    expect(view.lair?.name).toBe("Ironhold");
  });
});

describe("StatblockRenderer", () => {
  it("renders typed candidate mechanics and receipts", () => {
    render(<StatblockRenderer candidate={candidate} />);
    expect(screen.getByRole("heading", { name: "Ironhide Brute" })).toBeTruthy();
    expect(screen.getByText(/Candidate/)).toBeTruthy();
    expect(screen.getByText(/cand_fixture1/)).toBeTruthy();
    expect(screen.getByText("Greatclub")).toBeTruthy();
    expect(screen.getByText(/Melee Weapon Attack/)).toBeTruthy();
    expect(screen.getByText(/Attack bonus:/)).toBeTruthy();
    expect(screen.getByText(/Validation/)).toBeTruthy();
  });

  it("renders spellcasting groups, activation, usage, and costs", () => {
    const spellcasting: RuleElement_Output = {
      ...baseElement,
      key: "innate_spellcasting",
      name: "Innate Spellcasting",
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
            spells: [{ name: "Fear", school: "illusion", source_id: null, rules_text: null }],
          },
        ],
      },
    };
    render(<StatblockRenderer candidate={withDefinition({}, [spellcasting])} />);
    expect(screen.getByText("Innate Spellcasting")).toBeTruthy();
    expect(screen.getByText(/Casting mode: innate/)).toBeTruthy();
    expect(screen.getByText(/Save DC: 13/)).toBeTruthy();
    expect(screen.getByText(/Group L3/)).toBeTruthy();
    expect(screen.getByText(/Fear/)).toBeTruthy();
    expect(screen.getByText(/1× spell_charge/)).toBeTruthy();
  });

  it("renders legendary/lair structured regions", () => {
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
    render(
      <StatblockRenderer
        candidate={withDefinition(
          {
            lair: {
              name: "Ironhold",
              description: "A slag-choked cavern.",
              initiative_count: 20,
              initiative_tiebreak: 0,
              regional_rules_text: "Ash clouds impose disadvantage on Perception.",
            },
            defenses: {
              ...candidate.definition.defenses,
              damage_interactions: [
                {
                  key: "bludgeoning_resist",
                  kind: "resistance",
                  damage_types: ["bludgeoning"],
                  qualifiers: [],
                  bypasses: [],
                },
              ],
              condition_immunities: ["frightened"],
            },
            resources: [
              {
                key: "legendary",
                name: "Legendary Resistance",
                maximum: 3,
                refresh: "long_rest",
                rules_text: null,
              },
            ],
          },
          [lairAction],
        )}
      />,
    );
    expect(screen.getByText("Collapse Ceiling")).toBeTruthy();
    expect(screen.getByText(/Save: dexterity DC 14/)).toBeTruthy();
    expect(screen.getByText(/Condition immunities: frightened/)).toBeTruthy();
    expect(screen.getByText(/Legendary Resistance/)).toBeTruthy();
    expect(screen.getByText("Ironhold")).toBeTruthy();
    expect(screen.getByText(/Ash clouds impose disadvantage/)).toBeTruthy();
    expect(document.querySelector('[data-region="damage-interactions"]')?.textContent).toMatch(
      /resistance/i,
    );
  });

  it("renders phased creatures and phase transitions", () => {
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
        effects: [],
      },
    };
    render(
      <StatblockRenderer
        candidate={withDefinition(
          {
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
          },
          [transition],
        )}
      />,
    );
    expect(screen.getByText("Enter Enraged")).toBeTruthy();
    expect(screen.getByText(/Destination phase: enraged/)).toBeTruthy();
    expect(document.querySelector('[data-region="phases"]')?.textContent).toMatch(/Enraged/);
    expect(screen.getByText(/enables frenzy/)).toBeTruthy();
  });

  it("labels human-adjudicated elements", () => {
    const humanCandidate = withDefinition({}, [
      {
        ...baseElement,
        key: "lair_pressure",
        name: "Lair Pressure",
        section: "trait",
        rules_text: "The GM decides when the pressure escalates.",
        automation_support: "manual",
        mechanic: {
          kind: "human_adjudicated",
          adjudication_tags: ["table_judgment"],
        },
      },
    ]);
    render(<StatblockRenderer candidate={humanCandidate} />);
    expect(screen.getByText("Human adjudicated")).toBeTruthy();
    expect(screen.getByText(/Adjudication tags: table_judgment/)).toBeTruthy();
  });

  it("marks unknown mechanic kinds as unsupported instead of dropping them", () => {
    const unknown = withDefinition({}, [
      {
        ...baseElement,
        key: "weird_pulse",
        name: "Weird Pulse",
        section: "trait",
        rules_text: "An unfamiliar pulse ripples outward.",
        mechanic: { kind: "totally_new_kind" } as unknown as RuleElement_Output["mechanic"],
      },
    ]);
    render(<StatblockRenderer candidate={unknown} />);
    expect(screen.getByText("Weird Pulse")).toBeTruthy();
    expect(screen.getByText("Unsupported mechanic")).toBeTruthy();
    expect(screen.getByText(/An unfamiliar pulse ripples outward/)).toBeTruthy();
  });

  it("renders exact StatblockRevisionResourceV1 through the shared renderer", () => {
    render(<StatblockRenderer revision={revision} mode="summary" />);
    expect(screen.getByRole("heading", { name: "Ironhide Brute" })).toBeTruthy();
    expect(screen.getByText(/Revision/)).toBeTruthy();
    expect(screen.getByText("Armor Class")).toBeTruthy();
    expect(screen.getByText("15 (natural armor)")).toBeTruthy();
  });
});
