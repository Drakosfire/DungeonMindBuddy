import { mergeAttributes, Node } from "@tiptap/core";
import { ReactNodeViewRenderer } from "@tiptap/react";

import {
  isSupportedRunbookReference,
  normalizeRunbookReferenceAttrs,
  runbookReferenceClasses,
  type RunbookReferenceAttrs,
} from "../references/runbookReferences";
import { RunbookReferenceView } from "./RunbookReferenceView";

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
      kind: { default: "ref", rendered: false },
      refType: { default: "npc", rendered: false },
      refId: { default: "", rendered: false },
      label: { default: "", rendered: false },
    };
  },

  renderHTML({ node, HTMLAttributes }) {
    const attrs = normalizeRunbookReferenceAttrs(node.attrs);
    const hasKnownKind = node.attrs.kind === "ref" || node.attrs.kind === "action";
    const isSupported = hasKnownKind && isSupportedRunbookReference(attrs);
    return [
      "span",
      mergeAttributes(HTMLAttributes, {
        class: isSupported ? runbookReferenceClasses(attrs) : "md-ref-invalid",
        "data-md-ref-kind": isSupported ? attrs.kind : "invalid",
        "data-md-ref-type": attrs.refType,
        "data-md-ref-id": attrs.refId,
        contenteditable: "false",
        title: isSupported ? undefined : "Invalid runbook reference",
      }),
      attrs.label,
    ];
  },

  addNodeView() {
    return ReactNodeViewRenderer(RunbookReferenceView);
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
