import {beforeEach,expect,it} from 'vitest';
import type {AcceptThreatDraftMechanicsResponseV1,ReadStatblockCandidateResponseV1,ThreatDraftV2} from '../api/types';
import type {StoredGenerationAttempt} from '../surface/modules/statblockDraftScope';
import {persistGenerationAttempt,readGenerationAttempt,settleGenerationAttempt} from '../surface/modules/statblockDraftScope';
import {generationReading} from './GenerationObservations';
import {createWalkthrough,decodeWalkthrough,generationScope,reduceTour,sameGenerationScope,type TargetPin} from './protocol';
import {readWalkthrough,writeWalkthrough} from './storage';
import fixture from '../../../../tests/fixtures/statblocks/v1/candidate-response.json';
const plan:TargetPin={kind:'plan',worldId:'conks',objectId:'plan',revision:2,revisionId:'wr2',digest:'a'.repeat(64)};
const stamp='2026-10-28T00:00:00Z';
const locator={provider:'dungeonmind' as const,statblock_id:'sb',revision_id:'r1',contract:'statblocks',contract_version:'1',definition_digest:'sha256:'+'b'.repeat(64)};
function started(){let walk=createWalkthrough('conks','conks','tour',stamp);walk=reduceTour(walk,{kind:'bind',pin:plan});return reduceTour(walk,{kind:'move',index:3});}
function shapes(){const walk=started(),scope=generationScope(walk)!;
 const attempt:StoredGenerationAttempt={schema:'dmb_sbw_generation_attempt_v1',draft_id:'draft',expected_draft_version:1,client_request_id:'request',candidate_id:fixture.candidate_id,tour_scope:scope,tour_dispatch_instance_id:'first-mount'};
 const candidate:ReadStatblockCandidateResponseV1={schema:'dmb_statblock_candidate_read_v1',status:'active',candidate_id:fixture.candidate_id,source_draft_id:'draft',source_draft_version:1,candidate:{...fixture,generation_receipt:{request_id:'request',provider:'openai',model:'configured-model',prompt_version:'v1',schema_version:'v1',schema_fingerprint:'schema',generated_at:stamp,caller_scope:'workbench',provider_request_id:'provider-request',provider_response_id:'provider-response'}} as NonNullable<ReadStatblockCandidateResponseV1['candidate']>};
 const draft={schema:'dmb_threat_draft_v2',scope_mode:'world',world_id:'conks',campaign_id:null,draft_id:'draft',version:2,candidate_refs:[{candidate_id:fixture.candidate_id,generated_from_draft_version:1,request_id:'request',status:'accepted_source',created_at:stamp}],workflow_state:'mechanics_saved',accepted_mechanics_ref:{...locator,accepted_at:stamp,accepted_from_candidate_id:fixture.candidate_id,accepted_from_draft_version:1}} as ThreatDraftV2;
 const accepted:AcceptThreatDraftMechanicsResponseV1={schema:'dmb_accept_threat_draft_mechanics_response_v1',draft_id:'draft',operation_id:'accept-operation',result_label:'mechanics_saved',locator};
 return {walk,scope,attempt,candidate,draft,accepted};
}
beforeEach(()=>localStorage.clear());
it('credits recovered original provider candidate only after exact explicit save and retains proof through reload',()=>{
 const x=shapes(),scope={mode:'world' as const,worldId:'conks',campaignId:null};
 persistGenerationAttempt(scope,{...x.attempt,candidate_id:null});
 expect(settleGenerationAttempt(scope,readGenerationAttempt(scope)!,x.draft,x.candidate.candidate_id)).toBe(true);
 const restored=readGenerationAttempt(scope)!;expect(restored.tour_scope).toEqual(x.scope);
 const reading=generationReading(restored,x.draft,x.candidate,x.accepted,true,true,'reopened-mount')!;
 expect(reading.observation?.origin).toBe('acknowledged');
 const completed=reduceTour(x.walk,{kind:'observe',observation:reading.observation!});expect(completed.steps.generation.state).toBe('completed');
 expect(decodeWalkthrough(JSON.stringify(completed),'conks')).toEqual(completed);
 writeWalkthrough(localStorage,completed,null);expect(readWalkthrough(localStorage,'conks')?.record.steps.generation.evidence[0].proof).toMatchObject({kind:'creature-generation',dispatchInstanceId:'first-mount',acceptedInstanceId:'reopened-mount',locator});
});
it.each(['no-save','no-reopen','same-instance','wrong-candidate','wrong-request','wrong-version','wrong-world','fixture-receipt','wrong-locator','no-attribution'] as const)('does not credit %s',kind=>{
 const x=shapes();let reopened=true,instance='second';
 if(kind==='no-save')x.accepted.result_label='server_committed_reference_pending';
 if(kind==='no-reopen')reopened=false;
 if(kind==='same-instance')instance='first-mount';
 if(kind==='wrong-candidate')x.candidate.candidate_id='other';
 if(kind==='wrong-request')x.candidate.candidate!.generation_receipt!.request_id='other';
 if(kind==='wrong-version')x.candidate.source_draft_version=2;
 if(kind==='wrong-world')x.draft.world_id='other';
 if(kind==='fixture-receipt')x.candidate.candidate!.generation_receipt!.provider_response_id=null;
 if(kind==='wrong-locator')x.accepted.locator={...locator,revision_id:'other'};
 if(kind==='no-attribution')delete x.attempt.tour_scope;
 expect(generationReading(x.attempt,x.draft,x.candidate,x.accepted,reopened,true,instance)?.observation).toBeUndefined();
});
it('rejects stale queued acknowledgments after step departure/return, Plan change, pause and restart',()=>{
 const x=shapes(),observation=generationReading(x.attempt,x.draft,x.candidate,x.accepted,true,true,'second')!.observation!;
 const departed=reduceTour(reduceTour(x.walk,{kind:'move',index:4}),{kind:'move',index:3});
 const paused=reduceTour(reduceTour(x.walk,{kind:'phase',phase:'paused'}),{kind:'phase',phase:'running'});
 const changed=reduceTour(x.walk,{kind:'bind',pin:{...plan,revision:3,revisionId:'wr3',digest:'c'.repeat(64)}});
 const restarted={...x.walk,id:'other-tour'};
 for(const stale of [departed,paused,changed,restarted]){expect(sameGenerationScope(generationScope(stale),x.scope)).toBe(false);expect(reduceTour(stale,{kind:'observe',observation}).steps.generation.state).not.toBe('completed');}
});
it('observations do not invalidate a pending dispatch, and retries cannot rewrite attribution',()=>{
 const x=shapes(),owner={mode:'world' as const,worldId:'conks',campaignId:null};
 const unavailable=reduceTour(x.walk,{kind:'disposition',step:'generation',state:'unavailable',reason:'Still pending.'});expect(generationScope(unavailable)).toEqual(x.scope);
 const attempt={...x.attempt,candidate_id:null};persistGenerationAttempt(owner,attempt);
 expect(()=>persistGenerationAttempt(owner,{...attempt,tour_scope:{...x.scope,dispatchRevision:99}})).toThrow('attribution');
 expect(()=>persistGenerationAttempt(owner,{...attempt,tour_dispatch_instance_id:'another'})).toThrow('attribution');
 expect(readGenerationAttempt(owner)).toEqual(attempt);
});
