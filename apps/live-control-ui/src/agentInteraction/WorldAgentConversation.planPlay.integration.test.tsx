import { useMemo, useState } from "react";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { getWorldAgentConversationHistory, getWorldOwnedPlanCommittedRevision, getWorldPlanDocumentEditActions, postWorldPlanAgentTurn, postWorldPlayAgentTurn } from "../api/liveApi";
import type { WorldAgentConversationHistoryResponseV1, WorldPlanAgentTurnRequestV1, WorldPlayAgentTurnRequestV1 } from "../api/types";
import { AgentInteractionChrome } from "./AgentInteractionChrome";
import { AgentInteractionProvider } from "./AgentInteractionProvider";
import { AskPluginSlotProvider } from "./AskPluginSlot";
import { usePublishAgentSurfaceContext } from "./usePublishAgentSurfaceContext";
import { WorldAgentConversation, WorldAgentConversationProvider, WorldPlanConversationRegistration, usePublishWorldPlayConversation } from "./WorldAgentConversation";

const selectedWorld = vi.hoisted(() => ({ id: "world-one" }));
vi.mock("../selectedWorld/SelectedWorldContext", () => ({
  useSelectedWorld: () => ({ kind: "managed", worldId: selectedWorld.id, name: "Test World", documentId: "plan-one" }),
}));
vi.mock("../api/liveApi", async (importOriginal) => ({
  ...(await importOriginal<typeof import("../api/liveApi")>()),
  getWorldAgentConversationHistory: vi.fn(),
  getWorldOwnedPlanCommittedRevision: vi.fn(),
  getWorldPlanDocumentEditActions: vi.fn(),
  postWorldPlanAgentTurn: vi.fn(),
  postWorldPlayAgentTurn: vi.fn(),
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
function PlanPublisher({ documentId }: { documentId: string }) {
  return <WorldPlanConversationRegistration worldId={WORLD} worldName="Test World" documentId={documentId}
    surfaceInstanceId="plan-instance" revision={7} editBridge={null} draftGeneration={0} selectionGeneration={0}
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
function Harness({ initial = "plan", admitted = true }: { initial?: "plan" | "play"; admitted?: boolean }) {
  const [surface, setSurface] = useState(initial);
  const [world, setWorld] = useState(WORLD);
  const [documentId, setDocumentId] = useState("plan-one");
  return <AgentInteractionProvider><AskPluginSlotProvider>
    <WorldAgentConversationProvider key={world} worldId={world}>
      <button type="button" onClick={() => setSurface(surface === "plan" ? "play" : "plan")}>Switch surface</button>
      <button type="button" onClick={() => setDocumentId("plan-two")}>Switch Plan document</button>
      <button type="button" onClick={() => { selectedWorld.id = "world-two"; setWorld("world-two"); }}>Switch World</button>
      {surface === "plan" ? <PlanPublisher documentId={documentId} /> : <PlayPublisher admitted={admitted && world === WORLD} />}
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

  it("keeps one World draft and transcript through Plan→Play→Plan without dispatch", async () => {
    render(<Harness />);
    fireEvent.click(await screen.findByRole("button", { name: "Open" }));
    const composer = await screen.findByLabelText("Message DungeonBuddy");
    await screen.findByText("Original Plan answer");
    fireEvent.change(composer, { target: { value: "continue this World" } });
    fireEvent.click(screen.getByRole("button", { name: "Switch surface" }));
    expect(await screen.findByTestId("world-agent-conversation-host")).toBeInTheDocument();
    expect(screen.getByText("Test World · Play · The Crossing · West Gate")).toBeInTheDocument();
    expect(await screen.findByLabelText("Message DungeonBuddy")).toHaveValue("continue this World");
    expect(screen.getAllByRole("textbox")).toHaveLength(1);
    expect(screen.getByText("Original Plan answer")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Switch surface" }));
    expect(await screen.findByLabelText("Message DungeonBuddy")).toHaveValue("continue this World");
    expect(postWorldPlayAgentTurn).not.toHaveBeenCalled();
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
