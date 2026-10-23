import {beforeEach,afterEach,expect,it,vi} from 'vitest';
import {CombatRecoverySession,combatRecoveryKey,combatDraftEqual} from './combatRecovery';
import type {CombatEncounterRecord} from './combatTypes';
import {testCombatLocks} from './combatRecovery.testSupport';
const record={world_id:'elderwyld',encounter_id:'3f620410-21cb-4d18-88d4-5ea5e60b0b14',revision:1,campaign_id:null,session:null,created_at:'2026-10-22T00:00:00Z',updated_at:'2026-10-22T00:00:00Z',ruleset_digest:'a'.repeat(64),ruleset:{schema:'dmb_combat_ruleset_v1',config_id:'generic.manual-tracking',system_id:'generic',edition_id:'manual',revision:'1',mode:'manual_tracking',fields:[],manual_defaults:{}},
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
  expect(result).toEqual({recovery:null,committedMatch:true});expect(localStorage.getItem(combatRecoveryKey('elderwyld','3f620410-21cb-4d18-88d4-5ea5e60b0b14'))).toBeNull();
});
it.each([2,3])('preserves uncertain writes when the latest revision %s is not the exact submitted commit',async revision=>{
  const first=session();await first.open(record,()=>true);first.write(record,record.draft,{expected_revision:1,draft:record.draft});first.close();
  const result=await session().open({...record,revision,draft:{...record.draft,title:'Another client'}},()=>true);
  expect(result.committedMatch).toBe(false);expect(result.recovery?.pending?.expected_revision).toBe(1);
});
it('refuses foreign or corrupt recovery without deleting it',async()=>{
  const key=combatRecoveryKey('elderwyld','3f620410-21cb-4d18-88d4-5ea5e60b0b14');const raw=JSON.stringify({schema:'dmb_combat_recovery_v1',base:{...record,world_id:'other'},draft:record.draft,pending:null});
  localStorage.setItem(key,raw);await expect(session().open(record,()=>true)).rejects.toThrow('different encounter');expect(localStorage.getItem(key)).toBe(raw);
});
it('refuses ownership changes and unavailable storage without losing the earlier draft',async()=>{
  const first=session();await first.open(record,()=>true);first.write(record,record.draft);
  const key=combatRecoveryKey('elderwyld','3f620410-21cb-4d18-88d4-5ea5e60b0b14');localStorage.setItem(key,'foreign replacement');
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

it('refuses malformed nested mechanics and keeps the original bytes',async()=>{
  const key=combatRecoveryKey(record.world_id,record.encounter_id);
  const entity={id:'actor',name:'Keeper',team:'enemy',order:1,init:null,ac:null,hp:null,max_hp:null,temp_hp:0,defeated:false,notes:'',conditions:[],tags:[],statblock_path:null,statblock_artifact_id:null,statblock_title:null,corpus_fingerprint:null,source:'manual',world_identity:null,provenance:[],mechanics_snapshot:{}};
  const raw=JSON.stringify({schema:'dmb_combat_recovery_v1',base:record,draft:{...record.draft,entities:[entity]},pending:null});localStorage.setItem(key,raw);
  await expect(session().open(record,()=>true)).rejects.toThrow('invalid');expect(localStorage.getItem(key)).toBe(raw);
});
it('rejects omitted defaulted fields used directly by the renderer',async()=>{
  const key=combatRecoveryKey(record.world_id,record.encounter_id);const draft={...record.draft} as Partial<typeof record.draft>;delete draft.groups;
  const raw=JSON.stringify({schema:'dmb_combat_recovery_v1',base:record,draft,pending:null});localStorage.setItem(key,raw);
  await expect(session().open(record,()=>true)).rejects.toThrow('invalid');expect(localStorage.getItem(key)).toBe(raw);
});

/** Hold the actual lock-request completion after its callback has returned. */
function delayedOwnRelease() {
  let finish!: () => void;
  const gate = new Promise<void>(resolve => { finish = resolve; });
  let held = false;
  let calls = 0;
  const manager = {request: async (name: string, _options: unknown, callback: (lock: Lock | null) => unknown) => {
    const call = ++calls;
    if (held) return callback(null);
    held = true;
    try { return await callback({name,mode:'exclusive'} as Lock); }
    finally { if (call === 1) await gate; held = false; }
  }} as unknown as LockManager;
  Object.defineProperty(navigator,'locks',{configurable:true,value:manager});
  return {finish, calls:()=>calls};
}

it('waits for its own lock-request release before reopening the same encounter',async()=>{
  const locks=delayedOwnRelease(),owner=session();
  await owner.open(record,()=>true);
  owner.write(record,{...record.draft,title:'Keep local work'});
  const reopening=owner.open(record,()=>true);
  await Promise.resolve();await Promise.resolve();
  expect(locks.calls()).toBe(1);
  locks.finish();
  const result=await reopening;
  expect(locks.calls()).toBe(2);
  expect(result.recovery?.draft.title).toBe('Keep local work');
  await expect(session().open(record,()=>true)).rejects.toThrow('another view');
});

it.each(['close','stale'] as const)('refuses late reacquisition after %s while its prior release is pending',async(mode)=>{
  const locks=delayedOwnRelease(),owner=session();let current=true;
  await owner.open(record,()=>true);
  owner.write(record,{...record.draft,title:'Retained before cancellation'});
  const key=combatRecoveryKey(record.world_id,record.encounter_id),raw=localStorage.getItem(key);
  const reopening=owner.open(record,()=>current);
  if(mode==='close')owner.close();else current=false;
  locks.finish();
  await expect(reopening).rejects.toThrow('view changed');
  expect(locks.calls()).toBe(1);expect(localStorage.getItem(key)).toBe(raw);
  const next=await session().open(record,()=>true);
  expect(next.recovery?.draft.title).toBe('Retained before cancellation');
});
it('scoped scene editors preserve the standalone World chooser selection',async()=>{
 localStorage.setItem('dmb.combat.selected:elderwyld','standalone-fight');
 const scoped=session();await scoped.open(record,()=>true,false);scoped.write(record,{...record.draft,title:'Scoped draft'});scoped.close();
 expect(localStorage.getItem('dmb.combat.selected:elderwyld')).toBe('standalone-fight');
 const restored=await session().open(record,()=>true,false);expect(restored.recovery?.draft.title).toBe('Scoped draft');
});
