import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { mockHermesCliTrace, mockPlanView, mockSourceBundle } from "../test/fixtures";
import { PlanSurfaceShell } from "./PlanSurfaceShell";

describe("PlanSurfaceShell", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    localStorage.clear();
  });

  it("renders nav, toolbar, edit bar, and canvas regions", () => {
    render(<PlanSurfaceShell planView={mockPlanView} />);

    expect(screen.getByRole("navigation", { name: "Plan surface navigation" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Tools" })).toBeInTheDocument();
    expect(screen.getByRole("navigation", { name: "Toolbox tools" })).toBeInTheDocument();
    expect(screen.getByRole("complementary", { name: "Edit bar" })).toBeInTheDocument();
    expect(screen.getByLabelText("Plan canvas")).toBeInTheDocument();
    expect(screen.getByText(/preparing Session 23 · ingesting Session 21/i)).toBeInTheDocument();
    expect(screen.getByRole("complementary", { name: "Plan toolbox" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Open drawer" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Live Play" })).toHaveAttribute(
      "href",
      "/evals/c2_live_prep/mireward-prep/live-play.html",
    );
    expect(screen.getByText(/Document controls for the selected planning canvas/i)).toBeInTheDocument();
  });

  it("opens the local Agent Interaction placeholder proof pane", async () => {
    const user = userEvent.setup();
    vi.spyOn(globalThis, "fetch").mockResolvedValue({
      ok: true,
      text: async () => JSON.stringify(mockSourceBundle),
    } as Response);

    render(<PlanSurfaceShell planView={mockPlanView} />);

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
            citations: [{ evidence_id: "e1", path: "x", line_start: null, line_end: null }],
            context_packet: {
              admitted_evidence: [{
                path: "x",
                source_role: "play_recap",
                authority: "canon_play",
                text_excerpt: "Session 22 added the Lysandro gate reveal.",
              }],
              rejected_evidence: [{ reason_code: "authority_mismatch", evidence: { path: "y" } }],
            },
          }),
      } as Response);

    render(<PlanSurfaceShell planView={mockPlanView} />);

    await user.click(screen.getByRole("button", { name: "Open drawer" }));
    await screen.findByText("Ingested corpus interaction proof");
    expect(screen.getByRole("heading", { name: "Ask ingested corpus" })).toBeInTheDocument();
    await user.type(
      screen.getByLabelText("Question"),
      "What changed after Session 22?",
    );
    await user.click(screen.getByRole("button", { name: "Ask" }));

    expect(await screen.findByText("Preliminary verdict · Enough context")).toBeInTheDocument();
    expect(screen.getAllByText("Session 22 added the Lysandro gate reveal.").length).toBeGreaterThan(0);
    expect(screen.queryByText("Raw synthesized answer should not be the primary result.")).not.toBeInTheDocument();
    expect(screen.getByRole("region", { name: "Context packet review" })).toBeInTheDocument();
    expect(screen.getByText("authority_mismatch: 1")).toBeInTheDocument();
    const queryCall = vi.mocked(globalThis.fetch).mock.calls[1];
    expect(JSON.parse(String(queryCall[1]?.body))).toMatchObject({ query_backend: "live" });
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

    render(<PlanSurfaceShell planView={mockPlanView} />);

    await user.click(screen.getByRole("button", { name: "Open drawer" }));
    await screen.findByText("Ingested corpus interaction proof");
    await user.click(screen.getByRole("radio", { name: "Hermes tools" }));
    await user.type(screen.getByLabelText("Question"), "What happened at the end of session 22?");
    await user.click(screen.getByRole("button", { name: "Ask" }));

    expect(await screen.findByText("Preliminary verdict · Enough context")).toBeInTheDocument();
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

    render(<PlanSurfaceShell planView={mockPlanView} />);

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

    render(<PlanSurfaceShell planView={mockPlanView} />);

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

    await user.click(screen.getByRole("button", { name: "Clear history" }));
    expect(screen.queryByText("Conversation (2)")).not.toBeInTheDocument();
    expect(localStorage.getItem("plan-agent-turns-v1:longmont-c2")).toBe("[]");
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

    render(<PlanSurfaceShell planView={mockPlanView} />);

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

    render(<PlanSurfaceShell planView={mockPlanView} />);

    await user.click(screen.getByRole("button", { name: "Open drawer" }));
    await screen.findByText("Ingested corpus interaction proof");
    await user.type(screen.getByLabelText("Question"), "What carried over from prior sessions?");
    await user.click(screen.getByRole("button", { name: "Ask" }));

    expect(await screen.findByText("Retrieved text (2)")).toBeInTheDocument();
    expect(screen.getAllByText(/Session 21 - Drake Nest Mirathorn Call.md/).length).toBeGreaterThan(0);
    expect(screen.getByText("Preliminary verdict · Weak context")).toBeInTheDocument();
  });

  it("applies spike theme tokens at the surface root", () => {
    const { container } = render(<PlanSurfaceShell planView={mockPlanView} />);
    const root = container.querySelector(".plan-surface-root");
    expect(root).toHaveAttribute("data-md-theme", "mireward-runbook");
    expect(root).toHaveStyle({ "--accent": "#7aa2f7" });
  });

  it("opens ingestion projection from the toolbar registry", async () => {
    const user = userEvent.setup();
    render(<PlanSurfaceShell planView={mockPlanView} />);

    await user.click(screen.getByRole("button", { name: "Tools" }));

    expect(screen.getByRole("complementary", { name: /Ingest Recap projection/i })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: /Raw Recap Ingestion/i })).toBeInTheDocument();
  });

  it("opens statblock projection from the toolbar registry", async () => {
    const user = userEvent.setup();
    render(<PlanSurfaceShell planView={mockPlanView} />);

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

    render(<PlanSurfaceShell planView={mockPlanView} />);

    const canvas = screen.getByTestId("plan-surface-canvas-editor");
    const chip = canvas.querySelector(".md-ref-chip") as HTMLElement;
    fireEvent.click(chip);

    await waitFor(() => {
      expect(screen.getByRole("complementary", { name: /North Reach Gate projection/i })).toBeInTheDocument();
    });
    expect(screen.getByText(/Resolved from live location index/i)).toBeInTheDocument();
  });
});
