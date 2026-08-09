import { act, renderHook, waitFor } from "@testing-library/react";
import type { Editor } from "@tiptap/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import {
  commitTiptapMarkdownWrite,
  getWorkspaceDocumentSnapshot,
  prepareTiptapMarkdownWrite,
} from "../api/liveApi";
import type { WorkspaceDocumentSnapshot } from "../api/types";
import { fixtureWorkspaceDocumentRecord } from "../planSurface/config/planSessionDescriptor";
import { useWorkspaceDocumentAuthoring } from "./useWorkspaceDocumentAuthoring";

vi.mock("../api/liveApi", () => ({
  getWorkspaceDocumentSnapshot: vi.fn(),
  prepareTiptapMarkdownWrite: vi.fn(),
  commitTiptapMarkdownWrite: vi.fn(),
}));

const DOC_ID = "11111111-1111-4111-8111-111111111111";

function snapshot(markdown: string): WorkspaceDocumentSnapshot {
  return {
    schema_version: "dmb_workspace_document_snapshot_v1",
    record: fixtureWorkspaceDocumentRecord({
      document_id: DOC_ID,
      kind: "worldbuilding_source",
      campaign_id: "eldyrwild",
      target_session: null,
      revision: 1,
      content_status: "draft",
    }),
    markdown,
    content_sha256: "sha-source",
    file_fingerprint: "fp-source",
    file_exists: true,
    loaded_revision: 1,
  };
}

function editorWithJson(json: unknown): Editor {
  return { getJSON: vi.fn(() => json) } as unknown as Editor;
}

function editorWithParagraph(text: string): Editor {
  return editorWithJson({
    type: "doc",
    content: [{ type: "paragraph", content: [{ type: "text", text }] }],
  });
}

describe("useWorkspaceDocumentAuthoring Markdown fidelity", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
  });

  it("reattaches source frontmatter unchanged before prepare and commit", async () => {
    const source = "---\r\ntitle: Session 2 Prep\r\nsession: 2\r\n---\r\n# Old body\r\n";
    const committedMarkdown = "---\r\ntitle: Session 2 Prep\r\nsession: 2\r\n---\r\nChanged body\n";
    vi.mocked(getWorkspaceDocumentSnapshot)
      .mockResolvedValueOnce(snapshot(source))
      .mockResolvedValueOnce(snapshot(committedMarkdown));
    vi.mocked(prepareTiptapMarkdownWrite).mockResolvedValue({
      schema_version: "dmb_tiptap_markdown_write_prepare_v1",
      document_id: DOC_ID,
      title: "Session 2 Prep",
      target_relpath: "corpus/session-2.md",
      target_display_path: "corpus/session-2.md",
      registry_revision: 1,
      file_exists: true,
      writer_ok: true,
      writer_phase: "prepare",
      writer_confirm_token: "confirm-token",
      writer_diff: "+Changed body",
      warnings: [],
      diagnostics: [],
    });
    vi.mocked(commitTiptapMarkdownWrite).mockResolvedValue({
      schema_version: "dmb_tiptap_markdown_write_commit_v1",
      document_id: DOC_ID,
      title: "Session 2 Prep",
      target_relpath: "corpus/session-2.md",
      target_display_path: "corpus/session-2.md",
      registry_revision: 2,
      committed_revision: 2,
      committed_record: fixtureWorkspaceDocumentRecord({
        document_id: DOC_ID,
        kind: "worldbuilding_source",
        revision: 2,
        content_status: "committed",
      }),
      normalized_content_sha256: "sha-committed",
      writer_ok: true,
      bytes_written: committedMarkdown.length,
      file_fingerprint: "fp-committed",
      diagnostics: [],
    });

    const { result } = renderHook(() => useWorkspaceDocumentAuthoring({
      documentId: DOC_ID,
      surface: "build",
      kind: "worldbuilding_source",
    }));
    await waitFor(() => expect(result.current.phase).toBe("ready_clean"));

    act(() => {
      result.current.setEditor(editorWithParagraph("Changed body"));
      result.current.markDirty();
    });
    await act(async () => {
      await result.current.saveMarkdown();
    });

    expect(prepareTiptapMarkdownWrite).toHaveBeenCalledWith(expect.objectContaining({
      markdown: committedMarkdown,
    }));
    expect(commitTiptapMarkdownWrite).toHaveBeenCalledWith(expect.objectContaining({
      markdown: committedMarkdown,
    }));
  });

  it("blocks durable save when the loaded source contains unsupported Markdown", async () => {
    vi.mocked(getWorkspaceDocumentSnapshot).mockResolvedValue(
      snapshot("# Source\n\n```json\n{\"hp\": 95}\n```\n"),
    );

    const { result } = renderHook(() => useWorkspaceDocumentAuthoring({
      documentId: DOC_ID,
      surface: "build",
      kind: "worldbuilding_source",
    }));
    await waitFor(() => expect(result.current.phase).toBe("ready_clean"));

    act(() => {
      result.current.setEditor(editorWithParagraph("Changed"));
      result.current.markDirty();
    });
    await act(async () => {
      await result.current.saveMarkdown();
    });

    expect(prepareTiptapMarkdownWrite).not.toHaveBeenCalled();
    expect(commitTiptapMarkdownWrite).not.toHaveBeenCalled();
    expect(result.current.phase).toBe("save_error");
    expect(result.current.error).toContain("cannot round-trip safely");
  });

  it("blocks durable save when the editor creates a node the serializer would flatten", async () => {
    vi.mocked(getWorkspaceDocumentSnapshot).mockResolvedValue(snapshot("# Safe source\n"));

    const { result } = renderHook(() => useWorkspaceDocumentAuthoring({
      documentId: DOC_ID,
      surface: "build",
      kind: "worldbuilding_source",
    }));
    await waitFor(() => expect(result.current.phase).toBe("ready_clean"));

    const codeBlockEditor = editorWithJson({
      type: "doc",
      content: [{ type: "codeBlock", content: [{ type: "text", text: "const hp = 95" }] }],
    });
    act(() => {
      result.current.setEditor(codeBlockEditor);
      result.current.markDirty();
    });
    await act(async () => {
      await result.current.saveMarkdown();
    });

    expect(prepareTiptapMarkdownWrite).not.toHaveBeenCalled();
    expect(commitTiptapMarkdownWrite).not.toHaveBeenCalled();
    expect(result.current.phase).toBe("save_error");
    expect(result.current.error).toContain("cannot be represented safely as Markdown");
  });
});
