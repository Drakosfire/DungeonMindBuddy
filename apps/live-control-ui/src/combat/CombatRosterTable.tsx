import type {ReactNode} from 'react';
import type {CombatEncounterDraft, CombatEntity, CombatGroup} from './combatTypes';

/** Presentation segments preserve the saved order; grouping never moves an actor. */
function segments(entities: CombatEntity[], groups: CombatGroup[]) {
  const result: {group: CombatGroup | undefined; entities: CombatEntity[]}[] = [];
  for (const entity of entities) {
    const group = groups.find(item => item.member_ids.includes(entity.id));
    const last = result[result.length - 1];
    if (group && last?.group === group) last.entities.push(entity);
    else result.push({group, entities: [entity]});
  }
  return result;
}

export function CombatRosterTable({draft, disabled, onToggleGroup, renderRow}: {
  draft: CombatEncounterDraft;
  disabled: boolean;
  onToggleGroup: (key: string) => void;
  renderRow: (entity: CombatEntity, hidden: boolean) => ReactNode;
}) {
  const participating = draft.entities.filter(entity => !entity.defeated);
  const defeated = draft.entities.filter(entity => entity.defeated);
  return <div className="combat-roster-table-wrap" tabIndex={0} role="region" aria-label="Encounter roster">
    <table role="table" className="combat-roster-table">
      <caption className="combat-roster-caption">{participating.length} in action · {defeated.length} defeated</caption>
      <thead><tr><th scope="col">Init</th><th scope="col">Participant</th><th scope="col">AC</th><th scope="col">HP</th><th scope="col"><span className="sr-only">Adjust HP</span></th><th scope="col">Conditions</th><th scope="col">Notes</th><th scope="col"><span className="sr-only">Actions</span></th></tr></thead>
      <tbody role="rowgroup">
      {[
      ...segments(participating, draft.groups).flatMap(segment => {
        const {group, entities} = segment;
        // The active participant remains visible even when its group was collapsed.
        const active = entities.some(entity => entity.id === draft.active_turn_entity_id);
        const expanded = !group?.collapsed || active;
        return [
          group && <tr role="row" key={`group:${group.group_key}:${entities[0].id}`} className="combat-roster-group"><th role="cell" colSpan={8}>
            <button type="button" aria-expanded={expanded} disabled={disabled || active}
              onClick={() => onToggleGroup(group.group_key)}>
              {expanded ? '▾' : '▸'} {group.label} · {entities.length}{active ? ' · current actor' : ''}
            </button>
          </th></tr>,
          ...entities.map(entity => renderRow(entity, !expanded)),
        ];
      }),
      defeated.length > 0 && <tr role="row" key="defeated-heading" className="combat-roster-group"><th role="cell" colSpan={8}>Out of action · {defeated.length} defeated</th></tr>,
      ...defeated.map(entity => renderRow(entity, false)),
      ]}
      </tbody>
    </table>
  </div>;
}
