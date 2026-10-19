import { webcrypto, createHash } from "node:crypto";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { getWorldPlayRunContent } from "./playRunContentApi";
import { setNativeGraphAccessToken } from "./liveApi";
const run = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa";
function payload() {
  const markdown = "Exact café 🧙\r\n";
  const sha = createHash("sha256").update(markdown).digest("hex");
  return { schema_version: "dmb_world_play_run_content_v1", world_id: "world", run_id: run,
    origin: { playable_artifact_id: run, playable_revision: 1, playable_work_revision_id: run, playable_content_sha256: sha },
    source: "pinned", edition_revision: 0, edition_revision_id: null, markdown, content_sha256: sha,
    structure_sha256: "a".repeat(64), committed_at: "2026-10-18T00:00:00Z", observed_run_revision: 1 };
}
beforeEach(() => { vi.stubGlobal("crypto", webcrypto); setNativeGraphAccessToken("synthetic-test-credential"); });
afterEach(() => { vi.restoreAllMocks(); vi.unstubAllGlobals(); setNativeGraphAccessToken(""); });
it("uses authenticated GET transport with no cache or domain writes and verifies exact UTF8 bytes", async () => {
  const fetch = vi.spyOn(globalThis, "fetch").mockResolvedValue(Response.json(payload()));
  expect(await getWorldPlayRunContent(run, "world")).toEqual(payload());
  expect(fetch).toHaveBeenCalledOnce();
  expect(fetch.mock.calls[0][0]).toBe(`/api/live/world-play-runs/v2/${run}/content?world_id=world`);
  const init = fetch.mock.calls[0][1];
  expect(new Headers(init?.headers).get("Authorization")).toBe("Bearer synthetic-test-credential");
  expect(init?.cache).toBe("no-store");
});
it.each([401, 404, 409, 503])("retains HTTP failure %s without fallback", async status => {
  vi.spyOn(globalThis, "fetch").mockResolvedValue(Response.json({ detail: "Exact content unavailable" }, { status }));
  await expect(getWorldPlayRunContent(run, "world")).rejects.toMatchObject({ status });
});
it("rejects corrupt response and non-JSON payloads", async () => {
  const fetch = vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(Response.json({ ...payload(), markdown: "corrupt" })).mockResolvedValueOnce(new Response("not json"));
  await expect(getWorldPlayRunContent(run, "world")).rejects.toMatchObject({ status: 0 });
  await expect(getWorldPlayRunContent(run, "world")).rejects.toThrow(/not JSON/);
  expect(fetch).toHaveBeenCalledTimes(2);
});

it("restores the existing cookie session for a read without a domain write", async () => {
  setNativeGraphAccessToken(null);
  const fetch = vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(Response.json({ status: "active", csrf_token: "synthetic-csrf" })).mockResolvedValueOnce(Response.json(payload()));
  await getWorldPlayRunContent(run, "world");
  expect(fetch.mock.calls[0][0]).toBe("/api/live/agent/local-session");
  expect(fetch.mock.calls[1][1]?.credentials).toBe("same-origin");
  expect(fetch.mock.calls.every(([, init]) => !init?.method || init.method === "GET")).toBe(true);
});
it("blocks a non-loopback content destination before credential transport", async () => {
  vi.resetModules();
  vi.stubEnv("VITE_LIVE_API_BASE_URL", "https://foreign.example");
  try {
    const api = await import("./liveApi");
    const client = await import("./playRunContentApi");
    api.setNativeGraphAccessToken("synthetic-test-credential");
    const fetch = vi.spyOn(globalThis, "fetch");
    await expect(client.getWorldPlayRunContent(run, "world")).rejects.toThrow(/loopback/);
    expect(fetch).not.toHaveBeenCalled();
    api.setNativeGraphAccessToken(null);
  } finally { vi.unstubAllEnvs(); vi.resetModules(); }
});
