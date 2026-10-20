import { createHash } from 'node:crypto';
import type { RulesAnswerContext, RulesAnswerSegment, RulesHistoricalPassage } from '../api/rulesLookupTypes';
import { rulesCanonical } from '../rulesLookup/rulesCanonical';
export const fixtureHash = (text: string) => createHash('sha256').update(text).digest('hex');
export function rulesAnswerFixture(base: RulesAnswerContext['base_context'] = null) {
  const world = 'world-one', conversation = '11111111-1111-4111-8111-111111111111', turn = '22222222-2222-4222-8222-222222222222';
  const ruleText = 'Occupied 🦉 space is constrained.';
  const excerpt = 'You cannot willingly end movement in occupied 🦉 space.';
  const support = { schema: 'dmb_rules_support_v1' as const, support_id: '33333333-3333-4333-8333-333333333333', corpus_sha256: 'a'.repeat(64),
    ruleset_id: 'dnd_2024_srd_5_2_1', unit_id: 'b'.repeat(64), full_text_sha256: fixtureHash('full unit ' + excerpt),
    excerpt_start: 5, excerpt_end: 5 + Array.from(excerpt).length, excerpt_text: excerpt, excerpt_sha256: fixtureHash(excerpt),
    source_title: 'Public SRD', section: 'Occupancy', source_uri: 'https://example.test/rules.pdf', source_sha256: 'c'.repeat(64),
    page_fingerprint: 'd'.repeat(64), pdf_page_index: 13, printed_page: 14 };
  const ref = { support_id: support.support_id, support_sha256: fixtureHash(rulesCanonical(support)) };
  const baseTexts = base?.completion?.answer_segments.map(s => s.text) ?? [];
  const texts = [...baseTexts, ruleText], answer = texts.join('\n');
  let offset = 0;
  const map: RulesAnswerSegment[] = texts.map((text, ordinal) => {
    const segment: RulesAnswerSegment = { ordinal, domain: ordinal < baseTexts.length ? 'base' : 'rules_claim', text_start: offset,
      text_end: offset + Array.from(text).length, base_segment_index: ordinal < baseTexts.length ? ordinal : null,
      rules_claim_id: ordinal < baseTexts.length ? null : 'rules:0', rules_context_id: null, category: null,
      support_refs: ordinal < baseTexts.length ? [] : [ref] };
    offset = segment.text_end + 1; return segment;
  });
  const binding: RulesAnswerContext['accepted_binding'] = { schema: 'dmb_rules_accepted_binding_v1', world_id: world, conversation_id: conversation, turn_id: turn,
    corpus_sha256: support.corpus_sha256, ruleset_id: support.ruleset_id, accepted_turn_revision: 4, product_attempt: 1,
    execution_id: '44444444-4444-4444-8444-444444444444', producing_provider_attempt_id: '55555555-5555-4555-8555-555555555555',
    request_envelope_sha256: 'e'.repeat(64), composition_sha256: 'f'.repeat(64), assistant_text_sha256: fixtureHash(answer),
    base_text_sha256: base === null ? null : fixtureHash(baseTexts.join('\n')), base_disposition: base === null ? 'absent' : 'approved',
    segment_map: map, support_table: [{ ...ref, source_label: 'Public SRD · Page 14' }], graph_used: base?.completion?.answer_basis.includes('world_graph') ?? false };
  const context: RulesAnswerContext = { schema: 'dmb_agent_rules_answer_context_v1', accepted_binding: binding,
    accepted_binding_sha256: fixtureHash(rulesCanonical(binding)), base_context: base };
  const capsule: RulesHistoricalPassage = { schema: 'dmb_rules_historical_passage_v1', world_id: world, conversation_id: conversation, turn_id: turn,
    accepted_attempt: 1, support, support_sha256: ref.support_sha256 };
  return { context, answer, ruleText, capsule };
}
