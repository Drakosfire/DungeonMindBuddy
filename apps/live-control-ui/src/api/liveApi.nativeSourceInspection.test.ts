import {afterEach,expect,it,vi} from 'vitest';
const scope={managed_world_id:'w',native_world_id:'n',binding_version:1,revision_id:'r',scope_mode:'world' as const,campaign_id:null};
const selected={source_artifact_id:'source',source_revision_id:'saved',evidence_ref_id:'evidence'};
afterEach(()=>{vi.restoreAllMocks();vi.unstubAllEnvs();vi.resetModules();});
async function setup(base=''){vi.stubEnv('VITE_LIVE_API_BASE_URL',base);vi.resetModules();return import('./liveApi');}
it.each(['catalog','read'] as const)('authenticates the exact source %s wrapper without redirects',async kind=>{
 const api=await setup();api.setNativeGraphAccessToken('synthetic-source-token');
 const fetch=vi.spyOn(globalThis,'fetch').mockResolvedValue(Response.json({}));
 await (kind==='catalog'?api.getNativeSourceCatalog(scope):api.readNativeSource(scope,selected));
 expect(fetch).toHaveBeenCalledTimes(1);const [url,init]=fetch.mock.calls[0];
 expect(url).toBe(`/api/live/native-source-inspection/${kind}`);
 expect(new Headers(init?.headers).get('Authorization')).toBe('Bearer synthetic-source-token');
 expect(init).toMatchObject({method:'POST',credentials:'same-origin',redirect:'error',cache:'no-store'});
 expect(JSON.parse(String(init?.body))).toEqual(kind==='catalog'?scope:{scope,...selected});
});
it.each(['catalog','read'] as const)('refuses a remote source %s destination before sending a token',async kind=>{
 const api=await setup('https://outside.invalid');api.setNativeGraphAccessToken('synthetic-source-token');const fetch=vi.spyOn(globalThis,'fetch');
 await expect(kind==='catalog'?api.getNativeSourceCatalog(scope):api.readNativeSource(scope,selected)).rejects.toThrow(/loopback/);expect(fetch).not.toHaveBeenCalled();
});
it('renews an expired local session and retries the same exact read body once',async()=>{
 const api=await setup();let reads=0,boots=0;const bodies:string[]=[];
 vi.spyOn(globalThis,'fetch').mockImplementation(async(url,init)=>{
  if(String(url)==='/api/live/agent/local-session'){
   if(init?.method==='POST'){boots++;return Response.json({status:'active',csrf_token:`csrf-${boots}`});}
   return new Response(null,{status:401});
  }
  reads++;bodies.push(String(init?.body));expect(new Headers(init?.headers).get('X-DMB-Graph-CSRF')).toBe(`csrf-${boots}`);
  return reads===1?Response.json({detail:{code:'graph_auth_required'}},{status:401}):Response.json({fixture:true});
 });
 await expect(api.readNativeSource(scope,selected)).resolves.toEqual({fixture:true});expect(reads).toBe(2);expect(boots).toBe(2);expect(bodies[0]).toBe(bodies[1]);
});
it('does not authorize similarly named paths',async()=>{
 const api=await setup();api.setNativeGraphAccessToken('synthetic-source-token');const fetch=vi.spyOn(globalThis,'fetch').mockResolvedValue(Response.json({}));
 await api.authenticatedApiFetch('/api/live/native-source-inspection/catalog-extra');await api.authenticatedApiFetch('/api/live/native-source-inspection/read/other');
 for(const [,init] of fetch.mock.calls)expect(new Headers(init?.headers).has('Authorization')).toBe(false);
});
