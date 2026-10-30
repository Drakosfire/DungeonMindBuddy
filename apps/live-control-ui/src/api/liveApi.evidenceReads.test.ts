import { afterEach, describe, expect, it, vi } from 'vitest'

const cases = ['trace', 'historical-passage', 'prompt', 'source-passage', 'native-section', 'native-body', 'related-page', 'work-plan', 'action-index', 'action-prompt', 'action-diagnostic'] as const
async function setup(base = '') {
  vi.stubEnv('VITE_LIVE_API_BASE_URL', base)
  vi.resetModules()
  return import('./liveApi')
}
type Api = Awaited<ReturnType<typeof setup>>
function read(api: Api, kind: typeof cases[number]) {
  if (kind === 'historical-passage') return api.getWorldAgentHistoricalSourcePassage({schema:'dmb_trace_historical_source_ref_v1',world_id:'world/a',conversation_id:'conversation-a',turn_id:'turn-a',trace_id:'trace-a',attempt:1,source_read_event_id:'event-a',source_read_id:'read/a ?&=',content_sha256:'a'.repeat(64)})
  if (kind === 'action-diagnostic') return api.getPlanActionTerminalDiagnostic('world/a', 'action-a')
  if (kind === 'action-index') return api.getPlanActionPromptIndex('world/a', 'action-a')
  if (kind === 'action-prompt') return api.getPlanActionPromptBody('world/a', 'action-a', 'provider-a')
  if (kind === 'work-plan') return api.authenticatedApiFetch('/api/live/agent/worlds/world%2Fa/conversations/11111111-1111-4111-8111-111111111111/work-plans/22222222-2222-4222-8222-222222222222').then(r=>r.response.json())
  if (kind === 'related-page') return api.getAgentRelatedPage('world/a','turn-a','12345678-1234-1234-1234-123456789012')
  if (kind === 'native-body') return api.getAgentNativeBodyExcerpt('world/a','turn-a',0)
  if (kind === 'native-section') return api.getAgentNativeSourceSection('world/a','turn-a',0)
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
    expect(String(url)).toContain(kind === 'work-plan' ? '/worlds/world%2Fa/conversations/11111111-1111-4111-8111-111111111111/work-plans/22222222-2222-4222-8222-222222222222' : kind === 'action-diagnostic' ? '/world-plan-edit/actions/action-a/terminal-diagnostic' : kind.startsWith('action-') ? '/world-plan-edit/actions/action-a/prompts' : '/worlds/world%2Fa/conversation/turns/turn-a/' + (kind === 'source-passage' ? 'source-passages/0' : kind === 'native-body' ? 'native-body-excerpts/0' : kind === 'native-section' ? 'native-source-sections/0' : kind === 'related-page' ? 'related-pages/12345678-1234-1234-1234-123456789012' : 'context-trace'))
    if (kind.startsWith('action-')) expect(init?.cache).toBe('no-store')
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


const correctionPath = '/api/live/extract-promote/runs/parent%2Frun/recap-evidence-corrections'
it('authorizes recap correction with local cookie CSRF and blocks automatic mutation replay', async () => {
  const api = await setup(); let posts = 0
  vi.spyOn(globalThis, 'fetch').mockImplementation(async (url, init) => {
    if (String(url) === '/api/live/agent/local-session') return Response.json({ status: 'active', csrf_token: 'csrf-correction' })
    posts++
    expect(init?.method).toBe('POST'); expect(init?.body).toBe('{"frozen":true}')
    expect(new Headers(init?.headers).get('X-DMB-Graph-CSRF')).toBe('csrf-correction')
    expect(init?.redirect).toBe('error'); expect(init?.credentials).toBe('same-origin')
    return Response.json({ detail: { code: 'graph_auth_csrf_rejected' } }, { status: 403 })
  })
  const result = await api.authenticatedApiFetch(correctionPath, { method: 'POST', body: '{"frozen":true}' })
  expect(result.response.status).toBe(403); expect(posts).toBe(1)
})
it('forwards explicit correction bearer and never retries uncertain redirects', async () => {
  const api = await setup(); api.setNativeGraphAccessToken('synthetic-correction-token')
  const fetch = vi.spyOn(globalThis, 'fetch').mockRejectedValue(new TypeError('redirect rejected'))
  await expect(api.authenticatedApiFetch(correctionPath, { method: 'POST', body: '{}' })).rejects.toThrow()
  expect(fetch).toHaveBeenCalledTimes(1)
  expect(new Headers(fetch.mock.calls[0][1]?.headers).get('Authorization')).toBe('Bearer synthetic-correction-token')
  expect(fetch.mock.calls[0][1]?.redirect).toBe('error')
})
it('refuses remote correction destinations before mutation', async () => {
  const api = await setup('https://example.invalid'); api.setNativeGraphAccessToken('synthetic-correction-token')
  const fetch = vi.spyOn(globalThis, 'fetch')
  await expect(api.authenticatedApiFetch(correctionPath, { method: 'POST', body: '{}' })).rejects.toMatchObject({ status: 0 })
  expect(fetch).not.toHaveBeenCalled()
})
it.each(['/export', '-other'])('does not authorize a near-miss recap correction path %s', async suffix => {
  const api = await setup(); api.setNativeGraphAccessToken('synthetic-correction-token')
  const fetch = vi.spyOn(globalThis, 'fetch').mockResolvedValue(Response.json({}))
  await api.authenticatedApiFetch(correctionPath + suffix, { method: 'POST', body: '{}' })
  expect(new Headers(fetch.mock.calls[0][1]?.headers).has('Authorization')).toBe(false)
})

it.each(['/api/live/world-plan-edit/actions/action-a/prompts/attempt/export', '/api/live/world-plan-edit/actions/action-a/prompt'])('does not authorize near-miss Action prompt endpoint %s', async path => {
  const api = await setup(); api.setNativeGraphAccessToken('synthetic-evidence-token')
  const fetch = vi.spyOn(globalThis, 'fetch').mockResolvedValue(Response.json({}))
  await api.authenticatedApiFetch(path)
  expect(new Headers(fetch.mock.calls[0][1]?.headers).has('Authorization')).toBe(false)
})


it.each(['export','0/export','-1','1.5'])('does not authorize near-miss native section %s',async selector=>{
  const api=await setup();api.setNativeGraphAccessToken('synthetic-token');
  const fetch=vi.spyOn(globalThis,'fetch').mockResolvedValue(Response.json({}));
  await api.authenticatedApiFetch('/api/live/agent/worlds/world/conversation/turns/turn/native-source-sections/'+selector);
  expect(new Headers(fetch.mock.calls[0][1]?.headers).has('Authorization')).toBe(false);
});
it.each([-1,16384,0.5,NaN])('rejects invalid native section index before fetching %s',async index=>{
  const api=await setup();const fetch=vi.spyOn(globalThis,'fetch');
  await expect(api.getAgentNativeSourceSection('world','turn',index)).rejects.toThrow('Invalid section index');
  expect(fetch).not.toHaveBeenCalled();
});

it.each(['export','12345678-1234-1234-1234-123456789012/export','-1','1.5'])('does not authorize near-miss related page %s',async selector=>{
  const api=await setup();api.setNativeGraphAccessToken('synthetic-token');
  const fetch=vi.spyOn(globalThis,'fetch').mockResolvedValue(Response.json({}));
  await api.authenticatedApiFetch('/api/live/agent/worlds/world/conversation/turns/turn/related-pages/'+selector);
  expect(new Headers(fetch.mock.calls[0][1]?.headers).has('Authorization')).toBe(false);
});

const planRoute='/api/live/agent/worlds/world/conversations/11111111-1111-4111-8111-111111111111/work-plans/22222222-2222-4222-8222-222222222222';
it.each(['PUT','POST'])('never repeats an uncertain work-plan %s',async method=>{const api=await setup();api.setNativeGraphAccessToken('synthetic-plan-token');const fetch=vi.spyOn(globalThis,'fetch').mockRejectedValue(new TypeError('unknown outcome'));await expect(api.authenticatedApiFetch(planRoute+(method==='POST'?'/continue':''),{method,body:'{}'})).rejects.toThrow();expect(fetch).toHaveBeenCalledTimes(1);expect(new Headers(fetch.mock.calls[0][1]?.headers).get('Authorization')).toBe('Bearer synthetic-plan-token')});
it.each(['/export','/continue/export','-other'])('does not authorize near-miss work-plan %s',async suffix=>{const api=await setup();api.setNativeGraphAccessToken('synthetic-plan-token');const fetch=vi.spyOn(globalThis,'fetch').mockResolvedValue(Response.json({}));await api.authenticatedApiFetch(planRoute+suffix);expect(new Headers(fetch.mock.calls[0][1]?.headers).has('Authorization')).toBe(false)});

it.each([-1,0.5,16384,NaN])('refuses malformed native body excerpt indexes before fetching: %s',async index=>{
  const api=await setup();const fetch=vi.spyOn(globalThis,'fetch');
  await expect(api.getAgentNativeBodyExcerpt('world','turn',index)).rejects.toThrow('Invalid excerpt index');
  expect(fetch).not.toHaveBeenCalled();
});
