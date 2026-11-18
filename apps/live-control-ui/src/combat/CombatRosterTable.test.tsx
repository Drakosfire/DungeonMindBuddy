import {cleanup, render, screen} from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import {afterEach, expect, it, vi} from 'vitest';
import {CombatRosterTable} from './CombatRosterTable';
import type {CombatEncounterDraft, CombatEntity} from './combatTypes';

afterEach(cleanup);
const actor = (id: string, defeated = false) => ({id, name: id, defeated}) as CombatEntity;
function draft(): CombatEncounterDraft {
  return {schema:'dmb_combat_encounter_draft_v1', title:'Patrol', round:1,
    active_turn_entity_id:'a', round_start_entity_id:'a', queue_model:'circular_barrel_v1',
    entities:[actor('a'),actor('b'),actor('c'),actor('d',true)], provenance:[],
    groups:[{group_key:'patrol',label:'Patrol',statblock_path:null,member_ids:['a','c','d'],collapsed:true}]};
}
const row = (entity: CombatEntity, hidden: boolean) => <tr key={entity.id} hidden={hidden}><td colSpan={8}>{entity.name}</td></tr>;

it('preserves order across noncontiguous groups and keeps the current actor visible', () => {
  render(<CombatRosterTable draft={draft()} disabled={false} onToggleGroup={vi.fn()} renderRow={row}/>);
  expect(screen.getByRole('row',{name:'a'})).toBeInTheDocument();
  expect(screen.getByRole('row',{name:'b'})).toBeInTheDocument();
  expect(screen.queryByRole('row',{name:'c'})).toBeNull();
  expect(screen.getByRole('row',{name:'d'})).toBeInTheDocument();
  expect(screen.getByRole('button',{name:/current actor/})).toBeDisabled();
  expect(screen.getByText('3 in action · 1 defeated')).toBeInTheDocument();
});

it('requests persisted collapse changes without moving or rewriting actors', async () => {
  const onToggleGroup = vi.fn(), initial = draft();
  const view = render(<CombatRosterTable draft={initial} disabled={false} onToggleGroup={onToggleGroup} renderRow={row}/>);
  await userEvent.click(screen.getByRole('button',{name:'▸ Patrol · 1'}));
  expect(onToggleGroup).toHaveBeenCalledWith('patrol');
  expect(initial.entities.map(entity=>entity.id)).toEqual(['a','b','c','d']);
  view.rerender(<CombatRosterTable draft={{...initial, groups:initial.groups.map(group=>({...group,collapsed:false}))}} disabled={false} onToggleGroup={onToggleGroup} renderRow={row}/>);
  expect(screen.getAllByRole('row').map(item=>item.textContent).filter(text=>['a','b','c','d'].includes(text??''))).toEqual(['a','b','c','d']);
});
