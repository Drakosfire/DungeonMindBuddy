/**
 * Pure DungeonMind graph-lens → Surface Information mapping (SI-3).
 *
 * Descriptor identity is exact-request identity. Authority revision belongs
 * on the observation, never on the descriptor. unrevisioned is not used.
 */

import { LiveApiError } from "../api/liveApi";
import type { WorldGraphProjection, WorldGraphProjectionRequest } from "../api/types";
import type {
  SurfaceInformationDescriptor,
  SurfaceInformationDiagnostic,
  SurfaceInformationObservedMetadata,
  SurfaceInformationReference,
  SurfaceInformationState,
} from "../surfaceInformation";
import { verifyWorldGraphProjectionResponse } from "../worldGraph/verifyWorldGraphProjectionResponse";
import { worldGraphProjectionRequestKey } from "../worldGraph/worldGraphProjectionRequestKey";

export const WORLD_GRAPH_LENS_INFORMATION_KIND = "world_graph_projection";
export const WORLD_GRAPH_LENS_PROVIDER_ID = "world_graph_lens_projection";

const MAX_SAFE_DIAGNOSTICS = 8;

export function worldGraphLensRequestKey(request: WorldGraphProjectionRequest): string {
  return worldGraphProjectionRequestKey(request);
}

export function worldGraphLensInformationDescriptor(
  request: WorldGraphProjectionRequest,
): SurfaceInformationDescriptor {
  const requestKey = worldGraphLensRequestKey(request);
  const scope: SurfaceInformationReference[] = [
    { kind: "campaign", id: request.campaignId },
    { kind: "scope_mode", id: request.scopeMode ?? "campaign" },
    { kind: "admissibility", id: request.admissibility },
  ];
  if (request.focus.kind === "session" && request.focus.sessionId) {
    scope.push({
      kind: "focus_campaign",
      id: request.focus.campaignId?.trim() || request.campaignId,
    });
    scope.push({ kind: "focus_session", id: request.focus.sessionId });
  }
  return {
    channelId: `world-graph-lens:${requestKey}`,
    informationKind: WORLD_GRAPH_LENS_INFORMATION_KIND,
    providerId: WORLD_GRAPH_LENS_PROVIDER_ID,
    authority: "dungeonmind",
    subject: { kind: "world", id: request.worldId },
    scope,
  };
}

function boundedDiagnostics(
  diagnostics: readonly SurfaceInformationDiagnostic[],
): readonly SurfaceInformationDiagnostic[] {
  return diagnostics.slice(0, MAX_SAFE_DIAGNOSTICS).map((diagnostic) => ({
    code: diagnostic.code,
    message: diagnostic.message,
  }));
}

function formatFailureReason(error: unknown): {
  reason: string;
  diagnostics: readonly SurfaceInformationDiagnostic[];
} {
  if (error instanceof LiveApiError) {
    const reason = error.code ? `${error.message} (${error.code})` : error.message;
    return {
      reason,
      diagnostics: boundedDiagnostics([
        { code: error.code?.trim() || "authority_unavailable", message: error.message },
      ]),
    };
  }
  const message = error instanceof Error ? error.message : "Projection request failed.";
  return {
    reason: message,
    diagnostics: boundedDiagnostics([{ code: "authority_unavailable", message }]),
  };
}

function observedMetadata(
  response: WorldGraphProjection,
  revisionId: string,
): SurfaceInformationObservedMetadata {
  return {
    revision: { kind: "exact", value: revisionId },
    provenance: [{ kind: "world_graph_revision", id: revisionId }],
    inspectionTargets: [
      { kind: "world", id: response.snapshot.worldId },
      { kind: "campaign", id: response.snapshot.campaignId },
      { kind: "world_graph_revision", id: revisionId },
    ],
    diagnostics: boundedDiagnostics(
      response.diagnostics.map((diagnostic) => ({
        code: diagnostic.code,
        message: diagnostic.message,
      })),
    ),
  };
}

export function mapWorldGraphLensObservation(input: {
  request: WorldGraphProjectionRequest;
  response?: WorldGraphProjection | null;
  error?: unknown;
}): Exclude<SurfaceInformationState<WorldGraphProjection>, { status: "loading" }> {
  if (input.response == null) {
    const failure = formatFailureReason(input.error);
    return {
      status: "unavailable",
      reason: failure.reason,
      diagnostics: failure.diagnostics,
    };
  }

  const response = input.response;
  const mismatch = verifyWorldGraphProjectionResponse({
    request: input.request,
    response,
    revisionKind: input.request.revisionPin ? "pinned" : "head",
    pinnedRevisionId: input.request.revisionPin ?? null,
  });
  if (mismatch) {
    return {
      status: "integrity_error",
      reason: mismatch,
      diagnostics: boundedDiagnostics([
        { code: "projection_response_mismatch", message: mismatch },
      ]),
    };
  }

  const revisionId = response.snapshot.revisionId?.trim() ?? "";
  if (!revisionId) {
    return {
      status: "integrity_error",
      reason: "Verified World Graph projection is missing an exact DungeonMind revision.",
      diagnostics: boundedDiagnostics([
        {
          code: "missing_revision",
          message: "DungeonMind World Graph projections must carry an exact revision id.",
        },
      ]),
    };
  }

  const metadata = observedMetadata(response, revisionId);
  if (response.nodes.length === 0) {
    return {
      status: "empty",
      ...metadata,
    };
  }
  return {
    status: "ready",
    value: response,
    ...metadata,
  };
}
