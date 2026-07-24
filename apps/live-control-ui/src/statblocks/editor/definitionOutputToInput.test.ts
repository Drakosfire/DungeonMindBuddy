import { describe, expect, it } from "vitest";

import type { StatblockDefinitionV1_Output } from "../../contracts/dungeonbuddy-statblocks-v1/client";
import { baseCandidateDefinition, complexCandidateDefinition } from "./editorFixtures";
import { definitionOutputToInput } from "./definitionOutputToInput";

describe("definitionOutputToInput", () => {
  it("maps the base fixture completely without mutating the source output", () => {
    const output = baseCandidateDefinition();
    const snapshot = structuredClone(output);
    const input = definitionOutputToInput(output);

    expect(input.identity.name).toBe(output.identity.name);
    expect(input.rule_elements).toHaveLength(output.rule_elements.length);
    expect(input.vitality.hit_points.displayed_average).toBe(output.vitality.hit_points.displayed_average);

    input.identity.name = "Mutated";
    input.rule_elements[0].name = "Changed";
    expect(output.identity.name).toBe(snapshot.identity.name);
    expect(output.rule_elements[0].name).toBe(snapshot.rule_elements[0].name);
  });

  it("preserves untouched fields after a targeted identity rename in working copy flow", () => {
    const output = baseCandidateDefinition();
    const input = definitionOutputToInput(output);
    const before = structuredClone(input);
    input.identity.name = "Renamed Brute";
    expect(input.movement).toEqual(before.movement);
    expect(input.rule_elements[0].mechanic).toEqual(before.rule_elements[0].mechanic);
    expect(input.defenses).toEqual(before.defenses);
  });

  it("retains spellcasting, lair, phases, human adjudicated, and nested hit effects", () => {
    const output = complexCandidateDefinition();
    const input = definitionOutputToInput(output);

    const spellcasting = input.rule_elements.find((element) => element.key === "innate_spellcasting");
    expect(spellcasting?.mechanic).toMatchObject({ kind: "spellcasting", casting_mode: "innate" });
    expect(
      spellcasting && "groups" in spellcasting.mechanic ? spellcasting.mechanic.groups[0]?.spells[0]?.name : null,
    ).toBe("Fear");

    expect(input.lair?.name).toBe("Ironhold");
    expect(input.phases?.[0]?.key).toBe("enraged");

    const human = input.rule_elements.find((element) => element.key === "lair_pressure");
    expect(human?.mechanic).toMatchObject({ kind: "human_adjudicated", adjudication_tags: ["table_judgment"] });

    const attack = input.rule_elements.find((element) => element.key === "greatclub");
    expect(attack && "hit_effects" in attack.mechanic ? attack.mechanic.hit_effects?.length : 0).toBeGreaterThan(1);
  });

  it("round-trips complex output into input with structural parity on definition body", () => {
    const output: StatblockDefinitionV1_Output = complexCandidateDefinition();
    const input = definitionOutputToInput(output);
    expect(input).toEqual(output);
  });
});
