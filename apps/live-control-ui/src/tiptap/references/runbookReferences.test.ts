import { describe, expect, it } from "vitest";

import { tiptapJsonToSemanticMarkdown } from "../markdown/calloutMarkdown";
import { markdownToTiptapDoc } from "../markdown/markdownToTiptap";
import {
  healRunbookReferenceLabel,
  migrateLegacyTiptapReferenceLabels,
  normalizeRunbookReferenceAttrs,
  normalizeSemanticReferenceLabel,
} from "./runbookReferences";
import {
  readWorkspaceDocumentLocalState,
  WORKSPACE_DOCUMENT_LOCAL_STATE_SCHEMA,
  workspaceDocumentStorageKey,
  writeWorkspaceDocumentLocalState,
} from "../state/tiptapLocalState";

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

  it("preserves semantic labels with literal backslash-punctuation sequences", () => {
    const attrs = normalizeRunbookReferenceAttrs({
      kind: "ref",
      refType: "npc",
      refId: "path-ward",
      label: String.raw`C:\*ward`,
    });
    expect(attrs.label).toBe(String.raw`C:\*ward`);
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

describe("versioned persisted TipTap reference label migration", () => {
  const threatId = "threat:authored:d60f9863b0faf7f586d69182a0882f1f";
  const documentId = "11111111-1111-4111-8111-111111111111";

  it("heals legacy escaped labels once when reading pre-v5 local state", () => {
    const legacyTiptapJson = {
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

    // Direct migration helper (schema-version gate calls this).
    const migratedDoc = migrateLegacyTiptapReferenceLabels(legacyTiptapJson);
    expect(migratedDoc.content[0].content[0].attrs.label).toBe("Meat Mind");
    expect(migratedDoc.content[0].content[2].attrs.label).toBe("Meat Mind");

    const storage = new Map<string, string>();
    const memoryStorage: Pick<Storage, "getItem" | "setItem"> = {
      getItem: (key) => storage.get(key) ?? null,
      setItem: (key, value) => {
        storage.set(key, value);
      },
    };

    // Persist as v4 (pre-semantic-label schema) and read through the versioned gate.
    memoryStorage.setItem(
      workspaceDocumentStorageKey(documentId),
      JSON.stringify({
        schema_version: "dmb_workspace_document_local_state_v4",
        document_id: documentId,
        title: "Legacy labels",
        campaign_id: "longmont-c2",
        kind: "plan",
        target_session: 1,
        surface: "plan",
        base_revision: 1,
        base_content_sha256: "abc",
        tiptap_json: legacyTiptapJson,
        exported_markdown: "placeholder",
        exported_markdown_authoritative: true,
        dirty: true,
        created_at: "2026-08-09T00:00:00.000Z",
        updated_at: "2026-08-09T00:00:00.000Z",
        last_local_save_at: "2026-08-09T00:00:00.000Z",
      }),
    );

    const restored = readWorkspaceDocumentLocalState(memoryStorage, documentId);
    expect(restored?.schema_version).toBe(WORKSPACE_DOCUMENT_LOCAL_STATE_SCHEMA);
    const paragraph = (restored?.tiptap_json as typeof legacyTiptapJson).content[0];
    expect(paragraph.content[0].attrs.label).toBe("Meat Mind");
    expect(paragraph.content[2].attrs.label).toBe("Meat Mind");

    const exported = tiptapJsonToSemanticMarkdown(restored!.tiptap_json);
    expect(exported).toContain(`[Meat Mind](#dmb-ref:graph-node:${threatId})`);
    expect(exported).toContain("[Meat Mind](dmb-node:threat:meat-mind)");
    expect(exported).not.toContain("\\*");
    expect(tiptapJsonToSemanticMarkdown(restored!.tiptap_json)).toBe(exported);

    const reimported = markdownToTiptapDoc(exported);
    expect(reimported.diagnostics).toEqual([]);
  });

  it("does not heal semantic labels on render/serialize after v5 provenance", () => {
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
                refId: "path-ward",
                label: String.raw`C:\*ward`,
              },
            },
            { type: "text", text: " / " },
            {
              type: "graphNodeReference",
              attrs: {
                nodeId: "threat:meat-mind",
                label: "**Meat Mind**",
              },
            },
          ],
        },
      ],
    };

    // Serialize must treat in-memory attrs as semantic — no character heuristic.
    const exported = tiptapJsonToSemanticMarkdown(semanticDoc);
    expect(exported).toContain("dmb-ref:npc:path-ward");
    expect(exported).toContain("dmb-node:threat:meat-mind");
    // Literal backslash before * must survive as escaped Markdown, not be healed away.
    expect(exported).toContain("C:\\\\\\*ward");
    expect(exported).toContain(String.raw`[\*\*Meat Mind\*\*](dmb-node:threat:meat-mind)`);
    expect(exported).not.toContain("[C:*ward]");
    expect(exported).not.toContain("[Meat Mind](dmb-node:threat:meat-mind)");

    const storage = new Map<string, string>();
    const memoryStorage: Pick<Storage, "getItem" | "setItem"> = {
      getItem: (key) => storage.get(key) ?? null,
      setItem: (key, value) => {
        storage.set(key, value);
      },
    };

    writeWorkspaceDocumentLocalState(memoryStorage, {
      schema_version: WORKSPACE_DOCUMENT_LOCAL_STATE_SCHEMA,
      document_id: documentId,
      title: "Semantic labels",
      campaign_id: "longmont-c2",
      kind: "plan",
      target_session: 1,
      surface: "plan",
      base_revision: 1,
      base_content_sha256: "abc",
      tiptap_json: semanticDoc,
      exported_markdown: exported,
      exported_markdown_authoritative: true,
      dirty: true,
      created_at: "2026-08-09T00:00:00.000Z",
      updated_at: "2026-08-09T00:00:00.000Z",
      last_local_save_at: "2026-08-09T00:00:00.000Z",
    });

    const restored = readWorkspaceDocumentLocalState(memoryStorage, documentId);
    expect(restored?.schema_version).toBe(WORKSPACE_DOCUMENT_LOCAL_STATE_SCHEMA);
    const paragraph = (restored?.tiptap_json as typeof semanticDoc).content[0];
    expect(paragraph.content[0].attrs.label).toBe(String.raw`C:\*ward`);
    expect(paragraph.content[2].attrs.label).toBe("**Meat Mind**");
    expect(tiptapJsonToSemanticMarkdown(restored!.tiptap_json)).toBe(exported);
  });
});
