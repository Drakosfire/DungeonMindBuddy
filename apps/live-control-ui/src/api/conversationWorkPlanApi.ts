import {isAuthoredGraphReferenceList,isAuthoredGraphReferences,mergeAuthoredReferences} from '../agentInteraction/authoredGraphReferences'
import type {AuthoredGraphReferenceV1,AuthoredGraphReferencesV1,ReviewedStepReference} from './types'
import {authenticatedApiFetch,LiveApiError} from './liveApi'
import {canonical,exact} from '../shared/sourcePassageProtocol'
export type WorkStep={step_id:string;text:string;selected:boolean;kind:'discuss'|'prepare_insertion';references?:AuthoredGraphReferenceV1[]}
export type WorkDispatch={command_id:string;step_id:string;client_thread_id:string;client_turn_id:string;message:string;schema?:'dmb_work_plan_dispatch_v2';authored_references?:AuthoredGraphReferencesV1}
export type WorkExecution={command_id:string;step_id:string;status:'awaiting_dispatch'|'accepted'|'running'|'completed'|'prepared'|'failed'|'interrupted'|'needs_attention';turn_id:string|null;attempt:number|null;result:{kind:'reply';text:string|null}|{kind:'page_proposal';action_id:string}|null}
type WorkPlanBase={world_id:string;conversation_id:string;source_turn_id:string;source_answer_sha256:string;document_id:string;revision:number;steps:WorkStep[];dispatches:WorkDispatch[];execution:WorkExecution[]}
export type WorkPlan = WorkPlanBase & ({schema:'dmb_reviewed_work_plan_v1'}|{schema:'dmb_reviewed_work_plan_v2';objective:string}|{schema:'dmb_reviewed_work_plan_v3';objective:string;root_references:AuthoredGraphReferenceV1[]})
export const planObjective=(plan:WorkPlan|null|undefined)=>plan&&(plan.schema==='dmb_reviewed_work_plan_v2'||plan.schema==='dmb_reviewed_work_plan_v3')?plan.objective:''
export type WorkPlanScope={worldId:string;conversationId:string;turnId:string;documentId?:string}&({source:string;sourceSha256?:never}|{source?:never;sourceSha256:string})
const uuid=(v:unknown):v is string=>typeof v==='string'&&/^[a-f0-9]{8}-(?:[a-f0-9]{4}-){3}[a-f0-9]{12}$/i.test(v)
async function hash(s:string){return Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',new TextEncoder().encode(s))),b=>b.toString(16).padStart(2,'0')).join('')}
async function checked(v:unknown,s:WorkPlanScope):Promise<WorkPlan>{
 if(!exact(v,['schema','world_id','conversation_id','source_turn_id','source_answer_sha256','document_id','revision','steps','dispatches','execution',...(v&&typeof v==='object'&&'schema' in v&&['dmb_reviewed_work_plan_v2','dmb_reviewed_work_plan_v3'].includes(String(v.schema))?['objective',...(v.schema==='dmb_reviewed_work_plan_v3'?['root_references']:[])]:[])])
  ||!['dmb_reviewed_work_plan_v1','dmb_reviewed_work_plan_v2','dmb_reviewed_work_plan_v3'].includes(String(v.schema))||v.schema!=='dmb_reviewed_work_plan_v1'&&(typeof v.objective!=='string'||!v.objective.trim())||v.world_id!==s.worldId||v.conversation_id!==s.conversationId||v.source_turn_id!==s.turnId
  ||v.source_answer_sha256!==('sourceSha256' in s&&s.sourceSha256!==undefined?s.sourceSha256:await hash(s.source!))
  ||typeof v.document_id!=='string'||!v.document_id||(s.documentId!==undefined&&v.document_id!==s.documentId)
  ||!Number.isSafeInteger(v.revision)||(v.revision as number)<1||!Array.isArray(v.steps)||!v.steps.length||!Array.isArray(v.dispatches)||!Array.isArray(v.execution))throw new Error('The saved plan has a different source or owner.')
 const referenceAware=v.schema==='dmb_reviewed_work_plan_v3'
 if(referenceAware&&!isAuthoredGraphReferenceList(v.root_references,s.worldId))throw new Error('Invalid plan Graph references.')
 const ids=new Set<string>(),commands=new Set<string>(),turns=new Set<string>()
 for(const x of v.steps){if(!exact(x,['step_id','text','selected','kind',...(referenceAware?['references']:[])])||!uuid(x.step_id)||ids.has(x.step_id)||typeof x.text!=='string'||!x.text.trim()||typeof x.selected!=='boolean'||!['discuss','prepare_insertion'].includes(String(x.kind)))throw new Error('Invalid reviewed step.');if(referenceAware){if(!isAuthoredGraphReferenceList(x.references,s.worldId))throw new Error('Invalid step Graph references.');mergeAuthoredReferences(v.root_references as AuthoredGraphReferenceV1[],x.references)}ids.add(x.step_id)}
 for(const x of v.dispatches){if(!exact(x,['command_id','step_id','client_thread_id','client_turn_id','message',...('schema' in x?['schema','authored_references']:[])])||!uuid(x.command_id)||commands.has(x.command_id)||!ids.has(String(x.step_id))||!uuid(x.client_thread_id)||!uuid(x.client_turn_id)||turns.has(x.client_turn_id)||typeof x.message!=='string'||!x.message.trim())throw new Error('Invalid plan continuation.');if('schema' in x&&(!referenceAware||x.schema!=='dmb_work_plan_dispatch_v2'||!isAuthoredGraphReferences(x.authored_references,s.worldId)))throw new Error('Invalid frozen Graph references.');commands.add(x.command_id);turns.add(x.client_turn_id)}
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
const planReads=new Map<string,Promise<unknown>>()
export async function getWorkPlanRecord(s:WorkPlanScope){const url=path(s);let pending=planReads.get(url)
 if(!pending){pending=call(url);planReads.set(url,pending);const own=pending;const retire=()=>{if(planReads.get(url)===own)planReads.delete(url)};void pending.then(retire,retire)}
 const b=await pending;
 if(!exact(b,['schema','world_id','conversation_id','source_turn_id','plan',...(b&&typeof b==='object'&&'schema' in b&&b.schema==='dmb_work_plan_response_v3'?['source_references']:[])])
  ||!['dmb_work_plan_response_v2','dmb_work_plan_response_v3'].includes(String(b.schema))||b.world_id!==s.worldId||b.conversation_id!==s.conversationId||b.source_turn_id!==s.turnId
  ||b.schema==='dmb_work_plan_response_v3'&&!isAuthoredGraphReferenceList(b.source_references,s.worldId))throw new Error('The plan response belongs elsewhere.');
 const plan=b.plan===null?null:await checked(b.plan,s);
 if(plan?.schema==='dmb_reviewed_work_plan_v3'&&b.schema!=='dmb_work_plan_response_v3')throw new Error('Missing source Graph reference inventory.');
 return {plan,sourceReferences:(b.schema==='dmb_work_plan_response_v3'?b.source_references:[]) as AuthoredGraphReferenceV1[]};
}
export async function getWorkPlan(s:WorkPlanScope){return (await getWorkPlanRecord(s)).plan}
export async function saveWorkPlan(s:WorkPlanScope,revision:number,steps:WorkStep[],objective:string,rootReferences?:AuthoredGraphReferenceV1[]){
 const body=rootReferences===undefined?{schema:'dmb_reviewed_work_plan_review_v2',expected_revision:revision,steps,objective}
  :{schema:'dmb_reviewed_work_plan_review_v3',expected_revision:revision,steps:steps.map(step=>({...step,references:step.references??[]})),objective,root_references:rootReferences};
 return checked(await call(path(s),{method:'PUT',body:JSON.stringify(body)}),s);
}
export async function continueWorkPlan(s:WorkPlanScope,p:WorkPlan,stepId:string,commandId:string){const b=await call(path(s)+'/continue',{method:'POST',body:JSON.stringify({expected_revision:p.revision,step_id:stepId,command_id:commandId})});if(!exact(b,['plan','dispatch','reviewed_step']))throw new Error('Missing continuation.');const plan=await checked(b.plan,s),d=plan.dispatches.find(x=>canonical(x)===canonical(b.dispatch));if(!d||d.step_id!==stepId)throw new Error('This continuation belongs to another step.');const ref=b.reviewed_step;if(!(ref===null||exact(ref,['conversation_id','source_turn_id','command_id'])&&ref.conversation_id===s.conversationId&&ref.source_turn_id===s.turnId&&ref.command_id===d.command_id))throw new Error('Invalid reviewed action reference.');return {plan,dispatch:d,reference:ref as ReviewedStepReference|null}}
