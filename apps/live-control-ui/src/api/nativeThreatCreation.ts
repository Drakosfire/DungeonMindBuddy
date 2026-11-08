/** Native publication packets are opaque signed server reviews, never client authority. */
export interface NativeThreatReview {
  schema:'dmb_native_threat_review_v1';world_id:string;draft_id:string;draft_version:number;label:string;
  body_sha256:string;binding:{managed_world_id:string;native_world_id:string;binding_version:number};
  publication_id:string;source_evidence_id:string;source_artifact_id:string;source_revision_id:string;
  prepared_digest:string;principal:string;expires_at:string;
}
export interface PreparedNativeThreat {state:'prepared';source_text:string;review:NativeThreatReview;prepared:Record<string,unknown>;token:string}
export interface PublishedNativeThreat {state:'published';world_id:string;draft_id:string;native_world_id:string;binding_version:number;node_id:string;publication_id:string;published_revision_id:string;replayed:boolean}
export type NativeThreatReply=PreparedNativeThreat|PublishedNativeThreat;
const record=(value:unknown):value is Record<string,unknown>=>!!value&&typeof value==='object'&&!Array.isArray(value);
const text=(value:unknown):value is string=>typeof value==='string'&&value.length>0;
const positive=(value:unknown)=>Number.isInteger(value)&&Number(value)>0;
const hex=(value:unknown)=>typeof value==='string'&&/^[a-f0-9]{64}$/.test(value);
export async function verifyNativeThreatReply(value:unknown,world:string,draft:string):Promise<NativeThreatReply> {
  const fail=()=>{throw new Error('Native creature review does not match this saved draft. The retained review was kept.');};
  if(!record(value))return fail();
  const publication='dmb-native-threat:v1:'+draft;
  if(value.state==='published'){
    if(value.world_id!==world||value.draft_id!==draft||value.publication_id!==publication
      ||!text(value.native_world_id)||!positive(value.binding_version)||!text(value.node_id)||!value.node_id.startsWith('ent:')
      ||!text(value.published_revision_id)||typeof value.replayed!=='boolean')return fail();
    return value as unknown as PublishedNativeThreat;
  }
  const r=value.review;
  if(value.state!=='prepared'||!text(value.source_text)||!text(value.token)||!record(value.prepared)||!record(r)
    ||r.schema!=='dmb_native_threat_review_v1'||r.world_id!==world||r.draft_id!==draft||r.publication_id!==publication
    ||!positive(r.draft_version)||!text(r.label)||!hex(r.body_sha256)||!hex(r.prepared_digest)
    ||!record(r.binding)||r.binding.managed_world_id!==world||!text(r.binding.native_world_id)||!positive(r.binding.binding_version)
    ||![r.source_evidence_id,r.source_artifact_id,r.source_revision_id,r.principal,r.expires_at].every(text)
    ||!Number.isFinite(Date.parse(String(r.expires_at))))return fail();
  // Bind displayed retained text to the server review; WK/signature validation
  // stays on the server. Expiry is intentionally not a client recovery decision.
  const digest=Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',new TextEncoder().encode(value.source_text))),b=>b.toString(16).padStart(2,'0')).join('');
  if(digest!==r.body_sha256)return fail();
  return value as unknown as PreparedNativeThreat;
}
