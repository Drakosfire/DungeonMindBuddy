import { describe, expect, it } from "vitest";

import {
  applyCanvasBlockProposal,
  canvasBlockProposalsFromMutations,
  isCanvasBlockProposal,
} from "./canvasBlockProposal";

describe("canvasBlockProposal", () => {
  it("filters mutations to typed canvas proposals", () => {
    const proposals = canvasBlockProposalsFromMutations([
      { schema: "other" },
      {
        schema: "dmb_canvas_block_proposal_v1",
        documentId: "doc-1",
        surfaceId: "plan",
        op: "insert_callout",
        kind: "gm-note",
        body: "Metal leaves.",
        locator: { afterHeading: "Area 5: The Grotesque Tree" },
        previewMarkdown: "> [!GM-NOTE]\n> Metal leaves.",
        expectedContentSha256: "abc",
        provenanceRefs: [],
      },
    ]);
    expect(proposals).toHaveLength(1);
    expect(isCanvasBlockProposal(proposals[0])).toBe(true);
    expect(proposals[0]?.kind).toBe("gm-note");
  });

  it("refuses apply when document id mismatches", () => {
    const editor = {
      state: { doc: { descendants: () => undefined } },
      chain: () => ({
        focus: () => ({
          insertContent: () => ({ run: () => true }),
          insertContentAt: () => ({ run: () => true }),
          command: () => ({ run: () => true }),
        }),
      }),
      schema: { nodeFromJSON: (n: unknown) => n },
      getJSON: () => ({ type: "doc", content: [] }),
    } as never;

    const result = applyCanvasBlockProposal(
      editor,
      {
        schema: "dmb_canvas_block_proposal_v1",
        documentId: "doc-a",
        surfaceId: "plan",
        op: "insert_callout",
        kind: "gm-note",
        body: "Metal leaves.",
        locator: { afterHeading: "Area 5" },
        previewMarkdown: "> [!GM-NOTE]\n> Metal leaves.",
        expectedContentSha256: "sha-1",
      },
      { documentId: "doc-b", currentContentSha256: "sha-1" },
    );
    expect(result.ok).toBe(false);
  });

  it("refuses apply when expected sha mismatches admission CAS", () => {
    const editor = {
      state: { doc: { descendants: () => undefined } },
      chain: () => ({
        focus: () => ({
          insertContent: () => ({ run: () => true }),
          insertContentAt: () => ({ run: () => true }),
          command: () => ({ run: () => true }),
        }),
      }),
      schema: { nodeFromJSON: (n: unknown) => n },
      getJSON: () => ({ type: "doc", content: [] }),
    } as never;

    const result = applyCanvasBlockProposal(
      editor,
      {
        schema: "dmb_canvas_block_proposal_v1",
        documentId: "doc-1",
        surfaceId: "plan",
        op: "insert_callout",
        kind: "gm-note",
        body: "Metal leaves.",
        locator: { afterHeading: "Area 5" },
        previewMarkdown: "> [!GM-NOTE]\n> Metal leaves.",
        expectedContentSha256: "sha-old",
      },
      { documentId: "doc-1", currentContentSha256: "sha-new", isDirty: false },
    );
    expect(result).toEqual({
      ok: false,
      reason: "Document changed since Hermes read it. Re-ask after Save or Reload.",
    });
  });

  it("refuses apply when editor is dirty even if base sha matches", () => {
    const editor = {
      state: { doc: { descendants: () => undefined } },
      chain: () => ({
        focus: () => ({
          insertContent: () => ({ run: () => true }),
          insertContentAt: () => ({ run: () => true }),
          command: () => ({ run: () => true }),
        }),
      }),
      schema: { nodeFromJSON: (n: unknown) => n },
      getJSON: () => ({ type: "doc", content: [] }),
    } as never;

    const result = applyCanvasBlockProposal(
      editor,
      {
        schema: "dmb_canvas_block_proposal_v1",
        documentId: "doc-1",
        surfaceId: "plan",
        op: "insert_callout",
        kind: "gm-note",
        body: "Metal leaves.",
        locator: { afterHeading: "Area 5" },
        previewMarkdown: "> [!GM-NOTE]\n> Metal leaves.",
        expectedContentSha256: "sha-1",
      },
      { documentId: "doc-1", currentContentSha256: "sha-1", isDirty: true },
    );
    expect(result).toEqual({
      ok: false,
      reason: "Document has unsaved local edits. Save or Reload, then re-ask Hermes.",
    });
  });
});
