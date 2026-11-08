import {StrictMode,useState} from 'react';
import {act,cleanup,fireEvent,render,screen,waitFor,within} from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import {afterEach,beforeAll,beforeEach,expect,it,vi} from 'vitest';
import * as api from '../api/liveApi';
import revisionFixture from '../../../../tests/fixtures/statblocks/v1/exact-revision-response.json';
import type {StatblockRevisionResourceV1} from '../contracts/dungeonbuddy-statblocks-v1/client';
import type {RevisionSaveOutcome} from './revision/savedMechanicsRevisionTypes';
import {GenerationPlanProvider} from '../guidedTour/GenerationObservations';
import {TourEncounterProvider,type TourEncounterScope} from '../guidedTour/EncounterScope';
import {SavedStatblockProvider,SavedStatblockButton} from './SavedStatblockSession';
import {SavedStatblockFullView} from './StatblockPage';
function SessionHost(props:{worldId:string;draftId:string;revisionId?:string}) {return <SavedStatblockProvider worldId={props.worldId}><SavedStatblockButton {...props}/></SavedStatblockProvider>;}
const guidance=vi.hoisted(()=>({readings:[] as any[],captureMechanicsScope:vi.fn(()=>null)}));
vi.mock('../guidedTour/GuidedTour',async(importOriginal)=>({...await importOriginal<typeof import('../guidedTour/GuidedTour')>(),useGuidedTour:()=>({captureScope:()=>null,captureMechanicsScope:guidance.captureMechanicsScope}),useTourOwnerReading:(reading:unknown)=>{if(reading)guidance.readings.push(reading);}}));
vi.mock('../media/MediaImageWizard',()=>({MediaImageWizard:({onClose}:{onClose:()=>void})=><button onClick={onClose}>Close portrait studio</button>}));
vi.mock('../api/liveApi',()=>({listSavedMechanicsVersions:vi.fn(),openSavedMechanicsVersion:vi.fn(),saveMechanicsRevision:vi.fn(),recoverMechanicsRevision:vi.fn(),inspectMechanicsRevision:vi.fn(),validateStatblockDefinition:vi.fn()}));
const world='world',draft='11111111-1111-4111-8111-111111111111',resource=revisionFixture as StatblockRevisionResourceV1;
const locator={provider:'dungeonmind' as const,statblock_id:resource.statblock_id,revision_id:resource.revision_id,contract:resource.contract,contract_version:resource.contract_version,definition_digest:resource.definition_digest};
beforeAll(()=>{
 Object.defineProperty(HTMLDialogElement.prototype,'showModal',{configurable:true,value:function(this:HTMLDialogElement){this.setAttribute('open','');}});
 Object.defineProperty(HTMLDialogElement.prototype,'close',{configurable:true,value:function(this:HTMLDialogElement){this.removeAttribute('open');this.dispatchEvent(new Event('close'));}});
});
beforeEach(()=>{
 vi.resetAllMocks();guidance.readings=[];localStorage.clear();sessionStorage.clear();window.history.replaceState({},'', '/build?world=world');
 vi.mocked(api.listSavedMechanicsVersions).mockResolvedValue({world_id:world,draft_id:draft,name:resource.definition.identity.name,original:locator,operations:[],pending:null,next_offset:null});
 vi.mocked(api.openSavedMechanicsVersion).mockResolvedValue({world_id:world,draft_id:draft,locator,resource});
 vi.mocked(api.validateStatblockDefinition).mockResolvedValue({schema:'dmb_statblock_definition_validation_v1',outcome:'success',definition_digest:resource.definition_digest,validation_receipt:resource.validation_receipt} as Awaited<ReturnType<typeof api.validateStatblockDefinition>>);
});
afterEach(cleanup);
async function open(){await userEvent.click(screen.getByRole('button',{name:'Open statblock',exact:true}));const dialog=screen.getByRole('dialog',{name:'Saved statblock editor'});await within(dialog).findByRole('region',{name:'Saved statblock'});return dialog;}
it('loads lazily and keeps one real editor and dirty text across close, reopen and resize',async()=>{
 render(<SessionHost worldId={world} draftId={draft}/>);expect(api.listSavedMechanicsVersions).not.toHaveBeenCalled();
 const dialog=await open(),input=within(dialog).getByLabelText('Creature name');await userEvent.clear(input);await userEvent.type(input,'My retained creature');
 await userEvent.click(within(dialog).getByRole('button',{name:'Expand statblock'}));expect(within(dialog).getByLabelText('Creature name')).toBe(input);
 await userEvent.click(within(dialog).getByRole('button',{name:'Close statblock'}));await waitFor(()=>expect(screen.queryByRole('dialog',{name:'Saved statblock editor'})).toBeNull());expect(input.isConnected).toBe(true);
 await userEvent.click(screen.getByRole('button',{name:'Open statblock',exact:true}));expect(within(dialog).getByLabelText('Creature name')).toBe(input);expect(input).toHaveValue('My retained creature');
 expect(api.listSavedMechanicsVersions).toHaveBeenCalledTimes(1);expect(api.openSavedMechanicsVersion).toHaveBeenCalledTimes(1);expect(api.saveMechanicsRevision).not.toHaveBeenCalled();
});
it('keeps an unknown Save and its original operation when closed during dispatch',async()=>{
 let finish!:(outcome:RevisionSaveOutcome)=>void;vi.mocked(api.saveMechanicsRevision).mockImplementation(()=>new Promise(resolve=>{finish=resolve}));
 render(<SessionHost worldId={world} draftId={draft}/>);const dialog=await open();
 await userEvent.clear(within(dialog).getByLabelText('Creature name'));await userEvent.type(within(dialog).getByLabelText('Creature name'),'Edited creature');await userEvent.click(within(dialog).getByRole('button',{name:'Validate new version'}));
 await waitFor(()=>expect(within(dialog).getByRole('button',{name:'Save new version'})).toBeEnabled());await userEvent.click(within(dialog).getByRole('button',{name:'Save new version'}));await waitFor(()=>expect(api.saveMechanicsRevision).toHaveBeenCalledTimes(1));const body=vi.mocked(api.saveMechanicsRevision).mock.calls[0][1];
 await userEvent.click(within(dialog).getByRole('button',{name:'Close statblock'}));await act(async()=>finish({operation_id:body.operation_id,state:'outcome_unknown',base:locator,result:null,refusal_code:null,change_summary:body.change_summary,created_at:'2026-11-08T00:00:00Z'}));
 await userEvent.click(screen.getByRole('button',{name:'Open statblock',exact:true}));expect(within(dialog).getByRole('button',{name:'Recover Save'})).toBeInTheDocument();expect(within(dialog).getByLabelText('Creature name')).toBeDisabled();expect(api.saveMechanicsRevision).toHaveBeenCalledTimes(1);expect(api.recoverMechanicsRevision).not.toHaveBeenCalled();expect(api.openSavedMechanicsVersion).toHaveBeenCalledTimes(1);
});
it('retains read failure on reopening and retries only through the existing editor',async()=>{
 vi.mocked(api.openSavedMechanicsVersion).mockRejectedValueOnce(new Error('Exact version unavailable'));render(<SessionHost worldId={world} draftId={draft}/>);
 await userEvent.click(screen.getByRole('button',{name:'Open statblock',exact:true}));const dialog=screen.getByRole('dialog',{name:'Saved statblock editor'});await within(dialog).findByText('Exact version unavailable');await userEvent.click(within(dialog).getByRole('button',{name:'Close statblock'}));await userEvent.click(screen.getByRole('button',{name:'Open statblock',exact:true}));
 expect(within(dialog).getByText('Exact version unavailable')).toBeInTheDocument();expect(api.openSavedMechanicsVersion).toHaveBeenCalledTimes(1);await userEvent.click(within(dialog).getByRole('button',{name:'Open saved mechanics',exact:true}));expect(await within(dialog).findByRole('region',{name:'Saved statblock'})).toBeInTheDocument();expect(api.openSavedMechanicsVersion).toHaveBeenCalledTimes(2);expect(api.saveMechanicsRevision).not.toHaveBeenCalled();
});
it('completes first opening under strict lifecycle replay without starting a write',async()=>{
 render(<StrictMode><SessionHost worldId={world} draftId={draft}/></StrictMode>);await open();expect(api.saveMechanicsRevision).not.toHaveBeenCalled();expect(api.recoverMechanicsRevision).not.toHaveBeenCalled();
});
it('ignores a late exact read after the selected statblock scope changes',async()=>{
 let finish!:(value:Awaited<ReturnType<typeof api.openSavedMechanicsVersion>>)=>void;
 const otherLocator={...locator,statblock_id:'sb_other',revision_id:'rev_other'};
 const otherResource=structuredClone(resource);otherResource.statblock_id=otherLocator.statblock_id;otherResource.revision_id=otherLocator.revision_id;otherResource.definition.identity.name='Other creature';
 vi.mocked(api.listSavedMechanicsVersions).mockImplementation(async(id,w)=>({world_id:w,draft_id:id,name:'Creature',original:w===world?locator:otherLocator,operations:[],pending:null,next_offset:null}));
 vi.mocked(api.openSavedMechanicsVersion).mockImplementation(async(id,w)=>w===world?new Promise(resolve=>{finish=resolve}):{world_id:w,draft_id:id,locator:otherLocator,resource:otherResource});
 const mounted=render(<SessionHost worldId={world} draftId={draft}/>);await userEvent.click(screen.getByRole('button',{name:'Open statblock',exact:true}));
 await waitFor(()=>expect(api.openSavedMechanicsVersion).toHaveBeenCalledTimes(1));
 mounted.rerender(<SessionHost worldId="other-world" draftId="22222222-2222-4222-8222-222222222222"/>);
 expect(screen.queryByRole('dialog',{name:'Saved statblock editor'})).toBeNull();
 await userEvent.click(screen.getByRole('button',{name:'Open statblock',exact:true}));
 const dialog=screen.getByRole('dialog',{name:'Saved statblock editor'});await within(dialog).findByRole('heading',{name:'Other creature'});
 await act(async()=>finish({world_id:world,draft_id:draft,locator,resource}));
 expect(within(dialog).getByLabelText('Creature name')).toHaveValue('Other creature');expect(within(dialog).getByRole('heading',{name:'Other creature'})).toBeInTheDocument();expect(api.saveMechanicsRevision).not.toHaveBeenCalled();
});

it('keeps Escape inside the modal so the surrounding tool does not unmount its editor',async()=>{
 const outerEscape=vi.fn();document.addEventListener('keydown',outerEscape);
 try {
  render(<SessionHost worldId={world} draftId={draft}/>);const dialog=await open();
  const input=within(dialog).getByLabelText('Creature name');await userEvent.clear(input);await userEvent.type(input,'Retained after Escape');
  outerEscape.mockClear();expect(fireEvent.keyDown(input,{key:'Escape'})).toBe(true);expect(outerEscape).not.toHaveBeenCalled();
  act(()=>{(dialog as HTMLDialogElement).close();});
  await userEvent.click(screen.getByRole('button',{name:'Open statblock',exact:true}));
  expect(within(dialog).getByLabelText('Creature name')).toBe(input);expect(input).toHaveValue('Retained after Escape');
  expect(api.openSavedMechanicsVersion).toHaveBeenCalledTimes(1);
 } finally {document.removeEventListener('keydown',outerEscape);}
});

it('two hosts and replacement triggers share one mounted editor and its dirty draft',async()=>{
 function Hosts(){const [first,setFirst]=useState(true);return <SavedStatblockProvider worldId={world}>
  {first&&<section aria-label="Surface host"><SavedStatblockButton worldId={world} draftId={draft}/></section>}
  <section aria-label="Conversation host"><SavedStatblockButton worldId={world} draftId={draft}/></section>
  <button onClick={()=>setFirst(false)}>Remove surface trigger</button>
 </SavedStatblockProvider>;}
 render(<Hosts/>);await userEvent.click(within(screen.getByRole('region',{name:'Surface host'})).getByRole('button'));
 const dialog=screen.getByRole('dialog',{name:'Saved statblock editor'});const input=await within(dialog).findByLabelText('Creature name');
 await userEvent.clear(input);await userEvent.type(input,'Single retained draft');
 await userEvent.click(within(dialog).getByRole('button',{name:'Close statblock'}));
 await userEvent.click(screen.getByRole('button',{name:'Remove surface trigger'}));
 await userEvent.click(within(screen.getByRole('region',{name:'Conversation host'})).getByRole('button'));
 expect(within(dialog).getByLabelText('Creature name')).toBe(input);expect(input).toHaveValue('Single retained draft');
 expect(api.listSavedMechanicsVersions).toHaveBeenCalledTimes(1);expect(api.openSavedMechanicsVersion).toHaveBeenCalledTimes(1);
 expect(document.querySelectorAll('[aria-label="Saved mechanics versions"]')).toHaveLength(1);expect(api.saveMechanicsRevision).not.toHaveBeenCalled();
});
it('blocks a different target on dirty summary and allows it only after explicit revert and retry',async()=>{
 const other='22222222-2222-4222-8222-222222222222';
 vi.mocked(api.listSavedMechanicsVersions).mockImplementation(async(id,w)=>({world_id:w,draft_id:id,name:'Creature',original:locator,operations:[],pending:null,next_offset:null}));
 vi.mocked(api.openSavedMechanicsVersion).mockImplementation(async(id,w)=>({world_id:w,draft_id:id,locator,resource}));
 render(<SavedStatblockProvider worldId={world}><section aria-label="First"><SavedStatblockButton worldId={world} draftId={draft}/></section><section aria-label="Second"><SavedStatblockButton worldId={world} draftId={other}/></section></SavedStatblockProvider>);
 await userEvent.click(within(screen.getByRole('region',{name:'First'})).getByRole('button'));
 const dialog=screen.getByRole('dialog',{name:'Saved statblock editor'});await within(dialog).findByLabelText('Creature name');
 await userEvent.type(within(dialog).getByLabelText('Change summary'),' with portrait changes');
 await userEvent.click(within(dialog).getByRole('button',{name:'Close statblock'}));await userEvent.click(within(screen.getByRole('region',{name:'Second'})).getByRole('button'));
 expect(within(dialog).getByRole('alert')).toHaveTextContent('Save, recover or revert');expect(api.openSavedMechanicsVersion).toHaveBeenCalledTimes(1);
 await userEvent.click(within(dialog).getByRole('button',{name:'Revert local edits'}));expect(within(dialog).getByLabelText('Change summary')).toHaveValue('Manual mechanics revision');
 expect(api.openSavedMechanicsVersion).toHaveBeenCalledTimes(1);
 await userEvent.click(within(dialog).getByRole('button',{name:'Close statblock'}));await userEvent.click(within(screen.getByRole('region',{name:'Second'})).getByRole('button'));
 await waitFor(()=>expect(api.openSavedMechanicsVersion).toHaveBeenCalledWith(other,world,locator.revision_id));
 expect(document.querySelectorAll('[aria-label="Saved mechanics versions"]')).toHaveLength(1);expect(api.saveMechanicsRevision).not.toHaveBeenCalled();
});
it('does not provide an isolated fallback editor or open a foreign World target',()=>{
 const first=render(<SavedStatblockButton worldId={world} draftId={draft}/>);expect(screen.getByRole('button',{name:'Open statblock'})).toBeDisabled();first.unmount();
 render(<SavedStatblockProvider worldId="other"><SavedStatblockButton worldId={world} draftId={draft}/></SavedStatblockProvider>);
 expect(screen.getByRole('button',{name:'Open statblock'})).toBeDisabled();expect(api.listSavedMechanicsVersions).not.toHaveBeenCalled();
});
it('the full saved link uses in-document navigation and retains the same editing owner',async()=>{
 render(<SessionHost worldId={world} draftId={draft}/>);const dialog=await open();const input=within(dialog).getByLabelText('Creature name');
 await userEvent.clear(input);await userEvent.type(input,'Retained across surfaces');
 await userEvent.click(within(dialog).getByRole('link',{name:'Open full saved statblock'}));
 await waitFor(()=>expect(window.location.pathname).toBe('/statblock'));
 expect(window.location.search).toContain(`revision=${locator.revision_id}`);
 expect(input.isConnected).toBe(true);
 await waitFor(()=>expect(screen.queryByRole('dialog',{name:'Saved statblock editor'})).toBeNull());
 await userEvent.click(screen.getByRole('button',{name:'Open statblock',exact:true}));
 expect(within(dialog).getByLabelText('Creature name')).toBe(input);expect(input).toHaveValue('Retained across surfaces');expect(api.openSavedMechanicsVersion).toHaveBeenCalledTimes(1);
});

const anotherDraft='22222222-2222-4222-8222-222222222222';
function TwoTargets(){return <SavedStatblockProvider worldId={world}>
 <section aria-label="Original target"><SavedStatblockButton worldId={world} draftId={draft}/></section>
 <section aria-label="Other target"><SavedStatblockButton worldId={world} draftId={anotherDraft}/></section>
</SavedStatblockProvider>;}
async function requestOther(dialog:HTMLElement){await userEvent.click(within(dialog).getByRole('button',{name:'Close statblock'}));await userEvent.click(within(screen.getByRole('region',{name:'Other target'})).getByRole('button'));}
it('retains the original target during uncertain Save and requires recovery plus revert before switching',async()=>{
 vi.mocked(api.saveMechanicsRevision).mockImplementation(async(_d,body)=>({operation_id:body.operation_id,state:'outcome_unknown',base:locator,result:null,refusal_code:null,change_summary:body.change_summary,created_at:'2026-11-08T00:00:00Z'}));
 vi.mocked(api.recoverMechanicsRevision).mockResolvedValue(null);
 render(<TwoTargets/>);await userEvent.click(within(screen.getByRole('region',{name:'Original target'})).getByRole('button'));
 const dialog=screen.getByRole('dialog',{name:'Saved statblock editor'});const input=await within(dialog).findByLabelText('Creature name');
 await userEvent.clear(input);await userEvent.type(input,'Pending creature');await userEvent.click(within(dialog).getByRole('button',{name:'Validate new version'}));
 await waitFor(()=>expect(within(dialog).getByRole('button',{name:'Save new version'})).toBeEnabled());await userEvent.click(within(dialog).getByRole('button',{name:'Save new version'}));
 await within(dialog).findByRole('button',{name:'Recover Save'});const key=vi.mocked(api.saveMechanicsRevision).mock.calls[0][1].operation_id;
 await requestOther(dialog);expect(within(dialog).getByRole('alert')).toHaveTextContent('Save, recover or revert');expect(api.openSavedMechanicsVersion).toHaveBeenCalledTimes(1);
 await userEvent.click(within(dialog).getByRole('button',{name:'Recover Save'}));expect(api.recoverMechanicsRevision).toHaveBeenCalledWith(draft,world,key);
 await requestOther(dialog);expect(api.openSavedMechanicsVersion).toHaveBeenCalledTimes(1);expect(input).toHaveValue('Pending creature');
 expect(api.saveMechanicsRevision).toHaveBeenCalledTimes(1);
});
it('preserves closed portrait studio work until explicit revert instead of switching targets',async()=>{
 render(<TwoTargets/>);await userEvent.click(within(screen.getByRole('region',{name:'Original target'})).getByRole('button'));
 const dialog=screen.getByRole('dialog',{name:'Saved statblock editor'});await within(dialog).findByLabelText('Creature name');
 await userEvent.click(within(dialog).getByRole('button',{name:'Generate or choose portrait'}));
 await userEvent.click(within(dialog).getByRole('button',{name:'Close portrait studio'}));
 await requestOther(dialog);expect(within(dialog).getByRole('alert')).toHaveTextContent('Save, recover or revert');expect(api.openSavedMechanicsVersion).toHaveBeenCalledTimes(1);
 await userEvent.click(within(dialog).getByRole('button',{name:'Generate or choose portrait'}));expect(within(dialog).getByRole('button',{name:'Close portrait studio'})).toBeInTheDocument();
 expect(api.saveMechanicsRevision).not.toHaveBeenCalled();
});

const encounterScope:TourEncounterScope={plan:{kind:'plan',worldId:world,objectId:'plan-one',revision:1,revisionId:'work-one',digest:'a'.repeat(64)},sceneId:'scene',encounterId:'encounter'};
it('forwards admitted presentation scopes from a nested trigger to the real shared editor',async()=>{
 render(<SavedStatblockProvider worldId={world}><TourEncounterProvider scope={encounterScope}><GenerationPlanProvider pin={encounterScope.plan}><SavedStatblockButton worldId={world} draftId={draft}/></GenerationPlanProvider></TourEncounterProvider></SavedStatblockProvider>);
 await open();expect(guidance.readings.filter(reading=>reading.step==='mechanics').at(-1)?.target).toEqual(encounterScope.plan);
 expect(guidance.captureMechanicsScope).toHaveBeenCalledWith(encounterScope.plan,draft);
 expect(api.saveMechanicsRevision).not.toHaveBeenCalled();
});
it('does not retarget dirty work when another host opens the same statblock under a different presentation',async()=>{
 const secondScope={...encounterScope,plan:{...encounterScope.plan,objectId:'plan-two'}};
 render(<SavedStatblockProvider worldId={world}>
  <section aria-label="First scope"><TourEncounterProvider scope={encounterScope}><SavedStatblockButton worldId={world} draftId={draft}/></TourEncounterProvider></section>
  <section aria-label="Second scope"><TourEncounterProvider scope={secondScope}><SavedStatblockButton worldId={world} draftId={draft}/></TourEncounterProvider></section>
 </SavedStatblockProvider>);
 await userEvent.click(within(screen.getByRole('region',{name:'First scope'})).getByRole('button'));
 const dialog=screen.getByRole('dialog',{name:'Saved statblock editor'});const input=await within(dialog).findByLabelText('Creature name');await userEvent.type(input,' dirty');
 await userEvent.click(within(dialog).getByRole('button',{name:'Close statblock'}));await userEvent.click(within(screen.getByRole('region',{name:'Second scope'})).getByRole('button'));
 expect(guidance.readings.filter(reading=>reading.step==='mechanics').at(-1)?.target).toEqual(encounterScope.plan);
 await userEvent.click(within(dialog).getByRole('button',{name:'Revert local edits'}));await userEvent.click(within(dialog).getByRole('button',{name:'Close statblock'}));await userEvent.click(within(screen.getByRole('region',{name:'Second scope'})).getByRole('button'));
 await waitFor(()=>expect(guidance.readings.filter(reading=>reading.step==='mechanics').at(-1)?.target).toEqual(secondScope.plan));
 expect(api.openSavedMechanicsVersion).toHaveBeenCalledTimes(1);expect(api.saveMechanicsRevision).not.toHaveBeenCalled();
});

function exactVersions(){
 const successor={...locator,revision_id:'rev_successor'};const exact=structuredClone(resource);exact.revision_id=successor.revision_id;exact.definition.identity.name='Exact successor';
 vi.mocked(api.listSavedMechanicsVersions).mockResolvedValue({world_id:world,draft_id:draft,name:'Creature',original:locator,operations:[{operation_id:'op-successor',state:'committed',base:locator,result:successor,refusal_code:null,change_summary:'Successor',created_at:'2026-11-08T00:00:00Z'}],pending:null,next_offset:null});
 vi.mocked(api.openSavedMechanicsVersion).mockImplementation(async(_id,_w,revision)=>({world_id:world,draft_id:draft,locator:revision===successor.revision_id?successor:locator,resource:revision===successor.revision_id?exact:resource}));return successor;
}
it('opens the explicit revision despite the hint and shares dirty work with another exact trigger',async()=>{
 const successor=exactVersions();sessionStorage.setItem('dmb-manual-mechanics-writer','writer');localStorage.setItem(`dmb-manual-mechanics:${JSON.stringify(['writer',world,draft])}:selected`,locator.revision_id);
 render(<SavedStatblockProvider worldId={world}><SavedStatblockButton worldId={world} draftId={draft} revisionId={successor.revision_id}/><SavedStatblockButton worldId={world} draftId={draft} revisionId={successor.revision_id} label="Edit this version"/></SavedStatblockProvider>);
 const dialog=await open();expect(api.openSavedMechanicsVersion).toHaveBeenCalledExactlyOnceWith(draft,world,successor.revision_id);const input=within(dialog).getByLabelText('Creature name');expect(input).toHaveValue('Exact successor');await userEvent.clear(input);await userEvent.type(input,'Retained exact edits');await userEvent.click(within(dialog).getByRole('button',{name:'Close statblock'}));await userEvent.click(screen.getByRole('button',{name:'Edit this version'}));expect(within(dialog).getByLabelText('Creature name')).toBe(input);expect(input).toHaveValue('Retained exact edits');expect(api.openSavedMechanicsVersion).toHaveBeenCalledTimes(1);
});
it('guards a different revision and reselects an explicit target after the internal version chooser changes',async()=>{
 const successor=exactVersions();render(<SavedStatblockProvider worldId={world}><SavedStatblockButton worldId={world} draftId={draft} revisionId={successor.revision_id}/><SavedStatblockButton worldId={world} draftId={draft} revisionId={locator.revision_id} label="Open original"/></SavedStatblockProvider>);
 const dialog=await open();const input=within(dialog).getByLabelText('Creature name');await userEvent.clear(input);await userEvent.type(input,'Dirty successor');await userEvent.click(within(dialog).getByRole('button',{name:'Close statblock'}));await userEvent.click(screen.getByRole('button',{name:'Open original'}));expect(within(dialog).getByRole('alert')).toHaveTextContent(/Save, recover or revert/);expect(input).toHaveValue('Dirty successor');expect(api.openSavedMechanicsVersion).toHaveBeenCalledTimes(1);
 await userEvent.click(within(dialog).getByRole('button',{name:'Revert local edits'}));await userEvent.click(within(dialog).getByRole('button',{name:'Close statblock'}));await userEvent.click(screen.getByRole('button',{name:'Open original'}));await waitFor(()=>expect(within(dialog).getByLabelText('Creature name')).toHaveValue(resource.definition.identity.name));
 await userEvent.selectOptions(within(dialog).getByRole('combobox',{name:'Saved mechanics version'}),successor.revision_id);await waitFor(()=>expect(within(dialog).getByLabelText('Creature name')).toHaveValue('Exact successor'));
 await userEvent.click(within(dialog).getByRole('button',{name:'Close statblock'}));await userEvent.click(screen.getByRole('button',{name:'Open original'}));await waitFor(()=>expect(within(dialog).getByLabelText('Creature name')).toHaveValue(resource.definition.identity.name));expect(api.openSavedMechanicsVersion).toHaveBeenLastCalledWith(draft,world,locator.revision_id);expect(api.saveMechanicsRevision).not.toHaveBeenCalled();
});

it('edits the full reader’s exact version with the same retained popup owner',async()=>{
 const successor=exactVersions();render(<SavedStatblockProvider worldId={world}><SavedStatblockFullView target={{worldId:world,draftId:draft,revisionId:successor.revision_id}}/></SavedStatblockProvider>);
 await screen.findByRole('heading',{name:'Exact successor'});await userEvent.click(screen.getByRole('button',{name:'Edit this version'}));const dialog=screen.getByRole('dialog',{name:'Saved statblock editor'});const input=await within(dialog).findByLabelText('Creature name');expect(input).toHaveValue('Exact successor');expect(api.openSavedMechanicsVersion).toHaveBeenCalledTimes(2);for(const call of vi.mocked(api.openSavedMechanicsVersion).mock.calls)expect(call).toEqual([draft,world,successor.revision_id]);
 await userEvent.clear(input);await userEvent.type(input,'Unsent popup edits');await userEvent.click(within(dialog).getByRole('button',{name:'Close statblock'}));expect(screen.getByRole('heading',{name:'Exact successor'})).toBeVisible();await userEvent.click(screen.getByRole('button',{name:'Edit this version'}));expect(within(dialog).getByLabelText('Creature name')).toBe(input);expect(input).toHaveValue('Unsent popup edits');expect(api.openSavedMechanicsVersion).toHaveBeenCalledTimes(2);expect(api.saveMechanicsRevision).not.toHaveBeenCalled();
});
