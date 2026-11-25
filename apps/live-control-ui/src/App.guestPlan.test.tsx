// @vitest-environment jsdom
import { render, screen, waitFor } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { App } from "./App";

function response(status: number, payload: unknown): Response {
  const make = (): Response => ({ ok: status >= 200 && status < 300, status,
    json: async () => payload, text: async () => JSON.stringify(payload), clone: make } as Response);
  return make();
}

afterEach(() => { vi.unstubAllGlobals(); vi.unstubAllEnvs(); vi.restoreAllMocks(); });

it("opens the normal Plan surface in the session World", async () => {
  vi.stubEnv("PROD", true);
  vi.stubEnv("VITE_HOSTED_GUEST_GRAPH", "1");
  vi.stubEnv("VITE_HOSTED_GUEST_BUILD", "1");
  vi.stubEnv("VITE_HOSTED_GUEST_PLAN", "1");
  const worldId = `guest-${"a".repeat(32)}`;
  const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
    const path = String(input);
    if (path === "/api/auth/session") return response(401, { status: "signed_out" });
    if (path === "/api/live/index-graph/session") return response(200, { csrf_token: "guest-csrf" });
    if (path === "/api/live/index-graph/world") return response(200, { world_id: worldId, name: "Sizzek World" });
    if (path.startsWith("/api/live/plan-view?")) return response(200, { schema_version: "dmb_managed_world_plan_context_v2", scope_mode: "world", world_id: worldId, campaign_id: null, session: null, timeline: [] });
    if (path.startsWith("/api/live/workspace-documents/world-plans?")) return response(200, { world_id: worldId, records: [] });
    return response(404, { error: "Not found.", code: "not_found" });
  });
  vi.stubGlobal("fetch", fetchMock);
  window.history.replaceState({}, "", "/plan");
  render(<App />);
  await waitFor(() => {
    if (!fetchMock.mock.calls.some(([path]) => String(path).startsWith("/api/live/workspace-documents/world-plans?"))) {
      throw new Error(`Requests: ${fetchMock.mock.calls.map(([path]) => String(path)).join(", ")}; view: ${document.body.textContent?.slice(-1200)}`);
    }
  }, { timeout: 8000 });
  expect(screen.queryByRole("heading", { name: "Sign in to DungeonMind" })).not.toBeInTheDocument();
  expect(screen.getAllByText("New Plan").length).toBeGreaterThan(0);
}, 20000);
