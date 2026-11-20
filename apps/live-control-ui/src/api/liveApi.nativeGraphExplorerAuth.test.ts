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
  ["published Plan recap", "/api/live/native-source-inspection/published-recap", { managed_world_id: "managed-a", campaign_id: "campaign-a", session_id: "session-a" }],
  ["connected-page prepare", "/api/live/connected-pages/prepare", { world_id: "managed-a", operation_id: "11111111-1111-4111-8111-111111111111" }],
  ["connected-page confirm", "/api/live/connected-pages/confirm", { world_id: "managed-a", operation_id: "11111111-1111-4111-8111-111111111111", confirm_token: "fixture" }],
  ["Image Studio save", "/api/live/media/images/11111111-1111-4111-8111-111111111111/save", {}],
  ["relationship request", "/api/live/graph-authoring/document-relationship/request", { world_id: "managed-a" }],
  ["relationship preparation", "/api/live/graph-authoring/document-relationship/native-prepare", { review: { world_id: "managed-a" } }],
  ["relationship confirmation", "/api/live/graph-authoring/document-relationship/native-confirm", { review: { world_id: "managed-a" } }],
  ["authoring identities", "/api/live/native-graph-inspection/authoring-identities", { managed_world_id: "managed-a", scope_mode: "world", campaign_id: null }],
  ["documents trash", "/api/live/world-workspace/documents/11111111-1111-4111-8111-111111111111/trash?world_id=managed-a", { expected_revision: 1 }],
  ["documents restore", "/api/live/world-workspace/documents/11111111-1111-4111-8111-111111111111/restore?world_id=managed-a", { expected_revision: 1 }],
  ["sessions trash", "/api/live/world-workspace/sessions/11111111-1111-4111-8111-111111111111/trash?world_id=managed-a", { expected_revision: 1 }],
  ["sessions restore", "/api/live/world-workspace/sessions/11111111-1111-4111-8111-111111111111/restore?world_id=managed-a", { expected_revision: 1 }],
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

it("uses hosted cookies only for a complete-object read with a matching World pin", async () => {
  const api = await setup();
  hostedOrigin();
  api.setNativeGraphAccessToken("local-bearer");
  const fetch = vi.spyOn(globalThis, "fetch").mockResolvedValue(Response.json({ fixture: true }));
  const scope = { ...entityInspectionBody.scope, scope_mode: "world" as const };
  const request = {
    schema: "dmb_world_graph_object_projection_request_v1",
    worldId: scope.managed_world_id,
    campaignId: "campaign-a",
    revisionPin: scope.revision_id,
    nodeId: "entity-a",
    scopeMode: "world",
    admissibility: "gm",
  } satisfies Parameters<typeof api.postNativeWorldGraphCompleteObject>[0];

  await api.postNativeWorldGraphCompleteObject(request, scope);
  expect(fetch.mock.calls[0][1]).toMatchObject({
    credentials: "same-origin", redirect: "error", cache: "no-store",
  });
  expect(new Headers(fetch.mock.calls[0][1]?.headers).has("Authorization")).toBe(false);
  await expect(api.postNativeWorldGraphCompleteObject({ ...request, revisionPin: "other" }, scope))
    .rejects.toThrow(/exact same-origin/);
  expect(fetch).toHaveBeenCalledTimes(1);
});

it("authenticates Build authoring identity reads for the selected World", async () => {
  const api = await setup();
  api.setNativeGraphAccessToken("synthetic-managed-graph-token");
  const fetch = vi.spyOn(globalThis, "fetch").mockResolvedValue(Response.json({
    scope: { managed_world_id: "managed-a", scope_mode: "world", campaign_id: null },
    identities: [],
  }));

  await expect(api.getNativeAuthoringIdentities("managed-a")).resolves.toEqual([]);
  expect(fetch).toHaveBeenCalledTimes(1);
  const [url, init] = fetch.mock.calls[0]!;
  expect(url).toBe("/api/live/native-graph-inspection/authoring-identities");
  expect(new Headers(init?.headers).get("Authorization")).toBe("Bearer synthetic-managed-graph-token");
  expect(init).toMatchObject({ method: "POST", credentials: "same-origin", redirect: "error" });
});

it("shares pending catalog reads within an account and fences an account switch", async () => {
  const api = await setup();
  hostedOrigin();
  api.invalidateHostedGraphAccess("owner-a");
  let resolveOld!: (response: Response) => void;
  const fetch = vi.spyOn(globalThis, "fetch")
    .mockImplementationOnce(() => new Promise(resolve => { resolveOld = resolve; }))
    .mockResolvedValueOnce(Response.json({ records: [] }))
    .mockResolvedValueOnce(Response.json({ records: [] }));
  const first = expect(api.listWorldContainers()).rejects.toThrow(/account changed|session changed/);
  const second = expect(api.listWorldContainers()).rejects.toThrow(/account changed|session changed/);
  await vi.waitFor(() => expect(fetch).toHaveBeenCalledTimes(1));
  api.invalidateHostedGraphAccess("owner-b");
  await expect(api.listWorldContainers()).resolves.toEqual({ records: [] });
  resolveOld(Response.json({ records: [{ world_id: "owner-a-world" }] }));
  await Promise.all([first, second]);
  await api.listWorldContainers();
  expect(fetch).toHaveBeenCalledTimes(3);
});

it("admits the exact hosted Start Play preview without a local bearer", async () => {
  const api = await setup();
  hostedOrigin();
  api.setNativeGraphAccessToken("local-bearer");
  const fetch = vi.spyOn(globalThis, "fetch").mockResolvedValue(Response.json({}));
  const path = "/api/live/world-play-runs/v2/preparation?world_id=managed&entry_scene_id=scene%3Agate";
  const init = { method: "POST", body: JSON.stringify({ playable_artifact_id: "plan" }) };
  await api.authenticatedApiFetch(path, init);
  expect(fetch).toHaveBeenCalledTimes(1);
  expect(fetch.mock.calls[0][1]).toMatchObject({ credentials: "same-origin", redirect: "error", cache: "no-store" });
  expect(new Headers(fetch.mock.calls[0][1]?.headers).has("Authorization")).toBe(false);
  await expect(api.authenticatedApiFetch(path + "&world_id=foreign", init)).rejects.toThrow(/exact same-origin/);
  expect(fetch).toHaveBeenCalledTimes(1);
});

it("sends exact hosted run creation and recovery through the session cookie transport", async () => {
  const api = await setup();
  hostedOrigin();
  api.setNativeGraphAccessToken("local-bearer");
  const fetch = vi.spyOn(globalThis, "fetch").mockResolvedValue(Response.json({}));
  const base = "/api/live/world-play-runs/v2/12345678-1234-1234-1234-123456789abc";
  const body = JSON.stringify({ schema_version: "dmb_world_session_create_v1" });
  await api.authenticatedApiFetch(base + "?world_id=managed", { method: "PUT", body });
  await api.authenticatedApiFetch(base + "/creation?world_id=managed");
  await api.authenticatedApiFetch(base + "/creation:cancel?world_id=managed", { method: "POST", body });
  expect(fetch).toHaveBeenCalledTimes(3);
  for (const [, init] of fetch.mock.calls) {
    expect(init).toMatchObject({ credentials: "same-origin", redirect: "error", cache: "no-store" });
    expect(new Headers(init?.headers).has("Authorization")).toBe(false);
  }
  await expect(api.authenticatedApiFetch(base + "/creation?world_id=managed&scope=extra")).rejects.toThrow(/exact same-origin/);
  expect(fetch).toHaveBeenCalledTimes(3);
});

it("reads effective hosted run content with the session cookie and one World selector", async () => {
  const api = await setup();
  hostedOrigin();
  api.setNativeGraphAccessToken("local-bearer");
  const fetch = vi.spyOn(globalThis, "fetch").mockResolvedValue(Response.json({}));
  const path = "/api/live/world-play-runs/v2/12345678-1234-1234-1234-123456789abc/content?world_id=managed";
  await api.authenticatedApiFetch(path);
  expect(fetch.mock.calls[0][1]).toMatchObject({ credentials: "same-origin", cache: "no-store" });
  expect(new Headers(fetch.mock.calls[0][1]?.headers).has("Authorization")).toBe(false);
  await expect(api.authenticatedApiFetch(path + "&world_id=foreign")).rejects.toThrow(/exact same-origin/);
  expect(fetch).toHaveBeenCalledTimes(1);
});

it("lists hosted World mechanics from the exact picker route using session cookies", async () => {
  const api = await setup();
  hostedOrigin();
  api.setNativeGraphAccessToken("local-bearer");
  const fetch = vi.spyOn(globalThis, "fetch").mockResolvedValue(Response.json([]));
  await api.listWorldMechanicsAssociations("managed");
  expect(fetch.mock.calls[0][0]).toBe("/api/live/world-mechanics/associations?world_id=managed");
  expect(fetch.mock.calls[0][1]).toMatchObject({ credentials: "same-origin", cache: "no-store" });
  expect(new Headers(fetch.mock.calls[0][1]?.headers).has("Authorization")).toBe(false);
  await expect(api.authenticatedApiFetch("/api/live/world-mechanics/associations?world_id=managed", {
    method: "POST", body: "{}",
  })).rejects.toThrow(/exact same-origin/);
  expect(fetch).toHaveBeenCalledTimes(1);
});

it("opens an exact hosted statblock revision using session cookies", async () => {
  const api = await setup();
  hostedOrigin();
  api.setNativeGraphAccessToken("local-bearer");
  const fetch = vi.spyOn(globalThis, "fetch").mockResolvedValue(Response.json({}));
  const path = "/api/live/threat-drafts/12345678-1234-1234-1234-123456789abc/mechanics-revisions/rev_exact?world_id=managed";
  await api.authenticatedApiFetch(path);
  expect(fetch.mock.calls[0][1]).toMatchObject({ credentials: "same-origin", cache: "no-store" });
  expect(new Headers(fetch.mock.calls[0][1]?.headers).has("Authorization")).toBe(false);
  await expect(api.authenticatedApiFetch(path + "&world_id=foreign")).rejects.toThrow(/exact same-origin/);
  await expect(api.authenticatedApiFetch(path, { method: "POST", body: "{}" })).rejects.toThrow(/exact same-origin/);
  expect(fetch).toHaveBeenCalledTimes(1);
});

it("reads the hosted Ingest catalog and exact source using session cookies", async () => {
  const api = await setup();
  hostedOrigin();
  api.setNativeGraphAccessToken("local-bearer");
  const fetch = vi.spyOn(globalThis, "fetch").mockImplementation(async () => Response.json({}));
  const base = "/api/live/graph-preview/extraction-runs";
  const catalog = base + "?managed_world_id=managed&campaign_id=campaign";
  const inspection = base + "/recap-run/recap-inspection?managed_world_id=managed&expected_run_revision=2&source_revision_id=12345678-1234-1234-1234-123456789abc";
  const candidate = base + "/recap-run/candidate-projection?managed_world_id=managed";
  for (const [index, path] of [catalog, inspection, candidate].entries()) {
    await api.authenticatedApiFetch(path);
    expect(fetch.mock.calls[index][1]).toMatchObject({ credentials: "same-origin", cache: "no-store" });
    expect(new Headers(fetch.mock.calls[index][1]?.headers).has("Authorization")).toBe(false);
    await expect(api.authenticatedApiFetch(path + "&managed_world_id=foreign")).rejects.toThrow(/exact same-origin/);
  }
  expect(fetch).toHaveBeenCalledTimes(3);
});

it("reads and saves hosted Combat Tracker encounters with the session", async () => {
  const api = await setup();
  hostedOrigin();
  api.setNativeGraphAccessToken("local-bearer");
  const fetch = vi.spyOn(globalThis, "fetch").mockImplementation(async () => Response.json({}));
  const base = "/api/live/combat/encounters";
  for (const [index, suffix] of ["", "/12345678-1234-1234-1234-123456789abc"].entries()) {
    const path = base + suffix + "?world_id=managed";
    await api.authenticatedApiFetch(path);
    expect(fetch.mock.calls[index][1]).toMatchObject({ credentials: "same-origin", cache: "no-store" });
    expect(new Headers(fetch.mock.calls[index][1]?.headers).has("Authorization")).toBe(false);
    await expect(api.authenticatedApiFetch(path + "&world_id=foreign")).rejects.toThrow(/exact same-origin/);
    const method = suffix ? "PUT" : "POST";
    await expect(api.authenticatedApiFetch(path, { method: suffix ? "POST" : "PUT", body: "{}" })).rejects.toThrow(/exact same-origin/);
    await expect(api.authenticatedApiFetch(path, { method })).rejects.toThrow(/exact same-origin/);
  }
  await api.authenticatedApiFetch(base + "?world_id=managed", { method: "POST", body: "{}" });
  await api.authenticatedApiFetch(base + "/12345678-1234-1234-1234-123456789abc?world_id=managed", { method: "PUT", body: "{}" });
  expect(fetch).toHaveBeenCalledTimes(4);
  for (const [, init] of fetch.mock.calls.slice(2)) {
    expect(init).toMatchObject({ credentials: "same-origin", cache: "no-store" });
    expect(new Headers(init?.headers).has("Authorization")).toBe(false);
  }
});

it("reads hosted saved-version history and previews exact Combat mechanics", async () => {
  const api = await setup();
  hostedOrigin();
  api.setNativeGraphAccessToken("local-bearer");
  const fetch = vi.spyOn(globalThis, "fetch").mockImplementation(async () => Response.json({}));
  const draft = "12345678-1234-1234-1234-123456789abc";
  const history = `/api/live/threat-drafts/${draft}/mechanics-revisions?world_id=managed&offset=0`;
  const preview = "/api/live/combat/encounters/saved-mechanics/preview?world_id=managed";
  await api.authenticatedApiFetch(history);
  await api.authenticatedApiFetch(preview, { method: "POST", body: "{}" });
  await expect(api.authenticatedApiFetch(history + "&offset=1")).rejects.toThrow(/exact same-origin/);
  await expect(api.authenticatedApiFetch(preview)).rejects.toThrow(/exact same-origin/);
  expect(fetch).toHaveBeenCalledTimes(2);
  for (const [, init] of fetch.mock.calls) {
    expect(init).toMatchObject({ credentials: "same-origin", cache: "no-store" });
    expect(new Headers(init?.headers).has("Authorization")).toBe(false);
  }
});

it("routes hosted Combat adoption and recovery through same-origin session transport", async () => {
  const api = await setup();
  hostedOrigin();
  api.setNativeGraphAccessToken("local-bearer");
  const fetch = vi.spyOn(globalThis, "fetch").mockImplementation(async () => Response.json({}));
  const base = "/api/live/combat/encounters/12345678-1234-1234-1234-123456789abc/mechanics-adoptions";
  const operation = "87654321-1234-1234-1234-123456789abc";
  const world = "?world_id=managed";
  await api.authenticatedApiFetch(base + world, { method: "POST", body: "{}" });
  await api.authenticatedApiFetch(base + ":cancel" + world, { method: "POST", body: "{}" });
  await api.authenticatedApiFetch(base + "/" + operation + world);
  await api.authenticatedApiFetch(base + world + "&before_operation_id=" + operation);
  await expect(api.authenticatedApiFetch(base + ":cancel" + world)).rejects.toThrow(/exact same-origin/);
  await expect(api.authenticatedApiFetch(base + world + "&world_id=foreign")).rejects.toThrow(/exact same-origin/);
  expect(fetch).toHaveBeenCalledTimes(4);
  for (const [, init] of fetch.mock.calls) {
    expect(init).toMatchObject({ credentials: "same-origin", cache: "no-store" });
    expect(new Headers(init?.headers).has("Authorization")).toBe(false);
  }
});

it("uses the hosted session for both Combat actor previews", async () => {
  const api = await setup();
  hostedOrigin();
  api.setNativeGraphAccessToken("local-bearer");
  const fetch = vi.spyOn(globalThis, "fetch").mockImplementation(async () => Response.json({}));
  for (const kind of ["accepted-mechanics", "world-mechanics"]) {
    const path = `/api/live/combat/encounters/${kind}/preview?world_id=managed`;
    await api.authenticatedApiFetch(path, { method: "POST", body: "{}" });
    await expect(api.authenticatedApiFetch(path)).rejects.toThrow(/exact same-origin/);
    await expect(api.authenticatedApiFetch(path + "&world_id=foreign", {
      method: "POST", body: "{}",
    })).rejects.toThrow(/exact same-origin/);
  }
  expect(fetch).toHaveBeenCalledTimes(2);
  for (const [, init] of fetch.mock.calls) {
    expect(init).toMatchObject({ credentials: "same-origin", cache: "no-store", method: "POST" });
    expect(new Headers(init?.headers).has("Authorization")).toBe(false);
  }
});

it("starts and reloads a hosted World conversation through the DungeonMind session", async () => {
  const api = await setup();
  hostedOrigin();
  api.setNativeGraphAccessToken("local-bearer");
  const fetch = vi.spyOn(globalThis, "fetch").mockImplementation(async () => Response.json({}));
  const base = "/api/live/agent/worlds/managed/conversation";
  await api.authenticatedApiFetch(base + "?limit=25");
  await api.authenticatedApiFetch(base + "/new", { method: "POST", body: "{}" });
  await api.authenticatedApiFetch(base + "s/active/messages?limit=25");
  await expect(api.authenticatedApiFetch(base + "/new?world_id=foreign", {
    method: "POST", body: "{}",
  })).rejects.toThrow(/exact same-origin/);
  expect(fetch).toHaveBeenCalledTimes(3);
  for (const [, init] of fetch.mock.calls) {
    expect(init).toMatchObject({ credentials: "same-origin", cache: "no-store" });
    expect(new Headers(init?.headers).has("Authorization")).toBe(false);
  }
});

it("uses hosted same-origin credentials for exactly the draft read and edit routes", async () => {
  await setup();
  hostedOrigin();
  const { openConversationDraft, saveConversationDraft } = await import("./conversationDraftApi");
  const fetch = vi.spyOn(globalThis, "fetch")
    .mockResolvedValueOnce(Response.json({ revision: 1, markdown: "Original" }))
    .mockResolvedValueOnce(Response.json({ revision: 2, markdown: "Edited" }));
  const scope = {
    worldId: "managed",
    conversationId: "11111111-1111-4111-8111-111111111111",
    turnId: "22222222-2222-4222-8222-222222222222",
  };
  await expect(openConversationDraft(scope)).resolves.toEqual({ revision: 1, markdown: "Original" });
  await expect(saveConversationDraft(scope, 1, "Edited")).resolves.toEqual({ revision: 2, markdown: "Edited" });
  const path = `/api/live/agent/worlds/managed/conversations/${scope.conversationId}/drafts/${scope.turnId}`;
  expect(fetch.mock.calls.map(call => call[0])).toEqual([path, path]);
  expect(fetch.mock.calls[0][1]).toMatchObject({ credentials: "same-origin", mode: "same-origin" });
  expect(fetch.mock.calls[1][1]).toMatchObject({ method: "PUT", credentials: "same-origin", mode: "same-origin" });
  expect(JSON.parse(String(fetch.mock.calls[1][1]?.body))).toEqual({ expected_revision: 1, markdown: "Edited" });
});

it("reads earlier image directions with the exact hosted session route", async () => {
  const api = await setup();
  hostedOrigin();
  api.setNativeGraphAccessToken("local-bearer");
  const fetch = vi.spyOn(globalThis, "fetch").mockResolvedValue(Response.json({ items: [] }));
  const { listPreparedImages } = await import("../media/PreparedBuildImage");
  const conversation = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee";
  const path = `/api/live/media/images/preparations/list?world_id=elderwyld&conversation_id=${conversation}`;

  await expect(listPreparedImages("elderwyld", conversation)).resolves.toEqual([]);
  expect(fetch).toHaveBeenCalledTimes(1);
  expect(fetch.mock.calls[0][0]).toBe(path);
  expect(fetch.mock.calls[0][1]).toMatchObject({ credentials: "same-origin", redirect: "error", cache: "no-store" });
  expect(new Headers(fetch.mock.calls[0][1]?.headers).has("Authorization")).toBe(false);
  await expect(api.authenticatedApiFetch(path + "&world_id=other")).rejects.toThrow(/exact same-origin/);
  expect(fetch).toHaveBeenCalledTimes(1);
});

it("uses the hosted session only for exact read-only variant approval", async () => {
  const api = await setup();
  hostedOrigin();
  api.setNativeGraphAccessToken("local-bearer");
  const fetch = vi.spyOn(globalThis, "fetch").mockResolvedValue(Response.json({ status: "unavailable" }));
  const id = "12345678-1234-1234-1234-123456789abc";
  const path = `/api/live/agent/worlds/managed/conversations/${id}/turns/${id}/variant-approval`;
  await api.authenticatedApiFetch(path);
  expect(fetch.mock.calls[0][1]).toMatchObject({ credentials: "same-origin" });
  expect(new Headers(fetch.mock.calls[0][1]?.headers).has("Authorization")).toBe(false);
  await expect(api.authenticatedApiFetch(path, { method: "POST" })).rejects.toThrow(/exact same-origin/);
  await expect(api.authenticatedApiFetch(path + "?review=other")).rejects.toThrow(/exact same-origin/);
});

it.each(["creatures", "requests/11111111-1111-4111-8111-111111111111"])(
  "reads world mechanics through exact hosted %s route",
  async suffix => {
    const api = await setup();
    hostedOrigin();
    api.setNativeGraphAccessToken("local-bearer");
    const fetch = vi.spyOn(globalThis, "fetch").mockResolvedValue(Response.json({ fixture: true }));
    const path = `/api/live/world-mechanics/associations/${suffix}?world_id=managed`;
    await api.authenticatedApiFetch(path);
    const [, init] = fetch.mock.calls[0];
    expect(init).toMatchObject({ credentials: "same-origin", redirect: "error", cache: "no-store" });
    expect(new Headers(init?.headers).has("Authorization")).toBe(false);
    await expect(api.authenticatedApiFetch(path + "&world_id=other")).rejects.toThrow(/exact same-origin/);
    expect(fetch).toHaveBeenCalledTimes(1);
  },
);

it("uses the hosted session for exact saved PDF review reads", async () => {
  const api = await setup();
  hostedOrigin();
  api.setNativeGraphAccessToken("local-bearer");
  const fetch = vi.spyOn(globalThis, "fetch").mockResolvedValue(Response.json({ items: [] }));
  const list = "/api/live/agent/worlds/elderwyld/build-pdf-sources/statblock-reviews";
  const id = "12345678-1234-1234-1234-123456789abc";
  const detail = list + "/" + id;
  const status = detail + "/publication";
  const revision = status + "/statblock?draft_id=" + id + "&revision_id=rev_saved";
  for (const path of [list, detail, status, revision]) {
    await api.authenticatedApiFetch(path);
    const [url, init] = fetch.mock.calls.at(-1)!;
    expect(url).toBe(path);
    expect(init).toMatchObject({ credentials: "same-origin", cache: "no-store", redirect: "error" });
    expect(new Headers(init?.headers).has("Authorization")).toBe(false);
  }
  await expect(api.authenticatedApiFetch(detail + "?world_id=foreign")).rejects.toThrow(/exact same-origin/);
  await expect(api.authenticatedApiFetch(revision + "&revision_id=other")).rejects.toThrow(/exact same-origin/);
  await expect(api.authenticatedApiFetch(status, { method: "POST", body: "{}" })).rejects.toThrow(/exact same-origin/);
  const save = { method: "PUT", body: JSON.stringify({ expected_revision: 1, definition: {}, regions: [] }) };
  await api.authenticatedApiFetch(detail, save);
  const [url, init] = fetch.mock.calls.at(-1)!;
  expect(url).toBe(detail);
  expect(init).toMatchObject({ method: "PUT", credentials: "same-origin", redirect: "error" });
  expect(new Headers(init?.headers).has("Authorization")).toBe(false);
  for (const path of [list, status, detail + "?world_id=other"]) {
    await expect(api.authenticatedApiFetch(path, save)).rejects.toThrow(/exact same-origin/);
  }
  await expect(api.authenticatedApiFetch(detail, { ...save, body: "{}" })).rejects.toThrow(/exact same-origin/);
  expect(fetch).toHaveBeenCalledTimes(5);
});

it("uses the hosted session for each exact PDF publication step", async () => {
  const api = await setup();
  hostedOrigin();
  api.setNativeGraphAccessToken("local-bearer");
  const fetch = vi.spyOn(globalThis, "fetch").mockImplementation(async () => Response.json({}));
  const id = "12345678-1234-1234-1234-123456789abc";
  const root = "/api/live/agent/worlds/elderwyld/build-pdf-sources/statblock-reviews/" + id;
  const post = { method: "POST" };
  const accept = { ...post, body: JSON.stringify({
    operation_id: id, expected_revision: 1, expected_draft_version: 1,
    validation_receipt: {}, validation_definition_digest: "sha256:example",
  }) };
  for (const [path, options] of [
    ...["creature-draft", "validate", "publication"].map(operation =>
      [root + "/" + operation + "?expected_revision=1", post] as const),
    [root + "/accept/" + id, accept] as const,
  ]) {
    await api.authenticatedApiFetch(path, options);
    const [url, init] = fetch.mock.calls.at(-1)!;
    expect(url).toBe(path);
    expect(init).toMatchObject({ method: "POST", credentials: "same-origin", redirect: "error" });
    expect(new Headers(init?.headers).has("Authorization")).toBe(false);
  }
  await expect(api.authenticatedApiFetch(root + "/publication?expected_revision=1&expected_revision=2", post)).rejects.toThrow(/exact same-origin/);
  await expect(api.authenticatedApiFetch(root + "/validate?expected_revision=1", accept)).rejects.toThrow(/exact same-origin/);
  await expect(api.authenticatedApiFetch(root + "/accept/" + id, post)).rejects.toThrow(/exact same-origin/);
  expect(fetch).toHaveBeenCalledTimes(4);
});

it("reads captured diagnostic prompts through the hosted session", async () => {
  const api = await setup();
  hostedOrigin();
  api.setNativeGraphAccessToken("local-bearer");
  const fetch = vi.spyOn(globalThis, "fetch").mockResolvedValue(Response.json({ results: [] }));
  const id = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee";
  await api.getWorldAgentTurnPrompt("elderwyld", id, id, id);
  await api.getWorldAgentTurnPrompts("elderwyld", id, [{ trace_id: id, provider_attempt_id: id }]);
  expect(fetch).toHaveBeenCalledTimes(2);
  for (const [, init] of fetch.mock.calls) {
    expect(init).toMatchObject({ credentials: "same-origin", cache: "no-store", redirect: "error" });
    expect(new Headers(init?.headers).has("Authorization")).toBe(false);
  }
  await expect(api.authenticatedApiFetch(
    `/api/live/agent/worlds/elderwyld/conversation/turns/${id}/context-trace/prompts`,
    { method: "POST", body: JSON.stringify({ prompts: [], extra: true }) },
  )).rejects.toThrow(/exact same-origin/);
  expect(fetch).toHaveBeenCalledTimes(2);
});

it("reads a hosted conversation name without enabling name writes", async () => {
  const api = await setup();
  hostedOrigin();
  api.setNativeGraphAccessToken("local-bearer");
  const fetch = vi.spyOn(globalThis, "fetch").mockResolvedValue(Response.json({ title: "Saved" }));
  const path = "/api/live/agent/worlds/elderwyld/conversations/aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee/name";
  await api.authenticatedApiFetch(path);
  expect(fetch).toHaveBeenCalledOnce();
  expect(fetch.mock.calls[0][1]).toMatchObject({ credentials: "same-origin", cache: "no-store" });
  expect(new Headers(fetch.mock.calls[0][1]?.headers).has("Authorization")).toBe(false);
  await expect(api.authenticatedApiFetch(path, { method: "PUT", body: "{}" })).rejects.toThrow(/exact same-origin/);
  expect(fetch).toHaveBeenCalledOnce();
});

it("uses the hosted session for retained PDF evidence in Build", async () => {
  const api = await setup();
  hostedOrigin();
  api.setNativeGraphAccessToken("local-bearer");
  const fetch = vi.spyOn(globalThis, "fetch").mockImplementation(async () => Response.json({}));
  const root = "/api/live/agent/worlds/elderwyld/build-pdf-sources";
  const locator = { method: "POST", body: JSON.stringify({ source_revision_id: "retained-revision" }) };
  for (const [path, request] of [
    [root + "?after=", undefined],
    [root + "?after=cursor", undefined],
    [root + "/open", locator],
    [root + "/region:validate", locator],
  ] as const) {
    await api.authenticatedApiFetch(path, request);
    const [url, init] = fetch.mock.calls.at(-1)!;
    expect(url).toBe(path);
    expect(init).toMatchObject({ credentials: "same-origin", cache: "no-store", redirect: "error" });
    expect(new Headers(init?.headers).has("Authorization")).toBe(false);
  }
  await expect(api.authenticatedApiFetch(root + "?after=&after=other")).rejects.toThrow(/exact same-origin/);
  await expect(api.authenticatedApiFetch(root + "/open?world_id=foreign", locator)).rejects.toThrow(/exact same-origin/);
  await expect(api.authenticatedApiFetch(root + "/ocr", locator)).rejects.toThrow(/exact same-origin/);
  expect(fetch).toHaveBeenCalledTimes(4);
});

it("uses the hosted session for binary PDF admission to the selected World", async () => {
  const api = await setup();
  hostedOrigin();
  api.setNativeGraphAccessToken("local-bearer");
  const fetch = vi.spyOn(globalThis, "fetch").mockResolvedValue(Response.json({}));
  const path = "/api/live/agent/worlds/elderwyld/build-pdf-sources?admission_id=12345678-1234-1234-1234-123456789abc";
  const body = new File(["%PDF-1.7"], "fixture.pdf", { type: "application/pdf" });
  const upload = {
    method: "POST", body,
    headers: new Headers({ "Content-Type": "application/pdf", "X-Pdf-Created-At": "2026-11-15T00:00:00Z" }),
  };
  await api.authenticatedApiFetch(path, upload);
  const [url, init] = fetch.mock.calls[0]!;
  expect(url).toBe(path);
  expect(init?.body).toBe(body);
  expect(init).toMatchObject({ credentials: "same-origin", redirect: "error", cache: "no-store" });
  const headers = new Headers(init?.headers);
  expect(headers.has("Authorization")).toBe(false);
  expect(headers.get("Content-Type")).toBe("application/pdf");
  expect(headers.get("X-Pdf-Created-At")).toBe(upload.headers.get("X-Pdf-Created-At"));
  await expect(api.authenticatedApiFetch(path + "&world_id=foreign", upload)).rejects.toThrow(/exact same-origin/);
  await expect(api.authenticatedApiFetch(path, { ...upload, body: "{}" })).rejects.toThrow(/exact same-origin/);
  expect(fetch).toHaveBeenCalledTimes(1);
});

it("uses the hosted session to extract a statblock review from retained PDF regions", async () => {
  const api = await setup();
  hostedOrigin();
  api.setNativeGraphAccessToken("local-bearer");
  const fetch = vi.spyOn(globalThis, "fetch").mockResolvedValue(Response.json({}));
  const root = "/api/live/agent/worlds/elderwyld/build-pdf-sources/statblock-reviews/12345678-1234-1234-1234-123456789abc";
  const body = JSON.stringify({
    regions: [{ source_revision_id: "retained-revision", page: 1 }],
    instruction: "Use the printed action names.", edition: "2024", whole_pdf: true,
  });
  await api.authenticatedApiFetch(root + "/from-regions", { method: "POST", body });
  const [url, options] = fetch.mock.calls[0]!;
  expect(url).toBe(root + "/from-regions");
  expect(options).toMatchObject({ method: "POST", body, credentials: "same-origin", redirect: "error" });
  expect(new Headers(options?.headers).has("Authorization")).toBe(false);
  await expect(api.authenticatedApiFetch(root + "/from-regions?world_id=other", { method: "POST", body })).rejects.toThrow(/exact same-origin/);
  await expect(api.authenticatedApiFetch(root + "/from-regions", { method: "POST", body: "{}" })).rejects.toThrow(/exact same-origin/);
  expect(fetch).toHaveBeenCalledTimes(1);
});

it("uses the hosted session to append a PDF review to an exact saved draft", async () => {
  const api = await setup();
  hostedOrigin();
  api.setNativeGraphAccessToken("local-bearer");
  const fetch = vi.spyOn(globalThis, "fetch").mockResolvedValue(Response.json({}));
  const id = "12345678-1234-1234-1234-123456789abc";
  const path = "/api/live/agent/worlds/elderwyld/build-pdf-sources/statblock-reviews/" + id + "/append/" + id;
  const append = { method: "POST", body: JSON.stringify({ operation_id: id, expected_revision: 1, base: { revision_id: "rev_saved" } }) };
  await api.authenticatedApiFetch(path, append);
  const [url, init] = fetch.mock.calls[0]!;
  expect(url).toBe(path);
  expect(init).toMatchObject({ ...append, credentials: "same-origin", redirect: "error" });
  expect(new Headers(init?.headers).has("Authorization")).toBe(false);
  await expect(api.authenticatedApiFetch(path + "?world_id=other", append)).rejects.toThrow(/exact same-origin/);
  await expect(api.authenticatedApiFetch(path, { ...append, body: "{}" })).rejects.toThrow(/exact same-origin/);
  expect(fetch).toHaveBeenCalledTimes(1);
});

it("reads image capabilities for the selected hosted World", async () => {
  const api = await setup();
  hostedOrigin();
  const fetch = vi.spyOn(globalThis, "fetch").mockResolvedValue(Response.json({ models: [] }));
  const path = "/api/live/media/images/capabilities?world_id=elderwyld";
  await api.authenticatedApiFetch(path);
  expect(fetch.mock.calls[0][1]).toMatchObject({ credentials: "same-origin", cache: "no-store" });
  await expect(api.authenticatedApiFetch(path + "&world_id=foreign")).rejects.toThrow(/exact same-origin/);
  expect(fetch).toHaveBeenCalledOnce();
});

it("uses the hosted session for Worldbuilding extraction of an exact saved page", async () => {
  const api = await setup();
  hostedOrigin();
  const fetch = vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(Response.json({}));
  const path = "/api/live/graph-preview/extraction-runs";
  const request = { document_id: "00000000-0000-4000-8000-000000000001",
    expected_revision: 2, expected_content_sha256: "sha256:" + "a".repeat(64) };
  await api.launchExtractionRun(request);
  expect(fetch).toHaveBeenCalledWith(path, expect.objectContaining({
    method: "POST", credentials: "same-origin", mode: "same-origin", body: JSON.stringify(request),
  }));
  await expect(api.launchExtractionRun({ ...request, expected_revision: 0 })).rejects.toThrow(/exact same-origin/);
  expect(fetch).toHaveBeenCalledTimes(1);
});

it.each(["prepare", "confirm"])("uses exact hosted transport for PDF Event %s", async action => {
  const api = await setup();
  hostedOrigin();
  const fetch = vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(Response.json({}));
  const path = `/api/live/worlds/managed/pdf-adventure-events/${action}`;
  const init = { method: "POST", body: JSON.stringify({ fixture: true }) };
  await api.authenticatedApiFetch(path, init);
  expect(fetch).toHaveBeenCalledWith(path, expect.objectContaining({
    method: "POST", credentials: "same-origin", mode: "same-origin",
  }));
  await expect(api.authenticatedApiFetch(path + "?world_id=foreign", init)).rejects.toThrow(/exact same-origin/);
  expect(fetch).toHaveBeenCalledTimes(1);
});

it("uses the hosted session for exact native Build source status and admission", async () => {
  const api = await setup();
  hostedOrigin();
  api.setNativeGraphAccessToken("local-bearer");
  const fetch = vi.spyOn(globalThis, "fetch").mockImplementation(async () => Response.json({}));
  const id = "12345678-1234-1234-1234-123456789abc";
  const path = "/api/live/workspace-documents/" + id + "/native-world-source";
  await api.getNativeWorldSourceAdmissionStatus(id, 1);
  await api.admitNativeWorldSource(id, 1, "a".repeat(64));
  expect(fetch.mock.calls.map(([url]) => url)).toEqual([path + "?expected_revision=1", path]);
  for (const [, init] of fetch.mock.calls) {
    expect(init).toMatchObject({ credentials: "same-origin", redirect: "error" });
    expect(new Headers(init?.headers).has("Authorization")).toBe(false);
  }
  await expect(api.admitNativeWorldSource(id, 1, "invalid")).rejects.toThrow(/exact same-origin/);
  await expect(api.authenticatedApiFetch(path + "?world_id=other")).rejects.toThrow(/exact same-origin/);
  expect(fetch).toHaveBeenCalledTimes(2);
});

it.each(["pdf", "text"])("uses the hosted session to withdraw a pinned %s source", async kind => {
  const api = await setup();
  hostedOrigin();
  api.setNativeGraphAccessToken("local-bearer");
  const fetch = vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response(null, { status: 204 }));
  const path = "/api/live/agent/worlds/elderwyld/build-source-withdrawals";
  const request = { method: "POST", body: JSON.stringify({ kind, revision_id: "retained-revision" }) };
  await api.authenticatedApiFetch(path, request);
  const [url, init] = fetch.mock.calls[0]!;
  expect(url).toBe(path);
  expect(init).toMatchObject({ ...request, credentials: "same-origin", redirect: "error" });
  expect(new Headers(init?.headers).has("Authorization")).toBe(false);
  await expect(api.authenticatedApiFetch(path + "?world_id=other", request)).rejects.toThrow(/exact same-origin/);
  await expect(api.authenticatedApiFetch(path, { ...request, body: JSON.stringify({ kind }) })).rejects.toThrow(/exact same-origin/);
  expect(fetch).toHaveBeenCalledTimes(1);
});

it("uses hosted cookies for exact saved statblock revision operations", async () => {
  const api = await setup();
  hostedOrigin();
  api.setNativeGraphAccessToken("local-bearer");
  const fetch = vi.spyOn(globalThis, "fetch").mockImplementation(async () => Response.json({}));
  const draft = "/api/live/threat-drafts/11111111-1111-4111-8111-111111111111";
  const operation = draft + "/mechanics-revision-operations/22222222-2222-4222-8222-222222222222";
  await api.authenticatedApiFetch(draft + "/mechanics-revisions", {
    method: "POST", body: JSON.stringify({ world_id: "managed" }),
  });
  await api.authenticatedApiFetch(operation + "?world_id=managed");
  await api.authenticatedApiFetch(operation + ":recover?world_id=managed", { method: "POST" });
  for (const [, init] of fetch.mock.calls) {
    expect(init).toMatchObject({ credentials: "same-origin", redirect: "error", cache: "no-store" });
    expect(new Headers(init?.headers).has("Authorization")).toBe(false);
  }
  await expect(api.authenticatedApiFetch(operation + "?world_id=managed&world_id=other"))
    .rejects.toThrow(/exact same-origin/);
  expect(fetch).toHaveBeenCalledTimes(3);
});

it("archives only an exact saved statblock version through the hosted session", async () => {
  const api = await setup();
  hostedOrigin();
  api.setNativeGraphAccessToken("local-bearer");
  const fetch = vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response(null, { status: 204 }));
  const path = "/api/live/threat-drafts/11111111-1111-4111-8111-111111111111/saved-statblock?world_id=managed";
  const init = { method: "DELETE" };
  await api.authenticatedApiFetch(path + "&expected_version=1", init);
  const [, sent] = fetch.mock.calls[0];
  expect(sent).toMatchObject({ credentials: "same-origin", redirect: "error", cache: "no-store" });
  expect(new Headers(sent?.headers).has("Authorization")).toBe(false);
  await expect(api.authenticatedApiFetch(path, init)).rejects.toThrow(/exact same-origin/);
  expect(fetch).toHaveBeenCalledTimes(1);
});


it("associates mechanics with a creature in the same hosted World", async () => {
  const api = await setup();
  hostedOrigin();
  api.setNativeGraphAccessToken("local-bearer");
  const fetch = vi.spyOn(globalThis, "fetch").mockResolvedValue(Response.json({ fixture: true }));
  const path = "/api/live/world-mechanics/associations?world_id=managed";
  const command = (world: string) => ({ method: "POST", body: JSON.stringify({ target: { managed_world_id: world } }) });
  await api.authenticatedApiFetch(path, command("managed"));
  const [, sent] = fetch.mock.calls[0];
  expect(sent).toMatchObject({ credentials: "same-origin", redirect: "error", cache: "no-store" });
  expect(new Headers(sent?.headers).has("Authorization")).toBe(false);
  await expect(api.authenticatedApiFetch(path, command("other"))).rejects.toThrow(/exact same-origin/);
  expect(fetch).toHaveBeenCalledTimes(1);
});

it("uses the hosted session for status, prepare, and confirm of an exact creature draft", async () => {
  const api = await setup();
  hostedOrigin();
  api.setNativeGraphAccessToken("local-bearer");
  const fetch = vi.spyOn(globalThis, "fetch").mockImplementation(async () => Response.json({}));
  const path = "/api/live/threat-drafts/11111111-1111-4111-8111-111111111111/native-creature";
  await api.authenticatedApiFetch(path + "?world_id=managed");
  await api.authenticatedApiFetch(path + "/prepare", { method: "POST", body: '{"world_id":"managed"}' });
  await api.authenticatedApiFetch(path + "/confirm", { method: "POST", body: '{"review":{"world_id":"managed"}}' });
  for (const [, init] of fetch.mock.calls) {
    expect(init).toMatchObject({ credentials: "same-origin", redirect: "error", cache: "no-store" });
    expect(new Headers(init?.headers).has("Authorization")).toBe(false);
  }
  await expect(api.authenticatedApiFetch(path + "/confirm?world_id=managed", {
    method: "POST", body: '{"review":{"world_id":"managed"}}',
  })).rejects.toThrow(/exact same-origin/);
  expect(fetch).toHaveBeenCalledTimes(3);
});

it.each(["", "/11111111-1111-4111-8111-111111111111/revisions/1"])(
  "reads hosted session evidence at the exact World route %s",
  async suffix => {
    const api = await setup();
    hostedOrigin();
    api.setNativeGraphAccessToken("local-bearer");
    const fetch = vi.spyOn(globalThis, "fetch").mockResolvedValue(Response.json({ fixture: true }));
    const path = `/api/live/world-session-evidence${suffix}?world_id=managed`;
    await api.authenticatedApiFetch(path);
    const [, init] = fetch.mock.calls[0];
    expect(init).toMatchObject({ credentials: "same-origin", redirect: "error", cache: "no-store" });
    expect(new Headers(init?.headers).has("Authorization")).toBe(false);
    await expect(api.authenticatedApiFetch(path + "&world_id=foreign")).rejects.toThrow(/exact same-origin/);
    expect(fetch).toHaveBeenCalledTimes(1);
  },
);

it("opens a saved Play review only through the exact hosted World route", async () => {
  const api = await setup();
  hostedOrigin();
  api.setNativeGraphAccessToken("local-bearer");
  const fetch = vi.spyOn(globalThis, "fetch").mockResolvedValue(Response.json({ fixture: true }));
  const path = "/api/live/world-play-runs/v2/11111111-1111-4111-8111-111111111111/review?world_id=managed";
  await api.authenticatedApiFetch(path);
  const [, init] = fetch.mock.calls[0];
  expect(init).toMatchObject({ credentials: "same-origin", redirect: "error", cache: "no-store" });
  expect(new Headers(init?.headers).has("Authorization")).toBe(false);
  await expect(api.authenticatedApiFetch(path + "&world_id=foreign")).rejects.toThrow(/exact same-origin/);
  expect(fetch).toHaveBeenCalledTimes(1);
});

it.each(["", "/22222222-2222-4222-8222-222222222222"])(
  "reads owned hosted Play scene proposals at the exact route %s", async suffix => {
    const api = await setup();
    hostedOrigin();
    api.setNativeGraphAccessToken("local-bearer");
    const fetch = vi.spyOn(globalThis, "fetch").mockResolvedValue(Response.json({ fixture: true }));
    const path = `/api/live/world-play-runs/v2/11111111-1111-4111-8111-111111111111/content/proposals${suffix}?world_id=managed`;
    await api.authenticatedApiFetch(path);
    const [, init] = fetch.mock.calls[0];
    expect(init).toMatchObject({ credentials: "same-origin", redirect: "error", cache: "no-store" });
    expect(new Headers(init?.headers).has("Authorization")).toBe(false);
    await expect(api.authenticatedApiFetch(path + "&world_id=foreign")).rejects.toThrow(/exact same-origin/);
    expect(fetch).toHaveBeenCalledTimes(1);
  },
);

it("submits a scene proposal only at its exact hosted Play route", async () => {
  const api = await setup();
  hostedOrigin();
  api.setNativeGraphAccessToken("local-bearer");
  const fetch = vi.spyOn(globalThis, "fetch").mockResolvedValue(Response.json({ fixture: true }));
  const collection = "/api/live/world-play-runs/v2/11111111-1111-4111-8111-111111111111/content/proposals";
  const init = { method: "POST", body: JSON.stringify({ instruction: "Describe the gate" }) };
  await api.authenticatedApiFetch(collection + "/22222222-2222-4222-8222-222222222222?world_id=managed", init);
  const [, sent] = fetch.mock.calls[0];
  expect(sent).toMatchObject({ credentials: "same-origin", redirect: "error", cache: "no-store" });
  expect(new Headers(sent?.headers).has("Authorization")).toBe(false);
  await expect(api.authenticatedApiFetch(collection + "?world_id=managed", init)).rejects.toThrow(/exact same-origin/);
  expect(fetch).toHaveBeenCalledTimes(1);
});

it("saves Play progress through the exact hosted World route", async () => {
  const api = await setup();
  hostedOrigin();
  const fetch = vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(Response.json({}));
  const runId = "11111111-1111-4111-8111-111111111111";
  const path = `/api/live/world-play-runs/v2/${runId}/progress?world_id=managed`;
  const request = { method: "PUT", body: JSON.stringify({ expected_run_revision: 2, progress: {} }) };
  await api.authenticatedApiFetch(path, request);
  expect(fetch.mock.calls[0]).toEqual([path, expect.objectContaining({
    method: "PUT", credentials: "same-origin", mode: "same-origin",
  })]);
  await expect(api.authenticatedApiFetch(path + "&world_id=foreign", request)).rejects.toThrow(/exact same-origin/);
  expect(fetch).toHaveBeenCalledTimes(1);
});

it("uses hosted cookies for exact owned Play review commands", async () => {
  const api = await setup();
  hostedOrigin();
  api.setNativeGraphAccessToken("local-bearer");
  const fetch = vi.spyOn(globalThis, "fetch").mockResolvedValue(Response.json({ fixture: true }));
  const id = "11111111-1111-4111-8111-111111111111";
  const path = `/api/live/world-play-runs/v2/${id}/review/commands/${id}?world_id=managed`;
  for (const action of ["end", "save", "reopen"]) {
    await api.authenticatedApiFetch(path, { method: "PUT", body: JSON.stringify({ action }) });
    const [, init] = fetch.mock.calls.at(-1)!;
    expect(init).toMatchObject({ credentials: "same-origin", redirect: "error", cache: "no-store" });
    expect(new Headers(init?.headers).has("Authorization")).toBe(false);
  }
  await expect(api.authenticatedApiFetch(path, { method: "PUT", body: '{"action":"unknown"}' }))
    .rejects.toThrow(/exact same-origin/);
  expect(fetch).toHaveBeenCalledTimes(3);
});

it("saves Play editions with hosted cookies and the exact commit schema", async () => {
  const api = await setup();
  hostedOrigin();
  api.setNativeGraphAccessToken("local-bearer");
  const fetch = vi.spyOn(globalThis, "fetch").mockResolvedValue(Response.json({ fixture: true }));
  const id = "11111111-1111-4111-8111-111111111111";
  const path = `/api/live/world-play-runs/v2/${id}/content/commands/${id}?world_id=managed`;
  const init = { method: "PUT", body: JSON.stringify({ schema_version: "dmb_world_play_run_content_commit_v1" }) };
  await api.authenticatedApiFetch(path, init);
  const [, sent] = fetch.mock.calls[0];
  expect(sent).toMatchObject({ credentials: "same-origin", redirect: "error", cache: "no-store" });
  expect(new Headers(sent?.headers).has("Authorization")).toBe(false);
  await expect(api.authenticatedApiFetch(path, { ...init, body: "{}" })).rejects.toThrow(/exact same-origin/);
  expect(fetch).toHaveBeenCalledTimes(1);
});

it("uses hosted transport only for recap object requests with a matching World pin", async () => {
  const api = await setup();
  hostedOrigin();
  api.setNativeGraphAccessToken("local-bearer");
  const fetch = vi.spyOn(globalThis, "fetch").mockImplementation(async () => Response.json({}));
  const path = "/api/live/native-source-inspection/published-recap/objects";
  const body = {
    managed_world_id: "managed", campaign_id: "campaign", session_id: "session",
    source_artifact_id: "source", source_revision_id: "revision",
    scope: { managed_world_id: "managed", scope_mode: "world", campaign_id: null,
      native_world_id: "native", revision_id: "graph-revision", binding_version: 1 },
  };
  await api.authenticatedApiFetch(path, { method: "POST", body: JSON.stringify(body) });
  expect(fetch.mock.calls[0][1]).toMatchObject({ credentials: "same-origin", cache: "no-store", redirect: "error" });
  expect(new Headers(fetch.mock.calls[0][1]?.headers).has("Authorization")).toBe(false);
  await expect(api.authenticatedApiFetch(path, {
    method: "POST", body: JSON.stringify({ ...body, managed_world_id: "foreign" }),
  })).rejects.toThrow(/exact same-origin/);
  expect(fetch).toHaveBeenCalledTimes(1);
});

it.each(["conversation/turns", "plan-proposals"])("reads saved %s evidence with hosted cookies and exact citation selectors", async (subject) => {
  const api = await setup();
  hostedOrigin();
  api.setNativeGraphAccessToken("local-bearer");
  const fetch = vi.spyOn(globalThis, "fetch").mockResolvedValue(Response.json({ fixture: true }));
  const path = `/api/live/agent/worlds/managed/${subject}/11111111-1111-4111-8111-111111111111/graph-evidence?claim_id=claim&anchor_id=anchor`;
  await api.authenticatedApiFetch(path);
  const [, init] = fetch.mock.calls[0];
  expect(init).toMatchObject({ credentials: "same-origin", redirect: "error", cache: "no-store" });
  expect(new Headers(init?.headers).has("Authorization")).toBe(false);
  await expect(api.authenticatedApiFetch(path + "&anchor_id=foreign")).rejects.toThrow(/exact same-origin/);
  expect(fetch).toHaveBeenCalledTimes(1);
});

it("reads exact hosted Plan terminal diagnostics using the session cookie", async () => {
  const api = await setup();
  hostedOrigin();
  api.setNativeGraphAccessToken("local-bearer");
  const fetch = vi.spyOn(globalThis, "fetch").mockResolvedValue(Response.json({ availability: "unavailable" }));
  const path = "/api/live/world-plan-edit/actions/11111111-1111-4111-8111-111111111111/terminal-diagnostic?world_id=managed";
  await api.authenticatedApiFetch(path);
  const [, init] = fetch.mock.calls[0];
  expect(init).toMatchObject({ credentials: "same-origin", redirect: "error", cache: "no-store" });
  expect(new Headers(init?.headers).has("Authorization")).toBe(false);
  await expect(api.authenticatedApiFetch(path + "&world_id=foreign")).rejects.toThrow(/exact same-origin/);
  expect(fetch).toHaveBeenCalledTimes(1);
});

it("sends hosted work-plan commands through exact same-origin routes", async () => {
  const api = await setup();
  hostedOrigin();
  api.setNativeGraphAccessToken("local-bearer");
  const fetch = vi.spyOn(globalThis, "fetch").mockImplementation(async () => Response.json({}));
  const id = "12345678-1234-1234-1234-123456789abc";
  const path = `/api/live/agent/worlds/managed/conversations/${id}/work-plans/${id}`;
  for (const [url, method] of [[path, "GET"], [path, "PUT"], [path + "/continue", "POST"]]) {
    await api.authenticatedApiFetch(url, { method, body: method === "GET" ? undefined : "{}" });
    const [sent, init] = fetch.mock.calls.at(-1)!;
    expect(sent).toBe(url);
    expect(init).toMatchObject({ method, credentials: "same-origin", redirect: "error" });
    expect(new Headers(init?.headers).has("Authorization")).toBe(false);
  }
  await expect(api.authenticatedApiFetch(path + "/continue", { method: "PUT", body: "{}" })).rejects.toThrow(/exact same-origin/);
  expect(fetch).toHaveBeenCalledTimes(3);
});

it("opens and reviews an exact Plan proposal with hosted cookies", async () => {
  const api = await setup();
  hostedOrigin();
  api.setNativeGraphAccessToken("local-bearer");
  const fetch = vi.spyOn(globalThis, "fetch").mockResolvedValue(Response.json({ fixture: true }));
  const path = "/api/live/agent/worlds/managed-a/plan-proposals/11111111-1111-4111-8111-111111111111/review";
  const init = { method: "POST", body: JSON.stringify({ command_id: "command", operation: "open" }) };

  await api.authenticatedApiFetch(path);
  await api.authenticatedApiFetch(path, init);
  for (const [, options] of fetch.mock.calls) {
    expect(options).toMatchObject({ credentials: "same-origin", redirect: "error", cache: "no-store" });
    expect(new Headers(options?.headers).has("Authorization")).toBe(false);
  }
  await expect(api.authenticatedApiFetch(path + "?world=foreign", init)).rejects.toThrow(/exact same-origin/);
  expect(fetch).toHaveBeenCalledTimes(2);
});

it("uses hosted session cookies for Manual knowledge preview and confirmation", async () => {
  const api = await setup();
  hostedOrigin();
  api.setNativeGraphAccessToken("local-bearer");
  const fetch = vi.spyOn(globalThis, "fetch").mockImplementation(async () => Response.json({}));
  const body = { worldId: "managed", campaignId: "managed", sourceRunId: "saved-build-run", proposals: [] };
  for (const phase of ["prepare", "commit"]) {
    const path = `/api/live/graph-authoring/${phase}`;
    await api.authenticatedApiFetch(path, { method: "POST", body: JSON.stringify(body) });
    const [url, init] = fetch.mock.calls.at(-1)!;
    expect(url).toBe(path);
    expect(init).toMatchObject({ credentials: "same-origin", cache: "no-store", redirect: "error" });
    expect(new Headers(init?.headers).has("Authorization")).toBe(false);
    await expect(api.authenticatedApiFetch(path, {
      method: "POST", body: JSON.stringify({ ...body, campaignId: "foreign" }),
    })).rejects.toThrow(/exact same-origin/);
  }
  expect(fetch).toHaveBeenCalledTimes(2);
});

it("selects a Play run through the exact hosted World route", async () => {
  const api = await setup();
  hostedOrigin();
  const fetch = vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(Response.json({}));
  const path = "/api/live/world-play-runs/v2/active?world_id=managed";
  const request = { method: "PUT", body: JSON.stringify({ run_id: "11111111-1111-4111-8111-111111111111" }) };
  await api.authenticatedApiFetch(path, request);
  expect(fetch.mock.calls[0]).toEqual([path, expect.objectContaining({
    method: "PUT", credentials: "same-origin", mode: "same-origin",
  })]);
  await expect(api.authenticatedApiFetch(path + "&world_id=foreign", request)).rejects.toThrow(/exact same-origin/);
  expect(fetch).toHaveBeenCalledTimes(1);
});

it("uses the hosted session for exact conversation recovery and receipt reads", async () => {
  const api = await setup();
  hostedOrigin();
  api.setNativeGraphAccessToken("local-only-fixture");
  const fetch = vi.spyOn(globalThis, "fetch").mockImplementation(async () => Response.json({}));
  const commandId = "11111111-1111-4111-8111-111111111111";
  const operationId = "22222222-2222-4222-8222-222222222222";
  const request = {
    schema: "dmb_agent_new_conversation_resolution_request_v1",
    resolution_operation_id: operationId,
    original_command: {
      world_id: "managed", command_id: commandId, expected_pointer_revision: 2,
      expected_active_conversation_id: null,
    },
    expected_current_pointer_revision: 3,
    expected_current_active_conversation_id: null,
  } as const;
  const path = `/api/live/agent/worlds/managed/conversation/commands/${commandId}`;
  const receipt = `${path}/resolutions/${operationId}?original_pointer_revision=2&original_active_conversation_id=null&current_pointer_revision=3&current_active_conversation_id=null`;
  await api.postWorldCommandResolution(request);
  await api.getWorldCommandResolution(request);
  expect(fetch).toHaveBeenNthCalledWith(1, path + "/resolve", expect.objectContaining({
    method: "POST", credentials: "same-origin",
  }));
  expect(fetch).toHaveBeenNthCalledWith(2, receipt, expect.objectContaining({ credentials: "same-origin" }));
  for (const [, init] of fetch.mock.calls) {
    expect(new Headers(init?.headers).has("Authorization")).toBe(false);
  }
  await expect(api.authenticatedApiFetch(receipt + "&current_pointer_revision=4")).rejects.toThrow(/exact same-origin/);
  expect(fetch).toHaveBeenCalledTimes(2);
});

it("checks recap names through the hosted World route", async () => {
  const api = await setup();
  hostedOrigin();
  const fetch = vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(Response.json({}));
  const path = "/api/live/recap-name-review";
  const request = { method: "POST", body: JSON.stringify({
    operation: "generate_recap_memory", managed_world_id: "managed", raw_text: "A keeper scouts Mireward.",
  }) };
  await api.authenticatedApiFetch(path, request);
  expect(fetch.mock.calls[0]).toEqual([path, expect.objectContaining({
    method: "POST", credentials: "same-origin", mode: "same-origin",
  })]);
  await expect(api.authenticatedApiFetch(path + "?world_id=foreign", request)).rejects.toThrow(/exact same-origin/);
  expect(fetch).toHaveBeenCalledTimes(1);
});

it("uses the hosted session for exact Worldbuilding evidence corrections", async () => {
  const api = await setup();
  hostedOrigin();
  const fetch = vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(Response.json({}));
  const path = "/api/live/extract-promote/runs/saved-run/evidence-corrections";
  const init = { method: "POST", body: JSON.stringify({ parentRunId: "saved-run" }) };
  await api.authenticatedApiFetch(path, init);
  expect(fetch).toHaveBeenCalledWith(path, expect.objectContaining({
    method: "POST", credentials: "same-origin", mode: "same-origin",
  }));
  await expect(api.authenticatedApiFetch(path + "?world_id=foreign", init)).rejects.toThrow(/exact same-origin/);
  expect(fetch).toHaveBeenCalledTimes(1);
});

it.each([
  "/api/live/graph-preview/extraction-runs/saved-run",
  "/api/live/graph-preview/extraction-runs/run%3Areviewed",
  "/api/live/graph-preview/extraction-runs/saved-run/build-context",
  "/api/live/graph-preview/extraction-runs/run%3Areviewed/build-context",
  "/api/live/extract-promote/runs/saved-run/review-package",
  "/api/live/extract-promote/runs/run%3Areviewed/review-package",
  "/api/live/extract-promote/runs/saved-run/frozen-source-spans",
  "/api/live/extract-promote/runs/run%3Areviewed/frozen-source-spans",
])("uses the hosted session for exact saved extraction reads at %s", async path => {
  const api = await setup();
  hostedOrigin();
  const fetch = vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(Response.json({}));
  await api.authenticatedApiFetch(path, { headers: { Authorization: "Bearer local-only-fixture" } });
  const [url, init] = fetch.mock.calls[0]!;
  expect(url).toBe(path);
  expect(init).toMatchObject({ credentials: "same-origin", mode: "same-origin" });
  expect(new Headers(init?.headers).has("Authorization")).toBe(false);
  await expect(api.authenticatedApiFetch(path + "?world_id=foreign")).rejects.toThrow(/exact same-origin/);
  expect(fetch).toHaveBeenCalledTimes(1);
});

it("reopens a Build extraction whose saved run ID contains a colon", async () => {
  const api = await setup();
  hostedOrigin();
  const fetch = vi.spyOn(globalThis, "fetch").mockResolvedValue(Response.json({}));
  const base = "/api/live/graph-preview/extraction-runs/";
  await api.getExtractionRunStatus("run:reviewed");
  expect(fetch).toHaveBeenCalledWith(base + "run%3Areviewed/build-context", expect.objectContaining({
    credentials: "same-origin", mode: "same-origin", redirect: "error",
  }));
  for (const invalid of ["run%2Freviewed", "run%253Areviewed", "run%3Freviewed"]) {
    await expect(api.authenticatedApiFetch(base + invalid + "/build-context")).rejects.toThrow(/exact same-origin/);
  }
  expect(fetch).toHaveBeenCalledTimes(1);
});

it("uses the hosted session for World Plan inventory and creation", async () => {
  const api = await setup();
  hostedOrigin();
  const fetch = vi.spyOn(globalThis, "fetch").mockImplementation(async () => Response.json({}));
  const path = "/api/live/workspace-documents/world-plans";
  const body = {
    schema_version: "dmb_workspace_document_create_v2", scope_mode: "world",
    world_id: "managed", title: "Plan",
  } as const;
  await api.listWorldOwnedPlans("managed");
  await api.createWorldOwnedPlan(body);
  expect(fetch).toHaveBeenNthCalledWith(1, path + "?world_id=managed", expect.objectContaining({
    credentials: "same-origin", mode: "same-origin",
  }));
  expect(fetch).toHaveBeenNthCalledWith(2, path, expect.objectContaining({
    method: "POST", credentials: "same-origin", mode: "same-origin",
  }));
  await expect(api.authenticatedApiFetch(path + "?world_id=foreign", {
    method: "POST", body: JSON.stringify(body),
  })).rejects.toThrow(/exact same-origin/);
  expect(fetch).toHaveBeenCalledTimes(2);
});

it("loads a historical recap with the hosted session for the selected World", async () => {
  const api = await setup();
  hostedOrigin();
  api.setNativeGraphAccessToken("local-only-fixture");
  const fetch = vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(Response.json({}));
  const path = "/api/live/graph-preview/extraction-runs/saved/recap-projection?managed_world_id=managed";
  await api.getHistoricalRecapWorldProjection("saved", "managed");
  expect(fetch).toHaveBeenCalledWith(path, expect.objectContaining({ credentials: "same-origin" }));
  expect(new Headers(fetch.mock.calls[0]?.[1]?.headers).has("Authorization")).toBe(false);
  await expect(api.authenticatedApiFetch(path + "&managed_world_id=foreign")).rejects.toThrow(/exact same-origin/);
  expect(fetch).toHaveBeenCalledTimes(1);
});

it.each([false, true])("routes recap evidence correction for hosted=%s", async (hosted) => {
  const api = await setup();
  if (hosted) hostedOrigin();
  api.setNativeGraphAccessToken("synthetic-local-token");
  const { correctRecapRunEvidence } = await import("./extractPromoteApi");
  const fetch = vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(
    Response.json({ message: "Fixture refusal" }, { status: 409 }),
  );
  await expect(correctRecapRunEvidence({
    parentRunId: "saved-run", parentCandidateSha256: "a".repeat(64), corrections: [],
  }, "managed")).rejects.toThrow("Fixture refusal");
  const [url, init] = fetch.mock.calls[0]!;
  const route = "/api/live/extract-promote/runs/saved-run/recap-evidence-corrections";
  expect(url).toBe(hosted ? route + "?managed_world_id=managed" : route);
  expect(new Headers(init?.headers).get("Authorization")).toBe(
    hosted ? null : "Bearer synthetic-local-token",
  );
});

it("reopens a saved image direction under its hosted World", async () => {
  const api = await setup();
  hostedOrigin();
  api.setNativeGraphAccessToken("local-bearer");
  const fetch = vi.spyOn(globalThis, "fetch").mockResolvedValue(Response.json({}));
  const path = "/api/live/media/images/preparations/aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee?world_id=elderwyld";
  await api.authenticatedApiFetch(path);
  expect(fetch.mock.calls[0][1]).toMatchObject({ credentials: "same-origin", cache: "no-store" });
  expect(new Headers(fetch.mock.calls[0][1]?.headers).has("Authorization")).toBe(false);
  await expect(api.authenticatedApiFetch(path + "&world_id=foreign")).rejects.toThrow(/exact same-origin/);
  expect(fetch).toHaveBeenCalledOnce();
});

it("reads hosted image model catalog pages under one World", async () => {
  const api = await setup();
  hostedOrigin();
  const fetch = vi.spyOn(globalThis, "fetch").mockResolvedValue(Response.json({ models: [] }));
  const path = "/api/live/media/images/catalog?cursor=page-2&world_id=elderwyld";
  await api.authenticatedApiFetch(path);
  expect(fetch.mock.calls[0][1]).toMatchObject({ credentials: "same-origin", cache: "no-store" });
  await expect(api.authenticatedApiFetch(path + "&world_id=foreign")).rejects.toThrow(/exact same-origin/);
  await expect(api.authenticatedApiFetch(path + "&unknown=value")).rejects.toThrow(/exact same-origin/);
  expect(fetch).toHaveBeenCalledOnce();
});

it("browses a hosted World library and exact private preview", async () => {
  const api = await setup();
  hostedOrigin();
  const fetch = vi.spyOn(globalThis, "fetch").mockResolvedValue(Response.json({ items: [] }));
  const path = "/api/live/media/images/library?world_id=elderwyld";
  await api.authenticatedApiFetch(path);
  await api.authenticatedApiFetch("/api/live/media/images/aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee");
  for (const [, init] of fetch.mock.calls) {
    expect(init).toMatchObject({ credentials: "same-origin", cache: "no-store" });
    expect(new Headers(init?.headers).has("Authorization")).toBe(false);
  }
  await expect(api.authenticatedApiFetch(path + "&before_id=orphan")).rejects.toThrow(/exact same-origin/);
  expect(fetch).toHaveBeenCalledTimes(2);
});

it("opens World Runbook inventory with the hosted session", async () => {
  const api = await setup();
  hostedOrigin();
  api.setNativeGraphAccessToken("local-only-fixture");
  const inventory = {
    schema_version: "dmb_world_owned_runbooks_list_v2",
    scope_mode: "world", world_id: "managed", records: [],
  };
  const fetch = vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(Response.json(inventory));
  await expect(api.listWorldOwnedRunbooks("managed")).resolves.toEqual(inventory);
  const [url, init] = fetch.mock.calls[0]!;
  expect(url).toBe("/api/live/workspace-documents/world-runbooks?world_id=managed");
  expect(init).toMatchObject({ credentials: "same-origin", mode: "same-origin" });
  expect(new Headers(init?.headers).has("Authorization")).toBe(false);
  await expect(api.authenticatedApiFetch(String(url) + "&world_id=foreign")).rejects.toThrow(/exact same-origin/);
  expect(fetch).toHaveBeenCalledTimes(1);
});

it("uses the hosted session for a pinned Runbook revision", async () => {
  const api = await setup();
  hostedOrigin();
  const fetch = vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(Response.json({}));
  const path = "/api/live/workspace-documents/world-runbooks/00000000-0000-4000-8000-000000000001/committed-revision/2?world_id=managed";
  const exact = path + "&expected_sha256=" + "a".repeat(64);
  await api.authenticatedApiFetch(exact);
  expect(fetch).toHaveBeenCalledWith(exact, expect.objectContaining({
    credentials: "same-origin", mode: "same-origin",
  }));
  await expect(api.authenticatedApiFetch(path)).rejects.toThrow(/exact same-origin/);
  expect(fetch).toHaveBeenCalledTimes(1);
});

it("uses hosted transport for the exact scene template read and cancel", async () => {
  const api = await setup();
  hostedOrigin();
  const fetch = vi.spyOn(globalThis, "fetch").mockImplementation(async () => Response.json({}));
  const root = "/api/live/combat/scene-templates";
  const path = root + "/11111111-1111-4111-8111-111111111111/scenes/scene%3Agate?world_id=managed";
  await api.authenticatedApiFetch(path);
  const cancel = root + "/cancel?world_id=managed";
  const request = { method: "POST", body: JSON.stringify({ schema_version: "dmb_scene_template_create_v1" }) };
  await api.authenticatedApiFetch(cancel, request);
  expect(fetch.mock.calls).toEqual([
    [path, expect.objectContaining({ credentials: "same-origin", mode: "same-origin" })],
    [cancel, expect.objectContaining({ method: "POST", credentials: "same-origin", mode: "same-origin" })],
  ]);
  await expect(api.authenticatedApiFetch(cancel + "&world_id=foreign", request)).rejects.toThrow(/exact same-origin/);
  expect(fetch).toHaveBeenCalledTimes(2);
});

it("uses hosted transport for exact run encounter routes and adoption pagination", async () => {
  const api = await setup();
  hostedOrigin();
  const fetch = vi.spyOn(globalThis, "fetch").mockImplementation(async () => Response.json({}));
  const id = "11111111-1111-4111-8111-111111111111";
  const root = `/api/live/combat/run-encounters/${id}/scenes/scene%3Agate`;
  const path = `${root}/encounters/${id}/mechanics-adoptions?world_id=managed&limit=5`;
  await api.authenticatedApiFetch(path);
  const materialize = root + "?world_id=managed";
  const request = { method: "POST", body: JSON.stringify({ schema_version: "dmb_scene_encounter_materialize_v1" }) };
  await api.authenticatedApiFetch(materialize, request);
  expect(fetch.mock.calls).toEqual([
    [path, expect.objectContaining({ credentials: "same-origin", mode: "same-origin" })],
    [materialize, expect.objectContaining({ method: "POST", credentials: "same-origin", mode: "same-origin" })],
  ]);
  await expect(api.authenticatedApiFetch(path + "&limit=6")).rejects.toThrow(/exact same-origin/);
  await expect(api.authenticatedApiFetch(materialize + "&limit=5", request)).rejects.toThrow(/exact same-origin/);
  expect(fetch).toHaveBeenCalledTimes(2);
});

it("reads the managed graph projection on the exact hosted route", async () => {
  const api = await setup();
  hostedOrigin();
  const fetch = vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(Response.json({}));
  const path = "/api/live/world-graph/managed-projection";
  const body = { schema: "dmb_managed_world_graph_projection_request_v1", managedWorldId: "managed" };
  const init = { method: "POST", body: JSON.stringify(body) };
  await api.authenticatedApiFetch(path, init);
  expect(fetch).toHaveBeenCalledWith(path, expect.objectContaining({
    method: "POST", credentials: "same-origin", mode: "same-origin",
  }));
  await expect(api.authenticatedApiFetch(path + "?world_id=foreign", init)).rejects.toThrow(/exact same-origin/);
  expect(fetch).toHaveBeenCalledTimes(1);
});

it("reads recap usage through the exact hosted revision route", async () => {
  const api = await setup();
  hostedOrigin();
  api.setNativeGraphAccessToken("local-only-fixture");
  const fetch = vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(Response.json({}));
  const path = "/api/live/graph-preview/extraction-runs/recap-run/usage?managed_world_id=managed&expected_run_revision=2";
  await api.authenticatedApiFetch(path);
  expect(fetch).toHaveBeenCalledWith(path, expect.objectContaining({ credentials: "same-origin" }));
  expect(new Headers(fetch.mock.calls[0]?.[1]?.headers).has("Authorization")).toBe(false);
  await expect(api.authenticatedApiFetch(path + "&expected_run_revision=3")).rejects.toThrow(/exact same-origin/);
  expect(fetch).toHaveBeenCalledTimes(1);
});

it("prepares and commits a hosted Build page containing saved artwork", async () => {
  const api = await setup();
  hostedOrigin();
  api.setNativeGraphAccessToken("local-only-fixture");
  const fetch = vi.spyOn(globalThis, "fetch").mockImplementation(async () => Response.json({}));
  const body = {
    document_id: "12345678-1234-1234-1234-123456789abc",
    markdown: "![Artwork](dmb-media:23456789-1234-1234-1234-123456789abc)",
    expected_revision: 2,
  };
  await api.prepareTiptapMarkdownWrite(body);
  await api.commitTiptapMarkdownWrite({ ...body, writer_confirm_token: "fixture" });
  for (const [index, phase] of ["prepare", "commit"].entries()) {
    const path = "/api/live/tiptap/markdown-write/" + phase;
    expect(fetch).toHaveBeenNthCalledWith(index + 1, path, expect.objectContaining({
      method: "POST", credentials: "same-origin", mode: "same-origin", redirect: "error",
    }));
    expect(new Headers(fetch.mock.calls[index][1]?.headers).has("Authorization")).toBe(false);
    await expect(api.authenticatedApiFetch(path + "?world_id=foreign", {
      method: "POST", body: JSON.stringify(body),
    })).rejects.toThrow(/exact same-origin/);
  }
  const plan = { ...body, world_id: "managed", scope_mode: "world" } as const;
  await api.prepareTiptapMarkdownWrite({ ...plan, schema_version: "dmb_tiptap_markdown_write_prepare_v2" });
  await api.commitWorldOwnedPlanMarkdownWrite({
    ...plan, schema_version: "dmb_tiptap_markdown_write_commit_v2", writer_confirm_token: "fixture",
  });
  expect(fetch).toHaveBeenCalledTimes(4);
  for (const call of fetch.mock.calls.slice(2)) {
    expect(call[1]).toMatchObject({ credentials: "same-origin", mode: "same-origin" });
    expect(new Headers(call[1]?.headers).has("Authorization")).toBe(false);
  }
});


const nativeRecapContextBody = {
  managed_world_id: "managed-a", campaign_id: "campaign-a", session_id: "session-8", run_id: "run-a",
  expected_run_revision: 2, candidate_sha256: "a".repeat(64), source_artifact_id: "source-a",
  source_revision_id: "11111111-1111-4111-8111-111111111111", source_sha256: "b".repeat(64),
};
const nativeRecapExtensionBody = {
  managed_world_id: "managed-a", extension_id: "extension-a", original_admission_id: "admission-a",
  source_artifact_id: "native-source-a", source_revision_id: "native-revision-a",
  expected_body_sha256: "b".repeat(64), expected_parent_revision_id: "rev:parent", expected_source_authority_epoch: 3,
  created_at: "2026-11-19T20:00:00Z", spans: [{ client_ref: "witness-a", evidence_role: "support",
    start_byte: 2, end_byte: 8, expected_slice_sha256: "c".repeat(64) }],
};
const nativeRecapPublicationRoutes = [
  ["context", "/api/live/extract-promote/native-recap-context", nativeRecapContextBody],
  ["evidence extension", "/api/live/source-statements/extend-evidence", nativeRecapExtensionBody],
] as const;

it.each(nativeRecapPublicationRoutes)("authenticates exact local native Recap %s without changing its body", async (_name, path, body) => {
  const api = await setup(); api.setNativeGraphAccessToken("recap-local-token");
  const fetch = vi.spyOn(globalThis, "fetch").mockResolvedValue(Response.json({ fixture: true }));
  await api.authenticatedApiFetch(path, { method: "POST", body: JSON.stringify(body) });
  expect(fetch).toHaveBeenCalledTimes(1);
  expect(fetch.mock.calls[0][0]).toBe(path);
  expect(new Headers(fetch.mock.calls[0][1]?.headers).get("Authorization")).toBe("Bearer recap-local-token");
  expect(JSON.parse(String(fetch.mock.calls[0][1]?.body))).toEqual(body);
});

it.each(nativeRecapPublicationRoutes)("uses only secure same-origin cookies for native Recap %s", async (_name, path, body) => {
  const api = await setup(); api.setNativeGraphAccessToken("local-token"); hostedOrigin();
  const fetch = vi.spyOn(globalThis, "fetch").mockResolvedValue(Response.json({ fixture: true }));
  await api.authenticatedApiFetch(path, { method: "POST", body: JSON.stringify(body), credentials: "include", redirect: "follow",
    headers: { Authorization: "Bearer injected", "X-DMB-Graph-CSRF": "injected", Cookie: "injected", "X-DMS-Subject": "forged" } });
  expect(fetch).toHaveBeenCalledTimes(1);
  const init = fetch.mock.calls[0][1];
  expect(init).toMatchObject({ credentials: "same-origin", mode: "same-origin", redirect: "error", cache: "no-store" });
  for (const name of ["Authorization", "X-DMB-Graph-CSRF", "Cookie", "X-DMS-Subject"]) expect(new Headers(init?.headers).has(name)).toBe(false);
  expect(JSON.parse(String(init?.body))).toEqual(body);
});

it.each(nativeRecapPublicationRoutes)("blocks remote, lookalike, wrong-method and malformed native Recap %s requests", async (_name, path, body) => {
  const api = await setup(); hostedOrigin(); const fetch = vi.spyOn(globalThis, "fetch");
  for (const candidate of [path + "/", path + "-extra", path + "?world_id=foreign", path + "#fragment",
    path.replace("native-recap-context", "%6eative-recap-context").replace("extend-evidence", "%65xtend-evidence"),
    path.replace("/api/live/", "/api/live/./"), "https://buddy.example" + path, "//outside.invalid" + path]) {
    await expect(api.authenticatedApiFetch(candidate, { method: "POST", body: JSON.stringify(body) })).rejects.toThrow();
  }
  await expect(api.authenticatedApiFetch(path, { method: "GET" })).rejects.toThrow();
  await expect(api.authenticatedApiFetch(path, { method: "POST", body: "{}" })).rejects.toThrow();
  await expect(api.authenticatedApiFetch(path, { method: "POST", body: JSON.stringify({ ...body, managed_world_id: " " }) })).rejects.toThrow();
  expect(fetch).not.toHaveBeenCalled();
});

it("renews a local session once for the exact read-only Recap context", async () => {
  const api = await setup(); let boots = 0; const bodies: string[] = [];
  vi.spyOn(globalThis, "fetch").mockImplementation(async (url, init) => {
    if (String(url) === "/api/live/agent/local-session") {
      if (init?.method === "POST") return Response.json({ status: "active", csrf_token: `csrf-${++boots}` });
      return new Response(null, { status: 401 });
    }
    bodies.push(String(init?.body));
    return bodies.length === 1 ? Response.json({ detail: { code: "graph_auth_required" } }, { status: 401 }) : Response.json({ fixture: true });
  });
  await expect(api.authenticatedApiFetch(nativeRecapPublicationRoutes[0][1], {
    method: "POST", body: JSON.stringify(nativeRecapContextBody),
  })).resolves.toMatchObject({ response: { ok: true } });
  expect(boots).toBe(2); expect(bodies).toEqual([JSON.stringify(nativeRecapContextBody), JSON.stringify(nativeRecapContextBody)]);
});

it("never automatically replays a local evidence-extension mutation after auth rejection or response loss", async () => {
  const api = await setup(); api.setNativeGraphAccessToken("local-token");
  const fetch = vi.spyOn(globalThis, "fetch")
    .mockResolvedValueOnce(Response.json({ detail: { code: "graph_auth_required" } }, { status: 401 }))
    .mockRejectedValueOnce(new TypeError("lost response"));
  const init = { method: "POST", body: JSON.stringify(nativeRecapExtensionBody) };
  expect((await api.authenticatedApiFetch(nativeRecapPublicationRoutes[1][1], init)).response.status).toBe(401);
  expect(fetch).toHaveBeenCalledTimes(1);
  await expect(api.authenticatedApiFetch(nativeRecapPublicationRoutes[1][1], init)).rejects.toThrow("lost response");
  expect(fetch).toHaveBeenCalledTimes(2);
});

// Transport-only packets exercise the mounted path/body gate, not backend
// admission or signed-plan verification (covered by nativeManualKnowledgeApi).
const manualSource={managedWorldId:'managed-a',nativeWorldId:'space:a',bindingVersion:3,
 documentId:'20000000-0000-4000-8000-000000000002',documentRevision:2,bodySha256:'a'.repeat(64),
 runId:'30000000-0000-4000-8000-000000000003',runRevision:7,appSourceArtifactId:'app:one',
 appSourceRevisionId:'40000000-0000-4000-8000-000000000004',spanIndexSha256:'b'.repeat(64)};
const manualReview={schema:'dmb_native_manual_prepare_v1',source:manualSource,
 operationId:'10000000-0000-4000-8000-000000000001',createdAt:'2026-11-20T04:00:00.123Z',
 expectedParentRevisionId:'rev:a',expectedSourceAuthorityEpoch:1,witness:{},operation:{kind:'object'}};
const nativeManualRoutes=[
 ['/api/live/graph-authoring/native-manual/context',{schema:'dmb_native_manual_context_v1',managedWorldId:manualSource.managedWorldId,documentId:manualSource.documentId,documentRevision:2,bodySha256:manualSource.bodySha256,runId:manualSource.runId,runRevision:7}],
 ['/api/live/graph-authoring/native-manual/prepare',manualReview],
 ['/api/live/graph-authoring/native-manual/confirm',{schema:'dmb_native_manual_confirm_v1',plan:{schema:'dmb_native_manual_plan_v1',token:'test-only-token',review:manualReview,publication:{space_id:'space:a',publication_id:manualReview.operationId}}}],
 ['/api/live/graph-authoring/native-profile-transition/prepare',{schema:'dmb_native_profile_transition_prepare_v1',managedWorldId:'managed-a',expectedNativeWorldId:'space:a',expectedBindingVersion:3,expectedParentRevisionId:'rev:a',publicationId:'profile:a'}],
 ['/api/live/graph-authoring/native-profile-transition/confirm',{schema:'dmb_native_profile_transition_confirm_v1',plan:{schema:'dmb_native_profile_transition_plan_v1',token:'test-only-token',managedWorldId:'managed-a',nativeWorldId:'space:a',bindingVersion:3,request:{space_id:'space:a',publication_id:'profile:a',expected_parent_revision_id:'rev:a'}}}],
] as const;
it.each(nativeManualRoutes)('authenticates exact local native manual/profile transport %s',async(path,body)=>{
 const api=await setup();api.setNativeGraphAccessToken('local-test-token');const fetch=vi.spyOn(globalThis,'fetch').mockResolvedValue(Response.json({ok:true}));
 await api.authenticatedApiFetch(path,{method:'POST',body:JSON.stringify(body)});
 expect(fetch).toHaveBeenCalledTimes(1);expect(fetch.mock.calls[0][0]).toBe(path);expect(new Headers(fetch.mock.calls[0][1]?.headers).get('Authorization')).toBe('Bearer local-test-token');
 expect(fetch.mock.calls[0][1]).toMatchObject({credentials:'same-origin',redirect:'error'});expect(JSON.parse(String(fetch.mock.calls[0][1]?.body))).toEqual(body);
});
it.each(nativeManualRoutes)('uses only same-origin hosted cookies for native manual/profile %s',async(path,body)=>{
 const api=await setup();hostedOrigin();api.setNativeGraphAccessToken('must-not-leak');const fetch=vi.spyOn(globalThis,'fetch').mockResolvedValue(Response.json({ok:true}));
 await api.authenticatedApiFetch(path,{method:'POST',body:JSON.stringify(body),credentials:'include',redirect:'follow',headers:{Authorization:'Bearer forged','X-DMB-Graph-CSRF':'forged','X-DMS-Subject':'forged-owner','Content-Type':'application/json'}});
 expect(fetch).toHaveBeenCalledTimes(1);expect(fetch.mock.calls[0][0]).toBe(path);expect(fetch.mock.calls[0][1]).toMatchObject({credentials:'same-origin',redirect:'error',mode:'same-origin',cache:'no-store'});
 const headers=new Headers(fetch.mock.calls[0][1]?.headers);expect(headers.has('Authorization')).toBe(false);expect(headers.has('X-DMB-Graph-CSRF')).toBe(false);expect(headers.has('X-DMS-Subject')).toBe(false);
 expect(JSON.parse(String(fetch.mock.calls[0][1]?.body))).toEqual(body);
});
it.each([
 '/api/live/graph-authoring/native-manual/prepare-extra','/api/live/graph-authoring/native-manual/prepare/',
 '/api/live/graph-authoring/native-manual/prepare?extra=1','/api/live/graph-authoring/native-manual/%70repare',
 '/api/live/graph-authoring/native-manual/../native-manual/prepare','https://buddy.example/api/live/graph-authoring/native-manual/prepare',
 '//outside.invalid/api/live/graph-authoring/native-profile-transition/confirm','/api/live/graph-authoring/native-profile-transition/context',
])('blocks hosted native manual/profile lookalike %s before fetch',async path=>{
 const api=await setup();hostedOrigin();const fetch=vi.spyOn(globalThis,'fetch');await expect(api.authenticatedApiFetch(path,{method:'POST',body:JSON.stringify(manualReview)})).rejects.toThrow();expect(fetch).not.toHaveBeenCalled();
});
it.each(nativeManualRoutes)('rejects malformed hosted native manual/profile packet %s',async(path)=>{
 const api=await setup();hostedOrigin();const fetch=vi.spyOn(globalThis,'fetch');await expect(api.authenticatedApiFetch(path,{method:'POST',body:'{}'})).rejects.toThrow();expect(fetch).not.toHaveBeenCalled();
});
it.each(nativeManualRoutes.filter(([path])=>!path.endsWith('/context')))('never automatically replays native manual/profile mutation %s after auth failure',async(path,body)=>{
 const api=await setup();let mutations=0;const fetch=vi.spyOn(globalThis,'fetch').mockImplementation(async(url,init)=>{
  if(String(url)==='/api/live/agent/local-session')return init?.method==='POST'?Response.json({status:'active',csrf_token:'csrf-once'}):new Response(null,{status:401});
  mutations++;return Response.json({detail:{code:'graph_auth_csrf_rejected'}},{status:401});
 });
 await api.authenticatedApiFetch(path,{method:'POST',body:JSON.stringify(body)});expect(mutations).toBe(1);expect(fetch.mock.calls.filter(([url])=>String(url)===path)).toHaveLength(1);
});
it('rejects remote API bases for native manual transport before any credential dispatch',async()=>{
 const api=await setup('https://outside.invalid');api.setNativeGraphAccessToken('must-not-leak');const fetch=vi.spyOn(globalThis,'fetch');await expect(api.authenticatedApiFetch(nativeManualRoutes[0][0],{method:'POST',body:JSON.stringify(nativeManualRoutes[0][1])})).rejects.toThrow(/loopback/);expect(fetch).not.toHaveBeenCalled();
});


it.each(["local", "hosted"])("opens saved related recap pages through claim-bound GET on %s", async (destination) => {
  const api = await setup();
  if (destination === "hosted") hostedOrigin();
  api.setNativeGraphAccessToken("synthetic-managed-graph-token");
  const fetch = vi.spyOn(globalThis, "fetch").mockImplementation(async () => Response.json({ content: "Exact saved bytes." }));
  const request = {
    schema: "dmb_recap_context_read_request_v2" as const,
    worldId: "native", campaignId: "", scopeMode: "world" as const, revisionPin: "original-revision",
    contextAnchorId: "dm-context-anchor:v2:exact", maxChars: 12000, focus: { kind: "none" as const, sessionId: null, campaignId: null }, admissibility: "gm" as const,
    continuation: "recap-page:v2:second",
  };
  await expect(api.postWorldGraphRecapContextReadV2(request, {
    worldId: "managed", turnId: "11111111-1111-4111-8111-111111111111", claimId: "claim / original",
  })).resolves.toEqual({ content: "Exact saved bytes." });
  expect(fetch).toHaveBeenCalledTimes(1);
  const [url, init] = fetch.mock.calls[0]!;
  const parsed = new URL(String(url), "http://localhost");
  expect(parsed.pathname).toBe("/api/live/agent/worlds/managed/conversation/turns/11111111-1111-4111-8111-111111111111/graph-evidence");
  expect([...parsed.searchParams]).toEqual([
    ["claim_id", "claim / original"], ["anchor_id", request.contextAnchorId], ["continuation", request.continuation],
  ]);
  expect(init?.method ?? "GET").toBe("GET");
  expect(init?.body).toBeUndefined();
  expect(new Headers(init?.headers).get("Authorization")).toBe(destination === "hosted" ? null : "Bearer synthetic-managed-graph-token");
});

it.each([403, 404, 409, 500, "network"])("never falls back to public recap POST after saved GET %s", async (failure) => {
  const api = await setup();
  api.setNativeGraphAccessToken("synthetic-managed-graph-token");
  const fetch = vi.spyOn(globalThis, "fetch").mockImplementation(async () => {
    if (failure === "network") throw new TypeError("Offline");
    return Response.json({ detail: { code: "source_passage_not_found" } }, { status: failure });
  });
  await expect(api.postWorldGraphRecapContextReadV2({
    schema: "dmb_recap_context_read_request_v2", worldId: "native", campaignId: "", scopeMode: "world",
    revisionPin: "saved-revision", contextAnchorId: "dm-context-anchor:v2:exact", maxChars: 12000, focus: { kind: "none" as const, sessionId: null, campaignId: null }, admissibility: "gm" as const,
  }, { worldId: "managed", turnId: "11111111-1111-4111-8111-111111111111", claimId: "claim" })).rejects.toThrow();
  expect(fetch).toHaveBeenCalledTimes(1);
  expect(String(fetch.mock.calls[0]![0])).toContain("/graph-evidence?");
  expect(fetch.mock.calls[0]![1]?.method ?? "GET").toBe("GET");
});
