import { describe, expect, it } from "vitest";

import {
  readWorkspaceDocumentLocalState,
  WORKSPACE_DOCUMENT_LOCAL_STATE_SCHEMA,
} from "./tiptapLocalState";

describe("workspace local-state source envelope", () => {
  it("retains YAML frontmatter while re-deriving editable Markdown", () => {
    const state = {
      schema_version: WORKSPACE_DOCUMENT_LOCAL_STATE_SCHEMA,
      document_id: "11111111-1111-4111-8111-111111111111",
      title: "Session 2 Prep",
      campaign_id: "longmont-c2",
      kind: "plan",
      target_session: 2,
      surface: "plan",
      base_revision: 4,
      base_content_sha256: "abc",
      tiptap_json: {
        type: "doc",
        content: [
          { type: "heading", attrs: { level: 4 }, content: [{ type: "text", text: "New body" }] },
        ],
      },
      exported_markdown: "---\ntitle: Session 2 Prep\nsession: 2\n---\n# Old body\n",
      exported_markdown_authoritative: false,
      dirty: true,
      created_at: "2026-08-09T00:00:00.000Z",
      updated_at: "2026-08-09T00:00:00.000Z",
      last_local_save_at: "2026-08-09T00:00:00.000Z",
    };

    const restored = readWorkspaceDocumentLocalState(
      { getItem: () => JSON.stringify(state) },
      state.document_id,
    );

    expect(restored?.exported_markdown).toBe(
      "---\ntitle: Session 2 Prep\nsession: 2\n---\n#### New body\n",
    );
  });

  it("does not re-derive exported_markdown when the authority bit is sealed", () => {
    const authoritativeSource = "# Authoritative source\n\nKept even if TipTap differs.\n";
    const state = {
      schema_version: WORKSPACE_DOCUMENT_LOCAL_STATE_SCHEMA,
      document_id: "11111111-1111-4111-8111-111111111111",
      title: "Sealed",
      campaign_id: "longmont-c2",
      kind: "worldbuilding_source" as const,
      target_session: null,
      surface: "build" as const,
      base_revision: 1,
      base_content_sha256: "sha",
      tiptap_json: {
        type: "doc",
        content: [{ type: "paragraph", content: [{ type: "text", text: "Looks safe in editor" }] }],
      },
      exported_markdown: authoritativeSource,
      // Bit alone gates derive — independent of live import diagnostics / parser upgrades.
      exported_markdown_authoritative: true,
      dirty: true,
      created_at: "2026-08-09T00:00:00.000Z",
      updated_at: "2026-08-09T00:00:00.000Z",
      last_local_save_at: "2026-08-09T00:00:00.000Z",
    };

    const restored = readWorkspaceDocumentLocalState(
      { getItem: () => JSON.stringify(state) },
      state.document_id,
    );

    expect(restored?.exported_markdown).toBe(authoritativeSource);
    expect(restored?.exported_markdown).not.toContain("Looks safe in editor");
    expect(restored?.exported_markdown_authoritative).toBe(true);
  });

  it("migrates v3 unsafe drafts by sealing exported_markdown_authoritative", () => {
    const unsafeSource = "# Source\n\n```json\n{\"hp\": 95}\n```\n";
    const v3 = {
      schema_version: "dmb_workspace_document_local_state_v3",
      document_id: "11111111-1111-4111-8111-111111111111",
      title: "Unsafe",
      campaign_id: "longmont-c2",
      kind: "worldbuilding_source",
      target_session: null,
      surface: "build",
      base_revision: 1,
      base_content_sha256: "sha-unsafe",
      tiptap_json: {
        type: "doc",
        content: [{ type: "paragraph", content: [{ type: "text", text: "Looks safe in editor" }] }],
      },
      exported_markdown: unsafeSource,
      dirty: true,
      created_at: "2026-08-09T00:00:00.000Z",
      updated_at: "2026-08-09T00:00:00.000Z",
      last_local_save_at: "2026-08-09T00:00:00.000Z",
    };

    const restored = readWorkspaceDocumentLocalState(
      { getItem: () => JSON.stringify(v3) },
      v3.document_id,
    );

    expect(restored?.schema_version).toBe(WORKSPACE_DOCUMENT_LOCAL_STATE_SCHEMA);
    expect(restored?.exported_markdown_authoritative).toBe(true);
    expect(restored?.exported_markdown).toBe(unsafeSource);
  });
});
