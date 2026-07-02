import type { GoldReviewSessionSummary, GraphIngestRunSummary, GraphReviewLane } from "../../api/types";
import { requestedSessionFromLocation } from "../graphGoldReview/graphGoldReviewUtils";

function countFrom(counts: Record<string, number> | undefined, ...keys: string[]): number | undefined {
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

export function goldSessionToLane(session: GoldReviewSessionSummary): GraphReviewLane {
  return {
    laneId: `gold:${session.campaign_id}:${session.session_id}:${session.gold_fixture_id}`,
    role: "gold",
    sourceKind: "gold_fixture",
    label: `Gold · ${session.gold_fixture_id}`,
    campaignId: session.campaign_id,
    sessionId: session.session_id,
    manifestPath: session.gold_manifest_path,
    goldPath: session.gold_graph_path,
    status: session.gold_manifest_path && session.gold_graph_path ? "available" : "unknown",
    counts: {
      nodes: countFrom(session.gold_counts, "nodes", "node_count") ?? 0,
      edges: countFrom(session.gold_counts, "edges", "edge_count") ?? 0,
      beats: countFrom(session.gold_counts, "beats", "beat_count"),
      evidenceRefs: countFrom(session.gold_counts, "evidence_refs", "evidence_ref_count", "evidenceRefs"),
    },
    metadata: {
      vocabularyMode: "unknown",
      diagnostics: {
        goldFixtureId: session.gold_fixture_id,
      },
    },
  };
}

export function graphIngestRunToLane(run: GraphIngestRunSummary): GraphReviewLane {
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
      generatedAt: run.generated_at ?? run.updated_at ?? run.created_at ?? undefined,
      modelId: run.model_id ?? undefined,
      extractionProfile: run.extraction_profile ?? undefined,
      extractionMode: run.extraction_mode ?? undefined,
      vocabularyMode: run.vocabulary_mode ?? "unknown",
      runnerOptions: run.runner_options_summary,
      diagnostics: run.diagnostics_summary,
    },
  };
}

export function pickDefaultWorkbenchSession(
  sessions: GoldReviewSessionSummary[],
  requestedSessionId: string | null = requestedSessionFromLocation(),
  fallbackSessionId?: string,
): GoldReviewSessionSummary | null {
  if (!sessions.length) return null;
  if (requestedSessionId) {
    const requested = sessions.find((session) => session.session_id === requestedSessionId);
    if (requested) return requested;
  }
  if (fallbackSessionId) {
    const fallback = sessions.find((session) => session.session_id === fallbackSessionId);
    if (fallback) return fallback;
  }
  return sessions[0];
}

export function pickDefaultWorkbenchRun(runs: GraphIngestRunSummary[]): GraphIngestRunSummary | null {
  if (!runs.length) return null;
  return runs.find((run) => run.preview_union_available) ?? runs[0];
}
