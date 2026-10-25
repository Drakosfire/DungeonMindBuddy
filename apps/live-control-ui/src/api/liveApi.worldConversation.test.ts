import { afterEach, describe, expect, it, vi } from "vitest";

import {
  getWorldAgentConversationHistory,
  getExtractionRun,
  getPlanView,
  getWorldAgentTurnContextTrace,
  getWorldAgentHistoricalSourcePassage,
  getWorldAgentNewConversationStatus,
  postWorldAgentNewConversation,
  postWorldPlayAgentTurn,
  setNativeGraphAccessToken,
} from "./liveApi";
import type { WorldPlayAgentTurnRequestV1 } from "./types";

function jsonResponse(value: unknown): Response {
  return new Response(JSON.stringify(value), {
    status: 200,
    headers: { "Content-Type": "application/json" },
  });
}

afterEach(() => {
  vi.restoreAllMocks();
  vi.unstubAllEnvs();
  setNativeGraphAccessToken(null);
});

describe("World Agent conversation transport", () => {
  it("sends the exact selected World Graph Play request and preserves the native Graph receipt", async () => {
    setNativeGraphAccessToken("test-token");
    const request: WorldPlayAgentTurnRequestV1 = {
      schema: "dmb_agent_turn_request_v1", client_thread_id: "thread-one", turn_id: "turn-one",
      surface: { surface_id: "play", instance_id: "play-one" },
      owner_scope: { kind: "world", world_id: "managed-world" },
      primary_work: { kind: "run", object_id: "run-one", expected_revision: 3, play_content_basis: { edition_revision: 2, edition_revision_id: "edition-two", content_sha256: "a".repeat(64) } },
      play_target: { beat_id: "beat:approach", scene_id: "scene:gate", marker_grammar_version: "v2" },
      client_work_state: "saved_clean",
      graph_request: { mode: "world", world_id: "managed-world", campaign_id: null,
        revision_pin: null, focus: { kind: "none", session_id: null, campaign_id: null } },
      graph_selection: null, message: "What can I see?",
    };
    const response = { schema: "dmb_agent_turn_response_v1", client_thread_id: request.client_thread_id,
      turn_id: request.turn_id, owner_scope: { owner_id: "managed-world" },
      graph: { status: "ready", world_id: "native-world", revision_id: "native-revision", scope_mode: "world" } };
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockResolvedValue(jsonResponse(response));

    await expect(postWorldPlayAgentTurn(request)).resolves.toEqual(response);
    expect(String(fetchSpy.mock.calls[0]?.[0])).toBe("/api/live/agent/turn");
    expect(fetchSpy.mock.calls[0]?.[1]?.method).toBe("POST");
    expect(fetchSpy.mock.calls[0]?.[1]?.body).toBe(JSON.stringify(request));
  });

  it("reads the exact bounded World history route and preserves the accepted response", async () => {
    setNativeGraphAccessToken("test-token");
    const response = {
      schema: "dmb_agent_conversation_history_v1",
      world_id: "world/a",
      conversation_state: "active",
      conversation_id: "conversation-1",
      active_conversation_id: "conversation-1",
      pointer_revision: 12,
      turns: [],
      next_before_sequence: 50,
    };
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockResolvedValue(jsonResponse(response));

    await expect(getWorldAgentConversationHistory("world/a", {
      limit: 50,
      beforeSequence: 51,
    })).resolves.toEqual(response);

    expect(String(fetchSpy.mock.calls[0]?.[0])).toBe(
      "/api/live/agent/worlds/world%2Fa/conversation?limit=50&before_sequence=51",
    );
    expect(fetchSpy.mock.calls[0]?.[1]?.method).toBeUndefined();
    expect(fetchSpy.mock.calls[0]?.[1]?.body).toBeUndefined();
  });

  it.each(["history", "trace"])("passes cancellation only as transport control for the exact %s read", async kind => {
    setNativeGraphAccessToken("test-token");
    const controller = new AbortController();
    let owned: AbortSignal | null | undefined;
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockImplementation((_url, init) => {
      owned = init?.signal;
      return new Promise((_resolve, reject) => owned?.addEventListener("abort", () => reject(owned?.reason), {once:true}));
    });
    const read = kind === "history"
      ? getWorldAgentConversationHistory("world/a", {limit:50,includeTurnCorrelation:true,signal:controller.signal})
      : getWorldAgentTurnContextTrace("world/a", "turn/b", controller.signal);
    await vi.waitFor(() => expect(fetchSpy).toHaveBeenCalledTimes(1));
    expect(String(fetchSpy.mock.calls[0][0])).toBe(kind === "history"
      ? "/api/live/agent/worlds/world%2Fa/conversation?limit=50&include_turn_correlation=true"
      : "/api/live/agent/worlds/world%2Fa/conversation/turns/turn%2Fb/context-trace");
    const rejected = expect(read).rejects.toMatchObject({name:"AbortError"});
    controller.abort(); await rejected; expect(owned?.aborted).toBe(true);
  });

  it("posts the exact New Conversation CAS envelope", async () => {
    setNativeGraphAccessToken("test-token");
    const request = {
      schema: "dmb_agent_new_conversation_v1" as const,
      command_id: "00000000-0000-4000-8000-000000000001",
      expected_pointer_revision: 12,
      expected_active_conversation_id: "conversation-1",
    };
    const response = {
      schema: "dmb_agent_new_conversation_response_v1",
      world_id: "world-1",
      conversation_id: "conversation-2",
      active_conversation_id: "conversation-2",
      pointer_revision: 13,
    };
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockResolvedValue(jsonResponse(response));

    await expect(postWorldAgentNewConversation("world-1", request)).resolves.toEqual(response);

    expect(String(fetchSpy.mock.calls[0]?.[0])).toBe(
      "/api/live/agent/worlds/world-1/conversation/new",
    );
    expect(fetchSpy.mock.calls[0]?.[1]?.method).toBe("POST");
    expect(JSON.parse(String(fetchSpy.mock.calls[0]?.[1]?.body))).toEqual(request);
  });
});


it("checks the exact saved reset binding with GET only", async () => {
  setNativeGraphAccessToken("test-token");
  const fetchSpy = vi.spyOn(globalThis, "fetch").mockResolvedValue(jsonResponse({ status: "absent" }));
  await getWorldAgentNewConversationStatus("world/a", { schema: "dmb_agent_new_conversation_v1", command_id: "command-id", expected_pointer_revision: 0, expected_active_conversation_id: null });
  expect(String(fetchSpy.mock.calls[0]?.[0])).toBe("/api/live/agent/worlds/world%2Fa/conversation/commands/command-id?expected_pointer_revision=0&expected_active_conversation_id=null");
  expect(fetchSpy.mock.calls[0]?.[1]?.method).toBeUndefined();
  expect(fetchSpy.mock.calls[0]?.[1]?.body).toBeUndefined();
  expect(new Headers(fetchSpy.mock.calls[0]?.[1]?.headers).get("Authorization")).toBe("Bearer test-token");
  expect(fetchSpy.mock.calls[0]?.[1]?.redirect).toBe("error");
  expect(fetchSpy.mock.calls[0]?.[1]?.credentials).toBe("same-origin");
});


const savedStatusCommand = { schema: "dmb_agent_new_conversation_v1" as const,
  command_id: "00000000-0000-0000-0000-000000000001", expected_pointer_revision: 7,
  expected_active_conversation_id: "00000000-0000-0000-0000-000000000002" };

it("bootstraps and renews the protected status GET without reset/provider POST", async () => {
  vi.stubEnv("VITE_LIVE_API_BASE_URL", ""); vi.resetModules();
  const api = await import("./liveApi");
  let checks = 0; let boots = 0; let lookups = 0;
  const fetchSpy = vi.spyOn(globalThis, "fetch").mockImplementation(async (url, init) => {
    if (String(url) === "/api/live/agent/local-session") {
      if (init?.method === "POST") { boots++; return Response.json({ status: "active", csrf_token: `csrf-${boots}` }); }
      checks++;
      return new Response(null, { status: 401 });
    }
    expect(String(url)).toContain("/conversation/commands/");
    expect(init?.method).toBeUndefined(); expect(init?.body).toBeUndefined();
    expect(init?.redirect).toBe("error"); expect(init?.credentials).toBe("same-origin");
    expect(new Headers(init?.headers).has("Authorization")).toBe(false);
    lookups++;
    return lookups === 1 ? Response.json({ detail: { code: "graph_auth_required" } }, { status: 401 }) : Response.json({ status: "absent" });
  });
  await expect(api.getWorldAgentNewConversationStatus("world-a", savedStatusCommand)).resolves.toEqual({ status: "absent" });
  expect(lookups).toBe(2); expect(boots).toBe(2); expect(checks).toBe(2);
  expect(fetchSpy.mock.calls.filter(([, init]) => init?.method === "POST").every(([url]) => String(url) === "/api/live/agent/local-session")).toBe(true);
});

it("blocks the receipt status GET at a non-loopback destination before fetch", async () => {
  vi.stubEnv("VITE_LIVE_API_BASE_URL", "https://api.example.invalid"); vi.resetModules();
  const api = await import("./liveApi"); api.setNativeGraphAccessToken("test-token");
  const fetchSpy = vi.spyOn(globalThis, "fetch");
  await expect(api.getWorldAgentNewConversationStatus("world-a", savedStatusCommand)).rejects.toMatchObject({ status: 0, message: expect.stringContaining("loopback") });
  expect(fetchSpy).not.toHaveBeenCalled();
});

it("uses redirect rejection for status GET and never resends a reset after redirect failure", async () => {
  vi.stubEnv("VITE_LIVE_API_BASE_URL", "http://127.0.0.1:8000"); vi.resetModules();
  const api = await import("./liveApi"); api.setNativeGraphAccessToken("test-token");
  const fetchSpy = vi.spyOn(globalThis, "fetch").mockImplementation(async (_url, init) => {
    expect(init?.redirect).toBe("error");
    expect(new Headers(init?.headers).get("Authorization")).toBe("Bearer test-token");
    throw new TypeError("redirect blocked");
  });
  await expect(api.getWorldAgentNewConversationStatus("world-a", savedStatusCommand)).rejects.toThrow();
  expect(fetchSpy).toHaveBeenCalledTimes(1);
});


it("protects resolution POST/record GET and never automatically retries the metadata POST", async () => {
  vi.stubEnv("VITE_LIVE_API_BASE_URL", ""); vi.resetModules(); const api = await import("./liveApi");
  const original = { world_id: "world-a", command_id: savedStatusCommand.command_id, expected_pointer_revision: 0, expected_active_conversation_id: null };
  const request = { schema: "dmb_agent_new_conversation_resolution_request_v1" as const, resolution_operation_id: "00000000-0000-0000-0000-000000000004", original_command: original, expected_current_pointer_revision: 0, expected_current_active_conversation_id: null };
  let businessPosts = 0;
  const fetchSpy = vi.spyOn(globalThis, "fetch").mockImplementation(async (url, init) => {
    if (String(url) === "/api/live/agent/local-session") return init?.method === "POST" ? Response.json({ status: "active", csrf_token: "fresh" }) : Response.json({ status: "active", csrf_token: "old" });
    expect(init?.redirect).toBe("error"); expect(init?.credentials).toBe("same-origin");
    if (init?.method === "POST") { businessPosts++; expect(JSON.parse(String(init.body))).toEqual(request); return Response.json({ detail: { code: "graph_auth_required" } }, { status: 401 }); }
    return Response.json({ status: "absent" });
  });
  await expect(api.postWorldCommandResolution(request)).rejects.toMatchObject({ status: 401 });
  expect(businessPosts).toBe(1);
  await api.getWorldCommandResolution(request);
  expect(fetchSpy.mock.calls.filter(([url, init]) => init?.method === "POST" && String(url).endsWith("/new"))).toHaveLength(0);
  const lookup = fetchSpy.mock.calls.find(([url]) => String(url).includes("/resolutions/"))!;
  expect(String(lookup[0])).toContain("original_active_conversation_id=null"); expect(String(lookup[0])).toContain("current_pointer_revision=0");
});

it("injects bearer for both exact resolution routes and rejects off-loopback destinations", async () => {
  vi.stubEnv("VITE_LIVE_API_BASE_URL", "http://127.0.0.1:8000"); vi.resetModules(); const api = await import("./liveApi"); api.setNativeGraphAccessToken("resolution-token");
  const request = { schema: "dmb_agent_new_conversation_resolution_request_v1" as const, resolution_operation_id: savedStatusCommand.command_id,
    original_command: { world_id: "world-a", command_id: savedStatusCommand.command_id, expected_pointer_revision: 0, expected_active_conversation_id: null }, expected_current_pointer_revision: 0, expected_current_active_conversation_id: null };
  const fetchSpy = vi.spyOn(globalThis, "fetch").mockResolvedValue(Response.json({ status: "absent" }));
  await api.postWorldCommandResolution(request); fetchSpy.mockResolvedValue(Response.json({ status: "absent" })); await api.getWorldCommandResolution(request);
  for (const [, init] of fetchSpy.mock.calls) { expect(new Headers(init?.headers).get("Authorization")).toBe("Bearer resolution-token"); expect(init?.redirect).toBe("error"); }
  vi.stubEnv("VITE_LIVE_API_BASE_URL", "https://api.example.invalid"); vi.resetModules(); const blocked = await import("./liveApi"); blocked.setNativeGraphAccessToken("resolution-token");
  fetchSpy.mockClear(); await expect(blocked.postWorldCommandResolution(request)).rejects.toMatchObject({ status: 0 }); await expect(blocked.getWorldCommandResolution(request)).rejects.toMatchObject({ status: 0 }); expect(fetchSpy).not.toHaveBeenCalled();
});

describe('exact historical passage acquisition',()=>{
  const reference={schema:'dmb_trace_historical_source_ref_v1' as const,world_id:'world/a',turn_id:'turn/b',conversation_id:'conversation',trace_id:'trace',attempt:2,source_read_event_id:'event',source_read_id:'read/a ?&=🦉',content_sha256:'a'.repeat(64)}
  function read(ref=reference,signal?:AbortSignal) {return getWorldAgentHistoricalSourcePassage(ref,signal)}
  it('encodes every exact selector, authenticates, and shares only equivalent pending requests',async()=>{
    setNativeGraphAccessToken('passage-token');let release!:()=>void;const gate=new Promise<void>(r=>{release=r})
    const fetch=vi.spyOn(globalThis,'fetch').mockImplementation(()=>gate.then(()=>Response.json({exact:true})))
    const reads=[read(),read(),read({...reference,source_read_event_id:'other-event'}),read({...reference,source_read_id:'other-read'}),read({...reference,content_sha256:'b'.repeat(64)}),read({...reference,conversation_id:'other-conversation'})]
    await vi.waitFor(()=>expect(fetch).toHaveBeenCalledTimes(5))
    const url=String(fetch.mock.calls[0][0]);expect(url).toMatch(/^\/api\/live\/agent\/worlds\/world%2Fa\/conversation\/turns\/turn%2Fb\/context-trace\/trace\/source-passages\/event\?/)
    const query=new URL(url,'http://localhost').searchParams
    expect(Object.fromEntries(query)).toEqual({conversation_id:'conversation',attempt:'2',source_read_id:reference.source_read_id,content_sha256:reference.content_sha256})
    expect(new Headers(fetch.mock.calls[0][1]?.headers).get('Authorization')).toBe('Bearer passage-token')
    expect(fetch.mock.calls[0][1]?.cache).toBe('no-store');expect(fetch.mock.calls.every(([,init])=>!init?.body&&init?.method!=='POST')).toBe(true)
    release();await Promise.all(reads);await read();expect(fetch).toHaveBeenCalledTimes(6)
  })
  it('keeps a shared read for another subscriber after cancellation',async()=>{
    setNativeGraphAccessToken('passage-cancel');let release!:(value:Response)=>void;const gate=new Promise<Response>(r=>{release=r})
    const fetch=vi.spyOn(globalThis,'fetch').mockReturnValue(gate);const controller=new AbortController()
    const first=read(reference,controller.signal).catch(error=>error.name);const second=read()
    await vi.waitFor(()=>expect(fetch).toHaveBeenCalledTimes(1));controller.abort();expect(await first).toBe('AbortError')
    expect(fetch.mock.calls[0][1]?.signal?.aborted).toBe(false);release(Response.json({exact:true}));expect(await second).toEqual({exact:true})
  })
  it('rejects a body completing after credential rotation',async()=>{
    setNativeGraphAccessToken('passage-before');let stream!:ReadableStreamDefaultController<Uint8Array>
    vi.spyOn(globalThis,'fetch').mockResolvedValue(new Response(new ReadableStream<Uint8Array>({start(c){stream=c}})))
    const pending=read().catch(error=>error.code)
    await vi.waitFor(()=>expect(globalThis.fetch).toHaveBeenCalledTimes(1));setNativeGraphAccessToken('passage-after')
    stream.enqueue(new TextEncoder().encode('{"exact":true}'));stream.close();expect(await pending).toBe('local_graph_session_changed')
  })
})


it.each(["run", "plan"])("passes initial Ingest %s cancellation only as transport control", async kind => {
  const controller = new AbortController();
  const fetch = vi.spyOn(globalThis, "fetch").mockImplementation((_url, init) => new Promise((_resolve,reject) => {
    init?.signal?.addEventListener("abort", () => reject(init.signal?.reason), {once:true});
  }));
  const pending = kind === "run" ? getExtractionRun("run/a",controller.signal) : getPlanView("world/a",controller.signal);
  await vi.waitFor(() => expect(fetch).toHaveBeenCalledTimes(1));
  expect(String(fetch.mock.calls[0][0])).toBe(kind === "run" ? "/api/live/graph-preview/extraction-runs/run%2Fa" : "/api/live/plan-view?world_id=world%2Fa");
  expect(fetch.mock.calls[0][1]?.body).toBeUndefined();
  const failure = expect(pending).rejects.toMatchObject({name:"AbortError"});controller.abort();await failure;
});

it('joins separately versioned retry context to exact Build history IDs',async()=>{
 setNativeGraphAccessToken('test-token');
 const cid='11111111-1111-4111-8111-111111111111',tid='22222222-2222-4222-8222-222222222222';
 const retry={world_id:'world',conversation_id:cid,turn_id:tid,revision:7,root_id:tid,predecessor_id:null,successor_id:null,ordinal:0,eligible:true,reason:'ready'};
 const fetch=vi.spyOn(globalThis,'fetch').mockResolvedValueOnce(jsonResponse({schema:'dmb_agent_conversation_history_v3',world_id:'world',conversation_state:'active',conversation_id:cid,active_conversation_id:cid,pointer_revision:1,next_before_sequence:null,turns:[{turn_id:tid,provenance:{surface_id:'build',primary_work:{kind:'build'}}}]}))
 .mockResolvedValueOnce(jsonResponse({schema:'dmb_turn_retry_context_v1',world_id:'world',conversation_id:cid,turns:[{turn_id:tid,context:retry}]}));
 const result=await getWorldAgentConversationHistory('world',{includeTurnCorrelation:true});
 expect(result.turns[0].retry_context).toEqual(retry);expect(fetch).toHaveBeenCalledTimes(2);
 expect(String(fetch.mock.calls[1][0])).toContain('/conversations/'+cid+'/retry-context?');
});
