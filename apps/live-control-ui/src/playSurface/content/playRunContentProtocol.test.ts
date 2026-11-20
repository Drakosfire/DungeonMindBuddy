import { webcrypto } from "node:crypto";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { contentSha256 } from "../playRunEffectiveContent";
import type { PlayRunContentCommitRequest, PlayRunContentOrigin, PlayRunContentReceipt } from "../playRunContentTypes";
import { validatePlayRunContentReceipt } from "./playRunContentProtocol";

const worldId = "world";
const runId = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa";
const commandId = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb";
const artifactId = "cccccccc-cccc-4ccc-8ccc-cccccccccccc";
const workId = "dddddddd-dddd-4ddd-8ddd-dddddddddddd";
const origin: PlayRunContentOrigin = { playable_artifact_id: artifactId, playable_revision: 2,
  playable_work_revision_id: workId, playable_content_sha256: "a".repeat(64) };
const request: PlayRunContentCommitRequest = { schema_version: "dmb_world_play_run_content_commit_v1", expected_origin: origin,
  expected_edition_revision: 0, expected_content_sha256: origin.playable_content_sha256, markdown: "Exact café 🧙\r\n" };
const canonicalJson = (value: unknown): string => Array.isArray(value) ? `[${value.map(canonicalJson).join(",")}]`
  : typeof value === "object" && value !== null ? `{${Object.keys(value).sort().map(key => `${JSON.stringify(key)}:${canonicalJson((value as Record<string, unknown>)[key])}`).join(",")}}`
    : JSON.stringify(value) ?? "null";

async function receipt(): Promise<PlayRunContentReceipt> {
  return { schema_version: "dmb_world_play_run_content_receipt_v1", world_id: worldId, run_id: runId, command_id: commandId,
    request_sha256: await contentSha256(canonicalJson({ world_id: worldId, run_id: runId, command_id: commandId, ...request })),
    origin, expected_edition_revision: 0, expected_content_sha256: request.expected_content_sha256,
    accepted_edition_revision: 1, accepted_edition_revision_id: "eeeeeeee-eeee-4eee-8eee-eeeeeeeeeeee",
    accepted_content_sha256: await contentSha256(request.markdown), committed_at: "2026-10-18T00:00:00Z", observed_run_revision: 3 };
}

describe("Play session-copy receipt protocol", () => {
  beforeEach(() => vi.stubGlobal("crypto", webcrypto));

  it("accepts only the exact command, original pin, base, and UTF-8 body", async () => {
    const valid = await receipt();
    await expect(validatePlayRunContentReceipt(valid, { worldId, runId, commandId, origin, request })).resolves.toEqual(valid);
    await expect(validatePlayRunContentReceipt({ ...valid, command_id: runId }, { worldId, runId, commandId, origin, request })).rejects.toThrow(/identity|command/);
    await expect(validatePlayRunContentReceipt({ ...valid, request_sha256: "f".repeat(64) }, { worldId, runId, commandId, origin, request })).rejects.toThrow(/journaled command/);
    await expect(validatePlayRunContentReceipt({ ...valid, accepted_content_sha256: "f".repeat(64) }, { worldId, runId, commandId, origin, request })).rejects.toThrow(/exact content/);
    await expect(validatePlayRunContentReceipt({ ...valid, accepted_edition_revision: 2 }, { worldId, runId, commandId, origin, request })).rejects.toThrow(/exact content/);
    await expect(validatePlayRunContentReceipt({ ...valid, extra: true }, { worldId, runId, commandId, origin, request })).rejects.toThrow(/shape/);
  });
});
