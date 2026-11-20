import type {SessionReview} from '../playSurface/review/sessionReviewApi';
import type {PlayRunContent} from '../playSurface/playRunContentTypes';
import {useTourOwnerReading,type TourDispatchScope} from './GuidedTour';
import {useTourRun} from './RunScope';
export interface AcknowledgedSessionReview {dispatchScope?:TourDispatchScope|null;worldId:string;runId:string;revision:number;commandId:string}
export function useSessionReviewTourObservation({review,content,acknowledged,blocked,error}:{review:SessionReview|null;content:PlayRunContent;acknowledged:AcknowledgedSessionReview|null;blocked:boolean;error:string|null}){
 const scope=useTourRun(),checkpoint=review?.checkpoint;
 const origin=checkpoint?.content.origin;
 const matching=!!scope&&review?.world_id===scope.target.worldId&&review.run_id===scope.target.objectId&&checkpoint?.run_revision===scope.target.revision
  &&checkpoint.content.world_id===scope.target.worldId&&checkpoint.content.run_id===scope.target.objectId
  &&origin?.playable_artifact_id===scope.parent.objectId&&origin.playable_revision===scope.parent.revision&&origin.playable_work_revision_id===scope.parent.revisionId&&origin.playable_content_sha256===scope.parent.digest
  &&checkpoint.content.edition_revision===content.edition_revision&&checkpoint.content.edition_revision_id===content.edition_revision_id&&checkpoint.content.content_sha256===content.content_sha256;
 const usable=matching&&!blocked&&!error&&review.status==='ended'&&!!review.final_thoughts.trim();
 const fresh=!!review&&acknowledged?.worldId===review.world_id&&acknowledged.runId===review.run_id&&acknowledged.revision===review.revision;
 useTourOwnerReading(scope?{step:'reflection',dispatchScope:acknowledged?.dispatchScope,target:scope.target,parent:scope.parent,control:'reflection',status:error?'failed':usable?'ready':'unavailable',reason:error??(usable?undefined:'Finish the saved session and save nonempty closing reflections. Pending drafts or a changed checkpoint remain separate from this demonstration.'),
  ...(usable?{observation:{step:'reflection',target:scope.target,parent:scope.parent,origin:fresh?'acknowledged':'existing',observedAt:review.updated_at,receiptId:`review:${review.run_id}:${review.revision}`,proof:{kind:'session-review',reviewRevision:review.revision,checkpointRunRevision:checkpoint.run_revision,contentRevision:checkpoint.content.edition_revision,contentRevisionId:checkpoint.content.edition_revision_id,contentDigest:checkpoint.content.content_sha256,commandId:fresh?acknowledged.commandId:null}}}:{})}:null);
}
