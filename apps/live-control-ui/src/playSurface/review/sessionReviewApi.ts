import {authenticatedApiFetch, LiveApiError} from "../../api/liveApi";
import type {PlayRunContent} from "../playRunContentTypes";
export interface SessionReview {
  schema_version:"dmb_session_review_v1";world_id:string;run_id:string;revision:number;status:"playing"|"ended";updated_at:string;
  draft_markdown:string;
  checkpoint:{run_revision:number;captured_at:string;progress:{notes_by_element_id:Record<string,string>;[key:string]:unknown};content:PlayRunContent};
}
export interface ReviewRead {world_id:string;run_id:string;review:SessionReview|null;source_changed:boolean}
export interface ReviewCommand {action:"end"|"save"|"reopen";expected_revision:number;expected_run_revision:number;expected_content_sha256:string;draft_markdown:string}
async function call(path:string,init:RequestInit={}) {
 const {response}=await authenticatedApiFetch(path,{...init,cache:"no-store"});
 const body=await response.json();
 if(!response.ok)throw new LiveApiError(typeof body.detail==="string"?body.detail:"Session review could not be saved.",response.status);
 return body;
}
export async function readSessionReview(runId:string,worldId:string):Promise<ReviewRead>{
 const value=await call(`/api/live/world-play-runs/v2/${encodeURIComponent(runId)}/review?world_id=${encodeURIComponent(worldId)}`);
 if(value.run_id!==runId||value.world_id!==worldId)throw new Error("Review belongs to another session.");
 if(value.review)validate(value.review,runId,worldId);
 return value;
}
function validate(value:SessionReview,runId:string,worldId:string){
 if(value.schema_version!=="dmb_session_review_v1"||value.run_id!==runId||value.world_id!==worldId||!Number.isInteger(value.revision)||value.revision<1||!["playing","ended"].includes(value.status)||typeof value.draft_markdown!=="string"||!value.checkpoint?.progress?.notes_by_element_id||!value.checkpoint?.content?.content_sha256)throw new Error("Invalid saved session review.");
}
export async function saveSessionReview(runId:string,worldId:string,commandId:string,command:ReviewCommand):Promise<SessionReview>{
 const value=await call(`/api/live/world-play-runs/v2/${encodeURIComponent(runId)}/review/commands/${encodeURIComponent(commandId)}?world_id=${encodeURIComponent(worldId)}`,{method:"PUT",body:JSON.stringify(command)});
 validate(value,runId,worldId);return value;
}
export function exportSessionReview(review:SessionReview):string{
 return `${review.draft_markdown}\n\n---\n\n# Review source evidence\n\nSession: ${review.run_id}\nWorld: ${review.world_id}\nReview revision: ${review.revision}\nCheckpoint: ${review.checkpoint.captured_at}\nSaved session revision: ${review.checkpoint.run_revision}\nSession content SHA-256: ${review.checkpoint.content.content_sha256}\n\nThese are original saved notes, not additional events. Prepared content is retained separately in the session checkpoint.\n\n${Object.entries(review.checkpoint.progress.notes_by_element_id).map(([id,note])=>`## ${id}\n\n${note}`).join("\n\n")}\n`;
}
