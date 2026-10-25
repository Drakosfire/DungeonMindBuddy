import type {ReviewedStepReference} from './types'
import {authenticatedApiFetch,LiveApiError} from './liveApi'
import {canonical,exact} from '../shared/sourcePassageProtocol'
export type WorkStep={step_id:string;text:string;selected:boolean;kind:'discuss'|'prepare_insertion'}
export type WorkDispatch={command_id:string;step_id:string;client_thread_id:string;client_turn_id:string;message:string}
export type WorkExecution={command_id:string;step_id:string;status:'awaiting_dispatch'|'accepted'|'running'|'completed'|'prepared'|'failed'|'interrupted'|'needs_attention';turn_id:string|null;attempt:number|null;result:{kind:'reply';text:string|null}|{kind:'page_proposal';action_id:string}|null}
export type WorkPlan={schema:'dmb_reviewed_work_plan_v1';world_id:string;conversation_id:string;source_turn_id:string;source_answer_sha256:string;document_id:string;revision:number;steps:WorkStep[];dispatches:WorkDispatch[];execution:WorkExecution[]}
export type WorkPlanScope={worldId:string;conversationId:string;turnId:string;source:string}
const uuid=(v:unknown):v is string=>typeof v==='string'&&/^[a-f0-9]{8}-(?:[a-f0-9]{4}-){3}[a-f0-9]{12}$/i.test(v)
async function hash(s:string){return Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',new TextEncoder().encode(s))),b=>b.toString(16).padStart(2,'0')).join('')}
async function checked(v:unknown,s:WorkPlanScope):Promise<WorkPlan>{
 if(!exact(v,['schema','world_id','conversation_id','source_turn_id','source_answer_sha256','document_id','revision','steps','dispatches','execution'])
  ||v.schema!=='dmb_reviewed_work_plan_v1'||v.world_id!==s.worldId||v.conversation_id!==s.conversationId||v.source_turn_id!==s.turnId
  ||v.source_answer_sha256!==await hash(s.source)||typeof v.document_id!=='string'||!v.document_id
  ||!Number.isSafeInteger(v.revision)||(v.revision as number)<1||!Array.isArray(v.steps)||!v.steps.length||!Array.isArray(v.dispatches)||!Array.isArray(v.execution))throw new Error('The saved plan has a different source or owner.')
 const ids=new Set<string>(),commands=new Set<string>(),turns=new Set<string>()
 for(const x of v.steps){if(!exact(x,['step_id','text','selected','kind'])||!uuid(x.step_id)||ids.has(x.step_id)||typeof x.text!=='string'||!x.text.trim()||typeof x.selected!=='boolean'||!['discuss','prepare_insertion'].includes(String(x.kind)))throw new Error('Invalid reviewed step.');ids.add(x.step_id)}
 for(const x of v.dispatches){if(!exact(x,['command_id','step_id','client_thread_id','client_turn_id','message'])||!uuid(x.command_id)||commands.has(x.command_id)||!ids.has(String(x.step_id))||!uuid(x.client_thread_id)||!uuid(x.client_turn_id)||turns.has(x.client_turn_id)||typeof x.message!=='string'||!x.message.trim())throw new Error('Invalid plan continuation.');commands.add(x.command_id);turns.add(x.client_turn_id)}
 if(v.execution.length!==v.dispatches.length)throw new Error('Missing continuation result.')
 for(const [i,x] of v.execution.entries()){
  const d=v.dispatches[i] as WorkDispatch
  if(!exact(x,['command_id','step_id','status','turn_id','attempt','result'])||x.command_id!==d.command_id||x.step_id!==d.step_id
   ||!['awaiting_dispatch','accepted','running','completed','prepared','failed','interrupted','needs_attention'].includes(String(x.status))
   ||!(x.turn_id===null||uuid(x.turn_id))||!(x.attempt===null||Number.isSafeInteger(x.attempt)&&(x.attempt as number)>0)
   ||!(x.result===null||exact(x.result,['kind','text'])&&x.result.kind==='reply'&&(x.result.text===null||typeof x.result.text==='string')||exact(x.result,['kind','action_id'])&&x.result.kind==='page_proposal'&&uuid(x.result.action_id)))throw new Error('Invalid plan result.')
 }
 return v as unknown as WorkPlan
}
function path(s:WorkPlanScope){return `/api/live/agent/worlds/${encodeURIComponent(s.worldId)}/conversations/${encodeURIComponent(s.conversationId)}/work-plans/${encodeURIComponent(s.turnId)}`}
async function call(url:string,init?:RequestInit){const {response}=await authenticatedApiFetch(url,{...init,cache:'no-store',headers:{'Content-Type':'application/json'}});const b=await response.json();if(!response.ok)throw new LiveApiError(typeof b.detail==='string'?b.detail:'The saved plan is unavailable.',response.status);return b as unknown}
export async function getWorkPlan(s:WorkPlanScope){const b=await call(path(s));if(!exact(b,['schema','world_id','conversation_id','source_turn_id','plan'])||b.schema!=='dmb_work_plan_response_v1'||b.world_id!==s.worldId||b.conversation_id!==s.conversationId||b.source_turn_id!==s.turnId)throw new Error('The plan response belongs elsewhere.');return b.plan===null?null:checked(b.plan,s)}
export async function saveWorkPlan(s:WorkPlanScope,revision:number,steps:WorkStep[]){return checked(await call(path(s),{method:'PUT',body:JSON.stringify({expected_revision:revision,steps})}),s)}
export async function continueWorkPlan(s:WorkPlanScope,p:WorkPlan,stepId:string,commandId:string){const b=await call(path(s)+'/continue',{method:'POST',body:JSON.stringify({expected_revision:p.revision,step_id:stepId,command_id:commandId})});if(!exact(b,['plan','dispatch','reviewed_step']))throw new Error('Missing continuation.');const plan=await checked(b.plan,s),d=plan.dispatches.find(x=>canonical(x)===canonical(b.dispatch));if(!d||d.step_id!==stepId)throw new Error('This continuation belongs to another step.');const ref=b.reviewed_step;if(!(ref===null||exact(ref,['conversation_id','source_turn_id','command_id'])&&ref.conversation_id===s.conversationId&&ref.source_turn_id===s.turnId&&ref.command_id===d.command_id))throw new Error('Invalid reviewed action reference.');return {plan,dispatch:d,reference:ref as ReviewedStepReference|null}}
