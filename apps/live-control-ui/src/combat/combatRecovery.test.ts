import {beforeEach,afterEach,expect,it,vi} from 'vitest';
import {CombatRecoverySession,combatRecoveryKey,combatDraftEqual} from './combatRecovery';
import type {CombatEncounterRecord} from './combatTypes';
import {testCombatLocks} from './combatRecovery.testSupport';
const record={world_id:'elderwyld',encounter_id:'fight-one',revision:1,ruleset:{fields:[]},
  draft:{schema:'dmb_combat_encounter_draft_v1',title:'Fight',round:1,queue_model:'circular_barrel_v1',entities:[],groups:[],provenance:[],active_turn_entity_id:null,round_start_entity_id:null}} as unknown as CombatEncounterRecord;
const sessions:CombatRecoverySession[]=[];
const session=()=>{const next=new CombatRecoverySession();sessions.push(next);return next;};
beforeEach(()=>{localStorage.clear();Object.defineProperty(navigator,'locks',{configurable:true,value:testCombatLocks()});});
afterEach(()=>{sessions.splice(0).forEach(s=>s.close());vi.restoreAllMocks();});
it('retains exact base and unsaved draft across editor close/reopen',async()=>{
  const first=session();await first.open(record,()=>true);const draft={...record.draft,title:'Unsaved'};first.write(record,draft);first.close();
  const reopened=await session().open(record,()=>true);expect(reopened.recovery?.draft).toEqual(draft);expect(reopened.recovery?.base.revision).toBe(1);
});
it('prevents a second same-origin editor while allowing the same ID in a different World',async()=>{
  await session().open(record,()=>true);await expect(session().open(record,()=>true)).rejects.toThrow('another view');
  await expect(session().open({...record,world_id:'other'},()=>true)).resolves.toMatchObject({recovery:null});
});
it('reconciles an exact lost Save without reposting and preserves later edits on the new base',async()=>{
  const first=session();await first.open(record,()=>true);
  const submitted={...record.draft,title:'Submitted'};const later={...submitted,title:'Later local delta'};
  first.write(record,later,{expected_revision:1,draft:submitted});first.close();
  const result=await session().open({...record,revision:2,draft:submitted},()=>true);
  expect(result.committedMatch).toBe(true);expect(result.recovery).toMatchObject({base:{revision:2},draft:later,pending:null});
});
it('clears only the exactly matched submitted state',async()=>{
  const first=session();await first.open(record,()=>true);const submitted={...record.draft,title:'Submitted'};
  first.write(record,submitted,{expected_revision:1,draft:submitted});first.close();
  const result=await session().open({...record,revision:2,draft:submitted},()=>true);
  expect(result).toEqual({recovery:null,committedMatch:true});expect(localStorage.getItem(combatRecoveryKey('elderwyld','fight-one'))).toBeNull();
});
it.each([2,3])('preserves uncertain writes when the latest revision %s is not the exact submitted commit',async revision=>{
  const first=session();await first.open(record,()=>true);first.write(record,record.draft,{expected_revision:1,draft:record.draft});first.close();
  const result=await session().open({...record,revision,draft:{...record.draft,title:'Another client'}},()=>true);
  expect(result.committedMatch).toBe(false);expect(result.recovery?.pending?.expected_revision).toBe(1);
});
it('refuses foreign or corrupt recovery without deleting it',async()=>{
  const key=combatRecoveryKey('elderwyld','fight-one');const raw=JSON.stringify({schema:'dmb_combat_recovery_v1',base:{...record,world_id:'other'},draft:record.draft,pending:null});
  localStorage.setItem(key,raw);await expect(session().open(record,()=>true)).rejects.toThrow('different encounter');expect(localStorage.getItem(key)).toBe(raw);
});
it('refuses ownership changes and unavailable storage without losing the earlier draft',async()=>{
  const first=session();await first.open(record,()=>true);first.write(record,record.draft);
  const key=combatRecoveryKey('elderwyld','fight-one');localStorage.setItem(key,'foreign replacement');
  expect(()=>first.write(record,{...record.draft,title:'Late'})).toThrow('changed');expect(()=>first.clear()).toThrow('changed');expect(localStorage.getItem(key)).toBe('foreign replacement');
});
it('fails closed when Web Locks are unavailable',async()=>{
  Object.defineProperty(navigator,'locks',{configurable:true,value:undefined});await expect(session().open(record,()=>true)).rejects.toThrow('cannot safely retain');
});
it('checks lifetime after acquisition and releases a stale admission',async()=>{
  let current=true;const first=session();const opening=first.open(record,()=>current);current=false;
  await expect(opening).rejects.toThrow('view changed');await expect(session().open(record,()=>true)).resolves.toMatchObject({recovery:null});
});
it('compares JSON object content independently of transport key order',()=>{
  expect(combatDraftEqual({one:1,two:{a:2,b:3}},{two:{b:3,a:2},one:1})).toBe(true);
});
