import type {ManualCombatRecord} from './ManualCombatTypes';
import {newManualActor} from './ManualCombatState';

export function manualCombatRecord():ManualCombatRecord {
  const profile={schema:'dmb_combat_profile_v2' as const,profile_id:'crossing',name:'Crossing',system_id:'crossing',revision:1,
    stats:[{field_id:'position',label:'Position',value_type:'text' as const,initial:null}],
    resources:[{field_id:'stress',label:'Stress',initial:{current:2,minimum:0,maximum:6}}],pacing:{mode:'ordered' as const,rounds:false}};
  return {world_id:'crossing-world',encounter_id:'11111111-1111-4111-8111-111111111111',campaign_id:null,session:null,revision:1,
    created_at:'2026-11-18T00:00:00Z',updated_at:'2026-11-18T00:00:00Z',ruleset:profile,ruleset_digest:'a'.repeat(64),
    draft:{schema:'dmb_combat_encounter_draft_v2',title:'Crossing',entities:[newManualActor(profile,'Crew')],groups:[],sides:[],turn:{kind:'ordered',active_actor_id:null}}};
}

export function sideCombatRecord():ManualCombatRecord {
  const record=manualCombatRecord();
  record.ruleset.pacing={mode:'side',rounds:false};
  record.draft.sides=[{id:'crew',label:'Crew side'},{id:'river',label:'River'},{id:'watch',label:'Watch'}];
  record.draft.entities[0].side_id='crew';
  const watch=newManualActor(record.ruleset,'Watcher');watch.side_id='watch';record.draft.entities.push(watch);
  record.draft.turn={kind:'side',active_side_id:null,active_actor_id:null,acted_actor_ids:[]};
  return record;
}
