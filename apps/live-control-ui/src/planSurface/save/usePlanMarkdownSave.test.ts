import { act, renderHook, waitFor } from "@testing-library/react";
import type { Editor } from "@tiptap/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { commitTiptapMarkdownWrite, prepareTiptapMarkdownWrite } from "../../api/liveApi";
import { usePlanMarkdownSave } from "./usePlanMarkdownSave";
import type { PlanSessionDescriptor } from "../types";

vi.mock("../../api/liveApi", () => ({
  prepareTiptapMarkdownWrite: vi.fn(),
  commitTiptapMarkdownWrite: vi.fn(),
}));

const sessionDescriptor: PlanSessionDescriptor = {
  surfaceId: "plan",
  campaignId: "longmont-c2",
  campaignLabel: "Longmont C2",
  prepSession: 23,
  memorySession: 21,
  liveSession: 22,
  sourceStatusLabel: "Session 21",
  sourceStatusKind: "unknown",
  planningDocument: {
    documentId: "longmont-c2-session-23-prep",
    title: "C2 Session 23 Prep",
    targetRelpath:
      "corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/Session Prep/Session 23 Prep.md",
    storageKey: "dmb.planCanvas.longmont-c2.23.longmont-c2-session-23-prep",
    status: "local_draft",
  },
};

function createEditor(initialText: string) {
  let text = initialText;
  return {
    getJSON: vi.fn(() => ({
      type: "doc",
      content: [{ type: "paragraph", content: [{ type: "text", text }] }],
    })),
    editTo(nextText: string) {
      text = nextText;
    },
  } as unknown as Editor & { editTo: (nextText: string) => void };
}

describe("usePlanMarkdownSave", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(prepareTiptapMarkdownWrite).mockResolvedValue({
      schema_version: "dmb_tiptap_markdown_write_prepare_v1",
      document_id: "longmont-c2-session-23-prep",
      title: "C2 Session 23 Prep",
      target_relpath: sessionDescriptor.planningDocument.targetRelpath,
      target_display_path: sessionDescriptor.planningDocument.targetRelpath,
      file_exists: false,
      writer_ok: true,
      writer_phase: "prepare",
      writer_confirm_token: "confirm-token",
      writer_diff: "+# C2 Session 23 Prep\n",
      warnings: [],
      diagnostics: [],
    });
  });

  it("invalidates preview and disables commit when editor content changes after preview", async () => {
    const editor = createEditor("C2 Session 23 Prep");
    const { result } = renderHook(() => usePlanMarkdownSave({ editor, sessionDescriptor }));

    await act(async () => {
      await result.current.prepareSave();
    });

    await waitFor(() => {
      expect(result.current.state.status).toBe("preview_ready");
    });
    expect(result.current.canCommit).toBe(true);

    act(() => {
      result.current.markDirty();
    });

    expect(result.current.state.status).toBe("dirty");
    expect(result.current.state.prepared).toBeUndefined();
    expect(result.current.state.preparedMarkdown).toBeUndefined();
    expect(result.current.state.error).toMatch(/Preview the save again/i);
    expect(result.current.canCommit).toBe(false);

    await act(async () => {
      await result.current.commitSave();
    });

    expect(commitTiptapMarkdownWrite).not.toHaveBeenCalled();
  });
});
