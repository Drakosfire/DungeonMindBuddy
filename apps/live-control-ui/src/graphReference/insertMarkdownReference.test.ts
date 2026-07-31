import { describe, expect, it, vi } from "vitest";

import { insertMarkdownReference } from "./insertMarkdownReference";

describe("insertMarkdownReference", () => {
  it("inserts a runbook reference through the editor chain", () => {
    const run = vi.fn();
    const chain = {
      focus: vi.fn().mockReturnThis(),
      insertRunbookReference: vi.fn().mockReturnThis(),
      run,
    };
    const editor = {
      chain: vi.fn(() => chain),
    };

    const attrs = {
      kind: "ref" as const,
      refType: "graph-node",
      refId: "npc-glowkindle",
      label: "Glowkindle",
    };

    expect(insertMarkdownReference(editor as never, attrs)).toBe(true);
    expect(editor.chain).toHaveBeenCalled();
    expect(chain.focus).toHaveBeenCalled();
    expect(chain.insertRunbookReference).toHaveBeenCalledWith(attrs);
    expect(run).toHaveBeenCalled();
  });

  it("returns false when editor is absent", () => {
    expect(
      insertMarkdownReference(null, {
        kind: "ref",
        refType: "npc",
        refId: "missing",
        label: "Missing",
      }),
    ).toBe(false);
  });
});
