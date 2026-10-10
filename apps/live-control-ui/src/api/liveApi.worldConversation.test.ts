import { afterEach, describe, expect, it, vi } from "vitest";

import {
  getWorldAgentConversationHistory,
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
      primary_work: { kind: "run", object_id: "run-one", expected_revision: 3 },
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
