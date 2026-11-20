import { authenticatedApiFetch, LiveApiError } from "./liveApi";
import type { SavedRecapSource } from "./savedRecapRunsApi";

/** Coordinates from the loaded APP source; never a candidate digest or a path. */
export interface RecapSourceTarget {
  managedWorldId: string;
  nativeWorldId: string;
  bindingVersion: number;
  campaignId: string;
  session: number;
  sourceArtifactId: string;
  sourceRevisionId: string;
  contentSha256: string;
}
export interface NativeRecapSourceStatus {
  schema_version: "dmb_native_recap_source_status_v2";
  state: "reserved" | "dispatching" | "admitted" | "unavailable" | "conflict" | "unknown";
  run_id: string;
  run_revision: number;
  managed_world_id: string;
  native_world_id: string;
  binding_version: number;
  campaign_id: string;
  session_id: string;
  app_source_artifact_id: string;
  app_source_revision_id: string;
  app_body_sha256: string;
  admission_id: string;
  admission_committed: boolean;
  command_sha256: string | null;
  published_revision_id: string | null;
  evidence_ref_id: string | null;
  failure_code: string | null;
  opening: { state: "not_checked" | "verified" | "unavailable" | "integrity_error" };
}
const record = (v: unknown): v is Record<string, unknown> => typeof v === "object" && v !== null && !Array.isArray(v);
const text = (v: unknown): v is string => typeof v === "string" && !!v && v === v.trim();
const uuid = (v: unknown): v is string => typeof v === "string" && /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(v);
const digest = (v: unknown): v is string => typeof v === "string" && /^[0-9a-f]{64}$/.test(v);
const positive = (v: unknown) => Number.isSafeInteger(v) && Number(v) > 0;
function invalid(): never {
  throw new LiveApiError("The source admission result does not match this saved source. Recover the original request; its outcome is unverified here.", 0);
}
function validTarget(t: RecapSourceTarget) {
  return [t.managedWorldId, t.nativeWorldId, t.campaignId, t.sourceArtifactId].every(text)
    && positive(t.bindingVersion) && positive(t.session) && uuid(t.sourceRevisionId) && digest(t.contentSha256);
}
export function recapSourceTarget(source: SavedRecapSource): RecapSourceTarget | null {
  const run = source.run;
  const match = /^session-([1-9]\d*)$/.exec(run.sessionId ?? "");
  if (source.schema !== "dmb_saved_recap_source_v1" || !text(run.runId) || !positive(run.runRevision) || run.unavailableReason !== null || !match
    || !run.sourceRevisionId || !run.sourceSha256 || !run.campaignId) return null;
  const target = {
    managedWorldId: source.managedWorldId, nativeWorldId: source.nativeWorldId,
    bindingVersion: source.bindingVersion, campaignId: run.campaignId, session: Number(match[1]),
    sourceArtifactId: run.sourceArtifactId, sourceRevisionId: run.sourceRevisionId, contentSha256: run.sourceSha256,
  };
  return validTarget(target) ? target : null;
}
function matchesTarget(v: Record<string, unknown>, t: RecapSourceTarget) {
  return v.managed_world_id === t.managedWorldId && v.native_world_id === t.nativeWorldId
    && v.binding_version === t.bindingVersion && v.campaign_id === t.campaignId && v.session_id === `session-${t.session}`
    && v.app_source_artifact_id === t.sourceArtifactId && v.app_source_revision_id === t.sourceRevisionId
    && v.app_body_sha256 === t.contentSha256;
}
function scope(t: RecapSourceTarget) {
  if (!validTarget(t)) invalid();
  return { managed_world_id: t.managedWorldId, campaign_id: t.campaignId, session: t.session };
}
async function request(input: RecapSourceTarget, body: Record<string, unknown>, prior?: NativeRecapSourceStatus): Promise<NativeRecapSourceStatus> {
  const target = { ...input }, previous = prior ? { ...prior } : undefined;
  const selectedScope = scope(target);
  if (previous && (!matchesTarget(previous as unknown as Record<string, unknown>, target)
    || !uuid(previous.run_id) || !positive(previous.run_revision))) invalid();
  const { response } = await authenticatedApiFetch("/api/live/recap-ingest", {
    method: "POST", cache: "no-store", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ ...selectedScope, ...body }),
  });
  let value: unknown;
  try { value = JSON.parse(await response.text()); }
  catch { throw new LiveApiError(`Source admission response was not JSON (HTTP ${response.status}). The request may have completed; recover it deliberately.`, response.status); }
  if (!response.ok) {
    const detail = record(value) ? value.detail : null;
    const code = record(detail) && text(detail.code) ? detail.code : null;
    const message = typeof detail === "string" ? detail : record(detail) && text(detail.message) ? detail.message : "The source admission operation could not be completed.";
    throw new LiveApiError(message, response.status, { code });
  }
  if (!record(value) || value.schema !== "dmb_raw_recap_ingest_status_v1"
    || value.campaign_id !== target.campaignId || value.session !== target.session) invalid();
  const status = value.native_recap_source;
  if (!record(status) || status.schema_version !== "dmb_native_recap_source_status_v2" || !matchesTarget(status, target)
    || !uuid(status.run_id) || !positive(status.run_revision) || !text(status.admission_id)
    || !["reserved", "dispatching", "admitted", "unavailable", "conflict", "unknown"].includes(String(status.state))
    || typeof status.admission_committed !== "boolean" || !record(status.opening)
    || !["not_checked", "verified", "unavailable", "integrity_error"].includes(String(status.opening.state))
    || !(status.command_sha256 === null || digest(status.command_sha256))
    || ![status.published_revision_id, status.evidence_ref_id, status.failure_code].every(v => v === null || text(v))
    || (previous && (status.run_id !== previous.run_id || Number(status.run_revision) < previous.run_revision))) invalid();
  // Native owns receipt/source verification. These are display and response-scope checks only.
  if (status.state === "admitted" && (!status.admission_committed || status.opening.state !== "verified")) invalid();
  return status as unknown as NativeRecapSourceStatus;
}
export function admitRecapSource(target: RecapSourceTarget) {
  return request(target, {
    operation: "build_graph_preview_bundle", include_graph_extraction: false,
    native_recap_source: { source_artifact_id: target.sourceArtifactId, source_revision_id: target.sourceRevisionId, content_sha256: target.contentSha256 },
  });
}
export function inspectRecapSource(target: RecapSourceTarget, previous: NativeRecapSourceStatus) {
  return request(target, { operation: "inspect_status", native_recap_run_id: previous.run_id }, previous);
}
export function resumeRecapSource(target: RecapSourceTarget, previous: NativeRecapSourceStatus) {
  return request(target, {
    operation: "build_graph_preview_bundle", include_graph_extraction: false,
    native_recap_resume: { run_id: previous.run_id, expected_run_revision: previous.run_revision, command_sha256: previous.command_sha256 },
  }, previous);
}
