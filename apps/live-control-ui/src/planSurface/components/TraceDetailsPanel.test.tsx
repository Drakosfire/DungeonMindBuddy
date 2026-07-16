import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import type { AgentInteractionTrace } from "../../api/types";
import {
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
});
