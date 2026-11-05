import type {CandidateReadEvidence,ExactRunCandidateProjection} from '../api/exactRunCandidateProjectionApi';
import type {RecapNativeReview} from '../api/recapNativeReviewApi';
import type {NativeRecordSelection,ReviewedMetadata} from '../api/recapNativePublicationApi';

export function sameMergeContext(a:RecapNativeReview,b:RecapNativeReview) {
 return a.source_revision_id===b.source_revision_id && a.native_context.revision_id===b.native_context.revision_id
  && a.native_context.source_authority_epoch===b.native_context.source_authority_epoch
  && a.native_context.source_admission.state===b.native_context.source_admission.state
  && (a.native_context.source_admission.state!=='admitted'||(b.native_context.source_admission.state==='admitted'&&a.native_context.source_admission.run_id===b.native_context.source_admission.run_id));
}
const normalize=(s:string)=>s.normalize('NFKC').trim().toLocaleLowerCase();
export function mergeIdentity(p:ExactRunCandidateProjection,review:RecapNativeReview,id:string) {
 const node=p.nodes.find(n=>n.candidateNodeId===id)!;
 const selection=review.native_context.selections.find(s=>s.candidate_node_id===id);
 if(!selection)throw new Error(`World comparison is missing for ${node.label}.`);
 const matches=selection.identity_matches;
 if(!matches)throw new Error(`The identity check for ${node.label} is unavailable. Reload before merging.`);
 if(matches.length>1)throw new Error(`Resolve the ambiguous World identity for ${node.label} before merging.`);
 if(matches.some(m=>![...m.matched_names,...m.matched_aliases].some(name=>normalize(name)===normalize(node.label))))throw new Error('The identity match no longer matches the reviewed name.');
 return matches[0]?.entity_id??null;
}
export function recapMergeSelections(p:ExactRunCandidateProjection,reviews:RecapNativeReview[]):NativeRecordSelection[] {
 const first=reviews[0];if(!first||reviews.some(r=>!sameMergeContext(first,r)))throw new Error('The World changed. Close and reopen Merge.');
 function metadata(witnesses:CandidateReadEvidence[]):ReviewedMetadata {
  const evidence=supportEvidenceIds(p,first,witnesses);
  if(!evidence.length)throw new Error('A displayed claim has no verified supporting passage. Nothing was published.');
  return {evidence_ref_ids:evidence,visibility:{kind:'labels_any',labels:['dungeonbuddy.visibility:gm']},epistemic_basis:'asserted',claim_mode:'dungeonbuddy.claim:fact',standing:'provisional',temporal_scope:{kind:'domain_ref',valid_from:null,valid_until:null,schema_term:'dungeonbuddy.time:fictional_anchor_v1',payload:{episode:p.sessionId,qualified:true}},domain_metadata:[]};
 }
 const nodes:NativeRecordSelection[]=p.nodes.map(n=>{
  const review=reviews.find(r=>r.native_context.selections.some(s=>s.candidate_node_id===n.candidateNodeId));
  if(!review)throw new Error('A displayed object has no current World comparison.');
  const entity=mergeIdentity(p,review,n.candidateNodeId),m=metadata(n.evidence);
  return {kind:'node',record_id:n.candidateNodeId,action:entity?'use_existing':'create',entity_id:entity,facts:([{field:'label',index:null,metadata:m},{field:'node_type',index:null,metadata:m},...(n.description?[{field:'description' as const,index:null,metadata:m}]:[])]),metadata:null};
 });
 const ids=new Set(nodes.map(n=>n.record_id));
 return [...nodes,...p.edges.map(e=>{
  if(!ids.has(e.fromCandidateId)||!ids.has(e.toCandidateId))throw new Error('A relationship has an unresolved endpoint. Nothing was published.');
  return {kind:'edge' as const,record_id:e.candidateEdgeId,action:'create' as const,entity_id:null,facts:[],metadata:metadata(e.evidence)};
 })];
}

export function witnessByteRange(p:ExactRunCandidateProjection,w:CandidateReadEvidence) {
 const lines=p.sourceMarkdown.match(/[^\r\n\v\f\u001c-\u001e\u0085\u2028\u2029]*(?:\r\n|[\r\n\v\f\u001c-\u001e\u0085\u2028\u2029]|$)/g)?.filter(Boolean)??[];
 if(!Number.isInteger(w.startLine)||!Number.isInteger(w.endLine)||w.startLine<1||w.endLine<w.startLine||w.endLine>lines.length)throw new Error('The candidate source passage has invalid line bounds.');
 const start=new TextEncoder().encode(lines.slice(0,w.startLine-1).join('')).length;
 const selected=lines.slice(w.startLine-1,w.endLine);
 const text=selected.join('').replace(/[\r\n]+$/,'');
 if(text!==w.paragraphText)throw new Error('The candidate paragraph no longer matches its frozen source.');
 return {start,end:start+new TextEncoder().encode(text).length,boundEnd:start+new TextEncoder().encode(lines.slice(w.startLine-1,w.endLine).join('')).length,text};
}
export function supportEvidenceIds(p:ExactRunCandidateProjection,r:RecapNativeReview,witnesses:CandidateReadEvidence[]) {
 return r.native_context.source_evidence.filter(row=>row.opening.status==='available'&&witnesses.some(w=>{const span=witnessByteRange(p,w);return row.opening.status==='available'&&span.start<=row.opening.span_start_byte&&row.opening.span_end_byte<=span.boundEnd;})).map(row=>row.evidence_ref_id);
}
