import { mergeAttributes, Node } from "@tiptap/core";

import {
  defaultCalloutLabel,
  normalizeCalloutKind,
  type CalloutAttrs,
  type CalloutKind,
} from "../markdown/calloutMarkdown";

declare module "@tiptap/core" {
  interface Commands<ReturnType> {
    callout: {
      insertCallout: (attrs: Partial<CalloutAttrs>) => ReturnType;
    };
  }
}

export const CalloutNode = Node.create({
  name: "callout",
  group: "block",
  content: "block+",
  defining: true,
  isolating: true,

  addAttributes() {
    return {
      kind: {
        default: "warning" satisfies CalloutKind,
        parseHTML: (element: HTMLElement) => normalizeCalloutKind(element.getAttribute("data-md-callout")),
      },
      label: {
        default: null,
        rendered: false,
      },
    };
  },

  parseHTML() {
    return [
      {
        tag: "aside[data-md-callout]",
        getAttrs: (element) => ({
          kind: normalizeCalloutKind((element as HTMLElement).getAttribute("data-md-callout")),
        }),
        contentElement: ".md-callout-body",
      },
    ];
  },

  renderHTML({ node, HTMLAttributes }) {
    const kind = normalizeCalloutKind(node.attrs.kind);
    const label =
      typeof node.attrs.label === "string" && node.attrs.label.trim()
        ? node.attrs.label.trim()
        : defaultCalloutLabel(kind);

    return [
      "aside",
      mergeAttributes(HTMLAttributes, {
        class: `md-callout md-callout-${kind}`,
        "data-md-callout": kind,
      }),
      ["div", { class: "md-callout-label", contenteditable: "false" }, label],
      ["div", { class: "md-callout-body" }, 0],
    ];
  },

  addCommands() {
    return {
      insertCallout:
        (attrs) =>
        ({ commands }) =>
          commands.insertContent({
            type: this.name,
            attrs: {
              kind: normalizeCalloutKind(attrs.kind),
              label: typeof attrs.label === "string" ? attrs.label : null,
            },
            content: [{ type: "paragraph" }],
          }),
    };
  },
});
