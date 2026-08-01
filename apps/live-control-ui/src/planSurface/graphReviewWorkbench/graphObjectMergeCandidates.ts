import type { GraphProjectionNodeView } from "../../api/types";
import { inferCandidateGraphScopeFromProjectionNode } from "./graphObjectCandidateScope";
import type { GraphObjectAuthoringOverlapWarning } from "./graphObjectAuthoringOverlap";
import {
  areSameObjectRef,
  buildObjectRefFromInspectedNode,
  type GraphObjectAuthoringObjectRef,
  type GraphObjectAuthoringProposal,
} from "./graphObjectAuthoringDraft";

export type GraphObjectMergeCandidateConfidence = "high" | "medium" | "low";

export interface GraphObjectMergeCandidate {
  candidateId: string;
  survivorObjectRef: GraphObjectAuthoringObjectRef;
  mergedObjectRef: GraphObjectAuthoringObjectRef;
  confidence: GraphObjectMergeCandidateConfidence;
  matchedFeatures: string[];
  reason: string;
}

export function normalizeMergeLabel(text: string): string {
  return text
    .trim()
    .toLowerCase()
    .replace(/[^\w\s-]/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

function collapsePunctuationVariants(text: string): string {
  return normalizeMergeLabel(text).replace(/[-_]/g, " ");
}

function nodeTokens(node: GraphProjectionNodeView): Set<string> {
  const tokens = new Set<string>();
  const add = (value: string | null | undefined) => {
    const normalized = normalizeMergeLabel(value ?? "");
    if (normalized) {
      tokens.add(normalized);
    }
    const collapsed = collapsePunctuationVariants(value ?? "");
    if (collapsed) {
      tokens.add(collapsed);
    }
  };
  add(node.label);
  for (const alias of node.aliases) {
    add(alias);
  }
  add(node.source_anchor_text ?? null);
  return tokens;
}

function survivorScore(node: GraphProjectionNodeView): number {
  let score = 0;
  if (node.authored === true || node.source_domains.includes("authored_overlay")) {
    score += 1000;
  }
  if (
    node.source_domains.some((domain) =>
      ["campaign_memory", "worldbuilding", "party_pc"].includes(domain),
    )
  ) {
    score += 500;
  }
  score += (node.summary?.length ?? 0) / 10;
  score += node.evidence_badges.length * 5;
  score += node.adjacency.length * 2;
  score += node.aliases.length;
  return score;
}

function chooseSurvivor(
  left: GraphProjectionNodeView,
  right: GraphProjectionNodeView,
): { survivor: GraphProjectionNodeView; merged: GraphProjectionNodeView } {
  const leftScore = survivorScore(left);
  const rightScore = survivorScore(right);
  if (leftScore > rightScore) {
    return { survivor: left, merged: right };
  }
  if (rightScore > leftScore) {
    return { survivor: right, merged: left };
  }
  if (left.node_id.localeCompare(right.node_id) <= 0) {
    return { survivor: left, merged: right };
  }
  return { survivor: right, merged: left };
}

function sharedAdjacentLabels(
  left: GraphProjectionNodeView,
  right: GraphProjectionNodeView,
): string[] {
  const leftLabels = new Set(left.adjacency.map((item) => normalizeMergeLabel(item.label)));
  return right.adjacency
    .map((item) => item.label)
    .filter((label) => leftLabels.has(normalizeMergeLabel(label)));
}

function stripLeadingArticle(text: string): string {
  return text.replace(/^(the|a|an)\s+/, "");
}

function labelsSimilar(left: string, right: string): boolean {
  const leftNorm = normalizeMergeLabel(left);
  const rightNorm = normalizeMergeLabel(right);
  if (leftNorm === rightNorm) {
    return true;
  }
  const leftCollapsed = stripLeadingArticle(collapsePunctuationVariants(left));
  const rightCollapsed = stripLeadingArticle(collapsePunctuationVariants(right));
  return Boolean(leftCollapsed && leftCollapsed === rightCollapsed);
}

function isIdentitySignalFeature(feature: string): boolean {
  return (
    feature.startsWith("Exact normalized label") ||
    feature.startsWith("Very similar label") ||
    feature.startsWith("Alias overlap") ||
    feature.startsWith("Primary label matches alias") ||
    feature.startsWith("Same source anchor")
  );
}

function isPlayerCharacterNode(node: GraphProjectionNodeView): boolean {
  const kind = (node.kind || "").trim().toLowerCase();
  const role = (node.role || "").trim().toLowerCase();
  if (kind === "pc" || role === "pc") {
    return true;
  }
  return node.source_domains.some(
    (domain) => domain === "party_pc" || domain === "party",
  );
}

function normalizedAliasSet(node: GraphProjectionNodeView): Set<string> {
  const aliases = new Set<string>();
  for (const alias of node.aliases) {
    const normalized = normalizeMergeLabel(alias);
    if (normalized) {
      aliases.add(normalized);
    }
    const stripped = stripLeadingArticle(normalized);
    if (stripped) {
      aliases.add(stripped);
    }
  }
  return aliases;
}

function labelInAliasCrossMatch(
  left: GraphProjectionNodeView,
  right: GraphProjectionNodeView,
): boolean {
  const leftLabels = [
    normalizeMergeLabel(left.label),
    stripLeadingArticle(normalizeMergeLabel(left.label)),
  ].filter(Boolean);
  const rightLabels = [
    normalizeMergeLabel(right.label),
    stripLeadingArticle(normalizeMergeLabel(right.label)),
  ].filter(Boolean);
  const leftAliases = normalizedAliasSet(left);
  const rightAliases = normalizedAliasSet(right);

  for (const label of leftLabels) {
    if (rightAliases.has(label)) {
      return true;
    }
  }
  for (const label of rightLabels) {
    if (leftAliases.has(label)) {
      return true;
    }
  }
  return false;
}

function hasPcIdentitySignal(
  left: GraphProjectionNodeView,
  right: GraphProjectionNodeView,
): boolean {
  return (
    labelsSimilar(left.label, right.label) || labelInAliasCrossMatch(left, right)
  );
}

function matchedFeaturesForPair(
  left: GraphProjectionNodeView,
  right: GraphProjectionNodeView,
): { features: string[]; confidence: GraphObjectMergeCandidateConfidence; reason: string } {
  const leftTokens = nodeTokens(left);
  const rightTokens = nodeTokens(right);
  const features: string[] = [];
  const warnings: string[] = [];

  const leftNorm = normalizeMergeLabel(left.label);
  const rightNorm = normalizeMergeLabel(right.label);

  if (leftNorm && leftNorm === rightNorm) {
    features.push("Exact normalized label match");
  } else if (labelsSimilar(left.label, right.label)) {
    features.push("Very similar label after punctuation/case trimming");
  }

  const aliasOverlap = [...leftTokens].filter(
    (token) =>
      rightTokens.has(token) &&
      token !== leftNorm &&
      token !== rightNorm &&
      token !== stripLeadingArticle(leftNorm) &&
      token !== stripLeadingArticle(rightNorm),
  );
  if (aliasOverlap.length) {
    features.push(`Alias overlap: “${aliasOverlap[0]}”`);
  }

  if (labelInAliasCrossMatch(left, right)) {
    features.push("Primary label matches alias on other object");
  }

  if (left.kind && right.kind && left.kind === right.kind) {
    features.push(`Same kind/role: ${left.kind}${left.role ? ` / ${left.role}` : ""}`);
  } else if (left.kind && right.kind && left.kind !== right.kind) {
    warnings.push(`Kind mismatch: ${left.kind} vs ${right.kind}`);
  }

  const leftAnchor = normalizeMergeLabel(left.source_anchor_text ?? "");
  const rightAnchor = normalizeMergeLabel(right.source_anchor_text ?? "");
  if (leftAnchor && leftAnchor === rightAnchor) {
    features.push("Same source anchor text");
  }

  const sharedAdjacency = sharedAdjacentLabels(left, right);
  if (sharedAdjacency.length) {
    features.push(`Shared adjacent object: ${sharedAdjacency[0]}`);
  }

  const identityFeatures = features.filter(isIdentitySignalFeature);

  if (identityFeatures.length === 0) {
    return {
      features: [],
      confidence: "low",
      reason: "No identity duplicate signals matched",
    };
  }

  const matchedFeatures = [...features, ...warnings];

  let confidence: GraphObjectMergeCandidateConfidence = "low";
  if (features.some((feature) => feature.startsWith("Exact normalized label"))) {
    confidence = "high";
  } else if (
    features.some((feature) => feature.startsWith("Alias overlap")) ||
    features.some((feature) => feature.startsWith("Primary label matches alias")) ||
    features.some((feature) => feature.startsWith("Same source anchor")) ||
    features.some((feature) => feature.startsWith("Very similar label"))
  ) {
    confidence = "high";
  } else if (features.some((feature) => feature.startsWith("Shared adjacent"))) {
    confidence = "medium";
  }

  if (warnings.some((feature) => feature.startsWith("Kind mismatch"))) {
    confidence = confidence === "high" ? "medium" : "low";
  }

  const reason = matchedFeatures.join("; ");

  return { features: matchedFeatures, confidence, reason };
}

function objectRefFromNode(node: GraphProjectionNodeView): GraphObjectAuthoringObjectRef {
  return buildObjectRefFromInspectedNode({
    node_id: node.node_id,
    label: node.label,
    kind: node.kind,
    role: node.role,
    graphScope: inferCandidateGraphScopeFromProjectionNode(node),
    sourceLabel: node.source_anchor_text ?? null,
  });
}

export interface BuildMergeCandidateOptions {
  /** Stricter rules for bulk recap scans (default manual review is permissive). */
  forBulkScan?: boolean;
}

export function buildMergeCandidateFromNodes(
  left: GraphProjectionNodeView,
  right: GraphProjectionNodeView,
  options?: BuildMergeCandidateOptions,
): GraphObjectMergeCandidate | null {
  if (!left.node_id || !right.node_id || left.node_id === right.node_id) {
    return null;
  }

  const { survivor, merged } = chooseSurvivor(left, right);
  const { features, confidence, reason } = matchedFeaturesForPair(survivor, merged);
  if (features.length === 0) {
    return null;
  }

  if (options?.forBulkScan) {
    if (
      isPlayerCharacterNode(survivor) &&
      isPlayerCharacterNode(merged) &&
      !hasPcIdentitySignal(survivor, merged)
    ) {
      return null;
    }
    if (confidence === "low") {
      return null;
    }
  }

  const survivorRef = objectRefFromNode(survivor);
  const mergedRef = objectRefFromNode(merged);
  if (areSameObjectRef(survivorRef, mergedRef)) {
    return null;
  }

  return {
    candidateId: `${survivor.node_id}::${merged.node_id}`,
    survivorObjectRef: survivorRef,
    mergedObjectRef: mergedRef,
    confidence,
    matchedFeatures: features,
    reason,
  };
}

export function buildMergeCandidateFromPillAndExisting(
  pillNode: GraphProjectionNodeView,
  existingNode: GraphProjectionNodeView,
): GraphObjectMergeCandidate | null {
  return buildMergeCandidateFromNodes(pillNode, existingNode);
}

function projectionNodeFromProposal(
  proposal: Extract<GraphObjectAuthoringProposal, { proposalKind: "object" }>,
): GraphProjectionNodeView {
  return {
    node_id: proposal.localProposalId,
    label: proposal.objectRef.label,
    kind: proposal.objectRef.kind ?? "entity",
    role: proposal.objectRef.role ?? "authored",
    aliases: proposal.objectRef.aliases,
    source_domains: ["authored_overlay"],
    evidence_badges: [],
    adjacency: [],
    anchored_to_focus_session: false,
    authored: true,
    source_anchor_text: proposal.selection?.selectedText ?? null,
  };
}

export function buildMergeCandidateFromOverlapWarning(
  proposal: GraphObjectAuthoringProposal,
  warning: GraphObjectAuthoringOverlapWarning,
  nodeViews: Record<string, GraphProjectionNodeView> | null | undefined,
): GraphObjectMergeCandidate | null {
  if (!warning.relatedNodeId || !nodeViews) {
    return null;
  }
  const relatedNode = nodeViews[warning.relatedNodeId];
  if (!relatedNode) {
    return null;
  }

  let counterpart: GraphProjectionNodeView | null = null;
  if (proposal.proposalKind === "object") {
    counterpart = projectionNodeFromProposal(proposal);
  } else if (
    proposal.proposalKind === "link_existing" &&
    proposal.existingObjectRef.nodeId
  ) {
    counterpart = nodeViews[proposal.existingObjectRef.nodeId] ?? null;
  }

  if (!counterpart) {
    return null;
  }

  return buildMergeCandidateFromNodes(relatedNode, counterpart);
}

export function findProjectionMergeCandidates(
  nodeViews: Record<string, GraphProjectionNodeView> | null | undefined,
): GraphObjectMergeCandidate[] {
  if (!nodeViews) {
    return [];
  }

  const nodes = Object.values(nodeViews);
  const candidates: GraphObjectMergeCandidate[] = [];
  const seen = new Set<string>();

  for (let index = 0; index < nodes.length; index += 1) {
    for (let inner = index + 1; inner < nodes.length; inner += 1) {
      const candidate = buildMergeCandidateFromNodes(nodes[index], nodes[inner], {
        forBulkScan: true,
      });
      if (!candidate) {
        continue;
      }
      const key = `${candidate.survivorObjectRef.nodeId}::${candidate.mergedObjectRef.nodeId}`;
      if (seen.has(key)) {
        continue;
      }
      seen.add(key);
      candidates.push(candidate);
    }
  }

  return candidates.sort((left, right) => {
    const rank = { high: 0, medium: 1, low: 2 };
    const leftRank = rank[left.confidence];
    const rightRank = rank[right.confidence];
    if (leftRank !== rightRank) {
      return leftRank - rightRank;
    }
    return left.survivorObjectRef.label.localeCompare(right.survivorObjectRef.label);
  });
}
