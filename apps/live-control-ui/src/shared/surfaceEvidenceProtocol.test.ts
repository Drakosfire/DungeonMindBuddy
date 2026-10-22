import {describe,it,expect} from 'vitest';
import {isSurfaceEvidenceCompletion} from './surfaceEvidenceProtocol';
import type {SurfaceEvidenceCompletionV1} from '../api/types';
export function evidence():SurfaceEvidenceCompletionV1 {
  const id='11111111-1111-4111-8111-111111111111';
  return {schema:'dmb_surface_evidence_completion_v1',surface_id:'plan',context_receipt_sha256:'a'.repeat(64),
    answer_basis:'mixed_evidence',answer_context_status:'source_grounded',citation_map:null,
    answer_segments:[{kind:'source_passage_claim',text:'The journal describes a walkway.'},
      {kind:'authored_quote',text:'A proposed outing.',source_kind:'plan',source_name:'Committed Plan',
        source_handle:'q1',object_id:'plan-one',revision:'1',body_sha256:'b'.repeat(64),owner_sha256:'b'.repeat(64)}],
    source_citations:[{segment_index:0,text_sha256:'c'.repeat(64),provider_attempt_id:id,envelope_sha256:'d'.repeat(64),
      read_event_id:id,source_name:'Synthetic park journal',receipt:{source_read_id:'read1',anchor_id:'anchor1',evidence_ref_id:'e1',
        source_artifact_id:'source1',source_revision_id:'revision1',outcome:'enough',content_sha256:'e'.repeat(64),line_start:1,line_end:1,
        returned_chars:20,truncated:false,evidence_sufficiency_status:'sufficient'}}]};
}
describe('mixed surface evidence',()=>{
  it.each(['plan','play'] as const)('validates the same contract in %s',surface=>{
    const c=evidence();c.surface_id=surface;expect(isSurfaceEvidenceCompletion(c,'a'.repeat(64),surface)).toBe(true);
  });
  it.each(['missing citation','quote cited as corpus','wrong surface','wrong receipt','wrong status','truncated','unknown kind','extra field','duplicate citation'])('rejects %s',change=>{
    const c=evidence();
    if(change==='missing citation')c.source_citations=[];
    if(change==='quote cited as corpus')c.source_citations[0]!.segment_index=1;
    if(change==='wrong surface')c.surface_id='play';
    if(change==='wrong receipt')c.context_receipt_sha256='f'.repeat(64);
    if(change==='wrong status')c.answer_context_status='graph_grounded';
    if(change==='truncated')Object.assign(c.source_citations[0]!.receipt,{truncated:true});
    if(change==='unknown kind')Object.assign(c.answer_segments[1]!,{kind:'plan_claim'});
    if(change==='extra field')Object.assign(c,{metadata:'not admitted'});
    if(change==='duplicate citation')c.source_citations.push(c.source_citations[0]!);
    expect(isSurfaceEvidenceCompletion(c,'a'.repeat(64),'plan')).toBe(false);
  });
});

describe('host-materialized authored blocks',()=>{
  function current(){
    const old=evidence();
    const quote=old.answer_segments[1]!;
    return {...old,schema:'dmb_surface_evidence_completion_v2',answer_segments:[old.answer_segments[0],{
      ...quote,kind:'authored_excerpt',block_handle:'b'+'f'.repeat(64),partition_version:'markdown_source_blocks_v1',
      byte_start:12,byte_end:12+new TextEncoder().encode(quote.text).length,block_sha256:'e'.repeat(64),entry_identity:null}]};
  }
  it.each(['plan','play'] as const)('admits versioned exact stored blocks in %s',surface=>{
    const c={...current(),surface_id:surface};expect(isSurfaceEvidenceCompletion(c,'a'.repeat(64),surface)).toBe(true);
  });
  it.each(['legacy kind','span','partition','entry','duplicate','extra'])('rejects altered %s',change=>{
    const c=current(),s=c.answer_segments[1]!;
    if(change==='legacy kind')Object.assign(s,{kind:'authored_quote'});
    if(change==='span')Object.assign(s,{byte_end:1});
    if(change==='partition')Object.assign(s,{partition_version:'folded_v1'});
    if(change==='entry')Object.assign(s,{entry_identity:'unknown'});
    if(change==='duplicate')c.answer_segments.push(s);
    if(change==='extra')Object.assign(s,{model_text:'A rewritten quote.'});
    expect(isSurfaceEvidenceCompletion(c,'a'.repeat(64),'plan')).toBe(false);
  });
});
