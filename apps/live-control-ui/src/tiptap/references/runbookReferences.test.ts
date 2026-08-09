import { describe, expect, it } from "vitest";

import { tiptapJsonToSemanticMarkdown } from "../markdown/calloutMarkdown";
import { markdownToTiptapDoc } from "../markdown/markdownToTiptap";
import {
  healRunbookReferenceLabel,
  hydratePersistedRunbookReferenceAttrs,
  migratePersistedTiptapReferenceLabels,
  normalizeRunbookReferenceAttrs,
  normalizeSemanticReferenceLabel,
} from "./runbookReferences";

describe("healRunbookReferenceLabel", () => {
  it("unescapes markdown emphasis wrappers into a plain chip label", () => {
    expect(healRunbookReferenceLabel("\\*\\*Meat Mind\\*\\*")).toBe("Meat Mind");
  });

  it("collapses runaway backslash doubling from save/load cycles", () => {
    const runaway = "\\\\\\\\\\\\*\\\\\\\\\\\\*Meat Mind\\\\\\\\\\\\*\\\\\\\\\\\\*";
    expect(healRunbookReferenceLabel(runaway)).toBe("Meat Mind");
  });
});

describe("normalizeSemanticReferenceLabel", () => {
  it("trims without stripping literal emphasis characters", () => {
    expect(normalizeSemanticReferenceLabel("  **Meat Mind**  ")).toBe("**Meat Mind**");
    expect(normalizeSemanticReferenceLabel("  __Meat Mind__  ")).toBe("__Meat Mind__");
  });
});

describe("normalizeRunbookReferenceAttrs", () => {
  it("preserves parser-derived literal emphasis characters by default", () => {
    const attrs = normalizeRunbookReferenceAttrs({
      kind: "ref",
      refType: "graph-node",
      refId: "threat:authored:d60f9863b0faf7f586d69182a0882f1f",
      label: "**Meat Mind**",
    });
    expect(attrs.label).toBe("**Meat Mind**");
  });

  it("still heals escaped labels when labelSource is legacy", () => {
    const attrs = normalizeRunbookReferenceAttrs(
      {
        kind: "ref",
        refType: "graph-node",
        refId: "threat:authored:d60f9863b0faf7f586d69182a0882f1f",
        label: "\\*\\*Meat Mind\\*\\*",
      },
      { labelSource: "legacy" },
    );
    expect(attrs.label).toBe("Meat Mind");
  });
});

describe("persisted TipTap reference label hydration", () => {
  const threatId = "threat:authored:d60f9863b0faf7f586d69182a0882f1f";

  it("heals legacy escaped labels from old persisted TipTap JSON exactly once", () => {
    const oldPersistedDoc = {
      type: "doc",
      content: [
        {
          type: "paragraph",
          content: [
            {
              type: "runbookReference",
              attrs: {
                kind: "ref",
                refType: "graph-node",
                refId: threatId,
                label: "\\*\\*Meat Mind\\*\\*",
              },
            },
            { type: "text", text: " and " },
            {
              type: "graphNodeReference",
              attrs: {
                nodeId: "threat:meat-mind",
                label: "\\*\\*Meat Mind\\*\\*",
              },
            },
          ],
        },
      ],
    };

    const hydrated = migratePersistedTiptapReferenceLabels(oldPersistedDoc);
    const paragraph = hydrated.content[0];
    expect(paragraph.content[0].attrs.label).toBe("Meat Mind");
    expect(paragraph.content[2].attrs.label).toBe("Meat Mind");

    // Display/serialize path also heals unmigrated attrs once.
    expect(
      hydratePersistedRunbookReferenceAttrs(oldPersistedDoc.content[0].content[0].attrs).label,
    ).toBe("Meat Mind");

    const exported = tiptapJsonToSemanticMarkdown(hydrated);
    expect(exported).toContain(`[Meat Mind](#dmb-ref:graph-node:${threatId})`);
    expect(exported).toContain("[Meat Mind](dmb-node:threat:meat-mind)");
    expect(exported).not.toContain("\\*");

    // Stable: serializing hydrated attrs does not re-introduce escapes.
    expect(tiptapJsonToSemanticMarkdown(hydrated)).toBe(exported);
    // And serializing the *unmigrated* persisted JSON once yields the same clean Markdown.
    expect(tiptapJsonToSemanticMarkdown(oldPersistedDoc)).toBe(exported);

    const reimported = markdownToTiptapDoc(exported);
    expect(reimported.diagnostics).toEqual([]);
    const reimportedParagraph = reimported.doc.content?.[0] as {
      content?: Array<{ type?: string; attrs?: { label?: string } }>;
    };
    expect(reimportedParagraph.content?.find((n) => n.type === "runbookReference")?.attrs?.label).toBe(
      "Meat Mind",
    );
    expect(
      reimportedParagraph.content?.find((n) => n.type === "graphNodeReference")?.attrs?.label,
    ).toBe("Meat Mind");
  });

  it("does not strip fresh semantic labels that intentionally contain literal ** / __", () => {
    const semanticDoc = {
      type: "doc",
      content: [
        {
          type: "paragraph",
          content: [
            {
              type: "runbookReference",
              attrs: {
                kind: "ref",
                refType: "npc",
                refId: "lysandro-ironveil",
                label: "**Lysandro**",
              },
            },
            { type: "text", text: " / " },
            {
              type: "graphNodeReference",
              attrs: {
                nodeId: "threat:meat-mind",
                label: "__Meat Mind__",
              },
            },
          ],
        },
      ],
    };

    const migrated = migratePersistedTiptapReferenceLabels(semanticDoc);
    expect(migrated.content[0].content[0].attrs.label).toBe("**Lysandro**");
    expect(migrated.content[0].content[2].attrs.label).toBe("__Meat Mind__");

    const exported = tiptapJsonToSemanticMarkdown(migrated);
    expect(exported).toContain(String.raw`[\*\*Lysandro\*\*](#dmb-ref:npc:lysandro-ironveil)`);
    expect(exported).toContain(String.raw`[\_\_Meat Mind\_\_](dmb-node:threat:meat-mind)`);
    expect(exported).not.toContain("[Lysandro](#dmb-ref:npc:lysandro-ironveil)");
    expect(exported).not.toContain("[Meat Mind](dmb-node:threat:meat-mind)");

    const reimported = markdownToTiptapDoc(exported);
    expect(reimported.diagnostics).toEqual([]);
    expect(reimported.doc).toEqual(migrated);
  });
});
