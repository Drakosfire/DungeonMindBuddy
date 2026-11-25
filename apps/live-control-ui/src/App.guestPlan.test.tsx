// @vitest-environment jsdom
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
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
  const documentId = "11111111-1111-4111-8111-111111111111";
  let saved = "";
  let title = "Plan";
  const record = (revision: number) => ({ schema_version: "dmb_world_owned_plan_record_v2", scope_mode: "world", document_id: documentId,
    title, campaign_id: null, world_id: worldId, target_session: null, kind: "plan", target_relpath: `out/workspace/plan/${documentId}.md`,
    status: "active", content_status: revision > 1 ? "committed" : "draft", revision, created_at: "2026-01-01T00:00:00Z", updated_at: "2026-01-01T00:00:00Z" });
  const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const path = String(input);
    if (path === "/api/auth/session") return response(401, { status: "signed_out" });
    if (path === "/api/live/index-graph/session") return response(200, { csrf_token: "guest-csrf" });
    if (path === "/api/live/index-graph/world") return response(200, { world_id: worldId, name: "Sizzek World" });
    if (path.startsWith("/api/live/plan-view?")) return response(200, { schema_version: "dmb_managed_world_plan_context_v2", scope_mode: "world", world_id: worldId, campaign_id: null, session: null, timeline: [] });
    if (path.startsWith("/api/live/workspace-documents/world-plans?")) return response(200, { world_id: worldId, records: saved ? [record(2)] : [] });
    if (path === "/api/live/workspace-documents/world-plans" && init?.method === "POST") {
      title = JSON.parse(String(init.body)).title;
      return response(200, record(1));
    }
    if (path === "/api/live/tiptap/markdown-write/prepare") return response(200, { world_id: worldId, document_id: documentId, title,
      registry_revision: 1, writer_ok: true, writer_confirm_token: "token", warnings: [], diagnostics: [] });
    if (path === "/api/live/tiptap/markdown-write/commit") {
      saved = JSON.parse(String(init?.body)).markdown;
      return response(200, { world_id: worldId, document_id: documentId, title, registry_revision: 2, committed_revision: 2,
        committed_record: record(2), normalized_content_sha256: "b".repeat(64), writer_ok: true, writer_phase: "commit", diagnostics: [] });
    }
    if (path === `/api/live/workspace-documents/${documentId}`) return response(200, record(2));
    if (path === `/api/live/workspace-documents/${documentId}/snapshot`) return response(200, { schema_version: "dmb_workspace_document_snapshot_v2",
      record: record(2), markdown: saved, content_sha256: "b".repeat(64), file_fingerprint: "postgres", file_exists: true, loaded_revision: 2 });
    return response(404, { error: "Not found.", code: "not_found" });
  });
  vi.stubGlobal("fetch", fetchMock);
  window.history.replaceState({}, "", "/plan");
  const rendered = render(<App />);
  await waitFor(() => {
    if (!fetchMock.mock.calls.some(([path]) => String(path).startsWith("/api/live/workspace-documents/world-plans?"))) {
      throw new Error(`Requests: ${fetchMock.mock.calls.map(([path]) => String(path)).join(", ")}; view: ${document.body.textContent?.slice(-1200)}`);
    }
  }, { timeout: 8000 });
  expect(screen.queryByRole("heading", { name: "Sign in to DungeonMind" })).not.toBeInTheDocument();
  expect(screen.getAllByText("New Plan").length).toBeGreaterThan(0);
  fireEvent.click(screen.getByRole("button", { name: "Markdown" }));
  fireEvent.change(screen.getByRole("textbox", { name: "Plan Markdown" }), { target: { value: "# Guest Plan\n\nA clue." } });
  expect(screen.getByRole("textbox", { name: "Plan Markdown" })).toHaveValue("# Guest Plan\n\nA clue.");
  fireEvent.click(screen.getByRole("button", { name: "Edit" }));
  fireEvent.click(screen.getByRole("button", { name: "Save Plan" }));
  await waitFor(() => expect(saved).toContain("A clue."));
  for (const path of ["/api/live/workspace-documents/world-plans", "/api/live/tiptap/markdown-write/prepare", "/api/live/tiptap/markdown-write/commit"]) {
    const request = fetchMock.mock.calls.find(([url]) => String(url) === path);
    expect(new Headers(request?.[1]?.headers).get("X-DMB-Index-Graph-CSRF")).toBe("guest-csrf");
  }
  rendered.unmount();
  window.history.replaceState({}, "", `/plan?world=${worldId}&documentId=${documentId}`);
  render(<App />);
  await waitFor(() => expect(screen.getByTestId("world-owned-plan-markdown-editor")).toHaveTextContent("A clue."));
}, 20000);
