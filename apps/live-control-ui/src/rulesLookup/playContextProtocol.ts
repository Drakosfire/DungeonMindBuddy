import type { WorldPlayAgentTurnRequestV1, WorldPlayGraphContextReceiptV1 } from '../api/types';
import { rulesCanonical, rulesDigest } from './rulesCanonical';
import { isSurfaceGraphInput } from './surfaceGraphInput';

const record = (v: unknown): v is Record<string, unknown> => v !== null && typeof v === 'object' && !Array.isArray(v);
const keys = (v: unknown, required: string[]): v is Record<string, unknown> => record(v)
  && Object.keys(v).length === required.length && required.every(k => Object.prototype.hasOwnProperty.call(v, k));
const digest = (v: unknown): v is string => typeof v === 'string' && /^[a-f0-9]{64}$/.test(v);
const integer = (v: unknown, min: number, max = Number.MAX_SAFE_INTEGER): v is number => Number.isSafeInteger(v) && (v as number) >= min && (v as number) <= max;
const owner = (v: unknown): v is string => typeof v === 'string' && v.length > 0 && v.length <= 128 && v.trim() === v;
const uuid = (v: unknown): v is string => typeof v === 'string' && /^[a-f0-9]{8}-(?:[a-f0-9]{4}-){3}[a-f0-9]{12}$/.test(v);
const marker = (v: unknown, kind: 'beat' | 'scene'): v is string => typeof v === 'string' && v.length <= 135
  && new RegExp(`^${kind}:[a-z0-9][a-z0-9._-]{0,127}$`).test(v);
const bytes = (s: string) => new TextEncoder().encode(s).length;
function unicode(s: string): boolean {
  for (let i = 0; i < s.length; i++) {
    const c = s.charCodeAt(i);
    if (c >= 0xd800 && c <= 0xdbff) {
      const next = s.charCodeAt(++i);
      if (!(next >= 0xdc00 && next <= 0xdfff)) return false;
    } else if (c >= 0xdc00 && c <= 0xdfff) return false;
  }
  return true;
}
const edition = (v: unknown): boolean => keys(v, ['edition_revision', 'edition_revision_id', 'content_sha256'])
  && integer(v.edition_revision, 0) && digest(v.content_sha256)
  && (v.edition_revision === 0 ? v.edition_revision_id === null : uuid(v.edition_revision_id));

/** Pure, bounded native Play metadata admission. No source retrieval or Plan conversion. */
export function isWorldPlayGraphReceipt(value: unknown, request?: WorldPlayAgentTurnRequestV1): value is WorldPlayGraphContextReceiptV1 {
  if (!keys(value, ['schema', 'receipt_serializer_version', 'context_receipt_sha256', 'play_graph_policy', 'play_basis',
    'play_sources', 'play_source_frame_sha256', 'retrieval_session_id', 'graph_authority', 'graph_packet', 'assembled_input', 'evidence_mode', 'source_opened'])
    || value.schema !== 'dmb_play_world_graph_context_receipt_v1' || value.receipt_serializer_version !== 'canonical-json-utf8-v1'
    || !digest(value.context_receipt_sha256) || !digest(value.play_source_frame_sha256) || !owner(value.retrieval_session_id)
    || value.evidence_mode !== 'metadata_only' || value.source_opened !== false
    || !keys(value.play_graph_policy, ['schema', 'policy']) || value.play_graph_policy.schema !== 'dmb_play_graph_policy_v1'
    || value.play_graph_policy.policy !== 'native_play_world_v1') return false;
  const b = value.play_basis;
  if (!keys(b, ['schema', 'world_id', 'run_id', 'run_revision', 'runbook_object_id', 'runbook_object_revision',
    'runbook_work_revision_id', 'runbook_revision_n', 'runbook_content_sha256', 'beat_id', 'scene_id', 'marker_grammar_version',
    'edition_revision', 'edition_revision_id', 'content_sha256', 'scene_note', 'scene_note_sha256'])
    || b.schema !== 'dmb_play_run_turn_context_receipt_v2' || !owner(b.world_id) || !owner(b.run_id) || !owner(b.runbook_object_id)
    || !integer(b.run_revision, 1) || !integer(b.runbook_object_revision, 1) || !integer(b.runbook_revision_n, 1)
    || !uuid(b.runbook_work_revision_id) || !digest(b.runbook_content_sha256)
    || !edition({ edition_revision: b.edition_revision, edition_revision_id: b.edition_revision_id, content_sha256: b.content_sha256 })
    || (b.edition_revision === 0 && b.content_sha256 !== b.runbook_content_sha256)
    || !marker(b.beat_id, 'beat') || !(b.scene_id === null || marker(b.scene_id, 'scene')) || b.marker_grammar_version !== 'v2'
    || (b.scene_id === null && (b.scene_note !== null || b.scene_note_sha256 !== null))
    || (b.scene_note === null ? b.scene_note_sha256 !== null : typeof b.scene_note !== 'string' || !unicode(b.scene_note)
      || bytes(b.scene_note) > 32768 || !digest(b.scene_note_sha256))) return false;
  const m = value.play_sources;
  if (!keys(m, ['schema', 'entries', 'manifest_sha256']) || m.schema !== 'dmb_play_source_manifest_v1'
    || !digest(m.manifest_sha256) || !Array.isArray(m.entries) || m.entries.length > 2) return false;
  const locator = { world_id: b.world_id, run_id: b.run_id, run_revision: b.run_revision,
    edition: { edition_revision: b.edition_revision, edition_revision_id: b.edition_revision_id, content_sha256: b.content_sha256 },
    beat_id: b.beat_id, scene_id: b.scene_id };
  const kinds = new Set();
  let previous = '';
  for (const e of m.entries) {
    if (!keys(e, ['source_id', 'source_kind', 'locator', 'payload_sha256', 'payload_utf8_bytes', 'text_sha256', 'text_utf8_bytes', 'text_codepoints'])
      || !['current_moment', 'scene_note'].includes(String(e.source_kind)) || kinds.has(e.source_kind)
      || !digest(e.payload_sha256) || e.source_id !== 'play-source:' + e.payload_sha256 || e.source_id <= previous
      || !digest(e.text_sha256) || !integer(e.payload_utf8_bytes, 1, 49152) || !integer(e.text_utf8_bytes, 1, 32768)
      || !integer(e.text_codepoints, 1, 32000) || e.text_utf8_bytes < e.text_codepoints || e.text_utf8_bytes > 4 * e.text_codepoints
      || rulesCanonical(e.locator) !== rulesCanonical(locator)
      || (e.source_kind === 'scene_note' && (b.scene_note === null || e.text_sha256 !== b.scene_note_sha256
        || e.text_utf8_bytes !== bytes(b.scene_note as string) || e.text_codepoints !== Array.from(b.scene_note as string).length))) return false;
    previous = e.source_id; kinds.add(e.source_kind);
  }
  if (!isSurfaceGraphInput({ graph_authority: value.graph_authority, graph_packet: value.graph_packet,
    assembled_input: value.assembled_input }, b.world_id, 'dmb_play_world_graph_packet_v1',
    ['play', 'history', 'graph', 'instructions', 'tools', 'message', 'rules'])
    || !record(value.graph_authority) || value.graph_authority.admissibility_version !== 'gm-v1'
    || !owner(value.graph_authority.native_world_id) || !record(value.graph_packet)
    || value.graph_packet.selection_policy_version === 'parent_initial_retrieval_with_selected_source_index_v1') return false;
  if (!request) return true;
  return request.surface.surface_id === 'play' && request.primary_work.kind === 'run'
    && request.graph_request.mode === 'world' && request.graph_request.world_id === b.world_id
    && request.owner_scope.world_id === b.world_id && request.primary_work.object_id === b.run_id
    && request.primary_work.expected_revision === b.run_revision
    && rulesCanonical(request.primary_work.play_content_basis) === rulesCanonical(locator.edition)
    && !!request.play_target && request.play_target.beat_id === b.beat_id && request.play_target.scene_id === b.scene_id
    && request.play_target.marker_grammar_version === b.marker_grammar_version;
}

/** Verify only committed metadata and the inline saved note; never re-fetch Run or corpus content. */
export async function playReceiptDigestsBound(value: unknown): Promise<boolean> {
  if (!isWorldPlayGraphReceipt(value)) return false;
  const { context_receipt_sha256, ...body } = value;
  const { manifest_sha256, ...manifest } = value.play_sources;
  const raw = rulesCanonical(value);
  if (bytes(raw) > 131072 || !unicode(raw)
    || await rulesDigest(rulesCanonical(body)) !== context_receipt_sha256
    || await rulesDigest(rulesCanonical(manifest)) !== manifest_sha256) return false;
  const note = value.play_basis.scene_note;
  if (note !== null && await rulesDigest(note) !== value.play_basis.scene_note_sha256) return false;
  for (const entry of value.play_sources.entries) {
    if (entry.source_kind !== 'scene_note') continue;
    const payload = rulesCanonical({ schema: 'dmb_play_source_payload_v1', source_kind: 'scene_note', locator: entry.locator, text: note });
    if (bytes(payload) !== entry.payload_utf8_bytes || await rulesDigest(payload) !== entry.payload_sha256) return false;
  }
  return true;
}

/** Native Play segments and citations retain their own source domain. */
export function isWorldPlayGraphCompletion(value: unknown, receipt: WorldPlayGraphContextReceiptV1): value is import('../api/types').WorldPlayGraphCompletionV1 {
  if (!keys(value, ['schema', 'context_receipt_sha256', 'answer_basis', 'answer_context_status', 'answer_segments', 'citation_map'])
    || value.schema !== 'dmb_play_world_graph_completion_v1' || value.context_receipt_sha256 !== receipt.context_receipt_sha256
    || !['graph_grounded', 'graph_grounded_partial', 'play_only_insufficient_evidence', 'play_only_graph_unused'].includes(String(value.answer_context_status))
    || !Array.isArray(value.answer_segments) || !value.answer_segments.length || value.answer_segments.length > 128) return false;
  const sources = new Set(receipt.play_sources.entries.map(e => e.source_id));
  const claims = new Map<string, Record<string, unknown>>();
  let play = false;
  const text = (v: unknown): v is string => typeof v === 'string' && !!v.trim() && unicode(v) && Array.from(v).length <= 4000;
  const sorted = (v: unknown, max: number, min = 0): v is string[] => Array.isArray(v) && v.length >= min && v.length <= max
    && v.every((id, i) => typeof id === 'string' && !!id.trim() && id === id.trim() && (!i || v[i-1] < id));
  for (const s of value.answer_segments) {
    if (!record(s) || !text(s.text)) return false;
    if (s.kind === 'connective') { if (!keys(s, ['kind', 'text'])) return false; }
    else if (s.kind === 'play_context_claim') {
      if (!keys(s, ['kind', 'text', 'source_ids']) || !sorted(s.source_ids, 2, 1) || s.source_ids.some(id => !sources.has(id))) return false;
      play = true;
    } else if (s.kind === 'graph_claim') {
      if (!keys(s, ['kind', 'text', 'claim_id', 'target_kind', 'target_id', 'graph_revision', 'evidence_ref_ids'])
        || typeof s.claim_id !== 'string' || !s.claim_id.trim() || claims.has(s.claim_id)
        || !['assertion', 'relationship'].includes(String(s.target_kind)) || typeof s.target_id !== 'string' || !s.target_id.trim()
        || s.graph_revision !== receipt.graph_authority.graph_revision || !sorted(s.evidence_ref_ids, 64, 1)) return false;
      claims.set(s.claim_id, s);
    } else return false;
  }
  const graph = claims.size > 0;
  const basis = graph ? (play ? 'play_sources_plus_world_graph' : 'world_graph') : play ? 'play_sources' : 'nonfactual_context';
  if (value.answer_basis !== basis || graph !== ['graph_grounded', 'graph_grounded_partial'].includes(String(value.answer_context_status))) return false;
  const citations = value.citation_map;
  if (!graph) { if (citations !== null) return false; }
  else {
    if (!keys(citations, ['schema', 'context_receipt_sha256', 'entries']) || citations.schema !== 'dmb_graph_citation_map_v2'
      || citations.context_receipt_sha256 !== receipt.context_receipt_sha256 || !Array.isArray(citations.entries) || citations.entries.length !== claims.size) return false;
    const seen = new Set();
    for (const e of citations.entries) {
      if (!keys(e, ['claim_id', 'target_kind', 'target_id', 'graph_revision', 'evidence_ref_ids', 'source_opened', 'source_read_ids'])
        || typeof e.claim_id !== 'string' || seen.has(e.claim_id) || !sorted(e.source_read_ids, 16384)
        || e.source_opened !== (e.source_read_ids.length > 0)) return false;
      const c = claims.get(e.claim_id);
      if (!c || ['target_kind', 'target_id', 'graph_revision', 'evidence_ref_ids'].some(k => rulesCanonical(c[k]) !== rulesCanonical(e[k]))) return false;
      seen.add(e.claim_id);
    }
  }
  return bytes(rulesCanonical(value)) <= 65536;
}

export function isWorldPlayContextProjection(value: unknown, validateExecution: (v: unknown) => boolean,
  request?: WorldPlayAgentTurnRequestV1, history = false): value is import('../api/types').WorldPlayAgentContextV1 {
  if (!keys(value, ['schema', 'receipt', 'completion', 'execution', 'delivery_replay'])
    || value.schema !== 'dmb_agent_play_world_graph_context_response_v1' || !isWorldPlayGraphReceipt(value.receipt, request)
    || typeof value.delivery_replay !== 'boolean' || (value.execution !== null && !validateExecution(value.execution))
    || (value.completion === null ? !history || value.delivery_replay : !isWorldPlayGraphCompletion(value.completion, value.receipt))) return false;
  return true;
}

/** Join persisted provenance, including duplicate reserved references, before showing any source controls. */
export function isPlayContextProvenanceBound(receipt: WorldPlayGraphContextReceiptV1, provenance: unknown, worldId: string): boolean {
  if (!record(provenance) || provenance.world_id !== worldId || provenance.surface_id !== 'play' || provenance.surface_resolution !== 'resolved'
    || !record(provenance.selected_object) || provenance.selected_object.resolution !== 'absent' || !Array.isArray(provenance.supporting_work)) return false;
  const b = receipt.play_basis, a = receipt.graph_authority;
  if (b.world_id !== worldId) return false;
  const ref = (kind: string, object_id: string, revision: string, extra = {}) => ({ resolution: 'resolved', kind, object_id, revision,
    content_sha256: null, object_revision: null, work_revision_id: null, revision_n: null, ...extra });
  if (rulesCanonical(provenance.primary_work) !== rulesCanonical(ref('run', b.run_id, String(b.run_revision)))) return false;
  const expected = [ref('dmb_play_runbook_v1', b.runbook_object_id, String(b.runbook_object_revision), {
    content_sha256: b.runbook_content_sha256, object_revision: b.runbook_object_revision,
    work_revision_id: b.runbook_work_revision_id, revision_n: b.runbook_revision_n }),
    ref('dmb_play_current_beat_v1', b.beat_id, 'v2'),
    ...(b.scene_id === null ? [] : [ref('dmb_play_current_scene_v1', b.scene_id, 'v2')]),
    ref('dmb_play_graph_binding_v1', a.native_world_id, String(a.binding_version)), ref('world_graph_revision', a.native_world_id, a.graph_revision)];
  const reserved = new Set(['dmb_play_runbook_v1', 'dmb_play_current_beat_v1', 'dmb_play_current_scene_v1', 'dmb_play_graph_binding_v1', 'world_graph_revision', 'runbook']);
  const supplied = provenance.supporting_work.filter(r => record(r) && reserved.has(String(r.kind)));
  return supplied.length === expected.length && expected.every(e => supplied.filter(r => rulesCanonical(r) === rulesCanonical(e)).length === 1);
}
