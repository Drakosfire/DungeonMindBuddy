import { webcrypto } from 'node:crypto';
import { beforeEach, expect, it, vi } from 'vitest';
import { rulesAnswerFixture, fixtureHash } from '../test/rulesAnswerFixture';
import { isRulesAnswerContext, rulesAnswerDigestsBound } from './rulesAnswerProtocol';
import { rulesCanonical } from './rulesEvidence';
beforeEach(() => vi.stubGlobal('crypto', webcrypto));
it('validates a sealed Unicode answer map without inventing base authority', async () => {
  const { context, answer } = rulesAnswerFixture();
  expect(isRulesAnswerContext(context, answer, 'world-one', () => false)).toBe(true);
  expect(await rulesAnswerDigestsBound(context, answer)).toBe(true);
  expect(isRulesAnswerContext(context, answer, 'other-world', () => true)).toBe(false);
  expect(isRulesAnswerContext(context, answer, 'world-one', () => true, { conversationId: 'other' })).toBe(false);
  expect(isRulesAnswerContext(context, answer, 'world-one', () => true, { turnId: 'other' })).toBe(false);
});
it.each(['text','seal','map','source','unused','duplicate','category','base','graph','domain','range','utf16','unknown'])('refuses mismatched accepted %s data', async kind => {
  const { context, answer } = rulesAnswerFixture(), value = structuredClone(context);
  let text = answer;
  if (kind === 'text') text += ' changed';
  if (kind === 'seal') value.accepted_binding_sha256 = '0'.repeat(64);
  if (kind === 'map') value.accepted_binding.segment_map[0].ordinal = 1;
  if (kind === 'source') value.accepted_binding.segment_map[0].support_refs[0].support_sha256 = '0'.repeat(64);
  if (kind === 'unused') value.accepted_binding.support_table.push({ ...value.accepted_binding.support_table[0], support_id: value.accepted_binding.execution_id });
  if (kind === 'duplicate') value.accepted_binding.support_table.push(value.accepted_binding.support_table[0]);
  if (kind === 'category') value.accepted_binding.segment_map[0].category = 'connective';
  if (kind === 'base') value.accepted_binding.base_disposition = 'approved';
  if (kind === 'graph') value.accepted_binding.graph_used = true;
  if (kind === 'domain') value.accepted_binding.segment_map[0].domain = 'base';
  if (kind === 'range') value.accepted_binding.segment_map[0].text_start++;
  if (kind === 'utf16') value.accepted_binding.segment_map[0].text_end = answer.length;
  if (kind === 'unknown') Object.assign(value.accepted_binding, { old_protocol: true });
  const shape = isRulesAnswerContext(value, text, 'world-one', () => true);
  expect(shape && await rulesAnswerDigestsBound(value, text)).toBe(false);
});
it('does not accept a self-consistent seal after visible text was altered', async () => {
  const { context, answer } = rulesAnswerFixture();
  context.accepted_binding.segment_map[0].text_end++;
  context.accepted_binding_sha256 = fixtureHash(rulesCanonical(context.accepted_binding));
  expect(isRulesAnswerContext(context, answer + 'x', 'world-one', () => true)).toBe(true);
  expect(await rulesAnswerDigestsBound(context, answer + 'x')).toBe(false);
});

it('accepts an explicit evidence gap with no claim source controls', async () => {
  const { context } = rulesAnswerFixture(), answer = 'No supporting travel Rules evidence was retrieved.';
  const b = context.accepted_binding;
  b.support_table = [];
  b.segment_map = [{ ordinal: 0, domain: 'rules_context', text_start: 0, text_end: Array.from(answer).length,
    base_segment_index: null, rules_claim_id: null, rules_context_id: 'rules:0', category: 'gap', support_refs: [] }];
  b.assistant_text_sha256 = fixtureHash(answer);
  context.accepted_binding_sha256 = fixtureHash(rulesCanonical(b));
  expect(isRulesAnswerContext(context, answer, 'world-one', () => false)).toBe(true);
  expect(await rulesAnswerDigestsBound(context, answer)).toBe(true);
});
