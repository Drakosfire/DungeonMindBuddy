import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { commitGraphGoldAuthoringPreview, prepareGraphGoldAuthoringPreview } from "../../api/liveApi";
import type {
  GraphGoldAuthoringCommitResponse,
  GraphGoldAuthoringPrepareRequest,
  GraphGoldAuthoringPrepareResponse,
  GraphGoldAuthoringVerifyCommitResponse,
  GraphReviewExistingObjectCandidate,
} from "../../api/types";
import { buildGraphGoldAuthoringPrepareRequest } from "./graphReviewAuthoringPrepareApi";
import {
  createExistingObjectLinkIntentProposal,
  createGraphReviewLocalAuthoringIdFactory,
  createNodeAssertionProposal,
  createNodeFromSpanProposal,
  createRelationshipAssertionProposal,
  GRAPH_REVIEW_RELATIONSHIP_PREDICATES,
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
export type GraphReviewPrepareStatus = "idle" | "loading" | "ready" | "blocked" | "error";
export type GraphReviewCommitStatus = "idle" | "loading" | "success" | "blocked" | "error";
export type GraphReviewVerificationStatus = "idle" | "loading" | "ready" | "error";

export interface GraphReviewSelectedTextDraft {
  laneRole: GraphReviewProjectionLaneRole;
  text: string;
  sourceOffsets: { start: number; end: number } | null;
}

interface UseGraphReviewAuthorDraftWorkflowOptions {
  campaignId: string;
  sessionId: string;
  idFactory?: GraphReviewLocalAuthoringIdFactory;
  onReloadAndVerifyCommit?: (
    commitResponse: GraphGoldAuthoringCommitResponse,
  ) => Promise<GraphGoldAuthoringVerifyCommitResponse>;
  initialProposals?: GraphReviewLocalAuthoringProposal[];
}

function friendlyError(error: unknown, fallback: string): string {
  return error instanceof Error ? error.message : fallback;
}

export function useGraphReviewAuthorDraftWorkflow({
  campaignId,
  sessionId,
  idFactory,
  onReloadAndVerifyCommit,
  initialProposals = [],
}: UseGraphReviewAuthorDraftWorkflowOptions) {
  const [authorMode, setAuthorMode] = useState<GraphReviewAuthorMode>("review");
  const [selectedText, setSelectedText] = useState<GraphReviewSelectedTextDraft | null>(null);
  const [relationshipDraftSource, setRelationshipDraftSource] = useState<GraphReviewSelectedNode | null>(null);
  const [relationshipPredicate, setRelationshipPredicate] = useState(
    GRAPH_REVIEW_RELATIONSHIP_PREDICATES[0],
  );
  const [localProposals, setLocalProposals] = useState<GraphReviewLocalAuthoringProposal[]>(initialProposals);
  const [localProposalFactory] = useState(
    () => idFactory ?? createGraphReviewLocalAuthoringIdFactory(),
  );
  const [prepareStatus, setPrepareStatus] = useState<GraphReviewPrepareStatus>("idle");
  const [prepareResponse, setPrepareResponse] = useState<GraphGoldAuthoringPrepareResponse | null>(null);
  const [prepareError, setPrepareError] = useState<string | null>(null);
  const [preparedRequest, setPreparedRequest] = useState<GraphGoldAuthoringPrepareRequest | null>(null);
  const [commitConfirmed, setCommitConfirmed] = useState(false);
  const [commitStatus, setCommitStatus] = useState<GraphReviewCommitStatus>("idle");
  const [commitResponse, setCommitResponse] = useState<GraphGoldAuthoringCommitResponse | null>(null);
  const [commitError, setCommitError] = useState<string | null>(null);
  const [verificationStatus, setVerificationStatus] = useState<GraphReviewVerificationStatus>("idle");
  const [verificationResponse, setVerificationResponse] = useState<GraphGoldAuthoringVerifyCommitResponse | null>(null);
  const [verificationError, setVerificationError] = useState<string | null>(null);

  const proposalSignature = useMemo(
    () => JSON.stringify({ campaignId, sessionId, localProposals }),
    [campaignId, sessionId, localProposals],
  );

  const clearPreparedState = useCallback(() => {
    setPrepareStatus("idle");
    setPrepareResponse(null);
    setPrepareError(null);
    setPreparedRequest(null);
    setCommitConfirmed(false);
    setCommitStatus("idle");
    setCommitResponse(null);
    setCommitError(null);
    setVerificationStatus("idle");
    setVerificationResponse(null);
    setVerificationError(null);
  }, []);

  const lastProposalSignature = useRef(proposalSignature);

  useEffect(() => {
    if (lastProposalSignature.current === proposalSignature) return;
    lastProposalSignature.current = proposalSignature;
    if (prepareResponse) clearPreparedState();
  }, [proposalSignature, prepareResponse, clearPreparedState]);

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

  const stageNodeAssertion = useCallback((input: Parameters<typeof createNodeAssertionProposal>[1]) => {
    setLocalProposals((current) => [...current, createNodeAssertionProposal(localProposalFactory, input)]);
  }, [localProposalFactory]);

  const stageRelationshipAssertion = useCallback((input: { sourceNode: GraphReviewRelationshipNodeRef; targetNode: GraphReviewRelationshipNodeRef; predicate: string }) => {
    setLocalProposals((current) => [...current, createRelationshipAssertionProposal(localProposalFactory, input)]);
  }, [localProposalFactory]);

  const stageExistingObjectLinkIntent = useCallback((input: { selectedNode: GraphReviewRelationshipNodeRef; candidate: GraphReviewExistingObjectCandidate & { candidateId?: string } }) => {
    setLocalProposals((current) => [
      ...current,
      createExistingObjectLinkIntentProposal(localProposalFactory, {
        selectedNode: input.selectedNode,
        candidate: { ...input.candidate, candidateId: input.candidate.candidateId ?? input.candidate.candidate_id },
      }),
    ]);
  }, [localProposalFactory]);

  const updateProposalStatus = useCallback((proposalId: string, status: GraphReviewLocalAuthoringProposalStatus) => {
    setLocalProposals((current) => updateLocalProposalStatus(current, proposalId, status));
  }, []);

  const resetLocalDraft = useCallback(() => {
    setLocalProposals(resetLocalAuthoringDraft());
    setSelectedText(null);
    setRelationshipDraftSource(null);
    clearPreparedState();
  }, [clearPreparedState]);

  const preparePreview = useCallback(async () => {
    setPrepareStatus("loading");
    setPrepareError(null);
    setPrepareResponse(null);
    const request = buildGraphGoldAuthoringPrepareRequest({ campaignId, sessionId, proposals: localProposals.filter((proposal) => proposal.status !== "rejected_local") });
    try {
      const result = await prepareGraphGoldAuthoringPreview(request);
      setPrepareResponse(result);
      setPreparedRequest(request);
      setPrepareStatus(result.validation_status === "blocked" ? "blocked" : "ready");
      setCommitConfirmed(false);
      setCommitStatus("idle");
      setCommitResponse(null);
      setCommitError(null);
      setVerificationStatus("idle");
      setVerificationResponse(null);
      setVerificationError(null);
    } catch (error) {
      setPrepareStatus("error");
      setPrepareError(friendlyError(error, "Could not prepare write preview."));
    }
  }, [campaignId, sessionId, localProposals]);

  const commitPreparedPreview = useCallback(async () => {
    if (!prepareResponse || !preparedRequest || prepareResponse.validation_status === "blocked" || !commitConfirmed) return;
    setCommitStatus("loading");
    setCommitError(null);
    setCommitResponse(null);
    try {
      const result = await commitGraphGoldAuthoringPreview({ schema: "dmb_graph_gold_authoring_commit_request_v1", campaign_id: campaignId, session_id: sessionId, fixture_version: preparedRequest.fixture_version, proposals: preparedRequest.proposals, expected_prepare_fingerprint: prepareResponse.prepare_fingerprint });
      setCommitResponse(result);
      setCommitStatus(result.commit_status === "blocked" ? "blocked" : "success");
      setVerificationStatus("idle");
      setVerificationResponse(null);
      setVerificationError(null);
    } catch (error) {
      setCommitStatus("error");
      setCommitError(friendlyError(error, "Could not commit prepared preview."));
    }
  }, [campaignId, sessionId, commitConfirmed, prepareResponse, preparedRequest]);

  const reloadAndVerifyCommit = useCallback(async () => {
    if (!commitResponse || !onReloadAndVerifyCommit) return;
    setVerificationStatus("loading");
    setVerificationError(null);
    try {
      const result = await onReloadAndVerifyCommit(commitResponse);
      setVerificationResponse(result);
      setVerificationStatus("ready");
    } catch (error) {
      setVerificationStatus("error");
      setVerificationError(friendlyError(error, "Could not reload and verify gold projection."));
    }
  }, [commitResponse, onReloadAndVerifyCommit]);

  return {
    authorMode, setAuthorMode,
    localProposals, setLocalProposals, selectedText, setSelectedText,
    relationshipDraftSource, setRelationshipDraftSource,
    relationshipPredicate, setRelationshipPredicate,
    preparedRequest, prepareResponse, commitResponse, verificationResponse,
    prepareStatus, commitStatus, verificationStatus,
    prepareError, commitError, verificationError,
    commitConfirmed, setCommitConfirmed,
    stageNodeFromSpan, stageNodeAssertion, stageRelationshipAssertion, stageExistingObjectLinkIntent,
    updateProposalStatus, resetLocalDraft, preparePreview, commitPreparedPreview, reloadAndVerifyCommit, clearPreparedState,
  };
}

export type GraphReviewAuthorDraftWorkflow = ReturnType<typeof useGraphReviewAuthorDraftWorkflow>;
