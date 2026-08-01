import type { Distance, MovementModeKind, StatblockDefinitionV1_Output } from "./client";

export type CombatMinimums = {
  name: string;
  armor_class: number;
  hit_points: number | null;
  hit_point_formula: { count: number; die: number; modifier?: number } | null;
  challenge_rating: string;
  proficiency_bonus: number;
  speed: Array<{ mode: MovementModeKind; distance: Distance }>;
  human_adjudicated_elements: string[];
};

/** DungeonBuddy-owned combat summary projection from an exact revision definition. */
export function combatMinimums(definition: StatblockDefinitionV1_Output): CombatMinimums {
  const armor =
    definition.defenses.armor_classes.find((profile) => profile.default) ??
    definition.defenses.armor_classes[0];
  const hp = definition.vitality.hit_points;
  return {
    name: definition.identity.name,
    armor_class: armor.value,
    hit_points: hp.displayed_average ?? hp.fixed_value ?? null,
    hit_point_formula: hp.formula ?? null,
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
