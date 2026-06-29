import { mergeAttributes, Node } from "@tiptap/core";
import { ReactNodeViewRenderer } from "@tiptap/react";

import { GraphNodeReferenceView } from "./GraphNodeReferenceView";

export interface GraphNodeReferenceAttrs {
  nodeId: string;
  label: string;
}

export const GraphNodeReferenceNode = Node.create({
  name: "graphNodeReference",
  group: "inline",
  inline: true,
  atom: true,
  selectable: true,

  addAttributes() {
    return {
      nodeId: { default: "", rendered: false },
      label: { default: "", rendered: false },
    };
  },

  parseHTML() {
    return [
      {
        tag: 'button[data-graph-node-id]',
        getAttrs: (element) => {
          if (!(element instanceof HTMLElement)) {
            return false;
          }
          const nodeId = element.dataset.graphNodeId;
          if (!nodeId) {
            return false;
          }
          return {
            nodeId,
            label: element.textContent?.trim() || nodeId,
          };
        },
      },
    ];
  },

  renderHTML({ node, HTMLAttributes }) {
    const attrs = node.attrs as GraphNodeReferenceAttrs;
    return [
      "button",
      mergeAttributes(HTMLAttributes, {
        type: "button",
        class: "graph-node-reference-pill recap-node-token",
        "data-graph-node-id": attrs.nodeId,
        contenteditable: "false",
      }),
      attrs.label || attrs.nodeId,
    ];
  },

  addNodeView() {
    return ReactNodeViewRenderer(GraphNodeReferenceView);
  },
});
