import { act, renderHook, waitFor } from "@testing-library/react";
import type { Editor } from "@tiptap/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { commitTiptapMarkdownWrite, prepareTiptapMarkdownWrite } from "../../api/liveApi";
import { fixturePlanSessionDescriptor, FIXTURE_DOC_ID } from "../config/planSessionDescriptor";
import { usePlanMarkdownSave } from "./usePlanMarkdownSave";

vi.mock("../../api/liveApi", () => ({
  prepareTiptapMarkdownWrite: vi.fn(),
  commitTiptapMarkdownWrite: vi.fn(),
}));

const sessionDescriptor = fixturePlanSessionDescriptor({ memorySession: 21 });
const planningDocument = sessionDescriptor.planningDocument;

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
      document_id: FIXTURE_DOC_ID,
      title: "C2 Session 23 Prep",
      target_relpath: planningDocument.targetRelpath!,
      target_display_path: planningDocument.targetRelpath!,
      registry_revision: 1,
      file_exists: false,
      writer_ok: true,
      writer_phase: "prepare",
      writer_confirm_token: "confirm-token",
      writer_diff: "+# C2 Session 23 Prep\n",
      warnings: [],
      diagnostics: [],
    });
    vi.mocked(commitTiptapMarkdownWrite).mockResolvedValue({
      schema_version: "dmb_tiptap_markdown_write_commit_v1",
      document_id: FIXTURE_DOC_ID,
      title: "C2 Session 23 Prep",
      target_relpath: planningDocument.targetRelpath!,
      target_display_path: planningDocument.targetRelpath!,
      registry_revision: 2,
      writer_ok: true,
      writer_phase: "commit",
      bytes_written: 42,
      file_fingerprint: "abc123",
      diagnostics: ["reviewed Markdown file written"],
    });
  });

  it("prepares and commits in one saveMarkdown call", async () => {
    const editor = createEditor("C2 Session 23 Prep");
    const { result } = renderHook(() => usePlanMarkdownSave({ editor, planningDocument }));

    await act(async () => {
      await result.current.saveMarkdown();
    });

    await waitFor(() => {
      expect(result.current.state.status).toBe("committed");
    });
    expect(prepareTiptapMarkdownWrite).toHaveBeenCalledWith({
      document_id: FIXTURE_DOC_ID,
      markdown: expect.stringContaining("C2 Session 23 Prep"),
      expected_revision: planningDocument.revision,
    });
    expect(commitTiptapMarkdownWrite).toHaveBeenCalledTimes(1);
    expect(result.current.saveDisabled).toBe(false);
  });

  it("marks dirty after a successful save when the board changes", async () => {
    const editor = createEditor("C2 Session 23 Prep");
    const { result } = renderHook(() => usePlanMarkdownSave({ editor, planningDocument }));

    await act(async () => {
      await result.current.saveMarkdown();
    });

    act(() => {
      result.current.markDirty();
    });

    expect(result.current.state.status).toBe("dirty");
  });
});
