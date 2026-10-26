import {webcrypto} from 'node:crypto'
import {beforeEach,afterEach,expect,it,vi} from 'vitest'
import {getWorkPlan,getWorkPlanRecord,saveWorkPlan,continueWorkPlan,type WorkPlan} from './conversationWorkPlanApi'
import {authenticatedApiFetch} from './liveApi'
vi.mock('./liveApi',async original=>({...await original<typeof import('./liveApi')>(),authenticatedApiFetch:vi.fn()}))
const id='11111111-1111-4111-8111-111111111111',other='22222222-2222-4222-8222-222222222222',scope={worldId:'world/a',conversationId:id,turnId:other,source:'Reviewed source reply'}
let p:WorkPlan
beforeEach(async()=>{vi.clearAllMocks();vi.stubGlobal('crypto',webcrypto);const digest=await crypto.subtle.digest('SHA-256',new TextEncoder().encode(scope.source));p={schema:'dmb_reviewed_work_plan_v2',objective:'Develop the shop.',world_id:scope.worldId,conversation_id:id,source_turn_id:other,source_answer_sha256:Array.from(new Uint8Array(digest),b=>b.toString(16).padStart(2,'0')).join(''),document_id:'page',revision:1,steps:[{step_id:id,text:'Read related page',selected:true,kind:'discuss'}],dispatches:[],execution:[]}})
afterEach(()=>vi.unstubAllGlobals())
function response(body:unknown){vi.mocked(authenticatedApiFetch).mockResolvedValue({response:Response.json(body)} as Awaited<ReturnType<typeof authenticatedApiFetch>>)}
it('saves exact reviewed choices through the authenticated owner',async()=>{response(p);expect(await saveWorkPlan(scope,0,p.steps,'Develop the shop.')).toEqual(p);expect(authenticatedApiFetch).toHaveBeenCalledWith(expect.stringContaining('/worlds/world%2Fa/conversations/'+id+'/work-plans/'+other),expect.objectContaining({method:'PUT',body:JSON.stringify({schema:'dmb_reviewed_work_plan_review_v2',expected_revision:0,steps:p.steps,objective:'Develop the shop.'})}))})
it.each(['world','source','hash'])('refuses a mismatched saved-plan %s',async kind=>{const changed={...p,...(kind==='world'?{world_id:'foreign'}:kind==='source'?{source_turn_id:id}:{source_answer_sha256:'b'.repeat(64)})};response({schema:'dmb_work_plan_response_v2',world_id:scope.worldId,conversation_id:id,source_turn_id:other,plan:changed});await expect(getWorkPlan(scope)).rejects.toThrow()})
it('requires the returned dispatch to be retained in this exact plan',async()=>{const dispatch={command_id:id,step_id:id,client_thread_id:id,client_turn_id:other,message:'Exact reviewed request'};response({plan:p,dispatch,reviewed_step:null});await expect(continueWorkPlan(scope,p,id,id)).rejects.toThrow('another step');const next={...p,revision:2,dispatches:[dispatch],execution:[{command_id:id,step_id:id,status:'awaiting_dispatch',turn_id:null,attempt:null,result:null}]};response({plan:next,dispatch,reviewed_step:{conversation_id:id,source_turn_id:other,command_id:id}});expect((await continueWorkPlan(scope,p,id,id)).dispatch).toEqual(dispatch)})

it('refuses a reference for a different command',async()=>{const dispatch={command_id:id,step_id:id,client_thread_id:id,client_turn_id:other,message:'Exact request'};const next={...p,dispatches:[dispatch],execution:[{command_id:id,step_id:id,status:'awaiting_dispatch',turn_id:null,attempt:null,result:null}]};response({plan:next,dispatch,reviewed_step:{conversation_id:id,source_turn_id:other,command_id:other}});await expect(continueWorkPlan(scope,p,id,id)).rejects.toThrow('reference')})

it('reads an exact page reference without embedding the assistant reply',async()=>{
 response({schema:'dmb_work_plan_response_v2',world_id:scope.worldId,conversation_id:id,source_turn_id:other,plan:p});
 await expect(getWorkPlan({worldId:scope.worldId,conversationId:id,turnId:other,documentId:'page',sourceSha256:p.source_answer_sha256})).resolves.toEqual(p);
});
it('refuses a plan reference copied onto another document',async()=>{
 response({schema:'dmb_work_plan_response_v2',world_id:scope.worldId,conversation_id:id,source_turn_id:other,plan:p});
 await expect(getWorkPlan({worldId:scope.worldId,conversationId:id,turnId:other,documentId:'foreign',sourceSha256:p.source_answer_sha256})).rejects.toThrow();
});

const graphRef={schema:'dmb_authored_graph_reference_v1' as const,managed_world_id:scope.worldId,native_world_id:'native',binding_version:1,graph_revision:'rev-a',node_id:'cedar-box',label:'Cedar box'};
function referencePlan():WorkPlan{return {...p,schema:'dmb_reviewed_work_plan_v3',objective:'Keep the wick dry.',root_references:[graphRef],steps:p.steps.map(s=>({...s,references:[]}))};}
it('retains captured source references even before the initial plan Save',async()=>{
 response({schema:'dmb_work_plan_response_v3',world_id:scope.worldId,conversation_id:id,source_turn_id:other,source_references:[graphRef],plan:null});
 expect(await getWorkPlanRecord(scope)).toEqual({plan:null,sourceReferences:[graphRef]});
});
it('serializes reference-aware review with explicit empty step references',async()=>{
 const plan=referencePlan();response(plan);await expect(saveWorkPlan(scope,1,p.steps,'Keep the wick dry.',[graphRef])).resolves.toEqual(plan);
 const init=vi.mocked(authenticatedApiFetch).mock.calls.at(-1)![1]!;
 expect(JSON.parse(String(init.body))).toEqual({schema:'dmb_reviewed_work_plan_review_v3',expected_revision:1,steps:plan.steps,objective:'Keep the wick dry.',root_references:[graphRef]});
});
it.each(['foreign','conflict','missing'])('refuses invalid %s references in retained plans',async kind=>{
 const plan=referencePlan();if(plan.schema!=='dmb_reviewed_work_plan_v3')throw new Error();
 if(kind==='foreign')plan.root_references=[{...graphRef,managed_world_id:'foreign'}];
 if(kind==='conflict')plan.steps[0].references=[{...graphRef,graph_revision:'other-revision'}];
 if(kind==='missing')delete plan.steps[0].references;
 response({schema:'dmb_work_plan_response_v3',world_id:scope.worldId,conversation_id:id,source_turn_id:other,source_references:[graphRef],plan});await expect(getWorkPlan(scope)).rejects.toThrow();
});
it('preserves a frozen dispatch even after future root references change',async()=>{
 const plan=referencePlan();if(plan.schema!=='dmb_reviewed_work_plan_v3')throw new Error();
 plan.root_references=[];
 const dispatch={schema:'dmb_work_plan_dispatch_v2' as const,authored_references:{schema:'dmb_authored_graph_references_v1' as const,references:[graphRef]},command_id:id,step_id:id,client_thread_id:id,client_turn_id:other,message:'Exact request'};
 plan.dispatches=[dispatch];plan.execution=[{command_id:id,step_id:id,status:'awaiting_dispatch',turn_id:null,attempt:null,result:null}];
 response({plan,dispatch,reviewed_step:{conversation_id:id,source_turn_id:other,command_id:id}});
 expect((await continueWorkPlan(scope,plan,id,id)).dispatch.authored_references?.references).toEqual([graphRef]);
});
it('requires the dispatch bytes to match its retained plan',async()=>{
 const plan=referencePlan();const dispatch={schema:'dmb_work_plan_dispatch_v2' as const,authored_references:{schema:'dmb_authored_graph_references_v1' as const,references:[graphRef]},command_id:id,step_id:id,client_thread_id:id,client_turn_id:other,message:'Exact request'};
 plan.dispatches=[dispatch];plan.execution=[{command_id:id,step_id:id,status:'awaiting_dispatch',turn_id:null,attempt:null,result:null}];
 response({plan,dispatch:{...dispatch,authored_references:{...dispatch.authored_references,references:[]}},reviewed_step:null});
 await expect(continueWorkPlan(scope,plan,id,id)).rejects.toThrow('another step');
});

function scopedDispatch(){return {schema:'dmb_work_plan_dispatch_v3' as const,authored_references:null,command_id:id,step_id:id,client_thread_id:id,client_turn_id:other,message:'Discuss only this selected reviewed step:\n\nRead related page',scope:{schema:'dmb_reviewed_discussion_scope_v1' as const,task:{step_id:id,kind:'discuss' as const,text:'Read related page'},objective_context:'The original outcome.',sibling_context:[{step_id:other,text:'Write a later sentence.',kind:'prepare_insertion' as const,selected:false,status:'deferred',earlier_reply:null}]}};}
function withScopedDispatch(){const dispatch=scopedDispatch();p.dispatches=[dispatch];p.execution=[{command_id:id,step_id:id,status:'awaiting_dispatch',turn_id:null,attempt:null,result:null}];return dispatch;}
it('reads an immutable Discuss scope after the current objective changes',async()=>{
 const dispatch=withScopedDispatch();p={...p,schema:'dmb_reviewed_work_plan_v2',objective:'The newer plan outcome.'};
 response({plan:p,dispatch,reviewed_step:{conversation_id:id,source_turn_id:other,command_id:id}});
 expect((await continueWorkPlan(scope,p,id,id)).dispatch.scope?.objective_context).toBe('The original outcome.');
});
it('retains a plain scoped dispatch when the plan later gains Graph context',async()=>{
 const dispatch=withScopedDispatch();p=referencePlan();p.dispatches=[dispatch];
 response({schema:'dmb_work_plan_response_v3',world_id:scope.worldId,conversation_id:id,source_turn_id:other,source_references:[graphRef],plan:p});
 expect((await getWorkPlan(scope))?.dispatches[0].authored_references).toBeNull();
});
it.each(['missing','task','self sibling','duplicate sibling'])('refuses invalid scoped continuation: %s',async mutation=>{
 const dispatch=withScopedDispatch();const corrupted=JSON.parse(JSON.stringify(dispatch));
 if(mutation==='missing')delete corrupted.scope;
 else if(mutation==='task')corrupted.scope.task.text='Write the deferred sentence.';
 else if(mutation==='self sibling')corrupted.scope.sibling_context[0].step_id=id;
 else corrupted.scope.sibling_context.push(corrupted.scope.sibling_context[0]);
 p.dispatches=[corrupted];response({plan:p,dispatch:corrupted,reviewed_step:null});
 await expect(continueWorkPlan(scope,p,id,id)).rejects.toThrow();
});
