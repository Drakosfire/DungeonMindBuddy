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
  buildInitialWorkspaceDocumentLocalState,
  workspaceDocumentStorageKey,
  writeWorkspaceDocumentLocalState,
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
      editor.editTo("Build Source during verify");
      result.current.handleEditorUpdate(editor.getJSON(), editor, { programmatic: false });
    });

    await act(async () => {
      releaseVerification?.(buildSnapshot({
        loaded_revision: 2,
        content_sha256: "sha-committed",
        file_fingerprint: "fp-committed",
        markdown: "Build Source\n",
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

  it("quarantines stale snapshot when commit receipt omits file_fingerprint after writer_ok", async () => {
    const committedRecord = fixtureWorkspaceDocumentRecord({
      document_id: BUILD_DOC_ID,
      kind: "worldbuilding_source",
      revision: 2,
      content_status: "committed",
    });
    vi.mocked(commitTiptapMarkdownWrite).mockResolvedValueOnce({
      schema_version: "dmb_tiptap_markdown_write_commit_v1",
      document_id: BUILD_DOC_ID,
      title: "Build Source",
      target_relpath: "out/workspace/worldbuilding/build.md",
      target_display_path: "out/workspace/worldbuilding/build.md",
      registry_revision: 2,
      committed_revision: 2,
      committed_record: committedRecord,
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
    expect(result.current.statusLabel).toMatch(/missing file_fingerprint/i);
    expect(result.current.snapshot).toBeNull();
    expect(result.current.record).toBeNull();
    expect(result.current.saveDisabled).toBe(true);
    expect(getWorkspaceDocumentSnapshot).toHaveBeenCalledTimes(1);

    const storedRaw = window.localStorage.getItem(workspaceDocumentStorageKey(BUILD_DOC_ID));
    expect(storedRaw).toBeTruthy();
    const stored = JSON.parse(storedRaw!);
    expect(stored.base_revision).toBe(2);
    expect(stored.base_content_sha256).toBe("sha-committed");

    vi.mocked(getWorkspaceDocumentSnapshot).mockResolvedValue(
      verificationSnapshotForRevision(2, "sha-committed", "fp-server-2"),
    );
    await act(async () => {
      await result.current.reloadFromSnapshot();
    });
    await waitFor(() => {
      expect(result.current.phase).toBe("ready_clean");
    });
    expect(result.current.snapshot?.loaded_revision).toBe(2);
    expect(result.current.record?.revision).toBe(2);
  });

  it("ignores verification A while Save B commit is still pending", async () => {
    type PendingVerification = { resolve: (snapshot: WorkspaceDocumentSnapshot) => void };
    const pendingVerifications: PendingVerification[] = [];
    let releaseCommitB: ((receipt: ReturnType<typeof commitReceiptForRevision>) => void) | undefined;

    vi.mocked(getWorkspaceDocumentSnapshot)
      .mockResolvedValueOnce(buildSnapshot())
      .mockImplementation(() => new Promise((resolve) => {
        pendingVerifications.push({ resolve });
      }));
    vi.mocked(commitTiptapMarkdownWrite)
      .mockResolvedValueOnce(commitReceiptForRevision(2, "sha-commit-2", "fp-2"))
      .mockImplementationOnce(() => new Promise((resolve) => {
        releaseCommitB = resolve;
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

    let saveA: Promise<void> | undefined;
    act(() => {
      saveA = result.current.saveMarkdown();
    });
    await waitFor(() => {
      expect(result.current.phase).toBe("committed_verification_pending");
    });
    expect(pendingVerifications).toHaveLength(1);

    act(() => {
      editor.editTo("Build Source save B content");
      result.current.handleEditorUpdate(editor.getJSON(), editor, { programmatic: false });
    });
    await waitFor(() => {
      expect(result.current.dirty).toBe(true);
      expect(result.current.phase).toBe("ready_dirty");
    });

    let saveB: Promise<void> | undefined;
    act(() => {
      saveB = result.current.saveMarkdown();
    });
    await waitFor(() => {
      expect(result.current.phase).toBe("committing");
    });
    expect(result.current.saveDisabled).toBe(true);

    await act(async () => {
      pendingVerifications[0]?.resolve(
        verificationSnapshotForRevision(2, "sha-commit-2", "fp-2"),
      );
      await saveA;
    });

    expect(result.current.phase).toBe("committing");
    expect(result.current.saveDisabled).toBe(true);
    expect(result.current.dirty).toBe(true);
    const storedDuringB = window.localStorage.getItem(workspaceDocumentStorageKey(BUILD_DOC_ID));
    expect(storedDuringB).toContain("Build Source save B content");

    await act(async () => {
      releaseCommitB?.(commitReceiptForRevision(3, "sha-commit-3", "fp-3"));
      await waitFor(() => {
        expect(pendingVerifications.length).toBeGreaterThanOrEqual(2);
      });
      pendingVerifications[1]?.resolve(
        verificationSnapshotForRevision(3, "sha-commit-3", "fp-3"),
      );
      await saveB;
    });

    await waitFor(() => {
      expect(result.current.phase).toBe("ready_clean");
    });
    expect(result.current.snapshot?.loaded_revision).toBe(3);
  });

  it("keeps Save B prepare failure authoritative when verification A resolves afterward", async () => {
    type PendingVerification = { resolve: (snapshot: WorkspaceDocumentSnapshot) => void };
    const pendingVerifications: PendingVerification[] = [];
    let releasePrepareB: ((error: Error) => void) | undefined;

    vi.mocked(getWorkspaceDocumentSnapshot)
      .mockResolvedValueOnce(buildSnapshot())
      .mockImplementation(() => new Promise((resolve) => {
        pendingVerifications.push({ resolve });
      }));
    vi.mocked(commitTiptapMarkdownWrite)
      .mockResolvedValueOnce(commitReceiptForRevision(2, "sha-commit-2", "fp-2"));
    vi.mocked(prepareTiptapMarkdownWrite)
      .mockResolvedValueOnce({
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
      })
      .mockImplementationOnce(() => new Promise((_resolve, reject) => {
        releasePrepareB = reject;
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

    let saveA: Promise<void> | undefined;
    act(() => {
      saveA = result.current.saveMarkdown();
    });
    await waitFor(() => {
      expect(result.current.phase).toBe("committed_verification_pending");
    });

    act(() => {
      editor.editTo("Build Source after A");
      result.current.handleEditorUpdate(editor.getJSON(), editor, { programmatic: false });
    });

    let saveB: Promise<void> | undefined;
    act(() => {
      saveB = result.current.saveMarkdown();
    });
    await waitFor(() => {
      expect(result.current.phase).toBe("preparing");
    });

    await act(async () => {
      releasePrepareB?.(new Error("prepare B failed"));
      await saveB;
    });
    await waitFor(() => {
      expect(result.current.phase).toBe("save_error");
    });
    expect(result.current.error).toMatch(/prepare B failed/);

    await act(async () => {
      pendingVerifications[0]?.resolve(
        verificationSnapshotForRevision(2, "sha-commit-2", "fp-2"),
      );
      await saveA;
    });

    expect(result.current.phase).toBe("save_error");
    expect(result.current.error).toMatch(/prepare B failed/);
    expect(result.current.phase).not.toBe("ready_clean");

    vi.mocked(prepareTiptapMarkdownWrite).mockClear();
    vi.mocked(prepareTiptapMarkdownWrite).mockResolvedValue({
      schema_version: "dmb_tiptap_markdown_write_prepare_v1",
      document_id: BUILD_DOC_ID,
      title: "Build Source",
      target_relpath: "out/workspace/worldbuilding/build.md",
      target_display_path: "out/workspace/worldbuilding/build.md",
      registry_revision: 2,
      file_exists: true,
      writer_ok: true,
      writer_phase: "prepare",
      writer_confirm_token: "confirm-token-retry",
      writer_diff: "+retry\n",
      warnings: [],
      diagnostics: [],
    });
    vi.mocked(getWorkspaceDocumentSnapshot).mockResolvedValue(
      verificationSnapshotForRevision(2, "sha-commit-2", "fp-2"),
    );
    vi.mocked(commitTiptapMarkdownWrite).mockResolvedValue(
      commitReceiptForRevision(3, "sha-commit-3", "fp-3"),
    );

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

  it("keeps Save B commit failure authoritative when verification A resolves afterward", async () => {
    type PendingVerification = { resolve: (snapshot: WorkspaceDocumentSnapshot) => void };
    const pendingVerifications: PendingVerification[] = [];
    let releaseCommitB: ((error: Error) => void) | undefined;

    vi.mocked(getWorkspaceDocumentSnapshot)
      .mockResolvedValueOnce(buildSnapshot())
      .mockImplementation(() => new Promise((resolve) => {
        pendingVerifications.push({ resolve });
      }));
    vi.mocked(commitTiptapMarkdownWrite)
      .mockResolvedValueOnce(commitReceiptForRevision(2, "sha-commit-2", "fp-2"))
      .mockImplementationOnce(() => new Promise((_resolve, reject) => {
        releaseCommitB = reject;
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

    let saveA: Promise<void> | undefined;
    act(() => {
      saveA = result.current.saveMarkdown();
    });
    await waitFor(() => {
      expect(result.current.phase).toBe("committed_verification_pending");
    });

    act(() => {
      editor.editTo("Build Source after A for commit fail");
      result.current.handleEditorUpdate(editor.getJSON(), editor, { programmatic: false });
    });

    let saveB: Promise<void> | undefined;
    act(() => {
      saveB = result.current.saveMarkdown();
    });
    await waitFor(() => {
      expect(result.current.phase).toBe("committing");
    });
    expect(result.current.saveDisabled).toBe(true);

    await act(async () => {
      releaseCommitB?.(new Error("commit B failed"));
      await saveB;
    });
    await waitFor(() => {
      expect(result.current.phase).toBe("save_error");
    });
    expect(result.current.error).toMatch(/commit B failed/);

    await act(async () => {
      pendingVerifications[0]?.resolve(
        verificationSnapshotForRevision(2, "sha-commit-2", "fp-2"),
      );
      await saveA;
    });

    expect(result.current.phase).toBe("save_error");
    expect(result.current.error).toMatch(/commit B failed/);
    // B finished with save_error; save may be enabled again for retry, but A must not
    // have cleared B's error into ready_clean / accidentally opened a third save path.
    expect(result.current.phase).not.toBe("ready_clean");
    expect(result.current.phase).not.toBe("committed_verification_pending");
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

  it("preserves an edit made while prepare is pending through successful verification as ready_dirty", async () => {
    let releasePrepare: ((value: Awaited<ReturnType<typeof prepareTiptapMarkdownWrite>>) => void) | undefined;
    vi.mocked(prepareTiptapMarkdownWrite).mockImplementationOnce(() => new Promise((resolve) => {
      releasePrepare = resolve;
    }));
    vi.mocked(getWorkspaceDocumentSnapshot)
      .mockResolvedValueOnce(buildSnapshot())
      .mockResolvedValueOnce(verificationSnapshotForRevision(2, "sha-committed", "fp-committed"));

    const editor = createEditor("Build Source");
    const documentKeyAtReady = { current: "" };
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
    documentKeyAtReady.current = result.current.documentKey;

    let savePromise: Promise<void> | undefined;
    act(() => {
      savePromise = result.current.saveMarkdown();
    });
    await waitFor(() => {
      expect(result.current.phase).toBe("preparing");
    });

    act(() => {
      editor.editTo("Build Source plus late prepare edit");
      result.current.handleEditorUpdate(editor.getJSON(), editor, { programmatic: false });
    });
    await waitFor(() => {
      expect(result.current.dirty).toBe(true);
    });

    await act(async () => {
      releasePrepare?.({
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
      await savePromise;
    });

    await waitFor(() => {
      expect(result.current.phase).toBe("ready_dirty");
    });
    expect(result.current.dirty).toBe(true);
    expect(result.current.documentKey).toBe(documentKeyAtReady.current);
    const stored = JSON.parse(window.localStorage.getItem(workspaceDocumentStorageKey(BUILD_DOC_ID))!);
    expect(stored.base_revision).toBe(2);
    expect(stored.dirty).toBe(true);
    expect(stored.exported_markdown).toContain("late prepare edit");
    expect(result.current.editorContent).toEqual(editor.getJSON());
  });

  it("preserves an edit made while commit is pending through successful verification as ready_dirty", async () => {
    let releaseCommit: ((value: ReturnType<typeof commitReceiptForRevision>) => void) | undefined;
    vi.mocked(commitTiptapMarkdownWrite).mockImplementationOnce(() => new Promise((resolve) => {
      releaseCommit = resolve;
    }));
    vi.mocked(getWorkspaceDocumentSnapshot)
      .mockResolvedValueOnce(buildSnapshot())
      .mockResolvedValueOnce(verificationSnapshotForRevision(2, "sha-committed", "fp-committed"));

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
    const documentKeyBefore = result.current.documentKey;

    let savePromise: Promise<void> | undefined;
    act(() => {
      savePromise = result.current.saveMarkdown();
    });
    await waitFor(() => {
      expect(result.current.phase).toBe("committing");
    });

    act(() => {
      editor.editTo("Build Source plus late commit edit");
      result.current.handleEditorUpdate(editor.getJSON(), editor, { programmatic: false });
    });

    await act(async () => {
      releaseCommit?.(commitReceiptForRevision(2, "sha-committed", "fp-committed"));
      await savePromise;
    });

    await waitFor(() => {
      expect(result.current.phase).toBe("ready_dirty");
    });
    expect(result.current.dirty).toBe(true);
    expect(result.current.documentKey).toBe(documentKeyBefore);
    const stored = JSON.parse(window.localStorage.getItem(workspaceDocumentStorageKey(BUILD_DOC_ID))!);
    expect(stored.base_revision).toBe(2);
    expect(stored.exported_markdown).toContain("late commit edit");
    expect(stored.dirty).toBe(true);
  });

  it("keeps a late commit-pending edit dirty when the commit fails", async () => {
    let releaseCommit: ((error: Error) => void) | undefined;
    vi.mocked(commitTiptapMarkdownWrite).mockImplementationOnce(() => new Promise((_resolve, reject) => {
      releaseCommit = reject;
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
      expect(result.current.phase).toBe("committing");
    });

    act(() => {
      editor.editTo("Survives commit failure");
      result.current.handleEditorUpdate(editor.getJSON(), editor, { programmatic: false });
    });

    await act(async () => {
      releaseCommit?.(new Error("commit failed after late edit"));
      await savePromise;
    });

    await waitFor(() => {
      expect(result.current.phase).toBe("save_error");
    });
    expect(result.current.dirty).toBe(true);
    expect(result.current.error).toMatch(/commit failed after late edit/);
    const stored = window.localStorage.getItem(workspaceDocumentStorageKey(BUILD_DOC_ID));
    expect(stored).toContain("Survives commit failure");
  });

  it("ignores document A commit after switching to document B", async () => {
    const DOC_B = "22222222-2222-4222-8222-222222222222";
    let releaseCommitA: ((value: ReturnType<typeof commitReceiptForRevision>) => void) | undefined;

    vi.mocked(getWorkspaceDocumentSnapshot).mockImplementation(async (documentId: string) => {
      if (documentId === BUILD_DOC_ID) {
        return buildSnapshot();
      }
      return buildSnapshot({
        record: fixtureWorkspaceDocumentRecord({
          document_id: DOC_B,
          kind: "worldbuilding_source",
          campaign_id: "eldyrwild",
          target_session: null,
          revision: 5,
          content_status: "draft",
          title: "Doc B",
        }),
        markdown: "# Doc B body\n",
        content_sha256: "sha-b",
        loaded_revision: 5,
      });
    });
    vi.mocked(commitTiptapMarkdownWrite).mockImplementationOnce(() => new Promise((resolve) => {
      releaseCommitA = resolve;
    }));

    const editor = createEditor("Build Source");
    const { result, rerender } = renderHook(
      ({ documentId }: { documentId: string }) => useWorkspaceDocumentAuthoring({
        documentId,
        surface: "build",
        kind: "worldbuilding_source",
      }),
      { initialProps: { documentId: BUILD_DOC_ID } },
    );

    await waitFor(() => {
      expect(result.current.phase).toBe("ready_clean");
    });
    act(() => {
      result.current.setEditor(editor);
      result.current.markDirty();
    });

    let saveA: Promise<void> | undefined;
    act(() => {
      saveA = result.current.saveMarkdown();
    });
    await waitFor(() => {
      expect(result.current.phase).toBe("committing");
    });

    rerender({ documentId: DOC_B });
    await waitFor(() => {
      expect(result.current.phase).toBe("ready_clean");
      expect(result.current.record?.document_id).toBe(DOC_B);
    });
    const bStoredBefore = window.localStorage.getItem(workspaceDocumentStorageKey(DOC_B));

    await act(async () => {
      releaseCommitA?.(commitReceiptForRevision(2, "sha-a", "fp-a"));
      await saveA;
    });

    expect(result.current.record?.document_id).toBe(DOC_B);
    expect(result.current.snapshot?.loaded_revision).toBe(5);
    expect(result.current.lastCommitReceipt).toBeNull();
    expect(window.localStorage.getItem(workspaceDocumentStorageKey(DOC_B))).toBe(bStoredBefore);

    const editorB = createEditor("Doc B body");
    act(() => {
      result.current.setEditor(editorB);
      result.current.markDirty();
    });
    vi.mocked(prepareTiptapMarkdownWrite).mockClear();
    vi.mocked(commitTiptapMarkdownWrite).mockResolvedValue({
      schema_version: "dmb_tiptap_markdown_write_commit_v1",
      document_id: DOC_B,
      title: "Doc B",
      target_relpath: "out/workspace/worldbuilding/b.md",
      target_display_path: "out/workspace/worldbuilding/b.md",
      registry_revision: 6,
      committed_revision: 6,
      committed_record: fixtureWorkspaceDocumentRecord({
        document_id: DOC_B,
        kind: "worldbuilding_source",
        revision: 6,
        content_status: "committed",
        title: "Doc B",
      }),
      normalized_content_sha256: "sha-b-6",
      writer_ok: true,
      bytes_written: 10,
      file_fingerprint: "fp-b-6",
      diagnostics: [],
    });
    await act(async () => {
      await result.current.saveMarkdown();
    });
    expect(prepareTiptapMarkdownWrite).toHaveBeenCalledWith(
      expect.objectContaining({ document_id: DOC_B, expected_revision: 5 }),
    );
  });

  it("does not start document A commit after switching to B while A's prepare is pending", async () => {
    const DOC_B = "33333333-3333-4333-8333-333333333333";
    let releasePrepareA: ((value: Awaited<ReturnType<typeof prepareTiptapMarkdownWrite>>) => void) | undefined;

    vi.mocked(getWorkspaceDocumentSnapshot).mockImplementation(async (documentId: string) => {
      if (documentId === BUILD_DOC_ID) {
        return buildSnapshot();
      }
      return buildSnapshot({
        record: fixtureWorkspaceDocumentRecord({
          document_id: DOC_B,
          kind: "worldbuilding_source",
          campaign_id: "eldyrwild",
          target_session: null,
          revision: 7,
          content_status: "draft",
          title: "Doc B prepare",
        }),
        markdown: "# Doc B prepare\n",
        content_sha256: "sha-b-prep",
        loaded_revision: 7,
      });
    });
    vi.mocked(prepareTiptapMarkdownWrite).mockImplementationOnce(() => new Promise((resolve) => {
      releasePrepareA = resolve;
    }));
    vi.mocked(commitTiptapMarkdownWrite).mockClear();

    const editor = createEditor("Build Source");
    const { result, rerender } = renderHook(
      ({ documentId }: { documentId: string }) => useWorkspaceDocumentAuthoring({
        documentId,
        surface: "build",
        kind: "worldbuilding_source",
      }),
      { initialProps: { documentId: BUILD_DOC_ID } },
    );

    await waitFor(() => {
      expect(result.current.phase).toBe("ready_clean");
    });
    act(() => {
      result.current.setEditor(editor);
      result.current.markDirty();
    });

    let saveA: Promise<void> | undefined;
    act(() => {
      saveA = result.current.saveMarkdown();
    });
    await waitFor(() => {
      expect(result.current.phase).toBe("preparing");
    });

    rerender({ documentId: DOC_B });
    await waitFor(() => {
      expect(result.current.phase).toBe("ready_clean");
      expect(result.current.record?.document_id).toBe(DOC_B);
    });

    await act(async () => {
      releasePrepareA?.({
        schema_version: "dmb_tiptap_markdown_write_prepare_v1",
        document_id: BUILD_DOC_ID,
        title: "Build Source",
        target_relpath: "out/workspace/worldbuilding/build.md",
        target_display_path: "out/workspace/worldbuilding/build.md",
        registry_revision: 1,
        file_exists: false,
        writer_ok: true,
        writer_phase: "prepare",
        writer_confirm_token: "stale-a-token",
        writer_diff: "+stale\n",
        warnings: [],
        diagnostics: [],
      });
      await saveA;
    });

    expect(commitTiptapMarkdownWrite).not.toHaveBeenCalled();
    expect(result.current.record?.document_id).toBe(DOC_B);
    expect(result.current.snapshot?.loaded_revision).toBe(7);
    expect(result.current.lastCommitReceipt).toBeNull();
    expect(result.current.phase).toBe("ready_clean");
  });

  it("reopens clean when stale dirty local Markdown is identical to snapshot", async () => {
    const starter = {
      type: "doc",
      content: [{ type: "heading", attrs: { level: 1 }, content: [{ type: "text", text: "Build Source" }] }],
    };
    const stored = buildInitialWorkspaceDocumentLocalState({
      documentId: BUILD_DOC_ID,
      title: "Build Source",
      campaignId: "eldyrwild",
      kind: "worldbuilding_source",
      targetSession: null,
      surface: "build",
      baseRevision: 2,
      baseContentSha256: "sha-committed",
      starterContent: starter,
    });
    stored.dirty = true;
    writeWorkspaceDocumentLocalState(window.localStorage, stored);

    vi.mocked(getWorkspaceDocumentSnapshot).mockResolvedValue(buildSnapshot({
      markdown: stored.exported_markdown,
      content_sha256: "sha-committed",
      loaded_revision: 2,
      file_exists: true,
      file_fingerprint: "fp-committed",
      record: fixtureWorkspaceDocumentRecord({
        document_id: BUILD_DOC_ID,
        kind: "worldbuilding_source",
        campaign_id: "eldyrwild",
        target_session: null,
        revision: 2,
        content_status: "committed",
      }),
    }));

    const { result } = renderHook(() => useWorkspaceDocumentAuthoring({
      documentId: BUILD_DOC_ID,
      surface: "build",
      kind: "worldbuilding_source",
    }));

    await waitFor(() => {
      expect(result.current.phase).toBe("ready_clean");
    });
    expect(result.current.dirty).toBe(false);
    expect(result.current.statusLabel).not.toMatch(/Unsaved local changes/i);
    expect(result.current.snapshot?.loaded_revision).toBe(2);

    const rewritten = JSON.parse(
      window.localStorage.getItem(workspaceDocumentStorageKey(BUILD_DOC_ID))!,
    );
    expect(rewritten.dirty).toBe(false);
  });

  it("does not re-dirty on editor update when Markdown still matches the snapshot", async () => {
    vi.mocked(getWorkspaceDocumentSnapshot).mockResolvedValue(buildSnapshot({
      markdown: "Build Source\n",
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
      result.current.handleEditorUpdate(editor.getJSON(), editor, { programmatic: false });
    });

    expect(result.current.dirty).toBe(false);
    expect(result.current.phase).toBe("ready_clean");
    expect(result.current.statusLabel).not.toMatch(/Unsaved local changes/i);
    const stored = JSON.parse(
      window.localStorage.getItem(workspaceDocumentStorageKey(BUILD_DOC_ID))!,
    );
    expect(stored.dirty).toBe(false);
  });
});
