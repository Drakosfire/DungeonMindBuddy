import {afterEach,expect,it,vi} from 'vitest';
const intent={world_id:'test-world',document_source:{documentId:'11111111-1111-4111-8111-111111111111',revision:4,contentSha256:'a'.repeat(64)},quote:'A past temporary stint.',source:{node_id:null,label:'Rowan',kind:'npc'},target:{node_id:'node:brin',label:'Brin',kind:'npc'},predicate:'works_with',label:'worked together',context:'A past temporary stint.'};
const request={worldId:intent.world_id,campaignId:intent.world_id,documentSource:intent.document_source,proposals:[{}]};
afterEach(()=>{vi.restoreAllMocks();vi.unstubAllEnvs();vi.resetModules();});
async function modules(base=''){vi.stubEnv('VITE_LIVE_API_BASE_URL',base);vi.resetModules();return {live:await import('./liveApi'),relationship:await import('./graphDocumentRelationshipApi')};}
it('uses guarded bearer transport for the exact relationship source adapter',async()=>{
 const {live,relationship}=await modules();live.setNativeGraphAccessToken('synthetic-relationship-token');const fetch=vi.spyOn(globalThis,'fetch').mockResolvedValue(Response.json(request));await relationship.graphDocumentRelationshipRequest(intent);
 expect(new Headers(fetch.mock.calls[0][1]?.headers).get('Authorization')).toBe('Bearer synthetic-relationship-token');expect(fetch.mock.calls[0][1]).toMatchObject({redirect:'error',credentials:'same-origin',cache:'no-store'});
});
it('uses the local-session CSRF header for source/native review',async()=>{
 const {relationship}=await modules();const fetch=vi.spyOn(globalThis,'fetch').mockResolvedValueOnce(Response.json({status:'active',csrf_token:'synthetic-csrf'})).mockResolvedValueOnce(Response.json(request));await relationship.graphDocumentRelationshipRequest(intent);expect(new Headers(fetch.mock.calls[1][1]?.headers).get('X-DMB-Graph-CSRF')).toBe('synthetic-csrf');
});
it('refuses remote destinations before transmitting source or credentials',async()=>{
 const {live,relationship}=await modules('https://outside.invalid');live.setNativeGraphAccessToken('synthetic-relationship-token');const fetch=vi.spyOn(globalThis,'fetch');await expect(relationship.graphDocumentRelationshipRequest(intent)).rejects.toThrow(/loopback/);expect(fetch).not.toHaveBeenCalled();
});
it('does not attach credentials to near-miss adapter paths',async()=>{
 const {live}=await modules();live.setNativeGraphAccessToken('synthetic-relationship-token');const fetch=vi.spyOn(globalThis,'fetch').mockResolvedValue(Response.json({}));for(const path of ['/api/live/graph-authoring/document-relationship/request-extra','/api/live/graph-authoring/document-relationship/request/extra'])await live.authenticatedApiFetch(path);for(const call of fetch.mock.calls)expect(new Headers(call[1]?.headers).has('Authorization')).toBe(false);
});
