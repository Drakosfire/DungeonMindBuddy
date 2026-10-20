import { createElement, type ReactNode } from "react";
import { act, cleanup, renderHook, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import * as api from "./liveApi";
import { SelectedWorldProvider } from "../selectedWorld/SelectedWorldContext";
import { WorldGraphLensProvider, WorldGraphLensProjectionProvider, useWorldGraphLensProjection } from "../graphLens";
function deferred<T>() { let resolve!: (value:T)=>void; const promise=new Promise<T>(r=>{resolve=r;}); return {promise,resolve}; }
afterEach(()=>{cleanup();vi.restoreAllMocks();api.setNativeGraphAccessToken(null);});
const historyPath="/api/live/agent/worlds/elderwyld/conversation?limit=40";
describe("protected read acquisition",()=>{
 it("does not repeat mounted graph acquisition on its own cold session bootstrap",async()=>{
  window.history.replaceState({},"","/?world=elderwyld");
  vi.spyOn(api,"listWorldContainers").mockResolvedValue({schema_version:"dmb_world_container_registry_v1",records:[{schema_version:"dmb_world_container_record_v1",world_id:"elderwyld",name:"World",source_root_relpath:"corpus/world",created_at:"2026-01-01"}]} as never);
  vi.spyOn(api,"getSourceBundle").mockResolvedValue({schema:"dmb_ingestion_source_bundle_v1",campaigns:{}} as never);
  const gate=deferred<Response>();
  const fetch=vi.spyOn(globalThis,"fetch").mockImplementation(async url=>String(url).endsWith("local-session")?Response.json({status:"active",csrf_token:"test-csrf"}):gate.promise);
  const wrapper=({children}:{children:ReactNode})=>createElement(SelectedWorldProvider,{locationSnapshot:window.location.href},createElement(WorldGraphLensProvider,{planCampaignId:"elderwyld"},createElement(WorldGraphLensProjectionProvider,{defaultCampaignId:"elderwyld"},children)));
  const {result}=renderHook(()=>useWorldGraphLensProjection(),{wrapper});
  await waitFor(()=>expect(fetch.mock.calls.some(([url])=>String(url).endsWith("managed-projection"))).toBe(true));
  await act(async()=>{await new Promise(r=>setTimeout(r,20));});
  expect(fetch.mock.calls.filter(([url])=>String(url).endsWith("managed-projection"))).toHaveLength(1);
  gate.resolve(Response.json({schema:"dmb_managed_world_graph_projection_v1",managedWorldId:"elderwyld",nativeWorldId:"native-world",bindingVersion:1,projection:{schema:"dmb_world_graph_projection_v1",snapshot:{worldId:"native-world",campaignId:"",revisionId:"rev-1",headRevisionId:"rev-1",isHead:true,focus:{kind:"none",sessionId:null},admissibility:"gm",scopeMode:"world"},summary:{nodeCount:0,relationshipCount:0,attributeCount:0,evidenceCount:0,sourceArtifactCount:0,projectionTruncated:false},nodes:[],relationships:[],attributes:[],evidence:[],sourceArtifacts:[],diagnostics:[]}}));
  await waitFor(()=>expect(result.current.projectionState).toBe("ready"));
 });
 it.each([historyPath,"/api/live/world-session-evidence?world_id=elderwyld","/api/live/graph-preview/extraction-runs/run-a/candidate-projection?managed_world_id=elderwyld","/api/live/media/images/asset-a/metadata"])("shares pending %s with independently readable bodies, then refreshes",async path=>{
  api.setNativeGraphAccessToken("test-bearer");const gate=deferred<Response>();const fetch=vi.spyOn(globalThis,"fetch").mockReturnValue(gate.promise);
  const reads=[api.authenticatedApiFetch(path),api.authenticatedApiFetch(path)];await waitFor(()=>expect(fetch).toHaveBeenCalledTimes(1));gate.resolve(Response.json({version:1}));
  const responses=await Promise.all(reads);expect(await Promise.all(responses.map(r=>r.response.json()))).toEqual([{version:1},{version:1}]);
  fetch.mockResolvedValueOnce(Response.json({version:2}));expect(await(await api.authenticatedApiFetch(path)).response.json()).toEqual({version:2});expect(fetch).toHaveBeenCalledTimes(2);
 });
 it("shares equivalent option/header order while preserving distinct header values",async()=>{
  api.setNativeGraphAccessToken("header-test");const gate=deferred<Response>();const fetch=vi.spyOn(globalThis,"fetch").mockReturnValue(gate.promise);
  const reads=[api.authenticatedApiFetch(historyPath,{headers:{Accept:"application/json"},method:"GET"}),api.authenticatedApiFetch(historyPath,{method:"GET",headers:new Headers({accept:"application/json"})}),api.authenticatedApiFetch(historyPath,{headers:{Accept:"text/plain"}})];
  await waitFor(()=>expect(fetch).toHaveBeenCalledTimes(2));gate.resolve(Response.json({}));await Promise.all(reads);
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
 it("fences old bearer responses and native warm bytes after rotation",async()=>{
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
