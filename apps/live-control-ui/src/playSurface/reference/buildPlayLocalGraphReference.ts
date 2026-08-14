import { buildGraphObjectCardFromNodeView } from "../../graphObjectCard";
import { hasOfConksPlayObjectBody } from "../../graphReference/ofConksPlayObjectBridge";
import type { GraphReferenceResolution } from "../../graphReference/types";
import { playArtifactIdForThreatNode } from "../../statblocks/projection/ofConksThreatPlayBridge";

function kindFromNodeId(nodeId: string): string {
  const prefix = nodeId.split(":")[0] ?? "object";
  if (prefix === "threat") return "creature";
  return prefix;
}

/** Of Conks play-object bodies and workbench-bridged threats only. */
export function canResolveOfConksLocalGraphReference(nodeId: string): boolean {
  const graphNodeId = nodeId.trim();
  if (!graphNodeId) return false;
  return hasOfConksPlayObjectBody(graphNodeId) || playArtifactIdForThreatNode(graphNodeId) != null;
}

/**
 * Local Play resolution (no live graph fetch).
 * Bridged Of Conks nodes render Play/Threat sheets; others fall back to GraphObjectCard.
 */
export function buildPlayLocalGraphReferenceResolution(
  nodeId: string,
  label?: string | null,
): Extract<GraphReferenceResolution, { kind: "resolved_graph" }> | null {
  const graphNodeId = nodeId.trim();
  if (!graphNodeId) return null;

  const resolvedLabel = (label ?? "").trim() || graphNodeId;
  const kind = kindFromNodeId(graphNodeId);
  return {
    kind: "resolved_graph",
    locator: `dmb-node:${graphNodeId}`,
    reference: null,
    graphNodeId,
    graphObject: buildGraphObjectCardFromNodeView({
      node_id: graphNodeId,
      label: resolvedLabel,
      kind,
      role: kind,
      aliases: [],
      source_domains: ["worldbuilding"],
      evidence_badges: [],
      adjacency: [],
      anchored_to_focus_session: true,
      summary: null,
    }),
    graphScope: null,
    projectionState: "ready",
    message: null,
  };
}

/**
 * Plan/Play local fallback: only Of Conks bridged nodes, never arbitrary campaign ids.
 */
export function tryOfConksLocalGraphReferenceResolution(
  nodeId: string,
  label?: string | null,
): Extract<GraphReferenceResolution, { kind: "resolved_graph" }> | null {
  if (!canResolveOfConksLocalGraphReference(nodeId)) return null;
  return buildPlayLocalGraphReferenceResolution(nodeId, label);
}
