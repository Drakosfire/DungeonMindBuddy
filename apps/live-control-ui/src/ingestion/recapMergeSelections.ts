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
 const matches=selection.alternatives.filter(a=>a.entity_result?.assertions?.some(f=>f.predicate==='dnd5e:name'&&typeof f.value?.value==='string'&&normalize(f.value.value)===normalize(node.label)));
 if(selection.alternatives.length>1)throw new Error(`Resolve the ambiguous World identity for ${node.label} before merging.`);
 // A non-exact advisory match must not be silently treated as new or existing.
 if(!matches.length&&selection.alternatives.length)throw new Error(`Review the possible World identity for ${node.label} before merging.`);
 if(matches[0]&&matches[0].status!=='supported_facts')throw new Error(`The World identity for ${node.label} lacks verified support.`);
 return matches[0]?.entity_id??null;
}
export function recapMergeSelections(p:ExactRunCandidateProjection,reviews:RecapNativeReview[]):NativeRecordSelection[] {
 const first=reviews[0];if(!first||reviews.some(r=>!sameMergeContext(first,r)))throw new Error('The World changed. Close and reopen Merge.');
 const lines=p.sourceMarkdown.split(/(?<=\n)/),starts=[0];
 for(const line of lines)starts.push(starts[starts.length-1]+new TextEncoder().encode(line).length);
 function metadata(witnesses:CandidateReadEvidence[]):ReviewedMetadata {
  const evidence=first.native_context.source_evidence.filter(row=>row.opening.status==='available'&&witnesses.some(w=>row.opening.status==='available'&&starts[w.startLine-1]<=row.opening.span_start_byte&&row.opening.span_end_byte<=starts[w.endLine])).map(row=>row.evidence_ref_id);
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
