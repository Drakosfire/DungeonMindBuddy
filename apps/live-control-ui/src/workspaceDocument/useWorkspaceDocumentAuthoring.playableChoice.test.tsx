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
import { indexPlayableStructure, indexPlayableStructureV2 } from "../tiptap/playable/playableStructureIndex";
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

function snapshot(args: {
  markdown: string;
  revision: number;
  contentSha: string;
  fingerprint: string;
  contentStatus?: "draft" | "committed";
}): WorkspaceDocumentSnapshot {
  return {
    schema_version: "dmb_workspace_document_snapshot_v1",
    record: fixtureWorkspaceDocumentRecord({
      document_id: DOC_ID,
      kind: "worldbuilding_source",
      campaign_id: "eldyrwild",
      target_session: null,
      revision: args.revision,
      content_status: args.contentStatus ?? "draft",
    }),
    markdown: args.markdown,
    content_sha256: args.contentSha,
    file_fingerprint: args.fingerprint,
    file_exists: true,
    loaded_revision: args.revision,
  };
}

const sourceSnapshot = snapshot({
  markdown: sourceMarkdown,
  revision: 1,
  contentSha: "sha-source",
  fingerprint: "fp-source",
  contentStatus: "draft",
});

const committedSnapshot = snapshot({
  markdown: renamedMarkdown,
  revision: 2,
  contentSha: "sha-committed",
  fingerprint: "fp-committed",
  contentStatus: "committed",
});

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
      .mockResolvedValueOnce(sourceSnapshot)
      .mockResolvedValue(committedSnapshot);
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
    expect(result.current.phase).toBe("ready_clean");
    expect(result.current.error).toBeNull();
    expect(result.current.lastCommitReceipt).toEqual(expect.objectContaining({
      committed_revision: 2,
      normalized_content_sha256: "sha-committed",
      file_fingerprint: "fp-committed",
    }));
    expect(result.current.snapshot).toEqual(expect.objectContaining({
      loaded_revision: 2,
      content_sha256: "sha-committed",
      file_fingerprint: "fp-committed",
      markdown: renamedMarkdown,
    }));

    await act(async () => {
      await result.current.reloadFromSnapshot();
    });
    await waitFor(() => expect(result.current.phase).toBe("ready_clean"));
    expect(result.current.snapshot?.loaded_revision).toBe(2);
    expect(result.current.snapshot?.content_sha256).toBe("sha-committed");
    expect(result.current.snapshot?.file_fingerprint).toBe("fp-committed");

    const index = indexPlayableStructure(result.current.editorContent);
    expect(index.status).toBe("ready");
    if (index.status !== "ready") throw new Error("expected ready");
    expect(index.index.choices).toEqual([
      { choiceId: "choice:route", sceneId: "scene:gate", order: 0, optionOrder: ["option:fire", "option:wait"] },
    ]);
    expect(index.index.elements).toEqual(expect.arrayContaining([
      { kind: "option", id: "option:fire", order: 2, sceneId: "scene:gate", choiceId: "choice:route" },
      { kind: "option", id: "option:wait", order: 3, sceneId: "scene:gate", choiceId: "choice:route" },
    ]));
  });

  it("blocks durable save when Choice identity is nested inside a callout", async () => {
    vi.mocked(getWorkspaceDocumentSnapshot).mockResolvedValue(snapshot({
      markdown: "# Safe source\n",
      revision: 1,
      contentSha: "sha-source",
      fingerprint: "fp-source",
    }));

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
// ---------------------------------------------------------------------------
// Beat-first (v2) committed-Runbook round trip
// ---------------------------------------------------------------------------

const v2SourceMarkdown = [
  "<!-- dmb-playable-element:v2 kind=beat id=beat:hold-the-gate beat_kind=spine -->",
  "## Hold the gate",
  "",
  "Triage at the gate line.",
  "",
  "<!-- dmb-playable-element:v2 kind=scene id=scene:gate-line -->",
  "### The gate line",
  "",
  "<!-- dmb-playable-element:v2 kind=choice id=choice:who-gets-through scene=scene:gate-line -->",
  "### Who gets through first?",
  "",
  "<!-- dmb-playable-element:v2 kind=option id=option:cure-line-first activates=beat:panic-breaks -->",
  "- Prioritize the cure line",
  "",
  "<!-- dmb-playable-element:v2 kind=option id=option:families-first suppresses=beat:meat-flank -->",
  "- Keep families together",
  "",
  "<!-- dmb-playable-element:v2 kind=beat id=beat:panic-breaks beat_kind=optional -->",
  "## Panic breaks",
  "",
  "<!-- dmb-playable-element:v2 kind=beat id=beat:meat-flank beat_kind=interrupt -->",
  "## Meat flank",
  "",
].join("\n");

const v2RenamedMarkdown = v2SourceMarkdown.replace(
  "## Hold the gate",
  "## Hold the gate renamed",
);

const v2SourceSnapshot = snapshot({
  markdown: v2SourceMarkdown,
  revision: 1,
  contentSha: "sha-v2-source",
  fingerprint: "fp-v2-source",
  contentStatus: "draft",
});

const v2CommittedSnapshot = snapshot({
  markdown: v2RenamedMarkdown,
  revision: 2,
  contentSha: "sha-v2-committed",
  fingerprint: "fp-v2-committed",
  contentStatus: "committed",
});

describe("workspace Save/reload for Beat-first (v2) structure", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
  });

  it("commits a renamed v2 Runbook while preserving Beat/Scene/Decision/Option identity and edges", async () => {
    vi.mocked(getWorkspaceDocumentSnapshot)
      .mockResolvedValueOnce(v2SourceSnapshot)
      .mockResolvedValue(v2CommittedSnapshot);
    vi.mocked(prepareTiptapMarkdownWrite).mockResolvedValue({
      schema_version: "dmb_tiptap_markdown_write_prepare_v1",
      document_id: DOC_ID,
      title: "Hold the gate",
      target_relpath: "corpus/gate.md",
      target_display_path: "corpus/gate.md",
      registry_revision: 1,
      file_exists: true,
      writer_ok: true,
      writer_phase: "prepare",
      writer_confirm_token: "confirm-token",
      writer_diff: "+Hold the gate renamed",
      warnings: [],
      diagnostics: [],
    });
    vi.mocked(commitTiptapMarkdownWrite).mockResolvedValue({
      schema_version: "dmb_tiptap_markdown_write_commit_v1",
      document_id: DOC_ID,
      title: "Hold the gate",
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
      normalized_content_sha256: "sha-v2-committed",
      writer_ok: true,
      bytes_written: v2RenamedMarkdown.length,
      file_fingerprint: "fp-v2-committed",
      diagnostics: [],
    });

    const imported = markdownToTiptapDoc(v2SourceMarkdown);
    expect(imported.diagnostics).toEqual([]);
    const renamedJson = {
      ...imported.doc,
      content: (imported.doc.content ?? []).map((node) => {
        if (node.type !== "heading") return node;
        const id = (node.attrs as { playableElementId?: string } | undefined)?.playableElementId;
        if (id === "beat:hold-the-gate") {
          return { ...node, content: [{ type: "text", text: "Hold the gate renamed" }] };
        }
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

    // The committed bytes carry every v2 marker, including Option list items
    // with their transition edges.
    expect(prepareTiptapMarkdownWrite).toHaveBeenCalledWith(expect.objectContaining({
      markdown: v2RenamedMarkdown,
    }));
    expect(commitTiptapMarkdownWrite).toHaveBeenCalledWith(expect.objectContaining({
      markdown: v2RenamedMarkdown,
    }));
    expect(result.current.phase).toBe("ready_clean");
    expect(result.current.error).toBeNull();

    await act(async () => {
      await result.current.reloadFromSnapshot();
    });
    await waitFor(() => expect(result.current.phase).toBe("ready_clean"));

    const index = indexPlayableStructureV2(result.current.editorContent);
    expect(index.status).toBe("ready");
    if (index.status !== "ready") throw new Error("expected ready");
    expect(index.index.beatOrder).toEqual([
      "beat:hold-the-gate",
      "beat:panic-breaks",
      "beat:meat-flank",
    ]);
    expect(index.index.beats.map((beat) => [beat.beatId, beat.beatKind])).toEqual([
      ["beat:hold-the-gate", "spine"],
      ["beat:panic-breaks", "optional"],
      ["beat:meat-flank", "interrupt"],
    ]);
    expect(index.index.scenes).toEqual([
      { sceneId: "scene:gate-line", beatId: "beat:hold-the-gate", order: 0 },
    ]);
    expect(index.index.choices).toEqual([
      {
        choiceId: "choice:who-gets-through",
        beatId: "beat:hold-the-gate",
        sceneId: "scene:gate-line",
        order: 0,
        optionOrder: ["option:cure-line-first", "option:families-first"],
      },
    ]);
    expect(index.index.options).toEqual([
      {
        optionId: "option:cure-line-first",
        choiceId: "choice:who-gets-through",
        order: 0,
        activates: ["beat:panic-breaks"],
        suppresses: [],
      },
      {
        optionId: "option:families-first",
        choiceId: "choice:who-gets-through",
        order: 1,
        activates: [],
        suppresses: ["beat:meat-flank"],
      },
    ]);
  });
});
