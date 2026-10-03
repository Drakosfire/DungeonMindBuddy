import { useEffect, useLayoutEffect, useMemo, useRef, useState, type FormEvent } from "react";
import { createPortal } from "react-dom";

import { getWorldOwnedPlanCommittedRevision, getWorldPlanDocumentEditActions, postWorldPlanAgentTurn, postWorldPlanDocumentEditProposal, setNativeGraphAccessToken } from "../../api/liveApi";
import type {
  AgentInteractionThread,
  AgentInteractionTurn,
  WorldPlanDocumentEditProposalRequest,
  WorldPlanAgentContentBasisV1,
  WorldPlanAgentTurnRequestV1,
  WorldPlanAgentTurnResolvedSummary,
  WorldPlanActionProjection,
} from "../../api/types";
import { AgentTraceInspector } from "../../agentInteraction/trace/AgentTraceInspector";
import { useAskPluginSlotOptional, useRegisterAskPluginPresence } from "../../agentInteraction/AskPluginSlot";
import { usePublishAgentSurfaceContext } from "../../agentInteraction/usePublishAgentSurfaceContext";
import { useAgentInteraction } from "../../agentInteraction/useAgentInteraction";
import { useSelectedWorld } from "../../selectedWorld/SelectedWorldContext";
import {
  admitWorldPlanEditProposal,
  type AdmittedWorldPlanEditProposal,
  type CapturedWorldPlanEditTarget,
  type ExpectedWorldPlanEditAgentBinding,
  type WorldPlanEditBridge,
  worldPlanSectionUnavailableReason,
} from "../agentEdit/planAgentEditProposal";
import { planSectionTargets, type PlanSectionTarget } from "../agentEdit/planSectionTarget";
import {
  AGENT_TURN_HISTORY_CAP,
  createAgentInteractionThread,
  safeTraceForPersistence,
  threadTitleFromQuestion,
} from "./agentInteractionHistory";
import "./WorldPlanAgentConversation.css";

interface WorldPlanAgentConversationProps {
  worldId: string;
  worldName: string;
  documentId: string | null;
  surfaceInstanceId: string;
  revision: number | null;
  editBridge: WorldPlanEditBridge | null;
  draftGeneration: number;
  selectionGeneration: number;
  savedDirty: boolean;
  pageReady: boolean;
  saveInFlight: boolean;
}

interface ValidatedWorldPlanResponse {
  answer: string;
  trace: Record<string, unknown>;
  summary: WorldPlanAgentTurnResolvedSummary;
}

interface WorldPlanEditReview {
  captured: CapturedWorldPlanEditTarget;
  admitted: AdmittedWorldPlanEditProposal;
  expectedAgentBinding: ExpectedWorldPlanEditAgentBinding;
  threadId: string;
  turnId: string;
  fenceKey: string;
}

interface PlanSectionScan {
  captured: CapturedWorldPlanEditTarget;
  worldId: string;
  documentId: string;
}

interface PlanSectionOption extends PlanSectionTarget {
  unavailableReason: string | null;
}

interface PlanSectionTargetStatus {
  kind: "status" | "error";
  message: string;
}

type ValidationResult =
  | { ok: true; value: ValidatedWorldPlanResponse }
  | { ok: false; message: string };

const RESPONSE_MISMATCH = "DungeonBuddy's response did not match this saved Plan. Try again.";
const POINTER_STATUSES = ["absent", "accepted", "recovered", "rejected", "reused"] as const;

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function hasExactKeys(value: unknown, keys: readonly string[]): value is Record<string, unknown> {
  if (!isRecord(value)) return false;
  const actual = Object.keys(value);
  return actual.length === keys.length && keys.every((key) => Object.prototype.hasOwnProperty.call(value, key));
}

function isNullableString(value: unknown): value is string | null {
  return value === null || typeof value === "string";
}

function isPositiveRevision(value: unknown): value is number {
  return typeof value === "number" && Number.isSafeInteger(value) && value >= 1;
}

function readCommittedPlanBasis(
  value: unknown,
  worldId: string,
  documentId: string,
  expectedObjectRevision: number,
): WorldPlanAgentContentBasisV1 | null {
  if (!isRecord(value)
    || value.schema_version !== "dmb_workspace_committed_revision_v2"
    || value.scope_mode !== "world"
    || value.world_id !== worldId
    || value.campaign_id !== null
    || value.document_id !== documentId
    || value.kind !== "plan"
    || value.status !== "active"
    || value.object_revision !== expectedObjectRevision
    || !isPositiveRevision(value.object_revision)
    || !isPositiveRevision(value.revision_n)
    || typeof value.work_revision_id !== "string"
    || !value.work_revision_id.trim()
    || typeof value.markdown !== "string"
    || typeof value.content_sha256 !== "string"
    || !/^[0-9a-f]{64}$/.test(value.content_sha256)
    || typeof value.has_divergent_working_copy !== "boolean") return null;

  return {
    world_id: value.world_id,
    document_id: value.document_id,
    object_revision: value.object_revision,
    work_revision_id: value.work_revision_id,
    revision_n: value.revision_n,
    content_sha256: value.content_sha256,
    committed_status: "committed",
    has_divergent_working_copy: value.has_divergent_working_copy,
  };
}

function matchesCommittedPlanBasis(
  value: unknown,
  request: WorldPlanAgentTurnRequestV1,
): value is WorldPlanAgentContentBasisV1 {
  return hasExactKeys(value, [
    "world_id",
    "document_id",
    "object_revision",
    "work_revision_id",
    "revision_n",
    "content_sha256",
    "committed_status",
    "has_divergent_working_copy",
  ])
    && value.world_id === request.owner_scope.world_id
    && value.document_id === request.primary_work.object_id
    && value.object_revision === request.primary_work.expected_revision
    && value.revision_n === request.primary_work.expected_revision_n
    && value.content_sha256 === request.primary_work.expected_content_sha256
    && value.committed_status === "committed"
    && typeof value.work_revision_id === "string"
    && Boolean(value.work_revision_id.trim())
    && typeof value.has_divergent_working_copy === "boolean";
}

function planThreadNamespace(worldId: string, documentId: string): string {
  return `world-plan-agent:world:${encodeURIComponent(worldId)}:document:${encodeURIComponent(documentId)}`;
}

function validateWorldPlanResponse(
  value: unknown,
  request: WorldPlanAgentTurnRequestV1,
): ValidationResult {
  const topKeys = [
    "schema",
    "client_thread_id",
    "turn_id",
    "surface",
    "owner_scope",
    "primary_work",
    "client_work_state_reported",
    "graph",
    "conversation",
    "answer",
  ];
  if (!hasExactKeys(value, topKeys)
    || value.schema !== "dmb_agent_turn_response_v1"
    || value.client_thread_id !== request.client_thread_id
    || value.turn_id !== request.turn_id) {
    return { ok: false, message: RESPONSE_MISMATCH };
  }

  const surface = value.surface;
  if (!hasExactKeys(surface, ["surface_id", "instance_id", "status"])
    || surface.surface_id !== "plan"
    || surface.instance_id !== request.surface.instance_id
    || surface.status !== "resolved") {
    return { ok: false, message: RESPONSE_MISMATCH };
  }

  const owner = value.owner_scope;
  if (!hasExactKeys(owner, ["status", "kind", "owner_id", "name"])
    || owner.status !== "resolved"
    || owner.kind !== "world"
    || owner.owner_id !== request.owner_scope.world_id
    || !isNullableString(owner.name)) {
    return { ok: false, message: "The selected World could not be verified for this Plan response." };
  }

  const work = value.primary_work;
  if (!hasExactKeys(work, ["status", "kind", "object_id", "revision_used", "expected_revision", "content_basis"])
    || work.kind !== "plan"
    || work.object_id !== request.primary_work.object_id
    || work.expected_revision !== request.primary_work.expected_revision
    || work.status !== "resolved"
    || work.revision_used !== request.primary_work.expected_revision
    || !isPositiveRevision(work.revision_used)
    || !matchesCommittedPlanBasis(work.content_basis, request)) {
    return { ok: false, message: "The saved Plan identity or committed revision could not be verified. Reopen the Plan and try again." };
  }

  if (value.client_work_state_reported !== request.client_work_state) {
    return { ok: false, message: RESPONSE_MISMATCH };
  }

  const graph = value.graph;
  if (!hasExactKeys(graph, [
    "status",
    "world_id",
    "campaign_id",
    "scope_mode",
    "revision_id",
    "focus",
    "selection_node_id",
    "selection_found",
    "head_revision_id",
    "is_head",
  ])
    || graph.status !== "not_requested"
    || graph.world_id !== null
    || graph.campaign_id !== null
    || graph.scope_mode !== null
    || graph.revision_id !== null
    || graph.focus !== null
    || graph.selection_node_id !== null
    || graph.selection_found !== null
    || graph.head_revision_id !== null
    || graph.is_head !== null) {
    return { ok: false, message: RESPONSE_MISMATCH };
  }

  const conversation = value.conversation;
  if (!hasExactKeys(conversation, ["client_thread_id", "turn_id", "pointer_status", "pointer_id"])
    || conversation.client_thread_id !== request.client_thread_id
    || conversation.turn_id !== request.turn_id
    || !POINTER_STATUSES.includes(conversation.pointer_status as (typeof POINTER_STATUSES)[number])
    || !isNullableString(conversation.pointer_id)) {
    return { ok: false, message: RESPONSE_MISMATCH };
  }

  const answer = value.answer;
  if (!hasExactKeys(answer, ["status", "text", "code", "message", "graph_grounded", "trace"])
    || !["ok", "error"].includes(String(answer.status))
    || !isNullableString(answer.text)
    || !isNullableString(answer.code)
    || !isNullableString(answer.message)
    || answer.graph_grounded !== false
    || !isRecord(answer.trace)) {
    return { ok: false, message: RESPONSE_MISMATCH };
  }
  if (answer.status !== "ok" || typeof answer.text !== "string" || !answer.text.trim()
    || answer.code !== null || answer.message !== null) {
    return { ok: false, message: "DungeonBuddy could not complete this turn. Try again." };
  }

  const summary: WorldPlanAgentTurnResolvedSummary = {
    surfaceId: "plan",
    instanceId: request.surface.instance_id,
    ownerStatus: "resolved",
    ownerId: request.owner_scope.world_id,
    workKind: "plan",
    workObjectId: request.primary_work.object_id,
    workStatus: work.status as WorldPlanAgentTurnResolvedSummary["workStatus"],
    expectedRevision: request.primary_work.expected_revision,
    revisionUsed: work.revision_used,
    contentBasis: {
      worldId: work.content_basis.world_id,
      documentId: work.content_basis.document_id,
      objectRevision: work.content_basis.object_revision,
      workRevisionId: work.content_basis.work_revision_id,
      revisionN: work.content_basis.revision_n,
      contentSha256: work.content_basis.content_sha256,
      committedStatus: "committed",
      hasDivergentWorkingCopy: work.content_basis.has_divergent_working_copy,
    },
    clientWorkState: request.client_work_state,
    graphStatus: "not_requested",
    pointerStatus: conversation.pointer_status as WorldPlanAgentTurnResolvedSummary["pointerStatus"],
  };
  return { ok: true, value: { answer: answer.text, trace: answer.trace, summary } };
}

function isScopedPlanThread(
  thread: AgentInteractionThread | null,
  namespace: string,
  documentId: string,
): thread is AgentInteractionThread {
  return Boolean(thread
    && thread.campaignId === namespace
    && thread.surfaceId === "plan"
    && thread.session === null
    && thread.documentId === documentId);
}

export function WorldPlanAgentConversation({
  worldId,
  worldName,
  documentId,
  surfaceInstanceId,
  revision,
  editBridge,
  draftGeneration,
  selectionGeneration,
  savedDirty,
  pageReady,
  saveInFlight,
}: WorldPlanAgentConversationProps) {
  const selectedWorld = useSelectedWorld();
  const agent = useAgentInteraction();
  const askSlot = useAskPluginSlotOptional();
  const verifiedWorldId = selectedWorld.kind === "managed" ? selectedWorld.worldId : null;
  const planReady = Boolean(pageReady
    && verifiedWorldId === worldId
    && documentId
    && surfaceInstanceId
    && isPositiveRevision(revision));
  const namespace = planReady && documentId ? planThreadNamespace(worldId, documentId) : null;
  const surfaceContext = useMemo(() => namespace && documentId ? ({
    surfaceId: "plan" as const,
    label: "World Plan conversation",
    campaignId: namespace,
    documentId,
    sessionNumber: null,
    ambientSummary: "Plan Ask uses the exact committed revision; unsaved draft text is excluded",
    sourceEnvelope: null,
  }) : null, [documentId, namespace]);
  usePublishAgentSurfaceContext(surfaceContext);
  useRegisterAskPluginPresence(planReady);

  const scopeMatches = Boolean(namespace
    && documentId
    && agent.scope?.campaignId === namespace
    && agent.scope.surfaceId === "plan"
    && agent.scope.sessionNumber === null
    && agent.scope.documentId === documentId);
  const activeThread = isScopedPlanThread(agent.activeThread, namespace ?? "", documentId ?? "")
    ? agent.activeThread
    : null;
  const traceVisible = activeThread?.uiState?.traceVisible ?? false;
  const scopeKey = `${worldId}\u001f${documentId ?? ""}`;
  const requestFenceKey = JSON.stringify({
    worldId: verifiedWorldId,
    documentId,
    surfaceInstanceId,
    revision,
    planReady,
    saveInFlight,
  });
  const proposalFenceKey = JSON.stringify({
    requestFenceKey,
    draftGeneration,
    selectionGeneration,
    savedDirty,
    paneOpen: agent.paneState.isOpen,
    hasAskHost: Boolean(askSlot?.hostElement),
    agentScope: agent.scope ? {
      campaignId: agent.scope.campaignId,
      surfaceId: agent.scope.surfaceId ?? null,
      sessionNumber: agent.scope.sessionNumber,
      documentId: agent.scope.documentId ?? null,
    } : null,
  });
  const [question, setQuestion] = useState("");
  const [graphCredential, setGraphCredential] = useState("");
  const [graphCredentialStatus, setGraphCredentialStatus] = useState<string | null>(null);
  const [editInstruction, setEditInstruction] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [editError, setEditError] = useState<string | null>(null);
  const [sending, setSending] = useState(false);
  const [composing, setComposing] = useState(false);
  const [editReview, setEditReview] = useState<WorldPlanEditReview | null>(null);
  const [sectionTargets, setSectionTargets] = useState<PlanSectionOption[]>([]);
  const [selectedSectionTargetId, setSelectedSectionTargetId] = useState("");
  const [sectionTargetStatus, setSectionTargetStatus] = useState<PlanSectionTargetStatus | null>(null);
  const [actionHistory, setActionHistory] = useState<WorldPlanActionProjection[]>([]);
  const [actionHistoryError, setActionHistoryError] = useState<string | null>(null);
  const requestRef = useRef<{ token: symbol; threadId: string; fenceKey: string } | null>(null);
  const proposalRequestRef = useRef<{ token: symbol; threadId: string; fenceKey: string; providerThreadId: string | null } | null>(null);
  const proposalIntentRef = useRef<{ fingerprint: string; idempotencyKey: string } | null>(null);
  const editReviewRef = useRef<WorldPlanEditReview | null>(null);
  const sectionScanRef = useRef<PlanSectionScan | null>(null);
  const sectionOperationRef = useRef<symbol | null>(null);
  const sanitizedPointerRef = useRef<string | null>(null);
  const latestRef = useRef({
    fenceKey: requestFenceKey,
    proposalFenceKey,
    threadId: activeThread?.threadId ?? null,
    providerThreadId: agent.activeThread?.threadId ?? null,
    scopeMatches,
    verifiedWorldId,
    documentId,
    revision,
    scope: agent.scope ? {
      campaignId: agent.scope.campaignId,
      surfaceId: agent.scope.surfaceId ?? null,
      sessionNumber: agent.scope.sessionNumber,
      documentId: agent.scope.documentId ?? null,
    } : null,
    askVisible: Boolean(askSlot?.hostElement && agent.paneState.isOpen),
    mounted: false,
  });
  latestRef.current.fenceKey = requestFenceKey;
  latestRef.current.proposalFenceKey = proposalFenceKey;
  latestRef.current.threadId = activeThread?.threadId ?? null;
  latestRef.current.providerThreadId = agent.activeThread?.threadId ?? null;
  latestRef.current.scopeMatches = scopeMatches;
  latestRef.current.verifiedWorldId = verifiedWorldId;
  latestRef.current.documentId = documentId;
  latestRef.current.revision = revision;
  latestRef.current.scope = agent.scope ? {
    campaignId: agent.scope.campaignId,
    surfaceId: agent.scope.surfaceId ?? null,
    sessionNumber: agent.scope.sessionNumber,
    documentId: agent.scope.documentId ?? null,
  } : null;
  latestRef.current.askVisible = Boolean(askSlot?.hostElement && agent.paneState.isOpen);

  useLayoutEffect(() => {
    latestRef.current.mounted = true;
    return () => {
      latestRef.current.mounted = false;
      requestRef.current = null;
      proposalRequestRef.current = null;
      editReviewRef.current = null;
      sectionScanRef.current = null;
      sectionOperationRef.current = null;
    };
  }, []);

  useLayoutEffect(() => {
    sectionScanRef.current = null;
    sectionOperationRef.current = null;
    setSectionTargets([]);
    setSelectedSectionTargetId("");
    setSectionTargetStatus(null);
  }, [worldId, documentId, surfaceInstanceId, revision, draftGeneration]);

  useEffect(() => {
    let active = true;
    setActionHistory([]);
    setActionHistoryError(null);
    if (!scopeMatches || !verifiedWorldId || !documentId) return () => { active = false; };
    void getWorldPlanDocumentEditActions(verifiedWorldId, documentId)
      .then((page) => {
        if (active && page.schema_version === "dmb_world_plan_action_projection_v1"
          && page.basis.world_id === verifiedWorldId && page.basis.document_id === documentId
          && page.basis.object_revision === revision) {
          setActionHistory(page.actions);
        }
      })
      .catch((reason: unknown) => {
        if (active) setActionHistoryError(reason instanceof Error ? reason.message : "Could not load Plan edit action status.");
      });
    return () => { active = false; };
  }, [scopeMatches, verifiedWorldId, documentId, revision]);

  useLayoutEffect(() => {
    requestRef.current = null;
    setSending(false);
  }, [requestFenceKey]);

  useLayoutEffect(() => {
    proposalRequestRef.current = null;
    editReviewRef.current = null;
    setComposing(false);
    setEditReview(null);
    setEditError(null);
  }, [proposalFenceKey]);

  useLayoutEffect(() => {
    const pending = requestRef.current;
    if (pending && latestRef.current.providerThreadId !== pending.threadId) {
      requestRef.current = null;
      setSending(false);
    }
  }, [agent.activeThread?.threadId]);

  useLayoutEffect(() => {
    const pending = proposalRequestRef.current;
    if (pending && latestRef.current.providerThreadId !== pending.providerThreadId) {
      proposalRequestRef.current = null;
      setComposing(false);
    }
    const review = editReviewRef.current;
    if (review && activeThread?.threadId !== review.threadId) {
      editReviewRef.current = null;
      setEditReview(null);
    }
  }, [activeThread?.threadId, agent.activeThread?.threadId]);

  useLayoutEffect(() => {
    setQuestion("");
    setError(null);
  }, [scopeKey]);

  useEffect(() => {
    if (!activeThread?.hermesSession) {
      sanitizedPointerRef.current = null;
      return;
    }
    const pointerKey = `${activeThread.threadId}:${activeThread.hermesSession.sessionId}`;
    if (sanitizedPointerRef.current === pointerKey) return;
    sanitizedPointerRef.current = pointerKey;
    // The generic endpoint owns its continuity pointer; never carry a legacy provider pointer into it.
    agent.updateThread({ ...activeThread, hermesSession: null });
  }, [activeThread, agent.updateThread]);

  function startNewConversation() {
    if (!scopeMatches) return;
    requestRef.current = null;
    proposalRequestRef.current = null;
    editReviewRef.current = null;
    setEditReview(null);
    setComposing(false);
    const next = agent.createThread("New World Plan conversation");
    latestRef.current.threadId = next.threadId;
    setQuestion("");
    setError(null);
    setEditError(null);
    setSending(false);
  }

  function saveGraphCredential(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const credential = graphCredential.trim();
    setNativeGraphAccessToken(credential || null);
    setGraphCredential("");
    setGraphCredentialStatus(credential
      ? "Credential is held in this tab's memory and checked by the server on native Graph requests."
      : "Native Graph credential cleared.");
  }

  function clearGraphCredential() {
    setNativeGraphAccessToken(null);
    setGraphCredential("");
    setGraphCredentialStatus("Native Graph credential cleared.");
  }

  function toggleTraceVisibility() {
    if (!scopeMatches || sending || composing || requestRef.current || proposalRequestRef.current) return;
    const thread = activeThread ?? agent.createThread("New World Plan conversation");
    agent.updateThread({
      ...thread,
      uiState: {
        ...thread.uiState,
        traceVisible: !traceVisible,
      },
    });
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const message = question.trim();
    if (!planReady || !scopeMatches || !namespace || !documentId || !surfaceInstanceId
      || !isPositiveRevision(revision) || saveInFlight || !message || sending || requestRef.current) return;

    // Keep a first-turn candidate in memory only. A failed or mismatched response
    // must not create a persisted empty thread, turn summary, or question title.
    const currentThread = activeThread ?? createAgentInteractionThread(
      namespace,
      null,
      "plan",
      "hermes",
      threadTitleFromQuestion(message),
      documentId,
    );
    const providerThreadId = agent.activeThread?.threadId ?? null;
    const token = Symbol("world-plan-agent-turn");
    requestRef.current = { token, threadId: currentThread.threadId, fenceKey: requestFenceKey };
    setSending(true);
    setError(null);
    const isCurrent = () => latestRef.current.mounted
      && latestRef.current.fenceKey === requestFenceKey
      && latestRef.current.scopeMatches
      && latestRef.current.providerThreadId === providerThreadId
      && (providerThreadId === null || latestRef.current.threadId === currentThread.threadId)
      && requestRef.current?.token === token;

    try {
      const committedRevision: unknown = await getWorldOwnedPlanCommittedRevision(documentId);
      if (!isCurrent()) return;
      const contentBasis = readCommittedPlanBasis(committedRevision, worldId, documentId, revision);
      if (!contentBasis) {
        throw new Error("The committed Plan changed or could not be verified. Refresh the Plan before asking.");
      }
      const request: WorldPlanAgentTurnRequestV1 = {
        schema: "dmb_agent_turn_request_v1",
        client_thread_id: currentThread.threadId,
        turn_id: crypto.randomUUID(),
        surface: { surface_id: "plan", instance_id: surfaceInstanceId },
        owner_scope: { kind: "world", world_id: worldId },
        primary_work: {
          kind: "plan",
          object_id: documentId,
          expected_revision: revision,
          expected_revision_n: contentBasis.revision_n,
          expected_content_sha256: contentBasis.content_sha256,
        },
        client_work_state: savedDirty ? "saved_dirty" : "saved_clean",
        graph_request: { mode: "none" },
        graph_selection: null,
        message,
      };
      const response: unknown = await postWorldPlanAgentTurn(request);
      if (!isCurrent()) return;
      const validation = validateWorldPlanResponse(response, request);
      if (!validation.ok) throw new Error(validation.message);

      requestRef.current = null;
      setSending(false);
      const now = new Date().toISOString();
      const turn: AgentInteractionTurn = {
        turnId: request.turn_id,
        askedAt: now,
        completedAt: now,
        question: message,
        answer: validation.value.answer,
        backend: "hermes",
        status: "ok",
        trace: safeTraceForPersistence(validation.value.trace),
        agentTurnResolved: validation.value.summary,
      };
      agent.updateThread({
        ...currentThread,
        campaignId: namespace,
        session: null,
        documentId,
        surfaceId: "plan",
        activeBackend: "hermes",
        hermesSession: null,
        title: currentThread.turns.length ? currentThread.title : threadTitleFromQuestion(message),
        updatedAt: now,
        turns: [turn, ...currentThread.turns].slice(0, AGENT_TURN_HISTORY_CAP),
      });
      setQuestion("");
    } catch (reason) {
      if (isCurrent()) setError(reason instanceof Error ? reason.message : "The Agent turn failed. Try again.");
    } finally {
      if (isCurrent()) {
        requestRef.current = null;
        setSending(false);
      }
    }
  }

  function getLiveEditAgentBinding() {
    return {
      mounted: latestRef.current.mounted && latestRef.current.askVisible,
      verifiedWorldId: latestRef.current.verifiedWorldId,
      activeThreadId: latestRef.current.providerThreadId,
      scope: latestRef.current.scope,
    };
  }

  function isProposalRequestCurrent(
    token: symbol,
    fenceKey: string,
    providerThreadId: string | null,
  ) {
    return latestRef.current.mounted
      && latestRef.current.askVisible
      && latestRef.current.scopeMatches
      && latestRef.current.proposalFenceKey === fenceKey
      && latestRef.current.providerThreadId === providerThreadId
      && proposalRequestRef.current?.token === token;
  }

  async function refreshPlanSections() {
    if (!editBridge || !documentId || !scopeMatches || composing || sending || saveInFlight || editReviewRef.current) return;
    const token = Symbol("world-plan-section-scan");
    const fenceKey = proposalFenceKey;
    sectionOperationRef.current = token;
    sectionScanRef.current = null;
    setSectionTargets([]);
    setSelectedSectionTargetId("");
    setSectionTargetStatus({ kind: "status", message: "Reading safe headings from the mounted Plan…" });
    try {
      const captured = await editBridge.capture();
      if (!latestRef.current.mounted || sectionOperationRef.current !== token) return;
      if (latestRef.current.proposalFenceKey !== fenceKey) {
        setSectionTargetStatus({ kind: "error", message: "The Plan or editor selection changed while reading headings. Refresh the section list." });
        return;
      }
      const targets = planSectionTargets(captured.editor).map((target) => ({
        ...target,
        unavailableReason: worldPlanSectionUnavailableReason(captured.editor, target),
      }));
      const availableCount = targets.filter((target) => !target.unavailableReason).length;
      const unavailableCount = targets.length - availableCount;
      sectionScanRef.current = { captured, worldId, documentId };
      setSectionTargets(targets);
      setSectionTargetStatus({
        kind: "status",
        message: targets.length
          ? `${availableCount} of ${targets.length} heading sections are available for proposals.${unavailableCount ? ` ${unavailableCount} section${unavailableCount === 1 ? " is" : "s are"} unavailable because their Markdown round-trip is not safe; unavailable sections are labeled in the list.` : ""} Text before the first heading stays outside the list; select it directly in the editor.`
          : "This safe Plan draft has no nonempty root-level headings. Select text or place a caret directly in the editor.",
      });
    } catch (reason) {
      if (!latestRef.current.mounted || sectionOperationRef.current !== token) return;
      setSectionTargetStatus({
        kind: "error",
        message: reason instanceof Error ? reason.message : "Could not read headings from this mounted Plan.",
      });
    } finally {
      if (sectionOperationRef.current === token) sectionOperationRef.current = null;
    }
  }

  async function refreshActionHistory() {
    if (!verifiedWorldId || !documentId || !scopeMatches) return;
    setActionHistoryError(null);
    try {
      const page = await getWorldPlanDocumentEditActions(verifiedWorldId, documentId);
      if (page.schema_version === "dmb_world_plan_action_projection_v1"
        && page.basis.world_id === verifiedWorldId && page.basis.document_id === documentId
        && page.basis.object_revision === revision
        && latestRef.current.verifiedWorldId === verifiedWorldId
        && latestRef.current.documentId === documentId
        && latestRef.current.revision === revision) {
        setActionHistory(page.actions);
      }
    } catch (reason) {
      if (latestRef.current.scopeMatches
        && latestRef.current.verifiedWorldId === verifiedWorldId
        && latestRef.current.documentId === documentId
        && latestRef.current.revision === revision) {
        setActionHistoryError(reason instanceof Error ? reason.message : "Could not load Plan edit action status.");
      }
    }
  }

  async function selectPlanSection(sectionId: string) {
    setSelectedSectionTargetId(sectionId);
    if (!sectionId) {
      setSectionTargetStatus(null);
      return;
    }
    const scan = sectionScanRef.current;
    if (!editBridge || !scan) {
      setSelectedSectionTargetId("");
      setSectionTargetStatus({ kind: "error", message: "Refresh the section list before selecting a Plan heading." });
      return;
    }
    const sectionOption = sectionTargets.find((candidate) => candidate.id === sectionId);
    if (!sectionOption) {
      setSelectedSectionTargetId("");
      setSectionTargetStatus({ kind: "error", message: "That Plan heading is no longer available. Refresh the section list." });
      return;
    }
    if (sectionOption.unavailableReason) {
      setSelectedSectionTargetId("");
      setSectionTargetStatus({ kind: "error", message: sectionOption.unavailableReason });
      return;
    }
    const token = Symbol("world-plan-section-selection");
    const fenceKey = proposalFenceKey;
    sectionOperationRef.current = token;
    setSectionTargetStatus({ kind: "status", message: "Selecting this Plan section…" });
    try {
      const current = await editBridge.capture();
      if (!latestRef.current.mounted || sectionOperationRef.current !== token) return;
      if (latestRef.current.proposalFenceKey !== fenceKey) {
        throw new Error("The Plan or editor selection changed while choosing a section. Refresh the section list.");
      }
      if (current.editor.isDestroyed
        || current.editor !== scan.captured.editor
        || current.editorJson !== scan.captured.editorJson
        || current.draftGeneration !== scan.captured.draftGeneration
        || current.request.world_id !== scan.worldId
        || current.request.document_id !== scan.documentId
        || current.request.base_revision !== scan.captured.request.base_revision
        || current.request.draft_sha256 !== scan.captured.request.draft_sha256) {
        throw new Error("The mounted Plan draft changed. Refresh the section list before selecting a heading.");
      }
      const target = planSectionTargets(current.editor).find((candidate) => candidate.id === sectionId);
      if (!target) throw new Error("That Plan heading is no longer available. Refresh the section list.");
      const unavailableReason = worldPlanSectionUnavailableReason(current.editor, target);
      if (unavailableReason) throw new Error(unavailableReason);
      if (!current.editor.commands.setTextSelection({ from: target.from, to: target.to })) {
        throw new Error("The Plan editor could not select that heading section.");
      }
      setSectionTargetStatus({
        kind: "status",
        message: `${target.label} selected. Compose a proposal to review a replacement; Save remains separate.`,
      });
    } catch (reason) {
      if (!latestRef.current.mounted || sectionOperationRef.current !== token) return;
      setSelectedSectionTargetId("");
      setSectionTargetStatus({
        kind: "error",
        message: reason instanceof Error ? reason.message : "Could not select that Plan section.",
      });
    } finally {
      if (sectionOperationRef.current === token) sectionOperationRef.current = null;
    }
  }

  async function composeEdit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const instruction = editInstruction.trim();
    if (!planReady || !scopeMatches || !namespace || !documentId || !editBridge
      || !isPositiveRevision(revision) || saveInFlight || !instruction
      || composing || sending || requestRef.current || proposalRequestRef.current) return;

    const providerThreadId = agent.activeThread?.threadId ?? null;
    const currentThread = activeThread ?? createAgentInteractionThread(
      namespace,
      null,
      "plan",
      "hermes",
      threadTitleFromQuestion(instruction),
      documentId,
    );
    const token = Symbol("world-plan-edit-proposal");
    const fenceKey = proposalFenceKey;
    proposalRequestRef.current = { token, threadId: currentThread.threadId, fenceKey, providerThreadId };
    setComposing(true);
    setEditError(null);
    setEditReview(null);
    editReviewRef.current = null;

    const isCurrent = () => isProposalRequestCurrent(token, fenceKey, providerThreadId);
    try {
      const captured = await editBridge.capture();
      if (!isCurrent()) return;
      const conversationHistory = currentThread.turns.slice(0, 6).reverse().flatMap((turn) => [
        { role: "user" as const, content: turn.question.slice(0, 4000) },
        { role: "assistant" as const, content: turn.answer.slice(0, 4000) },
      ]);
      const requestWithoutKey = {
        ...captured.request,
        instruction,
        conversation_history: conversationHistory,
      };
      const fingerprint = JSON.stringify(requestWithoutKey);
      const idempotencyKey = proposalIntentRef.current?.fingerprint === fingerprint
        ? proposalIntentRef.current.idempotencyKey
        : crypto.randomUUID();
      proposalIntentRef.current = { fingerprint, idempotencyKey };
      const request: WorldPlanDocumentEditProposalRequest = {
        ...requestWithoutKey,
        idempotency_key: idempotencyKey,
      };
      const response = await postWorldPlanDocumentEditProposal(request);
      if (!isCurrent()) return;
      if (response.idempotency_key !== request.idempotency_key
        || typeof response.action_id !== "string" || !response.action_id.trim()) {
        throw new Error("DungeonBuddy's Plan action response did not match this edit request. No proposal was opened.");
      }
      const admitted = await admitWorldPlanEditProposal(captured, response);
      if (!isCurrent()) return;

      const now = new Date().toISOString();
      const turnId = crypto.randomUUID();
      const turn: AgentInteractionTurn = {
        turnId,
        askedAt: now,
        completedAt: now,
        question: instruction,
        answer: response.summary,
        backend: "plan_edit",
        status: "ok",
        planEdit: {
          proposalSummary: response.summary,
          replacementMarkdown: admitted.canonicalMarkdown,
          applied: false,
          targetKind: captured.request.target_kind,
        },
      };
      proposalRequestRef.current = null;
      setComposing(false);
      agent.updateThread({
        ...currentThread,
        campaignId: namespace,
        session: null,
        documentId,
        surfaceId: "plan",
        hermesSession: null,
        title: currentThread.turns.length ? currentThread.title : threadTitleFromQuestion(instruction),
        updatedAt: now,
        turns: [turn, ...currentThread.turns].slice(0, AGENT_TURN_HISTORY_CAP),
      });
      const expectedAgentBinding: ExpectedWorldPlanEditAgentBinding = {
        worldId,
        documentId,
        threadId: currentThread.threadId,
        namespace,
      };
      const nextReview: WorldPlanEditReview = {
        captured,
        admitted,
        expectedAgentBinding,
        threadId: currentThread.threadId,
        turnId,
        fenceKey: latestRef.current.proposalFenceKey,
      };
      editReviewRef.current = nextReview;
      setEditReview(nextReview);
      setEditInstruction("");
      proposalIntentRef.current = null;
      void getWorldPlanDocumentEditActions(worldId, documentId)
        .then((page) => {
          if (page.schema_version === "dmb_world_plan_action_projection_v1"
            && page.basis.world_id === worldId
            && page.basis.document_id === documentId
            && page.basis.object_revision === revision
            && latestRef.current.scopeMatches
            && latestRef.current.verifiedWorldId === worldId
            && latestRef.current.documentId === documentId
            && latestRef.current.revision === revision) {
            setActionHistory(page.actions);
          }
        })
        .catch(() => undefined);
    } catch (reason) {
      if (isCurrent()) setEditError(reason instanceof Error ? reason.message : "The Plan edit proposal failed. Try again.");
    } finally {
      if (isCurrent()) {
        proposalRequestRef.current = null;
        setComposing(false);
      }
    }
  }

  function discardEditReview() {
    editReviewRef.current = null;
    setEditReview(null);
    setEditError(null);
  }

  async function applyEditReview(review: WorldPlanEditReview) {
    if (!editBridge || editReviewRef.current !== review
      || latestRef.current.proposalFenceKey !== review.fenceKey
      || !latestRef.current.scopeMatches
      || latestRef.current.threadId !== review.threadId) {
      discardEditReview();
      setEditError("World Plan or Agent thread changed. Compose the proposal again.");
      return;
    }
    try {
      await editBridge.apply(
        review.captured,
        review.admitted,
        review.expectedAgentBinding,
        getLiveEditAgentBinding,
      );
      const currentThread = agent.activeThread;
      if (!currentThread || currentThread.threadId !== review.threadId) {
        throw new Error("The Agent thread changed before the proposal could be recorded.");
      }
      const now = new Date().toISOString();
      agent.updateThread({
        ...currentThread,
        updatedAt: now,
        turns: currentThread.turns.map((turn) => turn.turnId === review.turnId && turn.planEdit
          ? { ...turn, planEdit: { ...turn.planEdit, applied: true } }
          : turn),
      });
      discardEditReview();
    } catch (reason) {
      setEditError(reason instanceof Error ? reason.message : "The proposal could not be applied to this mounted Plan.");
    }
  }

  if (!pageReady) return null;
  if (!documentId) {
    return <p className="world-plan-agent-draft-note" role="status">Save this Plan to start an Agent conversation.</p>;
  }
  if (!planReady || !askSlot?.hostElement || !agent.paneState.isOpen || !scopeMatches) return null;

  const currentReview = editReview
    && editReview.fenceKey === proposalFenceKey
    && editReview.threadId === activeThread?.threadId
    ? editReview
    : null;

  return createPortal(
    <section className="world-plan-agent-conversation" aria-label="Saved World Plan conversation">
      <header className="world-plan-agent-conversation__header">
        <div>
          <h2>Ask DungeonBuddy</h2>
          <p>World: {worldName} · Saved Plan · Conversation only</p>
        </div>
        <div className="world-plan-agent-conversation__actions">
          <button
            type="button"
            aria-pressed={traceVisible}
            disabled={sending || composing || requestRef.current !== null || proposalRequestRef.current !== null}
            onClick={toggleTraceVisibility}
          >
            {traceVisible ? "Advanced diagnostics: On" : "Advanced diagnostics: Off"}
          </button>
          <button type="button" onClick={startNewConversation} disabled={sending || composing}>New conversation</button>
        </div>
      </header>
      <section aria-label="Native Graph access">
        <form onSubmit={(event) => { void saveGraphCredential(event); }}>
          <label htmlFor="world-plan-agent-graph-credential">Local operator Graph credential</label>
          <input
            id="world-plan-agent-graph-credential"
            type="password"
            autoComplete="off"
            value={graphCredential}
            onChange={(event) => setGraphCredential(event.currentTarget.value)}
            maxLength={4096}
          />
          <button type="submit">Set Graph access</button>
          <button type="button" onClick={clearGraphCredential}>Clear Graph access</button>
        </form>
        <p role="note">The credential stays in memory only. It is sent only with native Graph reads and graph-enabled Agent turns; ordinary Plan Ask remains graphless.</p>
        {graphCredentialStatus ? <p role="status">{graphCredentialStatus}</p> : null}
      </section>
      <p className="world-plan-agent-conversation__notice" role="note">
        Ask sends this Plan’s exact committed text and your question to the configured model. Unsaved editor changes are excluded; the turn records which committed revision it used and whether a divergent working copy existed. Compose or Revise below sends the selected text and current mounted draft to the configured model. Nothing changes until you review and apply a proposal.
      </p>
      {saveInFlight ? (
        <p className="world-plan-agent-conversation__saving" role="status">Conversation paused while the Plan is saving.</p>
      ) : null}
      {editBridge ? (
        <section className="world-plan-agent-conversation__compose" aria-label="Compose or revise Plan text">
          <h3>Compose or revise Plan text</h3>
          <form onSubmit={(event) => { void composeEdit(event); }}>
            <label htmlFor="world-plan-agent-edit-instruction">What should DungeonBuddy change?</label>
            <textarea
              id="world-plan-agent-edit-instruction"
              value={editInstruction}
              onChange={(event) => setEditInstruction(event.currentTarget.value)}
              maxLength={4000}
              disabled={composing || sending || saveInFlight || !scopeMatches || currentReview !== null}
            />
            <div role="group" aria-label="Target a Plan section">
              <label htmlFor="world-plan-agent-plan-section">Plan heading section</label>
              <select
                id="world-plan-agent-plan-section"
                value={selectedSectionTargetId}
                disabled={composing || sending || saveInFlight || !scopeMatches || currentReview !== null || sectionTargets.length === 0}
                onChange={(event) => { void selectPlanSection(event.currentTarget.value); }}
              >
                <option value="">Select a heading section</option>
                {sectionTargets.map((target) => (
                  <option
                    key={target.id}
                    value={target.id}
                    disabled={Boolean(target.unavailableReason)}
                    title={target.unavailableReason ?? undefined}
                  >
                    {target.unavailableReason
                      ? `${target.label} — unavailable (Markdown round-trip not safe)`
                      : target.label}
                  </option>
                ))}
              </select>
              <button
                type="button"
                onClick={() => { void refreshPlanSections(); }}
                disabled={composing || sending || saveInFlight || !scopeMatches || currentReview !== null}
              >
                Refresh section list
              </button>
              <p role="note">A section pick selects text in the editor. Compose uses the editor’s current selection; direct edits or selections take precedence.</p>
              {sectionTargetStatus ? (
                <p role={sectionTargetStatus.kind === "error" ? "alert" : "status"}>{sectionTargetStatus.message}</p>
              ) : null}
            </div>
            {editError ? <p role="alert">{editError}</p> : null}
            <button
              type="submit"
              disabled={composing || sending || saveInFlight || !scopeMatches || !editInstruction.trim() || currentReview !== null}
            >
              {composing ? "Composing…" : "Compose proposal"}
            </button>
          </form>
          <section aria-label="Plan edit action status">
            <h4>Recent Plan edit actions</h4>
            <button type="button" onClick={() => { void refreshActionHistory(); }} disabled={!scopeMatches || composing}>
              Refresh action status
            </button>
            {actionHistoryError ? <p role="alert">{actionHistoryError}</p> : null}
            {actionHistory.length ? (
              <ol>
                {actionHistory.map((action) => (
                  <li key={action.action_id}>
                    <strong>{action.status}</strong> · {action.instruction}
                    {action.status === "completed" && action.assistant_summary
                      ? <p>{action.assistant_summary}</p>
                      : action.status === "pending"
                        ? <p>This action is still running; it will not be dispatched again.</p>
                        : action.status === "indeterminate"
                          ? <p>The outcome is unknown. Start a new edit action if you still want to try again.</p>
                          : action.status === "failed"
                            ? <p>This action failed. Start a new edit action to try again.</p>
                            : null}
                    {action.status !== "pending" ? (
                      <button
                        type="button"
                        disabled={composing || currentReview !== null}
                        onClick={() => {
                          proposalIntentRef.current = null;
                          setEditInstruction(action.instruction);
                          setEditError(null);
                        }}
                      >
                        Start a new edit attempt
                      </button>
                    ) : null}
                </li>
                ))}
              </ol>
            ) : null}
          </section>
      {currentReview ? (
            <section className="world-plan-agent-conversation__review" aria-label="Review proposed Plan edit">
              <h4>Review proposal</h4>
              <p>{currentReview.admitted.response.summary}</p>
              {currentReview.admitted.response.assumptions.length ? (
                <ul>{currentReview.admitted.response.assumptions.map((assumption, index) => <li key={`${index}:${assumption}`}>{assumption}</li>)}</ul>
              ) : null}
              <div className="world-plan-agent-conversation__preview">
                <div>
                  <h5>Before</h5>
                  <pre>{currentReview.captured.request.selected_text || "Nothing selected · proposal will insert at the captured caret."}</pre>
                </div>
                <div>
                  <h5>After</h5>
                  <pre>{currentReview.admitted.canonicalMarkdown}</pre>
                </div>
              </div>
              <div className="world-plan-agent-conversation__review-actions">
                <button type="button" onClick={discardEditReview}>Discard</button>
                <button type="button" onClick={() => { void applyEditReview(currentReview); }}>Apply to mounted draft</button>
              </div>
            </section>
          ) : null}
        </section>
      ) : null}
      <div className="world-plan-agent-conversation__turns" aria-live="polite">
        {activeThread?.turns.length ? [...activeThread.turns].reverse().map((turn) => (
          <article key={turn.turnId}>
            <p><strong>You:</strong> {turn.question}</p>
            <p><strong>DungeonBuddy{turn.planEdit ? " · Plan proposal" : ""}:</strong> {turn.answer}</p>
            {turn.planEdit ? (
              <p className="world-plan-agent-conversation__context">
                Plan proposal · {turn.planEdit.applied ? "Applied to the local draft" : "Not applied"}
              </p>
            ) : null}
            {turn.agentTurnResolved?.surfaceId === "plan" ? (
              <>
                <p className="world-plan-agent-conversation__context">
                  {turn.agentTurnResolved.contentBasis
                    ? `Answered from committed Plan revision ${turn.agentTurnResolved.contentBasis.revisionN} (object revision ${turn.agentTurnResolved.contentBasis.objectRevision}).`
                    : `Saved Plan revision ${turn.agentTurnResolved.revisionUsed}.`}
                  {" "}Editor was {turn.agentTurnResolved.clientWorkState === "saved_dirty" ? "edited since save" : "unchanged"} when asked.
                </p>
                {turn.agentTurnResolved.contentBasis ? (
                  <details className="world-plan-agent-conversation__context-basis">
                    <summary>Exact committed content basis</summary>
                    <dl>
                      <dt>World</dt><dd>{turn.agentTurnResolved.contentBasis.worldId}</dd>
                      <dt>Plan</dt><dd>{turn.agentTurnResolved.contentBasis.documentId}</dd>
                      <dt>WorkRevision</dt><dd>{turn.agentTurnResolved.contentBasis.workRevisionId}</dd>
                      <dt>Revision number</dt><dd>{turn.agentTurnResolved.contentBasis.revisionN}</dd>
                      <dt>Content SHA-256</dt><dd><code>{turn.agentTurnResolved.contentBasis.contentSha256}</code></dd>
                      <dt>Status</dt><dd>{turn.agentTurnResolved.contentBasis.committedStatus}</dd>
                      <dt>Divergent working copy</dt><dd>{turn.agentTurnResolved.contentBasis.hasDivergentWorkingCopy ? "Present · excluded" : "None"}</dd>
                    </dl>
                  </details>
                ) : null}
              </>
            ) : null}
            {turn.trace && traceVisible ? <AgentTraceInspector trace={turn.trace} /> : null}
          </article>
        )) : (
          <p>Ask a general question to start a conversation associated with this Plan.</p>
        )}
      </div>
      <form onSubmit={(event) => { void submit(event); }}>
        <label htmlFor="world-plan-agent-question">Your question</label>
        <textarea
          id="world-plan-agent-question"
          value={question}
          onChange={(event) => setQuestion(event.currentTarget.value)}
          maxLength={8000}
          disabled={sending || composing || saveInFlight || !scopeMatches}
        />
        {error ? <p role="alert">{error}</p> : null}
        <button type="submit" disabled={sending || composing || saveInFlight || !scopeMatches || !question.trim()}>
          {sending ? "Asking…" : saveInFlight ? "Saving…" : "Ask"}
        </button>
      </form>
    </section>,
    askSlot.hostElement,
  );
}
