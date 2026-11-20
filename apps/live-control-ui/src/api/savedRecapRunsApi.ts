import { authenticatedApiFetch, LiveApiError } from "./liveApi";
/** APP read coordinates; no native admission or publication authority. */
export interface SavedRecapRun {
    runId: string;
    runRevision: number;
    runStatus: string;
    sourceArtifactId: string;
    campaignId: string | null;
    sessionId: string | null;
    profileId: string | null;
    createdAt: string | null;
    updatedAt: string | null;
    sourceRevisionId: string | null;
    sourceSha256: string | null;
    unavailableReason: string | null;
}
export interface SavedRecapRuns {
    schema: "dmb_saved_recap_runs_v1";
    managedWorldId: string;
    nativeWorldId: string;
    bindingVersion: number;
    runs: SavedRecapRun[];
}
export interface SavedRecapSource {
    schema: "dmb_saved_recap_source_v1";
    managedWorldId: string;
    nativeWorldId: string;
    bindingVersion: number;
    run: SavedRecapRun;
    sourceProse: string;
}
const record = (v: unknown): v is Record<string, unknown> => typeof v === "object" && v !== null && !Array.isArray(v);
const text = (v: unknown): v is string => typeof v === "string" && !!v && v === v.trim();
const nullableText = (v: unknown) => v === null || text(v);
const positive = (v: unknown) => Number.isSafeInteger(v) && Number(v) > 0;
function invalid(): never { throw new LiveApiError("Saved extraction response does not match the selected World, run or source revision. Reload saved work.", 0); }
function isRun(v: unknown): v is SavedRecapRun {
    if (!record(v) || !text(v.runId) || !positive(v.runRevision) || !text(v.sourceArtifactId)
        || !["draft", "prepared", "extracted", "validated", "reviewable", "promoted", "superseded", "failed", "incomplete"].includes(String(v.runStatus))
        || ![v.campaignId, v.sessionId, v.profileId, v.createdAt, v.updatedAt].every(nullableText))
        return false;
    if (v.unavailableReason !== null)
        return text(v.unavailableReason) && v.sourceRevisionId === null && v.sourceSha256 === null;
    return typeof v.sourceRevisionId === "string" && /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(v.sourceRevisionId)
        && typeof v.sourceSha256 === "string" && /^[0-9a-f]{64}$/.test(v.sourceSha256);
}
async function read(path: string, signal?: AbortSignal): Promise<Record<string, unknown>> {
    const { response } = await authenticatedApiFetch(path, { cache: "no-store", ...(signal ? { signal } : {}) });
    let body: unknown;
    try {
        body = JSON.parse(await response.text());
    }
    catch {
        throw new LiveApiError(`Saved extraction response was not JSON (HTTP ${response.status}).`, response.status);
    }
    if (!response.ok) {
        const detail = record(body) ? body.detail : null;
        throw new LiveApiError(typeof detail === "string" ? detail : record(detail) && typeof detail.message === "string" ? detail.message : "Saved extraction could not be opened.", response.status);
    }
    if (!record(body))
        invalid();
    return body;
}
export async function getSavedRecapRuns(managedWorldId: string, campaignId: string, signal?: AbortSignal): Promise<SavedRecapRuns> {
    if (!text(managedWorldId) || !text(campaignId))
        invalid();
    const body = await read(`/api/live/graph-preview/extraction-runs?${new URLSearchParams({ managed_world_id: managedWorldId, campaign_id: campaignId })}`, signal);
    if (body.schema !== "dmb_saved_recap_runs_v1" || body.managedWorldId !== managedWorldId || !text(body.nativeWorldId)
        || !positive(body.bindingVersion) || !Array.isArray(body.runs) || !body.runs.every(isRun)
        || body.runs.some(r => r.campaignId !== campaignId) || new Set(body.runs.map(r => r.runId)).size !== body.runs.length)
        invalid();
    return body as unknown as SavedRecapRuns;
}
export async function getSavedRecapSource(scope: SavedRecapRuns, run: SavedRecapRun, signal?: AbortSignal): Promise<SavedRecapSource> {
    if (!run.sourceRevisionId || run.unavailableReason || !scope.runs.some(row => row.runId === run.runId && row.runRevision === run.runRevision))
        invalid();
    const params = new URLSearchParams({ managed_world_id: scope.managedWorldId, expected_run_revision: String(run.runRevision), source_revision_id: run.sourceRevisionId });
    const body = await read(`/api/live/graph-preview/extraction-runs/${encodeURIComponent(run.runId)}/recap-inspection?${params}`, signal);
    if (body.schema !== "dmb_saved_recap_source_v1" || body.managedWorldId !== scope.managedWorldId || body.nativeWorldId !== scope.nativeWorldId
        || body.bindingVersion !== scope.bindingVersion || !isRun(body.run) || typeof body.sourceProse !== "string"
        || (["runId", "runRevision", "runStatus", "sourceArtifactId", "campaignId", "sessionId", "sourceRevisionId", "sourceSha256"] as const).some(key => (body.run as SavedRecapRun)[key] !== run[key]))
        invalid();
    return body as unknown as SavedRecapSource;
}
