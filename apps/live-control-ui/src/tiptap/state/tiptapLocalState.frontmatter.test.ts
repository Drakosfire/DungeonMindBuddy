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

  it("does not re-derive exported_markdown from TipTap when stored source is unsafe", () => {
    const unsafeSource = "# Source\n\n```json\n{\"hp\": 95}\n```\n";
    const state = {
      schema_version: WORKSPACE_DOCUMENT_LOCAL_STATE_SCHEMA,
      document_id: "11111111-1111-4111-8111-111111111111",
      title: "Unsafe",
      campaign_id: "longmont-c2",
      kind: "worldbuilding_source" as const,
      target_session: null,
      surface: "build" as const,
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
      { getItem: () => JSON.stringify(state) },
      state.document_id,
    );

    expect(restored?.exported_markdown).toBe(unsafeSource);
    expect(restored?.exported_markdown).not.toContain("Looks safe in editor");
  });
});
