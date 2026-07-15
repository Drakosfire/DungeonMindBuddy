import { act, renderHook } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { ReactNode } from "react";

import type { LiveQueryResponse } from "../api/types";
import { AgentInteractionProvider } from "./AgentInteractionProvider";
import { activeThreadStorageKey, createAgentInteractionThread, persistAgentThread, threadStorageKey } from "./agentInteractionStorage";
import { useAgentInteraction } from "./useAgentInteraction";

function wrapper({ children }: { children: ReactNode }) {
  return <AgentInteractionProvider>{children}</AgentInteractionProvider>;
}

const response: LiveQueryResponse = {
  answer: "Provider-owned answer",
  status: "ok",
  classification: {} as never,
  events_written: [],
  jobs_queued: [],
  next_suggestions: [],
  diagnostics: {},
  provenance: {},
  citations: [{ evidence_id: "e1", path: "corpus/session.md", line_start: 3, line_end: 5, source_role: "play_recap", authority: "canon_play" }],
  ["context" + "_packet"]: null,
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
};

describe("AgentInteractionProvider", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    localStorage.clear();
  });

  it("publishes plan surface context and appends turns into provider-owned state", () => {
    const { result } = renderHook(() => useAgentInteraction(), { wrapper });

    act(() => {
      result.current.rehydrateScope({ campaignId: "longmont-c2", sessionNumber: 23, surfaceId: "plan" });
      result.current.publishSurfaceContext({
        surfaceId: "plan",
        label: "Plan · Session 23",
        campaignId: "longmont-c2",
        sessionNumber: 23,
        ambientSummary: "Small bounded summary",
        sourceEnvelope: null,
        updatedAt: "2026-06-28T00:00:00.000Z",
      });
    });

    act(() => {
      result.current.appendResponseTurn("What changed?", response);
    });

    expect(result.current.activeSurfaceContext?.surfaceId).toBe("plan");
    expect(result.current.activeThread?.turns[0]).toMatchObject({ question: "What changed?", answer: "Provider-owned answer" });
    expect(result.current.activeThread?.turns[0].retrievalFreshness?.decision).toBe("fresh_retrieval");
  });

  it("rehydrates saved thread state and keeps thread turns isolated", () => {
    const first = { ...createAgentInteractionThread("longmont-c2", 23, "plan", "live", "First"), threadId: "first" };
    const second = { ...createAgentInteractionThread("longmont-c2", 23, "plan", "hermes", "Second"), threadId: "second" };
    first.turns = [{ turnId: "t1", askedAt: "2026-06-28T00:00:00.000Z", question: "A?", answer: "A", backend: "live", status: "ok" }];
    second.turns = [{ turnId: "t2", askedAt: "2026-06-28T00:00:00.000Z", question: "B?", answer: "B", backend: "hermes", status: "ok", corpusFreshness: { status: "changed", checked_at: "2026-06-28T00:00:00.000Z", diagnostics: [], warnings: [] } }];
    persistAgentThread(first);
    persistAgentThread(second);
    localStorage.setItem(activeThreadStorageKey("longmont-c2", "plan"), "second");

    const { result } = renderHook(() => useAgentInteraction(), { wrapper });
    act(() => result.current.rehydrateScope({ campaignId: "longmont-c2", sessionNumber: 23, surfaceId: "plan" }));

    expect(result.current.activeThread?.threadId).toBe("second");
    expect(result.current.turns[0].question).toBe("B?");
    expect(result.current.turns[0].corpusFreshness?.status).toBe("changed");

    act(() => {
      result.current.switchThread("first");
    });

    expect(result.current.activeThread?.threadId).toBe("first");
    expect(result.current.turns[0].question).toBe("A?");
    expect(result.current.turns[0].question).not.toBe("B?");
  });

  it("clears stale Hermes session and strips graph hermes_session_id from safe traces", () => {
    const staleSession = {
      sessionId: "stale-hermes-session",
      runtime: "api",
      title: "Stale session",
    };
    const seeded = {
      ...createAgentInteractionThread("longmont-c2", 23, "plan", "hermes", "Seeded"),
      threadId: "seeded-thread",
      hermesSession: staleSession,
    };
    persistAgentThread(seeded);
    localStorage.setItem(activeThreadStorageKey("longmont-c2", "plan"), seeded.threadId);

    const { result } = renderHook(() => useAgentInteraction(), { wrapper });
    act(() => result.current.rehydrateScope({ campaignId: "longmont-c2", sessionNumber: 23, surfaceId: "plan" }));
    expect(result.current.activeThread?.hermesSession).toEqual(staleSession);

    act(() => {
      result.current.appendResponseTurn("Graph question?", {
        ...response,
        mode: "hermes_graph_agent",
        hermes_session: null,
        agent_trace: {
          trace_id: "trace-hermes",
          hermes_session_id: "observability-only-session",
          runtime: "api",
          backend: "hermes",
          mode: "hermes_graph_agent",
          started_at: "2026-06-28T00:00:00.000Z",
          completed_at: "2026-06-28T00:00:01.000Z",
          elapsed_ms: 10,
          status: "ok",
          usage: { available: true, input_tokens: 1, output_tokens: 1, total_tokens: 2 },
          steps: [],
          context_summary: {},
          artifact_refs: [],
          warnings: [],
        } as never,
      });
    });

    expect(result.current.activeThread?.hermesSession).toBeNull();
    expect(result.current.activeThread?.turns[0].trace?.hermes_session_id).toBeUndefined();
  });

  it("keeps subsequent Hermes turns independent without forwarding a session handle", () => {
    const { result } = renderHook(() => useAgentInteraction(), { wrapper });
    act(() => result.current.rehydrateScope({ campaignId: "longmont-c2", sessionNumber: 23, surfaceId: "plan" }));

    act(() => {
      result.current.appendResponseTurn("First graph turn?", {
        ...response,
        mode: "hermes_graph_agent",
        hermes_session: null,
      });
    });
    act(() => {
      result.current.appendResponseTurn("Second graph turn?", {
        ...response,
        answer: "Second answer",
        mode: "hermes_graph_agent",
        hermes_session: null,
      });
    });

    expect(result.current.activeThread?.hermesSession).toBeNull();
    expect(result.current.activeThread?.turns).toHaveLength(2);
    expect(result.current.activeThread?.turns[0].answer).toBe("Second answer");
  });

  it("preserves legacy Live Hermes session forwarding behavior", () => {
    const liveSession = {
      sessionId: "live-hermes-session",
      runtime: "cli",
      title: "Live session",
    };
    const { result } = renderHook(() => useAgentInteraction(), { wrapper });
    act(() => result.current.rehydrateScope({ campaignId: "longmont-c2", sessionNumber: 23, surfaceId: "plan" }));

    act(() => {
      result.current.appendResponseTurn("Live turn?", {
        ...response,
        mode: "live",
        hermes_session: liveSession,
      });
    });

    expect(result.current.activeThread?.hermesSession).toEqual(liveSession);
  });

  it("persists bounded metadata without prompt previews or raw context packets", () => {
    const { result } = renderHook(() => useAgentInteraction(), { wrapper });
    act(() => result.current.rehydrateScope({ campaignId: "longmont-c2", sessionNumber: 23, surfaceId: "plan" }));
    act(() => result.current.appendResponseTurn("Bounded?", { ...response, ["context" + "_packet"]: { admitted_evidence: [{ evidence_id: "e1", path: "corpus/session.md", source_role: "play_recap", authority: "canon_play", text_excerpt: "unbounded excerpt" }], rejected_evidence: [] }, agent_trace: { trace_id: "trace", prompt_preview: "raw" + " prompt", artifact_refs: [{ kind: "file", label: "tmp", path: "/tmp/raw.json" }] } as never }));

    const activeThreadId = localStorage.getItem(activeThreadStorageKey("longmont-c2", "plan"));
    const stored = localStorage.getItem(threadStorageKey("longmont-c2", String(activeThreadId))) ?? "";
    expect(stored).toContain("Bounded?");
    expect(stored).toContain("corpus/session.md");
    expect(stored).not.toContain("raw" + " prompt");
    expect(stored).not.toContain("unbounded excerpt");
    expect(stored).not.toContain("context" + "_packet");
    expect(stored).not.toContain("/tmp/raw.json");
  });
});
