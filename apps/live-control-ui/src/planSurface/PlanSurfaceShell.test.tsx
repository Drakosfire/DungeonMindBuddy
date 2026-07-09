import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { mockHermesCliTrace, mockPlanView, mockSourceBundle } from "../test/fixtures";
import {
  activeThreadStorageKey,
  createAgentInteractionThread,
  threadIndexStorageKey,
  threadStorageKey,
  AGENT_THREAD_SUGGEST_NEW_AFTER_TURNS,
} from "./components/agentInteractionHistory";
import { AgentInteractionProvider } from "../agentInteraction/AgentInteractionProvider";
import { PlanSurfaceShell } from "./PlanSurfaceShell";

function renderPlanSurface() {
  return render(
    <AgentInteractionProvider>
      <PlanSurfaceShell planView={mockPlanView} />
    </AgentInteractionProvider>,
  );
}

describe("PlanSurfaceShell", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    localStorage.clear();
    window.history.pushState({}, "", "/plan");
  });

  it("renders nav, toolbar, edit bar, and canvas regions", () => {
    renderPlanSurface();

    expect(screen.getByRole("navigation", { name: "Plan surface navigation" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Tools" })).toBeInTheDocument();
    expect(screen.getByRole("navigation", { name: "Toolbox tools" })).toBeInTheDocument();
    expect(screen.getByRole("complementary", { name: "Edit bar" })).toBeInTheDocument();
    expect(screen.getByLabelText("Plan canvas")).toBeInTheDocument();
    expect(screen.getByText(/preparing Session 23/i)).toBeInTheDocument();
    expect(screen.getByTestId("plan-memory-source")).toHaveTextContent(/Session 21/i);
    expect(screen.getByTestId("plan-document-context")).toHaveTextContent(/C2 Session 23 Prep · local draft/i);
    expect(screen.getByTestId("plan-document-target")).toHaveTextContent(
      /Session Prep\/Session 23 Prep\.md/i,
    );
    expect(screen.getByRole("link", { name: "Review memory" })).toHaveAttribute(
      "href",
      "/ingest?campaign=longmont-c2&session=session-21",
    );
    expect(screen.getByRole("complementary", { name: "Plan toolbox" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Open drawer" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Live Play" })).toHaveAttribute(
      "href",
      "/evals/c2_live_prep/mireward-prep/live-play.html",
    );
    expect(screen.getByText(/Document controls for the selected planning canvas/i)).toBeInTheDocument();
  });

  it("opens Recap from the tool query parameter", async () => {
    window.history.pushState({}, "", "/plan?tool=recap");
    renderPlanSurface();

    await waitFor(() =>
      expect(screen.getByRole("button", { name: "Recap" })).toHaveAttribute("aria-pressed", "true"),
    );
  });

  it("opens the local Agent Interaction placeholder proof pane", async () => {
    const user = userEvent.setup();
    vi.spyOn(globalThis, "fetch").mockResolvedValue({
      ok: true,
      text: async () => JSON.stringify(mockSourceBundle),
    } as Response);

    renderPlanSurface();

    await user.click(screen.getByRole("button", { name: "Open drawer" }));

    expect(
      await screen.findByRole("complementary", { name: "Agent Interaction drawer" }),
    ).toBeInTheDocument();
    expect(screen.getByText("Ingested corpus interaction proof")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Ask ingested corpus" })).toBeInTheDocument();
    expect(screen.getByRole("radio", { name: "Live loop" })).toBeChecked();
    expect(screen.getByRole("radio", { name: "Hermes tools" })).toBeInTheDocument();
    expect(screen.getByRole("region", { name: "Ingestion proof" })).toBeInTheDocument();
    expect(screen.getByText("Advanced source metadata")).toBeInTheDocument();
    expect(screen.getByText("longmont-c2 Session 22: normalized")).toBeInTheDocument();
    expect(screen.getByText("corpus_bodies_not_embedded")).toBeInTheDocument();
  });

  it("asks through the Agent Interaction placeholder using live query", async () => {
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

    await user.click(screen.getByRole("button", { name: "Open drawer" }));
    await screen.findByText("Ingested corpus interaction proof");
    expect(screen.getByRole("heading", { name: "Ask ingested corpus" })).toBeInTheDocument();
    await user.type(
      screen.getByLabelText("Question"),
      "What changed after Session 22?",
    );
    await user.click(screen.getByRole("button", { name: "Ask" }));

    expect(await screen.findByText("Preliminary verdict · Enough context")).toBeInTheDocument();
    expect(screen.getAllByText("Fresh retrieval").length).toBeGreaterThan(0);
    expect(screen.getByRole("region", { name: "Agent answer" })).toHaveTextContent("Raw synthesized answer should not be the primary result.");
    expect(screen.getByRole("region", { name: "Context packet review" })).toBeInTheDocument();
    expect(screen.getByRole("region", { name: "Citation cards" })).toHaveTextContent("play_recap · canon_play");
    expect(screen.queryByRole("region", { name: "Current source reader" })).not.toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Open source" }));

    const sourceReader = await screen.findByRole("region", { name: "Current source reader" });
    expect(sourceReader).toHaveTextContent("Current source content has the Lysandro gate reveal.");
    expect(sourceReader).not.toHaveTextContent("Stale packet excerpt should not be the reader body.");
    const storedThreadId = localStorage.getItem(activeThreadStorageKey(mockPlanView.campaign_id, "plan"));
    expect(storedThreadId).toBeTruthy();
    expect(localStorage.getItem(threadStorageKey(mockPlanView.campaign_id, storedThreadId ?? "")) ?? "").not.toContain("Current source content has the Lysandro gate reveal.");
    expect(screen.getByRole("region", { name: "Retrieval freshness" })).toBeInTheDocument();
    expect(screen.getAllByText("Fresh retrieval").length).toBeGreaterThan(0);
    expect(screen.getByText("Fresh corpus evidence was admitted for this turn.")).toBeInTheDocument();
    expect(screen.getByText("authority_mismatch: 1")).toBeInTheDocument();
    const queryCall = vi.mocked(globalThis.fetch).mock.calls[1];
    expect(JSON.parse(String(queryCall[1]?.body))).toMatchObject({ query_backend: "live" });
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

    await user.click(screen.getByRole("button", { name: "Open drawer" }));
    await user.type(screen.getByLabelText("Question"), "Is this still current?");
    await user.click(screen.getByRole("button", { name: "Ask" }));

    expect(await screen.findByRole("region", { name: "Corpus change signal" })).toHaveTextContent("Corpus signal: Unknown");
    await user.click(screen.getByRole("button", { name: "Check current source state" }));

    expect(await screen.findByText("Corpus signal: Current")).toBeInTheDocument();
    const freshnessCall = vi.mocked(globalThis.fetch).mock.calls[2];
    expect(String(freshnessCall[0])).toContain("/api/live/citation-freshness");
    expect(JSON.parse(String(freshnessCall[1]?.body))).toMatchObject({
      path: "corpus/test/session.md",
      expected_fingerprint: "expected-source-lines-hash",
      fingerprint_algorithm: "sha256:source-lines-v1",
    });
    const storedThreadId = localStorage.getItem(activeThreadStorageKey(mockPlanView.campaign_id, "plan"));
    const storedThread = localStorage.getItem(threadStorageKey(mockPlanView.campaign_id, storedThreadId ?? "")) ?? "";
    expect(storedThread).toContain("expected-source-lines-hash");
    expect(storedThread).not.toContain("Current source content has the Lysandro gate reveal.");
    const indexJson = localStorage.getItem(threadIndexStorageKey(mockPlanView.campaign_id, "plan")) ?? "";
    expect(indexJson).not.toContain("expected-source-lines-hash");
    expect(indexJson).not.toContain("corpus/test/session.md");
  });

  it("can route the Agent Interaction drawer through Hermes tools", async () => {
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

    await user.click(screen.getByRole("button", { name: "Open drawer" }));
    await screen.findByText("Ingested corpus interaction proof");
    await user.click(screen.getByRole("radio", { name: "Hermes tools" }));
    await user.type(screen.getByLabelText("Question"), "What happened at the end of session 22?");
    await user.click(screen.getByRole("button", { name: "Ask" }));

    expect(await screen.findByText("Preliminary verdict · Enough context")).toBeInTheDocument();
    expect(screen.getAllByText("Blended").length).toBeGreaterThan(0);
    const queryCall = vi.mocked(globalThis.fetch).mock.calls[1];
    expect(JSON.parse(String(queryCall[1]?.body))).toMatchObject({ query_backend: "hermes" });
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

    await user.click(screen.getByRole("button", { name: "Open drawer" }));
    await screen.findByText("Ingested corpus interaction proof");
    await user.click(screen.getByRole("radio", { name: "Hermes tools" }));
    await user.type(screen.getByLabelText("Question"), "What happened at the end of session 22?");
    await user.click(screen.getByRole("button", { name: "Ask" }));

    expect(await screen.findByLabelText("Agent interaction trace")).toBeInTheDocument();
    expect(screen.getByText("CLI synthesized answer for operator.")).toBeInTheDocument();
    expect(screen.getByText(/3100 ms/)).toBeInTheDocument();
    expect(screen.getByText(/Prompt sent to Hermes/)).toBeInTheDocument();
    expect(screen.queryByText("No context packet returned for this query.")).not.toBeInTheDocument();
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

    await user.click(screen.getByRole("button", { name: "Open drawer" }));
    await screen.findByText("Ingested corpus interaction proof");

    await user.type(screen.getByLabelText("Question"), "First question?");
    await user.click(screen.getByRole("button", { name: "Ask" }));
    expect(await screen.findByText("First answer")).toBeInTheDocument();
    expect(screen.getByText("Conversation (1)")).toBeInTheDocument();

    await user.type(screen.getByLabelText("Question"), "Second question?");
    await user.click(screen.getByRole("button", { name: "Ask" }));
    expect(await screen.findByText("Second answer")).toBeInTheDocument();
    expect(screen.getByText("Conversation (2)")).toBeInTheDocument();

    const stored = localStorage.getItem("plan-agent-turns-v1:longmont-c2");
    expect(stored).toBeTruthy();
    const parsed = JSON.parse(String(stored)) as Array<{ question: string; answer: string }>;
    expect(parsed.length).toBe(2);
    expect(parsed[0].question).toBe("Second question?");
    expect(parsed[0].answer).toBe("Second answer");
    expect(JSON.stringify(parsed)).not.toMatch(/context_packet|text_excerpt/);

    const activeThreadId = localStorage.getItem(activeThreadStorageKey("longmont-c2", "plan"));
    expect(activeThreadId).toBeTruthy();
    const storedThread = localStorage.getItem(threadStorageKey("longmont-c2", String(activeThreadId)));
    expect(storedThread).toBeTruthy();
    expect(storedThread).not.toMatch(/context_packet/);
    expect(storedThread).not.toMatch(/text_excerpt/);
    expect(storedThread).not.toMatch(/prompt_preview/);
    expect(storedThread).not.toMatch(/Retrieved evidence excerpts/);
    expect(storedThread).not.toMatch(/\/tmp\/hermes/);

    await user.click(screen.getByRole("button", { name: "Clear history" }));
    expect(screen.queryByText("Conversation (2)")).not.toBeInTheDocument();
    expect(localStorage.getItem("plan-agent-turns-v1:longmont-c2")).toBe("[]");
  });

  it("migrates existing active threads into the switcher and renames the active thread", async () => {
    const user = userEvent.setup();
    const existingThread = {
      ...createAgentInteractionThread("longmont-c2", 23, "plan", "hermes", "Session 24 inn prep"),
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
    localStorage.setItem(activeThreadStorageKey("longmont-c2", "plan"), existingThread.threadId);
    localStorage.setItem(threadStorageKey("longmont-c2", existingThread.threadId), JSON.stringify(existingThread));

    vi.spyOn(globalThis, "fetch").mockResolvedValue({
      ok: true,
      text: async () => JSON.stringify(mockSourceBundle),
    } as Response);

    renderPlanSurface();

    await user.click(screen.getByRole("button", { name: "Open drawer" }));
    await screen.findByText("Session 24 inn prep");
    expect(screen.getByText("The inn has Mireward rumors.")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Threads" }));
    const switcher = screen.getByRole("region", { name: "Agent Interaction threads" });
    expect(switcher).toHaveTextContent("Session 24 inn prep");
    expect(localStorage.getItem(threadIndexStorageKey("longmont-c2", "plan"))).toContain("Session 24 inn prep");

    await user.click(screen.getByRole("button", { name: "Rename" }));
    await user.clear(screen.getByLabelText("Thread title"));
    await user.type(screen.getByLabelText("Thread title"), "Mireward inn prep");
    await user.click(screen.getByRole("button", { name: "Save title" }));

    expect(screen.getAllByText("Mireward inn prep").length).toBeGreaterThan(0);
    expect(screen.getByText("Agent Interaction · Mireward inn prep")).toBeInTheDocument();
    expect(localStorage.getItem(threadIndexStorageKey("longmont-c2", "plan"))).toContain("Mireward inn prep");
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

    await user.click(screen.getByRole("button", { name: "Open drawer" }));
    await screen.findByText("Ingested corpus interaction proof");
    await user.type(screen.getByLabelText("Question"), "Thread A question?");
    await user.click(screen.getByRole("button", { name: "Ask" }));
    expect(await screen.findByText("Answer for thread A")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Open source" }));
    expect(await screen.findByRole("region", { name: "Current source reader" })).toHaveTextContent("Thread A source body");

    await user.click(screen.getByRole("button", { name: "New thread" }));
    expect(screen.queryByText("Answer for thread A")).not.toBeInTheDocument();
    expect(screen.queryByRole("region", { name: "Current source reader" })).not.toBeInTheDocument();
    await user.type(screen.getByLabelText("Question"), "Thread B question?");
    await user.click(screen.getByRole("button", { name: "Ask" }));
    expect(await screen.findByText("Answer for thread B")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Threads" }));
    await user.click(screen.getAllByRole("button", { name: /Thread A question/i })[0]);
    expect(await screen.findByText("Answer for thread A")).toBeInTheDocument();
    expect(screen.queryByText("Answer for thread B")).not.toBeInTheDocument();

    const indexJson = localStorage.getItem(threadIndexStorageKey("longmont-c2", "plan")) ?? "";
    expect(indexJson).toContain("Thread A question?");
    expect(indexJson).toContain("Thread B question?");
    expect(indexJson).not.toContain("Answer for thread A");
    const activeThreadId = localStorage.getItem(activeThreadStorageKey("longmont-c2", "plan"));
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
    await user.click(screen.getByRole("button", { name: "Open drawer" }));
    await screen.findByText("Ingested corpus interaction proof");

    for (let index = 1; index <= AGENT_THREAD_SUGGEST_NEW_AFTER_TURNS; index += 1) {
      await user.type(screen.getByLabelText("Question"), `Question ${index}?`);
      await user.click(screen.getByRole("button", { name: "Ask" }));
      expect(await screen.findByText(`Answer ${index}`)).toBeInTheDocument();
    }

    expect(screen.getByRole("region", { name: "Thread getting long" })).toHaveTextContent(
      `This thread has ${AGENT_THREAD_SUGGEST_NEW_AFTER_TURNS} turns. Start a new prep thread for a fresh topic?`,
    );
    const originalThreadId = localStorage.getItem(activeThreadStorageKey("longmont-c2", "plan"));
    await user.click(screen.getByRole("button", { name: "Keep going" }));
    expect(screen.queryByRole("region", { name: "Thread getting long" })).not.toBeInTheDocument();
    expect(localStorage.getItem(activeThreadStorageKey("longmont-c2", "plan"))).toBe(originalThreadId);
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
    await user.click(screen.getByRole("button", { name: "Open drawer" }));
    await screen.findByText("Ingested corpus interaction proof");

    for (let index = 1; index <= AGENT_THREAD_SUGGEST_NEW_AFTER_TURNS; index += 1) {
      fireEvent.change(screen.getByLabelText("Question"), { target: { value: `Before clear ${index}?` } });
      fireEvent.click(screen.getByRole("button", { name: "Ask" }));
      expect(await screen.findByText(`Clear reset answer ${index}`)).toBeInTheDocument();
    }

    await user.click(screen.getByRole("button", { name: "Keep going" }));
    expect(screen.queryByRole("region", { name: "Thread getting long" })).not.toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Clear history" }));
    expect(screen.queryByText(`Conversation (${AGENT_THREAD_SUGGEST_NEW_AFTER_TURNS})`)).not.toBeInTheDocument();

    for (let index = 1; index <= AGENT_THREAD_SUGGEST_NEW_AFTER_TURNS; index += 1) {
      fireEvent.change(screen.getByLabelText("Question"), { target: { value: `After clear ${index}?` } });
      fireEvent.click(screen.getByRole("button", { name: "Ask" }));
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
    await user.click(screen.getByRole("button", { name: "Open drawer" }));
    await screen.findByText("Ingested corpus interaction proof");
    expect(screen.queryByRole("region", { name: "Thread getting long" })).not.toBeInTheDocument();

    for (let index = 1; index <= AGENT_THREAD_SUGGEST_NEW_AFTER_TURNS; index += 1) {
      await user.type(screen.getByLabelText("Question"), `Long question ${index}?`);
      await user.click(screen.getByRole("button", { name: "Ask" }));
      expect(await screen.findByText(`Long answer ${index}`)).toBeInTheDocument();
    }

    await user.click(screen.getByRole("button", { name: "Start new thread" }));
    expect(screen.getByText("Agent Interaction · New prep thread")).toBeInTheDocument();
    expect(screen.queryByText(`Conversation (${AGENT_THREAD_SUGGEST_NEW_AFTER_TURNS})`)).not.toBeInTheDocument();
    const activeThreadId = localStorage.getItem(activeThreadStorageKey("longmont-c2", "plan"));
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
    await user.click(screen.getByRole("button", { name: "Open drawer" }));
    await screen.findByText("Ingested corpus interaction proof");
    await user.type(screen.getByLabelText("Question"), "Restore thread A?");
    await user.click(screen.getByRole("button", { name: "Ask" }));
    expect(await screen.findByText("Answer for restore A")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "New thread" }));
    await user.type(screen.getByLabelText("Question"), "Restore thread B?");
    await user.click(screen.getByRole("button", { name: "Ask" }));
    expect(await screen.findByText("Answer for restore B")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Threads" }));
    await user.click(screen.getAllByRole("button", { name: /Restore thread A\?/i })[0]);
    expect(await screen.findByText("Answer for restore A")).toBeInTheDocument();

    rendered.unmount();
    renderPlanSurface();
    await user.click(screen.getByRole("button", { name: "Open drawer" }));
    expect(await screen.findByText("Answer for restore A")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Threads" }));
    const switcher = screen.getByRole("region", { name: "Agent Interaction threads" });
    expect(switcher).toHaveTextContent("Restore thread A?");
    expect(switcher).toHaveTextContent("Restore thread B?");
    expect(screen.getByText("Agent Interaction · Restore thread A?")).toBeInTheDocument();
  });

  it("ignores corrupt thread index localStorage", async () => {
    const user = userEvent.setup();
    localStorage.setItem(threadIndexStorageKey("longmont-c2", "plan"), "{not-json");
    vi.spyOn(globalThis, "fetch").mockResolvedValue({
      ok: true,
      text: async () => JSON.stringify(mockSourceBundle),
    } as Response);

    renderPlanSurface();
    await user.click(screen.getByRole("button", { name: "Open drawer" }));
    await screen.findByText("Ingested corpus interaction proof");
    await user.click(screen.getByRole("button", { name: "Threads" }));
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

    await user.click(screen.getByRole("button", { name: "Open drawer" }));
    await screen.findByText("Ingested corpus interaction proof");
    await user.type(screen.getByLabelText("Question"), "What happened at bootstrap?");
    await user.click(screen.getByRole("button", { name: "Ask" }));

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

    await user.click(screen.getByRole("button", { name: "Open drawer" }));
    await screen.findByText("Ingested corpus interaction proof");
    await user.type(screen.getByLabelText("Question"), "What carried over from prior sessions?");
    await user.click(screen.getByRole("button", { name: "Ask" }));

    expect(await screen.findByText("Retrieved text (2)")).toBeInTheDocument();
    expect(screen.getAllByText(/Session 21 - Drake Nest Mirathorn Call.md/).length).toBeGreaterThan(0);
    expect(screen.getByText("Preliminary verdict · Weak context")).toBeInTheDocument();
  });

  it("applies spike theme tokens at the surface root", () => {
    const { container } = renderPlanSurface();
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

    await user.click(screen.getByRole("button", { name: "Tools" }));

    expect(screen.getByRole("complementary", { name: /Recap projection/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Recap" })).toHaveAttribute("aria-pressed", "true");
  });

  it("opens statblock projection from the toolbar registry", async () => {
    const user = userEvent.setup();
    renderPlanSurface();

    await user.click(screen.getByRole("button", { name: "Tools" }));
    await user.click(screen.getByRole("button", { name: "Statblock" }));

    expect(screen.getByRole("complementary", { name: /Statblock projection/i })).toBeInTheDocument();
  });

  it("projects reference chip resolution through the shared container", async () => {
    const user = userEvent.setup();
    vi.spyOn(globalThis, "fetch").mockResolvedValue({
      ok: true,
      json: async () => ({
        locations: [{
          index_id: "north-reach-gate",
          title: "North Reach Gate",
          corpus_display_path: "corpus/locations/north_reach_gate.md",
        }],
      }),
    } as Response);

    renderPlanSurface();

    const canvas = screen.getByTestId("plan-surface-canvas-editor");
    const chip = canvas.querySelector(".md-ref-chip") as HTMLElement;
    fireEvent.click(chip);

    await waitFor(() => {
      expect(screen.getByRole("complementary", { name: /North Reach Gate projection/i })).toBeInTheDocument();
    });
    expect(screen.getByText(/Resolved from live location index/i)).toBeInTheDocument();
  });
});
