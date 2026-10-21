import { webcrypto } from 'node:crypto';
import { beforeEach, expect, it, vi } from 'vitest';
import wire from '../test/nativePlayReceipt.json';
import type { WorldPlayAgentTurnRequestV1 } from '../api/types';
import { isWorldPlayGraphReceipt, playReceiptDigestsBound } from './playContextProtocol';
import { rulesCanonical, rulesDigest } from './rulesCanonical';

// Generated from tests.test_play_graph_context.fixture(), then serialized by the APP type owner.
const receipt = () => structuredClone(wire);
const request = (): WorldPlayAgentTurnRequestV1 => ({
  schema: 'dmb_agent_turn_request_v1', client_thread_id: 'thread', turn_id: 'turn',
  surface: { surface_id: 'play', instance_id: 'play' }, owner_scope: { kind: 'world', world_id: 'world-one' },
  primary_work: { kind: 'run', object_id: 'run-one', expected_revision: 3,
    play_content_basis: { edition_revision: 0, edition_revision_id: null, content_sha256: 'a'.repeat(64) } },
  play_target: { beat_id: 'beat:north', scene_id: 'scene:boardwalk', marker_grammar_version: 'v2' },
  client_work_state: 'saved_clean', graph_request: { mode: 'world', world_id: 'world-one', campaign_id: null,
    revision_pin: null, focus: { kind: 'none', session_id: null, campaign_id: null } }, graph_selection: null, message: 'Question',
});
beforeEach(() => vi.stubGlobal('crypto', webcrypto));
it('admits the actual APP receipt and Unicode saved-note commitments without fetching source bodies', async () => {
  const fetch = vi.fn(); vi.stubGlobal('fetch', fetch);
  expect(isWorldPlayGraphReceipt(receipt(), request())).toBe(true);
  expect(await playReceiptDigestsBound(receipt())).toBe(true);
  expect(fetch).not.toHaveBeenCalled();
});
it.each(['world', 'run', 'revision', 'edition', 'digest', 'beat', 'scene', 'missing-target', 'missing-edition', 'graphless'])('refuses a foreign submitted %s basis', kind => {
  const r = request();
  if (kind === 'world') r.owner_scope.world_id = 'other';
  if (kind === 'run') r.primary_work.object_id = 'other';
  if (kind === 'revision') r.primary_work.expected_revision++;
  if (kind === 'edition') Object.assign(r.primary_work.play_content_basis!, { edition_revision: 1, edition_revision_id: '00000000-0000-4000-8000-000000000002' });
  if (kind === 'digest') r.primary_work.play_content_basis!.content_sha256 = 'f'.repeat(64);
  if (kind === 'beat') r.play_target!.beat_id = 'beat:other';
  if (kind === 'scene') r.play_target!.scene_id = 'scene:other';
  if (kind === 'missing-target') delete r.play_target;
  if (kind === 'missing-edition') delete r.primary_work.play_content_basis;
  if (kind === 'graphless') r.graph_request = { mode: 'none' };
  expect(isWorldPlayGraphReceipt(receipt(), r)).toBe(false);
});
it.each(['schema', 'extra', 'marker', 'edition', 'origin', 'note', 'note-utf8', 'note-size', 'locator', 'handle', 'duplicate',
  'source-order', 'kind', 'source-size', 'tokens', 'plan-accounting', 'plan-packet', 'candidate', 'scope', 'selected-index'])('refuses malformed native %s metadata', async kind => {
  const r = receipt(), b = r.play_basis, e = r.play_sources.entries[0]!;
  if (kind === 'schema') r.schema = 'dmb_agent_plan_world_graph_context_receipt_v1';
  if (kind === 'extra') Object.assign(r, { plan_basis: b });
  if (kind === 'marker') b.beat_id = 'beat:UPPER:case';
  if (kind === 'edition') b.edition_revision = 1;
  if (kind === 'origin') b.content_sha256 = 'e'.repeat(64);
  if (kind === 'note') b.scene_note_sha256 = null as unknown as string;
  if (kind === 'note-utf8') b.scene_note = '\ud800';
  if (kind === 'note-size') b.scene_note = '🦉'.repeat(9000);
  if (kind === 'locator') e.locator.run_id = 'other';
  if (kind === 'handle') e.source_id = 'play-source:' + 'e'.repeat(64);
  if (kind === 'duplicate') r.play_sources.entries[1] = structuredClone(e);
  if (kind === 'source-order') r.play_sources.entries.reverse();
  if (kind === 'kind') e.source_kind = 'old_source';
  if (kind === 'source-size') e.text_utf8_bytes = 32769;
  if (kind === 'tokens') r.assembled_input.provider_envelope_input_tokens = 1024;
  if (kind === 'plan-accounting') r.assembled_input.source_token_accounting[0]!.source_kind = 'plan';
  if (kind === 'plan-packet') r.graph_packet.schema = 'dmb_plan_world_graph_packet_v1';
  if (kind === 'candidate') r.assembled_input.dispatched_assertion_ids.push('unadmitted');
  if (kind === 'scope') r.graph_authority.managed_world_id = 'other';
  if (kind === 'selected-index') r.graph_packet.selection_policy_version = 'parent_initial_retrieval_with_selected_source_index_v1';
  expect(isWorldPlayGraphReceipt(r)).toBe(false);
  expect(await playReceiptDigestsBound(r)).toBe(false);
});
it.each(['receipt', 'manifest', 'note', 'note-payload'])('rechecks the %s commitment even with a newly sealed outer receipt', async kind => {
  const r = receipt();
  if (kind === 'receipt') r.play_source_frame_sha256 = 'e'.repeat(64);
  if (kind === 'manifest') r.play_sources.manifest_sha256 = 'e'.repeat(64);
  if (kind === 'note') {
    r.play_basis.scene_note = 'Altered 🦉 text.';
    const e = r.play_sources.entries.find(e => e.source_kind === 'scene_note')!;
    e.text_utf8_bytes = new TextEncoder().encode(r.play_basis.scene_note).length;
    e.text_codepoints = Array.from(r.play_basis.scene_note).length;
  }
  if (kind === 'note-payload') r.play_sources.entries.find(e => e.source_kind === 'scene_note')!.payload_utf8_bytes++;
  if (kind !== 'receipt') {
    const { manifest_sha256: _, ...m } = r.play_sources;
    if (kind !== 'manifest') r.play_sources.manifest_sha256 = await rulesDigest(rulesCanonical(m));
    const { context_receipt_sha256: __, ...body } = r;
    r.context_receipt_sha256 = await rulesDigest(rulesCanonical(body));
  }
  expect(isWorldPlayGraphReceipt(r)).toBe(true);
  expect(await playReceiptDigestsBound(r)).toBe(false);
});

it('validates native completion and provenance as a distinct Play domain', async () => {
  const { nativePlayContextFixture, nativePlayProvenanceFixture, nativePlayRequestFixture } = await import('../test/nativePlayContextFixture');
  const { isWorldPlayContextProjection, isPlayContextProvenanceBound } = await import('./playContextProtocol');
  const r = nativePlayRequestFixture(), c = nativePlayContextFixture(r);
  expect(isWorldPlayContextProjection(c, () => true, r)).toBe(true);
  expect(await playReceiptDigestsBound(c.receipt)).toBe(true);
  expect(isPlayContextProvenanceBound(c.receipt, nativePlayProvenanceFixture(c), r.owner_scope.world_id)).toBe(true);
});
it.each(['source', 'plan-cast', 'basis', 'status', 'receipt', 'citation', 'text', 'extra', 'execution', 'replay'])('rejects a mismatched native completion: %s', async kind => {
  const { nativePlayContextFixture, nativePlayRequestFixture } = await import('../test/nativePlayContextFixture');
  const { isWorldPlayContextProjection } = await import('./playContextProtocol');
  const r = nativePlayRequestFixture(), c = nativePlayContextFixture(r), completion = c.completion!;
  if (kind === 'source') Object.assign(completion.answer_segments[0]!, { source_ids: ['play-source:' + 'f'.repeat(64)] });
  if (kind === 'plan-cast') completion.answer_segments = [{ kind: 'plan_claim', text: 'Foreign', plan_content_sha256: 'a'.repeat(64) }] as never;
  if (kind === 'basis') completion.answer_basis = 'world_graph';
  if (kind === 'status') completion.answer_context_status = 'graph_grounded';
  if (kind === 'receipt') completion.context_receipt_sha256 = 'f'.repeat(64);
  if (kind === 'citation') completion.citation_map = { schema: 'dmb_graph_citation_map_v2', context_receipt_sha256: c.receipt.context_receipt_sha256, entries: [] };
  if (kind === 'text') completion.answer_segments[0]!.text = '🦉'.repeat(4001);
  if (kind === 'extra') Object.assign(c, { plan_context: null });
  if (kind === 'execution') c.execution = {} as never;
  if (kind === 'replay') { c.completion = null; c.delivery_replay = true; }
  expect(isWorldPlayContextProjection(c, v => !!v && 'schema' in (v as object), r)).toBe(false);
});
it.each(['duplicate', 'run', 'runbook', 'binding', 'revision', 'scene', 'world', 'surface', 'selected'])('rejects a foreign native provenance: %s', async kind => {
  const { nativePlayContextFixture, nativePlayProvenanceFixture, nativePlayRequestFixture } = await import('../test/nativePlayContextFixture');
  const { isPlayContextProvenanceBound } = await import('./playContextProtocol');
  const c = nativePlayContextFixture(nativePlayRequestFixture()), p = nativePlayProvenanceFixture(c);
  if (kind === 'duplicate') p.supporting_work.push(structuredClone(p.supporting_work[0]!));
  if (kind === 'run') p.primary_work.revision = '4';
  if (kind === 'runbook') p.supporting_work[0]!.content_sha256 = 'f'.repeat(64);
  if (kind === 'binding') p.supporting_work.find(r => r.kind === 'dmb_play_graph_binding_v1')!.revision = '2';
  if (kind === 'revision') p.supporting_work.find(r => r.kind === 'world_graph_revision')!.revision = 'other';
  if (kind === 'scene') p.supporting_work.find(r => r.kind === 'dmb_play_current_scene_v1')!.object_id = 'scene:other';
  if (kind === 'world') p.world_id = 'other';
  if (kind === 'surface') p.surface_id = 'plan';
  if (kind === 'selected') p.selected_object.resolution = 'resolved';
  expect(isPlayContextProvenanceBound(c.receipt, p, 'world-one')).toBe(false);
});

it.each(['valid', 'wrong-map', 'duplicate', 'opened-flag', 'old-map', 'revision'])('validates native Graph citations without retyping them as Play claims: %s', async kind => {
  const { nativePlayContextFixture, nativePlayRequestFixture } = await import('../test/nativePlayContextFixture');
  const { isWorldPlayContextProjection } = await import('./playContextProtocol');
  const c = nativePlayContextFixture(nativePlayRequestFixture()), completion = c.completion!;
  const claim = { kind: 'graph_claim' as const, claim_id: 'claim-one', text: 'A supported World fact.', target_kind: 'assertion' as const,
    target_id: 'dynamic-target', graph_revision: c.receipt.graph_authority.graph_revision, evidence_ref_ids: ['evidence-one'] };
  completion.answer_segments.push(claim); completion.answer_basis = 'play_sources_plus_world_graph'; completion.answer_context_status = 'graph_grounded';
  const { kind: _, text: __, ...identity } = claim;
  completion.citation_map = { schema: 'dmb_graph_citation_map_v2', context_receipt_sha256: c.receipt.context_receipt_sha256,
    entries: [{ ...identity, source_opened: true, source_read_ids: ['read-one'] }] };
  const e = completion.citation_map.entries[0]!;
  if (kind === 'wrong-map') e.target_id = 'other';
  if (kind === 'duplicate') completion.citation_map.entries.push(structuredClone(e));
  if (kind === 'opened-flag') e.source_opened = false;
  if (kind === 'old-map') Object.assign(completion.citation_map, { schema: 'dmb_graph_citation_map_v1' });
  if (kind === 'revision') claim.graph_revision = 'other';
  expect(isWorldPlayContextProjection(c, () => true)).toBe(kind === 'valid');
});
