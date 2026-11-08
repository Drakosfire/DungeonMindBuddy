import {StrictMode} from 'react';
import {act,cleanup,fireEvent,render,screen,waitFor,within} from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import {afterEach,beforeAll,beforeEach,expect,it,vi} from 'vitest';
import * as api from '../api/liveApi';
import revisionFixture from '../../../../tests/fixtures/statblocks/v1/exact-revision-response.json';
import type {StatblockRevisionResourceV1} from '../contracts/dungeonbuddy-statblocks-v1/client';
import type {RevisionSaveOutcome} from './revision/savedMechanicsRevisionTypes';
import {SavedStatblockDialog} from './SavedStatblockDialog';
vi.mock('../api/liveApi',()=>({listSavedMechanicsVersions:vi.fn(),openSavedMechanicsVersion:vi.fn(),saveMechanicsRevision:vi.fn(),recoverMechanicsRevision:vi.fn(),inspectMechanicsRevision:vi.fn(),validateStatblockDefinition:vi.fn()}));
const world='world',draft='11111111-1111-4111-8111-111111111111',resource=revisionFixture as StatblockRevisionResourceV1;
const locator={provider:'dungeonmind' as const,statblock_id:resource.statblock_id,revision_id:resource.revision_id,contract:resource.contract,contract_version:resource.contract_version,definition_digest:resource.definition_digest};
beforeAll(()=>{
 Object.defineProperty(HTMLDialogElement.prototype,'showModal',{configurable:true,value:function(this:HTMLDialogElement){this.setAttribute('open','');}});
 Object.defineProperty(HTMLDialogElement.prototype,'close',{configurable:true,value:function(this:HTMLDialogElement){this.removeAttribute('open');this.dispatchEvent(new Event('close'));}});
});
beforeEach(()=>{
 vi.resetAllMocks();localStorage.clear();sessionStorage.clear();
 vi.mocked(api.listSavedMechanicsVersions).mockResolvedValue({world_id:world,draft_id:draft,name:resource.definition.identity.name,original:locator,operations:[],pending:null,next_offset:null});
 vi.mocked(api.openSavedMechanicsVersion).mockResolvedValue({world_id:world,draft_id:draft,locator,resource});
 vi.mocked(api.validateStatblockDefinition).mockResolvedValue({schema:'dmb_statblock_definition_validation_v1',outcome:'success',definition_digest:resource.definition_digest,validation_receipt:resource.validation_receipt} as Awaited<ReturnType<typeof api.validateStatblockDefinition>>);
});
afterEach(cleanup);
async function open(){await userEvent.click(screen.getByRole('button',{name:'Open statblock',exact:true}));const dialog=screen.getByRole('dialog',{name:'Saved statblock editor'});await within(dialog).findByRole('region',{name:'Saved statblock'});return dialog;}
it('loads lazily and keeps one real editor and dirty text across close, reopen and resize',async()=>{
 render(<SavedStatblockDialog worldId={world} draftId={draft}/>);expect(api.listSavedMechanicsVersions).not.toHaveBeenCalled();
 const dialog=await open(),input=within(dialog).getByLabelText('Creature name');await userEvent.clear(input);await userEvent.type(input,'My retained creature');
 await userEvent.click(within(dialog).getByRole('button',{name:'Expand statblock'}));expect(within(dialog).getByLabelText('Creature name')).toBe(input);
 await userEvent.click(within(dialog).getByRole('button',{name:'Close statblock'}));await waitFor(()=>expect(screen.queryByRole('dialog',{name:'Saved statblock editor'})).toBeNull());expect(input.isConnected).toBe(true);
 await userEvent.click(screen.getByRole('button',{name:'Open statblock',exact:true}));expect(within(dialog).getByLabelText('Creature name')).toBe(input);expect(input).toHaveValue('My retained creature');
 expect(api.listSavedMechanicsVersions).toHaveBeenCalledTimes(1);expect(api.openSavedMechanicsVersion).toHaveBeenCalledTimes(1);expect(api.saveMechanicsRevision).not.toHaveBeenCalled();
});
it('keeps an unknown Save and its original operation when closed during dispatch',async()=>{
 let finish!:(outcome:RevisionSaveOutcome)=>void;vi.mocked(api.saveMechanicsRevision).mockImplementation(()=>new Promise(resolve=>{finish=resolve}));
 render(<SavedStatblockDialog worldId={world} draftId={draft}/>);const dialog=await open();
 await userEvent.clear(within(dialog).getByLabelText('Creature name'));await userEvent.type(within(dialog).getByLabelText('Creature name'),'Edited creature');await userEvent.click(within(dialog).getByRole('button',{name:'Validate new version'}));
 await waitFor(()=>expect(within(dialog).getByRole('button',{name:'Save new version'})).toBeEnabled());await userEvent.click(within(dialog).getByRole('button',{name:'Save new version'}));await waitFor(()=>expect(api.saveMechanicsRevision).toHaveBeenCalledTimes(1));const body=vi.mocked(api.saveMechanicsRevision).mock.calls[0][1];
 await userEvent.click(within(dialog).getByRole('button',{name:'Close statblock'}));await act(async()=>finish({operation_id:body.operation_id,state:'outcome_unknown',base:locator,result:null,refusal_code:null,change_summary:body.change_summary,created_at:'2026-11-08T00:00:00Z'}));
 await userEvent.click(screen.getByRole('button',{name:'Open statblock',exact:true}));expect(within(dialog).getByRole('button',{name:'Recover Save'})).toBeInTheDocument();expect(within(dialog).getByLabelText('Creature name')).toBeDisabled();expect(api.saveMechanicsRevision).toHaveBeenCalledTimes(1);expect(api.recoverMechanicsRevision).not.toHaveBeenCalled();expect(api.openSavedMechanicsVersion).toHaveBeenCalledTimes(1);
});
it('retains read failure on reopening and retries only through the existing editor',async()=>{
 vi.mocked(api.openSavedMechanicsVersion).mockRejectedValueOnce(new Error('Exact version unavailable'));render(<SavedStatblockDialog worldId={world} draftId={draft}/>);
 await userEvent.click(screen.getByRole('button',{name:'Open statblock',exact:true}));const dialog=screen.getByRole('dialog',{name:'Saved statblock editor'});await within(dialog).findByText('Exact version unavailable');await userEvent.click(within(dialog).getByRole('button',{name:'Close statblock'}));await userEvent.click(screen.getByRole('button',{name:'Open statblock',exact:true}));
 expect(within(dialog).getByText('Exact version unavailable')).toBeInTheDocument();expect(api.openSavedMechanicsVersion).toHaveBeenCalledTimes(1);await userEvent.click(within(dialog).getByRole('button',{name:'Open saved mechanics',exact:true}));expect(await within(dialog).findByRole('region',{name:'Saved statblock'})).toBeInTheDocument();expect(api.openSavedMechanicsVersion).toHaveBeenCalledTimes(2);expect(api.saveMechanicsRevision).not.toHaveBeenCalled();
});
it('completes first opening under strict lifecycle replay without starting a write',async()=>{
 render(<StrictMode><SavedStatblockDialog worldId={world} draftId={draft}/></StrictMode>);await open();expect(api.saveMechanicsRevision).not.toHaveBeenCalled();expect(api.recoverMechanicsRevision).not.toHaveBeenCalled();
});
it('ignores a late exact read after the selected statblock scope changes',async()=>{
 let finish!:(value:Awaited<ReturnType<typeof api.openSavedMechanicsVersion>>)=>void;
 const otherLocator={...locator,statblock_id:'sb_other',revision_id:'rev_other'};
 const otherResource=structuredClone(resource);otherResource.statblock_id=otherLocator.statblock_id;otherResource.revision_id=otherLocator.revision_id;otherResource.definition.identity.name='Other creature';
 vi.mocked(api.listSavedMechanicsVersions).mockImplementation(async(id,w)=>({world_id:w,draft_id:id,name:'Creature',original:w===world?locator:otherLocator,operations:[],pending:null,next_offset:null}));
 vi.mocked(api.openSavedMechanicsVersion).mockImplementation(async(id,w)=>w===world?new Promise(resolve=>{finish=resolve}):{world_id:w,draft_id:id,locator:otherLocator,resource:otherResource});
 const mounted=render(<SavedStatblockDialog worldId={world} draftId={draft}/>);await userEvent.click(screen.getByRole('button',{name:'Open statblock',exact:true}));
 await waitFor(()=>expect(api.openSavedMechanicsVersion).toHaveBeenCalledTimes(1));
 mounted.rerender(<SavedStatblockDialog worldId="other-world" draftId="22222222-2222-4222-8222-222222222222"/>);
 const dialog=screen.getByRole('dialog',{name:'Saved statblock editor'});await within(dialog).findByRole('heading',{name:'Other creature'});
 await act(async()=>finish({world_id:world,draft_id:draft,locator,resource}));
 expect(within(dialog).getByLabelText('Creature name')).toHaveValue('Other creature');expect(within(dialog).getByRole('heading',{name:'Other creature'})).toBeInTheDocument();expect(api.saveMechanicsRevision).not.toHaveBeenCalled();
});

it('keeps Escape inside the modal so the surrounding tool does not unmount its editor',async()=>{
 const outerEscape=vi.fn();document.addEventListener('keydown',outerEscape);
 try {
  render(<SavedStatblockDialog worldId={world} draftId={draft}/>);const dialog=await open();
  const input=within(dialog).getByLabelText('Creature name');await userEvent.clear(input);await userEvent.type(input,'Retained after Escape');
  outerEscape.mockClear();expect(fireEvent.keyDown(input,{key:'Escape'})).toBe(true);expect(outerEscape).not.toHaveBeenCalled();
  act(()=>{(dialog as HTMLDialogElement).close();});
  await userEvent.click(screen.getByRole('button',{name:'Open statblock',exact:true}));
  expect(within(dialog).getByLabelText('Creature name')).toBe(input);expect(input).toHaveValue('Retained after Escape');
  expect(api.openSavedMechanicsVersion).toHaveBeenCalledTimes(1);
 } finally {document.removeEventListener('keydown',outerEscape);}
});
