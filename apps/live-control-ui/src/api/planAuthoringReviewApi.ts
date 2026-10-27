import {canonical,exact} from '../shared/sourcePassageProtocol';
import {authenticatedApiFetch} from './liveApi';

export interface PlanAuthoringCapture {
  schema:'dmb_plan_authoring_capture_v1';idempotency_key:string;conversation_id:string;
  expected_pointer_revision:number;world_id:string;document_id:string;base_revision:number;base_content_sha256:string;
  draft_markdown:string;draft_sha256:string;editor_json:string;editor_sha256:string;selection_json:string;selection_sha256:string;
  from:number;to:number;draft_generation:number;selection_generation:number;
  target_kind:'insert_at_caret'|'replace_selection'|'replace_playable_body';selected_text:string;
  playable_target:{kind:'scene'|'beat'|'choice'|'option';id:string;marker_grammar_version:'v1'|'v2';
    body_scope:'heading_body'|'beat_direct_body'|'option_item_content';
    range_semantics_version:'plan-playable-ranges-v1';body_serialization_version:'plan-playable-body-markdown-v1';
    body_markdown:string;body_sha256:string}|null;
}
export interface PlanAuthoredProposal {
  schema:'dmb_plan_authored_proposal_v1';capture:PlanAuthoringCapture;replacement_markdown:string;
  origin:{schema:'dmb_plan_jev_proposal_origin_v1';action_id:string;idempotency_key:string;conversation_id:string;turn_id:string;
    action_request_fingerprint:string;action_fence:number;product_attempt:number;expected_pointer_revision:number;
    context_receipt_sha256:string;execution_policy_sha256:string;capture_sha256:string;controller_attempt_id:string;
    selection_event_id:string;expected_turn_revision:number;writer_attempt_id:string;writer_envelope_sha256:string;
    raw_reply_sha256:string;evidence_event_ids:string[];replacement_markdown_sha256:string;
    basis:{world_id:string;document_id:string;object_revision:number;work_revision_id:string;revision_n:number;content_sha256:string}};
}
export interface PlanReviewApplication {
  application_id:string;capture:PlanAuthoringCapture;markdown:string;markdown_sha256:string;
  after_editor_json:string;after_editor_sha256:string;after_markdown:string;after_draft_sha256:string;after_title:string;
  base_work_revision_id:string;base_revision_n:number;outcome:'applying'|'saved'|'not_applied'|'superseded';
  saved_work_revision_id:string|null;saved_revision_n:number|null;
}
export interface PlanAuthoringReview {
  schema:'dmb_plan_authoring_review_v1';world_id:string;action_id:string;origin_sha256:string;
  revision:number;state:'editing'|'applying'|'applied'|'discarded';markdown:string;markdown_sha256:string;
  capture:PlanAuthoringCapture;applications:PlanReviewApplication[];
  last_command_id:string;last_command_sha256:string;updated_at:string;
}
export interface PlanReviewSnapshot {
  schema:'dmb_plan_authoring_review_snapshot_v1';world_id:string;action_id:string;origin_sha256:string;
  review:PlanAuthoringReview|null;
}
type CommandIdentity={command_id:string;origin_sha256:string;expected_revision:number};
export type PlanReviewCommand=CommandIdentity&(
  |{operation:'open'|'discard'}
  |{operation:'save';markdown:string}
  |{operation:'move';capture:PlanAuthoringCapture}
  |{operation:'prepare';application_id:string;after_editor_json:string;after_editor_sha256:string;after_markdown:string;after_draft_sha256:string;after_title:string}
  |{operation:'confirm';application_id:string}
  |{operation:'resolve_before'|'recover_placement';application_id:string;capture:PlanAuthoringCapture}
);
export class PlanReviewRequestError extends Error {
  constructor(readonly status:number,message:string){super(message);this.name='PlanReviewRequestError';}
}
type WithoutIdentity<T>=T extends CommandIdentity?Omit<T,keyof CommandIdentity>:never;
export type PlanReviewOperation=WithoutIdentity<PlanReviewCommand>;
const digest=/^[a-f0-9]{64}$/;
function path(world:string,action:string){return `/api/live/agent/worlds/${encodeURIComponent(world)}/plan-proposals/${encodeURIComponent(action)}/review`;}
function checkedReview(review:PlanAuthoringReview,world:string,action:string,origin:string){
  if(review?.schema!=='dmb_plan_authoring_review_v1'||review.world_id!==world||review.action_id!==action
    ||review.origin_sha256!==origin||!digest.test(origin)||!Number.isSafeInteger(review.revision)||review.revision<1
    ||review.capture?.world_id!==world||!Array.isArray(review.applications))throw new Error('The Plan suggestion review does not match its owner. Your local copy is retained.');
  return review;
}
async function responseJson(world:string,action:string,command?:PlanReviewCommand):Promise<unknown>{
  const {response}=await authenticatedApiFetch(path(world,action),command
    ?{method:'POST',cache:'no-store',body:JSON.stringify(command)}:{cache:'no-store'});
  if(!response.ok)throw new PlanReviewRequestError(response.status,response.status===409
    ?'The Plan or suggestion changed. Your local copy is retained; inspect its saved review before continuing.'
    :'The Plan suggestion could not be checked. Your local copy and operation identity are retained.');
  return response.json();
}
export async function readPlanAuthoringReview(world:string,action:string):Promise<PlanReviewSnapshot>{
  const snapshot=await responseJson(world,action) as PlanReviewSnapshot;
  if(snapshot?.schema!=='dmb_plan_authoring_review_snapshot_v1'||snapshot.world_id!==world||snapshot.action_id!==action
    ||!digest.test(snapshot.origin_sha256))throw new Error('The Plan suggestion snapshot belongs to another request.');
  if(snapshot.review!==null)checkedReview(snapshot.review,world,action,snapshot.origin_sha256);
  return snapshot;
}
export async function commandPlanAuthoringReview(world:string,action:string,command:PlanReviewCommand):Promise<PlanAuthoringReview>{
  const review=checkedReview(await responseJson(world,action,command) as PlanAuthoringReview,world,action,command.origin_sha256);
  if(review.last_command_id!==command.command_id)throw new Error('The Plan suggestion did not acknowledge this exact command. Retain its identity for recovery.');
  return review;
}


const uuid=(v:unknown):v is string=>typeof v==='string'&&/^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$/i.test(v);
const hash=(v:unknown):v is string=>typeof v==='string'&&digest.test(v);
const positive=(v:unknown):v is number=>Number.isSafeInteger(v)&&Number(v)>0;
const nonnegative=(v:unknown):v is number=>Number.isSafeInteger(v)&&Number(v)>=0;
export function isPlanAuthoringCapture(v:unknown):v is PlanAuthoringCapture {
  if(!exact(v,['schema','idempotency_key','conversation_id','expected_pointer_revision','world_id','document_id','base_revision',
    'base_content_sha256','draft_markdown','draft_sha256','editor_json','editor_sha256','selection_json','selection_sha256',
    'from','to','draft_generation','selection_generation','target_kind','selected_text','playable_target'])
    ||v.schema!=='dmb_plan_authoring_capture_v1'||!uuid(v.idempotency_key)||!uuid(v.conversation_id)
    ||!positive(v.expected_pointer_revision)||typeof v.world_id!=='string'||!v.world_id||typeof v.document_id!=='string'||!v.document_id
    ||!positive(v.base_revision)||!hash(v.base_content_sha256)||!hash(v.draft_sha256)||!hash(v.editor_sha256)||!hash(v.selection_sha256)
    ||typeof v.draft_markdown!=='string'||typeof v.editor_json!=='string'||typeof v.selection_json!=='string'
    ||!nonnegative(v.from)||!nonnegative(v.to)||v.to<v.from||!nonnegative(v.draft_generation)||!nonnegative(v.selection_generation)
    ||typeof v.selected_text!=='string'||!['insert_at_caret','replace_selection','replace_playable_body'].includes(String(v.target_kind)))return false;
  try {const doc=JSON.parse(v.editor_json),selection=JSON.parse(v.selection_json);
    if(doc?.type!=='doc'||!Array.isArray(doc.content)||selection?.type!=='text'||!nonnegative(selection.anchor)||!nonnegative(selection.head))return false;
    if(v.target_kind!=='replace_playable_body'&&(v.from!==Math.min(selection.anchor,selection.head)||v.to!==Math.max(selection.anchor,selection.head)))return false;
  }catch{return false;}
  if(v.target_kind==='replace_playable_body'){
    const t=v.playable_target;
    return exact(t,['kind','id','marker_grammar_version','body_scope','range_semantics_version','body_serialization_version','body_markdown','body_sha256'])
      &&['scene','beat','choice','option'].includes(String(t.kind))&&typeof t.id==='string'&&t.id.startsWith(`${t.kind}:`)
      &&['v1','v2'].includes(String(t.marker_grammar_version))&&['heading_body','beat_direct_body','option_item_content'].includes(String(t.body_scope))
      &&t.range_semantics_version==='plan-playable-ranges-v1'&&t.body_serialization_version==='plan-playable-body-markdown-v1'
      &&typeof t.body_markdown==='string'&&!!t.body_markdown&&hash(t.body_sha256);
  }
  return v.playable_target===null&&(v.target_kind==='insert_at_caret'?v.from===v.to:v.from<v.to);
}
export function isPlanAuthoredProposal(v:unknown):v is PlanAuthoredProposal {
  if(!exact(v,['schema','capture','origin','replacement_markdown'])||v.schema!=='dmb_plan_authored_proposal_v1'
    ||!isPlanAuthoringCapture(v.capture)||typeof v.replacement_markdown!=='string'||!v.replacement_markdown.trim())return false;
  const o=v.origin,c=v.capture;
  if(!exact(o,['schema','action_id','idempotency_key','action_request_fingerprint','action_fence','basis','conversation_id','turn_id',
    'product_attempt','expected_pointer_revision','context_receipt_sha256','execution_policy_sha256','capture_sha256','controller_attempt_id',
    'selection_event_id','expected_turn_revision','writer_attempt_id','writer_envelope_sha256','raw_reply_sha256','evidence_event_ids','replacement_markdown_sha256'])
    ||o.schema!=='dmb_plan_jev_proposal_origin_v1'
    ||!['action_id','idempotency_key','conversation_id','turn_id','controller_attempt_id','selection_event_id','writer_attempt_id'].every(k=>uuid(o[k]))
    ||!['action_request_fingerprint','context_receipt_sha256','execution_policy_sha256','capture_sha256','writer_envelope_sha256','raw_reply_sha256','replacement_markdown_sha256'].every(k=>hash(o[k]))
    ||!['action_fence','product_attempt','expected_pointer_revision','expected_turn_revision'].every(k=>positive(o[k]))
    ||!Array.isArray(o.evidence_event_ids)||!o.evidence_event_ids.every(uuid)||new Set(o.evidence_event_ids).size!==o.evidence_event_ids.length
    ||o.idempotency_key!==c.idempotency_key||o.conversation_id!==c.conversation_id||o.expected_pointer_revision!==c.expected_pointer_revision)return false;
  const b=o.basis;
  return exact(b,['world_id','document_id','object_revision','work_revision_id','revision_n','content_sha256'])
    &&b.world_id===c.world_id&&b.document_id===c.document_id&&b.object_revision===c.base_revision
    &&b.content_sha256===c.base_content_sha256&&uuid(b.work_revision_id)&&positive(b.revision_n);
}
async function textHash(text:string){return Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',new TextEncoder().encode(text))),b=>b.toString(16).padStart(2,'0')).join('');}
export async function planProposalDigestsBound(v:unknown):Promise<boolean>{
  if(!isPlanAuthoredProposal(v))return false;
  const c=v.capture;
  try {const actual=await Promise.all([textHash(c.draft_markdown),textHash(c.editor_json),textHash(c.selection_json),
    textHash(canonical(c)),textHash(v.replacement_markdown)]);
    return actual.every((value,i)=>value===[c.draft_sha256,c.editor_sha256,c.selection_sha256,v.origin.capture_sha256,v.origin.replacement_markdown_sha256][i])
      &&(!c.playable_target||await textHash(c.playable_target.body_markdown)===c.playable_target.body_sha256);
  }catch{return false;}
}
