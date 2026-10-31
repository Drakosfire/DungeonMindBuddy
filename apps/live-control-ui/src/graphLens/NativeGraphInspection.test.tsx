import {act,cleanup,fireEvent,render,screen,waitFor,within} from '@testing-library/react';
import {afterEach,beforeAll,beforeEach,expect,it,vi} from 'vitest';
import {LoadedGraphBrowser} from './LoadedWorldGraphExplorer';
import {NativeGraphInspection} from './NativeGraphInspection';
import type {NativeGraphCatalog,NativeGraphEntity,NativeGraphSource,NativeAssertion} from '../api/nativeGraphInspection';
import {getNativeGraphCatalog,inspectNativeGraph} from '../api/liveApi';
vi.mock('../api/liveApi',()=>({getNativeGraphCatalog:vi.fn(),inspectNativeGraph:vi.fn()}));
vi.mock('./useWorldGraphLensProjection',()=>({useWorldGraphLensProjectionDemand:vi.fn(),useOptionalWorldGraphLensProjection:()=>null}));
vi.mock('../selectedWorld/SelectedWorldContext',()=>({useSelectedWorld:()=>({kind:'managed',worldId:'w',name:'World'})}));
beforeAll(()=>{HTMLDialogElement.prototype.showModal=function(){this.setAttribute('open','')};HTMLDialogElement.prototype.close=function(){this.removeAttribute('open')};});
afterEach(cleanup);
const scope={managed_world_id:'w',native_world_id:'n',binding_version:3,revision_id:'r',scope_mode:'world' as const,campaign_id:null};
const record=(id:number):NativeAssertion=>({assertion_id:`a${id}`,subject_entity_id:`e${id}`,predicate:'dnd5e:name',value:{kind:'literal',value:`Object ${id}`},metadata:{scope:[{axis:'campaign',value:'c1'}],visibility:{kind:'public'},epistemic_basis:'speculative',claim_mode:'dungeonbuddy.claim:belief',standing:'provisional',evidence_ref_ids:['ev'],temporal_scope:{kind:'unknown'},domain_metadata:[]}});
const packet:NativeGraphCatalog={schema:'dmb_native_graph_catalog_v1',scope,catalogue:{identity:{space_id:'n',revision_id:'r'},entities:Array.from({length:31},(_,i)=>({entity_id:`e${i}`})),admitted_assertion_ids:Array.from({length:30},(_,i)=>`a${i}`),completeness:{status:'complete',reason:null},request_sha256:'hash',result_digest:'digest'},assertions:Array.from({length:30},(_,i)=>record(i))};
const detail=(id=0):NativeGraphEntity=>({schema:'dmb_native_graph_entity_v1',scope,entity:{found:true,assertions:[record(id)],evidence:[{evidence_ref_id:'ev',evidence_role:'support'}],completeness:{status:'complete',reason:null}}});
const source:NativeGraphSource={schema:'dmb_native_graph_source_v1',scope,source:{status:'available',text:'Only the exact towér passage.',source_artifact_id:'src',source_revision_id:'srev',body_sha256:'body',span_sha256:'span',span_start_byte:0,span_end_byte:30,source_authority_epoch:23}};
beforeEach(()=>{vi.resetAllMocks();vi.mocked(getNativeGraphCatalog).mockResolvedValue(packet);vi.mocked(inspectNativeGraph).mockImplementation(async(_pin,s)=>s.kind==='entity'?detail(Number(s.entity_id.slice(1))):source)});
it('uses the existing modal, loads native only on explicit demand and opens only selected sources',async()=>{
 const original=JSON.stringify(packet);
 render(<LoadedGraphBrowser worldName="World" managedWorldId="w" projection={null} projectionState="idle" projectionError={null}/>);
 expect(getNativeGraphCatalog).not.toHaveBeenCalled();fireEvent.click(screen.getByRole('button',{name:'Explore graph'}));expect(getNativeGraphCatalog).not.toHaveBeenCalled();
 fireEvent.click(screen.getByRole('button',{name:'Reviewed Graph · read-only'}));expect(await screen.findByText(/31 objects/)).toBeInTheDocument();
 expect(within(screen.getByRole('navigation',{name:'Reviewed Graph objects'})).getAllByRole('button')).toHaveLength(31);
 expect(screen.getByRole('button',{name:'e30'})).toBeInTheDocument();expect(inspectNativeGraph).not.toHaveBeenCalled();
 fireEvent.click(screen.getByRole('button',{name:'Object 0'}));expect(await screen.findByText('belief · speculative · provisional')).toBeInTheDocument();expect(inspectNativeGraph).toHaveBeenCalledTimes(1);
 fireEvent.click(screen.getByRole('button',{name:'Read supporting source'}));expect(await screen.findByText(source.source.text)).toBeInTheDocument();
 expect(inspectNativeGraph).toHaveBeenLastCalledWith(scope,{kind:'source',assertion_id:'a0',evidence_ref_id:'ev'});
 fireEvent.click(screen.getByRole('button',{name:'Object 0'}));expect(screen.getByText(source.source.text)).toBeInTheDocument();expect(screen.queryByText('Loading selected object…')).not.toBeInTheDocument();expect(inspectNativeGraph).toHaveBeenCalledTimes(2);
 fireEvent.click(screen.getByRole('button',{name:'Object 1'}));await screen.findByText('Object 1 · name: Object 1');expect(screen.queryByText(source.source.text)).not.toBeInTheDocument();
 fireEvent.click(screen.getByRole('button',{name:'Close graph'}));expect(screen.queryByRole('region',{name:'Reviewed Graph inspection'})).not.toBeInTheDocument();expect(JSON.stringify(packet)).toBe(original);
});
it('discards an old catalogue after World switch',async()=>{
 let finish!:(p:NativeGraphCatalog)=>void;vi.mocked(getNativeGraphCatalog).mockImplementationOnce(()=>new Promise(resolve=>{finish=resolve}));
 const view=render(<NativeGraphInspection worldId="w"/>);vi.mocked(getNativeGraphCatalog).mockResolvedValue({...packet,scope:{...scope,managed_world_id:'next'}});view.rerender(<NativeGraphInspection worldId="next"/>);await screen.findByText(/31 objects/);
 await act(async()=>finish({...packet,assertions:[record(999)],catalogue:{...packet.catalogue,entities:[{entity_id:'e999'}]}}));expect(screen.queryByRole('button',{name:'Object 999'})).not.toBeInTheDocument();
 expect(getNativeGraphCatalog).toHaveBeenLastCalledWith({managed_world_id:'next',scope_mode:'world',campaign_id:null},expect.any(AbortSignal));
});
it('discards a late selected detail',async()=>{
 let finish!:(p:NativeGraphEntity)=>void;vi.mocked(inspectNativeGraph).mockImplementationOnce(()=>new Promise(resolve=>{finish=resolve}));
 render(<NativeGraphInspection worldId="w"/>);await screen.findByText(/31 objects/);fireEvent.click(screen.getByRole('button',{name:'Object 0'}));fireEvent.click(screen.getByRole('button',{name:'Object 1'}));
 await waitFor(()=>expect(within(screen.getByRole('article',{name:'Reviewed object details'})).getByRole('heading')).toHaveTextContent('Object 1'));await act(async()=>finish(detail(0)));
 expect(screen.getByRole('article',{name:'Reviewed object details'})).toHaveTextContent('Object 1 · name: Object 1');expect(screen.getByRole('article',{name:'Reviewed object details'})).not.toHaveTextContent('Object 0 · name');
});
it('distinguishes complete empty from unavailable authority and permits retry',async()=>{
 vi.mocked(getNativeGraphCatalog).mockRejectedValueOnce(new Error('Authority unavailable'));render(<NativeGraphInspection worldId="w"/>);expect(await screen.findByRole('alert')).toHaveTextContent('Authority unavailable');expect(screen.queryByText(/No reviewed objects/)).not.toBeInTheDocument();
 vi.mocked(getNativeGraphCatalog).mockResolvedValue({...packet,catalogue:{...packet.catalogue,entities:[]},assertions:[]});fireEvent.click(screen.getByRole('button',{name:'Refresh reviewed Graph'}));expect(await screen.findByText('No reviewed objects are available in this view.')).toBeInTheDocument();expect(screen.getByText(/0 objects/)).toBeInTheDocument();
});

it('retains a selected refusal on repeated click and recovers through explicit refresh',async()=>{
 vi.mocked(inspectNativeGraph).mockRejectedValueOnce(new Error('Record unavailable'));
 render(<NativeGraphInspection worldId="w"/>);await screen.findByText(/31 objects/);
 fireEvent.click(screen.getByRole('button',{name:'Object 0'}));expect(await screen.findByRole('alert')).toHaveTextContent('Record unavailable');
 fireEvent.click(screen.getByRole('button',{name:'Object 0'}));expect(screen.getByRole('alert')).toHaveTextContent('Record unavailable');expect(screen.queryByText('Loading selected object…')).not.toBeInTheDocument();expect(inspectNativeGraph).toHaveBeenCalledTimes(1);
 fireEvent.click(screen.getByRole('button',{name:'Refresh reviewed Graph'}));await screen.findByText(/31 objects/);
 fireEvent.click(screen.getByRole('button',{name:'Object 0'}));expect(await screen.findByText('belief · speculative · provisional')).toBeInTheDocument();expect(inspectNativeGraph).toHaveBeenCalledTimes(2);
});
