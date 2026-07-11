import type {
  GoldReviewCompareResponse,
  GoldReviewMissEntry,
  GoldReviewSessionSummary,
} from "../../api/types";

export type GoldReviewObjectKind =
  | "nodes"
  | "edges"
  | "beats"
  | "proposed_writes"
  | "ignored_items"
  | "deferred_items";

export interface GoldReviewSelection {
  objectKind: GoldReviewObjectKind;
  objectId: string;
}

export interface GoldReviewMissGroup {
  kind: GoldReviewObjectKind;
  label: string;
  missing: GoldReviewMissEntry[];
  extra: GoldReviewMissEntry[];
}

const KIND_LABELS: Record<GoldReviewObjectKind, string> = {
  nodes: "Nodes",
  edges: "Edges",
  beats: "Beats",
  proposed_writes: "Proposed writes",
  ignored_items: "Ignored",
  deferred_items: "Deferred",
};

export function objectKindLabel(kind: GoldReviewObjectKind): string {
  return KIND_LABELS[kind];
}

export function formatRecall(value: number | undefined): string {
  if (value == null || Number.isNaN(value)) return "n/a";
  return `${Math.round(value * 1000) / 10}%`;
}

export function requestedSessionFromLocation(): string | null {
  if (typeof window === "undefined") return null;
  return new URLSearchParams(window.location.search).get("session")?.trim() || null;
}

export function syncGoldReviewUrl(sessionId: string, campaignId?: string): void {
  if (typeof window === "undefined") return;
  const params = new URLSearchParams(window.location.search);
  params.set("tool", "graph-gold-review");
  params.set("session", sessionId);
  if (campaignId) {
    params.set("campaign", campaignId);
  }
  window.history.replaceState({}, "", `/plan?${params.toString()}`);
}

export function pickDefaultSession(
  sessions: GoldReviewSessionSummary[],
  requestedSessionId: string | null,
  fallbackSessionId: string,
): string {
  if (requestedSessionId && sessions.some((session) => session.session_id === requestedSessionId)) {
    return requestedSessionId;
  }
  return sessions.at(-1)?.session_id ?? fallbackSessionId;
}

export function pickDefaultManifestPath(session: GoldReviewSessionSummary | undefined): string | null {
  return session?.available_runs[0]?.manifest_path ?? null;
}

export function buildMissGroups(compare: GoldReviewCompareResponse | null): GoldReviewMissGroup[] {
  if (!compare) return [];
  const coverage = compare.comparison.coverage;
  const kinds: GoldReviewObjectKind[] = [
    "nodes",
    "edges",
    "beats",
    "proposed_writes",
    "ignored_items",
    "deferred_items",
  ];
  return kinds.map((kind) => ({
    kind,
    label: objectKindLabel(kind),
    missing: (coverage[`missing_gold_${kind}`] as GoldReviewMissEntry[] | undefined) ?? [],
    extra: (coverage[`extra_candidate_${kind}`] as GoldReviewMissEntry[] | undefined) ?? [],
  }));
}

export function headlineScores(compare: GoldReviewCompareResponse | null): Array<{ label: string; value: string }> {
  if (!compare) return [];
  const scores = compare.comparison.scores;
  return [
    { label: "Node recall", value: formatRecall(scores.node_recall) },
    { label: "Edge recall", value: formatRecall(scores.edge_recall) },
    { label: "Beat recall", value: formatRecall(scores.beat_recall) },
    { label: "Write recall", value: formatRecall(scores.proposed_write_recall) },
  ];
}

export function coverageRows(compare: GoldReviewCompareResponse | null): Array<{
  kind: string;
  goldTotal: number;
  liveTotal: number;
  matched: number;
}> {
  if (!compare) return [];
  const coverage = compare.comparison.coverage;
  return buildMissGroups(compare).map((group) => ({
    kind: group.label,
    goldTotal: Number(coverage[`gold_${group.kind}_total`] ?? 0),
    liveTotal: Number(coverage[`candidate_${group.kind}_total`] ?? 0),
    matched: Array.isArray(coverage[`matched_${group.kind}`])
      ? (coverage[`matched_${group.kind}`] as string[]).length
      : 0,
  }));
}
