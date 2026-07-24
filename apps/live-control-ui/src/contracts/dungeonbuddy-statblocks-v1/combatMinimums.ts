import type { StatblockDefinitionV1_Output } from "./client";

export type CombatMinimums = {
  name: string;
  armor_class: number;
  hit_points: number | null;
  hit_point_formula: { count: number; die: number; modifier?: number } | null;
  challenge_rating: string;
  proficiency_bonus: number;
  speed: Array<{ mode: string; distance: { value: number; unit: string } }>;
  human_adjudicated_elements: string[];
};

/** DungeonBuddy-owned combat summary projection from an exact revision definition. */
export function combatMinimums(definition: StatblockDefinitionV1_Output): CombatMinimums {
  const armor = definition.defenses.default_armor_class;
  const hp = definition.vitality.hit_points;
  const hitPoints =
    hp.displayed_average ??
    (hp.method === "fixed" ? hp.fixed_value : null) ??
    null;
  const hitPointFormula = hp.method === "formula" ? hp.formula : null;
  return {
    name: definition.identity.name,
    armor_class: armor.value,
    hit_points: hitPoints,
    hit_point_formula: hitPointFormula,
    challenge_rating: definition.challenge.rating,
    proficiency_bonus: definition.challenge.proficiency_bonus,
    speed: definition.movement.modes.map((mode) => ({
      mode: mode.mode,
      distance: mode.distance,
    })),
    human_adjudicated_elements: definition.rule_elements
      .filter((element) => element.mechanic.kind === "human_adjudicated")
      .map((element) => element.key),
  };
}
