import { afterEach, expect, it, vi } from "vitest";

afterEach(() => { vi.restoreAllMocks(); vi.unstubAllGlobals(); vi.unstubAllEnvs(); vi.resetModules(); });

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

const entityInspectionBody = {
  scope: { managed_world_id: "managed-a", native_world_id: "native-a", binding_version: 1,
    revision_id: "revision-a", scope_mode: "world", campaign_id: null },
  selection: { kind: "entity", entity_id: "entity-a" },
};
const hostedRoutes = [
  ...routes,
  ["entity-inspection", "/api/live/native-graph-inspection/read", entityInspectionBody],
  ["chronology", "/api/live/native-graph-inspection/read", { ...entityInspectionBody, selection: { kind: "chronology" } }],
  ["exact-source", "/api/live/native-graph-inspection/read", { ...entityInspectionBody, selection: { kind: "source", assertion_id: "a", evidence_ref_id: "e" } }],
] as const;

function hostedOrigin(href = "https://buddy.example/") {
  vi.stubGlobal("window", { location: { href }, dispatchEvent: vi.fn() });
}

it.each(hostedRoutes)("uses only secure same-origin cookies for hosted %s, never local credentials", async (_name, path, body) => {
  const api = await setup();
  // Retain a real cached local CSRF first, then change to the hosted destination.
  const fetch = vi.spyOn(globalThis, "fetch").mockResolvedValue(Response.json({ status: "active", csrf_token: "local-csrf" }));
  await api.ensureNativeGraphSession();
  api.setNativeGraphAccessToken("local-bearer");
  hostedOrigin();
  fetch.mockClear().mockResolvedValue(Response.json({ fixture: true }));

  await api.authenticatedApiFetch(path, {
    method: "POST", body: JSON.stringify(body), credentials: "include", redirect: "follow", mode: "cors",
    headers: { Authorization: "Bearer injected", "X-DMB-Graph-CSRF": "injected-csrf", Cookie: "injected-cookie",
      "X-DMS-Subject": "forged-owner", "Content-Type": "application/json", Accept: "application/json" },
  });

  expect(fetch).toHaveBeenCalledTimes(1);
  expect(fetch.mock.calls[0][0]).toBe(path);
  const init = fetch.mock.calls[0][1];
  expect(init).toMatchObject({ credentials: "same-origin", redirect: "error", cache: "no-store", mode: "same-origin" });
  expect(Object.fromEntries(new Headers(init?.headers))).toEqual({ accept: "application/json", "content-type": "application/json" });
  expect(JSON.parse(String(init?.body))).toEqual(body);
});

it("uses only cookies for the exact hosted World list and blocks creation", async () => {
  const api = await setup();
  hostedOrigin();
  api.setNativeGraphAccessToken("local-bearer");
  const fetch = vi.spyOn(globalThis, "fetch").mockResolvedValue(Response.json({ records: [] }));
  await api.listWorldContainers();
  expect(fetch).toHaveBeenCalledTimes(1);
  expect(fetch.mock.calls[0][0]).toBe("/api/live/world-containers");
  expect(fetch.mock.calls[0][1]).toMatchObject({ credentials: "same-origin", redirect: "error", cache: "no-store" });
  expect(new Headers(fetch.mock.calls[0][1]?.headers).has("Authorization")).toBe(false);
  await expect(api.createWorldContainer({ name: "Not allowed" })).rejects.toThrow(/exact same-origin/);
  expect(fetch).toHaveBeenCalledTimes(1);
});

it.each([
  "/api/live/native-graph-explorer.evil", "/api/live/native-graph-explorerExtra",
  "/api/live/native-graph-explorer/graph-extra", "/api/live/native-graph-explorer/graph/",
  "/api/live/native-graph-explorer/graph?world=managed-a", "/api/live/native-graph-explorer/graph#fragment",
  "/api/live/native-graph-explorer/operations/read/op-a", "/api/live/native-graph-explorer/../native-graph-explorer/graph",
  "/api/live/native-graph-explorer/%67raph", "/api/live/native-graph-inspection/catalog",
  "/api/live/native-source-inspection/read", "/api/live/agent/turn",
  "https://buddy.example/api/live/native-graph-explorer/graph",
  "https://injected:password@buddy.example/api/live/native-graph-explorer/graph",
  "//outside.invalid/api/live/native-graph-explorer/graph",
])( "blocks hosted lookalike or unsupported path %s before dispatch", async path => {
  const api = await setup();
  hostedOrigin();
  const fetch = vi.spyOn(globalThis, "fetch");
  await expect(api.authenticatedApiFetch(path, { method: "POST", body: "{}" })).rejects.toThrow(/loopback/);
  expect(fetch).not.toHaveBeenCalled();
});

it.each(["https://buddy.example", "https://outside.invalid"])("rejects explicit remote API base %s even on a hosted page", async base => {
  const api = await setup(base);
  hostedOrigin();
  const fetch = vi.spyOn(globalThis, "fetch");
  await expect(api.authenticatedApiFetch(routes[0][1], { method: "POST", body: "{}" })).rejects.toThrow(/loopback/);
  expect(fetch).not.toHaveBeenCalled();
});

it("rejects insecure hosted origins, wrong methods, unknown selections and campaign inspection", async () => {
  const api = await setup();
  const fetch = vi.spyOn(globalThis, "fetch");
  hostedOrigin("http://buddy.example/");
  await expect(api.authenticatedApiFetch(routes[0][1], { method: "POST", body: "{}" })).rejects.toThrow(/HTTPS/);
  hostedOrigin();
  await expect(api.authenticatedApiFetch(routes[0][1], { method: "GET" })).rejects.toThrow(/HTTPS/);
  for (const body of [
    { ...entityInspectionBody, selection: { kind: "unknown" } },
    { ...entityInspectionBody, scope: { ...entityInspectionBody.scope, scope_mode: "campaign", campaign_id: "c" } },
  ]) {
    await expect(api.authenticatedApiFetch("/api/live/native-graph-inspection/read", { method: "POST", body: JSON.stringify(body) }))
      .rejects.toThrow(/HTTPS/);
  }
  expect(fetch).not.toHaveBeenCalled();
});

it.each([routes[1], routes[2]])("never replays a hosted %s after auth rejection or an uncertain failure", async (_name, path, body) => {
  const api = await setup();
  hostedOrigin();
  const fetch = vi.spyOn(globalThis, "fetch")
    .mockResolvedValueOnce(Response.json({ detail: { code: "graph_auth_required" } }, { status: 401 }))
    .mockRejectedValueOnce(new TypeError("lost response"));
  const init = { method: "POST", body: JSON.stringify(body) };
  const first = await api.authenticatedApiFetch(path, init);
  expect(first.response.status).toBe(401);
  expect(fetch).toHaveBeenCalledTimes(1);
  await expect(api.authenticatedApiFetch(path, init)).rejects.toThrow("lost response");
  expect(fetch).toHaveBeenCalledTimes(2);
  expect(fetch.mock.calls.every(([url]) => url === path)).toBe(true);
});

it("invalidates pending hosted reads and already-returned bodies on account changes", async () => {
  const api = await setup();
  hostedOrigin();
  api.invalidateHostedGraphAccess("owner-a");
  let resolveOld!: (value: Response) => void;
  const fetch = vi.spyOn(globalThis, "fetch")
    .mockImplementationOnce(() => new Promise(resolve => { resolveOld = resolve; }))
    .mockResolvedValueOnce(Response.json({ account: "b" }));
  const old = api.authenticatedApiFetch(routes[0][1], { method: "POST", body: JSON.stringify(routes[0][2]) });
  const oldRejection = expect(old).rejects.toThrow(/account changed/);
  await vi.waitFor(() => expect(fetch).toHaveBeenCalledTimes(1));
  api.invalidateHostedGraphAccess("owner-b");
  const current = await api.authenticatedApiFetch(routes[0][1], { method: "POST", body: JSON.stringify(routes[0][2]) });
  resolveOld(Response.json({ account: "a" }));
  await oldRejection;
  api.invalidateHostedGraphAccess(null);
  await expect(current.response.json()).rejects.toThrow(/session changed|account changed/);
});

it("authenticates native complete-object reads with their exact revision pin", async () => {
  const api = await setup();
  api.setNativeGraphAccessToken("synthetic-managed-graph-token");
  const fetch = vi.spyOn(globalThis, "fetch").mockResolvedValue(Response.json({ fixture: true }));
  const request = {
    schema: "dmb_world_graph_object_projection_request_v1",
    worldId: "managed-a",
    campaignId: "campaign-a",
    revisionPin: "revision-a",
    nodeId: "entity-a",
    scopeMode: "world",
    admissibility: "gm",
  } satisfies Parameters<typeof api.postNativeWorldGraphCompleteObject>[0];

  const scope = { ...entityInspectionBody.scope, scope_mode: "world" as const };
  const signal = new AbortController().signal;
  await api.postNativeWorldGraphCompleteObject(request, scope, signal);

  expect(fetch).toHaveBeenCalledTimes(1);
  const [url, init] = fetch.mock.calls[0]!;
  expect(url).toBe("/api/live/native-graph-inspection/complete-object");
  expect(new Headers(init?.headers).get("Authorization")).toBe("Bearer synthetic-managed-graph-token");
  expect(init).toMatchObject({ method: "POST", credentials: "same-origin", redirect: "error" });
  expect(JSON.parse(String(init?.body))).toEqual({ request, scope });
  expect(init?.signal).toBe(signal);
});
