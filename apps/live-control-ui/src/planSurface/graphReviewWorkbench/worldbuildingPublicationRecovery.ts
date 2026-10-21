import type {ExactRunReviewPackage, ManagedWorldGraphProjectionResponse} from '../../api/types';
import type {WorldbuildingDecision, WorldbuildingPlan} from '../../api/worldbuildingPublicationApi';

export interface WorldbuildingPublicationRecovery {
  schema: 'dmb_worldbuilding_publication_recovery_v1';
  scope: string;
  plan: WorldbuildingPlan;
  submitted: boolean;
  staleParent: boolean;
}
const digest = (value: unknown) => typeof value === 'string' && /^sha256:[a-f0-9]{64}$/.test(value);
const nonblank = (value: unknown): value is string => typeof value === 'string' && !!value.trim();
export const worldbuildingPublicationScope = (review: ExactRunReviewPackage, worldId: string) =>
  JSON.stringify([worldId, review.worldId, review.runId, review.sourceArtifactId, review.sourceRevisionId]);
export const worldbuildingPublicationRecoveryKey = (scope: string) => 'dmb.worldbuildingPublication.v1:' + scope;

/** Browser state is a saved request, never authority or a verified publication receipt. */
export function assertWorldbuildingPlan(plan: WorldbuildingPlan, review: ExactRunReviewPackage,
  managedWorldId: string, projection?: ManagedWorldGraphProjectionResponse,
  decisions?: Record<string, WorldbuildingDecision>) {
  const binding = plan?.publicationBinding, snapshot = plan?.effect?.decisionSnapshot;
  if (review.worldId !== managedWorldId || review.sourceDomain !== 'worldbuilding' || review.inspectionStatus !== 'ready'
    || !plan || plan.schema !== 'dmb_worldbuilding_write_plan_v2' || plan.version !== 2
    || !nonblank(plan.planId) || !digest(plan.planDigest) || !digest(plan.decisionDigest)
    || !nonblank(plan.worldId) || !nonblank(plan.parentRevisionId) || !nonblank(plan.prepareBinding)
    || plan.runId !== review.runId || plan.sourceArtifactId !== review.sourceArtifactId
    || plan.sourceRevisionId !== review.sourceRevisionId || !digest(review.sourceRevisionId)
    || binding?.managedWorldId !== managedWorldId || binding.nativeWorldId !== plan.worldId
    || !Number.isSafeInteger(binding.bindingVersion) || binding.bindingVersion <= 0
    || binding.sourceArtifactId !== review.sourceArtifactId || binding.sourceSha256 !== review.sourceRevisionId.slice(7)
    || !nonblank(binding.documentId) || !Number.isSafeInteger(binding.documentRevision) || binding.documentRevision <= 0
    || !plan.summary || !['createNewNodeCount','bindExistingNodeCount','acceptedEdgeCount','rejectedCandidateCount',
      'deferredCandidateCount','acceptedAssertionCount'].every(key => {
        const n = plan.summary[key as keyof typeof plan.summary]; return Number.isSafeInteger(n) && n >= 0;
      })
    || !Array.isArray(plan.effect?.acceptedProposals) || !Array.isArray(plan.diagnostics)
    || plan.diagnostics.some(item => typeof item !== 'string')
    || !Array.isArray(snapshot) || snapshot.length !== review.assertions.length
    || new Set(snapshot.map(item => item?.assertionId)).size !== snapshot.length
    || snapshot.some(item => {
      const candidate = review.assertions.find(a => a.assertionId === item?.assertionId);
      if (!candidate || !['defer','reject', ...(candidate.kind === 'object' ? ['create_new','bind_existing'] : ['accept'])].includes(item.decision)) return true;
      if (item.decision === 'bind_existing' ? !nonblank(item.targetNodeId) : item.targetNodeId != null) return true;
      const expected = decisions?.[item.assertionId];
      return decisions !== undefined && (!expected || expected.decision !== item.decision || expected.targetNodeId !== (item.targetNodeId ?? undefined));
    })
    || (projection && (projection.managedWorldId !== managedWorldId || projection.nativeWorldId !== plan.worldId
      || projection.bindingVersion !== binding.bindingVersion))
    || (decisions && projection && plan.parentRevisionId !== projection.projection.snapshot.revisionId)) {
    throw new Error('The prepared plan does not match this exact source, World or reviewed choices.');
  }
}
export function readWorldbuildingPublicationRecovery(review: ExactRunReviewPackage, worldId: string): WorldbuildingPublicationRecovery | null {
  const scope = worldbuildingPublicationScope(review, worldId);
  const raw = localStorage.getItem(worldbuildingPublicationRecoveryKey(scope));
  if (raw === null) return null;
  const value = JSON.parse(raw) as WorldbuildingPublicationRecovery;
  if (!value || value.schema !== 'dmb_worldbuilding_publication_recovery_v1' || value.scope !== scope
    || typeof value.submitted !== 'boolean' || typeof value.staleParent !== 'boolean'
    || (value.staleParent && !value.submitted)) throw new Error('Saved publication belongs to another source or World.');
  assertWorldbuildingPlan(value.plan, review, worldId);
  return value;
}
const samePlan = (left: WorldbuildingPlan, right: WorldbuildingPlan) => JSON.stringify(left) === JSON.stringify(right);
async function withPublicationLock<T>(review: ExactRunReviewPackage, worldId: string, action: () => T): Promise<T> {
  if (!navigator.locks) throw new Error('This browser cannot safely retain publication recovery across tabs.');
  const key = worldbuildingPublicationRecoveryKey(worldbuildingPublicationScope(review, worldId));
  return navigator.locks.request(key, action);
}
export async function saveWorldbuildingPublicationRecovery(review: ExactRunReviewPackage, worldId: string,
  plan: WorldbuildingPlan, submitted: boolean, staleParent = false) {
  assertWorldbuildingPlan(plan, review, worldId);
  return withPublicationLock(review, worldId, () => {
    const current = readWorldbuildingPublicationRecovery(review, worldId);
    if ((current && !samePlan(current.plan, plan)) || (current?.submitted && !submitted)
      || (submitted && !current)) {
      throw new Error('Another publication request was retained. Reopen the review to recover that exact request.');
    }
    const scope = worldbuildingPublicationScope(review, worldId);
    const value: WorldbuildingPublicationRecovery = {schema:'dmb_worldbuilding_publication_recovery_v1', scope, plan, submitted, staleParent};
    localStorage.setItem(worldbuildingPublicationRecoveryKey(scope), JSON.stringify(value));
  });
}
export async function clearUnsubmittedWorldbuildingPublication(review: ExactRunReviewPackage, worldId: string, plan: WorldbuildingPlan) {
  return withPublicationLock(review, worldId, () => {
    const value = readWorldbuildingPublicationRecovery(review, worldId);
    if (!value || !samePlan(value.plan, plan) || value.submitted) {
      throw new Error('The saved publication changed. Reopen the review before changing its choices.');
    }
    localStorage.removeItem(worldbuildingPublicationRecoveryKey(value.scope));
  });
}

/** A typed server rejection permits replacement only after retaining the old request. */
export async function setAsideRejectedWorldbuildingPublication(review: ExactRunReviewPackage, worldId: string, plan: WorldbuildingPlan) {
  return withPublicationLock(review, worldId, () => {
    const value = readWorldbuildingPublicationRecovery(review, worldId);
    if (!value?.submitted || !value.staleParent || !samePlan(value.plan, plan)) {
      throw new Error('Recover the original confirmation before preparing another plan.');
    }
    const key = worldbuildingPublicationRecoveryKey(value.scope);
    localStorage.setItem(key + ':retained:' + value.plan.planId, JSON.stringify(value));
    localStorage.removeItem(key);
  });
}
