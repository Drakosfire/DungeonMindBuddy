import type { GraphProjectionNodeView } from "../../api/types";
import { buildGraphObjectCardFromNodeView } from "../../graphObjectCard";
import {
  GRAPH_NODE_REF_TYPE,
  type RunbookReferenceAttrs,
} from "../../tiptap/references/runbookReferences";
import type { PlanReferenceResolution } from "./graphAwareReferenceResolver";

/**
 * Build a Plan reference resolution from a projection node view already on the
 * surface (Recap/Ingest lane). Same card host as World Graph hits — no second
 * resolve ladder when the chip already carries the object.
 */
export function planReferenceResolutionFromNodeView(
  node: GraphProjectionNodeView,
  label?: string,
): { ref: RunbookReferenceAttrs; resolution: PlanReferenceResolution } {
  const nodeId = String(node.node_id || "").trim();
  const resolvedLabel = (label ?? node.label ?? nodeId).trim() || nodeId;
  const ref: RunbookReferenceAttrs = {
    kind: "ref",
    refType: GRAPH_NODE_REF_TYPE,
    refId: nodeId,
    label: resolvedLabel,
  };
  return {
    ref,
    resolution: {
      kind: "graph-node",
      locator: `#dmb-ref:${GRAPH_NODE_REF_TYPE}:${nodeId}`,
      refType: GRAPH_NODE_REF_TYPE,
      refId: nodeId,
      graphObject: buildGraphObjectCardFromNodeView(node),
      graphNodeId: nodeId,
      fallback: null,
      source: "world-graph",
      message: `Resolved graph node ${resolvedLabel}.`,
      graphProjectionState: "ready",
    },
  };
}
