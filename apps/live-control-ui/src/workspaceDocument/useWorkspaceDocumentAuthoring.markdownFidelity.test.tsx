import { StrictMode, useState } from "react";
import type { Content } from "@tiptap/react";
import { act, fireEvent, render, renderHook, screen, waitFor, within } from "@testing-library/react";
import type { Editor } from "@tiptap/react";
import { Editor as TiptapEditor } from "@tiptap/core";
import { afterAll, afterEach, beforeAll, beforeEach, describe, expect, it, vi } from "vitest";

import {
  authenticatedApiFetch,
  commitTiptapMarkdownWrite,
  getWorkspaceDocumentSnapshot,
  prepareTiptapMarkdownWrite,
} from "../api/liveApi";
import type { WorkspaceDocumentSnapshot } from "../api/types";
import { fixtureWorkspaceDocumentRecord } from "../planSurface/config/planSessionDescriptor";
import {
  readWorkspaceDocumentLocalState,
  workspaceDocumentStorageKey,
} from "../tiptap/state/tiptapLocalState";
import { DEFAULT_MARKDOWN_EDITOR_EXTENSIONS, MarkdownEditorCore } from "../tiptap/MarkdownEditorCore";
import { MarkdownCanvasSessionProvider, useMarkdownCanvasSession } from "../markdownCanvas/MarkdownCanvasSession";
import { BuildDraftRecovery, useBuildMarkdownCanvasSlots } from "../buildSurface/buildMarkdownCanvasAdapter";
import { markdownToTiptapDoc } from "../tiptap/markdown/markdownToTiptap";
import type { WorkspaceDocumentAuthoringValue } from "./useWorkspaceDocumentAuthoring";
import { useWorkspaceDocumentAuthoring } from "./useWorkspaceDocumentAuthoring";

// happy-dom lacks the native dialog API; browser focus/Escape behavior is a rendered gate.
const dialogPrototype = Object.getPrototypeOf(document.createElement("dialog"));
const originalShowModal = Object.getOwnPropertyDescriptor(dialogPrototype, "showModal");
beforeAll(() => {
  Object.defineProperty(dialogPrototype, "showModal", { configurable: true, value(this: HTMLDialogElement) {
    this.setAttribute("open", "");
    this.open = true;
  } });
});
afterAll(() => {
  if (originalShowModal) Object.defineProperty(dialogPrototype, "showModal", originalShowModal);
  else Reflect.deleteProperty(dialogPrototype, "showModal");
});

vi.mock("../api/liveApi", () => ({
  getWorkspaceDocumentSnapshot: vi.fn(),
  authenticatedApiFetch: vi.fn().mockResolvedValue({ response: { ok: false } }),
  prepareTiptapMarkdownWrite: vi.fn(),
  commitTiptapMarkdownWrite: vi.fn(),
}));

const DOC_ID = "11111111-1111-4111-8111-111111111111";

function snapshot(
  markdown: string,
  recordOverrides: Parameters<typeof fixtureWorkspaceDocumentRecord>[0] = {},
): WorkspaceDocumentSnapshot {
  return {
    schema_version: "dmb_workspace_document_snapshot_v1",
    record: fixtureWorkspaceDocumentRecord({
      document_id: DOC_ID,
      kind: "worldbuilding_source",
      campaign_id: "eldyrwild",
      target_session: null,
      revision: 1,
      content_status: "draft",
      ...recordOverrides,
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

  it("seals post-import dogfood markdown on a world-scoped source without lossy save", async () => {
    const importedUnsafe = [
      "# Hesta's Apothecary",
      "",
      "| Item | Note |",
      "| --- | --- |",
      "| Tonic | Rare |",
      "",
      "![Floor plan](assets/hesta-floor.png)",
      "",
      "---",
      "",
      "<div class=\"gm-note\">Hidden shelf</div>",
      "",
    ].join("\n");
    vi.mocked(getWorkspaceDocumentSnapshot).mockResolvedValue(
      snapshot(importedUnsafe, {
        content_status: "committed",
        target_relpath:
          "corpus/eldyrwild-markdown/_dungeonbuddy/sources/11111111-1111-4111-8111-111111111111/source.md",
      }),
    );

    const { result } = renderHook(() => useWorkspaceDocumentAuthoring({
      documentId: DOC_ID,
      surface: "build",
      kind: "worldbuilding_source",
    }));
    await waitFor(() => expect(result.current.phase).toBe("ready_clean"));

    expect(result.current.exportedMarkdownAuthoritative).toBe(true);
    expect(result.current.saveDisabled).toBe(true);
    expect(readWorkspaceDocumentLocalState(localStorage, DOC_ID)?.exported_markdown)
      .toBe(importedUnsafe);

    act(() => {
      result.current.setEditor(editorWithParagraph("Looks safe in the editor"));
      result.current.markDirty();
    });
    await act(async () => {
      await result.current.saveMarkdown();
    });

    expect(prepareTiptapMarkdownWrite).not.toHaveBeenCalled();
    expect(commitTiptapMarkdownWrite).not.toHaveBeenCalled();
    expect(result.current.phase).toBe("save_error");
    expect(result.current.error).toMatch(/sealed projection|cannot round-trip safely/i);
    expect(readWorkspaceDocumentLocalState(localStorage, DOC_ID)?.exported_markdown)
      .toBe(importedUnsafe);
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
    // Unsafe sources seal exported_markdown_authoritative on open; Save must
    // refuse the sealed projection before (and without) durable write.
    expect(result.current.error).toMatch(/sealed projection|cannot round-trip safely/i);
    expect(result.current.exportedMarkdownAuthoritative).toBe(true);
    expect(result.current.saveDisabled).toBe(true);
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

  it("blocks durable save when a Beat identity is missing its canonical heading level", async () => {
    vi.mocked(getWorkspaceDocumentSnapshot).mockResolvedValue(snapshot("# Safe source\n"));

    const { result } = renderHook(() => useWorkspaceDocumentAuthoring({
      documentId: DOC_ID,
      surface: "build",
      kind: "worldbuilding_source",
    }));
    await waitFor(() => expect(result.current.phase).toBe("ready_clean"));

    const beatMissingLevel = editorWithJson({
      type: "doc",
      content: [{
        type: "heading",
        attrs: { playableElementKind: "beat", playableElementId: "beat:x" },
        content: [{ type: "text", text: "Gate opens" }],
      }],
    });
    act(() => {
      result.current.setEditor(beatMissingLevel);
      result.current.markDirty();
    });
    await act(async () => {
      await result.current.saveMarkdown();
    });

    expect(prepareTiptapMarkdownWrite).not.toHaveBeenCalled();
    expect(commitTiptapMarkdownWrite).not.toHaveBeenCalled();
    expect(result.current.phase).toBe("save_error");
    expect(result.current.error).toContain("cannot be represented safely as Markdown");
    expect(result.current.error).toContain("heading level");
  });

  it("blocks durable save when playable identity is nested inside a callout", async () => {
    vi.mocked(getWorkspaceDocumentSnapshot).mockResolvedValue(snapshot("# Safe source\n"));

    const { result } = renderHook(() => useWorkspaceDocumentAuthoring({
      documentId: DOC_ID,
      surface: "build",
      kind: "worldbuilding_source",
    }));
    await waitFor(() => expect(result.current.phase).toBe("ready_clean"));

    const nestedPlayable = editorWithJson({
      type: "doc",
      content: [{
        type: "callout",
        attrs: { kind: "gm-note" },
        content: [{
          type: "heading",
          attrs: { level: 2, playableElementKind: "scene", playableElementId: "scene:arrival" },
          content: [{ type: "text", text: "Arrival" }],
        }],
      }],
    });
    act(() => {
      result.current.setEditor(nestedPlayable);
      result.current.markDirty();
    });
    await act(async () => {
      await result.current.saveMarkdown();
    });

    expect(prepareTiptapMarkdownWrite).not.toHaveBeenCalled();
    expect(commitTiptapMarkdownWrite).not.toHaveBeenCalled();
    expect(result.current.phase).toBe("save_error");
    expect(result.current.error).toContain("cannot be represented safely as Markdown");
    expect(result.current.error).toContain("document-root heading");
  });

  it("does not persist lossy exported_markdown when editing unsafe source", async () => {
    const unsafeSource = "# Source\n\n```json\n{\"hp\": 95}\n```\n";
    vi.mocked(getWorkspaceDocumentSnapshot).mockResolvedValue(snapshot(unsafeSource));

    const { result } = renderHook(() => useWorkspaceDocumentAuthoring({
      documentId: DOC_ID,
      surface: "build",
      kind: "worldbuilding_source",
    }));
    await waitFor(() => expect(result.current.phase).toBe("ready_clean"));

    const safeParagraph = {
      type: "doc",
      content: [{ type: "paragraph", content: [{ type: "text", text: "Looks safe in editor" }] }],
    };
    act(() => {
      result.current.setEditor(editorWithJson(safeParagraph));
      result.current.handleEditorUpdate(safeParagraph, editorWithJson(safeParagraph), { programmatic: false });
    });

    const stored = JSON.parse(localStorage.getItem(workspaceDocumentStorageKey(DOC_ID)) ?? "null") as {
      exported_markdown?: string;
      exported_markdown_authoritative?: boolean;
    } | null;
    expect(stored?.exported_markdown).toBe(unsafeSource);
    expect(stored?.exported_markdown_authoritative).toBe(true);

    await act(async () => {
      await result.current.saveMarkdown();
    });
    expect(prepareTiptapMarkdownWrite).not.toHaveBeenCalled();
    expect(commitTiptapMarkdownWrite).not.toHaveBeenCalled();
  });

  it("keeps authoritative unsafe markdown across public read/reconcile after local edit", async () => {
    const unsafeSource = "# Source\n\n```json\n{\"hp\": 95}\n```\n";
    vi.mocked(getWorkspaceDocumentSnapshot).mockResolvedValue(snapshot(unsafeSource));

    const first = renderHook(() => useWorkspaceDocumentAuthoring({
      documentId: DOC_ID,
      surface: "build",
      kind: "worldbuilding_source",
    }));
    await waitFor(() => expect(first.result.current.phase).toBe("ready_clean"));

    const safeParagraph = {
      type: "doc",
      content: [{ type: "paragraph", content: [{ type: "text", text: "Looks safe in editor" }] }],
    };
    act(() => {
      first.result.current.setEditor(editorWithJson(safeParagraph));
      first.result.current.handleEditorUpdate(safeParagraph, editorWithJson(safeParagraph), {
        programmatic: false,
      });
    });

    // Raw localStorage still has authoritative source (persist path).
    const raw = JSON.parse(localStorage.getItem(workspaceDocumentStorageKey(DOC_ID)) ?? "null") as {
      exported_markdown?: string;
      exported_markdown_authoritative?: boolean;
      tiptap_json?: unknown;
    } | null;
    expect(raw?.exported_markdown).toBe(unsafeSource);
    expect(raw?.exported_markdown_authoritative).toBe(true);

    // Public read must not re-derive exported_markdown from lossy TipTap JSON.
    const viaRead = readWorkspaceDocumentLocalState(localStorage, DOC_ID);
    expect(viaRead?.exported_markdown).toBe(unsafeSource);
    expect(viaRead?.exported_markdown_authoritative).toBe(true);
    expect(viaRead?.exported_markdown).not.toContain("Looks safe in editor");
    expect(viaRead?.tiptap_json).toEqual(safeParagraph);
    expect(viaRead?.dirty).toBe(true);

    first.unmount();

    const reopened = renderHook(() => useWorkspaceDocumentAuthoring({
      documentId: DOC_ID,
      surface: "build",
      kind: "worldbuilding_source",
    }));
    await waitFor(() => expect(reopened.result.current.phase).toBe("ready_dirty"));

    expect(reopened.result.current.dirty).toBe(true);
    expect(reopened.result.current.editorContent).toEqual(safeParagraph);
    expect(readWorkspaceDocumentLocalState(localStorage, DOC_ID)?.exported_markdown).toBe(unsafeSource);
    expect(reopened.result.current.exportedMarkdownAuthoritative).toBe(true);
    expect(reopened.result.current.saveDisabled).toBe(true);

    act(() => {
      reopened.result.current.setEditor(editorWithJson(safeParagraph));
    });
    await act(async () => {
      await reopened.result.current.saveMarkdown();
    });
    expect(prepareTiptapMarkdownWrite).not.toHaveBeenCalled();
    expect(commitTiptapMarkdownWrite).not.toHaveBeenCalled();
    expect(String(reopened.result.current.error ?? "")).toMatch(/sealed projection/i);
  });

  it("blocks Save of a sealed lossy TipTap projection after the source becomes parse-safe until re-import", async () => {
    // Simulate a parser-upgrade world: sealed source is currently import-safe,
    // but TipTap still holds the older lossy projection.
    const sealedSource = "# Authoritative source\n\nKeep this body.\n";
    const lossyProjection = {
      type: "doc",
      content: [{ type: "paragraph", content: [{ type: "text", text: "Stale lossy projection" }] }],
    };
    vi.mocked(getWorkspaceDocumentSnapshot).mockResolvedValue(snapshot(sealedSource));
    localStorage.setItem(
      workspaceDocumentStorageKey(DOC_ID),
      JSON.stringify({
        schema_version: "dmb_workspace_document_local_state_v4",
        document_id: DOC_ID,
        title: "World Lore",
        campaign_id: "eldyrwild",
        kind: "worldbuilding_source",
        target_session: null,
        surface: "build",
        base_revision: 1,
        base_content_sha256: "sha-source",
        tiptap_json: lossyProjection,
        exported_markdown: sealedSource,
        exported_markdown_authoritative: true,
        dirty: true,
        created_at: "2026-08-09T00:00:00.000Z",
        updated_at: "2026-08-09T00:00:00.000Z",
        last_local_save_at: "2026-08-09T00:00:00.000Z",
      }),
    );

    const { result } = renderHook(() => useWorkspaceDocumentAuthoring({
      documentId: DOC_ID,
      surface: "build",
      kind: "worldbuilding_source",
    }));
    await waitFor(() => expect(result.current.phase).toBe("ready_dirty"));
    expect(result.current.exportedMarkdownAuthoritative).toBe(true);
    expect(result.current.editorContent).toEqual(lossyProjection);
    expect(result.current.saveDisabled).toBe(true);

    act(() => {
      result.current.setEditor(editorWithJson(lossyProjection));
    });
    await act(async () => {
      await result.current.saveMarkdown();
    });
    expect(prepareTiptapMarkdownWrite).not.toHaveBeenCalled();
    expect(commitTiptapMarkdownWrite).not.toHaveBeenCalled();
    expect(result.current.error).toMatch(/sealed projection/i);

    act(() => {
      result.current.reimportFromAuthoritativeMarkdown();
    });
    expect(result.current.exportedMarkdownAuthoritative).toBe(false);
    expect(result.current.editorContent).not.toEqual(lossyProjection);
    expect(readWorkspaceDocumentLocalState(localStorage, DOC_ID)?.exported_markdown_authoritative)
      .toBe(false);

    vi.mocked(prepareTiptapMarkdownWrite).mockResolvedValue({
      schema_version: "dmb_tiptap_markdown_write_prepare_v1",
      document_id: DOC_ID,
      title: "World Lore",
      target_relpath: "corpus/source.md",
      target_display_path: "corpus/source.md",
      registry_revision: 1,
      file_exists: true,
      writer_ok: true,
      writer_phase: "prepare",
      writer_confirm_token: "confirm-token",
      writer_diff: "+Edited after re-import",
      warnings: [],
      diagnostics: [],
    });
    const committedMarkdown = "# Authoritative source\n\nEdited after re-import.\n";
    vi.mocked(commitTiptapMarkdownWrite).mockResolvedValue({
      schema_version: "dmb_tiptap_markdown_write_commit_v1",
      document_id: DOC_ID,
      title: "World Lore",
      target_relpath: "corpus/source.md",
      target_display_path: "corpus/source.md",
      registry_revision: 2,
      committed_revision: 2,
      committed_record: fixtureWorkspaceDocumentRecord({
        document_id: DOC_ID,
        kind: "worldbuilding_source",
        campaign_id: "eldyrwild",
        target_session: null,
        revision: 2,
        content_status: "draft",
      }),
      normalized_content_sha256: "sha-committed",
      writer_ok: true,
      file_fingerprint: "fp-committed",
      diagnostics: [],
    });
    vi.mocked(getWorkspaceDocumentSnapshot).mockResolvedValue({
      ...snapshot(committedMarkdown),
      content_sha256: "sha-committed",
      file_fingerprint: "fp-committed",
      loaded_revision: 2,
      record: fixtureWorkspaceDocumentRecord({
        document_id: DOC_ID,
        kind: "worldbuilding_source",
        campaign_id: "eldyrwild",
        target_session: null,
        revision: 2,
        content_status: "draft",
      }),
    });

    // After re-import, TipTap matches sealed source → dirty clears → Save stays
    // disabled by requireDirtyToSave. Force a post-reimport edit, then Save.
    const edited = {
      type: "doc",
      content: [{
        type: "heading",
        attrs: { level: 1 },
        content: [{ type: "text", text: "Authoritative source" }],
      }, {
        type: "paragraph",
        content: [{ type: "text", text: "Edited after re-import." }],
      }],
    };
    act(() => {
      result.current.setEditor(editorWithJson(edited));
      result.current.handleEditorUpdate(edited, editorWithJson(edited), { programmatic: false });
    });
    expect(result.current.exportedMarkdownAuthoritative).toBe(false);
    expect(result.current.saveDisabled).toBe(false);

    await act(async () => {
      await result.current.saveMarkdown();
    });
    expect(prepareTiptapMarkdownWrite).toHaveBeenCalledTimes(1);
    expect(commitTiptapMarkdownWrite).toHaveBeenCalledTimes(1);
    const preparedMarkdown = vi.mocked(prepareTiptapMarkdownWrite).mock.calls[0]?.[0]?.markdown ?? "";
    expect(preparedMarkdown).toContain("Edited after re-import.");
    expect(preparedMarkdown).not.toContain("Stale lossy projection");
  });
});


describe("real rich-editor mount and saved-source cleanliness", () => {
  beforeEach(() => { vi.clearAllMocks(); localStorage.clear(); });

  it("keeps Read→Edit and editable toggles clean until the first genuine document transaction", async () => {
    const source = "---\r\ntitle: Guard notes\r\n---\r\n###   Gate    watch\r\n\r\nA **quiet** gate.\r\n";
    vi.mocked(getWorkspaceDocumentSnapshot).mockResolvedValue(snapshot(source, { content_status: "committed" }));
    let current!: WorkspaceDocumentAuthoringValue;
    function Harness() {
      const session = useWorkspaceDocumentAuthoring({ documentId: DOC_ID, surface: "build", kind: "worldbuilding_source" });
      current = session;
      const [editing, setEditing] = useState(false);
      const [editable, setEditable] = useState(true);
      return <>
        <button onClick={() => setEditing(value => !value)}>Read or Edit</button>
        <button onClick={() => setEditable(value => !value)}>Toggle editable</button>
        {editing && session.phase.startsWith("ready") ? <MarkdownEditorCore
          documentKey={session.documentKey} content={session.editorContent as Content}
          editable={editable} onEditorChange={session.setEditor} onUpdate={session.handleEditorUpdate}
        /> : <p>Reading saved source</p>}
      </>;
    }
    render(<StrictMode><Harness /></StrictMode>);
    await waitFor(() => expect(current.phase).toBe("ready_clean"));
    const initial = readWorkspaceDocumentLocalState(localStorage, DOC_ID)!;
    fireEvent.click(screen.getByRole("button", { name: "Read or Edit" }));
    await waitFor(() => expect(current.editor).not.toBeNull());
    await act(async () => { await Promise.resolve(); });
    expect(current.editor!.getJSON()).toMatchObject(markdownToTiptapDoc(source).doc);
    const mountedJson = current.editor!.getJSON();
    expect(current.dirty).toBe(false);
    expect(readWorkspaceDocumentLocalState(localStorage, DOC_ID)).toEqual(initial);
    fireEvent.click(screen.getByRole("button", { name: "Toggle editable" }));
    await waitFor(() => expect(current.editor!.isEditable).toBe(false));
    fireEvent.click(screen.getByRole("button", { name: "Toggle editable" }));
    await waitFor(() => expect(current.editor!.isEditable).toBe(true));
    expect(current.editor!.getJSON()).toEqual(mountedJson);
    expect(current.dirty).toBe(false);
    expect(readWorkspaceDocumentLocalState(localStorage, DOC_ID)).toEqual(initial);
    fireEvent.click(screen.getByRole("button", { name: "Read or Edit" }));
    fireEvent.click(screen.getByRole("button", { name: "Read or Edit" }));
    await waitFor(() => expect(current.editor).not.toBeNull());
    await act(async () => { await Promise.resolve(); });
    expect(current.dirty).toBe(false);
    act(() => { current.editor!.commands.insertContent("A real addition."); });
    await waitFor(() => expect(current.dirty).toBe(true));
    const edited = readWorkspaceDocumentLocalState(localStorage, DOC_ID)!;
    expect(edited.exported_markdown).toContain("A real addition.");
    expect(edited.base_revision).toBe(initial.base_revision);
    expect(edited.base_content_sha256).toBe(initial.base_content_sha256);
    const editedJson = current.editor!.getJSON();
    fireEvent.click(screen.getByRole("button", { name: "Read or Edit" }));
    fireEvent.click(screen.getByRole("button", { name: "Read or Edit" }));
    await waitFor(() => expect(current.editor).not.toBeNull());
    await act(async () => { await Promise.resolve(); });
    expect(current.editor!.getJSON()).toEqual(editedJson);
    expect(current.dirty).toBe(true);
    expect(readWorkspaceDocumentLocalState(localStorage, DOC_ID)).toEqual(edited);
    expect(current.snapshot!.markdown).toBe(source);
    expect(prepareTiptapMarkdownWrite).not.toHaveBeenCalled();
    expect(commitTiptapMarkdownWrite).not.toHaveBeenCalled();
  });
});


describe("real-session Save and Build discard exclusion", () => {
  beforeEach(() => { vi.clearAllMocks(); localStorage.clear(); });
  afterEach(() => { vi.restoreAllMocks(); });

  it("cannot discard during deferred prepare/commit or invalidate the resulting receipt", async () => {
    function deferred<T>() {
      let resolve!: (value: T) => void;
      const promise = new Promise<T>(done => { resolve = done; });
      return { promise, resolve };
    }
    const prepare = deferred<Awaited<ReturnType<typeof prepareTiptapMarkdownWrite>>>();
    const commit = deferred<Awaited<ReturnType<typeof commitTiptapMarkdownWrite>>>();
    const original = snapshot("Original source.\n", { content_status: "committed" });
    let verified = original;
    vi.mocked(getWorkspaceDocumentSnapshot).mockImplementation(async () => verified);
    vi.mocked(prepareTiptapMarkdownWrite).mockReturnValue(prepare.promise);
    vi.mocked(commitTiptapMarkdownWrite).mockReturnValue(commit.promise);
    let current!: ReturnType<typeof useMarkdownCanvasSession>;
    function Controls() {
      current = useMarkdownCanvasSession();
      const slots = useBuildMarkdownCanvasSlots({ hideFooterSave: true });
      return current.snapshot ? <>
        {slots.tools}
        <MarkdownEditorCore documentKey={current.documentKey}
          content={current.editorContent as Content} onEditorChange={current.setEditor}
          onUpdate={current.handleEditorUpdate} />
      </> : null;
    }
    render(<MarkdownCanvasSessionProvider documentId={DOC_ID} surface="build" kind="worldbuilding_source">
      <Controls />
    </MarkdownCanvasSessionProvider>);
    await waitFor(() => expect(current.editor).not.toBeNull());
    await act(async () => { await Promise.resolve(); });
    act(() => { current.editor!.commands.insertContent("A real edit. "); });
    await waitFor(() => expect(current.dirty).toBe(true));
    const dirty = readWorkspaceDocumentLocalState(localStorage, DOC_ID);
    fireEvent.click(screen.getByRole("button", { name: "Discard draft", exact: true }));
    expect(screen.getByRole("alertdialog")).toBeInTheDocument();
    fireEvent.click(within(screen.getByRole("alertdialog")).getByRole("button", { name: "Keep editing" }));
    expect(screen.queryByRole("alertdialog")).not.toBeInTheDocument();
    expect(current.dirty).toBe(true);
    expect(readWorkspaceDocumentLocalState(localStorage, DOC_ID)).toEqual(dirty);
    expect(getWorkspaceDocumentSnapshot).toHaveBeenCalledTimes(1);
    fireEvent.click(screen.getByRole("button", { name: "Discard draft", exact: true }));
    let saving!: Promise<void>;
    act(() => { saving = current.saveMarkdown(); });
    await waitFor(() => expect(current.phase).toBe("preparing"));
    expect(current.activeCommand).not.toBeNull();
    let discard = within(screen.getByRole("alertdialog")).getByRole("button", { name: "Discard changes" });
    expect(discard).toBeDisabled();
    fireEvent.click(discard);
    expect(readWorkspaceDocumentLocalState(localStorage, DOC_ID)).toEqual(dirty);
    expect(getWorkspaceDocumentSnapshot).toHaveBeenCalledTimes(1);
    await act(async () => {
      prepare.resolve({ schema_version: "dmb_tiptap_markdown_write_prepare_v1", document_id: DOC_ID,
        title: "Source", target_relpath: "corpus/source.md", target_display_path: "corpus/source.md",
        registry_revision: 1, file_exists: true, writer_ok: true, writer_phase: "prepare",
        writer_confirm_token: "synthetic-confirm", writer_diff: "+A real edit.", warnings: [], diagnostics: [] });
    });
    await waitFor(() => expect(current.phase).toBe("committing"));
    discard = within(screen.getByRole("alertdialog")).getByRole("button", { name: "Discard changes" });
    expect(discard).toBeDisabled();
    fireEvent.click(discard);
    expect(getWorkspaceDocumentSnapshot).toHaveBeenCalledTimes(1);
    expect(readWorkspaceDocumentLocalState(localStorage, DOC_ID)).toEqual(dirty);
    const committedMarkdown = vi.mocked(commitTiptapMarkdownWrite).mock.calls[0][0].markdown;
    const record = fixtureWorkspaceDocumentRecord({ document_id: DOC_ID, kind: "worldbuilding_source",
      revision: 2, content_status: "committed", target_session: null });
    verified = { ...snapshot(committedMarkdown), record, loaded_revision: 2,
      content_sha256: "sha-committed", file_fingerprint: "fp-committed" };
    await act(async () => {
      commit.resolve({ schema_version: "dmb_tiptap_markdown_write_commit_v1", document_id: DOC_ID,
        title: record.title, target_relpath: record.target_relpath, target_display_path: record.target_relpath,
        registry_revision: 2, committed_revision: 2, committed_record: record,
        normalized_content_sha256: "sha-committed", writer_ok: true, bytes_written: committedMarkdown.length,
        file_fingerprint: "fp-committed", diagnostics: [] });
      await saving;
    });
    await waitFor(() => expect(current.phase).toBe("ready_clean"));
    expect(screen.queryByRole("alertdialog")).not.toBeInTheDocument();
    expect(current.lastCommitReceipt?.committed_revision).toBe(2);
    expect(current.snapshot?.loaded_revision).toBe(2);
    expect(current.snapshot?.markdown).toBe(committedMarkdown);
    expect(readWorkspaceDocumentLocalState(localStorage, DOC_ID)?.base_revision).toBe(2);
    expect(readWorkspaceDocumentLocalState(localStorage, DOC_ID)?.base_content_sha256).toBe("sha-committed");
    expect(current.activeCommand).toBeNull();
    expect(prepareTiptapMarkdownWrite).toHaveBeenCalledTimes(1);
    expect(commitTiptapMarkdownWrite).toHaveBeenCalledTimes(1);
    expect(getWorkspaceDocumentSnapshot).toHaveBeenCalledTimes(2);
  });
});


describe("verified protected draft recovery", () => {
  const source = "---\ntitle: Kept metadata\n---\n# Preserved source\n\nOriginal wording.\n";
  const projection = { type: "doc", content: [{ type: "paragraph", content: [{ type: "text", text: "Unsaved local wording" }] }] };
  const key = workspaceDocumentStorageKey(DOC_ID) + ".recovery.v1";
  function seed(markdown = source) {
    vi.mocked(getWorkspaceDocumentSnapshot).mockResolvedValue(snapshot(markdown));
    localStorage.setItem(workspaceDocumentStorageKey(DOC_ID), JSON.stringify({
      schema_version: "dmb_workspace_document_local_state_v5", document_id: DOC_ID,
      title: "World Lore", campaign_id: "eldyrwild", kind: "worldbuilding_source",
      target_session: null, surface: "build", base_revision: 1, base_content_sha256: "sha-source",
      tiptap_json: projection, exported_markdown: markdown, exported_markdown_authoritative: true,
      dirty: true, created_at: "2026-10-17T00:00:00Z", updated_at: "2026-10-17T00:00:00Z", last_local_save_at: "2026-10-17T00:00:00Z",
    }));
  }
  beforeEach(() => { vi.clearAllMocks(); localStorage.clear(); });
  it("preserves both versions and restores exact protected content after remount without server writes", async () => {
    seed();
    const first = renderHook(() => useWorkspaceDocumentAuthoring({ documentId: DOC_ID, surface: "build", kind: "worldbuilding_source" }));
    await waitFor(() => expect(first.result.current.phase).toBe("ready_dirty"));
    act(() => first.result.current.setEditor(editorWithJson(projection)));
    const original = readWorkspaceDocumentLocalState(localStorage, DOC_ID);
    const review = first.result.current.prepareDraftRecovery();
    expect(first.result.current.saveDisabledReason).toMatch(/protected after an earlier editing problem/);
    expect(localStorage.getItem(key)).toBeNull();
    act(() => first.result.current.confirmDraftRecovery(review));
    const checkpoint = JSON.parse(localStorage.getItem(key)!);
    expect(checkpoint.original.tiptap_json).toEqual(projection);
    expect(checkpoint.original.exported_markdown).toBe(source);
    expect(first.result.current.exportedMarkdownAuthoritative).toBe(false);
    expect(readWorkspaceDocumentLocalState(localStorage, DOC_ID)?.exported_markdown).toContain("title: Kept metadata");
    first.unmount();
    const reopened = renderHook(() => useWorkspaceDocumentAuthoring({ documentId: DOC_ID, surface: "build", kind: "worldbuilding_source" }));
    await waitFor(() => expect(reopened.result.current.phase).toMatch(/^ready/));
    act(() => reopened.result.current.setEditor(editorWithJson(reopened.result.current.editorContent)));
    expect(reopened.result.current.draftRecoveryAvailable).toBe(true);
    act(() => reopened.result.current.restoreDraftRecovery());
    expect(reopened.result.current.exportedMarkdownAuthoritative).toBe(true);
    expect(reopened.result.current.dirty).toBe(true);
    expect(reopened.result.current.editorContent).toEqual(projection);
    expect(readWorkspaceDocumentLocalState(localStorage, DOC_ID)).toEqual(original);
    expect(localStorage.getItem(key)).toBeNull();
    expect(prepareTiptapMarkdownWrite).not.toHaveBeenCalled();
    expect(commitTiptapMarkdownWrite).not.toHaveBeenCalled();
  });
  it("restores the real rich editor through the Build recovery controls", async () => {
    seed();
    let current!: ReturnType<typeof useMarkdownCanvasSession>;
    function RecoveryCanvas() {
      current = useMarkdownCanvasSession();
      return <>
        <BuildDraftRecovery session={current} />
        {current.phase.startsWith("ready") ? <MarkdownEditorCore documentKey={current.documentKey}
          content={current.editorContent as Content} editable onEditorChange={current.setEditor}
          onUpdate={current.handleEditorUpdate} /> : null}
      </>;
    }
    render(<MarkdownCanvasSessionProvider documentId={DOC_ID} surface="build" kind="worldbuilding_source"><RecoveryCanvas /></MarkdownCanvasSessionProvider>);
    await waitFor(() => expect(current.editor).not.toBeNull());
    const originalJson = current.editor!.getJSON();
    fireEvent.click(screen.getByRole("button", { name: "Review protected draft", exact: true }));
    const dialog = screen.getByRole("dialog", { name: "Review protected draft" });
    expect(dialog).toHaveTextContent("Unsaved local wording");
    fireEvent.click(within(dialog).getByRole("button", { name: "Use preserved version" }));
    await waitFor(() => expect(current.exportedMarkdownAuthoritative).toBe(false));
    await waitFor(() => expect(current.editor?.getText()).toContain("Original wording."));
    fireEvent.click(screen.getByRole("button", { name: "Restore protected draft" }));
    await waitFor(() => expect(current.exportedMarkdownAuthoritative).toBe(true));
    await waitFor(() => expect(current.editor?.getJSON()).toEqual(originalJson));
    expect(current.dirty).toBe(true);
    expect(prepareTiptapMarkdownWrite).not.toHaveBeenCalled();
    expect(commitTiptapMarkdownWrite).not.toHaveBeenCalled();
  });

  it.each([false, true])("keeps the actual image/table page, with explicit spacer normalization=%s, and restores its original seal", async withSpacer => {
    seed();
    vi.mocked(authenticatedApiFetch).mockResolvedValue({ response: new Response(null, {status:404}), csrf: null, requestEpoch: 0 });
    const currentDoc = markdownToTiptapDoc("# Current page\n\n![Map](dmb-media:11111111-1111-4111-8111-111111111111)\n\n| d20 | Soldier |\n| --- | --- |\n| 1 | Local edit |\n").doc;
    if (withSpacer) currentDoc.content!.splice(1, 0, { type: "paragraph" });
    const stored = readWorkspaceDocumentLocalState(localStorage, DOC_ID)!;
    localStorage.setItem(workspaceDocumentStorageKey(DOC_ID), JSON.stringify({ ...stored, tiptap_json: currentDoc }));
    let current!: ReturnType<typeof useMarkdownCanvasSession>;
    function Canvas() {
      current = useMarkdownCanvasSession();
      return <><BuildDraftRecovery session={current} />{current.phase.startsWith("ready") ? <MarkdownEditorCore documentKey={current.documentKey}
        content={current.editorContent as Content} editable onEditorChange={current.setEditor} onUpdate={current.handleEditorUpdate} /> : null}</>;
    }
    render(<MarkdownCanvasSessionProvider documentId={DOC_ID} surface="build" kind="worldbuilding_source"><Canvas /></MarkdownCanvasSessionProvider>);
    await waitFor(() => expect(current.editor).not.toBeNull());
    const original = current.editor!.getJSON();
    fireEvent.click(screen.getByRole("button", {name:"Review protected draft",exact:true}));
    if (withSpacer) {
      const review = current.prepareDraftRecovery();
      expect(review.canNormalizeCurrent).toBe(true);
      expect(review.removedSpacers).toBe(1);
      expect(() => current.confirmDraftRecovery(review, "current")).toThrow(/structure would change/);
      expect(localStorage.getItem(key)).toBeNull();
    }
    const keep = screen.getByRole("button", {name: withSpacer ? "Keep content, tidy spacing and resume saving" : "Keep current page and resume saving"});
    expect(keep).toBeEnabled();
    fireEvent.click(keep);
    await waitFor(() => expect(current.exportedMarkdownAuthoritative).toBe(false));
    const kept = withSpacer ? { ...original, content: original.content!.filter(node => node.type !== "paragraph" || Boolean(node.content?.length)) } : original;
    await waitFor(() => expect(current.editor?.getJSON()).toEqual(kept));
    expect(current.saveDisabled).toBe(false);
    expect(JSON.parse(localStorage.getItem(key)!).original.tiptap_json).toEqual(original);
    expect(prepareTiptapMarkdownWrite).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole("button", {name:"Restore protected draft"}));
    await waitFor(() => expect(current.exportedMarkdownAuthoritative).toBe(true));
    await waitFor(() => expect(current.editor?.getJSON()).toEqual(original));
  });
  it("actual Discard controls replace the protected projection with the supported saved page", async () => {
    seed();
    let current!: ReturnType<typeof useMarkdownCanvasSession>;
    function Canvas() {
      current = useMarkdownCanvasSession();
      return <><BuildDraftRecovery session={current} />{current.phase.startsWith("ready") ? <MarkdownEditorCore documentKey={current.documentKey}
        content={current.editorContent as Content} editable onEditorChange={current.setEditor} onUpdate={current.handleEditorUpdate} /> : null}</>;
    }
    render(<MarkdownCanvasSessionProvider documentId={DOC_ID} surface="build" kind="worldbuilding_source"><Canvas /></MarkdownCanvasSessionProvider>);
    await waitFor(() => expect(current.editor).not.toBeNull());
    fireEvent.click(screen.getByRole("button", {name:"Discard draft",exact:true}));
    fireEvent.click(screen.getByRole("button", {name:"Discard changes",exact:true}));
    await waitFor(() => expect(current.exportedMarkdownAuthoritative).toBe(false));
    await waitFor(() => expect(current.editor?.getText()).toContain("Original wording."));
    expect(current.editor?.getText()).not.toContain("Unsaved local wording");
    expect(current.phase).toBe("ready_clean");
  });

  it.each(["source", "editor"])("does not resume a currently unsupported %s", async kind => {
    seed(kind === "source" ? "# Source\n\n<div>Unsupported</div>" : source);
    const { result } = renderHook(() => useWorkspaceDocumentAuthoring({documentId:DOC_ID,surface:"build",kind:"worldbuilding_source"}));
    await waitFor(() => expect(result.current.phase).toBe("ready_dirty"));
    const editor = new TiptapEditor({ extensions: DEFAULT_MARKDOWN_EDITOR_EXTENSIONS,
      content: kind === "editor" ? {type:"doc",content:[{type:"codeBlock",content:[{type:"text",text:"Unsupported code"}]}]} : projection });
    try {
      act(() => result.current.setEditor(editor));
      const before = localStorage.getItem(workspaceDocumentStorageKey(DOC_ID));
      const review = result.current.prepareDraftRecovery();
      expect(review.canKeepCurrent).toBe(false);
      expect(() => result.current.confirmDraftRecovery(review, "current")).toThrow();
      expect(localStorage.getItem(workspaceDocumentStorageKey(DOC_ID))).toBe(before);
      expect(localStorage.getItem(key)).toBeNull();
      expect(result.current.exportedMarkdownAuthoritative).toBe(true);
    } finally { editor.destroy(); }
  });

  it.each(["quota", "readback"])("leaves projection and seal intact when checkpoint %s fails", async failure => {
    seed();
    const storage = {
      getItem: (k: string) => k === key && failure === "readback" ? null : localStorage.getItem(k),
      setItem: (k: string, v: string) => { if (k === key && failure === "quota") throw new Error("Quota exceeded"); localStorage.setItem(k, v); },
      removeItem: (k: string) => localStorage.removeItem(k),
    };
    const { result } = renderHook(() => useWorkspaceDocumentAuthoring({ documentId: DOC_ID, surface: "build", kind: "worldbuilding_source", storage }));
    await waitFor(() => expect(result.current.phase).toBe("ready_dirty"));
    act(() => result.current.setEditor(editorWithJson(projection)));
    const before = localStorage.getItem(workspaceDocumentStorageKey(DOC_ID));
    const review = result.current.prepareDraftRecovery();
    expect(() => result.current.confirmDraftRecovery(review)).toThrow();
    expect(result.current.editorContent).toEqual(projection);
    expect(result.current.exportedMarkdownAuthoritative).toBe(true);
    expect(localStorage.getItem(workspaceDocumentStorageKey(DOC_ID))).toBe(before);
  });
  it("invalidates review when live editor changes and refuses restore over newer edits", async () => {
    seed();
    const { result } = renderHook(() => useWorkspaceDocumentAuthoring({ documentId: DOC_ID, surface: "build", kind: "worldbuilding_source" }));
    await waitFor(() => expect(result.current.phase).toBe("ready_dirty"));
    const editor = editorWithJson(projection);
    act(() => result.current.setEditor(editor));
    const review = result.current.prepareDraftRecovery();
    vi.mocked(editor.getJSON).mockReturnValue({ type: "doc", content: [] });
    expect(() => result.current.confirmDraftRecovery(review)).toThrow(/changed after review/);
    expect(localStorage.getItem(key)).toBeNull();
    vi.mocked(editor.getJSON).mockReturnValue(projection);
    act(() => result.current.confirmDraftRecovery(result.current.prepareDraftRecovery()));
    act(() => result.current.setEditor(editorWithParagraph("Newer unique edits")));
    expect(() => result.current.restoreDraftRecovery()).toThrow(/newer edits/);
    expect(localStorage.getItem(key)).not.toBeNull();
  });
  it.each(["before review", "after review", "before restore"])("preserves another tab's persisted edits %s", async timing => {
    seed();
    const { result } = renderHook(() => useWorkspaceDocumentAuthoring({ documentId: DOC_ID, surface: "build", kind: "worldbuilding_source" }));
    await waitFor(() => expect(result.current.phase).toBe("ready_dirty"));
    act(() => result.current.setEditor(editorWithJson(projection)));
    const review = timing === "before review" ? null : result.current.prepareDraftRecovery();
    if (timing === "before restore") {
      act(() => result.current.confirmDraftRecovery(review!));
      act(() => result.current.setEditor(editorWithJson(result.current.editorContent)));
    }
    const checkpoint = localStorage.getItem(key);
    const stored = readWorkspaceDocumentLocalState(localStorage, DOC_ID)!;
    const other = JSON.stringify({ ...stored, tiptap_json: { type: "doc", content: [{ type: "paragraph", content: [{ type: "text", text: "Other tab unique edits" }] }] } });
    localStorage.setItem(workspaceDocumentStorageKey(DOC_ID), other);
    expect(() => timing === "before review" ? result.current.prepareDraftRecovery()
      : timing === "after review" ? result.current.confirmDraftRecovery(review!)
      : result.current.restoreDraftRecovery()).toThrow(/stored draft changed/);
    expect(localStorage.getItem(workspaceDocumentStorageKey(DOC_ID))).toBe(other);
    expect(localStorage.getItem(key)).toBe(checkpoint);
  });
  it.each([null, "not JSON"])("refuses recovery with missing/unreadable stored draft %s", async raw => {
    seed();
    const { result } = renderHook(() => useWorkspaceDocumentAuthoring({ documentId: DOC_ID, surface: "build", kind: "worldbuilding_source" }));
    await waitFor(() => expect(result.current.phase).toBe("ready_dirty"));
    act(() => result.current.setEditor(editorWithJson(projection)));
    if (raw == null) localStorage.removeItem(workspaceDocumentStorageKey(DOC_ID));
    else localStorage.setItem(workspaceDocumentStorageKey(DOC_ID), raw);
    expect(() => result.current.prepareDraftRecovery()).toThrow(/stored draft changed/);
    expect(localStorage.getItem(workspaceDocumentStorageKey(DOC_ID))).toBe(raw);
    expect(localStorage.getItem(key)).toBeNull();
  });
  it("keeps unsupported source protected without creating a checkpoint", async () => {
    seed("# Source\n\n<div>Unsupported raw HTML</div>\n");
    const { result } = renderHook(() => useWorkspaceDocumentAuthoring({ documentId: DOC_ID, surface: "build", kind: "worldbuilding_source" }));
    await waitFor(() => expect(result.current.phase).toBe("ready_dirty"));
    act(() => result.current.setEditor(editorWithJson(projection)));
    expect(() => result.current.confirmDraftRecovery(result.current.prepareDraftRecovery())).toThrow(/cannot be safely imported/);
    expect(localStorage.getItem(key)).toBeNull();
    expect(result.current.exportedMarkdownAuthoritative).toBe(true);
  });
});


describe("ordinary save preserves the mounted rich editor", () => {
  beforeEach(() => { vi.clearAllMocks(); localStorage.clear(); });
  it("retains editor identity, selection and undo across successive acknowledged saves", async () => {
    let saved = snapshot("The road enters the marsh.\n", { content_status: "committed" });
    vi.mocked(getWorkspaceDocumentSnapshot).mockImplementation(async () => saved);
    vi.mocked(prepareTiptapMarkdownWrite).mockResolvedValue({
      schema_version: "dmb_tiptap_markdown_write_prepare_v1", document_id: DOC_ID,
      title: "Source", target_relpath: saved.record.target_relpath, target_display_path: "Source",
      registry_revision: 1, file_exists: true, writer_ok: true, writer_phase: "prepare",
      writer_confirm_token: "token", writer_diff: "", warnings: [], diagnostics: [],
    });
    vi.mocked(commitTiptapMarkdownWrite).mockImplementation(async request => {
      const revision = saved.loaded_revision + 1;
      saved = { ...saved, markdown: request.markdown, loaded_revision: revision,
        record: { ...saved.record, revision }, content_sha256: 'sha-'+revision, file_fingerprint:'fp-'+revision };
      return {schema_version:'dmb_tiptap_markdown_write_commit_v1',document_id:DOC_ID,
        title:'Source',target_relpath:saved.record.target_relpath,target_display_path:'Source',
        registry_revision:revision,committed_revision:revision,committed_record:saved.record,
        normalized_content_sha256:saved.content_sha256,writer_ok:true,bytes_written:request.markdown.length,
        file_fingerprint:saved.file_fingerprint,diagnostics:[]};
    });
    let current!: WorkspaceDocumentAuthoringValue;
    function Harness(){
      current=useWorkspaceDocumentAuthoring({documentId:DOC_ID,surface:'build',kind:'worldbuilding_source'});
      return current.snapshot ? <MarkdownEditorCore documentKey={current.documentKey}
        content={current.editorContent as Content} onEditorChange={current.setEditor}
        onUpdate={current.handleEditorUpdate}/> : null;
    }
    render(<Harness/>);
    await waitFor(()=>expect(current.editor).not.toBeNull());
    await act(async()=>{await Promise.resolve();});
    const editor=current.editor!,element=editor.view.dom,key=current.documentKey;
    for(const text of [' The bell rings.',' Workers approach.']){
      act(()=>{editor.commands.setTextSelection(editor.state.doc.content.size-1);editor.commands.insertContent(text);});
      const position=editor.state.selection.from;
      await waitFor(()=>expect(current.dirty).toBe(true));
      await act(async()=>{await current.saveMarkdown();});
      expect(current.phase).toBe('ready_clean');
      expect(current.documentKey).toBe(key);expect(current.editor).toBe(editor);
      expect(editor.isDestroyed).toBe(false);expect(editor.view.dom).toBe(element);
      expect(editor.state.selection.from).toBe(position);
      expect(saved.markdown).toContain(text.trim());
    }
    act(()=>{editor.commands.undo();});
    await waitFor(()=>expect(current.dirty).toBe(true));
    expect(current.editor).toBe(editor);
    expect(commitTiptapMarkdownWrite).toHaveBeenCalledTimes(2);
  });
});
