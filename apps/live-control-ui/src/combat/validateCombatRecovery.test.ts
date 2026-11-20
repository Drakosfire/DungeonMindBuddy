import {expect,it} from 'vitest';
import resource from '../../../../tests/fixtures/statblocks/v1/exact-revision-response.json';
import {isCombatRecoveryDraft,isCombatRecoveryRecord} from './validateCombatRecovery';
const target={managed_world_id:'elderwyld',native_world_id:'native-world',binding_version:1,graph_revision_id:'head',node_id:'keeper',label:'Keeper',kind:'npc',role:'npc',campaign_scope:null};
const actor={id:'actor',name:'Keeper',team:'enemy',order:1,init:null,ac:null,hp:null,max_hp:null,temp_hp:0,defeated:false,notes:'',conditions:[],tags:[],statblock_path:null,statblock_artifact_id:null,statblock_title:null,corpus_fingerprint:null,source:'manual',world_identity:target,provenance:[],mechanics_snapshot:{association_id:'3f620410-21cb-4d18-88d4-5ea5e60b0b14',association_version:1,target,locator:{provider:'dungeonmind',statblock_id:resource.statblock_id,revision_id:resource.revision_id,contract:resource.contract,contract_version:resource.contract_version,definition_digest:resource.definition_digest},resource,snapshot_digest:'sha256:'+'a'.repeat(64)}};
const draft={schema:'dmb_combat_encounter_draft_v1',title:'Fight',round:1,queue_model:'circular_barrel_v1',entities:[actor],groups:[],provenance:[],active_turn_entity_id:null,round_start_entity_id:null};
it('accepts the complete current exact resource shape inside a Combat draft',()=>{expect(isCombatRecoveryDraft(draft)).toBe(true);});
it.each(['resource','definition','abilities','rule','conditions','groups'])('refuses nested malformed %s before the renderer sees it',field=>{
  const invalid=structuredClone(draft);
  const snapshot=invalid.entities[0].mechanics_snapshot as unknown as Record<string,any>;
  if(field==='resource')snapshot.resource={};
  else if(field==='definition')snapshot.resource.definition={};
  else if(field==='abilities')snapshot.resource.definition.abilities.strength={};
  else if(field==='rule')snapshot.resource.definition.rule_elements[0].mechanic={kind:'attack',attack_bonus:{}};
  else if(field==='conditions')(invalid.entities[0] as unknown as Record<string,unknown>).conditions={};
  else (invalid as unknown as Record<string,unknown>).groups=[{group_key:'x',label:'x',statblock_path:null,member_ids:{},collapsed:false}];
  expect(isCombatRecoveryDraft(invalid)).toBe(false);
});
it('requires the complete serialized base rather than a partial input body',()=>{expect(isCombatRecoveryRecord({world_id:'elderwyld',draft})).toBe(false);});
it('accepts the direct accepted-mechanics origin without a fabricated World identity and rejects mixed origins',()=>{
  const direct={origin:'world_accepted_mechanics_v1',managed_world_id:'elderwyld',draft_id:'3f620410-21cb-4d18-88d4-5ea5e60b0b14',draft_version:2,
    acceptance_operation_id:'accepted-operation',acceptance_request_digest:'sha256:'+'a'.repeat(64),accepted_from_draft_version:1,accepted_from_candidate_id:'cand_fixture1',
    locator:actor.mechanics_snapshot.locator,resource,snapshot_digest:actor.mechanics_snapshot.snapshot_digest};
  const directDraft={...draft,entities:[{...actor,world_identity:null,mechanics_snapshot:direct}]};
  expect(isCombatRecoveryDraft(directDraft)).toBe(true);
  expect(isCombatRecoveryDraft({...directDraft,entities:[{...directDraft.entities[0],mechanics_snapshot:{...direct,association_id:'forged'}}]})).toBe(false);
  expect(isCombatRecoveryDraft({...directDraft,entities:[{...directDraft.entities[0],mechanics_snapshot:{...direct,resource:{}}}]})).toBe(false);
});
