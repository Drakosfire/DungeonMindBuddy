import {webcrypto} from 'node:crypto'
import {beforeEach,afterEach,expect,it,vi} from 'vitest'
import {getWorkPlan,saveWorkPlan,continueWorkPlan,type WorkPlan} from './conversationWorkPlanApi'
import {authenticatedApiFetch} from './liveApi'
vi.mock('./liveApi',async original=>({...await original<typeof import('./liveApi')>(),authenticatedApiFetch:vi.fn()}))
const id='11111111-1111-4111-8111-111111111111',other='22222222-2222-4222-8222-222222222222',scope={worldId:'world/a',conversationId:id,turnId:other,source:'Reviewed source reply'}
let p:WorkPlan
beforeEach(async()=>{vi.clearAllMocks();vi.stubGlobal('crypto',webcrypto);const digest=await crypto.subtle.digest('SHA-256',new TextEncoder().encode(scope.source));p={schema:'dmb_reviewed_work_plan_v1',world_id:scope.worldId,conversation_id:id,source_turn_id:other,source_answer_sha256:Array.from(new Uint8Array(digest),b=>b.toString(16).padStart(2,'0')).join(''),document_id:'page',revision:1,steps:[{step_id:id,text:'Read related page',selected:true,kind:'discuss'}],dispatches:[],execution:[]}})
afterEach(()=>vi.unstubAllGlobals())
function response(body:unknown){vi.mocked(authenticatedApiFetch).mockResolvedValue({response:Response.json(body)} as Awaited<ReturnType<typeof authenticatedApiFetch>>)}
it('saves exact reviewed choices through the authenticated owner',async()=>{response(p);expect(await saveWorkPlan(scope,0,p.steps)).toEqual(p);expect(authenticatedApiFetch).toHaveBeenCalledWith(expect.stringContaining('/worlds/world%2Fa/conversations/'+id+'/work-plans/'+other),expect.objectContaining({method:'PUT',body:JSON.stringify({expected_revision:0,steps:p.steps})}))})
it.each(['world','source','hash'])('refuses a mismatched saved-plan %s',async kind=>{const changed={...p,...(kind==='world'?{world_id:'foreign'}:kind==='source'?{source_turn_id:id}:{source_answer_sha256:'b'.repeat(64)})};response({schema:'dmb_work_plan_response_v1',world_id:scope.worldId,conversation_id:id,source_turn_id:other,plan:changed});await expect(getWorkPlan(scope)).rejects.toThrow()})
it('requires the returned dispatch to be retained in this exact plan',async()=>{const dispatch={command_id:id,step_id:id,client_thread_id:id,client_turn_id:other,message:'Exact reviewed request'};response({plan:p,dispatch,reviewed_step:null});await expect(continueWorkPlan(scope,p,id,id)).rejects.toThrow('another step');const next={...p,revision:2,dispatches:[dispatch],execution:[{command_id:id,step_id:id,status:'awaiting_dispatch',turn_id:null,attempt:null,result:null}]};response({plan:next,dispatch,reviewed_step:{conversation_id:id,source_turn_id:other,command_id:id}});expect((await continueWorkPlan(scope,p,id,id)).dispatch).toEqual(dispatch)})

it('refuses a reference for a different command',async()=>{const dispatch={command_id:id,step_id:id,client_thread_id:id,client_turn_id:other,message:'Exact request'};const next={...p,dispatches:[dispatch],execution:[{command_id:id,step_id:id,status:'awaiting_dispatch',turn_id:null,attempt:null,result:null}]};response({plan:next,dispatch,reviewed_step:{conversation_id:id,source_turn_id:other,command_id:other}});await expect(continueWorkPlan(scope,p,id,id)).rejects.toThrow('reference')})

it('reads an exact page reference without embedding the assistant reply',async()=>{
 response({schema:'dmb_work_plan_response_v1',world_id:scope.worldId,conversation_id:id,source_turn_id:other,plan:p});
 await expect(getWorkPlan({worldId:scope.worldId,conversationId:id,turnId:other,documentId:'page',sourceSha256:p.source_answer_sha256})).resolves.toEqual(p);
});
it('refuses a plan reference copied onto another document',async()=>{
 response({schema:'dmb_work_plan_response_v1',world_id:scope.worldId,conversation_id:id,source_turn_id:other,plan:p});
 await expect(getWorkPlan({worldId:scope.worldId,conversationId:id,turnId:other,documentId:'foreign',sourceSha256:p.source_answer_sha256})).rejects.toThrow();
});
