/**
 * Graph Review carries two jobs. They are never the same state.
 *
 * PublishedMemoryBrowseContext != GraphReviewWriteAuthority
 */

import {
  requestedCampaignFromLocation,
  resolveInitialReviewCampaignId,
} from "../sessionCampaignContext";
import type { GraphReviewExactRunHandoff } from "./graphReviewRunSelection";

export type PublishedMemoryAdmissibility = "gm" | "pending" | "unknown";

export interface PublishedMemoryBrowseContext {
  worldId: string | null;
  campaignId: string;
  sessionId: string;
  revisionPin: string | null;
  admissibility: PublishedMemoryAdmissibility;
}

export interface ExactRunAuthority {
  kind: "exact_run";
  extractionRunId: string;
  sourceArtifactId: string;
  campaignId: string | null;
  sessionId: string | null;
}

export interface ExplicitAuthoringAuthority {
  kind: "explicit_authoring";
  runId: string;
  campaignId: string;
  sessionId: string;
}

export type GraphReviewWriteAuthority =
  | ExactRunAuthority
  | ExplicitAuthoringAuthority
  | null;

export function requestedBrowseSessionId(
  search: string | null | undefined,
  fallbackSessionId: string,
): string {
  if (search == null) return fallbackSessionId;
  const session = new URLSearchParams(search).get("session")?.trim();
  return session || fallbackSessionId;
}

export function resolvePublishedMemoryBrowseContext(input: {
  fallbackCampaignId: string;
  fallbackSessionId: string;
  search?: string | null;
}): PublishedMemoryBrowseContext {
  const search =
    input.search ?? (typeof window !== "undefined" ? window.location.search : "");
  return {
    worldId: null,
    campaignId: resolveInitialReviewCampaignId(
      input.fallbackCampaignId,
      requestedCampaignFromLocation(search),
    ),
    sessionId: requestedBrowseSessionId(search, input.fallbackSessionId),
    revisionPin: null,
    admissibility: "unknown",
  };
}

export function resolveGraphReviewWriteAuthority(input: {
  exactHandoff: GraphReviewExactRunHandoff | null;
  exactHandoffErrors: readonly string[];
  exactRun: {
    run_id: string;
    source_artifact_id: string;
    campaign_id?: string | null;
    session_id?: string | null;
  } | null;
  exactRunStatus: "idle" | "loading" | "ready" | "error";
}): GraphReviewWriteAuthority {
  if (!input.exactHandoff) return null;
  if (input.exactHandoffErrors.length > 0) return null;
  if (input.exactRunStatus !== "ready" || !input.exactRun) return null;
  const sourceArtifactId = input.exactRun.source_artifact_id.trim();
  if (!sourceArtifactId) return null;
  if (input.exactRun.run_id !== input.exactHandoff.extractionRunId) return null;
  return {
    kind: "exact_run",
    extractionRunId: input.exactRun.run_id,
    sourceArtifactId,
    campaignId: input.exactRun.campaign_id?.trim() || null,
    sessionId: input.exactRun.session_id?.trim() || null,
  };
}
