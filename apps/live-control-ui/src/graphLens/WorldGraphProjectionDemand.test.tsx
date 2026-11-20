import { act, cleanup, renderHook, waitFor } from '@testing-library/react';
import { createElement, StrictMode, type ReactNode } from 'react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import * as api from '../api/liveApi';
import type { ManagedWorldGraphProjectionResponse, WorldGraphProjection } from '../api/types';
import { SelectedWorldProvider } from '../selectedWorld/SelectedWorldContext';
import { WorldGraphLensProvider } from './WorldGraphLensContext';
import {
  WorldGraphLensProjectionProvider, useWorldGraphLensProjection,
  useWorldGraphLensProjectionDemand, useOptionalWorldGraphLensInformationChannel,
  WORLD_GRAPH_REVISION_COMMITTED_EVENT,
} from './useWorldGraphLensProjection';

function projection(revision = 'head'): WorldGraphProjection {
  return {
    schema:'dmb_world_graph_projection_v1',
    snapshot:{worldId:'eldyrwild',campaignId:'',revisionId:revision,headRevisionId:revision,
      isHead:true,focus:{kind:'none',sessionId:null},admissibility:'gm',scopeMode:'world'},
    summary:{nodeCount:1,relationshipCount:0,attributeCount:0,evidenceCount:0,
      sourceArtifactCount:0,projectionTruncated:false},
    nodes:[{nodeId:'road',label:'Road',kind:'location',role:null,aliases:[],sourceDomains:[],
      summary:'Saved graph bytes',anchoredToFocusSession:false,evidenceBadges:[],adjacency:[],
      suggestedExpansions:[],evidenceRefIds:[],sourceArtifactIds:[]}],relationships:[],attributes:[],evidence:[],sourceArtifacts:[],diagnostics:[],
  };
}
function managedProjection(revision = 'head'): ManagedWorldGraphProjectionResponse {
  return {schema:'dmb_managed_world_graph_projection_v1',managedWorldId:'managed',nativeWorldId:'eldyrwild',bindingVersion:1,projection:projection(revision)};
}
function deferred<T>() {
  let resolve!:(value:T)=>void, reject!:(reason:unknown)=>void;
  const promise=new Promise<T>((yes,no)=>{resolve=yes;reject=no});
  return {promise,resolve,reject};
}
let refresh='initial';
function wrapper({children}:{children:ReactNode}) {
  return createElement(SelectedWorldProvider,{locationSnapshot:'http://localhost/play?world=managed'},
    createElement(WorldGraphLensProvider,{planCampaignId:'longmont-c2'},
      createElement(WorldGraphLensProjectionProvider,{defaultCampaignId:'longmont-c2',revisionRefreshToken:refresh},children)));
}
function observe(a:boolean,b:boolean) {
  const retry=useWorldGraphLensProjectionDemand(a);
  useWorldGraphLensProjectionDemand(b);
  return {value:useWorldGraphLensProjection(),channel:useOptionalWorldGraphLensInformationChannel(),retry};
}
beforeEach(()=>{
  refresh='initial'; window.history.replaceState({},'', '/play');
  api.setNativeGraphAccessToken('demand-test');
  vi.spyOn(api,"getSourceSessions").mockResolvedValue([]);
  vi.spyOn(api,'listWorldContainers').mockResolvedValue({schema_version:'dmb_world_container_registry_v1',records:[{schema_version:'dmb_world_container_record_v1',world_id:'managed',name:'Managed World',source_root_relpath:'corpus/managed',created_at:'2026-01-01T00:00:00Z'}]});
  vi.spyOn(api,'postWorldGraphProjection').mockRejectedValue(new Error('Retired projection must not be called'));
});
afterEach(()=>{expect(api.postWorldGraphProjection).not.toHaveBeenCalled();cleanup();vi.restoreAllMocks();api.setNativeGraphAccessToken(null)});

describe('explicit projection demand',()=>{
  it('keeps observers idle, shares two owners, drops retained channel bytes on last release and reopens fresh',async()=>{
    const load=vi.spyOn(api,'postManagedWorldGraphProjection').mockResolvedValue(managedProjection());
    const view=renderHook(({a,b})=>observe(a,b),{wrapper,initialProps:{a:false,b:false}});
    await waitFor(()=>expect(view.result.current.value.projectionState).toBe('idle'));
    expect(view.result.current.value.request).not.toBeNull();
    expect(view.result.current.channel).toBeNull();expect(load).not.toHaveBeenCalled();
    view.rerender({a:true,b:true});
    await waitFor(()=>expect(view.result.current.value.projectionState).toBe('ready'));
    expect(load).toHaveBeenCalledTimes(1);
    const channel=view.result.current.channel!;
    expect(channel.getSnapshot().state.status).toBe('ready');
    view.rerender({a:false,b:true});
    expect(view.result.current.channel).toBe(channel);expect(load).toHaveBeenCalledTimes(1);
    view.rerender({a:false,b:false});
    expect(view.result.current.channel).toBeNull();
    expect(view.result.current.value).toMatchObject({projectionState:'idle',projection:null,nodeCount:0});
    expect(channel.getSnapshot().state).toEqual({status:'loading',diagnostics:[]});
    view.rerender({a:true,b:false});
    await waitFor(()=>expect(view.result.current.value.projectionState).toBe('ready'));
    expect(load).toHaveBeenCalledTimes(2);expect(view.result.current.channel).not.toBe(channel);
  });

  it.each(['resolve','reject'] as const)('aborts the last pending lease and ignores late %s on its retained channel',async settlement=>{
    const gate=deferred<ManagedWorldGraphProjectionResponse>();
    const load=vi.spyOn(api,'postManagedWorldGraphProjection').mockReturnValue(gate.promise);
    const view=renderHook(({a,b})=>observe(a,b),{wrapper,initialProps:{a:true,b:true}});
    await waitFor(()=>expect(load).toHaveBeenCalledTimes(1));
    const signal=load.mock.calls[0]![1]!;const channel=view.result.current.channel!;
    view.rerender({a:false,b:true});expect(signal.aborted).toBe(false);
    view.rerender({a:false,b:false});expect(signal.aborted).toBe(true);
    const retired=channel.getSnapshot();
    await act(async()=>{if(settlement==='resolve')gate.resolve(managedProjection('late'));else gate.reject(new Error('late error'))});
    expect(channel.getSnapshot()).toBe(retired);expect(view.result.current.value.projectionState).toBe('idle');
  });

  it('does no HTTP for idle revision/access events and refreshes exactly once when active',async()=>{
    const load=vi.spyOn(api,'postManagedWorldGraphProjection').mockResolvedValue(managedProjection());
    const view=renderHook(({a,b})=>observe(a,b),{wrapper,initialProps:{a:false,b:false}});
    act(()=>{window.dispatchEvent(new Event(WORLD_GRAPH_REVISION_COMMITTED_EVENT));api.setNativeGraphAccessToken('rotated-idle')});
    expect(load).not.toHaveBeenCalled();
    view.rerender({a:true,b:false});await waitFor(()=>expect(view.result.current.value.projectionState).toBe('ready'));
    act(()=>window.dispatchEvent(new Event(WORLD_GRAPH_REVISION_COMMITTED_EVENT)));
    await waitFor(()=>expect(load).toHaveBeenCalledTimes(2));
    act(()=>api.setNativeGraphAccessToken('rotated-active'));
    await waitFor(()=>expect(load).toHaveBeenCalledTimes(3));
    await waitFor(()=>expect(view.result.current.value.projectionState).toBe('ready'));
    act(()=>window.dispatchEvent(new Event(api.NATIVE_GRAPH_ACCESS_TOKEN_CHANGED_EVENT)));
    expect(load).toHaveBeenCalledTimes(3);
  });

  it('uses distinct channel generations for A→B→A and rejects late success and failure',async()=>{
    const old=deferred<ManagedWorldGraphProjectionResponse>(),middle=deferred<ManagedWorldGraphProjectionResponse>(),current=deferred<ManagedWorldGraphProjectionResponse>();
    const load=vi.spyOn(api,'postManagedWorldGraphProjection').mockReturnValueOnce(old.promise).mockReturnValueOnce(middle.promise).mockReturnValueOnce(current.promise);
    const view=renderHook(()=>observe(true,false),{wrapper});
    await waitFor(()=>expect(load).toHaveBeenCalledTimes(1));const channelA=view.result.current.channel!;
    refresh='middle';view.rerender();await waitFor(()=>expect(load).toHaveBeenCalledTimes(2));
    refresh='initial';view.rerender();await waitFor(()=>expect(load).toHaveBeenCalledTimes(3));
    expect(view.result.current.value.projection).toBeNull();expect(view.result.current.channel).not.toBe(channelA);
    await act(async()=>{current.resolve(managedProjection('current'))});
    await waitFor(()=>expect(view.result.current.value.projectionState).toBe('ready'));
    const accepted=view.result.current.channel!.getSnapshot();
    await act(async()=>{old.resolve(managedProjection('old'));middle.reject(new Error('middle'))});
    expect(view.result.current.channel!.getSnapshot()).toBe(accepted);
    expect(view.result.current.value.projection?.snapshot.revisionId).toBe('current');
    expect(channelA.getSnapshot().state.status).toBe('loading');
  });

  it('keeps response mismatches as integrity errors without admitting graph bytes',async()=>{
    vi.spyOn(api,'postManagedWorldGraphProjection').mockResolvedValue({...managedProjection(),projection:{...projection(),snapshot:{...projection().snapshot,worldId:'wrong-world'}}});
    const view=renderHook(()=>observe(true,false),{wrapper});
    await waitFor(()=>expect(view.result.current.value.projectionState).toBe('error'));
    expect(view.result.current.value.projection).toBeNull();
    expect(view.result.current.channel!.getSnapshot().state.status).toBe('integrity_error');
    expect(view.result.current.channel!.getSnapshot().state).not.toHaveProperty('value');
  });

  it('ignores a retry callback retained from a retired scope',async()=>{
    const load=vi.spyOn(api,'postManagedWorldGraphProjection').mockResolvedValue(managedProjection());
    const view=renderHook(()=>observe(true,false),{wrapper});
    await waitFor(()=>expect(view.result.current.value.projectionState).toBe('ready'));
    const oldRetry=view.result.current.retry!;
    refresh='replacement';view.rerender();
    await waitFor(()=>expect(view.result.current.value.projectionState).toBe('ready'));
    expect(load).toHaveBeenCalledTimes(2);
    act(()=>oldRetry());expect(load).toHaveBeenCalledTimes(2);
  });

  it('keeps one current load under StrictMode effect replay',async()=>{
    const load=vi.spyOn(api,'postManagedWorldGraphProjection').mockResolvedValue(managedProjection());
    const view=renderHook(()=>observe(true,true),{wrapper:({children})=>createElement(StrictMode,null,createElement(wrapper,null,children))});
    await waitFor(()=>expect(view.result.current.value.projectionState).toBe('ready'));
    expect(load).toHaveBeenCalledTimes(1);
    view.unmount();expect(load.mock.calls[0]![1]!.aborted).toBe(true);
  });

  it('retries a failed active load only on explicit retry'   ,async()=>{
    const load=vi.spyOn(api,'postManagedWorldGraphProjection').mockRejectedValueOnce(new Error('offline')).mockResolvedValue(managedProjection());
    const view=renderHook(()=>observe(true,false),{wrapper});
    await waitFor(()=>expect(view.result.current.value.projectionState).toBe('error'));
    view.rerender();expect(load).toHaveBeenCalledTimes(1);
    act(()=>view.result.current.retry!());await waitFor(()=>expect(view.result.current.value.projectionState).toBe('ready'));
    expect(load).toHaveBeenCalledTimes(2);
  });
});
