import {it,expect,vi} from 'vitest';
import {nativeTextDigest} from './nativeStatementAnswerProtocol';
import {isNativeAssertionCitation} from './nativeAssertionProtocol';
import {isSurfaceEvidenceCompletion,surfaceEvidenceReceiptBound} from './surfaceEvidenceProtocol';
import {nativeChoices} from '../planSurface/components/sourceCitationReads';
import * as api from '../api/liveApi';
import type {SurfaceEvidenceCompletionV7,PlanNativeContextReceiptV1} from '../api/types';

async function fixture(){
  const hash='a'.repeat(64),body='B fled.';
  const citation={segment_index:0,assertion_id:'asrt:B',read_event_id:'read',provider_attempt_id:'writer',envelope_sha256:hash,
    context_receipt_sha256:hash,managed_world_id:'managed',native_world_id:'native',read_revision_id:'rev:R',assertion_sha256:hash,
    evidence_ref_id:'ev:support',source_artifact_id:'source',source_revision_id:'srev:S',body_sha256:hash,start_byte:0,end_byte:7,
    span_sha256:await nativeTextDigest(body)};
  const completion:SurfaceEvidenceCompletionV7={schema:'dmb_surface_evidence_completion_v7',surface_id:'plan',answer_basis:'mixed_evidence',
    context_receipt_sha256:hash,answer_context_status:'graph_grounded',citation_map:null,source_citations:[],native_source_citations:[],
    native_body_citations:[],native_clause_citations:[],native_assertion_citations:[citation],answer_segments:[{
      kind:'native_assertion_claim',text:'Graph records a belief: B fled.',assertion_ids:['asrt:B'],qualifications:[{
        scope:[{axis:'campaign',value:'c1'}],visibility:{kind:'labels_any',labels:['gm']},epistemic_basis:'speculative',
        claim_mode:'dungeonbuddy.claim:belief',standing:'provisional',evidence_ref_ids:['ev:support'],temporal_scope:{kind:'unknown'},domain_metadata:[]}]}]};
  const receipt={schema:'dmb_plan_native_context_receipt_v1',context_receipt_sha256:hash,graph_capability:null,
    native_query:{schema:'dmb_native_plan_query_v2',authority:{managed_world_id:'managed',native_world_id:'native',revision_id:'rev:R'},
      matches:[],assertion_matches:[{assertion_id:'asrt:B',assertion_sha256:hash}]}} as unknown as PlanNativeContextReceiptV1;
  return {completion,citation,receipt,hash,body};
}
it('keeps native Graph grounding distinct from source-only evidence and binds the exact selected assertion',async()=>{
  const {completion,receipt,hash}=await fixture();
  expect(isSurfaceEvidenceCompletion(completion,hash,'plan')).toBe(true);
  expect(surfaceEvidenceReceiptBound(completion,receipt)).toBe(true);
  completion.native_assertion_citations[0]!.assertion_id='asrt:nearby';
  expect(isSurfaceEvidenceCompletion(completion,hash,'plan')).toBe(false);
  expect(surfaceEvidenceReceiptBound(completion,receipt)).toBe(false);
});
it.each(['missing','duplicate','wrong-status','extra-field'])('rejects unsupported presentation: %s',async change=>{
  const {completion,hash}=await fixture();
  if(change==='missing')completion.native_assertion_citations=[];
  if(change==='duplicate')completion.native_assertion_citations.push(completion.native_assertion_citations[0]!);
  if(change==='wrong-status')completion.answer_context_status='source_grounded';
  if(change==='extra-field')Object.assign(completion.native_assertion_citations[0]!,{publication_authority:true});
  expect(isSurfaceEvidenceCompletion(completion,hash,'plan')).toBe(false);
});
it('opens exact source bytes through the normal citation control and rejects substituted text',async()=>{
  const {completion,citation,hash,body}=await fixture();
  expect(isNativeAssertionCitation(citation,hash)).toBe(true);
  const read=vi.spyOn(api,'getAgentNativeAssertionSource').mockResolvedValue({schema:'dmb_native_assertion_source_read_v1',
    world_id:'managed',turn_id:'turn',citation_index:0,citation,content:body});
  try {
    const choice=nativeChoices(completion,'managed','turn',0)[0]!;
    expect(await choice.load()).toBe(body);
    expect(read).toHaveBeenCalledWith('managed','turn',0);
    read.mockResolvedValue({schema:'dmb_native_assertion_source_read_v1',world_id:'managed',turn_id:'turn',citation_index:0,citation,content:'nearby'});
    await expect(choice.load()).rejects.toThrow('source binding differs');
  } finally {read.mockRestore();}
});
