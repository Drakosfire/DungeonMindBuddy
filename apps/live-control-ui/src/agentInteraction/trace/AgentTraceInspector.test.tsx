import { readFileSync } from "node:fs";
import path from "node:path";

import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import type { AgentInteractionTrace } from "../../api/types";
import {
  AgentTraceInspector,
  formatSafeTraceDiagnostics,
  formatTraceConversationContextSummary,
  formatTraceToolSummary,
} from "./AgentTraceInspector";

const a0CompleteFixture: AgentInteractionTrace = {
  schema: "dmb_agent_turn_trace_v1",
  trace_id: "trace-a0-complete",
  agent_thread_id: "thread-a0",
  turn_id: "turn-a0",
  runtime: "process_isolated",
  backend: "hermes",
  mode: "hermes_graph_agent",
  provider: "openai-api",
  model: "gpt-5.4",
  started_at: "2026-08-26T18:00:00Z",
  completed_at: "2026-08-26T18:00:07Z",
  elapsed_ms: 7420,
  status: "ok",
  usage: {
    available: true,
    status: "reported",
    input_tokens: 21300,
    cached_input_tokens: 18000,
    cache_write_input_tokens: 0,
    uncached_input_tokens: 3300,
    output_tokens: 981,
    reasoning_tokens: 120,
    total_tokens: 22281,
    model_call_count: 2,
    usage_reported_call_count: 2,
  },
  cost: {
    status: "estimated",
    usd: 0.0061,
    currency: "USD",
    priced_call_count: 2,
    unpriced_call_count: 0,
  },
  model_calls: [
    {
      call_id: "call-1",
      sequence: 1,
      status: "ok",
      provider: "openai-api",
      requested_model: "gpt-5.4",
      response_model: "gpt-5.4",
      api_mode: "chat_completions",
      started_at: "2026-08-26T18:00:00Z",
      completed_at: "2026-08-26T18:00:05Z",
      duration_ms: 5000,
      finish_reason: "stop",
      usage: {
        available: true,
        status: "reported",
        input_tokens: 18000,
        cached_input_tokens: 18000,
        cache_write_input_tokens: 0,
        uncached_input_tokens: 0,
        output_tokens: 400,
        reasoning_tokens: 80,
        total_tokens: 18400,
      },
      cost: { status: "estimated", usd: 0.004, currency: "USD" },
    },
    {
      call_id: "call-2",
      sequence: 2,
      status: "ok",
      provider: "openai-api",
      requested_model: "gpt-5.4",
      response_model: "gpt-5.4",
      api_mode: "chat_completions",
      started_at: "2026-08-26T18:00:05Z",
      completed_at: "2026-08-26T18:00:07Z",
      duration_ms: 2200,
      finish_reason: "stop",
      usage: {
        available: true,
        status: "reported",
        input_tokens: 3300,
        cached_input_tokens: 0,
        cache_write_input_tokens: 0,
        uncached_input_tokens: 3300,
        output_tokens: 581,
        reasoning_tokens: 40,
        total_tokens: 3881,
      },
      cost: { status: "estimated", usd: 0.0021, currency: "USD" },
    },
  ],
  spans: [
    {
      span_id: "span-session",
      kind: "phase",
      name: "session_load",
      status: "ok",
      started_at: "2026-08-26T18:00:00Z",
      completed_at: "2026-08-26T18:00:00Z",
      duration_ms: 80,
    },
    {
      span_id: "span-harness",
      kind: "phase",
      name: "harness_turn",
      status: "ok",
      started_at: "2026-08-26T18:00:00Z",
      completed_at: "2026-08-26T18:00:07Z",
      duration_ms: 7120,
    },
    {
      span_id: "span-project",
      kind: "phase",
      name: "response_projection",
      status: "ok",
      started_at: "2026-08-26T18:00:07Z",
      completed_at: "2026-08-26T18:00:07Z",
      duration_ms: 220,
    },
  ],
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
  conversation_context: {
    history_present: true,
    message_count: 6,
    pair_count: 3,
    payload_shape: "role_content_only",
    graph_metadata_in_history: false,
    hermes_session_pointer_in_request: true,
    hermes_session_pointer_status: "accepted",
    worker_pid_changed: false,
    fresh_graph_revision_used: true,
  },
  hermes_session_id: "hermes-sess-obs-only",
  process_isolation: "process_exclusive",
  warnings: [],
};

const a0RetryPartialFixture: AgentInteractionTrace = {
  ...a0CompleteFixture,
  trace_id: "trace-a0-retry-partial",
  usage: {
    available: true,
    status: "partial",
    input_tokens: 21300,
    cached_input_tokens: 18000,
    cache_write_input_tokens: 0,
    uncached_input_tokens: 3300,
    output_tokens: 981,
    reasoning_tokens: 120,
    total_tokens: 22281,
    model_call_count: 2,
    usage_reported_call_count: 1,
  },
  cost: {
    status: "partial",
    usd: 0.0061,
    currency: "USD",
    priced_call_count: 1,
    unpriced_call_count: 1,
  },
  model_calls: [
    {
      call_id: "call-1",
      sequence: 1,
      status: "error",
      provider: "openai-api",
      requested_model: "gpt-5.4",
      response_model: "gpt-5.4",
      api_mode: "chat_completions",
      started_at: "2026-08-26T18:00:00Z",
      completed_at: "2026-08-26T18:00:01Z",
      duration_ms: 1000,
      usage: {
        available: false,
        status: "unavailable",
        input_tokens: null,
        output_tokens: null,
        total_tokens: null,
      },
      cost: { status: "unavailable", usd: null },
      retry_count: 1,
      retryable: true,
      status_code: 429,
      error_type: "rate_limit",
    },
    {
      call_id: "call-2",
      sequence: 2,
      status: "ok",
      provider: "openai-api",
      requested_model: "gpt-5.4",
      response_model: "gpt-5.4",
      api_mode: "chat_completions",
      started_at: "2026-08-26T18:00:01Z",
      completed_at: "2026-08-26T18:00:06Z",
      duration_ms: 5000,
      finish_reason: "stop",
      usage: {
        available: true,
        status: "reported",
        input_tokens: 21300,
        cached_input_tokens: 18000,
        uncached_input_tokens: 3300,
        output_tokens: 981,
        reasoning_tokens: 120,
        total_tokens: 22281,
      },
      cost: { status: "estimated", usd: 0.0061, currency: "USD" },
    },
  ],
};

const a0MillisecondPhaseFixture: AgentInteractionTrace = {
  ...a0CompleteFixture,
  trace_id: "trace-a0-ms-phases",
  started_at: "2026-08-26T18:00:00.000Z",
  completed_at: "2026-08-26T18:00:07.420Z",
  spans: [
    {
      span_id: "span-session",
      kind: "phase",
      name: "session_load",
      status: "ok",
      started_at: "2026-08-26T18:00:00.000Z",
      completed_at: "2026-08-26T18:00:00.080Z",
      duration_ms: 80,
    },
    {
      span_id: "span-harness",
      kind: "phase",
      name: "harness_turn",
      status: "ok",
      started_at: "2026-08-26T18:00:00.080Z",
      completed_at: "2026-08-26T18:00:07.200Z",
      duration_ms: 7120,
    },
    {
      span_id: "span-project",
      kind: "phase",
      name: "response_projection",
      status: "ok",
      started_at: "2026-08-26T18:00:07.200Z",
      completed_at: "2026-08-26T18:00:07.420Z",
      duration_ms: 220,
    },
  ],
};

const legacyHermesTrace: AgentInteractionTrace = {
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
  tool_events: a0CompleteFixture.tool_events,
  hermes_session_id: "hermes-sess-obs-only",
  process_isolation: "process_exclusive",
  warnings: [],
  prompt_preview: "RAW_PROMPT_SECRET should never render for graph agent traces",
};

function truncatedFixture(): AgentInteractionTrace {
  const retained = Array.from({ length: 64 }, (_, index) => ({
    call_id: `call-${index + 1}`,
    sequence: index + 1,
    status: "ok" as const,
    provider: "openai-api",
    requested_model: "gpt-5.4",
    response_model: "gpt-5.4",
    duration_ms: 10,
    usage: {
      available: true,
      status: "reported" as const,
      input_tokens: 10,
      output_tokens: 2,
      total_tokens: 12,
    },
    cost: { status: "estimated" as const, usd: 0.0001 },
  }));
  return {
    ...a0CompleteFixture,
    trace_id: "trace-truncated",
    usage: {
      available: true,
      status: "partial",
      input_tokens: 640,
      output_tokens: 128,
      total_tokens: 768,
      model_call_count: 64,
      usage_reported_call_count: 64,
      observed_model_call_count: 65,
    },
    cost: {
      status: "partial",
      usd: 0.0064,
      currency: "USD",
      priced_call_count: 64,
      unpriced_call_count: 0,
    },
    model_calls: retained,
    warnings: ["model_calls_truncated"],
  };
}

describe("AgentTraceInspector", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("does not import Plan, Play, or Build production symbols", () => {
    const source = readFileSync(
      path.join(__dirname, "AgentTraceInspector.tsx"),
      "utf8",
    );
    expect(source).not.toMatch(/from ["'].*(planSurface|playSurface|buildSurface)/);
  });

  it("renders complete A0 overview tokens, cost, model, and elapsed from server values", () => {
    render(<AgentTraceInspector trace={a0CompleteFixture} />);

    expect(screen.getByLabelText("Agent interaction trace")).toBeInTheDocument();
    expect(screen.getByText("Advanced diagnostics")).toBeInTheDocument();
    expect(screen.getByTestId("agent-trace-summary-meta")).toHaveTextContent(/7\.42 s/);
    expect(screen.getByTestId("agent-trace-summary-meta")).toHaveTextContent(/21\.3k in → 981 out/);
    expect(screen.getByTestId("agent-trace-summary-meta")).toHaveTextContent(/\$0\.0061 est\./);
    expect(screen.getByTestId("agent-trace-overview")).toHaveTextContent("trace-a0-complete");
    expect(screen.getByTestId("agent-trace-overview")).toHaveTextContent("openai-api / gpt-5.4");
    expect(screen.getByTestId("agent-trace-overview")).toHaveTextContent("7420 ms");
    expect(screen.getByTestId("agent-trace-overview")).toHaveTextContent("cached 18000");
    expect(screen.getByTestId("agent-trace-overview")).toHaveTextContent("reasoning 120");
    expect(screen.getByTestId("agent-trace-overview")).toHaveTextContent("$0.0061 estimated");
    expect(screen.getByTestId("agent-trace-overview")).toHaveTextContent("2 model calls");
    expect(screen.getByTestId("agent-trace-overview")).toHaveTextContent("2 priced / 0 unpriced");
  });

  it("keeps failed and retried model calls visible as separate rows with partial aggregates", () => {
    render(<AgentTraceInspector trace={a0RetryPartialFixture} />);

    const rows = screen.getAllByTestId("agent-trace-model-call");
    expect(rows).toHaveLength(2);
    expect(rows[0]).toHaveTextContent("#1");
    expect(rows[0]).toHaveTextContent("error");
    expect(rows[0]).toHaveTextContent("rate_limit");
    expect(rows[0]).toHaveTextContent("429");
    expect(rows[0]).toHaveTextContent("retryable");
    expect(rows[0]).toHaveTextContent("unavailable");
    expect(rows[1]).toHaveTextContent("#2");
    expect(rows[1]).toHaveTextContent("ok");
    expect(rows[1]).toHaveTextContent("5000 ms");
    expect(rows[1]).toHaveTextContent("$0.0061 estimated");
    expect(screen.getByTestId("agent-trace-overview")).toHaveTextContent("partial");
    expect(screen.getByTestId("agent-trace-overview")).toHaveTextContent("$0.0061 partial");
    expect(screen.getByTestId("agent-trace-overview")).toHaveTextContent("1 priced / 1 unpriced");
  });

  it("shows truncation as partial with retained vs observed counts", () => {
    render(<AgentTraceInspector trace={truncatedFixture()} />);

    expect(screen.getByTestId("agent-trace-summary-meta")).toHaveTextContent(
      /64 retained \/ 65 observed calls/,
    );
    expect(screen.getByTestId("agent-trace-overview")).toHaveTextContent("partial");
    expect(screen.getByTestId("agent-trace-overview")).toHaveTextContent("$0.0064 partial");
    expect(screen.getByText("model_calls_truncated")).toBeInTheDocument();
    expect(screen.getAllByTestId("agent-trace-model-call")).toHaveLength(64);
    expect(screen.getByTestId("agent-trace-overview")).toHaveTextContent("64 retained / 65 observed calls");
  });

  it("qualifies unavailable usage, cost, and missing span timing instead of zeros", () => {
    render(
      <AgentTraceInspector
        trace={{
          ...a0CompleteFixture,
          usage: {
            available: false,
            status: "unavailable",
            input_tokens: null,
            output_tokens: null,
            total_tokens: null,
          },
          cost: { status: "unavailable", usd: null },
          model_calls: [{
            ...a0CompleteFixture.model_calls![1],
            usage: {
              available: false,
              status: "unavailable",
              input_tokens: null,
              output_tokens: null,
              total_tokens: null,
            },
            cost: { status: "unavailable", usd: null },
          }],
          spans: [{
            span_id: "span-missing",
            kind: "phase",
            name: "world_context_resolution",
            status: "unavailable",
            duration_ms: null,
          }],
        }}
      />,
    );

    expect(screen.getByTestId("agent-trace-overview")).toHaveTextContent("unavailable");
    expect(screen.queryByText("$0.00")).not.toBeInTheDocument();
    expect(screen.queryByText("$0")).not.toBeInTheDocument();
    const phase = screen.getByTestId("agent-trace-phase");
    expect(phase).toHaveTextContent("timing unavailable");
    expect(phase.querySelector(".agent-trace-bar-fill")).toBeNull();
  });

  it("renders product phase durations without placing tools on that timeline", () => {
    render(<AgentTraceInspector trace={a0CompleteFixture} />);

    const phases = screen.getAllByTestId("agent-trace-phase");
    expect(phases).toHaveLength(3);
    expect(phases[0]).toHaveTextContent("session_load");
    expect(phases[0]).toHaveTextContent("80 ms");
    expect(screen.getByTestId("agent-trace-tools")).toHaveTextContent("18ms");
    expect(screen.getByTestId("agent-trace-tools")).toHaveTextContent("enough");
    expect(screen.getByTestId("agent-trace-phases").textContent).not.toContain("search_campaign_graph");
  });

  it("uses duration-only phase bars for A0 whole-second timestamps", () => {
    render(<AgentTraceInspector trace={a0CompleteFixture} />);

    const section = screen.getByTestId("agent-trace-phases");
    expect(section).toHaveAttribute("data-timing-placement", "duration-only");
    const bars = screen.getAllByTestId("agent-trace-phase-bar");
    expect(bars).toHaveLength(3);
    const widths = bars.map((bar) => {
      expect(bar).toHaveClass("agent-trace-bar-track--duration-only");
      expect(bar.getAttribute("style")).toContain("--trace-bar-offset: 0%");
      const match = bar.getAttribute("style")?.match(/--trace-bar-width:\s*([\d.]+)%/);
      return Number(match?.[1] ?? NaN);
    });
    expect(widths[0]).toBeCloseTo((80 / 7120) * 100, 5);
    expect(widths[1]).toBe(100);
    expect(widths[2]).toBeCloseTo((220 / 7120) * 100, 5);
    expect(new Set(widths).size).toBe(3);
  });

  it("places phase bars only when timestamp precision can distinguish the durations", () => {
    render(<AgentTraceInspector trace={a0MillisecondPhaseFixture} />);

    const section = screen.getByTestId("agent-trace-phases");
    expect(section).toHaveAttribute("data-timing-placement", "relative-offset");
    const bars = screen.getAllByTestId("agent-trace-phase-bar");
    const offsets = bars.map((bar) => {
      expect(bar).not.toHaveClass("agent-trace-bar-track--duration-only");
      const match = bar.getAttribute("style")?.match(/--trace-bar-offset:\s*([\d.]+)%/);
      return Number(match?.[1] ?? NaN);
    });
    expect(offsets[0]).toBe(0);
    expect(offsets[1]).toBeCloseTo((80 / 7420) * 100, 5);
    expect(offsets[2]).toBeCloseTo((7200 / 7420) * 100, 5);
    expect(offsets[1]).not.toBe(offsets[0]);
    expect(offsets[2]).not.toBe(offsets[1]);
  });

  it("copies safe structured diagnostics without question, answer, or raw bodies", async () => {
    const user = userEvent.setup();
    const writeText = vi.fn().mockResolvedValue(undefined);
    Object.defineProperty(navigator, "clipboard", {
      configurable: true,
      value: { writeText },
    });

    render(
      <AgentTraceInspector
        trace={{
          ...a0CompleteFixture,
          prompt_preview: "SECRET_PROMPT",
        }}
      />,
    );

    await user.click(screen.getByRole("button", { name: "Copy diagnostics" }));
    expect(writeText).toHaveBeenCalledTimes(1);
    const copied = String(writeText.mock.calls[0]?.[0] ?? "");
    expect(copied).toContain("trace-a0-complete");
    expect(copied).toContain("gpt-5.4");
    expect(copied).toContain("0.0061");
    expect(copied).not.toContain("Where is Tripod");
    expect(copied).not.toContain("SECRET_PROMPT");
    expect(copied).not.toContain('"question"');
    expect(copied).not.toContain('"answer"');
    expect(screen.getByRole("button", { name: "Copied" })).toBeInTheDocument();
  });

  it("strips forbidden sentinel keys from copied diagnostics", () => {
    const text = formatSafeTraceDiagnostics({
      ...a0CompleteFixture,
      request: { body: "SENTINEL_REQUEST_BODY" },
      response: { assistant_message: { content: "SENTINEL_RESPONSE" } },
      prompt: "SENTINEL_PROMPT",
      messages: [{ role: "user", content: "SENTINEL_MESSAGES" }],
      args: { q: "SENTINEL_ARGS" },
      result: "SENTINEL_RESULT",
    } as unknown as AgentInteractionTrace);

    expect(text).toContain("trace-a0-complete");
    expect(text).not.toContain("SENTINEL_REQUEST_BODY");
    expect(text).not.toContain("SENTINEL_RESPONSE");
    expect(text).not.toContain("SENTINEL_PROMPT");
    expect(text).not.toContain("SENTINEL_MESSAGES");
    expect(text).not.toContain("SENTINEL_ARGS");
    expect(text).not.toContain("SENTINEL_RESULT");
  });

  it("renders a legacy unversioned Hermes graph trace without crashing", () => {
    render(<AgentTraceInspector trace={legacyHermesTrace} />);

    expect(screen.getByLabelText("Agent interaction trace")).toBeInTheDocument();
    expect(screen.getByText("Graph tool activity (1)")).toBeInTheDocument();
    expect(screen.getByText(/completion · 18ms · enough/)).toBeInTheDocument();
    expect(screen.getByText("node-tripod")).toBeInTheDocument();
    expect(screen.queryByTestId("agent-trace-model-calls")).not.toBeInTheDocument();
    expect(screen.queryByText(/RAW_PROMPT_SECRET/)).not.toBeInTheDocument();
  });

  it("drops malformed additive fields and keeps usable siblings", () => {
    render(
      <AgentTraceInspector
        trace={{
          ...legacyHermesTrace,
          backend: { unexpected: true } as never,
          model_calls: [
            null as never,
            { not_a_call: true } as never,
            a0CompleteFixture.model_calls![1],
          ],
          spans: [
            { name: "no-id" } as never,
            a0CompleteFixture.spans![0],
          ],
          warnings: [{ secret: "unexpected object" }, "bounded string warning"] as never,
        }}
      />,
    );

    expect(screen.getByLabelText("Agent interaction trace")).toBeInTheDocument();
    expect(screen.getAllByTestId("agent-trace-model-call")).toHaveLength(1);
    expect(screen.getAllByTestId("agent-trace-phase")).toHaveLength(1);
    expect(screen.getByText("bounded string warning")).toBeInTheDocument();
    expect(screen.queryByText(/unexpected object/)).not.toBeInTheDocument();
  });

  it("shows conversation context telemetry and tools: none for empty Hermes graph traces", () => {
    render(
      <AgentTraceInspector
        trace={{
          ...legacyHermesTrace,
          tool_events: [],
          conversation_context: a0CompleteFixture.conversation_context,
        }}
      />,
    );

    expect(screen.getByTestId("agent-trace-summary-meta")).toHaveTextContent(/tools: none/);
    expect(screen.getByTestId("agent-trace-summary-meta")).toHaveTextContent(
      /ctx: 6 msgs · 3 pairs · graph meta excluded/,
    );
    expect(screen.getByTestId("agent-trace-conversation-context")).toBeInTheDocument();
    expect(screen.getByTestId("agent-trace-tools-none")).toHaveTextContent(/No graph tools were called/);
  });

  it("format helpers remain available for tool and conversation summaries", () => {
    expect(formatTraceToolSummary(legacyHermesTrace.tool_events ?? [], { isHermesGraphAgent: true }))
      .toBe("tools: search_campaign_graph");
    expect(formatTraceConversationContextSummary(a0CompleteFixture.conversation_context ?? null, {
      isHermesGraphAgent: true,
    })).toContain("ctx: 6 msgs");
  });
});
