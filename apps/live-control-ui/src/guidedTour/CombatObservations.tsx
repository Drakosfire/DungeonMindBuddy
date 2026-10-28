import type {CombatEncounterRecord} from '../combat/combatTypes';
import type {RunEncounterScope} from '../combat/runEncountersApi';
import {useTourOwnerReading} from './GuidedTour';
import {samePin} from './protocol';
import {useTourRun,type TourRunScope} from './RunScope';
export interface AcknowledgedCombatSave {scope:TourRunScope;sceneId:string;before:CombatEncounterRecord;saved:CombatEncounterRecord}
const fields=['hp','max_hp','temp_hp','ac','conditions','defeated','init'] as const;
/** Actor/turn changes are recognized only after the tracker owner verifies its Save. */
export function CombatTourObservation({record,runScope,acknowledged,blocked,error}:{record:CombatEncounterRecord|null;runScope:RunEncounterScope|null;acknowledged:AcknowledgedCombatSave|null;blocked:boolean;error:string|null}){
 const current=useTourRun();
 const scoped=!!current&&!!runScope&&current.target.objectId===runScope.runId&&!!record&&current.target.worldId===record.world_id;
 const matching=scoped&&!!acknowledged&&acknowledged.scope.target.objectId===current.target.objectId&&samePin(acknowledged.scope.parent,current.parent)&&acknowledged.sceneId===runScope.sceneId&&acknowledged.saved.world_id===record.world_id&&acknowledged.saved.encounter_id===record.encounter_id&&acknowledged.saved.revision===record.revision;
 const actors=matching?acknowledged.saved.draft.entities.flatMap(actor=>{
  const before=acknowledged.before.draft.entities.find(item=>item.id===actor.id);
  const changed=before?fields.filter(field=>JSON.stringify(before[field])!==JSON.stringify(actor[field])):[];
  return changed.length?[{actorId:actor.id,fields:changed}]:[];
 }):[];
 const roundChanged=!!matching&&acknowledged.before.draft.round!==acknowledged.saved.draft.round;
 const activeTurnChanged=!!matching&&acknowledged.before.draft.active_turn_entity_id!==acknowledged.saved.draft.active_turn_entity_id;
 const usable=matching&&!blocked&&!error&&(actors.length>0||roundChanged||activeTurnChanged);
 useTourOwnerReading(scoped?{step:'combat',target:current.target,parent:current.parent,control:'combat',status:error?'failed':usable?'ready':'unavailable',reason:error??(usable?undefined:'Open this Run’s scene encounter, make a manual tracker or turn change, then Save. Draft edits and roster-only changes do not demonstrate saved combat tracking.'),
  ...(usable?{observation:{step:'combat',target:acknowledged.scope.target,parent:acknowledged.scope.parent,origin:'acknowledged',observedAt:acknowledged.saved.updated_at,receiptId:`combat:${record.encounter_id}:${record.revision}`,proof:{kind:'combat-tracker',sceneId:runScope.sceneId,encounterId:record.encounter_id,baseRevision:acknowledged.before.revision,savedRevision:record.revision,roundChanged,activeTurnChanged,actors}}}:{})}:null);
 return null;
}
