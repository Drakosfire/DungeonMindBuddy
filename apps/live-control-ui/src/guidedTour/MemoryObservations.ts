import {useMemo,useRef} from 'react';
import type {WorldAgentConversationHistoryResponse,SessionSummarySupport,SurfaceEvidenceCompletionV4} from '../api/types';
import {sessionCitationTarget} from '../shared/sessionEvidenceCitation';
import type {TourOwnerReading} from './GuidedTour';
import {samePin,type Walkthrough,type MemoryEntryEvidence} from './protocol';
const digest=(value:string)=>/^[a-f0-9]{64}$/.test(value);
/** Read the normal accepted history projection; this does not validate model claims or fetch evidence again. */
export function useSessionMemoryReading(history:WorldAgentConversationHistoryResponse|null,walkthrough:Walkthrough|null):TourOwnerReading|null {
 const baseline=useRef(new Map<string,number>()),seen=useRef(new Map<string,{observedAt:string;origin:'existing'|'acknowledged'}>());
 useMemo(()=>{
  if(!history?.conversation_id)return;
  const key=`${history.world_id}:${history.conversation_id}`;
  const completed=history.turns.filter(turn=>turn.lifecycle_status==='completed');
  if(!baseline.current.has(key))baseline.current.set(key,completed.reduce((max,turn)=>Math.max(max,turn.sequence),0));
  for(const turn of completed){const id=`${key}:${turn.turn_id}`;if(!seen.current.has(id))seen.current.set(id,{observedAt:new Date().toISOString(),origin:turn.sequence>baseline.current.get(key)!?'acknowledged':'existing'});}
 },[history]);
 const run=walkthrough?.bindings.run,plan=walkthrough?.bindings.plan;
 if(!walkthrough||!run||!plan)return null;
 const reflection=walkthrough.steps.reflection.evidence.filter(item=>item.target.objectId===run.objectId&&item.parent&&samePin(item.parent,plan)&&item.proof?.kind==='session-review')
  .sort((a,b)=>(b.proof?.kind==='session-review'?b.proof.reviewRevision:0)-(a.proof?.kind==='session-review'?a.proof.reviewRevision:0))[0];
 const review=reflection?.proof?.kind==='session-review'?reflection.proof:null;
 const unavailable:TourOwnerReading={step:'memory',target:reflection?.target??run,parent:plan,control:'memory',status:'unavailable',reason:'Save closing reflections, then open Buddy in Plan and ask about this Run’s saved notes and reflections. Open the resulting session citations. Generic citations or an uncited answer do not demonstrate this capability.'};
 if(!review||!history||history.world_id!==walkthrough.worldId||history.conversation_state!=='active'||!history.conversation_id||history.active_conversation_id!==history.conversation_id)return unavailable;
 for(const turn of [...history.turns].sort((a,b)=>b.sequence-a.sequence)){
  if(turn.lifecycle_status!=='completed'||!turn.assistant_text?.trim()||turn.provenance.world_id!==walkthrough.worldId||!('plan_context' in turn))continue;
  const completion=turn.plan_context?.completion;
  if(completion?.schema!=='dmb_surface_evidence_completion_v4'||!digest(completion.context_receipt_sha256))continue;
  const supports=(completion as SurfaceEvidenceCompletionV4).answer_segments.flatMap(segment=>segment.kind==='session_summary'?segment.supports:[])
   .filter(s=>s.source_kind==='session'&&s.object_id===run.objectId&&s.revision===String(review.reviewRevision)&&s.checkpoint_content_sha256===review.contentDigest);
  const entries:MemoryEntryEvidence[]=[];
  try{
   for(const support of supports){sessionCitationTarget(walkthrough.worldId,support);entries.push(entry(support));}
  }catch{continue;}
  if(!['scene_note','closing_reflections'].every(kind=>entries.some(e=>e.kind===kind))||new Set(entries.map(e=>e.packetDigest)).size!==1)continue;
  const observed=seen.current.get(`${history.world_id}:${history.conversation_id}:${turn.turn_id}`);
  if(!observed)continue;
  return {step:'memory',target:reflection!.target,parent:plan,control:'memory',status:'ready',observation:{step:'memory',target:reflection!.target,parent:plan,...observed,receiptId:`memory:${turn.turn_id}:${completion.context_receipt_sha256}`,proof:{kind:'session-memory',turnId:turn.turn_id,reviewRevision:review.reviewRevision,checkpointContentDigest:review.contentDigest,contextReceiptDigest:completion.context_receipt_sha256,entries}}};
 }
 return unavailable;
}
function entry(s:SessionSummarySupport):MemoryEntryEvidence {
 if(!['scene_note','closing_reflections'].includes(s.entry_kind)||!s.entry_identity||![s.entry_identity,s.body_sha256,s.owner_sha256].every(digest)||!Number.isSafeInteger(s.source_ordinal)||s.source_ordinal<0||s.entry_kind==='scene_note'&&!s.element_id||s.entry_kind==='closing_reflections'&&s.element_id!==null)throw new Error('Session citation has no exact entry identity.');
 return {kind:s.entry_kind,elementId:s.element_id,sourceOrdinal:s.source_ordinal,entryIdentity:s.entry_identity,bodyDigest:s.body_sha256,packetDigest:s.owner_sha256};
}
