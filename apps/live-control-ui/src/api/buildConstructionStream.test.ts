import {describe,it,expect,vi} from 'vitest';
import {readBuildConstructionStream,ConstructionStreamError,type BuildConstructionProgress} from './buildConstructionStream';
import type {WorldBuildAgentTurnRequestV1} from './types';
const basis={world_id:'world',document_id:'doc',registry_revision:1,content_sha256:'a'.repeat(64),visibility:'internal',draft_sha256:'b'.repeat(64),editor_sha256:'c'.repeat(64),caret:1,draft_generation:0,selection_generation:0};
const request={turn_id:'client',build_write_capability:{idempotency_key:'action',conversation_id:'conversation',basis}} as unknown as WorldBuildAgentTurnRequestV1;
const progress={schema:'dmb_build_construction_v1',action_id:'action',reservation_sha256:'d'.repeat(64),conversation_id:'conversation',basis,
  origin:{client_turn_id:'client',durable_turn_id:'durable',turn_attempt:1,broker_operation_id:'op:1',arguments_sha256:'e'.repeat(64)},
  provider_attempt_id:'provider',sequence:1,status:'building',markdown:'| A |\n| --- |\n| 雪😀 |\n'} as BuildConstructionProgress;
const frame=(kind:string,extra:object)=>({schema:'dmb_build_turn_stream_v1',client_turn_id:'client',kind,...extra});
function response(events:unknown[],size=13,cancel=vi.fn()){
 const bytes=new TextEncoder().encode(events.map(e=>'data: '+JSON.stringify(e)+'\r\n\r\n').join(''));
 let cursor=0;
 return new Response(new ReadableStream({pull(controller){if(cursor>=bytes.length){controller.close();return;}controller.enqueue(bytes.slice(cursor,cursor+size));cursor+=size;},cancel}),{headers:{'content-type':'text/event-stream'}});
}
describe('one-request construction observation',()=>{
 it.each([1,2,11,4096])('handles UTF8 and SSE partitions of %s bytes',async size=>{
  const seen=vi.fn();const result={schema:'answer'};
  expect(await readBuildConstructionStream(response([frame('construction',{progress}),frame('result',{response:result})],size),request,seen)).toEqual(result);
  expect(seen).toHaveBeenCalledExactlyOnceWith(progress);
 });
 it('rejects foreign identity/basis and stale sequences without retargeting',async()=>{
  const seen=vi.fn();
  const p=(changes:object)=>frame('construction',{progress:{...progress,...changes}});
  await readBuildConstructionStream(response([p({sequence:1}),p({sequence:1}),p({sequence:2,basis:{...basis,document_id:'other'}}),
   p({sequence:3,origin:{...progress.origin,turn_attempt:2}}),p({sequence:2}),frame('result',{response:{schema:'answer'}})]),request,seen);
  expect(seen.mock.calls.map(call=>call[0].sequence)).toEqual([1,2]);
 });
 it('never retries EOF or a terminal error',async()=>{
  await expect(readBuildConstructionStream(response([frame('construction',{progress})]),request,vi.fn())).rejects.toThrow('stopped');
  await expect(readBuildConstructionStream(response([frame('error',{status:409,detail:{code:'stale'}})]),request,vi.fn())).rejects.toBeInstanceOf(ConstructionStreamError);
 });
 it('checks the access session before delivery and discards foreign terminal',async()=>{
  const seen=vi.fn();
  await expect(readBuildConstructionStream(response([frame('construction',{progress})]),request,seen,()=>{throw new Error('revoked');})).rejects.toThrow('revoked');
  expect(seen).not.toHaveBeenCalled();
  await expect(readBuildConstructionStream(response([{...frame('result',{response:{}}),client_turn_id:'other'}]),request,seen)).rejects.toThrow('another request');
 });
 it('preview failure cannot discard an observed final outcome',async()=>{
  const result={schema:'answer'};
  expect(await readBuildConstructionStream(response([frame('construction',{progress}),frame('result',{response:result})]),request,()=>{throw new Error('retired');})).toEqual(result);
 });
});

import {createHash,webcrypto} from 'node:crypto';
import type {BuildPlanConstructionProgress} from './buildConstructionStream';
const snapshot={schema:'dmb_build_draft_snapshot_v1',draft_markdown:'Author page 雪😀',draft_sha256:'a'.repeat(64)};
const planRequest={...request,owner_scope:{world_id:'world'},build_draft_context:{snapshot}} as unknown as WorldBuildAgentTurnRequestV1;
const planProgress:BuildPlanConstructionProgress={schema:'dmb_build_plan_construction_v1',placement_id:'action',basis,
 world_id:'world',conversation_id:'conversation',client_turn_id:'client',durable_turn_id:'11111111-1111-4111-8111-111111111111',turn_attempt:1,
 working_snapshot_sha256:createHash('sha256').update(JSON.stringify(Object.fromEntries(Object.entries(snapshot).sort(([a],[b])=>a.localeCompare(b))))).digest('hex'),
 provider_attempt_id:'22222222-2222-4222-8222-222222222222',sequence:1,status:'building',steps:[{text:'Discuss the hinge 雪😀.',kind:'discuss'}]};
it.each([1,11,4096])('reads exact-bound typed plan prefixes across %s byte partitions',async size=>{
 Object.defineProperty(globalThis,'crypto',{value:webcrypto,configurable:true});
 const seen=vi.fn();const next={...planProgress,sequence:2,steps:[...planProgress.steps,{text:'Prepare a proposed check.',kind:'prepare_insertion'}]};
 await readBuildConstructionStream(response([frame('construction',{progress:planProgress}),frame('construction',{progress:next}),frame('result',{response:{schema:'answer'}})],size),planRequest,seen);
 expect(seen.mock.calls.map(c=>c[0].steps.length)).toEqual([1,2]);
});
it('rejects foreign, rewritten, malformed and speculative plan rows without poisoning final reconciliation',async()=>{
 Object.defineProperty(globalThis,'crypto',{value:webcrypto,configurable:true});const seen=vi.fn();
 const p=(changes:object)=>frame('construction',{progress:{...planProgress,...changes}});
 await readBuildConstructionStream(response([p({world_id:'foreign'}),p({working_snapshot_sha256:'f'.repeat(64)}),p({extra:true}),p({status:'ready'}),p({sequence:1}),
 p({sequence:2,steps:[{text:'Changed prefix',kind:'discuss'}]}),p({sequence:2,provider_attempt_id:'33333333-3333-4333-8333-333333333333'}),
 p({sequence:2,status:'incomplete'}),p({sequence:3}),frame('result',{response:{schema:'answer'}})]),planRequest,seen);
 expect(seen.mock.calls.map(c=>c[0].status)).toEqual(['building','incomplete']);
});
it('a preview hash failure cannot discard the real terminal reply',async()=>{
 Object.defineProperty(globalThis,'crypto',{value:{subtle:{digest:vi.fn().mockRejectedValue(new Error('unavailable'))}},configurable:true});
 try{
  const seen=vi.fn();const final={schema:'answer'};
  expect(await readBuildConstructionStream(response([frame('construction',{progress:planProgress}),frame('result',{response:final})]),planRequest,seen)).toEqual(final);
  expect(seen).not.toHaveBeenCalled();
 }finally{Object.defineProperty(globalThis,'crypto',{value:webcrypto,configurable:true});}
});

it('observes an actual outcome before rows and rejects rewritten or speculative outcomes while retaining the final result',async()=>{
 Object.defineProperty(globalThis,'crypto',{value:webcrypto,configurable:true});const seen=vi.fn();
 const p={...planProgress,schema:'dmb_build_plan_construction_v2',objective:'Develop a useful shop scene 雪😀.',steps:[]};
 const result={schema:'answer'};
 expect(await readBuildConstructionStream(response([
  frame('construction',{progress:{...p,objective:null,steps:planProgress.steps}}),
  frame('construction',{progress:p}),
  frame('construction',{progress:{...p,sequence:2,objective:'Changed outcome'}}),
  frame('construction',{progress:{...p,sequence:2,steps:planProgress.steps}}),
  frame('construction',{progress:{...p,sequence:3,objective:null,steps:undefined}}),
  frame('result',{response:result}),
 ],1),planRequest,seen)).toEqual(result);
 expect(seen.mock.calls.map(c=>[c[0].objective,c[0].steps.length])).toEqual([[p.objective,0],[p.objective,1]]);
});

it('observes required selected booleans and rejects missing, coerced or rewritten choices',async()=>{
 Object.defineProperty(globalThis,'crypto',{value:webcrypto,configurable:true});const seen=vi.fn();
 const row={text:'Discuss first.',kind:'discuss',selected:true};
 const p={...planProgress,schema:'dmb_build_plan_construction_v3',objective:'Review first; defer writing.',steps:[row]};
 const next={...p,sequence:2,steps:[row,{text:'Write later.',kind:'prepare_insertion',selected:false}]};
 const result={schema:'answer'};
 expect(await readBuildConstructionStream(response([
  ...[undefined,null,'false',0].map(selected=>frame('construction',{progress:{...p,steps:[{...row,selected}]}})),
  frame('construction',{progress:p}),
  frame('construction',{progress:{...p,sequence:2,steps:[{...row,selected:false}]}}),
  frame('construction',{progress:next}),frame('result',{response:result}),
 ],1),planRequest,seen)).toEqual(result);
 expect(seen.mock.calls.map(c=>c[0].steps.map((r:{selected:boolean})=>r.selected))).toEqual([[true],[true,false]]);
});
