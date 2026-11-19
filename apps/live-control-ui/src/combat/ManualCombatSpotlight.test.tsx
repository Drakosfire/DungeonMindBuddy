import {afterEach,beforeEach,expect,it,vi} from 'vitest';
import {cleanup,fireEvent,render,screen,waitFor,within} from '@testing-library/react';
import {spotlightCombatRecord} from './ManualCombat.testSupport';
import {advanceManualTurn,removeManualActor,selectManualSpotlight,setManualParticipation} from './ManualCombatState';
import {validManualDraft} from './validateCombatRecovery';
import {ManualCombatEditor} from './ManualCombatEditor';
import {ManualCombatProfileForm} from './ManualCombatProfileForm';
import {testCombatLocks} from './combatRecovery.testSupport';
import {combatRecoveryKey} from './combatRecovery';

beforeEach(()=>{localStorage.clear();Object.defineProperty(navigator,'locks',{configurable:true,value:testCombatLocks()});});
afterEach(()=>{cleanup();vi.restoreAllMocks();});

it('selects freely and finishes without deriving an order, side, round or turn budget',()=>{
  const record=spotlightCombatRecord(),id=record.draft.entities[1].id;
  const active=selectManualSpotlight(record.draft,id);
  expect(active.turn).toEqual({kind:'spotlight',active_actor_id:id});expect(validManualDraft(record,active)).toBe(true);
  expect(record.draft.turn.active_actor_id).toBeNull();
  expect(selectManualSpotlight(active,null).turn).toEqual(record.draft.turn);
  expect(()=>advanceManualTurn(active)).toThrow('explicitly');
  expect(selectManualSpotlight({...active,entities:[...active.entities].reverse()},id).turn).toEqual(active.turn);
});

it('clears an active defeated or removed participant without advancing or changing values on return',()=>{
  const record=spotlightCombatRecord(),id=record.draft.entities[1].id;
  const active=selectManualSpotlight(record.draft,id),out=setManualParticipation(active,id,'out_of_action');
  expect(out.turn.active_actor_id).toBeNull();
  expect(setManualParticipation(out,id,'in_action').turn.active_actor_id).toBeNull();
  expect(out.entities[1].values).toEqual(active.entities[1].values);
  expect(removeManualActor(active,id).turn.active_actor_id).toBeNull();
  expect(()=>selectManualSpotlight(out,id)).toThrow('in-action');
  expect(()=>selectManualSpotlight(active,'foreign')).toThrow('in-action');
});

it('refuses recovery with another turn kind or a missing/out-of-action spotlight',()=>{
  const record=spotlightCombatRecord(),id=record.draft.entities[0].id;
  expect(validManualDraft(record,{...record.draft,turn:{kind:'ordered',active_actor_id:null}})).toBe(false);
  expect(validManualDraft(record,{...record.draft,turn:{kind:'spotlight',active_actor_id:'foreign'}})).toBe(false);
  const active=selectManualSpotlight(record.draft,id);active.entities=active.entities.map(actor=>({...actor,participation:'out_of_action'}));
  expect(validManualDraft(record,active)).toBe(false);
});

it('creates free spotlight explicitly and drops an ordered round counter',async()=>{
  const create=vi.fn().mockResolvedValue(undefined);render(<ManualCombatProfileForm disabled={false} onCreate={create}/>);
  fireEvent.click(screen.getByText('Create for another system'));fireEvent.click(screen.getByLabelText('Count rounds'));
  fireEvent.change(screen.getByLabelText('Turn structure'),{target:{value:'spotlight'}});
  expect(screen.queryByLabelText('Count rounds')).toBeNull();
  fireEvent.click(screen.getByRole('button',{name:'Create manual encounter'}));
  await waitFor(()=>expect(create).toHaveBeenCalledTimes(1));expect(create.mock.calls[0][1].pacing).toEqual({mode:'spotlight',rounds:false});
});

it('selects hidden grouped members through the shared rail and retains explicit Finish and defeat transitions',async()=>{
  const record=spotlightCombatRecord(),id=record.draft.entities[1].id;
  record.draft.groups=[{id:'group',label:'Crew group',member_ids:record.draft.entities.map(actor=>actor.id),collapsed:true}];
  render(<ManualCombatEditor record={record} onSaved={()=>{}} onBlocked={()=>{}}/>);
  await waitFor(()=>expect(screen.getByLabelText('Spotlight participant')).not.toBeDisabled());
  expect(screen.queryByRole('button',{name:'Next turn'})).toBeNull();
  expect(screen.queryByRole('row',{name:'Guide'})).toBeNull();
  fireEvent.change(screen.getByLabelText('Spotlight participant'),{target:{value:id}});
  expect(screen.getByRole('row',{name:'Guide'})).toBeVisible();
  fireEvent.click(screen.getByRole('button',{name:'Finish spotlight',exact:true}));
  expect(screen.queryByRole('row',{name:'Guide'})).toBeNull();
  fireEvent.change(screen.getByLabelText('Spotlight participant'),{target:{value:id}});
  fireEvent.click(within(screen.getByRole('row',{name:'Guide'})).getByRole('button',{name:'Take out of action'}));
  expect((screen.getByLabelText('Spotlight participant') as HTMLSelectElement).value).toBe('');
  const raw=JSON.parse(localStorage.getItem(combatRecoveryKey(record.world_id,record.encounter_id))!);
  expect(raw.draft.turn).toEqual({kind:'spotlight',active_actor_id:null});expect(raw.draft.entities[1].participation).toBe('out_of_action');
  fireEvent.click(screen.getByRole('button',{name:'Crew group · 2 participants'}));
  fireEvent.click(within(screen.getByRole('row',{name:'Guide'})).getByRole('button',{name:'Return to action'}));
  expect((screen.getByLabelText('Spotlight participant') as HTMLSelectElement).value).toBe('');
});
