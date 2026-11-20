import type {BuildProposalBasis,BuildPageBodyTarget,BuildPageEndTarget} from './buildDocumentProposalApi';
import {authenticatedApiFetch} from './liveApi';
export interface ProposalApplyReceipt {
  page_body_target?:BuildPageBodyTarget|null;
  page_end_target?:BuildPageEndTarget|null;
  placement_caret:number;apply_id:string; before_editor_sha256:string; after_editor_sha256:string;
  before_draft_sha256:string; after_draft_sha256:string; reviewed_sha256:string;
}
export interface PlacementCapability {
  command_id:string;conversation_id:string;expected_pointer_revision:number;
  basis:BuildProposalBasis;draft_markdown:string;
}
export interface RetiredPlacement {
  basis:BuildProposalBasis;markdown:string;markdown_sha256:string;apply:ProposalApplyReceipt|null;
  command_id:string|null;disposition:'superseded_unresolved'|'superseded_unapplied';
}
export interface BuildProposalReview {
  page_body_target?:BuildPageBodyTarget|null;
  page_end_target?:BuildPageEndTarget|null;
  schema:'dmb_build_proposal_review_v2'|'dmb_build_proposal_review_v3';world_id:string;action_id:string;reservation_sha256:string;
  placement_caret:number;revision:number;state:'editing'|'discarded'|'applying'|'applied';markdown:string;markdown_sha256:string;
  apply:ProposalApplyReceipt|null;updated_at:string;placement?:PlacementCapability;retired_placements?:RetiredPlacement[];
}
export type BuildReviewCommand = {operation:'open'|'save'|'move'|'discard'|'prepare'|'confirm'|'replace_placement';expected_revision:number;
  page_end_target?:BuildPageEndTarget;page_body_target?:BuildPageBodyTarget;placement?:PlacementCapability;placement_caret?:number;markdown?:string;apply_id?:string;after_editor_sha256?:string;after_draft_sha256?:string};
export async function proposalReview(world:string,action:string,command?:BuildReviewCommand):Promise<BuildProposalReview> {
  const {response}=await authenticatedApiFetch(`/api/live/agent/worlds/${encodeURIComponent(world)}/build-proposals/${encodeURIComponent(action)}/review`,
    command?{method:'POST',cache:'no-store',body:JSON.stringify(command)}:{cache:'no-store'});
  if(!response.ok)throw new Error(response.status===409?'The saved suggestion changed. Your local text is retained; reopen its saved review.':'The suggestion could not be checked. Your local text is retained.');
  const result=await response.json() as BuildProposalReview;
  if(!['dmb_build_proposal_review_v2','dmb_build_proposal_review_v3'].includes(result.schema)||result.world_id!==world||result.action_id!==action)throw new Error('The suggestion belongs to a different page request.');
  return result;
}
