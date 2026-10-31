import type {NativeAssertionCitationV1,NativeAssertionClaimV1} from '../api/types';
import {exact} from './sourcePassageProtocol';
const text=(v:unknown):v is string=>typeof v==='string'&&!!v.trim();
const hash=(v:unknown):v is string=>typeof v==='string'&&/^[a-f0-9]{64}$/.test(v);
/** Presentation shape only. Core and APP prove admission and producing reads. */
export function isNativeAssertionCitation(v:unknown,receiptHash:string):v is NativeAssertionCitationV1 {
  return exact(v,['segment_index','assertion_id','read_event_id','provider_attempt_id','envelope_sha256','context_receipt_sha256',
    'managed_world_id','native_world_id','read_revision_id','assertion_sha256','evidence_ref_id','source_artifact_id','source_revision_id',
    'body_sha256','start_byte','end_byte','span_sha256'])
    && Number.isSafeInteger(v.segment_index)&&Number(v.segment_index)>=0
    && [v.assertion_id,v.read_event_id,v.provider_attempt_id,v.managed_world_id,v.native_world_id,v.read_revision_id,
      v.evidence_ref_id,v.source_artifact_id,v.source_revision_id].every(text)
    && [v.envelope_sha256,v.context_receipt_sha256,v.assertion_sha256,v.body_sha256,v.span_sha256].every(hash)
    && v.context_receipt_sha256===receiptHash&&Number.isSafeInteger(v.start_byte)&&Number.isSafeInteger(v.end_byte)
    && Number(v.start_byte)>=0&&Number(v.end_byte)>Number(v.start_byte);
}
export function isNativeAssertionClaim(v:unknown):v is NativeAssertionClaimV1 {
  if(!exact(v,['kind','text','assertion_ids','qualifications'])||v.kind!=='native_assertion_claim'||!text(v.text)
    ||!Array.isArray(v.assertion_ids)||!v.assertion_ids.length||!v.assertion_ids.every(text)
    ||new Set(v.assertion_ids).size!==v.assertion_ids.length||!Array.isArray(v.qualifications)||!v.qualifications.length)return false;
  return v.qualifications.every(m=>exact(m,['scope','visibility','epistemic_basis','claim_mode','standing','evidence_ref_ids','temporal_scope','domain_metadata'])
    &&[m.epistemic_basis,m.claim_mode,m.standing].every(text)&&Array.isArray(m.scope)&&Array.isArray(m.evidence_ref_ids)&&Array.isArray(m.domain_metadata)
    &&typeof m.visibility==='object'&&m.visibility!==null&&typeof m.temporal_scope==='object'&&m.temporal_scope!==null);
}
