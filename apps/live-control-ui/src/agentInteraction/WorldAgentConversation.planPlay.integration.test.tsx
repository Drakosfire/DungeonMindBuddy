import { useMemo, useState } from "react";
import { webcrypto } from "node:crypto";
import { act, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { createWorkspaceDocument, getWorkspaceDocumentSnapshot, getWorldAgentConversationHistory, getWorldOwnedPlanCommittedRevision, getWorldPlanDocumentEditActions, listWorkspaceDocuments, listWorldContainers, LiveApiError, postWorldAgentNewConversation, postWorldPlanAgentTurn, postWorldPlayAgentTurn, postWorldBuildAgentTurn, postWorldGraphSourceAnchorRead, postWorldPlanDocumentEditProposal } from "../api/liveApi";
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

const selectedWorld = vi.hoisted(() => ({ id: "world-one" }));
vi.mock("../selectedWorld/SelectedWorldContext", async (importOriginal) => ({
  ...(await importOriginal<typeof import("../selectedWorld/SelectedWorldContext")>()),
  useSelectedWorld: () => ({ kind: "managed", worldId: selectedWorld.id, name: "Test World", documentId: "plan-one" }),
}));
vi.mock("../api/liveApi", async (importOriginal) => ({
  ...(await importOriginal<typeof import("../api/liveApi")>()),
  createWorkspaceDocument: vi.fn(),
  getWorkspaceDocumentSnapshot: vi.fn(),
  listWorkspaceDocuments: vi.fn(),
  listWorldContainers: vi.fn(),
  getWorldAgentConversationHistory: vi.fn(),
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
  return { schema: "dmb_agent_conversation_history_v1", world_id: WORLD,
    conversation_state: "active", conversation_id: "conversation-one", active_conversation_id: "conversation-one",
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
function PlayPublisher({ admitted }: { admitted: boolean }) {
  const context = useMemo(() => ({ surfaceId: "play" as const, label: "Play", campaignId: null,
    documentId: null, sessionNumber: null, ambientSummary: "World Run", sourceEnvelope: null }), []);
  const run = useMemo(() => admitted ? ({ worldId: WORLD, runId: RUN,
    runRevision: 3, surfaceInstanceId: "play-instance",
    beatTitle: "The Crossing", sceneTitle: "West Gate" }) : null, [admitted]);
  usePublishAgentSurfaceContext(context);
  usePublishWorldPlayConversation(run);
  return null;
}
function BuildPublisher({ admitted }: { admitted: boolean }) {
  const surface = useMemo(() => ({ surfaceId: "build" as const, label: "Build", campaignId: null,
    documentId: "source-one", sessionNumber: null, ambientSummary: "Saved source", sourceEnvelope: null }), []);
  const source = useMemo(() => admitted ? ({ worldId: WORLD, documentId: "source-one", revision: 2,
    contentSha256: SHA, surfaceInstanceId: "build-instance", title: "City of Mirathorn", dirty: true }) : null, [admitted]);
  usePublishAgentSurfaceContext(surface);
  return <DocumentConversationDock surface="build" contextLabel="City of Mirathorn" reader={<div>Build source projection</div>}>
    {hosts => <BuildHarnessBinding source={source} hosts={hosts} />}
  </DocumentConversationDock>;
}
function BuildHarnessBinding({source, hosts}: {source: SavedWorldBuildConversationContext | null; hosts: PlanConversationPresentationHosts}) {
  usePublishWorldBuildConversation(source, hosts);
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
      positions: [{ turnId: proposal.turnId, conversationId: "conversation-one", afterSequence: 1, ordinal: 1 }] }));
    agent.updateThread({ ...thread, worldPlanProposalHistory: "world_plan_proposals_v1", turns: [proposal] });
  }}>Seed Plan proposal</button>;
}
function NewerPendingFixture() {
  const state = useWorldAgentConversationState();
  return <><button type="button" onClick={() => state?.setPendingTurn({ surface: "plan", turnId: "newer-client-request" })}>Seed newer pending request</button>
    <button type="button" onClick={() => state?.setHistoryRefreshNonce(value => value + 1)}>Refresh shared history fixture</button></>;
}
function Harness({ initial = "plan", admitted = true, editBridge = null }: {
  initial?: "plan" | "play" | "build"; admitted?: boolean; editBridge?: WorldPlanEditBridge | null;
}) {
  const [surface, setSurface] = useState(initial);
  const [world, setWorld] = useState(WORLD);
  const [documentId, setDocumentId] = useState("plan-one");
  return <AgentInteractionProvider><AskPluginSlotProvider>
    <WorldAgentConversationProvider key={world} worldId={world}>
      <button type="button" onClick={() => setSurface(surface === "plan" ? "play" : "plan")}>Switch surface</button>
      <button type="button" onClick={() => setDocumentId("plan-two")}>Switch Plan document</button>
      <button type="button" onClick={() => { selectedWorld.id = "world-two"; setWorld("world-two"); }}>Switch World</button>
      <ProposalFixture /><NewerPendingFixture />
      {surface === "plan" ? <PlanPublisher documentId={documentId} editBridge={editBridge} /> : surface === "build" ? <BuildPublisher admitted={admitted && world === WORLD} /> : <PlayPublisher admitted={admitted && world === WORLD} />}
      <AgentInteractionChrome />
      <WorldAgentConversation surface={surface} worldId={world} worldName="Test World" />
    </WorldAgentConversationProvider>
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
  return {
    schema: "dmb_agent_turn_response_v1" as const, client_thread_id: request.client_thread_id, turn_id: request.turn_id,
    surface: { surface_id: "play", instance_id: "play-instance", status: "resolved" as const },
    owner_scope: { status: "resolved" as const, kind: "world" as const, owner_id: WORLD, name: "Test World" },
    primary_work: { status: "resolved" as const, kind: "run", object_id: RUN, revision_used: 3,
      expected_revision: 3, content_basis: null },
    client_work_state_reported: "saved_clean" as const,
    graph: request.graph_request.mode === "none"
      ? { status: "not_requested" as const, world_id: null, campaign_id: null, scope_mode: null,
        revision_id: null, focus: null, selection_node_id: null, selection_found: null, head_revision_id: null, is_head: null }
      : { status: "ready" as const, world_id: "native-world-one", campaign_id: "", scope_mode: "world" as const,
        revision_id: "native-revision-one", focus: { kind: "none" }, selection_node_id: null,
        selection_found: null, head_revision_id: "native-revision-one", is_head: true },
    conversation: { client_thread_id: request.client_thread_id, turn_id: request.turn_id,
      pointer_status: "accepted" as const, pointer_id: "pointer", conversation_id: "conversation-one" },
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
      pointer_status: "accepted" as const, pointer_id: "pointer", conversation_id: "conversation-one" },
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
    plan_context_policy: { schema: "dmb_plan_context_policy_v1" as const, policy: "auto_plan_world" as const },
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
  return { schema: "dmb_build_graph_context_response_v1", receipt, delivery_replay: false,
    execution: plan.execution, completion: { schema: "dmb_build_graph_completion_v1",
      context_receipt_sha256: receipt.context_receipt_sha256, answer_basis: "saved_source_plus_world_graph",
      answer_context_status: "graph_grounded", answer_segments: [claim], citation_map: {
        schema: "dmb_graph_citation_map_v2", context_receipt_sha256: receipt.context_receipt_sha256,
        entries: plan.completion!.citation_map!.entries.map(entry => ({ ...entry, source_read_ids: [] })),
      } },
    source_open_targets: [{ schema: "dmb_agent_evidence_anchor_open_target_v1", kind: "evidence_anchor",
      claim_id: claim.claim_id, source_artifact_id: "artifact-one", source_revision_id: "source-rev-one",
      managed_world_id: WORLD, native_world_id: receipt.graph_authority.native_world_id,
      binding_version: receipt.graph_authority.binding_version, scope_mode: "world", campaign_id: null,
      focus: {kind: "none", session_id: null, campaign_id: null}, admissibility: "gm",
      graph_revision: receipt.graph_authority.graph_revision, anchor_id: "anchor-one",
      evidence_ref_id: "evidence-internal-test", source_read_id: null, read_outcome: null }],
    evidence_anchor_statuses: [{schema: "dmb_agent_evidence_anchor_status_v1", claim_id: claim.claim_id,
      status: "available", target_count: 1}], related_recap_context_statuses: [],
  };
}

describe("one App-level World conversation host across Plan and Play", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    Object.defineProperty(globalThis, "crypto", { configurable: true, value: webcrypto });
    selectedWorld.id = WORLD;
    window.localStorage.clear();
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
    await screen.findByRole("region", { name: "Saved turn recovery" });
    expect(screen.getByRole("button", { name: "Retry exact saved turn" })).toBeEnabled();
    mounted.unmount();
    render(<Harness initial="build" />);
    fireEvent.click(await screen.findByRole("button", { name: "Open" }));
    await screen.findByRole("region", { name: "Saved turn recovery" });
    expect(screen.getByRole("button", { name: "Retry exact saved turn" })).toBeEnabled();
    expect(postWorldBuildAgentTurn).toHaveBeenCalledTimes(1);
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
    [409, "build_source_unavailable"], [413, "build_source_too_large"], [403, "graph_auth_required"],
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
    render(<Harness initial={surface} />);
    fireEvent.click(await screen.findByRole("button", {name: "Open"}));
    const input = await screen.findByLabelText("Message DungeonBuddy");
    await waitFor(() => expect(input).toBeEnabled());
    const options = screen.getByLabelText("Conversation options");
    expect(options).not.toHaveAttribute("open");
    fireEvent.change(input, {target: {value: "Help with this page"}});
    fireEvent.click(screen.getByRole("button", {name: "Send message"}));
    fireEvent.click(await screen.findByRole("button", {name: "Open Settings"}));
    expect(options).toHaveAttribute("open");
    expect(screen.getByRole("button", {name: "Connect local session"})).toBeVisible();
    fireEvent.click(screen.getByRole("button", {name: "Close connection settings"}));
    expect(screen.queryByRole("button", {name: "Connect local session"})).not.toBeInTheDocument();
  });

  it("keeps Build tools and keyboard help in Options and grows a compact composer", async () => {
    render(<Harness initial="build" />);
    fireEvent.click(await screen.findByRole("button", { name: "Open" }));
    const input = await screen.findByLabelText("Message DungeonBuddy");
    await waitFor(() => expect(input).toBeEnabled());
    expect(input).toHaveAttribute("rows", "1");
    expect(input).toHaveStyle({ height: "40px" });
    Object.defineProperty(input, "scrollHeight", { configurable: true, value: 120 });
    fireEvent.change(input, { target: { value: "First line\nSecond line\nThird line" } });
    expect(input).toHaveStyle({ height: "120px" });
    Object.defineProperty(input, "scrollHeight", { configurable: true, value: 20 });
    fireEvent.change(input, { target: { value: "" } });
    expect(input).toHaveStyle({ height: "40px" });
    const options = screen.getByLabelText("Conversation options");
    expect(options).toContainElement(screen.getByLabelText("Agent tools and access"));
    fireEvent.click(within(options).getByText("Conversation options", { selector: "summary" }));
    expect(within(options).getByText("World Graph and sources")).toBeVisible();
    expect(within(options).getByText("Generate images")).toBeVisible();
    expect(within(options).getByText(/Not exposed to this conversation/)).toBeVisible();
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
    const options = screen.getByLabelText("Conversation options");
    expect(options).toContainElement(screen.getByLabelText("Saved turn recovery"));
    expect(postWorldBuildAgentTurn).toHaveBeenCalledTimes(1);
    expect(screen.getByRole("button", { name: "Send message" })).toBeDisabled();
  });

  it.each(["correct", "wrong_hash", "wrong_key"] as const)("recovers Build using the durable correlation and exact source basis: %s", async scenario => {
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
    current = { ...history(), schema: "dmb_agent_conversation_history_v3", turns: [{
      ...turn("plan", 1, "Frank and Sara operate the Rocky Talkie."),
      turn_id: "00000000-0000-4000-8000-000000000055", user_text: submitted.message,
      idempotency_key: scenario === "wrong_key" ? "00000000-0000-4000-8000-000000000099" : await expectedHistoryCorrelationKey(WORLD, submitted.turn_id),
      provenance: { ...turn("plan", 1, "").provenance, surface_id: "build", surface_instance_id: "build-instance",
        primary_work: { resolution: "resolved", kind: "build", object_id: "source-one", revision: "2",
          content_sha256: scenario === "wrong_hash" ? "b".repeat(64) : SHA,
          object_revision: null, work_revision_id: null, revision_n: null } },
    }] };
    fireEvent.click(screen.getByRole("button", { name: "Refresh shared history fixture" }));
    await screen.findByText("Frank and Sara operate the Rocky Talkie.");
    if (scenario === "correct") await waitFor(() => expect(screen.getByLabelText("Message DungeonBuddy")).toBeEnabled());
    else expect(screen.getByLabelText("Message DungeonBuddy")).toBeDisabled();
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
    fireEvent.click(screen.getByRole("button", { name: /What Buddy sees/ }));
    expect(await screen.findByText(/Buddy uses the saved source “City of Mirathorn”/)).toBeVisible();
    const savedComposer = screen.getByLabelText("Message DungeonBuddy");
    await waitFor(() => expect(savedComposer).toBeEnabled());

    window.history.pushState({}, "", `/build?world=${WORLD}`);
    fireEvent(window, new PopStateEvent("popstate"));
    await screen.findByTestId("build-surface-empty");
    fireEvent.click(screen.getByRole("button", { name: /What Buddy sees/ }));
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
    expect(screen.getByText("Test World · Play · The Crossing · West Gate")).toBeInTheDocument();
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

  it("reconciles an uncertain Play turn after switching to Plan without reposting it", async () => {
    let phase: "initial" | "pending" | "completed" = "initial";
    let playTurnId = "";
    vi.mocked(getWorldAgentConversationHistory).mockImplementation(async () => history([
      turn("plan", 1, "Original Plan answer"),
      ...(phase === "initial" ? [] : [{ ...turn("play", 2, "Recovered Play answer"),
        turn_id: playTurnId, user_text: "What happens next?", assistant_text: phase === "pending" ? null : "Recovered Play answer",
        lifecycle_status: phase === "pending" ? "pending" as const : "completed" as const }]),
    ]));
    vi.mocked(postWorldPlayAgentTurn).mockImplementation(async (request) => {
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
    await waitFor(() => expect(screen.getByLabelText("Message DungeonBuddy")).toBeDisabled());
    phase = "completed";
    await waitFor(() => expect(screen.getByText("Recovered Play answer")).toBeInTheDocument(), { timeout: 7000 });
    await waitFor(() => expect(screen.getByLabelText("Message DungeonBuddy")).toBeEnabled());
    expect(screen.queryByText(/Connection lost after submit/)).not.toBeInTheDocument();
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
    view.unmount();
    render(<Harness initial="plan" />);
    fireEvent.click(await screen.findByRole("button", { name: "Open" }));
    await waitFor(() => expect(screen.getByLabelText("Message DungeonBuddy")).toBeDisabled());
    expect(postWorldPlayAgentTurn).toHaveBeenCalledTimes(1);
    expect(window.localStorage.getItem(storageKey)).toBe(frozen);
    fireEvent.click(screen.getByRole("button", { name: "Retry exact saved turn" }));
    await waitFor(() => expect(postWorldPlayAgentTurn).toHaveBeenCalledTimes(2));
    expect(vi.mocked(postWorldPlayAgentTurn).mock.calls[1]?.[0]).toEqual(firstRequest);
    expect(JSON.stringify(vi.mocked(postWorldPlayAgentTurn).mock.calls[1]?.[0])).toBe(JSON.stringify(firstRequest));
    await waitFor(() => expect(screen.getByText("Retried Play answer")).toBeInTheDocument());
    await waitFor(() => expect(screen.getByLabelText("Message DungeonBuddy")).toBeEnabled());
    expect(screen.queryByRole("button", { name: "Retry exact saved turn" })).not.toBeInTheDocument();
  });

  it("recovers an actual saved legacy graphless Play turn without changing its request", async () => {
    const request: WorldPlayAgentTurnRequestV1 = {
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
    const retry = await screen.findByRole("button", { name: "Retry exact saved turn" });
    expect(window.localStorage.getItem(storageKey)).toBe(serialized);
    fireEvent.click(retry);
    await waitFor(() => expect(postWorldPlayAgentTurn).toHaveBeenCalledWith(request));
    await waitFor(() => expect(window.localStorage.getItem(storageKey)).toBeNull());
  });

  it("accepts a replayed native Graph receipt for a saved managed World Play request", async () => {
    const request: WorldPlayAgentTurnRequestV1 = {
      schema: "dmb_agent_turn_request_v1",
      client_thread_id: "00000000-0000-4000-8000-000000000031",
      turn_id: "00000000-0000-4000-8000-000000000032",
      surface: { surface_id: "play", instance_id: "play-instance" },
      owner_scope: { kind: "world", world_id: WORLD },
      primary_work: { kind: "run", object_id: RUN, expected_revision: 3 },
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

  it("uses the compact dock, latest exchange and conversation options in Play", async () => {
    vi.mocked(getWorldAgentConversationHistory).mockResolvedValue(history([
      turn("plan", 1, "Older Plan answer"), turn("play", 2, "Latest Play answer"),
    ]));
    render(<Harness initial="play" />);
    fireEvent.click(await screen.findByRole("button", { name: "Open" }));
    expect(await screen.findByText("Latest Play answer")).toBeInTheDocument();
    expect(screen.getByText("Older Plan answer")).not.toBeVisible();
    fireEvent.click(screen.getByText("Earlier conversation · 1"));
    expect(screen.getByText("Older Plan answer")).toBeInTheDocument();
    expect(screen.getByRole("log", { name: "Conversation messages" })).toBeInTheDocument();
    fireEvent.click(screen.getByText("Conversation options"));
    expect(screen.getByRole("button", { name: "Settings" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "New conversation" })).toBeInTheDocument();
  });

  it("starts a World conversation from Play with the same saved-command path", async () => {
    vi.mocked(postWorldAgentNewConversation).mockImplementation(async (worldId, request) => {
      vi.mocked(getWorldAgentConversationHistory).mockResolvedValue({ ...history(),
        conversation_id: "conversation-two", active_conversation_id: "conversation-two", pointer_revision: 2 });
      return { schema: "dmb_agent_new_conversation_response_v1", world_id: worldId,
        conversation_id: "conversation-two", active_conversation_id: "conversation-two", pointer_revision: request.expected_pointer_revision + 1 };
    });
    render(<Harness initial="play" />);
    fireEvent.click(await screen.findByRole("button", { name: "Open" }));
    await screen.findByText("Original Plan answer");
    fireEvent.click(screen.getByText("Conversation options"));
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

  it("clears a draft when the saved Plan document changes within the World", async () => {
    render(<Harness />);
    fireEvent.click(await screen.findByRole("button", { name: "Open" }));
    const composer = await screen.findByLabelText("Message DungeonBuddy");
    fireEvent.change(composer, { target: { value: "Rewrite this Plan scene" } });
    fireEvent.click(screen.getByRole("button", { name: "Switch Plan document" }));
    await waitFor(() => expect(screen.getByLabelText("Message DungeonBuddy")).toHaveValue(""));
    expect(postWorldPlanAgentTurn).not.toHaveBeenCalled();
  });
});
