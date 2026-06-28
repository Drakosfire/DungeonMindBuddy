import type {
  GraphProjectionAdjacencyCandidate,
  GraphProjectionEvidenceBadge,
  GraphProjectionNodeView,
  RecapGraphChip,
  UnionSupergraphProjectionResponse,
} from "../../api/types";

export function roleClass(role: string): string {
  return role.toLowerCase().replace(/[^a-z0-9_-]+/g, "-") || "node";
}

export interface RecapPlanningThreadHint {
  nodeId: string;
  label: string;
  edgeLabel: string;
  anchoredToFocusSession: boolean;
}

export interface RecapNodePresentation {
  nodeId: string;
  label: string;
  kind: string;
  role: string;
  summary: string | null;
  whyNow: string | null;
  knownBefore: string | null;
  planningChips: RecapGraphChip[];
  threadHints: RecapPlanningThreadHint[];
}

function humanizeToken(value: string): string {
  return value.replace(/_/g, " ").trim();
}

export function evidencePlanningText(badge: GraphProjectionEvidenceBadge): string {
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

export function adjacencyThreadLabel(candidate: GraphProjectionAdjacencyCandidate): string {
  const edgeLabel = candidate.edge_label?.trim();
  if (edgeLabel) {
    return `${edgeLabel} ${candidate.label}`;
  }
  return `${humanizeToken(candidate.predicate)} ${candidate.label}`;
}

function sessionChipLabel(sessionId: string | null | undefined): string | null {
  if (!sessionId) {
    return null;
  }
  const match = sessionId.match(/(\d+)\s*$/);
  return match ? `S${match[1]}` : sessionId;
}

function buildPlanningChips(node: GraphProjectionNodeView): RecapGraphChip[] {
  const chips: RecapGraphChip[] = [
    { label: node.role, tone: "neutral" },
  ];

  if (node.anchored_to_focus_session) {
    const focusSession = sessionChipLabel(node.evidence_badges.find((b) => b.is_focus_session_evidence)?.session_id);
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

function buildThreadHints(node: GraphProjectionNodeView): RecapPlanningThreadHint[] {
  return node.adjacency.slice(0, 2).map((candidate) => ({
    nodeId: candidate.node_id,
    label: candidate.label,
    edgeLabel: adjacencyThreadLabel(candidate),
    anchoredToFocusSession: candidate.anchored_to_focus_session,
  }));
}

export function buildRecapNodePresentation(node: GraphProjectionNodeView): RecapNodePresentation {
  const focusEvidence = node.evidence_badges.filter((badge) => badge.is_focus_session_evidence);
  const contextEvidence = node.evidence_badges.filter((badge) => !badge.is_focus_session_evidence);

  const summary = node.summary?.trim() || null;
  const whyNow = focusEvidence.length ? evidencePlanningText(focusEvidence[0]) : null;
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

export function fallbackRecapNodePresentation(
  nodeId: string,
  label: string,
): RecapNodePresentation {
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

export function defaultPinnedNodeId(payload: UnionSupergraphProjectionResponse): string | null {
  for (const nodeId of payload.focus.focused_node_ids) {
    if (payload.node_views[nodeId]) {
      return nodeId;
    }
  }
  const mentionNodeId = payload.mentions[0]?.node_id;
  if (mentionNodeId && payload.node_views[mentionNodeId]) {
    return mentionNodeId;
  }
  const firstNodeId = Object.keys(payload.node_views)[0];
  return firstNodeId ?? null;
}
