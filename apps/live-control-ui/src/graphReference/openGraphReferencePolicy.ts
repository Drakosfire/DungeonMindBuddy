import {
  isThreatHoverPresentation,
} from "../statblocks/projection/threatSheetViewModel";
import type { GraphReferenceResolution } from "./types";

/**
 * Authored Threats open as full campaign sheet; other graph refs stay glance-first.
 */
export function glanceOnlyForGraphReference(resolution: GraphReferenceResolution): boolean {
  if (resolution.kind !== "resolved_graph") return true;
  return !isThreatHoverPresentation({
    nodeId: resolution.graphNodeId,
    kind: resolution.graphObject.kind,
    role: resolution.graphObject.role,
  });
}
