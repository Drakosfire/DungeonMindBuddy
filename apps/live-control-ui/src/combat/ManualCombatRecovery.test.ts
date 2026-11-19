import {afterEach,beforeEach,expect,it} from 'vitest';
import {CombatRecoverySession,combatRecoveryKey} from './combatRecovery';
import {testCombatLocks} from './combatRecovery.testSupport';
import type {ManualCombatRecord} from './ManualCombatTypes';
import {manualCombatRecord as record,sideCombatRecord} from './ManualCombat.testSupport';
import {actManualParticipant,finishManualParticipant,passManualSide} from './ManualCombatState';
import {validManualDraft} from './validateCombatRecovery';


const sessions:CombatRecoverySession<ManualCombatRecord>[]=[];
function session(){const value=new CombatRecoverySession<ManualCombatRecord>();sessions.push(value);return value;}
beforeEach(()=>{localStorage.clear();Object.defineProperty(navigator,'locks',{configurable:true,value:testCombatLocks()});});
afterEach(()=>sessions.splice(0).forEach(value=>value.close()));

it('settles exact pending side intent while retaining a later explicit side pass',async()=>{
  const base=sideCombatRecord(),owner=session();await owner.open(base,()=>true);
  const submitted=finishManualParticipant(actManualParticipant(passManualSide(base.draft),base.draft.entities[0].id));
  const later=passManualSide(submitted);
  owner.write(base,later,{expected_revision:1,draft:submitted});owner.close();
  const opened=await session().open({...base,revision:2,draft:submitted},()=>true);
  expect(opened.committedMatch).toBe(true);
  expect(opened.recovery).toMatchObject({base:{revision:2},draft:later,pending:null});
});

it('retains and refuses raw side recovery whose actor marker belongs to another side',async()=>{
  const base=sideCombatRecord(),draft=passManualSide(base.draft);
  if(draft.turn.kind!=='side')throw new Error('fixture');
  draft.turn.acted_actor_ids=[base.draft.entities[1].id];
  const key=combatRecoveryKey(base.world_id,base.encounter_id),raw=JSON.stringify({schema:'dmb_combat_recovery_v1',base,draft,pending:null});
  localStorage.setItem(key,raw);
  await expect(session().open(base,()=>true)).rejects.toThrow('invalid');
  expect(localStorage.getItem(key)).toBe(raw);
});
it('reconciles an unknown manual Save while retaining later resource and note edits',async()=>{
  const base=record(),first=session();await first.open(base,()=>true);
  const submitted=structuredClone(base.draft);submitted.entities[0].participation='out_of_action';
  const later=structuredClone(submitted);later.entities[0].values.resources.stress.current=0;later.entities[0].notes='Retain after acknowledgement';
  first.write(base,later,{expected_revision:1,draft:submitted});first.close();
  const result=await session().open({...base,revision:2,draft:submitted},()=>true);
  expect(result.committedMatch).toBe(true);expect(result.recovery).toMatchObject({base:{revision:2},draft:later,pending:null});
});
it('refuses tampered profile labels even when the local digest string matches',async()=>{
  const base=record(),first=session();await first.open(base,()=>true);first.write(base,base.draft);first.close();
  const key=combatRecoveryKey(base.world_id,base.encounter_id),raw=JSON.parse(localStorage.getItem(key)!);
  raw.base.ruleset.stats[0].label='Untrusted replacement';const changed=JSON.stringify(raw);localStorage.setItem(key,changed);
  await expect(session().open(base,()=>true)).rejects.toThrow('invalid');expect(localStorage.getItem(key)).toBe(changed);
});
it('preserves raw recovery with a foreign field or malformed participation reference',async()=>{
  const base=record(),key=combatRecoveryKey(base.world_id,base.encounter_id);
  const draft=structuredClone(base.draft);draft.entities[0].values.stats.foreign='not declared';
  const raw=JSON.stringify({schema:'dmb_combat_recovery_v1',base,draft,pending:null});localStorage.setItem(key,raw);
  await expect(session().open(base,()=>true)).rejects.toThrow('invalid');expect(localStorage.getItem(key)).toBe(raw);
});

it('refuses a draft that fits individual fields but exceeds the complete canonical budget',()=>{
  const base=record(),actor=base.draft.entities[0];
  actor.notes='名'.repeat(4096);
  const draft={...base.draft,entities:Array.from({length:60},(_,index)=>({...actor,id:`crew-${index}`}))};
  expect(new TextEncoder().encode(JSON.stringify(draft)).byteLength).toBeGreaterThan(700*1024);
  expect(validManualDraft(base,draft)).toBe(false);
});
