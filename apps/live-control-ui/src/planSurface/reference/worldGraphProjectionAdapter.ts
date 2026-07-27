import type { GraphProjectionNodeView, WorldGraphProjectionNodeView } from "../../api/types";
import { adaptWorldGraphNodeView } from "../../worldGraph/worldGraphNodeViewAdapter";

/** @deprecated Plan compatibility alias — prefer `adaptWorldGraphNodeView` from `worldGraph/`. */
export function adaptWorldGraphNodeForPlanCard(
  node: WorldGraphProjectionNodeView,
): GraphProjectionNodeView {
  return adaptWorldGraphNodeView(node);
}
