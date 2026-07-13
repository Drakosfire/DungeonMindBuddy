import type { GraphProjectionNodeView } from "../../api/types";
import {
  GRAPH_NODE_REF_TYPE,
  type RunbookReferenceAttrs,
} from "../../tiptap/references/runbookReferences";

/**
 * Build a Plan chip from a World Graph projection node.
 *
 * Always uses the graph-native `graph-node` ref type and the exact durable
 * `node_id` (including colons). Do not sanitize IDs or map unknown kinds onto
 * corpus taxonomy — resolution must bind to durable graph identity.
 */
export function runbookReferenceFromGraphNode(
  node: GraphProjectionNodeView,
): RunbookReferenceAttrs {
  const nodeId = String(node.node_id || "").trim();
  return {
    kind: "ref",
    refType: GRAPH_NODE_REF_TYPE,
    refId: nodeId,
    label: String(node.label || nodeId).trim() || nodeId,
  };
}
