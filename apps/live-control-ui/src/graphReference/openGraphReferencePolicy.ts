import { isThreatHoverPresentation } from "../statblocks/projection/threatSheetViewModel";
import { hasOfConksPlayObjectBody } from "./ofConksPlayObjectBridge";
import type { GraphReferenceResolution } from "./types";

/**
 * Full campaign/play sheets (Threat sheet or Of Conks play object sheet) skip glance-first.
 */
export function opensFullPlaySheet(resolution: GraphReferenceResolution): boolean {
  if (resolution.kind !== "resolved_graph") return false;
  if (
    isThreatHoverPresentation({
      nodeId: resolution.graphNodeId,
      kind: resolution.graphObject.kind,
      role: resolution.graphObject.role,
    })
  ) {
    return true;
  }
  return hasOfConksPlayObjectBody(resolution.graphNodeId);
}

/**
 * Authored Threats and Of Conks play-bridged nodes open as full sheets;
 * other graph refs stay glance-first.
 */
export function glanceOnlyForGraphReference(resolution: GraphReferenceResolution): boolean {
  return !opensFullPlaySheet(resolution);
}
