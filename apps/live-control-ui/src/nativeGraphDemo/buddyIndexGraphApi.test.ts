import { describe, expect, it, vi } from "vitest";
import { createBuddyIndexGraphApi } from "./buddyIndexGraphApi";
import type { NativeGraph } from "./nativeGraphDemoApi";

const graph: NativeGraph = {
  world_id: "private-space-1",
  revision_id: "revision-1",
  graph_sha256: "sha256:graph-1",
  nodes: [],
  edges: [],
  storage: "postgres",
  limitations: ["Event typing is not available in this native profile."],
  capabilities: { create: true, connect: true, rename: false, delete: false, object_kinds: ["person", "location"] },
};

function jsonResponse(value: unknown, status = 200): Response {
  return new Response(JSON.stringify(value), { status, headers: { "Content-Type": "application/json" } });
}

describe("Buddy index graph API", () => {
  it("bootstraps one same-origin session, then uses the scoped routes and mutation CSRF header", async () => {
    const calls: Array<{ path: string; init?: RequestInit }> = [];
    const fetcher = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const path = String(input);
      calls.push({ path, init });
      if (path.endsWith("/session")) return jsonResponse({ csrf_token: "csrf-private" });
      if (path.endsWith("/graph")) return jsonResponse(graph);
      if (path.endsWith("/prepare")) return jsonResponse({
        status: "prepared", operation_id: "op-1", parent_revision_id: graph.revision_id, review: { summary: "Create Mira." },
      });
      if (path.endsWith("/confirm")) return jsonResponse({ status: "committed", graph });
      return jsonResponse({ status: "not_found", operation_id: "op/one" });
    });
    const api = createBuddyIndexGraphApi({ fetcher });

    await api.readGraph();
    await api.prepare({
      operation_id: "op-1",
      expected_revision_id: graph.revision_id,
      kind: "create_object",
      name: "Mira",
      object_kind: "person",
    });
    await api.confirm("op-1");
    await api.readOperation("op/one");

    expect(calls.map(({ path }) => path)).toEqual([
      "/api/live/index-graph/session",
      "/api/live/index-graph/graph",
      "/api/live/index-graph/prepare",
      "/api/live/index-graph/confirm",
      "/api/live/index-graph/operations/op%2Fone",
    ]);
    expect(calls[0]?.init).toMatchObject({ method: "POST", credentials: "same-origin", cache: "no-store", redirect: "error" });
    expect(new Headers(calls[0]?.init?.headers).has("X-DMB-Index-Graph-CSRF")).toBe(false);
    for (const index of [1, 4]) {
      expect(calls[index]?.init).toMatchObject({ credentials: "same-origin", cache: "no-store", redirect: "error" });
      expect(new Headers(calls[index]?.init?.headers).has("X-DMB-Index-Graph-CSRF")).toBe(false);
    }
    for (const index of [2, 3]) {
      expect(calls[index]?.init?.method).toBe("POST");
      expect(new Headers(calls[index]?.init?.headers).get("X-DMB-Index-Graph-CSRF")).toBe("csrf-private");
      expect(new Headers(calls[index]?.init?.headers).get("Content-Type")).toBe("application/json");
    }
    expect(calls[2]?.init?.body).toBe(JSON.stringify({
      operation_id: "op-1", expected_revision_id: graph.revision_id, kind: "create_object", name: "Mira", object_kind: "person",
    }));
    expect(calls[3]?.init?.body).toBe(JSON.stringify({ operation_id: "op-1" }));
    expect(calls.every(({ path }) => !path.includes("csrf-private"))).toBe(true);
  });

  it("shares concurrent session bootstrap and keeps graph response validation", async () => {
    let resolveSession!: (response: Response) => void;
    const sessionWait = new Promise<Response>((resolve) => { resolveSession = resolve; });
    const fetcher = vi.fn(async (input: RequestInfo | URL) => String(input).endsWith("/session")
      ? sessionWait
      : jsonResponse({ ...graph, capabilities: undefined }));
    const api = createBuddyIndexGraphApi({ fetcher });

    const first = api.readGraph();
    const second = api.readGraph();
    await Promise.resolve();
    expect(fetcher.mock.calls.filter(([path]) => String(path).endsWith("/session"))).toHaveLength(1);
    resolveSession(jsonResponse({ csrf_token: "csrf-private" }));

    await expect(Promise.all([first, second])).rejects.toMatchObject({ code: "invalid_response" });
    expect(fetcher.mock.calls.filter(([path]) => String(path).endsWith("/graph"))).toHaveLength(2);
  });

  it("does not send a graph request or mutation when session bootstrap fails", async () => {
    const fetcher = vi.fn(async (input: RequestInfo | URL) => String(input).endsWith("/session")
      ? jsonResponse({ error: "Local guest graph is unavailable.", code: "index_graph_unavailable" }, 503)
      : jsonResponse(graph));
    const api = createBuddyIndexGraphApi({ fetcher });

    await expect(api.readGraph()).rejects.toMatchObject({ code: "index_graph_unavailable", status: 503 });
    expect(fetcher).toHaveBeenCalledTimes(1);
    expect(String(fetcher.mock.calls[0]?.[0])).toBe("/api/live/index-graph/session");
  });

  it("does not replay an unknown mutation after an auth failure; a later explicit read can resume", async () => {
    let prepareCalls = 0;
    const fetcher = vi.fn(async (input: RequestInfo | URL) => {
      const path = String(input);
      if (path.endsWith("/session")) return jsonResponse({ csrf_token: `csrf-${fetcher.mock.calls.filter(([url]) => String(url).endsWith("/session")).length}` });
      if (path.endsWith("/prepare")) {
        prepareCalls += 1;
        return jsonResponse({ error: "The session expired.", code: "session_expired" }, 401);
      }
      return jsonResponse({ status: "not_found", operation_id: "op-1" });
    });
    const api = createBuddyIndexGraphApi({ fetcher });
    const request = { operation_id: "op-1", expected_revision_id: "revision-1", kind: "create_object" as const, name: "Mira", object_kind: "person" as const };

    await expect(api.prepare(request)).rejects.toMatchObject({ code: "session_expired", status: 401 });
    expect(prepareCalls).toBe(1);
    expect(fetcher.mock.calls.filter(([path]) => String(path).endsWith("/session"))).toHaveLength(1);

    await api.readOperation("op-1");
    expect(prepareCalls).toBe(1);
    expect(fetcher.mock.calls.filter(([path]) => String(path).endsWith("/session"))).toHaveLength(2);
    const readCall = fetcher.mock.calls.find(([path]) => String(path).endsWith("/operations/op-1"));
    expect(readCall?.[1]?.method).toBeUndefined();
  });

  it("fails closed on an invalid session body and transport loss", async () => {
    const malformed = createBuddyIndexGraphApi({ fetcher: vi.fn(async () => jsonResponse({ csrf_token: " " })) });
    await expect(malformed.readGraph()).rejects.toMatchObject({ code: "network_error" });

    const disconnected = createBuddyIndexGraphApi({ fetcher: vi.fn(async () => { throw new Error("connection refused"); }) });
    await expect(disconnected.readGraph()).rejects.toMatchObject({ code: "network_error" });
  });
});
