import type {SurfaceNativeCompletionV1,SurfaceEvidenceCompletionV3,WorldBuildGraphReceiptV1} from './types';
import {exact,isBuildSourceBasis} from '../shared/sourcePassageProtocol';
import {isNativeBodyCitation,isNativeSourceCitation} from '../shared/nativeSourceCitationProtocol';
import {isNativeClauseCitationShape} from '../shared/nativeStatementAnswerProtocol';
import {isNativeAssertionCitationShape} from '../shared/nativeAssertionProtocol';

export type SavedCitationPreview = {
  schema:'dmb_saved_native_citation_preview_v1';status:'ready';surface_id:'build'|'plan'|'play';
  answer_segments:{kind:string;text:string;content_sha256?:string}[];
  native_source_citations:SurfaceEvidenceCompletionV3['native_source_citations'];
  native_body_citations:SurfaceNativeCompletionV1['native_body_citations'];
  native_clause_citations:SurfaceNativeCompletionV1['native_clause_citations'];
  native_assertion_citations:SurfaceNativeCompletionV1['native_assertion_citations'];
  saved_source_citations:SurfaceNativeCompletionV1['saved_source_citations'];
  source_basis:WorldBuildGraphReceiptV1['source_basis']|null;
}|{status:'details_required';reason:'mixed_rules'|'unsupported_completion'|'unsupported_sources'|'invalid_presentation'}|null;
const unavailable=():SavedCitationPreview=>({status:'details_required',reason:'invalid_presentation'});
const hash=(v:unknown):v is string=>typeof v==='string'&&/^[a-f0-9]{64}$/.test(v);
const uuid=(v:unknown):v is string=>typeof v==='string'&&/^[a-f0-9]{8}-(?:[a-f0-9]{4}-){3}[a-f0-9]{12}$/i.test(v);
/** Display-only shape. No execution, query membership, action or grounding grant. */
export function readSavedCitationPreview(v:unknown,world:string,surface:string,answer:string|null):SavedCitationPreview {
  if(v===null)return null;
  if(exact(v,['status','reason'])&&v.status==='details_required'&&['mixed_rules','unsupported_completion','unsupported_sources','invalid_presentation'].includes(String(v.reason)))return v as Exclude<SavedCitationPreview,null>;
  if(!exact(v,['schema','status','surface_id','answer_segments','native_source_citations','native_body_citations','native_clause_citations','native_assertion_citations','saved_source_citations','source_basis'])
    ||v.schema!=='dmb_saved_native_citation_preview_v1'||v.status!=='ready'||v.surface_id!==surface||!['build','plan','play'].includes(surface)
    ||!Array.isArray(v.answer_segments)||!v.answer_segments.length||v.answer_segments.length>128)return unavailable();
  const segments=v.answer_segments;
  if(!segments.every(s=>exact(s,s?.kind==='saved_source_claim'?['kind','text','content_sha256']:['kind','text'])
      &&['source_passage_claim','native_assertion_claim','saved_source_claim','proposal','limitation','discussion','draft_reference_claim'].includes(String(s.kind))
      &&typeof s.text==='string'&&!!s.text.trim()&&(s.kind!=='saved_source_claim'||hash(s.content_sha256)))
    ||segments.map(s=>s.text).join('\n')!==answer)return unavailable();
  const checks={native_source_citations:isNativeSourceCitation,native_body_citations:isNativeBodyCitation,native_clause_citations:isNativeClauseCitationShape,native_assertion_citations:isNativeAssertionCitationShape};
  const sourceSegments=new Set<number>(),graphSegments=new Set<number>(),savedSegments=new Set<number>();
  for(const [name,check] of Object.entries(checks)){
    const citations=v[name];if(!Array.isArray(citations)||citations.length>16384)return unavailable();
    const seen=new Set<string>();
    for(const c of citations){
      if(!check(c)||c.segment_index>=segments.length||('managed_world_id' in c&&c.managed_world_id!==world))return unavailable();
      const kind=segments[c.segment_index]?.kind;
      if(name==='native_assertion_citations'?kind!=='native_assertion_claim':kind!=='source_passage_claim')return unavailable();
      const key=JSON.stringify(c);if(seen.has(key))return unavailable();seen.add(key);
      (name==='native_assertion_citations'?graphSegments:sourceSegments).add(c.segment_index);
    }
  }
  if(!Array.isArray(v.saved_source_citations)||v.saved_source_citations.length>128)return unavailable();
  for(const c of v.saved_source_citations){
    if(!exact(c,['segment_index','text_sha256','section_event_ids'])||!Number.isSafeInteger(c.segment_index)||Number(c.segment_index)<0||!hash(c.text_sha256)
      ||!Array.isArray(c.section_event_ids)||!c.section_event_ids.length||c.section_event_ids.length>128||!c.section_event_ids.every((id,i,ids)=>uuid(id)&&(!i||String(ids[i-1])<id))
      ||segments[Number(c.segment_index)]?.kind!=='saved_source_claim'||savedSegments.has(Number(c.segment_index)))return unavailable();
    savedSegments.add(Number(c.segment_index));
  }
  const basis=v.source_basis;
  if(v.saved_source_citations.length ? surface!=='build'||!isBuildSourceBasis(basis,world)||segments.some(s=>s.kind==='saved_source_claim'&&s.content_sha256!==basis.content_sha256) : basis!==null)return unavailable();
  if(segments.some((s,i)=>s.kind==='source_passage_claim'&&!sourceSegments.has(i)||s.kind==='native_assertion_claim'&&!graphSegments.has(i)||s.kind==='saved_source_claim'&&!savedSegments.has(i)))return unavailable();
  return v as Exclude<SavedCitationPreview,null>;
}
