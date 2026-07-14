import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import type { AgentInteractionTrace } from "../../api/types";
import { TraceDetailsPanel } from "./TraceDetailsPanel";

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
      outcome: "enough",
      source_anchor_ids: ["source-anchor:v1:fixture"],
    },
  ],
  hermes_session_id: "hermes-sess-obs-only",
  process_isolation: "process_exclusive",
  warnings: [],
};

describe("TraceDetailsPanel", () => {
  it("renders a PR354 Hermes graph agent_trace with Trace shell fields safely", () => {
    render(
      <TraceDetailsPanel
        trace={pr354HermesTrace}
        answer="Tripod stands at the North Gate."
      />,
    );

    expect(screen.getByLabelText("Agent interaction trace")).toBeInTheDocument();
    expect(screen.getByText(/hermes · process_isolated · ok · 42ms/)).toBeInTheDocument();
    expect(screen.getByText("not reported")).toBeInTheDocument();
    expect(screen.getByText("hermes_graph_agent")).toBeInTheDocument();
  });
});
