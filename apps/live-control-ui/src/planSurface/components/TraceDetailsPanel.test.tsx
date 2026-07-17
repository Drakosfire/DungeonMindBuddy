import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import type { AgentInteractionTrace } from "../../api/types";
import {
  formatTraceConversationContextSummary,
  formatTraceForClipboard,
  formatTraceToolSummary,
  TraceDetailsPanel,
} from "./TraceDetailsPanel";

/** PR354 Hermes product trace shape — shell fields required by this panel. */
const pr354HermesTrace: AgentInteractionTrace = {
  trace_id: "agent-trace-pr354-fixture",
  runtime: "process_isolated",
  backend: "hermes",
  mode: "hermes_graph_agent",
  started_at: "2026-07-14T18:00:00Z",
  completed_at: "2026-07-14T18:00:01Z",
  elapsed_ms: 42,
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
      duration_ms: 18,
      outcome: "enough",
      world_id: "eldyrwild",
      campaign_id: "longmont-c2",
      revision_pin: "rev-1",
      focus: { kind: "session", session_id: "session-21" },
      admissibility: "gm",
      matched_node_ids: ["node-tripod"],
      relationship_ids: ["rel-gate"],
      source_anchor_ids: ["source-anchor:v1:fixture"],
      diagnostic_codes: [],
      bounded_ids: {},
      retrieval_schema: null,
    },
  ],
  hermes_session_id: "hermes-sess-obs-only",
  process_isolation: "process_exclusive",
  warnings: [],
  prompt_preview: "RAW_PROMPT_SECRET should never render for graph agent traces",
};

const populatedConversationContext = {
  history_present: true,
  message_count: 6,
  pair_count: 3,
  payload_shape: "role_content_only",
  graph_metadata_in_history: false,
  hermes_session_pointer_in_request: true,
  hermes_session_pointer_status: "accepted",
  worker_pid_changed: false,
  fresh_graph_revision_used: true,
} as const;

describe("TraceDetailsPanel", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("renders a PR354 Hermes graph agent_trace with Trace shell fields safely", () => {
    render(
      <TraceDetailsPanel
        trace={pr354HermesTrace}
        answer="Tripod stands at the North Gate."
      />,
    );

    expect(screen.getByLabelText("Agent interaction trace")).toBeInTheDocument();
    expect(screen.getByTestId("plan-agent-trace-summary-meta")).toHaveTextContent(
      /hermes · process_isolated · ok · 42ms · tools: search_campaign_graph/,
    );
    expect(screen.getByText("not reported")).toBeInTheDocument();
    expect(screen.getByText("hermes_graph_agent")).toBeInTheDocument();
  });

  it("renders bounded graph tool activity for Hermes graph agent traces", () => {
    render(<TraceDetailsPanel trace={pr354HermesTrace} />);

    expect(screen.getByText("Graph tool activity (1)")).toBeInTheDocument();
    expect(screen.getAllByText("search_campaign_graph").length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText(/completion · 18ms · enough/)).toBeInTheDocument();
    expect(screen.getByText("node-tripod")).toBeInTheDocument();
    expect(screen.getByText("rel-gate")).toBeInTheDocument();
    expect(screen.getByText("source-anchor:v1:fixture")).toBeInTheDocument();
    expect(screen.getByText("Hermes session (observability)")).toBeInTheDocument();
    expect(screen.getByText("hermes-sess-obs-only")).toBeInTheDocument();
  });

  it("shows tools: none in the collapsed summary when Hermes made no tool calls", () => {
    render(
      <TraceDetailsPanel
        trace={{
          ...pr354HermesTrace,
          tool_events: [],
          tool_event_count: 0,
        }}
      />,
    );

    expect(screen.getByTestId("plan-agent-trace-summary-meta")).toHaveTextContent(/tools: none/);
    expect(screen.getByText("Graph tool activity (0)")).toBeInTheDocument();
    expect(screen.getByTestId("plan-agent-trace-tools-none")).toHaveTextContent(
      /No graph tools were called/,
    );
  });

  it("copies a plain-text trace dump to the clipboard", async () => {
    const user = userEvent.setup();
    const writeText = vi.fn().mockResolvedValue(undefined);
    Object.defineProperty(navigator, "clipboard", {
      configurable: true,
      value: { writeText },
    });

    render(
      <TraceDetailsPanel
        trace={pr354HermesTrace}
        answer="Tripod stands at the North Gate."
      />,
    );

    await user.click(screen.getByRole("button", { name: "Copy trace" }));
    expect(writeText).toHaveBeenCalledTimes(1);
    const copied = String(writeText.mock.calls[0]?.[0] ?? "");
    expect(copied).toContain("Agent trace");
    expect(copied).toContain("search_campaign_graph");
    expect(copied).toContain("node-tripod");
    expect(copied).toContain("Tripod stands at the North Gate.");
    expect(screen.getByRole("button", { name: "Copied" })).toBeInTheDocument();
  });

  it("formatTraceToolSummary and formatTraceForClipboard are dogfood-ready", () => {
    const events = pr354HermesTrace.tool_events ?? [];
    expect(formatTraceToolSummary(events, { isHermesGraphAgent: true })).toBe(
      "tools: search_campaign_graph",
    );
    expect(formatTraceToolSummary([], { isHermesGraphAgent: true })).toBe("tools: none");

    const text = formatTraceForClipboard(pr354HermesTrace, {
      answer: "Tripod stands at the North Gate.",
      toolEvents: events,
      skippedToolEvents: 0,
    });
    expect(text).toContain("Graph tool activity (1)");
    expect(text).toContain("revision: rev-1");
    expect(text).not.toContain("RAW_PROMPT_SECRET");
  });

  it("ignores malformed graph tool events with a bounded warning", () => {
    render(
      <TraceDetailsPanel
        trace={{
          ...pr354HermesTrace,
          tool_events: [
            pr354HermesTrace.tool_events?.[0] ?? {},
            { not_a_tool: true },
          ],
        }}
      />,
    );

    expect(screen.getByText("Graph tool activity (1)")).toBeInTheDocument();
    expect(screen.getByText("Skipped 1 malformed graph tool event.")).toBeInTheDocument();
  });

  it("tolerates non-array tool_events, object tool_name, object ID collections, and missing usage", () => {
    render(
      <TraceDetailsPanel
        trace={{
          ...pr354HermesTrace,
          usage: undefined as never,
          tool_events: {
            tool_name: "should-not-iterate",
          } as never,
        }}
      />,
    );

    expect(screen.getByLabelText("Agent interaction trace")).toBeInTheDocument();
    expect(screen.getByText("not reported")).toBeInTheDocument();
    expect(screen.getByText("Skipped 1 malformed graph tool event.")).toBeInTheDocument();
  });

  it("normalizes object-valued shell fields and drops object warnings without crashing", () => {
    render(
      <TraceDetailsPanel
        trace={{
          ...pr354HermesTrace,
          backend: { unexpected: true } as never,
          runtime: { nested: true } as never,
          status: { ok: false } as never,
          mode: "hermes_graph_agent",
          provider: { nested: true } as never,
          model: ["not", "a", "string"] as never,
          toolset: { name: "nope" } as never,
          trace_id: { id: "nope" } as never,
          started_at: { when: "nope" } as never,
          warnings: [{ secret: "unexpected object" }, "bounded string warning"] as never,
          tool_events: [],
        }}
      />,
    );

    expect(screen.getByLabelText("Agent interaction trace")).toBeInTheDocument();
    expect(screen.getByTestId("plan-agent-trace-summary-meta")).toHaveTextContent(
      /unknown · 42ms · tools: none/,
    );
    expect(screen.getByText("hermes_graph_agent")).toBeInTheDocument();
    expect(screen.getByText("n/a / n/a")).toBeInTheDocument();
    expect(screen.getByText("bounded string warning")).toBeInTheDocument();
    expect(screen.queryByText(/unexpected object/)).not.toBeInTheDocument();
  });

  it("drops null events and object-valued tool_name while keeping valid siblings", () => {
    render(
      <TraceDetailsPanel
        trace={{
          ...pr354HermesTrace,
          tool_events: [
            null as never,
            { tool_name: { nested: true }, state: "completion" } as never,
            {
              ...(pr354HermesTrace.tool_events?.[0] ?? {}),
              matched_node_ids: { not: "array" } as never,
              relationship_ids: "nope" as never,
            },
          ],
        }}
      />,
    );

    expect(screen.getByText("Graph tool activity (1)")).toBeInTheDocument();
    expect(screen.getByText("search_campaign_graph")).toBeInTheDocument();
    expect(screen.getByText("Skipped 2 malformed graph tool events.")).toBeInTheDocument();
  });

  it("renders Hermes trace diagnostics when present", () => {
    render(
      <TraceDetailsPanel
        trace={{
          ...pr354HermesTrace,
          answer_scope: "conversation_context",
          tool_event_count: 1,
          evidence_event_count: 0,
          final_response_present: true,
          validator_path: "explicit_conversation_context",
        }}
      />,
    );

    expect(screen.getByText("Answer scope")).toBeInTheDocument();
    expect(screen.getByText("conversation_context")).toBeInTheDocument();
    expect(screen.getByText("Tool events")).toBeInTheDocument();
    expect(screen.getByText("Evidence events")).toBeInTheDocument();
    expect(screen.getByText("Final response")).toBeInTheDocument();
    expect(screen.getByText("present")).toBeInTheDocument();
    expect(screen.getByText("Validator path")).toBeInTheDocument();
    expect(screen.getByText("explicit_conversation_context")).toBeInTheDocument();
  });

  it("redacts Hermes graph agent prompt preview and legacy artifact paths", () => {
    render(
      <TraceDetailsPanel
        trace={{
          ...pr354HermesTrace,
          prompt_preview: "RAW_PROMPT_SECRET",
          artifact_refs: [{ kind: "hermes_session", path: "/tmp/hermes/session.json", label: "session" }],
          steps: [{ name: "lookup", summary: "legacy step should stay hidden for graph agent" }],
        }}
      />,
    );

    expect(screen.queryByText(/RAW_PROMPT_SECRET/)).not.toBeInTheDocument();
    expect(screen.queryByText(/Prompt sent to Hermes/)).not.toBeInTheDocument();
    expect(screen.queryByText(/\/tmp\/hermes/)).not.toBeInTheDocument();
    expect(screen.queryByText("lookup")).not.toBeInTheDocument();
  });

  it("preserves legacy prompt rendering for non-graph Hermes traces", () => {
    render(
      <TraceDetailsPanel
        trace={{
          ...pr354HermesTrace,
          mode: "hermes_cli_oneshot",
          tool_events: [],
          prompt_preview: "Legacy Hermes prompt body",
        }}
      />,
    );

    expect(screen.getByText(/Prompt sent to Hermes/)).toBeInTheDocument();
    expect(screen.getByText("Legacy Hermes prompt body")).toBeInTheDocument();
  });

  it("shows Hermes conversation context telemetry in collapsed summary and expanded section", () => {
    render(
      <TraceDetailsPanel
        trace={{
          ...pr354HermesTrace,
          conversation_context: populatedConversationContext,
        }}
      />,
    );

    expect(screen.getByTestId("plan-agent-trace-summary-meta")).toHaveTextContent(
      /ctx: 6 msgs · 3 pairs · graph meta excluded · pointer: accepted · worker: same · graph: fresh/,
    );
    expect(screen.getByTestId("plan-agent-trace-conversation-context")).toBeInTheDocument();
    expect(screen.getByText("Conversation context")).toBeInTheDocument();
    expect(screen.getByText("History present")).toBeInTheDocument();
    expect(screen.getByText("Message count")).toBeInTheDocument();
    expect(screen.getByText("Pair count")).toBeInTheDocument();
    expect(screen.getByText("Payload shape")).toBeInTheDocument();
    expect(screen.getByText("Graph metadata in history")).toBeInTheDocument();
    expect(screen.getByText("Hermes session pointer in request")).toBeInTheDocument();
    expect(screen.getByText("Hermes session pointer status")).toBeInTheDocument();
    expect(screen.getByText("Worker PID changed")).toBeInTheDocument();
    expect(screen.getByText("Fresh graph revision used")).toBeInTheDocument();
    expect(screen.getByText("accepted")).toBeInTheDocument();
    expect(screen.getByText("role_content_only")).toBeInTheDocument();
    const yesValues = screen.getAllByText("yes");
    const noValues = screen.getAllByText("no");
    expect(yesValues.length).toBeGreaterThanOrEqual(2);
    expect(noValues.length).toBeGreaterThanOrEqual(1);
  });

  it("shows explicit no-history state in collapsed summary when history_present is false", () => {
    render(
      <TraceDetailsPanel
        trace={{
          ...pr354HermesTrace,
          conversation_context: {
            ...populatedConversationContext,
            history_present: false,
            message_count: 0,
            pair_count: 0,
            hermes_session_pointer_status: "absent",
          },
        }}
      />,
    );

    expect(screen.getByTestId("plan-agent-trace-summary-meta")).toHaveTextContent(
      /ctx: no history · pointer: absent · worker: same · graph: fresh/,
    );
    expect(screen.getByTestId("plan-agent-trace-conversation-context")).toBeInTheDocument();
    expect(screen.getByText("History present")).toBeInTheDocument();
    expect(screen.getAllByText("no").length).toBeGreaterThanOrEqual(1);
  });

  it("includes conversation context telemetry in clipboard output without prose", () => {
    const text = formatTraceForClipboard(
      {
        ...pr354HermesTrace,
        conversation_context: populatedConversationContext,
      },
      {
        answer: "Tripod stands at the North Gate.",
        toolEvents: pr354HermesTrace.tool_events ?? [],
        skippedToolEvents: 0,
      },
    );

    expect(text).toContain("Conversation context");
    expect(text).toContain("history_present: yes");
    expect(text).toContain("message_count: 6");
    expect(text).toContain("pair_count: 3");
    expect(text).toContain("payload_shape: role_content_only");
    expect(text).toContain("graph_metadata_in_history: no");
    expect(text).toContain("hermes_session_pointer_in_request: yes");
    expect(text).toContain("hermes_session_pointer_status: accepted");
    expect(text).toContain("worker_pid_changed: no");
    expect(text).toContain("fresh_graph_revision_used: yes");
    expect(text).not.toContain("RAW_PROMPT_SECRET");
  });

  it("formatTraceConversationContextSummary handles populated and no-history states", () => {
    expect(
      formatTraceConversationContextSummary(populatedConversationContext, {
        isHermesGraphAgent: true,
      }),
    ).toBe("ctx: 6 msgs · 3 pairs · graph meta excluded · pointer: accepted · worker: same · graph: fresh");
    expect(
      formatTraceConversationContextSummary(
        { ...populatedConversationContext, graph_metadata_in_history: true },
        { isHermesGraphAgent: true },
      ),
    ).toBe("ctx: 6 msgs · 3 pairs · graph meta in history · pointer: accepted · worker: same · graph: fresh");
    expect(
      formatTraceConversationContextSummary(
        { ...populatedConversationContext, history_present: false },
        { isHermesGraphAgent: true },
      ),
    ).toBe("ctx: no history · pointer: accepted · worker: same · graph: fresh");
    expect(formatTraceConversationContextSummary(null, { isHermesGraphAgent: true })).toBe("");
    expect(
      formatTraceConversationContextSummary(populatedConversationContext, {
        isHermesGraphAgent: false,
      }),
    ).toBe("");
  });

  it("omits conversation context UI when telemetry is absent or malformed", () => {
    const { rerender } = render(<TraceDetailsPanel trace={pr354HermesTrace} />);

    expect(screen.getByTestId("plan-agent-trace-summary-meta")).toHaveTextContent(
      /hermes · process_isolated · ok · 42ms · tools: search_campaign_graph/,
    );
    expect(screen.queryByTestId("plan-agent-trace-conversation-context")).not.toBeInTheDocument();
    expect(screen.queryByText("Conversation context")).not.toBeInTheDocument();

    rerender(
      <TraceDetailsPanel
        trace={{
          ...pr354HermesTrace,
          conversation_context: {
            history_present: true,
            message_count: "not-a-number",
          } as never,
        }}
      />,
    );

    expect(screen.queryByTestId("plan-agent-trace-conversation-context")).not.toBeInTheDocument();
    expect(screen.getByTestId("plan-agent-trace-summary-meta")).not.toHaveTextContent(/ctx:/);
  });
});
