import {afterEach,expect,it,vi} from 'vitest';
const corpus='a'.repeat(64),citation='b'.repeat(64);
async function setup(base=''){vi.stubEnv('VITE_LIVE_API_BASE_URL',base);vi.resetModules();return import('./liveApi')}
afterEach(()=>{vi.restoreAllMocks();vi.unstubAllEnvs()});
it.each(['catalog','query','passage'])('authenticates the exact passive %s read',async kind=>{
 const api=await setup();api.setNativeGraphAccessToken('rules-test-token');const fetch=vi.spyOn(globalThis,'fetch').mockResolvedValue(Response.json({fixture:true}));
 if(kind==='catalog')await api.getRulesCatalog();else if(kind==='query')await api.queryRulesEvidence(corpus,'a ?&= question');else await api.getRulesPassage(corpus,citation);
 const [url,init]=fetch.mock.calls[0];expect(String(url)).toContain('/api/live/rules/');expect(new Headers(init?.headers).get('Authorization')).toBe('Bearer rules-test-token');expect(init?.credentials).toBe('same-origin');expect(init?.redirect).toBe('error');expect(init?.cache).toBe('no-store');expect(init?.body).toBeUndefined();expect(fetch).toHaveBeenCalledTimes(1);
 if(kind==='query')expect(new URL(String(url),'http://localhost').searchParams.get('question')).toBe('a ?&= question');
});
it('shares identical pending queries, releases settled reads and keeps different queries distinct',async()=>{
 const api=await setup();api.setNativeGraphAccessToken('rules-test-token');let resolve!:(value:Response)=>void;
 const fetch=vi.spyOn(globalThis,'fetch').mockImplementation(()=>new Promise(done=>{resolve=done}));
 const a=api.queryRulesEvidence(corpus,'prone'),b=api.queryRulesEvidence(corpus,'prone');await vi.waitFor(()=>expect(fetch).toHaveBeenCalledTimes(1));resolve(Response.json({fixture:true}));await Promise.all([a,b]);
 fetch.mockResolvedValue(Response.json({fixture:true}));await api.queryRulesEvidence(corpus,'prone');await api.queryRulesEvidence(corpus,'travel');expect(fetch).toHaveBeenCalledTimes(3);
});
it('refuses remote credential destinations before fetching',async()=>{
 const api=await setup('https://example.invalid');api.setNativeGraphAccessToken('rules-test-token');const fetch=vi.spyOn(globalThis,'fetch');await expect(api.getRulesCatalog()).rejects.toThrow();expect(fetch).not.toHaveBeenCalled();
});

const historicalTarget = { worldId: 'world ?&', conversationId: '11111111-1111-4111-8111-111111111111',
 turnId: '22222222-2222-4222-8222-222222222222', attempt: 2,
 supportId: '33333333-3333-4333-8333-333333333333', supportSha256: 'a'.repeat(64) };
it('authenticates the exact saved Rules capsule without a catalog request',async()=>{
 const api=await setup();api.setNativeGraphAccessToken('rules-test-token');
 const fetch=vi.spyOn(globalThis,'fetch').mockResolvedValue(Response.json({fixture:true}));
 await api.getHistoricalRulesPassage(historicalTarget);
 expect(fetch).toHaveBeenCalledTimes(1);
 const [url,init]=fetch.mock.calls[0], parsed=new URL(String(url),'http://localhost');
 expect(parsed.pathname).toBe(`/api/live/agent/worlds/world%20%3F%26/conversation/turns/${historicalTarget.turnId}/rules-passages/${historicalTarget.supportId}`);
 expect(Object.fromEntries(parsed.searchParams)).toEqual({conversation_id:historicalTarget.conversationId,attempt:'2',support_sha256:historicalTarget.supportSha256});
 expect(new Headers(init?.headers).get('Authorization')).toBe('Bearer rules-test-token');
 expect(init?.cache).toBe('no-store');expect(init?.redirect).toBe('error');expect(init?.body).toBeUndefined();
});
it('coalesces identical saved-citation reads only while pending and separates attempts',async()=>{
 const api=await setup();api.setNativeGraphAccessToken('rules-test-token');let resolve!:(value:Response)=>void;
 const fetch=vi.spyOn(globalThis,'fetch').mockImplementation(()=>new Promise(done=>{resolve=done}));
 const a=api.getHistoricalRulesPassage(historicalTarget),b=api.getHistoricalRulesPassage({...historicalTarget});
 await vi.waitFor(()=>expect(fetch).toHaveBeenCalledTimes(1));resolve(Response.json({fixture:true}));await Promise.all([a,b]);
 fetch.mockResolvedValue(Response.json({fixture:true}));await api.getHistoricalRulesPassage(historicalTarget);
 await api.getHistoricalRulesPassage({...historicalTarget,attempt:3});expect(fetch).toHaveBeenCalledTimes(3);
});
it.each(['attempt','uuid','digest','world'])('rejects invalid saved-citation %s selectors before transport',async kind=>{
 const api=await setup();const fetch=vi.spyOn(globalThis,'fetch');const target={...historicalTarget};
 if(kind==='attempt')target.attempt=0;if(kind==='uuid')target.turnId='not-a-uuid';if(kind==='digest')target.supportSha256='A'.repeat(64);if(kind==='world')target.worldId='';
 expect(()=>api.getHistoricalRulesPassage(target)).toThrow('Invalid historical Rules citation');expect(fetch).not.toHaveBeenCalled();
});
