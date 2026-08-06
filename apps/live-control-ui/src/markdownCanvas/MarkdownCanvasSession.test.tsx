import type { ReactNode } from "react";
import { act, renderHook, waitFor } from "@testing-library/react";
import type { Editor } from "@tiptap/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import * as liveApi from "../api/liveApi";
import {
  buildInitialWorkspaceDocumentLocalState,
  writeWorkspaceDocumentLocalState,
} from "../tiptap/state/tiptapLocalState";
import { DOCUMENT_SAVE_COMMAND_ID } from "./markdownCanvasTypes";
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
  };
});

const DOC_ID = "22222222-2222-4222-8222-222222222222";
const PLUGIN_WORK_ID = "plugin.work";

const VALID_GRAPH_REFERENCE = {
  kind: "ref" as const,
  refType: "graph-node",
  refId: "threat:tripod-null-calf",
  label: "Tripod Null Calf",
  graphWorldId: null,
  graphCampaignId: null,
  graphScopeMode: null,
  graphRevisionId: null,
};

function createInsertEditor() {
  const run = vi.fn(() => true);
  const chain = {
    focus: vi.fn().mockReturnThis(),
    insertRunbookReference: vi.fn().mockReturnThis(),
    run,
  };
  const editor = {
    getJSON: vi.fn(() => ({
      type: "doc",
      content: [{ type: "paragraph", content: [{ type: "text", text: "Session Doc" }] }],
    })),
    chain: vi.fn(() => chain),
  } as unknown as Editor & {
    chain: ReturnType<typeof vi.fn>;
  };
  return { editor, chain, run };
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

  it("does not expose editor or getEditor on the public session value", async () => {
    const { result } = renderHook(() => useMarkdownCanvasSession(), {
      wrapper: sessionWrapper(),
    });
    await waitFor(() => expect(result.current.phase).toMatch(/ready|committed/));
    expect(result.current).not.toHaveProperty("editor");
    expect(result.current).not.toHaveProperty("getEditor");
  });

  it("insertReference succeeds when editable and marks the document dirty", async () => {
    const { editor, chain, run } = createInsertEditor();
    const { result } = renderHook(() => useMarkdownCanvasSession(), {
      wrapper: sessionWrapper(),
    });
    await waitFor(() => expect(result.current.phase).toBe("ready_clean"));
    expect(result.current.dirty).toBe(false);

    act(() => {
      result.current.setEditor(editor);
    });

    let insertResult!: Awaited<ReturnType<typeof result.current.insertReference>>;
    await act(async () => {
      insertResult = await result.current.insertReference(VALID_GRAPH_REFERENCE);
    });

    expect(insertResult.ok).toBe(true);
    expect(editor.chain).toHaveBeenCalled();
    expect(chain.focus).toHaveBeenCalled();
    expect(chain.insertRunbookReference).toHaveBeenCalledWith(VALID_GRAPH_REFERENCE);
    expect(run).toHaveBeenCalled();
    // Mock editors do not emit handleEditorUpdate; insertReference marks dirty explicitly.
    expect(result.current.dirty).toBe(true);
  });

  it("rejects insertReference during loading without mutating the editor", async () => {
    const { editor, chain } = createInsertEditor();
    const { result } = renderHook(() => useMarkdownCanvasSession(), {
      wrapper: sessionWrapper(),
    });
    await waitFor(() => expect(result.current.phase).toBe("ready_clean"));

    act(() => {
      result.current.setEditor(editor);
    });

    let releaseReload:
      | ((value: Awaited<ReturnType<typeof liveApi.getWorkspaceDocumentSnapshot>>) => void)
      | undefined;
    vi.mocked(liveApi.getWorkspaceDocumentSnapshot).mockImplementationOnce(
      () =>
        new Promise((resolve) => {
          releaseReload = resolve;
        }),
    );

    act(() => {
      void result.current.reloadFromSnapshot();
    });

    await waitFor(() => expect(result.current.phase).toBe("loading"));

    let insertResult!: Awaited<ReturnType<typeof result.current.insertReference>>;
    await act(async () => {
      insertResult = await result.current.insertReference(VALID_GRAPH_REFERENCE);
    });

    expect(insertResult.ok).toBe(false);
    if (!insertResult.ok) {
      expect(insertResult.code).toBe("admission_failed");
      expect(["document_not_editable", "document_missing"]).toContain(insertResult.admissionCode);
    }
    expect(editor.chain).not.toHaveBeenCalled();
    expect(chain.insertRunbookReference).not.toHaveBeenCalled();

    await act(async () => {
      releaseReload?.({
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
    });
  });

  it("rejects insertReference for invalid attrs without editor mutation", async () => {
    const { editor, chain } = createInsertEditor();
    const { result } = renderHook(() => useMarkdownCanvasSession(), {
      wrapper: sessionWrapper(),
    });
    await waitFor(() => expect(result.current.phase).toBe("ready_clean"));

    act(() => {
      result.current.setEditor(editor);
    });

    let insertResult!: Awaited<ReturnType<typeof result.current.insertReference>>;
    await act(async () => {
      insertResult = await result.current.insertReference({
        kind: "ref",
        refType: "graph-node",
        refId: "threat:tripod-null-calf",
        label: "Tripod Null Calf",
        graphWorldId: "eldyrwild",
      });
    });

    expect(insertResult.ok).toBe(false);
    if (!insertResult.ok) {
      expect(insertResult.code).toBe("execute_failed");
      expect(insertResult.reason).toBe("Unsupported reference");
    }
    expect(editor.chain).not.toHaveBeenCalled();
    expect(chain.insertRunbookReference).not.toHaveBeenCalled();
  });

  it("rejects insertReference when the editor lease is missing on an editable document", async () => {
    const { result } = renderHook(() => useMarkdownCanvasSession(), {
      wrapper: sessionWrapper(),
    });
    await waitFor(() => expect(result.current.phase).toBe("ready_clean"));

    let insertResult!: Awaited<ReturnType<typeof result.current.insertReference>>;
    await act(async () => {
      insertResult = await result.current.insertReference(VALID_GRAPH_REFERENCE);
    });

    expect(insertResult.ok).toBe(false);
    if (!insertResult.ok) {
      expect(insertResult.code).toBe("execute_failed");
      expect(insertResult.reason).toBe("Editor lease is stale for the active document.");
    }
  });

  it("invalidates insertReference on unmount before adopting the result", async () => {
    let releaseInsert: (() => void) | undefined;
    const { editor } = createInsertEditor();
    const { result, unmount } = renderHook(() => useMarkdownCanvasSession(), {
      wrapper: sessionWrapper(),
    });
    await waitFor(() => expect(result.current.phase).toBe("ready_clean"));

    act(() => {
      result.current.setEditor(editor);
    });

    let insertPromise!: Promise<Awaited<ReturnType<typeof result.current.insertReference>>>;
    act(() => {
      insertPromise = result.current.runDocumentCommand(
        {
          id: "document.reference.insert",
          conflictsWith: [DOCUMENT_SAVE_COMMAND_ID, PLUGIN_WORK_ID],
          admission: "editable",
          invalidateOnDocumentChange: true,
        },
        () => new Promise<void>((resolve) => {
          releaseInsert = resolve;
        }),
      );
    });

    await waitFor(() => {
      expect(result.current.activeCommand?.id).toBe("document.reference.insert");
    });

    unmount();

    let settled!: Awaited<typeof insertPromise>;
    await act(async () => {
      releaseInsert?.();
      settled = await insertPromise;
    });

    expect(settled.ok).toBe(false);
    if (!settled.ok) {
      expect(["invalidated", "aborted"]).toContain(settled.code);
    }
  });
});
