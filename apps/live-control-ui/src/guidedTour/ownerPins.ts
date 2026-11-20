import type {SavedWorldBuildConversationContext} from '../agentInteraction/WorldAgentConversation';
import type {WorldPlayRunRecordV2} from '../api/types';
import type {TargetPin} from './protocol';
/** These functions project identities already validated by the owning surface. */
export function sourcePin(source:SavedWorldBuildConversationContext):TargetPin {
 return {kind:'source',worldId:source.worldId,objectId:source.documentId,revision:source.revision,digest:source.contentSha256};
}
export function pagePin(source:SavedWorldBuildConversationContext):TargetPin {
 return {...sourcePin(source),kind:'page'};
}
export function planPin(worldId:string,documentId:string,version:{revisionN:number;workRevisionId:string;contentSha256:string}):TargetPin {
 return {kind:'plan',worldId,objectId:documentId,revision:version.revisionN,revisionId:version.workRevisionId,digest:version.contentSha256};
}
export function runPins(run:WorldPlayRunRecordV2):{target:TargetPin;parent:TargetPin} {
 return {target:{kind:'run',worldId:run.world_id,objectId:run.run_id,revision:run.run_revision,digest:run.playable_content_sha256},
  parent:planPin(run.world_id,run.playable_artifact_id,{revisionN:run.playable_revision,workRevisionId:run.playable_work_revision_id,contentSha256:run.playable_content_sha256})};
}
