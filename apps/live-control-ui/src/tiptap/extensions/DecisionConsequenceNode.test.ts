import { Editor } from "@tiptap/core";
import StarterKit from "@tiptap/starter-kit";
import { describe, expect, it } from "vitest";

import { CalloutNode } from "./CalloutNode";
import { DECISION_CONSEQUENCE_EXTENSIONS } from "./DecisionConsequenceNode";

function createEditor(content: object) {
  const element = document.createElement("div");
  document.body.appendChild(element);
  const editor = new Editor({
    element,
    extensions: [StarterKit, CalloutNode, ...DECISION_CONSEQUENCE_EXTENSIONS],
    content,
  });
  return {
    editor,
    cleanup: () => {
      editor.destroy();
      element.remove();
    },
  };
}

describe("DecisionConsequenceNode", () => {
  it("inserts a paired Decision / Consequence block", () => {
    const { editor, cleanup } = createEditor({ type: "doc", content: [{ type: "paragraph" }] });
    expect(editor.commands.insertDecisionConsequence()).toBe(true);
    const html = editor.getHTML();
    expect(html).toContain('data-md-decision-consequence="true"');
    expect(html).toContain("md-dc-pane-decision");
    expect(html).toContain("md-dc-pane-consequence");
    expect(html).toContain("Decision");
    expect(html).toContain("Consequence");
    cleanup();
  });

  it("inserts exactly two ordered panes in TipTap JSON", () => {
    const { editor, cleanup } = createEditor({ type: "doc", content: [{ type: "paragraph" }] });
    expect(editor.commands.insertDecisionConsequence()).toBe(true);

    const json = editor.getJSON();
    const pair = json.content?.find((node) => node.type === "decisionConsequence");
    expect(pair).toBeDefined();
    expect(pair?.content).toHaveLength(2);
    expect(pair?.content?.[0]).toMatchObject({ type: "decisionPane" });
    expect(pair?.content?.[1]).toMatchObject({ type: "consequencePane" });

    cleanup();
  });

  it("removes the whole pair via deleteParentDecisionConsequence", () => {
    const { editor, cleanup } = createEditor({
      type: "doc",
      content: [
        {
          type: "decisionConsequence",
          content: [
            { type: "decisionPane", content: [{ type: "paragraph", content: [{ type: "text", text: "A" }] }] },
            { type: "consequencePane", content: [{ type: "paragraph", content: [{ type: "text", text: "B" }] }] },
          ],
        },
      ],
    });
    editor.commands.setTextSelection(4);
    expect(editor.commands.deleteParentDecisionConsequence()).toBe(true);
    expect(editor.getHTML()).not.toContain("md-decision-consequence");
    cleanup();
  });
});
