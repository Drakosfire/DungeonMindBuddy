import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { createHash, webcrypto } from 'node:crypto';
import { afterEach, beforeEach, expect, it, vi } from 'vitest';
import { RulesHistoricalCitation } from './RulesHistoricalCitation';
import { rulesCanonical, verifyHistoricalRulesPassage } from './rulesEvidence';
import type { RulesHistoricalPassage, RulesPassageTarget } from '../api/rulesLookupTypes';
import * as api from '../api/liveApi';
const state = vi.hoisted(() => ({ epoch: 0 }));
vi.mock('../api/liveApi', () => ({ NATIVE_GRAPH_ACCESS_TOKEN_CHANGED_EVENT: 'rules-test-epoch',
  getNativeGraphAccessGeneration: () => state.epoch, getHistoricalRulesPassage: vi.fn() }));
const hash = (text: string) => createHash('sha256').update(text).digest('hex');
const text = 'Occupied 🦉 space.';
const support = { schema: 'dmb_rules_support_v1' as const, support_id: '11111111-1111-4111-8111-111111111111',
  corpus_sha256: 'a'.repeat(64), ruleset_id: 'dnd_2024_srd_5_2_1', unit_id: 'b'.repeat(64), full_text_sha256: 'c'.repeat(64),
  excerpt_start: 5, excerpt_end: 5 + Array.from(text).length, excerpt_text: text, excerpt_sha256: hash(text),
  source_title: 'Public SRD', section: 'Occupancy', source_uri: 'https://example.test/rules.pdf', source_sha256: 'd'.repeat(64),
  page_fingerprint: 'e'.repeat(64), pdf_page_index: 13, printed_page: 14 };
const target: RulesPassageTarget = { worldId: 'world-one', conversationId: '22222222-2222-4222-8222-222222222222',
  turnId: '33333333-3333-4333-8333-333333333333', attempt: 2, supportId: support.support_id, supportSha256: hash(rulesCanonical(support)) };
const passage: RulesHistoricalPassage = { schema: 'dmb_rules_historical_passage_v1', world_id: target.worldId,
  conversation_id: target.conversationId, turn_id: target.turnId, accepted_attempt: 2, support, support_sha256: target.supportSha256 };
beforeEach(() => { state.epoch = 0; vi.stubGlobal('crypto', webcrypto); vi.mocked(api.getHistoricalRulesPassage).mockResolvedValue(passage); });
afterEach(() => { vi.clearAllMocks(); vi.unstubAllGlobals(); });
const label = 'Public SRD · p. 14';
it('reads nothing while closed, shows the exact Unicode excerpt and releases it on close', async () => {
  render(<RulesHistoricalCitation target={target} label={label} />);
  expect(api.getHistoricalRulesPassage).not.toHaveBeenCalled();
  fireEvent.click(screen.getByRole('button', { name: /Inspect Rules source/ }));
  expect(await screen.findByRole('region', { name: 'Cited rules passage' })).toHaveTextContent(text);
  expect(screen.getByText('Exact cited excerpt saved with this answer.')).toBeInTheDocument();
  expect(api.getHistoricalRulesPassage).toHaveBeenCalledTimes(1);
  fireEvent.click(screen.getByRole('button', { name: 'Close cited passage' }));
  expect(screen.queryByRole('region', { name: 'Cited rules passage' })).not.toBeInTheDocument();
});
it('does not refetch equivalent target objects on parent rerender', async () => {
  const view = render(<RulesHistoricalCitation target={target} label={label} />);
  fireEvent.click(screen.getByRole('button', { name: /Inspect Rules source/ }));
  await screen.findByRole('region', { name: 'Cited rules passage' });
  view.rerender(<RulesHistoricalCitation target={{ ...target }} label={label} />);
  expect(api.getHistoricalRulesPassage).toHaveBeenCalledTimes(1);
});
it.each(['close', 'target', 'access'] as const)('retires an in-flight source read on %s and refuses its late bytes', async kind => {
  let resolve!: (value: RulesHistoricalPassage) => void;
  let signal: AbortSignal | undefined;
  vi.mocked(api.getHistoricalRulesPassage).mockImplementation((_, supplied) => { signal = supplied; return new Promise(done => { resolve = done; }); });
  const view = render(<RulesHistoricalCitation target={target} label={label} />);
  fireEvent.click(screen.getByRole('button', { name: /Inspect Rules source/ }));
  await waitFor(() => expect(api.getHistoricalRulesPassage).toHaveBeenCalledTimes(1));
  if (kind === 'close') fireEvent.click(screen.getByRole('button', { name: /Hide Rules source/ }));
  if (kind === 'target') view.rerender(<RulesHistoricalCitation target={{ ...target, worldId: 'other-world' }} label={label} />);
  if (kind === 'access') act(() => { state.epoch++; window.dispatchEvent(new Event('rules-test-epoch')); });
  expect(signal?.aborted).toBe(true);
  await act(async () => { resolve(passage); });
  expect(screen.queryByRole('region', { name: 'Cited rules passage' })).not.toBeInTheDocument();
  expect(api.getHistoricalRulesPassage).toHaveBeenCalledTimes(1);
});
it('rejects changed access without an event after a successful transport', async () => {
  vi.mocked(api.getHistoricalRulesPassage).mockImplementation(async () => { state.epoch++; return passage; });
  render(<RulesHistoricalCitation target={target} label={label} />);
  fireEvent.click(screen.getByRole('button', { name: /Inspect Rules source/ }));
  expect(await screen.findByRole('alert')).toHaveTextContent('Access changed');
  expect(screen.queryByRole('region', { name: 'Cited rules passage' })).not.toBeInTheDocument();
});
it.each(['world', 'turn', 'attempt', 'support', 'digest', 'text', 'range', 'extra', 'uri', 'size'])('rejects a changed historical capsule %s', async kind => {
  const value = structuredClone(passage);
  if (kind === 'world') value.world_id = 'other';
  if (kind === 'turn') value.turn_id = target.conversationId;
  if (kind === 'attempt') value.accepted_attempt++;
  if (kind === 'support') value.support.support_id = target.conversationId;
  if (kind === 'digest') value.support_sha256 = 'f'.repeat(64);
  if (kind === 'text') value.support.excerpt_text += 'changed';
  if (kind === 'range') value.support.excerpt_end++;
  if (kind === 'extra') Object.assign(value.support, { authority: 'fake' });
  if (kind === 'uri') value.support.source_uri = 'javascript:alert(1)';
  if (kind === 'size') value.support.excerpt_text = '\x01'.repeat(8192);
  await expect(verifyHistoricalRulesPassage(value, target)).rejects.toThrow('could not be verified');
});
it('shows transport failure and permits an explicit bounded retry', async () => {
  vi.mocked(api.getHistoricalRulesPassage).mockRejectedValueOnce(new Error('Source unavailable'));
  render(<RulesHistoricalCitation target={target} label={label} />);
  fireEvent.click(screen.getByRole('button', { name: /Inspect Rules source/ }));
  expect(await screen.findByRole('alert')).toHaveTextContent('Source unavailable');
  fireEvent.click(screen.getByRole('button', { name: 'Retry cited excerpt' }));
  await screen.findByRole('region', { name: 'Cited rules passage' });
  expect(api.getHistoricalRulesPassage).toHaveBeenCalledTimes(2);
});
