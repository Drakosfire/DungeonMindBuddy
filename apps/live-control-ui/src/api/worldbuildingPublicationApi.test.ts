import { afterEach, expect, it, vi } from "vitest";
import * as live from "./liveApi";
import {confirmWorldbuilding, getWorldbuildingCapabilities, prepareWorldbuilding, type WorldbuildingPlan} from "./worldbuildingPublicationApi";
afterEach(() => vi.restoreAllMocks());
it("uses authenticated transport and exact existing-World contracts without stripping the sealed plan", async () => {
  const fetch = vi.spyOn(live, "authenticatedApiFetch").mockResolvedValue({response: new Response("{}"), csrf: "csrf", requestEpoch: 1});
  await getWorldbuildingCapabilities();
  expect(fetch).toHaveBeenLastCalledWith("/api/live/extract-promote/worldbuilding/capabilities", undefined);
  fetch.mockResolvedValue({response: new Response("{}"), csrf: "csrf", requestEpoch: 1});
  await prepareWorldbuilding({runId: "r", expectedParentRevisionId: "rev:1", dispositions: [{assertionId: "n", decision: "bind_existing", targetNodeId: "loc_3"}]});
  expect(JSON.parse(String(fetch.mock.calls[1][1]?.body))).toEqual({schema: "dmb_worldbuilding_write_plan_prepare_request_v1", runId: "r", expectedParentRevisionId: "rev:1", dispositions: [{assertionId: "n", decision: "bind_existing", targetNodeId: "loc_3"}]});
  const plan = {planId: "p", prepareBinding: "opaque", unknownServerSealedField: {keep: true}} as unknown as WorldbuildingPlan;
  fetch.mockResolvedValue({response: new Response("{}"), csrf: "csrf", requestEpoch: 1});
  await confirmWorldbuilding(plan);
  expect(JSON.parse(String(fetch.mock.calls[2][1]?.body))).toEqual({schema: "dmb_worldbuilding_write_plan_confirm_request_v1", plan});
});
it("preserves stale-head error code without retrying", async () => {
  const fetch = vi.spyOn(live, "authenticatedApiFetch").mockResolvedValue({response: new Response(JSON.stringify({code: "stale_parent_revision", message: "Head changed"}), {status: 409}), csrf: null, requestEpoch: 1});
  await expect(prepareWorldbuilding({runId: "r", expectedParentRevisionId: "rev:old", dispositions: []})).rejects.toMatchObject({status: 409, code: "stale_parent_revision", message: "Head changed"});
  expect(fetch).toHaveBeenCalledOnce();
});

// Exercise the actual authorization classifier and helper; only global fetch is mocked.
const endpoints = ["capabilities", "prepare", "confirm"] as const;
async function realClient(base = "") {
  vi.resetModules(); vi.stubEnv("VITE_LIVE_API_BASE_URL", base);
  return {live: await import("./liveApi"), api: await import("./worldbuildingPublicationApi")};
}
async function callEndpoint(client: Awaited<ReturnType<typeof realClient>>["api"], endpoint: typeof endpoints[number]) {
  if (endpoint === "capabilities") return client.getWorldbuildingCapabilities();
  if (endpoint === "prepare") return client.prepareWorldbuilding({runId: "run", expectedParentRevisionId: "rev:1", dispositions: [{assertionId: "n", decision: "defer"}]});
  return client.confirmWorldbuilding({planId: "sealed-plan"} as WorldbuildingPlan);
}
afterEach(() => {vi.unstubAllEnvs(); vi.resetModules();});
it.each(endpoints)("authorizes %s through the real helper with configured bearer", async endpoint => {
  const client = await realClient(); client.live.setNativeGraphAccessToken("synthetic-test-credential");
  const fetch = vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response("{}"));
  try {
    await callEndpoint(client.api, endpoint);
    expect(fetch).toHaveBeenCalledOnce();
    const [url, init] = fetch.mock.calls[0];
    expect(url).toBe(`/api/live/extract-promote/worldbuilding/${endpoint}`);
    expect(new Headers(init?.headers).get("Authorization")).toBe("Bearer synthetic-test-credential");
    expect(init?.credentials).toBe("same-origin"); expect(init?.redirect).toBe("error");
  } finally {client.live.setNativeGraphAccessToken(null);}
});
it("restores a local session and attaches CSRF to explicit prepare/confirm only", async () => {
  const client = await realClient();
  const fetch = vi.spyOn(globalThis, "fetch").mockImplementation(async url => String(url).endsWith("/agent/local-session")
    ? Response.json({status: "active", csrf_token: "synthetic-test-csrf"}) : new Response("{}"));
  for (const endpoint of endpoints) await callEndpoint(client.api, endpoint);
  expect(fetch).toHaveBeenCalledTimes(4);
  expect(fetch.mock.calls[0][0]).toBe("/api/live/agent/local-session");
  expect(new Headers(fetch.mock.calls[1][1]?.headers).get("X-DMB-Graph-CSRF")).toBeNull();
  for (const call of fetch.mock.calls.slice(2)) {
    expect(new Headers(call[1]?.headers).get("X-DMB-Graph-CSRF")).toBe("synthetic-test-csrf");
    expect(call[1]?.method).toBe("POST");
  }
});
it.each(endpoints)("blocks nonloopback %s before fetch", async endpoint => {
  const client = await realClient("https://untrusted.example.invalid"); client.live.setNativeGraphAccessToken("synthetic-test-credential");
  const fetch = vi.spyOn(globalThis, "fetch");
  try {
    await expect(callEndpoint(client.api, endpoint)).rejects.toMatchObject({message: expect.stringContaining("loopback")});
    expect(fetch).not.toHaveBeenCalled();
  } finally {client.live.setNativeGraphAccessToken(null);}
});
it.each(["prepare", "confirm"] as const)("does not automatically retry %s after a GM auth rejection", async endpoint => {
  const client = await realClient();
  const fetch = vi.spyOn(globalThis, "fetch")
    .mockResolvedValueOnce(Response.json({status: "active", csrf_token: "synthetic-test-csrf"}))
    .mockResolvedValueOnce(Response.json({detail: {code: "graph_auth_csrf_rejected"}}, {status: 403}))
    .mockResolvedValueOnce(Response.json({status: "active", csrf_token: "refreshed-test-csrf"}));
  await expect(callEndpoint(client.api, endpoint)).rejects.toMatchObject({status: 403});
  // Existing helper may refresh the local session; it must not resend a publication mutation.
  expect(fetch).toHaveBeenCalledTimes(3);
  expect(fetch.mock.calls.filter(c => String(c[0]).endsWith(`/${endpoint}`))).toHaveLength(1);
});

it("preserves a configured-bearer rejection without refreshing or retrying publication", async () => {
  const client = await realClient(); client.live.setNativeGraphAccessToken("synthetic-invalid-credential");
  const fetch = vi.spyOn(globalThis, "fetch").mockResolvedValue(Response.json({message: "GM authorization required", code: "graph_auth_required"}, {status: 401}));
  try {
    await expect(callEndpoint(client.api, "confirm")).rejects.toMatchObject({status: 401, code: "graph_auth_required"});
    expect(fetch).toHaveBeenCalledOnce();
  } finally {client.live.setNativeGraphAccessToken(null);}
});
