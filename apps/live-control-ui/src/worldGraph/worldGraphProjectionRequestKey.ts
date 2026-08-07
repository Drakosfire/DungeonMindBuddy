import type { WorldGraphProjectionRequest } from "../api/types";

/**
 * Stable exact-request identity for World Graph projections.
 * Surfaces reuse a shared verified projection only when keys match.
 */
export function worldGraphProjectionRequestKey(
  request: WorldGraphProjectionRequest,
): string {
  return JSON.stringify({
    schema: request.schema,
    worldId: request.worldId,
    campaignId: request.campaignId,
    scopeMode: request.scopeMode ?? null,
    focus: {
      kind: request.focus?.kind ?? "none",
      sessionId: request.focus?.sessionId ?? null,
      campaignId: request.focus?.campaignId ?? null,
    },
    admissibility: request.admissibility,
    revisionPin: request.revisionPin ?? null,
  });
}

export function worldGraphProjectionRequestsMatch(
  left: WorldGraphProjectionRequest,
  right: WorldGraphProjectionRequest,
): boolean {
  return worldGraphProjectionRequestKey(left) === worldGraphProjectionRequestKey(right);
}
