import {afterEach,expect,it,vi} from 'vitest';
const document='11111111-1111-4111-8111-111111111111';
const routes=['',`/${document}/scenes/scene:gate`,`/${document}/scenes/scene:gate/versions/1`,`/operations/${document}`,'/cancel'];
async function setup(base=''){vi.stubEnv('VITE_LIVE_API_BASE_URL',base);vi.resetModules();return import('./liveApi');}
afterEach(()=>{vi.restoreAllMocks();vi.unstubAllEnvs();});
it.each(routes)('authenticates scene-template route %s using the actual shared transport',async tail=>{
 const api=await setup();api.setNativeGraphAccessToken('synthetic-template-token');
 const fetch=vi.spyOn(globalThis,'fetch').mockResolvedValue(Response.json(null));
 await api.authenticatedApiFetch(`/api/live/combat/scene-templates${tail}?world_id=elderwyld`,{cache:'no-store'});
 expect(fetch).toHaveBeenCalledTimes(1);const [,init]=fetch.mock.calls[0];expect(new Headers(init?.headers).get('Authorization')).toBe('Bearer synthetic-template-token');expect(init?.credentials).toBe('same-origin');expect(init?.redirect).toBe('error');
});
it.each(['','/cancel'])('bootstraps session CSRF for a scene-template mutation %s',async tail=>{
 const api=await setup();api.setNativeGraphAccessToken(null);
 const fetch=vi.spyOn(globalThis,'fetch').mockResolvedValueOnce(Response.json({status:'active',csrf_token:'template-session-csrf'})).mockResolvedValueOnce(Response.json({ok:true}));
 await api.authenticatedApiFetch(`/api/live/combat/scene-templates${tail}?world_id=elderwyld`,{method:'POST',headers:{'Content-Type':'application/json'},body:'{}'});
 expect(fetch).toHaveBeenCalledTimes(2);expect(String(fetch.mock.calls[0][0])).toContain('/api/live/agent/local-session');
 const [,init]=fetch.mock.calls[1];expect(new Headers(init?.headers).get('X-DMB-Graph-CSRF')).toBe('template-session-csrf');expect(init?.credentials).toBe('same-origin');expect(init?.redirect).toBe('error');
});
it.each(routes)('refuses remote credential destinations for scene-template route %s',async tail=>{
 const api=await setup('https://example.invalid');api.setNativeGraphAccessToken('synthetic-template-token');const fetch=vi.spyOn(globalThis,'fetch');
 await expect(api.authenticatedApiFetch(`/api/live/combat/scene-templates${tail}?world_id=elderwyld`)).rejects.toThrow('loopback');expect(fetch).not.toHaveBeenCalled();
});
