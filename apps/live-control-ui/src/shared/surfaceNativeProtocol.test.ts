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


it('adopts V4 object navigation while preserving exact authored-target citation validation',()=>{
  const c=authoredContext();
  const q={...c.receipt.native_query,schema:'dmb_native_graph_query_v4',object_matches:[]};
  const receipt={...c.receipt,native_query:q};
  const world=c.receipt.work_context.source_basis.world_id;
  expect(isNativeGraphQuery(q,world)).toBe(true);
  expect(isSurfaceNativeReceipt(receipt,buildWork)).toBe(true);
  expect(isSurfaceNativeCompletion(c.completion,receipt as SurfaceNativeContextReceiptV1)).toBe(true);
  const missing={...receipt,native_query:{...q,authored_targets:[]}};
  expect(isSurfaceNativeCompletion(c.completion,missing as SurfaceNativeContextReceiptV1)).toBe(false);
});

it.each(['missing','foreign','duplicate','extra','blank'])('rejects a V4 object catalog outside exact discovered roots: %s',mutation=>{
  const c=authoredContext();
  const roots=['ent:one','ent:two'];
  const q={...c.receipt.native_query,schema:'dmb_native_graph_query_v4',discovered_entity_ids:roots,
    object_matches:roots.map(entity_id=>({entity_id,label:entity_id}))};
  expect(isNativeGraphQuery(q,c.receipt.work_context.source_basis.world_id)).toBe(true);
  if(mutation==='missing')q.object_matches.pop();
  else if(mutation==='foreign')q.object_matches[0]!.entity_id='ent:foreign';
  else if(mutation==='duplicate')q.object_matches[1]!.entity_id=roots[0]!;
  else if(mutation==='extra')Object.assign(q.object_matches[0]!,{revision:'invented'});
  else q.object_matches[0]!.label='';
  expect(isNativeGraphQuery(q,c.receipt.work_context.source_basis.world_id)).toBe(false);
});


it('refuses campaign-scoped V4 presentation even with an empty authored catalog',()=>{
  const c=authoredContext();
  const q={...c.receipt.native_query,schema:'dmb_native_graph_query_v4',object_matches:[],authored_targets:[],
    authority:{...c.receipt.native_query.authority,scope_mode:'campaign',campaign_id:'c1'}};
  expect(isNativeGraphQuery(q,c.receipt.work_context.source_basis.world_id)).toBe(false);
});


import providerCapacityWire from '../test/surface-native-provider-capacity-http.json';
it('accepts the actual current Plan HTTP receipt with provider-owned capacity',()=>{
  const c=structuredClone(providerCapacityWire.context);
  expect(c.receipt.assembled_input.context_window_limit).toBeNull();
  expect(c.receipt.assembled_input.output_token_reserve).toBe(0);
  expect(isSurfaceNativeReceipt(c.receipt,work)).toBe(true);
  expect(isSurfaceNativeContext(c,work,()=>true)).toBe(true);
});
it.each([0,-1,'128000',false,undefined,Number.NaN])('refuses malformed current provider capacity %s',window=>{
  const c=structuredClone(providerCapacityWire.context);
  Object.assign(c.receipt.assembled_input,{context_window_limit:window});
  expect(isSurfaceNativeReceipt(c.receipt,work)).toBe(false);
});
it.each(['count','reserve','hash','world'])('provider-owned capacity preserves current %s presentation checks',change=>{
  const c=structuredClone(providerCapacityWire.context);
  if(change==='count')c.receipt.assembled_input.provider_envelope_input_tokens=-1;
  if(change==='reserve')c.receipt.assembled_input.output_token_reserve=-1;
  if(change==='hash')c.receipt.assembled_input.assembled_input_sha256='not-a-hash';
  if(change==='world')c.receipt.source_authority.managed_world_id='foreign';
  expect(isSurfaceNativeReceipt(c.receipt,work)).toBe(false);
});


it('accepts semantic initial input only for fresh Build, preserving old receipt readers',()=>{
  const build=structuredClone(buildWire.proposal_wire.response.knowledge_context.receipt);
  expect(isSurfaceNativeReceipt(build,buildWork)).toBe(true);
  Object.assign(build.assembled_input,{assembler_version:'native_build_semantic_initial_v2'});
  expect(isSurfaceNativeReceipt(build,buildWork)).toBe(true);
  const plan=context().receipt;
  Object.assign(plan.assembled_input,{assembler_version:'native_build_semantic_initial_v2'});
  expect(isSurfaceNativeReceipt(plan,work)).toBe(false);
  Object.assign(build.assembled_input,{assembler_version:'unknown-native-input'});
  expect(isSurfaceNativeReceipt(build,buildWork)).toBe(false);
});


it.each(['valid','foreign','build-draft','play'])('keeps saved authored-page claims distinct on Plan: %s',mutation=>{
  const c=context();const world=c.receipt.work_context.plan_basis.world_id;
  const segment={kind:'related_page_claim' as const,text:'The saved Edge page describes the old bath house.',
    read_id:'00000000-0000-4000-8000-000000000001',page:{world_id:world,
      document_id:'00000000-0000-4000-8000-000000000002',registry_revision:3,title:'Edge',visibility:'internal' as const,content_sha256:'a'.repeat(64)}};
  const answer={...c.completion,answer_segments:[segment],answer_context_status:'authored_grounded',
    native_body_citations:[],native_clause_citations:[],native_assertion_citations:[],saved_source_citations:[]};
  if(mutation==='foreign')segment.page.world_id='foreign';
  if(mutation==='build-draft')Object.assign(segment,{kind:'draft_reference_claim',draft_record_id:segment.read_id});
  if(mutation==='play')Object.assign(answer,{surface_id:'play'});
  expect(isSurfaceNativeCompletion(answer,c.receipt as SurfaceNativeContextReceiptV1)).toBe(mutation==='valid');
});


it('accepts only the shared connected-page review on Plan, not other Build collaborations',()=>{
 const c=context();const answer:any=c.completion;
 answer.answer_segments=[];answer.answer_context_status='discussion';
 answer.native_assertion_citations=[];answer.native_clause_citations=[];answer.native_body_citations=[];answer.saved_source_citations=[];
 answer.collaboration={kind:'connected_page',title:'The Old Bath House',read_id:'11111111-1111-4111-8111-111111111111',quote:'A saved Worldbuilding passage.',person_label:null,relationships:[],instructions:'Scaffold only'};
 expect(isSurfaceNativeCompletion(answer,c.receipt as SurfaceNativeContextReceiptV1)).toBe(true);
 answer.collaboration={kind:'questions',questions:['Which entrance?']};
 expect(isSurfaceNativeCompletion(answer,c.receipt as SurfaceNativeContextReceiptV1)).toBe(false);
});
