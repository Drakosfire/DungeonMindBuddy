import type {
  WorldGraphProjection,
  WorldGraphProjectionRequest,
} from "../api/types";

function focusMatchesRequest(
  responseFocus: WorldGraphProjection["snapshot"]["focus"],
  requestFocus: WorldGraphProjectionRequest["focus"],
): boolean {
  const responseKind = responseFocus?.kind ?? "none";
  const requestKind = requestFocus.kind;
  if (responseKind !== requestKind) return false;
  const responseSessionId = responseFocus?.sessionId ?? null;
  const requestSessionId = requestFocus.sessionId ?? null;
  if (responseSessionId !== requestSessionId) return false;
  // Exact: a response campaignId is not tolerated when the request omitted one.
  const responseCampaignId = responseFocus?.campaignId ?? null;
  const requestCampaignId = requestFocus.campaignId ?? null;
  return responseCampaignId === requestCampaignId;
}

/**
 * Verify the projection response matches the exact request lens.
 * Pinned: revisionId must equal the pin.
 * Head: snapshot must report isHead and revisionId === headRevisionId.
 *
 * Shared across Build's local loader and the app-level World Graph lens provider.
 * Surfaces must not mark a projection ready unless this returns null.
 */
export function verifyWorldGraphProjectionResponse(input: {
  request: WorldGraphProjectionRequest;
  response: WorldGraphProjection;
  revisionKind: "head" | "pinned";
  pinnedRevisionId?: string | null;
}): string | null {
  const { request, response, revisionKind, pinnedRevisionId } = input;
  const snapshot = response.snapshot;

  if (snapshot.worldId !== request.worldId) {
    return `Projection world ${snapshot.worldId} does not match requested world ${request.worldId}.`;
  }
  if (snapshot.campaignId !== request.campaignId) {
    return `Projection campaign ${snapshot.campaignId} does not match requested campaign ${request.campaignId}.`;
  }
  if (snapshot.admissibility !== request.admissibility) {
    return `Projection admissibility ${snapshot.admissibility} does not match requested ${request.admissibility}.`;
  }
  const requestScope = request.scopeMode ?? null;
  const responseScope = snapshot.scopeMode ?? null;
  if (responseScope !== requestScope) {
    return `Projection scopeMode ${responseScope ?? "∅"} does not match requested ${requestScope ?? "∅"}.`;
  }
  if (!focusMatchesRequest(snapshot.focus, request.focus)) {
    return "Projection focus does not match the requested lens focus.";
  }

  if (revisionKind === "pinned") {
    const pin = pinnedRevisionId?.trim() || null;
    if (!pin) {
      return "Pinned revision request is missing a revision id.";
    }
    if (snapshot.revisionId !== pin) {
      return `Pinned revision ${pin} does not match loaded revision ${snapshot.revisionId}.`;
    }
    return null;
  }

  if (!snapshot.isHead) {
    return `Requested current head but projection reports non-head revision ${snapshot.revisionId}.`;
  }
  if (snapshot.revisionId !== snapshot.headRevisionId) {
    return `Projection head claim is inconsistent (revision ${snapshot.revisionId} ≠ head ${snapshot.headRevisionId}).`;
  }
  return null;
}
