import { Editor } from "@tiptap/core";
import StarterKit from "@tiptap/starter-kit";
import { describe, expect, it } from "vitest";

import { CalloutNode } from "./CalloutNode";
import { DECISION_CONSEQUENCE_EXTENSIONS } from "./DecisionConsequenceNode";
import { tiptapJsonToSemanticMarkdown } from "../markdown/calloutMarkdown";
import { markdownToTiptapDoc } from "../markdown/markdownToTiptap";

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

  it("round-trips through semantic Markdown", () => {
    const markdown = [
      "> [!DECISION-CONSEQUENCE]",
      "> ### Decision",
      "> If they push west along the wall.",
      ">",
      "> ### Consequence",
      "> Dark shapes answer from below.",
      "",
    ].join("\n");

    const { doc } = markdownToTiptapDoc(markdown);
    expect(doc.content?.[0]).toMatchObject({ type: "decisionConsequence" });

    const exported = tiptapJsonToSemanticMarkdown(doc);
    expect(exported).toContain("[!DECISION-CONSEQUENCE]");
    expect(exported).toContain("### Decision");
    expect(exported).toContain("If they push west along the wall.");
    expect(exported).toContain("### Consequence");
    expect(exported).toContain("Dark shapes answer from below.");

    const { editor, cleanup } = createEditor(doc);
    expect(editor.getHTML()).toContain("md-dc-pane-decision");
    expect(editor.getHTML()).toContain("push west");
    expect(editor.getHTML()).toContain("Dark shapes");
    cleanup();
  });

  it("removes the whole pair via deleteActiveBlock", () => {
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
    expect(editor.commands.deleteActiveBlock()).toBe(true);
    expect(editor.getHTML()).not.toContain("md-decision-consequence");
    cleanup();
  });
});
