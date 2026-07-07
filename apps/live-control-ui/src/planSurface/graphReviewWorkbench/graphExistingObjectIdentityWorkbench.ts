import type { GraphReviewExistingObjectCandidate } from "../../api/types";
import {
  buildObjectRefFromResolverCandidate,
  createDefaultGraphObjectAuthoringLinkExistingFormState,
  findDuplicateMergeProposal,
  mergeObjectPairKey,
  type GraphObjectAuthoringLinkExistingFormState,
  type GraphObjectAuthoringObjectRef,
  type GraphObjectAuthoringProposal,
} from "./graphObjectAuthoringDraft";
import { candidateScopeLabel } from "./graphObjectCandidateScope";
import { formatGraphObjectType } from "./graphReviewSelectionUtils";

export function existingObjectCandidateKey(
  candidate: GraphReviewExistingObjectCandidate,
): string {
  return candidate.candidate_id;
}

export function buildObjectRefFromExistingObjectCandidate(
  candidate: GraphReviewExistingObjectCandidate,
): GraphObjectAuthoringObjectRef {
  return buildObjectRefFromResolverCandidate(candidate);
}

export function buildLinkExistingFormStateFromResolverCandidate(
  candidate: GraphReviewExistingObjectCandidate,
): GraphObjectAuthoringLinkExistingFormState {
  return {
    ...createDefaultGraphObjectAuthoringLinkExistingFormState(),
    existingObjectRef: buildObjectRefFromExistingObjectCandidate(candidate),
    operation: "alias",
    aliasText: candidate.label,
  };
}

export interface ExistingObjectIdentitySelectionState {
  canonical: GraphReviewExistingObjectCandidate | null;
  duplicates: GraphReviewExistingObjectCandidate[];
}

export function createEmptyIdentitySelection(): ExistingObjectIdentitySelectionState {
  return { canonical: null, duplicates: [] };
}

export function setCanonicalCandidate(
  state: ExistingObjectIdentitySelectionState,
  candidate: GraphReviewExistingObjectCandidate,
): ExistingObjectIdentitySelectionState {
  const key = existingObjectCandidateKey(candidate);
  if (state.canonical?.candidate_id === key) {
    return state;
  }
  return {
    canonical: candidate,
    duplicates: state.duplicates.filter((item) => item.candidate_id !== key),
  };
}

export function clearCanonicalCandidate(
  state: ExistingObjectIdentitySelectionState,
): ExistingObjectIdentitySelectionState {
  return { ...state, canonical: null };
}

export function toggleDuplicateCandidate(
  state: ExistingObjectIdentitySelectionState,
  candidate: GraphReviewExistingObjectCandidate,
): ExistingObjectIdentitySelectionState {
  const key = existingObjectCandidateKey(candidate);
  if (state.canonical?.candidate_id === key) {
    return state;
  }
  const alreadySelected = state.duplicates.some((item) => item.candidate_id === key);
  if (alreadySelected) {
    return {
      ...state,
      duplicates: state.duplicates.filter((item) => item.candidate_id !== key),
    };
  }
  return {
    ...state,
    duplicates: [...state.duplicates, candidate],
  };
}

export function clearIdentitySelection(): ExistingObjectIdentitySelectionState {
  return createEmptyIdentitySelection();
}

export function canStageSearchMerge(
  state: ExistingObjectIdentitySelectionState,
): boolean {
  return Boolean(state.canonical && state.duplicates.length > 0);
}

export function buildSearchMergeReason(
  canonical: GraphReviewExistingObjectCandidate,
  duplicates: GraphReviewExistingObjectCandidate[],
): string {
  if (duplicates.length === 1) {
    return (
      `Search result identity merge: ${canonical.candidate_id} ← ` +
      `${duplicates[0].candidate_id}`
    );
  }
  const duplicateIds = duplicates.map((item) => item.candidate_id).join(", ");
  return `Search result identity merge: ${canonical.candidate_id} ← ${duplicateIds}`;
}

export function collectSearchMergeMatchedFeatures(
  canonical: GraphReviewExistingObjectCandidate,
  duplicates: GraphReviewExistingObjectCandidate[],
): string[] {
  const features = new Set<string>(["search_identity_workbench"]);
  for (const feature of canonical.matched_features) {
    features.add(feature);
  }
  for (const duplicate of duplicates) {
    for (const feature of duplicate.matched_features) {
      features.add(feature);
    }
  }
  return [...features];
}

export interface SearchMergeStageInput {
  survivorObjectRef: GraphObjectAuthoringObjectRef;
  mergedObjectRefs: GraphObjectAuthoringObjectRef[];
  mergeReason: string;
  matchedFeatures: string[];
  sourceGraphId?: string | null;
}

export function buildSearchMergeStageInput(
  state: ExistingObjectIdentitySelectionState,
  sourceGraphId?: string | null,
): SearchMergeStageInput | null {
  if (!canStageSearchMerge(state) || !state.canonical) {
    return null;
  }

  return {
    survivorObjectRef: buildObjectRefFromExistingObjectCandidate(state.canonical),
    mergedObjectRefs: state.duplicates.map(buildObjectRefFromExistingObjectCandidate),
    mergeReason: buildSearchMergeReason(state.canonical, state.duplicates),
    matchedFeatures: collectSearchMergeMatchedFeatures(
      state.canonical,
      state.duplicates,
    ),
    sourceGraphId: sourceGraphId ?? null,
  };
}

export function isSearchMergeAlreadyStaged(
  input: SearchMergeStageInput,
  proposals: GraphObjectAuthoringProposal[],
): boolean {
  return Boolean(
    findDuplicateMergeProposal(
      input.survivorObjectRef,
      input.mergedObjectRefs,
      proposals,
    ),
  );
}

export function searchMergePairKey(
  canonical: GraphReviewExistingObjectCandidate,
  duplicate: GraphReviewExistingObjectCandidate,
): string | null {
  return mergeObjectPairKey(
    buildObjectRefFromExistingObjectCandidate(canonical),
    buildObjectRefFromExistingObjectCandidate(duplicate),
  );
}

function normalizeClusterText(value: string): string {
  return value.trim().toLowerCase().replace(/\s+/g, " ");
}

export function candidateClusterKeys(
  candidate: GraphReviewExistingObjectCandidate,
): string[] {
  const keys = new Set<string>();
  keys.add(normalizeClusterText(candidate.label));
  for (const alias of candidate.aliases ?? []) {
    const normalized = normalizeClusterText(alias);
    if (normalized) {
      keys.add(normalized);
    }
  }
  return [...keys];
}

export function possibleDuplicateCount(
  candidate: GraphReviewExistingObjectCandidate,
  allCandidates: GraphReviewExistingObjectCandidate[],
): number {
  const keys = new Set(candidateClusterKeys(candidate));
  return allCandidates.filter((other) => {
    if (other.candidate_id === candidate.candidate_id) {
      return false;
    }
    return candidateClusterKeys(other).some((key) => keys.has(key));
  }).length;
}

export function sharesClusterKeys(
  left: GraphReviewExistingObjectCandidate,
  right: GraphReviewExistingObjectCandidate,
): boolean {
  const leftKeys = new Set(candidateClusterKeys(left));
  return candidateClusterKeys(right).some((key) => leftKeys.has(key));
}

export function isClusterPeerOfSelection(
  candidate: GraphReviewExistingObjectCandidate,
  state: ExistingObjectIdentitySelectionState,
): boolean {
  const selected = [
    ...(state.canonical ? [state.canonical] : []),
    ...state.duplicates,
  ];
  if (!selected.length) {
    return false;
  }
  if (selected.some((item) => item.candidate_id === candidate.candidate_id)) {
    return false;
  }
  return selected.some((item) => sharesClusterKeys(item, candidate));
}

export function formatCandidateIdentitySubline(
  candidate: GraphReviewExistingObjectCandidate,
): string {
  const scope = candidateScopeLabel(candidate);
  const type = formatGraphObjectType(candidate.kind, candidate.role);
  const typeSuffix = type && type !== "Unknown" ? ` · ${type}` : "";
  return `${candidate.candidate_id} · ${scope}${typeSuffix}`;
}

export function candidateSelectionRole(
  state: ExistingObjectIdentitySelectionState,
  candidate: GraphReviewExistingObjectCandidate,
): "canonical" | "duplicate" | null {
  if (state.canonical?.candidate_id === candidate.candidate_id) {
    return "canonical";
  }
  if (state.duplicates.some((item) => item.candidate_id === candidate.candidate_id)) {
    return "duplicate";
  }
  return null;
}

export interface StoredIdentityWorkbenchState {
  query: string;
  canonicalCandidateId: string | null;
  duplicateCandidateIds: string[];
}

export function identityWorkbenchStorageKey(scope: {
  campaignId: string;
  sessionId: string;
}): string {
  return `graph-existing-object-identity-workbench:${scope.campaignId}:${scope.sessionId}`;
}

export function readStoredIdentityWorkbenchState(
  scope: { campaignId: string; sessionId: string } | undefined,
): StoredIdentityWorkbenchState | null {
  if (!scope || typeof sessionStorage === "undefined") {
    return null;
  }
  try {
    const raw = sessionStorage.getItem(identityWorkbenchStorageKey(scope));
    if (!raw) {
      return null;
    }
    const parsed = JSON.parse(raw) as StoredIdentityWorkbenchState;
    if (typeof parsed.query !== "string") {
      return null;
    }
    return {
      query: parsed.query,
      canonicalCandidateId:
        typeof parsed.canonicalCandidateId === "string"
          ? parsed.canonicalCandidateId
          : null,
      duplicateCandidateIds: Array.isArray(parsed.duplicateCandidateIds)
        ? parsed.duplicateCandidateIds.filter((item): item is string => typeof item === "string")
        : [],
    };
  } catch {
    return null;
  }
}

export function writeStoredIdentityWorkbenchState(
  scope: { campaignId: string; sessionId: string } | undefined,
  state: StoredIdentityWorkbenchState,
): void {
  if (!scope || typeof sessionStorage === "undefined") {
    return;
  }
  const key = identityWorkbenchStorageKey(scope);
  if (
    !state.query.trim() &&
    !state.canonicalCandidateId &&
    state.duplicateCandidateIds.length === 0
  ) {
    sessionStorage.removeItem(key);
    return;
  }
  sessionStorage.setItem(key, JSON.stringify(state));
}

export function rehydrateIdentitySelection(
  stored: Pick<StoredIdentityWorkbenchState, "canonicalCandidateId" | "duplicateCandidateIds">,
  candidates: GraphReviewExistingObjectCandidate[],
): ExistingObjectIdentitySelectionState {
  const canonical =
    stored.canonicalCandidateId != null
      ? candidates.find((item) => item.candidate_id === stored.canonicalCandidateId) ?? null
      : null;
  const duplicates = stored.duplicateCandidateIds
    .map((candidateId) => candidates.find((item) => item.candidate_id === candidateId) ?? null)
    .filter((item): item is GraphReviewExistingObjectCandidate => item !== null);
  return { canonical, duplicates };
}

export function serializeIdentitySelection(
  query: string,
  state: ExistingObjectIdentitySelectionState,
): StoredIdentityWorkbenchState {
  return {
    query,
    canonicalCandidateId: state.canonical?.candidate_id ?? null,
    duplicateCandidateIds: state.duplicates.map((item) => item.candidate_id),
  };
}
