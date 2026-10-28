import {renderHook} from '@testing-library/react';
import {expect,it} from 'vitest';
import {useSessionMemoryReading} from './MemoryObservations';
import type {WorldAgentConversationHistoryResponse,SurfaceEvidenceCompletionV4} from '../api/types';
import {createWalkthrough,reduceTour,validObservation,type TargetPin} from './protocol';
const runId='11111111-1111-4111-8111-111111111111',planId='22222222-2222-4222-8222-222222222222';
const plan:TargetPin={kind:'plan',worldId:'world',objectId:planId,revision:2,revisionId:'work-2',digest:'a'.repeat(64)};
const run:TargetPin={kind:'run',worldId:'world',objectId:runId,revision:7,digest:plan.digest};
function walkthrough(){
 let value=createWalkthrough('world','conks','walk','2026-10-28T00:00:00Z');value=reduceTour(value,{kind:'bind',pin:plan});value=reduceTour(value,{kind:'bind',pin:run,parent:plan});
 return reduceTour(value,{kind:'observe',observation:{step:'reflection',target:run,parent:plan,origin:'existing',observedAt:'2026-10-28T00:00:00Z',receiptId:'review',proof:{kind:'session-review',reviewRevision:4,checkpointRunRevision:7,contentRevision:0,contentRevisionId:null,contentDigest:'f'.repeat(64),commandId:null}}});
}
function completion():SurfaceEvidenceCompletionV4{
 return {schema:'dmb_surface_evidence_completion_v4',surface_id:'plan',context_receipt_sha256:'c'.repeat(64),answer_basis:'mixed_evidence',answer_context_status:'authored_grounded',citation_map:null,source_citations:[],native_source_citations:[],answer_segments:[{kind:'session_summary',text:'The route remains unresolved.',supports:[0,1].map(index=>({kind:'authored_excerpt',text:'Saved source text.',source_kind:'session',source_name:'Saved Run',object_id:runId,revision:'4',body_sha256:'b'.repeat(64),owner_sha256:'d'.repeat(64),source_handle:'q'+'e'.repeat(64),block_handle:'b'+'e'.repeat(64),partition_version:'markdown_source_blocks_v1',byte_start:0,byte_end:18,block_sha256:'b'.repeat(64),entry_identity:(index?'1':'2').repeat(64),source_ordinal:index,entry_kind:index?'closing_reflections':'scene_note',element_id:index?null:'scene',checkpoint_content_sha256:'f'.repeat(64)}))}]};
}
function history(sequence=1,c=completion()):WorldAgentConversationHistoryResponse{
 return {schema:'dmb_agent_conversation_history_v2',world_id:'world',conversation_state:'active',conversation_id:'conversation',active_conversation_id:'conversation',pointer_revision:1,next_before_sequence:null,turns:[{turn_id:`turn-${sequence}`,sequence,lifecycle_status:'completed',user_text:'What happened?',assistant_text:'The route remains unresolved.',provenance:{world_id:'world'},plan_context:{completion:c}}]} as WorldAgentConversationHistoryResponse;
}
it('recognizes a delivered typed answer pinned to saved notes and closing reflections',()=>{
 const value=walkthrough();const scope={worldId:'world',walkthroughId:'walk',epoch:0};const dispatches=new Map([['turn-2',scope]]);const first=history();const hook=renderHook(({h})=>useSessionMemoryReading(h,value,dispatches),{initialProps:{h:first}});
 expect(hook.result.current?.observation?.origin).toBe('existing');
 hook.rerender({h:history(2)});
 const observation=hook.result.current?.observation;
 expect(hook.result.current?.dispatchScope).toEqual(scope);expect(observation?.origin).toBe('acknowledged');expect(validObservation(observation,'world')).toBe(true);
 expect(observation?.proof).toMatchObject({kind:'session-memory',turnId:'turn-2',reviewRevision:4,checkpointContentDigest:'f'.repeat(64)});
 expect(JSON.stringify(observation)).not.toContain('Saved source text.');
});
it.each(['missing-reflections','wrong-review','wrong-checkpoint','wrong-run','untyped'] as const)('does not complete memory with %s support',scenario=>{
 const c=completion(),segment=c.answer_segments[0];if(segment.kind!=='session_summary')throw Error();
 if(scenario==='missing-reflections')segment.supports=segment.supports.slice(0,1);
 if(scenario==='wrong-review')segment.supports.forEach(s=>s.revision='3');
 if(scenario==='wrong-checkpoint')segment.supports.forEach(s=>s.checkpoint_content_sha256='e'.repeat(64));
 if(scenario==='wrong-run')segment.supports.forEach(s=>s.object_id=planId);
 if(scenario==='untyped')c.answer_segments=[{kind:'connective',text:'A confident answer with no session support.'} as never];
 const hook=renderHook(()=>useSessionMemoryReading(history(1,c),walkthrough()));
 expect(hook.result.current?.status).toBe('unavailable');expect(hook.result.current?.observation).toBeUndefined();
});
it('keeps a later-loaded older history page classified as an example',()=>{
 const value=walkthrough();const hook=renderHook(({h})=>useSessionMemoryReading(h,value),{initialProps:{h:history(5)}});
 hook.rerender({h:history(2)});expect(hook.result.current?.observation?.origin).toBe('existing');
});
it('does not accept a foreign World history projection',()=>{
 const h=history();h.world_id='another-world';const hook=renderHook(()=>useSessionMemoryReading(h,walkthrough()));
 expect(hook.result.current?.observation).toBeUndefined();
});

it('does not infer fresh dispatch merely from a newly delivered sequence',()=>{const value=walkthrough();const hook=renderHook(({h})=>useSessionMemoryReading(h,value),{initialProps:{h:history(1)}});hook.rerender({h:history(2)});expect(hook.result.current?.observation?.origin).toBe('existing');});
