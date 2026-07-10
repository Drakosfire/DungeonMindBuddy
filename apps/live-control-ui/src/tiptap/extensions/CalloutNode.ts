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
