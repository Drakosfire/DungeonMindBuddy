import { Editor } from "@tiptap/core";
import StarterKit from "@tiptap/starter-kit";
import { describe, expect, it } from "vitest";

import { GraphNodeReferenceNode } from "../../tiptap/extensions/GraphNodeReferenceNode";
import {
  buildGraphAuthoringSelectionFromEditor,
  buildManualGraphAuthoringSelection,
  graphAuthoringSelectionsEqual,
  isManualGraphAuthoringSelection,
  MAX_AUTHORING_SELECTED_TEXT_LENGTH,
  normalizeAuthoringSelectedText,
} from "./graphAuthoringSelection";

const authoringContext = {
  campaignId: "longmont-c1",
  sessionId: "session-2",
  graphId: "graph-c1s2",
  laneRole: "live" as const,
  sourceArtifactPath: "artifacts/run/manifest.json",
};

function createAuthoringEditor(content: Parameters<Editor["commands"]["setContent"]>[0]) {
  const editor = new Editor({
    extensions: [StarterKit, GraphNodeReferenceNode],
    content,
    editable: false,
  });
  return editor;
}

describe("graphAuthoringSelection", () => {
  it("normalizes selected text whitespace", () => {
    expect(normalizeAuthoringSelectedText("  gang\n  members  ")).toBe("gang members");
  });

  it("builds a manual selection with no recap grounding and flags it as manual", () => {
    const selection = buildManualGraphAuthoringSelection({
      campaignId: "longmont-c1",
      sessionId: "session-2",
      graphId: "graph-c1s2",
      laneRole: "live",
    });

    expect(selection.selectedText).toBe("");
    expect(selection.sourceArtifactPath).toBeNull();
    expect(isManualGraphAuthoringSelection(selection)).toBe(true);
  });

  it("does not flag a recap-grounded selection as manual", () => {
    const selection = buildManualGraphAuthoringSelection({
      campaignId: "longmont-c1",
      sessionId: "session-2",
    });
    expect(isManualGraphAuthoringSelection({ ...selection, selectedText: "gang" })).toBe(false);
  });

  it("builds a text_span selection from ProseMirror text selection", () => {
    const editor = createAuthoringEditor({
      type: "doc",
      content: [
        {
          type: "paragraph",
          content: [{ type: "text", text: "The gang arrived at Stone Bridge." }],
        },
      ],
    });

    editor.commands.setTextSelection({ from: 5, to: 9 });

    const selection = buildGraphAuthoringSelectionFromEditor(editor, authoringContext);
    expect(selection).toMatchObject({
      selectionKind: "text_span",
      selectedText: "gang",
      normalizedSelectedText: "gang",
      campaignId: "longmont-c1",
      sessionId: "session-2",
      graphId: "graph-c1s2",
      laneRole: "live",
      paragraphOrdinal: 1,
      tiptapFrom: 5,
      tiptapTo: 9,
    });
    expect(selection?.surroundingTextBefore).toContain("The");
    expect(selection?.surroundingTextAfter).toContain("arrived");

    editor.destroy();
  });

  it("returns null for empty or whitespace-only selections", () => {
    const editor = createAuthoringEditor({
      type: "doc",
      content: [
        {
          type: "paragraph",
          content: [{ type: "text", text: "The gang arrived." }],
        },
      ],
    });

    editor.commands.setTextSelection({ from: 4, to: 4 });
    expect(buildGraphAuthoringSelectionFromEditor(editor, authoringContext)).toBeNull();

    editor.commands.setTextSelection({ from: 4, to: 5 });
    expect(buildGraphAuthoringSelectionFromEditor(editor, authoringContext)).toBeNull();

    editor.destroy();
  });

  it("returns null when selected text exceeds the configured bound", () => {
    const longText = "x".repeat(MAX_AUTHORING_SELECTED_TEXT_LENGTH + 1);
    const editor = createAuthoringEditor({
      type: "doc",
      content: [
        {
          type: "paragraph",
          content: [{ type: "text", text: longText }],
        },
      ],
    });

    editor.commands.setTextSelection({ from: 1, to: 1 + longText.length });
    expect(buildGraphAuthoringSelectionFromEditor(editor, authoringContext)).toBeNull();

    editor.destroy();
  });

  it("treats equivalent selections as unchanged", () => {
    const left = {
      campaignId: "longmont-c1",
      sessionId: "session-2",
      selectionKind: "text_span" as const,
      selectedText: "gang",
      normalizedSelectedText: "gang",
      tiptapFrom: 5,
      tiptapTo: 9,
    };
    const right = { ...left };
    expect(graphAuthoringSelectionsEqual(left, right)).toBe(true);
    expect(graphAuthoringSelectionsEqual(left, { ...left, selectedText: "gate" })).toBe(false);
  });

  it("builds a graph_node_reference selection when a graph chip atom is selected", () => {
    const editor = createAuthoringEditor({
      type: "doc",
      content: [
        {
          type: "paragraph",
          content: [
            { type: "text", text: "The party met " },
            {
              type: "graphNodeReference",
              attrs: { nodeId: "alden", label: "Alden" },
            },
            { type: "text", text: " at the gate." },
          ],
        },
      ],
    });

    const graphNodePos = (() => {
      let found: number | null = null;
      editor.state.doc.descendants((node, nodePos) => {
        if (node.type.name === "graphNodeReference") {
          found = nodePos;
          return false;
        }
        return true;
      });
      return found;
    })();
    expect(graphNodePos).not.toBeNull();
    editor.commands.setNodeSelection(graphNodePos!);

    const selection = buildGraphAuthoringSelectionFromEditor(editor, authoringContext);
    expect(selection).toMatchObject({
      selectionKind: "graph_node_reference",
      selectedText: "Alden",
      normalizedSelectedText: "Alden",
      existingNodeId: "alden",
      existingLabel: "Alden",
    });

    editor.destroy();
  });
});
