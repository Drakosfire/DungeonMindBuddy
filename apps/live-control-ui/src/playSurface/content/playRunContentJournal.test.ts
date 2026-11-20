import { webcrypto } from "node:crypto";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { contentSha256 } from "../playRunEffectiveContent";
import type { PlayRunContent, PlayRunContentCommitRequest } from "../playRunContentTypes";
import { playRunContentJournalKey, validatePlayRunContentJournal, writePlayRunContentJournal, type PlayRunContentIdentity } from "./playRunContentJournal";

const identity: PlayRunContentIdentity = { worldId: "world", runId: "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
  origin: { playable_artifact_id: "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb", playable_revision: 1,
    playable_work_revision_id: "cccccccc-cccc-4ccc-8ccc-cccccccccccc", playable_content_sha256: "d".repeat(64) } };
const markdown = "# Gate\n\nOriginal.\n";
let content: PlayRunContent;

beforeEach(async () => {
  vi.stubGlobal("crypto", webcrypto);
  window.localStorage.clear();
  identity.origin.playable_content_sha256 = await contentSha256(markdown);
  content = { schema_version: "dmb_world_play_run_content_v1", world_id: identity.worldId, run_id: identity.runId, origin: identity.origin, source: "pinned", edition_revision: 0,
    edition_revision_id: null, markdown, content_sha256: await contentSha256(markdown), structure_sha256: "e".repeat(64),
    committed_at: "2026-10-18T00:00:00Z", observed_run_revision: 1 };
});

describe("Play session-copy recovery journal", () => {
  it("keys by the complete World, Run, and immutable source pin", () => {
    const other = { ...identity, origin: { ...identity.origin, playable_revision: 2 } };
    expect(playRunContentJournalKey(identity)).not.toBe(playRunContentJournalKey(other));
    expect(playRunContentJournalKey(identity)).toContain(encodeURIComponent(JSON.stringify([
      identity.worldId, identity.runId, identity.origin.playable_artifact_id, identity.origin.playable_revision,
      identity.origin.playable_work_revision_id, identity.origin.playable_content_sha256,
    ])));
  });

  it("round-trips an exact pending command before transport recovery", async () => {
    const edited = "# Gate\n\nEdited.\n";
    const request: PlayRunContentCommitRequest = { schema_version: "dmb_world_play_run_content_commit_v1", expected_origin: identity.origin,
      expected_edition_revision: 0, expected_content_sha256: content.content_sha256, markdown: edited };
    const serialized = writePlayRunContentJournal(identity, { schema_version: "dmb_play_run_content_journal_v1", identity, accepted: content,
      draft_markdown: edited, draft_generation: 1,
      pending: { commandId: "dddddddd-dddd-4ddd-8ddd-dddddddddddd", draftGeneration: 1, request } });
    const restored = await validatePlayRunContentJournal(serialized, identity);
    expect(restored.pending?.request).toEqual(request);
    expect(restored.draft_markdown).toBe(edited);
    expect(window.localStorage.getItem(playRunContentJournalKey(identity))).toBe(serialized);
  });

  it("rejects an extended identity envelope instead of accepting ambiguous recovery state", async () => {
    const malformed = { schema_version: "dmb_play_run_content_journal_v1", identity: { ...identity,
      origin: { ...identity.origin, unexpected: true } }, accepted: content, draft_markdown: markdown, draft_generation: 0, pending: null };
    await expect(validatePlayRunContentJournal(JSON.stringify(malformed), identity)).rejects.toThrow(/shape/);
  });
});
