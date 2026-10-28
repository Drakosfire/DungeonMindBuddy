import {useMemo,useRef} from 'react';
import type {MarkdownCanvasSessionValue} from '../markdownCanvas/MarkdownCanvasSession';
import type {SavedWorldBuildConversationContext} from '../agentInteraction/WorldAgentConversation';
import {useTourOwnerReading} from './GuidedTour';
import {planPin,sourcePin,runPins} from './ownerPins';
import type {WorldPlayRunRecordV2} from '../api/types';
import type {PlanEncounterContext,SceneTemplateView} from '../combat/sceneTemplatesApi';

export function BuildTourObservations({source,session}:{source:SavedWorldBuildConversationContext|null;session:MarkdownCanvasSessionValue|null}){
 const target=source?sourcePin(source):null;
 const verified=!!source&&!source.dirty&&session?.phase==='ready_clean'&&!session.activeCommand;
 const receipt=session?.lastCommitReceipt;
 const initialReceipt=useRef(receipt);
 const stamp=useMemo(()=>new Date().toISOString(),[receipt]);
 const receiptStamp=receipt?.committed_record?.updated_at;
 const saved=verified&&receipt!==initialReceipt.current&&receipt?.writer_ok===true&&receipt.world_id===source.worldId&&typeof receiptStamp==='string'&&Number.isFinite(Date.parse(receiptStamp))&&receipt.document_id===source.documentId&&receipt.registry_revision===source.revision&&receipt.normalized_content_sha256===source.contentSha256;
 useTourOwnerReading({step:'source',target,control:'source',status:verified?'ready':'unavailable',reason:verified?undefined:'Open a verified page. Unsaved drafts and pending work are kept; finish or inspect them through the ordinary controls.',
  ...(verified&&target?{observation:{step:'source',target,observedAt:stamp,origin:'existing',receiptId:`source:${target.objectId}:${target.revision}:${target.digest}`}}:{})});
 useTourOwnerReading({step:'authoring',target,control:'save',status:verified?'ready':'unavailable',reason:verified?undefined:session?.saveDisabledReason??'Finish the page through the ordinary editor and Save controls.',
  ...(verified&&target?{observation:{step:'authoring',target,observedAt:saved?receiptStamp:stamp,origin:saved?'acknowledged':'existing',receiptId:saved?`source-save:${receipt.registry_revision}:${receipt.normalized_content_sha256}`:`source-existing:${target.objectId}:${target.revision}:${target.digest}`}}:{})});
 return null;
}
export interface TourPlanSave {worldId:string;documentId:string;revision:number;digest:string;observedAt:string}
export function PlanTourObservation({verified,error,saved=null,registryRevision=null}:{verified:{worldId:string;documentId:string;pin:{revisionN:number;workRevisionId:string;contentSha256:string}}|null;error:string|null;saved?:TourPlanSave|null;registryRevision?:number|null}){
 const target=verified?planPin(verified.worldId,verified.documentId,verified.pin):null;
 const stamp=useMemo(()=>new Date().toISOString(),[verified]);
 const acknowledged=!!saved&&!!target&&saved.worldId===target.worldId&&saved.documentId===target.objectId&&saved.revision===registryRevision&&saved.digest===target.digest;
 useTourOwnerReading({step:'plan',target,control:'plan',status:error?'failed':target?'ready':'unavailable',reason:error??(target?undefined:'Save the Plan, then use Start Play to inspect its exact saved version. Opening that preview does not start a session.'),
  ...(target&&!error?{observation:{step:'plan',target,observedAt:acknowledged?saved!.observedAt:stamp,origin:acknowledged?'acknowledged':'existing',receiptId:`plan:${target.revisionId}:${target.digest}`}}:{})});
 return null;
}

/** The scene owner has already admitted this view or verified its creation receipt. */
export function EncounterTourObservation({view,context,acknowledgedOperation,error,pending}:{view:SceneTemplateView|null;context:PlanEncounterContext;acknowledgedOperation:string|null;error:string|null;pending:boolean}){
 const target=view?planPin(view.binding.world_id,view.binding.origin.document_id,{revisionN:view.binding.origin.revision_n,workRevisionId:view.binding.origin.work_revision_id,contentSha256:view.binding.origin.content_sha256}):null;
 const version=view?.versions.find(item=>item.revision===view.encounter.revision);
 const usable=!error&&!!view&&!!version&&view.scene_present&&context.canCreate&&!pending&&view.binding.origin.content_sha256===context.contentSha256;
 useTourOwnerReading({step:'encounter',target,control:'encounter',status:error?'failed':usable?'ready':'unavailable',
  reason:error??(usable?undefined:pending?'Resolve the retained encounter creation with its ordinary recovery controls.':'Open the intended scene and a clean saved Plan. An encounter from another saved Plan version remains an older example.'),
  ...(usable&&target&&view&&version?{observation:{step:'encounter',target,observedAt:view.binding.created_at,origin:acknowledgedOperation===view.binding.operation_id?'acknowledged':'existing',receiptId:`encounter:${view.binding.operation_id}:${version.revision}:${version.digest}`,
   proof:{kind:'encounter',sceneId:view.binding.origin.scene_id,encounterId:view.binding.encounter_id,revision:version.revision,digest:version.digest,operationId:view.binding.operation_id}}}:{})});
 return null;
}

export function PlayTourObservation({run,blocked,error}:{run:WorldPlayRunRecordV2|null;blocked:boolean;error:string|null}){
 const pins=run?runPins(run):null;
 useTourOwnerReading({step:'play',target:pins?.target??null,...(pins?{parent:pins.parent}:{}),control:'start-play',status:error?'failed':run&&!blocked?'ready':'unavailable',reason:error??(run&&!blocked?undefined:'Open the exact saved Run through Play. Resolve pending session edits and recovery before inspecting its saved state.'),
  ...(run&&pins&&!blocked&&!error?{observation:{step:'play',target:pins.target,parent:pins.parent,observedAt:run.updated_at,origin:'existing',receiptId:`run:${run.run_id}:${run.run_revision}:${run.playable_work_revision_id}`}}:{})});
 return null;
}
