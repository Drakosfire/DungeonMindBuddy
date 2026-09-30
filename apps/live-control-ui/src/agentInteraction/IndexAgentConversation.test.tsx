import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { useEffect, useMemo } from "react";
import { afterEach, expect, it, vi } from "vitest";

import * as liveApi from "../api/liveApi";
import type { IndexAgentTurnRequestV1, IndexAgentTurnResponseV1 } from "../api/types";
import { threadStorageKey } from "../planSurface/components/agentInteractionHistory";
import { SelectedWorldProvider, useSelectedWorld } from "../selectedWorld/SelectedWorldContext";
import { AgentInteractionChrome } from "./AgentInteractionChrome";
import { AgentInteractionProvider } from "./AgentInteractionProvider";
import { AskPluginSlotProvider } from "./AskPluginSlot";
import { IndexAgentConversation } from "./IndexAgentConversation";
import { ROUTE_COMPATIBILITY_PUBLICATIONS } from "./surfaceInteractionCompat";
import { useAgentInteraction } from "./useAgentInteraction";
import { usePublishSurfaceInteraction } from "./usePublishSurfaceInteraction";

function IndexPublication() {
  const { publishSurfaceContext } = useAgentInteraction();
  usePublishSurfaceInteraction(ROUTE_COMPATIBILITY_PUBLICATIONS.index);
  const context = useMemo(() => ({
    surfaceId: "index" as const,
    label: "Command Board",
    campaignId: null,
    documentId: null,
    sessionNumber: null,
    ambientSummary: "Index",
    sourceEnvelope: null,
  }), []);
  useEffect(() => {
    publishSurfaceContext({ ...context, updatedAt: new Date().toISOString() });
  }, [context, publishSurfaceContext]);
  return null;
}

function SelectionStatus() {
  const selection = useSelectedWorld();
  return <span>Selection: {selection.kind}</span>;
}

function Harness({ location, showIndex = true }: { location: string; showIndex?: boolean }) {
  return <SelectedWorldProvider locationSnapshot={location}>
    <SelectionStatus />
    <AgentInteractionProvider>
      <AskPluginSlotProvider>
        {showIndex ? <IndexPublication /> : null}
        {showIndex ? <IndexAgentConversation /> : null}
        <AgentInteractionChrome />
      </AskPluginSlotProvider>
    </AgentInteractionProvider>
  </SelectedWorldProvider>;
}

function responseFor(request: IndexAgentTurnRequestV1, ordinal: number): IndexAgentTurnResponseV1 {
  return {
    schema: "dmb_agent_turn_response_v1",
    client_thread_id: request.client_thread_id,
    turn_id: request.turn_id,
    surface: { surface_id: "index", instance_id: request.surface.instance_id, status: "resolved" },
    owner_scope: request.owner_scope
      ? { status: "resolved", kind: "world", owner_id: request.owner_scope.world_id, name: "World A" }
      : { status: "absent", kind: null, owner_id: null, name: null },
    primary_work: { status: "absent", kind: null, object_id: null, revision_used: null, expected_revision: null },
    client_work_state_reported: "none",
    graph: { status: "not_requested", world_id: null, campaign_id: null, scope_mode: null,
      revision_id: null, selection_node_id: null, selection_found: null, head_revision_id: null, is_head: null },
    conversation: { client_thread_id: request.client_thread_id, turn_id: request.turn_id,
      pointer_status: ordinal === 1 ? "absent" : "reused", pointer_id: null },
    answer: { status: "ok", text: `Answer ${ordinal}`, code: null, message: null,
      graph_grounded: false, trace: { raw_source: "DO_NOT_PERSIST" } },
  };
}

function stubWorlds() {
  vi.spyOn(liveApi, "listWorldContainers").mockResolvedValue({
    schema_version: "dmb_world_container_registry_v1",
    records: ["world-a", "world-b"].map((id) => ({
      schema_version: "dmb_world_container_record_v1" as const,
      world_id: id,
      name: id === "world-a" ? "World A" : "World B",
      source_root_relpath: `corpus/${id}`,
      created_at: "2026-01-01T00:00:00Z",
    })),
  });
}

async function openAndAsk(question: string) {
  if (!screen.queryByLabelText("Index conversation")) {
    fireEvent.click(await screen.findByRole("button", { name: "Open" }));
  }
  const input = await screen.findByLabelText("Your question");
  fireEvent.change(input, { target: { value: question } });
  await act(async () => { fireEvent.click(screen.getByRole("button", { name: "Ask" })); });
}

afterEach(() => {
  vi.restoreAllMocks();
  localStorage.clear();
  window.history.replaceState({}, "", "/");
});

it("submits two real Index endpoint turns and reloads bounded World-resolved summaries", async () => {
  stubWorlds();
  const post = vi.spyOn(liveApi, "postIndexAgentTurn").mockImplementation(async (request) =>
    responseFor(request, post.mock.calls.length));
  const location = "/?world=world-a";
  window.history.replaceState({}, "", location);
  const view = render(<Harness location={location} />);
  await openAndAsk("First question");
  expect(await screen.findByText("Answer 1")).toBeInTheDocument();
  await openAndAsk("Second question");
  expect(await screen.findByText("Answer 2")).toBeInTheDocument();
  expect(post).toHaveBeenCalledTimes(2);
  const [first, second] = post.mock.calls.map(([request]) => request);
  expect(first).toMatchObject({
    surface: { surface_id: "index", instance_id: expect.any(String) },
    owner_scope: { kind: "world", world_id: "world-a" },
    primary_work: null,
    client_work_state: "none",
    graph_request: { mode: "none" },
    graph_selection: null,
  });
  expect(first.client_thread_id).toBe(second.client_thread_id);
  expect(first.turn_id).not.toBe(second.turn_id);
  expect(screen.getAllByText(/World: World A · No work object · No graph requested/)).toHaveLength(2);
  const stored = localStorage.getItem(threadStorageKey("index-owner:world:world-a", first.client_thread_id)) ?? "";
  expect(stored).not.toContain("DO_NOT_PERSIST");
  expect(JSON.parse(stored).turns).toHaveLength(2);
  view.unmount();
  render(<Harness location={location} />);
  fireEvent.click(await screen.findByRole("button", { name: "Open" }));
  expect(await screen.findByText("Answer 1")).toBeInTheDocument();
  expect(screen.getByText("Answer 2")).toBeInTheDocument();
});

it("uses no owner without a selected World and does not invent work or graph context", async () => {
  const post = vi.spyOn(liveApi, "postIndexAgentTurn").mockImplementation(async (request) => responseFor(request, 1));
  render(<Harness location="/" />);
  await openAndAsk("No World yet");
  expect(await screen.findByText("Answer 1")).toBeInTheDocument();
  expect(post.mock.calls[0][0].owner_scope).toBeNull();
  expect(post.mock.calls[0][0].primary_work).toBeNull();
  expect(post.mock.calls[0][0].graph_request).toEqual({ mode: "none" });
  expect(screen.getByText(/No World · No work object · No graph requested/)).toBeInTheDocument();
});

it("does not turn an unverified World lookup failure into a no-owner conversation", async () => {
  vi.spyOn(liveApi, "listWorldContainers").mockRejectedValue(new Error("World registry unavailable"));
  const post = vi.spyOn(liveApi, "postIndexAgentTurn");
  render(<Harness location="/?world=world-a" />);
  expect(await screen.findByText("Selection: error")).toBeInTheDocument();
  expect(screen.queryByRole("button", { name: "Open" })).not.toBeInTheDocument();
  expect(post).not.toHaveBeenCalled();
});

it("drops an old World answer after owner replacement and keeps the new World transcript separate", async () => {
  stubWorlds();
  let resolveOld!: (value: IndexAgentTurnResponseV1) => void;
  const oldTurn = new Promise<IndexAgentTurnResponseV1>((resolve) => { resolveOld = resolve; });
  const post = vi.spyOn(liveApi, "postIndexAgentTurn").mockImplementationOnce(() => oldTurn)
    .mockImplementation(async (request) => responseFor(request, 2));
  const view = render(<Harness location="/?world=world-a" />);
  await openAndAsk("Old World question");
  const oldRequest = post.mock.calls[0][0];
  view.rerender(<Harness location="/?world=world-b" />);
  await waitFor(() => expect(screen.getByText(/World: World B · Conversation only/)).toBeInTheDocument());
  await act(async () => { resolveOld(responseFor(oldRequest, 1)); });
  await waitFor(() => expect(screen.queryByText("Answer 1")).not.toBeInTheDocument());
  expect(localStorage.getItem(threadStorageKey("index-owner:world:world-b", oldRequest.client_thread_id))).toBeNull();
  await openAndAsk("New World question");
  expect(await screen.findByText("Answer 2")).toBeInTheDocument();
  expect(post.mock.calls[1][0].client_thread_id).not.toBe(oldRequest.client_thread_id);
  expect(post.mock.calls[1][0].owner_scope).toEqual({ kind: "world", world_id: "world-b" });
});

it("keeps a failed question for retry and rejects a mismatched response", async () => {
  const post = vi.spyOn(liveApi, "postIndexAgentTurn")
    .mockRejectedValueOnce(new Error("Agent temporarily unavailable"))
    .mockImplementationOnce(async (request) => ({ ...responseFor(request, 2), turn_id: "wrong-turn" }))
    .mockImplementation(async (request) => responseFor(request, 3));
  render(<Harness location="/" />);
  await openAndAsk("Keep this question");
  expect(await screen.findByRole("alert")).toHaveTextContent("Agent temporarily unavailable");
  expect(screen.getByLabelText("Your question")).toHaveValue("Keep this question");
  expect(screen.queryByText("Answer 1")).not.toBeInTheDocument();
  await act(async () => { fireEvent.click(screen.getByRole("button", { name: "Ask" })); });
  expect(await screen.findByRole("alert")).toHaveTextContent("did not match this Index conversation");
  expect(screen.getByLabelText("Your question")).toHaveValue("Keep this question");
  await act(async () => { fireEvent.click(screen.getByRole("button", { name: "Ask" })); });
  expect(await screen.findByText("Answer 3")).toBeInTheDocument();
  expect(post).toHaveBeenCalledTimes(3);
});

it("fences pending answers on new thread and route unmount", async () => {
  let resolveFirst!: (value: IndexAgentTurnResponseV1) => void;
  let resolveSecond!: (value: IndexAgentTurnResponseV1) => void;
  const post = vi.spyOn(liveApi, "postIndexAgentTurn")
    .mockImplementationOnce(() => new Promise((resolve) => { resolveFirst = resolve; }))
    .mockImplementationOnce(() => new Promise((resolve) => { resolveSecond = resolve; }));
  const view = render(<Harness location="/" />);
  await openAndAsk("First pending question");
  const first = post.mock.calls[0][0];
  fireEvent.click(screen.getByRole("button", { name: "New conversation" }));
  await act(async () => { resolveFirst(responseFor(first, 1)); });
  expect(screen.queryByText("Answer 1")).not.toBeInTheDocument();
  expect(localStorage.getItem(threadStorageKey("index-owner:none", first.client_thread_id))).not.toContain("Answer 1");
  await openAndAsk("Second pending question");
  const second = post.mock.calls[1][0];
  expect(second.client_thread_id).not.toBe(first.client_thread_id);
  view.unmount();
  await act(async () => { resolveSecond(responseFor(second, 2)); });
  expect(localStorage.getItem(threadStorageKey("index-owner:none", second.client_thread_id))).not.toContain("Answer 2");
});

it("retires the Index Ask owner and pending answer when the route is replaced", async () => {
  let resolvePending!: (value: IndexAgentTurnResponseV1) => void;
  const post = vi.spyOn(liveApi, "postIndexAgentTurn")
    .mockImplementation(() => new Promise((resolve) => { resolvePending = resolve; }));
  const view = render(<Harness location="/" />);
  await openAndAsk("Question before leaving Index");
  const request = post.mock.calls[0][0];
  view.rerender(<Harness location="/plan" showIndex={false} />);
  await act(async () => { resolvePending(responseFor(request, 1)); });
  expect(screen.queryByLabelText("Index conversation")).not.toBeInTheDocument();
  expect(screen.queryByRole("button", { name: "Open" })).not.toBeInTheDocument();
  expect(localStorage.getItem(threadStorageKey("index-owner:none", request.client_thread_id))).not.toContain("Answer 1");
});
