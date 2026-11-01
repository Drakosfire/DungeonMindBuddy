import { afterEach, expect, it, vi } from "vitest";
import type { SavedRecapRun, SavedRecapRuns } from "./savedRecapRunsApi";
function row(): SavedRecapRun {
    return { runId: "run-a", runRevision: 5, runStatus: "reviewable", sourceArtifactId: "artifact:a", campaignId: "longmont-c1", sessionId: "session-8", profileId: "recap_category_v2@2.0", createdAt: null, updatedAt: null, sourceRevisionId: "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa", sourceSha256: "a".repeat(64), unavailableReason: null };
}
function scope(): SavedRecapRuns { return { schema: "dmb_saved_recap_runs_v1", managedWorldId: "world-a", nativeWorldId: "native-a", bindingVersion: 3, runs: [row()] }; }
let auth: typeof import("./liveApi") | null = null;
afterEach(() => { auth?.setNativeGraphAccessToken(null); auth = null; vi.restoreAllMocks(); vi.unstubAllEnvs(); vi.resetModules(); });
async function client() { vi.resetModules(); vi.stubEnv("VITE_LIVE_API_BASE_URL", ""); auth = await import("./liveApi"); auth.setNativeGraphAccessToken("synthetic-operator-credential"); return import("./savedRecapRunsApi"); }
it("reads scoped metadata and exact source with the existing authenticated read transport", async () => {
    const c = await client(), s = scope(), r = s.runs[0];
    const fetch = vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(Response.json(s)).mockResolvedValueOnce(Response.json({ schema: "dmb_saved_recap_source_v1", managedWorldId: s.managedWorldId, nativeWorldId: s.nativeWorldId, bindingVersion: 3, run: r, sourceProse: "Exact source text.\r\n" }));
    expect(await c.getSavedRecapRuns("world-a", "longmont-c1")).toEqual(s);
    expect((await c.getSavedRecapSource(s, r)).sourceProse).toBe("Exact source text.\r\n");
    expect(fetch.mock.calls.map(([path]) => path)).toEqual([
        "/api/live/graph-preview/extraction-runs?managed_world_id=world-a&campaign_id=longmont-c1",
        "/api/live/graph-preview/extraction-runs/run-a/recap-inspection?managed_world_id=world-a&expected_run_revision=5&source_revision_id=aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
    ]);
    for (const [, init] of fetch.mock.calls) {
        expect(new Headers(init?.headers).get("Authorization")).toBe("Bearer synthetic-operator-credential");
        expect(init?.cache).toBe("no-store");
        expect(init?.redirect).toBe("error");
        expect(init?.method ?? "GET").toBe("GET");
    }
});
it.each(["managedWorldId", "campaignId", "sourceRevisionId", "duplicateRun"])("refuses contradictory catalog %s", async (key) => {
    const c = await client(), s = scope();
    if (key === "managedWorldId")
        s.managedWorldId = "foreign";
    if (key === "campaignId")
        s.runs[0].campaignId = "foreign";
    if (key === "sourceRevisionId")
        s.runs[0].sourceRevisionId = "a".repeat(64);
    if (key === "duplicateRun")
        s.runs.push({ ...s.runs[0] });
    vi.spyOn(globalThis, "fetch").mockResolvedValue(Response.json(s));
    await expect(c.getSavedRecapRuns("world-a", "longmont-c1")).rejects.toMatchObject({ status: 0 });
});
it.each(["runRevision", "sourceRevisionId", "nativeWorldId", "bindingVersion"])("refuses a stale or swapped source response: %s", async (key) => {
    const c = await client(), s = scope();
    const body = { schema: "dmb_saved_recap_source_v1", managedWorldId: s.managedWorldId, nativeWorldId: s.nativeWorldId, bindingVersion: 3, run: { ...s.runs[0] }, sourceProse: "Source." };
    if (key === "runRevision")
        body.run.runRevision++;
    if (key === "sourceRevisionId")
        body.run.sourceRevisionId = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb";
    if (key === "nativeWorldId")
        body.nativeWorldId = "foreign";
    if (key === "bindingVersion")
        body.bindingVersion++;
    vi.spyOn(globalThis, "fetch").mockResolvedValue(Response.json(body));
    await expect(c.getSavedRecapSource(s, s.runs[0])).rejects.toMatchObject({ status: 0 });
});
it("keeps an unfinished source unavailable and never calls Process or a file reader", async () => {
    const c = await client(), s = scope();
    Object.assign(s.runs[0], { runStatus: "draft", sourceRevisionId: null, sourceSha256: null, unavailableReason: "No frozen source component." });
    const fetch = vi.spyOn(globalThis, "fetch").mockResolvedValue(Response.json(s));
    const result = await c.getSavedRecapRuns("world-a", "longmont-c1");
    expect(result.runs[0].unavailableReason).toBe("No frozen source component.");
    await expect(c.getSavedRecapSource(result, result.runs[0])).rejects.toMatchObject({ status: 0 });
    expect(fetch).toHaveBeenCalledOnce();
});
it("preserves the owning HTTP refusal without selecting another attempt", async () => {
    const c = await client();
    const fetch = vi.spyOn(globalThis, "fetch").mockResolvedValue(Response.json({ detail: "Selected extraction run changed" }, { status: 409 }));
    await expect(c.getSavedRecapSource(scope(), row())).rejects.toMatchObject({ status: 409, message: "Selected extraction run changed" });
    expect(fetch).toHaveBeenCalledOnce();
});
