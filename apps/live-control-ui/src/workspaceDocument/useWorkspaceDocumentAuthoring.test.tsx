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
    vi.mocked(getWorkspaceDocumentSnapshot).mockReset();
    vi.mocked(prepareTiptapMarkdownWrite).mockReset();
    vi.mocked(commitTiptapMarkdownWrite).mockReset();
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

  function commitReceiptForRevision(revision: number, contentSha: string, fingerprint: string) {
    return {
      schema_version: "dmb_tiptap_markdown_write_commit_v1" as const,
      document_id: BUILD_DOC_ID,
      title: "Build Source",
      target_relpath: "out/workspace/worldbuilding/build.md",
      target_display_path: "out/workspace/worldbuilding/build.md",
      registry_revision: revision,
      committed_revision: revision,
      committed_record: fixtureWorkspaceDocumentRecord({
        document_id: BUILD_DOC_ID,
        kind: "worldbuilding_source",
        revision,
        content_status: "committed",
      }),
      normalized_content_sha256: contentSha,
      writer_ok: true,
      bytes_written: 42,
      file_fingerprint: fingerprint,
      diagnostics: [],
    };
  }

  function verificationSnapshotForRevision(revision: number, contentSha: string, fingerprint: string) {
    return buildSnapshot({
      loaded_revision: revision,
      content_sha256: contentSha,
      file_fingerprint: fingerprint,
      file_exists: true,
      record: fixtureWorkspaceDocumentRecord({
        document_id: BUILD_DOC_ID,
        kind: "worldbuilding_source",
        revision,
        content_status: "committed",
      }),
    });
  }

  async function runOverlappingSaveVerificationProof(resolveOrder: "AB" | "BA") {
    type PendingVerification = {
      resolve: (snapshot: WorkspaceDocumentSnapshot) => void;
    };
    const pendingVerifications: PendingVerification[] = [];

    vi.mocked(getWorkspaceDocumentSnapshot)
      .mockResolvedValueOnce(buildSnapshot())
      .mockImplementation(() => new Promise((resolve) => {
        pendingVerifications.push({ resolve });
      }));

    vi.mocked(commitTiptapMarkdownWrite)
      .mockResolvedValueOnce(commitReceiptForRevision(2, "sha-commit-2", "fp-2"))
      .mockResolvedValueOnce(commitReceiptForRevision(3, "sha-commit-3", "fp-3"));

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

    let saveA: Promise<void> | undefined;
    act(() => {
      saveA = result.current.saveMarkdown();
    });

    await waitFor(() => {
      expect(result.current.phase).toBe("committed_verification_pending");
    });
    expect(pendingVerifications).toHaveLength(1);

    act(() => {
      editor.editTo("Build Source save B");
      result.current.handleEditorUpdate(editor.getJSON(), editor, { programmatic: false });
    });

    let saveB: Promise<void> | undefined;
    act(() => {
      saveB = result.current.saveMarkdown();
    });

    await waitFor(() => {
      expect(pendingVerifications.length).toBeGreaterThanOrEqual(2);
    });

    const resolveA = () => {
      pendingVerifications[0]?.resolve(
        verificationSnapshotForRevision(2, "sha-commit-2", "fp-2"),
      );
    };
    const resolveB = () => {
      pendingVerifications[1]?.resolve(
        verificationSnapshotForRevision(3, "sha-commit-3", "fp-3"),
      );
    };

    await act(async () => {
      if (resolveOrder === "AB") {
        resolveA();
        await saveA;
        resolveB();
        await saveB;
      } else {
        resolveB();
        await saveB;
        resolveA();
        await saveA;
      }
    });

    await waitFor(() => {
      expect(result.current.phase).not.toBe("conflict");
    });
    expect(result.current.snapshot?.loaded_revision).toBe(3);

    vi.mocked(getWorkspaceDocumentSnapshot).mockReset();
    vi.mocked(getWorkspaceDocumentSnapshot).mockResolvedValue(
      verificationSnapshotForRevision(3, "sha-commit-3", "fp-3"),
    );
    vi.mocked(commitTiptapMarkdownWrite).mockResolvedValue(
      commitReceiptForRevision(4, "sha-commit-4", "fp-4"),
    );

    vi.mocked(prepareTiptapMarkdownWrite).mockClear();
    act(() => {
      result.current.markDirty();
    });
    await act(async () => {
      await result.current.saveMarkdown();
    });

    expect(prepareTiptapMarkdownWrite).toHaveBeenCalledWith(
      expect.objectContaining({ expected_revision: 3 }),
    );
  }

  it.each(["AB", "BA"] as const)(
    "ignores stale verification when overlapping saves resolve (%s)",
    async (resolveOrder) => {
      await runOverlappingSaveVerificationProof(resolveOrder);
    },
    10000,
  );

  it("enters conflict when commit receipt omits file_fingerprint after writer_ok", async () => {
    vi.mocked(commitTiptapMarkdownWrite).mockResolvedValueOnce({
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
      file_fingerprint: null,
      diagnostics: [],
    });

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
      result.current.markDirty();
    });

    await act(async () => {
      await result.current.saveMarkdown();
    });

    await waitFor(() => {
      expect(result.current.phase).toBe("conflict");
    });
    expect(result.current.phase).not.toBe("ready_clean");
    expect(result.current.statusLabel).toMatch(/missing file_fingerprint/i);
    expect(getWorkspaceDocumentSnapshot).toHaveBeenCalledTimes(1);
  });

  it("keeps dirty unsaved state and committed revision when verification throws after post-commit edits", async () => {
    let failVerification: (() => void) | undefined;
    vi.mocked(getWorkspaceDocumentSnapshot)
      .mockResolvedValueOnce(buildSnapshot())
      .mockImplementationOnce(() => new Promise((_resolve, reject) => {
        failVerification = () => reject(new Error("verification GET failed"));
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
      editor.editTo("Edited during verification");
      result.current.handleEditorUpdate(editor.getJSON(), editor, { programmatic: false });
    });

    await act(async () => {
      failVerification?.();
      await savePromise;
    });

    await waitFor(() => {
      expect(result.current.phase).toBe("ready_dirty");
    });
    expect(result.current.dirty).toBe(true);
    expect(result.current.statusLabel).toMatch(/Unsaved local changes/);

    vi.mocked(prepareTiptapMarkdownWrite).mockClear();
    act(() => {
      result.current.markDirty();
    });
    await act(async () => {
      await result.current.saveMarkdown();
    });

    expect(prepareTiptapMarkdownWrite).toHaveBeenCalledWith(
      expect.objectContaining({ expected_revision: 2 }),
    );
  });

  it("ignores a superseded open when a later reload completes first", async () => {
    const DOC_B = "22222222-2222-4222-8222-222222222222";
    let releaseA: ((snapshot: WorkspaceDocumentSnapshot) => void) | undefined;
    let releaseB: ((snapshot: WorkspaceDocumentSnapshot) => void) | undefined;

    vi.mocked(getWorkspaceDocumentSnapshot).mockImplementation((documentId: string) => {
      if (documentId === BUILD_DOC_ID) {
        return new Promise((resolve) => {
          releaseA = resolve;
        });
      }
      return new Promise((resolve) => {
        releaseB = resolve;
      });
    });

    const { result, rerender } = renderHook(
      ({ documentId }: { documentId: string }) => useWorkspaceDocumentAuthoring({
        documentId,
        surface: "build",
        kind: "worldbuilding_source",
      }),
      { initialProps: { documentId: BUILD_DOC_ID } },
    );

    await waitFor(() => {
      expect(result.current.phase).toBe("loading");
    });

    rerender({ documentId: DOC_B });

    await waitFor(() => {
      expect(releaseB).toBeTypeOf("function");
    });

    await act(async () => {
      releaseB?.(buildSnapshot({
        record: fixtureWorkspaceDocumentRecord({
          document_id: DOC_B,
          kind: "worldbuilding_source",
          campaign_id: "eldyrwild",
          target_session: null,
          revision: 5,
          content_status: "draft",
          title: "Doc B",
        }),
        markdown: "# Doc B\n",
        content_sha256: "sha-b",
        loaded_revision: 5,
      }));
    });

    await waitFor(() => {
      expect(result.current.phase).toBe("ready_clean");
      expect(result.current.record?.document_id).toBe(DOC_B);
    });

    await act(async () => {
      releaseA?.(buildSnapshot({
        record: fixtureWorkspaceDocumentRecord({
          document_id: BUILD_DOC_ID,
          kind: "worldbuilding_source",
          campaign_id: "eldyrwild",
          target_session: null,
          revision: 9,
          content_status: "committed",
          title: "Stale Doc A",
        }),
        markdown: "# Stale A\n",
        content_sha256: "sha-stale-a",
        loaded_revision: 9,
      }));
    });

    await act(async () => {
      await Promise.resolve();
    });

    expect(result.current.record?.document_id).toBe(DOC_B);
    expect(result.current.record?.title).not.toBe("Stale Doc A");
    expect(result.current.snapshot?.loaded_revision).toBe(5);
  });
});
