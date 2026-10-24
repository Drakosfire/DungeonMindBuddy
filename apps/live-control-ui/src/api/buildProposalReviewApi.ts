import {authenticatedApiFetch} from './liveApi';
export interface ProposalApplyReceipt {
  apply_id:string; before_editor_sha256:string; after_editor_sha256:string;
  before_draft_sha256:string; after_draft_sha256:string; reviewed_sha256:string;
}
export interface BuildProposalReview {
  schema:'dmb_build_proposal_review_v1';world_id:string;action_id:string;reservation_sha256:string;
  revision:number;state:'editing'|'discarded'|'applying'|'applied';markdown:string;markdown_sha256:string;
  apply:ProposalApplyReceipt|null;updated_at:string;
}
export type BuildReviewCommand = {operation:'open'|'save'|'discard'|'prepare'|'confirm';expected_revision:number;
  markdown?:string;apply_id?:string;after_editor_sha256?:string;after_draft_sha256?:string};
export async function proposalReview(world:string,action:string,command?:BuildReviewCommand):Promise<BuildProposalReview> {
  const {response}=await authenticatedApiFetch(`/api/live/agent/worlds/${encodeURIComponent(world)}/build-proposals/${encodeURIComponent(action)}/review`,
    command?{method:'POST',cache:'no-store',body:JSON.stringify(command)}:{cache:'no-store'});
  if(!response.ok)throw new Error(response.status===409?'The saved suggestion changed. Your local text is retained; reopen its saved review.':'The suggestion could not be checked. Your local text is retained.');
  const result=await response.json() as BuildProposalReview;
  if(result.schema!=='dmb_build_proposal_review_v1'||result.world_id!==world||result.action_id!==action)throw new Error('The suggestion belongs to a different page request.');
  return result;
}
