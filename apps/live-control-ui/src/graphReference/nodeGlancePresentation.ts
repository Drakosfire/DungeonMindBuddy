import type {
  GraphProjectionAdjacencyCandidate,
  GraphProjectionEvidenceBadge,
  GraphProjectionNodeView,
  GraphProjectionSuggestedExpansion,
  RecapGraphChip,
} from "../api/types";
import { primaryGameSummaryForNode } from "../graphObjectCard/graphObjectDisplay";
import type { GraphNodeGlancePresentation, GraphNodeGlanceThreadHint } from "./types";

function humanizeToken(value: string): string {
  return value.replace(/_/g, " ").trim();
}

function evidencePlanningText(badge: GraphProjectionEvidenceBadge): string {
  const label = badge.label?.trim();
  if (label) {
    const colonIdx = label.indexOf(":");
    if (colonIdx > 0 && label.slice(0, colonIdx) === badge.source_domain) {
      const stripped = label.slice(colonIdx + 1).trim();
      return stripped || label;
    }
    return label;
  }
  return humanizeToken(badge.evidence_role);
}

function labeledEvidenceText(badge: GraphProjectionEvidenceBadge): string | null {
  return badge.label?.trim() ? evidencePlanningText(badge) : null;
}

function adjacencyThreadLabel(candidate: GraphProjectionAdjacencyCandidate): string {
  const edgeLabel = candidate.edge_label?.trim();
  if (edgeLabel) {
    return `${edgeLabel} ${candidate.label}`;
  }
  return `${humanizeToken(candidate.predicate)} ${candidate.label}`;
}

function expansionPresentationLabel(expansion: GraphProjectionSuggestedExpansion): string {
  return adjacencyThreadLabel(expansion);
}

function sessionChipLabel(sessionId: string | null | undefined): string | null {
  if (!sessionId) {
    return null;
  }
  const match = sessionId.match(/(\d+)\s*$/);
  return match ? `S${match[1]}` : sessionId;
}

function buildPlanningChips(node: GraphProjectionNodeView): RecapGraphChip[] {
  const chips: RecapGraphChip[] = [{ label: node.role, tone: "neutral" }];

  if (node.anchored_to_focus_session) {
    const focusSession = sessionChipLabel(
      node.evidence_badges.find((b) => b.is_focus_session_evidence)?.session_id,
    );
    if (focusSession) {
      chips.push({ label: focusSession, tone: "evidence" });
    }
  }

  const hasWorldbuilding = node.source_domains.includes("worldbuilding");
  const hasRecap = node.source_domains.includes("recap");
  if (hasWorldbuilding && !hasRecap) {
    chips.push({ label: "worldbuilding", tone: "neutral" });
  }

  return chips;
}

function suggestedExpansionsForNode(node: GraphProjectionNodeView): GraphProjectionSuggestedExpansion[] {
  if (node.suggested_expansions?.length) {
    return node.suggested_expansions;
  }
  return node.adjacency.map((candidate, index) => ({
    ...candidate,
    rank: index + 1,
    rank_reason: candidate.anchored_to_focus_session ? "current session" : "connected thread",
  }));
}

function focusRelationshipText(node: GraphProjectionNodeView): string | null {
  const focusRelationship = suggestedExpansionsForNode(node).find(
    (candidate) => candidate.anchored_to_focus_session,
  );
  if (!focusRelationship) {
    return null;
  }
  const relationship = humanizeToken(
    focusRelationship.edge_label?.trim() || focusRelationship.predicate,
  );
  if (!relationship) {
    return null;
  }
  return focusRelationship.direction === "incoming"
    ? `${focusRelationship.label} ${relationship} ${node.label} this session.`
    : `${node.label} ${relationship} ${focusRelationship.label} this session.`;
}

function buildThreadHints(node: GraphProjectionNodeView): GraphNodeGlanceThreadHint[] {
  return suggestedExpansionsForNode(node)
    .slice(0, 2)
    .map((expansion) => ({
      nodeId: expansion.node_id,
      label: expansion.label,
      edgeLabel: expansionPresentationLabel(expansion),
      anchoredToFocusSession: expansion.anchored_to_focus_session,
      rankReason: expansion.rank_reason,
    }));
}

export function buildGraphNodeGlancePresentation(node: GraphProjectionNodeView): GraphNodeGlancePresentation {
  const focusEvidence = node.evidence_badges.filter((badge) => badge.is_focus_session_evidence);
  const contextEvidence = node.evidence_badges.filter((badge) => !badge.is_focus_session_evidence);

  const summary = primaryGameSummaryForNode(node);
  const whyNow = focusEvidence.map(labeledEvidenceText).find(Boolean)
    ?? focusRelationshipText(node);
  const knownBefore = contextEvidence.length ? evidencePlanningText(contextEvidence[0]) : null;

  return {
    nodeId: node.node_id,
    label: node.label,
    kind: node.kind,
    role: node.role,
    summary,
    whyNow,
    knownBefore,
    planningChips: buildPlanningChips(node),
    threadHints: buildThreadHints(node),
  };
}

export function fallbackGraphNodeGlancePresentation(
  nodeId: string,
  label: string,
): GraphNodeGlancePresentation {
  return {
    nodeId,
    label,
    kind: "node",
    role: "node",
    summary: null,
    whyNow: null,
    knownBefore: null,
    planningChips: [],
    threadHints: [],
  };
}
