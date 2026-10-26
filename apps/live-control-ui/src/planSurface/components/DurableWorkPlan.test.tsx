import {cleanup,fireEvent,render,screen,waitFor} from '@testing-library/react'
import {webcrypto} from 'node:crypto'
import {afterEach,beforeEach,expect,it,vi} from 'vitest'
import {DurableWorkPlan} from './DurableWorkPlan'
import {getWorkPlan,saveWorkPlan,continueWorkPlan,planObjective,type WorkPlan} from '../../api/conversationWorkPlanApi'
vi.mock('../../api/conversationWorkPlanApi',async original=>({...await original<typeof import('../../api/conversationWorkPlanApi')>(),getWorkPlan:vi.fn(),saveWorkPlan:vi.fn(),continueWorkPlan:vi.fn()}))
vi.mock('../../surface/SurfaceGraphReferenceInput',()=>({SurfaceGraphReferenceInput:({worldId,label,value,onChange,disabled}:any)=><section aria-label={label}><span>{value.map((r:any)=>r.node_id).join(',')}</span><button type="button" disabled={disabled} onClick={()=>onChange([...value,{schema:'dmb_authored_graph_reference_v1',managed_world_id:worldId,native_world_id:'native',binding_version:1,graph_revision:'rev-a',node_id:label,label}])}>Select {label}</button></section>}));
const scope={worldId:'world',conversationId:'conversation',turnId:'source-turn',source:'1. Discuss the shop.\n2. Prepare content.'}
const one='11111111-1111-4111-8111-111111111111',two='22222222-2222-4222-8222-222222222222'
function plan():WorkPlan{return {schema:'dmb_reviewed_work_plan_v2',objective:'Develop a useful shop scene.',world_id:'world',conversation_id:'conversation',source_turn_id:'source-turn',source_answer_sha256:'a'.repeat(64),document_id:'source',revision:1,steps:[{step_id:one,text:'Discuss the shop.',selected:true,kind:'discuss'},{step_id:two,text:'Prepare content.',selected:false,kind:'prepare_insertion'}],dispatches:[],execution:[]}}
function mount(extra={}){const onContinue=vi.fn();render(<DurableWorkPlan scope={scope} disabled={false} onContinue={onContinue} renderDraft={(save,busy)=><button disabled={busy} onClick={()=>void save([{text:'My edited step',include:true,kind:'prepare_insertion'}])}>Save draft review</button>} {...extra}/>);return onContinue}
beforeEach(()=>{vi.clearAllMocks();sessionStorage.clear();vi.stubGlobal('crypto',webcrypto);vi.mocked(getWorkPlan).mockResolvedValue(plan())})
afterEach(()=>{cleanup();vi.unstubAllGlobals()})
it('saves a reviewed draft without executing and restores the durable result',async()=>{vi.mocked(getWorkPlan).mockResolvedValue(null);vi.mocked(saveWorkPlan).mockResolvedValue(plan());const proceed=mount();fireEvent.change(await screen.findByLabelText('Expected outcome'),{target:{value:'Develop a useful shop scene.'}});fireEvent.click(await screen.findByRole('button',{name:'Save draft review'}));await screen.findByLabelText('Saved step 1');expect(saveWorkPlan).toHaveBeenCalledWith(scope,0,[expect.objectContaining({text:'My edited step',selected:true,kind:'prepare_insertion'})],'Develop a useful shop scene.');expect(proceed).not.toHaveBeenCalled();expect(continueWorkPlan).not.toHaveBeenCalled()})
it('retains unsaved edits over remount and requires reconciliation of a newer server review',async()=>{mount();fireEvent.change(await screen.findByLabelText('Saved step 1'),{target:{value:'My unsaved newer wording'}});cleanup();const newer={...plan(),revision:2};vi.mocked(getWorkPlan).mockResolvedValue(newer);mount();expect(await screen.findByLabelText('Saved step 1')).toHaveValue('My unsaved newer wording');expect(screen.getByRole('button',{name:'Save reviewed plan'})).toBeDisabled();fireEvent.click(screen.getByRole('button',{name:'Use these edits against the latest review'}));expect(screen.getByRole('button',{name:'Save reviewed plan'})).toBeEnabled()})
it('continues only on explicit click and preserves the exact reserved dispatch',async()=>{const p=plan(),dispatch={command_id:one,step_id:one,client_thread_id:two,client_turn_id:one,message:'Exact reviewed continuation'};vi.mocked(continueWorkPlan).mockResolvedValue({plan:{...p,revision:2,dispatches:[dispatch],execution:[{command_id:one,step_id:one,status:'awaiting_dispatch',turn_id:null,attempt:null,result:null}]},dispatch,reference:null});const proceed=mount();await screen.findByLabelText('Saved step 1');expect(continueWorkPlan).not.toHaveBeenCalled();fireEvent.click(screen.getAllByRole('button',{name:'Continue step'})[0]);await waitFor(()=>expect(proceed).toHaveBeenCalledWith(expect.objectContaining({revision:2}),dispatch,null));expect(screen.getByLabelText('Saved step 1')).toBeDisabled()})
it('shows a prepared insertion as prepared, never saved or completed',async()=>{const p=plan(),dispatch={command_id:one,step_id:one,client_thread_id:two,client_turn_id:one,message:'Exact'};vi.mocked(getWorkPlan).mockResolvedValue({...p,dispatches:[dispatch],execution:[{command_id:one,step_id:one,status:'prepared',turn_id:two,attempt:1,result:{kind:'page_proposal',action_id:one}}]});mount();await screen.findByText('Suggestion prepared · review and Save on the page');expect(screen.queryByText('Reply received')).not.toBeInTheDocument();expect(screen.getAllByRole('button',{name:'Continue step'})[0]).toBeDisabled()})
it('preserves unreadable local copies and blocks saving over them',async()=>{const identity=JSON.stringify([scope.worldId,scope.conversationId,scope.turnId,scope.source]);sessionStorage.setItem(`dmb:reviewed-plan-edit:v1:${identity}`,'unreadable retained bytes');mount();fireEvent.change(await screen.findByLabelText('Saved step 1'),{target:{value:'Another wording'}});expect(screen.getByRole('button',{name:'Save reviewed plan'})).toBeDisabled();expect(sessionStorage.getItem(`dmb:reviewed-plan-edit:v1:${identity}`)).toBe('unreadable retained bytes')})

it('retires a late continuation after unmount and leaves the reservation for explicit resume',async()=>{let resolve!:(value:Awaited<ReturnType<typeof continueWorkPlan>>)=>void;vi.mocked(continueWorkPlan).mockReturnValue(new Promise(r=>{resolve=r}));const proceed=mount();await screen.findByLabelText('Saved step 1');fireEvent.click(screen.getAllByRole('button',{name:'Continue step'})[0]);await waitFor(()=>expect(continueWorkPlan).toHaveBeenCalledTimes(1));cleanup();const dispatch={command_id:one,step_id:one,client_thread_id:two,client_turn_id:one,message:'Reserved but not sent'};resolve({plan:{...plan(),revision:2,dispatches:[dispatch],execution:[{command_id:one,step_id:one,status:'awaiting_dispatch',turn_id:null,attempt:null,result:null}]},dispatch,reference:null});await new Promise(r=>setTimeout(r,0));expect(proceed).not.toHaveBeenCalled()});

it('retires a delayed continuation when the same reference leaves and returns to an enabled context',async()=>{
 let resolve!:(value:Awaited<ReturnType<typeof continueWorkPlan>>)=>void;
 vi.mocked(continueWorkPlan).mockReturnValue(new Promise(r=>{resolve=r}));
 const proceed=vi.fn(),draft=()=>null;
 const mounted=render(<DurableWorkPlan scope={scope} disabled={false} onContinue={proceed} renderDraft={draft}/>);
 fireEvent.click((await screen.findAllByRole('button',{name:'Continue step'}))[0]);
 await waitFor(()=>expect(continueWorkPlan).toHaveBeenCalledTimes(1));
 mounted.rerender(<DurableWorkPlan scope={scope} disabled onContinue={proceed} renderDraft={draft}/>);
 mounted.rerender(<DurableWorkPlan scope={scope} disabled={false} onContinue={proceed} renderDraft={draft}/>);
 const dispatch={command_id:one,step_id:one,client_thread_id:two,client_turn_id:one,message:'Reserved but retired'};
 resolve({plan:{...plan(),revision:2,dispatches:[dispatch],execution:[{command_id:one,step_id:one,status:'awaiting_dispatch',turn_id:null,attempt:null,result:null}]},dispatch,reference:null});
 await screen.findByText(/reserved step was retained/);expect(proceed).not.toHaveBeenCalled();
});
it('checks host admission before reserving any continuation and rechecks after the RPC',async()=>{
 const begin=vi.fn(()=>{throw new Error('Page is dirty.');});mount({beginContinuation:begin});
 fireEvent.click((await screen.findAllByRole('button',{name:'Continue step'}))[0]);await screen.findByText('Page is dirty.');
 expect(begin).toHaveBeenCalledTimes(1);expect(continueWorkPlan).not.toHaveBeenCalled();
});

it('saves an outcome-only edit with the unchanged rows and restores it after remount',async()=>{
 const p=plan();mount();const field=await screen.findByLabelText('Expected outcome');
 fireEvent.change(field,{target:{value:'Create a memorable proposed shop scene.'}});cleanup();mount();
 expect(await screen.findByLabelText('Expected outcome')).toHaveValue('Create a memorable proposed shop scene.');
 vi.mocked(saveWorkPlan).mockResolvedValue({...p,schema:'dmb_reviewed_work_plan_v2',objective:'Create a memorable proposed shop scene.',revision:2});
 fireEvent.click(screen.getByRole('button',{name:'Save reviewed plan'}));
 await waitFor(()=>expect(saveWorkPlan).toHaveBeenCalledWith(scope,1,p.steps,'Create a memorable proposed shop scene.'));
 expect(continueWorkPlan).not.toHaveBeenCalled();
});
it('shows an absent historical outcome truthfully and requires explicit author Save before new continuation',async()=>{
 const p=plan();const {objective:_outcome,...legacy}=p as Extract<WorkPlan,{schema:'dmb_reviewed_work_plan_v2'}>;
 vi.mocked(getWorkPlan).mockResolvedValue({...legacy,schema:'dmb_reviewed_work_plan_v1'});mount();
 expect(await screen.findByLabelText('Expected outcome')).toHaveValue('');
 expect(screen.getAllByRole('button',{name:'Continue step'})[0]).toBeDisabled();expect(saveWorkPlan).not.toHaveBeenCalled();
 fireEvent.change(screen.getByLabelText('Expected outcome'),{target:{value:'The author supplied this outcome.'}});
 vi.mocked(saveWorkPlan).mockResolvedValue({...p,schema:'dmb_reviewed_work_plan_v2',objective:'The author supplied this outcome.',revision:2});
 fireEvent.click(screen.getByRole('button',{name:'Save reviewed plan'}));
 await waitFor(()=>expect(saveWorkPlan).toHaveBeenCalledWith(scope,1,p.steps,'The author supplied this outcome.'));
 expect(continueWorkPlan).not.toHaveBeenCalled();
});

it('collapses completed steps and replaces dispatched selection controls with status',async()=>{
 const p=plan(),dispatch={command_id:one,step_id:one,client_thread_id:two,client_turn_id:one,message:'Exact'};
 vi.mocked(getWorkPlan).mockResolvedValue({...p,dispatches:[dispatch],execution:[{command_id:one,step_id:one,status:'completed',turn_id:two,attempt:1,result:{kind:'reply',text:'The completed reply.'}}]});
 const {container}=render(<DurableWorkPlan scope={scope} disabled={false} onContinue={vi.fn()} renderDraft={()=>null}/>);
 const summary=await screen.findByText('1. Discuss the shop.');
 expect(container.querySelector('details')?.open).toBe(false);
 expect(screen.queryByRole('checkbox',{name:'Include step 1'})).toBeNull();
 expect(screen.getByRole('checkbox',{name:'Include step 2'})).toBeEnabled();
 fireEvent.click(summary); // native disclosure remains operable; no continuation is dispatched.
 expect(continueWorkPlan).not.toHaveBeenCalled();
});

it('removes an unexecuted row locally, restores it after remount and saves exact remaining IDs',async()=>{
 const p=plan();mount();
 fireEvent.click(await screen.findByRole('button',{name:'Remove step 1'}));
 expect(screen.getByLabelText('Saved step 1')).toHaveValue('Prepare content.');
 expect(saveWorkPlan).not.toHaveBeenCalled();expect(continueWorkPlan).not.toHaveBeenCalled();
 cleanup();mount();
 expect(await screen.findByLabelText('Saved step 1')).toHaveValue('Prepare content.');
 expect(screen.getByRole('button',{name:'Remove step 1'})).toBeDisabled();
 vi.mocked(saveWorkPlan).mockResolvedValue({...p,revision:2,steps:[p.steps[1]]});
 fireEvent.click(screen.getByRole('button',{name:'Save reviewed plan'}));
 await waitFor(()=>expect(saveWorkPlan).toHaveBeenCalledWith(scope,1,[p.steps[1]],'Develop a useful shop scene.'));
 expect(continueWorkPlan).not.toHaveBeenCalled();
});
it('offers no removal for a dispatched row while a pending row remains removable',async()=>{
 const p=plan();vi.mocked(getWorkPlan).mockResolvedValue({...p,dispatches:[{command_id:one,step_id:one,client_thread_id:two,client_turn_id:one,message:'Retained'}],execution:[]});
 mount();await screen.findByLabelText('Saved step 1');
 expect(screen.queryByRole('button',{name:'Remove step 1'})).toBeNull();
 expect(screen.getByRole('button',{name:'Remove step 2'})).toBeEnabled();
 fireEvent.click(screen.getByRole('button',{name:'Remove step 2'}));
 expect(screen.getByLabelText('Saved step 1')).toHaveValue('Discuss the shop.');
 expect(screen.queryByLabelText('Saved step 2')).toBeNull();expect(continueWorkPlan).not.toHaveBeenCalled();
});

it('retains root and deferred-step context through remount and explicit reference-aware Save',async()=>{
 const proceed=mount();await screen.findByLabelText('Saved step 1');
 fireEvent.click(screen.getByRole('button',{name:'Select Plan Graph context'}));
 fireEvent.click(screen.getByRole('button',{name:'Select Step 2 Graph context'}));
 expect(screen.getAllByRole('button',{name:'Continue step'})[0]).toBeDisabled();
 expect(saveWorkPlan).not.toHaveBeenCalled();cleanup();mount();await screen.findByLabelText('Saved step 1');
 expect(screen.getByLabelText('Plan Graph context')).toHaveTextContent('Plan Graph context');
 expect(screen.getByLabelText('Step 2 Graph context')).toHaveTextContent('Step 2 Graph context');
 const ref=(node:string)=>({schema:'dmb_authored_graph_reference_v1' as const,managed_world_id:'world',native_world_id:'native',binding_version:1,graph_revision:'rev-a',node_id:node,label:node});
 const roots=[ref('Plan Graph context')],steps=plan().steps.map((row,i)=>({...row,references:i===1?[ref('Step 2 Graph context')]:[]}));
 vi.mocked(saveWorkPlan).mockResolvedValue({...plan(),schema:'dmb_reviewed_work_plan_v3',objective:planObjective(plan()),root_references:roots,steps,revision:2});
 fireEvent.click(screen.getByRole('button',{name:'Save reviewed plan'}));
 await waitFor(()=>expect(saveWorkPlan).toHaveBeenCalledWith(scope,1,steps,planObjective(plan()),roots));
 expect(continueWorkPlan).not.toHaveBeenCalled();expect(proceed).not.toHaveBeenCalled();
});
it('keeps dispatched step context read-only while later root context remains editable',async()=>{
 const p=plan(),d={command_id:one,step_id:one,client_thread_id:two,client_turn_id:one,message:'Exact'};
 vi.mocked(getWorkPlan).mockResolvedValue({...p,schema:'dmb_reviewed_work_plan_v3',objective:planObjective(p),root_references:[],steps:p.steps.map(row=>({...row,references:[]})),dispatches:[d],execution:[{command_id:one,step_id:one,status:'prepared',turn_id:two,attempt:1,result:{kind:'page_proposal',action_id:one}}]});
 mount();await screen.findByLabelText('Saved step 1');
 expect(screen.getByRole('button',{name:'Select Step 1 Graph context'})).toBeDisabled();
 expect(screen.getByRole('button',{name:'Select Step 2 Graph context'})).toBeEnabled();
 expect(screen.getByRole('button',{name:'Select Plan Graph context'})).toBeEnabled();
});

it('preserves saved step references when reconciling an older V2 local wording draft',async()=>{
 const identity=JSON.stringify([scope.worldId,scope.conversationId,scope.turnId,scope.source]);
 const local=plan().steps.map(row=>({...row,text:row.step_id===one?'Older local wording':row.text}));
 sessionStorage.setItem(`dmb:reviewed-plan-edit:v1:${identity}`,JSON.stringify({schema:'dmb_reviewed_plan_edit_v2',identity,base_revision:1,steps:local,objective:planObjective(plan())}));
 const ref=(node:string)=>({schema:'dmb_authored_graph_reference_v1' as const,managed_world_id:'world',native_world_id:'native',binding_version:1,graph_revision:'rev-a',node_id:node,label:node});
 const roots=[ref('root box')],savedSteps=plan().steps.map((row,i)=>({...row,references:i===0?[ref('step box')]:[]}));
 const saved:WorkPlan={...plan(),schema:'dmb_reviewed_work_plan_v3',objective:planObjective(plan()),revision:2,root_references:roots,steps:savedSteps};
 vi.mocked(getWorkPlan).mockResolvedValue(saved);mount();
 expect(await screen.findByLabelText('Saved step 1')).toHaveValue('Older local wording');
 expect(screen.getByLabelText('Plan Graph context')).toHaveTextContent('root box');
 expect(screen.getByLabelText('Step 1 Graph context')).toHaveTextContent('step box');
 expect(screen.getByRole('button',{name:'Save reviewed plan'})).toBeDisabled();
 fireEvent.click(screen.getByRole('button',{name:'Use these edits against the latest review'}));
 const merged=savedSteps.map(row=>({...row,text:row.step_id===one?'Older local wording':row.text}));
 vi.mocked(saveWorkPlan).mockResolvedValue({...saved,revision:3,steps:merged});
 fireEvent.click(screen.getByRole('button',{name:'Save reviewed plan'}));
 await waitFor(()=>expect(saveWorkPlan).toHaveBeenCalledWith(scope,2,merged,planObjective(plan()),roots));
});
