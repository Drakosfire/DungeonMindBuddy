import {afterEach,beforeEach,expect,it,vi} from 'vitest';
import {act,cleanup,fireEvent,render,screen,waitFor} from '@testing-library/react';
import {ManualCombatEditor} from './ManualCombatEditor';
import {manualCombatRecord} from './ManualCombat.testSupport';
import {testCombatLocks} from './combatRecovery.testSupport';
import * as api from './combatApi';
import {combatRecoveryKey} from './combatRecovery';
import type {ManualCombatRecord} from './ManualCombatTypes';

beforeEach(()=>{localStorage.clear();Object.defineProperty(navigator,'locks',{configurable:true,value:testCombatLocks()});});
afterEach(()=>{cleanup();vi.restoreAllMocks();});
async function open(record=manualCombatRecord()) {
  const saved=vi.fn();render(<ManualCombatEditor record={record} onSaved={saved} onBlocked={()=>{}}/>);
  await waitFor(()=>expect((screen.getByLabelText('Stress current for Crew') as HTMLInputElement).disabled).toBe(false));
  return {record,saved};
}
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
