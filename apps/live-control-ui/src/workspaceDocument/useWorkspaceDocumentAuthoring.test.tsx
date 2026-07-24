import { act, renderHook, waitFor } from "@testing-library/react";
import type { Editor } from "@tiptap/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import {
  commitTiptapMarkdownWrite,
  getWorkspaceDocumentSnapshot,
  prepareTiptapMarkdownWrite,
} from "../api/liveApi";
import type { WorkspaceDocumentSnapshot } from "../api/types";
import {
  FIXTURE_DOC_ID,
  fixtureWorkspaceDocumentRecord,
} from "../planSurface/config/planSessionDescriptor";
import {
  workspaceDocumentStorageKey,
} from "../tiptap/state/tiptapLocalState";
import { useWorkspaceDocumentAuthoring } from "./useWorkspaceDocumentAuthoring";

vi.mock("../api/liveApi", () => ({
  getWorkspaceDocumentSnapshot: vi.fn(),
  prepareTiptapMarkdownWrite: vi.fn(),
  commitTiptapMarkdownWrite: vi.fn(),
}));

const BUILD_DOC_ID = "11111111-1111-4111-8111-111111111111";

function buildSnapshot(overrides: Partial<WorkspaceDocumentSnapshot> = {}): WorkspaceDocumentSnapshot {
  const record = fixtureWorkspaceDocumentRecord({
    document_id: BUILD_DOC_ID,
    kind: "worldbuilding_source",
    campaign_id: "eldyrwild",
    target_session: null,
    revision: 1,
    content_status: "draft",
  });
  return {
    schema_version: "dmb_workspace_document_snapshot_v1",
    record,
    markdown: "# Build Source\n",
    content_sha256: "sha-build",
    file_fingerprint: "absent",
    file_exists: false,
    loaded_revision: 1,
    ...overrides,
  };
}

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

describe("useWorkspaceDocumentAuthoring", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
    vi.mocked(getWorkspaceDocumentSnapshot).mockResolvedValue(buildSnapshot());
    vi.mocked(prepareTiptapMarkdownWrite).mockResolvedValue({
      schema_version: "dmb_tiptap_markdown_write_prepare_v1",
      document_id: BUILD_DOC_ID,
      title: "Build Source",
      target_relpath: "out/workspace/worldbuilding/build.md",
      target_display_path: "out/workspace/worldbuilding/build.md",
      registry_revision: 1,
      file_exists: false,
      writer_ok: true,
      writer_phase: "prepare",
      writer_confirm_token: "confirm-token",
      writer_diff: "+# Build Source\n",
      warnings: [],
      diagnostics: [],
    });
    vi.mocked(commitTiptapMarkdownWrite).mockResolvedValue({
      schema_version: "dmb_tiptap_markdown_write_commit_v1",
      document_id: BUILD_DOC_ID,
      title: "Build Source",
      target_relpath: "out/workspace/worldbuilding/build.md",
      target_display_path: "out/workspace/worldbuilding/build.md",
      registry_revision: 2,
      committed_revision: 2,
      committed_record: fixtureWorkspaceDocumentRecord({
        document_id: BUILD_DOC_ID,
        kind: "worldbuilding_source",
        revision: 2,
        content_status: "committed",
      }),
      normalized_content_sha256: "sha-committed",
      writer_ok: true,
      bytes_written: 42,
      file_fingerprint: "fp-committed",
      diagnostics: [],
    });
  });

  it("rejects wrong document kind without exposing record or writing local storage", async () => {
    vi.mocked(getWorkspaceDocumentSnapshot).mockResolvedValue(buildSnapshot({
      record: fixtureWorkspaceDocumentRecord({
        document_id: BUILD_DOC_ID,
        kind: "plan",
        target_session: 4,
      }),
      loaded_revision: 2,
    }));

    const { result } = renderHook(() => useWorkspaceDocumentAuthoring({
      documentId: BUILD_DOC_ID,
      surface: "build",
      kind: "worldbuilding_source",
    }));

    await waitFor(() => {
      expect(result.current.phase).toBe("load_error");
    });
    expect(result.current.record).toBeNull();
    expect(result.current.snapshot).toBeNull();
    expect(window.localStorage.getItem(workspaceDocumentStorageKey(BUILD_DOC_ID))).toBeNull();
  });

  it("enters conflict when verification snapshot is N+1 while receipt is N", async () => {
    vi.mocked(getWorkspaceDocumentSnapshot)
      .mockResolvedValueOnce(buildSnapshot())
      .mockResolvedValueOnce(buildSnapshot({
        loaded_revision: 3,
        content_sha256: "sha-remote",
        record: fixtureWorkspaceDocumentRecord({
          document_id: BUILD_DOC_ID,
          kind: "worldbuilding_source",
          revision: 3,
          content_status: "committed",
        }),
      }));

    const editor = createEditor("Build Source");
    const { result } = renderHook(() => useWorkspaceDocumentAuthoring({
      documentId: BUILD_DOC_ID,
      surface: "build",
      kind: "worldbuilding_source",
    }));

    await waitFor(() => {
      expect(result.current.phase).toBe("ready_clean");
    });

    act(() => {
      result.current.setEditor(editor);
    });
    act(() => {
      result.current.markDirty();
    });

    await act(async () => {
      await result.current.saveMarkdown();
    });

    await waitFor(() => {
      expect(result.current.phase).toBe("conflict");
    });
    expect(result.current.saveDisabled).toBe(true);
    expect(result.current.snapshot?.loaded_revision).toBe(2);
  });

  it("preserves dirty when user edits during exact verification match", async () => {
    let releaseVerification: ((snapshot: WorkspaceDocumentSnapshot) => void) | undefined;
    vi.mocked(getWorkspaceDocumentSnapshot)
      .mockResolvedValueOnce(buildSnapshot())
      .mockImplementationOnce(() => new Promise((resolve) => {
        releaseVerification = resolve;
      }));

    const editor = createEditor("Build Source");
    const { result } = renderHook(() => useWorkspaceDocumentAuthoring({
      documentId: BUILD_DOC_ID,
      surface: "build",
      kind: "worldbuilding_source",
    }));

    await waitFor(() => {
      expect(result.current.phase).toBe("ready_clean");
    });

    act(() => {
      result.current.setEditor(editor);
    });
    act(() => {
      result.current.markDirty();
    });

    let savePromise: Promise<void> | undefined;
    act(() => {
      savePromise = result.current.saveMarkdown();
    });

    await waitFor(() => {
      expect(result.current.phase).toBe("committed_verification_pending");
    });

    act(() => {
      result.current.handleEditorUpdate(editor.getJSON(), editor, { programmatic: false });
    });

    await act(async () => {
      releaseVerification?.(buildSnapshot({
        loaded_revision: 2,
        content_sha256: "sha-committed",
        file_fingerprint: "fp-committed",
        record: fixtureWorkspaceDocumentRecord({
          document_id: BUILD_DOC_ID,
          kind: "worldbuilding_source",
          revision: 2,
          content_status: "committed",
        }),
      }));
      await savePromise;
    });

    await waitFor(() => {
      expect(result.current.phase).toBe("ready_dirty");
    });
    expect(result.current.dirty).toBe(true);
  });

  it("persists first user editor update and ignores programmatic hydration", async () => {
    const editor = createEditor("Build Source");
    const { result } = renderHook(() => useWorkspaceDocumentAuthoring({
      documentId: BUILD_DOC_ID,
      surface: "build",
      kind: "worldbuilding_source",
    }));

    await waitFor(() => {
      expect(result.current.phase).toBe("ready_clean");
    });

    act(() => {
      result.current.setEditor(editor);
    });

    act(() => {
      result.current.handleEditorUpdate(editor.getJSON(), editor, { programmatic: true });
    });
    expect(result.current.dirty).toBe(false);

    act(() => {
      editor.editTo("Build Source edited");
      result.current.handleEditorUpdate(editor.getJSON(), editor, { programmatic: false });
    });

    await waitFor(() => {
      expect(result.current.dirty).toBe(true);
    });
    const stored = window.localStorage.getItem(workspaceDocumentStorageKey(BUILD_DOC_ID));
    expect(stored).toContain("Build Source edited");
  });
});
