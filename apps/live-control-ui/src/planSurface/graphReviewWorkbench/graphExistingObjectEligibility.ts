import type {
  GraphProjectionNodeView,
  GraphReviewExistingObjectCandidate,
} from "../../api/types";

/**
 * Classify a resolver result against the exact World projection currently
 * loaded by the shared World lens. `undefined` preserves legacy callers that
 * do not provide a World lens; `null` means the lens is unavailable and must
 * fail closed.
 */
export function isExactGovernedExistingTarget(
  candidate: Pick<GraphReviewExistingObjectCandidate, "candidate_id">,
  governedWorldNodeViews: Record<string, GraphProjectionNodeView> | null | undefined,
): boolean {
  if (governedWorldNodeViews === undefined) return true;
  if (governedWorldNodeViews === null) return false;
  const candidateId = candidate.candidate_id.trim();
  if (!candidateId) return false;
  if (governedWorldNodeViews[candidateId]) return true;
  return Object.values(governedWorldNodeViews).some((node) => node.node_id === candidateId);
}

export function governedExistingTargetMessage(
  candidate: Pick<GraphReviewExistingObjectCandidate, "candidate_id">,
  governedWorldNodeViews: Record<string, GraphProjectionNodeView> | null | undefined,
): string | null {
  return isExactGovernedExistingTarget(candidate, governedWorldNodeViews)
    ? null
    : "Not in the current governed World projection. Publish this object before linking it.";
}
