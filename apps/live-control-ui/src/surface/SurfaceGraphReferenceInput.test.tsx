import {act,cleanup,fireEvent,render,screen,within} from '@testing-library/react';
import {afterEach,beforeEach,expect,it,vi} from 'vitest';
import type {AuthoredGraphReferenceV1} from '../api/types';
import type {NativeGraphCatalog} from '../api/nativeGraphInspection';
import {getNativeGraphCatalog,inspectNativeGraph} from '../api/liveApi';
import {SurfaceGraphReferenceInput} from './SurfaceGraphReferenceInput';
vi.mock('../api/liveApi',()=>({getNativeGraphCatalog:vi.fn(),inspectNativeGraph:vi.fn()}));
const pin={managed_world_id:'quarry',native_world_id:'native',binding_version:3,revision_id:'rev-a',scope_mode:'world' as const,campaign_id:null};
const ids=['first-box','second-box','fellinor'];
const catalog:NativeGraphCatalog={schema:'dmb_native_graph_catalog_v1',scope:pin,catalogue:{identity:{space_id:'native',revision_id:'rev-a'},entities:ids.map(entity_id=>({entity_id})),admitted_assertion_ids:ids,completeness:{status:'complete',reason:null},request_sha256:'hash',result_digest:'digest'},assertions:ids.map((id,i)=>({assertion_id:id,subject_entity_id:id,predicate:'dnd5e:name',value:{kind:'literal',value:i===2?'Fellinor':'Cedar box'},metadata:{scope:[],visibility:{kind:'public'},epistemic_basis:'direct',claim_mode:'fact',standing:'admitted',evidence_ref_ids:[],temporal_scope:null,domain_metadata:[]}}))};
const reference:AuthoredGraphReferenceV1={schema:'dmb_authored_graph_reference_v1',managed_world_id:'quarry',native_world_id:'native',binding_version:3,graph_revision:'rev-a',node_id:'first-box',label:'Cedar box'};
beforeEach(()=>{vi.resetAllMocks();vi.mocked(getNativeGraphCatalog).mockResolvedValue(catalog);vi.mocked(inspectNativeGraph).mockResolvedValue({schema:'dmb_native_graph_entity_v1',scope:pin,entity:{found:true,assertions:[],evidence:[],completeness:{status:'complete',reason:null}}});});
afterEach(cleanup);
async function open(){fireEvent.click(screen.getByRole('button',{name:'@ Reference'}));return screen.findByRole('searchbox',{name:'Find an object'});}
it('finds Fellinor without a projection provider and selects the exact native revision without reading',async()=>{
 const change=vi.fn();render(<SurfaceGraphReferenceInput worldId="quarry" value={[]} onChange={change}/>);
 expect(getNativeGraphCatalog).not.toHaveBeenCalled();fireEvent.change(await open(),{target:{value:'FELLINOR'}});
 fireEvent.click(screen.getByRole('button',{name:'Use Fellinor as context'}));
 expect(change).toHaveBeenCalledWith([{...reference,node_id:'fellinor',label:'Fellinor'}]);expect(inspectNativeGraph).not.toHaveBeenCalled();expect(screen.queryByRole('searchbox')).toBeNull();
 expect(getNativeGraphCatalog).toHaveBeenCalledWith({managed_world_id:'quarry',scope_mode:'world',campaign_id:null},expect.any(AbortSignal));
});
it('keeps duplicate names distinct and inspection separate from selection',async()=>{
 const change=vi.fn();render(<SurfaceGraphReferenceInput worldId="quarry" value={[]} onChange={change}/>);await open();
 fireEvent.click(screen.getByRole('button',{name:'Cedar box second-box',exact:true}));await screen.findByRole('heading',{name:'Cedar box'});
 expect(inspectNativeGraph).toHaveBeenCalledWith(pin,{kind:'entity',entity_id:'second-box'},expect.any(AbortSignal));expect(change).not.toHaveBeenCalled();
 fireEvent.click(screen.getAllByRole('button',{name:'Use Cedar box as context'})[1]);expect(change).toHaveBeenCalledWith([{...reference,node_id:'second-box'}]);
});
it.each(['world','pin'] as const)('rejects a foreign %s catalogue and retains chips',async(kind)=>{
 vi.mocked(getNativeGraphCatalog).mockResolvedValue({...catalog,...(kind==='world'?{scope:{...pin,managed_world_id:'foreign'}}:{catalogue:{...catalog.catalogue,identity:{space_id:'native',revision_id:'other'}}})});
 const change=vi.fn();render(<SurfaceGraphReferenceInput worldId="quarry" value={[reference]} onChange={change}/>);fireEvent.click(screen.getByRole('button',{name:'@ Reference'}));
 expect(await screen.findByRole('alert')).toHaveTextContent('World changed');expect(screen.queryByRole('button',{name:/Use .* as context/})).toBeNull();expect(screen.getByText('@Cedar box')).toBeVisible();
 fireEvent.click(screen.getByRole('button',{name:'Remove reference Cedar box'}));expect(change).toHaveBeenCalledWith([]);
});
it('distinguishes failure from empty and recovers through refresh',async()=>{
 vi.mocked(getNativeGraphCatalog).mockRejectedValueOnce(new Error('Authority unavailable'));render(<SurfaceGraphReferenceInput worldId="quarry" value={[reference]} onChange={vi.fn()}/>);fireEvent.click(screen.getByRole('button',{name:'@ Reference'}));
 expect(await screen.findByRole('alert')).toHaveTextContent('Authority unavailable');expect(screen.queryByText('No reviewed objects are available in this view.')).toBeNull();expect(screen.getByText('@Cedar box')).toBeVisible();
 fireEvent.click(screen.getByRole('button',{name:'Refresh reviewed Graph'}));await screen.findByRole('button',{name:'Use Fellinor as context'});
});
it('isolates simultaneous searches',async()=>{
 render(<><SurfaceGraphReferenceInput worldId="quarry" label="First context" value={[]} onChange={()=>{}}/><SurfaceGraphReferenceInput worldId="quarry" label="Second context" value={[]} onChange={()=>{}}/></>);
 for(const button of screen.getAllByRole('button',{name:'@ Reference'}))fireEvent.click(button);
 const inputs=await screen.findAllByRole('searchbox',{name:'Find an object'});expect(inputs[0].id).not.toBe(inputs[1].id);
 fireEvent.change(inputs[1],{target:{value:'Fellinor'}});expect(inputs[0]).toHaveValue('');expect(inputs[1]).toHaveValue('Fellinor');
});
it('disables selection while busy without losing the catalogue',async()=>{
 const change=vi.fn(),view=render(<SurfaceGraphReferenceInput worldId="quarry" value={[]} onChange={change}/>);await open();view.rerender(<SurfaceGraphReferenceInput worldId="quarry" value={[]} onChange={change} disabled/>);
 const button=screen.getByRole('button',{name:'Use Fellinor as context'});expect(button).toBeDisabled();fireEvent.click(button);expect(change).not.toHaveBeenCalled();
});
it('discards an old World response before selecting in the new World',async()=>{
 let finish!:(value:NativeGraphCatalog)=>void;vi.mocked(getNativeGraphCatalog).mockImplementationOnce(()=>new Promise(resolve=>{finish=resolve}));
 const change=vi.fn(),view=render(<SurfaceGraphReferenceInput worldId="quarry" value={[reference]} onChange={change}/>);fireEvent.click(screen.getByRole('button',{name:'@ Reference'}));
 vi.mocked(getNativeGraphCatalog).mockResolvedValue({...catalog,scope:{...pin,managed_world_id:'next'}});view.rerender(<SurfaceGraphReferenceInput worldId="next" value={[]} onChange={change}/>);
 await screen.findByRole('button',{name:'Use Fellinor as context'});await act(async()=>finish(catalog));fireEvent.click(screen.getByRole('button',{name:'Use Fellinor as context'}));
 expect(change).toHaveBeenCalledWith([{...reference,managed_world_id:'next',node_id:'fellinor',label:'Fellinor'}]);
});
it('shows historical selections without requesting fresh bytes or edits',()=>{
 render(<SurfaceGraphReferenceInput worldId="quarry" value={[reference]} onChange={vi.fn()} readOnly/>);expect(screen.getByText('@Cedar box')).toBeVisible();expect(screen.queryByRole('button')).toBeNull();expect(getNativeGraphCatalog).not.toHaveBeenCalled();
});
it('keeps all returned objects reachable beyond the old forty-result ceiling and reports partial coverage',async()=>{
 const entities=Array.from({length:51},(_,i)=>({entity_id:`entity-${i}`}));vi.mocked(getNativeGraphCatalog).mockResolvedValue({...catalog,catalogue:{...catalog.catalogue,entities,completeness:{status:'partial',reason:'Some records unavailable'}},assertions:[]});
 render(<SurfaceGraphReferenceInput worldId="quarry" value={[]} onChange={vi.fn()}/>);await open();await screen.findByText(/51 objects.*Partial view/);
 expect(within(screen.getByRole('navigation',{name:'Reviewed Graph objects'})).getAllByRole('button',{name:/Use .* as context/})).toHaveLength(51);expect(screen.getByRole('button',{name:'Use entity-50 as context'})).toBeVisible();
});
