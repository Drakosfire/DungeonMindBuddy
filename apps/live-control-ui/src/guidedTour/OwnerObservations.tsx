import {useMemo,useRef} from 'react';
import type {MarkdownCanvasSessionValue} from '../markdownCanvas/MarkdownCanvasSession';
import type {SavedWorldBuildConversationContext} from '../agentInteraction/WorldAgentConversation';
import {useTourOwnerReading,type TourDispatchScope} from './GuidedTour';
import {planPin,sourcePin,pagePin,runPins} from './ownerPins';
import type {WorldPlayRunRecordV2} from '../api/types';
import {combatDraftEqual} from '../combat/combatRecovery';
import {sameEncounterScope} from './EncounterScope';
import type {PreparedCombatOwnerReading} from '../surface/modules/CombatRosterModule';
import type {PlanEncounterContext,SceneTemplateView} from '../combat/sceneTemplatesApi';

export function BuildTourObservations({source,session}:{source:SavedWorldBuildConversationContext|null;session:MarkdownCanvasSessionValue|null}){
 const sourceTarget=source?sourcePin(source):null;
 const target=source?pagePin(source):null;
 const verified=!!source&&!source.dirty&&session?.phase==='ready_clean'&&!session.activeCommand;
 const receipt=session?.lastCommitReceipt;
 const initialReceipt=useRef(receipt);
 const stamp=useMemo(()=>new Date().toISOString(),[receipt]);
 const receiptStamp=receipt?.committed_record?.updated_at;
 const saved=verified&&receipt!==initialReceipt.current&&receipt?.writer_ok===true&&receipt.committed_record?.world_id===source.worldId&&(receipt.world_id==null||receipt.world_id===source.worldId)&&typeof receiptStamp==='string'&&Number.isFinite(Date.parse(receiptStamp))&&receipt.document_id===source.documentId&&receipt.registry_revision===source.revision&&receipt.normalized_content_sha256===source.contentSha256;
 useTourOwnerReading({step:'source',target:sourceTarget,control:'source',label:source?.title,status:verified?'ready':'unavailable',reason:verified?undefined:'Open a verified page. Unsaved drafts and pending work are kept; finish or inspect them through the ordinary controls.',
  ...(verified&&sourceTarget?{observation:{step:'source',target:sourceTarget,observedAt:stamp,origin:'existing',receiptId:`source:${sourceTarget.objectId}:${sourceTarget.revision}:${sourceTarget.digest}`}}:{})});
 useTourOwnerReading({step:'authoring',dispatchScope:session?.tourSaveScope,target,control:'save',label:source?.title,status:verified?'ready':'unavailable',reason:verified?undefined:session?.saveDisabledReason??'Finish the page through the ordinary editor and Save controls.',
  ...(verified&&target?{observation:{step:'authoring',target,observedAt:saved?receiptStamp:stamp,origin:saved?'acknowledged':'existing',receiptId:saved?`source-save:${receipt.registry_revision}:${receipt.normalized_content_sha256}`:`source-existing:${target.objectId}:${target.revision}:${target.digest}`}}:{})});
 return null;
}
export interface TourPlanSave {dispatchScope?:TourDispatchScope|null;worldId:string;documentId:string;revision:number;digest:string;observedAt:string}
export function PlanTourObservation({verified,error,saved=null,registryRevision=null,label}:{verified:{worldId:string;documentId:string;pin:{revisionN:number;workRevisionId:string;contentSha256:string}}|null;error:string|null;label?:string;saved?:TourPlanSave|null;registryRevision?:number|null}){
 const target=verified?planPin(verified.worldId,verified.documentId,verified.pin):null;
 const stamp=useMemo(()=>new Date().toISOString(),[verified]);
 const acknowledged=!!saved&&!!target&&saved.worldId===target.worldId&&saved.documentId===target.objectId&&saved.revision===registryRevision&&saved.digest===target.digest;
 useTourOwnerReading({step:'plan',dispatchScope:saved?.dispatchScope,target,control:'plan',label,status:error?'failed':target?'ready':'unavailable',reason:error??(target?undefined:'Save the Plan, then use Start Play to inspect its exact saved version. Opening that preview does not start a session.'),
  ...(target&&!error?{observation:{step:'plan',target,observedAt:acknowledged?saved!.observedAt:stamp,origin:acknowledged?'acknowledged':'existing',receiptId:`plan:${target.revisionId}:${target.digest}`}}:{})});
 return null;
}

/** The scene owner has already admitted this view or verified its creation receipt. */
export function EncounterTourObservation({view,context,roster,acknowledgedOperation,dispatchScope,error,pending}:{view:SceneTemplateView|null;context:PlanEncounterContext;roster:PreparedCombatOwnerReading|null;acknowledgedOperation:string|null;dispatchScope?:TourDispatchScope|null;error:string|null;pending:boolean}){
 const pin=context.verifiedPlan;
 const target=pin&&pin.contentSha256===context.contentSha256?planPin(context.worldId,context.documentId,pin):null;
 const version=view?.versions.find(item=>item.revision===view.encounter.revision);
 const scoped=!!view&&view.binding.world_id===context.worldId&&view.binding.origin.document_id===context.documentId&&view.binding.origin.scene_id===context.sceneId&&view.encounter.world_id===context.worldId&&view.encounter.encounter_id===view.binding.encounter_id;
 const record=roster?.record;
 const admitted=scoped&&!!record&&record.world_id===context.worldId&&record.encounter_id===view.binding.encounter_id&&record.revision===view.encounter.revision&&combatDraftEqual(record.draft,view.encounter.draft);
 const usable=!error&&!!target&&!!view&&!!version&&view.scene_present&&context.canCreate&&!pending&&!!roster&&!roster.blocked&&!roster.error&&admitted;
 const saved=roster?.acknowledged;
 const scope=target&&view?{plan:target,sceneId:context.sceneId,encounterId:view.binding.encounter_id}:null;
 const acknowledgedSave=usable&&!!saved&&sameEncounterScope(scope,saved.scope)&&saved.saved.world_id===record!.world_id&&saved.saved.encounter_id===record!.encounter_id&&saved.saved.revision===record!.revision&&saved.saved.revision===saved.before.revision+1&&combatDraftEqual(saved.saved.draft,record!.draft);
 const acknowledgedCreation=acknowledgedOperation===view?.binding.operation_id;
 const failure=error??roster?.error;
 useTourOwnerReading({step:'encounter',dispatchScope:acknowledgedSave?saved!.dispatchScope:dispatchScope,target,control:'encounter',status:failure?'failed':usable?'ready':'unavailable',
  reason:failure??(usable?undefined:pending?'Resolve pending scene preparation before continuing.':'Open the intended scene and a clean saved Plan, verify its exact version with Start Play, and finish encounter saves or recovery.'),
  ...(usable&&target&&view&&version?{observation:{step:'encounter',target,observedAt:acknowledgedSave?saved!.saved.updated_at:version.saved_at,origin:acknowledgedSave||acknowledgedCreation?'acknowledged':'existing',receiptId:`encounter:${view.binding.operation_id}:${version.revision}:${version.digest}`,
   proof:{kind:'encounter',sceneId:context.sceneId,encounterId:view.binding.encounter_id,revision:version.revision,digest:version.digest,operationId:view.binding.operation_id}}}:{})});
 return null;
}

export function PlayTourObservation({run,blocked,error}:{run:WorldPlayRunRecordV2|null;blocked:boolean;error:string|null}){
 const pins=run?runPins(run):null;
 useTourOwnerReading({step:'play',target:pins?.target??null,...(pins?{parent:pins.parent}:{}),control:'start-play',status:error?'failed':run&&!blocked?'ready':'unavailable',reason:error??(run&&!blocked?undefined:'Open the exact saved Run through Play. Resolve pending session edits and recovery before inspecting its saved state.'),
  ...(run&&pins&&!blocked&&!error?{observation:{step:'play',target:pins.target,parent:pins.parent,observedAt:run.updated_at,origin:'existing',receiptId:`run:${run.run_id}:${run.run_revision}:${run.playable_work_revision_id}`}}:{})});
 return null;
}
