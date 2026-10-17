import { afterEach, describe, expect, it, vi } from 'vitest'

const cases = ['trace', 'prompt'] as const
async function setup(base = '') {
  vi.stubEnv('VITE_LIVE_API_BASE_URL', base)
  vi.resetModules()
  return import('./liveApi')
}
type Api = Awaited<ReturnType<typeof setup>>
function read(api: Api, kind: typeof cases[number]) {
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
    expect(String(url)).toContain('/worlds/world%2Fa/conversation/turns/turn-a/context-trace')
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
