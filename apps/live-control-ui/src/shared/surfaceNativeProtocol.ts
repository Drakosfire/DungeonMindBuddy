import type {BuildPendingContextReceiptV1,SurfaceNativeContextReceiptV1,SurfaceNativeCompletionV1,SurfaceNativeWorkContextV1,PlanSourceContextReceiptV1,NativePlanRequestAdmissionV1} from '../api/types';
import {exact,canonical,isCollaboration,isDraftReferenceClaim,isRelatedPageClaim,isSavedSourceClaim} from './sourcePassageProtocol';
import {isNativeGraphQuery,isNativeBuildQueryPending,isNativeClauseCitation} from './nativeStatementAnswerProtocol';
import {isNativeAssertionClaim,isNativeAssertionCitation} from './nativeAssertionProtocol';
import {isNativeBodyCitation} from './nativeSourceCitationProtocol';
import {isAuthoredExcerpt,isSessionSummary} from './surfaceEvidenceProtocol';
const text=(v:unknown):v is string=>typeof v==='string'&&!!v.trim();
const hash=(v:unknown):v is string=>typeof v==='string'&&/^[a-f0-9]{64}$/.test(v);
const uuid=(v:unknown):v is string=>typeof v==='string'&&/^[a-f0-9]{8}-(?:[a-f0-9]{4}-){3}[a-f0-9]{12}$/i.test(v);
const integer=(v:unknown,min=0):v is number=>typeof v==='number'&&Number.isSafeInteger(v)&&v>=min;
/** Closed presentation shape; Core and APP own admission and publication. */
export function isNativeSourceAuthority(a:unknown,worldId:string):a is PlanSourceContextReceiptV1['source_authority'] {
  if(exact(a,['schema','managed_world_id','failure_code'])&&a.schema==='dmb_native_corpus_unavailable_v1')
    return a.managed_world_id===worldId&&['native_source_identity_unavailable','native_source_head_unavailable','native_source_authority_unavailable'].includes(String(a.failure_code));
  const ref=(v:unknown)=>exact(v,['authority_id','revision','descriptor_sha256'])&&text(v.authority_id)&&text(v.revision)&&hash(v.descriptor_sha256);
  return exact(a,['schema_version','managed_world_id','native_world_id','binding_version','provisioning_id','revision_id','domain_ref','profile_ref','acquisition_epoch','scope','role'])
    &&a.schema_version==='dmb_native_corpus_authority_v1'&&a.managed_world_id===worldId&&text(a.native_world_id)&&text(a.revision_id)&&integer(a.binding_version,1)
    &&(a.provisioning_id===null||text(a.provisioning_id))&&integer(a.acquisition_epoch)&&ref(a.domain_ref)&&ref(a.profile_ref)&&a.scope==='gm_world_cross_campaign_source_inspection'&&a.role==='gm';
}
export function isNativeProviderInput(input:unknown,assembler:'surface_native_initial_v1'|'plan_source_jev_initial_v1'|'native_build_semantic_initial_v2'|'native_build_pending_initial_v3'):boolean {
  return exact(input,['assembler_version','provider_model_name','provider_model_version','tokenizer_name','tokenizer_version','provider_envelope_input_tokens','output_token_reserve','context_window_limit','included_history','assembled_input_sha256'])
    &&input.assembler_version===assembler&&[input.provider_model_name,input.provider_model_version,input.tokenizer_name,input.tokenizer_version].every(text)
    &&integer(input.provider_envelope_input_tokens)&&integer(input.output_token_reserve)
    &&(input.context_window_limit===null || integer(input.context_window_limit,1)
      &&input.provider_envelope_input_tokens+input.output_token_reserve<=input.context_window_limit)
    &&hash(input.assembled_input_sha256)
    &&Array.isArray(input.included_history)&&input.included_history.every(pin=>exact(pin,['turn_id','answer_sha256'])&&uuid(pin.turn_id)&&hash(pin.answer_sha256))
    &&new Set(input.included_history.map(pin=>pin.turn_id)).size===input.included_history.length;
}
/** Closed presentation only; APP owns the manifest and later SDK authorization. */
function isNativePlanRequestAdmission(input:unknown):input is NativePlanRequestAdmissionV1 {
  return exact(input,['assembler_version','manifest_sha256','submitted_intent_sha256','dialogue_sha256',
    'tokenizer_name','tokenizer_version','context_window_limit','output_token_reserve'])
    &&input.assembler_version==='native_plan_request_admission_v1'
    &&[input.manifest_sha256,input.submitted_intent_sha256,input.dialogue_sha256].every(hash)
    &&[input.tokenizer_name,input.tokenizer_version].every(text)&&integer(input.output_token_reserve)
    &&(input.context_window_limit===null||integer(input.context_window_limit,1)
      &&input.output_token_reserve<=input.context_window_limit);
}
export function nativeWorkWorld(work:SurfaceNativeWorkContextV1):string {
  return work.surface_id==='build'?work.source_basis.world_id:work.surface_id==='plan'?work.plan_basis.world_id:work.play_basis.world_id;
}
/** Work shape stays with its actual surface owner, never a fabricated old receipt. */
export function isSurfaceNativeReceipt(v:unknown,validateWork:(work:unknown)=>work is SurfaceNativeWorkContextV1):v is SurfaceNativeContextReceiptV1 {
  if(!exact(v,['schema','receipt_serializer_version','context_receipt_sha256','provenance_sha256','work_context','source_authority','native_query','assembled_input'])
    ||v.schema!=='dmb_surface_native_context_receipt_v1'||v.receipt_serializer_version!=='canonical-json-utf8-v1'||!hash(v.context_receipt_sha256)||!hash(v.provenance_sha256)||!validateWork(v.work_context))return false;
  const world=nativeWorkWorld(v.work_context),a=v.source_authority,q=v.native_query;
  if(!isNativeSourceAuthority(a,world))return false;
  if(isNativeBuildQueryPending(q,world)) {
    if(v.work_context.surface_id!=='build'||!('schema_version' in a)
      ||!isNativeProviderInput(v.assembled_input,'native_build_semantic_initial_v2'))return false;
  } else if(!isNativeGraphQuery(q,world))return false;
  if(q.schema!=='dmb_native_plan_query_unavailable_v1'&&'schema_version' in a&&['native_world_id','binding_version','revision_id','domain_ref','profile_ref','acquisition_epoch'].some(k=>canonical(a[k as keyof typeof a])!==canonical(q.authority[k as keyof typeof q.authority])))return false;
  return isNativeProviderInput(v.assembled_input,'surface_native_initial_v1')
    ||v.work_context.surface_id==='plan'&&isNativePlanRequestAdmission(v.assembled_input)
    ||v.work_context.surface_id==='build'&&isNativeProviderInput(v.assembled_input,'native_build_semantic_initial_v2')
    ||v.work_context.surface_id==='build'&&exact(v.assembled_input,['assembler_version','submitted_intent_sha256','assembled_input_sha256'])&&v.assembled_input.assembler_version==='reviewed_author_admission_v1'&&hash(v.assembled_input.submitted_intent_sha256)&&hash(v.assembled_input.assembled_input_sha256);
}
function isLorePageDraft(value: unknown): boolean {
  const questions=typeof value==='object'&&value!==null&&'open_questions' in value;
  return exact(value, ['kind', 'destination', ...(questions?['open_questions']:[])])
    && (!questions || Array.isArray(value.open_questions) && value.open_questions.length>0
      && value.open_questions.length<=24 && value.open_questions.every(q=>text(q)&&[...q].length<=1000&&!/[\r\n]/.test(q)))
    && value.kind === 'lore_page'
    && (exact(value.destination, ['instruction', 'title'])
      && text(value.destination.instruction) && [...value.destination.instruction].length <= 2000
      || exact(value.destination, ['request', 'title']) && value.destination.request === 'current_author_request')
    && text(value.destination.title) && [...value.destination.title].length <= 200
    && !/[\r\n]/.test(value.destination.title);
}

export function isSurfaceNativeCompletion(
  v:unknown,r:SurfaceNativeContextReceiptV1|BuildPendingContextReceiptV1,membership?:unknown,
):v is SurfaceNativeCompletionV1 {
  if(!exact(v,['schema','surface_id','context_receipt_sha256','producing_provider_attempt_id','answer_basis','answer_context_status','answer_segments','collaboration','saved_source_citations','native_body_citations','native_clause_citations','native_assertion_citations'])
    ||v.schema!=='dmb_surface_native_completion_v1'||v.surface_id!==r.work_context.surface_id||v.context_receipt_sha256!==r.context_receipt_sha256||!uuid(v.producing_provider_attempt_id)||v.answer_basis!=='mixed_evidence'
    ||!Array.isArray(v.answer_segments)||v.answer_segments.length>128||!(isCollaboration(v.collaboration,true,true,true,true) || v.surface_id === 'build' && isLorePageDraft(v.collaboration))||v.collaboration!==null&&v.surface_id!=='build'&&!(v.surface_id==='plan'&&typeof v.collaboration==='object'&&v.collaboration!==null&&'kind' in v.collaboration&&v.collaboration.kind==='connected_page')||!v.answer_segments.length&&v.collaboration===null)return false;
  const pending='source_observation' in r||r.native_query.schema==='dmb_native_build_query_pending_v1';
  const projected={statements:new Set<string>(),assertions:new Set<string>()};
  if(membership!==undefined) {
    if(!pending||!exact(membership,['context_receipt_sha256','producing_provider_attempt_id','statements','assertions'])
      ||membership.context_receipt_sha256!==r.context_receipt_sha256
      ||membership.producing_provider_attempt_id!==v.producing_provider_attempt_id)return false;
    for(const family of ['statements','assertions'] as const) {
      const rows=membership[family];
      if(!Array.isArray(rows)||rows.length>16384)return false;
      for(const row of rows) {
        if(!Array.isArray(row)||row.length!==2||!text(row[0])
          ||!(family==='statements'?text(row[1]):hash(row[1])))return false;
        const key=canonical(row);
        if(projected[family].has(key))return false;
        projected[family].add(key);
      }
    }
  }
  const witnessed={statements:new Set<string>(),assertions:new Set<string>()};
  const sources=new Set<number>(),graphs=new Map<number,string[]>(),saved=new Set<number>(),blocks=new Set<string>();
  let authored=false,buildAuthored=false,proposal=false,partial=false,discussion=false,pdf=false;
  const work=r.work_context;
  for(const [i,s] of v.answer_segments.entries()) {
    if(!s||typeof s!=='object'||!text(s.text))return false;
    if(s.kind==='source_passage_claim') {if(!exact(s,['kind','text']))return false;sources.add(i);}
    else if(s.kind==='native_assertion_claim') {if(!isNativeAssertionClaim(s))return false;graphs.set(i,s.assertion_ids);}
    else if(s.kind==='authored_excerpt'||s.kind==='session_summary') {
      if(work.surface_id==='build'||(s.kind==='session_summary'?!isSessionSummary(s):!isAuthoredExcerpt(s)))return false;
      for(const q of s.kind==='session_summary'?s.supports:[s]) {
        if(work.surface_id==='plan') {
          if(q.source_kind==='play'||q.source_kind==='plan'&&(q.object_id!==work.plan_basis.document_id||q.revision!==work.plan_basis.work_revision_id||q.owner_sha256!==work.plan_basis.content_sha256||q.body_sha256!==q.owner_sha256))return false;
        } else if(q.source_kind==='plan'||q.object_id!==work.play_basis.run_id
          ||q.source_kind==='play'&&!work.play_sources.entries.some(e=>e.source_id===q.source_handle&&e.text_sha256===q.body_sha256&&e.payload_sha256===q.owner_sha256&&String(e.locator.run_revision)===q.revision)
          ||q.source_kind==='session'&&s.kind==='session_summary'&&q.checkpoint_content_sha256!==work.play_basis.content_sha256)return false;
      }
      if(s.kind==='authored_excerpt'){if(blocks.has(s.block_handle))return false;blocks.add(s.block_handle);}authored=true;
    } else if(s.kind==='proposal') {if(!exact(s,['kind','text','label'])||!['invented_idea','image_prompt'].includes(String(s.label)))return false;proposal=true;}
    else if(s.kind==='limitation') {if(!exact(s,['kind','text','code','question_phrase'])||!['missing_requested_details','partial_retrieval','unresolved_conflict'].includes(String(s.code))||!(s.question_phrase===null||text(s.question_phrase)))return false;partial=true;}
    else if(work.surface_id==='build'&&s.kind==='statblock_pdf_claim') {
      if(!exact(s,['kind','text','scope','assertion_id','evidence_ref_id'])
        ||!exact(s.scope,['managed_world_id','native_world_id','binding_version','revision_id','scope_mode','campaign_id'])
        ||s.scope.managed_world_id!==nativeWorkWorld(work)||s.scope.scope_mode!=='world'||s.scope.campaign_id!==null
        ||!text(s.scope.native_world_id)||!text(s.scope.revision_id)
        ||typeof s.scope.binding_version!=='number'||!Number.isInteger(s.scope.binding_version)||s.scope.binding_version<1
        ||!text(s.assertion_id)||typeof s.evidence_ref_id!=='string'||!/^pdf-region:.+$/.test(s.evidence_ref_id))return false;
      pdf=true;
    }
    else if(work.surface_id==='build'&&s.kind==='discussion') {if(!exact(s,['kind','text']))return false;discussion=true;}
    else if(work.surface_id==='build'&&s.kind==='draft_reference_claim') {if(!isDraftReferenceClaim(s))return false;buildAuthored=true;}
    else if((work.surface_id==='build'||work.surface_id==='plan')&&s.kind==='related_page_claim') {
      if(!isRelatedPageClaim(s,nativeWorkWorld(work)))return false;buildAuthored=true;
    } else if(work.surface_id==='build'&&s.kind==='saved_source_claim') {if(!isSavedSourceClaim(s,work.source_basis.content_sha256))return false;saved.add(i);}
    else return false;
  }
  const seen=new Set<string>(),cited=new Set<number>(),assertions=new Map<number,Set<string>>();
  for(const family of ['native_body_citations','native_clause_citations','native_assertion_citations'] as const) {
    const cites=v[family];if(!Array.isArray(cites)||cites.length>16384)return false;
    for(const c of cites) {
      if(family==='native_body_citations'?!isNativeBodyCitation(c):family==='native_clause_citations'?!isNativeClauseCitation(c,r.context_receipt_sha256):!isNativeAssertionCitation(c,r.context_receipt_sha256))return false;
      if(c.provider_attempt_id!==v.producing_provider_attempt_id)return false;
      const index=c.segment_index,key=canonical(family==='native_body_citations'?['body',index,c.read_event_id]:family==='native_clause_citations'?['statement',index,c.statement_id]:['assertion',index,c.read_event_id,c.assertion_id,c.evidence_ref_id]);
      if(seen.has(key))return false;seen.add(key);
      if(family==='native_body_citations'){if(!sources.has(index)||c.line_end<c.line_start
        ||('prior_reference' in c && (work.surface_id!=='build'||!isLorePageDraft(v.collaboration))))return false;cited.add(index);continue;}
      const q='native_query' in r?r.native_query:null;
      if(q===null) {
        const observed='source_observation' in r?r.source_observation:null;
        if(!observed?.binding||c.managed_world_id!==observed.managed_world_id
          ||c.native_world_id!==observed.binding.native_world_id
          ||c.read_revision_id!==(observed.requested_revision_id??observed.observed_head_revision_id))return false;
      } else if(q.schema==='dmb_native_plan_query_unavailable_v1'||c.managed_world_id!==q.authority.managed_world_id||c.native_world_id!==q.authority.native_world_id||c.read_revision_id!==q.authority.revision_id)return false;
      if(family==='native_clause_citations') {
        const key=canonical([c.statement_id,c.campaign_id]);
        const matches=q===null||q.schema==='dmb_native_build_query_pending_v1'?projected.statements.has(key)
          :[...q.matches,...((q.schema==='dmb_native_graph_query_v3'||q.schema==='dmb_native_graph_query_v4')?q.authored_targets.flatMap(t=>t.matches):[])].some(m=>m.statement_id===c.statement_id&&m.campaign_id===c.campaign_id);
        if(!sources.has(index)||!matches)return false;
        witnessed.statements.add(key);cited.add(index);
      } else {
        const key=canonical([c.assertion_id,c.assertion_sha256]);
        const matches=q===null||q.schema==='dmb_native_build_query_pending_v1'?projected.assertions.has(key)
          :[...q.assertion_matches,...((q.schema==='dmb_native_graph_query_v3'||q.schema==='dmb_native_graph_query_v4')?q.authored_targets.flatMap(t=>t.assertion_matches):[])].some(m=>m.assertion_id===c.assertion_id&&m.assertion_sha256===c.assertion_sha256);
        if(!graphs.get(index)?.includes(c.assertion_id)||!matches)return false;
        witnessed.assertions.add(key);
        const ids=assertions.get(index)??new Set<string>();ids.add(c.assertion_id);assertions.set(index,ids);
      }
    }
  }
  if(pending&&['statements','assertions'].some(family=>
    projected[family as keyof typeof projected].size!==witnessed[family as keyof typeof witnessed].size))return false;
  if([...sources].some(i=>!cited.has(i))||[...graphs].some(([i,ids])=>ids.some(id=>!assertions.get(i)?.has(id))))return false;
  if(!Array.isArray(v.saved_source_citations)||v.saved_source_citations.length!==saved.size)return false;
  for(const [i,c] of v.saved_source_citations.entries())if(!exact(c,['segment_index','text_sha256','section_event_ids'])||c.segment_index!==[...saved][i]||!hash(c.text_sha256)||!Array.isArray(c.section_event_ids)||!c.section_event_ids.length||c.section_event_ids.length>128||!c.section_event_ids.every((id,j)=>uuid(id)&&(!j||((c.section_event_ids as string[])[j-1]!)<id)))return false;
  const status=graphs.size?'graph_grounded':buildAuthored?'authored_grounded':sources.size||saved.size||pdf?'source_grounded':authored?'authored_grounded':proposal?'creative_proposal':discussion&&!partial||!v.answer_segments.length?'discussion':'insufficient_evidence';
  return v.answer_context_status===status+(partial&&!['creative_proposal','insufficient_evidence','discussion'].includes(status)?'_partial':'');
}

export function isBuildAuthoringCompletion(value: unknown, receiptHash: string): value is import('../api/types').WorldBuildAuthoringCompletionV1 {
  return exact(value, ["schema", "context_receipt_sha256", "answer_basis", "answer_context_status",
    "answer_segments", "citation_map", "action_id", "reservation_sha256", "proposal_result_sha256", "provider_attempt_id", "envelope_sha256"])
    && value.schema === "dmb_build_authoring_completion_v1" && value.context_receipt_sha256 === receiptHash
    && value.answer_basis === "prepared_page_proposal" && value.answer_context_status === "proposal_ready"
    && value.citation_map === null && Array.isArray(value.answer_segments) && value.answer_segments.length === 1
    && exact(value.answer_segments[0], ["kind", "text"])
    && value.answer_segments[0].kind === "connective"
    && value.answer_segments[0].text === "A preview is ready. Review it before inserting it into the page. Nothing has been saved or published."
    && [value.action_id, value.provider_attempt_id].every(id => typeof id === "string" && /^[a-f0-9]{8}-(?:[a-f0-9]{4}-){3}[a-f0-9]{12}$/i.test(id))
    && [value.reservation_sha256, value.proposal_result_sha256, value.envelope_sha256].every(hash => typeof hash === "string" && /^[a-f0-9]{64}$/.test(hash));
}


export function isBuildImageCompletion(value: unknown, receiptHash: string): value is import('../api/types').WorldBuildImagePreparationCompletionV1 {
  return exact(value, ["schema", "context_receipt_sha256", "answer_basis", "answer_context_status",
    "answer_segments", "citation_map", "action_id", "reservation_sha256", "preparation_result_sha256", "provider_attempt_id", "envelope_sha256"])
    && value.schema === "dmb_build_image_preparation_completion_v1" && value.context_receipt_sha256 === receiptHash
    && value.answer_basis === "prepared_image_direction" && value.answer_context_status === "image_preparation_ready"
    && value.citation_map === null && Array.isArray(value.answer_segments) && value.answer_segments.length === 1
    && exact(value.answer_segments[0], ["kind", "text"])
    && value.answer_segments[0].kind === "connective"
    && value.answer_segments[0].text === "Your image prompt is ready in Image Studio. Review it before generating. Nothing has been generated, inserted or saved."
    && [value.action_id, value.provider_attempt_id].every(id => typeof id === "string" && /^[a-f0-9]{8}-(?:[a-f0-9]{4}-){3}[a-f0-9]{12}$/i.test(id))
    && [value.reservation_sha256, value.preparation_result_sha256, value.envelope_sha256].every(hash => typeof hash === "string" && /^[a-f0-9]{64}$/.test(hash));
}


type GraphReferenceCompletion = import('../api/types').WorldBuildGraphReferenceCompletionV1;

const graphReferenceReplies: Record<GraphReferenceCompletion['disposition'], string> = {
  ready: "The Graph reference is ready to review. The page is unchanged.",
  discussion: "If you want to add a reference, tell me which existing Graph object and where it should go.",
  new_object: "Choose an existing Graph object to reference on this page.",
  different_page: "Open the intended page and send the request there.",
  ambiguous_identity: "Select the exact Graph object you want to reference.",
  wrong_kind: "The matching Graph object has a different classification. Select the intended object.",
  missing_identity: "I couldn't find that Graph object. Select the existing object you want to reference.",
  ambiguous_boundary: "Which paragraph should the reference go next to? Include its heading or select the paragraph.",
  missing_boundary: "I couldn't find that paragraph on this page. Give its heading or exact text.",
  unresolved: "Tell me which existing Graph object to reference and where it should go on this page.",
};

export function graphReferenceReply(completion: GraphReferenceCompletion): string {
  return graphReferenceReplies[completion.disposition];
}

export function isBuildGraphReferenceCompletion(value: unknown, receiptHash: string): value is GraphReferenceCompletion {
  return exact(value, ['schema', 'context_receipt_sha256', 'disposition', 'action_id', 'placement_sha256'])
    && value.schema === 'dmb_build_graph_reference_completion_v1' && value.context_receipt_sha256 === receiptHash
    && typeof value.disposition === 'string' && Object.prototype.hasOwnProperty.call(graphReferenceReplies, value.disposition)
    && (value.disposition === 'ready' ? uuid(value.action_id) && hash(value.placement_sha256)
      : value.action_id === null && value.placement_sha256 === null);
}

type ImageMoveCompletion = import('../api/types').WorldBuildImageMoveCompletionV1;

const imageMoveReplies: Record<ImageMoveCompletion['disposition'], string> = {
  ready: "The image move is ready to review. Applying it updates the editor. Save when you're ready.",
  discussion: "To move an existing image, name or select it and ask to move it to the next slot on its right.",
  ambiguous: "Select the exact image you want to move.",
  missing: "I couldn't identify the image on this page. Select it and send the request again.",
  different_row: "This move supports the adjacent right slot in the image's current row.",
  unsupported: "This move supports one slot to the right in the current row.",
  unresolved: "Which image should move into the empty slot immediately to its right?",
  occupied: "The adjacent right slot is occupied.",
  unavailable: "The image has no slot immediately to its right.",
  changes_reading_order: "Moving that image would change the page's reading order.",
};

export function imageMoveReply(completion: ImageMoveCompletion): string {
  return imageMoveReplies[completion.disposition];
}

export function isBuildImageMoveCompletion(value: unknown, receiptHash: string): value is ImageMoveCompletion {
  return exact(value, ['schema', 'context_receipt_sha256', 'disposition', 'action_id', 'placement_sha256'])
    && value.schema === 'dmb_build_image_move_completion_v1' && value.context_receipt_sha256 === receiptHash
    && typeof value.disposition === 'string' && Object.prototype.hasOwnProperty.call(imageMoveReplies, value.disposition)
    && (value.disposition === 'ready' ? uuid(value.action_id) && hash(value.placement_sha256)
      : value.action_id === null && value.placement_sha256 === null);
}

/** The shared response envelope is independent of the surface-owned work shape. */
export function isSurfaceNativeContext(
  v:unknown, validateWork:(work:unknown)=>work is SurfaceNativeWorkContextV1,
  validateExecution:(execution:unknown)=>boolean, history=false,
):v is import('../api/types').AgentSurfaceNativeContextResponseV1 {
  const membership=typeof v==='object'&&v!==null&&'deferred_build_citations' in v;
  if(!exact(v,['schema','receipt','completion','execution','delivery_replay',...(membership?['deferred_build_citations']:[])])
    ||v.schema!=='dmb_agent_surface_native_context_response_v1'
    ||!isSurfaceNativeReceipt(v.receipt,validateWork)
    ||v.execution!==null&&!validateExecution(v.execution)||typeof v.delivery_replay!=='boolean'
    ||(v.completion===null?membership:!(isSurfaceNativeCompletion(v.completion,v.receipt,v.deferred_build_citations)
      ||!membership&&v.receipt.work_context.surface_id==='build'&&(isBuildAuthoringCompletion(v.completion,v.receipt.context_receipt_sha256)||isBuildImageCompletion(v.completion,v.receipt.context_receipt_sha256)
        ||isBuildGraphReferenceCompletion(v.completion,v.receipt.context_receipt_sha256)
        ||isBuildImageMoveCompletion(v.completion,v.receipt.context_receipt_sha256)))))return false;
  const execution=v.execution as import('../api/types').WorldPlanGraphExecutionProjectionV1|null;
  return v.completion===null?history&&(execution===null||execution.claimability!=='completed')
    :execution!==null&&execution.claimability==='completed'&&execution.authorization_state==='response_received';
}

/** Observed pointers are not a source grant or a verified native query. */
export function isBuildPendingReceipt(v:unknown,validateWork:(work:unknown)=>work is SurfaceNativeWorkContextV1):v is BuildPendingContextReceiptV1 {
  if(!exact(v,['schema','receipt_serializer_version','context_receipt_sha256','provenance_sha256',
      'work_context','source_observation','conversation_observation','assembled_input'])
    ||v.schema!=='dmb_build_pending_context_receipt_v1'||v.receipt_serializer_version!=='canonical-json-utf8-v1'
    ||!hash(v.context_receipt_sha256)||!hash(v.provenance_sha256)||!validateWork(v.work_context)
    ||v.work_context.surface_id!=='build'||!isNativeProviderInput(v.assembled_input,'native_build_pending_initial_v3'))return false;
  const world=v.work_context.source_basis.world_id,o=v.source_observation,c=v.conversation_observation;
  if(!exact(c,['conversation_id','pointer_revision'])||!uuid(c.conversation_id)||!integer(c.pointer_revision)
    ||!exact(o,['schema','managed_world_id','binding','requested_revision_id','observed_head_revision_id'])
    ||o.schema!=='dmb_build_source_observation_v1'||o.managed_world_id!==world
    ||!(o.requested_revision_id===null||text(o.requested_revision_id))
    ||!(o.observed_head_revision_id===null||text(o.observed_head_revision_id)))return false;
  return o.binding===null?o.observed_head_revision_id===null
    :exact(o.binding,['managed_world_id','native_world_id','binding_version','provisioning_id'])
      &&o.binding.managed_world_id===world&&text(o.binding.native_world_id)&&integer(o.binding.binding_version,1)
      &&(o.binding.provisioning_id===null||text(o.binding.provisioning_id));
}
export function isBuildPendingContext(v:unknown,validateWork:(work:unknown)=>work is SurfaceNativeWorkContextV1,
  validateExecution:(execution:unknown)=>boolean,history=false):v is import('../api/types').AgentBuildPendingContextResponseV1 {
  const membership=typeof v==='object'&&v!==null&&'deferred_build_citations' in v;
  if(!exact(v,['schema','receipt','completion','execution','delivery_replay',...(membership?['deferred_build_citations']:[])])
    ||v.schema!=='dmb_agent_build_pending_context_response_v1'||!isBuildPendingReceipt(v.receipt,validateWork)
    ||typeof v.delivery_replay!=='boolean'||v.execution!==null&&!validateExecution(v.execution))return false;
  const execution=v.execution as import('../api/types').WorldPlanGraphExecutionProjectionV1|null;
  return v.completion===null?!membership&&history&&(execution===null||execution.claimability!=='completed')
    :(isSurfaceNativeCompletion(v.completion,v.receipt,v.deferred_build_citations)
      ||!membership&&isBuildAuthoringCompletion(v.completion,v.receipt.context_receipt_sha256))&&execution!==null
      &&execution.claimability==='completed'&&execution.authorization_state==='response_received';
}
