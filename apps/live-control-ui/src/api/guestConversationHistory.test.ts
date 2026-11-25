import { afterEach, expect, it, vi } from 'vitest';
import * as guest from '../guestWorld/guestBuildSession';
import { getWorldAgentConversationHistory, setNativeGraphAccessToken } from './liveApi';

const retry = vi.hoisted(() => vi.fn());
vi.mock('./conversationRetryApi', () => ({ readRetryContext: retry }));
afterEach(() => { setNativeGraphAccessToken(null); vi.restoreAllMocks(); retry.mockReset(); });

it('loads guest Build history without calling owner-only retry context', async () => {
  vi.spyOn(guest, 'guestBuildRequestEpoch').mockReturnValue(1);
  vi.spyOn(guest, 'guestBuildEpochCurrent').mockReturnValue(true);
  vi.spyOn(guest, 'guestBuildCsrf').mockReturnValue(null);
  const turn = { turn_id: 'turn-one', provenance: { surface_id: 'build', primary_work: { kind: 'build' } } };
  const fetcher = vi.spyOn(globalThis, 'fetch').mockResolvedValue(Response.json({ conversation_id: 'conversation-one', turns: [turn] }));
  const result = await getWorldAgentConversationHistory('guest-world', { includeTurnCorrelation: true });
  expect(result.turns).toEqual([turn]);
  expect(fetcher).toHaveBeenCalledTimes(1);
  expect(retry).not.toHaveBeenCalled();
});

it('still resolves retry context for signed-in Build history', async () => {
  vi.spyOn(guest, 'guestBuildRequestEpoch').mockReturnValue(null);
  setNativeGraphAccessToken('test-only-owner-token');
  const turn = { turn_id: 'turn-one', provenance: { surface_id: 'build', primary_work: { kind: 'build' } } };
  vi.spyOn(globalThis, 'fetch').mockResolvedValue(Response.json({ conversation_id: 'conversation-one', turns: [turn] }));
  retry.mockResolvedValue(new Map([['turn-one', { eligible: true }]]));
  const result = await getWorldAgentConversationHistory('owner-world', { includeTurnCorrelation: true });
  expect(retry).toHaveBeenCalledOnce();
  expect(result.turns[0]).toMatchObject({ retry_context: { eligible: true } });
});
