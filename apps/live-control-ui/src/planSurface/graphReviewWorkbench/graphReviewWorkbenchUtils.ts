import type {
  GoldReviewSessionSummary,
  GraphIngestRunSummary,
  GraphReviewLane,
  WorldGraphSessionSummary,
} from "../../api/types";
import { requestedSessionFromLocation } from "../graphGoldReview/graphGoldReviewUtils";
import { goldReviewSessionLabel } from "../sessionCampaignContext";

export interface GraphReviewCatalogSession {
  campaignId: string;
  sessionId: string;
  sessionNumber: number | null;
  availableRuns: GraphIngestRunSummary[];
  hasGold: boolean;
  hasReviewableRun: boolean;
  /** World Graph browse row — Load recap uses this, not ingest runs. */
  browseable: boolean;
  recapAvailable: boolean;
  contributionCount: number;
  headRevisionId: string | null;
  goldFixtureId: string | null;
  goldManifestPath: string | null;
  goldGraphPath: string | null;
  goldCounts: Record<string, number>;
}

function parseSessionNumber(sessionId: string): number | null {
  const match = sessionId.match(/^session-(\d+)$/i);
  if (!match) return null;
  const value = Number.parseInt(match[1], 10);
  return Number.isFinite(value) && value > 0 ? value : null;
}

function catalogSessionKey(campaignId: string, sessionId: string): string {
  return `${campaignId}::${sessionId}`;
}

export function catalogSessionLabel(session: GraphReviewCatalogSession): string {
  return goldReviewSessionLabel({
    session_id: session.sessionId,
    session_number: session.sessionNumber,
  });
}

/** GM-facing session label for the workbench header — no run pipeline metadata. */
export function formatCompactAppliedLoadLabel(
  session: GraphReviewCatalogSession | null,
): string | null {
  if (!session) return null;
  return `${catalogSessionLabel(session)} · ${session.campaignId}`;
}

export function hasCatalogReviewableRun(
  session: GraphReviewCatalogSession,
): boolean {
  if (session.browseable && session.recapAvailable) return true;
  return session.availableRuns.some((run) => run.preview_union_available);
}

export function buildWorldGraphBrowseCatalog(
  sessions: WorldGraphSessionSummary[],
): GraphReviewCatalogSession[] {
  return sessions
    .map((session) => ({
      campaignId: session.campaign_id,
      sessionId: session.session_id,
      sessionNumber: session.session_number ?? parseSessionNumber(session.session_id),
      availableRuns: [] as GraphIngestRunSummary[],
      hasGold: false,
      hasReviewableRun: session.browseable && session.recap_available,
      browseable: session.browseable,
      recapAvailable: session.recap_available,
      contributionCount: session.contribution_count,
      headRevisionId: session.head_revision_id,
      goldFixtureId: null,
      goldManifestPath: null,
      goldGraphPath: null,
      goldCounts: {},
    }))
    .sort((left, right) => {
      const campaignCompare = left.campaignId.localeCompare(right.campaignId);
      if (campaignCompare !== 0) return campaignCompare;
      const leftNumber = left.sessionNumber ?? Number.MAX_SAFE_INTEGER;
      const rightNumber = right.sessionNumber ?? Number.MAX_SAFE_INTEGER;
      if (leftNumber !== rightNumber) return leftNumber - rightNumber;
      return left.sessionId.localeCompare(right.sessionId);
    });
}

export function buildGraphReviewCatalog(
  runs: GraphIngestRunSummary[],
  goldSessions: GoldReviewSessionSummary[] = [],
): GraphReviewCatalogSession[] {
  const byKey = new Map<string, GraphReviewCatalogSession>();

  for (const goldSession of goldSessions) {
    if (!goldSession.campaign_id) continue;
    const key = catalogSessionKey(goldSession.campaign_id, goldSession.session_id);
    byKey.set(key, {
      campaignId: goldSession.campaign_id,
      sessionId: goldSession.session_id,
      sessionNumber: goldSession.session_number ?? parseSessionNumber(goldSession.session_id),
      availableRuns: [...goldSession.available_runs],
      hasGold: true,
      hasReviewableRun: goldSession.available_runs.some(
        (run) => run.preview_union_available,
      ),
      browseable: false,
      recapAvailable: false,
      contributionCount: 0,
      headRevisionId: null,
      goldFixtureId: goldSession.gold_fixture_id,
      goldManifestPath: goldSession.gold_manifest_path,
      goldGraphPath: goldSession.gold_graph_path,
      goldCounts: { ...goldSession.gold_counts },
    });
  }

  for (const ingestRun of runs) {
    const key = catalogSessionKey(ingestRun.campaign_id, ingestRun.session_id);
    const existing = byKey.get(key);
    if (existing) {
      const mergedRuns = new Map<string, GraphIngestRunSummary>();
      for (const entry of [...existing.availableRuns, ingestRun]) {
        mergedRuns.set(entry.manifest_path, entry);
      }
      existing.availableRuns = Array.from(mergedRuns.values());
      existing.hasReviewableRun = existing.availableRuns.some(
        (run) => run.preview_union_available,
      );
      continue;
    }
    byKey.set(key, {
      campaignId: ingestRun.campaign_id,
      sessionId: ingestRun.session_id,
      sessionNumber: parseSessionNumber(ingestRun.session_id),
      availableRuns: [ingestRun],
      hasGold: false,
      hasReviewableRun: ingestRun.preview_union_available,
      browseable: false,
      recapAvailable: false,
      contributionCount: 0,
      headRevisionId: null,
      goldFixtureId: null,
      goldManifestPath: null,
      goldGraphPath: null,
      goldCounts: {},
    });
  }

  return Array.from(byKey.values()).sort((left, right) => {
    const campaignCompare = left.campaignId.localeCompare(right.campaignId);
    if (campaignCompare !== 0) return campaignCompare;
    const leftNumber = left.sessionNumber ?? Number.MAX_SAFE_INTEGER;
    const rightNumber = right.sessionNumber ?? Number.MAX_SAFE_INTEGER;
    if (leftNumber !== rightNumber) return leftNumber - rightNumber;
    return left.sessionId.localeCompare(right.sessionId);
  });
}

export const GRAPH_REVIEW_RUNS_CHANGED_EVENT = "dmb:graph-runs-changed";

export function catalogSessionsForReviewCampaign(
  sessions: GraphReviewCatalogSession[],
  selectedCampaignId: string,
): GraphReviewCatalogSession[] {
  return sessions.filter((session) => session.campaignId === selectedCampaignId);
}

export function catalogSessionToGoldLane(
  session: GraphReviewCatalogSession,
): GraphReviewLane | null {
  if (!session.hasGold || !session.goldFixtureId) return null;
  return goldSessionToLane({
    session_id: session.sessionId,
    session_number: session.sessionNumber ?? 0,
    campaign_id: session.campaignId,
    gold_fixture_id: session.goldFixtureId,
    gold_manifest_path: session.goldManifestPath ?? "",
    gold_graph_path: session.goldGraphPath ?? "",
    gold_counts: session.goldCounts,
    available_runs: session.availableRuns,
  });
}

function countFrom(
  counts: Record<string, number> | undefined,
  ...keys: string[]
): number | undefined {
  for (const key of keys) {
    const value = counts?.[key];
    if (typeof value === "number" && Number.isFinite(value)) return value;
  }
  return undefined;
}

export function unknownIfBlank(value: string | null | undefined): string {
  return value?.trim() || "Unknown";
}

export function yesNo(value: boolean | null | undefined): string {
  return value ? "Yes" : "No";
}

export function goldSessionToLane(
  session: GoldReviewSessionSummary,
): GraphReviewLane {
  return {
    laneId: `gold:${session.campaign_id}:${session.session_id}:${session.gold_fixture_id}`,
    role: "gold",
    sourceKind: "gold_fixture",
    label: `Gold · ${session.gold_fixture_id}`,
    campaignId: session.campaign_id,
    sessionId: session.session_id,
    manifestPath: session.gold_manifest_path,
    goldPath: session.gold_graph_path,
    status:
      session.gold_manifest_path && session.gold_graph_path
        ? "available"
        : "unknown",
    counts: {
      nodes: countFrom(session.gold_counts, "nodes", "node_count") ?? 0,
      edges: countFrom(session.gold_counts, "edges", "edge_count") ?? 0,
      beats: countFrom(session.gold_counts, "beats", "beat_count"),
      evidenceRefs: countFrom(
        session.gold_counts,
        "evidence_refs",
        "evidence_ref_count",
        "evidenceRefs",
      ),
    },
    metadata: {
      vocabularyMode: "unknown",
      diagnostics: {
        goldFixtureId: session.gold_fixture_id,
      },
    },
  };
}

export function graphIngestRunToLane(
  run: GraphIngestRunSummary,
): GraphReviewLane {
  return {
    laneId: `live:${run.campaign_id}:${run.session_id}:${run.manifest_path}`,
    role: "live",
    sourceKind: "graph_ingest_run",
    label: run.run_label || run.manifest_path,
    campaignId: run.campaign_id,
    sessionId: run.session_id,
    manifestPath: run.manifest_path,
    artifactPath: run.run_dir,
    previewUnionPath: run.preview_union_store_path ?? undefined,
    status: run.preview_union_available ? "available" : "missing_projection",
    counts: {
      nodes: run.node_count ?? 0,
      edges: run.edge_count ?? 0,
      evidenceRefs: run.evidence_ref_count ?? 0,
    },
    metadata: {
      runId: run.run_id ?? undefined,
      generatedAt:
        run.generated_at ?? run.updated_at ?? run.created_at ?? undefined,
      modelId: run.model_id ?? undefined,
      extractionProfile: run.extraction_profile ?? undefined,
      extractionMode: run.extraction_mode ?? undefined,
      vocabularyMode: run.vocabulary_mode ?? "unknown",
      runnerOptions: run.runner_options_summary,
      diagnostics: run.diagnostics_summary,
    },
  };
}

export function hasReviewableProjection(
  session: GoldReviewSessionSummary,
): boolean {
  return session.available_runs.some((run) => run.preview_union_available);
}

export function pickDefaultWorkbenchSession(
  sessions: GoldReviewSessionSummary[],
  requestedSessionId: string | null = requestedSessionFromLocation(),
  fallbackSessionId?: string,
): GoldReviewSessionSummary | null {
  if (!sessions.length) return null;
  const reviewableSessions = sessions.filter(hasReviewableProjection);
  const pickFrom = reviewableSessions.length ? reviewableSessions : sessions;
  if (requestedSessionId) {
    const requested = pickFrom.find(
      (session) => session.session_id === requestedSessionId,
    );
    if (requested) return requested;
  }
  if (fallbackSessionId) {
    const fallback = pickFrom.find(
      (session) => session.session_id === fallbackSessionId,
    );
    if (fallback) return fallback;
  }
  return pickFrom[0];
}

export function pickDefaultCatalogSession(
  sessions: GraphReviewCatalogSession[],
  requestedSessionId: string | null = requestedSessionFromLocation(),
  fallbackSessionId?: string,
): GraphReviewCatalogSession | null {
  if (!sessions.length) return null;
  const reviewableSessions = sessions.filter(hasCatalogReviewableRun);
  const pickFrom = reviewableSessions.length ? reviewableSessions : sessions;
  if (requestedSessionId) {
    const requested = pickFrom.find(
      (session) => session.sessionId === requestedSessionId,
    );
    if (requested) return requested;
  }
  if (fallbackSessionId) {
    const fallback = pickFrom.find(
      (session) => session.sessionId === fallbackSessionId,
    );
    if (fallback) return fallback;
  }
  return pickFrom[0];
}

export function pickDefaultWorkbenchRun(
  runs: GraphIngestRunSummary[],
): GraphIngestRunSummary | null {
  if (!runs.length) return null;
  return runs.find((run) => run.preview_union_available) ?? runs[0];
}
