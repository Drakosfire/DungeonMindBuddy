import {afterEach,describe,expect,it,vi} from 'vitest';
import * as api from './liveApi';
import {getReadWaveVersion} from './inFlightReads';
import {WORLD_GRAPH_REVISION_COMMITTED_EVENT} from '../planSurface/reference/planGraphContextRequest';
import type {WorldGraphProjectionRequest} from './types';
const request:WorldGraphProjectionRequest={schema:'dmb_world_graph_projection_request_v1',worldId:'native-world',campaignId:'',scopeMode:'world',focus:{kind:'none',sessionId:null},admissibility:'gm'};
const kinds=['native','recap','managed'] as const;
type Kind=typeof kinds[number];
function read(kind:Kind){return kind==='native'?api.postWorldGraphProjection(request):kind==='recap'?api.postWorldGraphRecapProjection(request):api.postManagedWorldGraphProjection({schema:'dmb_managed_world_graph_projection_request_v1',managedWorldId:'managed-world'})}
function deferred<T>(){let resolve!:(value:T)=>void;const promise=new Promise<T>(r=>{resolve=r});return{promise,resolve}}
afterEach(()=>{vi.unstubAllGlobals();api.setNativeGraphAccessToken(null);vi.restoreAllMocks()});
describe.each(kinds)('%s projection transport ownership',kind=>{
 it('shares equivalent pending reads, then performs a fresh settled read',async()=>{
  api.setNativeGraphAccessToken('projection-pending');const gate=deferred<Response>();const fetch=vi.spyOn(globalThis,'fetch').mockReturnValueOnce(gate.promise).mockResolvedValue(Response.json({capture:'fresh'}));
  const first=read(kind),second=read(kind);await vi.waitFor(()=>expect(fetch).toHaveBeenCalledTimes(1));gate.resolve(Response.json({capture:'shared'}));
  expect(await first).toEqual({capture:'shared'});expect(await second).toEqual({capture:'shared'});
  expect(await read(kind)).toEqual({capture:'fresh'});expect(fetch).toHaveBeenCalledTimes(2);
 });
 it('does not memoize settled failures',async()=>{
  api.setNativeGraphAccessToken('projection-error');const fetch=vi.spyOn(globalThis,'fetch').mockResolvedValueOnce(Response.json({detail:'unavailable'},{status:503})).mockResolvedValueOnce(Response.json({capture:'retry'}));
  await expect(read(kind)).rejects.toMatchObject({status:503});expect(await read(kind)).toEqual({capture:'retry'});expect(fetch).toHaveBeenCalledTimes(2);
 });
 it('keeps post-commit acquisition separate and old settlement cannot remove its pending owner',async()=>{
  api.setNativeGraphAccessToken('projection-revision');const old=deferred<Response>(),fresh=deferred<Response>();const fetch=vi.spyOn(globalThis,'fetch').mockReturnValueOnce(old.promise).mockReturnValue(fresh.promise);
  const before=read(kind);await vi.waitFor(()=>expect(fetch).toHaveBeenCalledTimes(1));window.dispatchEvent(new Event(WORLD_GRAPH_REVISION_COMMITTED_EVENT));
  const after=read(kind);await vi.waitFor(()=>expect(fetch).toHaveBeenCalledTimes(2));old.resolve(Response.json({capture:'before'}));expect(await before).toEqual({capture:'before'});
  const joined=read(kind);await Promise.resolve();expect(fetch).toHaveBeenCalledTimes(2);
  fresh.resolve(Response.json({capture:'after'}));expect(await after).toEqual({capture:'after'});expect(await joined).toEqual({capture:'after'});
 });
});
it('does not join different World, scope, query, pin or caller headers',async()=>{
 api.setNativeGraphAccessToken('projection-identities');const gate=deferred<void>();const fetch=vi.spyOn(globalThis,'fetch').mockImplementation(()=>gate.promise.then(()=>Response.json({capture:'bound'})));
 const reads=[api.postWorldGraphProjection(request),api.postWorldGraphProjection({...request,worldId:'other'}),api.postWorldGraphProjection({...request,campaignId:'c1',scopeMode:'campaign'}),api.postWorldGraphProjection({...request,queryText:'road'}),api.postWorldGraphProjection({...request,revisionPin:'revision'})];
 const headerRead=api.authenticatedApiFetch('/api/live/world-graph/projection',{method:'POST',body:JSON.stringify(request),headers:{'X-Fixture':'different'}});
 await vi.waitFor(()=>expect(fetch).toHaveBeenCalledTimes(6));gate.resolve();await Promise.all([...reads,headerRead]);
});
it('binds one invalidation listener across all projection wrappers',async()=>{
 api.setNativeGraphAccessToken('projection-listener');vi.spyOn(globalThis,'fetch').mockImplementation(async()=>Response.json({capture:'value'}));
 await Promise.all(kinds.map(read));const version=getReadWaveVersion();window.dispatchEvent(new Event(WORLD_GRAPH_REVISION_COMMITTED_EVENT));expect(getReadWaveVersion()).toBe(version+1);
});
it.each(['before','after'])('invalidates before a bubble refresh consumer registered %s the first request',async ordering=>{
 api.setNativeGraphAccessToken('projection-event-order');const old=deferred<Response>(),fresh=deferred<Response>();const fetch=vi.spyOn(globalThis,'fetch').mockReturnValueOnce(old.promise).mockReturnValue(fresh.promise);let refreshed:ReturnType<typeof read>|undefined;
 const consumer=()=>{refreshed=read('native')};if(ordering==='before')window.addEventListener(WORLD_GRAPH_REVISION_COMMITTED_EVENT,consumer);
 try{
  const initial=read('native');await vi.waitFor(()=>expect(fetch).toHaveBeenCalledTimes(1));if(ordering==='after')window.addEventListener(WORLD_GRAPH_REVISION_COMMITTED_EVENT,consumer);
  window.dispatchEvent(new Event(WORLD_GRAPH_REVISION_COMMITTED_EVENT));await vi.waitFor(()=>expect(fetch).toHaveBeenCalledTimes(2));old.resolve(Response.json({capture:'old'}));fresh.resolve(Response.json({capture:'new'}));expect(await initial).toEqual({capture:'old'});expect(await refreshed).toEqual({capture:'new'});
 }finally{window.removeEventListener(WORLD_GRAPH_REVISION_COMMITTED_EVENT,consumer)}
});
it('moves invalidation ownership to a replacement event target',async()=>{
 api.setNativeGraphAccessToken('projection-window');vi.spyOn(globalThis,'fetch').mockResolvedValue(Response.json({capture:'bound'}));await read('native');
 const prior=window;const replacement=Object.assign(new EventTarget(),{location:prior.location});vi.stubGlobal('window',replacement);await read('managed');
 const version=getReadWaveVersion();prior.dispatchEvent(new Event(WORLD_GRAPH_REVISION_COMMITTED_EVENT));expect(getReadWaveVersion()).toBe(version);
 replacement.dispatchEvent(new Event(WORLD_GRAPH_REVISION_COMMITTED_EVENT));expect(getReadWaveVersion()).toBe(version+1);
});
