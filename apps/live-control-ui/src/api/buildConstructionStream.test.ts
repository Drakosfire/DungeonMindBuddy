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
