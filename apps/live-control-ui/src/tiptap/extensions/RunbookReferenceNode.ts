import { mergeAttributes, Node } from "@tiptap/core";

import {
  normalizeRunbookReferenceAttrs,
  runbookReferenceClasses,
  type RunbookReferenceAttrs,
} from "../references/runbookReferences";

declare module "@tiptap/core" {
  interface Commands<ReturnType> {
    runbookReference: {
      insertRunbookReference: (attrs: Partial<RunbookReferenceAttrs>) => ReturnType;
    };
  }
}

export const RunbookReferenceNode = Node.create({
  name: "runbookReference",
  group: "inline",
  inline: true,
  atom: true,
  selectable: true,

  addAttributes() {
    return {
      kind: { default: "ref" },
      refType: { default: "npc" },
      refId: { default: "" },
      label: { default: "" },
    };
  },

  renderHTML({ node, HTMLAttributes }) {
    const attrs = normalizeRunbookReferenceAttrs(node.attrs);
    return [
      "span",
      mergeAttributes(HTMLAttributes, {
        class: runbookReferenceClasses(attrs),
        "data-md-ref-kind": attrs.kind,
        "data-md-ref-type": attrs.refType,
        "data-md-ref-id": attrs.refId,
        contenteditable: "false",
      }),
      attrs.label,
    ];
  },

  addCommands() {
    return {
      insertRunbookReference:
        (attrs) =>
        ({ commands }) =>
          commands.insertContent({
            type: this.name,
            attrs: normalizeRunbookReferenceAttrs(attrs),
          }),
    };
  },
});
