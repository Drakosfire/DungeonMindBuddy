import { describe, expect, it } from "vitest";

import type { StatblockDefinitionV1_Output } from "../../contracts/dungeonbuddy-statblocks-v1/client";
import {
  baseCandidateDefinition,
  baseCandidateDefinitionWithNullLair,
  complexCandidateDefinition,
} from "./editorFixtures";
import { definitionOutputToInput } from "./definitionOutputToInput";

describe("definitionOutputToInput", () => {
  it("deep-clones base candidate Output to Input with equality", () => {
    const output = baseCandidateDefinition();
    const input = definitionOutputToInput(output);
    expect(input).toEqual(output);
  });

  it("deep-clones complex candidate Output to Input with equality", () => {
    const output = complexCandidateDefinition();
    const input = definitionOutputToInput(output);
    expect(input).toEqual(output);
  });

  it("does not mutate source output when working copy is edited", () => {
    const output = baseCandidateDefinition();
    const snapshot = structuredClone(output);
    const input = definitionOutputToInput(output);

    input.identity.name = "Mutated";
    input.rule_elements[0].name = "Changed";
    expect(output).toEqual(snapshot);
  });

  it("preserves omitted optional fields (no spurious keys)", () => {
    const output = complexCandidateDefinition();
    const input = definitionOutputToInput(output);
    const wildSurge = input.rule_elements.find((element) => element.key === "wild_surge");
    expect(wildSurge).toBeDefined();
    const composite = wildSurge!.mechanic;
    expect(composite.kind).toBe("composite");
    const effect = composite.kind === "composite" ? composite.effects?.[0] : undefined;
    expect(effect).toBeDefined();
    expect(Object.prototype.hasOwnProperty.call(effect, "kind")).toBe(false);
  });

  it("preserves explicit null lair", () => {
    const output = baseCandidateDefinitionWithNullLair();
    const input = definitionOutputToInput(output);
    expect(input.lair).toBeNull();
    expect(output.lair).toBeNull();
  });

  it("preserves enable_elements and disable_elements effect shapes", () => {
    const output = complexCandidateDefinition();
    const input = definitionOutputToInput(output);

    const transition = input.rule_elements.find((element) => element.key === "enter_enraged");
    expect(transition?.mechanic).toMatchObject({ kind: "phase_transition" });
    const effects =
      transition && transition.mechanic.kind === "phase_transition" ? transition.mechanic.effects : [];
    expect(effects?.[0]).toEqual({ kind: "enable_elements", element_keys: ["frenzy"] });
    expect(effects?.[1]).toEqual({ kind: "disable_elements", element_keys: ["greatclub"] });

    const attack = input.rule_elements.find((element) => element.key === "greatclub");
    const miss =
      attack && attack.mechanic.kind === "attack" ? attack.mechanic.miss_effects?.[0] : undefined;
    expect(miss).toEqual({ kind: "enable_elements", element_keys: ["opening"] });
  });

  it("preserves spellcasting, lair, phases, human adjudicated, and nested hit effects", () => {
    const output = complexCandidateDefinition();
    const input = definitionOutputToInput(output);

    const spellcasting = input.rule_elements.find((element) => element.key === "innate_spellcasting");
    expect(spellcasting?.mechanic).toMatchObject({ kind: "spellcasting", casting_mode: "innate" });
    expect(
      spellcasting && spellcasting.mechanic.kind === "spellcasting"
        ? spellcasting.mechanic.groups[0]?.spells.map((spell) => spell.name)
        : [],
    ).toEqual(["Fear", "Fireball"]);

    expect(input.lair?.name).toBe("Ironhold");
    expect(input.phases?.[0]?.key).toBe("enraged");

    const human = input.rule_elements.find((element) => element.key === "lair_pressure");
    expect(human?.mechanic).toMatchObject({
      kind: "human_adjudicated",
      adjudication_tags: ["table_judgment"],
    });

    const attack = input.rule_elements.find((element) => element.key === "greatclub");
    expect(attack && attack.mechanic.kind === "attack" ? attack.mechanic.hit_effects?.length : 0).toBeGreaterThan(
      1,
    );
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

  it("accepts arbitrary Output assignable bodies", () => {
    const output: StatblockDefinitionV1_Output = complexCandidateDefinition();
    const input = definitionOutputToInput(output);
    expect(input).toEqual(output);
  });
});
