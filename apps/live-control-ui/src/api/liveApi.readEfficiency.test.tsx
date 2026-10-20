import { createElement, StrictMode, useEffect, type ReactNode } from "react";
import { act, cleanup, renderHook, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import * as api from "./liveApi";
import { SelectedWorldProvider } from "../selectedWorld/SelectedWorldContext";
import { WorldGraphLensProvider, WorldGraphLensProjectionProvider, useWorldGraphLensProjectionDemand, useWorldGraphLensProjection } from "../graphLens";
function deferred<T>() { let resolve!: (value:T)=>void; let reject!:(error:unknown)=>void; const promise=new Promise<T>((r,j)=>{resolve=r;reject=j;}); return {promise,resolve,reject}; }
afterEach(()=>{cleanup();vi.restoreAllMocks();api.setNativeGraphAccessToken(null);});
function managedPacket(revision:string){return {schema:"dmb_managed_world_graph_projection_v1",managedWorldId:"elderwyld",nativeWorldId:"native-world",bindingVersion:1,projection:{schema:"dmb_world_graph_projection_v1",snapshot:{worldId:"native-world",campaignId:"",revisionId:revision,headRevisionId:revision,isHead:true,focus:{kind:"none",sessionId:null},admissibility:"gm",scopeMode:"world"},summary:{nodeCount:0,relationshipCount:0,attributeCount:0,evidenceCount:0,sourceArtifactCount:0,projectionTruncated:false},nodes:[],relationships:[],attributes:[],evidence:[],sourceArtifacts:[],diagnostics:[]}}}
const historyPath="/api/live/agent/worlds/elderwyld/conversation?limit=40";
describe("protected read acquisition",()=>{
 it("reuses a pending World history request when its consumer effect restarts",async()=>{
  api.setNativeGraphAccessToken("strict-history-rehearsal");
  const gate=deferred<Response>();
  const fetch=vi.spyOn(globalThis,"fetch").mockReturnValue(gate.promise);
  const {rerender,unmount}=renderHook(({generation})=>{
   useEffect(()=>{
    const controller=new AbortController();
    void api.getWorldAgentConversationHistory("elderwyld",{limit:40,includeTurnCorrelation:true,signal:controller.signal}).catch(()=>undefined);
    return()=>controller.abort();
   },[generation]);
  },{wrapper:StrictMode,initialProps:{generation:0}});
  await waitFor(()=>expect(fetch).toHaveBeenCalledTimes(1));
  expect(String(fetch.mock.calls[0][0])).toBe("/api/live/agent/worlds/elderwyld/conversation?limit=40&include_turn_correlation=true");
  rerender({generation:1});
  expect(fetch).toHaveBeenCalledTimes(1);
  gate.resolve(Response.json({schema:"dmb_agent_conversation_history_v4",turns:[]}));
  unmount();
 });
 it("does not repeat mounted graph acquisition on its own cold session bootstrap",async()=>{
  window.history.replaceState({},"","/?world=elderwyld");
  vi.spyOn(api,"listWorldContainers").mockResolvedValue({schema_version:"dmb_world_container_registry_v1",records:[{schema_version:"dmb_world_container_record_v1",world_id:"elderwyld",name:"World",source_root_relpath:"corpus/world",created_at:"2026-01-01"}]} as never);
  vi.spyOn(api,"getSourceBundle").mockResolvedValue({schema:"dmb_ingestion_source_bundle_v1",campaigns:{}} as never);
  const gate=deferred<Response>();
  const fetch=vi.spyOn(globalThis,"fetch").mockImplementation(async url=>String(url).endsWith("local-session")?Response.json({status:"active",csrf_token:"test-csrf"}):gate.promise);
  const wrapper=({children}:{children:ReactNode})=>createElement(SelectedWorldProvider,{locationSnapshot:window.location.href},createElement(WorldGraphLensProvider,{planCampaignId:"elderwyld"},createElement(WorldGraphLensProjectionProvider,{defaultCampaignId:"elderwyld"},children)));
  const {result}=renderHook(()=>{useWorldGraphLensProjectionDemand(true);return useWorldGraphLensProjection()},{wrapper});
  await waitFor(()=>expect(fetch.mock.calls.some(([url])=>String(url).endsWith("managed-projection"))).toBe(true));
  await act(async()=>{await new Promise(r=>setTimeout(r,20));});
  expect(fetch.mock.calls.filter(([url])=>String(url).endsWith("managed-projection"))).toHaveLength(1);
  gate.resolve(Response.json({schema:"dmb_managed_world_graph_projection_v1",managedWorldId:"elderwyld",nativeWorldId:"native-world",bindingVersion:1,projection:{schema:"dmb_world_graph_projection_v1",snapshot:{worldId:"native-world",campaignId:"",revisionId:"rev-1",headRevisionId:"rev-1",isHead:true,focus:{kind:"none",sessionId:null},admissibility:"gm",scopeMode:"world"},summary:{nodeCount:0,relationshipCount:0,attributeCount:0,evidenceCount:0,sourceArtifactCount:0,projectionTruncated:false},nodes:[],relationships:[],attributes:[],evidence:[],sourceArtifacts:[],diagnostics:[]}}));
  await waitFor(()=>expect(result.current.projectionState).toBe("ready"));
 });
 it.each([false,true])("exposes failed local-session recovery as a terminal graph error; explicit retry=%s",async retry=>{
  api.setNativeGraphAccessToken('reset-session');api.setNativeGraphAccessToken(null);
  window.history.replaceState({},"","/?world=elderwyld");
  vi.spyOn(api,"listWorldContainers").mockResolvedValue({schema_version:"dmb_world_container_registry_v1",records:[{schema_version:"dmb_world_container_record_v1",world_id:"elderwyld",name:"World",source_root_relpath:"corpus/world",created_at:"2026-01-01"}]} as never);
  vi.spyOn(api,"getSourceBundle").mockResolvedValue({schema:"dmb_ingestion_source_bundle_v1",campaigns:{}} as never);
  let sessions=0;
  const fetch=vi.spyOn(globalThis,"fetch").mockImplementation(async url=>{
    if(String(url).endsWith("local-session")) return ++sessions===1
      ? Response.json({status:"active",csrf_token:"old-csrf"})
      : Response.json({detail:"session service unavailable"},{status:503});
    return Response.json({detail:{code:"graph_auth_required"}},{status:401});
  });
  const wrapper=({children}:{children:ReactNode})=>createElement(SelectedWorldProvider,{locationSnapshot:window.location.href},createElement(WorldGraphLensProvider,{planCampaignId:"elderwyld"},createElement(WorldGraphLensProjectionProvider,{defaultCampaignId:"elderwyld"},children)));
  const view=renderHook(()=>{const retry=useWorldGraphLensProjectionDemand(true);return{retry,value:useWorldGraphLensProjection()}},{wrapper});
  await waitFor(()=>expect(view.result.current.value.projectionState).toBe("error"));
  expect(view.result.current.value.projectionError).toContain("local_graph_session_recovery_failed");
  expect(view.result.current.value.projection).toBeNull();expect(sessions).toBe(2);
  expect(fetch.mock.calls.filter(([url])=>String(url).endsWith("managed-projection"))).toHaveLength(1);
  view.rerender();expect(sessions).toBe(2);
  if(retry){act(()=>view.result.current.retry!());await waitFor(()=>expect(sessions).toBe(3));
    await waitFor(()=>expect(view.result.current.value.projectionState).toBe("error"));}
 });
 it("recovers the actual projection API into a newly owned access generation",async()=>{
  api.setNativeGraphAccessToken('reset-recovery');api.setNativeGraphAccessToken(null);
  window.history.replaceState({},"","/?world=elderwyld");
  vi.spyOn(api,"listWorldContainers").mockResolvedValue({schema_version:"dmb_world_container_registry_v1",records:[{schema_version:"dmb_world_container_record_v1",world_id:"elderwyld",name:"World",source_root_relpath:"corpus/world",created_at:"2026-01-01"}]} as never);
  vi.spyOn(api,"getSourceBundle").mockResolvedValue({schema:"dmb_ingestion_source_bundle_v1",campaigns:{}} as never);
  let sessions=0,projections=0;
  const fetch=vi.spyOn(globalThis,"fetch").mockImplementation(async url=>{
    if(String(url).endsWith("local-session")) return Response.json({status:"active",csrf_token:++sessions===1?'old-csrf':'fresh-csrf'});
    return ++projections===1 ? Response.json({detail:{code:"graph_auth_required"}},{status:401}) : Response.json(managedPacket('fresh'));
  });
  const wrapper=({children}:{children:ReactNode})=>createElement(SelectedWorldProvider,{locationSnapshot:window.location.href},createElement(WorldGraphLensProvider,{planCampaignId:"elderwyld"},createElement(WorldGraphLensProjectionProvider,{defaultCampaignId:"elderwyld"},children)));
  const view=renderHook(()=>{useWorldGraphLensProjectionDemand(true);return useWorldGraphLensProjection()},{wrapper});
  await waitFor(()=>expect(view.result.current.projectionState).toBe('ready'));
  expect(view.result.current.projection?.snapshot.revisionId).toBe('fresh');expect(sessions).toBe(2);expect(projections).toBe(2);
  expect(fetch.mock.calls.filter(([url])=>String(url).endsWith('managed-projection'))).toHaveLength(2);
 });
 it.each(['rotation','release'] as const)("rejects late projection JSON body after %s with the real API transport",async transition=>{
  api.setNativeGraphAccessToken('body-old');window.history.replaceState({},"","/?world=elderwyld");
  vi.spyOn(api,"listWorldContainers").mockResolvedValue({schema_version:"dmb_world_container_registry_v1",records:[{schema_version:"dmb_world_container_record_v1",world_id:"elderwyld",name:"World",source_root_relpath:"corpus/world",created_at:"2026-01-01"}]} as never);
  vi.spyOn(api,"getSourceBundle").mockResolvedValue({schema:"dmb_ingestion_source_bundle_v1",campaigns:{}} as never);
  let body!:ReadableStreamDefaultController<Uint8Array>;let projections=0;
  const stream=new ReadableStream<Uint8Array>({start(controller){body=controller}});
  const fetch=vi.spyOn(globalThis,'fetch').mockImplementation(async()=>++projections===1 ? new Response(stream,{headers:{'Content-Type':'application/json'}}) : Response.json(managedPacket('current')));
  const wrapper=({children}:{children:ReactNode})=>createElement(SelectedWorldProvider,{locationSnapshot:window.location.href},createElement(WorldGraphLensProvider,{planCampaignId:"elderwyld"},createElement(WorldGraphLensProjectionProvider,{defaultCampaignId:"elderwyld"},children)));
  const view=renderHook(({enabled})=>{useWorldGraphLensProjectionDemand(enabled);return useWorldGraphLensProjection()},{wrapper,initialProps:{enabled:true}});
  await waitFor(()=>expect(fetch).toHaveBeenCalledTimes(1));await act(async()=>{});
  if(transition==='rotation'){
    act(()=>api.setNativeGraphAccessToken('body-current'));
    await waitFor(()=>expect(view.result.current.projectionState).toBe('ready'));
  }else view.rerender({enabled:false});
  await act(async()=>{body.enqueue(new TextEncoder().encode(JSON.stringify(managedPacket('old'))));body.close()});
  if(transition==='rotation')expect(view.result.current.projection?.snapshot.revisionId).toBe('current');
  else expect(view.result.current).toMatchObject({projectionState:'idle',projection:null});
 });
 it.each([historyPath,"/api/live/world-session-evidence?world_id=elderwyld","/api/live/graph-preview/extraction-runs/run-a/candidate-projection?managed_world_id=elderwyld","/api/live/media/images/asset-a/metadata","/api/live/play-runs?campaign_id=longmont-c2","/api/live/play-active-run","/api/live/world-play-runs/v2?world_id=elderwyld","/api/live/world-play-runs/v2/active?world_id=elderwyld"])("shares pending %s with independently readable bodies, then refreshes",async path=>{
  api.setNativeGraphAccessToken("test-bearer");const gate=deferred<Response>();const fetch=vi.spyOn(globalThis,"fetch").mockReturnValue(gate.promise);
  const reads=[api.authenticatedApiFetch(path),api.authenticatedApiFetch(path)];await waitFor(()=>expect(fetch).toHaveBeenCalledTimes(1));gate.resolve(Response.json({version:1}));
  const responses=await Promise.all(reads);expect(await Promise.all(responses.map(r=>r.response.json()))).toEqual([{version:1},{version:1}]);
  fetch.mockResolvedValueOnce(Response.json({version:2}));expect(await(await api.authenticatedApiFetch(path)).response.json()).toEqual({version:2});expect(fetch).toHaveBeenCalledTimes(2);
 });
 it("isolates World Play inventory reads by World and starts a fresh read after a mutation",async()=>{
  api.setNativeGraphAccessToken("play-inventory-scope");
  const reads=[deferred<Response>(),deferred<Response>(),deferred<Response>()];let readCount=0;
  const fetch=vi.spyOn(globalThis,"fetch").mockImplementation((url,init)=>{
   if(init?.method==="PUT")return Promise.resolve(Response.json({updated:true}));
   return reads[readCount++].promise;
  });
  const elderwyld="/api/live/world-play-runs/v2?world_id=elderwyld";
  const anotherWorld="/api/live/world-play-runs/v2?world_id=another-world";
  const firstController=new AbortController();
  const first=api.authenticatedApiFetch(elderwyld,{signal:firstController.signal}).then(() => "accepted",error=>error.name);
  const same=api.authenticatedApiFetch(elderwyld);
  const other=api.authenticatedApiFetch(anotherWorld);
  await waitFor(()=>expect(fetch).toHaveBeenCalledTimes(2));
  expect(fetch.mock.calls.map(([url])=>String(url))).toEqual([elderwyld,anotherWorld]);
  firstController.abort();
  expect(await first).toBe("AbortError");
  expect(fetch.mock.calls[0][1]?.signal?.aborted).toBe(false);
  const mutation=api.authenticatedApiFetch("/api/live/world-play-runs/v2/run-a/progress?world_id=elderwyld",{method:"PUT",body:"{}"});
  await mutation;
  const refreshed=api.authenticatedApiFetch(elderwyld);
  await waitFor(()=>expect(fetch).toHaveBeenCalledTimes(4));
  expect(fetch.mock.calls.filter(([url,init])=>String(url)===elderwyld&&init?.method!=="PUT")).toHaveLength(2);
  reads[0].resolve(Response.json({version:"before"}));
  reads[1].resolve(Response.json({version:"other-world"}));
  reads[2].resolve(Response.json({version:"after"}));
  const bodies=await Promise.all([same,other,refreshed].map(async request=>(await request).response.json()));
  expect(bodies).toEqual([{version:"before"},{version:"other-world"},{version:"after"}]);
 });
 it.each(["/api/live/agent/worlds/elderwyld/conversation/turns/turn-1/context-trace","/api/live/agent/worlds/elderwyld/conversation/turns/turn-1/context-trace/trace-1/prompt/attempt-1"])("shares exact pending trace evidence request %s",async path=>{
  api.setNativeGraphAccessToken("trace-evidence");const gate=deferred<Response>();const fetch=vi.spyOn(globalThis,"fetch").mockReturnValue(gate.promise);
  const reads=[api.authenticatedApiFetch(path),api.authenticatedApiFetch(path)];await waitFor(()=>expect(fetch).toHaveBeenCalledTimes(1));gate.resolve(Response.json({version:1}));
  const responses=await Promise.all(reads);expect(await Promise.all(responses.map(r=>r.response.json()))).toEqual([{version:1},{version:1}]);
  fetch.mockResolvedValueOnce(Response.json({version:2}));expect(await(await api.authenticatedApiFetch(path)).response.json()).toEqual({version:2});expect(fetch).toHaveBeenCalledTimes(2);
 });
 it("keeps trace evidence isolated by World, turn, trace and provider attempt",async()=>{
  api.setNativeGraphAccessToken("trace-isolation");const gate=deferred<Response>();const fetch=vi.spyOn(globalThis,"fetch").mockReturnValue(gate.promise);
  const paths=[
   "/api/live/agent/worlds/elderwyld/conversation/turns/turn-1/context-trace",
   "/api/live/agent/worlds/elderwyld/conversation/turns/turn-1/context-trace",
   "/api/live/agent/worlds/other-world/conversation/turns/turn-1/context-trace",
   "/api/live/agent/worlds/elderwyld/conversation/turns/turn-2/context-trace",
   "/api/live/agent/worlds/elderwyld/conversation/turns/turn-1/context-trace/trace-2/prompt/attempt-1",
   "/api/live/agent/worlds/elderwyld/conversation/turns/turn-1/context-trace/trace-2/prompt/attempt-2",
  ];
  const reads=paths.map(path=>api.authenticatedApiFetch(path));await waitFor(()=>expect(fetch).toHaveBeenCalledTimes(5));
  expect(fetch.mock.calls.map(([url])=>String(url)).sort()).toEqual([...new Set(paths)].sort());
  gate.resolve(Response.json({version:1}));await Promise.all(reads);
 });
 it("shares equivalent option/header order while preserving distinct header values",async()=>{
  api.setNativeGraphAccessToken("header-test");const gate=deferred<Response>();const fetch=vi.spyOn(globalThis,"fetch").mockReturnValue(gate.promise);
  const reads=[api.authenticatedApiFetch(historyPath,{headers:{Accept:"application/json"},method:"GET"}),api.authenticatedApiFetch(historyPath,{method:"GET",headers:new Headers({accept:"application/json"})}),api.authenticatedApiFetch(historyPath,{headers:{Accept:"text/plain"}})];
  await waitFor(()=>expect(fetch).toHaveBeenCalledTimes(2));gate.resolve(Response.json({}));await Promise.all(reads);
 });
 it("shares equivalent managed requests with omitted versus explicit null defaults",async()=>{
  api.setNativeGraphAccessToken("managed-defaults");const gate=deferred<Response>();const fetch=vi.spyOn(globalThis,"fetch").mockReturnValue(gate.promise);
  const plain={schema:"dmb_managed_world_graph_projection_request_v1" as const,managedWorldId:"elderwyld"};
  const reads=[api.postManagedWorldGraphProjection(plain),api.postManagedWorldGraphProjection({queryText:null,revisionPin:null,...plain})];
  await waitFor(()=>expect(fetch).toHaveBeenCalledTimes(1));gate.resolve(Response.json({fixture:true}));await Promise.all(reads);
 });
 it("preserves explicit empty queries, exact pins and unexpected fields for server rejection",async()=>{
  api.setNativeGraphAccessToken("managed-fields");const gate=deferred<Response>();const fetch=vi.spyOn(globalThis,"fetch").mockReturnValue(gate.promise);
  const plain={schema:"dmb_managed_world_graph_projection_request_v1" as const,managedWorldId:"elderwyld"};
  const reads=[api.postManagedWorldGraphProjection(plain),api.postManagedWorldGraphProjection({...plain,queryText:""}),api.postManagedWorldGraphProjection({...plain,revisionPin:"pin-1"}),api.postManagedWorldGraphProjection({...plain,managedWorldId:"other"}),api.postManagedWorldGraphProjection({...plain,unexpected:"reject-this"} as never).catch(error=>error.status)];
  await waitFor(()=>expect(fetch).toHaveBeenCalledTimes(5));const bodies=fetch.mock.calls.map(([,init])=>JSON.parse(String(init?.body)));
  expect(bodies.some(body=>body.queryText==="")).toBe(true);expect(bodies.some(body=>body.revisionPin==="pin-1")).toBe(true);expect(bodies.some(body=>body.unexpected==="reject-this")).toBe(true);
  gate.resolve(Response.json({detail:"Strict schema rejection"},{status:422}));expect((await Promise.allSettled(reads)).filter(result=>result.status==="rejected")).toHaveLength(4);
 });
 it("isolates World, page, options and projection query/revision",async()=>{
  api.setNativeGraphAccessToken("test-bearer");const gate=deferred<Response>();const fetch=vi.spyOn(globalThis,"fetch").mockReturnValue(gate.promise);
  const reads=[historyPath,historyPath.replace("elderwyld","other"),historyPath+"&before_sequence=10"].map(path=>api.authenticatedApiFetch(path));reads.push(api.authenticatedApiFetch(historyPath,{cache:"no-store"}));
  for(const body of [{worldId:"w",queryText:"a",revisionPin:"1"},{worldId:"w",queryText:"b",revisionPin:"1"},{worldId:"w",queryText:"a",revisionPin:"2"}])reads.push(api.authenticatedApiFetch("/api/live/world-graph/managed-projection",{method:"POST",body:JSON.stringify(body)}));
  await waitFor(()=>expect(fetch).toHaveBeenCalledTimes(7));gate.resolve(Response.json({}));await Promise.all(reads);
 });
 it("does not share a refresh across a command or coalesce command calls",async()=>{
  api.setNativeGraphAccessToken("test-bearer");const gate=deferred<Response>();const fetch=vi.spyOn(globalThis,"fetch").mockReturnValue(gate.promise);
  const first=api.authenticatedApiFetch(historyPath);const command={method:"POST",body:JSON.stringify({turn_id:"one"})};
  const writes=[api.authenticatedApiFetch("/api/live/agent/turn",command),api.authenticatedApiFetch("/api/live/agent/turn",command)];const after=api.authenticatedApiFetch(historyPath);
  await waitFor(()=>expect(fetch).toHaveBeenCalledTimes(4));gate.resolve(Response.json({}));await Promise.all([first,after,...writes]);
 });
 it.each(["success","failure","uncertain"] as const)("refreshes after a %s write without reusing a read begun during the write",async outcome=>{
  api.setNativeGraphAccessToken("settlement-test");const command=deferred<Response>();const during=deferred<Response>();
  const fetch=vi.spyOn(globalThis,"fetch").mockImplementation((url)=>String(url).endsWith("/turn")?command.promise:during.promise);
  const write=api.authenticatedApiFetch("/api/live/agent/turn",{method:"POST",body:"{}"}).catch(error=>error);
  const old=api.authenticatedApiFetch(historyPath);await waitFor(()=>expect(fetch).toHaveBeenCalledTimes(2));
  if(outcome==="uncertain")command.reject(new TypeError("Unknown dispatch outcome"));else command.resolve(Response.json({},{status:outcome==="success"?200:503}));
  await write;fetch.mockResolvedValueOnce(Response.json({version:2}));const refreshed=api.authenticatedApiFetch(historyPath);
  expect(await(await refreshed).response.json()).toEqual({version:2});expect(fetch.mock.calls.filter(([url])=>String(url)===historyPath)).toHaveLength(2);
  during.resolve(Response.json({version:1}));await old;
 });
 it("invalidates independently when overlapping writes settle",async()=>{
  api.setNativeGraphAccessToken("overlap-test");const a=deferred<Response>(),b=deferred<Response>(),during=deferred<Response>();
  const fetch=vi.spyOn(globalThis,"fetch").mockImplementation((url,init)=>String(url).endsWith("/turn")?(init?.body==="a"?a.promise:b.promise):during.promise);
  const first=api.authenticatedApiFetch("/api/live/agent/turn",{method:"POST",body:"a"});const second=api.authenticatedApiFetch("/api/live/agent/turn",{method:"POST",body:"b"});
  a.resolve(Response.json({}));await first;const old=api.authenticatedApiFetch(historyPath);await waitFor(()=>expect(fetch.mock.calls.filter(([url])=>String(url)===historyPath)).toHaveLength(1));
  b.resolve(Response.json({}));await second;fetch.mockResolvedValueOnce(Response.json({version:2}));expect(await(await api.authenticatedApiFetch(historyPath)).response.json()).toEqual({version:2});
  expect(fetch.mock.calls.filter(([url])=>String(url)===historyPath)).toHaveLength(2);expect(fetch.mock.calls.filter(([url])=>String(url).endsWith("/turn"))).toHaveLength(2);during.resolve(Response.json({}));await old;
 });
 it("keeps graph reads in one wave across passive recap status inspections without sharing the inspections",async()=>{
  api.setNativeGraphAccessToken("inspection-test");const gate=deferred<Response>();const fetch=vi.spyOn(globalThis,"fetch").mockReturnValue(gate.promise);
  const request={schema:"dmb_managed_world_graph_projection_request_v1" as const,managedWorldId:"elderwyld"};
  const first=api.postManagedWorldGraphProjection(request);const status={method:"POST",body:JSON.stringify({operation:"inspect_status",campaign_id:"longmont-c2",session:29,title:"Saved recap"})};
  const inspections=[api.authenticatedApiFetch("/api/live/recap-ingest",status),api.authenticatedApiFetch("/api/live/recap-ingest",status)];const second=api.postManagedWorldGraphProjection(request);
  await waitFor(()=>expect(fetch.mock.calls.filter(([url])=>String(url).endsWith("managed-projection"))).toHaveLength(1));
  expect(fetch.mock.calls.filter(([url])=>String(url).endsWith("recap-ingest"))).toHaveLength(2);gate.resolve(Response.json({}));await Promise.all([first,second,...inspections]);
 });
 it("preserves a pending graph read across inspection settlement",async()=>{
  api.setNativeGraphAccessToken("inspection-settlement");const graph=deferred<Response>();const fetch=vi.spyOn(globalThis,"fetch").mockImplementation(url=>String(url).endsWith("recap-ingest")?Promise.resolve(Response.json({})):graph.promise);
  const request={schema:"dmb_managed_world_graph_projection_request_v1" as const,managedWorldId:"elderwyld"};const first=api.postManagedWorldGraphProjection(request);
  await api.authenticatedApiFetch("/api/live/recap-ingest",{method:"POST",body:JSON.stringify({operation:"inspect_status",campaign_id:"longmont-c2",session:29})});
  const second=api.postManagedWorldGraphProjection(request);await waitFor(()=>expect(fetch.mock.calls.filter(([url])=>String(url).endsWith("managed-projection"))).toHaveLength(1));graph.resolve(Response.json({}));await Promise.all([first,second]);
 });
 it("keeps ordinary status inspection independent of Graph authentication",async()=>{
  api.setNativeGraphAccessToken(null);const fetch=vi.spyOn(globalThis,"fetch").mockResolvedValue(Response.json({status:"saved"}));
  const result=await api.authenticatedApiFetch("/api/live/recap-ingest",{method:"POST",body:JSON.stringify({operation:"inspect_status",campaign_id:"longmont-c2",session:29})});expect(await result.response.json()).toEqual({status:"saved"});expect(fetch).toHaveBeenCalledTimes(1);expect(String(fetch.mock.calls[0][0])).toBe("/api/live/recap-ingest");expect(new Headers(fetch.mock.calls[0][1]?.headers).has("Authorization")).toBe(false);
 });
 it.each([{operation:"generate_recap_memory"},{operation:"reconcile_normalized_recap"},{operation:"build_graph_preview_bundle"},{operation:"materialize_preview_supergraph"},{operation:"INSPECT_STATUS"},{operation:"inspect_status",force_recap:true},{operation:"inspect_status",session:0}])("retains a fresh wave for command/unknown inspection shape %j",async body=>{
  api.setNativeGraphAccessToken("inspection-command-test");const gate=deferred<Response>();const fetch=vi.spyOn(globalThis,"fetch").mockReturnValue(gate.promise);const request={schema:"dmb_managed_world_graph_projection_request_v1" as const,managedWorldId:"elderwyld"};
  const first=api.postManagedWorldGraphProjection(request);const command=api.authenticatedApiFetch("/api/live/recap-ingest",{method:"POST",body:JSON.stringify({campaign_id:"longmont-c2",session:29,...body})});const second=api.postManagedWorldGraphProjection(request);
  await waitFor(()=>expect(fetch.mock.calls.filter(([url])=>String(url).endsWith("managed-projection"))).toHaveLength(2));gate.resolve(Response.json({}));await Promise.all([first,command,second]);
 });
 it("fences old bearer responses and makes native reads fresh after rotation",async()=>{
  api.setNativeGraphAccessToken("old-bearer");const gate=deferred<Response>();const fetch=vi.spyOn(globalThis,"fetch").mockReturnValue(gate.promise);
  const old=api.authenticatedApiFetch(historyPath).then(()=>"accepted",error=>error.code);await waitFor(()=>expect(fetch).toHaveBeenCalledTimes(1));api.setNativeGraphAccessToken("new-bearer");
  const fresh=api.authenticatedApiFetch(historyPath);await waitFor(()=>expect(fetch).toHaveBeenCalledTimes(2));gate.resolve(Response.json({}));expect(await old).toBe("local_graph_session_changed");await fresh;
  fetch.mockResolvedValueOnce(Response.json({revision:"first"}));const request={worldId:"native",campaignId:"",focus:{kind:"none",sessionId:null},admissibility:"gm"} as never;
  expect(await api.postWorldGraphProjection(request)).toEqual({revision:"first"});api.setNativeGraphAccessToken("third-bearer");fetch.mockResolvedValueOnce(Response.json({revision:"second"}));expect(await api.postWorldGraphProjection(request)).toEqual({revision:"second"});
 });
 it("fences credential rotation while a successful evidence body is streaming",async()=>{
  api.setNativeGraphAccessToken("before-body");let stream!:ReadableStreamDefaultController<Uint8Array>;
  vi.spyOn(globalThis,"fetch").mockResolvedValue(new Response(new ReadableStream<Uint8Array>({start(controller){stream=controller;}})));
  const {response}=await api.authenticatedApiFetch("/api/live/world-session-evidence?world_id=elderwyld");
  const body=response.json().then(()=>"accepted",error=>error.code);api.setNativeGraphAccessToken("after-body");
  stream.enqueue(new TextEncoder().encode('{"sources":[]}'));stream.close();expect(await body).toBe("local_graph_session_changed");
 });
 it("does not dispatch an old caller using a newly rotated bearer",async()=>{
  api.setNativeGraphAccessToken("before-dispatch");const fetch=vi.spyOn(globalThis,"fetch").mockResolvedValue(Response.json({}));
  const old=api.authenticatedApiFetch(historyPath).catch(error=>error.code);api.setNativeGraphAccessToken("after-dispatch");
  expect(await old).toBe("local_graph_session_changed");expect(fetch).not.toHaveBeenCalled();
 });
 it("keeps transport alive for the other owner when one history subscriber cancels",async()=>{
  api.setNativeGraphAccessToken("cancel-test");const gate=deferred<Response>();const fetch=vi.spyOn(globalThis,"fetch").mockReturnValue(gate.promise);const firstController=new AbortController();
  const first=api.authenticatedApiFetch(historyPath,{signal:firstController.signal}).catch(error=>error.name);const second=api.authenticatedApiFetch(historyPath);
  await waitFor(()=>expect(fetch).toHaveBeenCalledTimes(1));firstController.abort();expect(await first).toBe("AbortError");expect(fetch.mock.calls[0][1]?.signal?.aborted).toBe(false);
  gate.resolve(Response.json({version:1}));expect(await(await second).response.json()).toEqual({version:1});
 });
 it("preserves shared failure and makes explicit retry fresh",async()=>{
  api.setNativeGraphAccessToken("test-bearer");const gate=deferred<Response>();const fetch=vi.spyOn(globalThis,"fetch").mockReturnValue(gate.promise);
  const reads=[api.getWorldAgentConversationHistory("elderwyld"),api.getWorldAgentConversationHistory("elderwyld")];await waitFor(()=>expect(fetch).toHaveBeenCalledTimes(1));gate.resolve(Response.json({detail:{code:"downstream_failed",message:"Read unavailable"}},{status:503}));
  const results=await Promise.allSettled(reads);expect(results.every(r=>r.status==="rejected"&&r.reason.status===503&&r.reason.code==="downstream_failed")).toBe(true);
  fetch.mockResolvedValueOnce(Response.json({version:2}));expect(await api.getWorldAgentConversationHistory("elderwyld")).toEqual({version:2});expect(fetch).toHaveBeenCalledTimes(2);
 });
});
