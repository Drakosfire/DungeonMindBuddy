import { Editor } from "@tiptap/core";
import StarterKit from "@tiptap/starter-kit";
import { describe, expect, it } from "vitest";

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
