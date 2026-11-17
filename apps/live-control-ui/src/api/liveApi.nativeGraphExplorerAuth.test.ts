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
  ["complete object", "/api/live/native-graph-inspection/complete-object", {
    scope: entityInspectionBody.scope,
    request: {
      schema: "dmb_world_graph_object_projection_request_v1",
      worldId: "managed-a", scopeMode: "world", campaignId: "",
      revisionPin: "revision-a", nodeId: "entity-a", admissibility: "gm",
    },
  }],
  ["published recap", "/api/live/native-source-inspection/published-recap", {
    managed_world_id: "managed-a", campaign_id: "campaign-a", session_id: "session-a",
  }],
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

it("opens saved World citations with session cookies and exact selectors", async () => {
  const api = await setup();
  hostedOrigin();
  api.setNativeGraphAccessToken("local-bearer");
  const fetch = vi.spyOn(globalThis, "fetch").mockImplementation(async () => Response.json({}));
  const root = "/api/live/agent/worlds/managed";
  const id = "12345678-1234-1234-1234-123456789abc";
  const turn = `${root}/conversation/turns/${id}/graph-evidence`;
  const action = `${root}/plan-proposals/${id}/graph-evidence`;
  const evidence = "?claim_id=claim&anchor_id=anchor";
  const recap = "?claim_id=claim&anchor_id=dm-context-anchor%3Av2%3Arecap&continuation=recap-page%3Av2%3A2";

  for (const path of [turn + evidence, turn + recap, action + evidence]) {
    await api.authenticatedApiFetch(path);
    const [url, init] = fetch.mock.calls.at(-1)!;
    expect(url).toBe(path);
    expect(init).toMatchObject({ credentials: "same-origin", cache: "no-store", redirect: "error" });
    expect(new Headers(init?.headers).has("Authorization")).toBe(false);
  }

  await expect(api.authenticatedApiFetch(action + recap)).rejects.toThrow(/exact same-origin/);
  await expect(api.authenticatedApiFetch(turn + evidence + "&anchor_id=another")).rejects.toThrow(/exact same-origin/);
  expect(fetch).toHaveBeenCalledTimes(3);
});

it("reads exact hosted conversation recovery without the local bearer", async () => {
  const api = await setup();
  hostedOrigin();
  api.setNativeGraphAccessToken("local-bearer");
  const fetch = vi.spyOn(globalThis, "fetch").mockImplementation(async () => Response.json({ status: "absent" }));
  const commandId = "12345678-1234-1234-1234-123456789abc";
  const operationId = "22345678-1234-1234-1234-123456789abc";
  await api.getWorldCommandResolution({
    schema: "dmb_agent_new_conversation_resolution_request_v1",
    original_command: { world_id: "managed", command_id: commandId,
      expected_pointer_revision: 0, expected_active_conversation_id: null },
    resolution_operation_id: operationId, expected_current_pointer_revision: 1,
    expected_current_active_conversation_id: null,
  });
  const [url, init] = fetch.mock.calls[0]!;
  expect(url).toBe(`/api/live/agent/worlds/managed/conversation/commands/${commandId}/resolutions/${operationId}?original_pointer_revision=0&original_active_conversation_id=null&current_pointer_revision=1&current_active_conversation_id=null`);
  expect(init).toMatchObject({ credentials: "same-origin", cache: "no-store", redirect: "error" });
  expect(new Headers(init?.headers).has("Authorization")).toBe(false);
  await expect(api.authenticatedApiFetch(String(url) + "&current_pointer_revision=2")).rejects.toThrow(/exact same-origin/);
  expect(fetch).toHaveBeenCalledTimes(1);
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

it("sends hosted work-plan commands through exact same-origin routes", async () => {
  const api = await setup();
  hostedOrigin();
  api.setNativeGraphAccessToken("local-bearer");
  const fetch = vi.spyOn(globalThis, "fetch").mockImplementation(async () => Response.json({}));
  const id = "12345678-1234-1234-1234-123456789abc";
  const path = `/api/live/agent/worlds/managed/conversations/${id}/work-plans/${id}`;
  for (const [url, method] of [[path, "PUT"], [path + "/continue", "POST"]]) {
    await api.authenticatedApiFetch(url, { method, body: "{}" });
    const [sent, init] = fetch.mock.calls.at(-1)!;
    expect(sent).toBe(url);
    expect(init).toMatchObject({ method, credentials: "same-origin", redirect: "error" });
    expect(new Headers(init?.headers).has("Authorization")).toBe(false);
  }
  await expect(api.authenticatedApiFetch(path + "/continue", { method: "PUT", body: "{}" })).rejects.toThrow(/exact same-origin/);
  expect(fetch).toHaveBeenCalledTimes(2);
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

it("reads saved PDF reviews on hosted Buddy without a local bearer", async () => {
  const api = await setup();
  hostedOrigin();
  api.setNativeGraphAccessToken("local-bearer");
  const fetch = vi.spyOn(globalThis, "fetch").mockImplementation(async () => Response.json({ reviews: [] }));
  const signal = new AbortController().signal;
  await expect(api.listPdfStatblockReviews("elderwyld", signal)).resolves.toEqual([]);
  const [url, init] = fetch.mock.calls[0]!;
  expect(url).toBe("/api/live/agent/worlds/elderwyld/build-pdf-sources/statblock-reviews");
  expect(init).toMatchObject({ signal, credentials: "same-origin", cache: "no-store", redirect: "error" });
  expect(new Headers(init?.headers).has("Authorization")).toBe(false);
  await expect(api.authenticatedApiFetch(String(url), { method: "POST", body: "{}" })).rejects.toThrow(/exact same-origin/);
  const detail = String(url) + "/12345678-1234-1234-1234-123456789abc";
  const published = detail + "/publication/statblock?draft_id=12345678-1234-1234-1234-123456789abc&revision_id=rev_saved";
  for (const path of [detail, detail + "/publication", published]) {
    await api.authenticatedApiFetch(path);
    const [sent, options] = fetch.mock.calls.at(-1)!;
    expect(sent).toBe(path);
    expect(options).toMatchObject({ credentials: "same-origin", cache: "no-store", redirect: "error" });
    expect(new Headers(options?.headers).has("Authorization")).toBe(false);
  }
  await expect(api.authenticatedApiFetch(detail + "?world_id=foreign")).rejects.toThrow(/exact same-origin/);
  await expect(api.authenticatedApiFetch(published + "&revision_id=another")).rejects.toThrow(/exact same-origin/);
  await api.authenticatedApiFetch(detail, {
    method: "PUT", body: JSON.stringify({ expected_revision: 1, definition: {}, regions: [] }),
  });
  expect(fetch.mock.calls.at(-1)?.[1]).toMatchObject({ method: "PUT", credentials: "same-origin", redirect: "error" });
  await expect(api.authenticatedApiFetch(detail, { method: "PUT", body: "{}" })).rejects.toThrow(/exact same-origin/);
  expect(fetch).toHaveBeenCalledTimes(5);
});

it("opens and checks saved PDF regions through hosted session transport", async () => {
  const api = await setup();
  hostedOrigin();
  api.setNativeGraphAccessToken("local-bearer");
  const fetch = vi.spyOn(globalThis, "fetch").mockImplementation(async () => Response.json({}));
  const root = "/api/live/agent/worlds/elderwyld/build-pdf-sources";
  const request = { method: "POST", body: JSON.stringify({ source_revision_id: "retained-revision" }) };
  for (const route of ["open", "region:validate"]) {
    await api.authenticatedApiFetch(`${root}/${route}`, request);
    const [url, init] = fetch.mock.calls.at(-1)!;
    expect(url).toBe(`${root}/${route}`);
    expect(init).toMatchObject({ credentials: "same-origin", cache: "no-store", redirect: "error" });
    expect(new Headers(init?.headers).has("Authorization")).toBe(false);
  }
  for (const route of ["ocr", "review"]) {
    await expect(api.authenticatedApiFetch(`${root}/${route}`, request)).rejects.toThrow(/exact same-origin/);
  }
  expect(fetch).toHaveBeenCalledTimes(2);
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

it.each([
  ["progress", { progress: {} }],
  ["rebase", { target_playable_revision: 4, target_playable_content_sha256: "a".repeat(64) }],
])("writes Play %s through the exact hosted World route", async (operation, payload) => {
  const api = await setup();
  hostedOrigin();
  const fetch = vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(Response.json({}));
  const runId = "11111111-1111-4111-8111-111111111111";
  const path = `/api/live/world-play-runs/v2/${runId}/${operation}?world_id=managed`;
  const request = { method: "PUT", body: JSON.stringify({ expected_run_revision: 2, ...payload }) };
  await api.authenticatedApiFetch(path, request);
  expect(fetch.mock.calls[0]).toEqual([path, expect.objectContaining({
    method: "PUT", credentials: "same-origin", mode: "same-origin",
  })]);
  await expect(api.authenticatedApiFetch(path + "&world_id=foreign", request)).rejects.toThrow(/exact same-origin/);
  expect(fetch).toHaveBeenCalledTimes(1);
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

it.each([
  "/api/live/graph-preview/extraction-runs/saved-run/usage?managed_world_id=managed&expected_run_revision=2",
  "/api/live/graph-preview/build-recap-launches/00000000-0000-4000-8000-000000000002?document_id=00000000-0000-4000-8000-000000000001&managed_world_id=managed",
])("uses hosted transport for exact saved recap reads at %s", async path => {
  const api = await setup();
  hostedOrigin();
  const fetch = vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(Response.json({}));
  await api.authenticatedApiFetch(path);
  expect(fetch).toHaveBeenCalledWith(path, expect.objectContaining({
    credentials: "same-origin", mode: "same-origin",
  }));
  await expect(api.authenticatedApiFetch(path + "&managed_world_id=foreign")).rejects.toThrow(/exact same-origin/);
  expect(fetch).toHaveBeenCalledTimes(1);
});

it("reads exact World Threat mechanics through hosted transport", async () => {
  const api = await setup();
  hostedOrigin();
  const fetch = vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(Response.json({}));
  const body = {
    schema: "dmb_threat_query_hydration_request_v1" as const,
    worldId: "managed", scopeMode: "world" as const, campaignId: null,
    revisionPin: "rev:exact", queryText: "Threat",
  };
  await api.postThreatQueryHydration(body);
  expect(fetch).toHaveBeenCalledWith("/api/live/threats/query-hydration", expect.objectContaining({
    method: "POST", credentials: "same-origin", mode: "same-origin",
  }));
  await expect(api.postThreatQueryHydration({ ...body, scopeMode: "campaign", campaignId: "other" }))
    .rejects.toThrow(/exact same-origin/);
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

it.each([
  "/api/live/graph-preview/extraction-runs/saved-run",
  "/api/live/graph-preview/extraction-runs/saved-run/build-context",
  "/api/live/extract-promote/runs/saved-run/review-package",
  "/api/live/extract-promote/runs/saved-run/frozen-source-spans",
  "/api/live/extract-promote/runs/saved-run/worldbuilding-publication-coverage",
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
