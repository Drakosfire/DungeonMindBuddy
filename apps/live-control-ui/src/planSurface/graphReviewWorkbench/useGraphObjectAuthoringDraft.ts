import { useCallback, useEffect, useState } from "react";

import type { GraphAuthoringSelection } from "./graphAuthoringSelection";
import {
  buildGraphObjectAuthoringLinkExistingProposal,
  buildGraphObjectAuthoringMergeProposal,
  buildGraphObjectAuthoringProposal,
  buildGraphObjectAuthoringRelationshipProposal,
  createDefaultGraphObjectAuthoringFormState,
  createDefaultGraphObjectAuthoringRelationshipFormState,
  createLocalGraphObjectProposalId,
  findDuplicateMergeProposal,
  findConflictingMergeProposal,
  type GraphObjectAuthoringFormState,
  type GraphObjectAuthoringProposal,
  type GraphObjectAuthoringRelationshipFormState,
} from "./graphObjectAuthoringDraft";
import { buildLinkExistingFormStateFromResolverCandidate } from "./graphExistingObjectIdentityWorkbench";

export interface UseGraphObjectAuthoringDraftResult {
  selectedSource: GraphAuthoringSelection | null;
  formState: GraphObjectAuthoringFormState;
  proposals: GraphObjectAuthoringProposal[];
  openWithSelection: (selection: GraphAuthoringSelection) => void;
  dismissSelection: () => void;
  updateFormField: <K extends keyof GraphObjectAuthoringFormState>(
    field: K,
    value: GraphObjectAuthoringFormState[K],
  ) => void;
  stageProposal: () => void;
  removeProposal: (localProposalId: string) => void;

  relationshipFormState: GraphObjectAuthoringRelationshipFormState;
  updateRelationshipField: <K extends keyof GraphObjectAuthoringRelationshipFormState>(
    field: K,
    value: GraphObjectAuthoringRelationshipFormState[K],
  ) => void;
  stageRelationshipProposal: () => void;
  stageMergeProposal: (input: {
    survivorObjectRef: import("./graphObjectAuthoringDraft").GraphObjectAuthoringObjectRef;
    mergedObjectRefs: import("./graphObjectAuthoringDraft").GraphObjectAuthoringObjectRef[];
    mergeReason: string;
    matchedFeatures: string[];
    sourceGraphId?: string | null;
  }) => boolean;
  stageLinkExistingFromResolver: (input: {
    selection: GraphAuthoringSelection;
    candidate: import("../../api/types").GraphReviewExistingObjectCandidate;
  }) => boolean;
  clearCommittedProposals: (localProposalIds: string[]) => void;
}

export interface GraphObjectAuthoringDraftStorageScope {
  campaignId: string;
  sessionId: string;
}

function stagedProposalsStorageKey(scope: GraphObjectAuthoringDraftStorageScope): string {
  return `graph-object-authoring-staged:${scope.campaignId}:${scope.sessionId}`;
}

export function writeStagedProposalsToSession(
  scope: GraphObjectAuthoringDraftStorageScope | undefined,
  proposals: GraphObjectAuthoringProposal[],
): void {
  if (!scope || typeof sessionStorage === "undefined") {
    return;
  }
  const key = stagedProposalsStorageKey(scope);
  if (proposals.length === 0) {
    sessionStorage.removeItem(key);
    return;
  }
  sessionStorage.setItem(key, JSON.stringify(proposals));
}

function readStagedProposalsFromSession(
  scope: GraphObjectAuthoringDraftStorageScope | undefined,
): GraphObjectAuthoringProposal[] {
  if (!scope || typeof sessionStorage === "undefined") {
    return [];
  }
  try {
    const raw = sessionStorage.getItem(stagedProposalsStorageKey(scope));
    if (!raw) {
      return [];
    }
    const parsed = JSON.parse(raw) as unknown;
    return Array.isArray(parsed) ? (parsed as GraphObjectAuthoringProposal[]) : [];
  } catch {
    return [];
  }
}

export function useGraphObjectAuthoringDraft(
  storageScope?: GraphObjectAuthoringDraftStorageScope,
): UseGraphObjectAuthoringDraftResult {
  const [selectedSource, setSelectedSource] = useState<GraphAuthoringSelection | null>(null);
  const [formState, setFormState] = useState<GraphObjectAuthoringFormState>(
    createDefaultGraphObjectAuthoringFormState(null),
  );
  const [relationshipFormState, setRelationshipFormState] =
    useState<GraphObjectAuthoringRelationshipFormState>(
      createDefaultGraphObjectAuthoringRelationshipFormState(),
    );
  const [proposals, setProposals] = useState<GraphObjectAuthoringProposal[]>(() =>
    readStagedProposalsFromSession(storageScope),
  );

  useEffect(() => {
    writeStagedProposalsToSession(storageScope, proposals);
  }, [proposals, storageScope]);

  const openWithSelection = useCallback((selection: GraphAuthoringSelection) => {
    setSelectedSource(selection);
    setFormState(createDefaultGraphObjectAuthoringFormState(selection));
  }, []);

  const dismissSelection = useCallback(() => {
    setSelectedSource(null);
    setFormState(createDefaultGraphObjectAuthoringFormState(null));
  }, []);

  const updateFormField = useCallback(
    <K extends keyof GraphObjectAuthoringFormState>(
      field: K,
      value: GraphObjectAuthoringFormState[K],
    ) => {
      setFormState((prev) => ({ ...prev, [field]: value }));
    },
    [],
  );

  const stageProposal = useCallback(() => {
    if (!selectedSource || !formState.label.trim()) {
      return;
    }
    const proposal = buildGraphObjectAuthoringProposal(
      selectedSource,
      formState,
      createLocalGraphObjectProposalId(),
    );
    setProposals((prev) => [...prev, proposal]);
    setSelectedSource(null);
    setFormState(createDefaultGraphObjectAuthoringFormState(null));
  }, [selectedSource, formState]);

  const updateRelationshipField = useCallback(
    <K extends keyof GraphObjectAuthoringRelationshipFormState>(
      field: K,
      value: GraphObjectAuthoringRelationshipFormState[K],
    ) => {
      setRelationshipFormState((prev) => ({ ...prev, [field]: value }));
    },
    [],
  );

  const stageRelationshipProposal = useCallback(() => {
    const proposal = buildGraphObjectAuthoringRelationshipProposal(
      relationshipFormState,
      selectedSource,
      createLocalGraphObjectProposalId(),
    );
    if (!proposal) {
      return;
    }
    setProposals((prev) => [...prev, proposal]);
    setRelationshipFormState(createDefaultGraphObjectAuthoringRelationshipFormState());
  }, [relationshipFormState, selectedSource]);

  const stageMergeProposal = useCallback(
    (input: {
      survivorObjectRef: import("./graphObjectAuthoringDraft").GraphObjectAuthoringObjectRef;
      mergedObjectRefs: import("./graphObjectAuthoringDraft").GraphObjectAuthoringObjectRef[];
      mergeReason: string;
      matchedFeatures: string[];
      sourceGraphId?: string | null;
    }) => {
      const proposal = buildGraphObjectAuthoringMergeProposal({
        ...input,
        localProposalId: createLocalGraphObjectProposalId(),
      });
      if (!proposal) {
        return false;
      }
      if (
        findDuplicateMergeProposal(
          input.survivorObjectRef,
          input.mergedObjectRefs,
          proposals,
        )
      ) {
        return false;
      }
      if (
        findConflictingMergeProposal(
          input.survivorObjectRef,
          input.mergedObjectRefs,
          proposals,
        )
      ) {
        return false;
      }
      setProposals((prev) => {
        if (
          findDuplicateMergeProposal(
            input.survivorObjectRef,
            input.mergedObjectRefs,
            prev,
          )
        ) {
          return prev;
        }
        if (
          findConflictingMergeProposal(
            input.survivorObjectRef,
            input.mergedObjectRefs,
            prev,
          )
        ) {
          return prev;
        }
        const next = [...prev, proposal];
        writeStagedProposalsToSession(storageScope, next);
        return next;
      });
      return true;
    },
    [proposals, storageScope],
  );

  const stageLinkExistingFromResolver = useCallback(
    (input: {
      selection: GraphAuthoringSelection;
      candidate: import("../../api/types").GraphReviewExistingObjectCandidate;
    }) => {
      const proposal = buildGraphObjectAuthoringLinkExistingProposal(
        input.selection,
        buildLinkExistingFormStateFromResolverCandidate(input.candidate, {
          aliasText: input.selection.selectedText,
        }),
        createLocalGraphObjectProposalId(),
      );
      if (!proposal) {
        return false;
      }
      setProposals((prev) => {
        const next = [...prev, proposal];
        writeStagedProposalsToSession(storageScope, next);
        return next;
      });
      return true;
    },
    [storageScope],
  );

  const removeProposal = useCallback((localProposalId: string) => {
    setProposals((prev) => {
      const next = prev.filter((proposal) => proposal.localProposalId !== localProposalId);
      writeStagedProposalsToSession(storageScope, next);
      return next;
    });
  }, [storageScope]);

  const clearCommittedProposals = useCallback((localProposalIds: string[]) => {
    const removeSet = new Set(localProposalIds);
    setProposals((prev) => {
      const next = prev.filter((proposal) => !removeSet.has(proposal.localProposalId));
      writeStagedProposalsToSession(storageScope, next);
      return next;
    });
  }, [storageScope]);

  return {
    selectedSource,
    formState,
    proposals,
    openWithSelection,
    dismissSelection,
    updateFormField,
    stageProposal,
    removeProposal,
    relationshipFormState,
    updateRelationshipField,
    stageRelationshipProposal,
    stageMergeProposal,
    stageLinkExistingFromResolver,
    clearCommittedProposals,
  };
}
