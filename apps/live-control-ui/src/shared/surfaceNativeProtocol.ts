import type {SurfaceNativeContextReceiptV1,SurfaceNativeCompletionV1,SurfaceNativeWorkContextV1,PlanSourceContextReceiptV1} from '../api/types';
import {exact,canonical,isCollaboration,isDraftReferenceClaim,isRelatedPageClaim,isSavedSourceClaim} from './sourcePassageProtocol';
import {isNativePlanQuery,isNativeClauseCitation} from './nativeStatementAnswerProtocol';
import {isNativeAssertionClaim,isNativeAssertionCitation} from './nativeAssertionProtocol';
import {isNativeBodyCitation} from './nativeSourceCitationProtocol';
import {isAuthoredExcerpt,isSessionSummary} from './surfaceEvidenceProtocol';
const text=(v:unknown):v is string=>typeof v==='string'&&!!v.trim();
const hash=(v:unknown):v is string=>typeof v==='string'&&/^[a-f0-9]{64}$/.test(v);
const uuid=(v:unknown):v is string=>typeof v==='string'&&/^[a-f0-9]{8}-(?:[a-f0-9]{4}-){3}[a-f0-9]{12}$/i.test(v);
const integer=(v:unknown,min=0):v is number=>typeof v==='number'&&Number.isSafeInteger(v)&&v>=min;
/** Closed presentation shape; Core and APP own admission and publication. */
export function isNativeSourceAuthority(a:unknown,worldId:string):a is PlanSourceContextReceiptV1['source_authority'] {
  if(exact(a,['schema','managed_world_id','failure_code'])&&a.schema==='dmb_native_corpus_unavailable_v1')
    return a.managed_world_id===worldId&&['native_source_identity_unavailable','native_source_head_unavailable','native_source_authority_unavailable'].includes(String(a.failure_code));
  const ref=(v:unknown)=>exact(v,['authority_id','revision','descriptor_sha256'])&&text(v.authority_id)&&text(v.revision)&&hash(v.descriptor_sha256);
  return exact(a,['schema_version','managed_world_id','native_world_id','binding_version','provisioning_id','revision_id','domain_ref','profile_ref','acquisition_epoch','scope','role'])
    &&a.schema_version==='dmb_native_corpus_authority_v1'&&a.managed_world_id===worldId&&text(a.native_world_id)&&text(a.revision_id)&&integer(a.binding_version,1)
    &&(a.provisioning_id===null||text(a.provisioning_id))&&integer(a.acquisition_epoch)&&ref(a.domain_ref)&&ref(a.profile_ref)&&a.scope==='gm_world_cross_campaign_source_inspection'&&a.role==='gm';
}
export function isNativeProviderInput(input:unknown,assembler:'surface_native_initial_v1'|'plan_source_jev_initial_v1'):boolean {
  return exact(input,['assembler_version','provider_model_name','provider_model_version','tokenizer_name','tokenizer_version','provider_envelope_input_tokens','output_token_reserve','context_window_limit','included_history','assembled_input_sha256'])
    &&input.assembler_version===assembler&&[input.provider_model_name,input.provider_model_version,input.tokenizer_name,input.tokenizer_version].every(text)
    &&integer(input.provider_envelope_input_tokens)&&integer(input.output_token_reserve)&&integer(input.context_window_limit,1)
    &&input.provider_envelope_input_tokens+input.output_token_reserve<=input.context_window_limit&&hash(input.assembled_input_sha256)
    &&Array.isArray(input.included_history)&&input.included_history.every(pin=>exact(pin,['turn_id','answer_sha256'])&&uuid(pin.turn_id)&&hash(pin.answer_sha256))
    &&new Set(input.included_history.map(pin=>pin.turn_id)).size===input.included_history.length;
}
export function nativeWorkWorld(work:SurfaceNativeWorkContextV1):string {
  return work.surface_id==='build'?work.source_basis.world_id:work.surface_id==='plan'?work.plan_basis.world_id:work.play_basis.world_id;
}
/** Work shape stays with its actual surface owner, never a fabricated old receipt. */
export function isSurfaceNativeReceipt(v:unknown,validateWork:(work:unknown)=>work is SurfaceNativeWorkContextV1):v is SurfaceNativeContextReceiptV1 {
  if(!exact(v,['schema','receipt_serializer_version','context_receipt_sha256','provenance_sha256','work_context','source_authority','native_query','assembled_input'])
    ||v.schema!=='dmb_surface_native_context_receipt_v1'||v.receipt_serializer_version!=='canonical-json-utf8-v1'||!hash(v.context_receipt_sha256)||!hash(v.provenance_sha256)||!validateWork(v.work_context))return false;
  const world=nativeWorkWorld(v.work_context),a=v.source_authority,q=v.native_query;
  if(!isNativeSourceAuthority(a,world)||!isNativePlanQuery(q,world)||q.schema==='dmb_native_plan_query_v1')return false;
  if(q.schema==='dmb_native_plan_query_v2'&&'schema_version' in a&&['native_world_id','binding_version','revision_id','domain_ref','profile_ref','acquisition_epoch'].some(k=>canonical(a[k as keyof typeof a])!==canonical(q.authority[k as keyof typeof q.authority])))return false;
  return isNativeProviderInput(v.assembled_input,'surface_native_initial_v1')||v.work_context.surface_id==='build'&&exact(v.assembled_input,['assembler_version','submitted_intent_sha256','assembled_input_sha256'])&&v.assembled_input.assembler_version==='reviewed_author_admission_v1'&&hash(v.assembled_input.submitted_intent_sha256)&&hash(v.assembled_input.assembled_input_sha256);
}
export function isSurfaceNativeCompletion(v:unknown,r:SurfaceNativeContextReceiptV1):v is SurfaceNativeCompletionV1 {
  if(!exact(v,['schema','surface_id','context_receipt_sha256','producing_provider_attempt_id','answer_basis','answer_context_status','answer_segments','collaboration','saved_source_citations','native_body_citations','native_clause_citations','native_assertion_citations'])
    ||v.schema!=='dmb_surface_native_completion_v1'||v.surface_id!==r.work_context.surface_id||v.context_receipt_sha256!==r.context_receipt_sha256||!uuid(v.producing_provider_attempt_id)||v.answer_basis!=='mixed_evidence'
    ||!Array.isArray(v.answer_segments)||v.answer_segments.length>128||!isCollaboration(v.collaboration,true,true,true,true)||v.collaboration!==null&&v.surface_id!=='build'||!v.answer_segments.length&&v.collaboration===null)return false;
  const sources=new Set<number>(),graphs=new Map<number,string[]>(),saved=new Set<number>(),blocks=new Set<string>();
  let authored=false,buildAuthored=false,proposal=false,partial=false,discussion=false;
  const work=r.work_context;
  for(const [i,s] of v.answer_segments.entries()) {
    if(!s||typeof s!=='object'||!text(s.text))return false;
    if(s.kind==='source_passage_claim') {if(!exact(s,['kind','text']))return false;sources.add(i);}
    else if(s.kind==='native_assertion_claim') {if(!isNativeAssertionClaim(s))return false;graphs.set(i,s.assertion_ids);}
    else if(s.kind==='authored_excerpt'||s.kind==='session_summary') {
      if(work.surface_id!=='plan'||(s.kind==='session_summary'?!isSessionSummary(s):!isAuthoredExcerpt(s)))return false;
      for(const q of s.kind==='session_summary'?s.supports:[s])if(q.source_kind==='play'||q.source_kind==='plan'&&(q.object_id!==work.plan_basis.document_id||q.revision!==work.plan_basis.work_revision_id||q.owner_sha256!==work.plan_basis.content_sha256||q.body_sha256!==q.owner_sha256))return false;
      if(s.kind==='authored_excerpt'){if(blocks.has(s.block_handle))return false;blocks.add(s.block_handle);}authored=true;
    } else if(s.kind==='proposal') {if(!exact(s,['kind','text','label'])||!['invented_idea','image_prompt'].includes(String(s.label)))return false;proposal=true;}
    else if(s.kind==='limitation') {if(!exact(s,['kind','text','code','question_phrase'])||!['missing_requested_details','partial_retrieval','unresolved_conflict'].includes(String(s.code))||!(s.question_phrase===null||text(s.question_phrase)))return false;partial=true;}
    else if(work.surface_id==='build'&&s.kind==='discussion') {if(!exact(s,['kind','text']))return false;discussion=true;}
    else if(work.surface_id==='build'&&s.kind==='draft_reference_claim') {if(!isDraftReferenceClaim(s))return false;buildAuthored=true;}
    else if(work.surface_id==='build'&&s.kind==='related_page_claim') {
      if(!isRelatedPageClaim(s,work.source_basis.world_id))return false;buildAuthored=true;
    } else if(work.surface_id==='build'&&s.kind==='saved_source_claim') {if(!isSavedSourceClaim(s,work.source_basis.content_sha256))return false;saved.add(i);}
    else return false;
  }
  const seen=new Set<string>(),cited=new Set<number>(),assertions=new Map<number,Set<string>>();
  for(const family of ['native_body_citations','native_clause_citations','native_assertion_citations'] as const) {
    const cites=v[family];if(!Array.isArray(cites)||cites.length>16384)return false;
    for(const c of cites) {
      if(family==='native_body_citations'?!isNativeBodyCitation(c):family==='native_clause_citations'?!isNativeClauseCitation(c,r.context_receipt_sha256):!isNativeAssertionCitation(c,r.context_receipt_sha256))return false;
      if(c.provider_attempt_id!==v.producing_provider_attempt_id)return false;
      const index=c.segment_index,key=canonical(family==='native_body_citations'?['body',index,c.read_event_id]:family==='native_clause_citations'?['statement',index,c.statement_id]:['assertion',index,c.read_event_id,c.assertion_id,c.evidence_ref_id]);
      if(seen.has(key))return false;seen.add(key);
      if(family==='native_body_citations'){if(!sources.has(index)||c.line_end<c.line_start)return false;cited.add(index);continue;}
      const q=r.native_query;
      if(q.schema!=='dmb_native_plan_query_v2'||c.managed_world_id!==q.authority.managed_world_id||c.native_world_id!==q.authority.native_world_id||c.read_revision_id!==q.authority.revision_id)return false;
      if(family==='native_clause_citations'){if(!sources.has(index)||!q.matches.some(m=>m.statement_id===c.statement_id&&m.campaign_id===c.campaign_id))return false;cited.add(index);}
      else {if(!graphs.get(index)?.includes(c.assertion_id)||!q.assertion_matches.some(m=>m.assertion_id===c.assertion_id&&m.assertion_sha256===c.assertion_sha256))return false;const ids=assertions.get(index)??new Set<string>();ids.add(c.assertion_id);assertions.set(index,ids);}
    }
  }
  if([...sources].some(i=>!cited.has(i))||[...graphs].some(([i,ids])=>ids.some(id=>!assertions.get(i)?.has(id))))return false;
  if(!Array.isArray(v.saved_source_citations)||v.saved_source_citations.length!==saved.size)return false;
  for(const [i,c] of v.saved_source_citations.entries())if(!exact(c,['segment_index','text_sha256','section_event_ids'])||c.segment_index!==[...saved][i]||!hash(c.text_sha256)||!Array.isArray(c.section_event_ids)||!c.section_event_ids.length||c.section_event_ids.length>128||!c.section_event_ids.every((id,j)=>uuid(id)&&(!j||((c.section_event_ids as string[])[j-1]!)<id)))return false;
  const status=graphs.size?'graph_grounded':buildAuthored?'authored_grounded':sources.size||saved.size?'source_grounded':authored?'authored_grounded':proposal?'creative_proposal':discussion&&!partial||!v.answer_segments.length?'discussion':'insufficient_evidence';
  return v.answer_context_status===status+(partial&&!['creative_proposal','insufficient_evidence','discussion'].includes(status)?'_partial':'');
}
