import {ConversationLibrary} from '../../agentInteraction/ConversationLibrary';
import {useSurfaceConversationRequests,claimSurfaceConversationRequest,acceptSurfaceConversationRequest,failSurfaceConversationRequest,retrySurfaceConversationRequest,cancelSurfaceConversationRequest,cancelSurfaceConversationTarget,ownsSurfaceConversationRequest,type SurfaceConversationRequest} from '../../agentInteraction/surfaceConversationRequests';
import { groupConversationAttempts, isUnansweredFailure } from "../../agentInteraction/conversationAttemptGroups";
import {isSurfaceEvidenceCompletion,surfaceEvidenceReceiptBound} from "../../shared/surfaceEvidenceProtocol";
import {SurfaceEvidenceAnswer} from "./SurfaceEvidenceAnswer";
import { classifySurfaceComposerIntent } from "../../agentInteraction/surfaceComposerIntent";
import { SurfaceImagePromptAction } from "../../shared/SurfaceImagePromptAction";
import { isWorldPlayContextProjection, isWorldPlayGraphReceipt, isPlayContextProvenanceBound, playReceiptDigestsBound, isPlaySourceContext, isPlaySourceProvenanceBound, playSourceContextDigestBound } from '../../rulesLookup/playContextProtocol';
import { isSurfaceGraphInput } from '../../rulesLookup/surfaceGraphInput';
import { RulesAnswerEvidence } from '../../rulesLookup/RulesAnswerEvidence';
import { isRulesAnswerContext, rulesAnswerDigestsBound } from '../../rulesLookup/rulesAnswerProtocol';
import type { RulesAnswerContext, RulesUnclaimedContext } from '../../api/rulesLookupTypes';
import { usePlaySceneEdits } from "../../playSurface/agentEdit/PlaySceneEditReview";
import { ActionPromptInspector } from "./ActionPromptInspector";
import { ActionTerminalDiagnostic } from "./ActionTerminalDiagnostic";
import { PlayAnswerEvidence } from "./PlayAnswerEvidence";
import { BuildSavedSectionEvidence, isSavedSectionTargets } from "./BuildSavedSectionEvidence";
import { BuildSourcePassageEvidence, isBuildSourceCompletion, isSurfaceSourceCompletion } from "./BuildSourcePassageEvidence";
import { useBuildCompose } from "./BuildComposeProposal";
import { positionLatestAssistantReply } from "./conversationReplyPosition";
import { LoadedWorldGraphExplorer } from "../../graphLens/LoadedWorldGraphExplorer";
import { useEffect, useLayoutEffect, useMemo, useRef, useState, type FormEvent, type KeyboardEvent } from "react";
import { createPortal } from "react-dom";
import { BuddyReadiness } from "../../agentInteraction/BuddyReadiness";
import { ConversationRecovery } from "../../agentInteraction/ConversationRecovery";
import { ConversationDock } from "../../ui/ConversationDock";
import type { PlanConversationPresentationHosts } from "./PlanConversationDockAdapter";
import { PlanEditReview } from "./PlanEditReview";
import { ResponseEvidenceTabs } from "./ResponseEvidenceTabs";
import { ConversationWorkbook } from "./ConversationWorkbook";
import { BuddyActivity } from "./BuddyActivity";
import { BuddyContextTraceLoader } from "./BuddyContextTraceLoader";
import { BuddyTurnInspection } from "./BuddyTurnInspection";

import { getWorldCommandResolution, postWorldCommandResolution, getWorldAgentNewConversationStatus, getWorldAgentConversationHistory, getWorldOwnedPlanCommittedRevision, getWorldPlanDocumentEditActions, getWorldPlanConversationActions, postWorldAgentNewConversation, postWorldPlanAgentTurn, postWorldPlayAgentTurn, postWorldBuildAgentTurn, postWorldPlanDocumentEditProposal, postWorldGraphSourceAnchorRead, postWorldGraphRecapContextReadV2, connectNativeGraphSession, revokeNativeGraphSession, isValidWorldPlanGraphContextFailure, LiveApiError } from "../../api/liveApi";
import type {
  AgentInteractionThread,
  AgentInteractionTurn,
  WorldPlanDocumentEditProposalRequest,
  WorldPlanAgentContentBasisV1,
  WorldPlanAgentTurnRequestV1,
  WorldPlayAgentTurnRequestV1,
  WorldBuildAgentTurnRequestV1,
  WorldPlanAgentTurnResolvedSummary,
  WorldPlanActionProjection,
  WorldAgentConversationHistoryResponse,
  WorldAgentConversationHistoryResponseV3,
  WorldAgentConversationHistoryTurn,
  WorldAgentConversationHistoryTurnV1,
  WorldAgentNewConversationRequestV1,
  WorldCommandResolutionRequestV1,
  WorldCommandResolutionRecordV1,
  WorldPlanAgentPlanContextV2,
  WorldPlayGraphContextReceiptV1,
  WorldPlayGraphCompletionV1,
  WorldBuildKnowledgeContextV1,
  WorldBuildGraphReceiptV1,
  WorldBuildGraphCompletionV1,
  WorldBuildGraphAnswerStatus,
  WorldBuildSourceAnswerStatus,
  WorldBuildAuthoringCompletionV1,
  WorldBuildImagePreparationCompletionV1,
  WorldPlanSourceOpenTargetV2,
  WorldGraphSourceAnchorReadResponse,
  WorldGraphRecapContextReadResponseV2,
  WorldPlanGraphAnswerContextStatusV1,
  WorldPlanGraphAnswerSegmentV1,
  WorldPlanGraphCitationMapV1,
  WorldPlanGraphCitationMapV2,
  WorldPlanGraphCompletionV1,
  WorldPlanGraphCompletionV2,
  WorldPlanGraphContextReceiptV1,
  WorldPlanGraphExecutionProjectionV1,
  WorldPlanContextPolicyV1,
  WorldPlanSelectedPlayableTargetV1,
} from "../../api/types";
import { deferredComponent } from "../../ui/deferredComponent";

import { useAskPluginSlotOptional, useRegisterAskPluginPresence } from "../../agentInteraction/AskPluginSlot";
import { usePublishAgentSurfaceContext } from "../../agentInteraction/usePublishAgentSurfaceContext";
import { useAgentInteraction } from "../../agentInteraction/useAgentInteraction";
import { useWorldAgentConversationState } from "../../agentInteraction/WorldAgentConversation";
import { useSelectedWorld } from "../../selectedWorld/SelectedWorldContext";
import {
  admitWorldPlanEditProposal,
  type AdmittedWorldPlanEditProposal,
  type CapturedWorldPlanEditTarget,
  type ExpectedWorldPlanEditAgentBinding,
  type WorldPlanEditBridge,
  type WorldPlanEditContextualPreview,
  PlanEditGuardError,
  worldPlanSectionUnavailableReason,
} from "../agentEdit/planAgentEditProposal";
import { planSectionTargets, type PlanSectionTarget } from "../agentEdit/planSectionTarget";
import { WorldPlanAgentAnswer, type InlineAnswerCitation } from "./WorldPlanAgentAnswer";
import { BuddySourceProvenance, sourceCitationTitle } from "./BuddySourceProvenance";
import {
  AGENT_TURN_HISTORY_CAP,
  createAgentInteractionThread,
  listAgentThreads,
  loadAgentThreadById,
  threadStorageKey,
  threadTitleFromQuestion,
} from "./agentInteractionHistory";
import "./WorldPlanAgentConversation.css";
import "../../agentInteraction/WorldConversationPresentation.css";

const BUILD_SOURCE_REQUIRED_DESCRIPTION_ID = "world-plan-agent-build-source-required";

function focusBuildSourceSelector(): void {
  document.querySelector<HTMLSelectElement>("[data-testid='build-document-select']")?.focus({ preventScroll: false });
}

function openBuildSourceActions(): void {
  const actions = document.querySelector<HTMLDetailsElement>("details.build-source-actions");
  const summary = actions?.querySelector<HTMLElement>("summary");
  if (!actions || !summary) return;
  if (!actions.open) summary.click();
  summary.focus({ preventScroll: true });
}

function buildSourceRequiredMessage(): string {
  return "Buddy needs a saved source before you can ask about your lore. Choose one, or create/import a source in Build and save it there.";
}

const AgentTraceInspector = deferredComponent(() => import("../../agentInteraction/trace/AgentTraceInspector").then(module => ({ default: module.AgentTraceInspector })), "execution details");

export interface WorldPlanAgentConversationProps {
  /** The persistent App host stays mounted while Plan and Play routes change. */
  visible?: boolean;
  buildMode?: { savedSource: import("../../agentInteraction/WorldAgentConversation").SavedWorldBuildConversationContext | null; composeBridge?: import("../../buildSurface/buildComposeBridge").BuildComposeBridge | null } | null;
  playMode?: { admittedRun: import("../../agentInteraction/WorldAgentConversation").AdmittedWorldPlayConversationContext | null; sceneEditBridge?: import("../../playSurface/agentEdit/playSceneEditBridge").PlaySceneEditBridge | null } | null;
  presentationHosts?: PlanConversationPresentationHosts;
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
  editorSelectionActive?: boolean;
  playableTargetLabel?: string;
  playableEditTargetLabel?: string;
  onClearPlayableEditTarget?: () => void;
  onSavePlan?: () => void;
  savePlanEnabled?: boolean;
  imagePromptHost?: { unavailableReason: string | null; open: (prompt: string) => boolean };
}

interface ValidatedWorldPlanResponse {
  answer: string;
  trace: Record<string, unknown>;
  summary: WorldPlanAgentTurnResolvedSummary;
  conversationId: string | null;
  replayed: boolean;
  planReceiptBasis: WorldPlanGraphContextReceiptV1["plan_basis"] | null;
}

interface WorldPlanEditReview {
  captured: CapturedWorldPlanEditTarget;
  admitted: AdmittedWorldPlanEditProposal;
  expectedAgentBinding: ExpectedWorldPlanEditAgentBinding;
  threadId: string;
  turnId: string;
  fenceKey: string;
}

interface FrozenPlanEditReview {
  scopeKey: string;
  worldId: string;
  documentId: string;
  threadId: string;
  conversationId: string | null;
  targetLabel: string;
  preview: WorldPlanEditContextualPreview;
}

type WorldPlanEditReviewBefore =
  | { kind: "captured-text"; markdown: string; target?: { kind: string; id: string } }
  | { kind: "caret" };

interface SavedProposalClaim {
  claimId: string;
  text: string;
  sourceOpened: boolean;
  targets: WorldPlanSourceOpenTargetV2[];
}

interface SavedProposalGrounding {
  action: WorldPlanActionProjection;
  claims: SavedProposalClaim[];
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
const PENDING_PLAY_TURN_STORAGE_PREFIX = "dmb:world-play-pending-turn:v1:";

interface StoredPendingPlayTurn {
  storageKey: string;
  serialized: string;
  request: WorldPlayAgentTurnRequestV1 | WorldBuildAgentTurnRequestV1;
}

function pendingPlayTurnStorageKey(worldId: string): string {
  return `${PENDING_PLAY_TURN_STORAGE_PREFIX}${encodeURIComponent(worldId)}`;
}

function isSavedPlayGraphRequest(value: unknown, worldId: string): boolean {
  if (hasExactKeys(value, ["mode"]) && value.mode === "none") return true;
  return hasExactKeys(value, ["mode", "world_id", "campaign_id", "revision_pin", "focus"])
    && value.mode === "world" && value.world_id === worldId
    && value.campaign_id === null && value.revision_pin === null
    && hasExactKeys(value.focus, ["kind", "session_id", "campaign_id"])
    && value.focus.kind === "none" && value.focus.session_id === null
    && value.focus.campaign_id === null;
}

function matchesPlayGraphResponse(value: unknown, request: WorldPlayAgentTurnRequestV1 | WorldBuildAgentTurnRequestV1): boolean {
  if (!isRecord(value)) return false;
  if (request.graph_request.mode === "none") return hasExactKeys(value,["status","world_id","campaign_id","scope_mode","revision_id","focus","selection_node_id","selection_found","head_revision_id","is_head"])
    && value.status === "not_requested" && Object.entries(value).every(([key,item]) => key === "status" || item === null);
  return ["ready", "empty", "replayed"].includes(String(value.status))
    && typeof value.world_id === "string" && Boolean(value.world_id.trim())
    && (value.campaign_id === null || value.campaign_id === "")
    && value.scope_mode === "world"
    && typeof value.revision_id === "string" && Boolean(value.revision_id.trim())
    && isRecord(value.focus) && value.focus.kind === "none"
    && value.selection_node_id === null && value.selection_found === null;
}

function isSavedPlayContentBasis(value: unknown): boolean {
  return hasExactKeys(value, ["edition_revision", "edition_revision_id", "content_sha256"])
    && typeof value.edition_revision === "number" && Number.isSafeInteger(value.edition_revision) && value.edition_revision >= 0
    && (value.edition_revision === 0 ? value.edition_revision_id === null : commandUuid(value.edition_revision_id))
    && typeof value.content_sha256 === "string" && /^[0-9a-f]{64}$/.test(value.content_sha256);
}

function isStoredBuildDraftContext(value:unknown,request:Record<string,unknown>):boolean {
  if(!hasExactKeys(value,['snapshot','conversation_id','expected_pointer_revision'])||!commandUuid(value.conversation_id)
    ||!Number.isSafeInteger(value.expected_pointer_revision)||(value.expected_pointer_revision as number)<0)return false;
  const snapshot=value.snapshot;
  if(!hasExactKeys(snapshot,['schema','world_id','document_id','registry_revision','content_sha256','visibility',
    'draft_markdown','draft_sha256','editor_sha256','draft_generation'])||snapshot.schema!=='dmb_build_draft_snapshot_v1'
    ||!isRecord(request.owner_scope)||!isRecord(request.primary_work)||!isRecord(request.graph_request)
    ||request.graph_request.mode!=='world'||snapshot.world_id!==request.owner_scope.world_id
    ||snapshot.document_id!==request.primary_work.object_id||snapshot.registry_revision!==request.primary_work.expected_revision
    ||snapshot.content_sha256!==request.primary_work.expected_content_sha256
    ||!['internal','player_safe'].includes(String(snapshot.visibility))||typeof snapshot.draft_markdown!=='string'
    ||![snapshot.content_sha256,snapshot.draft_sha256,snapshot.editor_sha256].every(v=>typeof v==='string'&&/^[a-f0-9]{64}$/.test(v))
    ||!Number.isSafeInteger(snapshot.draft_generation)||(snapshot.draft_generation as number)<0)return false;
  const capability=request.build_write_capability;
  return capability===undefined||(isRecord(capability)&&isRecord(capability.basis)
    &&capability.conversation_id===value.conversation_id&&capability.expected_pointer_revision===value.expected_pointer_revision
    &&capability.draft_markdown===snapshot.draft_markdown&&capability.basis.draft_sha256===snapshot.draft_sha256
    &&capability.basis.editor_sha256===snapshot.editor_sha256&&capability.basis.draft_generation===snapshot.draft_generation);
}

function readPendingPlayTurn(worldId: string): StoredPendingPlayTurn | null {
  const storageKey = pendingPlayTurnStorageKey(worldId);
  const serialized = window.localStorage.getItem(storageKey);
  if (serialized === null) return null;
  const value: unknown = JSON.parse(serialized);
  if (!hasExactKeys(value, ["schema", "request"]) || value.schema !== "dmb_world_play_pending_turn_v1"
    || !hasExactKeys(value.request, ["schema", "client_thread_id", "turn_id", "surface", "owner_scope",
      "primary_work", "client_work_state", "graph_request", "graph_selection", "message",
      ...(isRecord(value.request) && isRecord(value.request.surface) && value.request.surface.surface_id === "play" ? ["play_target"] : []),
      ...(isRecord(value.request) && "build_write_capability" in value.request ? ["build_write_capability"] : []),
      ...(isRecord(value.request) && "build_draft_context" in value.request ? ["build_draft_context"] : [])])
    || value.request.schema !== "dmb_agent_turn_request_v1"
    || !commandUuid(value.request.client_thread_id) || !commandUuid(value.request.turn_id)
    || !hasExactKeys(value.request.surface, ["surface_id", "instance_id"])
    || !["play", "build"].includes(String(value.request.surface.surface_id)) || typeof value.request.surface.instance_id !== "string"
    || !value.request.surface.instance_id.trim()
    || !hasExactKeys(value.request.owner_scope, ["kind", "world_id"])
    || value.request.owner_scope.kind !== "world" || value.request.owner_scope.world_id !== worldId
    || !hasExactKeys(value.request.primary_work, value.request.surface.surface_id === "build"
      ? ["kind", "object_id", "expected_revision", "expected_content_sha256"] : ["kind", "object_id", "expected_revision", "play_content_basis"])
    || value.request.primary_work.kind !== (value.request.surface.surface_id === "build" ? "build" : "run") || typeof value.request.primary_work.object_id !== "string"
    || !value.request.primary_work.object_id.trim() || !isPositiveRevision(value.request.primary_work.expected_revision)
    || !["saved_clean", ...(value.request.surface.surface_id === "build" ? ["saved_dirty"] : [])].includes(String(value.request.client_work_state))
    || (value.request.surface.surface_id === "build" && (!isRecord(value.request.primary_work)
      || typeof value.request.primary_work.expected_content_sha256 !== "string"
      || !/^[0-9a-f]{64}$/.test(value.request.primary_work.expected_content_sha256)))
    || (value.request.surface.surface_id === "play" && (!isSavedPlayContentBasis(value.request.primary_work.play_content_basis) || !isRecord(value.request.graph_request) || !["none", "world"].includes(String(value.request.graph_request.mode))))
    || (value.request.surface.surface_id === "play" && isRecord(value.request.graph_request) && (!hasExactKeys(value.request.play_target, ["beat_id", "scene_id", "marker_grammar_version"])
      || typeof value.request.play_target.beat_id !== "string" || !/^beat:[a-z0-9][a-z0-9._-]{0,127}$/.test(value.request.play_target.beat_id)
      || !(value.request.play_target.scene_id === null || typeof value.request.play_target.scene_id === "string" && /^scene:[a-z0-9][a-z0-9._-]{0,127}$/.test(value.request.play_target.scene_id))
      || value.request.play_target.marker_grammar_version !== "v2"))
    || !isSavedPlayGraphRequest(value.request.graph_request, worldId)
    || ("build_draft_context" in value.request && (value.request.surface.surface_id!=="build"
      || !isStoredBuildDraftContext(value.request.build_draft_context,value.request)))
    || value.request.graph_selection !== null || typeof value.request.message !== "string"
    || !value.request.message.trim()) {
    throw new Error("The saved Play request is malformed. It was retained and cannot be retried automatically.");
  }
  return { storageKey, serialized, request: value.request as unknown as WorldPlayAgentTurnRequestV1 | WorldBuildAgentTurnRequestV1 };
}

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
  clientTurnId: string;
}

interface WorldPlanPendingNewConversation {
  schema: "dmb_world_pending_new_conversation_v1";
  worldId: string;
  documentId: string | null;
  request: WorldAgentNewConversationRequestV1;
}

interface SavedCommandResolution {
  schema: "dmb_world_saved_command_resolution_v1";
  worldId: string;
  documentId: string | null;
  originalKey: string;
  originalBytes: string;
  request: WorldCommandResolutionRequestV1;
}

function commandResolutionKey(envelope: WorldPlanPendingNewConversation): string {
  return `dmb:world-command-resolution:v1:${encodeURIComponent(envelope.worldId)}:${encodeURIComponent(envelope.documentId ?? "")}:${encodeURIComponent(envelope.request.command_id)}`;
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
      || value.worldId !== worldId || !(value.documentId === null || typeof value.documentId === "string")
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

/** Keep each displayed fact and source bound to one durable action and citation. */
function savedProposalGrounding(
  action: WorldPlanActionProjection,
  worldId: string,
  conversationId: string | null,
  pointerRevision: number | null,
): SavedProposalGrounding | null {
  const consultation = action.consultation;
  const result: unknown = consultation?.result;
  if (action.status !== "completed" || !consultation || !isRecord(result)
    || result.kind !== "proposal" || !conversationId || pointerRevision === null
    || action.basis.world_id !== worldId
    || consultation.receipt.origin_conversation_id !== conversationId
    || consultation.receipt.origin_pointer_revision !== pointerRevision) return null;
  const segments = result.answer_segments;
  const citationMap = result.citation_map;
  if (!Array.isArray(segments) || segments.length > 128
    || !segments.every((segment) => isRecord(segment)
      && (segment.kind === "graph_claim" || segment.kind === "connective"))) return null;
  const rawClaims = segments.filter((segment): segment is Record<string, unknown> =>
    isRecord(segment) && segment.kind === "graph_claim");
  if (citationMap === null && rawClaims.length === 0) return { action, claims: [] };
  if (!isRecord(citationMap) || citationMap.schema !== "dmb_graph_citation_map_v2"
    || !Array.isArray(citationMap.entries) || citationMap.entries.length !== rawClaims.length) return null;
  const citations = new Map<string, Record<string, unknown>>();
  for (const entry of citationMap.entries) {
    if (!isRecord(entry) || typeof entry.claim_id !== "string" || citations.has(entry.claim_id)
      || !Array.isArray(entry.evidence_ref_ids)
      || !entry.evidence_ref_ids.every((id) => typeof id === "string" && Boolean(id))
      || typeof entry.source_opened !== "boolean" || !Array.isArray(entry.source_read_ids)
      || !entry.source_read_ids.every((id) => typeof id === "string" && Boolean(id))
      || entry.source_opened !== (entry.source_read_ids.length > 0)) return null;
    citations.set(entry.claim_id, entry);
  }
  const targets = action.source_open_targets ?? [];
  if (!Array.isArray(targets) || targets.length > 64) return null;
  const claims: SavedProposalClaim[] = [];
  const seen = new Set<string>();
  for (const claim of rawClaims) {
    const claimId = claim.claim_id;
    if (typeof claimId !== "string" || !claimId || seen.has(claimId)
      || typeof claim.text !== "string" || !claim.text.trim()
      || !Array.isArray(claim.evidence_ref_ids)
      || !claim.evidence_ref_ids.every((id) => typeof id === "string" && Boolean(id))) return null;
    const citation = citations.get(claimId);
    if (!citation || citation.target_kind !== claim.target_kind || citation.target_id !== claim.target_id
      || citation.graph_revision !== claim.graph_revision
      || JSON.stringify(citation.evidence_ref_ids) !== JSON.stringify(claim.evidence_ref_ids)) return null;
    seen.add(claimId);
    claims.push({ claimId, text: claim.text, sourceOpened: citation.source_opened as boolean, targets: [] });
  }
  for (const target of targets) {
    if (!isRecord(target) || target.kind !== "evidence_anchor"
      || target.schema !== "dmb_agent_evidence_anchor_open_target_v1"
      || typeof target.claim_id !== "string" || typeof target.evidence_ref_id !== "string"
      || typeof target.anchor_id !== "string" || !target.anchor_id
      || typeof target.source_artifact_id !== "string" || !target.source_artifact_id
      || typeof target.source_revision_id !== "string" || !target.source_revision_id
      || !(target.source_name === null || (typeof target.source_name === "string" && target.source_name.trim()))
      || typeof target.native_world_id !== "string" || !target.native_world_id
      || target.managed_world_id !== worldId) return null;
    const citation = citations.get(target.claim_id);
    const claim = claims.find((item) => item.claimId === target.claim_id);
    if (!citation || !claim || target.graph_revision !== citation.graph_revision
      || !(citation.evidence_ref_ids as string[]).includes(target.evidence_ref_id)
      || (target.source_read_id !== null
        && !(citation.source_read_ids as string[]).includes(String(target.source_read_id)))) return null;
    claim.targets.push(target as WorldPlanSourceOpenTargetV2);
  }
  return { action, claims };
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

  if (!isSurfaceGraphInput({ graph_authority: value.graph_authority, graph_packet: value.graph_packet,
    assembled_input: value.assembled_input }, basis.world_id, 'dmb_plan_world_graph_packet_v1',
    ['plan', 'history', 'graph', 'instructions', 'tools', 'message'])) return false;

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
  receipt: WorldPlanGraphContextReceiptV1 | WorldBuildGraphReceiptV1,
): value is WorldPlanGraphCompletionV1 | WorldPlanGraphCompletionV2 | WorldBuildGraphCompletionV1 | import("../../api/types").SurfaceSourceCompletionV1 | import("../../api/types").SurfaceEvidenceCompletion {
  if (isRecord(value) && (value.schema === "dmb_surface_evidence_completion_v1" || value.schema === "dmb_surface_evidence_completion_v2" || value.schema === "dmb_surface_evidence_completion_v3"))
    return receipt.schema === "dmb_agent_plan_world_graph_context_receipt_v1" && isSurfaceEvidenceCompletion(value, receipt.context_receipt_sha256, "plan") && surfaceEvidenceReceiptBound(value,receipt);
  if (isRecord(value) && value.schema === "dmb_surface_source_completion_v1")
    return receipt.schema === "dmb_agent_plan_world_graph_context_receipt_v1" && isSurfaceSourceCompletion(value, receipt.context_receipt_sha256, "plan");

  const build = receipt.schema === "dmb_build_graph_context_receipt_v1";
  const version = build || (isRecord(value) && value.schema === "dmb_plan_world_graph_completion_v2") ? 2 : 1;
  if (!hasExactKeys(value, [
    "schema", "context_receipt_sha256", "answer_basis", "answer_context_status", "answer_segments", "citation_map",
  ])
    || value.schema !== (build ? "dmb_build_graph_completion_v1" : `dmb_plan_world_graph_completion_v${version}`)
    || value.context_receipt_sha256 !== receipt.context_receipt_sha256
    || !(build ? ["saved_source", "saved_source_plus_world_graph"] : ["committed_plan", "committed_plan_plus_world_graph", "committed_plan_plus_session_evidence", "committed_plan_plus_world_graph_plus_session_evidence"]).includes(String(value.answer_basis))
    || !["graph_grounded", "graph_grounded_partial", ...(build ? ["source_only_insufficient_evidence", "source_only_graph_unused"] : ["plan_only_insufficient_evidence", "plan_only_graph_unused"])]
      .includes(String(value.answer_context_status))
    || !Array.isArray(value.answer_segments)
    || value.answer_segments.length < 1 || value.answer_segments.length > 128) return false;

  const graphClaims: Extract<WorldPlanGraphAnswerSegmentV1, { kind: "graph_claim" }>[] = [];
  let hasSessionEvidence = false;
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
    } else if (segment.kind === "session_evidence_claim" && !build) {
      if (!hasExactKeys(segment, ["kind", "text", "run_id", "review_revision", "evidence_sha256"])
        || typeof segment.text !== "string" || !segment.text.trim() || segment.text.length > 4000
        || typeof segment.run_id !== "string" || !/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/.test(segment.run_id)
        || typeof segment.review_revision !== "number" || !Number.isSafeInteger(segment.review_revision) || segment.review_revision < 1
        || typeof segment.evidence_sha256 !== "string" || !/^[0-9a-f]{64}$/.test(segment.evidence_sha256)
        || !segment.text.includes("/play?" + new URLSearchParams({world: receipt.plan_basis.world_id, run: segment.run_id, evidence_revision: String(segment.review_revision)}).toString())) return false;
      hasSessionEvidence = true;
    } else if (segment.kind === "saved_source_claim" && build) {
      if (!hasExactKeys(segment, ["kind", "text", "content_sha256"])
        || typeof segment.text !== "string" || !segment.text.trim()
        || segment.content_sha256 !== receipt.source_basis.content_sha256) return false;
    } else if (segment.kind === "plan_claim" && !build) {
      if (!hasExactKeys(segment, ["kind", "text", "plan_content_sha256"])
        || typeof segment.text !== "string" || !segment.text.trim()
        || segment.plan_content_sha256 !== receipt.plan_basis.content_sha256) return false;
    } else if (segment.kind === "proposal" && !build) {
      if (!hasExactKeys(segment, ["kind", "text", "label"])
        || typeof segment.text !== "string" || !segment.text.trim() || !["invented_idea", "image_prompt"].includes(String(segment.label))) return false;
    } else if (segment.kind === "connective") {
      if (!hasExactKeys(segment, ["kind", "text"]) || typeof segment.text !== "string" || !segment.text.trim()) return false;
    } else return false;
  }
  if (new Set(graphClaims.map((claim) => claim.claim_id)).size !== graphClaims.length) return false;

  const sourceBasis = build ? "saved_source" : "committed_plan";
  const graphBasis = build ? "saved_source_plus_world_graph" : "committed_plan_plus_world_graph";
  const expectedBasis = (graphClaims.length > 0 ? graphBasis : sourceBasis) + (hasSessionEvidence ? "_plus_session_evidence" : "");
  if (value.answer_basis !== expectedBasis) return false;

  const citationMap = value.citation_map;
  if (citationMap === null) {
    if (graphClaims.length > 0) return false;
  } else {
    if (!hasExactKeys(citationMap, ["schema", "context_receipt_sha256", "entries"])
      || citationMap.schema !== `dmb_graph_citation_map_v${version}`
      || citationMap.context_receipt_sha256 !== receipt.context_receipt_sha256
      || !Array.isArray(citationMap.entries)
      || citationMap.entries.length > 128
      || citationMap.entries.length !== graphClaims.length) return false;
    const entriesByClaimId = new Map<string, (WorldPlanGraphCitationMapV1 | WorldPlanGraphCitationMapV2)["entries"][number]>();
    for (const entry of citationMap.entries) {
      const readIds = isRecord(entry) ? entry.source_read_ids : undefined;
      if (!hasExactKeys(entry, ["claim_id", "target_kind", "target_id", "graph_revision", "evidence_ref_ids", "source_opened", ...(version === 2 ? ["source_read_ids"] : [])])
        || typeof entry.claim_id !== "string" || !entry.claim_id.trim()
        || !["assertion", "relationship"].includes(String(entry.target_kind))
        || typeof entry.target_id !== "string" || !entry.target_id.trim()
        || entry.graph_revision !== receipt.graph_authority.graph_revision
        || !isNonEmptyStringList(entry.evidence_ref_ids) || entry.evidence_ref_ids.length > 64
        || (version === 1 && entry.source_opened !== false)
        || (version === 2 && (
          typeof entry.source_opened !== "boolean"
          || !Array.isArray(readIds)
          || readIds.length > 16_384
          || readIds.some((id: unknown) => typeof id !== "string" || !id.trim() || id !== id.trim())
          || readIds.some((id: string, index: number) => index > 0 && id <= readIds[index - 1])
          || entry.source_opened !== (readIds.length > 0)
        ))
        || entriesByClaimId.has(entry.claim_id)) return false;
      entriesByClaimId.set(entry.claim_id, entry as unknown as (WorldPlanGraphCitationMapV1 | WorldPlanGraphCitationMapV2)["entries"][number]);
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

  const status = value.answer_context_status as WorldPlanGraphAnswerContextStatusV1 | WorldBuildGraphAnswerStatus;
  if (status === (build ? "source_only_insufficient_evidence" : "plan_only_insufficient_evidence")) {
    // Build's controller may select source-only final evidence after sufficient
    // initial discovery. The initial packet is not the final writer exposure.
    return (build || (receipt.graph_packet.evidence_sufficiency_status === "insufficient"
      && receipt.assembled_input.packet_disposition === "omitted_insufficient"))
      && graphClaims.length === 0 && citationMap === null
      && value.answer_basis === expectedBasis;
  }
  if (status === (build ? "source_only_graph_unused" : "plan_only_graph_unused")) {
    return graphClaims.length === 0 && citationMap === null && value.answer_basis === expectedBasis;
  }
  return graphClaims.length > 0 && citationMap !== null && value.answer_basis === expectedBasis;
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

function isWorldPlanSourceOpenTargets(
  value: unknown,
  receipt: WorldPlanGraphContextReceiptV1 | WorldBuildGraphReceiptV1,
  completion: WorldPlanGraphCompletionV1 | WorldPlanGraphCompletionV2 | WorldBuildGraphCompletionV1 | import("../../api/types").SurfaceSourceCompletionV1 | import("../../api/types").SurfaceEvidenceCompletion | null,
): value is WorldPlanSourceOpenTargetV2[] {
  if (!Array.isArray(value) || value.length > 64) return false;
  const citations = completion?.citation_map?.entries ?? [];
  const byClaim = new Map(citations.map((citation) => [citation.claim_id, citation]));
  const seen = new Set<string>();
  const perClaim = new Map<string, number>();
  for (const target of value) {
    if (!isRecord(target)) return false;
    const evidence = target.kind === "evidence_anchor";
    if (!evidence && target.kind !== "related_recap_context") return false;
    const common = ["schema", "kind", "claim_id", "source_artifact_id", "source_revision_id", "source_name", "managed_world_id",
      "native_world_id", "binding_version", "scope_mode", "campaign_id", "focus", "admissibility", "graph_revision"];
    const variant = evidence
      ? ["anchor_id", "evidence_ref_id", "source_read_id", "read_outcome"]
      : ["context_anchor_id", "provenance_evidence_ref_id", "source_campaign_id", "source_uri", "content_sha256", "expected_session_id",
        "canonical_heading", "legacy_session_heading", "legacy_recap_marker", "selector_schema", "selector_policy"];
    if (!hasExactKeys(target, [...common, ...variant])
      || target.schema !== (evidence ? "dmb_agent_evidence_anchor_open_target_v1" : "dmb_agent_related_recap_context_open_target_v2")
      || typeof target.claim_id !== "string" || !target.claim_id
      || typeof target.source_artifact_id !== "string" || !target.source_artifact_id
      || typeof target.source_revision_id !== "string" || !target.source_revision_id
      || !(target.source_name === null || (typeof target.source_name === "string" && target.source_name.trim()))
      || target.managed_world_id !== (receipt.schema === "dmb_build_graph_context_receipt_v1" ? receipt.source_basis.world_id : receipt.plan_basis.world_id)
      || target.managed_world_id !== receipt.graph_authority.managed_world_id
      || target.native_world_id !== receipt.graph_authority.native_world_id
      || target.binding_version !== receipt.graph_authority.binding_version
      || target.scope_mode !== "world" || target.campaign_id !== null
      || !hasExactKeys(target.focus, ["kind", "session_id", "campaign_id"])
      || target.focus.kind !== "none" || target.focus.session_id !== null || target.focus.campaign_id !== null
      || target.admissibility !== "gm" || target.graph_revision !== receipt.graph_authority.graph_revision) return false;
    const citation = byClaim.get(target.claim_id);
    const evidenceId = evidence ? target.evidence_ref_id : target.provenance_evidence_ref_id;
    if (!citation || !citation.evidence_ref_ids.includes(String(evidenceId))
      || citation.graph_revision !== target.graph_revision) return false;
    if (evidence) {
      if (typeof target.anchor_id !== "string" || !target.anchor_id
        || typeof evidenceId !== "string" || !evidenceId
        || !(target.source_read_id === null || (typeof target.source_read_id === "string" && target.source_read_id))
        || !(target.read_outcome === null || ["enough", "partial", "truncated"].includes(String(target.read_outcome)))
        || (target.source_read_id === null) !== (target.read_outcome === null)
        || (target.source_read_id !== null && !("source_read_ids" in citation && citation.source_read_ids.includes(target.source_read_id)))) return false;
    } else if (typeof target.context_anchor_id !== "string" || !target.context_anchor_id.startsWith("dm-context-anchor:v2:")
      || !(target.source_campaign_id === null || (typeof target.source_campaign_id === "string" && target.source_campaign_id.trim()))
      || typeof target.source_uri !== "string" || !target.source_uri.startsWith("repo://")
      || typeof target.content_sha256 !== "string" || !/^[0-9a-f]{64}$/.test(target.content_sha256)
      || typeof target.expected_session_id !== "string" || !/^session-[1-9][0-9]*$/.test(target.expected_session_id)
      || target.canonical_heading !== `# Session ${target.expected_session_id.slice(8)} Recap`
      || target.legacy_session_heading !== `## Session ${target.expected_session_id.slice(8)}:`
      || target.legacy_recap_marker !== "**Recap**:"
      || target.selector_schema !== "dm_recap_context_section_selector_v2"
      || target.selector_policy !== "markdown-session-recap-v2") return false;
    const identity = `${target.kind}\u001f${target.claim_id}\u001f${evidence ? target.anchor_id : target.context_anchor_id}`;
    if (seen.has(identity)) return false;
    const count = (perClaim.get(target.claim_id) ?? 0) + 1;
    if (count > 64) return false;
    perClaim.set(target.claim_id, count);
    seen.add(identity);
  }
  return true;
}

function isWorldPlanRelatedRecapStatuses(
  value: unknown,
  completion: WorldPlanGraphCompletionV1 | WorldPlanGraphCompletionV2 | WorldBuildGraphCompletionV1 | import("../../api/types").SurfaceSourceCompletionV1 | import("../../api/types").SurfaceEvidenceCompletion | null,
): boolean {
  if (!Array.isArray(value) || value.length > 128) return false;
  const claims = new Set((completion?.citation_map?.entries ?? []).map((entry) => entry.claim_id));
  const seen = new Set<string>();
  for (const row of value) {
    if (!hasExactKeys(row, ["schema", "claim_id", "status", "choice_count"])
      || row.schema !== "dmb_agent_related_recap_context_status_v2"
      || typeof row.claim_id !== "string" || !claims.has(row.claim_id) || seen.has(row.claim_id)
      || !Number.isSafeInteger(row.choice_count) || (row.choice_count as number) < 0 || (row.choice_count as number) > 512
      || !(row.status === "available" ? row.choice_count === 1
        : row.status === "multiple_choices" ? (row.choice_count as number) > 1
          : row.status === "partial" ? (row.choice_count as number) > 0
            : row.status === "metadata_unavailable" ? (row.choice_count as number) >= 0
              : ["no_context", "overflow"].includes(String(row.status)) && row.choice_count === 0)) return false;
    seen.add(row.claim_id);
  }
  return true;
}

function isWorldPlanEvidenceAnchorStatuses(
  value: unknown,
  completion: WorldPlanGraphCompletionV1 | WorldPlanGraphCompletionV2 | WorldBuildGraphCompletionV1 | import("../../api/types").SurfaceSourceCompletionV1 | import("../../api/types").SurfaceEvidenceCompletion | null,
): boolean {
  if (!Array.isArray(value) || value.length > 128) return false;
  const claims = new Set((completion?.citation_map?.entries ?? []).map((entry) => entry.claim_id));
  const seen = new Set<string>();
  for (const row of value) {
    if (!hasExactKeys(row, ["schema", "claim_id", "status", "target_count"])
      || row.schema !== "dmb_agent_evidence_anchor_status_v1"
      || typeof row.claim_id !== "string" || !claims.has(row.claim_id) || seen.has(row.claim_id)
      || !Number.isSafeInteger(row.target_count) || (row.target_count as number) < 0 || (row.target_count as number) > 64
      || !(["available", "partial"].includes(String(row.status))
        ? (row.target_count as number) > 0
        : ["no_anchor", "overflow"].includes(String(row.status)) && row.target_count === 0)) return false;
    seen.add(row.claim_id);
  }
  return true;
}

function isWorldPlanContextProjection(
  value: unknown,
  request?: WorldPlanAgentTurnRequestV1,
  historyTurn = false,
): value is WorldPlanAgentPlanContextV2 {
  const required = ["schema", "receipt", "completion", "execution"];
  if (isRecord(value) && Object.prototype.hasOwnProperty.call(value, "source_open_targets")) required.push("source_open_targets");
  if (isRecord(value) && Object.prototype.hasOwnProperty.call(value, "evidence_anchor_statuses")) required.push("evidence_anchor_statuses");
  if (isRecord(value) && Object.prototype.hasOwnProperty.call(value, "related_recap_context_statuses")) required.push("related_recap_context_statuses");
  const allowed = historyTurn && isRecord(value) && !Object.prototype.hasOwnProperty.call(value, "delivery_replay")
    ? required
    : [...required, "delivery_replay"];
  if (!hasExactKeys(value, allowed)
    || value.schema !== "dmb_agent_plan_world_graph_context_response_v2"
    || !isWorldPlanGraphReceipt(value.receipt, request)
    || (value.completion !== null && !isWorldPlanGraphCompletion(value.completion, value.receipt))
    || (Object.prototype.hasOwnProperty.call(value, "source_open_targets")
      && !isWorldPlanSourceOpenTargets(value.source_open_targets, value.receipt, value.completion))
    || (Object.prototype.hasOwnProperty.call(value, "evidence_anchor_statuses")
      && !isWorldPlanEvidenceAnchorStatuses(value.evidence_anchor_statuses, value.completion))
    || (Object.prototype.hasOwnProperty.call(value, "related_recap_context_statuses")
      && !isWorldPlanRelatedRecapStatuses(value.related_recap_context_statuses, value.completion))
    || (value.execution !== null && !isWorldPlanGraphExecution(value.execution))
    || (Object.prototype.hasOwnProperty.call(value, "delivery_replay") && typeof value.delivery_replay !== "boolean")) return false;
  if (!historyTurn && (!Object.prototype.hasOwnProperty.call(value, "delivery_replay")
    || value.completion === null)) return false;
  return true;
}

function isRulesUnclaimedContext(value: unknown, worldId: string,
  request?: WorldPlanAgentTurnRequestV1 | WorldPlayAgentTurnRequestV1 | WorldBuildAgentTurnRequestV1,
  provenance?: unknown): value is RulesUnclaimedContext {
  if (!hasExactKeys(value, ['schema', 'receipt', 'execution', 'delivery_replay'])
    || value.schema !== 'dmb_agent_rules_unclaimed_context_v1' || typeof value.delivery_replay !== 'boolean'
    || !isWorldPlanGraphExecution(value.execution) || value.execution.claimability !== 'completed'
    || value.execution.authorization_state !== 'response_received' || !isRecord(value.receipt)) return false;
  const receipt = value.receipt;
  if (receipt.schema === 'dmb_play_world_graph_context_receipt_v1') {
    if (request && request.primary_work.kind !== 'run') return false;
    return isWorldPlayGraphReceipt(receipt, request as WorldPlayAgentTurnRequestV1 | undefined)
      && receipt.play_basis.world_id === worldId
      && (provenance === undefined || isPlayContextProvenanceBound(receipt, provenance, worldId));
  }
  if (receipt.schema === 'dmb_agent_plan_world_graph_context_receipt_v1') {
    if (request && request.primary_work.kind !== 'plan') return false;
    return isWorldPlanGraphReceipt(receipt, request as WorldPlanAgentTurnRequestV1 | undefined)
      && receipt.plan_basis.world_id === worldId
      && (provenance === undefined || isHistoryPlanReceiptBound(receipt, provenance, worldId));
  }
  if (request && request.primary_work.kind !== 'build') return false;
  return isBuildGraphReceipt(receipt, worldId)
    && (request === undefined || receipt.source_basis.document_id === request.primary_work.object_id
      && receipt.source_basis.registry_revision === request.primary_work.expected_revision
      && receipt.source_basis.content_sha256 === (request as WorldBuildAgentTurnRequestV1).primary_work.expected_content_sha256)
    && (provenance === undefined || isRecord(provenance) && isHistoryBuildReceiptBound(receipt, provenance, worldId));
}

function rulesContextForTurn(turn: WorldAgentConversationHistoryTurn): RulesAnswerContext | undefined {
  return 'schema' in turn && (turn.schema === 'dmb_agent_conversation_history_mixed_turn_v1' || turn.schema === 'dmb_agent_conversation_history_play_rules_turn_v1') ? turn.rules_context : undefined;
}
function graphContextForTurn(turn: WorldAgentConversationHistoryTurn) {
  if (rulesContextForTurn(turn)) return rulesContextForTurn(turn)!.base_context ?? undefined;
  return turn.knowledge_context ?? ("play_context" in turn ? turn.play_context : "plan_context" in turn ? turn.plan_context : undefined);
}

function isBuildAuthoringCompletion(value: unknown, receiptHash: string): value is WorldBuildAuthoringCompletionV1 {
  return isRecord(value) && hasExactKeys(value, ["schema", "context_receipt_sha256", "answer_basis", "answer_context_status",
    "answer_segments", "citation_map", "action_id", "reservation_sha256", "proposal_result_sha256", "provider_attempt_id", "envelope_sha256"])
    && value.schema === "dmb_build_authoring_completion_v1" && value.context_receipt_sha256 === receiptHash
    && value.answer_basis === "prepared_page_proposal" && value.answer_context_status === "proposal_ready"
    && value.citation_map === null && Array.isArray(value.answer_segments) && value.answer_segments.length === 1
    && isRecord(value.answer_segments[0]) && hasExactKeys(value.answer_segments[0], ["kind", "text"])
    && value.answer_segments[0].kind === "connective"
    && value.answer_segments[0].text === "A preview is ready. Review it before inserting it into the page. Nothing has been saved or published."
    && [value.action_id, value.provider_attempt_id].every(id => typeof id === "string" && /^[a-f0-9]{8}-(?:[a-f0-9]{4}-){3}[a-f0-9]{12}$/i.test(id))
    && [value.reservation_sha256, value.proposal_result_sha256, value.envelope_sha256].every(hash => typeof hash === "string" && /^[a-f0-9]{64}$/.test(hash));
}

function isBuildImageCompletion(value: unknown, receiptHash: string): value is WorldBuildImagePreparationCompletionV1 {
  return isRecord(value) && hasExactKeys(value, ["schema", "context_receipt_sha256", "answer_basis", "answer_context_status",
    "answer_segments", "citation_map", "action_id", "reservation_sha256", "preparation_result_sha256", "provider_attempt_id", "envelope_sha256"])
    && value.schema === "dmb_build_image_preparation_completion_v1" && value.context_receipt_sha256 === receiptHash
    && value.answer_basis === "prepared_image_direction" && value.answer_context_status === "image_preparation_ready"
    && value.citation_map === null && Array.isArray(value.answer_segments) && value.answer_segments.length === 1
    && isRecord(value.answer_segments[0]) && hasExactKeys(value.answer_segments[0], ["kind", "text"])
    && value.answer_segments[0].kind === "connective"
    && value.answer_segments[0].text === "Your image prompt is ready in Image Studio. Review it before generating. Nothing has been generated, inserted or saved."
    && [value.action_id, value.provider_attempt_id].every(id => typeof id === "string" && /^[a-f0-9]{8}-(?:[a-f0-9]{4}-){3}[a-f0-9]{12}$/i.test(id))
    && [value.reservation_sha256, value.preparation_result_sha256, value.envelope_sha256].every(hash => typeof hash === "string" && /^[a-f0-9]{64}$/.test(hash));
}

function isBuildGraphReceipt(value: unknown, worldId: string): value is WorldBuildGraphReceiptV1 {
  if (!hasExactKeys(value, ['schema', 'receipt_serializer_version', 'context_receipt_sha256', 'source_basis', 'graph_authority', 'graph_packet', 'assembled_input', 'evidence_mode', 'source_opened'])
    || value.schema !== 'dmb_build_graph_context_receipt_v1' || value.receipt_serializer_version !== 'canonical-json-utf8-v1'
    || !isDigest(value.context_receipt_sha256) || !isRecord(value.source_basis) || !isRecord(value.graph_authority)
    || value.evidence_mode !== 'metadata_only' || value.source_opened !== false) return false;
  const source = value.source_basis;
  const authority = value.graph_authority;
  if (!hasExactKeys(source, ["world_id", "document_id", "registry_revision", "content_sha256", "visibility"])
    || source.world_id !== worldId || typeof source.document_id !== "string" || !source.document_id
    || !isPositiveRevision(source.registry_revision) || typeof source.content_sha256 !== "string"
    || !/^[0-9a-f]{64}$/.test(source.content_sha256) || !["internal", "player_safe"].includes(String(source.visibility))
    || authority.managed_world_id !== worldId || typeof authority.native_world_id !== "string" || !authority.native_world_id
    || !isPositiveRevision(authority.binding_version) || authority.scope_mode !== "world" || authority.campaign_id !== null
    || typeof authority.graph_revision !== "string" || !authority.graph_revision
    || authority.admissibility_version !== "gm-v1") return false;
  return isSurfaceGraphInput({ graph_authority: value.graph_authority, graph_packet: value.graph_packet,
    assembled_input: value.assembled_input }, worldId, 'dmb_plan_world_graph_packet_v1',
    ['plan', 'history', 'graph', 'instructions', 'tools', 'message']);
}

function isBuildKnowledgeContext(value: unknown, worldId: string): value is WorldBuildKnowledgeContextV1 {
  const required = ["saved_source_name", "schema", "receipt", "completion", "execution", "delivery_replay", "source_open_targets", "evidence_anchor_statuses", "related_recap_context_statuses"];
  if (isRecord(value) && Object.prototype.hasOwnProperty.call(value, "saved_source_sections")) required.push("saved_source_sections");
  if (!hasExactKeys(value, required)
    || !(value.saved_source_name === null || (typeof value.saved_source_name === "string" && !!value.saved_source_name.trim()))
    || value.schema !== "dmb_build_graph_context_response_v1" || !isRecord(value.receipt)
    || value.receipt.schema !== "dmb_build_graph_context_receipt_v1"
    || !isRecord(value.receipt.source_basis) || !isRecord(value.receipt.graph_authority)
    || !isRecord(value.receipt.graph_packet) || !isRecord(value.receipt.assembled_input)
    || typeof value.receipt.context_receipt_sha256 !== "string" || !/^[0-9a-f]{64}$/.test(value.receipt.context_receipt_sha256)
    || typeof value.delivery_replay !== "boolean") return false;
  const source = value.receipt.source_basis;
  const authority = value.receipt.graph_authority;
  if (!hasExactKeys(source, ["world_id", "document_id", "registry_revision", "content_sha256", "visibility"])
    || source.world_id !== worldId || typeof source.document_id !== "string" || !source.document_id
    || !isPositiveRevision(source.registry_revision) || typeof source.content_sha256 !== "string"
    || !/^[0-9a-f]{64}$/.test(source.content_sha256) || !["internal", "player_safe"].includes(String(source.visibility))
    || authority.managed_world_id !== worldId || typeof authority.native_world_id !== "string" || !authority.native_world_id
    || !isPositiveRevision(authority.binding_version) || authority.scope_mode !== "world" || authority.campaign_id !== null
    || typeof authority.graph_revision !== "string" || !authority.graph_revision
    || authority.admissibility_version !== "gm-v1") return false;
  const receipt = value.receipt as unknown as WorldBuildGraphReceiptV1;
  if (Object.prototype.hasOwnProperty.call(value, "saved_source_sections")
    && !isSavedSectionTargets(value.saved_source_sections, receipt.source_basis, value.completion)) return false;
  if (isRecord(value.completion) && value.completion.schema === "dmb_build_image_preparation_completion_v1") {
    return isBuildImageCompletion(value.completion, receipt.context_receipt_sha256)
      && (value.execution === null || isWorldPlanGraphExecution(value.execution))
      && [value.source_open_targets, value.evidence_anchor_statuses, value.related_recap_context_statuses]
        .every(items => Array.isArray(items) && items.length === 0);
  }
  if (isRecord(value.completion) && value.completion.schema === "dmb_build_authoring_completion_v1") {
    return isBuildAuthoringCompletion(value.completion, receipt.context_receipt_sha256)
      && (value.execution === null || isWorldPlanGraphExecution(value.execution))
      && [value.source_open_targets, value.evidence_anchor_statuses, value.related_recap_context_statuses]
        .every(items => Array.isArray(items) && items.length === 0);
  }
  if (isRecord(value.completion) && ["dmb_build_graph_completion_v2", "dmb_build_graph_completion_v3", "dmb_build_draft_context_completion_v1", "dmb_build_related_page_completion_v1"].includes(String(value.completion.schema))) {
    return isBuildSourceCompletion(value.completion, receipt.context_receipt_sha256, source.content_sha256, source.world_id)
      && (value.execution === null || isWorldPlanGraphExecution(value.execution))
      && [value.source_open_targets, value.evidence_anchor_statuses, value.related_recap_context_statuses]
        .every(items => Array.isArray(items) && items.length === 0);
  }
  if ((value.completion !== null && !isWorldPlanGraphCompletion(value.completion, receipt))
    || (value.execution !== null && !isWorldPlanGraphExecution(value.execution))) return false;
  const completion = value.completion as WorldBuildGraphCompletionV1 | null;
  return isWorldPlanSourceOpenTargets(value.source_open_targets, receipt, completion)
    && isWorldPlanEvidenceAnchorStatuses(value.evidence_anchor_statuses, completion)
    && isWorldPlanRelatedRecapStatuses(value.related_recap_context_statuses, completion);
}

function isHistoryBuildReceiptBound(receipt: WorldBuildGraphReceiptV1, provenance: Record<string, unknown>, worldId: string): boolean {
  if (!isRecord(provenance.primary_work) || !Array.isArray(provenance.supporting_work)) return false;
  const source = receipt.source_basis;
  const authority = receipt.graph_authority;
  const ref = provenance.primary_work;
  const bindings: [string, string, string][] = [
    ["dmb_build_source_visibility_v1", source.visibility, "1"],
    ["dmb_build_graph_binding_v1", authority.native_world_id, String(authority.binding_version)],
    ["world_graph_revision", authority.native_world_id, authority.graph_revision],
  ];
  return provenance.world_id === worldId && provenance.surface_id === "build" && provenance.surface_resolution === "resolved"
    && ref.resolution === "resolved" && ref.kind === "build" && ref.object_id === source.document_id
    && ref.revision === String(source.registry_revision) && ref.content_sha256 === source.content_sha256
    && ref.object_revision === null && ref.work_revision_id === null && ref.revision_n === null
    && bindings.every(([kind, objectId, revision]) => {
      const matches = (provenance.supporting_work as unknown[]).filter(item => isRecord(item) && item.kind === kind);
      return matches.length === 1 && isRecord(matches[0]) && matches[0].resolution === "resolved"
        && matches[0].object_id === objectId && matches[0].revision === revision;
    });
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
  schema: "dmb_agent_conversation_history_v1" | "dmb_agent_conversation_history_v2" | "dmb_agent_conversation_history_v3" | "dmb_agent_conversation_history_v4",
  worldId: string,
): boolean {
  if (!isRecord(value)) return false;
  if (schema === 'dmb_agent_conversation_history_v4') {
    if (value.schema === 'dmb_agent_conversation_history_play_source_turn_v1') {
      if (!hasExactKeys(value,['schema','turn_id','sequence','lifecycle_status','user_text','assistant_text','provenance','idempotency_key','play_source_context'])
        || !isPlaySourceProvenanceBound(value.play_source_context,value.provenance,worldId)) return false;
      const { schema: _schema, play_source_context: _source, ...envelope } = value;
      return isHistoryTurn(envelope,'dmb_agent_conversation_history_v3',worldId);
    }
    if ((value.schema === 'dmb_agent_conversation_history_mixed_turn_v1' || value.schema === 'dmb_agent_conversation_history_play_rules_turn_v1')) {
      const playRules = value.schema === 'dmb_agent_conversation_history_play_rules_turn_v1';
      if (!hasExactKeys(value, ['schema','turn_id','sequence','lifecycle_status','user_text','assistant_text','provenance','idempotency_key','rules_context',...(playRules ? ['play_source_context'] : [])])
        || value.lifecycle_status !== 'completed') return false;
      // Reuse only envelope field/provenance validation, never reinterpret mixed answer authority.
      const { schema: _schema, rules_context: _rules, play_source_context: _source, ...envelope } = value;
      if (playRules && (!isPlaySourceProvenanceBound(_source,value.provenance,worldId)
        || !isRecord(_rules) || !isRecord(_rules.accepted_binding) || _rules.accepted_binding.base_disposition !== 'absent')) return false;
      if (!isHistoryTurn(envelope, 'dmb_agent_conversation_history_v3', worldId)) return false;
      return isRulesAnswerContext(value.rules_context, value.assistant_text, worldId, base =>
        isRecord(base) && (base.schema === 'dmb_build_graph_context_response_v1'
          ? isBuildKnowledgeContext(base, worldId) && isHistoryBuildReceiptBound(base.receipt, value.provenance as Record<string, unknown>, worldId)
          : base.schema === 'dmb_agent_play_world_graph_context_response_v1'
            ? isWorldPlayContextProjection(base, isWorldPlanGraphExecution, undefined, true) && isPlayContextProvenanceBound(base.receipt, value.provenance, worldId)
            : isWorldPlanContextProjection(base, undefined, true) && isHistoryPlanReceiptBound(base.receipt, value.provenance, worldId)),
        { turnId: value.turn_id as string },
        c => isRulesUnclaimedContext(c, worldId, undefined, value.provenance));
    }
    if (Object.hasOwn(value, 'schema')) return false;
    return isHistoryTurn(value, Object.hasOwn(value, 'idempotency_key') ? 'dmb_agent_conversation_history_v3'
      : Object.hasOwn(value, 'plan_context') || Object.hasOwn(value, 'play_context') || Object.hasOwn(value, 'knowledge_context') ? 'dmb_agent_conversation_history_v2' : 'dmb_agent_conversation_history_v1', worldId);
  }
  const hasPlanContext = Object.prototype.hasOwnProperty.call(value, "plan_context");
  const hasBuildContext = Object.prototype.hasOwnProperty.call(value, "knowledge_context");
  const hasPlayContext = Object.prototype.hasOwnProperty.call(value, "play_context");
  if ([hasPlanContext, hasBuildContext, hasPlayContext].filter(Boolean).length > 1) return false;
  const keys = ["turn_id", "sequence", "lifecycle_status", "user_text", "assistant_text", "provenance"];
  if (schema === "dmb_agent_conversation_history_v2" && hasPlanContext) keys.push("plan_context");
  if (schema === "dmb_agent_conversation_history_v3") {
    keys.push("idempotency_key");
    if (hasPlanContext) keys.push("plan_context");
  }
  if (hasBuildContext && schema !== "dmb_agent_conversation_history_v1") keys.push("knowledge_context");
  if (hasPlayContext && schema !== "dmb_agent_conversation_history_v1") keys.push("play_context");
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
  if (hasPlayContext) {
    if (schema === "dmb_agent_conversation_history_v1" || !isWorldPlayContextProjection(value.play_context, isWorldPlanGraphExecution, undefined, true)
      || !isPlayContextProvenanceBound(value.play_context.receipt, provenance, worldId)) return false;
    const completion = value.play_context.completion;
    return value.lifecycle_status === "completed"
      ? completion !== null && value.assistant_text === completion.answer_segments.map(segment => segment.text).join("\n")
      : completion === null;
  }
  if (hasBuildContext) {
    if (schema === "dmb_agent_conversation_history_v1" || !isBuildKnowledgeContext(value.knowledge_context, worldId)
      || !isHistoryBuildReceiptBound(value.knowledge_context.receipt, provenance, worldId)) return false;
    const completion = value.knowledge_context.completion;
    return value.lifecycle_status === "completed"
      ? completion !== null && value.assistant_text === completion.answer_segments.map(segment => segment.text).join("\n")
      : completion === null;
  }
  if (!hasPlanContext) return true;
  if (schema === "dmb_agent_conversation_history_v1") return false;
  if (!isWorldPlanContextProjection(value.plan_context, undefined, true)
    || !isHistoryPlanReceiptBound(value.plan_context.receipt, provenance, worldId)) return false;
  const hasCompletion = value.plan_context.completion !== null;
  return value.lifecycle_status === "completed" ? hasCompletion : !hasCompletion;
}

function isHistoryPlanReceiptBound(value: unknown, provenance: unknown, worldId: string): boolean {
  if (!isRecord(value) || !isRecord(value.plan_basis)
    || !isRecord(provenance) || !isRecord(provenance.primary_work)) return false;
  const basis = value.plan_basis;
  const primary = provenance.primary_work;
  const target = value.playable_target;
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
    && schema !== "dmb_agent_conversation_history_v3"
    && schema !== "dmb_agent_conversation_history_v4") return false;
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
    if ((turn.schema === 'dmb_agent_conversation_history_mixed_turn_v1' || turn.schema === 'dmb_agent_conversation_history_play_rules_turn_v1')
      && (!isRecord(turn.rules_context) || !isRecord(turn.rules_context.accepted_binding)
        || turn.rules_context.accepted_binding.conversation_id !== value.conversation_id)) return false;
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

export async function commandCanonicalDigest(value: unknown): Promise<string> {
  const bytes = canonicalJson(value).replace(/[\u007f-\uffff]/g,
    (character) => `\\u${character.charCodeAt(0).toString(16).padStart(4, "0")}`);
  const digest = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(bytes));
  return Array.from(new Uint8Array(digest), (byte) => byte.toString(16).padStart(2, "0")).join("");
}

async function textSha256(value: string): Promise<string> {
  const digest = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(value));
  return Array.from(new Uint8Array(digest), (byte) => byte.toString(16).padStart(2, "0")).join("");
}

export async function newConversationRequestFingerprint(worldId: string, request: WorldAgentNewConversationRequestV1): Promise<string> {
  return commandCanonicalDigest({ world_id: worldId, expected_pointer_revision: request.expected_pointer_revision,
    expected_active_conversation_id: request.expected_active_conversation_id });
}

function commandUuid(value: unknown): value is string {
  return typeof value === "string" && /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(value);
}

export async function verifiedCommandResolution(value: unknown, request: WorldCommandResolutionRequestV1): Promise<WorldCommandResolutionRecordV1 | null> {
  if (!hasExactKeys(value, ["schema", "status", "record"]) || value.schema !== "dmb_agent_new_conversation_resolution_response_v1"
    || value.status !== "terminal") return null;
  const record = value.record;
  if (!hasExactKeys(record, ["schema", "request", "original_command_kind", "original_request_fingerprint", "resolution_request_fingerprint",
    "observed_pointer", "outcome", "actor", "recorded_at", "record_serializer_version", "confirmed_receipt", "occupied_receipt", "retirement_operation_id", "record_sha256"])
    || record.schema !== "dmb_agent_new_conversation_resolution_record_v1" || record.original_command_kind !== "new"
    || canonicalJson(record.request) !== canonicalJson(request) || record.record_serializer_version !== "canonical-json-ascii-v1"
    || typeof record.actor !== "string" || !record.actor.trim() || typeof record.recorded_at !== "string"
    || !Number.isFinite(Date.parse(record.recorded_at)) || !/(Z|[+-]\d{2}:\d{2})$/.test(record.recorded_at)
    || !isDigest(record.record_sha256)) return null;
  const command = request.original_command;
  const { resolution_operation_id: _id, ...operation } = request;
  const { record_sha256: digest, ...payload } = record;
  const originalDigest = await newConversationRequestFingerprint(command.world_id, {
    schema: "dmb_agent_new_conversation_v1", command_id: command.command_id,
    expected_pointer_revision: command.expected_pointer_revision, expected_active_conversation_id: command.expected_active_conversation_id });
  if (record.original_request_fingerprint !== originalDigest || record.resolution_request_fingerprint !== await commandCanonicalDigest(operation)
    || digest !== await commandCanonicalDigest(payload)) return null;
  const pointer = record.observed_pointer;
  if (!hasExactKeys(pointer, ["world_id", "active_conversation_id", "revision"]) || pointer.world_id !== command.world_id
    || !(pointer.active_conversation_id === null || commandUuid(pointer.active_conversation_id))
    || typeof pointer.revision !== "number" || !Number.isSafeInteger(pointer.revision) || pointer.revision < 0) return null;
  if (record.outcome === "retired") {
    if (record.confirmed_receipt !== null || record.occupied_receipt !== null || record.retirement_operation_id !== request.resolution_operation_id
      || pointer.revision !== request.expected_current_pointer_revision || pointer.active_conversation_id !== request.expected_current_active_conversation_id) return null;
  } else if (record.outcome === "submitted_binding_blocked") {
    const proof = record.occupied_receipt;
    if (record.confirmed_receipt !== null || record.retirement_operation_id !== null
      || !hasExactKeys(proof, ["world_id", "command_id", "command_kind", "request_fingerprint", "receipt_sha256"])
      || proof.world_id !== command.world_id || proof.command_id !== command.command_id
      || !["new", "archive", "reopen"].includes(String(proof.command_kind))
      || !isDigest(proof.request_fingerprint) || !isDigest(proof.receipt_sha256)
      || (proof.command_kind === "new" && proof.request_fingerprint === originalDigest)) return null;
  } else if (record.outcome === "confirmed") {
    const receipt = record.confirmed_receipt;
    if (record.occupied_receipt !== null || record.retirement_operation_id !== null
      || !hasExactKeys(receipt, ["world_id", "command_id", "command_kind", "conversation_id", "active_conversation_id", "pointer_revision", "recorded_at"])
      || receipt.world_id !== command.world_id || receipt.command_id !== command.command_id || receipt.command_kind !== "new"
      || !commandUuid(receipt.conversation_id) || receipt.active_conversation_id !== receipt.conversation_id
      || receipt.conversation_id === command.expected_active_conversation_id
      || typeof receipt.pointer_revision !== "number" || !Number.isSafeInteger(receipt.pointer_revision)
      || receipt.pointer_revision <= command.expected_pointer_revision
      || typeof receipt.recorded_at !== "string" || !Number.isFinite(Date.parse(receipt.recorded_at))) return null;
  } else return null;
  return record as unknown as WorldCommandResolutionRecordV1;
}

export async function confirmedNewConversationStatus(value: unknown, worldId: string,
  request: WorldAgentNewConversationRequestV1): Promise<boolean> {
  if (!hasExactKeys(value, ["schema", "world_id", "command_id", "command_kind", "expected_pointer_revision",
    "expected_active_conversation_id", "request_fingerprint", "status", "receipt"])
    || value.schema !== "dmb_agent_new_conversation_status_v1" || value.world_id !== worldId
    || value.command_id !== request.command_id || value.command_kind !== "new"
    || value.expected_pointer_revision !== request.expected_pointer_revision
    || value.expected_active_conversation_id !== request.expected_active_conversation_id
    || value.request_fingerprint !== await newConversationRequestFingerprint(worldId, request)
    || value.status !== "confirmed") return false;
  const receipt = value.receipt;
  return hasExactKeys(receipt, ["schema", "conversation_id", "active_conversation_id", "pointer_revision", "recorded_at"])
    && receipt.schema === "dmb_agent_new_conversation_receipt_v1"
    && typeof receipt.conversation_id === "string" && /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(receipt.conversation_id)
    && receipt.conversation_id !== request.expected_active_conversation_id
    && receipt.active_conversation_id === receipt.conversation_id
    && Number.isSafeInteger(receipt.pointer_revision) && typeof receipt.pointer_revision === "number"
    && receipt.pointer_revision > request.expected_pointer_revision
    && typeof receipt.recorded_at === "string" && Number.isFinite(Date.parse(receipt.recorded_at));
}

async function isReceiptDigestBound(receipt: WorldPlanGraphContextReceiptV1 | WorldBuildGraphReceiptV1 | WorldPlayGraphContextReceiptV1): Promise<boolean> {
  try {
    if (receipt.schema === "dmb_play_world_graph_context_receipt_v1") return await playReceiptDigestsBound(receipt);
    const { context_receipt_sha256: expected, ...payload } = receipt;
    const digest = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(canonicalJson(payload)));
    const actual = Array.from(new Uint8Array(digest), (byte) => byte.toString(16).padStart(2, "0")).join("");
    return actual === expected;
  } catch {
    return false;
  }
}

async function isHistoryReceiptDigestBound(turn: unknown): Promise<boolean> {
  if (!isRecord(turn)) return true;
  if ('play_source_context' in turn && !await playSourceContextDigestBound(turn.play_source_context)) return false;
  if (turn.schema === 'dmb_agent_conversation_history_play_source_turn_v1') return true;
  if ((turn.schema === 'dmb_agent_conversation_history_mixed_turn_v1' || turn.schema === 'dmb_agent_conversation_history_play_rules_turn_v1')) {
    const context = turn.rules_context as RulesAnswerContext;
    if (typeof turn.assistant_text !== 'string' || !await rulesAnswerDigestsBound(context, turn.assistant_text)) return false;
    const receipt = context.base_context?.receipt ?? context.unclaimed_context?.receipt;
    return receipt === undefined || await isReceiptDigestBound(receipt);
  }
  if (Object.prototype.hasOwnProperty.call(turn, "knowledge_context")) {
    const context = turn.knowledge_context;
    return isRecord(context) && isRecord(context.receipt) && isRecord(context.receipt.source_basis)
      && typeof context.receipt.source_basis.world_id === "string"
      && isBuildKnowledgeContext(context, context.receipt.source_basis.world_id)
      && isReceiptDigestBound(context.receipt);
  }
  if (Object.prototype.hasOwnProperty.call(turn, "play_context")) {
    return isWorldPlayContextProjection(turn.play_context, isWorldPlanGraphExecution, undefined, true)
      && isReceiptDigestBound(turn.play_context.receipt);
  }
  if (!isRecord(turn.plan_context)) return true;
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

async function pendingPlanAskIdempotencyKey(stored: StoredPendingAsk): Promise<string | null> {
  const envelope = stored.envelope;
  if (!envelope) return null;
  const worldId = envelope.origin.worldId;
  const turnId = envelope.request.turn_id;
  if (!worldId || !turnId) return null;
  return worldTurnIdempotencyKey(worldId, turnId);
}

async function worldTurnIdempotencyKey(worldId: string, turnId: string): Promise<string | null> {
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

async function confirmedReadOnlyTurn(page: WorldAgentConversationHistoryResponse, stored: StoredPendingPlayTurn) {
  const request = stored.request;
  if (page.world_id !== request.owner_scope.world_id || page.conversation_state !== "active" || page.active_conversation_id !== page.conversation_id) return false;
  const key = await worldTurnIdempotencyKey(request.owner_scope.world_id, request.turn_id);
  const matching = page.turns.filter(turn => {
    const basis = turn.provenance.primary_work;
    return (turn.turn_id === request.turn_id || (key && "idempotency_key" in turn && turn.idempotency_key === key))
      && ["completed", "failed", "interrupted"].includes(turn.lifecycle_status)
      && turn.user_text === request.message && turn.provenance.world_id === request.owner_scope.world_id
      && turn.provenance.surface_id === request.surface.surface_id && basis.kind === request.primary_work.kind
      && basis.object_id === request.primary_work.object_id && basis.revision === String(request.primary_work.expected_revision)
      && (request.primary_work.kind !== "build" || basis.content_sha256 === request.primary_work.expected_content_sha256)
      && (request.primary_work.kind !== "run" || (request.graph_request.mode === "none"
        ? "play_source_context" in turn && isPlaySourceContext(turn.play_source_context,request as WorldPlayAgentTurnRequestV1)
          && isPlaySourceProvenanceBound(turn.play_source_context,turn.provenance,request.owner_scope.world_id)
        : (() => {
        const context = graphContextForTurn(turn);
        const unclaimed = rulesContextForTurn(turn)?.unclaimed_context;
        const receipt = unclaimed?.receipt ?? context?.receipt;
        return isWorldPlayGraphReceipt(receipt, request as WorldPlayAgentTurnRequestV1)
          && isPlayContextProvenanceBound(receipt, turn.provenance, request.owner_scope.world_id);
      })()));
  });
  return matching.length === 1;
}

function completedHistoryTurnMatchesPendingAsk(
  page: WorldAgentConversationHistoryResponse,
  turn: WorldAgentConversationHistoryTurn,
  stored: StoredPendingAsk,
  idempotencyKey: string,
  acknowledgedConversationId?: string,
): boolean {
  const envelope = stored.envelope;
  if (!envelope) return false;
  const { request, origin } = envelope;
  if ((page.schema !== "dmb_agent_conversation_history_v3" && page.schema !== "dmb_agent_conversation_history_v4")
    || !("idempotency_key" in turn)
    || turn.idempotency_key !== idempotencyKey
    || page.world_id !== origin.worldId
    || !(acknowledgedConversationId === undefined ? historyPageMatchesPendingAskConversation(page, origin)
      : page.conversation_id === acknowledgedConversationId && page.active_conversation_id === acknowledgedConversationId)
    || turn.lifecycle_status !== "completed"
    || turn.user_text !== request.message
    || typeof turn.assistant_text !== "string"
    || !turn.assistant_text.trim()
    || turn.provenance.world_id !== origin.worldId
    || turn.provenance.surface_resolution !== "resolved"
    || turn.provenance.surface_id !== request.surface.surface_id
    || typeof request.surface.instance_id !== "string"
    || turn.provenance.surface_instance_id !== request.surface.instance_id) return false;

  if (!request.plan_context_policy) return isGraphOffPlanHistoryBound(turn,request,origin);
  const unclaimed = rulesContextForTurn(turn)?.unclaimed_context;
  if (unclaimed) {
    if (!isRulesUnclaimedContext(unclaimed, origin.worldId, request, turn.provenance)
      || !isWorldPlanGraphReceipt(unclaimed.receipt, request)) return false;
    const basis = unclaimed.receipt.plan_basis;
    return basis.world_id === origin.worldId && basis.document_id === origin.documentId
      && basis.object_revision === origin.objectRevision && basis.work_revision_id === origin.workRevisionId
      && basis.revision_n === origin.revisionN && basis.content_sha256 === origin.contentSha256;
  }
  const context = graphContextForTurn(turn);
  if (!context || context.schema !== 'dmb_agent_plan_world_graph_context_response_v2'
    || !isWorldPlanContextProjection(context, request, true)
    || context.completion === null
    || (context.execution !== null && context.execution.claimability !== "completed")
    || !isHistoryPlanReceiptBound(context.receipt, turn.provenance, origin.worldId)) return false;

  const basis = context.receipt.plan_basis;
  if (basis.world_id !== origin.worldId
    || basis.document_id !== origin.documentId
    || basis.object_revision !== origin.objectRevision
    || basis.work_revision_id !== origin.workRevisionId
    || basis.revision_n !== origin.revisionN
    || basis.content_sha256 !== origin.contentSha256) return false;

  const completedText = context.completion.answer_segments.map((segment) => segment.text).join("\n");
  return rulesContextForTurn(turn) !== undefined || turn.assistant_text === completedText;
}

function isGraphOffPlanHistoryBound(turn: WorldAgentConversationHistoryTurn, request: WorldPlanAgentTurnRequestV1,
  origin: WorldPlanPendingAskOrigin): boolean {
  const provenance = turn.provenance, basis = provenance.primary_work;
  const context = rulesContextForTurn(turn);
  const targets = provenance.supporting_work.filter(ref => ref.kind === 'dmb_plan_playable_target_v1');
  return request.graph_request.mode === 'none' && graphContextForTurn(turn) === undefined
    && (!context || context.accepted_binding.base_disposition === 'absent')
    && provenance.selected_object.resolution === 'absent'
    && !provenance.supporting_work.some(ref => ref.kind === 'world_graph_revision' || ref.kind === 'dmb_play_graph_binding_v1')
    && basis.resolution === 'resolved' && basis.kind === 'plan' && basis.object_id === origin.documentId
    && basis.object_revision === origin.objectRevision && basis.work_revision_id === origin.workRevisionId
    && basis.revision_n === origin.revisionN && basis.content_sha256 === origin.contentSha256
    && (request.playable_target ? targets.length === 1 && targets[0].resolution === 'resolved'
      && targets[0].object_id === request.playable_target.id && ['v1','v2'].includes(String(targets[0].revision)) : targets.length === 0);
}

async function confirmedAskHistoryMatches(
  page: WorldAgentConversationHistoryResponse,
  stored: StoredPendingAsk,
  conversationId: string,
  answer: string,
): Promise<boolean> {
  const envelope = stored.envelope;
  if (!envelope || page.world_id !== envelope.origin.worldId
    || page.conversation_state !== "active" || page.conversation_id !== conversationId
    || page.active_conversation_id !== conversationId) return false;
  const idempotencyKey = await pendingPlanAskIdempotencyKey(stored);
  return Boolean(idempotencyKey && page.turns.filter(turn =>
    completedHistoryTurnMatchesPendingAsk(page,turn,stored,idempotencyKey,
      envelope.request.plan_context_policy ? undefined : conversationId)
    && turn.assistant_text === answer).length === 1);

}

function failedHistoryTurnMatchesPendingAsk(
  page: WorldAgentConversationHistoryResponse,
  turn: WorldAgentConversationHistoryTurn,
  stored: StoredPendingAsk,
  idempotencyKey: string,
): boolean {
  const envelope = stored.envelope;
  if (!envelope) return false;
  const { request, origin } = envelope;
  if ((page.schema !== "dmb_agent_conversation_history_v3" && page.schema !== "dmb_agent_conversation_history_v4")
    || !("idempotency_key" in turn)
    || turn.idempotency_key !== idempotencyKey
    || page.world_id !== origin.worldId
    || !historyPageMatchesPendingAskConversation(page, origin)
    || !["failed", "interrupted"].includes(turn.lifecycle_status)
    || turn.user_text !== request.message
    || turn.provenance.world_id !== origin.worldId
    || turn.provenance.surface_resolution !== "resolved"
    || turn.provenance.surface_id !== request.surface.surface_id
    || typeof request.surface.instance_id !== "string"
    || turn.provenance.surface_instance_id !== request.surface.instance_id) return false;

  if (!request.plan_context_policy) return isGraphOffPlanHistoryBound(turn,request,origin);
  const context = "plan_context" in turn ? turn.plan_context : undefined;
  if (!context
    || !isWorldPlanContextProjection(context, request, true)
    || context.completion !== null
    || context.execution === null
    || context.execution.claimability === "completed"
    || !isHistoryPlanReceiptBound(context.receipt, turn.provenance, origin.worldId)) return false;

  const basis = context.receipt.plan_basis;
  return basis.world_id === origin.worldId
    && basis.document_id === origin.documentId
    && basis.object_revision === origin.objectRevision
    && basis.work_revision_id === origin.workRevisionId
    && basis.revision_n === origin.revisionN
    && basis.content_sha256 === origin.contentSha256;
}

async function classifyTerminalFailedPendingAsks(
  page: WorldAgentConversationHistoryResponse,
  worldId: string,
  documentId: string,
  isCurrent: () => boolean,
): Promise<ConfirmedTerminalFailureAsk[]> {
  if ((page.schema !== "dmb_agent_conversation_history_v3" && page.schema !== "dmb_agent_conversation_history_v4")) return [];
  const pending = readPendingAsks(worldId, documentId)
    .filter((stored) => stored.envelope !== null);
  const correlated = await Promise.all(pending.map(async (stored) => ({
    stored,
    key: await pendingPlanAskIdempotencyKey(stored),
  })));
  if (!isCurrent()) return [];

  const candidates = correlated.flatMap(({ stored, key }) => {
    if (!key) return [];
    const matchingRows = page.turns.filter((turn) => "idempotency_key" in turn && turn.idempotency_key === key);
    if (matchingRows.length !== 1) return [];
    const turn = matchingRows[0]!;
    return failedHistoryTurnMatchesPendingAsk(page, turn, stored, key)
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
      clientTurnId: stored.envelope!.request.turn_id,
    }));
}

function reconcileCompletedPendingAsks(
  page: WorldAgentConversationHistoryResponse,
  worldId: string,
  documentId: string,
  isCurrent: () => boolean,
): Promise<{ refreshPendingList: boolean; storageError: string | null; confirmedTurnIds: string[] }> {
  if ((page.schema !== "dmb_agent_conversation_history_v3" && page.schema !== "dmb_agent_conversation_history_v4")) {
    return Promise.resolve({ refreshPendingList: false, storageError: null, confirmedTurnIds: [] });
  }
  const pending = readPendingAsks(worldId, documentId)
    .filter((stored) => stored.envelope !== null);
  return Promise.all(pending.map(async (stored) => ({
    stored,
    key: await pendingPlanAskIdempotencyKey(stored),
  }))).then((correlated) => {
    if (!isCurrent()) return { refreshPendingList: false, storageError: null, confirmedTurnIds: [] };
    const candidates = correlated.flatMap(({ stored, key }) => {
      if (!key) return [];
      const matchingRows = page.turns.filter((turn) => "idempotency_key" in turn && turn.idempotency_key === key);
      if (matchingRows.length !== 1) return [];
      const turn = matchingRows[0]!;
      return completedHistoryTurnMatchesPendingAsk(page, turn, stored, key)
        ? [{ stored, key }]
        : [];
    });
    const matchesByKey = new Map<string, number>();
    for (const candidate of candidates) matchesByKey.set(candidate.key, (matchesByKey.get(candidate.key) ?? 0) + 1);

  const confirmedTurnIds: string[] = [];
  let refreshPendingList = false;
  let storageError: string | null = null;
    for (const candidate of candidates) {
      if (!isCurrent()) break;
      if (matchesByKey.get(candidate.key) !== 1) continue;
      const result = clearPendingAskIfUnchanged(candidate.stored);
      if (result.kind === "cleared") {
        confirmedTurnIds.push(candidate.stored.envelope!.request.turn_id);
        dispatchPendingAskSettlement(candidate.stored, result);
      } else {
        // A replacement envelope or storage failure stays visible and intact.
        refreshPendingList = true;
        if (result.kind === "unavailable") storageError = result.message;
      }
    }
    return { refreshPendingList, storageError, confirmedTurnIds };
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
  const mixed = isRecord(value) && value.schema === 'dmb_agent_rules_turn_response_v1';
  const topKeys = mixed ? [...baseKeys, 'rules_context'] : hasPolicy ? [...baseKeys, "plan_context"] : baseKeys;
  if (!hasExactKeys(value, topKeys)
    || value.schema !== (mixed ? 'dmb_agent_rules_turn_response_v1' : hasPolicy ? "dmb_agent_turn_response_v2" : "dmb_agent_turn_response_v1")
    || value.client_thread_id !== request.client_thread_id
    || value.turn_id !== request.turn_id) {
    return { ok: false, message: RESPONSE_MISMATCH };
  }

  if (mixed && (!isRecord(value.answer) || !isRecord(value.conversation)
    || typeof value.conversation.conversation_id !== 'string'
    || !isRulesAnswerContext(value.rules_context, value.answer.text, request.owner_scope.world_id,
      base => isWorldPlanContextProjection(base, request),
      typeof value.conversation.conversation_id === 'string' ? { conversationId: value.conversation.conversation_id } : undefined,
      c => isRulesUnclaimedContext(c, request.owner_scope.world_id, request))
    || !await rulesAnswerDigestsBound(value.rules_context, value.answer.text as string))) return { ok: false, message: RESPONSE_MISMATCH };
  const mixedContext = mixed ? value.rules_context as RulesAnswerContext : undefined;
  const candidateContext = mixed ? mixedContext?.base_context : value.plan_context;
  const planContext = hasPolicy
    ? isWorldPlanContextProjection(candidateContext, request) ? candidateContext : null
    : null;
  const unclaimed = mixedContext?.unclaimed_context;
  if (hasPolicy && !planContext && !unclaimed) return { ok: false, message: RESPONSE_MISMATCH };
  const responseReceipt = planContext?.receipt ?? unclaimed?.receipt;
  if (responseReceipt && !await isReceiptDigestBound(responseReceipt)) {
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
    || planContext?.delivery_replay === true || unclaimed?.delivery_replay === true;
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
  const expectedGraphGrounded = mixedContext ? mixedContext.accepted_binding.graph_used : planContext?.completion
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
  return { ok: true, value: { answer: answer.text, trace: answer.trace, summary, conversationId: typeof conversation.conversation_id === "string" ? conversation.conversation_id : null, replayed,
    planReceiptBasis: responseReceipt?.schema === "dmb_agent_plan_world_graph_context_receipt_v1" ? responseReceipt.plan_basis : null } };
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
  visible = true,
  playMode = null,
  buildMode = null,
  presentationHosts,
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
  editorSelectionActive = false,
  playableTargetLabel,
  playableEditTargetLabel,
  onClearPlayableEditTarget = () => undefined,
  onSavePlan,
  savePlanEnabled = false,
  imagePromptHost,
}: WorldPlanAgentConversationProps) {
  const selectedWorld = useSelectedWorld();
  const agent = useAgentInteraction();
  const sharedConversation = useWorldAgentConversationState();
  const [localHistory, setLocalHistory] = useState<WorldAgentConversationHistoryResponse | null>(null);
  const history = sharedConversation?.worldId === worldId ? sharedConversation.history : localHistory;
  const setHistory = sharedConversation?.worldId === worldId ? sharedConversation.setHistory : setLocalHistory;
  const askSlot = useAskPluginSlotOptional();
  const verifiedWorldId = selectedWorld.kind === "managed" ? selectedWorld.worldId : null;
  const isBuild = buildMode !== null;
  const surfaceRequests = useSurfaceConversationRequests();
  const surfacePreparationRef = useRef(false);
  const [surfacePreparing,setSurfacePreparing] = useState(false);
  const [libraryOpen,setLibraryOpen]=useState(false);
  const surfaceVisibleRef = useRef(visible);surfaceVisibleRef.current=visible;
  const surfaceObjectId=buildMode?.savedSource?.documentId;
  useEffect(()=>{
    if(!isBuild||!verifiedWorldId||!surfaceObjectId)return;
    return()=>cancelSurfaceConversationTarget(verifiedWorldId,'build',surfaceObjectId);
  },[isBuild,verifiedWorldId,surfaceObjectId]);
  const isReadOnly = playMode !== null || isBuild;
  const currentReadOnlyContext = isBuild ? buildMode?.savedSource : playMode?.admittedRun;
  const planReady = Boolean(!isReadOnly && pageReady
    && verifiedWorldId === worldId
    && documentId
    && surfaceInstanceId
    && isPositiveRevision(revision));
  const namespace = planReady && documentId ? planThreadNamespace(worldId, documentId) : null;
  const surfaceContext = useMemo(() => visible && !isReadOnly && namespace && documentId ? ({
    surfaceId: "plan" as const,
    label: "World Plan conversation",
    campaignId: namespace,
    documentId,
    sessionNumber: null,
    ambientSummary: "Plan Ask uses the exact committed revision; unsaved draft text is excluded",
    sourceEnvelope: null,
  }) : null, [documentId, namespace, visible, isReadOnly]);
  usePublishAgentSurfaceContext(surfaceContext);
  useRegisterAskPluginPresence(visible && (planReady || (isReadOnly && verifiedWorldId === worldId)));

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
  const committedPlanVersionKey = JSON.stringify([verifiedWorldId, documentId, revision]);
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
  const effectiveEditTarget = editorSelectionActive ? null
    : playableEditTarget ?? (playableTarget?.kind === "scene" ? playableTarget : null);
  const effectiveEditTargetStale = !editorSelectionActive && (playableEditTarget
    ? playableEditTargetStale : playableTarget?.kind === "scene" && playableTargetStale);
  const displayedEditKind = editorSelectionActive ? "replace_selection"
    : effectiveEditTarget ? "replace_playable_body" : "insert_at_caret";
  const displayedEditScope = editorSelectionActive ? "Replace selected editor text"
    : effectiveEditTarget ? `Replace ${effectiveEditTarget.kind} body: ${(playableEditTarget ? playableEditTargetLabel : playableTargetLabel) || effectiveEditTarget.id} (${effectiveEditTarget.id})`
      : "Insert at editor cursor — no scene or text target selected";
  const lastPlanScopeForReviewRef = useRef(agent.scope);
  if (!isReadOnly && scopeMatches) lastPlanScopeForReviewRef.current = agent.scope;
  const reviewScope = !isReadOnly && scopeMatches ? agent.scope : lastPlanScopeForReviewRef.current;
  // Route chrome can replace the portal host while the captured Plan and edit target remain unchanged.
  // Apply still checks the live mounted Plan and provider binding before touching the draft.
  const currentPlanProposalFenceKey = JSON.stringify({
    requestFenceKey,
    conversationId: history?.conversation_id ?? null,
    pointerRevision: history?.pointer_revision ?? null,
    draftGeneration,
    selectionGeneration,
    savedDirty,
    playableEditTarget,
    playableEditTargetGeneration,
    playableEditTargetStale,
    editorSelectionActive,
    effectiveEditTarget,
    effectiveEditTargetStale,
    sceneBasis: !editorSelectionActive && !playableEditTarget && playableTarget?.kind === "scene" ? playableTargetBasis : null,
    agentScope: reviewScope ? {
      campaignId: reviewScope.campaignId,
      surfaceId: reviewScope.surfaceId ?? null,
      sessionNumber: reviewScope.sessionNumber,
      documentId: reviewScope.documentId ?? null,
    } : null,
  });
  const lastPlanProposalFenceRef = useRef(currentPlanProposalFenceKey);
  if (!isReadOnly && scopeMatches) lastPlanProposalFenceRef.current = currentPlanProposalFenceKey;
  const proposalFenceKey = isReadOnly || !scopeMatches ? lastPlanProposalFenceRef.current : currentPlanProposalFenceKey;
  const [localComposerDrafts, setLocalComposerDrafts] = useState<Record<string, string>>({});
  const composerDrafts = sharedConversation?.worldId === worldId ? sharedConversation.composerDrafts : localComposerDrafts;
  const setComposerDrafts = sharedConversation?.worldId === worldId ? sharedConversation.setComposerDrafts : setLocalComposerDrafts;
  const composerDraftKey = isBuild ? `build:${buildMode?.savedSource?.documentId ?? "unavailable"}` : isReadOnly ? `play:${playMode?.admittedRun?.runId ?? "unadmitted"}` : `plan:${documentId ?? "unsaved"}`;
  const composerMessage = composerDrafts[composerDraftKey] ?? "";
  const setComposerMessage = (action: string | ((current: string) => string)) => {
    setComposerDrafts((drafts) => {
      const current = drafts[composerDraftKey] ?? "";
      const next = typeof action === "function" ? action(current) : action;
      return next === current ? drafts : { ...drafts, [composerDraftKey]: next };
    });
  };
  const composerEditGenerationRef = useRef(0);
  const lastVisiblePlanDocumentRef = useRef<string | null>(null);
  useLayoutEffect(() => {
    if (!sharedConversation || !visible || isReadOnly) return;
    const priorDocument = lastVisiblePlanDocumentRef.current;
    if (priorDocument && priorDocument !== documentId) {
      composerEditGenerationRef.current += 1;
      setContinuationOfActionId(null);
    }
    lastVisiblePlanDocumentRef.current = documentId;
  }, [sharedConversation?.worldId, visible, isReadOnly, documentId]);
  function restoreSubmittedDraft(snapshot: string, generation: number) {
    setComposerMessage((current) => current === "" && composerEditGenerationRef.current === generation ? snapshot : current);
  }
  const [retryPresentationOrigin, setRetryPresentationOrigin] = useState<{scopeKey:string;turnId:string}|null>(null);
  const [submittedMessage, setSubmittedMessage] = useState<{
    id: string; scopeKey: string; conversationId: string | null; pointerRevision: number | null;
    message: string; kind: "discuss" | "propose";
    idempotencyKey?: string | null;
  } | null>(null);
  const confirmedResetRef = useRef<{ commandId: string; worldId: string; conversationId: string; pointerRevision: number } | null>(null);
  const [retiredProposalTurns, setRetiredProposalTurns] = useState<{
    scopeKey: string; turns: AgentInteractionTurn[]; positions: WorldPlanLocalProposalPosition[];
  } | null>(null);
  const [composerIntent, setComposerIntent] = useState<"discuss" | "propose">("discuss");
  const [continuationOfActionId, setContinuationOfActionId] = useState<string | null>(null);
  const [composerIntentCorrection, setComposerIntentCorrection] = useState<{
    message: string;
    intent: "discuss" | "propose";
  } | null>(null);
  const [newReplyAvailable, setNewReplyAvailable] = useState(false);
  const followsLatestRef = useRef(true);
  const hasObservedConversationHistoryRef = useRef(false);
  const observedConversationIdRef = useRef<string | null>(null);
  const observedAssistantReplyKeyRef = useRef<string | null>(null);
  const olderPageScrollAnchorRef = useRef<{
    viewport: HTMLElement;
    scrollTop: number;
    scrollHeight: number;
  } | null>(null);
  const playMessagesHostRef = useRef<HTMLDivElement | null>(null);
  const previousVerifiedWorldIdRef = useRef(verifiedWorldId);
  const [useWorldGraphForAsk, setUseWorldGraphForAsk] = useState(true);
  const buildPlacementFenceKey = JSON.stringify([scopeKey, buildMode?.savedSource, history?.conversation_id,
    history?.active_conversation_id, history?.conversation_state, history?.pointer_revision, useWorldGraphForAsk]);
  const buildPlacementLifecycle = useRef({key: buildPlacementFenceKey, bridge: buildMode?.composeBridge, epoch: 0});
  if (buildPlacementLifecycle.current.key !== buildPlacementFenceKey
    || buildPlacementLifecycle.current.bridge !== buildMode?.composeBridge) {
    buildPlacementLifecycle.current = {key: buildPlacementFenceKey, bridge: buildMode?.composeBridge,
      epoch: buildPlacementLifecycle.current.epoch + 1};
  }
  const buildPlacementEpoch = buildPlacementLifecycle.current.epoch;
  const [buildPlacementFailure, setBuildPlacementFailure] = useState<{
    fenceKey: string; epoch: number; message: string; generation: number; reason: string;
    bridge: NonNullable<NonNullable<WorldPlanAgentConversationProps["buildMode"]>["composeBridge"]>;
  } | null>(null);
  const visibleBuildPlacementFailure = isBuild && buildPlacementFailure
    && buildPlacementFailure.fenceKey === buildPlacementFenceKey
    && buildPlacementFailure.epoch === buildPlacementEpoch
    && buildPlacementFailure.bridge === buildMode?.composeBridge
    && buildPlacementFailure.message === composerMessage.trim()
    && buildPlacementFailure.generation === composerEditGenerationRef.current ? buildPlacementFailure : null;
  useLayoutEffect(() => {
    if (previousVerifiedWorldIdRef.current === verifiedWorldId) return;
    previousVerifiedWorldIdRef.current = verifiedWorldId;
    setUseWorldGraphForAsk(true);
  }, [verifiedWorldId]);
  const [graphCredentialStatus, setGraphCredentialStatus] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const uncertainPlanNoticeRef = useRef<{ turnId: string; message: string } | null>(null);
  const uncertainPlayNoticeRef = useRef<{ turnId: string; message: string } | null>(null);
  const [editError, setEditError] = useState<string | null>(null);
  const [sending, setSending] = useState(false);
  const [composing, setComposing] = useState(false);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const connectionOptionsRef = useRef<HTMLDetailsElement | null>(null);
  const [traceVisible, setTraceVisible] = useState(false);
  const [openedTraceTurns, setOpenedTraceTurns] = useState<Record<string, boolean>>({});
  const [historyLoading, setHistoryLoading] = useState(false);
  const [olderLoading, setOlderLoading] = useState(false);
  const [historyError, setHistoryError] = useState<string | null>(null);
  const [sourcePassage, setSourcePassage] = useState<{
    turnId: string; claimId: string; targetId: string;
    status: "loading" | "open" | "unavailable"; content: string | null; message: string | null; partial: boolean;
    page?: WorldGraphRecapContextReadResponseV2; pages?: number; loadingMore?: boolean;
    lines?: { start: number; end: number }; sourceName?: string | null;
  } | null>(null);
  const sourceReadEpochRef = useRef(0);
  const [historyRefreshNonce, setHistoryRefreshNonce] = useState(0);
  const [proposalOrderRevision, setProposalOrderRevision] = useState(0);
  const [pendingAsks, setPendingAsks] = useState<StoredPendingAsk[]>([]);
  useEffect(() => {
    if (!submittedMessage || submittedMessage.kind !== "discuss"
      || submittedMessage.idempotencyKey !== undefined) return;
    const stored = pendingAsks.find((item) => item.envelope?.request.turn_id === submittedMessage.id);
    if (!stored) return;
    let active = true;
    void pendingPlanAskIdempotencyKey(stored).then((key) => {
      if (active) setSubmittedMessage((current) => current?.id === submittedMessage.id
        ? { ...current, idempotencyKey: key } : current);
    });
    return () => { active = false; };
  }, [pendingAsks, submittedMessage]);
  const [confirmedTerminalFailureAsks, setConfirmedTerminalFailureAsks] = useState<ConfirmedTerminalFailureAsk[]>([]);
  const [pendingAskLoadError, setPendingAskLoadError] = useState<string | null>(null);
  const [pendingCommands, setPendingCommands] = useState<StoredPendingNewConversation[]>([]);
  const [pendingPlayTurn, setPendingPlayTurn] = useState<StoredPendingPlayTurn | null>(null);
  const [pendingPlayLoadError, setPendingPlayLoadError] = useState<string | null>(null);
  const [pendingPlayLoadedWorldId, setPendingPlayLoadedWorldId] = useState<string | null>(null);
  const [pendingCommandLoadError, setPendingCommandLoadError] = useState<string | null>(null);
  const [newConversationSending, setNewConversationSending] = useState(false);
  const [newConversationError, setNewConversationError] = useState<string | null>(null);
  const [conversationNotice, setConversationNotice] = useState<string | null>(null);
  const confirmedAskNoticeRef = useRef<{
    stored: StoredPendingAsk;
    conversationId: string;
    answer: string;
    notice: string;
  } | null>(null);
  const [savedPlanVersion, setSavedPlanVersion] = useState<{
    key: string;
    revisionN: number | null;
    status: "checking" | "verified" | "unavailable";
  } | null>(null);
  const [editReview, setEditReview] = useState<WorldPlanEditReview | null>(null);
  const [reviewSnapshots, setReviewSnapshots] = useState<Record<string, FrozenPlanEditReview>>({});
  const [applyingTurnId, setApplyingTurnId] = useState<string | null>(null);
  const applyingReviewRef = useRef<WorldPlanEditReview | null>(null);
  const [sectionTargets, setSectionTargets] = useState<PlanSectionOption[]>([]);
  const [selectedSectionTargetId, setSelectedSectionTargetId] = useState("");
  const [sectionTargetStatus, setSectionTargetStatus] = useState<PlanSectionTargetStatus | null>(null);
  const selectedSectionTargetLabel = sectionTargets
    .find((target) => target.id === selectedSectionTargetId)
    ?.label.replace(/^#{1,6}\s+/, "") ?? null;
  const [actionHistory, setActionHistory] = useState<WorldPlanActionProjection[]>([]);
  const [actionHistoryError, setActionHistoryError] = useState<string | null>(null);
  const [conversationActions, setConversationActions] = useState<WorldPlanActionProjection[]>([]);
  const [conversationActionsError, setConversationActionsError] = useState<string | null>(null);
  const requestRef = useRef<{ token: symbol; scopeKey: string; fenceKey: string } | null>(null);
  const newConversationRef = useRef<symbol | null>(null);
  const commandStatusRef = useRef<symbol | null>(null);
  const [commandStatusChecking, setCommandStatusChecking] = useState(false);
  const resolutionGenerationRef = useRef(0);
  const [blockedResolution, setBlockedResolution] = useState<{
    resolutionKey: string; resolutionBytes: string; originalKey: string; originalBytes: string;
    envelope: WorldPlanPendingNewConversation; record: WorldCommandResolutionRecordV1; generation: number;
  } | null>(null);
  const historySnapshotRef = useRef<WorldAgentConversationHistoryResponse | null>(null);
  useLayoutEffect(() => {
    sourceReadEpochRef.current += 1;
    setSourcePassage(null);
  }, [scopeKey, verifiedWorldId, history?.conversation_id]);
  const historyGenerationRef = useRef(0);
  const olderHistoryReadRef = useRef<AbortController | null>(null);
  const historyReadScopeRef = useRef<string | null>(null);
  const legacyHistoryRef = useRef<{ scopeKey: string; thread: AgentInteractionThread; rawBytes: string | null } | null>(null);
  const proposalRequestRef = useRef<{ token: symbol; threadId: string; fenceKey: string; providerThreadId: string | null } | null>(null);
  const proposalIntentRef = useRef<{ fingerprint: string; idempotencyKey: string } | null>(null);
  const editReviewRef = useRef<WorldPlanEditReview | null>(null);
  const sectionScanRef = useRef<PlanSectionScan | null>(null);
  const sectionOperationRef = useRef<symbol | null>(null);
  const latestRef = useRef({
    fenceKey: requestFenceKey,
    presentationFenceKey: askPresentationFenceKey,
    buildPlacementFenceKey,
    buildPlacementEpoch,
    buildPlacementBridge: buildMode?.composeBridge,
    proposalFenceKey,
    threadId: activeThread?.threadId ?? null,
    providerThreadId: agent.activeThread?.threadId ?? null,
    savePlanEnabled,
    saveInFlight,
    savedDirty,
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
  const lastPlanProposalThreadRef = useRef<AgentInteractionThread | null>(null);
  if (!isReadOnly && scopeMatches) lastPlanProposalThreadRef.current = activeThread?.worldPlanProposalHistory === WORLD_PLAN_LOCAL_PROPOSAL_HISTORY
    ? activeThread : null;
  const proposalThreadForDisplay = lastPlanProposalThreadRef.current;
  const proposalOrderKeyForDisplay = namespace && proposalThreadForDisplay
    ? localProposalOrderStorageKey(namespace, proposalThreadForDisplay.threadId)
    : null;
  const proposalOrderForDisplay = useMemo(
    () => proposalOrderKeyForDisplay ? readLocalProposalOrder(proposalOrderKeyForDisplay) : null,
    [proposalOrderKeyForDisplay, proposalOrderRevision],
  );
  const [playEditMode, setPlayEditMode] = useState(false);
  const playCompose = usePlaySceneEdits({ worldId, runId: playMode?.admittedRun?.runId ?? null,
    bridge: playMode?.sceneEditBridge ?? null });
  const buildCompose = useBuildCompose({ worldId, history,
    bridge: buildMode?.composeBridge ?? null, enabled: visible && isBuild, onReviewOnPage:()=>agent.setPaneOpen(false), pageDocumentId: buildMode?.savedSource?.documentId ?? null, sourceKey: JSON.stringify([buildMode?.savedSource?.worldId, buildMode?.savedSource?.documentId, buildMode?.savedSource?.revision, buildMode?.savedSource?.contentSha256]),
    onHistory: next => { historySnapshotRef.current = next; setHistory(next); } });

  const conversationDisplay = useMemo(
    () => buildWorldConversationDisplayEvents(
      history,
      proposalThreadForDisplay?.turns ?? [],
      proposalOrderForDisplay?.positions ?? [],
    ),
    [history, proposalOrderForDisplay, proposalThreadForDisplay?.turns],
  );
  const archivedProposalTurns = useMemo(() => {
    if (!namespace || !documentId) return [];
    try {
      return listAgentThreads(namespace, "plan", documentId)
        .filter((summary) => summary.threadId !== proposalThreadForDisplay?.threadId)
        .flatMap((summary) => {
          const thread = loadAgentThreadById(namespace, summary.threadId);
          return thread?.worldPlanProposalHistory === WORLD_PLAN_LOCAL_PROPOSAL_HISTORY
            ? thread.turns.filter((turn) => turn.planEdit) : [];
        });
    } catch { return []; }
  }, [namespace, documentId, proposalThreadForDisplay?.threadId, proposalOrderRevision]);
  const otherLocalProposals = [...new Map([...conversationDisplay.localActivity, ...archivedProposalTurns,
    ...(retiredProposalTurns?.scopeKey === scopeKey ? retiredProposalTurns.turns : [])]
    .map((turn) => [turn.turnId, turn])).values()];
  const archivedProposalPositions = useMemo(() => {
    if (!namespace || !documentId) return [];
    try {
      return listAgentThreads(namespace, "plan", documentId)
        .filter((summary) => summary.threadId !== proposalThreadForDisplay?.threadId)
        .flatMap((summary) => readLocalProposalOrder(localProposalOrderStorageKey(namespace, summary.threadId))?.positions ?? []);
    } catch { return []; }
  }, [namespace, documentId, proposalThreadForDisplay?.threadId, proposalOrderRevision]);
  const latestAssistantReplyKey = (() => {
    const event = [...conversationDisplay.events].reverse().find((candidate) =>
      candidate.kind === "world"
      && candidate.turn.lifecycle_status === "completed"
      && Boolean(candidate.turn.assistant_text?.trim()));
    const proposal = buildCompose.items.at(-1);
    if (proposal && (!event || event.kind !== "world" || proposal.afterSequence >= event.turn.sequence)) return `build:${proposal.key}`;
    return event?.kind === "world" ? `${event.turn.turn_id}:${event.turn.assistant_text}` : null;
  })();
  useLayoutEffect(() => {
    if ((!presentationHosts && !isReadOnly) || !agent.paneState.isOpen) return;
    const viewport = presentationHosts?.messages?.parentElement ?? playMessagesHostRef.current?.parentElement;
    if (!viewport) return;
    const nearBottom = () => viewport.scrollHeight - viewport.scrollTop - viewport.clientHeight <= 48;
    const updateFollowState = () => {
      followsLatestRef.current = nearBottom();
      if (followsLatestRef.current) setNewReplyAvailable(false);
    };
    updateFollowState();
    viewport.addEventListener("scroll", updateFollowState, { passive: true });
    return () => viewport.removeEventListener("scroll", updateFollowState);
  }, [agent.paneState.isOpen, presentationHosts, isReadOnly]);
  useLayoutEffect(() => {
    const anchor = olderPageScrollAnchorRef.current;
    if (!anchor) return;
    olderPageScrollAnchorRef.current = null;
    const addedHeight = Math.max(0, anchor.viewport.scrollHeight - anchor.scrollHeight);
    anchor.viewport.scrollTop = anchor.scrollTop + addedHeight;
  }, [history]);
  useLayoutEffect(() => {
    if (!isReadOnly || presentationHosts || !agent.paneState.isOpen) return;
    const viewport = playMessagesHostRef.current?.parentElement;
    if (viewport) viewport.scrollTop = viewport.scrollHeight;
  }, [isReadOnly, agent.paneState.isOpen]);
  useLayoutEffect(() => {
    if ((!presentationHosts && !isReadOnly) || !agent.paneState.isOpen || !history || historyLoading) return;
    const viewport = presentationHosts?.messages?.parentElement ?? playMessagesHostRef.current?.parentElement;
    if (!viewport) return;
    if (!hasObservedConversationHistoryRef.current || observedConversationIdRef.current !== history.conversation_id) {
      hasObservedConversationHistoryRef.current = true;
      observedConversationIdRef.current = history.conversation_id;
      observedAssistantReplyKeyRef.current = latestAssistantReplyKey;
      setNewReplyAvailable(false);
      positionLatestAssistantReply(viewport);
      return;
    }
    if (!latestAssistantReplyKey || latestAssistantReplyKey === observedAssistantReplyKeyRef.current) return;
    const conversationId = history.conversation_id;
    const replyKey = latestAssistantReplyKey;
    const scrollToLatest = () => {
      if (observedConversationIdRef.current !== conversationId || !agent.paneState.isOpen) return;
      observedAssistantReplyKeyRef.current = replyKey;
      if (followsLatestRef.current) {
        positionLatestAssistantReply(viewport);
        setNewReplyAvailable(false);
      } else {
        setNewReplyAvailable(true);
      }
    };
    if (typeof window.requestAnimationFrame !== "function") {
      scrollToLatest();
      return;
    }
    const frame = window.requestAnimationFrame(scrollToLatest);
    return () => window.cancelAnimationFrame(frame);
  }, [agent.paneState.isOpen, history, historyLoading, latestAssistantReplyKey, presentationHosts, isReadOnly]);

  function jumpToLatestReply() {
    const viewport = presentationHosts?.messages?.parentElement ?? playMessagesHostRef.current?.parentElement;
    if (!viewport) return;
    followsLatestRef.current = true;
    positionLatestAssistantReply(viewport);
    setNewReplyAvailable(false);
  }

  latestRef.current.fenceKey = requestFenceKey;
  latestRef.current.presentationFenceKey = askPresentationFenceKey;
  latestRef.current.buildPlacementFenceKey = buildPlacementFenceKey;
  latestRef.current.buildPlacementEpoch = buildPlacementEpoch;
  latestRef.current.buildPlacementBridge = buildMode?.composeBridge;
  latestRef.current.proposalFenceKey = proposalFenceKey;
  latestRef.current.threadId = activeThread?.threadId ?? null;
  latestRef.current.providerThreadId = agent.activeThread?.threadId ?? null;
  latestRef.current.savePlanEnabled = savePlanEnabled;
  latestRef.current.saveInFlight = saveInFlight;
  latestRef.current.savedDirty = savedDirty;
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

  useEffect(() => {
    if (!agent.paneState.isOpen) return;
    let active = true;
    setSavedPlanVersion({ key: committedPlanVersionKey, revisionN: null, status: "checking" });
    if (!scopeMatches || !verifiedWorldId || !documentId || !isPositiveRevision(revision)) {
      setSavedPlanVersion({ key: committedPlanVersionKey, revisionN: null, status: "unavailable" });
      return () => { active = false; };
    }

    void getWorldOwnedPlanCommittedRevision(documentId)
      .then((value: unknown) => {
        if (!active) return;
        const basis = readCommittedPlanBasis(value, verifiedWorldId, documentId, revision);
        setSavedPlanVersion({
          key: committedPlanVersionKey,
          revisionN: basis?.revision_n ?? null,
          status: basis ? "verified" : "unavailable",
        });
      })
      .catch(() => {
        if (active) setSavedPlanVersion({ key: committedPlanVersionKey, revisionN: null, status: "unavailable" });
      });

    return () => { active = false; };
  }, [agent.paneState.isOpen, committedPlanVersionKey, documentId, revision, scopeMatches, verifiedWorldId]);

  useLayoutEffect(() => {
    latestRef.current.mounted = true;
    return () => {
      latestRef.current.mounted = false;
      requestRef.current = null;
      newConversationRef.current = null;
      commandStatusRef.current = null;
      historyGenerationRef.current += 1;
      sourceReadEpochRef.current += 1;
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

  useEffect(() => {
    let active = true;
    setConversationActions([]);
    setConversationActionsError(null);
    const viewedId = history?.conversation_id;
    if (!scopeMatches || !verifiedWorldId || !viewedId) return () => { active = false; };
    void getWorldPlanConversationActions(verifiedWorldId, viewedId)
      .then((page) => {
        if (active && page.schema_version === "dmb_world_plan_action_conversation_projection_v1"
          && page.world_id === verifiedWorldId && page.conversation_id === viewedId) {
          setConversationActions(page.actions);
        }
      })
      .catch((reason: unknown) => {
        if (active) setConversationActionsError(reason instanceof Error ? reason.message : "Could not load World edit dialogue.");
      });
    return () => { active = false; };
  }, [scopeMatches, verifiedWorldId, history?.conversation_id, history?.pointer_revision]);

  useLayoutEffect(() => {
    proposalRequestRef.current = null;
    if (applyingReviewRef.current?.fenceKey !== proposalFenceKey) {
      applyingReviewRef.current = null;
      setApplyingTurnId(null);
    }
    editReviewRef.current = null;
    setComposing(false);
    setEditReview(null);
    setEditError(null);
  }, [proposalFenceKey]);

  const unresolvedPlanAskKey = pendingAsks.filter((item) => item.envelope
    && !isPendingAskFailureConfirmed(item)).map((item) => item.serialized).join("\u001f");
  const historyRequested = Boolean(isBuild && buildMode?.savedSource) || agent.paneState.isOpen || sending || newConversationSending
    || Boolean(sharedConversation?.pendingTurn) || Boolean(pendingPlayTurn)
    || pendingAsks.some(item => item.envelope && !isPendingAskFailureConfirmed(item))
    || pendingCommands.some(item => item.envelope) || Boolean(confirmedAskNoticeRef.current);

  useEffect(() => {
    let active = true;
    const generation = ++historyGenerationRef.current;
    const confirmedAskNotice = confirmedAskNoticeRef.current;
    const settleRefreshFailure = () => {
      if (!active || generation !== historyGenerationRef.current || !confirmedAskNotice
        || confirmedAskNoticeRef.current !== confirmedAskNotice) return;
      const notice = confirmedAskNotice.notice.replace(/Refreshing World history[^.]*\.|refreshing World history\./,
        "World history refresh failed. Refresh history to check this confirmed Ask.");
      confirmedAskNoticeRef.current = { ...confirmedAskNotice, notice };
      setConversationNotice((current) => current === confirmedAskNotice.notice ? notice : current);
    };
    const sameHistoryScope = historyReadScopeRef.current === scopeKey;
    historyReadScopeRef.current = scopeKey;
    if (!sameHistoryScope) {
      historySnapshotRef.current = null;
      setHistory(null);
    }
    setOlderLoading(false);
    setHistoryError(null);
    const reconcilingPendingPlay = sharedConversation?.pendingTurn?.surface === "play" || sharedConversation?.pendingTurn?.surface === "build";
    if (((!isReadOnly && (!scopeMatches || !documentId)) && !reconcilingPendingPlay)
      || verifiedWorldId !== worldId || (!visible && !reconcilingPendingPlay) || !historyRequested) {
      setHistoryLoading(false);
      return () => { active = false; };
    }

    const controller = new AbortController();
    setHistoryLoading(true);
    void getWorldAgentConversationHistory(verifiedWorldId, {
      limit: WORLD_HISTORY_PAGE_SIZE,
      includeTurnCorrelation: true,
      signal: controller.signal,
    })
      .then(async (page) => {
        if (!active || generation !== historyGenerationRef.current) return;
        const validState = isWorldConversationHistory(page)
          && page.world_id === verifiedWorldId
          && await areHistoryReceiptDigestsBound(page);
        if (!validState) {
          setHistoryError("The World conversation response did not match the selected World or contained an invalid Graph-context receipt. Refresh history before continuing.");
          settleRefreshFailure();
          return;
        }
        if (!active || generation !== historyGenerationRef.current) return;
        sharedConversation?.setPendingTurn((current) => current && current.surface !== "plan" && page.turns.some((turn) =>
          turn.turn_id === current.turnId && ["completed", "failed", "interrupted"].includes(turn.lifecycle_status)) ? null : current);
        const readOnlyConfirmed = pendingPlayTurn && await confirmedReadOnlyTurn(page, pendingPlayTurn);
        if (!active || generation !== historyGenerationRef.current) return;
        if (pendingPlayTurn && readOnlyConfirmed) {
          sharedConversation?.setPendingTurn(current => current?.turnId === pendingPlayTurn.request.turn_id ? null : current);
          try {
            const storedBytes = window.localStorage.getItem(pendingPlayTurn.storageKey);
            if (storedBytes === null || storedBytes === pendingPlayTurn.serialized) {
              if (storedBytes === pendingPlayTurn.serialized) window.localStorage.removeItem(pendingPlayTurn.storageKey);
              setPendingPlayTurn(null);
              setPendingPlayLoadError(null);
              if (pendingPlayTurn.request.primary_work.kind === "build") buildCompose.refresh();
            } else {
              setPendingPlayLoadError("The saved request changed. Review its recovery record before another turn.");
            }
          } catch (reason) {
            setPendingPlayLoadError(reason instanceof Error ? reason.message : "Could not clear the confirmed request.");
          }
        }
        const uncertainNotice = uncertainPlayNoticeRef.current;
        if (uncertainNotice && readOnlyConfirmed && pendingPlayTurn?.request.turn_id === uncertainNotice.turnId) {
          uncertainPlayNoticeRef.current = null;
          setError((current) => current === uncertainNotice.message ? null : current);
        }
        try {
          if (isReadOnly || !documentId || !scopeMatches) {
            historySnapshotRef.current = page;
            setHistory(page);
            setHistoryLoading(false);
            return;
          }
          const reconciliation = await reconcileCompletedPendingAsks(
            page,
            verifiedWorldId,
            documentId,
            () => active && generation === historyGenerationRef.current,
          );
          if (!active || generation !== historyGenerationRef.current) return;
          if (reconciliation.refreshPendingList) refreshPendingAskList();
          if (reconciliation.storageError) setPendingAskLoadError(reconciliation.storageError);
          const terminalFailures = await classifyTerminalFailedPendingAsks(
            page,
            verifiedWorldId,
            documentId,
            () => active && generation === historyGenerationRef.current,
          );
          if (!active || generation !== historyGenerationRef.current) return;
          setConfirmedTerminalFailureAsks(terminalFailures);
          // Durable turn IDs differ from client request IDs. Only the exact
          // bound terminal envelope may release its client-side pending lock.
          const settledClientIds = new Set([
            ...reconciliation.confirmedTurnIds,
            ...terminalFailures.filter((failure) =>
              window.localStorage.getItem(failure.storageKey) === failure.serialized)
              .map((failure) => failure.clientTurnId),
          ]);
          sharedConversation?.setPendingTurn((current) => current?.surface === "plan"
            && settledClientIds.has(current.turnId) ? null : current);
          const uncertain = uncertainPlanNoticeRef.current;
          if (uncertain) {
            const failureConfirmed = readPendingAsks(verifiedWorldId, documentId).some((item) =>
              item.envelope?.request.turn_id === uncertain.turnId
              && terminalFailures.some((failure) => failure.storageKey === item.storageKey
                && failure.serialized === item.serialized));
            if (failureConfirmed || reconciliation.confirmedTurnIds.includes(uncertain.turnId)) {
              uncertainPlanNoticeRef.current = null;
              setSubmittedMessage((current) => current?.id === uncertain.turnId ? null : current);
              setError((current) => current === uncertain.message ? null : current);
            }
          }
        } catch (reason) {
          setPendingAskLoadError(reason instanceof Error
            ? reason.message
            : "Browser storage is unavailable for pending Ask recovery.");
        }
        const matchingNotice = confirmedAskNotice && confirmedAskNoticeRef.current === confirmedAskNotice
          && await confirmedAskHistoryMatches(page, confirmedAskNotice.stored,
            confirmedAskNotice.conversationId, confirmedAskNotice.answer);
        if (!active || generation !== historyGenerationRef.current) return;
        const reset = confirmedResetRef.current;
        if (reset?.worldId === verifiedWorldId && (page.pointer_revision < reset.pointerRevision
          || (page.pointer_revision === reset.pointerRevision && page.conversation_id !== reset.conversationId))) {
          setHistoryError("The refreshed transcript has not reached the confirmed new conversation. Refresh history again.");
          return;
        }
        historySnapshotRef.current = page;
        setHistory(page);
        if (matchingNotice && confirmedAskNotice
          && confirmedAskNoticeRef.current === confirmedAskNotice) {
          const settledNotice = confirmedAskNotice.notice.replace(/Refreshing World history[^.]*\.|refreshing World history\.|World history refresh failed\. Refresh history to check this confirmed Ask\./,
            "World history refreshed.");
          confirmedAskNoticeRef.current = null;
          setSubmittedMessage((current) => current?.kind === "discuss"
            && current.id === confirmedAskNotice.stored.envelope?.request.turn_id ? null : current);
          setConversationNotice((current) => current === confirmedAskNotice.notice ? settledNotice : current);
        }
      })
      .catch((reason: unknown) => {
        if (active && generation === historyGenerationRef.current) {
          setHistoryError(localOperatorCredentialFailure(reason, "refresh World history")
            ?? (reason instanceof Error ? reason.message : "Could not load the World conversation."));
          settleRefreshFailure();
        }
      })
      .finally(() => {
        if (active && generation === historyGenerationRef.current) setHistoryLoading(false);
      });
    return () => { active = false; controller.abort(); olderHistoryReadRef.current?.abort(); };
  }, [historyRequested, scopeKey, scopeMatches, verifiedWorldId, documentId, historyRefreshNonce, sharedConversation?.historyRefreshNonce,
    sharedConversation?.pendingTurn?.surface, pendingPlayTurn?.serialized, isReadOnly, visible]);

  useEffect(() => {
    if (verifiedWorldId !== worldId || !sharedConversation?.pendingTurn) return;
    const timer = window.setInterval(() => setHistoryRefreshNonce((current) => current + 1), 3000);
    return () => window.clearInterval(timer);
  }, [verifiedWorldId, worldId, sharedConversation?.pendingTurn]);

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

  // Recovery reads history only. Absence from a page never proves failure or permits reposting.
  useEffect(() => {
    if (!visible || !scopeMatches || !verifiedWorldId || !documentId || sending || !unresolvedPlanAskKey) return;
    let attempts = 0;
    let timer: number | undefined;
    const check = () => {
      if (document.visibilityState === "hidden" || !navigator.onLine) return;
      setHistoryRefreshNonce((current) => current + 1);
      attempts += 1;
      if (attempts < 10) timer = window.setTimeout(check, Math.min(3000 * 2 ** (attempts - 1), 30000));
    };
    const resume = () => {
      if (document.visibilityState === "hidden" || !navigator.onLine) return;
      if (timer !== undefined) window.clearTimeout(timer);
      attempts = 0;
      check();
    };
    timer = window.setTimeout(check, 1000);
    window.addEventListener("online", resume);
    window.addEventListener("focus", resume);
    document.addEventListener("visibilitychange", resume);
    return () => {
      if (timer !== undefined) window.clearTimeout(timer);
      window.removeEventListener("online", resume);
      window.removeEventListener("focus", resume);
      document.removeEventListener("visibilitychange", resume);
    };
  }, [visible, scopeMatches, verifiedWorldId, documentId, sending, unresolvedPlanAskKey]);

  useEffect(() => {
    if (!verifiedWorldId) return;
    try {
      const stored = readPendingPlayTurn(verifiedWorldId);
      setPendingPlayTurn(stored);
      setPendingPlayLoadError(null);
      setPendingPlayLoadedWorldId(verifiedWorldId);
      if (stored) sharedConversation?.setPendingTurn((current) => current ?? { surface: stored.request.surface.surface_id, turnId: stored.request.turn_id });
    } catch (reason) {
      setPendingPlayLoadError(reason instanceof Error ? reason.message : "Saved Play request recovery is unavailable.");
      setPendingPlayLoadedWorldId(verifiedWorldId);
    }
  }, [verifiedWorldId, sharedConversation?.setPendingTurn]);

  useEffect(() => {
    if (!verifiedWorldId) {
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
  }, [verifiedWorldId]);

  useLayoutEffect(() => {
    const pending = proposalRequestRef.current;
    if (!isReadOnly && scopeMatches && pending && latestRef.current.providerThreadId !== pending.providerThreadId) {
      proposalRequestRef.current = null;
      setComposing(false);
    }
    const review = editReviewRef.current;
    if (!isReadOnly && scopeMatches && review && activeThread && activeThread.threadId !== review.threadId) {
      editReviewRef.current = null;
      setEditReview(null);
    }
  }, [activeThread?.threadId, agent.activeThread?.threadId, isReadOnly, scopeMatches]);

  useLayoutEffect(() => {
    requestRef.current = null;
    newConversationRef.current = null;
    commandStatusRef.current = null;
    setCommandStatusChecking(false);
    setBlockedResolution(null);
    setConfirmedTerminalFailureAsks([]);
    uncertainPlanNoticeRef.current = null;
    resolutionGenerationRef.current += 1;
    historyGenerationRef.current += 1;
    historySnapshotRef.current = null;
    setOlderLoading(false);
    if (legacyHistoryRef.current?.scopeKey !== scopeKey) legacyHistoryRef.current = null;
    setSending(false);
    setNewConversationSending(false);
    setTraceVisible(false);
    if (!sharedConversation) setComposerMessage("");
    setComposerIntent("discuss");
    setError(null);
    setConversationNotice(null);
    confirmedAskNoticeRef.current = null;
  }, [sharedConversation?.worldId ?? scopeKey]);

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
    if (!verifiedWorldId) return;
    try {
      setPendingCommands(readPendingNewConversations(verifiedWorldId));
      setPendingCommandLoadError(null);
    } catch (reason) {
      setPendingCommandLoadError(reason instanceof Error
        ? reason.message
        : "Browser storage is unavailable for New Conversation recovery.");
    }
  }

  async function checkNewConversationCommand(stored: StoredPendingNewConversation) {
    const envelope = stored.envelope;
    if (!envelope || verifiedWorldId !== envelope.worldId
      || commandStatusRef.current !== null || newConversationRef.current !== null) return;
    const token = Symbol("command-status");
    commandStatusRef.current = token;
    setCommandStatusChecking(true);
    const stillCurrent = () => latestRef.current.mounted
      && latestRef.current.verifiedWorldId === envelope.worldId
      && commandStatusRef.current === token;
    try {
      const raw = window.localStorage.getItem(stored.storageKey);
      if (raw === null || JSON.stringify(parsePendingNewConversation(stored.storageKey, raw, envelope.worldId).envelope) !== JSON.stringify(envelope)) {
        throw new Error("The saved command changed. Its recovery record was retained.");
      }
      if (window.localStorage.getItem(commandResolutionKey(envelope)) !== null) {
        setNewConversationError("A resolution identity is already saved. Check its original resolution record; no request was resent.");
        return;
      }
      const response = await getWorldAgentNewConversationStatus(envelope.worldId, envelope.request);
      const confirmed = await confirmedNewConversationStatus(response, envelope.worldId, envelope.request);
      if (!stillCurrent()) return;
      if (!confirmed) {
        setNewConversationError("This exact command has no verified confirmation. Its recovery record remains saved; no command was resent.");
        return;
      }
      if (window.localStorage.getItem(stored.storageKey) !== raw) {
        setNewConversationError("The saved command changed while status was checked. Its recovery record was retained.");
        refreshPendingCommandList();
        return;
      }
      window.localStorage.removeItem(stored.storageKey);
      refreshPendingCommandList();
      setNewConversationError(null);
      setConversationNotice("The original New Conversation command is confirmed. Refreshing server history.");
      setHistoryRefreshNonce((current) => current + 1);
    } catch (reason) {
      if (stillCurrent()) setNewConversationError(reason instanceof Error ? reason.message : "Status is unavailable; the saved command was retained.");
    } finally {
      if (commandStatusRef.current === token) {
        commandStatusRef.current = null;
        setCommandStatusChecking(false);
      }
    }
  }

  function settleCommandResolution(value: NonNullable<typeof blockedResolution>) {
    if (!latestRef.current.mounted || resolutionGenerationRef.current !== value.generation
      || latestRef.current.verifiedWorldId !== value.envelope.worldId) return;
    try {
      if (window.localStorage.getItem(value.originalKey) !== value.originalBytes
        || window.localStorage.getItem(value.resolutionKey) !== value.resolutionBytes) {
        throw new Error("Recovery bytes changed. Both records were retained.");
      }
      // Clear one captured envelope atomically; retain the operation identity for exact readback.
      // Two independent localStorage removals cannot provide atomic recovery on quota/access failure.
      window.localStorage.removeItem(value.originalKey);
      refreshPendingCommandList();
      setBlockedResolution(null);
      setNewConversationError(null);
      setConversationNotice(value.record.outcome === "submitted_binding_blocked"
        ? "The submitted request was blocked by an occupied command ID. Its successful occupant and all history remain intact."
        : "The saved request is resolved. Refreshing history; starting a new conversation remains a separate action.");
      setHistoryRefreshNonce((current) => current + 1);
    } catch (reason) {
      setNewConversationError(reason instanceof Error ? reason.message : "Storage settlement failed; recovery records remain saved.");
      refreshPendingCommandList();
    }
  }

  async function resolveSavedCommand(stored: StoredPendingNewConversation, mode: "resolve" | "lookup") {
    const envelope = stored.envelope;
    if (!envelope || verifiedWorldId !== envelope.worldId
      || commandStatusRef.current !== null || newConversationRef.current !== null) return;
    const token = Symbol("command-resolution");
    const generation = ++resolutionGenerationRef.current;
    setBlockedResolution(null);
    commandStatusRef.current = token;
    setCommandStatusChecking(true);
    const current = () => latestRef.current.mounted && commandStatusRef.current === token
      && latestRef.current.verifiedWorldId === envelope.worldId;
    try {
      const originalBytes = window.localStorage.getItem(stored.storageKey);
      if (originalBytes === null || JSON.stringify(parsePendingNewConversation(stored.storageKey, originalBytes, envelope.worldId).envelope) !== JSON.stringify(envelope)) {
        throw new Error("The original recovery record changed; nothing was dispatched.");
      }
      const resolutionKey = commandResolutionKey(envelope);
      let resolutionBytes = window.localStorage.getItem(resolutionKey);
      if (resolutionBytes === null) {
        if (mode === "lookup") throw new Error("No resolution identity is saved. Resolve this request explicitly before checking its record.");
        const pointer = historySnapshotRef.current;
        if (!pointer || historyLoading || pointer.world_id !== envelope.worldId) throw new Error("Refresh canonical history before resolving the request.");
        const request: WorldCommandResolutionRequestV1 = {
          schema: "dmb_agent_new_conversation_resolution_request_v1", resolution_operation_id: crypto.randomUUID(),
          original_command: { world_id: envelope.worldId, command_id: envelope.request.command_id,
            expected_pointer_revision: envelope.request.expected_pointer_revision, expected_active_conversation_id: envelope.request.expected_active_conversation_id },
          expected_current_pointer_revision: pointer.pointer_revision, expected_current_active_conversation_id: pointer.active_conversation_id,
        };
        const saved: SavedCommandResolution = { schema: "dmb_world_saved_command_resolution_v1", worldId: envelope.worldId,
          documentId: envelope.documentId, originalKey: stored.storageKey, originalBytes, request };
        resolutionBytes = JSON.stringify(saved);
        window.localStorage.setItem(resolutionKey, resolutionBytes);
        if (window.localStorage.getItem(resolutionKey) !== resolutionBytes) throw new Error("Resolution identity could not be saved; nothing was dispatched.");
      }
      const saved = JSON.parse(resolutionBytes) as SavedCommandResolution;
      if (!hasExactKeys(saved, ["schema", "worldId", "documentId", "originalKey", "originalBytes", "request"])
        || saved.schema !== "dmb_world_saved_command_resolution_v1" || saved.worldId !== envelope.worldId || saved.documentId !== envelope.documentId
        || saved.originalKey !== stored.storageKey || saved.originalBytes !== originalBytes
        || !hasExactKeys(saved.request, ["schema", "resolution_operation_id", "original_command", "expected_current_pointer_revision", "expected_current_active_conversation_id"])
        || saved.request.schema !== "dmb_agent_new_conversation_resolution_request_v1" || !commandUuid(saved.request.resolution_operation_id)
        || canonicalJson(saved.request.original_command) !== canonicalJson({ world_id: envelope.worldId, command_id: envelope.request.command_id,
          expected_pointer_revision: envelope.request.expected_pointer_revision, expected_active_conversation_id: envelope.request.expected_active_conversation_id })
        || !Number.isSafeInteger(saved.request.expected_current_pointer_revision) || saved.request.expected_current_pointer_revision < 0
        || !(saved.request.expected_current_active_conversation_id === null || typeof saved.request.expected_current_active_conversation_id === "string")) {
        throw new Error("The saved resolution identity is invalid or differs from this envelope. It was retained.");
      }
      const response = mode === "lookup" ? await getWorldCommandResolution(saved.request) : await postWorldCommandResolution(saved.request);
      const record = await verifiedCommandResolution(response, saved.request);
      if (!current()) return;
      if (!record) throw new Error("No exact terminal resolution was verified. Recovery records remain saved; no fresh command was sent.");
      const value = { resolutionKey, resolutionBytes, originalKey: stored.storageKey, originalBytes, envelope, record, generation };
      if (record.outcome === "submitted_binding_blocked") {
        setBlockedResolution(value);
        setNewConversationError(null);
      } else settleCommandResolution(value);
    } catch (reason) {
      if (current()) setNewConversationError(reason instanceof Error ? reason.message : "Resolution unavailable. Its saved operation identity remains intact.");
    } finally {
      if (commandStatusRef.current === token) { commandStatusRef.current = null; setCommandStatusChecking(false); }
    }
  }

  async function sendNewConversationCommand(stored: StoredPendingNewConversation) {
    const envelope = stored.envelope;
    if (!envelope || verifiedWorldId !== envelope.worldId
      || newConversationRef.current !== null) return;
    const token = Symbol("world-agent-new-conversation");
    newConversationRef.current = token;
    setNewConversationSending(true);
    setNewConversationError(null);
    setConversationNotice(null);
    const stillCurrent = () => latestRef.current.mounted
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
      if (response.active_conversation_id !== response.conversation_id
        || response.conversation_id === envelope.request.expected_active_conversation_id
        || response.pointer_revision <= envelope.request.expected_pointer_revision) {
        throw new Error("The New Conversation response did not confirm an active fresh conversation.");
      }
      const freshReset = confirmedResetRef.current?.commandId !== envelope.request.command_id
        && historySnapshotRef.current?.conversation_id !== response.conversation_id;
      confirmedResetRef.current = { commandId: envelope.request.command_id, worldId: envelope.worldId, conversationId: response.conversation_id,
        pointerRevision: response.pointer_revision };
      if (freshReset) {
        historyGenerationRef.current += 1;
        historySnapshotRef.current = null;
        setHistory(null);
        setSubmittedMessage(null);
        setContinuationOfActionId(null);
        setConversationActions([]);
        editReviewRef.current = null;
        setEditReview(null);
        if (namespace && documentId && activeThread?.worldPlanProposalHistory === WORLD_PLAN_LOCAL_PROPOSAL_HISTORY) {
          setRetiredProposalTurns((current) => ({ scopeKey,
            turns: [...activeThread.turns.filter((turn) => turn.planEdit), ...(current?.scopeKey === scopeKey ? current.turns : [])],
            positions: [...(proposalOrderForDisplay?.positions ?? []), ...(current?.scopeKey === scopeKey ? current.positions : [])] }));
          agent.updateThread({ ...createAgentInteractionThread(namespace, null, "plan", "hermes", "New conversation", documentId),
            worldPlanProposalHistory: WORLD_PLAN_LOCAL_PROPOSAL_HISTORY });
        }
      }
      try {
        window.localStorage.removeItem(stored.storageKey);
        refreshPendingCommandList();
      } catch (reason) {
        setPendingCommandLoadError(reason instanceof Error
          ? reason.message
          : "The command succeeded, but its local recovery envelope could not be cleared. Retrying remains safe.");
      }
      setConversationNotice(null);
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
      commandStatusRef.current = null;
        setNewConversationSending(false);
      }
    }
  }

  function startNewConversation() {
    const pointer = historySnapshotRef.current;
    if (!verifiedWorldId || !pointer
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
      setError(null);
      setNewConversationError(null);
      void sendNewConversationCommand({ storageKey, envelope, error: null });
    } catch (reason) {
      setNewConversationError(reason instanceof Error
        ? `The command was not sent because its recovery envelope could not be saved. ${reason.message}`
        : "The command was not sent because browser storage is unavailable.");
    }
  }

  function openConnectionSettings() {
    setSettingsOpen(true);
    const options = presentationHosts?.header?.closest("details") ?? connectionOptionsRef.current;
    if (options instanceof HTMLDetailsElement) options.open = true;
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

  async function sendPendingAsk(stored: StoredPendingAsk, initialDispatch = false, composerSnapshotAtSubmit?: string, composerGenerationAtSubmit?: number) {
    const envelope = stored.envelope;
    if (!envelope || !scopeMatches || verifiedWorldId !== envelope.origin.worldId
      || documentId !== envelope.origin.documentId || requestRef.current) return;
    if (!initialDispatch) {
      setConversationNotice("This Ask is not reposted from browser recovery. Refresh World history to check whether it completed before taking another action.");
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
      const receiptBasis = validation.value.planReceiptBasis;
      const receiptMatchesOrigin = !envelope.request.plan_context_policy || receiptBasis !== null
        && receiptBasis.world_id === origin.worldId && receiptBasis.document_id === origin.documentId
        && receiptBasis.object_revision === origin.objectRevision && receiptBasis.work_revision_id === origin.workRevisionId
        && receiptBasis.revision_n === origin.revisionN && receiptBasis.content_sha256 === origin.contentSha256;
      if (!validation.value.conversationId || !responseBasisMatchesOrigin || !receiptMatchesOrigin) {
        throw new Error("The durable Ask result did not identify its original World conversation and committed basis. The saved request remains available for exact recovery.");
      }

      const clearResult = clearPendingAskIfUnchanged(stored);
      dispatchPendingAskSettlement(stored, clearResult);
      sharedConversation?.setPendingTurn((current) => current?.turnId === envelope.request.turn_id ? null : current);
      sharedConversation?.setHistoryRefreshNonce((current) => current + 1);
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
        const notice = `The server confirmed this Ask for its original ${originalContext} at committed Plan object revision ${envelope.origin.objectRevision}. Refreshing World history with that submitted provenance.`;
        confirmedAskNoticeRef.current = { stored, conversationId: validation.value.conversationId, answer: validation.value.answer, notice };
        setConversationNotice(notice);
      } else {
        const notice = belongsToPreviousConversation
          ? `The server confirmed this Ask under conversation ${validation.value.conversationId}. It was not inserted into the currently active conversation; refreshing World history.`
          : "The server confirmed this Ask. Refreshing World history.";
        confirmedAskNoticeRef.current = { stored, conversationId: validation.value.conversationId, answer: validation.value.answer, notice };
        setConversationNotice(notice);
      }
    } catch (reason) {
      if (isCurrent() && composerSnapshotAtSubmit !== undefined && composerGenerationAtSubmit !== undefined
        && latestRef.current.presentationFenceKey === submittedPresentationFenceKey
        && historySnapshotRef.current?.pointer_revision === envelope.origin.pointerRevision
        && historySnapshotRef.current?.active_conversation_id === envelope.origin.conversationId) {
        restoreSubmittedDraft(composerSnapshotAtSubmit, composerGenerationAtSubmit);
      }
      const definitivePreDispatchFailure = graphContextPreDispatchFailure(reason);
      if (definitivePreDispatchFailure) {
        const clearResult = clearPendingAskIfUnchanged(stored);
        if (clearResult.kind === "cleared") dispatchPendingAskSettlement(stored, clearResult);
        if (isCurrent()) {
          if (clearResult.kind === "unavailable") setPendingAskLoadError(clearResult.message);
          else if (clearResult.kind === "changed") refreshPendingAskList();
          setError(definitivePreDispatchFailure);
        }
      } else if (isCurrent()) {
        const graphNotice = localOperatorCredentialFailure(reason, "restore authorization so Buddy can check this turn without resending it")
          ?? `The outcome of this Ask is uncertain. Buddy is checking saved history automatically; this message will not be resent. ${reason instanceof Error ? reason.message : ""}`;
        uncertainPlanNoticeRef.current = { turnId: envelope.request.turn_id, message: graphNotice };
        setError(graphNotice);
      }
    } finally {
      if (requestRef.current?.token === token) {
        requestRef.current = null;
        setSending(false);
      }
    }
  }

  async function submit(event: Pick<FormEvent<HTMLFormElement>, "preventDefault">, intent = composerIntent, questionOverride?: string) {
    event.preventDefault();
    if (questionOverride === undefined) setRetryPresentationOrigin(null);
    const composerSnapshotAtSubmit = questionOverride ?? composerMessage;
    const message = composerSnapshotAtSubmit.trim();
    const pointerSnapshot = historySnapshotRef.current;
    const targetAtSubmit = playableTarget;
    const targetBasisAtSubmit = playableTargetBasis;
    if (intent !== "discuss" || !planReady || !scopeMatches || !namespace || !documentId || !surfaceInstanceId
      || !isPositiveRevision(revision) || saveInFlight || !message || sending || requestRef.current
      || sharedConversation?.pendingTurn
      || historyLoading || historyError || !pointerSnapshot || playableTargetStale
      || (targetAtSubmit && (!targetBasisAtSubmit || targetBasisAtSubmit.revision !== revision))) return;

    const startingFenceKey = requestFenceKey;
    const submittedClientThreadId = crypto.randomUUID();
    const submittedTurnId = crypto.randomUUID();
    const composerGenerationAtSubmit = composerEditGenerationRef.current;
    const submittedPresentationFenceKey = askPresentationFenceKey;
    setSubmittedMessage({ id: submittedTurnId, scopeKey, conversationId: pointerSnapshot.conversation_id,
      pointerRevision: pointerSnapshot.pointer_revision, message, kind: "discuss" });
    if (!sharedConversation && composerEditGenerationRef.current === composerGenerationAtSubmit) setComposerMessage((current) => current === composerSnapshotAtSubmit ? "" : current);
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
        client_thread_id: submittedClientThreadId,
        turn_id: submittedTurnId,
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
      refreshPendingAskList();
      sharedConversation?.setPendingTurn({ surface: "plan", turnId: request.turn_id });
      if (sharedConversation && composerEditGenerationRef.current === composerGenerationAtSubmit) setComposerMessage((current) => current === composerSnapshotAtSubmit ? "" : current);
      requestRef.current = null;
      setSending(false);
      await sendPendingAsk({ storageKey, serialized, envelope, error: null }, true, composerSnapshotAtSubmit, composerGenerationAtSubmit);
    } catch (reason) {
      if (requestRef.current?.token === preparationToken) {
        if (latestRef.current.presentationFenceKey === submittedPresentationFenceKey) restoreSubmittedDraft(composerSnapshotAtSubmit, composerGenerationAtSubmit);
        requestRef.current = null;
        setSending(false);
        setError(reason instanceof Error ? reason.message : "The Ask could not be prepared.");
      }
    }
  }

  function clearSavedPlayTurn(stored: StoredPendingPlayTurn): boolean {
    try {
      const current = window.localStorage.getItem(stored.storageKey);
      const terminal = sharedConversation?.history?.turns.some((turn) => turn.turn_id === stored.request.turn_id
        && ["completed", "failed", "interrupted"].includes(turn.lifecycle_status));
      if (current !== stored.serialized && !(current === null && terminal)) {
        throw new Error("The saved request changed. Its recovery record was retained.");
      }
      if (current === stored.serialized) window.localStorage.removeItem(stored.storageKey);
      setPendingPlayTurn(null);
      setPendingPlayLoadError(null);
      return true;
    } catch (reason) {
      setPendingPlayLoadError(reason instanceof Error ? reason.message : "Could not clear the saved Play request.");
      return false;
    }
  }

  async function dispatchSavedPlayTurn(stored: StoredPendingPlayTurn) {
    const request = stored.request;
    if (verifiedWorldId !== request.owner_scope.world_id || requestRef.current || sending || buildCompose.busy) return;
    const token = Symbol("world-readonly-turn");
    const constructionEpoch=latestRef.current.buildPlacementEpoch;
    let constructionRetired=false;
    requestRef.current = { token, scopeKey: request.owner_scope.world_id, fenceKey: JSON.stringify(request.primary_work) };
    sharedConversation?.setPendingTurn({ surface: request.surface.surface_id, turnId: request.turn_id });
    setSending(true);
    setError(null);
    try {
      setSubmittedMessage({ id: request.turn_id, scopeKey,
        conversationId: historySnapshotRef.current?.conversation_id ?? null,
        pointerRevision: historySnapshotRef.current?.pointer_revision ?? null,
        message: request.message, kind: "discuss" });
      void worldTurnIdempotencyKey(request.owner_scope.world_id, request.turn_id).then(key => {
        setSubmittedMessage(current => current?.id === request.turn_id ? { ...current, idempotencyKey: key } : current);
      });
      const response = await (request.primary_work.kind === "build"
        ? postWorldBuildAgentTurn(request as WorldBuildAgentTurnRequestV1, progress=>{
            if(latestRef.current.buildPlacementEpoch!==constructionEpoch)constructionRetired=true;
            if(!constructionRetired&&requestRef.current?.token===token&&latestRef.current.mounted)buildCompose.observeConstruction(progress);
          })
        : postWorldPlayAgentTurn(request as WorldPlayAgentTurnRequestV1));
      if (requestRef.current?.token !== token || !latestRef.current.mounted) return;
      const mixed = response.schema === 'dmb_agent_rules_turn_response_v1' || response.schema === 'dmb_agent_play_rules_turn_response_v1';
      const nativePlay = request.primary_work.kind === 'run' && request.graph_request.mode === 'world';
      const sourcePlay = request.primary_work.kind === 'run' && request.graph_request.mode === 'none';
      const expectedSchema = mixed ? sourcePlay ? 'dmb_agent_play_rules_turn_response_v1' : 'dmb_agent_rules_turn_response_v1'
        : nativePlay ? 'dmb_agent_play_graph_turn_response_v1' : sourcePlay ? 'dmb_agent_play_source_turn_response_v1' : 'dmb_agent_turn_response_v1';
      const contextKeys = [...(mixed ? ['rules_context'] : nativePlay ? ['play_context'] : request.graph_request.mode === 'world' ? ['knowledge_context'] : []),
        ...(sourcePlay ? ['play_source_context'] : [])];
      if (!hasExactKeys(response, ['schema', 'client_thread_id', 'turn_id', 'surface', 'owner_scope', 'primary_work',
        'client_work_state_reported', 'graph', 'conversation', 'answer', ...contextKeys]) || response.schema !== expectedSchema) {
        throw new Error('The reply did not match the current surface response contract. Its recovery record was retained.');
      }
      if (mixed && (typeof response.conversation.conversation_id !== 'string'
        || !isRulesAnswerContext(response.rules_context, response.answer.text, request.owner_scope.world_id,
        base => request.primary_work.kind === 'build' ? isBuildKnowledgeContext(base, request.owner_scope.world_id)
          : isWorldPlayContextProjection(base, isWorldPlanGraphExecution, request as WorldPlayAgentTurnRequestV1),
        typeof response.conversation.conversation_id === 'string' ? { conversationId: response.conversation.conversation_id } : undefined,
        c => isRulesUnclaimedContext(c, request.owner_scope.world_id, request))
        || !await rulesAnswerDigestsBound(response.rules_context, response.answer.text ?? '')
        || response.answer.graph_grounded !== response.rules_context.accepted_binding.graph_used
        || response.answer.status !== 'ok' || response.answer.code !== null || response.answer.message !== null)) {
        throw new Error('The Rules reply did not match its accepted answer and sources.');
      }
      if (!["dmb_agent_turn_response_v1", "dmb_agent_turn_response_v2", "dmb_agent_play_graph_turn_response_v1", 'dmb_agent_rules_turn_response_v1', 'dmb_agent_play_source_turn_response_v1', 'dmb_agent_play_rules_turn_response_v1'].includes(response.schema)
        || response.client_thread_id !== request.client_thread_id || response.turn_id !== request.turn_id
        || response.surface.status !== "resolved" || response.surface.surface_id !== request.surface.surface_id || response.surface.instance_id !== request.surface.instance_id
        || response.conversation.client_thread_id !== request.client_thread_id || response.conversation.turn_id !== request.turn_id
        || response.owner_scope.status !== "resolved"
        || response.owner_scope.kind !== "world" || response.owner_scope.owner_id !== request.owner_scope.world_id
        || response.primary_work.status !== "resolved"
        || response.primary_work.kind !== request.primary_work.kind || response.primary_work.object_id !== request.primary_work.object_id
        || response.primary_work.expected_revision !== request.primary_work.expected_revision
        || response.primary_work.revision_used !== request.primary_work.expected_revision
        || response.client_work_state_reported !== request.client_work_state
        || !matchesPlayGraphResponse(response.graph, request)) {
        throw new Error("The reply did not match the saved request. Check World history before continuing.");
      }
      if (request.primary_work.kind === "build" && request.graph_request.mode === "world") {
        const context = mixed ? response.rules_context.base_context : "knowledge_context" in response ? response.knowledge_context : undefined;
        const unclaimed = mixed ? response.rules_context.unclaimed_context : null;
        const receipt = unclaimed?.receipt;
        if (unclaimed) {
          if (!isRulesUnclaimedContext(unclaimed, request.owner_scope.world_id, request)
            || !receipt || !await isReceiptDigestBound(receipt)
            || receipt.graph_authority.native_world_id !== response.graph.world_id
            || receipt.graph_authority.graph_revision !== response.graph.revision_id) throw new Error("The unclaimed reply did not match the saved Build source.");
        } else if (!isBuildKnowledgeContext(context, request.owner_scope.world_id)
          || !await isReceiptDigestBound(context.receipt)
          || context.receipt.source_basis.document_id !== request.primary_work.object_id
          || context.receipt.source_basis.registry_revision !== request.primary_work.expected_revision
          || context.receipt.source_basis.content_sha256 !== request.primary_work.expected_content_sha256
          || context.receipt.graph_authority.native_world_id !== response.graph.world_id
          || context.receipt.graph_authority.graph_revision !== response.graph.revision_id) {
          throw new Error("The reply did not match the saved Build source and World Graph. Check World history before continuing.");
        }
      }
      if (sourcePlay && (!('play_source_context' in response)
        || !isPlaySourceContext(response.play_source_context,request as WorldPlayAgentTurnRequestV1)
        || !await playSourceContextDigestBound(response.play_source_context)
        || response.answer.graph_grounded || (mixed && response.rules_context.accepted_binding.base_disposition !== 'absent'))) {
        throw new Error('The reply did not match the saved Run edition and scene. Its recovery record was retained.');
      }
      if (request.primary_work.kind === "run" && request.graph_request.mode === "world") {
        const candidate = mixed ? response.rules_context.base_context : "play_context" in response ? response.play_context : undefined;
        const context = isWorldPlayContextProjection(candidate, isWorldPlanGraphExecution, request as WorldPlayAgentTurnRequestV1) ? candidate : null;
        const unclaimed = mixed ? response.rules_context.unclaimed_context : null;
        const receipt = unclaimed?.receipt ?? context?.receipt;
        if (!(unclaimed ? isRulesUnclaimedContext(unclaimed, request.owner_scope.world_id, request)
            : context !== null)
          || !receipt || !await isReceiptDigestBound(receipt)
          || receipt.graph_authority.native_world_id !== response.graph.world_id
          || receipt.graph_authority.graph_revision !== response.graph.revision_id
          || (!mixed && response.answer.text !== context!.completion!.answer_segments.map(s => s.text).join("\n"))
          || response.answer.status !== 'ok' || response.answer.code !== null || response.answer.message !== null
          || response.answer.graph_grounded !== (context?.completion?.answer_basis.includes('world_graph') ?? false)) {
          throw new Error("The reply did not match the saved Run edition, scene and World Graph. Its recovery record was retained.");
        }
      }
      if (requestRef.current?.token !== token || !latestRef.current.mounted) return;
      if (clearSavedPlayTurn(stored)) sharedConversation?.setPendingTurn((current) => current?.turnId === request.turn_id ? null : current);
      sharedConversation?.setHistoryRefreshNonce((current) => current + 1);
    } catch (reason) {
      if (requestRef.current?.token !== token || !latestRef.current.mounted) return;
      const terminalMatches = sharedConversation?.history && await confirmedReadOnlyTurn(sharedConversation.history, stored);
      if (requestRef.current?.token !== token || !latestRef.current.mounted) return;
      if (terminalMatches && sharedConversation) {
        if (clearSavedPlayTurn(stored)) sharedConversation.setPendingTurn((current) => current?.turnId === request.turn_id ? null : current);
        return;
      }
      const rejectedBeforeDispatch = reason instanceof LiveApiError
        && reason.code !== "local_graph_session_changed"
        && (["play_context_unavailable", "world_owner_unverified", "build_source_unavailable", "build_editor_context_changed"].includes(reason.code ?? "")
          || reason.status === 401 || reason.status === 403);
      if (rejectedBeforeDispatch) {
        if (clearSavedPlayTurn(stored)) {
          sharedConversation?.setPendingTurn((current) => current?.turnId === request.turn_id ? null : current);
          setSubmittedMessage(current => current?.id === request.turn_id ? null : current);
          setComposerDrafts((drafts) => {
            const key = `${request.surface.surface_id}:${request.primary_work.object_id}`;
            return drafts[key] ? drafts : { ...drafts, [key]: request.message };
          });
        }
      }
      const graphFailure = reason instanceof LiveApiError
        && ["graph_unavailable", "native_binding_invalid", "graph_revision_unavailable", "graph_read_failed"].includes(reason.code ?? "");
      const notice = rejectedBeforeDispatch
        ? `This message was not sent. ${localOperatorCredentialFailure(reason, "send this message again")
          ?? (reason instanceof Error ? reason.message : "Reopen the saved work.")}`
        : graphFailure
          ? `The World Graph could not be resolved for this message. ${reason.message} Check World history or explicitly retry the exact saved request; Graph context will remain required.`
        : `${reason instanceof Error ? reason.message : "The message outcome is unknown."} Check World history or explicitly retry the saved request with its original IDs.`;
      uncertainPlayNoticeRef.current = rejectedBeforeDispatch ? null : { turnId: request.turn_id, message: notice };
      setError(notice);
      sharedConversation?.setHistoryRefreshNonce((current) => current + 1);
    } finally {
      if (requestRef.current?.token === token) {
        requestRef.current = null;
        setSending(false);
        if (request.primary_work.kind === "build") {
          buildCompose.finishConstruction((request as WorldBuildAgentTurnRequestV1).build_write_capability?.idempotency_key);
          buildCompose.refresh();
        }
      }
    }
  }

  async function submitPlay(event?: Pick<FormEvent<HTMLFormElement>, "preventDefault">, discussionOnly = false, questionOverride?: string, explicitRequest?: SurfaceConversationRequest) {
    event?.preventDefault();
    if(surfacePreparationRef.current&&!explicitRequest)return;
    if (questionOverride === undefined) setRetryPresentationOrigin(null);
    const admittedRun = playMode?.admittedRun;
    const source = buildMode?.savedSource;
    const message = (questionOverride ?? composerMessage).trim();
    const composerGenerationAtSubmit = composerEditGenerationRef.current;
    if (!isBuild && playMode && playEditMode && questionOverride === undefined) {
      if (!visible || !admittedRun || admittedRun.worldId !== verifiedWorldId || !message
        || sending || playCompose.busy || requestRef.current || sharedConversation?.pendingTurn || pendingPlayTurn) return;
      if (await playCompose.submit(message)) setComposerMessage(current => current === message ? "" : current);
      return;
    }
    if (isBuild) {
      if (!visible || !source || source.worldId !== verifiedWorldId || !historySnapshotRef.current
        || historyLoading || historyError || !message || sending
        || requestRef.current || sharedConversation?.pendingTurn || pendingPlayTurn || pendingPlayLoadError) return;
      if (discussionOnly && !visibleBuildPlacementFailure) return;
      const request: WorldBuildAgentTurnRequestV1 = {
        schema: "dmb_agent_turn_request_v1", client_thread_id: explicitRequest?.clientThreadId ?? crypto.randomUUID(), turn_id: explicitRequest?.turnId ?? crypto.randomUUID(),
        surface: { surface_id: "build", instance_id: source.surfaceInstanceId },
        owner_scope: { kind: "world", world_id: source.worldId },
        primary_work: { kind: "build", object_id: source.documentId, expected_revision: source.revision, expected_content_sha256: source.contentSha256 },
        client_work_state: source.dirty ? "saved_dirty" : "saved_clean",
        graph_request: useWorldGraphForAsk ? { mode: "world", world_id: source.worldId, campaign_id: null, revision_pin: null,
          focus: { kind: "none", session_id: null, campaign_id: null } } : { mode: "none" }, graph_selection: null, message,
      };
      if (useWorldGraphForAsk && buildMode?.composeBridge) {
        const token = Symbol("build-editor-capability");
        const fence = latestRef.current.presentationFenceKey;
        const placementFence = buildPlacementFenceKey;
        const epoch = buildPlacementEpoch;
        const bridge = buildMode.composeBridge;
        const generation = composerEditGenerationRef.current;
        let expectedPlacementFence=placementFence;
        let initializedConversation=false;
        requestRef.current = { token, scopeKey, fenceKey: fence };
        setSending(true);
        try {
          const prepared=await buildCompose.prepareHarnessTurn(request.turn_id,discussionOnly);
          if(prepared.placementError){
            if(latestRef.current.mounted&&latestRef.current.buildPlacementFenceKey===placementFence
              &&latestRef.current.buildPlacementEpoch===epoch&&latestRef.current.buildPlacementBridge===bridge
              &&(questionOverride!==undefined||composerEditGenerationRef.current===generation)){
              if(questionOverride!==undefined)throw new Error(prepared.placementError);
              setBuildPlacementFailure({fenceKey:placementFence,epoch,message,generation,bridge,reason:prepared.placementError});
            }
            return;
          }
          if(!prepared.draftContext||!prepared.history)throw new Error('The current working draft could not be prepared.');
          initializedConversation=!!prepared.initializedConversation;
          request.build_draft_context=prepared.draftContext;
          if(prepared.capability)request.build_write_capability=prepared.capability;
          expectedPlacementFence=JSON.stringify([scopeKey,source,prepared.history.conversation_id,
            prepared.history.active_conversation_id,prepared.history.conversation_state,prepared.history.pointer_revision,useWorldGraphForAsk]);
        } catch (reason) {
          if(latestRef.current.mounted&&latestRef.current.buildPlacementBridge===bridge){
            if(questionOverride!==undefined)throw reason instanceof Error?reason:new Error('The page could not be prepared.');
            setError(reason instanceof Error?reason.message:'The page could not be prepared.');
          }
          return;
        }
        finally {
          if (requestRef.current?.token === token) { requestRef.current = null; setSending(false); }
        }
        if (!latestRef.current.mounted
          || ![placementFence,expectedPlacementFence].includes(latestRef.current.buildPlacementFenceKey)
          || (latestRef.current.buildPlacementEpoch!==epoch
            && !(initializedConversation&&latestRef.current.buildPlacementEpoch===epoch+1&&latestRef.current.buildPlacementFenceKey===expectedPlacementFence))
          || latestRef.current.buildPlacementBridge !== bridge
          || historySnapshotRef.current?.conversation_id!==request.build_draft_context?.conversation_id
          || historySnapshotRef.current?.pointer_revision!==request.build_draft_context?.expected_pointer_revision
          || (questionOverride === undefined && composerEditGenerationRef.current !== generation)) return;
      }
      if(explicitRequest&&!ownsSurfaceConversationRequest(explicitRequest))return;
      setBuildPlacementFailure(null);
      const storageKey = pendingPlayTurnStorageKey(source.worldId);
      const serialized = JSON.stringify({ schema: "dmb_world_play_pending_turn_v1", request });
      try {
        if (window.localStorage.getItem(storageKey) !== null) throw new Error("An earlier request still needs recovery.");
        window.localStorage.setItem(storageKey, serialized);
        if (window.localStorage.getItem(storageKey) !== serialized) throw new Error("Could not preserve the exact request.");
      } catch (reason) { setError(String(reason)); return; }
      if(explicitRequest)acceptSurfaceConversationRequest(explicitRequest.id);
      const stored = { storageKey, serialized, request };
      setPendingPlayTurn(stored);
      if(composerEditGenerationRef.current===composerGenerationAtSubmit)setComposerMessage(current => current.trim() === message ? "" : current);
      await dispatchSavedPlayTurn(stored);
      return;
    }

    if (!visible || !isReadOnly || !admittedRun || admittedRun.worldId !== verifiedWorldId
      || !historySnapshotRef.current || historyLoading || historyError || !message
      || sending || requestRef.current || sharedConversation?.pendingTurn || pendingPlayTurn || pendingPlayLoadError) return;
    if (!admittedRun.beatId || !admittedRun.contentBasis) {
      setError("Select a saved Run edition and scene before asking Buddy.");
      return;
    }
    const request: WorldPlayAgentTurnRequestV1 = {
      schema: "dmb_agent_turn_request_v1",
      client_thread_id: crypto.randomUUID(),
      turn_id: crypto.randomUUID(),
      surface: { surface_id: "play", instance_id: admittedRun.surfaceInstanceId },
      owner_scope: { kind: "world", world_id: admittedRun.worldId },
      primary_work: { kind: "run", object_id: admittedRun.runId, expected_revision: admittedRun.runRevision,
        play_content_basis: admittedRun.contentBasis },
      play_target: { beat_id: admittedRun.beatId, scene_id: admittedRun.sceneId, marker_grammar_version: "v2" },
      client_work_state: "saved_clean",
      graph_request: useWorldGraphForAsk ? { mode: "world", world_id: admittedRun.worldId, campaign_id: null,
        revision_pin: null, focus: { kind: "none", session_id: null, campaign_id: null } } : {mode:"none"},
      graph_selection: null,
      message,
    };
    const storageKey = pendingPlayTurnStorageKey(admittedRun.worldId);
    const serialized = JSON.stringify({ schema: "dmb_world_play_pending_turn_v1", request });
    try {
      if (window.localStorage.getItem(storageKey) !== null) throw new Error("An earlier Play request still needs recovery.");
      window.localStorage.setItem(storageKey, serialized);
      if (window.localStorage.getItem(storageKey) !== serialized) throw new Error("Browser storage did not preserve the exact Play request.");
    } catch (reason) {
      setError(`The Play turn was not sent because its exact recovery request could not be saved. ${reason instanceof Error ? reason.message : "Browser storage is unavailable."}`);
      return;
    }
    const stored = { storageKey, serialized, request };
    setPendingPlayTurn(stored);
    if(composerEditGenerationRef.current===composerGenerationAtSubmit)setComposerMessage((current) => current.trim() === message ? "" : current);
    await dispatchSavedPlayTurn(stored);
  }

  function submitComposer(event: FormEvent<HTMLFormElement>) {
    const intent = detectedComposerIntent;
    setComposerIntent(intent);
    setError(null);
    setEditError(null);
    if (intent === "propose") void composeEdit(event, intent);
    else void submit(event, intent);
  }

  async function loadOlderTurns() {
    const current = historySnapshotRef.current;
    if (!current || !current.next_before_sequence || olderLoading || historyLoading
      || (olderHistoryReadRef.current && !olderHistoryReadRef.current.signal.aborted)) return;
    const controller = new AbortController();
    olderHistoryReadRef.current = controller;
    const cursor = current.next_before_sequence;
    const generation = historyGenerationRef.current;
    setOlderLoading(true);
    setHistoryError(null);
    try {
      const page = await getWorldAgentConversationHistory(current.world_id, {
        limit: WORLD_HISTORY_PAGE_SIZE,
        beforeSequence: cursor,
        includeTurnCorrelation: true,
        signal: controller.signal,
      });
      const latest = historySnapshotRef.current;
      if (controller.signal.aborted || generation !== historyGenerationRef.current) return;
      const validPage = isWorldConversationHistory(page)
        && page.world_id === current.world_id
        && await areHistoryReceiptDigestsBound(page);
      if (controller.signal.aborted || generation !== historyGenerationRef.current) return;
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
      const viewport = presentationHosts?.messages?.parentElement ?? playMessagesHostRef.current?.parentElement;
      if (viewport) {
        olderPageScrollAnchorRef.current = {
          viewport,
          scrollTop: viewport.scrollTop,
          scrollHeight: viewport.scrollHeight,
        };
      }
      setHistory(merged);
    } catch (reason) {
      if (!controller.signal.aborted && generation === historyGenerationRef.current) {
        setHistoryError(localOperatorCredentialFailure(reason, "refresh World history")
          ?? (reason instanceof Error ? reason.message : "Could not load older World turns."));
      }
    } finally {
      if (olderHistoryReadRef.current === controller) olderHistoryReadRef.current = null;
      if (!controller.signal.aborted && generation === historyGenerationRef.current) setOlderLoading(false);
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

  function graphContextStatusLabel(status: WorldPlanGraphAnswerContextStatusV1 | WorldBuildGraphAnswerStatus | WorldBuildSourceAnswerStatus | WorldPlayGraphCompletionV1["answer_context_status"] | import("../../api/types").SurfaceEvidenceCompletion["answer_context_status"] | "proposal_ready" | "image_preparation_ready"): string {
    switch (status) {
      case "authored_grounded": return "Literal excerpts from frozen authored material.";
      case "authored_grounded_partial": return "Literal authored excerpts; coverage was incomplete.";
      case "insufficient_evidence": return "The supplied evidence did not establish the requested details.";
      case "creative_proposal": return "Hypothetical creative suggestion.";
      case "image_preparation_ready": return "Image prompt awaiting review; nothing generated or inserted.";
      case "proposal_ready": return "Authored page suggestion; review and placement are managed on the page.";
      case "source_grounded": return "Supported by opened source passages.";
      case "source_grounded_partial": return "Supported by opened source passages; coverage was incomplete.";
      case "source_insufficient_evidence": return "The opened sources did not support an answer.";
      case "graph_grounded":
        return "Grounded in World Graph evidence.";
      case "graph_grounded_partial":
        return "Partially grounded in World Graph evidence; coverage was incomplete.";
      case "play_only_insufficient_evidence": return "This answer uses the saved Run context; no sufficient World Graph evidence was available.";
      case "play_only_graph_unused": return "This answer uses the saved Run context; no World Graph claims were used.";
      case "source_only_insufficient_evidence": return "This answer uses the saved source; no sufficient World Graph evidence was available.";
      case "source_only_graph_unused": return "This answer uses the saved source; available Graph facts were not used.";
      case "plan_only_insufficient_evidence":
        return "No sufficient World Graph evidence was available; this answer uses the saved Plan context only.";
      case "plan_only_graph_unused":
        return "Graph context was available; no Graph claims were cited or used in the structured answer.";
    }
  }

  function replySourceLabel(status: WorldPlanGraphAnswerContextStatusV1 | WorldBuildGraphAnswerStatus | WorldBuildSourceAnswerStatus | WorldPlayGraphCompletionV1["answer_context_status"] | import("../../api/types").SurfaceEvidenceCompletion["answer_context_status"] | "proposal_ready" | "image_preparation_ready", surface: string | null): string | null {
    const work = surface === "build" ? "Source" : surface === "play" ? "Run" : "Plan";
    switch (status) {
      case "authored_grounded": return "Quoted material";
      case "authored_grounded_partial": return "Quoted material · partial";
      case "insufficient_evidence": return "Needs more context";
      case "creative_proposal": return "Proposed idea";
      case "image_preparation_ready": return "Image direction";
      case "proposal_ready": return "Page proposal";
      case "source_grounded": return "Sources";
      case "source_grounded_partial": return "Sources · partial";
      case "source_insufficient_evidence": return "Needs more context";
      case "graph_grounded": return `World + ${work}`;
      case "graph_grounded_partial": return `World + ${work} · partial`;
      case "play_only_insufficient_evidence":
      case "play_only_graph_unused":
      case "source_only_insufficient_evidence":
      case "source_only_graph_unused":
      case "plan_only_insufficient_evidence":
      case "plan_only_graph_unused": return `${work} only`;
      default: return null;
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
    return Boolean(item.envelope)
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

  function sourceReadMatchesAuthority(
    target: WorldPlanSourceOpenTargetV2,
    snapshot: WorldGraphSourceAnchorReadResponse["snapshot"],
  ): boolean {
    return snapshot !== null
      && snapshot.worldId === target.native_world_id
      && snapshot.campaignId === ""
      && snapshot.scopeMode === "world"
      && snapshot.revisionId === target.graph_revision
      && snapshot.admissibility === "gm"
      && snapshot.focus.kind === "none"
      && snapshot.focus.sessionId === null
      && (snapshot.focus.campaignId ?? null) === null;
  }

  async function openSourcePassage(turn: WorldAgentConversationHistoryTurn, target: WorldPlanSourceOpenTargetV2, more = false) {
    const page = historySnapshotRef.current;
    if (!page || page.world_id !== target.managed_world_id || page.world_id !== verifiedWorldId
      || page.conversation_state !== "active" || !page.conversation_id
      || !page.turns.some((item) => item.turn_id === turn.turn_id)) return;
    const conversationId = page.conversation_id;
    const targetId = target.kind === "evidence_anchor" ? target.anchor_id : target.context_anchor_id;
    const identity = { turnId: turn.turn_id, claimId: target.claim_id, targetId };
    const previous = more ? sourcePassage : null;
    if (more && (target.kind !== "related_recap_context" || !previous?.page?.nextContinuation
      || previous.turnId !== identity.turnId || previous.claimId !== identity.claimId || previous.targetId !== targetId
      || previous.loadingMore)) return;
    const epoch = ++sourceReadEpochRef.current;
    setSourcePassage(previous ? { ...previous, loadingMore: true } : { ...identity, status: "loading", content: null, message: null, partial: false });
    const stillCurrent = () => sourceReadEpochRef.current === epoch
      && historySnapshotRef.current?.world_id === target.managed_world_id
      && historySnapshotRef.current?.conversation_id === conversationId
      && historySnapshotRef.current?.turns.some((item) => {
        const context = graphContextForTurn(item);
        return item.turn_id === turn.turn_id && isRecord(context)
          && Array.isArray(context.source_open_targets)
          && context.source_open_targets.some((current: unknown) => JSON.stringify(current) === JSON.stringify(target));
      });
    const focus = { kind: "none" as const, sessionId: null, campaignId: null };
    try {
      let content: string | null = null;
      let partial = false;
      let lines: { start: number; end: number } | undefined;
      let sourceName: string | null = null;
      let recapPage: WorldGraphRecapContextReadResponseV2 | undefined;
      if (target.kind === "evidence_anchor") {
        const result = await postWorldGraphSourceAnchorRead({
          schema: "dmb_world_graph_source_anchor_read_request_v1",
          worldId: target.native_world_id, campaignId: "", scopeMode: "world", focus,
          admissibility: "gm", revisionPin: target.graph_revision, anchorId: target.anchor_id,
        });
        if (result.schema === "dmb_world_graph_source_anchor_read_v1"
          && ["enough", "partial", "truncated"].includes(result.outcome)
          && sourceReadMatchesAuthority(target, result.snapshot)
          && result.anchorId === target.anchor_id
          && result.evidenceRefId === target.evidence_ref_id
          && result.sourceArtifactId === target.source_artifact_id
          && typeof result.content === "string" && result.content) {
          content = result.content;
          sourceName = typeof result.sourceName === "string" && result.sourceName.trim() ? result.sourceName : null;
          partial = result.truncated || result.outcome === "partial" || result.outcome === "truncated";
        }
      } else {
        const result: WorldGraphRecapContextReadResponseV2 = await postWorldGraphRecapContextReadV2({
          schema: "dmb_recap_context_read_request_v2",
          worldId: target.native_world_id, campaignId: "", scopeMode: "world", focus,
          admissibility: "gm", revisionPin: target.graph_revision, contextAnchorId: target.context_anchor_id,
          maxChars: 12000, continuation: previous?.page?.nextContinuation ?? null,
        });
        const descriptor = result.context;
        if (result.schema === "dmb_recap_context_read_v2"
          && ["enough", "truncated"].includes(result.outcome)
          && sourceReadMatchesAuthority(target, result.snapshot)
          && result.contextAnchorId === target.context_anchor_id
          && hasExactKeys(descriptor, ["contextAnchorId", "worldId", "campaignId", "graphRevisionId", "sourceArtifactId", "sourceRevisionId", "sourceUri", "contentSha256", "expectedSessionId", "canonicalHeading", "legacySessionHeading", "legacyRecapMarker", "selectorSchema", "selectorPolicy"])
          && descriptor?.contextAnchorId === target.context_anchor_id
          && descriptor.worldId === target.native_world_id
          && descriptor.campaignId === target.source_campaign_id
          && descriptor.graphRevisionId === target.graph_revision
          && descriptor.sourceArtifactId === target.source_artifact_id
          && descriptor.sourceRevisionId === target.source_revision_id
          && descriptor.sourceUri === target.source_uri
          && descriptor.contentSha256 === target.content_sha256
          && descriptor.expectedSessionId === target.expected_session_id
          && descriptor.canonicalHeading === target.canonical_heading
          && descriptor.legacySessionHeading === target.legacy_session_heading
          && descriptor.legacyRecapMarker === target.legacy_recap_marker
          && descriptor.selectorSchema === target.selector_schema
          && descriptor.selectorPolicy === target.selector_policy
          && result.mediaType === "text/markdown"
          && Number.isInteger(result.headingLine) && result.headingLine! >= 1
          && result.sessionHeadingLine === result.headingLine
          && Number.isInteger(result.lineStart) && Number.isInteger(result.lineEnd) && result.lineEnd! >= result.lineStart!
          && ((result.selectedForm === "canonical_h1" && result.recapMarkerLine === null && result.lineStart === result.headingLine! + 1)
            || (result.selectedForm === "legacy_h2" && Number.isInteger(result.recapMarkerLine) && result.recapMarkerLine! > result.headingLine! && result.lineStart === result.recapMarkerLine! + 1))
          && typeof result.sectionSha256 === "string" && /^[0-9a-f]{64}$/.test(result.sectionSha256)
          && result.truncated === (result.outcome === "truncated")
          && (result.truncated ? typeof result.nextContinuation === "string" && result.nextContinuation.startsWith("recap-page:v2:") && result.nextContinuation.length <= 256 : result.nextContinuation === null)
          && Number.isInteger(result.offsetChars) && result.offsetChars >= 0
          && (previous?.page ? result.offsetChars === previous.page.offsetChars + [...previous.page.content!].length
            && ["selectedForm", "sessionHeadingLine", "recapMarkerLine", "headingLine", "lineStart", "lineEnd", "sectionSha256"].every((key) => result[key as keyof typeof result] === previous.page![key as keyof typeof result])
            : result.offsetChars === 0)
          && typeof result.content === "string" && result.content && [...result.content].length <= 12000) {
          content = result.content;
          if (Number.isInteger(result.lineStart) && Number.isInteger(result.lineEnd) && result.lineStart! >= 1 && result.lineEnd! >= result.lineStart!) {
            lines = { start: result.lineStart!, end: result.lineEnd! };
          }
          partial = result.truncated;
          recapPage = result;
        }
      }
      if (!stillCurrent()) return;
      setSourcePassage(content
        ? { ...identity, status: "open", content: (previous?.content ?? "") + content, message: null, partial, lines, sourceName, page: recapPage, pages: (previous?.pages ?? 0) + 1, loadingMore: false }
        : { ...identity, status: "unavailable", content: null, message: "This pinned source passage is unavailable or did not match the saved citation.", partial: false });
    } catch {
      if (stillCurrent()) setSourcePassage({ ...identity, status: "unavailable", content: null, message: "The source reader could not open this pinned passage.", partial: false });
    }
  }

  async function openActionEvidence(action: WorldPlanActionProjection, target: WorldPlanSourceOpenTargetV2) {
    const actionKind = action.consultation?.result?.kind;
    const proposalGrounding = actionKind === "proposal"
      ? savedProposalGrounding(action, worldId, history?.conversation_id ?? null, history?.pointer_revision ?? null)
      : null;
    if (target.kind !== "evidence_anchor"
      || (actionKind !== "clarification" && !proposalGrounding)
      || !action.source_open_targets?.some((item) => JSON.stringify(item) === JSON.stringify(target))
      || !conversationActions.some((item) => item.action_id === action.action_id)
      || action.consultation?.receipt.origin_conversation_id !== history?.conversation_id
      || action.consultation?.receipt.origin_pointer_revision !== history?.pointer_revision
      || target.managed_world_id !== verifiedWorldId || !scopeMatches) return;
    const epoch = ++sourceReadEpochRef.current;
    const identity = { turnId: action.action_id, claimId: target.claim_id, targetId: target.anchor_id };
    setSourcePassage({ ...identity, status: "loading", content: null, message: null, partial: false });
    try {
      const result = await postWorldGraphSourceAnchorRead({
        schema: "dmb_world_graph_source_anchor_read_request_v1",
        worldId: target.native_world_id, campaignId: "", scopeMode: "world",
        focus: { kind: "none", sessionId: null, campaignId: null },
        admissibility: "gm", revisionPin: target.graph_revision, anchorId: target.anchor_id,
      });
      if (sourceReadEpochRef.current !== epoch || latestRef.current.verifiedWorldId !== target.managed_world_id
        || historySnapshotRef.current?.conversation_id !== action.consultation?.receipt.origin_conversation_id
        || historySnapshotRef.current?.pointer_revision !== action.consultation?.receipt.origin_pointer_revision
        || latestRef.current.documentId !== documentId || !latestRef.current.scopeMatches) return;
      const admitted = result.schema === "dmb_world_graph_source_anchor_read_v1"
        && ["enough", "partial", "truncated"].includes(result.outcome)
        && sourceReadMatchesAuthority(target, result.snapshot)
        && result.anchorId === target.anchor_id
        && result.evidenceRefId === target.evidence_ref_id
        && result.sourceArtifactId === target.source_artifact_id
        && typeof result.content === "string" && Boolean(result.content);
      setSourcePassage(admitted
        ? { ...identity, status: "open", content: result.content, message: null, partial: result.truncated || result.outcome !== "enough" }
        : { ...identity, status: "unavailable", content: null, message: "This pinned source did not match the saved citation.", partial: false });
    } catch {
      if (sourceReadEpochRef.current === epoch) setSourcePassage({
        ...identity, status: "unavailable", content: null,
        message: "The pinned source passage is unavailable.", partial: false,
      });
    }
  }

  const renderProposalGrounding = (grounding: SavedProposalGrounding | null) => (
    <section className="world-plan-agent-conversation__source-actions" aria-label="Supporting World facts">
      <h5>Supporting World facts</h5>
      {grounding ? <ActionPromptInspector worldId={grounding.action.basis.world_id} actionId={grounding.action.action_id} /> : null}
      {!grounding ? (
        <p className="world-plan-agent-conversation__context">Supporting World facts are not yet available for this proposal.</p>
      ) : grounding.claims.length === 0 ? (
        <p className="world-plan-agent-conversation__context">No supporting World facts are attached to this proposal.</p>
      ) : <ol>{grounding.claims.map((claim) => <li key={claim.claimId}>
        <p>{claim.text}</p>
        <p className="world-plan-agent-conversation__context">{claim.sourceOpened
          ? "Buddy read a source passage for this fact."
          : "Buddy used a Graph fact; it did not read the source passage."}</p>
        {claim.targets.length === 0 ? (
          <p className="world-plan-agent-conversation__context">No source passage can be opened for this fact.</p>
        ) : claim.targets.map((target, index) => target.kind === "evidence_anchor" ? (
          <div key={`${target.anchor_id}:${target.evidence_ref_id}`}>
            <button type="button" onClick={() => { void openActionEvidence(grounding.action, target); }}>
              {claim.targets.length > 1 ? `Open evidence ${index + 1}` : "Open evidence"}
            </button>
            {sourcePassage?.turnId === grounding.action.action_id
              && sourcePassage.claimId === claim.claimId && sourcePassage.targetId === target.anchor_id ? (
              <div>
                <button type="button" onClick={() => { sourceReadEpochRef.current += 1; setSourcePassage(null); }}>Close passage</button>
                {sourcePassage.status === "loading" ? <p role="status">Opening pinned source…</p> : null}
                {sourcePassage.status === "unavailable" ? <p role="alert">{sourcePassage.message}</p> : null}
                {sourcePassage.status === "open" ? <pre>{sourcePassage.content}</pre> : null}
                {sourcePassage.partial ? <p role="note">Partial passage. More source text may be available.</p> : null}
              </div>
            ) : null}
          </div>
        ) : null)}
      </li>)}</ol>}
    </section>
  );

  async function beginClarificationReply(action: WorldPlanActionProjection) {
    setContinuationOfActionId(null);
    proposalIntentRef.current = null;
    const receipt = action.consultation?.receipt;
    const anchor = action.selection_anchor;
    if (!editBridge || !anchor || !receipt || !documentId || !history
      || !scopeMatches || !planReady || saveInFlight
      || action.basis.world_id !== worldId
      || action.basis.document_id !== documentId
      || action.basis.object_revision !== revision
      || receipt.origin_conversation_id !== history.conversation_id
      || receipt.origin_pointer_revision !== history.pointer_revision
      || history.active_conversation_id !== history.conversation_id) {
      setEditError("The saved selection is no longer available here. Start a fresh edit.");
      return;
    }
    try {
      const captured = await editBridge.restoreSelection(anchor, receipt.draft_sha256, receipt.selected_text_sha256, {
        worldId: action.basis.world_id, documentId: action.basis.document_id,
        baseRevision: action.basis.object_revision, baseContentSha256: action.basis.content_sha256,
      }, () => historySnapshotRef.current?.conversation_id === receipt.origin_conversation_id
        && historySnapshotRef.current?.pointer_revision === receipt.origin_pointer_revision
        && historySnapshotRef.current?.active_conversation_id === receipt.origin_conversation_id);
      if (captured.request.world_id !== worldId || captured.request.document_id !== documentId
        || captured.request.base_revision !== revision
        || captured.request.base_content_sha256 !== action.basis.content_sha256
        || captured.request.target_kind !== "replace_selection"
        || JSON.stringify(captured.request.selection_anchor) !== JSON.stringify(anchor)
        || historySnapshotRef.current?.conversation_id !== receipt.origin_conversation_id
        || historySnapshotRef.current?.pointer_revision !== receipt.origin_pointer_revision) {
        throw new PlanEditGuardError("The saved Plan basis or World conversation changed. Start a fresh edit.");
      }
      setContinuationOfActionId(action.action_id);
      setComposerMessage("");
      setComposerIntent("propose");
      setEditError(null);
    } catch (reason) {
      setEditError(reason instanceof Error ? reason.message : "The saved selection could not be restored. Start a fresh edit.");
    }
  }

  const renderConsultedAction = (action: WorldPlanActionProjection) => {
    const result = action.consultation?.result;
    if (!result && ["failed", "indeterminate", "pending"].includes(action.status)
      && action.consultation?.receipt.origin_conversation_id === history?.conversation_id) {
      return <article key={action.action_id} data-plan-action-id={action.action_id}
        className="world-plan-agent-conversation__proposal-event">
        <p><strong>You</strong> {action.instruction}</p>
        <p>{action.status === "failed" ? "This Plan edit failed." : "This Plan edit has no confirmed completion."} No applicable proposal was saved.</p>
        <ActionTerminalDiagnostic worldId={action.basis.world_id} actionId={action.action_id} />
        <ActionPromptInspector worldId={action.basis.world_id} actionId={action.action_id} />
      </article>;
    }
    if (!result || !["clarification", "context_unavailable", "proposal"].includes(result.kind)
      || action.consultation?.receipt.origin_conversation_id !== history?.conversation_id
      || action.consultation?.receipt.origin_pointer_revision !== history?.pointer_revision) return null;
    const grounding = result.kind === "proposal"
      ? savedProposalGrounding(action, worldId, history?.conversation_id ?? null, history?.pointer_revision ?? null)
      : null;
    if (result.kind === "proposal" && (!grounding || currentReview?.admitted.response.action_id === action.action_id)) return null;
    const currentBasisAction = actionHistory.some((candidate) => candidate.action_id === action.action_id);
    const targets = action.source_open_targets?.filter((target) => target.kind === "evidence_anchor") ?? [];
    return <article key={action.action_id} className="world-plan-agent-conversation__proposal-event"
      data-plan-action-id={action.action_id}>
      {!currentBasisAction ? <p className="world-plan-agent-conversation__context">Earlier saved Plan edit · read only</p> : null}
      <div className="world-plan-agent-conversation__message world-plan-agent-conversation__message--user">
        <span className="world-plan-agent-conversation__speaker">You</span><p>{action.instruction}</p>
      </div>
      <div className="world-plan-agent-conversation__message world-plan-agent-conversation__message--assistant">
        <span className="world-plan-agent-conversation__speaker">Buddy</span>
        <WorldPlanAgentAnswer answer={result.message} />
        {result.kind === "proposal" ? renderProposalGrounding(grounding) : <ActionPromptInspector worldId={action.basis.world_id} actionId={action.action_id} />}
        {result.kind === "context_unavailable" ? <p role="note">World context is unavailable. No edit can be applied from this answer.</p> : null}
        {result.kind !== "proposal" ? targets.map((target) => <div key={`${target.claim_id}:${target.anchor_id}`}>
          <button type="button" onClick={() => { void openActionEvidence(action, target); }}>Open evidence</button>
          {sourcePassage?.turnId === action.action_id && sourcePassage.targetId === target.anchor_id ? (
            <div>
              <button type="button" onClick={() => { sourceReadEpochRef.current += 1; setSourcePassage(null); }}>Close passage</button>
              {sourcePassage.status === "loading" ? <p role="status">Opening pinned source…</p> : null}
              {sourcePassage.status === "unavailable" ? <p role="alert">{sourcePassage.message}</p> : null}
              {sourcePassage.status === "open" ? <pre>{sourcePassage.content}</pre> : null}
            </div>
          ) : null}
        </div>) : null}
        {result.kind === "clarification" && !action.selection_anchor
          ? <p role="note">This older clarification has no saved selection. Start a fresh edit to continue.</p>
          : null}
        {result.kind === "clarification" && action.selection_anchor ? <button type="button"
          disabled={composing || !editBridge || !scopeMatches || !currentBasisAction
            || action.consultation?.receipt.origin_pointer_revision !== history?.pointer_revision
            || history?.active_conversation_id !== history?.conversation_id
            || conversationActions.some((candidate) => candidate.consultation?.receipt.continuation?.continuation_of_action_id === action.action_id)}
          onClick={() => { void beginClarificationReply(action); }}>Reply about this edit</button> : null}
      </div>
    </article>;
  };

  function inlineSourceCitations(turn: WorldAgentConversationHistoryTurn): InlineAnswerCitation[] {
    const context = graphContextForTurn(turn);
    if (!context?.completion || !("source_open_targets" in context) || rulesContextForTurn(turn)) return [];
    const entries = context.completion.citation_map?.entries ?? [];
    let number = 0;
    return context.completion.answer_segments.flatMap((segment, segmentIndex) => {
      if (segment.kind !== "graph_claim") return [];
      const citation = entries.find(entry => entry.claim_id === segment.claim_id);
      const targets = context.source_open_targets?.filter(item => item.claim_id === segment.claim_id
        && item.kind === "evidence_anchor" && citation?.evidence_ref_ids.includes(item.evidence_ref_id)) ?? [];
      return targets.map(target => ({ segmentIndex, label: String(++number), title: sourceCitationTitle(target), onOpen: () => {
        const panel = document.getElementById(`buddy-evidence-${turn.turn_id}`);
        if (panel instanceof HTMLDetailsElement) {
          panel.open = true;
          panel.querySelector<HTMLButtonElement>('[role="tab"]')?.click();
          panel.scrollIntoView?.({ block: "nearest" });
        }
        void openSourcePassage(turn, target);
      } }));
    });
  }

  function renderSourceActions(turn: WorldAgentConversationHistoryTurn) {
    const planContext = graphContextForTurn(turn);
    const savedEvidence = planContext?.schema === "dmb_build_graph_context_response_v1" && planContext.completion
      && verifiedWorldId && planContext.saved_source_sections?.length
      ? <BuildSavedSectionEvidence targets={planContext.saved_source_sections} basis={planContext.receipt.source_basis}
          sourceName={planContext.saved_source_name}
          segments={planContext.completion.answer_segments} worldId={verifiedWorldId} turnId={turn.turn_id} /> : null;
    if (planContext?.completion?.schema === "dmb_build_related_page_completion_v1" || planContext?.completion?.schema === "dmb_build_draft_context_completion_v1" || planContext?.completion?.schema === "dmb_build_graph_completion_v2" || planContext?.completion?.schema === "dmb_build_graph_completion_v3" || planContext?.completion?.schema === "dmb_surface_source_completion_v1" || planContext?.completion?.schema === "dmb_surface_evidence_completion_v1" || planContext?.completion?.schema === "dmb_surface_evidence_completion_v2" || planContext?.completion?.schema === "dmb_surface_evidence_completion_v3") {
      return <details className="world-plan-agent-conversation__evidence-trail">
        <summary>Evidence trail</summary>
        <ResponseEvidenceTabs evidence={verifiedWorldId
          ? <>{savedEvidence}<BuildSourcePassageEvidence completion={planContext.completion} worldId={verifiedWorldId} turnId={turn.turn_id} /></>
          : <p>Select the original World to open these source passages.</p>}
          prompt={verifiedWorldId && history?.conversation_id
            ? <BuddyContextTraceLoader enabled promptOnly worldId={verifiedWorldId} turnId={turn.turn_id}
              conversationId={history.conversation_id} />
            : <p>The saved request is unavailable.</p>} />
      </details>;
    }
    const playEvidence = turn.provenance.surface_id === "play" && verifiedWorldId
      ? <PlayAnswerEvidence provenance={turn.provenance} worldId={verifiedWorldId} turnId={turn.turn_id} /> : null;
    const targets = planContext && "source_open_targets" in planContext ? planContext.source_open_targets ?? [] : [];
    const claims = planContext?.completion?.answer_segments.filter((segment) => segment.kind === "graph_claim") ?? [];
    const citations = planContext?.completion?.citation_map?.entries ?? [];
    const citationByClaim = new Map(citations.map((citation) => [citation.claim_id, citation]));
    const evidenceStatuses = planContext && "evidence_anchor_statuses" in planContext ? planContext.evidence_anchor_statuses ?? [] : [];
    const recapStatuses = planContext && "related_recap_context_statuses" in planContext ? planContext.related_recap_context_statuses ?? [] : [];
    const hasEvidence = targets.length > 0 || evidenceStatuses.length > 0 || recapStatuses.length > 0 || claims.length > 0;

    const evidenceCount = targets.filter((target) => target.kind === "evidence_anchor").length;
    const recapCount = targets.length - evidenceCount;
    const referenceCount = citations.reduce((count, citation) => count + citation.evidence_ref_ids.length, 0);
    const summary = !hasEvidence ? "Sources and prepared request" : [
      `${claims.length} ${claims.length === 1 ? "claim" : "claims"}`,
      `${referenceCount} cited Graph ${referenceCount === 1 ? "reference" : "references"}`,
      `${evidenceCount} Graph source ${evidenceCount === 1 ? "passage" : "passages"}`,
      ...(recapCount ? [`${recapCount} related recap ${recapCount === 1 ? "passage" : "passages"}`] : []),
    ].join(" · ");

    const renderTarget = (target: WorldPlanSourceOpenTargetV2) => {
      const targetId = target.kind === "evidence_anchor" ? target.anchor_id : target.context_anchor_id;
      const evidenceChoices = target.kind === "evidence_anchor"
        ? targets.filter((candidate) => candidate.kind === "evidence_anchor" && candidate.claim_id === target.claim_id)
        : [];
      const evidenceNumber = target.kind === "evidence_anchor"
        ? evidenceChoices.findIndex((candidate) => candidate.kind === "evidence_anchor" && candidate.anchor_id === target.anchor_id) + 1
        : 0;
      const heading = target.kind === "related_recap_context"
        ? target.canonical_heading.replace(/^#{1,6}\s*/, "") || `Session ${target.expected_session_id} recap`
        : "";
      const label = target.kind === "evidence_anchor"
        ? evidenceChoices.length > 1 ? `Evidence passage ${evidenceNumber}` : "Evidence passage"
        : heading;
      const relatedChoices = target.kind === "related_recap_context"
        ? targets.filter((candidate) => candidate.kind === "related_recap_context" && candidate.claim_id === target.claim_id).length
        : 0;
      const ariaLabel = target.kind === "evidence_anchor"
        ? evidenceChoices.length > 1 ? `Open evidence passage ${evidenceNumber}` : "Open evidence"
        : relatedChoices > 1
          ? `Open related recap context · ${heading}`
          : "Open related recap context";
      return <button key={`${target.kind}-${target.claim_id}-${targetId}`} type="button"
        className="world-plan-agent-conversation__source-choice"
        aria-label={ariaLabel} title={target.kind === "related_recap_context" ? target.source_uri : undefined}
        onClick={() => { void openSourcePassage(turn, target); }}>
        <span className="world-plan-agent-conversation__source-choice-kind">
          {target.kind === "evidence_anchor" ? "Graph evidence" : `Session ${target.expected_session_id} recap`}
        </span>
        <strong>{sourcePassage?.turnId === turn.turn_id && sourcePassage.targetId === targetId && sourcePassage.sourceName || target.source_name || label}</strong>
        <span>Read source passage <span aria-hidden="true">→</span></span>
      </button>;
    };

    return <details id={`buddy-evidence-${turn.turn_id}`} className="world-plan-agent-conversation__evidence-trail">
      <summary aria-label={`Explore evidence for this answer: ${summary}`}>
        <span className="world-plan-agent-conversation__evidence-trail-title">Evidence trail</span>
        <span className="world-plan-agent-conversation__evidence-trail-summary">{summary}</span>
        <span className="world-plan-agent-conversation__evidence-trail-caret" aria-hidden="true">⌄</span>
      </summary>
      <ResponseEvidenceTabs evidence={<div className="world-plan-agent-conversation__evidence-trail-content">
        {savedEvidence}
        {playEvidence}
        {!hasEvidence && !savedEvidence && !playEvidence ? <p>No Graph citations were saved with this answer.</p> : null}
        {hasEvidence ? <div className="world-plan-agent-conversation__evidence-intro">
          Claims cited in this answer and the source passages you can inspect. The loaded World graph is a separate view.
        </div> : null}
        {claims.map((claim, index) => {
          const citation = citationByClaim.get(claim.claim_id);
          const claimTargets = targets.filter((target) => target.claim_id === claim.claim_id);
          const evidenceStatus = evidenceStatuses.find((row) => row.claim_id === claim.claim_id);
          const recapStatus = recapStatuses.find((row) => row.claim_id === claim.claim_id);
          const activeTarget = claimTargets.find((target) => sourcePassage?.turnId === turn.turn_id
            && sourcePassage.claimId === target.claim_id
            && sourcePassage.targetId === (target.kind === "evidence_anchor" ? target.anchor_id : target.context_anchor_id));
          const overflowTargets = claimTargets.slice(3);
          return <div key={`${turn.turn_id}-evidence-claim-${claim.claim_id}`} className="world-plan-agent-conversation__evidence-claim">
            <header className="world-plan-agent-conversation__evidence-claim-header">
              <span>{claims.length > 1 ? `Claim ${index + 1}` : "Evidence for this answer"}</span>
              {citation ? <span>{citation.target_kind === "relationship" ? "Graph relationship" : "Graph fact"}</span> : null}
            </header>
            {claims.length > 1 ? <blockquote>{claim.text}</blockquote> : null}
            {citation?.source_opened ? <p className="world-plan-agent-conversation__evidence-note">Buddy opened a source passage for this claim.</p> : null}
            {citation && claimTargets.length === 0 && evidenceStatus?.status !== "no_anchor" ? (
              <p className="world-plan-agent-conversation__evidence-note">{citation.evidence_ref_ids.length} Graph {citation.evidence_ref_ids.length === 1 ? "reference was" : "references were"} cited; no readable passage link was saved with this answer.</p>
            ) : null}
            {claimTargets.length > 0 ? <div className="world-plan-agent-conversation__source-choices">
              {claimTargets.slice(0, 3).map(renderTarget)}
              {overflowTargets.length ? <details className="world-plan-agent-conversation__source-more">
                <summary>Show {overflowTargets.length} more passage{overflowTargets.length === 1 ? "" : "s"}</summary>
                <div>{overflowTargets.map(renderTarget)}</div>
              </details> : null}
            </div> : null}
            {evidenceStatus?.status === "no_anchor" ? <p className="world-plan-agent-conversation__evidence-note">No readable Graph source passage is available for this claim.</p> : null}
            {evidenceStatus && ["partial", "overflow"].includes(evidenceStatus.status)
              ? <p className="world-plan-agent-conversation__evidence-note">Some Graph passages could not be shown. Available passages are listed above.</p> : null}
            {recapStatus?.status === "no_context" ? <p className="world-plan-agent-conversation__evidence-note">No related recap passage matched this claim.</p> : null}
            {recapStatus?.status === "metadata_unavailable" ? <p className="world-plan-agent-conversation__evidence-note">Related recap details could not be checked for this claim.</p> : null}
            {recapStatus && ["partial", "overflow"].includes(recapStatus.status)
              ? <p className="world-plan-agent-conversation__evidence-note">Some related recap passages could not be shown. Available passages are listed above.</p> : null}
            {activeTarget && sourcePassage ? <section className="world-plan-agent-conversation__source-reader">
              <header className="world-plan-agent-conversation__source-reader-header">
                <div><span className="world-plan-agent-conversation__source-reader-eyebrow">{activeTarget.kind === "evidence_anchor" ? "Graph evidence" : `Session ${activeTarget.expected_session_id} recap`}</span>
                  <BuddySourceProvenance target={activeTarget} name={activeTarget.source_name || (sourcePassage.status === "loading" ? "Opening source…" : sourcePassage.sourceName)}
                    lines={sourcePassage.lines ?? (sourcePassage.page ? { start: sourcePassage.page.lineStart!, end: sourcePassage.page.lineEnd! } : undefined)} /></div>
                <button type="button" onClick={() => { sourceReadEpochRef.current += 1; setSourcePassage(null); }} aria-label="Close passage" title="Close passage">×</button>
              </header>
              {sourcePassage.status === "loading" ? <p role="status">Opening pinned source…</p> : null}
              {sourcePassage.status === "unavailable" ? <p role="alert">{sourcePassage.message}</p> : null}
              {sourcePassage.status === "open" ? <div className="world-plan-agent-conversation__source-passage"
                role="region" aria-label={activeTarget.kind === "evidence_anchor" ? "Evidence passage" : "Related recap context passage"}>
                {sourcePassage.partial ? <p role="note">Partial passage. More source text may be available.</p> : null}
                {sourcePassage.content}
                {activeTarget.kind === "related_recap_context" && sourcePassage.page?.nextContinuation
                  ? <button type="button" disabled={sourcePassage.loadingMore} onClick={() => { void openSourcePassage(turn, activeTarget, true); }}>
                    {sourcePassage.loadingMore ? "Loading more…" : "Load more context"}
                  </button> : null}
              </div> : null}
            </section> : null}
          </div>;
        })}
      </div>} prompt={verifiedWorldId && history?.conversation_id ? <BuddyContextTraceLoader
        enabled promptOnly worldId={verifiedWorldId} turnId={turn.turn_id} conversationId={history.conversation_id}
      /> : <p>No complete request was captured for this response.</p>} />
    </details>;
  }

  function renderGraphContextHistory(turn: WorldAgentConversationHistoryTurn) {
    const context = graphContextForTurn(turn);
    if (!context) return null;
    const { completion, execution } = context;
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
                <span> · World Graph {citation.target_kind} · Graph revision <code>{citation.graph_revision}</code> · {citation.source_opened ? "source passage read." : "source text not opened."}</span>
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

  async function refreshConversationActions(conversationId: string, pointerRevision: number) {
    if (!verifiedWorldId || !scopeMatches) return;
    try {
      const page = await getWorldPlanConversationActions(verifiedWorldId, conversationId);
      if (page.schema_version === "dmb_world_plan_action_conversation_projection_v1"
        && page.world_id === verifiedWorldId && page.conversation_id === conversationId
        && historySnapshotRef.current?.conversation_id === conversationId
        && historySnapshotRef.current?.pointer_revision === pointerRevision) {
        setConversationActions(page.actions);
      }
    } catch (reason) {
      if (historySnapshotRef.current?.conversation_id === conversationId
        && historySnapshotRef.current?.pointer_revision === pointerRevision) {
        setConversationActionsError(reason instanceof Error ? reason.message : "Could not refresh World edit dialogue.");
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

  async function verifySceneCommittedBasis(captured: CapturedWorldPlanEditTarget) {
    const request = captured.request;
    const committed = await getWorldOwnedPlanCommittedRevision(request.document_id);
    const basis = readCommittedPlanBasis(committed, request.world_id, request.document_id, request.base_revision);
    if (!basis || basis.content_sha256 !== request.base_content_sha256) {
      throw new Error("The committed Plan changed. Refresh the Plan and select the scene again before editing.");
    }
  }

  async function composeEdit(event: FormEvent<HTMLFormElement>, intent = composerIntent) {
    event.preventDefault();
    const composerSnapshotAtSubmit = composerMessage;
    const instruction = composerSnapshotAtSubmit.trim();
    if (intent !== "propose" || !planReady || !scopeMatches || !namespace || !documentId || !editBridge
      || !isPositiveRevision(revision) || saveInFlight || !instruction
      || composing || sending || requestRef.current || proposalRequestRef.current) return;
    if (effectiveEditTarget && effectiveEditTargetStale) {
      setEditError("The selected card is stale or no longer unique in this draft. Select it again before composing.");
      return;
    }
    const submittedEditId = crypto.randomUUID();
    const composerGenerationAtSubmit = composerEditGenerationRef.current;
    setSubmittedMessage({ id: submittedEditId, scopeKey, conversationId: historySnapshotRef.current?.conversation_id ?? null,
      pointerRevision: historySnapshotRef.current?.pointer_revision ?? null, message: instruction, kind: "propose" });
    setComposerMessage((current) => current === composerSnapshotAtSubmit ? "" : current);

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
      if (captured.request.target_kind !== displayedEditKind
        || (displayedEditKind !== "replace_playable_body" && captured.request.playable_target != null)
        || captured.request.world_id !== worldId || captured.request.document_id !== documentId
        || captured.request.base_revision !== revision
        || captured.draftGeneration !== draftGeneration || captured.selectionGeneration !== selectionGeneration
        || (effectiveEditTarget && (captured.request.playable_target?.kind !== effectiveEditTarget.kind
          || captured.request.playable_target?.id !== effectiveEditTarget.id))
        || (playableEditTarget && captured.playableTargetGeneration !== playableEditTargetGeneration)
        || (!playableEditTarget && effectiveEditTarget && playableTargetBasis
          && captured.request.base_content_sha256 !== playableTargetBasis.contentSha256)) {
        throw new Error("The captured edit target no longer matches the displayed change target. Select the target again before proposing.");
      }
      if (worldPlanEditReviewBefore(captured) === null) {
        throw new Error("The captured Plan target has no valid Before snapshot. Reselect it and compose the proposal again.");
      }
      if (continuationOfActionId && captured.request.target_kind !== "replace_selection") {
        throw new Error("Reply to this clarification with the original Plan selection active.");
      }
      if (continuationOfActionId) {
        const predecessor = conversationActions.find((action) => action.action_id === continuationOfActionId);
        if (!predecessor?.selection_anchor
          || JSON.stringify(captured.request.selection_anchor) !== JSON.stringify(predecessor.selection_anchor)
          || predecessor.basis.world_id !== captured.request.world_id
          || predecessor.basis.document_id !== captured.request.document_id
          || predecessor.basis.object_revision !== captured.request.base_revision
          || predecessor.basis.content_sha256 !== captured.request.base_content_sha256
          || predecessor.consultation?.receipt.draft_sha256 !== captured.request.draft_sha256
          || predecessor.consultation?.receipt.selected_text_sha256 !== await textSha256(captured.request.selected_text)
          || predecessor.consultation?.receipt.origin_conversation_id !== dispatchHistory?.conversation_id
          || predecessor.consultation?.receipt.origin_pointer_revision !== dispatchHistory?.pointer_revision) {
          throw new Error("The saved selection or World conversation changed. Start a fresh edit.");
        }
      }
      if (captured.playableTargetSource === "scene") {
        await verifySceneCommittedBasis(captured);
        if (!isCurrent()) return;
      }
      const conversationHistory: WorldPlanDocumentEditProposalRequest["conversation_history"] = [];
      const { selection_anchor: capturedAnchor, ...capturedRequest } = captured.request;
      const requestWithoutKey = {
        ...capturedRequest,
        ...(capturedAnchor && proposalAnchor ? { selection_anchor: capturedAnchor } : {}),
        instruction,
        conversation_history: conversationHistory,
        ...(continuationOfActionId ? { continuation_of_action_id: continuationOfActionId } : {}),
        ...(captured.request.target_kind === "replace_selection" && proposalAnchor && dispatchHistory
          ? { expected_active_conversation_id: proposalAnchor.conversationId,
              expected_pointer_revision: dispatchHistory.pointer_revision }
          : {}),
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
      if (response.schema_version === "dmb_world_plan_edit_clarification_v1") {
        if (captured.request.target_kind !== "replace_selection"
          || response.world_id !== request.world_id
          || response.document_id !== request.document_id
          || response.base_revision !== request.base_revision
          || response.base_content_sha256 !== request.base_content_sha256
          || response.draft_sha256 !== request.draft_sha256
          || response.selected_text_sha256 !== await textSha256(request.selected_text)
          || !["clarification", "context_unavailable"].includes(response.kind)) {
          throw new Error("The saved Plan clarification did not match this captured selection.");
        }
        if (!isCurrent()) return;
        proposalRequestRef.current = null;
        setComposing(false);
        setSubmittedMessage((current) => current?.id === submittedEditId ? null : current);
        setComposerIntent("propose");
        setContinuationOfActionId(null);
        proposalIntentRef.current = null;
        await refreshActionHistory();
        if (proposalAnchor && dispatchHistory) {
          await refreshConversationActions(proposalAnchor.conversationId, dispatchHistory.pointer_revision);
        }
        return;
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
      setSubmittedMessage((current) => current?.id === submittedEditId ? null : current);
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
      // A newly created local proposal thread must remain the selected Plan thread
      // after Play temporarily rehydrates a different Agent Interaction scope.
      agent.switchThread?.(currentThread.threadId);
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
      if (editBridge.preview) {
        const preview = editBridge.preview(captured, admitted);
        setReviewSnapshots((current) => ({ ...current, [turnId]: {
          scopeKey, worldId: captured.request.world_id, documentId: captured.request.document_id,
          threadId: currentThread.threadId, conversationId: proposalAnchor?.conversationId ?? null,
          targetLabel: captured.playableTargetLabel || captured.playableBodyTarget?.target.id
            || captured.sectionTarget?.heading || (captured.request.target_kind === "insert_at_caret" ? "at the captured caret" : "selected text"),
          preview,
        } }));
      }
      editReviewRef.current = nextReview;
      setEditReview(nextReview);
      setComposerIntent("discuss");
      setContinuationOfActionId(null);
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
      if (proposalAnchor && dispatchHistory) {
        void refreshConversationActions(proposalAnchor.conversationId, dispatchHistory.pointer_revision);
      }
    } catch (reason) {
      if (isCurrent()) {
        restoreSubmittedDraft(composerSnapshotAtSubmit, composerGenerationAtSubmit);
        setEditError(reason instanceof Error ? reason.message : "The Plan edit proposal failed. Try again.");
        void refreshActionHistory();
        if (proposalAnchor && dispatchHistory) {
          void refreshConversationActions(proposalAnchor.conversationId, dispatchHistory.pointer_revision);
        }
      }
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
    if (applyingReviewRef.current) return;
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
    applyingReviewRef.current = review;
    setApplyingTurnId(review.turnId);
    try {
      if (review.captured.playableTargetSource === "scene") {
        await verifySceneCommittedBasis(review.captured);
        if (editReviewRef.current !== review || latestRef.current.proposalFenceKey !== review.fenceKey
          || !latestRef.current.scopeMatches || latestRef.current.threadId !== review.threadId) {
          throw new Error("World Plan or selected scene changed. Compose the proposal again.");
        }
      }
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
      if (editReviewRef.current !== review || !latestRef.current.mounted
        || latestRef.current.threadId !== review.threadId || !latestRef.current.scopeMatches) return;
      setComposerIntent("propose");
      if (reason instanceof PlanEditGuardError || (reason instanceof Error && reason.message.includes("committed Plan changed"))) discardEditReview();
      setEditError(reason instanceof Error ? reason.message : "The proposal could not be applied to this mounted Plan.");
    } finally {
      if (applyingReviewRef.current === review) {
        applyingReviewRef.current = null;
        setApplyingTurnId(null);
      }
    }
  }

  const presentAvailability = (message: string) => presentationHosts?.composer
    ? createPortal(<p className="world-plan-agent-draft-note" role="status">{message}</p>, presentationHosts.composer)
    : null;
  const requestedSurfaceTurn = surfaceRequests.find(item=>isBuild&&item.surfaceId==='build'
    &&item.worldId===verifiedWorldId&&item.objectId===buildMode?.savedSource?.documentId);
  useEffect(()=>{
    const source=buildMode?.savedSource;
    if(!visible||!isBuild||!source||!requestedSurfaceTurn||requestedSurfaceTurn.status!=='pending'
      ||historyLoading||!historySnapshotRef.current||pendingPlayLoadedWorldId!==verifiedWorldId)return;
    if(sending||composing||buildCompose.busy||requestRef.current||sharedConversation?.pendingTurn||pendingPlayTurn||pendingPlayLoadError||historyError){
      const occupied=claimSurfaceConversationRequest(requestedSurfaceTurn.id);
      if(occupied){failSurfaceConversationRequest(occupied.id);setError('Finish or recover the current reply, then try build out.');}
      return;
    }
    if(!useWorldGraphForAsk){setUseWorldGraphForAsk(true);return;}
    const request=claimSurfaceConversationRequest(requestedSurfaceTurn.id);
    if(!request)return;
    surfacePreparationRef.current=true;setSurfacePreparing(true);
    void (async()=>{
      try{
        await request.prepare?.({bridge:buildMode?.composeBridge,source});
        if(!ownsSurfaceConversationRequest(request)||!request.isCurrent()||!surfaceVisibleRef.current||!latestRef.current.mounted||latestRef.current.verifiedWorldId!==request.worldId
          ||latestRef.current.buildPlacementBridge!==buildMode?.composeBridge)return;
        await submitPlay(undefined,false,request.message,request);
      }catch(reason){if(latestRef.current.mounted&&request.isCurrent())setError(reason instanceof Error?reason.message:'Build out could not start.');}
      finally{surfacePreparationRef.current=false;if(latestRef.current.mounted)setSurfacePreparing(false);if(ownsSurfaceConversationRequest(request))failSurfaceConversationRequest(request.id);}
    })();
  },[requestedSurfaceTurn,visible,isBuild,buildMode?.savedSource,buildMode?.composeBridge,sending,composing,
    buildCompose.busy,sharedConversation?.pendingTurn,pendingPlayTurn,pendingPlayLoadError,historyLoading,historyError,
    pendingPlayLoadedWorldId,verifiedWorldId,useWorldGraphForAsk]);

  if (!visible) return null;
  if (!isReadOnly && !pageReady) return presentAvailability("Loading Plan conversation context…");
  if (!isReadOnly && !documentId) {
    if (presentationHosts) return presentAvailability("Save this Plan to start an Agent conversation.");
    return <p className="world-plan-agent-draft-note" role="status">Save this Plan to start an Agent conversation.</p>;
  }
  if (!isReadOnly && (!planReady || !askSlot?.hostElement || !scopeMatches)) return presentAvailability("Verifying saved Plan conversation context…");

  const currentReviewBefore = editReview ? worldPlanEditReviewBefore(editReview.captured) : null;
  const currentReview = editReview
    && currentReviewBefore !== null
    && editReview.fenceKey === proposalFenceKey
    && editReview.threadId === activeThread?.threadId
    ? editReview
    : null;
  const reviewGrounding = (() => {
    if (!currentReview || !history || history.active_conversation_id !== history.conversation_id) return null;
    const response = currentReview.admitted.response;
    const consultation = response.consultation;
    if (!consultation || consultation.result.kind !== "proposal"
      || consultation.origin_conversation_id !== history.conversation_id
      || consultation.origin_pointer_revision !== history.pointer_revision) return null;
    const action = conversationActions.find((candidate) => candidate.action_id === response.action_id);
    if (!action || action.basis.world_id !== response.world_id
      || action.basis.document_id !== response.document_id
      || action.basis.object_revision !== response.base_revision
      || action.basis.content_sha256 !== response.base_content_sha256
      || action.consultation?.receipt.draft_sha256 !== response.draft_sha256
      || action.consultation?.receipt.selected_text_sha256 !== response.selected_text_sha256
      || action.consultation?.result?.result_id !== consultation.result.result_id) return null;
    return savedProposalGrounding(action, worldId, history.conversation_id, history.pointer_revision);
  })();
  const authorizationBlocked = [historyError, error, editError].some((message) =>
    message?.includes("local Agent and Graph session is missing or was rejected"));
  const hasUncertainPlayNotice = Boolean(uncertainPlayNoticeRef.current
    && error === uncertainPlayNoticeRef.current.message);
  const hasUncertainPlanNotice = Boolean(uncertainPlanNoticeRef.current
    && error === uncertainPlanNoticeRef.current.message);
  const pendingSavedAsk = pendingAsks.some((item) => item.envelope !== null);
  const savedAskRecords = pendingAsks.filter((item): item is StoredPendingAsk & { envelope: WorldPlanPendingAskEnvelope } =>
    item.envelope !== null);
  const pendingAskRecords = savedAskRecords;
  const confirmedFailureCount = pendingAskRecords.filter((item) => isPendingAskFailureConfirmed(item)).length;
  const unconfirmedAskCount = pendingAskRecords.length - confirmedFailureCount;
  const intentBusy = sending || composing || saveInFlight || !scopeMatches || currentReview !== null;
  const inferredComposerIntent = classifySurfaceComposerIntent(composerMessage);
  const detectedComposerIntent = continuationOfActionId ? "propose" : composerIntentCorrection?.message === composerMessage
    ? composerIntentCorrection.intent
    : inferredComposerIntent;
  const buildSourceMissing = isBuild && !buildMode?.savedSource;
  const pendingPlayRecoveryHydrating = Boolean(verifiedWorldId && pendingPlayLoadedWorldId !== verifiedWorldId);
  const composerBusy = isReadOnly
    ? surfacePreparing || buildCompose.busy || playCompose.busy || sending || (Boolean(sharedConversation?.pendingTurn) || Boolean(pendingPlayTurn) || Boolean(pendingPlayLoadError))
      || historyLoading || !history || Boolean(historyError) || !currentReadOnlyContext || pendingPlayRecoveryHydrating
    : intentBusy || Boolean(sharedConversation?.pendingTurn) || Boolean(pendingPlayTurn) || Boolean(pendingPlayLoadError)
      || pendingPlayRecoveryHydrating
      || (detectedComposerIntent === "discuss"
      && (historyLoading || !history || Boolean(historyError)));
  const displayedSavedPlanVersion = savedPlanVersion?.key === committedPlanVersionKey
    ? savedPlanVersion
    : null;

  function handleComposerKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key !== "Enter" || event.shiftKey || event.altKey || event.ctrlKey || event.metaKey) return;
    if (event.nativeEvent.isComposing || event.nativeEvent.keyCode === 229) return;
    if (composerBusy || requestRef.current !== null || proposalRequestRef.current !== null) return;

    event.preventDefault();
    if (!composerMessage.trim()
      || (!isReadOnly && detectedComposerIntent === "discuss" && playableTargetStale)) return;
    event.currentTarget.form?.requestSubmit();
  }
  const localProposalPositionsByTurnId = new Map(
    [...archivedProposalPositions, ...(retiredProposalTurns?.scopeKey === scopeKey ? retiredProposalTurns.positions : []),
      ...(proposalOrderForDisplay?.positions ?? [])].map((position) => [position.turnId, position]),
  );
  const renderFrozenReview = (turn: AgentInteractionTurn) => {
    const snapshot = reviewSnapshots[turn.turnId];
    if (!snapshot || snapshot.scopeKey !== scopeKey) return null;
    if (isReadOnly) return <details className="world-plan-agent-conversation__review" aria-label="Read-only Plan proposal preview">
      <summary>Plan proposal preview · return to Plan to review or apply</summary>
      <div className="world-plan-agent-conversation__preview">
        <section><h5>Before</h5><WorldPlanAgentAnswer answer={snapshot.preview.before.markdown} /></section>
        <section><h5>After</h5><WorldPlanAgentAnswer answer={snapshot.preview.after.markdown} /></section>
      </div>
    </details>;
    const executable = !isReadOnly && currentReview?.turnId === turn.turnId ? currentReview : null;
    const status = turn.planEdit?.applied ? "applied"
      : executable ? applyingTurnId === turn.turnId ? "applying" : "review" : "stale";
    const canOfferSave = status === "applied" && savedDirty && snapshot.threadId === activeThread?.threadId
      && (!snapshot.conversationId || snapshot.conversationId === history?.conversation_id) && onSavePlan;
    return <PlanEditReview targetLabel={snapshot.targetLabel} before={snapshot.preview.before} after={snapshot.preview.after}
        status={status} onApply={() => { if (executable) void applyEditReview(executable); }}
        onDiscard={() => { if (executable && editReviewRef.current === executable) discardEditReview(); }}
        supportingFacts={executable ? renderProposalGrounding(reviewGrounding) : undefined}
        saveAction={canOfferSave ? { disabled: !savedDirty || !savePlanEnabled || saveInFlight, onSave: () => {
          if (latestRef.current.mounted && latestRef.current.verifiedWorldId === snapshot.worldId
            && latestRef.current.documentId === snapshot.documentId && latestRef.current.threadId === snapshot.threadId
            && (!snapshot.conversationId || historySnapshotRef.current?.conversation_id === snapshot.conversationId)
            && latestRef.current.scopeMatches && latestRef.current.savedDirty && latestRef.current.savePlanEnabled
            && !latestRef.current.saveInFlight) onSavePlan?.();
        } } : undefined}
      />;
  };
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
      <div className="world-plan-agent-conversation__message world-plan-agent-conversation__message--user">
        <span className="world-plan-agent-conversation__speaker">You</span>
        <p>{turn.question}</p>
      </div>
      <div className="world-plan-agent-conversation__message world-plan-agent-conversation__message--assistant">
        <span className="world-plan-agent-conversation__speaker">Buddy</span>
        <WorldPlanAgentAnswer answer={turn.planEdit
          ? `${turn.planEdit.applied ? "Applied to your draft" : "Proposal only; not applied"}. ${turn.planEdit.targetKind === "insert_at_caret"
            ? "Scope: insertion at the captured caret; no scene target was selected."
            : turn.planEdit.targetKind === "replace_selection" ? "Scope: replacement of the captured editor selection."
              : "Scope: replacement of the captured card body."}`
          : turn.answer} />
        {turn.planEdit ? <details><summary>Model proposal explanation</summary>
          <WorldPlanAgentAnswer answer={turn.planEdit.proposalSummary} />
        </details> : null}
      </div>
      {turn.planEdit?.applied ? (
        <p className="world-plan-agent-conversation__context">Apply changes your draft. Save keeps the changes.</p>
      ) : null}
      {turn.planEdit && !turn.planEdit.applied && reviewSnapshots[turn.turnId]?.scopeKey !== scopeKey
        && currentReview?.turnId !== turn.turnId ? (
        <>
          <p role="status">Review expired after reload. This proposal was not applied; request a new proposal to review it.</p>
          <details>
            <summary>Stored proposed replacement</summary>
            <WorldPlanAgentAnswer answer={turn.planEdit.replacementMarkdown} />
          </details>
        </>
      ) : null}
      {isReadOnly && turn.planEdit && !turn.planEdit.applied ? (
        <p role="note">Return to Plan to review or apply this proposal.</p>
      ) : null}
      {reviewSnapshots[turn.turnId]?.scopeKey === scopeKey ? renderFrozenReview(turn) : !isReadOnly && currentReview?.turnId === turn.turnId ? (
        <section className="world-plan-agent-conversation__review" aria-label="Review proposed Plan edit">
          <h4>Review this proposal</h4>
          {currentReview.admitted.response.assumptions.length ? (
            <ul>{currentReview.admitted.response.assumptions.map((assumption, index) => <li key={`${index}:${assumption}`}>{assumption}</li>)}</ul>
          ) : null}
          <div className="world-plan-agent-conversation__preview">
            <div>
              <h5>Before</h5>
              {currentReviewBefore?.kind === "captured-text" && currentReviewBefore.target ? (
                <p className="world-plan-agent-conversation__context">
                  Card target · {currentReview.captured.playableTargetLabel ? `${currentReview.captured.playableTargetLabel} · ` : ""}{currentReviewBefore.target.kind} {currentReviewBefore.target.id}
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
          {renderProposalGrounding(reviewGrounding)}
          <p className="world-plan-agent-conversation__context">Apply changes your draft. Save keeps the changes.</p>
          <div className="world-plan-agent-conversation__review-actions">
            <button type="button" onClick={discardEditReview}>Discard proposal</button>
            <button type="button" onClick={() => { void applyEditReview(currentReview); }}>Apply changes</button>
          </div>
        </section>
      ) : null}
    </article>
  );
  const unmatchedSubmittedMessage = submittedMessage?.scopeKey === scopeKey
    && (submittedMessage.conversationId === null
      ? submittedMessage.pointerRevision === (history?.pointer_revision ?? null)
      : submittedMessage.conversationId === history?.conversation_id)
    && !history?.turns.some(turn => turn.turn_id === submittedMessage.id
      || (submittedMessage.idempotencyKey && "idempotency_key" in turn
        && turn.idempotency_key === submittedMessage.idempotencyKey
        && turn.user_text === submittedMessage.message));
  const lastDisplayEvent = conversationDisplay.events.at(-1);
  const pendingRetryTurnId = unmatchedSubmittedMessage && lastDisplayEvent?.kind === "world"
    && retryPresentationOrigin?.scopeKey === scopeKey
    && retryPresentationOrigin.turnId === lastDisplayEvent.turn.turn_id
    && !buildCompose.items.some(item => item.afterSequence >= lastDisplayEvent.turn.sequence)
    && isUnansweredFailure(lastDisplayEvent.turn)
    && lastDisplayEvent.turn.user_text === submittedMessage?.message
    && lastDisplayEvent.turn.provenance.surface_id === (isBuild ? "build" : isReadOnly ? "play" : "plan")
    && lastDisplayEvent.turn.provenance.primary_work.object_id === (isBuild ? buildMode?.savedSource?.documentId : isReadOnly ? playMode?.admittedRun?.runId : documentId)
    ? lastDisplayEvent.turn.turn_id : null;
  const renderConversationEvent = (event: WorldConversationDisplayEvent,
    previousAttempts: WorldConversationDisplayEvent[] = [], historicalAttempt = false): React.ReactNode => {
    if (event.kind === "proposal") return renderProposalEvent(event.turn, event.position, false);
    const turn = event.turn;
    // The immutable receipt records generation; proposal controls own current review state.
    const pageProposalAcknowledgment = graphContextForTurn(turn)?.completion?.schema === "dmb_build_authoring_completion_v1"
      && !rulesContextForTurn(turn);
    const failed = turn.lifecycle_status !== "interrupted" && (isHistoryTurnFailureConfirmed(turn.turn_id)
      || isWorldHistoryTurnFailed(turn.turn_id) || turn.lifecycle_status === "failed");
    const interrupted = turn.lifecycle_status === "interrupted";
    const deliveryDiagnostic = (uncertainPlanNoticeRef.current?.turnId === turn.turn_id
      || (submittedMessage?.idempotencyKey && "idempotency_key" in turn
        && turn.idempotency_key === submittedMessage.idempotencyKey
        && turn.user_text === submittedMessage.message
        && uncertainPlanNoticeRef.current?.turnId === submittedMessage.id))
      ? uncertainPlanNoticeRef.current.message
      : null;
    const targetReceipt = historyTurnPlayableTargetLabel(turn);
    return (
      <BuddyTurnInspection key={`world:${turn.turn_id}`} worldId={verifiedWorldId ?? ""}
        conversationId={history?.conversation_id ?? ""} turnId={turn.turn_id}
        lifecycle={turn.lifecycle_status}>
      <article
        className={`world-plan-agent-conversation__turn world-plan-agent-conversation__turn--${turn.assistant_text ? "complete" : failed ? "failed" : interrupted ? "interrupted" : "pending"}`}
        data-sequence={turn.sequence}
      >
        <div className="world-plan-agent-conversation__message world-plan-agent-conversation__message--user">
          <span className="world-plan-agent-conversation__speaker">You</span>
          <p>{turn.user_text}</p>
        </div>
        {turn.assistant_text ? (
          <div className="world-plan-agent-conversation__message world-plan-agent-conversation__message--assistant">
            <div className="world-plan-agent-conversation__reply-heading">
              <span className="world-plan-agent-conversation__speaker">Buddy</span>
              {turn.lifecycle_status === "completed" && graphContextForTurn(turn)?.completion
                && replySourceLabel(graphContextForTurn(turn)!.completion!.answer_context_status, turn.provenance.surface_id) ? (
                <span className="world-plan-agent-conversation__answer-basis" aria-label="Answer sources"
                  title={graphContextStatusLabel(graphContextForTurn(turn)!.completion!.answer_context_status)}>
                  {graphContextForTurn(turn)!.completion!.answer_basis === "mixed_evidence" && graphContextForTurn(turn)!.completion!.answer_context_status.startsWith("graph_grounded")
                    ? `World evidence${graphContextForTurn(turn)!.completion!.answer_context_status.endsWith("_partial") ? " · partial" : ""}`
                    : graphContextForTurn(turn)!.completion!.answer_basis.endsWith("_plus_session_evidence") ? "Session evidence" : replySourceLabel(graphContextForTurn(turn)!.completion!.answer_context_status, turn.provenance.surface_id)}
                </span>
              ) : null}
              {rulesContextForTurn(turn) && <span className="world-plan-agent-conversation__answer-basis" aria-label="Rules answer sources">
                {rulesContextForTurn(turn)!.accepted_binding.support_table.length ? 'Rules evidence' : 'Rules lookup: no evidence'}
              </span>}
            </div>
            {(graphContextForTurn(turn)?.completion?.schema === "dmb_surface_evidence_completion_v1" || graphContextForTurn(turn)?.completion?.schema === "dmb_surface_evidence_completion_v2" || graphContextForTurn(turn)?.completion?.schema === "dmb_surface_evidence_completion_v3")
              ? <SurfaceEvidenceAnswer completion={graphContextForTurn(turn)!.completion as import("../../api/types").SurfaceEvidenceCompletion}
                worldId={verifiedWorldId} turnId={turn.turn_id} composition={rulesContextForTurn(turn) ? {text:turn.assistant_text,ranges:rulesContextForTurn(turn)!.accepted_binding.segment_map} : undefined}/>
              : <WorldPlanAgentAnswer
              answer={pageProposalAcknowledgment ? "Page suggestion prepared." : turn.assistant_text}
              inlineCitations={inlineSourceCitations(turn)}
              allowedInternalLinks={graphContextForTurn(turn)?.completion?.answer_segments.flatMap(segment => segment.kind === "session_evidence_claim" ? ["/play?" + new URLSearchParams({world: turn.provenance.world_id,run: segment.run_id,evidence_revision:String(segment.review_revision)}).toString()] : [])}
              displaySegments={pageProposalAcknowledgment || rulesContextForTurn(turn) ? undefined : graphContextForTurn(turn)?.completion
                ? graphContextForTurn(turn)!.completion!.answer_segments.map((segment) => segment.text)
                : undefined}
            />}
            {!isReadOnly && turn.provenance.surface_id === "plan" && graphContextForTurn(turn)?.completion?.answer_segments
              .filter(segment => segment.kind === "proposal" && segment.label === "image_prompt")
              .map((segment, index) => <SurfaceImagePromptAction key={`${turn.turn_id}:image:${index}`} prompt={segment.text}
                unavailableReason={!scopeMatches || !pageReady || saveInFlight || turn.provenance.world_id !== worldId
                  || turn.provenance.primary_work.object_id !== documentId
                  || turn.provenance.primary_work.object_revision !== revision
                  ? "Open the original saved Plan revision to use this image prompt."
                  : imagePromptHost?.unavailableReason ?? (imagePromptHost ? null : "Open this Plan with Image Studio available to use the prompt.")}
                onOpen={imagePromptHost ? (prompt) => { if (imagePromptHost.open(prompt)) agent.setPaneOpen(false); } : undefined}
              />)}
            {rulesContextForTurn(turn) && <RulesAnswerEvidence active={visible && agent.paneState.isOpen} context={rulesContextForTurn(turn)!} answer={turn.assistant_text ?? ''} />}
            {renderSourceActions(turn)}
            {verifiedWorldId && history?.conversation_id && <ConversationWorkbook
              key={`workbook:${verifiedWorldId}:${history.conversation_id}:${turn.turn_id}`}
              source={turn.assistant_text} worldId={verifiedWorldId} conversationId={history.conversation_id}
              turnId={turn.turn_id} disabled={composerBusy}
              onAdd={text=>{composerEditGenerationRef.current+=1;setComposerMessage(current=>current.trim()?`${current}\n\n${text}`:text);}} />}
          </div>
        ) : failed || interrupted ? (
          <div className="world-plan-agent-conversation__turn-status">
          {!historicalAttempt && turn.provenance.surface_id === (isBuild ? "build" : isReadOnly ? "play" : "plan")
            && turn.provenance.primary_work.object_id === (isBuild ? buildMode?.savedSource?.documentId : isReadOnly ? playMode?.admittedRun?.runId : documentId)
            ? <ConversationRecovery question={turn.user_text} blocked={composerBusy}
                onRetry={async(question)=>{
                  setRetryPresentationOrigin({scopeKey,turnId:turn.turn_id});
                  if(isReadOnly)await submitPlay(undefined,false,question);
                  else await submit({preventDefault:()=>undefined},"discuss",question);
                }} /> : null}
          </div>
        ) : null}
        <div className="world-plan-agent-conversation__turn-debug">
          <details className="world-plan-agent-conversation__turn-details" onToggle={(event) => {
            const open = event.currentTarget.open;
            const key = `${verifiedWorldId}\u001f${turn.turn_id}`;
            setOpenedTraceTurns(current => current[key] === open ? current : { ...current, [key]: open });
          }}>
            <summary>Debug</summary>
            {failed || interrupted ? (
              <p role="status">
                {pendingRetryTurnId === turn.turn_id && !historicalAttempt
                  ? sending ? "Retrying your question…" : "Checking the retried request…"
                  : failed
                  ? turn.provenance.surface_id === "play" ? "Buddy couldn’t finish this reply. No Run change was applied." : turn.provenance.surface_id === "build" ? "Buddy couldn’t finish this reply. Your saved source was not changed." : "Buddy couldn’t finish this reply. Your Plan was not changed."
                  : turn.provenance.surface_id === "play" ? "This reply stopped before it finished. No Run change was applied." : turn.provenance.surface_id === "build" ? "This reply stopped before it finished. Your saved source was not changed." : "This reply stopped before it finished. Your Plan was not changed."}
              </p>
            ) : null}
            {openedTraceTurns[`${verifiedWorldId}\u001f${turn.turn_id}`] && previousAttempts.length ? <details>
              <summary>Previous attempts · {previousAttempts.length}</summary>
              {previousAttempts.map(attempt => renderConversationEvent(attempt, [], true))}
            </details> : null}
            {pendingRetryTurnId === turn.turn_id && !historicalAttempt && (uncertainPlayNoticeRef.current || uncertainPlanNoticeRef.current)
              ? <p>{uncertainPlayNoticeRef.current?.message ?? uncertainPlanNoticeRef.current?.message}</p> : null}
            {verifiedWorldId && history?.conversation_id ? <BuddyContextTraceLoader
              enabled={openedTraceTurns[`${verifiedWorldId}\u001f${turn.turn_id}`] === true}
              worldId={verifiedWorldId} turnId={turn.turn_id} conversationId={history.conversation_id}
            /> : null}
            <p className="world-plan-agent-conversation__context">
              Turn {turn.sequence} · {turn.lifecycle_status} · {historyTurnProvenanceLabel(turn)}
            </p>
            {deliveryDiagnostic ? <p className="world-plan-agent-conversation__context">Delivery · {deliveryDiagnostic}</p> : null}
            {targetReceipt ? (
              <p role={targetReceipt.startsWith("Target receipt unavailable") ? "alert" : "note"}>{targetReceipt}</p>
            ) : null}
            {renderGraphContextHistory(turn)}
          </details>
        </div>
      </article>
      </BuddyTurnInspection>
    );
  };
  const displayedConversation = [
    ...groupConversationAttempts(conversationDisplay.events,
      event => event.kind === "world" ? event.turn : null,
      new Set(buildCompose.items.map(item=>item.afterSequence)))
      .map(({item:event,previous}, index) => ({
        order: event.kind === "world" ? event.turn.sequence : event.position.afterSequence + .25,
        ordinal: index, element: renderConversationEvent(event, previous),
      })),
    ...buildCompose.items.map((item, index) => ({ order: item.afterSequence + .5, ordinal: index, element: item.element })),
  ].sort((left, right) => left.order - right.order || left.ordinal - right.ordinal);
  const recoveryRecordCount = savedAskRecords.length + pendingCommands.filter((item) => item.envelope !== null || item.error).length
    + pendingAsks.filter((item) => item.error).length;
  const pendingNewConversation = pendingCommands.some((item) => item.envelope !== null);
  const newConversationDisabledReason = newConversationSending
    ? "A new conversation is already starting."
    : pendingNewConversation
      ? "A previous new-conversation request is awaiting confirmation. Check its status before starting another."
    : surfacePreparing || sending || composing || Boolean(sharedConversation?.pendingTurn) || Boolean(pendingPlayTurn) || Boolean(pendingPlayLoadError)
        ? "Wait for the current message to finish before starting a new conversation."
        : historyLoading
          ? "Conversation history is still loading."
          : !history
            ? historyError
              ? "Conversation history is unavailable. Refresh it before starting a new conversation."
              : "Conversation history is not ready yet."
            : null;

  const newConversationButton = (
    <button
      className={presentationHosts || isReadOnly ? "conversation-dock__icon-button" : undefined}
      type="button"
      onClick={startNewConversation}
      disabled={newConversationDisabledReason !== null}
      aria-label="New conversation"
      title={newConversationDisabledReason ?? "New conversation"}
      aria-describedby={newConversationDisabledReason ? "world-plan-new-conversation-disabled-reason" : undefined}
    >
      {newConversationSending ? "…" : (presentationHosts || isReadOnly) ? <svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true"><path d="M12 5v14M5 12h14" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" /></svg> : "New conversation"}
    </button>
  );
  const headerActions = (
    <div className="world-plan-agent-conversation__actions">
            <button type="button" aria-expanded={settingsOpen} aria-controls="world-plan-agent-settings" onClick={() => setSettingsOpen((open) => !open)}>
              {settingsOpen ? "Close settings" : "Settings"}
            </button>
            {!isReadOnly && (!presentationHosts || presentationHosts.newConversation === undefined) ? newConversationButton : null}
            {newConversationDisabledReason ? (
              <p id="world-plan-new-conversation-disabled-reason" className="world-plan-agent-conversation__management-reason" role="note">
                Unavailable right now: {newConversationDisabledReason}
              </p>
            ) : null}
          </div>
  );
  const buildContextDetails = <><LoadedWorldGraphExplorer />{buildMode?.savedSource ? <p>Buddy uses the saved source “{buildMode.savedSource.title}”. Unsaved edits stay in the editor. Source material is separate from admitted World Graph facts.</p> : <p role="note">No source context is loaded. World retrieval alone cannot start a Buddy turn.</p>}
    <button type="button" aria-pressed={useWorldGraphForAsk} disabled={!buildMode?.savedSource} onClick={() => setUseWorldGraphForAsk(value => !value)}>
      Use {worldName} facts · {useWorldGraphForAsk ? "On" : "Off"}</button></>;
  const playContextDetails = <><p>Buddy uses the verified current World Run. Each submitted turn keeps its original moment.</p>
    <button type="button" aria-pressed={useWorldGraphForAsk} disabled={!playMode?.admittedRun}
      onClick={() => setUseWorldGraphForAsk(value => !value)}>{`Use ${worldName} facts · ${useWorldGraphForAsk ? "On" : "Off"}`}</button></>;
  const contextDetails = isBuild ? buildContextDetails : isReadOnly ? playContextDetails : (
    <div className="world-plan-agent-conversation__header-context" role="group" aria-label="What Buddy uses and where changes go">
          <section className="world-plan-agent-conversation__context-section" aria-label="Question sources">
            <LoadedWorldGraphExplorer />
            <h3>Answers use</h3>
            <p className="world-plan-agent-conversation__context-summary">
              The saved Plan{playableTarget ? "" : " in full"}.
            </p>
            <button
              className="world-plan-agent-conversation__world-context-toggle"
              type="button"
              aria-pressed={useWorldGraphForAsk}
              disabled={!scopeMatches || !verifiedWorldId}
              onClick={() => setUseWorldGraphForAsk((enabled) => !enabled)}
              title={`Choose whether Buddy can use established facts from ${worldName} in a new question.`}
            >
              {`Use ${worldName} facts · ${useWorldGraphForAsk ? "On" : "Off"}`}
            </button>
            <p className="world-plan-agent-conversation__context-summary">Allows World retrieval. Each reply shows which sources it used.</p>
            {playableTarget ? (
              <div role="group" aria-label="Question focus" className="world-plan-agent-conversation__context-target">
                <span>Focus: {playableTargetLabel || playableTarget.id.replace(/^[^:]+:/, "")}</span>
                <button type="button" aria-label="Clear Ask target" onClick={onClearPlayableTarget}>Clear focus</button>
              </div>
            ) : null}
          </section>
          <section className="world-plan-agent-conversation__context-section" aria-label="Plan changes">
            <h3>Plan changes</h3>
            <p className="world-plan-agent-conversation__context-summary">
              Buddy will propose changes to {effectiveEditTarget ? "the selected card" : editorSelectionActive ? "the selected text" : "the cursor in the Plan"} and show a preview before you apply them.
            </p>
            {effectiveEditTarget ? (
              <div role="group" aria-label="Selected change target" className="world-plan-agent-conversation__context-target">
                <span>Target: {(playableEditTarget ? playableEditTargetLabel : playableTargetLabel) || effectiveEditTarget.id.replace(/^[^:]+:/, "")}</span>
                {playableEditTarget ? <button type="button" aria-label="Clear edit target" onClick={onClearPlayableEditTarget}>Clear target</button> : null}
              </div>
            ) : null}
          </section>
          {playableTargetStale ? (
            <p className="world-plan-agent-conversation__target-warning" role="alert">
              The Ask target is stale. Select it again or clear the target before asking.
            </p>
          ) : null}
          {effectiveEditTargetStale ? (
            <p className="world-plan-agent-conversation__target-warning" role="alert">
              The edit target is stale. Select it again before composing a proposal.
            </p>
          ) : null}
        </div>
  );
  const connectionSettings = (
      <section id="world-plan-agent-settings" className="world-plan-agent-conversation__settings" aria-label="Local operator Agent and Graph authorization">
        <h3>Local connection</h3>
        <button type="button" onClick={() => setSettingsOpen(false)}>Close connection settings</button>
        <button type="button" onClick={connectGraphSession}>Connect local session</button>
        <button type="button" onClick={clearGraphSession}>Revoke local session</button>
        <p role="note">This connects this browser to your local Buddy server. Once connected, it stays connected across reloads.</p>
        {graphCredentialStatus ? <p role="status">{graphCredentialStatus}</p> : null}
      </section>
  );
  const managementDetails = (<>
      {verifiedWorldId&&<><button type="button" onClick={()=>setLibraryOpen(true)}>Conversations…</button>
        {libraryOpen&&<ConversationLibrary key={verifiedWorldId} worldId={verifiedWorldId} onClose={()=>setLibraryOpen(false)}/>}</>}

      {playMode ? <div role="group" aria-label="Play message action">
          <button type="button" aria-pressed={!playEditMode} onClick={() => setPlayEditMode(false)}>Discuss</button>
          <button type="button" aria-pressed={playEditMode} onClick={() => setPlayEditMode(true)} disabled={!playMode.sceneEditBridge}>Propose scene edit</button>
          {playEditMode ? <p>Review a change to the current scene in this session copy. The Plan stays intact.</p> : null}
        </div> : null}
      <BuddyReadiness active={visible && agent.paneState.isOpen} surface={isBuild ? "build" : isReadOnly ? "play" : "plan"}
        worldGraph={useWorldGraphForAsk} blockedReason={composerBusy ? (
          sending || composing || buildCompose.busy || playCompose.busy ? "A request is running."
          : pendingPlayTurn || sharedConversation?.pendingTurn || pendingPlayLoadError || pendingPlayRecoveryHydrating
            ? "Resolve the saved request in Conversation options before sending another."
            : historyError ? "Conversation history could not be checked."
            : historyLoading || !history ? "Checking saved conversation history."
            : "Current work is not ready for submission."
        ) : null} />
      {settingsOpen ? connectionSettings : null}
      {isReadOnly ? <details><summary>Advanced</summary>
        {playMode?.admittedRun ? <p>Run {playMode.admittedRun.runId} · revision {playMode.admittedRun.runRevision}</p> : null}
        <button type="button" onClick={refreshWorldHistory} disabled={historyLoading}>Refresh World history</button>
      </details> : null}
      <section className="world-plan-agent-conversation__tools" aria-label="Agent tools and access">
        <h3>Tools and access</h3>
        <p>Configured for this page. Each reply’s Prompt shows the tools actually exposed to the model.</p>
        <dl>
          <dt>Read saved page</dt><dd>{isBuild ? buildMode?.savedSource ? "Connected" : "Save or choose a page first" : isReadOnly ? currentReadOnlyContext ? "Connected" : "Open a Run first" : scopeMatches ? "Connected" : "Open a saved Plan first"}</dd>
          <dt>World Graph and sources</dt><dd>{useWorldGraphForAsk ? "Enabled" : "Off"}</dd>
          <dt>Propose page changes</dt><dd>{isBuild ? buildMode?.composeBridge ? "Editor connected; insertion is checked when sending. Preview and approval required." : "No editable page connected" : isReadOnly ? playMode?.sceneEditBridge ? "Current scene connected; preview and approval required. Changes save to the session copy." : "Open a saved session scene first" : editBridge ? "Preview and approval required" : "No editable Plan connected"}</dd>
          <dt>Generate images</dt><dd>{isBuild ? buildMode?.composeBridge ? "Prepare an image prompt from this page and conversation, then review it in Image Studio. Generate, Save and Insert are explicit." : "Open an editable saved page first." : "Not exposed on this surface."}</dd>
        </dl>
        <p>Enter to send · Shift+Enter for a new line.</p>
      </section>
      {pendingPlayTurn && !sending && requestRef.current === null ? <section className="world-plan-agent-conversation__recovery-notice" aria-label="Saved turn recovery">
        <p>This request needs recovery. You can check its saved status or retry the exact request.</p>
        <details><summary>Saved request details</summary>
          <p>{pendingPlayTurn.request.message}</p>
          <p>Request: {pendingPlayTurn.request.turn_id} · Source: {pendingPlayTurn.request.primary_work.object_id} · Revision: {pendingPlayTurn.request.primary_work.expected_revision}</p>
          {pendingPlayTurn.request.primary_work.kind === "build" ? <p>Source digest: {pendingPlayTurn.request.primary_work.expected_content_sha256}</p> : null}
        </details>
        <button type="button" onClick={refreshWorldHistory} disabled={historyLoading}>Refresh World history</button>
        <button type="button" onClick={() => { void dispatchSavedPlayTurn(pendingPlayTurn); }} disabled={sending || buildCompose.busy || requestRef.current !== null}>
          Retry exact saved turn
        </button>
      </section> : null}

      {otherLocalProposals.length ? (
        <details className="world-plan-agent-conversation__local-activity" aria-label="Other local Plan proposals">
          <summary>Other local proposals · {otherLocalProposals.length}</summary>
          <p className="world-plan-agent-conversation__context">
            These browser-saved proposals could not be matched to this World conversation. They are kept separate and are not current Plan actions.
          </p>
          {otherLocalProposals.map((turn) => renderProposalEvent(
            turn,
            localProposalPositionsByTurnId.get(turn.turnId) ?? null,
            true,
          ))}
        </details>
      ) : null}
      {recoveryRecordCount ? (
      <>
      {unconfirmedAskCount > 0 ? (
        <div className="world-plan-agent-conversation__recovery-notice" role="status">
          <span>{unconfirmedAskCount} saved Ask outcome{unconfirmedAskCount === 1 ? " needs" : "s need"} a history check. Nothing will be resent.</span>
          <button type="button" onClick={refreshWorldHistory} disabled={historyLoading || !scopeMatches}>Refresh World history</button>
        </div>
      ) : null}
      <details className="world-plan-agent-conversation__recovery-details">
        <summary>{unconfirmedAskCount > 0
          ? `Needs attention · ${unconfirmedAskCount} outcome${unconfirmedAskCount === 1 ? "" : "s"} unconfirmed`
          : `Saved request recovery · ${recoveryRecordCount}`}</summary>
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
          <p>Resolve verifies an existing result or retires an unexecuted request so it cannot run later. It does not start a new conversation.</p>
          <p>A prior command has an uncertain outcome. Check its saved receipt without resending. An explicit retry keeps its original command ID and pointer snapshot.</p>
          {pendingCommands.filter((item): item is StoredPendingNewConversation & { envelope: WorldPlanPendingNewConversation } => item.envelope !== null)
            .map((item) => (
              <div key={item.storageKey}>
                <p>Command {item.envelope.request.command_id} · original pointer revision {item.envelope.request.expected_pointer_revision}</p>
                <button type="button" disabled={commandStatusChecking || newConversationSending || sending || composing}
                  onClick={() => { void checkNewConversationCommand(item); }}>
                  {commandStatusChecking ? "Checking status…" : "Check saved New Conversation status"}
                </button>
                <button type="button" disabled={commandStatusChecking || newConversationSending || sending || composing}
                  onClick={() => { void resolveSavedCommand(item, "resolve"); }}>Resolve saved New Conversation request</button>
                <button type="button" disabled={commandStatusChecking || newConversationSending || sending || composing}
                  onClick={() => { void resolveSavedCommand(item, "lookup"); }}>Check saved resolution record</button>
                <button type="button" disabled={commandStatusChecking || newConversationSending || sending || composing}
                  onClick={() => { void sendNewConversationCommand(item); }}>Retry saved New Conversation command</button>
              </div>
            ))}
        </section>
      ) : null}
      {blockedResolution ? <section aria-label="Blocked request acknowledgement">
        <p>This submitted request cannot execute: its command ID is occupied by a different immutable binding. Acknowledging clears only the matching saved request; its operation identity, the successful command and all history remain intact.</p>
        <button type="button" disabled={commandStatusChecking} onClick={() => settleCommandResolution(blockedResolution)}>Acknowledge blocked submitted request</button>
      </section> : null}
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
            ? `Ask recovery · ${unconfirmedAskCount} outcome${unconfirmedAskCount === 1 ? "" : "s"} unconfirmed · ${confirmedFailureCount} recorded failure${confirmedFailureCount === 1 ? "" : "s"} · ${savedAskRecords.length} saved`
            : `Pending recovery · ${savedAskRecords.length}`}</h3>
      {pendingAsks.some((item) => item.envelope !== null) ? (
            <p>{confirmedFailureCount > 0
              ? `${unconfirmedAskCount} Ask outcome${unconfirmedAskCount === 1 ? " remains" : "s remain"} unconfirmed in saved World history; ${confirmedFailureCount} failed turn${confirmedFailureCount === 1 ? " is" : "s are"} already recorded. All ${pendingAskRecords.length} Ask records remain saved. Refresh never reposts them.`
              : "Saved Asks stay in browser storage. Saved World history may confirm completion or record a failure; Refresh never reposts them."}</p>
          ) : null}
          {pendingAsks.filter((item): item is StoredPendingAsk & { envelope: WorldPlanPendingAskEnvelope } => item.envelope !== null)
            .map((item) => {
              const graphAsk = Boolean(item.envelope.request.plan_context_policy);
              const terminalFailureConfirmed = isPendingAskFailureConfirmed(item);
              return (
                <details key={item.storageKey}>
                  <summary>
                    {graphAsk ? "Graph Ask" : "Ask"} · {item.envelope.request.turn_id}
                    {terminalFailureConfirmed ? " · failure confirmed" : ""}
                  </summary>
                  <p>Turn ID · <code>{item.envelope.request.turn_id}</code></p>
                  <p>Status · {terminalFailureConfirmed
                    ? "terminal failure confirmed in saved World history"
                    : "outcome not confirmed in saved World history"}</p>
                  <p>Plan object revision {item.envelope.origin.objectRevision} · content revision {item.envelope.origin.revisionN} · conversation {item.envelope.origin.conversationId ?? "not yet active"}</p>
                  <p role="status">{terminalFailureConfirmed
                    ? "Saved World history records this turn as failed. The saved recovery record is preserved; Refresh will not repost it."
                    : "Saved World history has not confirmed this Ask. Refresh checks its original conversation and Plan basis without reposting it."}</p>
                </details>
              );
            })}
        </section>
      ) : null}
      </details>
      </>
      ) : pendingCommandLoadError || pendingAskLoadError ? (
        <details className="world-plan-agent-conversation__recovery-details">
          <summary>Saved request recovery · needs attention</summary>
          {pendingCommandLoadError ? <p role="alert">{pendingCommandLoadError}</p> : null}
          {pendingAskLoadError ? <p role="alert">{pendingAskLoadError}</p> : null}
        </details>
      ) : null}
      <details className="world-plan-agent-conversation__advanced">
        <summary>Advanced details</summary>
        <div className="world-plan-agent-conversation__advanced-content">
          {playableTarget ? (
            <section aria-label="Ask target details">
              <h3>Ask source</h3>
              <p>Ask uses the committed Plan. Unsaved editor changes are excluded; the selected card identifies the Ask target.</p>
              {playableTargetBasis ? (
                <p>Card basis · object revision {playableTargetBasis.revision} · SHA-256 <code>{playableTargetBasis.contentSha256}</code></p>
              ) : <p>The selected card basis is still being verified.</p>}
            </section>
          ) : null}
          {playableEditTarget ? (
            <section aria-label="Edit target details">
              <h3>Edit source</h3>
              <p>
                This proposal uses the {playableEditTargetDirty ? "unsaved Plan draft" : "current Plan draft"}.
                Apply changes only the mounted draft; Save keeps the changes.
              </p>
            </section>
          ) : null}
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
                    <ActionPromptInspector worldId={action.basis.world_id} actionId={action.action_id} />
                    {action.status !== "completed" && <ActionTerminalDiagnostic worldId={action.basis.world_id} actionId={action.action_id} />}
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
    </>);
  const messages = (
    <div className="world-plan-agent-conversation__body">
      {newConversationError ? <p role="alert">{newConversationError}</p> : null}
      {pendingPlayLoadError ? <p role="alert">{pendingPlayLoadError}</p> : null}
      {presentationHosts && playableTargetStale ? <p role="alert">The Ask target is stale. Select it again before asking.</p> : null}
      {presentationHosts && effectiveEditTargetStale ? <p role="alert">The edit target is stale. Select it again before composing a proposal.</p> : null}
      {authorizationBlocked ? (
        <section className="world-plan-agent-conversation__auth-notice" role="alert">
          <p>{pendingSavedAsk
            ? "Local authorization was rejected. Reconnect in Settings, then refresh World history before taking another action."
            : "Local authorization was rejected. Reconnect in Settings, then refresh history or retry the saved request."}</p>
          <button type="button" onClick={openConnectionSettings}>Open Settings</button>
        </section>
      ) : null}
      {saveInFlight ? (
        <p className="world-plan-agent-conversation__saving" role="status">Conversation paused while the Plan is saving.</p>
      ) : null}
      <section className="world-plan-agent-conversation__turns" aria-label="World conversation transcript" aria-live="polite" aria-busy={historyLoading || !history}>

        {historyLoading && !history ? <p className="world-plan-agent-conversation__loading" role="status">Loading conversation…</p> : null}
        {historyError ? (
          <div role="group" aria-label="World history unavailable">
            {authorizationBlocked
              ? null
              : <p>{historyError}</p>}
            <button type="button" onClick={refreshWorldHistory} disabled={historyLoading}>Refresh World history</button>
          </div>
        ) : null}
        {history?.next_before_sequence !== null && history?.next_before_sequence !== undefined ? (
          <button type="button" className="world-plan-agent-conversation__older-page" onClick={() => { void loadOlderTurns(); }} disabled={olderLoading || historyLoading}>
            {olderLoading ? "Loading earlier messages…" : "Load earlier messages"}
          </button>
        ) : null}
        {displayedConversation.map(item => item.element)}
        {playMode ? playCompose.review : null}
        {isBuild && buildCompose.error ? <p role="alert">{buildCompose.error}</p> : null}
        {!isReadOnly ? conversationActions.map(renderConsultedAction) : null}
        {!isReadOnly && conversationActionsError ? <p role="alert">{conversationActionsError}</p> : null}
        {unmatchedSubmittedMessage && submittedMessage && !pendingRetryTurnId ? (
          <article aria-label="Submitted message">
            <p><strong>You:</strong> {submittedMessage.message}</p>
            {uncertainPlayNoticeRef.current?.turnId === submittedMessage.id ? <div className="world-plan-agent-conversation__reply-failure" role="alert">
              <p>Buddy couldn’t finish this reply. Your message is saved. Open Conversation options to check its status or retry.</p>
              <details className="world-plan-agent-conversation__technical-details"><summary>Technical details</summary><p>{uncertainPlayNoticeRef.current.message}</p></details>
            </div> : null}
            {uncertainPlanNoticeRef.current?.turnId === submittedMessage.id ? (
              <div className="world-plan-agent-conversation__turn-debug">
                <details className="world-plan-agent-conversation__turn-details">
                  <summary>Debug</summary>
                  <p className="world-plan-agent-conversation__context">
                    Delivery · {uncertainPlanNoticeRef.current.message}
                  </p>
                </details>
              </div>
            ) : null}
          </article>
        ) : null}
        {conversationNotice && conversationNotice !== "The server confirmed this Ask. World history refreshed."
          ? <p role="status">{conversationNotice}</p> : null}
        {(presentationHosts || isReadOnly) && newReplyAvailable ? (
          <button type="button" className="world-plan-agent-conversation__new-reply" onClick={jumpToLatestReply}>
            Jump to latest reply
          </button>
        ) : null}
      </section>
      {!presentationHosts && !isReadOnly ? managementDetails : null}
    </div>
  );
  const activityBusy = sending || composing || buildCompose.busy || playCompose.busy;
  const pendingActivityId = activityBusy ? sharedConversation?.pendingTurn?.turnId
    ?? pendingPlayTurn?.request.turn_id
    ?? (submittedMessage?.scopeKey === scopeKey ? submittedMessage.id : null) : null;
  // Client request UUIDs are not APP turn UUIDs. History admits the durable
  // identity through the persisted idempotency key, never through row recency.
  const pendingActivityMatches = pendingActivityId && history?.world_id === verifiedWorldId
    ? history.turns.filter(turn => {
      if (turn.turn_id === pendingActivityId) return true;
      return submittedMessage?.scopeKey === scopeKey && submittedMessage.id === pendingActivityId
        && submittedMessage.conversationId === history.conversation_id
        && Boolean(submittedMessage.idempotencyKey)
        && "idempotency_key" in turn && turn.idempotency_key === submittedMessage.idempotencyKey
        && turn.user_text === submittedMessage.message
        && turn.provenance.world_id === verifiedWorldId
        && turn.provenance.surface_id === (isBuild ? "build" : isReadOnly ? "play" : "plan")
        && turn.provenance.primary_work.object_id === (isBuild ? buildMode?.savedSource?.documentId
          : isReadOnly ? playMode?.admittedRun?.runId : documentId);
    }) : [];
  const activityTurn = activityBusy
    ? pendingActivityMatches.length === 1 ? pendingActivityMatches[0] : undefined
    : [...(history?.turns ?? [])].sort((a,b)=>b.sequence-a.sequence)[0];
  const activityTurnId = activityTurn?.turn_id;
  const activityLifecycle = activityTurn?.lifecycle_status ?? 'running';
  const composer = (
    <section className="world-plan-agent-conversation__composer" aria-label="Conversation composer">
      {requestedSurfaceTurn?.status==='failed'&&<div role="status">
        <button type="button" onClick={()=>retrySurfaceConversationRequest(requestedSurfaceTurn.id)}>↻ Try build out</button>
        <button type="button" onClick={()=>cancelSurfaceConversationRequest(requestedSurfaceTurn.id)}>Dismiss</button>
      </div>}
      {sharedConversation?.worldId === worldId && sharedConversation.composerDraftWarning
        ? <p role="status">{sharedConversation.composerDraftWarning}</p> : null}

      {activityTurnId && verifiedWorldId && history?.conversation_id ? <BuddyTurnInspection
        key={`activity:${verifiedWorldId}:${history.conversation_id}:${activityTurnId}`}
        worldId={verifiedWorldId} conversationId={history.conversation_id} turnId={activityTurnId}
        lifecycle={activityLifecycle}>
        <BuddyActivity worldId={verifiedWorldId} conversationId={history.conversation_id} turnId={activityTurnId} lifecycle={activityLifecycle} />
      </BuddyTurnInspection> : activityBusy ? <div className="world-plan-agent-conversation__working" role="status">
        Getting things ready…
      </div> : null}

      {!sending && !composing && !buildCompose.busy && !playCompose.busy
        && Boolean(sharedConversation?.pendingTurn || pendingPlayTurn || pendingPlayLoadError) ? (
          <p className="world-plan-agent-conversation__notice" role="status">
            Check the previous request before sending. You can keep drafting.{" "}
            <button type="button" onClick={() => {
              const options = presentationHosts?.header?.closest("details") ?? connectionOptionsRef.current;
              if (options instanceof HTMLDetailsElement) options.open = true;
            }}>Check saved request</button>{" "}
            {pendingPlayTurn ? <button type="button"
              disabled={requestRef.current !== null}
              onClick={() => { void dispatchSavedPlayTurn(pendingPlayTurn); }}>Retry</button> : null}
          </p>
        ) : null}
      {visibleBuildPlacementFailure ? <section aria-label="Page proposal unavailable">
        <p role="alert">Buddy could not prepare a page proposal. {visibleBuildPlacementFailure.reason} Your message has not been sent.</p>
        <p>You can correct the page or insertion point and send again. Discussion includes your current draft. It won’t place writing on the page.</p>
        <button type="button" disabled={composerBusy || !composerMessage.trim()}
          onClick={() => { void submitPlay(undefined, true); }}>Send as discussion</button>
      </section> : null}
      <form onSubmit={isReadOnly ? (event) => { void submitPlay(event); } : submitComposer}>


        {!isReadOnly ? <p className="world-plan-agent-conversation__context" aria-label="Actual Plan change target">{displayedEditScope}</p> : null}
        {!isReadOnly && detectedComposerIntent === "propose" && !effectiveEditTarget && !editorSelectionActive ? (
          <details className="world-plan-agent-conversation__target-disclosure">
            <summary>
              {selectedSectionTargetLabel
                ? `Change target · ${selectedSectionTargetLabel}`
                : "Change target · selected text or cursor"}
              <span className="world-plan-agent-conversation__target-action">Choose section</span>
            </summary>
            <div className="world-plan-agent-conversation__target" role="group" aria-label="Choose where the proposed edit applies">
              <select
                id="world-plan-agent-plan-section"
                aria-label="Plan section (optional)"
                aria-describedby="world-plan-agent-target-help"
                value={selectedSectionTargetId}
                disabled={intentBusy || sectionTargets.length === 0 || Boolean(playableEditTarget)}
                onChange={(event) => { void selectPlanSection(event.currentTarget.value); }}
              >
                <option value="">Use the editor selection or caret</option>
                {sectionTargets.map((target) => (
                  <option key={target.id} value={target.id} disabled={Boolean(target.unavailableReason)} title={target.unavailableReason ?? undefined}>
                    {target.unavailableReason ? `${target.label} — unavailable` : target.label}
                  </option>
                ))}
              </select>
              <button type="button" aria-label="Refresh sections" onClick={() => { void refreshPlanSections(); }} disabled={intentBusy}>
                Refresh
              </button>
              <span id="world-plan-agent-target-help" className="sr-only">
                A selection in the editor takes precedence. With no selected text, the proposal inserts at the cursor.
              </span>
              {sectionTargetStatus?.kind === "status" ? <p role="status">{sectionTargetStatus.message}</p> : null}
            </div>
          </details>
        ) : null}
        {!isReadOnly && sectionTargetStatus?.kind === "error" && detectedComposerIntent === "propose" ? (
          <p className="world-plan-agent-conversation__target-error" role="alert">{sectionTargetStatus.message}</p>
        ) : null}
        <label className="sr-only" htmlFor="world-plan-agent-message">Message DungeonBuddy</label>
        <textarea
          id="world-plan-agent-message"
          rows={1}
          value={composerMessage}
          onChange={(event) => {
            composerEditGenerationRef.current += 1;
            setComposerMessage(event.currentTarget.value);
            setComposerIntentCorrection(null);
            setError(null);
            setEditError(null);
          }}
          onKeyDown={handleComposerKeyDown}
          disabled={isReadOnly ? !currentReadOnlyContext : !scopeMatches}
          placeholder={isReadOnly ? (isBuild ? "Ask about your World, or ask me to add something to this page…" : playEditMode ? "Tell Buddy what to change in this scene…" : "Ask about this Run…") : "Ask Buddy, or tell it what to change…"}
          aria-describedby={`world-plan-agent-composer-hint${buildSourceMissing ? ` ${BUILD_SOURCE_REQUIRED_DESCRIPTION_ID}` : ""}`}
        />
        <div className="world-plan-agent-conversation__composer-footer">
          {buildSourceMissing ? <>
            <p id={BUILD_SOURCE_REQUIRED_DESCRIPTION_ID} className="world-plan-agent-conversation__notice" role="note" style={{ gridColumn: "1 / -1" }}>
              {buildSourceRequiredMessage()}
            </p>
            <button type="button" aria-describedby={BUILD_SOURCE_REQUIRED_DESCRIPTION_ID} onClick={focusBuildSourceSelector}>Choose a source</button>
            <button type="button" aria-describedby={BUILD_SOURCE_REQUIRED_DESCRIPTION_ID} onClick={openBuildSourceActions}>Open source actions</button>
          </> : null}
          {isBuild && !useWorldGraphForAsk ? <p role="note">Discussion only. Page proposals are available with World facts enabled.</p> : null}
          <p id="world-plan-agent-composer-hint" className="sr-only">
            {buildSourceMissing
              ? "Sending is disabled until a saved source is available."
              : !isReadOnly && detectedComposerIntent === "propose"
              ? `Plan change${effectiveEditTarget ? ` · ${(playableEditTarget ? playableEditTargetLabel : playableTargetLabel) || effectiveEditTarget.id}` : editorSelectionActive ? " · selected text" : ""} · Buddy will show a preview before anything is applied.`
              : "Enter to send · Shift+Enter for a new line."}
          </p>
          {!isReadOnly && composerMessage.trim() ? (
            <details className="world-plan-agent-conversation__route-correction">
              <summary>{detectedComposerIntent === "propose" ? "Plan change · Change" : "Question · Change"}</summary>
              <div role="group" aria-label="Choose how Buddy handles this message">
                <button type="button" onClick={() => setComposerIntentCorrection({ message: composerMessage, intent: "discuss" })}>
                  Answer as a question
                </button>
                <button type="button" onClick={() => setComposerIntentCorrection({ message: composerMessage, intent: "propose" })}>
                  Request a Plan change
                </button>
              </div>
            </details>
          ) : null}
          <button
            type="submit"
            aria-label={!isReadOnly && detectedComposerIntent === "propose" ? "Propose edit" : "Send message"}
            aria-describedby={buildSourceMissing ? BUILD_SOURCE_REQUIRED_DESCRIPTION_ID : undefined}
            disabled={composerBusy || !composerMessage.trim()
            || (!isReadOnly && detectedComposerIntent === "discuss" && playableTargetStale)
            || (!isReadOnly && detectedComposerIntent === "propose" && (effectiveEditTargetStale || !editBridge))}
          >
            {sending || composing || buildCompose.busy || playCompose.busy ? "Working…" : saveInFlight ? "Saving…" : "Send"}
          </button>
        </div>
        {error && !authorizationBlocked && !hasUncertainPlanNotice && !hasUncertainPlayNotice ? <p role="alert">{error}</p> : null}
        {editError && !authorizationBlocked ? <p role="alert">{editError}</p> : null}
        {!isReadOnly && detectedComposerIntent === "propose" && !editBridge ? (
          <p className="world-plan-agent-conversation__context" role="note">Plan changes are unavailable on this surface.</p>
        ) : null}
      </form>
    </section>
  );
  if (isReadOnly && !presentationHosts) {
    if (!askSlot?.hostElement || !agent.paneState.isOpen) return null;
    const admittedRun = playMode?.admittedRun;
    return createPortal(
      <section className="world-plan-agent-conversation world-agent-conversation" aria-label="World conversation" data-testid="world-agent-conversation-host">
        <ConversationDock className="plan-conversation-dock world-agent-conversation__dock" reader={null} readerLabel={isBuild ? "Build workspace" : "Play workspace"}
          conversationLabel="World conversation" title="Conversation" showTitle={false}
          contextLabel={isBuild ? `${worldName} · ${buildMode?.savedSource?.title ?? "Build"}` : `${worldName} · Play${admittedRun?.beatTitle ? ` · ${admittedRun.beatTitle}` : ""}${admittedRun?.sceneTitle ? ` · ${admittedRun.sceneTitle}` : ""}`}
          initialHeight={360} minHeight={240} minimumReaderHeight={0} collapseMode="launcher" fullscreenEnabled
          expanded={agent.paneState.isOpen} onExpandedChange={agent.setPaneOpen}
          headerActions={newConversationButton} menuRef={connectionOptionsRef} menuActions={<><div ref={askSlot.setMenuHost}/>{headerActions}{managementDetails}</>}
          contextDetails={isBuild ? buildContextDetails : playContextDetails}
          messages={<div ref={playMessagesHostRef} className="plan-conversation-dock__messages">{messages}</div>}
          composer={<div className="plan-conversation-dock__composer">{composer}
            {!currentReadOnlyContext && !isBuild ? <p role="status">Choose a verified World Run to ask about Play.</p> : null}

</div>} />
      </section>, askSlot.hostElement,
    );
  }
  if (presentationHosts) {
    return <>
      {buildCompose.pageElement}
      {presentationHosts.header && createPortal(<>{headerActions}{managementDetails}</>, presentationHosts.header)}
      {presentationHosts.newConversation && createPortal(newConversationButton, presentationHosts.newConversation)}
      {presentationHosts.context && createPortal(contextDetails, presentationHosts.context)}
      {presentationHosts.messages && createPortal(messages, presentationHosts.messages)}
      {presentationHosts.composer && createPortal(composer, presentationHosts.composer)}
    </>;
  }
  if (!askSlot?.hostElement) return null;
  return createPortal(
    <section className="world-plan-agent-conversation" aria-label="Saved World Plan conversation">
      <header className="world-plan-agent-conversation__header">
        <div className="world-plan-agent-conversation__header-main">
          <div className="world-plan-agent-conversation__header-title">
            <h2>Plan conversation</h2>
            <p>{worldName} · {displayedSavedPlanVersion?.status === "verified"
              ? `Saved Plan · version ${displayedSavedPlanVersion.revisionN}`
              : displayedSavedPlanVersion?.status === "unavailable"
                ? "Saved Plan version unavailable"
                : "Checking saved Plan version…"}</p>
          </div>
          {headerActions}
        </div>
        {contextDetails}
      </header>
      {messages}
      {composer}
    </section>,
    askSlot.hostElement,
  );
}
