import {afterEach,expect,it,vi} from 'vitest';
import {setNativeGraphAccessToken} from '../api/liveApi';
import {listCombatMechanicsAdoptions,inspectCombatMechanicsAdoption} from './combatApi';
import {verifyInspectedAdoption} from './CombatMechanicsAdoptionRecovery';
import type {MechanicsAdoptionOutcome} from './combatTypes';
const op='11111111-1111-4111-8111-111111111111';
const receipt:MechanicsAdoptionOutcome['receipt']={schema:'dmb_combat_mechanics_adoption_receipt_v1',world_id:'world',encounter_id:'encounter',operation_id:op,request_digest:'sha256:'+'a'.repeat(64),state:'applied',expected_revision:1,committed_revision:2,created_at:'2026-10-28T00:00:00Z',source:{provider:'dungeonmind',statblock_id:'creature',revision_id:'exact',contract:'contract',contract_version:'1',definition_digest:'sha256:'+'b'.repeat(64)},transitions:[{actor_id:'actor',before_snapshot_digest:'sha256:'+'c'.repeat(64),after_snapshot_digest:'sha256:'+'d'.repeat(64),ac_policy:'keep',hp_policy:'clamp_current',before_ac:12,after_ac:12,before_hp:30,after_hp:20,before_max_hp:30,after_max_hp:20}]};
const page=()=>({schema:'dmb_combat_mechanics_adoption_history_v1',world_id:'world',encounter_id:'encounter',receipts:[structuredClone(receipt)],next_before_operation_id:null});
afterEach(()=>{vi.restoreAllMocks();setNativeGraphAccessToken(null);});
it('uses authenticated GETs and preserves complete Run/scene scope for history and inspection',async()=>{
 setNativeGraphAccessToken('synthetic-local-credential');
 const fetch=vi.spyOn(globalThis,'fetch').mockResolvedValueOnce(Response.json(page())).mockResolvedValueOnce(Response.json(null));
 const scope={runId:'run',sceneId:'scene:gate'};
 await listCombatMechanicsAdoptions('world','encounter',null,scope);await inspectCombatMechanicsAdoption('world','encounter',op,scope);
 expect(String(fetch.mock.calls[0][0])).toBe('/api/live/combat/run-encounters/run/scenes/scene%3Agate/encounters/encounter/mechanics-adoptions?world_id=world');
 expect(String(fetch.mock.calls[1][0])).toContain(`/mechanics-adoptions/${op}?world_id=world`);
 for(const [,init] of fetch.mock.calls){expect(init?.headers).toMatchObject({Authorization:'Bearer synthetic-local-credential'});expect(init?.method??'GET').toBe('GET');expect(init?.body).toBeUndefined();}
});
it.each(['scope','extra','duplicate','cursor','policy','revision','state'])('rejects malformed or foreign history at the API boundary: %s',async damage=>{
 const value=page();
 if(damage==='scope')value.encounter_id='other';
 if(damage==='extra')Object.assign(value.receipts[0],{unverified:true});
 if(damage==='duplicate')value.receipts.push(value.receipts[0]);
 if(damage==='cursor')Object.assign(value,{next_before_operation_id:'unknown'});
 if(damage==='policy')Object.assign(value.receipts[0].transitions[0],{hp_policy:'invented'});
 if(damage==='revision')value.receipts[0].committed_revision=100;
 if(damage==='state')Object.assign(value.receipts[0],{state:'canceled'});
 vi.spyOn(globalThis,'fetch').mockResolvedValueOnce(Response.json(value));
 await expect(listCombatMechanicsAdoptions('world','encounter')).rejects.toThrow();
});
it('opens an advanced historical receipt with a removed actor, but requires exact state at the committed revision',()=>{
 const result={receipt,encounter:{world_id:'world',encounter_id:'encounter',revision:3,draft:{entities:[]}},advanced_since_apply:true} as unknown as MechanicsAdoptionOutcome;
 expect(()=>verifyInspectedAdoption(receipt,result)).not.toThrow();
 expect(()=>verifyInspectedAdoption(receipt,{...result,encounter:{...result.encounter,revision:2},advanced_since_apply:false})).toThrow('committed receipt');
 expect(()=>verifyInspectedAdoption(receipt,{...result,advanced_since_apply:false})).toThrow('selected receipt');
});
