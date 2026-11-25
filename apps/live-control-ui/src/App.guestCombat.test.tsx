// @vitest-environment jsdom
import { render, screen, waitFor } from '@testing-library/react';
import { afterEach, expect, it, vi } from 'vitest';
import { App } from './App';

function response(status: number, payload: unknown): Response {
  const make = (): Response => ({ ok: status >= 200 && status < 300, status,
    json: async () => payload, text: async () => JSON.stringify(payload), clone: make } as Response);
  return make();
}
afterEach(() => { vi.unstubAllGlobals(); vi.unstubAllEnvs(); vi.restoreAllMocks(); });

it('opens the existing Combat Tracker in the signed-out guest World', async () => {
  vi.stubEnv('PROD', true);
  vi.stubEnv('VITE_HOSTED_GUEST_BUILD', '1');
  vi.stubEnv('VITE_HOSTED_GUEST_PLAN', '1');
  vi.stubEnv('VITE_HOSTED_GUEST_PLAY', '1');
  const worldId = `guest-${'a'.repeat(32)}`;
  const fetcher = vi.fn(async (input: RequestInfo | URL) => {
    const path = String(input);
    if (path === '/api/auth/session') return response(401, { status: 'signed_out' });
    if (path === '/api/live/index-graph/session') return response(200, { csrf_token: 'guest-csrf' });
    if (path === '/api/live/index-graph/world') return response(200, { world_id: worldId, name: 'Sizzek World' });
    if (path.startsWith('/api/live/combat/encounters?')) return response(200, []);
    return response(404, {});
  });
  vi.stubGlobal('fetch', fetcher);
  window.history.replaceState({}, '', '/combat');
  render(<App />);
  expect(await screen.findByRole('main', { name: 'Combat encounters' })).toBeInTheDocument();
  expect(await screen.findByText('No encounters yet. Set up your first encounter.')).toBeInTheDocument();
  expect(screen.queryByRole('heading', { name: 'Sign in to DungeonMind' })).not.toBeInTheDocument();
  await waitFor(() => expect(fetcher.mock.calls.some(([path]) => String(path).startsWith('/api/live/combat/encounters?'))).toBe(true));
});
