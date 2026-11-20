import type {AdoptMechanicsRequest,MechanicsAdoptionOutcome} from './combatTypes';
export interface PendingMechanicsAdoption {schema:'dmb_pending_combat_adoption_v1';worldId:string;encounterId:string;request:AdoptMechanicsRequest;afterDigest:string}
function ordered(value:unknown):unknown {
  if(Array.isArray(value))return value.map(ordered);
  if(value&&typeof value==='object')return Object.fromEntries(Object.keys(value).sort().map(key=>[key,ordered((value as Record<string,unknown>)[key])]));
  return value;
}
export const sameAdoptionValue=(a:unknown,b:unknown)=>JSON.stringify(ordered(a))===JSON.stringify(ordered(b));
const object=(v:unknown):v is Record<string,unknown>=>typeof v==='object'&&v!==null&&!Array.isArray(v);
const exact=(v:unknown,keys:string[]):v is Record<string,unknown>=>object(v)&&Object.keys(v).length===keys.length&&keys.every(k=>k in v);
const text=(v:unknown):v is string=>typeof v==='string'&&!!v.trim();
const digest=(v:unknown)=>typeof v==='string'&&/^sha256:[0-9a-f]{64}$/.test(v);
const tracked=(v:unknown)=>v===null||typeof v==='string'||typeof v==='number'&&Number.isFinite(v);
/** Validate an authoritative retained receipt, without claiming to reprove its original request. */
export function verifyHistoricalAdoptionReceipt(value:unknown,worldId:string,encounterId:string):asserts value is MechanicsAdoptionOutcome['receipt'] {
 const r=value;
 if(!exact(r,['schema','operation_id','world_id','encounter_id','request_digest','state','source','expected_revision','committed_revision','transitions','created_at'])
  ||r.schema!=='dmb_combat_mechanics_adoption_receipt_v1'||!text(r.operation_id)||r.world_id!==worldId||r.encounter_id!==encounterId||!digest(r.request_digest)
  ||!text(r.created_at)||!Number.isFinite(Date.parse(r.created_at))||!Number.isSafeInteger(r.expected_revision)||Number(r.expected_revision)<1
  ||!exact(r.source,['provider','statblock_id','revision_id','contract','contract_version','definition_digest'])||r.source.provider!=='dungeonmind'
  ||!['statblock_id','revision_id','contract','contract_version'].every(k=>text((r.source as Record<string,unknown>)[k]))||!digest(r.source.definition_digest)
  ||!Array.isArray(r.transitions)||!r.transitions.every(t=>exact(t,['actor_id','before_snapshot_digest','after_snapshot_digest','ac_policy','hp_policy','before_ac','after_ac','before_hp','after_hp','before_max_hp','after_max_hp'])
   &&text(t.actor_id)&&digest(t.before_snapshot_digest)&&digest(t.after_snapshot_digest)&&['keep','use_saved'].includes(String(t.ac_policy))
   &&['keep','preserve_current','clamp_current','reset_full'].includes(String(t.hp_policy))&&['before_ac','after_ac','before_hp','after_hp','before_max_hp','after_max_hp'].every(k=>tracked(t[k])))
  ||new Set(r.transitions.map(t=>t.actor_id)).size!==r.transitions.length
  ||!(r.state==='applied'?r.committed_revision===Number(r.expected_revision)+1&&r.transitions.length>0:r.state==='canceled'&&r.committed_revision===null&&r.transitions.length===0))
  throw new Error('Saved adoption receipt cannot be verified.');
}
export function verifyInspectedAdoption(expected:MechanicsAdoptionOutcome['receipt'],outcome:MechanicsAdoptionOutcome):void {
 verifyHistoricalAdoptionReceipt(outcome?.receipt,expected.world_id,expected.encounter_id);
 const {receipt,encounter}=outcome;
 if(!sameAdoptionValue(receipt,expected)||!encounter||encounter.world_id!==expected.world_id||encounter.encounter_id!==expected.encounter_id
  ||!Number.isSafeInteger(encounter.revision)||encounter.revision<1||typeof outcome.advanced_since_apply!=='boolean'
  ||(receipt.state==='applied'?(encounter.revision<receipt.committed_revision!||outcome.advanced_since_apply!==(encounter.revision>receipt.committed_revision!)):outcome.advanced_since_apply))
  throw new Error('Saved adoption inspection differs from the selected receipt.');
 if(receipt.state==='applied'&&!outcome.advanced_since_apply){
  for(const change of receipt.transitions){
   const actor=encounter.draft?.entities?.find(e=>e.id===change.actor_id);
   if(!actor||actor.mechanics_snapshot?.snapshot_digest!==change.after_snapshot_digest||!sameAdoptionValue(actor.mechanics_snapshot.locator,receipt.source)
    ||actor.ac!==change.after_ac||actor.hp!==change.after_hp||actor.max_hp!==change.after_max_hp)
    throw new Error('Saved adoption encounter does not match its committed receipt.');
  }
 }
}
export async function adoptionRequestDigest(pending:PendingMechanicsAdoption):Promise<string> {
  const body={world_id:pending.worldId,encounter_id:pending.encounterId,request:pending.request};
  const bytes=await crypto.subtle.digest('SHA-256',new TextEncoder().encode(JSON.stringify(ordered(body))));
  return 'sha256:'+Array.from(new Uint8Array(bytes),byte=>byte.toString(16).padStart(2,'0')).join('');
}
export async function verifyAdoptionOutcome(pending:PendingMechanicsAdoption,outcome:MechanicsAdoptionOutcome) {
  const {receipt,encounter}=outcome,request=pending.request;
  if(receipt.schema!=='dmb_combat_mechanics_adoption_receipt_v1'||receipt.operation_id!==request.operation_id
    ||receipt.world_id!==pending.worldId||receipt.encounter_id!==pending.encounterId
    ||encounter.world_id!==pending.worldId||encounter.encounter_id!==pending.encounterId
    ||receipt.request_digest!==await adoptionRequestDigest(pending)||receipt.expected_revision!==request.expected_revision
    ||!sameAdoptionValue(receipt.source,request.locator))throw new Error('Adoption acknowledgment differs from the retained request. Recover its original outcome.');
  if(receipt.state==='canceled'){
    if(receipt.committed_revision!==null||receipt.transitions.length||outcome.advanced_since_apply)throw new Error('Cancellation acknowledgment claims actor changes.');
    return;
  }
  if(receipt.state!=='applied'||receipt.committed_revision!==request.expected_revision+1||encounter.revision<receipt.committed_revision
    ||outcome.advanced_since_apply!==(encounter.revision>receipt.committed_revision)||receipt.transitions.length!==request.actors.length)
    throw new Error('Adoption revision acknowledgment is invalid.');
  if(new Set(receipt.transitions.map(t=>t.actor_id)).size!==receipt.transitions.length)throw new Error('Adoption repeats an actor.');
  for(const choice of request.actors){
    const change=receipt.transitions.find(t=>t.actor_id===choice.actor_id);
    if(!change||change.before_snapshot_digest!==choice.expected_snapshot_digest||change.after_snapshot_digest!==pending.afterDigest
      ||change.ac_policy!==choice.ac_policy||change.hp_policy!==choice.hp_policy)throw new Error('Adoption actor acknowledgment is invalid.');
    if(!outcome.advanced_since_apply){
      const actor=encounter.draft.entities.find(e=>e.id===choice.actor_id);
      if(!actor||actor.mechanics_snapshot?.snapshot_digest!==change.after_snapshot_digest
        ||actor.ac!==change.after_ac||actor.hp!==change.after_hp||actor.max_hp!==change.after_max_hp)
        throw new Error('Adoption encounter does not match its receipt.');
    }
  }
}
export function readPendingAdoption(raw:string|null,worldId:string,encounterId:string):PendingMechanicsAdoption|null {
  if(!raw)return null;
  const parsed=JSON.parse(raw) as PendingMechanicsAdoption;
  if(parsed.schema!=='dmb_pending_combat_adoption_v1'||parsed.worldId!==worldId||parsed.encounterId!==encounterId
    ||parsed.request?.schema!=='dmb_combat_mechanics_adoption_request_v1'||!Array.isArray(parsed.request.actors)
    ||!parsed.request.actors.length||typeof parsed.request.operation_id!=='string'||typeof parsed.afterDigest!=='string')
    throw new Error('Pending adoption could not be verified; it remains retained in this browser.');
  return parsed;
}
