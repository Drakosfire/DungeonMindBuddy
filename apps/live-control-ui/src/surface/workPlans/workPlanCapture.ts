import type {WorldBuildAgentTurnRequestV1,WorldAgentConversationHistoryTurn,ConversationCollaboration} from '../../api/types';
import {getWorkPlanRecord,planObjective,type WorkStep} from '../../api/conversationWorkPlanApi';
import {canonical} from '../../shared/sourcePassageProtocol';
import {placementDigest,stagePlacement} from './workPlanPlacement';
import type {WorkPlanReference} from './workPlanReference';

/** Join the validated terminal response to its durable history identity before retiring the pending request. */
export async function captureWorkPlan(request:WorldBuildAgentTurnRequestV1,turn:WorldAgentConversationHistoryTurn,
 conversationId:string,pointerRevision:number,idempotencyKey:string,answer:string,
 collaboration:Extract<ConversationCollaboration,{kind:'plan'}>,retainedCollaboration:unknown){
 const cap=request.build_write_capability,basis=turn.provenance.primary_work;
 if(!cap||cap.conversation_id!==conversationId||cap.expected_pointer_revision!==pointerRevision
  ||!('idempotency_key' in turn)||turn.idempotency_key!==idempotencyKey||turn.lifecycle_status!=='completed'
  ||turn.user_text!==request.message||turn.assistant_text!==answer||canonical(collaboration)!==canonical(retainedCollaboration)
  ||turn.provenance.world_id!==request.owner_scope.world_id||turn.provenance.surface_id!=='build'
  ||basis.kind!=='build'||basis.object_id!==request.primary_work.object_id||basis.revision!==String(request.primary_work.expected_revision)
  ||basis.content_sha256!==request.primary_work.expected_content_sha256||cap.basis.selection)
  throw new Error('The completed plan needs an explicit position on its original page.');
 const reference:WorkPlanReference={schema:'dmb_surface_work_plan_ref_v1',world_id:request.owner_scope.world_id,
  document_id:request.primary_work.object_id,conversation_id:conversationId,source_turn_id:turn.turn_id,
  source_answer_sha256:await placementDigest(answer),title:'Work plan'};
 const record=await getWorkPlanRecord({worldId:reference.world_id,documentId:reference.document_id,conversationId,turnId:turn.turn_id,sourceSha256:reference.source_answer_sha256});
 const saved=record.plan,roots=saved?.schema==='dmb_reviewed_work_plan_v3'?saved.root_references:record.sourceReferences.length?record.sourceReferences:undefined;
 const rows:WorkStep[]=saved?.steps??collaboration.steps.map(step=>({...step,step_id:crypto.randomUUID(),selected:true}));
 return stagePlacement(reference,cap.basis,pointerRevision,rows,saved?.revision??0,localStorage,navigator.locks,saved?planObjective(saved):'objective' in collaboration?collaboration.objective:'',roots);
}
