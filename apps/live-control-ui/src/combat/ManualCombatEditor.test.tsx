import {afterEach,beforeEach,expect,it,vi} from 'vitest';
import {act,cleanup,fireEvent,render,screen,waitFor,within} from '@testing-library/react';
import {ManualCombatEditor} from './ManualCombatEditor';
import {ManualCombatProfileForm} from './ManualCombatProfileForm';
import {manualCombatRecord,sideCombatRecord} from './ManualCombat.testSupport';
import {testCombatLocks} from './combatRecovery.testSupport';
import * as api from './combatApi';
import {combatRecoveryKey} from './combatRecovery';
import type {ManualCombatRecord} from './ManualCombatTypes';
import {newManualActor} from './ManualCombatState';
import exactSource from '../../../../tests/fixtures/statblocks/v1/exact-revision-response.json';
import type {AcceptedCombatMechanicsSnapshot} from './combatTypes';

beforeEach(()=>{localStorage.clear();Object.defineProperty(navigator,'locks',{configurable:true,value:testCombatLocks()});});
afterEach(()=>{cleanup();vi.restoreAllMocks();});
async function open(record=manualCombatRecord()) {
  const saved=vi.fn();render(<ManualCombatEditor record={record} onSaved={saved} onBlocked={()=>{}}/>);
  await waitFor(()=>expect((screen.getByLabelText('Stress current for Crew') as HTMLInputElement).disabled).toBe(false));
  return {record,saved};
}

it('creates a side profile explicitly without carrying an ordered round counter',async()=>{
  const create=vi.fn().mockResolvedValue(undefined);
  render(<ManualCombatProfileForm disabled={false} onCreate={create}/>);
  fireEvent.click(screen.getByText('Create for another system'));
  fireEvent.click(screen.getByLabelText('Count rounds'));
  fireEvent.change(screen.getByLabelText('Turn structure'),{target:{value:'side'}});
  expect(screen.queryByLabelText('Count rounds')).toBeNull();
  fireEvent.click(screen.getByRole('button',{name:'Create manual encounter'}));
  await waitFor(()=>expect(create).toHaveBeenCalledTimes(1));
  expect(create.mock.calls[0][1].pacing).toEqual({mode:'side',rounds:false});
  expect(create.mock.calls[0][1].stats.map((field:{label:string})=>field.label)).toEqual(['Position','Resolve']);
});

it('runs side turns through the shared editor, including empty sides and retained finished markers',async()=>{
  const record=sideCombatRecord();await open(record);
  expect(screen.queryByRole('button',{name:'Next turn'})).toBeNull();
  fireEvent.click(screen.getByRole('button',{name:'Start side turns'}));
  fireEvent.click(screen.getByRole('button',{name:'Act now with Crew'}));
  fireEvent.click(screen.getByRole('button',{name:'Finish turn for Crew'}));
  expect(screen.getByText('Took a turn')).toBeTruthy();
  const row=screen.getByRole('row',{name:'Crew'});
  fireEvent.click(within(row).getByRole('button',{name:'Take out of action'}));
  fireEvent.click(within(row).getByRole('button',{name:'Return to action'}));
  expect(screen.getByRole('button',{name:'Act again with Crew'})).toBeTruthy();
  fireEvent.click(screen.getByRole('button',{name:'Pass side'}));
  expect(screen.getByText('No participants in action on this side. You can pass explicitly.')).toBeTruthy();
  fireEvent.click(screen.getByRole('button',{name:'Pass side'}));
  fireEvent.change(screen.getByLabelText('Acting participant'),{target:{value:record.draft.entities[1].id}});
  expect(screen.getByRole('button',{name:'Finish turn for Watcher'})).toBeTruthy();
  const raw=JSON.parse(localStorage.getItem(combatRecoveryKey(record.world_id,record.encounter_id))!);
  expect(raw.draft.turn).toEqual({kind:'side',active_side_id:'watch',active_actor_id:record.draft.entities[1].id,acted_actor_ids:[]});
});

it('moves a finished actor to a different side without retaining invalid phase references',async()=>{
  const record=sideCombatRecord();await open(record);
  fireEvent.click(screen.getByRole('button',{name:'Start side turns'}));
  fireEvent.click(screen.getByRole('button',{name:'Act now with Crew'}));
  fireEvent.click(screen.getByRole('button',{name:'Finish turn for Crew'}));
  fireEvent.change(screen.getByLabelText('Side for Crew'),{target:{value:'watch'}});
  expect(screen.queryByText('Took a turn')).toBeNull();
  const raw=JSON.parse(localStorage.getItem(combatRecoveryKey(record.world_id,record.encounter_id))!);
  expect(raw.draft.turn).toMatchObject({active_side_id:'crew',active_actor_id:null,acted_actor_ids:[]});
  expect(raw.draft.entities[0].side_id).toBe('watch');
});

it('keeps an explicit side choice while adding several participants',async()=>{
  const record=sideCombatRecord();await open(record);
  fireEvent.change(screen.getByLabelText('Side for new participants'),{target:{value:'watch'}});
  for(const name of ['Guard one','Guard two']) {
    fireEvent.change(screen.getByLabelText('Participant name'),{target:{value:name}});
    fireEvent.click(screen.getByRole('button',{name:'Add participant',exact:true}));
  }
  const raw=JSON.parse(localStorage.getItem(combatRecoveryKey(record.world_id,record.encounter_id))!);
  expect(raw.draft.entities.slice(-2).map((actor:{side_id:string})=>actor.side_id)).toEqual(['watch','watch']);
});
it('keeps participation independent of zero and changing resource bounds',async()=>{
  const {record}=await open();
  fireEvent.change(screen.getByLabelText('Stress current for Crew'),{target:{value:'0'}});
  expect(screen.getByRole('button',{name:'Take out of action'})).toBeTruthy();
  fireEvent.click(screen.getByRole('button',{name:'Take out of action'}));
  fireEvent.change(screen.getByLabelText('Stress maximum for Crew'),{target:{value:'1'}});
  fireEvent.click(screen.getByRole('button',{name:'Return to action'}));
  expect((screen.getByLabelText('Stress current for Crew') as HTMLInputElement).value).toBe('0');
  const retained=JSON.parse(localStorage.getItem(combatRecoveryKey(record.world_id,record.encounter_id))!);
  expect(retained.draft.entities[0]).toMatchObject({participation:'in_action',values:{resources:{stress:{current:0,maximum:1}}}});
});
it('retains later notes and resource edits when a delayed Save acknowledges the submitted draft',async()=>{
  let resolve!:(record:ManualCombatRecord)=>void;
  const request=vi.spyOn(api,'saveManualCombatEncounter').mockImplementation(()=>new Promise(finish=>{resolve=finish;}));
  const {record,saved}=await open();
  fireEvent.change(screen.getByLabelText('Position for Crew'),{target:{value:'Covered'}});
  fireEvent.click(screen.getByRole('button',{name:'Save'}));
  await waitFor(()=>expect(request).toHaveBeenCalledTimes(1));
  const submitted=structuredClone(request.mock.calls[0][3]);
  fireEvent.change(screen.getByLabelText('Notes for Crew'),{target:{value:'Keep this after Save'}});
  fireEvent.change(screen.getByLabelText('Stress current for Crew'),{target:{value:'0'}});
  await act(async()=>resolve({...record,revision:2,draft:submitted}));
  expect(saved).toHaveBeenCalledTimes(1);
  expect((screen.getByLabelText('Notes for Crew') as HTMLTextAreaElement).value).toBe('Keep this after Save');
  const retained=JSON.parse(localStorage.getItem(combatRecoveryKey(record.world_id,record.encounter_id))!);
  expect(retained).toMatchObject({base:{revision:2},pending:null,draft:{entities:[{notes:'Keep this after Save',values:{resources:{stress:{current:0}}}}]}});
});
it('retries identical submitted bytes after an unknown Save instead of replacing its intent',async()=>{
  const request=vi.spyOn(api,'saveManualCombatEncounter').mockRejectedValue(new Error('Connection lost'));
  await open();fireEvent.change(screen.getByLabelText('Position for Crew'),{target:{value:'Covered'}});
  fireEvent.click(screen.getByRole('button',{name:'Save'}));
  await screen.findByRole('button',{name:'Retry Save'});
  const first=JSON.stringify(request.mock.calls[0]);
  fireEvent.click(screen.getByRole('button',{name:'Retry Save'}));
  await waitFor(()=>expect(request).toHaveBeenCalledTimes(2));
  expect(JSON.stringify(request.mock.calls[1])).toBe(first);
});

it('retains statuses without blur and permits comma entry, spaces and negative values',async()=>{
  const {record}=await open();
  const statuses=screen.getByLabelText('Statuses for Crew');fireEvent.focus(statuses);
  fireEvent.change(statuses,{target:{value:'Pinned, '}});
  expect((statuses as HTMLInputElement).value).toBe('Pinned, ');
  fireEvent.change(statuses,{target:{value:'Pinned, Exposed'}});
  const resource=screen.getByLabelText('Stress current for Crew');fireEvent.focus(resource);
  fireEvent.change(resource,{target:{value:'-'}});fireEvent.change(resource,{target:{value:'-2'}});
  const title=screen.getByLabelText('Encounter title');fireEvent.focus(title);
  fireEvent.change(title,{target:{value:'Crossing '}});expect((title as HTMLInputElement).value).toBe('Crossing ');
  fireEvent.change(title,{target:{value:'Crossing at dusk'}});
  cleanup();
  const raw=JSON.parse(localStorage.getItem(combatRecoveryKey(record.world_id,record.encounter_id))!);
  expect(raw.draft).toMatchObject({title:'Crossing at dusk',entities:[{statuses:['Pinned','Exposed'],values:{resources:{stress:{current:-2}}}}]});
});

it('shows an unknown Save even if later edits return the local draft to its base',async()=>{
  let reject!:(error:Error)=>void;
  vi.spyOn(api,'saveManualCombatEncounter').mockImplementation(()=>new Promise((_resolve,fail)=>{reject=fail;}));
  await open();const position=screen.getByLabelText('Position for Crew');
  fireEvent.change(position,{target:{value:'Covered'}});fireEvent.click(screen.getByRole('button',{name:'Save'}));
  await screen.findByRole('button',{name:'Saving…'});
  fireEvent.click(screen.getByRole('button',{name:'Unset Position for Crew'}));
  await act(async()=>reject(new Error('Connection lost')));
  expect(screen.getByRole('status').textContent).toContain('Save outcome unconfirmed');
});

it('restores accepted statuses after an invalid edit instead of presenting unsaved text as retained',async()=>{
  await open();const statuses=screen.getByLabelText('Statuses for Crew');
  fireEvent.focus(statuses);fireEvent.change(statuses,{target:{value:'Pinned'}});
  fireEvent.change(statuses,{target:{value:'x'.repeat(81)}});fireEvent.blur(statuses);
  expect((statuses as HTMLInputElement).value).toBe('Pinned');
  expect(screen.getByRole('alert').textContent).toContain('valid values');
});

it('does not turn an unset text stat into an empty string merely by focusing it',async()=>{
  const {record}=await open();const position=screen.getByLabelText('Position for Crew');
  fireEvent.focus(position);fireEvent.blur(position);
  expect(localStorage.getItem(combatRecoveryKey(record.world_id,record.encounter_id))).toBeNull();
  expect(screen.getByRole('button',{name:'Save'}).hasAttribute('disabled')).toBe(true);
});

it('removes the current round anchor without a round jump or dangling group member',async()=>{
  const record=manualCombatRecord(),first=record.draft.entities[0];
  record.ruleset.pacing.rounds=true;
  const second=newManualActor(record.ruleset,'Courier');record.draft.entities.push(second);
  record.draft.turn={kind:'ordered_rounds',active_actor_id:first.id,round_start_actor_id:first.id,round:4};
  record.draft.groups=[{id:'crew-group',label:'Crew group',member_ids:[first.id,second.id],collapsed:false}];
  await open(record);
  const crew=within(screen.getByRole('row',{name:'Crew',exact:true}));
  fireEvent.click(crew.getByText('Notes and participant options'));
  fireEvent.click(crew.getByRole('button',{name:'Remove Crew from encounter draft'}));
  expect(screen.queryByRole('row',{name:'Crew',exact:true})).toBeNull();
  expect(screen.getByText('Round 4')).toBeTruthy();
  const raw=JSON.parse(localStorage.getItem(combatRecoveryKey(record.world_id,record.encounter_id))!);
  expect(raw.draft.turn).toMatchObject({active_actor_id:second.id,round_start_actor_id:second.id,round:4});
  expect(raw.draft.groups[0].member_ids).toEqual([second.id]);
});

it('keeps the participant name when local retention refuses an addition',async()=>{
  await open();
  vi.spyOn(Storage.prototype,'setItem').mockImplementation(()=>{throw new Error('Storage quota reached');});
  fireEvent.change(screen.getByLabelText('Participant name'),{target:{value:'Bridge wardens'}});
  fireEvent.click(screen.getByRole('button',{name:'Add participant'}));
  expect((screen.getByLabelText('Participant name') as HTMLInputElement).value).toBe('Bridge wardens');
  expect(screen.queryByRole('row',{name:'Bridge wardens'})).toBeNull();
  expect(screen.getByRole('alert').textContent).toContain('Storage quota reached');
});

it('keeps source projection and edited fields on the same participant through reorder and group collapse',async()=>{
  const record=manualCombatRecord(),crew=record.draft.entities[0],courier=newManualActor(record.ruleset,'Courier');
  record.draft.entities.push(courier);record.draft.turn.active_actor_id=crew.id;
  record.draft.groups=[{id:'crew-group',label:'Bridge team',member_ids:[crew.id,courier.id],collapsed:false}];
  crew.mechanics_snapshot={origin:'world_accepted_mechanics_v1',managed_world_id:record.world_id,draft_id:'22222222-2222-4222-8222-222222222222',draft_version:3,
    acceptance_operation_id:'synthetic-accept',acceptance_request_digest:'sha256:'+'a'.repeat(64),accepted_from_draft_version:1,accepted_from_candidate_id:null,
    locator:{provider:'dungeonmind',statblock_id:exactSource.statblock_id,revision_id:exactSource.revision_id,contract:exactSource.contract,contract_version:exactSource.contract_version,definition_digest:exactSource.definition_digest},
    resource:exactSource,snapshot_digest:'sha256:'+'b'.repeat(64)} as AcceptedCombatMechanicsSnapshot;
  await open(record);
  fireEvent.click(screen.getByRole('button',{name:'Project source for Crew'}));
  const projection=screen.getByRole('complementary',{name:'Exact source for Crew'});
  expect(projection).toHaveFocus();
  fireEvent.change(screen.getByLabelText('Position for Crew'),{target:{value:'Covered'}});
  fireEvent.click(within(screen.getByRole('row',{name:'Crew',exact:true})).getByText('Notes and participant options'));
  fireEvent.click(screen.getByRole('button',{name:'Move Crew later'}));
  fireEvent.click(screen.getByRole('button',{name:'Bridge team · 2 participants'}));
  expect(screen.getByRole('row',{name:'Crew',exact:true})).toBeVisible();
  expect(screen.queryByRole('row',{name:'Courier',exact:true})).toBeNull();
  expect(screen.getByRole('complementary',{name:'Exact source for Crew'})).toBe(projection);
  expect((screen.getByLabelText('Position for Crew') as HTMLInputElement).value).toBe('Covered');
  fireEvent.click(screen.getByRole('button',{name:'Close source'}));
  expect(screen.getByRole('button',{name:'Project source for Crew'})).toHaveFocus();
  const retained=JSON.parse(localStorage.getItem(combatRecoveryKey(record.world_id,record.encounter_id))!);
  expect(retained.draft.entities.map((actor:{id:string})=>actor.id)).toEqual([courier.id,crew.id]);
  expect(retained.draft.turn.active_actor_id).toBe(crew.id);
  expect(retained.draft.entities[1].mechanics_snapshot).toEqual(crew.mechanics_snapshot);
});
