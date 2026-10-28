import {beforeEach,describe,it,expect,vi} from 'vitest';
import {render,screen,fireEvent,waitFor,cleanup} from '@testing-library/react';
import {PreparedTablesTool} from './PreparedTablesTool';
import type {TourOwnerReading} from '../guidedTour/GuidedTour';
const tourReadings=vi.hoisted(()=>new Map<string,TourOwnerReading>());
vi.mock('../guidedTour/GuidedTour',()=>({useTourOwnerReading:(reading:TourOwnerReading)=>tourReadings.set(reading.step,reading)}));
import {pendingTableKey} from './preparedTablesProjection';
import type {WorldPlayRunRecordV2} from '../api/types';
const request=vi.hoisted(()=>vi.fn());
vi.mock('../api/liveApi',()=>({authenticatedApiFetch:request,LiveApiError:class extends Error{status:number;constructor(message:string,status:number){super(message);this.status=status;}}}));
const run={schema_version:'dmb_world_play_run_record_v2',world_id:'world',run_id:'11111111-1111-4111-8111-111111111111',playable_artifact_id:'22222222-2222-4222-8222-222222222222',playable_revision:1,playable_work_revision_id:'33333333-3333-4333-8333-333333333333',playable_content_sha256:'a'.repeat(64),run_revision:1,progress:{notes_by_element_id:{'scene:gate':'Kept note'}},created_at:'2026-10-22T00:00:00Z',updated_at:'2026-10-22T00:00:00Z'} as WorldPlayRunRecordV2;
const source={playable_artifact_id:run.playable_artifact_id,playable_revision:1,playable_work_revision_id:run.playable_work_revision_id,playable_content_sha256:run.playable_content_sha256};
const table={schema_version:'dmb_roll_table_v1',table_id:'table:weather',title:'Weather',die_sides:6,rows:[{row_id:'row:rain',min:1,max:6,outcome:'Rain'}],table_sha256:'b'.repeat(64)};
const inventory={run,source,source_title:'Journey',can_record:true,tables:[table]};
const ok=(body:unknown,status=200)=>({response:{ok:status<400,status,json:async()=>body}});
const receipt=(id:string,body:any)=>({schema_version:'dmb_prepared_table_receipt_v1',world_id:run.world_id,run_id:run.run_id,command_id:id,source,source_title:'Journey',table_id:body.table_id,table_sha256:body.table_sha256,table_title:'Weather',die_sides:6,physical_value:body.physical_value,row_id:'row:rain',outcome:'Rain',expected_run_revision:1,resulting_run_revision:2,recorded_at:'2026-10-22T00:00:00Z'});
beforeEach(()=>{tourReadings.clear();cleanup();localStorage.clear();Object.defineProperty(navigator,'locks',{configurable:true,value:{request:(_name:string,action:()=>unknown)=>Promise.resolve().then(action)}});request.mockReset();request.mockImplementation(async(path:string)=>ok(path.includes('/receipts')?{receipts:[],next_before:null}:inventory));});
describe('prepared table pending command',()=>{
  it('persists before sending, recovers unknown outcome and explicitly retries exact identity',async()=>{
    const onRun=vi.fn(),onHeld=vi.fn();let firstId='';let firstBody='';let attempts=0;
    request.mockImplementation(async(path:string,init:RequestInit)=>{
      if(!path.includes('/commands/'))return ok(inventory);
      expect(localStorage.getItem(pendingTableKey(run.world_id,run.run_id))).not.toBeNull();
      attempts++;const id=path.split('/commands/')[1].split('?')[0];const raw=String(init.body);
      if(attempts===1){firstId=id;firstBody=raw;throw new Error('connection lost');}
      expect(id).toBe(firstId);expect(raw).toBe(firstBody);
      return ok({receipt:receipt(id,JSON.parse(raw)),run:{...run,run_revision:2},replayed:true});
    });
    const first=render(<PreparedTablesTool run={run} blocked={false} onRun={onRun} onHeld={onHeld}/>);
    await screen.findByLabelText('Physical roll');fireEvent.change(screen.getByLabelText('Physical roll'),{target:{value:'4'}});
    fireEvent.click(screen.getByText('Record outcome'));await screen.findByText(/save outcome is unknown/);
    first.unmount();
    render(<PreparedTablesTool run={run} blocked={false} onRun={onRun} onHeld={onHeld}/>);
    await screen.findByText('Retry saved command');expect(attempts).toBe(1);
    expect(screen.getByLabelText('Physical roll')).toBeDisabled();
    fireEvent.click(screen.getByText('Retry saved command'));
    await waitFor(()=>expect(onRun).toHaveBeenCalledWith({...run,run_revision:2}));
    expect(onHeld).toHaveBeenLastCalledWith(false);
    expect(localStorage.getItem(pendingTableKey(run.world_id,run.run_id))).toBeNull();
    expect(tourReadings.get('roll')?.observation).toMatchObject({origin:'acknowledged',target:{objectId:run.run_id,revision:2},parent:{revisionId:run.playable_work_revision_id},proof:{kind:'recorded-roll',commandId:firstId,physicalValue:4,dieSides:6,tableId:table.table_id,tableDigest:table.table_sha256,rowId:'row:rain'}});
  });
  it('retains entered values after a known conflict and requires refresh',async()=>{
    request.mockImplementation(async(path:string)=>path.includes('/commands/')?ok({detail:'Session changed'},409):ok(inventory));
    const onHeld=vi.fn();render(<PreparedTablesTool run={run} blocked={false} onHeld={onHeld} onRun={vi.fn()}/>);
    await screen.findByLabelText('Physical roll');fireEvent.change(screen.getByLabelText('Physical roll'),{target:{value:'3'}});fireEvent.click(screen.getByText('Record outcome'));
    await screen.findByText(/Your entered value is retained/);expect(screen.queryByText('Record outcome')).toBeNull();
    fireEvent.click(screen.getByText('Refresh saved preparation'));await screen.findByLabelText('Physical roll');expect(screen.getByLabelText('Physical roll')).toHaveValue('3');expect(onHeld).toHaveBeenLastCalledWith(false);
  });
  it('does not send a roll while notes/session edits are held',async()=>{
    render(<PreparedTablesTool run={run} blocked onRun={vi.fn()} onHeld={vi.fn()}/>);
    await screen.findByLabelText('Physical roll');expect(screen.getByText('Record outcome')).toBeDisabled();expect(request.mock.calls.every(([path])=>!String(path).includes('/commands/'))).toBe(true);
  });
  it('keeps an unknown command frozen when response identity is wrong',async()=>{
    request.mockImplementation(async(path:string,init:RequestInit)=>path.includes('/commands/')?ok({receipt:{...receipt(path.split('/commands/')[1].split('?')[0],JSON.parse(String(init.body))),run_id:'other'},run}):ok(inventory));
    const onRun=vi.fn();render(<PreparedTablesTool run={run} blocked={false} onRun={onRun} onHeld={vi.fn()}/>);
    await screen.findByLabelText('Physical roll');fireEvent.change(screen.getByLabelText('Physical roll'),{target:{value:'2'}});fireEvent.click(screen.getByText('Record outcome'));
    await screen.findByText(/save outcome is unknown/);expect(onRun).not.toHaveBeenCalled();expect(localStorage.getItem(pendingTableKey(run.world_id,run.run_id))).not.toBeNull();
  });
});

it.each([200,409])('does not erase a competing command when a late %s response arrives',async status=>{
  let resolve!:(value:unknown)=>void;
  request.mockImplementation(async(path:string)=>path.includes('/commands/')?new Promise(done=>{resolve=done}):ok(inventory));
  const onRun=vi.fn();render(<PreparedTablesTool run={run} blocked={false} onRun={onRun} onHeld={vi.fn()}/>);
  await screen.findByLabelText('Physical roll');fireEvent.change(screen.getByLabelText('Physical roll'),{target:{value:'2'}});fireEvent.click(screen.getByText('Record outcome'));
  await waitFor(()=>expect(resolve).toBeDefined());
  const key=pendingTableKey(run.world_id,run.run_id),original=JSON.parse(localStorage.getItem(key)!);
  const foreign={...original,id:'99999999-9999-4999-8999-999999999999'};localStorage.setItem(key,JSON.stringify(foreign));
  resolve(status===200?ok({receipt:receipt(original.id,original.body),run:{...run,run_revision:2}}):ok({detail:'Conflict'},409));
  await screen.findByText(status===200?/save outcome is unknown/:/Another view changed recovery/);
  expect(localStorage.getItem(key)).toBe(JSON.stringify(foreign));expect(onRun).not.toHaveBeenCalled();
});

it('retains an unknown original command when its retry is refused by authentication',async()=>{
  let attempts=0;request.mockImplementation(async(path:string)=>{
    if(!path.includes('/commands/'))return ok(inventory);
    if(++attempts===1)throw new Error('response lost');
    return ok({detail:'Unauthorized'},401);
  });
  render(<PreparedTablesTool run={run} blocked={false} onRun={vi.fn()} onHeld={vi.fn()}/>);
  await screen.findByLabelText('Physical roll');fireEvent.change(screen.getByLabelText('Physical roll'),{target:{value:'2'}});fireEvent.click(screen.getByText('Record outcome'));
  await screen.findByText(/save outcome is unknown/);const key=pendingTableKey(run.world_id,run.run_id),original=localStorage.getItem(key);
  fireEvent.click(screen.getByText('Retry saved command'));
  await waitFor(()=>expect(attempts).toBe(2));await waitFor(()=>expect(screen.getByText('Retry saved command')).toBeEnabled());
  expect(localStorage.getItem(key)).toBe(original);expect(screen.getByLabelText('Physical roll')).toBeDisabled();
});

it('refuses to replace a command created by another view while acquiring the browser lock',async()=>{
  let action:(()=>unknown)|undefined;
  const originalLocks=navigator.locks;
  const acquire=vi.fn((_name:string,callback:()=>unknown)=>new Promise((resolve,reject)=>{action=()=>{try{resolve(callback())}catch(e){reject(e)}}}));
  Object.defineProperty(navigator,'locks',{configurable:true,value:{request:acquire}});
  try{
    render(<PreparedTablesTool run={run} blocked={false} onRun={vi.fn()} onHeld={vi.fn()}/>);
    await screen.findByLabelText('Physical roll');fireEvent.change(screen.getByLabelText('Physical roll'),{target:{value:'2'}});fireEvent.click(screen.getByText('Record outcome'));
    await waitFor(()=>expect(action).toBeDefined());
    const key=pendingTableKey(run.world_id,run.run_id),foreign='{"another":"command"}';localStorage.setItem(key,foreign);action!();
    await screen.findByText(/Another view changed the pending roll/);expect(localStorage.getItem(key)).toBe(foreign);
    expect(request.mock.calls.every(([path])=>!String(path).includes('/commands/'))).toBe(true);
  }finally{Object.defineProperty(navigator,'locks',{configurable:true,value:originalLocks});}
});


it('does not post after its view closes while waiting for a browser lock',async()=>{
  let action:(()=>unknown)|undefined;
  const acquire=vi.fn((_name:string,callback:()=>unknown)=>new Promise((resolve,reject)=>{action=()=>{try{resolve(callback())}catch(e){reject(e)}}}));
  Object.defineProperty(navigator,'locks',{configurable:true,value:{request:acquire}});
  const mounted=render(<PreparedTablesTool run={run} blocked={false} onRun={vi.fn()} onHeld={vi.fn()}/>);
  await screen.findByLabelText('Physical roll');fireEvent.change(screen.getByLabelText('Physical roll'),{target:{value:'2'}});fireEvent.click(screen.getByText('Record outcome'));
  await waitFor(()=>expect(action).toBeDefined());mounted.unmount();action!();
  await Promise.resolve();await Promise.resolve();
  expect(localStorage.getItem(pendingTableKey(run.world_id,run.run_id))).toBeNull();
  expect(request.mock.calls.every(([path])=>!String(path).includes('/commands/'))).toBe(true);
});


it.each(['blocked','revision'])('revalidates host %s after waiting for the browser lock',async change=>{
  let action:(()=>unknown)|undefined;
  const acquire=vi.fn((_name:string,callback:()=>unknown)=>new Promise((resolve,reject)=>{action=()=>{try{resolve(callback())}catch(e){reject(e)}}}));
  Object.defineProperty(navigator,'locks',{configurable:true,value:{request:acquire}});
  const onRun=vi.fn(),onHeld=vi.fn();
  const mounted=render(<PreparedTablesTool run={run} blocked={false} onRun={onRun} onHeld={onHeld}/>);
  await screen.findByLabelText('Physical roll');fireEvent.change(screen.getByLabelText('Physical roll'),{target:{value:'2'}});fireEvent.click(screen.getByText('Record outcome'));
  await waitFor(()=>expect(action).toBeDefined());
  mounted.rerender(<PreparedTablesTool run={change==='revision'?{...run,run_revision:2}:run} blocked={change==='blocked'} onRun={onRun} onHeld={onHeld}/>);action!();
  await waitFor(()=>expect(screen.getByRole('alert')).toHaveTextContent(change==='blocked'?'Save or resolve':'Session changed'));
  expect(localStorage.getItem(pendingTableKey(run.world_id,run.run_id))).toBeNull();
  expect(request.mock.calls.every(([path])=>!String(path).includes('/commands/'))).toBe(true);
});
