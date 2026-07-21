import type {
  GraphProjectionAdjacencyCandidate,
  GraphProjectionEvidenceBadge,
  GraphProjectionNodeView,
  GraphProjectionSuggestedExpansion,
  WorldGraphProjectionNodeView,
} from "../../api/types";

function adaptEvidenceBadge(badge: WorldGraphProjectionNodeView["evidenceBadges"][number]): GraphProjectionEvidenceBadge {
  return {
    evidence_ref_id: badge.evidenceRefId,
    source_artifact_id: badge.sourceArtifactId,
    source_domain: badge.sourceDomain,
    evidence_role: badge.evidenceRole,
    is_focus_session_evidence: badge.isFocusSessionEvidence,
    can_open_source: badge.canOpenSource,
    can_highlight_span: badge.canHighlightSpan,
    label: badge.label,
    session_id: badge.sessionId,
    source_span_ref_id: badge.sourceSpanRefId,
  };
}

function adaptRelationshipDirection(direction: string | null | undefined): string | null {
  if (direction == null || direction === "") {
    return null;
  }
  if (direction === "outbound") {
    return "outgoing";
  }
  if (direction === "inbound") {
    return "incoming";
  }
  if (direction === "outgoing" || direction === "incoming" || direction === "related") {
    return direction;
  }
  return direction;
}

function adaptAdjacency(
  candidate: WorldGraphProjectionNodeView["adjacency"][number],
): GraphProjectionAdjacencyCandidate {
  return {
    edge_id: candidate.edgeId,
    node_id: candidate.nodeId,
    label: candidate.label,
    kind: candidate.kind,
    predicate: candidate.predicate,
    direction: adaptRelationshipDirection(candidate.direction),
    anchored_to_focus_session: candidate.anchoredToFocusSession,
    source_domains: candidate.sourceDomains,
    evidence_ref_ids: candidate.evidenceRefIds,
    edge_label: candidate.edgeLabel,
    session_ids: candidate.sessionIds,
    campaign_scope: candidate.campaignScope ?? null,
    related_summary: candidate.relatedSummary,
    source_excerpt: candidate.sourceExcerpt,
  };
}

function adaptSuggestedExpansion(
  candidate: WorldGraphProjectionNodeView["suggestedExpansions"][number],
): GraphProjectionSuggestedExpansion {
  return {
    ...adaptAdjacency(candidate),
    rank: candidate.rank,
    rank_reason: candidate.rankReason,
  };
}

/** Adapts the World Graph node contract at the Plan card boundary. */
export function adaptWorldGraphNodeForPlanCard(
  node: WorldGraphProjectionNodeView,
): GraphProjectionNodeView {
  return {
    node_id: node.nodeId,
    label: node.label,
    kind: node.kind,
    role: node.role,
    aliases: node.aliases,
    source_domains: node.sourceDomains,
    evidence_badges: node.evidenceBadges.map(adaptEvidenceBadge),
    adjacency: node.adjacency.map(adaptAdjacency),
    suggested_expansions: node.suggestedExpansions.map(adaptSuggestedExpansion),
    anchored_to_focus_session: node.anchoredToFocusSession,
    summary: node.summary,
    campaign_scope: node.campaignScope ?? null,
  };
}
