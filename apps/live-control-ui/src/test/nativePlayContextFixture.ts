import wire from './nativePlayReceipt.json';
import { fixtureHash } from './rulesAnswerFixture';
import { rulesCanonical } from '../rulesLookup/rulesCanonical';
import type { AgentConversationTurnProvenanceV1, WorldPlayAgentContextV1, WorldPlayAgentTurnRequestV1, WorldPlayGraphContextReceiptV1 } from '../api/types';

/** APP-serialized native receipt, rebound explicitly to the submitted synthetic Run fixture. */
export function nativePlayContextFixture(request: WorldPlayAgentTurnRequestV1, answer = 'Original Play answer'): WorldPlayAgentContextV1 {
  const r = structuredClone(wire) as WorldPlayGraphContextReceiptV1, b = r.play_basis;
  if (!request.primary_work.play_content_basis || !request.play_target) throw new Error('Native fixture requires the actual submitted edition and target');
  Object.assign(b, request.primary_work.play_content_basis, request.play_target, { world_id: request.owner_scope.world_id,
    run_id: request.primary_work.object_id, run_revision: request.primary_work.expected_revision });
  if (b.edition_revision === 0) b.runbook_content_sha256 = b.content_sha256;
  if (b.scene_id === null) { b.scene_note = null; b.scene_note_sha256 = null; }
  r.graph_authority.managed_world_id = b.world_id;
  r.play_sources.entries = r.play_sources.entries.filter(e => b.scene_id !== null || e.source_kind !== 'scene_note');
  for (const e of r.play_sources.entries) {
    const text = e.source_kind === 'scene_note' ? b.scene_note! : '# North\nThe prepared boardwalk 🦉 scene.';
    e.locator = { world_id: b.world_id, run_id: b.run_id, run_revision: b.run_revision,
      edition: request.primary_work.play_content_basis, beat_id: b.beat_id, scene_id: b.scene_id };
    const payload = rulesCanonical({ schema: 'dmb_play_source_payload_v1', source_kind: e.source_kind, locator: e.locator, text });
    e.payload_sha256 = fixtureHash(payload); e.source_id = 'play-source:' + e.payload_sha256;
    e.payload_utf8_bytes = new TextEncoder().encode(payload).length;
    e.text_sha256 = fixtureHash(text); e.text_utf8_bytes = new TextEncoder().encode(text).length; e.text_codepoints = Array.from(text).length;
  }
  r.play_sources.entries.sort((a,b) => a.source_id < b.source_id ? -1 : 1);
  const { manifest_sha256: _, ...manifest } = r.play_sources;
  r.play_sources.manifest_sha256 = fixtureHash(rulesCanonical(manifest));
  r.play_source_frame_sha256 = fixtureHash(rulesCanonical({ schema: 'dmb_play_source_frame_v1', manifest: r.play_sources,
    sources: r.play_sources.entries.map(e => ({ schema: 'dmb_play_source_payload_v1', source_kind: e.source_kind, locator: e.locator,
      text: e.source_kind === 'scene_note' ? b.scene_note! : '# North\nThe prepared boardwalk 🦉 scene.' })) }));
  const { context_receipt_sha256: __, ...body } = r;
  r.context_receipt_sha256 = fixtureHash(rulesCanonical(body));
  return { schema: 'dmb_agent_play_world_graph_context_response_v1', receipt: r, delivery_replay: false,
    execution: { schema: 'dmb_agent_plan_world_graph_execution_projection_v1', claimability: 'completed', authorization_state: 'response_received', automatic_redispatch: false },
    completion: { schema: 'dmb_play_world_graph_completion_v1', context_receipt_sha256: r.context_receipt_sha256,
      answer_basis: 'play_sources', answer_context_status: 'play_only_graph_unused',
      answer_segments: [{ kind: 'play_context_claim', text: answer, source_ids: [r.play_sources.entries[0]!.source_id] }], citation_map: null } };
}
export function nativePlayProvenanceFixture(context: WorldPlayAgentContextV1): AgentConversationTurnProvenanceV1 {
  const b = context.receipt.play_basis, a = context.receipt.graph_authority;
  const ref = (kind: string, object_id: string, revision: string, extra = {}) => ({ resolution: 'resolved' as const, kind, object_id, revision,
    content_sha256: null, object_revision: null, work_revision_id: null, revision_n: null, ...extra });
  return { world_id: b.world_id, surface_resolution: 'resolved', surface_id: 'play', surface_instance_id: 'play-instance',
    primary_work: ref('run', b.run_id, String(b.run_revision)), selected_object: { resolution: 'absent', kind: null, object_id: null,
      revision: null, content_sha256: null, object_revision: null, work_revision_id: null, revision_n: null },
    supporting_work: [ref('dmb_play_runbook_v1', b.runbook_object_id, String(b.runbook_object_revision), {
      object_revision: b.runbook_object_revision, work_revision_id: b.runbook_work_revision_id, revision_n: b.runbook_revision_n, content_sha256: b.runbook_content_sha256 }),
      ref('dmb_play_current_beat_v1', b.beat_id, 'v2'), ...(b.scene_id ? [ref('dmb_play_current_scene_v1', b.scene_id, 'v2')] : []),
      ref('dmb_play_graph_binding_v1', a.native_world_id, String(a.binding_version)), ref('world_graph_revision', a.native_world_id, a.graph_revision)] };
}

export function nativePlayRequestFixture(): WorldPlayAgentTurnRequestV1 {
  return { schema: 'dmb_agent_turn_request_v1', client_thread_id: 'thread', turn_id: 'turn',
    surface: { surface_id: 'play', instance_id: 'play-instance' }, owner_scope: { kind: 'world', world_id: 'world-one' },
    primary_work: { kind: 'run', object_id: 'run-one', expected_revision: 3,
      play_content_basis: { edition_revision: 0, edition_revision_id: null, content_sha256: 'a'.repeat(64) } },
    play_target: { beat_id: 'beat:crossing', scene_id: 'scene:west-gate', marker_grammar_version: 'v2' }, client_work_state: 'saved_clean',
    graph_request: { mode: 'world', world_id: 'world-one', campaign_id: null, revision_pin: null,
      focus: { kind: 'none', session_id: null, campaign_id: null } }, graph_selection: null, message: 'Question' };
}
