import type {NativeStatementAnswerContextV1} from '../api/types';
import {exact,canonical} from './sourcePassageProtocol';
const record=(v:unknown):v is Record<string,unknown>=>typeof v==='object'&&v!==null&&!Array.isArray(v);
const hash=(v:unknown):v is string=>typeof v==='string'&&/^[a-f0-9]{64}$/.test(v);
const text=(v:unknown):v is string=>typeof v==='string'&&v.trim().length>0;
export async function nativeTextDigest(value:string){
  const bytes=await crypto.subtle.digest('SHA-256',new TextEncoder().encode(value));
  return Array.from(new Uint8Array(bytes),b=>b.toString(16).padStart(2,'0')).join('');
}
export function nativeAnswerText(context:NativeStatementAnswerContextV1){
  const prefix={source_report:'Source reports: ',proposal:'Possibility: ',limitation:'Limitation: '};
  return context.completion?.answer_segments.map(s=>prefix[s.kind]+s.text).join('\n')??null;
}
export function isNativeStatementContext(value:unknown,worldId:string):value is NativeStatementAnswerContextV1{
  if(!exact(value,['schema','receipt','completion','delivery_replay'])||value.schema!=='dmb_native_statement_answer_context_v1'||typeof value.delivery_replay!=='boolean')return false;
  const r=value.receipt;
  if(!exact(r,['schema','selection','frame','user_text','provenance_sha256','context_receipt_sha256'])
    ||r.schema!=='dmb_native_statement_context_receipt_v1'||!hash(r.provenance_sha256)||!hash(r.context_receipt_sha256)||!text(r.user_text))return false;
  const f=r.frame,s=r.selection;
  if(!exact(s,['schema','managedWorldId','campaignId','revisionId','subjectId','domainRef','profileRef'])||s.schema!=='dmb_native_statement_selection_v1'
    ||!exact(f,['schema','authority','managed_world_id','native_world_id','binding_version','campaign_id','role','revision_id','domain_ref','profile_ref','subject_id','status','gap_codes','supports','universal_absence_claimed'])
    ||f.schema!=='dmb_native_statement_frame_v1'||f.authority!=='native_vnext'||f.managed_world_id!==worldId||s.managedWorldId!==worldId
    ||s.campaignId!==f.campaign_id||s.revisionId!==f.revision_id||s.subjectId!==f.subject_id||!text(f.subject_id)||!f.subject_id.startsWith('ent:')
    ||!text(f.native_world_id)||!Number.isSafeInteger(f.binding_version)||Number(f.binding_version)<1||!['gm','player'].includes(String(f.role))
    ||f.universal_absence_claimed!==false||!['complete','partial','no_visible_statements'].includes(String(f.status))
    ||!Array.isArray(f.gap_codes)||!f.gap_codes.every(text)||!Array.isArray(f.supports)
    ||canonical(s.domainRef)!==canonical(f.domain_ref)||canonical(s.profileRef)!==canonical(f.profile_ref))return false;
  for(const ref of [f.domain_ref,f.profile_ref])if(!exact(ref,['authority_id','revision','descriptor_sha256'])||!text(ref.authority_id)||!text(ref.revision)||!hash(ref.descriptor_sha256))return false;
  const supports=new Map<string,Record<string,unknown>>();
  for(const support of f.supports){
    if(!record(support)||!text(support.statement_id)||supports.has(support.statement_id)||!record(support.payload)
      ||support.payload.embedded_content_factive!==false||support.payload.assertion_target!=='source_statement'
      ||!Array.isArray(support.payload.referents)||!support.payload.referents.includes(f.subject_id)
      ||!hash(support.semantic_digest)||!text(support.source_artifact_id)||!text(support.source_revision_id)||!hash(support.source_body_sha256)
      ||!Number.isSafeInteger(support.clause_start_byte)||Number(support.clause_start_byte)<0||!Number.isSafeInteger(support.clause_end_byte)
      ||Number(support.clause_end_byte)<=Number(support.clause_start_byte)||!hash(support.clause_sha256)||!text(support.clause_text)
      ||!record(support.publication_receipt)||!text(support.publication_receipt.published_revision_id))return false;
    const p=support.payload,clause=p.clause;
    if(!exact(p,['schema','clause','quote','meaning','mode','reporter','referents','uncertainty','qualifications','episode','source_order','embedded_content_factive','assertion_target','visibility','proof'])
      ||p.schema!=='dmb_source_statement_v1'||!['narrator','reported','uncertain'].includes(String(p.mode))
      ||(p.reporter!==null&&!text(p.reporter))||(p.mode==='reported'&&!text(p.reporter))
      ||!text(p.meaning)||!text(p.episode)||!Array.isArray(p.uncertainty)||!p.uncertainty.every(text)
      ||!record(p.qualifications)||!Object.keys(p.qualifications).length||!Object.values(p.qualifications).every(text)
      ||!Array.isArray(p.source_order)||p.quote!==support.clause_text
      ||!exact(clause,['world','campaign','logical_source','source_sha256','start_byte','end_byte','clause_sha256'])
      ||clause.world!==f.native_world_id||clause.campaign!==f.campaign_id||clause.source_sha256!==support.source_body_sha256
      ||clause.start_byte!==support.clause_start_byte||clause.end_byte!==support.clause_end_byte||clause.clause_sha256!==support.clause_sha256
      ||!exact(p.proof,['source_admission_id','evidence_ref_id'])||!text(p.proof.source_admission_id)||!text(p.proof.evidence_ref_id))return false;
    supports.set(support.statement_id,support);
  }
  if(f.status==='complete'&&(!supports.size||f.gap_codes.length)||f.status==='partial'&&!f.gap_codes.length
    ||f.status==='no_visible_statements'&&(supports.size||f.gap_codes.length))return false;
  const c=value.completion;
  if(c===null)return true;
  if(!exact(c,['schema','surface_id','context_receipt_sha256','answer_context_status','answer_segments','native_clause_citations'])
    ||c.schema!=='dmb_native_statement_completion_v1'||c.surface_id!=='plan'||c.context_receipt_sha256!==r.context_receipt_sha256
    ||!['source_attributed','source_attributed_partial','insufficient_evidence'].includes(String(c.answer_context_status))
    ||!Array.isArray(c.answer_segments)||!c.answer_segments.length||!Array.isArray(c.native_clause_citations))return false;
  const wanted=new Set<string>(),seen=new Set<string>();
  for(const [i,seg] of c.answer_segments.entries()){
    if(!exact(seg,['kind','text','statement_ids'])||!['source_report','proposal','limitation'].includes(String(seg.kind))||!text(seg.text)
      ||!Array.isArray(seg.statement_ids)||Boolean(seg.statement_ids.length)!==(seg.kind==='source_report')
      ||new Set(seg.statement_ids).size!==seg.statement_ids.length)return false;
    for(const id of seg.statement_ids){if(!text(id)||!supports.has(id))return false;wanted.add(`${i}:${id}`);}
  }
  for(const cite of c.native_clause_citations){
    if(!exact(cite,['segment_index','statement_id','provider_attempt_id','envelope_sha256','context_receipt_sha256','managed_world_id','native_world_id','campaign_id','read_revision_id','publication_revision_id','source_artifact_id','source_revision_id','body_sha256','start_byte','end_byte','clause_sha256','semantic_digest'])
      ||!text(cite.statement_id)||!Number.isSafeInteger(cite.segment_index)||!text(cite.provider_attempt_id)||!hash(cite.envelope_sha256)
      ||cite.context_receipt_sha256!==r.context_receipt_sha256||cite.managed_world_id!==worldId||cite.native_world_id!==f.native_world_id
      ||cite.campaign_id!==f.campaign_id||cite.read_revision_id!==f.revision_id)return false;
    const support=supports.get(cite.statement_id),key=`${cite.segment_index}:${cite.statement_id}`;
    if(!support||!wanted.has(key)||seen.has(key)||!record(support.publication_receipt)||cite.publication_revision_id!==support.publication_receipt.published_revision_id
      ||cite.source_artifact_id!==support.source_artifact_id||cite.source_revision_id!==support.source_revision_id||cite.body_sha256!==support.source_body_sha256
      ||cite.start_byte!==support.clause_start_byte||cite.end_byte!==support.clause_end_byte||cite.clause_sha256!==support.clause_sha256||cite.semantic_digest!==support.semantic_digest)return false;
    seen.add(key);
  }
  return seen.size===wanted.size&&((c.answer_context_status==='insufficient_evidence')===!seen.size)
    &&(!seen.size||c.answer_context_status===(f.status==='partial'?'source_attributed_partial':'source_attributed'));
}
export async function nativeStatementDigestsBound(context:NativeStatementAnswerContextV1,provenance:unknown){
  const {context_receipt_sha256,...payload}=context.receipt;
  if(await nativeTextDigest(canonical(payload))!==context_receipt_sha256||await nativeTextDigest(canonical(provenance))!==context.receipt.provenance_sha256)return false;
  for(const s of context.receipt.frame.supports){
    const {proof:_,...meaning}=s.payload;
    if(await nativeTextDigest(canonical(meaning))!==s.semantic_digest||await nativeTextDigest(s.clause_text)!==s.clause_sha256
      ||new TextEncoder().encode(s.clause_text).length!==s.clause_end_byte-s.clause_start_byte)return false;
  }
  return true;
}
