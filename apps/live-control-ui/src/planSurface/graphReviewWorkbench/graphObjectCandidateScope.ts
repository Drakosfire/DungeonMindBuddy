import type {
  GraphObjectCandidateScope,
  GraphReviewExistingObjectCandidate,
} from "../../api/types";

export const GRAPH_OBJECT_CANDIDATE_SCOPE_ORDER: GraphObjectCandidateScope[] = [
  "authored_overlay",
  "current_recap_projection",
  "party_pc",
  "worldbuilding",
  "campaign_memory",
  "gm_private",
];

export const GRAPH_OBJECT_CANDIDATE_SCOPE_LABELS: Record<GraphObjectCandidateScope, string> = {
  current_recap_projection: "Current recap",
  authored_overlay: "Authored memory",
  campaign_memory: "Campaign memory",
  worldbuilding: "Worldbuilding",
  party_pc: "Party / PCs",
  gm_private: "GM private",
};

export function candidateScopeLabel(
  candidate: Pick<GraphReviewExistingObjectCandidate, "graph_scope" | "source_label">,
): string {
  if (candidate.source_label) {
    return candidate.source_label;
  }
  if (candidate.graph_scope) {
    return GRAPH_OBJECT_CANDIDATE_SCOPE_LABELS[candidate.graph_scope];
  }
  return "Unknown source";
}

export function formatResolverCandidateLabel(
  candidate: GraphReviewExistingObjectCandidate,
): string {
  const kindSuffix = candidate.kind ? ` · ${candidate.kind}` : "";
  const aliasSuffix =
    candidate.aliases && candidate.aliases.length > 0
      ? ` · aliases: ${candidate.aliases.join(", ")}`
      : "";
  return `${candidate.label}${kindSuffix}${aliasSuffix}`;
}

export function formatResolverCandidateMeta(
  candidate: GraphReviewExistingObjectCandidate,
): string {
  return `${candidateScopeLabel(candidate)} · ${candidate.reason}`;
}

export function groupCandidatesByScope(
  candidates: GraphReviewExistingObjectCandidate[],
): Array<{ scope: GraphObjectCandidateScope | "unknown"; candidates: GraphReviewExistingObjectCandidate[] }> {
  const grouped = new Map<GraphObjectCandidateScope | "unknown", GraphReviewExistingObjectCandidate[]>();
  for (const candidate of candidates) {
    const scope = candidate.graph_scope ?? "unknown";
    const bucket = grouped.get(scope) ?? [];
    bucket.push(candidate);
    grouped.set(scope, bucket);
  }
  const orderedScopes = [
    ...GRAPH_OBJECT_CANDIDATE_SCOPE_ORDER.filter((scope) => grouped.has(scope)),
    ...(grouped.has("unknown") ? (["unknown"] as const) : []),
  ];
  return orderedScopes.map((scope) => ({
    scope,
    candidates: (grouped.get(scope) ?? []).sort((a, b) => b.score - a.score || a.label.localeCompare(b.label)),
  }));
}

export function resolverCandidateToInspectedNode(
  candidate: GraphReviewExistingObjectCandidate,
): {
  node_id: string;
  label: string;
  kind?: string | null;
  role?: string | null;
  aliases?: string[];
  authored?: boolean;
  graphScope?: string | null;
  sourceLabel?: string | null;
  sourceGraphId?: string | null;
  sourcePath?: string | null;
  visibility?: string | null;
} {
  return {
    node_id: candidate.candidate_id,
    label: candidate.label,
    kind: candidate.kind,
    role: candidate.role,
    aliases: candidate.aliases,
    authored: candidate.authored === true || candidate.graph_scope === "authored_overlay",
    graphScope: candidate.graph_scope ?? null,
    sourceLabel: candidate.source_label ?? candidateScopeLabel(candidate),
    sourceGraphId: candidate.source_graph_id ?? null,
    sourcePath: candidate.source_path ?? null,
    visibility: candidate.visibility ?? null,
  };
}
