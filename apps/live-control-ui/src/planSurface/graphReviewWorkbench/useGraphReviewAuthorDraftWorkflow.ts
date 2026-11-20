import { useCallback, useState } from "react";
import type { GraphReviewExistingObjectCandidate } from "../../api/types";
import {
  createExistingObjectLinkIntentProposal,
  createGraphReviewLocalAuthoringIdFactory,
  createNodeAssertionProposal,
  createNodeFromSpanProposal,
  createRelationshipAssertionProposal,
  GRAPH_REVIEW_RELATIONSHIP_PREDICATES,
  type GraphReviewRelationshipPredicate,
  resetLocalAuthoringDraft,
  updateLocalProposalStatus,
  type GraphReviewLocalAuthoringIdFactory,
  type GraphReviewLocalAuthoringProposal,
  type GraphReviewLocalAuthoringProposalStatus,
  type GraphReviewRelationshipNodeRef,
} from "./graphReviewLocalAuthoringState";
import type { GraphReviewProjectionLaneRole } from "./GraphReviewProjectionLane";
import type { GraphReviewSelectedNode } from "./graphReviewSelectionUtils";

export type GraphReviewAuthorMode = "review" | "author_draft";

export interface GraphReviewSelectedTextDraft {
  laneRole: GraphReviewProjectionLaneRole;
  text: string;
  sourceOffsets: { start: number; end: number } | null;
}

interface UseGraphReviewAuthorDraftWorkflowOptions {
  idFactory?: GraphReviewLocalAuthoringIdFactory;
  initialProposals?: GraphReviewLocalAuthoringProposal[];
}

/** Ephemeral review notes only; native publication has its own reviewed workflow. */
export function useGraphReviewAuthorDraftWorkflow({
  idFactory,
  initialProposals = [],
}: UseGraphReviewAuthorDraftWorkflowOptions = {}) {
  const [authorMode, setAuthorMode] = useState<GraphReviewAuthorMode>("review");
  const [selectedText, setSelectedText] =
    useState<GraphReviewSelectedTextDraft | null>(null);
  const [relationshipDraftSource, setRelationshipDraftSource] =
    useState<GraphReviewSelectedNode | null>(null);
  const [relationshipPredicate, setRelationshipPredicate] =
    useState<GraphReviewRelationshipPredicate>(
      GRAPH_REVIEW_RELATIONSHIP_PREDICATES[0],
    );
  const [localProposals, setLocalProposals] =
    useState<GraphReviewLocalAuthoringProposal[]>(initialProposals);
  const [localProposalFactory] = useState(
    () => idFactory ?? createGraphReviewLocalAuthoringIdFactory(),
  );
  const stageNodeFromSpan = useCallback(() => {
    if (!selectedText?.text.trim()) return;
    setLocalProposals((current) => [
      ...current,
      createNodeFromSpanProposal(localProposalFactory, {
        laneRole: selectedText.laneRole,
        sourceText: selectedText.text.trim(),
        sourceOffsets: selectedText.sourceOffsets,
        suggestedLabel: selectedText.text.trim(),
        suggestedKind: null,
      }),
    ]);
  }, [localProposalFactory, selectedText]);

  const stageNodeAssertion = useCallback(
    (input: Parameters<typeof createNodeAssertionProposal>[1]) => {
      setLocalProposals((current) => [
        ...current,
        createNodeAssertionProposal(localProposalFactory, input),
      ]);
    },
    [localProposalFactory],
  );

  const stageRelationshipAssertion = useCallback(
    (input: {
      sourceNode: GraphReviewRelationshipNodeRef;
      targetNode: GraphReviewRelationshipNodeRef;
      predicate: string;
    }) => {
      setLocalProposals((current) => [
        ...current,
        createRelationshipAssertionProposal(localProposalFactory, input),
      ]);
    },
    [localProposalFactory],
  );

  const stageExistingObjectLinkIntent = useCallback(
    (input: {
      selectedNode: GraphReviewRelationshipNodeRef;
      candidate: GraphReviewExistingObjectCandidate & { candidateId?: string };
    }) => {
      setLocalProposals((current) => [
        ...current,
        createExistingObjectLinkIntentProposal(localProposalFactory, {
          selectedNode: input.selectedNode,
          candidate: {
            ...input.candidate,
            candidateId:
              input.candidate.candidateId ?? input.candidate.candidate_id,
          },
        }),
      ]);
    },
    [localProposalFactory],
  );

  const updateProposalStatus = useCallback(
    (proposalId: string, status: GraphReviewLocalAuthoringProposalStatus) => {
      setLocalProposals((current) =>
        updateLocalProposalStatus(current, proposalId, status),
      );
    },
    [],
  );

  const resetLocalDraft = useCallback(() => {
    setLocalProposals(resetLocalAuthoringDraft());
    setSelectedText(null);
    setRelationshipDraftSource(null);
  }, []);

  return {
    authorMode,
    setAuthorMode,
    localProposals,
    setLocalProposals,
    selectedText,
    setSelectedText,
    relationshipDraftSource,
    setRelationshipDraftSource,
    relationshipPredicate,
    setRelationshipPredicate,
    stageNodeFromSpan,
    stageNodeAssertion,
    stageRelationshipAssertion,
    stageExistingObjectLinkIntent,
    updateProposalStatus,
    resetLocalDraft,
  };
}

export type GraphReviewAuthorDraftWorkflow = ReturnType<
  typeof useGraphReviewAuthorDraftWorkflow
>;
