import type {CombatEncounterRecord, CombatEntity, CombatMechanicsSnapshot, CombatWorldIdentity} from './combatTypes';

export interface ManualResource {current:number|null; minimum:number|null; maximum:number|null}
export interface ManualCombatProfile {
  schema:'dmb_combat_profile_v2'; profile_id:string; name:string; system_id:string; revision:number;
  stats:{field_id:string; label:string; value_type:'integer'|'text'; initial:number|string|null}[];
  resources:{field_id:string; label:string; initial:ManualResource}[];
  pacing:{mode:'ordered'; rounds:boolean}|{mode:'side'; rounds:false}|{mode:'spotlight'; rounds:false};
}
export interface ManualCombatActor {
  id:string; name:string; side_id:string|null; participation:'in_action'|'out_of_action';
  values:{stats:Record<string,number|string|null>; resources:Record<string,ManualResource>};
  notes:string; statuses:string[]; tags:string[];
  world_identity:CombatWorldIdentity|null; mechanics_snapshot:CombatMechanicsSnapshot|null;
  deleted_mechanics?: CombatEntity['deleted_mechanics'];
}
export type ManualTurn = {kind:'ordered'; active_actor_id:string|null} |
  {kind:'ordered_rounds'; active_actor_id:string|null; round:number; round_start_actor_id:string|null} |
  {kind:'side'; active_side_id:string|null; active_actor_id:string|null; acted_actor_ids:string[]}|{kind:'spotlight'; active_actor_id:string|null};
export interface ManualCombatDraft {
  schema:'dmb_combat_encounter_draft_v2'; title:string; entities:ManualCombatActor[];
  groups:{id:string; label:string; member_ids:string[]; collapsed:boolean}[];
  sides:{id:string; label:string}[]; turn:ManualTurn;
}
export interface ManualCombatRecord extends Omit<CombatEncounterRecord,'ruleset'|'draft'> {
  ruleset:ManualCombatProfile; draft:ManualCombatDraft;
}
export type AnyCombatRecord = CombatEncounterRecord | ManualCombatRecord;
export type AnyCombatDraft = CombatEncounterRecord['draft'] | ManualCombatDraft;
export const isManualCombatRecord = (record:AnyCombatRecord):record is ManualCombatRecord =>
  record.ruleset?.schema === 'dmb_combat_profile_v2' && record.draft?.schema === 'dmb_combat_encounter_draft_v2';
