import {it,expect} from 'vitest';
import {canonical} from './sourcePassageProtocol';
import {isNativeStatementContext,nativeStatementDigestsBound,nativeTextDigest} from './nativeStatementAnswerProtocol';
import type {NativeStatementAnswerContextV1} from '../api/types';

async function fixture(){
  const provenance={world_id:'managed',surface_id:'plan'};
  const body=await nativeTextDigest('quote'),ref={authority_id:'domain',revision:'2',descriptor_sha256:'a'.repeat(64)};
  const payload={schema:'dmb_source_statement_v1',clause:{world:'native',campaign:'c1',logical_source:{namespace:'fixture',object_id:'source'},source_sha256:body,start_byte:0,end_byte:5,clause_sha256:body},
    quote:'quote',meaning:'An uncertain report',mode:'reported',reporter:'ent:A',referents:['ent:B'],uncertainty:['uncertain'],qualifications:{kind:'report'},episode:'one',source_order:[],embedded_content_factive:false,assertion_target:'source_statement',visibility:'gm',proof:{source_admission_id:'admission',evidence_ref_id:'ev:1'}};
  const {proof:_,...meaning}=payload;
  const semantic=await nativeTextDigest(canonical(meaning));
  const frame={schema:'dmb_native_statement_frame_v1',authority:'native_vnext',managed_world_id:'managed',native_world_id:'native',binding_version:1,campaign_id:'c1',role:'gm',revision_id:'rev:R',domain_ref:ref,profile_ref:ref,subject_id:'ent:B',status:'complete',gap_codes:[],universal_absence_claimed:false,
    supports:[{statement_id:'ent:statement',payload,semantic_digest:semantic,assertion_ids:['assertion:1'],publication_receipt:{published_revision_id:'rev:C'},result_mappings:[],ancestry:[],source_artifact_id:'source',source_revision_id:'srev:1',source_body_sha256:body,clause_start_byte:0,clause_end_byte:5,clause_sha256:body,clause_text:'quote'}]};
  const receipt={schema:'dmb_native_statement_context_receipt_v1',selection:{schema:'dmb_native_statement_selection_v1',managedWorldId:'managed',campaignId:'c1',revisionId:'rev:R',subjectId:'ent:B',domainRef:ref,profileRef:ref},frame,user_text:'What was reported?',provenance_sha256:await nativeTextDigest(canonical(provenance))};
  const hash=await nativeTextDigest(canonical(receipt));
  const context={schema:'dmb_native_statement_answer_context_v1',receipt:{...receipt,context_receipt_sha256:hash},delivery_replay:true,
    completion:{schema:'dmb_native_statement_completion_v1',surface_id:'plan',context_receipt_sha256:hash,answer_context_status:'source_attributed',answer_segments:[{kind:'source_report',text:'An uncertain report',statement_ids:['ent:statement']}],native_clause_citations:[{segment_index:0,statement_id:'ent:statement',provider_attempt_id:'attempt',envelope_sha256:'e'.repeat(64),context_receipt_sha256:hash,managed_world_id:'managed',native_world_id:'native',campaign_id:'c1',read_revision_id:'rev:R',publication_revision_id:'rev:C',source_artifact_id:'source',source_revision_id:'srev:1',body_sha256:body,start_byte:0,end_byte:5,clause_sha256:body,semantic_digest:semantic}]}} as NativeStatementAnswerContextV1;
  return {context,provenance};
}
it('keeps source revision, publication child and read revision separate with committed source bytes',async()=>{
  const {context,provenance}=await fixture();
  expect(isNativeStatementContext(context,'managed')).toBe(true);
  expect(await nativeStatementDigestsBound(context,provenance)).toBe(true);
  context.receipt.frame.supports[0]!.clause_text='nearby paragraph';
  expect(await nativeStatementDigestsBound(context,provenance)).toBe(false);
});
it.each(['campaign','source-revision','publication','read-revision','unincluded','unqualified','extra','uncited'])('rejects native context substitution: %s',async change=>{
  const {context}=await fixture(),c=context.completion!,citation=c.native_clause_citations[0]!;
  if(change==='campaign')citation.campaign_id='other';
  if(change==='source-revision')citation.source_revision_id='rev:R';
  if(change==='publication')citation.publication_revision_id='rev:R';
  if(change==='read-revision')citation.read_revision_id='rev:C';
  if(change==='unincluded')c.answer_segments[0]!.statement_ids=['ent:other'];
  if(change==='unqualified')context.receipt.frame.supports[0]!.payload.embedded_content_factive=true;
  if(change==='extra')Object.assign(context,{graph_authority:{}});
  if(change==='uncited')c.native_clause_citations=[];
  expect(isNativeStatementContext(context,'managed')).toBe(false);
});
