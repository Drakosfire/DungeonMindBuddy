import {it,expect} from 'vitest';
import wire from '../test/surface-native-http.json';
import {isSurfaceNativeReceipt,isSurfaceNativeCompletion} from './surfaceNativeProtocol';
import type {SurfaceNativeContextReceiptV1,SurfaceNativeWorkContextV1} from '../api/types';
// Captured from the real provider-free Plan HTTP/APP/Core/SDK boundary test.
const context=()=>structuredClone(wire.context);
const work=(v:unknown):v is SurfaceNativeWorkContextV1=>typeof v==='object'&&v!==null&&'surface_id' in v&&v.surface_id==='plan';
it('consumes the actual shared HTTP wire without fabricating a historical Plan receipt',()=>{
  const c=context();expect(isSurfaceNativeReceipt(c.receipt,work)).toBe(true);
  expect(isSurfaceNativeCompletion(c.completion,c.receipt as SurfaceNativeContextReceiptV1)).toBe(true);
});
it.each(['producer','root','revision','assertion','unsupported','foreign-surface','legacy','extra','empty','duplicate'])('refuses changed shared answer presentation: %s',mutation=>{
  const c=context(),answer=c.completion,cite=answer.native_assertion_citations[0]!;
  if(mutation==='producer')cite.provider_attempt_id='00000000-0000-4000-8000-000000000001';
  if(mutation==='root')cite.context_receipt_sha256='0'.repeat(64);
  if(mutation==='revision')cite.read_revision_id='rev:foreign';
  if(mutation==='assertion')cite.assertion_sha256='0'.repeat(64);
  if(mutation==='unsupported')answer.native_assertion_citations=[];
  if(mutation==='foreign-surface')answer.surface_id='play';
  if(mutation==='legacy')Object.assign(answer,{schema:'dmb_surface_evidence_completion_v7'});
  if(mutation==='extra')Object.assign(answer,{citation_map:null});
  if(mutation==='empty')answer.answer_segments=[];
  if(mutation==='duplicate')answer.native_assertion_citations.push({...cite});
  expect(isSurfaceNativeCompletion(answer,c.receipt as SurfaceNativeContextReceiptV1)).toBe(false);
});
it.each(['old-query','foreign-world','epoch','provider-budget','extra-root','extra-query','duplicate-history'])('refuses changed receipt shape: %s',mutation=>{
  const c=context(),r=c.receipt;
  if(mutation==='old-query')Object.assign(r.native_query,{schema:'dmb_native_plan_query_v1'});
  if(mutation==='foreign-world')r.source_authority.managed_world_id='foreign';
  if(mutation==='epoch')r.native_query.authority.acquisition_epoch++;
  if(mutation==='provider-budget')r.assembled_input.context_window_limit=1;
  if(mutation==='extra-root')Object.assign(r,{graph_capability:null});
  if(mutation==='extra-query')Object.assign(r.native_query,{fallback_graph_revision:'old'});
  if(mutation==='duplicate-history')r.assembled_input.included_history=[{turn_id:wire.source.turn_id,answer_sha256:'a'.repeat(64)},{turn_id:wire.source.turn_id,answer_sha256:'a'.repeat(64)}];
  expect(isSurfaceNativeReceipt(r,work)).toBe(false);
});
