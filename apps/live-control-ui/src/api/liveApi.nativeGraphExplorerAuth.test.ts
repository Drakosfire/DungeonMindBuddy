import { afterEach, expect, it, vi } from "vitest";

afterEach(() => { vi.restoreAllMocks(); vi.unstubAllEnvs(); vi.resetModules(); });

async function setup(base = "") {
  vi.stubEnv("VITE_LIVE_API_BASE_URL", base);
  vi.resetModules();
  return import("./liveApi");
}

const routes = [
  ["graph", "/api/live/native-graph-explorer/graph", { managed_world_id: "managed-a" }],
  ["prepare", "/api/live/native-graph-explorer/prepare", { managed_world_id: "managed-a", operation_id: "op-a" }],
  ["confirm", "/api/live/native-graph-explorer/confirm", { managed_world_id: "managed-a", operation_id: "op-a" }],
  ["operations-read", "/api/live/native-graph-explorer/operations/read", { managed_world_id: "managed-a", operation_id: "op-a" }],
] as const;

it.each(routes)("authenticates only the exact managed explorer %s route", async (_name, path, body) => {
  const api = await setup();
  api.setNativeGraphAccessToken("synthetic-managed-graph-token");
  const fetch = vi.spyOn(globalThis, "fetch").mockResolvedValue(Response.json({ fixture: true }));

  await api.authenticatedApiFetch(path, { method: "POST", body: JSON.stringify(body) });

  expect(fetch).toHaveBeenCalledTimes(1);
  const [url, init] = fetch.mock.calls[0]!;
  expect(url).toBe(path);
  expect(new Headers(init?.headers).get("Authorization")).toBe("Bearer synthetic-managed-graph-token");
  expect(init).toMatchObject({ method: "POST", credentials: "same-origin", redirect: "error" });
  expect(JSON.parse(String(init?.body))).toEqual(body);
});

it("does not authorize lookalike explorer paths", async () => {
  const api = await setup();
  api.setNativeGraphAccessToken("synthetic-managed-graph-token");
  const fetch = vi.spyOn(globalThis, "fetch").mockResolvedValue(Response.json({ fixture: true }));

  await api.authenticatedApiFetch("/api/live/native-graph-explorer/graph-extra", { method: "POST", body: "{}" });
  await api.authenticatedApiFetch("/api/live/native-graph-explorer/operations/read/op-a", { method: "POST", body: "{}" });

  expect(fetch).toHaveBeenCalledTimes(2);
  for (const [, init] of fetch.mock.calls) {
    expect(new Headers(init?.headers).has("Authorization")).toBe(false);
  }
});

it("refuses a remote managed explorer destination before sending credentials", async () => {
  const api = await setup("https://outside.invalid");
  api.setNativeGraphAccessToken("synthetic-managed-graph-token");
  const fetch = vi.spyOn(globalThis, "fetch");

  await expect(api.authenticatedApiFetch(routes[0][1], { method: "POST", body: JSON.stringify(routes[0][2]) }))
    .rejects.toThrow(/loopback/);
  expect(fetch).not.toHaveBeenCalled();
});

it.each([routes[0], routes[3]])("renews the local graph cookie and retries the exact %s read body once", async (_name, path, body) => {
  const api = await setup();
  let sessionBoots = 0;
  let readCalls = 0;
  const bodies: string[] = [];
  const fetch = vi.spyOn(globalThis, "fetch").mockImplementation(async (url, init) => {
    if (String(url) === "/api/live/agent/local-session") {
      if (init?.method === "POST") {
        sessionBoots += 1;
        expect(init).toMatchObject({ credentials: "same-origin", redirect: "error", cache: "no-store" });
        return Response.json({ status: "active", csrf_token: `csrf-${sessionBoots}` });
      }
      return new Response(null, { status: 401 });
    }
    readCalls += 1;
    bodies.push(String(init?.body));
    expect(new Headers(init?.headers).get("X-DMB-Graph-CSRF")).toBe(`csrf-${sessionBoots}`);
    return readCalls === 1
      ? Response.json({ detail: { code: "graph_auth_required" } }, { status: 401 })
      : Response.json({ fixture: true });
  });

  await expect(api.authenticatedApiFetch(path, { method: "POST", body: JSON.stringify(body) }))
    .resolves.toMatchObject({ response: { ok: true } });
  expect(readCalls).toBe(2);
  expect(sessionBoots).toBe(2);
  expect(bodies).toEqual([JSON.stringify(body), JSON.stringify(body)]);
  expect(fetch.mock.calls.filter(([url]) => String(url) === path)).toHaveLength(2);
});

it("does not automatically replay an uncertain managed mutation after local session recovery", async () => {
  const api = await setup();
  let sessionBoots = 0;
  let prepares = 0;
  const fetch = vi.spyOn(globalThis, "fetch").mockImplementation(async (url, init) => {
    if (String(url) === "/api/live/agent/local-session") {
      if (init?.method === "POST") {
        sessionBoots += 1;
        return Response.json({ status: "active", csrf_token: `csrf-${sessionBoots}` });
      }
      return new Response(null, { status: 401 });
    }
    if (String(url) === routes[1][1]) {
      prepares += 1;
      expect(new Headers(init?.headers).get("X-DMB-Graph-CSRF")).toBe("csrf-1");
      return Response.json({ detail: { code: "graph_auth_csrf_rejected" } }, { status: 403 });
    }
    return Response.json({ fixture: true });
  });

  await api.authenticatedApiFetch(routes[1][1], { method: "POST", body: JSON.stringify(routes[1][2]) });
  expect(prepares).toBe(1);
  expect(sessionBoots).toBe(2);
  expect(fetch.mock.calls.filter(([url]) => String(url) === routes[1][1])).toHaveLength(1);
});
