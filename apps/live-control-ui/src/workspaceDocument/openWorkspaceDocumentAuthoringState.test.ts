import { describe, expect, it } from "vitest";

import type { WorkspaceDocumentSnapshot } from "../api/types";
import { buildInitialWorkspaceDocumentLocalState } from "../tiptap/state/tiptapLocalState";
import { openWorkspaceDocumentAuthoringState } from "./openWorkspaceDocumentAuthoringState";

const DOC_ID = "11111111-1111-4111-8111-111111111111";
const EMPTY_SHA = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855";

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
      revision: 1,
      created_at: "2026-07-22T00:00:00Z",
      updated_at: "2026-07-22T00:00:00Z",
      source_domain: "worldbuilding",
      document_class: "lore",
      authority_state: "draft",
      visibility_state: "internal",
    },
    markdown: "",
    content_sha256: EMPTY_SHA,
    file_fingerprint: "absent",
    file_exists: false,
    loaded_revision: 1,
    ...overrides,
  };
}

describe("openWorkspaceDocumentAuthoringState", () => {
  it("uses emptyMarkdownFallback export when snapshot markdown is empty", () => {
    const fallback = {
      type: "doc",
      content: [{ type: "paragraph", content: [{ type: "text", text: "Starter body" }] }],
    };
    const opened = openWorkspaceDocumentAuthoringState({
      documentId: DOC_ID,
      snapshot: snapshot(),
      stored: null,
      surface: "build",
      kind: "worldbuilding_source",
      emptyMarkdownFallback: fallback,
    });
    expect(opened.status).toBe("ready");
    expect(opened.localState?.tiptap_json).toEqual(fallback);
    expect(opened.localState?.exported_markdown).toContain("Starter body");
    expect(opened.localState?.base_content_sha256).toBe(EMPTY_SHA);
    expect(opened.localState?.dirty).toBe(false);
  });

  it("rejects plan registry kind on build surface", () => {
    const opened = openWorkspaceDocumentAuthoringState({
      documentId: DOC_ID,
      snapshot: snapshot({
        record: {
          ...snapshot().record,
          kind: "plan",
          target_session: 4,
          source_domain: null,
          document_class: null,
          authority_state: null,
          visibility_state: null,
        },
      }),
      stored: null,
      surface: "build",
      kind: "worldbuilding_source",
    });
    expect(opened.status).toBe("reject");
    expect(opened.localState).toBeNull();
    expect(opened.reconciliation.rejectReason).toMatch(/kind/i);
  });

  it("keeps clean local draft content when server markdown is empty", () => {
    const stored = buildInitialWorkspaceDocumentLocalState({
      documentId: DOC_ID,
      title: "World Lore",
      campaignId: "eldyrwild",
      kind: "worldbuilding_source",
      targetSession: null,
      surface: "build",
      baseRevision: 1,
      baseContentSha256: EMPTY_SHA,
      starterContent: {
        type: "doc",
        content: [{ type: "paragraph", content: [{ type: "text", text: "Local draft body" }] }],
      },
    });
    stored.exported_markdown = "Local draft body";
    const opened = openWorkspaceDocumentAuthoringState({
      documentId: DOC_ID,
      snapshot: snapshot(),
      stored,
      surface: "build",
      kind: "worldbuilding_source",
    });
    expect(opened.status).toBe("ready");
    expect(opened.localState?.exported_markdown).toBe("Local draft body");
    expect(opened.localState?.dirty).toBe(false);
  });

  it("reopens clean when dirty local Markdown is byte-identical to snapshot", () => {
    const body = "# Committed title\n\nServer body.\n";
    const snap = snapshot({
      markdown: body,
      content_sha256: "sha-server",
      loaded_revision: 2,
      file_exists: true,
      file_fingerprint: "present",
      record: {
        ...snapshot().record,
        revision: 2,
      },
    });
    const stored = buildInitialWorkspaceDocumentLocalState({
      documentId: DOC_ID,
      title: "World Lore",
      campaignId: "eldyrwild",
      kind: "worldbuilding_source",
      targetSession: null,
      surface: "build",
      baseRevision: 2,
      baseContentSha256: "sha-server",
      starterContent: {
        type: "doc",
        content: [{ type: "paragraph", content: [{ type: "text", text: "Server body." }] }],
      },
    });
    stored.dirty = true;
    stored.exported_markdown = body;
    const opened = openWorkspaceDocumentAuthoringState({
      documentId: DOC_ID,
      snapshot: snap,
      stored,
      surface: "build",
      kind: "worldbuilding_source",
    });
    expect(opened.status).toBe("ready");
    expect(opened.reconciliation.kind).toBe("clean-match");
    expect(opened.localState?.dirty).toBe(false);
    expect(opened.localState?.exported_markdown).toBe(body);
  });

  it("rehydrates dirty-match from snapshot markdown when source has blocking import diagnostics", () => {
    const unsafeBody = "# Source\n\n```json\n{\"hp\": 95}\n```\n";
    const snap = snapshot({
      markdown: unsafeBody,
      content_sha256: "sha-unsafe",
      loaded_revision: 2,
      file_exists: true,
      file_fingerprint: "present",
      record: {
        ...snapshot().record,
        revision: 2,
      },
    });
    const stored = buildInitialWorkspaceDocumentLocalState({
      documentId: DOC_ID,
      title: "World Lore",
      campaignId: "eldyrwild",
      kind: "worldbuilding_source",
      targetSession: null,
      surface: "build",
      baseRevision: 2,
      baseContentSha256: "sha-unsafe",
      starterContent: {
        type: "doc",
        content: [{ type: "paragraph", content: [{ type: "text", text: "Lossy local body" }] }],
      },
    });
    stored.dirty = true;
    stored.exported_markdown = "# Lossy local export\n";
    const opened = openWorkspaceDocumentAuthoringState({
      documentId: DOC_ID,
      snapshot: snap,
      stored,
      surface: "build",
      kind: "worldbuilding_source",
    });
    expect(opened.status).toBe("ready");
    expect(opened.reconciliation.kind).toBe("dirty-match");
    expect(opened.localState?.exported_markdown).toBe(unsafeBody);
    expect(opened.localState?.dirty).toBe(true);
    expect(opened.localState?.tiptap_json).toEqual(stored.tiptap_json);
  });
});
