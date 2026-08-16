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
import { markdownToTiptapDoc } from "../tiptap/markdown/markdownToTiptap";
import { indexPlayableStructure } from "../tiptap/playable/playableStructureIndex";
import { useWorkspaceDocumentAuthoring } from "./useWorkspaceDocumentAuthoring";

vi.mock("../api/liveApi", () => ({
  getWorkspaceDocumentSnapshot: vi.fn(),
  prepareTiptapMarkdownWrite: vi.fn(),
  commitTiptapMarkdownWrite: vi.fn(),
}));

const DOC_ID = "11111111-1111-4111-8111-111111111111";

const sourceMarkdown = [
  "<!-- dmb-playable-element:v1 kind=scene id=scene:gate -->",
  "## The Gate",
  "",
  "<!-- dmb-playable-element:v1 kind=choice id=choice:route -->",
  "### Which route do they take?",
  "",
  "<!-- dmb-playable-element:v1 kind=option id=option:fire -->",
  "#### Burn through the growth",
  "",
  "<!-- dmb-playable-element:v1 kind=option id=option:wait -->",
  "#### Wait and watch",
  "",
].join("\n");

const renamedMarkdown = [
  "<!-- dmb-playable-element:v1 kind=scene id=scene:gate -->",
  "## The Gate",
  "",
  "<!-- dmb-playable-element:v1 kind=choice id=choice:route -->",
  "### Pick a path",
  "",
  "<!-- dmb-playable-element:v1 kind=option id=option:fire -->",
  "#### Burn it",
  "",
  "<!-- dmb-playable-element:v1 kind=option id=option:wait -->",
  "#### Wait and watch",
  "",
].join("\n");

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

describe("workspace Save/reload for Choice/Option identity", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
  });

  it("commits renamed Choice/Option labels while preserving exact IDs, then reloads them", async () => {
    vi.mocked(getWorkspaceDocumentSnapshot)
      .mockResolvedValueOnce(snapshot(sourceMarkdown))
      .mockResolvedValueOnce(snapshot(renamedMarkdown));
    vi.mocked(prepareTiptapMarkdownWrite).mockResolvedValue({
      schema_version: "dmb_tiptap_markdown_write_prepare_v1",
      document_id: DOC_ID,
      title: "The Gate",
      target_relpath: "corpus/gate.md",
      target_display_path: "corpus/gate.md",
      registry_revision: 1,
      file_exists: true,
      writer_ok: true,
      writer_phase: "prepare",
      writer_confirm_token: "confirm-token",
      writer_diff: "+Pick a path",
      warnings: [],
      diagnostics: [],
    });
    vi.mocked(commitTiptapMarkdownWrite).mockResolvedValue({
      schema_version: "dmb_tiptap_markdown_write_commit_v1",
      document_id: DOC_ID,
      title: "The Gate",
      target_relpath: "corpus/gate.md",
      target_display_path: "corpus/gate.md",
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
      bytes_written: renamedMarkdown.length,
      file_fingerprint: "fp-committed",
      diagnostics: [],
    });

    const imported = markdownToTiptapDoc(sourceMarkdown);
    expect(imported.diagnostics).toEqual([]);
    const renamedJson = {
      ...imported.doc,
      content: (imported.doc.content ?? []).map((node) => {
        if (node.type !== "heading") return node;
        const id = (node.attrs as { playableElementId?: string } | undefined)?.playableElementId;
        if (id === "choice:route") return { ...node, content: [{ type: "text", text: "Pick a path" }] };
        if (id === "option:fire") return { ...node, content: [{ type: "text", text: "Burn it" }] };
        return node;
      }),
    };

    const { result } = renderHook(() => useWorkspaceDocumentAuthoring({
      documentId: DOC_ID,
      surface: "build",
      kind: "worldbuilding_source",
    }));
    await waitFor(() => expect(result.current.phase).toBe("ready_clean"));

    act(() => {
      result.current.setEditor(editorWithJson(renamedJson));
      result.current.markDirty();
    });
    await act(async () => {
      await result.current.saveMarkdown();
    });

    expect(prepareTiptapMarkdownWrite).toHaveBeenCalledWith(expect.objectContaining({
      markdown: renamedMarkdown,
    }));
    expect(commitTiptapMarkdownWrite).toHaveBeenCalledWith(expect.objectContaining({
      markdown: renamedMarkdown,
    }));

    const reloaded = markdownToTiptapDoc(renamedMarkdown);
    expect(reloaded.diagnostics).toEqual([]);
    const index = indexPlayableStructure(reloaded.doc);
    expect(index.status).toBe("ready");
    if (index.status !== "ready") throw new Error("expected ready");
    expect(index.index.choices).toEqual([
      { choiceId: "choice:route", sceneId: "scene:gate", order: 0, optionOrder: ["option:fire", "option:wait"] },
    ]);
  });

  it("blocks durable save when Choice identity is nested inside a callout", async () => {
    vi.mocked(getWorkspaceDocumentSnapshot).mockResolvedValue(snapshot("# Safe source\n"));

    const { result } = renderHook(() => useWorkspaceDocumentAuthoring({
      documentId: DOC_ID,
      surface: "build",
      kind: "worldbuilding_source",
    }));
    await waitFor(() => expect(result.current.phase).toBe("ready_clean"));

    act(() => {
      result.current.setEditor(editorWithJson({
        type: "doc",
        content: [{
          type: "callout",
          attrs: { kind: "gm-note" },
          content: [{
            type: "heading",
            attrs: { level: 3, playableElementKind: "choice", playableElementId: "choice:route" },
            content: [{ type: "text", text: "Hidden" }],
          }],
        }],
      }));
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
});
