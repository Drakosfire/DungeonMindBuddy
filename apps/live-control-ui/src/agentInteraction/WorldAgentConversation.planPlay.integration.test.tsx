import {WorldGuidedTour} from '../guidedTour/WorldGuidedTour';
import {useGuidedTour} from '../guidedTour/GuidedTour';
import {createWalkthrough,reduceTour,type TargetPin} from '../guidedTour/protocol';
import {readWalkthrough,writeWalkthrough,pointerKey} from '../guidedTour/storage';
import type {ReactNode} from 'react';
import {Editor} from '@tiptap/core';
import {DEFAULT_MARKDOWN_EDITOR_EXTENSIONS} from '../tiptap/MarkdownEditorCore';
import {createBuildComposeBridge,type BuildComposeEditorState} from '../buildSurface/buildComposeBridge';
import type {BuildObjectConstructionProgress} from '../api/buildConstructionStream';
import * as graphLensProjection from '../graphLens/useWorldGraphLensProjection';
import {authoredGraphReferences,readComposerReferences,writeComposerReferences,composerReferenceKey} from './authoredGraphReferences';
import {getWorkPlan,continueWorkPlan} from '../api/conversationWorkPlanApi';
vi.mock('../api/conversationWorkPlanApi',async original=>({...await original<typeof import('../api/conversationWorkPlanApi')>(),getWorkPlan:vi.fn(async()=>null),saveWorkPlan:vi.fn(),continueWorkPlan:vi.fn()}));
vi.mock('../api/conversationLibraryApi',()=>({
 listConversations:vi.fn(async(world:string,status:string)=>({schema:'dmb_conversation_library_v1',world_id:world,status,items:[{conversation_id:'33333333-3333-4333-8333-333333333333',world_id:world,title:'Archived named work',status:'archived',name_revision:1,turn_count:1,created_at:'2026-10-24T00:00:00Z',updated_at:'2026-10-24T00:00:00Z'}],next_before:null})),
 readConversationName:vi.fn(async(world:string,id:string)=>({conversation_id:id,world_id:world,title:'Archived named work',status:'archived',name_revision:1,turn_count:1,created_at:'2026-10-24T00:00:00Z',updated_at:'2026-10-24T00:00:00Z'})),
 readConversationTurns:vi.fn(async(world:string,id:string)=>({schema:'dmb_conversation_library_turns_v1',world_id:world,conversation_id:id,turns:[{turn_id:'44444444-4444-4444-8444-444444444444',sequence:1,status:'completed',user_text:'Archived library question',assistant_text:'Archived library answer'}],next_before_sequence:null})),renameConversation:vi.fn(),
}));
import {queueSurfaceConversationRequest,cancelSurfaceConversationRequest,claimSurfaceConversationRequest} from "./surfaceConversationRequests";
import { COMPOSER_DRAFT_WRITE_WARNING } from "./conversationComposerDrafts";
import { listBuildProposals } from "../api/buildDocumentProposalApi";
vi.mock("../api/buildDocumentProposalApi", async (original) => ({
  ...await original<typeof import("../api/buildDocumentProposalApi")>(), listBuildProposals: vi.fn(async () => []),
}));
import type { BuildComposeBridge, CapturedBuildInsertion } from "../buildSurface/buildComposeBridge";
import { nativePlayContextFixture, nativePlayProvenanceFixture, nativePlayRequestFixture, nativePlaySourceFixture } from '../test/nativePlayContextFixture';
import { rulesAnswerFixture, rulesUnclaimedFixture, fixtureHash } from '../test/rulesAnswerFixture';
import { rulesCanonical } from '../rulesLookup/rulesEvidence';
import { listPlaySceneEdits, proposePlaySceneEdit, type PlaySceneEditRecord } from "../api/playSceneEditApi";
import { getWorldPlayRunContent, getWorldPlayRunContentCommand, putWorldPlayRunContentCommand } from "../api/playRunContentApi";
import { PlaySessionContentEditor } from "../playSurface/content/PlaySessionContentEditor";
import type { PlayRunContent } from "../playSurface/playRunContentTypes";
import { contentSha256 } from "../playSurface/playRunEffectiveContent";
vi.mock("../api/playSceneEditApi", () => ({ listPlaySceneEdits: vi.fn(async () => []), proposePlaySceneEdit: vi.fn() }));
vi.mock("../api/playRunContentApi", () => ({ getWorldPlayRunContent: vi.fn(), getWorldPlayRunContentCommand: vi.fn(), putWorldPlayRunContentCommand: vi.fn() }));
import { SESSION_COPY_AGENT_UNAVAILABLE } from "../playSurface/playRunEffectiveContent";
import { useMemo, useState } from "react";
import { webcrypto } from "node:crypto";
import { act, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { createWorkspaceDocument, getAgentRelatedPage, getWorldAgentTurnContextTrace, getWorkspaceDocumentSnapshot, getWorldAgentConversationHistory, getHistoricalRulesPassage, getWorldOwnedPlanCommittedRevision, getWorldPlanDocumentEditActions, listWorkspaceDocuments, listWorldContainers, LiveApiError, postWorldAgentNewConversation, postWorldPlanAgentTurn, postWorldPlayAgentTurn, postWorldBuildAgentTurn, postWorldGraphSourceAnchorRead, postWorldPlanDocumentEditProposal } from "../api/liveApi";
import type { AgentInteractionTurn, WorkspaceDocumentRecord, WorkspaceDocumentSnapshot, WorldAgentConversationHistoryResponseV1, WorldPlanAgentTurnRequestV1, WorldPlayAgentTurnRequestV1, WorldBuildAgentTurnRequestV1, WorldPlanAgentPlanContextV2, WorldPlanGraphAnswerContextStatusV1, WorldPlanGraphExecutionProjectionV1, WorldAgentConversationHistoryResponse, WorldBuildKnowledgeContextV1 } from "../api/types";
import { DocumentConversationDock, type PlanConversationPresentationHosts } from "../planSurface/components/PlanConversationDockAdapter";
import type { SavedWorldBuildConversationContext } from "./WorldAgentConversation";
import { AgentInteractionChrome } from "./AgentInteractionChrome";
import { AgentInteractionProvider } from "./AgentInteractionProvider";
import { useAgentInteraction } from "./useAgentInteraction";
import { AskPluginSlotProvider } from "./AskPluginSlot";
import { usePublishAgentSurfaceContext } from "./usePublishAgentSurfaceContext";
import { WorldAgentConversation, WorldAgentConversationProvider, WorldPlanConversationRegistration, usePublishWorldPlayConversation, usePublishWorldBuildConversation, useWorldAgentConversationState } from "./WorldAgentConversation";
import { BuildSurfacePage } from "../buildSurface/BuildSurfacePage";
import { SurfaceContextProvider } from "../surfaceInteraction/contextHost";
import { PeekRegionProvider } from "../surfaceInteraction/peekHost";
import { ToolHost } from "../surfaceInteraction/toolHost/ToolHost";
import { LegacyProjectionHostAdapter } from "../planSurface/projection/LegacyProjectionHostAdapter";
import type { CapturedWorldPlanEditTarget, WorldPlanEditBridge } from "../planSurface/agentEdit/planAgentEditProposal";

import {readDiscussionRetryInput} from '../api/conversationRetryApi';
vi.mock('../api/conversationRetryApi',async(original)=>({...await original<typeof import('../api/conversationRetryApi')>(),readDiscussionRetryInput:vi.fn()}));

const selectedWorld = vi.hoisted(() => ({ id: "world-one" }));
vi.mock("../selectedWorld/SelectedWorldContext", async (importOriginal) => ({
  ...(await importOriginal<typeof import("../selectedWorld/SelectedWorldContext")>()),
  useSelectedWorld: () => ({ kind: "managed", worldId: selectedWorld.id, name: "Test World", documentId: "plan-one" }),
}));
vi.mock("../api/liveApi", async (importOriginal) => ({
  ...(await importOriginal<typeof import("../api/liveApi")>()),
  getBuddyReadiness: vi.fn(async (surface: string, world_graph: boolean) => ({schema: "dmb_agent_readiness_v1", surface, world_graph, configured: true, issues: []})),
  createWorkspaceDocument: vi.fn(),
  getWorkspaceDocumentSnapshot: vi.fn(),
  listWorkspaceDocuments: vi.fn(),
  listWorldContainers: vi.fn(),
  getWorldAgentConversationHistory: vi.fn(),
  getHistoricalRulesPassage: vi.fn(),
  getAgentRelatedPage: vi.fn(),
  getWorldAgentTurnContextTrace: vi.fn(async (worldId: string, turnId: string) => ({
    schema: "dmb_agent_turn_context_trace_response_v1", world_id: worldId, turn_id: turnId, attempts: [],
  })),
  getWorldOwnedPlanCommittedRevision: vi.fn(),
  getWorldPlanDocumentEditActions: vi.fn(),
  postWorldAgentNewConversation: vi.fn(),
  postWorldPlanAgentTurn: vi.fn(),
  postWorldPlayAgentTurn: vi.fn(),
  postWorldBuildAgentTurn: vi.fn(),
  postWorldGraphSourceAnchorRead: vi.fn(),
  postWorldPlanDocumentEditProposal: vi.fn(),
}));

const WORLD = "world-one";
const RUN = "run-one";
const SHA = "a".repeat(64);
const WORK_REVISION = "00000000-0000-4000-8000-000000000011";
const BUILD_SOURCE_ID = "build-source-one";
const authoredRef=(node:string)=>({schema:'dmb_authored_graph_reference_v1' as const,managed_world_id:WORLD,native_world_id:'native',binding_version:1,graph_revision:'selected-revision',node_id:node,label:node});

function buildSourceSnapshot(): WorkspaceDocumentSnapshot {
  const record: WorkspaceDocumentRecord = {
    schema_version: "dmb_workspace_document_record_v1",
    document_id: BUILD_SOURCE_ID,
    title: "City of Mirathorn",
    campaign_id: WORLD,
    world_id: WORLD,
    target_session: null,
    kind: "worldbuilding_source",
    target_relpath: `out/workspace/worldbuilding/${BUILD_SOURCE_ID}.md`,
    status: "active",
    content_status: "committed",
    revision: 2,
    created_at: "2026-10-01T00:00:00Z",
    updated_at: "2026-10-02T00:00:00Z",
    source_domain: "worldbuilding",
    document_class: "lore",
    authority_state: "draft",
    visibility_state: "internal",
  };
  return {
    schema_version: "dmb_workspace_document_snapshot_v1",
    record,
    markdown: "# City of Mirathorn\n\nA city of old walls and new plans.\n",
    content_sha256: SHA,
    file_fingerprint: "source-file-fingerprint",
    file_exists: true,
    loaded_revision: 2,
  };
}

function history(turns: WorldAgentConversationHistoryResponseV1["turns"] = []): WorldAgentConversationHistoryResponseV1 {
  turns=turns.map(row=>{
    if(row.provenance.surface_id!=='build'||!['failed','interrupted'].includes(row.lifecycle_status)||row.assistant_text||row.retry_context)return row;
    const id=`22222222-2222-4222-8222-${String(row.sequence).padStart(12,'0')}`;
    return {...row,turn_id:id,provenance:{...row.provenance,primary_work:{...row.provenance.primary_work,kind:'build'}},
      retry_context:{world_id:WORLD,conversation_id:'11111111-1111-4111-8111-111111111111',turn_id:id,revision:4,root_id:id,
        predecessor_id:null,successor_id:null,ordinal:0,eligible:true,reason:'ready'}};
  });
  return { schema: "dmb_agent_conversation_history_v1", world_id: WORLD,
    conversation_state: "active", conversation_id: "11111111-1111-4111-8111-111111111111", active_conversation_id: "11111111-1111-4111-8111-111111111111",
    pointer_revision: 1, turns, next_before_sequence: null };
}
function turn(surface: "plan" | "play", sequence: number, answer: string) {
  return {
    turn_id: `turn-${sequence}`, sequence, lifecycle_status: "completed" as const,
    user_text: `${surface} question`, assistant_text: answer,
    provenance: {
      world_id: WORLD, surface_resolution: "resolved" as const, surface_id: surface,
      surface_instance_id: `${surface}-instance`,
      primary_work: { resolution: "resolved" as const, kind: surface === "plan" ? "plan" : "run",
        object_id: surface === "plan" ? "plan-one" : RUN, revision: "3", content_sha256: null,
        object_revision: 3, work_revision_id: null, revision_n: null },
      supporting_work: [], selected_object: { resolution: "absent" as const, kind: null, object_id: null,
        revision: null, content_sha256: null, object_revision: null, work_revision_id: null, revision_n: null },
    },
  };
}
function PlanPublisher({ documentId, editBridge = null }: { documentId: string; editBridge?: WorldPlanEditBridge | null }) {
  return <WorldPlanConversationRegistration worldId={WORLD} worldName="Test World" documentId={documentId}
    surfaceInstanceId="plan-instance" revision={7} editBridge={editBridge} draftGeneration={0} selectionGeneration={0}
    savedDirty={false} pageReady saveInFlight={false} />;
}
function PlayPublisher({ admitted, sessionCopy = false, editContent }: { admitted: boolean; sessionCopy?: boolean; editContent?: PlayRunContent }) {
  const context = useMemo(() => ({ surfaceId: "play" as const, label: "Play", campaignId: null,
    documentId: null, sessionNumber: null, ambientSummary: "World Run", sourceEnvelope: null }), []);
  const run = useMemo(() => admitted && !sessionCopy ? ({ worldId: WORLD, runId: editContent?.run_id ?? RUN,
    runRevision: 3, surfaceInstanceId: "play-instance",
    contentBasis: { edition_revision: 0, edition_revision_id: null, content_sha256: editContent?.content_sha256 ?? SHA },
    beatId: "beat:crossing", sceneId: "scene:west-gate", beatTitle: "The Crossing", sceneTitle: "West Gate" }) : null, [admitted, sessionCopy, editContent]);
  usePublishAgentSurfaceContext(context);
  usePublishWorldPlayConversation(run, sessionCopy ? SESSION_COPY_AGENT_UNAVAILABLE : null);
  return null;
}
function BuildPublisher({ admitted, bridge, sourceRevision = 2, sourceId='source-one' }: { admitted: boolean; bridge?: BuildComposeBridge | null; sourceRevision?: number;sourceId?:string }) {
  const surface = useMemo(() => ({ surfaceId: "build" as const, label: "Build", campaignId: null,
    documentId: sourceId, sessionNumber: null, ambientSummary: "Saved source", sourceEnvelope: null }), [sourceId]);
  const source = useMemo(() => admitted ? ({ worldId: WORLD, documentId: sourceId, revision: sourceRevision,
    contentSha256: SHA, surfaceInstanceId: "build-instance", title: "City of Mirathorn", dirty: true }) : null, [admitted, sourceRevision,sourceId]);
  usePublishAgentSurfaceContext(surface);
  return <DocumentConversationDock surface="build" contextLabel="City of Mirathorn" reader={<div>Build source projection</div>}>
    {hosts => <BuildHarnessBinding source={source} hosts={hosts} bridge={bridge} />}
  </DocumentConversationDock>;
}
function BuildHarnessBinding({source, hosts, bridge}: {source: SavedWorldBuildConversationContext | null; hosts: PlanConversationPresentationHosts; bridge?: BuildComposeBridge | null}) {
  usePublishWorldBuildConversation(source, hosts, bridge);
  return null;
}
function ProposalFixture() {
  const agent = useAgentInteraction();
  return <button type="button" onClick={() => {
    const thread = agent.ensureThread("Plan proposal");
    const proposal: AgentInteractionTurn = {
      turnId: "proposal-one", askedAt: "2026-10-10T07:00:00Z", completedAt: "2026-10-10T07:00:01Z",
      question: "Rewrite the crossing scene", answer: "Proposed a shorter crossing scene.",
      backend: "plan_edit", status: "ok", planEdit: {
        proposalSummary: "The crossing gets a clearer opening.", replacementMarkdown: "# Crossing\nA new opening.",
        applied: false, targetKind: "replace_playable_body",
      },
    };
    const key = `dmb:world-plan-local-proposal-order:v1:${encodeURIComponent(thread.campaignId)}:${encodeURIComponent(thread.threadId)}`;
    window.localStorage.setItem(key, JSON.stringify({ schema: "dmb_world_plan_local_proposal_order_v1",
      positions: [{ turnId: proposal.turnId, conversationId: "11111111-1111-4111-8111-111111111111", afterSequence: 1, ordinal: 1 }] }));
    agent.updateThread({ ...thread, worldPlanProposalHistory: "world_plan_proposals_v1", turns: [proposal] });
  }}>Seed Plan proposal</button>;
}
function NewerPendingFixture() {
  const state = useWorldAgentConversationState();
  return <><button type="button" onClick={() => state?.setPendingTurn({ surface: "plan", turnId: "newer-client-request" })}>Seed newer pending request</button>
    <button type="button" onClick={() => state?.setHistoryRefreshNonce(value => value + 1)}>Refresh shared history fixture</button></>;
}
function SceneEditorFixture({ content, allowed, onUnsubmitted }: { content: PlayRunContent; allowed: boolean; onUnsubmitted: (v: boolean) => void }) {
  const [accepted, setAccepted] = useState(content);
  return <SurfaceContextProvider><PlaySessionContentEditor content={accepted} currentSceneId="scene:gate" runRevision={3}
    canPropose={allowed} originLabel="From Plan" onAcceptedContent={setAccepted} onUnsubmittedChange={onUnsubmitted} /></SurfaceContextProvider>;
}
function OpenGuidance({repeatCorrelation}:{repeatCorrelation?:string}){const tour=useGuidedTour();return <><button onClick={()=>tour?.open()}>Open guidance</button>{repeatCorrelation?<button onClick={()=>tour?.recordConversationDispatch(repeatCorrelation,tour.captureScope())}>Repeat request registration</button>:null}</>;}
function TourBoundary({enabled,world,children,repeatCorrelation}:{enabled:boolean;world:string;children:ReactNode;repeatCorrelation?:string}){return enabled?<WorldGuidedTour worldId={world}><OpenGuidance repeatCorrelation={repeatCorrelation}/>{children}</WorldGuidedTour>:children;}
function Harness({ guided=false,repeatCorrelation,initial = "plan", admitted = true, editBridge = null, editContent, buildBridge, buildSourceRevision,buildSourceId }: {
  guided?:boolean;repeatCorrelation?:string;initial?: "plan" | "play" | "build"; admitted?: boolean; editBridge?: WorldPlanEditBridge | null; editContent?: PlayRunContent; buildBridge?: BuildComposeBridge | null; buildSourceRevision?: number;buildSourceId?:string;
}) {
  const [surface, setSurface] = useState(initial);
  const [sessionCopy, setSessionCopy] = useState(false);
  const [world, setWorld] = useState(WORLD);
  const [documentId, setDocumentId] = useState("plan-one");
  return <AgentInteractionProvider><AskPluginSlotProvider>
    <WorldAgentConversationProvider key={world} worldId={world}><TourBoundary enabled={guided} world={world} repeatCorrelation={repeatCorrelation}>
      <button type="button" onClick={() => setSurface(surface === "plan" ? "play" : "plan")}>Switch surface</button>
      <button type="button" onClick={() => setDocumentId(value => value === "plan-one" ? "plan-two" : "plan-one")}>Switch Plan document</button>
      <button type="button" onClick={() => { selectedWorld.id = "world-two"; setWorld("world-two"); }}>Switch World</button>
      <button type="button" onClick={() => setSessionCopy(value => !value)}>Use session copy</button>
      <ProposalFixture /><NewerPendingFixture />
      {surface === "plan" ? <PlanPublisher documentId={documentId} editBridge={editBridge} /> : surface === "build" ? <BuildPublisher admitted={admitted && world === WORLD} bridge={buildBridge} sourceRevision={buildSourceRevision} sourceId={buildSourceId} /> : <PlayPublisher admitted={admitted && world === WORLD} sessionCopy={sessionCopy} editContent={editContent} />}
      {editContent ? <SceneEditorFixture content={editContent} allowed={!sessionCopy} onUnsubmitted={setSessionCopy} /> : null}
      <AgentInteractionChrome />
      <WorldAgentConversation surface={surface} worldId={world} worldName="Test World" />
    </TourBoundary></WorldAgentConversationProvider>
  </AskPluginSlotProvider></AgentInteractionProvider>;
}

function RealBuildPageHarness() {
  return <AgentInteractionProvider><AskPluginSlotProvider>
    <WorldAgentConversationProvider worldId={WORLD}>
      <SurfaceContextProvider><PeekRegionProvider>
        <BuildSurfacePage />
        <ToolHost />
        <LegacyProjectionHostAdapter />
      </PeekRegionProvider></SurfaceContextProvider>
      <AgentInteractionChrome />
      <WorldAgentConversation surface="build" worldId={WORLD} worldName="Test World" />
    </WorldAgentConversationProvider>
  </AskPluginSlotProvider></AgentInteractionProvider>;
}

function playResponse(request: WorldPlayAgentTurnRequestV1) {
  const context = nativePlayContextFixture(request);
  return {
    schema: "dmb_agent_play_graph_turn_response_v1" as const, play_context: context, client_thread_id: request.client_thread_id, turn_id: request.turn_id,
    surface: { surface_id: "play", instance_id: "play-instance", status: "resolved" as const },
    owner_scope: { status: "resolved" as const, kind: "world" as const, owner_id: WORLD, name: "Test World" },
    primary_work: { status: "resolved" as const, kind: "run", object_id: RUN, revision_used: 3,
      expected_revision: 3, content_basis: null },
    client_work_state_reported: "saved_clean" as const,
    graph: request.graph_request.mode === "none"
      ? { status: "not_requested" as const, world_id: null, campaign_id: null, scope_mode: null,
        revision_id: null, focus: null, selection_node_id: null, selection_found: null, head_revision_id: null, is_head: null }
      : { status: "ready" as const, world_id: "native-world-one", campaign_id: "", scope_mode: "world" as const,
        revision_id: context.receipt.graph_authority.graph_revision, focus: { kind: "none" }, selection_node_id: null,
        selection_found: null, head_revision_id: context.receipt.graph_authority.graph_revision, is_head: true },
    conversation: { client_thread_id: request.client_thread_id, turn_id: request.turn_id,
      pointer_status: "accepted" as const, pointer_id: "pointer", conversation_id: "11111111-1111-4111-8111-111111111111" },
    answer: { status: "ok" as const, text: "Original Play answer", code: null, message: null,
      graph_grounded: false, trace: {} },
  };
}

function planResponse(request: WorldPlanAgentTurnRequestV1) {
  return {
    schema: "dmb_agent_turn_response_v1" as const, client_thread_id: request.client_thread_id, turn_id: request.turn_id,
    surface: { surface_id: "plan", instance_id: request.surface.instance_id, status: "resolved" as const },
    owner_scope: { status: "resolved" as const, kind: "world" as const, owner_id: WORLD, name: "Test World" },
    primary_work: { status: "resolved" as const, kind: "plan", object_id: "plan-one", revision_used: 7,
      expected_revision: 7, content_basis: { world_id: WORLD, document_id: "plan-one", object_revision: 7,
        work_revision_id: WORK_REVISION, revision_n: 2, content_sha256: SHA,
        committed_status: "committed" as const, has_divergent_working_copy: false } },
    client_work_state_reported: "saved_clean" as const,
    graph: { status: "not_requested" as const, world_id: null, campaign_id: null, scope_mode: null,
      revision_id: null, focus: null, selection_node_id: null, selection_found: null, head_revision_id: null, is_head: null },
    conversation: { client_thread_id: request.client_thread_id, turn_id: request.turn_id,
      pointer_status: "accepted" as const, pointer_id: "pointer", conversation_id: "11111111-1111-4111-8111-111111111111" },
    answer: { status: "ok" as const, text: "Late Plan answer", code: null, message: null,
      graph_grounded: false, trace: {} },
  };
}

function canonicalJson(value: unknown): string {
  if (Array.isArray(value)) return `[${value.map(canonicalJson).join(",")}]`;
  if (value !== null && typeof value === "object") {
    const record = value as Record<string, unknown>;
    return `{${Object.keys(record).sort().map((key) => `${JSON.stringify(key)}:${canonicalJson(record[key])}`).join(",")}}`;
  }
  const encoded = JSON.stringify(value);
  if (encoded === undefined) throw new Error("Unsupported value in canonical JSON payload.");
  return encoded;
}

async function sha256Hex(value: string): Promise<string> {
  const digest = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(value));
  return Array.from(new Uint8Array(digest), (byte) => byte.toString(16).padStart(2, "0")).join("");
}

async function expectedHistoryCorrelationKey(frozenWorldId: string, clientTurnId: string): Promise<string> {
  const namespace = Uint8Array.from("6ba7b8119dad11d180b400c04fd430c8".match(/.{2}/g)!, (pair) => Number.parseInt(pair, 16));
  const name = new TextEncoder().encode(`dmb-agent-turn:${frozenWorldId}:${clientTurnId}`);
  const input = new Uint8Array(namespace.length + name.length);
  input.set(namespace);
  input.set(name, namespace.length);
  const hash = new Uint8Array(await crypto.subtle.digest("SHA-1", input));
  hash[6] = (hash[6]! & 0x0f) | 0x50;
  hash[8] = (hash[8]! & 0x3f) | 0x80;
  const hex = Array.from(hash.slice(0, 16), (byte) => byte.toString(16).padStart(2, "0")).join("");
  return `${hex.slice(0, 8)}-${hex.slice(8, 12)}-${hex.slice(12, 16)}-${hex.slice(16, 20)}-${hex.slice(20)}`;
}

async function planGraphContext(
  status: WorldPlanGraphAnswerContextStatusV1,
  options: {
    request?: WorldPlanAgentTurnRequestV1;
    execution?: WorldPlanGraphExecutionProjectionV1 | null;
    completion?: boolean;
  } = {},
): Promise<WorldPlanAgentPlanContextV2> {
  const graphClaimed = status === "graph_grounded" || status === "graph_grounded_partial";
  const sufficient = status !== "plan_only_insufficient_evidence";
  const graphRevision = "graph-revision-test";
  const assertionIds = sufficient ? ["assertion-internal-test"] : [];
  const evidenceIds = sufficient ? ["evidence-internal-test"] : [];
  const receiptPayload = {
    schema: "dmb_agent_plan_world_graph_context_receipt_v1" as const,
    receipt_serializer_version: "canonical-json-utf8-v1" as const,
    context_receipt_sha256: "0".repeat(64),
    plan_context_policy: options.request?.plan_context_policy ?? { schema: "dmb_plan_context_policy_v1" as const, policy: "auto_plan_world" as const },
    plan_basis: {
      world_id: WORLD,
      document_id: "plan-one",
      object_revision: options.request?.primary_work.expected_revision ?? 7,
      work_revision_id: WORK_REVISION,
      revision_n: options.request?.primary_work.expected_revision_n ?? 1,
      content_sha256: options.request?.primary_work.expected_content_sha256 ?? SHA,
    },
    playable_target: options.request?.playable_target ? {
      schema: "dmb_plan_playable_target_receipt_v1" as const,
      kind: options.request.playable_target.kind,
      id: options.request.playable_target.id,
      marker_grammar_version: "v1" as const,
    } : null,
    graph_authority: {
      managed_world_id: WORLD,
      native_world_id: "native-world-internal-test",
      binding_version: 3,
      scope_mode: "world" as const,
      campaign_id: null,
      admissibility_version: "admissibility-test-v1",
      graph_revision: graphRevision,
    },
    graph_packet: {
      schema: "dmb_plan_world_graph_packet_v1" as const,
      packet_serializer_version: "canonical-json-utf8-v1" as const,
      selection_policy_version: "selection-test-v1",
      evidence_sufficiency_policy_version: "evidence-test-v1",
      retrieval_packet_sha256: "b".repeat(64),
      candidate_assertion_ids: assertionIds,
      candidate_relationship_ids: [],
      candidate_evidence_ref_ids: evidenceIds,
      retrieval_status: sufficient ? "complete" as const : "empty" as const,
      evidence_sufficiency_status: sufficient ? "sufficient" as const : "insufficient" as const,
      result_limit: 10,
      coverage_status: status === "graph_grounded_partial" ? "incomplete" as const : "complete" as const,
      truncated: status === "graph_grounded_partial",
      omission_reasons: sufficient ? [] : ["no_claim_ready_evidence"],
    },
    assembled_input: {
      assembler_version: "assembler-test-v1",
      budget_policy_version: "budget-test-v1",
      provider_model_name: "test-model",
      provider_model_version: "test-model-v1",
      tokenizer_name: "test-tokenizer",
      tokenizer_version: "test-tokenizer-v1",
      provider_envelope_input_tokens: 400,
      output_token_reserve: 100,
      context_window_limit: 1000,
      packet_disposition: sufficient ? "included" as const : "omitted_insufficient" as const,
      packet_disposition_reason: sufficient ? null : "insufficient_evidence" as const,
      dispatched_packet_sha256: sufficient ? "c".repeat(64) : null,
      dispatched_assertion_ids: assertionIds,
      dispatched_relationship_ids: [],
      dispatched_evidence_ref_ids: evidenceIds,
      source_token_accounting: [{ source_kind: "plan" as const, source_id: "plan-one", input_tokens: 200 }],
      included_history: [],
      assembled_input_sha256: "d".repeat(64),
    },
    evidence_mode: "metadata_only" as const,
    source_opened: false as const,
  };
  const { context_receipt_sha256: _ignored, ...receiptForHash } = receiptPayload;
  const receiptDigest = await sha256Hex(canonicalJson(receiptForHash));
  const receipt = { ...receiptPayload, context_receipt_sha256: receiptDigest };
  const segments = graphClaimed
    ? [{
      kind: "graph_claim" as const,
      claim_id: "claim-internal-test",
      text: "The western gate is watched.",
      target_kind: "assertion" as const,
      target_id: assertionIds[0]!,
      graph_revision: graphRevision,
      evidence_ref_ids: evidenceIds,
    }]
    : [{ kind: "connective" as const, text: "The saved Plan has one opening scene." }];
  const citationEntries = graphClaimed ? [{
    claim_id: "claim-internal-test",
    target_kind: "assertion" as const,
    target_id: assertionIds[0]!,
    graph_revision: graphRevision,
    evidence_ref_ids: evidenceIds,
    source_opened: false as const,
  }] : [];
  return {
    schema: "dmb_agent_plan_world_graph_context_response_v2",
    receipt,
    completion: options.completion === false ? null : {
      schema: "dmb_plan_world_graph_completion_v1",
      context_receipt_sha256: receiptDigest,
      answer_basis: graphClaimed ? "committed_plan_plus_world_graph" : "committed_plan",
      answer_context_status: status,
      answer_segments: segments,
      citation_map: graphClaimed ? {
        schema: "dmb_graph_citation_map_v1",
        context_receipt_sha256: receiptDigest,
        entries: citationEntries,
      } : null,
    },
    execution: options.execution === undefined ? {
      schema: "dmb_agent_plan_world_graph_execution_projection_v1",
      claimability: "completed",
      authorization_state: "response_received",
      automatic_redispatch: false,
    } : options.execution,
    delivery_replay: false,
  };
}


async function buildGraphContext(): Promise<WorldBuildKnowledgeContextV1> {
  const plan = await planGraphContext("graph_grounded");
  const { plan_basis: _plan, plan_context_policy: _policy, playable_target: _target, ...common } = plan.receipt;
  const receipt = { ...common, schema: "dmb_build_graph_context_receipt_v1" as const,
    graph_authority: {...common.graph_authority, admissibility_version: "gm-v1"},
    source_basis: { world_id: WORLD, document_id: "source-one", registry_revision: 2,
      content_sha256: SHA, visibility: "internal" as const } };
  const { context_receipt_sha256: _digest, ...hashable } = receipt;
  receipt.context_receipt_sha256 = await sha256Hex(canonicalJson(hashable));
  const claim = plan.completion!.answer_segments[0]!;
  if (claim.kind !== "graph_claim") throw new Error("Expected Graph fixture");
  return { schema: "dmb_build_graph_context_response_v1", saved_source_name: null, receipt, delivery_replay: false,
    execution: plan.execution, completion: { schema: "dmb_build_graph_completion_v1",
      context_receipt_sha256: receipt.context_receipt_sha256, answer_basis: "saved_source_plus_world_graph",
      answer_context_status: "graph_grounded", answer_segments: [claim], citation_map: {
        schema: "dmb_graph_citation_map_v2", context_receipt_sha256: receipt.context_receipt_sha256,
        entries: plan.completion!.citation_map!.entries.map(entry => ({ ...entry, source_read_ids: [] })),
      } },
    source_open_targets: [{ schema: "dmb_agent_evidence_anchor_open_target_v1", kind: "evidence_anchor",
      claim_id: claim.claim_id, source_artifact_id: "artifact-one", source_revision_id: "source-rev-one", source_name: null,
      managed_world_id: WORLD, native_world_id: receipt.graph_authority.native_world_id,
      binding_version: receipt.graph_authority.binding_version, scope_mode: "world", campaign_id: null,
      focus: {kind: "none", session_id: null, campaign_id: null}, admissibility: "gm",
      graph_revision: receipt.graph_authority.graph_revision, anchor_id: "anchor-one",
      evidence_ref_id: "evidence-internal-test", source_read_id: null, read_outcome: null }],
    evidence_anchor_statuses: [{schema: "dmb_agent_evidence_anchor_status_v1", claim_id: claim.claim_id,
      status: "available", target_count: 1}], related_recap_context_statuses: [],
  };
}


function insertionCapture(): CapturedBuildInsertion {
  return {editor:{} as CapturedBuildInsertion['editor'], editorJson:'{}', draftMarkdown:'# Unsaved page',
    basis:{world_id:WORLD,document_id:'source-one',registry_revision:2,content_sha256:SHA,
      visibility:'internal',draft_sha256:SHA,editor_sha256:SHA,caret:1,draft_generation:0,selection_generation:0}};
}
function draftSnapshot(){
 const captured=insertionCapture(),b=captured.basis;
 return {schema:'dmb_build_draft_snapshot_v1' as const,world_id:b.world_id,document_id:b.document_id,
  registry_revision:b.registry_revision,content_sha256:b.content_sha256,visibility:b.visibility,
  draft_markdown:captured.draftMarkdown,draft_sha256:b.draft_sha256,editor_sha256:b.editor_sha256!,draft_generation:b.draft_generation};
}
function retryBridge():BuildComposeBridge {
 return {captureContext:vi.fn(async()=>draftSnapshot()),capture:vi.fn(async()=>insertionCapture()),insert:vi.fn()};
}
function openConversationOptions() {
  const summary=screen.getByTitle("Conversation options");
  const menu=summary.closest("details")!;
  if (!menu.open) fireEvent.click(summary);
  return menu;
}

describe("one App-level World conversation host across Plan and Play", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    Object.defineProperty(globalThis, "crypto", { configurable: true, value: webcrypto });
    selectedWorld.id = WORLD;
    window.localStorage.clear();
    window.sessionStorage.clear();
    vi.mocked(getWorldAgentConversationHistory).mockResolvedValue(history([turn("plan", 1, "Original Plan answer")]));
    vi.mocked(listWorkspaceDocuments).mockResolvedValue({ schema_version: "dmb_workspace_document_registry_v1", records: [] });
    vi.mocked(listWorldContainers).mockResolvedValue({ schema_version: "dmb_world_container_registry_v1", records: [] });
    vi.mocked(getWorldOwnedPlanCommittedRevision).mockResolvedValue({
      schema_version: "dmb_workspace_committed_revision_v2", scope_mode: "world", world_id: WORLD,
      campaign_id: null, document_id: "plan-one", kind: "plan", status: "active", object_revision: 7,
      revision_n: 2, work_revision_id: WORK_REVISION, markdown: "# Plan", content_sha256: SHA,
      has_divergent_working_copy: false,
    } as Awaited<ReturnType<typeof getWorldOwnedPlanCommittedRevision>>);
    vi.mocked(getWorldPlanDocumentEditActions).mockResolvedValue({ schema_version: "dmb_world_plan_action_projection_v1",
      basis: { world_id: WORLD, document_id: "plan-one", object_revision: 7 }, actions: [] } as Awaited<ReturnType<typeof getWorldPlanDocumentEditActions>>);
  });



  it.each(['plan', 'play', 'build'] as const)('teaches memory at the actual %s composer without sending or crediting a turn', async initial => {
    const rect = vi.spyOn(HTMLElement.prototype, 'getBoundingClientRect').mockReturnValue(new DOMRect(100, 100, 200, 40));
    const rects = vi.spyOn(HTMLElement.prototype, 'getClientRects').mockReturnValue([new DOMRect(100, 100, 200, 40)] as unknown as DOMRectList);
    const priorScroll = Object.getOwnPropertyDescriptor(HTMLElement.prototype, 'scrollIntoView');
    Object.defineProperty(HTMLElement.prototype, 'scrollIntoView', {configurable: true, value: vi.fn()});
    const record = reduceTour(createWalkthrough(WORLD, 'conks', 'memory-anchor', '2026-01-01T00:00:00Z'), {kind: 'move', index: 14});
    writeWalkthrough(localStorage, record, null);
    const memoryTargets = () => document.querySelectorAll('[data-guided-control~="memory"]');
    const mounted = render(<Harness initial={initial} guided/>);
    try {
      const launcher = await screen.findByRole('button', {name: 'Open', exact: true});
      expect(memoryTargets()).toHaveLength(1);
      expect(memoryTargets()[0]).toBe(launcher);
      fireEvent.click(launcher);
      const composer = await screen.findByLabelText('Message DungeonBuddy');
      await waitFor(() => expect(composer).toBeEnabled());
      expect(memoryTargets()).toHaveLength(1);
      expect(memoryTargets()[0]).toBe(composer);
      fireEvent.change(composer, {target: {value: 'Unsent continuity question'}});
      fireEvent.click(screen.getByRole('button', {name: 'Open guidance'}));
      await screen.findByRole('heading', {name: 'Ask about the session'});
      fireEvent.click(screen.getByRole('button', {name: 'Show control'}));
      await screen.findByRole('dialog', {name: /Ask about the session/});
      expect(composer).toHaveAttribute('data-guided-highlight', 'true');
      expect(composer).toHaveFocus();
      fireEvent.click(screen.getByRole('button', {name: initial === 'plan' ? 'Close chat' : 'Close conversation'}));
      await waitFor(() => expect(memoryTargets()).toHaveLength(1));
      expect(memoryTargets()[0]).toBe(screen.getByRole('button', {name: 'Open', exact: true}));
      await screen.findByRole('complementary', {name: 'Guided journey'});
      fireEvent.click(screen.getByRole('button', {name: 'Open', exact: true}));
      const reopened = await screen.findByLabelText('Message DungeonBuddy');
      expect(reopened).toHaveValue('Unsent continuity question');
      expect(memoryTargets()).toHaveLength(1);
      expect(memoryTargets()[0]).toBe(reopened);
      fireEvent.click(screen.getByRole('button', {name: 'Show control'}));
      await screen.findByRole('dialog', {name: /Ask about the session/});
      expect(reopened).toHaveFocus();
      expect(postWorldPlanAgentTurn).not.toHaveBeenCalled();
      expect(postWorldPlayAgentTurn).not.toHaveBeenCalled();
      expect(readWalkthrough(localStorage, WORLD)?.record.steps.memory.state).toBe('pending');
      expect(readWalkthrough(localStorage, WORLD)?.record.steps.memory.evidence).toHaveLength(0);
    } finally {
      mounted.unmount(); rect.mockRestore(); rects.mockRestore();
      if (priorScroll) Object.defineProperty(HTMLElement.prototype, 'scrollIntoView', priorScroll);
      else delete (HTMLElement.prototype as Partial<HTMLElement>).scrollIntoView;
    }
  });

  it.each(['fresh','restart','retry-after-restart','restart-preparation','plan-preparation','wrong-key','wrong-review','missing-correlation'] as const)('correlates actual Plan memory dispatch with independent server identity: %s',async mode=>{
    Object.defineProperty(navigator,'locks',{configurable:true,value:{request:vi.fn(async(_key:string,callback:()=>unknown)=>callback())}});
    const runId='22222222-2222-4222-8222-222222222222',physicalId='33333333-3333-4333-8333-333333333333';
    const plan:TargetPin={kind:'plan',worldId:WORLD,objectId:'plan-one',revision:2,revisionId:WORK_REVISION,digest:SHA};
    const run:TargetPin={kind:'run',worldId:WORLD,objectId:runId,revision:7,digest:SHA};
    function seed(id:string){let w=createWalkthrough(WORLD,'conks',id,'2026-01-01T00:00:00Z');w=reduceTour(w,{kind:'bind',pin:plan});w=reduceTour(w,{kind:'bind',pin:run,parent:plan});w=reduceTour(w,{kind:'observe',observation:{step:'reflection',target:run,parent:plan,origin:'existing',observedAt:'2026-01-01T00:00:00Z',receiptId:'review',proof:{kind:'session-review',reviewRevision:4,checkpointRunRevision:7,contentRevision:0,contentRevisionId:null,contentDigest:'f'.repeat(64),commandId:null}}});return reduceTour(w,{kind:'move',index:13});}
    writeWalkthrough(localStorage,seed('walk-A'),null);
    let current:WorldAgentConversationHistoryResponse=history();
    let release!:()=>void;const pending=new Promise<void>(resolve=>{release=resolve;});
    vi.mocked(getWorldAgentConversationHistory).mockImplementation(async()=>current);
    let releasePreparation!:()=>void;const preparation=new Promise<void>(resolve=>{releasePreparation=resolve;});
    if(mode==='restart-preparation'||mode==='plan-preparation')vi.mocked(getWorldOwnedPlanCommittedRevision).mockImplementation(async()=>{await preparation;return {schema_version:'dmb_workspace_committed_revision_v2',scope_mode:'world',world_id:WORLD,campaign_id:null,document_id:'plan-one',kind:'plan',status:'active',object_revision:7,revision_n:2,work_revision_id:WORK_REVISION,markdown:'# Plan',content_sha256:SHA,has_divergent_working_copy:false};});
    vi.mocked(postWorldPlanAgentTurn).mockImplementation(async request=>{
      expect(request.turn_id).not.toBe(physicalId);await pending;
      const context=await planGraphContext('plan_only_graph_unused',{request});const text='Saved rehearsal: communication was chosen; the child’s future remains unresolved.';
      const supportText='Rehearsal only; communication was chosen and the child outcome remains open.',body=await sha256Hex(supportText);
      context.completion={schema:'dmb_surface_evidence_completion_v4',surface_id:'plan',context_receipt_sha256:context.receipt.context_receipt_sha256,answer_basis:'mixed_evidence',answer_context_status:'authored_grounded',citation_map:null,source_citations:[],native_source_citations:[],answer_segments:[{kind:'session_summary',text,supports:[0,1].map(i=>({kind:'authored_excerpt' as const,text:supportText,source_kind:'session' as const,source_name:'Synthetic rehearsal notes',object_id:runId,revision:mode==='wrong-review'?'3':'4',body_sha256:body,owner_sha256:'c'.repeat(64),source_handle:'q'+'a'.repeat(64),block_handle:'b'+String(i+3).repeat(64),partition_version:'markdown_source_blocks_v1' as const,byte_start:0,byte_end:new TextEncoder().encode(supportText).length,block_sha256:body,entry_identity:String(i+1).repeat(64),source_ordinal:i,entry_kind:i?'closing_reflections' as const:'scene_note' as const,element_id:i?null:'scene:gate',checkpoint_content_sha256:'f'.repeat(64)}))}]};
      const basis=context.receipt.plan_basis,prior=turn('plan',1,text);
      const row={...prior,turn_id:physicalId,user_text:request.message,...(mode==='missing-correlation'?{}:{idempotency_key:mode==='wrong-key'?'44444444-4444-5444-8444-444444444444':await expectedHistoryCorrelationKey(WORLD,request.turn_id)}),plan_context:context,provenance:{...prior.provenance,primary_work:{...prior.provenance.primary_work,revision:String(basis.object_revision),object_revision:basis.object_revision,revision_n:basis.revision_n,work_revision_id:basis.work_revision_id,content_sha256:basis.content_sha256}}};
      current={...history(),schema:mode==='missing-correlation'?'dmb_agent_conversation_history_v2':'dmb_agent_conversation_history_v3',turns:[row]} as WorldAgentConversationHistoryResponse;
      const response=planResponse(request);return {...response,schema:'dmb_agent_turn_response_v2' as const,plan_context:context,answer:{...response.answer,text}};
    });
    const mounted=render(<Harness initial='plan' guided/>);fireEvent.click(await screen.findByRole('button',{name:'Open',exact:true}));
    const composer=await screen.findByLabelText('Message DungeonBuddy');await waitFor(()=>expect(composer).toBeEnabled());fireEvent.change(composer,{target:{value:'Recall the saved notes and reflections.'}});fireEvent.click(screen.getByRole('button',{name:'Send message'}));
    if(mode==='restart-preparation'||mode==='plan-preparation'){
      await waitFor(()=>expect(getWorldOwnedPlanCommittedRevision).toHaveBeenCalled());
      if(mode==='plan-preparation'){fireEvent.click(screen.getByRole('button',{name:'Switch Plan document'}));await act(async()=>releasePreparation());expect(postWorldPlanAgentTurn).not.toHaveBeenCalled();expect(readWalkthrough(localStorage,WORLD)?.record.steps.memory.evidence).toHaveLength(0);return;}
      await act(async()=>{writeWalkthrough(localStorage,seed('walk-B'),readWalkthrough(localStorage,WORLD)!);window.dispatchEvent(new StorageEvent('storage',{key:pointerKey(WORLD)}));});
      await act(async()=>releasePreparation());
    }
    await waitFor(()=>expect(postWorldPlanAgentTurn).toHaveBeenCalledTimes(1));
    if(mode==='restart'||mode==='retry-after-restart'){await act(async()=>{const prior=readWalkthrough(localStorage,WORLD)!;writeWalkthrough(localStorage,seed('walk-B'),prior);window.dispatchEvent(new StorageEvent('storage',{key:pointerKey(WORLD)}));});}
    if(mode==='retry-after-restart'){
      const request=vi.mocked(postWorldPlanAgentTurn).mock.calls[0]![0],correlation=await expectedHistoryCorrelationKey(WORLD,request.turn_id);
      mounted.rerender(<Harness initial='plan' guided repeatCorrelation={correlation}/>);fireEvent.click(screen.getByRole('button',{name:'Repeat request registration'}));
    }
    await act(async()=>release());await screen.findByText('Saved rehearsal: communication was chosen; the child’s future remains unresolved.');
    if(mode==='fresh')await waitFor(()=>expect(readWalkthrough(localStorage,WORLD)?.record.steps.memory.state).toBe('completed'));
    else if(mode==='wrong-review')expect(readWalkthrough(localStorage,WORLD)?.record.steps.memory.evidence).toHaveLength(0);
    else await waitFor(()=>expect(readWalkthrough(localStorage,WORLD)?.record.steps.memory.state).toBe('existing'));
    const evidence=readWalkthrough(localStorage,WORLD)?.record.steps.memory.evidence??[];
    if(evidence.length)expect(evidence[0]?.proof).toMatchObject({kind:'session-memory',turnId:physicalId});
    expect(postWorldPlanAgentTurn).toHaveBeenCalledTimes(1);
  });

  it('opens named archives from the agent menu without changing the current composer',async()=>{
    Object.defineProperty(HTMLDialogElement.prototype,'showModal',{configurable:true,value(this:HTMLDialogElement){this.setAttribute('open','');}});
    render(<Harness initial="build"/>);fireEvent.click(await screen.findByRole('button',{name:'Open',exact:true}));
    const input=await screen.findByLabelText('Message DungeonBuddy');await waitFor(()=>expect(input).toBeEnabled());
    fireEvent.change(input,{target:{value:'Keep current work'}});openConversationOptions();
    expect(screen.getByRole('button',{name:'Export conversation',exact:true})).toBeInTheDocument();
    expect(screen.getByRole('button',{name:'Export with diagnostics'})).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button',{name:'Conversations…'}));await screen.findByText('Archived library question');
    expect(input).toHaveValue('Keep current work');expect(postWorldAgentNewConversation).not.toHaveBeenCalled();expect(postWorldBuildAgentTurn).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole('button',{name:'Close conversations'}));expect(input).toHaveValue('Keep current work');
  });
  it('retires an authoring gesture on document departure while history is still loading',async()=>{
    let finish!:(value:ReturnType<typeof history>)=>void;
    vi.mocked(getWorldAgentConversationHistory).mockImplementation(()=>new Promise(resolve=>{finish=resolve;}));
    const view=render(<Harness initial="build"/>);fireEvent.click(await screen.findByRole('button',{name:'Open',exact:true}));
    await waitFor(()=>expect(getWorldAgentConversationHistory).toHaveBeenCalled());
    const prepare=vi.fn(async()=>{});
    act(()=>queueSurfaceConversationRequest({id:'connected-departure',worldId:WORLD,surfaceId:'build',objectId:'source-one',message:'Build out',clientThreadId:'thread',turnId:'turn',isCurrent:()=>true,prepare}));
    view.rerender(<Harness initial="build" buildSourceId="source-two"/>);
    view.rerender(<Harness initial="build" buildSourceId="source-one"/>);
    await act(async()=>{finish(history());});
    expect(claimSurfaceConversationRequest('connected-departure')).toBeNull();expect(prepare).not.toHaveBeenCalled();expect(postWorldBuildAgentTurn).not.toHaveBeenCalled();
  });
  it('hands one explicit authoring gesture to durable Build submission without replacing composer text',async()=>{
    const bridge:BuildComposeBridge={captureContext:vi.fn(async()=>draftSnapshot()),capture:vi.fn(async()=>insertionCapture()),insert:vi.fn()};
    vi.mocked(postWorldBuildAgentTurn).mockImplementation(()=>new Promise(()=>{}));
    render(<Harness initial="build" buildBridge={bridge}/>);
    fireEvent.click(await screen.findByRole('button',{name:'Open',exact:true}));
    const input=await screen.findByLabelText('Message DungeonBuddy');await waitFor(()=>expect(input).toBeEnabled());
    fireEvent.change(input,{target:{value:'Keep my own next question'}});
    const prepare=vi.fn(async()=>{});
    act(()=>queueSurfaceConversationRequest({id:'connected-integration',worldId:WORLD,surfaceId:'build',objectId:'source-one',
      message:'Build out the selected starter sections.',clientThreadId:'11111111-1111-4111-8111-111111111111',
      turnId:'22222222-2222-4222-8222-222222222222',isCurrent:()=>true,prepare}));
    await waitFor(()=>expect(postWorldBuildAgentTurn).toHaveBeenCalledTimes(1));
    const request=vi.mocked(postWorldBuildAgentTurn).mock.calls[0][0];
    expect(request.turn_id).toBe('22222222-2222-4222-8222-222222222222');
    expect(request.message).toBe('Build out the selected starter sections.');
    expect(request.build_write_capability).toBeDefined();expect(prepare).toHaveBeenCalledTimes(1);
    expect(input).toHaveValue('Keep my own next question');
    const stored=JSON.parse(localStorage.getItem(`dmb:world-play-pending-turn:v1:${encodeURIComponent(WORLD)}`)!);
    expect(stored.request).toEqual(request);cancelSurfaceConversationRequest('connected-integration');
  });
  it('offers an explicit retry when an authoring gesture cannot prepare, without a request loop',async()=>{
    const bridge:BuildComposeBridge={captureContext:vi.fn(async()=>draftSnapshot()),capture:vi.fn(async()=>insertionCapture()),insert:vi.fn()};
    render(<Harness initial="build" buildBridge={bridge}/>);fireEvent.click(await screen.findByRole('button',{name:'Open',exact:true}));
    await waitFor(()=>expect(screen.getByLabelText('Message DungeonBuddy')).toBeEnabled());
    const prepare=vi.fn(async()=>{throw new Error('The created page changed.');});
    act(()=>queueSurfaceConversationRequest({id:'connected-failure',worldId:WORLD,surfaceId:'build',objectId:'source-one',message:'Build out',
      clientThreadId:'thread',turnId:'turn',isCurrent:()=>true,prepare}));
    await screen.findByRole('button',{name:'↻ Try build out'});expect(prepare).toHaveBeenCalledTimes(1);expect(postWorldBuildAgentTurn).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole('button',{name:'Dismiss'}));cancelSurfaceConversationRequest('connected-failure');
  });

  it.each(['rejected','undefined'] as const)('preserves a Build placement request before dispatch when capture is %s',async mode=>{
    const capture=vi.fn(async()=>{throw new Error('Place the caret where the new text should go.');});
    const bridge:BuildComposeBridge={captureContext:vi.fn(async()=>draftSnapshot()),capture,insert:vi.fn()};
    if(mode==='undefined')vi.mocked(getWorldAgentConversationHistory).mockResolvedValue({...history(),conversation_state:"absent",conversation_id:null,active_conversation_id:null,pointer_revision:0});
    render(<Harness initial="build" buildBridge={bridge}/>);
    fireEvent.click(await screen.findByRole('button',{name:'Open',exact:true}));
    const input=await screen.findByLabelText('Message DungeonBuddy');
    await waitFor(()=>expect(input).toBeEnabled());
    const message='Draft a section about Culture — keep the author’s wording.';
    fireEvent.change(input,{target:{value:message}});
    fireEvent.click(screen.getByRole('button',{name:'Send message',exact:true}));
    const placementFailure=await screen.findByRole('region',{name:'Page proposal unavailable'});
    expect(placementFailure).toHaveTextContent('Discussion includes your current draft. It won’t place writing on the page.');
    expect(placementFailure).not.toHaveTextContent('unsaved edits will not be included');
    expect(input).toHaveValue(message);
    expect(postWorldBuildAgentTurn).not.toHaveBeenCalled();
    expect(Object.keys(localStorage).filter(k=>k.startsWith('dmb:world-play-pending-turn:'))).toEqual([]);
    expect(bridge.insert).not.toHaveBeenCalled();
    vi.mocked(postWorldBuildAgentTurn).mockImplementation(()=>new Promise(()=>{}));
    if(mode==='undefined'){
      const active=history();
      vi.mocked(postWorldAgentNewConversation).mockResolvedValue({schema:'dmb_agent_new_conversation_response_v1',world_id:WORLD,
        conversation_id:active.conversation_id!,active_conversation_id:active.conversation_id!,pointer_revision:active.pointer_revision});
      vi.mocked(getWorldAgentConversationHistory).mockResolvedValue(active);
    }
    fireEvent.click(screen.getByRole('button',{name:'Send as discussion',exact:true}));
    await waitFor(()=>expect(postWorldBuildAgentTurn).toHaveBeenCalledTimes(1));
    const request=vi.mocked(postWorldBuildAgentTurn).mock.calls[0]![0];
    expect(request.message).toBe(message);
    expect(request.build_draft_context?.snapshot).toEqual(draftSnapshot());
    expect(request.build_draft_context?.snapshot.draft_markdown).toBe('# Unsaved page');
    expect(request).not.toHaveProperty('build_write_capability');
    expect(bridge.insert).not.toHaveBeenCalled();
  });

  it.each([['message','reject'],['source','reject'],['bridge','reject'],['message','resolve'],['source','resolve'],['bridge','resolve'],['source_aba','reject'],['source_aba','resolve']] as const)('does not dispatch retired placement after %s changes (%s)',async(change,outcome)=>{
    let reject!:(reason:Error)=>void;
    let resolve!:(value:CapturedBuildInsertion)=>void;
    const bridge:BuildComposeBridge={captureContext:vi.fn(async()=>draftSnapshot()),capture:vi.fn(()=>new Promise((ok,fail)=>{reject=fail;resolve=ok;})),insert:vi.fn()};
    const view=render(<Harness initial="build" buildBridge={bridge}/>);
    fireEvent.click(await screen.findByRole('button',{name:'Open',exact:true}));
    const input=await screen.findByLabelText('Message DungeonBuddy');
    await waitFor(()=>expect(input).toBeEnabled());
    fireEvent.change(input,{target:{value:'Draft Culture'}});
    fireEvent.click(screen.getByRole('button',{name:'Send message',exact:true}));
    await waitFor(()=>expect(bridge.capture).toHaveBeenCalledTimes(1));
    if(change==='message')fireEvent.change(input,{target:{value:'Keep this newer question'}});
    else if(change==='source'||change==='source_aba'){
      view.rerender(<Harness initial="build" buildBridge={bridge} buildSourceRevision={3}/>);
      if(change==='source_aba')view.rerender(<Harness initial="build" buildBridge={bridge} buildSourceRevision={2}/>);
    }
    else view.rerender(<Harness initial="build" buildBridge={{captureContext:vi.fn(async()=>draftSnapshot()),capture:vi.fn(async()=>insertionCapture()),insert:vi.fn()}}/>);
    await act(async()=>{if(outcome==='reject')reject(new Error('Old insertion point unavailable'));else resolve(insertionCapture());});
    expect(screen.queryByRole('region',{name:'Page proposal unavailable'})).not.toBeInTheDocument();
    expect(screen.queryByRole('button',{name:'Send as discussion'})).not.toBeInTheDocument();
    expect(input).toHaveValue(change==='message'?'Keep this newer question':'Draft Culture');
    expect(postWorldBuildAgentTurn).not.toHaveBeenCalled();
  });

  it('retires visible placement failure across a source round trip',async()=>{
    const bridge:BuildComposeBridge={captureContext:vi.fn(async()=>draftSnapshot()),capture:vi.fn(async()=>{throw new Error('Old placement failure');}),insert:vi.fn()};
    const view=render(<Harness initial="build" buildBridge={bridge}/>);
    fireEvent.click(await screen.findByRole('button',{name:'Open',exact:true}));
    const input=await screen.findByLabelText('Message DungeonBuddy');
    await waitFor(()=>expect(input).toBeEnabled());
    fireEvent.change(input,{target:{value:'Draft Culture'}});
    fireEvent.click(screen.getByRole('button',{name:'Send message',exact:true}));
    await screen.findByRole('region',{name:'Page proposal unavailable'});
    view.rerender(<Harness initial="build" buildBridge={bridge} buildSourceRevision={3}/>);
    view.rerender(<Harness initial="build" buildBridge={bridge} buildSourceRevision={2}/>);
    expect(screen.queryByRole('button',{name:'Send as discussion'})).not.toBeInTheDocument();
    expect(input).toHaveValue('Draft Culture');
    expect(postWorldBuildAgentTurn).not.toHaveBeenCalled();
  });

  it('prepares a fresh Build capability after the author corrects placement',async()=>{
    const capture=vi.fn().mockRejectedValueOnce(new Error('Select an insertion point')).mockResolvedValueOnce(insertionCapture());
    const bridge:BuildComposeBridge={captureContext:vi.fn(async()=>draftSnapshot()),capture,insert:vi.fn()};
    vi.mocked(postWorldBuildAgentTurn).mockImplementation(()=>new Promise(()=>{}));
    render(<Harness initial="build" buildBridge={bridge}/>);
    fireEvent.click(await screen.findByRole('button',{name:'Open',exact:true}));
    const input=await screen.findByLabelText('Message DungeonBuddy');
    await waitFor(()=>expect(input).toBeEnabled());
    fireEvent.change(input,{target:{value:'Draft Culture'}});
    fireEvent.click(screen.getByRole('button',{name:'Send message',exact:true}));
    await screen.findByRole('region',{name:'Page proposal unavailable'});
    fireEvent.click(screen.getByRole('button',{name:'Send message',exact:true}));
    await waitFor(()=>expect(postWorldBuildAgentTurn).toHaveBeenCalledTimes(1));
    expect(vi.mocked(postWorldBuildAgentTurn).mock.calls[0]![0].build_write_capability?.draft_markdown).toBe('# Unsaved page');
    expect(bridge.capture).toHaveBeenCalledTimes(2);
    expect(bridge.insert).not.toHaveBeenCalled();
  });
  it.each(["plan", "play", "build"] as const)("reuses Build page history and demand-loads %s conversation history", async initial => {
    render(<Harness initial={initial} />);
    const open = await screen.findByRole("button", { name: "Open", exact: true });
    await act(async () => { await new Promise(resolve => setTimeout(resolve, 20)); });
    if (initial === "build") {
      await waitFor(() => expect(getWorldAgentConversationHistory).toHaveBeenCalledTimes(1));
    } else {
      expect(getWorldAgentConversationHistory).not.toHaveBeenCalled();
    }
    fireEvent.click(open);
    await waitFor(() => expect(getWorldAgentConversationHistory).toHaveBeenCalledTimes(1));
    await screen.findByText("Original Plan answer");
    fireEvent.change(screen.getByLabelText("Message DungeonBuddy"), { target: { value: "Keep my draft" } });
    fireEvent.click(screen.getByRole("button", { name: initial === "plan" ? "Close chat" : "Close conversation", exact: true }));
    const count = vi.mocked(getWorldAgentConversationHistory).mock.calls.length;
    await act(async () => { await new Promise(resolve => setTimeout(resolve, 20)); });
    expect(getWorldAgentConversationHistory).toHaveBeenCalledTimes(count);
    fireEvent.click(screen.getByRole("button", { name: "Open", exact: true }));
    await waitFor(() => expect(getWorldAgentConversationHistory).toHaveBeenCalledTimes(initial === "build" ? count : count + 1));
    expect(screen.getByLabelText("Message DungeonBuddy")).toHaveValue("Keep my draft");
    expect(postWorldPlanAgentTurn).not.toHaveBeenCalled();
    expect(postWorldPlayAgentTurn).not.toHaveBeenCalled();
    expect(postWorldBuildAgentTurn).not.toHaveBeenCalled();
  });

  it.each(["plan", "play", "build"] as const)("continues %s pending-turn reconciliation with Buddy closed", async initial => {
    render(<Harness initial={initial} />);
    await screen.findByRole("button", { name: "Open", exact:true });
    if (initial === "build") {
      await waitFor(() => expect(getWorldAgentConversationHistory).toHaveBeenCalledTimes(1));
    } else {
      expect(getWorldAgentConversationHistory).not.toHaveBeenCalled();
    }
    fireEvent.click(screen.getByRole("button", {name:"Seed newer pending request"}));
    await waitFor(() => expect(getWorldAgentConversationHistory).toHaveBeenCalledTimes(initial === "build" ? 2 : 1));
    expect(screen.getByRole("button", { name:"Open", exact:true })).toBeInTheDocument();
    expect(postWorldPlanAgentTurn).not.toHaveBeenCalled();
    expect(postWorldPlayAgentTurn).not.toHaveBeenCalled();
    expect(postWorldBuildAgentTurn).not.toHaveBeenCalled();
  });

  it("cancels a closed-pane history subscription and ignores its late result after reopening", async () => {
    const releases:Array<(value:ReturnType<typeof history>)=>void>=[];
    vi.mocked(getWorldAgentConversationHistory).mockImplementation(() => new Promise(resolve=>{releases.push(resolve);}));
    render(<Harness initial="play" />);
    fireEvent.click(await screen.findByRole("button", {name:"Open",exact:true}));
    await waitFor(()=>expect(releases).toHaveLength(1));
    const signal=vi.mocked(getWorldAgentConversationHistory).mock.calls[0][1]?.signal;
    expect(signal?.aborted).toBe(false);
    fireEvent.click(screen.getByRole("button",{name:"Close conversation",exact:true}));
    expect(signal?.aborted).toBe(true);
    fireEvent.click(screen.getByRole("button",{name:"Open",exact:true}));
    await waitFor(()=>expect(releases).toHaveLength(2));
    await act(async()=>{releases[1](history([turn("play",2,"Fresh current answer")]));});
    await screen.findByText("Fresh current answer");
    await act(async()=>{releases[0](history([turn("play",1,"Stale closed-pane answer")]));});
    expect(screen.queryByText("Stale closed-pane answer")).not.toBeInTheDocument();
    expect(screen.getByText("Fresh current answer")).toBeInTheDocument();
  });

  it.each([false, true])("validates session evidence history and its pinned World citation (foreign=%s)", async foreign => {
    const context = await planGraphContext("plan_only_graph_unused");
    const url = `/play?world=${foreign ? "other-world" : WORLD}&run=11111111-1111-4111-8111-111111111111&evidence_revision=54`;
    const text = `Players want more combat. [Closing reflections](${url})`;
    context.completion = {...context.completion!, answer_basis: "committed_plan_plus_session_evidence", answer_segments: [{kind:"session_evidence_claim",text,run_id:"11111111-1111-4111-8111-111111111111",review_revision:54,evidence_sha256:"a".repeat(64)}],citation_map:null};
    const prior = turn("plan",1,text);
    const basis = context.receipt.plan_basis;
    const row = {...prior,provenance:{...prior.provenance,primary_work:{...prior.provenance.primary_work,revision:String(basis.object_revision),object_revision:basis.object_revision,revision_n:basis.revision_n,work_revision_id:basis.work_revision_id,content_sha256:basis.content_sha256}}};
    vi.mocked(getWorldAgentConversationHistory).mockResolvedValue({...history([{...row,plan_context:context}]),schema:"dmb_agent_conversation_history_v2"} as WorldAgentConversationHistoryResponse);
    render(<Harness initial="plan" />);
    fireEvent.click(await screen.findByRole("button", {name:"Open"}));
    if (foreign) {
      await screen.findByText("The World conversation response did not match the selected World or contained an invalid Graph-context receipt. Refresh history before continuing.");
      expect(screen.queryByRole("link", {name:"Closing reflections"})).not.toBeInTheDocument();
    } else {
      expect(await screen.findByRole("link", {name:"Closing reflections"})).toHaveAttribute("href", url);
    }
  });

  it("shows recovery only after an active Build request becomes uncertain, including after remount", async () => {
    let reject!: (reason: Error) => void;
    vi.mocked(postWorldBuildAgentTurn).mockReturnValue(new Promise((_resolve, rejectRequest) => { reject = rejectRequest; }));
    const mounted = render(<Harness initial="build" />);
    fireEvent.click(await screen.findByRole("button", { name: "Open" }));
    await waitFor(() => expect(screen.getByLabelText("Message DungeonBuddy")).toBeEnabled());
    fireEvent.change(screen.getByLabelText("Message DungeonBuddy"), { target: { value: "Describe Mirathorn" } });
    fireEvent.click(screen.getByRole("button", { name: "Send message" }));
    await waitFor(() => expect(postWorldBuildAgentTurn).toHaveBeenCalledTimes(1));
    expect(screen.getByRole("button", { name: "Send message" })).toHaveTextContent("Working…");
    expect(screen.queryByRole("region", { name: "Saved turn recovery" })).not.toBeInTheDocument();
    expect(screen.queryByText("This request needs recovery. You can check its saved status or retry the exact request.")).not.toBeInTheDocument();
    await act(async () => { reject(new Error("Connection lost after submit")); });
    openConversationOptions();
    await screen.findByRole("region", { name: "Saved turn recovery" });
    expect(screen.getByRole("button", { name: "Retry exact saved turn" })).toBeEnabled();
    mounted.unmount();
    render(<Harness initial="build" />);
    fireEvent.click(await screen.findByRole("button", { name: "Open" }));
    openConversationOptions();
    await screen.findByRole("region", { name: "Saved turn recovery" });
    expect(screen.getByRole("button", { name: "Retry exact saved turn" })).toBeEnabled();
    expect(postWorldBuildAgentTurn).toHaveBeenCalledTimes(1);
  });

  it("retains the exact Build envelope when the session changes after dispatch", async () => {
    let reject!: (reason: Error) => void;
    vi.mocked(postWorldBuildAgentTurn).mockReturnValue(new Promise((_resolve, fail) => { reject = fail; }));
    const mounted = render(<Harness initial="build" />);
    fireEvent.click(await screen.findByRole("button", { name: "Open" }));
    const input = screen.getByLabelText("Message DungeonBuddy");
    await waitFor(() => expect(input).toBeEnabled());
    fireEvent.change(input, { target: { value: "Construct the households table" } });
    fireEvent.click(screen.getByRole("button", { name: "Send message" }));
    await waitFor(() => expect(postWorldBuildAgentTurn).toHaveBeenCalledTimes(1));
    const key = 'dmb:world-play-pending-turn:v1:' + WORLD;
    const envelope = localStorage.getItem(key);
    expect(envelope).not.toBeNull();
    fireEvent.change(input, { target: { value: "My next thought" } });
    await act(async () => { reject(new LiveApiError("Local session changed during this reply. Check the saved request.", 401, { code: "local_graph_session_changed" })); });
    expect(localStorage.getItem(key)).toBe(envelope);
    expect(input).toHaveValue("My next thought");
    openConversationOptions();
    await screen.findByRole("region", { name: "Saved turn recovery" });
    mounted.unmount();
    render(<Harness initial="build" />);
    fireEvent.click(await screen.findByRole("button", { name: "Open" }));
    openConversationOptions();
    await screen.findByRole("region", { name: "Saved turn recovery" });
    expect(screen.getByLabelText("Message DungeonBuddy")).toHaveValue("My next thought");
    expect(localStorage.getItem(key)).toBe(envelope);
    expect(postWorldBuildAgentTurn).toHaveBeenCalledTimes(1);
  });

  it('retains an unknown-outcome original-context retry across reload without automatic resend',async()=>{
    const request:WorldBuildAgentTurnRequestV1={schema:'dmb_agent_turn_request_v1',client_thread_id:'00000000-0000-4000-8000-000000000021',turn_id:'00000000-0000-4000-8000-000000000022',
      surface:{surface_id:'build',instance_id:'original-surface'},owner_scope:{kind:'world',world_id:WORLD},
      primary_work:{kind:'build',object_id:'source-other',expected_revision:2,expected_content_sha256:SHA},client_work_state:'saved_dirty',
      graph_request:{mode:'world',world_id:WORLD,campaign_id:null,revision_pin:null,focus:{kind:'none',session_id:null,campaign_id:null}},graph_selection:null,message:'Original question',
      build_draft_context:{snapshot:{...draftSnapshot(),document_id:'source-other'},conversation_id:'11111111-1111-4111-8111-111111111111',expected_pointer_revision:1},
      retry_of:{turn_id:'22222222-2222-4222-8222-000000000001',revision:4,retained_snapshot_sha256:SHA}};
    const key='dmb:world-play-pending-turn:v1:'+WORLD,serialized=JSON.stringify({schema:'dmb_world_play_pending_turn_v1',request});
    localStorage.setItem(key,serialized);
    vi.mocked(postWorldBuildAgentTurn).mockImplementation(()=>new Promise(()=>{}));
    const bridge=retryBridge();render(<Harness initial='build' buildBridge={bridge}/>);
    fireEvent.click(await screen.findByRole('button',{name:'Open'}));
    openConversationOptions();
    const retry=await screen.findByRole('button',{name:'Retry exact saved turn'});
    await waitFor(()=>expect(retry).toBeEnabled());
    expect(postWorldBuildAgentTurn).not.toHaveBeenCalled();expect(localStorage.getItem(key)).toBe(serialized);
    fireEvent.click(retry);
    await waitFor(()=>expect(vi.mocked(postWorldBuildAgentTurn).mock.calls[0]?.[0]).toEqual(request));
    expect(bridge.captureContext).not.toHaveBeenCalled();expect(readDiscussionRetryInput).not.toHaveBeenCalled();
  });

  it('retries with retained foreign-page context without capturing the current editor or clearing typing',async()=>{
    const prior=turn('plan',1,'');
    const terminal={...prior,lifecycle_status:'interrupted' as const,provenance:{...prior.provenance,surface_id:'build' as const,primary_work:{...prior.provenance.primary_work,object_id:'source-other'}}};
    const saved=history([terminal]);
    vi.mocked(getWorldAgentConversationHistory).mockResolvedValue(saved);
    const snapshot={...draftSnapshot(),document_id:'source-other'};
    vi.mocked(readDiscussionRetryInput).mockResolvedValue({schema:'dmb_build_retained_discussion_retry_input_v1',world_id:WORLD,conversation_id:saved.conversation_id!,turn_id:saved.turns[0].turn_id,revision:4,pointer_revision:1,surface_instance_id:'original-surface',message:prior.user_text,client_work_state:'saved_clean',snapshot,snapshot_sha256:SHA,authored_references:null});
    vi.mocked(postWorldBuildAgentTurn).mockImplementation(()=>new Promise(()=>{}));
    const bridge=retryBridge();
    render(<Harness initial='build' buildBridge={bridge}/>);
    fireEvent.click(await screen.findByRole('button',{name:'Open'}));
    const retry=await screen.findByRole('button',{name:'Retry question'});
    await waitFor(()=>expect(retry).toBeEnabled());
    const input=screen.getByLabelText('Message DungeonBuddy');
    fireEvent.change(input,{target:{value:'Keep the newer Edge draft'}});
    fireEvent.click(retry);fireEvent.click(retry);
    await waitFor(()=>expect(postWorldBuildAgentTurn).toHaveBeenCalledTimes(1));
    const request=vi.mocked(postWorldBuildAgentTurn).mock.calls[0][0];
    expect(request.primary_work.object_id).toBe('source-other');expect(request.client_work_state).toBe('saved_clean');
    expect(request.build_draft_context?.snapshot).toEqual(snapshot);
    expect(request.retry_of).toEqual({turn_id:saved.turns[0].turn_id,revision:4,retained_snapshot_sha256:SHA});
    expect(request.build_write_capability).toBeUndefined();
    expect(bridge.captureContext).not.toHaveBeenCalled();expect(bridge.capture).not.toHaveBeenCalled();
    expect(input).toHaveValue('Keep the newer Edge draft');
    expect(JSON.parse(localStorage.getItem('dmb:world-play-pending-turn:v1:'+WORLD)! ).request).toEqual(request);
  });

  it.each((["plan", "play", "build"] as const).flatMap(surface => [false,true].map(otherDraft=>({surface,otherDraft}))))("retries terminal $surface in one click and preserves another draft: $otherDraft", async ({surface,otherDraft}) => {
    const prior = turn(surface === "build" ? "plan" : surface, 1, "");
    const terminal = {...prior, lifecycle_status: "interrupted" as const,
      provenance: {...prior.provenance, surface_id: surface,
        primary_work: {...prior.provenance.primary_work,
          object_id: surface === "build" ? "source-one" : prior.provenance.primary_work.object_id}}};
    vi.mocked(getWorldAgentConversationHistory).mockResolvedValue(history([terminal]));
    vi.mocked(postWorldPlanAgentTurn).mockImplementation(()=>new Promise(()=>{}));
    vi.mocked(postWorldPlayAgentTurn).mockImplementation(()=>new Promise(()=>{}));
    vi.mocked(postWorldBuildAgentTurn).mockImplementation(()=>new Promise(()=>{}));
    render(<Harness initial={surface} buildBridge={surface==='build'?retryBridge():undefined} />);
    fireEvent.click(await screen.findByRole("button", {name:"Open"}));
    const retry = await screen.findByRole("button", {name:"Retry question"});
    await waitFor(() => expect(retry).toBeEnabled());
    const failureText = screen.getByText(surface === 'build'
      ? 'This reply stopped before it finished. Your saved source was not changed.'
      : surface === 'play' ? 'This reply stopped before it finished. No Run change was applied.'
      : 'This reply stopped before it finished. Your Plan was not changed.');
    const debug = failureText.closest('details')!;
    expect(debug).not.toHaveAttribute('open');
    expect(retry.closest('.world-plan-agent-conversation__turn-status')).not.toContainElement(failureText);
    fireEvent.click(within(debug).getByText('Debug', {exact:true}));
    expect(debug).toHaveAttribute('open');
    fireEvent.click(within(debug).getByText('Debug', {exact:true}));
    const input=screen.getByLabelText("Message DungeonBuddy");
    if(otherDraft)fireEvent.change(input,{target:{value:"Keep my unsent draft"}});
    fireEvent.click(retry);fireEvent.click(retry);
    const post=surface==='build'?postWorldBuildAgentTurn:surface==='play'?postWorldPlayAgentTurn:postWorldPlanAgentTurn;
    await waitFor(()=>expect(post).toHaveBeenCalledTimes(1));
    const request=vi.mocked(post).mock.calls[0][0];
    expect(request.message).toBe(prior.user_text);expect(request.turn_id).not.toBe(prior.turn_id);
    if(surface==='build')expect((request as {retry_of?:unknown}).retry_of).toEqual({turn_id:'22222222-2222-4222-8222-000000000001',revision:4});
    expect(input).toHaveValue(otherDraft?"Keep my unsent draft":"");
    expect(screen.getAllByText(prior.user_text,{exact:true})).toHaveLength(1);
    expect(screen.queryByLabelText("Submitted message")).not.toBeInTheDocument();
    expect(screen.getByText("Retrying your question…")).toBeInTheDocument();
    fireEvent.change(input,{target:{value:"Keep my newer typing"}});
    expect(input).toHaveValue("Keep my newer typing");expect(retry).toBeDisabled();
    expect(screen.queryByLabelText("Turn surface")).not.toBeInTheDocument();
  });

  it.each(["plan","play","build"] as const)("keeps consecutive failed %s requests in one visible turn across remount",async surface=>{
    const base=turn(surface==='build'?'plan':surface,1,'');
    const rows=[1,2,3].map(sequence=>({...base,turn_id:`failed-${sequence}`,sequence,
      lifecycle_status:'interrupted' as const,provenance:{...base.provenance,surface_id:surface,
        primary_work:{...base.provenance.primary_work,object_id:surface==='build'?'source-one':base.provenance.primary_work.object_id}}}));
    const page=history(rows);
    if(surface==='build')page.turns=page.turns.map((row,index)=>({...row,retry_context:{...row.retry_context!,root_id:page.turns[0].turn_id,ordinal:index,
      predecessor_id:index?page.turns[index-1].turn_id:null,successor_id:index<2?page.turns[index+1].turn_id:null,
      eligible:index===2,reason:index===2?'ready':'retried'}}));
    vi.mocked(getWorldAgentConversationHistory).mockResolvedValue(page);
    const view=render(<Harness initial={surface}/>);fireEvent.click(await screen.findByRole('button',{name:'Open',exact:true}));
    await screen.findByRole('button',{name:'Retry question'});
    expect(screen.getAllByText(base.user_text,{exact:true})).toHaveLength(1);
    expect(screen.queryByText(/Earlier conversation/)).not.toBeInTheDocument();
    fireEvent.click(screen.getByText('Debug',{exact:true}));
    expect(await screen.findByText('Previous attempts · 2')).toBeInTheDocument();
    expect(screen.getAllByRole('button',{name:'Retry question'})).toHaveLength(1);
    view.unmount();render(<Harness initial={surface}/>);fireEvent.click(await screen.findByRole('button',{name:'Open',exact:true}));
    await screen.findByRole('button',{name:'Retry question'});
    expect(screen.getAllByText(base.user_text,{exact:true})).toHaveLength(1);
  });

  it('clears a refused Build retry without overwriting newer writing or dispatching again',async()=>{
    const base=turn('plan',1,''),terminal={...base,lifecycle_status:'interrupted' as const,
      provenance:{...base.provenance,surface_id:'build',primary_work:{...base.provenance.primary_work,object_id:'source-one'}}};
    vi.mocked(getWorldAgentConversationHistory).mockResolvedValue(history([terminal]));
    let reject!:(reason:Error)=>void;vi.mocked(postWorldBuildAgentTurn).mockImplementation(()=>new Promise((_resolve,failed)=>{reject=failed;}));
    render(<Harness initial='build' buildBridge={retryBridge()}/>);fireEvent.click(await screen.findByRole('button',{name:'Open',exact:true}));
    fireEvent.click(await screen.findByRole('button',{name:'Retry question'}));await waitFor(()=>expect(postWorldBuildAgentTurn).toHaveBeenCalledTimes(1));
    fireEvent.change(screen.getByLabelText('Message DungeonBuddy'),{target:{value:'Newer retry thought'}});
    await act(async()=>reject(new LiveApiError('This attempt already has a successor',409,{code:'build_retry_unavailable'})));
    await waitFor(()=>expect(screen.getByRole('button',{name:'Send message'})).toBeEnabled());
    expect(screen.getByLabelText('Message DungeonBuddy')).toHaveValue('Newer retry thought');
    expect(window.localStorage.getItem(`dmb:world-play-pending-turn:v1:${encodeURIComponent(WORLD)}`)).toBeNull();
    expect(postWorldBuildAgentTurn).toHaveBeenCalledTimes(1);
  });

  it('retains an exact pending Build retry across remount without losing newer composer text',async()=>{
    const base=turn('plan',1,''),terminal={...base,lifecycle_status:'interrupted' as const,
      provenance:{...base.provenance,surface_id:'build',primary_work:{...base.provenance.primary_work,object_id:'source-one'}}};
    vi.mocked(getWorldAgentConversationHistory).mockResolvedValue(history([terminal]));
    vi.mocked(postWorldBuildAgentTurn).mockImplementation(()=>new Promise(()=>{}));
    const view=render(<Harness initial='build' buildBridge={retryBridge()}/>);fireEvent.click(await screen.findByRole('button',{name:'Open',exact:true}));
    fireEvent.click(await screen.findByRole('button',{name:'Retry question'}));await waitFor(()=>expect(postWorldBuildAgentTurn).toHaveBeenCalledTimes(1));
    fireEvent.change(screen.getByLabelText('Message DungeonBuddy'),{target:{value:'Newer retained retry note'}});
    const request=vi.mocked(postWorldBuildAgentTurn).mock.calls[0][0],key=`dmb:world-play-pending-turn:v1:${encodeURIComponent(WORLD)}`,bytes=window.localStorage.getItem(key);
    expect(JSON.parse(bytes!).request.retry_of).toEqual(request.retry_of);
    view.unmount();render(<Harness initial='build' buildBridge={retryBridge()}/>);fireEvent.click(await screen.findByRole('button',{name:'Open',exact:true}));
    expect(screen.queryByText(/saved Play request is malformed/i)).not.toBeInTheDocument();
    expect(screen.getByLabelText('Message DungeonBuddy')).toHaveValue('Newer retained retry note');
    expect(window.localStorage.getItem(key)).toBe(bytes);expect(postWorldBuildAgentTurn).toHaveBeenCalledTimes(1);
  });

  it('keeps a successful explicit Build retry grouped after remount with no ancestor Retry',async()=>{
    const first=turn('plan',1,''),last=turn('plan',2,'Retry result');
    const cid='11111111-1111-4111-8111-111111111111',root='22222222-2222-4222-8222-000000000001',leaf='22222222-2222-4222-8222-000000000002';
    const rows=[first,last].map((row,i)=>({...row,turn_id:i?leaf:root,lifecycle_status:i?'completed' as const:'interrupted' as const,
      provenance:{...row.provenance,surface_id:'build',primary_work:{...row.provenance.primary_work,kind:'build',object_id:'source-one'}},
      retry_context:{world_id:WORLD,conversation_id:cid,turn_id:i?leaf:root,revision:4,root_id:root,ordinal:i,
        predecessor_id:i?root:null,successor_id:i?null:leaf,eligible:false,reason:i?'not_terminal' as const:'retried' as const}}));
    vi.mocked(getWorldAgentConversationHistory).mockResolvedValue(history(rows));
    const view=render(<Harness initial='build'/>);fireEvent.click(await screen.findByRole('button',{name:'Open',exact:true}));
    await screen.findByText('Retry result');expect(screen.getAllByText(first.user_text,{exact:true})).toHaveLength(1);
    expect(screen.queryByRole('button',{name:'Retry question'})).not.toBeInTheDocument();const priorAttempts=screen.getByText('Previous attempts · 1');
    expect(priorAttempts).not.toBeVisible();
    const debug=priorAttempts.closest('details.world-plan-agent-conversation__turn-details');
    expect(debug).not.toBeNull();expect(debug).not.toHaveAttribute('open');
    fireEvent.click(within(debug as HTMLElement).getByText('Debug',{exact:true}));
    expect(priorAttempts).toBeVisible();
    view.unmount();render(<Harness initial='build'/>);fireEvent.click(await screen.findByRole('button',{name:'Open',exact:true}));
    await screen.findByText('Retry result');expect(screen.getAllByText(first.user_text,{exact:true})).toHaveLength(1);
    expect(screen.queryByRole('button',{name:'Retry question'})).not.toBeInTheDocument();
  });

  it.each([false,true])("shows an exact Build retry placement failure while preserving its draft: %s",async otherDraft=>{
    const prior=turn('plan',1,'');const terminal={...prior,lifecycle_status:'interrupted' as const,
      provenance:{...prior.provenance,surface_id:'build',primary_work:{...prior.provenance.primary_work,object_id:'source-one'}}};
    vi.mocked(getWorldAgentConversationHistory).mockResolvedValue(history([terminal]));
    const bridge:BuildComposeBridge={captureContext:vi.fn(async()=>draftSnapshot()),capture:vi.fn(async()=>{throw new Error('Choose a page caret for this retry');}),insert:vi.fn()};
    render(<Harness initial="build" buildBridge={bridge}/>);fireEvent.click(await screen.findByRole('button',{name:'Open',exact:true}));
    const retry=await screen.findByRole('button',{name:'Retry question'});await waitFor(()=>expect(retry).toBeEnabled());
    const input=screen.getByLabelText('Message DungeonBuddy');if(otherDraft)fireEvent.change(input,{target:{value:'My other thought'}});
    fireEvent.click(retry);expect(await screen.findByText('Choose a page caret for this retry')).toHaveAttribute('role','alert');
    expect(input).toHaveValue(otherDraft?'My other thought':'');expect(postWorldBuildAgentTurn).not.toHaveBeenCalled();expect(retry).toBeEnabled();
  });
  it('continues Build retry capture independently of newer conversation typing',async()=>{
    const prior=turn('plan',1,'');const terminal={...prior,lifecycle_status:'interrupted' as const,
      provenance:{...prior.provenance,surface_id:'build',primary_work:{...prior.provenance.primary_work,object_id:'source-one'}}};
    vi.mocked(getWorldAgentConversationHistory).mockResolvedValue(history([terminal]));
    vi.mocked(postWorldBuildAgentTurn).mockImplementation(()=>new Promise(()=>{}));
    let finish!:(value:ReturnType<typeof insertionCapture>)=>void;
    const bridge:BuildComposeBridge={captureContext:vi.fn(async()=>draftSnapshot()),capture:vi.fn(()=>new Promise(resolve=>{finish=resolve;})),insert:vi.fn()};
    render(<Harness initial="build" buildBridge={bridge}/>);fireEvent.click(await screen.findByRole('button',{name:'Open',exact:true}));
    const retry=await screen.findByRole('button',{name:'Retry question'});await waitFor(()=>expect(retry).toBeEnabled());fireEvent.click(retry);
    await waitFor(()=>expect(bridge.capture).toHaveBeenCalledTimes(1));
    const input=screen.getByLabelText('Message DungeonBuddy');fireEvent.change(input,{target:{value:prior.user_text}});
    await act(async()=>finish(insertionCapture()));await waitFor(()=>expect(postWorldBuildAgentTurn).toHaveBeenCalledTimes(1));
    expect(input).toHaveValue(prior.user_text);
  });

  it('reports a same-page revision change during retry preparation instead of silently returning',async()=>{
    const prior=turn('plan',1,'');const terminal={...prior,lifecycle_status:'interrupted' as const,
      provenance:{...prior.provenance,surface_id:'build',primary_work:{...prior.provenance.primary_work,object_id:'source-one'}}};
    vi.mocked(getWorldAgentConversationHistory).mockResolvedValue(history([terminal]));
    let finish!:(value:ReturnType<typeof insertionCapture>)=>void;
    const bridge:BuildComposeBridge={captureContext:vi.fn(async()=>draftSnapshot()),capture:vi.fn(()=>new Promise(resolve=>{finish=resolve;})),insert:vi.fn()};
    const view=render(<Harness initial="build" buildBridge={bridge}/>);fireEvent.click(await screen.findByRole('button',{name:'Open',exact:true}));
    const retry=await screen.findByRole('button',{name:'Retry question'});await waitFor(()=>expect(retry).toBeEnabled());
    fireEvent.change(screen.getByLabelText('Message DungeonBuddy'),{target:{value:'Keep my next thought'}});
    fireEvent.click(retry);await waitFor(()=>expect(bridge.capture).toHaveBeenCalledTimes(1));
    view.rerender(<Harness initial="build" buildBridge={bridge} buildSourceRevision={3}/>);
    await act(async()=>finish(insertionCapture()));
    expect(await screen.findByText('The page or conversation changed while preparing this retry. Nothing was sent. Retry again to use the current page.')).toHaveAttribute('role','alert');
    expect(postWorldBuildAgentTurn).not.toHaveBeenCalled();expect(screen.getByLabelText('Message DungeonBuddy')).toHaveValue('Keep my next thought');
    vi.mocked(bridge.captureContext).mockResolvedValue({...draftSnapshot(),registry_revision:3});
    vi.mocked(bridge.capture).mockResolvedValue({...insertionCapture(),basis:{...insertionCapture().basis,registry_revision:3}});
    vi.mocked(postWorldBuildAgentTurn).mockImplementation(()=>new Promise(()=>{}));
    fireEvent.click(await screen.findByRole('button',{name:'Retry question'}));
    await waitFor(()=>expect(postWorldBuildAgentTurn).toHaveBeenCalledTimes(1));
    expect(vi.mocked(postWorldBuildAgentTurn).mock.calls[0][0].primary_work.expected_revision).toBe(3);
    expect(screen.getByLabelText('Message DungeonBuddy')).toHaveValue('Keep my next thought');
  });

  it.each(['page','world'] as const)('retires retry preparation after foreign %s navigation without posting or showing an old error',async change=>{
    const prior=turn('plan',1,'');const terminal={...prior,lifecycle_status:'interrupted' as const,
      provenance:{...prior.provenance,surface_id:'build',primary_work:{...prior.provenance.primary_work,object_id:'source-one'}}};
    vi.mocked(getWorldAgentConversationHistory).mockResolvedValue(history([terminal]));
    let finish!:(value:ReturnType<typeof insertionCapture>)=>void;
    const bridge:BuildComposeBridge={captureContext:vi.fn(async()=>draftSnapshot()),capture:vi.fn(()=>new Promise(resolve=>{finish=resolve;})),insert:vi.fn()};
    const view=render(<Harness initial="build" buildBridge={bridge}/>);fireEvent.click(await screen.findByRole('button',{name:'Open',exact:true}));
    const retry=await screen.findByRole('button',{name:'Retry question'});await waitFor(()=>expect(retry).toBeEnabled());fireEvent.click(retry);
    await waitFor(()=>expect(bridge.capture).toHaveBeenCalledTimes(1));
    if(change==='page')view.rerender(<Harness initial="build" buildBridge={bridge} buildSourceId="foreign-page"/>);
    else fireEvent.click(screen.getByRole('button',{name:'Switch World'}));
    await act(async()=>finish(insertionCapture()));
    expect(postWorldBuildAgentTurn).not.toHaveBeenCalled();expect(screen.queryByText('The page or conversation changed while preparing this retry. Nothing was sent. Retry again to use the current page.')).not.toBeInTheDocument();
  });

  it.each(["failed", "interrupted"] as const)("labels a historical Build %s with its saved source while viewing Plan", async lifecycle => {
    const historical = { ...turn("plan", 1, ""), lifecycle_status: lifecycle,
      provenance: { ...turn("plan", 1, "").provenance, surface_id: "build", surface_instance_id: "build-instance",
        primary_work: { resolution: "resolved" as const, kind: "build", object_id: "source-one", revision: "2",
          content_sha256: SHA, object_revision: null, work_revision_id: null, revision_n: null } } };
    vi.mocked(getWorldAgentConversationHistory).mockResolvedValue(history([historical]));
    render(<Harness initial="plan" />);
    fireEvent.click(await screen.findByRole("button", { name: "Open" }));
    await screen.findByText(lifecycle === "failed"
      ? "Buddy couldn’t finish this reply. Your saved source was not changed."
      : "This reply stopped before it finished. Your saved source was not changed.");
    expect(screen.queryByLabelText("Turn surface")).not.toBeInTheDocument();
    expect(screen.queryByRole("button", {name: "Retry question"})).not.toBeInTheDocument();
    expect(screen.queryByText(/Your Plan was not changed/)).not.toBeInTheDocument();
    expect(postWorldBuildAgentTurn).not.toHaveBeenCalled();
  });

  it.each([false, true])("opens a pinned Build Graph passage and rejects foreign source context: %s", async foreign => {
    const context = await buildGraphContext();
    const base = turn("plan", 1, "The western gate is watched.");
    const source = context.receipt.source_basis;
    const authority = context.receipt.graph_authority;
    const ref = (kind: string, object_id: string, revision: string) => ({ resolution: "resolved" as const,
      kind, object_id, revision, content_sha256: null, object_revision: null, work_revision_id: null, revision_n: null });
    const historical = { ...base, knowledge_context: context,
      provenance: { ...base.provenance, surface_id: "build", surface_instance_id: "build-instance",
        primary_work: { ...ref("build", "source-one", "2"), content_sha256: SHA }, supporting_work: [
          ref("dmb_build_source_visibility_v1", source.visibility, "1"),
          ref("dmb_build_graph_binding_v1", authority.native_world_id, String(authority.binding_version)),
          ref("world_graph_revision", authority.native_world_id, authority.graph_revision),
        ] } };
    if (foreign) context.receipt.source_basis.document_id = "another-source";
    vi.mocked(getWorldAgentConversationHistory).mockResolvedValue({ ...history(),
      schema: "dmb_agent_conversation_history_v2", turns: [historical] });
    vi.mocked(postWorldGraphSourceAnchorRead).mockResolvedValue({
      schema: "dmb_world_graph_source_anchor_read_v1", outcome: "enough", anchorId: "anchor-one",
      evidenceRefId: "evidence-internal-test", sourceArtifactId: "artifact-one", sourceRevisionId: "source-rev-one",
      content: "The saved source describes the guards at the western gate.", truncated: false,
      snapshot: { worldId: authority.native_world_id, campaignId: "", revisionId: authority.graph_revision,
        scopeMode: "world", admissibility: "gm", focus: {kind: "none", sessionId: null, campaignId: null} },
    } as Awaited<ReturnType<typeof postWorldGraphSourceAnchorRead>>);
    render(<Harness initial="build" />);
    fireEvent.click(await screen.findByRole("button", {name: "Open"}));
    if (foreign) {
      await screen.findByRole("group", {name: "World history unavailable"});
      expect(screen.queryByRole("button", {name: "Open evidence"})).not.toBeInTheDocument();
    } else {
      await screen.findAllByText("The western gate is watched.");
      fireEvent.click(screen.getByText(/1 claim · 1 cited Graph reference/));
      fireEvent.click(await screen.findByRole("button", {name: "Open evidence"}));
      await screen.findByText("The saved source describes the guards at the western gate.");
      expect(postWorldGraphSourceAnchorRead).toHaveBeenCalledWith(expect.objectContaining({
        worldId: authority.native_world_id, revisionPin: authority.graph_revision, anchorId: "anchor-one",
      }));
    }
  });

  it("waits for admission instead of polling the client request UUID", async()=>{
    vi.mocked(getWorldAgentConversationHistory).mockResolvedValue(history());
    vi.mocked(postWorldBuildAgentTurn).mockReturnValue(new Promise(()=>{}));
    render(<Harness initial="build"/>);
    fireEvent.click(await screen.findByRole("button",{name:"Open"}));
    await waitFor(()=>expect(screen.getByLabelText("Message DungeonBuddy")).toBeEnabled());
    fireEvent.change(screen.getByLabelText("Message DungeonBuddy"),{target:{value:"Ask me questions before writing."}});
    fireEvent.click(screen.getByRole("button",{name:"Send message"}));
    await waitFor(()=>expect(postWorldBuildAgentTurn).toHaveBeenCalledTimes(1));
    const request=vi.mocked(postWorldBuildAgentTurn).mock.calls[0][0];
    expect(getWorldAgentTurnContextTrace).not.toHaveBeenCalledWith(WORLD,request.turn_id,expect.any(AbortSignal));
    expect(screen.getByText("Getting things ready…")).toBeInTheDocument();
  });

  it.each(['matching','foreign-message','foreign-source','ambiguous','same-id-foreign-message','same-id-foreign-source'])('binds live Build activity only to admitted correlation: %s',async variant=>{
    vi.mocked(getWorldAgentConversationHistory).mockResolvedValue(history());
    vi.mocked(postWorldBuildAgentTurn).mockReturnValue(new Promise(()=>{}));
    render(<Harness initial="build"/>);
    fireEvent.click(await screen.findByRole('button',{name:'Open',exact:true}));
    await waitFor(()=>expect(screen.getByLabelText('Message DungeonBuddy')).toBeEnabled());
    fireEvent.change(screen.getByLabelText('Message DungeonBuddy'),{target:{value:'Read the named saved page.'}});
    fireEvent.click(screen.getByRole('button',{name:'Send message'}));
    await waitFor(()=>expect(postWorldBuildAgentTurn).toHaveBeenCalledTimes(1));
    const request=vi.mocked(postWorldBuildAgentTurn).mock.calls[0][0];
    const base=turn('plan',1,''),durable='44444444-4444-4444-8444-444444444444';
    const row={...base,turn_id:variant.startsWith('same-id-')?request.turn_id:durable,lifecycle_status:'running' as const,assistant_text:null,
      user_text:variant.endsWith('foreign-message')?'Another question':request.message,
      idempotency_key:await expectedHistoryCorrelationKey(WORLD,request.turn_id),
      provenance:{...base.provenance,surface_id:'build',surface_instance_id:'build-instance',
        primary_work:{...base.provenance.primary_work,kind:'build',object_id:variant.endsWith('foreign-source')?'another-source':request.primary_work.object_id}}};
    vi.mocked(getWorldAgentConversationHistory).mockResolvedValue({...history(),schema:'dmb_agent_conversation_history_v3',
      turns:variant==='ambiguous'?[row,{...row,turn_id:'55555555-5555-4555-8555-555555555555',sequence:2}]:[row]});
    await waitFor(()=>expect(document.querySelector('article[data-sequence="1"]')).toBeInTheDocument(),{timeout:4500});
    if(variant==='matching')await waitFor(()=>expect(getWorldAgentTurnContextTrace).toHaveBeenCalledWith(WORLD,durable,expect.any(AbortSignal)));
    else expect(getWorldAgentTurnContextTrace).not.toHaveBeenCalledWith(WORLD,row.turn_id,expect.any(AbortSignal));
    expect(getWorldAgentTurnContextTrace).not.toHaveBeenCalledWith(WORLD,request.turn_id,expect.any(AbortSignal));
    expect(postWorldBuildAgentTurn).toHaveBeenCalledTimes(1);
  });

  it.each(['discuss','prepare_insertion'] as const)('continues %s with its exact capture capability and newer composer text',async(kind)=>{
    const base=turn('plan',1,'1. Discuss the shop owner.\n2. Prepare the shop description.');
    const row={...base,provenance:{...base.provenance,surface_id:'build',surface_instance_id:'build-instance',primary_work:{...base.provenance.primary_work,kind:'build',object_id:'source-one'}}};
    vi.mocked(getWorldAgentConversationHistory).mockResolvedValue(history([row]));
    const stepId='11111111-1111-4111-8111-111111111111',clientId='22222222-2222-4222-8222-222222222222';
    const p={schema:'dmb_reviewed_work_plan_v3' as const,objective:'Discuss the chosen owner.',root_references:[],world_id:WORLD,conversation_id:history().conversation_id!,source_turn_id:row.turn_id,source_answer_sha256:SHA,document_id:'source-one',revision:1,
      steps:[{step_id:stepId,text:'Discuss the shop owner.',selected:true,kind,references:[]}],dispatches:[],execution:[]};
    const frozen=authoredGraphReferences([authoredRef('reviewed-box')]);
    writeComposerReferences(sessionStorage,WORLD,'source-one',null,[authoredRef('newer-box')]);
    const dispatch={...(kind==='discuss'?{schema:'dmb_work_plan_dispatch_v3' as const,scope:{schema:'dmb_reviewed_discussion_scope_v1' as const,task:{step_id:stepId,kind:'discuss' as const,text:'Discuss the shop owner.'},objective_context:p.objective,sibling_context:[]}}:{schema:'dmb_work_plan_dispatch_v2' as const}),authored_references:frozen,command_id:stepId,step_id:stepId,client_thread_id:stepId,client_turn_id:clientId,message:'Continue exactly this reviewed discussion step.'};
    vi.mocked(getWorkPlan).mockResolvedValue(p);
    vi.mocked(continueWorkPlan).mockResolvedValue({plan:{...p,revision:2,dispatches:[dispatch],execution:[{command_id:stepId,step_id:stepId,status:'awaiting_dispatch',turn_id:null,attempt:null,result:null}]},dispatch,reference:{conversation_id:p.conversation_id,source_turn_id:p.source_turn_id,command_id:dispatch.command_id}});
    vi.mocked(postWorldBuildAgentTurn).mockReturnValue(new Promise(()=>{}));
    const bridge={captureContext:vi.fn(async()=>draftSnapshot()),capture:vi.fn(async()=>{if(kind==='discuss')throw new Error('A plan NodeSelection cannot be an insertion target');return insertionCapture();}),insert:vi.fn()};
    render(<Harness initial='build' buildBridge={bridge}/>);
    fireEvent.click(await screen.findByRole('button',{name:'Open',exact:true}));
    fireEvent.change(await screen.findByLabelText('Message DungeonBuddy'),{target:{value:'My newer unsent author note'}});
    fireEvent.click(await screen.findByRole('button',{name:'Review plan'}));
    await screen.findByLabelText('Saved step 1');
    expect(postWorldBuildAgentTurn).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole('button',{name:'Continue step'}));
    await waitFor(()=>expect(postWorldBuildAgentTurn).toHaveBeenCalledTimes(1));
    expect(vi.mocked(postWorldBuildAgentTurn).mock.calls[0][0]).toMatchObject({turn_id:clientId,client_thread_id:stepId,message:dispatch.message,reviewed_step:{conversation_id:p.conversation_id,source_turn_id:p.source_turn_id,command_id:dispatch.command_id}});
    expect(vi.mocked(postWorldBuildAgentTurn).mock.calls[0][0].build_draft_context?.conversation_id).toBe(p.conversation_id);
    expect(bridge.captureContext).toHaveBeenCalledTimes(1);
    if(kind==='discuss'){expect(bridge.capture).not.toHaveBeenCalled();expect(vi.mocked(postWorldBuildAgentTurn).mock.calls[0][0].build_write_capability).toBeUndefined();}
    else{expect(bridge.capture).toHaveBeenCalledTimes(1);expect(vi.mocked(postWorldBuildAgentTurn).mock.calls[0][0].build_write_capability).toBeDefined();}
    expect(vi.mocked(postWorldBuildAgentTurn).mock.calls[0][0]).not.toHaveProperty('reviewedKind');
    expect(screen.getByLabelText('Message DungeonBuddy')).toHaveValue('My newer unsent author note');
    expect(vi.mocked(postWorldBuildAgentTurn).mock.calls[0][0].build_authored_references).toEqual(frozen);
    expect(readComposerReferences(sessionStorage,WORLD,'source-one').references[0].node_id).toBe('newer-box');
  });

  it('keeps failed author-bound steps on their saved-plan retry owner',async()=>{
    const context=await buildGraphContext();
    context.receipt.assembled_input.assembler_version='reviewed_author_admission_v1';
    const {context_receipt_sha256:_oldHash,...receiptBody}=context.receipt;
    context.receipt.context_receipt_sha256=await sha256Hex(canonicalJson(receiptBody));
    const base=turn('plan',1,'Continue my reviewed insertion.');
    const authority=context.receipt.graph_authority;
    const support=(kind:string,object_id:string,revision:string)=>({...base.provenance.primary_work,kind,object_id,revision,content_sha256:null,object_revision:null});
    const row={...base,assistant_text:null,lifecycle_status:'failed' as const,
      knowledge_context:{...context,completion:null,source_open_targets:[],evidence_anchor_statuses:[],related_recap_context_statuses:[],execution:null},provenance:{...base.provenance,surface_id:'build',surface_instance_id:'build-instance',supporting_work:[support('dmb_build_source_visibility_v1','internal','1'),support('dmb_build_graph_binding_v1',authority.native_world_id,String(authority.binding_version)),support('world_graph_revision',authority.native_world_id,authority.graph_revision)],
        primary_work:{...base.provenance.primary_work,kind:'build',object_id:'source-one',revision:'2',content_sha256:SHA,object_revision:null}}};
    vi.mocked(getWorldAgentConversationHistory).mockResolvedValue({...history(),schema:'dmb_agent_conversation_history_v2',turns:[row]});
    render(<Harness initial='build'/>);
    fireEvent.click(await screen.findByRole('button',{name:'Open',exact:true}));
    await screen.findByText(/Use “Try step again” in the saved reviewed plan/);
    expect(screen.queryByRole('button',{name:'Retry question'})).not.toBeInTheDocument();
    expect(postWorldBuildAgentTurn).not.toHaveBeenCalled();
  });

  it('retires a reserved plan continuation across a source round trip',async()=>{
    const base=turn('plan',1,'1. Discuss the shop owner.\n2. Prepare the shop description.');
    const row={...base,provenance:{...base.provenance,surface_id:'build',surface_instance_id:'build-instance',primary_work:{...base.provenance.primary_work,kind:'build',object_id:'source-one'}}};
    vi.mocked(getWorldAgentConversationHistory).mockResolvedValue(history([row]));
    const stepId='11111111-1111-4111-8111-111111111111',clientId='22222222-2222-4222-8222-222222222222';
    const p={schema:'dmb_reviewed_work_plan_v2' as const,objective:'Discuss the shop owner.',world_id:WORLD,conversation_id:history().conversation_id!,source_turn_id:row.turn_id,source_answer_sha256:SHA,document_id:'source-one',revision:1,
      steps:[{step_id:stepId,text:'Discuss the shop owner.',selected:true,kind:'discuss' as const}],dispatches:[],execution:[]};
    const dispatch={command_id:stepId,step_id:stepId,client_thread_id:stepId,client_turn_id:clientId,message:'Continue exactly this reviewed discussion step.'};
    vi.mocked(getWorkPlan).mockResolvedValue(p);
    let resolve!:(value:Awaited<ReturnType<typeof continueWorkPlan>>)=>void;vi.mocked(continueWorkPlan).mockReturnValue(new Promise(r=>{resolve=r}));
    vi.mocked(postWorldBuildAgentTurn).mockReturnValue(new Promise(()=>{}));
    const view=render(<Harness initial='build'/>);
    fireEvent.click(await screen.findByRole('button',{name:'Open',exact:true}));
    fireEvent.change(await screen.findByLabelText('Message DungeonBuddy'),{target:{value:'My newer unsent author note'}});
    fireEvent.click(await screen.findByRole('button',{name:'Review plan'}));
    await screen.findByLabelText('Saved step 1');
    expect(postWorldBuildAgentTurn).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole('button',{name:'Continue step'}));
    await waitFor(()=>expect(continueWorkPlan).toHaveBeenCalledTimes(1));
    view.rerender(<Harness initial='build' buildSourceId='other-source'/>);
    await act(async()=>{});
    view.rerender(<Harness initial='build' buildSourceId='source-one'/>);
    await act(async()=>{resolve({plan:{...p,revision:2,dispatches:[dispatch],execution:[{command_id:stepId,step_id:stepId,status:'awaiting_dispatch',turn_id:null,attempt:null,result:null}]},dispatch,reference:{conversation_id:p.conversation_id,source_turn_id:p.source_turn_id,command_id:dispatch.command_id}});});
    expect(postWorldBuildAgentTurn).not.toHaveBeenCalled();
  });

  it('opens a named related saved-page citation inline without technical details through the mounted Build conversation',async()=>{
    const context=await buildGraphContext(),base=turn('plan',1,'The saved Households table names Copper House.');
    const readId='11111111-1111-4111-8111-111111111111',body='A saved households table.';
    const page={world_id:WORLD,document_id:readId,registry_revision:9,title:'Households',visibility:'internal' as const,content_sha256:await sha256Hex(body)};
    const completion={schema:'dmb_build_related_page_completion_v1' as const,context_receipt_sha256:context.receipt.context_receipt_sha256,
      answer_basis:'working_draft_context' as const,answer_context_status:'authored_grounded' as const,citation_map:null,source_citations:[],
      answer_segments:[{kind:'related_page_claim' as const,text:base.assistant_text!,read_id:readId,page}]};
    const knowledge={...context,completion,source_open_targets:[],evidence_anchor_statuses:[],related_recap_context_statuses:[]};
    const a=context.receipt.graph_authority;
    const ref=(kind:string,object_id:string,revision:string)=>({resolution:'resolved' as const,kind,object_id,revision,content_sha256:null,object_revision:null,work_revision_id:null,revision_n:null});
    const row={...base,knowledge_context:knowledge,provenance:{...base.provenance,surface_id:'build',surface_instance_id:'build-instance',
      primary_work:{...ref('build','source-one','2'),content_sha256:SHA},supporting_work:[ref('dmb_build_source_visibility_v1','internal','1'),ref('dmb_build_graph_binding_v1',a.native_world_id,String(a.binding_version)),ref('world_graph_revision',a.native_world_id,a.graph_revision)]}};
    vi.mocked(getWorldAgentConversationHistory).mockResolvedValue({...history(),schema:'dmb_agent_conversation_history_v2',turns:[row]});
    vi.mocked(getAgentRelatedPage).mockResolvedValue({schema:'dmb_agent_related_page_read_v1',world_id:WORLD,turn_id:row.turn_id,read_id:readId,page,markdown:body});
    render(<Harness initial='build'/>);
    fireEvent.click(await screen.findByRole('button',{name:'Open',exact:true}));
    await screen.findAllByText(base.assistant_text!);
    expect(getAgentRelatedPage).not.toHaveBeenCalled();
    const ordinary=document.querySelector('.world-plan-agent-conversation__message--assistant > .source-citation-evidence')!;
    const marker=ordinary.querySelector('button')!;expect(marker.textContent).toBe('1');
    expect(marker.getAttribute('aria-label')).toBe('Read Households · saved revision 9');
    fireEvent.click(marker);
    await screen.findByText(body);
    expect(getAgentRelatedPage).toHaveBeenCalledWith(WORLD,row.turn_id,readId);
    expect(postWorldBuildAgentTurn).not.toHaveBeenCalled();
  });

  it("submits exact Build source pins through the same World conversation and keeps its answer on Plan", async () => {
    let current = history();
    vi.mocked(getWorldAgentConversationHistory).mockImplementation(async () => current);
    vi.mocked(postWorldBuildAgentTurn).mockImplementation(async (request: WorldBuildAgentTurnRequestV1) => {
      const answerTurn = { ...turn("plan", 1, "Frank and Sara operate the Rocky Talkie."),
        turn_id: request.turn_id, user_text: request.message,
        provenance: { ...turn("plan", 1, "").provenance, surface_id: "build", surface_instance_id: "build-instance",
          primary_work: { resolution: "resolved" as const, kind: "build", object_id: "source-one", revision: "2",
            content_sha256: SHA, object_revision: null, work_revision_id: null, revision_n: null } } };
      current = history([answerTurn]);
      const response = playResponse({ graph_request: { mode: "world" } } as WorldPlayAgentTurnRequestV1);
      return { ...response, client_thread_id: request.client_thread_id, turn_id: request.turn_id,
        surface: { ...response.surface, surface_id: "build", instance_id: "build-instance" },
        primary_work: { ...response.primary_work, kind: "build", object_id: "source-one", expected_revision: 2, revision_used: 2 },
        client_work_state_reported: "saved_dirty", graph: { ...response.graph, status: "ready", world_id: "native-world-one",
          campaign_id: "", scope_mode: "world", revision_id: "native-revision-one", focus: { kind: "none" } },
        conversation: { ...response.conversation, client_thread_id: request.client_thread_id, turn_id: request.turn_id } };
    });
    render(<Harness initial="build" />);
    fireEvent.click(await screen.findByRole("button", { name: "Open" }));
    await waitFor(() => expect(screen.getByLabelText("Message DungeonBuddy")).toBeEnabled());
    fireEvent.change(screen.getByLabelText("Message DungeonBuddy"), { target: { value: "Who operates the radio?" } });
    fireEvent.click(screen.getByRole("button", { name: "Send message" }));
    await waitFor(() => expect(postWorldBuildAgentTurn).toHaveBeenCalledTimes(1));
    const request = vi.mocked(postWorldBuildAgentTurn).mock.calls[0]![0];
    expect(request.primary_work).toEqual({ kind: "build", object_id: "source-one", expected_revision: 2, expected_content_sha256: SHA });
    expect(request.client_work_state).toBe("saved_dirty");
    expect(JSON.stringify(request)).not.toContain("markdown");
    expect(postWorldPlanAgentTurn).not.toHaveBeenCalled();
    expect(postWorldPlayAgentTurn).not.toHaveBeenCalled();
    await screen.findByText("Frank and Sara operate the Rocky Talkie.");
    fireEvent.click(screen.getByRole("button", { name: "Switch surface" }));
    await screen.findByText("Frank and Sara operate the Rocky Talkie.");
  });

  it.each([
    [409, "build_source_unavailable"], [403, "graph_auth_required"],
  ] as const)("restores the Build question after refusal before dispatch: %s %s", async (status, code) => {
    vi.mocked(postWorldBuildAgentTurn).mockRejectedValue(new LiveApiError("Saved source unavailable", status, { code }));
    render(<Harness initial="build" />);
    fireEvent.click(await screen.findByRole("button", { name: "Open" }));
    await waitFor(() => expect(screen.getByLabelText("Message DungeonBuddy")).toBeEnabled());
    fireEvent.change(screen.getByLabelText("Message DungeonBuddy"), { target: { value: "Who operates the radio?" } });
    fireEvent.click(screen.getByRole("button", { name: "Send message" }));
    await waitFor(() => expect(postWorldBuildAgentTurn).toHaveBeenCalledTimes(1));
    await waitFor(() => expect(screen.getByLabelText("Message DungeonBuddy")).toHaveValue("Who operates the radio?"));
    await waitFor(() => expect(screen.getByLabelText("Message DungeonBuddy")).toBeEnabled());
    expect(screen.queryByLabelText("Submitted message")).not.toBeInTheDocument();
    expect(postWorldBuildAgentTurn).toHaveBeenCalledTimes(1);
    expect(postWorldPlayAgentTurn).not.toHaveBeenCalled();
  });

  it.each(["build", "play"] as const)("opens the closed %s options from the authorization recovery button", async surface => {
    vi.mocked(postWorldBuildAgentTurn).mockRejectedValue(new LiveApiError("Unauthorized", 401));
    vi.mocked(postWorldPlayAgentTurn).mockRejectedValue(new LiveApiError("Unauthorized", 401));
    render(<Harness initial={surface} buildBridge={surface==='build'?retryBridge():undefined} />);
    fireEvent.click(await screen.findByRole("button", {name: "Open"}));
    const input = await screen.findByLabelText("Message DungeonBuddy");
    await waitFor(() => expect(input).toBeEnabled());
    const options = screen.getByTitle("Conversation options").closest("details")!;
    expect(options).not.toHaveAttribute("open");
    fireEvent.change(input, {target: {value: "Help with this page"}});
    fireEvent.click(screen.getByRole("button", {name: "Send message"}));
    fireEvent.click(await screen.findByRole("button", {name: "Open Settings"}));
    expect(options).toHaveAttribute("open");
    await waitFor(() => expect(screen.getByRole("button", {name: "Connect local session"})).toBeVisible());
    fireEvent.click(screen.getByRole("button", {name: "Close connection settings"}));
    expect(screen.queryByRole("button", {name: "Connect local session"})).not.toBeInTheDocument();
  });

  it("keeps Build tools and keyboard help in Options with native composer sizing", async () => {
    render(<Harness initial="build" />);
    fireEvent.click(await screen.findByRole("button", { name: "Open" }));
    const input = await screen.findByLabelText("Message DungeonBuddy");
    await waitFor(() => expect(input).toBeEnabled());
    expect(input).toHaveAttribute("rows", "1");
    expect(input.style.height).toBe("");
    fireEvent.change(input, { target: { value: "First line\nSecond line\nThird line" } });
    expect(input).toHaveValue("First line\nSecond line\nThird line");
    fireEvent.change(input, { target: { value: "" } });
    expect(input).toHaveValue("");
    const options = screen.getByTitle("Conversation options").closest("details")!;
    expect(options).toContainElement(screen.getByLabelText("Agent tools and access"));
    fireEvent.click(screen.getByTitle("Conversation options"));
    expect(within(options).getByText("World Graph and sources")).toBeVisible();
    expect(within(options).getByText("Generate images")).toBeVisible();
    expect(within(options).getByText("Open an editable saved page first.")).toBeVisible();
    expect(within(options).getByText("Enter to send · Shift+Enter for a new line.")).toBeVisible();
    expect(screen.queryByText("Conversation", { selector: "strong" })).not.toBeInTheDocument();
  });

  it("puts an unanswered Build failure beside its message and recovery in Options without resending", async () => {
    vi.mocked(postWorldBuildAgentTurn).mockRejectedValue(new LiveApiError("The Plan Graph provider did not return a durably acknowledged answer.", 503, { code: "plan_context_delivery_failure" }));
    render(<Harness initial="build" />);
    fireEvent.click(await screen.findByRole("button", { name: "Open" }));
    const input = await screen.findByLabelText("Message DungeonBuddy");
    await waitFor(() => expect(input).toBeEnabled());
    fireEvent.change(input, { target: { value: "Do you have image tools?" } });
    fireEvent.click(screen.getByRole("button", { name: "Send message" }));
    const failure = await screen.findByText(/Buddy couldn’t finish this reply/);
    expect(failure.closest("article")).toHaveTextContent("Do you have image tools?");
    const options = screen.getByTitle("Conversation options").closest("details")!;
    expect(options).toContainElement(screen.getByLabelText("Saved turn recovery"));
    expect(postWorldBuildAgentTurn).toHaveBeenCalledTimes(1);
    expect(screen.getByRole("button", { name: "Send message" })).toBeDisabled();
  });

  it.each(["correct", "wrong_hash", "wrong_key", "removed", "removed_wrong_hash", "replaced"] as const)("recovers Build using the durable correlation and exact source basis: %s", async scenario => {
    let current: WorldAgentConversationHistoryResponse = history();
    let submitted!: WorldBuildAgentTurnRequestV1;
    vi.mocked(getWorldAgentConversationHistory).mockImplementation(async () => current);
    vi.mocked(postWorldBuildAgentTurn).mockImplementation(async request => {
      submitted = request;
      throw new Error("Connection lost after submit");
    });
    render(<Harness initial="build" />);
    fireEvent.click(await screen.findByRole("button", { name: "Open" }));
    await waitFor(() => expect(screen.getByLabelText("Message DungeonBuddy")).toBeEnabled());
    fireEvent.change(screen.getByLabelText("Message DungeonBuddy"), { target: { value: "Who operates the radio?" } });
    fireEvent.click(screen.getByRole("button", { name: "Send message" }));
    await waitFor(() => expect(postWorldBuildAgentTurn).toHaveBeenCalledTimes(1));
    await screen.findByText(/Connection lost after submit/);
    const storedKey = 'dmb:world-play-pending-turn:v1:' + WORLD;
    const replacement = JSON.stringify({ replacement: 'newer request bytes must survive' });
    fireEvent.change(screen.getByLabelText("Message DungeonBuddy"), { target: { value: "Keep my next question" } });
    if (scenario === "removed" || scenario === "removed_wrong_hash") localStorage.removeItem(storedKey);
    if (scenario === "replaced") localStorage.setItem(storedKey, replacement);
    current = { ...history(), schema: "dmb_agent_conversation_history_v3", turns: [{
      ...turn("plan", 1, "Frank and Sara operate the Rocky Talkie."),
      turn_id: "00000000-0000-4000-8000-000000000055", user_text: submitted.message,
      idempotency_key: scenario === "wrong_key" ? "00000000-0000-4000-8000-000000000099" : await expectedHistoryCorrelationKey(WORLD, submitted.turn_id),
      provenance: { ...turn("plan", 1, "").provenance, surface_id: "build", surface_instance_id: "build-instance",
        primary_work: { resolution: "resolved", kind: "build", object_id: "source-one", revision: "2",
          content_sha256: (scenario === "wrong_hash" || scenario === "removed_wrong_hash") ? "b".repeat(64) : SHA,
          object_revision: null, work_revision_id: null, revision_n: null } },
    }] };
    const proposalReads = vi.mocked(listBuildProposals).mock.calls.length;
    fireEvent.click(screen.getByRole("button", { name: "Refresh shared history fixture" }));
    await screen.findByText("Frank and Sara operate the Rocky Talkie.");
    if (scenario === "correct" || scenario === "removed") {
      await waitFor(() => expect(screen.getByRole("button", { name: "Send message" })).toBeEnabled());
      await waitFor(() => expect(vi.mocked(listBuildProposals).mock.calls.length).toBeGreaterThan(proposalReads));
      expect(localStorage.getItem(storedKey)).toBeNull();
      expect(screen.queryByRole("button", { name: "Retry", exact: true })).not.toBeInTheDocument();
    } else {
      expect(vi.mocked(listBuildProposals).mock.calls.length).toBe(proposalReads);
      expect(screen.getByRole("button", { name: "Send message" })).toBeDisabled();
    }
    expect(screen.getByLabelText("Message DungeonBuddy")).toHaveValue("Keep my next question");
    if (scenario === "replaced") expect(localStorage.getItem(storedKey)).toBe(replacement);
    expect(postWorldBuildAgentTurn).toHaveBeenCalledTimes(1);
  });

  it("keeps Build composer closed to unverified or unsaved source context", async () => {
    render(<Harness initial="build" admitted={false} />);
    fireEvent.click(await screen.findByRole("button", { name: "Open" }));
    expect(await screen.findByLabelText("Message DungeonBuddy")).toBeDisabled();
    expect(postWorldBuildAgentTurn).not.toHaveBeenCalled();
  });

  it("explains empty Build, enables only the selected saved source, and clears its context on return to empty", async () => {
    const source = buildSourceSnapshot();
    vi.mocked(listWorkspaceDocuments).mockResolvedValue({
      schema_version: "dmb_workspace_document_registry_v1",
      records: [source.record],
    });
    vi.mocked(getWorkspaceDocumentSnapshot).mockResolvedValue(source);
    window.history.pushState({}, "", `/build?world=${WORLD}`);

    render(<RealBuildPageHarness />);
    const sourceSelector = await screen.findByRole("combobox", { name: "Worldbuilding source" });
    await waitFor(() => expect(sourceSelector).toBeEnabled());
    fireEvent.click(await screen.findByRole("button", { name: "Open" }));

    const emptyComposer = await screen.findByLabelText("Message DungeonBuddy");
    expect(emptyComposer).toBeDisabled();
    expect(emptyComposer.getAttribute("aria-describedby")).toContain("world-plan-agent-build-source-required");
    expect(screen.getByText(/Buddy needs a saved source before you can ask about your lore/)).toBeVisible();
    expect(screen.getByRole("button", { name: "Send message" })).toBeDisabled();
    fireEvent.click(screen.getByRole("button", { name: "Choose a source" }));
    expect(sourceSelector).toHaveFocus();
    fireEvent.click(screen.getByRole("button", { name: "Open source actions" }));
    expect(screen.getByText("Source actions", { selector: "summary" }).parentElement).toHaveAttribute("open");
    fireEvent.submit(emptyComposer.closest("form")!);
    expect(postWorldBuildAgentTurn).not.toHaveBeenCalled();
    expect(createWorkspaceDocument).not.toHaveBeenCalled();

    fireEvent.change(sourceSelector, { target: { value: BUILD_SOURCE_ID } });
    await screen.findByTestId("build-markdown-editor");
    openConversationOptions();
    fireEvent.click(screen.getByRole("button", { name: "Show context" }));
    expect(await screen.findByText(/Buddy uses the saved source “City of Mirathorn”/)).toBeVisible();
    const savedComposer = screen.getByLabelText("Message DungeonBuddy");
    await waitFor(() => expect(savedComposer).toBeEnabled());

    window.history.pushState({}, "", `/build?world=${WORLD}`);
    fireEvent(window, new PopStateEvent("popstate"));
    await screen.findByTestId("build-surface-empty");
    openConversationOptions();
    fireEvent.click(screen.getByRole("button", { name: "Show context" }));
    expect(await screen.findByText(/Buddy needs a saved source before you can ask about your lore/)).toBeVisible();
    expect(screen.queryByText(/Buddy uses the saved source “City of Mirathorn”/)).not.toBeInTheDocument();
    expect(screen.getByLabelText("Message DungeonBuddy")).toBeDisabled();
    expect(screen.getByRole("button", { name: "Send message" })).toBeDisabled();
    fireEvent.submit(screen.getByLabelText("Message DungeonBuddy").closest("form")!);
    expect(postWorldBuildAgentTurn).not.toHaveBeenCalled();
    expect(createWorkspaceDocument).not.toHaveBeenCalled();
  });

  it.each(["failed", "interrupted", "wrong_key", "wrong_basis", "wrong_conversation", "duplicate", "changed_envelope", "newer_pending"] as const)("reconciles terminal Graph Ask safely: %s", async (scenario) => {
    const terminal = scenario === "failed" ? "failed" : "interrupted";
    let current: WorldAgentConversationHistoryResponse = history();
    let request!: WorldPlanAgentTurnRequestV1;
    vi.mocked(getWorldAgentConversationHistory).mockImplementation(async () => current);
    vi.mocked(postWorldPlanAgentTurn).mockImplementation(async (value) => {
      request = value;
      throw new LiveApiError("Provider outcome uncertain", 503, { code: "provider_lifecycle_unavailable" });
    });
    render(<Harness />);
    fireEvent.click(await screen.findByRole("button", { name: "Open" }));
    const composer = await screen.findByLabelText("Message DungeonBuddy");
    await waitFor(() => expect(screen.getByRole("button", { name: "New conversation" })).toBeEnabled());
    fireEvent.change(composer, { target: { value: "Tell me all about Mirathorn." } });
    fireEvent.click(screen.getByRole("button", { name: "Send message" }));
    await waitFor(() => expect(postWorldPlanAgentTurn).toHaveBeenCalledTimes(1));
    await waitFor(() => expect(composer).toHaveValue(request.message));
    await waitFor(() => expect(screen.getByRole("button", { name: "New conversation" })).toBeDisabled());
    const key = Object.keys(localStorage).find(key => key.startsWith("dmb:world-plan-pending-ask:v1:"))!;
    const envelope = localStorage.getItem(key);
    const context = await planGraphContext("plan_only_graph_unused", { request, completion: false, execution: {
      schema: "dmb_agent_plan_world_graph_execution_projection_v1", claimability: "blocked_unknown_or_sent",
      authorization_state: "outcome_unknown", automatic_redispatch: false,
    } });
    const row = { ...turn("plan", 1, ""), turn_id: "00000000-0000-4000-8000-000000000090",
      idempotency_key: await expectedHistoryCorrelationKey(WORLD, request.turn_id),
      user_text: request.message, assistant_text: null, lifecycle_status: "running" as const,
      provenance: { ...turn("plan", 1, "").provenance, primary_work: {
        resolution: "resolved" as const, kind: "plan", object_id: "plan-one", revision: "7",
        object_revision: 7, revision_n: 2, work_revision_id: WORK_REVISION, content_sha256: SHA,
      } }, plan_context: context };
    current = { ...history(), schema: "dmb_agent_conversation_history_v3", turns: [row] };
    fireEvent(window, new Event("online"));
    await waitFor(() => expect(screen.getByRole("region", { name: "World conversation transcript" }).querySelector(".world-plan-agent-conversation__turn--pending")).not.toBeNull());
    await waitFor(() => expect(screen.queryByRole("article", { name: "Submitted message" })).not.toBeInTheDocument());
    expect(screen.getByRole("button", { name: "New conversation" })).toBeDisabled();
    // A newer draft must survive reconciliation of the older request.
    fireEvent.change(composer, { target: { value: "What about Sara?" } });
    const terminalRow = { ...row, lifecycle_status: terminal };
    if (scenario === "wrong_key") terminalRow.idempotency_key = "00000000-0000-4000-8000-000000000091";
    if (scenario === "wrong_basis") terminalRow.provenance.primary_work.content_sha256 = "b".repeat(64);
    let rows = [terminalRow];
    if (scenario === "duplicate") rows = [terminalRow, { ...terminalRow, turn_id: "00000000-0000-4000-8000-000000000092", sequence: 2 }];
    if (scenario === "changed_envelope") {
      const replacement = JSON.parse(envelope!);
      replacement.request.message = "A newer request with different intent";
      localStorage.setItem(key, JSON.stringify(replacement));
    }
    if (scenario === "newer_pending") await act(async () => { fireEvent.click(screen.getByRole("button", { name: "Seed newer pending request" })); });
    current = { ...current, turns: rows,
      ...(scenario === "wrong_conversation" ? { conversation_id: "other-conversation", active_conversation_id: "other-conversation", pointer_revision: 2 } : {}) };
    fireEvent.click(screen.getByRole("button", { name: "Refresh shared history fixture" }));
    if (scenario !== "failed" && scenario !== "interrupted") {
      if (scenario === "wrong_basis") await screen.findByText(/World conversation response did not match/);
      else await screen.findAllByText("This reply stopped before it finished. Your Plan was not changed.");
      expect(screen.getByRole("button", { name: "New conversation" })).toBeDisabled();
      expect(postWorldPlanAgentTurn).toHaveBeenCalledTimes(1);
      expect(localStorage.getItem(key)).not.toBeNull();
      return;
    }
    await waitFor(() => expect(screen.getByRole("button", { name: "New conversation" })).toBeEnabled());
    expect(composer).toHaveValue("What about Sara?");
    await waitFor(() => expect(screen.getByRole("button", { name: "Send message" })).toBeEnabled());
    expect(screen.getAllByText(request.message)).toHaveLength(1);
    expect(localStorage.getItem(key)).toBe(envelope);
    expect(postWorldPlanAgentTurn).toHaveBeenCalledTimes(1);
    expect(postWorldAgentNewConversation).not.toHaveBeenCalled();
  });

  it("keeps one transcript and restores unsent drafts to their original Plan or Run", async () => {
    render(<Harness />);
    fireEvent.click(await screen.findByRole("button", { name: "Open" }));
    const composer = await screen.findByLabelText("Message DungeonBuddy");
    await screen.findByText("Original Plan answer");
    fireEvent.change(composer, { target: { value: "Rewrite this Plan scene" } });
    fireEvent.click(screen.getByRole("button", { name: "Switch surface" }));
    expect(await screen.findByTestId("world-agent-conversation-host")).toBeInTheDocument();
    openConversationOptions();
    expect(screen.getByRole("button",{name:"Show Test World · Play · The Crossing · West Gate"})).toBeInTheDocument();
    expect(await screen.findByLabelText("Message DungeonBuddy")).toHaveValue("");
    expect(screen.getAllByRole("textbox")).toHaveLength(1);
    expect(screen.getByText("Original Plan answer")).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("Message DungeonBuddy"), { target: { value: "What happens at the gate?" } });
    fireEvent.click(screen.getByRole("button", { name: "Switch surface" }));
    expect(await screen.findByLabelText("Message DungeonBuddy")).toHaveValue("Rewrite this Plan scene");
    fireEvent.click(screen.getByRole("button", { name: "Switch surface" }));
    expect(await screen.findByLabelText("Message DungeonBuddy")).toHaveValue("What happens at the gate?");
    expect(postWorldPlayAgentTurn).not.toHaveBeenCalled();
  });

  it.each(['exact', 'exact-removed', 'other-edition', 'other-scene', 'failed', 'interrupted'] as const)("reconciles an uncertain Play turn after switching to Plan only for its exact basis: %s", async mode => {
    let phase: "initial" | "pending" | "completed" = "initial";
    let playTurnId = "";
    let submitted: WorldPlayAgentTurnRequestV1 | null = null;
    function contextForHistory() {
      const r = structuredClone(submitted!);
      if (mode === 'other-edition') r.primary_work.play_content_basis = { edition_revision: 1,
        edition_revision_id: '00000000-0000-4000-8000-000000000044', content_sha256: 'b'.repeat(64) };
      if (mode === 'other-scene') r.play_target.scene_id = 'scene:other';
      return nativePlayContextFixture(r, "Recovered Play answer");
    }
    vi.mocked(getWorldAgentConversationHistory).mockImplementation(async () => ({ ...history(), schema: "dmb_agent_conversation_history_v2", turns: [
      turn("plan", 1, "Original Plan answer"),
      ...(phase === "initial" ? [] : [{ ...turn("play", 2, "Recovered Play answer"),
        turn_id: playTurnId, user_text: "What happens next?", assistant_text: phase === "pending" || mode === 'failed' || mode === 'interrupted' ? null : "Recovered Play answer",
        lifecycle_status: phase === "pending" ? "running" as const : mode === 'failed' || mode === 'interrupted' ? mode : "completed" as const,
        ...(submitted ? { play_context: { ...contextForHistory(), delivery_replay: true,
          ...(phase === "pending" || mode === 'failed' || mode === 'interrupted' ? { completion: null,
            execution: { schema: 'dmb_agent_plan_world_graph_execution_projection_v1' as const,
              claimability: 'safe_to_reclaim_without_dispatch' as const, authorization_state: 'none' as const, automatic_redispatch: false as const } } : {}) }, provenance: nativePlayProvenanceFixture(contextForHistory()) } : {}) }]),
    ] }));
    vi.mocked(postWorldPlayAgentTurn).mockImplementation(async (request) => {
      submitted = request;
      playTurnId = request.turn_id;
      phase = "pending";
      throw new Error("Connection lost after submit");
    });
    const view = render(<Harness initial="play" />);
    fireEvent.click(await screen.findByRole("button", { name: "Open" }));
    const composer = await screen.findByLabelText("Message DungeonBuddy");
    await waitFor(() => expect(composer).toBeEnabled());
    fireEvent.change(composer, { target: { value: "What happens next?" } });
    fireEvent.click(screen.getByRole("button", { name: "Send message" }));
    await waitFor(() => expect(screen.getByText(/Connection lost after submit/)).toBeInTheDocument());
    view.unmount();
    render(<Harness initial="plan" />);
    fireEvent.click(await screen.findByRole("button", { name: "Open" }));
    await waitFor(() => expect(screen.getByLabelText("Message DungeonBuddy")).toBeEnabled());
    if (mode === "exact-removed") {
      fireEvent.change(screen.getByLabelText("Message DungeonBuddy"), { target: { value: "Keep the next Plan question" } });
      localStorage.removeItem("dmb:world-play-pending-turn:v1:" + WORLD);
    }
    phase = "completed";
    if (mode === 'failed' || mode === 'interrupted') {
      await waitFor(() => expect(screen.getByLabelText("Message DungeonBuddy")).toBeEnabled(), { timeout: 7000 });
      expect(screen.queryByText("Recovered Play answer")).not.toBeInTheDocument();
      await waitFor(() => expect(window.localStorage.getItem('dmb:world-play-pending-turn:v1:' + WORLD)).toBeNull(), { timeout: 7000 });
    } else if (mode === 'exact' || mode === 'exact-removed') {
      await waitFor(() => expect(screen.getByText("Recovered Play answer")).toBeInTheDocument(), { timeout: 7000 });
      await waitFor(() => expect(screen.getByLabelText("Message DungeonBuddy")).toBeEnabled());
      expect(screen.queryByText(/Connection lost after submit/)).not.toBeInTheDocument();
      if (mode === "exact-removed") {
        await waitFor(() => expect(screen.getByRole("button", { name: "Send message" })).toBeEnabled());
        expect(screen.getByLabelText("Message DungeonBuddy")).toHaveValue("Keep the next Plan question");
      }
    } else {
      await waitFor(() => expect(screen.getByText("Recovered Play answer")).toBeInTheDocument(), { timeout: 7000 });
      expect(screen.getByLabelText("Message DungeonBuddy")).toBeEnabled();
      expect(window.localStorage.getItem('dmb:world-play-pending-turn:v1:' + WORLD)).not.toBeNull();
    }
    expect(postWorldPlayAgentTurn).toHaveBeenCalledTimes(1);
  });

  it("keeps an unaccepted Play request available for explicit exact-ID retry from Plan", async () => {
    let firstRequest: WorldPlayAgentTurnRequestV1 | null = null;
    vi.mocked(postWorldPlayAgentTurn).mockImplementation(async (request) => {
      if (!firstRequest) {
        firstRequest = request;
        throw new Error("Connection closed before admission");
      }
      vi.mocked(getWorldAgentConversationHistory).mockResolvedValue(history([
        turn("plan", 1, "Original Plan answer"), { ...turn("play", 2, "Retried Play answer"), turn_id: request.turn_id },
      ]));
      return playResponse(request);
    });
    const view = render(<Harness initial="play" />);
    fireEvent.click(await screen.findByRole("button", { name: "Open" }));
    const composer = await screen.findByLabelText("Message DungeonBuddy");
    await waitFor(() => expect(composer).toBeEnabled());
    fireEvent.change(composer, { target: { value: "What happens at the gate?" } });
    fireEvent.click(screen.getByRole("button", { name: "Send message" }));
    await screen.findByText(/Connection closed before admission/);
    expect(postWorldPlayAgentTurn).toHaveBeenCalledTimes(1);
    const storageKey = `dmb:world-play-pending-turn:v1:${encodeURIComponent(WORLD)}`;
    const frozen = window.localStorage.getItem(storageKey);
    expect(JSON.parse(frozen ?? "null").request.graph_request).toEqual({ mode: "world", world_id: WORLD,
      campaign_id: null, revision_pin: null, focus: { kind: "none", session_id: null, campaign_id: null } });
    expect(JSON.parse(frozen ?? "null").request.play_target).toEqual({ beat_id: "beat:crossing",
      scene_id: "scene:west-gate", marker_grammar_version: "v2" });
    view.unmount();
    render(<Harness initial="plan" />);
    fireEvent.click(await screen.findByRole("button", { name: "Open" }));
    await waitFor(() => expect(screen.getByLabelText("Message DungeonBuddy")).toBeEnabled());
    expect(postWorldPlayAgentTurn).toHaveBeenCalledTimes(1);
    expect(window.localStorage.getItem(storageKey)).toBe(frozen);
    fireEvent.change(screen.getByLabelText("Message DungeonBuddy"), { target: { value: "My next draft" } });
    expect(screen.getByRole("button", { name: "Send message" })).toBeDisabled();
    fireEvent.click(screen.getByRole("button", { name: "Retry", exact: true }));
    await waitFor(() => expect(postWorldPlayAgentTurn).toHaveBeenCalledTimes(2));
    expect(vi.mocked(postWorldPlayAgentTurn).mock.calls[1]?.[0]).toEqual(firstRequest);
    expect(JSON.stringify(vi.mocked(postWorldPlayAgentTurn).mock.calls[1]?.[0])).toBe(JSON.stringify(firstRequest));
    await waitFor(() => expect(screen.getByText("Retried Play answer")).toBeInTheDocument());
    await waitFor(() => expect(screen.getByLabelText("Message DungeonBuddy")).toBeEnabled());
    expect(screen.queryByRole("button", { name: "Retry exact saved turn" })).not.toBeInTheDocument();
    expect(screen.getByLabelText("Message DungeonBuddy")).toHaveValue("My next draft");
  });

  it.each([0, 3])("recovers the exact saved session edition basis %s without substituting the current head", async edition => {
    const basis = { edition_revision: edition, edition_revision_id: edition ? "00000000-0000-4000-8000-000000000099" : null, content_sha256: SHA };
    const request: WorldPlayAgentTurnRequestV1 = {
      schema: "dmb_agent_turn_request_v1", client_thread_id: "00000000-0000-4000-8000-000000000021", turn_id: "00000000-0000-4000-8000-000000000022",
      surface: { surface_id: "play", instance_id: "play-instance" }, owner_scope: { kind: "world", world_id: WORLD },
      primary_work: { kind: "run", object_id: RUN, expected_revision: 3, play_content_basis: basis },
      play_target: { beat_id: "beat:crossing", scene_id: "scene:west-gate", marker_grammar_version: "v2" },
      client_work_state: "saved_clean", graph_request: { mode: "world", world_id: WORLD, campaign_id: null,
        revision_pin: null, focus: { kind: "none", session_id: null, campaign_id: null } }, graph_selection: null, message: "Saved edition question",
    };
    const key = `dmb:world-play-pending-turn:v1:${encodeURIComponent(WORLD)}`;
    window.localStorage.setItem(key, JSON.stringify({ schema: "dmb_world_play_pending_turn_v1", request }));
    vi.mocked(postWorldPlayAgentTurn).mockImplementation(async posted => playResponse(posted));
    render(<Harness initial="play" />);
    fireEvent.click(await screen.findByRole("button", { name: "Open" }));
    openConversationOptions();
    fireEvent.click(await screen.findByRole("button", { name: "Retry exact saved turn" }));
    await waitFor(() => expect(postWorldPlayAgentTurn).toHaveBeenCalledWith(request));
    expect(vi.mocked(postWorldPlayAgentTurn).mock.calls[0][0].primary_work.play_content_basis).toEqual(basis);
  });

  it("retains and refuses a retired graphless Play request without dispatch", async () => {
    const request = {
      schema: "dmb_agent_turn_request_v1",
      client_thread_id: "00000000-0000-4000-8000-000000000021",
      turn_id: "00000000-0000-4000-8000-000000000022",
      surface: { surface_id: "play", instance_id: "play-instance" },
      owner_scope: { kind: "world", world_id: WORLD },
      primary_work: { kind: "run", object_id: RUN, expected_revision: 3 },
      client_work_state: "saved_clean", graph_request: { mode: "none" },
      graph_selection: null, message: "Old saved Play question",
    };
    const storageKey = `dmb:world-play-pending-turn:v1:${encodeURIComponent(WORLD)}`;
    const serialized = JSON.stringify({ schema: "dmb_world_play_pending_turn_v1", request });
    window.localStorage.setItem(storageKey, serialized);
    vi.mocked(postWorldPlayAgentTurn).mockImplementation(async (posted) => playResponse(posted));
    render(<Harness initial="play" />);
    fireEvent.click(await screen.findByRole("button", { name: "Open" }));
    await screen.findByText(/saved Play request is malformed/i);
    expect(window.localStorage.getItem(storageKey)).toBe(serialized);
    expect(screen.queryByRole("button", { name: "Retry exact saved turn" })).not.toBeInTheDocument();
    expect(postWorldPlayAgentTurn).not.toHaveBeenCalled();
  });

  it("accepts a replayed native Graph receipt for a saved managed World Play request", async () => {
    const request: WorldPlayAgentTurnRequestV1 = {
      schema: "dmb_agent_turn_request_v1",
      client_thread_id: "00000000-0000-4000-8000-000000000031",
      turn_id: "00000000-0000-4000-8000-000000000032",
      surface: { surface_id: "play", instance_id: "play-instance" },
      owner_scope: { kind: "world", world_id: WORLD },
      primary_work: { kind: "run", object_id: RUN, expected_revision: 3, play_content_basis: { edition_revision: 0, edition_revision_id: null, content_sha256: SHA } },
      play_target: { beat_id: "beat:one", scene_id: "scene:gate", marker_grammar_version: "v2" },
      client_work_state: "saved_clean",
      graph_request: { mode: "world", world_id: WORLD, campaign_id: null,
        revision_pin: null, focus: { kind: "none", session_id: null, campaign_id: null } },
      graph_selection: null, message: "Saved Graph question",
    };
    const storageKey = `dmb:world-play-pending-turn:v1:${encodeURIComponent(WORLD)}`;
    window.localStorage.setItem(storageKey, JSON.stringify({ schema: "dmb_world_play_pending_turn_v1", request }));
    vi.mocked(postWorldPlayAgentTurn).mockImplementation(async (posted) => ({
      ...playResponse(posted),
      graph: { ...playResponse(posted).graph, status: "replayed" as const },
    }));
    render(<Harness initial="play" />);
    fireEvent.click(await screen.findByRole("button", { name: "Open" }));
    openConversationOptions();
    fireEvent.click(await screen.findByRole("button", { name: "Retry exact saved turn" }));
    await waitFor(() => expect(postWorldPlayAgentTurn).toHaveBeenCalledWith(request));
    await waitFor(() => expect(window.localStorage.getItem(storageKey)).toBeNull());
    expect(playResponse(request).graph.world_id).toBe("native-world-one");
    expect(request.owner_scope.world_id).toBe(WORLD);
  });

  it("keeps Graph unavailable as a saved Play failure without a graphless repost", async () => {
    vi.mocked(postWorldPlayAgentTurn).mockRejectedValue(
      new LiveApiError("Native World binding unavailable", 503, { code: "graph_unavailable" }),
    );
    render(<Harness initial="play" />);
    fireEvent.click(await screen.findByRole("button", { name: "Open" }));
    const composer = await screen.findByLabelText("Message DungeonBuddy");
    await waitFor(() => expect(composer).toBeEnabled());
    fireEvent.change(composer, { target: { value: "What does the Graph say?" } });
    fireEvent.click(screen.getByRole("button", { name: "Send message" }));
    await screen.findByText(/World Graph could not be resolved/);
    const posted = vi.mocked(postWorldPlayAgentTurn).mock.calls[0]?.[0];
    expect(posted?.graph_request.mode).toBe("world");
    expect(JSON.parse(window.localStorage.getItem(`dmb:world-play-pending-turn:v1:${encodeURIComponent(WORLD)}`) ?? "null")
      .request.graph_request).toEqual(posted?.graph_request);
    expect(postWorldPlayAgentTurn).toHaveBeenCalledTimes(1);
    expect(screen.queryByText("Original Play answer")).not.toBeInTheDocument();
  });

  it("rejects an unavailable Graph receipt even if a response contains answer text", async () => {
    vi.mocked(postWorldPlayAgentTurn).mockImplementation(async (request) => ({
      ...playResponse(request), graph: { ...playResponse(request).graph, status: "unavailable" as const },
    }));
    render(<Harness initial="play" />);
    fireEvent.click(await screen.findByRole("button", { name: "Open" }));
    const composer = await screen.findByLabelText("Message DungeonBuddy");
    await waitFor(() => expect(composer).toBeEnabled());
    fireEvent.change(composer, { target: { value: "What happens now?" } });
    fireEvent.click(screen.getByRole("button", { name: "Send message" }));
    await screen.findByText(/reply did not match the saved request/);
    expect(screen.queryByText("Original Play answer")).not.toBeInTheDocument();
    expect(postWorldPlayAgentTurn).toHaveBeenCalledTimes(1);
    expect(window.localStorage.getItem(`dmb:world-play-pending-turn:v1:${encodeURIComponent(WORLD)}`)).not.toBeNull();
  });

  it("does not expose a saved Play request after the selected World changes", async () => {
    vi.mocked(postWorldPlayAgentTurn).mockRejectedValue(new Error("Connection closed before admission"));
    render(<Harness initial="play" />);
    fireEvent.click(await screen.findByRole("button", { name: "Open" }));
    const composer = await screen.findByLabelText("Message DungeonBuddy");
    await waitFor(() => expect(composer).toBeEnabled());
    fireEvent.change(composer, { target: { value: "Question for World one" } });
    fireEvent.click(screen.getByRole("button", { name: "Send message" }));
    await screen.findByText(/Connection closed before admission/);
    const storageKey = `dmb:world-play-pending-turn:v1:${encodeURIComponent(WORLD)}`;
    const frozen = window.localStorage.getItem(storageKey);
    fireEvent.click(screen.getByRole("button", { name: "Switch World" }));
    await waitFor(() => expect(screen.queryByRole("button", { name: "Retry exact saved turn" })).not.toBeInTheDocument());
    expect(window.localStorage.getItem(storageKey)).toBe(frozen);
    expect(postWorldPlayAgentTurn).toHaveBeenCalledTimes(1);
  });

  it.each([
    [401, "local_session_required"], [403, "world_owner_unverified"],
  ])("releases a Play draft after a definite pre-dispatch refusal %s", async (status, code) => {
    vi.mocked(postWorldPlayAgentTurn).mockRejectedValue(new LiveApiError("Refused before provider dispatch", status, { code }));
    render(<Harness initial="play" />);
    fireEvent.click(await screen.findByRole("button", { name: "Open" }));
    const composer = await screen.findByLabelText("Message DungeonBuddy");
    await waitFor(() => expect(composer).toBeEnabled());
    fireEvent.change(composer, { target: { value: "Ask about this Run" } });
    fireEvent.click(screen.getByRole("button", { name: "Send message" }));
    await waitFor(() => expect(screen.getByLabelText("Message DungeonBuddy")).toHaveValue("Ask about this Run"));
    await waitFor(() => expect(screen.getByLabelText("Message DungeonBuddy")).toBeEnabled());
    expect(screen.queryByRole("button", { name: "Retry exact saved turn" })).not.toBeInTheDocument();
    expect(postWorldPlayAgentTurn).toHaveBeenCalledTimes(1);
  });

  it.each([false, true])("releases an unadmitted stale Build request and preserves a newer draft: %s", async newerDraft => {
    let reject!: (error: Error) => void;
    vi.mocked(postWorldBuildAgentTurn).mockImplementation(() => new Promise((_, fail) => { reject = fail; }));
    render(<Harness initial="build" />);
    fireEvent.click(await screen.findByRole("button", { name: "Open" }));
    const composer = await screen.findByLabelText("Message DungeonBuddy");
    await waitFor(() => expect(composer).toBeEnabled());
    fireEvent.change(composer, { target: { value: "Propose an Economy section" } });
    fireEvent.click(screen.getByRole("button", { name: "Send message" }));
    await waitFor(() => expect(postWorldBuildAgentTurn).toHaveBeenCalledTimes(1));
    if (newerDraft) fireEvent.change(composer, { target: { value: "My next thought" } });
    reject(new LiveApiError("The conversation changed since this request was prepared.", 409, { code: "build_editor_context_changed" }));
    await waitFor(() => expect(composer).toHaveValue(newerDraft ? "My next thought" : "Propose an Economy section"));
    await waitFor(() => expect(screen.getByRole("button", { name: "Send message" })).toBeEnabled());
    expect(localStorage.getItem('dmb:world-play-pending-turn:v1:' + WORLD)).toBeNull();
    expect(screen.queryByRole("button", { name: "Retry", exact: true })).not.toBeInTheDocument();
    expect(postWorldBuildAgentTurn).toHaveBeenCalledTimes(1);
  });

  it("shows authored context for a historical Play answer in the shared Build conversation", async () => {
    const row = turn("play", 1, "A useful arrival cue");
    row.provenance.primary_work.object_id = "00000000-0000-4000-8000-000000000070";
    row.provenance.supporting_work = [{ resolution: "resolved", kind: "dmb_play_runbook_v1",
      object_id: "00000000-0000-4000-8000-000000000071", revision: "9", content_sha256: SHA,
      object_revision: 9, work_revision_id: WORK_REVISION, revision_n: 2 }];
    vi.mocked(getWorldAgentConversationHistory).mockResolvedValue(history([row]));
    render(<Harness initial="build" />);
    fireEvent.click(await screen.findByRole("button", { name: "Open" }));
    await screen.findByText("A useful arrival cue");
    const trail = document.querySelector<HTMLDetailsElement>(".world-plan-agent-conversation__evidence-trail")!;
    fireEvent.click(trail.querySelector("summary")!);
    expect(within(trail).getByRole("region", { name: "Authored Play context" })).toBeInTheDocument();
    expect(within(trail).getByRole("button", { name: "Open pinned Runbook" })).toBeInTheDocument();
    expect(within(trail).queryByText("No Graph citations were saved with this answer.")).not.toBeInTheDocument();
  });

  it.each(["plan", "play", "build"] as const)("keeps %s draft editable while a prior request blocks sending", async initial => {
    render(<Harness initial={initial} />);
    fireEvent.click(await screen.findByRole("button", { name: "Open" }));
    const composer = await screen.findByLabelText("Message DungeonBuddy");
    await waitFor(() => expect(composer).toBeEnabled());
    expect(document.querySelector(".world-plan-agent-conversation__composer .buddy-readiness")).toBeNull();
    const readiness = document.querySelector(".buddy-readiness")!;
    expect(readiness).not.toBeVisible();
    fireEvent.click(screen.getByRole("button", { name: "Seed newer pending request" }));
    await screen.findByRole("button", { name: "Check saved request" });
    expect(composer).toBeEnabled();
    fireEvent.change(composer, { target: { value: "Keep this next thought" } });
    fireEvent.keyDown(composer, { key: "Enter", code: "Enter" });
    expect(composer).toHaveValue("Keep this next thought");
    expect(screen.getByRole("button", { name: "Send message" })).toBeDisabled();
    expect(postWorldPlanAgentTurn).not.toHaveBeenCalled();
    expect(postWorldPlayAgentTurn).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole("button", { name: "Check saved request" }));
    await waitFor(() => expect(readiness.querySelector("summary")).toBeVisible());
    expect(composer).toHaveValue("Keep this next thought");
  });

  it("prepends a requested Play history page without moving the reader or duplicating turns", async () => {
    const latest={...history([turn("play",2,"Middle answer"),turn("play",3,"Latest answer")]),next_before_sequence:2};
    vi.mocked(getWorldAgentConversationHistory).mockImplementation(async (_world,options)=>options?.beforeSequence
      ? history([turn("play",1,"Oldest answer"),turn("play",2,"Middle answer")]) : latest);
    render(<Harness initial="play"/>);
    fireEvent.click(await screen.findByRole("button",{name:"Open",exact:true}));
    await screen.findByText("Latest answer");
    expect(screen.getByText("Middle answer")).toBeVisible();
    const viewport=screen.getByRole("log",{name:"Conversation messages"});
    Object.defineProperties(viewport,{
      clientHeight:{configurable:true,value:120},
      scrollHeight:{configurable:true,get:()=>200+viewport.querySelectorAll("article").length*80},
    });
    viewport.scrollTop=40;fireEvent.scroll(viewport);
    const before=viewport.scrollHeight;
    fireEvent.click(screen.getByRole("button",{name:"Load earlier messages"}));
    await screen.findByText("Oldest answer");
    expect(viewport.scrollTop).toBe(40+viewport.scrollHeight-before);
    expect(screen.getAllByText("Middle answer")).toHaveLength(1);
    expect(screen.queryByRole("button",{name:"Load earlier messages"})).toBeNull();
    expect(getWorldAgentConversationHistory).toHaveBeenCalledWith(WORLD,expect.objectContaining({limit:50,beforeSequence:2}));
  });

  it("uses the compact dock, loaded exchanges and conversation options in Play", async () => {
    vi.mocked(getWorldAgentConversationHistory).mockResolvedValue(history([
      turn("plan", 1, "Older Plan answer"), turn("play", 2, "Latest Play answer"),
    ]));
    render(<Harness initial="play" />);
    fireEvent.click(await screen.findByRole("button", { name: "Open" }));
    expect(await screen.findByText("Latest Play answer")).toBeInTheDocument();
    expect(screen.getByText("Older Plan answer")).toBeVisible();
    expect(screen.queryByText(/Earlier conversation/)).not.toBeInTheDocument();
    expect(screen.getByText("Older Plan answer")).toBeInTheDocument();
    expect(screen.getByRole("log", { name: "Conversation messages" })).toBeInTheDocument();
    fireEvent.click(screen.getByTitle("Conversation options"));
    expect(screen.getByRole("button", { name: "Settings" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "New conversation" })).toBeInTheDocument();
  });

  it("starts a World conversation from Play with the same saved-command path", async () => {
    vi.mocked(postWorldAgentNewConversation).mockImplementation(async (worldId, request) => {
      vi.mocked(getWorldAgentConversationHistory).mockResolvedValue({ ...history(),
        conversation_id: "22222222-2222-4222-8222-222222222222", active_conversation_id: "22222222-2222-4222-8222-222222222222", pointer_revision: 2 });
      return { schema: "dmb_agent_new_conversation_response_v1", world_id: worldId,
        conversation_id: "22222222-2222-4222-8222-222222222222", active_conversation_id: "22222222-2222-4222-8222-222222222222", pointer_revision: request.expected_pointer_revision + 1 };
    });
    render(<Harness initial="play" />);
    fireEvent.click(await screen.findByRole("button", { name: "Open" }));
    await screen.findByText("Original Plan answer");
    fireEvent.click(screen.getByTitle("Conversation options"));
    fireEvent.click(screen.getByRole("button", { name: "New conversation" }));
    await waitFor(() => expect(postWorldAgentNewConversation).toHaveBeenCalledTimes(1));
    expect(vi.mocked(postWorldAgentNewConversation).mock.calls[0]?.[0]).toBe(WORLD);
    await waitFor(() => expect(screen.queryByText("Original Plan answer")).not.toBeInTheDocument());
    expect(screen.queryByText(/No messages yet/)).not.toBeInTheDocument();
    expect(screen.queryByText(/New World conversation confirmed/)).not.toBeInTheDocument();
  });

  it("keeps a local Plan proposal in the shared transcript while Play shows it read-only", async () => {
    render(<Harness />);
    fireEvent.click(await screen.findByRole("button", { name: "Open" }));
    await screen.findByText("Original Plan answer");
    fireEvent.click(screen.getByRole("button", { name: "Seed Plan proposal" }));
    expect(await screen.findByText("Rewrite the crossing scene")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Switch surface" }));
    expect(await screen.findByText("Rewrite the crossing scene")).toBeInTheDocument();
    expect(screen.getByText("Return to Plan to review or apply this proposal.")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Apply changes" })).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Switch surface" }));
    expect(await screen.findByText("Rewrite the crossing scene")).toBeInTheDocument();
  });

  it("keeps an active Plan proposal read-only in Play and reviewable on return", async () => {
    const captured = { editor: {} as CapturedWorldPlanEditTarget["editor"],
      request: { document_id: "plan-one", world_id: WORLD, session: 1, base_revision: 7,
        base_content_sha256: SHA, draft_markdown: "# Draft Plan", draft_sha256: "d".repeat(64),
        target_kind: "insert_at_caret" as const, selected_text: "" },
      from: 1, to: 1, editorJson: "{}", selectionJson: "{}", draftGeneration: 0, selectionGeneration: 0 };
    const bridge: WorldPlanEditBridge = { capture: vi.fn(async () => captured),
      preview: vi.fn(() => ({ before: { markdown: "# Before" }, after: { markdown: "# After" } })),
      apply: vi.fn(async () => undefined) };
    vi.mocked(postWorldPlanDocumentEditProposal).mockImplementation(async (request) => ({
      schema_version: "dmb_world_plan_document_edit_proposal_v1", action_id: "action-one",
      idempotency_key: request.idempotency_key, document_id: request.document_id, world_id: request.world_id,
      base_revision: request.base_revision, base_content_sha256: request.base_content_sha256,
      draft_sha256: request.draft_sha256, target_kind: request.target_kind,
      selected_text_sha256: "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
      replacement_markdown: "# After", summary: "A clearer opening.", assumptions: [], model: "test",
      model_observed: false, model_latency_ms: 0, wall_latency_ms: 0, usage: null,
    } as Awaited<ReturnType<typeof postWorldPlanDocumentEditProposal>>));
    render(<Harness editBridge={bridge} />);
    fireEvent.click(await screen.findByRole("button", { name: "Open" }));
    const composer = await screen.findByLabelText("Message DungeonBuddy");
    await waitFor(() => expect(composer).toBeEnabled());
    fireEvent.change(composer, { target: { value: "Rewrite this Plan opening" } });
    fireEvent.click(screen.getByRole("button", { name: "Propose edit" }));
    await waitFor(() => expect(postWorldPlanDocumentEditProposal).toHaveBeenCalledTimes(1));
    await waitFor(() => expect(bridge.preview).toHaveBeenCalledTimes(1));
    expect(screen.queryByText("This preview is no longer current. It cannot be applied.")).not.toBeInTheDocument();
    expect(await screen.findByRole("button", { name: "Apply to draft" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Switch surface" }));
    expect(await screen.findByText("Rewrite this Plan opening")).toBeInTheDocument();
    expect(screen.getByText("Plan proposal preview · return to Plan to review or apply")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Apply to draft" })).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Switch surface" }));
    const apply = await screen.findByRole("button", { name: "Apply to draft" });
    fireEvent.click(apply);
    await waitFor(() => expect(bridge.apply).toHaveBeenCalledTimes(1));
  });

  it("freezes the admitted Play request and shows its late reply on Plan without redispatch", async () => {
    let release!: (value: Awaited<ReturnType<typeof postWorldPlayAgentTurn>>) => void;
    const deferred = new Promise<Awaited<ReturnType<typeof postWorldPlayAgentTurn>>>((resolve) => { release = resolve; });
    vi.mocked(postWorldPlayAgentTurn).mockReturnValue(deferred);
    const mounted = render(<Harness initial="play" />);
    fireEvent.click(await screen.findByRole("button", { name: "Open" }));
    const composer = await screen.findByLabelText("Message DungeonBuddy");
    await waitFor(() => expect(composer).toBeEnabled());
    fireEvent.change(composer, { target: { value: "What happens now?" } });
    fireEvent.click(screen.getByRole("button", { name: "Send message" }));
    const request = vi.mocked(postWorldPlayAgentTurn).mock.calls[0]?.[0] as WorldPlayAgentTurnRequestV1;
    expect(request).toMatchObject({ surface: { surface_id: "play", instance_id: "play-instance" },
      owner_scope: { kind: "world", world_id: WORLD },
      primary_work: { kind: "run", object_id: RUN, expected_revision: 3 },
      graph_request: { mode: "world", world_id: WORLD, campaign_id: null, revision_pin: null,
        focus: { kind: "none", session_id: null, campaign_id: null } }, graph_selection: null });
    fireEvent.click(screen.getByRole("button", { name: "Switch surface" }));
    vi.mocked(getWorldAgentConversationHistory).mockResolvedValue(history([
      turn("plan", 1, "Original Plan answer"), turn("play", 2, "Original Play answer"),
    ]));
    release(playResponse(request));
    await waitFor(() => expect(screen.getByText("Original Play answer")).toBeInTheDocument());
    expect(postWorldPlayAgentTurn).toHaveBeenCalledTimes(1);
    fireEvent.click(screen.getByRole("button", { name: "Close chat" }));
    fireEvent.click(await screen.findByRole("button", { name: "Open" }));
    await waitFor(() => expect(screen.getByText("Original Play answer")).toBeInTheDocument());
    mounted.unmount();
    render(<Harness initial="play" />);
    fireEvent.click(await screen.findByRole("button", { name: "Open" }));
    await waitFor(() => expect(screen.getByText("Original Play answer")).toBeInTheDocument());
    expect(postWorldPlayAgentTurn).toHaveBeenCalledTimes(1);
  });

  it("keeps a deferred Plan answer pinned to its Plan when it arrives in Play", async () => {
    let release!: (value: Awaited<ReturnType<typeof postWorldPlanAgentTurn>>) => void;
    vi.mocked(postWorldPlanAgentTurn).mockReturnValue(new Promise((resolve) => { release = resolve; }));
    render(<Harness />);
    fireEvent.click(await screen.findByRole("button", { name: "Open" }));
    await screen.findByText("Original Plan answer");
    fireEvent.click(screen.getByRole("button", { name: "Use Test World facts · On" }));
    const composer = await screen.findByLabelText("Message DungeonBuddy");
    await waitFor(() => expect(composer).toBeEnabled());
    fireEvent.change(composer, { target: { value: "What changed in the Plan?" } });
    fireEvent.click(screen.getByRole("button", { name: "Send message" }));
    await waitFor(() => expect(postWorldPlanAgentTurn).toHaveBeenCalledTimes(1));
    const request = vi.mocked(postWorldPlanAgentTurn).mock.calls[0]![0];
    expect(request).toMatchObject({ surface: { surface_id: "plan", instance_id: "plan-instance" },
      primary_work: { kind: "plan", object_id: "plan-one", expected_revision: 7,
        expected_revision_n: 2, expected_content_sha256: SHA }, graph_request: { mode: "none" } });
    fireEvent.click(screen.getByRole("button", { name: "Switch surface" }));
    const lateTurn = { ...turn("plan", 2, "Late Plan answer"), turn_id: request.turn_id,
      user_text: request.message, provenance: { ...turn("plan", 2, "Late Plan answer").provenance,
        surface_instance_id: request.surface.instance_id,
        primary_work: { resolution: "resolved" as const, kind: "plan", object_id: "plan-one",
          revision: "7", content_sha256: SHA, object_revision: 7, work_revision_id: WORK_REVISION,
          revision_n: 2 } } };
    vi.mocked(getWorldAgentConversationHistory).mockResolvedValue(history([turn("plan", 1, "Original Plan answer"), lateTurn]));
    release(planResponse(request));
    expect(await screen.findByText("Late Plan answer")).toBeInTheDocument();
    expect(screen.getByTestId("world-agent-conversation-host")).toBeInTheDocument();
    expect(postWorldPlanAgentTurn).toHaveBeenCalledTimes(1);
  });

  it("blocks an unadmitted Run and isolates a replacement World", async () => {
    render(<Harness initial="play" admitted={false} />);
    fireEvent.click(await screen.findByRole("button", { name: "Open" }));
    expect(await screen.findByLabelText("Message DungeonBuddy")).toBeDisabled();
    expect(await screen.findByText("Original Plan answer")).toBeInTheDocument();
    expect(postWorldPlayAgentTurn).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole("button", { name: "Switch World" }));
    await waitFor(() => expect(screen.queryByText("Original Plan answer")).not.toBeInTheDocument());
  });

  it.each([false,true])("keeps failed draft memory and warning through actual keyed World remounts: blocked=%s",async blocked=>{
    if(blocked)sessionStorage.setItem('dmb:conversation-composer-drafts:v1:A','unknown bytes');
    function DraftProbe(){
      const state=useWorldAgentConversationState()!;
      return <><textarea aria-label="Draft probe" value={state.composerDrafts['build:doc']??''}
        onChange={event=>state.setComposerDrafts(d=>({...d,'build:doc':event.target.value}))}/>
        <span role="status">{state.composerDraftWarning}</span></>;
    }
    function Fixture({world}:{world:string}){
      return <AgentInteractionProvider><WorldAgentConversationProvider key={world} worldId={world}><DraftProbe/></WorldAgentConversationProvider></AgentInteractionProvider>;
    }
    const view=render(<Fixture world="A"/>);
    const write=Storage.prototype.setItem;
    const denied=vi.spyOn(Storage.prototype,'setItem').mockImplementation(function(key,value){
      if(this===window.sessionStorage)throw new DOMException('quota','QuotaExceededError');
      return write.call(this,key,value);
    });
    try{
      fireEvent.change(screen.getByLabelText('Draft probe'),{target:{value:'Unsent memory-only thought'}});
      const warning=screen.getByRole('status').textContent;
      expect(warning).toBeTruthy();
      denied.mockRestore();
      view.rerender(<Fixture world="B"/>);
      expect(screen.getByLabelText('Draft probe')).toHaveValue('');
      view.rerender(<Fixture world="A"/>);
      expect(screen.getByLabelText('Draft probe')).toHaveValue('Unsent memory-only thought');
      expect(screen.getByRole('status').textContent).toBe(warning);
      if(blocked)expect(sessionStorage.getItem('dmb:conversation-composer-drafts:v1:A')).toBe('unknown bytes');
    }finally{denied.mockRestore();}
  });

  it.each(["plan", "play", "build"] as const)("restores complete unsent %s text after remount without sending it", async initial => {
    const mounted=render(<Harness initial={initial}/>);
    fireEvent.click(await screen.findByRole("button",{name:"Open",exact:true}));
    const input=await screen.findByLabelText("Message DungeonBuddy");
    await waitFor(()=>expect(input).toBeEnabled());
    const text="  A next thought 🕯️\nKeep the exact wording.  ";
    fireEvent.change(input,{target:{value:text}});
    mounted.unmount();
    render(<Harness initial={initial}/>);
    fireEvent.click(await screen.findByRole("button",{name:"Open",exact:true}));
    await waitFor(()=>expect(screen.getByLabelText("Message DungeonBuddy")).toHaveValue(text));
    expect(postWorldBuildAgentTurn).not.toHaveBeenCalled();
    expect(postWorldPlanAgentTurn).not.toHaveBeenCalled();
    expect(postWorldPlayAgentTurn).not.toHaveBeenCalled();
  });

  it("keeps the composer usable and warns when its tab recovery write fails",async()=>{
    const write=Storage.prototype.setItem;
    const denied=vi.spyOn(Storage.prototype,'setItem').mockImplementation(function(key,value){
      if(this===window.sessionStorage&&key.startsWith('dmb:conversation-composer-drafts:'))throw new DOMException('quota','QuotaExceededError');
      return write.call(this,key,value);
    });
    try{
      render(<Harness initial="build"/>);
      fireEvent.click(await screen.findByRole("button",{name:"Open",exact:true}));
      const input=await screen.findByLabelText("Message DungeonBuddy");
      await waitFor(()=>expect(input).toBeEnabled());
      fireEvent.change(input,{target:{value:'Keep this text in memory'}});
      expect(input).toHaveValue('Keep this text in memory');
      expect(await screen.findByText(COMPOSER_DRAFT_WRITE_WARNING)).toBeVisible();
      expect(screen.getByRole("button",{name:"Send message"})).toBeEnabled();
    }finally{denied.mockRestore();}
  });

  it("retains each Plan draft in its own document slot while another Plan opens blank", async () => {
    render(<Harness />);
    fireEvent.click(await screen.findByRole("button", { name: "Open" }));
    const composer = await screen.findByLabelText("Message DungeonBuddy");
    fireEvent.change(composer, { target: { value: "Rewrite this Plan scene" } });
    fireEvent.click(screen.getByRole("button", { name: "Switch Plan document" }));
    await waitFor(() => expect(screen.getByLabelText("Message DungeonBuddy")).toHaveValue(""));
    fireEvent.click(screen.getByRole("button", { name: "Switch Plan document" }));
    await waitFor(() => expect(screen.getByLabelText("Message DungeonBuddy")).toHaveValue("Rewrite this Plan scene"));
    expect(postWorldPlanAgentTurn).not.toHaveBeenCalled();
  });
  it("retains an unsent Play question while the session note save gate unmounts transport", async () => {
    render(<Harness initial="play" />);
    fireEvent.click(await screen.findByRole("button", { name: "Open" }));
    const composer = await screen.findByLabelText("Message DungeonBuddy");
    await waitFor(() => expect(composer).toBeEnabled());
    fireEvent.change(composer, { target: { value: "Keep my unsent scene question" } });
    fireEvent.click(screen.getByRole("button", { name: "Use session copy" }));
    await screen.findByRole("status", { name: "Play conversation unavailable" });
    expect(screen.queryByLabelText("Message DungeonBuddy")).not.toBeInTheDocument();
    expect(postWorldPlayAgentTurn).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole("button", { name: "Use session copy" }));
    await waitFor(() => expect(screen.getByLabelText("Message DungeonBuddy")).toHaveValue("Keep my unsent scene question"));
    expect(postWorldPlayAgentTurn).not.toHaveBeenCalled();
  });

  it("proposes a scene from Play chat, reviews media/table/callout content, and applies only a guarded session save", async () => {
    const markdown = '<!-- dmb-playable-element:v2 kind=beat id=beat:road -->\n## Road\n\n<!-- dmb-playable-element:v2 kind=scene id=scene:gate -->\n### Gate\n\nOriginal scene.\n\n![Gate map](dmb-media:dddddddd-dddd-4ddd-8ddd-dddddddddddd "dmb-image:v1 width=30 collapsed=true")\n';
    const runId = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa";
    const origin = { playable_artifact_id: "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb", playable_revision: 1,
      playable_work_revision_id: WORK_REVISION, playable_content_sha256: await contentSha256(markdown) };
    const content: PlayRunContent = { schema_version: "dmb_world_play_run_content_v1", world_id: WORLD, run_id: runId,
      origin, source: "pinned", edition_revision: 0, edition_revision_id: null, markdown, content_sha256: origin.playable_content_sha256,
      committed_at: "2026-10-18T00:00:00Z", structure_sha256: SHA, observed_run_revision: 3 };
    const before = '\nOriginal scene.\n\n![Gate map](dmb-media:dddddddd-dddd-4ddd-8ddd-dddddddddddd "dmb-image:v1 width=30 collapsed=true")\n';
    const replacement = '\nRevised scene.\n\n| Object | State |\n| --- | --- |\n| Lantern | Lit |\n\n> [!READ-ALOUD]\n> The blue lantern glows.\n\n![Gate map](dmb-media:dddddddd-dddd-4ddd-8ddd-dddddddddddd "dmb-image:v1 width=60 collapsed=true")\n';
    const candidate = markdown.slice(0, markdown.length-before.length)+replacement;
    const record: PlaySceneEditRecord = { schema_version: "dmb_play_scene_edit_proposal_v1", world_id: WORLD, run_id: runId,
      proposal_id: "eeeeeeee-eeee-4eee-8eee-eeeeeeeeeeee", instruction: "Revise the scene", status: "ready", failure_code: null,
      created_at: "2026-10-18T01:00:00Z", updated_at: "2026-10-18T01:00:00Z",
      basis: { run_revision: 3, scene_id: "scene:gate", content_basis: { edition_revision: 0, edition_revision_id: null, content_sha256: content.content_sha256 }, origin, scene_note_sha256: null },
      result: { schema_version: "dmb_play_scene_edit_result_v1", before_markdown: before, replacement_markdown: replacement, candidate_markdown: candidate, candidate_sha256: await contentSha256(candidate),
        body_start_utf8: new TextEncoder().encode(markdown.slice(0, markdown.length-before.length)).length, body_end_utf8: new TextEncoder().encode(markdown).length,
        summary: "A clearer gate scene.", assumptions: [], model: "test", model_observed: true, model_latency_ms: 1, wall_latency_ms: 2 } };
    vi.mocked(proposePlaySceneEdit).mockResolvedValue(record);
    vi.mocked(listPlaySceneEdits).mockResolvedValue([]);
    vi.mocked(getWorldPlayRunContent).mockResolvedValue({ ...content, source: "edition", edition_revision: 1,
      edition_revision_id: record.proposal_id, markdown: candidate, content_sha256: record.result!.candidate_sha256 });
    vi.mocked(putWorldPlayRunContentCommand).mockImplementation(async (_run, _world, commandId, request) => ({
      schema_version: "dmb_world_play_run_content_receipt_v1", world_id: WORLD, run_id: runId, command_id: commandId,
      request_sha256: await sha256Hex(canonicalJson({ world_id: WORLD, run_id: runId, command_id: commandId, ...request })), origin,
      expected_edition_revision: 0, expected_content_sha256: content.content_sha256, accepted_edition_revision: 1,
      accepted_edition_revision_id: record.proposal_id, accepted_content_sha256: record.result!.candidate_sha256,
      committed_at: "2026-10-18T01:00:00Z", observed_run_revision: 3 }));
    render(<Harness initial="play" editContent={content} />);
    fireEvent.click(await screen.findByRole("button", { name: "Open", exact: true }));
    const composer = await screen.findByLabelText("Message DungeonBuddy");
    await waitFor(() => expect(composer).toBeEnabled());
    fireEvent.click(screen.getByTitle("Conversation options"));
    fireEvent.click(screen.getByRole("button", { name: "Propose scene edit", exact: true }));
    fireEvent.change(composer, { target: { value: "Revise the scene" } });
    fireEvent.click(screen.getByRole("button", { name: "Send message", exact: true }));
    expect(await screen.findByText("A clearer gate scene.")).toBeInTheDocument();
    expect(screen.getByRole("table")).toHaveTextContent("Lantern");
    expect(screen.getByText("The blue lantern glows.")).toBeInTheDocument();
    expect(document.querySelector('[data-media-asset-id="dddddddd-dddd-4ddd-8ddd-dddddddddddd"]')).not.toBeNull();
    expect(putWorldPlayRunContentCommand).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole("button", { name: "Apply to session copy" }));
    await waitFor(() => expect(putWorldPlayRunContentCommand).toHaveBeenCalledOnce());
    expect(vi.mocked(putWorldPlayRunContentCommand).mock.calls[0][3]).toMatchObject({ expected_run_revision: 3, markdown: candidate, expected_origin: origin });
    await waitFor(() => expect(screen.queryByRole("status", { name: "Play conversation unavailable" })).not.toBeInTheDocument());
    expect(postWorldPlanDocumentEditProposal).not.toHaveBeenCalled();
    expect(postWorldPlayAgentTurn).not.toHaveBeenCalled();
    expect(content.markdown).toBe(markdown);
  });

  it("unmounts Play transport for a session copy and ignores a late history result", async () => {
    let resolve!: (value: WorldAgentConversationHistoryResponseV1) => void;
    vi.mocked(getWorldAgentConversationHistory).mockReturnValue(new Promise(done => { resolve = done; }));
    render(<Harness initial="play" />);
    fireEvent.click(await screen.findByRole("button", { name: "Open" }));
    await waitFor(() => expect(getWorldAgentConversationHistory).toHaveBeenCalled());
    fireEvent.click(screen.getByRole("button", { name: "Use session copy" }));
    expect(await screen.findByRole("status", { name: "Play conversation unavailable" })).toHaveTextContent("temporarily unavailable");
    await act(async () => resolve(history([turn("play", 2, "Late original-pin reply")])));
    expect(screen.queryByLabelText("Message DungeonBuddy")).not.toBeInTheDocument();
    expect(screen.queryByText("Late original-pin reply")).not.toBeInTheDocument();
    expect(postWorldPlayAgentTurn).not.toHaveBeenCalled();
  });

  it("does not revive a session-copy composer when an original-pin in-flight reply arrives", async () => {
    let resolve!: (value: Awaited<ReturnType<typeof postWorldPlayAgentTurn>>) => void;
    vi.mocked(postWorldPlayAgentTurn).mockReturnValue(new Promise(done => { resolve = done; }));
    render(<Harness initial="play" />);
    fireEvent.click(await screen.findByRole("button", { name: "Open" }));
    const composer = await screen.findByLabelText("Message DungeonBuddy");
    await waitFor(() => expect(composer).toBeEnabled());
    fireEvent.change(composer, { target: { value: "Original pin question" } });
    fireEvent.click(screen.getByRole("button", { name: "Send message" }));
    await waitFor(() => expect(postWorldPlayAgentTurn).toHaveBeenCalledOnce());
    const request = vi.mocked(postWorldPlayAgentTurn).mock.calls[0][0];
    fireEvent.click(screen.getByRole("button", { name: "Use session copy" }));
    await screen.findByRole("status");
    await act(async () => resolve(playResponse(request)));
    expect(screen.queryByLabelText("Message DungeonBuddy")).not.toBeInTheDocument();
    expect(postWorldPlayAgentTurn).toHaveBeenCalledTimes(1);
    expect(screen.queryByRole("button", { name: /retry.*request/i })).not.toBeInTheDocument();
  });

  it.each(['plan','play','build'] as const)('renders sealed Rules history and source controls on %s without losing the composer', async initial => {
    const { context, answer, capsule } = rulesAnswerFixture();
    const b = context.accepted_binding;
    const row = { ...turn('play', 1, answer), schema: 'dmb_agent_conversation_history_mixed_turn_v1' as const,
      turn_id: b.turn_id, idempotency_key: '66666666-6666-4666-8666-666666666666', rules_context: context };
    const page = { ...history(), schema: 'dmb_agent_conversation_history_v4' as const,
      conversation_id: b.conversation_id, active_conversation_id: b.conversation_id, turns: [row] };
    vi.mocked(getWorldAgentConversationHistory).mockResolvedValue(page);
    vi.mocked(getHistoricalRulesPassage).mockResolvedValue(capsule);
    render(<Harness initial={initial} />);
    fireEvent.click(await screen.findByRole('button', { name: 'Open' }));
    await screen.findAllByText(answer);
    const composer = await screen.findByLabelText('Message DungeonBuddy');
    fireEvent.change(composer, { target: { value: 'Keep this unsent draft' } });
    expect(getHistoricalRulesPassage).not.toHaveBeenCalled();
    fireEvent.click(screen.getByText('Rules references', { selector: 'summary' }));
    fireEvent.click(await screen.findByRole('button', { name: /Inspect Rules source/ }));
    expect(await screen.findByRole('region', { name: 'Cited rules passage' })).toHaveTextContent(capsule.support.excerpt_text);
    expect(getHistoricalRulesPassage).toHaveBeenCalledTimes(1);
    expect(screen.getByLabelText('Message DungeonBuddy')).toBe(composer);
    expect(composer).toHaveValue('Keep this unsent draft');
    fireEvent.click(screen.getByRole('button', { name: /^(Close conversation|Close chat|Collapse)$/ }));
    expect(screen.queryByRole('region', { name: 'Cited rules passage' })).not.toBeInTheDocument();
    fireEvent.click(await screen.findByRole('button', { name: 'Open' }));
    expect(getHistoricalRulesPassage).toHaveBeenCalledTimes(1);
    expect(screen.getByLabelText('Message DungeonBuddy')).toHaveValue('Keep this unsent draft');
    expect(postWorldPlanAgentTurn).not.toHaveBeenCalled();
    expect(postWorldPlayAgentTurn).not.toHaveBeenCalled();
    expect(postWorldBuildAgentTurn).not.toHaveBeenCalled();
  });

  it('keeps Rules text alongside an independently approved Build base answer', async () => {
    const base = await buildGraphContext();
    const { context, answer, ruleText } = rulesAnswerFixture(base), b = context.accepted_binding;
    const authority = base.receipt.graph_authority;
    const ref = (kind: string, object_id: string, revision: string) => ({ resolution: 'resolved' as const, kind, object_id, revision,
      content_sha256: null, object_revision: null, work_revision_id: null, revision_n: null });
    const original = turn('plan', 1, answer);
    const row = { ...original, schema: 'dmb_agent_conversation_history_mixed_turn_v1' as const,
      turn_id: b.turn_id, idempotency_key: '66666666-6666-4666-8666-666666666666', rules_context: context,
      provenance: { ...original.provenance, surface_id: 'build', surface_instance_id: 'build-instance',
        supporting_work: [ref('dmb_build_source_visibility_v1', base.receipt.source_basis.visibility, '1'),
          ref('dmb_build_graph_binding_v1', authority.native_world_id, String(authority.binding_version)),
          ref('world_graph_revision', authority.native_world_id, authority.graph_revision)],
        primary_work: { resolution: 'resolved' as const, kind: 'build', object_id: 'source-one', revision: '2', content_sha256: SHA,
          object_revision: null, work_revision_id: null, revision_n: null } } };
    vi.mocked(getWorldAgentConversationHistory).mockResolvedValue({ ...history(), schema: 'dmb_agent_conversation_history_v4',
      conversation_id: b.conversation_id, active_conversation_id: b.conversation_id, turns: [row] });
    render(<Harness initial='plan' />);
    fireEvent.click(await screen.findByRole('button', { name: 'Open' }));
    await waitFor(() => expect(document.querySelector('.world-plan-agent-conversation__message--assistant .world-plan-agent-answer')).toHaveTextContent(ruleText));
    const visibleAnswer = document.querySelector('.world-plan-agent-conversation__message--assistant .world-plan-agent-answer');
    expect(visibleAnswer).toBeVisible();
    expect(visibleAnswer).toHaveTextContent(base.completion!.answer_segments[0].text);
    expect(getHistoricalRulesPassage).not.toHaveBeenCalled();
  });

  it.each(['text','world','conversation','seal'] as const)('rejects mismatched mixed history %s before displaying source controls', async kind => {
    const { context, answer } = rulesAnswerFixture(), b = context.accepted_binding;
    const row = { ...turn('play', 1, answer), schema: 'dmb_agent_conversation_history_mixed_turn_v1' as const,
      turn_id: b.turn_id, idempotency_key: '66666666-6666-4666-8666-666666666666', rules_context: context };
    if (kind === 'text') row.assistant_text += ' changed';
    if (kind === 'world') b.world_id = 'other-world';
    if (kind === 'conversation') b.conversation_id = b.turn_id;
    if (kind === 'seal') context.accepted_binding_sha256 = '0'.repeat(64);
    else context.accepted_binding_sha256 = fixtureHash(rulesCanonical(b));
    vi.mocked(getWorldAgentConversationHistory).mockResolvedValue({ ...history(), schema: 'dmb_agent_conversation_history_v4',
      conversation_id: '11111111-1111-4111-8111-111111111111', active_conversation_id: '11111111-1111-4111-8111-111111111111', turns: [row] });
    render(<Harness initial='play' />);
    fireEvent.click(await screen.findByRole('button', { name: 'Open' }));
    await waitFor(() => expect(getWorldAgentConversationHistory).toHaveBeenCalled());
    await waitFor(() => expect(screen.getByText(/history.*(invalid|match|verified)|could not.*history|history.*unavailable/i)).toBeInTheDocument());
    expect(screen.queryByText('Rules references')).not.toBeInTheDocument();
    expect(getHistoricalRulesPassage).not.toHaveBeenCalled();
  });

  it.each(['approved','unclaimed','bad_seal','bad_owner'] as const)('validates a live mixed Build reply before settling recovery: %s', async mode => {
    const base = await buildGraphContext();
    const fixture = mode === 'approved' ? rulesAnswerFixture(base) : rulesUnclaimedFixture(base), context = fixture.context, b = context.accepted_binding;
    const current: WorldAgentConversationHistoryResponse = history();
    vi.mocked(getWorldAgentConversationHistory).mockImplementation(async () => current);
    vi.mocked(postWorldBuildAgentTurn).mockImplementation(async request => {
      const { play_context: _unusedNativeContext, ...reply } = playResponse({ ...nativePlayRequestFixture(), client_thread_id: request.client_thread_id, turn_id: request.turn_id });
      const contextForReply = structuredClone(context);
      if (mode === 'bad_seal') contextForReply.accepted_binding_sha256 = '0'.repeat(64);
      const conversation = { ...reply.conversation, conversation_id: mode === 'bad_owner' ? b.turn_id : b.conversation_id };
      return { ...reply, schema: 'dmb_agent_rules_turn_response_v1', surface: { ...reply.surface, surface_id: 'build', instance_id: 'build-instance' },
        primary_work: { ...reply.primary_work, kind: 'build', object_id: 'source-one', revision_used: 2, expected_revision: 2 },
        client_work_state_reported: request.client_work_state, conversation,
        graph: base ? { ...reply.graph, world_id: base.receipt.graph_authority.native_world_id, revision_id: base.receipt.graph_authority.graph_revision } : reply.graph,
        answer: { ...reply.answer, text: fixture.answer, graph_grounded: b.graph_used }, rules_context: contextForReply };
    });
    render(<Harness initial='build' />);
    fireEvent.click(await screen.findByRole('button', { name: 'Open' }));
    const composer = await screen.findByLabelText('Message DungeonBuddy');
    await waitFor(() => expect(composer).toBeEnabled());
    fireEvent.change(composer, { target: { value: 'Discuss the source and occupied space.' } });
    fireEvent.click(screen.getByRole('button', { name: 'Send message' }));
    await waitFor(() => expect(postWorldBuildAgentTurn).toHaveBeenCalledTimes(1));
    const storageKey = 'dmb:world-play-pending-turn:v1:' + WORLD;
    if (mode === 'bad_seal' || mode === 'bad_owner') {
      await screen.findByText('The Rules reply did not match its accepted answer and sources. Check World history or explicitly retry the saved request with its original IDs.');
      expect(localStorage.getItem(storageKey)).not.toBeNull();
    } else {
      await waitFor(() => expect(localStorage.getItem(storageKey)).toBeNull());
      expect(screen.queryByText(/Rules reply did not match/)).not.toBeInTheDocument();
    }
    expect(getHistoricalRulesPassage).not.toHaveBeenCalled();
    expect(postWorldBuildAgentTurn).toHaveBeenCalledTimes(1);
  });

  it('rehydrates native Play synthesis with separate note and reflection links',async()=>{
    const request=nativePlayRequestFixture();request.primary_work.object_id='22222222-2222-4222-8222-222222222222';
    const base=nativePlayContextFixture(request);
    const text='The rehearsal kept the decision open; the reflection proposes talking next.';
    base.completion={schema:'dmb_surface_evidence_completion_v4',surface_id:'play',context_receipt_sha256:base.receipt.context_receipt_sha256,
      answer_basis:'mixed_evidence',answer_context_status:'authored_grounded',citation_map:null,source_citations:[],native_source_citations:[],answer_segments:[
        {kind:'session_summary',text,supports:[0,1].map(i=>({kind:'authored_excerpt' as const,text:'Saved source text.',source_kind:'session' as const,
          source_name:'Saved rehearsal',object_id:base.receipt.play_basis.run_id,revision:'4',body_sha256:'b'.repeat(64),owner_sha256:'c'.repeat(64),
          source_handle:'q'+'a'.repeat(64),block_handle:'b'+String(i+3).repeat(64),partition_version:'markdown_source_blocks_v1' as const,
          byte_start:0,byte_end:18,block_sha256:'b'.repeat(64),entry_identity:String(i+1).repeat(64),source_ordinal:i,
          entry_kind:i?'closing_reflections' as const:'scene_note' as const,element_id:i?null:'scene:gate',checkpoint_content_sha256:base.receipt.play_basis.content_sha256}))}]};
    const row={...turn('play',1,text),play_context:base,provenance:nativePlayProvenanceFixture(base)};
    vi.mocked(getWorldAgentConversationHistory).mockResolvedValue({...history(),schema:'dmb_agent_conversation_history_v2',turns:[row]});
    render(<Harness initial="play"/>);fireEvent.click(await screen.findByRole('button',{name:'Open',exact:true}));
    expect(await screen.findByLabelText('Saved session summary')).toHaveTextContent(text);
    expect(screen.getByRole('link',{name:'1'})).toHaveAttribute('title','Saved rehearsal · Scene notes');
    expect(screen.getByRole('link',{name:'2'})).toHaveAttribute('title','Saved rehearsal · Closing reflections');
    expect(postWorldPlayAgentTurn).not.toHaveBeenCalled();
  });

  it.each(['plan','play'] as const)('rehydrates quoted Play evidence on %s with the same source authority',async initial=>{
    const base=nativePlayContextFixture(nativePlayRequestFixture());
    const entry=base.receipt.play_sources.entries[0]!;
    const text='Frozen Play quotation.';
    base.completion={schema:'dmb_surface_evidence_completion_v1',surface_id:'play',context_receipt_sha256:base.receipt.context_receipt_sha256,
      answer_basis:'mixed_evidence',answer_context_status:'authored_grounded',citation_map:null,source_citations:[],answer_segments:[
        {kind:'authored_quote',text,source_kind:'play',source_handle:entry.source_id,source_name:'Saved Play scene',
          object_id:entry.locator.run_id,revision:String(entry.locator.run_revision),body_sha256:entry.text_sha256,owner_sha256:entry.payload_sha256}]};
    const row={...turn('play',1,text),play_context:base,provenance:nativePlayProvenanceFixture(base)};
    vi.mocked(getWorldAgentConversationHistory).mockResolvedValue({...history(),schema:'dmb_agent_conversation_history_v2',turns:[row]});
    render(<Harness initial={initial}/>);
    fireEvent.click(await screen.findByRole('button',{name:'Open',exact:true}));
    expect((await screen.findByText(text)).closest('blockquote')).not.toBeNull();
    expect(screen.getByText('Saved Play scene · quoted excerpt')).toBeInTheDocument();
    expect(postWorldPlayAgentTurn).not.toHaveBeenCalled();
  });

  it.each(['plan', 'play', 'build'] as const)('hosts native Play mixed evidence on %s without source reads or composer replacement', async initial => {
    const base = nativePlayContextFixture(nativePlayRequestFixture(), 'The saved scene note describes the crossing.');
    const f = rulesAnswerFixture(base), b = f.context.accepted_binding;
    const row = { ...turn('play', 1, f.answer), schema: 'dmb_agent_conversation_history_mixed_turn_v1' as const,
      turn_id: b.turn_id, idempotency_key: '66666666-6666-4666-8666-666666666666', rules_context: f.context,
      provenance: nativePlayProvenanceFixture(base) };
    vi.mocked(getWorldAgentConversationHistory).mockResolvedValue({ ...history(), schema: 'dmb_agent_conversation_history_v4',
      conversation_id: b.conversation_id, active_conversation_id: b.conversation_id, turns: [row] });
    vi.mocked(getHistoricalRulesPassage).mockResolvedValue(f.capsule);
    render(<Harness initial={initial} />);
    fireEvent.click(await screen.findByRole('button', { name: 'Open' }));
    await screen.findByText(/saved scene note describes the crossing/);
    const composer = await screen.findByLabelText('Message DungeonBuddy');
    fireEvent.change(composer, { target: { value: 'Keep this surface draft' } });
    expect(getHistoricalRulesPassage).not.toHaveBeenCalled();
    fireEvent.click(screen.getByText('Rules references', { selector: 'summary' }));
    fireEvent.click(await screen.findByRole('button', { name: /Inspect Rules source/ }));
    expect(await screen.findByRole('region', { name: 'Cited rules passage' })).toHaveTextContent(f.capsule.support.excerpt_text);
    expect(screen.getByLabelText('Message DungeonBuddy')).toBe(composer);
    expect(composer).toHaveValue('Keep this surface draft');
    expect(getHistoricalRulesPassage).toHaveBeenCalledTimes(1);
  });

  it.each(['ordinary', 'mixed', 'unclaimed', 'unclaimed-edition', 'unclaimed-scene', 'edition', 'scene', 'world', 'note', 'text'] as const)('admits only the exact native Play live reply before settling recovery: %s', async mode => {
    vi.mocked(postWorldPlayAgentTurn).mockImplementation(async request => {
      const sourceRequest = structuredClone(request);
      if (mode === 'edition' || mode === 'unclaimed-edition') sourceRequest.primary_work.play_content_basis = { edition_revision: 2,
        edition_revision_id: '00000000-0000-4000-8000-000000000044', content_sha256: 'b'.repeat(64) };
      if (mode === 'scene' || mode === 'unclaimed-scene') sourceRequest.play_target.scene_id = 'scene:other';
      if (mode === 'world') sourceRequest.owner_scope.world_id = 'other-world';
      const base = nativePlayContextFixture(sourceRequest), response = { ...playResponse(request), play_context: base };
      if (mode === 'note') base.receipt.play_basis.scene_note += ' changed';
      if (mode === 'text') response.answer.text = 'An uncommitted answer';
      if (mode === 'mixed' || mode.startsWith('unclaimed')) {
        const f = mode === 'mixed' ? rulesAnswerFixture(base) : rulesUnclaimedFixture(base), b = f.context.accepted_binding;
        const row = { ...turn('play', 1, f.answer), schema: 'dmb_agent_conversation_history_mixed_turn_v1' as const,
          turn_id: b.turn_id, user_text: request.message, idempotency_key: '66666666-6666-4666-8666-666666666666',
          provenance: nativePlayProvenanceFixture(base), rules_context: f.context };
        if (mode === 'mixed' || mode === 'unclaimed') vi.mocked(getWorldAgentConversationHistory).mockResolvedValue({ ...history(), schema: 'dmb_agent_conversation_history_v4',
          conversation_id: b.conversation_id, active_conversation_id: b.conversation_id, turns: [row] });
        const { play_context: _unusedNativeContext, ...mixedResponse } = response;
        return { ...mixedResponse, schema: 'dmb_agent_rules_turn_response_v1',
          conversation: { ...response.conversation, conversation_id: b.conversation_id },
          answer: { ...response.answer, text: f.answer }, rules_context: f.context };
      }
      if (mode === 'ordinary') vi.mocked(getWorldAgentConversationHistory).mockResolvedValue({ ...history(), schema: 'dmb_agent_conversation_history_v2',
        turns: [{ ...turn('play', 1, response.answer.text), turn_id: request.turn_id, user_text: request.message,
          play_context: base, provenance: nativePlayProvenanceFixture(base) }] });
      return response;
    });
    render(<Harness initial='play' />);
    fireEvent.click(await screen.findByRole('button', { name: 'Open' }));
    const composer = await screen.findByLabelText('Message DungeonBuddy');
    await waitFor(() => expect(composer).toBeEnabled());
    fireEvent.change(composer, { target: { value: 'What rules apply at this crossing?' } });
    fireEvent.click(screen.getByRole('button', { name: 'Send message' }));
    const key = 'dmb:world-play-pending-turn:v1:' + WORLD;
    if (mode === 'ordinary' || mode === 'mixed' || mode === 'unclaimed') {
      await waitFor(() => expect(window.localStorage.getItem(key)).toBeNull());
      if (mode !== 'unclaimed') await screen.findByText(/Original Play answer/);
      if (mode === 'mixed' || mode === 'unclaimed') await screen.findByText('Rules references', { selector: 'summary' });
    } else {
      await screen.findByText(/reply did not match.*(Run edition|accepted answer)/);
      expect(window.localStorage.getItem(key)).not.toBeNull();
      expect(screen.queryByText('An uncommitted answer')).not.toBeInTheDocument();
    }
    expect(postWorldPlayAgentTurn).toHaveBeenCalledTimes(1);
    expect(getHistoricalRulesPassage).not.toHaveBeenCalled();
  });

  it.each(['live','lost'] as const)('settles a Graph-off Plan Rules reply with the original saved Plan: %s', async mode => {
    const f = rulesAnswerFixture(), conversationId = f.context.accepted_binding.conversation_id;
    let current: WorldAgentConversationHistoryResponse = {...history(),conversation_id:conversationId,active_conversation_id:conversationId};
    vi.mocked(getWorldAgentConversationHistory).mockImplementation(async () => current);
    vi.mocked(postWorldPlanAgentTurn).mockImplementation(async request => {
      expect(request.graph_request).toEqual({mode:'none'});
      expect(request.plan_context_policy).toBeUndefined();
      const row = {...turn('plan',1,f.answer),schema:'dmb_agent_conversation_history_mixed_turn_v1' as const,
        turn_id:f.context.accepted_binding.turn_id,user_text:request.message,
        idempotency_key:await expectedHistoryCorrelationKey(WORLD,request.turn_id),rules_context:f.context,
        provenance:{...turn('plan',1,f.answer).provenance,primary_work:{resolution:'resolved' as const,kind:'plan',object_id:'plan-one',
          revision:'7',content_sha256:SHA,object_revision:7,work_revision_id:WORK_REVISION,revision_n:2}}};
      current = {...current,schema:'dmb_agent_conversation_history_v4',turns:[row]};
      if (mode === 'lost') throw new Error('Connection lost after accepted Plan Rules reply');
      const reply = planResponse(request);
      return {...reply,schema:'dmb_agent_rules_turn_response_v1',conversation:{...reply.conversation,conversation_id:conversationId},
        answer:{...reply.answer,text:f.answer},rules_context:f.context};
    });
    render(<Harness initial='plan' />);
    fireEvent.click(await screen.findByRole('button',{name:'Open'}));
    const composer = await screen.findByLabelText('Message DungeonBuddy');
    await waitFor(() => expect(composer).toBeEnabled());
    fireEvent.click(screen.getByRole('button',{name:'Use Test World facts · On'}));
    fireEvent.change(composer,{target:{value:'What occupancy rule applies?'}});
    fireEvent.click(screen.getByRole('button',{name:'Send message'}));
    await waitFor(() => expect(postWorldPlanAgentTurn).toHaveBeenCalledTimes(1));
    await waitFor(() => expect(Object.keys(localStorage).filter(k => k.startsWith('dmb:world-plan-pending-ask:v1:'))).toEqual([]),{timeout:7000});
    await screen.findByText(f.answer);
    expect(getHistoricalRulesPassage).not.toHaveBeenCalled();
  });

  it.each(['live','lost','ordinary','edition','scene','seal','note-body'] as const)('settles Graph-off Play only with its exact source identity: %s', async mode => {
    const seed = rulesAnswerFixture(), conversationId = seed.context.accepted_binding.conversation_id;
    let current: WorldAgentConversationHistoryResponse = { ...history(), conversation_id:conversationId, active_conversation_id:conversationId };
    vi.mocked(getWorldAgentConversationHistory).mockImplementation(async () => current);
    vi.mocked(postWorldPlayAgentTurn).mockImplementation(async request => {
      expect(request.graph_request).toEqual({mode:'none'});
      const sourceRequest = structuredClone(request);
      if (mode === 'edition') sourceRequest.primary_work.play_content_basis = {edition_revision:2,
        edition_revision_id:'00000000-0000-4000-8000-000000000044',content_sha256:'b'.repeat(64)};
      if (mode === 'scene') sourceRequest.play_target.scene_id = 'scene:other';
      const source = nativePlaySourceFixture(sourceRequest), f = rulesAnswerFixture();
      if (mode === 'seal') source.context.basis_sha256 = '0'.repeat(64);
      if (mode === 'note-body') Object.assign(source.context.basis,{scene_note:'Private note bytes must not be in this projection.'});
      const {play_context:_graph,...reply} = playResponse(request);
      const ordinary = mode === 'ordinary';
      if (mode === 'live' || mode === 'lost' || ordinary) {
        const row = { ...turn('play',1,ordinary ? 'Ordinary Graph-off answer' : f.answer),
          turn_id:f.context.accepted_binding.turn_id,user_text:request.message,
          provenance:source.provenance,idempotency_key:await expectedHistoryCorrelationKey(WORLD,request.turn_id),
          play_source_context:{...source.context,delivery_replay:true} };
        current = { ...current,schema:'dmb_agent_conversation_history_v4',turns:[ordinary
          ? {...row,schema:'dmb_agent_conversation_history_play_source_turn_v1'}
          : {...row,schema:'dmb_agent_conversation_history_play_rules_turn_v1',lifecycle_status:'completed',assistant_text:f.answer,rules_context:f.context}] };
      }
      if (mode === 'lost') throw new Error('Connection lost after accepted Graph-off Play answer');
      const common = {...reply,conversation:{...reply.conversation,conversation_id:conversationId},play_source_context:source.context};
      return ordinary ? {...common,schema:'dmb_agent_play_source_turn_response_v1',answer:{...reply.answer,text:'Ordinary Graph-off answer'}}
        : {...common,schema:'dmb_agent_play_rules_turn_response_v1',answer:{...reply.answer,text:f.answer},rules_context:f.context};
    });
    render(<Harness initial='play' />);
    fireEvent.click(await screen.findByRole('button',{name:'Open'}));
    const composer = await screen.findByLabelText('Message DungeonBuddy');
    await waitFor(() => expect(composer).toBeEnabled());
    if (!screen.queryByRole('button',{name:'Use Test World facts · On'})) {
      openConversationOptions();
      fireEvent.click(screen.getByRole('button',{name:/^Show .*Play/}));
    }
    fireEvent.click(screen.getByRole('button',{name:'Use Test World facts · On'}));
    fireEvent.change(composer,{target:{value:'What occupancy rule applies?'}});
    fireEvent.click(screen.getByRole('button',{name:'Send message'}));
    const pendingKey = 'dmb:world-play-pending-turn:v1:'+WORLD;
    await waitFor(() => expect(postWorldPlayAgentTurn).toHaveBeenCalledTimes(1));
    if (mode === 'live' || mode === 'lost' || mode === 'ordinary') {
      await waitFor(() => expect(localStorage.getItem(pendingKey)).toBeNull(),{timeout:7000});
      await screen.findByText(mode === 'ordinary' ? 'Ordinary Graph-off answer' : fText());
      fireEvent.change(composer,{target:{value:'Keep this next thought'}});
      expect(composer).toHaveValue('Keep this next thought');
    } else {
      await screen.findByText(/reply did not match the saved Run edition/);
      expect(localStorage.getItem(pendingKey)).not.toBeNull();
    }
    expect(getHistoricalRulesPassage).not.toHaveBeenCalled();
    function fText() { return seed.answer; }
  });

  it.each(['live', 'lost', 'foreign-work', 'lost-foreign-work'] as const)('settles unclaimed Plan Rules replies only with the original frozen receipt: %s', async mode => {
    const seed = rulesAnswerFixture();
    let current: WorldAgentConversationHistoryResponse = { ...history(), conversation_id: seed.context.accepted_binding.conversation_id,
      active_conversation_id: seed.context.accepted_binding.conversation_id };
    vi.mocked(getWorldAgentConversationHistory).mockImplementation(async () => current);
    vi.mocked(postWorldPlanAgentTurn).mockImplementation(async request => {
      const base = await planGraphContext('plan_only_graph_unused', { request });
      if (mode.includes('foreign-work')) {
        base.receipt.plan_basis.work_revision_id = '00000000-0000-4000-8000-000000000099';
        const { context_receipt_sha256: _, ...body } = base.receipt;
        base.receipt.context_receipt_sha256 = fixtureHash(rulesCanonical(body));
      }
      const f = rulesUnclaimedFixture(base), b = f.context.accepted_binding;
      if (mode.startsWith('lost')) {
        const row = { ...turn('plan', 1, f.answer), schema: 'dmb_agent_conversation_history_mixed_turn_v1' as const,
          turn_id: b.turn_id, idempotency_key: await expectedHistoryCorrelationKey(WORLD, request.turn_id),
          user_text: request.message, rules_context: f.context,
          provenance: { ...turn('plan', 1, f.answer).provenance,
            primary_work: { resolution: 'resolved' as const, kind: 'plan', object_id: 'plan-one', revision: '7', content_sha256: SHA,
              object_revision: 7, work_revision_id: base.receipt.plan_basis.work_revision_id, revision_n: 2 } } };
        current = { ...current, schema: 'dmb_agent_conversation_history_v4', turns: [row] };
        throw new Error('Connection lost after the accepted Rules answer');
      }
      const response = planResponse(request);
      return { ...response, schema: 'dmb_agent_rules_turn_response_v1',
        conversation: { ...response.conversation, conversation_id: b.conversation_id },
        answer: { ...response.answer, text: f.answer }, rules_context: f.context };
    });
    render(<Harness initial='plan' />);
    fireEvent.click(await screen.findByRole('button', { name: 'Open' }));
    const composer = await screen.findByLabelText('Message DungeonBuddy');
    await waitFor(() => expect(composer).toBeEnabled());
    fireEvent.change(composer, { target: { value: 'What occupancy rules apply here?' } });
    fireEvent.click(screen.getByRole('button', { name: 'Send message' }));
    await waitFor(() => expect(postWorldPlanAgentTurn).toHaveBeenCalledTimes(1));
    const pending = () => Object.keys(localStorage).filter(k => k.startsWith('dmb:world-plan-pending-ask:v1:'));
    if (mode === 'live' || mode === 'lost') {
      await waitFor(() => expect(pending()).toHaveLength(0), { timeout: 7000 });
    } else {
      if (mode.startsWith('lost')) await screen.findByText(seed.ruleText, {}, { timeout: 7000 });
      else await screen.findByText(/durable Ask result did not identify/);
      expect(pending()).toHaveLength(1);
    }
    expect(getHistoricalRulesPassage).not.toHaveBeenCalled();
    expect(postWorldPlanAgentTurn).toHaveBeenCalledTimes(1);
  });

  it('serializes composer references and reopens the exact pending snapshot after reload',async()=>{
    const original=authoredGraphReferences([authoredRef('original-box')]);
    writeComposerReferences(sessionStorage,WORLD,'source-one',null,original.references);
    vi.mocked(getWorldAgentConversationHistory).mockResolvedValue(history());
    let reject!:(reason:unknown)=>void;
    vi.mocked(postWorldBuildAgentTurn).mockReturnValueOnce(new Promise((_,r)=>{reject=r})).mockReturnValue(new Promise(()=>{}));
    const mounted=render(<Harness initial="build" buildBridge={retryBridge()}/>);
    fireEvent.click(await screen.findByRole('button',{name:'Open',exact:true}));
    const input=await screen.findByLabelText('Message DungeonBuddy');
    expect(within(screen.getByLabelText('Message Graph context')).getByText('@original-box')).toBeVisible();
    fireEvent.change(input,{target:{value:'Discuss the selected box.'}});fireEvent.click(screen.getByRole('button',{name:'Send message'}));
    await waitFor(()=>expect(postWorldBuildAgentTurn).toHaveBeenCalledTimes(1));
    const request=vi.mocked(postWorldBuildAgentTurn).mock.calls[0][0];expect(request.build_authored_references).toEqual(original);
    const key=`dmb:world-play-pending-turn:v1:${encodeURIComponent(WORLD)}`,pending=localStorage.getItem(key);
    expect(pending).not.toBeNull();expect(JSON.parse(pending!).request.build_authored_references).toEqual(original);
    fireEvent.change(input,{target:{value:'Keep my newer draft'}});
    await act(async()=>reject(new LiveApiError('Session changed',401,{code:'local_graph_session_changed'})));
    const draft=readComposerReferences(sessionStorage,WORLD,'source-one');
    writeComposerReferences(sessionStorage,WORLD,'source-one',draft.serialized,[authoredRef('newer-box')]);
    mounted.unmount();render(<Harness initial="build" buildBridge={retryBridge()}/>);
    fireEvent.click(await screen.findByRole('button',{name:'Open',exact:true}));
    expect(await screen.findByLabelText('Message DungeonBuddy')).toHaveValue('Keep my newer draft');
    expect(screen.getByText('@newer-box')).toBeVisible();openConversationOptions();
    fireEvent.click(await screen.findByRole('button',{name:'Retry exact saved turn'}));
    await waitFor(()=>expect(postWorldBuildAgentTurn).toHaveBeenCalledTimes(2));
    expect(vi.mocked(postWorldBuildAgentTurn).mock.calls[1][0]).toEqual(request);
    expect(readComposerReferences(sessionStorage,WORLD,'source-one').references[0].node_id).toBe('newer-box');
  });

  it('retries from the saved V2 references while preserving unrelated composer references',async()=>{
    const base=turn('plan',1,''),id='22222222-2222-4222-8222-000000000001',cid=history().conversation_id!;
    const frozen=authoredGraphReferences([authoredRef('failed-box')]);
    const terminal={...base,turn_id:id,lifecycle_status:'interrupted' as const,provenance:{...base.provenance,surface_id:'build',primary_work:{...base.provenance.primary_work,kind:'build',object_id:'source-one'}},retry_context:{schema:'dmb_turn_retry_context_row_v2' as const,authored_references:frozen,world_id:WORLD,conversation_id:cid,turn_id:id,revision:4,root_id:id,predecessor_id:null,successor_id:null,ordinal:0,eligible:true,reason:'ready' as const}};
    vi.mocked(getWorldAgentConversationHistory).mockResolvedValue(history([terminal]));
    vi.mocked(postWorldBuildAgentTurn).mockReturnValue(new Promise(()=>{}));
    const newer=writeComposerReferences(sessionStorage,WORLD,'source-one',null,[authoredRef('newer-box')]);
    render(<Harness initial="build" buildBridge={retryBridge()}/>);fireEvent.click(await screen.findByRole('button',{name:'Open',exact:true}));
    fireEvent.change(await screen.findByLabelText('Message DungeonBuddy'),{target:{value:'My newer note'}});
    fireEvent.click(await screen.findByRole('button',{name:'Retry question'}));
    await waitFor(()=>expect(postWorldBuildAgentTurn).toHaveBeenCalledTimes(1));
    expect(vi.mocked(postWorldBuildAgentTurn).mock.calls[0][0]).toMatchObject({retry_of:{turn_id:id,revision:4},build_authored_references:frozen,message:base.user_text});
    expect(screen.getByLabelText('Message DungeonBuddy')).toHaveValue('My newer note');
    expect(readComposerReferences(sessionStorage,WORLD,'source-one')).toEqual(newer);
  });

  it.each(['references','text'])('preserves a deliberate empty composer selection after newer %s edits and rejection',async kind=>{
    const node={nodeId:'newer-box',label:'newer-box',kind:'object',role:'match',aliases:[],sourceDomains:[],anchoredToFocusSession:false,evidenceBadges:[],adjacency:[],suggestedExpansions:[],evidenceRefIds:[],sourceArtifactIds:[]};
    const snapshot={worldId:'native',campaignId:'',revisionId:'selected-revision',headRevisionId:'selected-revision',isHead:true,focus:{kind:'none',sessionId:null},admissibility:'gm',scopeMode:'world'};
    const spy=vi.spyOn(graphLensProjection,'useOptionalWorldGraphLensProjection').mockReturnValue({request:null,requestKey:'managed-world',projectionState:'ready',projectionError:null,nodeCount:1,lastProjectionLoadMs:0,lastProjectionLoadOutcome:'ready',managedBinding:{managedWorldId:WORLD,nativeWorldId:'native',bindingVersion:1},projection:{schema:'dmb_world_graph_projection_v1',snapshot,nodes:[node],relationships:[],attributes:[],evidence:[],sourceArtifacts:[],diagnostics:[],summary:{nodeCount:1,relationshipCount:0,attributeCount:0,evidenceCount:0,sourceArtifactCount:0,projectionTruncated:false}}} as ReturnType<typeof graphLensProjection.useOptionalWorldGraphLensProjection>);
    try{
      const original=authoredGraphReferences([authoredRef('original-box')]);writeComposerReferences(sessionStorage,WORLD,'source-one',null,original.references);
      vi.mocked(getWorldAgentConversationHistory).mockResolvedValue(history());let reject!:(reason:unknown)=>void;
      vi.mocked(postWorldBuildAgentTurn).mockReturnValue(new Promise((_,r)=>{reject=r}));
      render(<Harness initial="build" buildBridge={retryBridge()}/>);fireEvent.click(await screen.findByRole('button',{name:'Open',exact:true}));
      const input=await screen.findByLabelText('Message DungeonBuddy');fireEvent.change(input,{target:{value:'Discuss the original box.'}});fireEvent.click(screen.getByRole('button',{name:'Send message'}));
      await waitFor(()=>expect(postWorldBuildAgentTurn).toHaveBeenCalledTimes(1));
      const request=vi.mocked(postWorldBuildAgentTurn).mock.calls[0][0];expect(readComposerReferences(sessionStorage,WORLD,'source-one').submittedTurnId).toBe(request.turn_id);
      if(kind==='references'){
        const composer=within(screen.getByLabelText('Message Graph context'));
        fireEvent.click(composer.getByRole('button',{name:'@ Reference'}));fireEvent.click(composer.getByRole('button',{name:'Use as context'}));
        fireEvent.click(composer.getByRole('button',{name:'Remove reference newer-box'}));
      }else{fireEvent.change(input,{target:{value:'A newer thought'}});fireEvent.change(input,{target:{value:''}});}
      const cleared=readComposerReferences(sessionStorage,WORLD,'source-one');expect(cleared.references).toEqual([]);expect(cleared.submittedTurnId).toBeNull();
      await act(async()=>reject(new LiveApiError('Source context changed',422,{code:'build_editor_context_changed'})));
      expect(readComposerReferences(sessionStorage,WORLD,'source-one')).toEqual(cleared);expect(input).toHaveValue('');
      await waitFor(()=>expect(localStorage.getItem(`dmb:world-play-pending-turn:v1:${WORLD}`)).toBeNull());expect(rejectedReferenceCopies()).toHaveLength(1);expect(postWorldBuildAgentTurn).toHaveBeenCalledTimes(1);
      fireEvent.change(input,{target:{value:'A new independent draft.'}});expect(screen.getByRole('button',{name:'Send message'})).toBeEnabled();
      vi.mocked(postWorldBuildAgentTurn).mockReturnValue(new Promise(()=>{}));fireEvent.click(screen.getByRole('button',{name:'Send message'}));
      await waitFor(()=>expect(postWorldBuildAgentTurn).toHaveBeenCalledTimes(2));const next=vi.mocked(postWorldBuildAgentTurn).mock.calls[1][0];
      expect(next.message).toBe('A new independent draft.');expect(next.turn_id).not.toBe(request.turn_id);expect(next.build_authored_references).toBeUndefined();expect(rejectedReferenceCopies()).toHaveLength(1);
    }finally{spy.mockRestore();}
  });

  it('restores a rejected request only while its exact submission marker owns the composer',async()=>{
    const original=authoredGraphReferences([authoredRef('original-box')]);writeComposerReferences(sessionStorage,WORLD,'source-one',null,original.references);
    vi.mocked(getWorldAgentConversationHistory).mockResolvedValue(history());let reject!:(reason:unknown)=>void;
    vi.mocked(postWorldBuildAgentTurn).mockReturnValue(new Promise((_,r)=>{reject=r}));
    render(<Harness initial="build" buildBridge={retryBridge()}/>);fireEvent.click(await screen.findByRole('button',{name:'Open',exact:true}));
    const input=await screen.findByLabelText('Message DungeonBuddy');fireEvent.change(input,{target:{value:'Discuss the original box.'}});fireEvent.click(screen.getByRole('button',{name:'Send message'}));
    await waitFor(()=>expect(postWorldBuildAgentTurn).toHaveBeenCalledTimes(1));
    await act(async()=>reject(new LiveApiError('Source context changed',422,{code:'build_editor_context_changed'})));
    await waitFor(()=>expect(input).toHaveValue('Discuss the original box.'));
    expect(readComposerReferences(sessionStorage,WORLD,'source-one').references).toEqual(original.references);expect(readComposerReferences(sessionStorage,WORLD,'source-one').submittedTurnId).toBeNull();
    expect(localStorage.getItem(`dmb:world-play-pending-turn:v1:${WORLD}`)).toBeNull();expect(within(screen.getByLabelText('Message Graph context')).getByText('@original-box')).toBeVisible();
  });

  it.each(['mounted','remounted'])('refuses automatic restoration after failed marker retirement: %s',async mode=>{
    const original=authoredGraphReferences([authoredRef('original-box')]);writeComposerReferences(sessionStorage,WORLD,'source-one',null,original.references);
    vi.mocked(getWorldAgentConversationHistory).mockResolvedValue(history());let reject!:(reason:unknown)=>void;
    vi.mocked(postWorldBuildAgentTurn).mockImplementation(()=>new Promise((_,r)=>{reject=r}));
    const mounted=render(<Harness initial="build" buildBridge={retryBridge()}/>);fireEvent.click(await screen.findByRole('button',{name:'Open',exact:true}));
    let input=await screen.findByLabelText('Message DungeonBuddy');fireEvent.change(input,{target:{value:'Discuss the original box.'}});fireEvent.click(screen.getByRole('button',{name:'Send message'}));
    await waitFor(()=>expect(postWorldBuildAgentTurn).toHaveBeenCalledTimes(1));
    const request=vi.mocked(postWorldBuildAgentTurn).mock.calls[0][0],before=readComposerReferences(sessionStorage,WORLD,'source-one');
    expect(before.submittedTurnId).toBe(request.turn_id);
    const write=Storage.prototype.setItem;
    const spy=vi.spyOn(Storage.prototype,'setItem').mockImplementation(function(key,value){if(key===composerReferenceKey(WORLD,'source-one'))throw new DOMException('Storage write denied','QuotaExceededError');return write.call(this,key,value)});
    try{
      fireEvent.change(input,{target:{value:'A newer thought'}});fireEvent.change(input,{target:{value:''}});
      expect(readComposerReferences(sessionStorage,WORLD,'source-one')).toEqual(before);
      if(mode==='remounted'){
        await act(async()=>reject(new LiveApiError('Session changed',401,{code:'local_graph_session_changed'})));
        mounted.unmount();render(<Harness initial="build" buildBridge={retryBridge()}/>);fireEvent.click(await screen.findByRole('button',{name:'Open',exact:true}));
        input=await screen.findByLabelText('Message DungeonBuddy');openConversationOptions();fireEvent.click(await screen.findByRole('button',{name:'Retry exact saved turn'}));
        await waitFor(()=>expect(postWorldBuildAgentTurn).toHaveBeenCalledTimes(2));
      }
      await act(async()=>reject(new LiveApiError('Source context changed',422,{code:'build_editor_context_changed'})));
      expect(input).toHaveValue('');expect(readComposerReferences(sessionStorage,WORLD,'source-one')).toEqual(before);
      await waitFor(()=>expect(localStorage.getItem(`dmb:world-play-pending-turn:v1:${WORLD}`)).toBeNull());expect(rejectedReferenceCopies()).toHaveLength(1);
      expect(within(screen.getByLabelText('Message Graph context')).queryByText('@original-box')).toBeNull();
      expect(postWorldBuildAgentTurn).toHaveBeenCalledTimes(mode==='mounted'?1:2);
    }finally{spy.mockRestore();}
  });

  it.each(['unknown','receipt-write','cleanup-crash','changed-pending'])('preserves rejected recovery at the actual storage boundary: %s',async mode=>{
    writeComposerReferences(sessionStorage,WORLD,'source-one',null,[authoredRef('original-box')]);
    vi.mocked(getWorldAgentConversationHistory).mockResolvedValue(history());let reject!:(reason:unknown)=>void;
    vi.mocked(postWorldBuildAgentTurn).mockReturnValue(new Promise((_,r)=>{reject=r}));
    const mounted=render(<Harness initial="build" buildBridge={retryBridge()}/>);fireEvent.click(await screen.findByRole('button',{name:'Open',exact:true}));
    const input=await screen.findByLabelText('Message DungeonBuddy');fireEvent.change(input,{target:{value:'Original box request.'}});fireEvent.click(screen.getByRole('button',{name:'Send message'}));
    await waitFor(()=>expect(postWorldBuildAgentTurn).toHaveBeenCalledTimes(1));
    const pendingKey=`dmb:world-play-pending-turn:v1:${WORLD}`,original=localStorage.getItem(pendingKey)!;
    fireEvent.change(input,{target:{value:'Newer independent note.'}});
    const write=Storage.prototype.setItem,remove=Storage.prototype.removeItem;
    const altered=JSON.stringify({...JSON.parse(original),request:{...JSON.parse(original).request,message:'Another tab request.'}});
    const spy=mode==='receipt-write'||mode==='changed-pending'?vi.spyOn(Storage.prototype,'setItem').mockImplementation(function(key,value){
      if(key.startsWith('dmb:rejected-authored-build:v1:')){
        if(mode==='receipt-write')throw new DOMException('Archive denied','QuotaExceededError');
        write.call(this,key,value);write.call(this,pendingKey,altered);return;
      }return write.call(this,key,value);
    }):mode==='cleanup-crash'?vi.spyOn(Storage.prototype,'removeItem').mockImplementation(function(key){if(key===pendingKey)throw new DOMException('Cleanup interrupted');return remove.call(this,key);}):null;
    try{
      await act(async()=>reject(mode==='unknown'?new LiveApiError('Unknown outcome',503,{code:'transport_unavailable'}):new LiveApiError('Source context changed',422,{code:'build_editor_context_changed'})));
      await screen.findByText(mode==='receipt-write'?/Archive denied/:mode==='changed-pending'?/The pending request changed. Both recovery copies were retained./:mode==='unknown'?'Unknown outcome Check World history or explicitly retry the saved request with its original IDs.':/^This message was not sent\./);
      expect(input).toHaveValue('Newer independent note.');expect(readComposerReferences(sessionStorage,WORLD,'source-one').references).toEqual([]);
      expect(localStorage.getItem(pendingKey)).toBe(mode==='changed-pending'?altered:original);
      expect(rejectedReferenceCopies()).toHaveLength(mode==='cleanup-crash'||mode==='changed-pending'?1:0);
      if(mode==='cleanup-crash'||mode==='changed-pending')expect(rejectedReferenceCopies()[0].original_bytes).toBe(original);
      if(mode==='changed-pending'){
        openConversationOptions();expect(await screen.findByLabelText('Retained rejected requests')).toHaveTextContent('Original box request.');expect(screen.getByLabelText('Saved turn recovery')).toHaveTextContent('Another tab request.');
        spy!.mockRestore();mounted.unmount();render(<Harness initial="build" buildBridge={retryBridge()}/>);fireEvent.click(await screen.findByRole('button',{name:'Open',exact:true}));
        openConversationOptions();expect(await screen.findByLabelText('Retained rejected requests')).toHaveTextContent('Original box request.');expect(screen.getByLabelText('Rejected request Graph context')).toHaveTextContent('@original-box');expect(screen.getByLabelText('Saved turn recovery')).toHaveTextContent('Another tab request.');
        expect(localStorage.getItem(pendingKey)).toBe(altered);expect(rejectedReferenceCopies()).toHaveLength(1);expect(postWorldBuildAgentTurn).toHaveBeenCalledTimes(1);
      }
      if(mode==='cleanup-crash'){
        spy!.mockRestore();mounted.unmount();const recovered=render(<Harness initial="build" buildBridge={retryBridge()}/>);fireEvent.click(await screen.findByRole('button',{name:'Open',exact:true}));
        await waitFor(()=>expect(localStorage.getItem(pendingKey)).toBeNull());expect(postWorldBuildAgentTurn).toHaveBeenCalledTimes(1);expect(rejectedReferenceCopies()).toHaveLength(1);
        openConversationOptions();expect(await screen.findByLabelText('Retained rejected requests')).toHaveTextContent('Original box request.');
        recovered.unmount();render(<Harness initial="build" buildBridge={retryBridge()}/>);fireEvent.click(await screen.findByRole('button',{name:'Open',exact:true}));
        expect(postWorldBuildAgentTurn).toHaveBeenCalledTimes(1);expect(rejectedReferenceCopies()).toHaveLength(1);
        fireEvent.change(await screen.findByLabelText('Message DungeonBuddy'),{target:{value:'Next independent request.'}});expect(screen.getByRole('button',{name:'Send message'})).toBeEnabled();
      }
    }finally{spy?.mockRestore();}
  });

  it('recovers unreadable composer references explicitly without replacing the message',async()=>{
    const key=composerReferenceKey(WORLD,'source-one'),raw='malformed reference draft';sessionStorage.setItem(key,raw);
    vi.mocked(getWorldAgentConversationHistory).mockResolvedValue(history());
    render(<Harness initial="build" buildBridge={retryBridge()}/>);fireEvent.click(await screen.findByRole('button',{name:'Open',exact:true}));
    const input=await screen.findByLabelText('Message DungeonBuddy');fireEvent.change(input,{target:{value:'Keep my newer words.'}});
    expect(postWorldBuildAgentTurn).not.toHaveBeenCalled();fireEvent.click(screen.getByRole('button',{name:'Retain unreadable copy and reset references'}));
    await waitFor(()=>expect(screen.queryByRole('button',{name:'Retain unreadable copy and reset references'})).toBeNull());
    expect(input).toHaveValue('Keep my newer words.');expect(readComposerReferences(sessionStorage,WORLD,'source-one').references).toEqual([]);expect(screen.getByRole('button',{name:'Send message'})).toBeEnabled();
    openConversationOptions();expect(await screen.findByLabelText('Retained reference drafts')).toHaveTextContent(raw);expect(postWorldBuildAgentTurn).not.toHaveBeenCalled();
  });

  it.each(['initial','crash-remount'])('recovers the exact rejected request despite an unrelated corrupt receipt: %s',async mode=>{
    const corruptKey=`dmb:rejected-authored-build:v1:${encodeURIComponent(WORLD)}:other-page:99999999-9999-4999-8999-999999999999`,corrupt='unreadable unrelated receipt';localStorage.setItem(corruptKey,corrupt);
    writeComposerReferences(sessionStorage,WORLD,'source-one',null,[authoredRef('original-box')]);
    vi.mocked(getWorldAgentConversationHistory).mockResolvedValue(history());let reject!:(reason:unknown)=>void;vi.mocked(postWorldBuildAgentTurn).mockReturnValue(new Promise((_,r)=>{reject=r}));
    const mounted=render(<Harness initial="build" buildBridge={retryBridge()}/>);fireEvent.click(await screen.findByRole('button',{name:'Open',exact:true}));
    const input=await screen.findByLabelText('Message DungeonBuddy');fireEvent.change(input,{target:{value:'Original selected object.'}});fireEvent.click(screen.getByRole('button',{name:'Send message'}));await waitFor(()=>expect(postWorldBuildAgentTurn).toHaveBeenCalledTimes(1));
    fireEvent.change(input,{target:{value:'Newer independent words.'}});const pendingKey=`dmb:world-play-pending-turn:v1:${WORLD}`,remove=Storage.prototype.removeItem;
    const spy=mode==='crash-remount'?vi.spyOn(Storage.prototype,'removeItem').mockImplementation(function(key){if(key===pendingKey)throw new Error('Interrupted cleanup');return remove.call(this,key);}):null;
    try{
      await act(async()=>reject(new LiveApiError('Source changed',422,{code:'build_editor_context_changed'})));await screen.findByText(/^This message was not sent\./);
      if(spy){expect(localStorage.getItem(pendingKey)).not.toBeNull();spy.mockRestore();mounted.unmount();render(<Harness initial="build" buildBridge={retryBridge()}/>);fireEvent.click(await screen.findByRole('button',{name:'Open',exact:true}));}
      await waitFor(()=>expect(localStorage.getItem(pendingKey)).toBeNull());expect(localStorage.getItem(corruptKey)).toBe(corrupt);expect(rejectedReferenceCopies()).toHaveLength(1);expect(postWorldBuildAgentTurn).toHaveBeenCalledTimes(1);
      fireEvent.change(await screen.findByLabelText('Message DungeonBuddy'),{target:{value:'Continue with the new draft.'}});expect(screen.getByRole('button',{name:'Send message'})).toBeEnabled();
      openConversationOptions();expect(await screen.findByLabelText('Retained rejected requests')).toHaveTextContent('Original selected object.');expect(screen.getByText(/1 retained rejection copy needs inspection/)).toBeVisible();
    }finally{spy?.mockRestore();}
  });

describe('first visible construction hands attention to the page',()=>{
 it.each(['prose','table','plan','newer-draft'] as const)('uses actual %s stream visibility without losing a newer composer',async(kind)=>{
  const editor=new Editor({extensions:DEFAULT_MARKDOWN_EDITOR_EXTENSIONS,content:'<p>Author page</p>'});
  const state:BuildComposeEditorState={editor,worldId:WORLD,documentId:'source-one',revision:2,contentSha256:SHA,visibility:'internal',draftGeneration:0,selectionGeneration:0,canEdit:true};
  const bridge=createBuildComposeBridge(()=>state,()=>undefined);
  const before=JSON.stringify(editor.getJSON());
  let emit!:(progress:BuildObjectConstructionProgress)=>void;
  vi.mocked(postWorldBuildAgentTurn).mockImplementation((_request,onProgress)=>{emit=onProgress!;return new Promise(()=>{});});
  const view=render(<Harness initial="build" buildBridge={bridge}/>);
  screen.getByRole('region',{name:'Build workspace'}).append(editor.view.dom);
  try{
   fireEvent.click(await screen.findByRole('button',{name:'Open',exact:true}));
   const input=await screen.findByLabelText('Message DungeonBuddy');await waitFor(()=>expect(input).toBeEnabled());
   fireEvent.change(input,{target:{value:'Write one proposed paragraph on this page.'}});
   fireEvent.click(screen.getByRole('button',{name:'Send message',exact:true}));
   await waitFor(()=>expect(postWorldBuildAgentTurn).toHaveBeenCalledTimes(1));
   const request=vi.mocked(postWorldBuildAgentTurn).mock.calls[0][0];const capability=request.build_write_capability!;
   if(kind==='newer-draft'){fireEvent.change(input,{target:{value:'Keep my newer thought'}});input.focus();}
   const prose={schema:'dmb_build_construction_v1' as const,action_id:capability.idempotency_key,reservation_sha256:SHA,
    conversation_id:capability.conversation_id,basis:capability.basis,origin:{client_turn_id:request.turn_id,durable_turn_id:'durable',turn_attempt:1,broker_operation_id:'op:1',arguments_sha256:SHA},provider_attempt_id:'provider',sequence:1,status:'building' as const,markdown:''};
   const plan={schema:'dmb_build_plan_construction_v2' as const,placement_id:'placement',basis:capability.basis,world_id:WORLD,
    conversation_id:capability.conversation_id,client_turn_id:request.turn_id,durable_turn_id:'durable',turn_attempt:1,working_snapshot_sha256:SHA,provider_attempt_id:'provider',sequence:1,status:'building' as const,objective:null,steps:[]};
   await act(async()=>emit(kind==='plan'?plan:prose));
   expect(screen.getByRole('button',{name:'Close conversation'})).toBeVisible();
   const filled=kind==='plan'?{...plan,sequence:2,objective:'Keep the wick dry.'}:kind==='table'?{...prose,sequence:2,markdown:'| Check |\n| --- |\n| Lid |\n'}:{...prose,sequence:2,markdown:'A covered box shelters the spare wick.'};
   await act(async()=>emit(filled));
   await screen.findByRole('region',{name:kind==='plan'?'Plan construction':'Object construction'});
   if(kind==='newer-draft'){
    expect(screen.getByRole('button',{name:'Close conversation'})).toBeVisible();expect(input).toHaveValue('Keep my newer thought');expect(input).toHaveFocus();
   }else{
    await waitFor(()=>expect(screen.queryByRole('button',{name:'Close conversation'})).not.toBeInTheDocument());
    fireEvent.click(screen.getByRole('button',{name:'Open',exact:true}));
    await act(async()=>emit({...filled,sequence:3}));
    expect(screen.getByRole('button',{name:'Close conversation'})).toBeVisible();
   }
   expect(JSON.stringify(editor.getJSON())).toBe(before);
  }finally{view.unmount();editor.destroy();}
 });
 it.each(['incomplete','stale'] as const)('does not close conversation for %s construction',async(kind)=>{
  const editor=new Editor({extensions:DEFAULT_MARKDOWN_EDITOR_EXTENSIONS,content:'<p>Author page</p>'});
  const state:BuildComposeEditorState={editor,worldId:WORLD,documentId:'source-one',revision:2,contentSha256:SHA,visibility:'internal',draftGeneration:0,selectionGeneration:0,canEdit:true};
  const bridge=createBuildComposeBridge(()=>state,()=>undefined);let emit!:(progress:BuildObjectConstructionProgress)=>void;
  vi.mocked(postWorldBuildAgentTurn).mockImplementation((_request,onProgress)=>{emit=onProgress!;return new Promise(()=>{});});
  const view=render(<Harness initial="build" buildBridge={bridge}/>);screen.getByRole('region',{name:'Build workspace'}).append(editor.view.dom);
  try{
   fireEvent.click(await screen.findByRole('button',{name:'Open',exact:true}));const input=await screen.findByLabelText('Message DungeonBuddy');await waitFor(()=>expect(input).toBeEnabled());
   fireEvent.change(input,{target:{value:'Write one proposed paragraph on this page.'}});fireEvent.click(screen.getByRole('button',{name:'Send message',exact:true}));
   await waitFor(()=>expect(postWorldBuildAgentTurn).toHaveBeenCalledTimes(1));const request=vi.mocked(postWorldBuildAgentTurn).mock.calls[0][0];const cap=request.build_write_capability!;
   if(kind==='stale'){editor.commands.insertContent('New author writing');state.draftGeneration++;}
   await act(async()=>emit({schema:'dmb_build_construction_v1',action_id:cap.idempotency_key,reservation_sha256:SHA,conversation_id:cap.conversation_id,basis:cap.basis,
    origin:{client_turn_id:request.turn_id,durable_turn_id:'durable',turn_attempt:1,broker_operation_id:'op:1',arguments_sha256:SHA},provider_attempt_id:'provider',sequence:1,status:kind==='incomplete'?'incomplete':'building',markdown:'A proposed description.'}));
   if(kind==='incomplete')await screen.findByRole('region',{name:'Object construction'});
   expect(screen.getByRole('button',{name:'Close conversation'})).toBeVisible();
  }finally{view.unmount();editor.destroy();}
 });
});

});

function rejectedReferenceCopies(){return Object.keys(localStorage).filter(key=>key.startsWith('dmb:rejected-authored-build:v1:')).flatMap(key=>{try{return [JSON.parse(localStorage.getItem(key)!)];}catch{return [];}});}
