import {cleanup,fireEvent,render,screen,within} from '@testing-library/react';
import {afterEach,beforeAll,beforeEach,expect,it,vi} from 'vitest';
import {SurfaceGraphReferenceInput} from '../surface/SurfaceGraphReferenceInput';
import {inspectNativeGraph,listWorldMechanicsAssociations} from '../api/liveApi';
import type {AuthoredGraphReferenceV1} from '../api/types';
vi.mock('../api/liveApi',()=>({inspectNativeGraph:vi.fn(),listWorldMechanicsAssociations:vi.fn()}));
const ref:AuthoredGraphReferenceV1={schema:'dmb_authored_graph_reference_v1',managed_world_id:'world',native_world_id:'native',binding_version:2,graph_revision:'captured',node_id:'ooze',label:'Ooze'};
const pin={managed_world_id:'world',native_world_id:'native',binding_version:2,revision_id:'captured',scope_mode:'world' as const,campaign_id:null};
beforeAll(()=>{
 Object.defineProperty(HTMLDialogElement.prototype,'showModal',{configurable:true,value:function(this:HTMLDialogElement){this.setAttribute('open','');}});
 Object.defineProperty(HTMLDialogElement.prototype,'close',{configurable:true,value:function(this:HTMLDialogElement){this.removeAttribute('open');}});
});
afterEach(cleanup);beforeEach(()=>{vi.resetAllMocks();vi.mocked(listWorldMechanicsAssociations).mockResolvedValue([]);vi.mocked(inspectNativeGraph).mockResolvedValue({schema:'dmb_native_graph_entity_v1',scope:pin,entity:{found:true,assertions:[],evidence:[],completeness:{status:'complete',reason:null}}});});
it.each([false,true])('inspects selected surface/composer references without editing or submitting (readOnly=%s)',async readOnly=>{
 const change=vi.fn();render(<SurfaceGraphReferenceInput worldId="world" value={[ref]} onChange={change} readOnly={readOnly}/>);
 expect(inspectNativeGraph).not.toHaveBeenCalled();fireEvent.click(screen.getByRole('button',{name:'Inspect Ooze'}));
 const dialog=screen.getByRole('dialog',{name:'Object · Ooze'});await within(dialog).findByText('No statblock linked in this view.');expect(inspectNativeGraph).toHaveBeenCalledWith(pin,{kind:'entity',entity_id:'ooze'},expect.any(AbortSignal));expect(change).not.toHaveBeenCalled();
 fireEvent.click(within(dialog).getByRole('button',{name:'Close object preview'}));expect(screen.queryByRole('dialog')).toBeNull();expect(screen.getByRole('button',{name:'Inspect Ooze'})).toBeVisible();
});
it('fails closed on a changed inspection pin and retries without changing the reference',async()=>{
 vi.mocked(inspectNativeGraph).mockResolvedValueOnce({schema:'dmb_native_graph_entity_v1',scope:{...pin,revision_id:'latest'},entity:{found:true,assertions:[],evidence:[],completeness:{status:'complete',reason:null}}});
 render(<SurfaceGraphReferenceInput worldId="world" value={[ref]} onChange={vi.fn()} readOnly/>);fireEvent.click(screen.getByRole('button',{name:'Inspect Ooze'}));expect(await screen.findByRole('alert')).toHaveTextContent('did not match');expect(listWorldMechanicsAssociations).not.toHaveBeenCalled();fireEvent.click(screen.getByRole('button',{name:'Retry object preview'}));await screen.findByText('No statblock linked in this view.');
});

it('retains the popup across equivalent reference hydration, and closes it on selection removal',async()=>{
 const view=render(<SurfaceGraphReferenceInput worldId="world" value={[ref]} onChange={vi.fn()} readOnly/>);fireEvent.click(screen.getByRole('button',{name:'Inspect Ooze'}));await screen.findByText('No statblock linked in this view.');
 view.rerender(<SurfaceGraphReferenceInput worldId="world" value={[{...ref}]} onChange={vi.fn()} readOnly/>);expect(screen.getByRole('dialog',{name:'Object · Ooze'})).toBeVisible();expect(inspectNativeGraph).toHaveBeenCalledTimes(1);
 view.rerender(<SurfaceGraphReferenceInput worldId="world" value={[]} onChange={vi.fn()} readOnly/>);expect(screen.queryByRole('dialog')).toBeNull();
 view.rerender(<SurfaceGraphReferenceInput worldId="world" value={[ref]} onChange={vi.fn()} readOnly/>);expect(screen.queryByRole('dialog')).toBeNull();
});

it('uses the selected object label for its own records without a whole catalogue read',async()=>{
 vi.mocked(inspectNativeGraph).mockResolvedValueOnce({schema:'dmb_native_graph_entity_v1',scope:pin,entity:{found:true,assertions:[{assertion_id:'name',subject_entity_id:'ooze',predicate:'dnd5e:name',value:{kind:'literal',value:'Ooze'},metadata:{scope:[],visibility:{kind:'public'},epistemic_basis:'asserted',claim_mode:'fact',standing:'provisional',evidence_ref_ids:[],temporal_scope:null,domain_metadata:[]}}],evidence:[],completeness:{status:'complete',reason:null}}});
 render(<SurfaceGraphReferenceInput worldId="world" value={[ref]} onChange={vi.fn()} readOnly/>);fireEvent.click(screen.getByRole('button',{name:'Inspect Ooze'}));expect(await screen.findByText('Ooze · name: Ooze')).toBeInTheDocument();
});
