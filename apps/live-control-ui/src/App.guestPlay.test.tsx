// @vitest-environment jsdom
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { createHash } from "node:crypto";
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

it("starts a guest session from an existing saved Plan", async () => {
  vi.stubEnv("PROD", true);
  vi.stubEnv("VITE_HOSTED_GUEST_BUILD", "1");
  vi.stubEnv("VITE_HOSTED_GUEST_PLAN", "1");
  vi.stubEnv("VITE_HOSTED_GUEST_PLAY", "1");
  Object.defineProperty(navigator, "locks", { configurable: true, value: { request: async (_: string, _options: unknown, action: () => unknown) => action() } });
  const worldId = `guest-${"a".repeat(32)}`;
  const documentId = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb";
  const revisionId = "dddddddd-dddd-4ddd-8ddd-dddddddddddd";
  const markdown = "<!-- dmb-playable-element:v2 kind=beat id=beat:opening beat_kind=spine -->\n## Opening\n";
  const digest = createHash("sha256").update(markdown).digest("hex");
  const record = { schema_version: "dmb_world_owned_plan_record_v2", scope_mode: "world", document_id: documentId, title: "Guest Plan", campaign_id: null, world_id: worldId,
    target_session: null, kind: "plan", target_relpath: null, status: "active", content_status: "committed", revision: 2, created_at: "2026-01-01T00:00:00Z", updated_at: "2026-01-01T00:00:00Z" };
  const snapshot = { schema_version: "dmb_workspace_document_snapshot_v2", record, markdown, content_sha256: digest, file_fingerprint: "postgres", file_exists: true, loaded_revision: 2 };
  const committed = { schema_version: "dmb_workspace_committed_revision_v2", scope_mode: "world", world_id: worldId, document_id: documentId, kind: "plan", campaign_id: null,
    title: record.title, status: "active", object_revision: 2, work_revision_id: revisionId, revision_n: 1, markdown, content_sha256: digest, has_divergent_working_copy: false, target_relpath: null };
  let createdRun = "";
  const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const path = String(input);
    if (path === "/api/auth/session") return response(401, { status: "signed_out" });
    if (path === "/api/live/index-graph/session") return response(200, { csrf_token: "guest-csrf" });
    if (path === "/api/live/index-graph/world") return response(200, { world_id: worldId, name: "Sizzek World" });
    if (path === `/api/live/workspace-documents/${documentId}`) return response(200, record);
    if (path === `/api/live/workspace-documents/${documentId}/snapshot`) return response(200, snapshot);
    if (path === `/api/live/workspace-documents/${documentId}/committed-revision`) return response(200, committed);
    if (path.startsWith("/api/live/plan-view?")) return response(200, { schema_version: "dmb_managed_world_plan_context_v2", scope_mode: "world", world_id: worldId, campaign_id: null, session: null, timeline: [] });
    if (path.startsWith("/api/live/workspace-documents/world-plans?")) return response(200, { world_id: worldId, records: [record] });
    if (path.startsWith("/api/live/world-play-runs/v2/preparation?")) {
      const source = JSON.parse(String(init?.body));
      return response(200, { request: { ...source, schema_version: "dmb_world_session_create_v1", entry_scene_id: null, encounters: [] }, scenes: [], excluded_orphan_count: 0 });
    }
    const match = /^\/api\/live\/world-play-runs\/v2\/([0-9a-f-]{36})\?/.exec(path);
    if (match && init?.method === "PUT") {
      createdRun = match[1];
      const request = JSON.parse(String(init.body));
      const run = { schema_version: "dmb_world_play_run_record_v2", run_id: createdRun, world_id: worldId, playable_artifact_id: documentId, playable_revision: 1,
        playable_work_revision_id: revisionId, playable_content_sha256: digest, run_revision: 1, created_at: record.created_at, updated_at: record.updated_at,
        progress: { current_scene_id: null, current_beat_id: "beat:opening", resolved_beat_ids: [], selections: {}, notes_by_element_id: {} } };
      return response(200, { schema_version: "dmb_world_session_creation_v1", state: "applied", run,
        manifest: { schema_version: "dmb_play_run_reference_manifest_v1", run_id: createdRun, playable_artifact_id: documentId, playable_revision: 1, playable_content_sha256: digest, elements: [], sealed_at: record.created_at },
        receipt: { world_id: worldId, run_id: createdRun, request, preparation_digest: `sha256:${digest}` } });
    }
    return response(404, { detail: "Not found" });
  });
  vi.stubGlobal("fetch", fetchMock);
  window.history.replaceState({}, "", `/plan?world=${worldId}&documentId=${documentId}`);
  render(<App />);
  const play = await screen.findByTestId("world-plan-start-play", {}, { timeout: 10000 });
  await waitFor(() => expect(play).toBeEnabled());
  fireEvent.click(play);
  await screen.findByRole("heading", { name: "Play this Plan" });
  const start = await screen.findByTestId("play-start-run-submit");
  await waitFor(() => { if (start.hasAttribute("disabled")) throw new Error(`Requests: ${fetchMock.mock.calls.map(([path]) => String(path)).join(", ")}; view: ${document.body.textContent?.slice(-1600)}`); }, { timeout: 5000 });
  fireEvent.click(start);
  await waitFor(() => { if (!createdRun) throw new Error(`Requests: ${fetchMock.mock.calls.map(([path]) => String(path)).join(", ")}; view: ${document.body.textContent?.slice(-1600)}`); }, { timeout: 5000 });
  const request = fetchMock.mock.calls.find(([url, init]) => String(url).includes(createdRun) && init?.method === "PUT");
  expect(new Headers(request?.[1]?.headers).get("X-DMB-Index-Graph-CSRF")).toBe("guest-csrf");
  await waitFor(() => expect(window.location.pathname).toBe("/play"));
}, 20000);

it("opens the prepared guest session from bare Play", async () => {
  vi.stubEnv("PROD",true); vi.stubEnv("VITE_HOSTED_GUEST_BUILD","1"); vi.stubEnv("VITE_HOSTED_GUEST_PLAN","1"); vi.stubEnv("VITE_HOSTED_GUEST_PLAY","1");
  const worldId=`guest-${'b'.repeat(32)}`;
  const helper=await import('./playSurface/guestAdventureSession');
  const open=vi.spyOn(helper,'guestAdventureSession').mockResolvedValue('11111111-1111-4111-8111-111111111111');
  vi.stubGlobal('fetch',vi.fn(async(input:RequestInfo|URL)=>{
    const path=String(input);
    if(path==='/api/auth/session')return response(401,{status:'signed_out'});
    if(path==='/api/live/index-graph/session')return response(200,{csrf_token:'guest-csrf'});
    if(path==='/api/live/index-graph/world')return response(200,{world_id:worldId,name:'Sizzek World'});
    if(path.startsWith('/api/live/world-play-runs/v2/active?'))return response(200,{schema_version:'dmb_world_play_active_run_v2',world_id:worldId,run_id:null,selected_at:null});
    if(path.startsWith('/api/live/world-play-runs/v2?'))return response(200,{schema_version:'dmb_world_play_runs_list_v2',world_id:worldId,records:[],source_titles:{}});
    return response(404,{detail:'Not found'});
  }));
  window.history.replaceState({},'','/play'); render(<App/>);
  await waitFor(()=>expect(open).toHaveBeenCalled(),{timeout:10000});
  await waitFor(()=>expect(new URLSearchParams(window.location.search).get('run')).toBe('11111111-1111-4111-8111-111111111111'));
},15000);
