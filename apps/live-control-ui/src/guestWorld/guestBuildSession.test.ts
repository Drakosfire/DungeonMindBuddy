import { afterEach, describe, expect, it, vi } from "vitest";
import { clearGuestBuildSession, guestBuildActive, guestBuildCsrf, guestBuildRequestEpoch, openGuestBuildWorld } from "./guestBuildSession";

afterEach(() => { clearGuestBuildSession(); vi.unstubAllGlobals(); vi.unstubAllEnvs(); });

describe("guest Build session", () => {
  it("scopes Buddy transport to the active guest World when enabled", async () => {
    vi.stubEnv("VITE_HOSTED_GUEST_BUDDY", "1");
    vi.stubEnv("VITE_HOSTED_GUEST_PLAN", "1");
    const world = `guest-${"a".repeat(32)}`;
    vi.stubGlobal("fetch", vi.fn()
      .mockResolvedValueOnce(Response.json({ csrf_token: "guest-token" }))
      .mockResolvedValueOnce(Response.json({ world_id: world, name: "Sizzek World" })));
    await openGuestBuildWorld(new AbortController().signal);
    const path = `/api/live/agent/worlds/${world}/conversation`;
    expect(guestBuildRequestEpoch(path, "GET")).not.toBeNull();
    expect(guestBuildRequestEpoch('/api/live/native-graph-inspection/catalog', 'POST')).not.toBeNull();
    expect(guestBuildCsrf('/api/live/native-graph-inspection/read', 'POST')).toBe('guest-token');
    expect(guestBuildCsrf('/api/live/native-graph-inspection/complete-object', 'POST')).toBeNull();
    expect(guestBuildRequestEpoch('/api/live/workspace-documents/11111111-1111-4111-8111-111111111111/committed-revision', 'GET')).not.toBeNull();
    expect(guestBuildRequestEpoch(`/api/live/agent/worlds/${world}/conversations/active/messages?limit=50`, "GET")).not.toBeNull();
    expect(guestBuildRequestEpoch(`${path}/turns/11111111-1111-4111-8111-111111111111/source-passages/0`, "GET")).not.toBeNull();
    expect(guestBuildRequestEpoch(`${path}/turns/11111111-1111-4111-8111-111111111111/context-trace`, "GET")).toBeNull();
    expect(guestBuildCsrf(`${path}/new`, "POST")).toBe("guest-token");
    expect(guestBuildCsrf("/api/live/agent/turn", "POST")).toBe("guest-token");
    expect(guestBuildRequestEpoch(`/api/live/agent/worlds/guest-${"b".repeat(32)}/conversation`, "GET")).toBeNull();
    expect(guestBuildCsrf(`/api/live/agent/worlds/guest-${"b".repeat(32)}/conversation/new`, "POST")).toBeNull();
  });
  it("uses the server-derived World and limits its CSRF token to Build writes", async () => {
    const fetcher = vi.fn()
      .mockResolvedValueOnce(Response.json({ csrf_token: "guest-token" }))
      .mockResolvedValueOnce(Response.json({ world_id: `guest-${"a".repeat(32)}`, name: "Sizzek World" }));
    vi.stubGlobal("fetch", fetcher);
    expect(await openGuestBuildWorld(new AbortController().signal)).toEqual({ worldId: `guest-${"a".repeat(32)}`, name: "Sizzek World" });
    expect(new Headers(fetcher.mock.calls[1][1].headers).get("X-DMB-Index-Graph-CSRF")).toBe("guest-token");
    expect(guestBuildCsrf("/api/live/workspace-documents", "POST")).toBe("guest-token");
    expect(guestBuildCsrf("/api/live/tiptap/markdown-write/commit", "POST")).toBe("guest-token");
    expect(guestBuildCsrf("/api/live/workspace-documents", "GET")).toBeNull();
    expect(guestBuildCsrf("https://elsewhere.example/api/live/workspace-documents", "POST")).toBeNull();
    expect(guestBuildCsrf("/api/live/world-containers", "POST")).toBeNull();
    clearGuestBuildSession();
    expect(guestBuildActive()).toBe(false);
  });

  it("does not retain a World after a session is invalidated during opening", async () => {
    let resolveWorld!: (response: Response) => void;
    const fetcher = vi.fn()
      .mockResolvedValueOnce(Response.json({ csrf_token: "guest-token" }))
      .mockImplementationOnce(() => new Promise<Response>(resolve => { resolveWorld = resolve; }));
    vi.stubGlobal("fetch", fetcher);
    const opening = openGuestBuildWorld(new AbortController().signal);
    await vi.waitFor(() => expect(resolveWorld).toBeDefined());
    clearGuestBuildSession();
    resolveWorld(Response.json({ world_id: `guest-${"a".repeat(32)}`, name: "Sizzek World" }));
    await expect(opening).rejects.toThrow();
    expect(guestBuildActive()).toBe(false);
  });
});

it("attaches the guest token to the normal Build transport only", async () => {
  const fetcher = vi.fn()
    .mockResolvedValueOnce(Response.json({ csrf_token: "guest-token" }))
    .mockResolvedValueOnce(Response.json({ world_id: `guest-${"b".repeat(32)}`, name: "Sizzek World" }))
    .mockResolvedValueOnce(Response.json({ ok: true }))
    .mockResolvedValueOnce(Response.json({ ok: true }));
  vi.stubGlobal("fetch", fetcher);
  await openGuestBuildWorld(new AbortController().signal);
  const { authenticatedApiFetch } = await import("../api/liveApi");
  await authenticatedApiFetch("/api/live/workspace-documents", { method: "POST", body: "{}" });
  await authenticatedApiFetch("/api/live/other", { method: "POST", body: "{}" });
  expect(new Headers(fetcher.mock.calls[2][1].headers).get("X-DMB-Index-Graph-CSRF")).toBe("guest-token");
  expect(new Headers(fetcher.mock.calls[3][1].headers).get("X-DMB-Index-Graph-CSRF")).toBeNull();
});

it("reports a changed guest session without retrying a write", async () => {
  const fetcher = vi.fn()
    .mockResolvedValueOnce(Response.json({ csrf_token: "old-token" }))
    .mockResolvedValueOnce(Response.json({ world_id: `guest-${"c".repeat(32)}`, name: "Sizzek World" }))
    .mockResolvedValueOnce(Response.json({ detail: { code: "csrf_rejected" } }, { status: 403 }));
  vi.stubGlobal("fetch", fetcher);
  await openGuestBuildWorld(new AbortController().signal);
  const { authenticatedApiFetch } = await import("../api/liveApi");
  await expect(authenticatedApiFetch("/api/live/tiptap/markdown-write/commit", { method: "POST", body: "{}" }))
    .rejects.toThrow("Copy any unsaved text, then reload Build");
  expect(fetcher).toHaveBeenCalledTimes(3);
});

it("rejects a document response that arrives after the guest session ends", async () => {
  let finish!: (value: Response) => void;
  const fetcher = vi.fn()
    .mockResolvedValueOnce(Response.json({ csrf_token: "guest-token" }))
    .mockResolvedValueOnce(Response.json({ world_id: `guest-${"d".repeat(32)}`, name: "Sizzek World" }))
    .mockImplementationOnce(() => new Promise<Response>(resolve => { finish = resolve; }));
  vi.stubGlobal("fetch", fetcher);
  await openGuestBuildWorld(new AbortController().signal);
  const { authenticatedApiFetch } = await import("../api/liveApi");
  const request = authenticatedApiFetch("/api/live/workspace-documents/11111111-1111-4111-8111-111111111111");
  await vi.waitFor(() => expect(finish).toBeDefined());
  clearGuestBuildSession();
  finish(Response.json({ title: "old guest page" }));
  await expect(request).rejects.toThrow("guest session changed");
});

it("sends the guest token only to the enabled image generation route", async () => {
  vi.stubEnv("VITE_HOSTED_GUEST_MEDIA", "1");
  const fetcher = vi.fn()
    .mockResolvedValueOnce(Response.json({ csrf_token: "guest-token" }))
    .mockResolvedValueOnce(Response.json({ world_id: `guest-${"e".repeat(32)}`, name: "Sizzek World" }))
    .mockResolvedValueOnce(Response.json({ images: [] }))
    .mockResolvedValueOnce(Response.json({ asset_id: '11111111-1111-4111-8111-111111111111', state: 'staged' }));
  vi.stubGlobal("fetch", fetcher);
  await openGuestBuildWorld(new AbortController().signal);
  const { authenticatedApiFetch } = await import("../api/liveApi");
  await authenticatedApiFetch(`/api/live/media/images/generate?world_id=guest-${"e".repeat(32)}`, { method: "POST", body: "{}" });
  await authenticatedApiFetch('/api/live/media/images/11111111-1111-4111-8111-111111111111/metadata');
  expect(new Headers(fetcher.mock.calls[2][1].headers).get("X-DMB-Index-Graph-CSRF")).toBe("guest-token");
  expect(guestBuildCsrf("/api/live/media/images/11111111-1111-4111-8111-111111111111/save", "POST")).toBeNull();
  expect(fetcher).toHaveBeenCalledTimes(4);
});

it("uses a session-bound non-streaming Build turn for guests", async () => {
  vi.stubEnv("VITE_HOSTED_GUEST_BUDDY", "1");
  const world = `guest-${"f".repeat(32)}`;
  const fetcher = vi.fn()
    .mockResolvedValueOnce(Response.json({ csrf_token: "guest-token" }))
    .mockResolvedValueOnce(Response.json({ world_id: world, name: "Sizzek World" }))
    .mockResolvedValueOnce(Response.json({ answer: { text: "Answer" } }));
  vi.stubGlobal("fetch", fetcher);
  await openGuestBuildWorld(new AbortController().signal);
  const api = await import("../api/liveApi");
  const request = { turn_id: "test", owner_scope: {kind: "world", world_id: world} } as Parameters<typeof api.postWorldBuildAgentTurn>[0];
  await expect(api.postWorldBuildAgentTurn(request)).resolves.toEqual({ answer: { text: "Answer" } });
  const headers = new Headers(fetcher.mock.calls[2][1].headers);
  expect(headers.get("X-DMB-Index-Graph-CSRF")).toBe("guest-token");
  expect(headers.get("accept")).not.toBe("text/event-stream");
});
