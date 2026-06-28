import { NodeViewWrapper } from "@tiptap/react";
import type { NodeViewProps } from "@tiptap/react";

import {
  GraphNodeToken,
  presentationForNodeId,
} from "../../planSurface/graphPreview/GraphNodePresentation";
import { useRecapGraphNodeRuntimeState } from "../../planSurface/graphPreview/recapGraphNodeRuntime";
import type { GraphNodeReferenceAttrs } from "./GraphNodeReferenceNode";

export function GraphNodeReferenceView({ node }: NodeViewProps) {
  const { nodeViews, pinnedNodeId, onSelectNode } = useRecapGraphNodeRuntimeState();
  const attrs = node.attrs as GraphNodeReferenceAttrs;
  const presentation = presentationForNodeId(nodeViews, attrs.nodeId, attrs.label);

  return (
    <NodeViewWrapper as="span" className="graph-node-reference-view">
      <GraphNodeToken
        presentation={presentation}
        label={attrs.label || attrs.nodeId}
        pinned={pinnedNodeId === attrs.nodeId}
        onSelect={() => onSelectNode(attrs.nodeId)}
      />
    </NodeViewWrapper>
  );
}
