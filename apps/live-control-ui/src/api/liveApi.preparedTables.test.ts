import {afterEach,it,expect,vi} from 'vitest';
afterEach(()=>{vi.restoreAllMocks();vi.unstubAllEnvs()});
it.each(['','/receipts','/commands/11111111-1111-4111-8111-111111111111'])('authenticates exact prepared-table route %s',async tail=>{
  vi.stubEnv('VITE_LIVE_API_BASE_URL','');vi.resetModules();const api=await import('./liveApi');api.setNativeGraphAccessToken('prepared-table-test-token');
  const fetch=vi.spyOn(globalThis,'fetch').mockResolvedValue(Response.json({ok:true}));
  await api.authenticatedApiFetch(`/api/live/world-play-runs/v2/11111111-1111-4111-8111-111111111111/prepared-tables${tail}?world_id=world`,{cache:'no-store'});
  const [,init]=fetch.mock.calls[0];expect(new Headers(init?.headers).get('Authorization')).toBe('Bearer prepared-table-test-token');expect(init?.redirect).toBe('error');
});
