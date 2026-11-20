import {samePin,sameMechanicsPin,validGeneratedMechanicsEvidence,type GeneratedMechanicsScope,type GeneratedMechanicsEvidence} from './protocol';
import type {TourOwnerReading} from './GuidedTour';
import type {OpenSavedMechanicsVersion,RevisionSaveOutcome,SavedMechanicsVersionList,SavedMechanicsLocator} from '../statblocks/revision/savedMechanicsRevisionTypes';
import type {MechanicsAdoptionOutcome} from '../combat/combatTypes';
import {useTourOwnerReading,type TourDispatchScope} from './GuidedTour';
import {sameEncounterScope,type TourEncounterScope} from './EncounterScope';
export const sameMechanicsLocator=(a:SavedMechanicsLocator,b:SavedMechanicsLocator)=>a.provider===b.provider&&a.statblock_id===b.statblock_id&&a.revision_id===b.revision_id&&a.contract===b.contract&&a.contract_version===b.contract_version&&a.definition_digest===b.definition_digest;
export interface AcknowledgedMechanicsSave {dispatchScope?:TourDispatchScope|null;scope:TourEncounterScope;draftId:string;operation:RevisionSaveOutcome}
export interface AcknowledgedMechanicsAdoption {dispatchScope?:TourDispatchScope|null;scope:TourEncounterScope;outcome:MechanicsAdoptionOutcome}
export function MechanicsTourObservation({scope,opened,history,acknowledged,blocked}:{scope:TourEncounterScope|null;opened:OpenSavedMechanicsVersion|null;history:SavedMechanicsVersionList|null;acknowledged:AcknowledgedMechanicsSave|null;blocked:boolean}){
 const fresh=!!acknowledged&&!!opened&&acknowledged.draftId===opened.draft_id&&!!acknowledged.operation.result&&sameMechanicsLocator(acknowledged.operation.result,opened.locator)&&sameEncounterScope(scope,acknowledged.scope);
 const operation=fresh?acknowledged.operation:history?.world_id===opened?.world_id&&history?.draft_id===opened?.draft_id?history?.operations.find(op=>op.state==='committed'&&!!op.result&&!!opened&&sameMechanicsLocator(op.result,opened.locator)):undefined;
 const usable=!!scope&&!!opened&&!blocked&&opened.world_id===scope.plan.worldId&&operation?.state==='committed'&&!!operation.result&&operation.result.revision_id!==operation.base.revision_id&&sameMechanicsLocator(operation.result,opened.locator);
 useTourOwnerReading(scope?{step:'mechanics',dispatchScope:acknowledged?.dispatchScope,target:scope.plan,control:'mechanics',status:usable?'ready':'unavailable',reason:usable?undefined:'Open this encounter’s saved creature, edit and validate its mechanics, then Save a new immutable version. Finish or recover pending edits before inspecting the result.',
  ...(usable&&operation?{observation:{step:'mechanics',target:scope.plan,origin:fresh?'acknowledged':'existing',observedAt:operation.created_at,receiptId:`mechanics:${operation.operation_id}:${opened.locator.revision_id}`,proof:{kind:'mechanics',sceneId:scope.sceneId,encounterId:scope.encounterId,draftId:opened.draft_id,operationId:operation.operation_id,locator:opened.locator}}}:{})}:null);
 return null;
}
/** Command outcomes and historical inspections are verified at their distinct owner boundaries. */
export function AdoptionTourObservation({scope,worldId,encounterId,acknowledged,inspected=null,blocked}:{scope:TourEncounterScope|null;worldId:string;encounterId:string;acknowledged:AcknowledgedMechanicsAdoption|null;inspected?:AcknowledgedMechanicsAdoption|null;blocked:boolean}){
 const scoped=!!scope&&scope.plan.worldId===worldId&&scope.encounterId===encounterId;
 const selected=inspected&&sameEncounterScope(scope,inspected.scope)?inspected:acknowledged;
 const receipt=selected?.outcome.receipt;
 const usable=scoped&&!blocked&&!!selected&&sameEncounterScope(scope,selected.scope)&&receipt?.state==='applied'&&receipt.world_id===worldId&&receipt.encounter_id===encounterId&&receipt.committed_revision!==null;
 useTourOwnerReading(scoped?{step:'adoption',dispatchScope:acknowledged?.dispatchScope,target:scope.plan,control:'adoption',status:usable?'ready':'unavailable',reason:usable?undefined:blocked?'Recover the retained adoption or finish encounter edits through the ordinary controls.':'Preview the exact saved version, choose actors and tracker policies, then explicitly use that version. An applied receipt is required.',
  ...(usable?{observation:{step:'adoption',target:scope.plan,origin:selected===acknowledged?'acknowledged':'existing',observedAt:receipt.created_at,receiptId:`adoption:${receipt.operation_id}:${receipt.committed_revision}`,proof:{kind:'adoption',sceneId:scope.sceneId,encounterId,operationId:receipt.operation_id,encounterRevision:receipt.committed_revision!,locator:receipt.source,actors:receipt.transitions.map(t=>({actorId:t.actor_id,beforeDigest:t.before_snapshot_digest,afterDigest:t.after_snapshot_digest,acPolicy:t.ac_policy,hpPolicy:t.hp_policy}))}}}:{})}:null);
 return null;
}

export interface AcknowledgedGeneratedMechanicsSave {scope:GeneratedMechanicsScope;dispatchScope:TourDispatchScope|null;operation:RevisionSaveOutcome}
export const sameGeneratedMechanicsScope=(a:GeneratedMechanicsScope|null,b:GeneratedMechanicsScope|null)=>!!a&&!!b&&a.walkthroughId===b.walkthroughId&&a.draftId===b.draftId&&a.acceptOperationId===b.acceptOperationId&&a.dispatchRevision===b.dispatchRevision&&samePin(a.plan,b.plan)&&sameMechanicsPin(a.original,b.original);
export function generatedMechanicsReading(scope:GeneratedMechanicsScope|null,opened:OpenSavedMechanicsVersion|null,history:SavedMechanicsVersionList|null,acknowledged:AcknowledgedGeneratedMechanicsSave|null,blocked:boolean):TourOwnerReading|null {
 if(!scope)return null;
 const fresh=sameGeneratedMechanicsScope(scope,acknowledged?.scope??null);
 const operations=[...(history?.operations??[]),...(fresh&&acknowledged?[acknowledged.operation]:[])];
 const lineage:GeneratedMechanicsEvidence['lineage']=[];let at=opened?.locator;const seen=new Set<string>();
 if(opened&&history&&opened.world_id===scope.plan.worldId&&opened.draft_id===scope.draftId&&history.world_id===opened.world_id&&history.draft_id===opened.draft_id&&sameMechanicsPin(history.original,scope.original)){
  while(at&&!sameMechanicsPin(at,scope.original)&&!seen.has(at.revision_id)){
   seen.add(at.revision_id);
   const matches=operations.filter(op=>op.state==='committed'&&op.result&&sameMechanicsPin(op.result,at!));
   const op=matches[0];if(!op||matches.some(other=>other.operation_id!==op.operation_id||!sameMechanicsPin(other.base,op.base)))break;
   lineage.unshift({operationId:op.operation_id,base:op.base,locator:op.result!});at=op.base;
  }
 }
 const proof:GeneratedMechanicsEvidence={kind:'generated-mechanics-revision',scope,lineage};
 const ready=!blocked&&!history?.pending&&!!opened&&!!at&&sameMechanicsPin(at,scope.original)&&validGeneratedMechanicsEvidence(proof,scope.plan.worldId);
 const last=lineage.at(-1),operation=last?operations.find(op=>op.operation_id===last.operationId):null;
 const isFresh=fresh&&!!last&&acknowledged?.operation.operation_id===last.operationId;
 return {step:'mechanics',target:scope.plan,control:'mechanics',status:ready?'ready':'unavailable',reason:ready?undefined:'Open the generated creature’s saved mechanics and a verified manual successor. Finish or recover pending edits first.',dispatchScope:isFresh?acknowledged?.dispatchScope:null,
  ...(ready&&last&&operation?{observation:{step:'mechanics',target:scope.plan,origin:isFresh?'acknowledged':'existing',observedAt:operation.created_at,receiptId:`mechanics:${operation.operation_id}:${last.locator.revision_id}`,proof}}:{})};
}
export function GeneratedMechanicsTourObservation(props:{scope:GeneratedMechanicsScope|null;opened:OpenSavedMechanicsVersion|null;history:SavedMechanicsVersionList|null;acknowledged:AcknowledgedGeneratedMechanicsSave|null;blocked:boolean}){useTourOwnerReading(generatedMechanicsReading(props.scope,props.opened,props.history,props.acknowledged,props.blocked));return null;}
