import { afterEach, expect, it, vi } from "vitest";
import type { ExactRunCandidateProjection } from "./exactRunCandidateProjectionApi";
function projection(): ExactRunCandidateProjection {
  return { runId: "run/a", runRevision: 5, runStatus: "reviewable", sourceArtifactId: "artifact:a",
    sourceRevisionId: "sha256:" + "a".repeat(64), sourceSha256: "sha256:" + "a".repeat(64),
    candidateSha256: "sha256:" + "b".repeat(64), spanIndexSha256: "sha256:" + "c".repeat(64),
    managedWorldId: "managed-a", nativeWorldId: "native-a", bindingVersion: 3, campaignId: "campaign-a", sessionId: "session-8",
    sourceMarkdown: "PRIVATE SOURCE NEVER UPLOADED", nodes: [{ candidateNodeId: "ari", viewKey: "candidate:ari" }] } as ExactRunCandidateProjection;
}
function reply() {
  const p = projection();
  return { schema: "dmb_ingest_native_review_context_v2", run_id: p.runId, run_revision: 5,
    source_artifact_id: p.sourceArtifactId, source_revision_id: "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
    source_sha256: "a".repeat(64), candidate_sha256: "b".repeat(64), span_index_sha256: "c".repeat(64),
    selected_node_ids: ["ari"], selected_edge_ids: [],
    scope: { managed_world_id: "managed-a", native_world_id: "native-a", binding_version: 3, campaign_id: "campaign-a", session_id: "session-8" },
    native_context: { revision_id: "rev:current", source_authority_epoch: 23, identity_approval: false, semantic_support_verified: false,
      domain_contract_ref: { domain_id: "world", domain_revision: "2", descriptor_sha256: "d".repeat(64) },
      semantic_profile_ref: { profile_id: "game", profile_revision: "1", descriptor_sha256: "e".repeat(64) },
      source_admission: { state: "admitted", run_id: "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb", run_revision: 4, opening_state: "verified", failure_code: null },
      source_evidence: [{ evidence_ref_id: "ev:one", evidence_role: "support", opening: { status: "available", source_artifact_id: "src:one", source_revision_id: "srev:one", body_sha256: "a".repeat(64), span_start_byte: 0, span_end_byte: 7, span_text: "Ari 🐉" } }],
      selections: [{ candidate_node_id: "ari", status: "ambiguous", search_is_advisory: true,
        alternatives: [{ entity_id: "ent:ari", identity_approved: false, status: "supported_facts", source_inspection: [{ span_text: "OTHER SOURCE IS NOT CANDIDATE SUPPORT" }] }] }],
    } };
}
let auth: typeof import("./liveApi") | null = null;
afterEach(() => { auth?.setNativeGraphAccessToken(null); auth = null; vi.restoreAllMocks(); vi.unstubAllEnvs(); vi.resetModules(); });
async function client() { vi.resetModules(); vi.stubEnv("VITE_LIVE_API_BASE_URL", ""); auth = await import("./liveApi"); auth.setNativeGraphAccessToken("synthetic-review-token"); return import("./recapNativeReviewApi"); }
it("uses only explicit scoped read coordinates, actual candidate ID and existing auth", async () => {
  const c = await client(), fetch = vi.spyOn(globalThis, "fetch").mockResolvedValue(Response.json(reply()));
  const result = await c.getRecapNativeReview(projection(), "ari");
  expect(fetch).toHaveBeenCalledOnce();
  expect(fetch.mock.calls[0][0]).toBe("/api/live/extract-promote/runs/run%2Fa/selection-context");
  const init = fetch.mock.calls[0][1]!;
  expect(init.method).toBe("POST"); expect(init.cache).toBe("no-store");
  expect(new Headers(init.headers).get("Authorization")).toBe("Bearer synthetic-review-token");
  expect(JSON.parse(String(init.body))).toEqual({ schema: "dmb_ingest_native_review_request_v2", expected_run_revision: 5,
    expected_candidate_sha256: "b".repeat(64), expected_source_sha256: "a".repeat(64), expected_span_index_sha256: "c".repeat(64),
    expected_world_id: "managed-a", node_ids: ["ari"], edge_ids: [], inspect_source_support: true });
  expect(String(init.body)).not.toContain("PRIVATE SOURCE");
  expect(result.source_revision_id).not.toBe(projection().sourceRevisionId);
});
it.each(["candidate:ari", "foreign"])("does not use a view key or foreign node: %s", async id => {
  const c = await client(), fetch = vi.spyOn(globalThis, "fetch");
  await expect(c.getRecapNativeReview(projection(), id)).rejects.toMatchObject({ status: 0 }); expect(fetch).not.toHaveBeenCalled();
});
it("does not inspect promoted extractions", async () => {
  const c = await client(), fetch = vi.spyOn(globalThis, "fetch");
  await expect(c.getRecapNativeReview({ ...projection(), runStatus: "promoted" }, "ari")).rejects.toMatchObject({ status: 0 }); expect(fetch).not.toHaveBeenCalled();
});
it.each([
  ["run_id", "other"], ["run_revision", 6], ["source_artifact_id", "foreign"], ["source_revision_id", "a".repeat(64)],
  ["source_sha256", "f".repeat(64)], ["candidate_sha256", "f".repeat(64)], ["span_index_sha256", "f".repeat(64)],
  ["selected_node_ids", ["foreign"]], ["selected_edge_ids", ["foreign"]],
])("refuses changed response %s", async (key, value) => {
  const c = await client(); vi.spyOn(globalThis, "fetch").mockResolvedValue(Response.json({ ...reply(), [key as string]: value }));
  await expect(c.getRecapNativeReview(projection(), "ari")).rejects.toMatchObject({ status: 0 });
});
it.each([["managed_world_id", "other"], ["native_world_id", "other"], ["binding_version", 4], ["campaign_id", "other"], ["session_id", "session-9"]])("refuses changed scope %s", async (key, value) => {
  const c = await client(), data = reply(); vi.spyOn(globalThis, "fetch").mockResolvedValue(Response.json({ ...data, scope: { ...data.scope, [key as string]: value } }));
  await expect(c.getRecapNativeReview(projection(), "ari")).rejects.toMatchObject({ status: 0 });
});
it.each(["role", "digest", "approval", "selection", "opening"])("refuses an inconsistent native display: %s", async change => {
  const c = await client(), data = reply();
  if (change === "role") data.native_context.source_evidence[0].evidence_role = "context";
  if (change === "digest") data.native_context.source_evidence[0].opening.body_sha256 = "f".repeat(64);
  if (change === "approval") data.native_context.identity_approval = true;
  if (change === "selection") data.native_context.selections[0].candidate_node_id = "other";
  if (change === "opening") data.native_context.source_evidence[0].opening.status = "invented";
  vi.spyOn(globalThis, "fetch").mockResolvedValue(Response.json(data));
  await expect(c.getRecapNativeReview(projection(), "ari")).rejects.toMatchObject({ status: 0 });
});
it("keeps missing admission and unavailable support distinct from verified support", async () => {
  const c = await client(), data = reply();
  vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(Response.json({ ...data, native_context: { ...data.native_context, source_admission: { state: "not_found" }, source_evidence: [] } }))
    .mockResolvedValueOnce(Response.json({ ...data, native_context: { ...data.native_context, source_evidence: [{ evidence_ref_id: "ev:one", evidence_role: "support", opening: { status: "unavailable" } }] } }));
  expect((await c.getRecapNativeReview(projection(), "ari")).native_context.source_admission.state).toBe("not_found");
  expect((await c.getRecapNativeReview(projection(), "ari")).native_context.source_evidence[0].opening.status).toBe("unavailable");
});
it("rejects support attached to an unverified admission", async () => {
  const c = await client(), data = reply(); data.native_context.source_admission.opening_state = "unavailable";
  vi.spyOn(globalThis, "fetch").mockResolvedValue(Response.json(data));
  await expect(c.getRecapNativeReview(projection(), "ari")).rejects.toMatchObject({ status: 0 });
});
it("preserves owner error codes and does not retry conflicts", async () => {
  const c = await client(), fetch = vi.spyOn(globalThis, "fetch").mockResolvedValue(Response.json({ code: "ingest_selection_conflict", message: "selected run changed" }, { status: 409 }));
  await expect(c.getRecapNativeReview(projection(), "ari")).rejects.toMatchObject({ status: 409, code: "ingest_selection_conflict", message: "selected run changed" }); expect(fetch).toHaveBeenCalledOnce();
});
it("compares with dispatched coordinates if the caller mutates props while pending", async () => {
  const c = await client(), p = projection(); let finish!: (response: Response) => void;
  vi.spyOn(globalThis, "fetch").mockReturnValue(new Promise(resolve => { finish = resolve; }));
  const pending = c.getRecapNativeReview(p, "ari"); p.managedWorldId = "foreign";
  const data = reply(); data.scope.managed_world_id = "foreign"; finish(Response.json(data));
  await expect(pending).rejects.toMatchObject({ status: 0 });
});

it("uses the local session and CSRF safeguards and retries only after trusted expiry", async () => {
  const c = await client(); auth!.setNativeGraphAccessToken(null);
  let sessions = 0, reads = 0;
  const fetch = vi.spyOn(globalThis, "fetch").mockImplementation(async (url, init) => {
    if (String(url) === "/api/live/agent/local-session") {
      return Response.json({ status: "active", csrf_token: ++sessions === 1 ? "old-csrf" : "fresh-csrf" });
    }
    expect(init?.credentials).toBe("same-origin"); expect(init?.redirect).toBe("error");
    expect(new Headers(init?.headers).has("Authorization")).toBe(false);
    expect(new Headers(init?.headers).get("X-DMB-Graph-CSRF")).toBe(reads ? "fresh-csrf" : "old-csrf");
    return ++reads === 1 ? Response.json({ detail: { code: "graph_auth_required" } }, { status: 401 }) : Response.json(reply());
  });
  await expect(c.getRecapNativeReview(projection(), "ari")).resolves.toMatchObject({ run_id: "run/a" });
  expect(sessions).toBe(2); expect(reads).toBe(2);
  const requests = fetch.mock.calls.filter(([url]) => !String(url).endsWith("local-session"));
  expect(requests[0][1]?.body).toBe(requests[1][1]?.body);
});
it("refuses a non-loopback credential destination before fetching", async () => {
  vi.resetModules(); vi.stubEnv("VITE_LIVE_API_BASE_URL", "https://api.example.invalid");
  auth = await import("./liveApi"); auth.setNativeGraphAccessToken("synthetic-review-token");
  const c = await import("./recapNativeReviewApi"), fetch = vi.spyOn(globalThis, "fetch");
  await expect(c.getRecapNativeReview(projection(), "ari")).rejects.toMatchObject({ status: 0, message: expect.stringContaining("loopback") });
  expect(fetch).not.toHaveBeenCalled();
});
it("rejects comparison JSON obtained before access is revoked", async () => {
  const c = await client(); let stream!: ReadableStreamDefaultController<Uint8Array>;
  vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response(new ReadableStream<Uint8Array>({ start(controller) { stream = controller; } })));
  const consume = vi.spyOn(Response.prototype, "text");
  const pending = c.getRecapNativeReview(projection(), "ari");
  const rejected = expect(pending).rejects.toMatchObject({ code: "local_graph_session_changed" });
  await vi.waitFor(() => expect(consume).toHaveBeenCalled());
  auth!.setNativeGraphAccessToken(null);
  stream.enqueue(new TextEncoder().encode(JSON.stringify(reply()))); stream.close();
  await rejected;
});
