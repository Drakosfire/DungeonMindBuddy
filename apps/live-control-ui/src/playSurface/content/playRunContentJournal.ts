import { contentSha256, validatePlayRunContent } from "../playRunEffectiveContent";
import { isCanonicalUuid } from "../runbook/nativeRunbookProjection";
import { samePlayRunContentOrigin } from "./playRunContentProtocol";
import type { PlayRunContent, PlayRunContentCommitRequest, PlayRunContentOrigin } from "../playRunContentTypes";

export interface PlayRunContentIdentity {
  worldId: string;
  runId: string;
  origin: PlayRunContentOrigin;
}

export interface PendingPlayRunContentCommand {
  commandId: string;
  draftGeneration: number;
  request: PlayRunContentCommitRequest;
}

export interface PlayRunContentJournal {
  schema_version: "dmb_play_run_content_journal_v1";
  identity: PlayRunContentIdentity;
  accepted: PlayRunContent;
  draft_markdown: string;
  draft_generation: number;
  pending: PendingPlayRunContentCommand | null;
}

const object = (value: unknown): value is Record<string, unknown> => typeof value === "object" && value !== null && !Array.isArray(value);
const integer = (value: unknown, minimum: number): value is number => Number.isSafeInteger(value) && (value as number) >= minimum;
function exactKeys(value: Record<string, unknown>, keys: string[]): boolean {
  return Object.keys(value).sort().join("|") === [...keys].sort().join("|");
}
function sameIdentity(a: PlayRunContentIdentity, b: PlayRunContentIdentity): boolean {
  return a.worldId === b.worldId && a.runId === b.runId && samePlayRunContentOrigin(a.origin, b.origin);
}

export function playRunContentJournalKey(identity: PlayRunContentIdentity): string {
  return `dmb.play.run-content.v1:${encodeURIComponent(JSON.stringify([
    identity.worldId,
    identity.runId,
    identity.origin.playable_artifact_id,
    identity.origin.playable_revision,
    identity.origin.playable_work_revision_id,
    identity.origin.playable_content_sha256,
  ]))}`;
}

export function hasPlayRunContentJournal(identity: PlayRunContentIdentity): boolean {
  try { return window.localStorage.getItem(playRunContentJournalKey(identity)) !== null; }
  catch { return true; }
}

export function readPlayRunContentJournalRaw(identity: PlayRunContentIdentity): string | null {
  return window.localStorage.getItem(playRunContentJournalKey(identity));
}

export function writePlayRunContentJournal(identity: PlayRunContentIdentity, journal: PlayRunContentJournal): string {
  const serialized = JSON.stringify(journal);
  const key = playRunContentJournalKey(identity);
  window.localStorage.setItem(key, serialized);
  if (window.localStorage.getItem(key) !== serialized) throw new Error("Browser storage did not retain the exact session-copy recovery journal.");
  return serialized;
}

export function removePlayRunContentJournalIfUnchanged(identity: PlayRunContentIdentity, serialized: string): boolean {
  const key = playRunContentJournalKey(identity);
  if (window.localStorage.getItem(key) !== serialized) return false;
  window.localStorage.removeItem(key);
  return window.localStorage.getItem(key) === null;
}

export async function validatePlayRunContentJournal(raw: string, expected: PlayRunContentIdentity): Promise<PlayRunContentJournal> {
  let parsed: unknown;
  try { parsed = JSON.parse(raw); }
  catch { throw new TypeError("Saved session-copy recovery data is not valid JSON."); }
  if (!object(parsed) || !exactKeys(parsed, ["schema_version", "identity", "accepted", "draft_markdown", "draft_generation", "pending"])
    || parsed.schema_version !== "dmb_play_run_content_journal_v1" || !object(parsed.identity)
    || !exactKeys(parsed.identity, ["worldId", "runId", "origin"]) || typeof parsed.identity.worldId !== "string"
    || typeof parsed.identity.runId !== "string" || !object(parsed.identity.origin)
    || !exactKeys(parsed.identity.origin, ["playable_artifact_id", "playable_revision", "playable_work_revision_id", "playable_content_sha256"])
    || !sameIdentity(parsed.identity as unknown as PlayRunContentIdentity, expected)
    || typeof parsed.draft_markdown !== "string" || new TextEncoder().encode(parsed.draft_markdown).byteLength > 1_048_576
    || !integer(parsed.draft_generation, 0)) throw new TypeError("Saved session-copy recovery data has an invalid identity or shape.");

  const accepted = await validatePlayRunContent(parsed.accepted, { worldId: expected.worldId, runId: expected.runId });
  if (!samePlayRunContentOrigin(accepted.origin, expected.origin)) throw new TypeError("Saved session-copy recovery data belongs to another pinned source.");

  let pending: PendingPlayRunContentCommand | null = null;
  if (parsed.pending !== null) {
    const rawPending = parsed.pending;
    if (!object(rawPending) || !exactKeys(rawPending, ["commandId", "draftGeneration", "request"])
      || typeof rawPending.commandId !== "string" || !isCanonicalUuid(rawPending.commandId)
      || !integer(rawPending.draftGeneration, 1) || rawPending.draftGeneration > parsed.draft_generation
      || !object(rawPending.request) || !exactKeys(rawPending.request, ["schema_version", "expected_origin", "expected_edition_revision", "expected_content_sha256", "markdown"])) {
      throw new TypeError("Saved session-copy command journal is invalid.");
    }
    const request = rawPending.request as unknown as PlayRunContentCommitRequest;
    if (request.schema_version !== "dmb_world_play_run_content_commit_v1"
      || !samePlayRunContentOrigin(request.expected_origin, expected.origin)
      || request.expected_edition_revision !== accepted.edition_revision
      || request.expected_content_sha256 !== accepted.content_sha256
      || typeof request.markdown !== "string"
      || await contentSha256(request.markdown) === accepted.content_sha256) {
      throw new TypeError("Saved session-copy command no longer matches its accepted base.");
    }
    pending = rawPending as unknown as PendingPlayRunContentCommand;
  }
  return { ...parsed, accepted, pending } as PlayRunContentJournal;
}
