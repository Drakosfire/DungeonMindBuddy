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
  candidate: Pick<GraphReviewExistingObjectCandidate, "candidate_id" | "existing_object_ref">,
  governedWorldNodeViews: Record<string, GraphProjectionNodeView> | null | undefined,
): boolean {
  if (governedWorldNodeViews === undefined) return true;
  if (governedWorldNodeViews === null) return false;
  const bindTargetNodeId = getGraphReviewBindTargetNodeId(candidate);
  if (!bindTargetNodeId) return false;
  if (governedWorldNodeViews[bindTargetNodeId]) return true;
  return Object.values(governedWorldNodeViews).some((node) => node.node_id === bindTargetNodeId);
}

export function governedExistingTargetMessage(
  candidate: Pick<GraphReviewExistingObjectCandidate, "candidate_id" | "existing_object_ref">,
  governedWorldNodeViews: Record<string, GraphProjectionNodeView> | null | undefined,
): string | null {
  return isExactGovernedExistingTarget(candidate, governedWorldNodeViews)
    ? null
    : "Not in the current governed World projection. Publish this object before linking it.";
}

/**
 * Return the durable node identity a resolver result will bind when staged.
 * `candidate_id` may be a display/search identity (for example a scoped party
 * key), while the server-provided object reference names the World node.
 */
export function getGraphReviewBindTargetNodeId(
  candidate: Pick<GraphReviewExistingObjectCandidate, "candidate_id" | "existing_object_ref">,
): string | null {
  const existingObjectId = candidate.existing_object_ref?.object_id?.trim();
  if (existingObjectId) return existingObjectId;
  const candidateId = candidate.candidate_id.trim();
  return candidateId || null;
}
