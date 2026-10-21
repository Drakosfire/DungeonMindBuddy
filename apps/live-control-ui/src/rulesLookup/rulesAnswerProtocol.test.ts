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

it('keeps unclaimed execution identity separate from the base answer and requires owning receipt admission', async () => {
  const { nativePlayContextFixture, nativePlayRequestFixture } = await import('../test/nativePlayContextFixture');
  const { rulesUnclaimedFixture } = await import('../test/rulesAnswerFixture');
  const f = rulesUnclaimedFixture(nativePlayContextFixture(nativePlayRequestFixture()));
  expect(isRulesAnswerContext(f.context, f.answer, 'world-one', () => false)).toBe(false);
  expect(isRulesAnswerContext(f.context, f.answer, 'world-one', () => false, undefined, c => c === f.context.unclaimed_context)).toBe(true);
  expect(f.context.base_context).toBeNull();
  expect(f.context.accepted_binding.segment_map.every(s => s.domain !== 'base')).toBe(true);
  expect(await rulesAnswerDigestsBound(f.context, f.answer)).toBe(true);
});
it.each(['missing', 'claims', 'execution', 'outcome', 'redispatch', 'absent', 'approved'])('refuses malformed or misclassified execution-only context: %s', async kind => {
  const { nativePlayContextFixture, nativePlayRequestFixture } = await import('../test/nativePlayContextFixture');
  const { rulesUnclaimedFixture } = await import('../test/rulesAnswerFixture');
  const f = rulesUnclaimedFixture(nativePlayContextFixture(nativePlayRequestFixture())), c = f.context.unclaimed_context!;
  if (kind === 'missing') f.context.unclaimed_context = null;
  if (kind === 'claims') Object.assign(c, { completion: { answer_segments: [{ kind: 'plan_claim', text: 'Forged claim' }] } });
  if (kind === 'execution') c.execution.claimability = 'blocked_unknown_or_sent';
  if (kind === 'outcome') c.execution.authorization_state = 'outcome_unknown';
  if (kind === 'redispatch') Object.assign(c.execution, { automatic_redispatch: true });
  if (kind === 'absent') f.context.accepted_binding.base_disposition = 'absent';
  if (kind === 'approved') f.context.accepted_binding.base_disposition = 'approved';
  expect(isRulesAnswerContext(f.context, f.answer, 'world-one', () => true, undefined, () => true)).toBe(false);
});
