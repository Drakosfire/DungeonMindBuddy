import type { RulesAnswerContext } from '../api/rulesLookupTypes';
import { rulesCanonical, rulesDigest } from './rulesCanonical';
const rec = (v: unknown): v is Record<string, unknown> => v !== null && typeof v === 'object' && !Array.isArray(v);
const exact = (v: unknown, names: string[]): v is Record<string, unknown> => rec(v) && Object.keys(v).length === names.length && names.every(n => Object.hasOwn(v, n));
const sha = (v: unknown): v is string => typeof v === 'string' && /^[a-f0-9]{64}$/.test(v);
const uuid = (v: unknown): v is string => typeof v === 'string' && /^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$/.test(v);
const positive = (v: unknown): v is number => typeof v === 'number' && Number.isSafeInteger(v) && v >= 1;
const index = (v: unknown): v is number => typeof v === 'number' && Number.isSafeInteger(v) && v >= 0;
const identity = (v: unknown): v is string => typeof v === 'string' && Array.from(v).length >= 1 && Array.from(v).length <= 128;

/** Shape/map checks do not replace the owning Plan/Build receipt validators or hashes. */
export function isRulesAnswerContext(value: unknown, text: unknown, worldId: string,
  validateBase: (base: unknown) => boolean, owner?: { conversationId?: string; turnId?: string }, validateUnclaimed: (context: unknown) => boolean = () => false): value is RulesAnswerContext {
  if (!exact(value, ['schema','accepted_binding','accepted_binding_sha256','base_context','unclaimed_context'])
    || value.schema !== 'dmb_agent_rules_answer_context_v1' || !sha(value.accepted_binding_sha256)
    || typeof text !== 'string' || !text || Array.from(text).length > 32000) return false;
  const b = value.accepted_binding;
  if (!exact(b, ['schema','world_id','conversation_id','turn_id','corpus_sha256','ruleset_id','accepted_turn_revision','product_attempt',
    'execution_id','producing_provider_attempt_id','request_envelope_sha256','composition_sha256','assistant_text_sha256',
    'base_text_sha256','base_disposition','segment_map','support_table','graph_used'])
    || b.schema !== 'dmb_rules_accepted_binding_v1' || b.world_id !== worldId
    || !['conversation_id','turn_id','execution_id','producing_provider_attempt_id'].every(k => uuid(b[k]))
    || (owner?.conversationId !== undefined && owner.conversationId !== b.conversation_id)
    || (owner?.turnId !== undefined && owner.turnId !== b.turn_id)
    || !['corpus_sha256','request_envelope_sha256','composition_sha256','assistant_text_sha256'].every(k => sha(b[k]))
    || typeof b.ruleset_id !== 'string' || !/^[a-z0-9_]{1,80}$/.test(b.ruleset_id)
    || !positive(b.accepted_turn_revision) || !positive(b.product_attempt)
    || !['absent','approved','unclaimed'].includes(String(b.base_disposition)) || typeof b.graph_used !== 'boolean'
    || !Array.isArray(b.segment_map) || b.segment_map.length < 1 || b.segment_map.length > 128
    || !Array.isArray(b.support_table) || b.support_table.length > 16
    || new TextEncoder().encode(rulesCanonical(b)).length > 32768) return false;
  const approved = b.base_disposition === 'approved';
  if (approved !== (value.base_context !== null) || approved !== sha(b.base_text_sha256)
    || (!approved && (b.base_text_sha256 !== null || b.graph_used))) return false;
  if (b.base_disposition === 'unclaimed') {
    const c = value.unclaimed_context;
    if (!exact(c, ['schema', 'receipt', 'execution', 'delivery_replay']) || c.schema !== 'dmb_agent_rules_unclaimed_context_v1'
      || typeof c.delivery_replay !== 'boolean' || !rec(c.receipt)
      || !exact(c.execution, ['schema', 'claimability', 'authorization_state', 'automatic_redispatch'])
      || c.execution.schema !== 'dmb_agent_plan_world_graph_execution_projection_v1'
      || c.execution.claimability !== 'completed' || c.execution.authorization_state !== 'response_received'
      || c.execution.automatic_redispatch !== false || !validateUnclaimed(c)) return false;
  } else if (value.unclaimed_context !== null) return false;
  let baseSegments: string[] = [];
  if (approved) {
    const base = value.base_context;
    if (!validateBase(base) || !rec(base) || !rec(base.completion) || !Array.isArray(base.completion.answer_segments)
      || typeof base.completion.answer_basis !== 'string'
      || b.graph_used !== base.completion.answer_segments.some(s => rec(s) && s.kind === 'graph_claim')) return false;
    if (!base.completion.answer_segments.every(s => rec(s) && typeof s.text === 'string')) return false;
    baseSegments = base.completion.answer_segments.map(s => (s as {text: string}).text);
  }
  const table = new Map<string, string>();
  for (const s of b.support_table) {
    if (!exact(s, ['support_id','support_sha256','source_label']) || !uuid(s.support_id) || !sha(s.support_sha256)
      || typeof s.source_label !== 'string' || !s.source_label || Array.from(s.source_label).length > 160 || table.has(s.support_id)) return false;
    table.set(s.support_id, s.support_sha256);
  }
  const chars = Array.from(text), used = new Set<string>(), ids = new Set<string>();
  let end = -1, baseIndex = 0, claimCount = 0, ruleCount = 0;
  for (const [ordinal, s] of b.segment_map.entries()) {
    if (!exact(s, ['ordinal','domain','text_start','text_end','base_segment_index','rules_claim_id','rules_context_id','category','support_refs'])
      || s.ordinal !== ordinal || !index(s.text_start) || !positive(s.text_end) || s.text_start !== end + 1
      || s.text_end <= s.text_start || s.text_end > chars.length
      || (ordinal > 0 && chars[s.text_start - 1] !== '\n')
      || !Array.isArray(s.support_refs) || s.support_refs.length > 4) return false;
    end = s.text_end;
    const segment = chars.slice(s.text_start, s.text_end).join('');
    if (s.domain === 'base') {
      if (!approved || s.base_segment_index !== baseIndex || s.rules_claim_id !== null || s.rules_context_id !== null
        || s.category !== null || s.support_refs.length || segment !== baseSegments[baseIndex++]) return false;
    } else {
      ruleCount++;
      if (!segment.trim() || Array.from(segment).length > 4000) return false;
      if (s.base_segment_index !== null) return false;
      const id = s.domain === 'rules_claim' ? s.rules_claim_id : s.rules_context_id;
      if (!identity(id) || ids.has(id)) return false;
      ids.add(id);
      if (s.domain === 'rules_claim') {
        if (++claimCount > 16 || s.rules_context_id !== null || s.category !== null || !s.support_refs.length) return false;
      } else if (s.domain !== 'rules_context' || s.rules_claim_id !== null || s.support_refs.length
        || !['interpretation','gap','connective'].includes(String(s.category))) return false;
      const distinct = new Set<string>();
      for (const ref of s.support_refs) {
        if (!exact(ref, ['support_id','support_sha256']) || !uuid(ref.support_id) || !sha(ref.support_sha256) || table.get(ref.support_id) !== ref.support_sha256 || distinct.has(ref.support_id)) return false;
        distinct.add(ref.support_id); used.add(ref.support_id);
      }
    }
  }
  return end === chars.length && baseIndex === baseSegments.length && approved === (baseIndex > 0)
    && ruleCount <= 32 && used.size === table.size;
}

export async function rulesAnswerDigestsBound(context: RulesAnswerContext, text: string): Promise<boolean> {
  const b = context.accepted_binding;
  const base = context.base_context?.completion?.answer_segments.map(s => s.text).join('\n') ?? null;
  try {
    const [seal, body, baseHash] = await Promise.all([rulesDigest(rulesCanonical(b)), rulesDigest(text), base === null ? null : rulesDigest(base)]);
    return seal === context.accepted_binding_sha256 && body === b.assistant_text_sha256 && baseHash === b.base_text_sha256;
  } catch { return false; }
}
