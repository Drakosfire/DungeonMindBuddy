import type { GraphProjectionNodeView } from "../api/types";
import {
  buildRecapNodePresentation,
  fallbackRecapNodePresentation,
} from "../planSurface/graphPreview/recapNodePresentation";
import type { GraphNodeGlancePresentation } from "./types";

export function presentationForNodeId(
  nodeViews: Record<string, GraphProjectionNodeView>,
  nodeId: string,
  label: string,
): GraphNodeGlancePresentation {
  const node = nodeViews[nodeId];
  return node ? buildRecapNodePresentation(node) : fallbackGlance(nodeId, label);
}

export function fallbackGlance(nodeId: string, label: string): GraphNodeGlancePresentation {
  return fallbackRecapNodePresentation(nodeId, label);
}

export function roleClass(role: string): string {
  return role.toLowerCase().replace(/[^a-z0-9_-]+/g, "-") || "node";
}
