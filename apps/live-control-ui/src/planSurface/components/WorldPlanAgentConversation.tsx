import { useEffect, useLayoutEffect, useMemo, useRef, useState, type FormEvent } from "react";
import { createPortal } from "react-dom";

import { getWorldAgentConversationHistory, getWorldOwnedPlanCommittedRevision, getWorldPlanDocumentEditActions, postWorldAgentNewConversation, postWorldPlanAgentTurn, postWorldPlanDocumentEditProposal, connectNativeGraphSession, revokeNativeGraphSession, isValidWorldPlanGraphContextFailure, LiveApiError } from "../../api/liveApi";
import type {
  AgentInteractionThread,
  AgentInteractionTurn,
  WorldPlanDocumentEditProposalRequest,
  WorldPlanAgentContentBasisV1,
  WorldPlanAgentTurnRequestV1,
  WorldPlanAgentTurnResolvedSummary,
  WorldPlanActionProjection,
  WorldAgentConversationHistoryResponse,
  WorldAgentConversationHistoryResponseV3,
  WorldAgentConversationHistoryTurn,
  WorldAgentConversationHistoryTurnV1,
  WorldAgentNewConversationRequestV1,
  WorldPlanAgentPlanContextV1,
  WorldPlanGraphAnswerContextStatusV1,
  WorldPlanGraphAnswerSegmentV1,
  WorldPlanGraphCitationMapV1,
  WorldPlanGraphCompletionV1,
  WorldPlanGraphContextReceiptV1,
  WorldPlanGraphExecutionProjectionV1,
  WorldPlanContextPolicyV1,
  WorldPlanSelectedPlayableTargetV1,
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
import { WorldPlanAgentAnswer } from "./WorldPlanAgentAnswer";
import {
  AGENT_TURN_HISTORY_CAP,
  createAgentInteractionThread,
  listAgentThreads,
  loadAgentThreadById,
  threadStorageKey,
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
  playableTarget?: Omit<WorldPlanSelectedPlayableTargetV1, "schema"> | null;
  playableTargetBasis?: { revision: number; contentSha256: string } | null;
  playableTargetStale?: boolean;
  onClearPlayableTarget?: () => void;
  playableEditTarget?: { kind: "scene" | "beat" | "choice" | "option"; id: string; generation: number } | null;
  playableEditTargetGeneration?: number;
  playableEditTargetStale?: boolean;
  playableEditTargetDirty?: boolean;
  onClearPlayableEditTarget?: () => void;
}

interface ValidatedWorldPlanResponse {
  answer: string;
  trace: Record<string, unknown>;
  summary: WorldPlanAgentTurnResolvedSummary;
  conversationId: string | null;
  replayed: boolean;
}

interface WorldPlanEditReview {
  captured: CapturedWorldPlanEditTarget;
  admitted: AdmittedWorldPlanEditProposal;
  expectedAgentBinding: ExpectedWorldPlanEditAgentBinding;
  threadId: string;
  turnId: string;
  fenceKey: string;
}

type WorldPlanEditReviewBefore =
  | { kind: "captured-text"; markdown: string; target?: { kind: string; id: string } }
  | { kind: "caret" };

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

function worldPlanEditReviewBefore(captured: CapturedWorldPlanEditTarget): WorldPlanEditReviewBefore | null {
  const { request } = captured;
  if (request.target_kind === "insert_at_caret") return { kind: "caret" };
  if (request.target_kind !== "replace_playable_body") {
    return typeof request.selected_text === "string"
      ? { kind: "captured-text", markdown: request.selected_text }
      : null;
  }

  const target = captured.playableBodyTarget;
  const requestTarget = request.playable_target;
  if (!target || !requestTarget
    || !target.target || target.target.kind !== requestTarget.kind || target.target.id !== requestTarget.id
    || typeof target.targetBodyMarkdown !== "string"
    || !/^[0-9a-f]{64}$/.test(target.targetBodySha256)
    || request.target_body_markdown !== target.targetBodyMarkdown
    || request.target_body_sha256 !== target.targetBodySha256
    || request.body_serialization_version !== target.bodySerializationVersion
    || target.bodySerializationVersion !== "plan-playable-body-markdown-v1"
    || target.rangeSemanticsVersion !== "plan-playable-ranges-v1"
    || !Number.isSafeInteger(target.from) || !Number.isSafeInteger(target.to)
    || target.from !== captured.from || target.to !== captured.to
    || !Number.isSafeInteger(captured.playableTargetGeneration)) {
    return null;
  }

  return {
    kind: "captured-text",
    markdown: target.targetBodyMarkdown,
    target: target.target,
  };
}

const WORLD_HISTORY_PAGE_SIZE = 50;
const WORLD_PLAN_LOCAL_PROPOSAL_HISTORY = "world_plan_proposals_v1" as const;
const WORLD_PLAN_LOCAL_PROPOSAL_ORDER_SCHEMA = "dmb_world_plan_local_proposal_order_v1" as const;
const WORLD_PLAN_LOCAL_PROPOSAL_ORDER_PREFIX = "dmb:world-plan-local-proposal-order:v1:";
const PENDING_ASK_STORAGE_PREFIX = "dmb:world-plan-pending-ask:v1:";
const PENDING_ASK_CLEARED_EVENT = "dmb:world-plan-pending-ask-cleared:v1";
const PENDING_ASK_ACCEPTED_EVENT = "dmb:world-plan-ask-accepted:v1";
const PENDING_NEW_CONVERSATION_STORAGE_PREFIX = "dmb:world-agent-new-conversation:v1:";

interface WorldPlanLocalProposalPosition {
  turnId: string;
  conversationId: string | null;
  afterSequence: number;
  ordinal: number;
}

interface WorldPlanLocalProposalOrderEnvelope {
  schema: typeof WORLD_PLAN_LOCAL_PROPOSAL_ORDER_SCHEMA;
  positions: WorldPlanLocalProposalPosition[];
}

type WorldConversationDisplayEvent =
  | { kind: "world"; turn: WorldAgentConversationHistoryTurn }
  | { kind: "proposal"; turn: AgentInteractionTurn; position: WorldPlanLocalProposalPosition };

interface WorldPlanPendingAskOrigin {
  worldId: string;
  documentId: string;
  objectRevision: number;
  workRevisionId: string;
  revisionN: number;
  contentSha256: string;
  pointerRevision: number;
  conversationId: string | null;
}

interface WorldPlanPendingAskEnvelope {
  schema: "dmb_world_plan_pending_ask_v1";
  request: WorldPlanAgentTurnRequestV1;
  origin: WorldPlanPendingAskOrigin;
  createdAt: string;
}

type PendingAskClearedOrigin = Pick<
  WorldPlanPendingAskOrigin,
  "worldId" | "documentId" | "objectRevision" | "workRevisionId" | "revisionN" | "contentSha256"
>;

interface PendingAskClearedEventDetail {
  version: 1;
  key: string;
  origin: PendingAskClearedOrigin;
}

interface StoredPendingAsk {
  storageKey: string;
  serialized: string;
  envelope: WorldPlanPendingAskEnvelope | null;
  error: string | null;
}

interface ConfirmedTerminalFailureAsk {
  storageKey: string;
  serialized: string;
  historyTurnId: string;
}

interface WorldPlanPendingNewConversation {
  schema: "dmb_world_pending_new_conversation_v1";
  worldId: string;
  documentId: string;
  request: WorldAgentNewConversationRequestV1;
}

interface StoredPendingNewConversation {
  storageKey: string;
  envelope: WorldPlanPendingNewConversation | null;
  error: string | null;
}

function pendingAskPrefix(worldId: string, documentId: string): string {
  return `${PENDING_ASK_STORAGE_PREFIX}${encodeURIComponent(worldId)}:${encodeURIComponent(documentId)}:`;
}

function pendingAskStorageKey(
  worldId: string,
  documentId: string,
  origin: WorldPlanPendingAskOrigin,
  turnId: string,
): string {
  const basis = [
    origin.objectRevision,
    origin.workRevisionId,
    origin.revisionN,
    origin.contentSha256,
    turnId,
  ].join("|");
  return `${pendingAskPrefix(worldId, documentId)}${encodeURIComponent(basis)}`;
}

function pendingNewConversationPrefix(worldId: string): string {
  return `${PENDING_NEW_CONVERSATION_STORAGE_PREFIX}${encodeURIComponent(worldId)}:`;
}

function pendingNewConversationStorageKey(worldId: string, commandId: string): string {
  return `${pendingNewConversationPrefix(worldId)}${encodeURIComponent(commandId)}`;
}

function readPrefixedStorage(prefix: string): Array<{ storageKey: string; raw: string }> {
  const storage = window.localStorage;
  const matches: Array<{ storageKey: string; raw: string }> = [];
  for (let index = 0; index < storage.length; index += 1) {
    const storageKey = storage.key(index);
    if (!storageKey?.startsWith(prefix)) continue;
    const raw = storage.getItem(storageKey);
    if (raw !== null) matches.push({ storageKey, raw });
  }
  return matches;
}

function parsePendingAsk(
  storageKey: string,
  raw: string,
  worldId: string,
  documentId: string,
): StoredPendingAsk {
  try {
    const value: unknown = JSON.parse(raw);
    if (!isRecord(value) || value.schema !== "dmb_world_plan_pending_ask_v1"
      || !isRecord(value.request) || !isRecord(value.origin)) {
      throw new Error("This saved Ask envelope is malformed and cannot be replayed safely.");
    }
    const request = value.request;
    const origin = value.origin;
    const primary = request.primary_work;
    if (request.schema !== "dmb_agent_turn_request_v1"
      || typeof request.client_thread_id !== "string"
      || typeof request.turn_id !== "string"
      || !isRecord(request.surface) || request.surface.surface_id !== "plan"
      || !isRecord(request.owner_scope) || request.owner_scope.kind !== "world"
      || request.owner_scope.world_id !== worldId
      || !isRecord(primary) || primary.kind !== "plan"
      || typeof primary.object_id !== "string" || primary.object_id !== documentId
      || !isRecord(request.graph_request) || request.graph_request.mode !== "none"
      || request.graph_selection !== null || typeof request.message !== "string"
      || (Object.prototype.hasOwnProperty.call(request, "playable_target")
        && !isPlanPlayableTarget(request.playable_target))
      || (Object.prototype.hasOwnProperty.call(request, "plan_context_policy")
        && !isWorldPlanContextPolicy(request.plan_context_policy))
      || origin.worldId !== worldId || origin.documentId !== documentId
      || !Number.isSafeInteger(origin.objectRevision)
      || typeof origin.workRevisionId !== "string"
      || !Number.isSafeInteger(origin.revisionN)
      || typeof origin.contentSha256 !== "string"
      || !Number.isSafeInteger(origin.pointerRevision)
      || !(origin.conversationId === null || typeof origin.conversationId === "string")
      || primary.expected_revision !== origin.objectRevision
      || primary.expected_revision_n !== origin.revisionN
      || primary.expected_content_sha256 !== origin.contentSha256
      || storageKey !== pendingAskStorageKey(worldId, documentId, origin as unknown as WorldPlanPendingAskOrigin, request.turn_id)) {
      throw new Error("This saved Ask envelope does not match its World, Plan, basis, or storage key.");
    }
    return {
      storageKey,
      serialized: raw,
      envelope: value as unknown as WorldPlanPendingAskEnvelope,
      error: null,
    };
  } catch (reason) {
    return {
      storageKey,
      serialized: raw,
      envelope: null,
      error: reason instanceof Error ? reason.message : "This saved Ask envelope is malformed.",
    };
  }
}

function isPendingAskClearedEventDetail(value: unknown): value is PendingAskClearedEventDetail {
  if (!isRecord(value) || Object.keys(value).sort().join(",") !== "key,origin,version"
    || value.version !== 1 || typeof value.key !== "string" || !isRecord(value.origin)) {
    return false;
  }
  const origin = value.origin;
  return Object.keys(origin).sort().join(",")
      === "contentSha256,documentId,objectRevision,revisionN,workRevisionId,worldId"
    && typeof origin.worldId === "string"
    && typeof origin.documentId === "string"
    && Number.isSafeInteger(origin.objectRevision)
    && typeof origin.workRevisionId === "string"
    && Number.isSafeInteger(origin.revisionN)
    && typeof origin.contentSha256 === "string"
    && value.key.startsWith(pendingAskPrefix(origin.worldId, origin.documentId));
}

type PendingAskClearResult =
  | { kind: "cleared" }
  | { kind: "changed" }
  | { kind: "unavailable"; message: string };

function clearPendingAskIfUnchanged(stored: StoredPendingAsk): PendingAskClearResult {
  const envelope = stored.envelope;
  if (!envelope) return { kind: "changed" };

  try {
    const storage = window.localStorage;
    if (storage.getItem(stored.storageKey) !== stored.serialized) return { kind: "changed" };
    storage.removeItem(stored.storageKey);
    if (storage.getItem(stored.storageKey) !== null) return { kind: "changed" };
  } catch (reason) {
    return {
      kind: "unavailable",
      message: reason instanceof Error
        ? reason.message
        : "The Ask completed, but browser storage could not clear its local recovery envelope.",
    };
  }

  return { kind: "cleared" };
}

function dispatchPendingAskSettlement(stored: StoredPendingAsk, result: PendingAskClearResult): void {
  const envelope = stored.envelope;
  if (!envelope) return;
  const origin = envelope.origin;
  const eventName = result.kind === "cleared" ? PENDING_ASK_CLEARED_EVENT : PENDING_ASK_ACCEPTED_EVENT;
  window.dispatchEvent(new CustomEvent<PendingAskClearedEventDetail>(eventName, {
    detail: {
      version: 1,
      key: stored.storageKey,
      origin: {
        worldId: origin.worldId,
        documentId: origin.documentId,
        objectRevision: origin.objectRevision,
        workRevisionId: origin.workRevisionId,
        revisionN: origin.revisionN,
        contentSha256: origin.contentSha256,
      },
    },
  }));
}

function readPendingAsks(worldId: string, documentId: string): StoredPendingAsk[] {
  return readPrefixedStorage(pendingAskPrefix(worldId, documentId))
    .map(({ storageKey, raw }) => parsePendingAsk(storageKey, raw, worldId, documentId));
}

function parsePendingNewConversation(
  storageKey: string,
  raw: string,
  worldId: string,
): StoredPendingNewConversation {
  try {
    const value: unknown = JSON.parse(raw);
    if (!isRecord(value) || value.schema !== "dmb_world_pending_new_conversation_v1"
      || value.worldId !== worldId || typeof value.documentId !== "string"
      || !isRecord(value.request) || value.request.schema !== "dmb_agent_new_conversation_v1"
      || typeof value.request.command_id !== "string"
      || !Number.isSafeInteger(value.request.expected_pointer_revision)
      || !(value.request.expected_active_conversation_id === null
        || typeof value.request.expected_active_conversation_id === "string")
      || storageKey !== pendingNewConversationStorageKey(worldId, value.request.command_id)) {
      throw new Error("This saved New Conversation command is malformed and cannot be replayed safely.");
    }
    return {
      storageKey,
      envelope: value as unknown as WorldPlanPendingNewConversation,
      error: null,
    };
  } catch (reason) {
    return {
      storageKey,
      envelope: null,
      error: reason instanceof Error ? reason.message : "This saved New Conversation command is malformed.",
    };
  }
}

function readPendingNewConversations(worldId: string): StoredPendingNewConversation[] {
  return readPrefixedStorage(pendingNewConversationPrefix(worldId))
    .map(({ storageKey, raw }) => parsePendingNewConversation(storageKey, raw, worldId));
}

function sameHistoryPointer(
  left: WorldAgentConversationHistoryResponse | null,
  right: WorldAgentConversationHistoryResponse,
): boolean {
  return Boolean(left
    && left.world_id === right.world_id
    && left.pointer_revision === right.pointer_revision
    && left.active_conversation_id === right.active_conversation_id
    && left.conversation_id === right.conversation_id);
}

function mergeHistoryTurns(
  older: WorldAgentConversationHistoryTurn[],
  latest: WorldAgentConversationHistoryTurn[],
): WorldAgentConversationHistoryTurn[] {
  const byId = new Map<string, WorldAgentConversationHistoryTurn>();
  for (const turn of older) byId.set(turn.turn_id, turn);
  for (const turn of latest) byId.set(turn.turn_id, turn);
  return [...byId.values()].sort((left, right) => left.sequence - right.sequence);
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function isPlanPlayableTarget(value: unknown): value is WorldPlanSelectedPlayableTargetV1 {
  if (!isRecord(value)
    || Object.keys(value).length !== 3
    || value.schema !== "dmb_plan_playable_target_v1"
    || !["scene", "beat", "choice", "option"].includes(String(value.kind))
    || typeof value.id !== "string"
    || !/^(scene|beat|choice|option):[a-z0-9][a-z0-9._-]{0,127}$/.test(value.id)) return false;
  return value.id.startsWith(`${value.kind}:`);
}

function localProposalOrderStorageKey(namespace: string, threadId: string): string {
  return `${WORLD_PLAN_LOCAL_PROPOSAL_ORDER_PREFIX}${encodeURIComponent(namespace)}:${encodeURIComponent(threadId)}`;
}

function readLocalProposalOrder(storageKey: string): WorldPlanLocalProposalOrderEnvelope {
  const empty: WorldPlanLocalProposalOrderEnvelope = {
    schema: WORLD_PLAN_LOCAL_PROPOSAL_ORDER_SCHEMA,
    positions: [],
  };
  try {
    const raw = window.localStorage.getItem(storageKey);
    if (!raw) return empty;
    const parsed: unknown = JSON.parse(raw);
    if (!isRecord(parsed) || parsed.schema !== WORLD_PLAN_LOCAL_PROPOSAL_ORDER_SCHEMA || !Array.isArray(parsed.positions)) {
      return empty;
    }
    const positions = parsed.positions.filter((value): value is WorldPlanLocalProposalPosition =>
      isRecord(value)
      && typeof value.turnId === "string" && value.turnId.length > 0
      && (value.conversationId === null || (typeof value.conversationId === "string" && value.conversationId.length > 0))
      && Number.isSafeInteger(value.afterSequence) && (value.afterSequence as number) >= 0
      && Number.isSafeInteger(value.ordinal) && (value.ordinal as number) >= 0,
    );
    return { schema: WORLD_PLAN_LOCAL_PROPOSAL_ORDER_SCHEMA, positions };
  } catch {
    return empty;
  }
}

function appendLocalProposalPosition(
  storageKey: string,
  turnId: string,
  conversationId: string,
  afterSequence: number,
): boolean {
  try {
    const current = readLocalProposalOrder(storageKey);
    if (current.positions.some((position) => position.turnId === turnId)) return true;
    const ordinal = current.positions.reduce((largest, position) => Math.max(largest, position.ordinal), -1) + 1;
    const positions = [...current.positions, { turnId, conversationId, afterSequence, ordinal }]
      .slice(-AGENT_TURN_HISTORY_CAP);
    window.localStorage.setItem(storageKey, JSON.stringify({
      schema: WORLD_PLAN_LOCAL_PROPOSAL_ORDER_SCHEMA,
      positions,
    } satisfies WorldPlanLocalProposalOrderEnvelope));
    return true;
  } catch {
    return false;
  }
}

function buildWorldConversationDisplayEvents(
  history: WorldAgentConversationHistoryResponse | null,
  proposalTurns: AgentInteractionTurn[],
  positions: WorldPlanLocalProposalPosition[],
): { events: WorldConversationDisplayEvent[]; localActivity: AgentInteractionTurn[] } {
  const positionByTurnId = new Map(positions.map((position) => [position.turnId, position]));
  const proposals = [...proposalTurns]
    .filter((turn) => turn.planEdit)
    .reverse();
  const conversationId = history?.conversation_id ?? null;
  const inline: Array<{ turn: AgentInteractionTurn; position: WorldPlanLocalProposalPosition }> = [];
  const localActivity: AgentInteractionTurn[] = [];
  for (const turn of proposals) {
    const position = positionByTurnId.get(turn.turnId);
    if (position && conversationId && position.conversationId === conversationId) {
      inline.push({ turn, position });
    } else {
      localActivity.push(turn);
    }
  }
  inline.sort((left, right) => left.position.ordinal - right.position.ordinal);

  const events: WorldConversationDisplayEvent[] = [];
  const inserted = new Set<string>();
  const chronologicalTurns = [...(history?.turns ?? [])]
    .sort((left, right) => left.sequence - right.sequence);
  for (const turn of chronologicalTurns) {
    for (const proposal of inline) {
      if (!inserted.has(proposal.turn.turnId) && proposal.position.afterSequence < turn.sequence) {
        events.push({ kind: "proposal", turn: proposal.turn, position: proposal.position });
        inserted.add(proposal.turn.turnId);
      }
    }
    events.push({ kind: "world", turn });
  }
  for (const proposal of inline) {
    if (inserted.has(proposal.turn.turnId)) continue;
    events.push({ kind: "proposal", turn: proposal.turn, position: proposal.position });
  }
  return { events, localActivity };
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

function localOperatorCredentialFailure(reason: unknown, nextStep: string): string | null {
  if (!(reason instanceof LiveApiError) || (reason.status !== 401 && reason.status !== 403)) return null;
  return `The local Agent and Graph session is missing or was rejected (HTTP ${reason.status}). Reconnect in Settings, then ${nextStep}.`;
}

function graphContextPreDispatchFailure(reason: unknown): string | null {
  if (!(reason instanceof LiveApiError)) return null;
  const failure: unknown = reason.planContextFailure;
  if (!isValidWorldPlanGraphContextFailure(failure, reason.code, reason.status)) return null;
  return `The server confirmed provider dispatch did not begin (${failure.failure_code}). ${reason.message} This Ask did not start and no answer was saved. Resolve the issue, then submit a new Ask if you want another attempt.`;
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

function isDurableReceiptReplayTrace(value: unknown, turnId: string): boolean {
  if (!isRecord(value)) return false;
  return value.schema === "dmb_agent_turn_trace_v1"
    && value.turn_id === turnId
    && value.runtime === "durable_receipt"
    && value.backend === "application_state"
    && value.mode === "replay"
    && value.status === "ok"
    && Array.isArray(value.model_calls)
    && value.model_calls.length === 0
    && value.conversation_context === "durable_replay"
    && Array.isArray(value.warnings)
    && value.warnings.includes("durable_turn_replay_no_provider_dispatch");
}

function planThreadNamespace(worldId: string, documentId: string): string {
  return `world-plan-agent:world:${encodeURIComponent(worldId)}:document:${encodeURIComponent(documentId)}`;
}

function isWorldPlanContextPolicy(value: unknown): value is WorldPlanContextPolicyV1 {
  return hasExactKeys(value, ["schema", "policy"])
    && value.schema === "dmb_plan_context_policy_v1"
    && value.policy === "auto_plan_world";
}

function isDigest(value: unknown): value is string {
  return typeof value === "string" && /^[0-9a-f]{64}$/.test(value);
}

function isNonEmptyStringList(value: unknown): value is string[] {
  return Array.isArray(value)
    && value.length > 0
    && value.every((item) => typeof item === "string" && Boolean(item.trim()));
}

function isStringList(value: unknown): value is string[] {
  return Array.isArray(value) && value.every((item) => typeof item === "string" && Boolean(item.trim()));
}

function isSortedUniqueStringList(value: unknown, maxLength: number): value is string[] {
  return isStringList(value)
    && value.length <= maxLength
    && value.every((item, index, list) => index === 0 || list[index - 1]! < item);
}

function isWorldPlanGraphReceipt(
  value: unknown,
  request?: WorldPlanAgentTurnRequestV1,
): value is WorldPlanGraphContextReceiptV1 {
  if (!hasExactKeys(value, [
    "schema",
    "receipt_serializer_version",
    "context_receipt_sha256",
    "plan_context_policy",
    "plan_basis",
    "playable_target",
    "graph_authority",
    "graph_packet",
    "assembled_input",
    "evidence_mode",
    "source_opened",
  ])
    || value.schema !== "dmb_agent_plan_world_graph_context_receipt_v1"
    || value.receipt_serializer_version !== "canonical-json-utf8-v1"
    || !isDigest(value.context_receipt_sha256)
    || !isWorldPlanContextPolicy(value.plan_context_policy)
    || value.evidence_mode !== "metadata_only"
    || value.source_opened !== false) return false;

  const basis = value.plan_basis;
  if (!hasExactKeys(basis, [
    "world_id", "document_id", "object_revision", "work_revision_id", "revision_n", "content_sha256",
  ])
    || typeof basis.world_id !== "string" || !basis.world_id.trim()
    || typeof basis.document_id !== "string" || !basis.document_id.trim()
    || !isPositiveRevision(basis.object_revision)
    || typeof basis.work_revision_id !== "string" || !basis.work_revision_id.trim()
    || !isPositiveRevision(basis.revision_n)
    || !isDigest(basis.content_sha256)) return false;

  const target = value.playable_target;
  if (target !== null && (!hasExactKeys(target, ["schema", "kind", "id", "marker_grammar_version"])
    || target.schema !== "dmb_plan_playable_target_receipt_v1"
    || !["scene", "beat", "choice", "option"].includes(String(target.kind))
    || typeof target.id !== "string" || !target.id.startsWith(`${String(target.kind)}:`)
    || !["v1", "v2"].includes(String(target.marker_grammar_version)))) return false;

  const authority = value.graph_authority;
  if (!hasExactKeys(authority, [
    "managed_world_id", "native_world_id", "binding_version", "scope_mode", "campaign_id", "admissibility_version", "graph_revision",
  ])
    || authority.managed_world_id !== basis.world_id
    || typeof authority.native_world_id !== "string" || !authority.native_world_id.trim()
    || !Number.isSafeInteger(authority.binding_version) || (authority.binding_version as number) < 1
    || authority.scope_mode !== "world" || authority.campaign_id !== null
    || typeof authority.admissibility_version !== "string" || !authority.admissibility_version.trim()
    || typeof authority.graph_revision !== "string" || !authority.graph_revision.trim()) return false;

  const packet = value.graph_packet;
  if (!hasExactKeys(packet, [
    "schema", "packet_serializer_version", "selection_policy_version", "evidence_sufficiency_policy_version",
    "retrieval_packet_sha256", "candidate_assertion_ids", "candidate_relationship_ids", "candidate_evidence_ref_ids",
    "retrieval_status", "evidence_sufficiency_status", "result_limit", "coverage_status", "truncated", "omission_reasons",
  ])
    || packet.schema !== "dmb_plan_world_graph_packet_v1"
    || packet.packet_serializer_version !== "canonical-json-utf8-v1"
    || typeof packet.selection_policy_version !== "string" || !packet.selection_policy_version.trim()
    || typeof packet.evidence_sufficiency_policy_version !== "string" || !packet.evidence_sufficiency_policy_version.trim()
    || !isDigest(packet.retrieval_packet_sha256)
    || !isSortedUniqueStringList(packet.candidate_assertion_ids, 512)
    || !isSortedUniqueStringList(packet.candidate_relationship_ids, 512)
    || !isSortedUniqueStringList(packet.candidate_evidence_ref_ids, 1024)
    || !["complete", "empty"].includes(String(packet.retrieval_status))
    || !["sufficient", "insufficient"].includes(String(packet.evidence_sufficiency_status))
    || !Number.isSafeInteger(packet.result_limit) || (packet.result_limit as number) < 0
    || !["complete", "incomplete"].includes(String(packet.coverage_status))
    || typeof packet.truncated !== "boolean"
    || !isStringList(packet.omission_reasons)) return false;

  const assembled = value.assembled_input;
  if (!hasExactKeys(assembled, [
    "assembler_version", "budget_policy_version", "provider_model_name", "provider_model_version", "tokenizer_name",
    "tokenizer_version", "provider_envelope_input_tokens", "output_token_reserve", "context_window_limit",
    "packet_disposition", "packet_disposition_reason", "dispatched_packet_sha256", "dispatched_assertion_ids",
    "dispatched_relationship_ids", "dispatched_evidence_ref_ids", "source_token_accounting", "included_history",
    "assembled_input_sha256",
  ])
    || !["included", "omitted_insufficient"].includes(String(assembled.packet_disposition))
    || !(assembled.packet_disposition_reason === null || assembled.packet_disposition_reason === "insufficient_evidence")
    || typeof assembled.assembler_version !== "string" || !assembled.assembler_version.trim()
    || typeof assembled.budget_policy_version !== "string" || !assembled.budget_policy_version.trim()
    || typeof assembled.provider_model_name !== "string" || !assembled.provider_model_name.trim()
    || typeof assembled.provider_model_version !== "string" || !assembled.provider_model_version.trim()
    || typeof assembled.tokenizer_name !== "string" || !assembled.tokenizer_name.trim()
    || typeof assembled.tokenizer_version !== "string" || !assembled.tokenizer_version.trim()
    || !Number.isSafeInteger(assembled.provider_envelope_input_tokens) || (assembled.provider_envelope_input_tokens as number) < 0
    || !Number.isSafeInteger(assembled.output_token_reserve) || (assembled.output_token_reserve as number) < 0
    || !Number.isSafeInteger(assembled.context_window_limit) || (assembled.context_window_limit as number) < 1
    || (assembled.provider_envelope_input_tokens as number) + (assembled.output_token_reserve as number) > (assembled.context_window_limit as number)
    || !isDigest(assembled.assembled_input_sha256)
    || !isSortedUniqueStringList(assembled.dispatched_assertion_ids, 512)
    || !isSortedUniqueStringList(assembled.dispatched_relationship_ids, 512)
    || !isSortedUniqueStringList(assembled.dispatched_evidence_ref_ids, 1024)
    || !Array.isArray(assembled.source_token_accounting)
    || assembled.source_token_accounting.length > 128
    || !assembled.source_token_accounting.every((entry) => hasExactKeys(entry, ["source_kind", "source_id", "input_tokens"])
      && ["plan", "history", "graph", "instructions", "tools", "message"].includes(String(entry.source_kind))
      && typeof entry.source_id === "string" && Boolean(entry.source_id.trim())
      && Number.isSafeInteger(entry.input_tokens) && (entry.input_tokens as number) >= 0)
    || !Array.isArray(assembled.included_history)
    || assembled.included_history.length > 64
    || !assembled.included_history.every((entry) => hasExactKeys(entry, ["turn_id", "answer_sha256"])
      && typeof entry.turn_id === "string" && Boolean(entry.turn_id.trim()) && isDigest(entry.answer_sha256))) return false;

  const packetAssertionIds = new Set(packet.candidate_assertion_ids as string[]);
  const packetRelationshipIds = new Set(packet.candidate_relationship_ids as string[]);
  const packetEvidenceIds = new Set(packet.candidate_evidence_ref_ids as string[]);
  const dispatchedAssertions = assembled.dispatched_assertion_ids as string[];
  const dispatchedRelationships = assembled.dispatched_relationship_ids as string[];
  const dispatchedEvidence = assembled.dispatched_evidence_ref_ids as string[];
  if (dispatchedAssertions.some((id) => !packetAssertionIds.has(id))
    || dispatchedRelationships.some((id) => !packetRelationshipIds.has(id))
    || dispatchedEvidence.some((id) => !packetEvidenceIds.has(id))) return false;

  if (packet.truncated && packet.coverage_status !== "incomplete") return false;
  if (packet.retrieval_status === "empty" && (packet.candidate_assertion_ids.length > 0
    || packet.candidate_relationship_ids.length > 0 || packet.candidate_evidence_ref_ids.length > 0
    || packet.evidence_sufficiency_status !== "insufficient")) return false;
  if (packet.evidence_sufficiency_status === "insufficient"
    ? assembled.packet_disposition !== "omitted_insufficient"
      || assembled.packet_disposition_reason !== "insufficient_evidence"
      || assembled.dispatched_packet_sha256 !== null
      || assembled.dispatched_assertion_ids.length > 0
      || assembled.dispatched_relationship_ids.length > 0
      || assembled.dispatched_evidence_ref_ids.length > 0
    : assembled.packet_disposition !== "included"
      || assembled.packet_disposition_reason !== null
      || !isDigest(assembled.dispatched_packet_sha256)
      || packet.evidence_sufficiency_status !== "sufficient") return false;

  if (!request) return true;
  const requestedTarget = request.playable_target ?? null;
  return value.plan_context_policy.schema === request.plan_context_policy?.schema
    && value.plan_context_policy.policy === request.plan_context_policy?.policy
    && basis.world_id === request.owner_scope.world_id
    && basis.document_id === request.primary_work.object_id
    && basis.object_revision === request.primary_work.expected_revision
    && basis.revision_n === request.primary_work.expected_revision_n
    && basis.content_sha256 === request.primary_work.expected_content_sha256
    && (requestedTarget === null
      ? target === null
      : target !== null && target.kind === requestedTarget.kind && target.id === requestedTarget.id);
}

function isWorldPlanGraphCompletion(
  value: unknown,
  receipt: WorldPlanGraphContextReceiptV1,
): value is WorldPlanGraphCompletionV1 {
  if (!hasExactKeys(value, [
    "schema", "context_receipt_sha256", "answer_basis", "answer_context_status", "answer_segments", "citation_map",
  ])
    || value.schema !== "dmb_plan_world_graph_completion_v1"
    || value.context_receipt_sha256 !== receipt.context_receipt_sha256
    || !["committed_plan", "committed_plan_plus_world_graph"].includes(String(value.answer_basis))
    || !["graph_grounded", "graph_grounded_partial", "plan_only_insufficient_evidence", "plan_only_graph_unused"]
      .includes(String(value.answer_context_status))
    || !Array.isArray(value.answer_segments)
    || value.answer_segments.length < 1 || value.answer_segments.length > 128) return false;

  const graphClaims: Extract<WorldPlanGraphAnswerSegmentV1, { kind: "graph_claim" }>[] = [];
  for (const segment of value.answer_segments) {
    if (!isRecord(segment) || typeof segment.kind !== "string") return false;
    if (segment.kind === "graph_claim") {
      if (!hasExactKeys(segment, ["kind", "claim_id", "text", "target_kind", "target_id", "graph_revision", "evidence_ref_ids"])
        || typeof segment.claim_id !== "string" || !segment.claim_id.trim()
        || typeof segment.text !== "string" || !segment.text.trim()
        || !["assertion", "relationship"].includes(String(segment.target_kind))
        || typeof segment.target_id !== "string" || !segment.target_id.trim()
        || segment.graph_revision !== receipt.graph_authority.graph_revision
        || !isNonEmptyStringList(segment.evidence_ref_ids) || segment.evidence_ref_ids.length > 64) return false;
      graphClaims.push(segment as unknown as Extract<WorldPlanGraphAnswerSegmentV1, { kind: "graph_claim" }>);
    } else if (segment.kind === "plan_claim") {
      if (!hasExactKeys(segment, ["kind", "text", "plan_content_sha256"])
        || typeof segment.text !== "string" || !segment.text.trim()
        || segment.plan_content_sha256 !== receipt.plan_basis.content_sha256) return false;
    } else if (segment.kind === "proposal") {
      if (!hasExactKeys(segment, ["kind", "text", "label"])
        || typeof segment.text !== "string" || !segment.text.trim() || segment.label !== "invented_idea") return false;
    } else if (segment.kind === "connective") {
      if (!hasExactKeys(segment, ["kind", "text"]) || typeof segment.text !== "string" || !segment.text.trim()) return false;
    } else return false;
  }
  if (new Set(graphClaims.map((claim) => claim.claim_id)).size !== graphClaims.length) return false;

  const expectedBasis = graphClaims.length > 0 ? "committed_plan_plus_world_graph" : "committed_plan";
  if (value.answer_basis !== expectedBasis) return false;

  const citationMap = value.citation_map;
  if (citationMap === null) {
    if (graphClaims.length > 0) return false;
  } else {
    if (!hasExactKeys(citationMap, ["schema", "context_receipt_sha256", "entries"])
      || citationMap.schema !== "dmb_graph_citation_map_v1"
      || citationMap.context_receipt_sha256 !== receipt.context_receipt_sha256
      || !Array.isArray(citationMap.entries)
      || citationMap.entries.length > 128
      || citationMap.entries.length !== graphClaims.length) return false;
    const entriesByClaimId = new Map<string, WorldPlanGraphCitationMapV1["entries"][number]>();
    for (const entry of citationMap.entries) {
      if (!hasExactKeys(entry, ["claim_id", "target_kind", "target_id", "graph_revision", "evidence_ref_ids", "source_opened"])
        || typeof entry.claim_id !== "string" || !entry.claim_id.trim()
        || !["assertion", "relationship"].includes(String(entry.target_kind))
        || typeof entry.target_id !== "string" || !entry.target_id.trim()
        || entry.graph_revision !== receipt.graph_authority.graph_revision
        || !isNonEmptyStringList(entry.evidence_ref_ids) || entry.evidence_ref_ids.length > 64
        || entry.source_opened !== false
        || entriesByClaimId.has(entry.claim_id)) return false;
      entriesByClaimId.set(entry.claim_id, entry as unknown as WorldPlanGraphCitationMapV1["entries"][number]);
    }
    for (const claim of graphClaims) {
      const entry = entriesByClaimId.get(claim.claim_id);
      if (!entry
        || entry.target_kind !== claim.target_kind
        || entry.target_id !== claim.target_id
        || entry.graph_revision !== claim.graph_revision
        || entry.evidence_ref_ids.length !== claim.evidence_ref_ids.length
        || entry.evidence_ref_ids.some((ref, index) => ref !== claim.evidence_ref_ids[index])) return false;
    }
  }

  const status = value.answer_context_status as WorldPlanGraphAnswerContextStatusV1;
  if (status === "plan_only_insufficient_evidence") {
    return receipt.graph_packet.evidence_sufficiency_status === "insufficient"
      && receipt.assembled_input.packet_disposition === "omitted_insufficient"
      && graphClaims.length === 0 && citationMap === null
      && value.answer_basis === "committed_plan";
  }
  if (status === "plan_only_graph_unused") {
    return graphClaims.length === 0 && citationMap === null && value.answer_basis === "committed_plan";
  }
  return graphClaims.length > 0 && citationMap !== null && value.answer_basis === "committed_plan_plus_world_graph";
}

function isWorldPlanGraphExecution(value: unknown): value is WorldPlanGraphExecutionProjectionV1 {
  return hasExactKeys(value, ["schema", "claimability", "authorization_state", "automatic_redispatch"])
    && value.schema === "dmb_agent_plan_world_graph_execution_projection_v1"
    && ["safe_to_reclaim_without_dispatch", "explicit_new_attempt_required", "blocked_unknown_or_sent", "completed"]
      .includes(String(value.claimability))
    && ["none", "authorized", "sdk_entered", "response_received", "known_not_sent", "outcome_unknown"]
      .includes(String(value.authorization_state))
    && value.automatic_redispatch === false;
}

function isWorldPlanContextProjection(
  value: unknown,
  request?: WorldPlanAgentTurnRequestV1,
  historyTurn = false,
): value is WorldPlanAgentPlanContextV1 {
  const required = ["schema", "receipt", "completion", "execution"];
  const allowed = historyTurn && isRecord(value) && !Object.prototype.hasOwnProperty.call(value, "delivery_replay")
    ? required
    : [...required, "delivery_replay"];
  if (!hasExactKeys(value, allowed)
    || value.schema !== "dmb_agent_plan_world_graph_context_response_v1"
    || !isWorldPlanGraphReceipt(value.receipt, request)
    || (value.completion !== null && !isWorldPlanGraphCompletion(value.completion, value.receipt))
    || (value.execution !== null && !isWorldPlanGraphExecution(value.execution))
    || (Object.prototype.hasOwnProperty.call(value, "delivery_replay") && typeof value.delivery_replay !== "boolean")) return false;
  if (!historyTurn && (!Object.prototype.hasOwnProperty.call(value, "delivery_replay")
    || value.completion === null)) return false;
  if (value.delivery_replay === true && value.completion === null) return false;
  return true;
}

function isHistoryReference(value: unknown): boolean {
  return hasExactKeys(value, [
    "resolution", "kind", "object_id", "revision", "content_sha256", "object_revision", "work_revision_id", "revision_n",
  ])
    && ["resolved", "absent", "unresolved", "unavailable"].includes(String(value.resolution))
    && isNullableString(value.kind)
    && isNullableString(value.object_id)
    && isNullableString(value.revision)
    && isNullableString(value.content_sha256)
    && (value.object_revision === null || isPositiveRevision(value.object_revision))
    && isNullableString(value.work_revision_id)
    && (value.revision_n === null || isPositiveRevision(value.revision_n));
}

function isHistoryTurn(
  value: unknown,
  schema: "dmb_agent_conversation_history_v1" | "dmb_agent_conversation_history_v2" | "dmb_agent_conversation_history_v3",
  worldId: string,
): boolean {
  if (!isRecord(value)) return false;
  const hasPlanContext = Object.prototype.hasOwnProperty.call(value, "plan_context");
  const keys = ["turn_id", "sequence", "lifecycle_status", "user_text", "assistant_text", "provenance"];
  if (schema === "dmb_agent_conversation_history_v2" && hasPlanContext) keys.push("plan_context");
  if (schema === "dmb_agent_conversation_history_v3") {
    keys.push("idempotency_key");
    if (hasPlanContext) keys.push("plan_context");
  }
  if (!hasExactKeys(value, keys)
    || typeof value.turn_id !== "string" || !value.turn_id.trim()
    || !isPositiveRevision(value.sequence)
    || !["accepted", "running", "completed", "failed", "interrupted"].includes(String(value.lifecycle_status))
    || typeof value.user_text !== "string"
    || !isNullableString(value.assistant_text)
    || (schema === "dmb_agent_conversation_history_v3"
      && (typeof value.idempotency_key !== "string"
        || !/^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(value.idempotency_key)))) return false;
  const provenance = value.provenance;
  if (!hasExactKeys(provenance, [
    "world_id", "surface_resolution", "surface_id", "surface_instance_id", "primary_work", "supporting_work", "selected_object",
  ])
    || provenance.world_id !== worldId
    || !["resolved", "absent", "unresolved", "unavailable"].includes(String(provenance.surface_resolution))
    || !isNullableString(provenance.surface_id)
    || !isNullableString(provenance.surface_instance_id)
    || !isHistoryReference(provenance.primary_work)
    || !Array.isArray(provenance.supporting_work)
    || !provenance.supporting_work.every(isHistoryReference)
    || !isHistoryReference(provenance.selected_object)) return false;
  if (!hasPlanContext) return true;
  if (schema === "dmb_agent_conversation_history_v1") return false;
  if (!isWorldPlanContextProjection(value.plan_context, undefined, true)
    || !isHistoryPlanContextBound(value.plan_context, provenance, worldId)) return false;
  const hasCompletion = value.plan_context.completion !== null;
  return value.lifecycle_status === "completed" ? hasCompletion : !hasCompletion;
}

function isHistoryPlanContextBound(value: unknown, provenance: unknown, worldId: string): boolean {
  if (!isRecord(value) || !isRecord(value.receipt) || !isRecord(value.receipt.plan_basis)
    || !isRecord(provenance) || !isRecord(provenance.primary_work)) return false;
  const basis = value.receipt.plan_basis;
  const primary = provenance.primary_work;
  const target = value.receipt.playable_target;
  const targetReferences = Array.isArray(provenance.supporting_work)
    ? provenance.supporting_work.filter((reference): reference is Record<string, unknown> =>
      isRecord(reference) && reference.kind === "dmb_plan_playable_target_v1")
    : [];
  const targetIsBound = target === null
    ? targetReferences.length === 0
    : isRecord(target)
      && hasExactKeys(target, ["schema", "kind", "id", "marker_grammar_version"])
      && target.schema === "dmb_plan_playable_target_receipt_v1"
      && ["scene", "beat", "choice", "option"].includes(String(target.kind))
      && typeof target.id === "string"
      && /^(scene|beat|choice|option):[a-z0-9][a-z0-9._-]{0,127}$/.test(target.id)
      && target.id.startsWith(`${String(target.kind)}:`)
      && ["v1", "v2"].includes(String(target.marker_grammar_version))
      && targetReferences.length === 1
      && targetReferences[0]!.resolution === "resolved"
      && targetReferences[0]!.object_id === target.id
      && targetReferences[0]!.revision === target.marker_grammar_version
      && targetReferences[0]!.content_sha256 === null
      && targetReferences[0]!.object_revision === null
      && targetReferences[0]!.work_revision_id === null
      && targetReferences[0]!.revision_n === null;
  return targetIsBound
    && provenance.world_id === worldId
    && basis.world_id === worldId
    && primary.resolution === "resolved"
    && primary.kind === "plan"
    && primary.object_id === basis.document_id
    && primary.revision === String(basis.object_revision)
    && primary.object_revision === basis.object_revision
    && primary.work_revision_id === basis.work_revision_id
    && primary.revision_n === basis.revision_n
    && primary.content_sha256 === basis.content_sha256;
}

function isWorldConversationHistory(value: unknown): value is WorldAgentConversationHistoryResponse {
  if (!isRecord(value)) return false;
  const schema = value.schema;
  if (schema !== "dmb_agent_conversation_history_v1"
    && schema !== "dmb_agent_conversation_history_v2"
    && schema !== "dmb_agent_conversation_history_v3") return false;
  if (!hasExactKeys(value, [
    "schema", "world_id", "conversation_state", "conversation_id", "active_conversation_id", "pointer_revision", "turns", "next_before_sequence",
  ])
    || typeof value.world_id !== "string" || !value.world_id.trim()
    || !["active", "absent"].includes(String(value.conversation_state))
    || !isNullableString(value.conversation_id)
    || !isNullableString(value.active_conversation_id)
    || !Number.isSafeInteger(value.pointer_revision) || (value.pointer_revision as number) < 0
    || !Array.isArray(value.turns)) return false;
  const turns = value.turns;
  if (typeof value.world_id !== "string"
    || !turns.every((turn) => isHistoryTurn(turn, schema, value.world_id as string))) return false;
  const seenIds = new Set<string>();
  let previousSequence = 0;
  let sequenceDirection: "ascending" | "descending" | null = null;
  for (const turn of turns) {
    if (!isRecord(turn) || typeof turn.turn_id !== "string" || !isPositiveRevision(turn.sequence)
      || turn.sequence === previousSequence || seenIds.has(turn.turn_id)) return false;
    if (previousSequence !== 0) {
      const currentDirection = turn.sequence > previousSequence ? "ascending" : "descending";
      if (sequenceDirection !== null && currentDirection !== sequenceDirection) return false;
      sequenceDirection = currentDirection;
    }
    previousSequence = turn.sequence;
    seenIds.add(turn.turn_id);
  }
  return (value.next_before_sequence === null || isPositiveRevision(value.next_before_sequence))
    && (value.conversation_state === "absent"
      ? value.conversation_id === null && value.active_conversation_id === null && turns.length === 0
      : typeof value.conversation_id === "string" && value.active_conversation_id === value.conversation_id);
}

function canonicalJson(value: unknown): string {
  if (Array.isArray(value)) return `[${value.map(canonicalJson).join(",")}]`;
  if (isRecord(value)) {
    return `{${Object.keys(value).sort().map((key) => `${JSON.stringify(key)}:${canonicalJson(value[key])}`).join(",")}}`;
  }
  const encoded = JSON.stringify(value);
  if (encoded === undefined) throw new Error("Unsupported value in canonical JSON payload.");
  return encoded;
}

async function isReceiptDigestBound(receipt: WorldPlanGraphContextReceiptV1): Promise<boolean> {
  try {
    const { context_receipt_sha256: expected, ...payload } = receipt;
    const digest = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(canonicalJson(payload)));
    const actual = Array.from(new Uint8Array(digest), (byte) => byte.toString(16).padStart(2, "0")).join("");
    return actual === expected;
  } catch {
    return false;
  }
}

async function isHistoryReceiptDigestBound(turn: unknown): Promise<boolean> {
  if (!isRecord(turn) || !isRecord(turn.plan_context)) return true;
  const context = turn.plan_context;
  return isWorldPlanContextProjection(context, undefined, true)
    && isReceiptDigestBound(context.receipt);
}

async function areHistoryReceiptDigestsBound(page: WorldAgentConversationHistoryResponse): Promise<boolean> {
  const checked = await Promise.all(page.turns.map(isHistoryReceiptDigestBound));
  return checked.every(Boolean);
}

function historyPageMatchesPendingAskConversation(
  page: WorldAgentConversationHistoryResponse,
  origin: WorldPlanPendingAskOrigin,
): boolean {
  if (page.conversation_state !== "active"
    || !page.conversation_id
    || page.active_conversation_id !== page.conversation_id) return false;

  if (origin.conversationId !== null) {
    return page.conversation_id === origin.conversationId
      && page.pointer_revision === origin.pointerRevision;
  }

  // The first accepted turn opens the World conversation and advances its
  // pointer exactly once. Any later pointer change makes the page ambiguous.
  return origin.pointerRevision < Number.MAX_SAFE_INTEGER
    && page.pointer_revision === origin.pointerRevision + 1;
}

const URL_NAMESPACE_UUID = "6ba7b811-9dad-11d1-80b4-00c04fd430c8";

function uuidBytes(value: string): Uint8Array {
  return Uint8Array.from(value.replaceAll("-", "").match(/.{2}/g) ?? [], (pair) => Number.parseInt(pair, 16));
}

async function pendingGraphAskIdempotencyKey(stored: StoredPendingAsk): Promise<string | null> {
  const envelope = stored.envelope;
  if (!envelope?.request.plan_context_policy) return null;
  const worldId = envelope.origin.worldId;
  const turnId = envelope.request.turn_id;
  if (!worldId || !turnId) return null;
  try {
    const namespace = uuidBytes(URL_NAMESPACE_UUID);
    if (namespace.length !== 16) return null;
    const name = new TextEncoder().encode(`dmb-agent-turn:${worldId}:${turnId}`);
    const input = new Uint8Array(namespace.length + name.length);
    input.set(namespace);
    input.set(name, namespace.length);
    const digest = new Uint8Array(await crypto.subtle.digest("SHA-1", input));
    digest[6] = (digest[6]! & 0x0f) | 0x50;
    digest[8] = (digest[8]! & 0x3f) | 0x80;
    const hex = Array.from(digest.slice(0, 16), (byte) => byte.toString(16).padStart(2, "0")).join("");
    return `${hex.slice(0, 8)}-${hex.slice(8, 12)}-${hex.slice(12, 16)}-${hex.slice(16, 20)}-${hex.slice(20)}`;
  } catch {
    return null;
  }
}

function completedHistoryTurnMatchesPendingGraphAsk(
  page: WorldAgentConversationHistoryResponse,
  turn: WorldAgentConversationHistoryTurn,
  stored: StoredPendingAsk,
  idempotencyKey: string,
): boolean {
  const envelope = stored.envelope;
  if (!envelope) return false;
  const { request, origin } = envelope;
  if (page.schema !== "dmb_agent_conversation_history_v3"
    || !("idempotency_key" in turn)
    || turn.idempotency_key !== idempotencyKey
    || !request.plan_context_policy
    || page.world_id !== origin.worldId
    || !historyPageMatchesPendingAskConversation(page, origin)
    || turn.lifecycle_status !== "completed"
    || turn.user_text !== request.message
    || typeof turn.assistant_text !== "string"
    || !turn.assistant_text.trim()
    || turn.provenance.world_id !== origin.worldId
    || turn.provenance.surface_resolution !== "resolved"
    || turn.provenance.surface_id !== request.surface.surface_id
    || typeof request.surface.instance_id !== "string"
    || turn.provenance.surface_instance_id !== request.surface.instance_id) return false;

  const context = "plan_context" in turn ? turn.plan_context : undefined;
  if (!context
    || !isWorldPlanContextProjection(context, request, true)
    || context.completion === null
    || (context.execution !== null && context.execution.claimability !== "completed")
    || !isHistoryPlanContextBound(context, turn.provenance, origin.worldId)) return false;

  const basis = context.receipt.plan_basis;
  if (basis.world_id !== origin.worldId
    || basis.document_id !== origin.documentId
    || basis.object_revision !== origin.objectRevision
    || basis.work_revision_id !== origin.workRevisionId
    || basis.revision_n !== origin.revisionN
    || basis.content_sha256 !== origin.contentSha256) return false;

  const completedText = context.completion.answer_segments.map((segment) => segment.text).join("\n");
  return turn.assistant_text === completedText;
}

function failedHistoryTurnMatchesPendingGraphAsk(
  page: WorldAgentConversationHistoryResponse,
  turn: WorldAgentConversationHistoryTurn,
  stored: StoredPendingAsk,
  idempotencyKey: string,
): boolean {
  const envelope = stored.envelope;
  if (!envelope) return false;
  const { request, origin } = envelope;
  if (page.schema !== "dmb_agent_conversation_history_v3"
    || !("idempotency_key" in turn)
    || turn.idempotency_key !== idempotencyKey
    || !request.plan_context_policy
    || page.world_id !== origin.worldId
    || !historyPageMatchesPendingAskConversation(page, origin)
    || turn.lifecycle_status !== "failed"
    || turn.user_text !== request.message
    || turn.provenance.world_id !== origin.worldId
    || turn.provenance.surface_resolution !== "resolved"
    || turn.provenance.surface_id !== request.surface.surface_id
    || typeof request.surface.instance_id !== "string"
    || turn.provenance.surface_instance_id !== request.surface.instance_id) return false;

  const context = "plan_context" in turn ? turn.plan_context : undefined;
  if (!context
    || !isWorldPlanContextProjection(context, request, true)
    || context.completion !== null
    || context.execution === null
    || context.execution.claimability === "completed"
    || !isHistoryPlanContextBound(context, turn.provenance, origin.worldId)) return false;

  const basis = context.receipt.plan_basis;
  return basis.world_id === origin.worldId
    && basis.document_id === origin.documentId
    && basis.object_revision === origin.objectRevision
    && basis.work_revision_id === origin.workRevisionId
    && basis.revision_n === origin.revisionN
    && basis.content_sha256 === origin.contentSha256;
}

async function classifyTerminalFailedGraphPendingAsks(
  page: WorldAgentConversationHistoryResponse,
  worldId: string,
  documentId: string,
  isCurrent: () => boolean,
): Promise<ConfirmedTerminalFailureAsk[]> {
  if (page.schema !== "dmb_agent_conversation_history_v3") return [];
  const pending = readPendingAsks(worldId, documentId)
    .filter((stored) => stored.envelope?.request.plan_context_policy);
  const correlated = await Promise.all(pending.map(async (stored) => ({
    stored,
    key: await pendingGraphAskIdempotencyKey(stored),
  })));
  if (!isCurrent()) return [];

  const candidates = correlated.flatMap(({ stored, key }) => {
    if (!key) return [];
    const matchingRows = page.turns.filter((turn) => "idempotency_key" in turn && turn.idempotency_key === key);
    if (matchingRows.length !== 1) return [];
    const turn = matchingRows[0]!;
    return failedHistoryTurnMatchesPendingGraphAsk(page, turn, stored, key)
      ? [{ stored, key, historyTurnId: turn.turn_id }]
      : [];
  });
  const matchesByKey = new Map<string, number>();
  for (const candidate of candidates) matchesByKey.set(candidate.key, (matchesByKey.get(candidate.key) ?? 0) + 1);
  return candidates
    .filter((candidate) => matchesByKey.get(candidate.key) === 1)
    .map(({ stored, historyTurnId }) => ({
      storageKey: stored.storageKey,
      serialized: stored.serialized,
      historyTurnId,
    }));
}

function reconcileCompletedGraphPendingAsks(
  page: WorldAgentConversationHistoryResponse,
  worldId: string,
  documentId: string,
  isCurrent: () => boolean,
): Promise<{ refreshPendingList: boolean; storageError: string | null }> {
  if (page.schema !== "dmb_agent_conversation_history_v3") {
    return Promise.resolve({ refreshPendingList: false, storageError: null });
  }
  const pending = readPendingAsks(worldId, documentId)
    .filter((stored) => stored.envelope?.request.plan_context_policy);
  return Promise.all(pending.map(async (stored) => ({
    stored,
    key: await pendingGraphAskIdempotencyKey(stored),
  }))).then((correlated) => {
    if (!isCurrent()) return { refreshPendingList: false, storageError: null };
    const candidates = correlated.flatMap(({ stored, key }) => {
      if (!key) return [];
      const matchingRows = page.turns.filter((turn) => "idempotency_key" in turn && turn.idempotency_key === key);
      if (matchingRows.length !== 1) return [];
      const turn = matchingRows[0]!;
      return completedHistoryTurnMatchesPendingGraphAsk(page, turn, stored, key)
        ? [{ stored, key }]
        : [];
    });
    const matchesByKey = new Map<string, number>();
    for (const candidate of candidates) matchesByKey.set(candidate.key, (matchesByKey.get(candidate.key) ?? 0) + 1);

  let refreshPendingList = false;
  let storageError: string | null = null;
    for (const candidate of candidates) {
      if (!isCurrent()) break;
      if (matchesByKey.get(candidate.key) !== 1) continue;
      const result = clearPendingAskIfUnchanged(candidate.stored);
      if (result.kind === "cleared") {
        dispatchPendingAskSettlement(candidate.stored, result);
      } else {
        // A replacement envelope or storage failure stays visible and intact.
        refreshPendingList = true;
        if (result.kind === "unavailable") storageError = result.message;
      }
    }
    return { refreshPendingList, storageError };
  });
}

async function validateWorldPlanResponse(
  value: unknown,
  request: WorldPlanAgentTurnRequestV1,
): Promise<ValidationResult> {
  const hasPolicy = request.plan_context_policy !== undefined;
  const baseKeys = [
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
  const topKeys = hasPolicy ? [...baseKeys, "plan_context"] : baseKeys;
  if (!hasExactKeys(value, topKeys)
    || value.schema !== (hasPolicy ? "dmb_agent_turn_response_v2" : "dmb_agent_turn_response_v1")
    || value.client_thread_id !== request.client_thread_id
    || value.turn_id !== request.turn_id) {
    return { ok: false, message: RESPONSE_MISMATCH };
  }

  const planContext = hasPolicy
    ? isWorldPlanContextProjection(value.plan_context, request) ? value.plan_context : null
    : null;
  if (hasPolicy && !planContext) return { ok: false, message: RESPONSE_MISMATCH };
  if (planContext && !await isReceiptDigestBound(planContext.receipt)) {
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

  const replayTrace = (isRecord(value.answer)
    && isDurableReceiptReplayTrace(value.answer.trace, request.turn_id))
    || planContext?.delivery_replay === true;
  const work = value.primary_work;
  if (!hasExactKeys(work, ["status", "kind", "object_id", "revision_used", "expected_revision", "content_basis"])
    || work.kind !== "plan"
    || work.object_id !== request.primary_work.object_id
    || work.expected_revision !== request.primary_work.expected_revision
    || work.status !== "resolved"
    || work.revision_used !== request.primary_work.expected_revision
    || !isPositiveRevision(work.revision_used)
    || !(matchesCommittedPlanBasis(work.content_basis, request)
      || (work.content_basis === null && replayTrace))) {
    return { ok: false, message: "The saved Plan identity or committed revision could not be verified. Reopen the Plan and try again." };
  }
  const replayed = work.content_basis === null && replayTrace;
  const responseContentBasis = matchesCommittedPlanBasis(work.content_basis, request)
    ? work.content_basis
    : null;

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
  const conversationKeys = isRecord(conversation) && Object.prototype.hasOwnProperty.call(conversation, "conversation_id")
    ? ["client_thread_id", "turn_id", "pointer_status", "pointer_id", "conversation_id"]
    : ["client_thread_id", "turn_id", "pointer_status", "pointer_id"];
  if (!hasExactKeys(conversation, conversationKeys)
    || conversation.client_thread_id !== request.client_thread_id
    || conversation.turn_id !== request.turn_id
    || !POINTER_STATUSES.includes(conversation.pointer_status as (typeof POINTER_STATUSES)[number])
    || !isNullableString(conversation.pointer_id)
    || (Object.prototype.hasOwnProperty.call(conversation, "conversation_id")
      && !isNullableString(conversation.conversation_id))) {
    return { ok: false, message: RESPONSE_MISMATCH };
  }
  if (replayed && (conversation.pointer_status !== "reused"
    || conversation.pointer_id !== null
    || typeof conversation.conversation_id !== "string"
    || !conversation.conversation_id.trim())) {
    return { ok: false, message: RESPONSE_MISMATCH };
  }

  const answer = value.answer;
  const expectedGraphGrounded = planContext?.completion
    ? ["graph_grounded", "graph_grounded_partial"].includes(planContext.completion.answer_context_status)
    : false;
  if (!hasExactKeys(answer, ["status", "text", "code", "message", "graph_grounded", "trace"])
    || !["ok", "error"].includes(String(answer.status))
    || !isNullableString(answer.text)
    || !isNullableString(answer.code)
    || !isNullableString(answer.message)
    || answer.graph_grounded !== expectedGraphGrounded
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
    ...(responseContentBasis ? {
      contentBasis: {
        worldId: responseContentBasis.world_id,
        documentId: responseContentBasis.document_id,
        objectRevision: responseContentBasis.object_revision,
        workRevisionId: responseContentBasis.work_revision_id,
        revisionN: responseContentBasis.revision_n,
        contentSha256: responseContentBasis.content_sha256,
        committedStatus: "committed" as const,
        hasDivergentWorkingCopy: responseContentBasis.has_divergent_working_copy,
      },
    } : {}),
    clientWorkState: request.client_work_state,
    graphStatus: "not_requested",
    pointerStatus: conversation.pointer_status as WorldPlanAgentTurnResolvedSummary["pointerStatus"],
  };
  return { ok: true, value: { answer: answer.text, trace: answer.trace, summary, conversationId: typeof conversation.conversation_id === "string" ? conversation.conversation_id : null, replayed } };
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
  playableTarget = null,
  playableTargetBasis = null,
  playableTargetStale = false,
  onClearPlayableTarget = () => undefined,
  playableEditTarget = null,
  playableEditTargetGeneration = 0,
  playableEditTargetStale = false,
  playableEditTargetDirty = false,
  onClearPlayableEditTarget = () => undefined,
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
  const scopeKey = `${worldId}\u001f${documentId ?? ""}`;
  const requestFenceKey = JSON.stringify({
    worldId: verifiedWorldId,
    documentId,
    surfaceInstanceId,
    revision,
    planReady,
    saveInFlight,
  });
  const askPresentationFenceKey = JSON.stringify({
    requestFenceKey,
    playableTarget: playableTarget ? {
      kind: playableTarget.kind,
      id: playableTarget.id,
    } : null,
    playableTargetBasis: playableTargetBasis ? {
      revision: playableTargetBasis.revision,
      contentSha256: playableTargetBasis.contentSha256,
    } : null,
    playableTargetStale,
    selectionGeneration,
    draftGeneration,
    savedDirty,
  });
  const proposalFenceKey = JSON.stringify({
    requestFenceKey,
    draftGeneration,
    selectionGeneration,
    savedDirty,
    playableEditTarget,
    playableEditTargetGeneration,
    playableEditTargetStale,
    paneOpen: agent.paneState.isOpen,
    hasAskHost: Boolean(askSlot?.hostElement),
    agentScope: agent.scope ? {
      campaignId: agent.scope.campaignId,
      surfaceId: agent.scope.surfaceId ?? null,
      sessionNumber: agent.scope.sessionNumber,
      documentId: agent.scope.documentId ?? null,
    } : null,
  });
  const [composerMessage, setComposerMessage] = useState("");
  const [composerIntent, setComposerIntent] = useState<"discuss" | "propose">("discuss");
  const [useWorldGraphForAsk, setUseWorldGraphForAsk] = useState(false);
  const [graphCredentialStatus, setGraphCredentialStatus] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [editError, setEditError] = useState<string | null>(null);
  const [sending, setSending] = useState(false);
  const [composing, setComposing] = useState(false);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [traceVisible, setTraceVisible] = useState(false);
  const [history, setHistory] = useState<WorldAgentConversationHistoryResponse | null>(null);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [olderLoading, setOlderLoading] = useState(false);
  const [historyError, setHistoryError] = useState<string | null>(null);
  const [historyRefreshNonce, setHistoryRefreshNonce] = useState(0);
  const [proposalOrderRevision, setProposalOrderRevision] = useState(0);
  const [pendingAsks, setPendingAsks] = useState<StoredPendingAsk[]>([]);
  const [confirmedTerminalFailureAsks, setConfirmedTerminalFailureAsks] = useState<ConfirmedTerminalFailureAsk[]>([]);
  const [pendingAskLoadError, setPendingAskLoadError] = useState<string | null>(null);
  const [pendingCommands, setPendingCommands] = useState<StoredPendingNewConversation[]>([]);
  const [pendingCommandLoadError, setPendingCommandLoadError] = useState<string | null>(null);
  const [newConversationSending, setNewConversationSending] = useState(false);
  const [newConversationError, setNewConversationError] = useState<string | null>(null);
  const [conversationNotice, setConversationNotice] = useState<string | null>(null);
  const [editReview, setEditReview] = useState<WorldPlanEditReview | null>(null);
  const [sectionTargets, setSectionTargets] = useState<PlanSectionOption[]>([]);
  const [selectedSectionTargetId, setSelectedSectionTargetId] = useState("");
  const [sectionTargetStatus, setSectionTargetStatus] = useState<PlanSectionTargetStatus | null>(null);
  const [actionHistory, setActionHistory] = useState<WorldPlanActionProjection[]>([]);
  const [actionHistoryError, setActionHistoryError] = useState<string | null>(null);
  const requestRef = useRef<{ token: symbol; scopeKey: string; fenceKey: string } | null>(null);
  const newConversationRef = useRef<symbol | null>(null);
  const historySnapshotRef = useRef<WorldAgentConversationHistoryResponse | null>(null);
  const historyGenerationRef = useRef(0);
  const legacyHistoryRef = useRef<{ scopeKey: string; thread: AgentInteractionThread; rawBytes: string | null } | null>(null);
  const proposalRequestRef = useRef<{ token: symbol; threadId: string; fenceKey: string; providerThreadId: string | null } | null>(null);
  const proposalIntentRef = useRef<{ fingerprint: string; idempotencyKey: string } | null>(null);
  const editReviewRef = useRef<WorldPlanEditReview | null>(null);
  const sectionScanRef = useRef<PlanSectionScan | null>(null);
  const sectionOperationRef = useRef<symbol | null>(null);
  const latestRef = useRef({
    fenceKey: requestFenceKey,
    presentationFenceKey: askPresentationFenceKey,
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
  const storedLegacyHistory = useMemo(() => {
    if (!namespace || !documentId
      || activeThread?.worldPlanProposalHistory !== WORLD_PLAN_LOCAL_PROPOSAL_HISTORY) return null;
    try {
      for (const summary of listAgentThreads(namespace, "plan", documentId)) {
        if (summary.threadId === activeThread.threadId) continue;
        const thread = loadAgentThreadById(namespace, summary.threadId);
        if (!thread || thread.worldPlanProposalHistory === WORLD_PLAN_LOCAL_PROPOSAL_HISTORY) continue;
        return {
          scopeKey,
          thread,
          rawBytes: window.localStorage.getItem(threadStorageKey(namespace, thread.threadId)),
        };
      }
    } catch {
      return null;
    }
    return null;
  }, [activeThread?.threadId, activeThread?.worldPlanProposalHistory, documentId, namespace, scopeKey]);
  if (storedLegacyHistory
    && (!legacyHistoryRef.current || legacyHistoryRef.current.scopeKey !== scopeKey)) {
    legacyHistoryRef.current = storedLegacyHistory;
  }
  const preservedLegacyHistory = legacyHistoryRef.current?.scopeKey === scopeKey
    ? legacyHistoryRef.current
    : storedLegacyHistory;
  const legacyThreadForDisplay = activeThread?.worldPlanProposalHistory === WORLD_PLAN_LOCAL_PROPOSAL_HISTORY
    ? preservedLegacyHistory?.thread ?? null
    : activeThread;
  const proposalThreadForDisplay = activeThread?.worldPlanProposalHistory === WORLD_PLAN_LOCAL_PROPOSAL_HISTORY
    ? activeThread
    : null;
  const proposalOrderKeyForDisplay = namespace && proposalThreadForDisplay
    ? localProposalOrderStorageKey(namespace, proposalThreadForDisplay.threadId)
    : null;
  const proposalOrderForDisplay = useMemo(
    () => proposalOrderKeyForDisplay ? readLocalProposalOrder(proposalOrderKeyForDisplay) : null,
    [proposalOrderKeyForDisplay, proposalOrderRevision],
  );
  const conversationDisplay = useMemo(
    () => buildWorldConversationDisplayEvents(
      history,
      proposalThreadForDisplay?.turns ?? [],
      proposalOrderForDisplay?.positions ?? [],
    ),
    [history, proposalOrderForDisplay, proposalThreadForDisplay?.turns],
  );

  latestRef.current.fenceKey = requestFenceKey;
  latestRef.current.presentationFenceKey = askPresentationFenceKey;
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
      newConversationRef.current = null;
      historyGenerationRef.current += 1;
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
    proposalRequestRef.current = null;
    editReviewRef.current = null;
    setComposing(false);
    setEditReview(null);
    setEditError(null);
  }, [proposalFenceKey]);

  useEffect(() => {
    let active = true;
    const generation = ++historyGenerationRef.current;
    historySnapshotRef.current = null;
    setOlderLoading(false);
    setHistory(null);
    setHistoryError(null);
    setConfirmedTerminalFailureAsks([]);
    if (!scopeMatches || !verifiedWorldId || !documentId) {
      setHistoryLoading(false);
      return () => { active = false; };
    }

    setHistoryLoading(true);
    void getWorldAgentConversationHistory(verifiedWorldId, {
      limit: WORLD_HISTORY_PAGE_SIZE,
      includeTurnCorrelation: true,
    })
      .then(async (page) => {
        if (!active || generation !== historyGenerationRef.current) return;
        const validState = isWorldConversationHistory(page)
          && page.world_id === verifiedWorldId
          && await areHistoryReceiptDigestsBound(page);
        if (!validState) {
          setHistoryError("The World conversation response did not match the selected World or contained an invalid Graph-context receipt. Refresh history before continuing.");
          return;
        }
        if (!active || generation !== historyGenerationRef.current) return;
        try {
          const reconciliation = await reconcileCompletedGraphPendingAsks(
            page,
            verifiedWorldId,
            documentId,
            () => active && generation === historyGenerationRef.current,
          );
          if (!active || generation !== historyGenerationRef.current) return;
          if (reconciliation.refreshPendingList) refreshPendingAskList();
          if (reconciliation.storageError) setPendingAskLoadError(reconciliation.storageError);
          const terminalFailures = await classifyTerminalFailedGraphPendingAsks(
            page,
            verifiedWorldId,
            documentId,
            () => active && generation === historyGenerationRef.current,
          );
          if (!active || generation !== historyGenerationRef.current) return;
          setConfirmedTerminalFailureAsks(terminalFailures);
        } catch (reason) {
          setPendingAskLoadError(reason instanceof Error
            ? reason.message
            : "Browser storage is unavailable for pending Ask recovery.");
        }
        historySnapshotRef.current = page;
        setHistory(page);
      })
      .catch((reason: unknown) => {
        if (active && generation === historyGenerationRef.current) {
          setHistoryError(localOperatorCredentialFailure(reason, "refresh World history")
            ?? (reason instanceof Error ? reason.message : "Could not load the World conversation."));
        }
      })
      .finally(() => {
        if (active && generation === historyGenerationRef.current) setHistoryLoading(false);
      });
    return () => { active = false; };
  }, [scopeKey, scopeMatches, verifiedWorldId, documentId, historyRefreshNonce]);

  useEffect(() => {
    if (!scopeMatches || !verifiedWorldId || !documentId) {
      setPendingAsks([]);
      setPendingAskLoadError(null);
      return;
    }
    try {
      setPendingAsks(readPendingAsks(verifiedWorldId, documentId));
      setPendingAskLoadError(null);
    } catch (reason) {
      setPendingAskLoadError(reason instanceof Error
        ? reason.message
        : "Browser storage is unavailable for pending Ask recovery.");
    }
  }, [scopeKey, scopeMatches, verifiedWorldId, documentId]);

  useEffect(() => {
    if (!scopeMatches || !verifiedWorldId || !documentId) {
      setPendingCommands([]);
      setPendingCommandLoadError(null);
      return;
    }
    try {
      setPendingCommands(readPendingNewConversations(verifiedWorldId));
      setPendingCommandLoadError(null);
    } catch (reason) {
      setPendingCommandLoadError(reason instanceof Error
        ? reason.message
        : "Browser storage is unavailable for New Conversation recovery.");
    }
  }, [scopeKey, scopeMatches, verifiedWorldId, documentId]);

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
    requestRef.current = null;
    newConversationRef.current = null;
    historyGenerationRef.current += 1;
    historySnapshotRef.current = null;
    setOlderLoading(false);
    if (legacyHistoryRef.current?.scopeKey !== scopeKey) legacyHistoryRef.current = null;
    setSending(false);
    setNewConversationSending(false);
    setTraceVisible(false);
    setComposerMessage("");
    setComposerIntent("discuss");
    setError(null);
    setConversationNotice(null);
  }, [scopeKey]);

  function refreshPendingAskList() {
    if (!verifiedWorldId || !documentId) return;
    try {
      setPendingAsks(readPendingAsks(verifiedWorldId, documentId));
      setPendingAskLoadError(null);
    } catch (reason) {
      setPendingAskLoadError(reason instanceof Error
        ? reason.message
        : "Browser storage is unavailable for pending Ask recovery.");
    }
  }

  useLayoutEffect(() => {
    if (!scopeMatches || !verifiedWorldId || !documentId) return;
    const onPendingAskSettled = (event: Event) => {
      const detail = (event as CustomEvent<unknown>).detail;
      if (!isPendingAskClearedEventDetail(detail)
        || detail.origin.worldId !== verifiedWorldId
        || detail.origin.documentId !== documentId
        || !detail.key.startsWith(pendingAskPrefix(verifiedWorldId, documentId))) {
        return;
      }
      refreshPendingAskList();
      setHistoryRefreshNonce((current) => current + 1);
    };
    window.addEventListener(PENDING_ASK_CLEARED_EVENT, onPendingAskSettled);
    window.addEventListener(PENDING_ASK_ACCEPTED_EVENT, onPendingAskSettled);
    return () => {
      window.removeEventListener(PENDING_ASK_CLEARED_EVENT, onPendingAskSettled);
      window.removeEventListener(PENDING_ASK_ACCEPTED_EVENT, onPendingAskSettled);
    };
  }, [scopeMatches, verifiedWorldId, documentId]);

  function refreshPendingCommandList() {
    if (!verifiedWorldId || !documentId) return;
    try {
      setPendingCommands(readPendingNewConversations(verifiedWorldId));
      setPendingCommandLoadError(null);
    } catch (reason) {
      setPendingCommandLoadError(reason instanceof Error
        ? reason.message
        : "Browser storage is unavailable for New Conversation recovery.");
    }
  }

  async function sendNewConversationCommand(stored: StoredPendingNewConversation) {
    const envelope = stored.envelope;
    if (!envelope || !scopeMatches || verifiedWorldId !== envelope.worldId
      || newConversationRef.current !== null) return;
    const token = Symbol("world-agent-new-conversation");
    newConversationRef.current = token;
    setNewConversationSending(true);
    setNewConversationError(null);
    setConversationNotice(null);
    const stillCurrent = () => latestRef.current.mounted
      && latestRef.current.scopeMatches
      && latestRef.current.verifiedWorldId === envelope.worldId
      && newConversationRef.current === token;
    try {
      const response = await postWorldAgentNewConversation(envelope.worldId, envelope.request);
      if (!stillCurrent()) return;
      if (response.schema !== "dmb_agent_new_conversation_response_v1"
        || response.world_id !== envelope.worldId
        || typeof response.conversation_id !== "string"
        || !response.conversation_id
        || !Number.isSafeInteger(response.pointer_revision)
        || !(response.active_conversation_id === null || typeof response.active_conversation_id === "string")) {
        throw new Error("The New Conversation response did not match its saved command.");
      }
      try {
        window.localStorage.removeItem(stored.storageKey);
        refreshPendingCommandList();
      } catch (reason) {
        setPendingCommandLoadError(reason instanceof Error
          ? reason.message
          : "The command succeeded, but its local recovery envelope could not be cleared. Retrying remains safe.");
      }
      setConversationNotice("New World conversation confirmed. Refreshing the server transcript.");
      setHistoryRefreshNonce((current) => current + 1);
    } catch (reason) {
      if (!stillCurrent()) return;
      if (reason instanceof LiveApiError && reason.status === 409) {
        try {
          window.localStorage.removeItem(stored.storageKey);
          refreshPendingCommandList();
        } catch {
          setPendingCommandLoadError("The pointer changed. The old command was rejected; clear its saved recovery item before starting a deliberate new command.");
        }
        setNewConversationError("The World conversation pointer changed. Current server history is being refreshed; review it, then deliberately start a new conversation if you still want one.");
        setHistoryRefreshNonce((current) => current + 1);
      } else {
        setNewConversationError(localOperatorCredentialFailure(reason, "retry the saved command; its ID and pointer snapshot are preserved")
          ?? (reason instanceof Error
            ? `The command outcome is uncertain. Retry the saved command to use the same command ID and pointer snapshot. ${reason.message}`
            : "The command outcome is uncertain. Retry the saved command to use the same command ID and pointer snapshot."));
      }
    } finally {
      if (newConversationRef.current === token) {
        newConversationRef.current = null;
        setNewConversationSending(false);
      }
    }
  }

  function startNewConversation() {
    const pointer = historySnapshotRef.current;
    if (!scopeMatches || !verifiedWorldId || !documentId || !pointer
      || historyLoading || sending || composing || newConversationSending
      || pendingCommands.some((item) => item.envelope !== null)) return;
    const request: WorldAgentNewConversationRequestV1 = {
      schema: "dmb_agent_new_conversation_v1",
      command_id: crypto.randomUUID(),
      expected_pointer_revision: pointer.pointer_revision,
      expected_active_conversation_id: pointer.active_conversation_id,
    };
    const envelope: WorldPlanPendingNewConversation = {
      schema: "dmb_world_pending_new_conversation_v1",
      worldId: verifiedWorldId,
      documentId,
      request,
    };
    const storageKey = pendingNewConversationStorageKey(verifiedWorldId, request.command_id);
    const serialized = JSON.stringify(envelope);
    try {
      window.localStorage.setItem(storageKey, serialized);
      if (window.localStorage.getItem(storageKey) !== serialized) {
        throw new Error("Browser storage did not preserve the exact command envelope.");
      }
      refreshPendingCommandList();
      setComposerMessage("");
      setError(null);
      setNewConversationError(null);
      void sendNewConversationCommand({ storageKey, envelope, error: null });
    } catch (reason) {
      setNewConversationError(reason instanceof Error
        ? `The command was not sent because its recovery envelope could not be saved. ${reason.message}`
        : "The command was not sent because browser storage is unavailable.");
    }
  }

  function connectGraphSession() {
    void connectNativeGraphSession().then(() => setGraphCredentialStatus("Local Agent and Graph session active."))
      .catch(() => setGraphCredentialStatus("Local Agent and Graph session unavailable."));
  }

  function clearGraphSession() {
    void revokeNativeGraphSession().then(() => setGraphCredentialStatus("Local Agent and Graph session revoked."))
      .catch(() => setGraphCredentialStatus("Local Agent and Graph session could not be revoked."));
  }

  function toggleTraceVisibility() {
    if (!scopeMatches || sending || composing || requestRef.current || proposalRequestRef.current) return;
    setTraceVisible((current) => !current);
  }

  async function sendPendingAsk(stored: StoredPendingAsk, initialDispatch = false) {
    const envelope = stored.envelope;
    if (!envelope || !scopeMatches || verifiedWorldId !== envelope.origin.worldId
      || documentId !== envelope.origin.documentId || requestRef.current) return;
    if (envelope.request.plan_context_policy && !initialDispatch) {
      setConversationNotice("This Graph-context Ask is not reposted from browser recovery. Refresh World history to check whether it completed before taking another action.");
      setHistoryRefreshNonce((current) => current + 1);
      return;
    }
    const token = Symbol("world-plan-agent-turn");
    const originScopeKey = `${envelope.origin.worldId}\u001f${envelope.origin.documentId}`;
    requestRef.current = { token, scopeKey: originScopeKey, fenceKey: requestFenceKey };
    const submittedPresentationFenceKey = askPresentationFenceKey;
    setSending(true);
    setError(null);
    setConversationNotice(null);
    // A changed selection only changes how this successful turn is presented; it must not abandon a server-accepted turn.
    const isCurrent = () => latestRef.current.mounted
      && latestRef.current.scopeMatches
      && latestRef.current.verifiedWorldId === envelope.origin.worldId
      && latestRef.current.documentId === envelope.origin.documentId
      && requestRef.current?.token === token;

    try {
      const response: unknown = await postWorldPlanAgentTurn(envelope.request);
      // The captured request is authoritative even when this SPA component has unmounted.
      const validation = await validateWorldPlanResponse(response, envelope.request);
      if (!validation.ok) throw new Error(validation.message);
      const origin = envelope.origin;
      const requestBasisMatchesOrigin = origin.worldId === envelope.request.owner_scope.world_id
        && origin.documentId === envelope.request.primary_work.object_id
        && origin.objectRevision === envelope.request.primary_work.expected_revision
        && origin.revisionN === envelope.request.primary_work.expected_revision_n
        && origin.contentSha256 === envelope.request.primary_work.expected_content_sha256
        && typeof origin.workRevisionId === "string"
        && Boolean(origin.workRevisionId.trim());
      const responseBasisMatchesOrigin = validation.value.replayed
        ? requestBasisMatchesOrigin
        : requestBasisMatchesOrigin
          && validation.value.summary.contentBasis?.worldId === origin.worldId
          && validation.value.summary.contentBasis?.documentId === origin.documentId
          && validation.value.summary.contentBasis?.objectRevision === origin.objectRevision
          && validation.value.summary.contentBasis?.workRevisionId === origin.workRevisionId
          && validation.value.summary.contentBasis?.revisionN === origin.revisionN
          && validation.value.summary.contentBasis?.contentSha256 === origin.contentSha256;
      if (!validation.value.conversationId || !responseBasisMatchesOrigin) {
        throw new Error("The durable Ask result did not identify its original World conversation and committed basis. The saved request remains available for exact recovery.");
      }

      const clearResult = clearPendingAskIfUnchanged(stored);
      dispatchPendingAskSettlement(stored, clearResult);
      if (clearResult.kind === "unavailable" && isCurrent()) {
        setPendingAskLoadError(clearResult.message);
      }
      if (!isCurrent()) return;

      const currentlyActiveConversationId = historySnapshotRef.current?.active_conversation_id ?? null;
      const belongsToPreviousConversation = Boolean(
        (envelope.origin.conversationId && envelope.origin.conversationId !== validation.value.conversationId)
        || (currentlyActiveConversationId && currentlyActiveConversationId !== validation.value.conversationId),
      );
      const submittedContextChanged = latestRef.current.presentationFenceKey !== submittedPresentationFenceKey;
      if (submittedContextChanged) {
        const target = envelope.request.playable_target;
        let originalContext = "saved Plan context";
        if (target) {
          const targetLabel = target.id.startsWith(`${target.kind}:`)
            ? target.id
            : `${target.kind} ${target.id}`;
          originalContext = `selected card ${targetLabel}`;
        }
        setConversationNotice(
          `The server confirmed this Ask for its original ${originalContext} at committed Plan object revision ${envelope.origin.objectRevision}. Refreshing World history with that submitted provenance.`,
        );
      } else {
        setConversationNotice(belongsToPreviousConversation
          ? `The server confirmed this Ask under conversation ${validation.value.conversationId}. It was not inserted into the currently active conversation; refreshing World history.`
          : "The server confirmed this Ask. Refreshing World history.");
      }
      setComposerMessage("");
    } catch (reason) {
      const definitivePreDispatchFailure = envelope.request.plan_context_policy
        ? graphContextPreDispatchFailure(reason)
        : null;
      if (definitivePreDispatchFailure) {
        const clearResult = clearPendingAskIfUnchanged(stored);
        if (clearResult.kind === "cleared") dispatchPendingAskSettlement(stored, clearResult);
        if (isCurrent()) {
          if (clearResult.kind === "unavailable") setPendingAskLoadError(clearResult.message);
          else if (clearResult.kind === "changed") refreshPendingAskList();
          setError(definitivePreDispatchFailure);
        }
      } else if (isCurrent()) {
        setError(envelope.request.plan_context_policy
          ? localOperatorCredentialFailure(reason, "refresh World history to inspect this turn; do not resend it")
            ?? `The outcome of this Graph-context Ask is uncertain. Refresh World history before taking another action. This saved turn will not be reposted. ${reason instanceof Error ? reason.message : ""}`
          : localOperatorCredentialFailure(reason, "retry the saved Ask; its exact request and turn ID are preserved")
            ?? (reason instanceof Error
              ? `The Ask outcome is uncertain. Retry the saved request to reuse its exact turn ID and intent. ${reason.message}`
              : "The Ask outcome is uncertain. Retry the saved request to reuse its exact turn ID and intent."));
      }
    } finally {
      if (requestRef.current?.token === token) {
        requestRef.current = null;
        setSending(false);
      }
    }
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const message = composerMessage.trim();
    const pointerSnapshot = historySnapshotRef.current;
    const targetAtSubmit = playableTarget;
    const targetBasisAtSubmit = playableTargetBasis;
    if (composerIntent !== "discuss" || !planReady || !scopeMatches || !namespace || !documentId || !surfaceInstanceId
      || !isPositiveRevision(revision) || saveInFlight || !message || sending || requestRef.current
      || historyLoading || historyError || !pointerSnapshot || playableTargetStale
      || (targetAtSubmit && (!targetBasisAtSubmit || targetBasisAtSubmit.revision !== revision))) return;

    const startingFenceKey = requestFenceKey;
    setSending(true);
    setError(null);
    setConversationNotice(null);
    const preparationToken = Symbol("world-plan-agent-turn-preparation");
    requestRef.current = {
      token: preparationToken,
      scopeKey,
      fenceKey: startingFenceKey,
    };
    const stillPreparing = () => {
      const currentPointer = historySnapshotRef.current;
      return latestRef.current.mounted
        && latestRef.current.scopeMatches
        && latestRef.current.verifiedWorldId === worldId
        && latestRef.current.documentId === documentId
        && latestRef.current.fenceKey === startingFenceKey
        && currentPointer !== null
        && sameHistoryPointer(pointerSnapshot, currentPointer)
        && requestRef.current?.token === preparationToken;
    };

    try {
      const committedRevision: unknown = await getWorldOwnedPlanCommittedRevision(documentId);
      if (!stillPreparing()) return;
      const contentBasis = readCommittedPlanBasis(committedRevision, worldId, documentId, revision);
      if (!contentBasis) {
        throw new Error("The committed Plan changed or could not be verified. Refresh the Plan before asking.");
      }
      if (targetAtSubmit && targetBasisAtSubmit
        && (contentBasis.object_revision !== targetBasisAtSubmit.revision
          || contentBasis.content_sha256 !== targetBasisAtSubmit.contentSha256)) {
        throw new Error("The selected card belongs to a different committed Plan revision. Select it again before asking.");
      }
      const request: WorldPlanAgentTurnRequestV1 = {
        schema: "dmb_agent_turn_request_v1",
        client_thread_id: crypto.randomUUID(),
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
        ...(useWorldGraphForAsk ? {
          plan_context_policy: { schema: "dmb_plan_context_policy_v1" as const, policy: "auto_plan_world" as const },
        } : {}),
        ...(targetAtSubmit ? {
          playable_target: { schema: "dmb_plan_playable_target_v1" as const, ...targetAtSubmit },
        } : {}),
        message,
      };
      const origin: WorldPlanPendingAskOrigin = {
        worldId,
        documentId,
        objectRevision: revision,
        workRevisionId: contentBasis.work_revision_id,
        revisionN: contentBasis.revision_n,
        contentSha256: contentBasis.content_sha256,
        pointerRevision: pointerSnapshot.pointer_revision,
        conversationId: pointerSnapshot.active_conversation_id,
      };
      const envelope: WorldPlanPendingAskEnvelope = {
        schema: "dmb_world_plan_pending_ask_v1",
        request,
        origin,
        createdAt: new Date().toISOString(),
      };
      const storageKey = pendingAskStorageKey(worldId, documentId, origin, request.turn_id);
      const serialized = JSON.stringify(envelope);
      try {
        window.localStorage.setItem(storageKey, serialized);
        if (window.localStorage.getItem(storageKey) !== serialized) {
          throw new Error("Browser storage did not preserve the exact Ask envelope.");
        }
      } catch (reason) {
        throw new Error(`The Ask was not sent because its recovery envelope could not be saved. ${reason instanceof Error ? reason.message : "Browser storage is unavailable."}`);
      }
      setUseWorldGraphForAsk(false);
      refreshPendingAskList();
      requestRef.current = null;
      setSending(false);
      await sendPendingAsk({ storageKey, serialized, envelope, error: null }, true);
    } catch (reason) {
      if (requestRef.current?.token === preparationToken) {
        requestRef.current = null;
        setSending(false);
        setError(reason instanceof Error ? reason.message : "The Ask could not be prepared.");
      }
    }
  }

  function submitComposer(event: FormEvent<HTMLFormElement>) {
    if (composerIntent === "propose") {
      void composeEdit(event);
      return;
    }
    void submit(event);
  }

  async function loadOlderTurns() {
    const current = historySnapshotRef.current;
    if (!current || !current.next_before_sequence || olderLoading || historyLoading) return;
    const cursor = current.next_before_sequence;
    const generation = historyGenerationRef.current;
    setOlderLoading(true);
    setHistoryError(null);
    try {
      const page = await getWorldAgentConversationHistory(current.world_id, {
        limit: WORLD_HISTORY_PAGE_SIZE,
        beforeSequence: cursor,
        includeTurnCorrelation: true,
      });
      const latest = historySnapshotRef.current;
      if (generation !== historyGenerationRef.current) return;
      const validPage = isWorldConversationHistory(page)
        && page.world_id === current.world_id
        && await areHistoryReceiptDigestsBound(page);
      if (!validPage || !latest || !sameHistoryPointer(current, latest)
        || !sameHistoryPointer(latest, page)
        || page.world_id !== current.world_id) {
        setHistoryError("The World conversation pointer changed or the older page contained an invalid Graph-context receipt. The stale page was discarded.");
        setHistoryRefreshNonce((nonce) => nonce + 1);
        return;
      }
      const merged: WorldAgentConversationHistoryResponse = {
        ...latest,
        turns: (mergeHistoryTurns(page.turns, latest.turns) as WorldAgentConversationHistoryResponseV3["turns"]),
        next_before_sequence: page.next_before_sequence,
      };
      historySnapshotRef.current = merged;
      setHistory(merged);
    } catch (reason) {
      if (generation === historyGenerationRef.current) {
        setHistoryError(localOperatorCredentialFailure(reason, "refresh World history")
          ?? (reason instanceof Error ? reason.message : "Could not load older World turns."));
      }
    } finally {
      if (generation === historyGenerationRef.current) setOlderLoading(false);
    }
  }

  function refreshWorldHistory() {
    setHistoryRefreshNonce((nonce) => nonce + 1);
  }

  function exportLegacyLocalHistory() {
    const thread = legacyThreadForDisplay;
    if (!thread) return;
    const preserved = legacyHistoryRef.current?.scopeKey === scopeKey
      && legacyHistoryRef.current.thread.threadId === thread.threadId
      ? legacyHistoryRef.current.rawBytes
      : null;
    let storedBytes = preserved;
    if (storedBytes === null) {
      try {
        storedBytes = window.localStorage.getItem(threadStorageKey(thread.campaignId, thread.threadId));
      } catch {
        storedBytes = null;
      }
    }
    const exportFile = new Blob([storedBytes ?? JSON.stringify(thread, null, 2)], {
      type: "application/json",
    });
    const url = URL.createObjectURL(exportFile);
    const link = document.createElement("a");
    link.href = url;
    link.download = `world-plan-local-history-${encodeURIComponent(worldId)}-${encodeURIComponent(documentId ?? "plan")}.json`;
    link.click();
    URL.revokeObjectURL(url);
  }

  function historyTurnProvenanceLabel(turn: WorldAgentConversationHistoryTurnV1): string {
    const surface = turn.provenance.surface_id ?? "unknown surface";
    const work = turn.provenance.primary_work;
    if (work.object_id) {
      const revision = work.revision_n === null ? "" : ` · revision ${work.revision_n}`;
      return `Historical surface: ${surface} · ${work.kind ?? "work"} ${work.object_id}${revision}`;
    }
    return `Historical surface: ${surface} · no primary work identity`;
  }

  function graphContextStatusLabel(status: WorldPlanGraphAnswerContextStatusV1): string {
    switch (status) {
      case "graph_grounded":
        return "Grounded in complete World Graph evidence.";
      case "graph_grounded_partial":
        return "Partially grounded in World Graph evidence; coverage was incomplete.";
      case "plan_only_insufficient_evidence":
        return "No sufficient World Graph evidence was available; this answer uses the saved Plan context only.";
      case "plan_only_graph_unused":
        return "Graph context was available; no Graph claims were cited or used in the structured answer.";
    }
  }

  function graphExecutionGuidance(
    execution: WorldPlanGraphExecutionProjectionV1 | null,
    hasCompletion: boolean,
    terminalFailureConfirmed = false,
    terminalFailureRecorded = false,
  ): string {
    if (terminalFailureConfirmed) {
      return `Exact V3 World history records this turn as failed. ${confirmedFailureExecutionGuidance(execution)}`;
    }
    if (terminalFailureRecorded) {
      return `World history records this turn as failed. ${confirmedFailureExecutionGuidance(execution)}`;
    }
    const guidance = (() => {
      if (!execution) return "No execution recovery status was recorded. Refresh World history before taking another action.";
      if (execution.claimability === "completed") {
        return hasCompletion
          ? "The server recorded this Ask as complete. Its structured outcome is shown above; this turn will not be automatically resent."
          : "Execution history is inconsistent: claimability is completed, but no completion was recorded. Refresh World history before taking another action.";
      }
      if (["authorized", "sdk_entered", "response_received", "outcome_unknown"].includes(execution.authorization_state)) {
        const detail = execution.authorization_state === "authorized"
          ? "The server authorized this attempt."
          : execution.authorization_state === "sdk_entered"
            ? "The provider call was entered."
            : execution.authorization_state === "response_received"
              ? "The provider returned a response."
              : "The attempt outcome is unknown.";
        return `${detail} Refresh World history before taking another action; this turn will not be automatically resent.`;
      }
      if (execution.claimability === "safe_to_reclaim_without_dispatch"
        && ["none", "known_not_sent"].includes(execution.authorization_state)) {
        return "The server confirms provider dispatch did not begin. Submit a new Ask if you want another attempt; recovery will not repost this turn.";
      }
      if (execution.claimability === "explicit_new_attempt_required") {
        return "A new attempt requires a new Ask. This saved turn will not be automatically reposted.";
      }
      if (execution.authorization_state === "known_not_sent") {
        return "The server confirms the provider was not sent this request. Follow the execution state above and use a new Ask if another attempt is needed.";
      }
      return "The attempt may have been sent or its outcome is unknown. Refresh World history; this turn will not be automatically resent.";
    })();
    return guidance;
  }

  function confirmedFailureExecutionGuidance(execution: WorldPlanGraphExecutionProjectionV1 | null): string {
    const noDispatchPair = execution?.claimability === "safe_to_reclaim_without_dispatch"
      && ["none", "known_not_sent"].includes(execution.authorization_state);
    const explicitAttemptPair = execution?.claimability === "explicit_new_attempt_required"
      && execution.authorization_state === "known_not_sent";
    const blockedAttemptPair = execution?.claimability === "blocked_unknown_or_sent"
      && ["authorized", "sdk_entered", "response_received", "outcome_unknown"].includes(execution.authorization_state);

    if (!execution) return "The execution disposition was not recorded. The saved turn is not automatically reposted; this view offers no retry.";
    if (!noDispatchPair && !explicitAttemptPair && !blockedAttemptPair) {
      const claimabilityLabel: Record<WorldPlanGraphExecutionProjectionV1["claimability"], string> = {
        safe_to_reclaim_without_dispatch: "safe to reclaim without dispatch",
        explicit_new_attempt_required: "explicit new attempt required",
        blocked_unknown_or_sent: "blocked because it may have been sent",
        completed: "completed",
      };
      const authorizationLabel: Record<WorldPlanGraphExecutionProjectionV1["authorization_state"], string> = {
        none: "no authorization event",
        authorized: "authorization granted",
        sdk_entered: "provider call entered",
        response_received: "provider response received",
        known_not_sent: "request known not sent",
        outcome_unknown: "execution outcome unknown",
      };
      return `Execution projection conflicts: claimability is ${claimabilityLabel[execution.claimability]} while authorization state is ${authorizationLabel[execution.authorization_state]}. The saved turn is not automatically reposted; this view offers no retry.`;
    }

    const disposition = noDispatchPair
      ? "Execution disposition: provider dispatch did not begin."
      : explicitAttemptPair
        ? "Execution disposition requires a separate new Ask for any new attempt."
        : execution.authorization_state === "response_received"
          ? "The provider returned a response; no final Graph-context completion was recorded."
          : execution.authorization_state === "sdk_entered"
            ? "The provider call was entered; its final outcome was not recorded."
            : execution.authorization_state === "authorized"
              ? "The server authorized this attempt; later provider execution is not established."
              : "The provider execution outcome remains unknown.";
    return `${disposition} The saved turn is not automatically reposted; this view offers no retry.`;
  }

  function isPendingAskFailureConfirmed(item: StoredPendingAsk, historyTurnId?: string): boolean {
    return Boolean(item.envelope?.request.plan_context_policy)
      && confirmedTerminalFailureAsks.some((classification) =>
        classification.storageKey === item.storageKey
        && classification.serialized === item.serialized
        && (historyTurnId === undefined || classification.historyTurnId === historyTurnId));
  }

  function isHistoryTurnFailureConfirmed(historyTurnId: string): boolean {
    return pendingAsks.some((item) => isPendingAskFailureConfirmed(item, historyTurnId));
  }

  function isWorldHistoryTurnFailed(historyTurnId: string): boolean {
    const page = historySnapshotRef.current;
    if (!page || page.world_id !== verifiedWorldId) return false;
    const matchingTurns = page.turns.filter((turn) => turn.turn_id === historyTurnId);
    return matchingTurns.length === 1 && matchingTurns[0]!.lifecycle_status === "failed";
  }

  function renderGraphContextHistory(turn: WorldAgentConversationHistoryTurn) {
    if (!("plan_context" in turn) || !turn.plan_context) return null;
    const { completion, execution } = turn.plan_context;
    const terminalFailureConfirmed = isHistoryTurnFailureConfirmed(turn.turn_id);
    const terminalFailureRecorded = isWorldHistoryTurnFailed(turn.turn_id);
    const claims = completion?.answer_segments.filter((segment) => segment.kind === "graph_claim") ?? [];
    const citations = completion?.citation_map?.entries ?? [];
    const citationByClaim = new Map(citations.map((entry) => [entry.claim_id, entry]));
    return (
      <section className="world-plan-agent-conversation__graph-context" aria-label="World Graph evidence and recovery">
        <p><strong>Graph context:</strong> {completion
          ? graphContextStatusLabel(completion.answer_context_status)
          : terminalFailureRecorded
            ? "This World history turn failed; no final Graph-context completion was recorded."
            : "No final Graph-context completion has been recorded for this turn yet."}</p>
        {claims.map((claim, index) => {
          const citation = citationByClaim.get(claim.claim_id);
          if (!citation) return null;
          const count = citation.evidence_ref_ids.length;
          return (
            <div key={`${turn.turn_id}-graph-claim-${index}`} className="world-plan-agent-conversation__graph-citation">
              <p>
                <q>{claim.text}</q>
                <span> · World Graph {citation.target_kind} · Graph revision <code>{citation.graph_revision}</code> · source text not opened.</span>
              </p>
              <details>
                <summary>{count} evidence reference{count === 1 ? "" : "s"}</summary>
                <ul>
                  {citation.evidence_ref_ids.map((referenceId) => <li key={referenceId}><code>{referenceId}</code></li>)}
                </ul>
              </details>
            </div>
          );
        })}
        <p className="world-plan-agent-conversation__context">
          {graphExecutionGuidance(execution, completion !== null, terminalFailureConfirmed, terminalFailureRecorded)}
        </p>
      </section>
    );
  }

  function historyTurnPlayableTargetLabel(turn: WorldAgentConversationHistoryTurnV1): string | null {
    const references = Array.isArray(turn.provenance.supporting_work)
      ? turn.provenance.supporting_work.filter((reference) => reference.kind === "dmb_plan_playable_target_v1")
      : [];
    if (references.length === 0) return null;
    if (references.length !== 1) return "Target receipt unavailable: duplicate Playable target references.";
    const reference = references[0];
    const primary = turn.provenance.primary_work;
    const id = reference.object_id;
    const targetKind = typeof id === "string" ? id.split(":", 1)[0] : "";
    const validIdentity = typeof id === "string"
      && ["scene", "beat", "choice", "option"].includes(targetKind)
      && id.startsWith(`${targetKind}:`)
      && /^(scene|beat|choice|option):[a-z0-9][a-z0-9._-]{0,127}$/.test(id)
      && reference.resolution === "resolved"
      && reference.revision !== null
      && ["v1", "v2"].includes(reference.revision)
      && reference.content_sha256 === null
      && reference.object_revision === null
      && reference.work_revision_id === null
      && reference.revision_n === null;
    const validBasis = primary.resolution === "resolved"
      && primary.kind === "plan"
      && typeof primary.object_id === "string"
      && Number.isSafeInteger(primary.object_revision)
      && typeof primary.work_revision_id === "string"
      && Number.isSafeInteger(primary.revision_n)
      && typeof primary.content_sha256 === "string"
      && /^[0-9a-f]{64}$/.test(primary.content_sha256);
    if (!validIdentity || !validBasis) {
      return "Target receipt unavailable: the stored target or exact committed Plan basis is malformed.";
    }
    return `Playable target: ${targetKind} ${id} · marker grammar ${reference.revision} · committed Plan ${primary.object_id}, object revision ${primary.object_revision}, WorkRevision ${primary.work_revision_id}, revision ${primary.revision_n}, SHA-256 ${primary.content_sha256}`;
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
    const instruction = composerMessage.trim();
    if (composerIntent !== "propose" || !planReady || !scopeMatches || !namespace || !documentId || !editBridge
      || !isPositiveRevision(revision) || saveInFlight || !instruction
      || composing || sending || requestRef.current || proposalRequestRef.current) return;
    if (playableEditTarget && playableEditTargetStale) {
      setEditError("The selected card is stale or no longer unique in this draft. Select it again before composing.");
      return;
    }

    const dispatchHistory = historySnapshotRef.current;
    const canAnchorProposal = !historyLoading && !historyError
      && dispatchHistory?.world_id === worldId
      && typeof dispatchHistory.conversation_id === "string"
      && dispatchHistory.conversation_id.length > 0
      && dispatchHistory.active_conversation_id === dispatchHistory.conversation_id
      && sameHistoryPointer(history, dispatchHistory);
    const proposalAnchor = canAnchorProposal && dispatchHistory
      ? {
        conversationId: dispatchHistory.conversation_id!,
        afterSequence: dispatchHistory.turns.reduce((max, turn) => Math.max(max, turn.sequence), 0),
      }
      : null;

    const providerThreadId = agent.activeThread?.threadId ?? null;
    if (activeThread?.worldPlanProposalHistory !== WORLD_PLAN_LOCAL_PROPOSAL_HISTORY) {
      let rawBytes: string | null = null;
      if (activeThread) {
        try {
          rawBytes = window.localStorage.getItem(threadStorageKey(activeThread.campaignId, activeThread.threadId));
        } catch {
          rawBytes = null;
        }
        legacyHistoryRef.current = { scopeKey, thread: activeThread, rawBytes };
      }
    }
    const currentThread = activeThread?.worldPlanProposalHistory === WORLD_PLAN_LOCAL_PROPOSAL_HISTORY
      ? activeThread
      : {
        ...createAgentInteractionThread(
          namespace,
          null,
          "plan",
          "hermes",
          threadTitleFromQuestion(instruction),
          documentId,
        ),
        worldPlanProposalHistory: WORLD_PLAN_LOCAL_PROPOSAL_HISTORY,
      };
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
      if (worldPlanEditReviewBefore(captured) === null) {
        throw new Error("The captured Plan target has no valid Before snapshot. Reselect it and compose the proposal again.");
      }
      const conversationHistory: WorldPlanDocumentEditProposalRequest["conversation_history"] = [];
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
      const admitted = await admitWorldPlanEditProposal(captured, response, request.idempotency_key);
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
      if (proposalAnchor) {
        const orderStorageKey = localProposalOrderStorageKey(namespace, currentThread.threadId);
        if (appendLocalProposalPosition(
          orderStorageKey,
          turnId,
          proposalAnchor.conversationId,
          proposalAnchor.afterSequence,
        )) {
          setProposalOrderRevision((current) => current + 1);
        }
      }
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
      setComposerMessage("");
      setComposerIntent("discuss");
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
    if (worldPlanEditReviewBefore(review.captured) === null) {
      discardEditReview();
      setEditError("The captured Plan target no longer has a valid Before snapshot. Reselect it and compose the proposal again.");
      return;
    }
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
      setComposerIntent("propose");
      setEditError(reason instanceof Error ? reason.message : "The proposal could not be applied to this mounted Plan.");
    }
  }

  if (!pageReady) return null;
  if (!documentId) {
    return <p className="world-plan-agent-draft-note" role="status">Save this Plan to start an Agent conversation.</p>;
  }
  if (!planReady || !askSlot?.hostElement || !agent.paneState.isOpen || !scopeMatches) return null;

  const currentReviewBefore = editReview ? worldPlanEditReviewBefore(editReview.captured) : null;
  const currentReview = editReview
    && currentReviewBefore !== null
    && editReview.fenceKey === proposalFenceKey
    && editReview.threadId === activeThread?.threadId
    ? editReview
    : null;
  const authorizationBlocked = [historyError, error, editError].some((message) =>
    message?.includes("local Agent and Graph session is missing or was rejected"));
  const pendingGraphAsk = pendingAsks.some((item) => item.envelope?.request.plan_context_policy);
  const savedAskRecords = pendingAsks.filter((item): item is StoredPendingAsk & { envelope: WorldPlanPendingAskEnvelope } =>
    item.envelope !== null);
  const pendingGraphAskRecords = savedAskRecords.filter((item) => item.envelope.request.plan_context_policy);
  const confirmedFailureCount = pendingGraphAskRecords.filter((item) => isPendingAskFailureConfirmed(item)).length;
  const unconfirmedGraphAskCount = pendingGraphAskRecords.length - confirmedFailureCount;
  const intentBusy = sending || composing || saveInFlight || !scopeMatches || currentReview !== null;
  const composerBusy = intentBusy || (composerIntent === "discuss"
    && (historyLoading || !history || Boolean(historyError)));
  const messageLimit = composerIntent === "discuss" ? 8000 : 4000;
  const messageTooLong = composerMessage.length > messageLimit;
  const localProposalPositionsByTurnId = new Map(
    (proposalOrderForDisplay?.positions ?? []).map((position) => [position.turnId, position]),
  );
  const renderProposalEvent = (
    turn: AgentInteractionTurn,
    position: WorldPlanLocalProposalPosition | null,
    detached: boolean,
  ) => (
    <article
      key={turn.turnId}
      className="world-plan-agent-conversation__proposal-event"
      data-proposal-turn-id={turn.turnId}
      data-asked-at={turn.askedAt}
      data-after-sequence={position?.afterSequence}
      data-world-conversation-id={position?.conversationId ?? undefined}
    >
      <p className="world-plan-agent-conversation__context">
        Local proposal · {turn.planEdit?.applied
          ? "Applied to your draft"
          : currentReview?.turnId === turn.turnId ? "Ready for review" : "Not applied"}
      </p>
      {detached ? (
        <p className="world-plan-agent-conversation__context">
          {position && history?.conversation_id !== position.conversationId
            ? "This proposal belongs to a different World conversation and stays in local activity."
            : "This proposal has no verified position in the active World conversation and stays in local activity."}
        </p>
      ) : null}
      <p><strong>You:</strong> {turn.question}</p>
      <div><strong>DungeonBuddy:</strong><WorldPlanAgentAnswer answer={turn.answer} /></div>
      {turn.planEdit?.applied ? (
        <p className="world-plan-agent-conversation__context">Apply changes your draft. Save keeps the changes.</p>
      ) : null}
      {currentReview?.turnId === turn.turnId ? (
        <section className="world-plan-agent-conversation__review" aria-label="Review proposed Plan edit">
          <h4>Review this proposal</h4>
          <p>{currentReview.admitted.response.summary}</p>
          {currentReview.admitted.response.assumptions.length ? (
            <ul>{currentReview.admitted.response.assumptions.map((assumption, index) => <li key={`${index}:${assumption}`}>{assumption}</li>)}</ul>
          ) : null}
          <div className="world-plan-agent-conversation__preview">
            <div>
              <h5>Before</h5>
              {currentReviewBefore?.kind === "captured-text" && currentReviewBefore.target ? (
                <p className="world-plan-agent-conversation__context">
                  Card target · {currentReviewBefore.target.kind} {currentReviewBefore.target.id}
                </p>
              ) : null}
              <pre>{currentReviewBefore?.kind === "caret"
                ? "Nothing selected · text will be inserted at the captured caret."
                : currentReviewBefore?.kind === "captured-text" && currentReviewBefore.markdown === "" && currentReviewBefore.target
                  ? "Empty card body"
                  : currentReviewBefore?.kind === "captured-text" ? currentReviewBefore.markdown : ""}</pre>
            </div>
            <div>
              <h5>After</h5>
              <pre>{currentReview.admitted.canonicalMarkdown}</pre>
            </div>
          </div>
          <p className="world-plan-agent-conversation__context">Apply changes your draft. Save keeps the changes.</p>
          <div className="world-plan-agent-conversation__review-actions">
            <button type="button" onClick={discardEditReview}>Discard proposal</button>
            <button type="button" onClick={() => { void applyEditReview(currentReview); }}>Apply changes</button>
          </div>
        </section>
      ) : null}
    </article>
  );

  return createPortal(
    <section className="world-plan-agent-conversation" aria-label="Saved World Plan conversation">
      <header className="world-plan-agent-conversation__header">
        <div>
          <h2>Plan conversation</h2>
          <p>{worldName} · Saved Plan</p>
        </div>
        <div className="world-plan-agent-conversation__actions">
          <button type="button" aria-expanded={settingsOpen} aria-controls="world-plan-agent-settings" onClick={() => setSettingsOpen((open) => !open)}>
            {settingsOpen ? "Close settings" : "Settings"}
          </button>
          <button
            type="button"
            onClick={startNewConversation}
            disabled={sending || composing || historyLoading || !history || newConversationSending
              || pendingCommands.some((item) => item.envelope !== null)}
          >
            {newConversationSending ? "Starting…" : "New conversation"}
          </button>
        </div>
      </header>
      <div className="world-plan-agent-conversation__body">
      {authorizationBlocked ? (
        <section className="world-plan-agent-conversation__auth-notice" role="alert">
          <p>{pendingGraphAsk
            ? "Local authorization was rejected. Reconnect in Settings, then refresh World history before taking another action."
            : "Local authorization was rejected. Reconnect in Settings, then refresh history or retry the saved request."}</p>
          <button type="button" onClick={() => setSettingsOpen(true)}>Open Settings</button>
        </section>
      ) : null}
      <section id="world-plan-agent-settings" className="world-plan-agent-conversation__settings" aria-label="Local operator Agent and Graph authorization" hidden={!settingsOpen}>
        <button type="button" onClick={connectGraphSession}>Connect local session</button>
        <button type="button" onClick={clearGraphSession}>Revoke local session</button>
        <p role="note">The local Agent and Graph session persists across reloads. A Plan Ask requests World Graph context only when you select that option.</p>
        {graphCredentialStatus ? <p role="status">{graphCredentialStatus}</p> : null}
      </section>
      <p className="world-plan-agent-conversation__notice" role="note">
        Talk through the saved Plan, or choose Propose edit to request a change. You’ll review it before it touches the draft.
      </p>
      {saveInFlight ? (
        <p className="world-plan-agent-conversation__saving" role="status">Conversation paused while the Plan is saving.</p>
      ) : null}
      {playableTarget ? (
        <section role="group" aria-label="Selected Playable card for Ask">
          <h3>Selected card for Ask</h3>
          <p><code>{playableTarget.kind} · {playableTarget.id}</code></p>
          {playableTargetBasis ? (
            <p>Committed Plan revision {playableTargetBasis.revision} · SHA-256 <code>{playableTargetBasis.contentSha256}</code></p>
          ) : null}
          <p role="note">Ask uses the committed Plan revision; unsaved edits are not included.</p>
          {playableTargetStale ? (
            <p role="alert">This card is stale or no longer uniquely matches the committed Plan. Select a card again or clear the target before asking.</p>
          ) : null}
          <button type="button" onClick={onClearPlayableTarget}>Clear selected card</button>
        </section>
      ) : null}
      {playableEditTarget ? (
        <section role="group" aria-label="Selected Playable card for edit">
          <h3>Selected card for edit</h3>
          <p><code>{playableEditTarget.kind} · {playableEditTarget.id}</code></p>
          <p role={playableEditTargetStale ? "alert" : "note"}>
            {playableEditTargetStale
              ? "This card is stale or no longer unique in the current draft. Select it again before composing."
              : playableEditTargetDirty
                ? "This proposal uses the unsaved Plan draft. Apply changes only the mounted draft; Save remains separate."
                : "This proposal uses the current Plan draft. Apply changes only the mounted draft; Save remains separate."}
          </p>
          <button type="button" onClick={onClearPlayableEditTarget}>Clear edit target</button>
        </section>
      ) : null}
      <section className="world-plan-agent-conversation__turns" aria-label="World conversation transcript" aria-live="polite">
        <h3>Conversation</h3>
        {historyLoading ? <p role="status">Loading the latest World conversation page…</p> : null}
        {historyError ? (
          <div role="group" aria-label="World history unavailable">
            {authorizationBlocked
              ? null
              : <p>{historyError}</p>}
            <button type="button" onClick={refreshWorldHistory} disabled={historyLoading}>Refresh World history</button>
          </div>
        ) : null}
        {history ? (
          <>
            <p role="note">
              {history.next_before_sequence !== null
                ? "Recent messages. Older turns are available below."
                : history.turns.length
                  ? "You’re all caught up."
                  : "No messages here yet. Start with a question about the saved Plan."}
            </p>
            {history.next_before_sequence !== null ? (
              <button type="button" onClick={() => { void loadOlderTurns(); }} disabled={olderLoading || historyLoading}>
                {olderLoading ? "Loading older turns…" : "Older turns"}
              </button>
            ) : null}
          </>
        ) : null}
        {conversationDisplay.events.map((event) => event.kind === "world" ? (
          <article key={`world:${event.turn.turn_id}`} data-sequence={event.turn.sequence}>
            <p className="world-plan-agent-conversation__context">
              Turn {event.turn.sequence} · {event.turn.lifecycle_status} · {historyTurnProvenanceLabel(event.turn)}
            </p>
            {(() => {
              const targetReceipt = historyTurnPlayableTargetLabel(event.turn);
              return targetReceipt ? (
                <p role={targetReceipt.startsWith("Target receipt unavailable") ? "alert" : "note"}>{targetReceipt}</p>
              ) : null;
            })()}
            <p><strong>You:</strong> {event.turn.user_text}</p>
            {event.turn.assistant_text ? (
              <div><strong>DungeonBuddy:</strong><WorldPlanAgentAnswer
                answer={event.turn.assistant_text}
                displaySegments={"plan_context" in event.turn && event.turn.plan_context?.completion
                  ? event.turn.plan_context.completion.answer_segments.map((segment) => segment.text)
                  : undefined}
              /></div>
            ) : (
              <p role="status">{isHistoryTurnFailureConfirmed(event.turn.turn_id)
                ? "This World history turn is recorded as failed."
                : isWorldHistoryTurnFailed(event.turn.turn_id)
                  ? "World history records this turn as failed."
                  : event.turn.lifecycle_status === "failed" || event.turn.lifecycle_status === "interrupted"
                  ? "This server turn did not complete."
                  : "DungeonBuddy is still working on this server turn."}</p>
            )}
            {renderGraphContextHistory(event.turn)}
          </article>
        ) : renderProposalEvent(event.turn, event.position, false))}
        {conversationNotice ? <p role="status">{conversationNotice}</p> : null}
      </section>
      {conversationDisplay.localActivity.length ? (
        <section className="world-plan-agent-conversation__local-activity" aria-label="Local Plan proposal activity">
          <h3>Local proposal activity</h3>
          <p className="world-plan-agent-conversation__context">
            These proposal events are stored in this browser and are not server World-history turns. Their position could not be matched safely to the active conversation.
          </p>
          {conversationDisplay.localActivity.map((turn) => renderProposalEvent(
            turn,
            localProposalPositionsByTurnId.get(turn.turnId) ?? null,
            true,
          ))}
        </section>
      ) : null}
      {newConversationError ? <p role="alert">{newConversationError}</p> : null}
      {pendingCommandLoadError ? <p role="alert">{pendingCommandLoadError}</p> : null}
      {pendingCommands.some((item) => item.error) ? (
        <section aria-label="Unreadable New Conversation recovery">
          <h3>Saved New Conversation command needs attention</h3>
          {pendingCommands.filter((item) => item.error).map((item) => (
            <p key={item.storageKey} role="alert">{item.error}</p>
          ))}
        </section>
      ) : null}
      {pendingCommands.some((item) => item.envelope) ? (
        <section aria-label="Pending New Conversation recovery">
          <h3>Pending New Conversation</h3>
          <p>A prior command has an uncertain outcome. Retry keeps its original command ID and pointer snapshot.</p>
          {pendingCommands.filter((item): item is StoredPendingNewConversation & { envelope: WorldPlanPendingNewConversation } => item.envelope !== null)
            .map((item) => (
              <button
                key={item.storageKey}
                type="button"
                disabled={newConversationSending || sending || composing}
                onClick={() => { void sendNewConversationCommand(item); }}
              >
                Retry saved New Conversation command
              </button>
            ))}
        </section>
      ) : null}
      {pendingAskLoadError ? <p role="alert">{pendingAskLoadError}</p> : null}
      {pendingAsks.some((item) => item.error) ? (
        <section aria-label="Unreadable Ask recovery">
          <h3>Saved Ask needs attention</h3>
          {pendingAsks.filter((item) => item.error).map((item) => (
            <p key={item.storageKey} role="alert">{item.error} The original bytes remain in browser storage.</p>
          ))}
        </section>
      ) : null}
      {pendingAsks.some((item) => item.envelope) ? (
        <section
          className="world-plan-agent-conversation__recovery"
          aria-label={confirmedFailureCount > 0 ? "Saved Ask recovery records" : "Pending Ask recovery"}
        >
          <h3>{confirmedFailureCount > 0
            ? `Ask recovery · ${unconfirmedGraphAskCount} Graph outcome${unconfirmedGraphAskCount === 1 ? "" : "s"} unconfirmed · ${confirmedFailureCount} recorded failure${confirmedFailureCount === 1 ? "" : "s"} · ${savedAskRecords.length} saved`
            : `Pending recovery · ${savedAskRecords.length}`}</h3>
          {pendingAsks.some((item) => item.envelope?.request.plan_context_policy) ? (
            <>
              <p>{confirmedFailureCount > 0
                ? `${unconfirmedGraphAskCount} Graph Ask outcome${unconfirmedGraphAskCount === 1 ? " remains" : "s remain"} unconfirmed in exact V3 World history; ${confirmedFailureCount} failed turn${confirmedFailureCount === 1 ? " is" : "s are"} already recorded. All ${pendingGraphAskRecords.length} Graph Ask records remain saved. Refresh never reposts them.`
                : "Saved Graph Asks stay in browser storage. Exact V3 World history may confirm completion or record a failure; Refresh never reposts them."}</p>
              <button type="button" onClick={refreshWorldHistory} disabled={historyLoading || !scopeMatches}>
                Refresh World history
              </button>
            </>
          ) : null}
          {pendingAsks.filter((item): item is StoredPendingAsk & { envelope: WorldPlanPendingAskEnvelope } => item.envelope !== null)
            .map((item) => {
              const graphAsk = Boolean(item.envelope.request.plan_context_policy);
              const terminalFailureConfirmed = graphAsk && isPendingAskFailureConfirmed(item);
              return (
                <details key={item.storageKey}>
                  <summary>
                    {graphAsk ? "Graph Ask" : "Ask"} · {item.envelope.request.turn_id}
                    {terminalFailureConfirmed ? " · failure confirmed" : ""}
                  </summary>
                  <p>Turn ID · <code>{item.envelope.request.turn_id}</code></p>
                  <p>Status · {graphAsk
                    ? terminalFailureConfirmed
                      ? "terminal failure confirmed in exact V3 World history"
                      : "outcome not confirmed in exact V3 World history"
                    : "saved for exact-ID retry"}</p>
                  <p>Plan object revision {item.envelope.origin.objectRevision} · content revision {item.envelope.origin.revisionN} · conversation {item.envelope.origin.conversationId ?? "not yet active"}</p>
                  {graphAsk ? (
                    <p role="status">{terminalFailureConfirmed
                      ? "Exact V3 World history records this turn as failed. The saved recovery record is preserved; Refresh will not repost it."
                      : "Exact V3 World history has not confirmed this Ask. Refresh checks its original conversation and Plan basis without reposting it."}</p>
                  ) : (
                    <button
                      type="button"
                      disabled={sending || composing || requestRef.current !== null}
                      onClick={() => { void sendPendingAsk(item); }}
                    >
                      Retry saved Ask
                    </button>
                  )}
                </details>
              );
            })}
        </section>
      ) : null}
      <details className="world-plan-agent-conversation__advanced">
        <summary>Advanced details</summary>
        <div className="world-plan-agent-conversation__advanced-content">
          <button
            type="button"
            aria-pressed={traceVisible}
            disabled={sending || composing || requestRef.current !== null || proposalRequestRef.current !== null}
            onClick={toggleTraceVisibility}
          >
            {traceVisible ? "Hide trace details" : "Show trace details"}
          </button>
          <section aria-label="Plan edit action status">
            <h3>Plan edit activity</h3>
            <button type="button" onClick={() => { void refreshActionHistory(); }} disabled={!scopeMatches || composing}>
              Refresh action status
            </button>
            {actionHistoryError ? <p role="alert">{actionHistoryError}</p> : null}
            {actionHistory.length ? (
              <ol>
                {actionHistory.map((action) => (
                  <li key={action.action_id}>
                    <strong>{action.status}</strong> · {action.instruction}
                    {action.playable_target_receipt ? (
                      <p className="world-plan-agent-conversation__context">
                        Target · {action.playable_target_receipt.kind} {action.playable_target_receipt.id}
                        · {action.playable_target_receipt.marker_grammar_version}
                        · {action.playable_target_receipt.body_scope}
                        · body SHA-256 <code>{action.playable_target_receipt.target_body_sha256}</code>
                      </p>
                    ) : null}
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
                          setComposerMessage(action.instruction);
                          setComposerIntent("propose");
                          setEditError(null);
                        }}
                      >
                        Continue with a new edit
                      </button>
                    ) : null}
                  </li>
                ))}
              </ol>
            ) : <p>No recent Plan edit actions.</p>}
          </section>
          {legacyThreadForDisplay?.turns.length ? (
            <section aria-label="Local-only legacy Plan history">
              <h3>Older local-only Plan history</h3>
              <p>This browser copy is not server-confirmed and is never used as conversation or proposal context.</p>
              <button type="button" onClick={exportLegacyLocalHistory}>Export local history JSON</button>
              <ol>
                {[...legacyThreadForDisplay.turns].reverse().map((turn) => (
                  <li key={turn.turnId}>
                    <p><strong>You:</strong> {turn.question}</p>
                    <div><strong>Local response{turn.planEdit ? " · Plan proposal" : ""}:</strong><WorldPlanAgentAnswer answer={turn.answer} /></div>
                    {turn.planEdit ? (
                      <p className="world-plan-agent-conversation__context">
                        Plan proposal · {turn.planEdit.applied ? "Applied to the local draft" : "Not applied"}
                      </p>
                    ) : null}
                    {turn.agentTurnResolved?.surfaceId === "plan" ? (
                      <p className="world-plan-agent-conversation__context">
                        Legacy local summary · committed revision {turn.agentTurnResolved.revisionUsed}; not part of server history.
                      </p>
                    ) : null}
                    {turn.trace && traceVisible ? <AgentTraceInspector trace={turn.trace} /> : null}
                  </li>
                ))}
              </ol>
            </section>
          ) : null}
          {proposalThreadForDisplay?.turns.some((turn) => turn.trace) ? (
            <section aria-label="Proposal trace details">
              <h3>Proposal traces</h3>
              {[...proposalThreadForDisplay.turns].reverse().filter((turn) => turn.trace && traceVisible).map((turn) => (
                <div key={turn.turnId}>
                  <p>{turn.question}</p>
                  <AgentTraceInspector trace={turn.trace!} />
                </div>
              ))}
            </section>
          ) : null}
        </div>
      </details>
      </div>
      {editBridge ? (
        <section className="world-plan-agent-conversation__composer" aria-label="Conversation composer">
          <form onSubmit={submitComposer}>
            <fieldset className="world-plan-agent-conversation__intent" disabled={intentBusy}>
              <legend>What would you like to do?</legend>
              <label>
                <input
                  type="radio"
                  name="world-plan-agent-intent"
                  value="discuss"
                  checked={composerIntent === "discuss"}
                  onChange={() => { setComposerIntent("discuss"); setError(null); setEditError(null); }}
                />
                Discuss
              </label>
              <label>
                <input
                  type="radio"
                  name="world-plan-agent-intent"
                  value="propose"
                  checked={composerIntent === "propose"}
                  onChange={() => { setComposerIntent("propose"); setError(null); setEditError(null); }}
                />
                Propose edit
              </label>
            </fieldset>
            {composerIntent === "propose" ? (
              <div className="world-plan-agent-conversation__target" role="group" aria-label="Choose where the proposed edit applies">
                {playableEditTarget ? (
                  <p role="note">The selected card body takes precedence over editor selection and Plan section. Clear the card target to use a different proposal target.</p>
                ) : null}
                <label htmlFor="world-plan-agent-plan-section">Plan section (optional)</label>
                <select
                  id="world-plan-agent-plan-section"
                  value={selectedSectionTargetId}
                  disabled={intentBusy || sectionTargets.length === 0 || Boolean(playableEditTarget)}
                  onChange={(event) => { void selectPlanSection(event.currentTarget.value); }}
                >
                  <option value="">Use the editor selection or caret</option>
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
                <button type="button" onClick={() => { void refreshPlanSections(); }} disabled={intentBusy}>
                  Refresh sections
                </button>
                <p role="note">Choosing a section selects it in the editor. A direct editor selection takes precedence. With no selected text, the proposal inserts at the caret.</p>
                {sectionTargetStatus ? (
                  <p role={sectionTargetStatus.kind === "error" ? "alert" : "status"}>{sectionTargetStatus.message}</p>
                ) : null}
              </div>
            ) : null}
            <label htmlFor="world-plan-agent-message">Message DungeonBuddy</label>
            <textarea
              id="world-plan-agent-message"
              value={composerMessage}
              onChange={(event) => setComposerMessage(event.currentTarget.value)}
              maxLength={messageLimit}
              disabled={composerBusy}
              placeholder={composerIntent === "discuss" ? "Ask about this Plan…" : "Describe the change you want…"}
            />
            {composerIntent === "discuss" ? (
              <label className="world-plan-agent-conversation__graph-context-opt-in">
                <input
                  type="checkbox"
                  checked={useWorldGraphForAsk}
                  disabled={composerBusy || !scopeMatches || !verifiedWorldId}
                  onChange={(event) => setUseWorldGraphForAsk(event.currentTarget.checked)}
                />
                Use this World’s Graph context for this question
              </label>
            ) : null}
            {messageTooLong ? <p role="alert">Edit requests can be at most 4,000 characters. Shorten this message to continue.</p> : null}
            {composerIntent === "discuss" && error && !authorizationBlocked ? <p role="alert">{error}</p> : null}
            {composerIntent === "propose" && editError && !authorizationBlocked ? <p role="alert">{editError}</p> : null}
            <div className="world-plan-agent-conversation__composer-footer">
              <p className="world-plan-agent-conversation__context">For proposed edits, Apply changes your draft. Save keeps the changes.</p>
              <button type="submit" disabled={composerBusy || !composerMessage.trim() || messageTooLong
                || (composerIntent === "discuss" && playableTargetStale)}>
                {sending ? "Sending…" : composing ? "Preparing proposal…" : saveInFlight ? "Saving…" : composerIntent === "discuss" ? "Send message" : "Propose edit"}
              </button>
            </div>
          </form>
        </section>
      ) : (
        <form className="world-plan-agent-conversation__composer" onSubmit={submitComposer}>
          <label htmlFor="world-plan-agent-message">Message DungeonBuddy</label>
          <textarea id="world-plan-agent-message" value={composerMessage} onChange={(event) => setComposerMessage(event.currentTarget.value)} maxLength={8000} disabled={composerBusy} />
          <label className="world-plan-agent-conversation__graph-context-opt-in">
            <input
              type="checkbox"
              checked={useWorldGraphForAsk}
              disabled={composerBusy || !scopeMatches || !verifiedWorldId}
              onChange={(event) => setUseWorldGraphForAsk(event.currentTarget.checked)}
            />
            Use this World’s Graph context for this question
          </label>
          {error ? <p role="alert">{error}</p> : null}
          <button type="submit" disabled={composerBusy || !composerMessage.trim() || playableTargetStale}>{sending ? "Sending…" : "Send message"}</button>
        </form>
      )}
    </section>,
    askSlot.hostElement,
  );
}
