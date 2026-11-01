import { afterEach, expect, it, vi } from "vitest";
import type { SavedRecapSource } from "./savedRecapRunsApi";
import type { NativeRecapSourceStatus, RecapSourceTarget } from "./nativeRecapSourceApi";
function source(): SavedRecapSource {
  return { schema: "dmb_saved_recap_source_v1", managedWorldId: "managed-a", nativeWorldId: "native-a", bindingVersion: 3,
    run: { runId: "extraction-a", runRevision: 5, runStatus: "reviewable", sourceArtifactId: "artifact:recap:a", campaignId: "campaign-a", sessionId: "session-8", profileId: "recap", createdAt: null, updatedAt: null, sourceRevisionId: "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa", sourceSha256: "a".repeat(64), unavailableReason: null }, sourceProse: "Private source body must not be transmitted by admission." };
}
function status(t: RecapSourceTarget, state: NativeRecapSourceStatus["state"] = "admitted"): NativeRecapSourceStatus {
  return { schema_version: "dmb_native_recap_source_status_v2", state, run_id: "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb", run_revision: 4,
    managed_world_id: t.managedWorldId, native_world_id: t.nativeWorldId, binding_version: t.bindingVersion, campaign_id: t.campaignId, session_id: `session-${t.session}`,
    app_source_artifact_id: t.sourceArtifactId, app_source_revision_id: t.sourceRevisionId, app_body_sha256: t.contentSha256, admission_id: "admission-a", admission_committed: state === "admitted", command_sha256: "b".repeat(64), published_revision_id: state === "admitted" ? "rev:admitted" : null, evidence_ref_id: state === "admitted" ? "evidence:a" : null, failure_code: null, opening: { state: state === "admitted" ? "verified" : "not_checked" } };
}
function envelope(t: RecapSourceTarget, s = status(t)) { return { schema: "dmb_raw_recap_ingest_status_v1", campaign_id: t.campaignId, session: t.session, native_recap_source: s }; }
let auth: typeof import("./liveApi") | null = null;
afterEach(() => { auth?.setNativeGraphAccessToken(null); auth = null; vi.restoreAllMocks(); vi.unstubAllEnvs(); vi.resetModules(); });
async function client() { vi.resetModules(); vi.stubEnv("VITE_LIVE_API_BASE_URL", ""); auth = await import("./liveApi"); auth.setNativeGraphAccessToken("synthetic-source-admission-operator-token"); return import("./nativeRecapSourceApi"); }
it("submits exact source UUID coordinates over existing authentication without uploading prose or extracting", async () => {
  const c = await client(), t = c.recapSourceTarget(source())!;
  const fetch = vi.spyOn(globalThis, "fetch").mockResolvedValue(Response.json(envelope(t)));
  expect(await c.admitRecapSource(t)).toEqual(status(t));
  expect(fetch).toHaveBeenCalledOnce();
  const [path, init] = fetch.mock.calls[0];
  expect(path).toBe("/api/live/recap-ingest");
  expect(JSON.parse(String(init?.body))).toEqual({ managed_world_id: "managed-a", campaign_id: "campaign-a", session: 8, operation: "build_graph_preview_bundle", include_graph_extraction: false, native_recap_source: { source_artifact_id: t.sourceArtifactId, source_revision_id: t.sourceRevisionId, content_sha256: t.contentSha256 } });
  expect(init?.body).not.toContain(source().sourceProse);
  expect(new Headers(init?.headers).get("Authorization")).toBe("Bearer synthetic-source-admission-operator-token");
  expect(init?.redirect).toBe("error");
});
it("inspects and explicitly resumes the same returned native run/revision/command", async () => {
  const c = await client(), t = c.recapSourceTarget(source())!, s = status(t, "unknown");
  const next = { ...s, run_revision: 5 };
  const fetch = vi.spyOn(globalThis, "fetch").mockImplementation(async () => Response.json(envelope(t, next)));
  await c.inspectRecapSource(t, s); await c.resumeRecapSource(t, s);
  expect(fetch.mock.calls.map(([, init]) => JSON.parse(String(init?.body)))).toEqual([
    { managed_world_id: "managed-a", campaign_id: "campaign-a", session: 8, operation: "inspect_status", native_recap_run_id: s.run_id },
    { managed_world_id: "managed-a", campaign_id: "campaign-a", session: 8, operation: "build_graph_preview_bundle", include_graph_extraction: false, native_recap_resume: { run_id: s.run_id, expected_run_revision: 4, command_sha256: s.command_sha256 } },
  ]);
});
it.each(["managed_world_id", "native_world_id", "binding_version", "campaign_id", "session_id", "app_source_artifact_id", "app_source_revision_id", "app_body_sha256"] as const)("refuses swapped response scope %s", async field => {
  const c = await client(), t = c.recapSourceTarget(source())!, s = status(t);
  Object.assign(s, { [field]: field === "binding_version" ? 4 : "foreign" });
  vi.spyOn(globalThis, "fetch").mockResolvedValue(Response.json(envelope(t, s)));
  await expect(c.admitRecapSource(t)).rejects.toMatchObject({ status: 0 });
});
it.each(["digest-as-revision", "missing-campaign", "invalid-session", "unavailable-source", "foreign-schema"])("refuses incomplete saved coordinates: %s", async kind => {
  const c = await client(), s = source();
  if (kind === "digest-as-revision") s.run.sourceRevisionId = s.run.sourceSha256;
  if (kind === "missing-campaign") s.run.campaignId = null;
  if (kind === "invalid-session") s.run.sessionId = "session-0";
  if (kind === "unavailable-source") s.run.unavailableReason = "Missing exact source.";
  if (kind === "foreign-schema") Object.assign(s, { schema: "candidate" });
  expect(c.recapSourceTarget(s)).toBeNull();
});
it("refuses wrong operation identity and older metadata during exact status recovery", async () => {
  const c = await client(), t = c.recapSourceTarget(source())!, s = status(t);
  const fetch = vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(Response.json(envelope(t, { ...s, run_id: "cccccccc-cccc-4ccc-8ccc-cccccccccccc" }))).mockResolvedValueOnce(Response.json(envelope(t, { ...s, run_revision: 3 })));
  await expect(c.inspectRecapSource(t, s)).rejects.toMatchObject({ status: 0 });
  await expect(c.resumeRecapSource(t, s)).rejects.toMatchObject({ status: 0 });
  expect(fetch).toHaveBeenCalledTimes(2);
});
it("does not request another source's recovery operation", async () => {
  const c = await client(), t = c.recapSourceTarget(source())!, s = { ...status(t), app_source_artifact_id: "foreign" };
  const fetch = vi.spyOn(globalThis, "fetch");
  await expect(c.inspectRecapSource(t, s)).rejects.toMatchObject({ status: 0 }); expect(fetch).not.toHaveBeenCalled();
});
it("keeps committed-but-unverified and unknown outcomes distinct from verified availability", async () => {
  const c = await client(), t = c.recapSourceTarget(source())!;
  const unverified: NativeRecapSourceStatus = { ...status(t), state: "unavailable", opening: { state: "unavailable" }, failure_code: "native_recap_opening_unavailable" };
  vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(Response.json(envelope(t, unverified))).mockResolvedValueOnce(Response.json(envelope(t, status(t, "unknown")))).mockResolvedValueOnce(Response.json(envelope(t, { ...status(t), opening: { state: "not_checked" } })));
  expect((await c.admitRecapSource(t)).admission_committed).toBe(true);
  expect((await c.admitRecapSource(t)).state).toBe("unknown");
  await expect(c.admitRecapSource(t)).rejects.toMatchObject({ status: 0 });
});
it("retains HTTP refusal codes and never falls back or retries automatically", async () => {
  const c = await client(), t = c.recapSourceTarget(source())!;
  const fetch = vi.spyOn(globalThis, "fetch").mockResolvedValue(Response.json({ detail: { code: "native_recap_source_input_changed" } }, { status: 409 }));
  await expect(c.admitRecapSource(t)).rejects.toMatchObject({ status: 409, code: "native_recap_source_input_changed" }); expect(fetch).toHaveBeenCalledOnce();
});
it("resends identical coordinates after a lost response and leaves recovery to the owner", async () => {
  const c = await client(), t = c.recapSourceTarget(source())!;
  const fetch = vi.spyOn(globalThis, "fetch").mockRejectedValueOnce(new TypeError("Response lost after possible commit")).mockResolvedValueOnce(Response.json(envelope(t)));
  await expect(c.admitRecapSource(t)).rejects.toThrow("Response lost");
  expect(fetch).toHaveBeenCalledOnce();
  expect((await c.admitRecapSource(t)).state).toBe("admitted");
  expect(fetch.mock.calls[0][1]?.body).toBe(fetch.mock.calls[1][1]?.body);
});

it("pins response comparison to dispatched coordinates even if a caller mutates its input", async () => {
  const c = await client(), target = c.recapSourceTarget(source())!, original = { ...target };
  let finish!: (value: Response) => void;
  vi.spyOn(globalThis, "fetch").mockImplementation(() => new Promise<Response>(resolve => { finish = resolve; }));
  const result = c.admitRecapSource(target);
  await vi.waitFor(() => expect(finish).toBeDefined());
  target.managedWorldId = "changed-later";
  finish(Response.json(envelope(original)));
  expect((await result).managed_world_id).toBe(original.managedWorldId);
});
