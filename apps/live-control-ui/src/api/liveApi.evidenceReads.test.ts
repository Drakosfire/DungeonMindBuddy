import { afterEach, describe, expect, it, vi } from 'vitest'

const cases = ['trace', 'prompt', 'source-passage'] as const
async function setup(base = '') {
  vi.stubEnv('VITE_LIVE_API_BASE_URL', base)
  vi.resetModules()
  return import('./liveApi')
}
type Api = Awaited<ReturnType<typeof setup>>
function read(api: Api, kind: typeof cases[number]) {
  if (kind === 'source-passage') return api.getAgentSourcePassage('world/a', 'turn-a', 0)
  return kind === 'trace' ? api.getWorldAgentTurnContextTrace('world/a', 'turn-a')
    : api.getWorldAgentTurnPrompt('world/a', 'turn-a', 'trace-a', 'provider-a')
}
afterEach(() => { vi.restoreAllMocks(); vi.unstubAllEnvs() })
describe.each(cases)('Agent %s evidence read authorization', kind => {
  it('forwards explicit local bearer with redirect and credential guards', async () => {
    const api = await setup()
    api.setNativeGraphAccessToken('synthetic-evidence-token')
    const fetch = vi.spyOn(globalThis, 'fetch').mockResolvedValue(Response.json({ fixture: true }))
    await read(api, kind)
    const [url, init] = fetch.mock.calls[0]
    expect(String(url)).toContain('/worlds/world%2Fa/conversation/turns/turn-a/' + (kind === 'source-passage' ? 'source-passages/0' : 'context-trace'))
    expect(new Headers(init?.headers).get('Authorization')).toBe('Bearer synthetic-evidence-token')
    expect(init?.redirect).toBe('error')
    expect(init?.credentials).toBe('same-origin')
    expect(init?.body).toBeUndefined()
    expect(fetch).toHaveBeenCalledTimes(1)
  })
  it('refuses remote destinations before fetching', async () => {
    const api = await setup('https://example.invalid')
    api.setNativeGraphAccessToken('synthetic-evidence-token')
    const fetch = vi.spyOn(globalThis, 'fetch').mockRejectedValue(new Error('unexpected fetch'))
    await expect(read(api, kind)).rejects.toMatchObject({ status: 0, message: expect.stringContaining('loopback') })
    expect(fetch).not.toHaveBeenCalled()
  })
  it('bootstraps and recovers an expired cookie using only the evidence GET', async () => {
    const api = await setup()
    let reads = 0, boots = 0
    const fetch = vi.spyOn(globalThis, 'fetch').mockImplementation(async (url, init) => {
      if (String(url) === '/api/live/agent/local-session') {
        if (init?.method === 'POST') { boots++; return Response.json({ status: 'active', csrf_token: `csrf-${boots}` }) }
        return new Response(null, { status: 401 })
      }
      reads++
      expect(init?.method ?? 'GET').toBe('GET')
      expect(init?.body).toBeUndefined()
      expect(init?.redirect).toBe('error')
      expect(new Headers(init?.headers).has('Authorization')).toBe(false)
      return reads === 1 ? Response.json({ detail: { code: 'graph_auth_required' } }, { status: 401 }) : Response.json({ fixture: true })
    })
    await expect(read(api, kind)).resolves.toEqual({ fixture: true })
    expect(reads).toBe(2); expect(boots).toBe(2)
    expect(fetch.mock.calls.filter(([, init]) => init?.method === 'POST').every(([url]) => String(url) === '/api/live/agent/local-session')).toBe(true)
  })
  it('never follows or retries a redirect transport failure', async () => {
    const api = await setup(); api.setNativeGraphAccessToken('synthetic-evidence-token')
    const fetch = vi.spyOn(globalThis, 'fetch').mockRejectedValue(new TypeError('redirect rejected'))
    await expect(read(api, kind)).rejects.toThrow()
    expect(fetch).toHaveBeenCalledTimes(1)
    expect(fetch.mock.calls[0][1]?.redirect).toBe('error')
  })
})
it('does not attach evidence credentials to a near-miss endpoint', async () => {
  const api = await setup(); api.setNativeGraphAccessToken('synthetic-evidence-token')
  const fetch = vi.spyOn(globalThis, 'fetch').mockResolvedValue(Response.json({}))
  await api.authenticatedApiFetch('/api/live/agent/worlds/world-a/conversation/turns/turn-a/context-trace/export-anything')
  expect(new Headers(fetch.mock.calls[0][1]?.headers).has('Authorization')).toBe(false)
})

const buildPaths = [
  '/api/live/agent/worlds/world%2Fa/build-proposals',
  '/api/live/agent/worlds/world%2Fa/build-proposals?conversation_id=conversation',
  '/api/live/agent/worlds/world%2Fa/build-proposals/action',
  '/api/live/agent/worlds/world%2Fa/build-proposals/action/prompt',
  '/api/live/agent/worlds/world%2Fa/build-proposals/action/inserted?expected_revision=5',
]
it.each(buildPaths)('guards the exact Build endpoint %s', async path => {
  const api = await setup(); api.setNativeGraphAccessToken('synthetic-build-token')
  const fetch = vi.spyOn(globalThis, 'fetch').mockResolvedValue(Response.json({}))
  await api.authenticatedApiFetch(path)
  expect(new Headers(fetch.mock.calls[0][1]?.headers).get('Authorization')).toBe('Bearer synthetic-build-token')
  expect(fetch.mock.calls[0][1]?.redirect).toBe('error')
})
it.each(buildPaths)('refuses remote credential dispatch for %s', async path => {
  const api = await setup('https://example.invalid'); api.setNativeGraphAccessToken('synthetic-build-token')
  const fetch = vi.spyOn(globalThis, 'fetch').mockResolvedValue(Response.json({}))
  await expect(api.authenticatedApiFetch(path)).rejects.toMatchObject({ status: 0 })
  expect(fetch).not.toHaveBeenCalled()
})
it('recovers a trusted pre-dispatch session rejection with identical Compose bytes', async () => {
  const api = await setup(); let calls = 0
  const body = JSON.stringify({ idempotency_key: 'same-action', conversation_id: 'conversation', expected_pointer_revision: 1 })
  vi.spyOn(globalThis, 'fetch').mockImplementation(async (url, init) => {
    if (String(url) === '/api/live/agent/local-session') return Response.json({ status: 'active', csrf_token: 'csrf' })
    calls++; expect(init?.body).toBe(body)
    expect(new Headers(init?.headers).get('X-DMB-Graph-CSRF')).toBe('csrf')
    return calls === 1 ? Response.json({ detail: { code: 'graph_auth_csrf_rejected' } }, { status: 403 }) : Response.json({})
  })
  await api.authenticatedApiFetch(buildPaths[0], { method: 'POST', body })
  expect(calls).toBe(2)
})
it('does not repeat Compose after an uncertain network failure', async () => {
  const api = await setup(); api.setNativeGraphAccessToken('synthetic-build-token')
  const fetch = vi.spyOn(globalThis, 'fetch').mockRejectedValue(new TypeError('Unknown outcome'))
  await expect(api.authenticatedApiFetch(buildPaths[0], { method: 'POST', body: '{}' })).rejects.toThrow('Unknown outcome')
  expect(fetch).toHaveBeenCalledTimes(1)
})
it('does not authorize a near-miss Build endpoint', async () => {
  const api = await setup(); api.setNativeGraphAccessToken('synthetic-build-token')
  const fetch = vi.spyOn(globalThis, 'fetch').mockResolvedValue(Response.json({}))
  await api.authenticatedApiFetch('/api/live/agent/worlds/world/build-proposals/action/export')
  expect(new Headers(fetch.mock.calls[0][1]?.headers).has('Authorization')).toBe(false)
})

it.each(['export', '0/export', '-1', '1.5'])('does not authorize a near-miss passage selector %s', async selector => {
  const api = await setup(); api.setNativeGraphAccessToken('synthetic-evidence-token')
  const fetch = vi.spyOn(globalThis, 'fetch').mockResolvedValue(Response.json({}))
  await api.authenticatedApiFetch('/api/live/agent/worlds/world-a/conversation/turns/turn-a/source-passages/' + selector)
  expect(new Headers(fetch.mock.calls[0][1]?.headers).has('Authorization')).toBe(false)
})
it.each([-1, 16384, 0.5, NaN])('rejects an invalid source index before fetching: %s', async index => {
  const api = await setup()
  const fetch = vi.spyOn(globalThis, 'fetch').mockRejectedValue(new Error('unexpected fetch'))
  await expect(api.getAgentSourcePassage('world', 'turn', index)).rejects.toThrow('Invalid source passage index')
  expect(fetch).not.toHaveBeenCalled()
})
