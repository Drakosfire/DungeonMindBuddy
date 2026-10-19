import { contentSha256 } from "../playRunEffectiveContent";
import { isCanonicalUuid } from "../runbook/nativeRunbookProjection";
import type { PlayRunContentCommitRequest, PlayRunContentOrigin, PlayRunContentReceipt } from "../playRunContentTypes";

const digest = (value: unknown): value is string => typeof value === "string" && /^[0-9a-f]{64}$/.test(value);
const integer = (value: unknown, minimum: number): value is number => Number.isSafeInteger(value) && (value as number) >= minimum;
const object = (value: unknown): value is Record<string, unknown> => typeof value === "object" && value !== null && !Array.isArray(value);
const ORIGIN_KEYS = ["playable_artifact_id", "playable_revision", "playable_work_revision_id", "playable_content_sha256"];
const RECEIPT_KEYS = ["schema_version", "world_id", "run_id", "command_id", "request_sha256", "origin", "expected_edition_revision", "expected_content_sha256", "accepted_edition_revision", "accepted_edition_revision_id", "accepted_content_sha256", "committed_at", "observed_run_revision"];

function exactKeys(value: Record<string, unknown>, expected: string[]): boolean {
  return Object.keys(value).sort().join("|") === [...expected].sort().join("|");
}

function validOrigin(value: unknown): value is PlayRunContentOrigin {
  return object(value) && exactKeys(value, ORIGIN_KEYS)
    && typeof value.playable_artifact_id === "string" && isCanonicalUuid(value.playable_artifact_id)
    && integer(value.playable_revision, 1)
    && typeof value.playable_work_revision_id === "string" && isCanonicalUuid(value.playable_work_revision_id)
    && digest(value.playable_content_sha256);
}

function canonicalJson(value: unknown): string {
  if (Array.isArray(value)) return `[${value.map(canonicalJson).join(",")}]`;
  if (object(value)) return `{${Object.keys(value).sort().map(key => `${JSON.stringify(key)}:${canonicalJson(value[key])}`).join(",")}}`;
  return JSON.stringify(value) ?? "null";
}

export function samePlayRunContentOrigin(left: PlayRunContentOrigin, right: PlayRunContentOrigin): boolean {
  return left.playable_artifact_id === right.playable_artifact_id
    && left.playable_revision === right.playable_revision
    && left.playable_work_revision_id === right.playable_work_revision_id
    && left.playable_content_sha256 === right.playable_content_sha256;
}

function receiptTime(value: unknown): value is string {
  return typeof value === "string"
    && /^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(?:\.\d+)?(?:Z|[+-]\d\d:\d\d)$/.test(value)
    && Number.isFinite(Date.parse(value));
}

/** Validate the server receipt against the exact immutable journal request. */
export async function validatePlayRunContentReceipt(
  value: unknown,
  expected: { worldId: string; runId: string; commandId: string; origin: PlayRunContentOrigin; request: PlayRunContentCommitRequest },
): Promise<PlayRunContentReceipt> {
  if (!object(value) || !exactKeys(value, RECEIPT_KEYS) || !validOrigin(value.origin)
    || value.schema_version !== "dmb_world_play_run_content_receipt_v1"
    || value.world_id !== expected.worldId || value.run_id !== expected.runId || value.command_id !== expected.commandId
    || !isCanonicalUuid(expected.runId) || !isCanonicalUuid(expected.commandId)
    || !digest(value.request_sha256) || !integer(value.expected_edition_revision, 0)
    || !digest(value.expected_content_sha256) || !integer(value.accepted_edition_revision, 1)
    || typeof value.accepted_edition_revision_id !== "string" || !isCanonicalUuid(value.accepted_edition_revision_id)
    || !digest(value.accepted_content_sha256) || !receiptTime(value.committed_at)
    || !integer(value.observed_run_revision, 1)) throw new TypeError("Session save receipt has an invalid shape or identity.");

  if (!samePlayRunContentOrigin(value.origin, expected.origin)
    || expected.request.schema_version !== "dmb_world_play_run_content_commit_v1"
    || !samePlayRunContentOrigin(expected.request.expected_origin, expected.origin)
    || value.expected_edition_revision !== expected.request.expected_edition_revision
    || value.accepted_edition_revision !== expected.request.expected_edition_revision + 1
    || value.expected_content_sha256 !== expected.request.expected_content_sha256
    || value.accepted_content_sha256 !== await contentSha256(expected.request.markdown)
    || (expected.request.expected_run_revision !== undefined && value.observed_run_revision !== expected.request.expected_run_revision)) {
    throw new TypeError("Session save receipt does not acknowledge the journaled base and exact content.");
  }

  const requestDigest = await contentSha256(canonicalJson({
    world_id: expected.worldId,
    run_id: expected.runId,
    command_id: expected.commandId,
    ...expected.request,
  }));
  if (value.request_sha256 !== requestDigest) throw new TypeError("Session save receipt does not match the journaled command.");
  return value as unknown as PlayRunContentReceipt;
}
