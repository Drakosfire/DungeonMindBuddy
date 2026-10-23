import {isNativeSourceCitation} from './nativeSourceCitationProtocol';
import type {SurfaceEvidenceCompletion,WorldPlanGraphContextReceiptV1,WorldPlayGraphContextReceiptV1} from "../api/types";
import {exact, canonical, isSurfaceSourceCompletion} from "./sourcePassageProtocol";
const text = (v:unknown):v is string => typeof v === 'string' && !!v.trim();
const hash = (v:unknown):v is string => typeof v === 'string' && /^[a-f0-9]{64}$/.test(v);
const sorted = (v:unknown):v is string[] => Array.isArray(v) && v.every((x,i) => text(x) && (!i || v[i-1] < x));
/** Closed presentation shape. The server independently proves producer input and authority. */
export function isSurfaceEvidenceCompletion(v:unknown, receiptHash:string, surface:'plan'|'play'):v is SurfaceEvidenceCompletion {
  const native=typeof v==='object' && v!==null && 'schema' in v && v.schema==='dmb_surface_evidence_completion_v3';
  if (!exact(v,['schema','surface_id','context_receipt_sha256','answer_basis','answer_context_status','answer_segments','citation_map','source_citations',...(native ? ['native_source_citations']:[])])
    || !['dmb_surface_evidence_completion_v1','dmb_surface_evidence_completion_v2','dmb_surface_evidence_completion_v3'].includes(String(v.schema)) || v.surface_id !== surface || v.context_receipt_sha256 !== receiptHash
    || v.answer_basis !== 'mixed_evidence' || !Array.isArray(v.answer_segments) || !v.answer_segments.length || v.answer_segments.length > 128
    || !Array.isArray(v.source_citations) || v.source_citations.length > 16384) return false;
  const claims = new Map<string,{index:number;segment:Record<string,unknown>}>(), sources = new Set<number>();
  let authored=false, proposal=false, partial=false;
  const blocks=new Set<string>();
  for (const [index,s] of v.answer_segments.entries()) {
    if (!s || typeof s !== 'object' || !text(s.text)) return false;
    if (s.kind === 'graph_claim') {
      if (!exact(s,['kind','text','claim_id','target_kind','target_id','graph_revision','evidence_ref_ids'])
        || !text(s.claim_id) || claims.has(s.claim_id) || !text(s.target_id) || !text(s.graph_revision)
        || !['assertion','relationship'].includes(String(s.target_kind)) || !sorted(s.evidence_ref_ids) || !s.evidence_ref_ids.length) return false;
      claims.set(s.claim_id,{index,segment:s});
    } else if (s.kind === 'source_passage_claim') {
      if (!exact(s,['kind','text'])) return false; sources.add(index);
    } else if (s.kind === 'authored_quote' || s.kind === 'authored_excerpt') {
      const block=s.kind === 'authored_excerpt';
      if(block !== (v.schema !== 'dmb_surface_evidence_completion_v1')) return false;
      if(block && (!text(s.block_handle) || !/^b[a-f0-9]{64}$/.test(s.block_handle) || blocks.has(s.block_handle)
        || s.partition_version !== 'markdown_source_blocks_v1' || !Number.isSafeInteger(s.byte_start)
        || !Number.isSafeInteger(s.byte_end) || s.byte_start < 0 || s.byte_end-s.byte_start !== new TextEncoder().encode(s.text).length
        || !hash(s.block_sha256) || !(s.entry_identity === null || hash(s.entry_identity))
        || (s.source_kind === 'session') !== (s.entry_identity !== null))) return false;
      if(block) blocks.add(s.block_handle);
      if (!exact(s,['kind','text','source_handle','source_kind','source_name','object_id','revision','body_sha256','owner_sha256',...(block ? ['block_handle','partition_version','byte_start','byte_end','block_sha256','entry_identity']:[])])
        || !['plan','session','play'].includes(String(s.source_kind)) || ![s.source_handle,s.source_name,s.object_id,s.revision].every(text)
        || !hash(s.body_sha256) || !hash(s.owner_sha256)) return false;
      authored=true;
    } else if (s.kind === 'proposal') {
      if (!exact(s,['kind','text','label']) || !['invented_idea','image_prompt'].includes(String(s.label))) return false; proposal=true;
    } else if (s.kind === 'limitation') {
      if (!exact(s,['kind','code','text','question_phrase']) || !['missing_requested_details','partial_retrieval','unresolved_conflict'].includes(String(s.code))
        || !(s.question_phrase === null || text(s.question_phrase))) return false; partial=true;
    } else return false;
  }
  const cited=new Set<number>(), seen=new Set<string>();
  for (const c of v.source_citations) {
    const segment = v.answer_segments[c?.segment_index];
    if (!segment || !['graph_claim','source_passage_claim'].includes(segment.kind)
      || !isSurfaceSourceCompletion({schema:'dmb_surface_source_completion_v1',surface_id:surface,context_receipt_sha256:receiptHash,
        answer_basis:'opened_source_passages',answer_context_status:'source_grounded',citation_map:null,
        answer_segments:[{kind:'source_passage_claim',text:segment.text}],source_citations:[{...c,segment_index:0}]},receiptHash,surface)) return false;
    const key=canonical([c.segment_index,c.read_event_id,c.receipt.source_read_id]);
    if(seen.has(key)) return false; seen.add(key); cited.add(c.segment_index);
    if(segment.kind === 'graph_claim' && !segment.evidence_ref_ids.includes(c.receipt.evidence_ref_id)) return false;
  }
  if(native) {
    if(!Array.isArray(v.native_source_citations) || v.native_source_citations.length>16384) return false;
    for(const c of v.native_source_citations) {
      if(!isNativeSourceCitation(c) || v.answer_segments[c.segment_index]?.kind !== 'source_passage_claim') return false;
      const key=canonical(['native',c.segment_index,c.read_event_id]);
      if(seen.has(key)) return false; seen.add(key); cited.add(c.segment_index);
    }
  }
  if([...sources].some(i => !cited.has(i))) return false;
  const map=v.citation_map;
  if(!claims.size) { if(map !== null) return false; }
  else {
    if(!exact(map,['schema','context_receipt_sha256','entries']) || map.schema !== 'dmb_graph_citation_map_v2'
      || map.context_receipt_sha256 !== receiptHash || !Array.isArray(map.entries) || map.entries.length !== claims.size) return false;
    const used=new Set();
    for(const e of map.entries) {
      if(!exact(e,['claim_id','target_kind','target_id','graph_revision','evidence_ref_ids','source_opened','source_read_ids'])
        || typeof e.claim_id !== 'string' || used.has(e.claim_id)) return false;
      const claim=claims.get(e.claim_id); if(!claim) return false; used.add(e.claim_id);
      if(['target_kind','target_id','graph_revision','evidence_ref_ids'].some(k => canonical(e[k]) !== canonical(claim.segment[k]))) return false;
      const reads=[...new Set(v.source_citations.filter(c => c.segment_index === claim.index).map(c => c.receipt.source_read_id))].sort();
      if(canonical(e.source_read_ids) !== canonical(reads) || e.source_opened !== !!reads.length) return false;
    }
  }
  const status=claims.size ? 'graph_grounded' : sources.size ? 'source_grounded' : authored ? 'authored_grounded' : proposal ? 'creative_proposal' : 'insufficient_evidence';
  return v.answer_context_status === status + (partial && !['creative_proposal','insufficient_evidence'].includes(status) ? '_partial' : '');
}


export function surfaceEvidenceReceiptBound(c:SurfaceEvidenceCompletion,r:WorldPlanGraphContextReceiptV1|WorldPlayGraphContextReceiptV1):boolean {
  if(c.context_receipt_sha256 !== r.context_receipt_sha256) return false;
  const plan=r.schema === 'dmb_agent_plan_world_graph_context_receipt_v1';
  if(c.surface_id !== (plan ? 'plan':'play')) return false;
  return c.answer_segments.every(s=>{
    if(s.kind === 'graph_claim') return s.graph_revision === r.graph_authority.graph_revision;
    if(s.kind !== 'authored_quote' && s.kind !== 'authored_excerpt') return true;
    if(s.source_kind === 'session') return plan;
    if(s.source_kind === 'plan') return plan && s.object_id === r.plan_basis.document_id
      && s.revision === r.plan_basis.work_revision_id && s.owner_sha256 === r.plan_basis.content_sha256 && s.body_sha256 === s.owner_sha256;
    if(plan) return false;
    const e=r.play_sources.entries.find(e=>e.source_id === s.source_handle);
    return !!e && s.body_sha256 === e.text_sha256 && s.owner_sha256 === e.payload_sha256
      && s.object_id === e.locator.run_id && s.revision === String(e.locator.run_revision);
  });
}
