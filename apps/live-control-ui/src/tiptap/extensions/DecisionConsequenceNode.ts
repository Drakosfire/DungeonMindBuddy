import { mergeAttributes, Node } from "@tiptap/core";
import type { ResolvedPos } from "@tiptap/pm/model";
import type { EditorState, Transaction } from "@tiptap/pm/state";

function findNodeDepth($from: ResolvedPos, name: string): number | null {
  for (let depth = $from.depth; depth > 0; depth -= 1) {
    if ($from.node(depth).type.name === name) {
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
    decisionConsequence: {
      insertDecisionConsequence: () => ReturnType;
      deleteParentDecisionConsequence: () => ReturnType;
    };
  }
}

const emptyPaneParagraph = { type: "paragraph" };

export const DecisionPane = Node.create({
  name: "decisionPane",
  content: "block+",
  defining: true,
  isolating: true,

  parseHTML() {
    return [{ tag: "div.md-dc-pane-decision", contentElement: ".md-dc-pane-body" }];
  },

  renderHTML({ HTMLAttributes }) {
    return [
      "div",
      mergeAttributes(HTMLAttributes, {
        class: "md-dc-pane md-dc-pane-decision",
        "data-md-dc-pane": "decision",
      }),
      ["div", { class: "md-dc-pane-label", contenteditable: "false" }, "Decision"],
      ["div", { class: "md-dc-pane-body" }, 0],
    ];
  },
});

export const ConsequencePane = Node.create({
  name: "consequencePane",
  content: "block+",
  defining: true,
  isolating: true,

  parseHTML() {
    return [{ tag: "div.md-dc-pane-consequence", contentElement: ".md-dc-pane-body" }];
  },

  renderHTML({ HTMLAttributes }) {
    return [
      "div",
      mergeAttributes(HTMLAttributes, {
        class: "md-dc-pane md-dc-pane-consequence",
        "data-md-dc-pane": "consequence",
      }),
      ["div", { class: "md-dc-pane-label", contenteditable: "false" }, "Consequence"],
      ["div", { class: "md-dc-pane-body" }, 0],
    ];
  },
});

export const DecisionConsequenceNode = Node.create({
  name: "decisionConsequence",
  group: "block",
  content: "decisionPane consequencePane",
  defining: true,
  isolating: true,

  parseHTML() {
    return [
      {
        tag: "aside[data-md-decision-consequence]",
      },
    ];
  },

  renderHTML({ HTMLAttributes }) {
    return [
      "aside",
      mergeAttributes(HTMLAttributes, {
        class: "md-decision-consequence",
        "data-md-decision-consequence": "true",
      }),
      0,
    ];
  },

  addCommands() {
    return {
      insertDecisionConsequence:
        () =>
        ({ commands }) =>
          commands.insertContent({
            type: this.name,
            content: [
              { type: "decisionPane", content: [emptyPaneParagraph] },
              { type: "consequencePane", content: [emptyPaneParagraph] },
            ],
          }),
      deleteParentDecisionConsequence:
        () =>
        ({ state, dispatch }) => {
          const { $from } = state.selection;
          const depth = findNodeDepth($from, this.name);
          if (depth === null) {
            return false;
          }
          return deleteNodeAtDepth(state, dispatch, $from, depth);
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
        const pairDepth = findNodeDepth($from, "decisionConsequence");
        if (pairDepth === null) {
          return false;
        }

        const paneDepth = findNodeDepth($from, "decisionPane") ?? findNodeDepth($from, "consequencePane");
        if (paneDepth === null) {
          return false;
        }

        if ($from.index(paneDepth) !== 0 || $from.parentOffset !== 0) {
          return false;
        }

        if ($from.parent.content.size > 0) {
          return false;
        }

        // Only delete the whole pair when both panes are essentially empty
        // and the caret is in the first empty paragraph of the first pane.
        const pair = $from.node(pairDepth);
        const decision = pair.child(0);
        const consequence = pair.child(1);
        const paneIsEmpty = (pane: typeof decision) =>
          pane.childCount === 1 && pane.firstChild?.type.name === "paragraph" && pane.firstChild.content.size === 0;

        if (!paneIsEmpty(decision) || !paneIsEmpty(consequence)) {
          return false;
        }

        if ($from.node(paneDepth).type.name !== "decisionPane") {
          return false;
        }

        return editor.commands.deleteParentDecisionConsequence();
      },
    };
  },
});

export const DECISION_CONSEQUENCE_EXTENSIONS = [
  DecisionConsequenceNode,
  DecisionPane,
  ConsequencePane,
];
