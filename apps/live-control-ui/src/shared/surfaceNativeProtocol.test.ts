import {it,expect} from 'vitest';
import wire from '../test/surface-native-http.json';
import {isSurfaceNativeReceipt,isSurfaceNativeCompletion,isSurfaceNativeContext} from './surfaceNativeProtocol';
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

import authoredWire from '../test/surface-native-authored.json';
import {isNativePlanQuery,isNativeGraphQuery} from './nativeStatementAnswerProtocol';
const authoredContext=()=>structuredClone(authoredWire);
const buildWork=(v:unknown):v is SurfaceNativeWorkContextV1=>typeof v==='object'&&v!==null&&'surface_id' in v&&v.surface_id==='build';
it('renders the actual APP-read and SDK-writer human target wire without turning it into search or historical Plan evidence',()=>{
  const c=authoredContext(),q=c.receipt.native_query;
  expect(q.discovered_entity_ids).toEqual([]);expect(q.matches).toEqual([]);expect(q.assertion_matches).toEqual([]);
  expect(q.authored_targets[0]!.matches.length).toBeGreaterThan(0);
  expect(q.authored_targets[0]!.assertion_matches.length).toBeGreaterThan(0);
  expect(isNativePlanQuery(q,c.receipt.work_context.source_basis.world_id)).toBe(false);
  expect(isNativeGraphQuery(q,c.receipt.work_context.source_basis.world_id)).toBe(true);
  expect(isSurfaceNativeReceipt(c.receipt,buildWork)).toBe(true);
  expect(isSurfaceNativeCompletion(c.completion,c.receipt as SurfaceNativeContextReceiptV1)).toBe(true);
});
it.each(['origin','node','members','duplicate','missing-statement','missing-assertion','hidden-gap','extra'])('refuses altered authored target presentation: %s',mutation=>{
  const c=authoredContext(),target=c.receipt.native_query.authored_targets[0]!;
  if(mutation==='origin')target.selection_revision_id='';
  else if(mutation==='node')target.node_id='ent:other';
  else if(mutation==='members')target.assertion_matches[0]!.discovered_entity_ids.push(target.node_id);
  else if(mutation==='duplicate')c.receipt.native_query.authored_targets.push(structuredClone(target));
  else if(mutation==='missing-statement')target.matches=[];
  else if(mutation==='missing-assertion')target.assertion_matches=[];
  else if(mutation==='hidden-gap'){target.status='partial';target.gap_codes=[];}
  else Object.assign(target,{provider_attempt_id:'invented-model-origin'});
  expect(isSurfaceNativeReceipt(c.receipt,buildWork)&&isSurfaceNativeCompletion(c.completion,c.receipt as SurfaceNativeContextReceiptV1)).toBe(false);
});


import buildWire from '../test/surface-native-build-http.json';
it('accepts the actual Build proposal acknowledgement only on its shared Build context',()=>{
  const c=structuredClone(buildWire.proposal_wire.response.knowledge_context);
  expect(isSurfaceNativeContext(c,buildWork,()=>true)).toBe(true);
  expect(isSurfaceNativeCompletion(c.completion,c.receipt as SurfaceNativeContextReceiptV1)).toBe(false);
  const plan=context();
  Object.assign(plan,{completion:{...c.completion,context_receipt_sha256:plan.receipt.context_receipt_sha256}});
  expect(isSurfaceNativeContext(plan,work,()=>true)).toBe(false);
  c.completion.context_receipt_sha256='0'.repeat(64);
  expect(isSurfaceNativeContext(c,buildWork,()=>true)).toBe(false);
});

it('accepts the actual native image preparation acknowledgement only for Build',()=>{
  const c=structuredClone(buildWire.image_context);
  expect(isSurfaceNativeContext(c,buildWork,()=>true)).toBe(true);
  expect(isSurfaceNativeCompletion(c.completion,c.receipt as SurfaceNativeContextReceiptV1)).toBe(false);
  const plan=context();
  Object.assign(plan,{completion:{...c.completion,context_receipt_sha256:plan.receipt.context_receipt_sha256}});
  expect(isSurfaceNativeContext(plan,work,()=>true)).toBe(false);
});
it.each(['root','basis','extra','producer'])('refuses changed native image acknowledgement: %s',mutation=>{
  const c=structuredClone(buildWire.image_context);
  if(mutation==='root')c.completion.context_receipt_sha256='0'.repeat(64);
  if(mutation==='basis')c.completion.answer_basis='prepared_page_proposal';
  if(mutation==='producer')c.completion.provider_attempt_id='not-an-id';
  if(mutation==='extra')Object.assign(c.completion,{native_assertion_citations:[]});
  expect(isSurfaceNativeContext(c,buildWork,()=>true)).toBe(false);
});
