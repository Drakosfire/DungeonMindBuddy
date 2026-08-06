import { describe, expect, it } from "vitest";

import type { WorkspaceDocumentSnapshot } from "../api/types";
import { buildInitialWorkspaceDocumentLocalState } from "../tiptap/state/tiptapLocalState";
import { reconcileLocalDraft } from "./reconcileLocalDraft";

const DOC_ID = "11111111-1111-4111-8111-111111111111";

function snapshot(overrides: Partial<WorkspaceDocumentSnapshot> = {}): WorkspaceDocumentSnapshot {
  return {
    schema_version: "dmb_workspace_document_snapshot_v1",
    record: {
      schema_version: "dmb_workspace_document_record_v1",
      document_id: DOC_ID,
      title: "World Lore",
      campaign_id: "eldyrwild",
      target_session: null,
      kind: "worldbuilding_source",
      target_relpath: `out/workspace/worldbuilding/${DOC_ID}.md`,
      status: "active",
      content_status: "draft",
      revision: 2,
      created_at: "2026-07-22T00:00:00Z",
      updated_at: "2026-07-22T00:00:00Z",
      source_domain: "worldbuilding",
      document_class: "lore",
      authority_state: "draft",
      visibility_state: "internal",
    },
    markdown: "# Committed title\n\nServer body.\n",
    content_sha256: "sha-server",
    file_fingerprint: "present",
    file_exists: true,
    loaded_revision: 2,
    ...overrides,
  };
}

describe("reconcileLocalDraft", () => {
  it("uses snapshot markdown when no local draft exists", () => {
    const result = reconcileLocalDraft(snapshot(), null);
    expect(result.kind).toBe("none");
    expect(result.markdown).toContain("Server body.");
  });

  it("uses snapshot markdown on clean base match", () => {
    const local = buildInitialWorkspaceDocumentLocalState({
      documentId: DOC_ID,
      title: "World Lore",
      campaignId: "eldyrwild",
      kind: "worldbuilding_source",
      targetSession: null,
      surface: "build",
      baseRevision: 2,
      baseContentSha256: "sha-server",
      starterContent: { type: "doc", content: [] },
    });
    const result = reconcileLocalDraft(snapshot(), local);
    expect(result.kind).toBe("clean-match");
    expect(result.markdown).toContain("Server body.");
  });

  it("restores dirty local draft when base matches and Markdown differs", () => {
    const local = buildInitialWorkspaceDocumentLocalState({
      documentId: DOC_ID,
      title: "World Lore",
      campaignId: "eldyrwild",
      kind: "worldbuilding_source",
      targetSession: null,
      surface: "build",
      baseRevision: 2,
      baseContentSha256: "sha-server",
      starterContent: { type: "doc", content: [] },
    });
    local.dirty = true;
    local.exported_markdown = "# Local edits\n";
    const result = reconcileLocalDraft(snapshot(), local);
    expect(result.kind).toBe("dirty-match");
    expect(result.markdown).toBe("# Local edits\n");
  });

  it("clears stale dirty when base matches and Markdown is byte-identical to snapshot", () => {
    const snap = snapshot();
    const local = buildInitialWorkspaceDocumentLocalState({
      documentId: DOC_ID,
      title: "World Lore",
      campaignId: "eldyrwild",
      kind: "worldbuilding_source",
      targetSession: null,
      surface: "build",
      baseRevision: 2,
      baseContentSha256: "sha-server",
      starterContent: { type: "doc", content: [] },
    });
    local.dirty = true;
    local.exported_markdown = snap.markdown;
    const result = reconcileLocalDraft(snap, local);
    expect(result.kind).toBe("clean-match");
    expect(result.markdown).toBe(snap.markdown);
  });

  it("enters conflict when dirty local draft base mismatches", () => {
    const local = buildInitialWorkspaceDocumentLocalState({
      documentId: DOC_ID,
      title: "World Lore",
      campaignId: "eldyrwild",
      kind: "worldbuilding_source",
      targetSession: null,
      surface: "build",
      baseRevision: 1,
      baseContentSha256: "sha-old",
      starterContent: { type: "doc", content: [] },
    });
    local.dirty = true;
    local.exported_markdown = "# Local edits\n";
    const result = reconcileLocalDraft(snapshot(), local);
    expect(result.kind).toBe("conflict");
    expect(result.conflictReason).toMatch(/changed while a dirty local draft/i);
  });

  it("rejects malformed local document ids", () => {
    const local = buildInitialWorkspaceDocumentLocalState({
      documentId: "22222222-2222-4222-8222-222222222222",
      title: "Other",
      campaignId: "eldyrwild",
      kind: "worldbuilding_source",
      targetSession: null,
      surface: "build",
      baseRevision: 2,
      baseContentSha256: "sha-server",
      starterContent: { type: "doc", content: [] },
    });
    const result = reconcileLocalDraft(snapshot(), local);
    expect(result.kind).toBe("reject");
  });
});
