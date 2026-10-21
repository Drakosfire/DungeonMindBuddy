import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { webcrypto } from 'node:crypto';
import { afterEach, beforeEach, expect, it, vi } from 'vitest';
import { RulesAnswerEvidence } from './RulesAnswerEvidence';
import { rulesAnswerFixture } from '../test/rulesAnswerFixture';
import type { RulesHistoricalPassage } from '../api/rulesLookupTypes';
import * as api from '../api/liveApi';
vi.mock('../api/liveApi', () => ({ NATIVE_GRAPH_ACCESS_TOKEN_CHANGED_EVENT: 'rules-disclosure-access',
  getNativeGraphAccessGeneration: () => 0, getHistoricalRulesPassage: vi.fn() }));
beforeEach(() => { vi.stubGlobal('crypto', webcrypto); vi.mocked(api.getHistoricalRulesPassage).mockResolvedValue(rulesAnswerFixture().capsule); });
afterEach(() => { vi.clearAllMocks(); vi.unstubAllGlobals(); });
async function expand() {
  fireEvent.click(screen.getByText('Rules references', { selector: 'summary' }));
  return screen.findByRole('button', { name: /Inspect Rules source/ });
}
it('aborts the pending reader on disclosure collapse and refuses its late body', async () => {
  const fixture = rulesAnswerFixture();
  let resolve!: (value: RulesHistoricalPassage) => void, signal: AbortSignal | undefined;
  vi.mocked(api.getHistoricalRulesPassage).mockImplementationOnce((_, supplied) => {
    signal = supplied; return new Promise(done => { resolve = done; });
  });
  render(<RulesAnswerEvidence context={fixture.context} answer={fixture.answer} />);
  expect(api.getHistoricalRulesPassage).not.toHaveBeenCalled();
  fireEvent.click(await expand());
  await waitFor(() => expect(api.getHistoricalRulesPassage).toHaveBeenCalledTimes(1));
  fireEvent.click(screen.getByText('Rules references', { selector: 'summary' }));
  await waitFor(() => expect(signal?.aborted).toBe(true));
  await act(async () => resolve(fixture.capsule));
  expect(screen.queryByRole('region', { name: 'Cited rules passage' })).not.toBeInTheDocument();
  const inspect = await expand();
  expect(api.getHistoricalRulesPassage).toHaveBeenCalledTimes(1);
  fireEvent.click(inspect);
  await screen.findByRole('region', { name: 'Cited rules passage' });
  expect(api.getHistoricalRulesPassage).toHaveBeenCalledTimes(2);
});
it('releases a loaded passage on disclosure collapse and requires another explicit inspection', async () => {
  const fixture = rulesAnswerFixture();
  render(<RulesAnswerEvidence context={fixture.context} answer={fixture.answer} />);
  fireEvent.click(await expand());
  await screen.findByRole('region', { name: 'Cited rules passage' });
  fireEvent.click(screen.getByText('Rules references', { selector: 'summary' }));
  await waitFor(() => expect(screen.queryByRole('region', { name: 'Cited rules passage' })).not.toBeInTheDocument());
  const inspect = await expand();
  expect(api.getHistoricalRulesPassage).toHaveBeenCalledTimes(1);
  expect(screen.queryByRole('region', { name: 'Cited rules passage' })).not.toBeInTheDocument();
  fireEvent.click(inspect);
  await screen.findByRole('region', { name: 'Cited rules passage' });
  expect(api.getHistoricalRulesPassage).toHaveBeenCalledTimes(2);
});
it('keeps an open equivalent target stable across rerenders and retires it when its conversation is inactive', async () => {
  const fixture = rulesAnswerFixture();
  const view = render(<RulesAnswerEvidence context={fixture.context} answer={fixture.answer} />);
  fireEvent.click(await expand());
  await screen.findByRole('region', { name: 'Cited rules passage' });
  view.rerender(<RulesAnswerEvidence context={structuredClone(fixture.context)} answer={fixture.answer} />);
  expect(api.getHistoricalRulesPassage).toHaveBeenCalledTimes(1);
  view.rerender(<RulesAnswerEvidence context={fixture.context} answer={fixture.answer} active={false} />);
  expect(screen.queryByRole('region', { name: 'Cited rules passage' })).not.toBeInTheDocument();
  view.rerender(<RulesAnswerEvidence context={fixture.context} answer={fixture.answer} active />);
  expect(screen.queryByRole('button', { name: /Hide Rules source/ })).not.toBeInTheDocument();
  expect(api.getHistoricalRulesPassage).toHaveBeenCalledTimes(1);
});
