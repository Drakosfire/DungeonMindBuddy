// @vitest-environment jsdom
import { render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { App } from "./App";

function response(status: number, payload: unknown): Response {
  const make = (): Response => ({ ok: status >= 200 && status < 300, status,
    json: async () => payload, text: async () => JSON.stringify(payload), clone: make } as Response);
  return make();
}

afterEach(() => { vi.unstubAllGlobals(); vi.unstubAllEnvs(); vi.restoreAllMocks(); });

it("opens the existing Play surface in the guest World", async () => {
  vi.stubEnv("PROD", true);
  vi.stubEnv("VITE_HOSTED_GUEST_BUILD", "1");
  vi.stubEnv("VITE_HOSTED_GUEST_PLAN", "1");
  vi.stubEnv("VITE_HOSTED_GUEST_PLAY", "1");
  const worldId = `guest-${"a".repeat(32)}`;
  vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL) => {
    const path = String(input);
    if (path === "/api/auth/session") return response(401, { status: "signed_out" });
    if (path === "/api/live/index-graph/session") return response(200, { csrf_token: "guest-csrf" });
    if (path === "/api/live/index-graph/world") return response(200, { world_id: worldId, name: "Sizzek World" });
    if (path.startsWith("/api/live/world-play-runs/v2/active?")) return response(200, { schema_version: "dmb_world_play_active_run_v2", world_id: worldId, run_id: null, selected_at: null });
    if (path.startsWith("/api/live/world-play-runs/v2?")) return response(200, { schema_version: "dmb_world_play_runs_list_v2", world_id: worldId, records: [], source_titles: {} });
    if (path.startsWith("/api/live/workspace-documents/world-runbooks?")) return response(200, { schema_version: "dmb_world_owned_runbooks_list_v2", scope_mode: "world", world_id: worldId, records: [] });
    return response(404, { detail: "Not found" });
  }));
  window.history.replaceState({}, "", "/play");
  render(<App />);
  expect(await screen.findByText("No sessions in this World yet. Open a Plan and press Play to start one.", {}, { timeout: 10000 })).toBeInTheDocument();
  expect(screen.queryByRole("heading", { name: "Sign in to DungeonMind" })).not.toBeInTheDocument();
}, 15000);
