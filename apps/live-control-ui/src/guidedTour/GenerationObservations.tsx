import {createContext,useContext,type ReactNode} from 'react';
import {type TargetPin} from './protocol';
import type {AcceptThreatDraftMechanicsResponseV1,ReadStatblockCandidateResponseV1,ThreatDraft} from '../api/types';
import type {StoredGenerationAttempt} from '../surface/modules/statblockDraftScope';
import {useGuidedTour,useTourOwnerReading,type TourOwnerReading} from './GuidedTour';
import {validGenerationScope} from './protocol';

const PlanContext=createContext<TargetPin|null>(null);
export const useGenerationPlan=()=>useContext(PlanContext);
export function GenerationPlanProvider({pin,children}:{pin:TargetPin|null;children:ReactNode}){return <PlanContext.Provider value={pin}>{children}</PlanContext.Provider>;}
/** Consumes owner-validated candidate membership and acceptance; performs no domain command. */
export function generationReading(attempt:StoredGenerationAttempt|null,draft:ThreatDraft|null,candidate:ReadStatblockCandidateResponseV1|null,accepted:AcceptThreatDraftMechanicsResponseV1|null,reopened:boolean,current:boolean,acceptedInstanceId:string):TourOwnerReading|null {
 const scope=attempt?.tour_scope;
 if(!scope||!validGenerationScope(scope))return null;
 const receipt=candidate?.candidate?.generation_receipt,ref=draft?.accepted_mechanics_ref;
 const member=!!attempt&&!!draft&&draft.world_id===scope.worldId&&draft.draft_id===attempt.draft_id
  &&candidate?.status==='active'&&candidate.source_draft_id===draft.draft_id&&candidate.source_draft_version===attempt.expected_draft_version
  &&candidate.candidate_id===attempt.candidate_id&&candidate.candidate?.candidate_id===attempt.candidate_id
  &&draft.candidate_refs.some(r=>r.candidate_id===attempt.candidate_id&&r.request_id===attempt.client_request_id&&r.generated_from_draft_version===attempt.expected_draft_version);
 const generated=member&&!!receipt&&receipt.request_id===attempt.client_request_id&&!!receipt.provider.trim()&&!!receipt.model.trim()
  &&!!receipt.provider_request_id?.trim()&&!!receipt.provider_response_id?.trim()&&Number.isFinite(Date.parse(receipt.generated_at));
 const saved=generated&&draft?.workflow_state==='mechanics_saved'&&accepted?.draft_id===draft.draft_id&&accepted.result_label==='mechanics_saved'&&!!accepted.operation_id&&!!accepted.locator&&!!ref
  &&ref.accepted_from_candidate_id===attempt.candidate_id&&ref.accepted_from_draft_version===attempt.expected_draft_version
  &&(['provider','statblock_id','revision_id','contract','contract_version','definition_digest'] as const).every(k=>accepted.locator![k]===ref[k])&&Number.isFinite(Date.parse(ref.accepted_at));
 const ready=!!saved&&reopened&&!!attempt.tour_dispatch_instance_id&&attempt.tour_dispatch_instance_id!==acceptedInstanceId;
 return {step:'generation',target:scope.plan,generationScope:scope,control:'generation',status:ready?'ready':'unavailable',reason:ready?undefined:!reopened?'Navigate away and reopen Statblocks to recover this same generation attempt.':!generated?'Recover the original generation request and its provider candidate through Statblocks.':'Review, validate and explicitly Accept/Save the recovered candidate. A saved mechanics receipt is required.',
  ...(ready&&accepted?.locator&&receipt&&ref?{observation:{step:'generation',target:scope.plan,origin:current?'acknowledged':'existing',observedAt:ref.accepted_at,receiptId:`generation:${attempt.client_request_id}:${accepted.operation_id}`,proof:{kind:'creature-generation',scope,dispatchInstanceId:attempt.tour_dispatch_instance_id!,acceptedInstanceId,providerRequestId:receipt.provider_request_id!,providerResponseId:receipt.provider_response_id!,draftId:attempt.draft_id,sourceVersion:attempt.expected_draft_version,requestId:attempt.client_request_id,candidateId:attempt.candidate_id!,provider:receipt.provider,model:receipt.model,generatedAt:receipt.generated_at,acceptOperationId:accepted.operation_id,locator:accepted.locator}}}:{})};
}
export function GenerationTourObservation(props:{attempt:StoredGenerationAttempt|null;draft:ThreatDraft|null;candidate:ReadStatblockCandidateResponseV1|null;accepted:AcceptThreatDraftMechanicsResponseV1|null;reopened:boolean;acceptedInstanceId:string}){
 const tour=useGuidedTour();
 useTourOwnerReading(generationReading(props.attempt,props.draft,props.candidate,props.accepted,props.reopened,tour?.isGenerationScopeCurrent(props.attempt?.tour_scope??null)??false,props.acceptedInstanceId));
 return null;
}
