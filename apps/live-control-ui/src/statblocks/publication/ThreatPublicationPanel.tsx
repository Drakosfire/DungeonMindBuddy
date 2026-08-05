import { useEffect, useMemo, useReducer, useRef, useState } from "react";

import type {
  CreateThreatIdentityResolutionRequestV1,
  PrepareThreatPublicationProposalRequestV1,
  ThreatDraftV1,
  ThreatIdentityCandidateSetV1,
  ThreatIdentityDecision,
  ThreatPublicationCommitResponseV1,
  ThreatPublicationCommitV1,
  ThreatPublicationIdentityResolutionV1,
  ThreatPublicationIdentityResponseV1,
  ThreatPublicationOperationResponseV1,
  ThreatPublicationOperationV1,
  ThreatPublicationProposalResponseV1,
  ThreatPublicationProposalV1,
} from "../../api/types";
import {
  beginThreatPublicationOperation,
  cancelThreatPublicationOperation,
  confirmThreatPublicationCommit,
  createThreatIdentityResolution,
  getThreatIdentityResolution,
  getThreatPublicationCommit,
  getThreatPublicationOperation,
  getThreatPublicationProposal,
  prepareThreatIdentityCandidates,
  prepareThreatPublicationProposal,
  refreshThreatPublicationOperation,
  retryThreatPublicationOperation,
} from "../../api/liveApi";
import {
  SESSION_SCHEMA,
  clearThreatPublicationSession,
  readThreatPublicationSession,
  writeThreatPublicationSession,
  type ThreatPublicationSessionStage,
  type ThreatPublicationWorkbenchSessionV1,
} from "./threatPublicationSession";
import {
  canCreateNewThreatIdentity,
  isThreatDraftEligibleForPublication,
  unrejectedExactCollisionNodeIds,
} from "./threatPublicationViewModel";

export type ThreatPublicationApi = {
  beginThreatPublicationOperation: typeof beginThreatPublicationOperation;
  getThreatPublicationOperation: typeof getThreatPublicationOperation;
  refreshThreatPublicationOperation: typeof refreshThreatPublicationOperation;
  cancelThreatPublicationOperation: typeof cancelThreatPublicationOperation;
  retryThreatPublicationOperation: typeof retryThreatPublicationOperation;
  prepareThreatIdentityCandidates: typeof prepareThreatIdentityCandidates;
  createThreatIdentityResolution: typeof createThreatIdentityResolution;
  getThreatIdentityResolution: typeof getThreatIdentityResolution;
  prepareThreatPublicationProposal: typeof prepareThreatPublicationProposal;
  getThreatPublicationProposal: typeof getThreatPublicationProposal;
  confirmThreatPublicationCommit: typeof confirmThreatPublicationCommit;
  getThreatPublicationCommit: typeof getThreatPublicationCommit;
};

export type ThreatPublicationDockTone = "info" | "error" | "success";

export interface ThreatPublicationDockAction {
  testId: string;
  label: string;
  disabled?: boolean;
  onClick: () => void;
}

/** Compact status + primary actions for the Workbench floating dock. */
export interface ThreatPublicationDockModel {
  status: string;
  tone: ThreatPublicationDockTone;
  actions: ThreatPublicationDockAction[];
}

export interface ThreatPublicationPanelProps {
  /** Must be workflow_state === "mechanics_saved" with an accepted_mechanics_ref. */
  draft: ThreatDraftV1;
  expectedParentRevisionId: string;
  /**
   * Re-resolve the current World Graph head before operation retry.
   * Required for governed retry; when omitted, the prop head is reused.
   */
  resolveExpectedParentRevisionId?: () => Promise<string>;
  actor?: string;
  /** Tests inject mocks here; production uses the real liveApi client by default. */
  api?: Partial<ThreatPublicationApi>;
  storage?: Storage;
  generateId?: () => string;
  /**
   * When set, primary journey CTAs are driven through the Workbench floating dock
   * and the panel keeps review surfaces (candidates / proposal / commit detail).
   */
  onDockModelChange?: (model: ThreatPublicationDockModel | null) => void;
}

const DEFAULT_ACTOR = "workbench-gm";

/** Read live module bindings so vitest spies on `liveApi` apply in the Workbench path. */
function defaultThreatPublicationApi(): ThreatPublicationApi {
  return {
    beginThreatPublicationOperation,
    getThreatPublicationOperation,
    refreshThreatPublicationOperation,
    cancelThreatPublicationOperation,
    retryThreatPublicationOperation,
    prepareThreatIdentityCandidates,
    createThreatIdentityResolution,
    getThreatIdentityResolution,
    prepareThreatPublicationProposal,
    getThreatPublicationProposal,
    confirmThreatPublicationCommit,
    getThreatPublicationCommit,
  };
}

function defaultGenerateId(): string {
  return crypto.randomUUID();
}

function errorMessage(err: unknown): string {
  return err instanceof Error ? err.message : String(err);
}

function hasCommittedRevision(
  commit: ThreatPublicationCommitV1 | null,
  resultLabel: string | null,
): boolean {
  if (!commit?.committed_revision_id) return false;
  return (
    resultLabel === "publication_commit_verified"
    || resultLabel === "publication_commit_committed_unverified"
  );
}

interface PanelState {
  mode: "idle" | "version_mismatch" | "busy_unknown" | "recovery_error" | "active";
  pending: boolean;
  lastError: string | null;
  operationId: string | null;
  operation: ThreatPublicationOperationV1 | null;
  operationResultLabel: string | null;
  operationMessage: string | null;
  candidateSet: ThreatIdentityCandidateSetV1 | null;
  candidateMessage: string | null;
  rejectedCandidateIds: string[];
  connectTargetId: string | null;
  /** Proposed or settled resolution id; retained under transport uncertainty. */
  resolutionId: string | null;
  resolution: ThreatPublicationIdentityResolutionV1 | null;
  pendingIdentityRequest: CreateThreatIdentityResolutionRequestV1 | null;
  identityMessage: string | null;
  /** Proposed or settled proposal id; retained under transport uncertainty. */
  proposalId: string | null;
  proposal: ThreatPublicationProposalV1 | null;
  pendingProposalRequest: PrepareThreatPublicationProposalRequestV1 | null;
  proposalMessage: string | null;
  commitId: string | null;
  commit: ThreatPublicationCommitV1 | null;
  commitResultLabel: string | null;
  commitMessage: string | null;
  retryAllowed: boolean;
  recoveryDetail: string | null;
  busyMessage: string | null;
  versionMismatchPointer: ThreatPublicationWorkbenchSessionV1 | null;
}

function initialPanelState(): PanelState {
  return {
    mode: "idle",
    pending: false,
    lastError: null,
    operationId: null,
    operation: null,
    operationResultLabel: null,
    operationMessage: null,
    candidateSet: null,
    candidateMessage: null,
    rejectedCandidateIds: [],
    connectTargetId: null,
    resolutionId: null,
    resolution: null,
    pendingIdentityRequest: null,
    identityMessage: null,
    proposalId: null,
    proposal: null,
    pendingProposalRequest: null,
    proposalMessage: null,
    commitId: null,
    commit: null,
    commitResultLabel: null,
    commitMessage: null,
    retryAllowed: false,
    recoveryDetail: null,
    busyMessage: null,
    versionMismatchPointer: null,
  };
}

type OperationResultSource = "begin" | "restore" | "refresh" | "cancel" | "retry";

type Action =
  | { type: "reset" }
  | { type: "restorePending" }
  | { type: "beginPending"; operationId: string }
  | { type: "retryPending" }
  | { type: "cancelPending" }
  | {
      type: "operationResult";
      response: ThreatPublicationOperationResponseV1;
      localOperationId: string | null;
      source: OperationResultSource;
    }
  | { type: "candidatesPending" }
  | { type: "candidatesResult"; response: ThreatPublicationIdentityResponseV1 }
  | { type: "toggleRejected"; nodeId: string }
  | { type: "setConnectTarget"; nodeId: string }
  | {
      type: "identityDecisionPending";
      resolutionId: string;
      request: CreateThreatIdentityResolutionRequestV1;
    }
  | { type: "identityResult"; response: ThreatPublicationIdentityResponseV1; accepted: boolean }
  | { type: "identityTransportError"; message: string }
  | {
      type: "proposalPending";
      proposalId: string;
      request: PrepareThreatPublicationProposalRequestV1;
    }
  | { type: "proposalResult"; response: ThreatPublicationProposalResponseV1; accepted: boolean }
  | { type: "proposalTransportError"; message: string }
  | { type: "confirmPending"; commitId: string }
  | { type: "commitResult"; response: ThreatPublicationCommitResponseV1 }
  | { type: "commitTransportError"; message: string }
  | { type: "genericError"; message: string }
  | { type: "beginRejected"; message: string | null; resultLabel: string }
  | { type: "versionMismatch"; pointer: ThreatPublicationWorkbenchSessionV1 }
  | { type: "recoveryError"; detail: string }
  | { type: "clearPointer" }
  | { type: "refuseReleased"; message: string };

function reducer(state: PanelState, action: Action): PanelState {
  switch (action.type) {
    case "reset":
      return initialPanelState();
    case "restorePending":
      return { ...initialPanelState(), mode: "active", pending: true };
    case "beginPending":
      return { ...initialPanelState(), mode: "active", pending: true, operationId: action.operationId };
    case "retryPending":
      // Keep the recoverable predecessor until the server accepts a ready successor.
      return { ...state, pending: true, lastError: null };
    case "cancelPending":
      return { ...state, pending: true, lastError: null };
    case "operationResult": {
      const { response, localOperationId, source } = action;
      if (source === "begin" && response.result_label === "publication_busy") {
        // When the server names the blocker, keep its operation_id so Cancel can release it.
        return {
          ...initialPanelState(),
          mode: "busy_unknown",
          busyMessage: response.message ?? null,
          operationId: response.operation?.operation_id ?? null,
          operation: response.operation ?? null,
          operationResultLabel: response.result_label,
          operationMessage: response.message ?? null,
        };
      }
      // Only an exact cancelled record terminalizes cancellation into a fresh begin path.
      if (response.result_label === "publication_cancelled") {
        return {
          ...initialPanelState(),
          lastError: response.message ?? "Publication cancelled.",
        };
      }
      const nextOperationId =
        response.operation?.operation_id
        ?? localOperationId
        ?? state.operationId;
      const clearDownstream =
        source === "retry"
        && response.result_label === "publication_ready"
        && response.operation?.operation_id
        && response.operation.operation_id !== state.operationId;
      return {
        ...state,
        mode: "active",
        pending: false,
        operationId: nextOperationId,
        operation: response.operation ?? state.operation,
        operationResultLabel: response.result_label,
        operationMessage: response.message ?? null,
        ...(clearDownstream
          ? {
              candidateSet: null,
              candidateMessage: null,
              rejectedCandidateIds: [],
              connectTargetId: null,
              resolutionId: null,
              resolution: null,
              pendingIdentityRequest: null,
              identityMessage: null,
              proposalId: null,
              proposal: null,
              pendingProposalRequest: null,
              proposalMessage: null,
              commitId: null,
              commit: null,
              commitResultLabel: null,
              commitMessage: null,
              retryAllowed: false,
            }
          : {}),
      };
    }
    case "candidatesPending":
      return { ...state, pending: true, candidateMessage: null, lastError: null };
    case "candidatesResult": {
      const { response } = action;
      if (response.result_label === "publication_identity_candidates_ready" && response.candidate_set) {
        return {
          ...state,
          pending: false,
          candidateSet: response.candidate_set,
          candidateMessage: null,
          rejectedCandidateIds: [],
          connectTargetId: null,
        };
      }
      if (response.result_label === "publication_identity_candidate_set_changed") {
        return {
          ...state,
          pending: false,
          candidateSet: null,
          candidateMessage:
            response.message ?? "Candidate set changed. Refresh candidates and review again.",
          rejectedCandidateIds: [],
          connectTargetId: null,
          resolutionId: null,
          resolution: null,
          pendingIdentityRequest: null,
          identityMessage: null,
        };
      }
      return {
        ...state,
        pending: false,
        candidateMessage: response.message ?? "Identity candidates could not be prepared.",
      };
    }
    case "toggleRejected": {
      const already = state.rejectedCandidateIds.includes(action.nodeId);
      if (already) {
        return {
          ...state,
          rejectedCandidateIds: state.rejectedCandidateIds.filter((id) => id !== action.nodeId),
        };
      }
      return {
        ...state,
        rejectedCandidateIds: [...state.rejectedCandidateIds, action.nodeId],
        connectTargetId: state.connectTargetId === action.nodeId ? null : state.connectTargetId,
      };
    }
    case "setConnectTarget":
      return {
        ...state,
        connectTargetId: action.nodeId,
        rejectedCandidateIds: state.rejectedCandidateIds.filter((id) => id !== action.nodeId),
      };
    case "identityDecisionPending":
      return {
        ...state,
        pending: true,
        resolutionId: action.resolutionId,
        pendingIdentityRequest: action.request,
        identityMessage: null,
        lastError: null,
      };
    case "identityResult": {
      const { response, accepted } = action;
      if (response.result_label === "publication_identity_candidate_set_changed") {
        return {
          ...state,
          pending: false,
          candidateSet: null,
          candidateMessage:
            response.message ?? "Candidate set changed. Refresh candidates and review again.",
          rejectedCandidateIds: [],
          connectTargetId: null,
          resolutionId: null,
          resolution: null,
          pendingIdentityRequest: null,
          identityMessage: null,
        };
      }
      if (accepted && response.resolution) {
        return {
          ...state,
          pending: false,
          resolutionId: response.resolution.resolution_id,
          resolution: response.resolution,
          pendingIdentityRequest: null,
          identityMessage: null,
          // Refuse is terminal for this operation — drop candidate review so the UI cannot
          // look "stuck" waiting for the next stage.
          candidateSet:
            response.resolution.decision === "refuse" ? null : state.candidateSet,
          candidateMessage: null,
        };
      }
      // Definitive typed rejection: clear uncertain resolution pointer from state.
      return {
        ...state,
        pending: false,
        resolutionId: null,
        resolution: null,
        pendingIdentityRequest: null,
        identityMessage: response.message ?? "Identity decision could not be recorded.",
      };
    }
    case "identityTransportError":
      return {
        ...state,
        pending: false,
        identityMessage: action.message,
      };
    case "proposalPending":
      return {
        ...state,
        pending: true,
        proposalId: action.proposalId,
        pendingProposalRequest: action.request,
        proposalMessage: null,
        lastError: null,
      };
    case "proposalResult": {
      const { response, accepted } = action;
      if (accepted && response.proposal) {
        return {
          ...state,
          pending: false,
          proposalId: response.proposal.proposal_id,
          proposal: response.proposal,
          pendingProposalRequest: null,
          proposalMessage: null,
        };
      }
      return {
        ...state,
        pending: false,
        proposalId: null,
        proposal: null,
        pendingProposalRequest: null,
        proposalMessage: response.message ?? "Publication proposal could not be prepared.",
      };
    }
    case "proposalTransportError":
      return {
        ...state,
        pending: false,
        proposalMessage: action.message,
      };
    case "confirmPending":
      return { ...state, pending: true, commitId: action.commitId, commitMessage: null, lastError: null };
    case "commitResult": {
      const { response } = action;
      // Typed response with no durable commit record: roll back to proposal stage.
      if (!response.commit) {
        return {
          ...state,
          pending: false,
          commitId: null,
          commit: null,
          commitResultLabel: response.result_label,
          commitMessage: response.message ?? null,
          retryAllowed: false,
        };
      }
      return {
        ...state,
        pending: false,
        commitId: response.commit.commit_id,
        commit: response.commit,
        commitResultLabel: response.result_label,
        commitMessage: response.message ?? null,
        retryAllowed: response.retry_allowed,
      };
    }
    case "commitTransportError":
      return { ...state, pending: false, commitMessage: action.message };
    case "genericError":
      return { ...state, pending: false, lastError: action.message };
    case "beginRejected":
      return {
        ...initialPanelState(),
        mode: "idle",
        lastError: action.message ?? `Publication could not begin (${action.resultLabel}).`,
      };
    case "versionMismatch":
      return { ...initialPanelState(), mode: "version_mismatch", versionMismatchPointer: action.pointer };
    case "recoveryError":
      return { ...initialPanelState(), mode: "recovery_error", recoveryDetail: action.detail };
    case "clearPointer":
      return initialPanelState();
    case "refuseReleased":
      // Terminal refuse that also released the server active lock — back to Publish.
      return {
        ...initialPanelState(),
        lastError: action.message,
      };
    default:
      return state;
  }
}

export function ThreatPublicationPanel(props: ThreatPublicationPanelProps): JSX.Element {
  const {
    draft,
    expectedParentRevisionId,
    resolveExpectedParentRevisionId,
    actor = DEFAULT_ACTOR,
    api: apiOverrides,
    storage,
    generateId = defaultGenerateId,
    onDockModelChange,
  } = props;

  const api = useMemo(
    () => ({ ...defaultThreatPublicationApi(), ...apiOverrides }),
    [apiOverrides],
  );
  const eligible = isThreatDraftEligibleForPublication(draft, expectedParentRevisionId);
  const dockDriven = typeof onDockModelChange === "function";
  const acceptedMechanicsKey = draft.accepted_mechanics_ref
    ? [
        draft.accepted_mechanics_ref.statblock_id,
        draft.accepted_mechanics_ref.revision_id,
        draft.accepted_mechanics_ref.definition_digest,
      ].join(":")
    : "";

  const [state, dispatch] = useReducer(reducer, undefined, initialPanelState);
  const generationRef = useRef(0);
  const autoPreparedCandidatesForOpRef = useRef<string | null>(null);
  const autoPreparedProposalForResolutionRef = useRef<string | null>(null);
  const identityCandidatesRef = useRef<HTMLDivElement | null>(null);
  const proposalReviewRef = useRef<HTMLDivElement | null>(null);
  const onDockModelChangeRef = useRef(onDockModelChange);
  onDockModelChangeRef.current = onDockModelChange;
  /** Blocks dock-driven auto-prepare until session restore finishes (avoids refuse/resolution races). */
  const [restoreGate, setRestoreGate] = useState<"idle" | "restoring" | "done">("idle");

  function isCurrent(generation: number): boolean {
    return generationRef.current === generation;
  }

  function buildPointer(overrides: {
    stage: ThreatPublicationSessionStage;
    operationId?: string;
    resolutionId?: string | null;
    proposalId?: string | null;
    commitId?: string | null;
  }): ThreatPublicationWorkbenchSessionV1 {
    return {
      schema: SESSION_SCHEMA,
      draft_id: draft.draft_id,
      draft_version: draft.version,
      operation_id: overrides.operationId ?? state.operationId ?? "",
      resolution_id: overrides.resolutionId ?? null,
      proposal_id: overrides.proposalId ?? null,
      commit_id: overrides.commitId ?? null,
      stage: overrides.stage,
      updated_at: new Date().toISOString(),
    };
  }

  async function restoreFromSession(generation: number): Promise<void> {
    const pointer = readThreatPublicationSession(draft.draft_id, storage);
    if (!pointer) return;
    if (pointer.draft_version !== draft.version) {
      if (!isCurrent(generation)) return;
      dispatch({ type: "versionMismatch", pointer });
      return;
    }

    dispatch({ type: "restorePending" });
    try {
      let activePointer = pointer;
      let operationResponse = await api.getThreatPublicationOperation(draft.draft_id, activePointer.operation_id);
      if (!isCurrent(generation)) return;

      // Lost successful retry: predecessor is superseded; follow exact server lineage.
      if (
        operationResponse.result_label === "publication_superseded"
        && operationResponse.operation?.superseded_by_operation_id
      ) {
        const successorId = operationResponse.operation.superseded_by_operation_id;
        const successorResponse = await api.getThreatPublicationOperation(draft.draft_id, successorId);
        if (!isCurrent(generation)) return;
        if (
          successorResponse.draft_id !== activePointer.draft_id
          || successorResponse.operation?.operation_id !== successorId
        ) {
          dispatch({
            type: "recoveryError",
            detail: "Superseding publication operation no longer matches the server.",
          });
          return;
        }
        activePointer = {
          schema: SESSION_SCHEMA,
          draft_id: draft.draft_id,
          draft_version: draft.version,
          operation_id: successorId,
          resolution_id: null,
          proposal_id: null,
          commit_id: null,
          stage: "operation",
          updated_at: new Date().toISOString(),
        };
        writeThreatPublicationSession(activePointer, storage);
        operationResponse = successorResponse;
      }

      if (
        operationResponse.draft_id !== activePointer.draft_id
        || operationResponse.operation?.operation_id !== activePointer.operation_id
      ) {
        dispatch({ type: "recoveryError", detail: "Stored publication operation no longer matches the server." });
        return;
      }
      if (
        operationResponse.operation
        && operationResponse.operation.source_snapshot.draft_id !== draft.draft_id
      ) {
        dispatch({
          type: "recoveryError",
          detail: "Publication operation source snapshot does not match the active draft.",
        });
        return;
      }
      dispatch({
        type: "operationResult",
        response: operationResponse,
        localOperationId: activePointer.operation_id,
        source: "restore",
      });
      if (operationResponse.result_label === "publication_cancelled") {
        clearThreatPublicationSession(draft.draft_id, storage);
        return;
      }
      if (operationResponse.result_label !== "publication_ready" || !activePointer.resolution_id) return;

      const identityResponse = await api.getThreatIdentityResolution(
        draft.draft_id,
        activePointer.operation_id,
        activePointer.resolution_id,
      );
      if (!isCurrent(generation)) return;
      if (
        identityResponse.draft_id !== activePointer.draft_id
        || identityResponse.operation_id !== activePointer.operation_id
        || identityResponse.resolution?.resolution_id !== activePointer.resolution_id
      ) {
        dispatch({ type: "recoveryError", detail: "Stored identity resolution no longer matches the server." });
        return;
      }
      dispatch({ type: "identityResult", response: identityResponse, accepted: true });

      const resolutionIsActionable =
        identityResponse.resolution?.state === "active"
        && (identityResponse.resolution.decision === "create_new"
          || identityResponse.resolution.decision === "connect_existing");
      if (!resolutionIsActionable || !activePointer.proposal_id) return;

      const proposalResponse = await api.getThreatPublicationProposal(
        draft.draft_id,
        activePointer.operation_id,
        activePointer.proposal_id,
      );
      if (!isCurrent(generation)) return;
      if (
        proposalResponse.draft_id !== activePointer.draft_id
        || proposalResponse.operation_id !== activePointer.operation_id
        || proposalResponse.proposal?.proposal_id !== activePointer.proposal_id
      ) {
        dispatch({ type: "recoveryError", detail: "Stored publication proposal no longer matches the server." });
        return;
      }
      dispatch({ type: "proposalResult", response: proposalResponse, accepted: true });
      if (proposalResponse.result_label !== "publication_proposal_ready" || !activePointer.commit_id) return;

      const commitResponse = await api.getThreatPublicationCommit(
        draft.draft_id,
        activePointer.operation_id,
        activePointer.commit_id,
      );
      if (!isCurrent(generation)) return;
      if (
        commitResponse.draft_id !== activePointer.draft_id
        || commitResponse.operation_id !== activePointer.operation_id
        || commitResponse.commit_id !== activePointer.commit_id
      ) {
        dispatch({ type: "recoveryError", detail: "Stored publication commit no longer matches the server." });
        return;
      }
      dispatch({ type: "commitResult", response: commitResponse });
    } catch (err) {
      if (!isCurrent(generation)) return;
      dispatch({ type: "recoveryError", detail: errorMessage(err) });
    }
  }

  useEffect(() => {
    generationRef.current += 1;
    const generation = generationRef.current;
    dispatch({ type: "reset" });
    autoPreparedCandidatesForOpRef.current = null;
    autoPreparedProposalForResolutionRef.current = null;
    if (!eligible) {
      setRestoreGate("done");
      return () => {
        generationRef.current += 1;
      };
    }
    setRestoreGate("restoring");
    void restoreFromSession(generation).finally(() => {
      if (generationRef.current === generation) {
        setRestoreGate("done");
      }
    });
    return () => {
      generationRef.current += 1;
    };
    // Re-anchor on exact draft identity, version, and accepted mechanics locator.
    // restoreFromSession reads live props/api/storage from this render's closure.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [draft.draft_id, draft.version, acceptedMechanicsKey]);

  async function handleClickPublish(): Promise<void> {
    const operationId = generateId();
    const generation = generationRef.current;
    const pointer = buildPointer({ stage: "operation", operationId });
    writeThreatPublicationSession(pointer, storage);
    dispatch({ type: "beginPending", operationId });
    try {
      const response = await api.beginThreatPublicationOperation(draft.draft_id, {
        schema: "dmb_begin_threat_publication_operation_request_v1",
        operation_id: operationId,
        expected_draft_version: draft.version,
        expected_parent_revision_id: expectedParentRevisionId,
        actor,
        operator_note: null,
      });
      if (!isCurrent(generation)) return;
      const accepted =
        response.result_label === "publication_ready"
        && response.operation?.operation_id === operationId;
      if (!accepted) {
        // Definitive rejection / busy: do not retain a pointer to a nonexistent operation.
        clearThreatPublicationSession(draft.draft_id, storage);
        if (response.result_label === "publication_busy") {
          dispatch({
            type: "operationResult",
            response,
            localOperationId: null,
            source: "begin",
          });
          return;
        }
        dispatch({
          type: "beginRejected",
          message: response.message ?? null,
          resultLabel: response.result_label,
        });
        return;
      }
      dispatch({ type: "operationResult", response, localOperationId: operationId, source: "begin" });
    } catch (err) {
      if (!isCurrent(generation)) return;
      // Transport uncertainty: keep the proposed operation_id for exact replay/read.
      dispatch({ type: "genericError", message: errorMessage(err) });
    }
  }

  async function handleCancelOperation(): Promise<void> {
    // Cancel is valid before identity/proposal/commit authority exists, after a
    // terminal refuse, and after a terminal uncommitted commit (merge rejected;
    // release the draft lock so Publish can start a fresh operation).
    const refuseTerminal = state.resolution?.decision === "refuse";
    const uncommittedTerminal = state.commitResultLabel === "publication_commit_uncommitted";
    if (
      !state.operationId
      || ((state.resolution || state.resolutionId || state.proposal || state.proposalId || state.commitId)
        && !refuseTerminal
        && !uncommittedTerminal)
    ) {
      return;
    }
    const generation = generationRef.current;
    dispatch({ type: "cancelPending" });
    try {
      const response = await api.cancelThreatPublicationOperation(draft.draft_id, state.operationId, {
        schema: "dmb_cancel_threat_publication_operation_request_v1",
        actor,
        note: null,
      });
      if (!isCurrent(generation)) return;
      if (response.result_label === "publication_cancelled") {
        clearThreatPublicationSession(draft.draft_id, storage);
        dispatch({
          type: "operationResult",
          response,
          localOperationId: state.operationId,
          source: "cancel",
        });
        return;
      }
      // Non-cancel labels remain truthfully classified; do not terminalize or invent a pointer rewrite.
      dispatch({
        type: "operationResult",
        response,
        localOperationId: state.operationId,
        source: "refresh",
      });
    } catch (err) {
      if (!isCurrent(generation)) return;
      dispatch({ type: "genericError", message: errorMessage(err) });
    }
  }

  async function handleRefreshOperation(): Promise<void> {
    if (!state.operationId) return;
    const generation = generationRef.current;
    dispatch({ type: "cancelPending" });
    try {
      const response = await api.refreshThreatPublicationOperation(draft.draft_id, state.operationId);
      if (!isCurrent(generation)) return;
      dispatch({
        type: "operationResult",
        response,
        localOperationId: state.operationId,
        source: "refresh",
      });
    } catch (err) {
      if (!isCurrent(generation)) return;
      dispatch({ type: "genericError", message: errorMessage(err) });
    }
  }

  async function handleRetryOperation(): Promise<void> {
    if (!state.operationId) return;
    if (state.operationResultLabel !== "publication_stale" || state.operation?.state !== "stale") {
      return;
    }
    const previousOperationId = state.operationId;
    const newOperationId = generateId();
    const generation = generationRef.current;
    // Do not advance the session pointer until the server returns a ready successor.
    dispatch({ type: "retryPending" });
    try {
      const refreshed = await api.refreshThreatPublicationOperation(draft.draft_id, previousOperationId);
      if (!isCurrent(generation)) return;
      if (refreshed.result_label !== "publication_stale" || refreshed.operation?.state !== "stale") {
        dispatch({
          type: "operationResult",
          response: refreshed,
          localOperationId: previousOperationId,
          source: "refresh",
        });
        return;
      }

      let parentRevisionId = expectedParentRevisionId;
      if (resolveExpectedParentRevisionId) {
        parentRevisionId = await resolveExpectedParentRevisionId();
        if (!isCurrent(generation)) return;
      }

      const response = await api.retryThreatPublicationOperation(draft.draft_id, previousOperationId, {
        schema: "dmb_retry_threat_publication_operation_request_v1",
        new_operation_id: newOperationId,
        expected_parent_revision_id: parentRevisionId,
        actor,
        operator_note: null,
      });
      if (!isCurrent(generation)) return;

      const acceptedSuccessor =
        response.result_label === "publication_ready"
        && response.operation?.operation_id === newOperationId;
      if (acceptedSuccessor) {
        writeThreatPublicationSession(
          {
            schema: SESSION_SCHEMA,
            draft_id: draft.draft_id,
            draft_version: draft.version,
            operation_id: newOperationId,
            resolution_id: null,
            proposal_id: null,
            commit_id: null,
            stage: "operation",
            updated_at: new Date().toISOString(),
          },
          storage,
        );
        dispatch({
          type: "operationResult",
          response,
          localOperationId: newOperationId,
          source: "retry",
        });
        return;
      }

      // Rejected retry: keep predecessor pointer; retain the server's typed classification.
      dispatch({
        type: "operationResult",
        response: {
          ...response,
          operation: response.operation ?? refreshed.operation ?? state.operation,
        },
        localOperationId: previousOperationId,
        source: "retry",
      });
    } catch (err) {
      if (!isCurrent(generation)) return;
      dispatch({ type: "genericError", message: errorMessage(err) });
    }
  }

  async function handlePrepareCandidates(): Promise<void> {
    if (!state.operationId) return;
    const generation = generationRef.current;
    dispatch({ type: "candidatesPending" });
    try {
      const response = await api.prepareThreatIdentityCandidates(draft.draft_id, state.operationId);
      if (!isCurrent(generation)) return;
      dispatch({ type: "candidatesResult", response });
    } catch (err) {
      if (!isCurrent(generation)) return;
      dispatch({ type: "genericError", message: errorMessage(err) });
    }
  }

  async function submitIdentityDecision(
    decision: ThreatIdentityDecision,
    targetNodeId: string | null,
    reason: string,
    options?: { reuseResolutionId?: string; rejectedIds?: string[] },
  ): Promise<void> {
    if (!state.operationId || !state.candidateSet) return;
    // Uncertainty mode: never mint a replacement ID while a prior attempt is unresolved.
    if (state.resolutionId && !state.resolution && !options?.reuseResolutionId) return;
    const resolutionId = options?.reuseResolutionId ?? state.resolutionId ?? generateId();
    const generation = generationRef.current;
    const rejectedIds =
      options?.rejectedIds
      ?? (decision === "connect_existing" && targetNodeId
        ? state.rejectedCandidateIds.filter((id) => id !== targetNodeId)
        : state.rejectedCandidateIds);
    const request: CreateThreatIdentityResolutionRequestV1 = {
      schema: "dmb_create_threat_identity_resolution_request_v1",
      resolution_id: resolutionId,
      matching_profile: "dmb_threat_identity_match_v1",
      candidate_query: state.candidateSet.candidate_query,
      candidate_set_digest: state.candidateSet.candidate_set_digest,
      decision,
      target_node_id: targetNodeId,
      rejected_candidate_node_ids: rejectedIds,
      actor,
      reason,
      supersedes_resolution_id: null,
    };
    const pointer = buildPointer({ stage: "identity", resolutionId });
    writeThreatPublicationSession(pointer, storage);
    dispatch({ type: "identityDecisionPending", resolutionId, request });
    try {
      const response = await api.createThreatIdentityResolution(draft.draft_id, state.operationId, request);
      if (!isCurrent(generation)) return;
      const settled: readonly string[] = [
        "publication_identity_created_new",
        "publication_identity_connected_existing",
        "publication_identity_refused",
      ];
      const accepted =
        settled.includes(response.result_label)
        && response.resolution?.resolution_id === resolutionId;
      if (!accepted) {
        // Definitive rejection: roll pointer back to last accepted predecessor (operation).
        writeThreatPublicationSession(
          buildPointer({
            stage: "operation",
            operationId: state.operationId,
            resolutionId: null,
            proposalId: null,
            commitId: null,
          }),
          storage,
        );
      }
      dispatch({ type: "identityResult", response, accepted });
      if (accepted && response.resolution?.decision === "refuse" && state.operationId) {
        // Release the server active lock so a later Publish is not publication_busy.
        try {
          const cancelResponse = await api.cancelThreatPublicationOperation(
            draft.draft_id,
            state.operationId,
            {
              schema: "dmb_cancel_threat_publication_operation_request_v1",
              actor,
              note: "released after identity refuse",
            },
          );
          if (!isCurrent(generation)) return;
          clearThreatPublicationSession(draft.draft_id, storage);
          if (cancelResponse.result_label === "publication_cancelled") {
            dispatch({
              type: "refuseReleased",
              message: "Publication refused. No graph write occurred.",
            });
            return;
          }
        } catch {
          clearThreatPublicationSession(draft.draft_id, storage);
          // Keep refuse UI; Start over / Cancel stuck publication can still release the lock.
        }
      }
    } catch (err) {
      if (!isCurrent(generation)) return;
      // Transport uncertainty: keep the proposed resolution_id for exact replay/read.
      dispatch({ type: "identityTransportError", message: errorMessage(err) });
    }
  }

  function handleDecideCreateNew(): void {
    if (!state.candidateSet) return;
    if (!canCreateNewThreatIdentity(state.candidateSet.candidates, new Set(state.rejectedCandidateIds))) return;
    void submitIdentityDecision("create_new", null, "Create new Threat");
  }

  function handleDecideConnect(): void {
    if (!state.connectTargetId) return;
    void submitIdentityDecision("connect_existing", state.connectTargetId, "Connect to existing Threat");
  }

  function handleDecideRefuse(): void {
    void submitIdentityDecision("refuse", null, "Refuse publication");
  }

  async function handleRereadIdentity(): Promise<void> {
    if (!state.operationId || !state.resolutionId || state.resolution) return;
    const generation = generationRef.current;
    dispatch({ type: "cancelPending" });
    try {
      const response = await api.getThreatIdentityResolution(
        draft.draft_id,
        state.operationId,
        state.resolutionId,
      );
      if (!isCurrent(generation)) return;
      const settled: readonly string[] = [
        "publication_identity_created_new",
        "publication_identity_connected_existing",
        "publication_identity_refused",
      ];
      const accepted =
        settled.includes(response.result_label)
        && response.resolution?.resolution_id === state.resolutionId;
      if (accepted) {
        dispatch({ type: "identityResult", response, accepted: true });
        return;
      }
      // Still unresolved or not found: remain in uncertainty with the exact ID.
      dispatch({
        type: "identityTransportError",
        message: response.message ?? "Identity decision is not yet confirmed on the server.",
      });
    } catch (err) {
      if (!isCurrent(generation)) return;
      dispatch({ type: "identityTransportError", message: errorMessage(err) });
    }
  }

  function handleReplayIdentity(): void {
    if (!state.pendingIdentityRequest || !state.resolutionId || state.resolution) return;
    const request = state.pendingIdentityRequest;
    void submitIdentityDecision(
      request.decision,
      request.target_node_id ?? null,
      request.reason,
      {
        reuseResolutionId: state.resolutionId,
        rejectedIds: request.rejected_candidate_node_ids,
      },
    );
  }

  async function handlePrepareProposal(options?: {
    reuseProposalId?: string;
  }): Promise<void> {
    if (!state.operationId || !state.resolution) return;
    // Uncertainty mode: never mint a replacement ID while a prior attempt is unresolved.
    if (state.proposalId && !state.proposal && !options?.reuseProposalId) return;
    const proposalId = options?.reuseProposalId ?? state.proposalId ?? generateId();
    const generation = generationRef.current;
    const request: PrepareThreatPublicationProposalRequestV1 = {
      schema: "dmb_prepare_threat_publication_proposal_request_v1",
      proposal_id: proposalId,
      actor,
      operator_note: null,
      supersedes_proposal_id: null,
    };
    const pointer = buildPointer({
      stage: "proposal",
      resolutionId: state.resolution.resolution_id,
      proposalId,
    });
    writeThreatPublicationSession(pointer, storage);
    dispatch({ type: "proposalPending", proposalId, request });
    try {
      const response = await api.prepareThreatPublicationProposal(
        draft.draft_id,
        state.operationId,
        state.resolution.resolution_id,
        request,
      );
      if (!isCurrent(generation)) return;
      const accepted =
        response.result_label === "publication_proposal_ready"
        && response.proposal?.proposal_id === proposalId;
      if (!accepted) {
        writeThreatPublicationSession(
          buildPointer({
            stage: "identity",
            operationId: state.operationId,
            resolutionId: state.resolution.resolution_id,
            proposalId: null,
            commitId: null,
          }),
          storage,
        );
      }
      dispatch({ type: "proposalResult", response, accepted });
    } catch (err) {
      if (!isCurrent(generation)) return;
      dispatch({ type: "proposalTransportError", message: errorMessage(err) });
    }
  }

  async function handleRereadProposal(): Promise<void> {
    if (!state.operationId || !state.proposalId || state.proposal) return;
    const generation = generationRef.current;
    dispatch({ type: "cancelPending" });
    try {
      const response = await api.getThreatPublicationProposal(
        draft.draft_id,
        state.operationId,
        state.proposalId,
      );
      if (!isCurrent(generation)) return;
      const accepted =
        response.result_label === "publication_proposal_ready"
        && response.proposal?.proposal_id === state.proposalId;
      if (accepted) {
        dispatch({ type: "proposalResult", response, accepted: true });
        return;
      }
      dispatch({
        type: "proposalTransportError",
        message: response.message ?? "Publication proposal is not yet confirmed on the server.",
      });
    } catch (err) {
      if (!isCurrent(generation)) return;
      dispatch({ type: "proposalTransportError", message: errorMessage(err) });
    }
  }

  function handleReplayProposal(): void {
    if (!state.pendingProposalRequest || !state.proposalId || state.proposal) return;
    void handlePrepareProposal({ reuseProposalId: state.proposalId });
  }

  async function handleConfirm(): Promise<void> {
    if (!state.operationId || !state.proposal) return;
    if (hasCommittedRevision(state.commit, state.commitResultLabel)) return;
    // Once a commit ID exists, only governed recovery replay may POST again.
    if (state.commitId && !state.retryAllowed) return;

    const commitId = state.commitId ?? generateId();
    const isFirstConfirm = state.commitId == null;
    const generation = generationRef.current;
    if (isFirstConfirm) {
      const pointer = buildPointer({
        stage: "commit",
        resolutionId: state.resolution?.resolution_id ?? state.resolutionId,
        proposalId: state.proposal.proposal_id,
        commitId,
      });
      writeThreatPublicationSession(pointer, storage);
    }
    dispatch({ type: "confirmPending", commitId });
    try {
      const response = await api.confirmThreatPublicationCommit(
        draft.draft_id,
        state.operationId,
        state.proposal.proposal_id,
        {
          schema: "dmb_confirm_threat_publication_request_v1",
          commit_id: commitId,
          sealed_proposal_digest: state.proposal.sealed_proposal_digest,
          expected_parent_revision_id: state.proposal.expected_parent_revision_id,
          actor,
          operator_note: null,
        },
      );
      if (!isCurrent(generation)) return;
      if (!response.commit) {
        // Pre-admission typed rejection: roll local chain back to proposal stage.
        writeThreatPublicationSession(
          buildPointer({
            stage: "proposal",
            operationId: state.operationId,
            resolutionId: state.resolution?.resolution_id ?? state.resolutionId,
            proposalId: state.proposal.proposal_id,
            commitId: null,
          }),
          storage,
        );
      }
      dispatch({ type: "commitResult", response });
    } catch (err) {
      if (!isCurrent(generation)) return;
      dispatch({ type: "commitTransportError", message: errorMessage(err) });
    }
  }

  async function handleRereadCommit(): Promise<void> {
    if (!state.operationId || !state.commitId) return;
    const generation = generationRef.current;
    dispatch({ type: "confirmPending", commitId: state.commitId });
    try {
      const response = await api.getThreatPublicationCommit(draft.draft_id, state.operationId, state.commitId);
      if (!isCurrent(generation)) return;
      if (!response.commit) {
        writeThreatPublicationSession(
          buildPointer({
            stage: "proposal",
            operationId: state.operationId,
            resolutionId: state.resolution?.resolution_id ?? state.resolutionId,
            proposalId: state.proposal?.proposal_id ?? state.proposalId,
            commitId: null,
          }),
          storage,
        );
      }
      dispatch({ type: "commitResult", response });
    } catch (err) {
      if (!isCurrent(generation)) return;
      dispatch({ type: "commitTransportError", message: errorMessage(err) });
    }
  }

  function handleClearPointer(): void {
    clearThreatPublicationSession(draft.draft_id, storage);
    dispatch({ type: "clearPointer" });
  }

  async function handleRereadOperationOnly(): Promise<void> {
    const pointer = state.versionMismatchPointer;
    if (!pointer) return;
    const generation = generationRef.current;
    dispatch({ type: "beginPending", operationId: pointer.operation_id });
    try {
      const response = await api.getThreatPublicationOperation(draft.draft_id, pointer.operation_id);
      if (!isCurrent(generation)) return;
      dispatch({
        type: "operationResult",
        response,
        localOperationId: pointer.operation_id,
        source: "restore",
      });
    } catch (err) {
      if (!isCurrent(generation)) return;
      dispatch({ type: "genericError", message: errorMessage(err) });
    }
  }

  const committed = hasCommittedRevision(state.commit, state.commitResultLabel);

  // Auto-advance (dock-driven product path): prepare candidates once the operation is ready.
  useEffect(() => {
    if (!dockDriven) return;
    if (restoreGate !== "done") return;
    const sessionPointer = readThreatPublicationSession(draft.draft_id, storage);
    // Never auto-prepare while a stored identity/proposal/commit pointer still needs restore.
    if (sessionPointer?.resolution_id || sessionPointer?.proposal_id || sessionPointer?.commit_id) {
      return;
    }
    if (
      state.mode !== "active"
      || state.operationResultLabel !== "publication_ready"
      || !state.operationId
      || state.candidateSet
      || state.resolution
      || state.resolutionId
      || state.pending
    ) {
      return;
    }
    if (autoPreparedCandidatesForOpRef.current === state.operationId) return;
    autoPreparedCandidatesForOpRef.current = state.operationId;
    void handlePrepareCandidates();
    // eslint-disable-next-line react-hooks/exhaustive-deps -- intentional stage trigger
  }, [
    dockDriven,
    restoreGate,
    state.mode,
    state.operationResultLabel,
    state.operationId,
    state.candidateSet,
    state.resolution,
    state.resolutionId,
    state.pending,
  ]);

  // Auto-advance (dock-driven product path): prepare proposal after an actionable identity decision.
  useEffect(() => {
    if (!dockDriven) return;
    if (restoreGate !== "done") return;
    if (
      !state.resolution
      || state.resolution.state !== "active"
      || state.resolution.decision === "refuse"
      || (state.resolution.decision !== "create_new" && state.resolution.decision !== "connect_existing")
      || state.proposal
      || state.proposalId
      || state.pending
    ) {
      return;
    }
    if (autoPreparedProposalForResolutionRef.current === state.resolution.resolution_id) return;
    autoPreparedProposalForResolutionRef.current = state.resolution.resolution_id;
    void handlePrepareProposal();
    // eslint-disable-next-line react-hooks/exhaustive-deps -- intentional stage trigger
  }, [
    dockDriven,
    restoreGate,
    state.resolution,
    state.proposal,
    state.proposalId,
    state.pending,
  ]);

  useEffect(() => {
    if (state.candidateSet && !state.resolution && !state.resolutionId) {
      const node = identityCandidatesRef.current;
      if (node && typeof node.scrollIntoView === "function") {
        node.scrollIntoView({ behavior: "smooth", block: "nearest" });
      }
    }
  }, [state.candidateSet, state.resolution, state.resolutionId]);

  useEffect(() => {
    if (state.proposal) {
      const node = proposalReviewRef.current;
      if (node && typeof node.scrollIntoView === "function") {
        node.scrollIntoView({ behavior: "smooth", block: "nearest" });
      }
    }
  }, [state.proposal]);

  useEffect(() => {
    const notify = onDockModelChangeRef.current;
    if (!notify) return;
    if (!eligible) {
      notify(null);
      return;
    }

    const actions: ThreatPublicationDockAction[] = [];
    let status = "Publish this Threat to the World Graph when ready.";
    let tone: ThreatPublicationDockTone = "info";

    if (state.mode === "version_mismatch") {
      status = "Draft changed since publication started in this browser. Clear the local pointer or re-read status.";
      tone = "error";
      actions.push(
        { testId: "clear-pointer", label: "Clear local pointer", onClick: handleClearPointer },
        {
          testId: "reread-operation-only",
          label: "Re-read publication status only",
          onClick: () => void handleRereadOperationOnly(),
        },
      );
    } else if (state.mode === "busy_unknown") {
      status = state.busyMessage
        ? `Another publication is active: ${state.busyMessage}`
        : "Another publication is active and cannot be safely recovered from this browser.";
      tone = "error";
      if (state.operationId) {
        actions.push({
          testId: "cancel-operation",
          label: "Cancel stuck publication",
          disabled: state.pending,
          onClick: () => void handleCancelOperation(),
        });
      }
    } else if (state.mode === "recovery_error") {
      status = state.recoveryDetail
        ? `Publication could not be restored: ${state.recoveryDetail}`
        : "Publication could not be safely restored in this browser.";
      tone = "error";
      actions.push({ testId: "clear-pointer", label: "Clear local pointer", onClick: handleClearPointer });
    } else if (state.mode === "idle") {
      if (state.lastError) {
        status = state.lastError;
        tone = "error";
      }
      actions.push({
        testId: "publish",
        label: "Publish Threat",
        disabled: state.pending,
        onClick: () => void handleClickPublish(),
      });
    } else if (state.mode === "active") {
      if (committed) {
        if (state.commitResultLabel === "publication_commit_committed_unverified") {
          status = `Published; verification needs attention. Revision ${state.commit?.committed_revision_id ?? "unknown"}.`;
          tone = "error";
        } else {
          status = `Published. Revision ${state.commit?.committed_revision_id ?? "unknown"}.`;
          tone = "success";
        }
        actions.push({
          testId: "reread-commit",
          label: "Re-read commit status",
          disabled: state.pending,
          onClick: () => void handleRereadCommit(),
        });
      } else if (state.resolution?.decision === "refuse") {
        status = "Publication refused. No graph write occurred.";
        actions.push({
          testId: "publication-start-over",
          label: "Start over",
          onClick: handleClearPointer,
        });
      } else if (state.pending && !state.operation && state.mode === "active") {
        status = "Starting publication…";
      } else if (state.proposalId && !state.proposal) {
        status = state.pending
          ? "Preparing publication proposal…"
          : (state.proposalMessage ?? "Proposal confirmation is uncertain. Re-read or replay the same proposal.");
        if (!state.pending) {
          tone = "error";
          actions.push({
            testId: "reread-proposal",
            label: "Re-read proposal",
            onClick: () => void handleRereadProposal(),
          });
          if (state.pendingProposalRequest) {
            actions.push({
              testId: "replay-proposal",
              label: "Replay proposal preparation",
              onClick: handleReplayProposal,
            });
          }
        }
      } else if (state.proposal) {
        status = state.commitMessage && !state.commitId
          ? state.commitMessage
          : "Proposal ready — confirm to publish to the World Graph.";
        if (state.commitMessage && !state.commitId) tone = "error";
        if (!state.commitId) {
          actions.push({
            testId: "confirm",
            label: state.pending ? "Confirming…" : "Confirm publish",
            disabled: state.pending,
            onClick: () => void handleConfirm(),
          });
        } else if (
          state.retryAllowed
          && state.commitResultLabel === "publication_commit_recovery_pending"
        ) {
          status = state.commitMessage ?? "Publication confirmation needs recovery.";
          tone = "error";
          actions.push({
            testId: "retry-confirm",
            label: "Retry confirmation",
            disabled: state.pending,
            onClick: () => void handleConfirm(),
          });
          actions.push({
            testId: "reread-commit",
            label: "Re-read commit status",
            disabled: state.pending,
            onClick: () => void handleRereadCommit(),
          });
        } else if (state.commitResultLabel === "publication_commit_uncommitted") {
          status =
            state.commitMessage
            ?? "Publication did not commit. Cancel and publish again.";
          tone = "error";
          actions.push({
            testId: "cancel-operation",
            label: "Cancel publication",
            disabled: state.pending,
            onClick: () => void handleCancelOperation(),
          });
          actions.push({
            testId: "reread-commit",
            label: "Re-read commit status",
            disabled: state.pending,
            onClick: () => void handleRereadCommit(),
          });
        } else if (state.commitId) {
          status = state.commitMessage ?? "Confirming publication…";
          actions.push({
            testId: "reread-commit",
            label: "Re-read commit status",
            disabled: state.pending,
            onClick: () => void handleRereadCommit(),
          });
        }
      } else if (state.resolutionId && !state.resolution) {
        status = state.pending
          ? "Recording identity decision…"
          : (state.identityMessage ?? "Identity confirmation is uncertain. Re-read or replay the same decision.");
        if (!state.pending) {
          tone = "error";
          actions.push({
            testId: "reread-identity",
            label: "Re-read identity decision",
            onClick: () => void handleRereadIdentity(),
          });
          if (state.pendingIdentityRequest) {
            actions.push({
              testId: "replay-identity",
              label: "Replay identity decision",
              onClick: handleReplayIdentity,
            });
          }
        }
      } else if (state.resolution) {
        if (state.pending && !state.proposal) {
          status = "Preparing publication proposal…";
        } else {
          status = state.proposalMessage
            ?? "Identity recorded. Preparing proposal…";
          if (state.proposalMessage) tone = "error";
        }
      } else if (state.candidateSet) {
        status = state.pending
          ? "Recording identity decision…"
          : `Review ${state.candidateSet.candidates.length} identity candidate(s) below, then choose Create / Connect / Refuse.`;
      } else if (state.operationResultLabel === "publication_stale" && state.operation?.state === "stale") {
        status = state.operationMessage ?? "Publication is stale — retry with the current graph head.";
        tone = "error";
        actions.push({
          testId: "retry-operation",
          label: "Retry publication",
          disabled: state.pending,
          onClick: () => void handleRetryOperation(),
        });
      } else if (state.operationResultLabel === "publication_ready" || state.pending) {
        status = state.pending || !state.candidateSet
          ? "Loading identity candidates…"
          : (state.operationMessage ?? "Publication operation active.");
      } else if (state.operation) {
        status = state.operationMessage ?? "Publication operation active.";
        if (state.lastError) {
          status = state.lastError;
          tone = "error";
        }
      } else if (state.lastError) {
        status = state.lastError;
        tone = "error";
      }

      const canCancel =
        Boolean(state.operationId)
        && !committed
        && (
          (!state.resolution
            && !state.resolutionId
            && !state.proposal
            && !state.proposalId
            && !state.commitId)
          || state.resolution?.decision === "refuse"
          || state.commitResultLabel === "publication_commit_uncommitted"
        );
      if (canCancel && !actions.some((action) => action.testId === "cancel-operation")) {
        actions.push({
          testId: "cancel-operation",
          label: "Cancel publication",
          disabled: state.pending,
          onClick: () => void handleCancelOperation(),
        });
      }
    }

    notify({ status, tone, actions });
    // Handlers are stable enough for dock projection; state fields are the truth trigger.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [
    eligible,
    committed,
    state.mode,
    state.pending,
    state.lastError,
    state.busyMessage,
    state.recoveryDetail,
    state.operationId,
    state.operation,
    state.operationResultLabel,
    state.operationMessage,
    state.candidateSet,
    state.candidateMessage,
    state.resolutionId,
    state.resolution,
    state.identityMessage,
    state.proposalId,
    state.proposal,
    state.proposalMessage,
    state.pendingIdentityRequest,
    state.pendingProposalRequest,
    state.commitId,
    state.commit,
    state.commitResultLabel,
    state.commitMessage,
    state.retryAllowed,
  ]);

  // Clear dock projection only on true unmount — never on every state tick / Strict remount race
  // against a sibling effect that just projected a model.
  useEffect(() => {
    return () => {
      onDockModelChangeRef.current?.(null);
    };
  }, []);

  if (!eligible) {
    return (
      <section data-testid="threat-publication-panel" aria-label="Threat publication">
        <p role="status">
          This Threat needs accepted mechanics and a known World Graph parent revision before it can be published.
        </p>
      </section>
    );
  }

  return (
    <section
      data-testid="threat-publication-panel"
      aria-label="Threat publication"
      className="statblock-publication-entry"
    >
      <h2>Publish to World Graph</h2>

      {state.mode === "idle" && (
        <div>
          {state.lastError && <p role="alert">{state.lastError}</p>}
          {!dockDriven && (
            <button data-testid="publish" onClick={() => void handleClickPublish()}>
              Publish Threat
            </button>
          )}
          {dockDriven && (
            <p className="module-muted" role="status">
              Use Publish Threat in the floating bar.
            </p>
          )}
        </div>
      )}

      {state.mode === "version_mismatch" && (
        <div role="status">
          <p>This draft changed since a publication was started in this browser.</p>
          <button data-testid="clear-pointer" onClick={handleClearPointer}>
            Clear local pointer
          </button>
          <button data-testid="reread-operation-only" onClick={() => void handleRereadOperationOnly()}>
            Re-read publication status only
          </button>
        </div>
      )}

      {state.mode === "busy_unknown" && (
        <div role="status">
          <p>
            Another publication is active
            {state.operationId
              ? " — cancel it to publish again."
              : " and cannot be safely recovered from this browser."}
            {state.busyMessage ? ` ${state.busyMessage}` : ""}
          </p>
          {state.operationId && !dockDriven && (
            <button
              data-testid="cancel-operation"
              disabled={state.pending}
              onClick={() => void handleCancelOperation()}
            >
              Cancel stuck publication
            </button>
          )}
          {state.operationId && dockDriven && (
            <p className="module-muted">Use Cancel stuck publication in the floating bar.</p>
          )}
        </div>
      )}

      {state.mode === "recovery_error" && (
        <div role="status">
          <p>
            This publication could not be safely restored in this browser.
            {state.recoveryDetail ? ` ${state.recoveryDetail}` : ""}
          </p>
          <button data-testid="clear-pointer" onClick={handleClearPointer}>
            Clear local pointer
          </button>
        </div>
      )}

      {state.mode === "active" && (
        <div data-testid="publication-active">
          {state.lastError && <p role="alert">{state.lastError}</p>}

          <div
            role="status"
            data-testid="operation-status"
            data-operation-result={state.operationResultLabel ?? "pending"}
          >
            {!state.operation && state.pending && <p>Starting publication…</p>}
            {state.operation && <p>{state.operationMessage ?? "Publication operation active."}</p>}
            {!state.operation && !state.pending && state.operationMessage && (
              <p>{state.operationMessage}</p>
            )}
            <details>
              <summary>Technical details</summary>
              <p>operation_id: {state.operationId}</p>
              {state.operation?.stale_reasons?.length ? (
                <p>stale_reasons: {state.operation.stale_reasons.join(", ")}</p>
              ) : null}
            </details>
          </div>

          {!dockDriven
            && state.operationId
            && state.operation
            && !committed
            && !state.resolution
            && !state.resolutionId
            && !state.proposal
            && !state.proposalId
            && !state.commitId && (
              <button
                data-testid="refresh-operation"
                disabled={state.pending}
                onClick={() => void handleRefreshOperation()}
              >
                Refresh publication status
              </button>
          )}

          {!state.candidateSet
            && !state.resolution
            && !state.resolutionId
            && state.operationResultLabel === "publication_ready" && (
            <>
              {state.candidateMessage && <p role="alert">{state.candidateMessage}</p>}
              {!dockDriven && (
                <button data-testid="prepare-candidates" disabled={state.pending} onClick={() => void handlePrepareCandidates()}>
                  {state.candidateMessage ? "Refresh candidates" : "Review identity candidates"}
                </button>
              )}
              {dockDriven && state.pending && (
                <p className="module-muted" role="status">Loading identity candidates…</p>
              )}
            </>
          )}

          {!dockDriven
            && state.operationResultLabel === "publication_stale"
            && state.operation?.state === "stale"
            && !state.candidateSet
            && !state.resolution
            && !state.resolutionId
            && !committed && (
              <button data-testid="retry-operation" disabled={state.pending} onClick={() => void handleRetryOperation()}>
                Retry publication
              </button>
          )}

          {state.candidateSet && !state.resolution && !state.resolutionId && (
            <div data-testid="identity-candidates" ref={identityCandidatesRef}>
              <h3>Review identity candidates</h3>
              <p>
                {state.candidateSet.candidates.length} candidate(s) found.{" "}
                {state.candidateSet.exact_collision_count} exact name match(es).
              </p>
              {state.candidateSet.candidates.length === 0 && (
                <p className="module-muted" role="status" data-testid="identity-candidates-empty">
                  No existing Threat matched this draft by name/alias. Create new Threat is the expected path
                  unless you intentionally connect to a node the matcher did not surface.
                </p>
              )}
              {state.candidateMessage && <p role="alert">{state.candidateMessage}</p>}
              <ul>
                {state.candidateSet.candidates.map((candidate) => {
                  const rejected = state.rejectedCandidateIds.includes(candidate.node_id);
                  return (
                    <li key={candidate.node_id}>
                      <h4>
                        {candidate.label} <span>({candidate.role})</span>
                      </h4>
                      {candidate.exact_name_collision && (
                        <span data-testid={`exact-collision-badge-${candidate.node_id}`}>Exact name match</span>
                      )}
                      <p>{candidate.summary ?? "No summary available."}</p>
                      <p>Aliases: {candidate.aliases.join(", ") || "None"}</p>
                      <p>Campaign scope: {candidate.campaign_scope ?? "Unscoped"}</p>
                      <p>
                        {candidate.binding_ids.length} statblock binding(s)
                        {candidate.has_exact_accepted_binding ? " (exact accepted binding present)" : ""}
                      </p>
                      <p>Why matched: {candidate.match_reasons.join(", ") || "No stated reasons"}</p>
                      <label>
                        <input
                          type="checkbox"
                          data-testid={`reject-candidate-${candidate.node_id}`}
                          checked={rejected}
                          onChange={() => dispatch({ type: "toggleRejected", nodeId: candidate.node_id })}
                        />
                        Reject as this Threat
                      </label>
                      <label>
                        <input
                          type="radio"
                          name="threat-publication-connect-target"
                          data-testid={`select-connect-${candidate.node_id}`}
                          checked={state.connectTargetId === candidate.node_id}
                          onChange={() => dispatch({ type: "setConnectTarget", nodeId: candidate.node_id })}
                        />
                        Use this as the existing Threat
                      </label>
                      <details>
                        <summary>Technical details</summary>
                        <p>node_id: {candidate.node_id}</p>
                      </details>
                    </li>
                  );
                })}
              </ul>
              <button
                data-testid="decide-create"
                disabled={
                  state.pending
                  || unrejectedExactCollisionNodeIds(
                    state.candidateSet.candidates,
                    new Set(state.rejectedCandidateIds),
                  ).length > 0
                }
                onClick={handleDecideCreateNew}
              >
                Create new Threat
              </button>
              <button data-testid="decide-connect" disabled={state.pending || !state.connectTargetId} onClick={handleDecideConnect}>
                Connect to existing Threat
              </button>
              <button data-testid="decide-refuse" disabled={state.pending} onClick={handleDecideRefuse}>
                Refuse publication
              </button>
              {state.candidateMessage && (
                <button data-testid="refresh-candidates" disabled={state.pending} onClick={() => void handlePrepareCandidates()}>
                  Refresh candidates
                </button>
              )}
            </div>
          )}

          {state.resolutionId && !state.resolution && (
            <div role="status" data-testid="identity-uncertainty">
              {state.pending ? (
                <p>Recording identity decision…</p>
              ) : (
                <>
                  <p>
                    Identity decision confirmation is uncertain. Re-read the exact decision or replay the same
                    request. A new decision id will not be generated.
                  </p>
                  {state.identityMessage && <p role="alert">{state.identityMessage}</p>}
                  <details>
                    <summary>Technical details</summary>
                    <p>resolution_id: {state.resolutionId}</p>
                  </details>
                  <button
                    data-testid="reread-identity"
                    disabled={state.pending}
                    onClick={() => void handleRereadIdentity()}
                  >
                    Re-read identity decision
                  </button>
                  {state.pendingIdentityRequest && (
                    <button
                      data-testid="replay-identity"
                      disabled={state.pending}
                      onClick={handleReplayIdentity}
                    >
                      Replay identity decision
                    </button>
                  )}
                </>
              )}
            </div>
          )}

          {state.resolution && (
            <div role="status" data-testid="identity-decision">
              {state.resolution.decision === "refuse" ? (
                <>
                  <p>Publication refused. No graph write occurred.</p>
                  {!dockDriven && (
                    <button data-testid="publication-start-over" onClick={handleClearPointer}>
                      Start over
                    </button>
                  )}
                  {dockDriven && (
                    <p className="module-muted">Use Start over in the floating bar to publish again.</p>
                  )}
                </>
              ) : (
                <>
                  <p>
                    Identity decision recorded:{" "}
                    {state.resolution.decision === "create_new" ? "create a new Threat" : "connect to an existing Threat"}.
                  </p>
                  {!state.proposal && !state.proposalId && !dockDriven && (
                    <button data-testid="prepare-proposal" disabled={state.pending} onClick={() => void handlePrepareProposal()}>
                      Review publication proposal
                    </button>
                  )}
                  {!state.proposal && !state.proposalId && dockDriven && (
                    <p className="module-muted" role="status">Preparing publication proposal…</p>
                  )}
                </>
              )}
              {state.identityMessage && <p role="alert">{state.identityMessage}</p>}
              {state.proposalMessage && !state.proposalId && <p role="alert">{state.proposalMessage}</p>}
            </div>
          )}

          {state.proposalId && !state.proposal && (
            <div role="status" data-testid="proposal-uncertainty">
              {state.pending ? (
                <p>Preparing publication proposal…</p>
              ) : (
                <>
                  <p>
                    Proposal confirmation is uncertain. Re-read the exact proposal or replay the same request.
                    A new proposal id will not be generated.
                  </p>
                  {state.proposalMessage && <p role="alert">{state.proposalMessage}</p>}
                  <details>
                    <summary>Technical details</summary>
                    <p>proposal_id: {state.proposalId}</p>
                  </details>
                  {!dockDriven && (
                    <>
                      <button
                        data-testid="reread-proposal"
                        disabled={state.pending}
                        onClick={() => void handleRereadProposal()}
                      >
                        Re-read proposal
                      </button>
                      {state.pendingProposalRequest && (
                        <button
                          data-testid="replay-proposal"
                          disabled={state.pending}
                          onClick={handleReplayProposal}
                        >
                          Replay proposal preparation
                        </button>
                      )}
                    </>
                  )}
                </>
              )}
            </div>
          )}

          {state.proposal && (
            <div data-testid="proposal-review" ref={proposalReviewRef}>
              <h3>Review before publishing</h3>
              <p>Decision: {state.proposal.decision === "create_new" ? "Create new Threat" : "Connect to existing Threat"}</p>
              <p>
                Accepted assertions: {state.proposal.effect_summary.accepted_assertion_count}
                {state.proposal.effect_summary.authored_field_assertion_count > 0
                  ? ` (${state.proposal.effect_summary.authored_field_assertion_count} authored fields)`
                  : ""}
              </p>
              <details>
                <summary>Technical details</summary>
                <p>Threat node: {state.proposal.threat_node_id}</p>
                <p>
                  Accepted mechanics:{" "}
                  {state.operation?.source_snapshot.accepted_mechanics_ref.statblock_id} rev{" "}
                  {state.operation?.source_snapshot.accepted_mechanics_ref.revision_id}
                </p>
                <p>
                  Mechanics digest:{" "}
                  {state.operation?.source_snapshot.accepted_mechanics_ref.definition_digest}
                </p>
                <p>Expected parent revision: {state.proposal.expected_parent_revision_id}</p>
              </details>
              {state.proposalMessage && <p role="alert">{state.proposalMessage}</p>}
              {state.commitMessage && !state.commitId && <p role="alert">{state.commitMessage}</p>}
              {!state.commitId && !dockDriven && (
                <button data-testid="confirm" disabled={state.pending} onClick={() => void handleConfirm()}>
                  Confirm publish
                </button>
              )}
              {!state.commitId && dockDriven && (
                <p className="module-muted" role="status">Confirm publish from the floating bar.</p>
              )}
            </div>
          )}

          {state.commitId && (
            <div
              role="status"
              data-testid="commit-status"
              data-commit-result={state.commitResultLabel ?? "pending"}
            >
              {state.commitResultLabel === "publication_commit_verified" && (
                <p>
                  Published. Threat node {state.commit?.threat_node_id}, binding {state.commit?.binding_id}, revision{" "}
                  {state.commit?.committed_revision_id}.
                </p>
              )}
              {state.commitResultLabel === "publication_commit_committed_unverified" && (
                <>
                  <p>Published; verification needs attention. Revision {state.commit?.committed_revision_id}.</p>
                  <details>
                    <summary>Verification details</summary>
                    <p>Verification status: {state.commit?.verification_status}</p>
                    <p>Verification codes: {state.commit?.verification_codes.join(", ") || "None"}</p>
                  </details>
                </>
              )}
              {state.commitResultLabel === "publication_commit_recovery_pending" && (
                <p>{state.commitMessage ?? "Publication confirmation needs recovery."}</p>
              )}
              {state.commitResultLabel === "publication_commit_uncommitted" && (
                <p>
                  {state.commitMessage
                    ?? "Publication did not commit to the World Graph. Cancel this publication and publish again."}
                </p>
              )}
              {state.commitResultLabel
                && state.commitResultLabel !== "publication_commit_verified"
                && state.commitResultLabel !== "publication_commit_committed_unverified"
                && state.commitResultLabel !== "publication_commit_recovery_pending"
                && state.commitResultLabel !== "publication_commit_uncommitted" && (
                  <p>{state.commitMessage ?? "Publication commit status is not yet resolved."}</p>
              )}
              {!state.commitResultLabel && <p>Confirming publication…</p>}
              {!dockDriven
                && state.retryAllowed
                && !committed
                && state.commitResultLabel === "publication_commit_recovery_pending" && (
                  <button
                    data-testid="retry-confirm"
                    disabled={state.pending || !state.proposal}
                    onClick={() => void handleConfirm()}
                  >
                    Retry confirmation
                  </button>
              )}
              {!dockDriven && (
                <button data-testid="reread-commit" disabled={state.pending} onClick={() => void handleRereadCommit()}>
                  Re-read commit status
                </button>
              )}
            </div>
          )}

          {!dockDriven
            && state.operationId
            && !committed
            && !state.resolution
            && !state.resolutionId
            && !state.proposal
            && !state.proposalId
            && !state.commitId && (
            <button data-testid="cancel-operation" disabled={state.pending} onClick={() => void handleCancelOperation()}>
              Cancel publication
            </button>
          )}
        </div>
      )}
    </section>
  );
}
