import "./CalloutNode.css";
import { mergeAttributes, Node } from "@tiptap/core";
import type { ResolvedPos } from "@tiptap/pm/model";
import type { EditorState, Transaction } from "@tiptap/pm/state";

import {
  defaultCalloutLabel,
  normalizeCalloutKind,
  type CalloutAttrs,
  type CalloutKind,
} from "../markdown/calloutMarkdown";

function findCalloutDepth($from: ResolvedPos): number | null {
  for (let depth = $from.depth; depth > 0; depth -= 1) {
    if ($from.node(depth).type.name === "callout") {
      return depth;
    }
  }
  return null;
}

function deleteNodeAtDepth(
  state: EditorState,
  dispatch: ((tr: Transaction) => void) | undefined,
  $from: ResolvedPos,
  depth: number,
): boolean {
  const node = $from.node(depth);
  const pos = $from.before(depth);
  const tr = state.tr.delete(pos, pos + node.nodeSize);
  if (dispatch) {
    dispatch(tr);
  }
  return true;
}

declare module "@tiptap/core" {
  interface Commands<ReturnType> {
    callout: {
      insertCallout: (attrs: Partial<CalloutAttrs>) => ReturnType;
      deleteParentCallout: () => ReturnType;
      deleteActiveBlock: () => ReturnType;
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
        tag: "aside[data-md-callout], details[data-md-callout]",
        getAttrs: (element) => {
          const dom = element as HTMLElement;
          const kind = normalizeCalloutKind(dom.getAttribute("data-md-callout"));
          const oldLabel = dom.querySelector(".md-callout-label")?.textContent?.trim();
          return { kind, label: dom.getAttribute("data-md-callout-label")
            ?? (dom.tagName === "ASIDE" && oldLabel !== defaultCalloutLabel(kind) ? oldLabel : null) };
        },
        contentElement: ".md-callout-body",
      },
    ];
  },

  renderHTML({ node, HTMLAttributes }) {
    const kind = normalizeCalloutKind(node.attrs.kind);
    const title = typeof node.attrs.label === "string" ? node.attrs.label.trim() : "";
    return [
      "details",
      mergeAttributes(HTMLAttributes, {
        class: `md-callout md-callout-${kind}`,
        "data-md-callout": kind,
        ...(title ? { "data-md-callout-label": title } : {}),
        open: "",
      }),
      ["summary", { class: "md-callout-label", contenteditable: "false" },
        ["span", { class: "md-callout-kind" }, defaultCalloutLabel(kind)],
        ...(title ? [["span", { class: "md-callout-title" }, `: ${title}`]] : []),
      ],
      ["div", { class: "md-callout-body" }, 0],
    ];
  },

  addNodeView() {
    return ({ node }) => {
      const dom = document.createElement("details");
      dom.open = true;
      const summary = document.createElement("summary");
      summary.className = "md-callout-label";
      summary.contentEditable = "false";
      const contentDOM = document.createElement("div");
      contentDOM.className = "md-callout-body";
      dom.append(summary, contentDOM);
      const updateHeader = (attrs: Record<string, unknown>) => {
        const kind = normalizeCalloutKind(attrs.kind);
        const title = typeof attrs.label === "string" ? attrs.label.trim() : "";
        dom.className = `md-callout md-callout-${kind}`;
        dom.dataset.mdCallout = kind;
        if (title) dom.dataset.mdCalloutLabel = title;
        else delete dom.dataset.mdCalloutLabel;
        const label = document.createElement("span");
        label.className = "md-callout-kind";
        label.textContent = defaultCalloutLabel(kind);
        summary.replaceChildren(label);
        if (title) {
          const caption = document.createElement("span");
          caption.className = "md-callout-title";
          caption.textContent = `: ${title}`;
          summary.append(caption);
        }
      };
      updateHeader(node.attrs);
      return {
        dom,
        contentDOM,
        update(next) {
          if (next.type !== node.type) return false;
          updateHeader(next.attrs);
          return true;
        },
        stopEvent: event => event.target instanceof globalThis.Node && summary.contains(event.target),
        ignoreMutation: mutation => (mutation.type === "attributes" && mutation.target === dom && mutation.attributeName === "open")
          || summary.contains(mutation.target),
      };
    };
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
      deleteParentCallout:
        () =>
        ({ state, dispatch }) => {
          const { $from } = state.selection;
          const calloutDepth = findCalloutDepth($from);
          if (calloutDepth === null) {
            return false;
          }
          return deleteNodeAtDepth(state, dispatch, $from, calloutDepth);
        },
      deleteActiveBlock:
        () =>
        ({ state, dispatch }) => {
          const { $from } = state.selection;
          const calloutDepth = findCalloutDepth($from);
          if (calloutDepth !== null) {
            return deleteNodeAtDepth(state, dispatch, $from, calloutDepth);
          }

          for (let depth = $from.depth; depth > 0; depth -= 1) {
            const node = $from.node(depth);
            if (node.isBlock && node.type.name !== "doc") {
              return deleteNodeAtDepth(state, dispatch, $from, depth);
            }
          }

          return false;
        },
    };
  },

  addKeyboardShortcuts() {
    return {
      Backspace: ({ editor }) => {
        const { state } = editor;
        const { selection } = state;
        if (!selection.empty) {
          return false;
        }

        const { $from } = selection;
        const calloutDepth = findCalloutDepth($from);
        if (calloutDepth === null) {
          return false;
        }

        if ($from.index(calloutDepth) !== 0 || $from.parentOffset !== 0) {
          return false;
        }

        if ($from.parent.content.size > 0) {
          return false;
        }

        return editor.commands.deleteParentCallout();
      },
    };
  },
});
