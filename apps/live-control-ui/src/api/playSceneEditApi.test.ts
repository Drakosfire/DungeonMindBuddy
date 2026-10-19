import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { listPlaySceneEdits, proposePlaySceneEdit, type PlaySceneEditRequest } from "./playSceneEditApi";
import { setNativeGraphAccessToken } from "./liveApi";
const run = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa";
const id = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb";
const digest = "a".repeat(64);
const basis = { edition_revision: 0, edition_revision_id: null, content_sha256: digest };
const request: PlaySceneEditRequest = { schema_version: "dmb_play_scene_edit_request_v1", run_revision: 1,
  content_basis: basis, scene_id: `scene:${run}`, instruction: "Synthetic scene edit" };
function record() { return { schema_version: "dmb_play_scene_edit_proposal_v1", world_id: "world", run_id: run,
  proposal_id: id, instruction: request.instruction, status: "pending", failure_code: null,
  created_at: "2026-10-19T00:00:00Z", updated_at: "2026-10-19T00:00:00Z", result: null,
  basis: { run_revision: 1, scene_id: request.scene_id, content_basis: basis, scene_note_sha256: null,
    origin: { playable_artifact_id: run, playable_revision: 1, playable_work_revision_id: run, playable_content_sha256: digest } } }; }
beforeEach(() => setNativeGraphAccessToken("synthetic-test-credential"));
afterEach(() => { vi.restoreAllMocks(); setNativeGraphAccessToken(null); });
it("authenticates proposal collection and exact POST with immutable request bytes", async () => {
  const fetch = vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(Response.json({ proposals: [record()] }))
    .mockResolvedValueOnce(Response.json(record()));
  expect(await listPlaySceneEdits("world", run)).toEqual([record()]);
  expect(await proposePlaySceneEdit("world", run, id, request)).toEqual(record());
  for (const [, init] of fetch.mock.calls) {
    expect(new Headers(init?.headers).get("Authorization")).toBe("Bearer synthetic-test-credential");
    expect(init?.credentials).toBe("same-origin");
    expect(init?.redirect).toBe("error");
    expect(init?.cache).toBe("no-store");
  }
  expect(fetch.mock.calls[1][1]?.body).toBe(JSON.stringify(request));
});
it("uses the existing cookie session with CSRF on the proposal POST", async () => {
  setNativeGraphAccessToken(null);
  const fetch = vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(Response.json({ status: "active", csrf_token: "synthetic-csrf" }))
    .mockResolvedValueOnce(Response.json(record()));
  await proposePlaySceneEdit("world", run, id, request);
  expect(fetch.mock.calls[0][0]).toBe("/api/live/agent/local-session");
  expect(new Headers(fetch.mock.calls[1][1]?.headers).get("X-DMB-Graph-CSRF")).toBe("synthetic-csrf");
  expect(fetch.mock.calls[1][1]?.credentials).toBe("same-origin");
  expect(fetch).toHaveBeenCalledTimes(2);
});
it("does not retry an uncertain proposal POST", async () => {
  const fetch = vi.spyOn(globalThis, "fetch").mockRejectedValue(new TypeError("network interrupted"));
  await expect(proposePlaySceneEdit("world", run, id, request)).rejects.toThrow("network interrupted");
  expect(fetch).toHaveBeenCalledOnce();
});
it("blocks collection and proposal egress to a non-loopback destination", async () => {
  vi.resetModules(); vi.stubEnv("VITE_LIVE_API_BASE_URL", "https://foreign.example");
  try {
    const api = await import("./liveApi"); const client = await import("./playSceneEditApi");
    api.setNativeGraphAccessToken("synthetic-test-credential");
    const fetch = vi.spyOn(globalThis, "fetch");
    await expect(client.listPlaySceneEdits("world", run)).rejects.toThrow(/loopback/);
    await expect(client.proposePlaySceneEdit("world", run, id, request)).rejects.toThrow(/loopback/);
    expect(fetch).not.toHaveBeenCalled(); api.setNativeGraphAccessToken(null);
  } finally { vi.unstubAllEnvs(); vi.resetModules(); }
});
