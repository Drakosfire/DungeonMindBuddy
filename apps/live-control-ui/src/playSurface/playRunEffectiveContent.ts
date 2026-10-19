import type { PlayRunContent } from "./playRunContentTypes";
import { isCanonicalUuid, projectEffectiveV2Content, type NativeRunbookReadyV2 } from "./runbook/nativeRunbookProjection";

export const SESSION_COPY_AGENT_UNAVAILABLE = "Buddy is temporarily unavailable for this session copy. Its Agent context still uses the original Plan; session-copy context support is coming next.";
const digest = (value: unknown): value is string => typeof value === "string" && /^[0-9a-f]{64}$/.test(value);
const integer = (value: unknown, minimum: number): value is number => Number.isSafeInteger(value) && (value as number) >= minimum;
const object = (value: unknown): value is Record<string, unknown> => typeof value === "object" && value !== null && !Array.isArray(value);
function exactKeys(value: Record<string, unknown>, keys: string[]): boolean {
  return Object.keys(value).sort().join("|") === [...keys].sort().join("|");
}
function timestamp(value: unknown): value is string {
  if (typeof value !== "string" || !/^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(?:\.\d+)?(?:Z|[+-]\d\d:\d\d)$/.test(value) || !Number.isFinite(Date.parse(value))) return false;
  const [year, month, day] = value.slice(0, 10).split("-").map(Number);
  const date = new Date(Date.UTC(year, month - 1, day));
  return date.getUTCFullYear() === year && date.getUTCMonth() === month - 1 && date.getUTCDate() === day;
}
export async function contentSha256(markdown: string): Promise<string> {
  const bytes = new TextEncoder().encode(markdown);
  return [...new Uint8Array(await crypto.subtle.digest("SHA-256", bytes))].map(n => n.toString(16).padStart(2, "0")).join("");
}
/** Validate actual transport bytes before they can acquire a projection identity. */
export async function validatePlayRunContent(value: unknown, expected: { worldId: string; runId: string }): Promise<PlayRunContent> {
  if (!object(value) || !exactKeys(value, ["schema_version", "world_id", "run_id", "origin", "source", "edition_revision", "edition_revision_id", "markdown", "content_sha256", "committed_at", "observed_run_revision", "structure_sha256"])) throw new TypeError("Session content response has an invalid shape.");
  const origin = value.origin;
  if (value.schema_version !== "dmb_world_play_run_content_v1" || value.world_id !== expected.worldId || value.run_id !== expected.runId || !isCanonicalUuid(expected.runId)
    || !object(origin) || !exactKeys(origin, ["playable_artifact_id", "playable_revision", "playable_work_revision_id", "playable_content_sha256"])
    || typeof origin.playable_artifact_id !== "string" || !isCanonicalUuid(origin.playable_artifact_id)
    || typeof origin.playable_work_revision_id !== "string" || !isCanonicalUuid(origin.playable_work_revision_id)
    || !integer(origin.playable_revision, 1) || !digest(origin.playable_content_sha256)
    || !integer(value.edition_revision, 0) || !digest(value.content_sha256) || !digest(value.structure_sha256)
    || !integer(value.observed_run_revision, 1) || !timestamp(value.committed_at) || typeof value.markdown !== "string") throw new TypeError("Session content identity or witness is invalid.");
  if (value.source === "pinned") {
    if (value.edition_revision !== 0 || value.edition_revision_id !== null || value.content_sha256 !== origin.playable_content_sha256) throw new TypeError("Pinned session content has an edition identity.");
  } else if (value.source !== "edition" || value.edition_revision < 1 || typeof value.edition_revision_id !== "string" || !isCanonicalUuid(value.edition_revision_id)) throw new TypeError("Session edition identity is invalid.");
  if (await contentSha256(value.markdown) !== value.content_sha256) throw new TypeError("Session content SHA256 does not match its exact UTF8 Markdown.");
  return value as unknown as PlayRunContent;
}
export async function admitEffectivePlayRunContent(original: NativeRunbookReadyV2, value: unknown): Promise<NativeRunbookReadyV2> {
  const run = original.run;
  if (run.schema_version !== "dmb_world_play_run_record_v2") throw new TypeError("Effective session content requires a World Run.");
  const content = await validatePlayRunContent(value, { worldId: run.world_id, runId: run.run_id });
  const origin = content.origin;
  if (origin.playable_artifact_id !== run.playable_artifact_id || origin.playable_revision !== run.playable_revision
    || origin.playable_work_revision_id !== run.playable_work_revision_id || origin.playable_content_sha256 !== run.playable_content_sha256) throw new TypeError("Session content origin does not match the Run pin.");
  if (content.source === "pinned" && content.markdown !== original.snapshot.markdown) throw new TypeError("Pinned session text disagrees with the retained origin.");
  const projected = projectEffectiveV2Content(original, content);
  if (!projected) throw new TypeError("Session content failed native structure or renderability admission.");
  return projected;
}
