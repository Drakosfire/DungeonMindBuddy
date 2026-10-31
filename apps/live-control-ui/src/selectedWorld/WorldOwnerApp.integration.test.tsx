import {act,cleanup,fireEvent,render,screen,waitFor} from '@testing-library/react';
import {useEffect,useMemo,useState} from 'react';
import {afterEach,beforeEach,expect,it,vi} from 'vitest';
import {App} from '../App';
import * as api from '../api/liveApi';
import * as combatApi from '../combat/combatApi';
import {useAgentInteraction} from '../agentInteraction/useAgentInteraction';
import {WorldPlanConversationRegistration} from '../agentInteraction/WorldAgentConversation';
import {useSelectedWorld} from './SelectedWorldContext';
import type {WorldPlanAgentConversationProps} from '../planSurface/components/WorldPlanAgentConversation';

const owner=vi.hoisted(()=>({next:0,mounts:[] as string[],unmounts:[] as string[],capture:vi.fn(),save:vi.fn(),last:null as WorldPlanAgentConversationProps|null}));
vi.mock('../planSurface/components/WorldPlanAgentConversation',()=>({WorldPlanAgentConversation:(props:WorldPlanAgentConversationProps)=>{
 owner.last=props;const [draft,setDraft]=useState('');const [identity]=useState(()=>++owner.next);
 useEffect(()=>{owner.mounts.push(props.worldId);return()=>{owner.unmounts.push(props.worldId)}},[]);
 return <section data-testid="world-controller" hidden={!props.visible} data-owner={identity} data-world={props.worldId}
   data-document={props.documentId??''} data-bridge={String(Boolean(props.editBridge))}>
  <input aria-label="Unsent World draft" value={draft} onChange={event=>setDraft(event.target.value)}/>
  {props.visible&&props.editBridge ? <button onClick={()=>{void props.editBridge!.capture()}}>Use current Plan bridge</button>:null}
 </section>;
}}));
vi.mock('../planSurface/PlanSurfacePage',()=>({PlanSurfacePage:()=>{
 const world=useSelectedWorld();const worldId=world.kind==='managed'?world.worldId:'';
 const doc=new URLSearchParams(window.location.search).get('documentId')??'doc-A';
 const props=useMemo<WorldPlanAgentConversationProps>(()=>({worldId,worldName:worldId,documentId:doc,surfaceInstanceId:doc,revision:1,
  editBridge:{capture:owner.capture,apply:vi.fn()},onSavePlan:owner.save,savePlanEnabled:true,draftGeneration:0,selectionGeneration:0,savedDirty:false,pageReady:true,saveInFlight:false}),[worldId,doc]);
 return <main data-testid="plan-page"><WorldPlanConversationRegistration {...props}/><button onClick={owner.capture}>Edit {doc}</button></main>;
}}));
vi.mock('../playSurface/PlaySurfacePage',()=>({PlaySurfacePage:()=> <main data-testid="play-page">Play route</main>}));
vi.mock('../buildSurface/BuildSurfacePage',()=>({BuildSurfacePage:()=> <main data-testid="build-page">Build route</main>}));
vi.mock('../agentInteraction/AgentInteractionChrome',()=>({AgentInteractionChrome:()=> <div data-testid="agent-chrome"/>}));
vi.mock('../surfaceInteraction/toolHost/ToolHost',()=>({ToolHost:()=>{const state=useAgentInteraction();return <div data-testid="tools" data-surface={state.surfaceInteractionPublication?.surfaceId??''}/>;}}));
vi.mock('../planSurface/projection/LegacyProjectionHostAdapter',()=>({LegacyProjectionHostAdapter:()=> <div data-testid="projections"/>}));

const worlds=['A','B'].map(id=>({schema_version:'dmb_world_container_record_v1' as const,world_id:id,name:id,source_root_relpath:`corpus/${id}`,created_at:'2026-01-01'}));
function record(id:string,world='A'){return {schema_version:'dmb_world_owned_plan_record_v2',scope_mode:'world',document_id:id,title:id,world_id:world,campaign_id:null,kind:'plan',status:'active',content_status:'committed',revision:1} as never}
function deferred<T>(){let resolve!:(value:T)=>void;let reject!:(reason:unknown)=>void;const promise=new Promise<T>((r,j)=>{resolve=r;reject=j});return{promise,resolve,reject}}
function navigate(url:string){act(()=>{window.history.pushState({},'',url);window.dispatchEvent(new PopStateEvent('popstate'))})}
async function start(url='/plan?world=A&documentId=doc-A'){
 window.history.replaceState({},'',url);const view=render(<App/>);
 await screen.findByTestId('plan-page');await screen.findByRole('textbox',{name:'Unsent World draft'});
 return view;
}
beforeEach(()=>{
 localStorage.clear();owner.mounts=[];owner.unmounts=[];owner.capture.mockReset();
 vi.spyOn(api,'listWorldContainers').mockResolvedValue({schema_version:'dmb_world_container_registry_v1',records:worlds});
 vi.spyOn(api,'getWorkspaceDocumentAny').mockImplementation(async id=>record(id));
 vi.spyOn(api,'getSourceBundle').mockResolvedValue({schema:'dmb_ingestion_source_bundle_v1',campaigns:{}} as never);
});
afterEach(()=>{cleanup();vi.restoreAllMocks();localStorage.clear()});

it('retains the actual App World controller and draft across Plan→Play→Plan and view/hash changes',async()=>{
 await start();const node=screen.getByTestId('world-controller');fireEvent.change(screen.getByRole('textbox',{name:'Unsent World draft'}),{target:{value:'Keep this unsent'}});
 navigate('/plan?world=A&documentId=doc-A&view=cards#second');expect(screen.getByTestId('world-controller')).toBe(node);
 navigate('/play?world=A');await screen.findByTestId('play-page');expect(screen.getByTestId('world-controller')).toBe(node);
 navigate('/plan?world=A&documentId=doc-A');expect(screen.getByRole('status')).toHaveTextContent('Verifying page selection');await screen.findByTestId('plan-page');
 expect(screen.getByTestId('world-controller')).toBe(node);expect(screen.getByRole('textbox',{name:'Unsent World draft'})).toHaveValue('Keep this unsent');
 expect(owner.mounts).toEqual(['A']);expect(api.listWorldContainers).toHaveBeenCalledTimes(2);expect(api.getWorkspaceDocumentAny).toHaveBeenCalledTimes(2);
});
it('keeps private memory during delayed same-World page admission but retires every old page action and bridge',async()=>{
 await start();const node=screen.getByTestId('world-controller');fireEvent.change(screen.getByRole('textbox',{name:'Unsent World draft'}),{target:{value:'Frozen draft'}});
 const gate=deferred<Awaited<ReturnType<typeof api.getWorkspaceDocumentAny>>>();vi.mocked(api.getWorkspaceDocumentAny).mockReturnValueOnce(gate.promise);
 navigate('/plan?world=A&documentId=doc-next');
 expect(screen.getByRole('status')).toHaveTextContent('Verifying page selection');expect(screen.getByTestId('world-controller')).toBe(node);expect(node).not.toBeVisible();expect(node).toHaveAttribute('data-bridge','false');
 for(const id of ['plan-page','agent-chrome','tools','projections'])expect(screen.queryByTestId(id)).not.toBeInTheDocument();
 expect(screen.queryByRole('button',{name:'Use current Plan bridge'})).not.toBeInTheDocument();expect(owner.capture).not.toHaveBeenCalled();
 expect(owner.last?.onSavePlan).toBeUndefined();expect(owner.last?.savePlanEnabled).toBe(false);expect(owner.last?.presentationHosts).toBeUndefined();
 await act(async()=>gate.resolve(record('doc-next')));await screen.findByTestId('plan-page');
 expect(screen.getByTestId('world-controller')).toBe(node);expect(node).toHaveAttribute('data-document','doc-next');expect(node).toHaveAttribute('data-bridge','true');
 expect(screen.getByRole('textbox',{name:'Unsent World draft'})).toHaveValue('Frozen draft');
 expect(api.getWorkspaceDocumentAny).toHaveBeenCalledTimes(2);expect(api.listWorldContainers).toHaveBeenCalledTimes(2);
});
it('removes private old-World ownership immediately while a different World is being verified',async()=>{
 await start();const node=screen.getByTestId('world-controller');fireEvent.change(screen.getByRole('textbox',{name:'Unsent World draft'}),{target:{value:'A private'}});
 const gate=deferred<Awaited<ReturnType<typeof api.listWorldContainers>>>();vi.mocked(api.listWorldContainers).mockReturnValueOnce(gate.promise);
 navigate('/plan?world=B');expect(screen.queryByTestId('world-controller')).not.toBeInTheDocument();expect(node).not.toBeInTheDocument();expect(screen.getByRole('status')).toHaveTextContent('Verifying World');
 await act(async()=>gate.resolve({schema_version:'dmb_world_container_registry_v1',records:worlds}));await screen.findByTestId('plan-page');
 expect(screen.getByTestId('world-controller')).toHaveAttribute('data-world','B');expect(screen.getByRole('textbox',{name:'Unsent World draft'})).toHaveValue('');
 expect(owner.unmounts).toContain('A');
});
it('fails closed for an incoming mismatched document and only admits a fresh owner after explicit retry',async()=>{
 await start();const node=screen.getByTestId('world-controller');
 vi.mocked(api.getWorkspaceDocumentAny).mockResolvedValueOnce(record('wrong','B'));
 navigate('/plan?world=A&documentId=wrong');await screen.findByRole('alert');
 expect(screen.queryByTestId('world-controller')).not.toBeInTheDocument();expect(screen.queryByTestId('plan-page')).not.toBeInTheDocument();
 vi.mocked(api.getWorkspaceDocumentAny).mockResolvedValueOnce(record('wrong','A'));
 fireEvent.click(screen.getByRole('button',{name:'Retry selection'}));await screen.findByTestId('plan-page');
 expect(screen.getByTestId('world-controller')).not.toBe(node);expect(screen.getByTestId('world-controller')).toHaveAttribute('data-document','wrong');
});
it.each(['resolve','reject'] as const)('ignores an abandoned document %s after returning to the accepted selector',async settlement=>{
 await start();const node=screen.getByTestId('world-controller');const gate=deferred<Awaited<ReturnType<typeof api.getWorkspaceDocumentAny>>>();vi.mocked(api.getWorkspaceDocumentAny).mockReturnValueOnce(gate.promise);
 navigate('/plan?world=A&documentId=abandoned');navigate('/plan?world=A&documentId=doc-A');await screen.findByTestId('plan-page');
 await act(async()=>{if(settlement==='resolve')gate.resolve(record('abandoned','B'));else gate.reject(new Error('late metadata failure'))});
 expect(screen.queryByRole('alert')).not.toBeInTheDocument();expect(screen.getByTestId('world-controller')).toBe(node);expect(node).toHaveAttribute('data-document','doc-A');
 expect(api.listWorldContainers).toHaveBeenCalledTimes(2);
});
it('can retain a server-verified inferred document World when navbar navigation names that same World explicitly',async()=>{
 await start('/plan?documentId=doc-A');const node=screen.getByTestId('world-controller');
 fireEvent.change(screen.getByRole('textbox',{name:'Unsent World draft'}),{target:{value:'Inferred but verified'}});
 navigate('/play?world=A');await screen.findByTestId('play-page');expect(screen.getByTestId('world-controller')).toBe(node);
 navigate('/plan?world=A&documentId=doc-A');await screen.findByTestId('plan-page');
 expect(screen.getByTestId('world-controller')).toBe(node);expect(screen.getByRole('textbox',{name:'Unsent World draft'})).toHaveValue('Inferred but verified');
});

it('never retains the previous private owner for an unknown requested World',async()=>{
 await start();navigate('/plan?world=unknown');
 expect(screen.queryByTestId('world-controller')).not.toBeInTheDocument();
 await screen.findByRole('alert');expect(screen.queryByTestId('world-controller')).not.toBeInTheDocument();expect(screen.queryByTestId('plan-page')).not.toBeInTheDocument();
});

it('boots native Combat through the actual App with a verified World and no automatic write',async()=>{
 const list=vi.spyOn(combatApi,'listWorldCombatEncounters').mockResolvedValue([]);
 const create=vi.spyOn(combatApi,'createWorldCombatEncounter');const save=vi.spyOn(combatApi,'saveWorldCombatEncounter');
 window.history.replaceState({},'','/combat?world=A');render(<App/>);
 expect(await screen.findByRole('main',{name:'Combat encounters'})).toBeInTheDocument();
 expect(await screen.findByText(/No encounters yet/)).toBeInTheDocument();
 expect(list).toHaveBeenCalledExactlyOnceWith('A');expect(create).not.toHaveBeenCalled();expect(save).not.toHaveBeenCalled();
 expect(screen.getByTestId('tools')).toHaveAttribute('data-surface','combat');
 expect(screen.queryByRole('heading',{name:'Command Board'})).not.toBeInTheDocument();
});
it('retains World dialogue across Plan→native Combat→Plan while suspending its Plan edit bridge',async()=>{
 vi.spyOn(combatApi,'listWorldCombatEncounters').mockResolvedValue([]);
 await start();const controller=screen.getByTestId('world-controller');
 fireEvent.change(screen.getByRole('textbox',{name:'Unsent World draft'}),{target:{value:'Unsent planning thought'}});
 navigate('/combat?world=A');await screen.findByRole('main',{name:'Combat encounters'});
 expect(screen.getByTestId('world-controller')).toBe(controller);expect(owner.last?.editBridge).toBeNull();
 expect(screen.queryByRole('button',{name:'Use current Plan bridge'})).not.toBeInTheDocument();
 navigate('/plan?world=A&documentId=doc-A');await screen.findByTestId('plan-page');
 expect(screen.getByTestId('world-controller')).toBe(controller);
 expect(screen.getByRole('textbox',{name:'Unsent World draft'})).toHaveValue('Unsent planning thought');
});


it.each([null,'longmont-c2'])('admits a Page by its exact owning World with campaign tag %s',async campaign_id=>{
 vi.mocked(api.getWorkspaceDocumentAny).mockResolvedValue({...record('page'),schema_version:'dmb_workspace_document_record_v1',kind:'worldbuilding_source',campaign_id,world_id:'A'} as never);
 window.history.replaceState({},'','/build?world=A&documentId=page');render(<App/>);
 await screen.findByTestId('build-page');expect(screen.queryByRole('alert')).not.toBeInTheDocument();
 navigate('/build?world=B&documentId=page');await screen.findByRole('alert');expect(screen.queryByTestId('build-page')).not.toBeInTheDocument();
});
