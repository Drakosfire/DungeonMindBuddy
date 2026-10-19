import { Editor } from "@tiptap/core";
import StarterKit from "@tiptap/starter-kit";
import { describe, expect, it, vi } from "vitest";

import { tiptapJsonToSemanticMarkdown } from "../markdown/calloutMarkdown";
import { markdownToTiptapDoc } from "../markdown/markdownToTiptap";
import { CalloutNode } from "./CalloutNode";

function createEditor(content: object) {
  const element = document.createElement("div");
  document.body.appendChild(element);
  const editor = new Editor({
    element,
    extensions: [StarterKit, CalloutNode],
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

function hasCallout(editor: Editor): boolean {
  let found = false;
  editor.state.doc.descendants((node) => {
    if (node.type.name === "callout") {
      found = true;
      return false;
    }
    return true;
  });
  return found;
}

describe("CalloutNode editing", () => {
  it("deletes a gm-note callout when backspacing inside an empty body", () => {
    const { editor, cleanup } = createEditor({
      type: "doc",
      content: [
        {
          type: "callout",
          attrs: { kind: "gm-note" },
          content: [{ type: "paragraph", content: [{ type: "text", text: "Scratch this." }] }],
        },
      ],
    });

    try {
      editor.commands.focus("end");
      while (editor.state.doc.textContent.length > 0) {
        editor.commands.deleteRange({
          from: editor.state.selection.from - 1,
          to: editor.state.selection.from,
        });
      }

      expect(hasCallout(editor)).toBe(true);
      expect(editor.commands.keyboardShortcut("Backspace")).toBe(true);
      expect(hasCallout(editor)).toBe(false);
    } finally {
      cleanup();
    }
  });

  it("removes a callout with deleteActiveBlock while the cursor is inside it", () => {
    const { editor, cleanup } = createEditor({
      type: "doc",
      content: [
        {
          type: "callout",
          attrs: { kind: "gm-note" },
          content: [{ type: "paragraph", content: [{ type: "text", text: "Keep triage focused." }] }],
        },
      ],
    });

    try {
      editor.commands.focus("end");
      expect(editor.commands.deleteActiveBlock()).toBe(true);
      expect(hasCallout(editor)).toBe(false);
      expect(editor.getText()).toBe("");
    } finally {
      cleanup();
    }
  });
});


it("folds an editable titled block without document updates, selection changes or undo loss", async () => {
  const source = "> [!RULES] Traveling\n> Three miles per hour.\n";
  const { editor, cleanup } = createEditor(markdownToTiptapDoc(source).doc);
  try {
    editor.commands.setTextSelection(3);
    editor.commands.insertContent("New ");
    const json = editor.getJSON();
    const markdown = tiptapJsonToSemanticMarkdown(json);
    const selection = editor.state.selection.toJSON();
    const updates = vi.fn();
    editor.on("update", updates);
    const details = editor.view.dom.querySelector("details")!;
    const summary = details.querySelector("summary")!;
    expect(summary.textContent).toBe("Rules: Traveling");
    summary.click();
    await new Promise(resolve => setTimeout(resolve, 0));
    expect(details.open).toBe(false);
    summary.click();
    await new Promise(resolve => setTimeout(resolve, 0));
    expect(details.open).toBe(true);
    expect(editor.getJSON()).toEqual(json);
    expect(tiptapJsonToSemanticMarkdown(editor.getJSON())).toBe(markdown);
    expect(editor.state.selection.toJSON()).toEqual(selection);
    expect(updates).not.toHaveBeenCalled();
    expect(editor.commands.undo()).toBe(true);
    expect(tiptapJsonToSemanticMarkdown(editor.getJSON())).toBe(source);
  } finally { cleanup(); }
});

it("round-trips titled callout HTML even when its local disclosure is closed", () => {
  const source = "> [!READ-ALOUD] North of Mireward Reach\n> The road loses its shoulders.\n";
  const first = createEditor(markdownToTiptapDoc(source).doc);
  try {
    const html = first.editor.getHTML().replace('open=""', "");
    const second = createEditor({ type: "doc", content: [] });
    try {
      second.editor.commands.setContent(html);
      expect(tiptapJsonToSemanticMarkdown(second.editor.getJSON())).toBe(source);
      expect(second.editor.getJSON()).toEqual(first.editor.getJSON());
    } finally { second.cleanup(); }
  } finally { first.cleanup(); }
});
