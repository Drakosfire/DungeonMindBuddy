import type {CombatEncounterDraft} from './combatTypes';

export function stepCombatTurn(current: CombatEncounterDraft, direction: "next" | "previous"): CombatEncounterDraft {
  const living = current.entities.filter((entity) => !entity.defeated);
  if (living.length === 0) return current;
  const activeIndex = living.findIndex((entity) => entity.id === current.active_turn_entity_id);
  if (activeIndex < 0) {
    return {
      ...current,
      active_turn_entity_id: living[0]?.id ?? null,
      round_start_entity_id: current.round_start_entity_id ?? living[0]?.id ?? null,
    };
  }
  const from = activeIndex;
  const nextIndex = (from + (direction === "next" ? 1 : living.length - 1)) % living.length;
  const anchorIndex = current.entities.findIndex(entity => entity.id === current.round_start_entity_id);
  const anchoredOrder = anchorIndex < 0 ? current.entities
    : [...current.entities.slice(anchorIndex), ...current.entities.slice(0, anchorIndex)];
  const roundStart = anchoredOrder.find(entity => !entity.defeated)?.id;
  const wrapped = direction === "next" ? living[nextIndex]?.id === roundStart : living[from]?.id === roundStart;
  return {
    ...current,
    active_turn_entity_id: living[nextIndex]?.id ?? null,
    round: Math.max(1, current.round + (wrapped ? (direction === "next" ? 1 : -1) : 0)),
    round_start_entity_id: current.round_start_entity_id ?? living[0]?.id ?? null,
  };
}
