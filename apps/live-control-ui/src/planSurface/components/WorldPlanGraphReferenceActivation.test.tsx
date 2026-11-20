import {act,cleanup,fireEvent,render,screen,waitFor} from '@testing-library/react';
import {afterEach,beforeAll,beforeEach,describe,expect,it,vi} from 'vitest';
import type {Editor} from '@tiptap/core';
import type {NativeGraphCatalog,NativeGraphEntity,NativeAssertion} from '../../api/nativeGraphInspection';
import * as api from '../../api/liveApi';
import {useGraphNodeChipRuntime} from '../../graphReference/GraphNodeChipRuntime';
import {WorldPlanGraphReferenceActivationProvider,useWorldPlanGraphReferenceActivation} from './WorldPlanGraphReferenceActivation';

vi.mock('../../api/liveApi',()=>({getNativeGraphCatalog:vi.fn(),inspectNativeGraph:vi.fn(),listWorldMechanicsAssociations:vi.fn(),postManagedWorldGraphProjection:vi.fn()}));
const pin={managed_world_id:'elderwyld',native_world_id:'native',binding_version:3,revision_id:'r17',scope_mode:'world' as const,campaign_id:null};
const record:NativeAssertion={assertion_id:'a',subject_entity_id:'ent:warehouse',predicate:'dnd5e:name',value:{kind:'literal',value:'Warehouse'},metadata:{scope:[],visibility:{kind:'public'},epistemic_basis:'speculative',claim_mode:'dungeonbuddy.claim:belief',standing:'provisional',evidence_ref_ids:['ev'],temporal_scope:{kind:'unknown'},domain_metadata:[]}};
const catalog:NativeGraphCatalog={schema:'dmb_native_graph_catalog_v1',scope:pin,catalogue:{identity:{space_id:'native',revision_id:'r17'},entities:[{entity_id:'ent:warehouse'}],admitted_assertion_ids:['a'],completeness:{status:'complete',reason:null},request_sha256:'h',result_digest:'d'},assertions:[record]};
const detail:NativeGraphEntity={schema:'dmb_native_graph_entity_v1',scope:pin,entity:{found:true,assertions:[record],evidence:[{evidence_ref_id:'ev',evidence_role:'support'}],completeness:{status:'complete',reason:null}}};
const editor={isDestroyed:false} as Editor;
let retained:(nodeId:string,trigger?:HTMLElement)=>void;
function Trigger({id='ent:warehouse',label='Open warehouse'}:{id?:string;label?:string}) {
 const {activateNode}=useWorldPlanGraphReferenceActivation();retained=activateNode;
 return <button onClick={e=>activateNode(id,e.currentTarget)}>{label}</button>;
}
function EditorTrigger({source=editor}:{source?:Editor}) {
 const runtime=useGraphNodeChipRuntime();
 return <button onClick={()=>runtime.onSelectEditorNode?.('ent:warehouse',source)}>Editor link</button>;
}
function tree({worldId='elderwyld',ownerKey='plan-a',currentEditor=editor,enabled=true,id='ent:warehouse'}:{worldId?:string;ownerKey?:string;currentEditor?:Editor;enabled?:boolean;id?:string}={}) {
 return <WorldPlanGraphReferenceActivationProvider worldId={worldId} ownerKey={ownerKey} editor={currentEditor} enabled={enabled}><Trigger id={id}/><EditorTrigger/></WorldPlanGraphReferenceActivationProvider>;
}
beforeAll(()=>{HTMLDialogElement.prototype.showModal=function(){this.setAttribute('open','')};HTMLDialogElement.prototype.close=function(){this.removeAttribute('open')};});
afterEach(cleanup);
beforeEach(()=>{vi.resetAllMocks();vi.mocked(api.getNativeGraphCatalog).mockResolvedValue(catalog);vi.mocked(api.inspectNativeGraph).mockResolvedValue(detail);vi.mocked(api.listWorldMechanicsAssociations).mockResolvedValue([]);});

describe('current Plan native object activation',()=>{
 it('does not eagerly load the old projection and opens an exact native object through the shared preview',async()=>{
  render(tree());expect(api.getNativeGraphCatalog).not.toHaveBeenCalled();expect(api.postManagedWorldGraphProjection).not.toHaveBeenCalled();
  const trigger=screen.getByRole('button',{name:'Open warehouse'});trigger.focus();fireEvent.click(trigger);
  expect(await screen.findByRole('dialog',{name:'Object · Warehouse'})).toBeInTheDocument();await screen.findByText('Warehouse · name: Warehouse');
  expect(api.getNativeGraphCatalog).toHaveBeenCalledWith({managed_world_id:'elderwyld',scope_mode:'world',campaign_id:null},expect.any(AbortSignal));
  expect(api.inspectNativeGraph).toHaveBeenCalledWith(pin,{kind:'entity',entity_id:'ent:warehouse'},expect.any(AbortSignal));
  expect(screen.getByRole('button',{name:'Close object preview'})).toHaveFocus();fireEvent.click(screen.getByRole('button',{name:'Close object preview'}));
  await waitFor(()=>expect(trigger).toHaveFocus());expect(api.postManagedWorldGraphProjection).not.toHaveBeenCalled();
 });
 it('uses the native exact-source reader only after opening a citation',async()=>{
  vi.mocked(api.inspectNativeGraph).mockImplementation(async(_pin,selection)=>selection.kind==='entity'?detail:{schema:'dmb_native_graph_source_v1',scope:pin,source:{status:'available',text:'Exact warehouse passage.',source_artifact_id:'src',source_revision_id:'srev',body_sha256:'body',span_sha256:'span',span_start_byte:0,span_end_byte:24,source_authority_epoch:3}});
  render(tree());fireEvent.click(screen.getByRole('button',{name:'Open warehouse'}));fireEvent.click(await screen.findByRole('button',{name:'Read supporting source'}));expect(await screen.findByText('Exact warehouse passage.')).toBeInTheDocument();
  expect(api.inspectNativeGraph).toHaveBeenLastCalledWith(pin,{kind:'source',assertion_id:'a',evidence_ref_id:'ev'});
 });
 it('retries a failed current catalogue read without a legacy fallback',async()=>{
  vi.mocked(api.getNativeGraphCatalog).mockRejectedValueOnce(new Error('Read unavailable'));render(tree());fireEvent.click(screen.getByRole('button',{name:'Open warehouse'}));expect(await screen.findByRole('alert')).toHaveTextContent('Read unavailable');fireEvent.click(screen.getByRole('button',{name:'Retry object'}));expect(await screen.findByRole('dialog',{name:'Object · Warehouse'})).toBeInTheDocument();
 });
 it.each(['document','World','editor','disabled'] as const)('discards a delayed read and retained callbacks after %s changes',async change=>{
  let finish!:(packet:NativeGraphCatalog)=>void;vi.mocked(api.getNativeGraphCatalog).mockReturnValueOnce(new Promise(resolve=>{finish=resolve}));
  const view=render(tree());fireEvent.click(screen.getByRole('button',{name:'Open warehouse'}));const old=retained!;const signal=vi.mocked(api.getNativeGraphCatalog).mock.calls[0][1]!;
  view.rerender(tree(change==='document'?{ownerKey:'plan-b'}:change==='World'?{worldId:'other'}:change==='editor'?{currentEditor:{isDestroyed:false} as Editor}:{enabled:false}));
  expect(signal.aborted).toBe(true);await act(async()=>{finish(catalog);old('ent:warehouse');});expect(screen.queryByRole('dialog')).not.toBeInTheDocument();expect(api.getNativeGraphCatalog).toHaveBeenCalledTimes(1);expect(api.inspectNativeGraph).not.toHaveBeenCalled();
 });
 it('aborts on unmount and rejects the retained activation callback',async()=>{
  let finish!:(packet:NativeGraphCatalog)=>void;vi.mocked(api.getNativeGraphCatalog).mockReturnValueOnce(new Promise(resolve=>{finish=resolve}));const view=render(tree());fireEvent.click(screen.getByRole('button',{name:'Open warehouse'}));const old=retained!;const signal=vi.mocked(api.getNativeGraphCatalog).mock.calls[0][1]!;view.unmount();await act(async()=>{finish(catalog);old('ent:warehouse');});expect(signal.aborted).toBe(true);expect(api.getNativeGraphCatalog).toHaveBeenCalledTimes(1);expect(api.inspectNativeGraph).not.toHaveBeenCalled();
 });
 it('accepts only the owning editor, leaving nested reader editors inert',async()=>{
  const view=render(<WorldPlanGraphReferenceActivationProvider worldId="elderwyld" ownerKey="plan" editor={editor} enabled><EditorTrigger source={{isDestroyed:false} as Editor}/></WorldPlanGraphReferenceActivationProvider>);
  fireEvent.click(screen.getByRole('button',{name:'Editor link'}));expect(api.getNativeGraphCatalog).not.toHaveBeenCalled();view.rerender(tree());fireEvent.click(screen.getByRole('button',{name:'Editor link'}));expect(await screen.findByRole('dialog',{name:'Object · Warehouse'})).toBeInTheDocument();
 });
 it('closes an opened preview on document change and discards a late native entity read',async()=>{
  let finish!:(packet:NativeGraphEntity)=>void;vi.mocked(api.inspectNativeGraph).mockReturnValueOnce(new Promise(resolve=>{finish=resolve}));
  const view=render(tree());fireEvent.click(screen.getByRole('button',{name:'Open warehouse'}));await screen.findByRole('dialog',{name:'Object · Warehouse'});
  const signal=vi.mocked(api.inspectNativeGraph).mock.calls[0][2]!;view.rerender(tree({ownerKey:'plan-b'}));expect(signal.aborted).toBe(true);
  await act(async()=>finish(detail));expect(screen.queryByRole('dialog')).not.toBeInTheDocument();expect(screen.queryByText('Warehouse · name: Warehouse')).not.toBeInTheDocument();
 });
 it('does not move scroll position when closing back to the original Plan control',async()=>{
  const scroll=vi.spyOn(window,'scrollTo').mockImplementation(()=>{});const original=window.scrollY;Object.defineProperty(window,'scrollY',{configurable:true,value:720});
  render(tree());const trigger=screen.getByRole('button',{name:'Open warehouse'});trigger.focus();fireEvent.click(trigger);await screen.findByRole('dialog',{name:'Object · Warehouse'});
  fireEvent.click(screen.getByRole('button',{name:'Close object preview'}));await waitFor(()=>expect(trigger).toHaveFocus());expect(scroll).not.toHaveBeenCalled();Object.defineProperty(window,'scrollY',{configurable:true,value:original});scroll.mockRestore();
 });
 it('closes a delayed read with Escape and prevents its late completion from reopening',async()=>{
  let finish!:(packet:NativeGraphCatalog)=>void;vi.mocked(api.getNativeGraphCatalog).mockReturnValueOnce(new Promise(resolve=>{finish=resolve}));render(tree());const trigger=screen.getByRole('button',{name:'Open warehouse'});trigger.focus();fireEvent.click(trigger);fireEvent.keyDown(screen.getByRole('button',{name:'Close object'}),{key:'Escape'});await act(async()=>finish(catalog));expect(screen.queryByRole('dialog')).not.toBeInTheDocument();await waitFor(()=>expect(trigger).toHaveFocus());
 });
 it.each(['bad id','ent:missing'])('does not resolve %s by a matching label',async id=>{
  render(tree({id}));fireEvent.click(screen.getByRole('button',{name:'Open warehouse'}));expect(await screen.findByRole('alert')).toHaveTextContent(id==='bad id'?'invalid node ID':'unavailable');expect(api.inspectNativeGraph).not.toHaveBeenCalled();
 });
 it('rejects a campaign-scoped or different-World catalogue before object preview',async()=>{
  vi.mocked(api.getNativeGraphCatalog).mockResolvedValue({...catalog,scope:{...pin,scope_mode:'campaign',campaign_id:'c1'}});render(tree());fireEvent.click(screen.getByRole('button',{name:'Open warehouse'}));expect(await screen.findByRole('alert')).toHaveTextContent('did not match this World');expect(api.inspectNativeGraph).not.toHaveBeenCalled();
 });
});
