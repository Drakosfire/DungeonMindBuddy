import type { ReactNode } from "react";
import { act, renderHook, waitFor } from "@testing-library/react";
import type { Editor } from "@tiptap/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import * as liveApi from "../api/liveApi";
import {
  buildInitialWorkspaceDocumentLocalState,
  writeWorkspaceDocumentLocalState,
} from "../tiptap/state/tiptapLocalState";
import { DOCUMENT_METADATA_UPDATE_COMMAND_ID, DOCUMENT_SAVE_COMMAND_ID } from "./markdownCanvasTypes";
import {
  MarkdownCanvasSessionProvider,
  useMarkdownCanvasSession,
} from "./MarkdownCanvasSession";

vi.mock("../api/liveApi", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../api/liveApi")>();
  return {
    ...actual,
    getWorkspaceDocumentSnapshot: vi.fn(),
    prepareTiptapMarkdownWrite: vi.fn(),
    commitTiptapMarkdownWrite: vi.fn(),
    updateWorkspaceDocumentMetadata: vi.fn(),
  };
});

const DOC_ID = "22222222-2222-4222-8222-222222222222";
const PLUGIN_WORK_ID = "plugin.work";

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

function sessionWrapper(saveConflictsWith: readonly string[] = [PLUGIN_WORK_ID]) {
  return function Wrapper({ children }: { children: ReactNode }) {
    return (
      <MarkdownCanvasSessionProvider
        documentId={DOC_ID}
        surface="build"
        kind="worldbuilding_source"
        saveConflictsWith={saveConflictsWith}
      >
        {children}
      </MarkdownCanvasSessionProvider>
    );
  };
}

describe("MarkdownCanvasSession", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
    writeWorkspaceDocumentLocalState(window.localStorage, {
      ...buildInitialWorkspaceDocumentLocalState({
        documentId: DOC_ID,
        title: "Session Doc",
        campaignId: "eldyrwild",
        kind: "worldbuilding_source",
        targetSession: null,
        surface: "build",
        baseRevision: 1,
        baseContentSha256: "sha-1",
        starterContent: { type: "doc", content: [] },
      }),
      dirty: false,
    });
    vi.mocked(liveApi.getWorkspaceDocumentSnapshot).mockResolvedValue({
      schema_version: "dmb_workspace_document_snapshot_v1",
      record: {
        schema_version: "dmb_workspace_document_record_v1",
        document_id: DOC_ID,
        title: "Session Doc",
        campaign_id: "eldyrwild",
        target_session: null,
        kind: "worldbuilding_source",
        target_relpath: `out/workspace/worldbuilding/${DOC_ID}.md`,
        status: "active",
        content_status: "committed",
        revision: 1,
        created_at: "2026-07-22T00:00:00Z",
        updated_at: "2026-07-22T00:00:00Z",
        source_domain: "worldbuilding",
        document_class: "lore",
        authority_state: "draft",
        visibility_state: "internal",
      },
      markdown: "# Session Doc\n",
      content_sha256: "sha-1",
      file_fingerprint: "fp",
      file_exists: true,
      loaded_revision: 1,
    });
    vi.mocked(liveApi.prepareTiptapMarkdownWrite).mockResolvedValue({
      schema_version: "dmb_tiptap_markdown_write_prepare_v1",
      document_id: DOC_ID,
      title: "Session Doc",
      target_relpath: `out/workspace/worldbuilding/${DOC_ID}.md`,
      target_display_path: `out/workspace/worldbuilding/${DOC_ID}.md`,
      registry_revision: 1,
      file_exists: true,
      writer_ok: true,
      writer_phase: "prepare",
      writer_confirm_token: "confirm-token",
      writer_diff: "+edited\n",
      warnings: [],
      diagnostics: [],
    });
    vi.mocked(liveApi.commitTiptapMarkdownWrite).mockResolvedValue({
      schema_version: "dmb_tiptap_markdown_write_commit_v1",
      document_id: DOC_ID,
      title: "Session Doc",
      target_relpath: `out/workspace/worldbuilding/${DOC_ID}.md`,
      target_display_path: `out/workspace/worldbuilding/${DOC_ID}.md`,
      registry_revision: 2,
      committed_revision: 2,
      committed_record: {
        schema_version: "dmb_workspace_document_record_v1",
        document_id: DOC_ID,
        title: "Session Doc",
        campaign_id: "eldyrwild",
        target_session: null,
        kind: "worldbuilding_source",
        target_relpath: `out/workspace/worldbuilding/${DOC_ID}.md`,
        status: "active",
        content_status: "committed",
        revision: 2,
        created_at: "2026-07-22T00:00:00Z",
        updated_at: "2026-07-22T00:00:00Z",
        source_domain: "worldbuilding",
        document_class: "lore",
        authority_state: "draft",
        visibility_state: "internal",
      },
      normalized_content_sha256: "sha-2",
      writer_ok: true,
      bytes_written: 12,
      file_fingerprint: "fp-2",
      diagnostics: [],
    });
  });

  it("exposes one document authority and committed_clean envelope", async () => {
    const { result } = renderHook(() => useMarkdownCanvasSession(), {
      wrapper: sessionWrapper(),
    });
    await waitFor(() => expect(result.current.phase).toMatch(/ready|committed/));
    const envelope = result.current.getAdmittedDocument("committed_clean");
    expect(envelope).toEqual({
      documentId: DOC_ID,
      revision: 1,
      contentSha256: "sha-1",
      contentStatus: "committed",
      documentKind: "worldbuilding_source",
      surfaceId: "build",
    });
  });

  it("blocks plugin work while session.saveMarkdown holds document.save", async () => {
    let releasePrepare: ((value: Awaited<ReturnType<typeof liveApi.prepareTiptapMarkdownWrite>>) => void) | undefined;
    vi.mocked(liveApi.prepareTiptapMarkdownWrite).mockImplementation(
      () => new Promise((resolve) => {
        releasePrepare = resolve;
      }),
    );

    const editor = createEditor("Session Doc");
    const { result } = renderHook(() => useMarkdownCanvasSession(), {
      wrapper: sessionWrapper(),
    });
    await waitFor(() => expect(result.current.phase).toBe("ready_clean"));

    act(() => {
      result.current.setEditor(editor);
      result.current.markDirty();
    });

    let savePromise: Promise<void> | undefined;
    act(() => {
      savePromise = result.current.saveMarkdown();
    });

    await waitFor(() => {
      expect(result.current.activeCommand?.id).toBe(DOCUMENT_SAVE_COMMAND_ID);
    });
    await waitFor(() => {
      expect(liveApi.prepareTiptapMarkdownWrite).toHaveBeenCalledTimes(1);
    });

    const executeSpy = vi.fn(async () => "should-not-run");
    let pluginResult!: Awaited<ReturnType<typeof result.current.runDocumentCommand>>;
    await act(async () => {
      pluginResult = await result.current.runDocumentCommand(
        {
          id: PLUGIN_WORK_ID,
          conflictsWith: [DOCUMENT_SAVE_COMMAND_ID],
          admission: "committed_clean",
        },
        executeSpy,
      );
    });

    expect(pluginResult.ok).toBe(false);
    if (!pluginResult.ok) {
      expect(pluginResult.code).toBe("conflict");
    }
    expect(executeSpy).not.toHaveBeenCalled();

    await act(async () => {
      releasePrepare?.({
        schema_version: "dmb_tiptap_markdown_write_prepare_v1",
        document_id: DOC_ID,
        title: "Session Doc",
        target_relpath: `out/workspace/worldbuilding/${DOC_ID}.md`,
        target_display_path: `out/workspace/worldbuilding/${DOC_ID}.md`,
        registry_revision: 1,
        file_exists: true,
        writer_ok: true,
        writer_phase: "prepare",
        writer_confirm_token: "confirm-token",
        writer_diff: "+edited\n",
        warnings: [],
        diagnostics: [],
      });
      await savePromise;
    });
  });

  it("disables and rejects save while a conflicting plugin command is pending", async () => {
    let releasePlugin: ((value: string) => void) | undefined;
    const editor = createEditor("Session Doc");
    const { result } = renderHook(() => useMarkdownCanvasSession(), {
      wrapper: sessionWrapper([PLUGIN_WORK_ID]),
    });
    await waitFor(() => expect(result.current.phase).toBe("ready_clean"));

    act(() => {
      result.current.setEditor(editor);
      result.current.markDirty();
    });

    let pluginPromise!: Promise<Awaited<ReturnType<typeof result.current.runDocumentCommand>>>;
    act(() => {
      pluginPromise = result.current.runDocumentCommand(
        {
          id: PLUGIN_WORK_ID,
          conflictsWith: [DOCUMENT_SAVE_COMMAND_ID],
          admission: "none",
        },
        () => new Promise((resolve) => {
          releasePlugin = resolve;
        }),
      );
    });

    await waitFor(() => {
      expect(result.current.activeCommand?.id).toBe(PLUGIN_WORK_ID);
    });
    expect(result.current.saveDisabled).toBe(true);

    const prepareCallsBefore = vi.mocked(liveApi.prepareTiptapMarkdownWrite).mock.calls.length;
    const commitCallsBefore = vi.mocked(liveApi.commitTiptapMarkdownWrite).mock.calls.length;

    await act(async () => {
      await result.current.saveMarkdown();
    });

    expect(result.current.activeCommand?.id).toBe(PLUGIN_WORK_ID);
    expect(vi.mocked(liveApi.prepareTiptapMarkdownWrite).mock.calls.length).toBe(prepareCallsBefore);
    expect(vi.mocked(liveApi.commitTiptapMarkdownWrite).mock.calls.length).toBe(commitCallsBefore);

    await act(async () => {
      releasePlugin?.("done");
      const settled = await pluginPromise;
      expect(settled.ok).toBe(true);
    });
  });

  it("invalidates a pending session command on unmount without adopting the late result", async () => {
    let releasePlugin: ((value: string) => void) | undefined;
    const adopted = vi.fn();
    const { result, unmount } = renderHook(() => useMarkdownCanvasSession(), {
      wrapper: sessionWrapper(),
    });
    await waitFor(() => expect(result.current.phase).toMatch(/ready|committed/));

    let pluginPromise!: Promise<Awaited<ReturnType<typeof result.current.runDocumentCommand>>>;
    act(() => {
      pluginPromise = result.current.runDocumentCommand(
        {
          id: PLUGIN_WORK_ID,
          conflictsWith: [DOCUMENT_SAVE_COMMAND_ID],
          admission: "none",
        },
        async () => {
          const value = await new Promise<string>((resolve) => {
            releasePlugin = resolve;
          });
          adopted(value);
          return value;
        },
      );
    });

    await waitFor(() => {
      expect(result.current.activeCommand?.id).toBe(PLUGIN_WORK_ID);
    });

    unmount();

    let settled!: Awaited<typeof pluginPromise>;
    await act(async () => {
      releasePlugin?.("too-late");
      settled = await pluginPromise;
    });

    expect(settled.ok).toBe(false);
    if (!settled.ok) {
      expect(["invalidated", "aborted"]).toContain(settled.code);
    }
  });

  it("updateDocumentMetadata PATCHes Canvas revision and rebases without remounting", async () => {
    const editor = createEditor("Session Doc");
    vi.mocked(liveApi.updateWorkspaceDocumentMetadata).mockResolvedValue({
      schema_version: "dmb_workspace_document_record_v1",
      document_id: DOC_ID,
      title: "Renamed Session Doc",
      campaign_id: "eldyrwild",
      target_session: null,
      kind: "worldbuilding_source",
      target_relpath: `out/workspace/worldbuilding/${DOC_ID}.md`,
      status: "active",
      content_status: "committed",
      revision: 2,
      created_at: "2026-07-22T00:00:00Z",
      updated_at: "2026-07-22T00:00:00Z",
      source_domain: "worldbuilding",
      document_class: "lore",
      authority_state: "draft",
      visibility_state: "internal",
    });

    const { result } = renderHook(() => useMarkdownCanvasSession(), {
      wrapper: sessionWrapper([DOCUMENT_METADATA_UPDATE_COMMAND_ID]),
    });
    await waitFor(() => expect(result.current.phase).toMatch(/ready|committed/));
    act(() => {
      result.current.setEditor(editor);
    });
    act(() => {
      editor.editTo("Unsaved sentence before rename.");
      result.current.handleEditorUpdate(editor.getJSON(), editor, { programmatic: false });
    });
    expect(result.current.dirty).toBe(true);
    const keyBefore = result.current.documentKey;

    let renameResult!: Awaited<ReturnType<typeof result.current.updateDocumentMetadata>>;
    await act(async () => {
      renameResult = await result.current.updateDocumentMetadata({
        title: "Renamed Session Doc",
      });
    });

    expect(renameResult.ok).toBe(true);
    expect(liveApi.updateWorkspaceDocumentMetadata).toHaveBeenCalledWith(
      DOC_ID,
      expect.objectContaining({
        title: "Renamed Session Doc",
        expected_revision: 1,
      }),
    );
    expect(result.current.record?.title).toBe("Renamed Session Doc");
    expect(result.current.snapshot?.loaded_revision).toBe(2);
    expect(result.current.dirty).toBe(true);
    expect(result.current.documentKey).toBe(keyBefore);
    expect(result.current.snapshot?.content_sha256).toBe("sha-1");
  });

  it("rename after Save uses Canvas revision not a stale preflight revision", async () => {
    const editor = createEditor("Session Doc");
    const { result } = renderHook(() => useMarkdownCanvasSession(), {
      wrapper: sessionWrapper([DOCUMENT_METADATA_UPDATE_COMMAND_ID]),
    });
    await waitFor(() => expect(result.current.phase).toMatch(/ready|committed/));
    act(() => {
      result.current.setEditor(editor);
    });
    act(() => {
      editor.editTo("Saved body");
      result.current.handleEditorUpdate(editor.getJSON(), editor, { programmatic: false });
    });

    vi.mocked(liveApi.getWorkspaceDocumentSnapshot).mockResolvedValue({
      schema_version: "dmb_workspace_document_snapshot_v1",
      record: {
        schema_version: "dmb_workspace_document_record_v1",
        document_id: DOC_ID,
        title: "Session Doc",
        campaign_id: "eldyrwild",
        target_session: null,
        kind: "worldbuilding_source",
        target_relpath: `out/workspace/worldbuilding/${DOC_ID}.md`,
        status: "active",
        content_status: "committed",
        revision: 2,
        created_at: "2026-07-22T00:00:00Z",
        updated_at: "2026-07-22T00:00:00Z",
        source_domain: "worldbuilding",
        document_class: "lore",
        authority_state: "draft",
        visibility_state: "internal",
      },
      markdown: "Saved body\n",
      content_sha256: "sha-2",
      file_fingerprint: "fp-2",
      file_exists: true,
      loaded_revision: 2,
    });

    await act(async () => {
      await result.current.saveMarkdown();
    });
    await waitFor(() => expect(result.current.snapshot?.loaded_revision).toBe(2));

    vi.mocked(liveApi.updateWorkspaceDocumentMetadata).mockResolvedValue({
      schema_version: "dmb_workspace_document_record_v1",
      document_id: DOC_ID,
      title: "Post-Save Rename",
      campaign_id: "eldyrwild",
      target_session: null,
      kind: "worldbuilding_source",
      target_relpath: `out/workspace/worldbuilding/${DOC_ID}.md`,
      status: "active",
      content_status: "committed",
      revision: 3,
      created_at: "2026-07-22T00:00:00Z",
      updated_at: "2026-07-22T00:00:00Z",
      source_domain: "worldbuilding",
      document_class: "lore",
      authority_state: "draft",
      visibility_state: "internal",
    });

    await act(async () => {
      await result.current.updateDocumentMetadata({ title: "Post-Save Rename" });
    });

    expect(liveApi.updateWorkspaceDocumentMetadata).toHaveBeenCalledWith(
      DOC_ID,
      expect.objectContaining({ expected_revision: 2 }),
    );
    expect(result.current.snapshot?.loaded_revision).toBe(3);
  });

  it("blocks metadata update while document.save is active", async () => {
    let releasePrepare: ((value: Awaited<ReturnType<typeof liveApi.prepareTiptapMarkdownWrite>>) => void) | undefined;
    vi.mocked(liveApi.prepareTiptapMarkdownWrite).mockImplementation(
      () =>
        new Promise((resolve) => {
          releasePrepare = resolve;
        }),
    );
    const editor = createEditor("Session Doc");
    const { result } = renderHook(() => useMarkdownCanvasSession(), {
      wrapper: sessionWrapper([DOCUMENT_METADATA_UPDATE_COMMAND_ID]),
    });
    await waitFor(() => expect(result.current.phase).toMatch(/ready|committed/));
    act(() => {
      result.current.setEditor(editor);
    });
    act(() => {
      editor.editTo("dirty");
      result.current.handleEditorUpdate(editor.getJSON(), editor, { programmatic: false });
    });

    act(() => {
      void result.current.saveMarkdown();
    });
    await waitFor(() => expect(result.current.activeCommand?.id).toBe(DOCUMENT_SAVE_COMMAND_ID));

    let renameResult!: Awaited<ReturnType<typeof result.current.updateDocumentMetadata>>;
    await act(async () => {
      renameResult = await result.current.updateDocumentMetadata({ title: "Nope" });
    });
    expect(renameResult.ok).toBe(false);
    if (!renameResult.ok) expect(renameResult.code).toBe("conflict");
    expect(liveApi.updateWorkspaceDocumentMetadata).not.toHaveBeenCalled();

    await act(async () => {
      releasePrepare?.({
        schema_version: "dmb_tiptap_markdown_write_prepare_v1",
        document_id: DOC_ID,
        title: "Session Doc",
        target_relpath: `out/workspace/worldbuilding/${DOC_ID}.md`,
        target_display_path: `out/workspace/worldbuilding/${DOC_ID}.md`,
        registry_revision: 1,
        file_exists: true,
        writer_ok: true,
        writer_phase: "prepare",
        writer_confirm_token: "confirm-token",
        writer_diff: "+edited\n",
        warnings: [],
        diagnostics: [],
      });
    });
  });

  it("blocks Save while document.metadata.update is active", async () => {
    let releasePatch: ((value: Awaited<ReturnType<typeof liveApi.updateWorkspaceDocumentMetadata>>) => void) | undefined;
    vi.mocked(liveApi.updateWorkspaceDocumentMetadata).mockImplementation(
      () =>
        new Promise((resolve) => {
          releasePatch = resolve;
        }),
    );
    const editor = createEditor("Session Doc");
    const { result } = renderHook(() => useMarkdownCanvasSession(), {
      wrapper: sessionWrapper([DOCUMENT_METADATA_UPDATE_COMMAND_ID]),
    });
    await waitFor(() => expect(result.current.phase).toMatch(/ready|committed/));
    act(() => {
      result.current.setEditor(editor);
    });
    act(() => {
      editor.editTo("dirty before rename");
      result.current.handleEditorUpdate(editor.getJSON(), editor, { programmatic: false });
    });

    act(() => {
      void result.current.updateDocumentMetadata({ title: "Pending Rename" });
    });
    await waitFor(() => {
      expect(result.current.activeCommand?.id).toBe(DOCUMENT_METADATA_UPDATE_COMMAND_ID);
    });

    await act(async () => {
      await result.current.saveMarkdown();
    });
    expect(liveApi.prepareTiptapMarkdownWrite).not.toHaveBeenCalled();

    await act(async () => {
      releasePatch?.({
        schema_version: "dmb_workspace_document_record_v1",
        document_id: DOC_ID,
        title: "Pending Rename",
        campaign_id: "eldyrwild",
        target_session: null,
        kind: "worldbuilding_source",
        target_relpath: `out/workspace/worldbuilding/${DOC_ID}.md`,
        status: "active",
        content_status: "committed",
        revision: 2,
        created_at: "2026-07-22T00:00:00Z",
        updated_at: "2026-07-22T00:00:00Z",
        source_domain: "worldbuilding",
        document_class: "lore",
        authority_state: "draft",
        visibility_state: "internal",
      });
    });
    await waitFor(() => expect(result.current.record?.title).toBe("Pending Rename"));
    expect(result.current.dirty).toBe(true);
  });

  it("does not adopt a late metadata PATCH after the Canvas unmounts", async () => {
    let releasePatch: ((value: Awaited<ReturnType<typeof liveApi.updateWorkspaceDocumentMetadata>>) => void) | undefined;
    vi.mocked(liveApi.updateWorkspaceDocumentMetadata).mockImplementation(
      () =>
        new Promise((resolve) => {
          releasePatch = resolve;
        }),
    );
    const editor = createEditor("Session Doc");
    const { result, unmount } = renderHook(() => useMarkdownCanvasSession(), {
      wrapper: sessionWrapper([DOCUMENT_METADATA_UPDATE_COMMAND_ID]),
    });
    await waitFor(() => expect(result.current.phase).toMatch(/ready|committed/));
    act(() => {
      result.current.setEditor(editor);
    });

    let renamePromise!: Promise<Awaited<ReturnType<typeof result.current.updateDocumentMetadata>>>;
    act(() => {
      renamePromise = result.current.updateDocumentMetadata({ title: "Stale Rename" });
    });
    await waitFor(() => {
      expect(result.current.activeCommand?.id).toBe(DOCUMENT_METADATA_UPDATE_COMMAND_ID);
    });

    unmount();

    let settled!: Awaited<typeof renamePromise>;
    await act(async () => {
      releasePatch?.({
        schema_version: "dmb_workspace_document_record_v1",
        document_id: DOC_ID,
        title: "Stale Rename",
        campaign_id: "eldyrwild",
        target_session: null,
        kind: "worldbuilding_source",
        target_relpath: `out/workspace/worldbuilding/${DOC_ID}.md`,
        status: "active",
        content_status: "committed",
        revision: 2,
        created_at: "2026-07-22T00:00:00Z",
        updated_at: "2026-07-22T00:00:00Z",
        source_domain: "worldbuilding",
        document_class: "lore",
        authority_state: "draft",
        visibility_state: "internal",
      });
      settled = await renamePromise;
    });
    expect(settled.ok).toBe(false);
    if (!settled.ok) {
      expect(["invalidated", "aborted"]).toContain(settled.code);
    }
  });

  it("preserves local draft and title when metadata PATCH returns 409", async () => {
    vi.mocked(liveApi.updateWorkspaceDocumentMetadata).mockRejectedValue(
      new liveApi.LiveApiError("revision conflict", 409),
    );
    const editor = createEditor("Session Doc");
    const { result } = renderHook(() => useMarkdownCanvasSession(), {
      wrapper: sessionWrapper([DOCUMENT_METADATA_UPDATE_COMMAND_ID]),
    });
    await waitFor(() => expect(result.current.phase).toMatch(/ready|committed/));
    act(() => {
      result.current.setEditor(editor);
    });
    act(() => {
      editor.editTo("Keep this unsaved sentence.");
      result.current.handleEditorUpdate(editor.getJSON(), editor, { programmatic: false });
    });
    const keyBefore = result.current.documentKey;
    const bodyBefore = result.current.editorContent;

    let renameResult!: Awaited<ReturnType<typeof result.current.updateDocumentMetadata>>;
    await act(async () => {
      renameResult = await result.current.updateDocumentMetadata({ title: "Conflict Title" });
    });

    expect(renameResult.ok).toBe(false);
    if (!renameResult.ok) {
      expect(renameResult.reason).toMatch(/Source changed elsewhere/i);
    }
    expect(result.current.record?.title).toBe("Session Doc");
    expect(result.current.snapshot?.loaded_revision).toBe(1);
    expect(result.current.dirty).toBe(true);
    expect(result.current.documentKey).toBe(keyBefore);
    expect(result.current.editorContent).toEqual(bodyBefore);
  });

  it("preserves local draft when metadata PATCH fails with network error", async () => {
    vi.mocked(liveApi.updateWorkspaceDocumentMetadata).mockRejectedValue(
      new liveApi.LiveApiError("upstream unavailable", 503),
    );
    const editor = createEditor("Session Doc");
    const { result } = renderHook(() => useMarkdownCanvasSession(), {
      wrapper: sessionWrapper([DOCUMENT_METADATA_UPDATE_COMMAND_ID]),
    });
    await waitFor(() => expect(result.current.phase).toMatch(/ready|committed/));
    act(() => {
      result.current.setEditor(editor);
    });
    act(() => {
      editor.editTo("Network-safe draft.");
      result.current.handleEditorUpdate(editor.getJSON(), editor, { programmatic: false });
    });

    let renameResult!: Awaited<ReturnType<typeof result.current.updateDocumentMetadata>>;
    await act(async () => {
      renameResult = await result.current.updateDocumentMetadata({ title: "Network Title" });
    });

    expect(renameResult.ok).toBe(false);
    expect(result.current.record?.title).toBe("Session Doc");
    expect(result.current.snapshot?.loaded_revision).toBe(1);
    expect(result.current.dirty).toBe(true);
  });
});
