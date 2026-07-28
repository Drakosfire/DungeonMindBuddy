import { act, renderHook } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { ReactNode } from "react";

import type { LiveQueryResponse } from "../api/types";
import { AgentInteractionProvider } from "./AgentInteractionProvider";
import { activeThreadStorageKey, createAgentInteractionThread, persistAgentThread, threadStorageKey } from "./agentInteractionStorage";
import { FIXTURE_DOC_ID } from "../planSurface/config/planSessionDescriptor";
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
      result.current.rehydrateScope({ campaignId: "longmont-c2", sessionNumber: 23, surfaceId: "plan", documentId: FIXTURE_DOC_ID });
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
    const first = { ...createAgentInteractionThread("longmont-c2", 23, "plan", "live", "First", FIXTURE_DOC_ID), threadId: "first" };
    const second = { ...createAgentInteractionThread("longmont-c2", 23, "plan", "hermes", "Second", FIXTURE_DOC_ID), threadId: "second" };
    first.turns = [{ turnId: "t1", askedAt: "2026-06-28T00:00:00.000Z", question: "A?", answer: "A", backend: "live", status: "ok" }];
    second.turns = [{ turnId: "t2", askedAt: "2026-06-28T00:00:00.000Z", question: "B?", answer: "B", backend: "hermes", status: "ok", corpusFreshness: { status: "changed", checked_at: "2026-06-28T00:00:00.000Z", diagnostics: [], warnings: [] } }];
    persistAgentThread(first);
    persistAgentThread(second);
    localStorage.setItem(activeThreadStorageKey("longmont-c2", "plan", FIXTURE_DOC_ID), "second");

    const { result } = renderHook(() => useAgentInteraction(), { wrapper });
    act(() => result.current.rehydrateScope({ campaignId: "longmont-c2", sessionNumber: 23, surfaceId: "plan", documentId: FIXTURE_DOC_ID }));

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

  it("persists server-approved Hermes pointer for graph turns", () => {
    const { result } = renderHook(() => useAgentInteraction(), { wrapper });
    act(() => result.current.rehydrateScope({ campaignId: "longmont-c2", sessionNumber: 23, surfaceId: "plan", documentId: FIXTURE_DOC_ID }));

    act(() => {
      result.current.appendResponseTurn("Graph question?", {
        ...response,
        mode: "hermes_graph_agent",
        hermes_session: {
          sessionId: "hptr-server-approved",
          runtime: "process_isolated",
          title: null,
          createdAt: "2026-06-28T00:00:00.000Z",
          updatedAt: "2026-06-28T00:00:01.000Z",
        },
        agent_trace: {
          trace_id: "trace-hermes",
          runtime: "process_isolated",
          backend: "hermes",
          mode: "hermes_graph_agent",
          started_at: "2026-06-28T00:00:00.000Z",
          completed_at: "2026-06-28T00:00:01.000Z",
          elapsed_ms: 10,
          status: "ok",
          usage: { available: false, input_tokens: null, output_tokens: null, total_tokens: null },
          steps: [],
          context_summary: {},
          artifact_refs: [],
          conversation_context: {
            history_present: false,
            message_count: 0,
            pair_count: 0,
            payload_shape: "role_content_only",
            graph_metadata_in_history: false,
            hermes_session_pointer_in_request: false,
            hermes_session_pointer_status: "absent",
            worker_pid_changed: false,
            fresh_graph_revision_used: true,
          },
          warnings: [],
        } as never,
      });
    });

    expect(result.current.activeThread?.hermesSession?.sessionId).toBe("hptr-server-approved");
    expect(result.current.activeThread?.turns[0].trace?.hermes_session_id).toBeUndefined();
  });

  it("rehydrates persisted Hermes pointer with the thread", () => {
    const seeded = {
      ...createAgentInteractionThread("longmont-c2", 23, "plan", "hermes", "Seeded", FIXTURE_DOC_ID),
      threadId: "seeded-thread",
      hermesSession: {
        sessionId: "hptr-reload",
        runtime: "process_isolated",
        title: null,
        createdAt: "2026-06-28T00:00:00.000Z",
        updatedAt: "2026-06-28T00:00:01.000Z",
      },
    };
    persistAgentThread(seeded);
    localStorage.setItem(activeThreadStorageKey("longmont-c2", "plan", FIXTURE_DOC_ID), seeded.threadId);

    const { result } = renderHook(() => useAgentInteraction(), { wrapper });
    act(() => result.current.rehydrateScope({ campaignId: "longmont-c2", sessionNumber: 23, surfaceId: "plan", documentId: FIXTURE_DOC_ID }));

    expect(result.current.activeThread?.hermesSession?.sessionId).toBe("hptr-reload");
  });

  it("keeps subsequent Hermes turns forwarding the persisted pointer", () => {
    const { result } = renderHook(() => useAgentInteraction(), { wrapper });
    act(() => result.current.rehydrateScope({ campaignId: "longmont-c2", sessionNumber: 23, surfaceId: "plan", documentId: FIXTURE_DOC_ID }));

    act(() => {
      result.current.appendResponseTurn("First graph turn?", {
        ...response,
        mode: "hermes_graph_agent",
        hermes_session: {
          sessionId: "hptr-follow-up",
          runtime: "process_isolated",
          title: null,
        },
      });
    });
    act(() => {
      result.current.appendResponseTurn("Second graph turn?", {
        ...response,
        answer: "Second answer",
        mode: "hermes_graph_agent",
        hermes_session: {
          sessionId: "hptr-follow-up",
          runtime: "process_isolated",
          title: null,
        },
      });
    });

    expect(result.current.activeThread?.hermesSession?.sessionId).toBe("hptr-follow-up");
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
    act(() => result.current.rehydrateScope({ campaignId: "longmont-c2", sessionNumber: 23, surfaceId: "plan", documentId: FIXTURE_DOC_ID }));

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
    act(() => result.current.rehydrateScope({ campaignId: "longmont-c2", sessionNumber: 23, surfaceId: "plan", documentId: FIXTURE_DOC_ID }));
    act(() => result.current.appendResponseTurn("Bounded?", { ...response, ["context" + "_packet"]: { admitted_evidence: [{ evidence_id: "e1", path: "corpus/session.md", source_role: "play_recap", authority: "canon_play", text_excerpt: "unbounded excerpt" }], rejected_evidence: [] }, agent_trace: { trace_id: "trace", prompt_preview: "raw" + " prompt", artifact_refs: [{ kind: "file", label: "tmp", path: "/tmp/raw.json" }] } as never }));

    const activeThreadId = localStorage.getItem(activeThreadStorageKey("longmont-c2", "plan", FIXTURE_DOC_ID));
    const stored = localStorage.getItem(threadStorageKey("longmont-c2", String(activeThreadId))) ?? "";
    expect(stored).toContain("Bounded?");
    expect(stored).toContain("corpus/session.md");
    expect(stored).not.toContain("raw" + " prompt");
    expect(stored).not.toContain("unbounded excerpt");
    expect(stored).not.toContain("context" + "_packet");
    expect(stored).not.toContain("/tmp/raw.json");
  });

  it("rehydrates build scope with null sessionNumber", () => {
    const { result } = renderHook(() => useAgentInteraction(), { wrapper });

    act(() => {
      result.current.rehydrateScope({
        campaignId: "eldyrwild",
        sessionNumber: null,
        surfaceId: "build",
        documentId: FIXTURE_DOC_ID,
      });
    });

    expect(result.current.scope?.sessionNumber).toBeNull();
  });

  it("publishes projection surface with token-safe cleanup", () => {
    const { result } = renderHook(() => useAgentInteraction(), { wrapper });
    const publication = {
      identity: { surfaceId: "build", instanceKey: "build\u001f__new_source__" },
      config: {
        id: "build" as const,
        label: "Build",
        context: null,
        tools: [],
        canvas: { documentId: null },
        theme: {},
      },
    };

    let cleanup: (() => void) | undefined;
    act(() => {
      cleanup = result.current.publishProjectionSurface(publication);
    });
    expect(result.current.projectionSurface?.projectionsEnabled).toBe(false);

    act(() => {
      cleanup?.();
    });
    expect(result.current.projectionSurface).toBeNull();
  });

  it("rejects stale openTool after surface replacement before rerender", () => {
    const planPublication = {
      identity: { surfaceId: "plan", instanceKey: "plan\u001ftest" },
      config: {
        id: "plan" as const,
        label: "Plan",
        context: {
          campaignId: "longmont-c2",
          liveSession: 22,
          ingestSession: 21,
          headerLabel: "Plan",
        },
        tools: [{ id: "recap", label: "Recap", size: "wide" as const }],
        canvas: { documentId: FIXTURE_DOC_ID },
        theme: {},
      },
    };
    const buildPublication = {
      identity: { surfaceId: "build", instanceKey: "build\u001f__new_source__" },
      config: {
        id: "build" as const,
        label: "Build",
        context: null,
        tools: [],
        canvas: { documentId: null },
        theme: {},
      },
    };

    const { result } = renderHook(() => useAgentInteraction(), { wrapper });
    act(() => {
      result.current.publishProjectionSurface(planPublication);
    });
    const staleOpenTool = result.current.openTool;
    act(() => {
      result.current.publishProjectionSurface(buildPublication);
      staleOpenTool("recap");
    });
    expect(result.current.active).toBeNull();
  });

  it("rejects stale close after surface replacement before rerender", () => {
    const planPublication = {
      identity: { surfaceId: "plan", instanceKey: "plan\u001fclose-test" },
      config: {
        id: "plan" as const,
        label: "Plan",
        context: {
          campaignId: "longmont-c2",
          liveSession: 22,
          ingestSession: 21,
          headerLabel: "Plan",
        },
        tools: [{ id: "recap", label: "Recap", size: "wide" as const }],
        canvas: { documentId: FIXTURE_DOC_ID },
        theme: {},
      },
    };
    const ingestPublication = {
      identity: { surfaceId: "ingest", instanceKey: "ingest\u001fclose-test" },
      config: {
        id: "ingest" as const,
        label: "Ingest",
        context: {
          campaignId: "longmont-c2",
          liveSession: 22,
          ingestSession: 21,
          headerLabel: "Ingest",
        },
        tools: [{ id: "ingest-recap", label: "Recap", size: "wide" as const }],
        canvas: { documentId: null },
        theme: {},
      },
    };

    const { result } = renderHook(() => useAgentInteraction(), { wrapper });
    act(() => {
      result.current.publishProjectionSurface(planPublication);
      result.current.openTool("recap");
    });
    const staleClose = result.current.close;
    act(() => {
      result.current.publishProjectionSurface(ingestPublication);
    });
    act(() => {
      result.current.openTool("ingest-recap");
    });
    act(() => {
      staleClose();
    });
    expect(result.current.active?.key).toBe("ingest-recap");
  });

  it("does not persist projection opens to localStorage", () => {
    const publication = {
      identity: { surfaceId: "plan", instanceKey: "plan\u001fpersist-test" },
      config: {
        id: "plan" as const,
        label: "Plan",
        context: {
          campaignId: "longmont-c2",
          liveSession: 22,
          ingestSession: 21,
          headerLabel: "Plan",
        },
        tools: [{ id: "recap", label: "Recap", size: "wide" as const }],
        canvas: { documentId: FIXTURE_DOC_ID },
        theme: {},
      },
    };
    const { result } = renderHook(() => useAgentInteraction(), { wrapper });
    act(() => {
      result.current.publishProjectionSurface(publication);
      result.current.openTool("recap");
    });
    const keys = Object.keys(localStorage);
    expect(keys.some((key) => key.includes("projection"))).toBe(false);
    expect(result.current.active?.key).toBe("recap");
  });
});
