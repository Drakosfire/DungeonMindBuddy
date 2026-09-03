import type {
  ExtractionRunRecord,
  GoldReviewSessionSummary,
  GraphIngestRunSummary,
  GraphReviewLane,
} from "../../api/types";
import { requestedSessionFromLocation } from "../graphGoldReview/graphGoldReviewUtils";
import { goldReviewSessionLabel } from "../sessionCampaignContext";

export interface GraphReviewCatalogRun {
  run: ExtractionRunRecord;
  compatibilityManifestPath: string | null;
  /**
   * Mirrors for existing live-state consumers outside this slice's write lease.
   * Product identity remains `run.run_id`; `manifest_path` is the Gold
   * compatibility locator after an exact canonical match, never catalog membership.
   */
  run_id: string;
  run_label: string;
  status: string;
  manifest_path: string;
  preview_union_store_path: string | null;
  next_actions: string[];
  promotable: boolean;
  promotable_reason: string | null;
}

export function toCatalogRun(
  run: ExtractionRunRecord,
  compatibilityManifestPath: string | null = null,
): GraphReviewCatalogRun {
  return {
    run,
    compatibilityManifestPath,
    run_id: run.run_id,
    run_label: run.run_id,
    status: run.status,
    manifest_path: compatibilityManifestPath ?? "",
    preview_union_store_path: null,
    next_actions: [],
    promotable: isCatalogRunDefaultCandidate(run),
    promotable_reason: null,
  };
}

export interface GraphReviewCatalogSession {
  campaignId: string;
  sessionId: string;
  sessionNumber: number | null;
  availableRuns: GraphReviewCatalogRun[];
  hasGold: boolean;
  hasReviewableRun: boolean;
  goldFixtureId: string | null;
  goldManifestPath: string | null;
  goldGraphPath: string | null;
  goldCounts: Record<string, number>;
}

const INSPECTABLE_STATUSES = new Set(["reviewable", "promoted"]);
const DEFAULT_PROMOTABLE_STATUSES = new Set(["reviewable"]);

export function catalogRunStatus(run: ExtractionRunRecord): string {
  return (run.status ?? "").trim().toLowerCase();
}

export function isCatalogRunInspectable(run: ExtractionRunRecord): boolean {
  return INSPECTABLE_STATUSES.has(catalogRunStatus(run));
}

export function isCatalogRunDefaultCandidate(run: ExtractionRunRecord): boolean {
  return DEFAULT_PROMOTABLE_STATUSES.has(catalogRunStatus(run));
}

export function isRecapCatalogRun(run: ExtractionRunRecord): boolean {
  return (
    run.source_domain === "recap"
    && Boolean(run.campaign_id?.trim())
    && Boolean(run.session_id?.trim())
  );
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
  return session.availableRuns.some((entry) => isCatalogRunInspectable(entry.run));
}

function goldCompatibilityLocator(
  goldSessions: GoldReviewSessionSummary[],
  run: ExtractionRunRecord,
): string | null {
  const campaignId = run.campaign_id?.trim() ?? "";
  const sessionId = run.session_id?.trim() ?? "";
  const runId = run.run_id.trim();
  if (!campaignId || !sessionId || !runId) return null;
  for (const goldSession of goldSessions) {
    if (goldSession.campaign_id !== campaignId || goldSession.session_id !== sessionId) {
      continue;
    }
    const match = goldSession.available_runs.find((legacy) => {
      const legacyRunId = (legacy.run_id ?? "").trim();
      const legacyCampaign = (legacy.campaign_id ?? "").trim();
      const legacySession = (legacy.session_id ?? "").trim();
      return (
        legacyRunId === runId
        && legacyCampaign === campaignId
        && legacySession === sessionId
      );
    });
    const locator = match?.manifest_path?.trim() ?? "";
    if (locator) return locator;
  }
  return null;
}

export function buildGraphReviewCatalog(
  canonicalRuns: ExtractionRunRecord[],
  goldSessions: GoldReviewSessionSummary[] = [],
): GraphReviewCatalogSession[] {
  const byKey = new Map<string, GraphReviewCatalogSession>();
  const byRunId = new Map<string, GraphReviewCatalogRun>();

  for (const run of canonicalRuns) {
    if (!isRecapCatalogRun(run)) continue;
    const runId = run.run_id.trim();
    if (byRunId.has(runId)) continue;
    const campaignId = run.campaign_id!.trim();
    const sessionId = run.session_id!.trim();
    const catalogRun = toCatalogRun(
      run,
      goldCompatibilityLocator(goldSessions, run),
    );
    byRunId.set(runId, catalogRun);
    const key = catalogSessionKey(campaignId, sessionId);
    const existing = byKey.get(key);
    if (existing) {
      existing.availableRuns.push(catalogRun);
      existing.hasReviewableRun = existing.availableRuns.some((entry) =>
        isCatalogRunInspectable(entry.run),
      );
      continue;
    }
    byKey.set(key, {
      campaignId,
      sessionId,
      sessionNumber: parseSessionNumber(sessionId),
      availableRuns: [catalogRun],
      hasGold: false,
      hasReviewableRun: isCatalogRunInspectable(run),
      goldFixtureId: null,
      goldManifestPath: null,
      goldGraphPath: null,
      goldCounts: {},
    });
  }

  for (const goldSession of goldSessions) {
    if (!goldSession.campaign_id) continue;
    const key = catalogSessionKey(goldSession.campaign_id, goldSession.session_id);
    const existing = byKey.get(key);
    if (!existing) continue;
    existing.hasGold = true;
    existing.goldFixtureId = goldSession.gold_fixture_id;
    existing.goldManifestPath = goldSession.gold_manifest_path;
    existing.goldGraphPath = goldSession.gold_graph_path;
    existing.goldCounts = { ...goldSession.gold_counts };
  }

  for (const session of byKey.values()) {
    session.availableRuns.sort((left, right) => left.run.run_id.localeCompare(right.run.run_id));
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
    available_runs: [],
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

export function catalogRunToLane(entry: GraphReviewCatalogRun): GraphReviewLane {
  const run = entry.run;
  const revision = (run as ExtractionRunRecord & { revision?: number }).revision;
  const rawStatus = catalogRunStatus(run);
  const laneStatus =
    rawStatus === "failed"
      ? "failed"
      : isCatalogRunInspectable(run)
        ? "available"
        : "unknown";
  return {
    laneId: `live:${run.campaign_id}:${run.session_id}:${run.run_id}`,
    role: "live",
    sourceKind: "graph_ingest_run",
    label: run.run_id,
    campaignId: run.campaign_id ?? "",
    sessionId: run.session_id ?? "",
    manifestPath: entry.compatibilityManifestPath ?? "",
    status: laneStatus,
    counts: {
      nodes: 0,
      edges: 0,
      evidenceRefs: 0,
    },
    metadata: {
      runId: run.run_id,
      generatedAt: run.updated_at ?? run.created_at ?? undefined,
      extractionProfile: run.profile_id ?? undefined,
      vocabularyMode: "unknown",
      diagnostics: {
        revision: revision ?? null,
        sourceArtifactId: run.source_artifact_id,
        sourceDomain: run.source_domain,
        canonicalStatus: run.status,
        compatibilityLocator: entry.compatibilityManifestPath,
      },
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
  runs: GraphReviewCatalogRun[],
): GraphReviewCatalogRun | null {
  if (!runs.length) return null;
  return (
    runs.find((entry) => isCatalogRunDefaultCandidate(entry.run))
    ?? runs.find((entry) => isCatalogRunInspectable(entry.run))
    ?? null
  );
}
