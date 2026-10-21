import {afterEach,expect,it,vi} from 'vitest';

const request={request_id:'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa',
  document_id:'bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb',expected_revision:2,
  expected_content_sha256:'a'.repeat(64),managed_world_id:'public-park',
  campaign_id:'public-park-new-campaign',session:1,session_evidence:[]};
const recovery=`/api/live/graph-preview/build-recap-launches/${request.request_id}?document_id=${request.document_id}&managed_world_id=public-park`;
afterEach(()=>{vi.restoreAllMocks();vi.unstubAllEnvs();vi.resetModules();});

async function modules(base=''){
  vi.stubEnv('VITE_LIVE_API_BASE_URL',base);vi.resetModules();
  const live=await import('./liveApi');
  const recap=await import('./buildRecapApi');
  return {live,recap};
}

it('sends session CSRF on the real Build launch wrapper and authenticates recovery',async()=>{
  const {recap}=await modules();
  const fetch=vi.spyOn(globalThis,'fetch')
    .mockResolvedValueOnce(Response.json({status:'active',csrf_token:'public-test-csrf'}))
    .mockResolvedValueOnce(Response.json({run:{run_id:'saved'}}))
    .mockResolvedValueOnce(Response.json({run:{run_id:'saved'}}));
  await recap.launchBuildRecap(request);
  await recap.recoverBuildRecap(request);
  expect(fetch).toHaveBeenCalledTimes(3);
  const launch=fetch.mock.calls[1];
  expect(launch[0]).toBe('/api/live/graph-preview/build-recap-launches');
  expect(new Headers(launch[1]?.headers).get('X-DMB-Graph-CSRF')).toBe('public-test-csrf');
  expect(launch[1]).toMatchObject({method:'POST',credentials:'same-origin',redirect:'error',cache:'no-store',body:JSON.stringify(request)});
  expect(fetch.mock.calls[2][0]).toBe(recovery);
  expect(fetch.mock.calls[2][1]).toMatchObject({credentials:'same-origin',redirect:'error'});
});

it.each(['launch','recover'])('sends a memory-only bearer for %s',async operation=>{
  const {live,recap}=await modules();
  live.setNativeGraphAccessToken('public-test-local-operator-token');
  const fetch=vi.spyOn(globalThis,'fetch').mockResolvedValue(Response.json({run:{run_id:'saved'}}));
  await (operation==='launch'?recap.launchBuildRecap(request):recap.recoverBuildRecap(request));
  expect(fetch).toHaveBeenCalledTimes(1);
  expect(new Headers(fetch.mock.calls[0][1]?.headers).get('Authorization')).toBe('Bearer public-test-local-operator-token');
  expect(fetch.mock.calls[0][1]?.redirect).toBe('error');
});

it.each(['launch','recover'])('refuses a remote API destination before %s',async operation=>{
  const {live,recap}=await modules('https://outside.invalid');
  live.setNativeGraphAccessToken('public-test-local-operator-token');
  const fetch=vi.spyOn(globalThis,'fetch');
  await expect(operation==='launch'?recap.launchBuildRecap(request):recap.recoverBuildRecap(request)).rejects.toThrow(/loopback/);
  expect(fetch).not.toHaveBeenCalled();
});

it('does not broaden authentication to sibling graph-preview paths',async()=>{
  const {live}=await modules();
  live.setNativeGraphAccessToken('public-test-local-operator-token');
  const fetch=vi.spyOn(globalThis,'fetch').mockResolvedValue(Response.json({}));
  await live.authenticatedApiFetch('/api/live/graph-preview/build-recap-launches-other');
  await live.authenticatedApiFetch(`${recovery.split('?')[0]}/extra`);
  for(const call of fetch.mock.calls){
    expect(new Headers(call[1]?.headers).has('Authorization')).toBe(false);
    expect(new Headers(call[1]?.headers).has('X-DMB-Graph-CSRF')).toBe(false);
  }
});
