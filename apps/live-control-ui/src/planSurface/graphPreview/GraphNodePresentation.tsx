import type { GraphProjectionNodeView } from "../../api/types";
import {
  GraphNodeHoverToken,
  presentationForNodeId as sharedPresentationForNodeId,
} from "../../graphReference";
import type { RecapNodePresentation } from "./recapNodePresentation";

/** @deprecated Prefer GraphNodeHoverToken from graphReference; kept as Graph Review lane alias. */
export const GraphNodeToken = GraphNodeHoverToken;

export function presentationForNodeId(
  nodeViews: Record<string, GraphProjectionNodeView>,
  nodeId: string,
  label: string,
): RecapNodePresentation {
  return sharedPresentationForNodeId(nodeViews, nodeId, label);
}
