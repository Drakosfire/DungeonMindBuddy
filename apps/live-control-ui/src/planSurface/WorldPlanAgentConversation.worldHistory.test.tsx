import { act, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { useEffect } from "react";
import { webcrypto } from "node:crypto";
import { afterEach, beforeAll, beforeEach, describe, expect, it, vi } from "vitest";

import * as liveApi from "../api/liveApi";
import type {
  AgentInteractionThread,
  AgentInteractionTurn,
  WorldAgentConversationHistoryResponseV1,
  WorldAgentConversationHistoryTurnV1,
  WorldPlanAgentTurnRequestV1,
} from "../api/types";

const harness = vi.hoisted(() => ({
  worldId: "",
  documentId: "",
  host: null as HTMLElement | null,
  agent: null as any,
}));

vi.mock("../selectedWorld/SelectedWorldContext", () => ({
  useSelectedWorld: () => ({ kind: "managed", worldId: harness.worldId }),
}));
vi.mock("../agentInteraction/AskPluginSlot", () => ({
  useAskPluginSlotOptional: () => ({ hostElement: harness.host }),
  useRegisterAskPluginPresence: () => undefined,
}));
vi.mock("../agentInteraction/useAgentInteraction", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../agentInteraction/useAgentInteraction")>();
  return {
    useAgentInteraction: () => harness.agent ?? actual.useAgentInteraction(),
  };
});
vi.mock("../agentInteraction/usePublishAgentSurfaceContext", () => ({
  usePublishAgentSurfaceContext: () => undefined,
}));

import { AgentInteractionProvider } from "../agentInteraction/AgentInteractionProvider";
import { activeThreadStorageKey, persistAgentThread } from "../agentInteraction/agentInteractionStorage";
import { useAgentInteraction } from "../agentInteraction/useAgentInteraction";
import { WorldPlanAgentConversation } from "./components/WorldPlanAgentConversation";
import { AGENT_TURN_HISTORY_CAP, threadStorageKey } from "./components/agentInteractionHistory";

const worldId = "world-conversation-test";
const documentId = "saved-plan-test";
const surfaceInstanceId = "plan-surface-test";
const namespace = `world-plan-agent:world:${encodeURIComponent(worldId)}:document:${encodeURIComponent(documentId)}`;
const workRevisionId = "00000000-0000-4000-8000-000000000011";
const contentSha256 = "a".repeat(64);
const legacyThreadId = "legacy-thread-test";

function makeTurn(
  sequence: number,
  turnId: string,
  userText: string,
  assistantText: string | null,
  surfaceId = "plan",
): WorldAgentConversationHistoryTurnV1 {
  return {
    turn_id: turnId,
    sequence,
    lifecycle_status: "completed",
    user_text: userText,
    assistant_text: assistantText,
    provenance: {
      world_id: worldId,
      surface_resolution: "resolved",
      surface_id: surfaceId,
      surface_instance_id: `${surfaceId}-instance`,
      primary_work: {
        resolution: "resolved",
        kind: surfaceId === "plan" ? "plan" : "build",
        object_id: surfaceId === "plan" ? documentId : "other-work",
        revision: null,
        content_sha256: null,
        object_revision: surfaceId === "plan" ? 7 : null,
        work_revision_id: surfaceId === "plan" ? workRevisionId : null,
        revision_n: surfaceId === "plan" ? 1 : null,
      },
      supporting_work: [],
      selected_object: {
        resolution: "absent",
        kind: null,
        object_id: null,
        revision: null,
        content_sha256: null,
        object_revision: null,
        work_revision_id: null,
        revision_n: null,
      },
    },
  };
}

function history(
  conversationId: string | null,
  pointerRevision: number,
  turns: WorldAgentConversationHistoryTurnV1[],
  nextBeforeSequence: number | null = null,
): WorldAgentConversationHistoryResponseV1 {
  const absent = conversationId === null;
  return {
    schema: "dmb_agent_conversation_history_v1",
    world_id: worldId,
    conversation_state: absent ? "absent" : "active",
    conversation_id: conversationId,
    active_conversation_id: conversationId,
    pointer_revision: pointerRevision,
    turns,
    next_before_sequence: nextBeforeSequence,
  };
}

function agentResponse(request: WorldPlanAgentTurnRequestV1, conversationId: string, answer: string) {
  return {
    schema: "dmb_agent_turn_response_v1",
    client_thread_id: request.client_thread_id,
    turn_id: request.turn_id,
    surface: {
      surface_id: "plan",
      instance_id: request.surface.instance_id,
      status: "resolved",
    },
    owner_scope: {
      status: "resolved",
      kind: "world",
      owner_id: worldId,
      name: "Test World",
    },
    primary_work: {
      status: "resolved",
      kind: "plan",
      object_id: documentId,
      revision_used: request.primary_work.expected_revision,
      expected_revision: request.primary_work.expected_revision,
      content_basis: {
        world_id: worldId,
        document_id: documentId,
        object_revision: request.primary_work.expected_revision,
        work_revision_id: workRevisionId,
        revision_n: request.primary_work.expected_revision_n,
        content_sha256: request.primary_work.expected_content_sha256,
        committed_status: "committed",
        has_divergent_working_copy: false,
      },
    },
    client_work_state_reported: request.client_work_state,
    graph: {
      status: "not_requested",
      world_id: null,
      campaign_id: null,
      scope_mode: null,
      revision_id: null,
      focus: null,
      selection_node_id: null,
      selection_found: null,
      head_revision_id: null,
      is_head: null,
    },
    conversation: {
      client_thread_id: request.client_thread_id,
      turn_id: request.turn_id,
      pointer_status: "accepted",
      pointer_id: null,
      conversation_id: conversationId,
    },
    answer: {
      status: "ok",
      text: answer,
      code: null,
      message: null,
      graph_grounded: false,
      trace: {},
    },
  };
}

function durableReplayResponse(request: WorldPlanAgentTurnRequestV1, conversationId: string, answer: string) {
  const accepted = agentResponse(request, conversationId, answer);
  return {
    ...accepted,
    primary_work: { ...accepted.primary_work, content_basis: null },
    conversation: { ...accepted.conversation, pointer_status: "reused" },
    answer: {
      ...accepted.answer,
      trace: {
        schema: "dmb_agent_turn_trace_v1",
        trace_id: "00000000-0000-4000-8000-000000000099",
        agent_thread_id: request.client_thread_id,
        turn_id: request.turn_id,
        runtime: "durable_receipt",
        backend: "application_state",
        mode: "replay",
        status: "ok",
        usage: {},
        model_calls: [],
        spans: [],
        steps: [],
        context_summary: {},
        artifact_refs: [],
        warnings: ["durable_turn_replay_no_provider_dispatch"],
        conversation_context: "durable_replay",
      },
    },
  };
}

function fullLegacyThread(): AgentInteractionThread {
  const thread = legacyThread();
  const first = thread.turns[0]!;
  return {
    ...thread,
    turns: Array.from({ length: AGENT_TURN_HISTORY_CAP }, (_, index) => ({
      ...first,
      turnId: `legacy-turn-${index + 1}`,
      askedAt: `2026-01-01T00:${String(index).padStart(2, "0")}:00.000Z`,
      completedAt: `2026-01-01T00:${String(index).padStart(2, "0")}:30.000Z`,
      question: `Legacy question ${index + 1}`,
      answer: `Legacy answer ${index + 1}`,
    })),
  };
}

function ActualProviderScopeInitializer() {
  const agent = useAgentInteraction();
  useEffect(() => {
    agent.rehydrateScope({
      campaignId: namespace,
      sessionNumber: null,
      surfaceId: "plan",
      documentId,
    });
    agent.setPaneOpen(true);
  }, []);
  return null;
}

async function sha256Hex(value: string): Promise<string> {
  const digest = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(value));
  return Array.from(new Uint8Array(digest), (byte) => byte.toString(16).padStart(2, "0")).join("");
}

function readBlob(blob: Blob): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result));
    reader.onerror = () => reject(reader.error ?? new Error("Could not read exported history."));
    reader.readAsText(blob);
  });
}

function deferred<T>() {
  let resolve!: (value: T | PromiseLike<T>) => void;
  let reject!: (reason?: unknown) => void;
  const promise = new Promise<T>((resolvePromise, rejectPromise) => {
    resolve = resolvePromise;
    reject = rejectPromise;
  });
  return { promise, resolve, reject };
}

interface ConversationTestProps {
  revision?: number;
  editBridge?: any;
  playableTarget?: { kind: "scene" | "beat" | "choice" | "option"; id: string } | null;
  playableTargetBasis?: { revision: number; contentSha256: string } | null;
  playableTargetStale?: boolean;
  selectionGeneration?: number;
  draftGeneration?: number;
  savedDirty?: boolean;
}

function conversationElement(props: ConversationTestProps = {}) {
  const revision = props.revision ?? 7;
  const playableTarget = props.playableTarget ?? null;
  const hasExplicitTargetBasis = Object.prototype.hasOwnProperty.call(props, "playableTargetBasis");
  const playableTargetBasis = hasExplicitTargetBasis
    ? props.playableTargetBasis ?? null
    : playableTarget ? { revision: 7, contentSha256 } : null;
  return (
    <WorldPlanAgentConversation
      worldId={worldId}
      worldName="Test World"
      documentId={documentId}
      surfaceInstanceId={surfaceInstanceId}
      revision={revision}
      editBridge={props.editBridge ?? null}
      draftGeneration={props.draftGeneration ?? 0}
      selectionGeneration={props.selectionGeneration ?? 0}
      savedDirty={props.savedDirty ?? false}
      pageReady
      saveInFlight={false}
      playableTarget={playableTarget}
      playableTargetBasis={playableTargetBasis}
      playableTargetStale={props.playableTargetStale ?? false}
    />
  );
}

function historyTurnForAsk(
  request: WorldPlanAgentTurnRequestV1,
  answer: string,
): WorldAgentConversationHistoryTurnV1 {
  const turn = makeTurn(1, request.turn_id, request.message, answer);
  turn.provenance.primary_work = {
    ...turn.provenance.primary_work,
    revision: String(request.primary_work.expected_revision),
    content_sha256: request.primary_work.expected_content_sha256,
    object_revision: request.primary_work.expected_revision,
    work_revision_id: workRevisionId,
    revision_n: request.primary_work.expected_revision_n,
  };
  turn.provenance.supporting_work = request.playable_target ? [{
    resolution: "resolved",
    kind: "dmb_plan_playable_target_v1",
    object_id: request.playable_target.id,
    revision: "v1",
    content_sha256: null,
    object_revision: null,
    work_revision_id: null,
    revision_n: null,
  }] : [];
  return turn;
}

function legacyThread(): AgentInteractionThread {
  const turn: AgentInteractionTurn = {
    turnId: "legacy-turn-1",
    askedAt: "2026-01-01T00:00:00.000Z",
    completedAt: "2026-01-01T00:01:00.000Z",
    question: "Legacy question",
    answer: "Legacy only fact",
    backend: "hermes",
    status: "ok",
  };
  return {
    threadId: legacyThreadId,
    title: "Old local thread",
    createdAt: "2026-01-01T00:00:00.000Z",
    updatedAt: "2026-01-01T00:01:00.000Z",
    campaignId: namespace,
    session: null,
    documentId,
    surfaceId: "plan",
    activeBackend: "hermes",
    hermesSession: { sessionId: "legacy-provider-session", pointerId: "legacy-pointer" },
    turns: [turn],
  };
}

function setHarness() {
  harness.worldId = worldId;
  harness.documentId = documentId;
  harness.host = document.createElement("div");
  document.body.appendChild(harness.host);
  const thread = legacyThread();
  harness.agent = {
    activeThread: thread,
    scope: {
      campaignId: namespace,
      surfaceId: "plan",
      sessionNumber: null,
      documentId,
    },
    paneState: { isOpen: true },
    updateThread: vi.fn((nextThread: AgentInteractionThread) => { harness.agent.activeThread = nextThread; }),
    createThread: vi.fn(),
  };
  return thread;
}

function mountComponent(
  revision = 7,
  editBridge: any = null,
  playableTarget: { kind: "scene" | "beat" | "choice" | "option"; id: string } | null = null,
  playableTargetStale = false,
) {
  return render(conversationElement({
    revision,
    editBridge,
    playableTarget,
    playableTargetStale,
  }));
}

function committedRevision() {
  return {
    schema_version: "dmb_workspace_committed_revision_v2",
    scope_mode: "world",
    world_id: worldId,
    campaign_id: null,
    document_id: documentId,
    kind: "plan",
    status: "active",
    object_revision: 7,
    work_revision_id: workRevisionId,
    revision_n: 1,
    content_sha256: contentSha256,
    markdown: "# Saved Plan",
    has_divergent_working_copy: false,
  };
}

function setupApi(initialHistory: WorldAgentConversationHistoryResponseV1) {
  let currentHistory = initialHistory;
  let currentBasis = committedRevision();
  let olderPage: WorldAgentConversationHistoryResponseV1 | null = null;
  let olderHandler: (() => Promise<WorldAgentConversationHistoryResponseV1>) | null = null;
  const historyCalls: Array<{ limit?: number; beforeSequence?: number }> = [];
  const getHistory = vi.spyOn(liveApi, "getWorldAgentConversationHistory").mockImplementation(async (_world, options = {}) => {
    historyCalls.push(options);
    if (options.beforeSequence !== undefined) {
      if (olderHandler) return olderHandler();
      if (olderPage) return olderPage;
    }
    return currentHistory;
  });
  const getPlanBasis = vi.spyOn(liveApi, "getWorldOwnedPlanCommittedRevision")
    .mockImplementation(async () => currentBasis as any);
  vi.spyOn(liveApi, "getWorldPlanDocumentEditActions").mockResolvedValue({
    schema_version: "dmb_world_plan_action_projection_v1",
    basis: {
      world_id: worldId,
      document_id: documentId,
      object_revision: 7,
      work_revision_id: workRevisionId,
      revision_n: 1,
      content_sha256: contentSha256,
    },
    actions: [],
  });
  return {
    getHistory,
    getPlanBasis,
    historyCalls,
    setCurrent(value: WorldAgentConversationHistoryResponseV1) { currentHistory = value; },
    setPlanBasis(value: ReturnType<typeof committedRevision>) { currentBasis = value; },
    setOlder(value: WorldAgentConversationHistoryResponseV1) { olderPage = value; },
    setOlderHandler(value: () => Promise<WorldAgentConversationHistoryResponseV1>) { olderHandler = value; },
  };
}

function pendingAskKeys(): string[] {
  return Object.keys(localStorage).filter((key) =>
    key.startsWith(`dmb:world-plan-pending-ask:v1:${encodeURIComponent(worldId)}:${encodeURIComponent(documentId)}:`));
}

function pendingCommandKeys(): string[] {
  return Object.keys(localStorage).filter((key) =>
    key.startsWith(`dmb:world-agent-new-conversation:v1:${encodeURIComponent(worldId)}:`));
}

beforeAll(() => {
  Object.defineProperty(globalThis, "crypto", { configurable: true, value: webcrypto });
});

beforeEach(() => {
  vi.restoreAllMocks();
  localStorage.clear();
  setHarness();
});

afterEach(() => {
  vi.restoreAllMocks();
  localStorage.clear();
  document.body.innerHTML = "";
  harness.host = null;
});

describe("World Plan conversation consumer", () => {
  it("renders the immutable target, grammar, and exact WorkRevision from history", async () => {
    const turn = makeTurn(1, "target-turn", "What happens at arrival?", "The arrival is guarded.");
    turn.provenance.primary_work = {
      ...turn.provenance.primary_work,
      revision: "7",
      content_sha256: contentSha256,
      object_revision: 7,
      work_revision_id: workRevisionId,
      revision_n: 4,
    };
    turn.provenance.supporting_work = [{
      resolution: "resolved",
      kind: "dmb_plan_playable_target_v1",
      object_id: "scene:arrival",
      revision: "v1",
      content_sha256: null,
      object_revision: null,
      work_revision_id: null,
      revision_n: null,
    }];
    setupApi(history("conversation-a", 1, [turn]));

    mountComponent();

    expect(await screen.findByText(/Playable target: scene scene:arrival · marker grammar v1 · committed Plan saved-plan-test, object revision 7/)).toBeInTheDocument();
    expect(screen.getByText(new RegExp(`WorkRevision ${workRevisionId}, revision 4, SHA-256 ${contentSha256}`))).toBeInTheDocument();
  });

  it("settles a successful late Ask as history for its original card after selection changes", async () => {
    const api = setupApi(history("conversation-a", 10, []));
    const response = deferred<ReturnType<typeof agentResponse>>();
    const sent: WorldPlanAgentTurnRequestV1[] = [];
    const postAsk = vi.spyOn(liveApi, "postWorldPlanAgentTurn").mockImplementation(async (request) => {
      sent.push(request);
      return response.promise as any;
    });
    const cardA = { kind: "scene" as const, id: "scene:opening" };
    const cardB = { kind: "scene" as const, id: "scene:ending" };
    const mounted = render(conversationElement({ playableTarget: cardA, selectionGeneration: 0 }));

    await screen.findByText(/No messages here yet/);
    fireEvent.change(screen.getByLabelText("Message DungeonBuddy"), {
      target: { value: "What happens at the opening?" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Send message" }));
    await waitFor(() => expect(postAsk).toHaveBeenCalledTimes(1));
    const originalRequest = sent[0]!;
    expect(originalRequest).toMatchObject({
      message: "What happens at the opening?",
      playable_target: { schema: "dmb_plan_playable_target_v1", ...cardA },
      primary_work: {
        object_id: documentId,
        expected_revision: 7,
        expected_content_sha256: contentSha256,
      },
    });
    expect(pendingAskKeys()).toHaveLength(1);

    mounted.rerender(conversationElement({ playableTarget: cardB, selectionGeneration: 1 }));
    const selectedCardForB = screen.getByRole("group", { name: "Selected Playable card for Ask" });
    const selectedCardForBBeforeSettlement = selectedCardForB.textContent;

    const answer = "The opening is guarded by two sentries.";
    const acceptedTurn = historyTurnForAsk(originalRequest, answer);
    await act(async () => {
      api.setCurrent(history("conversation-a", 11, [acceptedTurn]));
      response.resolve(agentResponse(originalRequest, "conversation-a", answer));
      await response.promise;
    });

    expect(await screen.findByText(answer)).toBeInTheDocument();
    expect(await screen.findByText(/original selected card scene:opening at committed Plan object revision 7/)).toBeInTheDocument();
    expect(screen.getByText(new RegExp(`Playable target: scene scene:opening · marker grammar v1 · committed Plan ${documentId}, object revision 7, WorkRevision ${workRevisionId}, revision 1, SHA-256 ${contentSha256}`))).toBeInTheDocument();
    expect(selectedCardForB.textContent).toBe(selectedCardForBBeforeSettlement);
    expect(screen.getByRole("region", { name: "World conversation transcript" }).querySelector("article"))
      .toHaveTextContent("scene:opening");
    expect(screen.getByRole("region", { name: "World conversation transcript" }).querySelector("article"))
      .not.toHaveTextContent("scene:ending");
    expect(postAsk).toHaveBeenCalledTimes(1);
    expect(sent).toEqual([originalRequest]);
    expect(pendingAskKeys()).toHaveLength(0);

    mounted.unmount();
    render(conversationElement({ playableTarget: cardA, selectionGeneration: 2 }));
    expect(await screen.findByText(answer)).toBeInTheDocument();
    expect(screen.getByText(/Playable target: scene scene:opening · marker grammar v1/)).toBeInTheDocument();
  });

  it("keeps a late same-card Ask attributed to its old committed basis after the basis changes", async () => {
    const api = setupApi(history("conversation-a", 10, []));
    const response = deferred<ReturnType<typeof agentResponse>>();
    const sent: WorldPlanAgentTurnRequestV1[] = [];
    const postAsk = vi.spyOn(liveApi, "postWorldPlanAgentTurn").mockImplementation(async (request) => {
      sent.push(request);
      return response.promise as any;
    });
    const sameCard = { kind: "scene" as const, id: "scene:arrival" };
    const mounted = render(conversationElement({ playableTarget: sameCard, selectionGeneration: 0 }));

    await screen.findByText(/No messages here yet/);
    fireEvent.change(screen.getByLabelText("Message DungeonBuddy"), {
      target: { value: "What changes at arrival?" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Send message" }));
    await waitFor(() => expect(postAsk).toHaveBeenCalledTimes(1));
    const originalRequest = sent[0]!;
    const newDigest = "b".repeat(64);

    mounted.rerender(conversationElement({
      revision: 8,
      playableTarget: sameCard,
      playableTargetBasis: { revision: 8, contentSha256: newDigest },
      selectionGeneration: 1,
      draftGeneration: 1,
      savedDirty: true,
    }));
    const selectedCardAfterBasisChange = screen.getByRole("group", { name: "Selected Playable card for Ask" });
    expect(selectedCardAfterBasisChange).toHaveTextContent(`Committed Plan revision 8 · SHA-256 ${newDigest}`);

    const answer = "The arrival now has a verified historical answer.";
    const acceptedTurn = historyTurnForAsk(originalRequest, answer);
    await act(async () => {
      api.setCurrent(history("conversation-a", 11, [acceptedTurn]));
      response.resolve(agentResponse(originalRequest, "conversation-a", answer));
      await response.promise;
    });

    expect(await screen.findByText(answer)).toBeInTheDocument();
    expect(await screen.findByText(/original selected card scene:arrival at committed Plan object revision 7/)).toBeInTheDocument();
    expect(screen.getByText(new RegExp(`Playable target: scene scene:arrival · marker grammar v1 · committed Plan ${documentId}, object revision 7, WorkRevision ${workRevisionId}, revision 1, SHA-256 ${contentSha256}`))).toBeInTheDocument();
    expect(selectedCardAfterBasisChange).toHaveTextContent(`Committed Plan revision 8 · SHA-256 ${newDigest}`);
    expect(selectedCardAfterBasisChange).not.toHaveTextContent(contentSha256);
    expect(postAsk).toHaveBeenCalledTimes(1);
    expect(sent[0]).toEqual(originalRequest);
    expect(originalRequest.primary_work.expected_revision).toBe(7);
    expect(originalRequest.primary_work.expected_content_sha256).toBe(contentSha256);
  });

  it("keeps a late Ask with a malformed target receipt generic after selection changes and reopen", async () => {
    const api = setupApi(history("conversation-a", 10, []));
    const response = deferred<ReturnType<typeof agentResponse>>();
    const postAsk = vi.spyOn(liveApi, "postWorldPlanAgentTurn").mockImplementation(async () => {
      return response.promise as any;
    });
    const cardA = { kind: "scene" as const, id: "scene:opening" };
    const cardB = { kind: "scene" as const, id: "scene:ending" };
    const mounted = render(conversationElement({ playableTarget: cardA, selectionGeneration: 0 }));

    await screen.findByText(/No messages here yet/);
    fireEvent.change(screen.getByLabelText("Message DungeonBuddy"), {
      target: { value: "What happens at the opening?" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Send message" }));
    await waitFor(() => expect(postAsk).toHaveBeenCalledTimes(1));
    const originalRequest = postAsk.mock.calls[0]![0];
    const acceptedTurn = historyTurnForAsk(originalRequest, "The opening has a safe generic historical answer.");
    acceptedTurn.provenance.supporting_work = [{
      resolution: "resolved",
      kind: "dmb_plan_playable_target_v1",
      object_id: "scene:invalid/id",
      revision: "v1",
      content_sha256: null,
      object_revision: null,
      work_revision_id: null,
      revision_n: null,
    }];

    mounted.rerender(conversationElement({ playableTarget: cardB, selectionGeneration: 1 }));
    await act(async () => {
      api.setCurrent(history("conversation-a", 11, [acceptedTurn]));
      response.resolve(agentResponse(originalRequest, "conversation-a", "The opening has a safe generic historical answer."));
      await response.promise;
    });

    const answer = "The opening has a safe generic historical answer.";
    expect(await screen.findByText(answer)).toBeInTheDocument();
    const transcript = screen.getByRole("region", { name: "World conversation transcript" });
    const row = transcript.querySelector("article")!;
    expect(within(row).getByRole("alert")).toHaveTextContent("Target receipt unavailable");
    expect(row).not.toHaveTextContent("Playable target:");
    expect(row).not.toHaveTextContent(cardA.id);
    expect(row).not.toHaveTextContent(cardB.id);

    mounted.unmount();
    render(conversationElement({ playableTarget: cardA, selectionGeneration: 2 }));
    expect(await screen.findByText(answer)).toBeInTheDocument();
    const reopenedTranscript = screen.getByRole("region", { name: "World conversation transcript" });
    const reopenedRow = reopenedTranscript.querySelector("article")!;
    expect(within(reopenedRow).getByRole("alert")).toHaveTextContent("Target receipt unavailable");
    expect(reopenedRow).not.toHaveTextContent("Playable target:");
    expect(reopenedRow).not.toHaveTextContent(cardA.id);
  });

  it("blocks a stale targeted Ask before browser persistence or API dispatch", async () => {
    setupApi(history("conversation-a", 1, []));
    const postAsk = vi.spyOn(liveApi, "postWorldPlanAgentTurn");

    mountComponent(7, null, { kind: "scene", id: "scene:arrival" }, true);
    await screen.findByText(/No messages here yet/);
    fireEvent.change(screen.getByLabelText("Message DungeonBuddy"), {
      target: { value: "Ask about the deleted card." },
    });
    expect(screen.getByRole("button", { name: "Send message" })).toBeDisabled();
    fireEvent.submit(screen.getByLabelText("Message DungeonBuddy").closest("form")!);

    expect(postAsk).not.toHaveBeenCalled();
    expect(pendingAskKeys()).toHaveLength(0);
  });

  it("loads the latest page, merges older turns by durable ID, and preserves server ordering", async () => {
    const api = setupApi(history("conversation-a", 5, [
      makeTurn(2, "turn-2", "Middle question", "Middle answer"),
      makeTurn(3, "turn-3", "Newest question", "Newest answer", "build"),
    ], 2));
    api.setOlder(history("conversation-a", 5, [
      makeTurn(1, "turn-1", "Oldest question", "Oldest answer"),
      makeTurn(2, "turn-2", "Middle question", "Middle answer"),
    ]));

    mountComponent();
    expect(await screen.findByText("Newest question")).toBeInTheDocument();
    expect(screen.getByText(/Recent messages. Older turns are available below./)).toBeInTheDocument();
    expect(screen.getByText(/Historical surface: build/)).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Older turns" }));
    expect(await screen.findByText("Oldest question")).toBeInTheDocument();
    await waitFor(() => expect(screen.getAllByText("Middle question")).toHaveLength(1));
    expect(api.historyCalls).toEqual([
      { limit: 50 },
      { limit: 50, beforeSequence: 2 },
    ]);
    const transcript = screen.getByRole("region", { name: "World conversation transcript" });
    const renderedTurns = Array.from(transcript.querySelectorAll("article"))
      .map((article) => article.getAttribute("data-sequence"));
    expect(renderedTurns).toEqual(["1", "2", "3"]);
  });

  it("unlocks older paging after navigation invalidates a pending page and discards its stale response", async () => {
    const oldLatest = history("conversation-a", 5, [
      makeTurn(3, "turn-3", "Current A turn", "A answer"),
    ], 3);
    const movedPointer = history("conversation-b", 6, [
      makeTurn(2, "turn-b2", "Fresh B turn", "Fresh answer"),
    ], 2);
    const api = setupApi(oldLatest);
    let releaseStalePage!: (value: WorldAgentConversationHistoryResponseV1) => void;
    const stalePage = new Promise<WorldAgentConversationHistoryResponseV1>((resolve) => { releaseStalePage = resolve; });
    api.setOlderHandler(() => stalePage);
    vi.spyOn(liveApi, "postWorldAgentNewConversation").mockImplementation(async (_world, request) => {
      api.setCurrent(movedPointer);
      return {
        schema: "dmb_agent_new_conversation_response_v1",
        world_id: worldId,
        conversation_id: "conversation-b",
        active_conversation_id: "conversation-b",
        pointer_revision: request.expected_pointer_revision + 1,
      } as any;
    });

    mountComponent();
    expect(await screen.findByText("Current A turn")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Older turns" }));
    await waitFor(() => expect(api.historyCalls.some((call) => call.beforeSequence === 3)).toBe(true));

    fireEvent.click(screen.getByRole("button", { name: "New conversation" }));
    expect(await screen.findByText("Fresh B turn")).toBeInTheDocument();
    expect(api.historyCalls).toContainEqual({ limit: 50 });

    await act(async () => {
      releaseStalePage(history("conversation-a", 5, [
        makeTurn(1, "stale-a-page", "Stale older page", "Must be discarded"),
      ], null));
    });
    expect(screen.queryByText("Stale older page")).not.toBeInTheDocument();
    const olderButton = screen.getByRole("button", { name: "Older turns" });
    await waitFor(() => expect(olderButton).toBeEnabled());

    api.setOlderHandler(async () => history("conversation-b", 6, [
      makeTurn(1, "turn-b1", "Fresh older B turn", "Older B answer"),
    ], null));
    fireEvent.click(olderButton);
    expect(await screen.findByText("Fresh older B turn")).toBeInTheDocument();
    expect(api.historyCalls).toContainEqual({ limit: 50, beforeSequence: 2 });
  });

  it("replays the exact Ask receipt across Plan and conversation changes without injecting it into the active transcript", async () => {
    const api = setupApi(history("conversation-a", 4, []));
    const thread = legacyThread();
    const localKey = threadStorageKey(namespace, legacyThreadId);
    const legacyBytes = JSON.stringify(thread);
    localStorage.setItem(localKey, legacyBytes);
    harness.agent.activeThread = thread;

    const createObjectUrl = vi.fn(() => "blob:legacy-export");
    const revokeObjectUrl = vi.fn();
    vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => undefined);
    const oldCreate = Object.getOwnPropertyDescriptor(URL, "createObjectURL");
    const oldRevoke = Object.getOwnPropertyDescriptor(URL, "revokeObjectURL");
    Object.defineProperty(URL, "createObjectURL", { configurable: true, value: createObjectUrl });
    Object.defineProperty(URL, "revokeObjectURL", { configurable: true, value: revokeObjectUrl });

    const sent: WorldPlanAgentTurnRequestV1[] = [];
    let replayReceipt: ReturnType<typeof durableReplayResponse> | null = null;
    const postAsk = vi.spyOn(liveApi, "postWorldPlanAgentTurn").mockImplementation(async (request) => {
      expect(pendingAskKeys()).toHaveLength(1);
      sent.push(request);
      if (sent.length === 1) {
        replayReceipt = durableReplayResponse(request, "conversation-b", "Recovered answer");
        api.setCurrent(history("conversation-c", 6, [
          makeTurn(1, "turn-c1", "Current C question", "Current C answer"),
        ]));
        throw new Error("connection reset after dispatch");
      }
      return replayReceipt as any;
    });

    const first = mountComponent();
    fireEvent.click(screen.getByText("Advanced details"));
    expect(await screen.findByRole("region", { name: "Local-only legacy Plan history" })).toBeInTheDocument();
    expect(screen.getByText("Legacy only fact")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Export local history JSON" }));
    expect(createObjectUrl).toHaveBeenCalledWith(expect.objectContaining({ type: "application/json" }));
    expect(revokeObjectUrl).toHaveBeenCalledWith("blob:legacy-export");
    fireEvent.change(screen.getByLabelText("Message DungeonBuddy"), { target: { value: "What is the plan?" } });
    fireEvent.click(screen.getByRole("button", { name: "Send message" }));
    expect(await screen.findByText(/Ask outcome is uncertain/)).toBeInTheDocument();

    const storedKey = pendingAskKeys()[0]!;
    const storedRaw = localStorage.getItem(storedKey)!;
    const storedEnvelope = JSON.parse(storedRaw);
    expect(storedEnvelope.request).toEqual(sent[0]);
    expect(storedEnvelope.origin).toMatchObject({
      worldId,
      documentId,
      objectRevision: 7,
      workRevisionId,
      revisionN: 1,
      contentSha256,
      pointerRevision: 4,
      conversationId: "conversation-a",
    });
    expect(storedEnvelope.request).not.toHaveProperty("work_revision_id");
    expect(JSON.stringify(storedEnvelope.request)).not.toContain(workRevisionId);
    expect(localStorage.getItem(localKey)).toBe(legacyBytes);
    expect(harness.agent.updateThread).not.toHaveBeenCalled();

    first.unmount();
    api.setPlanBasis({
      ...committedRevision(),
      object_revision: 8,
      work_revision_id: "00000000-0000-4000-8000-000000000012",
      revision_n: 2,
      content_sha256: "b".repeat(64),
      markdown: "# Changed Plan",
    });
    harness.host = document.createElement("div");
    document.body.appendChild(harness.host);
    mountComponent(8);
    fireEvent.click(await screen.findByRole("button", { name: "Retry saved Ask" }));
    await waitFor(() => expect(postAsk).toHaveBeenCalledTimes(2));
    expect(sent[1]).toEqual(sent[0]);
    expect(replayReceipt?.conversation.conversation_id).toBe("conversation-b");
    expect(replayReceipt?.answer.trace.model_calls).toEqual([]);
    expect(replayReceipt?.answer.trace.conversation_context).toBe("durable_replay");
    expect(api.getPlanBasis).toHaveBeenCalledTimes(1);
    expect(pendingAskKeys()).toHaveLength(0);
    expect(await screen.findByText(/confirmed this Ask under conversation conversation-b\. It was not inserted into the currently active conversation/)).toBeInTheDocument();
    expect(await screen.findByText("Current C question")).toBeInTheDocument();
    expect(screen.getByText("Current C answer")).toBeInTheDocument();
    expect(screen.queryByText("Recovered answer")).not.toBeInTheDocument();
    expect(localStorage.getItem(localKey)).toBe(legacyBytes);
    expect(harness.agent.updateThread).not.toHaveBeenCalled();

    if (oldCreate) Object.defineProperty(URL, "createObjectURL", oldCreate);
    else delete (URL as any).createObjectURL;
    if (oldRevoke) Object.defineProperty(URL, "revokeObjectURL", oldRevoke);
    else delete (URL as any).revokeObjectURL;
  });

  it("does not dispatch Ask when browser storage cannot save the exact recovery envelope", async () => {
    setupApi(history("conversation-a", 4, []));
    const postAsk = vi.spyOn(liveApi, "postWorldPlanAgentTurn");
    const originalSetItem = Storage.prototype.setItem;
    vi.spyOn(Storage.prototype, "setItem").mockImplementation(function (key, value) {
      if (key.startsWith("dmb:world-plan-pending-ask:v1:")) throw new Error("quota exceeded");
      return originalSetItem.call(this, key, value);
    });

    mountComponent();
    await screen.findByText(/No messages here yet/i);
    fireEvent.change(screen.getByLabelText("Message DungeonBuddy"), { target: { value: "Do not lose this request" } });
    fireEvent.click(screen.getByRole("button", { name: "Send message" }));

    expect(await screen.findByText(/Ask was not sent because its recovery envelope could not be saved/)).toBeInTheDocument();
    expect(postAsk).not.toHaveBeenCalled();
  });

  it("uses one message field for discussion and inline Plan proposals", async () => {
    const api = setupApi(history("conversation-a", 4, []));
    const askRequests: WorldPlanAgentTurnRequestV1[] = [];
    const postAsk = vi.spyOn(liveApi, "postWorldPlanAgentTurn").mockImplementation(async (request) => {
      askRequests.push(request);
      const answer = askRequests.length === 1
        ? "The saved Plan currently has one opening scene."
        : "The saved Plan discussion continues after the proposals.";
      const currentTurn = makeTurn(
        askRequests.length,
        request.turn_id,
        request.message,
        answer,
      );
      if (askRequests.length === 2) {
        api.setOlder(history("conversation-a", 6, [
          makeTurn(1, askRequests[0]!.turn_id, askRequests[0]!.message, "The saved Plan currently has one opening scene."),
        ]));
      }
      api.setCurrent(history(
        "conversation-a",
        4 + askRequests.length,
        [currentTurn],
        askRequests.length === 1 ? null : 2,
      ));
      return agentResponse(request, "conversation-a", answer) as any;
    });
    let proposalCount = 0;
    const proposalRequest = vi.spyOn(liveApi, "postWorldPlanDocumentEditProposal").mockImplementation(async (request) => ({
      schema_version: "dmb_world_plan_document_edit_proposal_v1",
      action_id: `00000000-0000-4000-8000-${String(++proposalCount).padStart(12, "0")}`,
      idempotency_key: request.idempotency_key,
      document_id: request.document_id,
      world_id: request.world_id,
      base_revision: request.base_revision,
      base_content_sha256: request.base_content_sha256,
      draft_sha256: request.draft_sha256,
      target_kind: request.target_kind,
      selected_text_sha256: await sha256Hex(request.selected_text),
      replacement_markdown: "A lantern shines at the arch.",
      summary: "Add a lantern to the opening.",
      assumptions: [],
      model: "test-model",
      model_observed: false,
      model_latency_ms: 0,
      wall_latency_ms: 0,
      usage: null,
    }) as any);
    vi.spyOn(liveApi, "postWorldAgentNewConversation").mockImplementation(async (_world, request) => {
      api.setCurrent(history("conversation-b", request.expected_pointer_revision + 1, [
        makeTurn(1, "conversation-b-turn-1", "A fresh conversation question", "A fresh conversation answer"),
      ]));
      return {
        schema: "dmb_agent_new_conversation_response_v1",
        world_id: worldId,
        conversation_id: "conversation-b",
        active_conversation_id: "conversation-b",
        pointer_revision: request.expected_pointer_revision + 1,
      } as any;
    });
    const captured = {
      editor: { isDestroyed: false },
      request: {
        document_id: documentId,
        world_id: worldId,
        session: 1,
        base_revision: 7,
        base_content_sha256: contentSha256,
        draft_markdown: "# Draft Plan",
        draft_sha256: "d".repeat(64),
        target_kind: "insert_at_caret" as const,
        selected_text: "",
      },
      from: 1,
      to: 1,
      editorJson: "{}",
      selectionJson: "[]",
      draftGeneration: 0,
      selectionGeneration: 0,
    };
    const bridge = {
      capture: vi.fn(async () => captured),
      apply: vi.fn(async () => undefined),
    };

    const mounted = mountComponent(7, bridge);
    await screen.findByText(/No messages here yet/i);
    expect(screen.getAllByRole("textbox")).toHaveLength(1);
    const messageBox = screen.getByLabelText("Message DungeonBuddy");
    expect(screen.getByRole("button", { name: "Settings" })).toBeInTheDocument();
    fireEvent.change(messageBox, { target: { value: "What is in the opening?" } });
    fireEvent.click(screen.getByRole("button", { name: "Send message" }));
    expect(await screen.findByText("The saved Plan currently has one opening scene.")).toBeInTheDocument();
    expect(postAsk).toHaveBeenCalledTimes(1);
    expect(askRequests[0]).toMatchObject({
      message: "What is in the opening?",
      graph_request: { mode: "none" },
      graph_selection: null,
      primary_work: { object_id: documentId, expected_revision: 7 },
    });

    fireEvent.click(screen.getByRole("radio", { name: "Propose edit" }));
    expect(screen.getByLabelText("Message DungeonBuddy")).toBe(messageBox);
    fireEvent.change(messageBox, { target: { value: "Add a lantern to the opening." } });
    fireEvent.click(screen.getByRole("button", { name: "Propose edit" }));
    const review = await screen.findByRole("region", { name: "Review proposed Plan edit" });
    expect(screen.getAllByRole("textbox")).toHaveLength(1);
    expect(proposalRequest).toHaveBeenCalledTimes(1);
    expect(proposalRequest.mock.calls[0]![0]).toMatchObject({
      instruction: "Add a lantern to the opening.",
      base_revision: 7,
      target_kind: "insert_at_caret",
    });
    expect(postAsk).toHaveBeenCalledTimes(1);
    expect(screen.getByRole("region", { name: "World conversation transcript" })).toContainElement(review);
    expect(review).toHaveTextContent("A lantern shines at the arch.");
    expect(bridge.apply).not.toHaveBeenCalled();

    fireEvent.click(screen.getByRole("button", { name: "Apply changes" }));
    await waitFor(() => expect(bridge.apply).toHaveBeenCalledTimes(1));
    expect(screen.queryByRole("region", { name: "Review proposed Plan edit" })).not.toBeInTheDocument();
    expect(screen.getByText("Apply changes your draft. Save keeps the changes.")).toBeInTheDocument();
    expect(postAsk).toHaveBeenCalledTimes(1);

    fireEvent.click(screen.getByRole("radio", { name: "Propose edit" }));
    fireEvent.change(messageBox, { target: { value: "Add a second detail to the opening." } });
    fireEvent.click(screen.getByRole("button", { name: "Propose edit" }));
    await screen.findByRole("region", { name: "Review proposed Plan edit" });
    fireEvent.click(screen.getByRole("button", { name: "Discard proposal" }));
    fireEvent.change(messageBox, { target: { value: "What follows the opening now?" } });
    fireEvent.click(screen.getByRole("button", { name: "Send message" }));
    expect(await screen.findByText("The saved Plan discussion continues after the proposals.")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Older turns" }));
    expect(await screen.findByText("What is in the opening?")).toBeInTheDocument();

    const transcriptArticles = Array.from(screen.getByRole("region", { name: "World conversation transcript" }).querySelectorAll("article"));
    expect(transcriptArticles.map((article) => article.hasAttribute("data-sequence")
      ? `world:${article.getAttribute("data-sequence")}`
      : `proposal:${article.querySelector("strong")?.parentElement?.textContent?.replace("You:", "").trim()}`)).toEqual([
      "world:1",
      "proposal:Add a lantern to the opening.",
      "proposal:Add a second detail to the opening.",
      "world:2",
    ]);
    expect(transcriptArticles.filter((article) => article.hasAttribute("data-proposal-turn-id"))
      .map((article) => article.getAttribute("data-after-sequence"))).toEqual(["1", "1"]);

    mounted.unmount();
    mountComponent(7, bridge);
    expect(await screen.findByText("The saved Plan discussion continues after the proposals.")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Older turns" }));
    expect(await screen.findByText("What is in the opening?")).toBeInTheDocument();
    const reloadedArticles = Array.from(screen.getByRole("region", { name: "World conversation transcript" }).querySelectorAll("article"));
    expect(reloadedArticles.map((article) => article.hasAttribute("data-sequence")
      ? `world:${article.getAttribute("data-sequence")}`
      : `proposal:${article.querySelector("strong")?.parentElement?.textContent?.replace("You:", "").trim()}`)).toEqual([
      "world:1",
      "proposal:Add a lantern to the opening.",
      "proposal:Add a second detail to the opening.",
      "world:2",
    ]);

    fireEvent.click(screen.getByRole("button", { name: "New conversation" }));
    expect(await screen.findByText("A fresh conversation question")).toBeInTheDocument();
    expect(screen.getByRole("region", { name: "World conversation transcript" })
      .querySelectorAll("[data-proposal-turn-id]")).toHaveLength(0);
    expect(screen.getByRole("region", { name: "Local Plan proposal activity" })).toHaveTextContent(
      "different World conversation",
    );
  });

  it("keeps an auth-rejected Ask pending until the operator sets a credential and explicitly retries", async () => {
    const api = setupApi(history("conversation-a", 4, []));
    const requests: WorldPlanAgentTurnRequestV1[] = [];
    const postAsk = vi.spyOn(liveApi, "postWorldPlanAgentTurn").mockImplementation(async (request) => {
      requests.push(request);
      if (requests.length === 1) throw new liveApi.LiveApiError("Unauthorized", 401);
      api.setCurrent(history("conversation-a", 4, [
        makeTurn(1, request.turn_id, request.message, "Authorized retry answer"),
      ]));
      return agentResponse(request, "conversation-a", "Authorized retry answer") as any;
    });

    mountComponent();
    await screen.findByText(/No messages here yet/i);
    fireEvent.change(screen.getByLabelText("Message DungeonBuddy"), { target: { value: "Keep this exact ask" } });
    fireEvent.click(screen.getByRole("button", { name: "Send message" }));

    expect(await screen.findByText(/Local authorization was rejected/)).toBeInTheDocument();
    expect(pendingAskKeys()).toHaveLength(1);
    expect(postAsk).toHaveBeenCalledTimes(1);
    const savedRequest = JSON.parse(localStorage.getItem(pendingAskKeys()[0]!)!).request;

    expect(screen.getByRole("button", { name: "Open Settings" })).toBeInTheDocument();
    expect(screen.getByLabelText("Local operator credential")).not.toBeVisible();
    fireEvent.click(screen.getByRole("button", { name: "Open Settings" }));
    expect(screen.getByLabelText("Local operator credential")).toBeVisible();

    fireEvent.change(screen.getByLabelText("Local operator credential"), {
      target: { value: "test-only-local-operator-credential-value" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Set authorization" }));
    expect(await screen.findByText(/This credential stays in this tab’s memory/)).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Retry saved Ask" }));

    expect(await screen.findByText("Authorized retry answer")).toBeInTheDocument();
    expect(postAsk).toHaveBeenCalledTimes(2);
    expect(requests[1]).toEqual(savedRequest);
    expect(pendingAskKeys()).toHaveLength(0);
  });

  it("retries New Conversation with the same CAS command and hydrates the confirmed server state", async () => {
    const api = setupApi(history("conversation-a", 10, [
      makeTurn(1, "turn-a", "Earlier question", "Earlier answer"),
    ]));
    const requests: any[] = [];
    const postNew = vi.spyOn(liveApi, "postWorldAgentNewConversation").mockImplementation(async (_world, request) => {
      expect(pendingCommandKeys()).toHaveLength(1);
      requests.push(request);
      if (requests.length === 1) throw new Error("connection lost after command");
      api.setCurrent(history("conversation-b", 11, []));
      return {
        schema: "dmb_agent_new_conversation_response_v1",
        world_id: worldId,
        conversation_id: "conversation-b",
        active_conversation_id: "conversation-b",
        pointer_revision: 11,
      } as any;
    });

    mountComponent();
    expect(await screen.findByText("Earlier question")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "New conversation" }));
    expect(await screen.findByText(/command outcome is uncertain/)).toBeInTheDocument();
    const storedCommand = JSON.parse(localStorage.getItem(pendingCommandKeys()[0]!)!);
    expect(storedCommand.request).toEqual(requests[0]);
    expect(requests[0]).toMatchObject({
      schema: "dmb_agent_new_conversation_v1",
      expected_pointer_revision: 10,
      expected_active_conversation_id: "conversation-a",
    });

    fireEvent.click(screen.getByRole("button", { name: "Retry saved New Conversation command" }));
    expect(await screen.findByText(/No messages here yet/)).toBeInTheDocument();
    expect(requests[1]).toEqual(requests[0]);
    expect(postNew).toHaveBeenCalledTimes(2);
    expect(pendingCommandKeys()).toHaveLength(0);
    expect(harness.agent.updateThread).not.toHaveBeenCalled();
    expect(harness.agent.createThread).not.toHaveBeenCalled();
  });

  it("keeps a delayed old Ask result out of a newly active World conversation", async () => {
    const api = setupApi(history("conversation-a", 10, []));
    const sent: WorldPlanAgentTurnRequestV1[] = [];
    const postAsk = vi.spyOn(liveApi, "postWorldPlanAgentTurn").mockImplementation(async (request) => {
      sent.push(request);
      if (sent.length === 1) throw new Error("temporary network failure");
      return agentResponse(request, "conversation-a", "Old conversation answer") as any;
    });
    vi.spyOn(liveApi, "postWorldAgentNewConversation").mockImplementation(async (_world, request) => {
      api.setCurrent(history("conversation-b", 11, []));
      return {
        schema: "dmb_agent_new_conversation_response_v1",
        world_id: worldId,
        conversation_id: "conversation-b",
        active_conversation_id: "conversation-b",
        pointer_revision: 11,
      } as any;
    });

    mountComponent();
    await screen.findByText(/No messages here yet/i);
    fireEvent.change(screen.getByLabelText("Message DungeonBuddy"), { target: { value: "Keep this in conversation A" } });
    fireEvent.click(screen.getByRole("button", { name: "Send message" }));
    expect(await screen.findByText(/Ask outcome is uncertain/)).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "New conversation" }));
    await waitFor(() => expect(screen.getByText(/New World conversation confirmed/)).toBeInTheDocument());
    await screen.findByText(/No messages here yet/i);
    fireEvent.click(screen.getByRole("button", { name: "Retry saved Ask" }));

    expect(await screen.findByText(/not inserted into the currently active conversation/)).toBeInTheDocument();
    expect(sent[1]).toEqual(sent[0]);
    expect(postAsk).toHaveBeenCalledTimes(2);
    expect(screen.queryByText("Old conversation answer")).not.toBeInTheDocument();
    expect(screen.queryByText("Keep this in conversation A")).not.toBeInTheDocument();
    expect(harness.agent.updateThread).not.toHaveBeenCalled();
  });

  it("keeps a null-basis Ask response pending unless it carries the durable receipt replay trace", async () => {
    setupApi(history("conversation-a", 4, []));
    const requests: WorldPlanAgentTurnRequestV1[] = [];
    vi.spyOn(liveApi, "postWorldPlanAgentTurn").mockImplementation(async (request) => {
      requests.push(request);
      const response = agentResponse(request, "conversation-a", "Unverified response");
      response.primary_work.content_basis = null as any;
      response.conversation.pointer_status = "reused";
      return response as any;
    });

    mountComponent();
    await screen.findByText(/No messages here yet/i);
    fireEvent.change(screen.getByLabelText("Message DungeonBuddy"), { target: { value: "Do not accept this result" } });
    fireEvent.click(screen.getByRole("button", { name: "Send message" }));

    expect(await screen.findByRole("alert")).toHaveTextContent(/did not match this saved Plan|could not be verified/i);
    expect(requests).toHaveLength(1);
    expect(requests[0]?.message).toBe("Do not accept this result");
    expect(pendingAskKeys()).toHaveLength(1);
  });

  it("keeps a full-cap legacy thread byte-for-byte exportable while real provider storage persists Compose and Apply separately", async () => {
    const api = setupApi(history("conversation-a", 4, []));
    harness.agent = null;
    const legacy = fullLegacyThread();
    persistAgentThread(legacy);
    const legacyKey = threadStorageKey(namespace, legacy.threadId);
    const legacyBytes = localStorage.getItem(legacyKey);
    expect(legacyBytes).toBeTruthy();
    expect(JSON.parse(legacyBytes!).turns).toHaveLength(AGENT_TURN_HISTORY_CAP);

    const createdBlobs: Blob[] = [];
    const oldCreate = Object.getOwnPropertyDescriptor(URL, "createObjectURL");
    const oldRevoke = Object.getOwnPropertyDescriptor(URL, "revokeObjectURL");
    Object.defineProperty(URL, "createObjectURL", {
      configurable: true,
      value: vi.fn((blob: Blob) => {
        createdBlobs.push(blob);
        return "blob:legacy-export";
      }),
    });
    Object.defineProperty(URL, "revokeObjectURL", { configurable: true, value: vi.fn() });
    vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => undefined);

    try {
      const captured = {
        editor: { isDestroyed: false },
        request: {
          document_id: documentId,
          world_id: worldId,
          session: 1,
          base_revision: 7,
          base_content_sha256: contentSha256,
          draft_markdown: "# Draft\n\nDraft excerpt.",
          draft_sha256: "d".repeat(64),
          target_kind: "replace_selection" as const,
          selected_text: "Draft excerpt",
        },
        from: 1,
        to: 2,
        editorJson: "{}",
        selectionJson: "[]",
        draftGeneration: 0,
        selectionGeneration: 0,
      };
      const bridge = {
        capture: vi.fn(async () => captured),
        apply: vi.fn(async () => undefined),
      };
      vi.spyOn(liveApi, "postWorldPlanDocumentEditProposal").mockImplementation(async (request) => ({
        schema_version: "dmb_world_plan_document_edit_proposal_v1",
        action_id: "00000000-0000-4000-8000-000000000088",
        idempotency_key: request.idempotency_key,
        document_id: request.document_id,
        world_id: request.world_id,
        base_revision: request.base_revision,
        base_content_sha256: request.base_content_sha256,
        draft_sha256: request.draft_sha256,
        target_kind: request.target_kind,
        selected_text_sha256: await sha256Hex(request.selected_text),
        replacement_markdown: "A distant bell rings.",
        summary: "Add a distant bell.",
        assumptions: [],
        model: "test-model",
        model_observed: false,
        model_latency_ms: 0,
        wall_latency_ms: 0,
        usage: null,
      }) as any);

      const renderRealProvider = () => render(
        <AgentInteractionProvider>
          <ActualProviderScopeInitializer />
          <WorldPlanAgentConversation
            worldId={worldId}
            worldName="Test World"
            documentId={documentId}
            surfaceInstanceId={surfaceInstanceId}
            revision={7}
            editBridge={bridge}
            draftGeneration={0}
            selectionGeneration={0}
            savedDirty={false}
            pageReady
            saveInFlight={false}
          />
        </AgentInteractionProvider>,
      );

      let view = renderRealProvider();
      expect(await screen.findByText("Legacy question 20")).toBeInTheDocument();
      fireEvent.click(screen.getByText("Advanced details"));
      expect(screen.getByRole("region", { name: "Local-only legacy Plan history" })).toBeInTheDocument();
      fireEvent.click(screen.getByRole("button", { name: "Export local history JSON" }));
      expect(await readBlob(createdBlobs[0]!)).toBe(legacyBytes);

      fireEvent.click(screen.getByRole("radio", { name: "Propose edit" }));
      fireEvent.change(screen.getByLabelText("Message DungeonBuddy"), {
        target: { value: "Add a distant bell." },
      });
      fireEvent.click(screen.getByRole("button", { name: "Propose edit" }));
      expect(await screen.findByRole("region", { name: "Review proposed Plan edit" })).toBeInTheDocument();
      fireEvent.click(screen.getByRole("button", { name: "Apply changes" }));
      await waitFor(() => expect(bridge.apply).toHaveBeenCalledTimes(1));

      const activeThreadId = localStorage.getItem(activeThreadStorageKey(namespace, "plan", documentId));
      expect(activeThreadId).toBeTruthy();
      expect(activeThreadId).not.toBe(legacy.threadId);
      const proposalKey = threadStorageKey(namespace, activeThreadId!);
      const proposalThread = JSON.parse(localStorage.getItem(proposalKey) ?? "null");
      expect(proposalThread).toMatchObject({
        worldPlanProposalHistory: "world_plan_proposals_v1",
        turns: [{ backend: "plan_edit", planEdit: { applied: true } }],
      });
      expect(proposalThread.turns).toHaveLength(1);
      expect(localStorage.getItem(legacyKey)).toBe(legacyBytes);
      expect(JSON.parse(legacyBytes!).turns).toHaveLength(AGENT_TURN_HISTORY_CAP);
      expect(await screen.findByRole("region", { name: "World conversation transcript" })).toBeInTheDocument();
      expect(screen.getByRole("region", { name: "Local-only legacy Plan history" })).toBeInTheDocument();

      fireEvent.click(screen.getByRole("button", { name: "Export local history JSON" }));
      expect(await readBlob(createdBlobs[1]!)).toBe(legacyBytes);
      view.unmount();
      api.setPlanBasis(committedRevision());

      harness.host = document.createElement("div");
      document.body.appendChild(harness.host);
      view = renderRealProvider();
      expect(await screen.findByRole("region", { name: "World conversation transcript" })).toBeInTheDocument();
      fireEvent.click(screen.getByText("Advanced details"));
      expect(await screen.findByRole("region", { name: "Local-only legacy Plan history" })).toBeInTheDocument();
      expect(localStorage.getItem(legacyKey)).toBe(legacyBytes);
      expect(JSON.parse(localStorage.getItem(proposalKey) ?? "null").turns[0].planEdit.applied).toBe(true);
      view.unmount();
    } finally {
      if (oldCreate) Object.defineProperty(URL, "createObjectURL", oldCreate);
      else delete (URL as any).createObjectURL;
      if (oldRevoke) Object.defineProperty(URL, "revokeObjectURL", oldRevoke);
      else delete (URL as any).revokeObjectURL;
    }
  });

  it("sends empty proposal history and preserves an in-flight PlanAction body across a conversation change", async () => {
    const api = setupApi(history("conversation-a", 10, []));
    let releaseProposal: ((value: any) => void) | null = null;
    const pendingProposal = new Promise<any>((resolve) => { releaseProposal = resolve; });
    const proposalSpy = vi.spyOn(liveApi, "postWorldPlanDocumentEditProposal").mockReturnValue(pendingProposal);
    vi.spyOn(liveApi, "postWorldAgentNewConversation").mockImplementation(async (_world, _request) => {
      api.setCurrent(history("conversation-b", 11, []));
      return {
        schema: "dmb_agent_new_conversation_response_v1",
        world_id: worldId,
        conversation_id: "conversation-b",
        active_conversation_id: "conversation-b",
        pointer_revision: 11,
      } as any;
    });
    const captured = {
      editor: { isDestroyed: false },
      request: {
        document_id: documentId,
        world_id: worldId,
        session: 1,
        base_revision: 7,
        base_content_sha256: contentSha256,
        draft_markdown: "# Draft",
        draft_sha256: "d".repeat(64),
        target_kind: "replace_selection" as const,
        selected_text: "Draft excerpt",
      },
      from: 1,
      to: 2,
      editorJson: "{}",
      selectionJson: "[]",
      draftGeneration: 0,
      selectionGeneration: 0,
    };
    const bridge = {
      capture: vi.fn(async () => captured),
      apply: vi.fn(async () => undefined),
    };

    const view = mountComponent(7, bridge);
    await screen.findByText(/No messages here yet/i);
    fireEvent.click(screen.getByRole("radio", { name: "Propose edit" }));
    fireEvent.change(screen.getByLabelText("Message DungeonBuddy"), {
      target: { value: "Revise this excerpt" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Propose edit" }));
    await waitFor(() => expect(proposalSpy).toHaveBeenCalledTimes(1));
    const originalRequest = proposalSpy.mock.calls[0]![0];
    expect(originalRequest.conversation_history).toEqual([]);
    expect(JSON.stringify(originalRequest)).not.toContain("Legacy only fact");

    view.rerender(
      <WorldPlanAgentConversation
        worldId={worldId}
        worldName="Test World"
        documentId={documentId}
        surfaceInstanceId={surfaceInstanceId}
        revision={8}
        editBridge={bridge}
        draftGeneration={0}
        selectionGeneration={0}
        savedDirty={false}
        pageReady
        saveInFlight={false}
      />,
    );
    await waitFor(() => expect(screen.getByRole("button", { name: "New conversation" })).toBeEnabled());
    fireEvent.click(screen.getByRole("button", { name: "New conversation" }));
    await screen.findByText(/No messages here yet/);

    expect(proposalSpy).toHaveBeenCalledTimes(1);
    expect(proposalSpy.mock.calls[0]![0]).toEqual(originalRequest);
    expect(originalRequest.idempotency_key).toBeTruthy();
    expect(harness.agent.updateThread).not.toHaveBeenCalled();
    await act(async () => {
      releaseProposal?.({ idempotency_key: originalRequest.idempotency_key, action_id: "action-1" });
    });
  });
});

it("requires a current bounded context preview before prototype Send", async () => {
  window.history.replaceState(null, "", "?prototype=focused");
  try {
    setupApi(history(null, 0, []));
    const preview = vi.spyOn(liveApi, "previewWorldPlanContext").mockImplementation(async request => ({
      message: request.message, characters: request.plan_context_mode === "whole_plan" ? 50312 : request.message.length,
      max_characters: 8000, within_budget: request.plan_context_mode !== "whole_plan", mode: request.plan_context_mode!,
      content_basis: { content_sha256: contentSha256, object_revision: 7, revision_n: 1 },
    }));
    const post = vi.spyOn(liveApi, "postWorldPlanAgentTurn").mockImplementation(async request => agentResponse(request, "conversation-one", "Test received") as any);
    mountComponent(7, { capture: vi.fn(), apply: vi.fn() }, { kind: "scene", id: "scene:opening" });
    await screen.findByText(/No messages here yet/i);
    fireEvent.change(screen.getByLabelText("Message DungeonBuddy"), { target: { value: "Test" } });
    fireEvent.change(screen.getByLabelText("Context", { exact: true }), { target: { value: "message_only" } });
    expect(screen.getByRole("button", { name: "Send message" })).toBeDisabled();
    fireEvent.click(screen.getByRole("button", { name: "Preview context" }));
    await waitFor(() => expect(screen.getByRole("button", { name: "Send message" })).toBeEnabled());
    expect(preview.mock.calls[0]![0].plan_context_mode).toBe("message_only");
    fireEvent.change(screen.getByLabelText("Message DungeonBuddy"), { target: { value: "Changed" } });
    expect(screen.getByRole("button", { name: "Send message" })).toBeDisabled();
    fireEvent.change(screen.getByLabelText("Context", { exact: true }), { target: { value: "whole_plan" } });
    fireEvent.click(screen.getByRole("button", { name: "Preview context" }));
    await screen.findByText(/exceeds the current transport budget/);
    expect(screen.getByRole("button", { name: "Send message" })).toBeDisabled();
    expect(post).not.toHaveBeenCalled();
  } finally { window.history.replaceState(null, "", "/"); }
});
