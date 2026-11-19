import {createHash} from 'node:crypto';
import {expect, vi} from 'vitest';
import * as api from '../api/liveApi';
import * as library from '../api/conversationLibraryApi';
import * as reviewApi from '../api/planAuthoringReviewApi';
import type {
  AgentConversationTurnProvenanceV1, AgentSurfaceNativeContextResponseV1,
  WorldOwnedPlanRecordV2, WorldOwnedCommittedRevisionV2,
  WorldPlanAgentTurnResponse,
  WorldAgentConversationHistoryTurnV3,
} from '../api/types';
import type {PlanAuthoredProposal, PlanAuthoringReview, PlanReviewApplication} from '../api/planAuthoringReviewApi';
import openingWire from './surface-native-plan-opening-http.json';
import {canonical} from '../shared/sourcePassageProtocol';

const hash = (text: string) => createHash('sha256').update(text).digest('hex');
const conversationId = '11111111-1111-4111-8111-111111111111';
const actionId = 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa';
const firstWork = '00000000-0000-4000-8000-000000000010';
const nextWork = '00000000-0000-4000-8000-000000000011';
const readyText = 'A suggestion is ready for review. Nothing has been saved.';

function correlationKey(world: string, turn: string) {
  const bytes = createHash('sha1').update(Buffer.from('6ba7b8119dad11d180b400c04fd430c8', 'hex'))
    .update('dmb-agent-turn:' + world + ':' + turn).digest();
  bytes[6] = (bytes[6]! & 0x0f) | 0x50;
  bytes[8] = (bytes[8]! & 0x3f) | 0x80;
  const hex = bytes.subarray(0, 16).toString('hex');
  return [hex.slice(0, 8), hex.slice(8, 12), hex.slice(12, 16), hex.slice(16, 20), hex.slice(20)].join('-');
}

/** Synthetic client transport only: real host/editor/Save machinery remains mounted. */
export function setupPlanAuthoringIntegration(
  initialRecord: WorldOwnedPlanRecordV2, initialMarkdown: string, replacement: string,
) {
  let record = {...initialRecord};
  let markdown = initialMarkdown;
  let digest = hash(markdown);
  let workRevision = firstWork;
  let revisionN = 1;
  let proposal: PlanAuthoredProposal | null = null;
  let review: PlanAuthoringReview | null = null;
  let originHash = '';
  const turns: WorldAgentConversationHistoryTurnV3[] = [];
  const world = record.world_id, documentId = record.document_id;
  const basis = () => ({
    world_id: world, document_id: documentId, object_revision: record.revision,
    work_revision_id: workRevision, revision_n: revisionN, content_sha256: digest,
  });
  const committed = (): WorldOwnedCommittedRevisionV2 => ({
    schema_version: 'dmb_workspace_committed_revision_v2', scope_mode: 'world',
    campaign_id: null, kind: 'plan',
    title: record.title, status: 'active', ...basis(), markdown,
    has_divergent_working_copy: false, target_relpath: record.target_relpath,
  });
  vi.spyOn(api, 'getWorkspaceDocumentAny').mockImplementation(async id => { expect(id).toBe(documentId); return {...record}; });
  vi.spyOn(api, 'listWorldOwnedPlans').mockImplementation(async requestedWorld => (expect(requestedWorld).toBe(world), {
    schema_version: 'dmb_workspace_document_registry_v2', scope_mode: 'world',
    world_id: world, records: [{...record}],
  }));
  vi.spyOn(api, 'getWorldOwnedPlanSnapshot').mockImplementation(async id => (expect(id).toBe(documentId), {
    schema_version: 'dmb_workspace_document_snapshot_v2', record: {...record}, markdown,
    content_sha256: digest, file_fingerprint: 'postgres', file_exists: true,
    loaded_revision: record.revision,
  }));
  vi.spyOn(api, 'getWorldOwnedPlanCommittedRevision').mockImplementation(async (id, requestedRevision) => { expect(id).toBe(documentId); if (requestedRevision !== undefined) expect(requestedRevision).toBe(revisionN); return committed(); });
  vi.spyOn(api, 'getWorldPlanDocumentEditActions').mockImplementation(async (requestedWorld, id) => (expect([requestedWorld, id]).toEqual([world, documentId]), {
    schema_version: 'dmb_world_plan_action_projection_v1', basis: basis(), actions: [],
  }));
  vi.spyOn(api, 'getWorldPlanConversationActions').mockImplementation(async (requestedWorld, id) => (expect([requestedWorld, id]).toEqual([world, conversationId]), {
    schema_version: 'dmb_world_plan_action_conversation_projection_v1',
    world_id: world, conversation_id: conversationId, actions: [], next_before_action_sequence: null,
  }));
  vi.spyOn(api, 'getWorldAgentConversationHistory').mockImplementation(async (requestedWorld, options = {}) => (expect(requestedWorld).toBe(world), {
    schema: 'dmb_agent_conversation_history_v3', world_id: world, conversation_state: 'active',
    conversation_id: conversationId, active_conversation_id: conversationId, pointer_revision: 4,
    turns: structuredClone(options.limit === 1
      ? turns.filter(turn => turn.sequence === options.beforeSequence! - 1) : turns),
    next_before_sequence: null,
  }));
  vi.spyOn(library, 'readActiveConversationMessages').mockImplementation(async (requestedWorld, before) => (expect(requestedWorld).toBe(world), {
    schema: 'dmb_active_conversation_messages_v4', world_id: world,
    conversation_state: 'active', conversation_id: conversationId,
    active_conversation_id: conversationId, pointer_revision: 4, next_before_sequence: null,
    messages: turns.filter(turn => before === undefined || turn.sequence < before).map(turn => ({
      turn_id: turn.turn_id, sequence: turn.sequence, status: turn.lifecycle_status,
      user_text: turn.user_text, assistant_text: turn.assistant_text,
      citation_preview: null, reply_object: null, authored_references: null,
      revision: 1, idempotency_key: turn.idempotency_key, provenance: turn.provenance,
    })),
  }));

  const legacyProposal = vi.spyOn(api, 'postWorldPlanDocumentEditProposal')
    .mockRejectedValue(new Error('Initial current Plan edits must not use the legacy proposal endpoint.'));
  const ordinaryPrepare = vi.spyOn(api, 'prepareTiptapMarkdownWrite')
    .mockRejectedValue(new Error('Current suggestion Save owns its application.'));
  const ordinaryCommit = vi.spyOn(api, 'commitWorldOwnedPlanMarkdownWrite')
    .mockRejectedValue(new Error('Current suggestion Save owns its application.'));

  const post = vi.spyOn(api, 'postWorldPlanAgentTurn').mockImplementation(async request => {
    const capture = request.plan_authoring_capture;
    if (!capture || request.plan_context_policy?.schema !== 'dmb_plan_context_policy_v2') {
      throw new Error('The current Plan fixture requires the real sealed capture and native context policy.');
    }
    expect(request.owner_scope.world_id).toBe(world);
    expect(capture.world_id).toBe(world);
    expect(capture.document_id).toBe(documentId);
    expect(capture.idempotency_key).toBe(correlationKey(world, request.turn_id));
    expect(capture.conversation_id).toBe(conversationId);
    expect(capture.expected_pointer_revision).toBe(4);
    expect(request.plan_placement_catalog?.original_capture_sha256).toBe(hash(canonical(capture)));
    const provenance: AgentConversationTurnProvenanceV1 = {
      world_id: world, surface_resolution: 'resolved', surface_id: 'plan',
      surface_instance_id: request.surface.instance_id,
      primary_work: {resolution: 'resolved', kind: 'plan', object_id: documentId,
        revision: String(record.revision), content_sha256: digest,
        object_revision: record.revision, work_revision_id: workRevision, revision_n: revisionN},
      supporting_work: [],
      selected_object: {resolution: 'absent', kind: null, object_id: null, revision: null,
        content_sha256: null, object_revision: null, work_revision_id: null, revision_n: null},
    };
    // Rebind the APP-shaped native fixture only at client-verifiable identities.
    // This does not establish APP admission, provider execution or Graph semantics.
    const context = structuredClone(openingWire.context) as AgentSurfaceNativeContextResponseV1;
    const work = context.receipt.work_context;
    if (work.surface_id !== 'plan') throw new Error('Expected a native Plan fixture.');
    work.plan_basis = basis();
    work.plan_context_policy = request.plan_context_policy;
    work.playable_target = null;
    const authority = context.receipt.source_authority;
    const query = context.receipt.native_query;
    if (!('schema_version' in authority) || !('authority' in query)) throw new Error('Expected native authority.');
    Object.assign(authority, {managed_world_id: world, native_world_id: world});
    Object.assign(query.authority, {managed_world_id: world, native_world_id: world});
    query.question = request.message;
    context.receipt.provenance_sha256 = hash(canonical(provenance));
    if ('submitted_intent_sha256' in context.receipt.assembled_input) {
      context.receipt.assembled_input.submitted_intent_sha256 = hash(request.message);
    }
    const {context_receipt_sha256: _previous, ...payload} = context.receipt;
    context.receipt.context_receipt_sha256 = hash(canonical(payload));
    context.completion = {
      schema: 'dmb_surface_native_completion_v1', surface_id: 'plan',
      context_receipt_sha256: context.receipt.context_receipt_sha256,
      producing_provider_attempt_id: '22222222-2222-4222-8222-222222222222',
      answer_basis: 'mixed_evidence', answer_context_status: 'creative_proposal',
      answer_segments: [{kind: 'proposal', label: 'invented_idea', text: readyText}], collaboration: null,
      saved_source_citations: [], native_body_citations: [], native_clause_citations: [], native_assertion_citations: [],
    };
    proposal = {
      schema: 'dmb_plan_authored_proposal_v1', capture: structuredClone(capture), replacement_markdown: replacement,
      origin: {
        schema: 'dmb_plan_jev_proposal_origin_v1', action_id: actionId,
        idempotency_key: capture.idempotency_key, action_request_fingerprint: hash('synthetic request'),
        action_fence: 1, basis: basis(), conversation_id: conversationId, turn_id: request.turn_id,
        product_attempt: 1, expected_pointer_revision: 4,
        context_receipt_sha256: context.receipt.context_receipt_sha256, execution_policy_sha256: hash('synthetic policy'),
        capture_sha256: hash(canonical(capture)),
        controller_attempt_id: '33333333-3333-4333-8333-333333333333',
        selection_event_id: '44444444-4444-4444-8444-444444444444', expected_turn_revision: 2,
        writer_attempt_id: '55555555-5555-4555-8555-555555555555',
        writer_envelope_sha256: hash('synthetic writer'), raw_reply_sha256: hash(replacement),
        evidence_event_ids: [], replacement_markdown_sha256: hash(replacement),
      },
    };
    originHash = hash(canonical(proposal.origin));
    turns.push({
      idempotency_key: capture.idempotency_key, turn_id: request.turn_id, sequence: turns.length + 1,
      lifecycle_status: 'completed', user_text: request.message, assistant_text: readyText,
      provenance, plan_context: context, plan_proposal: proposal,
    } as WorldAgentConversationHistoryTurnV3);
    const response: WorldPlanAgentTurnResponse = {
      schema: 'dmb_agent_turn_response_v2', client_thread_id: request.client_thread_id, turn_id: request.turn_id,
      surface: {surface_id: 'plan', instance_id: request.surface.instance_id, status: 'resolved'},
      owner_scope: {status: 'resolved', kind: 'world', owner_id: world, name: 'Integration World'},
      primary_work: {status: 'resolved', kind: 'plan', object_id: documentId,
        revision_used: record.revision, expected_revision: request.primary_work.expected_revision,
        content_basis: {...basis(), committed_status: 'committed', has_divergent_working_copy: false}},
      client_work_state_reported: request.client_work_state,
      graph: {status: 'not_requested', world_id: null, campaign_id: null, scope_mode: null,
        revision_id: null, focus: null, selection_node_id: null, selection_found: null,
        head_revision_id: null, is_head: null},
      conversation: {client_thread_id: request.client_thread_id, turn_id: request.turn_id,
        pointer_status: 'accepted', pointer_id: null, conversation_id: conversationId},
      answer: {status: 'ok', text: readyText, code: null, message: null, graph_grounded: false, trace: {}},
      plan_context: context, plan_proposal: proposal,
    };
    return response;
  });

  vi.spyOn(reviewApi, 'readPlanAuthoringReview').mockImplementation(async (requestedWorld, action) => (expect([requestedWorld, action]).toEqual([world, actionId]), {
    schema: 'dmb_plan_authoring_review_snapshot_v1', world_id: world, action_id: actionId,
    origin_sha256: originHash, review: structuredClone(review),
  }));
  const commands = vi.spyOn(reviewApi, 'commandPlanAuthoringReview').mockImplementation(async (_world, _action, command) => {
    if (!proposal) throw new Error('A sealed current proposal must exist first.');
    expect(_world).toBe(world);
    expect(_action).toBe(actionId);
    expect(command.expected_revision).toBe(review?.revision ?? 0);
    expect(command.origin_sha256).toBe(originHash);
    if (command.operation === 'open') {
      review = {schema: 'dmb_plan_authoring_review_v1', world_id: world, action_id: actionId,
        origin_sha256: originHash, revision: 0, state: 'editing', markdown: proposal.replacement_markdown,
        markdown_sha256: hash(proposal.replacement_markdown), capture: proposal.capture, applications: [],
        last_command_id: command.command_id, last_command_sha256: hash(canonical(command)), updated_at: '2026-11-19T00:00:00Z'};
    }
    if (!review) throw new Error('Review must be opened before another operation.');
    if (command.operation === 'move') review = {...review, capture: command.capture};
    if (command.operation === 'save') review = {...review, markdown: command.markdown, markdown_sha256: hash(command.markdown)};
    if (command.operation === 'prepare') {
      const application: PlanReviewApplication = {
        ...command, capture: review.capture, markdown: review.markdown, markdown_sha256: review.markdown_sha256,
        base_work_revision_id: workRevision, base_revision_n: revisionN, outcome: 'applying',
        saved_work_revision_id: null, saved_revision_n: null,
      };
      review = {...review, state: 'applying', applications: [application]};
    }
    if (command.operation === 'confirm') {
      const application = review.applications.find(row => row.application_id === command.application_id);
      if (!application) throw new Error('Expected the exact prepared application.');
      markdown = application.after_markdown;
      digest = application.after_draft_sha256;
      expect(digest).toBe(hash(markdown));
      record = {...record, revision: record.revision + 1, updated_at: '2026-11-19T00:01:00Z'};
      workRevision = nextWork;
      revisionN += 1;
      review = {...review, state: 'applied', applications: [{...application, outcome: 'saved',
        saved_work_revision_id: workRevision, saved_revision_n: revisionN}]};
    }
    review = {...review, revision: review.revision + 1, last_command_id: command.command_id,
      last_command_sha256: hash(canonical(command)), updated_at: '2026-11-19T00:01:00Z'};
    return structuredClone(review);
  });
  return {post, commands, legacyProposal, ordinaryPrepare, ordinaryCommit,
    readSaved: () => ({record: {...record}, markdown, digest, workRevision, revisionN}),
    readReview: () => structuredClone(review)};
}
