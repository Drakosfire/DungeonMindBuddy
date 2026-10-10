import { useMemo, useState } from "react";
import { webcrypto } from "node:crypto";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { getWorldAgentConversationHistory, getWorldOwnedPlanCommittedRevision, getWorldPlanDocumentEditActions, LiveApiError, postWorldAgentNewConversation, postWorldPlanAgentTurn, postWorldPlayAgentTurn, postWorldPlanDocumentEditProposal } from "../api/liveApi";
import type { AgentInteractionTurn, WorldAgentConversationHistoryResponseV1, WorldPlanAgentTurnRequestV1, WorldPlayAgentTurnRequestV1 } from "../api/types";
import { AgentInteractionChrome } from "./AgentInteractionChrome";
import { AgentInteractionProvider } from "./AgentInteractionProvider";
import { useAgentInteraction } from "./useAgentInteraction";
import { AskPluginSlotProvider } from "./AskPluginSlot";
import { usePublishAgentSurfaceContext } from "./usePublishAgentSurfaceContext";
import { WorldAgentConversation, WorldAgentConversationProvider, WorldPlanConversationRegistration, usePublishWorldPlayConversation } from "./WorldAgentConversation";
import type { CapturedWorldPlanEditTarget, WorldPlanEditBridge } from "../planSurface/agentEdit/planAgentEditProposal";

const selectedWorld = vi.hoisted(() => ({ id: "world-one" }));
vi.mock("../selectedWorld/SelectedWorldContext", () => ({
  useSelectedWorld: () => ({ kind: "managed", worldId: selectedWorld.id, name: "Test World", documentId: "plan-one" }),
}));
vi.mock("../api/liveApi", async (importOriginal) => ({
  ...(await importOriginal<typeof import("../api/liveApi")>()),
  getWorldAgentConversationHistory: vi.fn(),
  getWorldOwnedPlanCommittedRevision: vi.fn(),
  getWorldPlanDocumentEditActions: vi.fn(),
  postWorldAgentNewConversation: vi.fn(),
  postWorldPlanAgentTurn: vi.fn(),
  postWorldPlayAgentTurn: vi.fn(),
  postWorldPlanDocumentEditProposal: vi.fn(),
}));

const WORLD = "world-one";
const RUN = "run-one";
const SHA = "a".repeat(64);
const WORK_REVISION = "00000000-0000-4000-8000-000000000011";

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
function Harness({ initial = "plan", admitted = true, editBridge = null }: {
  initial?: "plan" | "play"; admitted?: boolean; editBridge?: WorldPlanEditBridge | null;
}) {
  const [surface, setSurface] = useState(initial);
  const [world, setWorld] = useState(WORLD);
  const [documentId, setDocumentId] = useState("plan-one");
  return <AgentInteractionProvider><AskPluginSlotProvider>
    <WorldAgentConversationProvider key={world} worldId={world}>
      <button type="button" onClick={() => setSurface(surface === "plan" ? "play" : "plan")}>Switch surface</button>
      <button type="button" onClick={() => setDocumentId("plan-two")}>Switch Plan document</button>
      <button type="button" onClick={() => { selectedWorld.id = "world-two"; setWorld("world-two"); }}>Switch World</button>
      <ProposalFixture />
      {surface === "plan" ? <PlanPublisher documentId={documentId} editBridge={editBridge} /> : <PlayPublisher admitted={admitted && world === WORLD} />}
      <AgentInteractionChrome />
      <WorldAgentConversation surface={surface} worldId={world} worldName="Test World" />
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
    graph: { status: "not_requested" as const, world_id: null, campaign_id: null, scope_mode: null,
      revision_id: null, focus: null, selection_node_id: null, selection_found: null, head_revision_id: null, is_head: null },
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

describe("one App-level World conversation host across Plan and Play", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    Object.defineProperty(globalThis, "crypto", { configurable: true, value: webcrypto });
    selectedWorld.id = WORLD;
    window.localStorage.clear();
    vi.mocked(getWorldAgentConversationHistory).mockResolvedValue(history([turn("plan", 1, "Original Plan answer")]));
    vi.mocked(getWorldOwnedPlanCommittedRevision).mockResolvedValue({
      schema_version: "dmb_workspace_committed_revision_v2", scope_mode: "world", world_id: WORLD,
      campaign_id: null, document_id: "plan-one", kind: "plan", status: "active", object_revision: 7,
      revision_n: 2, work_revision_id: WORK_REVISION, markdown: "# Plan", content_sha256: SHA,
      has_divergent_working_copy: false,
    } as Awaited<ReturnType<typeof getWorldOwnedPlanCommittedRevision>>);
    vi.mocked(getWorldPlanDocumentEditActions).mockResolvedValue({ schema_version: "dmb_world_plan_action_projection_v1",
      basis: { world_id: WORLD, document_id: "plan-one", object_revision: 7 }, actions: [] } as Awaited<ReturnType<typeof getWorldPlanDocumentEditActions>>);
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
        turn_id: playTurnId, assistant_text: phase === "pending" ? null : "Recovered Play answer",
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
    view.unmount();
    render(<Harness initial="plan" />);
    fireEvent.click(await screen.findByRole("button", { name: "Open" }));
    await waitFor(() => expect(screen.getByLabelText("Message DungeonBuddy")).toBeDisabled());
    expect(postWorldPlayAgentTurn).toHaveBeenCalledTimes(1);
    fireEvent.click(screen.getByRole("button", { name: "Retry exact Play turn" }));
    await waitFor(() => expect(postWorldPlayAgentTurn).toHaveBeenCalledTimes(2));
    expect(vi.mocked(postWorldPlayAgentTurn).mock.calls[1]?.[0]).toEqual(firstRequest);
    await waitFor(() => expect(screen.getByText("Retried Play answer")).toBeInTheDocument());
    await waitFor(() => expect(screen.getByLabelText("Message DungeonBuddy")).toBeEnabled());
    expect(screen.queryByRole("button", { name: "Retry exact Play turn" })).not.toBeInTheDocument();
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
    expect(screen.getByLabelText("Message DungeonBuddy")).toBeEnabled();
    expect(screen.queryByRole("button", { name: "Retry exact Play turn" })).not.toBeInTheDocument();
    expect(postWorldPlayAgentTurn).toHaveBeenCalledTimes(1);
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
    await waitFor(() => expect(screen.getByText("No messages yet. Ask about this Run.")).toBeInTheDocument());
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
      graph_request: { mode: "none" }, graph_selection: null });
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
