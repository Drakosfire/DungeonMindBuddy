import { Editor } from "@tiptap/core";
import StarterKit from "@tiptap/starter-kit";
import { describe, expect, it } from "vitest";

import { CalloutNode } from "./CalloutNode";
import { DECISION_CONSEQUENCE_EXTENSIONS } from "./DecisionConsequenceNode";
import { looksLikeSemanticMarkdown, SemanticMarkdownPaste } from "./SemanticMarkdownPaste";
import { markdownToTiptapDoc } from "../markdown/markdownToTiptap";

function createPasteEditor() {
  const element = document.createElement("div");
  document.body.appendChild(element);
  const editor = new Editor({
    element,
    extensions: [StarterKit, CalloutNode, ...DECISION_CONSEQUENCE_EXTENSIONS, SemanticMarkdownPaste],
    content: { type: "doc", content: [{ type: "paragraph" }] },
  });
  return {
    editor,
    cleanup: () => {
      editor.destroy();
      element.remove();
    },
  };
}

function simulatePaste(editor: Editor, payload: { text?: string; html?: string }): boolean {
  const event = {
    clipboardData: {
      getData: (type: string) => {
        if (type === "text/plain") return payload.text ?? "";
        if (type === "text/html") return payload.html ?? "";
        return "";
      },
    },
  } as ClipboardEvent;
  let handled = false;
  editor.view.someProp("handlePaste", (handler) => {
    if (handler(editor.view, event)) {
      handled = true;
    }
    return handled;
  });
  return handled;
}

describe("looksLikeSemanticMarkdown", () => {
  it("detects headings and callouts via importer projection", () => {
    expect(looksLikeSemanticMarkdown("# Title\n\nBody")).toBe(true);
    expect(looksLikeSemanticMarkdown("> [!GM-NOTE]\n> Note")).toBe(true);
  });

  it("rejects frontmatter envelopes (importer strips YAML → would be partial conversion)", () => {
    expect(
      looksLikeSemanticMarkdown(['---', 'title: "x"', "---", "", "# Body"].join("\n")),
    ).toBe(false);
  });

  it("rejects plain prose and paragraph-only markdown", () => {
    expect(looksLikeSemanticMarkdown("Just a sentence about the wall.")).toBe(false);
    expect(looksLikeSemanticMarkdown("")).toBe(false);
    expect(looksLikeSemanticMarkdown("A lone paragraph with **bold** and _italic_.")).toBe(false);
  });
});

describe("SemanticMarkdownPaste", () => {
  it("inserts supported semantic Markdown when import diagnostics are clean", () => {
    const markdown = [
      "> [!DECISION-CONSEQUENCE]",
      "> ### Decision",
      "> Hold the line",
      ">",
      "> ### Consequence",
      "> Escalation",
      "",
    ].join("\n");
    const { editor, cleanup } = createPasteEditor();
    const handled = simulatePaste(editor, { text: markdown });
    expect(handled).toBe(true);
    expect(editor.getHTML()).toContain("md-decision-consequence");
    cleanup();
  });

  it("does not partially convert mixed semantic Markdown with unsupported links", () => {
    const markdown = [
      "## Prep",
      "",
      "- Decision forks",
      "  - > [!DECISION-CONSEQUENCE]",
      "    > ### Decision",
      "    > Hold the line",
      "    >",
      "    > ### Consequence",
      "    > - Consequence beat",
      "    > - Next pressure",
      "",
      "See [rules](https://example.com/rules).",
      "",
    ].join("\n");
    expect(markdownToTiptapDoc(markdown).diagnostics.some((d) => d.level === "warning")).toBe(true);

    const { editor, cleanup } = createPasteEditor();
    const before = editor.getJSON();
    const handled = simulatePaste(editor, { text: markdown });
    expect(handled).toBe(false);
    expect(editor.getJSON()).toEqual(before);
    expect(editor.getHTML()).not.toContain("md-decision-consequence");
    cleanup();
  });

  it("defers to rich HTML paste when ProseMirror HTML is present", () => {
    const { editor, cleanup } = createPasteEditor();
    const before = editor.getJSON();
    const handled = simulatePaste(editor, {
      text: "> [!DECISION-CONSEQUENCE]\n> ### Decision\n> A\n>\n> ### Consequence\n> B\n",
      html: '<meta charset="utf-8"><div data-md-decision-consequence="true">rich</div>',
    });
    expect(handled).toBe(false);
    expect(editor.getJSON()).toEqual(before);
    cleanup();
  });

  it("does not intercept plain prose", () => {
    const { editor, cleanup } = createPasteEditor();
    const handled = simulatePaste(editor, { text: "Just a sentence with _underscores_ and [ brackets." });
    expect(handled).toBe(false);
    cleanup();
  });

  it("does not hijack paragraph-only markdown", () => {
    const markdown = "A lone paragraph with **bold** and _italic_.";
    expect(looksLikeSemanticMarkdown(markdown)).toBe(false);
    const { editor, cleanup } = createPasteEditor();
    const before = editor.getJSON();
    const handled = simulatePaste(editor, { text: markdown });
    expect(handled).toBe(false);
    expect(editor.getJSON()).toEqual(before);
    cleanup();
  });

  it("does not partially convert a frontmatter document by inserting only the body", () => {
    const markdown = ['---', 'title: "Session 26 Prep"', "---", "", "# Body", "", "Hold the wall."].join("\n");
    const { editor, cleanup } = createPasteEditor();
    const before = editor.getJSON();
    const handled = simulatePaste(editor, { text: markdown });
    expect(handled).toBe(false);
    expect(editor.getJSON()).toEqual(before);
    expect(editor.getText()).not.toContain("Hold the wall.");
    cleanup();
  });
});
