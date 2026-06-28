import type {
  GraphProjectionNodeView,
  RecapGraphChip,
  UnionSupergraphProjectionResponse,
} from "../../api/types";

export function roleClass(role: string): string {
  return role.toLowerCase().replace(/[^a-z0-9_-]+/g, "-") || "node";
}

export interface RecapNodePresentation {
  nodeId: string;
  label: string;
  kind: string;
  role: string;
  description: string | null;
  chips: RecapGraphChip[];
}

export function buildRecapNodePresentation(node: GraphProjectionNodeView): RecapNodePresentation {
  const focusEvidence = node.evidence_badges.filter((badge) => badge.is_focus_session_evidence);
  const contextEvidence = node.evidence_badges.filter((badge) => !badge.is_focus_session_evidence);
  const chips: RecapGraphChip[] = [];

  if (focusEvidence.length) {
    chips.push({ label: `${focusEvidence.length} focus evidence`, tone: "evidence" });
  }
  if (contextEvidence.length) {
    chips.push({ label: `${contextEvidence.length} broader context`, tone: "neutral" });
  }
  if (node.adjacency.length) {
    chips.push({ label: `${node.adjacency.length} adjacent`, tone: "neutral" });
  }
  for (const domain of node.source_domains) {
    chips.push({ label: domain, tone: "neutral" });
  }
  if (node.anchored_to_focus_session) {
    chips.push({ label: "focus session", tone: "evidence" });
  }

  const description =
    node.summary?.trim()
    || (node.source_domains.length ? `Sources: ${node.source_domains.join(", ")}` : null)
    || node.evidence_badges[0]?.label
    || null;

  return {
    nodeId: node.node_id,
    label: node.label,
    kind: node.kind,
    role: node.role,
    description,
    chips,
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
    description: null,
    chips: [],
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
