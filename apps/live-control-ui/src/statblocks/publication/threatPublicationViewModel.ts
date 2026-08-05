import type { ThreatDraftV1, ThreatIdentityCandidateV1 } from "../../api/types";

/**
 * A GM can only begin publication for a draft that has locked-in accepted
 * mechanics and a known current World Graph parent revision to publish
 * against. Both facts must be exact, not inferred.
 */
export function isThreatDraftEligibleForPublication(
  draft: Pick<ThreatDraftV1, "workflow_state" | "accepted_mechanics_ref">,
  expectedParentRevisionId: string | null | undefined,
): boolean {
  return (
    draft.workflow_state === "mechanics_saved"
    && draft.accepted_mechanics_ref != null
    && typeof expectedParentRevisionId === "string"
    && expectedParentRevisionId.trim().length > 0
  );
}

/** Exact-name-collision candidates that have not yet been explicitly rejected. */
export function unrejectedExactCollisionNodeIds(
  candidates: readonly ThreatIdentityCandidateV1[],
  rejectedNodeIds: ReadonlySet<string>,
): string[] {
  return candidates
    .filter((candidate) => candidate.exact_name_collision && !rejectedNodeIds.has(candidate.node_id))
    .map((candidate) => candidate.node_id);
}

/**
 * The backend contract requires every exact-name collision to be explicitly
 * rejected before a create-new decision is accepted. Mirror that rule client
 * side so the control can be disabled before the request is ever sent.
 */
export function canCreateNewThreatIdentity(
  candidates: readonly ThreatIdentityCandidateV1[],
  rejectedNodeIds: ReadonlySet<string>,
): boolean {
  return unrejectedExactCollisionNodeIds(candidates, rejectedNodeIds).length === 0;
}
