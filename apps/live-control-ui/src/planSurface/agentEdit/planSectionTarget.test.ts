import { Editor, type JSONContent } from "@tiptap/core";
import { describe, expect, it } from "vitest";

import { DEFAULT_MARKDOWN_EDITOR_EXTENSIONS } from "../../tiptap/MarkdownEditorCore";
import { planSectionTargetForSelection, planSectionTargets, type PlanSectionTarget } from "./planSectionTarget";

function editorWith(content: JSONContent[]): Editor {
  return new Editor({
    extensions: DEFAULT_MARKDOWN_EDITOR_EXTENSIONS,
    content: { type: "doc", content },
  });
}

function heading(level: number, text: string): JSONContent {
  return { type: "heading", attrs: { level }, content: [{ type: "text", text }] };
}

function paragraph(text: string): JSONContent {
  return { type: "paragraph", content: [{ type: "text", text }] };
}

describe("Plan heading section targets", () => {
  it("bounds a heading at the next same-or-higher root heading and keeps child headings with their parent", () => {
    const editor = editorWith([
      paragraph("Preamble stays outside the section list."),
      heading(2, "The Siege"),
      paragraph("Beat prose."),
      heading(3, "Outer Scene"),
      paragraph("Scene one."),
      {
        type: "blockquote",
        content: [heading(2, "Quoted heading"), paragraph("Quoted detail.")],
      },
      heading(4, "Subscene"),
      paragraph("Nested scene detail."),
      heading(3, "Outer Scene"),
      paragraph("Scene two."),
      heading(2, "Next Beat"),
      paragraph("Next beat prose."),
    ]);

    try {
      const targets = planSectionTargets(editor);
      expect(targets.map((target) => target.heading)).toEqual([
        "The Siege",
        "Outer Scene",
        "Subscene",
        "Outer Scene",
        "Next Beat",
      ]);

      const beat = targets[0]!;
      const firstScene = targets[1]!;
      const subscene = targets[2]!;
      const secondScene = targets[3]!;
      const textIn = (target: PlanSectionTarget) => editor.state.doc.textBetween(target.from, target.to, "\n");
      expect(textIn(beat)).toContain("Scene one.");
      expect(textIn(beat)).toContain("Nested scene detail.");
      expect(textIn(beat)).not.toContain("Next Beat");
      expect(textIn(firstScene)).toContain("Quoted heading");
      expect(textIn(firstScene)).toContain("Subscene");
      expect(textIn(firstScene)).not.toContain("Scene two.");
      expect(textIn(subscene)).not.toContain("Scene two.");
      expect(textIn(secondScene)).toContain("Scene two.");
      expect(textIn(secondScene)).not.toContain("Next Beat");

      expect(targets[1].id).not.toBe(targets[3].id);
      expect(targets[1].label).toBe("### Outer Scene · 1 of 2");
      expect(targets[3].label).toBe("### Outer Scene · 2 of 2");
      expect(textIn(beat)).not.toContain("Preamble stays outside");
      expect(beat.rootNodeStart).toBe(1);
      expect(beat.rootNodeEnd).toBe(10);
      expect(planSectionTargetForSelection(editor, beat.from, beat.to)?.id).toBe(beat.id);
      expect(planSectionTargetForSelection(editor, beat.from, beat.to - 1)).toBeNull();
    } finally {
      editor.destroy();
    }
  });

  it("returns no section targets for an empty, preamble-only, or unnamed-heading document", () => {
    const empty = new Editor({ extensions: DEFAULT_MARKDOWN_EDITOR_EXTENSIONS, content: { type: "doc", content: [] } });
    const preamble = editorWith([paragraph("Preamble text without headings.")]);
    const unnamed = editorWith([{ type: "heading", attrs: { level: 2 } }, paragraph("Text after unnamed heading.")]);

    try {
      expect(planSectionTargets(empty)).toEqual([]);
      expect(planSectionTargets(preamble)).toEqual([]);
      expect(planSectionTargets(unnamed)).toEqual([]);
    } finally {
      empty.destroy();
      preamble.destroy();
      unnamed.destroy();
    }
  });
});
