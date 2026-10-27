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
  origin:{action_id:string;idempotency_key:string;conversation_id:string;turn_id:string;[key:string]:unknown};
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
  if(!response.ok)throw new Error(response.status===409
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
