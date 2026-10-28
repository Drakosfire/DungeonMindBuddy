import {cleanup,render,screen} from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import {afterEach,beforeEach,expect,it,vi} from 'vitest';
import {webcrypto} from 'node:crypto';
import {CombatMechanicsAdoption} from './CombatMechanicsAdoption';
import {TourEncounterProvider,type TourEncounterScope} from '../guidedTour/EncounterScope';
import type {TourOwnerReading} from '../guidedTour/GuidedTour';
const tourReadings=vi.hoisted(()=>new Map<string,TourOwnerReading>());
vi.mock('../guidedTour/GuidedTour',()=>({useGuidedTour:()=>({captureScope:()=>null}),useTourOwnerReading:(reading:TourOwnerReading|null)=>{if(reading)tourReadings.set(reading.step,reading);}}));
import * as api from './combatApi';
import * as live from '../api/liveApi';
import type {CombatEncounterRecord,MechanicsAdoptionOutcome,MechanicsAdoptionPreview,AdoptMechanicsRequest} from './combatTypes';
import {adoptionRequestDigest,verifyAdoptionOutcome,type PendingMechanicsAdoption} from './CombatMechanicsAdoptionRecovery';
vi.mock('./combatApi',()=>({listAcceptedCombatMechanics:vi.fn(),previewSavedCombatMechanics:vi.fn(),adoptCombatMechanics:vi.fn(),listCombatMechanicsAdoptions:vi.fn(),inspectCombatMechanicsAdoption:vi.fn()}));
vi.mock('../api/liveApi',()=>({listSavedMechanicsVersions:vi.fn()}));
vi.mock('../statblocks/revision/SavedMechanicsRevisionEditor',()=>({SavedMechanicsRevisionEditor:()=>null}));
vi.mock('./CombatMechanicsInspection',()=>({CombatMechanicsInspection:()=>null}));
const world='elderwyld',id='11111111-1111-4111-8111-111111111111',draftId='22222222-2222-4222-8222-222222222222';
const tourScope:TourEncounterScope={plan:{kind:'plan',worldId:world,objectId:'plan',revision:2,revisionId:'work-2',digest:'d'.repeat(64)},sceneId:'scene',encounterId:id};
const locator={provider:'dungeonmind',statblock_id:'sb_keeper',revision_id:'rev_two',contract:'dungeonmind.dungeonbuddy-statblocks',contract_version:'1.0.0',definition_digest:'sha256:'+'a'.repeat(64)} as const;
const original={locator:{...locator,revision_id:'rev_one'},snapshot_digest:'sha256:'+'b'.repeat(64)};
const record={world_id:world,encounter_id:id,revision:4,draft:{entities:[{id:'one',name:'Keeper',ac:12,hp:35,max_hp:40,temp_hp:7,defeated:true,mechanics_snapshot:original},
  {id:'other',name:'Sibling',ac:12,hp:10,max_hp:40,temp_hp:0,mechanics_snapshot:original}]}} as unknown as CombatEncounterRecord;
const preview={snapshot:{origin:'buddy_saved_mechanics_override_v1',managed_world_id:world,draft_id:draftId,locator,snapshot_digest:'sha256:'+'c'.repeat(64)},armor_class:20,hit_points:28} as MechanicsAdoptionPreview;
beforeEach(()=>{
  vi.clearAllMocks();tourReadings.clear();localStorage.clear();sessionStorage.clear();vi.stubGlobal('crypto',webcrypto);
  vi.mocked(api.listAcceptedCombatMechanics).mockResolvedValue({choices:[{name:'Keeper source',draft_id:draftId,draft_version:3}],nextOffset:null});
  vi.mocked(live.listSavedMechanicsVersions).mockResolvedValue({world_id:world,draft_id:draftId,name:'Keeper',original:locator,operations:[],pending:null,next_offset:null});
  vi.mocked(api.previewSavedCombatMechanics).mockResolvedValue(preview);
});
afterEach(()=>{cleanup();vi.unstubAllGlobals();});
async function select(){await userEvent.click(screen.getByRole('button',{name:'Find saved creatures'}));await userEvent.click(await screen.findByRole('button',{name:'Keeper source'}));
  await userEvent.click(await screen.findByRole('button',{name:'Preview exact version'}));await screen.findByText('Saved AC: 20 · Maximum HP: 28');
  await userEvent.click(screen.getByLabelText('Select Keeper (1)'));
}
function pendingFrom(body:AdoptMechanicsRequest):PendingMechanicsAdoption {
  return {schema:'dmb_pending_combat_adoption_v1',worldId:world,encounterId:id,request:body,afterDigest:preview.snapshot.snapshot_digest};
}
async function outcome(body:AdoptMechanicsRequest,advanced=false):Promise<MechanicsAdoptionOutcome>{
  const pending=pendingFrom(body),choice=body.actors[0],actor={...record.draft.entities[0],mechanics_snapshot:preview.snapshot};
  return {receipt:{schema:'dmb_combat_mechanics_adoption_receipt_v1',operation_id:body.operation_id,world_id:world,encounter_id:id,
    request_digest:await adoptionRequestDigest(pending),state:'applied',source:locator,expected_revision:4,committed_revision:5,created_at:'2026-10-22T00:00:00Z',
    transitions:[{actor_id:'one',before_snapshot_digest:original.snapshot_digest,after_snapshot_digest:preview.snapshot.snapshot_digest,ac_policy:choice.ac_policy,hp_policy:choice.hp_policy,
      before_ac:12,after_ac:12,before_hp:35,after_hp:35,before_max_hp:40,after_max_hp:40}]},
    encounter:{...record,revision:advanced?6:5,draft:{...record.draft,entities:[advanced?{...actor,hp:11}:actor,record.draft.entities[1]]}},advanced_since_apply:advanced};
}

async function savedHistory(){
 const body:AdoptMechanicsRequest={schema:'dmb_combat_mechanics_adoption_request_v1',operation_id:crypto.randomUUID(),expected_revision:4,draft_id:draftId,locator,actors:[{actor_id:'one',expected_snapshot_digest:original.snapshot_digest,ac_policy:'keep',hp_policy:'keep'}]};
 const saved=await outcome(body,true);
 vi.mocked(api.listCombatMechanicsAdoptions).mockResolvedValue({schema:'dmb_combat_mechanics_adoption_history_v1',world_id:world,encounter_id:id,receipts:[saved.receipt],next_before_operation_id:null});
 vi.mocked(api.inspectCombatMechanicsAdoption).mockResolvedValue(saved);
 return saved;
}
async function openHistory(){
 await userEvent.click(screen.getByText('Saved adoptions',{exact:true}));
 await userEvent.click(screen.getByRole('button',{name:'Load saved adoptions'}));
 await userEvent.click(await screen.findByRole('button',{name:/Inspect applied version/}));
}
it('inspects an advanced historical adoption as an existing example without reconciling removed actors',async()=>{
 const saved=await savedHistory();saved.encounter.draft.entities=[];
 const reconcile=vi.fn();render(<TourEncounterProvider scope={tourScope}><CombatMechanicsAdoption record={record} disabled={false} onLockChange={()=>{}} onReconciled={reconcile}/></TourEncounterProvider>);
 await openHistory();await screen.findByText('Existing adoption · encounter version 5');
 expect(screen.getByText('Exact saved version: rev_two')).toBeTruthy();expect(screen.getByText(/one · AC policy: keep · HP policy: keep/)).toBeTruthy();
 expect(tourReadings.get('adoption')?.observation?.origin).toBe('existing');
 expect(api.adoptCombatMechanics).not.toHaveBeenCalled();expect(reconcile).not.toHaveBeenCalled();expect(localStorage.length).toBe(0);
});
it('reads historical receipts without clearing uncertain recovery or granting tour credit',async()=>{
 await savedHistory();vi.mocked(api.adoptCombatMechanics).mockRejectedValueOnce(new Error('Response lost'));
 const reconcile=vi.fn();render(<TourEncounterProvider scope={tourScope}><CombatMechanicsAdoption record={record} disabled={false} onLockChange={()=>{}} onReconciled={reconcile}/></TourEncounterProvider>);
 await select();await userEvent.click(screen.getByRole('button',{name:'Use version for selected actors'}));await screen.findByText(/Outcome unconfirmed/);
 const retained=Object.fromEntries(Object.keys(localStorage).map(k=>[k,localStorage.getItem(k)]));
 await openHistory();await screen.findByText('Existing adoption · encounter version 5');
 expect(Object.fromEntries(Object.keys(localStorage).map(k=>[k,localStorage.getItem(k)]))).toEqual(retained);
 expect(screen.getByRole('button',{name:'Retry original adoption'})).toBeTruthy();expect(reconcile).not.toHaveBeenCalled();
 expect(tourReadings.get('adoption')?.observation).toBeUndefined();expect(api.adoptCombatMechanics).toHaveBeenCalledTimes(1);
});
it.each(['applied','canceled'] as const)('inspects %s choices with dirty drafts without tour completion',async state=>{
 const saved=await savedHistory();if(state==='canceled'){saved.receipt={...saved.receipt,state:'canceled',committed_revision:null,transitions:[]};saved.advanced_since_apply=false;}
 vi.mocked(api.listCombatMechanicsAdoptions).mockResolvedValue({schema:'dmb_combat_mechanics_adoption_history_v1',world_id:world,encounter_id:id,receipts:[saved.receipt],next_before_operation_id:null});
 render(<TourEncounterProvider scope={tourScope}><CombatMechanicsAdoption record={record} disabled={true} onLockChange={()=>{}} onReconciled={()=>{}}/></TourEncounterProvider>);
 await userEvent.click(screen.getByText('Saved adoptions',{exact:true}));await userEvent.click(screen.getByRole('button',{name:'Load saved adoptions'}));
 await userEvent.click(await screen.findByRole('button',{name:state==='canceled'?/Inspect canceled choice/:/Inspect applied version/}));await screen.findByText(state==='canceled'?'Canceled choice · no actors changed':'Existing adoption · encounter version 5');
 expect(tourReadings.get('adoption')?.observation).toBeUndefined();expect(api.adoptCombatMechanics).not.toHaveBeenCalled();
});
it('refuses a foreign inspection and cannot credit a late response after the same encounter changes Plan scope',async()=>{
 const saved=await savedHistory();const mount=(s:TourEncounterScope)=><TourEncounterProvider scope={s}><CombatMechanicsAdoption record={record} disabled={false} onLockChange={()=>{}} onReconciled={()=>{}}/></TourEncounterProvider>;
 vi.mocked(api.inspectCombatMechanicsAdoption).mockResolvedValueOnce({...saved,receipt:{...saved.receipt,world_id:'foreign'}});
 const view=render(mount(tourScope));await openHistory();await screen.findByText(/Saved adoption receipt cannot be verified/);
 expect(tourReadings.get('adoption')?.observation).toBeUndefined();
 let finish!:(value:MechanicsAdoptionOutcome)=>void;vi.mocked(api.inspectCombatMechanicsAdoption).mockImplementationOnce(()=>new Promise(resolve=>{finish=resolve;}));
 await userEvent.click(screen.getByRole('button',{name:/Inspect applied version/}));
 view.rerender(mount({...tourScope,plan:{...tourScope.plan,revision:3,revisionId:'work-3'}}));finish(saved);await Promise.resolve();
 expect(screen.queryByLabelText('Saved adoption inspection')).toBeNull();expect(tourReadings.get('adoption')?.observation).toBeUndefined();
});
it('explicitly adopts selected actors with preserving defaults and unchanged sibling',async()=>{
  const reconciled=vi.fn();vi.mocked(api.adoptCombatMechanics).mockImplementation(async(_w,_e,body)=>outcome(body));
  render(<TourEncounterProvider scope={tourScope}><CombatMechanicsAdoption record={record} disabled={false} onLockChange={()=>{}} onReconciled={reconciled}/></TourEncounterProvider>);await select();
  expect(api.adoptCombatMechanics).not.toHaveBeenCalled();expect(tourReadings.get('adoption')?.status).toBe('unavailable');expect(tourReadings.get('adoption')?.reason).toContain('An applied receipt is required');expect(screen.getByLabelText('AC policy for Keeper (1)')).toHaveValue('keep');
  expect(screen.getByLabelText('HP policy for Keeper (1)')).toHaveValue('keep');
  await userEvent.click(screen.getByRole('button',{name:'Use version for selected actors'}));
  await screen.findByText('Selected actors now use this exact version. Other actors and World associations are unchanged.');
  expect(vi.mocked(api.adoptCombatMechanics).mock.calls[0][2].actors).toEqual([{actor_id:'one',expected_snapshot_digest:original.snapshot_digest,ac_policy:'keep',hp_policy:'keep'}]);
  expect(reconciled.mock.calls[0][0].draft.entities[1]).toEqual(record.draft.entities[1]);
  expect(tourReadings.get('adoption')?.status).toBe('ready');
  expect(tourReadings.get('adoption')?.observation).toMatchObject({origin:'acknowledged',target:tourScope.plan,proof:{kind:'adoption',sceneId:'scene',encounterId:id,encounterRevision:5,locator,actors:[{actorId:'one',beforeDigest:original.snapshot_digest,afterDigest:preview.snapshot.snapshot_digest,acPolicy:'keep',hpPolicy:'keep'}]}});
});
it('shows lower maximum and reset consequences before sending',async()=>{
  render(<CombatMechanicsAdoption record={record} disabled={false} onLockChange={()=>{}} onReconciled={()=>{}}/>);await select();
  await userEvent.selectOptions(screen.getByLabelText('HP policy for Keeper (1)'),'preserve_current');expect(screen.getByText(/After: HP 35 \/ 28/)).toBeTruthy();
  await userEvent.selectOptions(screen.getByLabelText('HP policy for Keeper (1)'),'reset_full');expect(screen.getByText(/After: HP 28 \/ 28/).textContent).toContain('defeated status remains set');
  expect(api.adoptCombatMechanics).not.toHaveBeenCalled();
});
it('retains uncertain exact request across remount and acknowledges advanced tracker state',async()=>{
  vi.mocked(api.adoptCombatMechanics).mockRejectedValueOnce(new Error('Response lost'));
  const first=render(<CombatMechanicsAdoption record={record} disabled={false} onLockChange={()=>{}} onReconciled={()=>{}}/>);await select();
  await userEvent.click(screen.getByRole('button',{name:'Use version for selected actors'}));await screen.findByText(/Outcome unconfirmed/);
  const body=vi.mocked(api.adoptCombatMechanics).mock.calls[0][2];first.unmount();const reconciled=vi.fn();
  vi.mocked(api.adoptCombatMechanics).mockImplementation(async(_w,_e,request)=>outcome(request,true));
  render(<CombatMechanicsAdoption record={record} disabled={false} onLockChange={()=>{}} onReconciled={reconciled}/>);
  await userEvent.click(await screen.findByRole('button',{name:'Retry original adoption'}));await screen.findByText('This adoption committed earlier. Newer encounter changes are loaded and preserved.');
  expect(vi.mocked(api.adoptCombatMechanics).mock.calls[1][2]).toEqual(body);expect(reconciled.mock.calls[0][0].draft.entities[0].hp).toBe(11);
});
it('refuses foreign acknowledgment and retains recovery',async()=>{
  vi.mocked(api.adoptCombatMechanics).mockImplementation(async(_w,_e,body)=>{const r=await outcome(body);return {...r,receipt:{...r.receipt,encounter_id:'other'}};});
  const reconciled=vi.fn();render(<CombatMechanicsAdoption record={record} disabled={false} onLockChange={()=>{}} onReconciled={reconciled}/>);await select();
  await userEvent.click(screen.getByRole('button',{name:'Use version for selected actors'}));await screen.findByText(/Outcome unconfirmed/);
  expect(reconciled).not.toHaveBeenCalled();expect(screen.getByRole('button',{name:'Cancel pending adoption'})).toBeTruthy();
});
it('protects dirty drafts from adoption',()=>{
  render(<CombatMechanicsAdoption record={record} disabled={true} onLockChange={()=>{}} onReconciled={()=>{}}/>);
  expect(screen.getByRole('button',{name:'Find saved creatures'}).matches(':disabled')).toBe(true);expect(api.listAcceptedCombatMechanics).not.toHaveBeenCalled();
});
it('rejects changed actor transitions',async()=>{
  const body:AdoptMechanicsRequest={schema:'dmb_combat_mechanics_adoption_request_v1',operation_id:crypto.randomUUID(),expected_revision:4,draft_id:draftId,locator,
    actors:[{actor_id:'one',expected_snapshot_digest:original.snapshot_digest,ac_policy:'keep',hp_policy:'keep'}]};
  const result=await outcome(body);result.receipt.transitions[0].hp_policy='reset_full';await expect(verifyAdoptionOutcome(pendingFrom(body),result)).rejects.toThrow('actor acknowledgment');
});

it('cancels only the retained unapplied command and releases its recovery',async()=>{
  vi.mocked(api.adoptCombatMechanics).mockRejectedValueOnce(new Error('Response lost'));
  const reconciled=vi.fn();render(<CombatMechanicsAdoption record={record} disabled={false} onLockChange={()=>{}} onReconciled={reconciled}/>);await select();
  await userEvent.click(screen.getByRole('button',{name:'Use version for selected actors'}));await screen.findByText(/Outcome unconfirmed/);
  const body=vi.mocked(api.adoptCombatMechanics).mock.calls[0][2];
  vi.mocked(api.adoptCombatMechanics).mockImplementation(async()=>({receipt:{...(await outcome(body)).receipt,state:'canceled',committed_revision:null,transitions:[]},encounter:record,advanced_since_apply:false}));
  await userEvent.click(screen.getByRole('button',{name:'Cancel pending adoption'}));
  await screen.findByText('Pending adoption canceled before commit. Current encounter state loaded; this command changed no actors.');
  expect(vi.mocked(api.adoptCombatMechanics).mock.calls[1]).toEqual([world,id,body,true]);
  expect(screen.queryByRole('button',{name:'Retry original adoption'})).toBeNull();
});

it('does not reconcile a late acknowledgment into a newly opened World',async()=>{
  let finish!:(result:MechanicsAdoptionOutcome)=>void;
  vi.mocked(api.adoptCombatMechanics).mockImplementation(()=>new Promise(resolve=>{finish=resolve;}));
  const old=vi.fn();const view=render(<CombatMechanicsAdoption record={record} disabled={false} onLockChange={()=>{}} onReconciled={old}/>);await select();
  await userEvent.click(screen.getByRole('button',{name:'Use version for selected actors'}));
  const body=vi.mocked(api.adoptCombatMechanics).mock.calls[0][2];view.unmount();const current=vi.fn();
  render(<CombatMechanicsAdoption record={{...record,world_id:'other-world'}} disabled={false} onLockChange={()=>{}} onReconciled={current}/>);
  finish(await outcome(body));await Promise.resolve();
  expect(old).not.toHaveBeenCalled();expect(current).not.toHaveBeenCalled();
  expect(Object.keys(localStorage).some(key=>key.startsWith('dmb.combat.adoption:'))).toBe(true);
});
