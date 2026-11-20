import { webcrypto, createHash } from "node:crypto";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { PlayRunContent } from "./playRunContentTypes";
import type { WorldPlayRunRecordV2, WorldOwnedCommittedRevisionV2, PlayRunReferenceManifestV2 } from "../api/types";
import { admitNativeRunbook, isNativeRunbookReadyV2, overlayRuntimeOnV2Ready } from "./runbook/nativeRunbookProjection";
import { admitEffectivePlayRunContent, validatePlayRunContent } from "./playRunEffectiveContent";
const runId = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa";
const artifactId = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb";
const workId = "cccccccc-cccc-4ccc-8ccc-cccccccccccc";
const editionId = "dddddddd-dddd-4ddd-8ddd-dddddddddddd";
const markdown = "<!-- dmb-playable-element:v2 kind=beat id=beat:one -->\n## One\n\n<!-- dmb-playable-element:v2 kind=scene id=scene:one -->\n### Scene\n\nOriginal prose.\n";
const sha = (value: string) => createHash("sha256").update(value).digest("hex");
function fixture() {
  const run: WorldPlayRunRecordV2 = { schema_version: "dmb_world_play_run_record_v2", world_id: "world", run_id: runId,
    playable_artifact_id: artifactId, playable_revision: 2, playable_work_revision_id: workId, playable_content_sha256: sha(markdown),
    run_revision: 3, created_at: "2026-10-18T00:00:00Z", updated_at: "2026-10-18T00:00:00Z",
    progress: { current_beat_id: "beat:one", current_scene_id: "scene:one", selections: {}, resolved_beat_ids: [], notes_by_element_id: { "scene:one": "Note" } } };
  const committed: WorldOwnedCommittedRevisionV2 = { schema_version: "dmb_workspace_committed_revision_v2", scope_mode: "world", world_id: "world",
    document_id: artifactId, kind: "plan", campaign_id: null, title: "Origin", status: "active", object_revision: 2,
    work_revision_id: workId, revision_n: 2, markdown, content_sha256: sha(markdown), has_divergent_working_copy: false, target_relpath: null };
  const manifest: PlayRunReferenceManifestV2 = { schema_version: "dmb_play_run_reference_manifest_v2", run_id: runId, playable_artifact_id: artifactId,
    playable_revision: 2, playable_content_sha256: sha(markdown), sealed_at: "2026-10-18T00:00:00Z", beats: [{ beat_id: "beat:one" }],
    scenes: [{ scene_id: "scene:one", beat_id: "beat:one" }], choices: [], options: [], edges: [] };
  const admitted = admitNativeRunbook({ run, committed, manifest });
  if (!isNativeRunbookReadyV2(admitted)) throw new Error("fixture failed");
  const text = markdown.replace("Original prose.", "Session café 🧙.\n\n| Item | Value |\n| --- | --- |\n| Gate | Open |\n\n> [!GM-NOTE]\n> A callout.");
  const content: PlayRunContent = { schema_version: "dmb_world_play_run_content_v1", world_id: "world", run_id: runId,
    origin: { playable_artifact_id: artifactId, playable_revision: 2, playable_work_revision_id: workId, playable_content_sha256: sha(markdown) },
    source: "edition", edition_revision: 1, edition_revision_id: editionId, markdown: text, content_sha256: sha(text),
    committed_at: "2026-10-18T01:00:00Z", observed_run_revision: 3, structure_sha256: "f".repeat(64) };
  return { admitted, content };
}
beforeEach(() => vi.stubGlobal("crypto", webcrypto));
describe("effective session content admission", () => {
  it("uses effective text and native body nodes while retaining actual origin and note identity", async () => {
    const { admitted, content } = fixture();
    const projected = await admitEffectivePlayRunContent(admitted, content);
    expect(projected.snapshot).toBe(admitted.snapshot);
    expect(projected.run).toBe(admitted.run);
    expect(projected.manifest).toBe(admitted.manifest);
    expect(projected.beats[0].scenes[0].bodyText).toContain("Session café");
    expect(JSON.stringify(projected.beats[0].scenes[0].bodyContent)).toContain("table");
    const overlaid = overlayRuntimeOnV2Ready(projected, { ...admitted.run, run_revision: 4,
      progress: { ...admitted.run.progress, notes_by_element_id: { "scene:one": "New note" } } });
    expect(overlaid?.effectiveContent).toBe(projected.effectiveContent);
    expect(overlaid?.beats[0].scenes[0].bodyText).toContain("Session café");
    expect(overlaid?.run.playable_work_revision_id).toBe(workId);
  });
  it.each(["world_id", "run_id", "content_sha256", "structure_sha256", "committed_at", "edition_revision", "edition_revision_id", "source", "schema_version"])("rejects invalid %s", async (key) => {
    const { content } = fixture();
    await expect(validatePlayRunContent({ ...content, [key]: "wrong" }, { worldId: "world", runId })).rejects.toThrow();
  });
  it("rejects origin contradiction, tampering, unsupported structure and invalid source relations", async () => {
    const { admitted, content } = fixture();
    await expect(admitEffectivePlayRunContent(admitted, { ...content, origin: { ...content.origin, playable_revision: 8 } })).rejects.toThrow(/origin/);
    await expect(admitEffectivePlayRunContent(admitted, { ...content, markdown: "tampered" })).rejects.toThrow(/SHA256/);
    const text = content.markdown.replaceAll("scene:one", "scene:two");
    await expect(admitEffectivePlayRunContent(admitted, { ...content, markdown: text, content_sha256: sha(text) })).rejects.toThrow(/native/);
    await expect(admitEffectivePlayRunContent(admitted, { ...content, source: "pinned" })).rejects.toThrow(/Pinned/);
    await expect(admitEffectivePlayRunContent(admitted, { ...content, edition_revision: 0 })).rejects.toThrow(/identity/);
    await expect(admitEffectivePlayRunContent(admitted, { ...content, committed_at: "2026-02-30T00:00:00Z" })).rejects.toThrow();
  });
  it("admits an unmodified pin as revision zero and rejects extra fields", async () => {
    const { admitted, content } = fixture();
    const pinned = { ...content, source: "pinned", edition_revision: 0, edition_revision_id: null,
      markdown, content_sha256: sha(markdown) };
    expect((await admitEffectivePlayRunContent(admitted, pinned)).effectiveContent?.source).toBe("pinned");
    await expect(admitEffectivePlayRunContent(admitted, { ...pinned, ignored: true })).rejects.toThrow();
  });
});
