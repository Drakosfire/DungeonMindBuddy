import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("./config/planSessionDescriptor", async (importOriginal) => {
  const actual = await importOriginal<typeof import("./config/planSessionDescriptor")>();
  return {
    ...actual,
    resolvePlanningDocument: vi.fn(async () => actual.fixturePlanDocumentDescriptor()),
  };
});

import * as planSessionDescriptor from "./config/planSessionDescriptor";
import {
  FIXTURE_DOC_ID,
  fixturePlanDocumentDescriptor,
  fixturePlanSessionDescriptor,
  fixtureWorkspaceDocumentRecord,
} from "./config/planSessionDescriptor";
import { mockHermesCliTrace, mockPlanView, mockSourceBundle } from "../test/fixtures";
import { AppChrome, type AppChromeTools } from "../chrome/AppChrome";
import {
  activeThreadStorageKey,
  createAgentInteractionThread,
  threadIndexStorageKey,
  threadStorageKey,
  AGENT_THREAD_SUGGEST_NEW_AFTER_TURNS,
} from "./components/agentInteractionHistory";
import { AgentInteractionProvider } from "../agentInteraction/AgentInteractionProvider";
import { PlanSurfaceShell } from "./PlanSurfaceShell";
import * as liveApi from "../api/liveApi";

const worldGraphProjection = {
  schema: "dmb_world_graph_projection_v1" as const,
  snapshot: {
    worldId: "eldyrwild",
    campaignId: "longmont-c2",
    revisionId: "rev-1",
    headRevisionId: "rev-1",
    isHead: true,
    focus: { kind: "none" as const, sessionId: null },
    admissibility: "gm" as const,
  },
  summary: { nodeCount: 0, relationshipCount: 0, attributeCount: 0, evidenceCount: 0, sourceArtifactCount: 0, projectionTruncated: false },
  nodes: [],
  relationships: [],
  attributes: [],
  evidence: [],
  sourceArtifacts: [],
  diagnostics: [],
};

const expectedWorldGraphContextRequest = {
  schema: "dmb_agent_world_graph_query_context_request_v1",
  world_id: "eldyrwild",
  campaign_id: "longmont-c2",
  focus: { kind: "none", session_id: null },
  admissibility: "gm",
  revision_pin: "rev-1",
};

function mockWorldGraphQueryContext(
  status: "ready" | "empty" | "unavailable",
  overrides: Partial<{
    matched_node_ids: string[];
    nodes: Array<Record<string, unknown>>;
    relationships: Array<Record<string, unknown>>;
    attributes: Array<Record<string, unknown>>;
    warning_codes: string[];
    diagnostics: Array<Record<string, unknown>>;
  }> = {},
) {
  return {
    schema: "dmb_agent_world_graph_query_context_v1",
    status,
    world_id: "eldyrwild",
    campaign_id: "longmont-c2",
    revision_id: "rev-1",
    head_revision_id: "rev-1",
    is_head: true,
    focus: { kind: "none", session_id: null },
    admissibility: "gm",
    query_text: "test query",
    matched_node_ids: overrides.matched_node_ids ?? [],
    nodes: overrides.nodes ?? [],
    relationships: overrides.relationships ?? [],
    attributes: overrides.attributes ?? [],
    projection_truncated: false,
    diagnostics: overrides.diagnostics ?? [],
    warning_codes: overrides.warning_codes ?? [],
    trust_boundary: {
      graph_role: "structured_campaign_memory_and_navigation",
      citation_authority: "corpus_source_evidence",
      graph_citations_permitted: false,
    },
  };
}

function PlanSurfaceTestHarness() {
  const [editorTools, setEditorTools] = useState<AppChromeTools | null>(null);

  return (
    <AgentInteractionProvider>
      <AppChrome activeRoute="plan" editorTools={editorTools} editToolboxLayout="dock">
        <PlanSurfaceShell planView={mockPlanView} onEditorToolsChange={setEditorTools} />
      </AppChrome>
    </AgentInteractionProvider>
  );
}

function renderPlanSurface() {
  return render(<PlanSurfaceTestHarness />);
}

async function waitForPlanSurfaceReady() {
  await waitFor(() => {
    expect(screen.getByLabelText("Plan canvas")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Close Edit" })).toBeInTheDocument();
  });
}

describe("PlanSurfaceShell", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    vi.spyOn(liveApi, "postWorldGraphProjection").mockResolvedValue(worldGraphProjection);
    vi.spyOn(liveApi, "listWorkspaceDocuments").mockResolvedValue({
      schema_version: "dmb_workspace_document_registry_v1",
      records: [fixtureWorkspaceDocumentRecord()],
    });
    vi.spyOn(liveApi, "getWorkspaceDocument").mockResolvedValue(fixtureWorkspaceDocumentRecord());
    vi.spyOn(liveApi, "createWorkspaceDocument").mockResolvedValue(fixtureWorkspaceDocumentRecord());
    localStorage.clear();
    window.history.pushState({}, "", "/plan");
  });

  it("renders toolbar, edit bar, and canvas regions", async () => {
    renderPlanSurface();
    await waitForPlanSurfaceReady();

    expect(screen.getByRole("button", { name: "Tools" })).toBeInTheDocument();
    expect(screen.getByRole("navigation", { name: "Toolbox tools" })).toBeInTheDocument();
    expect(screen.getByLabelText("Plan canvas")).toBeInTheDocument();
    expect(screen.getByTestId("plan-canvas-title")).toHaveTextContent(/C2 Session 23 Prep/i);
    expect(screen.queryByRole("navigation", { name: "Plan surface navigation" })).not.toBeInTheDocument();
    expect(screen.queryByTestId("plan-memory-source")).not.toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Review memory" })).not.toBeInTheDocument();
    expect(screen.getByRole("complementary", { name: "Plan toolbox" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Open drawer" })).toBeInTheDocument();
    // Docked Edit starts open; the side tab is hidden until the drawer closes.
    expect(screen.queryByRole("button", { name: "Edit" })).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Close Edit" })).toBeInTheDocument();
    expect(screen.getByRole("complementary", { name: "Edit toolbar" })).toBeInTheDocument();
    expect(screen.getByText("World Graph objects")).toBeInTheDocument();
    expect(screen.getByTestId("plan-graph-ref-search")).toBeInTheDocument();
  });

  it("opens Recap from the tool query parameter", async () => {
    window.history.pushState({}, "", "/plan?tool=recap");
    renderPlanSurface();
    await waitForPlanSurfaceReady();

    await waitFor(() =>
      expect(screen.getByRole("button", { name: "Recap" })).toHaveAttribute("aria-pressed", "true"),
    );
  });

  it("does not render dogfood checklist without ?dogfood=1", async () => {
    window.history.pushState({}, "", "/plan?campaign=longmont-c2&session=22");
    renderPlanSurface();
    await waitForPlanSurfaceReady();

    expect(screen.queryByTestId("plan-dogfood-panel")).not.toBeInTheDocument();
    expect(screen.queryByText("Dogfood checklist")).not.toBeInTheDocument();
  });

  it("renders dogfood checklist when ?dogfood=1 is present", async () => {
    window.history.pushState({}, "", "/plan?campaign=longmont-c2&session=22&dogfood=1");
    renderPlanSurface();
    await waitForPlanSurfaceReady();

    expect(screen.getByTestId("plan-dogfood-panel")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Dogfood checklist" })).toBeInTheDocument();
    expect(screen.getByText(/S1 only: ask what changed after the latest ingested recap/i)).toBeInTheDocument();
  });

  it("opens the prep memory Q&A drawer", async () => {
    const user = userEvent.setup();
    vi.spyOn(globalThis, "fetch").mockResolvedValue({
      ok: true,
      text: async () => JSON.stringify(mockSourceBundle),
    } as Response);

    renderPlanSurface();
    await waitForPlanSurfaceReady();

    await user.click(screen.getByRole("button", { name: "Open drawer" }));

    expect(
      await screen.findByRole("complementary", { name: "DungeonBuddy drawer" }),
    ).toBeInTheDocument();
    expect(screen.getByText("World graph (all sessions)")).toBeInTheDocument();
    expect(screen.getByLabelText("Question")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Ask DungeonBuddy" })).toBeInTheDocument();
    expect(screen.getByText("Memory coverage diagnostics")).toBeInTheDocument();
    expect(screen.queryByText("Advanced source metadata")).not.toBeInTheDocument();
    expect(screen.queryByText(/future Agent Interaction contract/i)).not.toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "New prep thread" })).toBeInTheDocument();
    expect(screen.queryByText("Ask DungeonBuddy · New prep thread")).not.toBeInTheDocument();
    expect(screen.queryByLabelText("Suggested prep questions")).not.toBeInTheDocument();
  });

  it("asks prep memory through live query using the live packet session", async () => {
    const user = userEvent.setup();
    const liveThread = createAgentInteractionThread("longmont-c2", 22, "plan", "live", "Live retrieval thread", FIXTURE_DOC_ID);
    localStorage.setItem(activeThreadStorageKey("longmont-c2", "plan", FIXTURE_DOC_ID), liveThread.threadId);
    localStorage.setItem(threadStorageKey("longmont-c2", liveThread.threadId), JSON.stringify(liveThread));

    vi.spyOn(globalThis, "fetch")
      .mockResolvedValueOnce({
        ok: true,
        text: async () => JSON.stringify(mockSourceBundle),
      } as Response)
      .mockResolvedValueOnce({
        ok: true,
        text: async () =>
          JSON.stringify({
            answer: "Raw synthesized answer should not be the primary result.",
            classification: {},
            events_written: [],
            jobs_queued: [],
            next_suggestions: [],
            diagnostics: [],
            provenance: {},
            citations: [{ evidence_id: "e1", path: "corpus/test/session.md", line_start: 2, line_end: 2, source_role: "play_recap", authority: "canon_play" }],
            retrieval_freshness: {
              schema: "dmb_retrieval_freshness_decision_v1",
              decision: "fresh_retrieval",
              used_fresh_retrieval: true,
              used_thread_context: false,
              admitted_evidence_count: 1,
              rejected_evidence_count: 1,
              prior_turn_count: 0,
              reason: "Fresh corpus evidence was admitted for this turn.",
              warnings: [],
            },
            context_packet: {
              admitted_evidence: [{
                evidence_id: "e1",
                path: "corpus/test/session.md",
                source_role: "play_recap",
                authority: "canon_play",
                line_start: 2,
                line_end: 2,
                text_excerpt: "Stale packet excerpt should not be the reader body.",
              }],
              rejected_evidence: [{ reason_code: "authority_mismatch", evidence: { path: "y" } }],
            },
          }),
      } as Response)
      .mockResolvedValueOnce({
        ok: true,
        text: async () =>
          JSON.stringify({
            schema_version: "dmb_citation_source_v1",
            path: "corpus/test/session.md",
            content_type: "text/markdown",
            content: "# Session file\nCurrent source content has the Lysandro gate reveal.\nMore notes.",
            truncated: false,
            highlight: {
              line_start: 2,
              line_end: 2,
              text_excerpt: "Current source content has the Lysandro gate reveal.",
              match_source: "line_range",
            },
            diagnostics: ["read-only source lookup", "no events or jobs written"],
          }),
      } as Response);

    renderPlanSurface();
    await waitForPlanSurfaceReady();

    await user.click(screen.getByRole("button", { name: "Open drawer" }));
    await screen.findByText("World graph (all sessions)");
    expect(screen.getByLabelText("Question")).toBeInTheDocument();
    await user.type(
      screen.getByLabelText("Question"),
      "What changed after Session 22?",
    );
    await user.click(screen.getByRole("button", { name: "Ask DungeonBuddy" }));

    expect(await screen.findByText("Preliminary verdict · Enough context")).toBeInTheDocument();
    expect(screen.getAllByText("Fresh retrieval").length).toBeGreaterThan(0);
    expect(screen.getByRole("region", { name: "Hermes reply" })).toHaveTextContent("Raw synthesized answer should not be the primary result.");
    expect(screen.getByRole("region", { name: "Context packet review" })).toBeInTheDocument();
    expect(screen.getByRole("region", { name: "Supporting sources" })).toHaveTextContent("play_recap · canon_play");
    expect(screen.queryByRole("region", { name: "Source preview" })).not.toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Open source" }));

    const sourceReader = await screen.findByRole("region", { name: "Source preview" });
    expect(sourceReader).toHaveTextContent("Current source content has the Lysandro gate reveal.");
    expect(sourceReader).not.toHaveTextContent("Stale packet excerpt should not be the reader body.");
    const storedThreadId = localStorage.getItem(activeThreadStorageKey(mockPlanView.campaign_id, "plan", FIXTURE_DOC_ID));
    expect(storedThreadId).toBeTruthy();
    expect(localStorage.getItem(threadStorageKey(mockPlanView.campaign_id, storedThreadId ?? "")) ?? "").not.toContain("Current source content has the Lysandro gate reveal.");
    expect(screen.getByRole("region", { name: "Retrieval freshness" })).toBeInTheDocument();
    expect(screen.getAllByText("Fresh retrieval").length).toBeGreaterThan(0);
    expect(screen.getByText("Fresh corpus evidence was admitted for this turn.")).toBeInTheDocument();
    expect(screen.getByText("authority_mismatch: 1")).toBeInTheDocument();
    expect(screen.queryByText("Grounded answer")).not.toBeInTheDocument();
    expect(screen.getByRole("region", { name: "Conversation transcript" })).toBeInTheDocument();
    expect(screen.getByText("Supporting sources")).toBeInTheDocument();
    const queryCall = vi.mocked(globalThis.fetch).mock.calls[1];
    expect(JSON.parse(String(queryCall[1]?.body))).toMatchObject({
      campaign_id: "longmont-c2",
      session: 22,
      query_backend: "live",
      world_graph_context: expectedWorldGraphContextRequest,
    });
    const sourceCall = vi.mocked(globalThis.fetch).mock.calls[2];
    expect(String(sourceCall[0])).toContain("/api/live/citation-source");
    expect(JSON.parse(String(sourceCall[1]?.body))).toMatchObject({ path: "corpus/test/session.md", line_start: 2, line_end: 2 });
  });


  it("checks corpus freshness from a stored source-lines snapshot", async () => {
    const user = userEvent.setup();
    vi.spyOn(globalThis, "fetch")
      .mockResolvedValueOnce({ ok: true, text: async () => JSON.stringify(mockSourceBundle) } as Response)
      .mockResolvedValueOnce({
        ok: true,
        text: async () => JSON.stringify({
          answer: "Stored answer with corpus evidence.",
          classification: {},
          events_written: [],
          jobs_queued: [],
          next_suggestions: [],
          diagnostics: [],
          provenance: {},
          citations: [{ evidence_id: "e1", path: "corpus/test/session.md", line_start: 2, line_end: 2, source_role: "play_recap", authority: "canon_play" }],
          evidence_snapshots: [{
            schema: "dmb_agent_evidence_snapshot_v1",
            evidence_id: "e1",
            path: "corpus/test/session.md",
            line_start: 2,
            line_end: 2,
            source_role: "play_recap",
            authority: "canon_play",
            fingerprint: "expected-source-lines-hash",
            fingerprint_algorithm: "sha256:source-lines-v1",
            captured_at: "2026-06-25T00:00:00Z",
          }],
          retrieval_freshness: {
            schema: "dmb_retrieval_freshness_decision_v1",
            decision: "fresh_retrieval",
            used_fresh_retrieval: true,
            used_thread_context: false,
            admitted_evidence_count: 1,
            rejected_evidence_count: 0,
            prior_turn_count: 0,
            reason: "Fresh corpus evidence was admitted for this turn.",
            warnings: [],
          },
          context_packet: null,
        }),
      } as Response)
      .mockResolvedValueOnce({
        ok: true,
        text: async () => JSON.stringify({
          schema: "dmb_citation_freshness_v1",
          path: "corpus/test/session.md",
          status: "current",
          current_fingerprint: "expected-source-lines-hash",
          expected_fingerprint: "expected-source-lines-hash",
          fingerprint_algorithm: "sha256:source-lines-v1",
          checked_at: "2026-06-25T00:01:00Z",
          diagnostics: ["read-only freshness lookup", "no source content returned"],
          warnings: [],
        }),
      } as Response);

    renderPlanSurface();
    await waitForPlanSurfaceReady();

    await user.click(screen.getByRole("button", { name: "Open drawer" }));
    await user.type(screen.getByLabelText("Question"), "Is this still current?");
    await user.click(screen.getByRole("button", { name: "Ask DungeonBuddy" }));

    expect(await screen.findByRole("region", { name: "Corpus change signal" })).toHaveTextContent("Corpus signal: Unknown");
    await user.click(screen.getByRole("button", { name: "Check current source state" }));

    expect(await screen.findByRole("region", { name: "Corpus change signal" })).toHaveTextContent("Corpus signal: Current");
    const freshnessCall = vi.mocked(globalThis.fetch).mock.calls[2];
    expect(String(freshnessCall[0])).toContain("/api/live/citation-freshness");
    expect(JSON.parse(String(freshnessCall[1]?.body))).toMatchObject({
      path: "corpus/test/session.md",
      expected_fingerprint: "expected-source-lines-hash",
      fingerprint_algorithm: "sha256:source-lines-v1",
    });
    const storedThreadId = localStorage.getItem(activeThreadStorageKey(mockPlanView.campaign_id, "plan", FIXTURE_DOC_ID));
    const storedThread = localStorage.getItem(threadStorageKey(mockPlanView.campaign_id, storedThreadId ?? "")) ?? "";
    expect(storedThread).toContain("expected-source-lines-hash");
    expect(storedThread).not.toContain("Current source content has the Lysandro gate reveal.");
    const indexJson = localStorage.getItem(threadIndexStorageKey(mockPlanView.campaign_id, "plan", FIXTURE_DOC_ID)) ?? "";
    expect(indexJson).not.toContain("expected-source-lines-hash");
    expect(indexJson).not.toContain("corpus/test/session.md");
  });

  it("can route the DungeonBuddy drawer through Hermes tools", async () => {
    const user = userEvent.setup();
    vi.spyOn(globalThis, "fetch")
      .mockResolvedValueOnce({
        ok: true,
        text: async () => JSON.stringify(mockSourceBundle),
      } as Response)
      .mockResolvedValueOnce({
        ok: true,
        text: async () =>
          JSON.stringify({
            answer: "Hermes returned enough manifest-backed context.",
            classification: { latency_mode: "context_lookup", event_type: "context_question" },
            mode: "hermes_context_lookup",
            events_written: [],
            jobs_queued: [],
            next_suggestions: [],
            diagnostics: { hermes_tool: "dungeon_context_lookup" },
            provenance: { backend: "hermes" },
            citations: [],
            retrieval_freshness: {
              schema: "dmb_retrieval_freshness_decision_v1",
              decision: "blended",
              used_fresh_retrieval: true,
              used_thread_context: true,
              admitted_evidence_count: 1,
              rejected_evidence_count: 0,
              prior_turn_count: 0,
              reason: "Fresh corpus evidence was admitted, and an active Hermes session/thread handle was reused.",
              warnings: [],
            },
            context_packet: {
              schema: "dmb_enriched_planning_context_packet_v1",
              question_id: "hermes-test",
              intent_class: "play_fact_retrieval",
              admitted_evidence: [{
                path: "corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/Session Recaps/Session 22 - Mireward Road and Lysandro.md",
                source_role: "play_recap",
                authority: "canon_play",
                text_excerpt: "Session 22 ended with Lysandro at the gate and a direct reveal.",
              }],
              rejected_evidence: [],
            },
          }),
      } as Response);

    renderPlanSurface();
    await waitForPlanSurfaceReady();

    await user.click(screen.getByRole("button", { name: "Open drawer" }));
    await screen.findByText("World graph (all sessions)");
    await user.type(screen.getByLabelText("Question"), "What happened at the end of session 22?");
    await user.click(screen.getByRole("button", { name: "Ask DungeonBuddy" }));

    expect(await screen.findByText("Preliminary verdict · Enough context")).toBeInTheDocument();
    expect(screen.getAllByText("Blended").length).toBeGreaterThan(0);
    const queryCall = vi.mocked(globalThis.fetch).mock.calls[1];
    expect(JSON.parse(String(queryCall[1]?.body))).toMatchObject({
      query_backend: "hermes",
      world_graph_context: expectedWorldGraphContextRequest,
    });
  });

  it("sends world graph context on follow-up turns without a thread-level pin", async () => {
    const user = userEvent.setup();
    vi.spyOn(globalThis, "fetch")
      .mockResolvedValueOnce({
        ok: true,
        text: async () => JSON.stringify(mockSourceBundle),
      } as Response)
      .mockResolvedValueOnce({
        ok: true,
        text: async () =>
          JSON.stringify({
            answer: "First answer",
            classification: {},
            events_written: [],
            jobs_queued: [],
            next_suggestions: [],
            diagnostics: {},
            provenance: {},
            citations: [],
            world_graph_context: mockWorldGraphQueryContext("ready"),
          }),
      } as Response)
      .mockResolvedValueOnce({
        ok: true,
        text: async () =>
          JSON.stringify({
            answer: "Second answer",
            classification: {},
            events_written: [],
            jobs_queued: [],
            next_suggestions: [],
            diagnostics: {},
            provenance: {},
            citations: [],
            world_graph_context: mockWorldGraphQueryContext("ready"),
          }),
      } as Response);

    renderPlanSurface();
    await waitForPlanSurfaceReady();

    await user.click(screen.getByRole("button", { name: "Open drawer" }));
    await screen.findByText("World graph (all sessions)");
    await user.type(screen.getByLabelText("Question"), "First question?");
    await user.click(screen.getByRole("button", { name: "Ask DungeonBuddy" }));
    expect(await screen.findByText("First answer")).toBeInTheDocument();

    await user.type(screen.getByLabelText("Question"), "Second question?");
    await user.click(screen.getByRole("button", { name: "Ask DungeonBuddy" }));
    expect(await screen.findByText("Second answer")).toBeInTheDocument();

    const firstQueryBody = JSON.parse(String(vi.mocked(globalThis.fetch).mock.calls[1][1]?.body));
    const secondQueryBody = JSON.parse(String(vi.mocked(globalThis.fetch).mock.calls[2][1]?.body));
    expect(firstQueryBody.world_graph_context).toEqual(expectedWorldGraphContextRequest);
    expect(secondQueryBody.world_graph_context).toEqual(expectedWorldGraphContextRequest);
    expect(firstQueryBody).not.toHaveProperty("revision_pin");
    expect(secondQueryBody).not.toHaveProperty("revision_pin");
  });

  it("renders ready world graph context with matched durable IDs", async () => {
    const user = userEvent.setup();
    vi.spyOn(globalThis, "fetch")
      .mockResolvedValueOnce({
        ok: true,
        text: async () => JSON.stringify(mockSourceBundle),
      } as Response)
      .mockResolvedValueOnce({
        ok: true,
        text: async () =>
          JSON.stringify({
            answer: "Lysandro is at the gate.",
            classification: {},
            events_written: [],
            jobs_queued: [],
            next_suggestions: [],
            diagnostics: {},
            provenance: {},
            citations: [],
            world_graph_context: mockWorldGraphQueryContext("ready", {
              matched_node_ids: ["node-lysandro"],
              nodes: [{
                node_id: "node-lysandro",
                label: "Lysandro",
                kind: "npc",
                role: "antagonist",
                summary: "Gate antagonist",
                anchored_to_focus_session: true,
              }],
            }),
          }),
      } as Response);

    renderPlanSurface();
    await waitForPlanSurfaceReady();

    await user.click(screen.getByRole("button", { name: "Open drawer" }));
    await screen.findByText("World graph (all sessions)");
    await user.type(screen.getByLabelText("Question"), "Who is Lysandro?");
    await user.click(screen.getByRole("button", { name: "Ask DungeonBuddy" }));

    const graphPanel = await screen.findByRole("region", { name: "World graph query context" });
    expect(graphPanel).toHaveTextContent("Graph context · ready");
    expect(graphPanel).toHaveTextContent("node-lysandro");
    expect(graphPanel).toHaveTextContent("Lysandro");
  });

  it("renders empty and unavailable world graph context states", async () => {
    const user = userEvent.setup();
    vi.spyOn(globalThis, "fetch")
      .mockResolvedValueOnce({
        ok: true,
        text: async () => JSON.stringify(mockSourceBundle),
      } as Response)
      .mockResolvedValueOnce({
        ok: true,
        text: async () =>
          JSON.stringify({
            answer: "No graph matches.",
            classification: {},
            events_written: [],
            jobs_queued: [],
            next_suggestions: [],
            diagnostics: {},
            provenance: {},
            citations: [],
            world_graph_context: mockWorldGraphQueryContext("empty", {
              warning_codes: ["graph_context_empty"],
            }),
          }),
      } as Response)
      .mockResolvedValueOnce({
        ok: true,
        text: async () =>
          JSON.stringify({
            answer: "Graph unavailable.",
            classification: {},
            events_written: [],
            jobs_queued: [],
            next_suggestions: [],
            diagnostics: {},
            provenance: {},
            citations: [],
            world_graph_context: mockWorldGraphQueryContext("unavailable", {
              warning_codes: ["world_graph_unavailable"],
            }),
          }),
      } as Response);

    renderPlanSurface();
    await waitForPlanSurfaceReady();

    await user.click(screen.getByRole("button", { name: "Open drawer" }));
    await screen.findByText("World graph (all sessions)");

    await user.type(screen.getByLabelText("Question"), "Empty graph question?");
    await user.click(screen.getByRole("button", { name: "Ask DungeonBuddy" }));
    expect(await screen.findByText("Graph context · empty")).toBeInTheDocument();
    expect(screen.getByText("graph_context_empty")).toBeInTheDocument();

    await user.type(screen.getByLabelText("Question"), "Unavailable graph question?");
    await user.click(screen.getByRole("button", { name: "Ask DungeonBuddy" }));
    expect(await screen.findByText("Graph context · unavailable")).toBeInTheDocument();
    expect(screen.getByText("world_graph_unavailable")).toBeInTheDocument();
  });

  it("disables ask submit while world graph projection is loading", async () => {
    const user = userEvent.setup();
    let resolveProjection: ((value: typeof worldGraphProjection) => void) | undefined;
    vi.spyOn(liveApi, "postWorldGraphProjection").mockImplementation(
      () => new Promise((resolve) => {
        resolveProjection = resolve;
      }),
    );
    vi.spyOn(globalThis, "fetch").mockResolvedValue({
      ok: true,
      text: async () => JSON.stringify(mockSourceBundle),
    } as Response);

    renderPlanSurface();
    await waitForPlanSurfaceReady();

    await user.click(screen.getByRole("button", { name: "Open drawer" }));
    await screen.findByText("World graph (all sessions)");
    expect(await screen.findByText("Initializing world graph context…")).toBeInTheDocument();

    await user.type(screen.getByLabelText("Question"), "Ask before projection is ready?");
    const submitButton = screen.getByRole("button", { name: "Ask DungeonBuddy" });
    expect(submitButton).toBeDisabled();

    resolveProjection?.(worldGraphProjection);
    await waitFor(() => expect(submitButton).not.toBeDisabled());
  });

  it("warns when a prep memory answer has no grounding evidence", async () => {
    const user = userEvent.setup();
    vi.spyOn(globalThis, "fetch")
      .mockResolvedValueOnce({
        ok: true,
        text: async () => JSON.stringify(mockSourceBundle),
      } as Response)
      .mockResolvedValueOnce({
        ok: true,
        text: async () =>
          JSON.stringify({
            answer: "I can speculate, but I did not find supporting campaign text.",
            classification: {},
            events_written: [],
            jobs_queued: [],
            next_suggestions: [],
            diagnostics: [],
            provenance: {},
            citations: [],
            retrieval_freshness: null,
            context_packet: {
              admitted_evidence: [],
              rejected_evidence: [],
            },
          }),
      } as Response);

    renderPlanSurface();
    await waitForPlanSurfaceReady();

    await user.click(screen.getByRole("button", { name: "Open drawer" }));
    await screen.findByText("World graph (all sessions)");
    await user.type(screen.getByLabelText("Question"), "What should I remember about the gate?");
    await user.click(screen.getByRole("button", { name: "Ask DungeonBuddy" }));

    const answerRegion = await screen.findByRole("region", { name: "Hermes reply" });
    expect(screen.getByText(/No grounded evidence returned/i)).toBeInTheDocument();
    expect(answerRegion).toBeInTheDocument();
    expect(screen.getByText("I can speculate, but I did not find supporting campaign text.")).toBeInTheDocument();
    expect(screen.queryByRole("region", { name: "Supporting sources" })).not.toBeInTheDocument();
  });

  it("shows agent trace panel for Hermes CLI answers without context packet", async () => {
    const user = userEvent.setup();
    vi.spyOn(globalThis, "fetch")
      .mockResolvedValueOnce({
        ok: true,
        text: async () => JSON.stringify(mockSourceBundle),
      } as Response)
      .mockResolvedValueOnce({
        ok: true,
        text: async () =>
          JSON.stringify({
            answer: "CLI synthesized answer for operator.",
            classification: { latency_mode: "context_lookup", event_type: "context_question" },
            mode: "hermes_cli_oneshot",
            status: "ok",
            events_written: [],
            jobs_queued: [],
            next_suggestions: [],
            diagnostics: { hermes_toolset: "dungeonbuddy" },
            provenance: { backend: "hermes", runtime: "cli" },
            citations: [],
            context_packet: null,
            agent_trace: mockHermesCliTrace,
          }),
      } as Response);

    renderPlanSurface();
    await waitForPlanSurfaceReady();

    await user.click(screen.getByRole("button", { name: "Open drawer" }));
    await screen.findByText("World graph (all sessions)");
    await user.type(screen.getByLabelText("Question"), "What happened at the end of session 22?");
    await user.click(screen.getByRole("button", { name: "Ask DungeonBuddy" }));

    expect(await screen.findByLabelText("Agent interaction trace")).toBeInTheDocument();
    expect(screen.getByText("CLI synthesized answer for operator.")).toBeInTheDocument();
    expect(screen.getByText(/3100 ms/)).toBeInTheDocument();
    expect(screen.getByText(/Prompt sent to Hermes/)).toBeInTheDocument();
    expect(screen.getByText(/No grounded evidence returned/i)).toBeInTheDocument();
    expect(screen.queryByText("No context packet returned for this query.")).not.toBeInTheDocument();
  });

  it("renders PR354 Hermes graph agent_trace safely with Trace On", async () => {
    const user = userEvent.setup();
    const pr354Trace = {
      trace_id: "agent-trace-pr354-shell",
      runtime: "process_isolated",
      backend: "hermes",
      mode: "hermes_graph_agent",
      started_at: "2026-07-14T18:00:00Z",
      completed_at: "2026-07-14T18:00:01Z",
      elapsed_ms: 88,
      status: "ok",
      usage: {
        available: false,
        input_tokens: null,
        output_tokens: null,
        total_tokens: null,
      },
      steps: [],
      context_summary: {},
      artifact_refs: [],
      tool_events: [
        {
          tool_name: "search_campaign_graph",
          state: "completion",
          outcome: "enough",
          source_anchor_ids: ["source-anchor:v1:fixture"],
        },
      ],
      hermes_session_id: "hermes-sess-obs-only",
      process_isolation: "process_exclusive",
      warnings: [],
    };

    vi.spyOn(globalThis, "fetch")
      .mockResolvedValueOnce({
        ok: true,
        text: async () => JSON.stringify(mockSourceBundle),
      } as Response)
      .mockResolvedValueOnce({
        ok: true,
        text: async () =>
          JSON.stringify({
            answer: "Tripod stands at the North Gate.",
            classification: {
              intent: "hermes_graph_agent",
              latency_mode: "hermes_graph_agent",
              event_type: "hermes_graph_agent",
            },
            mode: "hermes_graph_agent",
            status: "ok",
            events_written: [],
            jobs_queued: [],
            next_suggestions: [],
            diagnostics: { grounding_state: "grounded" },
            provenance: { backend: "hermes", runtime: "process_isolated" },
            citations: [],
            context_packet: null,
            grounding: {
              schema: "dmb_hermes_graph_grounding_v1",
              state: "grounded",
              revision_id: "revision:fixture",
              source_anchor_count: 1,
            },
            agent_trace: pr354Trace,
            hermes_session: null,
          }),
      } as Response);

    renderPlanSurface();
    await waitForPlanSurfaceReady();

    await user.click(screen.getByRole("button", { name: "Open drawer" }));
    await screen.findByText("World graph (all sessions)");
    await user.type(screen.getByLabelText("Question"), "Where is Tripod?");
    await user.click(screen.getByRole("button", { name: "Ask DungeonBuddy" }));

    expect(await screen.findByLabelText("Agent interaction trace")).toBeInTheDocument();
    expect(screen.getByText("Tripod stands at the North Gate.")).toBeInTheDocument();
    expect(screen.getByText(/88 ms/)).toBeInTheDocument();
    expect(screen.getByText("not reported")).toBeInTheDocument();
    expect(screen.getByText("hermes_graph_agent")).toBeInTheDocument();
    // Default new-thread UI keeps trace visible ("Trace On"); panel must not crash on PR354 shell.
    expect(screen.getByRole("button", { name: /Trace (On|Off)/ })).toBeInTheDocument();
  });

  it("persists bounded conversation metadata and supports clear history", async () => {
    const user = userEvent.setup();
    const makeQueryResponse = (answer: string, traceId: string) => ({
      answer,
      classification: { latency_mode: "context_lookup", event_type: "context_question" },
      mode: "hermes_cli_oneshot",
      status: "ok",
      events_written: [],
      jobs_queued: [],
      next_suggestions: [],
      diagnostics: {},
      provenance: { backend: "hermes", runtime: "cli" },
      citations: [],
      context_packet: null,
      agent_trace: {
        ...mockHermesCliTrace,
        trace_id: traceId,
        prompt_preview: "Retrieved evidence excerpts: secret corpus text_excerpt body",
        artifact_refs: [{ kind: "hermes_session", path: "/tmp/hermes/sessions/session.json", label: "session" }],
      },
    });

    vi.spyOn(globalThis, "fetch")
      .mockResolvedValueOnce({
        ok: true,
        text: async () => JSON.stringify(mockSourceBundle),
      } as Response)
      .mockResolvedValueOnce({
        ok: true,
        text: async () => JSON.stringify(makeQueryResponse("First answer", "trace-one")),
      } as Response)
      .mockResolvedValueOnce({
        ok: true,
        text: async () => JSON.stringify(makeQueryResponse("Second answer", "trace-two")),
      } as Response);

    renderPlanSurface();
    await waitForPlanSurfaceReady();

    await user.click(screen.getByRole("button", { name: "Open drawer" }));
    await screen.findByText("World graph (all sessions)");

    await user.type(screen.getByLabelText("Question"), "First question?");
    await user.click(screen.getByRole("button", { name: "Ask DungeonBuddy" }));
    expect(await screen.findByText("First answer")).toBeInTheDocument();
    expect(screen.getByRole("region", { name: "Conversation transcript" })).toBeInTheDocument();

    await user.type(screen.getByLabelText("Question"), "Second question?");
    await user.click(screen.getByRole("button", { name: "Ask DungeonBuddy" }));
    expect(await screen.findByText("Second answer")).toBeInTheDocument();
    expect(screen.getByRole("region", { name: "Conversation transcript" })).toBeInTheDocument();
    expect(screen.queryByText(/Conversation \(\d+\)/)).not.toBeInTheDocument();

    const activeThreadId = localStorage.getItem(activeThreadStorageKey("longmont-c2", "plan", FIXTURE_DOC_ID));
    expect(activeThreadId).toBeTruthy();
    const storedThread = localStorage.getItem(threadStorageKey("longmont-c2", String(activeThreadId)));
    expect(storedThread).toBeTruthy();
    const parsed = JSON.parse(String(storedThread)) as { turns: Array<{ question: string; answer: string }> };
    expect(parsed.turns.length).toBe(2);
    expect(parsed.turns[0].question).toBe("Second question?");
    expect(parsed.turns[0].answer).toBe("Second answer");
    expect(JSON.stringify(parsed)).not.toMatch(/context_packet|text_excerpt/);
    expect(storedThread).not.toMatch(/context_packet/);
    expect(storedThread).not.toMatch(/text_excerpt/);
    expect(storedThread).not.toMatch(/prompt_preview/);
    expect(storedThread).not.toMatch(/Retrieved evidence excerpts/);
    expect(storedThread).not.toMatch(/\/tmp\/hermes/);

    await user.click(screen.getByRole("button", { name: "Clear history" }));
    expect(screen.queryByRole("region", { name: "Conversation transcript" })).not.toBeInTheDocument();
    const clearedThreadId = localStorage.getItem(activeThreadStorageKey("longmont-c2", "plan", FIXTURE_DOC_ID));
    const clearedThread = JSON.parse(String(localStorage.getItem(threadStorageKey("longmont-c2", String(clearedThreadId))))) as { turns: unknown[] };
    expect(clearedThread.turns).toEqual([]);
  });

  it("migrates existing active threads into the switcher and renames the active thread", async () => {
    const user = userEvent.setup();
    const existingThread = {
      ...createAgentInteractionThread("longmont-c2", 23, "plan", "hermes", "Session 24 inn prep", FIXTURE_DOC_ID),
      turns: [{
        turnId: "turn-existing",
        askedAt: "2026-06-22T00:00:00.000Z",
        completedAt: "2026-06-22T00:00:01.000Z",
        question: "What do we know about the inn?",
        answer: "The inn has Mireward rumors.",
        backend: "hermes" as const,
        status: "ok",
        contextSummary: { admitted_count: 1, rejected_count: 0 },
        citations: [],
        trace: null,
        warnings: [],
      }],
      uiState: { traceVisible: true, scrollAnchorTurnId: "turn-existing" },
    };
    localStorage.setItem(activeThreadStorageKey("longmont-c2", "plan", FIXTURE_DOC_ID), existingThread.threadId);
    localStorage.setItem(threadStorageKey("longmont-c2", existingThread.threadId), JSON.stringify(existingThread));

    vi.spyOn(globalThis, "fetch").mockResolvedValue({
      ok: true,
      text: async () => JSON.stringify(mockSourceBundle),
    } as Response);

    renderPlanSurface();
    await waitForPlanSurfaceReady();

    await user.click(screen.getByRole("button", { name: "Open drawer" }));
    await screen.findByText("Session 24 inn prep");
    expect(screen.getByText("The inn has Mireward rumors.")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Prep threads" }));
    const switcher = screen.getByRole("region", { name: "DungeonBuddy threads" });
    expect(switcher).toHaveTextContent("Session 24 inn prep");
    expect(localStorage.getItem(threadIndexStorageKey("longmont-c2", "plan", FIXTURE_DOC_ID))).toContain("Session 24 inn prep");

    await user.click(screen.getByRole("button", { name: "Rename" }));
    await user.clear(screen.getByLabelText("Prep thread title"));
    await user.type(screen.getByLabelText("Prep thread title"), "Mireward inn prep");
    await user.click(screen.getByRole("button", { name: "Save title" }));

    expect(screen.getAllByText("Mireward inn prep").length).toBeGreaterThan(0);
    expect(screen.getByRole("heading", { name: "Mireward inn prep" })).toBeInTheDocument();
    expect(localStorage.getItem(threadIndexStorageKey("longmont-c2", "plan", FIXTURE_DOC_ID))).toContain("Mireward inn prep");
  });

  it("keeps questions isolated across named threads and resets source reader when switching", async () => {
    const user = userEvent.setup();
    const queryResponse = (answer: string, evidenceId: string) => ({
      answer,
      classification: {},
      events_written: [],
      jobs_queued: [],
      next_suggestions: [],
      diagnostics: [],
      provenance: {},
      citations: [{ evidence_id: evidenceId, path: `corpus/test/${evidenceId}.md`, line_start: 1, line_end: 1, source_role: "play_recap", authority: "canon_play" }],
      context_packet: {
        admitted_evidence: [{ evidence_id: evidenceId, path: `corpus/test/${evidenceId}.md`, source_role: "play_recap", authority: "canon_play", line_start: 1, line_end: 1 }],
        rejected_evidence: [],
      },
    });
    vi.spyOn(globalThis, "fetch")
      .mockResolvedValueOnce({ ok: true, text: async () => JSON.stringify(mockSourceBundle) } as Response)
      .mockResolvedValueOnce({ ok: true, text: async () => JSON.stringify(queryResponse("Answer for thread A", "a")) } as Response)
      .mockResolvedValueOnce({
        ok: true,
        text: async () => JSON.stringify({
          schema_version: "dmb_citation_source_v1",
          path: "corpus/test/a.md",
          content_type: "text/markdown",
          content: "Thread A source body",
          truncated: false,
          highlight: { line_start: 1, line_end: 1, text_excerpt: "Thread A source body", match_source: "line_range" },
          diagnostics: [],
        }),
      } as Response)
      .mockResolvedValueOnce({ ok: true, text: async () => JSON.stringify(queryResponse("Answer for thread B", "b")) } as Response);

    renderPlanSurface();
    await waitForPlanSurfaceReady();

    await user.click(screen.getByRole("button", { name: "Open drawer" }));
    await screen.findByText("World graph (all sessions)");
    await user.type(screen.getByLabelText("Question"), "Thread A question?");
    await user.click(screen.getByRole("button", { name: "Ask DungeonBuddy" }));
    expect(await screen.findByText("Answer for thread A")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Open source" }));
    expect(await screen.findByRole("region", { name: "Source preview" })).toHaveTextContent("Thread A source body");

    await user.click(screen.getByRole("button", { name: "New prep thread" }));
    expect(screen.queryByText("Answer for thread A")).not.toBeInTheDocument();
    expect(screen.queryByRole("region", { name: "Source preview" })).not.toBeInTheDocument();
    await user.type(screen.getByLabelText("Question"), "Thread B question?");
    await user.click(screen.getByRole("button", { name: "Ask DungeonBuddy" }));
    expect(await screen.findByText("Answer for thread B")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Prep threads" }));
    await user.click(screen.getAllByRole("button", { name: /Thread A question/i })[0]);
    expect(await screen.findByText("Answer for thread A")).toBeInTheDocument();
    expect(screen.queryByText("Answer for thread B")).not.toBeInTheDocument();

    const indexJson = localStorage.getItem(threadIndexStorageKey("longmont-c2", "plan", FIXTURE_DOC_ID)) ?? "";
    expect(indexJson).toContain("Thread A question?");
    expect(indexJson).toContain("Thread B question?");
    expect(indexJson).not.toContain("Answer for thread A");
    const activeThreadId = localStorage.getItem(activeThreadStorageKey("longmont-c2", "plan", FIXTURE_DOC_ID));
    expect(localStorage.getItem(threadStorageKey("longmont-c2", activeThreadId ?? "")) ?? "").not.toContain("Thread A source body");
  });


  it("suggests a new thread at the turn threshold and lets the GM dismiss it", async () => {
    const user = userEvent.setup();
    const responses = Array.from({ length: AGENT_THREAD_SUGGEST_NEW_AFTER_TURNS }, (_, index) => ({
      ok: true,
      text: async () => JSON.stringify({
        answer: `Answer ${index + 1}`,
        classification: {},
        events_written: [],
        jobs_queued: [],
        next_suggestions: [],
        diagnostics: [],
        provenance: {},
        citations: [],
        context_packet: null,
      }),
    } as Response));
    vi.spyOn(globalThis, "fetch")
      .mockResolvedValueOnce({ ok: true, text: async () => JSON.stringify(mockSourceBundle) } as Response);
    const fetchMock = vi.mocked(globalThis.fetch);
    responses.forEach((response) => fetchMock.mockResolvedValueOnce(response));

    renderPlanSurface();
    await waitForPlanSurfaceReady();
    await user.click(screen.getByRole("button", { name: "Open drawer" }));
    await screen.findByText("World graph (all sessions)");

    for (let index = 1; index <= AGENT_THREAD_SUGGEST_NEW_AFTER_TURNS; index += 1) {
      await user.type(screen.getByLabelText("Question"), `Question ${index}?`);
      await user.click(screen.getByRole("button", { name: "Ask DungeonBuddy" }));
      expect(await screen.findByText(`Answer ${index}`)).toBeInTheDocument();
    }

    expect(screen.getByRole("region", { name: "Thread getting long" })).toHaveTextContent(
      `This thread has ${AGENT_THREAD_SUGGEST_NEW_AFTER_TURNS} turns. Start a new prep thread for a fresh topic?`,
    );
    const originalThreadId = localStorage.getItem(activeThreadStorageKey("longmont-c2", "plan", FIXTURE_DOC_ID));
    await user.click(screen.getByRole("button", { name: "Keep going" }));
    expect(screen.queryByRole("region", { name: "Thread getting long" })).not.toBeInTheDocument();
    expect(localStorage.getItem(activeThreadStorageKey("longmont-c2", "plan", FIXTURE_DOC_ID))).toBe(originalThreadId);
    expect(JSON.parse(localStorage.getItem(threadStorageKey("longmont-c2", originalThreadId ?? "")) ?? "{}").uiState.newThreadSuggestionDismissed).toBe(true);
  });

  it("shows the suggestion again after dismissing then clearing history", async () => {
    const user = userEvent.setup();
    const responses = Array.from({ length: AGENT_THREAD_SUGGEST_NEW_AFTER_TURNS * 2 }, (_, index) => ({
      ok: true,
      text: async () => JSON.stringify({
        answer: `Clear reset answer ${index + 1}`,
        classification: {},
        events_written: [],
        jobs_queued: [],
        next_suggestions: [],
        diagnostics: [],
        provenance: {},
        citations: [],
        context_packet: null,
      }),
    } as Response));
    const fetchMock = vi.spyOn(globalThis, "fetch")
      .mockResolvedValueOnce({ ok: true, text: async () => JSON.stringify(mockSourceBundle) } as Response);
    responses.forEach((response) => fetchMock.mockResolvedValueOnce(response));

    renderPlanSurface();
    await waitForPlanSurfaceReady();
    await user.click(screen.getByRole("button", { name: "Open drawer" }));
    await screen.findByText("World graph (all sessions)");

    for (let index = 1; index <= AGENT_THREAD_SUGGEST_NEW_AFTER_TURNS; index += 1) {
      fireEvent.change(screen.getByLabelText("Question"), { target: { value: `Before clear ${index}?` } });
      fireEvent.click(screen.getByRole("button", { name: "Ask DungeonBuddy" }));
      expect(await screen.findByText(`Clear reset answer ${index}`)).toBeInTheDocument();
    }

    await user.click(screen.getByRole("button", { name: "Keep going" }));
    expect(screen.queryByRole("region", { name: "Thread getting long" })).not.toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Clear history" }));
    expect(screen.queryByRole("region", { name: "Conversation transcript" })).not.toBeInTheDocument();

    for (let index = 1; index <= AGENT_THREAD_SUGGEST_NEW_AFTER_TURNS; index += 1) {
      fireEvent.change(screen.getByLabelText("Question"), { target: { value: `After clear ${index}?` } });
      fireEvent.click(screen.getByRole("button", { name: "Ask DungeonBuddy" }));
      expect(await screen.findByText(`Clear reset answer ${AGENT_THREAD_SUGGEST_NEW_AFTER_TURNS + index}`)).toBeInTheDocument();
    }

    expect(screen.getByRole("region", { name: "Thread getting long" })).toHaveTextContent(
      `This thread has ${AGENT_THREAD_SUGGEST_NEW_AFTER_TURNS} turns. Start a new prep thread for a fresh topic?`,
    );
  });

  it("starts an empty active thread only when the long-thread suggestion is accepted", async () => {
    const user = userEvent.setup();
    const responses = Array.from({ length: AGENT_THREAD_SUGGEST_NEW_AFTER_TURNS }, (_, index) => ({
      ok: true,
      text: async () => JSON.stringify({ answer: `Long answer ${index + 1}`, classification: {}, events_written: [], jobs_queued: [], next_suggestions: [], diagnostics: [], provenance: {}, citations: [], context_packet: null }),
    } as Response));
    const fetchMock = vi.spyOn(globalThis, "fetch")
      .mockResolvedValueOnce({ ok: true, text: async () => JSON.stringify(mockSourceBundle) } as Response);
    responses.forEach((response) => fetchMock.mockResolvedValueOnce(response));

    renderPlanSurface();
    await waitForPlanSurfaceReady();
    await user.click(screen.getByRole("button", { name: "Open drawer" }));
    await screen.findByText("World graph (all sessions)");
    expect(screen.queryByRole("region", { name: "Thread getting long" })).not.toBeInTheDocument();

    for (let index = 1; index <= AGENT_THREAD_SUGGEST_NEW_AFTER_TURNS; index += 1) {
      await user.type(screen.getByLabelText("Question"), `Long question ${index}?`);
      await user.click(screen.getByRole("button", { name: "Ask DungeonBuddy" }));
      expect(await screen.findByText(`Long answer ${index}`)).toBeInTheDocument();
    }

    await user.click(screen.getByRole("button", { name: "Start new thread" }));
    expect(screen.getByRole("heading", { name: "New prep thread" })).toBeInTheDocument();
    expect(screen.queryByRole("region", { name: "Conversation transcript" })).not.toBeInTheDocument();
    const activeThreadId = localStorage.getItem(activeThreadStorageKey("longmont-c2", "plan", FIXTURE_DOC_ID));
    const activeThread = JSON.parse(localStorage.getItem(threadStorageKey("longmont-c2", activeThreadId ?? "")) ?? "{}");
    expect(activeThread.title).toBe("New prep thread");
    expect(activeThread.turns).toEqual([]);
  });

  it("restores active thread and thread list after remount", async () => {
    const user = userEvent.setup();
    vi.spyOn(globalThis, "fetch")
      .mockResolvedValueOnce({ ok: true, text: async () => JSON.stringify(mockSourceBundle) } as Response)
      .mockResolvedValueOnce({ ok: true, text: async () => JSON.stringify({ answer: "Answer for restore A", classification: {}, events_written: [], jobs_queued: [], next_suggestions: [], diagnostics: [], provenance: {}, citations: [], context_packet: null }) } as Response)
      .mockResolvedValueOnce({ ok: true, text: async () => JSON.stringify({ answer: "Answer for restore B", classification: {}, events_written: [], jobs_queued: [], next_suggestions: [], diagnostics: [], provenance: {}, citations: [], context_packet: null }) } as Response)
      .mockResolvedValue({ ok: true, text: async () => JSON.stringify(mockSourceBundle) } as Response);

    const rendered = renderPlanSurface();
    await waitForPlanSurfaceReady();
    await user.click(screen.getByRole("button", { name: "Open drawer" }));
    await screen.findByText("World graph (all sessions)");
    await user.type(screen.getByLabelText("Question"), "Restore thread A?");
    await user.click(screen.getByRole("button", { name: "Ask DungeonBuddy" }));
    expect(await screen.findByText("Answer for restore A")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "New prep thread" }));
    await user.type(screen.getByLabelText("Question"), "Restore thread B?");
    await user.click(screen.getByRole("button", { name: "Ask DungeonBuddy" }));
    expect(await screen.findByText("Answer for restore B")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Prep threads" }));
    await user.click(screen.getAllByRole("button", { name: /Restore thread A\?/i })[0]);
    expect(await screen.findByText("Answer for restore A")).toBeInTheDocument();

    rendered.unmount();
    renderPlanSurface();
    await waitForPlanSurfaceReady();
    await user.click(screen.getByRole("button", { name: "Open drawer" }));
    expect(await screen.findByText("Answer for restore A")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Prep threads" }));
    const switcher = screen.getByRole("region", { name: "DungeonBuddy threads" });
    expect(switcher).toHaveTextContent("Restore thread A?");
    expect(switcher).toHaveTextContent("Restore thread B?");
    expect(screen.getByRole("heading", { name: "Restore thread A?" })).toBeInTheDocument();
  });

  it("ignores corrupt thread index localStorage", async () => {
    const user = userEvent.setup();
    localStorage.setItem(threadIndexStorageKey("longmont-c2", "plan", FIXTURE_DOC_ID), "{not-json");
    vi.spyOn(globalThis, "fetch").mockResolvedValue({
      ok: true,
      text: async () => JSON.stringify(mockSourceBundle),
    } as Response);

    renderPlanSurface();
    await waitForPlanSurfaceReady();
    await user.click(screen.getByRole("button", { name: "Open drawer" }));
    await screen.findByText("World graph (all sessions)");
    await user.click(screen.getByRole("button", { name: "Prep threads" }));
    expect(screen.getByText("No saved prep threads yet.")).toBeInTheDocument();
  });

  it("shows weak context verdict for metadata-only admitted evidence", async () => {
    const user = userEvent.setup();
    vi.spyOn(globalThis, "fetch")
      .mockResolvedValueOnce({
        ok: true,
        text: async () => JSON.stringify(mockSourceBundle),
      } as Response)
      .mockResolvedValueOnce({
        ok: true,
        text: async () =>
          JSON.stringify({
            answer: "Should not appear as primary.",
            classification: {},
            events_written: [],
            jobs_queued: [],
            next_suggestions: [],
            diagnostics: [],
            provenance: {},
            citations: [],
            context_packet: {
              schema: "dmb_enriched_planning_context_packet_v1",
              question_id: "weak-1",
              intent_class: "play_fact_retrieval",
              admitted_evidence: [{
                path: "evals/c2_live_prep/live/session_23/live_packet.json",
                source_role: "live_packet",
                authority: "planning_scaffold",
                text_excerpt: '{"schema_version":"0.1.0","summary":"Fresh recap ingested"}',
              }],
              rejected_evidence: [],
            },
          }),
      } as Response);

    renderPlanSurface();
    await waitForPlanSurfaceReady();

    await user.click(screen.getByRole("button", { name: "Open drawer" }));
    await screen.findByText("World graph (all sessions)");
    await user.type(screen.getByLabelText("Question"), "What happened at bootstrap?");
    await user.click(screen.getByRole("button", { name: "Ask DungeonBuddy" }));

    expect(await screen.findByText("Preliminary verdict · Weak context")).toBeInTheDocument();
    expect(screen.getByText(/operational metadata/i)).toBeInTheDocument();
    expect(screen.getByText("Retrieved text (1)")).toBeInTheDocument();
  });

  it("shows broad recap routes in retrieved text", async () => {
    const user = userEvent.setup();
    vi.spyOn(globalThis, "fetch")
      .mockResolvedValueOnce({
        ok: true,
        text: async () => JSON.stringify(mockSourceBundle),
      } as Response)
      .mockResolvedValueOnce({
        ok: true,
        text: async () =>
          JSON.stringify({
            answer: "fallback",
            classification: {},
            events_written: [],
            jobs_queued: [],
            next_suggestions: [],
            diagnostics: [],
            provenance: {},
            citations: [],
            context_packet: {
              schema: "dmb_enriched_planning_context_packet_v1",
              question_id: "broad-1",
              intent_class: "play_fact_retrieval",
              admitted_evidence: [
                {
                  path: "corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/Session Recaps/_normalized/Session 21 - Drake Nest Mirathorn Call.md",
                  source_role: "session_memory",
                  authority: "derived_memory",
                },
                {
                  path: "corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/Session Recaps/_normalized/Session 22 - Mireward Road and Lysandro.md",
                  source_role: "session_memory",
                  authority: "derived_memory",
                },
              ],
              rejected_evidence: [],
            },
          }),
      } as Response);

    renderPlanSurface();
    await waitForPlanSurfaceReady();

    await user.click(screen.getByRole("button", { name: "Open drawer" }));
    await screen.findByText("World graph (all sessions)");
    await user.type(screen.getByLabelText("Question"), "What carried over from prior sessions?");
    await user.click(screen.getByRole("button", { name: "Ask DungeonBuddy" }));

    expect(await screen.findByText("Retrieved text (2)")).toBeInTheDocument();
    expect(screen.getAllByText(/Session 21 - Drake Nest Mirathorn Call.md/).length).toBeGreaterThan(0);
    expect(screen.getByText("Preliminary verdict · Weak context")).toBeInTheDocument();
  });

  it("applies spike theme tokens at the surface root", async () => {
    const { container } = renderPlanSurface();
    await waitForPlanSurfaceReady();
    const root = container.querySelector(".plan-surface-root");
    expect(root).toHaveAttribute("data-md-theme", "mireward-runbook");
    expect(root).toHaveStyle({ "--accent": "#7aa2f7" });
  });

  it("opens recap projection from the toolbar registry", async () => {
    const user = userEvent.setup();
    vi.spyOn(globalThis, "fetch").mockResolvedValue({
      ok: true,
      json: async () => ({ records: [] }),
    } as Response);
    renderPlanSurface();
    await waitForPlanSurfaceReady();

    await user.click(screen.getByRole("button", { name: "Tools" }));

    expect(screen.getByRole("complementary", { name: /Recap projection/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Recap" })).toHaveAttribute("aria-pressed", "true");
  });

  it("opens statblock projection from the toolbar registry", async () => {
    const user = userEvent.setup();
    renderPlanSurface();
    await waitForPlanSurfaceReady();

    await user.click(screen.getByRole("button", { name: "Tools" }));
    await user.click(screen.getByRole("button", { name: "Statblock" }));

    expect(screen.getByRole("complementary", { name: /Statblock projection/i })).toBeInTheDocument();
  });

  it("projects reference chip resolution through the shared container", async () => {
    const user = userEvent.setup();
    vi.mocked(liveApi.postWorldGraphProjection).mockRestore();
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockImplementation(async (input, init) => {
      const url = String(input);
      if (url === "/api/live/world-graph/projection") {
        expect(init?.method).toBe("POST");
        expect(JSON.parse(String(init?.body))).toEqual({
          schema: "dmb_world_graph_projection_request_v1",
          worldId: "eldyrwild",
          campaignId: "longmont-c2",
          focus: { kind: "none", sessionId: null },
          admissibility: "gm",
        });
        return {
          ok: true,
          text: async () => JSON.stringify(worldGraphProjection),
        } as Response;
      }
      return {
        ok: true,
        json: async () => ({
          locations: [{
            index_id: "north-reach-gate",
            title: "North Reach Gate",
            corpus_display_path: "corpus/locations/north_reach_gate.md",
          }],
        }),
      } as Response;
    });

    renderPlanSurface();
    await waitForPlanSurfaceReady();

    await waitFor(() => {
      expect(screen.getByLabelText("Find objects")).toBeInTheDocument();
    });

    const canvas = screen.getByTestId("plan-surface-canvas-editor");
    const chip = canvas.querySelector(".md-ref-chip") as HTMLElement;
    fireEvent.click(chip);

    await waitFor(() => {
      expect(screen.getByRole("complementary", { name: /North Reach Gate projection/i })).toBeInTheDocument();
    });
    const projection = screen.getByRole("complementary", { name: /North Reach Gate projection/i });
    expect(screen.getByTestId("plan-reference-fallback-banner")).toHaveTextContent(
      /Graph memory did not resolve this yet/i,
    );
    expect(within(projection).getByLabelText(/North Reach Gate corpus fallback object/i)).toBeInTheDocument();
    expect(within(projection).getByText(/Location reference resolved from corpus index/i)).toBeInTheDocument();
    expect(within(projection).queryByLabelText(/selected object/i)).not.toBeInTheDocument();
    expect(fetchSpy).toHaveBeenCalledWith(
      "/api/live/world-graph/projection",
      expect.objectContaining({ method: "POST" }),
    );
  });

  it("shows Markdown save control in the edit toolbar", async () => {
    renderPlanSurface();
    await waitForPlanSurfaceReady();

    expect(screen.getByRole("button", { name: "Save to Markdown" })).toBeInTheDocument();
  });

  it("saves Markdown for the active planning document", async () => {
    const user = userEvent.setup();
    const planTarget =
      "corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/Session Prep/Session 23 Prep.md";
    const fetchSpy = vi.spyOn(globalThis, "fetch")
      .mockResolvedValueOnce({
        ok: true,
        text: async () =>
          JSON.stringify({
            schema_version: "dmb_tiptap_markdown_write_prepare_v1",
            document_id: FIXTURE_DOC_ID,
            title: "C2 Session 23 Prep",
            target_relpath: planTarget,
            target_display_path: planTarget,
            file_exists: false,
            writer_ok: true,
            writer_phase: "prepare",
            writer_confirm_token: "confirm-token",
            writer_diff: "+# C2 Session 23 Prep\n",
            warnings: [],
            diagnostics: ["dry-run only; no file was written"],
          }),
      } as Response)
      .mockResolvedValueOnce({
        ok: true,
        text: async () =>
          JSON.stringify({
            schema_version: "dmb_tiptap_markdown_write_commit_v1",
            document_id: FIXTURE_DOC_ID,
            title: "C2 Session 23 Prep",
            target_relpath: planTarget,
            target_display_path: planTarget,
            writer_ok: true,
            writer_phase: "commit",
            bytes_written: 42,
            file_fingerprint: "abc123",
            diagnostics: ["reviewed Markdown file written"],
          }),
      } as Response);

    renderPlanSurface();
    await waitForPlanSurfaceReady();

    await user.click(screen.getByRole("button", { name: "Save to Markdown" }));

    await waitFor(() => {
      expect(screen.getByTestId("plan-markdown-save-success")).toBeInTheDocument();
    });
    expect(fetchSpy.mock.calls[0][0]).toBe("/api/live/tiptap/markdown-write/prepare");
    const prepareBody = JSON.parse(String(fetchSpy.mock.calls[0][1]?.body));
    expect(prepareBody.document_id).toBe(FIXTURE_DOC_ID);
    expect(prepareBody.markdown).toContain("C2 Session 23 Prep");
    expect(prepareBody).not.toHaveProperty("target_relpath");
    expect(fetchSpy.mock.calls[1][0]).toBe("/api/live/tiptap/markdown-write/commit");
    expect(JSON.parse(String(fetchSpy.mock.calls[1][1]?.body)).writer_confirm_token).toBe("confirm-token");
    expect(screen.getByTestId("plan-markdown-save-success")).toBeInTheDocument();
    expect(screen.getByTestId("plan-canvas-save-status")).toHaveTextContent(/Saved to Markdown/i);
  });

  function buildHermesGraphGrounding(
    state: "grounded" | "partial" | "abstained" | "error",
    overrides: Record<string, unknown> = {},
  ) {
    return {
      schema: "dmb_hermes_graph_grounding_v1",
      state,
      world_id: "eldyrwild",
      campaign_id: "longmont-c2",
      focus: { kind: "session", session_id: "session-21" },
      admissibility: "gm",
      revision_id: "rev-pinned-1",
      successful_tool_count: state === "error" ? 0 : 1,
      source_anchor_count: state === "grounded" || state === "partial" ? 1 : 0,
      diagnostic_codes: state === "error" ? ["graph_query_failed"] : [],
      warnings: state === "partial" ? ["partial graph evidence"] : [],
      ...overrides,
    };
  }

  function buildGraphAnchorCitation(revisionId = "rev-pinned-1") {
    return {
      schema: "dmb_world_graph_anchor_citation_v1",
      kind: "world_graph_anchor",
      anchor_id: "source-anchor:v1:fixture-anchor",
      world_id: "eldyrwild",
      campaign_id: "longmont-c2",
      focus: { kind: "session", session_id: "session-21" },
      admissibility: "gm",
      revision_id: revisionId,
    };
  }

  function buildHermesGraphQueryResponse(overrides: Record<string, unknown> = {}) {
    return {
      answer: "Tripod stands at the North Gate.",
      classification: { latency_mode: "hermes_graph_agent", event_type: "hermes_graph_agent" },
      mode: "hermes_graph_agent",
      status: "ok",
      events_written: [],
      jobs_queued: [],
      next_suggestions: [],
      diagnostics: {},
      provenance: { backend: "hermes", runtime: "process_isolated" },
      citations: [buildGraphAnchorCitation()],
      context_packet: null,
      grounding: buildHermesGraphGrounding("grounded"),
      agent_trace: {
        trace_id: "agent-trace-pr355",
        runtime: "process_isolated",
        backend: "hermes",
        mode: "hermes_graph_agent",
        started_at: "2026-07-14T18:00:00Z",
        completed_at: "2026-07-14T18:00:01Z",
        elapsed_ms: 88,
        status: "ok",
        usage: { available: false, input_tokens: null, output_tokens: null, total_tokens: null },
        steps: [],
        context_summary: {},
        artifact_refs: [],
        tool_events: [{
          tool_name: "search_campaign_graph",
          state: "completion",
          duration_ms: 20,
          outcome: "enough",
          world_id: "eldyrwild",
          campaign_id: "longmont-c2",
          revision_pin: "rev-pinned-1",
          focus: { kind: "session", session_id: "session-21" },
          admissibility: "gm",
          matched_node_ids: ["node-tripod"],
          relationship_ids: [],
          source_anchor_ids: ["source-anchor:v1:fixture-anchor"],
          diagnostic_codes: [],
          bounded_ids: {},
          retrieval_schema: null,
        }],
        warnings: [],
      },
      hermes_session: null,
      ...overrides,
    };
  }

  it("keeps Hermes interaction UI available when the source bundle fails to load", async () => {
    const user = userEvent.setup();
    vi.spyOn(globalThis, "fetch").mockImplementation(async (input) => {
      const url = String(input);
      if (url.includes("/api/live/source-bundle")) {
        return { ok: false, status: 500, text: async () => "bundle failed" } as Response;
      }
      if (url.includes("/api/live/query")) {
        return {
          ok: true,
          text: async () => JSON.stringify(buildHermesGraphQueryResponse()),
        } as Response;
      }
      return { ok: true, text: async () => "{}" } as Response;
    });

    renderPlanSurface();
    await waitForPlanSurfaceReady();

    await user.click(screen.getByRole("button", { name: "Open drawer" }));
    expect(await screen.findByLabelText("Question")).toBeInTheDocument();
    await user.type(screen.getByLabelText("Question"), "Where is Tripod?");
    await user.click(screen.getByRole("button", { name: "Ask DungeonBuddy" }));
    await user.click(await screen.findByRole("button", { name: "Trace On" }));

    expect(await screen.findByRole("region", { name: "Hermes reply" })).toBeInTheDocument();
    await user.click(screen.getByText("Memory coverage diagnostics"));
    expect(document.querySelector(".plan-agent-diagnostics-drawer .plan-agent-error")).toBeTruthy();
    expect(vi.mocked(globalThis.fetch).mock.calls.some(([url]) => String(url).includes("/api/live/query"))).toBe(true);
  });

  it.each([
    ["grounded", true] as const,
    ["partial", true] as const,
    ["abstained", false] as const,
    ["error", false] as const,
  ])("renders Hermes graph grounding state %s", async (state, showCards) => {
    const user = userEvent.setup();
    vi.spyOn(globalThis, "fetch")
      .mockResolvedValueOnce({ ok: true, text: async () => JSON.stringify(mockSourceBundle) } as Response)
      .mockResolvedValueOnce({
        ok: true,
        text: async () => JSON.stringify(buildHermesGraphQueryResponse({
          answer: `${state} answer`,
          grounding: buildHermesGraphGrounding(state),
          citations: showCards ? [buildGraphAnchorCitation()] : [],
          agent_trace: {
            ...buildHermesGraphQueryResponse().agent_trace,
            trace_id: `agent-trace-${state}`,
          },
        })),
      } as Response);

    renderPlanSurface();
    await waitForPlanSurfaceReady();
    await user.click(screen.getByRole("button", { name: "Open drawer" }));
    await user.type(screen.getByLabelText("Question"), `${state} question?`);
    await user.click(screen.getByRole("button", { name: "Ask DungeonBuddy" }));
    await user.click(await screen.findByRole("button", { name: /Trace On/i }));

    expect(await screen.findByRole("region", { name: "Hermes reply" })).toHaveTextContent(`${state} answer`);
    if (showCards) {
      expect(screen.getByRole("region", { name: "Graph evidence" })).toBeInTheDocument();
    } else {
      expect(screen.queryByRole("region", { name: "Graph evidence" })).not.toBeInTheDocument();
    }
    if (state === "abstained") {
      expect(screen.queryByText(/No grounded evidence returned/i)).not.toBeInTheDocument();
    }
    if (state === "error") {
      expect(screen.getByText("graph_query_failed")).toBeInTheDocument();
    }
  });

  it("shows contract error for grounded Hermes graph answer with scope-mismatched citation", async () => {
    const user = userEvent.setup();
    vi.spyOn(globalThis, "fetch")
      .mockResolvedValueOnce({ ok: true, text: async () => JSON.stringify(mockSourceBundle) } as Response)
      .mockResolvedValueOnce({
        ok: true,
        text: async () => JSON.stringify(buildHermesGraphQueryResponse({
          answer: "Citation scope mismatch answer.",
          citations: [buildGraphAnchorCitation("rev-wrong-revision")],
        })),
      } as Response);

    renderPlanSurface();
    await waitForPlanSurfaceReady();
    await user.click(screen.getByRole("button", { name: "Open drawer" }));
    await user.type(screen.getByLabelText("Question"), "Scope mismatch question?");
    await user.click(screen.getByRole("button", { name: "Ask DungeonBuddy" }));
    await user.click(await screen.findByRole("button", { name: /Trace On/i }));

    expect(await screen.findByRole("region", { name: "Hermes reply" })).toHaveTextContent(
      "Citation scope mismatch answer.",
    );
    expect(screen.queryByRole("region", { name: "Graph evidence" })).not.toBeInTheDocument();
    expect(screen.getByText(/graph citations were dropped due to scope or revision mismatch/i)).toBeInTheDocument();
  });

  it("clears stale hermesSession after Hermes graph submit and omits it from subsequent live asks", async () => {
    const user = userEvent.setup();
    const staleSession = {
      sessionId: "stale-hermes-session-handle",
      runtime: "api",
      title: "Stale Hermes session",
    };
    const seededThread = {
      ...createAgentInteractionThread("longmont-c2", 22, "plan", "live", "Stale session thread", FIXTURE_DOC_ID),
      hermesSession: staleSession,
    };
    localStorage.setItem(activeThreadStorageKey("longmont-c2", "plan", FIXTURE_DOC_ID), seededThread.threadId);
    localStorage.setItem(threadStorageKey("longmont-c2", seededThread.threadId), JSON.stringify(seededThread));

    vi.spyOn(globalThis, "fetch")
      .mockResolvedValueOnce({ ok: true, text: async () => JSON.stringify(mockSourceBundle) } as Response)
      .mockResolvedValueOnce({
        ok: true,
        text: async () => JSON.stringify(buildHermesGraphQueryResponse({
          hermes_session: {
            sessionId: "malformed-should-not-persist",
            runtime: "api",
            title: "Bad session from response",
          },
        })),
      } as Response)
      .mockResolvedValueOnce({
        ok: true,
        text: async () => JSON.stringify({
          answer: "Follow-up live answer.",
          classification: {},
          events_written: [],
          jobs_queued: [],
          next_suggestions: [],
          diagnostics: [],
          provenance: {},
          citations: [],
          context_packet: null,
        }),
      } as Response);

    renderPlanSurface();
    await waitForPlanSurfaceReady();
    await user.click(screen.getByRole("button", { name: "Open drawer" }));
    await screen.findByText("Stale session thread");
    await user.type(screen.getByLabelText("Question"), "Hermes graph question?");
    await user.click(screen.getByRole("button", { name: "Ask DungeonBuddy" }));
    await user.click(await screen.findByRole("button", { name: /Trace On/i }));
    expect(await screen.findByRole("region", { name: "Hermes reply" })).toBeInTheDocument();

    const storedAfterGraph = JSON.parse(
      localStorage.getItem(threadStorageKey("longmont-c2", seededThread.threadId)) ?? "{}",
    );
    expect(storedAfterGraph.hermesSession).toBeNull();

    await user.type(screen.getByLabelText("Question"), "Follow-up live question?");
    await user.click(screen.getByRole("button", { name: "Ask DungeonBuddy" }));
    expect(await screen.findByText("Follow-up live answer.")).toBeInTheDocument();

    const followUpCall = vi.mocked(globalThis.fetch).mock.calls[2];
    const followUpBody = JSON.parse(String(followUpCall[1]?.body));
    expect(followUpBody.hermes_session_id).toBeNull();
  });

  it("opens graph citations through the opaque source-anchor read route with pinned revision", async () => {
    const user = userEvent.setup();
    vi.spyOn(globalThis, "fetch")
      .mockResolvedValueOnce({ ok: true, text: async () => JSON.stringify(mockSourceBundle) } as Response)
      .mockResolvedValueOnce({
        ok: true,
        text: async () => JSON.stringify(buildHermesGraphQueryResponse()),
      } as Response)
      .mockResolvedValueOnce({
        ok: true,
        text: async () => JSON.stringify({
          schema: "dmb_world_graph_source_anchor_read_v1",
          outcome: "enough",
          anchorId: "source-anchor:v1:fixture-anchor",
          truncated: false,
          content: "Pinned anchor body from graph memory.",
          diagnostics: [],
          snapshot: {
            worldId: "eldyrwild",
            campaignId: "longmont-c2",
            revisionId: "rev-pinned-1",
            headRevisionId: "rev-pinned-1",
            isHead: true,
            focus: { kind: "session", sessionId: "session-21" },
            admissibility: "gm",
          },
        }),
      } as Response);

    renderPlanSurface();
    await waitForPlanSurfaceReady();

    await user.click(screen.getByRole("button", { name: "Open drawer" }));
    await user.type(screen.getByLabelText("Question"), "Where is Tripod?");
    await user.click(screen.getByRole("button", { name: "Ask DungeonBuddy" }));
    await user.click(await screen.findByRole("button", { name: "Open evidence" }));

    expect(await screen.findByRole("region", { name: "Graph evidence preview" })).toHaveTextContent(
      "Pinned anchor body from graph memory.",
    );
    const readCall = vi.mocked(globalThis.fetch).mock.calls.find(([url]) =>
      String(url).includes("/api/live/world-graph/retrieval/source-anchor/read"),
    );
    expect(readCall).toBeTruthy();
    expect(JSON.parse(String(readCall?.[1]?.body))).toEqual({
      schema: "dmb_world_graph_source_anchor_read_request_v1",
      worldId: "eldyrwild",
      campaignId: "longmont-c2",
      focus: { kind: "session", sessionId: "session-21" },
      admissibility: "gm",
      revisionPin: "rev-pinned-1",
      anchorId: "source-anchor:v1:fixture-anchor",
      maxChars: 4000,
    });
    expect(vi.mocked(globalThis.fetch).mock.calls.some(([url]) => String(url).includes("/api/live/citation-source"))).toBe(false);
  });

  it("shows no graph evidence content when the source-anchor read contradicts the citation contract", async () => {
    const user = userEvent.setup();
    vi.spyOn(globalThis, "fetch")
      .mockResolvedValueOnce({ ok: true, text: async () => JSON.stringify(mockSourceBundle) } as Response)
      .mockResolvedValueOnce({
        ok: true,
        text: async () => JSON.stringify(buildHermesGraphQueryResponse()),
      } as Response)
      .mockResolvedValueOnce({
        ok: true,
        text: async () => JSON.stringify({
          schema: "dmb_world_graph_source_anchor_read_v1",
          outcome: "enough",
          anchorId: "source-anchor:v1:fixture-anchor",
          truncated: false,
          content: "Contradictory body should not render.",
          diagnostics: [],
          snapshot: {
            worldId: "eldyrwild",
            campaignId: "longmont-c2",
            revisionId: "rev-wrong",
            headRevisionId: "rev-wrong",
            isHead: true,
            focus: { kind: "session", sessionId: "session-21" },
            admissibility: "gm",
          },
        }),
      } as Response);

    renderPlanSurface();
    await waitForPlanSurfaceReady();

    await user.click(screen.getByRole("button", { name: "Open drawer" }));
    await user.type(screen.getByLabelText("Question"), "Where is Tripod?");
    await user.click(screen.getByRole("button", { name: "Ask DungeonBuddy" }));
    await user.click(await screen.findByRole("button", { name: "Open evidence" }));

    const reader = await screen.findByRole("region", { name: "Graph evidence preview" });
    expect(reader).toHaveTextContent(/does not match the pinned citation|did not match the pinned citation contract/i);
    expect(reader).not.toHaveTextContent("Contradictory body should not render.");
  });

  it("reloads saved Hermes graph grounding, citations, and trace without a new query", async () => {
    const user = userEvent.setup();
    const savedThread = {
      ...createAgentInteractionThread("longmont-c2", 22, "plan", "hermes", "Saved graph thread", FIXTURE_DOC_ID),
      turns: [{
        turnId: "turn-saved-graph",
        askedAt: "2026-07-14T18:00:00Z",
        completedAt: "2026-07-14T18:00:01Z",
        question: "Saved graph question?",
        answer: "Saved graph answer.",
        backend: "hermes" as const,
        status: "ok",
        citations: [buildGraphAnchorCitation("rev-saved-original")],
        trace: buildHermesGraphQueryResponse().agent_trace,
        grounding: buildHermesGraphGrounding("grounded", { revision_id: "rev-saved-original" }),
        warnings: [],
      }],
      uiState: { traceVisible: true, scrollAnchorTurnId: "turn-saved-graph" },
    };
    localStorage.setItem(activeThreadStorageKey("longmont-c2", "plan", FIXTURE_DOC_ID), savedThread.threadId);
    localStorage.setItem(threadStorageKey("longmont-c2", savedThread.threadId), JSON.stringify(savedThread));

    const fetchSpy = vi.spyOn(globalThis, "fetch").mockResolvedValue({
      ok: true,
      text: async () => JSON.stringify(mockSourceBundle),
    } as Response);

    renderPlanSurface();
    await waitForPlanSurfaceReady();
    await user.click(screen.getByRole("button", { name: "Open drawer" }));

    expect(await screen.findByText("Saved graph answer.")).toBeInTheDocument();
    expect(screen.getByRole("region", { name: "Graph evidence" })).toBeInTheDocument();
    expect(screen.getByLabelText("Agent interaction trace")).toBeInTheDocument();
    expect(screen.getByText("Graph tool activity (1)")).toBeInTheDocument();
    expect(fetchSpy.mock.calls.filter(([url]) => String(url).includes("/api/live/query"))).toHaveLength(0);
  });

  it("serializes bounded prior-turn history on the second Hermes submit in the same thread", async () => {
    const user = userEvent.setup();
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockImplementation(async (input, init) => {
      const url = String(input);
      if (url.includes("/api/live/source-bundle")) {
        return { ok: true, text: async () => JSON.stringify(mockSourceBundle) } as Response;
      }
      if (url.includes("/api/live/query")) {
        return {
          ok: true,
          text: async () => JSON.stringify(buildHermesGraphQueryResponse()),
        } as Response;
      }
      return { ok: true, text: async () => "{}" } as Response;
    });

    renderPlanSurface();
    await waitForPlanSurfaceReady();

    await user.click(screen.getByRole("button", { name: "Open drawer" }));
    await user.type(
      screen.getByLabelText("Question"),
      "What do we know about Tripod Null-Calf at the North Gate?",
    );
    await user.click(screen.getByRole("button", { name: "Ask DungeonBuddy" }));
    await screen.findByText("Tripod stands at the North Gate.");

    await user.clear(screen.getByLabelText("Question"));
    await user.type(
      screen.getByLabelText("Question"),
      "What is it connected to that should affect my prep?",
    );
    await user.click(screen.getByRole("button", { name: "Ask DungeonBuddy" }));
    await waitFor(() => {
      expect(screen.getAllByText("Tripod stands at the North Gate.")).toHaveLength(2);
    });

    const queryCalls = fetchSpy.mock.calls.filter(([url]) => String(url).includes("/api/live/query"));
    expect(queryCalls).toHaveLength(2);
    const firstBody = JSON.parse(String(queryCalls[0][1]?.body)) as Record<string, unknown>;
    const secondBody = JSON.parse(String(queryCalls[1][1]?.body)) as Record<string, unknown>;
    expect(firstBody).not.toHaveProperty("conversation_history");
    expect(secondBody.text).toBe("What is it connected to that should affect my prep?");
    expect(secondBody.conversation_history).toEqual([
      {
        role: "user",
        content: "What do we know about Tripod Null-Calf at the North Gate?",
      },
      { role: "assistant", content: "Tripod stands at the North Gate." },
    ]);
    expect(secondBody.world_graph_context).toEqual(expectedWorldGraphContextRequest);
    expect(JSON.stringify(secondBody)).not.toContain("hermes_session_id");
    expect(JSON.stringify(secondBody.conversation_history)).not.toContain("source-anchor");
  });

  it("after persist and reload, follow-up history ignores hostile stored children and session ids", async () => {
    const user = userEvent.setup();
    const firstResponse = buildHermesGraphQueryResponse({
      answer: "Tripod stands at the North Gate.",
      agent_trace: {
        ...buildHermesGraphQueryResponse().agent_trace,
        hermes_session_id: "hermes-session-must-not-persist",
      },
    });

    const fetchSpy = vi.spyOn(globalThis, "fetch").mockImplementation(async (input) => {
      const url = String(input);
      if (url.includes("/api/live/source-bundle")) {
        return { ok: true, text: async () => JSON.stringify(mockSourceBundle) } as Response;
      }
      if (url.includes("/api/live/query")) {
        return {
          ok: true,
          text: async () => JSON.stringify(firstResponse),
        } as Response;
      }
      return { ok: true, text: async () => "{}" } as Response;
    });

    const { unmount } = renderPlanSurface();
    await waitForPlanSurfaceReady();
    await user.click(screen.getByRole("button", { name: "Open drawer" }));
    await user.type(
      screen.getByLabelText("Question"),
      "What do we know about Tripod Null-Calf at the North Gate?",
    );
    await user.click(screen.getByRole("button", { name: "Ask DungeonBuddy" }));
    await screen.findByText("Tripod stands at the North Gate.");

    const activeThreadId = localStorage.getItem(activeThreadStorageKey("longmont-c2", "plan", FIXTURE_DOC_ID));
    expect(activeThreadId).toBeTruthy();
    const storedKey = threadStorageKey("longmont-c2", String(activeThreadId));
    const storedBefore = localStorage.getItem(storedKey) ?? "";
    expect(storedBefore).not.toContain("hermes_session_id");
    expect(storedBefore).not.toContain("hermes-session-must-not-persist");

    const parsed = JSON.parse(storedBefore) as {
      turns: Array<Record<string, unknown>>;
    };
    // Newest-first: inject a malformed sibling ahead of the valid persisted turn.
    parsed.turns.unshift({
      turnId: "hostile-malformed",
      askedAt: "2026-07-14T17:00:00Z",
      completedAt: "2026-07-14T17:00:01Z",
      question: "",
      answer: "Malformed stored child",
      backend: "hermes",
      status: "ok",
      citations: [],
      warnings: [],
      grounding: null,
      trace: {
        trace_id: "RAW_TRACE_SECRET",
        hermes_session_id: "RAW_HERMES_TRANSCRIPT_SECRET",
        mode: "hermes_graph_agent",
        runtime: "process_isolated",
        backend: "hermes",
        started_at: "2026-07-14T17:00:00Z",
        completed_at: "2026-07-14T17:00:01Z",
        elapsed_ms: 1,
        status: "ok",
        usage: { available: false, input_tokens: null, output_tokens: null, total_tokens: null },
        steps: [],
        context_summary: {},
        artifact_refs: [],
        tool_events: [],
        warnings: [],
      },
    });
    localStorage.setItem(storedKey, JSON.stringify(parsed));

    unmount();
    fetchSpy.mockClear();
    fetchSpy.mockImplementation(async (input) => {
      const url = String(input);
      if (url.includes("/api/live/source-bundle")) {
        return { ok: true, text: async () => JSON.stringify(mockSourceBundle) } as Response;
      }
      if (url.includes("/api/live/query")) {
        return {
          ok: true,
          text: async () => JSON.stringify(buildHermesGraphQueryResponse({
            answer: "Follow-up after reload.",
          })),
        } as Response;
      }
      return { ok: true, text: async () => "{}" } as Response;
    });

    renderPlanSurface();
    await waitForPlanSurfaceReady();
    await user.click(screen.getByRole("button", { name: "Open drawer" }));
    expect(await screen.findByText("Tripod stands at the North Gate.")).toBeInTheDocument();

    await user.type(
      screen.getByLabelText("Question"),
      "What is it connected to that should affect my prep?",
    );
    await user.click(screen.getByRole("button", { name: "Ask DungeonBuddy" }));
    await screen.findByText("Follow-up after reload.");

    const queryCalls = fetchSpy.mock.calls.filter(([url]) => String(url).includes("/api/live/query"));
    expect(queryCalls).toHaveLength(1);
    const followUpBody = JSON.parse(String(queryCalls[0][1]?.body)) as Record<string, unknown>;
    expect(followUpBody.conversation_history).toEqual([
      {
        role: "user",
        content: "What do we know about Tripod Null-Calf at the North Gate?",
      },
      { role: "assistant", content: "Tripod stands at the North Gate." },
    ]);
    expect(JSON.stringify(followUpBody)).not.toContain("hermes_session_id");
    expect(JSON.stringify(followUpBody)).not.toContain("RAW_HERMES_TRANSCRIPT_SECRET");

    const storedAfter = localStorage.getItem(storedKey) ?? "";
    expect(storedAfter).not.toContain("hermes_session_id");
    expect(storedAfter).not.toContain("hermes-session-must-not-persist");
    expect(storedAfter).not.toContain("RAW_HERMES_TRANSCRIPT_SECRET");
  });

  it("does not leak Thread A history into Thread B follow-up requests", async () => {
    const user = userEvent.setup();
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockImplementation(async (input) => {
      const url = String(input);
      if (url.includes("/api/live/source-bundle")) {
        return { ok: true, text: async () => JSON.stringify(mockSourceBundle) } as Response;
      }
      if (url.includes("/api/live/query")) {
        return {
          ok: true,
          text: async () => JSON.stringify(buildHermesGraphQueryResponse()),
        } as Response;
      }
      return { ok: true, text: async () => "{}" } as Response;
    });

    renderPlanSurface();
    await waitForPlanSurfaceReady();

    await user.click(screen.getByRole("button", { name: "Open drawer" }));
    await user.type(screen.getByLabelText("Question"), "Thread A turn 1?");
    await user.click(screen.getByRole("button", { name: "Ask DungeonBuddy" }));
    await screen.findByText("Tripod stands at the North Gate.");

    await user.click(screen.getByRole("button", { name: "New prep thread" }));
    await user.type(
      screen.getByLabelText("Question"),
      "What is it connected to that should affect my prep?",
    );
    await user.click(screen.getByRole("button", { name: "Ask DungeonBuddy" }));

    const queryCalls = fetchSpy.mock.calls.filter(([url]) => String(url).includes("/api/live/query"));
    const threadBBody = JSON.parse(String(queryCalls.at(-1)?.[1]?.body)) as Record<string, unknown>;
    expect(threadBBody).not.toHaveProperty("conversation_history");
    expect(JSON.stringify(threadBBody)).not.toContain("Thread A turn 1?");
  });

  it("uses the saved citation revision when opening graph evidence after reload", async () => {
    const user = userEvent.setup();
    const savedThread = {
      ...createAgentInteractionThread("longmont-c2", 22, "plan", "hermes", "Saved graph thread", FIXTURE_DOC_ID),
      turns: [{
        turnId: "turn-saved-graph",
        askedAt: "2026-07-14T18:00:00Z",
        completedAt: "2026-07-14T18:00:01Z",
        question: "Saved graph question?",
        answer: "Saved graph answer.",
        backend: "hermes" as const,
        status: "ok",
        citations: [buildGraphAnchorCitation("rev-saved-original")],
        trace: null,
        grounding: buildHermesGraphGrounding("grounded", { revision_id: "rev-saved-original" }),
        warnings: [],
      }],
      uiState: { traceVisible: false, scrollAnchorTurnId: "turn-saved-graph" },
    };
    localStorage.setItem(activeThreadStorageKey("longmont-c2", "plan", FIXTURE_DOC_ID), savedThread.threadId);
    localStorage.setItem(threadStorageKey("longmont-c2", savedThread.threadId), JSON.stringify(savedThread));

    vi.spyOn(globalThis, "fetch")
      .mockResolvedValueOnce({ ok: true, text: async () => JSON.stringify(mockSourceBundle) } as Response)
      .mockResolvedValueOnce({
        ok: true,
        text: async () => JSON.stringify({
          schema: "dmb_world_graph_source_anchor_read_v1",
          outcome: "enough",
          anchorId: "source-anchor:v1:fixture-anchor",
          truncated: false,
          content: "Saved revision body.",
          diagnostics: [],
          snapshot: {
            worldId: "eldyrwild",
            campaignId: "longmont-c2",
            revisionId: "rev-saved-original",
            headRevisionId: "rev-head-newer",
            isHead: false,
            focus: { kind: "session", sessionId: "session-21" },
            admissibility: "gm",
          },
        }),
      } as Response);

    renderPlanSurface();
    await waitForPlanSurfaceReady();
    await user.click(screen.getByRole("button", { name: "Open drawer" }));
    await user.click(await screen.findByRole("button", { name: "Open evidence" }));

    expect(await screen.findByRole("region", { name: "Graph evidence preview" })).toHaveTextContent("Saved revision body.");
    const readCall = vi.mocked(globalThis.fetch).mock.calls.find(([url]) =>
      String(url).includes("/api/live/world-graph/retrieval/source-anchor/read"),
    );
    expect(JSON.parse(String(readCall?.[1]?.body)).revisionPin).toBe("rev-saved-original");
  });

  it("shows graph tool activity when Trace On is enabled for Hermes graph answers", async () => {
    const user = userEvent.setup();
    vi.spyOn(globalThis, "fetch")
      .mockResolvedValueOnce({ ok: true, text: async () => JSON.stringify(mockSourceBundle) } as Response)
      .mockResolvedValueOnce({
        ok: true,
        text: async () => JSON.stringify(buildHermesGraphQueryResponse()),
      } as Response);

    renderPlanSurface();
    await waitForPlanSurfaceReady();

    await user.click(screen.getByRole("button", { name: "Open drawer" }));
    await user.type(screen.getByLabelText("Question"), "Where is Tripod?");
    await user.click(screen.getByRole("button", { name: "Ask DungeonBuddy" }));

    expect(await screen.findByText("Graph tool activity (1)")).toBeInTheDocument();
    expect(screen.getByText("search_campaign_graph")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Trace On/i })).toBeInTheDocument();
  });

  it("renders a contract-error card for malformed Hermes grounding or null citations without crashing", async () => {
    const user = userEvent.setup();
    vi.spyOn(globalThis, "fetch")
      .mockResolvedValueOnce({ ok: true, text: async () => JSON.stringify(mockSourceBundle) } as Response)
      .mockResolvedValueOnce({
        ok: true,
        text: async () => JSON.stringify(buildHermesGraphQueryResponse({
          grounding: {
            schema: "dmb_hermes_graph_grounding_v1",
            state: "grounded",
          },
          citations: [null],
        })),
      } as Response);

    renderPlanSurface();
    await waitForPlanSurfaceReady();

    await user.click(screen.getByRole("button", { name: "Open drawer" }));
    await user.type(screen.getByLabelText("Question"), "Where is Tripod?");
    await user.click(screen.getByRole("button", { name: "Ask DungeonBuddy" }));
    await user.click(await screen.findByRole("button", { name: /Trace On/i }));

    expect(await screen.findByText("Hermes grounding contract error")).toBeInTheDocument();
    expect(screen.queryByRole("region", { name: "Graph evidence" })).not.toBeInTheDocument();
  });

  it("treats grounded Hermes answers with null revision as a contract error", async () => {
    const user = userEvent.setup();
    vi.spyOn(globalThis, "fetch")
      .mockResolvedValueOnce({ ok: true, text: async () => JSON.stringify(mockSourceBundle) } as Response)
      .mockResolvedValueOnce({
        ok: true,
        text: async () => JSON.stringify(buildHermesGraphQueryResponse({
          grounding: buildHermesGraphGrounding("grounded", { revision_id: null }),
        })),
      } as Response);

    renderPlanSurface();
    await waitForPlanSurfaceReady();

    await user.click(screen.getByRole("button", { name: "Open drawer" }));
    await user.type(screen.getByLabelText("Question"), "Where is Tripod?");
    await user.click(screen.getByRole("button", { name: "Ask DungeonBuddy" }));
    await user.click(await screen.findByRole("button", { name: /Trace On/i }));

    expect(await screen.findByText("Hermes grounding contract error")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Open evidence" })).not.toBeInTheDocument();
  });

  it("renders through Plan submit when Hermes agent_trace shell fields are objects", async () => {
    const user = userEvent.setup();
    vi.spyOn(globalThis, "fetch")
      .mockResolvedValueOnce({ ok: true, text: async () => JSON.stringify(mockSourceBundle) } as Response)
      .mockResolvedValueOnce({
        ok: true,
        text: async () => JSON.stringify(buildHermesGraphQueryResponse({
          warnings: { secret: "unexpected object" },
          agent_trace: {
            ...buildHermesGraphQueryResponse().agent_trace,
            backend: { unexpected: true },
            runtime: "process_isolated",
            status: "ok",
            provider: { nested: true },
            model: ["not", "a", "string"],
            toolset: { name: "nope" },
            warnings: [{ secret: "unexpected object" }, "bounded string warning"],
          },
        })),
      } as Response);

    renderPlanSurface();
    await waitForPlanSurfaceReady();

    await user.click(screen.getByRole("button", { name: "Open drawer" }));
    await user.type(screen.getByLabelText("Question"), "Where is Tripod?");
    await user.click(screen.getByRole("button", { name: "Ask DungeonBuddy" }));

    expect(await screen.findByLabelText("Agent interaction trace")).toBeInTheDocument();
    expect(screen.getByText("Tripod stands at the North Gate.")).toBeInTheDocument();
    expect(screen.getByText(/hermes · process_isolated · ok · 88ms/)).toBeInTheDocument();
    expect(screen.getByText("bounded string warning")).toBeInTheDocument();
    expect(screen.queryByText(/unexpected object/)).not.toBeInTheDocument();
    await user.click(await screen.findByRole("button", { name: /Trace On/i }));
    expect(await screen.findByRole("region", { name: "Hermes reply" })).toBeInTheDocument();
  });
  it("keeps Plan usable when top-level warnings are non-array and grounding is malformed", async () => {
    const user = userEvent.setup();
    vi.spyOn(globalThis, "fetch")
      .mockResolvedValueOnce({ ok: true, text: async () => JSON.stringify(mockSourceBundle) } as Response)
      .mockResolvedValueOnce({
        ok: true,
        text: async () => JSON.stringify(buildHermesGraphQueryResponse({
          grounding: {
            schema: "dmb_hermes_graph_grounding_v1",
            state: "grounded",
          },
          citations: [null],
          warnings: { not: "an array" },
          agent_trace: {
            ...buildHermesGraphQueryResponse().agent_trace,
            warnings: { also: "not an array" },
          },
        })),
      } as Response);

    renderPlanSurface();
    await waitForPlanSurfaceReady();

    await user.click(screen.getByRole("button", { name: "Open drawer" }));
    await user.type(screen.getByLabelText("Question"), "Where is Tripod?");
    await user.click(screen.getByRole("button", { name: "Ask DungeonBuddy" }));

    expect(await screen.findByLabelText("Agent interaction trace")).toBeInTheDocument();
    await user.click(await screen.findByRole("button", { name: /Trace On/i }));
    expect(await screen.findByText("Hermes grounding contract error")).toBeInTheDocument();
    expect(screen.queryByRole("region", { name: "Graph evidence" })).not.toBeInTheDocument();
  });

  it("accepts the Kernel unavailable source-anchor envelope with snapshot=null", async () => {
    const user = userEvent.setup();
    vi.spyOn(globalThis, "fetch")
      .mockResolvedValueOnce({ ok: true, text: async () => JSON.stringify(mockSourceBundle) } as Response)
      .mockResolvedValueOnce({
        ok: true,
        text: async () => JSON.stringify(buildHermesGraphQueryResponse()),
      } as Response)
      .mockResolvedValueOnce({
        ok: true,
        text: async () => JSON.stringify({
          schema: "dmb_world_graph_source_anchor_read_v1",
          outcome: "unavailable",
          snapshot: null,
          anchorId: "source-anchor:v1:fixture-anchor",
          evidenceRefId: null,
          sourceArtifactId: null,
          sourceDomain: null,
          locatorKind: null,
          mediaType: null,
          content: null,
          contentSha256: null,
          lineStart: null,
          lineEnd: null,
          truncated: false,
          diagnostics: [{ code: "graph_unavailable", message: "Revision cannot be opened.", severity: "error" }],
        }),
      } as Response);

    renderPlanSurface();
    await waitForPlanSurfaceReady();

    await user.click(screen.getByRole("button", { name: "Open drawer" }));
    await user.type(screen.getByLabelText("Question"), "Where is Tripod?");
    await user.click(screen.getByRole("button", { name: "Ask DungeonBuddy" }));
    await user.click(await screen.findByRole("button", { name: "Open evidence" }));

    expect(await screen.findByRole("region", { name: "Graph evidence preview" })).toHaveTextContent(
      "Source anchor content is unavailable.",
    );
    expect(screen.getByText("Revision cannot be opened.")).toBeInTheDocument();
    expect(screen.queryByText("Source-anchor read response did not match the pinned citation contract.")).not.toBeInTheDocument();
  });

  it("accepts unavailable with a matching authoritative snapshot and rejects a contradictory one", async () => {
    const user = userEvent.setup();
    const matchingUnavailable = {
      schema: "dmb_world_graph_source_anchor_read_v1",
      outcome: "unavailable",
      snapshot: {
        worldId: "eldyrwild",
        campaignId: "longmont-c2",
        revisionId: "rev-pinned-1",
        headRevisionId: "rev-pinned-1",
        isHead: true,
        focus: { kind: "session", sessionId: "session-21" },
        admissibility: "gm",
      },
      anchorId: "source-anchor:v1:fixture-anchor",
      evidenceRefId: null,
      sourceArtifactId: null,
      sourceDomain: null,
      locatorKind: null,
      mediaType: null,
      content: null,
      contentSha256: null,
      lineStart: null,
      lineEnd: null,
      truncated: false,
      diagnostics: [{ code: "source_unreadable", message: "Source artifact is unreadable.", severity: "error" }],
    };
    vi.spyOn(globalThis, "fetch")
      .mockResolvedValueOnce({ ok: true, text: async () => JSON.stringify(mockSourceBundle) } as Response)
      .mockResolvedValueOnce({
        ok: true,
        text: async () => JSON.stringify(buildHermesGraphQueryResponse()),
      } as Response)
      .mockResolvedValueOnce({
        ok: true,
        text: async () => JSON.stringify(matchingUnavailable),
      } as Response);

    renderPlanSurface();
    await waitForPlanSurfaceReady();

    await user.click(screen.getByRole("button", { name: "Open drawer" }));
    await user.type(screen.getByLabelText("Question"), "Where is Tripod?");
    await user.click(screen.getByRole("button", { name: "Ask DungeonBuddy" }));
    await user.click(await screen.findByRole("button", { name: "Open evidence" }));

    expect(await screen.findByRole("region", { name: "Graph evidence preview" })).toHaveTextContent(
      "Source anchor content is unavailable.",
    );
    expect(screen.getByText("Source artifact is unreadable.")).toBeInTheDocument();

    vi.mocked(globalThis.fetch).mockResolvedValueOnce({
      ok: true,
      text: async () => JSON.stringify({
        ...matchingUnavailable,
        snapshot: {
          ...matchingUnavailable.snapshot,
          campaignId: "FOREIGN_CAMPAIGN_ID",
        },
      }),
    } as Response);
    await user.click(screen.getByRole("button", { name: "Open evidence" }));
    expect(await screen.findByRole("region", { name: "Graph evidence preview" })).toHaveTextContent(
      /does not match the pinned citation/i,
    );
    expect(screen.queryByText("Source artifact is unreadable.")).not.toBeInTheDocument();
  });

  it("accepts Kernel partial with null content and shows diagnostics", async () => {
    const user = userEvent.setup();
    vi.spyOn(globalThis, "fetch")
      .mockResolvedValueOnce({ ok: true, text: async () => JSON.stringify(mockSourceBundle) } as Response)
      .mockResolvedValueOnce({
        ok: true,
        text: async () => JSON.stringify(buildHermesGraphQueryResponse()),
      } as Response)
      .mockResolvedValueOnce({
        ok: true,
        text: async () => JSON.stringify({
          schema: "dmb_world_graph_source_anchor_read_v1",
          outcome: "partial",
          snapshot: {
            worldId: "eldyrwild",
            campaignId: "longmont-c2",
            revisionId: "rev-pinned-1",
            headRevisionId: "rev-pinned-1",
            isHead: true,
            focus: { kind: "session", sessionId: "session-21" },
            admissibility: "gm",
          },
          anchorId: "source-anchor:v1:fixture-anchor",
          evidenceRefId: null,
          sourceArtifactId: null,
          sourceDomain: null,
          locatorKind: "unsupported",
          mediaType: null,
          content: null,
          contentSha256: null,
          lineStart: null,
          lineEnd: null,
          truncated: false,
          diagnostics: [{
            code: "unsupported_locator",
            message: "Locator kind is unsupported for content extraction.",
            severity: "warning",
          }],
        }),
      } as Response);

    renderPlanSurface();
    await waitForPlanSurfaceReady();

    await user.click(screen.getByRole("button", { name: "Open drawer" }));
    await user.type(screen.getByLabelText("Question"), "Where is Tripod?");
    await user.click(screen.getByRole("button", { name: "Ask DungeonBuddy" }));
    await user.click(await screen.findByRole("button", { name: "Open evidence" }));

    const reader = await screen.findByRole("region", { name: "Graph evidence preview" });
    expect(reader).toHaveTextContent("Qualified source-anchor read returned no readable content.");
    expect(reader).toHaveTextContent("Locator kind is unsupported for content extraction.");
    expect(reader).not.toHaveTextContent("contract");
  });

  it("hides the corpus change signal panel for graph-only Hermes turns", async () => {
    const user = userEvent.setup();
    vi.spyOn(globalThis, "fetch")
      .mockResolvedValueOnce({ ok: true, text: async () => JSON.stringify(mockSourceBundle) } as Response)
      .mockResolvedValueOnce({
        ok: true,
        text: async () => JSON.stringify(buildHermesGraphQueryResponse()),
      } as Response);

    renderPlanSurface();
    await waitForPlanSurfaceReady();

    await user.click(screen.getByRole("button", { name: "Open drawer" }));
    await user.type(screen.getByLabelText("Question"), "Where is Tripod?");
    await user.click(screen.getByRole("button", { name: "Ask DungeonBuddy" }));
    await user.click(await screen.findByRole("button", { name: /Trace On/i }));

    expect(await screen.findByRole("region", { name: "Hermes reply" })).toBeInTheDocument();
    expect(screen.queryByRole("region", { name: "Corpus change signal" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Check current source state" })).not.toBeInTheDocument();
  });
});
