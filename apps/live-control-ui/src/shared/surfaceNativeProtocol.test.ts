import {it,expect} from 'vitest';
import wire from '../test/surface-native-http.json';
import {graphReferenceReply,isBuildGraphReferenceCompletion,isSurfaceNativeReceipt,isSurfaceNativeCompletion,isSurfaceNativeContext} from './surfaceNativeProtocol';
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
it('accepts typed Graph Review receipts only in native Build and rejects an action on clarification',()=>{
 const c=authoredContext();
 const completion={schema:'dmb_build_graph_reference_completion_v1',context_receipt_sha256:c.receipt.context_receipt_sha256,
   disposition:'ready',action_id:'11111111-1111-4111-8111-111111111111',placement_sha256:'a'.repeat(64)};
 const envelope={schema:'dmb_agent_surface_native_context_response_v1',delivery_replay:false,
   execution:{schema:'dmb_agent_plan_world_graph_execution_projection_v1',claimability:'completed',authorization_state:'response_received',automatic_redispatch:false}};
 expect(isSurfaceNativeContext({...envelope,...c,completion},buildWork,()=>true)).toBe(true);
 const plan=context();
 expect(isSurfaceNativeContext({...envelope,receipt:plan.receipt,completion:{...completion,
   context_receipt_sha256:plan.receipt.context_receipt_sha256}},work,()=>true)).toBe(false);
 const refusal={...completion,disposition:'wrong_kind',action_id:null,placement_sha256:null};
 if (!isBuildGraphReferenceCompletion(refusal,c.receipt.context_receipt_sha256)) throw new Error('Refusal failed to decode');
 expect(graphReferenceReply(refusal)).toContain('different classification');
 expect(isBuildGraphReferenceCompletion({...refusal,action_id:completion.action_id},c.receipt.context_receipt_sha256)).toBe(false);
});
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


import openingWire from '../test/surface-native-plan-opening-http.json';
import playWire from '../test/surface-native-play-http.json';
it('accepts the actual request-admitted Plan HTTP wire without inventing SDK accounting',()=>{
  const c=structuredClone(openingWire.context);
  expect(isSurfaceNativeReceipt(c.receipt,work)).toBe(true);
  expect(isSurfaceNativeContext(c,work,()=>true)).toBe(true);
  expect(c.receipt.assembled_input.assembler_version).toBe('native_plan_request_admission_v1');
  expect(c.receipt.assembled_input).not.toHaveProperty('provider_envelope_input_tokens');
  expect(c.receipt.assembled_input).not.toHaveProperty('assembled_input_sha256');
});
it('keeps finite request-admission capacity coherent',()=>{
  const c=structuredClone(openingWire.context);
  Object.assign(c.receipt.assembled_input,{context_window_limit:100,output_token_reserve:10});
  expect(isSurfaceNativeReceipt(c.receipt,work)).toBe(true);
  c.receipt.assembled_input.output_token_reserve=101;
  expect(isSurfaceNativeReceipt(c.receipt,work)).toBe(false);
});
it.each(['version','missing','extra','fake-sdk-count','manifest-format','intent-format','dialogue-format',
  'tokenizer-name','tokenizer-version','negative-reserve','fractional-reserve','zero-limit','negative-limit',
  'fractional-limit','string-limit','reserve-exceeds-limit','foreign-world','epoch'])(
  'refuses malformed Plan request admission: %s',change=>{
  const c=structuredClone(openingWire.context),input=c.receipt.assembled_input;
  if(change==='version')Object.assign(input,{assembler_version:'unknown-native-request'});
  else if(change==='missing')Reflect.deleteProperty(input,'manifest_sha256');
  else if(change==='extra')Object.assign(input,{extra:true});
  else if(change==='fake-sdk-count')Object.assign(input,{provider_envelope_input_tokens:0});
  else if(change==='manifest-format')input.manifest_sha256='invalid';
  else if(change==='intent-format')input.submitted_intent_sha256='invalid';
  else if(change==='dialogue-format')input.dialogue_sha256='invalid';
  else if(change==='tokenizer-name')input.tokenizer_name='';
  else if(change==='tokenizer-version')input.tokenizer_version='';
  else if(change==='negative-reserve')input.output_token_reserve=-1;
  else if(change==='fractional-reserve')input.output_token_reserve=0.5;
  else if(change==='zero-limit')input.context_window_limit=0;
  else if(change==='negative-limit')input.context_window_limit=-1;
  else if(change==='fractional-limit')input.context_window_limit=0.5;
  else if(change==='string-limit')Object.assign(input,{context_window_limit:'100'});
  else if(change==='reserve-exceeds-limit')Object.assign(input,{context_window_limit:10,output_token_reserve:11});
  else if(change==='foreign-world')c.receipt.source_authority.managed_world_id='foreign';
  else c.receipt.native_query.authority.acquisition_epoch++;
  expect(isSurfaceNativeReceipt(c.receipt,work)).toBe(false);
});
it.each(['build','play'] as const)('does not use Plan request admission on %s',surface=>{
  const receipt=structuredClone(surface==='build'
    ?buildWire.proposal_wire.response.knowledge_context.receipt:playWire.response.play_context.receipt);
  const validateWork=(value:unknown):value is SurfaceNativeWorkContextV1=>
    typeof value==='object'&&value!==null&&'surface_id' in value&&value.surface_id===surface;
  expect(isSurfaceNativeReceipt(receipt,validateWork)).toBe(true);
  Object.assign(receipt,{assembled_input:structuredClone(openingWire.context.receipt.assembled_input)});
  expect(isSurfaceNativeReceipt(receipt,validateWork)).toBe(false);
});

it('accepts a source-grounded Build PDF claim only for its World',()=>{
  const {receipt,completion}=authoredContext();
  const scope={managed_world_id:receipt.work_context.source_basis.world_id,native_world_id:'native',
    binding_version:1,revision_id:'rev:pdf',scope_mode:'world',campaign_id:null};
  const answer={...completion,answer_context_status:'source_grounded',native_body_citations:[],
    native_clause_citations:[],native_assertion_citations:[],saved_source_citations:[],
    answer_segments:[{kind:'statblock_pdf_claim',text:'Hit Points 207',scope,
      assertion_id:'assertion:fixture',evidence_ref_id:'pdf-region:fixture'}]};
  expect(isSurfaceNativeCompletion(answer,receipt as SurfaceNativeContextReceiptV1)).toBe(true);
  scope.managed_world_id='foreign';
  expect(isSurfaceNativeCompletion(answer,receipt as SurfaceNativeContextReceiptV1)).toBe(false);
});

it('accepts an inert Build lore draft and rejects a writer-owned duplicate body', () => {
  const c = authoredContext();
  const draft = {
    kind: 'lore_page',
    destination: {instruction: 'Create a blank page for Rowan.', title: 'Rowan'},
  };
  const answer = {
    ...c.completion,
    answer_context_status: 'discussion',
    answer_segments: [],
    collaboration: draft,
    saved_source_citations: [],
    native_body_citations: [],
    native_clause_citations: [],
    native_assertion_citations: [],
  };
  const receipt = c.receipt as SurfaceNativeContextReceiptV1;
  expect(isSurfaceNativeCompletion(answer, receipt)).toBe(true);
  expect(isSurfaceNativeCompletion(
    {...answer, collaboration: {...draft, markdown: 'Uncited prose'}}, receipt,
  )).toBe(false);
  const destination = {request: 'current_author_request', title: 'The Memory Ferry — Échos'};
  expect(isSurfaceNativeCompletion({...answer, collaboration: {...draft, destination}}, receipt)).toBe(true);
  for (const invalid of [
    {...destination, request: 'prior_author_request'},
    {...destination, instruction: 'Create a page'},
    {...destination, title: 'Title\nInjected'},
  ]) {
    expect(isSurfaceNativeCompletion({...answer, collaboration: {...draft, destination: invalid}}, receipt)).toBe(false);
  }

});


it.each(['valid','missing','foreign-epoch','bad-receipt','wrong-producer','wrong-match','extra-match'])(
  'checks deferred Build receipt and exact citation membership: %s', mutation=>{
    const c=authoredContext(), r=c.receipt, answer=c.completion;
    const membership={
      context_receipt_sha256:r.context_receipt_sha256,
      producing_provider_attempt_id:answer.producing_provider_attempt_id,
      statements:answer.native_clause_citations.map(cite=>[cite.statement_id,cite.campaign_id]),
      assertions:answer.native_assertion_citations.map(cite=>[cite.assertion_id,cite.assertion_sha256]),
    };
    const authority=structuredClone(r.native_query.authority);
    const pending={
      ...r,
      native_query:{schema:'dmb_native_build_query_pending_v1',authority,question:r.native_query.question},
      assembled_input:{...r.assembled_input,assembler_version:'native_build_semantic_initial_v2'},
    };
    if(mutation==='foreign-epoch')authority.acquisition_epoch++;
    if(mutation==='bad-receipt')membership.context_receipt_sha256='f'.repeat(64);
    if(mutation==='wrong-producer')membership.producing_provider_attempt_id='00000000-0000-4000-8000-000000000001';
    if(mutation==='wrong-match')membership.assertions[0]![0]='foreign';
    if(mutation==='extra-match')membership.assertions.push(['extra','f'.repeat(64)]);
    const valid=isSurfaceNativeReceipt(pending,buildWork)
      &&isSurfaceNativeCompletion(answer,pending,mutation==='missing'?undefined:membership);
    expect(valid).toBe(mutation==='valid');
  },
);

// Actual projector output from the pending sixty-turn SDK/completion boundary fixture.
import pendingBuild from '../test/pending-build-page-api.json';
import {isBuildPendingReceipt,isBuildPendingContext} from './surfaceNativeProtocol';
it('accepts the distinct pending Build draft API projection without source authority',()=>{
  expect(isBuildPendingContext(pendingBuild,buildWork,()=>true)).toBe(true);
  expect(isSurfaceNativeReceipt(pendingBuild.receipt,buildWork)).toBe(false);
  expect(isBuildPendingContext(pendingBuild,work,()=>true)).toBe(false);
});
it('accepts only a receipt-bound pending Build proposal completion',()=>{
  const c=structuredClone(pendingBuild) as any;
  c.completion={schema:'dmb_build_authoring_completion_v1',context_receipt_sha256:c.receipt.context_receipt_sha256,
    answer_basis:'prepared_page_proposal',answer_context_status:'proposal_ready',
    answer_segments:[{kind:'connective',text:'A preview is ready. Review it before inserting it into the page. Nothing has been saved or published.'}],
    citation_map:null,action_id:'11111111-1111-4111-8111-111111111111',provider_attempt_id:'22222222-2222-4222-8222-222222222222',
    reservation_sha256:'a'.repeat(64),proposal_result_sha256:'b'.repeat(64),envelope_sha256:'c'.repeat(64)};
  expect(isBuildPendingContext(c,buildWork,()=>true)).toBe(true);
  c.completion.context_receipt_sha256='0'.repeat(64);
  expect(isBuildPendingContext(c,buildWork,()=>true)).toBe(false);
});
it.each(['world','binding','head','pointer','assembler','authority','surface','root','null','execution','citation','extra'])(
  'rejects invalid pending Build observation/completion: %s',mutation=>{
    const c=structuredClone(pendingBuild) as any;
    if(mutation==='world')c.receipt.source_observation.managed_world_id='foreign';
    if(mutation==='binding')c.receipt.source_observation.binding={managed_world_id:'foreign',native_world_id:'native',binding_version:1,provisioning_id:null};
    if(mutation==='head')c.receipt.source_observation.observed_head_revision_id='unbound-head';
    if(mutation==='pointer')c.receipt.conversation_observation.pointer_revision=true;
    if(mutation==='assembler')c.receipt.assembled_input.assembler_version='native_build_semantic_initial_v2';
    if(mutation==='authority')c.receipt.source_authority={};
    if(mutation==='surface')c.completion.surface_id='plan';
    if(mutation==='root')c.completion.context_receipt_sha256='0'.repeat(64);
    if(mutation==='null')c.completion=null;
    if(mutation==='execution')c.execution=null;
    if(mutation==='citation')c.completion.native_clause_citations=[{}];
    if(mutation==='extra')c.deferred_build_citations={};
    expect(isBuildPendingContext(c,buildWork,()=>true,true)).toBe(false);
});
it('permits only unfinished history without a pending completion',()=>{
  const c={...pendingBuild,completion:null,execution:null};
  expect(isBuildPendingContext(c,buildWork,()=>true)).toBe(false);
  expect(isBuildPendingContext(c,buildWork,()=>true,true)).toBe(true);
  expect(isBuildPendingReceipt(pendingBuild.receipt,buildWork)).toBe(true);
});

it('accepts an inert pending proposal only for its completed receipt without citation membership',()=>{
  const completion = {
    schema: 'dmb_build_authoring_completion_v1', context_receipt_sha256: pendingBuild.receipt.context_receipt_sha256,
    answer_basis: 'prepared_page_proposal', answer_context_status: 'proposal_ready', citation_map: null,
    answer_segments: [{kind: 'connective', text: 'A preview is ready. Review it before inserting it into the page. Nothing has been saved or published.'}],
    action_id: '00000000-0000-4000-8000-000000000001', provider_attempt_id: '00000000-0000-4000-8000-000000000002',
    reservation_sha256: 'a'.repeat(64), proposal_result_sha256: 'b'.repeat(64), envelope_sha256: 'c'.repeat(64),
  };
  const response = {...pendingBuild, completion};
  expect(isBuildPendingContext(response,buildWork,()=>true)).toBe(true);
  expect(isBuildPendingContext({...response,execution:null},buildWork,()=>true)).toBe(false);
  expect(isBuildPendingContext({...response,deferred_build_citations:{}},buildWork,()=>true)).toBe(false);
  expect(isBuildPendingContext({...response,completion:{...completion,context_receipt_sha256:'0'.repeat(64)}},buildWork,()=>true)).toBe(false);
});

it.each(['valid','missing','root','producer','assertion','extra','revision','native-world'])(
  'binds pending Graph citations to the settled membership and captured scope: %s', mutation=>{
    const original=authoredContext(), r=original.receipt, answer=original.completion;
    const c=structuredClone(pendingBuild) as any;
    c.receipt.context_receipt_sha256=r.context_receipt_sha256;
    c.receipt.provenance_sha256=r.provenance_sha256;
    c.receipt.work_context=r.work_context;
    const authority=r.native_query.authority;
    c.receipt.source_observation={schema:'dmb_build_source_observation_v1',managed_world_id:authority.managed_world_id,
      binding:{managed_world_id:authority.managed_world_id,native_world_id:authority.native_world_id,
        binding_version:authority.binding_version,provisioning_id:authority.provisioning_id??null},
      requested_revision_id:authority.revision_id,observed_head_revision_id:authority.revision_id};
    c.completion=answer;
    c.deferred_build_citations={context_receipt_sha256:r.context_receipt_sha256,
      producing_provider_attempt_id:answer.producing_provider_attempt_id,
      statements:answer.native_clause_citations.map(cite=>[cite.statement_id,cite.campaign_id]),
      assertions:answer.native_assertion_citations.map(cite=>[cite.assertion_id,cite.assertion_sha256])};
    if(mutation==='missing')delete c.deferred_build_citations;
    if(mutation==='root')c.deferred_build_citations.context_receipt_sha256='f'.repeat(64);
    if(mutation==='producer')c.deferred_build_citations.producing_provider_attempt_id='00000000-0000-4000-8000-000000000001';
    if(mutation==='assertion')c.deferred_build_citations.assertions[0][0]='foreign';
    if(mutation==='extra')c.deferred_build_citations.assertions.push(['extra','f'.repeat(64)]);
    if(mutation==='revision')c.receipt.source_observation.requested_revision_id='foreign';
    if(mutation==='native-world')c.receipt.source_observation.binding.native_world_id='foreign';
    expect(isBuildPendingContext(c,buildWork,()=>true)).toBe(mutation==='valid');
  },
);
