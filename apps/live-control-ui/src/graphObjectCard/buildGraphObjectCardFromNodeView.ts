import type { GraphProjectionAdjacencyCandidate, GraphProjectionNodeView } from "../api/types";
import {
  displayAliasesForNode,
  friendlyVisibilityCopy,
  graphObjectSecondaryRoleLabel,
  graphObjectTypeBadgeLabel,
  primaryGameSummaryForNode,
} from "./graphObjectDisplay";
import type {
  GraphObjectCardViewModel,
  GraphObjectEvidenceViewModel,
  GraphObjectRelationshipViewModel,
} from "./types";

function normalizeDirection(
  direction: string | null | undefined,
): GraphObjectRelationshipViewModel["direction"] {
  if (direction === "incoming" || direction === "outgoing" || direction === "related") {
    return direction;
  }
  return null;
}

export function relationshipViewModelsFromAdjacency(
  adjacency: GraphProjectionAdjacencyCandidate[],
): GraphObjectRelationshipViewModel[] {
  return adjacency.map((edge) => ({
    id: edge.edge_id,
    label: edge.label,
    predicate: edge.predicate ?? null,
    direction: normalizeDirection(edge.direction),
    summary: edge.related_summary ?? null,
    targetId: edge.node_id,
    targetKind: edge.kind,
    evidenceRefIds: edge.evidence_ref_ids,
  }));
}

export function evidenceViewModelsFromNode(
  node: GraphProjectionNodeView,
): GraphObjectEvidenceViewModel[] {
  return node.evidence_badges.map((badge) => ({
    id: badge.evidence_ref_id,
    label: badge.label ?? null,
    sourceArtifactId: badge.source_artifact_id,
    sourceDomain: badge.source_domain,
    sourcePath: null,
    excerpt: null,
  }));
}

export function buildGraphObjectCardFromNodeView(
  node: GraphProjectionNodeView,
  options?: {
    whyItMattersNow?: string | null;
  },
): GraphObjectCardViewModel {
  const summary = primaryGameSummaryForNode(node);
  const aliases = displayAliasesForNode(node);
  const evidence = evidenceViewModelsFromNode(node);

  return {
    id: node.node_id,
    label: node.label,
    kind: node.kind,
    role: node.role,
    typeBadgeLabel: graphObjectTypeBadgeLabel(node.kind, node.role),
    secondaryRoleLabel: graphObjectSecondaryRoleLabel(node.kind, node.role),
    aliases,
    summary,
    gameSummary: summary,
    whyItMattersNow: options?.whyItMattersNow ?? null,
    relationships: relationshipViewModelsFromAdjacency(node.adjacency),
    evidence,
    sourceDomains: node.source_domains,
    visibilityLabel: node.visibility ? friendlyVisibilityCopy(node.visibility) : null,
    freshnessLabel: null,
    details: {
      visibilityLabel: node.visibility ? friendlyVisibilityCopy(node.visibility) : null,
      sourceDomains: node.source_domains,
      evidenceCount: evidence.length,
      sourceAnchorText: node.source_anchor_text ?? null,
      nodeId: node.node_id,
    },
    actions: [],
  };
}
