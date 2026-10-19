import { webcrypto } from "node:crypto";
import { beforeEach, expect, it, vi } from "vitest";
import { createPlaySceneEditBridge, type PlaySceneEditorState } from "./playSceneEditBridge";
import type { PlaySceneEditRecord } from "../../api/playSceneEditApi";
import { contentSha256 } from "../playRunEffectiveContent";
beforeEach(() => vi.stubGlobal("crypto", webcrypto));
it("checks exact bytes and current scene/edition/note revision before approved apply", async () => {
  const markdown = "🧙 prefix\n\nBefore.\nSuffix"; const before = "Before.\n"; const replacement = "After.\n";
  const candidate = markdown.replace(before, replacement);
  const origin = { playable_artifact_id: "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb", playable_revision: 1, playable_work_revision_id: "cccccccc-cccc-4ccc-8ccc-cccccccccccc", playable_content_sha256: await contentSha256(markdown) };
  const state: PlaySceneEditorState = { content: { schema_version: "dmb_world_play_run_content_v1", world_id: "world", run_id: "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa", origin, source: "pinned", edition_revision: 0, edition_revision_id: null, markdown, content_sha256: origin.playable_content_sha256, committed_at: "2026-10-18T00:00:00Z", structure_sha256: "a".repeat(64), observed_run_revision: 3 },
    runRevision: 3, sceneId: "scene:gate", clean: true, allowed: true, draftMarkdown: markdown, applyReviewed: vi.fn(), remount: vi.fn() };
  const record: PlaySceneEditRecord = { schema_version: "dmb_play_scene_edit_proposal_v1", world_id: "world", run_id: state.content.run_id, proposal_id: "dddddddd-dddd-4ddd-8ddd-dddddddddddd", instruction: "Edit", status: "ready", failure_code: null, created_at: "", updated_at: "", basis: { run_revision: 3, scene_id: "scene:gate", content_basis: { edition_revision: 0, edition_revision_id: null, content_sha256: state.content.content_sha256 }, origin, scene_note_sha256: null }, result: { schema_version: "dmb_play_scene_edit_result_v1", before_markdown: before, replacement_markdown: replacement, candidate_markdown: candidate, candidate_sha256: await contentSha256(candidate), body_start_utf8: new TextEncoder().encode("🧙 prefix\n\n").length, body_end_utf8: new TextEncoder().encode("🧙 prefix\n\n"+before).length, summary: "Edit", assumptions: [], model: "test", model_observed: true, model_latency_ms: 1, wall_latency_ms: 1 } };
  const bridge = createPlaySceneEditBridge(() => state);
  expect(bridge.matches(record)).toBe(true);
  state.runRevision = 4; expect(bridge.matches(record)).toBe(false);
  await expect(bridge.apply(record)).rejects.toThrow(/changed/);
  state.runRevision = 3; state.clean = false; expect(bridge.matches(record)).toBe(false);
  state.clean = true; state.sceneId = "scene:lake"; expect(bridge.matches(record)).toBe(false);
  state.sceneId = "scene:gate";
  await expect(bridge.apply({ ...record, result: { ...record.result!, candidate_markdown: candidate+"outside" } })).rejects.toThrow(/Before\/After/);
  await bridge.apply(record);
  expect(state.applyReviewed).toHaveBeenCalledExactlyOnceWith(candidate, 3);
});
