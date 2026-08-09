import { NodeViewWrapper } from "@tiptap/react";
import type { NodeViewProps } from "@tiptap/react";

import {
  GraphNodeHoverToken,
  presentationForNodeId,
  useGraphNodeChipRuntime,
} from "../../graphReference";
import { healRunbookReferenceLabel } from "../references/runbookReferences";
import type { GraphNodeReferenceAttrs } from "./GraphNodeReferenceNode";

export function GraphNodeReferenceView({ node }: NodeViewProps) {
  const { nodeViews, activeNodeId, onSelectNode, deltaByNodeId } = useGraphNodeChipRuntime();
  const attrs = node.attrs as GraphNodeReferenceAttrs;
  const label = healRunbookReferenceLabel(attrs.label || attrs.nodeId) || attrs.nodeId;
  const presentation = presentationForNodeId(nodeViews, attrs.nodeId, label);
  const delta = deltaByNodeId?.[attrs.nodeId];

  return (
    <NodeViewWrapper as="span" className="graph-node-reference-view">
      <GraphNodeHoverToken
        presentation={presentation}
        label={label}
        pinned={activeNodeId === attrs.nodeId}
        onSelect={() => onSelectNode(attrs.nodeId)}
        deltaStatus={delta?.status}
        deltaLabel={delta?.label}
        deltaSummary={delta?.summary}
      />
    </NodeViewWrapper>
  );
}
