// @vitest-environment jsdom
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, expect, it, vi } from "vitest";
import { App } from "./App";

vi.mock("./buildSurface/BuildPdfPreview", () => ({ BuildPdfPreview: () => null }));

function response(status: number, payload: unknown): Response {
  const make = (): Response => ({ ok: status >= 200 && status < 300, status,
    json: async () => payload, clone: make } as Response);
  return make();
}

afterEach(() => { vi.unstubAllGlobals(); vi.unstubAllEnvs(); vi.restoreAllMocks(); });

it("opens the existing Build surface for a signed-out guest World", async () => {
  vi.stubEnv("PROD", true);
  vi.stubEnv("VITE_HOSTED_GUEST_GRAPH", "1");
  vi.stubEnv("VITE_HOSTED_GUEST_BUILD", "1");
  const worldId = `guest-${"a".repeat(32)}`;
  const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const path = String(input);
    if (path === "/api/auth/session") return response(401, { status: "signed_out" });
    if (path === "/api/live/index-graph/session") return response(200, { csrf_token: "guest-csrf" });
    if (path === "/api/live/index-graph/world") return response(200, { world_id: worldId, name: "Sizzek World" });
    if (path.startsWith("/api/live/workspace-documents/pages/inventory")) return response(200, { schema_version: "dmb_workspace_documents_v1", records: [], campaign_tags: [] });
    if (path === "/api/live/workspace-documents" && init?.method === "POST") return response(200, {
      schema_version: "dmb_workspace_document_record_v1", document_id: "11111111-1111-4111-8111-111111111111",
      title: "Guest note", world_id: worldId, campaign_id: worldId, target_session: null,
      target_relpath: "", kind: "worldbuilding_source", status: "active", content_status: "draft", revision: 1,
      source_domain: "worldbuilding", document_class: "lore", authority_state: "draft", visibility_state: "internal",
      created_at: "2026-01-01T00:00:00Z", updated_at: "2026-01-01T00:00:00Z",
    });
    return response(404, { error: "Not found.", code: "not_found" });
  });
  vi.stubGlobal("fetch", fetchMock);
  window.history.replaceState({}, "", "/build");
  render(<App />);
  expect(await screen.findByRole("navigation", { name: /navigation/i })).toBeInTheDocument();
  await waitFor(() => expect(fetchMock.mock.calls.some(([path]) => String(path).startsWith("/api/live/workspace-documents/pages/inventory"))).toBe(true));
  expect(screen.queryByRole("heading", { name: "Sign in to DungeonMind" })).not.toBeInTheDocument();
  expect(fetchMock.mock.calls.some(([path]) => String(path) === "/api/live/world-containers")).toBe(false);
  const user = userEvent.setup();
  await user.click(await screen.findByTestId("build-document-create-open"));
  await user.type(screen.getByTestId("build-document-create-title"), "Guest note");
  await user.click(screen.getByTestId("build-document-create-submit"));
  await waitFor(() => expect(fetchMock.mock.calls.some(([path, init]) => String(path) === "/api/live/workspace-documents" && init?.method === "POST")).toBe(true));
  const call = fetchMock.mock.calls.find(([path, init]) => String(path) === "/api/live/workspace-documents" && init?.method === "POST")!;
  expect(new Headers(call[1]?.headers).get("X-DMB-Index-Graph-CSRF")).toBe("guest-csrf");
  expect(JSON.parse(String(call[1]?.body))).toMatchObject({ world_id: worldId, campaign_id: worldId, title: "Guest note" });
});

it("does not mount a late guest World after sign-in", async () => {
  vi.stubEnv("PROD", true);
  vi.stubEnv("VITE_HOSTED_GUEST_GRAPH", "1");
  vi.stubEnv("VITE_HOSTED_GUEST_BUILD", "1");
  let signedIn = false;
  let finishWorld!: (value: Response) => void;
  const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
    const path = String(input);
    if (path === "/api/auth/session") return signedIn
      ? response(200, { status: "authenticated", subject: "owner" }) : response(401, { status: "signed_out" });
    if (path === "/api/live/index-graph/session") return response(200, { csrf_token: "guest-csrf" });
    if (path === "/api/live/index-graph/world") return new Promise<Response>(resolve => { finishWorld = resolve; });
    return response(404, { error: "Not found.", code: "not_found" });
  });
  vi.stubGlobal("fetch", fetchMock);
  window.history.replaceState({}, "", "/build");
  render(<App />);
  await waitFor(() => expect(finishWorld).toBeDefined());
  signedIn = true;
  window.dispatchEvent(new Event("focus"));
  expect(await screen.findByRole("heading", { name: "Choose a World" })).toBeInTheDocument();
  finishWorld(response(200, { world_id: `guest-${"a".repeat(32)}`, name: "Sizzek World" }));
  await waitFor(() => expect(screen.queryByText("Sizzek World")).not.toBeInTheDocument());
});

it("keeps navigation visible when the guest World is unavailable", async () => {
  vi.stubEnv("PROD", true);
  vi.stubEnv("VITE_HOSTED_GUEST_GRAPH", "1");
  vi.stubEnv("VITE_HOSTED_GUEST_BUILD", "1");
  vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL) => String(input) === "/api/auth/session"
    ? response(401, { status: "signed_out" }) : response(503, { error: "unavailable" })));
  window.history.replaceState({}, "", "/build");
  render(<App />);
  expect(await screen.findByRole("heading", { name: "World selection unavailable" })).toBeInTheDocument();
  expect(screen.getByRole("link", { name: "Graph" })).toHaveAttribute("href", "/graph");
  expect(screen.getByRole("button", { name: "Retry selection" })).toBeInTheDocument();
});
